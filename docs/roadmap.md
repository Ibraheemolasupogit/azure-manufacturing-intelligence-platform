# Roadmap

## Milestone 1 - Repository foundation and architecture

Objective: establish the repository scaffold, architecture docs, typed config, shared utilities, tests, and CI.
Principal components: docs, diagrams, package skeleton, config loader, structure validator.
Planned evidence: passing quality suite and milestone evidence document.
Dependencies: none.
Out of scope: data generation, analytics, ML, dashboards, and Azure deployment.

## Milestone 2 - Synthetic manufacturing datasets

Objective: create deterministic synthetic source data.
Principal components: data generators and source schemas.
Evidence: synthetic raw files, schema metadata, generator tests, generation manifest, and generation summary.
Dependencies: Milestone 1.
Out of scope: advanced analytics and cloud ingestion.

## Milestone 3 - Governed ingestion and validation

Objective: ingest source files into governed local zones with validation.
Principal components: schema checks, quarantine handling, lineage, and manifests.
Evidence: accepted records, empty successful quarantine files for the tracked sample, validation summaries, quarantine summaries, lineage records, ingestion manifest, data-quality report, and tests for invalid-record quarantine.
Dependencies: Milestones 1-2.
Out of scope: forecasting and optimisation.

## Milestone 4 - Demand forecasting

Objective: forecast product demand from synthetic sales history.
Principal components: baseline models, evaluation metrics, forecast outputs.
Evidence: daily demand series, feature dataset, chronological splits, backtests, model comparison, selected model metadata, held-out test metrics, forecast CSV, forecast manifest, lineage, Markdown report, and an ignored extended governed profile for stronger backtesting evidence.
Dependencies: Milestones 1-3.
Out of scope: inventory optimisation, deep learning, live demand feeds, and Azure ML deployment.

## Milestone 5 - Inventory intelligence and optimisation

Objective: score inventory risk, allocate forecast demand to warehouses, and recommend replenishment priorities under deterministic budget and capacity constraints.
Principal components: stockout risk, overstock, safety-stock coverage, reorder logic, supplier risk, working-capital exposure, and deterministic scenario comparison.
Evidence: warehouse demand forecast allocation, supplier risk metrics, policy inputs, inventory position, inventory score output, reorder recommendations, scenario results, diagnostics, manifest, lineage, reports, tests, and documented assumptions.
Dependencies: Milestones 1-4.
Out of scope: production scheduling, quality analytics, dashboards, GenAI, live solver services, and cloud deployment.

## Milestone 6 - Quality analytics and anomaly detection

Objective: detect quality deterioration and unusual measurements.
Principal components: specification compliance, yield proxies, Pareto analysis, capability diagnostics, control charts, SPC rules, robust z-score, Isolation Forest diagnostics, risk scoring, and deterministic alerts.
Evidence: quality observations, KPIs, defect Pareto, process capability, control-chart points, SPC signals, anomaly scores, quality alerts, diagnostics, manifest, lineage, reports, tests, and documented limitations.
Dependencies: Milestones 1-3.
Out of scope: predictive maintenance, root-cause claims, dashboards, GenAI, and Azure deployment.

## Milestone 7 - Predictive maintenance

Objective: identify equipment health risks from synthetic telemetry.
Principal components: governed equipment loading, production and quality context, threshold compliance, runtime/service proxies, degradation indicators, robust z-score, deterministic Isolation Forest diagnostics, failure-risk scoring, equipment-health scoring, alerts, manifest, lineage, reports, and existing-run validation.
Evidence: equipment features, scores, alerts, machine and sensor summaries, degradation signals, anomaly scores, diagnostics, `outputs/maintenance_predictions.json`, manifest, lineage, reports, tests, and documented limitations.
Dependencies: Milestones 1-6.
Status: Complete.
Out of scope: Milestone 8 monitoring, live IoT integration, cloud deployment, dashboards, GenAI, and safety-certified maintenance instructions.

## Milestone 8 - Operational monitoring and observability

Objective: expose local run metrics, logs, and health checks.
Principal components: structured logs, run summaries, pipeline status.
Planned evidence: monitoring report and failure examples.
Dependencies: Milestones 1-3.
Out of scope: live Azure Monitor integration.

## Milestone 9 - GenAI manufacturing operations assistant

Objective: generate governed operational recommendations for human review.
Principal components: prompt templates, context assembly, safety guardrails.
Planned evidence: recommendation examples from synthetic data.
Dependencies: Milestones 1-8.
Out of scope: ungrounded advice and real operational decisions.

## Milestone 10 - Power BI-ready analytical outputs

Objective: produce semantic extracts for dashboard development.
Principal components: fact tables, dimensions, KPI extracts, documentation.
Planned evidence: Power BI-ready CSVs and data dictionary.
Dependencies: Milestones 1-8.
Out of scope: publishing to Power BI service.

## Milestone 11 - Azure reference architecture and deployment mapping

Objective: document cloud deployment design and service responsibilities.
Principal components: architecture mapping, security model, IaC guidance if justified.
Planned evidence: reference architecture and deployment notes.
Dependencies: Milestones 1-10.
Out of scope: claiming deployed resources without real deployment evidence.

## Milestone 12 - Portfolio evidence and final polish

Objective: assemble interview-ready evidence and final documentation.
Principal components: demos, diagrams, summaries, limitations, and next steps.
Planned evidence: portfolio narrative and reproducible validation results.
Dependencies: all prior milestones.
Out of scope: adding new analytical scope without tests.
