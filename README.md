# Azure Manufacturing Intelligence Platform

## Executive overview

This repository is the foundation for a local-first, Azure-mapped manufacturing operations and supply-chain intelligence platform. It is designed to show how an enterprise manufacturer could ingest synthetic factory and supply-chain data, govern it, validate it, model it, and expose analytics-ready outputs without requiring live cloud resources during development.

## Business problem

Manufacturing organisations often make decisions from fragmented production, inventory, quality, equipment, warehouse, supplier, and demand data. That fragmentation makes it harder to identify constraints, anticipate shortages, manage supplier risk, protect quality, and prioritise operational interventions.

## Platform objectives

- Build deterministic synthetic data pipelines for manufacturing and supply-chain domains.
- Establish governed local data zones that map conceptually to Azure services.
- Support future forecasting, inventory intelligence, quality analytics, predictive maintenance, monitoring, GenAI assistance, and reporting.
- Keep every milestone reproducible, testable, auditable, and CI-ready.

## Core capabilities

Planned capabilities include production telemetry ingestion, schema validation, demand forecasting, inventory-risk scoring, supplier-performance analytics, quality anomaly detection, predictive maintenance, operational monitoring, scenario analysis, GenAI-assisted recommendations, and Power BI-ready extracts. Milestones 1 and 2 implement the repository foundation and deterministic synthetic raw datasets only.

## Intended users

The platform is intended for plant managers, production supervisors, maintenance engineers, quality managers, supply-chain planners, inventory analysts, procurement teams, operations analysts, data scientists, ML engineers, and executive leadership.

Example decisions include whether production is meeting plan, where throughput is constrained, which products may face shortages, which suppliers introduce operational risk, which batches show quality deterioration, and which machines should be inspected.

## Data domains

Synthetic raw sources now cover production operations, inventory, sales and demand, quality checks, equipment health, warehouse movements, and supplier performance. All data is synthetic and must not represent real individuals, employees, customers, suppliers, or commercially sensitive operations.

## Local-first approach

Local directories, Python modules, configuration files, tests, and run manifests will emulate the responsibilities of a cloud analytics estate. This keeps development affordable, deterministic, offline-friendly, and easy to demonstrate in interviews while preserving a clear path to Azure implementation.

## Azure reference mapping

| Local capability | Azure reference service |
| --- | --- |
| JSONL and CSV event simulation | Azure Event Hubs and Azure IoT Hub |
| Local raw-data directories | Azure Data Lake Storage Gen2 |
| Python streaming simulator | Azure Stream Analytics |
| Local telemetry analysis | Azure Data Explorer |
| Local analytical outputs | Azure Synapse Analytics |
| Local model training | Azure Machine Learning |
| Local GenAI adapter | Azure AI Foundry |
| Local dashboard extracts | Microsoft Power BI |
| Local lineage metadata | Microsoft Purview |
| Local structured logs and metrics | Azure Monitor and Application Insights |
| GitHub Actions | Azure DevOps Pipelines or GitHub Actions for Azure |

These mappings are architectural references only. No Azure resource IDs, endpoints, credentials, deployments, screenshots, or cloud success claims are created by Milestone 1.

## High-level architecture

```mermaid
flowchart TD
    sources["Synthetic Manufacturing Sources"] --> ingestion["Ingestion and Event Simulation"]
    ingestion --> validation["Validation and Data-Quality Controls"]
    validation --> zones["Governed Local Data Zones"]
    zones --> analytics["Analytics and Feature Engineering"]
    analytics --> intelligence["Forecasting / Inventory / Quality / Maintenance"]
    intelligence --> monitoring["Monitoring and GenAI Assistance"]
    monitoring --> outputs["Power BI-Ready Outputs and Executive Reports"]
```

See [diagrams/high-level-platform-architecture.mmd](diagrams/high-level-platform-architecture.mmd) and [docs/architecture/architecture-overview.md](docs/architecture/architecture-overview.md) for more detail.

## Repository structure

