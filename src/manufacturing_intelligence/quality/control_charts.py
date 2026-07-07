"""Control chart and SPC rule calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.quality.config import SpcSettings

CONTROL_GRAIN = ["machine_id", "quality_metric", "measurement_unit"]
VALID_RULES = {"SPC_RULE_1", "SPC_RULE_2", "SPC_RULE_3", "SPC_RULE_4"}


def calculate_control_chart_points(
    observations: pd.DataFrame, settings: SpcSettings
) -> pd.DataFrame:
    """Calculate leakage-safe expanding historical baselines."""
    rows: list[dict[str, Any]] = []
    ordered = observations.sort_values([*CONTROL_GRAIN, "inspection_timestamp", "inspection_id"])
    for keys, group in ordered.groupby(CONTROL_GRAIN, sort=True):
        key_values = dict(zip(CONTROL_GRAIN, keys, strict=True))
        history: list[float] = []
        for record in group.to_dict("records"):
            count = len(history)
            center = None
            std = None
            ucl = None
            lcl = None
            deviation = None
            outside = False
            status = "insufficient_history"
            value = float(record["measured_value"])
            if settings.enabled and count >= settings.baseline_minimum_observations:
                series = pd.Series(history, dtype="float64")
                center = float(series.mean())
                std = float(series.std(ddof=0))
                deviation = value - center
                if std > 0:
                    ucl = center + settings.control_limit_sigma * std
                    lcl = center - settings.control_limit_sigma * std
                    outside = value > ucl or value < lcl
                    status = "calculated"
                else:
                    status = "zero_standard_deviation"
            rows.append(
                {
                    "inspection_id": record["inspection_id"],
                    "inspection_timestamp": record["inspection_timestamp"],
                    **key_values,
                    "baseline_observation_count": count,
                    "center_line": center,
                    "process_standard_deviation": std,
                    "upper_control_limit": ucl,
                    "lower_control_limit": lcl,
                    "point_deviation_from_center": deviation,
                    "outside_control_limit_flag": outside,
                    "baseline_method": "expanding_prior_observations",
                    "control_chart_status": status,
                }
            )
            history.append(value)
    return pd.DataFrame(rows).sort_values(
        ["inspection_timestamp", "inspection_id"], ignore_index=True
    )


def evaluate_spc_rules(
    observations: pd.DataFrame,
    control_points: pd.DataFrame,
    settings: SpcSettings,
) -> pd.DataFrame:
    """Evaluate deterministic SPC rules chronologically."""
    merged = observations.merge(
        control_points[
            [
                "inspection_id",
                "baseline_observation_count",
                "center_line",
                "process_standard_deviation",
                "outside_control_limit_flag",
                "control_chart_status",
            ]
        ],
        on="inspection_id",
        how="left",
    ).sort_values([*CONTROL_GRAIN, "inspection_timestamp", "inspection_id"])
    rows: list[dict[str, Any]] = []
    for keys, group in merged.groupby(CONTROL_GRAIN, sort=True):
        key_values = dict(zip(CONTROL_GRAIN, keys, strict=True))
        records = group.to_dict("records")
        for index, record in enumerate(records):
            rules: list[str] = []
            evidence: list[str] = []
            std = float(record["process_standard_deviation"] or 0.0)
            center = record["center_line"]
            if (
                settings.enabled
                and record["control_chart_status"] == "calculated"
                and std > 0
                and center is not None
            ):
                if settings.enable_rule_1 and bool(record["outside_control_limit_flag"]):
                    rules.append("SPC_RULE_1")
                    evidence.append(str(record["inspection_id"]))
                window3 = records[max(0, index - 2) : index + 1]
                if settings.enable_rule_2 and _same_side_count(window3, center, 2.0 * std) >= 2:
                    rules.append("SPC_RULE_2")
                    evidence.append(",".join(str(item["inspection_id"]) for item in window3))
                window5 = records[max(0, index - 4) : index + 1]
                if settings.enable_rule_3 and _same_side_count(window5, center, 1.0 * std) >= 4:
                    rules.append("SPC_RULE_3")
                    evidence.append(",".join(str(item["inspection_id"]) for item in window5))
                window8 = records[max(0, index - 7) : index + 1]
                if settings.enable_rule_4 and len(window8) == 8 and _all_same_side(window8, center):
                    rules.append("SPC_RULE_4")
                    evidence.append(",".join(str(item["inspection_id"]) for item in window8))
            rows.append(
                {
                    "inspection_id": record["inspection_id"],
                    "inspection_timestamp": record["inspection_timestamp"],
                    **key_values,
                    "spc_rule_codes": ";".join(rules),
                    "spc_signal_flag": bool(rules),
                    "spc_triggering_window": "|".join(evidence),
                    "spc_evaluation_status": record["control_chart_status"],
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["inspection_timestamp", "inspection_id"], ignore_index=True
    )


def _same_side_count(window: list[dict[str, Any]], center: float, distance: float) -> int:
    high = sum(float(item["measured_value"]) > center + distance for item in window)
    low = sum(float(item["measured_value"]) < center - distance for item in window)
    return max(high, low)


def _all_same_side(window: list[dict[str, Any]], center: float) -> bool:
    values = [float(item["measured_value"]) for item in window]
    return all(value > center for value in values) or all(value < center for value in values)
