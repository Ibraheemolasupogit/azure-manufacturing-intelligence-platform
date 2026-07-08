"""Markdown observability reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def write_platform_report(
    path: Path,
    *,
    summary: dict[str, Any],
    domain_scores: pd.DataFrame,
    alerts: pd.DataFrame,
    max_alerts: int,
) -> None:
    """Write platform monitoring report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Platform Monitoring Report",
        "",
        f"Monitoring run ID: `{summary['monitoring_run_id']}`",
        f"Platform health score: {summary['platform_health_score']:.6f}",
        f"Platform health label: `{summary['platform_health_label']}`",
        "",
        "These are deterministic local observability checks over synthetic governed evidence. "
        "They are not live Azure Monitor telemetry or formal SLA measurements.",
        "",
        "## Domain health",
        "",
        *_markdown_table(domain_scores[["domain", "health_score", "health_label", "deductions"]]),
        "",
        "## Monitoring alerts",
        "",
    ]
    if alerts.empty:
        lines.append("No monitoring alerts were generated.")
    else:
        lines.extend(
            _markdown_table(
                alerts[
                    [
                        "severity",
                        "domain",
                        "alert_type",
                        "affected_artifact",
                        "message",
                    ]
                ].head(max_alerts)
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_observability_summary(path: Path, *, summary: dict[str, Any]) -> None:
    """Write concise observability summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Observability Summary",
        "",
        f"Monitoring run ID: `{summary['monitoring_run_id']}`",
        f"Platform health: `{summary['platform_health_label']}` "
        f"({summary['platform_health_score']:.6f})",
        "",
        "## Alert counts by severity",
        "",
    ]
    for severity, count in summary["alert_counts_by_severity"].items():
        lines.append(f"- {severity}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    columns = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for record in frame.astype(str).to_dict("records"):
        rows.append("| " + " | ".join(record[column] for column in columns) + " |")
    return rows
