"""Forecast Markdown reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def write_report(
    path: Path,
    *,
    forecast_run_id: str,
    selected: dict[str, Any],
    split_metadata: dict[str, str],
    model_comparison: pd.DataFrame,
    test_metrics: dict[str, Any],
    future_rows: int,
    limitation: str,
) -> None:
    """Write a deterministic Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Demand Forecasting Report",
        "",
        f"- Forecast run ID: `{forecast_run_id}`",
        f"- Selected model: `{selected['selected_model']}`",
        f"- Selection reason: {selected['selection_reason']}",
        f"- Forecast horizon rows: `{future_rows}`",
        f"- Held-out test WAPE: `{test_metrics.get('wape')}`",
        f"- Limitation: {limitation}",
        "",
        "## Split Dates",
        "",
    ]
    for key, value in split_metadata.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Validation Metrics",
            "",
            "| Model | WAPE | MAE | Bias |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    validation = model_comparison[model_comparison["split"] == "validation"]
    for row in validation.sort_values("model").itertuples(index=False):
        lines.append(f"| {row.model} | {row.wape} | {row.mae} | {row.bias} |")
    lines.extend(
        [
            "",
            "All data is synthetic. No Azure resources were deployed or called.",
            "Inventory optimisation is deferred to Milestone 5.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
