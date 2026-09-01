#!/usr/bin/env python3
"""Source-free Qwen3 WarrantRoute policy and route-application component."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "qwen3_warrantroute_freeze.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import qwen3_fixed_role_runtime as runtime  # noqa: E402


ROLE_ORDER = ("researcher", "qualitative_methods", "domain")
ROUTE_ORDER = ("none", "qualitative_methods", "domain", "both")
ROUTE_TO_ROLES = {
    "none": ("researcher",),
    "qualitative_methods": ("qualitative_methods",),
    "domain": ("domain",),
    "both": ("qualitative_methods", "domain"),
}
EXPECTED_ACTOR_IDS = {
    "researcher": "qwen3_8b_researcher_reviewer_v1",
    "qualitative_methods": "qwen3_8b_qualitative_methods_reviewer_v1",
    "domain": "qwen3_8b_domain_reviewer_v1",
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
FORBIDDEN_ROUTER_KEYS = frozenset(
    {
        "source_text",
        "text",
        "rationale",
        "protected_attributes",
        "participant_attributes",
        "truth",
        "target_flaw",
        "required_flag",
        "error_family",
        "controlled_condition",
        "specialist_observation",
        "specialist_observations",
        "specialist_outcome",
        "specialist_outcomes",
        "test_outcome",
        "test_result",
        "useful_role",
        "route_label",
        "human_response",
        "adjudication",
        "serious_error_flags",
    }
)
EXPECTED_ASSET_FILES = {
    "runner": "experiments/rq2_role_prompted_llm/scripts/run_qwen3_warrantroute.py",
    "runtime": "experiments/rq2_role_prompted_llm/scripts/qwen3_fixed_role_runtime.py",
    "contract": "experiments/rq2_role_prompted_llm/protocol/qwen3_warrantroute_contract_v1.md",
    "qwen3_fixed_role_freeze": "experiments/rq2_role_prompted_llm/config/qwen3_fixed_role_freeze.json",
    "qwen3_fixed_role_runner": "experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py",
    "router_input_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_router_input_v1.schema.json",
    "policy_manifest_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_policy_manifest_v1.schema.json",
    "route_record_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_route_record_v1.schema.json",
    "route_application_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_route_application_v1.schema.json",
    "application_result_schema": "experiments/rq2_role_prompted_llm/schemas/warrantroute_application_result_v1.schema.json",
}


class WarrantRouteError(RuntimeError):
    """A finite, content-free failure safe to report."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise WarrantRouteError(code)


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


def _exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


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


def _schema_validate(value: Any, schema: dict[str, Any], code: str) -> None:
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise WarrantRouteError(code) from exc
    require(_finite_numbers(value), f"{code}_nonfinite")


def _load_asset(entry: dict[str, Any], label: str) -> bytes:
    _exact_keys(entry, {"file", "sha256"}, f"{label}_asset")
    require(entry["file"] == EXPECTED_ASSET_FILES[label], f"{label}_path_drift")
    try:
        return runtime.validate_hash(
            runtime.workspace_path(entry["file"]), entry["sha256"], label
        )
    except runtime.FixedRoleRuntimeError as exc:
        raise WarrantRouteError(str(exc)) from exc


