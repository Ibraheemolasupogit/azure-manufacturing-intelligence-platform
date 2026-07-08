"""Governed equipment-health and context loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.maintenance.config import MaintenanceConfig

EQUIPMENT_REQUIRED_COLUMNS = {
    "sensor_event_id",
    "timestamp",
    "plant_id",
    "line_id",
    "machine_id",
    "sensor_id",
    "sensor_type",
    "measurement",
    "measurement_unit",
    "warning_threshold",
    "critical_threshold",
    "threshold_status",
    "runtime_hours",
    "service_hours_since_maintenance",
    "degradation_index",
    "operating_mode",
    "maintenance_state",
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
    "downtime_duration_minutes",
    "operating_status",
}

UNIT_BY_SENSOR_TYPE = {"vibration": "mm_s", "temperature": "celsius"}


@dataclass(frozen=True)
class MaintenanceInputEvidence:
    """Verified upstream evidence for maintenance analytics."""

    upstream_ingestion_run_id: str
    upstream_quality_run_id: str | None
    input_hashes: dict[str, str]
    input_row_counts: dict[str, int]
    synthetic_classification: str
    manifest_sha256: str
    quality_manifest_sha256: str | None
    before_hashes: dict[str, str]


@dataclass(frozen=True)
class MaintenanceInputs:
    """Loaded maintenance inputs."""

    equipment_health: pd.DataFrame
    production_events: pd.DataFrame
    quality_checks: pd.DataFrame
    quality_alerts: pd.DataFrame
    evidence: MaintenanceInputEvidence


def load_maintenance_inputs(config: MaintenanceConfig) -> MaintenanceInputs:
    """Load governed maintenance inputs and verify upstream evidence."""
    settings = config.maintenance
    for path in (settings.equipment_health_path, settings.production_events_path):
        if not path.is_file():
            raise DataContractError(f"Governed maintenance input is missing: {path}")
        if "data/raw" in path.as_posix():
            raise DataContractError("Maintenance analytics must not read directly from data/raw")

    manifest = cast(dict[str, Any], _read_json(settings.ingestion_manifest_path))
    validation_summary = cast(dict[str, Any], _read_json(settings.validation_summary_path))
    data_quality = cast(dict[str, Any], _read_json(settings.data_quality_report_path))
    lineage = _read_json(settings.ingestion_lineage_path, allow_list=True)
    if manifest.get("validation_status") != "success":
        raise DataContractError("Upstream ingestion manifest is not successful")
    if validation_summary.get("validation_status") != "success":
        raise DataContractError("Upstream validation summary is not successful")
    if manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
        raise DataContractError("Maintenance inputs must be classified as synthetic")
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("Upstream ingestion lineage is missing")
    for dataset in ("equipment_health", "production_events"):
        report = data_quality.get("datasets", {}).get(dataset, {})
        if report.get("status") != "passed":
            raise DataContractError(f"Upstream data-quality report is not passed: {dataset}")
        if validation_summary.get("quarantine_counts_by_dataset", {}).get(dataset) != 0:
            raise DataContractError(f"Maintenance dataset has quarantined records: {dataset}")

    equipment = pd.read_json(settings.equipment_health_path, lines=True)
    production = pd.read_json(settings.production_events_path, lines=True)
    _verify_manifest_entry(
        manifest, "equipment_health", settings.equipment_health_path, len(equipment)
    )
    _verify_manifest_entry(
        manifest, "production_events", settings.production_events_path, len(production)
    )
    _validate_columns(equipment, EQUIPMENT_REQUIRED_COLUMNS, "equipment_health")
    _validate_columns(production, PRODUCTION_REQUIRED_COLUMNS, "production_events")
    _validate_equipment(equipment, config)
    _validate_production(production)

    equipment = equipment.copy()
    equipment["event_timestamp"] = pd.to_datetime(equipment["timestamp"], errors="raise", utc=True)
    equipment["event_date"] = equipment["event_timestamp"].dt.date.astype(str)
    equipment["production_line_id"] = equipment["line_id"].astype(str)
    production = production.copy()
    production["event_timestamp"] = pd.to_datetime(
        production["event_timestamp"], errors="raise", utc=True
    )

    quality = _load_optional_quality(settings.quality_checks_path)
    quality_alerts = _load_optional_quality(settings.quality_alerts_path)
    if not quality.empty:
        quality["inspection_timestamp"] = pd.to_datetime(
            quality["inspection_timestamp"], errors="raise", utc=True
        )
        quality["production_line_id"] = quality.get(
            "production_line_id", quality.get("line_id", "")
        ).astype(str)

    quality_run_id: str | None = None
    quality_manifest_hash: str | None = None
    if settings.quality_manifest_path.is_file():
        quality_manifest = cast(dict[str, Any], _read_json(settings.quality_manifest_path))
        quality_run_id = str(quality_manifest.get("quality_run_id", ""))
        quality_manifest_hash = sha256_file(settings.quality_manifest_path)

    input_hashes = {
        "equipment_health": sha256_file(settings.equipment_health_path),
        "production_events": sha256_file(settings.production_events_path),
    }
    if not quality.empty:
        input_hashes["quality_checks"] = sha256_file(settings.quality_checks_path)
    if not quality_alerts.empty:
        input_hashes["quality_alerts"] = sha256_file(settings.quality_alerts_path)
    return MaintenanceInputs(
        equipment_health=equipment.sort_values(
            ["event_timestamp", "sensor_event_id"], ignore_index=True
        ),
        production_events=production.sort_values(
            ["event_timestamp", "event_id"], ignore_index=True
        ),
        quality_checks=quality,
        quality_alerts=quality_alerts,
        evidence=MaintenanceInputEvidence(
            upstream_ingestion_run_id=str(manifest["ingestion_run_id"]),
            upstream_quality_run_id=quality_run_id,
            input_hashes=input_hashes,
            input_row_counts={
                "equipment_health": len(equipment),
                "production_events": len(production),
                "quality_checks": len(quality),
                "quality_alerts": len(quality_alerts),
            },
            synthetic_classification=str(manifest["synthetic_data_classification"]),
            manifest_sha256=sha256_file(settings.ingestion_manifest_path),
            quality_manifest_sha256=quality_manifest_hash,
            before_hashes=input_hashes,
        ),
    )


def verify_upstream_unchanged(
    config: MaintenanceConfig, evidence: MaintenanceInputEvidence
) -> None:
    """Verify governed inputs were not modified during the run."""
    current = {
        "equipment_health": sha256_file(config.maintenance.equipment_health_path),
        "production_events": sha256_file(config.maintenance.production_events_path),
    }
    if "quality_checks" in evidence.before_hashes:
        current["quality_checks"] = sha256_file(config.maintenance.quality_checks_path)
    if "quality_alerts" in evidence.before_hashes:
        current["quality_alerts"] = sha256_file(config.maintenance.quality_alerts_path)
    if current != evidence.before_hashes:
        raise DataContractError("Governed maintenance inputs changed during the run")


def _load_optional_quality(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


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


def _validate_equipment(frame: pd.DataFrame, config: MaintenanceConfig) -> None:
    if frame[config.maintenance.primary_key].duplicated().any():
        raise DataContractError("Equipment sensor event IDs must be unique")
    pd.to_datetime(frame[config.maintenance.timestamp_field], errors="raise", utc=True)
    numeric = [
        "measurement",
        "warning_threshold",
        "critical_threshold",
        "runtime_hours",
        "service_hours_since_maintenance",
        "degradation_index",
    ]
    for column in numeric:
        if (frame[column] < 0).any():
            raise DataContractError(f"Equipment field must be non-negative: {column}")
    if (frame["critical_threshold"] <= frame["warning_threshold"]).any():
        raise DataContractError("Critical thresholds must exceed warning thresholds")
    expected_units = frame["sensor_type"].map(UNIT_BY_SENSOR_TYPE)
    if expected_units.isna().any() or (expected_units != frame["measurement_unit"]).any():
        raise DataContractError("Sensor type and unit combinations are not coherent")


def _validate_production(frame: pd.DataFrame) -> None:
    pd.to_datetime(frame["event_timestamp"], errors="raise", utc=True)
    numeric = [
        "produced_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "downtime_duration_minutes",
    ]
    for column in numeric:
        if (frame[column] < 0).any():
            raise DataContractError(f"Production field must be non-negative: {column}")


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
