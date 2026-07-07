"""CLI for inventory intelligence."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.inventory.config import load_inventory_config
from manufacturing_intelligence.inventory.existing_run import validate_existing_run
from manufacturing_intelligence.inventory.pipeline import run_inventory


def main() -> int:
    """Run or validate inventory intelligence."""
    parser = argparse.ArgumentParser(description="Run governed inventory intelligence.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--inventory-path", type=Path, default=None)
    parser.add_argument("--forecast-path", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--planning-horizon", type=int, default=None)
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--capacity", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_inventory_config(args.config)
            print(
                "Inventory config valid: "
                f"{config.inventory.inventory_path} -> {config.inventory.output_directory}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing inventory run is valid.")
            return 0
        result = run_inventory(
            args.config,
            inventory_path=args.inventory_path,
            forecast_path=args.forecast_path,
            output_directory=args.output_directory,
            planning_horizon=args.planning_horizon,
            budget=args.budget,
            capacity=args.capacity,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Inventory {result.inventory_run_id} scored {result.scored_rows} rows "
        f"and wrote {result.recommendation_rows} recommendations to {result.output_directory}"
    )
    return 0
