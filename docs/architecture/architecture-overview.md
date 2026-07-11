# Architecture Overview

The platform is designed as a local-first reference implementation of an Azure manufacturing analytics estate. Milestones 1 through 11 create the repository foundation, deterministic synthetic raw data, governed local ingestion, validation, quarantine, lineage, demand forecasting, inventory intelligence, quality analytics, anomaly detection, predictive maintenance, monitoring, a deterministic local GenAI-style operations assistant, Power BI-ready dashboard outputs, and a static Azure reference architecture blueprint.

## Conceptual flow

Synthetic manufacturing sources feed the raw zone under `data/raw/`. Milestone 3 ingestion validates those sources and separates accepted records from quarantined records under `data/interim/`. Milestone 4 uses accepted sales orders to build daily demand features, chronological model evaluation, future forecasts, reports, and lineage. Milestone 5 combines accepted inventory, supplier, warehouse-movement, sales, and forecast evidence to score inventory health and policy recommendations. Milestone 6 combines accepted quality checks and production events to calculate quality signals. Milestone 7 adds predictive maintenance, Milestone 8 adds monitoring, Milestone 9 adds deterministic GenAI-style assistance, Milestone 10 adds dashboard-ready semantic outputs, and Milestone 11 maps the tracked evidence to a static Azure reference architecture.

The planned domains are production telemetry, inventory, sales orders, quality checks, equipment health, warehouse movements, and supplier performance. Future pipelines will support both batch and streaming paths.

## Governance and observability

Milestone 3 produces lineage metadata, data-quality evidence, and run manifests containing run ID, pipeline name, configuration hash, input and output paths, hashes, row counts, validation status, software version, and synthetic-data classification. Forecasting, inventory, and quality analytics extend this pattern for analytical outputs, model diagnostics, rules, anomaly scores, and reports.

## Implementation boundary

Milestone 10 does not generate `.pbix` files, call Power BI/Fabric APIs, or deploy Azure resources.
## Milestone 7 predictive maintenance

The local predictive-maintenance layer consumes governed accepted equipment-health records, governed production events, and optional governed quality context. It produces deterministic equipment features, threshold compliance, degradation indicators, robust z-score and Isolation Forest anomaly diagnostics, failure-risk scores, equipment-health scores, maintenance alerts, summaries, reports, manifests, and lineage.

The implementation is local-first and reference-mapped only. It does not deploy Azure resources, stream live telemetry, issue certified safety instructions, or claim root cause. Runtime and service outputs are labelled proxies where the synthetic source data lacks real schedules.

## Milestone 8 monitoring

The local monitoring layer consumes tracked governed evidence from generation, ingestion, forecasting, inventory, quality, and maintenance. It verifies manifest integrity, hashes, row counts, lineage completeness, domain health, platform health, and monitoring alerts.

The implementation produces machine-readable monitoring outputs and Markdown observability reports. It is not live Azure Monitor integration and does not ingest live telemetry.
## Milestone 9 GenAI Assistant Layer

The architecture now includes a deterministic local GenAI-style operations assistant. It consumes tracked governed evidence from generation, ingestion, forecasting, inventory, quality, maintenance, and monitoring; builds an evidence catalogue; performs deterministic retrieval; renders prompt templates for audit; applies guardrails; synthesizes citation-backed responses; evaluates those responses; and writes reports, manifests, and lineage.

This layer maps conceptually to Azure AI Foundry, Azure OpenAI Service, Azure AI Search, Azure Machine Learning prompt evaluation, Microsoft Purview, Azure Monitor, and Power BI narrative outputs. These are reference mappings only. No Azure AI service, OpenAI endpoint, vector database, or dashboard is deployed or called.

## Milestone 10 dashboard outputs

The dashboard layer consumes governed ingestion, forecast, inventory, quality, maintenance, monitoring, and GenAI evidence to produce local dashboard dimensions, fact tables, executive scorecard, metric catalogue, semantic model metadata, dashboard page specifications, visual specifications, reports, manifest, and lineage.

The outputs are Power BI-ready local artefacts only. No Power BI workspace, Fabric semantic model, Azure Synapse serving layer, ADLS curated zone, Purview registration, or Azure Monitor view is deployed.

## Milestone 11 Azure reference architecture

The architecture layer consumes tracked governed evidence from ingestion, forecasting, inventory, quality, maintenance, monitoring, GenAI, and dashboard outputs. It produces Azure service mappings, security controls, data architecture layers, MLOps mappings, GenAI mappings, operations mappings, cost considerations, ADRs, diagrams, reports, static Bicep and Terraform blueprint files, runbooks, a manifest, and lineage.

This layer is reference-only. It does not require Azure credentials, create resource groups, call Azure SDKs, run Azure CLI deployment commands, run Terraform apply, execute Bicep deployments, publish Power BI content, or validate against a live subscription.
