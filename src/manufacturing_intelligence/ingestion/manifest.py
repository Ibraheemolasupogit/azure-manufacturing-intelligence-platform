"""Manifest and evidence helpers for governed ingestion."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root


@dataclass(frozen=True)
class FileEvidence:
    """Deterministic file evidence."""

    path: str
    row_count: int
    file_size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize file evidence."""
        return asdict(self)


def file_evidence(
    path: Path, row_count: int, *, base_directory: Path | None = None
) -> FileEvidence:
    """Build evidence for a generated file."""
    return FileEvidence(
        path=relative_path(path, base_directory=base_directory),
        row_count=row_count,
        file_size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
    )


def relative_path(path: Path, *, base_directory: Path | None = None) -> str:
    """Return a repository-relative path where possible."""
    resolved = path.resolve()
    if base_directory is not None:
        try:
            return resolved.relative_to(base_directory.resolve()).as_posix()
        except ValueError:
            pass
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        return resolved.as_posix()


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Write deterministic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_commit() -> str:
    """Return current Git commit if available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()
