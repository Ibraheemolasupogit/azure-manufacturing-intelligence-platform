from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest
import yaml

from manufacturing_intelligence.common.exceptions import (
    ConfigurationError,
    DataContractError,
    ManufacturingIntelligenceError,
    PipelineExecutionError,
)
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.data_generation.generator import (
    generate_synthetic_data,
    validate_generated_run,
)
from manufacturing_intelligence.forecasting.aggregation import build_daily_demand
from manufacturing_intelligence.forecasting.config import load_forecasting_config
from manufacturing_intelligence.forecasting.evaluation import metrics
from manufacturing_intelligence.forecasting.existing_run import validate_existing_run
from manufacturing_intelligence.forecasting.features import build_feature_dataset
from manufacturing_intelligence.forecasting.models import (
    moving_average_predict,
    seasonal_naive_predict,
)
from manufacturing_intelligence.forecasting.pipeline import run_forecast
from manufacturing_intelligence.ingestion.existing_run import (
    validate_existing_run as validate_ingestion_run,
)
from manufacturing_intelligence.ingestion.pipeline import run_ingestion
from scripts.prepare_forecasting_data import _verify_summary


def test_forecast_uses_governed_input_and_preserves_it(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    before = sha256_file(project_root() / "data" / "interim" / "accepted" / "sales_orders.csv")

    result = run_forecast(config)
    after = sha256_file(project_root() / "data" / "interim" / "accepted" / "sales_orders.csv")

    assert result.forecast_rows == 56
    assert before == after
    manifest = json.loads((tmp_path / "forecasting" / "forecast-manifest.json").read_text())
    assert manifest["governed_input_path"] == "data/interim/accepted/sales_orders.csv"
    assert manifest["upstream_ingestion_run_id"] == "INGEST-da9a11a67abc6a18"


def test_direct_raw_input_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["forecasting"].update({"input_path": "data/raw/sales_orders.csv"}),
    )

    with pytest.raises(DataContractError, match="data/raw"):
        run_forecast(config)


def test_upstream_manifest_hash_and_row_count_are_verified(tmp_path: Path) -> None:
    raw = _copy_interim(tmp_path)
    manifest_path = raw / "_metadata" / "ingestion-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["accepted_outputs"]["sales_orders"]["row_count"] = 999
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    config = _config_for(
        tmp_path,
        lambda payload: payload["forecasting"].update(
            {
                "input_path": str(raw / "accepted" / "sales_orders.csv"),
                "ingestion_manifest_path": str(manifest_path),
                "validation_summary_path": str(raw / "_metadata" / "validation-summary.json"),
                "data_quality_report_path": str(raw / "_metadata" / "data-quality-report.json"),
                "lineage_path": str(raw / "_metadata" / "lineage-records.json"),
            }
        ),
    )

    with pytest.raises(DataContractError, match="row count"):
        run_forecast(config)


def test_daily_aggregation_and_calendar_fill_policy(tmp_path: Path) -> None:
    config = load_forecasting_config(_config_for(tmp_path))
    frame = pd.DataFrame(
        [
            {
                "order_date": "2026-01-01",
                "product_id": "P1",
                "distribution_region": "north",
                "ordered_quantity": 2,
            },
            {
                "order_date": "2026-01-01",
                "product_id": "P1",
                "distribution_region": "north",
                "ordered_quantity": 3,
            },
            {
                "order_date": "2026-01-03",
                "product_id": "P1",
                "distribution_region": "north",
                "ordered_quantity": 4,
            },
        ]
    )

    daily = build_daily_demand(frame, config)

    assert list(daily["demand_quantity"]) == [5.0, 0.0, 4.0]
    assert list(daily["source_order_count"]) == [2, 0, 1]
    assert list(daily["calendar_filled_flag"]) == [False, True, False]
    assert daily["series_id"].tolist() == ["P1|north", "P1|north", "P1|north"]


def test_lag_and_rolling_features_do_not_use_current_target(tmp_path: Path) -> None:
    config = load_forecasting_config(_config_for(tmp_path))
    daily = pd.DataFrame(
        {
            "series_id": ["P1|north"] * 8,
            "product_id": ["P1"] * 8,
            "distribution_region": ["north"] * 8,
            "demand_date": pd.date_range("2026-01-01", periods=8),
            "demand_quantity": [10, 20, 30, 40, 50, 60, 70, 80],
            "source_order_count": [1] * 8,
            "calendar_filled_flag": [False] * 8,
        }
    )

    features = build_feature_dataset(daily, config)

    row = features.iloc[7]
    assert row["lag_1_demand"] == 70
    assert row["lag_7_demand"] == 10
    assert row["rolling_mean_3"] == pytest.approx((50 + 60 + 70) / 3)


