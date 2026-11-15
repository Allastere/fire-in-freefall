"""3-tier hybrid SQLite DDL for the 19 NASA PSI investigations, runs, conditions, measurements, and findings."""

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
    related_psi_ids TEXT DEFAULT '[]',
    pi_names TEXT DEFAULT '',
    pillar_classifications_json TEXT DEFAULT '[]',
    objective_tags_json TEXT DEFAULT '[]',
    hardware_relationships_json TEXT DEFAULT '{}',
    cross_relationships_json TEXT DEFAULT '[]',
    limitations_json TEXT DEFAULT '[]'
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
    geometry TEXT CHECK (geometry IN (
        'Thin Film', 'Thick Slab', 'Rod', 'Sphere', 'Fabric',
        'Droplet', 'Porous Burner', 'Gaseous Burner', 'Wire/Insulation', 'Bulk/Dust'
    )),
    thickness_mm REAL,
    width_cm REAL,
    diameter_mm REAL,
    original_material_designation TEXT,
    material_family TEXT,
    fuel_phase TEXT DEFAULT 'Solid',
    length_cm REAL,
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
    oxygen_location TEXT DEFAULT 'CHAMBER_AMBIENT',
    co2_diluent_pct REAL,
    he_diluent_pct REAL,
    n2_diluent_pct REAL,
    ambient_temp_k REAL,
    ignition_outcome TEXT DEFAULT 'UNKNOWN',
    propagation_outcome TEXT DEFAULT 'UNKNOWN',
    suppression_outcome TEXT DEFAULT 'UNKNOWN',
    material_behaviour TEXT DEFAULT 'NONE',
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
    value_type TEXT DEFAULT 'exact' CHECK (value_type IN (
        'exact', 'approximate', 'threshold', 'interval', 'upper_bound', 'lower_bound', 'censored_ft'
    )),
    source_doc TEXT,
    source_page INTEGER,
    verification_status TEXT DEFAULT 'verified' CHECK (verification_status IN ('verified', 'needs_review', 'conflict')),
    subtype TEXT,
    value_min REAL,
    value_max REAL,
    statistic_type TEXT DEFAULT 'EXACT_RUN',
    instrument TEXT,
    ignition_method TEXT,
    eligibility_status TEXT DEFAULT 'ML_ELIGIBLE' CHECK (eligibility_status IN ('ML_ELIGIBLE', 'EVIDENCE_ONLY', 'NEEDS_REVIEW')),
    source_trace_json TEXT DEFAULT '{}',
    FOREIGN KEY (psi_id) REFERENCES investigations(psi_id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES experiments(test_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    psi_id TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'Flammability Limit', 'Toxicity', 'Suppression', 'Detection',
        'Partial Gravity', 'Earth Spin-off', 'Hardware Link',
        'Research Limitation', 'Equipment Implication'
    )),
    claim TEXT NOT NULL,
    evidence_quote TEXT,
    source_doc TEXT,
    source_page INTEGER,
    finding_title TEXT DEFAULT '',
    finding_type TEXT DEFAULT 'DIRECT_EXPERIMENTAL',
    safety_pillar TEXT DEFAULT 'Prevention',
    objective_tag TEXT DEFAULT '',
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
CREATE INDEX IF NOT EXISTS idx_measurements_eligibility ON measurements(eligibility_status);
CREATE INDEX IF NOT EXISTS idx_findings_psi_id ON findings(psi_id);
"""
