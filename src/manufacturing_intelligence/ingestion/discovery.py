"""Source and metadata discovery for governed ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.data_generation.schemas import SCHEMAS, DatasetSchema
from manufacturing_intelligence.ingestion.config import IngestionConfig


@dataclass(frozen=True)
class DatasetSource:
    """Discovered raw dataset source."""

    dataset_name: str
    schema: DatasetSchema
    path: Path
    manifest_metadata: dict[str, Any]


@dataclass(frozen=True)
class DiscoveredSources:
    """All raw inputs and Milestone 2 metadata required by ingestion."""

    datasets: tuple[DatasetSource, ...]
    generation_manifest: dict[str, Any]
    schema_metadata: dict[str, Any]


def discover_sources(config: IngestionConfig) -> DiscoveredSources:
    """Discover expected raw datasets and verify Milestone 2 metadata files exist."""
    manifest_path = config.validation.generation_manifest_path
    schema_metadata_path = config.validation.schema_registry_path
    if not manifest_path.is_file():
        raise DataContractError(f"METADATA_MISSING: {manifest_path}")
    if not schema_metadata_path.is_file():
        raise DataContractError(f"METADATA_MISSING: {schema_metadata_path}")
    generation_manifest = _read_json(manifest_path)
    schema_metadata = _read_json(schema_metadata_path)
    outputs = generation_manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise DataContractError("METADATA_MISSING: generation manifest outputs")

    discovered: list[DatasetSource] = []
    for dataset_name in config.ingestion.expected_datasets:
        schema = SCHEMAS[dataset_name]
        path = config.ingestion.input_directory / schema.filename
        if not path.is_file():
            raise DataContractError(f"FILE_MISSING: {path}")
        output_metadata = outputs.get(dataset_name)
        if not isinstance(output_metadata, dict):
            raise DataContractError(f"METADATA_MISSING: manifest entry for {dataset_name}")
        if config.validation.verify_source_hashes:
            _verify_source_against_manifest(path, schema, output_metadata)
        discovered.append(
            DatasetSource(
                dataset_name=dataset_name,
                schema=schema,
                path=path,
                manifest_metadata=output_metadata,
            )
        )
    unexpected = [
        path.name
        for path in config.ingestion.input_directory.iterdir()
        if path.is_file()
        and path.suffix in {".csv", ".jsonl"}
        and path.name not in {SCHEMAS[name].filename for name in config.ingestion.expected_datasets}
    ]
    if unexpected:
        raise DataContractError(f"FILE_FORMAT_MISMATCH: unexpected dataset files {unexpected}")
    return DiscoveredSources(
        datasets=tuple(discovered),
        generation_manifest=generation_manifest,
        schema_metadata=schema_metadata,
    )


def _verify_source_against_manifest(
    path: Path, schema: DatasetSchema, metadata: dict[str, Any]
) -> None:
    if metadata.get("file_format") != schema.file_format:
        raise DataContractError(f"FILE_FORMAT_MISMATCH: {schema.dataset_name}")
    if metadata.get("file_size_bytes") != path.stat().st_size:
        raise DataContractError(f"FILE_SIZE_MISMATCH: {schema.dataset_name}")
    if metadata.get("sha256") != sha256_file(path):
        raise DataContractError(f"FILE_HASH_MISMATCH: {schema.dataset_name}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise DataContractError(f"INVALID_UTF8: {path}") from exc
    if not isinstance(payload, dict):
        raise DataContractError(f"METADATA_MISSING: expected object in {path}")
    return payload
