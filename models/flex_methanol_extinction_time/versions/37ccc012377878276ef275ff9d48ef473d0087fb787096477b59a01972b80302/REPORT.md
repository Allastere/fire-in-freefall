# Research model training report

Task: `flex_methanol_extinction_time`
Version: `37ccc012377878276ef275ff9d48ef473d0087fb787096477b59a01972b80302`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 68 | 25 |
| calibration | 15 | 6 |
| benchmark | 19 | 8 |

## Development grouped cross-validation

| Model | MAE (s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 5.84037 | 7.91562 | -0.00393562 | 6.29843 | 1 |
| linear_interpolation | 1.89265 | 2.40932 | 0.713965 | 1.50882 | 0.176471 |
| linear_regression | 4.40125 | 5.68202 | 0.482701 | 4.74207 | 1 |
| ridge | 4.36703 | 5.63681 | 0.4909 | 4.70987 | 1 |
| random_forest | 4.42396 | 5.65317 | 0.48794 | 4.66215 | 1 |
| gaussian_process | 2.89605 | 3.88378 | 0.758317 | 2.90644 | 1 |
| catboost | 4.13537 | 5.60267 | 0.497049 | 4.43695 | 1 |

## Independent benchmark

Selected model: **gaussian_process**
MAE: 2.35266 s.
RMSE: 3.19033; R2: 0.738018.
Mean-baseline MAE: 5.12231.

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
