"""Configuration loading for final release artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manufacturing_intelligence.common.exceptions import ConfigurationError
from manufacturing_intelligence.common.paths import project_root, resolve_project_path
from manufacturing_intelligence.forecasting.data import relative_path


@dataclass(frozen=True)
class ReleaseSettings:
    output_directory: Path
    report_directory: Path
    documentation_directory: Path
    overwrite: bool
    random_seed: int
    release_name: str
    release_mode: str
    allow_external_services: bool
    allow_cloud_deployment: bool
    synthetic_data_only: bool


@dataclass(frozen=True)
class ReleaseValidation:
    require_all_milestone_docs: bool
    require_all_validation_targets: bool
    require_all_core_outputs: bool
    require_all_manifests: bool
    require_all_lineage: bool
    require_dashboard_outputs: bool
    require_architecture_outputs: bool
    require_no_deployment_claims: bool
    require_no_secrets: bool
    require_no_large_temp_outputs: bool


@dataclass(frozen=True)
class ReleaseCatalogues:
    write_evidence_index: bool
    write_report_index: bool
    write_architecture_index: bool
    write_dashboard_index: bool
    write_model_catalogue: bool
    write_interview_pack: bool


@dataclass(frozen=True)
class ReleaseConfig:
    config_path: Path
    release: ReleaseSettings
    validation: ReleaseValidation
    catalogues: ReleaseCatalogues


def load_release_config(config_path: Path | None = None) -> ReleaseConfig:
    path = (
        resolve_project_path(config_path)
        if config_path
        else project_root() / "configs" / "release.yaml"
    )
    if not path.is_file():
        raise ConfigurationError(f"Release config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Release config must contain a mapping")
    release = _section(payload, "release")
    validation = _section(payload, "validation")
    catalogues = _section(payload, "catalogues")
    settings = ReleaseSettings(
        output_directory=_safe_output_path(_required_str(release, "output_directory")),
        report_directory=resolve_project_path(_required_str(release, "report_directory")),
        documentation_directory=resolve_project_path(
            _required_str(release, "documentation_directory")
        ),
        overwrite=_required_bool(release, "overwrite"),
        random_seed=_positive_int(release, "random_seed"),
        release_name=_required_str(release, "release_name"),
        release_mode=_required_str(release, "release_mode"),
        allow_external_services=_required_bool(release, "allow_external_services"),
        allow_cloud_deployment=_required_bool(release, "allow_cloud_deployment"),
        synthetic_data_only=_required_bool(release, "synthetic_data_only"),
    )
    if settings.release_mode != "portfolio_evidence":
        raise ConfigurationError("Release mode must be portfolio_evidence")
    if settings.allow_external_services:
        raise ConfigurationError("External services must remain disabled")
    if settings.allow_cloud_deployment:
        raise ConfigurationError("Cloud deployment must remain disabled")
    if not settings.synthetic_data_only:
        raise ConfigurationError("Release must remain synthetic-data-only")
    return ReleaseConfig(
        config_path=path.resolve(),
        release=settings,
        validation=ReleaseValidation(
            **{
                field: _required_bool(validation, field)
                for field in ReleaseValidation.__dataclass_fields__
            }
        ),
        catalogues=ReleaseCatalogues(
            **{
                field: _required_bool(catalogues, field)
                for field in ReleaseCatalogues.__dataclass_fields__
            }
        ),
    )


def semantic_config_payload(config: ReleaseConfig) -> dict[str, Any]:
    return {
        "release": {
            "random_seed": config.release.random_seed,
            "release_name": config.release.release_name,
            "release_mode": config.release.release_mode,
            "allow_external_services": config.release.allow_external_services,
            "allow_cloud_deployment": config.release.allow_cloud_deployment,
            "synthetic_data_only": config.release.synthetic_data_only,
        },
        "validation": {
            field: getattr(config.validation, field)
            for field in ReleaseValidation.__dataclass_fields__
        },
        "catalogues": {
            field: getattr(config.catalogues, field)
            for field in ReleaseCatalogues.__dataclass_fields__
        },
    }


def stable_config_path(path: Path) -> str:
    value = relative_path(path)
    return path.name if value.startswith("/") else value


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Release config section missing or invalid: {key}")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Required string missing: {key}")
    lowered = value.lower()
    if any(token in lowered for token in ["client_secret=", "password=", "access_key="]):
        raise ConfigurationError(f"Secret-looking value rejected: {key}")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"Required boolean missing: {key}")
    return value


def _positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"Required positive integer missing: {key}")
    return value


def _safe_output_path(value: str) -> Path:
    path = resolve_project_path(value)
    if "data" in path.parts and ".generated" not in path.parts:
        raise ConfigurationError("Release outputs must not be written under data/")
    return path
