"""Shared repository reads, filters and attribution widgets."""

import json
import sqlite3

import pandas as pd
import streamlit as st

from config.settings import DB_PATH, RAW_DATA_DIR
from database.repository import (
    get_all_investigations, get_experiments_df, get_findings, get_measurements_df,
)
from ui.data import CSV_BACKED, SEEDED, LABELS, csv_sources, document_sources
from scientific.evidence import source_index
from ingestion.file_loader import resolve_psi_folder


@st.cache_data(ttl=60, max_entries=2)
def load_catalog(mtime):
    investigations = get_all_investigations()
    runs = get_experiments_df()
    measurements = get_measurements_df()
    finds = get_findings()
    sources, _ = source_index(DB_PATH, RAW_DATA_DIR)
    def origin(row):
        item = sources.get(f"{row['psi_id']}:{row['test_id']}")
        if item and not item["ambiguous"]:
            try:
                raw = {k.strip(): v for k, v in json.loads(row["raw_attributes_json"]).items()}
                if raw == item["raw"]:
                    return CSV_BACKED
            except (ValueError, TypeError):
                pass
        return SEEDED
    runs["data_origin"] = [origin(row) for row in runs.to_dict("records")]
    origin = runs.set_index("test_id")["data_origin"].to_dict()
    measurements["data_origin"] = measurements["test_id"].map(origin).fillna(SEEDED)
    return investigations, runs, measurements, finds


def catalog():
    try:
        if not DB_PATH.is_file():
            raise FileNotFoundError
        return load_catalog(DB_PATH.stat().st_mtime_ns)
    except (sqlite3.Error, OSError, pd.errors.DatabaseError):
        st.error("The research database is unavailable. Restore data/database/research.db and reload.")
        st.stop()


def filtered_data(include_uploads=True):
    investigations, runs, measurements, findings = catalog()
    if include_uploads:
        for item in st.session_state.get("uploads", {}).values():
            runs = pd.concat([runs, item["runs"]], ignore_index=True)
            if not item["measurements"].empty:
                measurements = pd.concat([measurements, item["measurements"]], ignore_index=True)
    pillar = st.session_state.get("safety_pillar", "All")
    facility = st.session_state.get("facility", "All")
    facilities = None if facility == "All" else [facility]
    investigations = [i for i in investigations
                      if (pillar == "All" or i["safety_pillar"] in (pillar, "Multi"))
                      and (facilities is None or i["hardware_facility"] in facilities)]
    ids = {i["psi_id"] for i in investigations}
    return (investigations, runs[runs.psi_id.isin(ids)].copy(),
            measurements[measurements.psi_id.isin(ids)].copy(),
            [f for f in findings if f["psi_id"] in ids])


@st.cache_data(ttl=300, max_entries=20)
def local_sources(psi_id, doi, signature):
    folder = resolve_psi_folder(psi_id) or RAW_DATA_DIR / psi_id
    sources = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() == ".csv":
            sources.extend(csv_sources(path.read_bytes(), path.name, psi_id, doi))
        elif path.suffix.lower() in (".pdf", ".docx", ".txt"):
            sources.extend(document_sources(path.read_bytes(), path.name, psi_id, doi))
    return sources


def get_sources(investigation):
    folder = resolve_psi_folder(investigation["psi_id"]) or RAW_DATA_DIR / investigation["psi_id"]
    signature = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(folder.glob("*")) if p.is_file())
    return local_sources(investigation["psi_id"], investigation.get("doi"), signature)


def table(frame, **kwargs):
    if "parameter" in frame:
        from scientific.labels import name
        frame = frame.copy()
        frame["parameter"] = frame["parameter"].map(name)
    st.dataframe(frame.rename(columns=LABELS), hide_index=True, width="stretch", **kwargs)


def attribution(inv):
    st.markdown(f"[NASA PSI source]({inv['psi_url']}) · [DOI: {inv['doi']}](https://doi.org/{inv['doi']})")


def source_files(inv, prefix):
    folder = resolve_psi_folder(inv["psi_id"]) or RAW_DATA_DIR / inv["psi_id"]
    files = [p for p in sorted(folder.glob("*"))
             if p.suffix.lower() in (".csv", ".pdf", ".docx", ".txt")]
    if not files:
        st.caption("Original documents have not been added locally. Use the NASA PSI source link.")
    for path in files:
        st.download_button(path.name, path.read_bytes(), file_name=path.name,
                           key=f"{prefix}_{inv['psi_id']}_{path.name}")


def raw_record(row):
    st.caption("Original source values; empty fields remain unknown.")
    try:
        st.json(json.loads(row.get("raw_attributes_json") or "{}"))
    except (TypeError, ValueError):
        st.info("The original row is unavailable.")


def data_note():
    st.caption("Source CSV available ≠ every derived field verified. Catalog seeds and session uploads "
               "are not independently verified. Missing values stay unknown; backend outcomes may be inferred.")
