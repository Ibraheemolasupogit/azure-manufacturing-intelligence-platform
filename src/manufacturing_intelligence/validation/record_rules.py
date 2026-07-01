"""Generic schema, type, category, and timestamp validation rules."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from manufacturing_intelligence.data_generation.schemas import DatasetSchema
from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


def validate_record_contract(
    loaded: LoadedRecord,
    schema: DatasetSchema,
    *,
    ingestion_run_id: str,
    allow_unknown_fields: bool,
) -> list[ValidationIssue]:
    """Validate field presence, types, categories, timestamps, and units."""
    record = loaded.record
    issues: list[ValidationIssue] = []
    expected_fields = set(schema.fields)
    actual_fields = set(record)
    for field in schema.fields:
        if field not in record and field not in schema.nullable_fields:
            issues.append(
                _issue(
                    loaded,
                    ingestion_run_id,
                    field,
                    "MISSING_FIELD",
                    "Missing required field",
                    None,
                )
            )
    if not allow_unknown_fields:
        for field in sorted(actual_fields - expected_fields):
            issues.append(
                _issue(
                    loaded,
                    ingestion_run_id,
                    field,
                    "UNKNOWN_FIELD",
                    "Field is not declared in schema registry",
                    record.get(field),
                )
            )
    for field, expected_type in schema.data_types.items():
        if field not in record or record.get(field) == "":
            continue
        if not _matches_type(record[field], expected_type):
            issues.append(
                _issue(
                    loaded,
                    ingestion_run_id,
                    field,
                    "INVALID_TYPE",
                    f"Value does not match expected type {expected_type}",
                    record.get(field),
                )
            )
    for field, allowed in schema.categorical_domains.items():
        if field in record and record[field] not in allowed:
            issues.append(
                _issue(
                    loaded,
                    ingestion_run_id,
                    field,
                    "INVALID_CATEGORY",
                    "Value is not in the declared categorical domain",
                    record.get(field),
                )
            )
    for field in schema.timestamp_fields:
        if field in record and record[field] != "" and not _valid_temporal(record[field]):
            issues.append(
                _issue(
                    loaded,
                    ingestion_run_id,
                    field,
                    "INVALID_TIMESTAMP",
                    "Value is not a valid ISO date or timestamp",
                    record.get(field),
                )
            )
    return issues


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return _can_int(value)
    if expected_type == "float":
        return _can_float(value)
    if expected_type == "boolean":
        return isinstance(value, bool) or str(value) in {"True", "False", "true", "false"}
    if expected_type in {"date", "timestamp"}:
        return _valid_temporal(value)
    return True


def _valid_temporal(value: Any) -> bool:
    try:
        text = str(value)
        if "T" in text:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _can_int(value: Any) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _can_float(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _issue(
    loaded: LoadedRecord,
    ingestion_run_id: str,
    field: str,
    rule_code: str,
    reason: str,
    original_value: Any,
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
        original_value=original_value,
        ingestion_run_id=ingestion_run_id,
    )
