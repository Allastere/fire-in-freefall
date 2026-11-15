"""Clean data-access repository functions for Streamlit UI and SI engines."""

import json
from pathlib import Path
from typing import Any
import pandas as pd
from config.settings import DB_PATH
from core.ranking import rank_experiments_df, rank_investigations_df
from database.connection import get_connection


_FACILITY_ALIASES: dict[str, tuple[str, ...]] = {
    "CIR / MDCA": ("CIR", "MDCA"),
    "CIR/MDCA": ("CIR", "MDCA"),
    "Saffire / Cygnus": ("Saffire/Cygnus",),
}


def _resolve_facilities(
    hardware_facility: str | list[str] | tuple[str, ...] | set[str] | None,
) -> list[str] | None:
    """Normalize UI facility labels (e.g. 'CIR / MDCA') into stored database values."""
    if hardware_facility is None:
        return None
    if isinstance(hardware_facility, str):
        cleaned = hardware_facility.strip()
        if not cleaned or cleaned == "All":
            return None
        return list(_FACILITY_ALIASES.get(cleaned, (cleaned,)))

    resolved: list[str] = []
    for item in hardware_facility:
        sub = _resolve_facilities(item)
        if sub is None:
            return None
        for fac in sub:
            if fac not in resolved:
                resolved.append(fac)
    return resolved or None


