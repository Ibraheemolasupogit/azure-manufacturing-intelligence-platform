"""CLI helpers for deterministic synthetic data generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.data_generation.generator import (
    generate_synthetic_data,
    load_synthetic_config,
    validate_generated_run,
)


def main() -> int:
    """Generate deterministic Milestone 2 synthetic datasets."""
    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic manufacturing data."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to synthetic data YAML config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated raw files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace generated files managed by the generator.",
    )
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Validate an existing generated run without regenerating files.",
    )
    parser.add_argument(
        "--validate-config-only",
        action="store_true",
        help="Load and validate configuration without writing files.",
    )
    args = parser.parse_args()

    if args.validate_config_only:
        config = load_synthetic_config(args.config)
        print(
            "Synthetic data config valid: "
            f"{config.config_version}, {config.generation_mode}, seed {config.random_seed}"
        )
        return 0

    if args.validate_existing:
        validate_generated_run(args.output_dir)
        print(f"Generated synthetic data run is valid in {args.output_dir or 'data/raw'}")
        return 0

    result = generate_synthetic_data(
        config_path=args.config,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    print(f"Generated synthetic data run {result.run_id} in {result.raw_data_dir}")
    for dataset in result.datasets:
        print(f"- {dataset.dataset_name}: {dataset.row_count} rows -> {dataset.path.name}")
    return 0
