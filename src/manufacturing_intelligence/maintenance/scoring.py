"""Maintenance risk scoring and alert generation."""

from __future__ import annotations

import hashlib

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.maintenance.config import RiskSettings

RISK_SORT = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MAINTENANCE_STATE_SCORE = {
    "normal": 0.0,
    "warning_monitor": 60.0,
    "critical_inspection_required": 100.0,
}


def score_maintenance_risk(features: pd.DataFrame, settings: RiskSettings) -> pd.DataFrame:
    """Calculate transparent maintenance risk and health scores."""
    frame = features.copy()
    max_service = max(float(frame["service_hours_since_maintenance"].max()), 1.0)
    max_runtime = max(float(frame["runtime_hours"].max()), 1.0)
    frame["near_threshold_component_score"] = frame["near_threshold_flag"].map(
        {True: 35.0, False: 0.0}
    )
    frame["anomaly_component_score"] = frame["anomaly_score_0_100"].clip(lower=0, upper=100)
    frame["runtime_risk_score"] = (
        0.65 * frame["service_hours_since_maintenance"] / max_service
        + 0.35 * frame["runtime_hours"] / max_runtime
    ).clip(lower=0, upper=1) * 100.0
    frame["maintenance_state_risk_score"] = (
        frame["maintenance_state"].map(MAINTENANCE_STATE_SCORE).fillna(40.0)
    )
    frame["production_context_score"] = (
        0.5 * frame["recent_downtime_minutes"].clip(lower=0, upper=60) / 60.0
        + 0.5 * frame["recent_reject_rate"].clip(lower=0, upper=0.2) / 0.2
    ).clip(lower=0, upper=1) * 100.0
    frame["quality_context_score"] = (
        frame["quality_alert_count_for_machine"].clip(lower=0, upper=5) / 5.0 * 100.0
    )
    frame["failure_risk_score"] = (
        frame["threshold_breach_component_score"] * settings.threshold_breach_weight
        + frame["anomaly_component_score"] * settings.anomaly_weight
        + frame["degradation_score"] * settings.degradation_weight
        + frame["runtime_risk_score"] * settings.runtime_weight
        + frame["maintenance_state_risk_score"] * settings.maintenance_state_weight
        + frame["production_context_score"] * settings.production_context_weight
    ).clip(lower=0, upper=100)
    frame["equipment_health_score"] = (100.0 - frame["failure_risk_score"]).clip(lower=0, upper=100)
    frame["risk_level"] = frame["failure_risk_score"].map(
        lambda score: risk_level(float(score), settings)
    )
    frame["maintenance_priority"] = frame["risk_level"]
    frame["risk_level_sort"] = frame["risk_level"].map(RISK_SORT)
    frame["recommended_action"] = frame.apply(_recommended_action, axis=1)
    frame["recommendation_reason"] = frame.apply(_recommendation_reason, axis=1)
    frame["synthetic_data_flag"] = True
    return frame.sort_values(
        [
            "risk_level_sort",
            "failure_risk_score",
            "event_timestamp",
            "machine_id",
            "sensor_event_id",
        ],
        ascending=[True, False, True, True, True],
        ignore_index=True,
    )


def build_alerts(scored: pd.DataFrame, maintenance_run_id: str) -> pd.DataFrame:
    """Build deterministic maintenance alerts."""
    alerts = scored[
        scored["risk_level"].isin(["high", "critical"])
        | scored["warning_breach_flag"]
        | scored["critical_breach_flag"]
        | scored["combined_anomaly_flag"]
        | scored["degradation_signal_flag"]
        | scored["near_threshold_flag"]
    ].copy()
    alerts["maintenance_run_id"] = maintenance_run_id
    alerts["alert_id"] = alerts["sensor_event_id"].map(
        lambda value: deterministic_alert_id(maintenance_run_id, str(value))
    )
    alerts["anomaly_flags"] = alerts.apply(_anomaly_flags, axis=1)
    alerts["investigation_context"] = alerts.apply(
        lambda row: investigation_context(row, scored), axis=1
    )
    columns = [
        "maintenance_run_id",
        "alert_id",
        "sensor_event_id",
        "event_timestamp",
        "plant_id",
        "production_line_id",
        "machine_id",
        "sensor_id",
        "sensor_type",
        "measurement_unit",
        "sensor_value",
        "source_threshold_status",
        "calculated_threshold_status",
        "threshold_consistency_flag",
        "warning_breach_flag",
        "critical_breach_flag",
        "near_threshold_flag",
        "robust_zscore",
        "isolation_forest_score",
        "anomaly_flags",
        "degradation_score",
        "runtime_risk_score",
        "maintenance_state",
        "failure_risk_score",
        "equipment_health_score",
        "risk_level",
        "maintenance_priority",
        "recommended_action",
        "recommendation_reason",
        "investigation_context",
        "synthetic_data_flag",
    ]
    return alerts[columns].sort_values(
        ["risk_level", "failure_risk_score", "event_timestamp", "machine_id", "sensor_event_id"],
        ascending=[True, False, True, True, True],
        ignore_index=True,
    )


