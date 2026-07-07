"""Inventory allocation, policy, risk, and scenario calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.inventory.config import (
    InventoryConfig,
    OptimisationSettings,
    PolicySettings,
)

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class InventoryCalculations:
    """Complete inventory calculation tables."""

    warehouse_demand: pd.DataFrame
    supplier_risk: pd.DataFrame
    policy_inputs: pd.DataFrame
    inventory_position: pd.DataFrame
    scores: pd.DataFrame
    recommendations: pd.DataFrame
    scenarios: pd.DataFrame
    diagnostics: dict[str, Any]


def service_factor(service_level: float) -> float:
    """Map service level to a documented deterministic z-score approximation."""
    if service_level >= 0.99:
        return 2.33
    if service_level >= 0.98:
        return 2.05
    if service_level >= 0.95:
        return 1.65
    if service_level >= 0.90:
        return 1.28
    return 0.84


def run_policy_calculations(
    *,
    inventory_run_id: str,
    config: InventoryConfig,
    inventory: pd.DataFrame,
    suppliers: pd.DataFrame,
    movements: pd.DataFrame,
    sales_orders: pd.DataFrame,
    forecast: pd.DataFrame,
) -> InventoryCalculations:
    """Build all deterministic inventory calculations."""
    supplier_risk = build_supplier_risk_metrics(suppliers, config.policy)
    warehouse_demand = allocate_warehouse_demand(inventory_run_id, inventory, movements, forecast)
    policy_inputs = build_policy_inputs(
        inventory, suppliers, movements, sales_orders, warehouse_demand, supplier_risk, config
    )
    inventory_position = build_inventory_position(policy_inputs)
    scores = score_inventory(inventory_position, config)
    scores.insert(0, "inventory_run_id", inventory_run_id)
    recommendations = build_recommendations(scores, config.optimisation)
    scenarios = build_scenario_results(scores, config)
    diagnostics = build_diagnostics(
        inventory, warehouse_demand, policy_inputs, scores, recommendations, scenarios, config
    )
    return InventoryCalculations(
        warehouse_demand=warehouse_demand,
        supplier_risk=supplier_risk,
        policy_inputs=policy_inputs,
        inventory_position=inventory_position,
        scores=scores,
        recommendations=recommendations,
        scenarios=scenarios,
        diagnostics=diagnostics,
    )


def allocate_warehouse_demand(
    inventory_run_id: str,
    inventory: pd.DataFrame,
    movements: pd.DataFrame,
    forecast: pd.DataFrame,
) -> pd.DataFrame:
    """Allocate product-region forecast demand to warehouses without duplicating demand."""
    product_inventory = inventory[inventory["product_or_material_type"] == "product"]
    movement_weights = _warehouse_product_weights(product_inventory, movements)
    rows: list[dict[str, Any]] = []
    ordered_forecast = forecast.sort_values(["product_id", "distribution_region", "forecast_date"])
    for record in ordered_forecast.to_dict("records"):
        product_id = str(record["product_id"])
        candidates = movement_weights.get(product_id, [])
        if not candidates:
            warehouses = sorted(
                product_inventory[product_inventory["item_id"] == product_id]["warehouse_id"]
                .astype(str)
                .unique()
            )
            candidates = [
                (warehouse, 1.0 / len(warehouses), "equal_inventory_warehouse_fallback")
                for warehouse in warehouses
            ]
        for warehouse_id, weight, method in candidates:
            rows.append(
                {
                    "inventory_run_id": inventory_run_id,
                    "forecast_run_id": record["forecast_run_id"],
                    "warehouse_id": warehouse_id,
                    "product_id": product_id,
                    "distribution_region": record["distribution_region"],
                    "forecast_date": record["forecast_date"],
                    "forecast_horizon_day": int(record["forecast_horizon_day"]),
                    "selected_model": record["selected_model"],
                    "allocated_point_forecast": float(record["point_forecast"]) * weight,
                    "allocated_lower_bound": float(record["lower_bound"]) * weight,
                    "allocated_upper_bound": float(record["upper_bound"]) * weight,
                    "allocation_method": method,
                    "allocation_weight": weight,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["product_id", "distribution_region", "forecast_date", "warehouse_id"],
        ignore_index=True,
    )


def build_supplier_risk_metrics(suppliers: pd.DataFrame, policy: PolicySettings) -> pd.DataFrame:
    """Calculate material supplier risk and lead-time evidence."""
    rows = []
    for material_id, group in suppliers.groupby("material_id"):
        lead_times = (
            pd.to_datetime(group["actual_delivery_date"]) - pd.to_datetime(group["order_date"])
        ).dt.days.astype(float)
        delay_rate = float((group["delay_days"] > 0).mean())
        on_time_rate = float(group["on_time_flag"].astype(bool).mean())
        in_full_rate = float(group["in_full_flag"].astype(bool).mean())
        rejection_rate = float(
            group["rejected_quantity"].sum() / max(group["delivered_quantity"].sum(), 1)
        )
        quality_score = float(group["quality_score"].mean())
        supplier_delay_risk = min(100.0, delay_rate * 100.0)
        supplier_quality_risk = min(
            100.0,
            max(0.0, (100.0 - quality_score) * 5.0 + rejection_rate * 100.0),
        )
        lead_time_variability = float(lead_times.std(ddof=0))
        risk_score = min(
            100.0,
            delay_rate * 35.0
            + (1.0 - in_full_rate) * 25.0
            + supplier_quality_risk * 0.25
            + min(lead_time_variability * 8.0, 15.0),
        )
        rows.append(
            {
                "material_id": str(material_id),
                "supplier_observation_count": len(group),
                "average_lead_time_days": float(lead_times.mean()),
                "median_lead_time_days": float(lead_times.median()),
                "lead_time_std_days": lead_time_variability,
                "delay_rate": delay_rate,
                "on_time_rate": on_time_rate,
                "in_full_rate": in_full_rate,
                "supplier_quality_score": quality_score,
                "rejection_rate": rejection_rate,
                "supplier_delay_risk_score": supplier_delay_risk,
                "supplier_quality_risk_score": supplier_quality_risk,
                "supplier_risk_score": risk_score,
                "lead_time_source": "observed_supplier_history"
                if len(group) >= 2
                else "configured_default",
                "policy_default_lead_time_days": policy.default_lead_time_days,
            }
        )
    return pd.DataFrame(rows).sort_values("material_id", ignore_index=True)


def build_policy_inputs(
    inventory: pd.DataFrame,
    suppliers: pd.DataFrame,
    movements: pd.DataFrame,
    sales_orders: pd.DataFrame,
    warehouse_demand: pd.DataFrame,
    supplier_risk: pd.DataFrame,
    config: InventoryConfig,
) -> pd.DataFrame:
    """Build item-location policy inputs from governed sources."""
    movement_context = _movement_context(movements)
    allocated = warehouse_demand.groupby(["warehouse_id", "product_id"]).agg(
        forecast_demand=("allocated_point_forecast", "sum"),
        forecast_lower_bound=("allocated_lower_bound", "sum"),
        forecast_upper_bound=("allocated_upper_bound", "sum"),
        forecast_record_count=("forecast_date", "count"),
    )
    variability = _historical_demand_variability(sales_orders, config)
    material_usage = _material_usage(movements, config.policy)
    supplier_by_material = supplier_risk.set_index("material_id").to_dict("index")
    rows: list[dict[str, Any]] = []
    for record in inventory.sort_values(["warehouse_id", "item_id"]).to_dict("records"):
        item_id = str(record["item_id"])
        warehouse_id = str(record["warehouse_id"])
        item_type = "product" if record["product_or_material_type"] == "product" else "material"
        is_product = item_type == "product"
        key = (warehouse_id, item_id)
        demand_row = allocated.loc[key].to_dict() if is_product and key in allocated.index else {}
        horizon_demand = float(demand_row.get("forecast_demand", 0.0))
        average_daily_demand = horizon_demand / config.inventory.planning_horizon_days
        upper_horizon_demand = float(demand_row.get("forecast_upper_bound", horizon_demand))
        if not is_product:
            average_daily_demand = float(material_usage.get(key, 0.0))
            horizon_demand = average_daily_demand * config.inventory.planning_horizon_days
            upper_horizon_demand = horizon_demand
        variability_row = variability.get(item_id, {})
        demand_std = float(variability_row.get("demand_standard_deviation", 0.0))
        variability_source = str(
            variability_row.get("demand_variability_source", "configured_fallback")
        )
        if demand_std == 0.0 and average_daily_demand > 0:
            demand_std = max(
                1.0,
                average_daily_demand * config.policy.demand_variability_multiplier * 0.25,
            )
            variability_source = "configured_fallback"
        supplier = supplier_by_material.get(item_id, {})
        lead_time = (
            float(supplier.get("average_lead_time_days", config.policy.default_lead_time_days))
            if not is_product
            else float(record["lead_time_days"] or config.policy.default_lead_time_days)
        )
        lead_time_std = float(supplier.get("lead_time_std_days", 0.0)) if not is_product else 0.0
        lead_time_source = (
            str(supplier.get("lead_time_source", "configured_default"))
            if not is_product
            else "configured_finished_goods_assumption"
        )
        supplier_risk_score = (
            float(supplier.get("supplier_risk_score", 0.0)) if not is_product else 0.0
        )
        inbound = movement_context.get(key, {}).get("receipt", 0.0)
        outbound = movement_context.get(key, {}).get("issue_to_production", 0.0)
        transfer = movement_context.get(key, {}).get("transfer", 0.0)
        adjustment = movement_context.get(key, {}).get("adjustment", 0.0)
        rows.append(
            {
                "warehouse_id": warehouse_id,
                "plant_id": record["plant_id"],
                "item_id": item_id,
                "product_id": item_id if is_product else "",
                "material_id": "" if is_product else item_id,
                "item_type": item_type,
                "snapshot_timestamp": record["snapshot_timestamp"],
                "on_hand_quantity": int(record["on_hand_quantity"]),
                "reserved_quantity": int(record["reserved_quantity"]),
                "available_quantity": int(record["available_quantity"]),
                "inbound_quantity": inbound,
                "outbound_quantity": outbound,
                "transfer_quantity": transfer,
                "adjustment_quantity": adjustment,
                "unit_cost": float(record["unit_cost"]),
                "inventory_value": float(record["inventory_value"]),
                "forecast_demand": horizon_demand,
                "forecast_upper_bound_demand": upper_horizon_demand,
                "average_daily_demand": average_daily_demand,
                "demand_standard_deviation": demand_std,
                "demand_variability_source": variability_source,
                "lead_time_days": lead_time,
                "lead_time_std_days": lead_time_std,
                "lead_time_source": lead_time_source,
                "supplier_risk_score": supplier_risk_score,
                "supplier_delay_risk_score": float(supplier.get("supplier_delay_risk_score", 0.0)),
                "supplier_quality_risk_score": float(
                    supplier.get("supplier_quality_risk_score", 0.0)
                ),
                "current_reorder_point": int(record["reorder_point"]),
                "current_safety_stock_quantity": int(record["safety_stock_quantity"]),
                "expiry_date": "" if pd.isna(record["expiry_date"]) else record["expiry_date"],
                "synthetic_data_flag": True,
            }
        )
    return pd.DataFrame(rows).sort_values(["warehouse_id", "item_id"], ignore_index=True)


def build_inventory_position(policy_inputs: pd.DataFrame) -> pd.DataFrame:
    """Calculate inventory-position terms."""
    position = policy_inputs.copy()
    position["committed_outbound_quantity"] = position["outbound_quantity"]
    position["inventory_position"] = (
        position["on_hand_quantity"]
        + position["inbound_quantity"]
        - position["reserved_quantity"]
        - position["committed_outbound_quantity"]
    )
    return position


def score_inventory(position: pd.DataFrame, config: InventoryConfig) -> pd.DataFrame:
    """Calculate safety stock, reorder, risk scores, and explanation fields."""
    rows = []
    z_score = service_factor(config.policy.default_service_level)
    for record in position.to_dict("records"):
        demand_std = float(record["demand_standard_deviation"])
        lead_time = max(float(record["lead_time_days"]), 1.0)
        supplier_multiplier = 1.0
        if config.policy.supplier_risk_adjustment_enabled:
            supplier_multiplier += min(
                config.policy.supplier_safety_stock_adjustment_cap,
                float(record["supplier_risk_score"]) / 100.0,
            )
        pre_safety = z_score * demand_std * math.sqrt(lead_time) * supplier_multiplier
        safety_stock = max(0, math.ceil(pre_safety))
        lead_time_demand = float(record["average_daily_demand"]) * lead_time
        review_period_demand = (
            float(record["average_daily_demand"]) * config.policy.review_period_days
        )
        reorder_point = math.ceil(lead_time_demand + safety_stock)
        target_stock_level = reorder_point + review_period_demand
        reorder_point_gap = max(0.0, reorder_point - float(record["inventory_position"]))
        unconstrained = reorder_quantity(
            target_stock_level - float(record["inventory_position"]),
            config.policy,
        )
        projected_end = (
            float(record["inventory_position"]) - float(record["forecast_demand"]) + unconstrained
        )
        expected_shortage = max(
            0.0,
            float(record["forecast_demand"]) - float(record["inventory_position"]),
        )
        pessimistic_shortage = max(
            0.0,
            float(record["forecast_upper_bound_demand"]) - float(record["inventory_position"]),
        )
        days_of_supply = safe_days_of_supply(
            float(record["inventory_position"]), float(record["average_daily_demand"])
        )
        shortage_quantity = expected_shortage
        excess_quantity = max(
            0.0,
            float(record["inventory_position"])
            - float(record["average_daily_demand"]) * config.policy.excess_coverage_days,
        )
        expiry = expiry_metrics(
            str(record["expiry_date"]),
            str(record["snapshot_timestamp"]),
            float(record["inventory_position"]),
            float(record["average_daily_demand"]),
            float(record["unit_cost"]),
            config.policy.expiry_warning_days,
        )
        stockout_score = min(
            100.0,
            (pessimistic_shortage / max(float(record["forecast_upper_bound_demand"]), 1.0) * 70.0)
            + min(float(record["supplier_risk_score"]) * 0.30, 30.0),
        )
        excess_score = min(
            100.0,
            excess_quantity / max(float(record["on_hand_quantity"]), 1.0) * 100.0,
        )
        working_capital = float(record["on_hand_quantity"]) * float(record["unit_cost"])
        working_capital_score = min(100.0, working_capital / 1000.0)
        expiry_score = expiry["expiry_risk_score"]
        priority = min(
            100.0,
            stockout_score * 0.50
            + float(record["supplier_risk_score"]) * 0.15
            + expiry_score * 0.10
            + working_capital_score * 0.15
            + excess_score * 0.10,
        )
        level = priority_level(priority)
        action, reason = recommendation_reason(
            stockout_score, excess_score, expiry_score, unconstrained, level
        )
        rows.append(
            {
                **record,
                "service_level": config.policy.default_service_level,
                "service_level_z_score": z_score,
                "demand_uncertainty": demand_std,
                "lead_time_uncertainty": float(record["lead_time_std_days"])
                * config.policy.lead_time_variability_multiplier,
                "safety_stock_pre_rounded": pre_safety,
                "safety_stock": safety_stock,
                "recommended_safety_stock_quantity": safety_stock,
                "safety_stock_source": record["demand_variability_source"],
                "lead_time_demand": lead_time_demand,
                "review_period_demand": review_period_demand,
                "reorder_point": reorder_point,
                "recommended_reorder_point": reorder_point,
                "target_stock_level": target_stock_level,
                "reorder_point_gap": reorder_point_gap,
                "unconstrained_reorder_quantity": unconstrained,
                "recommended_reorder_quantity": unconstrained,
                "projected_end_of_horizon_inventory": projected_end,
                "projected_shortage_quantity": shortage_quantity,
                "pessimistic_shortage_quantity": pessimistic_shortage,
                "projected_excess_quantity": excess_quantity,
                "days_of_supply": days_of_supply,
                "projected_coverage_days": days_of_supply,
                "safety_stock_coverage": safe_ratio(
                    float(record["inventory_position"]), safety_stock
                ),
                "stockout_exposure": pessimistic_shortage,
                "stockout_cost_exposure": pessimistic_shortage
                * float(record["unit_cost"])
                * config.policy.stockout_cost_multiplier,
                "estimated_stockout_cost": pessimistic_shortage
                * float(record["unit_cost"])
                * config.policy.stockout_cost_multiplier,
                "expected_stockout_date": expected_stockout_date(
                    str(record["snapshot_timestamp"]),
                    float(record["inventory_position"]),
                    float(record["average_daily_demand"]),
                ),
                "days_until_stockout": min(days_of_supply, 999.0),
                "service_level_exposure": max(0.0, 1.0 - days_of_supply / max(lead_time, 1.0)),
                "stockout_risk_score": stockout_score,
                "excess_risk_score": excess_score,
                "expiry_risk_score": expiry_score,
                "working_capital_risk_score": working_capital_score,
                "overall_priority_score": priority,
                "priority_score": priority,
                "priority_level": level,
                "priority_band": level,
                "priority_level_sort": PRIORITY_ORDER[level],
                "excess_stock_flag": excess_quantity > 0,
                "excess_inventory_quantity": excess_quantity,
                "excess_inventory_value": excess_quantity * float(record["unit_cost"]),
                "working_capital_exposure": working_capital,
                "annual_holding_cost_estimate": working_capital
                * config.policy.holding_cost_rate_annual,
                "inventory_turnover_proxy": safe_ratio(
                    float(record["forecast_demand"]), max(working_capital, 1.0)
                ),
                "recommended_action": action,
                "recommendation_reason": reason,
                "constraint_status": "unconstrained_pending_allocation",
                "policy_type": "rules_based_inventory_policy",
                **expiry,
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values(
        ["priority_level_sort", "overall_priority_score", "warehouse_id", "item_id"],
        ascending=[True, False, True, True],
        ignore_index=True,
    )


def build_recommendations(scores: pd.DataFrame, optimisation: OptimisationSettings) -> pd.DataFrame:
    """Apply deterministic constrained allocation and build recommendation output."""
    working = scores.copy()
    working["objective_score"] = (
        working["stockout_risk_score"] * optimisation.objective_weights["stockout_risk"]
        + (working["service_level"] * 100.0) * optimisation.objective_weights["service_level"]
        + (100.0 - working["working_capital_risk_score"])
        * optimisation.objective_weights["working_capital"]
        + (100.0 - working["supplier_risk_score"]) * optimisation.objective_weights["supplier_risk"]
    )
    working = working.sort_values(
        ["priority_level_sort", "objective_score", "warehouse_id", "item_id"],
        ascending=[True, False, True, True],
        ignore_index=True,
    )
    budget_remaining = optimisation.available_budget
    capacity_remaining = float(optimisation.available_replenishment_capacity)
    constrained_quantities = []
    statuses = []
    for record in working.to_dict("records"):
        unconstrained = int(record["unconstrained_reorder_quantity"])
        unit_cost = float(record["unit_cost"])
        quantity = unconstrained
        if unit_cost > 0:
            quantity = min(quantity, int(budget_remaining // unit_cost))
        quantity = min(quantity, int(capacity_remaining))
        quantity = max(0, quantity)
        constrained_quantities.append(quantity)
        value = quantity * unit_cost
        budget_remaining = max(0.0, budget_remaining - value)
        capacity_remaining = max(0.0, capacity_remaining - quantity)
        if quantity == unconstrained:
            statuses.append("fully_allocated")
        elif quantity == 0 and unconstrained > 0:
            statuses.append("not_allocated_constraint_binding")
        elif quantity < unconstrained:
            statuses.append("partially_allocated_constraint_binding")
        else:
            statuses.append("not_required")
    working["recommended_reorder_quantity"] = constrained_quantities
    working["constrained_reorder_quantity"] = constrained_quantities
    working["constraint_status"] = statuses
    working["recommended_reorder_value"] = (
        working["recommended_reorder_quantity"] * working["unit_cost"]
    )
    working["unmet_replenishment_quantity"] = (
        working["unconstrained_reorder_quantity"] - working["recommended_reorder_quantity"]
    )
    working["unmet_replenishment_value"] = (
        working["unmet_replenishment_quantity"] * working["unit_cost"]
    )
    action_rows = working[
        (working["recommended_action"] != "maintain_current_policy")
        | (working["unconstrained_reorder_quantity"] > 0)
    ].copy()
    return (
        action_rows[RECOMMENDATION_COLUMNS]
        .sort_values(
            ["priority_level_sort", "overall_priority_score", "warehouse_id", "item_id"],
            ascending=[True, False, True, True],
            ignore_index=True,
        )
        .drop(columns=["priority_level_sort"])
    )


def build_scenario_results(scores: pd.DataFrame, config: InventoryConfig) -> pd.DataFrame:
    """Calculate aggregate deterministic scenario results."""
    rows = []
    for scenario in config.scenarios.enabled:
        demand_multiplier = 1.0
        lead_multiplier = 1.0
        budget = config.optimisation.available_budget
        capacity = config.optimisation.available_replenishment_capacity
        if scenario == "high_demand":
            demand_multiplier = config.scenarios.high_demand_multiplier
        elif scenario == "supplier_delay":
            lead_multiplier = config.scenarios.supplier_delay_multiplier
        elif scenario == "budget_constrained":
            budget *= config.scenarios.budget_constrained_fraction
        elif scenario == "capacity_constrained":
            capacity = int(capacity * config.scenarios.capacity_constrained_fraction)
        scenario_scores = scores.copy()
        scenario_scores["scenario_demand"] = scenario_scores["forecast_demand"] * demand_multiplier
        scenario_scores["scenario_lead_time"] = scenario_scores["lead_time_days"] * lead_multiplier
        scenario_scores["scenario_shortage"] = (
            scenario_scores["scenario_demand"] - scenario_scores["inventory_position"]
        ).clip(lower=0)
        scenario_scores["scenario_excess"] = (
            scenario_scores["inventory_position"] - scenario_scores["scenario_demand"]
        ).clip(lower=0)
        unconstrained_qty = scenario_scores["unconstrained_reorder_quantity"].sum()
        constrained = _scenario_allocate(scenario_scores, budget, capacity)
        rows.append(
            {
                "scenario_name": scenario,
                "demand_multiplier": demand_multiplier,
                "lead_time_multiplier": lead_multiplier,
                "available_budget": budget,
                "available_replenishment_capacity": capacity,
                "total_unconstrained_quantity": float(unconstrained_qty),
                "total_constrained_quantity": float(constrained["quantity"]),
                "working_capital_requirement": float(constrained["value"]),
                "projected_shortage_quantity": float(scenario_scores["scenario_shortage"].sum()),
                "projected_excess_quantity": float(scenario_scores["scenario_excess"].sum()),
                "projected_service_level_risk": float(
                    (scenario_scores["stockout_risk_score"] >= 50).mean()
                ),
                "high_risk_item_count": int((scenario_scores["priority_level"] == "high").sum()),
                "critical_risk_item_count": int(
                    (scenario_scores["priority_level"] == "critical").sum()
                ),
                "budget_utilisation": safe_ratio(float(constrained["value"]), budget),
                "capacity_utilisation": safe_ratio(float(constrained["quantity"]), float(capacity)),
                "constraint_binding_count": int(constrained["binding_count"]),
            }
        )
    return pd.DataFrame(rows).sort_values("scenario_name", ignore_index=True)


def build_diagnostics(
    inventory: pd.DataFrame,
    warehouse_demand: pd.DataFrame,
    policy_inputs: pd.DataFrame,
    scores: pd.DataFrame,
    recommendations: pd.DataFrame,
    scenarios: pd.DataFrame,
    config: InventoryConfig,
) -> dict[str, Any]:
    """Build run diagnostics with fallback and mapping visibility."""
    forecast_pairs = set(
        zip(warehouse_demand["warehouse_id"], warehouse_demand["product_id"], strict=False)
    )
    product_pairs = set(
        zip(
            policy_inputs[policy_inputs["item_type"] == "product"]["warehouse_id"],
            policy_inputs[policy_inputs["item_type"] == "product"]["item_id"],
            strict=False,
        )
    )
    unmapped = sorted(
        f"{warehouse}|{product}" for warehouse, product in product_pairs - forecast_pairs
    )
    return {
        "inventory_records_processed": len(inventory),
        "product_records": int((policy_inputs["item_type"] == "product").sum()),
        "material_records": int((policy_inputs["item_type"] == "material").sum()),
        "mapped_forecast_records": len(warehouse_demand),
        "unmapped_forecast_records": 0,
        "unmapped_product_inventory_records": unmapped,
        "items_with_configured_lead_time_fallback": int(
            policy_inputs["lead_time_source"].str.contains("configured").sum()
        ),
        "items_with_configured_variability_fallback": int(
            (policy_inputs["demand_variability_source"] == "configured_fallback").sum()
        ),
        "zero_demand_items": int((policy_inputs["average_daily_demand"] == 0).sum()),
        "zero_stock_items": int((policy_inputs["on_hand_quantity"] == 0).sum()),
        "below_safety_stock_items": int(
            (scores["inventory_position"] < scores["safety_stock"]).sum()
        ),
        "below_reorder_point_items": int(
            (scores["inventory_position"] < scores["reorder_point"]).sum()
        ),
        "excess_stock_items": int((scores["projected_excess_quantity"] > 0).sum()),
        "projected_stockout_items": int((scores["projected_shortage_quantity"] > 0).sum()),
        "expiry_risk_items": int((scores["expiry_risk_status"] != "not_applicable").sum()),
        "supplier_risk_distribution": _distribution(scores["supplier_risk_score"]),
        "recommendation_distribution": recommendations["recommended_action"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "constraint_binding_counts": recommendations["constraint_status"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "budget_utilisation": safe_ratio(
            float(recommendations["recommended_reorder_value"].sum()),
            config.optimisation.available_budget,
        ),
        "capacity_utilisation": safe_ratio(
            float(recommendations["recommended_reorder_quantity"].sum()),
            float(config.optimisation.available_replenishment_capacity),
        ),
        "total_recommended_value": float(recommendations["recommended_reorder_value"].sum()),
        "total_constrained_value": float(recommendations["recommended_reorder_value"].sum()),
        "unmet_replenishment_requirement": float(
            recommendations["unmet_replenishment_quantity"].sum()
        ),
        "scenario_comparison": scenarios.to_dict("records"),
    }


def reorder_quantity(raw_gap: float, policy: PolicySettings) -> int:
    """Apply non-negative clipping, minimum order, order multiple, and maximum quantity."""
    if raw_gap <= 0:
        return 0
    quantity = max(policy.minimum_order_quantity, math.ceil(raw_gap))
    if policy.order_multiple > 1:
        quantity = math.ceil(quantity / policy.order_multiple) * policy.order_multiple
    return min(policy.maximum_reorder_quantity, quantity)


def safe_days_of_supply(inventory_position: float, average_daily_demand: float) -> float:
    """Calculate safe days of supply for zero demand."""
    if average_daily_demand <= 0:
        return 999.0
    return max(0.0, inventory_position) / average_daily_demand


def safe_ratio(numerator: float, denominator: float) -> float:
    """Return a bounded safe ratio."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def priority_level(score: float) -> str:
    """Map 0-100 priority score to deterministic labels."""
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def expiry_metrics(
    expiry_date: str,
    snapshot_timestamp: str,
    inventory_position: float,
    average_daily_demand: float,
    unit_cost: float,
    warning_days: int,
) -> dict[str, Any]:
    """Calculate expiry risk only when expiry exists."""
    if not expiry_date or expiry_date == "nan":
        return {
            "days_until_expiry": None,
            "projected_demand_before_expiry": 0.0,
            "projected_remaining_quantity_at_expiry": 0.0,
            "expiry_at_risk_quantity": 0.0,
            "expiry_at_risk_value": 0.0,
            "expiry_risk_status": "not_applicable",
            "expiry_risk_score": 0.0,
        }
    days = int(
        (pd.to_datetime(expiry_date).date() - pd.to_datetime(snapshot_timestamp).date()).days
    )
    demand_before = max(0.0, average_daily_demand * max(days, 0))
    remaining = max(0.0, inventory_position - demand_before)
    status = "low"
    score = 10.0
    if days <= warning_days and remaining > 0:
        status = "high"
        score = 75.0
    elif days <= warning_days * 2 and remaining > 0:
        status = "medium"
        score = 40.0
    return {
        "days_until_expiry": days,
        "projected_demand_before_expiry": demand_before,
        "projected_remaining_quantity_at_expiry": remaining,
        "expiry_at_risk_quantity": remaining,
        "expiry_at_risk_value": remaining * unit_cost,
        "expiry_risk_status": status,
        "expiry_risk_score": score,
    }


