"""Monitoring summary helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def platform_summary(
    *,
    monitoring_run_id: str,
    platform_health_score: float,
    platform_health_label: str,
    domain_scores: pd.DataFrame,
    alerts: pd.DataFrame,
) -> dict[str, Any]:
    """Build stable platform health summary."""
    return {
        "monitoring_run_id": monitoring_run_id,
        "platform_health_score": platform_health_score,
        "platform_health_label": platform_health_label,
        "domain_health_scores": domain_scores.set_index("domain")["health_score"].to_dict(),
        "domain_health_labels": domain_scores.set_index("domain")["health_label"].to_dict(),
        "alert_counts_by_severity": alerts["severity"].value_counts().sort_index().to_dict(),
        "relationship": {
            "outputs/platform_health_summary.json": "portfolio-level projection",
            "outputs/monitoring/platform_health_summary.json": "controlled monitoring summary",
            "outputs/monitoring/monitoring_alerts.csv": "row-level monitoring alerts",
        },
        "synthetic_data_flag": True,
        "azure_deployment_status": "reference_only_no_azure_services_called",
    }
