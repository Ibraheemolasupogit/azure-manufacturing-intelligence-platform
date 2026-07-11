from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from manufacturing_intelligence.common.exceptions import ConfigurationError, DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.dashboard.config import load_dashboard_config
from manufacturing_intelligence.dashboard.data import load_dashboard_evidence
from manufacturing_intelligence.dashboard.existing_run import validate_existing_run
from manufacturing_intelligence.dashboard.pipeline import run_dashboard


def test_required_governed_evidence_is_loaded_and_hashed() -> None:
    config = load_dashboard_config(Path("configs/dashboard.yaml"))
    evidence = load_dashboard_evidence(config)
    assert set(evidence.manifests) == {
        "ingestion",
        "forecasting",
        "inventory",
        "quality",
        "maintenance",
        "monitoring",
        "genai",
    }
    assert evidence.input_hashes["genai_manifest_path"] == sha256_file(
        project_root() / "outputs/genai/genai-manifest.json"
    )


def test_missing_required_evidence_fails_clearly(tmp_path: Path) -> None:
    config_copy = tmp_path / "dashboard.yaml"
    config_copy.write_text(
        (project_root() / "configs/dashboard.yaml")
        .read_text(encoding="utf-8")
        .replace(
            "outputs/demand_forecast.csv",
            "outputs/missing_demand_forecast.csv",
        ),
        encoding="utf-8",
    )
    with pytest.raises(DataContractError, match="DASHBOARD_REQUIRED_INPUT_MISSING"):
        load_dashboard_evidence(load_dashboard_config(config_copy))


