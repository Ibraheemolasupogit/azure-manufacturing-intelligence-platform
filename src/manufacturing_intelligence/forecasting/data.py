"""Governed sales-order loading for forecasting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.forecasting.config import ForecastingConfig


@dataclass(frozen=True)
class GovernedInputEvidence:
    """Verified upstream input evidence."""

    upstream_ingestion_run_id: str
    input_hash: str
    input_row_count: int
    synthetic_classification: str


def load_governed_sales_orders(
    config: ForecastingConfig,
) -> tuple[pd.DataFrame, GovernedInputEvidence]:
    """Load accepted sales orders after verifying Milestone 3 evidence."""
    settings = config.forecasting
    if not settings.input_path.is_file():
        raise DataContractError(f"Accepted sales-order file is missing: {settings.input_path}")
    if "data/raw" in settings.input_path.as_posix():
        raise DataContractError("Forecasting must not train directly from data/raw")
    manifest = _read_json(settings.ingestion_manifest_path)
    validation_summary = _read_json(settings.validation_summary_path)
    _read_json(settings.data_quality_report_path)
    _read_json(settings.lineage_path, allow_list=True)
    if manifest.get("validation_status") != "success":
        raise DataContractError("Upstream ingestion manifest is not successful")
    if validation_summary.get("validation_status") != "success":
        raise DataContractError("Upstream validation summary is not successful")
    quarantine_counts = validation_summary.get("quarantine_counts_by_dataset", {})
    if quarantine_counts.get("sales_orders") != 0:
        raise DataContractError("Accepted sales-order quarantine count must be zero")
    if manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
        raise DataContractError("Forecasting input must be classified as synthetic")
    evidence = manifest["accepted_outputs"]["sales_orders"]
    if evidence["sha256"] != sha256_file(settings.input_path):
        raise DataContractError("Accepted sales-order SHA-256 does not match ingestion manifest")
    if evidence["file_size_bytes"] != settings.input_path.stat().st_size:
        raise DataContractError("Accepted sales-order size does not match ingestion manifest")

    frame = pd.read_csv(settings.input_path)
    if int(evidence["row_count"]) != len(frame):
        raise DataContractError("Accepted sales-order row count does not match ingestion manifest")
    required = set(settings.series_keys) | {settings.date_field, settings.target_field}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataContractError(f"Sales-order fields missing for forecasting: {missing}")
    try:
        frame[settings.date_field] = pd.to_datetime(frame[settings.date_field], errors="raise")
    except Exception as exc:  # pragma: no cover - pandas message varies by version
        raise DataContractError("Sales-order dates are not parseable") from exc
    if (frame[settings.target_field] < 0).any():
        raise DataContractError("Forecasting target quantities must be non-negative")

    return frame, GovernedInputEvidence(
        upstream_ingestion_run_id=str(manifest["ingestion_run_id"]),
        input_hash=sha256_file(settings.input_path),
        input_row_count=len(frame),
        synthetic_classification=str(manifest["synthetic_data_classification"]),
    )


def relative_path(path: Path, *, base_directory: Path | None = None) -> str:
    """Return a repository-relative path where possible."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        if base_directory is not None:
            try:
                return resolved.relative_to(base_directory.resolve()).as_posix()
            except ValueError:
                pass
        return resolved.as_posix()


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
