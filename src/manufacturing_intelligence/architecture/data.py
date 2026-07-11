"""Governed evidence loading for architecture outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.architecture.config import ArchitectureConfig, ArchitectureInputs
from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class ArchitectureEvidence:
    manifests: dict[str, dict[str, Any]]
    input_hashes: dict[str, str]
    source_row_counts: dict[str, int | None]


def load_architecture_evidence(config: ArchitectureConfig) -> ArchitectureEvidence:
    _verify_required_files(config)
    manifests = {
        "ingestion": _read_json(config.inputs.ingestion_manifest_path),
        "forecast": _read_json(config.inputs.forecast_manifest_path),
        "inventory": _read_json(config.inputs.inventory_manifest_path),
        "quality": _read_json(config.inputs.quality_manifest_path),
        "maintenance": _read_json(config.inputs.maintenance_manifest_path),
        "monitoring": _read_json(config.inputs.monitoring_manifest_path),
        "genai": _read_json(config.inputs.genai_manifest_path),
        "dashboard": _read_json(config.inputs.dashboard_manifest_path),
    }
    _verify_manifests(manifests)
    for path in [
        config.inputs.ingestion_lineage_path,
        config.inputs.forecast_lineage_path,
        config.inputs.inventory_lineage_path,
        config.inputs.quality_lineage_path,
        config.inputs.maintenance_lineage_path,
        config.inputs.monitoring_lineage_path,
        config.inputs.genai_lineage_path,
        config.inputs.dashboard_lineage_path,
    ]:
        if not _read_json_list(path):
            raise DataContractError(f"ARCHITECTURE_LINEAGE_EMPTY: {relative_path(path)}")
    return ArchitectureEvidence(
        manifests=manifests,
        input_hashes={
            field: sha256_file(getattr(config.inputs, field))
            for field in ArchitectureInputs.__dataclass_fields__
        },
        source_row_counts=_source_row_counts(manifests),
    )


def verify_upstream_unchanged(
    config: ArchitectureConfig,
    evidence: ArchitectureEvidence,
) -> None:
    for field, expected in evidence.input_hashes.items():
        if sha256_file(getattr(config.inputs, field)) != expected:
            raise DataContractError(f"ARCHITECTURE_UPSTREAM_CHANGED: {field}")


def _verify_required_files(config: ArchitectureConfig) -> None:
    for field in ArchitectureInputs.__dataclass_fields__:
        path = getattr(config.inputs, field)
        if not path.is_file():
            raise DataContractError(f"ARCHITECTURE_REQUIRED_INPUT_MISSING: {relative_path(path)}")


def _verify_manifests(manifests: dict[str, dict[str, Any]]) -> None:
    for domain, manifest in manifests.items():
        if manifest.get("validation_status") != "success":
            raise DataContractError(f"ARCHITECTURE_MANIFEST_NOT_SUCCESSFUL: {domain}")
        if domain == "genai" and manifest.get("external_model_called") is not False:
            raise DataContractError("ARCHITECTURE_GENAI_EXTERNAL_CALL_INVALID")
        if domain == "dashboard" and (
            manifest.get("azure_deployment") is not False
            or manifest.get("power_bi_deployment") is not False
        ):
            raise DataContractError("ARCHITECTURE_DASHBOARD_DEPLOYMENT_FLAG_INVALID")


def _source_row_counts(manifests: dict[str, dict[str, Any]]) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    for domain, manifest in manifests.items():
        outputs = manifest.get("output_files")
        if isinstance(outputs, dict):
            for name, evidence in outputs.items():
                if isinstance(evidence, dict) and "row_count" in evidence:
                    counts[f"{domain}.{name}"] = evidence.get("row_count")
    accepted = manifests["ingestion"].get("accepted_outputs")
    if isinstance(accepted, dict):
        for name, evidence in accepted.items():
            if isinstance(evidence, dict):
                counts[f"ingestion.accepted.{name}"] = evidence.get("row_count")
    return counts


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"ARCHITECTURE_JSON_INVALID: {relative_path(path)}")
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError(f"ARCHITECTURE_ABSOLUTE_PATH_IN_INPUT: {relative_path(path)}")
    return payload


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise DataContractError(f"ARCHITECTURE_JSON_LIST_INVALID: {relative_path(path)}")
    return payload
