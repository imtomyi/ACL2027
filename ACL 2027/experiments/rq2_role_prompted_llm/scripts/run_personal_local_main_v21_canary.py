#!/usr/bin/env python3
"""Run source-free structured-output canaries for the v2.1 compatibility freeze.

``dry-run`` validates only frozen source-free files and never contacts Ollama.
``run`` makes one no-source call for each v2.1 construction schema.  It writes
no files and emits only finite case, schema, and status codes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
ADAPTER = SCRIPT.with_name("run_personal_local_main_v21.py")
ADAPTER_SHA256 = "9cf46518f47edf25b2fbaab75e58815dbcc1acb8da60bb059bc867abf8122856"
COMPAT_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v2_compat_freeze.json"
BASELINE_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v2_freeze.json"
BASELINE_CONFIG_SHA256 = "c65834a98c3fa3703edfe24de163497c063a8276410f44c55bf8c4b022762b0a"


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_adapter() -> Any:
    if raw_sha256(ADAPTER) != ADAPTER_SHA256:
        raise SystemExit("v21_canary_adapter_hash_drift")
    spec = importlib.util.spec_from_file_location(
        "rq2_personal_local_main_v21_adapter_for_canary", ADAPTER
    )
    if spec is None or spec.loader is None:
        raise SystemExit("v21_canary_adapter_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()
core = adapter.core


class CanaryError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CanaryError(code)


ALLOWED_SCHEMA_KEYWORDS = {
    "$schema",
    "$id",
    "title",
    "type",
    "required",
    "properties",
    "additionalProperties",
    "enum",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
}
ALLOWED_TYPES = {"object", "array", "string", "integer", "boolean"}


def validate_ollama_schema_subset(schema: dict[str, Any]) -> None:
    """Validate the deliberately small recursive JSON-schema subset."""

    def visit(node: Any) -> None:
        require(isinstance(node, dict), "schema_node_not_object")
        require(set(node) <= ALLOWED_SCHEMA_KEYWORDS, "schema_keyword_not_allowed")
        if "type" in node:
            require(node["type"] in ALLOWED_TYPES, "schema_type_not_allowed")
        if "enum" in node:
            enum = node["enum"]
            require(
                isinstance(enum, list)
                and bool(enum)
                and len({json.dumps(value, sort_keys=True) for value in enum}) == len(enum)
                and all(isinstance(value, (str, int, bool)) for value in enum),
                "schema_enum_invalid",
            )
        if "properties" in node:
            properties = node["properties"]
            required = node.get("required")
            require(
                node.get("type") == "object"
                and isinstance(properties, dict)
                and bool(properties)
                and isinstance(required, list)
                and len(required) == len(set(required))
                and set(required) == set(properties)
                and node.get("additionalProperties") is False,
                "schema_object_not_closed_or_fully_required",
            )
            for child in properties.values():
                visit(child)
        else:
            require("required" not in node, "schema_required_without_properties")
            require(
                "additionalProperties" not in node,
                "schema_additional_properties_without_object",
            )
        if node.get("type") == "array":
            require(isinstance(node.get("items"), dict), "schema_array_items_invalid")
            visit(node["items"])
        else:
            require("items" not in node, "schema_items_without_array")
        for keyword in ("minItems", "maxItems", "minLength"):
            if keyword in node:
                require(
                    type(node[keyword]) is int and node[keyword] >= 0,
                    "schema_numeric_bound_invalid",
                )
        if "uniqueItems" in node:
            require(node["uniqueItems"] is True, "schema_unique_items_invalid")

    require(isinstance(schema, dict), "schema_root_invalid")
    require(
        schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
        "schema_draft_mismatch",
    )
    visit(schema)


FALSE_CHECKS = {
    "all_material_claims_warranted": False,
    "support_roles_accurate": False,
    "independent_support_units_sufficient": False,
    "counter_roles_genuine": False,
    "boundary_links_consequential_and_preserved": False,
    "claim_scope_packet_bounded": False,
    "no_outside_facts": False,
    "no_other_material_flaw": False,
}
NO_SOURCE_READINESS = {
    name: {"status": "not_ready", "evidence_positions": []}
    for name in (
        "non_support_anchor",
        "multi_unit_support",
        "consequential_counter",
        "local_distinction",
        "bounded_claim",
    )
}


CANARY_CASES: tuple[dict[str, Any], ...] = (
    {
        "code": "base_generation",
        "model_role": "generator",
        "prompt_key": "prompt_base_generation",
        "schema_key": "schema_base_generation",
        "user_prompt": (
            "COMPATIBILITY CANARY. No evidence content is supplied. Return "
            "not_constructable with the exact placeholders. Return reason_codes "
            "as exactly [insufficient_independent_support], with no duplicate code."
        ),
        "status_field": "status",
        "expected": {
            "generation_schema_version": "rq2-base-generation-v2.1",
            "status": "not_constructable",
            "theme_name": "NOT_CONSTRUCTED",
            "claim": "NOT_CONSTRUCTED",
            "explanation": "NOT_CONSTRUCTED",
            "claim_scope": "not_constructed",
            "role_plan": [
                {"position": position, "role": "unassigned"}
                for position in range(1, 7)
            ],
            "boundary_conditions": [],
            "reason_codes": ["insufficient_independent_support"],
        },
    },
    {
        "code": "base_admissibility",
        "model_role": "verifier",
        "prompt_key": "prompt_base_admissibility",
        "schema_key": "schema_base_admissibility",
        "user_prompt": (
            "COMPATIBILITY CANARY. No base content is supplied. Return base_status "
            "unclear. Set every check to false. For each of the five readiness "
            "entries, set status to not_ready and evidence_positions to an empty "
            "array; never use ready. Return reason_codes containing "
            "insufficient_displayed_information exactly once and do not repeat any "
            "code. Use the exact schema version and no other fields."
        ),
        "status_field": "base_status",
        "expected": {
            "admissibility_schema_version": "rq2-base-admissibility-v2.1",
            "base_status": "unclear",
            "checks": FALSE_CHECKS,
            "readiness": NO_SOURCE_READINESS,
            "reason_codes": ["insufficient_displayed_information"],
        },
    },
    {
        "code": "contextual_flattening_edit",
        "model_role": "generator",
        "prompt_key": "prompt_contextual_flattening_edit",
        "schema_key": "schema_contextual_flattening_edit",
        "user_prompt": (
            "COMPATIBILITY CANARY. No base content is supplied. Return "
            "not_constructable with exact placeholders. Return reason_codes as "
            "exactly [distinction_anchor_unclear], with no duplicate code."
        ),
        "status_field": "status",
        "expected": {
            "edit_schema_version": "rq2-contextual-flattening-edit-v2.1",
            "status": "not_constructable",
            "patch": {
                "edit_field": "not_applicable",
                "boundary_slot": 1,
                "replacement_text": "NOT_CONSTRUCTED",
                "evidence_positions": [],
                "edit_intent_code": "not_constructed",
            },
            "reason_codes": ["distinction_anchor_unclear"],
        },
    },
    {
        "code": "unsupported_abstraction_edit",
        "model_role": "generator",
        "prompt_key": "prompt_unsupported_abstraction_edit",
        "schema_key": "schema_unsupported_abstraction_edit",
        "user_prompt": (
            "COMPATIBILITY CANARY. No base content is supplied. Return "
            "not_constructable with exact placeholders. Return reason_codes as "
            "exactly [bounded_claim_not_clear], with no duplicate code."
        ),
        "status_field": "status",
        "expected": {
            "edit_schema_version": "rq2-unsupported-abstraction-edit-v2.1",
            "status": "not_constructable",
            "patch": {
                "edit_field": "not_applicable",
                "replacement_text": "NOT_CONSTRUCTED",
                "evidence_positions": [],
                "edit_intent_code": "not_constructed",
            },
            "reason_codes": ["bounded_claim_not_clear"],
        },
    },
    {
        "code": "construction_comparison",
        "model_role": "verifier",
        "prompt_key": "prompt_construction_comparison",
        "schema_key": "schema_construction_comparison",
        "user_prompt": (
            "COMPATIBILITY CANARY. No comparison content is supplied. Return "
            "unclear with the exact negative-branch conventions. Return "
            "uncertainty_codes as exactly [insufficient_displayed_context], with "
            "no duplicate code."
        ),
        "status_field": "comparison_clarity",
        "expected": {
            "comparison_schema_version": "rq2-construction-comparison-v2.1",
            "comparison_clarity": "unclear",
            "present_flaws": [],
            "other_material_flaw": False,
            "single_material_difference": False,
            "anchors": [],
            "uncertainty_codes": ["insufficient_displayed_context"],
        },
    },
)


EXPECTED_HISTORY = {
    "document_type": "rq2_personal_local_v2_compatibility_history",
    "created_at_utc": "2026-08-27T03:39:48Z",
    "status": "source_free_historical_non_reused_record",
    "prior_run_id": "rq2plv2_20260827T033053Z_4c9e7a12",
    "prior_run_outcome": "qualification_failed",
    "qualification_gate": {
        "file": (
            "Storage/rq2_personal_local_diagnostic/v2_runs/"
            "rq2plv2_20260827T033053Z_4c9e7a12/qualification_gate.json"
        ),
        "sha256": "b6c8d313fd896382e1c037f2fe557b0338cbe5a823e6298ca88c4fbf8f444313",
    },
    "output_seal": {
        "file": (
            "Storage/rq2_personal_local_diagnostic/v2_runs/"
            "rq2plv2_20260827T033053Z_4c9e7a12/output_seal.json"
        ),
        "sha256": "c4d9ecb04b53c502678141537c17385d590372f34bb024d780936367b47fc599",
    },
    "prior_results_reused": False,
    "prior_items_reused": False,
    "prior_calls_reused": False,
    "prior_selection_reused": False,
    "prior_threshold_decisions_reused": False,
    "historical_paths_opened_by_compat_runner": False,
    "contains_source_text": False,
    "manuscript_eligible": False,
    "publication_or_release_eligible": False,
}


EXPECTED_COMPAT_ASSET_FILES = {
    "prompt_base_generation": "experiments/rq2_role_prompted_llm/prompts/base_generation_v2_1.md",
    "schema_base_generation": "experiments/rq2_role_prompted_llm/schemas/base_generation_v2_1.schema.json",
    "prompt_base_admissibility": "experiments/rq2_role_prompted_llm/prompts/base_admissibility_v2_1.md",
    "schema_base_admissibility": "experiments/rq2_role_prompted_llm/schemas/base_admissibility_v2_1.schema.json",
    "rule_base_admissibility": "experiments/rq2_role_prompted_llm/protocol/base_admissibility_rule_v2.json",
    "rule_family_edit_contract": "experiments/rq2_role_prompted_llm/protocol/family_edit_contract_v2.json",
    "prompt_contextual_flattening_edit": "experiments/rq2_role_prompted_llm/prompts/contextual_flattening_edit_v2_1.md",
    "schema_contextual_flattening_edit": "experiments/rq2_role_prompted_llm/schemas/contextual_flattening_edit_v2_1.schema.json",
    "prompt_unsupported_abstraction_edit": "experiments/rq2_role_prompted_llm/prompts/unsupported_abstraction_edit_v2_1.md",
    "schema_unsupported_abstraction_edit": "experiments/rq2_role_prompted_llm/schemas/unsupported_abstraction_edit_v2_1.schema.json",
    "prompt_construction_comparison": "experiments/rq2_role_prompted_llm/prompts/construction_comparison_v2_1.md",
    "schema_construction_comparison": "experiments/rq2_role_prompted_llm/schemas/construction_comparison_v2_1.schema.json",
    "rule_construction_comparison_acceptance": (
        "experiments/rq2_role_prompted_llm/protocol/"
        "construction_comparison_acceptance_rule_v2.json"
    ),
    "rule_construction_qualification_thresholds": (
        "experiments/rq2_role_prompted_llm/protocol/"
        "construction_qualification_thresholds_v2.json"
    ),
    "frozen_v2_core_runner": "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py",
    "compat_canary": (
        "experiments/rq2_role_prompted_llm/scripts/"
        "run_personal_local_main_v21_canary.py"
    ),
    "compat_history": (
        "experiments/rq2_role_prompted_llm/protocol/"
        "personal_local_main_v2_compat_history.json"
    ),
}


def validate_compat_config_source_free(
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Validate compat bindings without resolving or opening any Storage path."""

    require(raw_sha256(BASELINE_CONFIG) == BASELINE_CONFIG_SHA256, "baseline_freeze_hash_drift")
    baseline = core.v1.load_json(BASELINE_CONFIG)
    require(set(config) == set(baseline), "compat_freeze_fields_mismatch")
    changed_fields = {"construction_assets", "runner_file", "runner_sha256"}
    require(
        all(config[key] == baseline[key] for key in set(baseline) - changed_fields),
        "compat_frozen_invariant_mismatch",
    )
    require(
        config["runner_file"]
        == "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v21.py"
        and config["runner_sha256"] == ADAPTER_SHA256
        and raw_sha256(ADAPTER) == ADAPTER_SHA256,
        "compat_adapter_binding_mismatch",
    )
    assets = config.get("construction_assets")
    require(
        isinstance(assets, dict) and set(assets) == set(EXPECTED_COMPAT_ASSET_FILES),
        "compat_asset_set_mismatch",
    )
    paths: dict[str, Path] = {}
    for key, expected_file in EXPECTED_COMPAT_ASSET_FILES.items():
        row = assets.get(key)
        require(
            isinstance(row, dict)
            and set(row) == {"file", "sha256"}
            and row["file"] == expected_file
            and isinstance(row["sha256"], str)
            and core.SHA_RE.fullmatch(row["sha256"]) is not None,
            "compat_asset_binding_invalid",
        )
        path = core.v1.resolve_workspace_path(expected_file)
        require(
            path.is_file()
            and not path.is_symlink()
            and "Storage" not in path.relative_to(core.WORKSPACE).parts,
            "compat_asset_path_invalid",
        )
        require(raw_sha256(path) == row["sha256"], "compat_asset_hash_mismatch")
        paths[key] = path
    require(
        raw_sha256(paths["frozen_v2_core_runner"]) == adapter.CORE_RUNNER_SHA256,
        "compat_core_binding_mismatch",
    )
    return baseline, paths


