#!/usr/bin/env python3
"""Profile-aware source-free All roles compatibility component.

Qwen3 is the default and primary profile. Llama and Gemma are closed sibling
profiles that reuse the same roles, prompts, scoring rule, seeds, and schemas.
Source-bearing execution is blocked for every profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "all_roles_profiles_v2_freeze.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import qwen3_all_roles_runtime as transport_runtime  # noqa: E402
import run_qwen3_all_roles as v1_core  # noqa: E402
from prompt_limit_guard import (  # noqa: E402
    PromptLimitError,
    harden_ollama_request,
    validate_successful_context_use,
)


ROLE_ORDER = ("researcher", "qualitative_methods", "domain")
REPETITIONS = (1, 2, 3)
PRIMARY_PROFILE_ID = "qwen3_8b"
EXPECTED_PROFILE_IDS = ("qwen3_8b", "llama3_1_8b", "gemma3_4b")
EXPECTED_ASSET_FILES = {
    "runner": "experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py",
    "legacy_qwen_v1_runner": "experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py",
    "transport_runtime": "experiments/rq2_role_prompted_llm/scripts/qwen3_all_roles_runtime.py",
    "prompt_limit_guard": "experiments/rq2_role_prompted_llm/scripts/prompt_limit_guard.py",
    "contract": "experiments/rq2_role_prompted_llm/protocol/all_roles_profiles_v2_contract.md",
    "model_profiles": "experiments/rq2_role_prompted_llm/config/all_roles_model_profiles_v1.json",
    "model_profiles_schema": "experiments/rq2_role_prompted_llm/schemas/all_roles_model_profiles_v1.schema.json",
    "shared_rater_guide": "experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md",
    "evaluator_item_schema": "experiments/direction_j_llm_as_rater/schemas/evaluator_item.schema.json",
    "shared_rating_transport_schema": "experiments/rq2_role_prompted_llm/schemas/shared_rating_transport_v1.schema.json",
    "shared_rating_schema": "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json",
    "all_roles_input_schema_v1": "experiments/rq2_role_prompted_llm/schemas/all_roles_input_v1.schema.json",
    "all_roles_result_schema_v1": "experiments/rq2_role_prompted_llm/schemas/all_roles_result_v1.schema.json",
    "all_roles_result_seal_schema_v1": "experiments/rq2_role_prompted_llm/schemas/all_roles_result_seal_v1.schema.json",
}
EXPECTED_PROMPT_FILES = {
    "researcher": "experiments/rq2_role_prompted_llm/prompts/researcher_v1.md",
    "qualitative_methods": "experiments/rq2_role_prompted_llm/prompts/methods_v1.md",
    "domain": "experiments/rq2_role_prompted_llm/prompts/domain_v1.md",
}
OUTPUT_CONSISTENCY_REMINDER = """OUTPUT CONSISTENCY CHECK (must hold):
List a construct in cannot_judge if and only if its score is null. Every
unlisted construct score must be an integer from 1 through 5. A nonempty
cannot_judge array requires disposition=\"escalate\" and requested_expertise
equal to \"qualitative_methods\", \"domain\", or \"both\". Every other
disposition requires requested_expertise=\"none\". Disposition=\"accept\"
requires all three scores to be 4 or 5, an empty cannot_judge array, and an
empty serious_error_flags array. Return only the schema object."""
_VERIFIED_MODEL_BLOBS: set[tuple[Any, ...]] = set()


class ProfileAllRolesError(RuntimeError):
    """Finite, source-free failure safe to expose to an operator."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ProfileAllRolesError(code)


def canonical_bytes(value: Any) -> bytes:
    return v1_core.canonical_bytes(value)


def sha256_bytes(value: bytes) -> str:
    return v1_core.sha256_bytes(value)


def _exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def _load_asset(entry: dict[str, Any], label: str) -> bytes:
    _exact_keys(entry, {"file", "sha256"}, f"{label}_asset")
    try:
        return transport_runtime.validate_hash(
            transport_runtime.workspace_path(entry["file"]),
            entry["sha256"],
            label,
        )
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc


def _strict_json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileAllRolesError(f"{label}_invalid_json") from exc
    require(isinstance(value, dict), f"{label}_root_not_object")
    return value


