"""Lineage records for deterministic assistant outputs."""

from __future__ import annotations

from typing import Any


def lineage_records(
    *,
    run_id: str,
    sources: list[dict[str, Any]],
    outputs: dict[str, dict[str, Any]],
    configuration_hash: str,
) -> list[dict[str, Any]]:
    """Build deterministic lineage records."""
    source_refs = [
        {
            "source_path": item["relative_path"],
            "source_sha256": item["sha256"],
            "source_row_count": item["row_count"],
            "source_domain": item["domain"],
        }
        for item in sources
    ]
    records = []
    transformations = {
        "evidence_catalog_json": "catalogue governed evidence",
        "retrieval_results": "deterministic retrieval",
        "rendered_prompts": "prompt template rendering",
        "guardrail_results": "guardrail decisioning",
        "assistant_responses": "deterministic response synthesis",
        "assistant_evaluation": "deterministic assistant evaluation",
        "executive_manufacturing_brief": "portfolio narrative projection",
    }
    for name, output in sorted(outputs.items()):
        records.append(
            {
                "genai_run_id": run_id,
                "source_inputs": source_refs,
                "target_path": output["path"],
                "target_sha256": output["sha256"],
                "target_row_count": output["row_count"],
                "transformation_name": transformations.get(name, name),
                "configuration_hash": configuration_hash,
                "validation_status": "success",
                "synthetic_data_classification": "synthetic_portfolio_sample",
                "external_model_called": False,
            }
        )
    return records
