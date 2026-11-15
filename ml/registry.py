"""Immutable artifacts and persistent leakage-aware data roles."""

import json
import math
import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from ml.dataset import fingerprint, read_json


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def assign_roles(snapshot, registry, task):
    path = Path(registry) / "split_manifest.json"
    samples = snapshot["samples"]
    contract = fingerprint({k: task[k] for k in ("version", "target", "filters", "numeric_features", "categorical_features")})
    scientific_contract = {k: task[k] for k in ("unit", "phenomenon", "constant_conditions")}
    if path.is_file():
        manifest: dict[str, Any] = read_json(path)
        if manifest["contract_sha256"] != contract:
            raise ValueError("Task feature contract changed. Use a new task version/registry for a new benchmark.")
        if "scientific_contract" not in manifest:
            # Preserve the first local research run's fixed roles when adding this stricter manifest field.
            old_pointer = read_json(Path(registry) / "latest_research.json")
            old_task = read_json(Path(registry) / "versions" / old_pointer["version_id"] / "metadata.json")["task"]
            manifest["scientific_contract"] = {k: old_task[k] for k in scientific_contract}
        if manifest["scientific_contract"] != scientific_contract:
            raise ValueError("Physical target/conditions changed. Use a new task version and benchmark.")
    else:
        groups = sorted({s["group"] for s in samples})
        if len(groups) < 5:
            raise ValueError("INSUFFICIENT_DATA: fewer than five independent groups for development/calibration/benchmark.")
        groups = np.random.default_rng(task["seed"]).permutation(groups).tolist()
        ntest, ncal = max(1, math.ceil(len(groups)*0.2)), max(1, int(len(groups)*0.15))
        initial_roles = {g: "benchmark" if i < ntest else "calibration" if i < ntest+ncal else "development"
                for i, g in enumerate(groups)}
        tokens = {t: initial_roles[s["group"]] for s in samples for t in s["tokens"]}
        frozen = {s["uid"]: {"role": initial_roles[s["group"]], "observation_sha256": s["observation_sha256"]}
                  for s in samples if initial_roles[s["group"]] != "development"}
        manifest = dict[str, Any](contract_sha256=contract, scientific_contract=scientific_contract,
                                  seed=task["seed"], tokens=tokens, frozen=frozen)
    found = {s["uid"]: s for s in samples}
    for uid, record in manifest["frozen"].items():
        if uid not in found or found[uid]["observation_sha256"] != record["observation_sha256"]:
            raise ValueError("Frozen calibration/benchmark data changed or disappeared; benchmark comparison blocked.")
    assigned, quarantined = [], []
    for sample in samples:
        roles = {manifest["tokens"][t] for t in sample["tokens"] if t in manifest["tokens"]}
        if len(roles) > 1:
            raise ValueError("New sample/session link crosses existing split roles. Training blocked to prevent leakage.")
        role = next(iter(roles), "development")
        if role != "development" and sample["uid"] not in manifest["frozen"]:
            quarantined.append({"uid": sample["uid"], "reason": "new_record_in_frozen_group"})
            continue
        for token in sample["tokens"]:
            manifest["tokens"][token] = role
        assigned.append({**sample, "role": role})
    roles_by_group = {}
    for sample in assigned:
        existing = roles_by_group.setdefault(sample["group"], sample["role"])
        if existing != sample["role"]:
            raise ValueError("A leakage group appears in multiple roles.")
    write_json(path, manifest)
    return assigned, quarantined, manifest


def approved_version(registry):
    pointer = Path(registry) / "approved.json"
    return read_json(pointer) if pointer.is_file() else None


def promote(registry, version_id, artifact_sha256, expected_previous):
    if approved_version(registry) != expected_previous:
        raise ValueError("Approved version changed concurrently; refusing to replace it.")
    write_json(Path(registry) / "approved.json", {"version_id": version_id, "artifact_sha256": artifact_sha256})
