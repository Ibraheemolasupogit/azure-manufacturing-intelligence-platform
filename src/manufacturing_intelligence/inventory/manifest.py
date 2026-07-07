"""Inventory manifest helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.inventory.config import InventoryConfig


def inventory_run_id(config: InventoryConfig, input_hashes: dict[str, str]) -> str:
    """Build deterministic inventory run ID."""
    payload = {
        "pipeline": "inventory_intelligence",
        "version": "0.1.0",
        "config_hash": semantic_config_hash(config),
        "input_hashes": input_hashes,
        "random_seed": config.inventory.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"INVENTORY-{digest[:16]}"


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


def semantic_config_hash(config: InventoryConfig) -> str:
    """Hash decision-relevant inventory configuration."""
    payload = {
        "inventory": {
            "random_seed": config.inventory.random_seed,
            "decision_grain": list(config.inventory.decision_grain),
            "planning_horizon_days": config.inventory.planning_horizon_days,
        },
        "policy": config.policy.__dict__,
        "optimisation": config.optimisation.__dict__,
        "scenarios": config.scenarios.__dict__,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def manifest_hash(path: Path) -> str:
    """Hash an upstream manifest."""
    return sha256_file(path)
