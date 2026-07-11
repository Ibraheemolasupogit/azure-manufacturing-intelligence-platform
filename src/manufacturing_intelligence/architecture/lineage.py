"""Lineage records for architecture blueprint outputs."""

from __future__ import annotations

from typing import Any

from manufacturing_intelligence.architecture.artefacts import SYNTHETIC_CLASSIFICATION


def lineage_records(
    *,
    run_id: str,
    source_hashes: dict[str, str],
    outputs: dict[str, dict[str, Any]],
    configuration_hash: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for target_name, evidence in sorted(outputs.items()):
        records.append(
            {
                "architecture_run_id": run_id,
                "source_paths": sorted(source_hashes),
                "source_hashes": source_hashes,
                "target_name": target_name,
                "target_path": evidence["path"],
                "target_hash": evidence["sha256"],
                "target_row_count": evidence.get("row_count"),
                "transformation_name": "azure_reference_architecture_static_mapping",
                "configuration_hash": configuration_hash,
                "validation_status": "success",
                "synthetic_data_classification": SYNTHETIC_CLASSIFICATION,
                "deployment_mode": "reference_only",
                "purview_registration": False,
            }
        )
    return records
