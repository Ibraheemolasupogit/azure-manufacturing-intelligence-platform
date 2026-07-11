"""Validation-only checks for dashboard outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.dashboard.config import load_dashboard_config
from manufacturing_intelligence.dashboard.manifest import dashboard_run_id
from manufacturing_intelligence.dashboard.semantic_model import PRIMARY_KEYS

REQUIRED_OUTPUTS = {
    "dim_date",
    "dim_product",
    "dim_plant",
    "dim_production_line",
    "dim_machine",
    "dim_warehouse",
    "dim_supplier",
    "dim_metric",
    "dim_risk_level",
    "dim_dashboard_page",
    "fact_production_kpis",
    "fact_demand_forecast",
    "fact_inventory_risk",
    "fact_quality_alerts",
    "fact_maintenance_alerts",
    "fact_platform_health",
    "fact_operations_assistant_narratives",
    "executive_scorecard",
    "metric_catalogue",
    "semantic_model",
    "dashboard_page_specs",
    "visual_specifications",
    "dashboard_diagnostics",
    "dashboard_output_report",
    "semantic_model_summary",
    "dashboard_index",
    "powerbi_ready_outputs",
    "semantic_model_notes",
}


def validate_existing_run(
    config_path: Path | None = None, output_directory: Path | None = None
) -> None:
    config = load_dashboard_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.dashboard.output_directory
    )
    manifest_path = output_dir / "dashboard-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("DASHBOARD_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("DASHBOARD_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    outputs = manifest.get("output_files")
    if not isinstance(outputs, dict):
        raise DataContractError("DASHBOARD_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"DASHBOARD_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        _verify_file(output_dir, evidence)
    _validate_tables(output_dir, outputs)
    semantic = _read_json(_resolve_output_path(output_dir, outputs["semantic_model"]["path"]))
    pages = _read_json_list(
        _resolve_output_path(output_dir, outputs["dashboard_page_specs"]["path"])
    )
    visuals = _read_json_list(
        _resolve_output_path(output_dir, outputs["visual_specifications"]["path"])
    )
    _validate_semantic_model(output_dir, outputs, semantic)
    _validate_pages(pages, outputs)
    _validate_visuals(visuals, pages)
    _validate_lineage(lineage_path, outputs)
    _validate_upstream_hashes(config, manifest)
    expected = dashboard_run_id(config, manifest["input_hashes"])
    if manifest["dashboard_run_id"] != expected:
        raise DataContractError("DASHBOARD_RUN_ID_MISMATCH")
    if (
        manifest.get("power_bi_deployment") is not False
        or manifest.get("azure_deployment") is not False
    ):
        raise DataContractError("DASHBOARD_DEPLOYMENT_FLAG_INVALID")


def _validate_tables(output_dir: Path, outputs: dict[str, Any]) -> None:
    for table, keys in PRIMARY_KEYS.items():
        frame = pd.read_csv(_resolve_output_path(output_dir, outputs[table]["path"]))
        if frame.empty:
            raise DataContractError(f"DASHBOARD_TABLE_EMPTY: {table}")
        if keys and frame.duplicated(keys).any():
            raise DataContractError(f"DASHBOARD_PRIMARY_KEY_DUPLICATE: {table}")
    metric = pd.read_csv(_resolve_output_path(output_dir, outputs["metric_catalogue"]["path"]))
    required = {"production_output", "demand_forecast", "inventory_score", "quality_alert"}
    if not required <= set(metric["metric_name"]):
        raise DataContractError("DASHBOARD_METRIC_CATALOGUE_INCOMPLETE")
    if metric["calculation_formula"].isna().any():
        raise DataContractError("DASHBOARD_METRIC_FORMULA_MISSING")


def _validate_semantic_model(
    output_dir: Path,
    outputs: dict[str, Any],
    semantic: dict[str, Any],
) -> None:
    output_names = set(outputs)
    for table in semantic["tables"]:
        if table["name"] not in output_names:
            raise DataContractError("DASHBOARD_SEMANTIC_TABLE_INVALID")
    for relationship in semantic["relationships"]:
        left = pd.read_csv(
            _resolve_output_path(output_dir, outputs[relationship["from_table"]]["path"])
        )
        right = pd.read_csv(
            _resolve_output_path(output_dir, outputs[relationship["to_table"]]["path"])
        )
        if (
            relationship["from_column"] not in left.columns
            or relationship["to_column"] not in right.columns
        ):
            raise DataContractError("DASHBOARD_SEMANTIC_RELATIONSHIP_INVALID")


def _validate_pages(pages: list[dict[str, Any]], outputs: dict[str, Any]) -> None:
    page_ids = {page["page_id"] for page in pages}
    required_pages = {
        "executive_overview",
        "production_operations",
        "demand_forecasting",
        "inventory_and_supply_chain",
        "quality_analytics",
        "predictive_maintenance",
        "platform_monitoring",
        "operations_assistant",
    }
    if page_ids != required_pages:
        raise DataContractError("DASHBOARD_PAGE_SPECS_INCOMPLETE")
    for page in pages:
        if "synthetic" not in page["synthetic_data_disclaimer"].lower():
            raise DataContractError("DASHBOARD_PAGE_DISCLAIMER_MISSING")
        if not set(page["source_tables"]) <= set(outputs):
            raise DataContractError("DASHBOARD_PAGE_SOURCE_TABLE_INVALID")


def _validate_visuals(visuals: list[dict[str, Any]], pages: list[dict[str, Any]]) -> None:
    page_ids = {page["page_id"] for page in pages}
    if not visuals:
        raise DataContractError("DASHBOARD_VISUAL_SPECS_MISSING")
    if any(visual["page_id"] not in page_ids for visual in visuals):
        raise DataContractError("DASHBOARD_VISUAL_PAGE_INVALID")


def _validate_lineage(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = _read_json_list(lineage_path)
    targets = {item["path"] for item in outputs.values()}
    lineage_targets = {item["target_path"] for item in lineage}
    if not targets <= lineage_targets:
        raise DataContractError("DASHBOARD_LINEAGE_TARGETS_MISSING")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    for field, expected in manifest["input_hashes"].items():
        if sha256_file(getattr(config.inputs, field)) != expected:
            raise DataContractError(f"DASHBOARD_UPSTREAM_HASH_MISMATCH: {field}")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, evidence["path"])
    if not path.is_file():
        raise DataContractError(f"DASHBOARD_OUTPUT_MISSING: {evidence['path']}")
    if path.stat().st_size != int(evidence["file_size_bytes"]):
        raise DataContractError(f"DASHBOARD_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if sha256_file(path) != evidence["sha256"]:
        raise DataContractError(f"DASHBOARD_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if rows != int(evidence["row_count"]):
            raise DataContractError(f"DASHBOARD_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


def _resolve_output_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise DataContractError("DASHBOARD_ABSOLUTE_OUTPUT_PATH")
    candidate = resolve_project_path(path_value)
    if candidate.is_file():
        return candidate
    return output_dir.parent / path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError("DASHBOARD_JSON_INVALID")
    return payload


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise DataContractError("DASHBOARD_JSON_LIST_INVALID")
    return payload
