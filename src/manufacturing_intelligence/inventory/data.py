"""Governed input loading for inventory intelligence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.inventory.config import InventoryConfig


@dataclass(frozen=True)
class InventoryInputEvidence:
    """Verified upstream input evidence."""

    upstream_ingestion_run_id: str
    upstream_forecast_run_id: str
    synthetic_classification: str
    input_hashes: dict[str, str]
    input_row_counts: dict[str, int]


@dataclass(frozen=True)
class InventoryInputs:
    """Loaded governed inventory inputs."""

    inventory: pd.DataFrame
    suppliers: pd.DataFrame
    warehouse_movements: pd.DataFrame
    sales_orders: pd.DataFrame
    forecast: pd.DataFrame
    evidence: InventoryInputEvidence
    forecast_manifest: dict[str, Any]


def load_governed_inventory_inputs(config: InventoryConfig) -> InventoryInputs:
    """Load governed inventory inputs after verifying upstream evidence."""
    settings = config.inventory
    manifest = _read_json(settings.ingestion_manifest_path)
    validation_summary = _read_json(settings.validation_summary_path)
    _read_json(settings.data_quality_report_path)
    _read_json(settings.ingestion_lineage_path, allow_list=True)
    forecast_manifest = _read_json(settings.forecast_manifest_path)
    _read_json(settings.forecast_model_metadata_path)
    _read_json(settings.forecast_lineage_path, allow_list=True)
    if manifest.get("validation_status") != "success":
        raise DataContractError("Upstream ingestion manifest is not successful")
    if validation_summary.get("validation_status") != "success":
        raise DataContractError("Upstream validation summary is not successful")
    if forecast_manifest.get("validation_status") != "success":
        raise DataContractError("Upstream forecast manifest is not successful")
    if manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
        raise DataContractError("Inventory input must be classified as synthetic")

    accepted = manifest.get("accepted_outputs", {})
    if not isinstance(accepted, dict):
        raise DataContractError("Upstream ingestion manifest accepted outputs are invalid")
    required = {
        "inventory_levels": settings.inventory_path,
        "supplier_performance": settings.supplier_path,
        "warehouse_movements": settings.movements_path,
        "sales_orders": settings.sales_orders_path,
    }
    frames: dict[str, pd.DataFrame] = {}
    input_hashes: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    for dataset, path in required.items():
        _reject_raw_path(path)
        evidence = accepted.get(dataset)
        if not isinstance(evidence, dict):
            raise DataContractError(f"Upstream accepted evidence missing: {dataset}")
        frame = _read_verified_csv(path, evidence, dataset)
        frames[dataset] = frame
        input_hashes[dataset] = sha256_file(path)
        row_counts[dataset] = len(frame)

    forecast_evidence = forecast_manifest["output_files"]["demand_forecast"]
    forecast = _read_verified_csv(settings.forecast_path, forecast_evidence, "demand_forecast")
    input_hashes["demand_forecast"] = sha256_file(settings.forecast_path)
    row_counts["demand_forecast"] = len(forecast)
    if forecast_manifest["governed_input_sha256"] != input_hashes["sales_orders"]:
        raise DataContractError("Forecast manifest does not match governed sales-order input")
    if forecast_manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
        raise DataContractError("Forecast input must be classified as synthetic")
    _validate_columns(frames["inventory_levels"], _INVENTORY_COLUMNS, "inventory_levels")
    _validate_columns(frames["supplier_performance"], _SUPPLIER_COLUMNS, "supplier_performance")
    _validate_columns(frames["warehouse_movements"], _WAREHOUSE_COLUMNS, "warehouse_movements")
    _validate_columns(frames["sales_orders"], _SALES_COLUMNS, "sales_orders")
    _validate_columns(forecast, _FORECAST_COLUMNS, "demand_forecast")
    _validate_inventory_values(frames["inventory_levels"])
    _validate_supplier_values(frames["supplier_performance"])
    _validate_identifier_resolution(
        frames["inventory_levels"],
        frames["supplier_performance"],
        frames["warehouse_movements"],
        forecast,
    )
    observed_end = pd.to_datetime(forecast_manifest["observed_date_range"][1])
    if (pd.to_datetime(forecast["forecast_date"]) <= observed_end).any():
        raise DataContractError("Inventory forecast dates must be future dated")

    return InventoryInputs(
        inventory=frames["inventory_levels"],
        suppliers=frames["supplier_performance"],
        warehouse_movements=frames["warehouse_movements"],
        sales_orders=frames["sales_orders"],
        forecast=forecast,
        evidence=InventoryInputEvidence(
            upstream_ingestion_run_id=str(manifest["ingestion_run_id"]),
            upstream_forecast_run_id=str(forecast_manifest["forecast_run_id"]),
            synthetic_classification=str(manifest["synthetic_data_classification"]),
            input_hashes=input_hashes,
            input_row_counts=row_counts,
        ),
        forecast_manifest=forecast_manifest,
    )


def _read_verified_csv(path: Path, evidence: dict[str, Any], dataset: str) -> pd.DataFrame:
    if not path.is_file():
        raise DataContractError(f"Governed input is missing: {path}")
    if sha256_file(path) != evidence["sha256"]:
        raise DataContractError(f"Governed input SHA-256 mismatch: {dataset}")
    if path.stat().st_size != evidence["file_size_bytes"]:
        raise DataContractError(f"Governed input file size mismatch: {dataset}")
    frame = pd.read_csv(path)
    if len(frame) != int(evidence["row_count"]):
        raise DataContractError(f"Governed input row count mismatch: {dataset}")
    return frame


def _read_json(path: Path, *, allow_list: bool = False) -> dict[str, Any]:
    if not path.is_file():
        raise DataContractError(f"Required upstream evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if allow_list and isinstance(payload, list):
        return {}
    if not isinstance(payload, dict):
        raise DataContractError(f"Upstream evidence must be an object: {path}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"Upstream evidence contains machine-specific paths: {path}")
    return payload


def _reject_raw_path(path: Path) -> None:
    if "data/raw" in path.as_posix():
        raise DataContractError("Inventory intelligence must not read directly from data/raw")


def _validate_columns(frame: pd.DataFrame, required: set[str], dataset: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataContractError(f"Required fields missing for {dataset}: {missing}")


def _validate_inventory_values(inventory: pd.DataFrame) -> None:
    numeric = [
        "on_hand_quantity",
        "reserved_quantity",
        "available_quantity",
        "reorder_point",
        "safety_stock_quantity",
        "lead_time_days",
        "unit_cost",
        "inventory_value",
    ]
    for column in numeric:
        if (inventory[column] < 0).any():
            raise DataContractError(f"Inventory values must be non-negative: {column}")


def _validate_supplier_values(suppliers: pd.DataFrame) -> None:
    order_dates = pd.to_datetime(suppliers["order_date"])
    delivery_dates = pd.to_datetime(suppliers["actual_delivery_date"])
    if ((delivery_dates - order_dates).dt.days < 0).any():
        raise DataContractError("Supplier lead times must be non-negative")


def _validate_identifier_resolution(
    inventory: pd.DataFrame,
    suppliers: pd.DataFrame,
    movements: pd.DataFrame,
    forecast: pd.DataFrame,
) -> None:
    inventory_items = set(inventory["item_id"].astype(str))
    inventory_warehouses = set(inventory["warehouse_id"].astype(str))
    supplier_materials = set(suppliers["material_id"].astype(str))
    movement_items = set(movements["item_id"].astype(str))
    movement_warehouses = set(movements["warehouse_id"].astype(str))
    forecast_products = set(forecast["product_id"].astype(str))
    unresolved_movement_items = sorted(movement_items - inventory_items)
    unresolved_movement_warehouses = sorted(movement_warehouses - inventory_warehouses)
    if unresolved_movement_items:
        raise DataContractError(
            f"Warehouse movement items do not resolve: {unresolved_movement_items}"
        )
    if unresolved_movement_warehouses:
        raise DataContractError(
            f"Warehouse movement warehouses do not resolve: {unresolved_movement_warehouses}"
        )
    product_items = set(
        inventory[inventory["product_or_material_type"] == "product"]["item_id"].astype(str)
    )
    if not forecast_products <= product_items:
        raise DataContractError("Forecast products must resolve to product inventory records")
    material_items = set(
        inventory[inventory["product_or_material_type"] != "product"]["item_id"].astype(str)
    )
    if not supplier_materials <= material_items:
        raise DataContractError("Supplier materials must resolve to material inventory records")


_INVENTORY_COLUMNS = {
    "snapshot_timestamp",
    "warehouse_id",
    "plant_id",
    "item_id",
    "product_or_material_type",
    "on_hand_quantity",
    "reserved_quantity",
    "available_quantity",
    "reorder_point",
    "safety_stock_quantity",
    "lead_time_days",
    "unit_cost",
    "inventory_value",
    "expiry_date",
}
_SUPPLIER_COLUMNS = {
    "supplier_id",
    "material_id",
    "order_date",
    "actual_delivery_date",
    "delay_days",
    "on_time_flag",
    "in_full_flag",
    "ordered_quantity",
    "delivered_quantity",
    "accepted_quantity",
    "rejected_quantity",
    "quality_score",
    "delivery_status",
}
_WAREHOUSE_COLUMNS = {"movement_id", "warehouse_id", "item_id", "quantity", "movement_type"}
_SALES_COLUMNS = {"order_id", "order_date", "product_id", "ordered_quantity"}
_FORECAST_COLUMNS = {
    "forecast_run_id",
    "product_id",
    "distribution_region",
    "forecast_date",
    "forecast_horizon_day",
    "point_forecast",
    "lower_bound",
    "upper_bound",
}
