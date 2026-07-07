# Inventory Intelligence Design

Milestone 5 adds a deterministic local inventory-intelligence pipeline. It consumes governed accepted inventory snapshots, supplier performance, warehouse movements, sales orders, and validated demand forecasts. It writes inventory health, reorder recommendations, scenario comparison, diagnostics, manifest, lineage, and a human-readable report.

The default controlled run uses only tracked governed inputs:

- `data/interim/accepted/inventory_levels.csv`
- `data/interim/accepted/supplier_performance.csv`
- `data/interim/accepted/warehouse_movements.csv`
- `data/interim/accepted/sales_orders.csv`
- `outputs/demand_forecast.csv`

The pipeline verifies upstream ingestion and forecast manifests before scoring. It rejects direct raw-zone inputs and records all governed input hashes in `outputs/inventory/inventory-manifest.json`.

No Azure services are deployed or called.
