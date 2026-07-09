"""Configuration loading for the deterministic local GenAI assistant."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

SUPPORTED_DOMAINS = {
    "generation",
    "ingestion",
    "forecasting",
    "inventory",
    "quality",
    "maintenance",
    "monitoring",
}
SUPPORTED_ANSWER_DOMAINS = {
    "executive_summary",
    "forecasting",
    "inventory",
    "quality",
    "maintenance",
    "monitoring",
    "lineage",
    "data_quality",
}


@dataclass(frozen=True)
class GenAISettings:
    """Assistant run settings."""

    evidence_catalog_path: Path
    output_directory: Path
    report_directory: Path
    overwrite: bool
    random_seed: int
    assistant_name: str
    mode: str
    allow_external_model_calls: bool
    require_citations: bool
    require_synthetic_data_disclaimer: bool
    maximum_response_words: int


@dataclass(frozen=True)
class GenAIInputs:
    """Governed local evidence inputs."""

    generation_manifest_path: Path
    schema_metadata_path: Path
    ingestion_manifest_path: Path
    validation_summary_path: Path
    data_quality_report_path: Path
    data_quality_markdown_path: Path
    ingestion_lineage_path: Path
    forecast_manifest_path: Path
    forecast_lineage_path: Path
    demand_forecast_path: Path
    forecast_report_path: Path
    inventory_manifest_path: Path
    inventory_lineage_path: Path
    inventory_scores_path: Path
    inventory_report_path: Path
    quality_manifest_path: Path
    quality_lineage_path: Path
    quality_alerts_path: Path
    quality_report_path: Path
    maintenance_manifest_path: Path
    maintenance_lineage_path: Path
    maintenance_predictions_path: Path
    maintenance_report_path: Path
    monitoring_manifest_path: Path
    monitoring_lineage_path: Path
    platform_health_summary_path: Path
    monitoring_report_path: Path


@dataclass(frozen=True)
class EvidenceSettings:
    """Evidence catalogue settings."""

    required_domains: tuple[str, ...]
    include_reports: bool
    include_manifests: bool
    include_diagnostics: bool
    include_lineage: bool


@dataclass(frozen=True)
class RetrievalSettings:
    """Deterministic retrieval settings."""

    method: str
    maximum_evidence_items: int
    minimum_evidence_items: int
    include_file_hashes: bool
    include_row_counts: bool


@dataclass(frozen=True)
class GuardrailSettings:
    """Assistant guardrail settings."""

    refuse_ungrounded_answers: bool
    refuse_live_operational_commands: bool
    refuse_safety_critical_claims: bool
    refuse_real_world_claims: bool
    require_local_evidence_references: bool
    allowed_answer_domains: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationSettings:
    """Assistant evaluation thresholds."""

    write_eval_results: bool
    minimum_grounding_score: float
    minimum_citation_coverage: float
    maximum_unsupported_claims: int


@dataclass(frozen=True)
class ReportingSettings:
    """Report settings."""

    maximum_example_answers: int
    write_markdown_report: bool


@dataclass(frozen=True)
class GenAIConfig:
    """Complete GenAI assistant configuration."""

    config_path: Path
    genai: GenAISettings
    inputs: GenAIInputs
    evidence: EvidenceSettings
    retrieval: RetrievalSettings
    guardrails: GuardrailSettings
    evaluation: EvaluationSettings
    reporting: ReportingSettings


def load_genai_config(config_path: Path | None = None) -> GenAIConfig:
    """Load and validate GenAI assistant configuration."""
    path = (
        resolve_project_path(config_path)
        if config_path
        else project_root() / "configs" / "genai.yaml"
    )
    if not path.is_file():
        raise ConfigurationError(f"GenAI config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("GenAI config must contain a mapping")
    genai = _section(payload, "genai")
    inputs = _section(payload, "inputs")
    evidence = _section(payload, "evidence")
    retrieval = _section(payload, "retrieval")
    guardrails = _section(payload, "guardrails")
    evaluation = _section(payload, "evaluation")
    reporting = _section(payload, "reporting")

    mode = _required_str(genai, "mode")
    if mode != "deterministic_local":
        raise ConfigurationError("Only deterministic_local GenAI mode is supported")
    if _required_bool(genai, "allow_external_model_calls"):
        raise ConfigurationError("External model calls must be disabled")
    required_domains = tuple(_str_list(evidence, "required_domains"))
    unsupported_domains = sorted(set(required_domains) - SUPPORTED_DOMAINS)
    if unsupported_domains:
        raise ConfigurationError(f"Unsupported GenAI evidence domains: {unsupported_domains}")
    if len(set(required_domains)) != len(required_domains):
        raise ConfigurationError("evidence.required_domains must be unique")
    allowed = tuple(_str_list(guardrails, "allowed_answer_domains"))
    unsupported_answers = sorted(set(allowed) - SUPPORTED_ANSWER_DOMAINS)
    if unsupported_answers:
        raise ConfigurationError(f"Unsupported GenAI answer domains: {unsupported_answers}")
    max_items = _positive_int(retrieval, "maximum_evidence_items")
    min_items = _positive_int(retrieval, "minimum_evidence_items")
    if min_items > max_items:
        raise ConfigurationError("minimum_evidence_items cannot exceed maximum_evidence_items")

    output_directory = resolve_project_path(_required_str(genai, "output_directory"))
    evidence_catalog_path = resolve_project_path(_required_str(genai, "evidence_catalog_path"))
    input_paths = [_resolve_input(inputs, field) for field in GenAIInputs.__dataclass_fields__]
    for input_path in input_paths:
        if _is_relative_to(input_path, output_directory) or input_path == evidence_catalog_path:
            raise ConfigurationError("GenAI outputs must not overlap governed inputs")
    if ".generated" not in output_directory.parts and output_directory.name != "genai":
        raise ConfigurationError("GenAI output directory must be outputs/genai or .generated")

    return GenAIConfig(
        config_path=path.resolve(),
        genai=GenAISettings(
            evidence_catalog_path=evidence_catalog_path,
            output_directory=output_directory,
            report_directory=resolve_project_path(_required_str(genai, "report_directory")),
            overwrite=_required_bool(genai, "overwrite"),
            random_seed=_positive_int(genai, "random_seed"),
            assistant_name=_required_str(genai, "assistant_name"),
            mode=mode,
            allow_external_model_calls=False,
            require_citations=_required_bool(genai, "require_citations"),
            require_synthetic_data_disclaimer=_required_bool(
                genai, "require_synthetic_data_disclaimer"
            ),
            maximum_response_words=_positive_int(genai, "maximum_response_words"),
        ),
        inputs=GenAIInputs(
            **{field: _resolve_input(inputs, field) for field in GenAIInputs.__dataclass_fields__}
        ),
        evidence=EvidenceSettings(
            required_domains=required_domains,
            include_reports=_required_bool(evidence, "include_reports"),
            include_manifests=_required_bool(evidence, "include_manifests"),
            include_diagnostics=_required_bool(evidence, "include_diagnostics"),
            include_lineage=_required_bool(evidence, "include_lineage"),
        ),
        retrieval=RetrievalSettings(
            method=_required_str(retrieval, "method"),
            maximum_evidence_items=max_items,
            minimum_evidence_items=min_items,
            include_file_hashes=_required_bool(retrieval, "include_file_hashes"),
            include_row_counts=_required_bool(retrieval, "include_row_counts"),
        ),
        guardrails=GuardrailSettings(
            refuse_ungrounded_answers=_required_bool(guardrails, "refuse_ungrounded_answers"),
            refuse_live_operational_commands=_required_bool(
                guardrails, "refuse_live_operational_commands"
            ),
            refuse_safety_critical_claims=_required_bool(
                guardrails, "refuse_safety_critical_claims"
            ),
            refuse_real_world_claims=_required_bool(guardrails, "refuse_real_world_claims"),
            require_local_evidence_references=_required_bool(
                guardrails, "require_local_evidence_references"
            ),
            allowed_answer_domains=allowed,
        ),
        evaluation=EvaluationSettings(
            write_eval_results=_required_bool(evaluation, "write_eval_results"),
            minimum_grounding_score=_fraction(evaluation, "minimum_grounding_score"),
            minimum_citation_coverage=_fraction(evaluation, "minimum_citation_coverage"),
            maximum_unsupported_claims=_non_negative_int(evaluation, "maximum_unsupported_claims"),
        ),
        reporting=ReportingSettings(
            maximum_example_answers=_positive_int(reporting, "maximum_example_answers"),
            write_markdown_report=_required_bool(reporting, "write_markdown_report"),
        ),
    )


def semantic_config_payload(config: GenAIConfig) -> dict[str, Any]:
    """Return a stable subset of config values for hashing."""
    return {
        "genai": {
            "random_seed": config.genai.random_seed,
            "assistant_name": config.genai.assistant_name,
            "mode": config.genai.mode,
            "allow_external_model_calls": config.genai.allow_external_model_calls,
            "require_citations": config.genai.require_citations,
            "require_synthetic_data_disclaimer": config.genai.require_synthetic_data_disclaimer,
            "maximum_response_words": config.genai.maximum_response_words,
        },
        "evidence": {"required_domains": list(config.evidence.required_domains)},
        "retrieval": {
            "method": config.retrieval.method,
            "maximum_evidence_items": config.retrieval.maximum_evidence_items,
            "minimum_evidence_items": config.retrieval.minimum_evidence_items,
        },
        "guardrails": {
            "allowed_answer_domains": list(config.guardrails.allowed_answer_domains),
            "refuse_ungrounded_answers": config.guardrails.refuse_ungrounded_answers,
            "refuse_live_operational_commands": config.guardrails.refuse_live_operational_commands,
            "refuse_safety_critical_claims": config.guardrails.refuse_safety_critical_claims,
            "refuse_real_world_claims": config.guardrails.refuse_real_world_claims,
        },
        "evaluation": {
            "minimum_grounding_score": config.evaluation.minimum_grounding_score,
            "minimum_citation_coverage": config.evaluation.minimum_citation_coverage,
            "maximum_unsupported_claims": config.evaluation.maximum_unsupported_claims,
        },
    }


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"GenAI config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    if value.lower() in {"live", "deploy", "azure", "openai"}:
        raise ConfigurationError("Live deployment modes and model providers are not supported")
    return value


def _resolve_input(section: dict[str, Any], key: str) -> Path:
    return resolve_project_path(_required_str(section, key))


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean missing: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Required positive integer missing: {key}")
    return value


def _non_negative_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"Required non-negative integer missing: {key}")
    return value


def _fraction(section: dict[str, Any], key: str) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= float(value) <= 1:
        raise ConfigurationError(f"Threshold must be between 0 and 1: {key}")
    return float(value)


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ConfigurationError(f"Required string list missing: {key}")
    return list(value)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
