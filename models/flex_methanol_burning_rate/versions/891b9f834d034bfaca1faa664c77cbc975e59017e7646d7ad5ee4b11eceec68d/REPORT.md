# Research model training report

Task: `flex_methanol_burning_rate`
Version: `891b9f834d034bfaca1faa664c77cbc975e59017e7646d7ad5ee4b11eceec68d`
Status: **RESEARCH_ONLY**

The model was selected using development-group CV, never benchmark scores.
Full retraining excludes frozen calibration and benchmark groups.

| Role | Samples | Independent groups |
| --- | ---: | ---: |
| development | 92 | 32 |
| calibration | 22 | 7 |
| benchmark | 35 | 10 |

## Development grouped cross-validation

| Model | MAE (mm2/s) | RMSE | R2 | Group MAE | Prediction coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean_baseline | 0.0858349 | 0.106932 | -0.0365349 | 0.0915651 | 1 |
| linear_interpolation | 0.0339985 | 0.0423134 | 0.30662 | 0.033967 | 0.293478 |
| linear_regression | 0.0282926 | 0.0422208 | 0.838407 | 0.0299773 | 1 |
| ridge | 0.0288137 | 0.0424257 | 0.836835 | 0.0305495 | 1 |
| random_forest | 0.0515518 | 0.0716874 | 0.534141 | 0.0570427 | 1 |
| gaussian_process | 0.0294656 | 0.0440635 | 0.823995 | 0.0321804 | 1 |
| catboost | 0.0487549 | 0.0675883 | 0.585894 | 0.0556505 | 1 |

## Independent benchmark

Selected model: **linear_regression**
MAE: 0.0339362 mm2/s.
RMSE: 0.0439769; R2: 0.902447.
Mean-baseline MAE: 0.125314.

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
