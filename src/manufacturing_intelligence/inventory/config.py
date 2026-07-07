"""Configuration loading for inventory intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_DECISION_GRAINS = {
    ("warehouse_id", "item_id"),
    ("warehouse_id", "product_id"),
    ("warehouse_id", "material_id"),
}
SUPPORTED_SCENARIOS = {
    "baseline",
    "high_demand",
    "supplier_delay",
    "budget_constrained",
    "capacity_constrained",
}


@dataclass(frozen=True)
class InventorySettings:
    """Inventory runtime settings."""

    inventory_path: Path
    supplier_path: Path
    movements_path: Path
    sales_orders_path: Path
    forecast_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    ingestion_lineage_path: Path
    forecast_manifest_path: Path
    forecast_model_metadata_path: Path
    forecast_lineage_path: Path
    output_directory: Path
    inventory_scores_path: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    decision_grain: tuple[str, ...]
    planning_horizon_days: int


@dataclass(frozen=True)
class PolicySettings:
    """Inventory policy assumptions."""

    default_service_level: float
    default_lead_time_days: int
    lead_time_variability_multiplier: float
    demand_variability_multiplier: float
    review_period_days: int
    minimum_order_quantity: int
    order_multiple: int
    maximum_reorder_quantity: int
    holding_cost_rate_annual: float
    stockout_cost_multiplier: float
    excess_coverage_days: int
    critical_coverage_days: int
    expiry_warning_days: int
    supplier_risk_adjustment_enabled: bool
    supplier_safety_stock_adjustment_cap: float
    material_usage_window_days: int
    default_material_daily_usage: float


@dataclass(frozen=True)
class OptimisationSettings:
    """Deterministic constrained-allocation settings."""

    enabled: bool
    method: str
    available_budget: float
    available_replenishment_capacity: int
    objective_weights: dict[str, float]


@dataclass(frozen=True)
class ScenarioSettings:
    """Inventory scenario settings."""

    enabled: tuple[str, ...]
    high_demand_multiplier: float
    supplier_delay_multiplier: float
    budget_constrained_fraction: float
    capacity_constrained_fraction: float


@dataclass(frozen=True)
class ReportingSettings:
    """Inventory report settings."""

    write_inventory_report: bool
    write_scenario_comparison: bool
    maximum_recommendation_examples: int


@dataclass(frozen=True)
class InventoryConfig:
    """Complete inventory configuration."""

    config_path: Path
    inventory: InventorySettings
    policy: PolicySettings
    optimisation: OptimisationSettings
    scenarios: ScenarioSettings
    reporting: ReportingSettings


def load_inventory_config(config_path: Path | None = None) -> InventoryConfig:
    """Load and validate inventory YAML configuration."""
    path = config_path or project_root() / "configs" / "inventory.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Inventory config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Inventory config must contain a mapping")

    inventory = _section(payload, "inventory")
    policy = _section(payload, "policy")
    optimisation = _section(payload, "optimisation")
    scenarios = _section(payload, "scenarios")
    reporting = _section(payload, "reporting")

    decision_grain = tuple(_str_list(inventory, "decision_grain"))
    if decision_grain not in SUPPORTED_DECISION_GRAINS:
        raise ConfigurationError(f"inventory.decision_grain is unsupported: {decision_grain}")
    enabled_scenarios = tuple(_str_list(scenarios, "enabled"))
    unsupported = sorted(set(enabled_scenarios) - SUPPORTED_SCENARIOS)
    if unsupported:
        raise ConfigurationError(f"scenarios.enabled contains unsupported scenarios: {unsupported}")
    objective_weights = _number_dict(optimisation, "objective_weights")
    weight_sum = sum(objective_weights.values())
    if any(value < 0 for value in objective_weights.values()):
        raise ConfigurationError("optimisation.objective_weights must be non-negative")
    if abs(weight_sum - 1.0) > 0.000001:
        raise ConfigurationError("optimisation.objective_weights must sum to 1.0")

    output_directory = resolve_project_path(_required_str(inventory, "output_directory"))
    inventory_scores_path = resolve_project_path(_required_str(inventory, "inventory_scores_path"))
    input_paths = [
        resolve_project_path(_required_str(inventory, key))
        for key in (
            "inventory_path",
            "supplier_path",
            _path_key(inventory, "movements_path", "warehouse_movements_path"),
            "sales_orders_path",
            "forecast_path",
        )
    ]
    for input_path in input_paths:
        if input_path == output_directory or input_path in output_directory.parents:
            raise ConfigurationError("inventory.output_directory must not overwrite inputs")
        if input_path == inventory_scores_path:
            raise ConfigurationError("inventory.inventory_scores_path must not overwrite inputs")

    return InventoryConfig(
        config_path=path.resolve(),
        inventory=InventorySettings(
            inventory_path=input_paths[0],
            supplier_path=input_paths[1],
            movements_path=input_paths[2],
            sales_orders_path=input_paths[3],
            forecast_path=input_paths[4],
            ingestion_manifest_path=resolve_project_path(
                _required_str(inventory, "ingestion_manifest_path")
            ),
            validation_summary_path=resolve_project_path(
                _required_str(inventory, "validation_summary_path")
            ),
            data_quality_report_path=resolve_project_path(
                _required_str(inventory, "data_quality_report_path")
            ),
            ingestion_lineage_path=resolve_project_path(
                _required_str(inventory, "ingestion_lineage_path")
            ),
            forecast_manifest_path=resolve_project_path(
                _required_str(inventory, "forecast_manifest_path")
            ),
            forecast_model_metadata_path=resolve_project_path(
                _required_str(inventory, "forecast_model_metadata_path")
            ),
            forecast_lineage_path=resolve_project_path(
                _required_str(inventory, "forecast_lineage_path")
            ),
            output_directory=output_directory,
            inventory_scores_path=inventory_scores_path,
            report_directory=resolve_project_path(_required_str(inventory, "report_directory")),
            overwrite=_required_bool(inventory, "overwrite"),
            random_seed=_positive_int(inventory, "random_seed"),
            decision_grain=decision_grain,
            planning_horizon_days=_positive_int(inventory, "planning_horizon_days"),
        ),
        policy=PolicySettings(
            default_service_level=_probability(policy, "default_service_level"),
            default_lead_time_days=_positive_int(policy, "default_lead_time_days"),
            lead_time_variability_multiplier=_non_negative_number(
                policy, "lead_time_variability_multiplier"
            ),
            demand_variability_multiplier=_non_negative_number(
                policy, "demand_variability_multiplier"
            ),
            review_period_days=_non_negative_int(policy, "review_period_days"),
            minimum_order_quantity=_non_negative_int(policy, "minimum_order_quantity"),
            order_multiple=_positive_int(policy, "order_multiple"),
            maximum_reorder_quantity=_positive_int(policy, "maximum_reorder_quantity"),
            holding_cost_rate_annual=_non_negative_number(policy, "holding_cost_rate_annual"),
            stockout_cost_multiplier=_non_negative_number(policy, "stockout_cost_multiplier"),
            excess_coverage_days=_positive_int(policy, "excess_coverage_days"),
            critical_coverage_days=_positive_int(policy, "critical_coverage_days"),
            expiry_warning_days=_positive_int(policy, "expiry_warning_days"),
            supplier_risk_adjustment_enabled=_required_bool(
                policy, "supplier_risk_adjustment_enabled"
            ),
            supplier_safety_stock_adjustment_cap=_non_negative_number(
                policy, "supplier_safety_stock_adjustment_cap"
            ),
            material_usage_window_days=_positive_int(policy, "material_usage_window_days"),
            default_material_daily_usage=_non_negative_number(
                policy, "default_material_daily_usage"
            ),
        ),
        optimisation=OptimisationSettings(
            enabled=_required_bool(optimisation, "enabled"),
            method=_required_str(optimisation, "method"),
            available_budget=_non_negative_number(optimisation, "available_budget"),
            available_replenishment_capacity=_non_negative_int(
                optimisation, "available_replenishment_capacity"
            ),
            objective_weights=objective_weights,
        ),
        scenarios=ScenarioSettings(
            enabled=enabled_scenarios,
            high_demand_multiplier=_positive_number(scenarios, "high_demand_multiplier"),
            supplier_delay_multiplier=_positive_number(scenarios, "supplier_delay_multiplier"),
            budget_constrained_fraction=_probability(scenarios, "budget_constrained_fraction"),
            capacity_constrained_fraction=_probability(scenarios, "capacity_constrained_fraction"),
        ),
        reporting=ReportingSettings(
            write_inventory_report=_required_bool(reporting, "write_inventory_report"),
            write_scenario_comparison=_required_bool(reporting, "write_scenario_comparison"),
            maximum_recommendation_examples=_positive_int(
                reporting, "maximum_recommendation_examples"
            ),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Inventory config section missing or invalid: {key}")
    return value


def _path_key(section: dict[str, Any], primary: str, fallback: str) -> str:
    return primary if primary in section else fallback


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Inventory config string missing or invalid: {key}")
    if value.lower() in {"deploy", "deployment", "live"}:
        raise ConfigurationError("Live deployment mode is not accepted")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Inventory config boolean missing or invalid: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Inventory config positive integer missing or invalid: {key}")
    return value


def _non_negative_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"Inventory config non-negative integer missing or invalid: {key}")
    return value


def _positive_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value <= 0:
        raise ConfigurationError(f"Inventory config positive number missing or invalid: {key}")
    return value


def _non_negative_number(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if value < 0:
        raise ConfigurationError(f"Inventory config non-negative number missing or invalid: {key}")
    return value


def _number(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, int | float):
        raise ConfigurationError(f"Inventory config number missing or invalid: {key}")
    return float(value)


def _probability(section: dict[str, Any], key: str) -> float:
    value = _number(section, key)
    if not 0 < value < 1:
        raise ConfigurationError(f"Inventory config probability must be between 0 and 1: {key}")
    return value


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Inventory config string list missing or invalid: {key}")
    return value


def _number_dict(section: dict[str, Any], key: str) -> dict[str, float]:
    value = section.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Inventory config number mapping missing or invalid: {key}")
    result: dict[str, float] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, int | float):
            raise ConfigurationError(f"Inventory config number mapping invalid: {key}")
        result[item_key] = float(item_value)
    return result
