from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from manufacturing_intelligence.common.exceptions import (
    ConfigurationError,
    DataContractError,
    PipelineExecutionError,
)
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.release.config import load_release_config
from manufacturing_intelligence.release.existing_run import validate_existing_run
from manufacturing_intelligence.release.pipeline import run_release


def test_release_config_loads() -> None:
    config = load_release_config(Path("configs/release.yaml"))
    assert config.release.release_mode == "portfolio_evidence"
    assert config.release.allow_external_services is False
    assert config.release.synthetic_data_only is True


def test_invalid_external_service_and_cloud_config_rejected(tmp_path: Path) -> None:
    base = Path("configs/release.yaml").read_text(encoding="utf-8")
    external = tmp_path / "external.yaml"
    external.write_text(
        base.replace("allow_external_services: false", "allow_external_services: true")
    )
    with pytest.raises(ConfigurationError):
        load_release_config(external)
    cloud = tmp_path / "cloud.yaml"
    cloud.write_text(base.replace("allow_cloud_deployment: false", "allow_cloud_deployment: true"))
    with pytest.raises(ConfigurationError):
        load_release_config(cloud)


def test_release_generation_outputs_catalogues(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    result = run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=True)
    assert result.evidence_count > 100
    assert result.report_count >= 20
    assert result.catalogue_count == 8
    for name in [
        "final_evidence_index.csv",
        "final_evidence_index.json",
        "final_report_index.csv",
        "final_architecture_index.csv",
        "final_data_catalogue.csv",
        "final_model_analytics_catalogue.csv",
        "final_dashboard_catalogue.csv",
        "final_genai_catalogue.csv",
        "final_azure_reference_catalogue.csv",
        "final_validation_summary.json",
        "final_repository_health.json",
        "release_diagnostics.json",
        "release-manifest.json",
        "lineage-records.json",
    ]:
        assert (output_dir / name).is_file()


def test_release_catalogues_reference_existing_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=True)
    evidence = pd.read_csv(output_dir / "final_evidence_index.csv")
    assert not evidence["relative_path"].str.contains(".generated", regex=False).any()
    assert all((project_root() / path).exists() for path in evidence["relative_path"].head(50))
    reports = pd.read_csv(output_dir / "final_report_index.csv")
    assert all((project_root() / path).exists() for path in reports["relative_path"].head(20))
    architecture = pd.read_csv(output_dir / "final_architecture_index.csv")
    assert {"markdown", "mermaid", "iac_blueprint"} & set(architecture["item_type"])
    models = pd.read_csv(output_dir / "final_model_analytics_catalogue.csv")
    assert {"forecasting", "inventory", "quality", "maintenance", "genai", "dashboard"} <= set(
        models["domain"]
    )
    dashboard = pd.read_csv(output_dir / "final_dashboard_catalogue.csv")
    assert dashboard["relative_path"].str.contains("semantic_model.json").any()
    genai = pd.read_csv(output_dir / "final_genai_catalogue.csv")
    assert set(genai["external_model_called"]) == {False}
    azure = pd.read_csv(output_dir / "final_azure_reference_catalogue.csv")
    assert "deployed" not in set(azure["deployment_status"])


def test_release_manifest_and_lineage_hashes(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=True)
    manifest = json.loads((output_dir / "release-manifest.json").read_text())
    assert manifest["synthetic_data_only"] is True
    assert manifest["external_services_called"] is False
    assert manifest["cloud_deployment"] is False
    assert manifest["azure_deployment"] is False
    for evidence in manifest["output_files"].values():
        path = _resolve_generated_path(output_dir, evidence["path"])
        assert path.stat().st_size == evidence["file_size_bytes"]
        assert sha256_file(path) == evidence["sha256"]
        if path.suffix == ".csv":
            assert max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1) == evidence["row_count"]
    lineage = json.loads((output_dir / "lineage-records.json").read_text())
    assert lineage
    for record in lineage:
        target = _resolve_generated_path(output_dir, record["target_path"])
        assert sha256_file(target) == record["target_hash"]
        assert record["purview_registration"] is False


def test_release_existing_validation_and_tamper_detection(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=True)
    validate_existing_run(Path("configs/release.yaml"), output_directory=output_dir)
    catalogue = output_dir / "final_report_index.csv"
    catalogue.write_text(catalogue.read_text(encoding="utf-8") + "tampered\n")
    with pytest.raises(DataContractError):
        validate_existing_run(Path("configs/release.yaml"), output_directory=output_dir)


def test_release_manifest_tamper_detection(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=True)
    manifest_path = output_dir / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["cloud_deployment"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError):
        validate_existing_run(Path("configs/release.yaml"), output_directory=output_dir)


def test_release_overwrite_protection_preserves_unrelated_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    unrelated = output_dir / "keep.txt"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("keep", encoding="utf-8")
    with pytest.raises(PipelineExecutionError):
        run_release(Path("configs/release.yaml"), output_directory=output_dir, overwrite=False)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_release_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "release"
    env = os.environ.copy()
    env.pop("COV_CORE_SOURCE", None)
    env.pop("COV_CORE_CONFIG", None)
    env.pop("COV_CORE_DATAFILE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.release",
            "--config",
            str(project_root() / "configs" / "release.yaml"),
            "--output-directory",
            str(output_dir),
            "--overwrite",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Release REL-" in result.stdout
    validate_existing_run(project_root() / "configs" / "release.yaml", output_directory=output_dir)


def test_release_ci_execution_completes_quickly(tmp_path: Path) -> None:
    output_dir = tmp_path / "ci" / "release"
    result = run_release(
        Path("configs/release_ci.yaml"),
        output_directory=output_dir,
        overwrite=True,
    )
    assert result.catalogue_count == 8
    validate_existing_run(Path("configs/release_ci.yaml"), output_directory=output_dir)


def test_validate_all_target_includes_every_validator() -> None:
    makefile = (project_root() / "Makefile").read_text(encoding="utf-8")
    for target in [
        "validate-generation",
        "validate-ingestion",
        "validate-forecast",
        "validate-inventory",
        "validate-quality-analytics",
        "validate-maintenance",
        "validate-monitoring",
        "validate-genai",
        "validate-dashboard",
        "validate-architecture",
        "validate-release",
    ]:
        assert target in makefile


def _resolve_generated_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    repo_candidate = project_root() / path
    if repo_candidate.exists():
        return repo_candidate
    return output_dir.parent / path
