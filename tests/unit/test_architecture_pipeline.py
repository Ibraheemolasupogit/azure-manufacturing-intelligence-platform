from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from manufacturing_intelligence.architecture.config import load_architecture_config
from manufacturing_intelligence.architecture.existing_run import validate_existing_run
from manufacturing_intelligence.architecture.pipeline import run_architecture
from manufacturing_intelligence.architecture.validation import scan_forbidden_active_commands
from manufacturing_intelligence.common.exceptions import (
    ConfigurationError,
    DataContractError,
    PipelineExecutionError,
)
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root


def test_architecture_config_loads() -> None:
    config = load_architecture_config(Path("configs/azure_architecture.yaml"))
    assert config.architecture.deployment_mode == "reference_only"
    assert config.architecture.allow_live_deployment is False
    assert config.services.include_event_hubs is True


def test_invalid_live_deployment_mode_is_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.yaml"
    config_text = Path("configs/azure_architecture.yaml").read_text(encoding="utf-8")
    config_path.write_text(config_text.replace("reference_only", "live", 1), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_architecture_config(config_path)


def test_architecture_generation_outputs_required_artefacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    result = run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    assert result.service_mapping_count == 15
    assert result.security_control_count == 9
    assert result.adr_count == 11
    for name in [
        "azure_service_mapping.csv",
        "security_controls_matrix.csv",
        "data_architecture_layers.csv",
        "mlops_mapping.csv",
        "genai_architecture_mapping.csv",
        "operations_mapping.csv",
        "cost_considerations.csv",
        "architecture_decision_records.json",
        "architecture_validation_results.json",
        "architecture-manifest.json",
        "lineage-records.json",
    ]:
        assert (output_dir / name).is_file()
    for name in [
        "azure-reference-architecture.md",
        "deployment-boundary.md",
        "security-architecture.md",
        "data-architecture.md",
        "mlops-architecture.md",
        "genai-architecture.md",
        "operations-architecture.md",
        "cost-management.md",
    ]:
        assert (output_dir / "docs" / "architecture" / name).is_file()
    assert (output_dir / "diagrams" / "azure-reference-architecture.mmd").is_file()
    assert (infra_dir / "bicep" / "main.bicep").is_file()
    assert (infra_dir / "terraform" / "main.tf").is_file()


def test_architecture_tables_include_required_content(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    services = pd.read_csv(output_dir / "azure_service_mapping.csv")
    assert "Azure Event Hubs" in set(services["azure_service"])
    assert "Azure Data Lake Storage Gen2" in set(services["azure_service"])
    assert "Microsoft Entra ID" in set(services["azure_service"])
    assert set(services["deployment_status"]) <= {"reference_only", "planned"}
    security = pd.read_csv(output_dir / "security_controls_matrix.csv")
    assert {"identity boundary", "rbac", "key vault"} <= set(security["control_domain"])
    layers = pd.read_csv(output_dir / "data_architecture_layers.csv")
    assert {"raw", "accepted", "curated", "dashboard"} <= set(layers["layer_name"])
    mlops = pd.read_csv(output_dir / "mlops_mapping.csv")
    assert {"forecasting", "inventory", "quality", "maintenance"} <= set(mlops["ml_capability"])
    genai = pd.read_csv(output_dir / "genai_architecture_mapping.csv")
    assert genai["limitations"].str.contains("No", case=False).any()
    operations = pd.read_csv(output_dir / "operations_mapping.csv")
    assert operations["runbook_reference"].str.contains("runbooks").all()
    costs = pd.read_csv(output_dir / "cost_considerations.csv")
    assert {"ingestion", "storage", "analytics", "ml", "ai", "reporting", "monitoring"} <= set(
        costs["service_area"]
    )


def test_architecture_manifest_counts_hashes_and_flags(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    result = run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    manifest = json.loads((output_dir / "architecture-manifest.json").read_text())
    assert manifest["architecture_run_id"] == result.architecture_run_id
    assert manifest["deployment_mode"] == "reference_only"
    assert manifest["azure_deployment"] is False
    assert manifest["azure_credentials_required"] is False
    assert manifest["allow_terraform_apply"] is False
    assert manifest["allow_bicep_deployment"] is False
    for evidence in manifest["output_files"].values():
        path = _resolve_generated_path(output_dir, evidence["path"])
        assert path.stat().st_size == evidence["file_size_bytes"]
        assert sha256_file(path) == evidence["sha256"]
        if path.suffix == ".csv":
            assert max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1) == evidence["row_count"]


def test_architecture_lineage_hashes_are_valid(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    lineage = json.loads((output_dir / "lineage-records.json").read_text())
    assert lineage
    for record in lineage:
        target = _resolve_generated_path(output_dir, record["target_path"])
        assert sha256_file(target) == record["target_hash"]
        assert record["deployment_mode"] == "reference_only"
        assert record["purview_registration"] is False


def test_existing_run_validation_and_tamper_detection(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    validate_existing_run(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
    )
    service_mapping = output_dir / "azure_service_mapping.csv"
    service_mapping.write_text(
        service_mapping.read_text(encoding="utf-8") + "tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(DataContractError):
        validate_existing_run(
            Path("configs/azure_architecture.yaml"),
            output_directory=output_dir,
            infra_directory=infra_dir,
        )


def test_manifest_tamper_detection(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    run_architecture(
        Path("configs/azure_architecture.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    manifest_path = output_dir / "architecture-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["deployment_mode"] = "deployed"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError):
        validate_existing_run(
            Path("configs/azure_architecture.yaml"),
            output_directory=output_dir,
            infra_directory=infra_dir,
        )


def test_overwrite_protection_preserves_unrelated_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    unrelated = output_dir / "keep.txt"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("keep", encoding="utf-8")
    with pytest.raises(PipelineExecutionError):
        run_architecture(
            Path("configs/azure_architecture.yaml"),
            output_directory=output_dir,
            infra_directory=infra_dir,
            overwrite=False,
        )
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_forbidden_live_deployment_commands_are_not_active() -> None:
    assert scan_forbidden_active_commands(project_root()) == []


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "architecture"
    infra_dir = tmp_path / "infra"
    env = os.environ.copy()
    env.pop("COV_CORE_SOURCE", None)
    env.pop("COV_CORE_CONFIG", None)
    env.pop("COV_CORE_DATAFILE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.architecture",
            "--config",
            str(project_root() / "configs" / "azure_architecture.yaml"),
            "--output-directory",
            str(output_dir),
            "--infra-directory",
            str(infra_dir),
            "--overwrite",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Architecture ARCH-" in result.stdout
    validate_existing_run(
        project_root() / "configs" / "azure_architecture.yaml",
        output_directory=output_dir,
        infra_directory=infra_dir,
    )


def test_ci_architecture_execution_completes_quickly(tmp_path: Path) -> None:
    output_dir = tmp_path / "ci" / "architecture"
    infra_dir = output_dir / "infra"
    result = run_architecture(
        Path("configs/azure_architecture_ci.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
        overwrite=True,
    )
    assert result.service_mapping_count == 15
    validate_existing_run(
        Path("configs/azure_architecture_ci.yaml"),
        output_directory=output_dir,
        infra_directory=infra_dir,
    )


def _resolve_generated_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    repo_candidate = project_root() / path
    if repo_candidate.exists():
        return repo_candidate
    return output_dir.parent / path
