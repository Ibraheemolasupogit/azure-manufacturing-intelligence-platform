"""Quality lineage helpers."""

from __future__ import annotations

from typing import Any


def lineage_record(
    *,
    quality_run_id: str,
    upstream_ingestion_run_id: str,
    source_inputs: dict[str, dict[str, Any]],
    target: dict[str, Any],
    transformation_name: str,
    configuration_hash: str,
    rule_or_model: str = "",
) -> dict[str, Any]:
    """Build a deterministic local lineage record."""
    return {
        "quality_run_id": quality_run_id,
        "upstream_ingestion_run_id": upstream_ingestion_run_id,
        "source_inputs": source_inputs,
        "target_path": target["path"],
        "target_sha256": target["sha256"],
        "target_row_count": target["row_count"],
        "transformation_name": transformation_name,
        "rule_or_model": rule_or_model,
        "transformation_type": "local governed quality analytics and anomaly detection",
        "configuration_hash": configuration_hash,
        "validation_status": "success",
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "azure_mapping": "Microsoft Purview lineage responsibility, not registered",
    }
