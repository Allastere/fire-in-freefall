"""Physical unit normalization using Pint and deterministic NASA PSI cleaning utilities."""

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
    "nm": "nanometer",
    "nanometer": "nanometer",
    "nanometers": "nanometer",
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "um": "micrometer",
    "µm": "micrometer",
    "μm": "micrometer",
    "micron": "micrometer",
    "microns": "micrometer",
    "micrometer": "micrometer",
    "micrometers": "micrometer",
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

_TIME_ALIASES: dict[str, str] = {
    "s": "second",
    "sec": "second",
    "secs": "second",
    "second": "second",
    "seconds": "second",
    "ms": "millisecond",
    "msec": "millisecond",
    "millisecond": "millisecond",
    "milliseconds": "millisecond",
    "min": "minute",
    "mins": "minute",
    "minute": "minute",
    "minutes": "minute",
    "hr": "hour",
    "hour": "hour",
}

_MASS_RATE_ALIASES: dict[str, str] = {
    "g/s": "gram / second",
    "g/sec": "gram / second",
    "mg/s": "milligram / second",
    "mg/sec": "milligram / second",
    "mg/min": "milligram / minute",
    "g/min": "gram / minute",
    "kg/s": "kilogram / second",
}

_HEAT_FLUX_ALIASES: dict[str, str] = {
    "kw/m2": "kilowatt / meter ** 2",
    "kw/m^2": "kilowatt / meter ** 2",
    "kw/m²": "kilowatt / meter ** 2",
    "w/cm2": "watt / centimeter ** 2",
    "w/cm^2": "watt / centimeter ** 2",
    "w/cm²": "watt / centimeter ** 2",
    "w/m2": "watt / meter ** 2",
    "w/m^2": "watt / meter ** 2",
    "w/m²": "watt / meter ** 2",
}


def normalize_pressure_to_psi(value: float, unit: str = "psi") -> float:
    """Convert pressure from atm, kPa, bar, Pa, torr, mmHg, or psi into psi via Pint."""
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


def normalize_diameter_to_nm(value: float, unit: str = "nm") -> float:
    """Convert particle diameter from nm, µm/micron, or mm into nm via Pint."""
    canonical = _LENGTH_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("nanometer").magnitude), 4)


def normalize_velocity_to_cm_s(value: float, unit: str = "cm/s") -> float:
    """Convert flow velocity from mm/s, cm/s, or m/s into cm/s via Pint."""
    canonical = _VELOCITY_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("cm/s").magnitude), 4)


def normalize_spread_rate_to_mm_s(value: float, unit: str = "mm/s") -> float:
    """Convert flame spread rate from cm/s, mm/s, or m/s into mm/s via Pint."""
    canonical = _VELOCITY_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("mm/s").magnitude), 4)


def normalize_time_to_s(value: float, unit: str = "s") -> float:
    """Convert time from ms, s, min, or hr into seconds via Pint."""
    canonical = _TIME_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("second").magnitude), 4)


def normalize_mass_rate_to_g_s(value: float, unit: str = "g/s") -> float:
    """Convert mass loss / flow / burning rate from mg/s, mg/min, g/min, or g/s into g/s via Pint."""
    canonical = _MASS_RATE_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("gram / second").magnitude), 6)


def normalize_heat_flux_to_kw_m2(value: float, unit: str = "kW/m2") -> float:
    """Convert heat flux from W/cm², W/m², or kW/m² into kW/m² via Pint."""
    canonical = _HEAT_FLUX_ALIASES.get(unit.strip().lower(), unit.strip())
    return round(float(Q_(value, canonical).to("kilowatt / meter ** 2").magnitude), 4)


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


