"""Evidence integrity and lineage completeness checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path


def evidence_integrity_checks(manifests: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Verify output evidence declared by upstream manifests."""
    rows: list[dict[str, Any]] = []
    rows.extend(_generation_checks(manifests["generation"]))
    rows.extend(_accepted_output_checks(manifests["ingestion"]))
    for domain in ("forecasting", "inventory", "quality", "maintenance"):
        rows.extend(_output_file_checks(domain, manifests[domain]))
    return pd.DataFrame(rows).sort_values(["domain", "artifact"], ignore_index=True)


def lineage_completeness_checks(
    manifests: dict[str, dict[str, Any]],
    lineages: dict[str, list[dict[str, Any]]],
) -> pd.DataFrame:
    """Check whether output targets appear in lineage records."""
    rows: list[dict[str, Any]] = []
    rows.append(
        _lineage_row(
            "ingestion",
            len(manifests["ingestion"].get("accepted_outputs", {})),
            lineages["ingestion"],
        )
    )
    for domain in ("forecasting", "inventory", "quality", "maintenance"):
        expected = set()
        for entry in manifests[domain].get("output_files", {}).values():
            if isinstance(entry, dict):
                expected.add(str(entry.get("path")))
        target_paths = {
            str(item.get("target_path") or item.get("target", {}).get("path"))
            for item in lineages[domain]
            if isinstance(item, dict)
        }
        present = len(expected & target_paths)
        missing = sorted(expected - target_paths)
        score = 100.0 if not expected else present / len(expected) * 100.0
        rows.append(
            {
                "domain": domain,
                "expected_lineage_targets": len(expected),
                "observed_lineage_targets": present,
                "lineage_completeness_score": score,
                "missing_targets": ";".join(missing),
                "lineage_status": "passed" if score >= 90 else "failed",
            }
        )
    return pd.DataFrame(rows).sort_values("domain", ignore_index=True)


def manifest_integrity_score(checks: pd.DataFrame) -> float:
    """Calculate manifest integrity score."""
    if checks.empty:
        return 0.0
    return float((checks["integrity_status"] == "passed").mean() * 100.0)


def _generation_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, entry in manifest.get("outputs", {}).items():
        if isinstance(entry, dict):
            rows.append(_verify_artifact("generation", name, entry))
    schema = manifest.get("schema_metadata", {})
    if isinstance(schema, dict):
        rows.append(
            _verify_artifact(
                "generation",
                "schema_metadata",
                {"path": schema.get("path"), "sha256": schema.get("sha256"), "row_count": None},
            )
        )
    return rows


def _accepted_output_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, entry in manifest.get("accepted_outputs", {}).items():
        if isinstance(entry, dict):
            rows.append(_verify_artifact("ingestion", f"accepted_{name}", _with_interim(entry)))
    return rows


def _output_file_checks(domain: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _verify_artifact(domain, name, entry)
        for name, entry in manifest.get("output_files", {}).items()
        if isinstance(entry, dict)
    ]


def _with_interim(entry: dict[str, Any]) -> dict[str, Any]:
    updated = dict(entry)
    path = str(updated.get("path"))
    if not path.startswith("data/"):
        updated["path"] = str(Path("data/interim") / path)
    return updated


def _verify_artifact(domain: str, artifact: str, entry: dict[str, Any]) -> dict[str, Any]:
    path_value = str(entry.get("path"))
    path = resolve_project_path(path_value)
    exists = path.is_file()
    actual_size = path.stat().st_size if exists else -1
    expected_size = (
        int(entry.get("file_size_bytes", actual_size))
        if entry.get("file_size_bytes") is not None
        else actual_size
    )
    actual_hash = sha256_file(path) if exists else ""
    expected_hash = str(entry.get("sha256", ""))
    row_status = True
    actual_rows: int | None = None
    expected_rows = entry.get("row_count")
    if exists and path.suffix == ".csv" and expected_rows is not None:
        actual_rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        row_status = int(expected_rows) == actual_rows
    status = (
        exists
        and actual_size == expected_size
        and (not expected_hash or actual_hash == expected_hash)
        and row_status
    )
    return {
        "domain": domain,
        "artifact": artifact,
        "path": path_value,
        "exists": exists,
        "expected_row_count": expected_rows,
        "actual_row_count": actual_rows,
        "expected_file_size_bytes": expected_size,
        "actual_file_size_bytes": actual_size,
        "expected_sha256": expected_hash,
        "actual_sha256": actual_hash,
        "integrity_status": "passed" if status else "failed",
    }


def _lineage_row(domain: str, expected_count: int, lineage: list[dict[str, Any]]) -> dict[str, Any]:
    score = (
        100.0 if len(lineage) >= expected_count else len(lineage) / max(expected_count, 1) * 100.0
    )
    return {
        "domain": domain,
        "expected_lineage_targets": expected_count,
        "observed_lineage_targets": len(lineage),
        "lineage_completeness_score": score,
        "missing_targets": "",
        "lineage_status": "passed" if score >= 90 else "failed",
    }
