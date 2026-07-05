"""Model selection."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

MODEL_PRIORITY = {
    "seasonal_naive": 0,
    "moving_average": 1,
    "linear_regression": 2,
    "random_forest": 3,
}


def select_model(model_comparison: pd.DataFrame, metric: str) -> dict[str, object]:
    """Select one global model from validation metrics only."""
    candidates = model_comparison[model_comparison["split"] == "validation"].copy()
    candidates["selection_value"] = candidates[metric].fillna(float("inf"))
    candidates["priority"] = candidates["model"].map(MODEL_PRIORITY).fillna(99)
    ordered = candidates.sort_values(
        ["selection_value", "mae", "absolute_bias", "priority", "model"],
        ignore_index=True,
    )
    selected = ordered.iloc[0].to_dict()
    return {
        "selected_model": selected["model"],
        "selection_metric": metric,
        "validation_score": selected[metric],
        "validation_mae": selected["mae"],
        "validation_absolute_bias": selected["absolute_bias"],
        "selection_reason": (
            f"Lowest validation {metric} with deterministic tie-breaks "
            "on MAE, absolute bias, model simplicity, and model name."
        ),
    }
