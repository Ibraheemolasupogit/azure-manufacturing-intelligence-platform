"""Deterministic accepted and quarantine serialization."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from manufacturing_intelligence.data_generation.schemas import DatasetSchema
from manufacturing_intelligence.ingestion.manifest import file_evidence
from manufacturing_intelligence.validation.quarantine import quarantine_payload
from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


def write_accepted(
    output_dir: Path,
    schema: DatasetSchema,
    records: tuple[LoadedRecord, ...],
) -> tuple[Path, int]:
    """Write accepted records in their original source format."""
    path = output_dir / "accepted" / schema.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if schema.file_format == "jsonl":
        with path.open("w", encoding="utf-8") as handle:
            for loaded in records:
                handle.write(json.dumps(loaded.record, sort_keys=True))
                handle.write("\n")
    else:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(schema.fields), lineterminator="\n")
            writer.writeheader()
            writer.writerows(loaded.record for loaded in records)
    return path, len(records)


def write_quarantine(
    output_dir: Path,
    schema: DatasetSchema,
    quarantined: tuple[tuple[LoadedRecord, tuple[ValidationIssue, ...]], ...],
    ingestion_run_id: str,
) -> tuple[Path, int]:
    """Write structured quarantine JSONL for every dataset."""
    path = output_dir / "quarantine" / f"{schema.dataset_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for loaded, issues in quarantined:
            payload = quarantine_payload(loaded, issues, ingestion_run_id)
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")
    return path, len(quarantined)


def evidence_for(path: Path, row_count: int) -> dict[str, Any]:
    """Return serializable file evidence."""
    return file_evidence(path, row_count).to_dict()
