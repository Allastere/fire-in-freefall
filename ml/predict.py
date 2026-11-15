"""Stable inference entry point: research-only versions are never silently deployed."""

import hashlib
import importlib.metadata
import math
import re
from pathlib import Path

from config.settings import BASE_DIR
from ml.dataset import read_json
from ml.registry import approved_version


def load_version(registry, version, require_approved=True):
    import joblib

    if not re.fullmatch(r"[0-9a-f]{64}", version):
        raise ValueError("Invalid model version identifier.")
    directory = Path(registry) / "versions" / version
    metadata = read_json(directory / "metadata.json")
    if require_approved and (metadata["status"] != "APPROVED" or not metadata["promotion"]["approved"]):
        raise ValueError("The selected version has not passed promotion gates.")
    for package, expected in metadata["environment"]["packages"].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f"Model runtime version mismatch: {package}.")
    artifact = directory / "pipeline.joblib"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != metadata["artifact_sha256"]:
        raise ValueError("Model artifact checksum mismatch.")
    return joblib.load(artifact), metadata, read_json(directory / "domain.json")


def load_approved(registry):
    pointer = approved_version(registry)
    if pointer is None:
        raise ValueError("No approved model is available for this physical task.")
    result = load_version(registry, pointer["version_id"])
    if result[1]["artifact_sha256"] != pointer["artifact_sha256"]:
        raise ValueError("Approved pointer checksum mismatch.")
    return result


def assess(task_id, features, material, conditions, models_dir=BASE_DIR / "models"):
    import pandas as pd

    from ml.uncertainty import domain_reasons

    result = {"status": "INSUFFICIENT_DATA", "value": None, "unit": None, "interval": None,
              "model_version": None, "dataset_sha256": None, "reasons": [], "sources": []}
    if not re.fullmatch(r"[a-z][a-z0-9_]*", task_id):
        result["reasons"] = ["Invalid task identifier."]
        return result
    try:
        model, metadata, domain = load_approved(Path(models_dir) / task_id)
        result.update(model_version=metadata["version_id"], dataset_sha256=metadata["dataset_sha256"], unit=metadata["unit"])
        reasons = domain_reasons(domain, features, material, conditions)
        half_width = metadata["uncertainty"]["half_width"]
        if not domain["radius_validated"] or half_width is None:
            reasons.append("No independently validated domain and uncertainty interval available.")
        if reasons:
            result["reasons"] = reasons
            return result
        value = float(model.predict(pd.DataFrame([features]))[0])
        bounds = metadata["task"].get("target_bounds", [0, 25])
        if not math.isfinite(value) or value < bounds[0] or (bounds[1] is not None and value > bounds[1]):
            raise ValueError("Model returned a value outside the physical target limits.")
        result.update(status="PREDICTED", value=value, interval=[value-half_width, value+half_width],
                      reasons=[], limitations=metadata["limitations"])
    except (ValueError, OSError, KeyError, importlib.metadata.PackageNotFoundError) as exc:
        result["reasons"] = [str(exc)]
    return result
