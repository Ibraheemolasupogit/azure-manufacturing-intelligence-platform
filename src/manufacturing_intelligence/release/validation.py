"""Validation-only checks for final release artefacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

REQUIRED_OUTPUTS = {
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
}

REQUIRED_REPORTS = {
    "final_portfolio_summary.md",
    "final_evidence_register.md",
    "final_validation_report.md",
    "final_release_readiness_report.md",
    "interview_talking_points.md",
    "cv_project_summary.md",
    "recruiter_readme_summary.md",
}

REQUIRED_DOCS = {
    "release/final-release-notes.md",
    "release/repository-evidence-map.md",
    "release/local-first-boundary.md",
    "release/synthetic-data-boundary.md",
    "release/validation-and-quality-gates.md",
    "release/interview-guide.md",
    "release/limitations.md",
    "milestones/milestone-12.md",
}


def validate_release_outputs(output_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest.get("output_files")
    if not isinstance(outputs, dict):
        raise DataContractError("RELEASE_OUTPUTS_INVALID")
    output_paths = {item["path"] for item in outputs.values() if isinstance(item, dict)}
    for name in REQUIRED_OUTPUTS:
        expected = _relative_or_output_parent(output_dir / name, output_dir)
        if expected not in output_paths:
            raise DataContractError(f"RELEASE_OUTPUT_MISSING_FROM_MANIFEST: {name}")
    for evidence in outputs.values():
        _verify_evidence(output_dir, evidence)
    _validate_catalogues(output_dir)
    _validate_lineage(output_dir, outputs)
    _validate_flags(manifest)
    if _secret_findings():
        raise DataContractError("RELEASE_SECRET_FINDINGS")
    if _forbidden_ci_findings():
        raise DataContractError("RELEASE_FORBIDDEN_CI_COMMANDS")
    return {
        "validation_status": "success",
        "catalogue_reference_status": "success",
        "lineage_status": "success",
        "secret_findings": [],
        "forbidden_command_findings": [],
    }


def _validate_catalogues(output_dir: Path) -> None:
    evidence = pd.read_csv(output_dir / "final_evidence_index.csv")
    if evidence.empty:
        raise DataContractError("RELEASE_EVIDENCE_INDEX_EMPTY")
    if evidence["relative_path"].str.contains(".generated", regex=False).any():
        raise DataContractError("RELEASE_EVIDENCE_INDEX_INCLUDES_GENERATED")
    for path_value in evidence["relative_path"].head(50):
        if not resolve_project_path(str(path_value)).exists():
            raise DataContractError(f"RELEASE_EVIDENCE_REFERENCE_MISSING: {path_value}")
    reports = pd.read_csv(output_dir / "final_report_index.csv")
    if reports.empty:
        raise DataContractError("RELEASE_REPORT_INDEX_EMPTY")
    architecture = pd.read_csv(output_dir / "final_architecture_index.csv")
    if not {"markdown", "mermaid", "iac_blueprint"} & set(architecture["item_type"]):
        raise DataContractError("RELEASE_ARCHITECTURE_INDEX_INCOMPLETE")
    models = pd.read_csv(output_dir / "final_model_analytics_catalogue.csv")
    required = {"forecasting", "inventory", "quality", "maintenance", "genai", "dashboard"}
    if not required <= set(models["domain"]):
        raise DataContractError("RELEASE_MODEL_CATALOGUE_INCOMPLETE")
    genai = pd.read_csv(output_dir / "final_genai_catalogue.csv")
    external_values = set(genai["external_model_called"])
    if external_values != {False} and external_values != {"false"}:
        raise DataContractError("RELEASE_GENAI_EXTERNAL_FLAG_INVALID")
    azure = pd.read_csv(output_dir / "final_azure_reference_catalogue.csv")
    if "deployed" in set(azure["deployment_status"]):
        raise DataContractError("RELEASE_AZURE_DEPLOYMENT_STATUS_INVALID")


def _validate_lineage(output_dir: Path, outputs: dict[str, Any]) -> None:
    lineage_path = output_dir / "lineage-records.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or not lineage:
        raise DataContractError("RELEASE_LINEAGE_INVALID")
    targets = {item["path"] for item in outputs.values()}
    lineage_targets = {item["target_path"] for item in lineage}
    if not targets <= lineage_targets:
        raise DataContractError("RELEASE_LINEAGE_TARGETS_MISSING")
    for record in lineage:
        target = _resolve_output_path(output_dir, record["target_path"])
        if sha256_file(target) != record["target_hash"]:
            raise DataContractError("RELEASE_LINEAGE_HASH_MISMATCH")


def _validate_flags(manifest: dict[str, Any]) -> None:
    if manifest.get("release_mode") != "portfolio_evidence":
        raise DataContractError("RELEASE_MODE_INVALID")
    for flag in [
        "synthetic_data_only",
    ]:
        if manifest.get(flag) is not True:
            raise DataContractError(f"RELEASE_FLAG_INVALID: {flag}")
    for flag in [
        "external_services_called",
        "cloud_deployment",
        "azure_deployment",
        "power_bi_deployment",
    ]:
        if manifest.get(flag) is not False:
            raise DataContractError(f"RELEASE_FLAG_INVALID: {flag}")


def _verify_evidence(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, evidence["path"])
    if not path.is_file():
        raise DataContractError(f"RELEASE_OUTPUT_MISSING: {evidence['path']}")
    if path.stat().st_size != int(evidence["file_size_bytes"]):
        raise DataContractError(f"RELEASE_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if sha256_file(path) != evidence["sha256"]:
        raise DataContractError(f"RELEASE_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if rows != int(evidence["row_count"]):
            raise DataContractError(f"RELEASE_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


def _resolve_output_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise DataContractError("RELEASE_ABSOLUTE_OUTPUT_PATH")
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


def _secret_findings() -> list[str]:
    findings = []
    pattern = re.compile(r"(?i)(client_secret|password|access_key)\s*[:=]\s*['\"][^'\"]{8,}")
    for path in [project_root() / ".github" / "workflows" / "ci.yml"]:
        if path.is_file() and pattern.search(path.read_text(encoding="utf-8")):
            findings.append(str(path))
    return findings


def _forbidden_ci_findings() -> list[str]:
    forbidden = ["az deployment group create", "terraform apply", "az login"]
    path = project_root() / ".github" / "workflows" / "ci.yml"
    if not path.is_file():
        return []
    findings = []
    for line in path.read_text(encoding="utf-8").splitlines():
        lowered = line.lower()
        if any(item in lowered for item in forbidden):
            findings.append(line)
    return findings
