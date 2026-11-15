"""Full, reproducible CPU training. Usage: python -m ml.train [--audit-only]."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import uuid
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from ml.dataset import extract_dataset, fingerprint, read_json
from ml.registry import approved_version, assign_roles, promote, write_json


def environment():
    packages = ("numpy", "pandas", "scipy", "scikit-learn", "joblib", "pint", "threadpoolctl", "cloudpickle")
    result = {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {p: importlib.metadata.version(p) for p in packages}}
    try:
        result["packages"]["catboost"] = importlib.metadata.version("catboost")
    except importlib.metadata.PackageNotFoundError:
        pass
    return result


def git_state():
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True, check=True).stdout.decode().strip()
        diff = subprocess.run(["git", "diff", "HEAD", "--", "*.py", "*.json", "requirements*.txt"],
                              cwd=BASE_DIR, capture_output=True, check=True).stdout
        return {"head": head, "tracked_diff_sha256": hashlib.sha256(diff).hexdigest()}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "tracked_diff_sha256": None}


def frame(samples):
    return pd.DataFrame([s["features"] for s in samples]), np.array([s["target"] for s in samples]), np.array([s["group"] for s in samples])


def train(task_id, task, snapshot, registry):
    started = time.perf_counter()
    import joblib
    from sklearn.base import clone
    from threadpoolctl import threadpool_limits

    from ml.evaluate import metrics, promotion_decision, select_model
    from ml.predict import load_approved, load_version
    from ml.preprocessing import candidates
    from ml.uncertainty import calibrate, domain_reasons, supported_domain

    registry = Path(registry)
    registry.mkdir(parents=True, exist_ok=True)
    lock_path = registry / ".training.lock"
    # Exclusive creation prevents two local publishers from racing over split and approved manifests.
    lock = lock_path.open("x", encoding="utf-8")
    try:
        lock.write(str(os.getpid()))
        lock.flush()
        assigned, quarantine, split = assign_roles(snapshot, registry, task)
        roles = {role: [s for s in assigned if s["role"] == role]
                 for role in ("development", "calibration", "benchmark")}
        if any(not rows for rows in roles.values()):
            raise ValueError("INSUFFICIENT_DATA: an independent data role has no observations.")
        X, y, groups = frame(roles["development"])
        cal_X, cal_y, cal_groups = frame(roles["calibration"])
        test_X, test_y, test_groups = frame(roles["benchmark"])
        benchmark_sha = fingerprint([{k: s[k] for k in ("uid", "observation_sha256")} for s in roles["benchmark"]])
        code_paths = list(Path(__file__).parent.glob("*.py")) + [BASE_DIR / "core/normalization.py", BASE_DIR / "scientific/archive.py", BASE_DIR / "requirements-ml.txt"]
        code = {str(p.relative_to(BASE_DIR)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(code_paths)}
        env = environment()
        version_id = fingerprint({"dataset": snapshot["dataset_sha256"], "split": split, "code": code,
                                  "environment": env, "task_id": task_id})
        version_dir = registry / "versions" / version_id
        if version_dir.is_dir():
            return read_json(version_dir / "metadata.json")
        models = candidates(task)
        with threadpool_limits(limits=1):
            winner, cv, oof = select_model(models, X, y, groups)
            fitted = clone(models[winner]).fit(X, y)
            baseline = clone(models["mean_baseline"]).fit(X, y)
            estimate = fitted.predict(test_X)
            baseline_estimate = baseline.predict(test_X)
            test_metrics = metrics(test_y, estimate, test_groups)
            baseline_metrics = metrics(test_y, baseline_estimate, test_groups)
            uncertainty = calibrate(fitted, cal_X, cal_y, cal_groups, test_X, test_y, task["interval_alpha"])
        domain = supported_domain(roles["development"], task)
        domain_checks = [domain_reasons(domain, sample["features"], task["filters"]["material_name"],
                                        task["constant_conditions"]) for sample in roles["benchmark"]]
        domain_coverage = sum(not r for r in domain_checks) / len(domain_checks)
        domain["benchmark_domain_coverage"] = domain_coverage
        domain["radius_validated"] = domain_coverage >= task["promotion"]["min_test_coverage"]
        expected_previous = approved_version(registry)
        previous_result = None
        previous_research_result = None
        previous_research = registry / "latest_research.json"
        if previous_research.is_file():
            old_pointer = read_json(previous_research)
            old_model, old_metadata, _ = load_version(registry, old_pointer["version_id"], require_approved=False)
            if old_metadata["benchmark_sha256"] == benchmark_sha:
                previous_research_result = {"version_id": old_metadata["version_id"],
                    "metrics": metrics(test_y, old_model.predict(test_X), test_groups)}
        if expected_previous:
            previous_model, previous_metadata, _ = load_approved(registry)
            if previous_metadata["benchmark_sha256"] != benchmark_sha:
                raise ValueError("Benchmark fingerprint differs from the approved version. Comparison aborted.")
            previous_result = metrics(test_y, previous_model.predict(test_X), test_groups)
        decision = promotion_decision(task, cv[winner], test_metrics, baseline_metrics, uncertainty,
                                      [s["scientific_status"] for s in assigned], previous_result)
        if not domain["radius_validated"]:
            decision["approved"] = False
            decision["reasons"].append("Supported-domain gate failed on the independent benchmark.")
        if cv[winner]["group_mae"] >= cv["mean_baseline"]["group_mae"]:
            decision["approved"] = False
            decision["reasons"].append("Learned model did not beat the mean baseline in grouped development CV.")
        metadata = {"version_id": version_id, "task_id": task_id, "target": task["target"], "unit": task["unit"],
                    "phenomenon": task["phenomenon"], "trained_at_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "APPROVED" if decision["approved"] else "RESEARCH_ONLY",
                    "resource_usage": {"elapsed_seconds":time.perf_counter()-started,"parallel_training":False,"max_estimator_threads":2},
                    "model": winner, "hyperparameters": {k: v if isinstance(v, (str, int, float, bool, type(None)))
                        else repr(v) for k, v in fitted.get_params(deep=True).items()},
                    "dataset_sha256": snapshot["dataset_sha256"], "benchmark_sha256": benchmark_sha,
                    "split_sha256": fingerprint(split), "code_sha256": fingerprint(code), "code_files": code,
                    "environment": env, "git": git_state(), "task": task,
                    "counts": {role: {"samples": len(rows), "groups": len({s['group'] for s in rows})}
                               for role, rows in roles.items()},
                    "supported_materials": domain["materials"], "investigations": sorted({s["psi_id"] for s in assigned}),
                    "features": task["numeric_features"] + task["categorical_features"],
                    "evaluation": {"cross_validation": cv, "benchmark": test_metrics, "baseline_benchmark": baseline_metrics,
                                   "previous_approved_benchmark": previous_result,
                                   "previous_research_benchmark": previous_research_result, "domain_coverage": domain_coverage},
                    "uncertainty": uncertainty, "promotion": decision, "limitations": task["limitations"],
                    "previous_approved": expected_previous, "training_mode": "full_retraining"}
        temporary = registry / "versions" / (".candidate-" + uuid.uuid4().hex)
        temporary.mkdir(parents=True)
        artifact = temporary / "pipeline.joblib"
        joblib.dump(fitted, artifact, compress=3)
        metadata["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        write_json(temporary / "metadata.json", metadata)
        write_json(temporary / "dataset_snapshot.json", snapshot)
        write_json(temporary / "split_manifest.json", split)
        write_json(temporary / "assigned_observations.json", assigned)
        write_json(temporary / "domain.json", domain)
        write_json(temporary / "evaluation_results.json", metadata["evaluation"])
        write_json(temporary / "promotion_decision.json", decision)
        write_json(temporary / "exclusions.json", snapshot["exclusions"] + quarantine)
        pd.DataFrame({"uid": [s["uid"] for s in roles["development"]], "group": groups, "observed": y,
                      **oof}).to_csv(temporary / "cv_predictions.csv", index=False)
        pd.DataFrame({"uid": [s["uid"] for s in roles["benchmark"]], "group": test_groups,
                      "observed": test_y, "predicted": estimate, "mean_baseline": baseline_estimate,
                      "inside_supported_domain": [not r for r in domain_checks]}).to_csv(temporary / "benchmark_predictions.csv", index=False)
        write_report(temporary, metadata)
        os.replace(temporary, version_dir)
        if decision["approved"]:
            promote(registry, version_id, metadata["artifact_sha256"], expected_previous)
        write_json(registry / "latest_research.json", {"version_id": version_id, "status": metadata["status"]})
        return metadata
    finally:
        lock.close()
        lock_path.unlink()


def write_report(directory, metadata):
    lines = ["# Research model training report", "", f"Task: `{metadata['task_id']}`",
             f"Version: `{metadata['version_id']}`", f"Status: **{metadata['status']}**", "",
             "The model was selected using development-group CV, never benchmark scores.",
             "Full retraining excludes frozen calibration and benchmark groups.", "",
             "| Role | Samples | Independent groups |", "| --- | ---: | ---: |"]
    for role, counts in metadata["counts"].items():
        lines.append(f"| {role} | {counts['samples']} | {counts['groups']} |")
    lines += ["", "## Development grouped cross-validation", "",
              f"| Model | MAE ({metadata['unit']}) | RMSE | R2 | Group MAE | Prediction coverage |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    def display(value):
        return "unavailable" if value is None else f"{value:.6g}"
    for name, result in metadata["evaluation"]["cross_validation"].items():
        lines.append("| " + " | ".join([name] + [display(result[k]) for k in
                     ("mae", "rmse", "r2", "group_mae", "prediction_coverage")]) + " |")
    test = metadata["evaluation"]["benchmark"]
    lines += ["", "## Independent benchmark", "", f"Selected model: **{metadata['model']}**",
              f"MAE: {display(test['mae'])} {metadata['unit']}.",
              f"RMSE: {display(test['rmse'])}; R2: {display(test['r2'])}.",
              f"Mean-baseline MAE: {display(metadata['evaluation']['baseline_benchmark']['mae'])}.",
              "", "## Promotion blockers", ""]
    lines.extend("- " + reason for reason in metadata["promotion"]["reasons"])
    lines += ["", "## Scientific limitations", ""]
    lines.extend("- " + item for item in metadata["limitations"])
    lines += ["", "A numeric experimental benchmark prediction is not an approved assessment or safety rating.",
              "No supported partial-gravity or high-oxygen model is established by this training run."]
    (directory / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="pmma_slab_co2_final")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("tasks.json"))
    parser.add_argument("--protocols", type=Path, default=Path(__file__).with_name("protocols.json"))
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--raw-root", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--models-dir", type=Path, default=BASE_DIR / "models")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--all", action="store_true", help="Train every compatible configured task sequentially on CPU")
    args = parser.parse_args(argv)
    if args.all:
        for task_id in read_json(args.config):
            command=[sys.executable,"-m","ml.train","--task",task_id,"--config",str(args.config),"--protocols",str(args.protocols),
                "--db",str(args.db),"--raw-root",str(args.raw_root),"--models-dir",str(args.models_dir)]
            if args.audit_only: command.append("--audit-only")
            subprocess.run(command,check=True)
        return 0
    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.task):
        parser.error("Task ID must be a lowercase identifier.")
    task = read_json(args.config)[args.task]
    snapshot = extract_dataset(args.db, args.raw_root, task, read_json(args.protocols)["protocols"])
    if args.audit_only:
        print(json.dumps({"samples": len(snapshot["samples"]), "groups": len({s['group'] for s in snapshot['samples']}),
                          "dataset_sha256": snapshot["dataset_sha256"],
                          "exclusions": dict(Counter(s['reason'] for s in snapshot['exclusions']))}, indent=2))
        return 0
    metadata = train(args.task, task, snapshot, args.models_dir / args.task)
    print(json.dumps({k: metadata[k] for k in ("version_id", "status", "model", "counts", "evaluation", "promotion")}, indent=2))
    # Successful research training is distinct from production approval.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileExistsError, KeyError, OSError) as exc:
        print(json.dumps({"status": "TRAINING_BLOCKED", "reason": str(exc)}), file=sys.stderr)
        sys.exit(2)
