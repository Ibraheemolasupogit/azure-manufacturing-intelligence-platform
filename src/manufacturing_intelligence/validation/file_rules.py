"""File-level validation helpers."""

from __future__ import annotations

from manufacturing_intelligence.data_generation.schemas import DatasetSchema


def validate_schema_version(schema: DatasetSchema, supported_version: str = "1.0.0") -> bool:
    """Return whether a dataset schema version is supported."""
    return schema.schema_version == supported_version
