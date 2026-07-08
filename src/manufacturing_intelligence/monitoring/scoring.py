"""Monitoring health scoring."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.monitoring.config import MonitoringThresholds


def health_label(score: float, thresholds: MonitoringThresholds) -> str:
    """Map score to monitoring health labels."""
    if score < thresholds.critical_score_threshold:
        return "critical"
    if score < thresholds.warning_score_threshold:
        return "degraded"
    if score < thresholds.minimum_pipeline_health_score:
        return "watch"
    return "healthy"


def domain_health_scores(
    *,
    manifests: dict[str, dict[str, Any]],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> pd.DataFrame:
    """Calculate deterministic domain health scores."""
    rows = [
        _generation_score(manifests["generation"], integrity, lineage, thresholds),
        _ingestion_score(
            manifests["ingestion"], manifests["validation"], integrity, lineage, thresholds
        ),
        _forecast_score(manifests["forecasting"], integrity, lineage, thresholds),
        _inventory_score(manifests["inventory"], integrity, lineage, thresholds),
        _quality_score(manifests["quality"], integrity, lineage, thresholds),
        _maintenance_score(manifests["maintenance"], integrity, lineage, thresholds),
    ]
    frame = pd.DataFrame(rows)
    frame["health_label"] = frame["health_score"].map(
        lambda score: health_label(float(score), thresholds)
    )
    return frame.sort_values("domain", ignore_index=True)


def overall_platform_health(domain_scores: pd.DataFrame) -> float:
    """Calculate overall platform health score."""
    return float(domain_scores["health_score"].mean()) if not domain_scores.empty else 0.0


def _base_score(
    domain: str, integrity: pd.DataFrame, lineage: pd.DataFrame
) -> tuple[float, list[str]]:
    score = 100.0
    deductions: list[str] = []
    failed_integrity = int(
        ((integrity["domain"] == domain) & (integrity["integrity_status"] != "passed")).sum()
    )
    if failed_integrity:
        penalty = min(60.0, failed_integrity * 15.0)
        score -= penalty
        deductions.append(f"integrity_failures={failed_integrity} penalty={penalty}")
    lineage_rows = lineage[lineage["domain"] == domain]
    if not lineage_rows.empty:
        lineage_score = float(lineage_rows["lineage_completeness_score"].min())
        if lineage_score < 100:
            penalty = min(30.0, (100.0 - lineage_score) * 0.5)
            score -= penalty
            deductions.append(f"lineage_score={lineage_score:.2f} penalty={penalty:.2f}")
    return score, deductions


def _generation_score(
    manifest: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("generation", integrity, lineage)
    if not manifest.get("synthetic_data_only"):
        score -= 50
        deductions.append("synthetic_data_only_missing penalty=50")
    if manifest.get("status") != "success":
        score -= 80
        deductions.append("generation_status_not_success penalty=80")
    return _row("generation", score, deductions, thresholds)


def _ingestion_score(
    manifest: dict[str, Any],
    validation: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("ingestion", integrity, lineage)
    quarantine_rate = float(validation.get("quarantine_rate", manifest.get("quarantine_rate", 1.0)))
    if quarantine_rate > thresholds.maximum_allowed_quarantine_rate:
        score -= min(40.0, quarantine_rate * 100.0)
        deductions.append(f"quarantine_rate={quarantine_rate:.4f}")
    if validation.get("validation_status") != "success":
        score -= 80
        deductions.append("validation_status_not_success penalty=80")
    return _row("ingestion", score, deductions, thresholds, quarantine_rate=quarantine_rate)


def _forecast_score(
    manifest: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("forecasting", integrity, lineage)
    warnings = len(manifest.get("warnings", []))
    if warnings > thresholds.maximum_forecast_warning_count:
        score -= min(30.0, (warnings - thresholds.maximum_forecast_warning_count) * 2.0)
        deductions.append(f"forecast_warnings={warnings}")
    if int(manifest.get("output_files", {}).get("demand_forecast", {}).get("row_count", 0)) <= 0:
        score -= 60
        deductions.append("demand_forecast_empty penalty=60")
    return _row("forecasting", score, deductions, thresholds, warning_count=warnings)


def _inventory_score(
    manifest: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("inventory", integrity, lineage)
    metrics = manifest.get("metrics_summary", {})
    high = int(metrics.get("high_priority_count", metrics.get("high_risk_item_count", 0)))
    critical = int(
        metrics.get("critical_priority_count", metrics.get("critical_risk_item_count", 0))
    )
    if high > thresholds.maximum_inventory_high_risk_count:
        score -= min(30.0, high - thresholds.maximum_inventory_high_risk_count)
        deductions.append(f"inventory_high_risk_count={high}")
    if critical:
        score -= min(25.0, critical * 2.0)
        deductions.append(f"inventory_critical_risk_count={critical}")
    return _row(
        "inventory",
        score,
        deductions,
        thresholds,
        high_risk_count=high,
        critical_risk_count=critical,
    )


def _quality_score(
    manifest: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("quality", integrity, lineage)
    summary = manifest.get("kpi_summary", {})
    high = int(summary.get("high_risk_alert_count", 0))
    critical = int(summary.get("critical_risk_alert_count", 0))
    if high > thresholds.maximum_quality_high_risk_alerts:
        score -= min(30.0, high - thresholds.maximum_quality_high_risk_alerts)
        deductions.append(f"quality_high_risk_alerts={high}")
    if critical:
        score -= min(20.0, critical * 2.0)
        deductions.append(f"quality_critical_alerts={critical}")
    return _row(
        "quality", score, deductions, thresholds, high_risk_count=high, critical_risk_count=critical
    )


def _maintenance_score(
    manifest: dict[str, Any],
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    thresholds: MonitoringThresholds,
) -> dict[str, Any]:
    score, deductions = _base_score("maintenance", integrity, lineage)
    summary = manifest.get("kpi_summary", {})
    high = int(summary.get("high_risk_alert_count", 0))
    critical = int(summary.get("critical_risk_alert_count", 0))
    if high > thresholds.maximum_maintenance_high_risk_alerts:
        score -= min(30.0, high - thresholds.maximum_maintenance_high_risk_alerts)
        deductions.append(f"maintenance_high_risk_alerts={high}")
    if critical:
        score -= min(20.0, critical * 2.0)
        deductions.append(f"maintenance_critical_alerts={critical}")
    return _row(
        "maintenance",
        score,
        deductions,
        thresholds,
        high_risk_count=high,
        critical_risk_count=critical,
    )


def _row(
    domain: str,
    score: float,
    deductions: list[str],
    thresholds: MonitoringThresholds,
    **metrics: Any,
) -> dict[str, Any]:
    clipped = max(0.0, min(100.0, score))
    return {
        "domain": domain,
        "health_score": clipped,
        "health_label": health_label(clipped, thresholds),
        "deductions": "; ".join(deductions),
        **metrics,
    }
