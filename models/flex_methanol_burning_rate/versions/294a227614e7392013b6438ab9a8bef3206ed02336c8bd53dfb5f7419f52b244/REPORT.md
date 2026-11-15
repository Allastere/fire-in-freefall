# Research model training report

Task: `flex_methanol_burning_rate`
Version: `294a227614e7392013b6438ab9a8bef3206ed02336c8bd53dfb5f7419f52b244`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 91 | 31 |
| calibration | 22 | 7 |
| benchmark | 35 | 10 |

## Development grouped cross-validation

| Model | MAE (mm2/s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 0.0859882 | 0.107257 | -0.0336199 | 0.0921835 | 1 |
| linear_interpolation | 0.0346955 | 0.0438636 | 0.102918 | 0.0371538 | 0.21978 |
| linear_regression | 0.0287419 | 0.0425883 | 0.837036 | 0.0303998 | 1 |
| ridge | 0.0293758 | 0.0428226 | 0.835237 | 0.03098 | 1 |
| random_forest | 0.0550879 | 0.0767804 | 0.470321 | 0.0614068 | 1 |
| gaussian_process | 0.0304638 | 0.044802 | 0.819654 | 0.0334705 | 1 |
| catboost | 0.049141 | 0.067065 | 0.595885 | 0.0549369 | 1 |

## Independent benchmark

Selected model: **linear_regression**
MAE: 0.0342153 mm2/s.
RMSE: 0.0443825; R2: 0.900639.
Mean-baseline MAE: 0.125356.

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
