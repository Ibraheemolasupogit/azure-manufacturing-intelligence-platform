"""Configuration loading for dashboard outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_PAGES = {
    "executive_overview",
    "production_operations",
    "demand_forecasting",
    "inventory_and_supply_chain",
    "quality_analytics",
    "predictive_maintenance",
    "platform_monitoring",
    "operations_assistant",
}


@dataclass(frozen=True)
class DashboardSettings:
    output_directory: Path
    report_directory: Path
    dashboard_directory: Path
    overwrite: bool
    random_seed: int
    semantic_model_name: str
    currency: str
    synthetic_data_disclaimer_required: bool


@dataclass(frozen=True)
class DashboardInputs:
    production_events_path: Path
    sales_orders_path: Path
    inventory_levels_path: Path
    supplier_performance_path: Path
    quality_checks_path: Path
    equipment_health_path: Path
    demand_forecast_path: Path
    inventory_scores_path: Path
    quality_alerts_path: Path
    maintenance_predictions_path: Path
    maintenance_alerts_path: Path
    platform_health_summary_path: Path
    genai_responses_path: Path
    executive_brief_path: Path
    supply_chain_summary_path: Path
    operations_report_path: Path
    ingestion_manifest_path: Path
    ingestion_lineage_path: Path
    forecast_manifest_path: Path
    forecast_lineage_path: Path
    inventory_manifest_path: Path
    inventory_lineage_path: Path
    quality_manifest_path: Path
    quality_lineage_path: Path
    maintenance_manifest_path: Path
    maintenance_lineage_path: Path
    monitoring_manifest_path: Path
    monitoring_lineage_path: Path
    genai_manifest_path: Path
    genai_lineage_path: Path


@dataclass(frozen=True)
class DashboardValidation:
    require_non_empty_tables: bool
    require_unique_keys: bool
    require_metric_catalogue: bool
    require_visual_specs: bool
    require_lineage: bool
    require_synthetic_disclaimer: bool


@dataclass(frozen=True)
class DashboardReporting:
    write_dashboard_report: bool
    write_semantic_model_docs: bool
    maximum_visuals_per_page: int


@dataclass(frozen=True)
class DashboardConfig:
    config_path: Path
    dashboard: DashboardSettings
    inputs: DashboardInputs
    dashboard_pages: tuple[str, ...]
    validation: DashboardValidation
    reporting: DashboardReporting


def load_dashboard_config(config_path: Path | None = None) -> DashboardConfig:
    path = (
        resolve_project_path(config_path)
        if config_path
        else project_root() / "configs" / "dashboard.yaml"
    )
    if not path.is_file():
        raise ConfigurationError(f"Dashboard config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Dashboard config must contain a mapping")
    dashboard = _section(payload, "dashboard")
    inputs = _section(payload, "inputs")
    validation = _section(payload, "validation")
    reporting = _section(payload, "reporting")
    pages = tuple(_str_list(payload, "dashboard_pages"))
    unsupported = sorted(set(pages) - SUPPORTED_PAGES)
    if unsupported:
        raise ConfigurationError(f"Unsupported dashboard pages: {unsupported}")
    if len(set(pages)) != len(pages):
        raise ConfigurationError("Dashboard pages must be unique")
    output_dir = resolve_project_path(_required_str(dashboard, "output_directory"))
    input_paths = [_resolve_input(inputs, field) for field in DashboardInputs.__dataclass_fields__]
    for input_path in input_paths:
        if _is_relative_to(input_path, output_dir):
            raise ConfigurationError("Dashboard output directory must not overlap inputs")
    if ".generated" not in output_dir.parts and output_dir.name != "dashboard":
        raise ConfigurationError(
            "Dashboard output directory must be outputs/dashboard or .generated"
        )

    return DashboardConfig(
        config_path=path.resolve(),
        dashboard=DashboardSettings(
            output_directory=output_dir,
            report_directory=resolve_project_path(_required_str(dashboard, "report_directory")),
            dashboard_directory=resolve_project_path(
                _required_str(dashboard, "dashboard_directory")
            ),
            overwrite=_required_bool(dashboard, "overwrite"),
            random_seed=_positive_int(dashboard, "random_seed"),
            semantic_model_name=_required_str(dashboard, "semantic_model_name"),
            currency=_required_str(dashboard, "currency"),
            synthetic_data_disclaimer_required=_required_bool(
                dashboard, "synthetic_data_disclaimer_required"
            ),
        ),
        inputs=DashboardInputs(
            **{
                field: _resolve_input(inputs, field)
                for field in DashboardInputs.__dataclass_fields__
            }
        ),
        dashboard_pages=pages,
        validation=DashboardValidation(
            require_non_empty_tables=_required_bool(validation, "require_non_empty_tables"),
            require_unique_keys=_required_bool(validation, "require_unique_keys"),
            require_metric_catalogue=_required_bool(validation, "require_metric_catalogue"),
            require_visual_specs=_required_bool(validation, "require_visual_specs"),
            require_lineage=_required_bool(validation, "require_lineage"),
            require_synthetic_disclaimer=_required_bool(validation, "require_synthetic_disclaimer"),
        ),
        reporting=DashboardReporting(
            write_dashboard_report=_required_bool(reporting, "write_dashboard_report"),
            write_semantic_model_docs=_required_bool(reporting, "write_semantic_model_docs"),
            maximum_visuals_per_page=_positive_int(reporting, "maximum_visuals_per_page"),
        ),
    )


def semantic_config_payload(config: DashboardConfig) -> dict[str, Any]:
    return {
        "dashboard": {
            "random_seed": config.dashboard.random_seed,
            "semantic_model_name": config.dashboard.semantic_model_name,
            "currency": config.dashboard.currency,
            "synthetic_data_disclaimer_required": (
                config.dashboard.synthetic_data_disclaimer_required
            ),
        },
        "dashboard_pages": list(config.dashboard_pages),
        "validation": {
            "require_non_empty_tables": config.validation.require_non_empty_tables,
            "require_unique_keys": config.validation.require_unique_keys,
            "require_metric_catalogue": config.validation.require_metric_catalogue,
            "require_visual_specs": config.validation.require_visual_specs,
            "require_lineage": config.validation.require_lineage,
            "require_synthetic_disclaimer": config.validation.require_synthetic_disclaimer,
        },
        "reporting": {"maximum_visuals_per_page": config.reporting.maximum_visuals_per_page},
    }


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Dashboard config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    if value.lower() in {"live", "deploy", "powerbi", "fabric", "azure"}:
        raise ConfigurationError("Live dashboard deployment modes are not supported")
    return value


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


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ConfigurationError(f"Required string list missing: {key}")
    return list(value)


def _resolve_input(section: dict[str, Any], key: str) -> Path:
    return resolve_project_path(_required_str(section, key))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
