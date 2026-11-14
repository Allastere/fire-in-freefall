"""Two-stage adaptive CSV schema mapper (deterministic dictionary + optional SI LLM callback)."""

import re
from typing import Any, Callable
from core.schemas import ColumnMappingPlan, ColumnMappingTarget

LLMMapperCallback = Callable[[list[str], list[dict[str, Any]], str], ColumnMappingPlan]


def _normalize_header(header: str) -> str:
    """Lowercase, trim, and collapse whitespace for deterministic header matching."""
    return re.sub(r"\s+", " ", header.strip()).lower()


# Stage 1: Deterministic synonym rules (Context.md Section 5.1 & 5.2)
# Tuples of (regex_pattern, target_table, target_field, detected_unit)
_DETERMINISTIC_RULES: list[tuple[str, str, str, str | None]] = [
    (r"^(pi|pi_name|principal investigator)$", "experiments", "pi_name", None),
    (r"^(test\s*#|test\s*id|test\s*number|as-run test.*)$", "experiments", "test_id", None),
    (r"^(sample\s*#|sample\s*id|sample\s*number)$", "experiments", "sample_id", None),
    (r"^(flow\s*direction|sample\s*distance)$", "experiments", "flow_direction", None),
    (r"^(outcome|result)$", "experiments", "outcome", None),
    (r"^(observations?|test observations.*)$", "experiments", "observations", None),
    (r"^(fuel\s*sample\s*material|material|fuel)$", "samples", "material_name", None),
    # Rule 2 (Section 5.2): Strictly prefer Calibrated O2 columns; ignore uncalibrated O2 columns
    (r"^calibrated\s+initial\s+o2.*$", "conditions", "o2_initial_pct", "%"),
    (r"^calibrated\s+final\s+o2.*$", "conditions", "o2_final_pct", "%"),
    (r"^(initial\s+o2.*|final\s+o2.*)$", "ignore", "uncalibrated_o2", "%"),
    (r"^(xo2|o2_pct|o2\s*%)$", "conditions", "o2_initial_pct", "%"),
    (r"^(pressure|p_psi|pressure_psi)$", "conditions", "pressure_psi", "psi"),
    (r"^p_atm$", "conditions", "pressure_psi", "atm"),
    (r"^(air\s*display|flow\s*rate|v_air|duct\s*velocity.*)$", "conditions", "flow_velocity_initial_cm_s", "cm/s"),
    (r"^diluent.*$", "conditions", "diluent_gas", None),
    (r"^gravity.*$", "conditions", "gravity_level", None),
    (r"^initial\s+co2.*$", "measurements", "co2_initial_pct", "%"),
    (r"^final\s+co2.*$", "measurements", "co2_final_pct", "%"),
    (r"^initial\s+co\b.*$", "measurements", "co_initial_ppm", "ppm"),
    (r"^final\s+co\b.*$", "measurements", "co_final_ppm", "ppm"),
    (r"^(spread\s*rate|vf|flame_spread_rate.*)$", "measurements", "flame_spread_rate_mm_s", "mm/s"),
    (r"^(k_burn|burning\s*rate\s*constant.*)$", "measurements", "burning_rate_constant_mm2_s", "mm2/s"),
    (r"^(loi|limiting\s*oxygen\s*index.*)$", "measurements", "limiting_oxygen_index_pct", "%"),
    (r"^(hrr|heat\s*release\s*rate.*)$", "measurements", "hrr_watts", "W"),
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
