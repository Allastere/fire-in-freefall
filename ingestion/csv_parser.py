"""Deterministic and adaptive NASA PSI CSV parser with Pint normalization and SQLite persistence."""

import json
import math
from pathlib import Path
from typing import Any
import pandas as pd

from config.settings import DB_PATH, RAW_DATA_DIR, STANDARD_PRESSURE_PSI
from core.normalization import (
    normalize_pressure_to_psi,
    normalize_velocity_to_cm_s,
    parse_air_display,
    parse_co_value,
    parse_fuel_sample_material,
    parse_optional_float,
)
from core.schemas import (
    ColumnMappingPlan,
    ConditionModel,
    ExperimentModel,
    ExperimentOutcome,
    FlowDirection,
    MeasurementModel,
    SampleModel,
)
from core.validation import validate_co2_pct, validate_condition
from database.connection import get_connection, init_db
from ingestion.file_loader import compute_sha256, discover_psi_files, is_file_processed, register_file
from ingestion.pdf_parser import parse_bass2_appendix_a
from ingestion.schema_mapper import LLMMapperCallback, map_csv_columns
from ingestion.text_parser import parse_bass2_faq


def _clean_raw_row(row_dict: dict[str, Any]) -> dict[str, Any]:
    """Convert pandas NaN values to None so raw_attributes_json is valid strict JSON."""
    cleaned: dict[str, Any] = {}
    for k, v in row_dict.items():
        key = str(k).strip()
        if isinstance(v, float) and math.isnan(v):
            cleaned[key] = None
        else:
            cleaned[key] = v
    return cleaned


def _infer_outcome(
    air_info: dict[str, Any],
    observations: str,
    total_frames_raw: Any,
) -> ExperimentOutcome:
    """Infer standardized outcome from flow sequence, PDF observations, and imaging count."""
    combined = f"{air_info.get('flow_sequence_raw') or ''} {observations}".lower()
    if any(p in combined for p in ("no ign", "did not ignite", "would not sustain", "no sustained", "not spread")):
        return "No Ignition"
    if air_info.get("has_blowoff_marker") or "blowoff" in combined or "blew out" in combined:
        return "Blowoff"
    if (
        air_info.get("flow_velocity_extinction_cm_s") is not None
        or air_info.get("has_extinction_marker")
        or any(p in combined for p in ("extinguish", "quench", "flame died"))
    ):
        return "Quenched"
    frames_str = str(total_frames_raw or "").strip().lower()
    if frames_str not in {"", "none", "nan"} or air_info.get("flow_velocity_initial_cm_s") is not None:
        return "Sustained"
    return "Unknown"


def _resolve_flow_direction(
    test_id: str,
    pi_name: str,
    pdf_meta: dict[str, dict[str, Any]],
    faq_defaults: dict[str, str],
) -> FlowDirection:
    """Resolve flow direction strictly from PDF Appendix A first, falling back to FAQ PI defaults."""
    raw_dir = pdf_meta.get(test_id, {}).get("flow_direction")
    if raw_dir in {"Opposed", "Concurrent", "Stagnation", "Quiescent"}:
        return raw_dir  # type: ignore[return-value]
    faq_dir = faq_defaults.get(pi_name)
    if faq_dir in {"Opposed", "Concurrent", "Stagnation", "Quiescent"}:
        return faq_dir  # type: ignore[return-value]
    return "Unknown"


def _field_lookup_from_plan(plan: ColumnMappingPlan) -> dict[tuple[str, str], tuple[str, str | None]]:
    """Build (target_table, target_field) -> (raw_column, unit) index from ColumnMappingPlan."""
    lookup: dict[tuple[str, str], tuple[str, str | None]] = {}
    for item in plan.mappings:
        if item.target_table != "ignore":
            lookup[(item.target_table, item.target_field)] = (item.raw_column, item.detected_unit)
    return lookup


