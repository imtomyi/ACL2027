#!/usr/bin/env python3
"""Source-free Qwen3 fixed-role component for WarrantRoute.

The component builds hardened requests for three reviewer roles and implements
the development-only fixed-role selector. It cannot open a packet bank or run a
real experiment under the tracked source-free freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "qwen3_fixed_role_freeze.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import qwen3_fixed_role_runtime as runtime  # noqa: E402
from prompt_limit_guard import harden_ollama_request  # noqa: E402


ROLE_ORDER = ("researcher", "qualitative_methods", "domain")
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
EXPECTED_ASSET_FILES = {
    "runner": "experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py",
    "prompt_limit_guard": "experiments/rq2_role_prompted_llm/scripts/prompt_limit_guard.py",
    "fixed_role_runtime": "experiments/rq2_role_prompted_llm/scripts/qwen3_fixed_role_runtime.py",
    "contract": "experiments/rq2_role_prompted_llm/protocol/qwen3_fixed_role_contract_v1.md",
    "shared_rater_guide": "experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md",
    "evaluator_item_schema": "experiments/direction_j_llm_as_rater/schemas/evaluator_item.schema.json",
    "shared_rating_transport_schema": "experiments/rq2_role_prompted_llm/schemas/shared_rating_transport_v1.schema.json",
    "shared_rating_schema": "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json",
    "development_input_schema": "experiments/rq2_role_prompted_llm/schemas/fixed_role_development_input_v1.schema.json",
    "selection_schema": "experiments/rq2_role_prompted_llm/schemas/fixed_role_selection_v1.schema.json",
}


class FixedRoleError(RuntimeError):
    """A finite source-free failure safe to expose to an operator."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FixedRoleError(code)


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
    path = runtime.workspace_path(entry["file"])
    try:
        return runtime.validate_hash(path, entry["sha256"], label)
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc


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
            "fixed_role_selection_allowed",
            "manuscript_eligible",
            "reviewer_actors",
            "candidate_generation_separation",
            "service",
            "decoding",
            "rating_repetitions",
            "primary_repetition",
            "repetition_seeds",
            "roles",
            "fixed_role_selection",
            "assets",
            "prompt_limit",
            "source_free_canary",
        },
        "freeze",
    )
    require(
        config["document_type"] == "warrantroute_qwen3_fixed_role_component_freeze",
        "freeze_type_invalid",
    )
    require(config["freeze_version"] == "qwen3-fixed-role-v1", "freeze_version_invalid")
    require(config["status"] == "source_free_component_only", "freeze_status_invalid")
    require(config["execution_class"] == "engineering_component", "execution_class_invalid")
    require(config["source_bearing_execution_allowed"] is False, "source_execution_enabled")
    require(config["fixed_role_selection_allowed"] is False, "selection_execution_enabled")
    require(config["manuscript_eligible"] is False, "manuscript_eligibility_enabled")

    actors = config["reviewer_actors"]
    require(tuple(actors) == ROLE_ORDER, "reviewer_actor_order_invalid")
    actor_ids: set[str] = set()
    manifest: tuple[str, str] | None = None
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
        require(actor["actor_id"] not in actor_ids, "reviewer_actor_id_duplicate")
        actor_ids.add(actor["actor_id"])
        require(
            actor["actor_id"] == EXPECTED_ACTOR_IDS[role],
            f"reviewer_actor_id_drift:{role}",
        )
        require(actor["actor_kind"] == "llm", f"actor_kind_invalid:{role}")
        require(actor["task_role"] == "reviewer", f"actor_task_invalid:{role}")
        require(actor["prompted_role"] == role, f"actor_prompted_role_invalid:{role}")
        require(actor["model_id"] == "qwen3:8b", f"actor_model_invalid:{role}")
        observed_manifest = (
            actor["local_manifest_path"],
            actor["local_manifest_file_sha256"],
        )
        require(manifest in {None, observed_manifest}, "reviewer_snapshot_not_shared")
        manifest = observed_manifest
    assert manifest is not None
    manifest_path = Path(manifest[0])
    require(manifest_path.is_absolute(), "model_manifest_path_not_absolute")
    try:
        runtime.validate_hash(manifest_path, manifest[1], "qwen_model_manifest")
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc

    separation = config["candidate_generation_separation"]
    require(
        separation
        == {
            "consumes_sealed_evaluator_items_only": True,
            "candidate_generator_actor_bound_in_component": False,
            "distinct_actor_and_run_records_required": True,
            "authorized_study_freeze_required": True,
        },
        "candidate_generation_separation_invalid",
    )
    try:
        runtime.validate_numeric_loopback(config["service"]["url"])
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc
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

    selection = config["fixed_role_selection"]
    require(
        selection
        == {
            "development_corpus": "dreaddit",
            "development_split": "official_train",
            "development_role": "development",
            "error_families": list(ERROR_FAMILIES),
            "target_to_flag_mapping": TARGET_TO_FLAG,
            "family_balance_required": True,
            "minimum_items_per_family": None,
            "minimum_independent_clusters_per_family": None,
            "selection_metric": "repetition_1_micro_recall",
            "tie_order": list(ROLE_ORDER),
            "zero_denominator_action": "block",
            "seal_before_heldout_access": True,
            "reselection_allowed": False,
        },
        "fixed_role_selection_contract_invalid",
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
        "development_input_schema",
        "selection_schema",
    ):
        try:
            schemas[label] = json.loads(loaded[label])
            jsonschema.Draft202012Validator.check_schema(schemas[label])
        except (json.JSONDecodeError, jsonschema.SchemaError) as exc:
            raise FixedRoleError(f"{label}_invalid") from exc
    return {
        "role_prompts": {role: value.decode("utf-8") for role, value in role_prompts.items()},
        "shared_rater_guide": loaded["shared_rater_guide"].decode("utf-8"),
        **schemas,
    }


