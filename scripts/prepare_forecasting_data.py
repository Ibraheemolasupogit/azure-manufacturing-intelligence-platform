"""Prepare extended governed forecasting data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.data_generation.generator import (
    generate_synthetic_data,
    validate_generated_run,
)
from manufacturing_intelligence.data_generation.schemas import SCHEMAS
from manufacturing_intelligence.ingestion.existing_run import validate_existing_run
from manufacturing_intelligence.ingestion.pipeline import run_ingestion


def main() -> int:
    """Prepare and verify the extended forecasting dataset."""
    parser = argparse.ArgumentParser(description="Prepare extended governed forecasting data.")
    parser.add_argument(
        "--synthetic-config",
        type=Path,
        default=Path("configs/synthetic_data_forecasting.yaml"),
    )
    parser.add_argument(
        "--ingestion-config",
        type=Path,
        default=Path("configs/ingestion_forecasting.yaml"),
    )
    parser.add_argument("--raw-output-dir", type=Path, default=Path(".generated/forecasting/raw"))
    parser.add_argument(
        "--interim-output-dir",
        type=Path,
        default=Path(".generated/forecasting/interim"),
    )
    parser.add_argument("--allowed-sales-quarantine-rate", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        generation = generate_synthetic_data(
            config_path=args.synthetic_config,
            output_dir=args.raw_output_dir,
            overwrite=args.overwrite,
        )
        validate_generated_run(args.raw_output_dir)
        ingestion = run_ingestion(
            args.ingestion_config,
            input_directory=args.raw_output_dir,
            output_directory=args.interim_output_dir,
            overwrite=args.overwrite,
        )
        validate_existing_run(args.ingestion_config, args.interim_output_dir)
        summary_path = args.interim_output_dir / "_metadata" / "validation-summary.json"
        manifest_path = args.interim_output_dir / "_metadata" / "ingestion-manifest.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _verify_summary(summary, args.allowed_sales_quarantine_rate)
        _verify_sales_hash(args.interim_output_dir, manifest)
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1

    print(f"Extended generation run {generation.run_id} is valid in {generation.raw_data_dir}")
    print(
        f"Extended ingestion run {ingestion.ingestion_run_id} is valid in "
        f"{ingestion.output_directory}"
    )
    print(
        "Extended sales orders: "
        f"source={summary['source_counts_by_dataset']['sales_orders']} "
        f"accepted={summary['accepted_counts_by_dataset']['sales_orders']} "
        f"quarantine={summary['quarantine_counts_by_dataset']['sales_orders']}"
    )
    return 0


def _verify_summary(summary: dict[str, object], allowed_rate: float) -> None:
    discovered = set(summary["discovered_datasets"])  # type: ignore[arg-type]
    if discovered != set(SCHEMAS):
        raise ManufacturingIntelligenceError("Extended ingestion did not process all datasets")
    source_counts = summary["source_counts_by_dataset"]  # type: ignore[assignment]
    accepted_counts = summary["accepted_counts_by_dataset"]  # type: ignore[assignment]
    quarantine_counts = summary["quarantine_counts_by_dataset"]  # type: ignore[assignment]
    sales_source = int(source_counts["sales_orders"])
    sales_accepted = int(accepted_counts["sales_orders"])
    sales_quarantine = int(quarantine_counts["sales_orders"])
    sales_rate = 0.0 if sales_source == 0 else sales_quarantine / sales_source
    if sales_rate > allowed_rate:
        raise ManufacturingIntelligenceError(
            "Extended sales-order quarantine threshold exceeded: "
            f"{sales_quarantine}/{sales_source} ({sales_rate:.6f}) > {allowed_rate:.6f}"
        )
    if sales_accepted + sales_quarantine != sales_source:
        raise ManufacturingIntelligenceError("Extended sales-order counts are inconsistent")


def _verify_sales_hash(interim_output_dir: Path, manifest: dict[str, object]) -> None:
    accepted = manifest["accepted_outputs"]  # type: ignore[index]
    sales = accepted["sales_orders"]  # type: ignore[index]
    path = interim_output_dir / str(sales["path"])  # type: ignore[index]
    if not path.is_file():
        raise ManufacturingIntelligenceError("Extended accepted sales-order file is missing")
    if sha256_file(path) != sales["sha256"]:  # type: ignore[index]
        raise ManufacturingIntelligenceError("Extended accepted sales-order hash mismatch")


if __name__ == "__main__":
    raise SystemExit(main())
