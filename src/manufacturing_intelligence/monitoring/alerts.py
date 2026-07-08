"""Deterministic monitoring alerts."""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.monitoring.config import MonitoringThresholds

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def monitoring_alerts(
    *,
    monitoring_run_id: str,
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    domain_scores: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> pd.DataFrame:
    """Build deterministic monitoring alerts."""
    rows: list[dict[str, Any]] = []
    for record in integrity.to_dict("records"):
        if record["integrity_status"] != "passed":
            rows.append(
                _alert(
                    monitoring_run_id,
                    str(record["domain"]),
                    "critical",
                    "manifest_integrity_failure",
                    str(record["path"]),
                    str(record["actual_sha256"]),
                    str(record["expected_sha256"]),
                    "Manifest hash, size, or row count did not match the artifact.",
                    "Regenerate or investigate the affected governed evidence.",
                )
            )
    for record in lineage.to_dict("records"):
        if (
            float(record["lineage_completeness_score"])
            < thresholds.minimum_lineage_completeness_score
        ):
            rows.append(
                _alert(
                    monitoring_run_id,
                    str(record["domain"]),
                    "warning",
                    "lineage_incomplete",
                    str(record["domain"]),
                    f"{float(record['lineage_completeness_score']):.2f}",
                    f"{thresholds.minimum_lineage_completeness_score:.2f}",
                    "Lineage completeness fell below the configured threshold.",
                    "Inspect lineage metadata and target coverage.",
                )
            )
    for record in domain_scores.to_dict("records"):
        score = float(record["health_score"])
        if score < thresholds.critical_score_threshold:
            severity = "critical"
        elif score < thresholds.minimum_pipeline_health_score:
            severity = "warning"
        else:
            continue
        rows.append(
            _alert(
                monitoring_run_id,
                str(record["domain"]),
                severity,
                "domain_health_below_threshold",
                str(record["domain"]),
                f"{score:.2f}",
                f"{thresholds.minimum_pipeline_health_score:.2f}",
                "Domain health score is below the configured platform threshold.",
                "Review domain deductions and upstream evidence.",
            )
        )
    if not rows:
        rows.append(
            _alert(
                monitoring_run_id,
                "platform",
                "info",
                "monitoring_completed",
                "all_domains",
                "0",
                "0",
                "All required monitoring checks completed without warning or critical alerts.",
                "Continue standard local evidence monitoring.",
            )
        )
    frame = pd.DataFrame(rows)
    frame["severity_sort"] = frame["severity"].map(SEVERITY_ORDER)
    return frame.sort_values(
        ["severity_sort", "domain", "alert_type", "affected_artifact"],
        ignore_index=True,
    ).drop(columns=["severity_sort"])


def deterministic_alert_id(
    monitoring_run_id: str,
    domain: str,
    severity: str,
    alert_type: str,
    affected_artifact: str,
) -> str:
    """Build stable monitoring alert IDs."""
    digest = hashlib.sha256(
        f"{monitoring_run_id}|{domain}|{severity}|{alert_type}|{affected_artifact}".encode()
    ).hexdigest()
    return f"MO-{digest[:12]}"


def _alert(
    monitoring_run_id: str,
    domain: str,
    severity: str,
    alert_type: str,
    affected_artifact: str,
    observed_value: str,
    threshold_value: str,
    message: str,
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "monitoring_run_id": monitoring_run_id,
        "alert_id": deterministic_alert_id(
            monitoring_run_id, domain, severity, alert_type, affected_artifact
        ),
        "domain": domain,
        "severity": severity,
        "alert_type": alert_type,
        "affected_artifact": affected_artifact,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "message": message,
        "recommended_action": recommended_action,
        "synthetic_data_flag": True,
    }
