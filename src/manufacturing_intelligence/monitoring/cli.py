"""CLI for monitoring and observability."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.monitoring.config import load_monitoring_config
from manufacturing_intelligence.monitoring.existing_run import validate_existing_run
from manufacturing_intelligence.monitoring.pipeline import run_monitoring


def main() -> int:
    """Run or validate monitoring."""
    parser = argparse.ArgumentParser(description="Run local platform monitoring.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_monitoring_config(args.config)
            print(
                "Monitoring config valid: "
                f"{config.monitoring.output_directory} domains="
                f"{','.join(config.monitoring.required_domains)}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing monitoring run is valid.")
            return 0
        result = run_monitoring(
            args.config,
            output_directory=args.output_directory,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Monitoring {result.monitoring_run_id} scored platform health "
        f"{result.platform_health_score:.2f} and wrote {result.alert_rows} alerts "
        f"to {result.output_directory}"
    )
    return 0
