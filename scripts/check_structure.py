"""Validate the repository scaffold and generated synthetic-data assets."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Unable to locate repository root.")


REQUIRED_PATHS = [
    ".github/workflows/ci.yml",
    "configs/platform.yaml",
    "configs/ingestion.yaml",
    "configs/ingestion_ci.yaml",
    "configs/forecasting.yaml",
    "configs/forecasting_ci.yaml",
    "configs/forecasting_extended.yaml",
    "configs/synthetic_data_forecasting.yaml",
    "configs/ingestion_forecasting.yaml",
    "configs/synthetic_data.yaml",
    "configs/synthetic_data_ci.yaml",
    "configs/environments/local.yaml",
    "configs/environments/ci.yaml",
    "dashboard/README.md",
    "data/README.md",
    "data/raw/.gitkeep",
    "data/interim/.gitkeep",
    "data/processed/.gitkeep",
    "diagrams/high-level-platform-architecture.mmd",
    "diagrams/data-lifecycle.mmd",
    "docs/architecture/architecture-overview.md",
    "docs/architecture/azure-service-mapping.md",
    "docs/architecture/local-first-design.md",
    "docs/business/business-context.md",
    "docs/business/manufacturing-use-cases.md",
    "docs/business/kpi-catalogue.md",
    "docs/engineering/development-standards.md",
    "docs/engineering/data-contracts.md",
    "docs/engineering/testing-strategy.md",
    "docs/forecasting/backtesting-and-model-selection.md",
    "docs/forecasting/chronological-splitting.md",
    "docs/forecasting/demand-series-and-grain.md",
    "docs/forecasting/evaluation-metrics.md",
    "docs/forecasting/forecast-lineage-and-manifest.md",
    "docs/forecasting/forecasting-design.md",
    "docs/forecasting/leakage-prevention.md",
    "docs/forecasting/limitations.md",
    "docs/forecasting/prediction-intervals.md",
    "docs/ingestion/data-quality-metrics.md",
    "docs/ingestion/ingestion-design.md",
    "docs/ingestion/lineage-and-manifests.md",
    "docs/ingestion/quarantine-design.md",
    "docs/ingestion/strict-vs-permissive-mode.md",
    "docs/ingestion/validation-rules.md",
    "docs/milestones/milestone-1.md",
    "docs/milestones/milestone-2.md",
    "docs/milestones/milestone-3.md",
    "docs/milestones/milestone-4.md",
    "docs/roadmap.md",
    "outputs/.gitkeep",
    "reports/.gitkeep",
    "reports/data_quality_report.md",
    "reports/demand_forecasting_report.md",
    "src/manufacturing_intelligence/__init__.py",
    "src/manufacturing_intelligence/common/config.py",
    "src/manufacturing_intelligence/common/exceptions.py",
    "src/manufacturing_intelligence/common/hashing.py",
    "src/manufacturing_intelligence/common/logging.py",
    "src/manufacturing_intelligence/common/paths.py",
    "src/manufacturing_intelligence/data_generation/catalog.py",
    "src/manufacturing_intelligence/data_generation/cli.py",
    "src/manufacturing_intelligence/data_generation/generator.py",
    "src/manufacturing_intelligence/data_generation/schemas.py",
    "src/manufacturing_intelligence/forecasting/__main__.py",
    "src/manufacturing_intelligence/forecasting/aggregation.py",
    "src/manufacturing_intelligence/forecasting/backtesting.py",
    "src/manufacturing_intelligence/forecasting/baselines.py",
    "src/manufacturing_intelligence/forecasting/cli.py",
    "src/manufacturing_intelligence/forecasting/config.py",
    "src/manufacturing_intelligence/forecasting/data.py",
    "src/manufacturing_intelligence/forecasting/evaluation.py",
    "src/manufacturing_intelligence/forecasting/existing_run.py",
    "src/manufacturing_intelligence/forecasting/features.py",
    "src/manufacturing_intelligence/forecasting/intervals.py",
    "src/manufacturing_intelligence/forecasting/lineage.py",
    "src/manufacturing_intelligence/forecasting/manifest.py",
    "src/manufacturing_intelligence/forecasting/models.py",
    "src/manufacturing_intelligence/forecasting/pipeline.py",
    "src/manufacturing_intelligence/forecasting/reporting.py",
    "src/manufacturing_intelligence/forecasting/selection.py",
    "src/manufacturing_intelligence/forecasting/serialization.py",
    "src/manufacturing_intelligence/forecasting/splits.py",
    "src/manufacturing_intelligence/ingestion/__main__.py",
    "src/manufacturing_intelligence/ingestion/cli.py",
    "src/manufacturing_intelligence/ingestion/config.py",
    "src/manufacturing_intelligence/ingestion/discovery.py",
    "src/manufacturing_intelligence/ingestion/existing_run.py",
    "src/manufacturing_intelligence/ingestion/loader.py",
    "src/manufacturing_intelligence/ingestion/manifest.py",
    "src/manufacturing_intelligence/ingestion/pipeline.py",
    "src/manufacturing_intelligence/ingestion/reporting.py",
    "src/manufacturing_intelligence/ingestion/serialization.py",
    "src/manufacturing_intelligence/validation/contracts.py",
    "src/manufacturing_intelligence/validation/domain_rules.py",
    "src/manufacturing_intelligence/validation/duplicates.py",
    "src/manufacturing_intelligence/validation/file_rules.py",
    "src/manufacturing_intelligence/validation/lineage.py",
    "src/manufacturing_intelligence/validation/quality.py",
    "src/manufacturing_intelligence/validation/quarantine.py",
    "src/manufacturing_intelligence/validation/record_rules.py",
    "src/manufacturing_intelligence/validation/relationships.py",
    "src/manufacturing_intelligence/validation/result.py",
    "scripts/generate_synthetic_data.py",
    "scripts/prepare_forecasting_data.py",
    "tests/unit/test_config.py",
    "tests/unit/test_repository_structure.py",
    "tests/unit/test_synthetic_data_generation.py",
    "tests/unit/test_ingestion_pipeline.py",
    "tests/unit/test_forecasting_pipeline.py",
    "tests/fixtures/README.md",
    ".editorconfig",
    ".gitignore",
    ".markdownlint.json",
    ".pre-commit-config.yaml",
    "CONTRIBUTING.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "pyproject.toml",
    "requirements-dev.txt",
]

RAW_SYNTHETIC_OUTPUTS = [
    "data/raw/production_events.jsonl",
    "data/raw/inventory_levels.csv",
    "data/raw/sales_orders.csv",
    "data/raw/quality_checks.csv",
    "data/raw/equipment_health.jsonl",
    "data/raw/warehouse_movements.csv",
    "data/raw/supplier_performance.csv",
    "data/raw/schema_metadata.json",
    "data/raw/generation_manifest.json",
    "data/raw/generation_summary.md",
]

INTERIM_INGESTION_OUTPUTS = [
    "data/interim/accepted/production_events.jsonl",
    "data/interim/accepted/inventory_levels.csv",
    "data/interim/accepted/sales_orders.csv",
    "data/interim/accepted/quality_checks.csv",
    "data/interim/accepted/equipment_health.jsonl",
    "data/interim/accepted/warehouse_movements.csv",
    "data/interim/accepted/supplier_performance.csv",
    "data/interim/quarantine/production_events.jsonl",
    "data/interim/quarantine/inventory_levels.jsonl",
    "data/interim/quarantine/sales_orders.jsonl",
    "data/interim/quarantine/quality_checks.jsonl",
    "data/interim/quarantine/equipment_health.jsonl",
    "data/interim/quarantine/warehouse_movements.jsonl",
    "data/interim/quarantine/supplier_performance.jsonl",
    "data/interim/_metadata/ingestion-manifest.json",
    "data/interim/_metadata/validation-summary.json",
    "data/interim/_metadata/quarantine-summary.json",
    "data/interim/_metadata/data-quality-report.json",
    "data/interim/_metadata/lineage-records.json",
]

FORECAST_OUTPUTS = [
    "outputs/demand_forecast.csv",
    "outputs/forecasting/daily_demand_series.csv",
    "outputs/forecasting/feature_dataset.csv",
    "outputs/forecasting/split_metadata.json",
    "outputs/forecasting/model_comparison.csv",
    "outputs/forecasting/backtest_predictions.csv",
    "outputs/forecasting/backtest_metrics.csv",
    "outputs/forecasting/test_metrics.csv",
    "outputs/forecasting/forecast_diagnostics.json",
    "outputs/forecasting/model_metadata.json",
    "outputs/forecasting/forecast-manifest.json",
    "outputs/forecasting/lineage-records.json",
]

PACKAGE_DIRS = [
    "common",
    "data_generation",
    "ingestion",
    "validation",
    "forecasting",
    "inventory",
    "quality",
    "maintenance",
    "monitoring",
    "genai",
    "reporting",
]


def main() -> int:
    root = project_root()
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    missing.extend(path for path in RAW_SYNTHETIC_OUTPUTS if not (root / path).exists())
    missing.extend(path for path in INTERIM_INGESTION_OUTPUTS if not (root / path).exists())
    missing.extend(path for path in FORECAST_OUTPUTS if not (root / path).exists())
    for package_dir in PACKAGE_DIRS:
        marker = root / "src" / "manufacturing_intelligence" / package_dir / "__init__.py"
        if not marker.exists():
            missing.append(str(marker.relative_to(root)))

    if missing:
        print("Repository structure check failed. Missing required paths:")
        for path in sorted(missing):
            print(f"  - {path}")
        return 1

    print("Repository structure check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
