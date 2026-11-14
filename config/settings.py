"""Application paths, ranking formula weights, physical constants, and NASA mission profiles."""

from pathlib import Path
from typing import Any

BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
DB_DIR: Path = DATA_DIR / "database"
DB_PATH: Path = DB_DIR / "research.db"

GEMINI_MODEL: str = "gemini-3.5-flash-lite"

# Deterministic Research Relevance Score weights (Context.md Section 6.1):
# Score = 0.40 * S_scenario + 0.25 * S_completeness + 0.20 * S_evidence + 0.15 * S_comparability
RANKING_WEIGHTS: dict[str, float] = {
    "scenario": 0.40,
    "completeness": 0.25,
    "evidence": 0.20,
    "comparability": 0.15,
}

# Physical reference constants
STANDARD_PRESSURE_PSI: float = 14.7
STANDARD_O2_PCT: float = 21.0
MIN_0G_LOI_PCT: float = 13.5  # Minimum oxygen limit observed in 0g (BASS-II) vs 15.4-19% in 1g

GRAVITY_LEVELS_G: dict[str, float] = {
    "0g": 0.0,
    "Lunar (1/6g)": 0.166,
    "Martian (3/8g)": 0.376,
    "1g": 1.0,
}

# 4 Mission Profiles (Context.md Sections 6.1 & 7)
MISSION_PROFILES: dict[str, dict[str, Any]] = {
    "Lunar Base": {
        "key": "Lunar Base",
        "label": "Lunar Base / Pressurized Rover (≥30% O2, ≤10.2 psi, 1/6g)",
        "gravity_level": "Simulated Partial-g",
        "gravity_g": 0.166,
        "gravity_corridor": ("0g", "1g"),
        "target_o2_pct": 34.0,
        "min_o2_pct": 30.0,
        "target_pressure_psi": 8.2,
        "max_pressure_psi": 10.2,
        "target_flow_cm_s_range": (1.0, 15.0),
        "priority_pillars": ["Prevention", "Detection", "Multi"],
        "preferred_fuel_categories": ["Solid", "Aerosol/Smoke", "Gas"],
        "preferred_facilities": ["MSG", "CIR", "Saffire/Cygnus"],
        "description": (
            "Exploration atmosphere (≥30% O2, ≤10.2 psi) designed to reduce nitrogen pre-breathe time "
            "before EVA in 4.3 psi / 100% O2 suits; partial gravity (1/6g) bounded by the 0g–1g risk "
            "corridor, cabin polymer/fabric flammability, and lunar dust vs. smoke discrimination (SAME + DAFT)."
        ),
    },
    "ISS": {
        "key": "ISS",
        "label": "ISS / Deep Space Transit Spacecraft (21% O2, 14.7 psi, 0g)",
        "gravity_level": "0g",
        "gravity_g": 0.0,
        "gravity_corridor": ("0g", "0g"),
        "target_o2_pct": 21.0,
        "min_o2_pct": 18.0,
        "target_pressure_psi": 14.7,
        "max_pressure_psi": 15.2,
        "target_flow_cm_s_range": (1.0, 20.0),
        "priority_pillars": ["Prevention", "Detection", "Suppression", "Multi"],
        "preferred_fuel_categories": ["Solid", "Liquid", "Gas", "Aerosol/Smoke"],
        "preferred_facilities": ["MSG", "CIR", "MDCA", "Saffire/Cygnus"],
        "description": (
            "Microgravity (0g) spacecraft cabin environment at sea-level pressure (14.7 psi, ~21% O2) "
            "where buoyant convection vanishes and low HVAC ventilation flows (1–20 cm/s) sustain "
            "combustion down to 13.5% O2."
        ),
    },
    "Mars Habitat": {
        "key": "Mars Habitat",
        "label": "Martian Habitat (Elevated O2, 3/8g Corridor, Solid/Liquid Suppression)",
        "gravity_level": "Simulated Partial-g",
        "gravity_g": 0.376,
        "gravity_corridor": ("0g", "1g"),
        "target_o2_pct": 26.0,
        "min_o2_pct": 21.0,
        "target_pressure_psi": 10.2,
        "max_pressure_psi": 14.7,
        "target_flow_cm_s_range": (2.0, 25.0),
        "priority_pillars": ["Prevention", "Suppression", "Multi"],
        "preferred_fuel_categories": ["Solid", "Liquid", "Gas"],
        "preferred_facilities": ["MSG", "CIR", "MDCA", "Saffire/Cygnus"],
        "description": (
            "Long-duration Martian surface habitat at 3/8g (0.376g) within the 0g–1g partial-gravity "
            "convective-diffusive corridor, emphasizing solid/liquid fire suppression and material limits."
        ),
    },
    "Earth Spin-off": {
        "key": "Earth Spin-off",
        "label": "Terrestrial Fire Safety (Earth Spin-off, 1g Comparisons & Tech Transfer)",
        "gravity_level": "1g",
        "gravity_g": 1.0,
        "gravity_corridor": ("0g", "1g"),
        "target_o2_pct": 21.0,
        "min_o2_pct": 15.0,
        "target_pressure_psi": 14.7,
        "max_pressure_psi": 44.1,
        "target_flow_cm_s_range": (0.0, 50.0),
        "priority_pillars": ["Suppression", "Detection", "Prevention", "Multi"],
        "preferred_fuel_categories": ["Liquid", "Aerosol/Smoke", "Solid", "Gas"],
        "preferred_facilities": ["CIR", "MDCA", "MSG", "Saffire/Cygnus"],
        "description": (
            "1g vs. 0g baseline comparisons and terrestrial spinoffs: ISS fine-water-mist extinguishers, "
            "dust-immune early smoke detectors, Project FIRES firefighter turnout gear, and 4,500 psi "
            "composite SCBA breathing tanks."
        ),
    },
}
