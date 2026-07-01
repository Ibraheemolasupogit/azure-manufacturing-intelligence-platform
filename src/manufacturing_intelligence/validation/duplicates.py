"""Duplicate primary-key validation."""

from __future__ import annotations

from manufacturing_intelligence.validation.result import LoadedRecord


def duplicate_record_ids(records: tuple[LoadedRecord, ...]) -> set[str]:
    """Return duplicate primary-key identifiers after first occurrence."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        if record.record_id in seen:
            duplicates.add(record.record_id)
        seen.add(record.record_id)
    return duplicates
