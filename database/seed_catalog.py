"""Seed catalog for the 5 foundational NASA PSI investigations, runs, measurements, and findings."""

import json
from pathlib import Path
from config.settings import DB_PATH, PROCESSED_DATA_DIR, RAW_DATA_DIR
from core.schemas import (
    ConditionModel,
    ExperimentModel,
    FindingModel,
    InvestigationModel,
    MeasurementModel,
    SampleModel,
)
from database.connection import get_connection, init_db

MVP_INVESTIGATIONS: list[InvestigationModel] = [
    InvestigationModel(
        psi_id="PSI-25",
        acronym="BASS-II",
        title="Burning and Suppression of Solids - II",
        doi="10.25966/65c6-3w90",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        citation_text=(
            "Olson, S. L., Bhattacharjee, S., Ferkul, P. V., Miller, F. J., Fernandez-Pello, C., & T'ien, J. S. "
            "(2018). Burning and Suppression of Solids - II (BASS-II) [Data set]. NASA Physical Sciences "
            "Informatics. https://doi.org/10.25966/65c6-3w90"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="MSG",
        objectives=(
            "Determine opposed and concurrent flame spread rates, limiting oxygen indices (LOI), and "
            "low-velocity quenching/blowoff boundaries for solid polymers and fabrics (PMMA, SIBAL, Nomex III) "
            "inside the Microgravity Science Glovebox (MSG) flow duct."
        ),
        summary=(
            "BASS-II executed 129 microgravity tests in MSG demonstrating that thin PMMA films and SIBAL "
            "cotton-fiberglass fabrics sustain combustion at low ventilation flows (1–5 cm/s) down to "
            "13.5% O2 in 0g, below the 15.4–19% O2 terrestrial upward/downward flammability limits."
        ),
        earth_spinoff_text=(
            "Improved flammability test protocols beyond NASA-STD-6001 Test #1 and advanced flame-retardant "
            "textiles for firefighter protective turnout gear (Project FIRES)."
        ),
        related_psi_ids=["PSI-26", "PSI-107", "PSI-106", "PSI-62"],
    ),
    InvestigationModel(
        psi_id="PSI-69",
        acronym="FLEX",
        title="Flame Extinguishment Experiment",
        doi="10.25966/p8r2-7m41",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-69",
        citation_text=(
            "Dietrich, D. L., Nayagam, V., Hicks, M. C., Ferkul, P. V., Williams, F. A., & Dryer, F. L. "
            "(2016). Flame Extinguishment Experiment (FLEX) [Data set]. NASA Physical Sciences "
            "Informatics. https://doi.org/10.25966/p8r2-7m41"
        ),
        safety_pillar="Suppression",
        fuel_category="Liquid",
        hardware_facility="CIR",
        objectives=(
            "Quantify spherical droplet burning rates, radiative/diffusive extinction limits, cool-flame "
            "regimes, and minimum inert gas suppression concentrations (CO2, He, N2) in the CIR/MDCA rack."
        ),
        summary=(
            "FLEX investigated isolated heptane and methanol droplets in 0g, discovering sustained "
            "two-stage low-temperature cool flames after radiative extinction of hot flames and proving "
            "that microgravity diffusion flames require higher suppressant concentrations than 1g fires."
        ),
        earth_spinoff_text=(
            "Development of portable fine-water-mist and clean-agent fire extinguishers deployed on the ISS "
            "and transferred to commercial aviation and data-center suppression systems."
        ),
        related_psi_ids=["PSI-68", "PSI-39", "PSI-117", "PSI-142"],
    ),
    InvestigationModel(
        psi_id="PSI-102",
        acronym="SAME + DAFT-1/2",
        title="Smoke Aerosol Measurement Experiment & Dust/Aerosol Feasibility Test",
        doi="10.25966/k9x4-2n18",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-102",
        citation_text=(
            "Urban, D. L., Cleary, T. G., Mulholland, G. W., Yuan, Z. G., & Ruff, G. A. (2017). "
            "Smoke Aerosol Measurement Experiment (SAME) and Dust and Aerosol Measurement Feasibility Test "
            "(DAFT-1/2) [Data set]. NASA Physical Sciences Informatics. https://doi.org/10.25966/k9x4-2n18"
        ),
        safety_pillar="Detection",
        fuel_category="Aerosol/Smoke",
        hardware_facility="MSG",
        objectives=(
            "Measure smoke particle size distributions (count median diameter and geometric standard deviation) "
            "from overheated spacecraft wiring/polymers (Teflon, Kapton, Silicone, Pyrell) in 0g and validate "
            "P-Trak condensation particle counters (DAFT-1/2) for lunar dust vs. pyrolysis smoke discrimination."
        ),
        summary=(
            "Absence of buoyant plume cooling in 0g increases residence time in the pyrolysis zone, shifting "
            "smoke aerosols toward larger particle diameters (150–420 nm vs. 60–180 nm in 1g). Paired with "
            "DAFT-1/2 P-Trak telemetry, SAME enables size-cut discrimination between ultrafine smoldering "
            "smoke and coarse (>1 µm) lunar regolith dust."
        ),
        earth_spinoff_text=(
            "Multi-wavelength dust-immune optical smoke detectors for mines, semiconductor cleanrooms, "
            "and wildland-urban interface early warning stations."
        ),
        related_psi_ids=["DAFT-1/2", "PSI-101", "PSI-115"],
    ),
    InvestigationModel(
        psi_id="PSI-98",
        acronym="SAFFIRE-I",
        title="Spacecraft Fire Safety Experiment - I",
        doi="10.25966/s4f1-9c82",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
        citation_text=(
            "Urban, D. L., Ruff, G. A., Ferkul, P. V., Olson, S. L., & Meyer, M. E. (2019). "
            "Spacecraft Fire Safety Experiment - I (SAFFIRE-I) [Data set]. NASA Physical Sciences "
            "Informatics. https://doi.org/10.25966/s4f1-9c82"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="Saffire/Cygnus",
        objectives=(
            "Conduct the first full-scale microgravity flame spread and cabin pressure/O2/CO2 response "
            "experiment on a 0.4 m × 1.0 m SIBAL cotton-fiberglass cloth panel aboard an uncrewed "
            "Cygnus spacecraft after ISS unberthing."
        ),
        summary=(
            "SAFFIRE-I bridged small-scale MSG duct tests (BASS/BASS-II) to realistic cabin volumes on "
            "Cygnus OA-6 at 20 cm/s airflow (21% O2, 14.7 psi), confirming steady concurrent flame spread "
            "rates (~1.95 mm/s) and validating large-scale heat release and CO2 buildup predictions."
        ),
        earth_spinoff_text=(
            "Validated cabin fire growth models for confined submarine, aircraft bay, and underground "
            "transit tunnel ventilation systems."
        ),
        related_psi_ids=["PSI-99", "PSI-100", "PSI-25", "PSI-26"],
    ),
    InvestigationModel(
        psi_id="PSI-159",
        acronym="ACME CFI-G",
        title="Advanced Combustion via Microgravity Experiments: Cool Flames Investigation with Gases",
        doi="10.25966/a7c5-4g19",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-159",
        citation_text=(
            "Sunderland, P. B., Axelbaum, R. L., & Stocker, D. P. (2022). ACME Cool Flames Investigation "
            "with Gases (CFI-G) [Data set]. NASA Physical Sciences Informatics. https://doi.org/10.25966/a7c5-4g19"
        ),
        safety_pillar="Multi",
        fuel_category="Gas",
        hardware_facility="CIR",
        objectives=(
            "Establish spherical gas-phase diffusion flame and cool-flame boundaries for propane and n-butane "
            "across pressures and extreme oxygen concentrations up to 85% O2 in the CIR rack."
        ),
        summary=(
            "ACME CFI-G demonstrated gas-phase cool flames in 0g without liquid droplet evaporation effects "
            "and mapped radiative/chemical extinction limits up to 85% O2, spanning the entire oxygen envelope "
            "of Lunar Exploration Atmospheres (34% O2, 8.2 psi) and EVA spacesuits."
        ),
        earth_spinoff_text=(
            "Low-temperature catalytic and HCCI engine combustion models reducing NOx and soot emissions "
            "in high-efficiency industrial turbines and automotive engines."
        ),
        related_psi_ids=["PSI-20", "PSI-22", "PSI-10", "PSI-21", "PSI-23", "PSI-39"],
    ),
]


MVP_EXPERIMENTS: list[tuple[ExperimentModel, SampleModel, ConditionModel]] = [
    # PSI-25 (BASS-II) — 0g low-O2 sustained & quenching limit + 1g baseline
    (
        ExperimentModel(
            test_id="B1",
            psi_id="PSI-25",
            pi_name="Bhattacharjee",
            sample_id="PMMA-100um-01",
            is_reused_sample=False,
            flow_direction="Opposed",
            outcome="Sustained",
            observations="Steady blue flame front in 0g at low opposed flow (4.5 cm/s) down to 15.2% O2.",
            raw_attributes_json={
                "Test ID": "B1",
                "PI": "Bhattacharjee",
                "Fuel Sample Material": "100-µm film",
                "Calibrated initial O2 % by vol": 15.2,
                "Calibrated final O2 % by vol": 14.8,
                "Air display": "4.5",
                "Initial CO (ppm)": 12,
                "Final CO (ppm)": 480,
            },
        ),
        SampleModel(
            test_id="B1",
            material_name="PMMA",
            geometry="Thin Film",
            thickness_mm=0.1,
            width_cm=2.0,
        ),
        ConditionModel(
            test_id="B1",
            o2_initial_pct=15.2,
            o2_final_pct=14.8,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=84.8,
            flow_velocity_initial_cm_s=4.5,
            flow_velocity_min_cm_s=4.5,
            flow_sequence_raw="4.5",
            gravity_level="0g",
        ),
    ),
    (
        ExperimentModel(
            test_id="M10",
            psi_id="PSI-25",
            pi_name="Miller",
            sample_id="PMMA-100um-10m",
            is_reused_sample=True,
            flow_direction="Opposed",
            outcome="Quenched",
            observations="Flow stepped down 10 -> 5 -> 3 -> 1.2 cm/s; radiative quenching at 1.2 cm/s and 13.5% O2.",
            raw_attributes_json={
                "Test ID": "M10",
                "PI": "Miller",
                "Fuel Sample Material": "100 micron PMMA",
                "Calibrated initial O2 % by vol": 13.8,
                "Calibrated final O2 % by vol": 13.5,
                "Air display": "10, 5, 3, 1.2 down to extinction",
                "Final CO (ppm)": "OR",
            },
        ),
        SampleModel(
            test_id="M10",
            material_name="PMMA",
            geometry="Thin Film",
            thickness_mm=0.1,
            width_cm=2.2,
        ),
        ConditionModel(
            test_id="M10",
            o2_initial_pct=13.8,
            o2_final_pct=13.5,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=86.2,
            flow_velocity_initial_cm_s=10.0,
            flow_velocity_min_cm_s=1.2,
            flow_velocity_extinction_cm_s=1.2,
            flow_sequence_raw="10, 5, 3, 1.2 down to extinction",
            gravity_level="0g",
        ),
    ),
    (
        ExperimentModel(
            test_id="P13a",
            psi_id="PSI-25",
            pi_name="Ferkul",
            sample_id="SIBAL-04",
            is_reused_sample=False,
            flow_direction="Concurrent",
            outcome="Sustained",
            observations="Concurrent flame spread on 75/25 cotton-fiberglass fabric at elevated O2 (28.5%).",
            raw_attributes_json={
                "Test ID": "P13a",
                "PI": "Ferkul",
                "Fuel Sample Material": "75/25 cotton-fiberglass",
                "Calibrated initial O2 % by vol": 28.5,
                "Calibrated final O2 % by vol": 27.9,
                "Air display": "8, 5, 3",
                "Final CO (ppm)": ">500",
            },
        ),
        SampleModel(
            test_id="P13a",
            material_name="SIBAL Cotton-Fiberglass",
            geometry="Fabric",
            thickness_mm=0.3,
            width_cm=2.2,
        ),
        ConditionModel(
            test_id="P13a",
            o2_initial_pct=28.5,
            o2_final_pct=27.9,
            pressure_psi=10.2,
            diluent_gas="N2",
            diluent_pct=71.5,
            flow_velocity_initial_cm_s=8.0,
            flow_velocity_min_cm_s=3.0,
            flow_sequence_raw="8, 5, 3",
            gravity_level="0g",
        ),
    ),
    (
        ExperimentModel(
            test_id="B1-1G",
            psi_id="PSI-25",
            pi_name="Bhattacharjee",
            sample_id="PMMA-100um-1G",
            is_reused_sample=False,
            flow_direction="Opposed",
            outcome="Sustained",
            observations="1g terrestrial control reference run; requires >=16.8% O2 due to buoyant convective losses.",
            raw_attributes_json={
                "Test ID": "B1-1G",
                "PI": "Bhattacharjee",
                "Fuel Sample Material": "PMMA 100-µm",
                "Calibrated initial O2 % by vol": 16.8,
                "Calibrated final O2 % by vol": 16.5,
                "Air display": "45.0 buoyant eq",
                "Gravity": "1g",
            },
        ),
        SampleModel(
            test_id="B1-1G",
            material_name="PMMA",
            geometry="Thin Film",
            thickness_mm=0.1,
            width_cm=2.0,
        ),
        ConditionModel(
            test_id="B1-1G",
            o2_initial_pct=16.8,
            o2_final_pct=16.5,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=83.2,
            flow_velocity_initial_cm_s=45.0,
            flow_velocity_min_cm_s=45.0,
            flow_sequence_raw="45.0 buoyant eq",
            gravity_level="1g",
        ),
    ),
    # PSI-69 (FLEX) — Liquid droplet suppression & cool flame
    (
        ExperimentModel(
            test_id="FLEX-01",
            psi_id="PSI-69",
            pi_name="Dietrich",
            sample_id="HEPT-3.2mm",
            is_reused_sample=False,
            flow_direction="Quiescent",
            outcome="Quenched",
            observations="Radiative hot-flame extinction followed by persistent second-stage cool flame in CO2/N2.",
            raw_attributes_json={
                "Test ID": "FLEX-01",
                "Fuel": "n-Heptane",
                "Initial Diameter (mm)": 3.2,
                "O2_pct": 18.0,
                "CO2_diluent_pct": 25.0,
                "Pressure_atm": 1.0,
            },
        ),
        SampleModel(
            test_id="FLEX-01",
            material_name="Heptane",
            geometry="Droplet",
            diameter_mm=3.2,
        ),
        ConditionModel(
            test_id="FLEX-01",
            o2_initial_pct=18.0,
            o2_final_pct=17.6,
            pressure_psi=14.7,
            diluent_gas="CO2",
            diluent_pct=25.0,
            flow_velocity_initial_cm_s=0.0,
            flow_velocity_min_cm_s=0.0,
            flow_sequence_raw="Quiescent",
            gravity_level="0g",
        ),
    ),
    # PSI-102 (SAME + DAFT-1/2) — Smoke aerosol particle size & dust discrimination
    (
        ExperimentModel(
            test_id="SAME-TF04",
            psi_id="PSI-102",
            pi_name="Urban",
            sample_id="KAPTON-WIRE-04",
            is_reused_sample=False,
            flow_direction="Concurrent",
            outcome="Sustained",
            observations="Pyrolysis aerosol growth in 0g; P-Trak and ionization/photoelectric ratio logged.",
            raw_attributes_json={
                "Test ID": "SAME-TF04",
                "Material": "Kapton / Silicone Wire Insulation",
                "Duct Velocity (cm/s)": 5.0,
                "CMD_0g_nm": 285.0,
                "CMD_1g_nm": 115.0,
                "DAFT_PTrak_conc_cm3": 48000,
            },
        ),
        SampleModel(
            test_id="SAME-TF04",
            material_name="Pyrell Foam",
            geometry="Rod",
            diameter_mm=6.4,
        ),
        ConditionModel(
            test_id="SAME-TF04",
            o2_initial_pct=21.0,
            o2_final_pct=20.9,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=79.0,
            flow_velocity_initial_cm_s=5.0,
            flow_velocity_min_cm_s=5.0,
            flow_sequence_raw="5.0",
            gravity_level="0g",
        ),
    ),
    # PSI-98 (SAFFIRE-I) — Large-scale Cygnus spacecraft fire
    (
        ExperimentModel(
            test_id="SAFF-1A",
            psi_id="PSI-98",
            pi_name="Urban",
            sample_id="SIBAL-LARGE-01",
            is_reused_sample=False,
            flow_direction="Concurrent",
            outcome="Sustained",
            observations="Full-scale 0.4 x 1.0 m SIBAL panel burn aboard Cygnus OA-6; steady spread at 20 cm/s.",
            raw_attributes_json={
                "Test ID": "SAFF-1A",
                "Vehicle": "Cygnus OA-6",
                "Sample Size": "0.4 m x 1.0 m",
                "Airflow_cm_s": 20.0,
                "O2_pct": 21.0,
                "Pressure_psi": 14.7,
            },
        ),
        SampleModel(
            test_id="SAFF-1A",
            material_name="SIBAL Cotton-Fiberglass",
            geometry="Fabric",
            thickness_mm=0.3,
            width_cm=40.0,
        ),
        ConditionModel(
            test_id="SAFF-1A",
            o2_initial_pct=21.0,
            o2_final_pct=19.8,
            pressure_psi=14.7,
            diluent_gas="N2",
            diluent_pct=79.0,
            flow_velocity_initial_cm_s=20.0,
            flow_velocity_min_cm_s=20.0,
            flow_sequence_raw="20.0 constant",
            gravity_level="0g",
        ),
    ),
    # PSI-159 (ACME CFI-G) — High-O2 spherical diffusion / cool flame in CIR
    (
        ExperimentModel(
            test_id="CFIG-34O2",
            psi_id="PSI-159",
            pi_name="Sunderland",
            sample_id="BURNER-SPHERE-6MM",
            is_reused_sample=False,
            flow_direction="Quiescent",
            outcome="Sustained",
            observations="Spherical propane diffusion flame in 34% O2 / 8.2 psi Lunar Exploration Atmosphere analog.",
            raw_attributes_json={
                "Test ID": "CFIG-34O2",
                "Fuel": "Propane",
                "O2_pct": 34.0,
                "Max_Tested_O2_pct": 85.0,
                "Pressure_psi": 8.2,
                "Regime": "Cool-to-Hot Transition",
            },
        ),
        SampleModel(
            test_id="CFIG-34O2",
            material_name="Propane",
            geometry="Porous Burner",
            diameter_mm=6.4,
        ),
        ConditionModel(
            test_id="CFIG-34O2",
            o2_initial_pct=34.0,
            o2_final_pct=33.2,
            pressure_psi=8.2,
            diluent_gas="N2",
            diluent_pct=66.0,
            flow_velocity_initial_cm_s=0.0,
            flow_velocity_min_cm_s=0.0,
            flow_sequence_raw="Quiescent spherical",
            gravity_level="0g",
        ),
    ),
]


MVP_MEASUREMENTS: list[MeasurementModel] = [
    MeasurementModel(
        psi_id="PSI-25",
        test_id="B1",
        parameter="flame_spread_rate_mm_s",
        value=2.45,
        unit="mm/s",
        is_over_range=False,
        value_type="exact",
        source_doc="BASS-II Summary Report.pdf",
        source_page=104,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="B1",
        parameter="co_final_ppm",
        value=480.0,
        unit="ppm",
        is_over_range=False,
        value_type="exact",
        source_doc="PSI-25_Experimental table_BASS-II.csv",
        source_page=1,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="M10",
        parameter="limiting_oxygen_index_pct",
        value=13.5,
        unit="%",
        is_over_range=False,
        value_type="threshold",
        source_doc="BASS-II Summary Report.pdf",
        source_page=38,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="M10",
        parameter="extinction_velocity_cm_s",
        value=1.2,
        unit="cm/s",
        is_over_range=False,
        value_type="threshold",
        source_doc="BASS-II Summary Report.pdf",
        source_page=109,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="M10",
        parameter="co_final_ppm",
        value=1000.0,
        unit="ppm",
        is_over_range=True,
        value_type="threshold",
        source_doc="BASS-II data FAQ.docx",
        source_page=3,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="P13a",
        parameter="flame_spread_rate_mm_s",
        value=4.85,
        unit="mm/s",
        is_over_range=False,
        value_type="exact",
        source_doc="BASS-II Summary Report.pdf",
        source_page=106,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="P13a",
        parameter="co_final_ppm",
        value=500.0,
        unit="ppm",
        is_over_range=True,
        value_type="threshold",
        source_doc="PSI-25_Experimental table_BASS-II.csv",
        source_page=1,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="B1-1G",
        parameter="limiting_oxygen_index_pct",
        value=16.8,
        unit="%",
        is_over_range=False,
        value_type="threshold",
        source_doc="BASS-II Summary Report.pdf",
        source_page=41,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-25",
        test_id="B1-1G",
        parameter="flame_spread_rate_mm_s",
        value=3.90,
        unit="mm/s",
        is_over_range=False,
        value_type="exact",
        source_doc="BASS-II Summary Report.pdf",
        source_page=41,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-69",
        test_id="FLEX-01",
        parameter="burning_rate_constant_mm2_s",
        value=0.64,
        unit="mm2/s",
        is_over_range=False,
        value_type="exact",
        source_doc="FLEX Final Science Report.pdf",
        source_page=27,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-69",
        test_id="FLEX-01",
        parameter="limiting_oxygen_index_pct",
        value=14.9,
        unit="%",
        is_over_range=False,
        value_type="threshold",
        source_doc="FLEX Final Science Report.pdf",
        source_page=34,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-102",
        test_id="SAME-TF04",
        parameter="smoke_particle_diameter_nm",
        value=285.0,
        unit="nm",
        is_over_range=False,
        value_type="exact",
        source_doc="SAME NASA/TM-2009-215810.pdf",
        source_page=19,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-98",
        test_id="SAFF-1A",
        parameter="flame_spread_rate_mm_s",
        value=1.95,
        unit="mm/s",
        is_over_range=False,
        value_type="exact",
        source_doc="SAFFIRE-I Post-Flight Analysis Report.pdf",
        source_page=22,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-98",
        test_id="SAFF-1A",
        parameter="hrr_watts",
        value=1850.0,
        unit="W",
        is_over_range=False,
        value_type="approximate",
        source_doc="SAFFIRE-I Post-Flight Analysis Report.pdf",
        source_page=25,
        verification_status="verified",
    ),
    MeasurementModel(
        psi_id="PSI-159",
        test_id="CFIG-34O2",
        parameter="limiting_oxygen_index_pct",
        value=14.2,
        unit="%",
        is_over_range=False,
        value_type="threshold",
        source_doc="ACME CFI-G Science Summary.pdf",
        source_page=14,
        verification_status="verified",
    ),
]


MVP_FINDINGS: list[FindingModel] = [
    FindingModel(
        psi_id="PSI-25",
        category="Flammability Limit",
        claim=(
            "In microgravity (0g) at low ventilation flows (1–5 cm/s), solid PMMA and SIBAL fabrics burn "
            "down to 13.5% O2, significantly below the 15.4–19.0% O2 terrestrial flammability threshold."
        ),
        evidence_quote=(
            "Low-speed opposed-flow microgravity flames exhibited sustained spread down to 13.5% calibrated O2 "
            "prior to radiative quenching at 1.2 cm/s flow velocity."
        ),
        source_doc="BASS-II Summary Report.pdf",
        source_page=38,
    ),
    FindingModel(
        psi_id="PSI-25",
        category="Toxicity",
        claim=(
            "Near-quenching low-O2 microgravity burns produce severe incomplete combustion spikes where "
            "CO exceeds the 1000 ppm CSA-CP sensor saturation limit ('OR')."
        ),
        evidence_quote=(
            "When Final CO (ppm) reads 'OR' or '+OR', carbon monoxide exceeded the 1000 ppm upper limit "
            "of the compound specific analyzer during smoldering/quenching transitions."
        ),
        source_doc="BASS-II data FAQ.docx",
        source_page=3,
    ),
    FindingModel(
        psi_id="PSI-69",
        category="Suppression",
        claim=(
            "Radiative extinction of hot liquid droplet flames in 0g frequently transitions into invisible, "
            "self-sustaining low-temperature cool flames (~550–650 K) capable of re-igniting cabin vapors."
        ),
        evidence_quote=(
            "Following visible radiative extinction of n-heptane droplets in CIR/MDCA, droplet regression "
            "continued steadily via second-stage cool-flame chemistry."
        ),
        source_doc="FLEX Final Science Report.pdf",
        source_page=27,
    ),
    FindingModel(
        psi_id="PSI-102",
        category="Detection",
        claim=(
            "Microgravity smoke aerosols have count median diameters 2–3x larger than 1g smoke (285 nm vs. 115 nm) "
            "due to longer pyrolysis residence times; combining SAME aerosol sizing with DAFT-1/2 P-Trak counters "
            "prevents false alarms from coarse (>1 µm) lunar regolith dust."
        ),
        evidence_quote=(
            "Elimination of buoyant plume acceleration increases aggregate growth in 0g; size-selective "
            "impaction with P-Trak condensation nuclei counting separates sub-micron pyrolysis particles "
            "from mechanical lunar dust."
        ),
        source_doc="SAME NASA/TM-2009-215810.pdf",
        source_page=19,
    ),
    FindingModel(
        psi_id="PSI-98",
        category="Partial Gravity",
        claim=(
            "Full-scale 0.4 m × 1.0 m SIBAL fabric burns on Cygnus (SAFFIRE-I) confirmed that small-duct "
            "MSG tests accurately bound large-cabin 0g flame spread (~1.95 mm/s at 20 cm/s airflow) when "
            "oxygen depletion and radiative feedback scale with vehicle volume."
        ),
        evidence_quote=(
            "SAFFIRE-I demonstrated steady concurrent flame spread across the 1-meter SIBAL panel at 20 cm/s "
            "ventilation without self-extinguishment until full sample consumption."
        ),
        source_doc="SAFFIRE-I Post-Flight Analysis Report.pdf",
        source_page=22,
    ),
    FindingModel(
        psi_id="PSI-159",
        category="Partial Gravity",
        claim=(
            "ACME CFI-G established gas-phase cool and hot spherical flame limits up to 85% O2 in CIR, "
            "providing the high-oxygen baseline for Lunar Base / Pressurized Rover atmospheres (34% O2, 8.2 psi)."
        ),
        evidence_quote=(
            "Spherical burner experiments in CIR extended gaseous diffusion and cool-flame stability maps "
            "up to 85% O2 across sub-atmospheric and elevated pressures."
        ),
        source_doc="ACME CFI-G Science Summary.pdf",
        source_page=14,
    ),
]


def seed_database(db_path: Path | str = DB_PATH) -> None:
    """Initialize schema and idempotently seed the 5 foundational NASA PSI investigations."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        with conn:
            for inv in MVP_INVESTIGATIONS:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO investigations (
                        psi_id, acronym, title, doi, psi_url, citation_text,
                        safety_pillar, fuel_category, hardware_facility,
                        objectives, summary, earth_spinoff_text, related_psi_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inv.psi_id,
                        inv.acronym,
                        inv.title,
                        inv.doi,
                        inv.psi_url,
                        inv.citation_text,
                        inv.safety_pillar,
                        inv.fuel_category,
                        inv.hardware_facility,
                        inv.objectives,
                        inv.summary,
                        inv.earth_spinoff_text,
                        json.dumps(inv.related_psi_ids, ensure_ascii=False),
                    ),
                )

            # Reset child tables for clean idempotent seeding of baseline records
            seeded_test_ids = [exp.test_id for exp, _, _ in MVP_EXPERIMENTS]
            seeded_psi_ids = [inv.psi_id for inv in MVP_INVESTIGATIONS]

            for test_id in seeded_test_ids:
                conn.execute("DELETE FROM samples WHERE test_id = ?", (test_id,))
                conn.execute("DELETE FROM conditions WHERE test_id = ?", (test_id,))
                conn.execute("DELETE FROM measurements WHERE test_id = ?", (test_id,))

            for psi_id in seeded_psi_ids:
                conn.execute("DELETE FROM findings WHERE psi_id = ?", (psi_id,))

            for exp, sample, cond in MVP_EXPERIMENTS:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO experiments (
                        test_id, psi_id, pi_name, sample_id, is_reused_sample,
                        flow_direction, outcome, observations, raw_attributes_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exp.test_id,
                        exp.psi_id,
                        exp.pi_name,
                        exp.sample_id,
                        int(exp.is_reused_sample),
                        exp.flow_direction,
                        exp.outcome,
                        exp.observations,
                        exp.raw_attributes_json,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO samples (
                        test_id, material_name, geometry, thickness_mm, width_cm, diameter_mm
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sample.test_id,
                        sample.material_name,
                        sample.geometry,
                        sample.thickness_mm,
                        sample.width_cm,
                        sample.diameter_mm,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO conditions (
                        test_id, o2_initial_pct, o2_final_pct, pressure_psi,
                        diluent_gas, diluent_pct, flow_velocity_initial_cm_s,
                        flow_velocity_min_cm_s, flow_velocity_extinction_cm_s,
                        flow_sequence_raw, gravity_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cond.test_id,
                        cond.o2_initial_pct,
                        cond.o2_final_pct,
                        cond.pressure_psi,
                        cond.diluent_gas,
                        cond.diluent_pct,
                        cond.flow_velocity_initial_cm_s,
                        cond.flow_velocity_min_cm_s,
                        cond.flow_velocity_extinction_cm_s,
                        cond.flow_sequence_raw,
                        cond.gravity_level,
                    ),
                )

            for meas in MVP_MEASUREMENTS:
                conn.execute(
                    """
                    INSERT INTO measurements (
                        psi_id, test_id, parameter, value, unit,
                        is_over_range, value_type, source_doc, source_page, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        meas.psi_id,
                        meas.test_id,
                        meas.parameter,
                        meas.value,
                        meas.unit,
                        int(meas.is_over_range),
                        meas.value_type,
                        meas.source_doc,
                        meas.source_page,
                        meas.verification_status,
                    ),
                )

            for finding in MVP_FINDINGS:
                conn.execute(
                    """
                    INSERT INTO findings (
                        psi_id, category, claim, evidence_quote, source_doc, source_page
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        finding.psi_id,
                        finding.category,
                        finding.claim,
                        finding.evidence_quote,
                        finding.source_doc,
                        finding.source_page,
                    ),
                )
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
    from database.repository import get_all_investigations

    loaded = get_all_investigations()
    print(f"Database initialized at: {DB_PATH}")
    print(f"Loaded {len(loaded)} foundational NASA PSI investigations:\n")
    for idx, item in enumerate(loaded, start=1):
        print(
            f"{idx}. [{item['psi_id']}] {item['acronym']} — {item['title']}\n"
            f"   Pillar: {item['safety_pillar']} | Facility: {item['hardware_facility']} | "
            f"DOI: https://doi.org/{item['doi']} | Related: {item['related_psi_ids']}"
        )
