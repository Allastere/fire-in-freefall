"""Comprehensive NASA PSI multi-format (CSV, XLSX, PDF, DOCX) ingestion pipeline for all 19 investigations."""

import csv
import json
import math
import re
from pathlib import Path
from typing import Any
import openpyxl
import pandas as pd

from config.settings import DB_PATH, RAW_DATA_DIR, STANDARD_PRESSURE_PSI
from core.normalization import (
    normalize_length_to_cm,
    normalize_length_to_mm,
    normalize_mass_rate_to_g_s,
    normalize_mole_fraction_to_pct,
    normalize_pressure_to_psi,
    normalize_spread_rate_to_mm_s,
    normalize_temperature_to_k,
    normalize_time_to_s,
    normalize_velocity_to_cm_s,
    parse_air_display,
    parse_co_value,
    parse_fuel_sample_material,
    parse_gmt_duration_s,
    parse_interval_or_float,
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
from ingestion.file_loader import (
    compute_sha256,
    discover_psi_files,
    is_file_processed,
    register_file,
    resolve_psi_folder,
)
from ingestion.pdf_parser import extract_verified_pdf_measurements, parse_bass2_appendix_a
from ingestion.schema_mapper import LLMMapperCallback, map_csv_columns
from ingestion.text_parser import parse_bass2_faq


def _read_csv_with_fallback(path: Path) -> pd.DataFrame:
    """Read a NASA CSV file using encoding cascade (utf-8-sig -> cp1252 -> latin-1)."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1", errors="replace")


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


def _make_meas(
    psi_id: str,
    test_id: str | None,
    parameter: str,
    value: float,
    unit: str,
    source_doc: str,
    source_page: int | None = None,
    is_over_range: bool = False,
    value_type: str = "exact",
    verification_status: str = "verified",
    subtype: str | None = None,
    value_min: float | None = None,
    value_max: float | None = None,
    statistic_type: str = "EXACT_RUN",
    instrument: str | None = None,
    ignition_method: str | None = None,
    eligibility_status: str = "ML_ELIGIBLE",
    raw_col: str | None = None,
    raw_val: Any = None,
) -> MeasurementModel:
    trace = {
        "psi_id": psi_id,
        "test_id": test_id,
        "source_doc": source_doc,
        "source_page": source_page,
        "raw_column": raw_col,
        "raw_value": str(raw_val) if raw_val is not None else None,
        "subtype": subtype,
    }
    return MeasurementModel(
        psi_id=psi_id,
        test_id=test_id,
        parameter=parameter,
        value=round(float(value), 6),
        unit=unit,
        is_over_range=is_over_range,
        value_type=value_type,  # type: ignore[arg-type]
        source_doc=source_doc,
        source_page=source_page,
        verification_status=verification_status,  # type: ignore[arg-type]
        subtype=subtype,
        value_min=round(float(value_min), 6) if value_min is not None else None,
        value_max=round(float(value_max), 6) if value_max is not None else None,
        statistic_type=statistic_type,
        instrument=instrument,
        ignition_method=ignition_method,
        eligibility_status=eligibility_status,  # type: ignore[arg-type]
        source_trace_json=json.dumps(trace, ensure_ascii=False),
    )


def _persist_records(
    records: list[tuple[ExperimentModel, SampleModel, ConditionModel, list[MeasurementModel]]],
    db_path: Path | str = DB_PATH,
) -> int:
    """Persist a batch of (ExperimentModel, SampleModel, ConditionModel, list[MeasurementModel]) into SQLite."""
    if not records:
        return 0
    conn = get_connection(db_path)
    total_measurements = 0
    try:
        with conn:
            for exp, sample, cond, meas_list in records:
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
                        test_id, material_name, geometry, thickness_mm, width_cm, diameter_mm,
                        original_material_designation, material_family, fuel_phase, length_cm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sample.test_id,
                        sample.material_name,
                        sample.geometry,
                        sample.thickness_mm,
                        sample.width_cm,
                        sample.diameter_mm,
                        sample.original_material_designation,
                        sample.material_family,
                        sample.fuel_phase,
                        sample.length_cm,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO conditions (
                        test_id, o2_initial_pct, o2_final_pct, pressure_psi,
                        diluent_gas, diluent_pct, flow_velocity_initial_cm_s,
                        flow_velocity_min_cm_s, flow_velocity_extinction_cm_s,
                        flow_sequence_raw, gravity_level, oxygen_location,
                        co2_diluent_pct, he_diluent_pct, n2_diluent_pct, ambient_temp_k,
                        ignition_outcome, propagation_outcome, suppression_outcome, material_behaviour
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        cond.oxygen_location,
                        cond.co2_diluent_pct,
                        cond.he_diluent_pct,
                        cond.n2_diluent_pct,
                        cond.ambient_temp_k,
                        cond.ignition_outcome,
                        cond.propagation_outcome,
                        cond.suppression_outcome,
                        cond.material_behaviour,
                    ),
                )

                for m in meas_list:
                    conn.execute(
                        """
                        INSERT INTO measurements (
                            psi_id, test_id, parameter, value, unit,
                            is_over_range, value_type, source_doc, source_page, verification_status,
                            subtype, value_min, value_max, statistic_type,
                            instrument, ignition_method, eligibility_status, source_trace_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            m.subtype,
                            m.value_min,
                            m.value_max,
                            m.statistic_type,
                            m.instrument,
                            m.ignition_method,
                            m.eligibility_status,
                            m.source_trace_json,
                        ),
                    )
                    total_measurements += 1
    finally:
        conn.close()
    return total_measurements


def parse_and_store_csv(
    csv_path: Path | str,
    psi_id: str = "PSI-25",
    pdf_meta: dict[str, dict[str, Any]] | None = None,
    faq_info: dict[str, Any] | None = None,
    llm_callback: LLMMapperCallback | None = None,
    db_path: Path | str = DB_PATH,
    force: bool = False,
) -> dict[str, Any]:
    """Parse PSI-25 (BASS-II) experimental CSV table using 2-stage mapping + Pint and persist to SQLite."""
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

    df = _read_csv_with_fallback(path)
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

        raw_mat = _get_col(row, "samples", "material_name", "")
        mat_info = parse_fuel_sample_material(raw_mat, default_phase="Solid")

        raw_air = _get_col(row, "conditions", "flow_velocity_initial_cm_s")
        raw_fan = row.get("Fan display")
        air_info = parse_air_display(raw_air, raw_fan)
        air_unit = (lookup.get(("conditions", "flow_velocity_initial_cm_s")) or (None, "cm/s"))[1] or "cm/s"
        if air_unit != "cm/s":
            for k_vel in ("flow_velocity_initial_cm_s", "flow_velocity_min_cm_s", "flow_velocity_extinction_cm_s"):
                if air_info[k_vel] is not None:
                    air_info[k_vel] = normalize_velocity_to_cm_s(air_info[k_vel], air_unit)

        raw_pressure = parse_optional_float(_get_col(row, "conditions", "pressure_psi"))
        pressure_unit = (lookup.get(("conditions", "pressure_psi")) or (None, "psi"))[1] or "psi"
        pressure_psi = (
            normalize_pressure_to_psi(raw_pressure, pressure_unit)
            if raw_pressure is not None
            else STANDARD_PRESSURE_PSI
        )

        o2_init = parse_optional_float(_get_col(row, "conditions", "o2_initial_pct"))
        o2_final = parse_optional_float(_get_col(row, "conditions", "o2_final_pct"))
        co2_init = parse_optional_float(_get_col(row, "measurements", "co2_initial_pct"))
        co2_final = parse_optional_float(_get_col(row, "measurements", "co2_final_pct"))

        pdf_row = pdf_meta.get(test_id, {})
        observations = str(pdf_row.get("observations") or "").strip()
        if not observations and row.get("Total Frames Shot"):
            observations = (
                f"Total frames shot: {row.get('Total Frames Shot')}; "
                f"Radiometer gain: {row.get('Radiometer gain   (1000   250   50   10)', 'N/A')}"
            )

        flow_direction = _resolve_flow_direction(test_id, pi_name, pdf_meta, faq_defaults)
        outcome = _infer_outcome(air_info, observations, row.get("Total Frames Shot"))

        ign_outcome = "NO_IGNITION" if outcome == "No Ignition" else "SUCCESSFUL_IGNITION"
        prop_outcome = "SUSTAINED_SPREAD" if outcome == "Sustained" else ("ARRESTED_PROPAGATION" if outcome in {"Quenched", "Blowoff"} else "NO_SPREAD")
        supp_outcome = (
            "BLOWOFF_HIGH_FLOW"
            if outcome == "Blowoff"
            else ("QUENCHED_LOW_FLOW" if outcome == "Quenched" else "SUSTAINED_BURNING")
        )
        obs_lower = observations.lower()
        mat_behav = "SOOTING" if "soot" in obs_lower else ("CHARRING" if "char" in obs_lower else ("MELTING" if "melt" in obs_lower else "NONE"))

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
            oxygen_location="CHAMBER_AMBIENT",
            co2_diluent_pct=co2_init,
            n2_diluent_pct=round(100.0 - o2_init - (co2_init or 0.0), 2) if o2_init is not None else None,
            ignition_outcome=ign_outcome,
            propagation_outcome=prop_outcome,
            suppression_outcome=supp_outcome,
            material_behaviour=mat_behav,
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
            original_material_designation=mat_info["original_material_designation"],
            material_family=mat_info["material_family"],
            fuel_phase=mat_info["fuel_phase"],
        )

        meas_rows: list[MeasurementModel] = []
        src_page = pdf_row.get("source_page")

        if air_info["flow_velocity_extinction_cm_s"] is not None:
            meas_rows.append(
                _make_meas(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="extinction_velocity_cm_s",
                    value=air_info["flow_velocity_extinction_cm_s"],
                    unit="cm/s",
                    source_doc=path.name,
                    source_page=src_page,
                    value_type="threshold",
                    subtype=air_info.get("extinction_subtype") or "LOW_FLOW_EXTINCTION",
                    instrument="Anemometer/Fan Display",
                    ignition_method="piloted",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Air display",
                    raw_val=raw_air,
                )
            )

        for param in ("co_initial_ppm", "co_final_ppm"):
            raw_co = _get_col(row, "measurements", param)
            co_val, is_or, val_type = parse_co_value(raw_co)
            if co_val is not None:
                meas_rows.append(
                    _make_meas(
                        psi_id=psi_id,
                        test_id=test_id,
                        parameter=param,
                        value=co_val,
                        unit="ppm",
                        source_doc=path.name,
                        source_page=src_page,
                        is_over_range=is_or,
                        value_type=val_type,
                        subtype="OVER_RANGE_SATURATED" if is_or else "CALIBRATED_CSA_CP",
                        instrument="CSA-CP",
                        eligibility_status="EVIDENCE_ONLY" if is_or else "ML_ELIGIBLE",
                        raw_col=param,
                        raw_val=raw_co,
                    )
                )

        for param, co2_val in (("co2_initial_pct", co2_init), ("co2_final_pct", co2_final)):
            if co2_val is not None:
                co2_status, _ = validate_co2_pct(co2_val)
                v_stat = co2_status if cond_status == "verified" else cond_status
                meas_rows.append(
                    _make_meas(
                        psi_id=psi_id,
                        test_id=test_id,
                        parameter=param,
                        value=co2_val,
                        unit="%",
                        source_doc=path.name,
                        source_page=src_page,
                        verification_status=v_stat,
                        subtype="CHAMBER_AMBIENT_CO2" if param == "co2_initial_pct" else "POST_BURN_CO2",
                        instrument="Crowcon CO2 Analyzer",
                        eligibility_status="ML_ELIGIBLE" if v_stat == "verified" else "NEEDS_REVIEW",
                        raw_col=param,
                        raw_val=co2_val,
                    )
                )

        if o2_init is not None:
            meas_rows.append(
                _make_meas(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="o2_initial_calibrated_pct",
                    value=o2_init,
                    unit="%",
                    source_doc=path.name,
                    source_page=src_page,
                    verification_status=cond_status,
                    subtype="CALIBRATED_INITIAL_O2",
                    instrument="CSA-CP",
                    eligibility_status="ML_ELIGIBLE" if cond_status == "verified" else "NEEDS_REVIEW",
                )
            )
            if outcome == "No Ignition":
                meas_rows.append(
                    _make_meas(
                        psi_id=psi_id,
                        test_id=test_id,
                        parameter="oxygen_limit_pct",
                        value=o2_init,
                        unit="%",
                        source_doc=path.name,
                        source_page=src_page,
                        value_type="upper_bound",
                        value_max=o2_init,
                        subtype="NO_IGNITION_O2_BOUND",
                        instrument="CSA-CP",
                        ignition_method="piloted",
                        eligibility_status="EVIDENCE_ONLY",
                    )
                )

        if o2_final is not None:
            meas_rows.append(
                _make_meas(
                    psi_id=psi_id,
                    test_id=test_id,
                    parameter="o2_final_calibrated_pct",
                    value=o2_final,
                    unit="%",
                    source_doc=path.name,
                    source_page=src_page,
                    verification_status=cond_status,
                    subtype="CALIBRATED_FINAL_O2",
                    instrument="CSA-CP",
                    eligibility_status="ML_ELIGIBLE" if cond_status == "verified" else "NEEDS_REVIEW",
                )
            )

        records_to_insert.append((experiment, sample, condition, meas_rows))

    total_measurements = _persist_records(records_to_insert, db_path=db_path)
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
        raise FileNotFoundError(f"Master CSV for PSI-25 not found under {Path(raw_root)}")

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


