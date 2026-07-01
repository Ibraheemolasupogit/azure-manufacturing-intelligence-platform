"""Structured validation result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    """One deterministic validation issue."""

    dataset: str
    source_path: str
    source_row_number: int | None
    record_id: str
    field: str
    rule_code: str
    severity: str
    reason: str
    original_value: Any
    ingestion_run_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize issue for metadata and quarantine evidence."""
        return asdict(self)


@dataclass(frozen=True)
class LoadedRecord:
    """A parsed source record with source context."""

    dataset: str
    source_path: str
    source_row_number: int
    record: dict[str, Any]
    record_id: str


@dataclass(frozen=True)
class DatasetValidationResult:
    """Accepted and quarantined records for one dataset."""

    dataset: str
    accepted: tuple[LoadedRecord, ...]
    quarantined: tuple[tuple[LoadedRecord, tuple[ValidationIssue, ...]], ...]
    file_issues: tuple[ValidationIssue, ...]
