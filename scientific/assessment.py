"""Automatic routing: original observations, reviewed interpolation, approved ML, refusal.

No LLM participates in routing. No training, registry writes or database writes occur here.
"""

import json
import math
from pathlib import Path

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from scientific.evidence import equal, finite, load_evidence, related_records
from scientific.schemas import Assessment, AssessmentRequest

MATCH_FIELDS = ("material_name", "geometry", "thickness_mm", "width_cm", "diameter_mm",
                "o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s", "gravity_g",
                "flow_direction", "is_reused_sample", "burn_sides", "co2_initial_pct", "flow_sequence_raw")


def differences(request, observation):
    data = request.model_dump()
    reasons = [key for key in MATCH_FIELDS if not equal(data.get(key), observation["features"].get(key))]
    if (not observation["pressure_measured"] and not request.allow_nominal_pressure
        and request.reference_uid != observation["uid"]):
        reasons.append("pressure provenance: source has no measured pressure")
    geometry = request.geometry.lower()
    if any(shape in geometry for shape in ("slab", "sheet", "film")) and (request.thickness_mm is None or request.width_cm is None):
        reasons.append("missing sample dimensions")
    if ("rod" in geometry or "sphere" in geometry) and request.diameter_mm is None:
        reasons.append("missing sample diameter")
    if request.flow_sequence_raw is None:
        reasons.append("missing complete recorded airflow sequence")
    return list(dict.fromkeys(reasons))


def public_observation(item, matched=False):
    return {"uid": item["uid"], "psi_id": item["psi_id"], "test_id": item["test_id"],
            "material": item["features"]["material_name"], "value": item["value"], "unit": item["unit"],
            "conditions": item["features"], "exact_match": matched, "pressure_measured": item["pressure_measured"],
            "source": item["source"]}


def describe_domain(observations):
    ranges = {}
    for key in ("o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s", "gravity_g"):
        values = [o["features"][key] for o in observations if finite(o["features"].get(key)) is not None]
        if values:
            ranges[key] = [min(values), max(values)]
    return {"available_target_observations": len(observations), "recorded_ranges": ranges,
            "materials": sorted({o["features"]["material_name"] for o in observations}),
            "range_warning": "Marginal ranges describe records; they do not validate a multivariate prediction domain."}


def interpolate(request, observations, policies_path):
    """Interpolation is disabled until a scientist-reviewed, independently validated policy exists.

    Policies specify one axis, a validated maximum bracket span, physical filters and validation
    metadata. All remaining physical conditions must match. No arbitrary distance threshold.
    """
    if not Path(policies_path).is_file():
        return None
    policies = json.loads(Path(policies_path).read_text(encoding="utf-8"))
    for policy in policies:
        if (policy.get("status") != "APPROVED" or policy.get("target") != request.target
            or not policy.get("scientific_review") or not policy.get("validation", {}).get("independent_groups", 0) >= 2
            or not policy.get("validation", {}).get("method") or not policy.get("version")
            or not policy.get("source_scope")):
            continue
        axis = policy.get("axis")
        # Vary one quantitative environmental feature; never interpolate categorical/geometry changes.
        if axis not in ("o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s"):
            continue
        query = request.model_dump()
        if not policy.get("physical_filters") or any(not equal(query.get(k), v) for k, v in policy["physical_filters"].items()):
            continue
        candidates = [o for o in observations if o["psi_id"] in policy["source_scope"]
                      and o["pressure_measured"] and o["unit"] == policy.get("unit")
                      and not [reason for reason in differences(request, o) if reason not in (axis, "flow_sequence_raw")]
                      and (axis != "flow_velocity_initial_cm_s" or o["features"]["flow_sequence_raw"] == str(o["features"][axis])
                           or o["features"]["flow_sequence_raw"] == str(int(o["features"][axis])))]
        if axis != "flow_velocity_initial_cm_s":
            candidates = [o for o in candidates if equal(query["flow_sequence_raw"], o["features"]["flow_sequence_raw"])]
        elif query["flow_sequence_raw"] not in (str(query[axis]), str(int(query[axis]))):
            continue
        lower = [o for o in candidates if o["features"][axis] < query[axis]]
        upper = [o for o in candidates if o["features"][axis] > query[axis]]
        if not lower or not upper:
            continue
        lo = max(o["features"][axis] for o in lower)
        hi = min(o["features"][axis] for o in upper)
        a = [o for o in lower if equal(o["features"][axis], lo)]
        b = [o for o in upper if equal(o["features"][axis], hi)]
        if (hi-lo > float(policy.get("max_bracket_span", 0)) or len(a) != 1 or len(b) != 1
            or not a[0].get("sample_id") or not b[0].get("sample_id")
            or (a[0]["psi_id"], a[0]["sample_id"]) == (b[0]["psi_id"], b[0]["sample_id"])):
            continue
        value = a[0]["value"] + (b[0]["value"]-a[0]["value"]) * (query[axis]-lo)/(hi-lo)
        return {"value": value, "unit": policy["unit"], "policy": policy, "observations": [a[0], b[0]]}
    return None


