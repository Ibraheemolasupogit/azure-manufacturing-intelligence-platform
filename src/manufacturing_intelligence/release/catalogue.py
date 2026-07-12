"""Final release catalogue builders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.forecasting.data import relative_path

SYNTHETIC_FLAG = "synthetic_portfolio_sample"
DEPLOYMENT_STATUS = "local_reference_only"

EVIDENCE_ROOTS = ["data", "outputs", "reports", "docs", "diagrams", "infra", "dashboard"]
EXCLUDED_PARTS = {".generated", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}


def build_all_catalogues() -> dict[str, pd.DataFrame]:
    evidence = evidence_rows()
    return {
        "final_evidence_index": pd.DataFrame(evidence),
        "final_report_index": pd.DataFrame(report_rows()),
        "final_architecture_index": pd.DataFrame(architecture_rows()),
        "final_data_catalogue": pd.DataFrame(data_rows()),
        "final_model_analytics_catalogue": pd.DataFrame(model_rows()),
        "final_dashboard_catalogue": pd.DataFrame(dashboard_rows()),
        "final_genai_catalogue": pd.DataFrame(genai_rows()),
        "final_azure_reference_catalogue": pd.DataFrame(azure_rows()),
    }


def evidence_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(_tracked_like_files(), 1):
        rel = relative_path(path)
        rows.append(
            {
                "evidence_id": f"EVID-{index:04d}",
                "milestone": _milestone_for_path(rel),
                "domain": _domain_for_path(rel),
                "artefact_type": _artefact_type(path),
                "relative_path": rel,
                "title": _title(path),
                "description": f"Tracked portfolio evidence for {_domain_for_path(rel)}.",
                "row_count": _row_count(path),
                "file_size": path.stat().st_size,
                "sha256": sha256_file(path),
                "source_manifest": _source_manifest(rel),
                "source_lineage": _source_lineage(rel),
                "validation_target": _validation_target(rel),
                "portfolio_relevance": "Demonstrates completed local-first milestone evidence.",
                "interview_relevance": "Use as concrete proof of reproducible implementation.",
                "synthetic_data_flag": SYNTHETIC_FLAG,
                "deployment_status": DEPLOYMENT_STATUS,
            }
        )
    return rows


def report_rows() -> list[dict[str, str]]:
    rows = []
    for index, path in enumerate(sorted((project_root() / "reports").glob("*.md")), 1):
        rel = relative_path(path)
        rows.append(
            {
                "report_id": f"RPT-{index:03d}",
                "title": _title(path),
                "relative_path": rel,
                "domain": _domain_for_path(rel),
                "milestone": _milestone_for_path(rel),
                "audience": "technical and portfolio reviewers",
                "purpose": "Summarise generated evidence and limitations.",
                "key_topics": _domain_for_path(rel),
                "source_outputs": _source_manifest(rel),
                "synthetic_data_flag": SYNTHETIC_FLAG,
                "limitations": "Local synthetic evidence only.",
            }
        )
    return rows


def architecture_rows() -> list[dict[str, str]]:
    paths = [
        *sorted((project_root() / "docs" / "architecture").glob("*.md")),
        *sorted((project_root() / "diagrams").glob("*.mmd")),
        *sorted((project_root() / "infra").glob("**/*")),
    ]
    rows = []
    for index, path in enumerate([item for item in paths if item.is_file()], 1):
        rel = relative_path(path)
        rows.append(
            {
                "architecture_item_id": f"ARCHITEM-{index:03d}",
                "relative_path": rel,
                "item_type": _artefact_type(path),
                "domain": _domain_for_path(rel),
                "purpose": (
                    "Reference architecture, boundary, policy, runbook, or blueprint evidence."
                ),
                "azure_reference_services": _azure_services_for_path(rel),
                "security_or_governance_relevance": (
                    "Documents reference-only controls and lineage."
                ),
                "deployment_status": "reference_only",
                "limitations": "No Azure resources were deployed.",
            }
        )
    return rows


def data_rows() -> list[dict[str, Any]]:
    rows = []
    data_paths = [
        *sorted((project_root() / "data").glob("**/*")),
        *sorted((project_root() / "outputs").glob("**/*")),
    ]
    files = [path for path in data_paths if path.is_file() and _include_file(path)]
    for index, path in enumerate(files, 1):
        rel = relative_path(path)
        rows.append(
            {
                "dataset_id": f"DATA-{index:04d}",
                "dataset_name": path.stem,
                "relative_path": rel,
                "data_zone": _data_zone(rel),
                "format": path.suffix.lstrip(".") or "text",
                "row_count": _row_count(path),
                "grain": _grain_for_path(rel),
                "key_fields": _key_fields_for_path(rel),
                "domain": _domain_for_path(rel),
                "validation_status": "validated",
                "source_manifest": _source_manifest(rel),
                "synthetic_data_flag": SYNTHETIC_FLAG,
                "limitations": "Synthetic local portfolio evidence.",
            }
        )
    return rows


def model_rows() -> list[dict[str, str]]:
    return [
        _model("AN-001", "Demand forecasting", "forecasting", "baseline model", "forecasting"),
        _model("AN-002", "Inventory scoring", "inventory", "rules and policy", "inventory"),
        _model("AN-003", "Quality anomaly detection", "quality", "SPC and anomalies", "quality"),
        _model("AN-004", "Maintenance risk scoring", "maintenance", "risk scoring", "maintenance"),
        _model("AN-005", "Monitoring health scoring", "monitoring", "health scoring", "monitoring"),
        _model(
            "AN-006",
            "Deterministic GenAI assistant",
            "genai",
            "retrieval and synthesis",
            "genai",
        ),
        _model("AN-007", "Dashboard semantic model", "dashboard", "semantic metadata", "dashboard"),
        _model(
            "AN-008",
            "Architecture static validation",
            "architecture",
            "static validation",
            "architecture",
        ),
    ]


def dashboard_rows() -> list[dict[str, str]]:
    paths = sorted((project_root() / "outputs" / "dashboard").glob("*")) + sorted(
        (project_root() / "dashboard").glob("*.md")
    )
    rows = []
    for index, path in enumerate([item for item in paths if item.is_file()], 1):
        rel = relative_path(path)
        rows.append(
            {
                "dashboard_item_id": f"DASH-{index:03d}",
                "item_type": _artefact_type(path),
                "relative_path": rel,
                "dashboard_page": "multiple" if "page" in path.stem else "semantic model",
                "source_tables": "outputs/dashboard/",
                "metrics": "metric_catalogue.csv",
                "visual_type": "metadata" if path.suffix == ".json" else "table",
                "Power_BI_ready_status": "import_ready_local_file",
                "deployment_status": DEPLOYMENT_STATUS,
                "limitations": "No .pbix or Power BI workspace.",
            }
        )
    return rows


def genai_rows() -> list[dict[str, str]]:
    paths = sorted((project_root() / "outputs" / "genai").glob("*")) + sorted(
        (project_root() / "reports").glob("*genai*.md")
    )
    rows = []
    for index, path in enumerate([item for item in paths if item.is_file()], 1):
        rows.append(
            {
                "genai_item_id": f"GENAI-{index:03d}",
                "item_type": _artefact_type(path),
                "relative_path": relative_path(path),
                "capability": "grounded deterministic assistant evidence",
                "evidence_grounding": "governed local evidence catalogue",
                "guardrail_relevance": "guardrails and refusal paths documented",
                "evaluation_relevance": "assistant evaluation outputs available",
                "external_model_called": "false",
                "deployment_status": DEPLOYMENT_STATUS,
                "limitations": "No OpenAI or Azure OpenAI call.",
            }
        )
    return rows


def azure_rows() -> list[dict[str, str]]:
    paths = [
        *sorted((project_root() / "outputs" / "architecture").glob("*")),
        *sorted((project_root() / "infra").glob("**/*")),
        *sorted((project_root() / "diagrams").glob("azure-*.mmd")),
    ]
    rows = []
    for index, path in enumerate([item for item in paths if item.is_file()], 1):
        rel = relative_path(path)
        rows.append(
            {
                "azure_item_id": f"AZREF-{index:03d}",
                "item_type": _artefact_type(path),
                "relative_path": rel,
                "azure_service": _azure_services_for_path(rel),
                "platform_capability": _domain_for_path(rel),
                "reference_layer": "reference architecture",
                "security_relevance": "documents least-privilege and no-secret boundaries",
                "governance_relevance": "maps lineage, evidence, and catalogue responsibilities",
                "deployment_status": "reference_only",
                "limitations": "Blueprint only; not deployed.",
            }
        )
    return rows


def _tracked_like_files() -> list[Path]:
    files: list[Path] = []
    for root_name in EVIDENCE_ROOTS:
        root = project_root() / root_name
        if root.exists():
            files.extend(
                path for path in root.glob("**/*") if path.is_file() and _include_file(path)
            )
    return sorted(set(files))


def _include_file(path: Path) -> bool:
    rel_parts = set(path.relative_to(project_root()).parts)
    if rel_parts & EXCLUDED_PARTS:
        return False
    if path.suffix in {".pyc", ".tmp"}:
        return False
    return "outputs/release" not in relative_path(path)


def _row_count(path: Path) -> int | None:
    if path.suffix == ".csv":
        return max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    if path.suffix == ".jsonl":
        return sum(1 for _ in path.open(encoding="utf-8"))
    return None


def _milestone_for_path(path: str) -> str:
    mapping = [
        ("outputs/architecture", "Milestone 11"),
        ("infra/", "Milestone 11"),
        ("outputs/dashboard", "Milestone 10"),
        ("outputs/genai", "Milestone 9"),
        ("outputs/monitoring", "Milestone 8"),
        ("outputs/maintenance", "Milestone 7"),
        ("outputs/quality", "Milestone 6"),
        ("outputs/inventory", "Milestone 5"),
        ("outputs/forecasting", "Milestone 4"),
        ("data/interim", "Milestone 3"),
        ("data/raw", "Milestone 2"),
        ("docs/milestones/milestone-1", "Milestone 1"),
    ]
    for prefix, milestone in mapping:
        if path.startswith(prefix):
            return milestone
    if "milestone-" in path:
        return "Milestone documentation"
    return "Cross-milestone"


def _domain_for_path(path: str) -> str:
    for domain in [
        "architecture",
        "dashboard",
        "genai",
        "monitoring",
        "maintenance",
        "quality",
        "inventory",
        "forecasting",
        "ingestion",
        "release",
    ]:
        if domain in path:
            return domain
    if "data/raw" in path:
        return "data_generation"
    return "portfolio"


def _artefact_type(path: Path) -> str:
    if path.suffix == ".csv":
        return "csv"
    if path.suffix in {".json", ".jsonl"}:
        return "json"
    if path.suffix == ".md":
        return "markdown"
    if path.suffix == ".mmd":
        return "mermaid"
    if path.suffix in {".bicep", ".tf"}:
        return "iac_blueprint"
    return path.suffix.lstrip(".") or "file"


def _title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def _source_manifest(path: str) -> str:
    domain = _domain_for_path(path)
    candidates = {
        "forecasting": "outputs/forecasting/forecast-manifest.json",
        "inventory": "outputs/inventory/inventory-manifest.json",
        "quality": "outputs/quality/quality-manifest.json",
        "maintenance": "outputs/maintenance/maintenance-manifest.json",
        "monitoring": "outputs/monitoring/monitoring-manifest.json",
        "genai": "outputs/genai/genai-manifest.json",
        "dashboard": "outputs/dashboard/dashboard-manifest.json",
        "architecture": "outputs/architecture/architecture-manifest.json",
        "ingestion": "data/interim/_metadata/ingestion-manifest.json",
    }
    return candidates.get(domain, "data/raw/generation_manifest.json")


def _source_lineage(path: str) -> str:
    manifest = _source_manifest(path)
    if "data/raw" in manifest:
        return "data/raw/generation_manifest.json"
    return str(Path(manifest).with_name("lineage-records.json"))


def _validation_target(path: str) -> str:
    domain = _domain_for_path(path)
    return {
        "forecasting": "make validate-forecast",
        "inventory": "make validate-inventory",
        "quality": "make validate-quality-analytics",
        "maintenance": "make validate-maintenance",
        "monitoring": "make validate-monitoring",
        "genai": "make validate-genai",
        "dashboard": "make validate-dashboard",
        "architecture": "make validate-architecture",
        "ingestion": "make validate-ingestion",
    }.get(domain, "make quality")


def _data_zone(path: str) -> str:
    if path.startswith("data/raw"):
        return "raw"
    if path.startswith("data/interim/accepted"):
        return "accepted"
    if path.startswith("data/interim/quarantine"):
        return "quarantine"
    if path.startswith("outputs/dashboard"):
        return "dashboard"
    if path.startswith("outputs"):
        return "curated_output"
    return "documentation"


def _grain_for_path(path: str) -> str:
    if path.endswith(".csv") or path.endswith(".jsonl"):
        return "one row per record in file"
    return "document"


def _key_fields_for_path(path: str) -> str:
    if "dashboard" in path:
        return "dashboard metadata keys"
    if "data/raw" in path or "data/interim" in path:
        return "domain primary identifiers"
    return "relative_path"


def _model(
    analytics_id: str,
    name: str,
    domain: str,
    method: str,
    output_domain: str,
) -> dict[str, str]:
    return {
        "analytics_id": analytics_id,
        "analytics_name": name,
        "domain": domain,
        "method_type": method,
        "local_module": f"manufacturing_intelligence.{output_domain}",
        "input_evidence": _source_manifest(output_domain),
        "output_evidence": f"outputs/{output_domain}/",
        "evaluation_or_validation_method": _validation_target(output_domain),
        "key_metrics": "See manifest, diagnostics, and reports.",
        "limitations": "Local deterministic portfolio evidence only.",
        "deployment_status": DEPLOYMENT_STATUS,
        "interview_relevance": "Explains the implemented analytical capability and validation.",
    }


def _azure_services_for_path(path: str) -> str:
    if "genai" in path:
        return "Azure AI Foundry, Azure OpenAI, Azure AI Search"
    if "dashboard" in path:
        return "Power BI, Microsoft Fabric"
    if "security" in path or "key" in path or "rbac" in path:
        return "Microsoft Entra ID, Azure Key Vault"
    if "monitor" in path:
        return "Azure Monitor, Log Analytics"
    if "mlops" in path or "machine" in path:
        return "Azure Machine Learning"
    if "data" in path or "storage" in path:
        return "Azure Data Lake Storage Gen2, Microsoft Purview"
    return "Azure reference architecture services"


def health_summary() -> dict[str, Any]:
    root = project_root()
    return {
        "milestone_completion_status": "Milestones 1-12 complete",
        "package_count": len(
            [
                path
                for path in (root / "src" / "manufacturing_intelligence").iterdir()
                if path.is_dir()
            ]
        ),
        "test_count": len(list((root / "tests").glob("**/test_*.py"))),
        "source_file_count": len(list((root / "src").glob("**/*.py"))),
        "documentation_count": len(list((root / "docs").glob("**/*.md"))),
        "report_count": len(list((root / "reports").glob("*.md"))),
        "output_artefact_count": len(list((root / "outputs").glob("**/*"))),
        "manifest_count": len(list(root.glob("**/*manifest*.json"))),
        "lineage_count": len(list(root.glob("**/lineage-records.json"))),
        "diagram_count": len(list((root / "diagrams").glob("*.mmd"))),
        "infra_blueprint_count": len(
            [path for path in (root / "infra").glob("**/*") if path.is_file()]
        ),
        "ci_workflow_status": "static local validation only",
        "make_target_coverage": (
            "quality, generation, ingestion, analytics, dashboard, architecture, release"
        ),
        "known_limitations": (
            "No live Azure, Power BI, Fabric, OpenAI, or external service deployment."
        ),
        "release_readiness_label": "portfolio_release_ready",
    }


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
