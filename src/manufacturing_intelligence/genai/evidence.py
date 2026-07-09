"""Governed local evidence catalogue for the deterministic assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.genai.config import GenAIConfig


@dataclass(frozen=True)
class EvidenceCatalogue:
    """Evidence catalogue and upstream hash metadata."""

    items: list[dict[str, Any]]
    input_hashes: dict[str, str]
    warnings: list[str]


def build_evidence_catalogue(config: GenAIConfig) -> EvidenceCatalogue:
    """Build a deterministic catalogue from governed local artefacts."""
    _verify_core_evidence(config)
    specs = _evidence_specs(config)
    items = []
    warnings = []
    for index, spec in enumerate(specs, start=1):
        path = spec["path"]
        if not path.is_file():
            if spec["required"]:
                raise DataContractError(f"GENAI_REQUIRED_EVIDENCE_MISSING: {relative_path(path)}")
            warnings.append(f"Optional evidence missing: {relative_path(path)}")
            continue
        items.append(_catalogue_item(index, spec))
    domains = {str(item["domain"]) for item in items}
    missing_domains = sorted(set(config.evidence.required_domains) - domains)
    if missing_domains:
        raise DataContractError(f"GENAI_REQUIRED_DOMAIN_EVIDENCE_MISSING: {missing_domains}")
    return EvidenceCatalogue(
        items=items,
        input_hashes={name: sha256_file(path) for name, path in _input_hash_paths(config).items()},
        warnings=warnings,
    )


def validate_catalogue_references(items: list[dict[str, Any]]) -> None:
    """Validate that catalogue evidence references existing files with matching hashes."""
    for item in items:
        path = resolve_project_path(str(item["relative_path"]))
        if not path.is_file():
            raise DataContractError(f"GENAI_CATALOGUE_REFERENCE_MISSING: {item['relative_path']}")
        if sha256_file(path) != item["sha256"]:
            raise DataContractError(f"GENAI_CATALOGUE_HASH_MISMATCH: {item['evidence_id']}")
        if (
            path.suffix == ".csv"
            and item.get("row_count") is not None
            and int(item["row_count"]) != _row_count(path)
        ):
            raise DataContractError(f"GENAI_CATALOGUE_ROW_COUNT_MISMATCH: {item['evidence_id']}")


def _verify_core_evidence(config: GenAIConfig) -> None:
    generation = _read_json(config.inputs.generation_manifest_path)
    ingestion = _read_json(config.inputs.ingestion_manifest_path)
    validation = _read_json(config.inputs.validation_summary_path)
    forecast = _read_json(config.inputs.forecast_manifest_path)
    inventory = _read_json(config.inputs.inventory_manifest_path)
    quality = _read_json(config.inputs.quality_manifest_path)
    maintenance = _read_json(config.inputs.maintenance_manifest_path)
    monitoring = _read_json(config.inputs.monitoring_manifest_path)
    manifests = [generation, ingestion, forecast, inventory, quality, maintenance, monitoring]
    if generation.get("synthetic_data_only") is not True:
        raise DataContractError("GENAI_GENERATION_NOT_SYNTHETIC")
    if validation.get("validation_status") != "success":
        raise DataContractError("GENAI_INGESTION_VALIDATION_NOT_SUCCESSFUL")
    for manifest in manifests[1:]:
        if manifest.get("validation_status") != "success":
            raise DataContractError("GENAI_UPSTREAM_MANIFEST_NOT_SUCCESSFUL")
        if manifest.get("synthetic_data_classification") != "synthetic_portfolio_sample":
            raise DataContractError("GENAI_UPSTREAM_SYNTHETIC_CLASSIFICATION_MISSING")
    _verify_manifest_hash(config.inputs.ingestion_manifest_path, monitoring, "ingestion_manifest")
    _verify_manifest_hash(config.inputs.forecast_manifest_path, monitoring, "forecast_manifest")
    _verify_manifest_hash(config.inputs.inventory_manifest_path, monitoring, "inventory_manifest")
    _verify_manifest_hash(config.inputs.quality_manifest_path, monitoring, "quality_manifest")
    _verify_manifest_hash(
        config.inputs.maintenance_manifest_path, monitoring, "maintenance_manifest"
    )
    for path in [
        config.inputs.ingestion_lineage_path,
        config.inputs.forecast_lineage_path,
        config.inputs.inventory_lineage_path,
        config.inputs.quality_lineage_path,
        config.inputs.maintenance_lineage_path,
        config.inputs.monitoring_lineage_path,
    ]:
        lineage = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(lineage, list) or not lineage:
            raise DataContractError(f"GENAI_LINEAGE_MISSING_OR_EMPTY: {relative_path(path)}")


def _verify_manifest_hash(path: Path, monitoring_manifest: dict[str, Any], key: str) -> None:
    expected = monitoring_manifest.get("input_hashes", {}).get(key)
    if expected and expected != sha256_file(path):
        raise DataContractError(f"GENAI_MONITORING_HASH_MISMATCH: {key}")


def _evidence_specs(config: GenAIConfig) -> list[dict[str, Any]]:
    i = config.inputs
    return [
        _spec(
            "generation", "manifest", i.generation_manifest_path, "Synthetic generation manifest"
        ),
        _spec("generation", "json_output", i.schema_metadata_path, "Synthetic schema metadata"),
        _spec("ingestion", "manifest", i.ingestion_manifest_path, "Governed ingestion manifest"),
        _spec("ingestion", "diagnostics", i.validation_summary_path, "Validation summary"),
        _spec("ingestion", "diagnostics", i.data_quality_report_path, "Data quality JSON report"),
        _spec("ingestion", "markdown_report", i.data_quality_markdown_path, "Data quality report"),
        _spec("ingestion", "lineage", i.ingestion_lineage_path, "Ingestion lineage records"),
        _spec("forecasting", "manifest", i.forecast_manifest_path, "Forecast manifest"),
        _spec("forecasting", "csv_output", i.demand_forecast_path, "Demand forecast output"),
        _spec(
            "forecasting", "markdown_report", i.forecast_report_path, "Demand forecasting report"
        ),
        _spec("forecasting", "lineage", i.forecast_lineage_path, "Forecast lineage records"),
        _spec("inventory", "manifest", i.inventory_manifest_path, "Inventory manifest"),
        _spec("inventory", "csv_output", i.inventory_scores_path, "Inventory risk scores"),
        _spec(
            "inventory", "markdown_report", i.inventory_report_path, "Inventory intelligence report"
        ),
        _spec("inventory", "lineage", i.inventory_lineage_path, "Inventory lineage records"),
        _spec("quality", "manifest", i.quality_manifest_path, "Quality analytics manifest"),
        _spec("quality", "csv_output", i.quality_alerts_path, "Quality alerts"),
        _spec("quality", "markdown_report", i.quality_report_path, "Quality analytics report"),
        _spec("quality", "lineage", i.quality_lineage_path, "Quality lineage records"),
        _spec("maintenance", "manifest", i.maintenance_manifest_path, "Maintenance manifest"),
        _spec(
            "maintenance", "json_output", i.maintenance_predictions_path, "Maintenance predictions"
        ),
        _spec(
            "maintenance",
            "markdown_report",
            i.maintenance_report_path,
            "Maintenance analytics report",
        ),
        _spec("maintenance", "lineage", i.maintenance_lineage_path, "Maintenance lineage records"),
        _spec("monitoring", "manifest", i.monitoring_manifest_path, "Monitoring manifest"),
        _spec(
            "monitoring",
            "json_output",
            i.platform_health_summary_path,
            "Platform health summary",
        ),
        _spec("monitoring", "markdown_report", i.monitoring_report_path, "Monitoring report"),
        _spec("monitoring", "lineage", i.monitoring_lineage_path, "Monitoring lineage records"),
    ]


def _spec(domain: str, evidence_type: str, path: Path, title: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "evidence_type": evidence_type,
        "path": path,
        "title": title,
        "required": True,
    }


def _catalogue_item(index: int, spec: dict[str, Any]) -> dict[str, Any]:
    path = spec["path"]
    payload = _safe_payload(path)
    metrics = _key_metrics(path, payload)
    return {
        "evidence_id": f"EVID-{index:03d}-{spec['domain']}-{spec['evidence_type']}",
        "domain": spec["domain"],
        "evidence_type": spec["evidence_type"],
        "relative_path": relative_path(path),
        "title": spec["title"],
        "description": _description(spec["domain"], spec["evidence_type"], metrics),
        "row_count": _row_count(path) if path.suffix == ".csv" else None,
        "file_size": path.stat().st_size,
        "sha256": sha256_file(path),
        "synthetic_data_flag": True,
        "upstream_run_id": _run_id(payload),
        "related_manifest": _related_manifest(spec["domain"]),
        "related_lineage": _related_lineage(spec["domain"]),
        "freshness_label": "controlled_static_evidence",
        "supported_question_types": _supported_question_types(spec["domain"]),
        "key_metrics": metrics,
    }


def _description(domain: str, evidence_type: str, metrics: dict[str, Any]) -> str:
    metric_text = ", ".join(f"{key}={value}" for key, value in sorted(metrics.items())[:4])
    suffix = f" Key metrics: {metric_text}." if metric_text else ""
    return f"Controlled {domain} {evidence_type} for synthetic manufacturing operations.{suffix}"


def _key_metrics(path: Path, payload: Any) -> dict[str, Any]:
    if path.suffix == ".csv":
        frame = pd.read_csv(path)
        return {"rows": len(frame), "columns": len(frame.columns)}
    if isinstance(payload, dict):
        keys = [
            "validation_status",
            "platform_health_score",
            "platform_health_label",
            "quarantine_rate",
            "warning_count",
            "error_count",
            "pipeline_name",
        ]
        return {key: payload[key] for key in keys if key in payload}
    if isinstance(payload, list):
        return {"records": len(payload)}
    return {}


def _safe_payload(path: Path) -> Any:
    if path.suffix not in {".json", ".jsonl"}:
        return {}
    if path.suffix == ".jsonl":
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"GENAI_EVIDENCE_ABSOLUTE_PATH: {relative_path(path)}")
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DataContractError(f"GENAI_REQUIRED_EVIDENCE_MISSING: {relative_path(path)}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"GENAI_REQUIRED_JSON_OBJECT_INVALID: {relative_path(path)}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"GENAI_EVIDENCE_ABSOLUTE_PATH: {relative_path(path)}")
    return payload


def _row_count(path: Path) -> int:
    return max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)


def _run_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in [
        "run_id",
        "ingestion_run_id",
        "forecast_run_id",
        "inventory_run_id",
        "quality_run_id",
        "maintenance_run_id",
        "monitoring_run_id",
    ]:
        if key in payload:
            return str(payload[key])
    return None


def _related_manifest(domain: str) -> str | None:
    return {
        "generation": "data/raw/generation_manifest.json",
        "ingestion": "data/interim/_metadata/ingestion-manifest.json",
        "forecasting": "outputs/forecasting/forecast-manifest.json",
        "inventory": "outputs/inventory/inventory-manifest.json",
        "quality": "outputs/quality/quality-manifest.json",
        "maintenance": "outputs/maintenance/maintenance-manifest.json",
        "monitoring": "outputs/monitoring/monitoring-manifest.json",
    }.get(domain)


def _related_lineage(domain: str) -> str | None:
    return {
        "ingestion": "data/interim/_metadata/lineage-records.json",
        "forecasting": "outputs/forecasting/lineage-records.json",
        "inventory": "outputs/inventory/lineage-records.json",
        "quality": "outputs/quality/lineage-records.json",
        "maintenance": "outputs/maintenance/lineage-records.json",
        "monitoring": "outputs/monitoring/lineage-records.json",
    }.get(domain)


def _supported_question_types(domain: str) -> list[str]:
    mapping = {
        "generation": ["executive_summary", "data_quality", "lineage"],
        "ingestion": ["executive_summary", "data_quality", "lineage"],
        "forecasting": ["executive_summary", "forecasting"],
        "inventory": ["executive_summary", "inventory"],
        "quality": ["executive_summary", "quality"],
        "maintenance": ["executive_summary", "maintenance"],
        "monitoring": ["executive_summary", "monitoring"],
    }
    return mapping[domain]


def _input_hash_paths(config: GenAIConfig) -> dict[str, Path]:
    return {field: getattr(config.inputs, field) for field in GenAIInputsFields}


GenAIInputsFields = (
    "generation_manifest_path",
    "schema_metadata_path",
    "ingestion_manifest_path",
    "validation_summary_path",
    "forecast_manifest_path",
    "inventory_manifest_path",
    "quality_manifest_path",
    "maintenance_manifest_path",
    "monitoring_manifest_path",
)
