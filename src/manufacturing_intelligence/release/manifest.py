"""Release manifest and run identity helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess

from manufacturing_intelligence.release.config import ReleaseConfig, semantic_config_payload


def semantic_config_hash(config: ReleaseConfig) -> str:
    payload = json.dumps(semantic_config_payload(config), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def release_run_id(config: ReleaseConfig, source_hashes: dict[str, str]) -> str:
    payload = {
        "pipeline_name": "final_portfolio_release",
        "pipeline_version": "0.1.0",
        "configuration_hash": semantic_config_hash(config),
        "source_hashes": source_hashes,
        "random_seed": config.release.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"REL-{digest[:16]}"


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


def manifest_source_hashes(paths: list[str], hashes: dict[str, str]) -> dict[str, str]:
    return {path: hashes[path] for path in sorted(paths) if path in hashes}
