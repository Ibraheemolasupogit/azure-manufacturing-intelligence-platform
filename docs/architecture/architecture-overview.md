# Architecture Overview

The platform is designed as a local-first reference implementation of an Azure manufacturing analytics estate. Milestones 1 through 3 create the repository foundation, deterministic synthetic raw data, governed local ingestion, validation, quarantine, lineage, and CI workflow.

## Conceptual flow

Synthetic manufacturing sources feed the raw zone under `data/raw/`. Milestone 3 ingestion validates those sources and separates accepted records from quarantined records under `data/interim/`. Governed local data zones will later support transformation, analytics, feature engineering, ML workflows, monitoring, GenAI assistance, and reporting.

The planned domains are production telemetry, inventory, sales orders, quality checks, equipment health, warehouse movements, and supplier performance. Future pipelines will support both batch and streaming paths.

## Governance and observability

Milestone 3 produces lineage metadata, data-quality evidence, and run manifests containing run ID, pipeline name, configuration hash, input and output paths, hashes, row counts, validation status, software version, and synthetic-data classification. Later milestones should extend this pattern for analytical outputs and model artifacts.

## Implementation boundary

Milestone 3 does not run analytics, train models, generate dashboards, or deploy Azure resources.
