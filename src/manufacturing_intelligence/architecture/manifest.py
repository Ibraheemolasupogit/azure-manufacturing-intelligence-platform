"""Manifest and deterministic run identity helpers for architecture outputs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from manufacturing_intelligence.architecture.config import (
    ArchitectureConfig,
    semantic_config_payload,
)


def semantic_config_hash(config: ArchitectureConfig) -> str:
    payload = json.dumps(semantic_config_payload(config), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def architecture_run_id(
    config: ArchitectureConfig,
    input_hashes: dict[str, str],
    specification_hash: str,
) -> str:
    payload = {
        "pipeline_name": "azure_reference_architecture",
        "pipeline_version": "0.1.0",
        "configuration_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "random_seed": config.architecture.random_seed,
        "specification_hash": specification_hash,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"ARCH-{digest[:16]}"


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def specification_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
