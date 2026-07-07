"""Existing inventory-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.inventory.config import (
    SUPPORTED_SCENARIOS,
    load_inventory_config,
)
from manufacturing_intelligence.inventory.manifest import inventory_run_id, manifest_hash

REQUIRED_OUTPUTS = {
    "warehouse_demand_forecast",
    "supplier_risk_metrics",
    "inventory_policy_inputs",
    "inventory_position",
    "inventory_scores",
    "portfolio_inventory_scores",
    "reorder_recommendations",
    "scenario_results",
    "inventory_summary",
    "inventory_diagnostics",
}

RISK_COLUMNS = {
    "stockout_risk_score",
    "excess_risk_score",
    "supplier_risk_score",
    "expiry_risk_score",
    "working_capital_risk_score",
    "overall_priority_score",
}

NON_NEGATIVE_COLUMNS = {
    "on_hand_quantity",
    "reserved_quantity",
    "available_quantity",
    "inbound_quantity",
    "outbound_quantity",
    "forecast_demand",
    "average_daily_demand",
    "demand_standard_deviation",
    "safety_stock",
    "reorder_point",
    "unconstrained_reorder_quantity",
    "recommended_reorder_quantity",
    "projected_shortage_quantity",
    "projected_excess_quantity",
    "working_capital_exposure",
}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing inventory run without rescoring."""
    config = load_inventory_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.inventory.output_directory
    )
    manifest_path = output_dir / "inventory-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("INVENTORY_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("INVENTORY_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files", {})
    if not isinstance(outputs, dict):
        raise DataContractError("INVENTORY_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"INVENTORY_MANIFEST_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        if isinstance(evidence, dict):
            _verify_file(output_dir, evidence)

    scores = pd.read_csv(_resolve_output_path(output_dir, outputs["inventory_scores"]["path"]))
    recommendations = pd.read_csv(
        _resolve_output_path(output_dir, outputs["reorder_recommendations"]["path"])
    )
    scenarios = pd.read_csv(_resolve_output_path(output_dir, outputs["scenario_results"]["path"]))
    _validate_scores(scores)
    _validate_recommendations(recommendations, config.optimisation.available_budget)
    _validate_scenarios(scenarios)
    _validate_upstream_hashes(config, manifest)
    _validate_run_identity(config, manifest)
    _validate_lineage(lineage_path, outputs)


def _validate_scores(scores: pd.DataFrame) -> None:
    if scores.empty:
        raise DataContractError("INVENTORY_SCORES_EMPTY")
    for column in RISK_COLUMNS:
        if not scores[column].between(0, 100).all():
            raise DataContractError(f"INVENTORY_RISK_SCORE_RANGE: {column}")
    for column in NON_NEGATIVE_COLUMNS:
        if (scores[column] < 0).any():
            raise DataContractError(f"INVENTORY_NEGATIVE_VALUE: {column}")
    if (scores["reorder_point"] < scores["safety_stock"]).any():
        raise DataContractError("INVENTORY_REORDER_POINT_BELOW_SAFETY_STOCK")
    if scores.duplicated(["warehouse_id", "item_id"]).any():
        raise DataContractError("INVENTORY_DUPLICATE_ITEM_LOCATION")
    critical = scores["overall_priority_score"] >= 75
    high = scores["overall_priority_score"].between(50, 75, inclusive="left")
    medium = scores["overall_priority_score"].between(25, 50, inclusive="left")
    low = scores["overall_priority_score"] < 25
    if not (scores.loc[critical, "priority_level"] == "critical").all():
        raise DataContractError("INVENTORY_PRIORITY_LABEL_MISMATCH")
    if not (scores.loc[high, "priority_level"] == "high").all():
        raise DataContractError("INVENTORY_PRIORITY_LABEL_MISMATCH")
    if not (scores.loc[medium, "priority_level"] == "medium").all():
        raise DataContractError("INVENTORY_PRIORITY_LABEL_MISMATCH")
    if not (scores.loc[low, "priority_level"] == "low").all():
        raise DataContractError("INVENTORY_PRIORITY_LABEL_MISMATCH")


def _validate_recommendations(recommendations: pd.DataFrame, budget: float) -> None:
    if recommendations.empty:
        raise DataContractError("INVENTORY_RECOMMENDATIONS_EMPTY")
    if (
        recommendations["recommended_reorder_quantity"]
        > recommendations["unconstrained_reorder_quantity"]
    ).any():
        raise DataContractError("INVENTORY_CONSTRAINT_EXCEEDS_UNCONSTRAINED")
    if (recommendations["recommended_reorder_quantity"] < 0).any():
        raise DataContractError("INVENTORY_NEGATIVE_REORDER_QUANTITY")
    if recommendations["recommended_reorder_value"].sum() > budget + 1e-6:
        raise DataContractError("INVENTORY_BUDGET_CONSTRAINT_EXCEEDED")


def _validate_scenarios(scenarios: pd.DataFrame) -> None:
    scenario_names = set(scenarios["scenario_name"])
    if scenario_names != SUPPORTED_SCENARIOS:
        raise DataContractError(f"INVENTORY_SCENARIO_SET_INVALID: {sorted(scenario_names)}")
    numeric_columns = [
        "total_unconstrained_quantity",
        "total_constrained_quantity",
        "working_capital_requirement",
        "projected_shortage_quantity",
        "projected_excess_quantity",
    ]
    for column in numeric_columns:
        if (scenarios[column] < 0).any():
            raise DataContractError(f"INVENTORY_SCENARIO_NEGATIVE_VALUE: {column}")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    input_hashes = manifest["governed_input_hashes"]
    checks = {
        "inventory_levels": config.inventory.inventory_path,
        "supplier_performance": config.inventory.supplier_path,
        "warehouse_movements": config.inventory.movements_path,
        "sales_orders": config.inventory.sales_orders_path,
        "demand_forecast": config.inventory.forecast_path,
    }
    for name, path in checks.items():
        if sha256_file(path) != input_hashes[name]:
            raise DataContractError(f"INVENTORY_UPSTREAM_INPUT_HASH_MISMATCH: {name}")


def _validate_run_identity(config: Any, manifest: dict[str, Any]) -> None:
    stable_inputs = {
        **manifest["governed_input_hashes"],
        "ingestion_manifest": manifest_hash(config.inventory.ingestion_manifest_path),
        "forecast_manifest": manifest_hash(config.inventory.forecast_manifest_path),
    }
    expected = inventory_run_id(config, stable_inputs)
    if manifest["inventory_run_id"] != expected:
        raise DataContractError("INVENTORY_RUN_ID_MISMATCH")


def _validate_lineage(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("INVENTORY_LINEAGE_INVALID")
    output_paths = {
        str(evidence["path"]) for evidence in outputs.values() if isinstance(evidence, dict)
    }
    lineage_targets = {
        str(record.get("target_path")) for record in lineage if isinstance(record, dict)
    }
    if not output_paths <= lineage_targets:
        raise DataContractError("INVENTORY_LINEAGE_TARGETS_MISSING")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"INVENTORY_OUTPUT_MISSING: {evidence['path']}")
    if evidence["file_size_bytes"] != path.stat().st_size:
        raise DataContractError(f"INVENTORY_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"INVENTORY_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if evidence["row_count"] != row_count:
            raise DataContractError(f"INVENTORY_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


def _resolve_output_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    candidate = resolve_project_path(path_value)
    if candidate.is_file():
        return candidate
    return output_dir.parent / path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"INVENTORY_JSON_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("Inventory manifest contains machine-specific absolute paths")
