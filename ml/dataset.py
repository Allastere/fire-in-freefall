"""Read-only scientific snapshot, provenance checks and leakage groups."""

import hashlib
import json
import math
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from core.normalization import parse_fuel_sample_material


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def source_records(db_path, raw_root, protocols, task):
    """Resolve every registered CSV dynamically; unknown scientific protocols are quarantined."""
    records, exclusions, source_hashes = {}, [], {}
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("BEGIN")
        sources = pd.read_sql_query("SELECT file_path, sha256_hash, psi_id FROM sources ORDER BY psi_id, file_path", conn)
        runs = pd.read_sql_query("SELECT e.*, i.doi, s.material_name, s.geometry, s.thickness_mm, s.width_cm, "
                                 "s.diameter_mm, c.o2_initial_pct, c.pressure_psi, c.gravity_level "
                                 "FROM experiments e JOIN investigations i USING(psi_id) "
                                 "JOIN samples s USING(test_id) JOIN conditions c USING(test_id)", conn)
        measures = pd.read_sql_query("SELECT * FROM measurements WHERE parameter = ?", conn, params=[task["target"]])
    if runs.duplicated(["psi_id", "test_id"]).any():
        raise ValueError("Ambiguous sample/condition joins; training aborted to avoid duplicated observations.")
    for source in sources.to_dict("records"):
        name = source["file_path"].replace("\\", "/").rsplit("/", 1)[-1]
        if Path(name).suffix.lower() != ".csv":
            continue
        protocol = next((p for p in protocols if p["psi_id"] == source["psi_id"] and p["file_name"] == name
                         and task["phenomenon"] in p["compatible_phenomena"]), None)
        if protocol is None:
            exclusions.append({"source": name, "reason": "unreviewed_or_incompatible_protocol"})
            continue
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source["psi_id"]):
            raise ValueError("Invalid investigation path in source registry.")
        path = Path(raw_root) / source["psi_id"] / name
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != source["sha256_hash"]:
            raise ValueError(f"Source hash mismatch: {name}")
        source_hashes[f"{source['psi_id']}/{name}"] = digest
        raw = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        raw.columns = raw.columns.str.strip()
        columns = protocol["raw_columns"]
        if not set(columns.values()).issubset(raw.columns):
            raise ValueError(f"Source schema changed: {name}; review the protocol mapping.")
        for index, row in enumerate(raw.to_dict("records")):
            test_id = row[columns["test_id"]].strip()
            uid = f"{source['psi_id']}:{test_id}"
            if uid in records:
                raise ValueError(f"Duplicate source identity: {uid}")
            sample = re.sub(r"[mM]$", "", row[columns["sample_id"]].strip())
            session = row[columns["session"]].strip()
            records[uid] = {"raw": row, "protocol": protocol, "source_doc": name,
                            "source_sha256": digest, "source_record": index + 1,
                            "tokens": [f"sample:{source['psi_id']}:{sample}",
                                       f"session:{protocol['id']}:{session}"],
                            "identity_complete": bool(sample and session)}
    return runs, measures, records, exclusions, source_hashes


def components(records):
    """Union all shared specimens or calibration sessions, including subsequently excluded runs."""
    parent = {uid: uid for uid in records}
    def root(uid):
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid
    seen = {}
    for uid, record in sorted(records.items()):
        for token in record["tokens"]:
            if token in seen:
                parent[root(uid)] = root(seen[token])
            else:
                seen[token] = uid
    groups = defaultdict(list)
    for uid in records:
        groups[root(uid)].append(uid)
    result = {}
    for members in groups.values():
        tokens = sorted({t for uid in members for t in records[uid]["tokens"]})
        for uid in members:
            result[uid] = {"group": fingerprint(tokens), "tokens": tokens}
    return result


