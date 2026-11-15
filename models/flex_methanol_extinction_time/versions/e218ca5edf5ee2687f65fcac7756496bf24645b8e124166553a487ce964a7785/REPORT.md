# Research model training report

Task: `flex_methanol_extinction_time`
Version: `e218ca5edf5ee2687f65fcac7756496bf24645b8e124166553a487ce964a7785`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 69 | 26 |
| calibration | 15 | 6 |
| benchmark | 19 | 8 |

## Development grouped cross-validation

| Model | MAE (s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 5.88209 | 7.90183 | -0.00460755 | 6.34874 | 1 |
| linear_interpolation | 2.30343 | 2.93207 | 0.696901 | 1.9364 | 0.26087 |
| linear_regression | 4.52271 | 5.78244 | 0.462023 | 4.89558 | 1 |
| ridge | 4.48148 | 5.73109 | 0.471536 | 4.85224 | 1 |
| random_forest | 4.45999 | 5.69236 | 0.478655 | 4.53346 | 1 |
| gaussian_process | 2.93272 | 3.91383 | 0.753542 | 3.01726 | 1 |
| catboost | 4.12145 | 5.50584 | 0.51226 | 4.25816 | 1 |

## Independent benchmark

Selected model: **gaussian_process**
MAE: 2.37095 s.
RMSE: 3.18748; R2: 0.738486.
Mean-baseline MAE: 5.11718.

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
