from __future__ import annotations

import json
import os
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
    PipelineExecutionError,
)
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.quality.capability import calculate_process_capability
from manufacturing_intelligence.quality.config import CapabilitySettings, load_quality_config
from manufacturing_intelligence.quality.control_charts import (
    calculate_control_chart_points,
    evaluate_spc_rules,
)
from manufacturing_intelligence.quality.existing_run import validate_existing_run
from manufacturing_intelligence.quality.pipeline import run_quality
from manufacturing_intelligence.quality.specification import evaluate_specification


def test_quality_uses_governed_inputs_and_preserves_upstream_files(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    upstream = {
        "quality": project_root() / "data" / "interim" / "accepted" / "quality_checks.csv",
        "production": project_root() / "data" / "interim" / "accepted" / "production_events.jsonl",
    }
    before = {name: sha256_file(path) for name, path in upstream.items()}

    result = run_quality(config)
    after = {name: sha256_file(path) for name, path in upstream.items()}

    assert result.observation_rows == 168
    assert result.alert_rows == 38
    assert before == after
    manifest = json.loads((tmp_path / "quality" / "quality-manifest.json").read_text())
    assert manifest["upstream_ingestion_run_id"] == "INGEST-da9a11a67abc6a18"
    assert manifest["governed_input_hashes"]["quality_checks"] == before["quality"]
    assert manifest["governed_input_hashes"]["production_events"] == before["production"]


def test_quality_outputs_are_deterministic_and_config_changes_run_id(tmp_path: Path) -> None:
    first = run_quality(_config_for(tmp_path / "first"))
    second = run_quality(_config_for(tmp_path / "second"))
    changed = run_quality(
        _config_for(
            tmp_path / "changed",
            lambda payload: payload["anomaly_detection"].update({"robust_zscore_threshold": 4.0}),
        )
    )

    assert first.quality_run_id == second.quality_run_id
    assert first.quality_run_id != changed.quality_run_id
    assert _tree_bytes(first.output_directory) == _tree_bytes(second.output_directory)


def test_quality_outputs_and_alerts_are_coherent(tmp_path: Path) -> None:
    result = run_quality(_config_for(tmp_path))
    observations = pd.read_csv(result.output_directory / "quality_observations.csv")
    alerts = pd.read_csv(result.output_directory / "quality_alerts.csv")
    pareto = pd.read_csv(result.output_directory / "defect_pareto.csv")
    diagnostics = json.loads((result.output_directory / "quality_diagnostics.json").read_text())

    assert len(observations) == 168
    assert observations["quality_risk_score"].between(0, 100).all()
    assert observations["calculated_specification_result"].isin(["pass", "fail"]).all()
    assert alerts["alert_id"].is_unique
    assert not alerts["investigation_context"].str.contains("root cause", case=False).any()
    assert pareto["rank"].min() == 1
    assert diagnostics["spc_signals_by_rule"]["SPC_RULE_1"] == 5
    assert diagnostics["robust_z_anomaly_count"] == 2


def test_specification_capability_and_spc_math() -> None:
    frame = pd.DataFrame(
        {
            "inspection_id": [f"QC-{i:03d}" for i in range(12)],
            "inspection_timestamp": pd.date_range("2026-01-01", periods=12, freq="h"),
            "plant_id": ["PLANT-01"] * 12,
            "line_id": ["LINE-01-01"] * 12,
            "production_line_id": ["LINE-01-01"] * 12,
            "machine_id": ["MACH-01"] * 12,
            "batch_id": [f"BATCH-{i:03d}" for i in range(12)],
            "product_id": ["PROD-001"] * 12,
            "quality_metric": ["diameter_mm"] * 12,
            "measurement_unit": ["mm"] * 12,
            "sample_size": [10] * 12,
            "defective_units": [0] * 11 + [2],
            "measured_value": [10.0] * 8 + [10.1, 10.1, 10.1, 11.2],
            "lower_specification_limit": [9.5] * 12,
            "upper_specification_limit": [10.5] * 12,
            "inspection_result": ["pass"] * 11 + ["fail"],
            "defect_category": [""] * 12,
            "severity": ["none"] * 11 + ["high"],
        }
    )
    specified = evaluate_specification(
        frame,
        load_quality_config().specification,
    )
    assert specified.loc[11, "above_upper_limit_flag"]
    assert specified.loc[11, "calculated_specification_result"] == "fail"
    capability = calculate_process_capability(
        specified,
        CapabilitySettings(True, 10, True, True),
    )
    assert capability.loc[0, "cp"] > 0
    charts = calculate_control_chart_points(specified, load_quality_config().spc)
    spc = evaluate_spc_rules(specified, charts, load_quality_config().spc)
    assert "SPC_RULE_1" in set(";".join(spc["spc_rule_codes"].fillna("")).split(";"))


def test_existing_run_validation_and_tamper_detection(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_quality(config)
    validate_existing_run(config)
    with (tmp_path / "quality" / "quality_alerts.csv").open("a", encoding="utf-8") as handle:
        handle.write("#tamper\n")

    with pytest.raises(DataContractError, match="MISMATCH"):
        validate_existing_run(config)


def test_direct_raw_quality_input_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["quality"].update(
            {"quality_checks_path": "data/raw/quality_checks.csv"}
        ),
    )

    with pytest.raises(DataContractError, match="data/raw"):
        run_quality(config)


def test_invalid_quality_config_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["risk_scoring"].update({"critical_threshold": 40}),
    )

    with pytest.raises(ConfigurationError, match="critical_threshold"):
        load_quality_config(config)


def test_quality_overwrite_protection_and_cli(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_quality(config)

    with pytest.raises(PipelineExecutionError, match="already exist"):
        run_quality(config)

    output = tmp_path / "cli-quality"
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
            "manufacturing_intelligence.quality",
            "--config",
            str(project_root() / "configs" / "quality.yaml"),
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
    assert "Quality QUALITY-" in completed.stdout


def _config_for(
    tmp_path: Path,
    mutate: Any | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_load((project_root() / "configs" / "quality.yaml").read_text())
    payload["quality"].update(
        {
            "output_directory": str(tmp_path / "quality"),
            "quality_alerts_path": str(tmp_path / "quality_alerts.csv"),
            "report_directory": str(tmp_path / "reports"),
            "overwrite": False,
        }
    )
    if mutate:
        mutate(payload)
    path = tmp_path / "quality.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        child.relative_to(path).as_posix(): child.read_bytes()
        for child in sorted(path.rglob("*"))
        if child.is_file()
    }
