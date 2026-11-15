"""Two-stage adaptive CSV schema mapper (deterministic dictionary + optional SI LLM callback)."""

import re
from typing import Any, Callable
from core.schemas import ColumnMappingPlan, ColumnMappingTarget

LLMMapperCallback = Callable[[list[str], list[dict[str, Any]], str], ColumnMappingPlan]

# Canonical parameter dictionary across the 3 NASA Fire Safety Pillars (Prevention, Detection, Suppression)
CANONICAL_PARAMETER_UNITS: dict[str, str] = {
    # Prevention
    "ignition_time_s": "s",
    "igniter_operation_duration_s": "s",
    "ignition_temperature_k": "K",
    "adiabatic_flame_temperature_k": "K",
    "burner_temperature_k": "K",
    "sample_pyrolysis_temperature_k": "K",
    "critical_ignition_heat_flux_kw_m2": "kW/m²",
    "incident_heat_flux_kw_m2": "kW/m²",
    "flame_spread_rate_mm_s": "mm/s",
    "oxygen_limit_pct": "%",
    "extinction_velocity_cm_s": "cm/s",
    "burning_duration_s": "s",
    "pyrolysis_heating_duration_s": "s",
    "mass_loss_rate_g_s": "g/s",
    "fuel_mass_flow_rate_g_s": "g/s",
    "mass_burning_rate_g_s": "g/s",
    "hrr_watts": "W",
    "ignition_power_watts": "W",
    "radiative_output": "raw",
    "burning_rate_constant_mm2_s": "mm2/s",
    "o2_initial_calibrated_pct": "%",
    "o2_final_calibrated_pct": "%",
    "co2_initial_pct": "%",
    "co2_final_pct": "%",
    "co_initial_ppm": "ppm",
    "co_final_ppm": "ppm",
    # Detection
    "smoke_particle_diameter_nm": "nm",
    "particle_number_concentration_cm3": "particles/cm³",
    "smoke_mass_concentration_mg_m3": "mg/m³",
    "detector_response_time_s": "s",
    "detection_threshold": "mixed",
    "detection_efficiency_pct": "%",
    "smoke_optical_property": "mixed",
    "aerosol_aging_time_s": "s",
    # Suppression
    "suppressant_concentration_pct": "%",
    "minimum_extinguishing_concentration_pct": "%",
    "extinguishing_time_s": "s",
    "reignition_time_s": "s",
    "extinction_droplet_diameter_mm": "mm",
}


def _normalize_header(header: str) -> str:
    """Lowercase, trim, and collapse whitespace for deterministic header matching."""
    return re.sub(r"\s+", " ", header.strip()).lower()


