"""Leakage-safe feature engineering."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.forecasting.config import ForecastingConfig


def build_feature_dataset(daily: pd.DataFrame, config: ForecastingConfig) -> pd.DataFrame:
    """Build features using only earlier demand values."""
    features = daily.copy()
    features["demand_date"] = pd.to_datetime(features["demand_date"])
    features = features.sort_values(["series_id", "demand_date"], ignore_index=True)
    by_series = features.groupby("series_id")["demand_quantity"]
    for lag in config.features.lag_days:
        features[f"lag_{lag}_demand"] = by_series.shift(lag)
    shifted = by_series.shift(1)
    for window in config.features.rolling_windows:
        features[f"rolling_mean_{window}"] = (
            shifted.groupby(features["series_id"])
            .rolling(window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        features[f"rolling_std_{window}"] = (
            shifted.groupby(features["series_id"])
            .rolling(window, min_periods=2)
            .std()
            .reset_index(level=0, drop=True)
            .fillna(0)
        )
    if config.features.include_day_of_week:
        features["day_of_week"] = features["demand_date"].dt.dayofweek
    if config.features.include_weekend_flag:
        features["weekend_flag"] = features["demand_date"].dt.dayofweek.isin([5, 6]).astype(int)
    if config.features.include_month:
        features["month"] = features["demand_date"].dt.month
    if config.features.include_trend_index:
        features["trend_index"] = features.groupby("series_id").cumcount()
    return features.sort_values(["series_id", "demand_date"], ignore_index=True)


def model_feature_columns(config: ForecastingConfig) -> list[str]:
    """Return model feature columns."""
    columns = [f"lag_{lag}_demand" for lag in config.features.lag_days]
    for window in config.features.rolling_windows:
        columns.extend([f"rolling_mean_{window}", f"rolling_std_{window}"])
    if config.features.include_day_of_week:
        columns.append("day_of_week")
    if config.features.include_weekend_flag:
        columns.append("weekend_flag")
    if config.features.include_month:
        columns.append("month")
    if config.features.include_trend_index:
        columns.append("trend_index")
    if config.features.include_product:
        columns.append("product_id")
    if config.features.include_region:
        columns.append("distribution_region")
    return columns
