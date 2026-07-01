"""Data-quality metric helpers."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.data_generation.schemas import DatasetSchema
from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


def dataset_quality_metrics(
    schema: DatasetSchema,
    source_records: tuple[LoadedRecord, ...],
    accepted_count: int,
    quarantine_count: int,
    issues: tuple[ValidationIssue, ...],
    source_hash_verified: bool,
) -> dict[str, Any]:
    """Build dataset-level quality metrics from actual processed records."""
    record_count = len(source_records)
    issue_codes = [issue.rule_code for issue in issues]
    completeness = {field: _completeness(source_records, field) for field in schema.fields}
    return {
        "record_count": record_count,
        "accepted_count": accepted_count,
        "quarantine_count": quarantine_count,
        "completeness_by_field": completeness,
        "primary_key_uniqueness": 1.0
        if record_count == 0
        else len({record.record_id for record in source_records}) / record_count,
        "validity_rate": 1.0 if record_count == 0 else accepted_count / record_count,
        "accepted_rate": 1.0 if record_count == 0 else accepted_count / record_count,
        "quarantine_rate": 0.0 if record_count == 0 else quarantine_count / record_count,
        "duplicate_count": issue_codes.count("DUPLICATE_PRIMARY_KEY"),
        "unresolved_reference_count": issue_codes.count("INVALID_REFERENCE"),
        "invalid_category_count": issue_codes.count("INVALID_CATEGORY"),
        "invalid_timestamp_count": issue_codes.count("INVALID_TIMESTAMP"),
        "invariant_violation_count": sum(
            1
            for code in issue_codes
            if code in {"INVALID_DERIVED_FIELD", "INVALID_QUANTITY_RELATIONSHIP"}
        ),
        "source_hash_verified": source_hash_verified,
        "status": "passed" if quarantine_count == 0 and not issues else "failed",
    }


def _completeness(records: tuple[LoadedRecord, ...], field: str) -> float:
    if not records:
        return 1.0
    present = sum(1 for record in records if record.record.get(field) not in {"", None})
    return present / len(records)
