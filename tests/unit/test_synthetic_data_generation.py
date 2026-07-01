from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError, DataContractError
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.data_generation.generator import (
    generate_synthetic_data,
    validate_generated_run,
)
from manufacturing_intelligence.data_generation.schemas import SCHEMAS


def test_local_and_ci_profiles_generate_expected_scales(tmp_path: Path) -> None:
    local = generate_synthetic_data(output_dir=tmp_path / "local")
    ci = generate_synthetic_data(
        config_path=project_root() / "configs" / "synthetic_data_ci.yaml",
        output_dir=tmp_path / "ci",
    )

    assert _row_counts(local) == {
        "production_events": 168,
        "inventory_levels": 72,
        "sales_orders": 180,
        "quality_checks": 168,
        "equipment_health": 504,
        "warehouse_movements": 220,
        "supplier_performance": 120,
    }
    assert _row_counts(ci) == {
        "production_events": 4,
        "inventory_levels": 14,
        "sales_orders": 12,
        "quality_checks": 4,
        "equipment_health": 8,
        "warehouse_movements": 16,
        "supplier_performance": 10,
    }


def test_same_config_seed_produces_byte_identical_outputs(tmp_path: Path) -> None:
    first = generate_synthetic_data(output_dir=tmp_path / "first")
    second = generate_synthetic_data(output_dir=tmp_path / "second")

    assert first.run_id == second.run_id
    for schema in SCHEMAS.values():
        assert (first.raw_data_dir / schema.filename).read_bytes() == (
            second.raw_data_dir / schema.filename
        ).read_bytes()


def test_different_seed_changes_at_least_one_dataset(tmp_path: Path) -> None:
    config_path = _write_config_variant(
        tmp_path,
        lambda payload: payload["generation"].update({"random_seed": 20260799}),
    )

    baseline = generate_synthetic_data(output_dir=tmp_path / "baseline")
    changed = generate_synthetic_data(config_path=config_path, output_dir=tmp_path / "changed")

    assert _hashes(baseline) != _hashes(changed)


def test_generation_works_outside_repository_cwd(tmp_path: Path) -> None:
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = generate_synthetic_data(output_dir=tmp_path / "outside")
    finally:
        os.chdir(original_cwd)

    assert (result.raw_data_dir / "generation_manifest.json").is_file()
    validate_generated_run(result.raw_data_dir)


def test_overwrite_disabled_fails_and_cli_exits_nonzero(tmp_path: Path) -> None:
    output_dir = tmp_path / "raw"
    generate_synthetic_data(output_dir=output_dir)

    with pytest.raises(DataContractError, match="overwrite existing files"):
        generate_synthetic_data(output_dir=output_dir)

    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("COV_CORE") or key.startswith("COVERAGE"):
            env.pop(key, None)
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root() / "scripts" / "generate_synthetic_data.py"),
            "--output-dir",
            str(output_dir),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode != 0
    assert "overwrite existing files" in completed.stderr