def build_rating_request(
    config: dict[str, Any],
    assets: dict[str, Any],
    item: dict[str, Any],
    *,
    role: str,
    repetition: int,
) -> dict[str, Any]:
    require(role in ROLE_ORDER, "unknown_reviewer_role")
    try:
        runtime.validate_evaluator_item(item, assets["evaluator_item_schema"])
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc
    require(1 <= repetition <= config["rating_repetitions"], "rating_repetition_invalid")
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
                    assets["shared_rater_guide"], item
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
    requests = []
    for role in ROLE_ORDER:
        for repetition in range(1, config["rating_repetitions"] + 1):
            request = build_rating_request(
                config, assets, item, role=role, repetition=repetition
            )
            requests.append(
                {
                    "role": role,
                    "repetition": repetition,
                    "request_sha256": sha256_bytes(canonical_bytes(request)),
                    "seed": request["options"]["seed"],
                }
            )
    return {
        "component": config["freeze_version"],
        "status": "passed",
        "request_count": len(requests),
        "requests": requests,
        "source_text_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
        "manuscript_eligible": False,
    }


def _validate_development_input(
    value: dict[str, Any],
    *,
    schema: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, int], dict[str, int]]:
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise FixedRoleError("development_input_schema_invalid") from exc
    require(value["reviewer_model"]["model_id"] == "qwen3:8b", "development_model_invalid")
    snapshot = next(iter(config["reviewer_actors"].values()))[
        "local_manifest_file_sha256"
    ]
    require(
        value["reviewer_model"]["model_snapshot_sha256"] == snapshot,
        "development_model_snapshot_drift",
    )
    items = value["items"]
    require(bool(items), "development_items_empty")
    item_ids: set[str] = set()
    evaluator_item_hashes: set[str] = set()
    observation_hashes: set[str] = set()
    family_counts: Counter[str] = Counter()
    family_clusters: dict[str, set[str]] = defaultdict(set)
    for item in items:
        require(item["item_id"] not in item_ids, "development_item_duplicate")
        item_ids.add(item["item_id"])
        require(
            item["evaluator_item_sha256"] not in evaluator_item_hashes,
            "evaluator_item_duplicate",
        )
        evaluator_item_hashes.add(item["evaluator_item_sha256"])
        family = item["error_family"]
        require(item["required_flag"] == TARGET_TO_FLAG[family], "target_flag_mapping_drift")
        family_counts[family] += 1
        family_clusters[family].add(item["cluster_id"])
        for role in ROLE_ORDER:
            observation = item["role_observations"][role]
            require(
                observation["actor_id"] == config["reviewer_actors"][role]["actor_id"],
                f"reviewer_actor_drift:{role}",
            )
            require(
                observation["model_snapshot_sha256"] == snapshot,
                f"reviewer_snapshot_drift:{role}",
            )
            require(
                observation["evaluator_item_sha256"] == item["evaluator_item_sha256"],
                f"evaluator_item_hash_drift:{role}",
            )
            observation_hash = observation["observation_sha256"]
            require(observation_hash not in observation_hashes, "observation_duplicate")
            observation_hashes.add(observation_hash)
    require(set(family_counts) == set(ERROR_FAMILIES), "development_family_missing")
    require(len(set(family_counts.values())) == 1, "development_family_unbalanced")
    minimum_items = value["minimum_items_per_family"]
    minimum_clusters = value["minimum_independent_clusters_per_family"]
    require(
        all(family_counts[family] >= minimum_items for family in ERROR_FAMILIES),
        "minimum_items_per_family_not_met",
    )
    cluster_counts = {family: len(family_clusters[family]) for family in ERROR_FAMILIES}
    require(
        all(cluster_counts[family] >= minimum_clusters for family in ERROR_FAMILIES),
        "minimum_clusters_per_family_not_met",
    )
    return (
        {family: family_counts[family] for family in ERROR_FAMILIES},
        cluster_counts,
    )


