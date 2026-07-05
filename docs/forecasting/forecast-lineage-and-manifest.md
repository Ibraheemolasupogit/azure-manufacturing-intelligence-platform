# Forecast Lineage And Manifest

`outputs/forecasting/forecast-manifest.json` records the forecast run ID, governed input hash, upstream ingestion manifest hash, upstream ingestion run ID, grain, target field, split dates, enabled models, selected model, output file evidence, metrics, warnings, and no-deployment status.

`outputs/forecasting/lineage-records.json` links accepted sales orders to daily demand, features, model comparison, backtests, model metadata, forecasts, diagnostics, and reports. It does not claim Microsoft Purview registration.

Extended forecasting evidence is produced under `.generated/forecasting/` from the accepted governed sales-order file only. Raw extended files are never used directly for model training.
