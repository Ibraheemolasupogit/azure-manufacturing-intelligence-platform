"""Configuration loading for predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_MODELS = {"robust_zscore", "isolation_forest"}


@dataclass(frozen=True)
class MaintenanceSettings:
    """Maintenance input and output settings."""

    equipment_health_path: Path
    production_events_path: Path
    quality_checks_path: Path
    quality_alerts_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    ingestion_lineage_path: Path
    quality_manifest_path: Path
    output_directory: Path
    portfolio_predictions_path: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    timestamp_field: str
    primary_key: str


@dataclass(frozen=True)
class ThresholdSettings:
    """Sensor threshold settings."""

    use_record_thresholds: bool
    warning_margin_fraction: float
    critical_margin_fraction: float


@dataclass(frozen=True)
class DegradationSettings:
    """Degradation feature settings."""

    enabled: bool
    rolling_windows: tuple[int, ...]
    minimum_observations: int
    trend_method: str
    rising_risk_sensor_types: tuple[str, ...]
    falling_risk_sensor_types: tuple[str, ...]


@dataclass(frozen=True)
class AnomalySettings:
    """Anomaly-detection settings."""

    enabled: bool
    models: tuple[str, ...]
    contamination: float
    robust_zscore_threshold: float
    minimum_training_rows: int


@dataclass(frozen=True)
class RiskSettings:
    """Maintenance risk-scoring settings."""

    threshold_breach_weight: float
    anomaly_weight: float
    degradation_weight: float
    runtime_weight: float
    maintenance_state_weight: float
    production_context_weight: float
    high_threshold: float
    critical_threshold: float


@dataclass(frozen=True)
class RecommendationSettings:
    """Maintenance recommendation settings."""

    maximum_alert_examples: int
    create_machine_summary: bool
    create_sensor_summary: bool
    include_quality_context: bool
    include_production_context: bool


@dataclass(frozen=True)
class MaintenanceConfig:
    """Complete predictive-maintenance configuration."""

    config_path: Path
    maintenance: MaintenanceSettings
    thresholds: ThresholdSettings
    degradation: DegradationSettings
    anomaly_detection: AnomalySettings
    risk_scoring: RiskSettings
    recommendations: RecommendationSettings


def load_maintenance_config(config_path: Path | None = None) -> MaintenanceConfig:
    """Load and validate predictive-maintenance configuration."""
    path = config_path or project_root() / "configs" / "maintenance.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Maintenance config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Maintenance config must contain a mapping")

    maintenance = _section(payload, "maintenance")
    thresholds = _section(payload, "thresholds")
    degradation = _section(payload, "degradation")
    anomaly = _section(payload, "anomaly_detection")
    risk = _section(payload, "risk_scoring")
    recommendations = _section(payload, "recommendations")

    models = tuple(_str_list(anomaly, "models"))
    unsupported = sorted(set(models) - SUPPORTED_MODELS)
    if unsupported:
        raise ConfigurationError(f"Unsupported maintenance anomaly models: {unsupported}")
    contamination = _number(anomaly, "contamination")
    if not 0 < contamination < 0.5:
        raise ConfigurationError("anomaly_detection.contamination must be between 0 and 0.5")
    robust_threshold = _positive_number(anomaly, "robust_zscore_threshold")
    rolling_windows = tuple(sorted(set(_positive_int_list(degradation, "rolling_windows"))))
    if len(rolling_windows) != len(_positive_int_list(degradation, "rolling_windows")):
        raise ConfigurationError("degradation.rolling_windows must be unique")
    if _required_str(degradation, "trend_method") != "slope":
        raise ConfigurationError("Only slope degradation trend_method is supported")

    weights = [
        _non_negative_number(risk, "threshold_breach_weight"),
        _non_negative_number(risk, "anomaly_weight"),
        _non_negative_number(risk, "degradation_weight"),
        _non_negative_number(risk, "runtime_weight"),
        _non_negative_number(risk, "maintenance_state_weight"),
        _non_negative_number(risk, "production_context_weight"),
    ]
    if abs(sum(weights) - 1.0) > 0.000001:
        raise ConfigurationError("Maintenance risk weights must sum to 1.0")
    high_threshold = _non_negative_number(risk, "high_threshold")
    critical_threshold = _non_negative_number(risk, "critical_threshold")
    if critical_threshold <= high_threshold:
        raise ConfigurationError("risk_scoring.critical_threshold must exceed high_threshold")

    equipment_path = resolve_project_path(_required_str(maintenance, "equipment_health_path"))
    production_path = resolve_project_path(_required_str(maintenance, "production_events_path"))
    output_directory = resolve_project_path(_required_str(maintenance, "output_directory"))
    portfolio_path = resolve_project_path(_required_str(maintenance, "portfolio_predictions_path"))
    report_directory = resolve_project_path(_required_str(maintenance, "report_directory"))
    for input_path in (equipment_path, production_path):
        if input_path == output_directory or input_path in output_directory.parents:
            raise ConfigurationError("maintenance.output_directory must not overlap inputs")
        if input_path == portfolio_path:
            raise ConfigurationError("portfolio output must not overwrite inputs")
    if "data/raw" in equipment_path.as_posix() or "data/raw" in production_path.as_posix():
        raise ConfigurationError("Maintenance must use governed accepted inputs, not data/raw")

    return MaintenanceConfig(
        config_path=path.resolve(),
        maintenance=MaintenanceSettings(
            equipment_health_path=equipment_path,
            production_events_path=production_path,
            quality_checks_path=resolve_project_path(
                _required_str(maintenance, "quality_checks_path")
            ),
            quality_alerts_path=resolve_project_path(
                _required_str(maintenance, "quality_alerts_path")
            ),
            ingestion_manifest_path=resolve_project_path(
                _required_str(maintenance, "ingestion_manifest_path")
            ),
            validation_summary_path=resolve_project_path(
                _required_str(maintenance, "validation_summary_path")
            ),
            data_quality_report_path=resolve_project_path(
                _required_str(maintenance, "data_quality_report_path")
            ),
            ingestion_lineage_path=resolve_project_path(
                _required_str(maintenance, "ingestion_lineage_path")
            ),
            quality_manifest_path=resolve_project_path(
                _required_str(maintenance, "quality_manifest_path")
            ),
            output_directory=output_directory,
            portfolio_predictions_path=portfolio_path,
            report_directory=report_directory,
            overwrite=_required_bool(maintenance, "overwrite"),
            random_seed=_positive_int(maintenance, "random_seed"),
            timestamp_field=_required_str(maintenance, "timestamp_field"),
            primary_key=_required_str(maintenance, "primary_key"),
        ),
        thresholds=ThresholdSettings(
            use_record_thresholds=_required_bool(thresholds, "use_record_thresholds"),
            warning_margin_fraction=_non_negative_number(thresholds, "warning_margin_fraction"),
            critical_margin_fraction=_non_negative_number(thresholds, "critical_margin_fraction"),
        ),
        degradation=DegradationSettings(
            enabled=_required_bool(degradation, "enabled"),
            rolling_windows=rolling_windows,
            minimum_observations=_positive_int(degradation, "minimum_observations"),
            trend_method="slope",
            rising_risk_sensor_types=tuple(_str_list(degradation, "rising_risk_sensor_types")),
            falling_risk_sensor_types=tuple(_str_list(degradation, "falling_risk_sensor_types")),
        ),
        anomaly_detection=AnomalySettings(
            enabled=_required_bool(anomaly, "enabled"),
            models=models,
            contamination=contamination,
            robust_zscore_threshold=robust_threshold,
            minimum_training_rows=_positive_int(anomaly, "minimum_training_rows"),
        ),
        risk_scoring=RiskSettings(
            threshold_breach_weight=weights[0],
            anomaly_weight=weights[1],
            degradation_weight=weights[2],
            runtime_weight=weights[3],
            maintenance_state_weight=weights[4],
            production_context_weight=weights[5],
            high_threshold=high_threshold,
            critical_threshold=critical_threshold,
        ),
        recommendations=RecommendationSettings(
            maximum_alert_examples=_positive_int(recommendations, "maximum_alert_examples"),
            create_machine_summary=_required_bool(recommendations, "create_machine_summary"),
            create_sensor_summary=_required_bool(recommendations, "create_sensor_summary"),
            include_quality_context=_required_bool(recommendations, "include_quality_context"),
            include_production_context=_required_bool(
                recommendations, "include_production_context"
            ),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Maintenance config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    if value.lower() in {"live", "deploy", "azure"}:
        raise ConfigurationError("Live deployment modes are not supported")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean missing: {key}")
    return value


def _number(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"Required number missing: {key}")
    return float(value)


def _non_negative_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value < 0:
        raise ConfigurationError(f"Number must be non-negative: {key}")
    return value


def _positive_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value <= 0:
        raise ConfigurationError(f"Number must be positive: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Required positive integer missing: {key}")
    return value


def _positive_int_list(section: dict[str, Any], key: str) -> list[int]:
    values = section.get(key)
    if not isinstance(values, list) or not values:
        raise ConfigurationError(f"Required integer list missing: {key}")
    result: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ConfigurationError(f"Invalid positive integer in {key}")
        result.append(value)
    return result


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    values = section.get(key)
    if not isinstance(values, list) or not values:
        raise ConfigurationError(f"Required string list missing: {key}")
    if not all(isinstance(value, str) and value for value in values):
        raise ConfigurationError(f"Invalid string list: {key}")
    return values
