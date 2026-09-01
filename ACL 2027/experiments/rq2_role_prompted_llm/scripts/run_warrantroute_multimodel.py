#!/usr/bin/env python3
"""Source-free model-neutral reviewer adapter for WarrantRoute."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "warrantroute_multimodel_adapter_freeze.json"
MODEL_MANIFEST_ROOT = Path(
    "/Users/OODI/.ollama/models/manifests/registry.ollama.ai/library"
)

ROLE_ORDER = ("researcher", "qualitative_methods", "domain")
ROUTE_ORDER = ("none", "qualitative_methods", "domain", "both")
ROUTE_TO_ROLES = {
    "none": ("researcher",),
    "qualitative_methods": ("qualitative_methods",),
    "domain": ("domain",),
    "both": ("qualitative_methods", "domain"),
}
FLAG_ORDER = (
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
    "inconsistent_codebook",
    "other",
)
PROFILE_ORDER = ("qwen3_8b", "llama3_1_8b", "gemma3_4b")
EXPECTED_PROMPT_FILES = {
    "researcher": "experiments/rq2_role_prompted_llm/prompts/researcher_v1.md",
    "qualitative_methods": "experiments/rq2_role_prompted_llm/prompts/methods_v1.md",
    "domain": "experiments/rq2_role_prompted_llm/prompts/domain_v1.md",
}
EXPECTED_ASSET_FILES = {
    "runner": "experiments/rq2_role_prompted_llm/scripts/run_warrantroute_multimodel.py",
    "contract": "experiments/rq2_role_prompted_llm/protocol/warrantroute_multimodel_adapter_contract_v1.md",
    "reviewer_profile_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_reviewer_profile_v1.schema.json",
    "reviewer_matrix_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_reviewer_matrix_v1.schema.json",
    "result_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_model_neutral_result_v1.schema.json",
}


class MultimodelAdapterError(RuntimeError):
    """Finite content-free adapter failure."""


@dataclass(frozen=True)
class ValidatedAdapter:
    """Immutable source-free binding returned only after freeze validation."""

    freeze_version: str
    adapter_freeze_sha256: str
    primary_profile_id: str
    profile_order: tuple[str, ...]
    profile_id: str
    profile_sha256: str
    profile_json: str
    matrix_schema_sha256: str
    matrix_schema_json: str
    result_schema_sha256: str
    result_schema_json: str

    def profile(self) -> dict[str, Any]:
        return json.loads(self.profile_json)

    def matrix_schema(self) -> dict[str, Any]:
        return json.loads(self.matrix_schema_json)

    def result_schema(self) -> dict[str, Any]:
        return json.loads(self.result_schema_json)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise MultimodelAdapterError(code)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _finite_numbers(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_finite_numbers(child) for child in value)
    if isinstance(value, dict):
        return all(_finite_numbers(child) for child in value.values())
    return False


def _exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def _schema_validate(value: Any, schema: dict[str, Any], code: str) -> None:
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise MultimodelAdapterError(code) from exc
    require(_finite_numbers(value), f"{code}_nonfinite")


def read_regular_bytes(path: Path) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise MultimodelAdapterError("required_file_unavailable") from exc
    require(not stat.S_ISLNK(before.st_mode), "symlink_rejected")
    require(stat.S_ISREG(before.st_mode), "nonregular_file_rejected")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MultimodelAdapterError("required_file_unavailable") from exc
    try:
        after = os.fstat(descriptor)
        require(stat.S_ISREG(after.st_mode), "nonregular_file_rejected")
        require(
            (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
            "file_identity_changed",
        )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def workspace_path(relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "workspace_path_invalid")
    candidate = Path(relative)
    require(not candidate.is_absolute(), "workspace_path_not_relative")
    resolved = (WORKSPACE / candidate).resolve()
    try:
        resolved.relative_to(WORKSPACE)
    except ValueError as exc:
        raise MultimodelAdapterError("workspace_path_escape") from exc
    return resolved


def validate_hash(path: Path, expected: str, label: str) -> bytes:
    require(
        isinstance(expected, str)
        and len(expected) == 64
        and all(character in "0123456789abcdef" for character in expected),
        f"{label}_hash_invalid",
    )
    data = read_regular_bytes(path)
    require(sha256_bytes(data) == expected, f"{label}_hash_drift")
    return data


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_regular_bytes(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MultimodelAdapterError("config_invalid_json") from exc
    require(isinstance(value, dict), "config_root_not_object")
    return value


def _load_asset(entry: dict[str, Any], label: str) -> bytes:
    _exact_keys(entry, {"file", "sha256"}, f"{label}_asset")
    require(entry["file"] == EXPECTED_ASSET_FILES[label], f"{label}_path_drift")
    return validate_hash(workspace_path(entry["file"]), entry["sha256"], label)


def select_reviewer_profile(config: dict[str, Any], profile_id: Any) -> dict[str, Any]:
    require(isinstance(profile_id, str) and bool(profile_id), "reviewer_profile_id_invalid")
    profiles = config.get("reviewer_profiles", {})
    require(profile_id in profiles, "unknown_reviewer_profile")
    profile = profiles[profile_id]
    require(profile.get("profile_id") == profile_id, "reviewer_profile_key_drift")
    return profile


def validate_freeze(
    config: dict[str, Any],
    *,
    config_path: Path = DEFAULT_CONFIG,
    selected_profile_id: str | None = None,
) -> dict[str, Any]:
    require(config_path.resolve() == DEFAULT_CONFIG.resolve(), "nondefault_freeze_rejected")
    _exact_keys(
        config,
        {
            "document_type",
            "freeze_version",
            "status",
            "primary_reviewer_profile_id",
            "profile_order",
            "source_bearing_execution_allowed",
            "heldout_access_allowed",
            "router_training_allowed",
            "routing_policy_bound",
            "manuscript_eligible",
            "role_prompt_contract",
            "reviewer_profiles",
            "assets",
        },
        "freeze",
    )
    require(
        config["document_type"] == "warrantroute_multimodel_adapter_freeze",
        "freeze_type_invalid",
    )
    require(config["freeze_version"] == "warrantroute-multimodel-adapter-v1", "freeze_version_invalid")
    require(config["status"] == "source_free_adapter_only", "freeze_status_invalid")
    require(config["primary_reviewer_profile_id"] == "qwen3_8b", "primary_profile_drift")
    require(tuple(config["profile_order"]) == PROFILE_ORDER, "profile_order_invalid")
    require(config["source_bearing_execution_allowed"] is False, "source_execution_enabled")
    require(config["heldout_access_allowed"] is False, "heldout_access_enabled")
    require(config["router_training_allowed"] is False, "router_training_enabled")
    require(config["routing_policy_bound"] is False, "unexpected_routing_policy")
    require(config["manuscript_eligible"] is False, "manuscript_eligibility_enabled")

    assets = config["assets"]
    require(set(assets) == set(EXPECTED_ASSET_FILES), "asset_set_invalid")
    loaded = {label: _load_asset(assets[label], label) for label in EXPECTED_ASSET_FILES}
    schemas: dict[str, Any] = {}
    for label in ("reviewer_profile_schema", "reviewer_matrix_schema", "result_schema"):
        try:
            schema = json.loads(loaded[label])
            jsonschema.Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
            raise MultimodelAdapterError(f"{label}_invalid") from exc
        schemas[label] = schema

    prompt_contract = config["role_prompt_contract"]
    _exact_keys(prompt_contract, set(ROLE_ORDER), "role_prompt_contract")
    for role in ROLE_ORDER:
        entry = prompt_contract[role]
        _exact_keys(entry, {"file", "sha256"}, f"role_prompt:{role}")
        require(entry["file"] == EXPECTED_PROMPT_FILES[role], f"role_prompt_path_drift:{role}")
        validate_hash(workspace_path(entry["file"]), entry["sha256"], f"role_prompt:{role}")

    profiles = config["reviewer_profiles"]
    require(tuple(profiles) == PROFILE_ORDER, "reviewer_profile_registry_order_invalid")
    all_actor_ids: set[str] = set()
    all_model_ids: set[str] = set()
    for profile_id in PROFILE_ORDER:
        profile = select_reviewer_profile(config, profile_id)
        _schema_validate(profile, schemas["reviewer_profile_schema"], "reviewer_profile_schema_invalid")
        require(tuple(profile["actor_ids"]) == ROLE_ORDER, f"reviewer_actor_order_invalid:{profile_id}")
        actors = tuple(profile["actor_ids"].values())
        require(len(set(actors)) == len(actors), f"reviewer_actor_duplicate:{profile_id}")
        require(not (set(actors) & all_actor_ids), "reviewer_actor_cross_profile_duplicate")
        all_actor_ids.update(actors)
        require(profile["model_id"] not in all_model_ids, "reviewer_model_duplicate")
        all_model_ids.add(profile["model_id"])
        manifest_path = Path(profile["model_manifest_path"])
        require(manifest_path.is_absolute(), f"reviewer_manifest_not_absolute:{profile_id}")
        try:
            model_name, model_tag = profile["model_id"].rsplit(":", 1)
        except ValueError as exc:
            raise MultimodelAdapterError(f"reviewer_model_id_invalid:{profile_id}") from exc
        require(bool(model_name) and bool(model_tag), f"reviewer_model_id_invalid:{profile_id}")
        model_name_path = Path(model_name)
        require(
            not model_name_path.is_absolute()
            and all(part not in {"", ".", ".."} for part in model_name_path.parts)
            and "/" not in model_tag,
            f"reviewer_model_id_invalid:{profile_id}",
        )
        expected_manifest = MODEL_MANIFEST_ROOT / model_name / model_tag
        require(manifest_path == expected_manifest, f"reviewer_manifest_path_drift:{profile_id}")
        require(
            profile["role_prompt_contract"] == "shared_role_prompts_v1",
            f"reviewer_prompt_contract_drift:{profile_id}",
        )
        require(profile["source_bearing_execution_allowed"] is False, f"profile_source_enabled:{profile_id}")
        require(profile["manuscript_eligible"] is False, f"profile_manuscript_enabled:{profile_id}")

    qwen = profiles["qwen3_8b"]
    require(qwen["status"] == "primary_source_free_interface", "qwen_profile_status_invalid")
    require(qwen["reviewer_canary_status"] == "passed_source_free_interface", "qwen_canary_status_invalid")
    for profile_id in ("llama3_1_8b", "gemma3_4b"):
        profile = profiles[profile_id]
        require(profile["status"] == "adapter_template_unbound", f"template_status_invalid:{profile_id}")
        require(profile["reviewer_canary_status"] == "required_before_activation", f"template_canary_invalid:{profile_id}")
    require(profiles["gemma3_4b"]["minimum_num_ctx"] >= 16384, "gemma_context_guard_too_small")
    chosen_profile_id = selected_profile_id or config["primary_reviewer_profile_id"]
    chosen_profile = select_reviewer_profile(config, chosen_profile_id)
    validate_hash(
        Path(chosen_profile["model_manifest_path"]),
        chosen_profile["model_manifest_sha256"],
        f"reviewer_manifest:{chosen_profile_id}",
    )
    return schemas


def load_validated_adapter(
    config_path: Path, reviewer_profile_id: str
) -> ValidatedAdapter:
    resolved = config_path.resolve()
    require(resolved == DEFAULT_CONFIG.resolve(), "nondefault_freeze_rejected")
    raw_config = read_regular_bytes(resolved)
    try:
        config = json.loads(raw_config.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MultimodelAdapterError("config_invalid_json") from exc
    require(isinstance(config, dict), "config_root_not_object")
    schemas = validate_freeze(
        config,
        config_path=resolved,
        selected_profile_id=reviewer_profile_id,
    )
    profile = select_reviewer_profile(config, reviewer_profile_id)
    return ValidatedAdapter(
        freeze_version=config["freeze_version"],
        adapter_freeze_sha256=sha256_bytes(raw_config),
        primary_profile_id=config["primary_reviewer_profile_id"],
        profile_order=tuple(config["profile_order"]),
        profile_id=reviewer_profile_id,
        profile_sha256=sha256_bytes(canonical_bytes(profile)),
        profile_json=canonical_bytes(profile).decode("utf-8"),
        matrix_schema_sha256=config["assets"]["reviewer_matrix_schema"]["sha256"],
        matrix_schema_json=canonical_bytes(schemas["reviewer_matrix_schema"]).decode("utf-8"),
        result_schema_sha256=config["assets"]["result_schema"]["sha256"],
        result_schema_json=canonical_bytes(schemas["result_schema"]).decode("utf-8"),
    )


def verify_adapter_binding(adapter: ValidatedAdapter) -> dict[str, Any]:
    """Rebind a fixture adapter to the exact current freeze and profile bytes."""
    require(isinstance(adapter, ValidatedAdapter), "validated_adapter_required")
    fresh = load_validated_adapter(DEFAULT_CONFIG, adapter.profile_id)
    require(adapter == fresh, "validated_adapter_drift")
    return fresh.profile()


def validate_reviewer_matrix(
    value: dict[str, Any],
    *,
    adapter: ValidatedAdapter,
) -> dict[str, Any]:
    profile = verify_adapter_binding(adapter)
    matrix_schema = adapter.matrix_schema()
    _schema_validate(value, matrix_schema, "reviewer_matrix_schema_invalid")
    require(value["reviewer_profile_id"] == adapter.profile_id, "matrix_profile_drift")
    require(
        value["adapter_freeze_sha256"] == adapter.adapter_freeze_sha256,
        "matrix_adapter_freeze_drift",
    )
    require(
        value["reviewer_profile_sha256"] == adapter.profile_sha256,
        "matrix_profile_hash_drift",
    )
    reviewer_model = value["reviewer_model"]
    require(reviewer_model["model_id"] == profile["model_id"], "matrix_model_drift")
    require(
        reviewer_model["model_snapshot_sha256"] == profile["model_manifest_sha256"],
        "matrix_snapshot_drift",
    )
    observed_hashes: set[str] = set()
    for role in ROLE_ORDER:
        observations = value["role_observations"][role]
        require(
            {row["rating_repetition"] for row in observations} == {1, 2, 3},
            f"matrix_repetition_grid_invalid:{role}",
        )
        for observation in observations:
            require(observation["actor_id"] == profile["actor_ids"][role], f"matrix_actor_drift:{role}")
            require(observation["prompted_role"] == role, f"matrix_role_drift:{role}")
            require(observation["model_id"] == profile["model_id"], f"matrix_model_drift:{role}")
            require(
                observation["model_snapshot_sha256"] == profile["model_manifest_sha256"],
                f"matrix_snapshot_drift:{role}",
            )
            require(observation["item_id"] == value["item_id"], f"matrix_item_drift:{role}")
            require(
                observation["evaluator_item_sha256"] == value["evaluator_item_sha256"],
                f"matrix_evaluator_hash_drift:{role}",
            )
            observation_hash = observation["observation_sha256"]
            require(observation_hash not in observed_hashes, "matrix_observation_duplicate")
            observed_hashes.add(observation_hash)
    return profile


def _usable_flags(observation: dict[str, Any]) -> tuple[set[str], bool]:
    if observation["observation_status"] != "valid":
        return set(), False
    rating = observation["rating"]
    if not isinstance(rating, dict) or rating.get("cannot_judge") != []:
        return set(), False
    return set(rating["serious_error_flags"]), True


def _role_flags(
    observations: list[dict[str, Any]], aggregation: str
) -> tuple[set[str], bool, list[str]]:
    by_repetition = {row["rating_repetition"]: row for row in observations}
    if aggregation == "repetition_1":
        observation = by_repetition[1]
        flags, usable = _usable_flags(observation)
        return flags, usable, [observation["observation_sha256"]]
    require(aggregation == "two_of_three", "aggregation_invalid")
    counts: Counter[str] = Counter()
    usable_count = 0
    hashes: list[str] = []
    for repetition in (1, 2, 3):
        observation = by_repetition[repetition]
        hashes.append(observation["observation_sha256"])
        flags, usable = _usable_flags(observation)
        if usable:
            usable_count += 1
            counts.update(flags)
    return {flag for flag, count in counts.items() if count >= 2}, usable_count >= 2, hashes


def combine_route_flags(route: str, role_flags: dict[str, set[str]]) -> set[str]:
    require(route in ROUTE_TO_ROLES, "route_invalid")
    selected: set[str] = set()
    for role in ROUTE_TO_ROLES[route]:
        selected.update(role_flags[role])
    return selected


def reduce_reviewer_matrix_contract_fixture(
    value: dict[str, Any],
    *,
    route: str,
    aggregation: str,
    adapter: ValidatedAdapter,
) -> dict[str, Any]:
    """Reduce a source-free fixture. This function never authenticates evidence."""
    profile = validate_reviewer_matrix(value, adapter=adapter)
    require(route in ROUTE_TO_ROLES, "route_invalid")
    require(aggregation in {"repetition_1", "two_of_three"}, "aggregation_invalid")
    selected_roles = list(ROUTE_TO_ROLES[route])
    role_flags: dict[str, set[str]] = {}
    selected_hashes: list[str] = []
    failures: list[str] = []
    for role in selected_roles:
        flags, usable, hashes = _role_flags(value["role_observations"][role], aggregation)
        role_flags[role] = flags
        selected_hashes.extend(hashes)
        if not usable:
            failures.append(role)
    selected = combine_route_flags(route, role_flags)
    result = {
        "result_schema_version": "warrantroute-model-neutral-result-v1",
        "reviewer_profile_id": adapter.profile_id,
        "adapter_freeze_sha256": adapter.adapter_freeze_sha256,
        "reviewer_profile_sha256": adapter.profile_sha256,
        "reviewer_model_id": profile["model_id"],
        "study_id": value["study_id"],
        "item_id": value["item_id"],
        "evaluator_item_sha256": value["evaluator_item_sha256"],
        "matrix_sha256": sha256_bytes(canonical_bytes(value)),
        "route": route,
        "selected_roles": selected_roles,
        "selected_observation_sha256": selected_hashes,
        "selected_serious_error_flags": [flag for flag in FLAG_ORDER if flag in selected],
        "selected_role_failures": failures,
        "aggregation": aggregation,
        "fallback_used": False,
        "merged_rating_created": False,
        "contains_source_text": False,
        "software_contract_fixture": True,
        "manuscript_eligible": False,
    }
    _schema_validate(
        result,
        adapter.result_schema(),
        "model_neutral_result_schema_invalid",
    )
    return result


def source_free_contract_test(adapter: ValidatedAdapter) -> dict[str, Any]:
    profile = adapter.profile()
    role_flags = {
        "researcher": {"unsupported_inference"},
        "qualitative_methods": {"lost_negative_case"},
        "domain": {"contextual_flattening"},
    }
    expected = {
        "none": ["unsupported_inference"],
        "qualitative_methods": ["lost_negative_case"],
        "domain": ["contextual_flattening"],
        "both": ["lost_negative_case", "contextual_flattening"],
    }
    observed = {
        route: [flag for flag in FLAG_ORDER if flag in combine_route_flags(route, role_flags)]
        for route in ROUTE_ORDER
    }
    require(observed == expected, "source_free_route_contract_failed")
    return {
        "component": adapter.freeze_version,
        "status": "passed",
        "reviewer_profile_id": profile["profile_id"],
        "reviewer_model_id": profile["model_id"],
        "route_contracts_checked": 4,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def dry_run(adapter: ValidatedAdapter) -> dict[str, Any]:
    profile = adapter.profile()
    return {
        "component": adapter.freeze_version,
        "status": "passed",
        "primary_reviewer_profile_id": adapter.primary_profile_id,
        "selected_reviewer_profile_id": adapter.profile_id,
        "selected_model_id": profile["model_id"],
        "selected_profile_status": profile["status"],
        "reviewer_canary_status": profile["reviewer_canary_status"],
        "available_reviewer_profiles": list(adapter.profile_order),
        "source_bearing_execution_allowed": False,
        "routing_policy_bound": False,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dry-run", "source-free-test", "train", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--reviewer-profile", default="qwen3_8b")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config_path = args.config.resolve()
        require(config_path == DEFAULT_CONFIG.resolve(), "nondefault_freeze_rejected")
        if args.command == "train":
            raise MultimodelAdapterError("router_training_not_authorized")
        if args.command == "run":
            raise MultimodelAdapterError("source_bearing_execution_not_authorized")
        adapter = load_validated_adapter(config_path, args.reviewer_profile)
        if args.command == "dry-run":
            payload = dry_run(adapter)
            print(json.dumps(payload, sort_keys=True))
            return 0
        if args.command == "source-free-test":
            payload = source_free_contract_test(adapter)
            print(json.dumps(payload, sort_keys=True))
            return 0
        raise MultimodelAdapterError("command_invalid")
    except MultimodelAdapterError as exc:
        payload = {
            "component": "warrantroute-multimodel-adapter-v1",
            "status": "blocked",
            "error": str(exc),
            "source_text_accessed": False,
            "model_service_contacted": False,
            "outputs_written": False,
            "manuscript_eligible": False,
        }
        print(json.dumps(payload, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
