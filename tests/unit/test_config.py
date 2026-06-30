from __future__ import annotations

import os
from pathlib import Path

import pytest

from manufacturing_intelligence.common.config import load_config
from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path


def test_local_configuration_loads_successfully() -> None:
    config = load_config("local")

    assert config.project.name == "azure-manufacturing-intelligence-platform"
    assert config.project.environment == "local"
    assert config.runtime.random_seed == 20260701
    assert config.paths.raw_data == project_root() / "data" / "raw"
    assert config.azure_mapping.enabled is False
    assert config.azure_mapping.deployment_mode == "reference-only"


def test_ci_override_changes_environment_and_logging() -> None:
    config = load_config("ci")

    assert config.project.environment == "ci"
    assert config.logging.level == "WARNING"
    assert config.azure_mapping.enabled is False


def test_environment_variable_overrides_are_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUFACTURING_INTELLIGENCE_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("MANUFACTURING_INTELLIGENCE_RUNTIME_RANDOM_SEED", "123")
    monkeypatch.setenv("MANUFACTURING_INTELLIGENCE_PROJECT_ENVIRONMENT", "local-env-override")

    config = load_config("local")

    assert config.logging.level == "DEBUG"
    assert config.runtime.random_seed == 123
    assert config.project.environment == "local-env-override"


def test_live_azure_mapping_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUFACTURING_INTELLIGENCE_AZURE_MAPPING_ENABLED", "true")

    with pytest.raises(ConfigurationError, match="reference-only Azure mapping"):
        load_config("local")


def test_deployment_mode_cannot_imply_live_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUFACTURING_INTELLIGENCE_AZURE_MAPPING_DEPLOYMENT_MODE", "production")

    with pytest.raises(ConfigurationError, match="reference-only Azure mapping"):
        load_config("local")


def test_path_resolution_is_independent_of_cwd(tmp_path: Path) -> None:
    original = Path.cwd()
    try:
        os.chdir(tmp_path)
        root = project_root()
        assert root.name == "azure-manufacturing-intelligence-platform"
        assert resolve_project_path("outputs") == root / "outputs"
    finally:
        os.chdir(original)


def test_missing_config_environment_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        load_config("missing")
