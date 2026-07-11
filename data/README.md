# Data Zones

The local data layout mirrors governed lakehouse zones without requiring Azure storage.

| Zone | Purpose | Current status |
| --- | --- | --- |
| `data/raw/` | Immutable synthetic source extracts and event files. | Deterministic Milestone 2 synthetic files |
| `data/interim/` | Governed accepted records, quarantine records, and ingestion metadata. | Milestone 3 local ingestion evidence |
| `data/processed/` | Analytics-ready local outputs for later pipelines. | Directory scaffold only |

Milestone 4 forecast outputs are stored outside the data lake zones:

- `outputs/forecasting/`: daily demand series, features, split metadata, model comparison, backtests, metrics, diagnostics, model metadata, forecast manifest, and lineage.
- `outputs/demand_forecast.csv`: forecast-ready demand output.
- `reports/demand_forecasting_report.md`: human-readable forecast evidence.

Milestone 5 inventory outputs are also stored outside the data lake zones:

- `outputs/inventory_scores.csv`: portfolio-level inventory health and action scores.
- `outputs/inventory/`: warehouse demand allocation, supplier risk metrics, policy inputs, inventory position, inventory scores, reorder recommendations, scenario results, diagnostics, manifest, and lineage.
- `reports/inventory_intelligence_report.md`: human-readable inventory recommendation evidence.
- `reports/inventory_scenario_summary.md`: human-readable scenario comparison evidence.

Milestone 6 quality outputs are also stored outside the data lake zones:

- `outputs/quality_alerts.csv`: portfolio-level quality alert extract.
- `outputs/quality/`: quality observations, KPIs, defect Pareto, process capability, control-chart points, SPC signals, anomaly scores, alerts, risk summary, diagnostics, manifest, and lineage.
- `reports/quality_analytics_report.md`: human-readable quality analytics evidence.
- `reports/quality_alert_summary.md`: human-readable alert summary evidence.

Milestone 7 maintenance outputs are also stored outside the data lake zones:

- `outputs/maintenance_predictions.json`: portfolio-level projection of alert and score summaries.
- `outputs/maintenance/`: equipment-health features, scores, alerts, machine and sensor summaries, degradation signals, anomaly scores, risk summary, diagnostics, manifest, and lineage.
- `reports/maintenance_analytics_report.md`: human-readable predictive-maintenance evidence.
- `reports/maintenance_alert_summary.md`: human-readable maintenance alert summary.

Milestone 8 monitoring outputs are also stored outside the data lake zones:

- `outputs/platform_health_summary.json`: portfolio-level platform health projection.
- `outputs/monitoring/`: platform health summary, pipeline health, domain health scores, data-quality monitoring, model and analytics monitoring, alerts, integrity checks, lineage completeness, diagnostics, manifest, and lineage.
- `reports/platform_monitoring_report.md`: human-readable monitoring report.
- `reports/observability_summary.md`: concise observability summary.

Milestone 9 GenAI assistant outputs are also stored outside the data lake zones:

- `outputs/genai/`: evidence catalogue, retrieval results, prompt templates, rendered prompts, assistant responses, guardrail decisions, evaluation, diagnostics, manifest, and lineage.
- `reports/genai_operations_assistant_report.md`: controlled assistant run summary.
- `reports/genai_guardrails_report.md`: guardrail policy and refusal summary.
- `reports/executive_manufacturing_brief.md`, `reports/supply_chain_summary.md`, and `reports/manufacturing_operations_report.md`: stable curated narrative projections from deterministic assistant responses.

Milestone 10 dashboard outputs are also stored outside the data lake zones:

- `outputs/dashboard/`: dashboard dimensions, facts, executive scorecard, metric catalogue, semantic model metadata, page specs, visual specs, diagnostics, manifest, and lineage.
- `reports/dashboard_output_report.md`: controlled dashboard output summary.
- `reports/semantic_model_summary.md`: semantic model summary.
- `dashboard/dashboard_index.md`, `dashboard/powerbi_ready_outputs.md`, and `dashboard/semantic_model_notes.md`: portfolio-level dashboard documentation.

Milestone 11 architecture outputs are also stored outside the data lake zones:

