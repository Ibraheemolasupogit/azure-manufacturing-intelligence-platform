"""Deterministic forecasting models."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
from sklearn.compose import ColumnTransformer  # type: ignore[import-untyped]
from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LinearRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import OneHotEncoder  # type: ignore[import-untyped]

from manufacturing_intelligence.forecasting.config import ForecastingConfig
from manufacturing_intelligence.forecasting.features import model_feature_columns


def seasonal_naive_predict(
    history: pd.DataFrame,
    target: pd.DataFrame,
    seasonal_lag: int,
) -> pd.Series:
    """Predict demand from same-series seasonal lag."""
    history_map = {
        (row.series_id, pd.to_datetime(row.demand_date).date()): float(row.demand_quantity)
        for row in history.itertuples(index=False)
    }
    predictions = []
    for row in target.itertuples(index=False):
        forecast_date = pd.to_datetime(row.demand_date).date()
        lag_date = forecast_date - pd.Timedelta(days=seasonal_lag)
        predictions.append(max(0.0, history_map.get((row.series_id, lag_date), 0.0)))
    return pd.Series(predictions, index=target.index, dtype=float)


def moving_average_predict(history: pd.DataFrame, target: pd.DataFrame, window: int) -> pd.Series:
    """Predict with trailing same-series mean."""
    predictions = []
    for row in target.itertuples(index=False):
        series_history = history[
            (history["series_id"] == row.series_id)
            & (pd.to_datetime(history["demand_date"]) < pd.to_datetime(row.demand_date))
        ].tail(window)
        prediction = (
            0.0 if series_history.empty else float(series_history["demand_quantity"].mean())
        )
        predictions.append(max(0.0, prediction))
    return pd.Series(predictions, index=target.index, dtype=float)


def fit_ml_model(
    model_name: str,
    train: pd.DataFrame,
    config: ForecastingConfig,
) -> Pipeline:
    """Fit a deterministic sklearn model."""
    columns = model_feature_columns(config)
    categorical = [column for column in ("product_id", "distribution_region") if column in columns]
    numeric = [column for column in columns if column not in categorical]
    transformer = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="constant", fill_value=0.0), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ]
    )
    estimator = (
        LinearRegression()
        if model_name == "linear_regression"
        else RandomForestRegressor(
            n_estimators=40,
            max_depth=6,
            min_samples_leaf=2,
            random_state=config.forecasting.random_seed,
            n_jobs=1,
        )
    )
    pipeline = Pipeline([("features", transformer), ("model", estimator)])
    pipeline.fit(train[columns], train["demand_quantity"])
    return pipeline


def predict_ml(model: Pipeline, target: pd.DataFrame, config: ForecastingConfig) -> pd.Series:
    """Predict and clip demand to non-negative values."""
    columns = model_feature_columns(config)
    raw = model.predict(target[columns])
    return pd.Series([max(0.0, float(value)) for value in raw], index=target.index, dtype=float)