# =============================================================================
# SPECIALIZED HIGH-PRECISION INGESTERS FOR REMAINING 18 INVESTIGATIONS
# =============================================================================


def _ingest_psi26_bass(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-26 (BASS): 122 CSV runs enriched with BASS Test Matrix 050213.xlsx planned ignition intervals."""
    folder = resolve_psi_folder("PSI-26", raw_root)
    if not folder:
        return 0, 0
    csv_path = folder / "PSI-26_Experimental table_BASS.csv"
    xlsx_path = folder / "BASS Test Matrix 050213.xlsx"

    # Parse planned ignition intervals from BASS Test Matrix 050213.xlsx keyed by Test Point
    matrix_by_tp: dict[str, dict[str, Any]] = {}
    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        ws = wb["BASS Test Matrix"]
        last_fuel = ""
        last_igniter = ""
        for idx, r in enumerate(ws.iter_rows(values_only=True)):
            if idx < 6:
                continue
            tp = str(r[2] or "").strip()
            fuel_desc = str(r[3] or "").strip() or last_fuel
            ign_type = str(r[4] or "").strip() or last_igniter
            ign_time_raw = str(r[5] or "").strip()
            ext_flag = str(r[6] or "").strip()
            gn2_pot = str(r[9] or "").strip()
            if fuel_desc:
                last_fuel = fuel_desc
            if ign_type:
                last_igniter = ign_type
            if tp and tp.isdigit():
                matrix_by_tp[tp] = {
                    "fuel_desc": fuel_desc,
                    "ign_type": ign_type,
                    "ign_time_raw": ign_time_raw,
                    "ext_flag": ext_flag,
                    "gn2_pot": gn2_pot,
                }
        register_file(xlsx_path, compute_sha256(xlsx_path), psi_id="PSI-26", db_path=db_path)

    df = _read_csv_with_fallback(csv_path)
    records = []
    for row in df.to_dict(orient="records"):
        raw_clean = _clean_raw_row(row)
        as_run = str(row.get("As Run Test #", "")).strip()
        tp = str(row.get("Test #", "")).strip()
        if not as_run:
            continue
        test_id = f"BASS-{as_run.zfill(3)}"
        sample_id = str(row.get("Sample #", "")).strip()
        raw_mat = str(row.get("Fuel Sample Material", "")).strip()
        mat_info = parse_fuel_sample_material(raw_mat, default_phase="Solid")

        m_info = matrix_by_tp.get(tp, {})
        ign_type = m_info.get("ign_type", "")
        flow_dir: FlowDirection = (
            "Opposed" if "FORWARD" in ign_type.upper() else ("Concurrent" if "WAKE" in ign_type.upper() else "Unknown")
        )
        outcome: ExperimentOutcome = "Quenched" if m_info.get("ext_flag") == "Y" else "Sustained"
        obs = f"Test Point #{tp}; Material: {raw_mat}"
        if ign_type:
            obs += f"; Igniter: {ign_type.replace(chr(10), ' ')}"

        exp = ExperimentModel(
            test_id=test_id,
            psi_id="PSI-26",
            pi_name="Ferkul / T'ien / Olson",
            sample_id=sample_id,
            is_reused_sample=False,
            flow_direction=flow_dir,
            outcome=outcome,
            observations=obs,
            raw_attributes_json=raw_clean,
        )
        samp = SampleModel(
            test_id=test_id,
            material_name=mat_info["material_name"],
            geometry=mat_info["geometry"],
            thickness_mm=mat_info["thickness_mm"],
            width_cm=mat_info["width_cm"],
            diameter_mm=mat_info["diameter_mm"],
            original_material_designation=mat_info["original_material_designation"],
            material_family=mat_info["material_family"],
            fuel_phase="Solid",
        )
        cond = ConditionModel(
            test_id=test_id,
            o2_initial_pct=21.0,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=79.0,
            gravity_level="0g",
            oxygen_location="CHAMBER_AMBIENT",
            ignition_outcome="SUCCESSFUL_IGNITION",
            propagation_outcome="SUSTAINED_SPREAD",
            suppression_outcome="QUENCHED_LOW_FLOW" if outcome == "Quenched" else "SUSTAINED_BURNING",
        )
        meas_list: list[MeasurementModel] = []
        ign_interval = parse_interval_or_float(m_info.get("ign_time_raw"), unit="s", target_unit="s")
        if ign_interval is not None:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-26",
                    test_id=test_id,
                    parameter="ignition_time_s",
                    value=ign_interval["value"],
                    unit="s",
                    source_doc="BASS Test Matrix 050213.xlsx",
                    value_type=ign_interval["value_type"],
                    value_min=ign_interval["value_min"],
                    value_max=ign_interval["value_max"],
                    subtype="PLANNED_MATRIX_IGNITION_INTERVAL",
                    statistic_type="RANGE_MIDPOINT" if ign_interval["value_type"] == "interval" else "EXACT_RUN",
                    instrument="Hot-Wire Igniter",
                    ignition_method="piloted",
                    eligibility_status="EVIDENCE_ONLY",
                    raw_col="Ignition time - seconds",
                    raw_val=m_info.get("ign_time_raw"),
                )
            )
        records.append((exp, samp, cond, meas_list))

    n_meas = _persist_records(records, db_path=db_path)
    register_file(csv_path, compute_sha256(csv_path), psi_id="PSI-26", db_path=db_path)
    return len(records), n_meas


def _ingest_psi39_cfi(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-39 (CFI): Merge CFI.csv (87 rows) and CFI_DataSummary_Spreadsheet_Jan2021.xlsx (227 droplet runs)."""
    folder = resolve_psi_folder("PSI-39", raw_root)
    if not folder:
        return 0, 0
    csv_path = folder / "PSI-39_Experimental table_CFI.csv"
    xlsx_path = folder / "CFI_DataSummary_Spreadsheet_Jan2021.xlsx"

    master_by_flex: dict[str, dict[str, Any]] = {}
    if csv_path.exists():
        df_csv = _read_csv_with_fallback(csv_path)
        for r in df_csv.to_dict(orient="records"):
            fn = str(r.get("Flex Number", "")).strip()
            if fn:
                master_by_flex[fn] = dict(r)
        register_file(csv_path, compute_sha256(csv_path), psi_id="PSI-39", db_path=db_path)

    data_by_flex: dict[str, dict[str, Any]] = {}
    ign_by_flex: dict[str, dict[str, Any]] = {}
    comm_by_flex: dict[str, str] = {}

    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        if "Master Sheet" in wb.sheetnames:
            ws = wb["Master Sheet"]
            rows = list(ws.iter_rows(values_only=True))
            hdrs = [str(h or "").strip() for h in rows[0]]
            for r in rows[1:]:
                if not r or r[0] is None:
                    continue
                fn = str(r[0]).strip().removesuffix(".0")
                if fn:
                    d = {hdrs[i]: r[i] for i in range(min(len(hdrs), len(r))) if hdrs[i]}
                    master_by_flex.setdefault(fn, {}).update(d)
        if "DATA" in wb.sheetnames:
            ws = wb["DATA"]
            rows = list(ws.iter_rows(values_only=True))
            hdrs = [str(h or "").strip() for h in rows[0]]
            for r in rows[1:]:
                if not r or r[0] is None:
                    continue
                fn = str(r[0]).strip().removesuffix(".0")
                if fn:
                    data_by_flex[fn] = {hdrs[i]: r[i] for i in range(min(len(hdrs), len(r))) if hdrs[i]}
        if "Igniter" in wb.sheetnames:
            ws = wb["Igniter"]
            rows = list(ws.iter_rows(values_only=True))
            hdrs = [str(h or "").strip() for h in rows[0]]
            for r in rows[1:]:
                if not r or r[0] is None:
                    continue
                fn = str(r[0]).strip().removesuffix(".0")
                if fn:
                    ign_by_flex[fn] = {hdrs[i]: r[i] for i in range(min(len(hdrs), len(r))) if hdrs[i]}
        if "Comments" in wb.sheetnames:
            ws = wb["Comments"]
            rows = list(ws.iter_rows(values_only=True))
            for r in rows[1:]:
                if not r or r[0] is None:
                    continue
                fn = str(r[0]).strip().removesuffix(".0")
                if fn and len(r) > 1 and r[1] is not None:
                    comm_by_flex[fn] = str(r[1]).strip()
        register_file(xlsx_path, compute_sha256(xlsx_path), psi_id="PSI-39", db_path=db_path)

    all_flex_nums = sorted(set(master_by_flex.keys()) | set(data_by_flex.keys()))
    records = []
    for fn in all_flex_nums:
        m_row = master_by_flex.get(fn, {})
        d_row = data_by_flex.get(fn, {})
        i_row = ign_by_flex.get(fn, {})
        comment = comm_by_flex.get(fn, "")

        # Skip unpopulated placeholder rows in Master Sheet that have no fuel, pressure, or data
        fuel_raw = str(m_row.get("Fuel") or m_row.get("Fuel ") or "").strip()
        if not fuel_raw and not d_row:
            continue

        test_id = f"CFI-{fn}"
        mat_info = parse_fuel_sample_material(fuel_raw or "C12H26", default_phase="Liquid")
        d0_mm = parse_optional_float(d_row.get("D0 ( mm )"))

        p_raw = d_row.get("Pressure (atm)") or m_row.get("Pressure")
        p_atm = parse_optional_float(p_raw)
        pressure_psi = normalize_pressure_to_psi(p_atm, "atm") if p_atm is not None else 14.7

        o2_mf = parse_optional_float(m_row.get("Oxygen"))
        n2_mf = parse_optional_float(m_row.get("Nitrogen"))
        he_mf = parse_optional_float(m_row.get("Helium"))
        o2_pct = normalize_mole_fraction_to_pct(o2_mf, True) if o2_mf is not None else 21.0
        n2_pct = normalize_mole_fraction_to_pct(n2_mf, True) if n2_mf is not None else None
        he_pct = normalize_mole_fraction_to_pct(he_mf, True) if he_mf is not None else None

        reign_count = parse_optional_float(d_row.get("Reignitions"))
        hf_burn_s = parse_optional_float(d_row.get("HF Burn Time"))
        outcome: ExperimentOutcome = "Quenched" if d_row.get("Dext, hot ( mm )") not in (None, "") else "Sustained"

        combined_raw = _clean_raw_row({**m_row, **d_row, **i_row, "Comments": comment})
        exp = ExperimentModel(
            test_id=test_id,
            psi_id="PSI-39",
            pi_name="Dietrich / Nayagam / Williams",
            sample_id=str(m_row.get("CIR") or m_row.get("CIR ") or fn).strip(),
            is_reused_sample=False,
            flow_direction="Quiescent",
            outcome=outcome,
            observations=comment or f"CFI Droplet Flex #{fn} ({mat_info['material_name']})",
            raw_attributes_json=combined_raw,
        )
        samp = SampleModel(
            test_id=test_id,
            material_name=mat_info["material_name"],
            geometry="Droplet",
            diameter_mm=d0_mm,
            original_material_designation=fuel_raw or "C12H26",
            material_family=mat_info["material_family"],
            fuel_phase="Liquid",
        )
        cond = ConditionModel(
            test_id=test_id,
            o2_initial_pct=o2_pct,
            pressure_psi=pressure_psi,
            diluent_gas="N2/He" if (he_pct and he_pct > 0) else "N2",
            diluent_pct=round((n2_pct or 0.0) + (he_pct or 0.0), 2) if (n2_pct is not None or he_pct is not None) else None,
            flow_velocity_initial_cm_s=0.0,
            flow_velocity_min_cm_s=0.0,
            flow_sequence_raw="Quiescent CIR/MDCA",
            gravity_level="0g",
            oxygen_location="CHAMBER_AMBIENT",
            he_diluent_pct=he_pct,
            n2_diluent_pct=n2_pct,
            ignition_outcome="REIGNITION" if (reign_count and reign_count > 0) else ("SUCCESSFUL_IGNITION" if hf_burn_s else "UNKNOWN"),
            propagation_outcome="DROPLET_REGRESSION",
            suppression_outcome="RADIATIVE_EXTINCTION_TO_COOL_FLAME" if d_row.get("kcool ( mm^2/s )") else "SELF_EXTINGUISHED",
        )

        meas_list: list[MeasurementModel] = []
        src_doc = "CFI_DataSummary_Spreadsheet_Jan2021.xlsx"

        if hf_burn_s is not None and hf_burn_s > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="burning_duration_s",
                    value=hf_burn_s,
                    unit="s",
                    source_doc=src_doc,
                    subtype="HOT_FLAME_DURATION",
                    instrument="High-Speed Camera / Radiometer",
                    ignition_method="piloted",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="HF Burn Time",
                    raw_val=hf_burn_s,
                )
            )
        for col_k, sub_k in (("khot ( mm^2/s )", "HOT_FLAME"), ("kcool ( mm^2/s )", "COOL_FLAME")):
            kv = parse_optional_float(d_row.get(col_k))
            if kv is not None and kv > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-39",
                        test_id=test_id,
                        parameter="burning_rate_constant_mm2_s",
                        value=kv,
                        unit="mm2/s",
                        source_doc=src_doc,
                        subtype=sub_k,
                        instrument="Backlit Droplet Camera",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col=col_k,
                        raw_val=kv,
                    )
                )
        for col_d, sub_d in (("Dext, hot ( mm )", "HOT_FLAME_EXTINCTION"), ("Dext,cool ( mm )", "COOL_FLAME_EXTINCTION")):
            dv = parse_optional_float(d_row.get(col_d))
            if dv is not None and dv > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-39",
                        test_id=test_id,
                        parameter="extinction_droplet_diameter_mm",
                        value=dv,
                        unit="mm",
                        source_doc=src_doc,
                        subtype=sub_d,
                        instrument="Backlit Droplet Camera",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col=col_d,
                        raw_val=dv,
                    )
                )
        peak_rad = parse_optional_float(d_row.get("Peak HF Rad"))
        if peak_rad is not None:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="radiative_output",
                    value=peak_rad,
                    unit="raw",
                    source_doc=src_doc,
                    subtype="PEAK_HOT_FLAME_RADIOMETER",
                    statistic_type="PEAK",
                    instrument="Wide-Band Radiometer",
                    eligibility_status="EVIDENCE_ONLY",
                    raw_col="Peak HF Rad",
                    raw_val=peak_rad,
                )
            )
        ign_p_w = parse_optional_float(i_row.get("Ignition Power ( W )"))
        if ign_p_w is not None:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="ignition_power_watts",
                    value=ign_p_w,
                    unit="W",
                    source_doc=src_doc,
                    subtype="HOT_WIRE_IGNITER_POWER",
                    instrument="Hot-Wire Igniter",
                    eligibility_status="EVIDENCE_ONLY",
                    raw_col="Ignition Power ( W )",
                    raw_val=i_row.get("Ignition Power ( W )"),
                )
            )
        ign_t_ms = parse_optional_float(i_row.get("Ignition Time ( ms )"))
        if ign_t_ms is not None and ign_t_ms > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="igniter_operation_duration_s",
                    value=normalize_time_to_s(ign_t_ms, "ms"),
                    unit="s",
                    source_doc=src_doc,
                    subtype="IGNITER_ENERGIZATION_DURATION",
                    instrument="Hot-Wire Igniter",
                    ignition_method="piloted",
                    eligibility_status="EVIDENCE_ONLY",
                    raw_col="Ignition Time ( ms )",
                    raw_val=i_row.get("Ignition Time ( ms )"),
                )
            )
        if he_pct is not None and he_pct > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="suppressant_concentration_pct",
                    value=he_pct,
                    unit="%",
                    source_doc=src_doc,
                    subtype="HE_DILUENT_MOLE_PCT",
                    instrument="Gas Mixing Manifold",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Helium",
                    raw_val=he_mf,
                )
            )
        if n2_pct is not None and n2_pct > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-39",
                    test_id=test_id,
                    parameter="suppressant_concentration_pct",
                    value=n2_pct,
                    unit="%",
                    source_doc=src_doc,
                    subtype="N2_DILUENT_MOLE_PCT",
                    instrument="Gas Mixing Manifold",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Nitrogen",
                    raw_val=n2_mf,
                )
            )
        records.append((exp, samp, cond, meas_list))

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _ingest_psi69_flex(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-69 (FLEX): 274 isolated droplet combustion & CO2/He/N2 suppression runs."""
    folder = resolve_psi_folder("PSI-69", raw_root)
    if not folder:
        return 0, 0
    csv_path = folder / "PSI-69_Experimental table_FLEX.csv"
    df = _read_csv_with_fallback(csv_path)
    records = []
    for row in df.to_dict(orient="records"):
        raw_clean = _clean_raw_row(row)
        t_num = str(row.get("FLEX Test #", "")).strip()
        if not t_num:
            continue
        test_id = f"FLEX-{t_num.zfill(3)}"
        flex_ident = str(row.get("FLEX Identifier", "")).strip()
        fuel_raw = str(row.get("Fuel", "")).strip()
        mat_info = parse_fuel_sample_material(fuel_raw, default_phase="Liquid")

        p_mmhg = parse_optional_float(row.get("Ambient pressure; mmHg"))
        pressure_psi = normalize_pressure_to_psi(p_mmhg, "mmHg") if p_mmhg is not None else 14.7

        o2_mf = parse_optional_float(row.get("O initial ambient composition; mole fraction"))
        n2_mf = parse_optional_float(row.get("N initial ambient composition; mole fraction"))
        co2_mf = parse_optional_float(row.get("CO initial ambient composition; mole fraction"))
        he_mf = parse_optional_float(row.get("He initial ambient composition; mole fraction"))

        o2_pct = normalize_mole_fraction_to_pct(o2_mf, True) if o2_mf is not None else None
        n2_pct = normalize_mole_fraction_to_pct(n2_mf, True) if n2_mf is not None else None
        co2_pct = normalize_mole_fraction_to_pct(co2_mf, True) if co2_mf is not None else None
        he_pct = normalize_mole_fraction_to_pct(he_mf, True) if he_mf is not None else None

        d0_mm = parse_optional_float(row.get("Droplet initial diameter; mm"))
        d_ext_mm = parse_optional_float(row.get("Visible flame extinction diameter; mm"))
        k_burn = parse_optional_float(row.get("Burning rate; mm"))
        burn_s = parse_optional_float(row.get("Burn time; s"))
        test_end = str(row.get("Test end", "")).strip()

        outcome: ExperimentOutcome = (
            "Quenched"
            if test_end.lower() == "extinction"
            else ("Sustained" if test_end.lower() == "completion" else "Unknown")
        )
        diluents = []
        if co2_pct and co2_pct > 0:
            diluents.append("CO2")
        if he_pct and he_pct > 0:
            diluents.append("He")
        if n2_pct and n2_pct > 0:
            diluents.append("N2")
        dil_gas = "/".join(diluents) if diluents else "N2"
        dil_total = round((n2_pct or 0.0) + (co2_pct or 0.0) + (he_pct or 0.0), 2)

        exp = ExperimentModel(
            test_id=test_id,
            psi_id="PSI-69",
            pi_name="Dietrich / Williams / Nayagam",
            sample_id=flex_ident or t_num,
            is_reused_sample=False,
            flow_direction="Quiescent",
            outcome=outcome,
            observations=f"FLEX #{t_num} ({flex_ident}): {fuel_raw}, Test end={test_end}",
            raw_attributes_json=raw_clean,
        )
        samp = SampleModel(
            test_id=test_id,
            material_name=mat_info["material_name"],
            geometry="Droplet",
            diameter_mm=d0_mm,
            original_material_designation=fuel_raw,
            material_family=mat_info["material_family"],
            fuel_phase="Liquid",
        )
        cond = ConditionModel(
            test_id=test_id,
            o2_initial_pct=o2_pct,
            pressure_psi=pressure_psi,
            diluent_gas=dil_gas,
            diluent_pct=dil_total if dil_total <= 100.0 else None,
            flow_velocity_initial_cm_s=0.0,
            flow_velocity_min_cm_s=0.0,
            flow_sequence_raw="Quiescent CIR/MDCA",
            gravity_level="0g",
            oxygen_location="CHAMBER_AMBIENT",
            co2_diluent_pct=co2_pct,
            he_diluent_pct=he_pct,
            n2_diluent_pct=n2_pct,
            ignition_outcome="SUCCESSFUL_IGNITION" if (burn_s and burn_s > 0) else "UNKNOWN",
            propagation_outcome="DROPLET_REGRESSION",
            suppression_outcome=(
                "SELF_EXTINGUISHED"
                if test_end.lower() == "extinction"
                else ("COMPLETE_CONSUMPTION" if test_end.lower() == "completion" else "UNKNOWN")
            ),
        )

        meas_list: list[MeasurementModel] = []
        if burn_s is not None and burn_s > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-69",
                    test_id=test_id,
                    parameter="burning_duration_s",
                    value=burn_s,
                    unit="s",
                    source_doc=csv_path.name,
                    subtype=f"DROPLET_BURN_TIME_{test_end.upper() or 'UNKNOWN'}",
                    instrument="High-Speed Backlit Camera",
                    ignition_method="piloted",
                    eligibility_status="ML_ELIGIBLE" if test_end.lower() in {"extinction", "completion"} else "EVIDENCE_ONLY",
                    raw_col="Burn time; s",
                    raw_val=burn_s,
                )
            )
            if test_end.lower() == "extinction":
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-69",
                        test_id=test_id,
                        parameter="extinguishing_time_s",
                        value=burn_s,
                        unit="s",
                        source_doc=csv_path.name,
                        subtype="RADIATIVE_DIFFUSIVE_DROPLET_EXTINCTION_TIME",
                        instrument="High-Speed Backlit Camera",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Burn time; s",
                        raw_val=burn_s,
                    )
                )
        if k_burn is not None and k_burn > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-69",
                    test_id=test_id,
                    parameter="burning_rate_constant_mm2_s",
                    value=k_burn,
                    unit="mm2/s",
                    source_doc=csv_path.name,
                    subtype="OVERALL_DROPLET",
                    instrument="High-Speed Backlit Camera",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Burning rate; mm",
                    raw_val=k_burn,
                )
            )
        if d_ext_mm is not None and d_ext_mm > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-69",
                    test_id=test_id,
                    parameter="extinction_droplet_diameter_mm",
                    value=d_ext_mm,
                    unit="mm",
                    source_doc=csv_path.name,
                    subtype="VISIBLE_FLAME_EXTINCTION_DIAMETER",
                    instrument="High-Speed Backlit Camera",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Visible flame extinction diameter; mm",
                    raw_val=d_ext_mm,
                )
            )
        for gas_code, gas_val, raw_c in (
            ("CO2_DILUENT_MOLE_PCT", co2_pct, "CO initial ambient composition; mole fraction"),
            ("HE_DILUENT_MOLE_PCT", he_pct, "He initial ambient composition; mole fraction"),
            ("N2_DILUENT_MOLE_PCT", n2_pct, "N initial ambient composition; mole fraction"),
        ):
            if gas_val is not None and gas_val > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-69",
                        test_id=test_id,
                        parameter="suppressant_concentration_pct",
                        value=gas_val,
                        unit="%",
                        source_doc=csv_path.name,
                        subtype=gas_code,
                        instrument="Gas Mixing Manifold",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col=raw_c,
                        raw_val=gas_val,
                    )
                )
        records.append((exp, samp, cond, meas_list))

    n_meas = _persist_records(records, db_path=db_path)
    register_file(csv_path, compute_sha256(csv_path), psi_id="PSI-69", db_path=db_path)
    return len(records), n_meas


def _ingest_saffire_98_99_100(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-98 (SAFFIRE-I), PSI-99 (SAFFIRE-II), and PSI-100 (SAFFIRE-III)."""
    records = []

    # 1. PSI-98 (SAFFIRE-I)
    f98 = resolve_psi_folder("PSI-98", raw_root)
    if f98:
        p98 = f98 / "PSI-98_Experimental table_SAFFIRE-1.csv"
        df98 = _read_csv_with_fallback(p98)
        for row in df98.to_dict(orient="records"):
            s_num = str(row.get("Sample Number ", "") or row.get("Sample Number", "")).strip()
            if s_num not in {"S1", "S2"}:
                continue
            test_id = f"SAFF1-{s_num}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Material", "SIBAL Fabric")).strip()
            mat_info = parse_fuel_sample_material(mat_raw, default_phase="Solid")
            thick_cm = parse_optional_float(row.get("Sample Thickness (cm)"))
            len_cm = parse_optional_float(row.get("Sample Length (cm)"))
            wid_cm = parse_optional_float(row.get("Sample Width (cm)"))
            v_air = parse_optional_float(row.get("Air Flow (cm/s)"))
            o2_parsed = parse_interval_or_float(row.get("Percent O2"), unit="%", target_unit="%")
            o2_val = o2_parsed["value"] if o2_parsed else 21.5
            ign_p = parse_optional_float(row.get("Ignition Power (W)"))
            ign_t = parse_optional_float(row.get("Ignition Time (s)"))
            burn_t = parse_optional_float(row.get("Burn Time (s)"))
            f_dir = str(row.get("Flow Direction ", "") or row.get("Flow Direction", "")).strip()

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-98",
                pi_name="Urban DL",
                sample_id=s_num,
                is_reused_sample=False,
                flow_direction=f_dir if f_dir in {"Concurrent", "Opposed"} else "Unknown",  # type: ignore[arg-type]
                outcome="Sustained",
                observations=f"SAFFIRE-I large-scale {f_dir} SIBAL panel burn ({len_cm}x{wid_cm} cm) aboard Cygnus OA-6",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Fabric",
                thickness_mm=normalize_length_to_mm(thick_cm, "cm") if thick_cm else None,
                width_cm=wid_cm,
                length_cm=len_cm,
                original_material_designation=mat_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Solid",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=o2_val,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=round(100.0 - o2_val, 2),
                flow_velocity_initial_cm_s=v_air,
                flow_velocity_min_cm_s=v_air,
                flow_sequence_raw=f"{v_air} cm/s",
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ignition_outcome="SUCCESSFUL_IGNITION",
                propagation_outcome="SUSTAINED_SPREAD",
                suppression_outcome="SELF_EXTINGUISHED",
            )
            meas_list = []
            if burn_t is not None:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-98",
                        test_id=test_id,
                        parameter="burning_duration_s",
                        value=burn_t,
                        unit="s",
                        source_doc=p98.name,
                        subtype="LARGE_SCALE_PANEL_BURN_DURATION",
                        instrument="Video Camera / Thermocouples",
                        ignition_method="piloted",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Burn Time (s)",
                        raw_val=burn_t,
                    )
                )
            if ign_p is not None:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-98",
                        test_id=test_id,
                        parameter="ignition_power_watts",
                        value=ign_p,
                        unit="W",
                        source_doc=p98.name,
                        subtype="HOT_WIRE_IGNITER_POWER",
                        instrument="Hot-Wire Igniter",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Ignition Power (W)",
                        raw_val=ign_p,
                    )
                )
            if ign_t is not None:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-98",
                        test_id=test_id,
                        parameter="igniter_operation_duration_s",
                        value=ign_t,
                        unit="s",
                        source_doc=p98.name,
                        subtype="IGNITER_ENERGIZATION_DURATION",
                        instrument="Hot-Wire Igniter",
                        ignition_method="piloted",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Ignition Time (s)",
                        raw_val=ign_t,
                    )
                )
            records.append((exp, samp, cond, meas_list))
        register_file(p98, compute_sha256(p98), psi_id="PSI-98", db_path=db_path)

    # 2. PSI-99 (SAFFIRE-II)
    f99 = resolve_psi_folder("PSI-99", raw_root)
    if f99:
        p99 = f99 / "PSI-99_Experimental table_SAFFIRE-2.csv"
        df99 = _read_csv_with_fallback(p99)
        last_mat = "Silicone"
        for row in df99.to_dict(orient="records"):
            s_num = str(row.get("Sample Number", "")).strip()
            if not re.match(r"^2-\d+$", s_num):
                continue
            test_id = f"SAFF2-{s_num}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Material", "")).strip() or last_mat
            last_mat = mat_raw
            mat_info = parse_fuel_sample_material(mat_raw, default_phase="Solid")

            thick_str = str(row.get("Samle Thickness ", "")).strip()
            thick_mm = None
            if "037 mm" in thick_str:
                thick_mm = 0.37
            elif "1 cm" in thick_str:
                thick_mm = 10.0
            else:
                thick_mm = parse_optional_float(thick_str.split("and")[0])

            len_cm = parse_optional_float(str(row.get("Sample Length ", "")).split("and")[0])
            wid_cm = parse_optional_float(row.get("Sample Width (cm)"))
            v_air = parse_optional_float(row.get("Air Flow (cm/s)"))
            o2_parsed = parse_interval_or_float(row.get("Percent O2 (Note 1)"), unit="%", target_unit="%")
            o2_val = o2_parsed["value"] if o2_parsed else 22.0

            ign_p = parse_optional_float(row.get("Ignition Power (W)"))
            ign_t = parse_optional_float(row.get("Ignition Time (s)"))
            burn_raw = str(row.get("Burn Time (s)", "")).strip()
            burn_t = parse_optional_float(burn_raw)
            f_dir = str(row.get("Flow Direction", "")).strip()

            # Check microgravity spread rate column (named '?-g Spread Length' / 'µ-g Spread Length')
            ug_spread_col = [k for k in row.keys() if "Spread Length" in k]
            ug_spread_raw = str(row.get(ug_spread_col[0], "")).strip() if ug_spread_col else ""
            g1_spread_raw = str(row.get("1-g Spread Rate", "")).strip()

            outcome: ExperimentOutcome = "Quenched" if "insignificant" in burn_raw.lower() else "Sustained"
            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-99",
                pi_name="Urban DL / Ruff GA",
                sample_id=s_num,
                is_reused_sample=False,
                flow_direction=f_dir if f_dir in {"Concurrent", "Opposed"} else "Unknown",  # type: ignore[arg-type]
                outcome=outcome,
                observations=f"SAFFIRE-II Sample {s_num} ({mat_raw}): 0g burn={burn_raw}, 1g spread={g1_spread_raw}",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry=mat_info["geometry"],
                thickness_mm=thick_mm,
                width_cm=wid_cm,
                length_cm=len_cm,
                original_material_designation=mat_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Solid",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=o2_val,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=round(100.0 - o2_val, 2),
                flow_velocity_initial_cm_s=v_air,
                flow_velocity_min_cm_s=v_air,
                flow_sequence_raw=f"{v_air} cm/s",
                gravity_level="0g",
                oxygen_location="CALCULATED_FROM_CO2",
                ignition_outcome="TRANSIENT_FLASH" if outcome == "Quenched" else "SUCCESSFUL_IGNITION",
                propagation_outcome="NO_SPREAD" if outcome == "Quenched" else ("ANCHORED_REGRESSION" if "note 4" in ug_spread_raw.lower() else "SUSTAINED_SPREAD"),
                suppression_outcome="SELF_EXTINGUISHED",
            )

            meas_list = []
            if burn_t is not None and burn_t > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-99",
                        test_id=test_id,
                        parameter="burning_duration_s",
                        value=burn_t,
                        unit="s",
                        source_doc=p99.name,
                        subtype="SOLID_SAMPLE_BURN_DURATION",
                        instrument="Video Camera",
                        ignition_method="piloted",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Burn Time (s)",
                        raw_val=burn_raw,
                    )
                )
            if "mm/s" in ug_spread_raw:
                sr_val = parse_optional_float(ug_spread_raw)
                if sr_val is not None:
                    meas_list.append(
                        _make_meas(
                            psi_id="PSI-99",
                            test_id=test_id,
                            parameter="flame_spread_rate_mm_s",
                            value=sr_val,
                            unit="mm/s",
                            source_doc=p99.name,
                            subtype="0G_CONCURRENT_SPREAD_RATE",
                            instrument="Video Camera",
                            eligibility_status="ML_ELIGIBLE",
                            raw_col="µ-g Spread Length",
                            raw_val=ug_spread_raw,
                        )
                    )
            elif "note 4" in ug_spread_raw.lower():
                # Note 4: "very slow regression rate (0.01 to 0.04 mm/s)"
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-99",
                        test_id=test_id,
                        parameter="flame_spread_rate_mm_s",
                        value=0.025,
                        unit="mm/s",
                        source_doc=p99.name,
                        value_type="interval",
                        value_min=0.01,
                        value_max=0.04,
                        subtype="0G_ANCHORED_BASE_REGRESSION_RATE",
                        statistic_type="RANGE_MIDPOINT",
                        instrument="Video Camera",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="µ-g Spread Length (Note 4)",
                        raw_val="0.01 to 0.04 mm/s",
                    )
                )
            if "mm/s" in g1_spread_raw:
                sr_1g = parse_optional_float(g1_spread_raw)
                if sr_1g is not None:
                    meas_list.append(
                        _make_meas(
                            psi_id="PSI-99",
                            test_id=test_id,
                            parameter="flame_spread_rate_mm_s",
                            value=sr_1g,
                            unit="mm/s",
                            source_doc=p99.name,
                            subtype="1G_REFERENCE_SPREAD_RATE",
                            instrument="Ground Control Video",
                            eligibility_status="EVIDENCE_ONLY",
                            raw_col="1-g Spread Rate",
                            raw_val=g1_spread_raw,
                        )
                    )
            if ign_p is not None:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-99",
                        test_id=test_id,
                        parameter="ignition_power_watts",
                        value=ign_p,
                        unit="W",
                        source_doc=p99.name,
                        subtype="HOT_WIRE_IGNITER_POWER",
                        instrument="Hot-Wire Igniter",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Ignition Power (W)",
                        raw_val=ign_p,
                    )
                )
            if ign_t is not None:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-99",
                        test_id=test_id,
                        parameter="igniter_operation_duration_s",
                        value=ign_t,
                        unit="s",
                        source_doc=p99.name,
                        subtype="IGNITER_ENERGIZATION_DURATION",
                        instrument="Hot-Wire Igniter",
                        ignition_method="piloted",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Ignition Time (s)",
                        raw_val=ign_t,
                    )
                )
            records.append((exp, samp, cond, meas_list))
        register_file(p99, compute_sha256(p99), psi_id="PSI-99", db_path=db_path)

    # 3. PSI-100 (SAFFIRE-III)
    f100 = resolve_psi_folder("PSI-100", raw_root)
    if f100:
        p100 = f100 / "PSI-100_Experimental table_SAFFIRE-3.csv"
        df100 = _read_csv_with_fallback(p100)
        for row in df100.to_dict(orient="records"):
            s_num = str(row.get("Sample Number ", "") or row.get("Sample Number", "")).strip()
            if not s_num:
                continue
            test_id = f"SAFF3-{s_num}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Material", "SIBAL Fabric")).strip()
            mat_info = parse_fuel_sample_material(mat_raw, default_phase="Solid")
            thick_cm = parse_optional_float(row.get("Sample Thickness"))
            len_cm = parse_optional_float(row.get("Sample Length"))
            wid_cm = parse_optional_float(row.get("Sample Width"))
            v_air = parse_optional_float(row.get("Air Flow "))
            f_dir = str(row.get("Direction", "")).strip()

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-100",
                pi_name="Urban DL",
                sample_id=s_num,
                is_reused_sample=False,
                flow_direction=f_dir if f_dir in {"Concurrent", "Opposed"} else "Unknown",  # type: ignore[arg-type]
                outcome="Sustained",
                observations=f"SAFFIRE-III {f_dir} SIBAL panel burn at {v_air} cm/s airflow",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Fabric",
                thickness_mm=normalize_length_to_mm(thick_cm, "cm") if thick_cm else None,
                width_cm=wid_cm,
                length_cm=len_cm,
                original_material_designation=mat_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Solid",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=21.0,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=79.0,
                flow_velocity_initial_cm_s=v_air,
                flow_velocity_min_cm_s=v_air,
                flow_sequence_raw=f"{v_air} cm/s",
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ignition_outcome="SUCCESSFUL_IGNITION",
                propagation_outcome="SUSTAINED_SPREAD",
                suppression_outcome="SELF_EXTINGUISHED",
            )
            records.append((exp, samp, cond, []))
        register_file(p100, compute_sha256(p100), psi_id="PSI-100", db_path=db_path)

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _ingest_same_101_102_daft_47(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-101 (SAME-R, 109 runs), PSI-102 (SAME, 8 runs), and PSI-47 (DAFT, 2 sessions)."""
    records = []

    # 1. PSI-101 (SAME-R)
    f101 = resolve_psi_folder("PSI-101", raw_root)
    if f101:
        p101 = f101 / "PSI-101_Experimental table_SAME-R.csv"
        df101 = _read_csv_with_fallback(p101)
        for row in df101.to_dict(orient="records"):
            t_num = str(row.get("SAME Test #", "")).strip()
            if not t_num:
                continue
            test_id = f"SAME-R-{t_num}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Sample Type", "")).strip()
            mat_info = parse_fuel_sample_material(mat_raw, default_phase="Solid")
            v_inlet = parse_optional_float(row.get("Inlet velocity (cm/s)"))
            dur_s = parse_optional_float(row.get("Duration (sec)"))
            t_prim = parse_optional_float(row.get("Primary aging time (sec)"))
            t_mix = parse_optional_float(row.get("Primary mixing time (sec)"))
            t_net = parse_optional_float(row.get("Net aging time (sec)"))
            desc = str(row.get("Description", "")).strip()

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-101",
                pi_name="Urban DL / Mulholland GW",
                sample_id=t_num,
                is_reused_sample=False,
                flow_direction="Concurrent" if (v_inlet and v_inlet > 0) else "Quiescent",
                outcome="Sustained",
                observations=f"SAME-R non-flaming pyrolysis smoke test #{t_num} ({mat_raw}): {desc}",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Wire/Insulation",
                original_material_designation=mat_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Solid",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=21.0,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=79.0,
                flow_velocity_initial_cm_s=v_inlet,
                flow_velocity_min_cm_s=v_inlet,
                flow_sequence_raw=f"{v_inlet} cm/s" if v_inlet is not None else None,
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ignition_outcome="PYROLYSIS_NO_FLAME",
                propagation_outcome="NO_SPREAD",
                suppression_outcome="UNKNOWN",
                material_behaviour="SMOLDERING_PYROLYSIS",
            )
            meas_list = []
            # Strictly classify Duration (sec) as pyrolysis_heating_duration_s, NEVER burning_duration_s!
            if dur_s is not None and dur_s > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-101",
                        test_id=test_id,
                        parameter="pyrolysis_heating_duration_s",
                        value=dur_s,
                        unit="s",
                        source_doc=p101.name,
                        subtype="NON_FLAMING_PYROLYSIS_HEATER_DURATION",
                        instrument="Pyrolysis Wire Heater",
                        ignition_method="non_flaming_pyrolysis",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Duration (sec)",
                        raw_val=dur_s,
                    )
                )
            for age_val, age_sub, age_col in (
                (t_prim, "PRIMARY_AGING_TIME", "Primary aging time (sec)"),
                (t_mix, "PRIMARY_MIXING_TIME", "Primary mixing time (sec)"),
                (t_net, "NET_AGING_TIME", "Net aging time (sec)"),
            ):
                if age_val is not None and age_val >= 0:
                    meas_list.append(
                        _make_meas(
                            psi_id="PSI-101",
                            test_id=test_id,
                            parameter="aerosol_aging_time_s",
                            value=age_val,
                            unit="s",
                            source_doc=p101.name,
                            subtype=age_sub,
                            instrument="Aging Chamber Timer",
                            ignition_method="non_flaming_pyrolysis",
                            eligibility_status="ML_ELIGIBLE",
                            raw_col=age_col,
                            raw_val=age_val,
                        )
                    )
            records.append((exp, samp, cond, meas_list))
        register_file(p101, compute_sha256(p101), psi_id="PSI-101", db_path=db_path)

    # 2. PSI-102 (SAME)
    f102 = resolve_psi_folder("PSI-102", raw_root)
    if f102:
        p102 = f102 / "PSI-102_Experimental table_SAME.csv"
        df102 = _read_csv_with_fallback(p102)
        for row in df102.to_dict(orient="records"):
            s_num = str(row.get("Sample #", "")).strip()
            if not s_num:
                continue
            test_id = f"SAME-{s_num.zfill(2)}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Sample Material  ", "") or row.get("Sample Material", "")).strip()
            mat_info = parse_fuel_sample_material(mat_raw, default_phase="Solid")
            v_air = parse_optional_float(row.get("Air Flow (cm/s)"))
            w_loss_mg_min = parse_optional_float(row.get("Weight loss rate (mg/min)"))
            age_min = parse_optional_float(row.get("Aging Duration (minutes)"))

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-102",
                pi_name="Urban DL / Mulholland GW",
                sample_id=s_num,
                is_reused_sample=False,
                flow_direction="Concurrent",
                outcome="Sustained",
                observations=f"SAME flight pyrolysis smoke test #{s_num} ({mat_raw})",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Wire/Insulation",
                original_material_designation=mat_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Solid",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=21.0,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=79.0,
                flow_velocity_initial_cm_s=v_air,
                flow_velocity_min_cm_s=v_air,
                flow_sequence_raw=f"{v_air} cm/s",
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ignition_outcome="PYROLYSIS_NO_FLAME",
                propagation_outcome="NO_SPREAD",
                suppression_outcome="UNKNOWN",
                material_behaviour="SMOLDERING_PYROLYSIS",
            )
            meas_list = []
            if w_loss_mg_min is not None and w_loss_mg_min > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-102",
                        test_id=test_id,
                        parameter="mass_loss_rate_g_s",
                        value=normalize_mass_rate_to_g_s(w_loss_mg_min, "mg/min"),
                        unit="g/s",
                        source_doc=p102.name,
                        subtype="SOLID_PYROLYSIS_MASS_LOSS_RATE",
                        instrument="Analytical Balance",
                        ignition_method="non_flaming_pyrolysis",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Weight loss rate (mg/min)",
                        raw_val=w_loss_mg_min,
                    )
                )
            if age_min is not None and age_min >= 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-102",
                        test_id=test_id,
                        parameter="aerosol_aging_time_s",
                        value=normalize_time_to_s(age_min, "min"),
                        unit="s",
                        source_doc=p102.name,
                        subtype="AGING_DURATION",
                        instrument="Aging Chamber Timer",
                        ignition_method="non_flaming_pyrolysis",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Aging Duration (minutes)",
                        raw_val=age_min,
                    )
                )
            records.append((exp, samp, cond, meas_list))
        register_file(p102, compute_sha256(p102), psi_id="PSI-102", db_path=db_path)

    # 3. PSI-47 (DAFT / DAFT-2)
    f47 = resolve_psi_folder("PSI-47", raw_root)
    if f47:
        p47 = f47 / "PSI-47_Experimental table_DAFT.csv"
        df47 = _read_csv_with_fallback(p47)
        for row in df47.to_dict(orient="records"):
            sess = str(row.get("Session Name", "")).strip()
            if not sess:
                continue
            test_id = f"DAFT-{sess}"
            raw_clean = _clean_raw_row(row)
            mat_raw = str(row.get("Sample Material", "")).strip()
            hw_desc = str(row.get("Hardware Description", "")).strip()
            loc_desc = str(row.get("Sampled Location", "")).strip()

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-47",
                pi_name="Urban DL / Fortenberry C",
                sample_id=sess,
                is_reused_sample=False,
                flow_direction="Quiescent",
                outcome="Sustained",
                observations=f"{hw_desc} | {loc_desc}",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name="Arizona Road Dust (ARD)",
                geometry="Bulk/Dust",
                original_material_designation=mat_raw,
                material_family="Calibration Dust (ARD)",
                fuel_phase="Aerosol/Dust",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=21.0,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=79.0,
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ignition_outcome="UNKNOWN",
                propagation_outcome="UNKNOWN",
                suppression_outcome="UNKNOWN",
            )
            records.append((exp, samp, cond, []))
        register_file(p47, compute_sha256(p47), psi_id="PSI-47", db_path=db_path)

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _ingest_psi107_spice(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-107 (SPICE): Deduplicate 469 camera-frame rows into 153 unique microgravity burns."""
    folder = resolve_psi_folder("PSI-107", raw_root)
    if not folder:
        return 0, 0
    csv_path = folder / "PSI-107_Experimental table_Spice.csv"
    df = _read_csv_with_fallback(csv_path)

    grouped_burns: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in df.to_dict(orient="records"):
        g_date = str(row.get("GMT date", "")).strip()
        g_ign = str(row.get("GMT ignition", "")).strip()
        g_off = str(row.get("GMT  Flame Off ", "") or row.get("GMT Flame Off", "")).strip()
        if not g_date and not g_ign:
            continue
        key = (g_date, g_ign, g_off)
        grouped_burns.setdefault(key, []).append(_clean_raw_row(row))

    records = []
    for idx, ((g_date, g_ign, g_off), frame_rows) in enumerate(grouped_burns.items(), start=1):
        test_id = f"SPICE-{idx:03d}"
        first = frame_rows[0]
        fuel_raw = str(first.get("Fuel", "Ethylene")).strip()
        mat_info = parse_fuel_sample_material(fuel_raw, default_phase="Gas")
        nozzle_mm = parse_optional_float(first.get("Nozzle (mm)"))
        v_air = parse_optional_float(first.get("Air Rate (cm/s)"))
        fuel_mg_s = parse_optional_float(first.get("Fuel Rate (mg/s)")) or parse_optional_float(first.get("HC Fuel Rate (mg/s)"))
        dur_s = parse_gmt_duration_s(g_ign, g_off)

        exp = ExperimentModel(
            test_id=test_id,
            psi_id="PSI-107",
            pi_name="Urban DL / Sunderland PB",
            sample_id=f"GMT{g_date}-{g_ign}",
            is_reused_sample=False,
            flow_direction="Concurrent",
            outcome="Sustained",
            observations=f"SPICE coflow smoke-point burn ({fuel_raw}, nozzle={nozzle_mm} mm, {len(frame_rows)} logged frames)",
            raw_attributes_json={"burn_key": [g_date, g_ign, g_off], "frame_count": len(frame_rows), "first_frame": first},
        )
        samp = SampleModel(
            test_id=test_id,
            material_name=mat_info["material_name"],
            geometry="Gaseous Burner",
            diameter_mm=nozzle_mm,
            original_material_designation=fuel_raw,
            material_family=mat_info["material_family"],
            fuel_phase="Gas",
        )
        cond = ConditionModel(
            test_id=test_id,
            o2_initial_pct=21.0,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=79.0,
            flow_velocity_initial_cm_s=v_air,
            flow_velocity_min_cm_s=v_air,
            flow_sequence_raw=f"{v_air} cm/s" if v_air is not None else None,
            gravity_level="0g",
            oxygen_location="CHAMBER_AMBIENT",
            ignition_outcome="SUCCESSFUL_IGNITION",
            propagation_outcome="STATIONARY_BURNER",
            suppression_outcome="FLOW_TERMINATED",
            material_behaviour="SOOTING",
        )
        meas_list = []
        if dur_s is not None and dur_s > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-107",
                    test_id=test_id,
                    parameter="burning_duration_s",
                    value=dur_s,
                    unit="s",
                    source_doc=csv_path.name,
                    subtype="DEDUPLICATED_GMT_BURN_DURATION",
                    instrument="GMT Video Timestamp",
                    ignition_method="piloted",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="GMT Flame Off - GMT ignition",
                    raw_val=f"{g_ign} -> {g_off}",
                )
            )
        if fuel_mg_s is not None and fuel_mg_s > 0:
            meas_list.append(
                _make_meas(
                    psi_id="PSI-107",
                    test_id=test_id,
                    parameter="fuel_mass_flow_rate_g_s",
                    value=normalize_mass_rate_to_g_s(fuel_mg_s, "mg/s"),
                    unit="g/s",
                    source_doc=csv_path.name,
                    subtype="CONTROLLED_BURNER_MFC_FLOW",
                    instrument="Mass Flow Controller",
                    eligibility_status="ML_ELIGIBLE",
                    raw_col="Fuel Rate (mg/s)",
                    raw_val=fuel_mg_s,
                )
            )
        records.append((exp, samp, cond, meas_list))

    n_meas = _persist_records(records, db_path=db_path)
    register_file(csv_path, compute_sha256(csv_path), psi_id="PSI-107", db_path=db_path)
    return len(records), n_meas


