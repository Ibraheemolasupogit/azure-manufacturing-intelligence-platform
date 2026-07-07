"""Inventory intelligence and optimisation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.inventory.config import InventoryConfig, load_inventory_config
from manufacturing_intelligence.inventory.data import (
    InventoryInputEvidence,
    load_governed_inventory_inputs,
)
from manufacturing_intelligence.inventory.lineage import lineage_record
from manufacturing_intelligence.inventory.manifest import (
    git_commit,
    inventory_run_id,
    manifest_hash,
    semantic_config_hash,
)
from manufacturing_intelligence.inventory.policy import (
    InventoryCalculations,
    run_policy_calculations,
)
from manufacturing_intelligence.inventory.reporting import write_report, write_scenario_report
from manufacturing_intelligence.inventory.serialization import file_evidence, write_csv, write_json


@dataclass(frozen=True)
class InventoryResult:
    """Inventory pipeline result."""

    inventory_run_id: str
    output_directory: Path
    scored_rows: int
    recommendation_rows: int


def run_inventory(
    config_path: Path | None = None,
    *,
    inventory_path: Path | None = None,
    forecast_path: Path | None = None,
    output_directory: Path | None = None,
    planning_horizon: int | None = None,
    budget: float | None = None,
    capacity: int | None = None,
    overwrite: bool = False,
) -> InventoryResult:
    """Run deterministic governed inventory intelligence."""
    config = _with_overrides(
        load_inventory_config(config_path),
        inventory_path=inventory_path,
        forecast_path=forecast_path,
        output_directory=output_directory,
        planning_horizon=planning_horizon,
        budget=budget,
        capacity=capacity,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    inputs = load_governed_inventory_inputs(config)
    stable_inputs = {
        **inputs.evidence.input_hashes,
        "ingestion_manifest": manifest_hash(config.inventory.ingestion_manifest_path),
        "forecast_manifest": manifest_hash(config.inventory.forecast_manifest_path),
    }
    run_id = inventory_run_id(config, stable_inputs)
    calculations = run_policy_calculations(
        inventory_run_id=run_id,
        config=config,
        inventory=inputs.inventory,
        suppliers=inputs.suppliers,
        movements=inputs.warehouse_movements,
        sales_orders=inputs.sales_orders,
        forecast=inputs.forecast,
    )
    _publish_outputs(config, run_id, inputs.evidence, calculations)
    return InventoryResult(
        inventory_run_id=run_id,
        output_directory=config.inventory.output_directory,
        scored_rows=len(calculations.scores),
        recommendation_rows=len(calculations.recommendations),
    )


def _publish_outputs(
    config: InventoryConfig,
    run_id: str,
    evidence: InventoryInputEvidence,
    calculations: InventoryCalculations,
) -> None:
    output_dir = config.inventory.output_directory
    write_csv(output_dir / "warehouse_demand_forecast.csv", calculations.warehouse_demand)
    write_csv(output_dir / "supplier_risk_metrics.csv", calculations.supplier_risk)
    write_csv(output_dir / "inventory_policy_inputs.csv", calculations.policy_inputs)
    write_csv(output_dir / "inventory_position.csv", calculations.inventory_position)
    write_csv(output_dir / "inventory_scores.csv", calculations.scores)
    write_csv(output_dir / "inventory_health.csv", calculations.scores)
    write_csv(output_dir / "reorder_recommendations.csv", calculations.recommendations)
    write_csv(output_dir / "scenario_results.csv", calculations.scenarios)
    write_csv(output_dir / "scenario_comparison.csv", calculations.scenarios)
    summary = _summary(calculations)
    write_json(output_dir / "inventory_summary.json", summary)
    write_json(output_dir / "inventory_diagnostics.json", calculations.diagnostics)
    write_csv(config.inventory.inventory_scores_path, calculations.scores)
    evidence_base = output_dir.parent
    output_files = {
        "warehouse_demand_forecast": file_evidence(
            output_dir / "warehouse_demand_forecast.csv", base_directory=evidence_base
        ),
        "supplier_risk_metrics": file_evidence(
            output_dir / "supplier_risk_metrics.csv", base_directory=evidence_base
        ),
        "inventory_policy_inputs": file_evidence(
            output_dir / "inventory_policy_inputs.csv", base_directory=evidence_base
        ),
        "inventory_position": file_evidence(
            output_dir / "inventory_position.csv", base_directory=evidence_base
        ),
        "inventory_scores": file_evidence(
            output_dir / "inventory_scores.csv", base_directory=evidence_base
        ),
        "portfolio_inventory_scores": file_evidence(
            config.inventory.inventory_scores_path, base_directory=evidence_base
        ),
        "inventory_health": file_evidence(
            output_dir / "inventory_health.csv", base_directory=evidence_base
        ),
        "reorder_recommendations": file_evidence(
            output_dir / "reorder_recommendations.csv", base_directory=evidence_base
        ),
        "scenario_results": file_evidence(
            output_dir / "scenario_results.csv", base_directory=evidence_base
        ),
        "scenario_comparison": file_evidence(
            output_dir / "scenario_comparison.csv", base_directory=evidence_base
        ),
        "inventory_summary": file_evidence(
            output_dir / "inventory_summary.json", None, base_directory=evidence_base
        ),
        "inventory_diagnostics": file_evidence(
            output_dir / "inventory_diagnostics.json", None, base_directory=evidence_base
        ),
    }
    manifest = _manifest(config, run_id, evidence, calculations, summary, output_files)
    write_json(output_dir / "inventory-manifest.json", manifest)
    output_files["inventory_manifest"] = file_evidence(
        output_dir / "inventory-manifest.json", None, base_directory=evidence_base
    )
    lineage = _lineage(config, run_id, evidence, output_files)
    write_json(output_dir / "lineage-records.json", lineage)
    if config.reporting.write_inventory_report:
        write_report(
            config.inventory.report_directory / "inventory_intelligence_report.md",
            inventory_run_id=run_id,
            scores=calculations.scores,
            recommendations=calculations.recommendations,
            summary=summary,
            maximum_recommendations=config.reporting.maximum_recommendation_examples,
        )
    if config.reporting.write_scenario_comparison:
        write_scenario_report(
            config.inventory.report_directory / "inventory_scenario_summary.md",
            inventory_run_id=run_id,
            scenarios=calculations.scenarios,
        )


def _summary(calculations: InventoryCalculations) -> dict[str, Any]:
    scores = calculations.scores
    recommendations = calculations.recommendations
    return {
        "row_count": len(scores),
        "item_count": int(scores["item_id"].nunique()),
        "warehouse_count": int(scores["warehouse_id"].nunique()),
        "product_record_count": int((scores["item_type"] == "product").sum()),
        "material_record_count": int((scores["item_type"] == "material").sum()),
        "recommendation_row_count": len(recommendations),
        "high_risk_count": int((scores["priority_level"] == "high").sum()),
        "critical_risk_count": int((scores["priority_level"] == "critical").sum()),
        "total_unconstrained_quantity": float(
            recommendations["unconstrained_reorder_quantity"].sum()
        ),
        "total_constrained_quantity": float(recommendations["recommended_reorder_quantity"].sum()),
        "total_recommended_value": float(recommendations["recommended_reorder_value"].sum()),
        "total_working_capital_exposure": float(scores["working_capital_exposure"].sum()),
        "projected_shortage_quantity": float(scores["projected_shortage_quantity"].sum()),
        "projected_excess_quantity": float(scores["projected_excess_quantity"].sum()),
        "budget_utilisation": float(calculations.diagnostics["budget_utilisation"]),
        "capacity_utilisation": float(calculations.diagnostics["capacity_utilisation"]),
    }


def _manifest(
    config: InventoryConfig,
    run_id: str,
    evidence: InventoryInputEvidence,
    calculations: InventoryCalculations,
    summary: dict[str, Any],
    output_files: dict[str, Any],
) -> dict[str, Any]:
    return {
        "inventory_run_id": run_id,
        "pipeline_name": "inventory_intelligence",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "input_paths": {
            "inventory_levels": relative_path(config.inventory.inventory_path),
            "supplier_performance": relative_path(config.inventory.supplier_path),
            "warehouse_movements": relative_path(config.inventory.movements_path),
            "sales_orders": relative_path(config.inventory.sales_orders_path),
            "demand_forecast": relative_path(config.inventory.forecast_path),
        },
        "governed_input_hashes": evidence.input_hashes,
        "governed_input_row_counts": evidence.input_row_counts,
        "upstream_ingestion_run_id": evidence.upstream_ingestion_run_id,
        "upstream_forecast_run_id": evidence.upstream_forecast_run_id,
        "upstream_ingestion_manifest_sha256": manifest_hash(
            config.inventory.ingestion_manifest_path
        ),
        "upstream_forecast_manifest_sha256": manifest_hash(config.inventory.forecast_manifest_path),
        "decision_grain": list(config.inventory.decision_grain),
        "planning_horizon_days": config.inventory.planning_horizon_days,
        "scored_row_count": len(calculations.scores),
        "recommendation_row_count": len(calculations.recommendations),
        "policy_parameters": config.policy.__dict__,
        "scenario_parameters": config.scenarios.__dict__,
        "constrained_allocation": {
            "method": config.optimisation.method,
            "available_budget": config.optimisation.available_budget,
            "available_replenishment_capacity": (
                config.optimisation.available_replenishment_capacity
            ),
            "objective_weights": config.optimisation.objective_weights,
            "solver_claim": "deterministic greedy allocation; not exact global optimisation",
        },
        "output_files": output_files,
        "metrics_summary": summary,
        "validation_status": "success",
        "warnings": [
            "Material inventory health uses warehouse movement usage because no BOM exists.",
            "Tracked forecast history is a short synthetic smoke sample.",
        ],
        "synthetic_data_classification": evidence.synthetic_classification,
        "git_commit": git_commit(),
        "governed_inputs_modified": False,
        "azure_mapping": {
            "batch_scoring": "Azure Machine Learning batch scoring responsibility",
            "analytical_preparation": "Synapse Analytics or Microsoft Fabric responsibility",
            "recommendation_service": "Azure Functions or Container Apps responsibility",
            "lineage": "Microsoft Purview responsibility",
            "operations": "Azure Monitor responsibility",
            "dashboard_extracts": "Power BI-ready outputs responsibility",
            "deployment_status": "reference-only; no Azure services deployed or called",
        },
    }


def _lineage(
    config: InventoryConfig,
    run_id: str,
    evidence: InventoryInputEvidence,
    output_files: dict[str, Any],
) -> list[dict[str, Any]]:
    sources = {
        "accepted_inventory": {
            "path": relative_path(config.inventory.inventory_path),
            "sha256": evidence.input_hashes["inventory_levels"],
            "row_count": evidence.input_row_counts["inventory_levels"],
        },
        "accepted_supplier_performance": {
            "path": relative_path(config.inventory.supplier_path),
            "sha256": evidence.input_hashes["supplier_performance"],
            "row_count": evidence.input_row_counts["supplier_performance"],
        },
        "accepted_warehouse_movements": {
            "path": relative_path(config.inventory.movements_path),
            "sha256": evidence.input_hashes["warehouse_movements"],
            "row_count": evidence.input_row_counts["warehouse_movements"],
        },
        "accepted_sales_orders": {
            "path": relative_path(config.inventory.sales_orders_path),
            "sha256": evidence.input_hashes["sales_orders"],
            "row_count": evidence.input_row_counts["sales_orders"],
        },
        "governed_demand_forecast": {
            "path": relative_path(config.inventory.forecast_path),
            "sha256": evidence.input_hashes["demand_forecast"],
            "row_count": evidence.input_row_counts["demand_forecast"],
        },
    }
    config_hash = semantic_config_hash(config)
    return [
        lineage_record(
            inventory_run_id=run_id,
            upstream_ingestion_run_id=evidence.upstream_ingestion_run_id,
            upstream_forecast_run_id=evidence.upstream_forecast_run_id,
            source_inputs=sources,
            target=target,
            transformation_name=name,
            configuration_hash=config_hash,
        )
        for name, target in output_files.items()
    ]


def _with_overrides(
    config: InventoryConfig,
    *,
    inventory_path: Path | None,
    forecast_path: Path | None,
    output_directory: Path | None,
    planning_horizon: int | None,
    budget: float | None,
    capacity: int | None,
    overwrite: bool,
) -> InventoryConfig:
    inventory = config.inventory
    optimisation = config.optimisation
    resolved_output = output_directory.resolve() if output_directory else inventory.output_directory
    scores_path = (
        resolved_output / "inventory_scores.csv"
        if output_directory
        else inventory.inventory_scores_path
    )
    report_directory = (
        resolved_output / "reports" if output_directory else inventory.report_directory
    )
    return InventoryConfig(
        config_path=config.config_path,
        inventory=type(inventory)(
            inventory_path=inventory_path.resolve() if inventory_path else inventory.inventory_path,
            supplier_path=inventory.supplier_path,
            movements_path=inventory.movements_path,
            sales_orders_path=inventory.sales_orders_path,
            forecast_path=forecast_path.resolve() if forecast_path else inventory.forecast_path,
            ingestion_manifest_path=inventory.ingestion_manifest_path,
            validation_summary_path=inventory.validation_summary_path,
            data_quality_report_path=inventory.data_quality_report_path,
            ingestion_lineage_path=inventory.ingestion_lineage_path,
            forecast_manifest_path=inventory.forecast_manifest_path,
            forecast_model_metadata_path=inventory.forecast_model_metadata_path,
            forecast_lineage_path=inventory.forecast_lineage_path,
            output_directory=resolved_output,
            inventory_scores_path=scores_path,
            report_directory=report_directory,
            overwrite=overwrite or inventory.overwrite,
            random_seed=inventory.random_seed,
            decision_grain=inventory.decision_grain,
            planning_horizon_days=planning_horizon or inventory.planning_horizon_days,
        ),
        policy=config.policy,
        optimisation=type(optimisation)(
            enabled=optimisation.enabled,
            method=optimisation.method,
            available_budget=budget if budget is not None else optimisation.available_budget,
            available_replenishment_capacity=(
                capacity if capacity is not None else optimisation.available_replenishment_capacity
            ),
            objective_weights=optimisation.objective_weights,
        ),
        scenarios=config.scenarios,
        reporting=config.reporting,
    )


def _ensure_can_write(config: InventoryConfig) -> None:
    managed_paths = [
        config.inventory.output_directory,
        config.inventory.inventory_scores_path,
        config.inventory.report_directory / "inventory_intelligence_report.md",
        config.inventory.report_directory / "inventory_scenario_summary.md",
    ]
    if config.inventory.overwrite:
        return
    existing = [path for path in managed_paths if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Inventory outputs already exist: {existing}")


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    if value.startswith("/"):
        return path.name
    return value
