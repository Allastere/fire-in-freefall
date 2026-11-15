"""Conservative supported-domain and group calibration summaries."""

import math

import numpy as np


def calibrate(model, calibration_X, calibration_y, calibration_groups, benchmark_X, benchmark_y, alpha):
    residuals = np.abs(calibration_y - model.predict(calibration_X))
    groups = sorted(set(calibration_groups))
    scores = sorted(float(residuals[calibration_groups == g].max()) for g in groups)
    rank = math.ceil((len(scores) + 1) * (1-alpha))
    half_width = scores[rank-1] if rank <= len(scores) else None
    coverage = None
    if half_width is not None:
        coverage = float(np.mean(np.abs(benchmark_y-model.predict(benchmark_X)) <= half_width))
    return {"method": "group_max_absolute_residual_split_conformal", "alpha": alpha,
            "calibration_groups": len(groups), "quantile_rank": rank, "half_width": half_width,
            "benchmark_coverage": coverage,
            "limitation": "Requires exchangeable experimental groups; domain transfer is not established."}


def supported_domain(samples, task):
    numeric = {name: {"min": min(s["features"][name] for s in samples),
                      "max": max(s["features"][name] for s in samples)} for name in task["numeric_features"]}
    categories = {name: sorted({s["features"][name] for s in samples}) for name in task["categorical_features"]}
    array = np.asarray([[s["features"][k] for k in task["numeric_features"]] for s in samples], dtype=float)
    scale = np.std(array, axis=0)
    scale[scale < 1e-12] = 1
    normalized = array / scale
    # One nearest distance per independent group, not per repeated measurement.
    group_distances = []
    for i, sample in enumerate(samples):
        other = [j for j, item in enumerate(samples) if item["group"] != sample["group"]]
        if other:
            group_distances.append(float(np.linalg.norm(normalized[other]-normalized[i], axis=1).min()))
    radius = float(np.quantile(group_distances, 0.9)) if group_distances else 0.0
    return {"numeric_ranges": numeric, "numeric_feature_order": task["numeric_features"],
            "categories": categories, "scale": scale.tolist(),
            "neighbor_radius": radius, "radius_method": "training_90th_percentile_nearest_other_group_distance",
            "radius_validated": False, "min_local_groups": task["promotion"]["min_local_groups"],
            "materials": sorted({s["material"] for s in samples}), "conditions": task["constant_conditions"],
            "physical_series": task["filters"], "training_points": [s["features"] for s in samples],
            "training_groups": [s["group"] for s in samples]}


def domain_reasons(domain, features, material, conditions):
    reasons = []
    if material not in domain["materials"]:
        reasons.append("Unknown material.")
    for key, value in domain["conditions"].items():
        supplied = conditions.get(key)
        if not isinstance(supplied, (int, float)) or not math.isclose(supplied, value, abs_tol=1e-8):
            reasons.append(f"Unsupported or unknown condition: {key}.")
    for key, bounds in domain["numeric_ranges"].items():
        value = features.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not bounds["min"] <= value <= bounds["max"]:
            reasons.append(f"Missing or out-of-domain feature: {key}.")
    for key, allowed in domain["categories"].items():
        if features.get(key) not in allowed:
            reasons.append(f"Unknown categorical regime: {key}.")
    if features.get("is_reused_sample") not in (0, 1):
        reasons.append("Material reuse must be known (0 or 1).")
    if reasons:
        return reasons
    names = domain["numeric_feature_order"]
    point = np.array([features[k] for k in names]) / domain["scale"]
    local_groups = set()
    for observed, group in zip(domain["training_points"], domain["training_groups"]):
        if any(observed[k] != features[k] for k in domain["categories"]):
            continue
        distance = np.linalg.norm(np.array([observed[k] for k in names]) / domain["scale"] - point)
        if distance <= domain["neighbor_radius"]:
            local_groups.add(group)
    if len(local_groups) < domain["min_local_groups"]:
        reasons.append("Too few nearby independent groups in this physical regime.")
    return reasons
