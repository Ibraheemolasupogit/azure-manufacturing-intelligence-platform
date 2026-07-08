"""Existing monitoring-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.monitoring.config import SUPPORTED_DOMAINS, load_monitoring_config
from manufacturing_intelligence.monitoring.manifest import monitoring_run_id

REQUIRED_OUTPUTS = {
    "platform_health_summary",
    "pipeline_health",
    "domain_health_scores",
    "data_quality_monitoring",
    "model_and_analytics_monitoring",
    "monitoring_alerts",
    "evidence_integrity_checks",
    "lineage_completeness",
    "monitoring_diagnostics",
    "portfolio_platform_health_summary",
    "platform_monitoring_report",
    "observability_summary",
}
VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_LABELS = {"healthy", "watch", "degraded", "critical"}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing monitoring run without recalculating outputs."""
    config = load_monitoring_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.monitoring.output_directory
    )
    manifest_path = output_dir / "monitoring-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("MONITORING_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("MONITORING_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files", {})
    if not isinstance(outputs, dict):
        raise DataContractError("MONITORING_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"MONITORING_MANIFEST_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        if isinstance(evidence, dict):
            _verify_file(output_dir, evidence)
    domain_scores = pd.read_csv(
        _resolve_output_path(output_dir, outputs["domain_health_scores"]["path"])
    )
    alerts = pd.read_csv(_resolve_output_path(output_dir, outputs["monitoring_alerts"]["path"]))
    integrity = pd.read_csv(
        _resolve_output_path(output_dir, outputs["evidence_integrity_checks"]["path"])
    )
    lineage = pd.read_csv(_resolve_output_path(output_dir, outputs["lineage_completeness"]["path"]))
    _validate_domain_scores(domain_scores)
    _validate_alerts(alerts)
    _validate_integrity(integrity)
    _validate_lineage_scores(lineage)
    _validate_upstream_hashes(config, manifest)
    _validate_run_identity(config, manifest)
    _validate_lineage_file(lineage_path, outputs)


def _validate_domain_scores(frame: pd.DataFrame) -> None:
    if not set(frame["domain"]) <= SUPPORTED_DOMAINS:
        raise DataContractError("MONITORING_UNKNOWN_DOMAIN")
    if not frame["health_score"].between(0, 100).all():
        raise DataContractError("MONITORING_HEALTH_SCORE_RANGE")
    if not set(frame["health_label"]) <= VALID_LABELS:
        raise DataContractError("MONITORING_HEALTH_LABEL_INVALID")


def _validate_alerts(alerts: pd.DataFrame) -> None:
    if alerts["alert_id"].duplicated().any():
        raise DataContractError("MONITORING_DUPLICATE_ALERT_ID")
    if not set(alerts["severity"]) <= VALID_SEVERITIES:
        raise DataContractError("MONITORING_ALERT_SEVERITY_INVALID")
    if not set(alerts["domain"]) <= (SUPPORTED_DOMAINS | {"platform"}):
        raise DataContractError("MONITORING_ALERT_DOMAIN_INVALID")


def _validate_integrity(integrity: pd.DataFrame) -> None:
    for row in integrity.to_dict("records"):
        if (
            bool(row["exists"])
            and row["expected_sha256"]
            and sha256_file(resolve_project_path(str(row["path"]))) != row["expected_sha256"]
        ):
            raise DataContractError("MONITORING_INTEGRITY_SOURCE_HASH_MISMATCH")


def _validate_lineage_scores(lineage: pd.DataFrame) -> None:
    if not lineage["lineage_completeness_score"].between(0, 100).all():
        raise DataContractError("MONITORING_LINEAGE_SCORE_RANGE")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    expected = {
        "generation_manifest": config.inputs.generation_manifest_path,
        "ingestion_manifest": config.inputs.ingestion_manifest_path,
        "forecast_manifest": config.inputs.forecast_manifest_path,
        "inventory_manifest": config.inputs.inventory_manifest_path,
        "quality_manifest": config.inputs.quality_manifest_path,
        "maintenance_manifest": config.inputs.maintenance_manifest_path,
    }
    for name, path in expected.items():
        if manifest["input_hashes"][name] != sha256_file(path):
            raise DataContractError(f"MONITORING_UPSTREAM_HASH_MISMATCH: {name}")


def _validate_run_identity(config: Any, manifest: dict[str, Any]) -> None:
    stable = {
        key: manifest["input_hashes"][key]
        for key in [
            "generation_manifest",
            "ingestion_manifest",
            "forecast_manifest",
            "inventory_manifest",
            "quality_manifest",
            "maintenance_manifest",
        ]
    }
    expected = monitoring_run_id(config, stable)
    if manifest["monitoring_run_id"] != expected:
        raise DataContractError("MONITORING_RUN_ID_MISMATCH")


def _validate_lineage_file(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("MONITORING_LINEAGE_INVALID")
    paths = {str(item["path"]) for item in outputs.values() if isinstance(item, dict)}
    lineage_paths = {str(item.get("target_path")) for item in lineage if isinstance(item, dict)}
    if not paths <= lineage_paths:
        raise DataContractError("MONITORING_LINEAGE_TARGETS_MISSING")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"MONITORING_OUTPUT_MISSING: {evidence['path']}")
    if int(evidence["file_size_bytes"]) != path.stat().st_size:
        raise DataContractError(f"MONITORING_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"MONITORING_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if int(evidence["row_count"]) != row_count:
            raise DataContractError(f"MONITORING_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


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
        raise DataContractError(f"MONITORING_JSON_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("Monitoring manifest contains machine-specific absolute paths")
