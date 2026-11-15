"""Lightweight pypdf parser for NASA technical reports, BASS-II Appendix A, and PDF tabular data."""

import json
import re
from pathlib import Path
from typing import Any
from pypdf import PdfReader
from core.normalization import (
    normalize_diameter_to_nm,
    normalize_heat_flux_to_kw_m2,
    normalize_mass_rate_to_g_s,
    normalize_spread_rate_to_mm_s,
)
from core.schemas import MeasurementModel

_CAMERA_METADATA_MARKERS: tuple[str, ...] = (
    "Exposure Mode",
    "Exposure compensation",
    "Bracket frames",
    "Shutter speed",
    "Shutter hold",
    "F stop",
    "ISO",
    "SD card",
    "Secure digital",
    "Release mode",
    "Filter (Y/N)",
)

_SKIP_SECTION_MARKERS: tuple[str, ...] = (
    "References",
    "Presentations and Publications",
    "Publications",
)


def _clean_pdf_text(text: str) -> str:
    """Normalize PDF line breaks and filter camera header noise."""
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(marker.lower() in stripped.lower() for marker in _CAMERA_METADATA_MARKERS):
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _extract_observation_tail(row_block: str) -> str:
    """Extract the descriptive Test observations and anomalies text after sensor columns."""
    tail_match = re.search(
        r"(?:\bNA\b|---|\+?OR|over|[-+]?\d+(?:\.\d+)?)\s+"
        r"(?:\bNA\b|---|\+?OR|over|[-+]?\d+(?:\.\d+)?)\s+"
        r"([A-Z][A-Za-z0-9,.;:()'\"/\-\s%°µ]+)$",
        row_block.strip(),
    )
    if tail_match:
        obs = re.sub(r"\s+", " ", tail_match.group(1)).strip()
        obs = re.split(r"\b[a-h](?:Greenwich|Manual|Continuous|Exposure|Number|Bracket)\b", obs)[0].strip()
        return obs[:400]
    return ""


def parse_bass2_appendix_a(pdf_path: Path | str) -> dict[str, dict[str, Any]]:
    """Extract per-test flow_direction, observations, and report source_page from Appendix A (Tables A.1–A.6)."""
    path = Path(pdf_path)
    if not path.exists():
        return {}

    reader = PdfReader(str(path))
    test_metadata: dict[str, dict[str, Any]] = {}

    row_pattern = re.compile(
        r"(?:^|\s)(?:[-0-9]+|---+|NA)\s+"
        r"([BFMOP]\d+[ab]?|T\d+[ab]?)\s+"
        r"(?:\d+[mML]?|---)\s+"
        r".{1,220}?"
        r"(?<!\w)(Opposed|Concurrent|Stagnation|\?)(?!\w)",
        flags=re.DOTALL,
    )

    for page_idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        if "Appendix A" not in raw_text and "TABLE A." not in raw_text:
            continue

        header_line = raw_text.splitlines()[0] if raw_text else ""
        if any(sec.lower() in header_line.lower() for sec in _SKIP_SECTION_MARKERS):
            continue

        tm_match = re.search(r"NASA/TM-\S+\s+(\d+)", raw_text)
        report_page = int(tm_match.group(1)) if tm_match else (page_idx + 1)

        cleaned = _clean_pdf_text(raw_text)
        matches = list(row_pattern.finditer(cleaned))

        for i, match in enumerate(matches):
            test_id = match.group(1).strip()
            raw_dir = match.group(2).strip()
            flow_direction = "Unknown" if raw_dir == "?" else raw_dir

            start_pos = match.end()
            end_pos = matches[i + 1].start() if (i + 1) < len(matches) else min(len(cleaned), start_pos + 700)
            row_tail = cleaned[start_pos:end_pos]
            observations = _extract_observation_tail(row_tail)

            test_metadata[test_id] = {
                "flow_direction": flow_direction,
                "observations": observations,
                "source_page": report_page,
                "source_doc": path.name,
            }

    return test_metadata