def number(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("Non-finite measurement")
    return parsed


def extract_dataset(db_path, raw_root, task, protocols):
    runs, measures, raw_records, exclusions, sources = source_records(db_path, raw_root, protocols, task)
    groups = components(raw_records)
    samples: list[dict[str, Any]] = []
    for row in runs.to_dict("records"):
        uid = f"{row['psi_id']}:{row['test_id']}"
        if any(row.get(key) != value for key, value in task["filters"].items()):
            exclusions.append({"uid": uid, "reason": "incompatible_physical_series"})
            continue
        source = raw_records.get(uid)
        if source is None:
            exclusions.append({"uid": uid, "reason": "no_compatible_original_source"})
            continue
        try:
            raw, protocol = source["raw"], source["protocol"]
            cols = protocol["raw_columns"]
            if not source["identity_complete"]:
                raise ValueError("missing_sample_or_session")
            stored_raw = {k.strip(): v for k, v in json.loads(row["raw_attributes_json"]).items()}
            if stored_raw != raw:
                raise ValueError("database_source_row_mismatch")
            material_description = raw[cols["material"]]
            if not re.search(r"\b" + re.escape(task["filters"]["material_name"]) + r"\b", material_description, re.I):
                raise ValueError("unconfirmed_material_identity")
            oxygen = number(raw[cols["oxygen"]])
            if not 0 <= oxygen <= 100:
                raise ValueError("invalid_oxygen")
            final_oxygen = raw[cols["final_oxygen"]]
            if final_oxygen:
                final = number(final_oxygen)
                if final > oxygen + 0.5 or (final < 5 and oxygen > 15):
                    raise ValueError("sensor_condition_anomaly")
            air_match = re.match(r"^\s*(\d+(?:\.\d+)?)(?=\s|,|$)", raw[cols["airflow"]])
            if not air_match:
                raise ValueError("initial_airflow_not_exact")
            geometry = parse_fuel_sample_material(material_description)
            initial = number(raw[cols["co2_initial_pct"]])
            target_rows = measures[(measures.test_id == row["test_id"]) & (measures.psi_id == row["psi_id"])]
            if len(target_rows) != 1:
                raise ValueError("missing_or_multiple_target_measurements")
            target = target_rows.iloc[0]
            if target["verification_status"] != "verified" or target["is_over_range"] or target["value_type"] != "exact":
                raise ValueError("target_not_exact_verified")
            if target["source_doc"] != source["source_doc"]:
                raise ValueError("target_source_mismatch")
            raw_unit = protocol["source_target_units"].get(task["target"])
            if raw_unit != task["unit"] or target["unit"] != task["unit"]:
                raise ValueError("target_unit_requires_review")
            value = number(raw[cols[task["target"]]])
            if not math.isclose(value, float(target["value"]), abs_tol=1e-9) or not 0 <= value <= 25 or not 0 <= initial <= 25:
                raise ValueError("invalid_target_or_background")
            sides = "one" if re.search(r"1\s*sided|one\s*sided", material_description, re.I) else (
                "two" if re.search(r"2\s*sided|2ide|two\s*sided", material_description, re.I) else "unspecified")
            feature_values = {"o2_initial_pct": oxygen, "flow_velocity_initial_cm_s": float(air_match.group(1)),
                              "thickness_mm": geometry["thickness_mm"], "width_cm": geometry["width_cm"],
                              "co2_initial_pct": initial, "is_reused_sample": float(row["is_reused_sample"]),
                              "burn_sides": sides}
            features: dict[str, Any] = {k: feature_values[k] for k in task["numeric_features"] + task["categorical_features"]}
            for key in task["numeric_features"]:
                features[key] = number(features[key])
                if features[key] < 0:
                    raise ValueError("negative_feature")
            if features["thickness_mm"] <= 0 or features["width_cm"] <= 0:
                raise ValueError("missing_critical_geometry")
            sample: dict[str, Any] = {"uid": uid, "test_id": row["test_id"], "psi_id": row["psi_id"],
                      "material": row["material_name"], "geometry": row["geometry"], "doi": row["doi"],
                      "features": features, "target": value, **groups[uid],
                      "source": {k: source[k] for k in ("source_doc", "source_sha256", "source_record")},
                      "protocol_id": protocol["id"], "scientific_status": protocol["scientific_status"]}
            # Source file hashes change when other rows are appended; held-out observation identity must not.
            sample["observation_sha256"] = fingerprint({"uid": uid, "raw": raw, "features": features, "target": value})
            samples.append(sample)
        except (ValueError, TypeError, KeyError) as exc:
            exclusions.append({"uid": uid, "reason": str(exc)})
    samples.sort(key=lambda s: s["uid"])
    unique, seen = [], set()
    for sample in samples:
        source = raw_records[sample["uid"]]
        id_column = source["protocol"]["raw_columns"]["test_id"]
        duplicate_key = fingerprint({"protocol": sample["protocol_id"], "tokens": source["tokens"],
                                     "raw": {k: v for k, v in source["raw"].items() if k != id_column}})
        if duplicate_key in seen:
            exclusions.append({"uid": sample["uid"], "reason": "duplicate_source_observation"})
        else:
            unique.append(sample)
            seen.add(duplicate_key)
    samples = unique
    if not samples:
        raise ValueError("INSUFFICIENT_DATA: no source-backed compatible observations.")
    source_snapshot = [{"uid": uid, "raw": source["raw"], "protocol_id": source["protocol"]["id"],
                        "source_doc": source["source_doc"], "source_sha256": source["source_sha256"],
                        "source_record": source["source_record"]} for uid, source in sorted(raw_records.items())]
    snapshot = {"samples": samples, "source_hashes": sources, "source_observations": source_snapshot,
                "task": task, "protocols": protocols}
    return {**snapshot, "dataset_sha256": fingerprint(snapshot), "exclusions": exclusions}
