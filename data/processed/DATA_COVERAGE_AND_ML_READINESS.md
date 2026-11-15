# NASA PSI Expanded Scientific Data Collection & ML Readiness Report

- **Database Path:** `data/database/research.db`
- **Total NASA PSI Investigations:** `19`
- **Total Normalized Experimental Runs:** `1810`
- **Total Verified EAV Measurements:** `6199`
- **Total Verified Literature Findings:** `15`
- **Total Tracked Source Files (SHA-256):** `78`

---

## Section 29 — Updated Data Coverage Report Across NASA Safety Pillars

### Pillar 1 — Fire Prevention (Materials Flammability, Ignition & Flame Spread)
- **Core Investigations:** `PSI-25` (BASS-II), `PSI-26` (BASS), `PSI-98` (SAFFIRE-I), `PSI-99` (SAFFIRE-II), `PSI-100` (SAFFIRE-III), `PSI-20` (ACME BRE), `PSI-21` (ACME CLD Flame), `PSI-22` (ACME E-FIELD), `PSI-23` (ACME s-Flame), `PSI-39` (CFI), `PSI-68` (FLEX-2), `PSI-106` (SLICE), `PSI-107` (SPICE), `PSI-159` (ACME CFI-G).
- **Extracted Prevention Parameters:**
  - `burning_duration_s`: `808` measurements (`663` `ML_ELIGIBLE`, `145` `EVIDENCE_ONLY`) across `PSI-39`, `PSI-69`, `PSI-98`, `PSI-99`, `PSI-107` (deduplicated from 469 camera frames to 153 unique burns), and `PSI-159` (excluding `burn time = 0` no-ignition rows; `FT` rows tagged `censored_ft` / `EVIDENCE_ONLY`). (`PSI-101` 60 s heating duration is separated into `pyrolysis_heating_duration_s`: `67` rows).
  - `burning_rate_constant_mm2_s`: `533` droplet regression rate constant ($K$) measurements across `PSI-39` (CFI) and `PSI-69` (FLEX).
  - `fuel_mass_flow_rate_g_s` (`471` rows in `PSI-10`, `PSI-107`, `PSI-159`) & `mass_burning_rate_g_s` (`155` rows in `PSI-159`, `PSI-25`).
  - `ignition_time_s`: `39` measurements across `PSI-26` (BASS igniter-on to ignition intervals) and `PSI-25` (BASS-II report p. 25 `11 s`).
  - `flame_spread_rate_mm_s`: `8` measurements (`2` `ML_ELIGIBLE` run-level in `PSI-99`, `6` `EVIDENCE_ONLY` across `PSI-99` and `PSI-25`).
  - `oxygen_limit_pct`: `7` subtype-separated measurements (`LOI`, `LOC`, `IGNITION_THRESHOLD`, `EXTINCTION_THRESHOLD`, `SUSTAINED_SPREAD_THRESHOLD`) in `PSI-25`.
  - `ignition_temperature_k` (`1` row: `550 K` experimental autoignition onset in `PSI-159` p. 23) & `sample_pyrolysis_temperature_k` (`1` row: `570 K` PMMA pyrolysis boundary in `PSI-26` p. 50). Numerical CRECK `885 K` prediction is excluded from experimental measurements.
  - `critical_ignition_heat_flux_kw_m2` (`1` row in `PSI-25`), `incident_heat_flux_kw_m2` (`3` rows in `PSI-102`, `PSI-25`), `hrr_watts` (`1` row in `PSI-25`).

### Pillar 2 — Fire Detection (Smoke Particle Sizing, Aerosol Concentration & Gas Signatures)
- **Core Investigations:** `PSI-47` (DAFT / DAFT-2), `PSI-101` (SAME-R), `PSI-102` (SAME), `PSI-107` (SPICE), plus gas/smoke measurements in `PSI-25`.
- **Extracted Detection Parameters:**
  - `smoke_particle_diameter_nm`: `86` measurements (`28` `ML_ELIGIBLE` run-linked TEM/Moment rows in `PSI-101` Table 2 p. 16 + `58` `EVIDENCE_ONLY` condition-level aggregate rows in `PSI-102` Table 1 p. 27, `PSI-101` Table 1 p. 78, and `PSI-47`).
  - `aerosol_aging_time_s`: `240` measurements across `PSI-101` (`SAME-R`) and `PSI-102` (`SAME`).
  - `o2_initial_calibrated_pct` (`129`), `o2_final_calibrated_pct` (`127`), `co2_initial_pct` (`127`), `co2_final_pct` (`123`), `co_initial_ppm` (`127`), `co_final_ppm` (`124`) in `PSI-25` (BASS-II).
  - `particle_number_concentration_cm3` (`6` rows in `PSI-47`, `PSI-102`), `smoke_mass_concentration_mg_m3` (`5` rows in `PSI-47`, `PSI-101`), `detection_threshold` (`3` rows in `PSI-101`, `PSI-102`), and `smoke_optical_property` (`1` row in `PSI-102`).

### Pillar 3 — Fire Suppression (Flow Extinction, Gaseous Diluent Suppression & Droplet Extinction)
- **Core Investigations:** `PSI-10` (ACME Flame Design), `PSI-22` (ACME E-FIELD), `PSI-23` (ACME s-Flame), `PSI-25` (BASS-II), `PSI-39` (CFI), `PSI-68` (FLEX-2), `PSI-69` (FLEX), `PSI-159` (ACME CFI-G).
- **Extracted Suppression Parameters:**
  - `suppressant_concentration_pct`: `726` `ML_ELIGIBLE` measurements across `PSI-69` (FLEX `CO2`, `He`, `N2` mole fraction converted to `%`, including proper mapping of `CO initial ambient composition; mole fraction` to `CO2_DILUENT_MOLE_PCT`) and `PSI-39` (CFI).
  - `extinction_droplet_diameter_mm`: `404` `ML_ELIGIBLE` visible/cool flame extinction diameters (`d_ext`) in `PSI-39` (CFI) and `PSI-69` (FLEX).
  - `extinguishing_time_s`: `367` `ML_ELIGIBLE` natural radiative/diffusive self-extinguishment durations (`extinction` runs in `PSI-69` FLEX and `SE` runs in `PSI-159` CFI-G).
  - `extinction_velocity_cm_s`: `18` `ML_ELIGIBLE` low-flow quenching and blowoff velocity measurements in `PSI-25` (BASS-II).

