# Data Contracts

Milestones 2 through 9 implement deterministic synthetic raw source files, governed local ingestion into accepted and quarantined interim zones, governed demand-forecast outputs, governed inventory-intelligence outputs, governed quality-analytics outputs, governed maintenance outputs, governed monitoring outputs, and deterministic GenAI assistant evidence. These are local synthetic-data contracts only; they do not describe external customer feeds.

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

## Synthetic raw data domains

- `production_events.jsonl`: event ID, event timestamp, plant ID, production-line ID, machine ID, product ID, production order ID, shift ID, planned quantity, produced quantity, accepted quantity, rejected quantity, cycle time, target cycle time, downtime duration, event type, and operating status.
- `inventory_levels.csv`: snapshot timestamp, warehouse ID, plant ID, item ID, product or material type, on-hand quantity, reserved quantity, available quantity, reorder point, safety-stock quantity, lead time, unit cost, and expiry date where applicable.
- `sales_orders.csv`: order ID, order date, requested delivery date, customer or market segment, product ID, ordered quantity, fulfilled quantity, selling price, distribution region, and order status.
- `quality_checks.csv`: inspection ID, inspection timestamp, plant ID, line ID, machine ID, batch ID, product ID, quality metric, measured value, lower specification limit, upper specification limit, inspection result, defect category, and severity.
- `equipment_health.jsonl`: sensor-event ID, timestamp, plant ID, line ID, machine ID, sensor ID, sensor type, measurement, measurement unit, warning threshold, critical threshold, operating mode, and maintenance state.
- `warehouse_movements.csv`: movement ID, movement timestamp, warehouse ID, source location, destination location, item ID, quantity, movement type, reference order, and operator or automated-system ID.
- `supplier_performance.csv`: supplier ID, material ID, purchase-order ID, order date, promised date, actual delivery date, ordered quantity, delivered quantity, accepted quantity, rejected quantity, unit price, supplier region, quality score, and delivery status.

All data must be synthetic and free of real personal, customer, supplier, employee, and commercially sensitive information.

## Milestone 2 schema metadata

Milestone 2 writes `data/raw/schema_metadata.json` with dataset filenames, file formats, schema version, and ordered fields. It also writes `data/raw/generation_manifest.json` with deterministic run metadata, output paths, row counts, hashes, software version, configuration version, and random seed.

The schema registry also records primary keys, field data types, nullable fields, categorical domains, timestamp fields, units, relationship references, invariants, logical owner/domain, and synthetic-data classification. The committed `data/raw/` files are a small deterministic sample; larger local or CI runs belong under ignored output locations such as `.generated/`.

## Milestone 3 ingestion contracts

Milestone 3 reads the raw schema registry and generation manifest as source-of-truth metadata. It verifies required files, row-level parseability, configured schema fields, source file sizes, and SHA-256 hashes before writing governed outputs.

Accepted outputs preserve the raw dataset format:

- CSV sources remain CSV with the same header order.
- JSONL sources remain JSONL.
- Accepted files are written under `data/interim/accepted/`.

Quarantine outputs are always JSONL under `data/interim/quarantine/`. Each quarantined record includes dataset, source row number, record ID, ordered rule codes, structured issues, ingestion run ID, and original record payload.

Ingestion metadata is written under `data/interim/_metadata/`:

- `ingestion-manifest.json`
- `validation-summary.json`
- `quarantine-summary.json`
- `data-quality-report.json`
- `lineage-records.json`

`make validate-ingestion` validates these metadata files and output hashes without regenerating the run.

## Future output contracts

Planned outputs include:

Implemented Milestone 4 outputs include:

- `outputs/demand_forecast.csv`
- `outputs/forecasting/daily_demand_series.csv`
- `outputs/forecasting/feature_dataset.csv`
- `outputs/forecasting/model_comparison.csv`
- `outputs/forecasting/backtest_predictions.csv`
- `outputs/forecasting/backtest_metrics.csv`
- `outputs/forecasting/test_metrics.csv`
- `outputs/forecasting/forecast-manifest.json`
- `outputs/forecasting/lineage-records.json`
- `reports/demand_forecasting_report.md`

Implemented Milestone 5 outputs include:

- `outputs/inventory_scores.csv`
- `outputs/inventory/warehouse_demand_forecast.csv`
- `outputs/inventory/supplier_risk_metrics.csv`
- `outputs/inventory/inventory_policy_inputs.csv`
- `outputs/inventory/inventory_position.csv`
- `outputs/inventory/inventory_scores.csv`
- `outputs/inventory/inventory_health.csv`
- `outputs/inventory/reorder_recommendations.csv`
- `outputs/inventory/scenario_results.csv`
- `outputs/inventory/scenario_comparison.csv`
- `outputs/inventory/inventory_summary.json`
- `outputs/inventory/inventory_diagnostics.json`
- `outputs/inventory/inventory-manifest.json`
- `outputs/inventory/lineage-records.json`
- `reports/inventory_intelligence_report.md`

Implemented Milestone 6 outputs include:

