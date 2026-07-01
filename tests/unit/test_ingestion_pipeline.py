from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from manufacturing_intelligence.common.exceptions import DataContractError, PipelineExecutionError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.ingestion.existing_run import validate_existing_run
from manufacturing_intelligence.ingestion.pipeline import run_ingestion


def test_valid_tracked_data_yields_zero_quarantine_and_preserves_raw(tmp_path: Path) -> None:
    raw_hashes_before = _raw_hashes(project_root() / "data" / "raw")
    result = run_ingestion(output_directory=tmp_path / "interim")
    raw_hashes_after = _raw_hashes(project_root() / "data" / "raw")

    assert result.validation_status == "success"
    assert sum(result.quarantine_counts.values()) == 0
    assert result.source_counts == result.accepted_counts
    assert raw_hashes_before == raw_hashes_after


def test_identical_inputs_produce_identical_outputs_and_run_id(tmp_path: Path) -> None:
    first = run_ingestion(output_directory=tmp_path / "first")
    second = run_ingestion(output_directory=tmp_path / "second")

    assert first.ingestion_run_id == second.ingestion_run_id
    assert _tree_bytes(first.output_directory) == _tree_bytes(second.output_directory)


def test_relevant_config_change_changes_run_id(tmp_path: Path) -> None:
    permissive_config = _write_config_variant(
        tmp_path,
        lambda payload: payload["ingestion"].update(
            {"mode": "permissive", "output_directory": str(tmp_path / "permissive")}
        ),
    )

    strict = run_ingestion(output_directory=tmp_path / "strict")
    permissive = run_ingestion(config_path=permissive_config)

    assert strict.ingestion_run_id != permissive.ingestion_run_id