---

## Section 30 — Compact Parameter Coverage Matrix

| Canonical Parameter | Unit | Total | ML_ELIGIBLE | EVIDENCE_ONLY | NEEDS_REVIEW | Solid | Liquid | Gas | Unique Runs | Investigations |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `burning_duration_s` | `s` | **808** | 663 | 145 | 0 | 7 | 415 | 386 | 808 | 6 (PSI-39,PSI-69,PSI-98,PSI-99,PSI-107,PSI-159) |
| `suppressant_concentration_pct` | `%` | **726** | 726 | 0 | 0 | 0 | 726 | 0 | 501 | 2 (PSI-39,PSI-69) |
| `adiabatic_flame_temperature_k` | `K` | **587** | 0 | 587 | 0 | 0 | 0 | 587 | 587 | 2 (PSI-10,PSI-159) |
| `burning_rate_constant_mm2_s` | `mm2/s` | **533** | 533 | 0 | 0 | 0 | 533 | 0 | 406 | 2 (PSI-39,PSI-69) |
| `fuel_mass_flow_rate_g_s` | `g/s` | **471** | 471 | 0 | 0 | 0 | 0 | 471 | 471 | 3 (PSI-107,PSI-10,PSI-159) |
| `extinction_droplet_diameter_mm` | `mm` | **404** | 404 | 0 | 0 | 0 | 404 | 0 | 333 | 2 (PSI-39,PSI-69) |
| `extinguishing_time_s` | `s` | **367** | 367 | 0 | 0 | 0 | 184 | 183 | 367 | 2 (PSI-69,PSI-159) |
| `burner_temperature_k` | `K` | **285** | 285 | 0 | 0 | 0 | 0 | 285 | 285 | 1 (PSI-159) |
| `aerosol_aging_time_s` | `s` | **240** | 240 | 0 | 0 | 240 | 0 | 0 | 111 | 2 (PSI-101,PSI-102) |
| `igniter_operation_duration_s` | `s` | **235** | 0 | 235 | 0 | 11 | 224 | 0 | 235 | 3 (PSI-39,PSI-98,PSI-99) |
| `ignition_power_watts` | `W` | **235** | 0 | 235 | 0 | 11 | 224 | 0 | 235 | 3 (PSI-39,PSI-98,PSI-99) |
| `mass_burning_rate_g_s` | `g/s` | **155** | 154 | 1 | 0 | 1 | 0 | 154 | 154 | 2 (PSI-159,PSI-25) |
| `radiative_output` | `raw` | **145** | 0 | 145 | 0 | 0 | 145 | 0 | 145 | 1 (PSI-39) |
| `o2_initial_calibrated_pct` | `%` | **129** | 124 | 0 | 5 | 129 | 0 | 0 | 129 | 1 (PSI-25) |
| `co2_initial_pct` | `%` | **127** | 124 | 0 | 3 | 127 | 0 | 0 | 127 | 1 (PSI-25) |
| `co_initial_ppm` | `ppm` | **127** | 126 | 1 | 0 | 127 | 0 | 0 | 127 | 1 (PSI-25) |
| `o2_final_calibrated_pct` | `%` | **127** | 122 | 0 | 5 | 127 | 0 | 0 | 127 | 1 (PSI-25) |
| `co_final_ppm` | `ppm` | **124** | 120 | 4 | 0 | 124 | 0 | 0 | 124 | 1 (PSI-25) |
| `co2_final_pct` | `%` | **123** | 121 | 0 | 2 | 123 | 0 | 0 | 123 | 1 (PSI-25) |
| `smoke_particle_diameter_nm` | `nm` | **86** | 28 | 58 | 0 | 28 | 0 | 0 | 8 | 3 (PSI-102,PSI-101,PSI-47) |
| `pyrolysis_heating_duration_s` | `s` | **67** | 0 | 67 | 0 | 67 | 0 | 0 | 67 | 1 (PSI-101) |
| `ignition_time_s` | `s` | **39** | 0 | 39 | 0 | 39 | 0 | 0 | 38 | 2 (PSI-26,PSI-25) |
| `extinction_velocity_cm_s` | `cm/s` | **18** | 18 | 0 | 0 | 18 | 0 | 0 | 18 | 1 (PSI-25) |
| `flame_spread_rate_mm_s` | `mm/s` | **8** | 2 | 6 | 0 | 8 | 0 | 0 | 6 | 2 (PSI-99,PSI-25) |
| `oxygen_limit_pct` | `%` | **7** | 0 | 7 | 0 | 7 | 0 | 0 | 5 | 1 (PSI-25) |
| `particle_number_concentration_cm3` | `particles/cm³` | **6** | 0 | 6 | 0 | 0 | 0 | 0 | 1 | 2 (PSI-102,PSI-47) |
| `smoke_mass_concentration_mg_m3` | `mg/m³` | **5** | 0 | 5 | 0 | 0 | 0 | 0 | 1 | 2 (PSI-101,PSI-47) |
| `mass_loss_rate_g_s` | `g/s` | **4** | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 1 (PSI-102) |
| `incident_heat_flux_kw_m2` | `kW/m²` | **3** | 0 | 3 | 0 | 2 | 0 | 0 | 0 | 2 (PSI-102,PSI-25) |
| `detection_threshold` | `mg/m³` | **2** | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 1 (PSI-102) |
| `critical_ignition_heat_flux_kw_m2` | `kW/m²` | **1** | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 (PSI-25) |
| `detection_threshold` | `particles/cm³` | **1** | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 (PSI-101) |
| `hrr_watts` | `W` | **1** | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 (PSI-25) |
| `ignition_temperature_k` | `K` | **1** | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 (PSI-159) |
| `sample_pyrolysis_temperature_k` | `K` | **1** | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 (PSI-26) |
| `smoke_optical_property` | `%/ft` | **1** | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 (PSI-102) |

