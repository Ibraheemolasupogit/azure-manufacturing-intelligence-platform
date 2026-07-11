"""Static validation for Azure reference architecture artefacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.architecture import artefacts
from manufacturing_intelligence.architecture.config import ArchitectureConfig
from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

FORBIDDEN_PATTERNS = [
    "az deployment group create",
    "az deployment sub create",
    "terraform apply",
    "az group create",
    "az login",
    "az account set",
    "Power BI REST API",
    "Azure SDK deployment client",
]

SECRET_PATTERNS = [
    re.compile(r"(?i)(client_secret|password|access_key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
]

REQUIRED_SERVICES = {
    "Azure Event Hubs",
    "Azure Data Lake Storage Gen2",
    "Azure Stream Analytics",
    "Azure Data Explorer",
    "Azure Synapse Analytics or Microsoft Fabric",
    "Azure Machine Learning",
    "Azure Machine Learning batch jobs",
    "Azure AI Foundry, Azure OpenAI Service, Azure AI Search",
    "Azure Monitor and Log Analytics",
    "Power BI and Microsoft Fabric semantic model",
    "Microsoft Purview",
    "Azure Key Vault",
    "Microsoft Entra ID",
}

REQUIRED_SECURITY_DOMAINS = {
    "identity boundary",
    "rbac",
    "key vault",
    "private networking",
    "data exfiltration",
    "logging and audit",
    "ci cd security",
    "supply chain",
    "synthetic data boundary",
}


def validate_static_artefacts(
    config: ArchitectureConfig,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _validate_config_flags(manifest)
    _validate_files(config, manifest)
    _validate_tables(config.architecture.output_directory)
    _validate_adrs(config.architecture.output_directory)
    findings = scan_forbidden_active_commands(project_root())
    secret_findings = scan_secret_like_values(config)
    if findings:
        raise DataContractError(f"ARCHITECTURE_FORBIDDEN_COMMANDS: {findings}")
    if secret_findings:
        raise DataContractError(f"ARCHITECTURE_SECRET_FINDINGS: {secret_findings}")
    return {
        **artefacts.validation_result_template(),
        "service_mapping_count": len(artefacts.SERVICE_MAPPING_ROWS),
        "security_control_count": len(artefacts.SECURITY_ROWS),
        "adr_count": len(artefacts.ADR_ROWS),
        "required_doc_count": len(artefacts.REQUIRED_DOCS),
        "required_diagram_count": len(artefacts.REQUIRED_DIAGRAMS),
        "required_infra_file_count": len(artefacts.REQUIRED_INFRA_FILES),
    }


def scan_forbidden_active_commands(base: Path) -> list[str]:
    findings: list[str] = []
    paths = [base / ".github" / "workflows" / "ci.yml"]
    for path in paths:
        if not path.is_file():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            if any(pattern.lower() in lowered for pattern in FORBIDDEN_PATTERNS) and (
                not _safe_non_executable_context(lowered)
            ):
                findings.append(f"{path}:{line_number}:{line.strip()}")
    return findings


def scan_secret_like_values(config: ArchitectureConfig) -> list[str]:
    findings: list[str] = []
    scan_paths = [
        config.config_path,
        *[config.architecture.infra_directory / path for path in artefacts.REQUIRED_INFRA_FILES],
        project_root() / ".github" / "workflows" / "ci.yml",
    ]
    for path in scan_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text) and "placeholder" not in text.lower():
                findings.append(str(path))
    return findings


def _validate_config_flags(manifest: dict[str, Any]) -> None:
    if manifest.get("deployment_mode") != "reference_only":
        raise DataContractError("ARCHITECTURE_DEPLOYMENT_MODE_INVALID")
    false_flags = [
        "allow_live_deployment",
        "allow_azure_cli",
        "allow_terraform_apply",
        "allow_bicep_deployment",
        "azure_deployment",
        "azure_credentials_required",
    ]
    for flag in false_flags:
        if manifest.get(flag) is not False:
            raise DataContractError(f"ARCHITECTURE_FLAG_INVALID: {flag}")


def _validate_files(config: ArchitectureConfig, manifest: dict[str, Any]) -> None:
    _require_file(config.architecture.output_directory / "architecture-manifest.json")
    _require_file(config.architecture.output_directory / "lineage-records.json")
    for doc in artefacts.REQUIRED_DOCS:
        _require_file(config.architecture.docs_directory / doc)
    for diagram in artefacts.REQUIRED_DIAGRAMS:
        _require_file(config.architecture.diagrams_directory / diagram)
    for infra in artefacts.REQUIRED_INFRA_FILES:
        _require_file(config.architecture.infra_directory / infra)
    outputs = manifest.get("output_files")
    if not isinstance(outputs, dict):
        raise DataContractError("ARCHITECTURE_OUTPUTS_INVALID")
    output_paths = {item["path"] for item in outputs.values() if isinstance(item, dict)}
    for name in artefacts.REQUIRED_OUTPUTS:
        expected_path = (config.architecture.output_directory / name).resolve()
        expected = _relative_or_output_parent(expected_path, config.architecture.output_directory)
        if expected not in output_paths:
            raise DataContractError(f"ARCHITECTURE_OUTPUT_MISSING_FROM_MANIFEST: {name}")
    for evidence in outputs.values():
        _verify_evidence(config.architecture.output_directory, evidence)
    _validate_lineage(config.architecture.output_directory, outputs)
    _validate_bicep_and_terraform_comments(config)


def _validate_tables(output_dir: Path) -> None:
    service_mapping = pd.read_csv(output_dir / "azure_service_mapping.csv")
    if not set(service_mapping["azure_service"]) >= REQUIRED_SERVICES:
        raise DataContractError("ARCHITECTURE_SERVICE_MAPPING_INCOMPLETE")
    allowed_status = {"reference_only", "planned"}
    if not set(service_mapping["deployment_status"]) <= allowed_status:
        raise DataContractError("ARCHITECTURE_SERVICE_DEPLOYMENT_STATUS_INVALID")
    security = pd.read_csv(output_dir / "security_controls_matrix.csv")
    if not set(security["control_domain"]) >= REQUIRED_SECURITY_DOMAINS:
        raise DataContractError("ARCHITECTURE_SECURITY_DOMAINS_INCOMPLETE")
    layers = pd.read_csv(output_dir / "data_architecture_layers.csv")
    if not {"raw", "accepted", "curated", "dashboard"} <= set(layers["layer_name"]):
        raise DataContractError("ARCHITECTURE_DATA_LAYERS_INCOMPLETE")
    mlops = pd.read_csv(output_dir / "mlops_mapping.csv")
    if not {"forecasting", "inventory", "quality", "maintenance"} <= set(mlops["ml_capability"]):
        raise DataContractError("ARCHITECTURE_MLOPS_INCOMPLETE")
    genai = pd.read_csv(output_dir / "genai_architecture_mapping.csv")
    if not genai["limitations"].str.contains("No", case=False).any():
        raise DataContractError("ARCHITECTURE_GENAI_BOUNDARY_MISSING")
    operations = pd.read_csv(output_dir / "operations_mapping.csv")
    if not operations["runbook_reference"].str.contains("runbooks").all():
        raise DataContractError("ARCHITECTURE_RUNBOOKS_MISSING")
    costs = pd.read_csv(output_dir / "cost_considerations.csv")
    required_costs = {"ingestion", "storage", "analytics", "ml", "ai", "reporting", "monitoring"}
    if not required_costs <= set(costs["service_area"]):
        raise DataContractError("ARCHITECTURE_COST_AREAS_INCOMPLETE")


def _validate_adrs(output_dir: Path) -> None:
    adrs = json.loads(
        (output_dir / "architecture_decision_records.json").read_text(encoding="utf-8")
    )
    if not isinstance(adrs, list):
        raise DataContractError("ARCHITECTURE_ADR_INVALID")
    titles = {item["title"] for item in adrs}
    required = {
        "Keep implementation local first",
        "Use synthetic data only",
        "Do not deploy during Milestone 11",
    }
    if not required <= titles:
        raise DataContractError("ARCHITECTURE_ADR_REQUIRED_DECISIONS_MISSING")


def _validate_lineage(output_dir: Path, outputs: dict[str, Any]) -> None:
    lineage = json.loads((output_dir / "lineage-records.json").read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("ARCHITECTURE_LINEAGE_INVALID")
    targets = {item["path"] for item in outputs.values()}
    lineage_targets = {item["target_path"] for item in lineage}
    if not targets <= lineage_targets:
        raise DataContractError("ARCHITECTURE_LINEAGE_TARGETS_MISSING")
    for record in lineage:
        target_path = _resolve_path(output_dir, record["target_path"])
        if sha256_file(target_path) != record["target_hash"]:
            raise DataContractError("ARCHITECTURE_LINEAGE_HASH_MISMATCH")


def _validate_bicep_and_terraform_comments(config: ArchitectureConfig) -> None:
    for path in config.architecture.infra_directory.glob("**/*.bicep"):
        text = path.read_text(encoding="utf-8").lower()
        if "reference-only" not in text or "do not deploy" not in text:
            raise DataContractError(f"ARCHITECTURE_BICEP_COMMENT_MISSING: {path}")
    for path in config.architecture.infra_directory.glob("terraform/*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8").lower()
            if path.suffix == ".tf" and "reference-only" not in text:
                raise DataContractError(f"ARCHITECTURE_TERRAFORM_COMMENT_MISSING: {path}")


def _verify_evidence(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_path(output_dir, evidence["path"])
    if not path.is_file():
        raise DataContractError(f"ARCHITECTURE_OUTPUT_MISSING: {evidence['path']}")
    if path.stat().st_size != int(evidence["file_size_bytes"]):
        raise DataContractError(f"ARCHITECTURE_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if sha256_file(path) != evidence["sha256"]:
        raise DataContractError(f"ARCHITECTURE_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if rows != int(evidence["row_count"]):
            raise DataContractError(f"ARCHITECTURE_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


def _resolve_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise DataContractError("ARCHITECTURE_ABSOLUTE_OUTPUT_PATH")
    candidate = resolve_project_path(path_value)
    if candidate.exists():
        return candidate
    return output_dir.parent / path


def _relative_or_output_parent(path: Path, output_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        return resolved.relative_to(output_dir.parent.resolve()).as_posix()


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise DataContractError(f"ARCHITECTURE_REQUIRED_FILE_MISSING: {path}")


def _safe_non_executable_context(line: str) -> bool:
    markers = ["do not", "not run", "reference-only", "forbidden", "must not"]
    return any(marker in line for marker in markers)
