"""Defect Pareto calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

PARETO_DIMENSIONS = [
    "defect_category",
    "severity",
    "product_id",
    "plant_id",
    "production_line_id",
    "machine_id",
    "batch_id",
    "quality_metric",
]


def calculate_defect_pareto(observations: pd.DataFrame) -> pd.DataFrame:
    """Build deterministic Pareto rows for supported dimensions."""
    defects = observations[
        (observations["calculated_specification_result"] == "fail")
        | (observations["defective_units"] > 0)
    ].copy()
    defects["defect_category"] = defects["defect_category"].replace("", "unspecified")
    rows: list[dict[str, Any]] = []
    for dimension in PARETO_DIMENSIONS:
        grouped = (
            defects.groupby(dimension, dropna=False)
            .agg(
                defect_count=("inspection_id", "count"),
                defective_units=("defective_units", "sum"),
            )
            .reset_index()
            .rename(columns={dimension: "category_value"})
        )
        if grouped.empty:
            continue
        total = float(grouped["defect_count"].sum())
        grouped = grouped.sort_values(
            ["defect_count", "defective_units", "category_value"],
            ascending=[False, False, True],
            ignore_index=True,
        )
        grouped["percentage_of_total"] = grouped["defect_count"] / total
        grouped["cumulative_percentage"] = grouped["percentage_of_total"].cumsum()
        grouped["rank"] = range(1, len(grouped) + 1)
        grouped["dimension"] = dimension
        rows.extend(grouped.to_dict("records"))
    columns = [
        "dimension",
        "category_value",
        "defect_count",
        "defective_units",
        "percentage_of_total",
        "cumulative_percentage",
        "rank",
    ]
    return pd.DataFrame(rows, columns=columns)
