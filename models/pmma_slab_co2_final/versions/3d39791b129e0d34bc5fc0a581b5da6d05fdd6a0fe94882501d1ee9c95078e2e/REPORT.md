# Research model training report

Task: `pmma_slab_co2_final`
Version: `3d39791b129e0d34bc5fc0a581b5da6d05fdd6a0fe94882501d1ee9c95078e2e`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 9 | 4 |
| calibration | 4 | 1 |
| benchmark | 6 | 2 |

## Development grouped cross-validation

| Model | MAE (%) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 0.360813 | 0.435184 | -0.121639 | 0.361509 | 1 |
| linear_interpolation | unavailable | unavailable | unavailable | unavailable | 0 |
| linear_regression | 1.12993 | 1.99055 | -22.4666 | 0.770782 | 1 |
| ridge | 0.854299 | 1.30849 | -9.1402 | 0.687678 | 1 |
| random_forest | 0.388233 | 0.450898 | -0.204104 | 0.387309 | 1 |
| gaussian_process | 0.392639 | 0.458808 | -0.246722 | 0.396257 | 1 |
| catboost | 0.406758 | 0.441695 | -0.155451 | 0.405897 | 1 |

## Independent benchmark

Selected model: **random_forest**
MAE: 0.372171 %.
RMSE: 0.441916; R2: -1.83611.
Mean-baseline MAE: 0.420556.

## Promotion blockers

- Scientific protocol review is incomplete.
- No approved physical tolerance configured: max_mae.
- No approved physical tolerance configured: max_rmse.
- No approved physical tolerance configured: max_interval_width.
- Too few independent calibration groups for a finite requested coverage interval.
- Supported-domain gate failed on the independent benchmark.
- Learned model did not beat the mean baseline in grouped development CV.

## Scientific limitations

- Research candidate only: measurement duration, complete airflow history and independent campaign validation are unavailable.
- 14.7 psi is an importer assumption, not a measured pressure feature.
- Only the source-backed PMMA slab/opposed-flow series is used; no partial-gravity or high-oxygen predictions are supported.
- Material reuse and burn-side descriptions require scientific review before deployment.
- No production quality tolerances have been approved. Training does not imply promotion.

A numeric experimental benchmark prediction is not an approved assessment or safety rating.
No supported partial-gravity or high-oxygen model is established by this training run.