def parse_and_store_csv(
    csv_path: Path | str,
    psi_id: str = "PSI-25",
    pdf_meta: dict[str, dict[str, Any]] | None = None,
    faq_info: dict[str, Any] | None = None,
    llm_callback: LLMMapperCallback | None = None,
    db_path: Path | str = DB_PATH,
    force: bool = False,
) -> dict[str, Any]:
    """Parse a NASA PSI experimental CSV table using 2-stage mapping + Pint and persist to SQLite."""
    path = Path(csv_path)
    sha256_hash = compute_sha256(path)
    init_db(db_path)

    if not force and is_file_processed(sha256_hash, db_path):
        return {
            "status": "skipped_duplicate",
            "file": path.name,
            "sha256": sha256_hash,
            "experiments_loaded": 0,
            "measurements_loaded": 0,
        }

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    sample_rows = df.head(3).to_dict(orient="records")
    plan = map_csv_columns(list(df.columns), sample_rows, psi_id=psi_id, llm_callback=llm_callback)
    lookup = _field_lookup_from_plan(plan)

    pdf_meta = pdf_meta or {}
    faq_defaults = (faq_info or {}).get("pi_flow_defaults", {})

    def _get_col(row: dict[str, Any], table: str, field: str, default: Any = None) -> Any:
        col_info = lookup.get((table, field))
        if not col_info:
            return default
        return row.get(col_info[0], default)

    records_to_insert: list[tuple[ExperimentModel, SampleModel, ConditionModel, list[MeasurementModel]]] = []
    validation_warnings: list[str] = []

    for row in df.to_dict(orient="records"):
        raw_clean = _clean_raw_row(row)
        test_id = str(_get_col(row, "experiments", "test_id", "")).strip()
        if not test_id:
            continue

        pi_name = str(_get_col(row, "experiments", "pi_name", "Unknown")).strip() or "Unknown"
        sample_id = str(_get_col(row, "experiments", "sample_id", "")).strip()
        is_reused = sample_id.lower().endswith("m")

        # Sample material & dimensions via Pint
        raw_mat = _get_col(row, "samples", "material_name", "")
        mat_info = parse_fuel_sample_material(raw_mat)

        # Airflow & Fan parsing
        raw_air = _get_col(row, "conditions", "flow_velocity_initial_cm_s")
        raw_fan = row.get("Fan display")
        air_info = parse_air_display(raw_air, raw_fan)
        air_unit = (lookup.get(("conditions", "flow_velocity_initial_cm_s")) or (None, "cm/s"))[1] or "cm/s"
        if air_unit != "cm/s":
            if air_info["flow_velocity_initial_cm_s"] is not None:
                air_info["flow_velocity_initial_cm_s"] = normalize_velocity_to_cm_s(
                    air_info["flow_velocity_initial_cm_s"], air_unit
                )
            if air_info["flow_velocity_min_cm_s"] is not None:
                air_info["flow_velocity_min_cm_s"] = normalize_velocity_to_cm_s(
                    air_info["flow_velocity_min_cm_s"], air_unit
                )
            if air_info["flow_velocity_extinction_cm_s"] is not None:
                air_info["flow_velocity_extinction_cm_s"] = normalize_velocity_to_cm_s(
                    air_info["flow_velocity_extinction_cm_s"], air_unit
                )

        # Pressure via Pint (default ISS cabin 14.7 psi when absent)
        raw_pressure = parse_optional_float(_get_col(row, "conditions", "pressure_psi"))
        pressure_unit = (lookup.get(("conditions", "pressure_psi")) or (None, "psi"))[1] or "psi"
        pressure_psi = (
            normalize_pressure_to_psi(raw_pressure, pressure_unit)
            if raw_pressure is not None
            else STANDARD_PRESSURE_PSI
        )

        # Strictly calibrated O2 columns (Rule 2)
        o2_init = parse_optional_float(_get_col(row, "conditions", "o2_initial_pct"))
        o2_final = parse_optional_float(_get_col(row, "conditions", "o2_final_pct"))

        pdf_row = pdf_meta.get(test_id, {})
        observations = str(pdf_row.get("observations") or "").strip()
        if not observations and row.get("Total Frames Shot"):
            observations = f"Total frames shot: {row.get('Total Frames Shot')}; Radiometer gain: {row.get('Radiometer gain   (1000   250   50   10)', 'N/A')}"

        flow_direction = _resolve_flow_direction(test_id, pi_name, pdf_meta, faq_defaults)
        outcome = _infer_outcome(air_info, observations, row.get("Total Frames Shot"))

        condition = ConditionModel(
            test_id=test_id,
            o2_initial_pct=o2_init,
            o2_final_pct=o2_final,
            pressure_psi=pressure_psi,
            diluent_gas="N2",
            diluent_pct=round(100.0 - o2_init, 2) if o2_init is not None else None,
            flow_velocity_initial_cm_s=air_info["flow_velocity_initial_cm_s"],
            flow_velocity_min_cm_s=air_info["flow_velocity_min_cm_s"],
            flow_velocity_extinction_cm_s=air_info["flow_velocity_extinction_cm_s"],
            flow_sequence_raw=air_info["flow_sequence_raw"],
            gravity_level="0g",
        )
        cond_status, cond_warns = validate_condition(condition)
        if cond_warns:
            validation_warnings.extend(f"{test_id}: {w}" for w in cond_warns)
            observations = (observations + f" [Validation: {'; '.join(cond_warns)}]").strip()

        experiment = ExperimentModel(
            test_id=test_id,
            psi_id=psi_id,
            pi_name=pi_name,
            sample_id=sample_id,
            is_reused_sample=is_reused,
            flow_direction=flow_direction,
            outcome=outcome,
            observations=observations,
            raw_attributes_json=json.dumps(raw_clean, ensure_ascii=False),
        )
        sample = SampleModel(
            test_id=test_id,
            material_name=mat_info["material_name"],
            geometry=mat_info["geometry"],
            thickness_mm=mat_info["thickness_mm"],
            width_cm=mat_info["width_cm"],
            diameter_mm=mat_info["diameter_mm"],
        )

        # Build EAV measurements rows
        meas_rows: list[MeasurementModel] = []
        src_page = pdf_row.get("source_page")

        if air_info["flow_velocity_extinction_cm_s"] is not None:
            meas_rows.append(
                MeasurementModel(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="extinction_velocity_cm_s",
                    value=air_info["flow_velocity_extinction_cm_s"],
                    unit="cm/s",
                    is_over_range=False,
                    value_type="threshold",
                    source_doc=path.name,
                    source_page=src_page,
                    verification_status="verified",
                )
            )

        for param in ("co_initial_ppm", "co_final_ppm"):
            raw_co = _get_col(row, "measurements", param)
            co_val, is_or, val_type = parse_co_value(raw_co)
            if co_val is not None:
                meas_rows.append(
                    MeasurementModel(
                        psi_id=psi_id,
                        test_id=test_id,
                        parameter=param,
                        value=co_val,
                        unit="ppm",
                        is_over_range=is_or,
                        value_type=val_type,  # type: ignore[arg-type]
                        source_doc=path.name,
                        source_page=src_page,
                        verification_status="verified",
                    )
                )

        for param in ("co2_initial_pct", "co2_final_pct"):
            co2_val = parse_optional_float(_get_col(row, "measurements", param))
            if co2_val is not None:
                co2_status, _ = validate_co2_pct(co2_val)
                meas_rows.append(
                    MeasurementModel(
                        psi_id=psi_id,
                        test_id=test_id,
                        parameter=param,
                        value=co2_val,
                        unit="%",
                        is_over_range=False,
                        value_type="exact",
                        source_doc=path.name,
                        source_page=src_page,
                        verification_status=co2_status if cond_status == "verified" else cond_status,
                    )
                )

        if o2_init is not None:
            meas_rows.append(
                MeasurementModel(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="o2_initial_calibrated_pct",
                    value=o2_init,
                    unit="%",
                    is_over_range=False,
                    value_type="exact",
                    source_doc=path.name,
                    source_page=src_page,
                    verification_status=cond_status,
                )
            )

        if o2_final is not None:
            meas_rows.append(
                MeasurementModel(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="o2_final_calibrated_pct",
                    value=o2_final,
                    unit="%",
                    is_over_range=False,
                    value_type="exact",
                    source_doc=path.name,
                    source_page=src_page,
                    verification_status=cond_status,
                )
            )

        records_to_insert.append((experiment, sample, condition, meas_rows))

    conn = get_connection(db_path)
    total_measurements = 0
    try:
        with conn:
            for exp, sample, cond, meas_list in records_to_insert:
                conn.execute("DELETE FROM samples WHERE test_id = ?", (exp.test_id,))
                conn.execute("DELETE FROM conditions WHERE test_id = ?", (exp.test_id,))
                conn.execute("DELETE FROM measurements WHERE test_id = ?", (exp.test_id,))

                conn.execute(
                    """
                    INSERT OR REPLACE INTO experiments (
                        test_id, psi_id, pi_name, sample_id, is_reused_sample,
                        flow_direction, outcome, observations, raw_attributes_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exp.test_id,
                        exp.psi_id,
                        exp.pi_name,
                        exp.sample_id,
                        int(exp.is_reused_sample),
                        exp.flow_direction,
                        exp.outcome,
                        exp.observations,
                        exp.raw_attributes_json,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO samples (
                        test_id, material_name, geometry, thickness_mm, width_cm, diameter_mm
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sample.test_id,
                        sample.material_name,
                        sample.geometry,
                        sample.thickness_mm,
                        sample.width_cm,
                        sample.diameter_mm,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO conditions (
                        test_id, o2_initial_pct, o2_final_pct, pressure_psi,
                        diluent_gas, diluent_pct, flow_velocity_initial_cm_s,
                        flow_velocity_min_cm_s, flow_velocity_extinction_cm_s,
                        flow_sequence_raw, gravity_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cond.test_id,
                        cond.o2_initial_pct,
                        cond.o2_final_pct,
                        cond.pressure_psi,
                        cond.diluent_gas,
                        cond.diluent_pct,
                        cond.flow_velocity_initial_cm_s,
                        cond.flow_velocity_min_cm_s,
                        cond.flow_velocity_extinction_cm_s,
                        cond.flow_sequence_raw,
                        cond.gravity_level,
                    ),
                )

                for m in meas_list:
                    conn.execute(
                        """
                        INSERT INTO measurements (
                            psi_id, test_id, parameter, value, unit,
                            is_over_range, value_type, source_doc, source_page, verification_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            m.psi_id,
                            m.test_id,
                            m.parameter,
                            m.value,
                            m.unit,
                            int(m.is_over_range),
                            m.value_type,
                            m.source_doc,
                            m.source_page,
                            m.verification_status,
                        ),
                    )
                    total_measurements += 1
    finally:
        conn.close()

    register_file(path, sha256_hash, psi_id=psi_id, status="completed", db_path=db_path)

    return {
        "status": "completed",
        "file": path.name,
        "sha256": sha256_hash,
        "experiments_loaded": len(records_to_insert),
        "measurements_loaded": total_measurements,
        "unmapped_columns": plan.unmapped_columns,
        "validation_warnings": validation_warnings,
    }


