"""CLI for the deterministic local GenAI operations assistant."""

from __future__ import annotations

import argparse
from pathlib import Path

from manufacturing_intelligence.common.exceptions import ManufacturingIntelligenceError
from manufacturing_intelligence.genai.config import load_genai_config
from manufacturing_intelligence.genai.existing_run import validate_existing_run
from manufacturing_intelligence.genai.pipeline import run_genai


def main() -> int:
    """Run or validate GenAI assistant outputs."""
    parser = argparse.ArgumentParser(description="Run local deterministic GenAI assistant.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--task-type", type=str, default=None)
    parser.add_argument("--validate-config-only", action="store_true")
    parser.add_argument("--validate-existing-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_config_only:
            config = load_genai_config(args.config)
            print(f"GenAI config valid: {config.genai.output_directory} mode={config.genai.mode}")
            return 0
        if args.validate_existing_run:
            validate_existing_run(args.config, args.output_directory)
            print("Existing GenAI assistant run is valid.")
            return 0
        result = run_genai(
            args.config,
            output_directory=args.output_directory,
            overwrite=args.overwrite,
            question=args.question,
            task_type=args.task_type,
        )
    except ManufacturingIntelligenceError as exc:
        print(str(exc))
        return 1
    print(
        f"GenAI assistant {result.genai_run_id} wrote {result.evidence_count} evidence items, "
        f"{result.response_count} responses, and {result.guardrail_count} guardrail results "
        f"to {result.output_directory}"
    )
    return 0
