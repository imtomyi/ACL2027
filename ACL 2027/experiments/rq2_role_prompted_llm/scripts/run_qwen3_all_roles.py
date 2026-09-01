#!/usr/bin/env python3
"""Source-free Qwen3 All roles component for WarrantRoute.

The component validates the three-role review matrix, derives primary and
stability All roles outcomes, and blocks all source-bearing execution under the
tracked engineering freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "qwen3_all_roles_freeze.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import qwen3_all_roles_runtime as runtime  # noqa: E402
from prompt_limit_guard import harden_ollama_request  # noqa: E402


ROLE_ORDER = ("researcher", "qualitative_methods", "domain")
REPETITIONS = (1, 2, 3)
ERROR_FAMILIES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)
TARGET_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}
EXPECTED_ACTOR_IDS = {
    "researcher": "qwen3_8b_researcher_reviewer_v1",
    "qualitative_methods": "qwen3_8b_qualitative_methods_reviewer_v1",
    "domain": "qwen3_8b_domain_reviewer_v1",
}
EXPECTED_DISPLAY_NAMES = {
    "researcher": "Researchers without specialist expertise",
    "qualitative_methods": "Qualitative methods experts",
    "domain": "Domain experts",
}
EXPECTED_PROMPT_FILES = {
    "researcher": "experiments/rq2_role_prompted_llm/prompts/researcher_v1.md",
    "qualitative_methods": "experiments/rq2_role_prompted_llm/prompts/methods_v1.md",
    "domain": "experiments/rq2_role_prompted_llm/prompts/domain_v1.md",
}
EXPECTED_MODEL_MANIFEST_PATH = (
    "/Users/OODI/.ollama/models/manifests/registry.ollama.ai/library/qwen3/8b"
)
EXPECTED_MODEL_MANIFEST_SHA256 = (
    "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
)
EXPECTED_ASSET_FILES = {
    "runner": "experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py",
    "runtime": "experiments/rq2_role_prompted_llm/scripts/qwen3_all_roles_runtime.py",
    "prompt_limit_guard": "experiments/rq2_role_prompted_llm/scripts/prompt_limit_guard.py",
    "contract": "experiments/rq2_role_prompted_llm/protocol/qwen3_all_roles_contract_v1.md",
    "shared_rater_guide": "experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md",
    "evaluator_item_schema": "experiments/direction_j_llm_as_rater/schemas/evaluator_item.schema.json",
    "shared_rating_transport_schema": "experiments/rq2_role_prompted_llm/schemas/shared_rating_transport_v1.schema.json",
    "shared_rating_schema": "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json",
    "all_roles_input_schema": "experiments/rq2_role_prompted_llm/schemas/all_roles_input_v1.schema.json",
    "all_roles_result_schema": "experiments/rq2_role_prompted_llm/schemas/all_roles_result_v1.schema.json",
    "all_roles_result_seal_schema": "experiments/rq2_role_prompted_llm/schemas/all_roles_result_seal_v1.schema.json",
}


class AllRolesError(RuntimeError):
    """A finite source-free failure safe to expose to an operator."""


@dataclass(frozen=True)
class FrozenContext:
    """Immutable bytes for the validated tracked component freeze."""

    raw_config_bytes: bytes
    freeze_sha256: str
    canonical_config_bytes: bytes
    input_schema_bytes: bytes
    result_schema_bytes: bytes
    result_seal_schema_bytes: bytes

    def config(self) -> dict[str, Any]:
        return json.loads(self.canonical_config_bytes)

    def input_schema(self) -> dict[str, Any]:
        return json.loads(self.input_schema_bytes)

    def result_schema(self) -> dict[str, Any]:
        return json.loads(self.result_schema_bytes)

    def result_seal_schema(self) -> dict[str, Any]:
        return json.loads(self.result_seal_schema_bytes)


@dataclass(frozen=True)
class ValidatedFixture:
    """Canonical source-free fixture captured after structural and hash checks."""

    canonical_input_bytes: bytes
    input_sha256: str
    fixture_matrix_sha256: str

    def value(self) -> dict[str, Any]:
        return json.loads(self.canonical_input_bytes)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AllRolesError(code)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def _load_asset(entry: dict[str, Any], label: str) -> bytes:
    _exact_keys(entry, {"file", "sha256"}, f"{label}_asset")
    try:
        return runtime.validate_hash(
            runtime.workspace_path(entry["file"]),
            entry["sha256"],
            label,
        )
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc


def validate_freeze(
    config: dict[str, Any],
    *,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    require(config_path == DEFAULT_CONFIG, "nondefault_freeze_rejected")
    _exact_keys(
        config,
        {
            "document_type",
            "freeze_version",
            "status",
            "execution_class",
            "source_bearing_execution_allowed",
            "all_roles_real_derivation_allowed",
            "manuscript_eligible",
            "reviewer_actors",
            "candidate_generation_separation",
            "service",
            "decoding",
            "rating_repetitions",
            "primary_repetition",
            "repetition_seeds",
            "roles",
            "all_roles_rule",
            "bootstrap",
            "assets",
            "prompt_limit",
            "source_free_canary",
        },
        "freeze",
    )
    require(
        config["document_type"] == "warrantroute_qwen3_all_roles_component_freeze",
        "freeze_type_invalid",
    )
    require(config["freeze_version"] == "qwen3-all-roles-v1", "freeze_version_invalid")
    require(config["status"] == "source_free_component_only", "freeze_status_invalid")
    require(config["execution_class"] == "engineering_component", "execution_class_invalid")
    require(config["source_bearing_execution_allowed"] is False, "source_execution_enabled")
    require(config["all_roles_real_derivation_allowed"] is False, "real_derivation_enabled")
    require(config["manuscript_eligible"] is False, "manuscript_eligibility_enabled")

    actors = config["reviewer_actors"]
    require(tuple(actors) == ROLE_ORDER, "reviewer_actor_order_invalid")
    observed_actor_ids: set[str] = set()
    for role in ROLE_ORDER:
        actor = actors[role]
        _exact_keys(
            actor,
            {
                "actor_id",
                "actor_kind",
                "task_role",
                "prompted_role",
                "model_id",
                "local_manifest_path",
                "local_manifest_file_sha256",
            },
            f"actor_{role}",
        )
        require(actor["actor_id"] not in observed_actor_ids, "reviewer_actor_id_duplicate")
        observed_actor_ids.add(actor["actor_id"])
        require(actor["actor_id"] == EXPECTED_ACTOR_IDS[role], f"reviewer_actor_id_drift:{role}")
        require(actor["actor_kind"] == "llm", f"actor_kind_invalid:{role}")
        require(actor["task_role"] == "reviewer", f"actor_task_invalid:{role}")
        require(actor["prompted_role"] == role, f"actor_prompted_role_invalid:{role}")
        require(actor["model_id"] == "qwen3:8b", f"actor_model_invalid:{role}")
        require(
            actor["local_manifest_path"] == EXPECTED_MODEL_MANIFEST_PATH,
            f"model_manifest_path_drift:{role}",
        )
        require(
            actor["local_manifest_file_sha256"] == EXPECTED_MODEL_MANIFEST_SHA256,
            f"model_manifest_hash_drift:{role}",
        )
    try:
        runtime.validate_hash(
            Path(EXPECTED_MODEL_MANIFEST_PATH),
            EXPECTED_MODEL_MANIFEST_SHA256,
            "qwen_model_manifest",
        )
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc

    require(
        config["candidate_generation_separation"]
        == {
            "authorized_study_must_consume_sealed_evaluator_items": True,
            "authorized_study_must_consume_sealed_review_matrix": True,
            "candidate_generator_actor_bound_in_component": False,
            "distinct_actor_and_run_records_required": True,
            "same_review_matrix_reused_across_rq2_methods": True,
            "authorized_study_freeze_required": True,
        },
        "candidate_generation_separation_invalid",
    )
    try:
        runtime.validate_numeric_loopback(config["service"]["url"])
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc
    require(
        config["service"]
        == {"url": "http://127.0.0.1:11434", "ollama_version": "0.18.0"},
        "service_contract_invalid",
    )
    require(
        config["decoding"]
        == {
            "temperature": 0.2,
            "top_p": 1,
            "num_ctx": 8192,
            "max_output_tokens": 512,
            "think": False,
            "stream": False,
            "tools_enabled": False,
            "automatic_retries": 0,
        },
        "decoding_contract_invalid",
    )
    require(config["rating_repetitions"] == 3, "rating_repetition_count_invalid")
    require(config["primary_repetition"] == 1, "primary_repetition_invalid")
    require(
        config["repetition_seeds"] == [2027082601, 2027082602, 2027082603]
        and len(set(config["repetition_seeds"])) == 3,
        "repetition_seeds_invalid",
    )

    roles = config["roles"]
    require(tuple(roles) == ROLE_ORDER, "role_order_invalid")
    for role in ROLE_ORDER:
        _exact_keys(roles[role], {"display_name", "prompt"}, f"role_{role}")
        require(
            roles[role]["display_name"] == EXPECTED_DISPLAY_NAMES[role],
            f"role_label_invalid:{role}",
        )
        require(
            roles[role]["prompt"]["file"] == EXPECTED_PROMPT_FILES[role],
            f"role_prompt_path_drift:{role}",
        )

    require(
        config["all_roles_rule"]
        == {
            "method_status": "descriptive_full_review_reference",
            "roles": list(ROLE_ORDER),
            "primary_repetition": 1,
            "primary_operation": "per_item_or_of_role_target_flag_hits",
            "role_hit_rule": "valid_empty_cannot_judge_contains_required_flag",
            "overlapping_role_hits_count_once": True,
            "failure_contributes_empty_flags": True,
            "missing_observation_must_be_explicit": True,
            "denominator": "eligible_items",
            "repetitions_never_enlarge_denominator": True,
            "stability_operation": "two_of_three_within_role_then_or_across_roles",
            "no_fourth_prompt_or_actor": True,
            "routing_or_fixed_role_selection_used": False,
        },
        "all_roles_rule_invalid",
    )
    require(
        config["bootstrap"]
        == {
            "resamples": 10000,
            "seed": 20270826,
            "minimum_independent_clusters": 5,
            "interval": "percentile_95",
            "resampling_unit": "frozen_source_cluster",
            "too_few_or_degenerate_action": "ci_not_estimable",
        },
        "bootstrap_contract_invalid",
    )
    require(
        config["prompt_limit"]
        == {
            "truncate": False,
            "shift": False,
            "safety_margin_tokens": 256,
            "real_packet_chunking_allowed": False,
        },
        "prompt_limit_contract_invalid",
    )
    require(
        config["source_free_canary"]
        == {"enabled": True, "contains_source_text": False, "writes_outputs": False},
        "canary_contract_invalid",
    )

    assets = config["assets"]
    require(set(assets) == set(EXPECTED_ASSET_FILES), "asset_set_invalid")
    for label, expected_file in EXPECTED_ASSET_FILES.items():
        require(assets[label]["file"] == expected_file, f"{label}_path_drift")
    loaded = {label: _load_asset(entry, label) for label, entry in assets.items()}
    role_prompts = {
        role: _load_asset(roles[role]["prompt"], f"{role}_prompt")
        for role in ROLE_ORDER
    }
    require(b"generalist" not in role_prompts["researcher"].lower(), "researcher_prompt_naming_drift")

    schemas: dict[str, Any] = {}
    for label in (
        "evaluator_item_schema",
        "shared_rating_transport_schema",
        "shared_rating_schema",
        "all_roles_input_schema",
        "all_roles_result_schema",
        "all_roles_result_seal_schema",
    ):
        try:
            schemas[label] = json.loads(loaded[label])
            jsonschema.Draft202012Validator.check_schema(schemas[label])
        except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
            raise AllRolesError(f"{label}_invalid") from exc
    return {
        "role_prompts": {role: value.decode("utf-8") for role, value in role_prompts.items()},
        "shared_rater_guide": loaded["shared_rater_guide"].decode("utf-8"),
        **schemas,
    }


def load_frozen_context() -> FrozenContext:
    """Load and validate only the tracked default freeze and capture immutable bytes."""

    try:
        raw_config = runtime.read_regular_bytes(DEFAULT_CONFIG)
        config = json.loads(raw_config)
    except (runtime.AllRolesRuntimeError, json.JSONDecodeError) as exc:
        raise AllRolesError("active_freeze_load_failed") from exc
    assets = validate_freeze(config, config_path=DEFAULT_CONFIG)
    return FrozenContext(
        raw_config_bytes=raw_config,
        freeze_sha256=sha256_bytes(raw_config),
        canonical_config_bytes=canonical_bytes(config),
        input_schema_bytes=canonical_bytes(assets["all_roles_input_schema"]),
        result_schema_bytes=canonical_bytes(assets["all_roles_result_schema"]),
        result_seal_schema_bytes=canonical_bytes(
            assets["all_roles_result_seal_schema"]
        ),
    )


def build_rating_request(
    config: dict[str, Any],
    assets: dict[str, Any],
    item: dict[str, Any],
    *,
    role: str,
    repetition: int,
) -> dict[str, Any]:
    require(role in ROLE_ORDER, "unknown_reviewer_role")
    require(repetition in REPETITIONS, "rating_repetition_invalid")
    try:
        runtime.validate_evaluator_item(item, assets["evaluator_item_schema"])
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc
    profile = config["decoding"]
    request = {
        "model": config["reviewer_actors"][role]["model_id"],
        "stream": profile["stream"],
        "think": profile["think"],
        "messages": [
            {"role": "system", "content": assets["role_prompts"][role]},
            {
                "role": "user",
                "content": runtime.reviewer_user_prompt(
                    assets["shared_rater_guide"],
                    item,
                ),
            },
        ],
        "format": assets["shared_rating_transport_schema"],
        "options": {
            "temperature": profile["temperature"],
            "top_p": profile["top_p"],
            "num_predict": profile["max_output_tokens"],
            "seed": config["repetition_seeds"][repetition - 1],
        },
        "keep_alive": "5m",
    }
    require("tools" not in request, "tools_payload_rejected")
    return harden_ollama_request(request, num_ctx=profile["num_ctx"])


def source_free_request_plan(config: dict[str, Any], assets: dict[str, Any]) -> dict[str, Any]:
    item = runtime.inert_canary_item()
    item_sha256 = sha256_bytes(canonical_bytes(item))
    requests: list[dict[str, Any]] = []
    for role in ROLE_ORDER:
        for repetition in REPETITIONS:
            request = build_rating_request(
                config,
                assets,
                item,
                role=role,
                repetition=repetition,
            )
            requests.append(
                {
                    "role": role,
                    "repetition": repetition,
                    "evaluator_item_sha256": item_sha256,
                    "request_sha256": sha256_bytes(canonical_bytes(request)),
                    "seed": request["options"]["seed"],
                }
            )
    return {
        "component": config["freeze_version"],
        "status": "passed",
        "request_count": len(requests),
        "reviewer_role_count": len(ROLE_ORDER),
        "fourth_all_roles_actor_created": False,
        "requests": requests,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def _observation_hash_preimage(
    item_id: str,
    role: str,
    observation: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in observation.items()
        if key != "fixture_observation_sha256"
    }
    return {
        "hash_domain": "warrantroute:qwen3-all-roles:fixture-observation:v1",
        "item_id": item_id,
        "prompted_role": role,
        "observation": payload,
    }


def fixture_observation_sha256(
    item_id: str,
    role: str,
    observation: dict[str, Any],
) -> str:
    return sha256_bytes(
        canonical_bytes(_observation_hash_preimage(item_id, role, observation))
    )


def fixture_matrix_sha256(value: dict[str, Any]) -> str:
    items: list[dict[str, Any]] = []
    try:
        for item in value["items"]:
            observations: list[dict[str, Any]] = []
            for role in ROLE_ORDER:
                for observation in item["role_observations"][role]:
                    observations.append(
                        {
                            "prompted_role": role,
                            "rating_repetition": observation["rating_repetition"],
                            "fixture_observation_sha256": observation[
                                "fixture_observation_sha256"
                            ],
                        }
                    )
            items.append(
                {
                    "item_id": item["item_id"],
                    "cluster_id": item["cluster_id"],
                    "error_family": item["error_family"],
                    "required_flag": item["required_flag"],
                    "evaluator_item_sha256": item["evaluator_item_sha256"],
                    "observations": observations,
                }
            )
        preimage = {
            "hash_domain": "warrantroute:qwen3-all-roles:fixture-matrix:v1",
            "reviewer_model": value["reviewer_model"],
            "items": items,
        }
    except (KeyError, TypeError) as exc:
        raise AllRolesError("fixture_matrix_preimage_invalid") from exc
    return sha256_bytes(canonical_bytes(preimage))


def seal_fixture_observations(value: dict[str, Any]) -> dict[str, Any]:
    """Return a copied fixture with domain-separated observation commitments."""

    copied = json.loads(json.dumps(value, ensure_ascii=False))
    try:
        for item in copied["items"]:
            for role in ROLE_ORDER:
                for observation in item["role_observations"][role]:
                    observation["fixture_observation_sha256"] = (
                        fixture_observation_sha256(
                        item["item_id"],
                        role,
                        observation,
                    )
                    )
    except (KeyError, TypeError) as exc:
        raise AllRolesError("fixture_observation_sealing_invalid") from exc
    return copied


def _validate_analysis_input(
    value: dict[str, Any],
    *,
    schema: dict[str, Any],
    config: dict[str, Any],
) -> None:
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise AllRolesError("all_roles_input_schema_invalid") from exc
    require(bool(value["items"]), "all_roles_items_empty")
    snapshot = EXPECTED_MODEL_MANIFEST_SHA256
    require(
        value["reviewer_model"]
        == {"model_id": "qwen3:8b", "model_snapshot_sha256": snapshot},
        "analysis_reviewer_model_drift",
    )

    item_ids: set[str] = set()
    evaluator_hashes: set[str] = set()
    observation_hashes: set[str] = set()
    observation_tuples: set[tuple[str, str, int]] = set()
    for item in value["items"]:
        item_id = item["item_id"]
        evaluator_hash = item["evaluator_item_sha256"]
        require(item_id not in item_ids, "all_roles_item_duplicate")
        item_ids.add(item_id)
        require(evaluator_hash not in evaluator_hashes, "evaluator_item_duplicate")
        evaluator_hashes.add(evaluator_hash)
        require(
            item["required_flag"] == TARGET_TO_FLAG[item["error_family"]],
            "target_flag_mapping_drift",
        )
        for role in ROLE_ORDER:
            observations = item["role_observations"][role]
            require(
                tuple(row["rating_repetition"] for row in observations) == REPETITIONS,
                f"role_repetition_order_invalid:{role}",
            )
            for observation in observations:
                repetition = observation["rating_repetition"]
                observation_tuple = (item_id, role, repetition)
                require(
                    observation_tuple not in observation_tuples,
                    "observation_tuple_duplicate",
                )
                observation_tuples.add(observation_tuple)
                require(
                    observation["actor_id"] == config["reviewer_actors"][role]["actor_id"],
                    f"reviewer_actor_drift:{role}",
                )
                require(
                    observation["model_snapshot_sha256"] == snapshot,
                    f"reviewer_snapshot_drift:{role}",
                )
                require(
                    observation["role_prompt_sha256"]
                    == config["roles"][role]["prompt"]["sha256"],
                    f"reviewer_prompt_drift:{role}",
                )
                require(
                    observation["evaluator_item_sha256"] == evaluator_hash,
                    f"evaluator_item_hash_drift:{role}",
                )
                observation_hash = observation["fixture_observation_sha256"]
                require(observation_hash not in observation_hashes, "observation_hash_duplicate")
                observation_hashes.add(observation_hash)
                require(
                    observation_hash
                    == fixture_observation_sha256(item_id, role, observation),
                    "observation_hash_mismatch",
                )

    expected_observations = len(value["items"]) * len(ROLE_ORDER) * len(REPETITIONS)
    require(len(observation_tuples) == expected_observations, "review_matrix_incomplete")


def validate_fixture(
    value: dict[str, Any],
    context: FrozenContext,
) -> ValidatedFixture:
    """Validate and snapshot a source-free fixture without trusting external seals."""

    require(context == load_frozen_context(), "frozen_context_not_active")
    _validate_analysis_input(
        value,
        schema=context.input_schema(),
        config=context.config(),
    )
    captured = canonical_bytes(value)
    return ValidatedFixture(
        canonical_input_bytes=captured,
        input_sha256=sha256_bytes(captured),
        fixture_matrix_sha256=fixture_matrix_sha256(value),
    )


def usable_flags(observation: dict[str, Any]) -> set[str]:
    if observation["observation_status"] != "valid":
        return set()
    rating = observation["rating"]
    if not isinstance(rating, dict) or rating.get("cannot_judge") != []:
        return set()
    flags = rating.get("serious_error_flags")
    return set(flags) if isinstance(flags, list) else set()


def two_of_three_flags(observations: Sequence[dict[str, Any]]) -> set[str]:
    require(len(observations) == 3, "stability_observation_count_invalid")
    counts: Counter[str] = Counter()
    for observation in observations:
        counts.update(usable_flags(observation))
    return {flag for flag, count in counts.items() if count >= 2}


def _summary(hits: Sequence[bool]) -> dict[str, Any]:
    require(bool(hits), "all_roles_summary_empty")
    n = len(hits)
    tp = sum(bool(hit) for hit in hits)
    return {"tp": tp, "fn": n - tp, "n": n, "recall": tp / n}


def _percentile(values: Sequence[float], probability: float) -> float:
    require(bool(values), "bootstrap_percentile_empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def cluster_bootstrap_interval(
    items: Sequence[dict[str, Any]],
    *,
    hit_key: str,
    bootstrap: dict[str, Any],
) -> dict[str, Any]:
    require(bool(items), "bootstrap_items_empty")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["cluster_id"], []).append(item)
    clusters = sorted(grouped)
    minimum = bootstrap["minimum_independent_clusters"]
    common = {
        "cluster_count": len(clusters),
        "minimum_independent_clusters": minimum,
        "resamples": bootstrap["resamples"],
        "seed": bootstrap["seed"],
    }
    if len(clusters) < minimum:
        return {
            "estimable": False,
            "reason": "fewer_than_minimum_independent_clusters",
            "lower": None,
            "upper": None,
            **common,
        }
    observed_hits = {bool(item[hit_key]) for item in items}
    if len(observed_hits) == 1:
        return {
            "estimable": False,
            "reason": "degenerate_bootstrap_distribution",
            "lower": None,
            "upper": None,
            **common,
        }
    rng = random.Random(bootstrap["seed"])
    distribution: list[float] = []
    for _ in range(bootstrap["resamples"]):
        sampled: list[dict[str, Any]] = []
        for cluster in rng.choices(clusters, k=len(clusters)):
            sampled.extend(grouped[cluster])
        distribution.append(
            sum(bool(item[hit_key]) for item in sampled) / len(sampled)
        )
    if min(distribution) == max(distribution):
        return {
            "estimable": False,
            "reason": "degenerate_bootstrap_distribution",
            "lower": None,
            "upper": None,
            **common,
        }
    return {
        "estimable": True,
        "reason": None,
        "lower": _percentile(distribution, 0.025),
        "upper": _percentile(distribution, 0.975),
        **common,
    }


def aggregate_all_roles(
    fixture: ValidatedFixture,
    context: FrozenContext,
) -> dict[str, Any]:
    require(context == load_frozen_context(), "frozen_context_not_active")
    analysis_input = fixture.value()
    verified_fixture = validate_fixture(
        analysis_input,
        context,
    )
    require(fixture == verified_fixture, "validated_fixture_snapshot_invalid")
    config = context.config()
    item_results: list[dict[str, Any]] = []
    primary_hits: list[bool] = []
    stability_hits: list[bool] = []
    for item in analysis_input["items"]:
        required_flag = item["required_flag"]
        primary_flags_by_role: dict[str, set[str]] = {}
        stability_flags_by_role: dict[str, set[str]] = {}
        fixture_observation_hashes: dict[str, list[str]] = {}
        for role in ROLE_ORDER:
            observations = item["role_observations"][role]
            primary_flags_by_role[role] = usable_flags(observations[0])
            stability_flags_by_role[role] = two_of_three_flags(observations)
            fixture_observation_hashes[role] = [
                observation["fixture_observation_sha256"]
                for observation in observations
            ]
        primary_union = set().union(*primary_flags_by_role.values())
        stability_union = set().union(*stability_flags_by_role.values())
        primary_role_hits = {
            role: required_flag in primary_flags_by_role[role] for role in ROLE_ORDER
        }
        stability_role_hits = {
            role: required_flag in stability_flags_by_role[role] for role in ROLE_ORDER
        }
        primary_hit = required_flag in primary_union
        stability_hit = required_flag in stability_union
        primary_hits.append(primary_hit)
        stability_hits.append(stability_hit)
        item_results.append(
            {
                "item_id": item["item_id"],
                "cluster_id": item["cluster_id"],
                "error_family": item["error_family"],
                "required_flag": required_flag,
                "fixture_observation_hashes": fixture_observation_hashes,
                "primary_role_flags": {
                    role: sorted(primary_flags_by_role[role]) for role in ROLE_ORDER
                },
                "primary_role_hits": primary_role_hits,
                "primary_all_roles_flags": sorted(primary_union),
                "primary_all_roles_hit": primary_hit,
                "stability_role_flags": {
                    role: sorted(stability_flags_by_role[role]) for role in ROLE_ORDER
                },
                "stability_role_hits": stability_role_hits,
                "stability_all_roles_flags": sorted(stability_union),
                "stability_all_roles_hit": stability_hit,
            }
        )

    result = {
        "document_type": "rq2_qwen3_all_roles_result",
        "analysis_version": "rq2-qwen3-all-roles-analysis-v1",
        "study_id": analysis_input["study_id"],
        "lane": analysis_input["lane"],
        "reviewer_model": analysis_input["reviewer_model"],
        "role_order": list(ROLE_ORDER),
        "aggregation_rule": "union_across_roles",
        "primary_repetition": 1,
        "stability_rule": "two_of_three_within_role_then_union_across_roles",
        "input_sha256": fixture.input_sha256,
        "fixture_matrix_sha256": fixture.fixture_matrix_sha256,
        "external_study_references": analysis_input["external_study_references"],
        "external_references_verified": False,
        "item_count": len(item_results),
        "primary_summary": _summary(primary_hits),
        "stability_summary": _summary(stability_hits),
        "bootstrap": config["bootstrap"],
        "primary_interval": cluster_bootstrap_interval(
            item_results,
            hit_key="primary_all_roles_hit",
            bootstrap=config["bootstrap"],
        ),
        "stability_interval": cluster_bootstrap_interval(
            item_results,
            hit_key="stability_all_roles_hit",
            bootstrap=config["bootstrap"],
        ),
        "items": item_results,
        "descriptive_reference": True,
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }
    validate_all_roles_result(result, schema=context.result_schema())
    return result


def validate_all_roles_result(
    result: dict[str, Any],
    *,
    schema: dict[str, Any],
) -> None:
    try:
        jsonschema.Draft202012Validator(schema).validate(result)
    except jsonschema.ValidationError as exc:
        raise AllRolesError("all_roles_result_schema_invalid") from exc
    items = result["items"]
    require(result["item_count"] == len(items) and bool(items), "result_item_count_invalid")
    item_ids: set[str] = set()
    observation_hashes: set[str] = set()
    primary_hits: list[bool] = []
    stability_hits: list[bool] = []
    for item in items:
        require(item["item_id"] not in item_ids, "result_item_duplicate")
        item_ids.add(item["item_id"])
        require(
            item["required_flag"] == TARGET_TO_FLAG[item["error_family"]],
            "result_target_flag_mapping_drift",
        )
        for role in ROLE_ORDER:
            hashes = item["fixture_observation_hashes"][role]
            for observation_hash in hashes:
                require(
                    observation_hash not in observation_hashes,
                    "result_observation_hash_duplicate",
                )
                observation_hashes.add(observation_hash)
        require(
            all(
                item["primary_role_flags"][role]
                == sorted(item["primary_role_flags"][role])
                for role in ROLE_ORDER
            ),
            "result_primary_role_flags_not_canonical",
        )
        require(
            all(
                item["stability_role_flags"][role]
                == sorted(item["stability_role_flags"][role])
                for role in ROLE_ORDER
            ),
            "result_stability_role_flags_not_canonical",
        )
        primary_union = sorted(
            set().union(*(set(item["primary_role_flags"][role]) for role in ROLE_ORDER))
        )
        stability_union = sorted(
            set().union(*(set(item["stability_role_flags"][role]) for role in ROLE_ORDER))
        )
        require(
            item["primary_all_roles_flags"] == primary_union,
            "result_primary_flags_union_invalid",
        )
        require(
            item["stability_all_roles_flags"] == stability_union,
            "result_stability_flags_union_invalid",
        )
        require(
            all(
                item["primary_role_hits"][role]
                == (item["required_flag"] in item["primary_role_flags"][role])
                for role in ROLE_ORDER
            ),
            "result_primary_role_hits_invalid",
        )
        require(
            all(
                item["stability_role_hits"][role]
                == (item["required_flag"] in item["stability_role_flags"][role])
                for role in ROLE_ORDER
            ),
            "result_stability_role_hits_invalid",
        )
        primary_hit = item["required_flag"] in item["primary_all_roles_flags"]
        stability_hit = item["required_flag"] in item["stability_all_roles_flags"]
        require(
            item["primary_all_roles_hit"] == primary_hit
            and primary_hit == any(item["primary_role_hits"].values()),
            "result_primary_union_invalid",
        )
        require(
            item["stability_all_roles_hit"] == stability_hit
            and stability_hit == any(item["stability_role_hits"].values()),
            "result_stability_union_invalid",
        )
        primary_hits.append(primary_hit)
        stability_hits.append(stability_hit)
    require(result["primary_summary"] == _summary(primary_hits), "result_primary_summary_invalid")
    require(
        result["stability_summary"] == _summary(stability_hits),
        "result_stability_summary_invalid",
    )
    require(
        result["primary_interval"]
        == cluster_bootstrap_interval(
            items,
            hit_key="primary_all_roles_hit",
            bootstrap=result["bootstrap"],
        ),
        "result_primary_interval_invalid",
    )
    require(
        result["stability_interval"]
        == cluster_bootstrap_interval(
            items,
            hit_key="stability_all_roles_hit",
            bootstrap=result["bootstrap"],
        ),
        "result_stability_interval_invalid",
    )


def build_result_seal(
    fixture: ValidatedFixture,
    result: dict[str, Any],
    context: FrozenContext,
) -> dict[str, Any]:
    require(context == load_frozen_context(), "frozen_context_not_active")
    expected_result = aggregate_all_roles(fixture, context)
    require(
        canonical_bytes(result) == canonical_bytes(expected_result),
        "result_not_derived_from_bound_fixture",
    )
    validate_all_roles_result(result, schema=context.result_schema())
    seal = {
        "document_type": "rq2_qwen3_all_roles_result_seal",
        "seal_version": "rq2-qwen3-all-roles-result-seal-v1",
        "freeze_sha256": context.freeze_sha256,
        "input_sha256": fixture.input_sha256,
        "fixture_matrix_sha256": fixture.fixture_matrix_sha256,
        "result_sha256": sha256_bytes(canonical_bytes(expected_result)),
        "external_study_references": expected_result["external_study_references"],
        "external_references_verified": False,
        "internal_lane": result["lane"]["internal_lane"],
        "item_count": result["item_count"],
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }
    validate_result_seal(fixture, result, seal, context)
    return seal


def validate_result_seal(
    fixture: ValidatedFixture,
    result: dict[str, Any],
    seal: dict[str, Any],
    context: FrozenContext,
) -> None:
    require(context == load_frozen_context(), "frozen_context_not_active")
    expected_result = aggregate_all_roles(fixture, context)
    require(
        canonical_bytes(result) == canonical_bytes(expected_result),
        "result_not_derived_from_bound_fixture",
    )
    expected_seal = {
        "document_type": "rq2_qwen3_all_roles_result_seal",
        "seal_version": "rq2-qwen3-all-roles-result-seal-v1",
        "freeze_sha256": context.freeze_sha256,
        "input_sha256": fixture.input_sha256,
        "fixture_matrix_sha256": fixture.fixture_matrix_sha256,
        "result_sha256": sha256_bytes(canonical_bytes(expected_result)),
        "external_study_references": expected_result["external_study_references"],
        "external_references_verified": False,
        "internal_lane": expected_result["lane"]["internal_lane"],
        "item_count": expected_result["item_count"],
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }
    try:
        jsonschema.Draft202012Validator(context.result_seal_schema()).validate(seal)
    except jsonschema.ValidationError as exc:
        raise AllRolesError("all_roles_result_seal_schema_invalid") from exc
    require(canonical_bytes(seal) == canonical_bytes(expected_seal), "result_seal_invalid")


def preflight_service(config: dict[str, Any]) -> dict[str, Any]:
    try:
        result = runtime.preflight_service(config)
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc
    result["reviewer_role_count"] = len(ROLE_ORDER)
    result["fourth_all_roles_actor_created"] = False
    return result


def _post_source_free_role_canary(role: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Post only a frozen role's exact built-in source-free canary."""

    require(role in ROLE_ORDER, "canary_role_not_frozen")
    try:
        frozen_config = runtime.load_json(DEFAULT_CONFIG)
        frozen_assets = validate_freeze(frozen_config, config_path=DEFAULT_CONFIG)
        request = build_rating_request(
            frozen_config,
            frozen_assets,
            runtime.inert_canary_item(),
            role=role,
            repetition=1,
        )
        response = runtime.api_json(
            frozen_config,
            "/api/chat",
            payload=request,
            timeout=120,
        )
    except runtime.AllRolesRuntimeError as exc:
        raise AllRolesError(str(exc)) from exc
    return request, response


