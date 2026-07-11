"""Command-line interface for Azure reference architecture artefacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.architecture.config import load_architecture_config
from manufacturing_intelligence.architecture.existing_run import validate_existing_run
from manufacturing_intelligence.architecture.pipeline import run_architecture


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--infra-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate_config_only:
        config = load_architecture_config(args.config)
        print(
            "Architecture config valid: "
            f"{config.architecture.output_directory} mode={config.architecture.deployment_mode}"
        )
        return 0
    if args.validate_existing_run:
        validate_existing_run(args.config, args.output_directory, args.infra_directory)
        print("Existing architecture run is valid.")
        return 0
    result = run_architecture(
        args.config,
        output_directory=args.output_directory,
        infra_directory=args.infra_directory,
        overwrite=args.overwrite,
    )
    print(
        f"Architecture {result.architecture_run_id} wrote "
        f"{result.service_mapping_count} service mappings, "
        f"{result.security_control_count} security controls, and "
        f"{result.adr_count} ADRs to {result.output_directory}"
    )
    return 0
