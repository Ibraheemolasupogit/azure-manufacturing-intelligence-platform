"""Prediction interval helpers."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]


def residual_quantile(predictions: pd.DataFrame, selected_model: str, level: float) -> float:
    """Return empirical absolute residual quantile for prediction intervals."""
    selected = predictions[predictions["model"] == selected_model].copy()
    if selected.empty:
        return 0.0
    residuals = (selected["actual"] - selected["prediction"]).abs()
    if residuals.empty:
        return 0.0
    return float(residuals.quantile(level))


def apply_intervals(frame: pd.DataFrame, residual_width: float, level: float) -> pd.DataFrame:
    """Apply non-negative deterministic interval bounds."""
    output = frame.copy()
    output["prediction_interval_level"] = level
    output["lower_bound"] = (output["point_forecast"] - residual_width).clip(lower=0)
    output["upper_bound"] = output["point_forecast"] + residual_width
    return output
