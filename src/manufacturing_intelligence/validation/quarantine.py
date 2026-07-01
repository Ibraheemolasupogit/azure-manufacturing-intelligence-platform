"""Quarantine serialization helpers."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


def quarantine_payload(
    loaded: LoadedRecord,
    issues: tuple[ValidationIssue, ...],
    ingestion_run_id: str,
) -> dict[str, Any]:
    """Create deterministic quarantine evidence for one source record."""
    sorted_issues = tuple(
        sorted(issues, key=lambda issue: (issue.rule_code, issue.field, issue.reason))
    )
    return {
        "ingestion_run_id": ingestion_run_id,
        "dataset": loaded.dataset,
        "source_path": loaded.source_path,
        "source_row_number": loaded.source_row_number,
        "record_id": loaded.record_id,
        "rule_codes": [issue.rule_code for issue in sorted_issues],
        "errors": [
            {
                "field": issue.field,
                "original_value": issue.original_value,
                "reason": issue.reason,
                "rule_code": issue.rule_code,
                "severity": issue.severity,
            }
            for issue in sorted_issues
        ],
        "original_record": loaded.record,
    }
