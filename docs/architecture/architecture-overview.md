# Architecture Overview

The platform is designed as a local-first reference implementation of an Azure manufacturing analytics estate. Milestones 1 through 9 create the repository foundation, deterministic synthetic raw data, governed local ingestion, validation, quarantine, lineage, demand forecasting, inventory intelligence, quality analytics, anomaly detection, predictive maintenance, monitoring, and a deterministic local GenAI-style operations assistant.

## Conceptual flow

Synthetic manufacturing sources feed the raw zone under `data/raw/`. Milestone 3 ingestion validates those sources and separates accepted records from quarantined records under `data/interim/`. Milestone 4 uses accepted sales orders to build daily demand features, chronological model evaluation, future forecasts, reports, and lineage. Milestone 5 combines accepted inventory, supplier, warehouse-movement, sales, and forecast evidence to score inventory health and policy recommendations. Milestone 6 combines accepted quality checks and production events to calculate specification compliance, KPIs, Pareto summaries, capability diagnostics, control charts, SPC signals, anomaly scores, quality-risk scores, alerts, reports, and lineage. Milestone 7 adds predictive maintenance, Milestone 8 adds monitoring, and Milestone 9 adds deterministic GenAI-style assistance. Later milestones will add dashboard outputs.

The planned domains are production telemetry, inventory, sales orders, quality checks, equipment health, warehouse movements, and supplier performance. Future pipelines will support both batch and streaming paths.

## Governance and observability

Milestone 3 produces lineage metadata, data-quality evidence, and run manifests containing run ID, pipeline name, configuration hash, input and output paths, hashes, row counts, validation status, software version, and synthetic-data classification. Forecasting, inventory, and quality analytics extend this pattern for analytical outputs, model diagnostics, rules, anomaly scores, and reports.

## Implementation boundary

Milestone 9 does not call real LLMs, generate dashboards, or deploy Azure resources.
## Milestone 7 predictive maintenance

The local predictive-maintenance layer consumes governed accepted equipment-health records, governed production events, and optional governed quality context. It produces deterministic equipment features, threshold compliance, degradation indicators, robust z-score and Isolation Forest anomaly diagnostics, failure-risk scores, equipment-health scores, maintenance alerts, summaries, reports, manifests, and lineage.

The implementation is local-first and reference-mapped only. It does not deploy Azure resources, stream live telemetry, issue certified safety instructions, or claim root cause. Runtime and service outputs are labelled proxies where the synthetic source data lacks real schedules.

## Milestone 8 monitoring

The local monitoring layer consumes tracked governed evidence from generation, ingestion, forecasting, inventory, quality, and maintenance. It verifies manifest integrity, hashes, row counts, lineage completeness, domain health, platform health, and monitoring alerts.

The implementation produces machine-readable monitoring outputs and Markdown observability reports. It is not live Azure Monitor integration and does not ingest live telemetry.
## Milestone 9 GenAI Assistant Layer

The architecture now includes a deterministic local GenAI-style operations assistant. It consumes tracked governed evidence from generation, ingestion, forecasting, inventory, quality, maintenance, and monitoring; builds an evidence catalogue; performs deterministic retrieval; renders prompt templates for audit; applies guardrails; synthesizes citation-backed responses; evaluates those responses; and writes reports, manifests, and lineage.

This layer maps conceptually to Azure AI Foundry, Azure OpenAI Service, Azure AI Search, Azure Machine Learning prompt evaluation, Microsoft Purview, Azure Monitor, and Power BI narrative outputs. These are reference mappings only. No Azure AI service, OpenAI endpoint, vector database, or dashboard is deployed or called.