- `outputs/architecture/`: Azure service mapping, security controls, data architecture layers, MLOps mapping, GenAI architecture mapping, operations mapping, cost considerations, ADRs, validation results, manifest, and lineage.
- `reports/azure_architecture_report.md`: controlled architecture blueprint summary.
- `reports/deployment_boundary_report.md`: no-deployment boundary summary.
- `docs/architecture/`, `diagrams/`, and `infra/`: reference-only docs, Mermaid diagrams, Bicep/Terraform blueprints, policy notes, and runbooks.

Milestone 2 generates synthetic raw files only:

- `production_events.jsonl`
- `inventory_levels.csv`
- `sales_orders.csv`
- `quality_checks.csv`
- `equipment_health.jsonl`
- `warehouse_movements.csv`
- `supplier_performance.csv`
- `schema_metadata.json`
- `generation_manifest.json`
- `generation_summary.md`

These files are generated from `configs/synthetic_data.yaml` using `make generate-data`. The local sample is intentionally committed because it is small, deterministic, and useful as portfolio evidence. Larger or run-specific outputs should be written outside `data/raw/`, preferably under ignored `.generated/`.

Milestone 3 validates the raw files into:

- `data/interim/accepted/`: accepted records in the original dataset format.
- `data/interim/quarantine/`: rejected records as JSONL with rule codes, issue details, and original records.
- `data/interim/_metadata/`: ingestion manifest, validation summary, quarantine summary, data-quality report, and lineage records.

`configs/synthetic_data_ci.yaml` is a deliberately smaller profile for fast CI and tests. It writes to `.generated/ci/raw/` through `make generate-data-ci`.

Useful commands:

- `make generate-data`: regenerate the tracked local sample with explicit overwrite.
- `make generate-data-ci`: generate the smaller ignored CI sample.
- `make validate-generation`: validate the existing tracked sample without regenerating it.
- `make ingest`: validate the tracked raw sample and regenerate local interim evidence.
- `make ingest-ci`: run the CI ingestion profile under ignored `.generated/ci/interim/`.
- `make validate-ingestion`: validate the existing tracked interim evidence without regenerating it.
- `make forecast`: regenerate tracked controlled forecast evidence.
- `make prepare-forecast-data`: generate, validate, ingest, validate, and threshold-check the ignored extended forecasting dataset.
- `make forecast-ci`: generate ignored CI forecast evidence.
- `make validate-forecast`: validate an existing forecast run without retraining.
- `make inventory`: regenerate tracked controlled inventory intelligence evidence.
- `make inventory-ci`: generate ignored CI inventory evidence.
- `make validate-inventory`: validate an existing inventory run without rescoring.
- `make quality-analytics`: regenerate tracked controlled quality analytics evidence.
- `make quality-analytics-ci`: generate ignored CI quality evidence.
- `make validate-quality-analytics`: validate an existing quality run without rescoring.
- `make maintenance`: regenerate tracked controlled predictive-maintenance evidence.
- `make maintenance-ci`: generate and validate ignored CI maintenance evidence.
- `make validate-maintenance`: validate an existing maintenance run without rescoring.
- `make monitoring`: regenerate tracked controlled monitoring evidence.
- `make monitoring-ci`: generate and validate ignored CI monitoring evidence.
- `make validate-monitoring`: validate an existing monitoring run without recalculating.
- `make genai`: regenerate tracked controlled GenAI assistant evidence.
- `make genai-ci`: generate and validate ignored CI GenAI assistant evidence.
- `make validate-genai`: validate an existing GenAI assistant run without recalculating responses.
- `make dashboard`: regenerate tracked controlled dashboard evidence.
- `make dashboard-ci`: generate and validate ignored CI dashboard evidence.
- `make validate-dashboard`: validate an existing dashboard run without recalculating outputs.
- `make architecture`: regenerate tracked controlled Azure reference architecture evidence.
- `make architecture-ci`: generate and validate ignored CI architecture evidence.
- `make validate-architecture`: validate an existing architecture run without regenerating outputs.

Direct generator and ingestion calls refuse to overwrite existing managed files unless `--overwrite` is provided. Raw files are treated as immutable inputs. All data must remain synthetic and must not represent real employees, customers, suppliers, or commercially sensitive operations.
