"""Inventory lineage helpers."""

from __future__ import annotations

from typing import Any


def lineage_record(
    *,
    inventory_run_id: str,
    upstream_ingestion_run_id: str,
    upstream_forecast_run_id: str,
    source_inputs: dict[str, dict[str, Any]],
    target: dict[str, Any],
    transformation_name: str,
    configuration_hash: str,
) -> dict[str, Any]:
    """Build a deterministic local lineage record."""
    return {
        "inventory_run_id": inventory_run_id,
        "upstream_ingestion_run_id": upstream_ingestion_run_id,
        "upstream_forecast_run_id": upstream_forecast_run_id,
        "source_inputs": source_inputs,
        "target_path": target["path"],
        "target_sha256": target["sha256"],
        "target_row_count": target["row_count"],
        "transformation_name": transformation_name,
        "transformation_type": "local governed inventory intelligence and policy scoring",
        "configuration_hash": configuration_hash,
        "validation_status": "success",
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "azure_mapping": "Microsoft Purview lineage responsibility, not registered",
    }
