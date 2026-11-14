"""Deterministic Research Relevance Score (0-100) ranking engine for NASA mission profiles."""

from typing import Any
import pandas as pd
from config.settings import MISSION_PROFILES, RANKING_WEIGHTS


def _safe_float(val: Any) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _score_scenario(row: pd.Series, profile: dict[str, Any]) -> float:
    """Compute S_scenario (0-100) from O2%, pressure, flow speed, pillar, and fuel match."""
    score = 0.0

    # 1. Oxygen proximity (35 pts)
    o2 = _safe_float(row.get("o2_initial_pct"))
    target_o2 = float(profile["target_o2_pct"])
    min_o2 = float(profile["min_o2_pct"])
    if o2 is not None:
        o2_prox = max(0.0, 1.0 - abs(o2 - target_o2) / 22.0)
        score += 30.0 * o2_prox
        if o2 >= min_o2:
            score += 5.0
    else:
        score += 8.0

    # 2. Pressure proximity (20 pts)
    pressure = _safe_float(row.get("pressure_psi"))
    target_p = float(profile["target_pressure_psi"])
    if pressure is not None:
        p_prox = max(0.0, 1.0 - abs(pressure - target_p) / 10.0)
        score += 20.0 * p_prox
    else:
        score += 6.0

    # 3. Airflow / ventilation speed match (20 pts)
    v_flow = _safe_float(row.get("flow_velocity_min_cm_s"))
    if v_flow is None:
        v_flow = _safe_float(row.get("flow_velocity_initial_cm_s"))
    v_lo, v_hi = profile["target_flow_cm_s_range"]
    if v_flow is not None:
        if v_lo <= v_flow <= v_hi:
            score += 20.0
        else:
            dist = min(abs(v_flow - v_lo), abs(v_flow - v_hi))
            score += 20.0 * max(0.0, 1.0 - dist / 25.0)
    else:
        score += 6.0

    # 4. Safety pillar & fuel/material relevance (25 pts)
    pillar = str(row.get("safety_pillar") or "")
    if pillar in profile["priority_pillars"]:
        score += 15.0
    else:
        score += 7.0

    fuel_cat = str(row.get("fuel_category") or "")
    if fuel_cat in profile["preferred_fuel_categories"]:
        score += 10.0
    else:
        score += 4.0

    return round(min(100.0, score), 2)


def _score_completeness(row: pd.Series, meas_count: int) -> float:
    """Compute S_completeness (0-100) from calibrated boundary fields and EAV sensor density."""
    key_fields = (
        row.get("o2_initial_pct"),
        row.get("o2_final_pct"),
        row.get("pressure_psi"),
        row.get("flow_velocity_initial_cm_s"),
        row.get("material_name"),
    )
    present_count = sum(1 for v in key_fields if v is not None and not pd.isna(v))
    if str(row.get("flow_direction") or "Unknown") != "Unknown":
        present_count += 1
    field_score = 70.0 * (present_count / 6.0)
    meas_score = 30.0 * min(1.0, meas_count / 4.0)
    return round(min(100.0, field_score + meas_score), 2)


def _score_evidence(row: pd.Series, verified_meas_count: int, total_meas_count: int) -> float:
    """Compute S_evidence (0-100) from official DOI, verified multi-sensor data, and report notes."""
    score = 0.0
    if row.get("doi"):
        score += 40.0

    if total_meas_count > 0:
        verified_ratio = verified_meas_count / total_meas_count
        sensor_density = min(1.0, total_meas_count / 4.0)
        score += 40.0 * (0.6 * verified_ratio + 0.4 * sensor_density)

    obs = str(row.get("observations") or "").strip()
    if obs and "Validation:" not in obs[:15]:
        score += 20.0
    elif obs:
        score += 12.0

    return round(min(100.0, score), 2)


def _score_comparability(
    row: pd.Series,
    profile: dict[str, Any],
    psi_has_0g_1g_pair: bool,
) -> float:
    """Compute S_comparability (0-100) from 0g-1g corridor coverage and shared NASA hardware rack."""
    score = 0.0
    grav = str(row.get("gravity_level") or "0g")
    target_grav = str(profile["gravity_level"])

    if target_grav == "1g":
        score += 45.0 if grav == "1g" else 25.0
    elif target_grav == "0g":
        score += 45.0 if grav == "0g" else 20.0
    else:
        # Partial gravity (Lunar 1/6g, Martian 3/8g) uses 0g and 1g bounds as design envelope
        score += 40.0 if grav in {"0g", "1g", "Simulated Partial-g"} else 20.0

    if psi_has_0g_1g_pair:
        score += 35.0
    else:
        score += 15.0

    facility = str(row.get("hardware_facility") or "")
    if facility in profile["preferred_facilities"]:
        score += 20.0
    elif facility:
        score += 10.0

    return round(min(100.0, score), 2)


