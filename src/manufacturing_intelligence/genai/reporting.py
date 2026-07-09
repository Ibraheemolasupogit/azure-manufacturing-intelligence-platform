"""Markdown report writers for GenAI assistant outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_markdown(path: Path, title: str, body: str) -> None:
    """Write a deterministic Markdown document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{body.rstrip()}\n", encoding="utf-8")


def assistant_responses_markdown(responses: list[dict[str, Any]]) -> str:
    """Render assistant responses as Markdown."""
    sections = []
    for response in responses:
        citations = ", ".join(response["citations"]) or "none"
        sections.append(
            "\n".join(
                [
                    f"## {response['task_type']}",
                    "",
                    f"Question: {response['user_question']}",
                    "",
                    response["answer"],
                    "",
                    f"Citations: {citations}",
                ]
            )
        )
    return "\n\n".join(sections)


def operations_report(
    *,
    run_id: str,
    evidence_count: int,
    response_count: int,
    guardrail_count: int,
    evaluation_summary: dict[str, Any],
) -> str:
    """Render the controlled assistant report body."""
    return "\n".join(
        [
            f"Run ID: {run_id}",
            "",
            "This deterministic local assistant uses governed synthetic evidence only. "
            "It does not call an LLM, Azure OpenAI, Azure AI Foundry, the internet, "
            "a vector database, or any external endpoint.",
            "",
            f"- Evidence items: {evidence_count}",
            f"- Assistant responses: {response_count}",
            f"- Guardrail results: {guardrail_count}",
            f"- Minimum grounding score: {evaluation_summary['minimum_grounding_score']:.6f}",
            f"- Minimum citation coverage: {evaluation_summary['minimum_citation_coverage']:.6f}",
            "- Maximum unsupported claims: "
            f"{evaluation_summary['maximum_unsupported_claim_count']}",
            "- External model called: false",
            "",
            "Azure services are reference architecture mappings only; no Azure AI services "
            "were deployed or called.",
        ]
    )