def run_source_free_canary(config: dict[str, Any], assets: dict[str, Any]) -> dict[str, Any]:
    baseline = preflight_service(config)
    results: list[dict[str, Any]] = []
    for role in ROLE_ORDER:
        try:
            request, response = _post_source_free_role_canary(role)
            rating, context = runtime.parse_rating_response(
                response,
                expected_model="qwen3:8b",
                rating_schema=assets["shared_rating_schema"],
                config=config,
            )
        except runtime.AllRolesRuntimeError as exc:
            raise AllRolesError(str(exc)) from exc
        results.append(
            {
                "role": role,
                "rating_schema_valid": True,
                "disposition": rating["disposition"],
                "prompt_eval_count": context["prompt_eval_count"],
                "eval_count": context["eval_count"],
                "request_sha256": sha256_bytes(canonical_bytes(request)),
                "response_sha256": sha256_bytes(canonical_bytes(response)),
            }
        )
    require(preflight_service(config) == baseline, "service_identity_changed_during_canary")
    return {
        "component": config["freeze_version"],
        "status": "passed",
        "roles": results,
        "fourth_all_roles_actor_created": False,
        "source_text_accessed": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    value.add_argument(
        "command",
        choices=("dry-run", "preflight-service", "source-free-test", "run"),
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        require(args.config == DEFAULT_CONFIG, "nondefault_freeze_rejected")
        try:
            config = runtime.load_json(DEFAULT_CONFIG)
        except runtime.AllRolesRuntimeError as exc:
            raise AllRolesError(str(exc)) from exc
        assets = validate_freeze(config, config_path=DEFAULT_CONFIG)
        if args.command == "dry-run":
            result = source_free_request_plan(config, assets)
        elif args.command == "preflight-service":
            result = preflight_service(config)
        elif args.command == "source-free-test":
            result = run_source_free_canary(config, assets)
        else:
            raise AllRolesError("source_bearing_execution_not_authorized")
        print(json.dumps(result, sort_keys=True))
        return 0
    except AllRolesError as exc:
        print(
            json.dumps(
                {
                    "component": "qwen3-all-roles-v1",
                    "status": "blocked",
                    "error": str(exc),
                    "source_text_accessed": False,
                    "outputs_written": False,
                    "manuscript_eligible": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
