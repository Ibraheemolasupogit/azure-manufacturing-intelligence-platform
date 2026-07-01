"""Configuration loading for governed ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path
from manufacturing_intelligence.data_generation.schemas import SCHEMAS

INGESTION_MODES = {"strict", "permissive"}


@dataclass(frozen=True)
class IngestionSettings:
    """Runtime behaviour for ingestion."""

    input_directory: Path
    output_directory: Path
    mode: str
    overwrite: bool
    fail_fast: bool
    preserve_empty_quarantine_files: bool
    expected_datasets: tuple[str, ...]


@dataclass(frozen=True)
class ValidationSettings:
    """Validation contract paths and thresholds."""

    generation_manifest_path: Path
    schema_registry_path: Path
    entity_catalogue_path: Path
    verify_source_hashes: bool
    allow_unknown_fields: bool
    allow_missing_optional_fields: bool
    reject_duplicate_primary_keys: bool
    reject_unresolved_references: bool
    maximum_quarantine_rate: float
    numeric_tolerance: float


@dataclass(frozen=True)
class ReportingSettings:
    """Reporting controls."""

    include_record_examples: bool
    maximum_error_examples: int
    write_lineage: bool
    write_quality_report: bool


@dataclass(frozen=True)
class IngestionConfig:
    """Complete governed ingestion configuration."""

    config_path: Path
    ingestion: IngestionSettings
    validation: ValidationSettings
    reporting: ReportingSettings


def load_ingestion_config(config_path: Path | None = None) -> IngestionConfig:
    """Load and validate ingestion YAML configuration."""
    path = config_path or project_root() / "configs" / "ingestion.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Ingestion config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Ingestion config must contain a mapping.")

    ingestion = _section(payload, "ingestion")
    validation = _section(payload, "validation")
    reporting = _section(payload, "reporting")
    mode = _required_str(ingestion, "mode")
    if mode not in INGESTION_MODES:
        raise ConfigurationError(f"ingestion.mode must be strict or permissive: {mode}")
    input_directory = resolve_project_path(_required_str(ingestion, "input_directory"))
    output_directory = resolve_project_path(_required_str(ingestion, "output_directory"))
    if input_directory == output_directory:
        raise ConfigurationError("ingestion.input_directory and output_directory must differ")
    if output_directory == input_directory or input_directory in output_directory.parents:
        raise ConfigurationError(
            "ingestion.output_directory must not be inside immutable raw input"
        )
    expected = tuple(_required_str_list(ingestion, "expected_datasets"))
    unknown = sorted(set(expected) - set(SCHEMAS))
    if unknown:
        raise ConfigurationError(f"ingestion.expected_datasets contains unknown names: {unknown}")
    maximum_quarantine_rate = _required_float(validation, "maximum_quarantine_rate")
    if not 0 <= maximum_quarantine_rate <= 1:
        raise ConfigurationError("validation.maximum_quarantine_rate must be between 0 and 1")
    numeric_tolerance = _required_float(validation, "numeric_tolerance")
    if numeric_tolerance < 0:
        raise ConfigurationError("validation.numeric_tolerance must be non-negative")

    return IngestionConfig(
        config_path=path.resolve(),
        ingestion=IngestionSettings(
            input_directory=input_directory,
            output_directory=output_directory,
            mode=mode,
            overwrite=_required_bool(ingestion, "overwrite"),
            fail_fast=_required_bool(ingestion, "fail_fast"),
            preserve_empty_quarantine_files=_required_bool(
                ingestion, "preserve_empty_quarantine_files"
            ),
            expected_datasets=expected,
        ),
        validation=ValidationSettings(
            generation_manifest_path=resolve_project_path(
                _required_str(validation, "generation_manifest_path")
            ),
            schema_registry_path=resolve_project_path(
                _required_str(validation, "schema_registry_path")
            ),
            entity_catalogue_path=resolve_project_path(
                _required_str(validation, "entity_catalogue_path")
            ),
            verify_source_hashes=_required_bool(validation, "verify_source_hashes"),
            allow_unknown_fields=_required_bool(validation, "allow_unknown_fields"),
            allow_missing_optional_fields=_required_bool(
                validation, "allow_missing_optional_fields"
            ),
            reject_duplicate_primary_keys=_required_bool(
                validation, "reject_duplicate_primary_keys"
            ),
            reject_unresolved_references=_required_bool(validation, "reject_unresolved_references"),
            maximum_quarantine_rate=maximum_quarantine_rate,
            numeric_tolerance=numeric_tolerance,
        ),
        reporting=ReportingSettings(
            include_record_examples=_required_bool(reporting, "include_record_examples"),
            maximum_error_examples=_required_positive_int(reporting, "maximum_error_examples"),
            write_lineage=_required_bool(reporting, "write_lineage"),
            write_quality_report=_required_bool(reporting, "write_quality_report"),
        ),
    )


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Ingestion config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Ingestion config string missing or invalid: {key}")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Ingestion config boolean missing or invalid: {key}")
    return value


def _required_float(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, int | float):
        raise ConfigurationError(f"Ingestion config number missing or invalid: {key}")
    return float(value)


def _required_positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Ingestion config positive integer missing or invalid: {key}")
    return value


def _required_str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Ingestion config string list missing or invalid: {key}")
    return value