def model_assessment(request, models_dir):
    """Read current registry pointers each request; load the existing serialized preprocessing pipeline."""
    from ml.predict import assess as predict, load_version
    from ml.uncertainty import domain_reasons

    rejected, diagnostics, accepted = [], None, []
    for registry in sorted(Path(models_dir).glob("*")):
        approved = registry / "approved.json"
        pointer_path = approved if approved.is_file() else registry / "latest_research.json"
        if not pointer_path.is_file():
            continue
        try:
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
            version = pointer["version_id"]
            if len(version) != 64 or any(c not in "0123456789abcdef" for c in version):
                raise ValueError("Invalid model version")
            declared = json.loads((registry / "versions" / version / "metadata.json").read_text(encoding="utf-8"))
            if declared["target"] != request.target:
                continue
            _, metadata, domain = load_version(registry, pointer["version_id"], require_approved=approved.is_file())
            if metadata["target"] != request.target:
                continue
            task = metadata["task"]
            query = request.model_dump()
            query["gravity_level"] = {0.0: "0g", 1.0: "1g"}.get(request.gravity_g, "Simulated Partial-g")
            mismatch = [f"Model requires {k}={v}." for k, v in task["filters"].items() if not equal(query.get(k), v)]
            features = {key: query.get(key) for key in metadata["features"]}
            conditions = {key: query.get(key) for key in task["constant_conditions"]}
            reasons = domain_reasons(domain, features, request.material_name, conditions)
            diagnostics = {"status": metadata["status"], "artifact_loaded": True, "model": metadata["model"],
                "version": metadata["version_id"], "trained_at_utc": metadata["trained_at_utc"],
                "dataset_sha256": metadata["dataset_sha256"], "validation_metrics": metadata["evaluation"]["benchmark"],
                "domain_coverage": metadata["evaluation"].get("domain_coverage"), "counts": metadata["counts"],
                "validation_method": "Fixed, specimen/session-disjoint benchmark; grouped development CV; separate conformal calibration",
                "promotion_reasons": metadata["promotion"]["reasons"], "feature_domain": domain,
                "limitations": metadata["limitations"]}
            if not approved.is_file() or metadata["status"] != "APPROVED":
                rejected.append("The trained model is RESEARCH_ONLY; promotion and uncertainty validation have not passed.")
                rejected.extend(mismatch + reasons)
                continue
            if mismatch:
                rejected.extend(mismatch)
                continue
            result = predict(registry.name, features, request.material_name, conditions, models_dir=Path(models_dir))
            if result["status"] == "PREDICTED":
                interval = result.get("interval")
                if (finite(result.get("value")) is None or not interval or len(interval) != 2
                    or any(finite(v) is None for v in interval) or not interval[0] <= result["value"] <= interval[1]):
                    raise ValueError("Invalid prediction or uncertainty interval")
                accepted.append((result, diagnostics))
                continue
            rejected.extend(result["reasons"])
        except Exception:
            # A broken optional ML runtime/artifact must never interrupt database retrieval.
            rejected.append(f"Model {registry.name} is missing, incompatible or failed integrity/domain validation.")
    if len(accepted) == 1:
        return accepted[0][0], accepted[0][1], rejected
    if len(accepted) > 1:
        rejected.append("Several approved physical tasks overlap these inputs; the applicable phenomenon or apparatus is ambiguous. Numerical selection was withheld.")
    return None, diagnostics, rejected or ["No compatible approved model is available for this target."]