- `outputs/quality_alerts.csv`
- `outputs/quality/quality_observations.csv`
- `outputs/quality/quality_kpis.csv`
- `outputs/quality/defect_pareto.csv`
- `outputs/quality/process_capability.csv`
- `outputs/quality/control_chart_points.csv`
- `outputs/quality/spc_signals.csv`
- `outputs/quality/anomaly_scores.csv`
- `outputs/quality/quality_alerts.csv`
- `outputs/quality/quality_risk_summary.csv`
- `outputs/quality/quality_diagnostics.json`
- `outputs/quality/quality-manifest.json`
- `outputs/quality/lineage-records.json`
- `reports/quality_analytics_report.md`
- `reports/quality_alert_summary.md`

Future outputs include:

- `outputs/maintenance_predictions.json`
- `outputs/production_kpis.csv`
- `outputs/supplier_risk_scores.csv`
- `outputs/powerbi_manufacturing_fact.csv`
- `outputs/powerbi_inventory_fact.csv`
- `reports/manufacturing_operations_report.md`
- `reports/supply_chain_summary.md`
- `reports/executive_manufacturing_brief.md`

Future run manifests should include run ID, pipeline name, configuration version, input paths, input hashes, output paths, output hashes, row counts, validation status, software version, random seed, and success or failure status. Current controlled analytical manifests avoid current timestamps so outputs remain reproducible.
## Maintenance analytics contract

Milestone 7 consumes only governed accepted inputs:

- `data/interim/accepted/equipment_health.jsonl`
- `data/interim/accepted/production_events.jsonl`
- optional `data/interim/accepted/quality_checks.csv`
- optional `outputs/quality/quality_alerts.csv`

Required equipment fields include `sensor_event_id`, `timestamp`, `plant_id`, `line_id`, `machine_id`, `sensor_id`, `sensor_type`, `measurement`, `measurement_unit`, `warning_threshold`, `critical_threshold`, `threshold_status`, `runtime_hours`, `service_hours_since_maintenance`, `degradation_index`, `operating_mode`, and `maintenance_state`.

The maintenance contract requires upstream manifest hash verification, row-count verification, successful ingestion validation, synthetic-data classification, coherent sensor type/unit pairs, non-negative runtime and service fields, valid thresholds, unique sensor event IDs, relative manifest paths, deterministic run identity, and unchanged upstream inputs.

Maintenance outputs under `outputs/maintenance/` are controlled portfolio evidence. CI and experiments must write under `.generated/`.

## Monitoring contract

Milestone 8 consumes tracked evidence only: generation, ingestion, forecast, inventory, quality, and maintenance manifests; lineage files; portfolio outputs; and data-quality evidence. Required evidence must exist, parse successfully, match declared SHA-256 hashes and row counts where available, and confirm synthetic classification.

Monitoring outputs under `outputs/monitoring/` and `outputs/platform_health_summary.json` are controlled portfolio evidence. CI and experiments must write under `.generated/`.
## GenAI Assistant Evidence Contract

Milestone 9 treats generation, ingestion, forecasting, inventory, quality, maintenance, and monitoring artefacts as immutable governed inputs. Required inputs must exist, be parseable, retain matching hashes where upstream manifests expose them, carry successful validation status, carry synthetic-data classification, and provide lineage where available.

GenAI outputs must use relative safe paths, stable SHA-256 hashes, row counts for CSV outputs, `external_model_called=false`, `azure_deployment=false`, citation references to valid evidence IDs, zero unsupported claims for standard tasks, grounding and citation coverage above configured thresholds, synthetic-data disclaimers, and deterministic run identity.

Existing-run validation must detect missing outputs, tampered hashes, row-count mismatches, invalid citations, invalid evidence references, missing disclaimers, external-call flags, lineage target gaps, and run-ID mismatches.

## Dashboard Output Contract

Milestone 10 dashboard outputs must consume governed tracked evidence only. Required inputs must exist, upstream manifests must be successful, source hashes must match where manifests expose them, lineage must exist, synthetic classification must be present, and upstream files must remain unchanged.

Dashboard outputs must include non-empty dimensions and facts, unique primary keys where declared, valid semantic model relationships, complete metric catalogue entries, page and visual specs that reference generated tables/pages, synthetic-data disclaimers, `power_bi_deployment=false`, `fabric_deployment=false`, `azure_deployment=false`, deterministic run identity, output row counts, sizes, hashes, manifest, and lineage.

## Azure Architecture Output Contract

Milestone 11 architecture outputs consume governed tracked evidence only. Required ingestion, forecast, inventory, quality, maintenance, monitoring, GenAI, and dashboard manifests and lineage files must exist, validate successfully, carry governed evidence, retain source hashes, and remain unchanged.

Architecture outputs must include Azure service mapping, security controls, data architecture layers, MLOps mapping, GenAI architecture mapping, operations mapping, cost considerations, ADRs, validation results, manifest, lineage, reports, docs, diagrams, and static Bicep/Terraform blueprint files. Deployment mode must be `reference_only`; live deployment, Azure CLI execution, Terraform apply, Bicep deployment, Power BI deployment, Fabric deployment, and Azure credential requirements must remain false.

Existing-run validation must detect missing files, tampered row counts, tampered sizes, tampered hashes, incomplete service mappings, incomplete security domains, missing ADR decisions, invalid deployment flags, forbidden active deployment commands, real-looking secrets, lineage target gaps, upstream hash changes, and run-ID mismatches.
