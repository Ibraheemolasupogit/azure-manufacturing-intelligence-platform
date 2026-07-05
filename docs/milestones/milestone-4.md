# Milestone 4 - Demand Forecasting And Forecast Evaluation

## Objective

Build a deterministic, leakage-safe, local-first demand-forecasting pipeline from governed accepted sales orders.

## Evidence

- Governed input: `data/interim/accepted/sales_orders.csv`
- Upstream ingestion run ID: `INGEST-da9a11a67abc6a18`
- Input row count: 180
- Input date range: 2026-01-01 to 2026-01-14
- Forecast grain: `product_id` plus `distribution_region`
- Series count: 8
- Forecast run ID: `FORECAST-6357daf22de3ea43`
- Split dates: train 2026-01-01 to 2026-01-08, validation 2026-01-09 to 2026-01-11, test 2026-01-12 to 2026-01-14, forecast 2026-01-15 to 2026-01-21
- Enabled models: seasonal naive, moving average, linear regression, random forest
- Selected model: random forest
- Selection reason: lowest validation WAPE with deterministic tie-breaks
- Held-out test WAPE: 0.2584642904249187
- Forecast horizon: 7 days
- Future forecast rows: 56
- Prediction interval method: empirical absolute residual quantile from rolling backtests

## Validation Metrics

| Model | Validation WAPE | Validation MAE | Bias |
| --- | ---: | ---: | ---: |
| linear_regression | 1.144443 | 191.789633 | 191.065654 |
| moving_average | 1.078639 | 180.761905 | 13.095238 |
| random_forest | 0.263065 | 44.085331 | 6.493944 |
| seasonal_naive | 2.095972 | 351.250000 | 16.083333 |

## Commands Executed

- `git status --short --branch`
- `git log -5 --oneline`
- `make quality`
- `make validate-generation`
- `make validate-ingestion`
- `make prepare-forecast-data`
- `python3 scripts/generate_synthetic_data.py --validate-existing --output-dir .generated/forecasting/raw`
- `python3 -m manufacturing_intelligence.ingestion --config configs/ingestion_forecasting.yaml --validate-existing-run --output-directory .generated/forecasting/interim`
- `python3 -m manufacturing_intelligence.forecasting --config configs/forecasting_extended.yaml --overwrite`
- `python3 -m manufacturing_intelligence.forecasting --config configs/forecasting_extended.yaml --validate-existing-run`
- `make forecast`
- `make validate-forecast`
- `make forecast-ci`
- `python3 -m manufacturing_intelligence.forecasting --config configs/forecasting_ci.yaml --validate-config-only`
- `python3 -m manufacturing_intelligence.forecasting --config configs/forecasting_ci.yaml --validate-existing-run --output-directory .generated/ci/forecasting`

## Known Limitations

The tracked governed sample has 14 days of history. Results are smoke evidence and should not be treated as strong forecasting performance.

## Extended Workflow Correction

Original extended ingestion evidence before correction:

- Extended ingestion run ID: `INGEST-566698637729fb43`
- Sales-order generated rows: 1,629
- Sales-order accepted rows: 1,086
- Sales-order quarantined rows: 543
- Sales-order quarantine rate: 33.333333%
- Rule-code counts: `INVALID_REFERENCE`: 543
- Severity counts: `critical`: 543
- Representative failure: `PROD-001` and `PROD-004` sales orders failed `product_id does not resolve to a known source entity`.
- Concentration: quarantines were concentrated in `PROD-001` and `PROD-004`, `north`, `automotive_oem`, every third order-date pattern.

Root cause:

- The defect was in synthetic data generation.
- The extended profile used a sparse production schedule with six configured products.
- Production product assignment used `(event_index + day_offset) % product_count`, which emitted only `PROD-002`, `PROD-003`, `PROD-005`, and `PROD-006` for the extended two-event-per-day cadence.
- Sales-order generation correctly cycled all six products, so `PROD-001` and `PROD-004` sales references were valid catalogue products but absent from production-derived relationship indexes.

Correction:

- `src/manufacturing_intelligence/data_generation/generator.py` now assigns production products with `(event_index - 1) % product_count`, ensuring sparse production schedules cover the configured product catalogue deterministically.
- `configs/ingestion_forecasting.yaml` is strict with `maximum_quarantine_rate: 0.0`.
- `scripts/prepare_forecasting_data.py` validates generation, validates ingestion, verifies all datasets, verifies accepted sales-order hashes, and fails when sales-order quarantine exceeds the explicit threshold.
- `src/manufacturing_intelligence/forecasting/data.py` again requires zero accepted sales-order quarantine for forecasting inputs.

Corrected extended evidence:

- Extended generation run ID: `synthetic-f0db089ccb37ba01`
- Extended ingestion run ID: `INGEST-314b38d25162c2af`
- Generated row counts: equipment health 724, inventory levels 42, production events 362, quality checks 362, sales orders 1,629, supplier performance 240, warehouse movements 360
- Accepted row counts: equipment health 724, inventory levels 42, production events 362, quality checks 362, sales orders 1,629, supplier performance 240, warehouse movements 360
- Quarantine row counts: zero for all seven datasets
- Quarantine rule-code counts: `{}`
- Extended accepted sales-order path: `.generated/forecasting/interim/accepted/sales_orders.csv`
- Extended accepted sales-order hash: `47c85b4c097a00842c8642bac6e272b5d1e348400bf5d3159c46fa195eeff579`
- Extended demand forecast hash: `7107fa6684c1f4343dacb26f75221a379b34aae8a5521b224d34255d1c8880ed`
- Extended forecast manifest hash: `69e6bbe6c6446b8890c6094c8814637102d25a6b28984a8f07d5ae6bbb961719`
- Extended sales-order date range: 2025-01-01 to 2025-06-30
- Extended forecasting series count: 6
- Extended split dates: train 2025-01-01 to 2025-05-05, validation 2025-05-06 to 2025-06-02, test 2025-06-03 to 2025-06-30, forecast 2025-07-01 to 2025-07-14
- Rolling-origin windows: 3 (`2025-05-03`, `2025-05-04`, `2025-05-05`)
- Extended forecast run ID: `FORECAST-f38190089e889ed7`
- Extended selected model: linear regression
- Extended selection reason: lowest validation WAPE with deterministic tie-breaks
- Extended held-out test WAPE: 0.368752657340131

Extended validation metrics:

| Model | Validation WAPE | Validation MAE | Bias |
| --- | ---: | ---: | ---: |
| linear_regression | 0.370084 | 61.870160 | 5.289425 |
| moving_average | 0.422391 | 70.614796 | 4.357143 |
| random_forest | 0.383225 | 64.067050 | 1.880909 |
| seasonal_naive | 0.872036 | 145.785714 | -122.011905 |

No invalid record was silently discarded. Validation was not weakened. The corrected extended data remains synthetic and ignored under `.generated/`.

## Confirmations

- Upstream raw and interim evidence was not modified.
- All data is synthetic.
- No Azure resources were deployed or called.
- Milestone 5 inventory intelligence and optimisation were not implemented.
- No commit or push was performed.
