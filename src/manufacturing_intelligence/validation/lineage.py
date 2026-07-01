"""Lineage metadata helpers."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.ingestion.manifest import FileEvidence


def lineage_record(
    *,
    ingestion_run_id: str,
    dataset: str,
    schema_version: str,
    source: FileEvidence,
    accepted: FileEvidence,
    quarantine: FileEvidence,
    configuration_hash: str,
    validation_status: str,
) -> dict[str, Any]:
    """Build one local lineage record."""
    return {
        "ingestion_run_id": ingestion_run_id,
        "dataset": dataset,
        "schema_version": schema_version,
        "source_relative_path": source.path,
        "source_row_count": source.row_count,
        "source_file_size_bytes": source.file_size_bytes,
        "source_sha256": source.sha256,
        "accepted_relative_path": accepted.path,
        "accepted_row_count": accepted.row_count,
        "accepted_file_size_bytes": accepted.file_size_bytes,
        "accepted_sha256": accepted.sha256,
        "quarantine_relative_path": quarantine.path,
        "quarantine_row_count": quarantine.row_count,
        "quarantine_file_size_bytes": quarantine.file_size_bytes,
        "quarantine_sha256": quarantine.sha256,
        "transformation_type": "local governed ingestion and validation",
        "configuration_hash": configuration_hash,
        "validation_status": validation_status,
        "synthetic_data_classification": "synthetic_portfolio_sample",
    }
