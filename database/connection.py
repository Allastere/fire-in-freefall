"""SQLite connection manager and 3-tier hybrid schema DDL with Cloud Run read-only resilience."""

import sqlite3
from pathlib import Path
from config.settings import DB_PATH

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS investigations (
    psi_id TEXT PRIMARY KEY,
    acronym TEXT NOT NULL,
    title TEXT NOT NULL,
    doi TEXT NOT NULL,
    psi_url TEXT NOT NULL,
    citation_text TEXT NOT NULL,
    safety_pillar TEXT NOT NULL CHECK (safety_pillar IN ('Prevention', 'Detection', 'Suppression', 'Multi')),
    fuel_category TEXT NOT NULL CHECK (fuel_category IN ('Solid', 'Liquid', 'Gas', 'Aerosol/Smoke')),
    hardware_facility TEXT NOT NULL CHECK (hardware_facility IN ('MSG', 'CIR', 'MDCA', 'Saffire/Cygnus')),
    objectives TEXT,
    summary TEXT,
    earth_spinoff_text TEXT,
    related_psi_ids TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS experiments (
    test_id TEXT PRIMARY KEY,
    psi_id TEXT NOT NULL,
    pi_name TEXT,
    sample_id TEXT,
    is_reused_sample BOOLEAN DEFAULT 0,
    flow_direction TEXT CHECK (flow_direction IN ('Opposed', 'Concurrent', 'Stagnation', 'Quiescent', 'Unknown')),
    outcome TEXT CHECK (outcome IN ('Sustained', 'Quenched', 'Blowoff', 'No Ignition', 'Unknown')),
    observations TEXT,
    raw_attributes_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT NOT NULL,
    material_name TEXT NOT NULL,
    geometry TEXT CHECK (geometry IN ('Thin Film', 'Thick Slab', 'Rod', 'Sphere', 'Fabric', 'Droplet', 'Porous Burner')),
    thickness_mm REAL,
    width_cm REAL,
    diameter_mm REAL,
    FOREIGN KEY (test_id) REFERENCES experiments(test_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT NOT NULL,
    o2_initial_pct REAL,
    o2_final_pct REAL,
    pressure_psi REAL DEFAULT 14.7,
    diluent_gas TEXT,
    diluent_pct REAL,
    flow_velocity_initial_cm_s REAL,
    flow_velocity_min_cm_s REAL,
    flow_velocity_extinction_cm_s REAL,
    flow_sequence_raw TEXT,
    gravity_level TEXT CHECK (gravity_level IN ('0g', '1g', 'Simulated Partial-g')),
    FOREIGN KEY (test_id) REFERENCES experiments(test_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    psi_id TEXT NOT NULL,
    test_id TEXT,
    parameter TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    is_over_range BOOLEAN DEFAULT 0,
    value_type TEXT DEFAULT 'exact' CHECK (value_type IN ('exact', 'approximate', 'threshold')),
    source_doc TEXT,
    source_page INTEGER,
    verification_status TEXT DEFAULT 'verified' CHECK (verification_status IN ('verified', 'needs_review', 'conflict')),
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES experiments(test_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    psi_id TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'Flammability Limit', 'Toxicity', 'Suppression', 'Detection',
        'Partial Gravity', 'Earth Spin-off', 'Hardware Link'
    )),
    claim TEXT NOT NULL,
    evidence_quote TEXT,
    source_doc TEXT,
    source_page INTEGER,
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sha256_hash TEXT UNIQUE NOT NULL,
    psi_id TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed',
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    psi_id TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS llm_cache (
    prompt_hash TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_experiments_psi_id ON experiments(psi_id);
CREATE INDEX IF NOT EXISTS idx_samples_test_id ON samples(test_id);
CREATE INDEX IF NOT EXISTS idx_conditions_test_id ON conditions(test_id);
CREATE INDEX IF NOT EXISTS idx_measurements_psi_test ON measurements(psi_id, test_id);
CREATE INDEX IF NOT EXISTS idx_measurements_param ON measurements(parameter);
CREATE INDEX IF NOT EXISTS idx_findings_psi_id ON findings(psi_id);
"""


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
