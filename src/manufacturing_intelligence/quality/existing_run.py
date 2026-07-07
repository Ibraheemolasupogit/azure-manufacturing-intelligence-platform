"""Existing quality-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.quality.config import load_quality_config
from manufacturing_intelligence.quality.control_charts import VALID_RULES
from manufacturing_intelligence.quality.manifest import manifest_hash, quality_run_id

REQUIRED_OUTPUTS = {
    "quality_observations",
    "quality_kpis",
    "defect_pareto",
    "process_capability",
    "control_chart_points",
    "spc_signals",
    "anomaly_scores",
    "quality_alerts",
    "portfolio_quality_alerts",
    "quality_risk_summary",
    "quality_diagnostics",
    "quality_analytics_report",
    "quality_alert_summary",
}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing quality analytics run without rescoring."""
    config = load_quality_config(config_path)
    output_dir = output_directory.resolve() if output_directory else config.quality.output_directory
    manifest_path = output_dir / "quality-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("QUALITY_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("QUALITY_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files", {})
    if not isinstance(outputs, dict):
        raise DataContractError("QUALITY_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"QUALITY_MANIFEST_OUTPUTS_MISSING: {missing}")
    for evidence in outputs.values():
        if isinstance(evidence, dict):
            _verify_file(output_dir, evidence)

    observations = pd.read_csv(
        _resolve_output_path(output_dir, outputs["quality_observations"]["path"])
    )
    alerts = pd.read_csv(_resolve_output_path(output_dir, outputs["quality_alerts"]["path"]))
    capability = pd.read_csv(
        _resolve_output_path(output_dir, outputs["process_capability"]["path"])
    )
    anomaly = pd.read_csv(_resolve_output_path(output_dir, outputs["anomaly_scores"]["path"]))
    spc = pd.read_csv(_resolve_output_path(output_dir, outputs["spc_signals"]["path"]))
    _validate_observations(
        observations,
        config.risk_scoring.high_threshold,
        config.risk_scoring.critical_threshold,
    )
    _validate_alerts(alerts)
    _validate_capability(capability)
    _validate_anomalies(anomaly, config.anomaly_detection.robust_zscore_threshold)
    _validate_spc(spc)
    _validate_upstream_hashes(config, manifest)
    _validate_run_identity(config, manifest)
    _validate_lineage(lineage_path, outputs)


def _validate_observations(
    observations: pd.DataFrame, high_threshold: float, critical_threshold: float
) -> None:
    if observations["inspection_id"].duplicated().any():
        raise DataContractError("QUALITY_DUPLICATE_INSPECTION_ID")
    calculated = (
        observations["measured_value"]
        .between(
            observations["lower_specification_limit"],
            observations["upper_specification_limit"],
            inclusive="both",
        )
        .map({True: "pass", False: "fail"})
    )
    if not (calculated == observations["calculated_specification_result"]).all():
        raise DataContractError("QUALITY_SPECIFICATION_FORMULA_MISMATCH")
    if not observations["quality_risk_score"].between(0, 100).all():
        raise DataContractError("QUALITY_RISK_SCORE_RANGE")
    critical = observations["quality_risk_score"] >= critical_threshold
    high = observations["quality_risk_score"].between(
        high_threshold, critical_threshold, inclusive="left"
    )
    if not (observations.loc[critical, "risk_level"] == "critical").all():
        raise DataContractError("QUALITY_RISK_LABEL_MISMATCH")
    if not (observations.loc[high, "risk_level"] == "high").all():
        raise DataContractError("QUALITY_RISK_LABEL_MISMATCH")


def _validate_alerts(alerts: pd.DataFrame) -> None:
    if alerts["alert_id"].duplicated().any():
        raise DataContractError("QUALITY_DUPLICATE_ALERT_ID")
    if alerts["quality_risk_score"].isna().any():
        raise DataContractError("QUALITY_ALERT_SCORE_MISSING")


def _validate_capability(capability: pd.DataFrame) -> None:
    calculated = capability[capability["capability_status"] == "calculated"]
    if not calculated.empty and ((calculated["cp"] < 0).any() or (calculated["cpk"].isna()).any()):
        raise DataContractError("QUALITY_CAPABILITY_INVALID")
    grouped = capability.groupby(["product_id", "quality_metric", "measurement_unit"]).size()
    if grouped.empty:
        raise DataContractError("QUALITY_CAPABILITY_GROUPS_MISSING")


def _validate_anomalies(anomaly: pd.DataFrame, threshold: float) -> None:
    expected = anomaly["robust_zscore_abs"] >= threshold
    calculated_rows = anomaly["robust_zscore_status"] == "calculated"
    if not (
        expected[calculated_rows] == anomaly.loc[calculated_rows, "robust_zscore_anomaly_flag"]
    ).all():
        raise DataContractError("QUALITY_ROBUST_Z_FLAG_MISMATCH")
    if (
        anomaly["isolation_forest_score_interpretation"]
        .str.contains("calibrated_probability")
        .any()
    ):
        raise DataContractError("QUALITY_ANOMALY_SCORE_PROBABILITY_CLAIM")


def _validate_spc(spc: pd.DataFrame) -> None:
    for codes in spc["spc_rule_codes"].fillna(""):
        unknown = sorted(set(str(codes).split(";")) - VALID_RULES - {""})
        if unknown:
            raise DataContractError(f"QUALITY_UNKNOWN_SPC_RULE: {unknown}")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    hashes = manifest["governed_input_hashes"]
    if sha256_file(config.quality.quality_checks_path) != hashes["quality_checks"]:
        raise DataContractError("QUALITY_UPSTREAM_HASH_MISMATCH: quality_checks")
    if sha256_file(config.quality.production_events_path) != hashes["production_events"]:
        raise DataContractError("QUALITY_UPSTREAM_HASH_MISMATCH: production_events")


def _validate_run_identity(config: Any, manifest: dict[str, Any]) -> None:
    stable_inputs = {
        **manifest["governed_input_hashes"],
        "ingestion_manifest": manifest_hash(config.quality.ingestion_manifest_path),
    }
    expected = quality_run_id(config, stable_inputs)
    if manifest["quality_run_id"] != expected:
        raise DataContractError("QUALITY_RUN_ID_MISMATCH")


def _validate_lineage(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("QUALITY_LINEAGE_INVALID")
    paths = {str(item["path"]) for item in outputs.values() if isinstance(item, dict)}
    lineage_paths = {str(item.get("target_path")) for item in lineage if isinstance(item, dict)}
    if not paths <= lineage_paths:
        raise DataContractError("QUALITY_LINEAGE_TARGETS_MISSING")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"QUALITY_OUTPUT_MISSING: {evidence['path']}")
    if int(evidence["file_size_bytes"]) != path.stat().st_size:
        raise DataContractError(f"QUALITY_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"QUALITY_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if int(evidence["row_count"]) != row_count:
            raise DataContractError(f"QUALITY_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


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
        raise DataContractError(f"QUALITY_JSON_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("Quality manifest contains machine-specific absolute paths")