---

## Section 31 — Investigation Profiles (All 19 NASA PSI Investigations)

| PSI ID | Acronym | Primary Pillar | Fuel Phase | Facility | Runs | Measurements | Findings | Files | DOI |
|---|---|---|---|---|---:|---:|---:|---:|---|
| `PSI-10` | **ACME Flame Design** | Suppression | Gas | CIR | 327 | 403 | 0 | 4 | `10.60555/w4zy-bt45` |
| `PSI-20` | **ACME BRE** | Prevention | Gas | CIR | 18 | 0 | 1 | 7 | `10.60555/vb93-3y72` |
| `PSI-21` | **ACME CLD Flame** | Prevention | Gas | CIR | 32 | 0 | 0 | 2 | `10.60555/23e1-9950` |
| `PSI-22` | **ACME E-FIELD Flames** | Suppression | Gas | CIR | 32 | 0 | 1 | 6 | `10.60555/se5a-8c73` |
| `PSI-23` | **ACME s-Flame** | Suppression | Gas | CIR | 18 | 0 | 0 | 5 | `10.60555/k57n-p030` |
| `PSI-25` | **BASS-II** | Prevention | Solid | MSG | 129 | 790 | 4 | 4 | `10.60555/4qc4-de67` |
| `PSI-26` | **BASS** | Prevention | Solid | MSG | 116 | 39 | 1 | 6 | `10.60555/58h4-dy80` |
| `PSI-39` | **CFI** | Suppression | Liquid | CIR | 227 | 1509 | 1 | 5 | `10.60555/m6pj-a914` |
| `PSI-47` | **DAFT / DAFT-2** | Detection | Aerosol/Smoke | MSG | 2 | 11 | 1 | 5 | `10.60555/ztgj-d202` |
| `PSI-68` | **FLEX-2** | Suppression | Liquid | CIR | 8 | 0 | 0 | 3 | `10.60555/byp8-h018` |
| `PSI-69` | **FLEX** | Suppression | Liquid | CIR | 274 | 1346 | 1 | 4 | `10.60555/mbq8-0451` |
| `PSI-98` | **SAFFIRE-I** | Prevention | Solid | Saffire/Cygnus | 2 | 6 | 1 | 3 | `10.60555/0t15-1z43` |
| `PSI-99` | **SAFFIRE-II** | Prevention | Solid | Saffire/Cygnus | 9 | 29 | 1 | 3 | `10.60555/2chp-m469` |
| `PSI-100` | **SAFFIRE-III** | Prevention | Solid | Saffire/Cygnus | 2 | 0 | 0 | 2 | `10.60555/040q-4h36` |
| `PSI-101` | **SAME-R** | Detection | Aerosol/Smoke | MSG | 108 | 364 | 1 | 3 | `10.60555/2np7-jv14` |
| `PSI-102` | **SAME** | Detection | Aerosol/Smoke | MSG | 8 | 38 | 1 | 5 | `10.60555/gd4k-8h62` |
| `PSI-106` | **SLICE** | Prevention | Gas | MSG | 12 | 0 | 0 | 2 | `10.60555/pm12-rg61` |
| `PSI-107` | **SPICE** | Detection | Gas | MSG | 153 | 262 | 0 | 5 | `10.60555/9kbh-e962` |
| `PSI-159` | **ACME CFI-G** | Multi | Gas | CIR | 333 | 1402 | 1 | 4 | `10.60555/cyt1-kh64` |

### Detailed Investigation Intelligence Profiles

#### `PSI-10` — ACME Flame Design: Advanced Combustion via Microgravity Experiments: Flame Design
- **PIs:** Axelbaum RL, Sunderland PB, Urban DL, Stocker DP, Frolov SM | **DOI:** `10.60555/w4zy-bt45`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Maps radiative and convective extinction limits as functions of Zst and N2 dilution."}, {"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Quantifies soot-inception thresholds and adiabatic flame temperatures across O2/N2 mixtures."}]`
- **Objective Tags:** `FLAME_EXTINCTION, ATMOSPHERIC_DILUTION, COMBUSTION_STABILITY, OXYGEN_ENRICHED_ATMOSPHERE, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME Modular Chamber (Spherical porous burner)", "shared_hardware_psi_ids": ["PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"], "sensors": ["Mass Flow Controllers (MFC)", "Thin Filament Pyrometry (TFP)", "Radiometers", "Color/Intensified Cameras"]}`
- **Dataset Size:** `327` runs, `403` measurements, `0` findings, `4` files
- **Experimental Limitations:** Gaseous ethylene burner experiments; does not directly measure solid polymer pyrolysis or spread.; Inverse flames supply oxidizer from the central burner into fuel/inert mixtures.

#### `PSI-20` — ACME BRE: Advanced Combustion via Microgravity Experiments: Burning Rate Emulator
- **PIs:** Quintiere JG, de Ris J, Sunderland PB, Stocker DP | **DOI:** `10.60555/vb93-3y72`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Emulates solid/liquid material heat-feedback vaporization and flammability limits up to 40% O2."}, {"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Analyzes flame oscillation onset and radiative/diffusive extinction times in quiescent 0g."}]`
- **Objective Tags:** `MATERIAL_FLAMMABILITY, HEAT_RELEASE, FLAME_EXTINCTION, OXYGEN_ENRICHED_ATMOSPHERE, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME Chamber with 25 mm & 50 mm flat porous Burning Rate Emulator burners", "shared_hardware_psi_ids": ["PSI-10", "PSI-21", "PSI-22", "PSI-23", "PSI-159"], "sensors": ["Heat flux sensor", "Thermocouples", "TFP", "Radiometers"]}`
- **Dataset Size:** `18` runs, `0` measurements, `1` findings, `7` files
- **Experimental Limitations:** Public PSI CSV provides a 18-row daily test-day summary; run-level extinction times are reported in aggregate empirical fits.

