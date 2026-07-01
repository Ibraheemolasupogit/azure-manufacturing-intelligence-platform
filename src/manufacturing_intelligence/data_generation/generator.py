"""Deterministic synthetic manufacturing data generation."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError, DataContractError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path
from manufacturing_intelligence.data_generation.catalog import EntityCatalog, build_catalog
from manufacturing_intelligence.data_generation.schemas import SCHEMAS, DatasetSchema

JsonRecord = dict[str, str | int | float | bool]
CsvRecord = dict[str, str | int | float | bool]
SAFE_GENERATION_MODES = {"local_sample", "ci_smoke"}
METADATA_FILENAMES = ("schema_metadata.json", "generation_manifest.json", "generation_summary.md")


@dataclass(frozen=True)
class SyntheticDataConfig:
    """Configuration for Milestone 2 data generation."""

    schema_version: str
    config_version: str
    random_seed: int
    generation_timestamp: str
    start_date: date
    end_date: date
    timezone: str
    generation_mode: str
    overwrite_existing: bool
    config_source_path: Path
    days: int
    shifts_per_day: int
    probabilities: dict[str, float]
    catalog: EntityCatalog
    volumes: dict[str, int]


@dataclass(frozen=True)
class GeneratedDataset:
    """Metadata for one generated file."""

    dataset_name: str
    path: Path
    row_count: int
    sha256: str
    file_size_bytes: int


@dataclass(frozen=True)
class GenerationResult:
    """Summary of a complete deterministic generation run."""

    run_id: str
    raw_data_dir: Path
    datasets: tuple[GeneratedDataset, ...]
    manifest_path: Path
    schema_metadata_path: Path
    summary_path: Path


def generate_synthetic_data(
    *,
    config_path: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool | None = None,
) -> GenerationResult:
    """Generate all Milestone 2 synthetic source datasets."""
    config = load_synthetic_config(config_path)
    raw_data_dir = output_dir or resolve_project_path("data/raw")
    overwrite_enabled = config.overwrite_existing if overwrite is None else overwrite
    _ensure_generation_can_write(raw_data_dir, overwrite_enabled)
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(config.random_seed)
    run_id = _build_run_id(config)

    production_events = _generate_production_events(config, rng)
    datasets: dict[str, list[JsonRecord] | list[CsvRecord]] = {
        "production_events": production_events,
        "inventory_levels": _generate_inventory_levels(config, rng),
        "sales_orders": _generate_sales_orders(config, rng),
        "quality_checks": _generate_quality_checks(config, production_events, rng),
        "equipment_health": _generate_equipment_health(config, rng),
        "warehouse_movements": _generate_warehouse_movements(config, rng),
        "supplier_performance": _generate_supplier_performance(config, rng),
    }

    generated = tuple(
        _write_dataset(raw_data_dir, SCHEMAS[dataset_name], records)
        for dataset_name, records in datasets.items()
    )
    schema_metadata_path = _write_schema_metadata(raw_data_dir, config)
    manifest_path = _write_manifest(raw_data_dir, config, run_id, generated, schema_metadata_path)
    summary_path = _write_summary(raw_data_dir, config, run_id, generated)
    return GenerationResult(
        run_id=run_id,
        raw_data_dir=raw_data_dir,
        datasets=generated,
        manifest_path=manifest_path,
        schema_metadata_path=schema_metadata_path,
        summary_path=summary_path,
    )


def validate_generated_run(output_dir: Path | None = None) -> None:
    """Validate an existing generated run without regenerating files."""
    raw_data_dir = output_dir or resolve_project_path("data/raw")
    manifest_path = raw_data_dir / "generation_manifest.json"
    schema_metadata_path = raw_data_dir / "schema_metadata.json"
    summary_path = raw_data_dir / "generation_summary.md"
    for path in (manifest_path, schema_metadata_path, summary_path):
        if not path.is_file():
            raise DataContractError(f"Required metadata file is missing: {path}")

    manifest = _read_json_file(manifest_path)
    schema_metadata = _read_json_file(schema_metadata_path)
    if manifest.get("status") != "success":
        raise DataContractError("generation_manifest.status must be success")
    if manifest.get("synthetic_data_only") is not True:
        raise DataContractError("generation_manifest.synthetic_data_only must be true")
    for required_key in (
        "schema_version",
        "configuration_hash",
        "random_seed",
        "date_range",
        "timezone",
        "generation_mode",
    ):
        if required_key not in manifest:
            raise DataContractError(f"generation_manifest missing required key: {required_key}")
    if manifest.get("generation_mode") not in SAFE_GENERATION_MODES:
        raise DataContractError("generation_manifest.generation_mode is unsupported")
    if set(schema_metadata.get("datasets", {})) != set(SCHEMAS):
        raise DataContractError("schema_metadata datasets do not match schema registry")

    _reject_absolute_paths(manifest)
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise DataContractError("generation_manifest.outputs must be a mapping")
    missing_outputs = sorted(set(SCHEMAS) - set(outputs))
    if missing_outputs:
        raise DataContractError(f"generation_manifest.outputs missing: {missing_outputs}")

    for dataset_name, schema in SCHEMAS.items():
        output_metadata = outputs.get(dataset_name)
        if not isinstance(output_metadata, dict):
            raise DataContractError(f"Missing manifest metadata for {dataset_name}")
        path_value = output_metadata.get("path")
        if not isinstance(path_value, str):
            raise DataContractError(f"Manifest path missing for {dataset_name}")
        path = _resolve_manifest_output_path(raw_data_dir, path_value)
        if path.name != schema.filename or not path.is_file():
            raise DataContractError(f"Expected dataset file is missing: {schema.filename}")
        actual_rows = _count_rows(path, schema.file_format)
        if output_metadata.get("row_count") != actual_rows:
            raise DataContractError(f"Manifest row count mismatch for {dataset_name}")
        if output_metadata.get("sha256") != _sha256(path):
            raise DataContractError(f"Manifest SHA-256 mismatch for {dataset_name}")
        if output_metadata.get("file_size_bytes") != path.stat().st_size:
            raise DataContractError(f"Manifest file size mismatch for {dataset_name}")
        if output_metadata.get("file_format") != schema.file_format:
            raise DataContractError(f"Manifest file format mismatch for {dataset_name}")


def load_synthetic_config(config_path: Path | None = None) -> SyntheticDataConfig:
    """Load and validate the synthetic data generation configuration."""
    path = config_path or project_root() / "configs" / "synthetic_data.yaml"
    if not path.is_file():
        raise ConfigurationError(f"Synthetic data config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Synthetic data config must contain a mapping.")

    generation = _section(payload, "generation")
    entities = _section(payload, "entities")
    volumes = _section(payload, "volumes")
    probabilities = _section(payload, "probabilities")
    regions = tuple(_required_str_list(entities, "regions"))
    customer_segments = tuple(_required_str_list(entities, "customer_segments"))
    catalog = build_catalog(
        plant_count=_required_positive_int(entities, "plants"),
        lines_per_plant=_required_positive_int(entities, "lines_per_plant"),
        machines_per_line=_required_positive_int(entities, "machines_per_line"),
        product_count=_required_positive_int(entities, "products"),
        material_count=_required_positive_int(entities, "materials"),
        warehouse_count=_required_positive_int(entities, "warehouses"),
        supplier_count=_required_positive_int(entities, "suppliers"),
        customer_segments=customer_segments,
        regions=regions,
    )
    parsed_volumes = {
        key: _required_positive_int(volumes, key)
        for key in (
            "production_events_per_line_shift",
            "sales_orders",
            "inventory_snapshots_per_item_warehouse",
            "quality_checks_per_production_event",
            "equipment_health_readings_per_machine_day",
            "warehouse_movements",
            "supplier_purchase_orders",
        )
    }
    parsed_probabilities = {
        key: _required_probability(probabilities, key)
        for key in ("quality_defect", "supplier_delay", "sales_backorder")
    }
    start_date = date.fromisoformat(_required_str(generation, "start_date"))
    end_date = date.fromisoformat(_required_str(generation, "end_date"))
    if end_date < start_date:
        raise ConfigurationError("Synthetic data config end_date must be on or after start_date")
    timezone = _required_str(generation, "timezone")
    generation_mode = _required_str(generation, "generation_mode")
    if generation_mode not in SAFE_GENERATION_MODES:
        raise ConfigurationError(
            f"Synthetic data config generation_mode is unsupported: {generation_mode}"
        )
    return SyntheticDataConfig(
        schema_version=_required_str(generation, "schema_version"),
        config_version=_required_str(generation, "config_version"),
        random_seed=_required_positive_int(generation, "random_seed"),
        generation_timestamp=_required_str(generation, "generation_timestamp"),
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        generation_mode=generation_mode,
        overwrite_existing=_required_bool(generation, "overwrite_existing"),
        config_source_path=path.resolve(),
        days=(end_date - start_date).days + 1,
        shifts_per_day=_required_positive_int(generation, "shifts_per_day"),
        probabilities=parsed_probabilities,
        catalog=catalog,
        volumes=parsed_volumes,
    )


def _generate_production_events(
    config: SyntheticDataConfig, rng: random.Random
) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    event_index = 1
    machines_by_line = {
        line_id: [machine for machine in config.catalog.machines if machine.line_id == line_id]
        for line_id in config.catalog.lines
    }
    for day_offset in range(config.days):
        current_date = config.start_date + timedelta(days=day_offset)
        for shift_number in range(1, config.shifts_per_day + 1):
            timestamp = _timestamp(current_date, 6 + (shift_number - 1) * 8)
            for line_id in config.catalog.lines:
                for _ in range(config.volumes["production_events_per_line_shift"]):
                    line_machines = machines_by_line[line_id]
                    machine = line_machines[(event_index - 1) % len(line_machines)]
                    product = config.catalog.products[
                        (event_index + day_offset) % len(config.catalog.products)
                    ]
                    planned = 95 + rng.randint(0, 35)
                    downtime = rng.choice((0, 0, 5, 10, 15, 25, 40))
                    produced = max(0, planned - rng.randint(0, 18) - downtime // 5)
                    rejected = min(produced, rng.choice((0, 1, 2, 3, 5, 8)))
                    accepted = produced - rejected
                    cycle_time = round(
                        product.target_cycle_time_seconds * rng.uniform(0.92, 1.18),
                        2,
                    )
                    records.append(
                        {
                            "event_id": f"PE-{event_index:06d}",
                            "event_timestamp": timestamp,
                            "plant_id": machine.plant_id,
                            "production_line_id": machine.line_id,
                            "machine_id": machine.machine_id,
                            "product_id": product.product_id,
                            "production_order_id": (
                                f"PO-{current_date:%Y%m%d}-"
                                f"{line_id.replace('-', '')}-{shift_number}"
                            ),
                            "batch_id": (
                                f"BATCH-PO-{current_date:%Y%m%d}-"
                                f"{line_id.replace('-', '')}-{shift_number}"
                            ),
                            "shift_id": f"{current_date:%Y%m%d}-S{shift_number}",
                            "planned_quantity": planned,
                            "produced_quantity": produced,
                            "accepted_quantity": accepted,
                            "rejected_quantity": rejected,
                            "cycle_time_seconds": cycle_time,
                            "target_cycle_time_seconds": product.target_cycle_time_seconds,
                            "downtime_duration_minutes": downtime,
                            "event_type": "production_run",
                            "operating_status": _operating_status(downtime, produced, planned),
                        }
                    )
                    event_index += 1
    return records


def _generate_inventory_levels(config: SyntheticDataConfig, rng: random.Random) -> list[CsvRecord]:
    records: list[CsvRecord] = []
    snapshot_timestamp = _timestamp(config.start_date + timedelta(days=config.days), 0)
    items = [
        (product.product_id, "product", product.unit_price, None)
        for product in config.catalog.products
    ] + [
        (material.material_id, material.material_type, material.unit_cost, material.shelf_life_days)
        for material in config.catalog.materials
    ]
    for warehouse_index, warehouse_id in enumerate(config.catalog.warehouses):
        plant_id = config.catalog.plants[warehouse_index % len(config.catalog.plants)]
        for item_index, (item_id, item_type, unit_cost, shelf_life_days) in enumerate(
            items,
            start=1,
        ):
            for _ in range(config.volumes["inventory_snapshots_per_item_warehouse"]):
                reorder_point = 90 + (item_index % 6) * 15
                safety_stock = 45 + (item_index % 5) * 10
                on_hand = reorder_point + rng.randint(-45, 180)
                reserved = max(0, int(on_hand * rng.uniform(0.05, 0.35)))
                available = max(0, on_hand - reserved)
                inventory_value = round(on_hand * unit_cost, 2)
                expiry_date = ""
                if shelf_life_days is not None:
                    expiry_date = (config.start_date + timedelta(days=shelf_life_days)).isoformat()
                records.append(
                    {
                        "snapshot_timestamp": snapshot_timestamp,
                        "warehouse_id": warehouse_id,
                        "plant_id": plant_id,
                        "item_id": item_id,
                        "product_or_material_type": item_type,
                        "on_hand_quantity": on_hand,
                        "reserved_quantity": reserved,
                        "available_quantity": available,
                        "reorder_point": reorder_point,
                        "safety_stock_quantity": safety_stock,
                        "lead_time_days": 4 + (item_index % 9),
                        "unit_cost": unit_cost,
                        "inventory_value": inventory_value,
                        "expiry_date": expiry_date,
                    }
                )
    return records


def _generate_sales_orders(config: SyntheticDataConfig, rng: random.Random) -> list[CsvRecord]:
    records: list[CsvRecord] = []
    for index in range(1, config.volumes["sales_orders"] + 1):
        order_date = config.start_date + timedelta(days=(index - 1) % config.days)
        product = config.catalog.products[(index - 1) % len(config.catalog.products)]
        ordered = 20 + rng.randint(0, 180)
        fulfilment_gap = rng.choice((0, 0, 0, 3, 8, 15, 25))
        fulfilled = max(0, ordered - fulfilment_gap)
        status = "fulfilled" if fulfilled == ordered else "partially_fulfilled"
        if rng.random() < config.probabilities["sales_backorder"]:
            status = "backordered"
            fulfilled = max(0, ordered - 35)
        requested_delivery_date = order_date + timedelta(days=5 + index % 8)
        actual_delivery_date = requested_delivery_date
        if status == "backordered":
            actual_delivery_date = requested_delivery_date + timedelta(days=3)
        records.append(
            {
                "order_id": f"SO-{index:06d}",
                "order_date": order_date.isoformat(),
                "requested_delivery_date": requested_delivery_date.isoformat(),
                "actual_delivery_date": actual_delivery_date.isoformat(),
                "customer_segment": config.catalog.customer_segments[
                    (index - 1) % len(config.catalog.customer_segments)
                ],
                "product_id": product.product_id,
                "ordered_quantity": ordered,
                "fulfilled_quantity": fulfilled,
                "selling_price": product.unit_price,
                "order_value": round(fulfilled * product.unit_price, 2),
                "distribution_region": config.catalog.regions[
                    (index - 1) % len(config.catalog.regions)
                ],
                "order_status": status,
            }
        )
    return records


def _generate_quality_checks(
    config: SyntheticDataConfig,
    production_events: list[JsonRecord],
    rng: random.Random,
) -> list[CsvRecord]:
    records: list[CsvRecord] = []
    for index, event in enumerate(production_events, start=1):
        for check_index in range(config.volumes["quality_checks_per_production_event"]):
            metric = ("diameter_mm", "surface_finish_ra", "torque_nm")[(index + check_index) % 3]
            lower, upper, target = _quality_limits(metric)
            drift = rng.uniform(-0.7, 0.7)
            if rng.random() < config.probabilities["quality_defect"]:
                drift += rng.choice((-1.8, 1.8))
            measured = round(target + drift, 3)
            passed = lower <= measured <= upper
            records.append(
                {
                    "inspection_id": f"QC-{index:06d}-{check_index + 1}",
                    "inspection_timestamp": str(event["event_timestamp"]),
                    "plant_id": str(event["plant_id"]),
                    "line_id": str(event["production_line_id"]),
                    "machine_id": str(event["machine_id"]),
                    "batch_id": str(event["batch_id"]),
                    "product_id": str(event["product_id"]),
                    "quality_metric": metric,
                    "sample_size": 20,
                    "defective_units": 0 if passed else rng.randint(1, 3),
                    "measured_value": measured,
                    "lower_specification_limit": lower,
                    "upper_specification_limit": upper,
                    "inspection_result": "pass" if passed else "fail",
                    "defect_category": "" if passed else _defect_category(metric),
                    "severity": "none" if passed else ("high" if abs(drift) > 1.5 else "medium"),
                }
            )
    return records


def _generate_equipment_health(config: SyntheticDataConfig, rng: random.Random) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    sensor_specs = (
        ("vibration", "mm_s", 6.5, 8.0),
        ("temperature", "celsius", 78.0, 90.0),
    )
    event_index = 1
    for day_offset in range(config.days):
        current_date = config.start_date + timedelta(days=day_offset)
        for machine in config.catalog.machines:
            for reading_index in range(config.volumes["equipment_health_readings_per_machine_day"]):
                sensor_type, unit, warning, critical = sensor_specs[
                    reading_index % len(sensor_specs)
                ]
                baseline = 4.2 if sensor_type == "vibration" else 64.0
                measurement = round(baseline + rng.uniform(-0.9, 2.8) + (day_offset % 5) * 0.18, 3)
                if event_index % 53 == 0:
                    measurement = round(critical + rng.uniform(0.2, 1.4), 3)
                threshold_status = _threshold_status(measurement, warning, critical)
                runtime_hours = round(day_offset * 16 + reading_index * 8 + rng.uniform(0, 2), 2)
                service_hours = round(80 + day_offset * 12 + (event_index % 17), 2)
                degradation_index = round(min(1.0, measurement / critical), 4)
                records.append(
                    {
                        "sensor_event_id": f"EH-{event_index:06d}",
                        "timestamp": _timestamp(current_date, 2 + reading_index * 10),
                        "plant_id": machine.plant_id,
                        "line_id": machine.line_id,
                        "machine_id": machine.machine_id,
                        "sensor_id": f"SENS-{machine.machine_id}-{sensor_type.upper()}",
                        "sensor_type": sensor_type,
                        "measurement": measurement,
                        "measurement_unit": unit,
                        "warning_threshold": warning,
                        "critical_threshold": critical,
                        "threshold_status": threshold_status,
                        "runtime_hours": runtime_hours,
                        "service_hours_since_maintenance": service_hours,
                        "degradation_index": degradation_index,
                        "operating_mode": "production" if reading_index == 1 else "standby",
                        "maintenance_state": _maintenance_state(measurement, warning, critical),
                    }
                )
                event_index += 1
    return records


def _generate_warehouse_movements(
    config: SyntheticDataConfig,
    rng: random.Random,
) -> list[CsvRecord]:
    records: list[CsvRecord] = []
    item_ids = tuple(product.product_id for product in config.catalog.products) + tuple(
        material.material_id for material in config.catalog.materials
    )
    movement_types = ("receipt", "issue_to_production", "transfer", "adjustment")
    for index in range(1, config.volumes["warehouse_movements"] + 1):
        movement_date = config.start_date + timedelta(days=(index - 1) % config.days)
        movement_type = movement_types[(index - 1) % len(movement_types)]
        warehouse = config.catalog.warehouses[(index - 1) % len(config.catalog.warehouses)]
        records.append(
            {
                "movement_id": f"WM-{index:06d}",
                "movement_timestamp": _timestamp(movement_date, index % 24),
                "warehouse_id": warehouse,
                "source_location": f"{warehouse}-A{(index % 9) + 1:02d}",
                "destination_location": f"{warehouse}-B{(index % 7) + 1:02d}",
                "item_id": item_ids[(index - 1) % len(item_ids)],
                "quantity": 5 + rng.randint(0, 95),
                "movement_type": movement_type,
                "movement_status": "completed",
                "reference_order": f"REF-{movement_type.upper()}-{index:06d}",
                "operator_or_automated_system_id": f"SYS-{(index % 5) + 1:02d}",
            }
        )
    return records


def _generate_supplier_performance(
    config: SyntheticDataConfig,
    rng: random.Random,
) -> list[CsvRecord]:
    records: list[CsvRecord] = []
    for index in range(1, config.volumes["supplier_purchase_orders"] + 1):
        supplier = config.catalog.suppliers[(index - 1) % len(config.catalog.suppliers)]
        material = config.catalog.materials[(index - 1) % len(config.catalog.materials)]
        order_date = config.start_date + timedelta(days=(index - 1) % config.days)
        shelf_life_buffer_days = 1 if material.shelf_life_days is not None else 0
        promised_date = order_date + timedelta(days=shelf_life_buffer_days + 5 + index % 6)
        delay = (
            rng.choice((1, 2, 4)) if rng.random() < config.probabilities["supplier_delay"] else 0
        )
        actual_delivery_date = promised_date + timedelta(days=delay)
        ordered = 100 + rng.randint(0, 500)
        delivered = max(0, ordered - rng.choice((0, 0, 0, 10, 25, 50)))
        rejected = min(delivered, rng.choice((0, 0, 2, 5, 12, 20)))
        accepted = delivered - rejected
        on_time_flag = actual_delivery_date <= promised_date
        in_full_flag = delivered >= ordered
        records.append(
            {
                "supplier_id": supplier.supplier_id,
                "material_id": material.material_id,
                "purchase_order_id": f"PO-SUP-{index:06d}",
                "order_date": order_date.isoformat(),
                "promised_date": promised_date.isoformat(),
                "actual_delivery_date": actual_delivery_date.isoformat(),
                "delay_days": delay,
                "on_time_flag": on_time_flag,
                "in_full_flag": in_full_flag,
                "ordered_quantity": ordered,
                "delivered_quantity": delivered,
                "accepted_quantity": accepted,
                "rejected_quantity": rejected,
                "unit_price": material.unit_cost,
                "quality_score": round(max(0.0, 100.0 - rejected / max(delivered, 1) * 100), 2),
                "supplier_region": supplier.region,
                "delivery_status": _delivery_status(
                    actual_delivery_date,
                    promised_date,
                    delivered,
                    ordered,
                ),
            }
        )
    return records


def _write_dataset(
    raw_data_dir: Path,
    schema: DatasetSchema,
    records: list[JsonRecord] | list[CsvRecord],
) -> GeneratedDataset:
    path = raw_data_dir / schema.filename
    if schema.file_format == "jsonl":
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True))
                handle.write("\n")
    else:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(schema.fields), lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    return GeneratedDataset(
        dataset_name=schema.dataset_name,
        path=path,
        row_count=len(records),
        sha256=_sha256(path),
        file_size_bytes=path.stat().st_size,
    )


def _write_schema_metadata(raw_data_dir: Path, config: SyntheticDataConfig) -> Path:
    path = raw_data_dir / "schema_metadata.json"
    payload = {
        "schema_version": config.schema_version,
        "synthetic_data_only": True,
        "datasets": {
            name: {
                "dataset_name": schema.dataset_name,
                "schema_version": schema.schema_version,
                "filename": schema.filename,
                "file_format": schema.file_format,
                "primary_key": list(schema.primary_key),
                "fields": list(schema.fields),
                "data_types": schema.data_types,
                "nullable_fields": list(schema.nullable_fields),
                "categorical_domains": {
                    field_name: list(values)
                    for field_name, values in schema.categorical_domains.items()
                },
                "timestamp_fields": list(schema.timestamp_fields),
                "units": schema.units,
                "relationships": schema.relationships,
                "invariants": list(schema.invariants),
                "logical_owner": schema.logical_owner,
                "synthetic_data_classification": schema.synthetic_data_classification,
            }
            for name, schema in SCHEMAS.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_manifest(
    raw_data_dir: Path,
    config: SyntheticDataConfig,
    run_id: str,
    datasets: tuple[GeneratedDataset, ...],
    schema_metadata_path: Path,
) -> Path:
    path = raw_data_dir / "generation_manifest.json"
    payload = {
        "run_id": run_id,
        "pipeline_name": "synthetic_data_generation",
        "configuration_version": config.config_version,
        "schema_version": config.schema_version,
        "software_version": "0.1.0",
        "random_seed": config.random_seed,
        "configuration_hash": _sha256(config.config_source_path),
        "date_range": {
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
        },
        "timezone": config.timezone,
        "generation_mode": config.generation_mode,
        "generation_timestamp": config.generation_timestamp,
        "synthetic_data_only": True,
        "input_paths": [_portable_path(config.config_source_path)],
        "output_paths": [_manifest_path(raw_data_dir, dataset.path) for dataset in datasets]
        + [_manifest_path(raw_data_dir, schema_metadata_path)],
        "outputs": {
            dataset.dataset_name: {
                "path": _manifest_path(raw_data_dir, dataset.path),
                "file_format": SCHEMAS[dataset.dataset_name].file_format,
                "row_count": dataset.row_count,
                "file_size_bytes": dataset.file_size_bytes,
                "sha256": dataset.sha256,
            }
            for dataset in datasets
        },
        "schema_metadata": {
            "path": _manifest_path(raw_data_dir, schema_metadata_path),
            "sha256": _sha256(schema_metadata_path),
        },
        "status": "success",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_summary(
    raw_data_dir: Path,
    config: SyntheticDataConfig,
    run_id: str,
    datasets: tuple[GeneratedDataset, ...],
) -> Path:
    path = raw_data_dir / "generation_summary.md"
    lines = [
        "# Synthetic Data Generation Summary",
        "",
        f"- Run ID: `{run_id}`",
        f"- Configuration version: `{config.config_version}`",
        f"- Schema version: `{config.schema_version}`",
        f"- Random seed: `{config.random_seed}`",
        f"- Date range: `{config.start_date.isoformat()}` to `{config.end_date.isoformat()}`",
        f"- Timezone: `{config.timezone}`",
        f"- Generation mode: `{config.generation_mode}`",
        f"- Generation timestamp: `{config.generation_timestamp}`",
        "- Data classification: synthetic only",
        "",
        "| Dataset | Rows | File | SHA-256 |",
        "| --- | ---: | --- | --- |",
    ]
    for dataset in datasets:
        lines.append(
            f"| {dataset.dataset_name} | {dataset.row_count} | "
            f"`{dataset.path.name}` | `{dataset.sha256}` |"
        )
    lines.extend(
        [
            "",
            "No records represent real people, customers, suppliers, employees, plants, products, "
            "or commercial operations.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _build_run_id(config: SyntheticDataConfig) -> str:
    payload = (
        f"{config.config_version}|{config.schema_version}|{config.random_seed}|"
        f"{config.start_date.isoformat()}|{config.end_date.isoformat()}|"
        f"{config.timezone}|{config.generation_mode}"
    )
    return f"synthetic-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _manifest_path(raw_data_dir: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        return resolved.relative_to(raw_data_dir.resolve()).as_posix()


def _ensure_generation_can_write(raw_data_dir: Path, overwrite_enabled: bool) -> None:
    if raw_data_dir.exists() and not raw_data_dir.is_dir():
        raise ConfigurationError(f"Output path is not a directory: {raw_data_dir}")
    expected = [raw_data_dir / schema.filename for schema in SCHEMAS.values()]
    expected.extend(raw_data_dir / filename for filename in METADATA_FILENAMES)
    existing = [path for path in expected if path.exists()]
    if existing and not overwrite_enabled:
        paths = ", ".join(path.name for path in existing)
        raise DataContractError(
            "Synthetic generation would overwrite existing files. "
            f"Pass overwrite=True or --overwrite to replace: {paths}"
        )


def _read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DataContractError(f"JSON metadata must contain an object: {path}")
    return payload


def _reject_absolute_paths(manifest: dict[str, Any]) -> None:
    paths: list[str] = []
    output_paths = manifest.get("output_paths", [])
    if isinstance(output_paths, list):
        paths.extend(path for path in output_paths if isinstance(path, str))
    outputs = manifest.get("outputs", {})
    if isinstance(outputs, dict):
        for output_metadata in outputs.values():
            if isinstance(output_metadata, dict) and isinstance(output_metadata.get("path"), str):
                paths.append(output_metadata["path"])
    schema_metadata = manifest.get("schema_metadata", {})
    if isinstance(schema_metadata, dict) and isinstance(schema_metadata.get("path"), str):
        paths.append(schema_metadata["path"])
    absolute_paths = [path for path in paths if Path(path).is_absolute()]
    if absolute_paths:
        raise DataContractError(f"Manifest contains absolute paths: {absolute_paths}")


def _resolve_manifest_output_path(raw_data_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    repo_path = resolve_project_path(path)
    if repo_path.exists():
        return repo_path
    return raw_data_dir / path


def _count_rows(path: Path, file_format: str) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        if file_format == "jsonl":
            return sum(1 for line in handle if line.strip())
        return max(0, sum(1 for _ in handle) - 1)


def _timestamp(day: date, hour: int) -> str:
    return (
        datetime(day.year, day.month, day.day, hour % 24, tzinfo=UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _operating_status(downtime: int, produced: int, planned: int) -> str:
    if downtime >= 25:
        return "degraded"
    if produced < planned * 0.85:
        return "under_target"
    return "running"


def _quality_limits(metric: str) -> tuple[float, float, float]:
    limits = {
        "diameter_mm": (9.5, 10.5, 10.0),
        "surface_finish_ra": (0.2, 1.6, 0.8),
        "torque_nm": (45.0, 55.0, 50.0),
    }
    return limits[metric]


def _defect_category(metric: str) -> str:
    return {
        "diameter_mm": "dimensional_variance",
        "surface_finish_ra": "surface_finish",
        "torque_nm": "assembly_torque",
    }[metric]


def _maintenance_state(measurement: float, warning: float, critical: float) -> str:
    if measurement >= critical:
        return "critical_inspection_required"
    if measurement >= warning:
        return "warning_monitor"
    return "normal"


def _threshold_status(measurement: float, warning: float, critical: float) -> str:
    if measurement >= critical:
        return "critical"
    if measurement >= warning:
        return "warning"
    return "normal"


def _delivery_status(
    actual_delivery_date: date,
    promised_date: date,
    delivered_quantity: int,
    ordered_quantity: int,
) -> str:
    on_time = actual_delivery_date <= promised_date
    in_full = delivered_quantity >= ordered_quantity
    if on_time and in_full:
        return "on_time_in_full"
    if on_time:
        return "on_time_short"
    if in_full:
        return "late_in_full"
    return "late_short"


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Synthetic data config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Synthetic data config string missing or invalid: {key}")
    return value


def _required_positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigurationError(
            f"Synthetic data config positive integer missing or invalid: {key}"
        )
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Synthetic data config boolean missing or invalid: {key}")
    return value


def _required_probability(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, int | float) or not 0 <= float(value) <= 1:
        raise ConfigurationError(f"Synthetic data config probability outside 0-1: {key}")
    return float(value)


def _required_str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Synthetic data config string list missing or invalid: {key}")
    return value
