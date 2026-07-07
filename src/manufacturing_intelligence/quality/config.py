"""Configuration loading for quality analytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_MODELS = {"robust_zscore", "isolation_forest"}
SUPPORTED_CENTER_LINES = {"mean"}
SUPPORTED_DISPERSION = {"standard_deviation"}


@dataclass(frozen=True)
class QualitySettings:
    """Quality analytics input and output settings."""

    quality_checks_path: Path
    production_events_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    ingestion_lineage_path: Path
    output_directory: Path
    quality_alerts_path: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    timestamp_field: str
    primary_key: str
    trend_grain: tuple[str, ...]
    alert_grain: tuple[str, ...]


@dataclass(frozen=True)
class SpecificationSettings:
    """Specification-limit settings."""

    use_record_limits: bool
    warning_margin_fraction: float
    near_limit_margin_fraction: float


@dataclass(frozen=True)
class SpcSettings:
    """SPC settings."""

    enabled: bool
    baseline_minimum_observations: int
    center_line_method: str
    dispersion_method: str
    control_limit_sigma: float
    enable_rule_1: bool
    enable_rule_2: bool
    enable_rule_3: bool
    enable_rule_4: bool
    minimum_series_length: int


@dataclass(frozen=True)
class CapabilitySettings:
    """Process-capability settings."""

    enabled: bool
    minimum_observations: int
    calculate_cp: bool
    calculate_cpk: bool


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
    """Quality-risk scoring settings."""

    specification_failure_weight: float
    spc_signal_weight: float
    anomaly_score_weight: float
    defect_severity_weight: float
    high_threshold: float
    critical_threshold: float


@dataclass(frozen=True)
class ReportingSettings:
    """Quality report settings."""

    maximum_alert_examples: int
    maximum_pareto_categories: int
    write_markdown_report: bool


@dataclass(frozen=True)
class QualityConfig:
    """Complete quality analytics configuration."""

    config_path: Path
    quality: QualitySettings
    specification: SpecificationSettings
    spc: SpcSettings
    capability: CapabilitySettings
    anomaly_detection: AnomalySettings
    risk_scoring: RiskSettings
    reporting: ReportingSettings


def load_quality_config(config_path: Path | None = None) -> QualityConfig:
    """Load and validate quality analytics configuration."""
    path = config_path or project_root() / "configs" / "quality.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Quality config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Quality config must contain a mapping")

    quality = _section(payload, "quality")
    specification = _section(payload, "specification")
    spc = _section(payload, "spc")
    capability = _section(payload, "capability")
    anomaly = _section(payload, "anomaly_detection")
    risk = _section(payload, "risk_scoring")
    reporting = _section(payload, "reporting")

    models = tuple(_str_list(anomaly, "models"))
    unsupported = sorted(set(models) - SUPPORTED_MODELS)
    if unsupported:
        raise ConfigurationError(f"Unsupported quality anomaly models: {unsupported}")
    center = _required_str(spc, "center_line_method")
    dispersion = _required_str(spc, "dispersion_method")
    if center not in SUPPORTED_CENTER_LINES:
        raise ConfigurationError(f"Unsupported SPC center-line method: {center}")
    if dispersion not in SUPPORTED_DISPERSION:
        raise ConfigurationError(f"Unsupported SPC dispersion method: {dispersion}")

    weights = [
        _non_negative_number(risk, "specification_failure_weight"),
        _non_negative_number(risk, "spc_signal_weight"),
        _non_negative_number(risk, "anomaly_score_weight"),
        _non_negative_number(risk, "defect_severity_weight"),
    ]
    if abs(sum(weights) - 1.0) > 0.000001:
        raise ConfigurationError("Quality risk weights must sum to 1.0")
    high_threshold = _non_negative_number(risk, "high_threshold")
    critical_threshold = _non_negative_number(risk, "critical_threshold")
    if critical_threshold <= high_threshold:
        raise ConfigurationError("critical_threshold must exceed high_threshold")

    quality_path = resolve_project_path(_required_str(quality, "quality_checks_path"))
    production_path = resolve_project_path(_required_str(quality, "production_events_path"))
    output_directory = resolve_project_path(_required_str(quality, "output_directory"))
    alerts_path = resolve_project_path(_required_str(quality, "quality_alerts_path"))
    report_directory = resolve_project_path(_required_str(quality, "report_directory"))
    for input_path in (quality_path, production_path):
        if input_path == output_directory or input_path in output_directory.parents:
            raise ConfigurationError("quality.output_directory must not overlap inputs")
        if input_path == alerts_path:
            raise ConfigurationError("quality.quality_alerts_path must not overwrite inputs")

    contamination = _number(anomaly, "contamination")
    if not 0 < contamination < 0.5:
        raise ConfigurationError("anomaly_detection.contamination must be between 0 and 0.5")

    return QualityConfig(
        config_path=path.resolve(),
        quality=QualitySettings(
            quality_checks_path=quality_path,
            production_events_path=production_path,
            ingestion_manifest_path=resolve_project_path(
                _required_str(quality, "ingestion_manifest_path")
            ),
            validation_summary_path=resolve_project_path(
                _required_str(quality, "validation_summary_path")
            ),
            data_quality_report_path=resolve_project_path(
                _required_str(quality, "data_quality_report_path")
            ),
            ingestion_lineage_path=resolve_project_path(
                _required_str(quality, "ingestion_lineage_path")
            ),
            output_directory=output_directory,
            quality_alerts_path=alerts_path,
            report_directory=report_directory,
            overwrite=_required_bool(quality, "overwrite"),
            random_seed=_positive_int(quality, "random_seed"),
            timestamp_field=_required_str(quality, "timestamp_field"),
            primary_key=_required_str(quality, "primary_key"),
            trend_grain=tuple(_str_list(quality, "trend_grain")),
            alert_grain=tuple(_str_list(quality, "alert_grain")),
        ),
        specification=SpecificationSettings(
            use_record_limits=_required_bool(specification, "use_record_limits"),
            warning_margin_fraction=_non_negative_number(specification, "warning_margin_fraction"),
            near_limit_margin_fraction=_non_negative_number(
                specification, "near_limit_margin_fraction"
            ),
        ),
        spc=SpcSettings(
            enabled=_required_bool(spc, "enabled"),
            baseline_minimum_observations=_positive_int(spc, "baseline_minimum_observations"),
            center_line_method=center,
            dispersion_method=dispersion,
            control_limit_sigma=_positive_number(spc, "control_limit_sigma"),
            enable_rule_1=_required_bool(spc, "enable_rule_1"),
            enable_rule_2=_required_bool(spc, "enable_rule_2"),
            enable_rule_3=_required_bool(spc, "enable_rule_3"),
            enable_rule_4=_required_bool(spc, "enable_rule_4"),
            minimum_series_length=_positive_int(spc, "minimum_series_length"),
        ),
        capability=CapabilitySettings(
            enabled=_required_bool(capability, "enabled"),
            minimum_observations=_positive_int(capability, "minimum_observations"),
            calculate_cp=_required_bool(capability, "calculate_cp"),
            calculate_cpk=_required_bool(capability, "calculate_cpk"),
        ),
        anomaly_detection=AnomalySettings(
            enabled=_required_bool(anomaly, "enabled"),
            models=models,
            contamination=contamination,
            robust_zscore_threshold=_positive_number(anomaly, "robust_zscore_threshold"),
            minimum_training_rows=_positive_int(anomaly, "minimum_training_rows"),
        ),
        risk_scoring=RiskSettings(
            specification_failure_weight=weights[0],
            spc_signal_weight=weights[1],
            anomaly_score_weight=weights[2],
            defect_severity_weight=weights[3],
            high_threshold=high_threshold,
            critical_threshold=critical_threshold,
        ),
        reporting=ReportingSettings(
            maximum_alert_examples=_positive_int(reporting, "maximum_alert_examples"),
            maximum_pareto_categories=_positive_int(reporting, "maximum_pareto_categories"),
            write_markdown_report=_required_bool(reporting, "write_markdown_report"),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Quality config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Quality config string missing or invalid: {key}")
    if value.lower() in {"deploy", "deployment", "live"}:
        raise ConfigurationError("Live deployment mode is not accepted")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Quality config boolean missing or invalid: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Quality config positive integer missing or invalid: {key}")
    return value


def _positive_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value <= 0:
        raise ConfigurationError(f"Quality config positive number missing or invalid: {key}")
    return value


def _non_negative_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value < 0:
        raise ConfigurationError(f"Quality config non-negative number missing or invalid: {key}")
    return value


def _number(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, int | float):
        raise ConfigurationError(f"Quality config number missing or invalid: {key}")
    return float(value)


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Quality config string list missing or invalid: {key}")
    return value
