# Inventory Outputs And Lineage

Milestone 5 writes:

- `outputs/inventory_scores.csv`: portfolio-level inventory score table.
- `outputs/inventory/inventory_health.csv`: full item-location calculations.
- `outputs/inventory/reorder_recommendations.csv`: prioritised non-maintain actions.
- `outputs/inventory/scenario_comparison.csv`: baseline, higher-service-level, and constrained-capital scenario evidence.
- `outputs/inventory/inventory_summary.json`: aggregate KPIs.
- `outputs/inventory/inventory_diagnostics.json`: calculation diagnostics.
- `outputs/inventory/inventory-manifest.json`: run ID, input hashes, policy assumptions, output evidence, and Azure reference mapping.
- `outputs/inventory/lineage-records.json`: local lineage from governed inputs to each output.
- `reports/inventory_intelligence_report.md`: human-readable recommendation summary.

`make validate-inventory` validates an existing inventory run without rescoring. It checks the manifest, lineage, output hashes, row counts, bounded risk scores, non-negative reorder quantities, duplicate item-location keys, and current upstream input hashes.
