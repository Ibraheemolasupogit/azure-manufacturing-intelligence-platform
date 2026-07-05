"""Configuration loading for demand forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_MODELS = {"seasonal_naive", "moving_average", "linear_regression", "random_forest"}
SUPPORTED_METRICS = {"mae", "rmse", "wape", "smape", "bias", "absolute_bias"}


@dataclass(frozen=True)
class ForecastingSettings:
    """Forecast runtime settings."""

    input_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    lineage_path: Path
    output_directory: Path
    forecast_output_path: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    frequency: str
    target_field: str
    date_field: str
    series_keys: tuple[str, ...]
    forecast_horizon_days: int
    minimum_history_days: int
    prediction_interval_level: float


@dataclass(frozen=True)
class SplitSettings:
    """Chronological split settings."""

    validation_days: int
    test_days: int
    minimum_training_days: int
    rolling_backtest_windows: int
    step_days: int


@dataclass(frozen=True)
class FeatureSettings:
    """Leakage-safe feature settings."""

    lag_days: tuple[int, ...]
    rolling_windows: tuple[int, ...]
    include_day_of_week: bool
    include_weekend_flag: bool
    include_month: bool
    include_trend_index: bool
    include_region: bool
    include_product: bool


@dataclass(frozen=True)
class ModelSettings:
    """Model settings."""

    enabled: tuple[str, ...]
    moving_average_window: int
    seasonal_lag_days: int
    selection_metric: str


@dataclass(frozen=True)
class ReportingSettings:
    """Forecast reporting settings."""

    write_forecast_report: bool
    write_model_comparison: bool
    write_backtest_predictions: bool
    maximum_series_examples: int


@dataclass(frozen=True)
class ForecastingConfig:
    """Complete forecasting configuration."""

    config_path: Path
    forecasting: ForecastingSettings
    splitting: SplitSettings
    features: FeatureSettings
    models: ModelSettings
    reporting: ReportingSettings


def load_forecasting_config(config_path: Path | None = None) -> ForecastingConfig:
    """Load and validate forecasting YAML configuration."""
    path = config_path or project_root() / "configs" / "forecasting.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Forecasting config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Forecasting config must contain a mapping")

    forecasting = _section(payload, "forecasting")
    splitting = _section(payload, "splitting")
    features = _section(payload, "features")
    models = _section(payload, "models")
    reporting = _section(payload, "reporting")

    frequency = _required_str(forecasting, "frequency")
    if frequency != "daily":
        raise ConfigurationError("forecasting.frequency must be daily")
    horizon = _positive_int(forecasting, "forecast_horizon_days")
    minimum_history = _positive_int(forecasting, "minimum_history_days")
    interval_level = _number(forecasting, "prediction_interval_level")
    if not 0 < interval_level < 1:
        raise ConfigurationError("forecasting.prediction_interval_level must be between 0 and 1")
    series_keys = tuple(_str_list(forecasting, "series_keys"))
    if not series_keys:
        raise ConfigurationError("forecasting.series_keys must not be empty")

    validation_days = _positive_int(splitting, "validation_days")
    test_days = _positive_int(splitting, "test_days")
    minimum_training_days = _positive_int(splitting, "minimum_training_days")
    rolling_windows = _positive_int(splitting, "rolling_backtest_windows")
    step_days = _positive_int(splitting, "step_days")

    lag_days = _positive_unique_ints(features, "lag_days")
    rolling_feature_windows = _positive_unique_ints(features, "rolling_windows")
    if minimum_history < max(lag_days):
        raise ConfigurationError("forecasting.minimum_history_days must cover the largest lag")
    if minimum_training_days < max(lag_days):
        raise ConfigurationError("splitting.minimum_training_days must cover the largest lag")

    enabled = tuple(_str_list(models, "enabled"))
    unsupported = sorted(set(enabled) - SUPPORTED_MODELS)
    if unsupported:
        raise ConfigurationError(f"models.enabled contains unsupported models: {unsupported}")
    selection_metric = _required_str(models, "selection_metric")
    if selection_metric not in SUPPORTED_METRICS:
        raise ConfigurationError(f"models.selection_metric is unsupported: {selection_metric}")

    input_path = resolve_project_path(_required_str(forecasting, "input_path"))
    output_directory = resolve_project_path(_required_str(forecasting, "output_directory"))
    forecast_output_path = resolve_project_path(_required_str(forecasting, "forecast_output_path"))
    if input_path == output_directory or input_path in output_directory.parents:
        raise ConfigurationError("forecasting.output_directory must not overwrite governed input")
    if forecast_output_path == input_path:
        raise ConfigurationError("forecasting.forecast_output_path must not overwrite input")

    return ForecastingConfig(
        config_path=path.resolve(),
        forecasting=ForecastingSettings(
            input_path=input_path,
            ingestion_manifest_path=resolve_project_path(
                _required_str(forecasting, "ingestion_manifest_path")
            ),
            validation_summary_path=resolve_project_path(
                _required_str(forecasting, "validation_summary_path")
            ),
            data_quality_report_path=resolve_project_path(
                _required_str(forecasting, "data_quality_report_path")
            ),
            lineage_path=resolve_project_path(_required_str(forecasting, "lineage_path")),
            output_directory=output_directory,
            forecast_output_path=forecast_output_path,
            report_directory=resolve_project_path(_required_str(forecasting, "report_directory")),
            overwrite=_required_bool(forecasting, "overwrite"),
            random_seed=_positive_int(forecasting, "random_seed"),
            frequency=frequency,
            target_field=_required_str(forecasting, "target_field"),
            date_field=_required_str(forecasting, "date_field"),
            series_keys=series_keys,
            forecast_horizon_days=horizon,
            minimum_history_days=minimum_history,
            prediction_interval_level=interval_level,
        ),
        splitting=SplitSettings(
            validation_days=validation_days,
            test_days=test_days,
            minimum_training_days=minimum_training_days,
            rolling_backtest_windows=rolling_windows,
            step_days=step_days,
        ),
        features=FeatureSettings(
            lag_days=tuple(lag_days),
            rolling_windows=tuple(rolling_feature_windows),
            include_day_of_week=_required_bool(features, "include_day_of_week"),
            include_weekend_flag=_required_bool(features, "include_weekend_flag"),
            include_month=_required_bool(features, "include_month"),
            include_trend_index=_required_bool(features, "include_trend_index"),
            include_region=_required_bool(features, "include_region"),
            include_product=_required_bool(features, "include_product"),
        ),
        models=ModelSettings(
            enabled=enabled,
            moving_average_window=_positive_int(models, "moving_average_window"),
            seasonal_lag_days=_positive_int(models, "seasonal_lag_days"),
            selection_metric=selection_metric,
        ),
        reporting=ReportingSettings(
            write_forecast_report=_required_bool(reporting, "write_forecast_report"),
            write_model_comparison=_required_bool(reporting, "write_model_comparison"),
            write_backtest_predictions=_required_bool(reporting, "write_backtest_predictions"),
            maximum_series_examples=_positive_int(reporting, "maximum_series_examples"),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Forecasting config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Forecasting config string missing or invalid: {key}")
    if value.lower() in {"deploy", "deployment", "live"}:
        raise ConfigurationError("Live deployment mode is not accepted")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Forecasting config boolean missing or invalid: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Forecasting config positive integer missing or invalid: {key}")
    return value


def _number(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, int | float):
        raise ConfigurationError(f"Forecasting config number missing or invalid: {key}")
    return float(value)


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Forecasting config string list missing or invalid: {key}")
    return value


def _positive_unique_ints(section: dict[str, Any], key: str) -> list[int]:
    value = section.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, int) for item in value):
        raise ConfigurationError(f"Forecasting config integer list missing or invalid: {key}")
    unique = sorted(set(value))
    if len(unique) != len(value) or any(item <= 0 for item in unique):
        raise ConfigurationError(f"Forecasting config {key} must contain positive unique values")
    return unique