def _observation_hit(observation: dict[str, Any], required_flag: str) -> bool:
    if observation["observation_status"] != "valid":
        return False
    rating = observation["rating"]
    return bool(
        isinstance(rating, dict)
        and rating.get("cannot_judge") == []
        and required_flag in rating.get("serious_error_flags", [])
    )


def select_fixed_role(
    development: dict[str, Any],
    *,
    config: dict[str, Any],
    assets: dict[str, Any],
) -> dict[str, Any]:
    family_counts, cluster_counts = _validate_development_input(
        development,
        schema=assets["development_input_schema"],
        config=config,
    )
    items = development["items"]
    require(bool(items), "development_items_empty")
    summaries: dict[str, dict[str, Any]] = {}
    for role in ROLE_ORDER:
        tp = sum(
            _observation_hit(item["role_observations"][role], item["required_flag"])
            for item in items
        )
        n = len(items)
        summaries[role] = {"tp": tp, "fn": n - tp, "n": n, "recall": tp / n}
    selected = max(
        ROLE_ORDER,
        key=lambda role: (summaries[role]["tp"], -ROLE_ORDER.index(role)),
    )
    record = {
        "document_type": "rq2_qwen3_fixed_role_selection",
        "selection_version": "rq2-qwen3-fixed-role-selection-v1",
        "study_id": development["study_id"],
        "selected_role": selected,
        "tie_order": list(ROLE_ORDER),
        "selection_metric": "repetition_1_micro_recall",
        "primary_repetition": 1,
        "development_input_sha256": sha256_bytes(canonical_bytes(development)),
        "qualification_seal_sha256": development["qualification_seal_sha256"],
        "reviewer_model": development["reviewer_model"],
        "family_item_counts": family_counts,
        "family_cluster_counts": cluster_counts,
        "development_role_summary": summaries,
        "heldout_accessed_before_selection": False,
        "reselection_allowed": False,
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }
    try:
        jsonschema.Draft202012Validator(assets["selection_schema"]).validate(record)
    except jsonschema.ValidationError as exc:
        raise FixedRoleError("selection_record_schema_invalid") from exc
    return record


