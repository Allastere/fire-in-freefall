"""SQLite connection manager and 3-tier hybrid schema DDL with Cloud Run read-only resilience."""

import sqlite3
from pathlib import Path
from config.settings import DB_PATH
from database.schema import SCHEMA_DDL


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory and foreign key enforcement."""
    resolved_path = Path(db_path)
    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Cloud Run read-only container fallback when directory already exists
        pass

    conn = sqlite3.connect(str(resolved_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.OperationalError:
        pass
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    """Create the 3-tier hybrid database schema idempotently."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_DDL)
    except sqlite3.OperationalError:
        # Read-only container environment where research.db is already pre-built
        pass
    finally:
        conn.close()


def get_cached_llm_response(prompt_hash: str, db_path: Path | str = DB_PATH) -> str | None:
    """Read a cached SI response from llm_cache by SHA-256 prompt_hash."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT response_json FROM llm_cache WHERE prompt_hash = ?",
            (prompt_hash,),
        ).fetchone()
        return str(row["response_json"]) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def save_cached_llm_response(
    prompt_hash: str,
    model_name: str,
    response_json: str,
    db_path: Path | str = DB_PATH,
) -> bool:
    """Persist an SI response into llm_cache, swallowing OperationalError in read-only Cloud Run."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache (prompt_hash, model_name, response_json, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (prompt_hash, model_name, response_json),
            )
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
