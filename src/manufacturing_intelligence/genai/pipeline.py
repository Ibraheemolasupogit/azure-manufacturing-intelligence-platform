"""Deterministic local GenAI operations assistant pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import PipelineExecutionError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.forecasting.data import relative_path
from manufacturing_intelligence.genai.config import GenAIConfig, load_genai_config
from manufacturing_intelligence.genai.evaluation import evaluate_responses
from manufacturing_intelligence.genai.evidence import build_evidence_catalogue
from manufacturing_intelligence.genai.guardrails import (
    evaluate_guardrails,
    standard_guardrail_checks,
)
from manufacturing_intelligence.genai.lineage import lineage_records
from manufacturing_intelligence.genai.manifest import genai_run_id, git_commit, semantic_config_hash
from manufacturing_intelligence.genai.prompts import prompt_templates, render_prompt
from manufacturing_intelligence.genai.reporting import (
    assistant_responses_markdown,
    operations_report,
    write_markdown,
)
from manufacturing_intelligence.genai.retrieval import (
    TASK_QUESTIONS,
    retrieve_evidence,
    standard_queries,
)
from manufacturing_intelligence.genai.serialization import output_evidence, write_csv, write_json
from manufacturing_intelligence.genai.synthesis import synthesize_response


@dataclass(frozen=True)
class GenAIResult:
    """GenAI assistant run result."""

    genai_run_id: str
    output_directory: Path
    evidence_count: int
    response_count: int
    guardrail_count: int


def run_genai(
    config_path: Path | None = None,
    *,
    output_directory: Path | None = None,
    overwrite: bool = False,
    question: str | None = None,
    task_type: str | None = None,
) -> GenAIResult:
    """Run the deterministic local assistant."""
    config = _with_overrides(load_genai_config(config_path), output_directory, overwrite)
    _ensure_can_write(config)
    catalogue = build_evidence_catalogue(config)
    output_dir = config.genai.output_directory
    write_json(output_dir / "evidence_catalog.json", catalogue.items)
    write_csv(output_dir / "evidence_catalog.csv", pd.DataFrame(catalogue.items))
    evidence_catalogue_hash = sha256_file(output_dir / "evidence_catalog.json")
    run_id = genai_run_id(
        config,
        evidence_catalogue_hash=evidence_catalogue_hash,
        input_hashes=catalogue.input_hashes,
    )

    retrievals = standard_queries(config, catalogue.items)
    if question:
        retrievals.append(
            retrieve_evidence(
                config=config,
                items=catalogue.items,
                question=question,
                task_type=task_type,
            )
        )
    write_json(output_dir / "retrieval_results.json", retrievals)
    write_json(output_dir / "prompt_templates.json", prompt_templates())
    rendered_prompts = [
        render_prompt(result["inferred_intent"], result["query_text"], result)
        for result in retrievals
    ]
    write_json(output_dir / "rendered_prompts.json", rendered_prompts)

    guardrails = [evaluate_guardrails(result["query_text"], result) for result in retrievals]
    guardrails.extend(standard_guardrail_checks(retrievals[0]))
    write_json(output_dir / "guardrail_results.json", guardrails)

    responses = []
    for result, guardrail in zip(retrievals, guardrails, strict=False):
        responses.append(
            synthesize_response(
                assistant_name=config.genai.assistant_name,
                task_type=str(result["inferred_intent"]),
                question=str(result["query_text"]),
                retrieval=result,
                guardrail=guardrail,
                maximum_words=config.genai.maximum_response_words,
            )
        )
    write_json(output_dir / "assistant_responses.json", responses)
    write_markdown(
        output_dir / "assistant_responses.md",
        "Deterministic Assistant Responses",
        assistant_responses_markdown(responses),
    )
    evaluation_frame, evaluation_summary = evaluate_responses(config, responses, catalogue.items)
    write_csv(output_dir / "assistant_evaluation.csv", evaluation_frame)
    write_json(output_dir / "assistant_evaluation_summary.json", evaluation_summary)
    diagnostics = _diagnostics(
        config, catalogue, retrievals, responses, guardrails, evaluation_summary
    )
    write_json(output_dir / "genai_diagnostics.json", diagnostics)

    if config.reporting.write_markdown_report:
        _write_reports(config, run_id, catalogue.items, responses, guardrails, evaluation_summary)

    outputs = _output_evidence(config)
    manifest = _manifest(
        config=config,
        run_id=run_id,
        catalogue=catalogue.items,
        input_hashes=catalogue.input_hashes,
        outputs=outputs,
        evaluation_summary=evaluation_summary,
        warnings=catalogue.warnings,
    )
    write_json(output_dir / "genai-manifest.json", manifest)
    outputs["genai_manifest"] = output_evidence(
        output_dir / "genai-manifest.json", base_directory=output_dir.parent
    )
    write_json(
        output_dir / "lineage-records.json",
        lineage_records(
            run_id=run_id,
            sources=catalogue.items,
            outputs=outputs,
            configuration_hash=semantic_config_hash(config),
        ),
    )
    return GenAIResult(
        genai_run_id=run_id,
        output_directory=output_dir,
        evidence_count=len(catalogue.items),
        response_count=len(responses),
        guardrail_count=len(guardrails),
    )


def _write_reports(
    config: GenAIConfig,
    run_id: str,
    catalogue: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    guardrails: list[dict[str, Any]],
    evaluation_summary: dict[str, Any],
) -> None:
    report_body = operations_report(
        run_id=run_id,
        evidence_count=len(catalogue),
        response_count=len(responses),
        guardrail_count=len(guardrails),
        evaluation_summary=evaluation_summary,
    )
    write_markdown(
        config.genai.report_directory / "genai_operations_assistant_report.md",
        "GenAI Operations Assistant Report",
        report_body,
    )
    refused = [item for item in guardrails if item["decision"] == "refuse"]
    write_markdown(
        config.genai.report_directory / "genai_guardrails_report.md",
        "GenAI Guardrails Report",
        "\n".join(
            [
                f"Guardrail checks: {len(guardrails)}",
                f"Refusals: {len(refused)}",
                "Policies refuse live operational commands, safety-critical instructions, "
                "real-world plant claims, external data requests, validation overrides, "
                "secrets, and unsupported causal claims.",
            ]
        ),
    )
    executive = next(item for item in responses if item["task_type"] == "executive_summary")
    inventory = next(item for item in responses if item["task_type"] == "inventory")
    quality = next(item for item in responses if item["task_type"] == "quality")
    maintenance = next(item for item in responses if item["task_type"] == "maintenance")
    write_markdown(
        config.genai.report_directory / "executive_manufacturing_brief.md",
        "Executive Manufacturing Brief",
        executive["answer"],
    )
    write_markdown(
        config.genai.report_directory / "supply_chain_summary.md",
        "Supply Chain Summary",
        inventory["answer"],
    )
    write_markdown(
        config.genai.report_directory / "manufacturing_operations_report.md",
        "Manufacturing Operations Report",
        "\n\n".join([executive["answer"], quality["answer"], maintenance["answer"]]),
    )


def _diagnostics(
    config: GenAIConfig,
    catalogue: Any,
    retrievals: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    guardrails: list[dict[str, Any]],
    evaluation_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "assistant_name": config.genai.assistant_name,
        "mode": config.genai.mode,
        "evidence_item_count": len(catalogue.items),
        "retrieval_count": len(retrievals),
        "assistant_response_count": len(responses),
        "guardrail_result_count": len(guardrails),
        "evaluation_summary": evaluation_summary,
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "external_model_called": False,
        "azure_deployment": False,
        "warnings": catalogue.warnings,
    }


def _output_evidence(config: GenAIConfig) -> dict[str, dict[str, Any]]:
    output_dir = config.genai.output_directory
    report_dir = config.genai.report_directory
    base = output_dir.parent
    return {
        "evidence_catalog_json": output_evidence(
            output_dir / "evidence_catalog.json", base_directory=base
        ),
        "evidence_catalog_csv": output_evidence(
            output_dir / "evidence_catalog.csv", base_directory=base
        ),
        "retrieval_results": output_evidence(
            output_dir / "retrieval_results.json", base_directory=base
        ),
        "prompt_templates": output_evidence(
            output_dir / "prompt_templates.json", base_directory=base
        ),
        "rendered_prompts": output_evidence(
            output_dir / "rendered_prompts.json", base_directory=base
        ),
        "assistant_responses": output_evidence(
            output_dir / "assistant_responses.json", base_directory=base
        ),
        "assistant_responses_markdown": output_evidence(
            output_dir / "assistant_responses.md", base_directory=base
        ),
        "guardrail_results": output_evidence(
            output_dir / "guardrail_results.json", base_directory=base
        ),
        "assistant_evaluation": output_evidence(
            output_dir / "assistant_evaluation.csv", base_directory=base
        ),
        "assistant_evaluation_summary": output_evidence(
            output_dir / "assistant_evaluation_summary.json", base_directory=base
        ),
        "genai_diagnostics": output_evidence(
            output_dir / "genai_diagnostics.json", base_directory=base
        ),
        "genai_operations_assistant_report": output_evidence(
            report_dir / "genai_operations_assistant_report.md", base_directory=base
        ),
        "genai_guardrails_report": output_evidence(
            report_dir / "genai_guardrails_report.md", base_directory=base
        ),
        "executive_manufacturing_brief": output_evidence(
            report_dir / "executive_manufacturing_brief.md", base_directory=base
        ),
        "supply_chain_summary": output_evidence(
            report_dir / "supply_chain_summary.md", base_directory=base
        ),
        "manufacturing_operations_report": output_evidence(
            report_dir / "manufacturing_operations_report.md", base_directory=base
        ),
    }


def _manifest(
    *,
    config: GenAIConfig,
    run_id: str,
    catalogue: list[dict[str, Any]],
    input_hashes: dict[str, str],
    outputs: dict[str, dict[str, Any]],
    evaluation_summary: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "genai_run_id": run_id,
        "pipeline_name": "genai_operations_assistant",
        "pipeline_version": "0.1.0",
        "software_version": "0.1.0",
        "configuration_path": _stable_config_path(config.config_path),
        "configuration_sha256": semantic_config_hash(config),
        "evidence_inputs": [item["relative_path"] for item in catalogue],
        "evidence_input_hashes": input_hashes,
        "evidence_catalogue_row_count": len(catalogue),
        "supported_task_types": list(TASK_QUESTIONS),
        "prompt_template_hashes": {
            key: sha256_file(config.genai.output_directory / "prompt_templates.json")
            for key in prompt_templates()
        },
        "assistant_response_count": int(evaluation_summary["response_count"]),
        "guardrail_result_count": _json_count(
            config.genai.output_directory / "guardrail_results.json"
        ),
        "evaluation_metrics": evaluation_summary,
        "output_files": outputs,
        "validation_status": evaluation_summary["validation_status"],
        "warnings": warnings,
        "synthetic_data_classification": "synthetic_portfolio_sample",
        "external_model_called": False,
        "azure_deployment": False,
        "git_commit": git_commit(),
        "upstream_inputs_modified": False,
        "azure_mapping": {
            "assistant_orchestration": "Azure AI Foundry reference only",
            "future_llm": "Azure OpenAI Service reference only",
            "retrieval": "Azure AI Search reference only",
            "evaluation": "Azure Machine Learning prompt evaluation reference only",
            "lineage": "Microsoft Purview reference only",
            "observability": "Azure Monitor reference only",
            "narrative_outputs": "Power BI-ready narrative outputs reference only",
            "deployment_status": "reference-only; no Azure services deployed or called",
        },
    }


def _with_overrides(
    config: GenAIConfig,
    output_directory: Path | None,
    overwrite: bool,
) -> GenAIConfig:
    if output_directory is None and not overwrite:
        return config
    output_dir = output_directory.resolve() if output_directory else config.genai.output_directory
    settings = config.genai
    return GenAIConfig(
        config_path=config.config_path,
        genai=type(settings)(
            evidence_catalog_path=output_dir / "evidence_catalog.json",
            output_directory=output_dir,
            report_directory=output_dir / "reports"
            if output_directory
            else settings.report_directory,
            overwrite=overwrite or settings.overwrite,
            random_seed=settings.random_seed,
            assistant_name=settings.assistant_name,
            mode=settings.mode,
            allow_external_model_calls=settings.allow_external_model_calls,
            require_citations=settings.require_citations,
            require_synthetic_data_disclaimer=settings.require_synthetic_data_disclaimer,
            maximum_response_words=settings.maximum_response_words,
        ),
        inputs=config.inputs,
        evidence=config.evidence,
        retrieval=config.retrieval,
        guardrails=config.guardrails,
        evaluation=config.evaluation,
        reporting=config.reporting,
    )


def _ensure_can_write(config: GenAIConfig) -> None:
    managed = [
        config.genai.output_directory / "evidence_catalog.json",
        config.genai.output_directory / "evidence_catalog.csv",
        config.genai.output_directory / "retrieval_results.json",
        config.genai.output_directory / "prompt_templates.json",
        config.genai.output_directory / "rendered_prompts.json",
        config.genai.output_directory / "assistant_responses.json",
        config.genai.output_directory / "assistant_responses.md",
        config.genai.output_directory / "guardrail_results.json",
        config.genai.output_directory / "assistant_evaluation.csv",
        config.genai.output_directory / "assistant_evaluation_summary.json",
        config.genai.output_directory / "genai_diagnostics.json",
        config.genai.output_directory / "genai-manifest.json",
        config.genai.output_directory / "lineage-records.json",
        config.genai.report_directory / "genai_operations_assistant_report.md",
        config.genai.report_directory / "genai_guardrails_report.md",
        config.genai.report_directory / "executive_manufacturing_brief.md",
        config.genai.report_directory / "supply_chain_summary.md",
        config.genai.report_directory / "manufacturing_operations_report.md",
    ]
    if config.genai.overwrite:
        return
    existing = [path for path in managed if path.exists()]
    if existing:
        raise PipelineExecutionError(f"GenAI outputs already exist: {existing}")


def _json_count(path: Path) -> int:
    payload = path.read_text(encoding="utf-8")
    import json

    value = json.loads(payload)
    return len(value) if isinstance(value, list) else 1


def _stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value
