# Lineage And Manifests

Milestone 3 produces local lineage evidence that mirrors the responsibilities of a governed lakehouse without using cloud services.

## Ingestion manifest

`data/interim/_metadata/ingestion-manifest.json` records:

- ingestion run ID;
- pipeline name and version;
- execution mode;
- Git commit;
- configuration path and hash;
- source generation manifest and schema registry hashes;
- accepted and quarantine output evidence;
- source dataset evidence;
- validation status and issue counts;
- synthetic-data classification.

## Lineage records

`data/interim/_metadata/lineage-records.json` contains one record per dataset. Each record links source evidence to accepted and quarantine outputs with row counts, SHA-256 hashes, schema version, configuration hash, validation status, and transformation type.

Generated artifact paths are output-relative where possible so local runs remain deterministic across machines and temporary directories.

## Existing-run validation

`make validate-ingestion` checks an existing interim run without regenerating outputs. It verifies required metadata files, accepted files, quarantine files, file sizes, hashes, and machine-specific absolute path leakage.
