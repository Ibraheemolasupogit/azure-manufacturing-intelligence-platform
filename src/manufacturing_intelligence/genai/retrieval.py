"""Deterministic local evidence retrieval."""

from __future__ import annotations

import hashlib
from typing import Any

from manufacturing_intelligence.genai.config import GenAIConfig

INTENT_DOMAINS = {
    "executive_summary": (
        "generation",
        "ingestion",
        "forecasting",
        "inventory",
        "quality",
        "maintenance",
        "monitoring",
    ),
    "forecasting": ("forecasting", "inventory"),
    "inventory": ("inventory", "forecasting"),
    "quality": ("quality", "ingestion"),
    "maintenance": ("maintenance", "monitoring"),
    "monitoring": ("monitoring", "ingestion"),
    "lineage": ("ingestion", "forecasting", "inventory", "quality", "maintenance", "monitoring"),
    "data_quality": ("ingestion", "monitoring", "generation"),
}

TASK_QUESTIONS = {
    "executive_summary": (
        "Provide an executive operations brief for the synthetic manufacturing platform."
    ),
    "forecasting": "Summarize forecast outlook and inventory risk using governed evidence.",
    "inventory": "Explain the most important inventory risks and recommended local actions.",
    "quality": "Summarize current quality alerts and quality analytics evidence.",
    "maintenance": "Summarize maintenance risks and predictive maintenance alerts.",
    "monitoring": "Summarize platform health and observability status.",
    "lineage": "Explain governed data lineage from generation through analytics outputs.",
    "data_quality": "Summarize data quality and governance validation status.",
}


def infer_intent(question: str, task_type: str | None = None) -> str:
    """Infer a supported deterministic intent."""
    if task_type:
        return task_type
    text = question.lower()
    if any(word in text for word in ["forecast", "demand", "outlook"]):
        return "forecasting"
    if any(word in text for word in ["maintenance", "equipment", "machine", "sensor"]):
        return "maintenance"
    if any(word in text for word in ["inventory", "stock", "reorder", "supplier"]):
        return "inventory"
    if any(word in text for word in ["quality", "defect", "yield", "alert"]):
        return "quality"
    if any(word in text for word in ["health", "monitoring", "observability"]):
        return "monitoring"
    if "lineage" in text:
        return "lineage"
    if any(word in text for word in ["data quality", "validation", "governance"]):
        return "data_quality"
    return "executive_summary"


def retrieve_evidence(
    *,
    config: GenAIConfig,
    items: list[dict[str, Any]],
    question: str,
    task_type: str | None = None,
) -> dict[str, Any]:
    """Retrieve evidence with deterministic domain and keyword scoring."""
    intent = infer_intent(question, task_type)
    domains = INTENT_DOMAINS[intent]
    scored = []
    keywords = {token.strip(".,?:;").lower() for token in question.split() if len(token) > 3}
    for item in items:
        score = 0
        if item["domain"] in domains:
            score += 50
        if intent in item["supported_question_types"]:
            score += 30
        if item["evidence_type"] in {"manifest", "markdown_report"}:
            score += 10
        haystack = " ".join(
            [
                str(item["domain"]),
                str(item["title"]),
                str(item["description"]),
                " ".join(item["supported_question_types"]),
            ]
        ).lower()
        score += sum(1 for keyword in keywords if keyword in haystack)
        if score:
            scored.append((score, str(item["evidence_id"]), item))
    scored.sort(key=lambda value: (-value[0], value[1]))
    selected = [item for _, _, item in scored[: config.retrieval.maximum_evidence_items]]
    warnings = []
    if len(selected) < config.retrieval.minimum_evidence_items:
        warnings.append("Minimum evidence threshold not met")
    return {
        "query_id": _query_id(question, intent),
        "query_text": question,
        "inferred_intent": intent,
        "matched_domains": list(domains),
        "evidence_items": selected,
        "evidence_count": len(selected),
        "retrieval_warnings": warnings,
    }


def standard_queries(config: GenAIConfig, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return retrieval outputs for all supported standard tasks."""
    return [
        retrieve_evidence(config=config, items=items, question=question, task_type=task)
        for task, question in TASK_QUESTIONS.items()
    ]


def _query_id(question: str, intent: str) -> str:
    digest = hashlib.sha256(f"{intent}|{question}".encode()).hexdigest()[:12]
    return f"QUERY-{digest}"
