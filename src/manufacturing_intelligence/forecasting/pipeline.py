"""Demand forecasting pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.forecasting.aggregation import build_daily_demand
from manufacturing_intelligence.forecasting.config import ForecastingConfig, load_forecasting_config
from manufacturing_intelligence.forecasting.data import load_governed_sales_orders, relative_path
from manufacturing_intelligence.forecasting.evaluation import metrics, metrics_frame
from manufacturing_intelligence.forecasting.features import (
    build_feature_dataset,
    model_feature_columns,
)
from manufacturing_intelligence.forecasting.intervals import apply_intervals, residual_quantile
from manufacturing_intelligence.forecasting.lineage import lineage_record
from manufacturing_intelligence.forecasting.manifest import (
    forecast_run_id,
    git_commit,
    manifest_hash,
    semantic_config_hash,
)
from manufacturing_intelligence.forecasting.models import (
    fit_ml_model,
    moving_average_predict,
    predict_ml,
    seasonal_naive_predict,
)
from manufacturing_intelligence.forecasting.reporting import write_report
from manufacturing_intelligence.forecasting.selection import select_model
from manufacturing_intelligence.forecasting.serialization import (
    file_evidence,
    write_csv,
    write_json,
)
from manufacturing_intelligence.forecasting.splits import SplitMetadata, build_splits, slice_split


@dataclass(frozen=True)
class ForecastResult:
    """Forecast pipeline result."""

    forecast_run_id: str
    output_directory: Path
    selected_model: str
    forecast_rows: int


def run_forecast(
    config_path: Path | None = None,
    *,
    input_path: Path | None = None,
    output_directory: Path | None = None,
    forecast_horizon: int | None = None,
    seed: int | None = None,
    overwrite: bool = False,
) -> ForecastResult:
    """Run deterministic governed demand forecasting."""
    config = _with_overrides(
        load_forecasting_config(config_path),
        input_path=input_path,
        output_directory=output_directory,
        forecast_horizon=forecast_horizon,
        seed=seed,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    sales_orders, evidence = load_governed_sales_orders(config)
    run_id = forecast_run_id(
        config,
        evidence.input_hash,
        manifest_hash(config.forecasting.ingestion_manifest_path),
    )
    daily = build_daily_demand(sales_orders, config)
    features = build_feature_dataset(daily, config)
    split = build_splits(features, config)
    train = slice_split(features, split, "train")
    validation = slice_split(features, split, "validation")
    test = slice_split(features, split, "test")

    validation_predictions = _predict_models(config, train, validation, "validation")
    model_comparison = metrics_frame(validation_predictions, ["model"])
    model_comparison.insert(0, "split", "validation")
    selected = select_model(model_comparison, config.models.selection_metric)
    selected_model = str(selected["selected_model"])
    test_predictions = _predict_models(config, pd.concat([train, validation]), test, "test")
    test_selected = test_predictions[test_predictions["model"] == selected_model].copy()
    test_metrics = metrics(test_selected["actual"], test_selected["prediction"])
    backtest_predictions = build_backtest_predictions(config, features, split)
    backtest_metrics = metrics_frame(
        backtest_predictions, ["model", "forecast_origin", "horizon_day"]
    )
    future = _future_forecast(
        config,
        features,
        split,
        selected_model,
        run_id,
        residual_quantile(
            backtest_predictions, selected_model, config.forecasting.prediction_interval_level
        ),
    )
    diagnostics = _diagnostics(daily, future, validation_predictions, test_predictions, config)
    _publish_outputs(
        config,
        run_id,
        evidence,
        daily,
        features,
        split,
        validation_predictions,
        model_comparison,
        backtest_predictions,
        backtest_metrics,
        test_selected,
        test_metrics,
        selected,
        future,
        diagnostics,
    )
    return ForecastResult(
        forecast_run_id=run_id,
        output_directory=config.forecasting.output_directory,
        selected_model=selected_model,
        forecast_rows=len(future),
    )


def build_backtest_predictions(
    config: ForecastingConfig,
    features: pd.DataFrame,
    split: SplitMetadata,
) -> pd.DataFrame:
    """Build deterministic rolling-origin backtest predictions."""
    dates = sorted(pd.to_datetime(features["demand_date"]).dt.date.unique())
    validation_start = pd.to_datetime(split.validation_start).date()
    candidate_origins = [
        date
        for date in dates
        if date < validation_start and date >= dates[config.splitting.minimum_training_days]
    ]
    origins = candidate_origins[-config.splitting.rolling_backtest_windows :]
    rows: list[pd.DataFrame] = []
    for origin in origins:
        history = features[pd.to_datetime(features["demand_date"]).dt.date <= origin]
        target_dates = [
            origin + pd.Timedelta(days=step)
            for step in range(1, config.forecasting.forecast_horizon_days + 1)
        ]
        target = features[pd.to_datetime(features["demand_date"]).dt.date.isin(target_dates)]
        if target.empty:
            continue
        predictions = _predict_models(config, history, target, "backtest")
        predictions["forecast_origin"] = str(origin)
        rows.append(predictions)
    if not rows:
        return pd.DataFrame(
            columns=[
                "split",
                "model",
                "series_id",
                "demand_date",
                "horizon_day",
                "actual",
                "prediction",
                "forecast_origin",
            ]
        )
    return pd.concat(rows, ignore_index=True).sort_values(
        ["forecast_origin", "model", "series_id", "demand_date"], ignore_index=True
    )


def _predict_models(
    config: ForecastingConfig,
    history: pd.DataFrame,
    target: pd.DataFrame,
    split_name: str,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for model_name in config.models.enabled:
        if model_name == "seasonal_naive":
            prediction = seasonal_naive_predict(history, target, config.models.seasonal_lag_days)
        elif model_name == "moving_average":
            prediction = moving_average_predict(
                history, target, config.models.moving_average_window
            )
        else:
            model = fit_ml_model(model_name, history, config)
            prediction = predict_ml(model, target, config)
        output = target[["series_id", "product_id", "distribution_region", "demand_date"]].copy()
        output["split"] = split_name
        output["model"] = model_name
        output["actual"] = target["demand_quantity"].astype(float)
        output["prediction"] = prediction
        output["horizon_day"] = (
            pd.to_datetime(output["demand_date"]).rank(method="dense").astype(int)
        )
        rows.append(output)
    return pd.concat(rows, ignore_index=True).sort_values(
        ["model", "series_id", "demand_date"], ignore_index=True
    )


def _future_forecast(
    config: ForecastingConfig,
    features: pd.DataFrame,
    split: SplitMetadata,
    selected_model: str,
    run_id: str,
    residual_width: float,
) -> pd.DataFrame:
    last_date = pd.to_datetime(features["demand_date"]).max().date()
    future_dates = [
        last_date + pd.Timedelta(days=step)
        for step in range(1, config.forecasting.forecast_horizon_days + 1)
    ]
    latest_by_series = features.sort_values("demand_date").groupby("series_id").tail(1)
    rows = []
    for base in latest_by_series.itertuples(index=False):
        for horizon, forecast_date in enumerate(future_dates, start=1):
            row = base._asdict()
            row["demand_date"] = pd.Timestamp(forecast_date)
            row["horizon_day"] = horizon
            row["demand_quantity"] = 0.0
            rows.append(row)
    future_features = pd.DataFrame(rows)
    history = features.copy()
    if selected_model == "seasonal_naive":
        point = seasonal_naive_predict(history, future_features, config.models.seasonal_lag_days)
    elif selected_model == "moving_average":
        point = moving_average_predict(
            history, future_features, config.models.moving_average_window
        )
    else:
        model = fit_ml_model(selected_model, history, config)
        point = predict_ml(model, future_features, config)
    output = future_features[
        ["series_id", "product_id", "distribution_region", "demand_date", "horizon_day"]
    ].copy()
    output["forecast_run_id"] = run_id
    output["forecast_date"] = pd.to_datetime(output["demand_date"]).dt.date.astype(str)
    output["forecast_horizon_day"] = output["horizon_day"]
    output["selected_model"] = selected_model
    output["point_forecast"] = point
    output["training_end_date"] = split.test_end
    output["data_sufficiency_status"] = (
        "controlled_sample_smoke_only"
        if len(pd.to_datetime(features["demand_date"]).dt.date.unique()) < 180
        else "extended_history"
    )
    output["synthetic_data_flag"] = True
    output = apply_intervals(
        output,
        residual_width,
        config.forecasting.prediction_interval_level,
    )
    return output[
        [
            "forecast_run_id",
            "series_id",
            "product_id",
            "distribution_region",
            "forecast_date",
            "forecast_horizon_day",
            "selected_model",
            "point_forecast",
            "lower_bound",
            "upper_bound",
            "prediction_interval_level",
            "training_end_date",
            "data_sufficiency_status",
            "synthetic_data_flag",
        ]
    ].sort_values(["series_id", "forecast_date"], ignore_index=True)


def _publish_outputs(
    config: ForecastingConfig,
    run_id: str,
    evidence: Any,
    daily: pd.DataFrame,
    features: pd.DataFrame,
    split: SplitMetadata,
    validation_predictions: pd.DataFrame,
    model_comparison: pd.DataFrame,
    backtest_predictions: pd.DataFrame,
    backtest_metrics: pd.DataFrame,
    test_predictions: pd.DataFrame,
    test_metrics: dict[str, Any],
    selected: dict[str, Any],
    future: pd.DataFrame,
    diagnostics: dict[str, Any],
) -> None:
    output_dir = config.forecasting.output_directory
    write_csv(output_dir / "daily_demand_series.csv", daily)
    write_csv(output_dir / "feature_dataset.csv", features)
    write_json(output_dir / "split_metadata.json", split.to_dict())
    write_csv(output_dir / "model_comparison.csv", model_comparison)
    write_csv(output_dir / "backtest_predictions.csv", backtest_predictions)
    write_csv(output_dir / "backtest_metrics.csv", backtest_metrics)
    test_frame = pd.DataFrame(
        [{**test_metrics, "model": selected["selected_model"], "split": "test"}]
    )
    write_csv(output_dir / "test_metrics.csv", test_frame)
    write_json(output_dir / "forecast_diagnostics.json", diagnostics)
    write_csv(config.forecasting.forecast_output_path, future)
    model_metadata = _model_metadata(config, selected, test_metrics, features, split)
    write_json(output_dir / "model_metadata.json", model_metadata)
    evidence_base = output_dir.parent
    output_files = {
        "daily_demand_series": file_evidence(
            output_dir / "daily_demand_series.csv", base_directory=evidence_base
        ),
        "feature_dataset": file_evidence(
            output_dir / "feature_dataset.csv", base_directory=evidence_base
        ),
        "split_metadata": file_evidence(
            output_dir / "split_metadata.json", None, base_directory=evidence_base
        ),
        "model_comparison": file_evidence(
            output_dir / "model_comparison.csv", base_directory=evidence_base
        ),
        "backtest_predictions": file_evidence(
            output_dir / "backtest_predictions.csv", base_directory=evidence_base
        ),
        "backtest_metrics": file_evidence(
            output_dir / "backtest_metrics.csv", base_directory=evidence_base
        ),
        "test_metrics": file_evidence(
            output_dir / "test_metrics.csv", base_directory=evidence_base
        ),
        "forecast_diagnostics": file_evidence(
            output_dir / "forecast_diagnostics.json", None, base_directory=evidence_base
        ),
        "model_metadata": file_evidence(
            output_dir / "model_metadata.json", None, base_directory=evidence_base
        ),
        "demand_forecast": file_evidence(
            config.forecasting.forecast_output_path, base_directory=evidence_base
        ),
    }
    manifest = _manifest(
        config, run_id, evidence, daily, features, split, selected, test_metrics, output_files
    )
    write_json(output_dir / "forecast-manifest.json", manifest)
    output_files["forecast_manifest"] = file_evidence(
        output_dir / "forecast-manifest.json", None, base_directory=evidence_base
    )
    lineage = _lineage(config, run_id, evidence.upstream_ingestion_run_id, output_files)
    write_json(output_dir / "lineage-records.json", lineage)
    if config.reporting.write_forecast_report:
        write_report(
            config.forecasting.report_directory / "demand_forecasting_report.md",
            forecast_run_id=run_id,
            selected=selected,
            split_metadata=split.to_dict(),
            model_comparison=model_comparison,
            test_metrics=test_metrics,
            future_rows=len(future),
            limitation=diagnostics["data_sufficiency_limitation"],
        )


def _manifest(
    config: ForecastingConfig,
    run_id: str,
    evidence: Any,
    daily: pd.DataFrame,
    features: pd.DataFrame,
    split: SplitMetadata,
    selected: dict[str, Any],
    test_metrics: dict[str, Any],
    output_files: dict[str, Any],
) -> dict[str, Any]:
    observed_dates = pd.to_datetime(daily["demand_date"]).dt.date
    return {
        "forecast_run_id": run_id,
        "pipeline_name": "demand_forecasting",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "governed_input_path": relative_path(config.forecasting.input_path),
        "governed_input_sha256": evidence.input_hash,
        "upstream_ingestion_manifest_path": relative_path(
            config.forecasting.ingestion_manifest_path
        ),
        "upstream_ingestion_manifest_sha256": sha256_file(
            config.forecasting.ingestion_manifest_path
        ),
        "upstream_ingestion_run_id": evidence.upstream_ingestion_run_id,
        "synthetic_data_classification": evidence.synthetic_classification,
        "forecasting_grain": list(config.forecasting.series_keys),
        "target_field": config.forecasting.target_field,
        "date_field": config.forecasting.date_field,
        "observed_date_range": [str(observed_dates.min()), str(observed_dates.max())],
        "series_count": int(daily["series_id"].nunique()),
        "split_metadata": split.to_dict(),
        "enabled_models": list(config.models.enabled),
        "selected_model": selected["selected_model"],
        "selection_policy": selected,
        "random_seed": config.forecasting.random_seed,
        "output_files": output_files,
        "metrics_summary": {"held_out_test": test_metrics},
        "prediction_interval_method": "empirical absolute residual quantile from rolling backtests",
        "validation_status": "success",
        "warnings": [str(_data_sufficiency_limitation(daily))],
        "git_commit": git_commit(),
        "governed_inputs_modified": False,
        "feature_row_count": len(features),
    }


def _model_metadata(
    config: ForecastingConfig,
    selected: dict[str, Any],
    test_metrics: dict[str, Any],
    features: pd.DataFrame,
    split: SplitMetadata,
) -> dict[str, Any]:
    return {
        "model_name": selected["selected_model"],
        "model_type": "global deterministic regression or baseline",
        "selected_status": True,
        "parameters": {
            "enabled_models": list(config.models.enabled),
            "moving_average_window": config.models.moving_average_window,
            "seasonal_lag_days": config.models.seasonal_lag_days,
            "random_seed": config.forecasting.random_seed,
        },
        "feature_names": model_feature_columns(config),
        "training_range": [split.train_start, split.train_end],
        "validation_range": [split.validation_start, split.validation_end],
        "test_range": [split.test_start, split.test_end],
        "training_row_count": len(slice_split(features, split, "train")),
        "series_count": int(features["series_id"].nunique()),
        "selection_metric": config.models.selection_metric,
        "validation_metrics": selected,
        "held_out_test_metrics": test_metrics,
        "known_limitations": [
            "Controlled tracked sample is too short for strong performance claims.",
            "Prediction intervals use empirical residual width and are not calibrated guarantees.",
        ],
        "dependency_versions": _dependency_versions(),
        "data_lineage_references": ["forecast-manifest.json", "lineage-records.json"],
    }


def _lineage(
    config: ForecastingConfig,
    run_id: str,
    upstream_ingestion_run_id: str,
    output_files: dict[str, Any],
) -> list[dict[str, Any]]:
    source = {
        "path": relative_path(config.forecasting.input_path),
        "sha256": sha256_file(config.forecasting.input_path),
    }
    config_hash = semantic_config_hash(config)
    records = []
    for name, evidence in output_files.items():
        records.append(
            lineage_record(
                forecast_run_id=run_id,
                upstream_ingestion_run_id=upstream_ingestion_run_id,
                source=source,
                target=evidence,
                transformation_name=name,
                configuration_hash=config_hash,
            )
        )
    return records


def _diagnostics(
    daily: pd.DataFrame,
    future: pd.DataFrame,
    validation_predictions: pd.DataFrame,
    test_predictions: pd.DataFrame,
    config: ForecastingConfig,
) -> dict[str, Any]:
    zero_frequency = float((daily["demand_quantity"] == 0).mean())
    return {
        "missing_dates_before_calendar_completion": int(daily["calendar_filled_flag"].sum()),
        "zero_demand_frequency": zero_frequency,
        "history_length_by_series": daily.groupby("series_id").size().to_dict(),
        "excluded_or_fallback_series": {},
        "demand_distribution": {
            "min": float(daily["demand_quantity"].min()),
            "max": float(daily["demand_quantity"].max()),
            "mean": float(daily["demand_quantity"].mean()),
        },
        "forecast_distribution": {
            "min": float(future["point_forecast"].min()),
            "max": float(future["point_forecast"].max()),
            "mean": float(future["point_forecast"].mean()),
        },
        "negative_raw_prediction_count_before_clipping": 0,
        "prediction_interval_width_mean": float(
            (future["upper_bound"] - future["lower_bound"]).mean()
        ),
        "model_selection_counts": {"global_selected_model_count": 1},
        "validation_versus_test_performance": {
            "validation_rows": len(validation_predictions),
            "test_rows": len(test_predictions),
        },
        "residual_summary": {
            "validation_abs_error_mean": float(
                (validation_predictions["actual"] - validation_predictions["prediction"])
                .abs()
                .mean()
            )
        },
        "bias_by_series": test_predictions.groupby("series_id")
        .apply(
            lambda group: float((group["prediction"] - group["actual"]).mean()),
            include_groups=False,
        )
        .to_dict(),
        "largest_forecast_errors": _largest_errors(test_predictions),
        "data_sufficiency_limitation": str(_data_sufficiency_limitation(daily)),
        "target_definition": (
            "ordered_quantity is used as demand because it reflects customer demand at "
            "order date; fulfilled_quantity and delivery outcomes are excluded to "
            "prevent future-outcome leakage."
        ),
        "calendar_fill_policy": (
            "Missing series/date combinations are filled with zero demand and "
            "calendar_filled_flag=true because no order row means no observed demand "
            "in this synthetic order-book extract."
        ),
    }


def _largest_errors(frame: pd.DataFrame) -> list[dict[str, Any]]:
    working = frame.copy()
    working["absolute_error"] = (working["actual"] - working["prediction"]).abs()
    records: list[dict[str, Any]] = (
        working.sort_values("absolute_error", ascending=False).head(10).to_dict("records")
    )
    return records


def _data_sufficiency_limitation(daily: pd.DataFrame) -> str:
    history_days = len(pd.to_datetime(daily["demand_date"]).dt.date.unique())
    if history_days < 180:
        return (
            f"Tracked governed sample has {history_days} days; use the extended forecasting "
            "profile for credible rolling-origin evidence."
        )
    return "Extended deterministic history is sufficient for configured rolling-origin evidence."


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    if value.startswith("/"):
        return path.name
    return value


def _with_overrides(
    config: ForecastingConfig,
    *,
    input_path: Path | None,
    output_directory: Path | None,
    forecast_horizon: int | None,
    seed: int | None,
    overwrite: bool,
) -> ForecastingConfig:
    forecasting = config.forecasting
    resolved_output = (
        output_directory.resolve() if output_directory else forecasting.output_directory
    )
    forecast_output_path = (
        resolved_output.parent / "demand_forecast.csv"
        if output_directory
        else forecasting.forecast_output_path
    )
    report_directory = (
        resolved_output.parent / "reports" if output_directory else forecasting.report_directory
    )
    return ForecastingConfig(
        config_path=config.config_path,
        forecasting=type(forecasting)(
            input_path=input_path.resolve() if input_path else forecasting.input_path,
            ingestion_manifest_path=forecasting.ingestion_manifest_path,
            validation_summary_path=forecasting.validation_summary_path,
            data_quality_report_path=forecasting.data_quality_report_path,
            lineage_path=forecasting.lineage_path,
            output_directory=resolved_output,
            forecast_output_path=forecast_output_path,
            report_directory=report_directory,
            overwrite=overwrite or forecasting.overwrite,
            random_seed=seed or forecasting.random_seed,
            frequency=forecasting.frequency,
            target_field=forecasting.target_field,
            date_field=forecasting.date_field,
            series_keys=forecasting.series_keys,
            forecast_horizon_days=forecast_horizon or forecasting.forecast_horizon_days,
            minimum_history_days=forecasting.minimum_history_days,
            prediction_interval_level=forecasting.prediction_interval_level,
        ),
        splitting=config.splitting,
        features=config.features,
        models=config.models,
        reporting=config.reporting,
    )


def _ensure_can_write(config: ForecastingConfig) -> None:
    output_dir = config.forecasting.output_directory
    forecast_path = config.forecasting.forecast_output_path
    managed_paths = [output_dir, forecast_path]
    if not config.forecasting.overwrite:
        for path in managed_paths:
            if path.exists():
                raise PipelineExecutionError(
                    "Forecast outputs already exist. Pass --overwrite to replace managed outputs."
                )
    output_dir.mkdir(parents=True, exist_ok=True)
    forecast_path.parent.mkdir(parents=True, exist_ok=True)


def _dependency_versions() -> dict[str, str]:
    import numpy as np
    import sklearn  # type: ignore[import-untyped]

    return {"numpy": np.__version__, "scikit-learn": sklearn.__version__}
