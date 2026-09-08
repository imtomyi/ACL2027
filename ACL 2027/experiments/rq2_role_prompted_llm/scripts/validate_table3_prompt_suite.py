#!/usr/bin/env python3
"""Validate the model-neutral Table 3 baseline prompt suite."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_SUITE = (
    WORKSPACE
    / "experiments/rq2_role_prompted_llm/config/table3_baseline_prompt_suite_v2.json"
)
MODELS = ("qwen3_8b", "llama3_1_8b", "gemma3_4b")
ROLES = ("generalist", "qualitative_methods", "domain")
METHODS = ("Generalist", "Fixed role", "All roles")
FIXED_ROLE = "qualitative_methods"
EXPECTED_ALLOWED_FIELDS = (
    "packet_schema_version",
    "packet_id",
    "research_question",
    "source_text_context",
    "llm_generated_qualitative_claim",
)


class PromptSuiteError(RuntimeError):
    """Raised when prompt identity or payload blinding is invalid."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PromptSuiteError(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptSuiteError("prompt_suite_unreadable") from exc
    require(isinstance(value, dict), "prompt_suite_not_object")
    return value


def resolve_asset(reference: Any) -> Path:
    require(isinstance(reference, str) and reference, "asset_reference_missing")
    candidate = Path(reference)
    if not candidate.is_absolute():
        candidate = WORKSPACE / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(WORKSPACE.resolve())
    except ValueError as exc:
        raise PromptSuiteError("asset_outside_workspace") from exc
    require(resolved.is_file() and not resolved.is_symlink(), "asset_missing_or_not_regular")
    return resolved


def validate_asset(binding: dict[str, Any], label: str) -> tuple[Path, bytes]:
    require(isinstance(binding, dict), f"{label}_binding_invalid")
    path = resolve_asset(binding.get("path") or binding.get("prompt_path"))
    expected = binding.get("sha256") or binding.get("prompt_sha256")
    require(
        isinstance(expected, str)
        and len(expected) == 64
        and all(character in "0123456789abcdef" for character in expected),
        f"{label}_sha256_invalid",
    )
    value = path.read_bytes()
    require(sha256_bytes(value) == expected, f"{label}_sha256_mismatch")
    return path, value


