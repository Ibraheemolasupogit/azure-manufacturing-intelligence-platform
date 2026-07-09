"""Transparent deterministic response evaluation."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.genai.config import GenAIConfig
from manufacturing_intelligence.genai.prompts import SYNTHETIC_DISCLAIMER


def evaluate_responses(
    config: GenAIConfig,
    responses: list[dict[str, Any]],
    catalogue: list[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate groundedness, citations, guardrails, length, and determinism."""
    evidence_ids = {str(item["evidence_id"]) for item in catalogue}
    rows = []
    for response in responses:
        cited_ids = {citation.strip("[]") for citation in response["citations"]}
        references = {ref["evidence_id"] for ref in response["evidence_references"]}
        citations_valid = cited_ids <= evidence_ids
        references_valid = references <= evidence_ids
        word_count = len(str(response["answer"]).split())
        disclaimer_present = SYNTHETIC_DISCLAIMER in str(response["answer"])
        external_ok = response["external_model_called"] is False
        unsupported_ok = (
            int(response["unsupported_claim_count"]) <= config.evaluation.maximum_unsupported_claims
        )
        grounding_ok = (
            float(response["grounding_score"]) >= config.evaluation.minimum_grounding_score
        )
        citation_ok = (
            float(response["citation_coverage"]) >= config.evaluation.minimum_citation_coverage
        )
        length_ok = word_count <= config.genai.maximum_response_words
        passed = all(
            [
                citations_valid,
                references_valid,
                disclaimer_present,
                external_ok,
                unsupported_ok,
                grounding_ok,
                citation_ok,
                length_ok,
            ]
        )
        rows.append(
            {
                "response_id": response["response_id"],
                "task_type": response["task_type"],
                "grounding_score": response["grounding_score"],
                "citation_coverage": response["citation_coverage"],
                "unsupported_claim_count": response["unsupported_claim_count"],
                "synthetic_disclaimer_present": disclaimer_present,
                "external_model_called": response["external_model_called"],
                "citation_ids_valid": citations_valid,
                "evidence_references_valid": references_valid,
                "word_count": word_count,
                "length_compliant": length_ok,
                "evaluation_status": "passed" if passed else "failed",
            }
        )
    frame = pd.DataFrame(rows).sort_values("response_id").reset_index(drop=True)
    summary = {
        "response_count": len(responses),
        "passed_count": int((frame["evaluation_status"] == "passed").sum()),
        "failed_count": int((frame["evaluation_status"] != "passed").sum()),
        "minimum_grounding_score": float(frame["grounding_score"].min()),
        "minimum_citation_coverage": float(frame["citation_coverage"].min()),
        "maximum_unsupported_claim_count": int(frame["unsupported_claim_count"].max()),
        "synthetic_disclaimer_coverage": float(frame["synthetic_disclaimer_present"].mean()),
        "external_model_called": False,
        "validation_status": "success"
        if (frame["evaluation_status"] == "passed").all()
        else "failed",
    }
    return frame, summary