def expected_stockout_date(
    snapshot_timestamp: str, inventory_position: float, average_daily_demand: float
) -> str:
    """Return deterministic projected stockout date or blank when not derivable."""
    if average_daily_demand <= 0 or inventory_position <= 0:
        return ""
    days = math.floor(inventory_position / average_daily_demand)
    return str((pd.to_datetime(snapshot_timestamp) + pd.Timedelta(days=days)).date())


def recommendation_reason(
    stockout_score: float,
    excess_score: float,
    expiry_score: float,
    reorder_qty: int,
    level: str,
) -> tuple[str, str]:
    """Return deterministic recommendation action and reason."""
    if expiry_score >= 50:
        return "prioritise_consumption_before_expiry", "Expiry risk exceeds threshold."
    if reorder_qty > 0 and stockout_score >= 70:
        return (
            "expedite_replenishment",
            "Stockout risk is high and inventory position is below target.",
        )
    if reorder_qty > 0:
        return "place_replenishment_order", "Inventory position is below reorder target."
    if excess_score >= 50:
        return "rebalance_or_reduce_excess_stock", "Days of supply exceeds excess threshold."
    if level in {"high", "critical"}:
        return "review_inventory_policy", "Priority score exceeds review threshold."
    return "maintain_current_policy", "No replenishment or intervention threshold was crossed."