def risk_level(score: float, settings: RiskSettings) -> str:
    """Map score to maintenance risk labels."""
    if score >= settings.critical_threshold:
        return "critical"
    if score >= settings.high_threshold:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def deterministic_alert_id(maintenance_run_id: str, sensor_event_id: str) -> str:
    """Build a stable alert ID."""
    digest = hashlib.sha256(f"{maintenance_run_id}|{sensor_event_id}".encode()).hexdigest()
    return f"MA-{digest[:12]}"


def investigation_context(row: pd.Series, observations: pd.DataFrame) -> str:
    """Return deterministic investigation context without causal claims."""
    machine_rows = observations[observations["machine_id"] == row["machine_id"]]
    sensor_rows = machine_rows[machine_rows["sensor_type"] == row["sensor_type"]]
    parts = [
        f"machine_warning_breach_count={int(machine_rows['warning_breach_flag'].sum())}",
        f"machine_critical_breach_count={int(machine_rows['critical_breach_flag'].sum())}",
        f"sensor_type_anomaly_count={int(sensor_rows['combined_anomaly_flag'].sum())}",
        "context_is_investigative_not_causal",
    ]
    if bool(row["degradation_signal_flag"]):
        parts.append(str(row["degradation_reason"]))
    if float(row["runtime_risk_score"]) >= 70:
        parts.append("high_runtime_since_service_proxy")
    if row["maintenance_state"] != "normal":
        parts.append(f"maintenance_state={row['maintenance_state']}")
    if float(row["recent_downtime_minutes"]) > 0:
        parts.append("recent_production_downtime_present")
    if int(row["quality_alert_count_for_machine"]) > 0:
        parts.append("quality_alert_context_available")
    return "; ".join(parts)


def _recommended_action(row: pd.Series) -> str:
    if bool(row["critical_breach_flag"]):
        return "prioritise_non_binding_maintenance_review"
    if bool(row["warning_breach_flag"]):
        return "review_sensor_threshold_breach"
    if bool(row["degradation_signal_flag"]):
        return "review_degradation_trend"
    if bool(row["combined_anomaly_flag"]):
        return "review_anomalous_equipment_reading"
    if bool(row["near_threshold_flag"]):
        return "monitor_near_threshold_sensor"
    return "continue_standard_monitoring"


def _recommendation_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if bool(row["critical_breach_flag"]):
        reasons.append("sensor value breached critical threshold")
    if bool(row["warning_breach_flag"]):
        reasons.append("sensor value breached warning threshold")
    if bool(row["near_threshold_flag"]):
        reasons.append("sensor value is near a configured threshold")
    if bool(row["degradation_signal_flag"]):
        reasons.append(f"degradation signal: {row['degradation_reason']}")
    if bool(row["combined_anomaly_flag"]):
        reasons.append("deterministic anomaly score exceeded configured threshold")
    if float(row["runtime_risk_score"]) >= 70:
        reasons.append("runtime/service proxy is elevated")
    if not reasons:
        reasons.append("maintenance risk remained below alert thresholds")
    return "; ".join(reasons)


def _anomaly_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if bool(row["robust_zscore_anomaly_flag"]):
        flags.append("robust_zscore")
    if bool(row["isolation_forest_anomaly_flag"]):
        flags.append("isolation_forest")
    return ";".join(flags)
