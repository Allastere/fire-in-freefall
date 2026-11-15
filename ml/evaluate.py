"""Model selection only on development groups; independent benchmark remains untouched."""

import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold


def metrics(actual, predicted, groups):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    finite = np.isfinite(predicted)
    result = {"n": len(actual), "n_predicted": int(finite.sum()), "prediction_coverage": float(finite.mean()),
              "mae": None, "rmse": None, "r2": None, "group_mae": None}
    if finite.any():
        truth, estimate = actual[finite], predicted[finite]
        result.update(mae=float(mean_absolute_error(truth, estimate)),
                      rmse=float(np.sqrt(mean_squared_error(truth, estimate))))
        if len(truth) > 1 and np.ptp(truth) > 0:
            result["r2"] = float(r2_score(truth, estimate))
        by_group = pd.DataFrame({"group": np.asarray(groups)[finite], "error": np.abs(truth-estimate)})
        result["group_mae"] = float(by_group.groupby("group").error.mean().mean())
    return result


def select_model(models, X, y, groups):
    unique = len(set(groups))
    if unique < 3:
        raise ValueError("INSUFFICIENT_DATA: at least three development groups are required for model comparison.")
    folds = list(GroupKFold(n_splits=min(4, unique)).split(X, y, groups))
    results, predictions = {}, {}
    for name, pipeline in models.items():
        prediction = np.full(len(X), np.nan)
        notices = []
        for training, validation in folds:
            assert not set(groups[training]) & set(groups[validation])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model = clone(pipeline).fit(X.iloc[training], y[training])
                prediction[validation] = model.predict(X.iloc[validation])
            notices.extend(str(w.message) for w in caught)
        predictions[name] = prediction
        results[name] = {**metrics(y, prediction, groups), "warnings": sorted(set(notices)),
                         "folds": len(folds)}
    eligible = [name for name, result in results.items() if result["prediction_coverage"] == 1.0
                and name not in ("mean_baseline", "linear_interpolation")]
    winner = min(eligible, key=lambda name: (results[name]["group_mae"], name))
    return winner, results, predictions


def promotion_decision(task, cv, test, baseline, uncertainty, protocol_statuses, previous=None):
    """All criteria are fixed before training; missing scientific tolerances always block release."""
    policy = task["promotion"]
    reasons = []
    if task["scientific_review"] != "approved" or set(protocol_statuses) != {"approved"}:
        reasons.append("Scientific protocol review is incomplete.")
    for key in ("max_mae", "max_rmse", "max_interval_width"):
        if policy.get(key) is None:
            reasons.append(f"No approved physical tolerance configured: {key}.")
    if test["prediction_coverage"] < policy["min_test_coverage"]:
        reasons.append("Insufficient benchmark prediction coverage.")
    if test["mae"] is None or test["mae"] >= baseline["mae"]:
        reasons.append("No independent MAE improvement over the mean baseline.")
    if cv["group_mae"] is None or not np.isfinite(cv["group_mae"]):
        reasons.append("Development group error is unavailable.")
    for metric, bound in (("mae", "max_mae"), ("rmse", "max_rmse")):
        if policy.get(bound) is not None and (test[metric] is None or test[metric] > policy[bound]):
            reasons.append(f"Benchmark {metric} exceeds the approved tolerance.")
    if uncertainty["half_width"] is None:
        reasons.append("Too few independent calibration groups for a finite requested coverage interval.")
    else:
        if policy.get("max_interval_width") is not None and 2 * uncertainty["half_width"] > policy["max_interval_width"]:
            reasons.append("Prediction interval is too wide.")
        if uncertainty["benchmark_coverage"] < 1 - task["interval_alpha"]:
            reasons.append("Requested interval coverage not reached on the independent benchmark.")
    if previous is not None and test["mae"] > previous["mae"]:
        reasons.append("Challenger MAE regressed against the approved model on the same benchmark.")
    return {"approved": not reasons, "reasons": reasons}
