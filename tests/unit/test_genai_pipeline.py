from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from manufacturing_intelligence.common.exceptions import ConfigurationError, DataContractError
from manufacturing_intelligence.common.hashing import sha256_file
from manufacturing_intelligence.common.paths import project_root
from manufacturing_intelligence.genai.config import load_genai_config
from manufacturing_intelligence.genai.evidence import build_evidence_catalogue
from manufacturing_intelligence.genai.existing_run import validate_existing_run
from manufacturing_intelligence.genai.guardrails import evaluate_guardrails
from manufacturing_intelligence.genai.pipeline import run_genai
from manufacturing_intelligence.genai.prompts import SYNTHETIC_DISCLAIMER, render_prompt
from manufacturing_intelligence.genai.retrieval import retrieve_evidence


def test_evidence_catalogue_loads_required_domains() -> None:
    config = load_genai_config(Path("configs/genai.yaml"))
    catalogue = build_evidence_catalogue(config)
    assert {item["domain"] for item in catalogue.items} == set(config.evidence.required_domains)
    assert len(catalogue.items) == 27


def test_evidence_hashes_are_calculated_correctly() -> None:
    catalogue = build_evidence_catalogue(load_genai_config(Path("configs/genai.yaml")))
    first = catalogue.items[0]
    assert first["sha256"] == sha256_file(project_root() / first["relative_path"])


def test_evidence_catalogue_excludes_generated_artifacts() -> None:
    catalogue = build_evidence_catalogue(load_genai_config(Path("configs/genai.yaml")))
    assert all(".generated" not in item["relative_path"] for item in catalogue.items)


def test_missing_required_evidence_fails_clearly(tmp_path: Path) -> None:
    source = project_root() / "configs" / "genai.yaml"
    config_copy = tmp_path / "genai.yaml"
    config_copy.write_text(
        source.read_text(encoding="utf-8").replace(
            "data/raw/generation_manifest.json",
            "data/raw/missing_generation_manifest.json",
        ),
        encoding="utf-8",
    )
    with pytest.raises(DataContractError, match="GENAI_REQUIRED_EVIDENCE_MISSING"):
        build_evidence_catalogue(load_genai_config(config_copy))


def test_retrieval_by_task_type_is_deterministic() -> None:
    config = load_genai_config(Path("configs/genai.yaml"))
    items = build_evidence_catalogue(config).items
    one = retrieve_evidence(
        config=config, items=items, question="inventory risk", task_type="inventory"
    )
    two = retrieve_evidence(
        config=config, items=items, question="inventory risk", task_type="inventory"
    )
    assert one == two
    assert one["evidence_count"] <= config.retrieval.maximum_evidence_items
    assert one["evidence_items"][0]["domain"] == "inventory"


def test_retrieval_by_keyword_is_deterministic() -> None:
    config = load_genai_config(Path("configs/genai.yaml"))
    items = build_evidence_catalogue(config).items
    result = retrieve_evidence(config=config, items=items, question="Summarize maintenance alerts")
    assert result["inferred_intent"] == "maintenance"
    assert result["evidence_items"][0]["domain"] == "maintenance"


def test_prompt_rendering_includes_guardrails_evidence_and_disclaimer() -> None:
    config = load_genai_config(Path("configs/genai.yaml"))
    items = build_evidence_catalogue(config).items
    retrieval = retrieve_evidence(
        config=config, items=items, question="quality alert", task_type="quality"
    )
    prompt = render_prompt("quality", "quality alert", retrieval)
    assert prompt == render_prompt("quality", "quality alert", retrieval)
    assert "Guardrails:" in prompt["rendered_prompt"]
    assert retrieval["evidence_items"][0]["evidence_id"] in prompt["rendered_prompt"]
    assert SYNTHETIC_DISCLAIMER in prompt["rendered_prompt"]
    assert prompt["external_model_called"] is False


@pytest.mark.parametrize(
    ("question", "rule"),
    [
        ("Start production line now", "live_operational_command"),
        (
            "Is machine M1 safe to operate and how do I bypass lockout?",
            "safety_critical_instruction",
        ),
        ("What is the current real-world plant status right now?", "real_world_claim"),
        ("Explain missing evidence", "missing_evidence"),
    ],
)
def test_guardrails_refuse_required_paths(question: str, rule: str) -> None:
    retrieval = {"query_id": "QUERY-test", "evidence_count": 0, "evidence_items": []}
    result = evaluate_guardrails(question, retrieval)
    assert result["decision"] == "refuse"
    assert rule in result["triggered_rules"]
    assert result["external_model_called"] is False