def validate_freeze(
    config: dict[str, Any], *, config_path: Path = DEFAULT_CONFIG
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
            "heldout_access_allowed",
            "router_training_allowed",
            "routing_policy_bound",
            "manuscript_eligible",
            "qwen_reviewer",
            "route_contract",
            "feature_contract",
            "future_policy",
            "scientific_decisions_required",
            "assets",
        },
        "freeze",
    )
    require(
        config["document_type"] == "warrantroute_qwen3_component_freeze",
        "freeze_type_invalid",
    )
    require(config["freeze_version"] == "qwen3-warrantroute-v1", "freeze_version_invalid")
    require(config["status"] == "source_free_policy_unbound", "freeze_status_invalid")
    require(config["execution_class"] == "engineering_component", "execution_class_invalid")
    require(config["source_bearing_execution_allowed"] is False, "source_execution_enabled")
    require(config["heldout_access_allowed"] is False, "heldout_access_enabled")
    require(config["router_training_allowed"] is False, "router_training_enabled")
    require(config["routing_policy_bound"] is False, "unexpected_routing_policy")
    require(config["manuscript_eligible"] is False, "manuscript_eligibility_enabled")

    reviewer = config["qwen_reviewer"]
    _exact_keys(
        reviewer,
        {
            "model_id",
            "model_manifest_path",
            "model_manifest_sha256",
            "roles",
            "actor_ids",
            "primary_repetition",
            "stability_repetitions",
        },
        "qwen_reviewer",
    )
    require(reviewer["model_id"] == "qwen3:8b", "reviewer_model_invalid")
    require(tuple(reviewer["roles"]) == ROLE_ORDER, "reviewer_role_order_invalid")
    require(reviewer["actor_ids"] == EXPECTED_ACTOR_IDS, "reviewer_actor_ids_invalid")
    require(reviewer["primary_repetition"] == 1, "primary_repetition_invalid")
    require(reviewer["stability_repetitions"] == [1, 2, 3], "stability_repetitions_invalid")
    manifest_path = Path(reviewer["model_manifest_path"])
    require(manifest_path.is_absolute(), "model_manifest_path_not_absolute")
    try:
        runtime.validate_hash(
            manifest_path, reviewer["model_manifest_sha256"], "qwen_model_manifest"
        )
    except runtime.FixedRoleRuntimeError as exc:
        raise WarrantRouteError(str(exc)) from exc

    require(
        config["route_contract"]
        == {
            "route_values": list(ROUTE_ORDER),
            "selected_roles": {
                route: list(roles) for route, roles in ROUTE_TO_ROLES.items()
            },
            "both_aggregation": "union_serious_error_flags",
            "selected_role_failure": "empty_flags_no_fallback",
            "specialist_routes_include_researcher": False,
            "merged_rating_created": False,
            "primary_aggregation": "repetition_1",
            "stability_aggregation": "two_of_three_within_role_then_same_route",
        },
        "route_contract_invalid",
    )
    require(
        config["feature_contract"]
        == {
            "feature_set_bound": False,
            "feature_set_id": None,
            "feature_set_sha256": None,
            "allowed_feature_names": [],
            "free_text_allowed": False,
            "protected_attributes_allowed": False,
            "verified_error_allowed": False,
            "specialist_outcomes_allowed": False,
            "heldout_outcomes_allowed": False,
        },
        "feature_contract_invalid",
    )
    require(
        config["future_policy"]
        == {
            "policy_manifest_file": None,
            "policy_manifest_sha256": None,
            "policy_asset_file": None,
            "policy_asset_sha256": None,
            "qualification_gate_file": None,
            "qualification_gate_sha256": None,
            "pre_access_seal_file": None,
            "pre_access_seal_sha256": None,
        },
        "future_policy_contract_invalid",
    )
    decisions = config["scientific_decisions_required"]
    require(isinstance(decisions, list) and len(decisions) >= 12, "scientific_decision_inventory_invalid")
    require(len(set(decisions)) == len(decisions), "scientific_decision_inventory_duplicate")

    assets = config["assets"]
    require(set(assets) == set(EXPECTED_ASSET_FILES), "asset_set_invalid")
    loaded = {label: _load_asset(assets[label], label) for label in EXPECTED_ASSET_FILES}
    schemas: dict[str, Any] = {}
    for label in (
        "router_input_schema",
        "policy_manifest_schema",
        "route_record_schema",
        "route_application_schema",
        "application_result_schema",
    ):
        try:
            schema = json.loads(loaded[label])
            jsonschema.Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
            raise WarrantRouteError(f"{label}_invalid") from exc
        schemas[label] = schema

    try:
        dependency = json.loads(loaded["qwen3_fixed_role_freeze"])
    except json.JSONDecodeError as exc:
        raise WarrantRouteError("qwen_dependency_invalid_json") from exc
    require(
        dependency.get("document_type")
        == "warrantroute_qwen3_fixed_role_component_freeze",
        "qwen_dependency_type_invalid",
    )
    require(dependency.get("source_bearing_execution_allowed") is False, "qwen_dependency_source_enabled")
    require(dependency.get("manuscript_eligible") is False, "qwen_dependency_manuscript_enabled")
    dependency_actors = dependency.get("reviewer_actors", {})
    for role in ROLE_ORDER:
        require(
            dependency_actors.get(role, {}).get("actor_id") == EXPECTED_ACTOR_IDS[role],
            f"qwen_dependency_actor_drift:{role}",
        )
        require(
            dependency_actors.get(role, {}).get("model_id") == "qwen3:8b",
            f"qwen_dependency_model_drift:{role}",
        )
    return schemas