def ingest_psi25_directory(
    raw_root: Path | str = RAW_DATA_DIR,
    db_path: Path | str = DB_PATH,
    force: bool = True,
) -> dict[str, Any]:
    """Ingest all PSI-25 (BASS-II) files (FAQ DOCX + Summary PDF Appendix A + Master CSV)."""
    files = discover_psi_files("PSI-25", raw_root=raw_root)
    csv_path = files.get("csv")
    pdf_path = files.get("pdf")
    docx_path = files.get("docx")

    if csv_path is None:
        raise FileNotFoundError(f"Master CSV for PSI-25 not found under {Path(raw_root) / 'PSI-25'}")

    faq_info = parse_bass2_faq(docx_path) if docx_path else {"pi_flow_defaults": {}}
    pdf_meta = parse_bass2_appendix_a(pdf_path) if pdf_path else {}

    if docx_path:
        register_file(docx_path, compute_sha256(docx_path), psi_id="PSI-25", status="completed", db_path=db_path)
    if pdf_path:
        register_file(pdf_path, compute_sha256(pdf_path), psi_id="PSI-25", status="completed", db_path=db_path)

    result = parse_and_store_csv(
        csv_path=csv_path,
        psi_id="PSI-25",
        pdf_meta=pdf_meta,
        faq_info=faq_info,
        db_path=db_path,
        force=force,
    )
    result["pdf_tests_enriched"] = len(pdf_meta)
    return result


