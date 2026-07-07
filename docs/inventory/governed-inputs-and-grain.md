# Governed Inputs And Grain

Milestone 5 consumes only governed local inputs:

- `data/interim/accepted/inventory_levels.csv`
- `data/interim/accepted/supplier_performance.csv`
- `data/interim/accepted/warehouse_movements.csv`
- `data/interim/accepted/sales_orders.csv`
- `outputs/demand_forecast.csv`
- `data/interim/_metadata/ingestion-manifest.json`
- `data/interim/_metadata/validation-summary.json`
- `data/interim/_metadata/data-quality-report.json`
- `data/interim/_metadata/lineage-records.json`
- `outputs/forecasting/forecast-manifest.json`
- `outputs/forecasting/model_metadata.json`
- `outputs/forecasting/lineage-records.json`

The configured decision grain is `warehouse_id` plus `item_id`. Product rows use
`product_id`, material rows use `material_id`, and both are normalised into the
shared item-location grain.

The loader rejects direct `data/raw` inventory inputs, missing upstream evidence,
unresolved product/material identifiers, unresolved warehouses, non-synthetic
classifications, and invalid negative quantities in governed source files.

The inventory run never mutates upstream accepted data or forecast files. Tests
verify upstream file hashes before and after a run.