def _ingest_psi10_flame_design(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-10 (ACME Flame Design): 207 Normal Flame runs + 120 Inverse Flame runs."""
    folder = resolve_psi_folder("PSI-10", raw_root)
    if not folder:
        return 0, 0
    records = []

    for fname, is_inverse in (
        ("PSI-10_Experimental table_Flame Design_Normal Flame.csv", False),
        ("PSI-10_Experimental table_Flame Design_Inverse Flame.csv", True),
    ):
        cpath = folder / fname
        if not cpath.exists():
            continue
        df = _read_csv_with_fallback(cpath)
        for row in df.to_dict(orient="records"):
            raw_clean = _clean_raw_row(row)
            t_code = str(row.get("Test", "")).strip()
            if not t_code:
                continue
            prefix = "FD-INV" if is_inverse else "FD-NRM"
            test_id = f"{prefix}-{t_code}"
            fuel_raw = str(row.get("Fuel", "C2H4")).strip()
            mat_info = parse_fuel_sample_material(fuel_raw, default_phase="Gas")

            o2_init_mf = parse_optional_float(row.get("XO2") if is_inverse else row.get("XO2 (init)"))
            o2_final_mf = parse_optional_float(row.get("XO2 (final)")) if not is_inverse else None
            o2_init_pct = normalize_mole_fraction_to_pct(o2_init_mf, True) if o2_init_mf is not None else None
            o2_final_pct = normalize_mole_fraction_to_pct(o2_final_mf, True) if o2_final_mf is not None else None

            p_atm = parse_optional_float(row.get("pinit (atm)")) or parse_optional_float(row.get("pmean (atm)"))
            pressure_psi = normalize_pressure_to_psi(p_atm, "atm") if p_atm is not None else 14.7

            mfuel_mg_s = parse_optional_float(row.get("mfuel (mg/s)"))
            tad_k = parse_optional_float(row.get("Tad (K)"))

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-10",
                pi_name="Axelbaum RL / Sunderland PB",
                sample_id=t_code,
                is_reused_sample=False,
                flow_direction="Quiescent",
                outcome="Sustained",
                observations=f"ACME Flame Design {'Inverse' if is_inverse else 'Normal'} spherical flame {t_code}",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Porous Burner",
                diameter_mm=6.35,
                original_material_designation=fuel_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Gas",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=o2_init_pct,
                o2_final_pct=o2_final_pct,
                pressure_psi=pressure_psi,
                diluent_gas="N2",
                diluent_pct=round(100.0 - o2_init_pct, 2) if o2_init_pct is not None else None,
                flow_velocity_initial_cm_s=0.0,
                flow_velocity_min_cm_s=0.0,
                flow_sequence_raw="Quiescent spherical burner",
                gravity_level="0g",
                oxygen_location="BURNER_OXIDIZER_STREAM" if is_inverse else "CHAMBER_AMBIENT",
                ignition_outcome="SUCCESSFUL_IGNITION",
                propagation_outcome="STATIONARY_BURNER",
                suppression_outcome="UNKNOWN",
            )
            meas_list = []
            if mfuel_mg_s is not None and mfuel_mg_s > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-10",
                        test_id=test_id,
                        parameter="fuel_mass_flow_rate_g_s",
                        value=normalize_mass_rate_to_g_s(mfuel_mg_s, "mg/s"),
                        unit="g/s",
                        source_doc=cpath.name,
                        subtype="CONTROLLED_BURNER_MFC_FLOW",
                        instrument="Mass Flow Controller",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="mfuel (mg/s)",
                        raw_val=mfuel_mg_s,
                    )
                )
            if tad_k is not None and tad_k > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-10",
                        test_id=test_id,
                        parameter="adiabatic_flame_temperature_k",
                        value=tad_k,
                        unit="K",
                        source_doc=cpath.name,
                        subtype="CALCULATED_ADIABATIC_FLAME_TEMP",
                        instrument="Thermodynamic Calculation",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Tad (K)",
                        raw_val=tad_k,
                    )
                )
            records.append((exp, samp, cond, meas_list))
        register_file(cpath, compute_sha256(cpath), psi_id="PSI-10", db_path=db_path)

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _ingest_psi159_cfig(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-159 (ACME CFI-G): Normal & Inverse spherical gaseous cool/hot flames with SE vs FT separation."""
    folder = resolve_psi_folder("PSI-159", raw_root)
    if not folder:
        return 0, 0
    records = []

    for fname, is_inverse in (
        ("PSI-159_Experimental table_CFI-G_Normal Flames.csv", False),
        ("PSI-159_Experimental table_CFI-G_Inverse Flames.csv", True),
    ):
        cpath = folder / fname
        if not cpath.exists():
            continue
        df = _read_csv_with_fallback(cpath)
        for row in df.to_dict(orient="records"):
            t_code = str(row.get("Test", "")).strip()
            hot_ign = str(row.get("Hot ignition", "")).strip()
            p_bar = parse_optional_float(row.get("approx p (bar)"))
            # Skip trailing blank rows in Inverse Flames.csv
            if not t_code or (not hot_ign and p_bar is None):
                continue

            raw_clean = _clean_raw_row(row)
            prefix = "CFIG-INV" if is_inverse else "CFIG-NRM"
            test_id = f"{prefix}-{t_code}"
            fuel_raw = str(row.get("Fuel", "C4H10")).strip()
            mat_info = parse_fuel_sample_material(fuel_raw, default_phase="Gas")

            o2_init_mf = parse_optional_float(row.get("XO2") if is_inverse else row.get(" XO2 before test") or row.get("XO2 before test"))
            o2_final_mf = parse_optional_float(row.get("XO2  after test") or row.get("XO2 after test")) if not is_inverse else None
            o2_init_pct = normalize_mole_fraction_to_pct(o2_init_mf, True) if o2_init_mf is not None else None
            o2_final_pct = normalize_mole_fraction_to_pct(o2_final_mf, True) if o2_final_mf is not None else None

            pressure_psi = normalize_pressure_to_psi(p_bar, "bar") if p_bar is not None else 14.7
            term_raw = str(row.get("Self-ext or flow term") or row.get("Self -ext or flow term") or "").strip().upper()
            burn_s = parse_optional_float(row.get("burn time (sec)"))
            mhc_mg_s = parse_optional_float(row.get("mHC (mg/s)"))
            hc_burn_mg_s = parse_optional_float(row.get("HC burnrate (mg/s)"))
            tad_k = parse_optional_float(row.get("Tad (K)"))
            t_burner_k = parse_optional_float(row.get("Peak burner temp (K)"))
            t_burner_c = parse_optional_float(row.get("Peak burner Temp (C)") or row.get("Peak burner T (C )"))
            if t_burner_k is None and t_burner_c is not None:
                t_burner_k = normalize_temperature_to_k(t_burner_c, "degC")

            hot_lower = hot_ign.lower()
            if hot_lower in {"no", "n"}:
                outcome: ExperimentOutcome = "No Ignition"
                ign_outcome = "NO_IGNITION"
            elif hot_lower == "flash":
                outcome = "Quenched"
                ign_outcome = "TRANSIENT_FLASH"
            elif term_raw == "SE":
                outcome = "Quenched"
                ign_outcome = "SUCCESSFUL_IGNITION"
            else:
                outcome = "Sustained"
                ign_outcome = "SUCCESSFUL_IGNITION"

            supp_outcome = (
                "SELF_EXTINGUISHED"
                if term_raw == "SE"
                else ("FLOW_TERMINATED" if term_raw == "FT" else "UNKNOWN")
            )
            comm = str(row.get("Comments", "")).strip()

            exp = ExperimentModel(
                test_id=test_id,
                psi_id="PSI-159",
                pi_name="Sunderland PB / Axelbaum RL",
                sample_id=t_code,
                is_reused_sample=False,
                flow_direction="Quiescent",
                outcome=outcome,
                observations=f"CFI-G {'Inverse' if is_inverse else 'Normal'} {t_code}: HotIgn={hot_ign}, Term={term_raw}. {comm}".strip(),
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry="Porous Burner",
                diameter_mm=6.35,
                original_material_designation=fuel_raw,
                material_family=mat_info["material_family"],
                fuel_phase="Gas",
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=o2_init_pct,
                o2_final_pct=o2_final_pct,
                pressure_psi=pressure_psi,
                diluent_gas="N2",
                diluent_pct=round(100.0 - o2_init_pct, 2) if o2_init_pct is not None else None,
                flow_velocity_initial_cm_s=0.0,
                flow_velocity_min_cm_s=0.0,
                flow_sequence_raw="Quiescent 6.35 mm spherical burner",
                gravity_level="0g",
                oxygen_location="BURNER_OXIDIZER_STREAM" if is_inverse else "CHAMBER_AMBIENT",
                ignition_outcome=ign_outcome,
                propagation_outcome="STATIONARY_BURNER",
                suppression_outcome=supp_outcome,
            )

            meas_list = []
            # Strictly exclude burn_s == 0 (No Ignition) and tag FT as right-censored!
            if burn_s is not None and burn_s > 0 and hot_lower not in {"no", "n"}:
                is_ft = term_raw == "FT"
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-159",
                        test_id=test_id,
                        parameter="burning_duration_s",
                        value=burn_s,
                        unit="s",
                        source_doc=cpath.name,
                        value_type="censored_ft" if is_ft else "exact",
                        subtype="FLOW_TERMINATED_CENSORED" if is_ft else "SELF_EXTINGUISHED_BURN_DURATION",
                        instrument="Intensified Camera / Radiometer",
                        ignition_method="piloted",
                        eligibility_status="EVIDENCE_ONLY" if is_ft else "ML_ELIGIBLE",
                        raw_col="burn time (sec)",
                        raw_val=burn_s,
                    )
                )
                if term_raw == "SE":
                    meas_list.append(
                        _make_meas(
                            psi_id="PSI-159",
                            test_id=test_id,
                            parameter="extinguishing_time_s",
                            value=burn_s,
                            unit="s",
                            source_doc=cpath.name,
                            subtype="SELF_EXTINGUISHMENT_TIME",
                            instrument="Intensified Camera / Radiometer",
                            eligibility_status="ML_ELIGIBLE",
                            raw_col="burn time (sec)",
                            raw_val=burn_s,
                        )
                    )
            if mhc_mg_s is not None and mhc_mg_s > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-159",
                        test_id=test_id,
                        parameter="fuel_mass_flow_rate_g_s",
                        value=normalize_mass_rate_to_g_s(mhc_mg_s, "mg/s"),
                        unit="g/s",
                        source_doc=cpath.name,
                        subtype="CONTROLLED_BURNER_MFC_FLOW",
                        instrument="Mass Flow Controller",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="mHC (mg/s)",
                        raw_val=mhc_mg_s,
                    )
                )
            if hc_burn_mg_s is not None and hc_burn_mg_s > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-159",
                        test_id=test_id,
                        parameter="mass_burning_rate_g_s",
                        value=normalize_mass_rate_to_g_s(hc_burn_mg_s, "mg/s"),
                        unit="g/s",
                        source_doc=cpath.name,
                        subtype="GASEOUS_HYDROCARBON_BURNING_RATE",
                        instrument="Mass Flow Controller",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="HC burnrate (mg/s)",
                        raw_val=hc_burn_mg_s,
                    )
                )
            if t_burner_k is not None and t_burner_k > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-159",
                        test_id=test_id,
                        parameter="burner_temperature_k",
                        value=t_burner_k,
                        unit="K",
                        source_doc=cpath.name,
                        subtype="PEAK_SPHERICAL_BURNER_TEMP",
                        statistic_type="PEAK",
                        instrument="Thermocouple",
                        eligibility_status="ML_ELIGIBLE",
                        raw_col="Peak burner temp (K)",
                        raw_val=t_burner_k,
                    )
                )
            if tad_k is not None and tad_k > 0:
                meas_list.append(
                    _make_meas(
                        psi_id="PSI-159",
                        test_id=test_id,
                        parameter="adiabatic_flame_temperature_k",
                        value=tad_k,
                        unit="K",
                        source_doc=cpath.name,
                        subtype="CALCULATED_ADIABATIC_FLAME_TEMP",
                        instrument="Thermodynamic Calculation",
                        eligibility_status="EVIDENCE_ONLY",
                        raw_col="Tad (K)",
                        raw_val=tad_k,
                    )
                )
            records.append((exp, samp, cond, meas_list))
        register_file(cpath, compute_sha256(cpath), psi_id="PSI-159", db_path=db_path)

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _ingest_summary_matrix_investigations(raw_root: Path, db_path: Path | str) -> tuple[int, int]:
    """Ingest PSI-20 (BRE), PSI-21 (CLD), PSI-22 (E-FIELD), PSI-23 (s-Flame), PSI-68 (FLEX-2), PSI-106 (SLICE)."""
    records = []

    configs = [
        ("PSI-20", "PSI-20_Experimental table_ACME BRE.csv", "BRE", "Quintiere JG / Sunderland PB", "Gas"),
        ("PSI-21", "PSI-21_Experimental table_CLD Flame.csv", "CLD", "Long MB / Smooke MD", "Gas"),
        ("PSI-22", "PSI-22_Experimental table_ACME E-FIELD Flames.csv", "EFIELD", "Dunn-Rankin D / Chien YC", "Gas"),
        ("PSI-23", "PSI-23_Experimental table_ACME s-Flame.csv", "SFLAME", "Law CK / Tse SD", "Gas"),
        ("PSI-68", "PSI-68_Experimental table_Flex2.csv", "FLEX2", "Williams FA / Dietrich DL", "Liquid"),
        ("PSI-106", "PSI-106_Experimental table_Slice.csv", "SLICE", "Long MB / Smooke MD", "Gas"),
    ]

    for psi_id, csv_name, prefix, pi_name, phase in configs:
        folder = resolve_psi_folder(psi_id, raw_root)
        if not folder:
            continue
        cpath = folder / csv_name
        if not cpath.exists():
            continue
        df = _read_csv_with_fallback(cpath)
        for idx, row in enumerate(df.to_dict(orient="records"), start=1):
            raw_clean = _clean_raw_row(row)
            test_id = f"{prefix}-{idx:02d}"
            fuel_raw = str(
                row.get("Fuel Bottle")
                or row.get("Sample (Fuel Type)")
                or row.get("Fuel Type")
                or "C2H4"
            ).strip()
            mat_info = parse_fuel_sample_material(fuel_raw, default_phase=phase)

            diam_mm = parse_optional_float(row.get("Burner Size (mm)"))
            if diam_mm is None and psi_id == "PSI-68":
                diam_mm = 3.2  # 1.5 - 5 mm droplet range midpoint

            o2_pct = 21.0
            if psi_id == "PSI-20":
                o2_str = str(row.get("Oxygen Conc (percent)", "")).split(";")[0].strip()
                v_o2 = parse_optional_float(o2_str)
                if v_o2 and 0 < v_o2 <= 100:
                    o2_pct = v_o2
            elif psi_id == "PSI-68":
                o2_pct = 21.0

            v_flow = 0.0
            if psi_id == "PSI-68":
                v_flow = 2.5

            notes = str(row.get("Notes") or row.get("Test Type") or row.get("Test Date") or "").strip()
            if psi_id == "PSI-22":
                notes = f"Electric-field polarity: {row.get('Mesh Polarity', 'N/A')} (ELECTRIC_FIELD_BUOYANCY_ANALOG). {notes}"

            exp = ExperimentModel(
                test_id=test_id,
                psi_id=psi_id,
                pi_name=pi_name,
                sample_id=str(row.get("Test Day") or row.get("Test Day*") or idx),
                is_reused_sample=False,
                flow_direction="Concurrent" if psi_id in {"PSI-21", "PSI-22", "PSI-106"} else "Quiescent",
                outcome="Sustained",
                observations=notes or f"{psi_id} test matrix configuration #{idx}",
                raw_attributes_json=raw_clean,
            )
            samp = SampleModel(
                test_id=test_id,
                material_name=mat_info["material_name"],
                geometry=mat_info["geometry"],
                diameter_mm=diam_mm,
                original_material_designation=fuel_raw,
                material_family=mat_info["material_family"],
                fuel_phase=phase,
            )
            cond = ConditionModel(
                test_id=test_id,
                o2_initial_pct=o2_pct,
                pressure_psi=14.7,
                diluent_gas="N2",
                diluent_pct=round(100.0 - o2_pct, 2),
                flow_velocity_initial_cm_s=v_flow,
                flow_velocity_min_cm_s=0.1 if psi_id == "PSI-68" else v_flow,
                flow_sequence_raw=str(row.get("Flow Velocity (cm/s)") or "Quiescent/Coflow"),
                gravity_level="0g",
                oxygen_location="CHAMBER_AMBIENT",
                ambient_temp_k=298.15 if psi_id == "PSI-68" else None,
                ignition_outcome="SUCCESSFUL_IGNITION",
                propagation_outcome="DROPLET_REGRESSION" if phase == "Liquid" else "STATIONARY_BURNER",
                suppression_outcome="UNKNOWN",
            )
            records.append((exp, samp, cond, []))
        register_file(cpath, compute_sha256(cpath), psi_id=psi_id, db_path=db_path)

    n_meas = _persist_records(records, db_path=db_path)
    return len(records), n_meas