def validate_router_input(
    value: dict[str, Any], *, config: dict[str, Any], schema: dict[str, Any]
) -> None:
    validate_freeze(config)
    _schema_validate(value, schema, "router_input_schema_invalid")
    forbidden = FORBIDDEN_ROUTER_KEYS & set(_walk_keys(value))
    require(not forbidden, "router_input_contains_forbidden_key")
    require(
        value["researcher_observation"]["evaluator_item_sha256"]
        == value["evaluator_item_sha256"],
        "router_researcher_packet_hash_drift",
    )
    require(config["feature_contract"]["feature_set_bound"] is True, "router_feature_set_not_frozen")
    projection = value["feature_projection"]
    require(
        projection["feature_set_id"] == config["feature_contract"]["feature_set_id"],
        "router_feature_set_id_drift",
    )
    require(
        projection["feature_set_sha256"]
        == config["feature_contract"]["feature_set_sha256"],
        "router_feature_set_hash_drift",
    )
    observed_names = set().union(
        projection["numeric"], projection["boolean"], projection["categorical_codes"]
    )
    require(
        observed_names == set(config["feature_contract"]["allowed_feature_names"]),
        "router_feature_names_drift",
    )
    observation = value["researcher_observation"]
    reviewer = config["qwen_reviewer"]
    require(
        observation["model_snapshot_sha256"] == reviewer["model_manifest_sha256"],
        "router_researcher_snapshot_drift",
    )


def validate_policy_manifest(
    value: dict[str, Any], *, config: dict[str, Any], schema: dict[str, Any]
) -> None:
    validate_freeze(config)
    _schema_validate(value, schema, "policy_manifest_schema_invalid")
    require(config["routing_policy_bound"] is True, "routing_policy_not_bound")
    expected = config["future_policy"]
    require(
        expected["policy_manifest_sha256"] == sha256_bytes(canonical_bytes(value)),
        "policy_manifest_hash_drift",
    )
    for key in (
        "policy_manifest_file",
        "policy_asset_file",
        "qualification_gate_file",
        "pre_access_seal_file",
    ):
        require(isinstance(expected[key], str) and bool(expected[key]), f"{key}_not_bound")


def validate_route_record(value: dict[str, Any], *, schema: dict[str, Any]) -> None:
    _schema_validate(value, schema, "route_record_schema_invalid")
    require(
        tuple(value["selected_roles"]) == ROUTE_TO_ROLES[value["route"]],
        "route_selected_roles_mismatch",
    )


def build_route_record(
    router_input: dict[str, Any],
    policy_manifest: dict[str, Any],
    *,
    config: dict[str, Any],
    assets: dict[str, Any],
) -> dict[str, Any]:
    validate_router_input(
        router_input, config=config, schema=assets["router_input_schema"]
    )
    validate_policy_manifest(
        policy_manifest, config=config, schema=assets["policy_manifest_schema"]
    )
    raise WarrantRouteError("policy_inference_not_implemented_in_source_free_freeze")


