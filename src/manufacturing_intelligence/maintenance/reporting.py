"""Markdown reports for maintenance analytics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def write_maintenance_report(
    path: Path,
    *,
    maintenance_run_id: str,
    summary: dict[str, Any],
    top_alerts: pd.DataFrame,
    max_alerts: int,
) -> None:
    """Write the main maintenance analytics report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Predictive Maintenance Analytics Report",
        "",
        f"Maintenance run ID: `{maintenance_run_id}`",
        "",
        "This report is deterministic decision-support evidence from synthetic governed inputs. "
        "Failure-risk scores are heuristic 0-100 scores, not calibrated probabilities or "
        "certified safety instructions.",
        "",
        "## KPI summary",
        "",
    ]
    for key in sorted(summary):
        lines.append(f"- {key}: {summary[key]}")
    lines.extend(["", "## Top maintenance alerts", ""])
    if top_alerts.empty:
        lines.append("No maintenance alerts were generated.")
    else:
        columns = [
            "alert_id",
            "sensor_event_id",
            "machine_id",
            "sensor_type",
            "failure_risk_score",
            "risk_level",
            "recommended_action",
        ]
        lines.extend(_markdown_table(top_alerts[columns].head(max_alerts)))
    lines.extend(
        [
            "",
            "## Method notes",
            "",
            "- Threshold compliance preserves both source and calculated threshold status.",
            "- Degradation uses chronological rolling statistics and does not use future "
            "observations for operational scoring.",
            "- Robust z-score uses `0.6745 * (x - median) / MAD` where sufficient prior "
            "history exists.",
            "- Isolation Forest is deterministic and retrospective; its score is a relative "
            "anomaly diagnostic, not a probability.",
            "- Investigation context is analytical context only and does not assert root cause.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_alert_summary(path: Path, *, maintenance_run_id: str, alerts: pd.DataFrame) -> None:
    """Write a concise alert summary report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Maintenance Alert Summary",
        "",
        f"Maintenance run ID: `{maintenance_run_id}`",
        "",
        f"Alert count: {len(alerts)}",
        "",
    ]
    if not alerts.empty:
        lines.extend(["## Risk distribution", ""])
        for risk, count in alerts["risk_level"].value_counts().sort_index().items():
            lines.append(f"- {risk}: {count}")
        lines.extend(["", "## Investigation context", ""])
        for row in alerts.head(10).to_dict("records"):
            lines.append(
                f"- `{row['alert_id']}` / `{row['machine_id']}`: {row['investigation_context']}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    columns = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for record in frame.astype(str).to_dict("records"):
        rows.append("| " + " | ".join(record[column] for column in columns) + " |")
    return rows