def validate_fixed_role_selection(binding: Any) -> dict[str, Any]:
    require(isinstance(binding, dict), "fixed_role_selection_binding_invalid")
    _, value = validate_asset(binding, "fixed_role_selection")
    try:
        selection = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptSuiteError("fixed_role_selection_invalid_json") from exc
    require(isinstance(selection, dict), "fixed_role_selection_not_object")
    require(
        selection.get("document_type")
        == "table3_fixed_role_global_development_selection",
        "fixed_role_selection_document_type_invalid",
    )
    require(selection.get("selection_data") == "development_only", "fixed_role_not_development_only")
    require(
        selection.get("selection_scope") == "shared_across_all_reviewer_models",
        "fixed_role_selection_not_global",
    )
    selected = selection.get("selected_shared_role")
    require(isinstance(selected, dict), "fixed_role_selected_shared_role_invalid")
    require(selected.get("role") == FIXED_ROLE, "fixed_role_selected_role_drift")
    require(
        selection.get("applies_to_model_profile_ids") == list(MODELS),
        "fixed_role_selection_model_set_invalid",
    )
    rule = selection.get("selection_rule")
    require(isinstance(rule, dict), "fixed_role_selection_rule_invalid")
    require(rule.get("metric") == "pooled_repetition_1_micro_recall", "fixed_role_metric_drift")
    require(rule.get("candidate_roles") == list(ROLES), "fixed_role_candidate_roles_drift")
    require(rule.get("tie_order") == list(ROLES), "fixed_role_tie_order_drift")
    require(rule.get("selection_unit") == "all_reviewer_models_pooled", "fixed_role_selection_unit_drift")
    for field in (
        "test_time_reselection_allowed",
        "per_model_reselection_allowed",
        "per_dataset_reselection_allowed",
        "bootstrap_reselection_allowed",
    ):
        require(rule.get(field) is False, f"fixed_role_{field}")
    require(selection.get("final_test_outcomes_used") is False, "fixed_role_uses_final_test")
    require(selection.get("manuscript_result") is False, "fixed_role_selection_claims_result")
    require(selection.get("manuscript_eligible") is False, "fixed_role_selection_claims_eligibility")
    require(binding.get("selected_shared_role") == FIXED_ROLE, "fixed_role_binding_role_drift")
    require(
        binding.get("applies_to_model_profile_ids") == list(MODELS),
        "fixed_role_binding_model_set_invalid",
    )
    require(binding.get("test_time_reselection_allowed") is False, "fixed_role_binding_allows_reselection")

    _, source_bytes = validate_asset(
        selection.get("source_selection_table"), "fixed_role_source_table"
    )
    rows = list(csv.DictReader(io.StringIO(source_bytes.decode("utf-8"))))
    expected_model_ids = {"qwen3:8b", "llama3.1:8b", "gemma3:4b"}
    require(len(rows) == len(ROLES) * len(MODELS), "fixed_role_source_row_count_invalid")
    require({row.get("model_id") for row in rows} == expected_model_ids, "fixed_role_source_models_invalid")
    require({row.get("role") for row in rows} == set(ROLES), "fixed_role_source_roles_invalid")
    totals = {role: {"development_tp": 0, "development_n": 0} for role in ROLES}
    seen_pairs: set[tuple[str, str]] = set()
    for row in rows:
        model_id = row.get("model_id")
        role = row.get("role")
        require((model_id, role) not in seen_pairs, "fixed_role_source_duplicate_pair")
        seen_pairs.add((str(model_id), str(role)))
        try:
            tp_text, n_text = str(row.get("tp_over_n")).split("/", 1)
            tp, denominator = int(tp_text), int(n_text)
        except (TypeError, ValueError) as exc:
            raise PromptSuiteError("fixed_role_source_score_invalid") from exc
        totals[str(role)]["development_tp"] += tp
        totals[str(role)]["development_n"] += denominator
    computed_totals = {
        role: {
            **totals[role],
            "development_recall": (
                totals[role]["development_tp"] / totals[role]["development_n"]
            ),
        }
        for role in ROLES
    }
    require(
        selection.get("candidate_role_totals") == computed_totals,
        "fixed_role_pooled_totals_mismatch",
    )
    tie_rank = {role: index for index, role in enumerate(rule["tie_order"])}
    computed_winner = max(
        ROLES,
        key=lambda role: (
            computed_totals[role]["development_recall"],
            -tie_rank[role],
        ),
    )
    require(computed_winner == FIXED_ROLE, "fixed_role_pooled_winner_drift")
    return selection


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for item in value.values():
            result.update(nested_keys(item))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(nested_keys(item))
        return result
    return set()


def project_reviewer_payload(packet: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(packet, dict), "packet_not_object")
    contract = suite["reviewer_payload_contract"]
    allowed = contract["allowed_top_level_fields"]
    required = contract["required_top_level_fields"]
    require(tuple(allowed) == EXPECTED_ALLOWED_FIELDS, "payload_allowlist_drift")
    require(tuple(required) == EXPECTED_ALLOWED_FIELDS, "payload_required_fields_drift")
    missing = [field for field in required if field not in packet]
    require(not missing, "payload_required_field_missing")
    payload = {field: packet[field] for field in allowed}
    forbidden = set(contract["forbidden_fields_at_any_depth"])
    require(not forbidden.intersection(nested_keys(payload)), "forbidden_field_in_projected_payload")
    return payload


