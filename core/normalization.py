"""Physical unit normalization using Pint and deterministic NASA PSI-25 cleaning utilities."""

import math
import re
from typing import Any
from pint import UnitRegistry

ureg = UnitRegistry()
Q_ = ureg.Quantity

_PRESSURE_ALIASES: dict[str, str] = {
    "psi": "psi",
    "psia": "psi",
    "atm": "atm",
    "kpa": "kPa",
    "pa": "Pa",
    "bar": "bar",
    "mbar": "mbar",
    "torr": "torr",
    "mmhg": "mmHg",
}

_LENGTH_ALIASES: dict[str, str] = {
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "um": "micrometer",
    "µm": "micrometer",
    "micron": "micrometer",
    "microns": "micrometer",
    "in": "inch",
    "inch": "inch",
    "inches": "inch",
    '"': "inch",
}

_VELOCITY_ALIASES: dict[str, str] = {
    "cm/s": "cm/s",
    "cm/sec": "cm/s",
    "mm/s": "mm/s",
    "mm/sec": "mm/s",
    "m/s": "m/s",
    "m/sec": "m/s",
}


def normalize_pressure_to_psi(value: float, unit: str = "psi") -> float:
    """Convert pressure from atm, kPa, bar, Pa, torr, or psi into psi via Pint."""
    canonical = _PRESSURE_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("psi").magnitude), 4)


def normalize_length_to_mm(value: float, unit: str = "mm") -> float:
    """Convert length from micron/µm, mm, cm, m, or inch into mm via Pint."""
    canonical = _LENGTH_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("mm").magnitude), 4)


def normalize_length_to_cm(value: float, unit: str = "cm") -> float:
    """Convert length from mm, cm, m, or inch into cm via Pint."""
    canonical = _LENGTH_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("cm").magnitude), 4)


def normalize_velocity_to_cm_s(value: float, unit: str = "cm/s") -> float:
    """Convert flow velocity from mm/s, cm/s, or m/s into cm/s via Pint."""
    canonical = _VELOCITY_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("cm/s").magnitude), 4)


def normalize_temperature_to_c(value: float, unit: str = "degC") -> float:
    """Convert temperature from K, degF, or degC into degrees Celsius via Pint."""
    cleaned = unit.strip().lower()
    if cleaned in {"c", "degc", "°c", "celsius"}:
        src_unit = "degC"
    elif cleaned in {"f", "degf", "°f", "fahrenheit"}:
        src_unit = "degF"
    elif cleaned in {"k", "kelvin"}:
        src_unit = "kelvin"
    else:
        src_unit = unit.strip()
    return round(float(Q_(value, src_unit).to("degC").magnitude), 4)


def parse_optional_float(raw_val: Any) -> float | None:
    """Safely parse numeric strings while treating 'none', empty strings, and NaN as None."""
    if raw_val is None:
        return None
    if isinstance(raw_val, float):
        return None if math.isnan(raw_val) else raw_val
    if isinstance(raw_val, int):
        return float(raw_val)
    text = str(raw_val).strip()
    if not text or text.lower() in {"none", "nan", "na", "n/a", "---", "------"}:
        return None
    try:
        val = float(text)
        return None if math.isnan(val) else val
    except ValueError:
        return None


def parse_co_value(raw_val: Any) -> tuple[float | None, bool, str]:
    """Parse NASA CSA-CP CO readings handling 'OR', '+OR', 'over', '>500', and zero-drift negatives.

    Returns:
        (normalized_ppm, is_over_range, value_type)
    """
    if raw_val is None:
        return None, False, "exact"
    if isinstance(raw_val, float) and math.isnan(raw_val):
        return None, False, "exact"

    text = str(raw_val).strip()
    if not text or text.lower() in {"none", "nan", "na", "n/a", "---"}:
        return None, False, "exact"

    lowered = text.lower()
    if lowered in {"or", "+or", "over", "over range", "overrange"}:
        return 1000.0, True, "threshold"

    if lowered.startswith(">"):
        num = parse_optional_float(lowered[1:].strip())
        if num is not None:
            return num, True, "threshold"

    num = parse_optional_float(text)
    if num is not None:
        # Initial CO readings occasionally show -1/-2/-3 ppm sensor zero drift; clamp physical ppm >= 0
        return max(0.0, num), False, "exact"

    return None, False, "exact"