if __name__ == "__main__":
    from database.seed_catalog import seed_database
    from database.repository import (
        get_all_investigations,
        get_experiments_df,
        get_measurements_df,
        get_ranked_experiments_df,
    )

    seed_database(db_path=DB_PATH)
    ingest_stats = ingest_psi25_directory(raw_root=RAW_DATA_DIR, db_path=DB_PATH, force=True)

    invs = get_all_investigations(db_path=DB_PATH)
    exp_df = get_experiments_df(db_path=DB_PATH)
    meas_df = get_measurements_df(db_path=DB_PATH)
    ranked_all = get_ranked_experiments_df(mission_profile="Lunar Base", db_path=DB_PATH)
    ranked_psi25 = ranked_all[ranked_all["psi_id"] == "PSI-25"].head(3)

    print("=== STAGE 2 INGESTION SUMMARY ===")
    print(f"Database path: {DB_PATH}")
    print(f"CSV file: {ingest_stats['file']} | SHA-256: {ingest_stats['sha256'][:16]}...")
    print(f"PSI-25 runs ingested: {ingest_stats['experiments_loaded']} (PDF Appendix A enriched: {ingest_stats['pdf_tests_enriched']})")
    print(f"Total experimental runs in research.db: {len(exp_df)} (PSI-25: {len(exp_df[exp_df['psi_id'] == 'PSI-25'])})")
    print(f"Total measurements in research.db: {len(meas_df)} (over-range CO flags: {int(meas_df['is_over_range'].sum())})")
    print(f"Validation warnings flagged: {len(ingest_stats['validation_warnings'])}")

    print("\n=== 5 FOUNDATIONAL INVESTIGATIONS & OFFICIAL DOIs ===")
    for item in invs:
        print(f"- [{item['psi_id']}] {item['acronym']} | DOI: https://doi.org/{item['doi']} | URL: {item['psi_url']}")

    print("\n=== TOP-3 TESTS FOR 'Lunar Base' (OVERALL) ===")
    for idx, row in ranked_all.head(3).iterrows():
        print(
            f"{idx + 1}. [{row['psi_id']}] {row['test_id']} | Score={row['research_relevance_score']} "
            f"(S_scen={row['s_scenario']}, S_comp={row['s_completeness']}, S_evid={row['s_evidence']}, S_cmpr={row['s_comparability']}) | "
            f"Mat={row['material_name']} | O2={row['o2_initial_pct']}% | P={row['pressure_psi']} psi | "
            f"Flow={row['flow_velocity_min_cm_s']} cm/s | Dir={row['flow_direction']} | Outcome={row['outcome']}"
        )

    print("\n=== TOP-3 PSI-25 (BASS-II) TESTS FOR 'Lunar Base' ===")
    for rank_i, (_, row) in enumerate(ranked_psi25.iterrows(), start=1):
        print(
            f"{rank_i}. [{row['psi_id']}] {row['test_id']} | Score={row['research_relevance_score']} "
            f"(S_scen={row['s_scenario']}, S_comp={row['s_completeness']}, S_evid={row['s_evidence']}, S_cmpr={row['s_comparability']}) | "
            f"Mat={row['material_name']} | O2={row['o2_initial_pct']}% | P={row['pressure_psi']} psi | "
            f"Flow={row['flow_velocity_min_cm_s']} cm/s | Dir={row['flow_direction']} | Outcome={row['outcome']}"
        )