def _validate_selection_for_seal(
    selection: dict[str, Any],
    *,
    selection_schema: dict[str, Any],
) -> None:
    try:
        jsonschema.Draft202012Validator(selection_schema).validate(selection)
    except jsonschema.ValidationError as exc:
        raise FixedRoleError("selection_record_schema_invalid") from exc

    summaries = selection["development_role_summary"]
    denominators = {summaries[role]["n"] for role in ROLE_ORDER}
    require(len(denominators) == 1 and next(iter(denominators)) > 0, "selection_denominator_invalid")
    denominator = next(iter(denominators))
    for role in ROLE_ORDER:
        summary = summaries[role]
        require(summary["tp"] + summary["fn"] == denominator, "selection_summary_arithmetic_invalid")
        require(
            abs(summary["recall"] - (summary["tp"] / denominator)) <= 1e-12,
            "selection_recall_invalid",
        )

    item_counts = selection["family_item_counts"]
    cluster_counts = selection["family_cluster_counts"]
    require(len(set(item_counts.values())) == 1, "selection_family_unbalanced")
    require(sum(item_counts.values()) == denominator, "selection_family_denominator_invalid")
    require(
        all(cluster_counts[family] <= item_counts[family] for family in ERROR_FAMILIES),
        "selection_cluster_count_invalid",
    )
    expected_role = max(
        ROLE_ORDER,
        key=lambda role: (summaries[role]["tp"], -ROLE_ORDER.index(role)),
    )
    require(selection["selected_role"] == expected_role, "selection_role_not_reproducible")


def build_selection_seal(
    selection: dict[str, Any],
    *,
    freeze_sha256: str,
    selection_schema: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(freeze_sha256, str)
        and len(freeze_sha256) == 64
        and all(char in "0123456789abcdef" for char in freeze_sha256),
        "freeze_sha256_invalid",
    )
    _validate_selection_for_seal(selection, selection_schema=selection_schema)
    return {
        "document_type": "rq2_qwen3_fixed_role_selection_seal",
        "seal_version": "rq2-qwen3-fixed-role-selection-seal-v1",
        "selection_sha256": sha256_bytes(canonical_bytes(selection)),
        "development_input_sha256": selection["development_input_sha256"],
        "qualification_seal_sha256": selection["qualification_seal_sha256"],
        "freeze_sha256": freeze_sha256,
        "selected_role": selection["selected_role"],
        "sealed_before_heldout_access": True,
        "contains_source_text": False,
        "result_label": "diagnostic_not_manuscript_evidence",
        "manuscript_eligible": False,
    }


def preflight_service(config: dict[str, Any]) -> dict[str, Any]:
    try:
        result = runtime.preflight_service(config)
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc
    result["reviewer_role_count"] = len(ROLE_ORDER)
    return result


def _post_source_free_role_canary(
    role: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    except runtime.FixedRoleRuntimeError as exc:
        raise FixedRoleError(str(exc)) from exc
    return request, response


def run_source_free_canary(config: dict[str, Any], assets: dict[str, Any]) -> dict[str, Any]:
    baseline = preflight_service(config)
    results = []
    for role in ROLE_ORDER:
        try:
            request, response = _post_source_free_role_canary(role)
            rating, context = runtime.parse_rating_response(
                response,
                expected_model="qwen3:8b",
                rating_schema=assets["shared_rating_schema"],
                config=config,
            )
        except runtime.FixedRoleRuntimeError as exc:
            raise FixedRoleError(str(exc)) from exc
        results.append(
            {
                "role": role,
                "rating_schema_valid": True,
                "disposition": rating["disposition"],
                "prompt_eval_count": context["prompt_eval_count"],
                "eval_count": context["eval_count"],
            }
        )
    require(preflight_service(config) == baseline, "service_identity_changed_during_canary")
    return {
        "component": config["freeze_version"],
        "status": "passed",
        "roles": results,
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
        except runtime.FixedRoleRuntimeError as exc:
            raise FixedRoleError(str(exc)) from exc
        assets = validate_freeze(config, config_path=DEFAULT_CONFIG)
        if args.command == "dry-run":
            result = source_free_request_plan(config, assets)
        elif args.command == "preflight-service":
            result = preflight_service(config)
        elif args.command == "source-free-test":
            result = run_source_free_canary(config, assets)
        else:
            raise FixedRoleError("source_bearing_execution_not_authorized")
        print(json.dumps(result, sort_keys=True))
        return 0
    except FixedRoleError as exc:
        print(
            json.dumps(
                {
                    "component": "qwen3-fixed-role-v1",
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