def parse_air_display(raw_air: Any, raw_fan: Any = None) -> dict[str, Any]:
    """Extract initial, minimum, and extinction airflow velocities (cm/s) from NASA Air display strings."""
    air_str = "" if raw_air is None or (isinstance(raw_air, float) and math.isnan(raw_air)) else str(raw_air).strip()
    fan_str = "" if raw_fan is None or (isinstance(raw_fan, float) and math.isnan(raw_fan)) else str(raw_fan).strip()

    combined_lower = f"{air_str} {fan_str}".lower()
    has_extinction_marker = bool(
        re.search(r"(\bext\b|\bextinguished\b|\bextinction\b|\bquench\w*\b|\bout\b|\d+\s*ext\b)", combined_lower)
    )
    has_blowoff_marker = "blowoff" in combined_lower or "blew out" in combined_lower

    # Clean potentiometer notes so pot voltages are not mistaken for cm/s velocities
    cleaned = air_str
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*pots?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpots?\b.*$", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*1\b", "0.5", cleaned)

    velocities: list[float] = []
    if cleaned and "no ign" not in cleaned.lower():
        for match in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?=[A-Za-z\s,;>?/]|$)", cleaned):
            val = float(match)
            if 0.0 <= val <= 100.0:
                velocities.append(val)

    # Fallback: when Air display is blank or 'see fan', check Fan display for explicit cm/s or initial 5 cm/s
    if not velocities and fan_str:
        cm_s_matches = re.findall(r"(\d+(?:\.\d+)?)\s*cm/s", fan_str, flags=re.IGNORECASE)
        if cm_s_matches:
            velocities = [float(x) for x in cm_s_matches]
        elif re.match(r"^\s*5\b", fan_str):
            velocities = [5.0]

    v_initial = velocities[0] if velocities else None
    v_min = min(velocities) if velocities else None
    v_ext = v_min if (has_extinction_marker and v_min is not None) else None

    return {
        "flow_velocity_initial_cm_s": v_initial,
        "flow_velocity_min_cm_s": v_min,
        "flow_velocity_extinction_cm_s": v_ext,
        "flow_sequence_raw": air_str or (f"Fan: {fan_str}" if fan_str else None),
        "has_extinction_marker": has_extinction_marker,
        "has_blowoff_marker": has_blowoff_marker,
    }


def parse_fuel_sample_material(raw_material: Any) -> dict[str, Any]:
    """Normalize NASA Fuel Sample Material into canonical material name, geometry, and mm/cm dimensions."""
    text = "" if raw_material is None else str(raw_material).strip()
    lower = text.lower()

    if "sibal" in lower or "75/25" in lower or "cotton" in lower:
        material_name = "SIBAL"
    elif "nomex" in lower:
        material_name = "Nomex III"
    elif "candle" in lower or "wax" in lower:
        material_name = "Japan Wax"
    else:
        material_name = "PMMA"

    # Geometry determination
    if "spherical" in lower or "sphere" in lower:
        geometry = "Sphere"
    elif material_name in {"SIBAL", "Nomex III"}:
        geometry = "Fabric"
    elif "rod" in lower or "wax" in lower or "candle" in lower:
        geometry = "Rod"
    elif "slab" in lower:
        geometry = "Thick Slab"
    else:
        # Check thickness threshold for PMMA sheets/films (>= 1 mm -> Thick Slab, < 1 mm -> Thin Film)
        geometry = "Thin Film"

    thickness_mm: float | None = None
    width_cm: float | None = None
    diameter_mm: float | None = None

    # 1. Rod diameters in fractional or decimal inches (e.g., 1/4", 3/8", 1/2", 0.5", or "1/4 clear rod")
    frac_match = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:\"|in\b)?", lower)
    if frac_match and "75/25" not in lower:
        inches = float(frac_match.group(1)) / float(frac_match.group(2))
        diameter_mm = normalize_length_to_mm(inches, "inch")
    elif '0.5"' in lower or "0.5 in" in lower:
        diameter_mm = normalize_length_to_mm(0.5, "inch")

    # 2. Spherical diameter (e.g., '4 cm spherical section')
    if geometry == "Sphere":
        sph_cm = re.search(r"(\d+(?:\.\d+)?)\s*cm\b", lower)
        if sph_cm:
            diameter_mm = normalize_length_to_mm(float(sph_cm.group(1)), "cm")

    # 3. Thickness in micron or mm
    micron_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:micron|µm|um)\b", lower)
    if micron_match:
        thickness_mm = normalize_length_to_mm(float(micron_match.group(1)), "micron")
    else:
        mm_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\b", lower)
        if mm_match:
            thickness_mm = normalize_length_to_mm(float(mm_match.group(1)), "mm")
            if thickness_mm >= 1.0 and geometry == "Thin Film":
                geometry = "Thick Slab"

    # 4. Width in cm (excluding spherical diameter)
    if geometry != "Sphere":
        cm_match = re.search(r"(\d+(?:\.\d+)?)\s*cm\b", lower)
        if cm_match:
            width_cm = normalize_length_to_cm(float(cm_match.group(1)), "cm")

    return {
        "material_name": material_name,
        "geometry": geometry,
        "thickness_mm": thickness_mm,
        "width_cm": width_cm,
        "diameter_mm": diameter_mm,
    }
