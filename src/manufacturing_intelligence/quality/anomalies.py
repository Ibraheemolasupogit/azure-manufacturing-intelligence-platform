"""Deterministic quality anomaly scoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

from manufacturing_intelligence.quality.config import AnomalySettings
from manufacturing_intelligence.quality.control_charts import CONTROL_GRAIN


def calculate_anomaly_scores(
    observations: pd.DataFrame,
    settings: AnomalySettings,
    *,
    random_seed: int,
) -> pd.DataFrame:
    """Calculate robust z-score and deterministic Isolation Forest diagnostics."""
    frame = observations.sort_values(
        [*CONTROL_GRAIN, "inspection_timestamp", "inspection_id"]
    ).copy()
    robust_rows = _robust_zscores(frame, settings)
    isolation_rows = _isolation_forest_scores(frame, settings, random_seed=random_seed)
    result = robust_rows.merge(isolation_rows, on="inspection_id", how="left")
    result["combined_anomaly_flag"] = (
        result["robust_zscore_anomaly_flag"] | result["isolation_forest_anomaly_flag"]
    )
    result["anomaly_score_0_100"] = result[
        ["robust_zscore_score_0_100", "isolation_forest_score_0_100"]
    ].max(axis=1)
    return result.sort_values("inspection_id", ignore_index=True)


def _robust_zscores(frame: pd.DataFrame, settings: AnomalySettings) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _keys, group in frame.groupby(CONTROL_GRAIN, sort=True):
        history: list[float] = []
        for record in group.to_dict("records"):
            value = float(record["measured_value"])
            status = "insufficient_history"
            robust_z = 0.0
            flag = False
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
                    "inspection_id": record["inspection_id"],
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
    frame: pd.DataFrame, settings: AnomalySettings, *, random_seed: int
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    features = _feature_frame(frame)
    for _keys, group in frame.groupby(CONTROL_GRAIN, sort=True):
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
        for inspection_id, raw_score, flag in zip(
            group["inspection_id"], raw_scores, flags, strict=True
        ):
            rows.append(
                {
                    "inspection_id": inspection_id,
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
    span = (frame["upper_specification_limit"] - frame["lower_specification_limit"]).replace(0, 1)
    center = frame["lower_specification_limit"] + span / 2.0
    nearest = pd.concat(
        [
            (frame["measured_value"] - frame["lower_specification_limit"]).abs(),
            (frame["upper_specification_limit"] - frame["measured_value"]).abs(),
        ],
        axis=1,
    ).min(axis=1)
    return pd.DataFrame(
        {
            "normalised_center_distance": (frame["measured_value"] - center).abs() / span,
            "normalised_nearest_limit_distance": nearest / span,
            "measured_value_within_spec_range": (
                frame["measured_value"] - frame["lower_specification_limit"]
            )
            / span,
            "sample_size": frame["sample_size"].astype(float),
            "defective_unit_rate": frame["defective_unit_rate"].astype(float),
            "cycle_time_ratio": frame["cycle_time_ratio"].fillna(0).astype(float),
            "production_yield": frame["production_yield"].fillna(0).astype(float),
        }
    )
