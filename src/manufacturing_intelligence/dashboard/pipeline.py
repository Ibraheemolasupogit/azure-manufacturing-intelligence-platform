"""Dashboard output pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.dashboard.config import DashboardConfig, load_dashboard_config
from manufacturing_intelligence.dashboard.data import (
    DashboardEvidence,
    load_dashboard_evidence,
    verify_upstream_unchanged,
)
from manufacturing_intelligence.dashboard.lineage import lineage_records
from manufacturing_intelligence.dashboard.manifest import (
    dashboard_run_id,
    git_commit,
    semantic_config_hash,
)
from manufacturing_intelligence.dashboard.metrics import SYNTHETIC_DISCLAIMER, build_tables
from manufacturing_intelligence.dashboard.pages import dashboard_page_specs
from manufacturing_intelligence.dashboard.reporting import dashboard_report, write_markdown
from manufacturing_intelligence.dashboard.semantic_model import PRIMARY_KEYS, build_semantic_model
from manufacturing_intelligence.dashboard.serialization import file_evidence, write_csv, write_json
from manufacturing_intelligence.dashboard.visuals import visual_specs
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class DashboardResult:
    dashboard_run_id: str
    output_directory: Path
    table_count: int
    metric_count: int
    page_count: int
    visual_count: int


def run_dashboard(
    config_path: Path | None = None,
    *,
    output_directory: Path | None = None,
    dashboard_directory: Path | None = None,
    overwrite: bool = False,
) -> DashboardResult:
    config = _with_overrides(
        load_dashboard_config(config_path),
        output_directory=output_directory,
        dashboard_directory=dashboard_directory,
        overwrite=overwrite,
    )
    _ensure_can_write(config)
    evidence = load_dashboard_evidence(config)
    run_id = dashboard_run_id(config, evidence.input_hashes)
    tables = build_tables(evidence.frames, evidence.json_inputs)
    for name, frame in tables.items():
        write_csv(config.dashboard.output_directory / f"{name}.csv", frame)
    semantic_model = build_semantic_model(config.dashboard.semantic_model_name, tables)
    pages = dashboard_page_specs(config.dashboard_pages)
    visuals = visual_specs(pages, config.reporting.maximum_visuals_per_page)
    diagnostics = _diagnostics(tables, semantic_model, pages, visuals, evidence)
    write_json(config.dashboard.output_directory / "semantic_model.json", semantic_model)
    write_json(config.dashboard.output_directory / "dashboard_page_specs.json", pages)
    write_json(config.dashboard.output_directory / "visual_specifications.json", visuals)
    write_json(config.dashboard.output_directory / "dashboard_diagnostics.json", diagnostics)
    _write_reports(config, run_id, diagnostics)
    outputs = _output_evidence(config)
    manifest = _manifest(config, run_id, evidence, outputs, diagnostics, semantic_model)
    write_json(config.dashboard.output_directory / "dashboard-manifest.json", manifest)
    outputs["dashboard_manifest"] = file_evidence(
        config.dashboard.output_directory / "dashboard-manifest.json",
        base_directory=config.dashboard.output_directory.parent,
    )
    write_json(
        config.dashboard.output_directory / "lineage-records.json",
        lineage_records(
            run_id=run_id,
            source_hashes=evidence.input_hashes,
            outputs=outputs,
            configuration_hash=semantic_config_hash(config),
        ),
    )
    verify_upstream_unchanged(config, evidence)
    return DashboardResult(
        dashboard_run_id=run_id,
        output_directory=config.dashboard.output_directory,
        table_count=len(tables),
        metric_count=len(tables["metric_catalogue"]),
        page_count=len(pages),
        visual_count=len(visuals),
    )


def _write_reports(config: DashboardConfig, run_id: str, diagnostics: dict[str, Any]) -> None:
    if config.reporting.write_dashboard_report:
        write_markdown(
            config.dashboard.report_directory / "dashboard_output_report.md",
            "Dashboard Output Report",
            dashboard_report(run_id, diagnostics),
        )
    if config.reporting.write_semantic_model_docs:
        write_markdown(
            config.dashboard.report_directory / "semantic_model_summary.md",
            "Semantic Model Summary",
            "\n".join(
                [
                    f"Model: {config.dashboard.semantic_model_name}",
                    "",
                    "Local metadata only. No Fabric semantic model or Power BI dataset "
                    "was deployed.",
                    SYNTHETIC_DISCLAIMER,
                ]
            ),
        )
    write_markdown(
        config.dashboard.dashboard_directory / "dashboard_index.md",
        "Dashboard Index",
        "Power BI-ready local dashboard outputs are available under `outputs/dashboard/`.",
    )
    write_markdown(
        config.dashboard.dashboard_directory / "powerbi_ready_outputs.md",
        "Power BI-Ready Outputs",
        "CSV and JSON outputs are local import-ready artefacts, not Power BI exports.",
    )
    write_markdown(
        config.dashboard.dashboard_directory / "semantic_model_notes.md",
        "Semantic Model Notes",
        f"{SYNTHETIC_DISCLAIMER}\n\nRelationships are limited to available keys.",
    )


def _diagnostics(
    tables: dict[str, Any],
    semantic_model: dict[str, Any],
    pages: list[dict[str, Any]],
    visuals: list[dict[str, Any]],
    evidence: DashboardEvidence,
) -> dict[str, Any]:
    row_counts = {name: len(frame) for name, frame in tables.items()}
    return {
        "generated_table_count": len(tables),
        "dimension_table_count": len([name for name in tables if name.startswith("dim_")]),
        "fact_table_count": len([name for name in tables if name.startswith("fact_")]),
        "generated_row_counts": row_counts,
        "empty_table_count": sum(1 for value in row_counts.values() if value == 0),
        "missing_optional_input_count": len(evidence.warnings),
        "relationship_count": len(semantic_model["relationships"]),
        "metric_count": len(tables["metric_catalogue"]),
        "visual_spec_count": len(visuals),
        "dashboard_page_count": len(pages),
        "executive_scorecard_kpi_count": len(tables["executive_scorecard"]),
        "unsupported_metric_count": 0,
        "warning_count": len(evidence.warnings),
        "source_manifest_count": len(evidence.manifests),
        "lineage_record_count": 0,
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "power_bi_deployment": False,
        "fabric_deployment": False,
        "azure_deployment": False,
    }


def _manifest(
    config: DashboardConfig,
    run_id: str,
    evidence: DashboardEvidence,
    outputs: dict[str, dict[str, Any]],
    diagnostics: dict[str, Any],
    semantic_model: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dashboard_run_id": run_id,
        "pipeline_name": "dashboard_outputs",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "input_manifests": {
            name: relative_path(getattr(config.inputs, f"{name}_manifest_path"))
            for name in [
                "ingestion",
                "forecast",
                "inventory",
                "quality",
                "maintenance",
                "monitoring",
                "genai",
            ]
        },
        "input_hashes": evidence.input_hashes,
        "dashboard_tables": [
            name
            for name, evidence_item in outputs.items()
            if evidence_item["path"].endswith(".csv")
        ],
        "output_files": outputs,
        "semantic_model_summary": {
            "model_name": semantic_model["model_name"],
            "table_count": len(semantic_model["tables"]),
            "relationship_count": len(semantic_model["relationships"]),
            "measure_count": len(semantic_model["measures"]),
        },
        "dashboard_page_count": diagnostics["dashboard_page_count"],
        "visual_specification_count": diagnostics["visual_spec_count"],
        "metric_count": diagnostics["metric_count"],
        "validation_status": "success",
        "warnings": evidence.warnings,
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "power_bi_deployment": False,
        "fabric_deployment": False,
        "azure_deployment": False,
        "git_commit": git_commit(),
        "upstream_inputs_modified": False,
        "primary_keys": PRIMARY_KEYS,
        "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
    }


def _output_evidence(config: DashboardConfig) -> dict[str, dict[str, Any]]:
    base = config.dashboard.output_directory.parent
    output_dir = config.dashboard.output_directory
    report_dir = config.dashboard.report_directory
    dashboard_dir = config.dashboard.dashboard_directory
    outputs = {
        path.stem: file_evidence(path, base_directory=base)
        for path in sorted(output_dir.glob("*.csv"))
    }
    for path in [
        output_dir / "semantic_model.json",
        output_dir / "dashboard_page_specs.json",
        output_dir / "visual_specifications.json",
        output_dir / "dashboard_diagnostics.json",
        report_dir / "dashboard_output_report.md",
        report_dir / "semantic_model_summary.md",
        dashboard_dir / "dashboard_index.md",
        dashboard_dir / "powerbi_ready_outputs.md",
        dashboard_dir / "semantic_model_notes.md",
    ]:
        outputs[path.stem] = file_evidence(path, base_directory=base)
    return outputs


def _with_overrides(
    config: DashboardConfig,
    *,
    output_directory: Path | None,
    dashboard_directory: Path | None,
    overwrite: bool,
) -> DashboardConfig:
    if output_directory is None and dashboard_directory is None and not overwrite:
        return config
    settings = config.dashboard
    output_dir = output_directory.resolve() if output_directory else settings.output_directory
    if dashboard_directory:
        dash_dir = dashboard_directory.resolve()
    elif output_directory:
        dash_dir = output_dir / "portfolio"
    else:
        dash_dir = settings.dashboard_directory
    report_dir = output_dir / "reports" if output_directory else settings.report_directory
    return DashboardConfig(
        config_path=config.config_path,
        dashboard=type(settings)(
            output_directory=output_dir,
            report_directory=report_dir,
            dashboard_directory=dash_dir,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            semantic_model_name=settings.semantic_model_name,
            currency=settings.currency,
            synthetic_data_disclaimer_required=settings.synthetic_data_disclaimer_required,
        ),
        inputs=config.inputs,
        dashboard_pages=config.dashboard_pages,
        validation=config.validation,
        reporting=config.reporting,
    )


def _ensure_can_write(config: DashboardConfig) -> None:
    managed = [
        config.dashboard.output_directory,
        config.dashboard.report_directory / "dashboard_output_report.md",
        config.dashboard.report_directory / "semantic_model_summary.md",
        config.dashboard.dashboard_directory / "dashboard_index.md",
        config.dashboard.dashboard_directory / "powerbi_ready_outputs.md",
        config.dashboard.dashboard_directory / "semantic_model_notes.md",
    ]
    if config.dashboard.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"Dashboard outputs already exist: {existing}")


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value
