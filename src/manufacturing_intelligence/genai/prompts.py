"""Prompt templates that are rendered locally but never sent to a model."""

from __future__ import annotations

from typing import Any

SYNTHETIC_DISCLAIMER = (
    "This answer is based only on local synthetic manufacturing evidence and does not "
    "describe real customers, suppliers, employees, plants, products, or live operations."
)
NO_LIVE_OPERATIONS = "No external model, cloud service, or live operational system is called."


def prompt_templates() -> dict[str, str]:
    """Return deterministic prompt templates."""
    return {
        "system_instruction": (
            "You are a local deterministic manufacturing operations assistant. Use only "
            "provided evidence. Refuse unsupported or live-operation requests."
        ),
        "evidence_summary": "Evidence: {evidence_list}",
        "task_instruction": "Task: {task}. Answer with citations for every material claim.",
        "refusal": "I cannot answer because: {reason}. Allowed scope: local synthetic evidence.",
        "answer": "{answer}\n\nCitations: {citations}",
        "citation": "[{evidence_id}] {relative_path}",
        "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
        "no_live_operations_disclaimer": NO_LIVE_OPERATIONS,
    }


def render_prompt(task_type: str, question: str, retrieval: dict[str, Any]) -> dict[str, Any]:
    """Render a prompt for auditability without making an external call."""
    templates = prompt_templates()
    evidence_lines = []
    for item in retrieval["evidence_items"]:
        evidence_lines.append(
            f"{item['evidence_id']} | {item['domain']} | {item['relative_path']} | "
            f"sha256={item['sha256']}"
        )
    rendered = "\n".join(
        [
            templates["system_instruction"],
            templates["synthetic_data_disclaimer"],
            templates["no_live_operations_disclaimer"],
            templates["task_instruction"].format(task=task_type),
            templates["evidence_summary"].format(evidence_list="; ".join(evidence_lines)),
            "Guardrails: require citations; refuse live operations, real-world claims, "
            "safety-critical instructions, unsupported causal claims, external data, "
            "credentials, and validation override requests.",
            f"User question: {question}",
        ]
    )
    return {
        "task_type": task_type,
        "user_question": question,
        "rendered_prompt": rendered,
        "evidence_ids": [item["evidence_id"] for item in retrieval["evidence_items"]],
        "external_model_called": False,
    }
