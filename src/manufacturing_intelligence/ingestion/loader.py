"""Load raw CSV and JSONL records with deterministic source context."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.data_generation.schemas import DatasetSchema
from manufacturing_intelligence.validation.result import LoadedRecord


def load_dataset(path: Path, schema: DatasetSchema) -> tuple[LoadedRecord, ...]:
    """Load a raw dataset and preserve source row or line numbers."""
    if schema.file_format == "csv":
        return _load_csv(path, schema)
    if schema.file_format == "jsonl":
        return _load_jsonl(path, schema)
    raise DataContractError(f"FILE_FORMAT_MISMATCH: unsupported format {schema.file_format}")


def _load_csv(path: Path, schema: DatasetSchema) -> tuple[LoadedRecord, ...]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(schema.fields):
                raise DataContractError(f"INVALID_HEADER: {schema.dataset_name}")
            records = [
                LoadedRecord(
                    dataset=schema.dataset_name,
                    source_path=path.as_posix(),
                    source_row_number=index,
                    record=dict(row),
                    record_id=_record_id(schema, row),
                )
                for index, row in enumerate(reader, start=2)
            ]
    except UnicodeDecodeError as exc:
        raise DataContractError(f"INVALID_UTF8: {path}") from exc
    if not records:
        raise DataContractError(f"EMPTY_REQUIRED_FILE: {schema.dataset_name}")
    return tuple(records)


def _load_jsonl(path: Path, schema: DatasetSchema) -> tuple[LoadedRecord, ...]:
    records: list[LoadedRecord] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DataContractError(
                        f"INVALID_JSON: {schema.dataset_name} line {line_number}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise DataContractError(
                        f"INVALID_JSON: {schema.dataset_name} line {line_number}"
                    )
                records.append(
                    LoadedRecord(
                        dataset=schema.dataset_name,
                        source_path=path.as_posix(),
                        source_row_number=line_number,
                        record=payload,
                        record_id=_record_id(schema, payload),
                    )
                )
    except UnicodeDecodeError as exc:
        raise DataContractError(f"INVALID_UTF8: {path}") from exc
    if not records:
        raise DataContractError(f"EMPTY_REQUIRED_FILE: {schema.dataset_name}")
    return tuple(records)


def _record_id(schema: DatasetSchema, record: dict[str, Any]) -> str:
    values = [str(record.get(field, "")) for field in schema.primary_key]
    return "|".join(values) if values else "UNKNOWN"
