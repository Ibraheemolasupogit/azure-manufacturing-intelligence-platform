"""Maintenance summary tables."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]


def machine_summary(scored: pd.DataFrame, alerts: pd.DataFrame) -> pd.DataFrame:
    """Summarise maintenance analytics by machine."""
    grouped = scored.groupby(["plant_id", "production_line_id", "machine_id"], sort=True).agg(
        equipment_event_count=("sensor_event_id", "count"),
        unique_sensor_count=("sensor_id", "nunique"),
        warning_breach_count=("warning_breach_flag", "sum"),
        critical_breach_count=("critical_breach_flag", "sum"),
        anomaly_count=("combined_anomaly_flag", "sum"),
        degradation_signal_count=("degradation_signal_flag", "sum"),
        average_failure_risk_score=("failure_risk_score", "mean"),
        maximum_failure_risk_score=("failure_risk_score", "max"),
        average_equipment_health_score=("equipment_health_score", "mean"),
    )
    result = grouped.reset_index()
    alert_counts = alerts.groupby("machine_id", sort=True).size().rename("machine_alert_count")
    result = result.merge(alert_counts, on="machine_id", how="left")
    result["machine_alert_count"] = result["machine_alert_count"].fillna(0).astype(int)
    result["machine_review_priority_count"] = (
        result["critical_breach_count"]
        + result["degradation_signal_count"]
        + result["anomaly_count"]
    )
    result["dominant_risk_level"] = result["maximum_failure_risk_score"].map(_summary_level)
    return result.sort_values(
        ["maximum_failure_risk_score", "machine_id"], ascending=[False, True], ignore_index=True
    )


def sensor_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Summarise maintenance analytics by machine sensor."""
    grouped = scored.groupby(
        [
            "plant_id",
            "production_line_id",
            "machine_id",
            "sensor_id",
            "sensor_type",
            "measurement_unit",
        ],
        sort=True,
    ).agg(
        equipment_event_count=("sensor_event_id", "count"),
        average_sensor_value=("sensor_value", "mean"),
        maximum_sensor_value=("sensor_value", "max"),
        warning_breach_count=("warning_breach_flag", "sum"),
        critical_breach_count=("critical_breach_flag", "sum"),
        near_threshold_count=("near_threshold_flag", "sum"),
        anomaly_count=("combined_anomaly_flag", "sum"),
        degradation_signal_count=("degradation_signal_flag", "sum"),
        maximum_failure_risk_score=("failure_risk_score", "max"),
    )
    return grouped.reset_index().sort_values(
        ["maximum_failure_risk_score", "machine_id", "sensor_id"],
        ascending=[False, True, True],
        ignore_index=True,
    )


def risk_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Summarise maintenance risk labels."""
    grouped = scored.groupby("risk_level", sort=True).agg(
        equipment_event_count=("sensor_event_id", "count"),
        average_failure_risk_score=("failure_risk_score", "mean"),
        warning_breach_count=("warning_breach_flag", "sum"),
        critical_breach_count=("critical_breach_flag", "sum"),
        degradation_signal_count=("degradation_signal_flag", "sum"),
        anomaly_count=("combined_anomaly_flag", "sum"),
    )
    return grouped.reset_index()


def _summary_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
