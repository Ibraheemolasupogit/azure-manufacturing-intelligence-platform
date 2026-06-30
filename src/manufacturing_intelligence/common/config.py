"""Typed configuration loading for the local-first platform."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path

ENV_PREFIX = "MANUFACTURING_INTELLIGENCE_"
SAFE_DEPLOYMENT_MODES = {"local", "reference-only"}
EnvCaster = Callable[[str], str | int | bool]


@dataclass(frozen=True)
class ProjectConfig:
    """Project metadata and active environment."""

    name: str
    version: str
    environment: str


@dataclass(frozen=True)
class PathConfig:
    """Filesystem locations used by local pipelines."""

    raw_data: Path
    interim_data: Path
    processed_data: Path
    outputs: Path
    reports: Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime controls shared by future pipelines."""

    random_seed: int
    timezone: str
    fail_fast: bool


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration for local execution and CI."""

    level: str
    format: str


@dataclass(frozen=True)
class AzureMappingConfig:
    """Reference-only Azure mapping flags."""

    enabled: bool
    deployment_mode: str


@dataclass(frozen=True)
class PlatformConfig:
    """Complete platform configuration."""

    project: ProjectConfig
    paths: PathConfig
    runtime: RuntimeConfig
    logging: LoggingConfig
    azure_mapping: AzureMappingConfig


def load_config(environment: str | None = None) -> PlatformConfig:
    """Load base config, environment overrides, and supported env-var overrides."""
    root = project_root()
    base_data = _read_yaml(root / "configs" / "platform.yaml")
    project_data = base_data.get("project", {})
    active_environment = environment or str(project_data.get("environment", "local"))
    env_path = root / "configs" / "environments" / f"{active_environment}.yaml"
    merged = _deep_merge(base_data, _read_yaml(env_path))
    _apply_environment_overrides(merged)
    return _parse_config(merged)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Configuration file must contain a mapping: {path}")
    return payload


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_environment_overrides(config: MutableMapping[str, Any]) -> None:
    supported: dict[str, tuple[str, str, EnvCaster]] = {
        f"{ENV_PREFIX}PROJECT_ENVIRONMENT": ("project", "environment", str),
        f"{ENV_PREFIX}RUNTIME_RANDOM_SEED": ("runtime", "random_seed", int),
        f"{ENV_PREFIX}RUNTIME_FAIL_FAST": ("runtime", "fail_fast", _parse_bool),
        f"{ENV_PREFIX}LOGGING_LEVEL": ("logging", "level", str),
        f"{ENV_PREFIX}AZURE_MAPPING_ENABLED": ("azure_mapping", "enabled", _parse_bool),
        f"{ENV_PREFIX}AZURE_MAPPING_DEPLOYMENT_MODE": ("azure_mapping", "deployment_mode", str),
    }
    for env_name, (section, key, caster) in supported.items():
        if env_name not in os.environ:
            continue
        config.setdefault(section, {})
        section_data = config[section]
        if not isinstance(section_data, MutableMapping):
            raise ConfigurationError(f"Configuration section must be a mapping: {section}")
        section_data[key] = caster(os.environ[env_name])


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean environment override: {value}")


def _parse_config(config: Mapping[str, Any]) -> PlatformConfig:
    required_sections = ("project", "paths", "runtime", "logging", "azure_mapping")
    missing_sections = [section for section in required_sections if section not in config]
    if missing_sections:
        raise ConfigurationError(f"Missing required config sections: {', '.join(missing_sections)}")

    project = _section(config, "project")
    paths = _section(config, "paths")
    runtime = _section(config, "runtime")
    logging_config = _section(config, "logging")
    azure_mapping = _section(config, "azure_mapping")

    deployment_mode = _required_str(azure_mapping, "deployment_mode")
    azure_enabled = _required_bool(azure_mapping, "enabled")
    if azure_enabled or deployment_mode not in SAFE_DEPLOYMENT_MODES:
        raise ConfigurationError(
            "Milestone 1 supports only disabled, local/reference-only Azure mapping."
        )

    return PlatformConfig(
        project=ProjectConfig(
            name=_required_str(project, "name"),
            version=_required_str(project, "version"),
            environment=_required_str(project, "environment"),
        ),
        paths=PathConfig(
            raw_data=resolve_project_path(_required_str(paths, "raw_data")),
            interim_data=resolve_project_path(_required_str(paths, "interim_data")),
            processed_data=resolve_project_path(_required_str(paths, "processed_data")),
            outputs=resolve_project_path(_required_str(paths, "outputs")),
            reports=resolve_project_path(_required_str(paths, "reports")),
        ),
        runtime=RuntimeConfig(
            random_seed=_required_int(runtime, "random_seed"),
            timezone=_required_str(runtime, "timezone"),
            fail_fast=_required_bool(runtime, "fail_fast"),
        ),
        logging=LoggingConfig(
            level=_required_str(logging_config, "level"),
            format=_required_str(logging_config, "format"),
        ),
        azure_mapping=AzureMappingConfig(
            enabled=azure_enabled,
            deployment_mode=deployment_mode,
        ),
    )


def _section(config: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = config[name]
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Configuration section must be a mapping: {name}")
    return value


def _required_str(section: Mapping[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string configuration value is missing: {key}")
    return value


def _required_int(section: Mapping[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int):
        raise ConfigurationError(f"Required integer configuration value is missing: {key}")
    return value


def _required_bool(section: Mapping[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean configuration value is missing: {key}")
    return value