# Stage 1: Deterministic synonym rules (Context.md Section 5.1 & 5.2 + Expanded 3-Pillar Dictionary)
# Tuples of (regex_pattern, target_table, target_field, detected_unit)
_DETERMINISTIC_RULES: list[tuple[str, str, str, str | None]] = [
    (r"^(pi|pi_name|principal investigator)$", "experiments", "pi_name", None),
    (
        r"^(test\s*#|test\s*id|test\s*number|as-run test.*|as run test #|same test #|flex test #|flex number|test|session name|test point)$",
        "experiments",
        "test_id",
        None,
    ),
    (r"^(sample\s*#|sample\s*id|sample\s*number|flex identifier)$", "experiments", "sample_id", None),
    (r"^(flow\s*direction|direction|sample\s*distance\*?)$", "experiments", "flow_direction", None),
    (r"^(outcome|result|test end|self\s*-?\s*ext or flow term)$", "experiments", "outcome", None),
    (r"^(observations?|test observations.*|notes|comments|description)$", "experiments", "observations", None),
    (
        r"^(fuel\s*sample\s*material|sample\s*material|sample\s*type|material|fuel|fuel\s*type|sample\s*\(fuel type\)|fuel\s*bottle|fuel\s*descriptioin)$",
        "samples",
        "material_name",
        None,
    ),
    (r"^(sample\s*thickness.*|samle\s*thickness.*)$", "samples", "thickness_mm", "cm"),
    (r"^(sample\s*width.*)$", "samples", "width_cm", "cm"),
    (r"^(sample\s*length.*)$", "samples", "length_cm", "cm"),
    (
        r"^(droplet\s*initial\s*diameter.*|initial\s*droplet\s*diameter.*|d0\s*\(\s*mm\s*\)|nozzle\s*\(mm\)|burner\s*size\s*\(mm\))$",
        "samples",
        "diameter_mm",
        "mm",
    ),
    # Rule 2 (Section 5.2): Strictly prefer Calibrated O2 columns; ignore uncalibrated O2 columns
    (r"^calibrated\s+initial\s+o2.*$", "conditions", "o2_initial_pct", "%"),
    (r"^calibrated\s+final\s+o2.*$", "conditions", "o2_final_pct", "%"),
    (r"^(initial\s+o2.*|final\s+o2.*)$", "ignore", "uncalibrated_o2", "%"),
    (
        r"^(xo2|xo2\s*\(init\)|xo2\s*before\s*test|o\s*initial\s*ambient\s*composition.*|oxygen\s*mole\s*fraction|oxygen)$",
        "conditions",
        "o2_initial_pct",
        "mole_fraction",
    ),
    (r"^(xo2\s*\(final\)|xo2\s*after\s*test)$", "conditions", "o2_final_pct", "mole_fraction"),
    (r"^(percent\s*o2.*|oxygen\s*conc.*|o2_pct|o2\s*%)$", "conditions", "o2_initial_pct", "%"),
    (r"^(pressure|p_psi|pressure_psi)$", "conditions", "pressure_psi", "psi"),
    (r"^(p_atm|pinit\s*\(atm\)|pmean\s*\(atm\)|ambient\s*pressure\s*\(atm\)|pressure\s*\(atm\))$", "conditions", "pressure_psi", "atm"),
    (r"^(approx\s*p\s*\(bar\))$", "conditions", "pressure_psi", "bar"),
    (r"^(ambient\s*pressure;\s*mmhg)$", "conditions", "pressure_psi", "mmHg"),
    (
        r"^(air\s*display|air\s*flow.*|air\s*rate.*|inlet\s*velocity.*|flow\s*velocity.*|flow\s*rate|v_air|duct\s*velocity.*)$",
        "conditions",
        "flow_velocity_initial_cm_s",
        "cm/s",
    ),
    (r"^diluent.*|ambient\s*gas\s*mixture.*$", "conditions", "diluent_gas", None),
    (r"^gravity.*$", "conditions", "gravity_level", None),
    # Gas emissions & suppressant concentrations
    (r"^initial\s+co2.*$", "measurements", "co2_initial_pct", "%"),
    (r"^final\s+co2.*$", "measurements", "co2_final_pct", "%"),
    (r"^initial\s+co\b.*$", "measurements", "co_initial_ppm", "ppm"),
    (r"^final\s+co\b.*$", "measurements", "co_final_ppm", "ppm"),
    (r"^(co\s*initial\s*ambient\s*composition;\s*mole\s*fraction)$", "measurements", "suppressant_concentration_pct", "mole_fraction_co2"),
    (r"^(he\s*initial\s*ambient\s*composition;\s*mole\s*fraction|helium)$", "measurements", "suppressant_concentration_pct", "mole_fraction_he"),
    (r"^(n\s*initial\s*ambient\s*composition;\s*mole\s*fraction|nitrogen)$", "measurements", "suppressant_concentration_pct", "mole_fraction_n2"),
    # 10 Prevention + Detection + Suppression canonical parameters
    (r"^(ignition\s*time\s*\(\s*s\s*\)|ignition\s*time\s*-\s*seconds|time\s*to\s*ignition|tti)$", "measurements", "ignition_time_s", "s"),
    (r"^(ignition\s*time\s*\(\s*ms\s*\))$", "measurements", "igniter_operation_duration_s", "ms"),
    (r"^(ignition\s*temperature.*|autoignition\s*temperature.*)$", "measurements", "ignition_temperature_k", "K"),
    (r"^(tad\s*\(k\))$", "measurements", "adiabatic_flame_temperature_k", "K"),
    (r"^(peak\s*burner\s*temp\s*\(k\))$", "measurements", "burner_temperature_k", "K"),
    (r"^(peak\s*burner\s*t(?:emp)?\s*\(\s*c\s*\))$", "measurements", "burner_temperature_k", "degC"),
    (r"^(critical\s*heat\s*flux.*|critical\s*ignition\s*heat\s*flux.*)$", "measurements", "critical_ignition_heat_flux_kw_m2", "kW/m²"),
    (
        r"^(spread\s*rate|vf|flame_spread_rate.*|1-g\s*spread\s*rate|.?-g\s*spread\s*length)$",
        "measurements",
        "flame_spread_rate_mm_s",
        "mm/s",
    ),
    (r"^(loi|limiting\s*oxygen\s*index.*|oxygen\s*limit.*)$", "measurements", "oxygen_limit_pct", "%"),
    (r"^(extinction\s*velocity.*|blowoff\s*velocity.*)$", "measurements", "extinction_velocity_cm_s", "cm/s"),
    (r"^(burn\s*time\s*\(s\)|burn\s*time\s*\(sec\)|burn\s*time;\s*s|hf\s*burn\s*time)$", "measurements", "burning_duration_s", "s"),
    (r"^(duration\s*\(sec\))$", "measurements", "pyrolysis_heating_duration_s", "s"),
    (r"^(weight\s*loss\s*rate\s*\(mg/min\)|mass\s*loss\s*rate.*)$", "measurements", "mass_loss_rate_g_s", "mg/min"),
    (r"^(fuel\s*rate\s*\(mg/s\)|hc\s*fuel\s*rate\s*\(mg/s\)|mfuel\s*\(mg/s\)|mhc\s*\(mg/s\))$", "measurements", "fuel_mass_flow_rate_g_s", "mg/s"),
    (r"^(hc\s*burnrate\s*\(mg/s\)|mass\s*burning\s*rate.*)$", "measurements", "mass_burning_rate_g_s", "mg/s"),
    (r"^(hrr|heat\s*release\s*rate.*)$", "measurements", "hrr_watts", "W"),
    (r"^(ignition\s*power\s*\(\s*w\s*\))$", "measurements", "ignition_power_watts", "W"),
    (r"^(peak\s*hf\s*rad)$", "measurements", "radiative_output", "raw"),
    (r"^(k_burn|burning\s*rate\s*constant.*|burning\s*rate;\s*mm|khot\s*\(\s*mm\^2/s\s*\)|kcool\s*\(\s*mm\^2/s\s*\))$", "measurements", "burning_rate_constant_mm2_s", "mm2/s"),
    (r"^(primary\s*aging\s*time\s*\(sec\)|primary\s*mixing\s*time\s*\(sec\)|net\s*aging\s*time\s*\(sec\))$", "measurements", "aerosol_aging_time_s", "s"),
    (r"^(aging\s*duration\s*\(minutes\))$", "measurements", "aerosol_aging_time_s", "min"),
    (r"^(visible\s*flame\s*extinction\s*diameter;\s*mm|dext,\s*hot\s*\(\s*mm\s*\)|dext,cool\s*\(\s*mm\s*\))$", "measurements", "extinction_droplet_diameter_mm", "mm"),
]