def build_route_seal(
    route_record: dict[str, Any],
    *,
    route_schema: dict[str, Any],
    freeze_sha256: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    validate_freeze(config)
    raise WarrantRouteError("route_sealing_not_authorized_in_source_free_freeze")


def _build_route_seal_projection_for_contract_test(
    route_record: dict[str, Any], *, route_schema: dict[str, Any], freeze_sha256: str
) -> dict[str, Any]:
    """Build a source-free shape fixture; never an authentic execution seal."""
    validate_route_record(route_record, schema=route_schema)
    require(
        isinstance(freeze_sha256, str)
        and len(freeze_sha256) == 64
        and all(character in "0123456789abcdef" for character in freeze_sha256),
        "freeze_sha256_invalid",
    )
    return {
        "document_type": "warrantroute_route_seal",
        "seal_version": "warrantroute-route-seal-v1",
        "route_record_sha256": sha256_bytes(canonical_bytes(route_record)),
        "policy_manifest_sha256": route_record["policy_manifest_sha256"],
        "freeze_sha256": freeze_sha256,
        "item_id": route_record["item_id"],
        "route": route_record["route"],
        "sealed_before_specialist_observations": True,
        "sealed_before_heldout_access": True,
        "contains_source_text": False,
        "manuscript_eligible": False,
    }


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


def _validate_application_projection_contract(
    value: dict[str, Any], *, config: dict[str, Any], assets: dict[str, Any]
) -> None:
    _schema_validate(
        value, assets["route_application_schema"], "route_application_schema_invalid"
    )
    route_record = value["route_record"]
    validate_route_record(route_record, schema=assets["route_record_schema"])
    route_seal = value["route_seal"]
    require(
        route_seal["route_record_sha256"]
        == sha256_bytes(canonical_bytes(route_record)),
        "application_route_seal_record_drift",
    )
    require(
        route_seal["policy_manifest_sha256"]
        == route_record["policy_manifest_sha256"],
        "application_route_seal_policy_drift",
    )
    require(route_seal["item_id"] == route_record["item_id"], "application_route_seal_item_drift")
    require(route_seal["route"] == route_record["route"], "application_route_seal_route_drift")
    try:
        frozen_config_sha256 = sha256_bytes(runtime.read_regular_bytes(DEFAULT_CONFIG))
    except runtime.FixedRoleRuntimeError as exc:
        raise WarrantRouteError(str(exc)) from exc
    require(
        route_seal["freeze_sha256"] == frozen_config_sha256,
        "application_route_seal_freeze_drift",
    )
    require(value["study_id"] == route_record["study_id"], "application_study_drift")
    require(value["item_id"] == route_record["item_id"], "application_item_drift")
    require(value["lane"] == route_record["lane"], "application_lane_drift")
    require(
        value["evaluator_item_sha256"] == route_record["evaluator_item_sha256"],
        "application_packet_hash_drift",
    )
    reviewer = config["qwen_reviewer"]
    require(value["reviewer_model"]["model_id"] == reviewer["model_id"], "application_model_drift")
    require(
        value["reviewer_model"]["model_snapshot_sha256"]
        == reviewer["model_manifest_sha256"],
        "application_snapshot_drift",
    )
    observed_hashes: set[str] = set()
    for role in ROLE_ORDER:
        observations = value["role_observations"][role]
        require(
            {row["rating_repetition"] for row in observations} == {1, 2, 3},
            f"application_repetition_grid_invalid:{role}",
        )
        for observation in observations:
            require(observation["actor_id"] == EXPECTED_ACTOR_IDS[role], f"application_actor_drift:{role}")
            require(observation["prompted_role"] == role, f"application_role_drift:{role}")
            require(observation["model_id"] == reviewer["model_id"], f"application_model_drift:{role}")
            require(
                observation["model_snapshot_sha256"] == reviewer["model_manifest_sha256"],
                f"application_snapshot_drift:{role}",
            )
            require(observation["item_id"] == value["item_id"], f"application_item_drift:{role}")
            require(
                observation["evaluator_item_sha256"] == value["evaluator_item_sha256"],
                f"application_evaluator_hash_drift:{role}",
            )
            observation_hash = observation["observation_sha256"]
            require(observation_hash not in observed_hashes, "application_observation_duplicate")
            observed_hashes.add(observation_hash)


def validate_application_input(
    value: dict[str, Any], *, config: dict[str, Any], assets: dict[str, Any]
) -> None:
    """Authorize an application before inspecting its source-linked projection."""
    validate_freeze(config)
    require(config["routing_policy_bound"] is True, "routing_policy_not_bound")
    require(
        config["source_bearing_execution_allowed"] is True,
        "source_bearing_execution_not_authorized",
    )
    _validate_application_projection_contract(value, config=config, assets=assets)


def _apply_route_projection_for_contract_test(
    value: dict[str, Any],
    *,
    aggregation: str,
    config: dict[str, Any],
    assets: dict[str, Any],
) -> dict[str, Any]:
    """Exercise route semantics on source-free fixtures without authorizing a run."""
    _validate_application_projection_contract(value, config=config, assets=assets)
    require(aggregation in {"repetition_1", "two_of_three"}, "aggregation_invalid")
    route_record = value["route_record"]
    selected_roles = list(ROUTE_TO_ROLES[route_record["route"]])
    flags_by_role: dict[str, set[str]] = {}
    selected_hashes: list[str] = []
    failures: list[str] = []
    for role in selected_roles:
        flags, usable, hashes = _role_flags(
            value["role_observations"][role], aggregation
        )
        flags_by_role[role] = flags
        selected_hashes.extend(hashes)
        if not usable:
            failures.append(role)
    selected_flags = combine_route_flags(route_record["route"], flags_by_role)
    result = {
        "result_schema_version": "warrantroute-application-result-v1",
        "study_id": value["study_id"],
        "item_id": value["item_id"],
        "evaluator_item_sha256": value["evaluator_item_sha256"],
        "lane": value["lane"],
        "application_input_sha256": sha256_bytes(canonical_bytes(value)),
        "route_record_sha256": sha256_bytes(canonical_bytes(route_record)),
        "route": route_record["route"],
        "selected_roles": selected_roles,
        "selected_observation_sha256": selected_hashes,
        "selected_serious_error_flags": [
            flag for flag in FLAG_ORDER if flag in selected_flags
        ],
        "selected_role_failures": failures,
        "aggregation": aggregation,
        "fallback_used": False,
        "merged_rating_created": False,
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }
    _schema_validate(
        result, assets["application_result_schema"], "application_result_schema_invalid"
    )
    return result


def apply_frozen_route(
    value: dict[str, Any],
    *,
    aggregation: str,
    config: dict[str, Any],
    assets: dict[str, Any],
) -> dict[str, Any]:
    """Apply a route only under an authorized successor freeze.

    The present v1 freeze is deliberately unbound, so this entrypoint always
    fails closed before examining the source-linked application projection.
    """
    validate_application_input(value, config=config, assets=assets)
    return _apply_route_projection_for_contract_test(
        value, aggregation=aggregation, config=config, assets=assets
    )


def source_free_contract_test(config: dict[str, Any]) -> dict[str, Any]:
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
        "component": config["freeze_version"],
        "status": "passed",
        "route_contracts_checked": 4,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def source_free_plan(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "component": config["freeze_version"],
        "status": "passed",
        "reviewer_model": config["qwen_reviewer"]["model_id"],
        "reviewer_roles": list(ROLE_ORDER),
        "route_values": list(ROUTE_ORDER),
        "route_mapping": {
            route: list(roles) for route, roles in ROUTE_TO_ROLES.items()
        },
        "routing_policy_bound": False,
        "router_training_allowed": False,
        "source_bearing_execution_allowed": False,
        "heldout_access_allowed": False,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    value.add_argument(
        "command", choices=("dry-run", "source-free-test", "train", "run")
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        require(args.config == DEFAULT_CONFIG, "nondefault_freeze_rejected")
        try:
            config = runtime.load_json(DEFAULT_CONFIG)
        except runtime.FixedRoleRuntimeError as exc:
            raise WarrantRouteError(str(exc)) from exc
        validate_freeze(config, config_path=DEFAULT_CONFIG)
        if args.command == "dry-run":
            result = source_free_plan(config)
        elif args.command == "source-free-test":
            result = source_free_contract_test(config)
        elif args.command == "train":
            raise WarrantRouteError("router_training_not_authorized")
        else:
            raise WarrantRouteError("source_bearing_execution_not_authorized")
        print(json.dumps(result, sort_keys=True))
        return 0
    except WarrantRouteError as exc:
        print(
            json.dumps(
                {
                    "component": "qwen3-warrantroute-v1",
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
