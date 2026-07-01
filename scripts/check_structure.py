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
    "docs/milestones/milestone-1.md",
    "docs/milestones/milestone-2.md",
    "docs/roadmap.md",
    "outputs/.gitkeep",
    "reports/.gitkeep",
    "src/manufacturing_intelligence/__init__.py",
    "src/manufacturing_intelligence/common/config.py",
    "src/manufacturing_intelligence/common/exceptions.py",
    "src/manufacturing_intelligence/common/logging.py",
    "src/manufacturing_intelligence/common/paths.py",
    "src/manufacturing_intelligence/data_generation/catalog.py",
    "src/manufacturing_intelligence/data_generation/cli.py",
    "src/manufacturing_intelligence/data_generation/generator.py",
    "src/manufacturing_intelligence/data_generation/schemas.py",
    "scripts/generate_synthetic_data.py",
    "tests/unit/test_config.py",
    "tests/unit/test_repository_structure.py",
    "tests/unit/test_synthetic_data_generation.py",
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