def validate_static() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = core.v1.load_json(COMPAT_CONFIG)
    _, paths = validate_compat_config_source_free(config)
    require(raw_sha256(core.V1_CONFIG) == core.V1_FREEZE_SHA256, "v1_freeze_hash_drift")
    v1_config = core.v1.load_json(core.V1_CONFIG)
    assets = core.load_assets(paths)
    acceptance_rule = assets.get("rule_construction_comparison_acceptance")
    require(
        isinstance(acceptance_rule, dict)
        and acceptance_rule.get("verification_label") == core.VERIFICATION_LABEL
        and config["result_labels"]["verification_label"] == core.VERIFICATION_LABEL,
        "compat_verification_label_mismatch",
    )
    for case in CANARY_CASES:
        schema = assets.get(case["schema_key"])
        prompt = assets.get(case["prompt_key"])
        require(isinstance(prompt, str) and bool(prompt.strip()), "canary_prompt_invalid")
        validate_ollama_schema_subset(schema)
        try:
            jsonschema.validate(case["expected"], schema)
        except jsonschema.ValidationError as exc:
            raise CanaryError("canary_fixture_schema_invalid") from exc
    history = core.v1.load_json(paths["compat_history"])
    require(history == EXPECTED_HISTORY, "compat_history_record_invalid")
    return v1_config, assets, config


