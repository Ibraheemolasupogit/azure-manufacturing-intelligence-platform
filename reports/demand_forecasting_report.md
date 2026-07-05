# Demand Forecasting Report

- Forecast run ID: `FORECAST-6357daf22de3ea43`
- Selected model: `random_forest`
- Selection reason: Lowest validation wape with deterministic tie-breaks on MAE, absolute bias, model simplicity, and model name.
- Forecast horizon rows: `56`
- Held-out test WAPE: `0.2584642904249187`
- Limitation: Tracked governed sample has 14 days; use the extended forecasting profile for credible rolling-origin evidence.

## Split Dates

- train_start: `2026-01-01`
- train_end: `2026-01-08`
- validation_start: `2026-01-09`
- validation_end: `2026-01-11`
- test_start: `2026-01-12`
- test_end: `2026-01-14`
- forecast_start: `2026-01-15`
- forecast_end: `2026-01-21`

## Validation Metrics

| Model | WAPE | MAE | Bias |
| --- | ---: | ---: | ---: |
| linear_regression | 1.14444335877609 | 191.78963287489307 | 191.0656537170115 |
| moving_average | 1.0786389145414508 | 180.7619047619048 | 13.095238095238088 |
| random_forest | 0.26306512907364477 | 44.08533121392497 | 6.493943602693615 |
| seasonal_naive | 2.095972153157633 | 351.25 | 16.083333333333332 |

All data is synthetic. No Azure resources were deployed or called.
Inventory optimisation is deferred to Milestone 5.
