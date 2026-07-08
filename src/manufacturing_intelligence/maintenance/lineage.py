"""Lineage records for maintenance analytics."""

from __future__ import annotations

from typing import Any


def lineage_record(
    *,
    maintenance_run_id: str,
    upstream_ingestion_run_id: str,
    upstream_quality_run_id: str | None,
    source_inputs: dict[str, Any],
    target: dict[str, Any],
    transformation_name: str,
    configuration_hash: str,
    rule_or_model: str,
) -> dict[str, Any]:
    """Build a deterministic lineage record."""
    return {
        "maintenance_run_id": maintenance_run_id,
        "upstream_ingestion_run_id": upstream_ingestion_run_id,
        "upstream_quality_run_id": upstream_quality_run_id,
        "source_inputs": source_inputs,
        "target_path": target["path"],
        "target_sha256": target["sha256"],
        "target_row_count": target.get("row_count"),
        "transformation_name": transformation_name,
        "configuration_hash": configuration_hash,
        "rule_or_model": rule_or_model,
        "validation_status": "success",
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "purview_registration_status": "not_registered_reference_only",
    }
