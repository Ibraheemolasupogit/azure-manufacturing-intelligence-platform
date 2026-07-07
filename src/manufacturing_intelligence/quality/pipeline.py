"""Quality analytics and anomaly-detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.quality.anomalies import calculate_anomaly_scores
from manufacturing_intelligence.quality.capability import calculate_process_capability
from manufacturing_intelligence.quality.config import QualityConfig, load_quality_config
from manufacturing_intelligence.quality.control_charts import (
    calculate_control_chart_points,
    evaluate_spc_rules,
)
from manufacturing_intelligence.quality.data import (
    QualityInputEvidence,
    load_quality_inputs,
    verify_upstream_unchanged,
)
from manufacturing_intelligence.quality.lineage import lineage_record
from manufacturing_intelligence.quality.manifest import (
    git_commit,
    manifest_hash,
    quality_run_id,
    semantic_config_hash,
)
from manufacturing_intelligence.quality.metrics import (
    attach_production_context,
    calculate_quality_kpis,
)
from manufacturing_intelligence.quality.pareto import calculate_defect_pareto
from manufacturing_intelligence.quality.reporting import write_alert_summary, write_quality_report
from manufacturing_intelligence.quality.scoring import build_alerts, score_quality_risk
from manufacturing_intelligence.quality.serialization import file_evidence, write_csv, write_json
from manufacturing_intelligence.quality.specification import evaluate_specification


@dataclass(frozen=True)
class QualityResult:
    """Quality pipeline result."""

    quality_run_id: str
    output_directory: Path
    observation_rows: int
    alert_rows: int


@dataclass(frozen=True)
class QualityTables:
    """Quality analytics output tables."""

    observations: pd.DataFrame
    kpis: pd.DataFrame
    pareto: pd.DataFrame
    capability: pd.DataFrame
    control_points: pd.DataFrame
    spc_signals: pd.DataFrame
    anomaly_scores: pd.DataFrame
    alerts: pd.DataFrame
    risk_summary: pd.DataFrame
    diagnostics: dict[str, Any]


def run_quality(
    config_path: Path | None = None,
    *,
    quality_checks_path: Path | None = None,
    production_events_path: Path | None = None,
    output_directory: Path | None = None,
    overwrite: bool = False,
) -> QualityResult:
    """Run deterministic governed quality analytics."""
    config = _with_overrides(
        load_quality_config(config_path),
        quality_checks_path=quality_checks_path,
        production_events_path=production_events_path,
        output_directory=output_directory,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    inputs = load_quality_inputs(config)
    stable_inputs = {
        **inputs.evidence.input_hashes,
        "ingestion_manifest": manifest_hash(config.quality.ingestion_manifest_path),
    }
    run_id = quality_run_id(config, stable_inputs)
    tables = _calculate_tables(config, run_id, inputs.quality_checks, inputs.production_events)
    verify_upstream_unchanged(config, inputs.evidence)
    _publish_outputs(config, run_id, inputs.evidence, tables)
    return QualityResult(
        quality_run_id=run_id,
        output_directory=config.quality.output_directory,
        observation_rows=len(tables.observations),
        alert_rows=len(tables.alerts),
    )


def _calculate_tables(
    config: QualityConfig,
    run_id: str,
    quality_checks: pd.DataFrame,
    production_events: pd.DataFrame,
) -> QualityTables:
    specified = evaluate_specification(quality_checks, config.specification)
    contextual = attach_production_context(specified, production_events)
    control_points = calculate_control_chart_points(contextual, config.spc)
    spc_signals = evaluate_spc_rules(contextual, control_points, config.spc)
    anomaly_scores = calculate_anomaly_scores(
        contextual,
        config.anomaly_detection,
        random_seed=config.quality.random_seed,
    )
    observations = (
        contextual.merge(
            control_points[
                [
                    "inspection_id",
                    "baseline_observation_count",
                    "center_line",
                    "process_standard_deviation",
                    "upper_control_limit",
                    "lower_control_limit",
                    "point_deviation_from_center",
                    "outside_control_limit_flag",
                    "baseline_method",
                    "control_chart_status",
                ]
            ],
            on="inspection_id",
            how="left",
        )
        .merge(
            spc_signals[
                [
                    "inspection_id",
                    "spc_rule_codes",
                    "spc_signal_flag",
                    "spc_triggering_window",
                    "spc_evaluation_status",
                ]
            ],
            on="inspection_id",
            how="left",
        )
        .merge(anomaly_scores, on="inspection_id", how="left")
    )
    observations["quality_run_id"] = run_id
    observations["synthetic_data_flag"] = True
    scored = score_quality_risk(observations, config.risk_scoring)
    alerts = build_alerts(scored, run_id)
    kpis = calculate_quality_kpis(scored)
    pareto = calculate_defect_pareto(scored)
    capability = calculate_process_capability(scored, config.capability)
    risk_summary = _risk_summary(scored)
    diagnostics = _diagnostics(
        scored, control_points, spc_signals, anomaly_scores, capability, alerts
    )
    return QualityTables(
        observations=scored,
        kpis=kpis,
        pareto=pareto,
        capability=capability,
        control_points=control_points,
        spc_signals=spc_signals,
        anomaly_scores=anomaly_scores,
        alerts=alerts,
        risk_summary=risk_summary,
        diagnostics=diagnostics,
    )


def _publish_outputs(
    config: QualityConfig,
    run_id: str,
    evidence: QualityInputEvidence,
    tables: QualityTables,
) -> None:
    output_dir = config.quality.output_directory
    write_csv(output_dir / "quality_observations.csv", tables.observations)
    write_csv(output_dir / "quality_kpis.csv", tables.kpis)
    write_csv(output_dir / "defect_pareto.csv", tables.pareto)
    write_csv(output_dir / "process_capability.csv", tables.capability)
    write_csv(output_dir / "control_chart_points.csv", tables.control_points)
    write_csv(output_dir / "spc_signals.csv", tables.spc_signals)
    write_csv(output_dir / "anomaly_scores.csv", tables.anomaly_scores)
    write_csv(output_dir / "quality_alerts.csv", tables.alerts)
    write_csv(output_dir / "quality_risk_summary.csv", tables.risk_summary)
    write_json(output_dir / "quality_diagnostics.json", tables.diagnostics)
    write_csv(config.quality.quality_alerts_path, tables.alerts)
    summary = _summary(tables)
    if config.reporting.write_markdown_report:
        write_quality_report(
            config.quality.report_directory / "quality_analytics_report.md",
            quality_run_id=run_id,
            summary=summary,
            alerts=tables.alerts,
            max_alerts=config.reporting.maximum_alert_examples,
        )
        write_alert_summary(
            config.quality.report_directory / "quality_alert_summary.md",
            quality_run_id=run_id,
            alerts=tables.alerts,
        )
    base = output_dir.parent
    outputs = {
        "quality_observations": file_evidence(
            output_dir / "quality_observations.csv", base_directory=base
        ),
        "quality_kpis": file_evidence(output_dir / "quality_kpis.csv", base_directory=base),
        "defect_pareto": file_evidence(output_dir / "defect_pareto.csv", base_directory=base),
        "process_capability": file_evidence(
            output_dir / "process_capability.csv", base_directory=base
        ),
        "control_chart_points": file_evidence(
            output_dir / "control_chart_points.csv", base_directory=base
        ),
        "spc_signals": file_evidence(output_dir / "spc_signals.csv", base_directory=base),
        "anomaly_scores": file_evidence(output_dir / "anomaly_scores.csv", base_directory=base),
        "quality_alerts": file_evidence(output_dir / "quality_alerts.csv", base_directory=base),
        "portfolio_quality_alerts": file_evidence(
            config.quality.quality_alerts_path, base_directory=base
        ),
        "quality_risk_summary": file_evidence(
            output_dir / "quality_risk_summary.csv", base_directory=base
        ),
        "quality_diagnostics": file_evidence(
            output_dir / "quality_diagnostics.json", None, base_directory=base
        ),
    }
    if config.reporting.write_markdown_report:
        outputs["quality_analytics_report"] = file_evidence(
            config.quality.report_directory / "quality_analytics_report.md",
            None,
            base_directory=base,
        )
        outputs["quality_alert_summary"] = file_evidence(
            config.quality.report_directory / "quality_alert_summary.md",
            None,
            base_directory=base,
        )
    manifest = _manifest(config, run_id, evidence, tables, summary, outputs)
    write_json(output_dir / "quality-manifest.json", manifest)
    outputs["quality_manifest"] = file_evidence(
        output_dir / "quality-manifest.json", None, base_directory=base
    )
    write_json(output_dir / "lineage-records.json", _lineage(config, run_id, evidence, outputs))


def _summary(tables: QualityTables) -> dict[str, Any]:
    observations = tables.observations
    alerts = tables.alerts
    return {
        "quality_records_processed": len(observations),
        "specification_failure_count": int(
            (observations["calculated_specification_result"] == "fail").sum()
        ),
        "near_limit_count": int(observations["near_limit_flag"].sum()),
        "spc_signal_count": int(observations["spc_signal_flag"].sum()),
        "robust_z_anomaly_count": int(observations["robust_zscore_anomaly_flag"].sum()),
        "isolation_forest_anomaly_count": int(observations["isolation_forest_anomaly_flag"].sum()),
        "alert_count": len(alerts),
        "high_risk_alert_count": int((alerts["risk_level"] == "high").sum()),
        "critical_risk_alert_count": int((alerts["risk_level"] == "critical").sum()),
        "products_represented": int(observations["product_id"].nunique()),
        "plants_represented": int(observations["plant_id"].nunique()),
        "lines_represented": int(observations["production_line_id"].nunique()),
        "machines_represented": int(observations["machine_id"].nunique()),
        "batches_represented": int(observations["batch_id"].nunique()),
        "quality_metrics_represented": int(observations["quality_metric"].nunique()),
    }


def _diagnostics(
    observations: pd.DataFrame,
    control_points: pd.DataFrame,
    spc_signals: pd.DataFrame,
    anomaly_scores: pd.DataFrame,
    capability: pd.DataFrame,
    alerts: pd.DataFrame,
) -> dict[str, Any]:
    rule_counts: dict[str, int] = {}
    for codes in spc_signals["spc_rule_codes"].fillna(""):
        for code in str(codes).split(";"):
            if code:
                rule_counts[code] = rule_counts.get(code, 0) + 1
    return {
        **_summary(
            QualityTables(
                observations=observations,
                kpis=pd.DataFrame(),
                pareto=pd.DataFrame(),
                capability=capability,
                control_points=control_points,
                spc_signals=spc_signals,
                anomaly_scores=anomaly_scores,
                alerts=alerts,
                risk_summary=pd.DataFrame(),
                diagnostics={},
            )
        ),
        "source_calculated_result_inconsistencies": int(
            (~observations["specification_consistency_flag"]).sum()
        ),
        "groups_with_sufficient_spc_history": int(
            (control_points["control_chart_status"] == "calculated").sum()
        ),
        "groups_with_insufficient_spc_history": int(
            (control_points["control_chart_status"] == "insufficient_history").sum()
        ),
        "spc_signals_by_rule": rule_counts,
        "groups_using_anomaly_fallback": int(
            (anomaly_scores["robust_zscore_status"] != "calculated").sum()
            + (anomaly_scores["isolation_forest_status"] != "retrospective_batch_diagnostic").sum()
        ),
        "capability_groups_calculated": int(
            (capability["capability_status"] == "calculated").sum()
        ),
        "capability_groups_unavailable": int(
            (capability["capability_status"] != "calculated").sum()
        ),
        "alert_distribution_by_product": alerts["product_id"].value_counts().sort_index().to_dict(),
        "alert_distribution_by_line": alerts["production_line_id"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "alert_distribution_by_machine": alerts["machine_id"].value_counts().sort_index().to_dict(),
        "alert_distribution_by_category": alerts["defect_category"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "alert_distribution_by_metric": alerts["quality_metric"]
        .value_counts()
        .sort_index()
        .to_dict(),
        "missing_or_unsupported_fields": [],
        "fallback_counts": {
            "first_pass_yield_proxy": len(observations),
            "rework_information_unavailable": len(observations),
        },
    }


def _risk_summary(observations: pd.DataFrame) -> pd.DataFrame:
    grouped = observations.groupby(["risk_level"], sort=True).agg(
        observation_count=("inspection_id", "count"),
        average_quality_risk_score=("quality_risk_score", "mean"),
        specification_failures=(
            "calculated_specification_result",
            lambda x: int((x == "fail").sum()),
        ),
        spc_signals=("spc_signal_flag", "sum"),
        anomaly_count=("combined_anomaly_flag", "sum"),
    )
    return grouped.reset_index()


def _manifest(
    config: QualityConfig,
    run_id: str,
    evidence: QualityInputEvidence,
    tables: QualityTables,
    summary: dict[str, Any],
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "quality_run_id": run_id,
        "pipeline_name": "quality_analytics",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "governed_input_paths": {
            "quality_checks": relative_path(config.quality.quality_checks_path),
            "production_events": relative_path(config.quality.production_events_path),
        },
        "governed_input_hashes": evidence.input_hashes,
        "governed_input_row_counts": evidence.input_row_counts,
        "upstream_ingestion_run_id": evidence.upstream_ingestion_run_id,
        "upstream_ingestion_manifest_sha256": evidence.manifest_sha256,
        "analysis_grains": {
            "alert_grain": list(config.quality.alert_grain),
            "trend_grain": list(config.quality.trend_grain),
            "control_chart_grain": ["machine_id", "quality_metric", "measurement_unit"],
        },
        "specification_settings": config.specification.__dict__,
        "spc_settings": config.spc.__dict__,
        "capability_settings": config.capability.__dict__,
        "anomaly_settings": config.anomaly_detection.__dict__,
        "risk_scoring_settings": config.risk_scoring.__dict__,
        "output_files": outputs,
        "kpi_summary": summary,
        "alert_summary": {
            "alert_count": len(tables.alerts),
            "risk_level_distribution": tables.alerts["risk_level"]
            .value_counts()
            .sort_index()
            .to_dict(),
        },
        "validation_status": "success",
        "warnings": [
            "First-pass yield is a labelled proxy because explicit rework fields are unavailable.",
            "Isolation Forest scores are retrospective deterministic diagnostics, "
            "not probabilities.",
        ],
        "synthetic_data_classification": evidence.synthetic_classification,
        "git_commit": git_commit(),
        "governed_inputs_modified": False,
        "azure_mapping": {
            "governed_quality_zone": "Azure Data Lake Storage Gen2 responsibility",
            "analytical_preparation": "Synapse Analytics or Microsoft Fabric responsibility",
            "operational_quality_analytics": "Azure Data Explorer responsibility",
            "batch_anomaly_scoring": "Azure Machine Learning responsibility",
            "lineage": "Microsoft Purview responsibility",
            "quality_metrics": "Azure Monitor responsibility",
            "dashboard_extracts": "Power BI-ready outputs responsibility",
            "deployment_status": "reference-only; no Azure services deployed or called",
        },
    }


def _lineage(
    config: QualityConfig,
    run_id: str,
    evidence: QualityInputEvidence,
    outputs: dict[str, Any],
) -> list[dict[str, Any]]:
    sources = {
        "accepted_quality_checks": {
            "path": relative_path(config.quality.quality_checks_path),
            "sha256": evidence.input_hashes["quality_checks"],
            "row_count": evidence.input_row_counts["quality_checks"],
        },
        "accepted_production_events": {
            "path": relative_path(config.quality.production_events_path),
            "sha256": evidence.input_hashes["production_events"],
            "row_count": evidence.input_row_counts["production_events"],
        },
    }
    config_hash = semantic_config_hash(config)
    return [
        lineage_record(
            quality_run_id=run_id,
            upstream_ingestion_run_id=evidence.upstream_ingestion_run_id,
            source_inputs=sources,
            target=target,
            transformation_name=name,
            configuration_hash=config_hash,
            rule_or_model=_rule_or_model(name),
        )
        for name, target in outputs.items()
    ]


def _with_overrides(
    config: QualityConfig,
    *,
    quality_checks_path: Path | None,
    production_events_path: Path | None,
    output_directory: Path | None,
    overwrite: bool,
) -> QualityConfig:
    settings = config.quality
    resolved_output = output_directory.resolve() if output_directory else settings.output_directory
    alerts_path = (
        resolved_output / "quality_alerts.csv" if output_directory else settings.quality_alerts_path
    )
    report_directory = (
        resolved_output / "reports" if output_directory else settings.report_directory
    )
    return QualityConfig(
        config_path=config.config_path,
        quality=type(settings)(
            quality_checks_path=quality_checks_path.resolve()
            if quality_checks_path
            else settings.quality_checks_path,
            production_events_path=production_events_path.resolve()
            if production_events_path
            else settings.production_events_path,
            ingestion_manifest_path=settings.ingestion_manifest_path,
            validation_summary_path=settings.validation_summary_path,
            data_quality_report_path=settings.data_quality_report_path,
            ingestion_lineage_path=settings.ingestion_lineage_path,
            output_directory=resolved_output,
            quality_alerts_path=alerts_path,
            report_directory=report_directory,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            timestamp_field=settings.timestamp_field,
            primary_key=settings.primary_key,
            trend_grain=settings.trend_grain,
            alert_grain=settings.alert_grain,
        ),
        specification=config.specification,
        spc=config.spc,
        capability=config.capability,
        anomaly_detection=config.anomaly_detection,
        risk_scoring=config.risk_scoring,
        reporting=config.reporting,
    )


def _ensure_can_write(config: QualityConfig) -> None:
    managed = [
        config.quality.output_directory,
        config.quality.quality_alerts_path,
        config.quality.report_directory / "quality_analytics_report.md",
        config.quality.report_directory / "quality_alert_summary.md",
    ]
    if config.quality.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Quality outputs already exist: {existing}")


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value


def _rule_or_model(name: str) -> str:
    mapping = {
        "spc_signals": "SPC_RULE_1;SPC_RULE_2;SPC_RULE_3;SPC_RULE_4",
        "anomaly_scores": "robust_zscore;isolation_forest",
        "control_chart_points": "expanding_prior_observations",
    }
    return mapping.get(name, "")
