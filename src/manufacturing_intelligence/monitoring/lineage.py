"""Lineage records for monitoring outputs."""

from __future__ import annotations

from typing import Any


def lineage_record(
    *,
    monitoring_run_id: str,
    source_inputs: dict[str, Any],
    target: dict[str, Any],
    transformation_name: str,
    configuration_hash: str,
) -> dict[str, Any]:
    """Build a deterministic local monitoring lineage record."""
    return {
        "monitoring_run_id": monitoring_run_id,
        "source_inputs": source_inputs,
        "target_path": target["path"],
        "target_sha256": target["sha256"],
        "target_row_count": target.get("row_count"),
        "transformation_name": transformation_name,
        "configuration_hash": configuration_hash,
        "validation_status": "success",
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "purview_registration_status": "not_registered_reference_only",
    }
