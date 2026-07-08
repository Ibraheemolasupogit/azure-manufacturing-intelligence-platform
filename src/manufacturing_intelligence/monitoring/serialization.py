"""Deterministic monitoring output serialization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.forecasting.data import relative_path


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    """Write deterministic CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_float_dtype(output[column]):
            output[column] = output[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.6f}"
            )
    output.to_csv(path, index=False, lineterminator="\n")


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Write deterministic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def file_evidence(
    path: Path, row_count: int | None = None, *, base_directory: Path | None = None
) -> dict[str, Any]:
    """Build output evidence."""
    if row_count is None and path.suffix == ".csv":
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return {
        "path": relative_path(path, base_directory=base_directory),
        "row_count": row_count,
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