def extract_verified_pdf_measurements() -> list[MeasurementModel]:
    """Return scientifically verified tabular and text measurements from NASA PSI PDF reports.

    Follows all audit rules:
    - Aggregate material-level smoke particle diameters (SAME p.27, SAME-R p.78) have test_id=None
      and eligibility_status='EVIDENCE_ONLY', preserving GMD/CMD/AMD/MMD statistics and instruments.
    - Flight-specific TEM/Moment comparison rows in SAME-R Table 2 (p.16) link to their exact SAME-R test_id.
    - DAFT-3/4 tabular P-Trak & DustTrak rows (p.11, Fig. 5) are tagged with subtype='ARD_CALIBRATION_DUST'.
    - Literature, model, and upper-bound values are strictly separated from direct experimental runs.
    """
    measurements: list[MeasurementModel] = []

    def _add(
        psi_id: str,
        test_id: str | None,
        parameter: str,
        value: float,
        unit: str,
        source_doc: str,
        source_page: int,
        subtype: str | None = None,
        value_type: str = "exact",
        value_min: float | None = None,
        value_max: float | None = None,
        statistic_type: str = "EXACT_RUN",
        instrument: str | None = None,
        ignition_method: str | None = None,
        eligibility_status: str = "ML_ELIGIBLE",
        trace_meta: dict[str, Any] | None = None,
    ) -> None:
        trace = {
            "psi_id": psi_id,
            "source_doc": source_doc,
            "source_page": source_page,
            "subtype": subtype,
            "statistic_type": statistic_type,
            "instrument": instrument,
            **(trace_meta or {}),
        }
        measurements.append(
            MeasurementModel(
                psi_id=psi_id,
                test_id=test_id,
                parameter=parameter,
                value=value,
                unit=unit,
                is_over_range=False,
                value_type=value_type,  # type: ignore[arg-type]
                source_doc=source_doc,
                source_page=source_page,
                verification_status="verified",
                subtype=subtype,
                value_min=value_min,
                value_max=value_max,
                statistic_type=statistic_type,
                instrument=instrument,
                ignition_method=ignition_method,
                eligibility_status=eligibility_status,  # type: ignore[arg-type]
                source_trace_json=json.dumps(trace, ensure_ascii=False),
            )
        )

    # =========================================================================
    # 1. PSI-102 (SAME) — Table 1 (p.27): 8 material/aging states x 3 statistics = 24 measurements
    # =========================================================================
    same_doc = "SAME Final Science report  03 18 10 with papers attached.pdf"
    same_table1 = [
        ("Kapton", "UNAGED", 80.0, 105.0, 179.0, 2.08),
        ("Kapton", "AGED", 155.0, 186.0, 267.0, 1.82),
        ("Cellulose (Lamp Wick)", "UNAGED", 186.0, 227.0, 341.0, 1.89),
        ("Cellulose (Lamp Wick)", "AGED", 258.0, 308.0, 438.0, 1.81),
        ("Silicone", "UNAGED", 189.0, 257.0, 472.0, 2.18),
        ("Silicone", "AGED", 352.0, 422.0, 606.0, 1.83),
        ("Teflon", "UNAGED", 170.0, 205.0, 297.0, 1.84),
        ("Teflon", "AGED", 228.0, 273.0, 392.0, 1.82),
    ]
    for mat, aging_state, gmd, amd, mmd, sigma_g in same_table1:
        for stat_code, val in (("GMD", gmd), ("AMD", amd), ("MMD", mmd)):
            _add(
                psi_id="PSI-102",
                test_id=None,
                parameter="smoke_particle_diameter_nm",
                value=val,
                unit="nm",
                source_doc=same_doc,
                source_page=27,
                subtype=f"{stat_code}_{aging_state}",
                statistic_type=stat_code,
                instrument="Moment/Ionization-Scattering",
                ignition_method="non_flaming_pyrolysis",
                eligibility_status="EVIDENCE_ONLY",
                trace_meta={
                    "table": "Table 1. Results of SAME flight tests",
                    "material": mat,
                    "aging_state": aging_state,
                    "sigma_g": sigma_g,
                    "raw_unit": "nm",
                },
            )

    # PSI-102 (SAME) Detector Thresholds & Concentrations (pp. 12, 14, 19, 39, 65)
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="detection_threshold",
        value=2.0,
        unit="mg/m³",
        source_doc=same_doc,
        source_page=12,
        subtype="STS_IONIZATION_MASS_ALARM_THRESHOLD",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="STS Smoke Detector",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Space Shuttle detector alarm threshold (2 mg/m3 for 5 s)"},
    )
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="detection_threshold",
        value=0.5,
        unit="mg/m³",
        source_doc=same_doc,
        source_page=65,
        subtype="ISS_LASER_SCATTERING_MASS_ALARM_THRESHOLD",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="ISS Honeywell Smoke Detector",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "ISS laser forward-scattering detector alarm point (~0.5 mg/m3)"},
    )
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="smoke_optical_property",
        value=1.0,
        unit="%/ft",
        source_doc=same_doc,
        source_page=12,
        subtype="OBSCURATION_PER_FOOT_ALARM_THRESHOLD",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="ISS Honeywell Smoke Detector",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "1% obscuration per foot UL alarm design criteria"},
    )
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="particle_number_concentration_cm3",
        value=5.0,
        unit="particles/cm³",
        source_doc=same_doc,
        source_page=14,
        subtype="ISS_CABIN_BACKGROUND_UPPER_BOUND",
        value_type="upper_bound",
        value_max=5.0,
        statistic_type="THRESHOLD",
        instrument="P-Trak CPC",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Ambient ISS cabin background < 5 particles/cm3"},
    )
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="particle_number_concentration_cm3",
        value=2750000.0,
        unit="particles/cm³",
        source_doc=same_doc,
        source_page=19,
        subtype="SAME_SMOKE_CONCENTRATION_RANGE",
        value_type="interval",
        value_min=500000.0,
        value_max=5000000.0,
        statistic_type="RANGE_MIDPOINT",
        instrument="Moment/P-Trak CPC",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Smoke concentration in SAME ranges from 0.5e6 to 5e6 particles/cm3"},
    )
    _add(
        psi_id="PSI-102",
        test_id=None,
        parameter="incident_heat_flux_kw_m2",
        value=57.6,
        unit="kW/m²",
        source_doc=same_doc,
        source_page=65,
        subtype="SIMULATION_BURNER_HEAT_FLUX",
        statistic_type="EXACT_RUN",
        instrument="Simulation/Model",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "LES model source heat flux 57.6 kW/m2"},
    )

    # =========================================================================
    # 2. PSI-101 (SAME-R) — Table 1 (p.78): 5 materials x 2 aging states x 3 stats = 30 measurements
    # =========================================================================
    samer_doc = "SAMER_Final 0602 2014.pdf"
    samer_table1_um = [
        ("Kapton", "UNAGED", 0.042, 0.056, 0.101, 2.154),
        ("Kapton", "AGED_720S", 0.089, 0.109, 0.161, 1.872),
        ("Cellulose (Lamp Wick)", "UNAGED", 0.090, 0.128, 0.258, 2.312),
        ("Cellulose (Lamp Wick)", "AGED_720S", 0.229, 0.276, 0.398, 1.834),
        ("Silicone", "UNAGED", 0.128, 0.196, 0.465, 2.530),
        ("Silicone", "AGED_720S", 0.269, 0.355, 0.619, 2.108),
        ("Teflon", "UNAGED", 0.081, 0.101, 0.170, 2.198),
        ("Teflon", "AGED_720S", 0.070, 0.105, 0.232, 2.442),
        ("Pyrell Foam", "UNAGED", 0.149, 0.204, 0.384, 2.211),
        ("Pyrell Foam", "AGED_720S", 0.293, 0.359, 0.539, 1.892),
    ]
    for mat, aging_state, dg_um, cmd_um, mmd_um, sigma_g in samer_table1_um:
        for stat_code, val_um in (("GMD", dg_um), ("CMD", cmd_um), ("MMD", mmd_um)):
            _add(
                psi_id="PSI-101",
                test_id=None,
                parameter="smoke_particle_diameter_nm",
                value=normalize_diameter_to_nm(val_um, "um"),
                unit="nm",
                source_doc=samer_doc,
                source_page=78,
                subtype=f"{stat_code}_{aging_state}",
                statistic_type=stat_code,
                instrument="Moment/Ionization-Scattering",
                ignition_method="non_flaming_pyrolysis",
                eligibility_status="EVIDENCE_ONLY",
                trace_meta={
                    "table": "Table 1: Diameter results for baseline runs (micrometers)",
                    "material": mat,
                    "aging_state": aging_state,
                    "sigma_g": sigma_g,
                    "raw_value": val_um,
                    "raw_unit": "µm",
                },
            )

    # PSI-101 (SAME-R) Table 2 (p.16): Run-specific TEM vs Moment Method measurements linked to test_id!
    # Columns: (test_id, material, aging, temp_c, tem_dm_um, mom_dm_um, tem_cmd_um, mom_cmd_um, tem_dg_um, mom_dg_um)
    samer_table2 = [
        ("SAME-R-54", "Cellulose (Lamp Wick)", "UNAGED", 264.7, 0.403, 0.253, 0.304, 0.110, 0.255, 0.072),
        ("SAME-R-55", "Cellulose (Lamp Wick)", "AGED", 262.9, 0.499, 0.320, 0.359, 0.149, 0.284, 0.102),
        ("SAME-R-94", "Kapton", "AGED", 527.3, 0.159, 0.176, 0.120, 0.136, 0.103, 0.119),
        ("SAME-R-62", "Kapton", "UNAGED", 574.3, 0.226, 0.251, 0.180, 0.148, 0.158, 0.114),
        ("SAME-R-63", "Pyrell Foam", "UNAGED", 225.3, 0.394, 0.392, 0.290, 0.207, 0.244, 0.151),
        ("SAME-R-64", "Pyrell Foam", "UNAGED", 242.1, 0.411, 0.445, 0.298, 0.254, 0.249, 0.192),
        ("SAME-R-60", "Silicone", "UNAGED", 379.9, 0.153, 0.533, 0.120, 0.241, 0.107, 0.162),
    ]
    for tid, mat, aging, temp_c, tem_dm, mom_dm, tem_cmd, mom_cmd, tem_dg, mom_dg in samer_table2:
        _add(
            psi_id="PSI-101",
            test_id=tid,
            parameter="smoke_particle_diameter_nm",
            value=normalize_diameter_to_nm(tem_dg, "um"),
            unit="nm",
            source_doc=samer_doc,
            source_page=16,
            subtype=f"GMD_{aging}_TEM",
            statistic_type="GMD",
            instrument="TEM",
            ignition_method="non_flaming_pyrolysis",
            eligibility_status="ML_ELIGIBLE",
            trace_meta={"table": "Table 2 p.16", "material": mat, "pyrolysis_temp_c": temp_c, "raw_unit": "µm"},
        )
        _add(
            psi_id="PSI-101",
            test_id=tid,
            parameter="smoke_particle_diameter_nm",
            value=normalize_diameter_to_nm(mom_dg, "um"),
            unit="nm",
            source_doc=samer_doc,
            source_page=16,
            subtype=f"GMD_{aging}_MOMENT",
            statistic_type="GMD",
            instrument="Moment/Ionization-Scattering",
            ignition_method="non_flaming_pyrolysis",
            eligibility_status="ML_ELIGIBLE",
            trace_meta={"table": "Table 2 p.16", "material": mat, "pyrolysis_temp_c": temp_c, "raw_unit": "µm"},
        )
        _add(
            psi_id="PSI-101",
            test_id=tid,
            parameter="smoke_particle_diameter_nm",
            value=normalize_diameter_to_nm(mom_cmd, "um"),
            unit="nm",
            source_doc=samer_doc,
            source_page=16,
            subtype=f"CMD_{aging}_MOMENT",
            statistic_type="CMD",
            instrument="Moment/Ionization-Scattering",
            ignition_method="non_flaming_pyrolysis",
            eligibility_status="ML_ELIGIBLE",
            trace_meta={"table": "Table 2 p.16", "material": mat, "pyrolysis_temp_c": temp_c, "raw_unit": "µm"},
        )
        _add(
            psi_id="PSI-101",
            test_id=tid,
            parameter="smoke_particle_diameter_nm",
            value=normalize_diameter_to_nm(mom_dm, "um"),
            unit="nm",
            source_doc=samer_doc,
            source_page=16,
            subtype=f"MMD_{aging}_MOMENT",
            statistic_type="MMD",
            instrument="Moment/Ionization-Scattering",
            ignition_method="non_flaming_pyrolysis",
            eligibility_status="ML_ELIGIBLE",
            trace_meta={"table": "Table 2 p.16", "material": mat, "pyrolysis_temp_c": temp_c, "raw_unit": "µm"},
        )

    # PSI-101 SMPS vs TEM (p.15) & Smoke Mass Concentration Range (p.4) & Threshold (p.10)
    _add(
        psi_id="PSI-101",
        test_id=None,
        parameter="smoke_particle_diameter_nm",
        value=248.0,
        unit="nm",
        source_doc=samer_doc,
        source_page=15,
        subtype="GMD_AGED_SMPS",
        statistic_type="GMD",
        instrument="SMPS",
        ignition_method="non_flaming_pyrolysis",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Fig. 18 Lampwick aged test 689 (285.8 C) SMPS dgn=248 nm"},
    )
    _add(
        psi_id="PSI-101",
        test_id=None,
        parameter="smoke_mass_concentration_mg_m3",
        value=8.5,
        unit="mg/m³",
        source_doc=samer_doc,
        source_page=4,
        subtype="SAMER_SMOKE_MASS_CONC_RANGE",
        value_type="interval",
        value_min=2.0,
        value_max=15.0,
        statistic_type="RANGE_MIDPOINT",
        instrument="DustTrak Photometer",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Typical SAME-R mass concentrations were 2 to 15 mg/m3"},
    )
    _add(
        psi_id="PSI-101",
        test_id=None,
        parameter="detection_threshold",
        value=20000.0,
        unit="particles/cm³",
        source_doc=samer_doc,
        source_page=10,
        subtype="COAGULATION_THRESHOLD_CONCENTRATION",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="SMPS",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Rule-of-thumb coagulation threshold 2e4 particles/cm3"},
    )

    # =========================================================================
    # 3. PSI-47 (DAFT / DAFT-2) — Figure 5 Tabular Data (p.11): Bag #1, Bag #2, Bag #3
    # =========================================================================
    daft_doc = "Exp_13_DAFT_30-Day_Postflight_Report.pdf"
    # Summary statistics from Figure 5 (p.11) for Bags 1, 2, 3 + ISS cabin baseline (p.2 of fact sheet)
    daft_bags = [
        ("Bag1", 17314.3, 16400.0, 18200.0, 43.15, 40.4, 46.0, 1.68),
        ("Bag2", 17256.0, 12500.0, 25000.0, 34.09, 32.8, 37.6, 1.56),
        ("Bag3", 24350.0, 11400.0, 36500.0, 63.18, 51.6, 71.0, 1.70),
    ]
    for bag_id, n_mean, n_min, n_max, m_mean, m_min, m_max, d_um in daft_bags:
        _add(
            psi_id="PSI-47",
            test_id="DAFT-D1",
            parameter="particle_number_concentration_cm3",
            value=n_mean,
            unit="particles/cm³",
            source_doc=daft_doc,
            source_page=11,
            subtype=f"ARD_CALIBRATION_DUST_{bag_id}",
            value_type="interval",
            value_min=n_min,
            value_max=n_max,
            statistic_type="MEAN",
            instrument="P-Trak CPC",
            eligibility_status="EVIDENCE_ONLY",
            trace_meta={"table": "Figure 5: Tabular data from DAFT-3 and -4", "bag": bag_id},
        )
        _add(
            psi_id="PSI-47",
            test_id="DAFT-D2",
            parameter="smoke_mass_concentration_mg_m3",
            value=m_mean,
            unit="mg/m³",
            source_doc=daft_doc,
            source_page=11,
            subtype=f"ARD_CALIBRATION_DUST_{bag_id}",
            value_type="interval",
            value_min=m_min,
            value_max=m_max,
            statistic_type="MEAN",
            instrument="DustTrak Photometer",
            eligibility_status="EVIDENCE_ONLY",
            trace_meta={"table": "Figure 5: Tabular data from DAFT-3 and -4", "bag": bag_id},
        )
        _add(
            psi_id="PSI-47",
            test_id="DAFT-D2",
            parameter="smoke_particle_diameter_nm",
            value=normalize_diameter_to_nm(d_um, "um"),
            unit="nm",
            source_doc=daft_doc,
            source_page=11,
            subtype=f"ARD_CALIBRATION_DUST_{bag_id}",
            statistic_type="MEAN",
            instrument="P-Trak/DustTrak Ratio",
            eligibility_status="EVIDENCE_ONLY",
            trace_meta={"table": "Figure 5: Tabular data from DAFT-3 and -4", "raw_unit": "µm"},
        )

    _add(
        psi_id="PSI-47",
        test_id="DAFT-D1",
        parameter="particle_number_concentration_cm3",
        value=15.0,
        unit="particles/cm³",
        source_doc="daft_fact_sheet_final1.pdf",
        source_page=2,
        subtype="ISS_CABIN_BACKGROUND_UPPER_BOUND",
        value_type="upper_bound",
        value_max=15.0,
        statistic_type="THRESHOLD",
        instrument="P-Trak CPC",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "ISS US Lab background fewer than 15 particles/cm3"},
    )
    _add(
        psi_id="PSI-47",
        test_id="DAFT-D2",
        parameter="smoke_mass_concentration_mg_m3",
        value=0.005,
        unit="mg/m³",
        source_doc="daft_fact_sheet_final1.pdf",
        source_page=2,
        subtype="ISS_CABIN_BACKGROUND_UPPER_BOUND",
        value_type="upper_bound",
        value_max=0.005,
        statistic_type="THRESHOLD",
        instrument="DustTrak Photometer",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "ISS US Lab background fewer than 0.005 mg/m3"},
    )

    # =========================================================================
    # 4. PSI-25 (BASS-II) — Verified Report Measurements (Summary Report PDF)
    # =========================================================================
    bass2_doc = "BASS-II Summary Report.pdf"
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="hrr_watts",
        value=191.0,
        unit="W",
        source_doc=bass2_doc,
        source_page=40,
        subtype="TOTAL_FLAME_POWER_PMMA_SPHERE",
        statistic_type="EXACT_RUN",
        instrument="Analytical Balance / Calorimetry",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "PMMA sphere burning rate 1.9 mg/s corresponding to 191 W total power"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="mass_burning_rate_g_s",
        value=normalize_mass_rate_to_g_s(1.9, "mg/s"),
        unit="g/s",
        source_doc=bass2_doc,
        source_page=40,
        subtype="PMMA_SPHERE_MASS_BURNING_RATE",
        statistic_type="EXACT_RUN",
        instrument="Analytical Balance",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 1.9, "raw_unit": "mg/s"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="critical_ignition_heat_flux_kw_m2",
        value=normalize_heat_flux_to_kw_m2(1.57, "W/cm2"),
        unit="kW/m²",
        source_doc=bass2_doc,
        source_page=94,
        subtype="LITERATURE_AND_BLOWOFF_MINIMUM_PMMA",
         value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="Literature Ref. 31 / Stagnation Model",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 1.57, "raw_unit": "W/cm2", "reference": "Ref. 31 PMMA critical heat flux"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="incident_heat_flux_kw_m2",
        value=normalize_heat_flux_to_kw_m2(12.0, "W/cm2"),
        unit="kW/m²",
        source_doc=bass2_doc,
        source_page=94,
        subtype="PEAK_FLAME_TO_SURFACE_HEAT_FLUX",
        statistic_type="PEAK",
        instrument="Stagnation Model",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 12.0, "raw_unit": "W/cm2"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="incident_heat_flux_kw_m2",
        value=225.0,
        unit="kW/m²",
        source_doc=bass2_doc,
        source_page=69,
        subtype="SIMULATION_MAX_SURFACE_HEAT_FLUX",
        statistic_type="PEAK",
        instrument="FDS 2D Simulation",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 225.0, "raw_unit": "kW/m2"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="flame_spread_rate_mm_s",
        value=normalize_spread_rate_to_mm_s(0.22, "cm/s"),
        unit="mm/s",
        source_doc=bass2_doc,
        source_page=21,
        subtype="OPPOSED_0G_THIN_PMMA",
        statistic_type="EXACT_RUN",
        instrument="Video/Visual",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 0.22, "raw_unit": "cm/s"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="flame_spread_rate_mm_s",
        value=0.037,
        unit="mm/s",
        source_doc=bass2_doc,
        source_page=135,
        subtype="LOW_O2_NEAR_QUENCH_PMMA_ROD",
        statistic_type="EXACT_RUN",
        instrument="Video/Visual",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"raw_value": 0.037, "raw_unit": "mm/s"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="oxygen_limit_pct",
        value=13.6,
        unit="%",
        source_doc=bass2_doc,
        source_page=81,
        subtype="LOC_0G_PMMA_ROD",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="CSA-CP",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Minimum oxygen concentration sustaining flame spread in 0g (13.6% O2)"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="oxygen_limit_pct",
        value=16.2,
        unit="%",
        source_doc=bass2_doc,
        source_page=25,
        subtype="LOI_0G_THIN_PMMA_2CM_S",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="CSA-CP",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Limiting oxygen concentration at 2 cm/s opposed flow"},
    )
    _add(
        psi_id="PSI-25",
        test_id=None,
        parameter="ignition_time_s",
        value=230.0,
        unit="s",
        source_doc=bass2_doc,
        source_page=75,
        subtype="MAX_SUSTAINED_IGNITION_DELAY_PMMA_ROD",
        value_type="upper_bound",
        value_max=230.0,
        statistic_type="THRESHOLD",
        instrument="Video/Visual",
        ignition_method="piloted",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Ignition times to achieve sustained flames on PMMA rods could be as long as 230 s"},
    )

    # =========================================================================
    # 5. PSI-26 (BASS) & PSI-159 (ACME CFI-G) — Verified Report Measurements
    # =========================================================================
    _add(
        psi_id="PSI-26",
        test_id=None,
        parameter="sample_pyrolysis_temperature_k",
        value=570.0,
        unit="K",
        source_doc="ISS Denver 2013-BASS.pdf",
        source_page=50,
        subtype="SOLID_SURFACE_PYROLYSIS_MODEL_BOUNDARY",
        value_type="threshold",
        statistic_type="THRESHOLD",
        instrument="Simulation/Model",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Burning angle defined by solid surface pyrolysis temperature (570 K) in 2D PMMA sphere model"},
    )
    _add(
        psi_id="PSI-159",
        test_id=None,
        parameter="ignition_temperature_k",
        value=550.0,
        unit="K",
        source_doc="PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf",
        source_page=23,
        subtype="COOL_DIFFUSION_FLAME_AUTOIGNITION_ONSET",
        value_type="exact",
        statistic_type="THRESHOLD",
        instrument="Thermocouple",
        ignition_method="autoignition",
        eligibility_status="EVIDENCE_ONLY",
        trace_meta={"note": "Direct experimental observation: Autoignition first occurred at 550 K"},
    )

    return measurements
