"""Azure reference architecture output pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.architecture import artefacts
from manufacturing_intelligence.architecture.config import (
    ArchitectureConfig,
    ArchitectureSettings,
    load_architecture_config,
    stable_config_path,
)
from manufacturing_intelligence.architecture.data import (
    ArchitectureEvidence,
    load_architecture_evidence,
    verify_upstream_unchanged,
)
from manufacturing_intelligence.architecture.lineage import lineage_records
from manufacturing_intelligence.architecture.manifest import (
    architecture_run_id,
    git_commit,
    semantic_config_hash,
    specification_hash,
)
from manufacturing_intelligence.architecture.reporting import markdown_reports
from manufacturing_intelligence.architecture.serialization import (
    file_evidence,
    write_csv,
    write_json,
    write_text,
)
from manufacturing_intelligence.architecture.service_mapping import (
    architecture_spec_payload,
    build_tables,
)
from manufacturing_intelligence.architecture.validation import validate_static_artefacts
from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class ArchitectureResult:
    architecture_run_id: str
    output_directory: Path
    service_mapping_count: int
    security_control_count: int
    adr_count: int


def run_architecture(
    config_path: Path | None = None,
    *,
    output_directory: Path | None = None,
    infra_directory: Path | None = None,
    overwrite: bool = False,
) -> ArchitectureResult:
    config = with_overrides(
        load_architecture_config(config_path),
        output_directory=output_directory,
        infra_directory=infra_directory,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    evidence = load_architecture_evidence(config)
    spec_hash = specification_hash(architecture_spec_payload())
    run_id = architecture_run_id(config, evidence.input_hashes, spec_hash)
    tables = build_tables()
    for name, frame in tables.items():
        write_csv(config.architecture.output_directory / f"{name}.csv", frame)
    write_json(
        config.architecture.output_directory / "azure_service_mapping.json",
        artefacts.SERVICE_MAPPING_ROWS,
    )
    write_json(
        config.architecture.output_directory / "architecture_decision_records.json",
        artefacts.ADR_ROWS,
    )
    _write_docs(config)
    _write_diagrams(config)
    _write_infra(config)
    for report_name, content in markdown_reports(
        run_id,
        len(artefacts.SERVICE_MAPPING_ROWS),
        len(artefacts.SECURITY_ROWS),
        len(artefacts.ADR_ROWS),
    ).items():
        write_text(config.architecture.report_directory / report_name, content)
    write_json(
        config.architecture.output_directory / "architecture_validation_results.json",
        artefacts.validation_result_template(),
    )
    outputs = _output_evidence(config)
    manifest = _manifest(config, run_id, evidence, outputs, spec_hash)
    write_json(config.architecture.output_directory / "architecture-manifest.json", manifest)
    write_json(
        config.architecture.output_directory / "lineage-records.json",
        lineage_records(
            run_id=run_id,
            source_hashes=evidence.input_hashes,
            outputs=outputs,
            configuration_hash=semantic_config_hash(config),
        ),
    )
    validation_results = validate_static_artefacts(config, manifest)
    write_json(
        config.architecture.output_directory / "architecture_validation_results.json",
        validation_results,
    )
    outputs = _output_evidence(config)
    manifest = _manifest(config, run_id, evidence, outputs, spec_hash)
    manifest["validation_results"] = validation_results
    write_json(config.architecture.output_directory / "architecture-manifest.json", manifest)
    write_json(
        config.architecture.output_directory / "lineage-records.json",
        lineage_records(
            run_id=run_id,
            source_hashes=evidence.input_hashes,
            outputs=outputs,
            configuration_hash=semantic_config_hash(config),
        ),
    )
    verify_upstream_unchanged(config, evidence)
    return ArchitectureResult(
        architecture_run_id=run_id,
        output_directory=config.architecture.output_directory,
        service_mapping_count=len(artefacts.SERVICE_MAPPING_ROWS),
        security_control_count=len(artefacts.SECURITY_ROWS),
        adr_count=len(artefacts.ADR_ROWS),
    )


def with_overrides(
    config: ArchitectureConfig,
    *,
    output_directory: Path | None,
    infra_directory: Path | None,
    overwrite: bool,
) -> ArchitectureConfig:
    if output_directory is None and infra_directory is None and not overwrite:
        return config
    settings = config.architecture
    output_dir = output_directory.resolve() if output_directory else settings.output_directory
    infra_dir = infra_directory.resolve() if infra_directory else settings.infra_directory
    report_dir = output_dir / "reports" if output_directory else settings.report_directory
    docs_dir = output_dir / "docs" / "architecture" if output_directory else settings.docs_directory
    diagrams_dir = output_dir / "diagrams" if output_directory else settings.diagrams_directory
    return ArchitectureConfig(
        config_path=config.config_path,
        architecture=ArchitectureSettings(
            output_directory=output_dir,
            report_directory=report_dir,
            docs_directory=docs_dir,
            diagrams_directory=diagrams_dir,
            infra_directory=infra_dir,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            deployment_mode=settings.deployment_mode,
            allow_live_deployment=settings.allow_live_deployment,
            allow_azure_cli=settings.allow_azure_cli,
            allow_terraform_apply=settings.allow_terraform_apply,
            allow_bicep_deployment=settings.allow_bicep_deployment,
            architecture_name=settings.architecture_name,
            environment=settings.environment,
        ),
        inputs=config.inputs,
        services=config.services,
        governance=config.governance,
        validation=config.validation,
    )


def _write_docs(config: ArchitectureConfig) -> None:
    for name, content in artefacts.architecture_docs().items():
        write_text(config.architecture.docs_directory / name, content)


def _write_diagrams(config: ArchitectureConfig) -> None:
    for name, content in artefacts.diagrams().items():
        write_text(config.architecture.diagrams_directory / name, content)


def _write_infra(config: ArchitectureConfig) -> None:
    for name, content in artefacts.infra_files().items():
        write_text(config.architecture.infra_directory / name, content)


def _manifest(
    config: ArchitectureConfig,
    run_id: str,
    evidence: ArchitectureEvidence,
    outputs: dict[str, dict[str, Any]],
    spec_hash: str,
) -> dict[str, Any]:
    return {
        "architecture_run_id": run_id,
        "pipeline_name": "azure_reference_architecture",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "architecture_specification_sha256": spec_hash,
        "referenced_milestone_manifests": _input_manifests(config),
        "input_hashes": evidence.input_hashes,
        "source_row_counts": evidence.source_row_counts,
        "generated_docs": [
            relative_path(config.architecture.docs_directory / item)
            for item in artefacts.REQUIRED_DOCS
        ],
        "generated_diagrams": [
            relative_path(config.architecture.diagrams_directory / item)
            for item in artefacts.REQUIRED_DIAGRAMS
        ],
        "generated_infra_files": [
            relative_path(config.architecture.infra_directory / item)
            for item in artefacts.REQUIRED_INFRA_FILES
        ],
        "output_files": outputs,
        "service_mapping_count": len(artefacts.SERVICE_MAPPING_ROWS),
        "security_control_count": len(artefacts.SECURITY_ROWS),
        "adr_count": len(artefacts.ADR_ROWS),
        "validation_status": "success",
        "validation_results": artefacts.validation_result_template(),
        "deployment_mode": "reference_only",
        "allow_live_deployment": False,
        "allow_azure_cli": False,
        "allow_terraform_apply": False,
        "allow_bicep_deployment": False,
        "azure_deployment": False,
        "azure_credentials_required": False,
        "power_bi_deployment": False,
        "fabric_deployment": False,
        "terraform_apply_executed": False,
        "bicep_deployment_executed": False,
        "warnings": [],
        "synthetic_data_classification": artefacts.SYNTHETIC_CLASSIFICATION,
        "git_commit": git_commit(),
        "upstream_inputs_modified": False,
    }


def _input_manifests(config: ArchitectureConfig) -> dict[str, str]:
    return {
        "ingestion": relative_path(config.inputs.ingestion_manifest_path),
        "forecast": relative_path(config.inputs.forecast_manifest_path),
        "inventory": relative_path(config.inputs.inventory_manifest_path),
        "quality": relative_path(config.inputs.quality_manifest_path),
        "maintenance": relative_path(config.inputs.maintenance_manifest_path),
        "monitoring": relative_path(config.inputs.monitoring_manifest_path),
        "genai": relative_path(config.inputs.genai_manifest_path),
        "dashboard": relative_path(config.inputs.dashboard_manifest_path),
    }


def _output_evidence(config: ArchitectureConfig) -> dict[str, dict[str, Any]]:
    paths = [
        *(config.architecture.output_directory / item for item in artefacts.REQUIRED_OUTPUTS),
        *(config.architecture.docs_directory / item for item in artefacts.REQUIRED_DOCS),
        *(config.architecture.diagrams_directory / item for item in artefacts.REQUIRED_DIAGRAMS),
        *(config.architecture.infra_directory / item for item in artefacts.REQUIRED_INFRA_FILES),
        config.architecture.report_directory / "azure_architecture_report.md",
        config.architecture.report_directory / "deployment_boundary_report.md",
    ]
    outputs: dict[str, dict[str, Any]] = {}
    for path in sorted(paths):
        outputs[_evidence_key(path)] = file_evidence(
            path,
            base_directory=config.architecture.output_directory.parent,
        )
    return outputs


def _evidence_key(path: Path) -> str:
    return path.as_posix().replace("/", "_").replace(".", "_").replace("-", "_")


def _ensure_can_write(config: ArchitectureConfig) -> None:
    managed = [
        config.architecture.output_directory,
        *[config.architecture.docs_directory / item for item in artefacts.REQUIRED_DOCS],
        *[config.architecture.diagrams_directory / item for item in artefacts.REQUIRED_DIAGRAMS],
        config.architecture.infra_directory,
        config.architecture.report_directory / "azure_architecture_report.md",
        config.architecture.report_directory / "deployment_boundary_report.md",
    ]
    if config.architecture.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Architecture outputs already exist: {existing}")
