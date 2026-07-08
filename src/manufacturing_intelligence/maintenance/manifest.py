"""Maintenance manifest helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.maintenance.config import MaintenanceConfig


def maintenance_run_id(config: MaintenanceConfig, input_hashes: dict[str, str]) -> str:
    """Build a deterministic maintenance run ID."""
    payload = {
        "pipeline": "predictive_maintenance",
        "version": "0.1.0",
        "config_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "random_seed": config.maintenance.random_seed,
        "models": list(config.anomaly_detection.models),
        "risk_scoring": config.risk_scoring.__dict__,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"MAINT-{digest[:16]}"


def semantic_config_hash(config: MaintenanceConfig) -> str:
    """Hash decision-relevant maintenance configuration."""
    payload = {
        "maintenance": {
            "random_seed": config.maintenance.random_seed,
            "timestamp_field": config.maintenance.timestamp_field,
            "primary_key": config.maintenance.primary_key,
        },
        "thresholds": config.thresholds.__dict__,
        "degradation": config.degradation.__dict__,
        "anomaly_detection": config.anomaly_detection.__dict__,
        "risk_scoring": config.risk_scoring.__dict__,
        "recommendations": config.recommendations.__dict__,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def manifest_hash(path: Path) -> str:
    """Hash an upstream manifest."""
    return sha256_file(path)


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
