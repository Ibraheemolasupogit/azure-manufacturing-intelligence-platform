"""Cross-dataset relationship validation."""

from __future__ import annotations

from dataclasses import dataclass

from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


@dataclass(frozen=True)
class ReferenceIndexes:
    """Reference sets derived from the complete source run."""

    plants: frozenset[str]
    lines: frozenset[str]
    machines: frozenset[str]
    products: frozenset[str]
    batches: frozenset[str]
    shifts: frozenset[str]
    warehouses: frozenset[str]
    items: frozenset[str]
    suppliers: frozenset[str]
    materials: frozenset[str]


def build_reference_indexes(
    records_by_dataset: dict[str, tuple[LoadedRecord, ...]],
) -> ReferenceIndexes:
    """Build all indexes before validating relationships."""
    production = records_by_dataset.get("production_events", ())
    inventory = records_by_dataset.get("inventory_levels", ())
    equipment = records_by_dataset.get("equipment_health", ())
    suppliers = records_by_dataset.get("supplier_performance", ())
    return ReferenceIndexes(
        plants=frozenset(str(record.record.get("plant_id")) for record in equipment),
        lines=frozenset(str(record.record.get("line_id")) for record in equipment),
        machines=frozenset(str(record.record.get("machine_id")) for record in equipment),
        products=frozenset(str(record.record.get("product_id")) for record in production),
        batches=frozenset(str(record.record.get("batch_id")) for record in production),
        shifts=frozenset(str(record.record.get("shift_id")) for record in production),
        warehouses=frozenset(str(record.record.get("warehouse_id")) for record in inventory),
        items=frozenset(str(record.record.get("item_id")) for record in inventory),
        suppliers=frozenset(str(record.record.get("supplier_id")) for record in suppliers),
        materials=frozenset(str(record.record.get("material_id")) for record in suppliers),
    )


def validate_relationships(
    loaded: LoadedRecord,
    indexes: ReferenceIndexes,
    ingestion_run_id: str,
) -> list[ValidationIssue]:
    """Validate record references against complete-run indexes."""
    record = loaded.record
    issues: list[ValidationIssue] = []
    if loaded.dataset == "production_events":
        checks = {
            "plant_id": indexes.plants,
            "production_line_id": indexes.lines,
            "machine_id": indexes.machines,
            "product_id": indexes.products,
            "batch_id": indexes.batches,
            "shift_id": indexes.shifts,
        }
    elif loaded.dataset == "quality_checks":
        checks = {
            "plant_id": indexes.plants,
            "line_id": indexes.lines,
            "machine_id": indexes.machines,
            "product_id": indexes.products,
            "batch_id": indexes.batches,
        }
    elif loaded.dataset == "equipment_health":
        checks = {
            "plant_id": indexes.plants,
            "line_id": indexes.lines,
            "machine_id": indexes.machines,
        }
    elif loaded.dataset == "inventory_levels":
        checks = {
            "warehouse_id": indexes.warehouses,
            "plant_id": indexes.plants,
            "item_id": indexes.items,
        }
    elif loaded.dataset == "sales_orders":
        checks = {"product_id": indexes.products}
    elif loaded.dataset == "warehouse_movements":
        checks = {"warehouse_id": indexes.warehouses, "item_id": indexes.items}
    elif loaded.dataset == "supplier_performance":
        checks = {"supplier_id": indexes.suppliers, "material_id": indexes.materials}
    else:
        checks = {}
    for field, allowed_values in checks.items():
        if str(record.get(field)) not in allowed_values:
            issues.append(
                ValidationIssue(
                    dataset=loaded.dataset,
                    source_path=loaded.source_path,
                    source_row_number=loaded.source_row_number,
                    record_id=loaded.record_id,
                    field=field,
                    rule_code="INVALID_REFERENCE",
                    severity="critical",
                    reason=f"{field} does not resolve to a known source entity",
                    original_value=record.get(field),
                    ingestion_run_id=ingestion_run_id,
                )
            )
    return issues
