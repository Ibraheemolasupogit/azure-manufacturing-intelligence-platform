# Quarantine Design

Quarantine files make validation failures auditable while preserving the original source record for later debugging.

## File layout

Each dataset has a matching JSONL file under `data/interim/quarantine/`. Empty quarantine files are intentionally written in successful runs so downstream checks can prove every dataset was evaluated.

## Record shape

Each quarantine entry includes:

- ingestion run ID;
- dataset name;
- source path and source row number;
- source record ID;
- ordered rule codes;
- structured issue details;
- the original raw record exactly as loaded.

## Deterministic handling

When duplicate primary keys are found, the first source record wins and later duplicates are quarantined. Rule codes are sorted deterministically for stable output. In permissive mode, accepted and quarantined files are written when the configured quarantine-rate threshold is not exceeded.

## Strict mode

Strict mode fails the run when any record is quarantined. This protects the tracked local sample from silently accepting invalid data while still allowing tests and future examples to exercise permissive quarantine behavior.
