"""CLI for governed ingestion."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.ingestion.config import load_ingestion_config
from manufacturing_intelligence.ingestion.existing_run import validate_existing_run
from manufacturing_intelligence.ingestion.pipeline import run_ingestion


def main() -> int:
    """Run or validate governed ingestion."""
    parser = argparse.ArgumentParser(description="Run governed manufacturing data ingestion.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--input-directory", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--mode", choices=("strict", "permissive"), default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_ingestion_config(args.config)
            print(
                "Ingestion config valid: "
                f"{config.ingestion.mode}, {config.ingestion.input_directory} -> "
                f"{config.ingestion.output_directory}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing ingestion run is valid.")
            return 0
        result = run_ingestion(
            args.config,
            input_directory=args.input_directory,
            output_directory=args.output_directory,
            mode=args.mode,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Ingestion {result.ingestion_run_id} completed with status "
        f"{result.validation_status} in {result.output_directory}"
    )
    return 0
