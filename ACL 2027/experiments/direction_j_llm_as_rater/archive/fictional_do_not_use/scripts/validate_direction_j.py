#!/usr/bin/env python3
"""Fail-closed validation for the prepared, synthetic-only Direction J package.

The validator has no arbitrary input option and never opens dataset/ or the
Warrant Study application's protected item bank. It validates contracts,
frozen hashes, the generated fictional bank, private/public separation, and
the absence of ratings or empirical results in the prepared run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import runpy
import stat
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
SCHEMA_ROOT = DIRECTION_ROOT / "schemas"
FREEZE_PATH = DIRECTION_ROOT / "config" / "freeze_v1.json"
GOVERNANCE_PATH = DIRECTION_ROOT / "config" / "governance_gate.template.json"
EXECUTION_READINESS_TEMPLATE_PATH = (
    DIRECTION_ROOT / "config" / "execution_readiness.template.json"
)
REQUEST_RENDERER_PATH = DIRECTION_ROOT / "scripts" / "render_request_packets.py"
RATER_GUIDE_PATH = DIRECTION_ROOT / "protocol" / "shared_rater_guide_v1.md"
RUN_ROOT = (
    DIRECTION_ROOT
    / "runs"
    / "20260825_synthetic_paired_qualification_prepared"
)
REQUEST_PACKETS_PATH = RUN_ROOT / "request-packets" / "request_packets_v1.jsonl"
LEGACY_MANIFEST = (
    PROJECT_ROOT
    / "experiments"
    / "qualitative_coding_baselines"
    / "runs"
    / "20260825_synthetic_qualification"
    / "run_manifest.json"
)
LEGACY_BLIND_MAP = LEGACY_MANIFEST.parent / "blind_map_private.csv"
BASELINE_ROOT = LEGACY_MANIFEST.parents[2]
BENCHMARK_PATH = BASELINE_ROOT / "benchmark" / "synthetic_packets_v1.json"
BLINDED_DIR = LEGACY_MANIFEST.parent / "blinded"
EXPECTED_BENCHMARK_PROVENANCE = (
    "Entirely fictional text written for pipeline qualification; no "
    "source-corpus text or published theme was used."
)
EXPECTED_ASSIGNMENTS = {
    "charlie_rep1.csv": ("charlie", "human", 1),
    "J_PRIMARY_rep1.csv": ("J_PRIMARY", "llm", 1),
    "J_PRIMARY_rep2.csv": ("J_PRIMARY", "llm", 2),
    "J_PRIMARY_rep3.csv": ("J_PRIMARY", "llm", 3),
    "J_SENS_GEMINI_rep1.csv": ("J_SENS_GEMINI", "llm", 1),
    "QME_QUAL_rep1.csv": ("QME_QUAL", "human", 1),
    "DOMAIN_QUAL_rep1.csv": ("DOMAIN_QUAL", "human", 1),
}
EXPECTED_SERIOUS_FAMILIES = {
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
}
PUBLIC_FORBIDDEN_KEYS = {
    "base_packet_id",
    "baseline_packet_id",
    "baseline_blind_id",
    "baseline_theme_id",
    "blind_id",
    "candidate_model_id",
    "candidate_provider",
    "condition",
    "generation_model_id",
    "model_id",
    "parent_natural_item_sha256",
    "planted_serious_error_flags",
    "provider",
    "truth_scope",
}


class DirectionJValidationError(RuntimeError):
    """Raised when a frozen Direction J invariant does not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DirectionJValidationError(message)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_canonical_jsonl(path: Path) -> list[dict[str, Any]]:
    raw_lines = path.read_bytes().splitlines(keepends=True)
    require(raw_lines, f"JSONL file is empty: {path}")
    values: list[dict[str, Any]] = []
    for number, raw_line in enumerate(raw_lines, start=1):
        require(raw_line.endswith(b"\n"), f"JSONL line {number} lacks newline: {path}")
        value = json.loads(raw_line)
        require(
            raw_line == canonical_bytes(value),
            f"Noncanonical JSONL line {number}: {path}",
        )
        require(isinstance(value, dict), f"JSONL line {number} is not an object: {path}")
        values.append(value)
    return values


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def schema_contracts() -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    registry = Registry()
    paths = sorted(SCHEMA_ROOT.glob("*.schema.json"))
    require(len(paths) == 7, f"Expected seven Direction J schemas; found {len(paths)}")
    for path in paths:
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        require(isinstance(schema_id, str) and schema_id, f"Schema lacks $id: {path}")
        require(schema_id not in schemas, f"Duplicate schema $id: {schema_id}")
        schemas[schema_id] = schema
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return schemas, registry


def validator_for(
    schemas: dict[str, dict[str, Any]], registry: Registry, id_fragment: str
) -> Draft202012Validator:
    matches = [schema for schema_id, schema in schemas.items() if id_fragment in schema_id]
    require(len(matches) == 1, f"Could not resolve one schema for {id_fragment}")
    return Draft202012Validator(
        matches[0], registry=registry, format_checker=FormatChecker()
    )


