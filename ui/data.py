"""Read the existing repository and parse uploads without changing research.db."""

import hashlib
import json
import math
from io import BytesIO
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader

from core.normalization import (
    normalize_pressure_to_psi, parse_air_display, parse_co_value,
    parse_fuel_sample_material, parse_optional_float,
)
from ingestion.schema_mapper import map_csv_columns

CSV_BACKED = "Source CSV available"
SEEDED = "Catalog seed — source not checked"
UPLOADED = "Session upload — not verified"
RUN_COLUMNS = [
    "test_id", "psi_id", "acronym", "material_name", "o2_initial_pct",
    "o2_final_pct", "pressure_psi", "flow_velocity_initial_cm_s",
    "flow_velocity_min_cm_s", "gravity_level", "flow_direction", "outcome",
    "data_origin", "observations", "raw_attributes_json",
]
LABELS = {
    "test_id": "Test ID", "psi_id": "Investigation", "material_name": "Material",
    "o2_initial_pct": "Initial O₂ (%)", "o2_final_pct": "Final O₂ (%)",
    "pressure_psi": "Pressure (psi)", "flow_velocity_initial_cm_s": "Initial airflow (cm/s)",
    "flow_velocity_min_cm_s": "Minimum airflow (cm/s)", "gravity_level": "Gravity",
    "flow_direction": "Flow direction", "outcome": "Outcome", "data_origin": "Data origin",
    "parameter": "Parameter", "value": "Value", "unit": "Unit",
    "is_over_range": "Sensor over-range", "source_doc": "Source document",
    "source_page": "Stored source page", "verification_status": "Database status",
}


def read_csv(content):
    return pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")


def csv_sources(content, name, psi_id, doi=None):
    frame = read_csv(content)
    return [
        {"source_id": f"{psi_id}:{name}:record:{index + 1}", "psi_id": psi_id,
         "doi": doi, "source_doc": name, "locator": f"CSV record {index + 1} (header excluded)",
         "text": json.dumps(row, ensure_ascii=False, sort_keys=True),
         "test_id": str(row.get("Test #", row.get("Test ID", row.get("test_id", "")))).strip()}
        for index, row in enumerate(frame.to_dict("records"))
    ]


def document_sources(content, name, psi_id, doi=None):
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 300:
            raise ValueError("Please split PDFs longer than 300 pages before uploading.")
        parts = [(f"PDF page {i + 1}", p.extract_text() or "") for i, p in enumerate(reader.pages)]
    elif suffix == ".docx":
        doc = Document(BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs]
        paragraphs += [" | ".join(c.text for c in r.cells) for t in doc.tables for r in t.rows]
        parts = [("DOCX text; page unknown", "\n".join(paragraphs))]
    elif suffix == ".txt":
        parts = [("Text; page unknown", content.decode("utf-8-sig"))]
    else:
        raise ValueError("Supported files: CSV, PDF, DOCX and UTF-8 TXT.")
    sources = []
    for locator, text in parts:
        for start in range(0, len(text), 2200):
            excerpt = text[start:start + 2200].strip()
            if excerpt:
                sources.append({"source_id": f"{psi_id}:{name}:{locator}:{start}",
                                "psi_id": psi_id, "doi": doi, "source_doc": name,
                                "locator": locator, "text": excerpt})
    return sources


