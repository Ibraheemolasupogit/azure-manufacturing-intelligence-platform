# Governed Evidence Inputs

Monitoring consumes tracked governed evidence only:

- `data/raw/generation_manifest.json`
- `data/raw/schema_metadata.json`
- `data/interim/_metadata/ingestion-manifest.json`
- `data/interim/_metadata/validation-summary.json`
- `data/interim/_metadata/data-quality-report.json`
- lineage files from ingestion, forecasting, inventory, quality, and maintenance
- forecasting, inventory, quality, and maintenance manifests
- portfolio outputs such as `outputs/demand_forecast.csv`, `outputs/inventory_scores.csv`, `outputs/quality_alerts.csv`, and `outputs/maintenance_predictions.json`

Required evidence must exist, be parseable, and match manifest hashes and row counts where available. Optional live telemetry is not used.