#### `PSI-21` — ACME CLD Flame: Advanced Combustion via Microgravity Experiments: Coflow Laminar Diffusion Flame
- **PIs:** Long MB, Smooke MD, Stocker DP | **DOI:** `10.60555/23e1-9950`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Characterizes laminar coflow flame liftoff and soot radiation in microgravity."}]`
- **Objective Tags:** `COMBUSTION_STABILITY, SMOKE_GENERATION, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME Coflow Burner", "shared_hardware_psi_ids": ["PSI-22", "PSI-10", "PSI-20", "PSI-23", "PSI-159"], "sensors": ["High-resolution color camera", "MFCs", "Radiometers"]}`
- **Dataset Size:** `32` runs, `0` measurements, `0` findings, `2` files
- **Experimental Limitations:** Daily summary CSV table; gaseous fuel only.

#### `PSI-22` — ACME E-FIELD Flames: Advanced Combustion via Microgravity Experiments: Electric-Field Effects on Laminar Diffusion Flames
- **PIs:** Dunn-Rankin D, Stocker DP, Chien YC | **DOI:** `10.60555/se5a-8c73`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Demonstrates active flame blowoff and soot suppression via electric fields in 0g."}, {"pillar": "PREVENTION", "relevance_type": "SUPPORTING", "explanation": "Provides an ion-driven flow analog to buoyant convection for studying gravity scaling."}]`
- **Objective Tags:** `COMBUSTION_STABILITY, FLAME_EXTINCTION, GRAVITY_EFFECTS, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME Coflow Burner with high-voltage electrode mesh", "shared_hardware_psi_ids": ["PSI-21", "PSI-10", "PSI-20", "PSI-23", "PSI-159"], "sensors": ["High-voltage current monitor", "MFCs", "Cameras"]}`
- **Dataset Size:** `32` runs, `0` measurements, `1` findings, `6` files
- **Experimental Limitations:** Electric-field ion-wind is an analog for body-force convection and MUST NOT be treated as a direct Lunar (1/6g) or Martian (3/8g) partial-gravity measurement.

#### `PSI-23` — ACME s-Flame: Advanced Combustion via Microgravity Experiments: Structure and Response of Spherical Diffusion Flames
- **PIs:** Law CK, Tse SD, Stocker DP | **DOI:** `10.60555/k57n-p030`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Studies radiative and kinetic extinction limits and oscillatory flash reignition under N2/He dilution."}]`
- **Objective Tags:** `FLAME_EXTINCTION, ATMOSPHERIC_DILUTION, REIGNITION, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME Spherical Porous Burner", "shared_hardware_psi_ids": ["PSI-10", "PSI-159", "PSI-20", "PSI-21", "PSI-22"], "sensors": ["TFP fiber array", "Thermocouples", "Radiometers", "Intensified camera"]}`
- **Dataset Size:** `18` runs, `0` measurements, `0` findings, `5` files
- **Experimental Limitations:** Daily summary CSV table; gaseous fuels only.

#### `PSI-25` — BASS-II: Burning and Suppression of Solids - II
- **PIs:** Ferkul PV, Fernandez-Pello C, Miller FJ, T'ien JS, Bhattacharjee S, Olson SL | **DOI:** `10.60555/4qc4-de67`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "DIRECT", "explanation": "Directly measures solid spacecraft material ignition, flame spread rate, and limiting oxygen concentration (13.6%-16.2% O2)."}, {"pillar": "SUPPRESSION", "relevance_type": "DIRECT", "explanation": "Directly tests nitrogen dilution, oxygen depletion, and airflow step-down extinction (quenching vs blowoff)."}]`
- **Objective Tags:** `MATERIAL_SELECTION, MATERIAL_FLAMMABILITY, IGNITION, FLAME_SPREAD, OXYGEN_LIMITS, FLAME_EXTINCTION, GAS_EMISSIONS, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "BASS/SPICE 7.6 cm x 7.6 cm fan-driven flow tunnel inside Microgravity Science Glovebox", "shared_hardware_psi_ids": ["PSI-26", "PSI-107", "PSI-106"], "sensors": ["CSA-CP (O2, CO),", "Crowcon CO2 analyzer", "Thermocouples", "Radiometer", "Nikon D300s & video camera"]}`
- **Dataset Size:** `129` runs, `790` measurements, `4` findings, `4` files
- **Experimental Limitations:** Conducted near 1 atm (14.7 psi) in MSG; no reduced total cabin pressure (e.g. 8.2 psi) runs.; CSA-CP CO sensor saturates at 1000 ppm ('OR' / '+OR').; Final O2/CO2/CO readings require post-burn equilibration wait time and occasionally reflect sensor turn-off.

#### `PSI-26` — BASS: Burning and Suppression of Solids
- **PIs:** Ferkul PV, Takahashi F, T'ien JS, Olson SL | **DOI:** `10.60555/58h4-dy80`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "DIRECT", "explanation": "Directly investigates solid fuel ignition and flame spread across airflow velocities in 0g."}, {"pillar": "SUPPRESSION", "relevance_type": "DIRECT", "explanation": "Investigates airflow cut-off quenching and nitrogen-flow extinguishment of solid fuels."}]`
- **Objective Tags:** `MATERIAL_FLAMMABILITY, IGNITION, FLAME_SPREAD, FLAME_EXTINCTION, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "BASS/SPICE flow duct inside MSG", "shared_hardware_psi_ids": ["PSI-25", "PSI-107", "PSI-106"], "sensors": ["Anemometer", "Video and still cameras", "GN2 flow potentiometer"]}`
- **Dataset Size:** `116` runs, `39` measurements, `1` findings, `6` files
- **Experimental Limitations:** Master CSV lists test IDs and materials; planned ignition intervals (5-10 s, 10-20 s) come from BASS Test Matrix.xlsx.