def parse_upload(content, name, investigation):
    """Keep raw data and conservative mapped values in memory; do not infer missing conditions."""
    if not content or len(content) > 10 * 1024 * 1024:
        raise ValueError("Choose a non-empty file smaller than 10 MB.")
    name = Path(name).name
    pid = investigation["psi_id"]
    digest = hashlib.sha256(content).hexdigest()
    result = {"name": name, "psi_id": pid, "sha256": digest, "content": content,
              "runs": pd.DataFrame(columns=RUN_COLUMNS), "measurements": pd.DataFrame(),
              "mapping": [], "unmapped": []}
    if Path(name).suffix.lower() != ".csv":
        result["sources"] = document_sources(content, name, pid, investigation.get("doi"))
        if not result["sources"]:
            raise ValueError("No text could be extracted. Scanned PDFs require a text layer.")
        for source in result["sources"]:
            source["source_id"] = f"upload:{digest}:" + source["source_id"]
            source["origin"] = UPLOADED
        return result
    raw = read_csv(content)
    if raw.empty or len(raw) > 10000:
        raise ValueError("CSV must contain between 1 and 10,000 records.")
    result["raw"] = raw
    result["sources"] = csv_sources(content, name, pid, investigation.get("doi"))
    for source in result["sources"]:
        source["source_id"] = f"upload:{digest}:" + source["source_id"]
        source["origin"] = UPLOADED
    plan = map_csv_columns(list(raw.columns), raw.head(3).to_dict("records"), psi_id=pid)
    result["mapping"] = [m.model_dump() for m in plan.mappings]
    result["unmapped"] = plan.unmapped_columns
    lookup = {(m.target_table, m.target_field): m for m in plan.mappings}
    runs, measurements = [], []
    for index, row in enumerate(raw.to_dict("records")):
        def field(table, key, default=""):
            mapping = lookup.get((table, key))
            return row.get(mapping.raw_column, default) if mapping else default

        test_id = str(field("experiments", "test_id")).strip() or f"record-{index + 1}"
        session_id = f"upload:{digest[:12]}:{index + 1}:{test_id}"
        material = parse_fuel_sample_material(field("samples", "material_name"))
        air = parse_air_display(field("conditions", "flow_velocity_initial_cm_s"))
        numbers = {key: parse_optional_float(field("conditions", key))
                   for key in ("o2_initial_pct", "o2_final_pct", "pressure_psi")}
        for key, value in numbers.items():
            if value is not None and (not math.isfinite(value) or value < 0 or
                                      (key.startswith("o2") and value > 100) or
                                      (key == "pressure_psi" and value == 0)):
                raise ValueError(f"Record {index + 1}: invalid {key}. Check the source units.")
        pressure_map = lookup.get(("conditions", "pressure_psi"))
        if numbers["pressure_psi"] is not None:
            numbers["pressure_psi"] = normalize_pressure_to_psi(
                numbers["pressure_psi"], (pressure_map.detected_unit if pressure_map else None) or "psi")
        runs.append({**{key: investigation.get(key) for key in
                        ("psi_id", "acronym", "doi", "safety_pillar", "hardware_facility", "fuel_category")},
                     **material, **numbers, **air, "test_id": session_id, "original_test_id": test_id,
                     "gravity_level": field("conditions", "gravity_level") or "Unknown",
                     "flow_direction": field("experiments", "flow_direction") or "Unknown",
                     "outcome": field("experiments", "outcome") or "Unknown",
                     "observations": field("experiments", "observations"),
                     "raw_attributes_json": json.dumps(row, ensure_ascii=False), "data_origin": UPLOADED})
        for mapping in plan.mappings:
            if mapping.target_table != "measurements":
                continue
            value, over, kind = parse_optional_float(row[mapping.raw_column]), False, "exact"
            if pid == "PSI-25" and mapping.target_field in ("co_initial_ppm", "co_final_ppm"):
                value, over, kind = parse_co_value(row[mapping.raw_column])
            if value is not None and math.isfinite(value):
                measurements.append({"id": f"{session_id}:{mapping.target_field}", "test_id": session_id,
                                     "psi_id": pid, "acronym": investigation["acronym"],
                                     "parameter": mapping.target_field, "value": value,
                                     "unit": mapping.detected_unit, "is_over_range": over, "value_type": kind,
                                     "source_doc": name, "source_page": None,
                                     "verification_status": "needs_review", "data_origin": UPLOADED})
        result["sources"][index]["test_id"] = session_id
    result["runs"] = pd.DataFrame(runs)
    result["measurements"] = pd.DataFrame(measurements)
    return result