```text
configs/       Base and environment configuration
data/          Local raw, interim, and processed data zones
diagrams/      Mermaid architecture diagrams
docs/          Architecture, business, engineering, milestone, and roadmap docs
outputs/       Future analytics-ready outputs
reports/       Future generated narrative reports
scripts/       Repository validation utilities
src/           Python package scaffold and shared utilities
tests/         Unit tests and deterministic fixture guidance
```

## Milestone roadmap

| Milestone | Status |
| --- | --- |
| Milestone 1 - Repository foundation and architecture | Complete |
| Milestone 2 - Deterministic synthetic manufacturing datasets | Complete |
| Milestone 3 onward | Planned |

Full roadmap: [docs/roadmap.md](docs/roadmap.md).

## Current implementation status

Implemented through Milestone 2:

- Repository scaffold and package boundaries.
- Configuration loading with base, local, CI, and environment-variable overrides.
- Project-root path resolution independent of current working directory.
- Standard-library structured logging foundation.
- Exception hierarchy for future pipelines.
- Documentation, diagrams, tests, CI workflow, and structure validation.
- Deterministic synthetic data generation for seven raw manufacturing and supply-chain domains.
- Schema metadata, generation manifest, and generation summary for the synthetic raw files.
- Separate local and CI synthetic-data profiles.
- Existing-run validation for generated data without regenerating it.

Not implemented yet: ingestion pipelines, validation rules, accepted/quarantined data zones, forecasting, optimisation, anomaly detection, predictive maintenance, GenAI, dashboards, or live Azure integration.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

The package supports Python 3.11 or newer.

## Quality commands

```bash
make structure-check
make format
make lint
make type-check
make test
make generate-data
make generate-data-ci
make validate-generation
make quality
```

`make generate-data` regenerates the intentionally tracked local sample under `data/raw/` using `configs/synthetic_data.yaml` and an explicit overwrite flag. Direct CLI generation refuses to overwrite existing managed files unless `--overwrite` is passed. `make generate-data-ci` uses the smaller `configs/synthetic_data_ci.yaml` profile and writes to ignored `.generated/ci/raw/`. `make validate-generation` validates the existing `data/raw/` run without regenerating it.

## Testing approach

Current tests verify configuration loading, environment overrides, path resolution, repository structure, package imports, project metadata, Azure reference-only safety, deterministic synthetic generation, schema headers, row counts, manifests, and cross-dataset entity consistency. Later milestones will add governed schema tests, data-quality tests, pipeline integration tests, model evaluation tests, and regression tests.

## Security, privacy, and synthetic data

This repository is synthetic-data only. Do not commit credentials, `.env` files, real employee data, customer data, supplier data, commercial production details, or private operational records. Future cloud deployments should use least privilege, managed identities, Key Vault, immutable raw-data conventions, lineage metadata, retention principles, and accepted-versus-quarantined data separation.

## Generated-data tracking policy

The small deterministic `data/raw/` sample is intentionally tracked as portfolio evidence. Larger, ad hoc, CI, and temporary generated runs must stay out of Git; `.generated/` is ignored for that purpose. The generation timestamp is configured, not read from wall-clock time, so controlled runs remain byte-for-byte reproducible.

## Known limitations

Milestone 2 generates synthetic raw source files only. It does not ingest data into governed zones, produce analytical outputs, deploy cloud infrastructure, train models, connect to Azure services, or fabricate operational results.

## Planned portfolio outputs

Future milestones are expected to produce documented, reproducible outputs such as `outputs/demand_forecast.csv`, `outputs/inventory_scores.csv`, `outputs/quality_alerts.csv`, `outputs/maintenance_predictions.json`, `outputs/production_kpis.csv`, `outputs/supplier_risk_scores.csv`, Power BI fact extracts, and narrative reports under `reports/`.

## Disclaimer

Azure services are represented through architecture mappings and local adapters unless a later milestone explicitly implements deployment guidance. Milestone 1 does not deploy, call, or require Azure resources.
