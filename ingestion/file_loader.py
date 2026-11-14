"""SHA-256 file deduplication, source registry, and PSI-25 directory file discovery."""

import hashlib
import sqlite3
from pathlib import Path
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


def discover_psi_files(psi_id: str = "PSI-25", raw_root: Path | str = RAW_DATA_DIR) -> dict[str, Path | None]:
    """Locate master CSV, summary PDF, and FAQ DOCX files for a given PSI investigation folder."""
    folder = Path(raw_root) / psi_id
    discovered: dict[str, Path | None] = {"csv": None, "pdf": None, "docx": None}
    if not folder.exists():
        return discovered

    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name in SKIPPED_DUPLICATE_FILES:
            continue
        suffix = path.suffix.lower()
        if suffix == ".csv" and discovered["csv"] is None:
            discovered["csv"] = path
        elif suffix == ".pdf" and discovered["pdf"] is None:
            discovered["pdf"] = path
        elif suffix == ".docx" and discovered["docx"] is None:
            discovered["docx"] = path

    return discovered
