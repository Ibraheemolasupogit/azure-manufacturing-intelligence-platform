"""Manifest helpers for the deterministic assistant."""

from __future__ import annotations

import hashlib
import json
import subprocess

from manufacturing_intelligence.genai.config import GenAIConfig, semantic_config_payload


def semantic_config_hash(config: GenAIConfig) -> str:
    """Hash stable GenAI config semantics."""
    payload = json.dumps(semantic_config_payload(config), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def genai_run_id(
    config: GenAIConfig,
    *,
    evidence_catalogue_hash: str,
    input_hashes: dict[str, str],
) -> str:
    """Derive deterministic GenAI run identity."""
    payload = {
        "pipeline_name": "genai_operations_assistant",
        "pipeline_version": "0.1.0",
        "configuration_hash": semantic_config_hash(config),
        "evidence_catalogue_hash": evidence_catalogue_hash,
        "input_hashes": input_hashes,
        "guardrails": semantic_config_payload(config)["guardrails"],
        "prompt_templates": "deterministic-local-v1",
        "random_seed": config.genai.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"GENAI-{digest}"


def git_commit() -> str | None:
    """Return current Git commit if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip()
