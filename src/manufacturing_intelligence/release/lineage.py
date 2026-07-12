"""Release lineage records."""

from __future__ import annotations

from typing import Any


def lineage_records(
    *,
    run_id: str,
    source_hashes: dict[str, str],
    outputs: dict[str, dict[str, Any]],
    configuration_hash: str,
) -> list[dict[str, Any]]:
    return [
        {
            "release_run_id": run_id,
            "source_paths": sorted(source_hashes),
            "source_hashes": source_hashes,
            "target_name": name,
            "target_path": evidence["path"],
            "target_hash": evidence["sha256"],
            "target_row_count": evidence.get("row_count"),
            "transformation_name": "final_portfolio_evidence_consolidation",
            "configuration_hash": configuration_hash,
            "validation_status": "success",
            "synthetic_data_classification": "synthetic_portfolio_sample",
            "deployment_status": "local_reference_only",
            "purview_registration": False,
        }
        for name, evidence in sorted(outputs.items())
    ]
