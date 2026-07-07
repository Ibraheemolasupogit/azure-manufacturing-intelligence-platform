"""CLI for quality analytics."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.quality.config import load_quality_config
from manufacturing_intelligence.quality.existing_run import validate_existing_run
from manufacturing_intelligence.quality.pipeline import run_quality


def main() -> int:
    """Run or validate quality analytics."""
    parser = argparse.ArgumentParser(description="Run governed quality analytics.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--quality-checks-path", type=Path, default=None)
    parser.add_argument("--production-events-path", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_quality_config(args.config)
            print(
                "Quality config valid: "
                f"{config.quality.quality_checks_path} -> {config.quality.output_directory}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing quality analytics run is valid.")
            return 0
        result = run_quality(
            args.config,
            quality_checks_path=args.quality_checks_path,
            production_events_path=args.production_events_path,
            output_directory=args.output_directory,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Quality {result.quality_run_id} processed {result.observation_rows} rows "
        f"and wrote {result.alert_rows} alerts to {result.output_directory}"
    )
    return 0