def validate_suite(suite: dict[str, Any]) -> dict[str, Any]:
    require(suite.get("document_type") == "table3_baseline_prompt_suite", "document_type_invalid")
    require(suite.get("suite_version") == "table3-baseline-prompt-suite-v2", "suite_version_invalid")
    require(tuple(suite.get("model_profile_ids", [])) == MODELS, "model_profile_order_invalid")
    require(suite.get("model_specific_prompt_overrides_allowed") is False, "model_prompt_override_allowed")
    require(suite.get("dataset_specific_prompt_overrides_allowed") is False, "dataset_prompt_override_allowed")
    require(
        suite.get("method_prompt_mapping_shared_across_models") is True,
        "method_prompt_mapping_not_shared",
    )
    roles = suite.get("roles")
    require(isinstance(roles, dict) and tuple(roles) == ROLES, "role_order_invalid")
    prompt_hashes: dict[str, str] = {}
    for role in ROLES:
        _, value = validate_asset(roles[role], f"{role}_prompt")
        text = value.decode("utf-8")
        lowered = text.casefold()
        for forbidden_name in ("qwen", "llama", "gemma", "goemotions", "parlamint", "cache"):
            require(forbidden_name not in lowered, f"{role}_prompt_contains_model_or_dataset_name")
        require("direction-j-shared-rating-v1" in text, f"{role}_output_contract_missing")
        require("An empty" in text or "empty" in text, f"{role}_no_flaw_rule_missing")
        prompt_hashes[role] = sha256_bytes(value)
    require(len(set(prompt_hashes.values())) == len(ROLES), "role_prompts_not_distinct")

    method_plan = suite.get("method_prompt_plan")
    require(isinstance(method_plan, dict) and tuple(method_plan) == METHODS, "method_plan_invalid")
    expected_method_roles = {
        "Generalist": ["generalist"],
        "Fixed role": [FIXED_ROLE],
        "All roles": list(ROLES),
    }
    for method in METHODS:
        executed_roles = method_plan[method].get("roles_executed")
        require(executed_roles == expected_method_roles[method], f"{method.casefold().replace(' ', '_')}_method_roles_invalid")
        expected_hashes = {role: prompt_hashes[role] for role in executed_roles}
        require(
            method_plan[method].get("prompt_sha256_by_role") == expected_hashes,
            f"{method.casefold().replace(' ', '_')}_method_prompt_hash_drift",
        )
        require(method_plan[method].get("separate_method_prompt") is False, "separate_method_prompt_not_allowed")
    require(
        method_plan["Fixed role"].get("shared_role_across_models") is True,
        "fixed_role_not_shared_across_models",
    )
    validate_fixed_role_selection(suite.get("fixed_role_selection"))

    contract = suite.get("reviewer_payload_contract")
    require(isinstance(contract, dict), "payload_contract_invalid")
    require(tuple(contract.get("allowed_top_level_fields", [])) == EXPECTED_ALLOWED_FIELDS, "payload_allowlist_drift")
    require(tuple(contract.get("required_top_level_fields", [])) == EXPECTED_ALLOWED_FIELDS, "payload_required_fields_drift")
    forbidden = contract.get("forbidden_fields_at_any_depth")
    require(isinstance(forbidden, list) and len(forbidden) == len(set(forbidden)), "payload_forbidden_fields_invalid")
    required_forbidden = {
        "known_intended_flaw_type",
        "known_intended_flaw_note",
        "review_instruction",
        "answer_key",
        "target_flaw",
        "route",
        "route_assignment",
        "other_reviewer_output",
    }
    require(set(forbidden) == required_forbidden, "payload_forbidden_fields_drift")

    shared_assets = suite.get("shared_assets")
    require(isinstance(shared_assets, dict), "shared_assets_invalid")
    for label in ("rater_guide", "transport_schema", "postvalidation_schema"):
        validate_asset(shared_assets.get(label), label)
    require(suite.get("manuscript_result") is False, "prompt_suite_claims_result")
    require(suite.get("manuscript_eligible") is False, "prompt_suite_claims_eligibility")
    return {
        "status": "valid",
        "suite_version": suite["suite_version"],
        "models": list(MODELS),
        "roles": list(ROLES),
        "methods": list(METHODS),
        "method_roles": expected_method_roles,
        "fixed_role": FIXED_ROLE,
        "model_specific_prompt_overrides_allowed": False,
        "dataset_specific_prompt_overrides_allowed": False,
        "role_prompt_sha256": prompt_hashes,
        "reviewer_payload_fields": list(EXPECTED_ALLOWED_FIELDS),
    }


def build_prompt(suite: dict[str, Any], role: str, packet: dict[str, Any]) -> str:
    require(role in ROLES, "unknown_role")
    validate_suite(suite)
    payload = project_reviewer_payload(packet, suite)
    _, role_bytes = validate_asset(suite["roles"][role], f"{role}_prompt")
    _, guide_bytes = validate_asset(suite["shared_assets"]["rater_guide"], "rater_guide")
    return "\n\n".join(
        [
            role_bytes.decode("utf-8").strip(),
            "Shared rater guide:",
            guide_bytes.decode("utf-8").strip(),
            "Task payload JSON:",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            "Return exactly one JSON object and no surrounding text.",
        ]
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Table 3 prompt identity and blinding")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = validate_suite(load_json(args.suite.resolve()))
    except PromptSuiteError as exc:
        print(json.dumps({"status": "invalid", "error_code": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