def validate_case_semantics(case: dict[str, Any], output: dict[str, Any]) -> None:
    """Apply source-free branch invariants after schema/model compatibility.

    Structured-output validation is layer 1. This is layer 2: it rejects a
    wrong branch or a cross-field contradiction and enforces the exact
    source-free sentinel conventions requested by the embedded canary prompt.
    """

    code = case["code"]
    expected = case["expected"]

    if code == "base_generation":
        valid = (
            output.get("generation_schema_version")
            == expected["generation_schema_version"]
            and output.get("status") == "not_constructable"
            and output.get("theme_name") == "NOT_CONSTRUCTED"
            and output.get("claim") == "NOT_CONSTRUCTED"
            and output.get("explanation") == "NOT_CONSTRUCTED"
            and output.get("claim_scope") == "not_constructed"
            and output.get("role_plan") == expected["role_plan"]
            and output.get("boundary_conditions") == []
            and output.get("reason_codes") == expected["reason_codes"]
        )
    elif code == "base_admissibility":
        readiness = output.get("readiness", {})
        valid = (
            output.get("admissibility_schema_version")
            == expected["admissibility_schema_version"]
            and output.get("base_status") == "unclear"
            and output.get("checks") == FALSE_CHECKS
            and readiness == NO_SOURCE_READINESS
            and output.get("reason_codes") == expected["reason_codes"]
        )
    elif code == "contextual_flattening_edit":
        valid = (
            output.get("edit_schema_version") == expected["edit_schema_version"]
            and output.get("status") == "not_constructable"
            and output.get("patch") == expected["patch"]
            and output.get("reason_codes") == expected["reason_codes"]
        )
    elif code == "unsupported_abstraction_edit":
        valid = (
            output.get("edit_schema_version") == expected["edit_schema_version"]
            and output.get("status") == "not_constructable"
            and output.get("patch") == expected["patch"]
            and output.get("reason_codes") == expected["reason_codes"]
        )
    elif code == "construction_comparison":
        valid = (
            output.get("comparison_schema_version")
            == expected["comparison_schema_version"]
            and output.get("comparison_clarity") == "unclear"
            and output.get("present_flaws") == []
            and output.get("other_material_flaw") is False
            and output.get("single_material_difference") is False
            and output.get("anchors") == []
            and output.get("uncertainty_codes") == expected["uncertainty_codes"]
        )
    else:
        raise CanaryError("canary_unknown_case_layer_2_semantic_failure")

    if not valid:
        raise CanaryError(f"canary_{code}_layer_2_semantic_failure")


