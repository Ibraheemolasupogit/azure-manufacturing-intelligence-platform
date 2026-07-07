"""Process capability calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.quality.config import CapabilitySettings

CAPABILITY_GRAIN = [
    "product_id",
    "quality_metric",
    "measurement_unit",
    "plant_id",
    "production_line_id",
]


def calculate_process_capability(
    observations: pd.DataFrame, settings: CapabilitySettings
) -> pd.DataFrame:
    """Calculate Cp/Cpk only for comparable groups with enough observations."""
    rows: list[dict[str, Any]] = []
    for keys, group in observations.groupby(CAPABILITY_GRAIN, sort=True):
        key_values = dict(zip(CAPABILITY_GRAIN, keys, strict=True))
        limits_stable = (
            group["lower_specification_limit"].nunique() == 1
            and group["upper_specification_limit"].nunique() == 1
        )
        count = len(group)
        mean = float(group["measured_value"].mean()) if count else 0.0
        std = float(group["measured_value"].std(ddof=0)) if count else 0.0
        lower = float(group["lower_specification_limit"].iloc[0])
        upper = float(group["upper_specification_limit"].iloc[0])
        available = settings.enabled and limits_stable and count >= settings.minimum_observations
        cp = None
        cpk = None
        status = "calculated"
        if not available:
            status = (
                "insufficient_observations" if limits_stable else "unstable_specification_limits"
            )
        elif std == 0:
            status = "zero_standard_deviation"
        else:
            if settings.calculate_cp:
                cp = (upper - lower) / (6.0 * std)
            if settings.calculate_cpk:
                cpk = min((upper - mean) / (3.0 * std), (mean - lower) / (3.0 * std))
        rows.append(
            {
                **key_values,
                "observation_count": count,
                "lower_specification_limit": lower,
                "upper_specification_limit": upper,
                "mean_measured_value": mean,
                "standard_deviation": std,
                "cp": cp,
                "cpk": cpk,
                "capability_status": status,
                "capability_interpretation": "diagnostic_only_not_stability_claim",
            }
        )
    return pd.DataFrame(rows).sort_values(CAPABILITY_GRAIN, ignore_index=True)