#### `PSI-39` — CFI: Cool Flames Investigation
- **PIs:** Williams FA, Dryer FL, Farouk TI, Nayagam V, Dietrich DL | **DOI:** `10.60555/m6pj-a914`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Quantifies radiative hot-flame extinction, cool-flame persistence, and post-extinction reignition hazards in N2/He atmospheres."}, {"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Measures hot and cool burning rate constants across pressures (0.5-3 atm) and O2 concentrations."}]`
- **Objective Tags:** `FLAME_EXTINCTION, REIGNITION, ATMOSPHERIC_DILUTION, HEAT_RELEASE, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "Multi-user Droplet Combustion Apparatus (MDCA) inside CIR", "shared_hardware_psi_ids": ["PSI-69", "PSI-68"], "sensors": ["Hot-wire igniter", "Narrow-band & wide-band radiometers", "HIBMS/LLL cameras"]}`
- **Dataset Size:** `227` runs, `1509` measurements, `1` findings, `5` files
- **Experimental Limitations:** Liquid alkane droplets (C12H26, C10H22, C7H16); extinction/reignition thresholds cannot be directly applied to solid cabin polymers.; Ignition Time (ms) on the Igniter sheet represents hot-wire energization duration, not ignition delay.

#### `PSI-47` — DAFT / DAFT-2: Dust and Aerosol Measurement Feasibility Test / DAFT-2
- **PIs:** Urban DL, Fortenberry C | **DOI:** `10.60555/ztgj-d202`
- **Pillar Classifications:** `[{"pillar": "DETECTION", "relevance_type": "SUPPORTING", "explanation": "Validates P-Trak and DustTrak aerosol instruments shared with SAME/SAME-R and measures ISS background particle levels."}]`
- **Objective Tags:** `SENSOR_DEVELOPMENT, SMOKE_DETECTION, AEROSOL_TRANSPORT, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "TSI P-Trak CPC (alcohol wick) & TSI DustTrak laser photometer", "shared_hardware_psi_ids": ["PSI-102", "PSI-101"], "sensors": ["TSI P-Trak Condensation Particle Counter", "TSI DustTrak Laser Photometer"]}`
- **Dataset Size:** `2` runs, `11` measurements, `1` findings, `5` files
- **Experimental Limitations:** Uses Arizona Road Dust (ARD) mechanical test aerosol rather than combustion smoke; ARD particle sizes (1.56-1.70 µm) must not be merged with pyrolysis smoke.

#### `PSI-68` — FLEX-2: Flame Extinguishment Experiment - 2
- **PIs:** Williams FA, Dryer FL, Shaw BD, Choi MY, Nayagam V, Avedisian CT, Dietrich DL, Hicks MC | **DOI:** `10.60555/byp8-h018`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Evaluates droplet extinction across O2/N2 and O2/He mixtures and low convective velocities."}, {"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Characterizes liquid fuel mixture burning rates and soot shells."}]`
- **Objective Tags:** `FLAME_EXTINCTION, ATMOSPHERIC_DILUTION, REDUCED_PRESSURE, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "MDCA inside CIR", "shared_hardware_psi_ids": ["PSI-69", "PSI-39"], "sensors": ["Backlit droplet camera", "Radiometers", "Hot-wire igniters"]}`
- **Dataset Size:** `8` runs, `0` measurements, `0` findings, `3` files
- **Experimental Limitations:** Public PSI CSV provides an 8-row parameter matrix summary across fuel types rather than individual droplet run logs.

#### `PSI-69` — FLEX: Flame Extinguishment Experiment
- **PIs:** Williams FA, Shaw BD, Hicks MC, Nayagam V, Choi MY, Dryer FL, Dietrich DL | **DOI:** `10.60555/mbq8-0451`
- **Pillar Classifications:** `[{"pillar": "SUPPRESSION", "relevance_type": "DIRECT", "explanation": "Directly tests CO2, He, and N2 suppressant dilution, reduced pressure, and radiative/diffusive flame extinction."}, {"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Quantifies burning rate constants and cool-flame vapor reignition risks."}]`
- **Objective Tags:** `FIRE_SUPPRESSION, FLAME_EXTINCTION, ATMOSPHERIC_DILUTION, OXYGEN_LIMITS, REDUCED_PRESSURE, REIGNITION, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "MDCA inside CIR", "shared_hardware_psi_ids": ["PSI-68", "PSI-39"], "sensors": ["High-speed backlit camera", "UV/IR radiometers", "Gas mixing manifold"]}`
- **Dataset Size:** `274` runs, `1346` measurements, `1` findings, `4` files
- **Experimental Limitations:** Liquid droplets (Methanol, Heptane); extinction concentrations cannot be assumed identical for solid polymer cabin fires.; In PSI-69_Experimental table_FLEX.csv, the column 'CO initial ambient composition; mole fraction' represents CO2 diluent mole fraction (subscript '2' omitted in ASCII export).

