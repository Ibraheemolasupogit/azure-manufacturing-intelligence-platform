"""Governed dashboard input loading and verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.dashboard.config import DashboardConfig, DashboardInputs
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class DashboardEvidence:
    frames: dict[str, pd.DataFrame]
    json_inputs: dict[str, Any]
    manifests: dict[str, dict[str, Any]]
    input_hashes: dict[str, str]
    warnings: list[str]


def load_dashboard_evidence(config: DashboardConfig) -> DashboardEvidence:
    """Load governed inputs after manifest and lineage validation."""
    _verify_required_files(config)
    manifests = {
        "ingestion": _read_json(config.inputs.ingestion_manifest_path),
        "forecasting": _read_json(config.inputs.forecast_manifest_path),
        "inventory": _read_json(config.inputs.inventory_manifest_path),
        "quality": _read_json(config.inputs.quality_manifest_path),
        "maintenance": _read_json(config.inputs.maintenance_manifest_path),
        "monitoring": _read_json(config.inputs.monitoring_manifest_path),
        "genai": _read_json(config.inputs.genai_manifest_path),
    }
    _verify_manifests(manifests)
    for path in [
        config.inputs.ingestion_lineage_path,
        config.inputs.forecast_lineage_path,
        config.inputs.inventory_lineage_path,
        config.inputs.quality_lineage_path,
        config.inputs.maintenance_lineage_path,
        config.inputs.monitoring_lineage_path,
        config.inputs.genai_lineage_path,
    ]:
        if not _read_json_list(path):
            raise DataContractError(f"DASHBOARD_LINEAGE_EMPTY: {relative_path(path)}")
    frames = {
        "production_events": pd.read_json(config.inputs.production_events_path, lines=True),
        "sales_orders": pd.read_csv(config.inputs.sales_orders_path),
        "inventory_levels": pd.read_csv(config.inputs.inventory_levels_path),
        "supplier_performance": pd.read_csv(config.inputs.supplier_performance_path),
        "quality_checks": pd.read_csv(config.inputs.quality_checks_path),
        "equipment_health": pd.read_json(config.inputs.equipment_health_path, lines=True),
        "demand_forecast": pd.read_csv(config.inputs.demand_forecast_path),
        "inventory_scores": pd.read_csv(config.inputs.inventory_scores_path),
        "quality_alerts": pd.read_csv(config.inputs.quality_alerts_path),
        "maintenance_alerts": pd.read_csv(config.inputs.maintenance_alerts_path),
    }
    json_inputs = {
        "maintenance_predictions": _read_json(config.inputs.maintenance_predictions_path),
        "platform_health_summary": _read_json(config.inputs.platform_health_summary_path),
        "genai_responses": _read_json_list(config.inputs.genai_responses_path),
        "executive_brief": config.inputs.executive_brief_path.read_text(encoding="utf-8"),
        "supply_chain_summary": config.inputs.supply_chain_summary_path.read_text(encoding="utf-8"),
        "operations_report": config.inputs.operations_report_path.read_text(encoding="utf-8"),
    }
    _verify_manifest_hashes(config, manifests)
    return DashboardEvidence(
        frames=frames,
        json_inputs=json_inputs,
        manifests=manifests,
        input_hashes={
            field: sha256_file(getattr(config.inputs, field)) for field in INPUT_HASH_FIELDS
        },
        warnings=[],
    )


def verify_upstream_unchanged(config: DashboardConfig, evidence: DashboardEvidence) -> None:
    for field, expected in evidence.input_hashes.items():
        if sha256_file(getattr(config.inputs, field)) != expected:
            raise DataContractError(f"DASHBOARD_UPSTREAM_CHANGED: {field}")


def _verify_required_files(config: DashboardConfig) -> None:
    for field in DashboardInputs.__dataclass_fields__:
        path = getattr(config.inputs, field)
        if not path.is_file():
            raise DataContractError(f"DASHBOARD_REQUIRED_INPUT_MISSING: {relative_path(path)}")


def _verify_manifests(manifests: dict[str, dict[str, Any]]) -> None:
    for domain, manifest in manifests.items():
        if manifest.get("validation_status") != "success":
            raise DataContractError(f"DASHBOARD_MANIFEST_NOT_SUCCESSFUL: {domain}")
        if domain != "genai" and manifest.get("synthetic_data_classification") != (
            "synthetic_portfolio_sample"
        ):
            raise DataContractError(f"DASHBOARD_SYNTHETIC_CLASSIFICATION_MISSING: {domain}")
        if domain == "genai" and manifest.get("external_model_called") is not False:
            raise DataContractError("DASHBOARD_GENAI_EXTERNAL_CALL_INVALID")


def _verify_manifest_hashes(
    config: DashboardConfig,
    manifests: dict[str, dict[str, Any]],
) -> None:
    ingestion = manifests["ingestion"]
    for dataset, path in {
        "production_events": config.inputs.production_events_path,
        "sales_orders": config.inputs.sales_orders_path,
        "inventory_levels": config.inputs.inventory_levels_path,
        "supplier_performance": config.inputs.supplier_performance_path,
        "quality_checks": config.inputs.quality_checks_path,
        "equipment_health": config.inputs.equipment_health_path,
    }.items():
        expected = ingestion["accepted_outputs"][dataset]
        if sha256_file(path) != expected["sha256"]:
            raise DataContractError(f"DASHBOARD_INGESTION_HASH_MISMATCH: {dataset}")
        if path.suffix == ".csv":
            rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
            if rows != int(expected["row_count"]):
                raise DataContractError(f"DASHBOARD_INGESTION_ROW_COUNT_MISMATCH: {dataset}")
    _verify_output_hash(config.inputs.demand_forecast_path, manifests["forecasting"], "forecast")
    _verify_output_hash(config.inputs.inventory_scores_path, manifests["inventory"], "inventory")
    _verify_output_hash(config.inputs.quality_alerts_path, manifests["quality"], "quality")
    _verify_output_hash(
        config.inputs.maintenance_predictions_path, manifests["maintenance"], "maintenance"
    )
    _verify_output_hash(
        config.inputs.platform_health_summary_path, manifests["monitoring"], "monitoring"
    )
    _verify_output_hash(config.inputs.genai_responses_path, manifests["genai"], "genai")


def _verify_output_hash(path: Path, manifest: dict[str, Any], domain: str) -> None:
    outputs = manifest.get("output_files", {})
    for evidence in outputs.values():
        if isinstance(evidence, dict) and evidence.get("path") == relative_path(path):
            if sha256_file(path) != evidence["sha256"]:
                raise DataContractError(f"DASHBOARD_OUTPUT_HASH_MISMATCH: {domain}")
            return
    raise DataContractError(f"DASHBOARD_OUTPUT_NOT_IN_MANIFEST: {relative_path(path)}")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"DASHBOARD_JSON_INVALID: {relative_path(path)}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"DASHBOARD_ABSOLUTE_PATH_IN_INPUT: {relative_path(path)}")
    return payload


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise DataContractError(f"DASHBOARD_JSON_LIST_INVALID: {relative_path(path)}")
    return payload


INPUT_HASH_FIELDS = tuple(DashboardInputs.__dataclass_fields__)