def test_missing_required_dataset_is_detected(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    (raw / "sales_orders.csv").unlink()
    config = _config_for(tmp_path, raw)

    with pytest.raises(DataContractError, match="FILE_MISSING"):
        run_ingestion(config)


def test_missing_required_metadata_is_detected(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    (raw / "generation_manifest.json").unlink()
    config = _config_for(tmp_path, raw)

    with pytest.raises(DataContractError, match="METADATA_MISSING"):
        run_ingestion(config)


def test_source_size_or_hash_mismatch_is_detected(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    with (raw / "sales_orders.csv").open("a", encoding="utf-8") as handle:
        handle.write("#tamper\n")
    config = _config_for(tmp_path, raw)

    with pytest.raises(DataContractError, match="FILE_SIZE_MISMATCH"):
        run_ingestion(config)


def test_invalid_json_reports_line_number(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    with (raw / "production_events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{bad json\n")
    config = _config_for(tmp_path, raw, verify_hashes=False)

    with pytest.raises(DataContractError, match="INVALID_JSON: production_events line 169"):
        run_ingestion(config)


def test_invalid_csv_header_is_detected(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    path = raw / "inventory_levels.csv"
    rows = path.read_text(encoding="utf-8").splitlines()
    rows[0] = rows[0].replace("available_quantity", "available_qty")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    config = _config_for(tmp_path, raw, verify_hashes=False)

    with pytest.raises(DataContractError, match="INVALID_HEADER"):
        run_ingestion(config)


def test_permissive_mode_quarantines_invalid_record_and_preserves_value(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    _mutate_csv(
        raw / "inventory_levels.csv",
        lambda row: row.update({"available_quantity": "999999"}),
    )
    config = _config_for(
        tmp_path,
        raw,
        mode="permissive",
        verify_hashes=False,
        maximum_quarantine_rate=1.0,
    )

    result = run_ingestion(config)
    quarantine = _read_jsonl(result.output_directory / "quarantine" / "inventory_levels.jsonl")

    assert result.quarantine_counts["inventory_levels"] == 1
    assert quarantine[0]["rule_codes"] == ["INVALID_DERIVED_FIELD"]
    assert quarantine[0]["original_record"]["available_quantity"] == "999999"


def test_duplicate_primary_key_first_record_wins_in_permissive_mode(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    path = raw / "sales_orders.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")
    config = _config_for(
        tmp_path,
        raw,
        mode="permissive",
        verify_hashes=False,
        maximum_quarantine_rate=1.0,
    )

    result = run_ingestion(config)

    assert result.accepted_counts["sales_orders"] == 180
    assert result.quarantine_counts["sales_orders"] == 1


@pytest.mark.parametrize(
    ("filename", "mutate", "rule_code"),
    [
        (
            "production_events.jsonl",
            lambda record: record.update({"accepted_quantity": 0}),
            "INVALID_QUANTITY_RELATIONSHIP",
        ),
        (
            "sales_orders.csv",
            lambda record: record.update({"order_value": "1.0"}),
            "INVALID_DERIVED_FIELD",
        ),
        (
            "equipment_health.jsonl",
            lambda record: record.update({"threshold_status": "critical"}),
            "INVALID_DERIVED_FIELD",
        ),
        (
            "supplier_performance.csv",
            lambda record: record.update({"delay_days": "999"}),
            "INVALID_DERIVED_FIELD",
        ),
    ],
)
def test_domain_invariant_corruptions_are_quarantined(
    tmp_path: Path,
    filename: str,
    mutate: Callable[[dict[str, Any]], None],
    rule_code: str,
) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    path = raw / filename
    if filename.endswith(".jsonl"):
        _mutate_jsonl(path, mutate)
    else:
        _mutate_csv(path, mutate)
    config = _config_for(
        tmp_path,
        raw,
        mode="permissive",
        verify_hashes=False,
        maximum_quarantine_rate=1.0,
    )

    result = run_ingestion(config)
    dataset = filename.rsplit(".", maxsplit=1)[0]
    quarantine = _read_jsonl(result.output_directory / "quarantine" / f"{dataset}.jsonl")

    assert result.quarantine_counts[dataset] >= 1
    assert rule_code in quarantine[0]["rule_codes"]


def test_strict_mode_fails_on_record_violation(tmp_path: Path) -> None:
    raw = _copy_raw(tmp_path)
    _disable_hash_checks(tmp_path, raw)
    _mutate_csv(raw / "sales_orders.csv", lambda row: row.update({"fulfilled_quantity": "999999"}))
    config = _config_for(tmp_path, raw, verify_hashes=False)

    with pytest.raises(PipelineExecutionError, match="Strict ingestion failed"):
        run_ingestion(config)


def test_existing_run_validation_detects_tampering(tmp_path: Path) -> None:
    result = run_ingestion(output_directory=tmp_path / "interim")
    accepted_file = result.output_directory / "accepted" / "sales_orders.csv"
    with accepted_file.open("a", encoding="utf-8") as handle:
        handle.write("#tamper\n")

    with pytest.raises(DataContractError, match="FILE_SIZE_MISMATCH"):
        validate_existing_run(output_directory=result.output_directory)


def test_overwrite_protection_and_unrelated_file_preservation(tmp_path: Path) -> None:
    output = tmp_path / "interim"
    run_ingestion(output_directory=output)
    unrelated = output / "keep_me.txt"
    unrelated.write_text("keep\n", encoding="utf-8")

    with pytest.raises(PipelineExecutionError, match="already exists"):
        run_ingestion(output_directory=output)

    run_ingestion(output_directory=output, overwrite=True)
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output = tmp_path / "interim"
    env = os.environ.copy()
    for key in (
        "COVERAGE_PROCESS_START",
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
    ):
        env.pop(key, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.ingestion",
            "--config",
            str(project_root() / "configs" / "ingestion.yaml"),
            "--output-directory",
            str(output),
            "--overwrite",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert completed.returncode == 0
    assert "completed with status success" in completed.stdout


def _copy_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    shutil.copytree(project_root() / "data" / "raw", raw)
    return raw


def _config_for(
    tmp_path: Path,
    raw: Path,
    *,
    mode: str = "strict",
    verify_hashes: bool = True,
    maximum_quarantine_rate: float = 0.0,
) -> Path:
    return _write_config_variant(
        tmp_path,
        lambda payload: (
            payload["ingestion"].update(
                {
                    "input_directory": str(raw),
                    "output_directory": str(tmp_path / "interim"),
                    "mode": mode,
                    "overwrite": True,
                }
            ),
            payload["validation"].update(
                {
                    "generation_manifest_path": str(raw / "generation_manifest.json"),
                    "schema_registry_path": str(raw / "schema_metadata.json"),
                    "entity_catalogue_path": str(raw / "schema_metadata.json"),
                    "verify_source_hashes": verify_hashes,
                    "maximum_quarantine_rate": maximum_quarantine_rate,
                }
            ),
        ),
    )


def _write_config_variant(tmp_path: Path, mutate: Callable[[dict[str, Any]], object]) -> Path:
    payload = yaml.safe_load((project_root() / "configs" / "ingestion.yaml").read_text())
    mutate(payload)
    path = tmp_path / "ingestion.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _disable_hash_checks(tmp_path: Path, raw: Path) -> None:
    manifest_path = raw / "generation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for _dataset, metadata in manifest["outputs"].items():
        path = raw / Path(metadata["path"]).name
        metadata["file_size_bytes"] = path.stat().st_size
        metadata["sha256"] = sha256_file(path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mutate_csv(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    mutate(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _mutate_jsonl(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    mutate(rows[0])
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _raw_hashes(raw: Path) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in sorted(raw.iterdir()) if path.is_file()}


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        child.relative_to(path).as_posix(): child.read_bytes()
        for child in sorted(path.rglob("*"))
        if child.is_file()
    }
