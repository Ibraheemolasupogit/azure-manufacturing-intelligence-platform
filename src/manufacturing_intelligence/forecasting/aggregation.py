"""Demand aggregation and calendar completion."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.forecasting.config import ForecastingConfig


def build_daily_demand(frame: pd.DataFrame, config: ForecastingConfig) -> pd.DataFrame:
    """Aggregate sales orders into complete daily demand series."""
    settings = config.forecasting
    working = frame.copy()
    working["demand_date"] = pd.to_datetime(working[settings.date_field]).dt.date
    grouped = (
        working.groupby([*settings.series_keys, "demand_date"], as_index=False)
        .agg(
            demand_quantity=(settings.target_field, "sum"),
            source_order_count=(settings.target_field, "size"),
        )
        .sort_values([*settings.series_keys, "demand_date"])
    )
    min_date = grouped["demand_date"].min()
    max_date = grouped["demand_date"].max()
    series_frames: list[pd.DataFrame] = []
    for keys, series_group in grouped.groupby(list(settings.series_keys), dropna=False):
        key_values = keys if isinstance(keys, tuple) else (keys,)
        calendar = pd.DataFrame({"demand_date": pd.date_range(min_date, max_date, freq="D").date})
        for key, value in zip(settings.series_keys, key_values, strict=True):
            calendar[key] = value
        merged = calendar.merge(series_group, on=[*settings.series_keys, "demand_date"], how="left")
        merged["calendar_filled_flag"] = merged["demand_quantity"].isna()
        merged["demand_quantity"] = merged["demand_quantity"].fillna(0).astype(float)
        merged["source_order_count"] = merged["source_order_count"].fillna(0).astype(int)
        series_frames.append(merged)
    result = pd.concat(series_frames, ignore_index=True)
    result["series_id"] = result[list(settings.series_keys)].astype(str).agg("|".join, axis=1)
    result = result[
        [
            "series_id",
            *settings.series_keys,
            "demand_date",
            "demand_quantity",
            "source_order_count",
            "calendar_filled_flag",
        ]
    ].sort_values(["series_id", "demand_date"], ignore_index=True)
    return result
