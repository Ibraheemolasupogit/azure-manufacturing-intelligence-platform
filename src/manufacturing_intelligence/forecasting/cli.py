"""CLI for demand forecasting."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.forecasting.config import load_forecasting_config
from manufacturing_intelligence.forecasting.existing_run import validate_existing_run
from manufacturing_intelligence.forecasting.pipeline import run_forecast


def main() -> int:
    """Run or validate demand forecasting."""
    parser = argparse.ArgumentParser(description="Run governed demand forecasting.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--input-path", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--forecast-horizon", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_forecasting_config(args.config)
            print(
                "Forecasting config valid: "
                f"{config.forecasting.input_path} -> {config.forecasting.output_directory}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing forecast run is valid.")
            return 0
        result = run_forecast(
            args.config,
            input_path=args.input_path,
            output_directory=args.output_directory,
            forecast_horizon=args.forecast_horizon,
            seed=args.seed,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Forecast {result.forecast_run_id} selected {result.selected_model} "
        f"and wrote {result.forecast_rows} rows to {result.output_directory}"
    )
    return 0
