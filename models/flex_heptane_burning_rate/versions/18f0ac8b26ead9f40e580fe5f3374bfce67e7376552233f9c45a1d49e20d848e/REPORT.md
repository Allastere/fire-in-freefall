# Research model training report

Task: `flex_heptane_burning_rate`
Version: `18f0ac8b26ead9f40e580fe5f3374bfce67e7376552233f9c45a1d49e20d848e`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 74 | 26 |
| calibration | 17 | 6 |
| benchmark | 14 | 8 |

## Development grouped cross-validation

| Model | MAE (mm2/s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 0.117588 | 0.159855 | -0.219939 | 0.110071 | 1 |
| linear_interpolation | 0.0437073 | 0.0544018 | 0.538489 | 0.0393393 | 0.27027 |
| linear_regression | 0.0735912 | 0.108078 | 0.442353 | 0.0733485 | 1 |
| ridge | 0.0828815 | 0.118593 | 0.328562 | 0.0853838 | 1 |
| random_forest | 0.090092 | 0.125593 | 0.246962 | 0.0843981 | 1 |
| gaussian_process | 0.0805419 | 0.112938 | 0.391073 | 0.075478 | 1 |
| catboost | 0.095125 | 0.127794 | 0.220341 | 0.0923051 | 1 |

## Independent benchmark

Selected model: **linear_regression**
MAE: 0.0459001 mm2/s.
RMSE: 0.0541432; R2: 0.841994.
Mean-baseline MAE: 0.119981.

## Promotion blockers

- Scientific protocol review is incomplete.
- No approved physical tolerance configured: max_mae.
- No approved physical tolerance configured: max_rmse.
- No approved physical tolerance configured: max_interval_width.
- Too few independent calibration groups for a finite requested coverage interval.
- Supported-domain gate failed on the independent benchmark.

## Scientific limitations

- FLEX liquid droplets only; not applicable to solid fires or operational suppression.
- Grouped by test date and specimen identifiers; no independent investigation replication.
- Only initial atmospheric composition, droplet diameter and pressure are predictors.
- Scientific deployment tolerances require review; import eligibility does not authorize deployment.

A numeric experimental benchmark prediction is not an approved assessment or safety rating.
No supported partial-gravity or high-oxygen model is established by this training run.
