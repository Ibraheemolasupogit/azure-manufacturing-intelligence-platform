"""Deterministic serialization for release artefacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.forecasting.data import relative_path


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def file_evidence(path: Path, *, base_directory: Path | None = None) -> dict[str, Any]:
    row_count = None
    if path.suffix == ".csv":
        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return {
        "path": relative_path(path, base_directory=base_directory),
        "row_count": row_count,
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
