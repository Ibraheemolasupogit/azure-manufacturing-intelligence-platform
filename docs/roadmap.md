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
Planned evidence: sample synthetic files, generator tests, and manifest examples.
Dependencies: Milestone 1.
Out of scope: advanced analytics and cloud ingestion.

## Milestone 3 - Governed ingestion and validation

Objective: ingest source files into governed local zones with validation.
Principal components: schema checks, quarantine handling, lineage, and manifests.
Planned evidence: accepted and rejected synthetic records with audit trails.
Dependencies: Milestones 1-2.
Out of scope: forecasting and optimisation.

## Milestone 4 - Demand forecasting

Objective: forecast product demand from synthetic sales history.
Principal components: baseline models, evaluation metrics, forecast outputs.
Planned evidence: forecast CSV and model report.
Dependencies: Milestones 1-3.
Out of scope: deep learning and live demand feeds.

## Milestone 5 - Inventory intelligence and optimisation

Objective: score inventory risk and recommend replenishment priorities.
Principal components: stockout risk, overstock, safety-stock coverage, reorder logic.
Planned evidence: inventory score output and documented assumptions.
Dependencies: Milestones 1-4.
Out of scope: solver-heavy optimisation unless justified.

## Milestone 6 - Quality analytics and anomaly detection

Objective: detect quality deterioration and unusual measurements.
Principal components: quality KPIs, rule-based alerts, statistical anomaly checks.
Planned evidence: quality alerts and evaluation notes.
Dependencies: Milestones 1-3.
Out of scope: unvalidated production claims.

## Milestone 7 - Predictive maintenance

Objective: identify equipment health risks from synthetic telemetry.
Principal components: sensor features, maintenance labels, risk scoring.
Planned evidence: maintenance prediction output and explainability notes.
Dependencies: Milestones 1-3.
Out of scope: live IoT integration.

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
