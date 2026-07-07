"""Quality-risk scoring and recommendation reasons."""

from __future__ import annotations

import hashlib

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.quality.config import RiskSettings

RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_SCORE = {"none": 0.0, "low": 20.0, "medium": 50.0, "high": 85.0, "critical": 100.0}


def score_quality_risk(observations: pd.DataFrame, settings: RiskSettings) -> pd.DataFrame:
    """Calculate transparent 0-100 quality-risk scores."""
    frame = observations.copy()
    frame["specification_failure_component_score"] = frame["calculated_specification_result"].map(
        {"pass": 0.0, "fail": 100.0}
    )
    frame["near_limit_component_score"] = frame["near_limit_flag"].map({True: 40.0, False: 0.0})
    frame["spc_signal_component_score"] = frame["spc_signal_flag"].map({True: 100.0, False: 0.0})
    frame["anomaly_component_score"] = frame["anomaly_score_0_100"].clip(lower=0, upper=100)
    frame["defect_severity_component_score"] = frame["severity"].map(SEVERITY_SCORE).fillna(0.0)
    frame["defective_unit_rate_component_score"] = (
        frame["defective_unit_rate"].clip(lower=0, upper=1) * 100.0
    )
    recurrence = frame.groupby(["machine_id", "quality_metric"])[
        "calculated_specification_result"
    ].transform(lambda series: (series == "fail").cumsum())
    frame["recurrence_component_score"] = (recurrence.clip(upper=5) / 5.0) * 100.0
    frame["quality_risk_score"] = (
        frame["specification_failure_component_score"] * settings.specification_failure_weight
        + frame["spc_signal_component_score"] * settings.spc_signal_weight
        + frame["anomaly_component_score"] * settings.anomaly_score_weight
        + frame["defect_severity_component_score"] * settings.defect_severity_weight
    ).clip(lower=0, upper=100)
    frame["risk_level"] = frame["quality_risk_score"].map(
        lambda score: risk_level(float(score), settings)
    )
    frame["investigation_priority"] = frame["risk_level"]
    frame["risk_level_sort"] = frame["risk_level"].map(RISK_ORDER)
    frame["recommended_action"] = frame.apply(_recommended_action, axis=1)
    frame["recommendation_reason"] = frame.apply(_recommendation_reason, axis=1)
    return frame.sort_values(
        ["risk_level_sort", "quality_risk_score", "inspection_timestamp", "inspection_id"],
        ascending=[True, False, True, True],
        ignore_index=True,
    )


def build_alerts(observations: pd.DataFrame, quality_run_id: str) -> pd.DataFrame:
    """Generate deterministic quality alerts."""
    alert_frame = observations[
        (observations["risk_level"].isin(["high", "critical"]))
        | (observations["calculated_specification_result"] == "fail")
        | (observations["spc_signal_flag"])
        | (observations["combined_anomaly_flag"])
        | (observations["near_limit_flag"])
    ].copy()
    alert_frame["quality_run_id"] = quality_run_id
    alert_frame["alert_id"] = alert_frame.apply(
        lambda row: deterministic_alert_id(quality_run_id, str(row["inspection_id"])),
        axis=1,
    )
    alert_frame["anomaly_flags"] = alert_frame.apply(_anomaly_flags, axis=1)
    alert_frame["investigation_context"] = alert_frame.apply(
        lambda row: investigation_context(row, observations), axis=1
    )
    columns = [
        "quality_run_id",
        "alert_id",
        "inspection_id",
        "inspection_timestamp",
        "plant_id",
        "production_line_id",
        "machine_id",
        "batch_id",
        "product_id",
        "quality_metric",
        "measurement_unit",
        "measured_value",
        "lower_specification_limit",
        "upper_specification_limit",
        "source_inspection_result",
        "calculated_specification_result",
        "specification_consistency_flag",
        "near_limit_flag",
        "spc_rule_codes",
        "robust_zscore",
        "isolation_forest_score",
        "anomaly_flags",
        "defect_category",
        "severity",
        "quality_risk_score",
        "risk_level",
        "recommended_action",
        "recommendation_reason",
        "investigation_context",
        "synthetic_data_flag",
    ]
    return alert_frame[columns].sort_values(
        ["risk_level", "quality_risk_score", "inspection_timestamp", "inspection_id"],
        ascending=[True, False, True, True],
        ignore_index=True,
    )


def risk_level(score: float, settings: RiskSettings) -> str:
    """Map quality-risk score to labels."""
    if score >= settings.critical_threshold:
        return "critical"
    if score >= settings.high_threshold:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def deterministic_alert_id(quality_run_id: str, inspection_id: str) -> str:
    """Build stable alert IDs."""
    digest = hashlib.sha256(f"{quality_run_id}|{inspection_id}".encode()).hexdigest()
    return f"QA-{digest[:12]}"


def investigation_context(row: pd.Series, observations: pd.DataFrame) -> str:
    """Return deterministic non-causal investigation context."""
    product_failures = int(
        (
            (observations["product_id"] == row["product_id"])
            & (observations["calculated_specification_result"] == "fail")
        ).sum()
    )
    machine_failures = int(
        (
            (observations["machine_id"] == row["machine_id"])
            & (observations["calculated_specification_result"] == "fail")
        ).sum()
    )
    batch_checks = int((observations["batch_id"] == row["batch_id"]).sum())
    category = row["defect_category"] or "none"
    parts = [
        f"product_failure_count={product_failures}",
        f"machine_failure_count={machine_failures}",
        f"batch_check_count={batch_checks}",
        f"recurring_defect_category={category}",
        "context_is_investigative_not_causal",
    ]
    if bool(row["near_limit_flag"]):
        parts.append("metric_near_specification_limit")
    if float(row["downtime_duration_minutes"]) > 0:
        parts.append("recent_production_downtime_present")
    return "; ".join(parts)


def _recommended_action(row: pd.Series) -> str:
    if row["calculated_specification_result"] == "fail":
        return "investigate_specification_failure"
    if row["spc_signal_flag"]:
        return "review_process_control_signal"
    if row["combined_anomaly_flag"]:
        return "review_anomalous_quality_measurement"
    if row["near_limit_flag"]:
        return "monitor_near_limit_quality_metric"
    return "continue_standard_quality_monitoring"


def _recommendation_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if row["calculated_specification_result"] == "fail":
        reasons.append("measurement is outside specification limits")
    if row["spc_signal_flag"]:
        reasons.append(f"SPC rules triggered: {row['spc_rule_codes']}")
    if row["combined_anomaly_flag"]:
        reasons.append("deterministic anomaly score exceeded configured threshold")
    if row["near_limit_flag"]:
        reasons.append("measurement is near a specification limit")
    if not reasons:
        reasons.append("quality risk remained below alert thresholds")
    return "; ".join(reasons)


def _anomaly_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if row["robust_zscore_anomaly_flag"]:
        flags.append("robust_zscore")
    if row["isolation_forest_anomaly_flag"]:
        flags.append("isolation_forest")
    return ";".join(flags)