def rank_experiments_df(
    df_exp: pd.DataFrame,
    df_meas: pd.DataFrame | None = None,
    mission_profile: str = "Lunar Base",
) -> pd.DataFrame:
    """Calculate deterministic Research Relevance Score (0-100) for all experimental runs."""
    if df_exp.empty:
        return df_exp.copy()

    if mission_profile not in MISSION_PROFILES:
        raise ValueError(
            f"Unknown mission_profile '{mission_profile}'. Choose from: {list(MISSION_PROFILES.keys())}"
        )

    profile = MISSION_PROFILES[mission_profile]
    result = df_exp.copy()

    # Pre-aggregate measurement counts and verification ratios per test_id
    meas_stats: dict[str, tuple[int, int]] = {}
    if df_meas is not None and not df_meas.empty:
        for tid, group in df_meas.groupby("test_id"):
            total = int(len(group))
            verified = int((group["verification_status"] == "verified").sum())
            meas_stats[str(tid)] = (total, verified)

    # Identify psi_ids that contain both 0g and 1g experimental points for corridor comparability
    psi_gravs = result.groupby("psi_id")["gravity_level"].apply(set).to_dict()
    paired_psi_ids = {
        pid for pid, gravs in psi_gravs.items() if "0g" in gravs and "1g" in gravs
    }

    s_scen_list: list[float] = []
    s_comp_list: list[float] = []
    s_evid_list: list[float] = []
    s_cmpr_list: list[float] = []
    total_scores: list[float] = []

    w_scen = RANKING_WEIGHTS["scenario"]
    w_comp = RANKING_WEIGHTS["completeness"]
    w_evid = RANKING_WEIGHTS["evidence"]
    w_cmpr = RANKING_WEIGHTS["comparability"]

    for _, row in result.iterrows():
        tid = str(row.get("test_id") or "")
        pid = str(row.get("psi_id") or "")
        m_total, m_verified = meas_stats.get(tid, (0, 0))

        s_scen = _score_scenario(row, profile)
        s_comp = _score_completeness(row, m_total)
        s_evid = _score_evidence(row, m_verified, m_total)
        s_cmpr = _score_comparability(row, profile, pid in paired_psi_ids)

        final_score = round(
            w_scen * s_scen + w_comp * s_comp + w_evid * s_evid + w_cmpr * s_cmpr,
            2,
        )
        s_scen_list.append(s_scen)
        s_comp_list.append(s_comp)
        s_evid_list.append(s_evid)
        s_cmpr_list.append(s_cmpr)
        total_scores.append(final_score)

    result["s_scenario"] = s_scen_list
    result["s_completeness"] = s_comp_list
    result["s_evidence"] = s_evid_list
    result["s_comparability"] = s_cmpr_list
    result["research_relevance_score"] = total_scores
    result["mission_profile"] = mission_profile

    return result.sort_values(
        by=["research_relevance_score", "s_scenario", "test_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def rank_investigations_df(
    investigations: list[dict[str, Any]],
    df_exp: pd.DataFrame,
    df_meas: pd.DataFrame | None = None,
    mission_profile: str = "Lunar Base",
) -> pd.DataFrame:
    """Aggregate deterministic experiment scores up to the NASA PSI investigation level."""
    ranked_exp = rank_experiments_df(df_exp, df_meas=df_meas, mission_profile=mission_profile)
    inv_df = pd.DataFrame(investigations)
    if inv_df.empty:
        return inv_df

    if ranked_exp.empty:
        inv_df["research_relevance_score"] = 0.0
        inv_df["run_count"] = 0
        return inv_df

    agg = (
        ranked_exp.groupby("psi_id")
        .agg(
            run_count=("test_id", "count"),
            max_run_score=("research_relevance_score", "max"),
            mean_run_score=("research_relevance_score", "mean"),
            s_scenario=("s_scenario", "max"),
            s_completeness=("s_completeness", "mean"),
            s_evidence=("s_evidence", "mean"),
            s_comparability=("s_comparability", "max"),
        )
        .reset_index()
    )
    # Investigation score blends peak scenario fit (70%) with average run quality (30%)
    agg["research_relevance_score"] = (0.7 * agg["max_run_score"] + 0.3 * agg["mean_run_score"]).round(2)
    merged = inv_df.merge(agg, on="psi_id", how="left").fillna(
        {
            "run_count": 0,
            "research_relevance_score": 0.0,
            "s_scenario": 0.0,
            "s_completeness": 0.0,
            "s_evidence": 0.0,
            "s_comparability": 0.0,
        }
    )
    merged["run_count"] = merged["run_count"].astype(int)
    return merged.sort_values(
        by=["research_relevance_score", "psi_id"],
        ascending=[False, True],
    ).reset_index(drop=True)
