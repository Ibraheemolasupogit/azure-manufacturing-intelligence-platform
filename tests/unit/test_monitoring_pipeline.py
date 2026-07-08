"""Tests for Milestone 8 monitoring and observability."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from manufacturing_intelligence.common.exceptions import (
    ConfigurationError,
    DataContractError,
    PipelineExecutionError,
)
from manufacturing_intelligence.monitoring.alerts import deterministic_alert_id, monitoring_alerts
from manufacturing_intelligence.monitoring.config import load_monitoring_config
from manufacturing_intelligence.monitoring.existing_run import validate_existing_run
from manufacturing_intelligence.monitoring.integrity import evidence_integrity_checks
from manufacturing_intelligence.monitoring.pipeline import run_monitoring
from manufacturing_intelligence.monitoring.scoring import health_label

ROOT = Path(__file__).resolve().parents[2]


def test_monitoring_loads_required_manifests(tmp_path: Path) -> None:
    result = run_monitoring(
        ROOT / "configs" / "monitoring_ci.yaml",
        output_directory=tmp_path / "monitoring",
        overwrite=True,
    )
    manifest = json.loads((result.output_directory / "monitoring-manifest.json").read_text())
    assert manifest["monitored_domains"] == [
        "generation",
        "ingestion",
        "forecasting",
        "inventory",
        "quality",
        "maintenance",
    ]
    assert manifest["manifest_integrity_score"] == 100.0
    assert manifest["lineage_completeness_score"] == 100.0


def test_missing_required_evidence_fails_clearly(tmp_path: Path) -> None:
    config_path = tmp_path / "monitoring.yaml"
    text = (ROOT / "configs" / "monitoring_ci.yaml").read_text(encoding="utf-8")
    config_path.write_text(
        text.replace("data/raw/generation_manifest.json", "data/raw/missing_manifest.json"),
        encoding="utf-8",
    )
    with pytest.raises(DataContractError):
        run_monitoring(config_path, output_directory=tmp_path / "out", overwrite=True)


def test_integrity_checks_detect_tampering(tmp_path: Path) -> None:
    run_monitoring(
        ROOT / "configs" / "monitoring_ci.yaml", output_directory=tmp_path / "out", overwrite=True
    )
    alerts = tmp_path / "out" / "monitoring_alerts.csv"
    alerts.write_text(alerts.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(DataContractError):
        validate_existing_run(ROOT / "configs" / "monitoring_ci.yaml", tmp_path / "out")


def test_domain_scores_and_labels_are_in_range(tmp_path: Path) -> None:
    run_monitoring(
        ROOT / "configs" / "monitoring_ci.yaml", output_directory=tmp_path / "out", overwrite=True
    )
    scores = pd.read_csv(tmp_path / "out" / "domain_health_scores.csv")
    assert scores["health_score"].between(0, 100).all()
    assert set(scores["health_label"]) <= {"healthy", "watch", "degraded", "critical"}
    config = load_monitoring_config(ROOT / "configs" / "monitoring_ci.yaml")
    assert health_label(100.0, config.thresholds) == "healthy"
    assert health_label(65.0, config.thresholds) == "degraded"
    assert health_label(40.0, config.thresholds) == "critical"


def test_alert_ids_are_deterministic_and_ordered(tmp_path: Path) -> None:
    config = load_monitoring_config(ROOT / "configs" / "monitoring_ci.yaml")
    integrity = pd.DataFrame(
        [
            {
                "domain": "quality",
                "integrity_status": "failed",
                "path": "b",
                "actual_sha256": "x",
                "expected_sha256": "y",
            },
            {
                "domain": "forecasting",
                "integrity_status": "failed",
                "path": "a",
                "actual_sha256": "x",
                "expected_sha256": "y",
            },
        ]
    )
    lineage = pd.DataFrame(
        [
            {
                "domain": "forecasting",
                "lineage_completeness_score": 100.0,
            }
        ]
    )
    domain_scores = pd.DataFrame(
        [{"domain": "generation", "health_score": 100.0, "health_label": "healthy"}]
    )
    alerts = monitoring_alerts(
        monitoring_run_id="MONITOR-test",
        integrity=integrity,
        lineage=lineage,
        domain_scores=domain_scores,
        thresholds=config.thresholds,
    )
    assert deterministic_alert_id(
        "MONITOR-test", "quality", "critical", "x", "y"
    ) == deterministic_alert_id("MONITOR-test", "quality", "critical", "x", "y")
    assert list(alerts["domain"]) == ["forecasting", "quality"]


def test_platform_summary_is_deterministic(tmp_path: Path) -> None:
    first = run_monitoring(
        ROOT / "configs" / "monitoring_ci.yaml",
        output_directory=tmp_path / "one",
        overwrite=True,
    )
    second = run_monitoring(
        ROOT / "configs" / "monitoring_ci.yaml",
        output_directory=tmp_path / "two",
        overwrite=True,
    )
    assert first.monitoring_run_id == second.monitoring_run_id
    assert (tmp_path / "one" / "platform_health_summary.json").read_text() == (
        tmp_path / "two" / "platform_health_summary.json"
    ).read_text()


def test_overwrite_protection_preserves_unrelated_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "monitoring"
    output_dir.mkdir()
    unrelated = output_dir / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    run_monitoring(
        ROOT / "configs" / "monitoring.yaml", output_directory=output_dir, overwrite=True
    )
    with pytest.raises(PipelineExecutionError):
        run_monitoring(ROOT / "configs" / "monitoring.yaml", output_directory=output_dir)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_invalid_configuration_is_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "monitoring.yaml"
    text = (ROOT / "configs" / "monitoring_ci.yaml").read_text(encoding="utf-8")
    config_path.write_text(
        text.replace("critical_score_threshold: 50", "critical_score_threshold: 90"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError):
        load_monitoring_config(config_path)


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("COV_CORE") or key == "COVERAGE_PROCESS_START":
            env.pop(key, None)
    output_dir = tmp_path / "outside"
    completed = subprocess.run(
        [
            "python3",
            "-m",
            "manufacturing_intelligence.monitoring",
            "--config",
            str(ROOT / "configs" / "monitoring_ci.yaml"),
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
    assert "Monitoring MONITOR-" in completed.stdout
    validate_existing_run(ROOT / "configs" / "monitoring_ci.yaml", output_dir)


def test_relevant_config_change_alters_run_id(tmp_path: Path) -> None:
    config_copy = tmp_path / "monitoring_ci.yaml"
    shutil.copy(ROOT / "configs" / "monitoring_ci.yaml", config_copy)
    first = run_monitoring(config_copy, output_directory=tmp_path / "one", overwrite=True)
    config_copy.write_text(
        config_copy.read_text(encoding="utf-8").replace(
            "minimum_pipeline_health_score: 80", "minimum_pipeline_health_score: 81"
        ),
        encoding="utf-8",
    )
    second = run_monitoring(config_copy, output_directory=tmp_path / "two", overwrite=True)
    assert first.monitoring_run_id != second.monitoring_run_id


def test_evidence_integrity_checks_cover_generation() -> None:
    generation = json.loads((ROOT / "data/raw/generation_manifest.json").read_text())
    checks = evidence_integrity_checks(
        {
            "generation": generation,
            "ingestion": {"accepted_outputs": {}},
            "forecasting": {"output_files": {}},
            "inventory": {"output_files": {}},
            "quality": {"output_files": {}},
            "maintenance": {"output_files": {}},
        }
    )
    assert "generation" in set(checks["domain"])
    assert checks["integrity_status"].eq("passed").all()