def _register_all_raw_files(raw_root: Path, db_path: Path | str) -> int:
    """Register every PDF, DOCX, DOC, and DOI.txt file across all 19 folders in sources table."""
    count = 0
    for folder in sorted(raw_root.iterdir()):
        if not folder.is_dir():
            continue
        psi_id = folder.name.split()[0]
        for fp in sorted(folder.iterdir()):
            if fp.is_file() and fp.suffix.lower() in {".pdf", ".docx", ".doc", ".txt"}:
                register_file(fp, compute_sha256(fp), psi_id=psi_id, status="completed", db_path=db_path)
                count += 1
    return count


def ingest_all_psi_directories(
    raw_root: Path | str = RAW_DATA_DIR,
    db_path: Path | str = DB_PATH,
    force: bool = True,
) -> dict[str, Any]:
    """Rebuild research.db from all 19 NASA PSI folders in data/raw/ with complete scientific validation."""
    from database.seed_catalog import seed_database

    root = Path(raw_root)
    if force and Path(db_path).exists():
        conn = get_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM measurements")
                conn.execute("DELETE FROM conditions")
                conn.execute("DELETE FROM samples")
                conn.execute("DELETE FROM experiments")
                conn.execute("DELETE FROM findings")
                conn.execute("DELETE FROM sources")
        finally:
            conn.close()

    seed_database(db_path=db_path)

    # 1. PSI-25 (BASS-II)
    psi25_res = ingest_psi25_directory(raw_root=root, db_path=db_path, force=True)

    # 2. Remaining 18 PSI folders
    r26, m26 = _ingest_psi26_bass(root, db_path)
    r39, m39 = _ingest_psi39_cfi(root, db_path)
    r69, m69 = _ingest_psi69_flex(root, db_path)
    r_saff, m_saff = _ingest_saffire_98_99_100(root, db_path)
    r_same, m_same = _ingest_same_101_102_daft_47(root, db_path)
    r107, m107 = _ingest_psi107_spice(root, db_path)
    r10, m10 = _ingest_psi10_flame_design(root, db_path)
    r159, m159 = _ingest_psi159_cfig(root, db_path)
    r_mat, m_mat = _ingest_summary_matrix_investigations(root, db_path)

    # 3. Insert verified PDF tabular & report measurements (SAME Table 1, SAME-R Tables 1 & 2, DAFT Fig 5, BASS-II, CFI-G)
    pdf_measurements = extract_verified_pdf_measurements()
    conn = get_connection(db_path)
    try:
        with conn:
            for m in pdf_measurements:
                conn.execute(
                    """
                    INSERT INTO measurements (
                        psi_id, test_id, parameter, value, unit,
                        is_over_range, value_type, source_doc, source_page, verification_status,
                        subtype, value_min, value_max, statistic_type,
                        instrument, ignition_method, eligibility_status, source_trace_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        m.subtype,
                        m.value_min,
                        m.value_max,
                        m.statistic_type,
                        m.instrument,
                        m.ignition_method,
                        m.eligibility_status,
                        m.source_trace_json,
                    ),
                )
    finally:
        conn.close()

    doc_files_registered = _register_all_raw_files(root, db_path)

    total_runs = (
        psi25_res["experiments_loaded"]
        + r26
        + r39
        + r69
        + r_saff
        + r_same
        + r107
        + r10
        + r159
        + r_mat
    )
    total_meas = (
        psi25_res["measurements_loaded"]
        + m26
        + m39
        + m69
        + m_saff
        + m_same
        + m107
        + m10
        + m159
        + m_mat
        + len(pdf_measurements)
    )

    return {
        "status": "completed",
        "investigations_seeded": 19,
        "experiments_loaded": total_runs,
        "measurements_loaded": total_meas,
        "pdf_measurements_loaded": len(pdf_measurements),
        "raw_docs_registered": doc_files_registered,
        "psi25_details": psi25_res,
    }


if __name__ == "__main__":
    summary = ingest_all_psi_directories(raw_root=RAW_DATA_DIR, db_path=DB_PATH, force=True)
    print("=== FULL 19-INVESTIGATION NASA PSI INGESTION COMPLETE ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "psi25_details"}, indent=2))