def test_chronological_splits_and_future_dates(tmp_path: Path) -> None:
    result = run_forecast(_config_for(tmp_path))
    split = json.loads((result.output_directory / "split_metadata.json").read_text())
    forecast = pd.read_csv(tmp_path / "demand_forecast.csv")

    assert split["train_end"] < split["validation_start"]
    assert split["validation_end"] < split["test_start"]
    assert split["test_end"] < split["forecast_start"]
    assert pd.to_datetime(forecast["forecast_date"]).min() > pd.to_datetime(split["test_end"])


def test_baselines_and_metrics_are_mathematically_correct() -> None:
    history = pd.DataFrame(
        {
            "series_id": ["S"] * 8,
            "demand_date": pd.date_range("2026-01-01", periods=8),
            "demand_quantity": [1, 2, 3, 4, 5, 6, 7, 8],
        }
    )
    target = pd.DataFrame({"series_id": ["S"], "demand_date": [pd.Timestamp("2026-01-08")]})

    assert seasonal_naive_predict(history, target, 7).iloc[0] == 1
    assert moving_average_predict(history, target, 3).iloc[0] == pytest.approx(6)
    scored = metrics([10, 20], [12, 18])
    assert scored["mae"] == pytest.approx(2)
    assert scored["rmse"] == pytest.approx(2)
    assert scored["wape"] == pytest.approx(4 / 30)
    assert scored["bias"] == pytest.approx(0)
    assert metrics([0], [0])["wape"] is None


def test_same_inputs_produce_identical_outputs_and_config_changes_run_id(tmp_path: Path) -> None:
    first = run_forecast(_config_for(tmp_path / "first"))
    second = run_forecast(_config_for(tmp_path / "second"))
    changed = run_forecast(
        _config_for(
            tmp_path / "changed",
            lambda payload: payload["forecasting"].update({"random_seed": 20260705}),
        )
    )

    assert first.forecast_run_id == second.forecast_run_id
    assert first.forecast_run_id != changed.forecast_run_id
    assert _tree_bytes(first.output_directory) == _tree_bytes(second.output_directory)


