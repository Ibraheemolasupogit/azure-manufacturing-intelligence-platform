"""Quality manifest helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.quality.config import QualityConfig


def quality_run_id(config: QualityConfig, input_hashes: dict[str, str]) -> str:
    """Build deterministic quality run ID."""
    payload = {
        "pipeline": "quality_analytics",
        "version": "0.1.0",
        "config_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "random_seed": config.quality.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"QUALITY-{digest[:16]}"


def semantic_config_hash(config: QualityConfig) -> str:
    """Hash decision-relevant quality configuration."""
    payload = {
        "quality": {
            "random_seed": config.quality.random_seed,
            "timestamp_field": config.quality.timestamp_field,
            "primary_key": config.quality.primary_key,
            "trend_grain": list(config.quality.trend_grain),
            "alert_grain": list(config.quality.alert_grain),
        },
        "specification": config.specification.__dict__,
        "spc": config.spc.__dict__,
        "capability": config.capability.__dict__,
        "anomaly_detection": config.anomaly_detection.__dict__,
        "risk_scoring": config.risk_scoring.__dict__,
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
