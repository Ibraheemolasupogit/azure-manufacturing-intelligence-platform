# Governed Ingestion Design

Milestone 3 adds a local governed ingestion layer for the synthetic raw files produced in Milestone 2. The pipeline reads the configured raw directory, verifies source metadata, validates each dataset, writes accepted records to `data/interim/accepted/`, writes rejected records to `data/interim/quarantine/`, and emits run evidence under `data/interim/_metadata/`.

## Inputs

- `configs/ingestion.yaml` for the tracked local sample.
- `configs/ingestion_ci.yaml` for the ignored CI smoke run.
- `data/raw/generation_manifest.json` for source hashes, row counts, and generation lineage.
- `data/raw/schema_metadata.json` for schema definitions, categories, primary keys, relationship references, and invariants.
- Seven synthetic source datasets under `data/raw/`.

## Outputs

- Accepted records preserve the source format and field order.
- Quarantine files are JSONL so every rejected record can carry its original record, rule codes, source row number, and issue details.
- Metadata files include `ingestion-manifest.json`, `validation-summary.json`, `quarantine-summary.json`, `data-quality-report.json`, and `lineage-records.json`.
- `reports/data_quality_report.md` provides a compact human-readable run summary.

## Local-first boundaries

The implementation uses local files and Python only. It does not create accepted or quarantined cloud zones, call Azure services, use databases, run orchestration services, train models, or produce analytics outputs.

## Immutability

Raw files are read-only inputs for ingestion. The pipeline verifies Milestone 2 size and SHA-256 evidence before loading source datasets, and tests confirm tracked `data/raw/` files are unchanged by ingestion.
