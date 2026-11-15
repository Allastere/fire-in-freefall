"""Complete catalog of the 19 NASA PSI investigations, intelligence profiles, and verified findings."""

import json
from pathlib import Path
from config.settings import DB_PATH, PROCESSED_DATA_DIR, RAW_DATA_DIR
from core.schemas import FindingModel, InvestigationModel
from database.connection import get_connection, init_db

MVP_INVESTIGATIONS: list[InvestigationModel] = [
    InvestigationModel(
        psi_id="PSI-10",
        acronym="ACME Flame Design",
        title="Advanced Combustion via Microgravity Experiments: Flame Design",
        doi="10.60555/w4zy-bt45",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-10",
        citation_text=(
            'Axelbaum RL, Sunderland PB, Urban DL, Stocker DP, Frolov SM. '
            '"Advanced Combustion via Microgravity Experiments / Flame Design(ACME/Flame Design)", '
            "NASA PSI Data Repository, Version 1, https://doi.org/10.60555/w4zy-bt45"
        ),
        safety_pillar="Suppression",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Axelbaum RL, Sunderland PB, Urban DL, Stocker DP, Frolov SM",
        objectives=(
            "Determine soot inception and radiative/chemical-kinetic flame extinction limits for normal and "
            "inverse spherical/cylindrical ethylene diffusion flames as functions of stoichiometric mixture "
            "fraction (Zst), inert dilution (N2/CO2), and pressure in the CIR ACME chamber."
        ),
        summary=(
            "ACME Flame Design executed 327 normal and inverse gaseous ethylene diffusion flame tests in CIR, "
            "demonstrating how stoichiometric mixture fraction (Zst) controls soot-free combustion and "
            "quasi-steady radiative/diffusive extinction boundaries."
        ),
        earth_spinoff_text=(
            "Soot-free high-efficiency industrial burner design through stoichiometric mixture fraction (Zst) "
            "tailoring and oxygen-enhanced clean combustion."
        ),
        related_psi_ids=["PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Maps radiative and convective extinction limits as functions of Zst and N2 dilution.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Quantifies soot-inception thresholds and adiabatic flame temperatures across O2/N2 mixtures.",
            },
        ],
        objective_tags_json=[
            "FLAME_EXTINCTION",
            "ATMOSPHERIC_DILUTION",
            "COMBUSTION_STABILITY",
            "OXYGEN_ENRICHED_ATMOSPHERE",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME Modular Chamber (Spherical porous burner)",
            "shared_hardware_psi_ids": ["PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
            "sensors": ["Mass Flow Controllers (MFC)", "Thin Filament Pyrometry (TFP)", "Radiometers", "Color/Intensified Cameras"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-159", "type": "SHARED_HARDWARE", "note": "Uses identical 6.35 mm spherical porous burner in CIR ACME."},
            {"target_psi_id": "PSI-23", "type": "COMPLEMENTARY_EVIDENCE", "note": "Both study spherical diffusion flame radiative extinction."},
        ],
        limitations_json=[
            "Gaseous ethylene burner experiments; does not directly measure solid polymer pyrolysis or spread.",
            "Inverse flames supply oxidizer from the central burner into fuel/inert mixtures.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-20",
        acronym="ACME BRE",
        title="Advanced Combustion via Microgravity Experiments: Burning Rate Emulator",
        doi="10.60555/vb93-3y72",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-20",
        citation_text=(
            'Quintiere JG, Ris J, Sunderland P, Stocker D. '
            '"Advanced Combustion via Microgravity Experiments - Burning Rate Emulator(ACME BRE)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/vb93-3y72"
        ),
        safety_pillar="Prevention",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Quintiere JG, de Ris J, Sunderland PB, Stocker DP",
        objectives=(
            "Simulate condensed-phase solid and liquid pool burning in microgravity using a flat porous "
            "gas burner whose fuel flow is coupled to measured flame heat flux feedback, identifying "
            "quasi-steady burning and extinction limits across 21%–40% O2."
        ),
        summary=(
            "ACME BRE emulated solid/liquid pool fire heat-feedback physics in CIR across 18 test days, "
            "finding that quasi-steady flat-surface burning in 0g requires elevated ambient oxygen "
            "(>=26.5% O2) and quantifying oscillation onset and flame extinction times."
        ),
        earth_spinoff_text=(
            "Validated B-number mass-transfer flammability scaling for condensed-phase plastics and liquid fuels."
        ),
        related_psi_ids=["PSI-10", "PSI-25", "PSI-26", "PSI-159"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Emulates solid/liquid material heat-feedback vaporization and flammability limits up to 40% O2.",
            },
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Analyzes flame oscillation onset and radiative/diffusive extinction times in quiescent 0g.",
            },
        ],
        objective_tags_json=[
            "MATERIAL_FLAMMABILITY",
            "HEAT_RELEASE",
            "FLAME_EXTINCTION",
            "OXYGEN_ENRICHED_ATMOSPHERE",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME Chamber with 25 mm & 50 mm flat porous Burning Rate Emulator burners",
            "shared_hardware_psi_ids": ["PSI-10", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
            "sensors": ["Heat flux sensor", "Thermocouples", "TFP", "Radiometers"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-25", "type": "COMPLEMENTARY_EVIDENCE", "note": "Bridges gaseous burner physics to solid PMMA burning rates."},
        ],
        limitations_json=[
            "Public PSI CSV provides a 18-row daily test-day summary; run-level extinction times are reported in aggregate empirical fits.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-21",
        acronym="ACME CLD Flame",
        title="Advanced Combustion via Microgravity Experiments: Coflow Laminar Diffusion Flame",
        doi="10.60555/23e1-9950",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-21",
        citation_text=(
            'Long MB, Smooke M, Stocker D. '
            '"Advanced Combustion via Microgravity Experiments / Coflow Laminar Diffusion Flame(ACME CLD Flame)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/23e1-9950"
        ),
        safety_pillar="Prevention",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Long MB, Smooke MD, Stocker DP",
        objectives=(
            "Measure 2D temperature, soot volume fraction, and liftoff/extinction behavior in nitrogen-diluted "
            "methane and ethylene coflow laminar diffusion flames in microgravity."
        ),
        summary=(
            "ACME CLD Flame extended SLICE coflow burner studies into the CIR rack across 32 test days, "
            "mapping flame liftoff, soot formation, and dilution extinction boundaries for CH4 and C2H4."
        ),
        earth_spinoff_text=(
            "Benchmarked multidimensional CFD combustion and soot radiation submodels for practical gas turbines."
        ),
        related_psi_ids=["PSI-106", "PSI-107", "PSI-22", "PSI-10"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Characterizes laminar coflow flame liftoff and soot radiation in microgravity.",
            }
        ],
        objective_tags_json=["COMBUSTION_STABILITY", "SMOKE_GENERATION", "MICROGRAVITY_COMBUSTION", "EARTH_APPLICATIONS"],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME Coflow Burner",
            "shared_hardware_psi_ids": ["PSI-22", "PSI-10", "PSI-20", "PSI-23", "PSI-159"],
            "sensors": ["High-resolution color camera", "MFCs", "Radiometers"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-106", "type": "FOLLOW_UP", "note": "Direct CIR follow-up to the MSG SLICE investigation."},
            {"target_psi_id": "PSI-22", "type": "SHARED_HARDWARE", "note": "Shares ACME coflow burner hardware."},
        ],
        limitations_json=["Daily summary CSV table; gaseous fuel only."],
    ),
    InvestigationModel(
        psi_id="PSI-22",
        acronym="ACME E-FIELD Flames",
        title="Advanced Combustion via Microgravity Experiments: Electric-Field Effects on Laminar Diffusion Flames",
        doi="10.60555/se5a-8c73",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-22",
        citation_text=(
            'Dunn-Rankin D, Stocker D, Chien A. '
            '"Advanced Combustion via Microgravity Experiments Electric-Field Effects on Laminar Diffusion Flames(ACME E-FIELD Flames)", '
            "NASA PSI Data Repository, Version 7, https://doi.org/10.60555/se5a-8c73"
        ),
        safety_pillar="Suppression",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Dunn-Rankin D, Stocker DP, Chien YC",
        objectives=(
            "Investigate how high-voltage electric fields act on flame chemi-ions to drive ion-wind convection, "
            "control soot emission, stabilize liftoff, or induce blowoff extinction in microgravity without buoyancy."
        ),
        summary=(
            "ACME E-FIELD Flames tested 32 test-day configurations in CIR, proving that electric-field ion-driven "
            "convection provides an adjustable body-force analog to buoyancy in 0g and can actively suppress soot "
            "or blow off flames."
        ),
        earth_spinoff_text=(
            "Electrically assisted low-emission burners and non-mechanical flame stabilization/suppression."
        ),
        related_psi_ids=["PSI-21", "PSI-106", "PSI-10", "PSI-20"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Demonstrates active flame blowoff and soot suppression via electric fields in 0g.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "SUPPORTING",
                "explanation": "Provides an ion-driven flow analog to buoyant convection for studying gravity scaling.",
            },
        ],
        objective_tags_json=[
            "COMBUSTION_STABILITY",
            "FLAME_EXTINCTION",
            "GRAVITY_EFFECTS",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME Coflow Burner with high-voltage electrode mesh",
            "shared_hardware_psi_ids": ["PSI-21", "PSI-10", "PSI-20", "PSI-23", "PSI-159"],
            "sensors": ["High-voltage current monitor", "MFCs", "Cameras"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-21", "type": "SHARED_HARDWARE", "note": "Adds high-voltage mesh to ACME coflow burner."},
        ],
        limitations_json=[
            "Electric-field ion-wind is an analog for body-force convection and MUST NOT be treated as a direct Lunar (1/6g) or Martian (3/8g) partial-gravity measurement."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-23",
        acronym="ACME s-Flame",
        title="Advanced Combustion via Microgravity Experiments: Structure and Response of Spherical Diffusion Flames",
        doi="10.60555/k57n-p030",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-23",
        citation_text=(
            'Law CK, Tse S, Stocker D. '
            '"Advanced Combustion via Microgravity Experiments-Structure and Response of Spherical Diffusion Flames(ACME s-Flame)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/k57n-p030"
        ),
        safety_pillar="Suppression",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Law CK, Tse SD, Stocker DP",
        objectives=(
            "Determine quasi-steady convective/chemical-kinetic (low Damköhler) and radiative/chemical-kinetic "
            "(high Damköhler) extinction limits and oscillatory reignition of spherical diffusion flames in CIR."
        ),
        summary=(
            "ACME s-Flame conducted 18 test days with ethylene, methane, and hydrogen spherical flames in CIR "
            "using N2 and He dilution, documenting pulsating radiative extinction and flash reignition cycles."
        ),
        earth_spinoff_text=(
            "Validated chemical-kinetic and radiative heat-loss mechanisms at lean/diluted combustion limits."
        ),
        related_psi_ids=["PSI-10", "PSI-159", "PSI-39", "PSI-69"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Studies radiative and kinetic extinction limits and oscillatory flash reignition under N2/He dilution.",
            }
        ],
        objective_tags_json=[
            "FLAME_EXTINCTION",
            "ATMOSPHERIC_DILUTION",
            "REIGNITION",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME Spherical Porous Burner",
            "shared_hardware_psi_ids": ["PSI-10", "PSI-159", "PSI-20", "PSI-21", "PSI-22"],
            "sensors": ["TFP fiber array", "Thermocouples", "Radiometers", "Intensified camera"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-10", "type": "SHARED_HARDWARE", "note": "Shares ACME spherical porous burner in CIR."},
            {"target_psi_id": "PSI-159", "type": "COMPLEMENTARY_EVIDENCE", "note": "Both observe low-temperature/radiative quenching and reignition."},
        ],
        limitations_json=["Daily summary CSV table; gaseous fuels only."],
    ),
    InvestigationModel(
        psi_id="PSI-25",
        acronym="BASS-II",
        title="Burning and Suppression of Solids - II",
        doi="10.60555/4qc4-de67",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        citation_text=(
            'Ferkul P, Fernandez-Pello C, Miller F, T\'ien J, Bhattachjee S. '
            '"Burning and Suppression of Solids - II(BASS-II)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/4qc4-de67"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="MSG",
        pi_names="Ferkul PV, Fernandez-Pello C, Miller FJ, T'ien JS, Bhattacharjee S, Olson SL",
        objectives=(
            "Determine opposed, concurrent, and stagnation flame spread rates, limiting oxygen concentrations "
            "(LOC/LOI), and low-velocity quenching/blowoff boundaries for solid polymers and fabrics "
            "(PMMA films/slabs/rods/spheres, SIBAL, Nomex III) inside the MSG flow duct."
        ),
        summary=(
            "BASS-II executed 129 microgravity solid-fuel tests in MSG demonstrating that thin PMMA and SIBAL "
            "cotton-fiberglass sustain combustion at low ventilation flows (1–5 cm/s) down to 13.6% O2 in 0g, "
            "below terrestrial upward/downward flammability limits, while producing >1000 ppm CO spikes near quenching."
        ),
        earth_spinoff_text=(
            "Improved spacecraft material screening protocols beyond NASA-STD-6001 Test #1 and advanced "
            "flame-retardant textiles for firefighter protective turnout gear (Project FIRES)."
        ),
        related_psi_ids=["PSI-26", "PSI-98", "PSI-99", "PSI-100", "PSI-107"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "DIRECT",
                "explanation": "Directly measures solid spacecraft material ignition, flame spread rate, and limiting oxygen concentration (13.6%-16.2% O2).",
            },
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "DIRECT",
                "explanation": "Directly tests nitrogen dilution, oxygen depletion, and airflow step-down extinction (quenching vs blowoff).",
            },
        ],
        objective_tags_json=[
            "MATERIAL_SELECTION",
            "MATERIAL_FLAMMABILITY",
            "IGNITION",
            "FLAME_SPREAD",
            "OXYGEN_LIMITS",
            "FLAME_EXTINCTION",
            "GAS_EMISSIONS",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "BASS/SPICE 7.6 cm x 7.6 cm fan-driven flow tunnel inside Microgravity Science Glovebox",
            "shared_hardware_psi_ids": ["PSI-26", "PSI-107", "PSI-106"],
            "sensors": ["CSA-CP (O2, CO),", "Crowcon CO2 analyzer", "Thermocouples", "Radiometer", "Nikon D300s & video camera"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-26", "type": "FOLLOW_UP", "note": "Direct reflight and expansion of BASS in the MSG flow duct."},
            {"target_psi_id": "PSI-98", "type": "COMPARATIVE_STUDY", "note": "Small-scale SIBAL duct burns in BASS-II scaled up to 0.4x0.94 m in SAFFIRE-I."},
            {"target_psi_id": "PSI-107", "type": "SHARED_HARDWARE", "note": "Uses the SPICE flow duct hardware inside MSG."},
        ],
        limitations_json=[
            "Conducted near 1 atm (14.7 psi) in MSG; no reduced total cabin pressure (e.g. 8.2 psi) runs.",
            "CSA-CP CO sensor saturates at 1000 ppm ('OR' / '+OR').",
            "Final O2/CO2/CO readings require post-burn equilibration wait time and occasionally reflect sensor turn-off.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-26",
        acronym="BASS",
        title="Burning and Suppression of Solids",
        doi="10.60555/58h4-dy80",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-26",
        citation_text=(
            'Ferkul P, Takahashi F, T\'ien J, Olson S. '
            '"Burning and Suppression of Solids(BASS)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/58h4-dy80"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="MSG",
        pi_names="Ferkul PV, Takahashi F, T'ien JS, Olson SL",
        objectives=(
            "Examine burning and extinction characteristics of solid fuels (PMMA spheres/slabs/rods, SIBAL fabric, "
            "wax candles) under controlled opposed and concurrent airflows (0–55 cm/s) and N2 dilution in MSG."
        ),
        summary=(
            "BASS executed 122 flight runs in MSG, proving that low-speed microgravity ventilation flows can enhance "
            "solid fuel flammability compared to 1g and mapping the dual quenching/blowoff extinction boundary."
        ),
        earth_spinoff_text=(
            "Improved fire modeling for ventilated electronics bays and spacecraft cabin ducts."
        ),
        related_psi_ids=["PSI-25", "PSI-98", "PSI-99", "PSI-107"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "DIRECT",
                "explanation": "Directly investigates solid fuel ignition and flame spread across airflow velocities in 0g.",
            },
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "DIRECT",
                "explanation": "Investigates airflow cut-off quenching and nitrogen-flow extinguishment of solid fuels.",
            },
        ],
        objective_tags_json=[
            "MATERIAL_FLAMMABILITY",
            "IGNITION",
            "FLAME_SPREAD",
            "FLAME_EXTINCTION",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "BASS/SPICE flow duct inside MSG",
            "shared_hardware_psi_ids": ["PSI-25", "PSI-107", "PSI-106"],
            "sensors": ["Anemometer", "Video and still cameras", "GN2 flow potentiometer"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-25", "type": "FOLLOW_UP", "note": "Precursor to BASS-II using the same MSG flow duct."},
        ],
        limitations_json=[
            "Master CSV lists test IDs and materials; planned ignition intervals (5-10 s, 10-20 s) come from BASS Test Matrix.xlsx."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-39",
        acronym="CFI",
        title="Cool Flames Investigation",
        doi="10.60555/m6pj-a914",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-39",
        citation_text=(
            'Williams F, Dryer F, Farouk T, Nayagam V, Dietrich D. '
            '"Cool Flames Investigation(CFI)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/m6pj-a914"
        ),
        safety_pillar="Suppression",
        fuel_category="Liquid",
        hardware_facility="CIR",
        pi_names="Williams FA, Dryer FL, Farouk TI, Nayagam V, Dietrich DL",
        objectives=(
            "Investigate radiative extinction of hot flames, transition to quasi-steady low-temperature cool flames, "
            "and multi-cycle hot-flame reignition for large n-dodecane, n-decane, and n-heptane droplets up to 3 atm."
        ),
        summary=(
            "CFI recorded 227 droplet combustion runs in CIR/MDCA, quantifying hot-flame and cool-flame burning rate "
            "constants (k_hot, k_cool), extinction droplet diameters, radiative emissions, and repeated reignition "
            "cycles above 2 atm in O2/N2/He atmospheres."
        ),
        earth_spinoff_text=(
            "Low-temperature chemical kinetic mechanisms for HCCI/RCCI high-efficiency clean diesel/biofuel engines."
        ),
        related_psi_ids=["PSI-69", "PSI-68", "PSI-159"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Quantifies radiative hot-flame extinction, cool-flame persistence, and post-extinction reignition hazards in N2/He atmospheres.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Measures hot and cool burning rate constants across pressures (0.5-3 atm) and O2 concentrations.",
            },
        ],
        objective_tags_json=[
            "FLAME_EXTINCTION",
            "REIGNITION",
            "ATMOSPHERIC_DILUTION",
            "HEAT_RELEASE",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "Multi-user Droplet Combustion Apparatus (MDCA) inside CIR",
            "shared_hardware_psi_ids": ["PSI-69", "PSI-68"],
            "sensors": ["Hot-wire igniter", "Narrow-band & wide-band radiometers", "HIBMS/LLL cameras"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-69", "type": "FOLLOW_UP", "note": "Follow-up to FLEX after the discovery of cool flames in 0g."},
            {"target_psi_id": "PSI-159", "type": "COMPLEMENTARY_EVIDENCE", "note": "Extends liquid droplet cool flames (CFI) to gaseous fuels (CFI-G)."},
        ],
        limitations_json=[
            "Liquid alkane droplets (C12H26, C10H22, C7H16); extinction/reignition thresholds cannot be directly applied to solid cabin polymers.",
            "Ignition Time (ms) on the Igniter sheet represents hot-wire energization duration, not ignition delay.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-47",
        acronym="DAFT / DAFT-2",
        title="Dust and Aerosol Measurement Feasibility Test / DAFT-2",
        doi="10.60555/ztgj-d202",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-47",
        citation_text=(
            'Urban DL, Fortenberry C. '
            '"Dust and Aerosol Measurement Feasibility Test / Dust and Aerosol Measurement Feasibility Test-2(DAFT / DAFT-2)", '
            "NASA PSI Data Repository, Version 5, https://doi.org/10.60555/ztgj-d202"
        ),
        safety_pillar="Detection",
        fuel_category="Aerosol/Smoke",
        hardware_facility="MSG",
        pi_names="Urban DL, Fortenberry C",
        objectives=(
            "Validate Condensation Particle Counter (P-Trak) and laser photometer (DustTrak) operation in ISS "
            "microgravity using Arizona Road Dust (ARD) calibration aerosols and measure baseline ISS cabin air particulates."
        ),
        summary=(
            "DAFT and DAFT-2 verified P-Trak (particles/cm3) and DustTrak (mg/m3) performance in 0g across 3 calibration "
            "bags (44 paired time-series points) and established that ambient ISS US Lab cabin air is ultra-clean "
            "(<15 particles/cm3 and <0.005 mg/m3)."
        ),
        earth_spinoff_text=(
            "Portable dual-moment aerosol monitors for cleanrooms and occupational dust/smoke discrimination."
        ),
        related_psi_ids=["PSI-102", "PSI-101"],
        pillar_classifications_json=[
            {
                "pillar": "DETECTION",
                "relevance_type": "SUPPORTING",
                "explanation": "Validates P-Trak and DustTrak aerosol instruments shared with SAME/SAME-R and measures ISS background particle levels.",
            }
        ],
        objective_tags_json=[
            "SENSOR_DEVELOPMENT",
            "SMOKE_DETECTION",
            "AEROSOL_TRANSPORT",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "TSI P-Trak CPC (alcohol wick) & TSI DustTrak laser photometer",
            "shared_hardware_psi_ids": ["PSI-102", "PSI-101"],
            "sensors": ["TSI P-Trak Condensation Particle Counter", "TSI DustTrak Laser Photometer"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-102", "type": "SHARED_HARDWARE", "note": "Validates the P-Trak and DustTrak instruments used in SAME."},
            {"target_psi_id": "PSI-101", "type": "SHARED_HARDWARE", "note": "Provides baseline aerosol instrument calibration for SAME-R."},
        ],
        limitations_json=[
            "Uses Arizona Road Dust (ARD) mechanical test aerosol rather than combustion smoke; ARD particle sizes (1.56-1.70 µm) must not be merged with pyrolysis smoke."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-68",
        acronym="FLEX-2",
        title="Flame Extinguishment Experiment - 2",
        doi="10.60555/byp8-h018",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-68",
        citation_text=(
            'Williams FA, Dryer F, Shaw B, Choi M, Nayagam V, Avedisian T, Dietrich D, Hicks M. '
            '"Flame Extinguishment Experiment - 2(FLEX-2)", '
            "NASA PSI Data Repository, Version 6, https://doi.org/10.60555/byp8-h018"
        ),
        safety_pillar="Suppression",
        fuel_category="Liquid",
        hardware_facility="CIR",
        pi_names="Williams FA, Dryer FL, Shaw BD, Choi MY, Nayagam V, Avedisian CT, Dietrich DL, Hicks MC",
        objectives=(
            "Study bi-component and pure alkane/alcohol droplet burning rates, soot shell formation, convective flow "
            "effects (0.1–5 cm/s), and extinction limits across O2/N2 and O2/He atmospheres (0.5–3.0 atm) in CIR/MDCA."
        ),
        summary=(
            "FLEX-2 expanded droplet combustion tests in CIR/MDCA across 8 pure and bi-component fuel matrices "
            "(iso-octane, n-octane, n-heptane, n-decane, ethanol, 1-propanol, toluene), characterizing radiative "
            "and convective extinction under low-speed flows."
        ),
        earth_spinoff_text=(
            "Multi-component aviation and biofuel spray combustion models."
        ),
        related_psi_ids=["PSI-69", "PSI-39"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Evaluates droplet extinction across O2/N2 and O2/He mixtures and low convective velocities.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Characterizes liquid fuel mixture burning rates and soot shells.",
            },
        ],
        objective_tags_json=[
            "FLAME_EXTINCTION",
            "ATMOSPHERIC_DILUTION",
            "REDUCED_PRESSURE",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "MDCA inside CIR",
            "shared_hardware_psi_ids": ["PSI-69", "PSI-39"],
            "sensors": ["Backlit droplet camera", "Radiometers", "Hot-wire igniters"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-69", "type": "FOLLOW_UP", "note": "Second-generation FLEX campaign in CIR/MDCA."},
            {"target_psi_id": "PSI-39", "type": "SHARED_HARDWARE", "note": "Uses identical CIR/MDCA droplet deployment hardware."},
        ],
        limitations_json=[
            "Public PSI CSV provides an 8-row parameter matrix summary across fuel types rather than individual droplet run logs."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-69",
        acronym="FLEX",
        title="Flame Extinguishment Experiment",
        doi="10.60555/mbq8-0451",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-69",
        citation_text=(
            'Williams FA, Shaw BD, Hicks MC, Nayagam V, Choi MY, Dryer FL, Dietrich D. '
            '"Flame Extinguishment Experiment(FLEX)", '
            "NASA PSI Data Repository, Version 5, https://doi.org/10.60555/mbq8-0451"
        ),
        safety_pillar="Suppression",
        fuel_category="Liquid",
        hardware_facility="CIR",
        pi_names="Williams FA, Shaw BD, Hicks MC, Nayagam V, Choi MY, Dryer FL, Dietrich DL",
        objectives=(
            "Quantify spherical heptane and methanol droplet burning rates, visible flame extinction diameters, "
            "burn times, and inert-gas suppression limits across O2/N2/CO2/He atmospheres in CIR/MDCA."
        ),
        summary=(
            "FLEX executed 274 isolated heptane and methanol droplet burns in CIR/MDCA across varying pressures "
            "(226–2290 mmHg) and O2/N2/CO2/He compositions, discovering two-stage cool flames in 0g and "
            "quantifying diffusive/radiative extinction diameters."
        ),
        earth_spinoff_text=(
            "Supported development of portable fine-water-mist and clean-agent fire extinguishers deployed on ISS "
            "and commercial aircraft."
        ),
        related_psi_ids=["PSI-68", "PSI-39", "PSI-159"],
        pillar_classifications_json=[
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "DIRECT",
                "explanation": "Directly tests CO2, He, and N2 suppressant dilution, reduced pressure, and radiative/diffusive flame extinction.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Quantifies burning rate constants and cool-flame vapor reignition risks.",
            },
        ],
        objective_tags_json=[
            "FIRE_SUPPRESSION",
            "FLAME_EXTINCTION",
            "ATMOSPHERIC_DILUTION",
            "OXYGEN_LIMITS",
            "REDUCED_PRESSURE",
            "REIGNITION",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "MDCA inside CIR",
            "shared_hardware_psi_ids": ["PSI-68", "PSI-39"],
            "sensors": ["High-speed backlit camera", "UV/IR radiometers", "Gas mixing manifold"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-39", "type": "FOLLOW_UP", "note": "Cool flames discovered in FLEX motivated the dedicated CFI investigation."},
            {"target_psi_id": "PSI-68", "type": "FOLLOW_UP", "note": "Extended to convective flows and bi-component fuels in FLEX-2."},
        ],
        limitations_json=[
            "Liquid droplets (Methanol, Heptane); extinction concentrations cannot be assumed identical for solid polymer cabin fires.",
            "In PSI-69_Experimental table_FLEX.csv, the column 'CO initial ambient composition; mole fraction' represents CO2 diluent mole fraction (subscript '2' omitted in ASCII export).",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-98",
        acronym="SAFFIRE-I",
        title="Spacecraft Fire Safety Experiment - I",
        doi="10.60555/0t15-1z43",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
        citation_text=(
            'Urban DL. "Spacecraft Fire Safety Experiment-I(SAFFIRE-I)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/0t15-1z43"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="Saffire/Cygnus",
        pi_names="Urban DL, Ruff GA, Ferkul PV, Olson SL, Meyer ME",
        objectives=(
            "Conduct the first large-scale microgravity flame spread experiment on a 0.406 m x 0.94 m SIBAL "
            "cotton-fiberglass panel in concurrent and opposed 20 cm/s airflow aboard an uncrewed Cygnus spacecraft."
        ),
        summary=(
            "SAFFIRE-I burned two large 40.6 x 94 cm SIBAL fabric panels aboard Cygnus OA-6 at 20 cm/s airflow "
            "and ~21.5% O2 (420 s concurrent burn and 70 s opposed burn), bridging small MSG duct tests to "
            "realistic spacecraft cabin scales."
        ),
        earth_spinoff_text=(
            "Validated confined cabin fire growth models for submarines, aircraft bays, and transit tunnels."
        ),
        related_psi_ids=["PSI-99", "PSI-100", "PSI-25", "PSI-26"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "DIRECT",
                "explanation": "Large-scale spacecraft solid material flame propagation under realistic cabin ventilation.",
            }
        ],
        objective_tags_json=[
            "MATERIAL_FLAMMABILITY",
            "FLAME_SPREAD",
            "IGNITION",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "Saffire/Cygnus",
            "apparatus": "SAFFIRE flow duct module aboard Cygnus OA-6 resupply vehicle",
            "shared_hardware_psi_ids": ["PSI-99", "PSI-100"],
            "sensors": ["Dual video cameras (S1C1/S1C2)", "Thermocouple arrays", "Radiometers", "O2/CO2/pressure sensors"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-99", "type": "FOLLOW_UP", "note": "Followed by multi-sample SAFFIRE-II on Cygnus OA-5."},
            {"target_psi_id": "PSI-25", "type": "SHARED_MATERIAL", "note": "Tests identical SIBAL 75/25 cotton-fiberglass fabric at meter scale vs cm scale."},
        ],
        limitations_json=[
            "CSV does not report final burned length for S1/S2; total sample length must not be divided by burn time without accounting for partial/anchored burning."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-99",
        acronym="SAFFIRE-II",
        title="Spacecraft Fire Experiment - II",
        doi="10.60555/2chp-m469",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-99",
        citation_text=(
            'Urban DL, Ruff G. "Spacecraft Fire Experiment-II(SAFFIRE-II)", '
            "NASA PSI Data Repository, Version 5, https://doi.org/10.60555/2chp-m469"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="Saffire/Cygnus",
        pi_names="Urban DL, Ruff GA",
        objectives=(
            "Evaluate oxygen-limit and thickness effects on 9 spacecraft solid samples (Silicone sheets 0.27–1.03 mm, "
            "SIBAL fabric, PMMA/Nomex composite, and profiled/thick PMMA slabs) at 20 cm/s airflow in 0g vs 1g."
        ),
        summary=(
            "SAFFIRE-II tested 9 solid samples (5 x 29 cm) on Cygnus OA-5 with direct 1g comparison data, "
            "measuring 0g concurrent spread rates of 2.1–2.6 mm/s on SIBAL, slow 0.01–0.04 mm/s base regression "
            "on thick PMMA, and self-extinguishment of silicone sheets in 0g that burned completely in 1g."
        ),
        earth_spinoff_text=(
            "Improved thickness-dependent material flammability qualification standards (NASA-STD-6001)."
        ),
        related_psi_ids=["PSI-98", "PSI-100", "PSI-25", "PSI-26"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "DIRECT",
                "explanation": "Directly compares 0g and 1g flammability, burn length, and flame spread rates across 9 spacecraft materials.",
            }
        ],
        objective_tags_json=[
            "MATERIAL_SELECTION",
            "MATERIAL_FLAMMABILITY",
            "FLAME_SPREAD",
            "IGNITION",
            "GRAVITY_EFFECTS",
            "MICROGRAVITY_COMBUSTION",
            "NORMAL_GRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "Saffire/Cygnus",
            "apparatus": "SAFFIRE multi-sample flow duct aboard Cygnus OA-5",
            "shared_hardware_psi_ids": ["PSI-98", "PSI-100"],
            "sensors": ["Top/side cameras", "Hot-wire igniters (80 W / 97 W)", "CO2/O2 sensors"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-98", "type": "FOLLOW_UP", "note": "Second flight in the SAFFIRE series."},
            {"target_psi_id": "PSI-100", "type": "FOLLOW_UP", "note": "Followed by SAFFIRE-III at higher 30 cm/s airflow."},
        ],
        limitations_json=[
            "In PSI-99 CSV, the header 'µ-g Spread Length' contains direct 0g spread rates ('2.1 mm/s', '2.6 mm/s') for samples 2-5 and 2-6.",
            "Percent O2 in SAFFIRE-II CSV was derived from measured CO2 production referenced to ISS initial O2 (Note 1).",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-100",
        acronym="SAFFIRE-III",
        title="Spacecraft Fire Experiment - III",
        doi="10.60555/040q-4h36",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-100",
        citation_text=(
            'Urban DL. "Spacecraft Fire Experiment-III(SAFFIRE-III)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/040q-4h36"
        ),
        safety_pillar="Prevention",
        fuel_category="Solid",
        hardware_facility="Saffire/Cygnus",
        pi_names="Urban DL, Ruff GA",
        objectives=(
            "Measure large-scale (40.6 x 94 cm) SIBAL fabric flame spread in concurrent and opposed directions "
            "at elevated 30 cm/s ventilation velocity aboard Cygnus."
        ),
        summary=(
            "SAFFIRE-III tested two large 40.6 x 94 cm SIBAL panels at 30 cm/s airflow (concurrent and opposed), "
            "extending the SAFFIRE-I (20 cm/s) large-scale spacecraft fire dataset."
        ),
        earth_spinoff_text=(
            "Large-scale validation of ventilation-limited fire dynamics in sealed modules."
        ),
        related_psi_ids=["PSI-98", "PSI-99", "PSI-25"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "DIRECT",
                "explanation": "Large-scale SIBAL fabric flammability at 30 cm/s ventilation flow.",
            }
        ],
        objective_tags_json=[
            "MATERIAL_FLAMMABILITY",
            "FLAME_SPREAD",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "Saffire/Cygnus",
            "apparatus": "SAFFIRE module aboard Cygnus OA-7",
            "shared_hardware_psi_ids": ["PSI-98", "PSI-99"],
            "sensors": ["Dual cameras (S1C1/S1C2)", "Thermocouples", "Radiometers"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-98", "type": "COMPARATIVE_STUDY", "note": "Identical large SIBAL panel tested at 30 cm/s vs 20 cm/s in SAFFIRE-I."},
        ],
        limitations_json=[
            "Public PSI CSV lists sample dimensions, airflow (30 cm/s), and flow direction, but omits numerical burn time and O2% columns."
        ],
    ),
    InvestigationModel(
        psi_id="PSI-101",
        acronym="SAME-R",
        title="Smoke Aerosol Measurement Experiment - Reflight",
        doi="10.60555/2np7-jv14",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
        citation_text=(
            'Urban D, Yuan Z, Yang JC, Cleary T, Mulholland GW, Fortenberry C. '
            '"Smoke Aerosol Measurement Experiment-Reflight(SAME-R)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/2np7-jv14"
        ),
        safety_pillar="Detection",
        fuel_category="Aerosol/Smoke",
        hardware_facility="MSG",
        pi_names="Urban DL, Yuan ZG, Yang JC, Cleary TG, Mulholland GW, Fortenberry C",
        objectives=(
            "Characterize unaged and aged microgravity pyrolysis smoke particle size distributions (GMD, CMD, MMD) "
            "across 109 runs of 6 spacecraft materials (Kapton, Teflon, Silicone, Pyrell, Lampwick cellulose, DBP) "
            "using moment instruments, SMPS, and uncontaminated TEM grids."
        ),
        summary=(
            "SAME-R executed 109 non-flaming overheat smoke tests in MSG at 0–8.1 cm/s airflow and 0–720 s aging, "
            "proving that Kapton and Teflon generate ultrafine particles (42–232 nm) poorly detected by ISS optical "
            "scattering detectors, whereas silicone and cellulose coagulate into larger (>350–619 nm) aerosols."
        ),
        earth_spinoff_text=(
            "Multi-moment dust-immune early warning smoke detectors for cleanrooms, mines, and aviation."
        ),
        related_psi_ids=["PSI-102", "PSI-47"],
        pillar_classifications_json=[
            {
                "pillar": "DETECTION",
                "relevance_type": "DIRECT",
                "explanation": "Directly measures spacecraft pyrolysis smoke particle diameters, aging coagulation, and ISS/STS detector responses across 109 runs.",
            }
        ],
        objective_tags_json=[
            "SMOKE_GENERATION",
            "AEROSOL_TRANSPORT",
            "SMOKE_DETECTION",
            "SENSOR_DEVELOPMENT",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "SAME aerosol generation duct, aging chamber, and SMPS drum in MSG",
            "shared_hardware_psi_ids": ["PSI-102", "PSI-47"],
            "sensors": [
                "STS Ionization Detector",
                "ISS Honeywell Laser Forward-Scattering Detector",
                "TSI P-Trak CPC",
                "TSI DustTrak Photometer",
                "Scanning Mobility Particle Sizer (SMPS)",
                "Thermal Precipitator (TEM grids)",
            ],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-102", "type": "FOLLOW_UP", "note": "Reflight of SAME with clean TEM grids and added SMPS."},
            {"target_psi_id": "PSI-47", "type": "SHARED_HARDWARE", "note": "Shares P-Trak and DustTrak aerosol monitors."},
        ],
        limitations_json=[
            "Duration (sec) = 60 s in SAME-R.csv is programmed non-flaming pyrolysis wire heating duration, NOT flame burning duration.",
            "Table 1 (p.78) reports baseline material-level aggregate diameters rather than run-by-run values for all 109 CSV rows.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-102",
        acronym="SAME",
        title="Smoke and Aerosol Measurement Experiment",
        doi="10.60555/gd4k-8h62",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-102",
        citation_text=(
            'Urban D, Mulholland G, Cleary T, Yang J, Fortenberry C. '
            '"Smoke and Aerosol Measurement Experiment(SAME)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/gd4k-8h62"
        ),
        safety_pillar="Detection",
        fuel_category="Aerosol/Smoke",
        hardware_facility="MSG",
        pi_names="Urban DL, Mulholland GW, Cleary TG, Yang JC, Fortenberry C",
        objectives=(
            "Measure particle size distributions (GMD, AMD, MMD) of fresh and aged smoke from overheated "
            "spacecraft polymers (Kapton, Teflon, Silicone, Lampwick, Santoprene, Douglas Fir) in 0g vs 1g "
            "and evaluate ISS and Space Shuttle smoke detector sensitivity."
        ),
        summary=(
            "SAME demonstrated that absence of buoyant cooling in 0g increases pyrolysis residence time, "
            "producing smoke particles ~50% larger than in 1g (80–606 nm across Kapton, Teflon, Silicone, "
            "and Lampwick), and modeled smoke transit delays to ISS US Lab detectors using LES."
        ),
        earth_spinoff_text=(
            "Multi-criteria optical/ionization smoke detection algorithms for high-airflow facilities."
        ),
        related_psi_ids=["PSI-101", "PSI-47"],
        pillar_classifications_json=[
            {
                "pillar": "DETECTION",
                "relevance_type": "DIRECT",
                "explanation": "Directly measures 0g smoke particle size distributions, polymer weight loss rates, and ISS/STS detector thresholds.",
            }
        ],
        objective_tags_json=[
            "SMOKE_GENERATION",
            "AEROSOL_TRANSPORT",
            "SMOKE_DETECTION",
            "SENSOR_DEVELOPMENT",
            "GRAVITY_EFFECTS",
            "MICROGRAVITY_COMBUSTION",
            "NORMAL_GRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "SAME smoke duct & aging chamber inside MSG",
            "shared_hardware_psi_ids": ["PSI-101", "PSI-47"],
            "sensors": ["STS Ionization Detector", "ISS Laser Scattering Detector", "P-Trak CPC", "DustTrak Photometer", "TEM Precipitator"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-101", "type": "FOLLOW_UP", "note": "Followed by SAME-R reflight."},
            {"target_psi_id": "PSI-47", "type": "SHARED_HARDWARE", "note": "Shares P-Trak and DustTrak instruments."},
        ],
        limitations_json=[
            "TEM grids on SAME-1 experienced pre-flight assembly particle contamination (resolved in SAME-R).",
            "Detector alarm response times in the report (pp. 65-66) are LES numerical predictions rather than live cabin fire tests.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-106",
        acronym="SLICE",
        title="Structure and Liftoff In Combustion Experiment",
        doi="10.60555/pm12-rg61",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-106",
        citation_text=(
            'Long M, Smooke MD, Takahashi F, Stocker D. '
            '"Structure and Liftoff In Combustion Experiment(SLICE)", '
            "NASA PSI Data Repository, Version 3, https://doi.org/10.60555/pm12-rg61"
        ),
        safety_pillar="Prevention",
        fuel_category="Gas",
        hardware_facility="MSG",
        pi_names="Long MB, Smooke MD, Takahashi F, Stocker DP",
        objectives=(
            "Measure 2D temperature fields, soot volume fractions, and flame liftoff/blowoff heights in "
            "co-flowing laminar methane and ethylene jet diffusion flames inside the MSG flow duct."
        ),
        summary=(
            "SLICE conducted 12 test sessions in MSG with pure and N2-diluted methane and ethylene coflow flames, "
            "providing foundational 0g flame structure and liftoff datasets prior to ACME CLD Flame."
        ),
        earth_spinoff_text=(
            "Quantitative optical diagnostics (color-ratio pyrometry) for industrial burner validation."
        ),
        related_psi_ids=["PSI-21", "PSI-107", "PSI-25", "PSI-26"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Studies laminar coflow flame liftoff and stabilization in the MSG flow duct.",
            }
        ],
        objective_tags_json=["COMBUSTION_STABILITY", "MICROGRAVITY_COMBUSTION"],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "SPICE/SLICE coflow duct inside MSG",
            "shared_hardware_psi_ids": ["PSI-107", "PSI-25", "PSI-26"],
            "sensors": ["Digital color camera", "Thin filament pyrometry", "Airflow fan"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-21", "type": "FOLLOW_UP", "note": "Continued at higher pressures/flows in CIR as ACME CLD Flame."},
            {"target_psi_id": "PSI-107", "type": "SHARED_HARDWARE", "note": "Uses the SPICE flow duct in MSG."},
        ],
        limitations_json=["Public PSI CSV lists 12 test session dates and fuel types without run-by-run numerical columns."],
    ),
    InvestigationModel(
        psi_id="PSI-107",
        acronym="SPICE",
        title="Smoke Point In Co-flow Experiment",
        doi="10.60555/9kbh-e962",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-107",
        citation_text=(
            'Urban D, Sunderland P. "Smoke Point In Co-flow Experiment(SPICE)", '
            "NASA PSI Data Repository, Version 4, https://doi.org/10.60555/9kbh-e962"
        ),
        safety_pillar="Detection",
        fuel_category="Gas",
        hardware_facility="MSG",
        pi_names="Urban DL, Sunderland PB, Yuan ZG",
        objectives=(
            "Determine laminar smoke points (critical fuel flow rates and flame lengths at onset of soot emission) "
            "for gaseous hydrocarbon fuels (ethylene, propane, propylene, methane, n-butane) across nozzle diameters "
            "and coflow air velocities in MSG."
        ),
        summary=(
            "SPICE logged 469 measurement rows across 153 unique microgravity burns in MSG, establishing the "
            "transition from non-sooting to sooting flames across coflow velocities (2–40 cm/s) and fuel flow rates."
        ),
        earth_spinoff_text=(
            "Soot-point scaling models for aviation combustors and clean-burning gaseous flares."
        ),
        related_psi_ids=["PSI-106", "PSI-25", "PSI-26", "PSI-102"],
        pillar_classifications_json=[
            {
                "pillar": "DETECTION",
                "relevance_type": "INDIRECT",
                "explanation": "Quantifies soot-emission onset (smoke point) conditions that govern soot aerosol production in 0g flames.",
            },
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Characterizes radiative heat loss transition at the soot point in ventilated coflow.",
            },
        ],
        objective_tags_json=[
            "SMOKE_GENERATION",
            "COMBUSTION_STABILITY",
            "MICROGRAVITY_COMBUSTION",
        ],
        hardware_relationships_json={
            "facility": "MSG",
            "apparatus": "SPICE fan-driven flow duct in MSG (later reused for SLICE, BASS, and BASS-II)",
            "shared_hardware_psi_ids": ["PSI-106", "PSI-25", "PSI-26"],
            "sensors": ["Mass flow controller", "Anemometer", "Digital still & video cameras"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-25", "type": "SHARED_HARDWARE", "note": "The SPICE flow duct in MSG was modified and reused for BASS and BASS-II."},
        ],
        limitations_json=[
            "PSI-107 CSV contains 469 camera-frame rows spanning 153 unique burns (GMT date + GMT ignition + GMT Flame Off); burning duration must be deduplicated per unique burn.",
            "Fuel Rate (mg/s) is controlled gaseous burner supply rate, not solid material mass loss rate.",
        ],
    ),
    InvestigationModel(
        psi_id="PSI-159",
        acronym="ACME CFI-G",
        title="Advanced Combustion via Microgravity Experiments: Cool Flames Investigation with Gases",
        doi="10.60555/cyt1-kh64",
        psi_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-159",
        citation_text=(
            'Sunderland PB, Axelbaum RL, Williams F, Stocker DP. '
            '"Advanced Combustion via Microgravity Experiments / Cool Flames Investigation with Gases(ACME CFI-G)", '
            "NASA PSI Data Repository, Version 1, https://doi.org/10.60555/cyt1-kh64"
        ),
        safety_pillar="Multi",
        fuel_category="Gas",
        hardware_facility="CIR",
        pi_names="Sunderland PB, Axelbaum RL, Williams FA, Stocker DP",
        objectives=(
            "Produce and characterize the first gas-fueled spherical cool diffusion flames (CDFs) and map "
            "hot-flame ignition, self-extinguishment (SE), and cool-flame stability for ethane, propane, and "
            "n-butane across pressures (0.3–3 bar) and oxygen mole fractions up to 0.85 in CIR."
        ),
        summary=(
            "ACME CFI-G executed 333 active normal and inverse flame tests (within 1,194 CSV rows) in CIR, "
            "achieving the first observation of gas-fueled spherical cool diffusion flames (n-butane at 2 bar, "
            "XO2=0.39), measuring autoignition onset at 550 K, and mapping extinction boundaries across 13%–85% O2."
        ),
        earth_spinoff_text=(
            "Low-temperature autoignition and cool-flame kinetic models (Cantera/CRECK validation) for clean engines."
        ),
        related_psi_ids=["PSI-39", "PSI-10", "PSI-20", "PSI-23", "PSI-69"],
        pillar_classifications_json=[
            {
                "pillar": "PREVENTION",
                "relevance_type": "INDIRECT",
                "explanation": "Maps hot ignition, flash ignition, and cool-flame autoignition (550 K) across pressures and elevated O2.",
            },
            {
                "pillar": "SUPPRESSION",
                "relevance_type": "INDIRECT",
                "explanation": "Characterizes self-extinguishment (SE), transition to invisible cool flames, and catalytic hot-flame reignition.",
            },
        ],
        objective_tags_json=[
            "IGNITION",
            "FLAME_EXTINCTION",
            "REIGNITION",
            "OXYGEN_ENRICHED_ATMOSPHERE",
            "REDUCED_PRESSURE",
            "MICROGRAVITY_COMBUSTION",
            "EARTH_APPLICATIONS",
        ],
        hardware_relationships_json={
            "facility": "CIR",
            "apparatus": "ACME 6.35 mm spherical porous burner in CIR",
            "shared_hardware_psi_ids": ["PSI-10", "PSI-23", "PSI-20", "PSI-21", "PSI-22"],
            "sensors": ["Intensified UV/visible camera", "Radiometers", "Short/far and long/near Type-B thermocouple rakes"],
        },
        cross_relationships_json=[
            {"target_psi_id": "PSI-39", "type": "FOLLOW_UP", "note": "Extends liquid droplet CFI to non-evaporating gaseous spherical flames."},
            {"target_psi_id": "PSI-10", "type": "SHARED_HARDWARE", "note": "Reuses ACME spherical burner and gas delivery system in CIR."},
        ],
        limitations_json=[
            "In Inverse Flames, XO2 is the oxidizer stream concentration flowing from the spherical burner into ambient fuel/N2, NOT cabin ambient O2.",
            "89 runs terminated by operator Flow Termination ('FT') are right-censored and must not be treated as natural self-extinguishment ('SE').",
            "Platinum in the exposed Type-B thermocouple on the long rake caused unwanted catalytic hot-flame reignition on GMT 291.",
        ],
    ),
]


MVP_FINDINGS: list[FindingModel] = [
    FindingModel(
        psi_id="PSI-25",
        category="Flammability Limit",
        finding_title="Sub-Terrestrial 0g Oxygen Limit (13.6% O2) at Low Ventilation Flows",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="OXYGEN_LIMITS",
        claim=(
            "In microgravity (0g) at low ventilation flows (1–5 cm/s), solid PMMA and SIBAL fabrics sustain "
            "flame spread down to 13.6% calibrated O2, significantly below 1g upward/downward limits (15.4–19% O2)."
        ),
        evidence_quote=(
            "Minimum oxygen concentration sustaining flame spread in microgravity reached 13.6% O2 at low opposed flow velocities."
        ),
        source_doc="BASS-II Summary Report.pdf",
        source_page=81,
    ),
    FindingModel(
        psi_id="PSI-25",
        category="Toxicity",
        finding_title="Incomplete Combustion CO Saturation (>1000 ppm) Near Quenching",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="GAS_EMISSIONS",
        claim=(
            "Near-quenching low-O2 microgravity burns produce severe incomplete combustion spikes where "
            "CO exceeds the 1000 ppm CSA-CP sensor saturation limit ('OR')."
        ),
        evidence_quote=(
            "When Final CO (ppm) reads 'OR' or '+OR', carbon monoxide exceeded the 1000 ppm upper limit of the analyzer."
        ),
        source_doc="BASS-II data FAQ.docx",
        source_page=3,
    ),
    FindingModel(
        psi_id="PSI-25",
        category="Suppression",
        finding_title="Dual Low-Flow Quenching and High-Flow Blowoff Extinction Regimes",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Suppression",
        objective_tag="FLAME_EXTINCTION",
        claim=(
            "Solid fuels in microgravity exhibit two distinct airflow extinction boundaries: radiative/diffusive "
            "quenching when ventilation is stepped down below ~0.5–3 cm/s, and convective blowoff at high flow rates."
        ),
        evidence_quote=(
            "Along the blowoff branch (a > 10 s-1), fuel vaporization parallels total heat flux; at low flow, radiative heat loss quenches the flame."
        ),
        source_doc="BASS-II Summary Report.pdf",
        source_page=94,
    ),
    FindingModel(
        psi_id="PSI-26",
        category="Flammability Limit",
        finding_title="Ventilation Enhancement of Microgravity Solid Combustion",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="FLAME_SPREAD",
        claim=(
            "Low-speed forced airflow (1–10 cm/s) in microgravity replenishes oxidizer without buoyant cooling losses, "
            "allowing solid PMMA spheres and SIBAL fabrics to burn more vigorously than under quiescent or 1g conditions."
        ),
        evidence_quote=(
            "Microgravity flame spread and burning rates peak at intermediate forced flow velocities where oxygen transport balances radiative loss."
        ),
        source_doc="ISS Denver 2013-BASS.pdf",
        source_page=50,
    ),
    FindingModel(
        psi_id="PSI-69",
        category="Suppression",
        finding_title="CO2 vs Helium Inerting and Cool-Flame Persistence in Droplet Extinction",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Suppression",
        objective_tag="ATMOSPHERIC_DILUTION",
        claim=(
            "Radiative extinction of hot liquid droplet flames in CO2/He/N2-diluted 0g atmospheres frequently "
            "transitions into invisible low-temperature cool flames rather than complete chemical extinguishment."
        ),
        evidence_quote=(
            "Following visible radiative extinction of n-heptane droplets in CIR/MDCA, droplet regression continued steadily via cool-flame chemistry."
        ),
        source_doc="20130013847_FLEX.pdf",
        source_page=12,
    ),
    FindingModel(
        psi_id="PSI-39",
        category="Suppression",
        finding_title="Multi-Cycle Hot-Flame Reignition Following Radiative Extinction",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Suppression",
        objective_tag="REIGNITION",
        claim=(
            "At pressures above 2 atm in O2/N2/He mixtures, large alkane droplets undergo multiple reignition "
            "cycles where hot flames radiatively extinguish into cool flames (~5 s) and spontaneously reignite back into hot flames."
        ),
        evidence_quote=(
            "When pressure is increased above 2 atm, multiple reignition cycles were observed, where first the hot flame extinguishes due to radiative heat loss followed by cool flame, and then reignition to a hot-flame."
        ),
        source_doc="CFI Science Final Report.pdf",
        source_page=6,
    ),
    FindingModel(
        psi_id="PSI-102",
        category="Detection",
        finding_title="Microgravity Smoke Particle Enlargement and ISS Detector Blind Spots",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Detection",
        objective_tag="SMOKE_DETECTION",
        claim=(
            "Smoke particles generated in 0g are ~50% larger than in 1g due to longer pyrolysis residence times; "
            "however, Kapton (80 nm GMD) and Teflon (170 nm GMD) particles remain below the 300 nm minimum sensitivity of ISS laser-scattering detectors."
        ),
        evidence_quote=(
            "The small diameters for the Kapton and Teflon will make detection of this smoke challenging for light scattering devices, whereas lamp wick and silicone generate large signals."
        ),
        source_doc="SAME Final Science report  03 18 10 with papers attached.pdf",
        source_page=27,
    ),
    FindingModel(
        psi_id="PSI-101",
        category="Detection",
        finding_title="Aerosol Aging Coagulation and Low-Airflow Particle Growth in Avionics Bays",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Detection",
        objective_tag="AEROSOL_TRANSPORT",
        claim=(
            "Aging smoke for 720 s and reducing duct velocity from 8 to 2 cm/s substantially increases count mean "
            "and mass mean diameters via coagulation, proving that smoke trapped in unventilated avionics enclosures "
            "has a markedly different size signature than ventilated cabin smoke."
        ),
        evidence_quote=(
            "These figures show a strong trend of increased particle size at low flow rates. This indicates that smoke trapped in an avionics enclosure can be expected to be substantially larger."
        ),
        source_doc="SAMER_Final 0602 2014.pdf",
        source_page=79,
    ),
    FindingModel(
        psi_id="PSI-47",
        category="Detection",
        finding_title="Ultra-Low ISS Cabin Particulate Baseline and Dust vs Smoke Sizing",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Detection",
        objective_tag="SENSOR_DEVELOPMENT",
        claim=(
            "ISS US Lab cabin air averages <15 particles/cm3 (P-Trak) and <0.005 mg/m3 (DustTrak), while mechanical "
            "Arizona Road Dust exhibits mean diameters of 1.56–1.70 µm, allowing sub-micrometer size discrimination between pyrolysis smoke and cabin dust."
        ),
        evidence_quote=(
            "Particulates averaging fewer than 0.005 mg/m3 from the DustTrak and fewer than 15 particles/cm3 from the P-Trak are typical in the ISS US Lab."
        ),
        source_doc="daft_fact_sheet_final1.pdf",
        source_page=2,
    ),
    FindingModel(
        psi_id="PSI-98",
        category="Flammability Limit",
        finding_title="Full-Scale Cygnus Cabin Flame Spread Validation (SAFFIRE-I)",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="FLAME_SPREAD",
        claim=(
            "Full-scale 0.406 x 0.94 m SIBAL fabric burns on Cygnus OA-6 sustained concurrent flame spread for 420 s "
            "and opposed spread for 70 s at 20 cm/s airflow, confirming small-duct MSG flammability predictions at vehicle scale."
        ),
        evidence_quote=(
            "Sample S1 (SIBAL Fabric, 40.6 x 94 cm) burned for 420 s in concurrent 20 cm/s airflow at 21.5-21.7% O2."
        ),
        source_doc="PSI-98_Experimental table_SAFFIRE-1.csv",
        source_page=1,
    ),
    FindingModel(
        psi_id="PSI-99",
        category="Partial Gravity",
        finding_title="0g vs 1g Silicone Self-Extinguishment and SIBAL/PMMA Spread Rates (SAFFIRE-II)",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="GRAVITY_EFFECTS",
        claim=(
            "In SAFFIRE-II, thin silicone sheets (0.27–0.61 mm) that burned completely with acceleratory or 0.6–1.2 mm/s "
            "spread in 1g self-extinguished immediately in 0g at 20 cm/s, while SIBAL spread steadily at 2.1–2.6 mm/s in 0g."
        ),
        evidence_quote=(
            "Samples 2-1 to 2-4 (Silicone) showed insignificant burn time (~0 cm) in µ-g vs Complete burn (0.6-1.2 mm/s or Acceleratory) in 1-g; Samples 2-5 and 2-6 (SIBAL) spread at 2.1 and 2.6 mm/s in µ-g."
        ),
        source_doc="PSI-99_Experimental table_SAFFIRE-2.csv",
        source_page=1,
    ),
    FindingModel(
        psi_id="PSI-159",
        category="Suppression",
        finding_title="First Observation of Gas-Fueled Spherical Cool Diffusion Flames & 550 K Autoignition",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Suppression",
        objective_tag="REIGNITION",
        claim=(
            "ACME CFI-G observed spherical gas-fueled cool diffusion flames for the first time (normal n-butane at 2 bar, "
            "XO2=0.39), measured autoignition onset at 550 K (vs 885 K CRECK model prediction), and documented catalytic "
            "hot-flame reignition from exposed platinum thermocouples."
        ),
        evidence_quote=(
            "Spherical CDFs burning gases were observed for the first time... Autoignition first occurred at 550 K. Cantera autoignition simulations with the CRECK mechanism predicted 885 K, which is significantly higher than observed."
        ),
        source_doc="PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf",
        source_page=23,
    ),
    FindingModel(
        psi_id="PSI-20",
        category="Flammability Limit",
        finding_title="Elevated Oxygen Requirement (>=26.5% O2) for Quasi-Steady Flat Pool Burning in 0g",
        finding_type="DIRECT_EXPERIMENTAL",
        safety_pillar="Prevention",
        objective_tag="OXYGEN_ENRICHED_ATMOSPHERE",
        claim=(
            "Using the Burning Rate Emulator (BRE) in CIR, quasi-steady burning on a flat surface representing a condensed-phase "
            "pool fire required nominal ambient oxygen mole fractions of 26.5% O2 and above in microgravity."
        ),
        evidence_quote=(
            "Quasi-steady burning on a flat surface, representing a pool fire, can exist in microgravity. Ambient oxygen mole fraction plays the most significant role... observed for nominal ambient oxygen mole fractions of 0.265 and above."
        ),
        source_doc="BRE_final_report_20220201.pdf",
        source_page=39,
    ),
    FindingModel(
        psi_id="PSI-22",
        category="Partial Gravity",
        finding_title="Electric-Field Ion-Driven Convection as a Body-Force Buoyancy Analog in 0g",
        finding_type="AUTHOR_INTERPRETATION",
        safety_pillar="Prevention",
        objective_tag="GRAVITY_EFFECTS",
        claim=(
            "High-voltage electric fields acting on flame chemi-ions induce controllable ion-driven convective flows "
            "in 0g that reduce soot and modify extinction limits, acting as an experimental body-force analog but not a direct partial-gravity measurement."
        ),
        evidence_quote=(
            "An electric field can strongly influence flames because of its effect on the chemi-ions produced in the reaction zone, generating ion-driven flows."
        ),
        source_doc="E-FIELD Flames Final Report.pdf",
        source_page=4,
    ),
    FindingModel(
        psi_id="PSI-25",
        category="Research Limitation",
        finding_title="Absence of Direct Lunar (1/6g) and Martian (3/8g) Partial-Gravity Data in PSI",
        finding_type="RESEARCH_LIMITATION",
        safety_pillar="Prevention",
        objective_tag="GRAVITY_EFFECTS",
        claim=(
            "Direct partial-gravity combustion experiments at Lunar (0.16g) and Martian (0.38g) gravity are currently "
            "unavailable in the NASA PSI archive; flammability in partial gravity is non-monotonic and must be bounded using 0g low-flow data until future campaigns (e.g. LUCI, FM2) fly."
        ),
        evidence_quote=(
            "Low-velocity opposed and concurrent microgravity tests demonstrate that convective氧 transport at 1-5 cm/s yields lower oxygen limits (13.6% O2) than 1g buoyant flow."
        ),
        source_doc="BASS-II Summary Report.pdf",
        source_page=74,
    ),
]


def seed_database(db_path: Path | str = DB_PATH) -> None:
    """Initialize schema and idempotently seed all 19 official NASA PSI investigations and verified findings."""
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
                        objectives, summary, earth_spinoff_text, related_psi_ids,
                        pi_names, pillar_classifications_json, objective_tags_json,
                        hardware_relationships_json, cross_relationships_json, limitations_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        inv.pi_names,
                        inv.pillar_classifications_json,
                        inv.objective_tags_json,
                        inv.hardware_relationships_json,
                        inv.cross_relationships_json,
                        inv.limitations_json,
                    ),
                )

            conn.execute("DELETE FROM findings")
            for finding in MVP_FINDINGS:
                conn.execute(
                    """
                    INSERT INTO findings (
                        psi_id, category, claim, evidence_quote, source_doc, source_page,
                        finding_title, finding_type, safety_pillar, objective_tag
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        finding.psi_id,
                        finding.category,
                        finding.claim,
                        finding.evidence_quote,
                        finding.source_doc,
                        finding.source_page,
                        finding.finding_title,
                        finding.finding_type,
                        finding.safety_pillar,
                        finding.objective_tag,
                    ),
                )
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
    from database.repository import get_all_investigations

    loaded = get_all_investigations()
    print(f"Database initialized at: {DB_PATH}")
    print(f"Loaded {len(loaded)} official NASA PSI investigations:\n")
    for idx, item in enumerate(loaded, start=1):
        print(
            f"{idx}. [{item['psi_id']}] {item['acronym']} — {item['title']}\n"
            f"   Pillar: {item['safety_pillar']} | Facility: {item['hardware_facility']} | "
            f"DOI: https://doi.org/{item['doi']} | Related: {item['related_psi_ids']}"
        )
