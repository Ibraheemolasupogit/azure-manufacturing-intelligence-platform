"""Load governed evidence for monitoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.monitoring.config import MonitoringConfig


@dataclass(frozen=True)
class MonitoringEvidence:
    """Loaded monitoring evidence."""

    manifests: dict[str, dict[str, Any]]
    lineages: dict[str, list[dict[str, Any]]]
    frames: dict[str, pd.DataFrame]
    input_hashes: dict[str, str]
    before_hashes: dict[str, str]


def load_monitoring_evidence(config: MonitoringConfig) -> MonitoringEvidence:
    """Load required manifests, lineages, and observed output tables."""
    paths = {
        "generation_manifest": config.inputs.generation_manifest_path,
        "schema_metadata": config.inputs.schema_metadata_path,
        "ingestion_manifest": config.inputs.ingestion_manifest_path,
        "validation_summary": config.inputs.validation_summary_path,
        "data_quality_report": config.inputs.data_quality_report_path,
        "data_quality_markdown": config.inputs.data_quality_markdown_path,
        "forecast_manifest": config.inputs.forecast_manifest_path,
        "inventory_manifest": config.inputs.inventory_manifest_path,
        "quality_manifest": config.inputs.quality_manifest_path,
        "maintenance_manifest": config.inputs.maintenance_manifest_path,
        "demand_forecast": config.inputs.demand_forecast_path,
        "inventory_scores": config.inputs.inventory_scores_path,
        "quality_alerts": config.inputs.quality_alerts_path,
        "maintenance_predictions": config.inputs.maintenance_predictions_path,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise DataContractError(f"Monitoring required evidence is missing: {name}={path}")

    manifests = {
        "generation": _read_json(config.inputs.generation_manifest_path),
        "ingestion": _read_json(config.inputs.ingestion_manifest_path),
        "validation": _read_json(config.inputs.validation_summary_path),
        "data_quality": _read_json(config.inputs.data_quality_report_path),
        "forecasting": _read_json(config.inputs.forecast_manifest_path),
        "inventory": _read_json(config.inputs.inventory_manifest_path),
        "quality": _read_json(config.inputs.quality_manifest_path),
        "maintenance": _read_json(config.inputs.maintenance_manifest_path),
    }
    lineages = {
        "ingestion": _read_lineage(config.inputs.ingestion_lineage_path),
        "forecasting": _read_lineage(config.inputs.forecast_lineage_path),
        "inventory": _read_lineage(config.inputs.inventory_lineage_path),
        "quality": _read_lineage(config.inputs.quality_lineage_path),
        "maintenance": _read_lineage(config.inputs.maintenance_lineage_path),
    }
    frames = {
        "demand_forecast": pd.read_csv(config.inputs.demand_forecast_path),
        "inventory_scores": pd.read_csv(config.inputs.inventory_scores_path),
        "quality_alerts": pd.read_csv(config.inputs.quality_alerts_path),
        "maintenance_alerts": pd.read_csv(
            _output_path(manifests["maintenance"], "maintenance_alerts")
        ),
    }
    _validate_statuses(manifests)
    input_hashes = {name: sha256_file(path) for name, path in paths.items()}
    input_hashes.update(
        {
            "ingestion_lineage": sha256_file(config.inputs.ingestion_lineage_path),
            "forecast_lineage": sha256_file(config.inputs.forecast_lineage_path),
            "inventory_lineage": sha256_file(config.inputs.inventory_lineage_path),
            "quality_lineage": sha256_file(config.inputs.quality_lineage_path),
            "maintenance_lineage": sha256_file(config.inputs.maintenance_lineage_path),
        }
    )
    return MonitoringEvidence(
        manifests=manifests,
        lineages=lineages,
        frames=frames,
        input_hashes=input_hashes,
        before_hashes=input_hashes,
    )


def verify_upstream_unchanged(config: MonitoringConfig, evidence: MonitoringEvidence) -> None:
    """Verify monitored evidence was not modified during the run."""
    current = load_monitoring_evidence(config).input_hashes
    if current != evidence.before_hashes:
        raise DataContractError("Monitored upstream evidence changed during monitoring run")


def _validate_statuses(manifests: dict[str, dict[str, Any]]) -> None:
    if manifests["generation"].get("status") != "success":
        raise DataContractError("Generation manifest is not successful")
    for domain in ("ingestion", "validation", "forecasting", "inventory", "quality", "maintenance"):
        if manifests[domain].get("validation_status") != "success":
            raise DataContractError(f"{domain} validation status is not successful")
    if not manifests["generation"].get("synthetic_data_only"):
        raise DataContractError("Generation manifest does not confirm synthetic data")
    for domain in ("ingestion", "forecasting", "inventory", "quality", "maintenance"):
        if manifests[domain].get("synthetic_data_classification") != "synthetic_portfolio_sample":
            raise DataContractError(f"{domain} synthetic data classification missing")


def _output_path(manifest: dict[str, Any], output_name: str) -> Path:
    entry = manifest.get("output_files", {}).get(output_name)
    if not isinstance(entry, dict):
        raise DataContractError(f"Manifest missing output file entry: {output_name}")
    return resolve_project_path(str(entry["path"]))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"Monitoring evidence must be a JSON object: {path}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"Monitoring evidence contains machine-specific paths: {path}")
    return payload


def _read_lineage(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise DataContractError(f"Monitoring lineage must be a non-empty list: {path}")
    return [item for item in payload if isinstance(item, dict)]
