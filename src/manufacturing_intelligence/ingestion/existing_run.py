"""Existing interim-run validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.data_generation.schemas import SCHEMAS
from manufacturing_intelligence.ingestion.config import load_ingestion_config


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing interim run without regenerating outputs."""
    config = load_ingestion_config(config_path)
    output_dir = (
        output_directory.resolve() if output_directory else config.ingestion.output_directory
    )
    metadata_dir = output_dir / "_metadata"
    required_metadata = (
        "ingestion-manifest.json",
        "validation-summary.json",
        "data-quality-report.json",
        "quarantine-summary.json",
        "lineage-records.json",
    )
    for filename in required_metadata:
        if not (metadata_dir / filename).is_file():
            raise DataContractError(f"METADATA_MISSING: {filename}")
    manifest = _read_json(metadata_dir / "ingestion-manifest.json")
    _reject_absolute_paths(manifest)
    for dataset, schema in SCHEMAS.items():
        _verify_file(output_dir, manifest["accepted_outputs"][dataset])
        _verify_file(output_dir, manifest["quarantine_outputs"][dataset])
        if not (output_dir / "accepted" / schema.filename).is_file():
            raise DataContractError(f"FILE_MISSING: accepted {schema.filename}")
        if not (output_dir / "quarantine" / f"{dataset}.jsonl").is_file():
            raise DataContractError(f"FILE_MISSING: quarantine {dataset}")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path_value = evidence["path"]
    path = Path(path_value)
    path = output_dir / path if not path.is_absolute() else resolve_project_path(path_value)
    if not path.exists():
        path = output_dir / Path(path_value).name
    if not path.is_file():
        raise DataContractError(f"FILE_MISSING: {path_value}")
    if evidence["file_size_bytes"] != path.stat().st_size:
        raise DataContractError(f"FILE_SIZE_MISMATCH: {path_value}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"FILE_HASH_MISMATCH: {path_value}")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"METADATA_MISSING: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    text = json.dumps(payload)
    if str(Path.home()) in text:
        raise DataContractError("Manifest contains machine-specific absolute paths")
