"""Validation-only entry point for architecture outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manufacturing_intelligence.architecture.config import load_architecture_config
from manufacturing_intelligence.architecture.data import load_architecture_evidence
from manufacturing_intelligence.architecture.manifest import architecture_run_id, specification_hash
from manufacturing_intelligence.architecture.service_mapping import architecture_spec_payload
from manufacturing_intelligence.architecture.validation import validate_static_artefacts
from manufacturing_intelligence.common.exceptions import DataContractError


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
    infra_directory: Path | None = None,
) -> None:
    config = load_architecture_config(config_path)
    if output_directory or infra_directory:
        from manufacturing_intelligence.architecture.pipeline import with_overrides

        config = with_overrides(
            config,
            output_directory=output_directory,
            infra_directory=infra_directory,
            overwrite=False,
        )
    manifest_path = config.architecture.output_directory / "architecture-manifest.json"
    if not manifest_path.is_file():
        raise DataContractError("ARCHITECTURE_MANIFEST_MISSING")
    manifest = _read_json(manifest_path)
    evidence = load_architecture_evidence(config)
    expected_run_id = architecture_run_id(
        config,
        evidence.input_hashes,
        specification_hash(architecture_spec_payload()),
    )
    if manifest.get("architecture_run_id") != expected_run_id:
        raise DataContractError("ARCHITECTURE_RUN_ID_MISMATCH")
    if manifest.get("input_hashes") != evidence.input_hashes:
        raise DataContractError("ARCHITECTURE_UPSTREAM_HASH_MISMATCH")
    validate_static_artefacts(config, manifest)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError("ARCHITECTURE_MANIFEST_INVALID")
    return payload
