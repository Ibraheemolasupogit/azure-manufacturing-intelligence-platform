"""Visual specification metadata."""

from __future__ import annotations

from typing import Any


def visual_specs(pages: list[dict[str, Any]], max_per_page: int) -> list[dict[str, Any]]:
    specs = []
    visual_types = ["KPI card", "line chart", "bar chart", "matrix", "table", "narrative text box"]
    for page in pages:
        source_table = page["source_tables"][0]
        for index, visual_type in enumerate(visual_types[:max_per_page], start=1):
            specs.append(
                {
                    "visual_id": f"{page['page_id']}-visual-{index:02d}",
                    "page_id": page["page_id"],
                    "visual_type": visual_type,
                    "title": f"{page['page_title']} {visual_type}",
                    "business_question": page["primary_questions_answered"][0],
                    "source_table": source_table,
                    "fields": _fields(source_table),
                    "measures": page["kpi_cards"],
                    "filters": page["recommended_filters"],
                    "sort_order": index,
                    "expected_interaction": (
                        "filter and cross-highlight within local dashboard design"
                    ),
                    "caveats": "Specification only; no Power BI visual was rendered.",
                }
            )
    return specs


def _fields(table: str) -> list[str]:
    mapping = {
        "executive_scorecard": ["domain", "metric_name", "metric_value"],
        "fact_production_kpis": ["event_date", "plant_id", "accepted_quantity"],
        "fact_demand_forecast": ["forecast_date", "product_id", "point_forecast"],
        "fact_inventory_risk": ["warehouse_id", "item_id", "priority_score"],
        "fact_quality_alerts": ["plant_id", "risk_level", "quality_risk_score"],
        "fact_maintenance_alerts": ["machine_id", "risk_level", "failure_risk_score"],
        "fact_platform_health": ["domain", "domain_health_score", "platform_health_score"],
        "fact_operations_assistant_narratives": ["task_type", "answer", "grounding_score"],
    }
    return mapping[table]
