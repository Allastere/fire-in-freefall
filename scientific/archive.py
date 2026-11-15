"""Read-only, provenance-aware archive shared by intelligence, ranking and ML audit."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from config.settings import DB_PATH, RAW_DATA_DIR
from ingestion.file_loader import matches_sha256, resolve_psi_folder
from ml.dataset import fingerprint
from ui.data import read_csv


def json_value(value, fallback=None):
    try:
        return json.loads(value or "null") or fallback
    except (ValueError, TypeError):
        return fallback


def load_archive(db_path=DB_PATH, raw_root=RAW_DATA_DIR):
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        tables = {t: [dict(r) for r in conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid')]
                  for t in ("investigations", "experiments", "samples", "conditions", "measurements", "findings", "sources")}
    source_map, frames, problems = {}, {}, []
    for source in tables["sources"]:
        pid = source["psi_id"]
        name = str(source["file_path"]).replace("\\", "/").rsplit("/", 1)[-1]
        folder = resolve_psi_folder(pid, raw_root)
        path = folder / name if folder else None
        if not path or not path.is_file() or not matches_sha256(path.read_bytes(), source["sha256_hash"]):
            problems.append(f"Missing or changed source: {pid}/{name}")
            continue
        source_map[pid, name] = {"path": str(path), "sha256": source["sha256_hash"]}
        if path.suffix.lower() == ".csv":
            try:
                frame = read_csv(path.read_bytes())
                frame.columns = frame.columns.str.strip()
                frames[pid, name] = frame.to_dict("records")
            except (ValueError, OSError):
                problems.append(f"Unparseable source: {pid}/{name}")
    runs = {e["test_id"]: {**e, "raw": json_value(e["raw_attributes_json"], {})} for e in tables["experiments"]}
    for t in ("samples", "conditions"):
        for row in tables[t]:
            if row["test_id"] in runs:
                runs[row["test_id"]].update({k: v for k, v in row.items() if k not in ("id", "test_id")})
    rows = []
    aging = {}
    for m in tables["measurements"]:
        if m["parameter"]=="aerosol_aging_time_s" and m["verification_status"]=="verified" and m["value_type"]=="exact":
            key={"NET_AGING_TIME":"aerosol_aging_time_s","PRIMARY_MIXING_TIME":"mixing_time_s"}.get(m.get("subtype"))
            if key: aging.setdefault(m["test_id"],{})[key]=m["value"]
    for m in tables["measurements"]:
        trace = json_value(m.get("source_trace_json"), {})
        source = source_map.get((m["psi_id"], m["source_doc"]))
        run = runs.get(m["test_id"], {})
        raw = {str(k).strip(): v for k, v in run.get("raw", {}).items()}
        originals = frames.get((m["psi_id"], m["source_doc"]), [])
        record = next((i for i, r in enumerate(originals, 1) if r == raw), None) if raw else None
        raw_column = trace.get("raw_column")
        csv_verified = record is not None and raw_column in raw and str(raw[raw_column]) == str(trace.get("raw_value"))
        # PDF tables carry explicit import traces; they are reported observations, not run-level controls.
        reported = bool(source and m.get("source_page") and trace.get("source_page") == m["source_page"]
                        and (trace.get("table") or trace.get("raw_value") is not None))
        verified = bool(source and m["verification_status"] == "verified" and (csv_verified or reported))
        material = run.get("material_name") or trace.get("material")
        conditions = {k: run.get(k) for k in ("o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s",
            "ambient_temp_k", "geometry", "fuel_phase", "diameter_mm", "thickness_mm", "width_cm",
            "flow_direction", "co2_diluent_pct", "he_diluent_pct", "n2_diluent_pct")}
        conditions["gravity_g"] = {"0g": 0., "1g": 1.}.get(run.get("gravity_level"))
        conditions.update(aging.get(m["test_id"],{}))
        # A legacy default pressure is not measured. Only raw pressure columns certify this condition.
        if not any("pressure" in k.lower() or k.lower().startswith(("pinit", "pmean")) for k in raw):
            conditions["pressure_psi"] = None
        sid = f"{m['psi_id']}:{m['source_doc']}:measurement:{m['id']}"
        text = json.dumps({"original": raw if csv_verified else trace, "reported_measurement": {
            k: m.get(k) for k in ("parameter", "subtype", "value", "unit", "value_type", "statistic_type", "instrument")}}, ensure_ascii=False)
        rows.append({**m, "material": material, "conditions": conditions, "verified": verified,
            "provenance": "original CSV row checked" if csv_verified else "reported document table" if reported else "needs source review",
            "source": {"source_id": sid, "psi_id": m["psi_id"], "source_doc": m["source_doc"],
                "locator": f"CSV record {record}" if csv_verified else f"Page {m['source_page']}",
                "source_sha256": source["sha256"] if source else None, "text": text},
            "run": run})
    # Cache fingerprints exclude API caches/timestamps but include every scientific row and actual source health.
    return {"tables": tables, "runs": runs, "rows": rows, "problems": problems,
            "fingerprint": fingerprint({"tables": tables, "source_health": problems})}