def _warehouse_product_weights(
    inventory: pd.DataFrame, movements: pd.DataFrame
) -> dict[str, list[tuple[str, float, str]]]:
    products = set(inventory["item_id"].astype(str))
    product_movements = movements[movements["item_id"].astype(str).isin(products)]
    weights: dict[str, list[tuple[str, float, str]]] = {}
    for product_id, group in product_movements.groupby("item_id"):
        by_warehouse = group.groupby("warehouse_id")["quantity"].sum()
        total = float(by_warehouse.sum())
        if total > 0:
            weights[str(product_id)] = [
                (str(warehouse), float(quantity) / total, "recent_warehouse_movement_share")
                for warehouse, quantity in by_warehouse.sort_index().items()
            ]
    return weights


def _movement_context(movements: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    grouped = movements.groupby(["warehouse_id", "item_id", "movement_type"])["quantity"].sum()
    context: dict[tuple[str, str], dict[str, float]] = {}
    for (warehouse_id, item_id, movement_type), quantity in grouped.items():
        context.setdefault((str(warehouse_id), str(item_id)), {})[str(movement_type)] = float(
            quantity
        )
    return context


def _material_usage(
    movements: pd.DataFrame, policy: PolicySettings
) -> dict[tuple[str, str], float]:
    issues = movements[movements["movement_type"] == "issue_to_production"]
    grouped = issues.groupby(["warehouse_id", "item_id"])["quantity"].sum()
    return {
        (str(warehouse), str(item)): float(quantity) / policy.material_usage_window_days
        for (warehouse, item), quantity in grouped.items()
    }


def _historical_demand_variability(
    sales_orders: pd.DataFrame, config: InventoryConfig
) -> dict[str, dict[str, Any]]:
    sales = sales_orders.copy()
    sales["order_date"] = pd.to_datetime(sales["order_date"])
    daily = sales.groupby(["product_id", "order_date"])["ordered_quantity"].sum().reset_index()
    rows: dict[str, dict[str, Any]] = {}
    pooled_std = float(daily["ordered_quantity"].std(ddof=0)) if len(daily) else 0.0
    for product_id, group in daily.groupby("product_id"):
        std = float(group["ordered_quantity"].std(ddof=0)) if len(group) >= 2 else 0.0
        source = "observed_history" if len(group) >= 2 and std > 0 else "pooled_history"
        if std == 0:
            std = pooled_std
        if std == 0:
            std = config.policy.demand_variability_multiplier
            source = "configured_fallback"
        rows[str(product_id)] = {
            "demand_standard_deviation": std,
            "demand_variability_source": source,
        }
    return rows


def _scenario_allocate(frame: pd.DataFrame, budget: float, capacity: int) -> dict[str, float | int]:
    budget_remaining = budget
    capacity_remaining = float(capacity)
    quantity_total = 0.0
    value_total = 0.0
    binding = 0
    for record in frame.sort_values(
        ["priority_level_sort", "overall_priority_score", "warehouse_id", "item_id"],
        ascending=[True, False, True, True],
    ).to_dict("records"):
        qty = int(record["unconstrained_reorder_quantity"])
        unit_cost = float(record["unit_cost"])
        approved = min(qty, int(capacity_remaining))
        if unit_cost > 0:
            approved = min(approved, int(budget_remaining // unit_cost))
        if approved < qty:
            binding += 1
        budget_remaining -= approved * unit_cost
        capacity_remaining -= approved
        quantity_total += approved
        value_total += approved * unit_cost
    return {"quantity": quantity_total, "value": value_total, "binding_count": binding}


def _distribution(series: pd.Series) -> dict[str, float]:
    return {
        "min": float(series.min()) if len(series) else 0.0,
        "max": float(series.max()) if len(series) else 0.0,
        "mean": float(series.mean()) if len(series) else 0.0,
    }


RECOMMENDATION_COLUMNS = [
    "inventory_run_id",
    "warehouse_id",
    "item_id",
    "product_id",
    "material_id",
    "item_type",
    "on_hand_quantity",
    "available_quantity",
    "inventory_position",
    "forecast_demand",
    "average_daily_demand",
    "lead_time_days",
    "demand_standard_deviation",
    "safety_stock",
    "reorder_point",
    "unconstrained_reorder_quantity",
    "recommended_reorder_quantity",
    "projected_shortage_quantity",
    "projected_excess_quantity",
    "days_of_supply",
    "stockout_risk_score",
    "excess_risk_score",
    "supplier_risk_score",
    "expiry_risk_score",
    "overall_priority_score",
    "priority_level",
    "priority_level_sort",
    "recommended_action",
    "recommendation_reason",
    "constraint_status",
    "recommended_reorder_value",
    "unmet_replenishment_quantity",
    "objective_score",
    "synthetic_data_flag",
]