def run_live_canary() -> dict[str, str]:
    v1_config, assets, _ = validate_static()
    try:
        core.v1.preflight_service(v1_config)
    except Exception:
        raise CanaryError("canary_preflight_layer_1_compatibility_failure") from None
    statuses: dict[str, str] = {}
    for case in CANARY_CASES:
        request = core.v1.build_model_request(
            v1_config,
            model_role=case["model_role"],
            system_prompt=assets[case["prompt_key"]],
            user_prompt=case["user_prompt"],
            output_schema=assets[case["schema_key"]],
            rating_call=False,
            rating_repetition=None,
        )
        try:
            response = core.v1.api_json(
                v1_config["service_url"], "/api/chat", request, timeout=180
            )
            output, _ = core.v1.parse_model_response(
                response,
                expected_model=v1_config["models"][case["model_role"]]["model_id"],
                output_schema=assets[case["schema_key"]],
            )
        except Exception:
            raise CanaryError(
                f"canary_{case['code']}_layer_1_compatibility_failure"
            ) from None
        validate_case_semantics(case, output)
        statuses[case["code"]] = output[case["status_field"]]
    return statuses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dry-run", "run"))
    return parser.parse_args()


def emit(value: dict[str, Any], *, error: bool = False) -> None:
    print(json.dumps(value, sort_keys=True), file=sys.stderr if error else sys.stdout)


def main() -> int:
    args = parse_args()
    try:
        if args.command == "dry-run":
            validate_static()
            emit(
                {
                    "canary_status": "static_valid",
                    "schema_statuses": {
                        case["code"]: "schema_valid" for case in CANARY_CASES
                    },
                }
            )
            return 0
        statuses = run_live_canary()
        emit({"canary_status": "passed", "case_statuses": statuses})
        return 0
    except CanaryError as exc:
        emit({"canary_status": "failed", "failure_code": exc.code}, error=True)
        return 2
    except Exception:
        emit(
            {"canary_status": "failed", "failure_code": "canary_runtime_failure"},
            error=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
