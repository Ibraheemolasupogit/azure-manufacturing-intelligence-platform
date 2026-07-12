"""Command-line interface for final release artefacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.release.config import load_release_config
from manufacturing_intelligence.release.existing_run import validate_existing_run
from manufacturing_intelligence.release.pipeline import run_release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate_config_only:
        config = load_release_config(args.config)
        print(
            "Release config valid: "
            f"{config.release.output_directory} mode={config.release.release_mode}"
        )
        return 0
    if args.validate_existing_run:
        validate_existing_run(args.config, args.output_directory)
        print("Existing release run is valid.")
        return 0
    result = run_release(
        args.config,
        output_directory=args.output_directory,
        overwrite=args.overwrite,
    )
    print(
        f"Release {result.release_run_id} wrote {result.evidence_count} evidence rows, "
        f"{result.report_count} report rows, and {result.catalogue_count} catalogues "
        f"to {result.output_directory}"
    )
    return 0
