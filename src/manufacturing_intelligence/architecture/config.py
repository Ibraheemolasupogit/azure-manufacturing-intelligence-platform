"""Configuration loading for Azure reference architecture artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class ArchitectureSettings:
    output_directory: Path
    report_directory: Path
    docs_directory: Path
    diagrams_directory: Path
    infra_directory: Path
    overwrite: bool
    random_seed: int
    deployment_mode: str
    allow_live_deployment: bool
    allow_azure_cli: bool
    allow_terraform_apply: bool
    allow_bicep_deployment: bool
    architecture_name: str
    environment: str


@dataclass(frozen=True)
class ArchitectureInputs:
    ingestion_manifest_path: Path
    ingestion_lineage_path: Path
    forecast_manifest_path: Path
    forecast_lineage_path: Path
    inventory_manifest_path: Path
    inventory_lineage_path: Path
    quality_manifest_path: Path
    quality_lineage_path: Path
    maintenance_manifest_path: Path
    maintenance_lineage_path: Path
    monitoring_manifest_path: Path
    monitoring_lineage_path: Path
    genai_manifest_path: Path
    genai_lineage_path: Path
    dashboard_manifest_path: Path
    dashboard_lineage_path: Path


@dataclass(frozen=True)
class ArchitectureServices:
    include_event_hubs: bool
    include_data_lake: bool
    include_stream_analytics: bool
    include_data_explorer: bool
    include_synapse_or_fabric: bool
    include_machine_learning: bool
    include_ai_foundry: bool
    include_ai_search: bool
    include_azure_openai: bool
    include_monitor: bool
    include_log_analytics: bool
    include_application_insights: bool
    include_purview: bool
    include_power_bi: bool
    include_key_vault: bool
    include_entra_id: bool
    include_container_apps: bool


@dataclass(frozen=True)
class ArchitectureGovernance:
    require_private_networking_notes: bool
    require_identity_notes: bool
    require_rbac_notes: bool
    require_key_vault_notes: bool
    require_purview_lineage_notes: bool
    require_cost_management_notes: bool
    require_no_deployment_disclaimer: bool


@dataclass(frozen=True)
class ArchitectureValidationSettings:
    forbid_live_deployment_commands: bool
    forbid_secret_values: bool
    require_parameter_templates: bool
    require_architecture_diagrams: bool
    require_service_mapping: bool
    require_security_controls: bool
    require_lineage_mapping: bool
    require_operational_runbooks: bool


@dataclass(frozen=True)
class ArchitectureConfig:
    config_path: Path
    architecture: ArchitectureSettings
    inputs: ArchitectureInputs
    services: ArchitectureServices
    governance: ArchitectureGovernance
    validation: ArchitectureValidationSettings


def load_architecture_config(config_path: Path | None = None) -> ArchitectureConfig:
    path = (
        resolve_project_path(config_path)
        if config_path
        else project_root() / "configs" / "azure_architecture.yaml"
    )
    if not path.is_file():
        raise ConfigurationError(f"Architecture config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Architecture config must contain a mapping")
    architecture = _section(payload, "azure_architecture")
    inputs = _section(payload, "inputs")
    services = _section(payload, "services")
    governance = _section(payload, "governance")
    validation = _section(payload, "validation")
    settings = ArchitectureSettings(
        output_directory=_safe_output_path(_required_str(architecture, "output_directory")),
        report_directory=resolve_project_path(_required_str(architecture, "report_directory")),
        docs_directory=resolve_project_path(_required_str(architecture, "docs_directory")),
        diagrams_directory=resolve_project_path(_required_str(architecture, "diagrams_directory")),
        infra_directory=resolve_project_path(_required_str(architecture, "infra_directory")),
        overwrite=_required_bool(architecture, "overwrite"),
        random_seed=_positive_int(architecture, "random_seed"),
        deployment_mode=_required_str(architecture, "deployment_mode"),
        allow_live_deployment=_required_bool(architecture, "allow_live_deployment"),
        allow_azure_cli=_required_bool(architecture, "allow_azure_cli"),
        allow_terraform_apply=_required_bool(architecture, "allow_terraform_apply"),
        allow_bicep_deployment=_required_bool(architecture, "allow_bicep_deployment"),
        architecture_name=_required_str(architecture, "architecture_name"),
        environment=_required_str(architecture, "environment"),
    )
    _validate_reference_only(settings)
    input_paths = {
        field: resolve_project_path(_required_str(inputs, field))
        for field in ArchitectureInputs.__dataclass_fields__
    }
    for field, input_path in input_paths.items():
        if _is_relative_to(input_path, settings.output_directory):
            raise ConfigurationError(f"Architecture output overlaps input: {field}")
        if _looks_like_secret_value(str(input_path)):
            raise ConfigurationError(f"Secret-looking input path rejected: {field}")
    return ArchitectureConfig(
        config_path=path.resolve(),
        architecture=settings,
        inputs=ArchitectureInputs(**input_paths),
        services=ArchitectureServices(
            **{
                field: _required_bool(services, field)
                for field in ArchitectureServices.__dataclass_fields__
            }
        ),
        governance=ArchitectureGovernance(
            **{
                field: _required_bool(governance, field)
                for field in ArchitectureGovernance.__dataclass_fields__
            }
        ),
        validation=ArchitectureValidationSettings(
            **{
                field: _required_bool(validation, field)
                for field in ArchitectureValidationSettings.__dataclass_fields__
            }
        ),
    )


def semantic_config_payload(config: ArchitectureConfig) -> dict[str, Any]:
    return {
        "architecture": {
            "random_seed": config.architecture.random_seed,
            "deployment_mode": config.architecture.deployment_mode,
            "allow_live_deployment": config.architecture.allow_live_deployment,
            "allow_azure_cli": config.architecture.allow_azure_cli,
            "allow_terraform_apply": config.architecture.allow_terraform_apply,
            "allow_bicep_deployment": config.architecture.allow_bicep_deployment,
            "architecture_name": config.architecture.architecture_name,
            "environment": config.architecture.environment,
        },
        "services": {
            field: getattr(config.services, field)
            for field in ArchitectureServices.__dataclass_fields__
        },
        "governance": {
            field: getattr(config.governance, field)
            for field in ArchitectureGovernance.__dataclass_fields__
        },
        "validation": {
            field: getattr(config.validation, field)
            for field in ArchitectureValidationSettings.__dataclass_fields__
        },
    }


def stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value


def _validate_reference_only(settings: ArchitectureSettings) -> None:
    if settings.deployment_mode != "reference_only":
        raise ConfigurationError("Architecture deployment_mode must be reference_only")
    if settings.allow_live_deployment:
        raise ConfigurationError("Live deployment must remain disabled")
    if settings.allow_azure_cli:
        raise ConfigurationError("Azure CLI execution must remain disabled")
    if settings.allow_terraform_apply:
        raise ConfigurationError("Terraform apply must remain disabled")
    if settings.allow_bicep_deployment:
        raise ConfigurationError("Bicep deployment must remain disabled")


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Architecture config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    if _looks_like_secret_value(value):
        raise ConfigurationError(f"Secret-looking value rejected: {key}")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean missing: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Required positive integer missing: {key}")
    return value


def _safe_output_path(value: str) -> Path:
    path = resolve_project_path(value)
    if path.name in {"raw", "accepted", "interim", "forecasting", "inventory", "quality"}:
        raise ConfigurationError("Architecture output path overlaps governed evidence")
    if "data" in path.parts and ".generated" not in path.parts:
        raise ConfigurationError("Architecture outputs must not be written under data/")
    return path


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _looks_like_secret_value(value: str) -> bool:
    lowered = value.lower()
    suspicious_keys = [
        "client_secret=",
        "password=",
        "access_key=",
        "tenant_id=",
        "subscription_id=",
    ]
    return any(item in lowered for item in suspicious_keys)
