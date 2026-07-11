"""Semantic model metadata for local dashboard outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.dashboard.metrics import SYNTHETIC_DISCLAIMER

PRIMARY_KEYS = {
    "dim_date": ["date_key"],
    "dim_product": ["product_id"],
    "dim_plant": ["plant_id"],
    "dim_production_line": ["production_line_id"],
    "dim_machine": ["machine_id"],
    "dim_warehouse": ["warehouse_id"],
    "dim_supplier": ["supplier_id"],
    "dim_metric": ["metric_id"],
    "dim_risk_level": ["risk_level"],
    "dim_dashboard_page": ["page_id"],
}

RELATIONSHIPS = [
    ("fact_production_kpis", "product_id", "dim_product", "product_id"),
    ("fact_production_kpis", "plant_id", "dim_plant", "plant_id"),
    ("fact_production_kpis", "production_line_id", "dim_production_line", "production_line_id"),
    ("fact_production_kpis", "machine_id", "dim_machine", "machine_id"),
    ("fact_demand_forecast", "product_id", "dim_product", "product_id"),
    ("fact_inventory_risk", "warehouse_id", "dim_warehouse", "warehouse_id"),
    ("fact_quality_alerts", "product_id", "dim_product", "product_id"),
    ("fact_quality_alerts", "machine_id", "dim_machine", "machine_id"),
    ("fact_maintenance_alerts", "machine_id", "dim_machine", "machine_id"),
    ("fact_platform_health", "domain", "dim_metric", "domain"),
]


def build_semantic_model(model_name: str, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Build local semantic model metadata from generated tables."""
    table_metadata = []
    for name, frame in sorted(tables.items()):
        table_metadata.append(
            {
                "name": name,
                "description": f"Power BI-ready local table for {name}.",
                "primary_key": PRIMARY_KEYS.get(name, []),
                "columns": [
                    {
                        "name": column,
                        "data_type": _dtype(frame[column]),
                        "description": f"{column} from governed synthetic evidence",
                        "hidden": column.endswith("_sort"),
                    }
                    for column in frame.columns
                ],
            }
        )
    relationships = [
        {
            "from_table": left_table,
            "from_column": left_column,
            "to_table": right_table,
            "to_column": right_column,
            "relationship_type": "many_to_one",
        }
        for left_table, left_column, right_table, right_column in RELATIONSHIPS
        if left_table in tables
        and right_table in tables
        and left_column in tables[left_table].columns
        and right_column in tables[right_table].columns
    ]
    measures = [
        {
            "name": "Total Production Output",
            "expression": "SUM(fact_production_kpis[accepted_quantity])",
        },
        {"name": "Forecast Demand", "expression": "SUM(fact_demand_forecast[point_forecast])"},
        {
            "name": "Inventory Priority",
            "expression": "AVERAGE(fact_inventory_risk[priority_score])",
        },
        {"name": "Quality Alerts", "expression": "COUNTROWS(fact_quality_alerts)"},
        {"name": "Maintenance Alerts", "expression": "COUNTROWS(fact_maintenance_alerts)"},
        {
            "name": "Platform Health",
            "expression": "AVERAGE(fact_platform_health[platform_health_score])",
        },
    ]
    return {
        "model_name": model_name,
        "tables": table_metadata,
        "relationships": relationships,
        "measures": measures,
        "display_folders": {
            "Executive": ["executive_scorecard"],
            "Operations": ["fact_production_kpis", "fact_platform_health"],
            "Supply Chain": ["fact_demand_forecast", "fact_inventory_risk"],
            "Assurance": ["fact_quality_alerts", "fact_maintenance_alerts"],
            "Narratives": ["fact_operations_assistant_narratives"],
        },
        "calculation_notes": "Measures are local semantic-model suggestions, not deployed DAX.",
        "limitations": "No Fabric semantic model or Power BI dataset was deployed.",
        "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
    }


def _dtype(series: pd.Series[Any]) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "decimal"
    return "text"