def validate_profile_registry(
    registry: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    try:
        jsonschema.Draft202012Validator(schema).validate(registry)
    except jsonschema.ValidationError as exc:
        raise ProfileAllRolesError("model_profile_registry_schema_invalid") from exc
    require(
        set(registry["profiles"]) == set(EXPECTED_PROFILE_IDS)
        and len(registry["profiles"]) == len(EXPECTED_PROFILE_IDS),
        "model_profile_registry_set_invalid",
    )
    require(
        registry["primary_profile_id"] == PRIMARY_PROFILE_ID,
        "primary_model_profile_drift",
    )
    model_ids: set[str] = set()
    manifest_hashes: set[str] = set()
    actor_ids: set[str] = set()
    primary_count = 0
    for key, profile in registry["profiles"].items():
        require(profile["profile_id"] == key, f"profile_id_key_mismatch:{key}")
        require(profile["model_id"] not in model_ids, "profile_model_id_duplicate")
        model_ids.add(profile["model_id"])
        require(
            profile["local_manifest_file_sha256"] not in manifest_hashes,
            "profile_manifest_hash_duplicate",
        )
        manifest_hashes.add(profile["local_manifest_file_sha256"])
        require(
            set(profile["role_actor_ids"]) == set(ROLE_ORDER)
            and len(profile["role_actor_ids"]) == len(ROLE_ORDER),
            f"profile_actor_role_set_invalid:{key}",
        )
        for actor_id in profile["role_actor_ids"].values():
            require(actor_id not in actor_ids, "profile_actor_id_duplicate")
            actor_ids.add(actor_id)
        if profile["profile_status"] == "primary_source_free_canary_passed":
            primary_count += 1
            require(key == PRIMARY_PROFILE_ID, "nonprimary_profile_marked_primary")
    require(primary_count == 1, "primary_model_profile_count_invalid")


def validate_component_freeze(config: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        config,
        {
            "document_type",
            "freeze_version",
            "status",
            "default_model_profile_id",
            "allowed_model_profile_ids",
            "source_bearing_execution_allowed",
            "real_results_allowed",
            "fallback_model_allowed",
            "manuscript_eligible",
            "service",
            "reviewer_runtime",
            "rating_repetitions",
            "primary_repetition",
            "repetition_seeds",
            "roles",
            "all_roles_rule",
            "bootstrap",
            "prompt_limit",
            "source_free_canary",
            "assets",
        },
        "component_freeze",
    )
    require(
        config["document_type"] == "warrantroute_all_roles_profile_component_freeze",
        "component_freeze_type_invalid",
    )
    require(config["freeze_version"] == "all-roles-profiles-v2", "freeze_version_invalid")
    require(config["status"] == "source_free_compatibility_only", "freeze_status_invalid")
    require(
        config["default_model_profile_id"] == PRIMARY_PROFILE_ID,
        "default_model_profile_drift",
    )
    require(
        tuple(config["allowed_model_profile_ids"]) == EXPECTED_PROFILE_IDS,
        "allowed_model_profile_set_invalid",
    )
    require(config["source_bearing_execution_allowed"] is False, "source_execution_enabled")
    require(config["real_results_allowed"] is False, "real_results_enabled")
    require(config["fallback_model_allowed"] is False, "fallback_model_enabled")
    require(config["manuscript_eligible"] is False, "manuscript_eligibility_enabled")
    require(config["service"] == {
        "url": "http://127.0.0.1:11434",
        "ollama_version": "0.18.0",
    }, "service_contract_invalid")
    try:
        transport_runtime.validate_numeric_loopback(config["service"]["url"])
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc
    require(config["reviewer_runtime"] == {
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 20,
        "repeat_penalty": 1,
        "num_ctx": 8192,
        "max_output_tokens": 512,
        "think": False,
        "stream": False,
        "tools_enabled": False,
        "automatic_retries": 0,
    }, "reviewer_runtime_invalid")
    require(config["rating_repetitions"] == 3, "rating_repetition_count_invalid")
    require(config["primary_repetition"] == 1, "primary_repetition_invalid")
    require(
        config["repetition_seeds"] == [2027082601, 2027082602, 2027082603]
        and len(set(config["repetition_seeds"])) == 3,
        "repetition_seeds_invalid",
    )
    require(
        set(config["roles"]) == set(ROLE_ORDER)
        and len(config["roles"]) == len(ROLE_ORDER),
        "role_set_invalid",
    )
    for role in ROLE_ORDER:
        _exact_keys(config["roles"][role], {"display_name", "prompt"}, f"role_{role}")
        require(
            config["roles"][role]["prompt"]["file"] == EXPECTED_PROMPT_FILES[role],
            f"role_prompt_path_drift:{role}",
        )
    require(config["all_roles_rule"] == {
        "roles": list(ROLE_ORDER),
        "primary_repetition": 1,
        "primary_operation": "per_item_or_of_role_target_flag_hits",
        "role_hit_rule": "valid_empty_cannot_judge_contains_required_flag",
        "stability_operation": "two_of_three_within_role_then_or_across_roles",
        "overlapping_role_hits_count_once": True,
        "failure_contributes_empty_flags": True,
        "missing_observation_must_be_explicit": True,
        "denominator": "eligible_items",
        "no_fourth_prompt_or_actor": True,
    }, "all_roles_rule_invalid")
    require(config["bootstrap"] == {
        "resamples": 10000,
        "seed": 20270826,
        "minimum_independent_clusters": 5,
        "interval": "percentile_95",
        "resampling_unit": "frozen_source_cluster",
        "too_few_or_degenerate_action": "ci_not_estimable",
    }, "bootstrap_contract_invalid")
    require(config["prompt_limit"] == {
        "truncate": False,
        "shift": False,
        "safety_margin_tokens": 256,
        "real_packet_chunking_allowed": False,
    }, "prompt_limit_contract_invalid")
    require(config["source_free_canary"] == {
        "enabled": True,
        "contains_source_text": False,
        "writes_outputs": False,
    }, "source_free_canary_invalid")

    assets_config = config["assets"]
    require(set(assets_config) == set(EXPECTED_ASSET_FILES), "asset_set_invalid")
    for label, expected in EXPECTED_ASSET_FILES.items():
        require(assets_config[label]["file"] == expected, f"{label}_path_drift")
    loaded = {
        label: _load_asset(entry, label)
        for label, entry in assets_config.items()
    }
    role_prompts = {
        role: _load_asset(config["roles"][role]["prompt"], f"{role}_prompt")
        for role in ROLE_ORDER
    }
    require(
        all(
            profile_name.encode("utf-8") not in prompt.lower()
            for prompt in role_prompts.values()
            for profile_name in ("qwen", "llama", "gemma")
        ),
        "model_name_leaked_into_role_prompt",
    )
    schemas: dict[str, Any] = {}
    for label in (
        "model_profiles_schema",
        "evaluator_item_schema",
        "shared_rating_transport_schema",
        "shared_rating_schema",
        "all_roles_input_schema_v1",
        "all_roles_result_schema_v1",
        "all_roles_result_seal_schema_v1",
    ):
        schemas[label] = _strict_json_object(loaded[label], label)
        try:
            jsonschema.Draft202012Validator.check_schema(schemas[label])
        except jsonschema.SchemaError as exc:
            raise ProfileAllRolesError(f"{label}_invalid") from exc
    registry = _strict_json_object(loaded["model_profiles"], "model_profiles")
    validate_profile_registry(registry, schemas["model_profiles_schema"])
    return {
        "registry": registry,
        "role_prompts": {
            role: value.decode("utf-8") for role, value in role_prompts.items()
        },
        "shared_rater_guide": loaded["shared_rater_guide"].decode("utf-8"),
        **schemas,
    }


@dataclass(frozen=True)
class ModelContext:
    raw_freeze_bytes: bytes
    freeze_sha256: str
    model_profile_id: str
    model_profile_bytes: bytes
    model_profile_sha256: str
    component_config_bytes: bytes
    asset_bundle_bytes: bytes

    def profile(self) -> dict[str, Any]:
        return json.loads(self.model_profile_bytes)

    def config(self) -> dict[str, Any]:
        return json.loads(self.component_config_bytes)

    def assets(self) -> dict[str, Any]:
        return json.loads(self.asset_bundle_bytes)


@dataclass(frozen=True)
class ValidatedProfileFixture:
    canonical_input_bytes: bytes
    input_sha256: str
    fixture_matrix_sha256: str
    model_profile_id: str
    model_profile_sha256: str

    def value(self) -> dict[str, Any]:
        return json.loads(self.canonical_input_bytes)


def _blob_path(manifest_path: Path, digest: str) -> Path:
    require(
        isinstance(digest, str)
        and digest.startswith("sha256:")
        and len(digest) == 71
        and all(character in "0123456789abcdef" for character in digest[7:]),
        "profile_blob_digest_invalid",
    )
    return manifest_path.parents[4] / "blobs" / digest.replace(":", "-")


def _verify_small_blob(path: Path, digest: str, label: str) -> bytes:
    try:
        return transport_runtime.validate_hash(path, digest[7:], label)
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc


def _verify_model_blob(path: Path, digest: str, label: str) -> None:
    """Stream and cache one content-addressed model blob verification."""

    require(path.resolve(strict=False) == path, f"{label}_path_resolution_drift")
    try:
        before = path.lstat()
    except OSError as exc:
        raise ProfileAllRolesError(f"{label}_unavailable") from exc
    require(stat.S_ISREG(before.st_mode), f"{label}_not_regular_file")
    expected = digest[7:]
    fingerprint = (
        str(path),
        expected,
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    if fingerprint in _VERIFIED_MODEL_BLOBS:
        return
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProfileAllRolesError(f"{label}_unavailable") from exc
    observed = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        require(
            (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
            f"{label}_identity_changed",
        )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            observed.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    require(
        (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        == (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ),
        f"{label}_changed_during_hash",
    )
    require(observed.hexdigest() == expected, f"{label}_hash_drift")
    _VERIFIED_MODEL_BLOBS.add(fingerprint)


def load_model_context(profile_id: str = PRIMARY_PROFILE_ID) -> ModelContext:
    require(profile_id in EXPECTED_PROFILE_IDS, "unknown_model_profile")
    try:
        raw = transport_runtime.read_regular_bytes(DEFAULT_CONFIG)
        config = json.loads(raw)
    except (transport_runtime.AllRolesRuntimeError, json.JSONDecodeError) as exc:
        raise ProfileAllRolesError("component_freeze_load_failed") from exc
    assets = validate_component_freeze(config)
    profile = assets["registry"]["profiles"][profile_id]
    try:
        manifest_bytes = transport_runtime.validate_hash(
            Path(profile["local_manifest_path"]),
            profile["local_manifest_file_sha256"],
            f"{profile_id}_manifest",
        )
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc
    manifest = _strict_json_object(manifest_bytes, f"{profile_id}_manifest")
    require(
        manifest.get("config", {}).get("digest") == profile["config_digest"],
        f"profile_config_digest_drift:{profile_id}",
    )
    expected_layers = {
        "application/vnd.ollama.image.model": profile["model_layer_digest"],
        "application/vnd.ollama.image.template": profile["template_layer_digest"],
        "application/vnd.ollama.image.license": profile["license_layer_digest"],
        "application/vnd.ollama.image.params": profile["params_layer_digest"],
    }
    observed_layers: dict[str, str] = {}
    for layer in manifest.get("layers", []):
        require(isinstance(layer, dict), f"profile_layer_invalid:{profile_id}")
        media_type = layer.get("mediaType")
        if media_type in expected_layers:
            require(media_type not in observed_layers, f"profile_layer_duplicate:{profile_id}")
            observed_layers[media_type] = layer.get("digest")
    require(observed_layers == expected_layers, f"profile_layer_digest_drift:{profile_id}")
    manifest_path = Path(profile["local_manifest_path"])
    _verify_small_blob(
        _blob_path(manifest_path, profile["config_digest"]),
        profile["config_digest"],
        f"{profile_id}_config_blob",
    )
    for layer_name in ("template", "license"):
        layer_digest = profile[f"{layer_name}_layer_digest"]
        _verify_small_blob(
            _blob_path(manifest_path, layer_digest),
            layer_digest,
            f"{profile_id}_{layer_name}_blob",
        )
    params_digest = profile["params_layer_digest"]
    params_bytes = _verify_small_blob(
        _blob_path(manifest_path, params_digest),
        params_digest,
        f"{profile_id}_params_blob",
    )
    params = _strict_json_object(params_bytes, f"{profile_id}_params")
    require(
        params == profile["inherited_manifest_parameters"],
        f"profile_inherited_parameters_drift:{profile_id}",
    )
    profile_bytes = canonical_bytes(profile)
    serializable_assets = {
        key: value
        for key, value in assets.items()
        if key != "registry"
    }
    return ModelContext(
        raw_freeze_bytes=raw,
        freeze_sha256=sha256_bytes(raw),
        model_profile_id=profile_id,
        model_profile_bytes=profile_bytes,
        model_profile_sha256=sha256_bytes(profile_bytes),
        component_config_bytes=canonical_bytes(config),
        asset_bundle_bytes=canonical_bytes(serializable_assets),
    )


def _require_active_context(context: ModelContext) -> None:
    require(
        context == load_model_context(context.model_profile_id),
        "model_context_not_active",
    )


def _profile_service_config(context: ModelContext) -> dict[str, Any]:
    profile = context.profile()
    config = context.config()
    return {
        "service": config["service"],
        "reviewer_actors": {
            role: {
                "actor_id": profile["role_actor_ids"][role],
                "model_id": profile["model_id"],
                "local_manifest_file_sha256": profile[
                    "local_manifest_file_sha256"
                ],
            }
            for role in ROLE_ORDER
        },
        "decoding": config["reviewer_runtime"],
        "prompt_limit": config["prompt_limit"],
    }


def _profile_schema(
    base: dict[str, Any],
    context: ModelContext,
    kind: str,
) -> dict[str, Any]:
    schema = json.loads(json.dumps(base))
    profile = context.profile()
    if kind == "input":
        schema["title"] = "Profile-aware source-free All roles fixture"
        schema["$id"] = (
            "https://warrantroute.local/schemas/rq2/"
            "all-roles-profile-input-v2/"
            f"{context.model_profile_id}/{context.freeze_sha256}.json"
        )
        schema["properties"]["input_schema_version"] = {
            "const": "rq2-all-roles-profile-input-v2"
        }
        schema["required"].append("model_profile_id")
        schema["properties"]["model_profile_id"] = {
            "const": context.model_profile_id
        }
        schema["properties"]["reviewer_model"]["properties"]["model_id"] = {
            "const": profile["model_id"]
        }
        schema["properties"]["reviewer_model"]["properties"][
            "model_snapshot_sha256"
        ] = {"const": profile["local_manifest_file_sha256"]}
        schema["$defs"]["observation"]["properties"]["model_id"] = {
            "const": profile["model_id"]
        }
        schema["$defs"]["observation"]["properties"][
            "model_snapshot_sha256"
        ] = {"const": profile["local_manifest_file_sha256"]}
    elif kind == "result":
        schema["title"] = "Profile-aware source-free All roles result"
        schema["$id"] = (
            "https://warrantroute.local/schemas/rq2/"
            "all-roles-profile-result-v2/"
            f"{context.model_profile_id}/{context.freeze_sha256}.json"
        )
        schema["properties"]["document_type"] = {
            "const": "rq2_all_roles_profile_result"
        }
        schema["properties"]["analysis_version"] = {
            "const": "rq2-all-roles-profile-analysis-v2"
        }
        schema["required"].extend([
            "component_freeze_sha256",
            "model_profile_id",
            "model_profile_sha256",
        ])
        schema["properties"]["component_freeze_sha256"] = {
            "const": context.freeze_sha256
        }
        schema["properties"]["model_profile_id"] = {
            "const": context.model_profile_id
        }
        schema["properties"]["model_profile_sha256"] = {
            "const": context.model_profile_sha256
        }
        schema["properties"]["reviewer_model"]["properties"]["model_id"] = {
            "const": profile["model_id"]
        }
        schema["properties"]["reviewer_model"]["properties"][
            "model_snapshot_sha256"
        ] = {"const": profile["local_manifest_file_sha256"]}
    elif kind == "seal":
        schema["title"] = "Profile-aware source-free All roles result seal"
        schema["$id"] = (
            "https://warrantroute.local/schemas/rq2/"
            "all-roles-profile-result-seal-v2/"
            f"{context.model_profile_id}/{context.freeze_sha256}.json"
        )
        schema["properties"]["document_type"] = {
            "const": "rq2_all_roles_profile_result_seal"
        }
        schema["properties"]["seal_version"] = {
            "const": "rq2-all-roles-profile-result-seal-v2"
        }
        schema["required"].extend(["model_profile_id", "model_profile_sha256"])
        schema["properties"]["model_profile_id"] = {
            "const": context.model_profile_id
        }
        schema["properties"]["model_profile_sha256"] = {
            "const": context.model_profile_sha256
        }
        schema["properties"]["freeze_sha256"] = {
            "const": context.freeze_sha256
        }
    else:
        raise ProfileAllRolesError("unknown_profile_schema_kind")
    return schema


def build_rating_request(
    context: ModelContext,
    item: dict[str, Any],
    *,
    role: str,
    repetition: int,
) -> dict[str, Any]:
    _require_active_context(context)
    require(role in ROLE_ORDER, "unknown_reviewer_role")
    require(repetition in REPETITIONS, "rating_repetition_invalid")
    profile = context.profile()
    config = context.config()
    assets = context.assets()
    try:
        transport_runtime.validate_evaluator_item(
            item,
            assets["evaluator_item_schema"],
        )
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc
    user_content = transport_runtime.reviewer_user_prompt(
        assets["shared_rater_guide"],
        item,
    )
    user_content += "\n\n" + OUTPUT_CONSISTENCY_REMINDER
    if profile["transport"]["message_packaging"] == "system_and_user_messages":
        messages = [
            {"role": "system", "content": assets["role_prompts"][role]},
            {"role": "user", "content": user_content},
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": (
                    "ROLE CONTRACT (authoritative):\n"
                    + assets["role_prompts"][role]
                    + "\n\nREVIEW INTERFACE:\n"
                    + user_content
                ),
            }
        ]
    decoding = config["reviewer_runtime"]
    request = {
        "model": profile["model_id"],
        "stream": decoding["stream"],
        "think": decoding["think"],
        "messages": messages,
        "format": assets[profile["transport"]["transport_schema_asset"]],
        "options": {
            "temperature": decoding["temperature"],
            "top_p": decoding["top_p"],
            "top_k": decoding["top_k"],
            "repeat_penalty": decoding["repeat_penalty"],
            "num_predict": decoding["max_output_tokens"],
            "seed": config["repetition_seeds"][repetition - 1],
        },
        "keep_alive": "5m",
    }
    require("tools" not in request, "tools_payload_rejected")
    return harden_ollama_request(request, num_ctx=decoding["num_ctx"])


def request_semantics(
    context: ModelContext,
    item: dict[str, Any],
    *,
    role: str,
    repetition: int,
) -> dict[str, Any]:
    request = build_rating_request(
        context,
        item,
        role=role,
        repetition=repetition,
    )
    assets = context.assets()
    return {
        "role": role,
        "repetition": repetition,
        "seed": request["options"]["seed"],
        "temperature": request["options"]["temperature"],
        "top_p": request["options"]["top_p"],
        "top_k": request["options"]["top_k"],
        "repeat_penalty": request["options"]["repeat_penalty"],
        "num_ctx": request["options"]["num_ctx"],
        "num_predict": request["options"]["num_predict"],
        "truncate": request["truncate"],
        "shift": request["shift"],
        "role_prompt_sha256": sha256_bytes(
            assets["role_prompts"][role].encode("utf-8")
        ),
        "guide_sha256": sha256_bytes(
            assets["shared_rater_guide"].encode("utf-8")
        ),
        "item_sha256": sha256_bytes(canonical_bytes(item)),
        "transport_schema_sha256": sha256_bytes(
            canonical_bytes(assets["shared_rating_transport_schema"])
        ),
        "postvalidation_schema_sha256": sha256_bytes(
            canonical_bytes(assets["shared_rating_schema"])
        ),
        "output_consistency_reminder_sha256": sha256_bytes(
            OUTPUT_CONSISTENCY_REMINDER.encode("utf-8")
        ),
    }


def source_free_request_plan(context: ModelContext) -> dict[str, Any]:
    _require_active_context(context)
    item = transport_runtime.inert_canary_item()
    profile = context.profile()
    rows = []
    for role in ROLE_ORDER:
        for repetition in REPETITIONS:
            request = build_rating_request(
                context,
                item,
                role=role,
                repetition=repetition,
            )
            rows.append({
                "role": role,
                "repetition": repetition,
                "request_sha256": sha256_bytes(canonical_bytes(request)),
                "request_semantics_sha256": sha256_bytes(
                    canonical_bytes(
                        request_semantics(
                            context,
                            item,
                            role=role,
                            repetition=repetition,
                        )
                    )
                ),
                "model_id": profile["model_id"],
            })
    return {
        "component": "all-roles-profiles-v2",
        "status": "passed",
        "component_freeze_sha256": context.freeze_sha256,
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "profile_status": profile["profile_status"],
        "request_count": len(rows),
        "reviewer_role_count": len(ROLE_ORDER),
        "fourth_all_roles_actor_created": False,
        "requests": rows,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def preflight_service(context: ModelContext) -> dict[str, Any]:
    _require_active_context(context)
    profile = context.profile()
    service_config = _profile_service_config(context)
    try:
        version = transport_runtime.api_json(service_config, "/api/version", timeout=20)
        require(
            version.get("version") == context.config()["service"]["ollama_version"],
            "ollama_version_drift",
        )
        tags = transport_runtime.api_json(service_config, "/api/tags", timeout=20)
    except transport_runtime.AllRolesRuntimeError as exc:
        raise ProfileAllRolesError(str(exc)) from exc
    models = tags.get("models")
    require(isinstance(models, list), "ollama_model_list_invalid")
    matches = [
        row
        for row in models
        if isinstance(row, dict) and row.get("name") == profile["model_id"]
    ]
    require(len(matches) == 1, "selected_model_not_uniquely_available")
    digest = str(matches[0].get("digest", "")).removeprefix("sha256:")
    require(digest == profile["local_manifest_file_sha256"], "selected_model_digest_drift")
    manifest_path = Path(profile["local_manifest_path"])
    _verify_model_blob(
        _blob_path(manifest_path, profile["model_layer_digest"]),
        profile["model_layer_digest"],
        f"{context.model_profile_id}_model_blob",
    )
    return {
        "status": "passed",
        "component_freeze_sha256": context.freeze_sha256,
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "model_id": profile["model_id"],
        "model_digest": digest,
        "endpoint": context.config()["service"]["url"],
        "ollama_version": version["version"],
        "source_text_accessed": False,
    }


def _reject_duplicate_key(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = child
    return value


def parse_rating_response(
    context: ModelContext,
    response: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    _require_active_context(context)
    profile = context.profile()
    assets = context.assets()
    try:
        if response.get("model") != profile["model_id"]:
            raise ValueError("model_identity_mismatch")
        if response.get("done") is not True or response.get("done_reason") != "stop":
            raise ValueError("response_not_clean_stop")
        message = response.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ValueError("response_message_invalid")
        if message.get("tool_calls") not in (None, []):
            raise ValueError("response_tool_calls_rejected")
        if message.get("thinking") not in (None, ""):
            raise ValueError("response_thinking_rejected")
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("response_content_missing")
        rating = json.loads(
            content,
            object_pairs_hook=_reject_duplicate_key,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("nonfinite_json_number")
            ),
        )
        if not isinstance(rating, dict):
            raise ValueError("rating_root_not_object")
        jsonschema.Draft202012Validator(assets["shared_rating_schema"]).validate(rating)
        context_use = validate_successful_context_use(
            response,
            num_ctx=context.config()["reviewer_runtime"]["num_ctx"],
            reserved_output_tokens=context.config()["reviewer_runtime"][
                "max_output_tokens"
            ],
            safety_margin_tokens=context.config()["prompt_limit"][
                "safety_margin_tokens"
            ],
        )
    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
        jsonschema.ValidationError,
        PromptLimitError,
    ) as exc:
        raise ProfileAllRolesError("rating_response_invalid") from exc
    return rating, context_use


def run_source_free_canary(context: ModelContext) -> dict[str, Any]:
    _require_active_context(context)
    baseline = preflight_service(context)
    profile = context.profile()
    service_config = _profile_service_config(context)
    results = []
    for role in ROLE_ORDER:
        require(preflight_service(context) == baseline, "service_identity_changed_before_role")
        request = build_rating_request(
            context,
            transport_runtime.inert_canary_item(),
            role=role,
            repetition=1,
        )
        try:
            response = transport_runtime.api_json(
                service_config,
                "/api/chat",
                payload=request,
                timeout=180,
            )
        except transport_runtime.AllRolesRuntimeError as exc:
            raise ProfileAllRolesError(str(exc)) from exc
        rating, context_use = parse_rating_response(context, response)
        require(preflight_service(context) == baseline, "service_identity_changed_after_role")
        results.append({
            "role": role,
            "model_id": profile["model_id"],
            "rating_schema_valid": True,
            "disposition": rating["disposition"],
            "prompt_eval_count": context_use["prompt_eval_count"],
            "eval_count": context_use["eval_count"],
            "request_sha256": sha256_bytes(canonical_bytes(request)),
            "response_sha256": sha256_bytes(canonical_bytes(response)),
        })
    return {
        "component": "all-roles-profiles-v2",
        "status": "passed",
        "component_freeze_sha256": context.freeze_sha256,
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "roles": results,
        "fallback_used": False,
        "fourth_all_roles_actor_created": False,
        "source_text_accessed": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def _fixture_observation_hash(
    context: ModelContext,
    item_id: str,
    role: str,
    observation: dict[str, Any],
) -> str:
    payload = {
        key: value
        for key, value in observation.items()
        if key != "fixture_observation_sha256"
    }
    return sha256_bytes(canonical_bytes({
        "hash_domain": "warrantroute:all-roles:profile-fixture-observation:v2",
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "item_id": item_id,
        "prompted_role": role,
        "observation": payload,
    }))


def seal_fixture_observations(
    context: ModelContext,
    value: dict[str, Any],
) -> dict[str, Any]:
    _require_active_context(context)
    copied = json.loads(json.dumps(value, ensure_ascii=False))
    try:
        for item in copied["items"]:
            for role in ROLE_ORDER:
                for observation in item["role_observations"][role]:
                    observation["fixture_observation_sha256"] = (
                        _fixture_observation_hash(
                            context,
                            item["item_id"],
                            role,
                            observation,
                        )
                    )
    except (KeyError, TypeError) as exc:
        raise ProfileAllRolesError("fixture_observation_sealing_invalid") from exc
    return copied


def _fixture_matrix_hash(context: ModelContext, value: dict[str, Any]) -> str:
    items = []
    for item in value["items"]:
        observations = []
        for role in ROLE_ORDER:
            for observation in item["role_observations"][role]:
                observations.append({
                    "prompted_role": role,
                    "rating_repetition": observation["rating_repetition"],
                    "fixture_observation_sha256": observation[
                        "fixture_observation_sha256"
                    ],
                })
        items.append({
            "item_id": item["item_id"],
            "cluster_id": item["cluster_id"],
            "error_family": item["error_family"],
            "required_flag": item["required_flag"],
            "evaluator_item_sha256": item["evaluator_item_sha256"],
            "observations": observations,
        })
    return sha256_bytes(canonical_bytes({
        "hash_domain": "warrantroute:all-roles:profile-fixture-matrix:v2",
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "reviewer_model": value["reviewer_model"],
        "items": items,
    }))


def validate_fixture(
    context: ModelContext,
    value: dict[str, Any],
) -> ValidatedProfileFixture:
    _require_active_context(context)
    profile = context.profile()
    assets = context.assets()
    schema = _profile_schema(
        assets["all_roles_input_schema_v1"],
        context,
        "input",
    )
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise ProfileAllRolesError("profile_fixture_schema_invalid") from exc
    require(value["model_profile_id"] == context.model_profile_id, "fixture_profile_drift")
    require(value["reviewer_model"] == {
        "model_id": profile["model_id"],
        "model_snapshot_sha256": profile["local_manifest_file_sha256"],
    }, "fixture_reviewer_model_drift")
    item_ids: set[str] = set()
    evaluator_hashes: set[str] = set()
    observation_hashes: set[str] = set()
    for item in value["items"]:
        require(item["item_id"] not in item_ids, "fixture_item_duplicate")
        item_ids.add(item["item_id"])
        require(
            item["evaluator_item_sha256"] not in evaluator_hashes,
            "fixture_evaluator_item_duplicate",
        )
        evaluator_hashes.add(item["evaluator_item_sha256"])
        require(
            item["required_flag"] == v1_core.TARGET_TO_FLAG[item["error_family"]],
            "fixture_target_flag_mapping_drift",
        )
        for role in ROLE_ORDER:
            observations = item["role_observations"][role]
            require(
                tuple(row["rating_repetition"] for row in observations)
                == REPETITIONS,
                f"fixture_repetition_order_invalid:{role}",
            )
            for observation in observations:
                require(
                    observation["actor_id"] == profile["role_actor_ids"][role],
                    f"fixture_actor_drift:{role}",
                )
                require(observation["model_id"] == profile["model_id"], f"fixture_model_drift:{role}")
                require(
                    observation["model_snapshot_sha256"]
                    == profile["local_manifest_file_sha256"],
                    f"fixture_snapshot_drift:{role}",
                )
                require(
                    observation["role_prompt_sha256"]
                    == context.config()["roles"][role]["prompt"]["sha256"],
                    f"fixture_prompt_drift:{role}",
                )
                require(
                    observation["evaluator_item_sha256"]
                    == item["evaluator_item_sha256"],
                    f"fixture_item_hash_drift:{role}",
                )
                observed_hash = observation["fixture_observation_sha256"]
                require(observed_hash not in observation_hashes, "fixture_observation_duplicate")
                observation_hashes.add(observed_hash)
                require(
                    observed_hash
                    == _fixture_observation_hash(
                        context,
                        item["item_id"],
                        role,
                        observation,
                    ),
                    "fixture_observation_hash_mismatch",
                )
    captured = canonical_bytes(value)
    return ValidatedProfileFixture(
        canonical_input_bytes=captured,
        input_sha256=sha256_bytes(captured),
        fixture_matrix_sha256=_fixture_matrix_hash(context, value),
        model_profile_id=context.model_profile_id,
        model_profile_sha256=context.model_profile_sha256,
    )


def aggregate_all_roles(
    context: ModelContext,
    fixture: ValidatedProfileFixture,
) -> dict[str, Any]:
    _require_active_context(context)
    require(
        fixture.model_profile_id == context.model_profile_id
        and fixture.model_profile_sha256 == context.model_profile_sha256,
        "fixture_context_profile_mismatch",
    )
    value = fixture.value()
    require(validate_fixture(context, value) == fixture, "fixture_snapshot_invalid")
    config = context.config()
    item_results = []
    primary_hits = []
    stability_hits = []
    for item in value["items"]:
        target = item["required_flag"]
        primary_by_role = {}
        stability_by_role = {}
        hashes = {}
        for role in ROLE_ORDER:
            observations = item["role_observations"][role]
            primary_by_role[role] = v1_core.usable_flags(observations[0])
            stability_by_role[role] = v1_core.two_of_three_flags(observations)
            hashes[role] = [
                row["fixture_observation_sha256"] for row in observations
            ]
        primary_union = set().union(*primary_by_role.values())
        stability_union = set().union(*stability_by_role.values())
        primary_role_hits = {
            role: target in primary_by_role[role] for role in ROLE_ORDER
        }
        stability_role_hits = {
            role: target in stability_by_role[role] for role in ROLE_ORDER
        }
        primary_hit = target in primary_union
        stability_hit = target in stability_union
        primary_hits.append(primary_hit)
        stability_hits.append(stability_hit)
        item_results.append({
            "item_id": item["item_id"],
            "cluster_id": item["cluster_id"],
            "error_family": item["error_family"],
            "required_flag": target,
            "fixture_observation_hashes": hashes,
            "primary_role_flags": {
                role: sorted(primary_by_role[role]) for role in ROLE_ORDER
            },
            "primary_role_hits": primary_role_hits,
            "primary_all_roles_flags": sorted(primary_union),
            "primary_all_roles_hit": primary_hit,
            "stability_role_flags": {
                role: sorted(stability_by_role[role]) for role in ROLE_ORDER
            },
            "stability_role_hits": stability_role_hits,
            "stability_all_roles_flags": sorted(stability_union),
            "stability_all_roles_hit": stability_hit,
        })
    result = {
        "document_type": "rq2_all_roles_profile_result",
        "analysis_version": "rq2-all-roles-profile-analysis-v2",
        "component_freeze_sha256": context.freeze_sha256,
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "study_id": value["study_id"],
        "lane": value["lane"],
        "reviewer_model": value["reviewer_model"],
        "role_order": list(ROLE_ORDER),
        "aggregation_rule": "union_across_roles",
        "primary_repetition": 1,
        "stability_rule": "two_of_three_within_role_then_union_across_roles",
        "input_sha256": fixture.input_sha256,
        "fixture_matrix_sha256": fixture.fixture_matrix_sha256,
        "external_study_references": value["external_study_references"],
        "external_references_verified": False,
        "item_count": len(item_results),
        "primary_summary": v1_core._summary(primary_hits),
        "stability_summary": v1_core._summary(stability_hits),
        "bootstrap": config["bootstrap"],
        "primary_interval": v1_core.cluster_bootstrap_interval(
            item_results,
            hit_key="primary_all_roles_hit",
            bootstrap=config["bootstrap"],
        ),
        "stability_interval": v1_core.cluster_bootstrap_interval(
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
    result_schema = _profile_schema(
        context.assets()["all_roles_result_schema_v1"],
        context,
        "result",
    )
    v1_core.validate_all_roles_result(result, schema=result_schema)
    return result


def _expected_result_seal(
    context: ModelContext,
    fixture: ValidatedProfileFixture,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "document_type": "rq2_all_roles_profile_result_seal",
        "seal_version": "rq2-all-roles-profile-result-seal-v2",
        "freeze_sha256": context.freeze_sha256,
        "model_profile_id": context.model_profile_id,
        "model_profile_sha256": context.model_profile_sha256,
        "input_sha256": fixture.input_sha256,
        "fixture_matrix_sha256": fixture.fixture_matrix_sha256,
        "result_sha256": sha256_bytes(canonical_bytes(result)),
        "external_study_references": result["external_study_references"],
        "external_references_verified": False,
        "internal_lane": result["lane"]["internal_lane"],
        "item_count": result["item_count"],
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }


def build_result_seal(
    context: ModelContext,
    fixture: ValidatedProfileFixture,
    result: dict[str, Any],
) -> dict[str, Any]:
    _require_active_context(context)
    expected_result = aggregate_all_roles(context, fixture)
    require(
        canonical_bytes(result) == canonical_bytes(expected_result),
        "result_not_derived_from_profile_fixture",
    )
    seal = _expected_result_seal(context, fixture, expected_result)
    schema = _profile_schema(
        context.assets()["all_roles_result_seal_schema_v1"],
        context,
        "seal",
    )
    try:
        jsonschema.Draft202012Validator(schema).validate(seal)
    except jsonschema.ValidationError as exc:
        raise ProfileAllRolesError("profile_result_seal_schema_invalid") from exc
    return seal


def validate_result_seal(
    context: ModelContext,
    fixture: ValidatedProfileFixture,
    result: dict[str, Any],
    seal: dict[str, Any],
) -> None:
    expected_result = aggregate_all_roles(context, fixture)
    require(
        canonical_bytes(result) == canonical_bytes(expected_result),
        "result_not_derived_from_profile_fixture",
    )
    require(
        canonical_bytes(seal)
        == canonical_bytes(_expected_result_seal(context, fixture, expected_result)),
        "profile_result_seal_invalid",
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--model-profile",
        default=PRIMARY_PROFILE_ID,
        choices=EXPECTED_PROFILE_IDS,
    )
    value.add_argument(
        "command",
        choices=("dry-run", "preflight-service", "source-free-test", "run"),
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        context = load_model_context(args.model_profile)
        if args.command == "dry-run":
            result = source_free_request_plan(context)
        elif args.command == "preflight-service":
            result = preflight_service(context)
        elif args.command == "source-free-test":
            result = run_source_free_canary(context)
        else:
            raise ProfileAllRolesError("source_bearing_execution_not_authorized")
        print(json.dumps(result, sort_keys=True))
        return 0
    except ProfileAllRolesError as exc:
        print(json.dumps({
            "component": "all-roles-profiles-v2",
            "status": "blocked",
            "error": str(exc),
            "fallback_used": False,
            "source_text_accessed": False,
            "outputs_written": False,
            "manuscript_eligible": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
