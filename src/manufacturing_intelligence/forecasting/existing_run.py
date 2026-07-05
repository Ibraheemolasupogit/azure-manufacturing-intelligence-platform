"""Existing forecast-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.forecasting.config import load_forecasting_config

REQUIRED_OUTPUTS = {
    "daily_demand_series",
    "feature_dataset",
    "model_comparison",
    "backtest_predictions",
    "backtest_metrics",
    "test_metrics",
    "forecast_diagnostics",
    "model_metadata",
    "demand_forecast",
}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing forecast run without retraining."""
    config = load_forecasting_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.forecasting.output_directory
    )
    manifest_path = output_dir / "forecast-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("FORECAST_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("FORECAST_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files", {})
    if not isinstance(outputs, dict):
        raise DataContractError("FORECAST_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"FORECAST_MANIFEST_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        if isinstance(evidence, dict):
            _verify_file(output_dir, evidence)
    forecast = pd.read_csv(_resolve_output_path(output_dir, outputs["demand_forecast"]["path"]))
    if (forecast["point_forecast"] < 0).any():
        raise DataContractError("FORECAST_NEGATIVE_POINT")
    if (forecast["lower_bound"] < 0).any():
        raise DataContractError("FORECAST_NEGATIVE_LOWER")
    if (forecast["lower_bound"] > forecast["point_forecast"]).any():
        raise DataContractError("FORECAST_INTERVAL_ORDER")
    if (forecast["upper_bound"] < forecast["point_forecast"]).any():
        raise DataContractError("FORECAST_INTERVAL_ORDER")
    if forecast.duplicated(["series_id", "forecast_date"]).any():
        raise DataContractError("FORECAST_DUPLICATE_SERIES_DATE")
    observed_end = pd.to_datetime(manifest["observed_date_range"][1])
    if (pd.to_datetime(forecast["forecast_date"]) <= observed_end).any():
        raise DataContractError("FORECAST_DATE_NOT_FUTURE")
    split = manifest["split_metadata"]
    if not (
        split["train_end"]
        < split["validation_start"]
        <= split["validation_end"]
        < split["test_start"]
        <= split["test_end"]
        < split["forecast_start"]
    ):
        raise DataContractError("FORECAST_SPLIT_CHRONOLOGY_INVALID")
    if sha256_file(config.forecasting.input_path) != manifest["governed_input_sha256"]:
        raise DataContractError("FORECAST_UPSTREAM_INPUT_HASH_MISMATCH")
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("FORECAST_LINEAGE_INVALID")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"FORECAST_OUTPUT_MISSING: {evidence['path']}")
    if evidence["file_size_bytes"] != path.stat().st_size:
        raise DataContractError(f"FORECAST_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"FORECAST_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if evidence["row_count"] != row_count:
            raise DataContractError(f"FORECAST_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


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
        raise DataContractError(f"FORECAST_JSON_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("Forecast manifest contains machine-specific absolute paths")
