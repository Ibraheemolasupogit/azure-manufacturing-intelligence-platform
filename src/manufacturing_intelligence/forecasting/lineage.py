"""Forecast lineage helpers."""

from __future__ import annotations

from typing import Any


def lineage_record(
    *,
    forecast_run_id: str,
    upstream_ingestion_run_id: str,
    source: dict[str, Any],
    target: dict[str, Any],
    transformation_name: str,
    configuration_hash: str,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Build one forecast lineage record."""
    return {
        "forecast_run_id": forecast_run_id,
        "upstream_ingestion_run_id": upstream_ingestion_run_id,
        "source": source,
        "target": target,
        "transformation_name": transformation_name,
        "configuration_hash": configuration_hash,
        "model_name": model_name,
        "validation_status": "success",
        "synthetic_data_classification": "synthetic_portfolio_sample",
    }
