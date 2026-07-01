"""Markdown reporting for governed ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_markdown_report(path: Path, quality_report: dict[str, Any]) -> None:
    """Write a Markdown data-quality report from machine-readable metrics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Data Quality Report",
        "",
        f"- Ingestion run ID: `{quality_report['ingestion_run_id']}`",
        f"- Validation status: `{quality_report['validation_status']}`",
        f"- Total records: `{quality_report['overall']['record_count']}`",
        f"- Accepted records: `{quality_report['overall']['accepted_count']}`",
        f"- Quarantined records: `{quality_report['overall']['quarantine_count']}`",
        f"- Quarantine rate: `{quality_report['overall']['quarantine_rate']:.6f}`",
        "",
        "| Dataset | Records | Accepted | Quarantined | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for dataset, metrics in quality_report["datasets"].items():
        lines.append(
            f"| {dataset} | {metrics['record_count']} | {metrics['accepted_count']} | "
            f"{metrics['quarantine_count']} | {metrics['status']} |"
        )
    lines.extend(
        [
            "",
            "All metrics are generated from the controlled local ingestion outputs. "
            "No Azure resources were deployed or called.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
