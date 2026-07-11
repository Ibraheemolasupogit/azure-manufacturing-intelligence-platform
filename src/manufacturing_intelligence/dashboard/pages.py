"""Dashboard page specifications."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.dashboard.metrics import SYNTHETIC_DISCLAIMER


def dashboard_page_specs(pages: tuple[str, ...]) -> list[dict[str, Any]]:
    specs = []
    for page in pages:
        specs.append(
            {
                "page_id": page,
                "page_title": page.replace("_", " ").title(),
                "purpose": f"Power BI-ready local specification for {page}.",
                "target_audience": _audience(page),
                "primary_questions_answered": _questions(page),
                "source_tables": _source_tables(page),
                "recommended_filters": ["date_key", "plant_id", "product_id", "risk_level"],
                "recommended_visuals": _visuals(page),
                "kpi_cards": _kpis(page),
                "drillthrough_paths": _drillthrough(page),
                "refresh_dependencies": ["tracked governed milestone outputs"],
                "limitations": "Specification only; no page was deployed.",
                "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
            }
        )
    return specs


def _audience(page: str) -> str:
    if page == "executive_overview":
        return "executive leadership"
    if page in {"inventory_and_supply_chain", "demand_forecasting"}:
        return "supply-chain planners"
    if page in {"quality_analytics", "predictive_maintenance"}:
        return "quality and maintenance leaders"
    if page == "operations_assistant":
        return "operations analysts"
    return "plant and platform operators"


def _questions(page: str) -> list[str]:
    return [
        f"What does the governed synthetic evidence say about {page.replace('_', ' ')}?",
        "Which metrics need review in the controlled portfolio sample?",
    ]


def _source_tables(page: str) -> list[str]:
    mapping = {
        "executive_overview": ["executive_scorecard", "fact_platform_health"],
        "production_operations": ["fact_production_kpis"],
        "demand_forecasting": ["fact_demand_forecast"],
        "inventory_and_supply_chain": ["fact_inventory_risk"],
        "quality_analytics": ["fact_quality_alerts"],
        "predictive_maintenance": ["fact_maintenance_alerts"],
        "platform_monitoring": ["fact_platform_health"],
        "operations_assistant": ["fact_operations_assistant_narratives"],
    }
    return mapping[page]


def _visuals(page: str) -> list[str]:
    return ["KPI card", "line chart", "bar chart", "matrix", "table", "narrative text box"]


def _kpis(page: str) -> list[str]:
    mapping = {
        "executive_overview": ["platform_health_score", "quality_alert_count"],
        "production_operations": ["production_output", "production_variance"],
        "demand_forecasting": ["demand_forecast", "forecast_horizon"],
        "inventory_and_supply_chain": ["inventory_score", "stockout_risk"],
        "quality_analytics": ["quality_alert", "specification_failure"],
        "predictive_maintenance": ["maintenance_alert", "failure_risk"],
        "platform_monitoring": ["platform_health", "monitoring_alert"],
        "operations_assistant": ["assistant_response_count"],
    }
    return mapping[page]


def _drillthrough(page: str) -> list[str]:
    return (
        ["from KPI to detail table"]
        if page != "operations_assistant"
        else ["from task to response"]
    )