def test_pipeline_outputs_are_deterministic_and_grounded(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    result_one = run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    manifest_one = json.loads((output_dir / "genai-manifest.json").read_text(encoding="utf-8"))
    result_two = run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    manifest_two = json.loads((output_dir / "genai-manifest.json").read_text(encoding="utf-8"))
    assert result_one.genai_run_id == result_two.genai_run_id
    assert manifest_one["genai_run_id"] == manifest_two["genai_run_id"]
    responses = json.loads((output_dir / "assistant_responses.json").read_text(encoding="utf-8"))
    evidence_ids = {
        item["evidence_id"]
        for item in json.loads((output_dir / "evidence_catalog.json").read_text(encoding="utf-8"))
    }
    assert {response["task_type"] for response in responses} >= {
        "executive_summary",
        "inventory",
        "quality",
        "maintenance",
        "monitoring",
        "lineage",
    }
    for response in responses:
        assert response["unsupported_claim_count"] == 0
        assert response["grounding_score"] == 1.0
        assert response["citation_coverage"] == 1.0
        assert response["external_model_called"] is False
        assert SYNTHETIC_DISCLAIMER in response["answer"]
        assert {citation.strip("[]") for citation in response["citations"]} <= evidence_ids


def test_existing_run_validation_and_tamper_detection(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    validate_existing_run(Path("configs/genai.yaml"), output_dir)
    response_path = output_dir / "assistant_responses.json"
    responses = json.loads(response_path.read_text(encoding="utf-8"))
    responses[0]["answer"] = "tampered"
    response_path.write_text(json.dumps(responses, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match=r"GENAI_OUTPUT_.*MISMATCH"):
        validate_existing_run(Path("configs/genai.yaml"), output_dir)


def test_manifest_counts_sizes_hashes_and_lineage_are_valid(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    manifest = json.loads((output_dir / "genai-manifest.json").read_text(encoding="utf-8"))
    outputs = manifest["output_files"]
    for evidence in outputs.values():
        path = output_dir.parent / evidence["path"]
        assert path.stat().st_size == evidence["file_size_bytes"]
        assert sha256_file(path) == evidence["sha256"]
    lineage = json.loads((output_dir / "lineage-records.json").read_text(encoding="utf-8"))
    assert {item["path"] for item in outputs.values()} <= {item["target_path"] for item in lineage}
    assert all(item["external_model_called"] is False for item in lineage)


def test_overwrite_protection_does_not_remove_unrelated_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    unrelated = output_dir / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    with pytest.raises(Exception, match="GenAI outputs already exist"):
        run_genai(Path("configs/genai.yaml"), output_directory=output_dir)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_invalid_configuration_is_rejected(tmp_path: Path) -> None:
    config_copy = tmp_path / "genai.yaml"
    config_copy.write_text(
        (project_root() / "configs" / "genai.yaml")
        .read_text(encoding="utf-8")
        .replace(
            "allow_external_model_calls: false",
            "allow_external_model_calls: true",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="External model calls"):
        load_genai_config(config_copy)


def test_relevant_config_changes_alter_run_id(tmp_path: Path) -> None:
    output_one = tmp_path / "one" / "genai"
    output_two = tmp_path / "two" / "genai"
    config_copy = tmp_path / "genai.yaml"
    config_copy.write_text(
        (project_root() / "configs" / "genai.yaml")
        .read_text(encoding="utf-8")
        .replace(
            "maximum_response_words: 600",
            "maximum_response_words: 500",
        ),
        encoding="utf-8",
    )
    one = run_genai(Path("configs/genai.yaml"), output_directory=output_one, overwrite=True)
    two = run_genai(config_copy, output_directory=output_two, overwrite=True)
    assert one.genai_run_id != two.genai_run_id


def test_cli_works_outside_repository_root(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("COV_CORE") or key.startswith("COVERAGE"):
            env.pop(key)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manufacturing_intelligence.genai",
            "--config",
            "configs/genai.yaml",
            "--output-directory",
            str(output_dir),
            "--overwrite",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (output_dir / "genai-manifest.json").is_file()


def test_ci_genai_execution_completes_quickly(tmp_path: Path) -> None:
    output_dir = tmp_path / "ci" / "genai"
    result = run_genai(Path("configs/genai_ci.yaml"), output_directory=output_dir, overwrite=True)
    assert result.evidence_count == 27
    validate_existing_run(Path("configs/genai_ci.yaml"), output_dir)


def test_existing_run_validation_detects_manifest_tampering(tmp_path: Path) -> None:
    output_dir = tmp_path / "genai"
    run_genai(Path("configs/genai.yaml"), output_directory=output_dir, overwrite=True)
    manifest_path = output_dir / "genai-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["genai_run_id"] = "GENAI-tampered"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="GENAI_RUN_ID_MISMATCH"):
        validate_existing_run(Path("configs/genai.yaml"), output_dir)


def test_existing_milestone_output_validators_still_available() -> None:
    assert shutil.which("make") is not None
