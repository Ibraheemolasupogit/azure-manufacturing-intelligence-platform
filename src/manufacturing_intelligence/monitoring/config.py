"""Configuration loading for local monitoring and observability."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_DOMAINS = {
    "generation",
    "ingestion",
    "forecasting",
    "inventory",
    "quality",
    "maintenance",
}


@dataclass(frozen=True)
class MonitoringSettings:
    """Monitoring run settings."""

    output_directory: Path
    portfolio_summary_path: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    required_domains: tuple[str, ...]


@dataclass(frozen=True)
class MonitoringInputs:
    """Configured monitoring input paths."""

    generation_manifest_path: Path
    schema_metadata_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    data_quality_markdown_path: Path
    ingestion_lineage_path: Path
    forecast_manifest_path: Path
    forecast_lineage_path: Path
    demand_forecast_path: Path
    inventory_manifest_path: Path
    inventory_lineage_path: Path
    inventory_scores_path: Path
    quality_manifest_path: Path
    quality_lineage_path: Path
    quality_alerts_path: Path
    maintenance_manifest_path: Path
    maintenance_lineage_path: Path
    maintenance_predictions_path: Path


@dataclass(frozen=True)
class MonitoringThresholds:
    """Monitoring threshold settings."""

    maximum_allowed_quarantine_rate: float
    maximum_forecast_warning_count: int
    maximum_inventory_high_risk_count: int
    maximum_quality_high_risk_alerts: int
    maximum_maintenance_high_risk_alerts: int
    minimum_manifest_integrity_score: float
    minimum_lineage_completeness_score: float
    minimum_pipeline_health_score: float
    warning_score_threshold: float
    critical_score_threshold: float


@dataclass(frozen=True)
class MonitoringReporting:
    """Monitoring report settings."""

    maximum_alert_examples: int
    write_markdown_report: bool
    include_domain_sections: bool


@dataclass(frozen=True)
class MonitoringConfig:
    """Complete monitoring configuration."""

    config_path: Path
    monitoring: MonitoringSettings
    inputs: MonitoringInputs
    thresholds: MonitoringThresholds
    reporting: MonitoringReporting


def load_monitoring_config(config_path: Path | None = None) -> MonitoringConfig:
    """Load and validate monitoring configuration."""
    path = config_path or project_root() / "configs" / "monitoring.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Monitoring config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Monitoring config must contain a mapping")
    monitoring = _section(payload, "monitoring")
    inputs = _section(payload, "inputs")
    thresholds = _section(payload, "thresholds")
    reporting = _section(payload, "reporting")

    required_domains = tuple(_str_list(monitoring, "required_domains"))
    unsupported = sorted(set(required_domains) - SUPPORTED_DOMAINS)
    if unsupported:
        raise ConfigurationError(f"Unsupported monitoring domains: {unsupported}")
    if len(set(required_domains)) != len(required_domains):
        raise ConfigurationError("monitoring.required_domains must be unique")

    warning_threshold = _score(thresholds, "warning_score_threshold")
    critical_threshold = _score(thresholds, "critical_score_threshold")
    if warning_threshold <= critical_threshold:
        raise ConfigurationError("warning_score_threshold must exceed critical_score_threshold")

    output_directory = resolve_project_path(_required_str(monitoring, "output_directory"))
    portfolio_summary_path = resolve_project_path(
        _required_str(monitoring, "portfolio_summary_path")
    )
    input_paths = [_resolve_input(inputs, field) for field in MonitoringInputs.__dataclass_fields__]
    for input_path in input_paths:
        if input_path == output_directory or input_path in output_directory.parents:
            raise ConfigurationError("monitoring.output_directory must not overlap inputs")
        if input_path == portfolio_summary_path:
            raise ConfigurationError("monitoring portfolio output must not overwrite inputs")

    return MonitoringConfig(
        config_path=path.resolve(),
        monitoring=MonitoringSettings(
            output_directory=output_directory,
            portfolio_summary_path=portfolio_summary_path,
            report_directory=resolve_project_path(_required_str(monitoring, "report_directory")),
            overwrite=_required_bool(monitoring, "overwrite"),
            random_seed=_positive_int(monitoring, "random_seed"),
            required_domains=required_domains,
        ),
        inputs=MonitoringInputs(
            **{
                field: _resolve_input(inputs, field)
                for field in MonitoringInputs.__dataclass_fields__
            }
        ),
        thresholds=MonitoringThresholds(
            maximum_allowed_quarantine_rate=_fraction(
                thresholds, "maximum_allowed_quarantine_rate"
            ),
            maximum_forecast_warning_count=_non_negative_int(
                thresholds, "maximum_forecast_warning_count"
            ),
            maximum_inventory_high_risk_count=_non_negative_int(
                thresholds, "maximum_inventory_high_risk_count"
            ),
            maximum_quality_high_risk_alerts=_non_negative_int(
                thresholds, "maximum_quality_high_risk_alerts"
            ),
            maximum_maintenance_high_risk_alerts=_non_negative_int(
                thresholds, "maximum_maintenance_high_risk_alerts"
            ),
            minimum_manifest_integrity_score=_score(thresholds, "minimum_manifest_integrity_score"),
            minimum_lineage_completeness_score=_score(
                thresholds, "minimum_lineage_completeness_score"
            ),
            minimum_pipeline_health_score=_score(thresholds, "minimum_pipeline_health_score"),
            warning_score_threshold=warning_threshold,
            critical_score_threshold=critical_threshold,
        ),
        reporting=MonitoringReporting(
            maximum_alert_examples=_positive_int(reporting, "maximum_alert_examples"),
            write_markdown_report=_required_bool(reporting, "write_markdown_report"),
            include_domain_sections=_required_bool(reporting, "include_domain_sections"),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Monitoring config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    if value.lower() in {"live", "deploy", "azure"}:
        raise ConfigurationError("Live deployment modes are not supported")
    return value


def _resolve_input(section: dict[str, Any], key: str) -> Path:
    return resolve_project_path(_required_str(section, key))


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean missing: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Required positive integer missing: {key}")
    return value


def _non_negative_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"Required non-negative integer missing: {key}")
    return value


def _number(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"Required number missing: {key}")
    return float(value)


def _fraction(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if not 0 <= value <= 1:
        raise ConfigurationError(f"Threshold must be between 0 and 1: {key}")
    return value


def _score(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if not 0 <= value <= 100:
        raise ConfigurationError(f"Score threshold must be between 0 and 100: {key}")
    return value


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    values = section.get(key)
    if not isinstance(values, list) or not values:
        raise ConfigurationError(f"Required string list missing: {key}")
    if not all(isinstance(value, str) and value for value in values):
        raise ConfigurationError(f"Invalid string list: {key}")
    return values
