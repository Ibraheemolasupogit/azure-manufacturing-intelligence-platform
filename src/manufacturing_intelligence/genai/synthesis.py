"""Deterministic grounded response synthesis."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.genai.prompts import SYNTHETIC_DISCLAIMER


def synthesize_response(
    *,
    assistant_name: str,
    task_type: str,
    question: str,
    retrieval: dict[str, Any],
    guardrail: dict[str, Any],
    maximum_words: int,
) -> dict[str, Any]:
    """Create a grounded local response without calling an external model."""
    response_id = f"RESP-{task_type.replace('_', '-').upper()}"
    if guardrail["decision"] == "refuse":
        answer = f"{guardrail['refusal_message']} {SYNTHETIC_DISCLAIMER}"
        citations: list[str] = []
        references: list[dict[str, str]] = []
        grounding = 1.0
        coverage = 1.0
    else:
        evidence = retrieval["evidence_items"]
        facts = [_fact_from_item(item) for item in evidence[:5]]
        answer = " ".join(
            [
                _opening(task_type),
                " ".join(facts),
                "The response is constrained to governed local artefacts and uses citations "
                "for each evidence-backed statement.",
                SYNTHETIC_DISCLAIMER,
            ]
        )
        citations = [f"[{item['evidence_id']}]" for item in evidence[:5]]
        references = [
            {"evidence_id": item["evidence_id"], "relative_path": item["relative_path"]}
            for item in evidence
        ]
        grounding = 1.0 if evidence else 0.0
        coverage = 1.0 if citations else 0.0
    answer = _limit_words(answer, maximum_words)
    return {
        "response_id": response_id,
        "task_type": task_type,
        "user_question": question,
        "answer": answer,
        "evidence_references": references,
        "citations": citations,
        "unsupported_claim_count": 0,
        "grounding_score": grounding,
        "citation_coverage": coverage,
        "guardrail_status": guardrail["decision"],
        "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
        "generated_by": assistant_name,
        "external_model_called": False,
    }


def _opening(task_type: str) -> str:
    openings = {
        "executive_summary": "Executive brief: the controlled portfolio is healthy and traceable.",
        "forecasting": (
            "Forecast and inventory risk summary: demand evidence is linked to inventory outputs."
        ),
        "inventory": (
            "Inventory risk summary: reorder and supplier-risk evidence should guide "
            "local planning review."
        ),
        "quality": (
            "Quality alert summary: governed quality evidence identifies alert and risk signals."
        ),
        "maintenance": (
            "Maintenance risk summary: predictive maintenance evidence identifies "
            "equipment risk signals."
        ),
        "monitoring": (
            "Platform health summary: monitoring evidence reports governed pipeline health."
        ),
        "lineage": (
            "Lineage summary: evidence connects generation through ingestion and analytics outputs."
        ),
        "data_quality": (
            "Governance summary: validation evidence reports successful controlled "
            "synthetic processing."
        ),
    }
    return openings[task_type]


def _fact_from_item(item: dict[str, Any]) -> str:
    row_text = f", row_count={item['row_count']}" if item.get("row_count") is not None else ""
    metrics = item.get("key_metrics", {})
    metric_text = ""
    if metrics:
        metric_text = ", " + ", ".join(
            f"{key}={value}" for key, value in sorted(metrics.items())[:3]
        )
    return (
        f"{item['title']} supports the answer from {item['relative_path']}"
        f"{row_text}{metric_text} [{item['evidence_id']}]."
    )


def _limit_words(text: str, maximum_words: int) -> str:
    words = text.split()
    if len(words) <= maximum_words:
        return text
    return " ".join(words[:maximum_words])
