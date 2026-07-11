"""Dashboard metric catalogue and fact/dimension builders."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

SYNTHETIC_DISCLAIMER = (
    "Dashboard outputs are based only on deterministic synthetic manufacturing evidence. "
    "No Power BI, Fabric, Azure service, or live operational system was called."
)


def build_tables(
    frames: dict[str, pd.DataFrame], json_inputs: dict[str, Any]
) -> dict[str, pd.DataFrame]:
    """Build dashboard dimensions, facts, scorecard, and metric catalogue."""
    production = frames["production_events"].copy()
    production["event_date"] = pd.to_datetime(production["event_timestamp"]).dt.date.astype(str)
    demand = frames["demand_forecast"].copy()
    inventory = frames["inventory_scores"].copy()
    quality = frames["quality_alerts"].copy()
    maintenance = frames["maintenance_alerts"].copy()
    platform = json_inputs["platform_health_summary"]
    responses = pd.DataFrame(json_inputs["genai_responses"])

    dim_date = _dim_date(production, frames["sales_orders"], demand, quality, maintenance)
    tables = {
        "dim_date": dim_date,
        "dim_product": _dimension(
            "product_id", [production, frames["sales_orders"], demand, quality]
        ),
        "dim_plant": _dimension("plant_id", [production, frames["inventory_levels"], quality]),
        "dim_production_line": _dimension("production_line_id", [production, quality]),
        "dim_machine": _dimension("machine_id", [production, quality, maintenance]),
        "dim_warehouse": _dimension("warehouse_id", [frames["inventory_levels"], inventory]),
        "dim_supplier": _dimension("supplier_id", [frames["supplier_performance"]]),
        "dim_metric": metric_catalogue(),
        "dim_risk_level": _risk_levels(),
        "dim_dashboard_page": _dashboard_pages(),
        "fact_production_kpis": _production_fact(production),
        "fact_demand_forecast": _demand_fact(demand),
        "fact_inventory_risk": _inventory_fact(inventory),
        "fact_quality_alerts": _quality_fact(quality),
        "fact_maintenance_alerts": _maintenance_fact(maintenance),
        "fact_platform_health": _platform_fact(platform),
        "fact_operations_assistant_narratives": _assistant_fact(responses),
    }
    tables["executive_scorecard"] = _executive_scorecard(tables, platform, json_inputs)
    tables["metric_catalogue"] = metric_catalogue()
    return tables


def metric_catalogue() -> pd.DataFrame:
    rows = [
        (
            "M001",
            "production_output",
            "production",
            "Accepted production quantity",
            "Sum accepted_quantity",
            "sum(accepted_quantity)",
            "date, plant, line, product",
            "fact_production_kpis",
            "accepted_quantity",
        ),
        (
            "M002",
            "demand_forecast",
            "forecasting",
            "Forecast demand quantity",
            "Point forecast",
            "sum(point_forecast)",
            "date, product, region",
            "fact_demand_forecast",
            "point_forecast",
        ),
        (
            "M003",
            "forecast_horizon",
            "forecasting",
            "Forecast horizon days",
            "Horizon day",
            "max(forecast_horizon_day)",
            "series",
            "fact_demand_forecast",
            "forecast_horizon_day",
        ),
        (
            "M004",
            "inventory_score",
            "inventory",
            "Inventory priority score",
            "Priority score",
            "avg(priority_score)",
            "warehouse, item",
            "fact_inventory_risk",
            "priority_score",
        ),
        (
            "M005",
            "reorder_recommendation",
            "inventory",
            "Recommended reorder quantity",
            "Rules-based quantity",
            "sum(recommended_reorder_quantity)",
            "warehouse, item",
            "fact_inventory_risk",
            "recommended_reorder_quantity",
        ),
        (
            "M006",
            "stockout_risk",
            "inventory",
            "Stockout risk score",
            "Stockout risk",
            "avg(stockout_risk_score)",
            "warehouse, item",
            "fact_inventory_risk",
            "stockout_risk_score",
        ),
        (
            "M007",
            "quality_alert",
            "quality",
            "Quality alert count",
            "Alert rows",
            "count(alert_id)",
            "alert",
            "fact_quality_alerts",
            "alert_id",
        ),
        (
            "M008",
            "specification_failure",
            "quality",
            "Specification failures",
            "Failed specification flags",
            "count where calculated_specification_result=fail",
            "inspection",
            "fact_quality_alerts",
            "calculated_specification_result",
        ),
        (
            "M009",
            "maintenance_alert",
            "maintenance",
            "Maintenance alert count",
            "Alert rows",
            "count(alert_id)",
            "alert",
            "fact_maintenance_alerts",
            "alert_id",
        ),
        (
            "M010",
            "failure_risk",
            "maintenance",
            "Failure risk score",
            "Failure risk score",
            "avg(failure_risk_score)",
            "machine",
            "fact_maintenance_alerts",
            "failure_risk_score",
        ),
        (
            "M011",
            "platform_health",
            "monitoring",
            "Platform health score",
            "Monitoring score",
            "platform_health_score",
            "platform",
            "fact_platform_health",
            "platform_health_score",
        ),
        (
            "M012",
            "monitoring_alert",
            "monitoring",
            "Monitoring alert count",
            "Monitoring alerts",
            "sum(alert_count)",
            "platform",
            "fact_platform_health",
            "alert_count",
        ),
        (
            "M013",
            "assistant_response_count",
            "genai",
            "Assistant response count",
            "Response rows",
            "count(response_id)",
            "response",
            "fact_operations_assistant_narratives",
            "response_id",
        ),
    ]
    columns = [
        "metric_id",
        "metric_name",
        "domain",
        "business_definition",
        "technical_definition",
        "calculation_formula",
        "grain",
        "source_table",
        "source_fields",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["refresh_dependency"] = "tracked governed milestone outputs"
    frame["owner_role"] = "manufacturing analytics owner"
    frame["quality_notes"] = "validated synthetic evidence"
    frame["limitations"] = "portfolio sample; not live operations"
    frame["synthetic_data_flag"] = True
    return frame


def _dim_date(*frames: pd.DataFrame) -> pd.DataFrame:
    values: set[str] = set()
    for frame in frames:
        for column in frame.columns:
            if "date" in column or "timestamp" in column:
                parsed = pd.to_datetime(frame[column], errors="coerce")
                values.update(parsed.dropna().dt.date.astype(str).tolist())
    output = pd.DataFrame({"date_key": sorted(values)})
    output["year"] = pd.to_datetime(output["date_key"]).dt.year
    output["month"] = pd.to_datetime(output["date_key"]).dt.month
    output["day"] = pd.to_datetime(output["date_key"]).dt.day
    output["synthetic_data_flag"] = True
    return output


def _dimension(key: str, frames: list[pd.DataFrame]) -> pd.DataFrame:
    values: set[str] = set()
    for frame in frames:
        if key in frame.columns:
            values.update(str(value) for value in frame[key].dropna().unique())
    label = key.removesuffix("_id")
    output = pd.DataFrame({key: sorted(values)})
    output[f"{label}_name"] = output[key]
    output["synthetic_data_flag"] = True
    return output


def _risk_levels() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"risk_level": "low", "risk_sort": 1, "risk_description": "Low dashboard risk"},
            {"risk_level": "medium", "risk_sort": 2, "risk_description": "Medium dashboard risk"},
            {"risk_level": "high", "risk_sort": 3, "risk_description": "High dashboard risk"},
            {
                "risk_level": "critical",
                "risk_sort": 4,
                "risk_description": "Critical dashboard risk",
            },
        ]
    ).assign(synthetic_data_flag=True)


def _dashboard_pages() -> pd.DataFrame:
    pages = [
        "executive_overview",
        "production_operations",
        "demand_forecasting",
        "inventory_and_supply_chain",
        "quality_analytics",
        "predictive_maintenance",
        "platform_monitoring",
        "operations_assistant",
    ]
    return pd.DataFrame(
        {
            "page_id": pages,
            "page_title": [page.replace("_", " ").title() for page in pages],
            "synthetic_data_flag": True,
        }
    )


def _production_fact(production: pd.DataFrame) -> pd.DataFrame:
    grouped = production.groupby(
        ["event_date", "plant_id", "production_line_id", "machine_id", "product_id"],
        dropna=False,
    ).agg(
        planned_quantity=("planned_quantity", "sum"),
        produced_quantity=("produced_quantity", "sum"),
        accepted_quantity=("accepted_quantity", "sum"),
        rejected_quantity=("rejected_quantity", "sum"),
        downtime_minutes=("downtime_duration_minutes", "sum"),
        event_count=("event_id", "count"),
    )
    output = grouped.reset_index()
    output["production_variance"] = output["produced_quantity"] - output["planned_quantity"]
    output["yield_rate"] = output["accepted_quantity"] / output["produced_quantity"].clip(lower=1)
    output["synthetic_data_flag"] = True
    return output


def _demand_fact(demand: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "forecast_run_id",
        "series_id",
        "product_id",
        "distribution_region",
        "forecast_date",
        "forecast_horizon_day",
        "selected_model",
        "point_forecast",
        "lower_bound",
        "upper_bound",
        "synthetic_data_flag",
    ]
    return demand[columns].sort_values(columns[:6]).reset_index(drop=True)


def _inventory_fact(inventory: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "inventory_run_id",
        "warehouse_id",
        "plant_id",
        "item_id",
        "product_id",
        "material_id",
        "priority_level",
        "priority_score",
        "stockout_risk_score",
        "recommended_reorder_quantity",
        "recommended_action",
        "inventory_value",
        "synthetic_data_flag",
    ]
    return inventory[columns].sort_values(["priority_level", "warehouse_id", "item_id"])


def _quality_fact(quality: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "quality_run_id",
        "alert_id",
        "inspection_timestamp",
        "plant_id",
        "production_line_id",
        "machine_id",
        "product_id",
        "quality_metric",
        "risk_level",
        "quality_risk_score",
        "recommended_action",
        "synthetic_data_flag",
    ]
    return quality[columns].sort_values(["risk_level", "alert_id"])


def _maintenance_fact(maintenance: pd.DataFrame) -> pd.DataFrame:
    columns = [
        column
        for column in [
            "maintenance_run_id",
            "alert_id",
            "machine_id",
            "plant_id",
            "production_line_id",
            "sensor_type",
            "risk_level",
            "failure_risk_score",
            "recommended_action",
            "synthetic_data_flag",
        ]
        if column in maintenance.columns
    ]
    return maintenance[columns].sort_values(["risk_level", "alert_id"])


def _platform_fact(platform: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for domain, score in sorted(platform["domain_health_scores"].items()):
        rows.append(
            {
                "monitoring_run_id": platform["monitoring_run_id"],
                "domain": domain,
                "platform_health_score": platform["platform_health_score"],
                "domain_health_score": score,
                "domain_health_label": platform["domain_health_labels"][domain],
                "alert_count": sum(platform["alert_counts_by_severity"].values()),
                "synthetic_data_flag": True,
            }
        )
    return pd.DataFrame(rows)


def _assistant_fact(responses: pd.DataFrame) -> pd.DataFrame:
    output = responses[
        [
            "response_id",
            "task_type",
            "user_question",
            "answer",
            "grounding_score",
            "citation_coverage",
            "guardrail_status",
            "external_model_called",
        ]
    ].copy()
    output["synthetic_data_flag"] = True
    return output.sort_values("response_id")


def _executive_scorecard(
    tables: dict[str, pd.DataFrame],
    platform: dict[str, Any],
    json_inputs: dict[str, Any],
) -> pd.DataFrame:
    inventory = tables["fact_inventory_risk"]
    quality = tables["fact_quality_alerts"]
    maintenance = tables["fact_maintenance_alerts"]
    forecast = tables["fact_demand_forecast"]
    rows = [
        (
            "monitoring",
            "platform_health_score",
            platform["platform_health_score"],
            "score",
            "healthy",
        ),
        ("forecasting", "total_forecast_rows", len(forecast), "rows", ""),
        ("forecasting", "selected_forecast_model", forecast["selected_model"].iloc[0], "model", ""),
        (
            "inventory",
            "inventory_high_risk_count",
            int((inventory["priority_level"] == "high").sum()),
            "count",
            "high",
        ),
        (
            "inventory",
            "inventory_critical_risk_count",
            int((inventory["priority_level"] == "critical").sum()),
            "count",
            "critical",
        ),
        ("quality", "quality_alert_count", len(quality), "count", ""),
        (
            "quality",
            "quality_high_risk_count",
            int((quality["risk_level"] == "high").sum()),
            "count",
            "high",
        ),
        (
            "quality",
            "quality_critical_risk_count",
            int((quality["risk_level"] == "critical").sum()),
            "count",
            "critical",
        ),
        ("maintenance", "maintenance_alert_count", len(maintenance), "count", ""),
        (
            "maintenance",
            "maintenance_high_risk_count",
            int((maintenance["risk_level"] == "high").sum()),
            "count",
            "high",
        ),
        (
            "maintenance",
            "maintenance_critical_risk_count",
            int((maintenance["risk_level"] == "critical").sum()),
            "count",
            "critical",
        ),
        (
            "monitoring",
            "monitoring_alert_count",
            sum(platform["alert_counts_by_severity"].values()),
            "count",
            "",
        ),
        ("genai", "genai_response_count", len(json_inputs["genai_responses"]), "count", ""),
        ("governance", "synthetic_data_flag", 1, "boolean", ""),
    ]
    return pd.DataFrame(
        [
            {
                "run_date_label": "controlled_static_run",
                "domain": domain,
                "metric_name": metric,
                "metric_value": value,
                "metric_unit": unit,
                "risk_level": risk,
                "source_artifact": "tracked governed milestone evidence",
                "source_run_id": "",
                "synthetic_data_flag": True,
            }
            for domain, metric, value, unit, risk in rows
        ]
    )