def assert_valid(validator: Draft202012Validator, value: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(error.message for error in errors[:5])
        raise DirectionJValidationError(f"{label} fails schema: {detail}")


def check_schema_semantics(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> None:
    rating_validator = validator_for(schemas, registry, "shared-rating-v1")
    rating = {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 4,
        "voice_boundary_preservation": 4,
        "scope_calibration": 4,
        "cannot_judge": [],
        "confidence": 4,
        "disposition": "accept",
        "requested_expertise": "none",
        "serious_error_flags": [],
        "rationale": "Contract-validation probe; not a study record.",
    }
    assert_valid(rating_validator, rating, "Shared-rating contract probe")
    invalid = deepcopy(rating)
    invalid["scope_calibration"] = None
    require(
        not rating_validator.is_valid(invalid),
        "Shared rating accepted null without cannot_judge",
    )
    invalid = deepcopy(rating)
    invalid["cannot_judge"] = ["scope_calibration"]
    invalid["scope_calibration"] = None
    require(
        not rating_validator.is_valid(invalid),
        "Shared rating accepted cannot_judge without escalation",
    )
    invalid = deepcopy(rating)
    invalid["disposition"] = "escalate"
    require(
        not rating_validator.is_valid(invalid),
        "Shared rating accepted escalation without requested expertise",
    )
    invalid = deepcopy(rating)
    invalid["serious_error_flags"] = ["unsupported_inference"]
    require(
        not rating_validator.is_valid(invalid),
        "Shared rating accepted a serious-error flag with accept",
    )
    invalid = deepcopy(rating)
    invalid["evidential_credibility"] = 3
    require(
        not rating_validator.is_valid(invalid),
        "Shared rating accepted a material construct score with accept",
    )

    actor_validator = validator_for(schemas, registry, "actor-registry-v1")
    actor_probe = {
        "actor_registry_schema_version": "direction-j-actor-registry-v1",
        "registry_id": "contract-probe-not-study-data",
        "frozen_at_utc": "2026-08-25T00:00:00Z",
        "actors": [
            {
                "actor_id": "LLM_CONTRACT_PROBE",
                "actor_kind": "llm",
                "analysis_status": "excluded",
                "exclusion_reason": "Schema branch validation only.",
                "llm_profile": {
                    "provider": "contract-probe",
                    "model_id": "contract-probe",
                    "model_family": "contract-probe",
                    "model_snapshot": "contract-probe",
                    "surface": "contract-probe",
                    "reasoning_mode": None,
                    "reasoning_effort": None,
                    "temperature": None,
                    "top_p": None,
                    "seed": None,
                    "max_output_tokens": 100,
                    "response_count": 1,
                    "structured_output": True,
                    "tools_enabled": False,
                    "web_enabled": False,
                    "function_calling_enabled": False,
                    "retrieval_enabled": False,
                    "url_context_enabled": False,
                    "code_execution_enabled": False,
                    "memory_enabled": False,
                    "judge_role": "cross_family_sensitivity",
                    "candidate_family_overlap": False,
                    "data_processing_scope": "synthetic_only",
                    "provider_processing_profile_id": "contract-probe",
                },
            }
        ],
    }
    assert_valid(actor_validator, actor_probe, "Actor-registry contract probe")
    invalid_actor = deepcopy(actor_probe)
    invalid_actor["actors"][0]["human_profile"] = {
        "evaluator_group": "researcher"
    }
    require(
        not actor_validator.is_valid(invalid_actor),
        "Actor registry allowed an LLM to carry a human profile",
    )
    invalid_actor = deepcopy(actor_probe)
    invalid_actor["actors"][0]["analysis_status"] = "primary"
    invalid_actor["actors"][0]["exclusion_reason"] = None
    require(
        not actor_validator.is_valid(invalid_actor),
        "Actor registry accepted primary analysis status with a sensitivity role",
    )
    invalid_actor = deepcopy(actor_probe)
    invalid_actor["actors"][0]["llm_profile"]["judge_role"] = (
        "same_family_sensitivity"
    )
    require(
        not actor_validator.is_valid(invalid_actor),
        "Actor registry accepted same-family sensitivity with overlap false",
    )
    invalid_actor = deepcopy(actor_probe)
    invalid_actor["actors"][0]["analysis_status"] = "primary"
    invalid_actor["actors"][0]["exclusion_reason"] = None
    invalid_actor["actors"][0]["llm_profile"]["judge_role"] = "primary"
    invalid_actor["actors"][0]["llm_profile"]["candidate_family_overlap"] = True
    require(
        not actor_validator.is_valid(invalid_actor),
        "Actor registry accepted a primary judge with candidate-family overlap",
    )

    observation_validator = validator_for(
        schemas, registry, "paired-observation-v1"
    )
    hash_probe = "0" * 64

    def execution_attempt(
        status: str,
        index: int = 1,
        kind: str = "initial",
    ) -> dict[str, Any]:
        response_present = status not in {"timeout", "provider_error"}
        usage_available = response_present
        return {
            "attempt_index": index,
            "attempt_kind": kind,
            "started_at_utc": "2026-08-25T00:00:00Z",
            "completed_at_utc": "2026-08-25T00:00:01Z",
            "attempt_status": status,
            "raw_request_artifact_id": f"request-{index}",
            "raw_request_sha256": hash_probe,
            "raw_response_artifact_id": f"response-{index}" if response_present else None,
            "raw_response_sha256": hash_probe if response_present else None,
            "provider_request_id": None,
            "provider_response_id": None,
            "provider_returned_model_id": "contract-probe" if response_present else None,
            "provider_returned_model_version": None,
            "provider_region": None,
            "finish_reason": "stop" if response_present else None,
            "filter_status": "filtered" if status == "content_filtered" else "not_filtered",
            "schema_error_summary": (
                "Schema-validation probe."
                if status in {"invalid_json", "invalid_schema"}
                else None
            ),
            "token_usage_available": usage_available,
            "input_tokens": 10 if usage_available else None,
            "output_tokens": 5 if usage_available else None,
            "cached_input_tokens": 0 if usage_available else None,
            "reasoning_tokens_available": usage_available,
            "reasoning_tokens": 2 if usage_available else None,
        }

    observation_probe = {
        "observation_schema_version": "direction-j-paired-observation-v1",
        "observation_id": "contract-probe",
        "study_id": "direction-j-v1",
        "evaluation_role": "synthetic_qualification",
        "item_id": "DJI_0000000000000000",
        "packet_id": "contract-probe",
        "output_id": "contract-probe",
        "corpus_id": "synthetic_proxy",
        "candidate_generation_run_id": "contract-probe",
        "candidate_generation_repetition": 1,
        "actor_id": "LLM_CONTRACT_PROBE",
        "actor_kind": "llm",
        "rating_repetition": 1,
        "item_payload_sha256": hash_probe,
        "interface_version": "direction-j-shared-interface-v1",
        "shared_rater_guide_version": "direction-j-rater-guide-v1",
        "shared_rater_guide_sha256": hash_probe,
        "semantic_input_sha256": hash_probe,
        "prompt_or_instrument_version": "contract-probe",
        "prompt_or_instrument_sha256": hash_probe,
        "started_at_utc": "2026-08-25T00:00:00Z",
        "completed_at_utc": "2026-08-25T00:00:01Z",
        "review_seconds": 1,
        "observation_status": "valid",
        "rating": rating,
        "blinding": {
            "blind_id": "contract-probe",
            "candidate_identity_hidden": True,
            "condition_hidden": True,
            "other_ratings_hidden": True,
            "unblinded_at_utc": None,
        },
        "execution": {
            "retry_count": 0,
            "attempts": [execution_attempt("schema_valid_output")],
            "token_usage_available": True,
            "input_tokens": 10,
            "output_tokens": 5,
            "cached_input_tokens": 0,
            "reasoning_tokens_available": True,
            "reasoning_tokens": 2,
            "cost_available": True,
            "cost_amount": 0,
            "cost_currency": "USD",
            "pricing_snapshot_id": "contract-probe",
        },
    }
    assert_valid(
        observation_validator, observation_probe, "First-call LLM observation probe"
    )

    repaired_probe = deepcopy(observation_probe)
    repaired_probe["execution"]["retry_count"] = 1
    repaired_probe["execution"]["attempts"] = [
        execution_attempt("invalid_json"),
        execution_attempt("schema_valid_output", 2, "format_only_repair"),
    ]
    assert_valid(
        observation_validator, repaired_probe, "Repaired LLM observation probe"
    )

    human_probe = deepcopy(observation_probe)
    human_probe["actor_id"] = "HUMAN_CONTRACT_PROBE"
    human_probe["actor_kind"] = "human"
    human_probe["execution"] = {
        "retry_count": 0,
        "attempts": [],
        "token_usage_available": False,
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "reasoning_tokens_available": False,
        "reasoning_tokens": None,
        "cost_available": False,
        "cost_amount": None,
        "cost_currency": None,
        "pricing_snapshot_id": None,
    }
    assert_valid(observation_validator, human_probe, "Human observation probe")

    for terminal_status, attempt_status in {
        "invalid_output": "invalid_schema",
        "timeout": "timeout",
        "provider_error": "provider_error",
        "content_filtered": "content_filtered",
    }.items():
        terminal_probe = deepcopy(observation_probe)
        terminal_probe["observation_status"] = terminal_status
        terminal_probe["rating"] = None
        terminal_probe["execution"]["attempts"] = [execution_attempt(attempt_status)]
        if attempt_status in {"timeout", "provider_error"}:
            terminal_probe["execution"].update(
                {
                    "token_usage_available": False,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cached_input_tokens": None,
                    "reasoning_tokens_available": False,
                    "reasoning_tokens": None,
                }
            )
        assert_valid(
            observation_validator,
            terminal_probe,
            f"Terminal {terminal_status} observation probe",
        )

    invalid_observation = deepcopy(observation_probe)
    invalid_observation["observation_status"] = "invalid_output"
    invalid_observation["rating"] = None
    require(
        not observation_validator.is_valid(invalid_observation),
        "Observation schema accepted invalid_output with a schema-valid final attempt",
    )
    invalid_observation = deepcopy(observation_probe)
    invalid_observation["observation_status"] = "invalid_output"
    invalid_observation["execution"]["attempts"] = [
        execution_attempt("invalid_schema")
    ]
    require(
        not observation_validator.is_valid(invalid_observation),
        "Observation schema accepted a nonnull rating on terminal failure",
    )
    invalid_observation = deepcopy(repaired_probe)
    invalid_observation["execution"]["attempts"][0] = execution_attempt(
        "schema_valid_output"
    )
    require(
        not observation_validator.is_valid(invalid_observation),
        "Observation schema accepted format-only repair after a valid first response",
    )

    adjudication_validator = validator_for(schemas, registry, "expert-adjudication-v1")
    adjudication_probe = {
        "adjudication_version": "direction-j-expert-adjudication-v1",
        "item_id": "DJI_0000000000000000",
        "panel_id": "contract-probe",
        "locked_individual_observation_ids": ["probe-1", "probe-2"],
        "adjudicated_at_utc": "2026-08-25T00:00:00Z",
        "operational_action": "accept",
        "severity": "none",
        "serious_error_flags": [],
        "error_locations": [],
        "requested_expertise": "none",
        "rationale": "Contract-validation probe; not an adjudication record.",
        "locked_before_private_unblind": True,
    }
    assert_valid(
        adjudication_validator, adjudication_probe, "Adjudication contract probe"
    )

    rationale_validator = validator_for(schemas, registry, "rationale-usefulness-v1")
    rationale_probe = {
        "rationale_rating_version": "direction-j-rationale-usefulness-v1",
        "rationale_packet_id": "contract-probe",
        "item_id": "DJI_0000000000000000",
        "evaluator_id": "contract-probe",
        "rated_at_utc": "2026-08-25T00:00:00Z",
        "source_localization": 4,
        "diagnostic_correctness": None,
        "bounded_actionability": 4,
        "ambiguity_and_material_preservation": 4,
        "cannot_judge": ["diagnostic_correctness"],
        "safe_to_send_to_revision": True,
        "review_seconds": 0,
        "rationale": "Contract-validation probe; not a study record.",
    }
    assert_valid(rationale_validator, rationale_probe, "Rationale contract probe")
    invalid_rationale = deepcopy(rationale_probe)
    invalid_rationale["diagnostic_correctness"] = 3
    require(
        not rationale_validator.is_valid(invalid_rationale),
        "Rationale schema accepted value and cannot_judge simultaneously",
    )

    repair_validator = validator_for(schemas, registry, "repair-assessment-v1")
    repair_probe = {
        "repair_assessment_version": "direction-j-repair-assessment-v1",
        "repair_packet_id": "contract-probe",
        "item_id": "DJI_0000000000000000",
        "revision_id": "contract-probe",
        "evaluator_id": "contract-probe",
        "rated_at_utc": "2026-08-25T00:00:00Z",
        "targeted_defect_repaired": True,
        "accurate_material_preserved": True,
        "collateral_error_flags": [],
        "cannot_judge": [],
        "successful_repair_without_collateral_error": True,
        "review_seconds": 0,
        "rationale": "Contract-validation probe; not a study record.",
    }
    assert_valid(repair_validator, repair_probe, "Repair contract probe")
    invalid_repair = deepcopy(repair_probe)
    invalid_repair["successful_repair_without_collateral_error"] = False
    require(
        not repair_validator.is_valid(invalid_repair),
        "Repair schema accepted an inconsistent derived outcome",
    )


def check_frozen_hashes(freeze: dict[str, Any]) -> None:
    require(
        freeze.get("status") == "synthetic_design_frozen_execution_pending",
        "Unexpected freeze status",
    )
    scope = freeze["scope"]
    require(scope["contains_real_source_text"] is False, "Freeze permits real text")
    require(scope["real_text_execution"] == "blocked", "Real-text gate is not blocked")
    require(
        scope["confirmatory_inference_allowed"] is False,
        "Freeze permits confirmatory inference from qualification",
    )

    for relative, expected in freeze["shared_interface"]["files"].items():
        path = DIRECTION_ROOT / relative
        require(path.is_file(), f"Frozen file is missing: {path}")
        require(sha256_path(path) == expected, f"Frozen hash mismatch: {path}")

    for relative, expected in freeze["normative_artifact_sha256"].items():
        path = DIRECTION_ROOT / relative
        require(path.is_file(), f"Frozen normative artifact is missing: {path}")
        require(
            sha256_path(path) == expected,
            f"Frozen normative-artifact hash mismatch: {path}",
        )

    builder = freeze["item_selection"]
    builder_path = PROJECT_ROOT / builder["builder_path"]
    require(
        sha256_path(builder_path) == builder["builder_sha256"],
        "Synthetic builder hash mismatch",
    )
    source_evidence = freeze["source_evidence"]
    for key in ("legacy_run_manifest", "legacy_private_blind_map", "legacy_judge_inventory"):
        record = source_evidence[key]
        path = PROJECT_ROOT / record["path"]
        require(path.is_file(), f"Frozen source evidence is missing: {path}")
        require(sha256_path(path) == record["sha256"], f"Source hash mismatch: {path}")
    benchmark_record = source_evidence["synthetic_benchmark"]
    require(
        (PROJECT_ROOT / benchmark_record["path"]).resolve() == BENCHMARK_PATH.resolve(),
        "Frozen benchmark path changed",
    )
    require(
        sha256_path(BENCHMARK_PATH) == benchmark_record["sha256"],
        "Frozen fictional benchmark hash mismatch",
    )
    bundle_hashes = source_evidence["blinded_bundle_sha256"]
    require(
        set(bundle_hashes) == {path.name for path in BLINDED_DIR.glob("*.json")},
        "Frozen blinded-bundle file set mismatch",
    )
    for filename, expected in bundle_hashes.items():
        require(
            sha256_path(BLINDED_DIR / filename) == expected,
            f"Frozen blinded-bundle hash mismatch: {filename}",
        )
    require(
        hashlib.sha256(canonical_bytes(bundle_hashes)).hexdigest()
        == source_evidence["blinded_bundle_fileset_sha256"],
        "Frozen blinded-bundle fileset receipt mismatch",
    )

    require(
        freeze["judges"]["primary"]["provider"] != "OpenAI",
        "Primary judge is not vendor-disjoint from the qualification candidates",
    )
    require(
        freeze["judges"]["primary"]["candidate_family_overlap_for_qualification"]
        is False,
        "Primary qualification overlap is not false",
    )
    require(
        freeze["judges"]["primary"]["rating_repetitions"] == 3,
        "Primary repetition count changed",
    )
    require(
        freeze["aggregation"]["primary_analysis"]
        == "J_PRIMARY_rating_repetition_1",
        "Primary aggregation changed",
    )
    require(
        freeze["aggregation"]["best_repeat_selection_forbidden"] is True,
        "Best-repeat selection is not forbidden",
    )
    require(
        freeze["prompting"]["answer_guide_visible"] is False
        and freeze["prompting"]["other_candidate_outputs_visible"] is False,
        "Prompt leaks legacy comparison information",
    )


def check_governance() -> None:
    gate = load_json(GOVERNANCE_PATH)
    require(gate["record_status"] == "template_not_approved", "Gate template appears approved")
    require(gate["gate_mode"] == "synthetic_only", "Gate is not synthetic-only")
    require(gate["synthetic_lane"]["runnable"] is True, "Synthetic lane is blocked")
    require(
        gate["synthetic_lane"]["contains_protected_real_text"] is False,
        "Synthetic lane claims protected real text",
    )
    real = gate["real_text_gate"]
    require(real["decision"] == "blocked" and real["runnable"] is False, "Real lane is open")
    require(real["all_requirements_satisfied"] is False, "Real requirements claim completion")
    require(len(real["requirements"]) == 10, "Governance requirement count changed")
    require(
        all(entry["status"] == "pending" for entry in real["requirements"]),
        "A tracked template requirement is not pending",
    )
    require(
        all(lane["runnable"] is False for lane in gate["corpus_lanes"].values()),
        "A real corpus lane is runnable",
    )
    require(
        gate["machine_check"]["allow_operator_override"] is False,
        "Governance permits an operator override",
    )
    require(
        "app/feedback-collector-demo/lib/study-data.ts"
        in gate["synthetic_lane"]["forbidden_input_files"],
        "Protected Warrant Study item bank is not explicitly forbidden",
    )
    legacy_manifest = load_json(LEGACY_MANIFEST)
    require(
        legacy_manifest.get("qualification_scope") == "synthetic_only",
        "Legacy source manifest is not synthetic-only",
    )
    require(
        legacy_manifest.get("benchmark", {}).get("contains_real_source_text") is False,
        "Legacy source manifest does not exclude real text",
    )
    legacy_governance = legacy_manifest.get("governance", {})
    require(
        legacy_governance.get("real_dreaddit_processed") is False
        and legacy_governance.get("real_agyw_processed") is False,
        "Legacy source manifest reports real-text processing",
    )
    benchmark = load_json(BENCHMARK_PATH)
    require(
        benchmark.get("provenance") == EXPECTED_BENCHMARK_PROVENANCE,
        "Fictional benchmark provenance assertion changed",
    )
    require(
        benchmark.get("license") == "CC0-1.0"
        and legacy_manifest.get("benchmark", {}).get("sha256")
        == sha256_path(BENCHMARK_PATH),
        "Fictional benchmark receipt does not match the baseline manifest",
    )


def check_execution_preparation(freeze: dict[str, Any]) -> None:
    """Verify offline request compilation while keeping every dispatch gate shut."""

    preparation = freeze.get("execution_preparation")
    require(isinstance(preparation, dict), "Freeze lacks execution preparation")
    expected = {
        "request_packet_version": "direction-j-provider-neutral-request-v1",
        "request_rendering_contract": "protocol/request_rendering_contract.md",
        "request_renderer": "scripts/render_request_packets.py",
        "request_packets_path": (
            "runs/20260825_synthetic_paired_qualification_prepared/"
            "request-packets/request_packets_v1.jsonl"
        ),
        "expected_request_packets": 96,
        "primary_request_packets": 72,
        "cross_family_sensitivity_request_packets": 24,
        "transport_schema_role": "structural_decoding_only",
        "full_shared_rating_post_validation_required": True,
        "format_only_retry_count": 1,
        "format_only_retry_trigger": ["invalid_json", "invalid_schema"],
        "third_attempt_allowed": False,
        "wire_adapter_status": "pending_provider_profile_and_wire_validation",
        "provider_wire_request_rendered": False,
        "provider_wire_adapters_frozen": False,
        "network_dispatch_authorized": False,
        "human_instrument_ready": False,
        "model_calls_authorized": False,
        "human_ratings_authorized": False,
        "execution_readiness_template": "config/execution_readiness.template.json",
        "execution_readiness_template_status": (
            "template_incomplete_not_authorizing"
        ),
        "execution_readiness_checker": "scripts/check_execution_readiness.py",
    }
    require(
        preparation == expected,
        "Frozen execution-preparation contract changed or is incomplete",
    )

    readiness = load_json(EXECUTION_READINESS_TEMPLATE_PATH)
    require(
        readiness.get("document_type")
        == "direction_j_synthetic_execution_readiness"
        and readiness.get("readiness_version")
        == "direction-j-synthetic-execution-readiness-v1"
        and readiness.get("record_status")
        == "template_incomplete_not_authorizing",
        "Tracked execution-readiness template appears authorizing or version-drifted",
    )
    scope = readiness.get("authorization_scope", {})
    require(
        scope.get("execution_lane") == "synthetic_qualification_only"
        and scope.get("contains_real_source_text") is False
        and scope.get("real_text_authorized") is False
        and scope.get("model_calls_authorized") is False
        and scope.get("human_rating_authorized") is False,
        "Tracked execution-readiness template opens an execution or real-text gate",
    )
    require(
        readiness.get("lineage", {}).get("status") == "pending"
        and all(
            readiness.get("human_actors", {}).get(actor_id, {}).get("status")
            == "pending"
            for actor_id in ("charlie", "QME_QUAL", "DOMAIN_QUAL")
        )
        and readiness.get("human_instrument", {}).get("status") == "pending"
        and all(
            profile.get("status") == "pending"
            for profile in readiness.get("provider_profiles", {}).values()
        ),
        "Tracked readiness template contains a completed prerequisite",
    )

    require(REQUEST_RENDERER_PATH.is_file(), "Request renderer is missing")
    require(REQUEST_PACKETS_PATH.is_file(), "Frozen request-packet bank is missing")
    renderer = runpy.run_path(
        str(REQUEST_RENDERER_PATH), run_name="direction_j_request_renderer"
    )
    bundle = renderer["load_and_validate_sources"]()
    packets, expected_bytes = renderer["render_packets"](bundle)
    stored_bytes = REQUEST_PACKETS_PATH.read_bytes()
    count = renderer["validate_candidate_jsonl"](stored_bytes, expected_bytes)
    require(count == 96 and len(packets) == 96, "Request-packet count drift")
    actor_counts = Counter(packet["actor_id"] for packet in packets)
    require(
        actor_counts == {"J_PRIMARY": 72, "J_SENS_GEMINI": 24},
        "Request-packet actor counts drift",
    )
    for packet in packets:
        adapter = packet.get("provider_wire_adapter", {})
        require(
            packet.get("contains_real_source_text") is False
            and packet.get("wire_adapter_status")
            == "pending_provider_profile_and_wire_validation"
            and packet.get("post_validation_required") is True
            and packet.get("structured_decoding_replaces_post_validation") is False
            and adapter.get("provider_wire_request") is None
            and adapter.get("provider_wire_request_rendered") is False
            and adapter.get("network_dispatch_authorized") is False
            and adapter.get("credential_access_authorized") is False,
            "A provider-neutral packet permits wire rendering, dispatch, or real text",
        )


def check_item_semantics(item: dict[str, Any], private: dict[str, Any]) -> None:
    forbidden = PUBLIC_FORBIDDEN_KEYS.intersection(walk_keys(item))
    require(not forbidden, f"Private keys leaked into {item['item_id']}: {sorted(forbidden)}")
    evidence = item["evidence"]
    require(
        [entry["display_order"] for entry in evidence] == list(range(1, len(evidence) + 1)),
        f"Display order is not contiguous: {item['item_id']}",
    )
    excerpt_ids = [entry["excerpt_id"] for entry in evidence]
    require(len(excerpt_ids) == len(set(excerpt_ids)), f"Duplicate excerpt ID: {item['item_id']}")

    presented = Counter(entry["source_id"] for entry in evidence)
    cited_entries = [entry for entry in evidence if entry["candidate_role"] != "context_only"]
    cited = Counter(entry["candidate_attributed_source_id"] for entry in cited_entries)
    require(None not in cited, f"Cited entry lacks candidate source: {item['item_id']}")
    coverage = item["source_coverage"]
    require(coverage["presented_excerpt_count"] == len(evidence), "Presented excerpt count drift")
    require(coverage["presented_source_count"] == len(presented), "Presented source count drift")
    require(
        coverage["candidate_cited_excerpt_count"] == len(cited_entries),
        "Candidate cited-excerpt count drift",
    )
    require(
        coverage["candidate_cited_source_count"] == len(cited),
        "Candidate cited-source count drift",
    )
    distribution = {row["source_id"]: row for row in coverage["source_distribution"]}
    require(set(distribution) == set(presented), "Coverage distribution source set drift")
    for source_id, count in presented.items():
        row = distribution[source_id]
        require(row["presented_excerpt_count"] == count, "Per-source presented count drift")
        require(
            row["candidate_cited_excerpt_count"] == cited[source_id],
            "Per-source candidate citation count drift",
        )

    displayed_sources = set(presented)
    displayed_excerpts = set(excerpt_ids)
    for entry in cited_entries:
        require(
            entry["candidate_attributed_source_id"] in displayed_sources,
            f"Candidate source not displayed: {item['item_id']}",
        )
        require(
            entry["candidate_attributed_excerpt_id"] in displayed_excerpts,
            f"Candidate excerpt not displayed: {item['item_id']}",
        )

    flags = private["planted_serious_error_flags"]
    quote_mismatches = [
        entry
        for entry in cited_entries
        if entry["candidate_quote"] not in entry["text"]
    ]
    source_mismatches = [
        entry
        for entry in cited_entries
        if entry["candidate_attributed_source_id"] != entry["source_id"]
    ]
    excerpt_mismatches = [
        entry
        for entry in cited_entries
        if entry["candidate_attributed_excerpt_id"] != entry["excerpt_id"]
    ]
    if "fabricated_or_altered_quote" in flags:
        require(quote_mismatches, f"Quote sentinel is not observable: {item['item_id']}")
    else:
        require(not quote_mismatches, f"Unexpected quote mismatch: {item['item_id']}")
    if "wrong_attribution" in flags:
        require(
            source_mismatches or excerpt_mismatches,
            f"Attribution sentinel is not observable: {item['item_id']}",
        )
    else:
        require(not source_mismatches, f"Unexpected source mismatch: {item['item_id']}")
        require(not excerpt_mismatches, f"Unexpected excerpt mismatch: {item['item_id']}")


def check_prepared_run(
    freeze: dict[str, Any], schemas: dict[str, dict[str, Any]], registry: Registry
) -> None:
    require(RUN_ROOT.is_dir(), f"Prepared run is missing: {RUN_ROOT}")
    item_path = RUN_ROOT / "evaluator_items.jsonl"
    private_path = RUN_ROOT / "private" / "item_key.jsonl"
    items = load_canonical_jsonl(item_path)
    private_rows = load_canonical_jsonl(private_path)
    require(len(items) == 24 and len(private_rows) == 24, "Expected 24 public/private items")
    require(
        stat.S_IMODE(private_path.stat().st_mode) == 0o600,
        "Private item key is not mode 0600",
    )
    item_validator = validator_for(schemas, registry, "evaluator-item-v1")
    item_by_id: dict[str, dict[str, Any]] = {}
    item_hashes: dict[str, str] = {}
    for item in items:
        assert_valid(item_validator, item, f"Evaluator item {item.get('item_id')}")
        require(
            item["corpus_id"] == "synthetic_proxy",
            f"Prepared qualification item has non-synthetic corpus_id: {item.get('item_id')}",
        )
        item_id = item["item_id"]
        require(item_id not in item_by_id, f"Duplicate public item: {item_id}")
        item_by_id[item_id] = item
        item_hashes[item_id] = hashlib.sha256(canonical_bytes(item)).hexdigest()

    guide_sha256 = sha256_path(RATER_GUIDE_PATH)
    semantic_input_hashes = {
        item_id: hashlib.sha256(
            canonical_bytes(
                {
                    "interface_version": "direction-j-shared-interface-v1",
                    "item_payload_sha256": item_hash,
                    "shared_rater_guide_sha256": guide_sha256,
                    "shared_rater_guide_version": "direction-j-rater-guide-v1",
                }
            )
        ).hexdigest()
        for item_id, item_hash in item_hashes.items()
    }

    private_by_id = {row["item_id"]: row for row in private_rows}
    require(len(private_by_id) == 24, "Duplicate private item key")
    require(set(item_by_id) == set(private_by_id), "Public/private item set mismatch")
    conditions = Counter(row["condition"] for row in private_rows)
    require(conditions == {"natural": 12, "sentinel_control": 12}, "Condition balance changed")
    families = Counter(
        flag for row in private_rows for flag in row["planted_serious_error_flags"]
    )
    require(set(families) == EXPECTED_SERIOUS_FAMILIES, "Sentinel family set changed")
    require(sum(families.values()) == 12, "Expected exactly 12 planted sentinel flags")
    require(
        len({row["parent_natural_item_sha256"] for row in private_rows}) == 24,
        "Selected parent theme outputs overlap",
    )
    for item_id, item in item_by_id.items():
        private = private_by_id[item_id]
        require(
            private["item_payload_sha256"] == item_hashes[item_id],
            f"Private/public hash mismatch: {item_id}",
        )
        if private["condition"] == "natural":
            require(
                private["planted_serious_error_flags"] == [],
                f"Natural row contains a planted flag: {item_id}",
            )
        else:
            require(
                len(private["planted_serious_error_flags"]) == 1,
                f"Control does not have exactly one planted flag: {item_id}",
            )
        check_item_semantics(item, private)

    assignment_dir = RUN_ROOT / "assignments"
    actual_assignment_names = {path.name for path in assignment_dir.glob("*.csv")}
    require(
        actual_assignment_names == set(EXPECTED_ASSIGNMENTS),
        "Assignment file set changed",
    )
    assignment_orders: dict[str, tuple[str, ...]] = {}
    all_assignment_ids: set[str] = set()
    for name, (actor_id, actor_kind, repetition) in EXPECTED_ASSIGNMENTS.items():
        path = assignment_dir / name
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            require(
                reader.fieldnames
                == [
                    "assignment_id",
                    "actor_id",
                    "actor_kind",
                    "rating_repetition",
                    "sequence",
                    "item_id",
                    "item_payload_sha256",
                    "interface_version",
                    "shared_rater_guide_version",
                    "shared_rater_guide_sha256",
                    "semantic_input_sha256",
                    "packet_id",
                    "output_id",
                    "corpus_id",
                    "evaluation_role",
                ],
                f"Assignment columns changed or expose private fields: {name}",
            )
            rows = list(reader)
        require(len(rows) == 24, f"Expected 24 assignments in {name}")
        require({row["item_id"] for row in rows} == set(item_by_id), f"Item set drift in {name}")
        require([int(row["sequence"]) for row in rows] == list(range(1, 25)), f"Sequence drift in {name}")
        require(all(row["actor_id"] == actor_id for row in rows), f"Actor drift in {name}")
        require(all(row["actor_kind"] == actor_kind for row in rows), f"Actor kind drift in {name}")
        require(
            all(int(row["rating_repetition"]) == repetition for row in rows),
            f"Rating repetition drift in {name}",
        )
        require(
            all(row["evaluation_role"] == "synthetic_qualification" for row in rows),
            f"Evaluation role drift in {name}",
        )
        for row in rows:
            require(
                row["item_payload_sha256"] == item_hashes[row["item_id"]],
                f"Assignment item hash drift in {name}",
            )
            require(
                row["interface_version"] == "direction-j-shared-interface-v1",
                f"Assignment interface drift in {name}",
            )
            require(
                row["shared_rater_guide_version"] == "direction-j-rater-guide-v1"
                and row["shared_rater_guide_sha256"] == guide_sha256,
                f"Assignment guide lock drift in {name}",
            )
            require(
                row["semantic_input_sha256"]
                == semantic_input_hashes[row["item_id"]],
                f"Assignment semantic-input hash drift in {name}",
            )
            require(
                row["corpus_id"] == item_by_id[row["item_id"]]["corpus_id"],
                f"Assignment corpus drift in {name}",
            )
            require(row["assignment_id"] not in all_assignment_ids, "Duplicate assignment ID")
            all_assignment_ids.add(row["assignment_id"])
        assignment_orders[name] = tuple(row["item_id"] for row in rows)
    require(
        len(set(assignment_orders.values())) == len(assignment_orders),
        "Two actor/repetition assignment orders are identical",
    )

    build_report = load_json(RUN_ROOT / "build_report.json")
    run_manifest = load_json(RUN_ROOT / "run_manifest.json")
    require(build_report["status"] == "prepared_not_run", "Build report claims execution")
    require(run_manifest["status"] == "prepared_not_run", "Run manifest claims execution")
    require(run_manifest["ratings_collected"] == 0, "Run manifest claims ratings")
    require(run_manifest["outcomes_available"] is False, "Run manifest claims outcomes")
    require(build_report["contains_real_source_text"] is False, "Build report claims real text")
    require(build_report["selection_uses_legacy_judge_scores"] is False, "Selection used old scores")
    require(build_report["evaluator_items"] == 24, "Build report item count drift")
    source_receipt = build_report["source_receipt"]
    require(
        hashlib.sha256(canonical_bytes(source_receipt)).hexdigest()
        == build_report["source_receipt_sha256"],
        "Synthetic source receipt hash drift",
    )
    require(
        source_receipt["independently_authored_fictional_text"] is True
        and source_receipt["contains_real_source_text"] is False
        and source_receipt["synthetic_benchmark_provenance"]
        == EXPECTED_BENCHMARK_PROVENANCE,
        "Synthetic source receipt lacks fictional provenance",
    )
    require(
        source_receipt["baseline_run_manifest_sha256"] == sha256_path(LEGACY_MANIFEST)
        and source_receipt["synthetic_benchmark_sha256"] == sha256_path(BENCHMARK_PATH)
        and source_receipt["blinded_bundle_sha256"]
        == freeze["source_evidence"]["blinded_bundle_sha256"],
        "Synthetic source receipt does not match frozen inputs",
    )
    require(
        build_report["unique_fictional_base_packets"] == 4
        and build_report["items_are_source_independent"] is False,
        "Qualification source-cluster limitation drift",
    )
    require(
        run_manifest["assignment_manifest_count"] == 7
        and run_manifest["unique_fictional_base_packets"] == 4
        and run_manifest["items_are_source_independent"] is False,
        "Run-manifest qualification structure drift",
    )
    require(
        run_manifest["qualification_blinding_strength"]
        == "operational_mount_isolation_not_secure_against_workspace_reader",
        "Synthetic blinding limitation is missing",
    )
    require(
        run_manifest["independently_authored_fictional_text"] is True
        and run_manifest["source_receipt_sha256"]
        == build_report["source_receipt_sha256"]
        and run_manifest["synthetic_benchmark_sha256"]
        == sha256_path(BENCHMARK_PATH)
        and run_manifest["blinded_bundle_fileset_sha256"]
        == freeze["source_evidence"]["blinded_bundle_fileset_sha256"],
        "Run-manifest synthetic source lineage drift",
    )
    require(
        run_manifest["freeze_sha256"] == sha256_path(FREEZE_PATH)
        and run_manifest["build_report_sha256"]
        == sha256_path(RUN_ROOT / "build_report.json"),
        "Run-manifest freeze/build lineage drift",
    )
    require(
        build_report["input_hashes"]["direction_j_freeze"] == sha256_path(FREEZE_PATH),
        "Run was not built from the current freeze",
    )
    require(
        build_report["input_hashes"]["baseline_run_manifest"]
        == sha256_path(LEGACY_MANIFEST),
        "Legacy manifest hash drift in build report",
    )
    require(
        build_report["input_hashes"]["baseline_blind_map"]
        == sha256_path(LEGACY_BLIND_MAP),
        "Legacy blind-map hash drift in build report",
    )
    require(
        build_report["input_hashes"]["evaluator_item_schema"]
        == sha256_path(SCHEMA_ROOT / "evaluator_item.schema.json"),
        "Evaluator-item schema hash drift in build report",
    )
    require(
        build_report["input_hashes"]["shared_rater_guide"] == guide_sha256,
        "Shared-guide hash drift in build report",
    )
    require(
        build_report["output_hashes"]["evaluator_items.jsonl"] == sha256_path(item_path),
        "Evaluator bank output hash drift",
    )
    require(
        build_report["output_hashes"]["private/item_key.jsonl"] == sha256_path(private_path),
        "Private key output hash drift",
    )
    require(
        run_manifest["evaluator_items_sha256"] == sha256_path(item_path),
        "Run-manifest evaluator hash drift",
    )
    require(
        run_manifest["interface_version"] == "direction-j-shared-interface-v1"
        and run_manifest["shared_rater_guide_version"]
        == "direction-j-rater-guide-v1"
        and run_manifest["shared_rater_guide_sha256"] == guide_sha256
        and run_manifest["semantic_input_hash_rule"] == "canonical_manifest_v1",
        "Run-manifest semantic-input lock drift",
    )
    require(
        run_manifest["private_key_sha256"] == sha256_path(private_path),
        "Run-manifest private-key hash drift",
    )
    for name, report in build_report["assignment_files"].items():
        require(
            sha256_path(assignment_dir / name) == report["sha256"],
            f"Assignment output hash drift: {name}",
        )
        require(int(report["rows"]) == 24, f"Assignment count drift: {name}")

    expected_observations = freeze["first_run"]["expected_observations"]
    require(
        run_manifest["expected_observations"] == {
            "charlie": expected_observations["charlie"],
            "J_PRIMARY": expected_observations["J_PRIMARY"],
            "J_SENS_GEMINI": expected_observations["J_SENS_GEMINI"],
            "QME_QUAL": expected_observations["QME_QUAL"],
            "DOMAIN_QUAL": expected_observations["DOMAIN_QUAL"],
        },
        "Expected-observation plan drift",
    )

    rating_payloads = [
        path
        for path in (RUN_ROOT / "ratings").iterdir()
        if path.name != "README.md"
    ]
    raw_payloads = [
        path
        for path in (RUN_ROOT / "raw_model_responses").iterdir()
        if path.name != "README.md"
    ]
    require(not rating_payloads, "Prepared run contains rating payloads")
    require(not raw_payloads, "Prepared run contains raw model responses")
    require((RUN_ROOT / "README.md").is_file(), "Prepared run README is missing")
    require(
        not list(RUN_ROOT.glob("*result*")) and not list(RUN_ROOT.glob("*RESULT*")),
        "Prepared run contains a results artifact",
    )


def main() -> None:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    freeze = load_json(FREEZE_PATH)
    schemas, registry = schema_contracts()
    check_schema_semantics(schemas, registry)
    check_frozen_hashes(freeze)
    check_governance()
    check_prepared_run(freeze, schemas, registry)
    check_execution_preparation(freeze)
    print(
        "Direction J validation passed: 7 schemas, 24 fictional items, "
        "7 blinded assignment manifests (5 first-stage, 2 expert), "
        "96 provider-neutral request packets with dispatch blocked, "
        "real-text gate blocked, 0 ratings, 0 results."
    )


if __name__ == "__main__":
    main()
