"""Validation-only checks for an existing GenAI assistant run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from manufacturing_intelligence.common.exceptions import DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import resolve_project_path
from manufacturing_intelligence.genai.config import load_genai_config
from manufacturing_intelligence.genai.evidence import validate_catalogue_references
from manufacturing_intelligence.genai.manifest import genai_run_id

REQUIRED_OUTPUTS = {
    "evidence_catalog_json",
    "evidence_catalog_csv",
    "retrieval_results",
    "prompt_templates",
    "rendered_prompts",
    "assistant_responses",
    "assistant_responses_markdown",
    "guardrail_results",
    "assistant_evaluation",
    "assistant_evaluation_summary",
    "genai_diagnostics",
    "genai_operations_assistant_report",
    "genai_guardrails_report",
    "executive_manufacturing_brief",
    "supply_chain_summary",
    "manufacturing_operations_report",
}


def validate_existing_run(
    config_path: Path | None = None,
    output_directory: Path | None = None,
) -> None:
    """Validate an existing run without recalculating responses."""
    config = load_genai_config(config_path)
    output_dir = output_directory.resolve() if output_directory else config.genai.output_directory
    manifest_path = output_dir / "genai-manifest.json"
    lineage_path = output_dir / "lineage-records.json"
    if not manifest_path.is_file():
        raise DataContractError("GENAI_MANIFEST_MISSING")
    if not lineage_path.is_file():
        raise DataContractError("GENAI_LINEAGE_MISSING")
    manifest = _read_json(manifest_path)
    _reject_absolute_paths(manifest)
    outputs = manifest.get("output_files")
    if not isinstance(outputs, dict):
        raise DataContractError("GENAI_MANIFEST_OUTPUTS_INVALID")
    missing = sorted(REQUIRED_OUTPUTS - set(outputs))
    if missing:
        raise DataContractError(f"GENAI_MANIFEST_OUTPUTS_MISSING: {missing}")
    genai_manifest = manifest.get("output_files", {}).get("genai_manifest", {})
    for evidence in [*outputs.values(), genai_manifest]:
        if isinstance(evidence, dict) and evidence:
            _verify_file(output_dir, evidence)
    catalogue_path = _resolve_output_path(output_dir, outputs["evidence_catalog_json"]["path"])
    responses_path = _resolve_output_path(output_dir, outputs["assistant_responses"]["path"])
    evaluation_path = _resolve_output_path(output_dir, outputs["assistant_evaluation"]["path"])
    catalogue = _read_json_list(catalogue_path)
    responses = _read_json_list(responses_path)
    evaluation = pd.read_csv(evaluation_path)
    validate_catalogue_references(catalogue)
    _validate_responses(config, responses, catalogue)
    _validate_evaluation(config, evaluation)
    _validate_lineage(lineage_path, outputs)
    _validate_upstream_hashes(config, manifest)
    _validate_run_identity(config, manifest, catalogue_path)


def _validate_responses(
    config: Any,
    responses: list[dict[str, Any]],
    catalogue: list[dict[str, Any]],
) -> None:
    evidence_ids = {item["evidence_id"] for item in catalogue}
    for response in responses:
        if response.get("external_model_called") is not False:
            raise DataContractError("GENAI_EXTERNAL_MODEL_CALLED")
        if response.get("unsupported_claim_count") > config.evaluation.maximum_unsupported_claims:
            raise DataContractError("GENAI_UNSUPPORTED_CLAIMS_EXCEEDED")
        if response.get("grounding_score") < config.evaluation.minimum_grounding_score:
            raise DataContractError("GENAI_GROUNDING_SCORE_TOO_LOW")
        if response.get("citation_coverage") < config.evaluation.minimum_citation_coverage:
            raise DataContractError("GENAI_CITATION_COVERAGE_TOO_LOW")
        disclaimer = str(response.get("synthetic_data_disclaimer"))
        if disclaimer not in str(response.get("answer")):
            raise DataContractError("GENAI_SYNTHETIC_DISCLAIMER_MISSING")
        for reference in response.get("evidence_references", []):
            if reference.get("evidence_id") not in evidence_ids:
                raise DataContractError("GENAI_RESPONSE_EVIDENCE_ID_INVALID")
        for citation in response.get("citations", []):
            if str(citation).strip("[]") not in evidence_ids:
                raise DataContractError("GENAI_RESPONSE_CITATION_INVALID")


def _validate_evaluation(config: Any, frame: pd.DataFrame) -> None:
    if not (frame["external_model_called"] == False).all():  # noqa: E712
        raise DataContractError("GENAI_EVALUATION_EXTERNAL_CALL_INVALID")
    if not (frame["unsupported_claim_count"] <= config.evaluation.maximum_unsupported_claims).all():
        raise DataContractError("GENAI_EVALUATION_UNSUPPORTED_CLAIMS_INVALID")
    if not (frame["grounding_score"] >= config.evaluation.minimum_grounding_score).all():
        raise DataContractError("GENAI_EVALUATION_GROUNDING_INVALID")
    if not (frame["citation_coverage"] >= config.evaluation.minimum_citation_coverage).all():
        raise DataContractError("GENAI_EVALUATION_CITATION_INVALID")
    if not (frame["evaluation_status"] == "passed").all():
        raise DataContractError("GENAI_EVALUATION_STATUS_FAILED")


def _validate_lineage(lineage_path: Path, outputs: dict[str, Any]) -> None:
    lineage = _read_json_list(lineage_path)
    targets = {item["path"] for item in outputs.values() if isinstance(item, dict)}
    lineage_targets = {item.get("target_path") for item in lineage}
    if not targets <= lineage_targets:
        raise DataContractError("GENAI_LINEAGE_TARGETS_MISSING")
    if any(item.get("external_model_called") is not False for item in lineage):
        raise DataContractError("GENAI_LINEAGE_EXTERNAL_CALL_INVALID")


def _validate_upstream_hashes(config: Any, manifest: dict[str, Any]) -> None:
    hashes = manifest.get("evidence_input_hashes")
    if not isinstance(hashes, dict):
        raise DataContractError("GENAI_INPUT_HASHES_MISSING")
    for key, expected in hashes.items():
        path = getattr(config.inputs, key)
        if sha256_file(path) != expected:
            raise DataContractError(f"GENAI_UPSTREAM_HASH_MISMATCH: {key}")


def _validate_run_identity(config: Any, manifest: dict[str, Any], catalogue_path: Path) -> None:
    expected = genai_run_id(
        config,
        evidence_catalogue_hash=sha256_file(catalogue_path),
        input_hashes=manifest["evidence_input_hashes"],
    )
    if manifest["genai_run_id"] != expected:
        raise DataContractError("GENAI_RUN_ID_MISMATCH")


def _verify_file(output_dir: Path, evidence: dict[str, Any]) -> None:
    path = _resolve_output_path(output_dir, str(evidence["path"]))
    if not path.is_file():
        raise DataContractError(f"GENAI_OUTPUT_MISSING: {evidence['path']}")
    if int(evidence["file_size_bytes"]) != path.stat().st_size:
        raise DataContractError(f"GENAI_OUTPUT_SIZE_MISMATCH: {evidence['path']}")
    if evidence["sha256"] != sha256_file(path):
        raise DataContractError(f"GENAI_OUTPUT_HASH_MISMATCH: {evidence['path']}")
    if path.suffix == ".csv" and evidence.get("row_count") is not None:
        rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        if int(evidence["row_count"]) != rows:
            raise DataContractError(f"GENAI_OUTPUT_ROW_COUNT_MISMATCH: {evidence['path']}")


def _resolve_output_path(output_dir: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        raise DataContractError("GENAI_ABSOLUTE_OUTPUT_PATH")
    candidate = resolve_project_path(path_value)
    if candidate.is_file():
        return candidate
    return output_dir.parent / path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DataContractError(f"GENAI_JSON_INVALID: {path}")
    return payload


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise DataContractError(f"GENAI_JSON_LIST_INVALID: {path}")
    return payload


def _reject_absolute_paths(payload: dict[str, Any]) -> None:
    if str(Path.home()) in json.dumps(payload):
        raise DataContractError("GENAI_MANIFEST_ABSOLUTE_PATH")
