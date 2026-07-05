"""Chronological split helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.forecasting.config import ForecastingConfig


@dataclass(frozen=True)
class SplitMetadata:
    """Chronological split date ranges."""

    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    forecast_start: str
    forecast_end: str

    def to_dict(self) -> dict[str, str]:
        """Serialize split metadata."""
        return {
            "train_start": self.train_start,
            "train_end": self.train_end,
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "forecast_start": self.forecast_start,
            "forecast_end": self.forecast_end,
        }


def build_splits(feature_frame: pd.DataFrame, config: ForecastingConfig) -> SplitMetadata:
    """Build global chronological split boundaries."""
    dates = sorted(pd.to_datetime(feature_frame["demand_date"]).dt.date.unique())
    required_days = (
        config.splitting.minimum_training_days
        + config.splitting.validation_days
        + config.splitting.test_days
    )
    if len(dates) < required_days:
        raise DataContractError(
            f"Insufficient history: {len(dates)} days available, {required_days} required"
        )
    test_start_index = len(dates) - config.splitting.test_days
    validation_start_index = test_start_index - config.splitting.validation_days
    train_end = dates[validation_start_index - 1]
    validation_start = dates[validation_start_index]
    validation_end = dates[test_start_index - 1]
    test_start = dates[test_start_index]
    test_end = dates[-1]
    forecast_start = pd.Timestamp(test_end) + pd.Timedelta(days=1)
    forecast_end = forecast_start + pd.Timedelta(days=config.forecasting.forecast_horizon_days - 1)
    return SplitMetadata(
        train_start=str(dates[0]),
        train_end=str(train_end),
        validation_start=str(validation_start),
        validation_end=str(validation_end),
        test_start=str(test_start),
        test_end=str(test_end),
        forecast_start=str(forecast_start.date()),
        forecast_end=str(forecast_end.date()),
    )


def slice_split(frame: pd.DataFrame, split: SplitMetadata, name: str) -> pd.DataFrame:
    """Return one chronological split."""
    dates = pd.to_datetime(frame["demand_date"]).dt.date
    if name == "train":
        mask = dates <= pd.to_datetime(split.train_end).date()
    elif name == "validation":
        mask = (dates >= pd.to_datetime(split.validation_start).date()) & (
            dates <= pd.to_datetime(split.validation_end).date()
        )
    elif name == "test":
        mask = (dates >= pd.to_datetime(split.test_start).date()) & (
            dates <= pd.to_datetime(split.test_end).date()
        )
    else:
        raise ValueError(f"Unknown split: {name}")
    return frame.loc[mask].copy()
