"""Forecast manifest helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.forecasting.config import ForecastingConfig


def forecast_run_id(config: ForecastingConfig, input_hash: str, manifest_hash: str) -> str:
    """Build deterministic forecast run ID."""
    payload = {
        "pipeline": "demand_forecasting",
        "version": "0.1.0",
        "config_hash": semantic_config_hash(config),
        "input_hash": input_hash,
        "ingestion_manifest_hash": manifest_hash,
        "features": {
            "lags": config.features.lag_days,
            "rolling_windows": config.features.rolling_windows,
        },
        "models": config.models.enabled,
        "random_seed": config.forecasting.random_seed,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"FORECAST-{digest[:16]}"


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


def manifest_hash(path: Path) -> str:
    """Hash an upstream manifest."""
    return sha256_file(path)


def semantic_config_hash(config: ForecastingConfig) -> str:
    payload = {
        "forecasting": {
            "frequency": config.forecasting.frequency,
            "target_field": config.forecasting.target_field,
            "date_field": config.forecasting.date_field,
            "series_keys": config.forecasting.series_keys,
            "forecast_horizon_days": config.forecasting.forecast_horizon_days,
            "minimum_history_days": config.forecasting.minimum_history_days,
            "prediction_interval_level": config.forecasting.prediction_interval_level,
            "random_seed": config.forecasting.random_seed,
        },
        "splitting": config.splitting.__dict__,
        "features": config.features.__dict__,
        "models": config.models.__dict__,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def serializable_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Convert non-JSON metric values."""
    return {key: (None if value != value else value) for key, value in metrics.items()}
