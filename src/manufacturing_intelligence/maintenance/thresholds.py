"""Sensor threshold compliance calculations."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.maintenance.config import ThresholdSettings


def evaluate_thresholds(equipment: pd.DataFrame, settings: ThresholdSettings) -> pd.DataFrame:
    """Calculate threshold status, distances, and consistency flags."""
    frame = equipment.copy()
    frame["sensor_value"] = frame["measurement"].astype(float)
    frame["source_threshold_status"] = frame["threshold_status"].astype(str)
    frame["distance_from_warning_threshold"] = frame["warning_threshold"] - frame["sensor_value"]
    frame["distance_from_critical_threshold"] = frame["critical_threshold"] - frame["sensor_value"]
    span = (frame["critical_threshold"] - frame["warning_threshold"]).replace(0, 1)
    frame["normalised_distance_to_nearest_threshold"] = (
        pd.concat(
            [
                frame["distance_from_warning_threshold"].abs(),
                frame["distance_from_critical_threshold"].abs(),
            ],
            axis=1,
        ).min(axis=1)
        / span
    )
    frame["warning_breach_flag"] = (frame["sensor_value"] >= frame["warning_threshold"]) & (
        frame["sensor_value"] < frame["critical_threshold"]
    )
    frame["critical_breach_flag"] = frame["sensor_value"] >= frame["critical_threshold"]
    frame["near_warning_flag"] = (
        (
            frame["sensor_value"]
            >= frame["warning_threshold"] * (1 - settings.warning_margin_fraction)
        )
        & ~frame["warning_breach_flag"]
        & ~frame["critical_breach_flag"]
    )
    frame["near_critical_flag"] = (
        frame["sensor_value"]
        >= frame["critical_threshold"] * (1 - settings.critical_margin_fraction)
    ) & ~frame["critical_breach_flag"]
    frame["near_threshold_flag"] = frame["near_warning_flag"] | frame["near_critical_flag"]
    frame["calculated_threshold_status"] = "normal"
    frame.loc[frame["warning_breach_flag"], "calculated_threshold_status"] = "warning"
    frame.loc[frame["critical_breach_flag"], "calculated_threshold_status"] = "critical"
    frame["threshold_consistency_flag"] = (
        frame["source_threshold_status"] == frame["calculated_threshold_status"]
    )
    frame["threshold_breach_direction"] = frame.apply(
        lambda row: (
            "above_upper_threshold"
            if row["warning_breach_flag"] or row["critical_breach_flag"]
            else "none"
        ),
        axis=1,
    )
    frame["threshold_margin_percentage"] = (
        frame["distance_from_warning_threshold"] / frame["warning_threshold"].replace(0, 1)
    ) * 100.0
    frame["threshold_breach_component_score"] = 0.0
    frame.loc[frame["near_threshold_flag"], "threshold_breach_component_score"] = 35.0
    frame.loc[frame["warning_breach_flag"], "threshold_breach_component_score"] = 70.0
    frame.loc[frame["critical_breach_flag"], "threshold_breach_component_score"] = 100.0
    return frame
