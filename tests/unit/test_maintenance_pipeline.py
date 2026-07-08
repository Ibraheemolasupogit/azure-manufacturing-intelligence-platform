"""Tests for Milestone 7 predictive maintenance."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from manufacturing_intelligence.common.exceptions import DataContractError, PipelineExecutionError
from manufacturing_intelligence.maintenance.anomalies import calculate_anomaly_scores
from manufacturing_intelligence.maintenance.config import AnomalySettings, load_maintenance_config
from manufacturing_intelligence.maintenance.existing_run import validate_existing_run
from manufacturing_intelligence.maintenance.pipeline import run_maintenance
from manufacturing_intelligence.maintenance.scoring import deterministic_alert_id
from manufacturing_intelligence.maintenance.thresholds import evaluate_thresholds

ROOT = Path(__file__).resolve().parents[2]


def test_maintenance_uses_governed_accepted_inputs(tmp_path: Path) -> None:
    result = run_maintenance(
        ROOT / "configs" / "maintenance_ci.yaml",
        output_directory=tmp_path / "maintenance",
        overwrite=True,
    )

    manifest = json.loads((result.output_directory / "maintenance-manifest.json").read_text())
    assert manifest["governed_input_paths"]["equipment_health"].endswith(
        "data/interim/accepted/equipment_health.jsonl"
    )
    assert manifest["governed_input_paths"]["production_events"].endswith(
        "data/interim/accepted/production_events.jsonl"
    )
    assert manifest["governed_input_row_counts"]["equipment_health"] == 504
    assert manifest["governed_input_row_counts"]["production_events"] == 168
    assert manifest["governed_inputs_modified"] is False


def test_raw_equipment_input_is_rejected() -> None:
    with pytest.raises(DataContractError):
        run_maintenance(
            ROOT / "configs" / "maintenance_ci.yaml",
            equipment_health_path=ROOT / "data" / "raw" / "equipment_health.jsonl",
            overwrite=True,
        )


def test_threshold_calculation_and_consistency() -> None:
    frame = pd.DataFrame(
        [
            {
                "measurement": 7.0,
                "warning_threshold": 6.5,
                "critical_threshold": 8.0,
                "threshold_status": "warning",
            },
            {
                "measurement": 8.5,
                "warning_threshold": 6.5,
                "critical_threshold": 8.0,
                "threshold_status": "normal",
            },
        ]
    )
    result = evaluate_thresholds(
        frame,
        load_maintenance_config(ROOT / "configs" / "maintenance_ci.yaml").thresholds,
    )
    assert result.loc[0, "warning_breach_flag"]
    assert result.loc[1, "critical_breach_flag"]
    assert not result.loc[1, "threshold_consistency_flag"]


def test_isolation_forest_is_deterministic_and_not_probability() -> None:
    config = load_maintenance_config(ROOT / "configs" / "maintenance_ci.yaml")
    frame = pd.read_csv(ROOT / "outputs" / "maintenance" / "equipment_health_features.csv")
    first = calculate_anomaly_scores(frame, config.anomaly_detection, random_seed=20260707)
    second = calculate_anomaly_scores(frame, config.anomaly_detection, random_seed=20260707)
    pd.testing.assert_frame_equal(first, second)
    assert (
        first["isolation_forest_score_interpretation"]
        .eq("relative_anomaly_score_not_probability")
        .all()
    )


def test_zero_mad_and_insufficient_history_are_explicit() -> None:
    settings = AnomalySettings(
        enabled=True,
        models=("robust_zscore", "isolation_forest"),
        contamination=0.05,
        robust_zscore_threshold=3.5,
        minimum_training_rows=3,
    )
    frame = pd.DataFrame(
        [
            {
                "sensor_event_id": f"EH-T{i:03d}",
                "machine_id": "M1",
                "sensor_type": "temperature",
                "measurement_unit": "celsius",
                "event_timestamp": pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(hours=i),
                "sensor_value": 10.0,
                "critical_threshold": 20.0,
                "warning_threshold": 15.0,
                "normalised_distance_to_nearest_threshold": 1.0,
                "runtime_hours": 1.0,
                "service_hours_since_maintenance": 1.0,
                "warning_breach_flag": False,
                "critical_breach_flag": False,
                "rolling_mean_3": 10.0,
                "rolling_std_3": 0.0,
            }
            for i in range(5)
        ]
    )
    result = calculate_anomaly_scores(frame, settings, random_seed=1)
    assert "insufficient_history" in set(result["robust_zscore_status"])
    assert "zero_mad_fallback" in set(result["robust_zscore_status"])


def test_existing_run_validation_detects_output_tampering(tmp_path: Path) -> None:
    run_maintenance(
        ROOT / "configs" / "maintenance_ci.yaml",
        output_directory=tmp_path / "maintenance",
        overwrite=True,
    )
    validate_existing_run(ROOT / "configs" / "maintenance_ci.yaml", tmp_path / "maintenance")
    alerts = tmp_path / "maintenance" / "maintenance_alerts.csv"
    alerts.write_text(alerts.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(DataContractError):
        validate_existing_run(ROOT / "configs" / "maintenance_ci.yaml", tmp_path / "maintenance")


def test_overwrite_protection_preserves_unrelated_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "maintenance"
    unrelated = output_dir / "keep.txt"
    output_dir.mkdir()
    unrelated.write_text("keep", encoding="utf-8")
    run_maintenance(
        ROOT / "configs" / "maintenance.yaml", output_directory=output_dir, overwrite=True
    )
    with pytest.raises(PipelineExecutionError):
        run_maintenance(ROOT / "configs" / "maintenance.yaml", output_directory=output_dir)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "outside"
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("COV_CORE") or key == "COVERAGE_PROCESS_START":
            env.pop(key, None)
    completed = subprocess.run(
        [
            "python3",
            "-m",
            "manufacturing_intelligence.maintenance",
            "--config",
            str(ROOT / "configs" / "maintenance_ci.yaml"),
            "--output-directory",
            str(output_dir),
            "--overwrite",
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Maintenance MAINT-" in completed.stdout
    validate_existing_run(ROOT / "configs" / "maintenance_ci.yaml", output_dir)


def test_relevant_config_change_alters_run_id(tmp_path: Path) -> None:
    config_copy = tmp_path / "maintenance_ci.yaml"
    shutil.copy(ROOT / "configs" / "maintenance_ci.yaml", config_copy)
    first = run_maintenance(config_copy, output_directory=tmp_path / "one", overwrite=True)
    text = config_copy.read_text(encoding="utf-8").replace(
        "robust_zscore_threshold: 3.5", "robust_zscore_threshold: 3.6"
    )
    config_copy.write_text(text, encoding="utf-8")
    second = run_maintenance(config_copy, output_directory=tmp_path / "two", overwrite=True)
    assert first.maintenance_run_id != second.maintenance_run_id


def test_alert_ids_are_deterministic() -> None:
    assert deterministic_alert_id("MAINT-x", "EH-1") == deterministic_alert_id("MAINT-x", "EH-1")
