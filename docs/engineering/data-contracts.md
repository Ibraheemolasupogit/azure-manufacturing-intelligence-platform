# Data Contracts

Milestone 1 does not implement datasets. Future data contracts should follow these principles.

## Contract principles

- Schema versioning must identify breaking and non-breaking changes.
- Every event should have a unique identifier.
- Event timestamps and ingestion timestamps must be distinct.
- Units of measure must be explicit and consistent.
- Timezone handling must be standardised, preferably UTC at rest.
- Nullability must be documented field by field.
- Categorical values must have valid enumerations.
- Duplicate handling must be deterministic and auditable.
- Invalid records must be quarantined with reasons.
- Source lineage must identify file, generator, run ID, and configuration version.
- Synthetic generation must be deterministic from a seed.
- Raw inputs should be treated as immutable.
- Pipeline runs should produce manifests.

## Planned data domains

- `production_events.jsonl`: event ID, event timestamp, plant ID, production-line ID, machine ID, product ID, production order ID, shift ID, planned quantity, produced quantity, accepted quantity, rejected quantity, cycle time, target cycle time, downtime duration, event type, and operating status.
- `inventory_levels.csv`: snapshot timestamp, warehouse ID, plant ID, item ID, product or material type, on-hand quantity, reserved quantity, available quantity, reorder point, safety-stock quantity, lead time, unit cost, and expiry date where applicable.
- `sales_orders.csv`: order ID, order date, requested delivery date, customer or market segment, product ID, ordered quantity, fulfilled quantity, selling price, distribution region, and order status.
- `quality_checks.csv`: inspection ID, inspection timestamp, plant ID, line ID, machine ID, batch ID, product ID, quality metric, measured value, lower specification limit, upper specification limit, inspection result, defect category, and severity.
- `equipment_health.jsonl`: sensor-event ID, timestamp, plant ID, line ID, machine ID, sensor ID, sensor type, measurement, measurement unit, warning threshold, critical threshold, operating mode, and maintenance state.
- `warehouse_movements.csv`: movement ID, movement timestamp, warehouse ID, source location, destination location, item ID, quantity, movement type, reference order, and operator or automated-system ID.
- `supplier_performance.csv`: supplier ID, material ID, purchase-order ID, order date, promised date, actual delivery date, ordered quantity, delivered quantity, accepted quantity, rejected quantity, unit price, supplier region, quality score, and delivery status.

All data must be synthetic and free of real personal, customer, supplier, employee, and commercially sensitive information.

## Future output contracts

Planned outputs include:

- `outputs/demand_forecast.csv`
- `outputs/inventory_scores.csv`
- `outputs/quality_alerts.csv`
- `outputs/maintenance_predictions.json`
- `outputs/production_kpis.csv`
- `outputs/supplier_risk_scores.csv`
- `outputs/powerbi_manufacturing_fact.csv`
- `outputs/powerbi_inventory_fact.csv`
- `reports/manufacturing_operations_report.md`
- `reports/supply_chain_summary.md`
- `reports/executive_manufacturing_brief.md`

Future run manifests should include run ID, pipeline name, configuration version, input paths, input hashes, output paths, output hashes, row counts, validation status, start and completion timestamps, software version, random seed, and success or failure status.
