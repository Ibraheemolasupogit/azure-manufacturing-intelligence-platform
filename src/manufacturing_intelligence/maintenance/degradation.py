"""Deterministic equipment degradation indicators."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.maintenance.config import DegradationSettings


def calculate_degradation_features(
    frame: pd.DataFrame, settings: DegradationSettings
) -> pd.DataFrame:
    """Calculate chronological degradation features without future leakage."""
    ordered = frame.sort_values(
        ["machine_id", "sensor_type", "measurement_unit", "event_timestamp", "sensor_event_id"]
    ).copy()
    rows: list[dict[str, Any]] = []
    for _keys, group in ordered.groupby(
        ["machine_id", "sensor_type", "measurement_unit"], sort=True
    ):
        history: list[float] = []
        warning_history: list[bool] = []
        critical_history: list[bool] = []
        for record in group.to_dict("records"):
            value = float(record["sensor_value"])
            history_with_current = [*history, value]
            recent = history_with_current[-settings.rolling_windows[0] :]
            long = history_with_current[-settings.rolling_windows[-1] :]
            status = (
                "calculated"
                if len(history_with_current) >= settings.minimum_observations
                else "insufficient_history"
            )
            slope = _slope(long) if status == "calculated" else 0.0
            direction_risky = (
                slope > 0 and record["sensor_type"] in settings.rising_risk_sensor_types
            ) or (slope < 0 and record["sensor_type"] in settings.falling_risk_sensor_types)
            repeated_warning = (
                sum([*warning_history[-3:], bool(record["warning_breach_flag"])]) >= 2
            )
            repeated_critical = (
                sum([*critical_history[-3:], bool(record["critical_breach_flag"])]) >= 1
            )
            score = 0.0
            reasons: list[str] = []
            if status == "calculated" and direction_risky:
                score += min(45.0, abs(slope) * 12.0)
                reasons.append("sensor_trend_moving_toward_risk")
            if repeated_warning:
                score += 25.0
                reasons.append("repeated_warning_breaches")
            if repeated_critical:
                score += 45.0
                reasons.append("recent_critical_breach")
            score += min(20.0, float(record["degradation_index"]) * 20.0)
            rows.append(
                {
                    "sensor_event_id": record["sensor_event_id"],
                    "rolling_mean_3": float(pd.Series(recent).mean()),
                    "rolling_max_3": float(pd.Series(recent).max()),
                    "rolling_std_3": float(pd.Series(recent).std(ddof=0))
                    if len(recent) > 1
                    else 0.0,
                    "rolling_mean_7": float(pd.Series(long).mean()),
                    "rolling_max_7": float(pd.Series(long).max()),
                    "rolling_std_7": float(pd.Series(long).std(ddof=0)) if len(long) > 1 else 0.0,
                    "degradation_slope": slope,
                    "degradation_status": status,
                    "degradation_signal_flag": bool(score >= 40.0 and status == "calculated"),
                    "degradation_score": min(100.0, score) if status == "calculated" else 0.0,
                    "degradation_reason": "; ".join(reasons) if reasons else status,
                }
            )
            history.append(value)
            warning_history.append(bool(record["warning_breach_flag"]))
            critical_history.append(bool(record["critical_breach_flag"]))
    return pd.DataFrame(rows)


def _slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((idx - x_mean) * (value - y_mean) for idx, value in enumerate(values))
    denominator = sum((idx - x_mean) ** 2 for idx in range(n))
    return numerator / denominator if denominator else 0.0
