"""Domain-specific validation rules for synthetic manufacturing records."""

from __future__ import annotations

from datetime import date
from typing import Any

from manufacturing_intelligence.validation.result import LoadedRecord, ValidationIssue


def validate_domain_rules(loaded: LoadedRecord, ingestion_run_id: str) -> list[ValidationIssue]:
    """Validate dataset-specific invariants and derived fields."""
    dataset = loaded.dataset
    record = loaded.record
    if dataset == "production_events":
        return _validate_production(loaded, ingestion_run_id, record)
    if dataset == "inventory_levels":
        return _validate_inventory(loaded, ingestion_run_id, record)
    if dataset == "sales_orders":
        return _validate_sales(loaded, ingestion_run_id, record)
    if dataset == "quality_checks":
        return _validate_quality(loaded, ingestion_run_id, record)
    if dataset == "equipment_health":
        return _validate_equipment(loaded, ingestion_run_id, record)
    if dataset == "warehouse_movements":
        return _validate_warehouse(loaded, ingestion_run_id, record)
    if dataset == "supplier_performance":
        return _validate_supplier(loaded, ingestion_run_id, record)
    return []


def _validate_production(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    produced = _to_int(record.get("produced_quantity"))
    accepted = _to_int(record.get("accepted_quantity"))
    rejected = _to_int(record.get("rejected_quantity"))
    for field in (
        "planned_quantity",
        "produced_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "downtime_duration_minutes",
    ):
        if _to_float(record.get(field)) < 0:
            _append(issues, loaded, ingestion_run_id, field, "OUT_OF_RANGE", "Value is negative")
    if accepted + rejected != produced:
        issues.append(
            _issue(
                loaded,
                ingestion_run_id,
                "accepted_quantity",
                "INVALID_QUANTITY_RELATIONSHIP",
                "accepted_quantity plus rejected_quantity must equal produced_quantity",
            )
        )
    return issues


def _validate_inventory(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    on_hand = _to_int(record.get("on_hand_quantity"))
    reserved = _to_int(record.get("reserved_quantity"))
    available = _to_int(record.get("available_quantity"))
    unit_cost = _to_float(record.get("unit_cost"))
    if reserved > on_hand:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "reserved_quantity",
            "OUT_OF_RANGE",
            "Reserved exceeds on hand",
        )
    if available != on_hand - reserved:
        issues.append(
            _issue(
                loaded,
                ingestion_run_id,
                "available_quantity",
                "INVALID_DERIVED_FIELD",
                "available_quantity must equal on_hand_quantity minus reserved_quantity",
            )
        )
    if abs(_to_float(record.get("inventory_value")) - round(on_hand * unit_cost, 2)) > 0.000001:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "inventory_value",
            "INVALID_DERIVED_FIELD",
            "Inventory value is incorrect",
        )
    return issues


def _validate_sales(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    ordered = _to_int(record.get("ordered_quantity"))
    fulfilled = _to_int(record.get("fulfilled_quantity"))
    if fulfilled > ordered:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "fulfilled_quantity",
            "INVALID_QUANTITY_RELATIONSHIP",
            "Fulfilled exceeds ordered",
        )
    expected_order_value = round(fulfilled * _to_float(record.get("selling_price")), 2)
    if abs(_to_float(record.get("order_value")) - expected_order_value) > 0.000001:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "order_value",
            "INVALID_DERIVED_FIELD",
            "Order value is incorrect",
        )
    if str(record.get("requested_delivery_date")) < str(record.get("order_date")):
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "requested_delivery_date",
            "INVALID_DATE_RELATIONSHIP",
            "Requested date precedes order date",
        )
    return issues


def _validate_quality(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    lower = _to_float(record.get("lower_specification_limit"))
    upper = _to_float(record.get("upper_specification_limit"))
    measured = _to_float(record.get("measured_value"))
    sample_size = _to_int(record.get("sample_size"))
    defective = _to_int(record.get("defective_units"))
    if lower > upper:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "lower_specification_limit",
            "OUT_OF_RANGE",
            "Lower specification exceeds upper",
        )
    if sample_size <= 0 or defective < 0 or defective > sample_size:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "defective_units",
            "INVALID_QUANTITY_RELATIONSHIP",
            "Defective units are incoherent",
        )
    expected_result = "pass" if lower <= measured <= upper else "fail"
    if record.get("inspection_result") != expected_result:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "inspection_result",
            "INVALID_DERIVED_FIELD",
            "Inspection result is incorrect",
        )
    if expected_result == "pass" and record.get("defect_category") not in {"", None}:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "defect_category",
            "INVALID_DERIVED_FIELD",
            "Passing inspection has defect category",
        )
    return issues


