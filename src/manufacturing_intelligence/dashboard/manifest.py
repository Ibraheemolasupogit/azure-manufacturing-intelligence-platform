"""Dashboard manifest identity helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess

from manufacturing_intelligence.dashboard.config import DashboardConfig, semantic_config_payload


def semantic_config_hash(config: DashboardConfig) -> str:
    payload = json.dumps(semantic_config_payload(config), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def dashboard_run_id(config: DashboardConfig, input_hashes: dict[str, str]) -> str:
    payload = {
        "pipeline_name": "dashboard_outputs",
        "pipeline_version": "0.1.0",
        "configuration_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "pages": list(config.dashboard_pages),
        "random_seed": config.dashboard.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"DASHBOARD-{digest}"


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()
