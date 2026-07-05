"""Forecast evaluation metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd  # type: ignore[import-untyped]


def metrics(actual: Iterable[float], predicted: Iterable[float]) -> dict[str, float | None]:
    """Calculate deterministic forecast metrics."""
    pairs = [(float(a), float(p)) for a, p in zip(actual, predicted, strict=True)]
    if not pairs:
        return {
            "mae": None,
            "rmse": None,
            "wape": None,
            "smape": None,
            "bias": None,
            "absolute_bias": None,
        }
    errors = [p - a for a, p in pairs]
    absolute_errors = [abs(item) for item in errors]
    mae = sum(absolute_errors) / len(pairs)
    rmse = math.sqrt(sum(error * error for error in errors) / len(pairs))
    denominator = sum(abs(actual_value) for actual_value, _ in pairs)
    wape = None if denominator == 0 else sum(absolute_errors) / denominator
    smape_terms = []
    for actual_value, predicted_value in pairs:
        denom = abs(actual_value) + abs(predicted_value)
        smape_terms.append(0.0 if denom == 0 else 2 * abs(predicted_value - actual_value) / denom)
    bias = sum(errors) / len(pairs)
    return {
        "mae": mae,
        "rmse": rmse,
        "wape": wape,
        "smape": sum(smape_terms) / len(smape_terms),
        "bias": bias,
        "absolute_bias": abs(bias),
    }


def metrics_frame(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Calculate metrics by group."""
    rows: list[dict[str, object]] = []
    for keys, group in frame.groupby(group_columns, dropna=False):
        key_values = keys if isinstance(keys, tuple) else (keys,)
        row = dict(zip(group_columns, key_values, strict=True))
        row.update(metrics(group["actual"], group["prediction"]))
        row["row_count"] = len(group)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_columns).reset_index(drop=True)