#### `PSI-98` — SAFFIRE-I: Spacecraft Fire Safety Experiment - I
- **PIs:** Urban DL, Ruff GA, Ferkul PV, Olson SL, Meyer ME | **DOI:** `10.60555/0t15-1z43`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "DIRECT", "explanation": "Large-scale spacecraft solid material flame propagation under realistic cabin ventilation."}]`
- **Objective Tags:** `MATERIAL_FLAMMABILITY, FLAME_SPREAD, IGNITION, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "Saffire/Cygnus", "apparatus": "SAFFIRE flow duct module aboard Cygnus OA-6 resupply vehicle", "shared_hardware_psi_ids": ["PSI-99", "PSI-100"], "sensors": ["Dual video cameras (S1C1/S1C2)", "Thermocouple arrays", "Radiometers", "O2/CO2/pressure sensors"]}`
- **Dataset Size:** `2` runs, `6` measurements, `1` findings, `3` files
- **Experimental Limitations:** CSV does not report final burned length for S1/S2; total sample length must not be divided by burn time without accounting for partial/anchored burning.

#### `PSI-99` — SAFFIRE-II: Spacecraft Fire Experiment - II
- **PIs:** Urban DL, Ruff GA | **DOI:** `10.60555/2chp-m469`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "DIRECT", "explanation": "Directly compares 0g and 1g flammability, burn length, and flame spread rates across 9 spacecraft materials."}]`
- **Objective Tags:** `MATERIAL_SELECTION, MATERIAL_FLAMMABILITY, FLAME_SPREAD, IGNITION, GRAVITY_EFFECTS, MICROGRAVITY_COMBUSTION, NORMAL_GRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "Saffire/Cygnus", "apparatus": "SAFFIRE multi-sample flow duct aboard Cygnus OA-5", "shared_hardware_psi_ids": ["PSI-98", "PSI-100"], "sensors": ["Top/side cameras", "Hot-wire igniters (80 W / 97 W)", "CO2/O2 sensors"]}`
- **Dataset Size:** `9` runs, `29` measurements, `1` findings, `3` files
- **Experimental Limitations:** In PSI-99 CSV, the header 'µ-g Spread Length' contains direct 0g spread rates ('2.1 mm/s', '2.6 mm/s') for samples 2-5 and 2-6.; Percent O2 in SAFFIRE-II CSV was derived from measured CO2 production referenced to ISS initial O2 (Note 1).

#### `PSI-100` — SAFFIRE-III: Spacecraft Fire Experiment - III
- **PIs:** Urban DL, Ruff GA | **DOI:** `10.60555/040q-4h36`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "DIRECT", "explanation": "Large-scale SIBAL fabric flammability at 30 cm/s ventilation flow."}]`
- **Objective Tags:** `MATERIAL_FLAMMABILITY, FLAME_SPREAD, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "Saffire/Cygnus", "apparatus": "SAFFIRE module aboard Cygnus OA-7", "shared_hardware_psi_ids": ["PSI-98", "PSI-99"], "sensors": ["Dual cameras (S1C1/S1C2)", "Thermocouples", "Radiometers"]}`
- **Dataset Size:** `2` runs, `0` measurements, `0` findings, `2` files
- **Experimental Limitations:** Public PSI CSV lists sample dimensions, airflow (30 cm/s), and flow direction, but omits numerical burn time and O2% columns.

#### `PSI-101` — SAME-R: Smoke Aerosol Measurement Experiment - Reflight
- **PIs:** Urban DL, Yuan ZG, Yang JC, Cleary TG, Mulholland GW, Fortenberry C | **DOI:** `10.60555/2np7-jv14`
- **Pillar Classifications:** `[{"pillar": "DETECTION", "relevance_type": "DIRECT", "explanation": "Directly measures spacecraft pyrolysis smoke particle diameters, aging coagulation, and ISS/STS detector responses across 109 runs."}]`
- **Objective Tags:** `SMOKE_GENERATION, AEROSOL_TRANSPORT, SMOKE_DETECTION, SENSOR_DEVELOPMENT, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "SAME aerosol generation duct, aging chamber, and SMPS drum in MSG", "shared_hardware_psi_ids": ["PSI-102", "PSI-47"], "sensors": ["STS Ionization Detector", "ISS Honeywell Laser Forward-Scattering Detector", "TSI P-Trak CPC", "TSI DustTrak Photometer", "Scanning Mobility Particle Sizer (SMPS)", "Thermal Precipitator (TEM grids)"]}`
- **Dataset Size:** `108` runs, `364` measurements, `1` findings, `3` files
- **Experimental Limitations:** Duration (sec) = 60 s in SAME-R.csv is programmed non-flaming pyrolysis wire heating duration, NOT flame burning duration.; Table 1 (p.78) reports baseline material-level aggregate diameters rather than run-by-run values for all 109 CSV rows.

#### `PSI-102` — SAME: Smoke and Aerosol Measurement Experiment
- **PIs:** Urban DL, Mulholland GW, Cleary TG, Yang JC, Fortenberry C | **DOI:** `10.60555/gd4k-8h62`
- **Pillar Classifications:** `[{"pillar": "DETECTION", "relevance_type": "DIRECT", "explanation": "Directly measures 0g smoke particle size distributions, polymer weight loss rates, and ISS/STS detector thresholds."}]`
- **Objective Tags:** `SMOKE_GENERATION, AEROSOL_TRANSPORT, SMOKE_DETECTION, SENSOR_DEVELOPMENT, GRAVITY_EFFECTS, MICROGRAVITY_COMBUSTION, NORMAL_GRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "SAME smoke duct & aging chamber inside MSG", "shared_hardware_psi_ids": ["PSI-101", "PSI-47"], "sensors": ["STS Ionization Detector", "ISS Laser Scattering Detector", "P-Trak CPC", "DustTrak Photometer", "TEM Precipitator"]}`
- **Dataset Size:** `8` runs, `38` measurements, `1` findings, `5` files
- **Experimental Limitations:** TEM grids on SAME-1 experienced pre-flight assembly particle contamination (resolved in SAME-R).; Detector alarm response times in the report (pp. 65-66) are LES numerical predictions rather than live cabin fire tests.

#### `PSI-106` — SLICE: Structure and Liftoff In Combustion Experiment
- **PIs:** Long MB, Smooke MD, Takahashi F, Stocker DP | **DOI:** `10.60555/pm12-rg61`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Studies laminar coflow flame liftoff and stabilization in the MSG flow duct."}]`
- **Objective Tags:** `COMBUSTION_STABILITY, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "SPICE/SLICE coflow duct inside MSG", "shared_hardware_psi_ids": ["PSI-107", "PSI-25", "PSI-26"], "sensors": ["Digital color camera", "Thin filament pyrometry", "Airflow fan"]}`
- **Dataset Size:** `12` runs, `0` measurements, `0` findings, `2` files
- **Experimental Limitations:** Public PSI CSV lists 12 test session dates and fuel types without run-by-run numerical columns.

