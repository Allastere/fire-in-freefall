"""Scientific display names shared by the service and the editorial interface."""

NAMES = {
    "co2_final_pct": "Final CO₂ concentration", "co2_initial_pct": "Initial CO₂ concentration",
    "co_final_ppm": "Final carbon monoxide concentration", "co_initial_ppm": "Initial carbon monoxide concentration",
    "o2_initial_calibrated_pct": "Initial calibrated oxygen", "o2_final_calibrated_pct": "Final calibrated oxygen",
    "flame_spread_rate_mm_s": "Flame spread rate", "burning_rate_constant_mm2_s": "Burning rate constant",
    "limiting_oxygen_index_pct": "Limiting oxygen index", "hrr_watts": "Heat release rate",
    "flow_velocity_extinction_cm_s": "Extinction airflow", "extinction_velocity_cm_s": "Extinction airflow velocity",
    "smoke_particle_diameter_nm": "Smoke particle diameter", "o2_initial_pct": "Oxygen concentration",
    "pressure_psi": "Pressure", "gravity_g": "Gravity", "flow_velocity_initial_cm_s": "Initial airflow velocity",
    "flow_direction": "Airflow direction", "geometry": "Sample geometry", "thickness_mm": "Thickness",
    "width_cm": "Width", "diameter_mm": "Diameter", "burn_sides": "Burn sides", "is_reused_sample": "Specimen reuse",
    "flow_sequence_raw": "Recorded airflow sequence", "material_name": "Material",
}
UNITS = {"o2_initial_pct": "%", "pressure_psi": "psi", "gravity_g": "g",
         "flow_velocity_initial_cm_s": "cm/s", "thickness_mm": "mm", "width_cm": "cm",
         "diameter_mm": "mm", "co2_initial_pct": "%"}


def name(key):
    return NAMES.get(key, key.replace("_", " ").capitalize())
