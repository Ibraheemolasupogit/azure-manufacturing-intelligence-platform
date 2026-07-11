"""CLI for dashboard output generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.dashboard.config import load_dashboard_config
from manufacturing_intelligence.dashboard.existing_run import validate_existing_run
from manufacturing_intelligence.dashboard.pipeline import run_dashboard


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local dashboard outputs.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--dashboard-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_config_only:
            config = load_dashboard_config(args.config)
            print(
                "Dashboard config valid: "
                f"{config.dashboard.output_directory} pages={len(config.dashboard_pages)}"
            )
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing dashboard run is valid.")
            return 0
        result = run_dashboard(
            args.config,
            output_directory=args.output_directory,
            dashboard_directory=args.dashboard_directory,
            overwrite=args.overwrite,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"Dashboard {result.dashboard_run_id} wrote {result.table_count} tables, "
        f"{result.metric_count} metrics, {result.page_count} pages, and "
        f"{result.visual_count} visual specs to {result.output_directory}"
    )
    return 0
