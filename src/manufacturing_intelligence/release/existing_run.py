"""Validation-only entry point for final release artefacts."""

from __future__ import annotations

import json
from pathlib import Path

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.release.config import load_release_config
from manufacturing_intelligence.release.manifest import release_run_id
from manufacturing_intelligence.release.pipeline import _source_hashes, with_overrides
from manufacturing_intelligence.release.validation import validate_release_outputs


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    config = load_release_config(config_path)
    if output_directory:
        config = with_overrides(config, output_directory=output_directory, overwrite=False)
    manifest_path = config.release.output_directory / "release-manifest.json"
    if not manifest_path.is_file():
        raise DataContractError("RELEASE_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hashes = _source_hashes()
    expected = release_run_id(config, source_hashes)
    if manifest.get("release_run_id") != expected:
        raise DataContractError("RELEASE_RUN_ID_MISMATCH")
    if manifest.get("input_hashes") != source_hashes:
        raise DataContractError("RELEASE_UPSTREAM_HASH_MISMATCH")
    validate_release_outputs(config.release.output_directory, manifest)
