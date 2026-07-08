"""Predictive maintenance and equipment failure-risk pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.maintenance.anomalies import calculate_anomaly_scores
from manufacturing_intelligence.maintenance.config import MaintenanceConfig, load_maintenance_config
from manufacturing_intelligence.maintenance.data import (
    MaintenanceInputEvidence,
    load_maintenance_inputs,
    verify_upstream_unchanged,
)
from manufacturing_intelligence.maintenance.degradation import calculate_degradation_features
from manufacturing_intelligence.maintenance.lineage import lineage_record
from manufacturing_intelligence.maintenance.manifest import (
    git_commit,
    maintenance_run_id,
    manifest_hash,
    semantic_config_hash,
)
from manufacturing_intelligence.maintenance.reporting import (
    write_alert_summary,
    write_maintenance_report,
)
from manufacturing_intelligence.maintenance.scoring import build_alerts, score_maintenance_risk
from manufacturing_intelligence.maintenance.serialization import (
    file_evidence,
    write_csv,
    write_json,
)
from manufacturing_intelligence.maintenance.summaries import (
    machine_summary,
    risk_summary,
    sensor_summary,
)
from manufacturing_intelligence.maintenance.thresholds import evaluate_thresholds


@dataclass(frozen=True)
class MaintenanceResult:
    """Maintenance pipeline result."""

    maintenance_run_id: str
    output_directory: Path
    equipment_rows: int
    alert_rows: int


@dataclass(frozen=True)
class MaintenanceTables:
    """Maintenance output tables."""

    features: pd.DataFrame
    scores: pd.DataFrame
    alerts: pd.DataFrame
    machine_summary: pd.DataFrame
    sensor_summary: pd.DataFrame
    degradation_signals: pd.DataFrame
    anomaly_scores: pd.DataFrame
    risk_summary: pd.DataFrame
    diagnostics: dict[str, Any]


def run_maintenance(
    config_path: Path | None = None,
    *,
    equipment_health_path: Path | None = None,
    production_events_path: Path | None = None,
    output_directory: Path | None = None,
    overwrite: bool = False,
) -> MaintenanceResult:
    """Run deterministic governed predictive maintenance."""
    config = _with_overrides(
        load_maintenance_config(config_path),
        equipment_health_path=equipment_health_path,
        production_events_path=production_events_path,
        output_directory=output_directory,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    inputs = load_maintenance_inputs(config)
    stable_inputs = {
        **inputs.evidence.input_hashes,
        "ingestion_manifest": manifest_hash(config.maintenance.ingestion_manifest_path),
    }
    if inputs.evidence.quality_manifest_sha256:
        stable_inputs["quality_manifest"] = inputs.evidence.quality_manifest_sha256
    run_id = maintenance_run_id(config, stable_inputs)
    tables = _calculate_tables(
        config,
        run_id,
        inputs.equipment_health,
        inputs.production_events,
        inputs.quality_checks,
        inputs.quality_alerts,
    )
    verify_upstream_unchanged(config, inputs.evidence)
    _publish_outputs(config, run_id, inputs.evidence, tables)
    return MaintenanceResult(
        maintenance_run_id=run_id,
        output_directory=config.maintenance.output_directory,
        equipment_rows=len(tables.features),
        alert_rows=len(tables.alerts),
    )


def _calculate_tables(
    config: MaintenanceConfig,
    run_id: str,
    equipment: pd.DataFrame,
    production: pd.DataFrame,
    quality: pd.DataFrame,
    quality_alerts: pd.DataFrame,
) -> MaintenanceTables:
    thresholded = evaluate_thresholds(equipment, config.thresholds)
    contextual = _attach_context(thresholded, production, quality, quality_alerts)
    degradation = calculate_degradation_features(contextual, config.degradation)
    features = contextual.merge(degradation, on="sensor_event_id", how="left")
    anomaly = calculate_anomaly_scores(
        features,
        config.anomaly_detection,
        random_seed=config.maintenance.random_seed,
    )
    features = features.merge(anomaly, on="sensor_event_id", how="left")
    features["maintenance_run_id"] = run_id
    scored = score_maintenance_risk(features, config.risk_scoring)
    alerts = build_alerts(scored, run_id)
    machines = machine_summary(scored, alerts)
    sensors = sensor_summary(scored)
    risks = risk_summary(scored)
    diagnostics = _diagnostics(scored, anomaly, alerts, quality, production)
    degradation_signals = scored[
        [
            "sensor_event_id",
            "event_timestamp",
            "machine_id",
            "sensor_type",
            "measurement_unit",
            "degradation_status",
            "degradation_slope",
            "degradation_score",
            "degradation_signal_flag",
            "degradation_reason",
        ]
    ].copy()
    return MaintenanceTables(
        features=scored,
        scores=scored[_score_columns()].copy(),
        alerts=alerts,
        machine_summary=machines,
        sensor_summary=sensors,
        degradation_signals=degradation_signals,
        anomaly_scores=anomaly,
        risk_summary=risks,
        diagnostics=diagnostics,
    )


def _attach_context(
    equipment: pd.DataFrame,
    production: pd.DataFrame,
    quality: pd.DataFrame,
    quality_alerts: pd.DataFrame,
) -> pd.DataFrame:
    frame = equipment.copy()
    prod = production.copy()
    prod["event_date"] = prod["event_timestamp"].dt.date.astype(str)
    prod_context = prod.groupby(["machine_id", "event_date"], sort=True).agg(
        recent_downtime_minutes=("downtime_duration_minutes", "sum"),
        recent_produced_quantity=("produced_quantity", "sum"),
        recent_rejected_quantity=("rejected_quantity", "sum"),
        recent_production_event_count=("event_id", "count"),
    )
    prod_context = prod_context.reset_index()
    frame = frame.merge(prod_context, on=["machine_id", "event_date"], how="left")
    for column in [
        "recent_downtime_minutes",
        "recent_produced_quantity",
        "recent_rejected_quantity",
        "recent_production_event_count",
    ]:
        frame[column] = frame[column].fillna(0)
    produced = frame["recent_produced_quantity"].astype(float)
    rejected = frame["recent_rejected_quantity"].astype(float)
    frame["recent_reject_rate"] = (rejected / produced.where(produced > 0)).fillna(0.0)
    if not quality.empty:
        quality_context = quality.groupby("machine_id", sort=True).agg(
            quality_check_count_for_machine=("inspection_id", "count"),
            quality_failure_count_for_machine=(
                "inspection_result",
                lambda series: int((series == "fail").sum()),
            ),
        )
        frame = frame.merge(quality_context.reset_index(), on="machine_id", how="left")
    else:
        frame["quality_check_count_for_machine"] = 0
        frame["quality_failure_count_for_machine"] = 0
    if not quality_alerts.empty:
        alert_context = (
            quality_alerts.groupby("machine_id", sort=True)
            .size()
            .rename("quality_alert_count_for_machine")
        )
        frame = frame.merge(alert_context.reset_index(), on="machine_id", how="left")
    else:
        frame["quality_alert_count_for_machine"] = 0
    for column in [
        "quality_check_count_for_machine",
        "quality_failure_count_for_machine",
        "quality_alert_count_for_machine",
    ]:
        frame[column] = frame[column].fillna(0).astype(int)
    frame["service_interval_proxy_hours"] = 120.0
    frame["service_overdue_indicator"] = (
        frame["service_hours_since_maintenance"] > frame["service_interval_proxy_hours"]
    )
    frame["utilisation_intensity"] = (frame["runtime_hours"] / frame["runtime_hours"].max()).fillna(
        0
    )
    return frame


def _publish_outputs(
    config: MaintenanceConfig,
    run_id: str,
    evidence: MaintenanceInputEvidence,
    tables: MaintenanceTables,
) -> None:
    output_dir = config.maintenance.output_directory
    write_csv(output_dir / "equipment_health_features.csv", tables.features)
    write_csv(output_dir / "equipment_health_scores.csv", tables.scores)
    write_csv(output_dir / "maintenance_alerts.csv", tables.alerts)
    write_csv(output_dir / "machine_health_summary.csv", tables.machine_summary)
    write_csv(output_dir / "sensor_health_summary.csv", tables.sensor_summary)
    write_csv(output_dir / "degradation_signals.csv", tables.degradation_signals)
    write_csv(output_dir / "anomaly_scores.csv", tables.anomaly_scores)
    write_csv(output_dir / "maintenance_risk_summary.csv", tables.risk_summary)
    write_json(output_dir / "maintenance_diagnostics.json", tables.diagnostics)
    write_maintenance_report(
        config.maintenance.report_directory / "maintenance_analytics_report.md",
        maintenance_run_id=run_id,
        summary=_summary(tables),
        top_alerts=tables.alerts,
        max_alerts=config.recommendations.maximum_alert_examples,
    )
    write_alert_summary(
        config.maintenance.report_directory / "maintenance_alert_summary.md",
        maintenance_run_id=run_id,
        alerts=tables.alerts,
    )
    write_json(config.maintenance.portfolio_predictions_path, _portfolio_projection(run_id, tables))

    base = output_dir.parent
    outputs = {
        "equipment_health_features": file_evidence(
            output_dir / "equipment_health_features.csv", base_directory=base
        ),
        "equipment_health_scores": file_evidence(
            output_dir / "equipment_health_scores.csv", base_directory=base
        ),
        "maintenance_alerts": file_evidence(
            output_dir / "maintenance_alerts.csv", base_directory=base
        ),
        "machine_health_summary": file_evidence(
            output_dir / "machine_health_summary.csv", base_directory=base
        ),
        "sensor_health_summary": file_evidence(
            output_dir / "sensor_health_summary.csv", base_directory=base
        ),
        "degradation_signals": file_evidence(
            output_dir / "degradation_signals.csv", base_directory=base
        ),
        "anomaly_scores": file_evidence(output_dir / "anomaly_scores.csv", base_directory=base),
        "maintenance_risk_summary": file_evidence(
            output_dir / "maintenance_risk_summary.csv", base_directory=base
        ),
        "maintenance_diagnostics": file_evidence(
            output_dir / "maintenance_diagnostics.json", None, base_directory=base
        ),
        "maintenance_analytics_report": file_evidence(
            config.maintenance.report_directory / "maintenance_analytics_report.md",
            None,
            base_directory=base,
        ),
        "maintenance_alert_summary": file_evidence(
            config.maintenance.report_directory / "maintenance_alert_summary.md",
            None,
            base_directory=base,
        ),
        "portfolio_maintenance_predictions": file_evidence(
            config.maintenance.portfolio_predictions_path,
            None,
            base_directory=base,
        ),
    }
    manifest = _manifest(config, run_id, evidence, tables, outputs)
    write_json(output_dir / "maintenance-manifest.json", manifest)
    outputs["maintenance_manifest"] = file_evidence(
        output_dir / "maintenance-manifest.json", None, base_directory=base
    )
    write_json(output_dir / "lineage-records.json", _lineage(config, run_id, evidence, outputs))


def _summary(tables: MaintenanceTables) -> dict[str, Any]:
    scored = tables.features
    alerts = tables.alerts
    return {
        "equipment_records_processed": len(scored),
        "machines_represented": int(scored["machine_id"].nunique()),
        "sensors_represented": int(scored["sensor_id"].nunique()),
        "sensor_types_represented": int(scored["sensor_type"].nunique()),
        "warning_breach_count": int(scored["warning_breach_flag"].sum()),
        "critical_breach_count": int(scored["critical_breach_flag"].sum()),
        "near_threshold_observations": int(scored["near_threshold_flag"].sum()),
        "threshold_status_inconsistency_count": int((~scored["threshold_consistency_flag"]).sum()),
        "degradation_signal_count": int(scored["degradation_signal_flag"].sum()),
        "robust_z_anomaly_count": int(scored["robust_zscore_anomaly_flag"].sum()),
        "isolation_forest_anomaly_count": int(scored["isolation_forest_anomaly_flag"].sum()),
        "alert_count": len(alerts),
        "high_risk_alert_count": int((alerts["risk_level"] == "high").sum()),
        "critical_risk_alert_count": int((alerts["risk_level"] == "critical").sum()),
    }


def _diagnostics(
    scored: pd.DataFrame,
    anomaly: pd.DataFrame,
    alerts: pd.DataFrame,
    quality: pd.DataFrame,
    production: pd.DataFrame,
) -> dict[str, Any]:
    summary = _summary(
        MaintenanceTables(
            features=scored,
            scores=pd.DataFrame(),
            alerts=alerts,
            machine_summary=pd.DataFrame(),
            sensor_summary=pd.DataFrame(),
            degradation_signals=pd.DataFrame(),
            anomaly_scores=anomaly,
            risk_summary=pd.DataFrame(),
            diagnostics={},
        )
    )
    return {
        **summary,
        "plants_represented": int(scored["plant_id"].nunique()),
        "lines_represented": int(scored["production_line_id"].nunique()),
        "operating_modes_represented": sorted(scored["operating_mode"].unique().tolist()),
        "maintenance_states_represented": sorted(scored["maintenance_state"].unique().tolist()),
        "groups_with_sufficient_degradation_history": int(
            (scored["degradation_status"] == "calculated").sum()
        ),
        "groups_with_insufficient_degradation_history": int(
            (scored["degradation_status"] == "insufficient_history").sum()
        ),
        "groups_using_anomaly_fallback": int(
            (anomaly["robust_zscore_status"] != "calculated").sum()
            + (anomaly["isolation_forest_status"] != "retrospective_batch_diagnostic").sum()
        ),
        "alert_distribution_by_machine": alerts["machine_id"].value_counts().sort_index().to_dict(),
        "alert_distribution_by_sensor_type": alerts["sensor_type"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "alert_distribution_by_line": alerts["production_line_id"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "alert_distribution_by_plant": alerts["plant_id"].value_counts().sort_index().to_dict(),
        "missing_or_unsupported_fields": [],
        "fallback_counts": {
            "service_interval_proxy_used": len(scored),
            "quality_context_records_used": len(quality),
            "production_context_records_used": len(production),
        },
        "quality_context_records_used": len(quality),
        "production_context_records_used": len(production),
    }


def _manifest(
    config: MaintenanceConfig,
    run_id: str,
    evidence: MaintenanceInputEvidence,
    tables: MaintenanceTables,
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "maintenance_run_id": run_id,
        "pipeline_name": "predictive_maintenance",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "governed_input_paths": {
            "equipment_health": relative_path(config.maintenance.equipment_health_path),
            "production_events": relative_path(config.maintenance.production_events_path),
            "quality_checks": relative_path(config.maintenance.quality_checks_path),
            "quality_alerts": relative_path(config.maintenance.quality_alerts_path),
        },
        "governed_input_hashes": evidence.input_hashes,
        "governed_input_row_counts": evidence.input_row_counts,
        "upstream_ingestion_run_id": evidence.upstream_ingestion_run_id,
        "upstream_ingestion_manifest_sha256": evidence.manifest_sha256,
        "upstream_quality_run_id": evidence.upstream_quality_run_id,
        "upstream_quality_manifest_sha256": evidence.quality_manifest_sha256,
        "analysis_grains": {
            "principal_alert_grain": ["sensor_event_id"],
            "trend_grain": ["machine_id", "sensor_type", "event_date"],
            "supported_grains": [
                "plant_id",
                "plant_id+production_line_id",
                "plant_id+production_line_id+machine_id",
                "machine_id",
                "machine_id+sensor_type",
                "machine_id+sensor_id",
                "machine_id+maintenance_state",
                "machine_id+operating_mode",
            ],
        },
        "threshold_settings": config.thresholds.__dict__,
        "degradation_settings": config.degradation.__dict__,
        "anomaly_settings": config.anomaly_detection.__dict__,
        "risk_scoring_settings": config.risk_scoring.__dict__,
        "output_files": outputs,
        "kpi_summary": _summary(tables),
        "alert_summary": {
            "alert_count": len(tables.alerts),
            "risk_level_distribution": tables.alerts["risk_level"]
            .value_counts()
            .sort_index()
            .to_dict(),
        },
        "validation_status": "success",
        "warnings": [
            "Failure-risk scores are deterministic heuristic scores, not calibrated probabilities.",
            "Runtime and service outputs use configured proxy assumptions where explicit "
            "schedules are unavailable.",
            "Investigation context is not root-cause proof and is not an operationally "
            "binding instruction.",
        ],
        "synthetic_data_classification": evidence.synthetic_classification,
        "git_commit": git_commit(),
        "governed_inputs_modified": False,
        "azure_mapping": {
            "governed_equipment_zone": "Azure Data Lake Storage Gen2 responsibility",
            "operational_telemetry_analytics": "Azure Data Explorer responsibility",
            "feature_preparation": "Synapse Analytics or Microsoft Fabric responsibility",
            "batch_predictive_scoring": "Azure Machine Learning responsibility",
            "lineage": "Microsoft Purview responsibility",
            "equipment_metrics": "Azure Monitor responsibility",
            "dashboard_extracts": "Power BI-ready outputs responsibility",
            "deployment_status": "reference-only; no Azure services deployed or called",
        },
    }


def _lineage(
    config: MaintenanceConfig,
    run_id: str,
    evidence: MaintenanceInputEvidence,
    outputs: dict[str, Any],
) -> list[dict[str, Any]]:
    sources = {
        "accepted_equipment_health": {
            "path": relative_path(config.maintenance.equipment_health_path),
            "sha256": evidence.input_hashes["equipment_health"],
            "row_count": evidence.input_row_counts["equipment_health"],
        },
        "accepted_production_events": {
            "path": relative_path(config.maintenance.production_events_path),
            "sha256": evidence.input_hashes["production_events"],
            "row_count": evidence.input_row_counts["production_events"],
        },
    }
    if "quality_checks" in evidence.input_hashes:
        sources["accepted_quality_checks"] = {
            "path": relative_path(config.maintenance.quality_checks_path),
            "sha256": evidence.input_hashes["quality_checks"],
            "row_count": evidence.input_row_counts["quality_checks"],
        }
    config_hash = semantic_config_hash(config)
    return [
        lineage_record(
            maintenance_run_id=run_id,
            upstream_ingestion_run_id=evidence.upstream_ingestion_run_id,
            upstream_quality_run_id=evidence.upstream_quality_run_id,
            source_inputs=sources,
            target=target,
            transformation_name=name,
            configuration_hash=config_hash,
            rule_or_model=_rule_or_model(name),
        )
        for name, target in outputs.items()
    ]


def _portfolio_projection(run_id: str, tables: MaintenanceTables) -> dict[str, Any]:
    top = tables.alerts.head(20)
    return {
        "maintenance_run_id": run_id,
        "relationship": {
            "maintenance_predictions_json": "stable portfolio projection",
            "maintenance_alerts_csv": "row-level alert details",
            "equipment_health_scores_csv": "all scored equipment sensor events",
        },
        "summary": _summary(tables),
        "top_alerts": top[
            [
                "alert_id",
                "sensor_event_id",
                "machine_id",
                "sensor_type",
                "failure_risk_score",
                "equipment_health_score",
                "risk_level",
                "recommended_action",
                "investigation_context",
            ]
        ].to_dict("records"),
    }


def _score_columns() -> list[str]:
    return [
        "maintenance_run_id",
        "sensor_event_id",
        "event_timestamp",
        "plant_id",
        "production_line_id",
        "machine_id",
        "sensor_id",
        "sensor_type",
        "measurement_unit",
        "sensor_value",
        "threshold_breach_component_score",
        "near_threshold_component_score",
        "anomaly_component_score",
        "degradation_score",
        "runtime_risk_score",
        "maintenance_state_risk_score",
        "production_context_score",
        "quality_context_score",
        "failure_risk_score",
        "equipment_health_score",
        "risk_level",
        "maintenance_priority",
        "recommended_action",
        "recommendation_reason",
        "synthetic_data_flag",
    ]


def _with_overrides(
    config: MaintenanceConfig,
    *,
    equipment_health_path: Path | None,
    production_events_path: Path | None,
    output_directory: Path | None,
    overwrite: bool,
) -> MaintenanceConfig:
    settings = config.maintenance
    resolved_output = output_directory.resolve() if output_directory else settings.output_directory
    portfolio_path = (
        resolved_output / "maintenance_predictions.json"
        if output_directory
        else settings.portfolio_predictions_path
    )
    report_directory = (
        resolved_output / "reports" if output_directory else settings.report_directory
    )
    return MaintenanceConfig(
        config_path=config.config_path,
        maintenance=type(settings)(
            equipment_health_path=equipment_health_path.resolve()
            if equipment_health_path
            else settings.equipment_health_path,
            production_events_path=production_events_path.resolve()
            if production_events_path
            else settings.production_events_path,
            quality_checks_path=settings.quality_checks_path,
            quality_alerts_path=settings.quality_alerts_path,
            ingestion_manifest_path=settings.ingestion_manifest_path,
            validation_summary_path=settings.validation_summary_path,
            data_quality_report_path=settings.data_quality_report_path,
            ingestion_lineage_path=settings.ingestion_lineage_path,
            quality_manifest_path=settings.quality_manifest_path,
            output_directory=resolved_output,
            portfolio_predictions_path=portfolio_path,
            report_directory=report_directory,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            timestamp_field=settings.timestamp_field,
            primary_key=settings.primary_key,
        ),
        thresholds=config.thresholds,
        degradation=config.degradation,
        anomaly_detection=config.anomaly_detection,
        risk_scoring=config.risk_scoring,
        recommendations=config.recommendations,
    )


def _ensure_can_write(config: MaintenanceConfig) -> None:
    managed = [
        config.maintenance.output_directory,
        config.maintenance.portfolio_predictions_path,
        config.maintenance.report_directory / "maintenance_analytics_report.md",
        config.maintenance.report_directory / "maintenance_alert_summary.md",
    ]
    if config.maintenance.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Maintenance outputs already exist: {existing}")


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value


def _rule_or_model(name: str) -> str:
    mapping = {
        "equipment_health_features": "thresholds;production_context;quality_context",
        "degradation_signals": "rolling_slope_no_future_leakage",
        "anomaly_scores": "robust_zscore;isolation_forest",
        "equipment_health_scores": "transparent_weighted_heuristic_score",
        "maintenance_alerts": "deterministic_alert_rules",
    }
    return mapping.get(name, "")
