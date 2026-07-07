# Governed Inputs And Grains

Milestone 6 consumes:

- `data/interim/accepted/quality_checks.csv`
- `data/interim/accepted/production_events.jsonl`
- `data/interim/_metadata/ingestion-manifest.json`
- `data/interim/_metadata/validation-summary.json`
- `data/interim/_metadata/data-quality-report.json`
- `data/interim/_metadata/lineage-records.json`

The principal alert grain is `inspection_id`. The trend grain is
`product_id + quality_metric + inspection_date`. Control charts and anomaly
baselines use comparable `machine_id + quality_metric + measurement_unit` groups.

The quality source uses `line_id`; quality outputs expose this as
`production_line_id` to align with production events. References are checked by
`batch_id`, `plant_id`, `line_id`, `machine_id`, and `product_id`.

Metrics are not aggregated across incompatible units. The current synthetic
mapping is `diameter_mm -> mm`, `torque_nm -> Nm`, and
`surface_finish_ra -> ra`.
