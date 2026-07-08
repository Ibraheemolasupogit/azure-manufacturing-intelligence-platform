"""Existing maintenance-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.maintenance.config import load_maintenance_config
from manufacturing_intelligence.maintenance.manifest import maintenance_run_id, manifest_hash

REQUIRED_OUTPUTS = {
    "equipment_health_features",
    "equipment_health_scores",
    "maintenance_alerts",
    "machine_health_summary",
    "sensor_health_summary",
    "degradation_signals",
    "anomaly_scores",
    "maintenance_risk_summary",
    "maintenance_diagnostics",
    "maintenance_analytics_report",
    "maintenance_alert_summary",
    "portfolio_maintenance_predictions",
}

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing maintenance run without rescoring."""
    config = load_maintenance_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.maintenance.output_directory
    )
    manifest_path = output_dir / "maintenance-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("MAINTENANCE_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("MAINTENANCE_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files", {})
    if not isinstance(outputs, dict):
        raise DataContractError("MAINTENANCE_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"MAINTENANCE_MANIFEST_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        if isinstance(evidence, dict):
            _verify_file(output_dir, evidence)

    features = pd.read_csv(
        _resolve_output_path(output_dir, outputs["equipment_health_features"]["path"])
    )
    scores = pd.read_csv(
        _resolve_output_path(output_dir, outputs["equipment_health_scores"]["path"])
    )
    alerts = pd.read_csv(_resolve_output_path(output_dir, outputs["maintenance_alerts"]["path"]))
    anomaly = pd.read_csv(_resolve_output_path(output_dir, outputs["anomaly_scores"]["path"]))
    _validate_features(features)
    _validate_scores(scores, manifest["risk_scoring_settings"])
    _validate_alerts(alerts)
    _validate_anomalies(anomaly)
    _validate_upstream_hashes(config, manifest)
    _validate_run_identity(config, manifest)
    _validate_lineage(lineage_path, outputs)


def _validate_features(features: pd.DataFrame) -> None:
    if features["sensor_event_id"].duplicated().any():
        raise DataContractError("MAINTENANCE_DUPLICATE_SENSOR_EVENT_ID")
    calculated = pd.Series("normal", index=features.index)
    warning = (features["sensor_value"] >= features["warning_threshold"]) & (
        features["sensor_value"] < features["critical_threshold"]
    )
    critical = features["sensor_value"] >= features["critical_threshold"]
    calculated.loc[warning] = "warning"
    calculated.loc[critical] = "critical"
    if not (calculated == features["calculated_threshold_status"]).all():
        raise DataContractError("MAINTENANCE_THRESHOLD_FORMULA_MISMATCH")
    expected_consistency = (
        features["source_threshold_status"] == features["calculated_threshold_status"]
    )
    if not (expected_consistency == features["threshold_consistency_flag"]).all():
        raise DataContractError("MAINTENANCE_THRESHOLD_CONSISTENCY_MISMATCH")
    incompatible = features.groupby(["machine_id", "sensor_type"])["measurement_unit"].nunique()
    if (incompatible > 1).any():
        raise DataContractError("MAINTENANCE_INCOMPATIBLE_SENSOR_UNITS_AGGREGATED")


def _validate_scores(scores: pd.DataFrame, risk_settings: dict[str, Any]) -> None:
    if not scores["failure_risk_score"].between(0, 100).all():
        raise DataContractError("MAINTENANCE_RISK_SCORE_RANGE")
    if not scores["equipment_health_score"].between(0, 100).all():
        raise DataContractError("MAINTENANCE_HEALTH_SCORE_RANGE")
    if not set(scores["risk_level"]) <= VALID_RISK_LEVELS:
        raise DataContractError("MAINTENANCE_UNKNOWN_RISK_LEVEL")
    high = float(risk_settings["high_threshold"])
    critical = float(risk_settings["critical_threshold"])
    if not (scores.loc[scores["failure_risk_score"] >= critical, "risk_level"] == "critical").all():
        raise DataContractError("MAINTENANCE_RISK_LABEL_MISMATCH")
    high_rows = scores["failure_risk_score"].between(high, critical, inclusive="left")
    if not (scores.loc[high_rows, "risk_level"] == "high").all():
        raise DataContractError("MAINTENANCE_RISK_LABEL_MISMATCH")


def _validate_alerts(alerts: pd.DataFrame) -> None:
    if alerts["alert_id"].duplicated().any():
        raise DataContractError("MAINTENANCE_DUPLICATE_ALERT_ID")
    if alerts["failure_risk_score"].isna().any():
        raise DataContractError("MAINTENANCE_ALERT_SCORE_MISSING")


def _validate_anomalies(anomaly: pd.DataFrame) -> None:
    calculated = anomaly["robust_zscore_status"] == "calculated"
    expected = anomaly["robust_zscore_abs"] >= anomaly["robust_zscore_threshold"]
    if not (expected[calculated] == anomaly.loc[calculated, "robust_zscore_anomaly_flag"]).all():
        raise DataContractError("MAINTENANCE_ROBUST_Z_FLAG_MISMATCH")
    if (
        anomaly["isolation_forest_score_interpretation"].str.contains("probability").any()
        and not anomaly["isolation_forest_score_interpretation"]
        .str.contains("not_probability")
        .all()
    ):
        raise DataContractError("MAINTENANCE_ANOMALY_PROBABILITY_CLAIM")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    hashes = manifest["governed_input_hashes"]
    if sha256_file(config.maintenance.equipment_health_path) != hashes["equipment_health"]:
        raise DataContractError("MAINTENANCE_UPSTREAM_HASH_MISMATCH: equipment_health")
    if sha256_file(config.maintenance.production_events_path) != hashes["production_events"]:
        raise DataContractError("MAINTENANCE_UPSTREAM_HASH_MISMATCH: production_events")


def _validate_run_identity(config: Any, manifest: dict[str, Any]) -> None:
    stable_inputs = {
        **manifest["governed_input_hashes"],
        "ingestion_manifest": manifest_hash(config.maintenance.ingestion_manifest_path),
    }
    if manifest.get("upstream_quality_manifest_sha256"):
        stable_inputs["quality_manifest"] = str(manifest["upstream_quality_manifest_sha256"])
    expected = maintenance_run_id(config, stable_inputs)
    if manifest["maintenance_run_id"] != expected:
        raise DataContractError("MAINTENANCE_RUN_ID_MISMATCH")


def _validate_lineage(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("MAINTENANCE_LINEAGE_INVALID")
    paths = {str(item["path"]) for item in outputs.values() if isinstance(item, dict)}
    lineage_paths = {str(item.get("target_path")) for item in lineage if isinstance(item, dict)}
    if not paths <= lineage_paths:
        raise DataContractError("MAINTENANCE_LINEAGE_TARGETS_MISSING")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"MAINTENANCE_OUTPUT_MISSING: {evidence['path']}")
    if int(evidence["file_size_bytes"]) != path.stat().st_size:
        raise DataContractError(f"MAINTENANCE_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"MAINTENANCE_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if int(evidence["row_count"]) != row_count:
            raise DataContractError(f"MAINTENANCE_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


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
        raise DataContractError(f"MAINTENANCE_JSON_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("Maintenance manifest contains machine-specific absolute paths")