#### `PSI-107` — SPICE: Smoke Point In Co-flow Experiment
- **PIs:** Urban DL, Sunderland PB, Yuan ZG | **DOI:** `10.60555/9kbh-e962`
- **Pillar Classifications:** `[{"pillar": "DETECTION", "relevance_type": "INDIRECT", "explanation": "Quantifies soot-emission onset (smoke point) conditions that govern soot aerosol production in 0g flames."}, {"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Characterizes radiative heat loss transition at the soot point in ventilated coflow."}]`
- **Objective Tags:** `SMOKE_GENERATION, COMBUSTION_STABILITY, MICROGRAVITY_COMBUSTION`
- **Hardware Lineage:** `{"facility": "MSG", "apparatus": "SPICE fan-driven flow duct in MSG (later reused for SLICE, BASS, and BASS-II)", "shared_hardware_psi_ids": ["PSI-106", "PSI-25", "PSI-26"], "sensors": ["Mass flow controller", "Anemometer", "Digital still & video cameras"]}`
- **Dataset Size:** `153` runs, `262` measurements, `0` findings, `5` files
- **Experimental Limitations:** PSI-107 CSV contains 469 camera-frame rows spanning 153 unique burns (GMT date + GMT ignition + GMT Flame Off); burning duration must be deduplicated per unique burn.; Fuel Rate (mg/s) is controlled gaseous burner supply rate, not solid material mass loss rate.

#### `PSI-159` — ACME CFI-G: Advanced Combustion via Microgravity Experiments: Cool Flames Investigation with Gases
- **PIs:** Sunderland PB, Axelbaum RL, Williams FA, Stocker DP | **DOI:** `10.60555/cyt1-kh64`
- **Pillar Classifications:** `[{"pillar": "PREVENTION", "relevance_type": "INDIRECT", "explanation": "Maps hot ignition, flash ignition, and cool-flame autoignition (550 K) across pressures and elevated O2."}, {"pillar": "SUPPRESSION", "relevance_type": "INDIRECT", "explanation": "Characterizes self-extinguishment (SE), transition to invisible cool flames, and catalytic hot-flame reignition."}]`
- **Objective Tags:** `IGNITION, FLAME_EXTINCTION, REIGNITION, OXYGEN_ENRICHED_ATMOSPHERE, REDUCED_PRESSURE, MICROGRAVITY_COMBUSTION, EARTH_APPLICATIONS`
- **Hardware Lineage:** `{"facility": "CIR", "apparatus": "ACME 6.35 mm spherical porous burner in CIR", "shared_hardware_psi_ids": ["PSI-10", "PSI-23", "PSI-20", "PSI-21", "PSI-22"], "sensors": ["Intensified UV/visible camera", "Radiometers", "Short/far and long/near Type-B thermocouple rakes"]}`
- **Dataset Size:** `333` runs, `1402` measurements, `1` findings, `4` files
- **Experimental Limitations:** In Inverse Flames, XO2 is the oxidizer stream concentration flowing from the spherical burner into ambient fuel/N2, NOT cabin ambient O2.; 89 runs terminated by operator Flow Termination ('FT') are right-censored and must not be treated as natural self-extinguishment ('SE').; Platinum in the exposed Type-B thermocouple on the long rake caused unwanted catalytic hot-flame reignition on GMT 291.

---

## Section 32 — ML Readiness Assessment

