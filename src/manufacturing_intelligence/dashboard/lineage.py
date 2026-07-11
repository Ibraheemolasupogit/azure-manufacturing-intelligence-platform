"""Dashboard lineage records."""

from __future__ import annotations

from typing import Any


def lineage_records(
    *,
    run_id: str,
    source_hashes: dict[str, str],
    outputs: dict[str, dict[str, Any]],
    configuration_hash: str,
) -> list[dict[str, Any]]:
    sources = [
        {"source_name": name, "source_sha256": sha256, "source_row_count": None}
        for name, sha256 in sorted(source_hashes.items())
    ]
    return [
        {
            "dashboard_run_id": run_id,
            "source_inputs": sources,
            "target_path": output["path"],
            "target_sha256": output["sha256"],
            "target_row_count": output["row_count"],
            "transformation_name": name,
            "configuration_hash": configuration_hash,
            "validation_status": "success",
            "synthetic_data_classification": "synthetic_portfolio_sample",
            "power_bi_deployment": False,
        }
        for name, output in sorted(outputs.items())
    ]