def normalize_temperature_to_k(value: float, unit: str = "K") -> float:
    """Convert temperature from degC, degF, or K into Kelvin via Pint."""
    cleaned = unit.strip().lower()
    if cleaned in {"c", "degc", "°c", "celsius"}:
        src_unit = "degC"
    elif cleaned in {"f", "degf", "°f", "fahrenheit"}:
        src_unit = "degF"
    elif cleaned in {"k", "kelvin"}:
        src_unit = "kelvin"
    else:
        src_unit = unit.strip()
    return round(float(Q_(value, src_unit).to("kelvin").magnitude), 4)


def normalize_mole_fraction_to_pct(value: float, is_mole_fraction: bool = True) -> float:
    """Convert mole fraction (0..1) into volume/mole percentage (0..100%)."""
    if is_mole_fraction and 0.0 <= value <= 1.0:
        return round(value * 100.0, 4)
    return round(value, 4)


def parse_optional_float(raw_val: Any) -> float | None:
    """Safely parse numeric strings while treating 'none', empty strings, and NaN as None."""
    if raw_val is None:
        return None
    if isinstance(raw_val, float):
        return None if math.isnan(raw_val) else raw_val
    if isinstance(raw_val, int):
        return float(raw_val)
    text = str(raw_val).strip()
    if not text or text.lower() in {"none", "nan", "na", "n/a", "---", "------", "ramped", "insignificant"}:
        return None
    # Strip leading ~ or trailing units when simple float
    cleaned = re.sub(r"^~\s*", "", text)
    cleaned = re.sub(r"\s*(?:mm/s|cm/s|mm|cm|s|ms|w|atm|bar|%)$", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        val = float(cleaned)
        return None if math.isnan(val) else val
    except ValueError:
        return None


def parse_interval_or_float(raw_val: Any, unit: str = "s", target_unit: str = "s") -> dict[str, Any] | None:
    """Parse exact number or interval string like '5 - 10' or '21.5 - 21.7' without fabricating midpoints as exact."""
    if raw_val is None:
        return None
    text = str(raw_val).strip()
    if not text or text.lower() in {"none", "nan", "na", "n/a", "---"}:
        return None

    # Check interval pattern: "5 - 10", "22.1 to 22.0", "0.01 to 0.04"
    m_int = re.match(
        r"^~?\s*(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*([A-Za-z/%°µ]*)$",
        text,
        flags=re.IGNORECASE,
    )
    if m_int:
        v1 = float(m_int.group(1))
        v2 = float(m_int.group(2))
        lo, hi = min(v1, v2), max(v1, v2)
        if target_unit == "s" and unit != "s":
            lo = normalize_time_to_s(lo, unit)
            hi = normalize_time_to_s(hi, unit)
        return {
            "value": round((lo + hi) / 2.0, 4),
            "value_min": round(lo, 4),
            "value_max": round(hi, 4),
            "value_type": "interval",
        }

    approx = text.strip().startswith("~")
    val = parse_optional_float(text)
    if val is not None:
        if target_unit == "s" and unit != "s":
            val = normalize_time_to_s(val, unit)
        return {
            "value": round(val, 4),
            "value_min": None,
            "value_max": None,
            "value_type": "approximate" if approx else "exact",
        }
    return None


def parse_gmt_duration_s(gmt_start: Any, gmt_end: Any) -> float | None:
    """Calculate duration in seconds between two HH:MM:SS GMT strings (e.g. SPICE ignition to flame off)."""
    s1 = str(gmt_start or "").strip()
    s2 = str(gmt_end or "").strip()
    m1 = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?$", s1)
    m2 = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?$", s2)
    if not m1 or not m2:
        return None
    t1 = int(m1.group(1)) * 3600 + int(m1.group(2)) * 60 + int(m1.group(3))
    t2 = int(m2.group(1)) * 3600 + int(m2.group(2)) * 60 + int(m2.group(3))
    diff = t2 - t1
    if diff < 0:
        diff += 86400
    return float(diff) if 0 < diff <= 7200 else None


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
    ext_subtype = None
    if v_ext is not None:
        ext_subtype = "HIGH_FLOW_BLOWOFF" if (has_blowoff_marker or v_ext >= 15.0) else "LOW_FLOW_EXTINCTION"

    return {
        "flow_velocity_initial_cm_s": v_initial,
        "flow_velocity_min_cm_s": v_min,
        "flow_velocity_extinction_cm_s": v_ext,
        "extinction_subtype": ext_subtype,
        "flow_sequence_raw": air_str or (f"Fan: {fan_str}" if fan_str else None),
        "has_extinction_marker": has_extinction_marker,
        "has_blowoff_marker": has_blowoff_marker,
    }


def parse_fuel_sample_material(raw_material: Any, default_phase: str = "Solid") -> dict[str, Any]:
    """Normalize NASA Fuel Sample Material into canonical material name, family, fuel phase, geometry, and dimensions."""
    text = "" if raw_material is None else str(raw_material).strip()
    lower = text.lower()

    # Determine material name, normalized family, and fuel phase
    fuel_phase = default_phase
    if "pmma" in lower and "nomex" in lower:
        material_name = "PMMA & Nomex"
        material_family = "PMMA/Nomex Composite"
    elif "sibal" in lower or "75/25" in lower or ("cotton" in lower and "fiberglass" in lower):
        material_name = "SIBAL"
        material_family = "Cotton-Fiberglass (SIBAL)"
    elif "nomex" in lower:
        material_name = "Nomex III" if "iii" in lower else "Nomex"
        material_family = "Aramid (Nomex)"
    elif "kapton" in lower or "polyimide" in lower:
        material_name = "Kapton"
        material_family = "Polyimide (Kapton)"
    elif "teflon" in lower or "ptfe" in lower:
        material_name = "Teflon"
        material_family = "PTFE (Teflon)"
    elif "pyrell" in lower:
        material_name = "Pyrell Foam"
        material_family = "Polyurethane Foam (Pyrell)"
    elif "silicone" in lower:
        material_name = "Silicone"
        material_family = "Silicone Elastomer"
    elif "lamp wick" in lower or "lampwick" in lower or "cellulose" in lower or "kimwipe" in lower or "cotton" in lower:
        material_name = "Cellulose (Lamp Wick)"
        material_family = "Cellulose"
    elif "dibutyl" in lower or "dbp" in lower:
        material_name = "Dibutyl Phthalate"
        material_family = "Phthalate Ester"
    elif "candle" in lower or "wax" in lower:
        material_name = "Japan Wax"
        material_family = "Paraffin/Wax"
    elif "arizona road dust" in lower or "ard" in lower:
        material_name = "Arizona Road Dust (ARD)"
        material_family = "Calibration Dust (ARD)"
        fuel_phase = "Aerosol/Dust"
    elif "heptane" in lower or "c7h16" in lower:
        material_name = "n-Heptane"
        material_family = "Alkane (n-Heptane)"
        fuel_phase = "Liquid"
    elif "methanol" in lower or "ch3oh" in lower:
        material_name = "Methanol"
        material_family = "Alcohol (Methanol)"
        fuel_phase = "Liquid"
    elif "dodecane" in lower or "c12h26" in lower:
        material_name = "n-Dodecane"
        material_family = "Alkane (n-Dodecane)"
        fuel_phase = "Liquid"
    elif "decane" in lower or "c10h22" in lower:
        material_name = "n-Decane"
        material_family = "Alkane (n-Decane)"
        fuel_phase = "Liquid"
    elif "isooctane" in lower:
        material_name = "Iso-Octane"
        material_family = "Alkane (Iso-Octane)"
        fuel_phase = "Liquid"
    elif "octane" in lower:
        material_name = "n-Octane"
        material_family = "Alkane (n-Octane)"
        fuel_phase = "Liquid"
    elif "ethanol" in lower:
        material_name = "Ethanol"
        material_family = "Alcohol (Ethanol)"
        fuel_phase = "Liquid"
    elif "propanol" in lower:
        material_name = "1-Propanol"
        material_family = "Alcohol (Propanol)"
        fuel_phase = "Liquid"
    elif "toluene" in lower:
        material_name = "Toluene"
        material_family = "Aromatic (Toluene)"
        fuel_phase = "Liquid"
    elif "c2h4" in lower or "ethylene" in lower:
        material_name = "Ethylene (C2H4)"
        material_family = "Alkene Gas (Ethylene)"
        fuel_phase = "Gas"
    elif "ch4" in lower or "methane" in lower or "ch5" in lower:
        material_name = "Methane (CH4)"
        material_family = "Alkane Gas (Methane)"
        fuel_phase = "Gas"
    elif "c3h8" in lower or "propane" in lower:
        material_name = "Propane (C3H8)"
        material_family = "Alkane Gas (Propane)"
        fuel_phase = "Gas"
    elif "c4h10" in lower or "butane" in lower:
        material_name = "n-Butane (C4H10)"
        material_family = "Alkane Gas (n-Butane)"
        fuel_phase = "Gas"
    elif "c2h6" in lower or "ethane" in lower:
        material_name = "Ethane (C2H6)"
        material_family = "Alkane Gas (Ethane)"
        fuel_phase = "Gas"
    elif "h2" in lower or "hydrogen" in lower:
        material_name = "Hydrogen (H2)"
        material_family = "Hydrogen Gas"
        fuel_phase = "Gas"
    elif "pmma" in lower or "acrylic" in lower or "clear rod" in lower or "black rod" in lower:
        material_name = "PMMA"
        material_family = "Polymethyl Methacrylate (PMMA)"
    else:
        material_name = text if text else "PMMA"
        material_family = material_name if text else "Polymethyl Methacrylate (PMMA)"

    # Geometry determination
    if fuel_phase == "Liquid":
        geometry = "Droplet"
    elif fuel_phase == "Gas":
        geometry = "Porous Burner" if "sphere" in lower or "spherical" in lower else "Gaseous Burner"
    elif fuel_phase == "Aerosol/Dust":
        geometry = "Bulk/Dust"
    elif "spherical" in lower or "sphere" in lower:
        geometry = "Sphere"
    elif material_name in {"SIBAL", "Nomex III", "Nomex"} or "fabric" in lower:
        geometry = "Fabric"
    elif "wire" in lower or material_name in {"Kapton", "Teflon", "Cellulose (Lamp Wick)"}:
        geometry = "Wire/Insulation"
    elif "rod" in lower or "wax" in lower or "candle" in lower:
        geometry = "Rod"
    elif "slab" in lower:
        geometry = "Thick Slab"
    else:
        geometry = "Thin Film"

    thickness_mm: float | None = None
    width_cm: float | None = None
    diameter_mm: float | None = None
    length_cm: float | None = None

    # 1. Rod diameters in fractional or decimal inches (e.g., 1/4", 3/8", 1/2", 0.5", or "1/4 clear rod")
    frac_match = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:\"|in\b)?", lower)
    if frac_match and "75/25" not in lower:
        inches = float(frac_match.group(1)) / float(frac_match.group(2))
        diameter_mm = normalize_length_to_mm(inches, "inch")
    elif '0.5"' in lower or "0.5 in" in lower:
        diameter_mm = normalize_length_to_mm(0.5, "inch")

    # 2. Spherical diameter (e.g., '4 cm spherical section', '2 cm sphere')
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
        if mm_match and geometry not in {"Droplet", "Gaseous Burner", "Porous Burner"}:
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
        "material_family": material_family,
        "original_material_designation": text or material_name,
        "fuel_phase": fuel_phase,
        "geometry": geometry,
        "thickness_mm": thickness_mm,
        "width_cm": width_cm,
        "diameter_mm": diameter_mm,
        "length_cm": length_cm,
    }