| Parameter | Status | ML_ELIGIBLE Rows | Rationale & Modeling Guidance |
|---|---|---:|---|
| `suppressant_concentration_pct` | `READY_FOR_MODEL_EXPERIMENTATION` | **726** | Multi-diluent (`CO2`, `He`, `N2`, `Xe`) suppression dataset across `PSI-69` (FLEX) and `PSI-39` (CFI). Keep `subtype` (`CO2_DILUENT_MOLE_PCT`, etc.) as categorical feature. |
| `burning_duration_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **663** | `808` total (`663` `ML_ELIGIBLE`, `145` `EVIDENCE_ONLY` right-censored `FT` rows) across `PSI-39`, `PSI-69`, `PSI-98`, `PSI-99`, `PSI-107`, `PSI-159`. Stratify by `fuel_phase` and `oxygen_location`. |
| `burning_rate_constant_mm2_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **533** | Clean droplet burning rate constant $K$ in `PSI-39` (CFI) and `PSI-69` (FLEX). |
| `fuel_mass_flow_rate_g_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **471** | High-density burner mass flow rate dataset across `PSI-10`, `PSI-107`, `PSI-159`. |
| `extinction_droplet_diameter_mm` | `READY_FOR_MODEL_EXPERIMENTATION` | **404** | Clean droplet extinction diameter (`d_ext`) dataset in `PSI-39` (CFI) and `PSI-69` (FLEX). |
| `extinguishing_time_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **367** | Strong natural self-extinguishment dataset across `PSI-69` (FLEX `extinction` runs) and `PSI-159` (CFI-G `SE` runs). |
| `burner_temperature_k` | `READY_FOR_MODEL_EXPERIMENTATION` | **285** | Peak spherical burner temperatures in `PSI-159` (`CFI-G`). |
| `aerosol_aging_time_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **240** | Controlled smoke aging delay times in `PSI-101` (`SAME-R`) and `PSI-102` (`SAME`). |
| `mass_burning_rate_g_s` | `READY_FOR_MODEL_EXPERIMENTATION` | **154** | `155` total (`154` `ML_ELIGIBLE` hydrocarbon burning rate in `PSI-159` + `1` PMMA report value in `PSI-25`). |
| `o2_initial_calibrated_pct` / `co2` / `co` | `READY_FOR_MODEL_EXPERIMENTATION` | **120–126** | Calibrated gas telemetry in `PSI-25` (BASS-II); over-range rows (`>5000 ppm`) flagged. |
| `smoke_particle_diameter_nm` | `LIMITED_DATA` | **28** | `86` total (`28` `ML_ELIGIBLE` run-linked TEM/Moment rows in `PSI-101` Table 2 + `58` `EVIDENCE_ONLY` aggregate condition rows in `PSI-101` Table 1 & `PSI-102` Table 1). Stratify by `subtype` (`GMD_NM`, `AMD_NM`, `MMD_NM`, `TEM_PRIMARY_SPHERE_NM`). |
| `extinction_velocity_cm_s` | `LIMITED_DATA` | **18** | `18` `ML_ELIGIBLE` low-flow quenching and blowoff velocity rows in `PSI-25` (BASS-II); suitable for threshold modeling when stratified by `subtype`. |
| `flame_spread_rate_mm_s` | `LIMITED_DATA` | **2** | `8` total (`2` `ML_ELIGIBLE` run-level `0g` SIBAL rows in `PSI-99` + `6` `EVIDENCE_ONLY` rows in `PSI-99` and `PSI-25`). |
| `mass_loss_rate_g_s` | `LIMITED_DATA` | **4** | `4` `ML_ELIGIBLE` pyrolysis mass loss rate rows in `PSI-102` (`SAME`). |
| `ignition_time_s` | `EVIDENCE_RETRIEVAL_ONLY` | **0** | `39` `EVIDENCE_ONLY` rows (`38` igniter-to-ignition timing rows in `PSI-26` BASS + `1` report value `11 s` in `PSI-25`). |
| `oxygen_limit_pct` | `EVIDENCE_RETRIEVAL_ONLY` | **0** | `7` `EVIDENCE_ONLY` threshold rows across `LOI`, `LOC`, `IGNITION_THRESHOLD`, `EXTINCTION_THRESHOLD`, `SUSTAINED_SPREAD_THRESHOLD`. Use as deterministic physical boundaries in Ranking Engine and SI RAG. |
| `ignition_temperature_k` | `EVIDENCE_RETRIEVAL_ONLY` | **0** | `1` `EVIDENCE_ONLY` row (`550 K` experimental autoignition onset in `PSI-159`) + `1` `sample_pyrolysis_temperature_k` (`570 K` in `PSI-26`). |
| `critical_ignition_heat_flux_kw_m2` | `EVIDENCE_RETRIEVAL_ONLY` | **0** | `1` `EVIDENCE_ONLY` report row in `PSI-25` + `3` `incident_heat_flux_kw_m2` rows (`PSI-102`, `PSI-25`). |

---

## Section 33 — Research Gap Matrix

| Gap ID | Safety Pillar | Gap Category | Target Parameter / Condition | Status in PSI Archive | Scientific Explanation & Future Mission Recommendation |
|---|---|---|---|---|---|
| **GAP-01** | All Pillars | `PARTIAL_GRAVITY_GAP` | Lunar (`1/6g`) & Martian (`3/8g`) experimental runs | `UNAVAILABLE_IN_PSI` (`0` runs) | All 19 PSI folders contain only `0g` (ISS/Cygnus/STS) and `1g` ground comparison runs. Upward buoyant plume acceleration at `1/6g` and `3/8g` creates a worst-case minimum LOC below both `0g` and `1g` (`PSI-25` p. 21). **Future NASA campaigns:** `LUCI` (Lunar Combustion Investigation) and `FM2` (Flammability Metrics in Partial Gravity). |
| **GAP-02** | Fire Prevention | `MISSING_PARAMETER_GAP` | `critical_ignition_heat_flux_kw_m2` & piloted `ignition_temperature_k` | `LIMITED_DATA` (`1` row each) | Microgravity solid combustion experiments (`BASS`, `BASS-II`, `SAFFIRE`) used resistively heated Kanthal wires rather than calibrated radiant heat flux cones (`ASTM E1354`) due to ISS power/volume constraints. |
| **GAP-03** | Fire Prevention | `MISSING_PARAMETER_GAP` | Flaming solid `mass_loss_rate_g_s` | `LIMITED_DATA` (`4` non-flaming pyrolysis rows in `PSI-102`) | Continuous mass-loss load cells cannot operate directly on free-floating flaming microgravity solid samples; only non-flaming pyrolysis clip mass differences (`PSI-102`) or gas burner MFC flow rates (`fuel_mass_flow_rate_g_s`: `471` rows) exist. |
| **GAP-04** | Fire Detection | `SENSOR_INTERACTION_GAP` | Multi-material flaming vs smoldering false-alarm cross-sensitivity in partial gravity | `LIMITED_DATA` (`PSI-47`, `PSI-101`, `PSI-102`) | `SAME`/`SAME-R` characterized non-flaming pyrolysis smoke (`60 s` heating) for 5 spacecraft materials, and `DAFT` characterized lunar dust simulants, but combined flaming soot + lunar regolith dust false-alarm thresholds in `36% O2 / 8.2 psi` Exploration Atmosphere remain unmeasured. |
| **GAP-05** | Fire Suppression | `MATERIAL_COVERAGE_GAP` | Active Fine Water Mist (`FWM`) & Momentum-Driven Jet Suppression on thick solids in `0g`/`1/6g` | `LIMITED_DATA` | `PSI-69` (`FLEX`) and `PSI-39` (`CFI`) measured quiescent gas diluent (`CO2`, `He`, `N2`, `Xe`) extinction on droplets, while `PSI-25`/`26` measured ventilation flow cut-off on solids. No PSI dataset in the current 19 folders tests active directed water-mist or momentum-jet discharge on burning solid polymers. |