def test_dashboard_generation_outputs_required_tables(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    result = run_dashboard(
        Path("configs/dashboard.yaml"),
        output_directory=output_dir,
        overwrite=True,
    )
    assert result.table_count == 19
    required = [
        "dim_date.csv",
        "dim_product.csv",
        "fact_production_kpis.csv",
        "fact_demand_forecast.csv",
        "fact_inventory_risk.csv",
        "fact_quality_alerts.csv",
        "fact_maintenance_alerts.csv",
        "fact_platform_health.csv",
        "fact_operations_assistant_narratives.csv",
        "executive_scorecard.csv",
        "metric_catalogue.csv",
    ]
    for name in required:
        assert (output_dir / name).is_file()
        assert not pd.read_csv(output_dir / name).empty


def test_primary_keys_and_relationships_are_valid(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    validate_existing_run(Path("configs/dashboard.yaml"), output_dir)
    semantic = json.loads((output_dir / "semantic_model.json").read_text(encoding="utf-8"))
    assert semantic["relationships"]
    table_names = {table["name"] for table in semantic["tables"]}
    assert "fact_inventory_risk" in table_names


def test_metric_catalogue_and_scorecard_contents(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    metrics = pd.read_csv(output_dir / "metric_catalogue.csv")
    scorecard = pd.read_csv(output_dir / "executive_scorecard.csv")
    assert {
        "production_output",
        "demand_forecast",
        "inventory_score",
        "quality_alert",
        "maintenance_alert",
        "platform_health",
        "assistant_response_count",
    } <= set(metrics["metric_name"])
    assert len(scorecard) == 14
    assert not metrics["calculation_formula"].isna().any()


def test_page_and_visual_specs_reference_existing_pages(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    pages = json.loads((output_dir / "dashboard_page_specs.json").read_text(encoding="utf-8"))
    visuals = json.loads((output_dir / "visual_specifications.json").read_text(encoding="utf-8"))
    page_ids = {page["page_id"] for page in pages}
    assert len(page_ids) == 8
    assert len(visuals) == 48
    assert {visual["page_id"] for visual in visuals} <= page_ids
    assert all("synthetic" in page["synthetic_data_disclaimer"].lower() for page in pages)


def test_manifest_sizes_hashes_and_lineage_are_valid(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    manifest = json.loads((output_dir / "dashboard-manifest.json").read_text(encoding="utf-8"))
    for evidence in manifest["output_files"].values():
        path = output_dir.parent / evidence["path"]
        assert path.stat().st_size == evidence["file_size_bytes"]
        assert sha256_file(path) == evidence["sha256"]
    lineage = json.loads((output_dir / "lineage-records.json").read_text(encoding="utf-8"))
    assert {item["path"] for item in manifest["output_files"].values()} <= {
        item["target_path"] for item in lineage
    }
    assert manifest["power_bi_deployment"] is False
    assert manifest["azure_deployment"] is False


def test_dashboard_runs_are_deterministic_and_config_changes_run_id(tmp_path: Path) -> None:
    output_one = tmp_path / "one" / "dashboard"
    output_two = tmp_path / "two" / "dashboard"
    result_one = run_dashboard(
        Path("configs/dashboard.yaml"),
        output_directory=output_one,
        overwrite=True,
    )
    result_two = run_dashboard(
        Path("configs/dashboard.yaml"),
        output_directory=output_one,
        overwrite=True,
    )
    config_copy = tmp_path / "dashboard.yaml"
    config_copy.write_text(
        (project_root() / "configs/dashboard.yaml")
        .read_text(encoding="utf-8")
        .replace(
            "maximum_visuals_per_page: 12",
            "maximum_visuals_per_page: 8",
        ),
        encoding="utf-8",
    )
    result_three = run_dashboard(config_copy, output_directory=output_two, overwrite=True)
    assert result_one.dashboard_run_id == result_two.dashboard_run_id
    assert result_one.dashboard_run_id != result_three.dashboard_run_id


def test_existing_run_validation_detects_output_tampering(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    scorecard = output_dir / "executive_scorecard.csv"
    scorecard.write_text(scorecard.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    with pytest.raises(DataContractError, match=r"DASHBOARD_OUTPUT_.*MISMATCH"):
        validate_existing_run(Path("configs/dashboard.yaml"), output_dir)


def test_existing_run_validation_detects_manifest_tampering(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    manifest_path = output_dir / "dashboard-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dashboard_run_id"] = "DASHBOARD-tampered"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="DASHBOARD_RUN_ID_MISMATCH"):
        validate_existing_run(Path("configs/dashboard.yaml"), output_dir)


def test_overwrite_protection_preserves_unrelated_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir, overwrite=True)
    unrelated = output_dir / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    with pytest.raises(Exception, match="Dashboard outputs already exist"):
        run_dashboard(Path("configs/dashboard.yaml"), output_directory=output_dir)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_invalid_configuration_is_rejected(tmp_path: Path) -> None:
    config_copy = tmp_path / "dashboard.yaml"
    config_copy.write_text(
        (project_root() / "configs/dashboard.yaml")
        .read_text(encoding="utf-8")
        .replace(
            "semantic_model_name: manufacturing_operations_intelligence",
            "semantic_model_name: ''",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="Required string"):
        load_dashboard_config(config_copy)


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "dashboard"
    dashboard_dir = tmp_path / "portfolio"
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("COV_CORE") or key.startswith("COVERAGE"):
            env.pop(key)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.dashboard",
            "--config",
            "configs/dashboard.yaml",
            "--output-directory",
            str(output_dir),
            "--dashboard-directory",
            str(dashboard_dir),
            "--overwrite",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (output_dir / "dashboard-manifest.json").is_file()
    assert (dashboard_dir / "dashboard_index.md").is_file()


def test_ci_dashboard_execution_completes_quickly(tmp_path: Path) -> None:
    output_dir = tmp_path / "ci" / "dashboard"
    result = run_dashboard(
        Path("configs/dashboard_ci.yaml"),
        output_directory=output_dir,
        overwrite=True,
    )
    assert result.table_count == 19
    validate_existing_run(Path("configs/dashboard_ci.yaml"), output_dir)
