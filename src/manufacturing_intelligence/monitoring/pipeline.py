"""Local platform monitoring and observability pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.monitoring.alerts import monitoring_alerts
from manufacturing_intelligence.monitoring.config import MonitoringConfig, load_monitoring_config
from manufacturing_intelligence.monitoring.data import (
    MonitoringEvidence,
    load_monitoring_evidence,
    verify_upstream_unchanged,
)
from manufacturing_intelligence.monitoring.domain_checks import (
    data_quality_monitoring,
    model_and_analytics_monitoring,
    pipeline_health,
)
from manufacturing_intelligence.monitoring.integrity import (
    evidence_integrity_checks,
    lineage_completeness_checks,
    manifest_integrity_score,
)
from manufacturing_intelligence.monitoring.lineage import lineage_record
from manufacturing_intelligence.monitoring.manifest import (
    git_commit,
    monitoring_run_id,
    semantic_config_hash,
)
from manufacturing_intelligence.monitoring.reporting import (
    write_observability_summary,
    write_platform_report,
)
from manufacturing_intelligence.monitoring.scoring import (
    domain_health_scores,
    health_label,
    overall_platform_health,
)
from manufacturing_intelligence.monitoring.serialization import file_evidence, write_csv, write_json
from manufacturing_intelligence.monitoring.summaries import platform_summary


@dataclass(frozen=True)
class MonitoringResult:
    """Monitoring pipeline result."""

    monitoring_run_id: str
    output_directory: Path
    platform_health_score: float
    alert_rows: int


@dataclass(frozen=True)
class MonitoringTables:
    """Monitoring output tables."""

    platform_summary: dict[str, Any]
    pipeline_health: pd.DataFrame
    domain_scores: pd.DataFrame
    data_quality: pd.DataFrame
    model_analytics: pd.DataFrame
    alerts: pd.DataFrame
    integrity: pd.DataFrame
    lineage_completeness: pd.DataFrame
    diagnostics: dict[str, Any]


def run_monitoring(
    config_path: Path | None = None,
    *,
    output_directory: Path | None = None,
    overwrite: bool = False,
) -> MonitoringResult:
    """Run deterministic local monitoring."""
    config = _with_overrides(
        load_monitoring_config(config_path),
        output_directory=output_directory,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    evidence = load_monitoring_evidence(config)
    run_id = monitoring_run_id(config, _run_identity_hashes(evidence))
    tables = _calculate_tables(config, run_id, evidence)
    verify_upstream_unchanged(config, evidence)
    _publish_outputs(config, run_id, evidence, tables)
    return MonitoringResult(
        monitoring_run_id=run_id,
        output_directory=config.monitoring.output_directory,
        platform_health_score=float(tables.platform_summary["platform_health_score"]),
        alert_rows=len(tables.alerts),
    )


def _calculate_tables(
    config: MonitoringConfig,
    run_id: str,
    evidence: MonitoringEvidence,
) -> MonitoringTables:
    integrity = evidence_integrity_checks(evidence.manifests)
    lineage = lineage_completeness_checks(evidence.manifests, evidence.lineages)
    domains = domain_health_scores(
        manifests=evidence.manifests,
        integrity=integrity,
        lineage=lineage,
        thresholds=config.thresholds,
    )
    platform_score = overall_platform_health(domains)
    platform_label = health_label(platform_score, config.thresholds)
    alerts = monitoring_alerts(
        monitoring_run_id=run_id,
        integrity=integrity,
        lineage=lineage,
        domain_scores=domains,
        thresholds=config.thresholds,
    )
    summary = platform_summary(
        monitoring_run_id=run_id,
        platform_health_score=platform_score,
        platform_health_label=platform_label,
        domain_scores=domains,
        alerts=alerts,
    )
    pipeline = pipeline_health(evidence.manifests, domains)
    data_quality = data_quality_monitoring(evidence.manifests)
    model_analytics = model_and_analytics_monitoring(evidence.manifests)
    diagnostics = _diagnostics(evidence, integrity, lineage, domains, alerts, platform_score)
    return MonitoringTables(
        platform_summary=summary,
        pipeline_health=pipeline,
        domain_scores=domains,
        data_quality=data_quality,
        model_analytics=model_analytics,
        alerts=alerts,
        integrity=integrity,
        lineage_completeness=lineage,
        diagnostics=diagnostics,
    )


def _publish_outputs(
    config: MonitoringConfig,
    run_id: str,
    evidence: MonitoringEvidence,
    tables: MonitoringTables,
) -> None:
    output_dir = config.monitoring.output_directory
    write_json(output_dir / "platform_health_summary.json", tables.platform_summary)
    write_csv(output_dir / "pipeline_health.csv", tables.pipeline_health)
    write_csv(output_dir / "domain_health_scores.csv", tables.domain_scores)
    write_csv(output_dir / "data_quality_monitoring.csv", tables.data_quality)
    write_csv(output_dir / "model_and_analytics_monitoring.csv", tables.model_analytics)
    write_csv(output_dir / "monitoring_alerts.csv", tables.alerts)
    write_csv(output_dir / "evidence_integrity_checks.csv", tables.integrity)
    write_csv(output_dir / "lineage_completeness.csv", tables.lineage_completeness)
    write_json(output_dir / "monitoring_diagnostics.json", tables.diagnostics)
    write_json(config.monitoring.portfolio_summary_path, tables.platform_summary)
    if config.reporting.write_markdown_report:
        write_platform_report(
            config.monitoring.report_directory / "platform_monitoring_report.md",
            summary=tables.platform_summary,
            domain_scores=tables.domain_scores,
            alerts=tables.alerts,
            max_alerts=config.reporting.maximum_alert_examples,
        )
        write_observability_summary(
            config.monitoring.report_directory / "observability_summary.md",
            summary=tables.platform_summary,
        )
    base = output_dir.parent
    outputs = _output_evidence(config, base)
    manifest = _manifest(config, run_id, evidence, tables, outputs)
    write_json(output_dir / "monitoring-manifest.json", manifest)
    outputs["monitoring_manifest"] = file_evidence(
        output_dir / "monitoring-manifest.json", None, base_directory=base
    )
    write_json(output_dir / "lineage-records.json", _lineage(config, run_id, evidence, outputs))


def _output_evidence(config: MonitoringConfig, base: Path) -> dict[str, Any]:
    output_dir = config.monitoring.output_directory
    outputs = {
        "platform_health_summary": file_evidence(
            output_dir / "platform_health_summary.json", None, base_directory=base
        ),
        "pipeline_health": file_evidence(output_dir / "pipeline_health.csv", base_directory=base),
        "domain_health_scores": file_evidence(
            output_dir / "domain_health_scores.csv", base_directory=base
        ),
        "data_quality_monitoring": file_evidence(
            output_dir / "data_quality_monitoring.csv", base_directory=base
        ),
        "model_and_analytics_monitoring": file_evidence(
            output_dir / "model_and_analytics_monitoring.csv", base_directory=base
        ),
        "monitoring_alerts": file_evidence(
            output_dir / "monitoring_alerts.csv", base_directory=base
        ),
        "evidence_integrity_checks": file_evidence(
            output_dir / "evidence_integrity_checks.csv", base_directory=base
        ),
        "lineage_completeness": file_evidence(
            output_dir / "lineage_completeness.csv", base_directory=base
        ),
        "monitoring_diagnostics": file_evidence(
            output_dir / "monitoring_diagnostics.json", None, base_directory=base
        ),
        "portfolio_platform_health_summary": file_evidence(
            config.monitoring.portfolio_summary_path, None, base_directory=base
        ),
    }
    if config.reporting.write_markdown_report:
        outputs["platform_monitoring_report"] = file_evidence(
            config.monitoring.report_directory / "platform_monitoring_report.md",
            None,
            base_directory=base,
        )
        outputs["observability_summary"] = file_evidence(
            config.monitoring.report_directory / "observability_summary.md",
            None,
            base_directory=base,
        )
    return outputs


def _manifest(
    config: MonitoringConfig,
    run_id: str,
    evidence: MonitoringEvidence,
    tables: MonitoringTables,
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "monitoring_run_id": run_id,
        "pipeline_name": "platform_monitoring",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "monitored_domains": list(config.monitoring.required_domains),
        "input_hashes": evidence.input_hashes,
        "input_manifests": {
            "generation": relative_path(config.inputs.generation_manifest_path),
            "ingestion": relative_path(config.inputs.ingestion_manifest_path),
            "forecasting": relative_path(config.inputs.forecast_manifest_path),
            "inventory": relative_path(config.inputs.inventory_manifest_path),
            "quality": relative_path(config.inputs.quality_manifest_path),
            "maintenance": relative_path(config.inputs.maintenance_manifest_path),
        },
        "output_files": outputs,
        "domain_health_scores": tables.domain_scores.set_index("domain")["health_score"].to_dict(),
        "platform_health_score": tables.platform_summary["platform_health_score"],
        "platform_health_label": tables.platform_summary["platform_health_label"],
        "alert_counts_by_severity": tables.alerts["severity"].value_counts().sort_index().to_dict(),
        "manifest_integrity_score": manifest_integrity_score(tables.integrity),
        "lineage_completeness_score": float(
            tables.lineage_completeness["lineage_completeness_score"].mean()
        ),
        "validation_status": "success",
        "warnings": [
            "Monitoring is deterministic local evidence monitoring, not live Azure "
            "Monitor integration.",
            "Health scores are heuristic observability indicators, not formal SLA measurements.",
        ],
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "git_commit": git_commit(),
        "upstream_inputs_modified": False,
        "azure_mapping": {
            "metrics": "Azure Monitor responsibility",
            "logs": "Log Analytics responsibility",
            "operational_queries": "Azure Data Explorer responsibility",
            "ml_monitoring": "Azure Machine Learning monitoring responsibility",
            "lineage": "Microsoft Purview responsibility",
            "dashboard_extracts": "Power BI-ready outputs responsibility",
            "deployment_status": "reference-only; no Azure services deployed or called",
        },
    }


def _lineage(
    config: MonitoringConfig,
    run_id: str,
    evidence: MonitoringEvidence,
    outputs: dict[str, Any],
) -> list[dict[str, Any]]:
    sources = {
        name: {"path": name, "sha256": value, "row_count": None}
        for name, value in sorted(evidence.input_hashes.items())
    }
    config_hash = semantic_config_hash(config)
    return [
        lineage_record(
            monitoring_run_id=run_id,
            source_inputs=sources,
            target=target,
            transformation_name=name,
            configuration_hash=config_hash,
        )
        for name, target in outputs.items()
    ]


def _diagnostics(
    evidence: MonitoringEvidence,
    integrity: pd.DataFrame,
    lineage: pd.DataFrame,
    domain_scores: pd.DataFrame,
    alerts: pd.DataFrame,
    platform_score: float,
) -> dict[str, Any]:
    return {
        "monitored_manifest_count": 6,
        "monitored_input_hash_count": len(evidence.input_hashes),
        "evidence_integrity_checks": len(integrity),
        "failed_integrity_checks": int((integrity["integrity_status"] != "passed").sum()),
        "lineage_domains_checked": len(lineage),
        "minimum_lineage_completeness_score": float(lineage["lineage_completeness_score"].min()),
        "platform_health_score": platform_score,
        "domain_health_scores": domain_scores.set_index("domain")["health_score"].to_dict(),
        "alert_counts_by_severity": alerts["severity"].value_counts().sort_index().to_dict(),
        "synthetic_data_flag": True,
        "live_azure_monitor_integration": False,
    }


def _run_identity_hashes(evidence: MonitoringEvidence) -> dict[str, str]:
    keys = [
        "generation_manifest",
        "ingestion_manifest",
        "forecast_manifest",
        "inventory_manifest",
        "quality_manifest",
        "maintenance_manifest",
    ]
    return {key: evidence.input_hashes[key] for key in keys}


def _with_overrides(
    config: MonitoringConfig,
    *,
    output_directory: Path | None,
    overwrite: bool,
) -> MonitoringConfig:
    settings = config.monitoring
    resolved_output = output_directory.resolve() if output_directory else settings.output_directory
    portfolio_path = (
        resolved_output / "platform_health_summary.json"
        if output_directory
        else settings.portfolio_summary_path
    )
    report_directory = (
        resolved_output / "reports" if output_directory else settings.report_directory
    )
    return MonitoringConfig(
        config_path=config.config_path,
        monitoring=type(settings)(
            output_directory=resolved_output,
            portfolio_summary_path=portfolio_path,
            report_directory=report_directory,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            required_domains=settings.required_domains,
        ),
        inputs=config.inputs,
        thresholds=config.thresholds,
        reporting=config.reporting,
    )


def _ensure_can_write(config: MonitoringConfig) -> None:
    managed = [
        config.monitoring.output_directory,
        config.monitoring.portfolio_summary_path,
        config.monitoring.report_directory / "platform_monitoring_report.md",
        config.monitoring.report_directory / "observability_summary.md",
    ]
    if config.monitoring.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Monitoring outputs already exist: {existing}")


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value