def test_overwrite_enabled_replaces_managed_files_without_deleting_unrelated_files(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "raw"
    first = generate_synthetic_data(output_dir=output_dir)
    unrelated = output_dir / "keep_me.txt"
    unrelated.write_text("do not remove\n", encoding="utf-8")

    second = generate_synthetic_data(output_dir=output_dir, overwrite=True)

    assert unrelated.read_text(encoding="utf-8") == "do not remove\n"
    assert _hashes(first) == _hashes(second)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["entities"].update({"plants": 0}), "plants"),
        (lambda payload: payload["generation"].update({"end_date": "2025-12-31"}), "end_date"),
        (
            lambda payload: payload["probabilities"].update({"quality_defect": 1.5}),
            "quality_defect",
        ),
        (lambda payload: payload["generation"].update({"timezone": ""}), "timezone"),
        (
            lambda payload: payload["generation"].update({"generation_mode": "azure_live"}),
            "generation_mode",
        ),
    ],
)
def test_invalid_configuration_values_identify_problem_field(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    config_path = _write_config_variant(tmp_path, mutate)

    with pytest.raises(ConfigurationError, match=message):
        generate_synthetic_data(config_path=config_path, output_dir=tmp_path / "raw")


def test_invalid_output_path_is_actionable(tmp_path: Path) -> None:
    invalid_output = tmp_path / "not_a_directory"
    invalid_output.write_text("file\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Output path is not a directory"):
        generate_synthetic_data(output_dir=invalid_output)


def test_schema_registry_is_complete() -> None:
    assert set(SCHEMAS) == {
        "production_events",
        "inventory_levels",
        "sales_orders",
        "quality_checks",
        "equipment_health",
        "warehouse_movements",
        "supplier_performance",
    }
    for schema in SCHEMAS.values():
        assert schema.dataset_name
        assert schema.schema_version == "1.0.0"
        assert schema.file_format in {"csv", "jsonl"}
        assert schema.primary_key
        assert set(schema.fields) == set(schema.data_types)
        assert schema.timestamp_fields
        assert schema.relationships
        assert schema.invariants
        assert schema.logical_owner
        assert schema.synthetic_data_classification == "synthetic_portfolio_sample"


def test_manifest_integrity_is_independently_verified(tmp_path: Path) -> None:
    result = generate_synthetic_data(output_dir=tmp_path)
    validate_generated_run(tmp_path)
    manifest = _read_json(result.manifest_path)

    assert manifest["schema_version"] == "1.0.0"
    assert manifest["configuration_hash"]
    assert manifest["random_seed"] == 20260702
    assert manifest["date_range"] == {"start_date": "2026-01-01", "end_date": "2026-01-14"}
    assert manifest["timezone"] == "UTC"
    assert manifest["generation_mode"] == "local_sample"
    assert manifest["synthetic_data_only"] is True
    assert manifest["status"] == "success"
    assert not any(Path(path).is_absolute() for path in manifest["output_paths"])

    for dataset_name, schema in SCHEMAS.items():
        output = manifest["outputs"][dataset_name]
        path = tmp_path / output["path"]
        assert output["file_format"] == schema.file_format
        assert output["row_count"] == _count_rows(path, schema.file_format)
        assert output["file_size_bytes"] == path.stat().st_size
        assert output["sha256"] == _sha256(path)


def test_cross_dataset_references_are_valid(tmp_path: Path) -> None:
    bundle = _generated_bundle(tmp_path)
    production = bundle["production_events"]
    inventory = bundle["inventory_levels"]
    sales = bundle["sales_orders"]
    quality = bundle["quality_checks"]
    equipment = bundle["equipment_health"]
    movements = bundle["warehouse_movements"]
    suppliers = bundle["supplier_performance"]

    plants = {record["plant_id"] for record in equipment}
    line_to_plant = {record["line_id"]: record["plant_id"] for record in equipment}
    machine_to_line = {record["machine_id"]: record["line_id"] for record in equipment}
    products = {record["product_id"] for record in production}
    batches = {record["batch_id"] for record in production}
    production_orders = {record["production_order_id"] for record in production}
    shifts = {record["shift_id"] for record in production}
    items = {record["item_id"] for record in inventory}
    warehouses = {record["warehouse_id"] for record in inventory}
    materials = {record["material_id"] for record in suppliers}
    supplier_ids = {record["supplier_id"] for record in suppliers}

    assert all(line_to_plant[line] in plants for line in line_to_plant)
    assert all(machine_to_line[machine] in line_to_plant for machine in machine_to_line)
    for record in production:
        assert record["plant_id"] in plants
        assert record["production_line_id"] in line_to_plant
        assert record["machine_id"] in machine_to_line
        assert record["product_id"] in products
        assert record["production_order_id"] in production_orders
        assert record["batch_id"] in batches
        assert record["shift_id"] in shifts
    for record in quality:
        assert record["batch_id"] in batches
        assert record["machine_id"] in machine_to_line
        assert record["product_id"] in products
    for record in sales:
        assert record["product_id"] in products
        assert record["customer_segment"]
        assert record["distribution_region"]
    for record in movements:
        assert record["warehouse_id"] in warehouses
        assert record["item_id"] in items
        assert record["reference_order"].startswith("REF-")
    assert all(record["material_id"] in materials for record in suppliers)
    assert all(record["supplier_id"] in supplier_ids for record in suppliers)


def test_domain_invariants_and_derived_fields(tmp_path: Path) -> None:
    bundle = _generated_bundle(tmp_path)

    for record in bundle["production_events"]:
        assert int(record["accepted_quantity"]) + int(record["rejected_quantity"]) == int(
            record["produced_quantity"]
        )

    for record in bundle["inventory_levels"]:
        on_hand = int(record["on_hand_quantity"])
        reserved = int(record["reserved_quantity"])
        unit_cost = float(record["unit_cost"])
        assert int(record["available_quantity"]) == on_hand - reserved
        assert float(record["inventory_value"]) == round(on_hand * unit_cost, 2)

    for record in bundle["sales_orders"]:
        ordered = int(record["ordered_quantity"])
        fulfilled = int(record["fulfilled_quantity"])
        assert fulfilled <= ordered
        assert float(record["order_value"]) == round(fulfilled * float(record["selling_price"]), 2)
        assert (
            record["order_date"]
            <= record["requested_delivery_date"]
            <= record["actual_delivery_date"]
        )
        expected_status = "fulfilled" if fulfilled == ordered else record["order_status"]
        assert record["order_status"] == expected_status or record["order_status"] == "backordered"

    for record in bundle["quality_checks"]:
        measured = float(record["measured_value"])
        lower = float(record["lower_specification_limit"])
        upper = float(record["upper_specification_limit"])
        passed = lower <= measured <= upper
        assert record["inspection_result"] == ("pass" if passed else "fail")
        assert int(record["defective_units"]) <= int(record["sample_size"])
        assert (record["defect_category"] == "") is passed

    for record in bundle["equipment_health"]:
        measurement = float(record["measurement"])
        warning = float(record["warning_threshold"])
        critical = float(record["critical_threshold"])
        assert record["threshold_status"] == _threshold_status(measurement, warning, critical)
        assert float(record["runtime_hours"]) >= 0
        assert float(record["service_hours_since_maintenance"]) >= 0
        assert 0 <= float(record["degradation_index"]) <= 1

    for record in bundle["warehouse_movements"]:
        assert int(record["quantity"]) > 0
        assert (
            record["movement_type"]
            in SCHEMAS["warehouse_movements"].categorical_domains["movement_type"]
        )
        assert record["movement_status"] == "completed"

    for record in bundle["supplier_performance"]:
        accepted = int(record["accepted_quantity"])
        rejected = int(record["rejected_quantity"])
        delivered = int(record["delivered_quantity"])
        ordered = int(record["ordered_quantity"])
        delay_days = _date_delta_days(record["actual_delivery_date"], record["promised_date"])
        assert accepted + rejected <= delivered
        assert int(record["delay_days"]) == delay_days
        assert _as_bool(record["on_time_flag"]) is (delay_days <= 0)
        assert _as_bool(record["in_full_flag"]) is (delivered >= ordered)
        assert record["delivery_status"] == _delivery_status(delay_days <= 0, delivered >= ordered)
        assert float(record["quality_score"]) == round(
            max(0.0, 100.0 - rejected / max(delivered, 1) * 100),
            2,
        )


def _generated_bundle(tmp_path: Path) -> dict[str, list[dict[str, str]] | list[dict[str, object]]]:
    generate_synthetic_data(output_dir=tmp_path)
    return {
        "production_events": _read_jsonl(tmp_path / "production_events.jsonl"),
        "inventory_levels": _read_csv(tmp_path / "inventory_levels.csv"),
        "sales_orders": _read_csv(tmp_path / "sales_orders.csv"),
        "quality_checks": _read_csv(tmp_path / "quality_checks.csv"),
        "equipment_health": _read_jsonl(tmp_path / "equipment_health.jsonl"),
        "warehouse_movements": _read_csv(tmp_path / "warehouse_movements.csv"),
        "supplier_performance": _read_csv(tmp_path / "supplier_performance.csv"),
    }


def _write_config_variant(tmp_path: Path, mutate: Callable[[dict[str, Any]], None]) -> Path:
    payload = yaml.safe_load((project_root() / "configs" / "synthetic_data.yaml").read_text())
    mutate(payload)
    path = tmp_path / "synthetic_data_variant.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _row_counts(result: Any) -> dict[str, int]:
    return {dataset.dataset_name: dataset.row_count for dataset in result.datasets}


def _hashes(result: Any) -> dict[str, str]:
    return {dataset.dataset_name: dataset.sha256 for dataset in result.datasets}


def _count_rows(path: Path, file_format: str) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        if file_format == "jsonl":
            return sum(1 for line in handle if line.strip())
        return max(0, sum(1 for _ in handle) - 1)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _threshold_status(measurement: float, warning: float, critical: float) -> str:
    if measurement >= critical:
        return "critical"
    if measurement >= warning:
        return "warning"
    return "normal"


def _date_delta_days(actual_date: str, promised_date: str) -> int:
    from datetime import date

    return (date.fromisoformat(actual_date) - date.fromisoformat(promised_date)).days


def _as_bool(value: str) -> bool:
    return value == "True"


def _delivery_status(on_time: bool, in_full: bool) -> str:
    if on_time and in_full:
        return "on_time_in_full"
    if on_time:
        return "on_time_short"
    if in_full:
        return "late_in_full"
    return "late_short"
