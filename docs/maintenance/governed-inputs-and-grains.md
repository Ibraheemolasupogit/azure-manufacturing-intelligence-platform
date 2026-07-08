# Governed Inputs and Grains

Maintenance analytics reads `data/interim/accepted/equipment_health.jsonl` and `data/interim/accepted/production_events.jsonl`. It also uses `data/interim/accepted/quality_checks.csv` and `outputs/quality/quality_alerts.csv` as optional context. The ingestion manifest, validation summary, data-quality report, ingestion lineage, and quality manifest are verified before scoring.

Principal alert grain is `sensor_event_id`. Trend grain is `machine_id + sensor_type + event_date`. Supported analysis grains include plant, plant plus line, plant plus line plus machine, machine, machine plus sensor type, machine plus sensor ID, machine plus maintenance state, and machine plus operating mode.

The equipment schema uses `timestamp`, `line_id`, `sensor_event_id`, `sensor_type`, `measurement_unit`, threshold fields, runtime fields, service-hour proxy fields, operating mode, and maintenance state. Maintenance outputs expose `event_timestamp` and `production_line_id` for downstream consistency.
