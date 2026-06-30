from __future__ import annotations

import importlib.metadata

import manufacturing_intelligence
from manufacturing_intelligence.common.paths import project_root


def test_package_imports_successfully() -> None:
    assert manufacturing_intelligence.__version__ == "0.1.0"


def test_project_metadata_is_coherent() -> None:
    assert importlib.metadata.version("azure-manufacturing-intelligence-platform") == "0.1.0"


def test_required_repository_documents_exist() -> None:
    root = project_root()
    required = [
        "README.md",
        "CONTRIBUTING.md",
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
        "docs/roadmap.md",
        "diagrams/high-level-platform-architecture.mmd",
        "diagrams/data-lifecycle.mmd",
    ]

    missing = [path for path in required if not (root / path).is_file()]

    assert missing == []


def test_required_package_boundaries_exist() -> None:
    root = project_root()
    packages = [
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

    for package in packages:
        assert (root / "src" / "manufacturing_intelligence" / package / "__init__.py").is_file()
