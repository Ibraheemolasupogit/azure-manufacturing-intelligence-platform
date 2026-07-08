"""CLI for predictive maintenance."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.maintenance.config import load_maintenance_config
from manufacturing_intelligence.maintenance.existing_run import validate_existing_run
from manufacturing_intelligence.maintenance.pipeline import run_maintenance


def main() -> int:
    """Run or validate predictive maintenance."""
    parser = argparse.ArgumentParser(description="Run governed predictive maintenance.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--equipment-health-path", type=Path, default=None)
    parser.add_argument("--production-events-path", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.validate_config_only:
            config = load_maintenance_config(args.config)
            print(
                "Maintenance config valid: "
                f"{config.maintenance.equipment_health_path} -> "
                f"{config.maintenance.output_directory}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing maintenance run is valid.")
            return 0
        result = run_maintenance(
            args.config,
            equipment_health_path=args.equipment_health_path,
            production_events_path=args.production_events_path,
            output_directory=args.output_directory,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Maintenance {result.maintenance_run_id} processed {result.equipment_rows} rows "
        f"and wrote {result.alert_rows} alerts to {result.output_directory}"
    )
    return 0
