from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest
import yaml

from manufacturing_intelligence.common.exceptions import (
    ConfigurationError,
    DataContractError,
    PipelineExecutionError,
)
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.inventory.config import load_inventory_config
from manufacturing_intelligence.inventory.existing_run import validate_existing_run
from manufacturing_intelligence.inventory.pipeline import run_inventory
from manufacturing_intelligence.inventory.policy import reorder_quantity, service_factor


def test_inventory_uses_governed_inputs_and_preserves_upstream_files(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    upstream = {
        "inventory": project_root() / "data" / "interim" / "accepted" / "inventory_levels.csv",
        "supplier": project_root() / "data" / "interim" / "accepted" / "supplier_performance.csv",
        "warehouse": project_root() / "data" / "interim" / "accepted" / "warehouse_movements.csv",
        "forecast": project_root() / "outputs" / "demand_forecast.csv",
    }
    before = {name: sha256_file(path) for name, path in upstream.items()}

    result = run_inventory(config)
    after = {name: sha256_file(path) for name, path in upstream.items()}

    assert result.scored_rows == 72
    assert result.recommendation_rows > 0
    assert before == after
    manifest = json.loads((tmp_path / "inventory" / "inventory-manifest.json").read_text())
    assert manifest["upstream_ingestion_run_id"] == "INGEST-da9a11a67abc6a18"
    assert manifest["upstream_forecast_run_id"] == "FORECAST-6357daf22de3ea43"
    assert manifest["governed_input_hashes"]["inventory_levels"] == before["inventory"]
    assert manifest["decision_grain"] == ["warehouse_id", "item_id"]
    assert manifest["planning_horizon_days"] == 14
    assert manifest["azure_mapping"]["deployment_status"].startswith("reference-only")


def test_inventory_outputs_are_deterministic_and_policy_changes_run_id(tmp_path: Path) -> None:
    first = run_inventory(_config_for(tmp_path / "first"))
    second = run_inventory(_config_for(tmp_path / "second"))
    changed = run_inventory(
        _config_for(
            tmp_path / "changed",
            lambda payload: payload["policy"].update({"default_service_level": 0.98}),
        )
    )

    assert first.inventory_run_id == second.inventory_run_id
    assert first.inventory_run_id != changed.inventory_run_id
    assert _tree_bytes(first.output_directory) == _tree_bytes(second.output_directory)


def test_inventory_health_recommendations_and_scenarios_are_coherent(tmp_path: Path) -> None:
    result = run_inventory(_config_for(tmp_path))
    health = pd.read_csv(tmp_path / "inventory_scores.csv")
    recommendations = pd.read_csv(result.output_directory / "reorder_recommendations.csv")
    scenarios = pd.read_csv(result.output_directory / "scenario_results.csv")
    warehouse_demand = pd.read_csv(result.output_directory / "warehouse_demand_forecast.csv")

    assert len(health) == 72
    assert health["stockout_risk_score"].between(0, 100).all()
    assert (health["recommended_reorder_quantity"] >= 0).all()
    assert (
        health["recommended_reorder_point"] >= health["recommended_safety_stock_quantity"]
    ).all()
    assert not health.duplicated(["snapshot_timestamp", "warehouse_id", "item_id"]).any()
    assert set(recommendations["recommended_action"]) <= {
        "expedite_replenishment",
        "place_replenishment_order",
        "rebalance_or_reduce_excess_stock",
        "prioritise_consumption_before_expiry",
        "review_inventory_policy",
        "maintain_current_policy",
    }
    assert set(scenarios["scenario_name"]) == {
        "baseline",
        "high_demand",
        "supplier_delay",
        "budget_constrained",
        "capacity_constrained",
    }
    assert len(scenarios) == 5
    assert (
        recommendations["recommended_reorder_quantity"]
        <= recommendations["unconstrained_reorder_quantity"]
    ).all()
    forecast = pd.read_csv(project_root() / "outputs" / "demand_forecast.csv")
    allocated_total = warehouse_demand["allocated_point_forecast"].sum()
    assert allocated_total == pytest.approx(forecast["point_forecast"].sum())


def test_policy_math_rounding_and_service_factor() -> None:
    config = load_inventory_config()
    assert service_factor(0.95) == pytest.approx(1.65)
    assert reorder_quantity(85, config.policy) == 90
    assert reorder_quantity(-5, config.policy) == 0


def test_existing_run_validation_and_tamper_detection(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_inventory(config)
    validate_existing_run(config)
    with (tmp_path / "inventory_scores.csv").open("a", encoding="utf-8") as handle:
        handle.write("#tamper\n")

    with pytest.raises(DataContractError, match="MISMATCH"):
        validate_existing_run(config)


def test_direct_raw_inventory_input_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["inventory"].update(
            {"inventory_path": "data/raw/inventory_levels.csv"}
        ),
    )

    with pytest.raises(DataContractError, match="data/raw"):
        run_inventory(config)


def test_invalid_inventory_config_is_rejected(tmp_path: Path) -> None:
    config = _config_for(
        tmp_path,
        lambda payload: payload["policy"].update({"default_service_level": 1.5}),
    )

    with pytest.raises(ConfigurationError, match="probability"):
        load_inventory_config(config)


def test_inventory_overwrite_protection(tmp_path: Path) -> None:
    config = _config_for(tmp_path)
    run_inventory(config)

    with pytest.raises(PipelineExecutionError, match="already exist"):
        run_inventory(config)


def test_inventory_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output = tmp_path / "inventory"
    env = os.environ.copy()
    for key in (
        "COVERAGE_PROCESS_START",
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
    ):
        env.pop(key, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.inventory",
            "--config",
            str(project_root() / "configs" / "inventory.yaml"),
            "--output-directory",
            str(output),
            "--overwrite",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert completed.returncode == 0
    assert "Inventory INVENTORY-" in completed.stdout


def _config_for(
    tmp_path: Path,
    mutate: Any | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_load((project_root() / "configs" / "inventory.yaml").read_text())
    payload["inventory"].update(
        {
            "output_directory": str(tmp_path / "inventory"),
            "inventory_scores_path": str(tmp_path / "inventory_scores.csv"),
            "report_directory": str(tmp_path / "reports"),
            "overwrite": False,
        }
    )
    if mutate:
        mutate(payload)
    path = tmp_path / "inventory.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        child.relative_to(path).as_posix(): child.read_bytes()
        for child in sorted(path.rglob("*"))
        if child.is_file()
    }
