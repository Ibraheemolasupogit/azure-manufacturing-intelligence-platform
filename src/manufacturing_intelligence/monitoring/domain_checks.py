"""Domain-level monitoring table builders."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]


def pipeline_health(
    manifests: dict[str, dict[str, Any]], domain_scores: pd.DataFrame
) -> pd.DataFrame:
    """Build pipeline health table."""
    rows = []
    run_ids = {
        "generation": manifests["generation"].get("run_id"),
        "ingestion": manifests["ingestion"].get("ingestion_run_id"),
        "forecasting": manifests["forecasting"].get("forecast_run_id"),
        "inventory": manifests["inventory"].get("inventory_run_id"),
        "quality": manifests["quality"].get("quality_run_id"),
        "maintenance": manifests["maintenance"].get("maintenance_run_id"),
    }
    for record in domain_scores.to_dict("records"):
        domain = str(record["domain"])
        manifest = manifests["validation"] if domain == "ingestion" else manifests.get(domain, {})
        rows.append(
            {
                "domain": domain,
                "run_id": run_ids.get(domain, ""),
                "validation_status": manifest.get(
                    "validation_status", manifest.get("status", "success")
                ),
                "health_score": record["health_score"],
                "health_label": record["health_label"],
                "warning_count": len(manifest.get("warnings", []))
                if isinstance(manifest.get("warnings", []), list)
                else 0,
                "synthetic_data_flag": True,
            }
        )
    return pd.DataFrame(rows).sort_values("domain", ignore_index=True)


def data_quality_monitoring(manifests: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build data-quality monitoring table."""
    validation = manifests["validation"]
    rows = []
    accepted = validation.get("accepted_counts_by_dataset", {})
    quarantine = validation.get("quarantine_counts_by_dataset", {})
    for dataset in sorted(accepted):
        rows.append(
            {
                "dataset": dataset,
                "accepted_count": int(accepted.get(dataset, 0)),
                "quarantine_count": int(quarantine.get(dataset, 0)),
                "quarantine_rate": 0.0
                if int(accepted.get(dataset, 0)) == 0
                else int(quarantine.get(dataset, 0)) / int(accepted.get(dataset, 1)),
                "validation_status": validation.get("validation_status", "unknown"),
                "synthetic_data_flag": bool(validation.get("synthetic_data_confirmation", False)),
            }
        )
    return pd.DataFrame(rows)


def model_and_analytics_monitoring(manifests: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build model and analytics monitoring table."""
    rows = []
    forecast = manifests["forecasting"]
    rows.append(
        {
            "domain": "forecasting",
            "selected_model": forecast.get("selected_model", ""),
            "row_count": forecast.get("output_files", {})
            .get("demand_forecast", {})
            .get("row_count", 0),
            "warning_count": len(forecast.get("warnings", [])),
            "indicator": "forecast_horizon_and_model_documented",
        }
    )
    inventory = manifests["inventory"]
    rows.append(
        {
            "domain": "inventory",
            "selected_model": "rules_based_inventory_policy",
            "row_count": inventory.get("scored_row_count", 0),
            "warning_count": len(inventory.get("warnings", [])),
            "indicator": "inventory_risk_and_scenario_outputs_present",
        }
    )
    quality = manifests["quality"]
    rows.append(
        {
            "domain": "quality",
            "selected_model": "robust_zscore;isolation_forest;spc_rules",
            "row_count": quality.get("kpi_summary", {}).get("quality_records_processed", 0),
            "warning_count": len(quality.get("warnings", [])),
            "indicator": "quality_alert_and_anomaly_outputs_present",
        }
    )
    maintenance = manifests["maintenance"]
    rows.append(
        {
            "domain": "maintenance",
            "selected_model": "robust_zscore;isolation_forest;heuristic_failure_risk",
            "row_count": maintenance.get("kpi_summary", {}).get("equipment_records_processed", 0),
            "warning_count": len(maintenance.get("warnings", [])),
            "indicator": "maintenance_alert_and_risk_outputs_present",
        }
    )
    return pd.DataFrame(rows).sort_values("domain", ignore_index=True)
