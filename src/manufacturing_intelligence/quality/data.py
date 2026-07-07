"""Governed quality and production data loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.quality.config import QualityConfig

QUALITY_REQUIRED_COLUMNS = {
    "inspection_id",
    "inspection_timestamp",
    "plant_id",
    "line_id",
    "machine_id",
    "batch_id",
    "product_id",
    "quality_metric",
    "sample_size",
    "defective_units",
    "measured_value",
    "lower_specification_limit",
    "upper_specification_limit",
    "inspection_result",
    "defect_category",
    "severity",
}

PRODUCTION_REQUIRED_COLUMNS = {
    "event_id",
    "event_timestamp",
    "plant_id",
    "production_line_id",
    "machine_id",
    "batch_id",
    "product_id",
    "produced_quantity",
    "accepted_quantity",
    "rejected_quantity",
    "cycle_time_seconds",
    "target_cycle_time_seconds",
    "downtime_duration_minutes",
    "operating_status",
}

METRIC_UNITS = {
    "diameter_mm": "mm",
    "surface_finish_ra": "ra",
    "torque_nm": "Nm",
}


@dataclass(frozen=True)
class QualityInputEvidence:
    """Verified upstream evidence for quality analytics."""

    upstream_ingestion_run_id: str
    input_hashes: dict[str, str]
    input_row_counts: dict[str, int]
    synthetic_classification: str
    manifest_sha256: str
    before_hashes: dict[str, str]


@dataclass(frozen=True)
class QualityInputs:
    """Loaded quality inputs and evidence."""

    quality_checks: pd.DataFrame
    production_events: pd.DataFrame
    evidence: QualityInputEvidence


def load_quality_inputs(config: QualityConfig) -> QualityInputs:
    """Load accepted quality inputs after verifying upstream evidence."""
    settings = config.quality
    for path in (settings.quality_checks_path, settings.production_events_path):
        if not path.is_file():
            raise DataContractError(f"Governed quality input is missing: {path}")
        if "data/raw" in path.as_posix():
            raise DataContractError("Quality analytics must not read directly from data/raw")

    manifest = cast(dict[str, Any], _read_json(settings.ingestion_manifest_path))
    validation_summary = cast(dict[str, Any], _read_json(settings.validation_summary_path))
    data_quality = cast(dict[str, Any], _read_json(settings.data_quality_report_path))
    lineage = _read_json(settings.ingestion_lineage_path, allow_list=True)
    if manifest.get("validation_status") != "success":
        raise DataContractError("Upstream ingestion manifest is not successful")
    if validation_summary.get("validation_status") != "success":
        raise DataContractError("Upstream validation summary is not successful")
    if manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
        raise DataContractError("Quality inputs must be classified as synthetic")
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("Upstream ingestion lineage is missing")
    for dataset in ("quality_checks", "production_events"):
        report = data_quality.get("datasets", {}).get(dataset, {})
        if report.get("status") != "passed":
            raise DataContractError(f"Upstream data-quality report is not passed: {dataset}")
        if validation_summary.get("quarantine_counts_by_dataset", {}).get(dataset) != 0:
            raise DataContractError(f"Quality dataset has quarantined records: {dataset}")

    quality = pd.read_csv(settings.quality_checks_path)
    production = pd.read_json(settings.production_events_path, lines=True)
    _verify_manifest_entry(manifest, "quality_checks", settings.quality_checks_path, len(quality))
    _verify_manifest_entry(
        manifest, "production_events", settings.production_events_path, len(production)
    )
    _validate_columns(quality, QUALITY_REQUIRED_COLUMNS, "quality_checks")
    _validate_columns(production, PRODUCTION_REQUIRED_COLUMNS, "production_events")
    _validate_quality_records(quality, config)
    _validate_production_records(production)
    _validate_references(quality, production)

    quality = quality.copy()
    production = production.copy()
    quality["inspection_timestamp"] = pd.to_datetime(
        quality["inspection_timestamp"], errors="raise", utc=True
    )
    quality["inspection_date"] = quality["inspection_timestamp"].dt.date.astype(str)
    quality["production_line_id"] = quality["line_id"].astype(str)
    quality["measurement_unit"] = quality["quality_metric"].map(METRIC_UNITS).fillna("unknown")
    quality["defect_category"] = quality["defect_category"].fillna("")
    production["event_timestamp"] = pd.to_datetime(
        production["event_timestamp"], errors="raise", utc=True
    )

    input_hashes = {
        "quality_checks": sha256_file(settings.quality_checks_path),
        "production_events": sha256_file(settings.production_events_path),
    }
    return QualityInputs(
        quality_checks=quality.sort_values(
            ["inspection_timestamp", "inspection_id"], ignore_index=True
        ),
        production_events=production.sort_values(
            ["event_timestamp", "event_id"], ignore_index=True
        ),
        evidence=QualityInputEvidence(
            upstream_ingestion_run_id=str(manifest["ingestion_run_id"]),
            input_hashes=input_hashes,
            input_row_counts={
                "quality_checks": len(quality),
                "production_events": len(production),
            },
            synthetic_classification=str(manifest["synthetic_data_classification"]),
            manifest_sha256=sha256_file(settings.ingestion_manifest_path),
            before_hashes=input_hashes,
        ),
    )


def verify_upstream_unchanged(config: QualityConfig, evidence: QualityInputEvidence) -> None:
    """Verify governed inputs were not modified during the run."""
    current = {
        "quality_checks": sha256_file(config.quality.quality_checks_path),
        "production_events": sha256_file(config.quality.production_events_path),
    }
    if current != evidence.before_hashes:
        raise DataContractError("Governed quality inputs changed during the quality run")


def _verify_manifest_entry(
    manifest: dict[str, Any], dataset: str, path: Path, row_count: int
) -> None:
    entry = manifest.get("accepted_outputs", {}).get(dataset)
    if not isinstance(entry, dict):
        raise DataContractError(f"Upstream manifest lacks accepted output: {dataset}")
    if entry.get("sha256") != sha256_file(path):
        raise DataContractError(f"Accepted input hash mismatch: {dataset}")
    if int(entry.get("row_count", -1)) != row_count:
        raise DataContractError(f"Accepted input row count mismatch: {dataset}")
    if int(entry.get("file_size_bytes", -1)) != path.stat().st_size:
        raise DataContractError(f"Accepted input file-size mismatch: {dataset}")


def _validate_columns(frame: pd.DataFrame, required: set[str], dataset: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataContractError(f"{dataset} missing required fields: {missing}")


def _validate_quality_records(frame: pd.DataFrame, config: QualityConfig) -> None:
    if frame[config.quality.primary_key].duplicated().any():
        raise DataContractError("Quality inspection IDs must be unique")
    pd.to_datetime(frame[config.quality.timestamp_field], errors="raise", utc=True)
    if (frame["sample_size"] <= 0).any() or (frame["defective_units"] < 0).any():
        raise DataContractError("Quality sample and defect counts must be valid")
    if (frame["defective_units"] > frame["sample_size"]).any():
        raise DataContractError("Defective units must not exceed sample size")
    if (frame["lower_specification_limit"] >= frame["upper_specification_limit"]).any():
        raise DataContractError("Quality specification limits must be valid")
    if frame["quality_metric"].map(METRIC_UNITS).isna().any():
        raise DataContractError("Quality measurement units are not coherent")


def _validate_production_records(frame: pd.DataFrame) -> None:
    pd.to_datetime(frame["event_timestamp"], errors="raise", utc=True)
    numeric = [
        "produced_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "cycle_time_seconds",
        "target_cycle_time_seconds",
        "downtime_duration_minutes",
    ]
    for column in numeric:
        if (frame[column] < 0).any():
            raise DataContractError(f"Production field must be non-negative: {column}")


def _validate_references(quality: pd.DataFrame, production: pd.DataFrame) -> None:
    production_batches = set(production["batch_id"].astype(str))
    unresolved_batches = sorted(set(quality["batch_id"].astype(str)) - production_batches)
    if unresolved_batches:
        raise DataContractError(f"Quality batches do not resolve: {unresolved_batches[:5]}")
    merged = quality.merge(
        production[
            [
                "batch_id",
                "plant_id",
                "production_line_id",
                "machine_id",
                "product_id",
            ]
        ],
        on="batch_id",
        suffixes=("_quality", "_production"),
        how="left",
    )
    mismatches = (
        (merged["plant_id_quality"] != merged["plant_id_production"])
        | (merged["line_id"] != merged["production_line_id"])
        | (merged["machine_id_quality"] != merged["machine_id_production"])
        | (merged["product_id_quality"] != merged["product_id_production"])
    )
    if mismatches.any():
        raise DataContractError("Quality product, plant, line, or machine references mismatch")


def _read_json(path: Path, *, allow_list: bool = False) -> dict[str, Any] | list[Any]:
    if not path.is_file():
        raise DataContractError(f"Required upstream evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if allow_list and isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise DataContractError(f"Upstream evidence must be an object: {path}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"Upstream evidence contains machine-specific paths: {path}")
    return payload
