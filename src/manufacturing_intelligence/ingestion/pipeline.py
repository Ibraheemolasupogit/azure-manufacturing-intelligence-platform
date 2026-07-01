"""Governed ingestion and validation pipeline."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.data_generation.schemas import SCHEMAS
from manufacturing_intelligence.ingestion.config import IngestionConfig, load_ingestion_config
from manufacturing_intelligence.ingestion.discovery import discover_sources
from manufacturing_intelligence.ingestion.loader import load_dataset
from manufacturing_intelligence.ingestion.manifest import (
    file_evidence,
    git_commit,
    relative_path,
    write_json,
)
from manufacturing_intelligence.ingestion.reporting import write_markdown_report
from manufacturing_intelligence.ingestion.serialization import write_accepted, write_quarantine
from manufacturing_intelligence.validation.domain_rules import validate_domain_rules
from manufacturing_intelligence.validation.duplicates import duplicate_record_ids
from manufacturing_intelligence.validation.quality import dataset_quality_metrics
from manufacturing_intelligence.validation.record_rules import validate_record_contract
from manufacturing_intelligence.validation.relationships import (
    build_reference_indexes,
    validate_relationships,
)
from manufacturing_intelligence.validation.result import (
    DatasetValidationResult,
    LoadedRecord,
    ValidationIssue,
)


@dataclass(frozen=True)
class IngestionResult:
    """Summary of one ingestion run."""

    ingestion_run_id: str
    output_directory: Path
    validation_status: str
    source_counts: dict[str, int]
    accepted_counts: dict[str, int]
    quarantine_counts: dict[str, int]


def run_ingestion(
    config_path: Path | None = None,
    *,
    input_directory: Path | None = None,
    output_directory: Path | None = None,
    mode: str | None = None,
    overwrite: bool = False,
) -> IngestionResult:
    """Run governed ingestion and write deterministic interim evidence."""
    config = _with_overrides(
        load_ingestion_config(config_path),
        input_directory=input_directory,
        output_directory=output_directory,
        mode=mode,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    discovered = discover_sources(config)
    records_by_dataset = {
        source.dataset_name: load_dataset(source.path, source.schema)
        for source in discovered.datasets
    }
    ingestion_run_id = _run_id(config, discovered.generation_manifest)
    references = build_reference_indexes(records_by_dataset)
    dataset_results: list[DatasetValidationResult] = []
    for source in discovered.datasets:
        records = records_by_dataset[source.dataset_name]
        duplicate_ids = duplicate_record_ids(records)
        accepted: list[LoadedRecord] = []
        quarantined: list[tuple[LoadedRecord, tuple[ValidationIssue, ...]]] = []
        seen_ids: set[str] = set()
        for loaded in records:
            issues: list[ValidationIssue] = []
            issues.extend(
                validate_record_contract(
                    loaded,
                    source.schema,
                    ingestion_run_id=ingestion_run_id,
                    allow_unknown_fields=config.validation.allow_unknown_fields,
                )
            )
            issues.extend(validate_domain_rules(loaded, ingestion_run_id))
            issues.extend(validate_relationships(loaded, references, ingestion_run_id))
            if loaded.record_id in duplicate_ids and loaded.record_id in seen_ids:
                issues.append(
                    _issue(
                        loaded,
                        ingestion_run_id,
                        source.schema.primary_key[0],
                        "DUPLICATE_PRIMARY_KEY",
                        "Duplicate primary key; first source record wins",
                    )
                )
            seen_ids.add(loaded.record_id)
            sorted_issues = tuple(
                sorted(issues, key=lambda issue: (issue.rule_code, issue.field, issue.reason))
            )
            if sorted_issues:
                quarantined.append((loaded, sorted_issues))
            else:
                accepted.append(loaded)
        dataset_results.append(
            DatasetValidationResult(
                dataset=source.dataset_name,
                accepted=tuple(accepted),
                quarantined=tuple(quarantined),
                file_issues=(),
            )
        )
    total_source = sum(len(records) for records in records_by_dataset.values())
    total_quarantine = sum(len(result.quarantined) for result in dataset_results)
    quarantine_rate = 0.0 if total_source == 0 else total_quarantine / total_source
    if config.ingestion.mode == "strict" and total_quarantine:
        raise PipelineExecutionError("Strict ingestion failed because records were quarantined")
    threshold_exceeded = quarantine_rate > config.validation.maximum_quarantine_rate
    if threshold_exceeded:
        raise PipelineExecutionError("QUARANTINE_RATE_EXCEEDED: maximum quarantine rate exceeded")
    return _publish_outputs(
        config,
        discovered.generation_manifest,
        discovered.schema_metadata,
        records_by_dataset,
        tuple(dataset_results),
        ingestion_run_id,
    )


def _publish_outputs(
    config: IngestionConfig,
    generation_manifest: dict[str, Any],
    schema_metadata: dict[str, Any],
    records_by_dataset: dict[str, tuple[LoadedRecord, ...]],
    dataset_results: tuple[DatasetValidationResult, ...],
    ingestion_run_id: str,
) -> IngestionResult:
    output_dir = config.ingestion.output_directory
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "accepted").mkdir(exist_ok=True)
    (output_dir / "quarantine").mkdir(exist_ok=True)
    metadata_dir = output_dir / "_metadata"
    metadata_dir.mkdir(exist_ok=True)
    accepted_evidence: dict[str, dict[str, Any]] = {}
    quarantine_evidence: dict[str, dict[str, Any]] = {}
    source_evidence: dict[str, dict[str, Any]] = {}
    source_counts: dict[str, int] = {}
    accepted_counts: dict[str, int] = {}
    quarantine_counts: dict[str, int] = {}
    all_issues: list[ValidationIssue] = []
    quality_by_dataset: dict[str, dict[str, Any]] = {}
    lineage_records: list[dict[str, Any]] = []
    configuration_hash = sha256_file(config.config_path)
    status = "success"
    for result in dataset_results:
        schema = SCHEMAS[result.dataset]
        source_path = config.ingestion.input_directory / schema.filename
        source_rows = len(records_by_dataset[result.dataset])
        accepted_path, accepted_count = write_accepted(output_dir, schema, result.accepted)
        quarantine_path, quarantine_count = write_quarantine(
            output_dir,
            schema,
            result.quarantined,
            ingestion_run_id,
        )
        source_file = file_evidence(source_path, source_rows)
        accepted_file = file_evidence(
            accepted_path,
            accepted_count,
            base_directory=output_dir,
        )
        quarantine_file = file_evidence(
            quarantine_path,
            quarantine_count,
            base_directory=output_dir,
        )
        source_evidence[result.dataset] = source_file.to_dict()
        accepted_evidence[result.dataset] = accepted_file.to_dict()
        quarantine_evidence[result.dataset] = quarantine_file.to_dict()
        source_counts[result.dataset] = source_rows
        accepted_counts[result.dataset] = accepted_count
        quarantine_counts[result.dataset] = quarantine_count
        issues = tuple(issue for _, record_issues in result.quarantined for issue in record_issues)
        all_issues.extend(issues)
        quality_by_dataset[result.dataset] = dataset_quality_metrics(
            schema,
            records_by_dataset[result.dataset],
            accepted_count,
            quarantine_count,
            issues,
            source_hash_verified=True,
        )
        lineage_records.append(
            {
                "ingestion_run_id": ingestion_run_id,
                "dataset": result.dataset,
                "schema_version": schema.schema_version,
                "source_relative_path": source_file.path,
                "source_row_count": source_file.row_count,
                "source_file_size_bytes": source_file.file_size_bytes,
                "source_sha256": source_file.sha256,
                "accepted_relative_path": accepted_file.path,
                "accepted_row_count": accepted_file.row_count,
                "accepted_file_size_bytes": accepted_file.file_size_bytes,
                "accepted_sha256": accepted_file.sha256,
                "quarantine_relative_path": quarantine_file.path,
                "quarantine_row_count": quarantine_file.row_count,
                "quarantine_file_size_bytes": quarantine_file.file_size_bytes,
                "quarantine_sha256": quarantine_file.sha256,
                "transformation_type": "local governed ingestion and validation",
                "configuration_hash": configuration_hash,
                "validation_status": status,
                "synthetic_data_classification": "synthetic_portfolio_sample",
            }
        )
    total_source = sum(source_counts.values())
    total_accepted = sum(accepted_counts.values())
    total_quarantine = sum(quarantine_counts.values())
    quarantine_rate = 0.0 if total_source == 0 else total_quarantine / total_source
    rule_counts = Counter(issue.rule_code for issue in all_issues)
    severity_counts = Counter(issue.severity for issue in all_issues)
    manifest_payload = {
        "accepted_outputs": accepted_evidence,
        "configuration_path": relative_path(config.config_path),
        "configuration_sha256": configuration_hash,
        "critical_count": severity_counts.get("critical", 0),
        "error_count": severity_counts.get("error", 0),
        "execution_mode": config.ingestion.mode,
        "generation_manifest_path": relative_path(config.validation.generation_manifest_path),
        "generation_manifest_sha256": sha256_file(config.validation.generation_manifest_path),
        "git_commit": git_commit(),
        "ingestion_run_id": ingestion_run_id,
        "pipeline_name": "governed_ingestion",
        "pipeline_version": "0.1.0",
        "quarantine_outputs": quarantine_evidence,
        "quarantine_rate": quarantine_rate,
        "raw_input_immutability_confirmed": True,
        "schema_registry_path": relative_path(config.validation.schema_registry_path),
        "schema_registry_sha256": sha256_file(config.validation.schema_registry_path),
        "software_version": "0.1.0",
        "source_datasets": source_evidence,
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "validation_status": status,
        "warning_count": severity_counts.get("warning", 0),
    }
    validation_summary = {
        "accepted_counts_by_dataset": accepted_counts,
        "configured_maximum_quarantine_rate": config.validation.maximum_quarantine_rate,
        "discovered_datasets": list(source_counts),
        "file_level_issue_count": 0,
        "ingestion_run_id": ingestion_run_id,
        "mode": config.ingestion.mode,
        "quarantine_counts_by_dataset": quarantine_counts,
        "quarantine_rate": quarantine_rate,
        "record_level_issue_count": len(all_issues),
        "rule_code_counts": dict(sorted(rule_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "source_counts_by_dataset": source_counts,
        "source_hash_verification_result": "passed",
        "synthetic_data_confirmation": True,
        "total_accepted_count": total_accepted,
        "total_quarantine_count": total_quarantine,
        "total_source_count": total_source,
        "validation_status": status,
    }
    quarantine_summary = {
        "actual_quarantine_rate": quarantine_rate,
        "error_examples": [],
        "maximum_quarantine_rate": config.validation.maximum_quarantine_rate,
        "quarantined_records_by_dataset": quarantine_counts,
        "quarantined_records_by_rule_code": dict(sorted(rule_counts.items())),
        "quarantined_records_by_severity": dict(sorted(severity_counts.items())),
        "threshold_status": "passed",
        "total_quarantined_records": total_quarantine,
    }
    quality_report = {
        "datasets": quality_by_dataset,
        "ingestion_run_id": ingestion_run_id,
        "overall": {
            "accepted_count": total_accepted,
            "quarantine_count": total_quarantine,
            "quarantine_rate": quarantine_rate,
            "record_count": total_source,
        },
        "validation_status": status,
    }
    write_json(metadata_dir / "ingestion-manifest.json", manifest_payload)
    write_json(metadata_dir / "validation-summary.json", validation_summary)
    write_json(metadata_dir / "quarantine-summary.json", quarantine_summary)
    write_json(metadata_dir / "data-quality-report.json", quality_report)
    write_json(metadata_dir / "lineage-records.json", lineage_records)
    if config.reporting.write_quality_report:
        write_markdown_report(project_root() / "reports" / "data_quality_report.md", quality_report)
    return IngestionResult(
        ingestion_run_id=ingestion_run_id,
        output_directory=output_dir,
        validation_status=status,
        source_counts=source_counts,
        accepted_counts=accepted_counts,
        quarantine_counts=quarantine_counts,
    )


def _with_overrides(
    config: IngestionConfig,
    *,
    input_directory: Path | None,
    output_directory: Path | None,
    mode: str | None,
    overwrite: bool,
) -> IngestionConfig:
    ingestion = config.ingestion
    return IngestionConfig(
        config_path=config.config_path,
        ingestion=type(ingestion)(
            input_directory=(
                input_directory.resolve() if input_directory else ingestion.input_directory
            ),
            output_directory=(
                output_directory.resolve() if output_directory else ingestion.output_directory
            ),
            mode=mode or ingestion.mode,
            overwrite=overwrite or ingestion.overwrite,
            fail_fast=ingestion.fail_fast,
            preserve_empty_quarantine_files=ingestion.preserve_empty_quarantine_files,
            expected_datasets=ingestion.expected_datasets,
        ),
        validation=config.validation,
        reporting=config.reporting,
    )


def _ensure_can_write(config: IngestionConfig) -> None:
    output_dir = config.ingestion.output_directory
    if output_dir.exists() and any(output_dir.iterdir()) and not config.ingestion.overwrite:
        raise PipelineExecutionError(
            "Ingestion output already exists. Pass --overwrite to replace managed outputs."
        )
    for child in ("accepted", "quarantine", "_metadata"):
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def _run_id(config: IngestionConfig, generation_manifest: dict[str, Any]) -> str:
    import hashlib

    payload = {
        "configuration_hash": sha256_file(config.config_path),
        "generation_manifest_hash": sha256_file(config.validation.generation_manifest_path),
        "mode": config.ingestion.mode,
        "source_hashes": {
            dataset: metadata["sha256"]
            for dataset, metadata in sorted(generation_manifest["outputs"].items())
        },
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"INGEST-{digest[:16]}"


def _issue(
    loaded: LoadedRecord,
    ingestion_run_id: str,
    field: str,
    rule_code: str,
    reason: str,
) -> ValidationIssue:
    return ValidationIssue(
        dataset=loaded.dataset,
        source_path=loaded.source_path,
        source_row_number=loaded.source_row_number,
        record_id=loaded.record_id,
        field=field,
        rule_code=rule_code,
        severity="critical",
        reason=reason,
        original_value=loaded.record.get(field),
        ingestion_run_id=ingestion_run_id,
    )