def assess(request: AssessmentRequest, db_path=DB_PATH, raw_root=RAW_DATA_DIR,
           models_dir=BASE_DIR / "models", policies_path=None, evidence_snapshot=None, related_context=None):
    result = Assessment(target=request.target)
    try:
        observations, problems = evidence_snapshot if evidence_snapshot is not None else load_evidence(db_path, raw_root, request.target)
    except Exception:
        result.limitations = ["Experimental database or source registry is unavailable; numerical assessment was withheld."]
        return result
    related = [o for o in observations if equal(o["features"]["material_name"], request.material_name)]
    result.domain_assessment = describe_domain(observations)
    exact = [o for o in related if (request.reference_uid is None or o["uid"] == request.reference_uid)
             and not differences(request, o)]
    result.supporting_experiments = [public_observation(o, bool(o in exact)) for o in (exact or related)]
    result.sources = list({o["source"]["source_id"]: o["source"] for o in (exact or related)}.values())
    if not related:
        try:
            context = related_context if related_context is not None else related_records(db_path, raw_root, request.material_name)
            result.sources = [o["source"] for o in context]
            result.domain_assessment["related_records_without_verified_target"] = [
                {k: o[k] for k in ("uid", "psi_id", "test_id")} for o in context]
        except Exception:
            result.domain_assessment["related_records_without_verified_target"] = []
    result.limitations = problems + [
        "Recorded measurements describe these runs, not a prediction of repeat experiments or a certified safety limit.",
        "No measurement uncertainty is supplied in the source CSV. Observed variability is not a prediction interval.",
        "Gravity regime and flow orientation use investigation/import metadata; they are not acceleration or direction sensor measurements.",
        "Exposure duration and complete time-resolved ventilation are unavailable; causal effects cannot be isolated."]
    if request.allow_nominal_pressure:
        result.limitations.append("Pressure matching explicitly accepts the database's nominal importer pressure; it was not measured in the original CSV.")
    if request.reference_uid and any(not o["pressure_measured"] for o in exact):
        result.limitations.append("This is retrieval of a recorded observation. Its nominal importer pressure is not a measured or validated pressure condition.")
    if exact and len({o["unit"] for o in exact}) == 1:
        values = [o["value"] for o in exact]
        result.status, result.method, result.unit = "OBSERVED", "Original, source-verified experimental measurements", exact[0]["unit"]
        result.observed_values = values
        result.value = values[0] if len(values) == 1 else None
        result.observed_range = [min(values), max(values)]
        result.domain_assessment["exact_matches"] = len(exact)
        return result
    reasons = []
    if not related:
        reasons.append("No source-verified measurements of this target are available for the requested material.")
    if related:
        for key in ("geometry", "gravity_g", "flow_direction"):
            if not any(equal(o["features"].get(key), request.model_dump()[key]) for o in related):
                reasons.append(f"Unsupported {key}: {request.model_dump()[key]}.")
        nearest_differences = sorted((differences(request, o) for o in related), key=len)[0]
        result.domain_assessment["closest_record_differences"] = nearest_differences
    try:
        interpolation = interpolate(request, related, policies_path or Path(models_dir) / "interpolation_policies.json")
    except (OSError, ValueError, KeyError, TypeError):
        interpolation = None
    if interpolation:
        result.status, result.method = "INTERPOLATED", "Scientifically reviewed one-dimensional linear interpolation"
        result.value, result.unit = interpolation["value"], interpolation["unit"]
        result.supporting_experiments = [public_observation(o) for o in interpolation["observations"]]
        result.sources = [o["source"] for o in interpolation["observations"]]
        result.domain_assessment["interpolation_policy"] = interpolation["policy"]
        result.limitations.append("Interpolation uncertainty is unavailable; no interval is implied.")
        return result
    prediction, diagnostics, rejected = model_assessment(request, models_dir)
    result.model_diagnostics = diagnostics
    comparable = []
    if prediction and diagnostics:
        from ml.uncertainty import domain_reasons
        domain = diagnostics["feature_domain"]
        for observation in related:
            physical = observation["features"]
            if (observation["unit"] == prediction["unit"]
                and all(equal(physical.get(key), request.model_dump().get(key)) for key in ("material_name", "geometry", "gravity_g", "flow_direction"))
                and not domain_reasons(domain, physical, physical["material_name"], physical)):
                comparable.append(observation)
    if prediction and comparable:
        result.status, result.method = "PREDICTED", "Approved serialized ML pipeline with validated joint applicability domain"
        result.value, result.unit = prediction["value"], prediction["unit"]
        result.prediction_interval = prediction["interval"]
        result.model_version, result.dataset_sha256 = prediction["model_version"], prediction["dataset_sha256"]
        result.supporting_experiments = [public_observation(o) for o in comparable]
        result.sources = [o["source"] for o in comparable]
        result.domain_assessment["comparable_supporting_experiments"] = len(comparable)
        result.domain_assessment["validated_domain_coverage"] = diagnostics.get("domain_coverage") if diagnostics else None
        if diagnostics:
            result.validation_metrics = diagnostics["validation_metrics"]
            result.training_sample_count = diagnostics["counts"]["development"]["samples"]
            result.independent_training_groups = diagnostics["counts"]["development"]["groups"]
        result.limitations.extend(prediction.get("limitations", []))
        return result
    if prediction:
        reasons.append("No current source-verified observations support this approved model's physical domain and target unit.")
    reasons.extend(rejected)
    reasons.append("No approved interpolation policy supports this query. Individual min/max ranges are insufficient.")
    result.domain_assessment["rejection_reasons"] = list(dict.fromkeys(reasons))
    result.limitations.extend(result.domain_assessment["rejection_reasons"])
    return result
