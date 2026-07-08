"""Monitoring manifest helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.maintenance.manifest import manifest_hash
from manufacturing_intelligence.monitoring.config import MonitoringConfig


def monitoring_run_id(config: MonitoringConfig, input_hashes: dict[str, str]) -> str:
    """Build deterministic monitoring run ID."""
    payload = {
        "pipeline": "platform_monitoring",
        "version": "0.1.0",
        "config_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "thresholds": config.thresholds.__dict__,
        "random_seed": config.monitoring.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"MONITOR-{digest[:16]}"


def semantic_config_hash(config: MonitoringConfig) -> str:
    """Hash decision-relevant monitoring config."""
    payload = {
        "monitoring": {
            "random_seed": config.monitoring.random_seed,
            "required_domains": list(config.monitoring.required_domains),
        },
        "thresholds": config.thresholds.__dict__,
        "reporting": config.reporting.__dict__,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def git_commit() -> str:
    """Return current Git commit if available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()


__all__ = [
    "git_commit",
    "manifest_hash",
    "monitoring_run_id",
    "semantic_config_hash",
    "sha256_file",
]
