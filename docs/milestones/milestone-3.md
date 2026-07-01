# Milestone 3 - Governed Ingestion And Data Validation

## Objective

Ingest the deterministic synthetic raw datasets from Milestone 2 into governed local interim zones with reproducible validation, quarantine, metadata, lineage, and quality-report evidence.

## Scope delivered

- Local ingestion configuration in `configs/ingestion.yaml`.
- CI ingestion configuration in `configs/ingestion_ci.yaml`.
- CLI entry point via `python3 -m manufacturing_intelligence.ingestion`.
- Make targets for `make ingest`, `make ingest-ci`, and `make validate-ingestion`.
- Source discovery and generation-manifest verification.
- Schema, type, category, timestamp, duplicate, domain-invariant, and cross-dataset relationship validation.
- Accepted outputs under `data/interim/accepted/`.
- Quarantine outputs under `data/interim/quarantine/`.
- Metadata under `data/interim/_metadata/`.
- Markdown quality report at `reports/data_quality_report.md`.
- Existing-run validation without regenerating outputs.
- Unit tests for valid runs, deterministic outputs, config changes, missing files, metadata checks, hash mismatch, invalid JSON, invalid CSV headers, permissive quarantine, duplicate handling, strict-mode failure, output tampering, overwrite behavior, raw immutability, and CLI execution outside the repository root.

## Scope boundaries

Milestone 3 does not implement forecasting, optimisation, anomaly-detection models, predictive-maintenance models, dashboards, GenAI, Azure SDK integration, databases, orchestration services, or cloud deployment.

## Acceptance checklist

- [x] Raw inputs are preserved unchanged.
- [x] Accepted and quarantine zones are generated locally.
- [x] Invalid records are quarantined with structured reasons in permissive mode.
- [x] Strict mode fails on any quarantined record.
- [x] Source hashes and file sizes are verified from Milestone 2 metadata.
- [x] Existing-run validation is available.
- [x] Data-quality summaries are emitted.
- [x] Lineage records link source files to accepted and quarantine outputs.
- [x] CLI and Makefile entry points are available.
- [x] CI runs the ingestion smoke workflow.
- [x] Tests and documentation cover Milestone 3 behavior.

## Synthetic-data confirmation

All data remains synthetic and must not represent real customers, suppliers, employees, plants, products, or commercial operations.
