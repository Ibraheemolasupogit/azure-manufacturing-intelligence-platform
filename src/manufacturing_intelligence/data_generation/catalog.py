"""Deterministic synthetic entity catalog shared across datasets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Machine:
    """Production machine tied to one plant and line."""

    plant_id: str
    line_id: str
    machine_id: str


@dataclass(frozen=True)
class Product:
    """Synthetic product metadata."""

    product_id: str
    product_family: str
    unit_price: float
    target_cycle_time_seconds: int


@dataclass(frozen=True)
class Material:
    """Synthetic material metadata."""

    material_id: str
    material_type: str
    unit_cost: float
    shelf_life_days: int | None


@dataclass(frozen=True)
class Supplier:
    """Synthetic supplier metadata."""

    supplier_id: str
    region: str
    reliability_score: float


@dataclass(frozen=True)
class EntityCatalog:
    """Shared entity lists used to maintain cross-dataset consistency."""

    plants: tuple[str, ...]
    lines: tuple[str, ...]
    machines: tuple[Machine, ...]
    products: tuple[Product, ...]
    materials: tuple[Material, ...]
    warehouses: tuple[str, ...]
    suppliers: tuple[Supplier, ...]
    customer_segments: tuple[str, ...]
    regions: tuple[str, ...]


def build_catalog(
    *,
    plant_count: int,
    lines_per_plant: int,
    machines_per_line: int,
    product_count: int,
    material_count: int,
    warehouse_count: int,
    supplier_count: int,
    customer_segments: tuple[str, ...],
    regions: tuple[str, ...],
) -> EntityCatalog:
    """Build stable synthetic IDs without relying on external state."""
    plants = tuple(f"PLANT-{index:02d}" for index in range(1, plant_count + 1))
    lines = tuple(
        f"LINE-{plant_index:02d}-{line_index:02d}"
        for plant_index in range(1, plant_count + 1)
        for line_index in range(1, lines_per_plant + 1)
    )
    machines = tuple(
        Machine(
            plant_id=f"PLANT-{plant_index:02d}",
            line_id=f"LINE-{plant_index:02d}-{line_index:02d}",
            machine_id=f"MACH-{plant_index:02d}-{line_index:02d}-{machine_index:02d}",
        )
        for plant_index in range(1, plant_count + 1)
        for line_index in range(1, lines_per_plant + 1)
        for machine_index in range(1, machines_per_line + 1)
    )
    families = ("gearbox", "pump", "sensor", "valve")
    products = tuple(
        Product(
            product_id=f"PROD-{index:03d}",
            product_family=families[(index - 1) % len(families)],
            unit_price=round(85.0 + index * 13.75, 2),
            target_cycle_time_seconds=42 + (index % 5) * 6,
        )
        for index in range(1, product_count + 1)
    )
    material_types = ("steel", "aluminium", "electronics", "polymer", "packaging")
    materials = tuple(
        Material(
            material_id=f"MAT-{index:03d}",
            material_type=material_types[(index - 1) % len(material_types)],
            unit_cost=round(8.5 + index * 2.4, 2),
            shelf_life_days=(
                180 if material_types[(index - 1) % len(material_types)] == "polymer" else None
            ),
        )
        for index in range(1, material_count + 1)
    )
    warehouses = tuple(f"WH-{index:02d}" for index in range(1, warehouse_count + 1))
    suppliers = tuple(
        Supplier(
            supplier_id=f"SUP-{index:03d}",
            region=regions[(index - 1) % len(regions)],
            reliability_score=round(0.78 + (index % 5) * 0.04, 2),
        )
        for index in range(1, supplier_count + 1)
    )
    return EntityCatalog(
        plants=plants,
        lines=lines,
        machines=machines,
        products=products,
        materials=materials,
        warehouses=warehouses,
        suppliers=suppliers,
        customer_segments=customer_segments,
        regions=regions,
    )
