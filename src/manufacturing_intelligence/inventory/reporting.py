"""Inventory Markdown reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def write_report(
    path: Path,
    *,
    inventory_run_id: str,
    scores: pd.DataFrame,
    recommendations: pd.DataFrame,
    summary: dict[str, Any],
    maximum_recommendations: int,
) -> None:
    """Write a compact human-readable inventory intelligence report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    top = recommendations.sort_values(
        ["overall_priority_score", "warehouse_id", "item_id"],
        ascending=[False, True, True],
    ).head(maximum_recommendations)
    lines = [
        "# Inventory Intelligence Report",
        "",
        f"- Inventory run ID: `{inventory_run_id}`",
        f"- Evaluated item-location rows: {len(scores)}",
        f"- Recommendation rows: {len(recommendations)}",
        f"- Total working-capital exposure: {summary['total_working_capital_exposure']:.2f}",
        f"- Total recommended reorder value: {summary['total_recommended_value']:.2f}",
        f"- Projected shortage quantity: {summary['projected_shortage_quantity']:.2f}",
        f"- Projected excess quantity: {summary['projected_excess_quantity']:.2f}",
        f"- Budget utilisation: {summary['budget_utilisation']:.4f}",
        f"- Capacity utilisation: {summary['capacity_utilisation']:.4f}",
        "",
        "## Top Recommendations",
        "",
        "| Priority | Item | Warehouse | Action | Recommended qty | Risk score | Constraint |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in top.to_dict("records"):
        lines.append(
            "| "
            f"{row['priority_level']} | "
            f"{row['item_id']} | "
            f"{row['warehouse_id']} | "
            f"{row['recommended_action']} | "
            f"{int(row['recommended_reorder_quantity'])} | "
            f"{float(row['overall_priority_score']):.2f} | "
            f"{row['constraint_status']} |"
        )
    lines.extend(
        [
            "",
            "## Assumptions",
            "",
            "- Outputs are deterministic local recommendations from synthetic governed data.",
            "- Demand is allocated to warehouses before inventory policy scoring.",
            "- Constrained allocation is deterministic greedy prioritisation, not a cloud solver.",
            "- No Azure services are deployed or called by this milestone.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_scenario_report(
    path: Path,
    *,
    inventory_run_id: str,
    scenarios: pd.DataFrame,
) -> None:
    """Write a scenario comparison report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Inventory Scenario Summary",
        "",
        f"- Inventory run ID: `{inventory_run_id}`",
        f"- Scenario count: {len(scenarios)}",
        "",
        "| Scenario | Shortage qty | Excess qty | Recommended qty | "
        "Working capital | Budget use | Capacity use |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in scenarios.sort_values("scenario_name").to_dict("records"):
        lines.append(
            "| "
            f"{row['scenario_name']} | "
            f"{float(row['projected_shortage_quantity']):.2f} | "
            f"{float(row['projected_excess_quantity']):.2f} | "
            f"{float(row['total_constrained_quantity']):.2f} | "
            f"{float(row['working_capital_requirement']):.2f} | "
            f"{float(row['budget_utilisation']):.4f} | "
            f"{float(row['capacity_utilisation']):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Baseline uses the configured demand, supplier, budget, and capacity assumptions.",
            "- High-demand, supplier-delay, budget, and capacity scenarios apply deterministic "
            "multipliers to the same synthetic governed inputs.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