def _validate_equipment(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    warning = _to_float(record.get("warning_threshold"))
    critical = _to_float(record.get("critical_threshold"))
    measurement = _to_float(record.get("measurement"))
    if warning >= critical:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "warning_threshold",
            "OUT_OF_RANGE",
            "Warning threshold must be below critical",
        )
    expected = _threshold_status(measurement, warning, critical)
    if record.get("threshold_status") != expected:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "threshold_status",
            "INVALID_DERIVED_FIELD",
            "Threshold status is incorrect",
        )
    if (
        _to_float(record.get("runtime_hours")) < 0
        or _to_float(record.get("service_hours_since_maintenance")) < 0
    ):
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "runtime_hours",
            "OUT_OF_RANGE",
            "Runtime values must be non-negative",
        )
    expected_unit = "mm_s" if record.get("sensor_type") == "vibration" else "celsius"
    if record.get("measurement_unit") != expected_unit:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "measurement_unit",
            "INVALID_UNIT",
            "Measurement unit does not match sensor type",
        )
    return issues


def _validate_warehouse(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    if _to_int(record.get("quantity")) <= 0:
        return [
            _issue(
                loaded,
                ingestion_run_id,
                "quantity",
                "OUT_OF_RANGE",
                "Movement quantity must be positive",
            )
        ]
    return []


def _validate_supplier(
    loaded: LoadedRecord, ingestion_run_id: str, record: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    ordered = _to_int(record.get("ordered_quantity"))
    delivered = _to_int(record.get("delivered_quantity"))
    accepted = _to_int(record.get("accepted_quantity"))
    rejected = _to_int(record.get("rejected_quantity"))
    if accepted + rejected > delivered:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "accepted_quantity",
            "INVALID_QUANTITY_RELATIONSHIP",
            "Accepted plus rejected exceeds delivered",
        )
    actual_delivery_date = date.fromisoformat(str(record.get("actual_delivery_date")))
    promised_date = date.fromisoformat(str(record.get("promised_date")))
    delay_days = (actual_delivery_date - promised_date).days
    if _to_int(record.get("delay_days")) != delay_days:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "delay_days",
            "INVALID_DERIVED_FIELD",
            "Delay days are incorrect",
        )
    on_time = delay_days <= 0
    in_full = delivered >= ordered
    if _to_bool(record.get("on_time_flag")) is not on_time:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "on_time_flag",
            "INVALID_DERIVED_FIELD",
            "On-time flag is incorrect",
        )
    if _to_bool(record.get("in_full_flag")) is not in_full:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "in_full_flag",
            "INVALID_DERIVED_FIELD",
            "In-full flag is incorrect",
        )
    expected_status = _delivery_status(on_time, in_full)
    if record.get("delivery_status") != expected_status:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "delivery_status",
            "INVALID_DERIVED_FIELD",
            "Delivery status is incorrect",
        )
    expected_quality = round(max(0.0, 100.0 - rejected / max(delivered, 1) * 100), 2)
    if abs(_to_float(record.get("quality_score")) - expected_quality) > 0.000001:
        _append(
            issues,
            loaded,
            ingestion_run_id,
            "quality_score",
            "INVALID_DERIVED_FIELD",
            "Quality score is incorrect",
        )
    return issues


def _issue(
    loaded: LoadedRecord, ingestion_run_id: str, field: str, rule_code: str, reason: str
) -> ValidationIssue:
    return ValidationIssue(
        dataset=loaded.dataset,
        source_path=loaded.source_path,
        source_row_number=loaded.source_row_number,
        record_id=loaded.record_id,
        field=field,
        rule_code=rule_code,
        severity="critical",
        reason=reason,
        original_value=loaded.record.get(field),
        ingestion_run_id=ingestion_run_id,
    )


def _append(
    issues: list[ValidationIssue],
    loaded: LoadedRecord,
    ingestion_run_id: str,
    field: str,
    rule_code: str,
    reason: str,
) -> None:
    issues.append(_issue(loaded, ingestion_run_id, field, rule_code, reason))


def _threshold_status(measurement: float, warning: float, critical: float) -> str:
    if measurement >= critical:
        return "critical"
    if measurement >= warning:
        return "warning"
    return "normal"


def _to_int(value: Any) -> int:
    return int(value)


def _to_float(value: Any) -> float:
    return float(value)


def _to_bool(value: Any) -> bool:
    return value is True or str(value) in {"True", "true"}


def _delivery_status(on_time: bool, in_full: bool) -> str:
    if on_time and in_full:
        return "on_time_in_full"
    if on_time:
        return "on_time_short"
    if in_full:
        return "late_in_full"
    return "late_short"
