# Forecasting Design

Milestone 4 adds a deterministic local demand-forecasting pipeline. It consumes governed accepted sales orders, verifies Milestone 3 ingestion evidence, constructs daily demand series, creates leakage-safe features, performs chronological validation and test evaluation, and writes forecast-ready outputs.

The default controlled run uses `data/interim/accepted/sales_orders.csv`. This tracked sample is intentionally small and supports smoke evidence only. The extended deterministic profile in `configs/synthetic_data_forecasting.yaml` and `configs/ingestion_forecasting.yaml` prepares longer governed data under `.generated/forecasting/` when deeper backtesting evidence is needed. The preparation command validates generation, validates ingestion, verifies accepted sales-order hashes, and enforces a zero unexpected sales-order quarantine threshold.

No Azure services are deployed or called.