def test_existing_run_validation_and_tamper_detection(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_forecast(config)
    validate_existing_run(config)
    with (tmp_path / "demand_forecast.csv").open("a", encoding="utf-8") as handle:
        handle.write("#tamper\n")

    with pytest.raises(DataContractError, match="MISMATCH"):
        validate_existing_run(config)


def test_interval_ordering_no_duplicates_and_overwrite_protection(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_forecast(config)
    forecast = pd.read_csv(tmp_path / "demand_forecast.csv")

    assert not forecast.duplicated(["series_id", "forecast_date"]).any()
    assert (forecast["lower_bound"] <= forecast["point_forecast"]).all()
    assert (forecast["upper_bound"] >= forecast["point_forecast"]).all()
    assert (forecast["lower_bound"] >= 0).all()
    with pytest.raises(PipelineExecutionError, match="already exist"):
        run_forecast(config)


def test_invalid_config_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["features"].update({"lag_days": [1, 1]}),
    )

    with pytest.raises(ConfigurationError, match="positive unique"):
        load_forecasting_config(config)


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output = tmp_path / "forecasting"
    env = os.environ.copy()
    for key in (
        "COVERAGE_PROCESS_START",
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
    ):
        env.pop(key, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.forecasting",
            "--config",
            str(project_root() / "configs" / "forecasting.yaml"),
            "--output-directory",
            str(output),
            "--overwrite",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert completed.returncode == 0
    assert "Forecast FORECAST-" in completed.stdout


def test_extended_profile_sales_references_resolve_and_ingest_without_quarantine(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    generated = generate_synthetic_data(
        config_path=project_root() / "configs" / "synthetic_data_forecasting.yaml",
        output_dir=raw,
        overwrite=True,
    )
    validate_generated_run(raw)
    first_ids = _sales_order_ids(raw / "sales_orders.csv")
    second_raw = tmp_path / "raw_second"
    generate_synthetic_data(
        config_path=project_root() / "configs" / "synthetic_data_forecasting.yaml",
        output_dir=second_raw,
        overwrite=True,
    )

    assert generated.run_id == "synthetic-f0db089ccb37ba01"
    assert first_ids == _sales_order_ids(second_raw / "sales_orders.csv")
    assert len(first_ids) == len(set(first_ids)) == 1629
    production_products = _jsonl_values(raw / "production_events.jsonl", "product_id")
    sales_rows = list(csv.DictReader((raw / "sales_orders.csv").open()))
    assert {row["product_id"] for row in sales_rows} <= production_products
    assert all(row["order_date"] <= row["requested_delivery_date"] for row in sales_rows)
    assert all(int(row["fulfilled_quantity"]) <= int(row["ordered_quantity"]) for row in sales_rows)
    assert all(
        float(row["order_value"])
        == round(int(row["fulfilled_quantity"]) * float(row["selling_price"]), 2)
        for row in sales_rows
    )

    ingestion_config = _extended_ingestion_config(tmp_path, raw)
    ingestion = run_ingestion(ingestion_config)
    validate_ingestion_run(ingestion_config, ingestion.output_directory)
    summary = json.loads(
        (ingestion.output_directory / "_metadata" / "validation-summary.json").read_text()
    )
    assert summary["source_counts_by_dataset"]["sales_orders"] == 1629
    assert summary["accepted_counts_by_dataset"]["sales_orders"] == 1629
    assert summary["quarantine_counts_by_dataset"]["sales_orders"] == 0
    assert summary["rule_code_counts"] == {}


def test_prepare_threshold_rejects_unexpected_sales_quarantine() -> None:
    summary = {
        "discovered_datasets": [
            "production_events",
            "inventory_levels",
            "sales_orders",
            "quality_checks",
            "equipment_health",
            "warehouse_movements",
            "supplier_performance",
        ],
        "source_counts_by_dataset": {"sales_orders": 100},
        "accepted_counts_by_dataset": {"sales_orders": 99},
        "quarantine_counts_by_dataset": {"sales_orders": 1},
    }

    with pytest.raises(ManufacturingIntelligenceError, match="quarantine threshold exceeded"):
        _verify_summary(summary, 0.0)


def test_extended_forecast_uses_accepted_input_and_three_rolling_origins(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    generate_synthetic_data(
        config_path=project_root() / "configs" / "synthetic_data_forecasting.yaml",
        output_dir=raw,
        overwrite=True,
    )
    ingestion_config = _extended_ingestion_config(tmp_path, raw)
    ingestion = run_ingestion(ingestion_config)
    forecast_config = _extended_forecast_config(tmp_path, ingestion.output_directory)

    result = run_forecast(forecast_config)
    manifest = json.loads((result.output_directory / "forecast-manifest.json").read_text())
    backtest = pd.read_csv(result.output_directory / "backtest_predictions.csv")

    assert manifest["governed_input_path"].endswith("accepted/sales_orders.csv")
    assert "/raw/" not in manifest["governed_input_path"]
    assert manifest["governed_input_sha256"] == sha256_file(
        ingestion.output_directory / "accepted" / "sales_orders.csv"
    )
    origins = sorted(backtest["forecast_origin"].unique())
    assert len(origins) == 3
    assert origins == sorted(origins)


def _config_for(
    tmp_path: Path,
    mutate: Any | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_load((project_root() / "configs" / "forecasting.yaml").read_text())
    payload["forecasting"].update(
        {
            "output_directory": str(tmp_path / "forecasting"),
            "forecast_output_path": str(tmp_path / "demand_forecast.csv"),
            "report_directory": str(tmp_path / "reports"),
            "overwrite": False,
        }
    )
    if mutate:
        mutate(payload)
    path = tmp_path / "forecasting.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _copy_interim(tmp_path: Path) -> Path:
    target = tmp_path / "interim"
    shutil.copytree(project_root() / "data" / "interim", target)
    return target


def _extended_ingestion_config(tmp_path: Path, raw: Path) -> Path:
    payload = yaml.safe_load(
        (project_root() / "configs" / "ingestion_forecasting.yaml").read_text()
    )
    payload["ingestion"].update(
        {
            "input_directory": str(raw),
            "output_directory": str(tmp_path / "interim"),
            "overwrite": True,
        }
    )
    payload["validation"].update(
        {
            "generation_manifest_path": str(raw / "generation_manifest.json"),
            "schema_registry_path": str(raw / "schema_metadata.json"),
            "entity_catalogue_path": str(raw / "schema_metadata.json"),
        }
    )
    path = tmp_path / "ingestion_forecasting.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _extended_forecast_config(tmp_path: Path, interim: Path) -> Path:
    payload = yaml.safe_load((project_root() / "configs" / "forecasting_extended.yaml").read_text())
    payload["forecasting"].update(
        {
            "input_path": str(interim / "accepted" / "sales_orders.csv"),
            "ingestion_manifest_path": str(interim / "_metadata" / "ingestion-manifest.json"),
            "validation_summary_path": str(interim / "_metadata" / "validation-summary.json"),
            "data_quality_report_path": str(interim / "_metadata" / "data-quality-report.json"),
            "lineage_path": str(interim / "_metadata" / "lineage-records.json"),
            "output_directory": str(tmp_path / "forecasting"),
            "forecast_output_path": str(tmp_path / "extended_demand_forecast.csv"),
            "report_directory": str(tmp_path / "reports"),
            "overwrite": True,
        }
    )
    path = tmp_path / "forecasting_extended.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _sales_order_ids(path: Path) -> list[str]:
    return [row["order_id"] for row in csv.DictReader(path.open())]


def _jsonl_values(path: Path, field: str) -> set[str]:
    return {json.loads(line)[field] for line in path.read_text().splitlines() if line}


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        child.relative_to(path).as_posix(): child.read_bytes()
        for child in sorted(path.rglob("*"))
        if child.is_file()
    }
