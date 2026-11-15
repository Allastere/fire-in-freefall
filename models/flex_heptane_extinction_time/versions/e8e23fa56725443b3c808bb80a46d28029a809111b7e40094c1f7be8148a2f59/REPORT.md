# Research model training report

Task: `flex_heptane_extinction_time`
Version: `e8e23fa56725443b3c808bb80a46d28029a809111b7e40094c1f7be8148a2f59`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 34 | 18 |
| calibration | 6 | 4 |
| benchmark | 12 | 6 |

## Development grouped cross-validation

| Model | MAE (s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 2.58485 | 2.98795 | -0.147181 | 2.80964 | 1 |
| linear_interpolation | 1.09292 | 1.09444 | 0.815795 | 1.09292 | 0.0588235 |
| linear_regression | 1.96986 | 2.42623 | 0.243605 | 1.84927 | 1 |
| ridge | 1.7076 | 2.1212 | 0.42184 | 1.61848 | 1 |
| random_forest | 1.77929 | 2.29176 | 0.325125 | 1.60982 | 1 |
| gaussian_process | 1.78543 | 2.48647 | 0.205576 | 1.81395 | 1 |
| catboost | 1.53063 | 1.96273 | 0.504999 | 1.45137 | 1 |

## Independent benchmark

Selected model: **catboost**
MAE: 1.9483 s.
RMSE: 2.10617; R2: 0.462237.
Mean-baseline MAE: 2.7826.

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
