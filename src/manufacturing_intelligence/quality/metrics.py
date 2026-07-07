"""Quality KPI and production-context metrics."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

KPI_GRAINS = [
    ("portfolio", []),
    ("plant", ["plant_id"]),
    ("line", ["plant_id", "production_line_id"]),
    ("machine", ["plant_id", "production_line_id", "machine_id"]),
    ("product", ["product_id"]),
    ("quality_metric", ["quality_metric"]),
]


def attach_production_context(observations: pd.DataFrame, production: pd.DataFrame) -> pd.DataFrame:
    """Attach production yield context by batch."""
    production_columns = [
        "batch_id",
        "event_id",
        "event_timestamp",
        "produced_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "cycle_time_seconds",
        "target_cycle_time_seconds",
        "downtime_duration_minutes",
        "operating_status",
    ]
    merged = observations.merge(
        production[production_columns],
        on="batch_id",
        how="left",
        validate="one_to_one",
    )
    merged["production_yield"] = safe_series_ratio(
        merged["accepted_quantity"], merged["produced_quantity"]
    )
    merged["first_pass_yield_proxy"] = merged["production_yield"]
    merged["first_pass_yield_method"] = "accepted_quantity_over_produced_quantity_proxy"
    merged["scrap_rate"] = safe_series_ratio(
        merged["rejected_quantity"], merged["produced_quantity"]
    )
    merged["cycle_time_ratio"] = safe_series_ratio(
        merged["cycle_time_seconds"], merged["target_cycle_time_seconds"]
    )
    return merged


def calculate_quality_kpis(observations: pd.DataFrame) -> pd.DataFrame:
    """Calculate deterministic quality KPIs at supported grains."""
    rows: list[dict[str, Any]] = []
    for grain_name, columns in KPI_GRAINS:
        if columns:
            grouped = observations.groupby(columns, dropna=False, sort=True)
            for keys, group in grouped:
                key_values = keys if isinstance(keys, tuple) else (keys,)
                row = _kpi_row(group, grain_name)
                for column, value in zip(columns, key_values, strict=True):
                    row[column] = value
                rows.append(row)
        else:
            rows.append(_kpi_row(observations, grain_name))
    return (
        pd.DataFrame(rows)
        .fillna("")
        .sort_values(
            [
                "grain_name",
                "plant_id",
                "production_line_id",
                "machine_id",
                "product_id",
                "quality_metric",
            ],
            ignore_index=True,
        )
    )


def _kpi_row(group: pd.DataFrame, grain_name: str) -> dict[str, Any]:
    inspection_count = len(group)
    passed = int((group["calculated_specification_result"] == "pass").sum())
    failed = int((group["calculated_specification_result"] == "fail").sum())
    sample_size = float(group["sample_size"].sum())
    defective_units = float(group["defective_units"].sum())
    produced = float(group["produced_quantity"].sum())
    accepted = float(group["accepted_quantity"].sum())
    rejected = float(group["rejected_quantity"].sum())
    severe = int(group["severity"].isin(["high", "critical"]).sum())
    critical = int((group["severity"] == "critical").sum())
    return {
        "grain_name": grain_name,
        "plant_id": "",
        "production_line_id": "",
        "machine_id": "",
        "product_id": "",
        "quality_metric": "",
        "inspection_count": inspection_count,
        "passed_inspection_count": passed,
        "failed_inspection_count": failed,
        "inspection_pass_rate": safe_number(passed / inspection_count if inspection_count else 0.0),
        "defect_rate": safe_number(failed / inspection_count if inspection_count else 0.0),
        "defective_unit_rate": safe_scalar_ratio(defective_units, sample_size),
        "sample_weighted_defect_rate": safe_scalar_ratio(defective_units, sample_size),
        "first_pass_yield_proxy": safe_scalar_ratio(accepted, produced),
        "first_pass_yield_method": "accepted_quantity_over_produced_quantity_proxy",
        "accepted_quantity": accepted,
        "rejected_quantity": rejected,
        "production_yield": safe_scalar_ratio(accepted, produced),
        "scrap_rate": safe_scalar_ratio(rejected, produced),
        "rework_related_indicator": "not_available",
        "specification_failure_count": failed,
        "near_limit_count": int(group["near_limit_flag"].sum()),
        "severe_defect_count": severe,
        "critical_defect_count": critical,
        "anomaly_count": int(group.get("combined_anomaly_flag", pd.Series(False)).sum()),
        "spc_signal_count": int(group.get("spc_signal_flag", pd.Series(False)).sum()),
    }


def safe_series_ratio(numerator: Any, denominator: Any) -> pd.Series:
    """Vectorised safe division."""
    return (numerator / pd.Series(denominator).replace(0, pd.NA)).fillna(0.0)


def safe_scalar_ratio(numerator: float, denominator: float) -> float:
    """Scalar safe division."""
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def safe_number(value: float) -> float:
    """Return a finite float."""
    return 0.0 if pd.isna(value) else float(value)
