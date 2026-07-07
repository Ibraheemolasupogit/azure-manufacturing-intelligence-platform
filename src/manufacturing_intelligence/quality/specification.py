"""Specification compliance calculations."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.quality.config import SpecificationSettings


def evaluate_specification(quality: pd.DataFrame, settings: SpecificationSettings) -> pd.DataFrame:
    """Calculate record-level specification compliance."""
    frame = quality.copy()
    lower = frame["lower_specification_limit"].astype(float)
    upper = frame["upper_specification_limit"].astype(float)
    value = frame["measured_value"].astype(float)
    span = (upper - lower).clip(lower=0.000001)
    center = lower + span / 2.0
    distance_lower = value - lower
    distance_upper = upper - value
    nearest = pd.concat([distance_lower.abs(), distance_upper.abs()], axis=1).min(axis=1)
    below = value < lower
    above = value > upper
    within = ~(below | above)
    near_limit = within & (nearest <= span * settings.near_limit_margin_fraction)
    warning_limit = within & (nearest <= span * settings.warning_margin_fraction)
    calculated = within.map({True: "pass", False: "fail"})
    direction = pd.Series("", index=frame.index)
    direction[below] = "below_lower_limit"
    direction[above] = "above_upper_limit"
    frame["specification_center"] = center
    frame["specification_range"] = span
    frame["distance_from_lower_limit"] = distance_lower
    frame["distance_from_upper_limit"] = distance_upper
    frame["normalised_distance_to_nearest_limit"] = nearest / span
    frame["within_specification_flag"] = within
    frame["below_lower_limit_flag"] = below
    frame["above_upper_limit_flag"] = above
    frame["near_limit_flag"] = near_limit
    frame["warning_limit_flag"] = warning_limit
    frame["specification_failure_direction"] = direction
    frame["specification_margin_percentage"] = (nearest / span) * 100.0
    frame["source_inspection_result"] = frame["inspection_result"]
    frame["calculated_specification_result"] = calculated
    frame["specification_consistency_flag"] = (
        frame["source_inspection_result"] == frame["calculated_specification_result"]
    )
    frame["defective_unit_rate"] = frame["defective_units"] / frame["sample_size"]
    return frame
