"""Dashboard Markdown reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_markdown(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{body.rstrip()}\n", encoding="utf-8")


def dashboard_report(run_id: str, diagnostics: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Dashboard run ID: {run_id}",
            "",
            "The dashboard output layer is local, deterministic, and Power BI-ready.",
            "No .pbix file, Power BI Service connection, Fabric API call, or Azure "
            "deployment was created.",
            "",
            f"- Generated tables: {diagnostics['generated_table_count']}",
            f"- Dimension tables: {diagnostics['dimension_table_count']}",
            f"- Fact tables: {diagnostics['fact_table_count']}",
            f"- Metrics: {diagnostics['metric_count']}",
            f"- Dashboard pages: {diagnostics['dashboard_page_count']}",
            f"- Visual specifications: {diagnostics['visual_spec_count']}",
            f"- Executive scorecard KPIs: {diagnostics['executive_scorecard_kpi_count']}",
        ]
    )