def map_csv_columns(
    headers: list[str],
    sample_rows: list[dict[str, Any]],
    psi_id: str,
    llm_callback: LLMMapperCallback | None = None,
) -> ColumnMappingPlan:
    """Map raw CSV headers to canonical database targets using Stage 1 rules + optional Stage 2 LLM callback."""
    mappings: list[ColumnMappingTarget] = []
    unmapped: list[str] = []

    for raw_col in headers:
        norm = _normalize_header(raw_col)
        matched = False
        for pattern, target_table, target_field, unit in _DETERMINISTIC_RULES:
            if re.match(pattern, norm):
                mappings.append(
                    ColumnMappingTarget(
                        raw_column=raw_col,
                        target_table=target_table,  # type: ignore[arg-type]
                        target_field=target_field,
                        detected_unit=unit,
                        confidence=1.0,
                    )
                )
                matched = True
                break
        if not matched:
            unmapped.append(raw_col)

    # Stage 2: Optional LLM callback receives ONLY unmapped headers + first 2-3 sample rows
    if unmapped and llm_callback is not None:
        llm_plan = llm_callback(unmapped, sample_rows[:3], psi_id)
        mapped_by_llm = {m.raw_column for m in llm_plan.mappings}
        mappings.extend(llm_plan.mappings)
        unmapped = [col for col in unmapped if col not in mapped_by_llm]

    return ColumnMappingPlan(
        psi_id=psi_id,
        mappings=mappings,
        unmapped_columns=unmapped,
    )