def get_all_investigations(
    safety_pillar: str | None = None,
    hardware_facility: str | list[str] | tuple[str, ...] | set[str] | None = None,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    """Return all NASA PSI investigations with parsed related_psi_ids and mandatory DOI fields."""
    query = """
        SELECT
            psi_id, acronym, title, doi, psi_url, citation_text,
            safety_pillar, fuel_category, hardware_facility,
            objectives, summary, earth_spinoff_text, related_psi_ids,
            pi_names, pillar_classifications_json, objective_tags_json,
            hardware_relationships_json, cross_relationships_json, limitations_json
        FROM investigations
        WHERE 1 = 1
    """
    params: list[Any] = []

    if safety_pillar and safety_pillar != "All":
        query += " AND (safety_pillar = ? OR safety_pillar = 'Multi')"
        params.append(safety_pillar)

    facilities = _resolve_facilities(hardware_facility)
    if facilities:
        placeholders = ", ".join("?" for _ in facilities)
        query += f" AND hardware_facility IN ({placeholders})"
        params.extend(facilities)

    query += " ORDER BY psi_id ASC"

    conn = get_connection(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            raw_related = item.get("related_psi_ids") or "[]"
            try:
                item["related_psi_ids"] = json.loads(raw_related) if isinstance(raw_related, str) else raw_related
            except json.JSONDecodeError:
                item["related_psi_ids"] = []
            results.append(item)
        return results
    finally:
        conn.close()


def get_experiments_df(
    psi_id: str | None = None,
    safety_pillar: str | None = None,
    gravity_level: str | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """Return normalized experimental runs joined with sample geometry, conditions, and investigation DOI."""
    query = """
        SELECT
            e.test_id,
            e.psi_id,
            i.acronym,
            i.safety_pillar,
            i.fuel_category,
            i.hardware_facility,
            i.doi,
            e.pi_name,
            e.sample_id,
            CAST(e.is_reused_sample AS INTEGER) AS is_reused_sample,
            e.flow_direction,
            e.outcome,
            s.material_name,
            s.original_material_designation,
            s.material_family,
            s.fuel_phase,
            s.geometry,
            s.thickness_mm,
            s.width_cm,
            s.length_cm,
            s.diameter_mm,
            c.o2_initial_pct,
            c.o2_final_pct,
            c.oxygen_location,
            c.pressure_psi,
            c.diluent_gas,
            c.diluent_pct,
            c.co2_diluent_pct,
            c.he_diluent_pct,
            c.n2_diluent_pct,
            c.ambient_temp_k,
            c.flow_velocity_initial_cm_s,
            c.flow_velocity_min_cm_s,
            c.flow_velocity_extinction_cm_s,
            c.flow_sequence_raw,
            c.gravity_level,
            c.ignition_outcome,
            c.propagation_outcome,
            c.suppression_outcome,
            c.material_behaviour,
            e.observations,
            e.raw_attributes_json
        FROM experiments e
        JOIN investigations i ON e.psi_id = i.psi_id
        LEFT JOIN samples s ON e.test_id = s.test_id
        LEFT JOIN conditions c ON e.test_id = c.test_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if psi_id and psi_id != "All":
        query += " AND e.psi_id = ?"
        params.append(psi_id)

    if safety_pillar and safety_pillar != "All":
        query += " AND (i.safety_pillar = ? OR i.safety_pillar = 'Multi')"
        params.append(safety_pillar)

    if gravity_level and gravity_level != "All":
        query += " AND c.gravity_level = ?"
        params.append(gravity_level)

    query += " ORDER BY e.psi_id ASC, e.test_id ASC"

    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty and "is_reused_sample" in df.columns:
            df["is_reused_sample"] = df["is_reused_sample"].astype(bool)
        return df
    finally:
        conn.close()


def get_measurements_df(
    psi_id: str | None = None,
    parameter: str | None = None,
    test_id: str | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """Return vertical EAV sensor measurements enriched with experimental conditions and DOI metadata."""
    query = """
        SELECT
            m.id,
            m.psi_id,
            i.acronym,
            i.safety_pillar,
            i.doi,
            m.test_id,
            s.material_name,
            s.material_family,
            s.fuel_phase,
            c.o2_initial_pct,
            c.oxygen_location,
            c.pressure_psi,
            c.flow_velocity_initial_cm_s,
            c.flow_velocity_min_cm_s,
            c.gravity_level,
            e.outcome,
            m.parameter,
            m.subtype,
            m.value,
            m.value_min,
            m.value_max,
            m.unit,
            m.statistic_type,
            m.instrument,
            m.ignition_method,
            CAST(m.is_over_range AS INTEGER) AS is_over_range,
            m.value_type,
            m.eligibility_status,
            m.source_doc,
            m.source_page,
            m.source_trace_json,
            m.verification_status
        FROM measurements m
        JOIN investigations i ON m.psi_id = i.psi_id
        LEFT JOIN experiments e ON m.test_id = e.test_id
        LEFT JOIN samples s ON m.test_id = s.test_id
        LEFT JOIN conditions c ON m.test_id = c.test_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if psi_id and psi_id != "All":
        query += " AND m.psi_id = ?"
        params.append(psi_id)

    if parameter and parameter != "All":
        query += " AND m.parameter = ?"
        params.append(parameter)

    if test_id:
        query += " AND m.test_id = ?"
        params.append(test_id)

    query += " ORDER BY m.psi_id ASC, m.test_id ASC, m.parameter ASC"

    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty and "is_over_range" in df.columns:
            df["is_over_range"] = df["is_over_range"].astype(bool)
        return df
    finally:
        conn.close()


def get_findings(
    psi_id: str | None = None,
    category: str | None = None,
    safety_pillar: str | None = None,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    """Return verified scientific findings with source document, page reference, and NASA DOI."""
    query = """
        SELECT
            f.id,
            f.psi_id,
            i.acronym,
            i.title,
            i.safety_pillar,
            i.hardware_facility,
            i.doi,
            i.psi_url,
            f.finding_title,
            f.finding_type,
            f.safety_pillar AS finding_safety_pillar,
            f.objective_tag,
            f.category,
            f.claim,
            f.evidence_quote,
            f.source_doc,
            f.source_page
        FROM findings f
        JOIN investigations i ON f.psi_id = i.psi_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if psi_id and psi_id != "All":
        query += " AND f.psi_id = ?"
        params.append(psi_id)

    if category and category != "All":
        query += " AND f.category = ?"
        params.append(category)

    if safety_pillar and safety_pillar != "All":
        query += " AND (i.safety_pillar = ? OR i.safety_pillar = 'Multi')"
        params.append(safety_pillar)

    query += " ORDER BY f.psi_id ASC, f.id ASC"

    conn = get_connection(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_ranked_experiments_df(
    mission_profile: str = "Lunar Base",
    psi_id: str | None = None,
    safety_pillar: str | None = None,
    gravity_level: str | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """Return experimental runs scored and sorted deterministically for a mission profile."""
    exp_df = get_experiments_df(
        psi_id=psi_id,
        safety_pillar=safety_pillar,
        gravity_level=gravity_level,
        db_path=db_path,
    )
    meas_df = get_measurements_df(psi_id=psi_id, db_path=db_path)
    return rank_experiments_df(exp_df, df_meas=meas_df, mission_profile=mission_profile)


def get_ranked_investigations(
    mission_profile: str = "Lunar Base",
    safety_pillar: str | None = None,
    hardware_facility: str | list[str] | tuple[str, ...] | set[str] | None = None,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    """Return investigations ranked deterministically for a mission profile."""
    invs = get_all_investigations(
        safety_pillar=safety_pillar,
        hardware_facility=hardware_facility,
        db_path=db_path,
    )
    exp_df = get_experiments_df(safety_pillar=safety_pillar, db_path=db_path)
    meas_df = get_measurements_df(db_path=db_path)
    ranked_df = rank_investigations_df(invs, exp_df, df_meas=meas_df, mission_profile=mission_profile)
    return ranked_df.to_dict(orient="records")


if __name__ == "__main__":
    invs = get_all_investigations()
    exp_df = get_experiments_df()
    meas_df = get_measurements_df()
    finds = get_findings()
    ranked_df = get_ranked_experiments_df(mission_profile="Lunar Base")
    assert len(invs) == 19, f"Expected 19 investigations, got {len(invs)}"
    assert len(exp_df) >= 750, f"Expected >= 750 experiments, got {len(exp_df)}"
    assert len(meas_df) >= 2500, f"Expected >= 2500 measurements, got {len(meas_df)}"
    assert len(finds) >= 15, f"Expected >= 15 findings, got {len(finds)}"
    assert len(ranked_df) == len(exp_df)
    assert len(get_experiments_df(psi_id="'; DROP TABLE investigations; --")) == 0
    cir_mdca_invs = get_all_investigations(hardware_facility="CIR / MDCA")
    assert {i["psi_id"] for i in cir_mdca_invs} == {
        "PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-39", "PSI-68", "PSI-69", "PSI-159"
    }, cir_mdca_invs
    saffire_invs = get_all_investigations(hardware_facility="Saffire / Cygnus")
    assert {i["psi_id"] for i in saffire_invs} == {"PSI-98", "PSI-99", "PSI-100"}, saffire_invs
    assert len(get_ranked_investigations(mission_profile="Lunar Base", hardware_facility="CIR / MDCA")) == 9
    print(
        f"Repository self-check PASSED: {len(invs)} investigations, "
        f"{len(exp_df)} experiments, {len(meas_df)} measurements, {len(finds)} findings."
    )

