"""SHA-256 file deduplication, source registry, and NASA PSI directory file discovery."""

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any
from config.settings import DB_PATH, RAW_DATA_DIR
from database.connection import get_connection

# Master file selection rule (Context.md Section 5.2 Rule 1): skip PI Excel matrix that duplicates master CSV
SKIPPED_DUPLICATE_FILES: set[str] = {
    "BASS-II Test Matrix by PI Final.xlsx",
}


def compute_sha256(file_path: Path | str) -> str:
    """Calculate SHA-256 digest of a file in chunks."""
    hasher = hashlib.sha256()
    with Path(file_path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_file_processed(sha256_hash: str, db_path: Path | str = DB_PATH) -> bool:
    """Return True if a file with this SHA-256 digest is already recorded as completed in sources."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM sources WHERE sha256_hash = ? AND status = 'completed'",
            (sha256_hash,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def register_file(
    file_path: Path | str,
    sha256_hash: str,
    psi_id: str,
    status: str = "completed",
    db_path: Path | str = DB_PATH,
) -> None:
    """Record processed file metadata into sources and processing_jobs tables."""
    path_str = str(Path(file_path))
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO sources (file_path, sha256_hash, psi_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sha256_hash) DO UPDATE SET
                    file_path = excluded.file_path,
                    psi_id = excluded.psi_id,
                    processed_at = CURRENT_TIMESTAMP,
                    status = excluded.status
                """,
                (path_str, sha256_hash, psi_id, status),
            )
            conn.execute(
                """
                INSERT INTO processing_jobs (file_path, sha256_hash, psi_id, status)
                VALUES (?, ?, ?, ?)
                """,
                (path_str, sha256_hash, psi_id, status),
            )
    except sqlite3.OperationalError:
        # Read-only container fallback
        pass
    finally:
        conn.close()


def resolve_psi_folder(psi_id: str, raw_root: Path | str = RAW_DATA_DIR) -> Path | None:
    """Resolve a folder in raw_root by exact psi_id ('PSI-25') or prefix ('PSI-25 Burning...')."""
    root = Path(raw_root)
    exact = root / psi_id
    if exact.is_dir():
        return exact
    for item in sorted(root.iterdir()):
        if item.is_dir() and (item.name == psi_id or item.name.startswith(psi_id + " ")):
            return item
    return None


def parse_doi_file(txt_path: Path | str) -> dict[str, str]:
    """Extract official citation text and normalized DOI from a NASA PSI DOI.txt file."""
    path = Path(txt_path)
    if not path.exists():
        return {"doi": "", "citation_text": ""}
    raw = ""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            raw = path.read_text(encoding=enc).strip()
            break
        except Exception:
            continue
    # Match standard 10.60555/xxxx-xxxx or malformed httpdoi.org10.60555xxxx-xxxx
    m = re.search(r"10\.60555/?([a-z0-9]{4}-[a-z0-9]{4})", raw, flags=re.IGNORECASE)
    doi = f"10.60555/{m.group(1).lower()}" if m else ""
    # Fix malformed URL inside citation text if present
    citation = re.sub(
        r"httpdoi\.org10\.60555([a-z0-9]{4}-[a-z0-9]{4})",
        r"https://doi.org/10.60555/\1",
        raw,
        flags=re.IGNORECASE,
    )
    return {"doi": doi, "citation_text": citation}


def discover_psi_files(psi_id: str = "PSI-25", raw_root: Path | str = RAW_DATA_DIR) -> dict[str, Any]:
    """Locate master CSVs, XLSX spreadsheets, summary PDFs, FAQ DOCXs, and DOI.txt for a PSI folder."""
    folder = resolve_psi_folder(psi_id, raw_root=raw_root)
    discovered: dict[str, Any] = {
        "folder": folder,
        "csv": None,
        "csv_files": [],
        "xlsx_files": [],
        "pdf": None,
        "pdf_files": [],
        "docx": None,
        "docx_files": [],
        "doi_txt": None,
    }
    if folder is None or not folder.exists():
        return discovered

    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name in SKIPPED_DUPLICATE_FILES:
            continue
        suffix = path.suffix.lower()
        if suffix == ".csv":
            discovered["csv_files"].append(path)
            if discovered["csv"] is None:
                discovered["csv"] = path
        elif suffix == ".xlsx":
            discovered["xlsx_files"].append(path)
        elif suffix == ".pdf":
            discovered["pdf_files"].append(path)
            if discovered["pdf"] is None:
                discovered["pdf"] = path
        elif suffix in {".docx", ".doc"}:
            discovered["docx_files"].append(path)
            if suffix == ".docx" and discovered["docx"] is None:
                discovered["docx"] = path
        elif suffix == ".txt":
            discovered["doi_txt"] = path

    return discovered
