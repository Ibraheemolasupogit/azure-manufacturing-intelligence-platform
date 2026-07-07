"""Markdown reporting for quality analytics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def write_quality_report(
    path: Path,
    *,
    quality_run_id: str,
    summary: dict[str, Any],
    alerts: pd.DataFrame,
    max_alerts: int,
) -> None:
    """Write a compact quality analytics report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    top = alerts.head(max_alerts)
    lines = [
        "# Quality Analytics Report",
        "",
        f"- Quality run ID: `{quality_run_id}`",
        f"- Quality records processed: {summary['quality_records_processed']}",
        f"- Specification failures: {summary['specification_failure_count']}",
        f"- Near-limit observations: {summary['near_limit_count']}",
        f"- Robust-z anomalies: {summary['robust_z_anomaly_count']}",
        f"- Isolation Forest anomalies: {summary['isolation_forest_anomaly_count']}",
        f"- High-risk alerts: {summary['high_risk_alert_count']}",
        f"- Critical-risk alerts: {summary['critical_risk_alert_count']}",
        "",
        "## Top Alerts",
        "",
        "| Risk | Inspection | Product | Machine | Metric | Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in top.to_dict("records"):
        lines.append(
            "| "
            f"{row['risk_level']} | "
            f"{row['inspection_id']} | "
            f"{row['product_id']} | "
            f"{row['machine_id']} | "
            f"{row['quality_metric']} | "
            f"{row['recommended_action']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Quality-risk scores are deterministic heuristic scores, not calibrated "
            "probabilities.",
            "- Investigation context is analytical context, not root-cause proof.",
            "- No Azure services are deployed or called by this milestone.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_alert_summary(
    path: Path,
    *,
    quality_run_id: str,
    alerts: pd.DataFrame,
) -> None:
    """Write a compact alert summary report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    by_level = alerts["risk_level"].value_counts().sort_index().to_dict()
    by_metric = alerts["quality_metric"].value_counts().sort_index().to_dict()
    lines = [
        "# Quality Alert Summary",
        "",
        f"- Quality run ID: `{quality_run_id}`",
        f"- Alert rows: {len(alerts)}",
        "",
        "## Alerts By Risk Level",
        "",
    ]
    for key, value in by_level.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Alerts By Quality Metric", ""])
    for key, value in by_metric.items():
        lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
