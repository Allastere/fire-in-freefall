"""Resolve original CSV evidence dynamically, without trusting importer defaults."""

import hashlib
import json
import math
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from core.normalization import normalize_pressure_to_psi, parse_fuel_sample_material
from database.repository import get_experiments_df, get_measurements_df
from ingestion.schema_mapper import map_csv_columns
from config.settings import BASE_DIR
from ui.data import csv_sources, read_csv


def finite(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def equal(left, right):
    left = None if isinstance(left, float) and math.isnan(left) else left
    right = None if isinstance(right, float) and math.isnan(right) else right
    if left is None or right is None:
        return left is None and right is None
    a, b = finite(left), finite(right)
    if a is not None and b is not None:
        return math.isclose(a, b, rel_tol=0, abs_tol=1e-7)
    return str(left).strip().casefold() == str(right).strip().casefold()


def source_index(db_path, raw_root):
    """Only hash-checked, unambiguous original records are marked source-backed."""
    result, problems = {}, []
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        registered = conn.execute("SELECT psi_id, file_path, sha256_hash FROM sources ORDER BY psi_id, file_path").fetchall()
    for pid, location, expected_hash in registered:
        name = str(location).replace("\\", "/").rsplit("/", 1)[-1]
        if Path(name).suffix.lower() != ".csv" or not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
            continue
        path = Path(raw_root) / pid / name
        try:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != expected_hash:
                raise ValueError("registered checksum mismatch")
            frame = read_csv(content)
            frame.columns = frame.columns.str.strip()
            plan = map_csv_columns(list(frame.columns), frame.head(3).to_dict("records"), pid)
            mapping = {(m.target_table, m.target_field): m for m in plan.mappings}
            identifier = mapping.get(("experiments", "test_id"))
            if identifier is None:
                raise ValueError("no deterministic test identifier mapping")
            sources = csv_sources(content, name, pid)
            for index, raw in enumerate(frame.to_dict("records")):
                test = str(raw[identifier.raw_column]).strip()
                uid = f"{pid}:{test}"
                item = {"raw": raw, "mapping": mapping, "source": {
                    **sources[index], "test_id": test, "source_sha256": digest}, "ambiguous": False}
                if uid in result:
                    result[uid]["ambiguous"] = True
                else:
                    result[uid] = item
        except (OSError, ValueError, pd.errors.ParserError):
            problems.append(f"Original CSV unavailable or incompatible: {pid}/{name}")
    return result, problems


def load_evidence(db_path, raw_root, target):
    """Use repositories for data, and independently verify each numeric source value."""
    runs = get_experiments_df(db_path=db_path)
    measurements = get_measurements_df(parameter=target, db_path=db_path)
    index, problems = source_index(db_path, raw_root)
    try:
        protocols = json.loads((BASE_DIR / "ml" / "protocols.json").read_text(encoding="utf-8"))["protocols"]
    except (OSError, ValueError, KeyError):
        protocols = []
    observations = []
    for row in runs.to_dict("records"):
        uid = f"{row['psi_id']}:{row['test_id']}"
        original = index.get(uid)
        if not original or original["ambiguous"]:
            continue
        raw, mapping = original["raw"], original["mapping"]
        try:
            stored = {k.strip(): v for k, v in json.loads(row["raw_attributes_json"]).items()}
        except (TypeError, ValueError):
            continue
        if stored != raw:
            continue
        def field(table, name):
            entry = mapping.get((table, name))
            return raw.get(entry.raw_column, "") if entry else ""

        material = field("samples", "material_name")
        # The legacy importer defaults unknown material names to PMMA; do not inherit that assumption.
        material_known = bool(row.get("material_name")) and bool(re.search(
            r"\b" + re.escape(row["material_name"]) + r"\b", material, re.I))
        geometry = parse_fuel_sample_material(material)
        oxygen = finite(field("conditions", "o2_initial_pct"))
        air = re.match(r"^\s*(\d+(?:\.\d+)?)(?=\s|,|$)", field("conditions", "flow_velocity_initial_cm_s"))
        pressure_entry = mapping.get(("conditions", "pressure_psi"))
        pressure = finite(field("conditions", "pressure_psi"))
        if pressure is not None and pressure_entry:
            pressure = normalize_pressure_to_psi(pressure, pressure_entry.detected_unit or "psi")
        gravity = {"0g": 0.0, "1g": 1.0}.get(str(row.get("gravity_level")))
        known_protocol = any(p["psi_id"] == row["psi_id"] and p["file_name"] == original["source"]["source_doc"] for p in protocols)
        raw_gravity = field("conditions", "gravity_level")
        raw_direction = field("experiments", "flow_direction")
        # Unknown imports may inherit the legacy importer's 0g/opposed defaults. Require raw
        # conditions or a reviewed source mapping before treating those defaults as recorded metadata.
        regime_known = equal(raw_gravity, row.get("gravity_level")) if raw_gravity else known_protocol
        orientation_known = equal(raw_direction, row.get("flow_direction")) if raw_direction else known_protocol
        # 0g metadata means the investigation's recorded microgravity regime, not measured acceleration.
        features = {"material_name": row.get("material_name"), "geometry": row.get("geometry"),
                    "o2_initial_pct": oxygen, "pressure_psi": pressure or finite(row.get("pressure_psi")),
                    "flow_velocity_initial_cm_s": float(air.group(1)) if air else None,
                    "gravity_g": gravity, "flow_direction": row.get("flow_direction"),
                    "is_reused_sample": bool(row.get("is_reused_sample")),
                    "flow_sequence_raw": field("conditions", "flow_velocity_initial_cm_s"),
                    "co2_initial_pct": finite(field("measurements", "co2_initial_pct")),
                    "burn_sides": "one" if re.search(r"1\s*sided|one\s*sided", material, re.I) else (
                        "two" if re.search(r"2\s*sided|2ide|two\s*sided", material, re.I) else "unspecified")}
        for dimension in ("thickness_mm", "width_cm", "diameter_mm"):
            features[dimension] = finite(geometry.get(dimension))
        geometry_known = equal(geometry.get("geometry"), row.get("geometry")) and row.get("geometry") not in (None, "Unknown")
        conditions_verified = (material_known and geometry_known and oxygen is not None and 0 <= oxygen <= 100
                               and air is not None and gravity is not None and regime_known and orientation_known
                               and finite(features["pressure_psi"]) is not None and features["pressure_psi"] > 0)
        for key in ("o2_initial_pct", "flow_velocity_initial_cm_s", "thickness_mm", "width_cm", "diameter_mm"):
            conditions_verified = conditions_verified and equal(features.get(key), row.get(key))
        matches = measurements[(measurements.psi_id == row["psi_id"]) & (measurements.test_id == row["test_id"])]
        condition_target = {"o2_initial_calibrated_pct": "o2_initial_pct",
                            "o2_final_calibrated_pct": "o2_final_pct"}.get(target)
        table_name = "conditions" if condition_target else "measurements"
        field_name = condition_target or target
        target_entry = mapping.get((table_name, field_name))
        raw_target = finite(field(table_name, field_name))
        for measurement in matches.to_dict("records"):
            if (not conditions_verified or target_entry is None or raw_target is None
                or measurement.get("is_over_range") or measurement.get("value_type") != "exact"
                or measurement.get("verification_status") != "verified"
                or measurement.get("source_doc") != original["source"]["source_doc"]
                or not equal(raw_target, measurement.get("value"))
                or target_entry.detected_unit != measurement.get("unit")):
                continue
            if target_entry.detected_unit == "%" and not 0 <= raw_target <= 100:
                continue
            if target_entry.detected_unit in ("ppm", "mm/s", "mm2/s", "W") and raw_target < 0:
                continue
            source = {**original["source"], "doi": row.get("doi")}
            observations.append({"uid": uid, "psi_id": row["psi_id"], "test_id": row["test_id"],
                "acronym": row["acronym"], "features": features, "value": raw_target,
                "unit": measurement["unit"], "pressure_measured": pressure is not None,
                "source": source, "sample_id": row.get("sample_id")})
    return observations, problems


def related_records(db_path, raw_root, material):
    """Original records for qualitative context when the requested target itself is absent."""
    index, _ = source_index(db_path, raw_root)
    related = []
    for row in get_experiments_df(db_path=db_path).to_dict("records"):
        if not equal(row.get("material_name"), material):
            continue
        uid = f"{row['psi_id']}:{row['test_id']}"
        source = index.get(uid)
        if not source or source["ambiguous"]:
            continue
        try:
            stored = {k.strip(): v for k, v in json.loads(row["raw_attributes_json"]).items()}
            mapping = source["mapping"].get(("samples", "material_name"))
            if (stored != source["raw"] or not mapping or not re.search(
                r"\b" + re.escape(material) + r"\b", source["raw"][mapping.raw_column], re.I)):
                continue
        except (TypeError, ValueError):
            continue
        related.append({"uid": uid, "psi_id": row["psi_id"], "test_id": row["test_id"],
                        "source": {**source["source"], "doi": row.get("doi")}})
    return related
