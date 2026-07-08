"""Maintenance anomaly scoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

from manufacturing_intelligence.maintenance.config import AnomalySettings

ANOMALY_GRAIN = ["machine_id", "sensor_type", "measurement_unit"]


def calculate_anomaly_scores(
    features: pd.DataFrame,
    settings: AnomalySettings,
    *,
    random_seed: int,
) -> pd.DataFrame:
    """Calculate robust z-score and deterministic Isolation Forest scores."""
    ordered = features.sort_values([*ANOMALY_GRAIN, "event_timestamp", "sensor_event_id"]).copy()
    robust = _robust_zscores(ordered, settings)
    isolation = _isolation_forest_scores(ordered, settings, random_seed=random_seed)
    result = robust.merge(isolation, on="sensor_event_id", how="left")
    result["combined_anomaly_flag"] = (
        result["robust_zscore_anomaly_flag"] | result["isolation_forest_anomaly_flag"]
    )
    result["anomaly_score_0_100"] = result[
        ["robust_zscore_score_0_100", "isolation_forest_score_0_100"]
    ].max(axis=1)
    return result.sort_values("sensor_event_id", ignore_index=True)


def _robust_zscores(frame: pd.DataFrame, settings: AnomalySettings) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _keys, group in frame.groupby(ANOMALY_GRAIN, sort=True):
        history: list[float] = []
        for record in group.to_dict("records"):
            value = float(record["sensor_value"])
            robust_z = 0.0
            flag = False
            status = "insufficient_history"
            if (
                settings.enabled
                and "robust_zscore" in settings.models
                and len(history) >= settings.minimum_training_rows
            ):
                series = pd.Series(history, dtype="float64")
                median = float(series.median())
                mad = float((series - median).abs().median())
                if mad == 0:
                    status = "zero_mad_fallback"
                else:
                    robust_z = 0.6745 * (value - median) / mad
                    flag = abs(robust_z) >= settings.robust_zscore_threshold
                    status = "calculated"
            rows.append(
                {
                    "sensor_event_id": record["sensor_event_id"],
                    "robust_zscore": robust_z,
                    "robust_zscore_abs": abs(robust_z),
                    "robust_zscore_threshold": settings.robust_zscore_threshold,
                    "robust_zscore_anomaly_flag": flag,
                    "robust_zscore_status": status,
                    "robust_zscore_score_0_100": min(
                        100.0,
                        abs(robust_z) / settings.robust_zscore_threshold * 100.0
                        if settings.robust_zscore_threshold > 0
                        else 0.0,
                    ),
                }
            )
            history.append(value)
    return pd.DataFrame(rows)


def _isolation_forest_scores(
    frame: pd.DataFrame,
    settings: AnomalySettings,
    *,
    random_seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    features = _feature_frame(frame)
    for _keys, group in frame.groupby(ANOMALY_GRAIN, sort=True):
        group_features = features.loc[group.index]
        status = "disabled"
        raw_scores = np.zeros(len(group))
        flags = np.zeros(len(group), dtype=bool)
        if settings.enabled and "isolation_forest" in settings.models:
            if len(group) >= settings.minimum_training_rows:
                model = IsolationForest(
                    n_estimators=50,
                    contamination=settings.contamination,
                    random_state=random_seed,
                )
                model.fit(group_features)
                raw_scores = -model.decision_function(group_features)
                flags = model.predict(group_features) == -1
                status = "retrospective_batch_diagnostic"
            else:
                status = "insufficient_history_fallback"
        max_abs = max(float(np.max(np.abs(raw_scores))), 0.000001)
        for sensor_event_id, raw_score, flag in zip(
            group["sensor_event_id"], raw_scores, flags, strict=True
        ):
            rows.append(
                {
                    "sensor_event_id": sensor_event_id,
                    "isolation_forest_score": float(raw_score),
                    "isolation_forest_score_0_100": min(
                        100.0, abs(float(raw_score)) / max_abs * 100.0
                    ),
                    "isolation_forest_anomaly_flag": bool(flag),
                    "isolation_forest_status": status,
                    "isolation_forest_contamination": settings.contamination,
                    "isolation_forest_score_interpretation": (
                        "relative_anomaly_score_not_probability"
                    ),
                }
            )
    return pd.DataFrame(rows)


def _feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    span = (frame["critical_threshold"] - frame["warning_threshold"]).replace(0, 1)
    return pd.DataFrame(
        {
            "sensor_value": frame["sensor_value"].astype(float),
            "normalised_threshold_distance": frame[
                "normalised_distance_to_nearest_threshold"
            ].astype(float),
            "runtime_hours": frame["runtime_hours"].astype(float),
            "service_hours_since_maintenance": frame["service_hours_since_maintenance"].astype(
                float
            ),
            "warning_breach_flag": frame["warning_breach_flag"].astype(float),
            "critical_breach_flag": frame["critical_breach_flag"].astype(float),
            "rolling_mean_3": frame["rolling_mean_3"].astype(float),
            "rolling_std_3": frame["rolling_std_3"].astype(float),
            "threshold_span_position": (frame["sensor_value"] - frame["warning_threshold"]) / span,
        }
    )
