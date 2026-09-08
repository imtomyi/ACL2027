#!/usr/bin/env python3
"""Fail-closed, source-free preflight for the complete Table 3 experiment.

The checker validates only the prospective freeze and its metadata bindings. It
does not run a reviewer, read packet contents, score truth, or create a queue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_FREEZE = (
    WORKSPACE
    / "experiments/rq2_role_prompted_llm/config/"
    "table3_formal_full_matrix_v1.template.json"
)

DATASETS = ("dreaddit", "goemotions", "cache", "parlamint_gb")
DATASET_DISPLAY_NAMES = {
    "dreaddit": "Dreaddit",
    "goemotions": "GoEmotions",
    "cache": "CaChe",
    "parlamint_gb": "ParlaMint-GB",
}
METHODS = ("generalist", "fixed_role", "all_roles", "warrantroute")
METHOD_DISPLAY_NAMES = {
    "generalist": "Generalist",
    "fixed_role": "Fixed role",
    "all_roles": "All roles",
    "warrantroute": "WarrantRoute",
}
ROLES = ("generalist", "qualitative_methods", "domain")
FIXED_ROLE = "qualitative_methods"
MODELS = ("qwen3_8b", "llama3_1_8b", "gemma3_4b")
MODEL_IDS = {
    "qwen3_8b": "qwen3:8b",
    "llama3_1_8b": "llama3.1:8b",
    "gemma3_4b": "gemma3:4b",
}
N_PER_DATASET = 100
REPETITIONS = 3
EXPECTED_PER_REPETITION = len(DATASETS) * N_PER_DATASET * len(ROLES) * len(MODELS)
EXPECTED_TOTAL_OUTPUTS = EXPECTED_PER_REPETITION * REPETITIONS
EXPECTED_TABLE_ROWS = len(DATASETS) * len(METHODS) * len(MODELS)
BASELINE_METHODS = ("generalist", "fixed_role", "all_roles")
BASELINE_TABLE_ROWS = len(DATASETS) * len(BASELINE_METHODS) * len(MODELS)
PHASES = ("baseline", "complete")
SHA256_HEX_LENGTH = 64

TOP_LEVEL_KEYS = {
    "document_type",
    "freeze_version",
    "record_status",
    "study_id",
    "frozen_at_utc",
    "frozen_by",
    "execution_authorized",
    "manuscript_eligible",
    "qualification_contract",
    "scope",
    "datasets",
    "models",
    "reviewer_freeze",
    "methods",
    "analysis",
    "governance",
    "implementation",
    "template_notice",
}


class FreezeError(RuntimeError):
    """Raised when the freeze does not even satisfy the template contract."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FreezeError(code)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreezeError("freeze_json_unreadable") from exc
    require(isinstance(value, dict), "freeze_root_not_object")
    return value


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def is_prefixed_sha256(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and is_sha256(value[7:])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_workspace_reference(value: Any, workspace: Path) -> Path | None:
    if not is_nonempty_string(value):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError:
        return None
    return resolved


def validate_static_contract(freeze: dict[str, Any]) -> None:
    require(set(freeze) == TOP_LEVEL_KEYS, "freeze_top_level_keys_invalid")
    require(
        freeze.get("document_type") == "table3_formal_full_matrix_freeze",
        "freeze_document_type_invalid",
    )
    require(
        freeze.get("freeze_version") == "table3-formal-full-matrix-v1",
        "freeze_version_invalid",
    )

    scope = freeze.get("scope")
    require(isinstance(scope, dict), "scope_not_object")
    require(scope.get("dataset_order") == list(DATASETS), "dataset_order_drift")
    require(scope.get("dataset_display_names") == DATASET_DISPLAY_NAMES, "dataset_display_name_drift")
    require(scope.get("method_order") == list(METHODS), "method_order_drift")
    require(scope.get("method_display_names") == METHOD_DISPLAY_NAMES, "method_display_name_drift")
    require(scope.get("reviewer_role_order") == list(ROLES), "reviewer_role_order_drift")
    require(scope.get("model_profile_order") == list(MODELS), "model_profile_order_drift")
    require(scope.get("n_per_dataset") == N_PER_DATASET, "sample_size_drift")
    require(scope.get("rating_repetitions") == REPETITIONS, "repetition_count_drift")
    require(
        scope.get("expected_reviewer_outputs_per_repetition") == EXPECTED_PER_REPETITION,
        "per_repetition_output_count_drift",
    )
    require(
        scope.get("expected_total_reviewer_outputs") == EXPECTED_TOTAL_OUTPUTS,
        "total_output_count_drift",
    )
    require(scope.get("expected_table_rows") == EXPECTED_TABLE_ROWS, "table_row_count_drift")
    require(set(freeze.get("datasets", {})) == set(DATASETS), "dataset_set_drift")
    require(set(freeze.get("models", {})) == set(MODELS), "model_set_drift")
    require(set(freeze.get("methods", {})) == set(METHODS), "method_set_drift")


def check_binding(
    blockers: list[str],
    *,
    label: str,
    reference: Any,
    expected_sha256: Any,
    workspace: Path,
) -> None:
    path = resolve_workspace_reference(reference, workspace)
    if path is None:
        blockers.append(f"{label}_reference_missing_or_outside_workspace")
    if not is_sha256(expected_sha256):
        blockers.append(f"{label}_sha256_missing")
    if path is None or not is_sha256(expected_sha256):
        return
    if path.is_symlink() or not path.is_file():
        blockers.append(f"{label}_file_missing_or_not_regular")
        return
    if file_sha256(path) != expected_sha256:
        blockers.append(f"{label}_sha256_mismatch")


def check_readiness_report(
    blockers: list[str],
    *,
    freeze: dict[str, Any],
    path: Path | None,
) -> None:
    if path is None or not path.is_file() or path.is_symlink():
        return
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        blockers.append("governance_readiness_report_invalid_json")
        return
    if not isinstance(report, dict):
        blockers.append("governance_readiness_report_not_object")
        return
    if report.get("all_real_corpora_ready") is not True:
        blockers.append("governance_not_all_real_corpora_ready")
    if report.get("contains_real_source_text") is not False:
        blockers.append("governance_report_contains_source_text")
    lanes = report.get("corpora")
    if not isinstance(lanes, dict):
        blockers.append("governance_corpora_missing")
        return
    for dataset_id in DATASETS:
        lane_id = freeze["datasets"][dataset_id].get("governance_lane_id")
        if not is_nonempty_string(lane_id):
            continue
        lane = lanes.get(lane_id)
        if not isinstance(lane, dict):
            blockers.append(f"{dataset_id}_governance_lane_missing")
            continue
        if lane.get("required_gate_count") != 10:
            blockers.append(f"{dataset_id}_governance_gate_requirement_invalid")
        if lane.get("completed_gate_count") != 10 or lane.get("real_text_ready") is not True:
            blockers.append(f"{dataset_id}_governance_gates_incomplete")


def check_activation_record(
    blockers: list[str],
    *,
    freeze: dict[str, Any],
    path: Path | None,
) -> None:
    if path is None or not path.is_file() or path.is_symlink():
        return
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        blockers.append("activation_record_invalid_json")
        return
    if not isinstance(record, dict):
        blockers.append("activation_record_not_object")
        return
    if record.get("document_type") != "table3_formal_activation_record":
        blockers.append("activation_record_document_type_invalid")
    if record.get("status") != "approved" or record.get("execution_authorized") is not True:
        blockers.append("activation_record_not_approved")
    if record.get("study_id") != freeze.get("study_id"):
        blockers.append("activation_record_study_id_mismatch")


def collect_blockers(
    freeze: dict[str, Any],
    workspace: Path = WORKSPACE,
    phase: str = "complete",
    allow_existing_output: bool = False,
) -> list[str]:
    require(phase in PHASES, "preflight_phase_invalid")
    validate_static_contract(freeze)
    blockers: list[str] = []

    if freeze.get("record_status") != "formal_study_frozen":
        blockers.append("study_not_formally_frozen")
    for field in ("study_id", "frozen_at_utc", "frozen_by"):
        if not is_nonempty_string(freeze.get(field)):
            blockers.append(f"{field}_missing")
    if freeze.get("execution_authorized") is not True:
        blockers.append("execution_not_authorized")
    if freeze.get("manuscript_eligible") is not False:
        blockers.append("premature_manuscript_eligibility_claim")

    contract = freeze.get("qualification_contract", {})
    check_binding(
        blockers,
        label="qualification_contract",
        reference=contract.get("path"),
        expected_sha256=contract.get("sha256"),
        workspace=workspace,
    )

    datasets = freeze["datasets"]
    for dataset_id in DATASETS:
        dataset = datasets[dataset_id]
        if not is_nonempty_string(dataset.get("governance_lane_id")):
            blockers.append(f"{dataset_id}_governance_lane_unassigned")
        for stem in (
            "development_manifest",
            "final_packet_bank",
            "final_packet_manifest",
            "private_truth_map",
            "source_cluster_map",
        ):
            check_binding(
                blockers,
                label=f"{dataset_id}_{stem}",
                reference=dataset.get(f"{stem}_reference"),
                expected_sha256=dataset.get(f"{stem}_sha256"),
                workspace=workspace,
            )
        if not is_sha256(dataset.get("packet_id_set_sha256")):
            blockers.append(f"{dataset_id}_packet_id_set_sha256_missing")
        if dataset.get("eligible_packet_count") != N_PER_DATASET:
            blockers.append(f"{dataset_id}_eligible_packet_count_not_100")
        cluster_count = dataset.get("source_cluster_count")
        if type(cluster_count) is not int or cluster_count <= 0:
            blockers.append(f"{dataset_id}_source_cluster_count_invalid")
        if dataset.get("development_final_cluster_overlap_count") != 0:
            blockers.append(f"{dataset_id}_development_final_cluster_overlap_not_zero")
        for field in ("privacy_reviewed", "cluster_disjoint", "truth_hidden_during_review"):
            if dataset.get(field) is not True:
                blockers.append(f"{dataset_id}_{field}_false")

    models = freeze["models"]
    runtime_versions: set[str] = set()
    hardware_classes: set[str] = set()
    for profile_id in MODELS:
        model = models[profile_id]
        if model.get("model_id") != MODEL_IDS[profile_id]:
            blockers.append(f"{profile_id}_model_id_drift")
        if not is_sha256(model.get("model_manifest_sha256")):
            blockers.append(f"{profile_id}_model_manifest_sha256_missing")
        for field in ("config_digest", "model_layer_digest"):
            if not is_prefixed_sha256(model.get(field)):
                blockers.append(f"{profile_id}_{field}_missing")
        if not is_nonempty_string(model.get("runtime_version")):
            blockers.append(f"{profile_id}_runtime_version_missing")
        else:
            runtime_versions.add(model["runtime_version"])
        if not is_nonempty_string(model.get("hardware_class")):
            blockers.append(f"{profile_id}_hardware_class_missing")
        else:
            hardware_classes.add(model["hardware_class"])
        minimum_context = 16384 if profile_id == "gemma3_4b" else 8192
        if type(model.get("num_ctx")) is not int or model["num_ctx"] < minimum_context:
            blockers.append(f"{profile_id}_num_ctx_below_required_minimum")
    if len(runtime_versions) > 1:
        blockers.append("runtime_version_not_shared_across_models")
    if len(hardware_classes) > 1:
        blockers.append("hardware_class_not_shared_across_models")

    reviewer = freeze.get("reviewer_freeze", {})
    prompt_suite = reviewer.get("prompt_suite", {})
    check_binding(
        blockers,
        label="prompt_suite",
        reference=prompt_suite.get("path"),
        expected_sha256=prompt_suite.get("sha256"),
        workspace=workspace,
    )
    prompts = reviewer.get("role_prompt_bindings", {})
    if set(prompts) != set(ROLES):
        blockers.append("role_prompt_binding_set_invalid")
    else:
        for role_id in ROLES:
            binding = prompts[role_id]
            check_binding(
                blockers,
                label=f"{role_id}_prompt",
                reference=binding.get("path"),
                expected_sha256=binding.get("sha256"),
                workspace=workspace,
            )
    for field in ("shared_rater_guide", "transport_schema", "postvalidation_schema"):
        binding = reviewer.get(field, {})
        check_binding(
            blockers,
            label=field,
            reference=binding.get("path"),
            expected_sha256=binding.get("sha256"),
            workspace=workspace,
        )
    if type(reviewer.get("timeout_seconds")) is not int or reviewer["timeout_seconds"] <= 0:
        blockers.append("reviewer_timeout_seconds_invalid")
    seeds = reviewer.get("repetition_seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) != REPETITIONS
        or len(set(seeds)) != REPETITIONS
        or not all(type(seed) is int for seed in seeds)
    ):
        blockers.append("repetition_seeds_invalid")
    if reviewer.get("primary_repetition") != 1:
        blockers.append("primary_repetition_drift")
    if reviewer.get("stability_rule") != "flag_present_in_at_least_two_of_three_repetitions":
        blockers.append("stability_rule_drift")

    methods = freeze["methods"]
    if methods["generalist"].get("source_roles") != ["generalist"]:
        blockers.append("generalist_method_definition_drift")
    fixed = methods["fixed_role"]
    if (
        fixed.get("selection_data") != "development_only"
        or fixed.get("selection_unit") != "all_reviewer_models_pooled"
        or fixed.get("shared_frozen_role") != FIXED_ROLE
        or fixed.get("per_model_reselection_allowed") is not False
        or fixed.get("per_dataset_reselection_allowed") is not False
        or fixed.get("test_time_reselection_allowed") is not False
    ):
        blockers.append("fixed_role_selection_boundary_invalid")
    check_binding(
        blockers,
        label="fixed_role_selection_manifest",
        reference=fixed.get("selection_manifest_reference"),
        expected_sha256=fixed.get("selection_manifest_sha256"),
        workspace=workspace,
    )
    selected_roles = fixed.get("frozen_role_by_model")
    if not isinstance(selected_roles, dict) or set(selected_roles) != set(MODELS):
        blockers.append("fixed_role_model_set_invalid")
    else:
        for profile_id in MODELS:
            if selected_roles.get(profile_id) != FIXED_ROLE:
                blockers.append(f"fixed_role_{profile_id}_not_shared")
    all_roles = methods["all_roles"]
    if all_roles.get("source_roles") != list(ROLES) or all_roles.get("composition") != "per_item_union":
        blockers.append("all_roles_method_definition_drift")
    if phase == "complete":
        route = methods["warrantroute"]
        if route.get("selection_data") != "development_only" or route.get("test_time_refitting_allowed") is not False:
            blockers.append("warrantroute_training_boundary_invalid")
        if route.get("test_truth_features_allowed") is not False:
            blockers.append("warrantroute_test_truth_feature_leakage")
        if route.get("composition") not in route.get("permitted_compositions", []):
            blockers.append("warrantroute_composition_not_frozen")
        for stem in ("policy", "policy_training_manifest", "independent_route_validator"):
            check_binding(
                blockers,
                label=f"warrantroute_{stem}",
                reference=route.get(f"{stem}_reference"),
                expected_sha256=route.get(f"{stem}_sha256"),
                workspace=workspace,
            )

    analysis = freeze.get("analysis", {})
    if phase == "complete" and analysis.get("primary_model_profile_id") not in MODELS:
        blockers.append("primary_model_profile_not_frozen")
    expected_analysis = {
        "primary_corpus_id": "cache",
        "primary_comparison": "warrantroute_vs_fixed_role",
        "primary_endpoint": "recall",
        "primary_direction": "higher_is_better",
        "bootstrap_resamples": 10000,
        "bootstrap_seed": 20270826,
        "bootstrap_unit": "frozen_source_cluster",
        "interval": "paired_cluster_percentile_95",
    }
    analysis_fields = (
        expected_analysis
        if phase == "complete"
        else {
            field: expected
            for field, expected in expected_analysis.items()
            if field.startswith("bootstrap_") or field == "interval"
        }
    )
    for field, expected in analysis_fields.items():
        if analysis.get(field) != expected:
            blockers.append(f"analysis_{field}_drift")
    judge_needed = analysis.get("report_credibility") is True or analysis.get("report_confirmability") is True
    judge = analysis.get("quality_judge", {})
    if judge_needed:
        if judge.get("enabled") is not True:
            blockers.append("quality_judge_required_but_disabled")
        if not is_nonempty_string(judge.get("judge_model_id")):
            blockers.append("quality_judge_model_id_missing")
        if not is_prefixed_sha256(judge.get("judge_model_digest")):
            blockers.append("quality_judge_model_digest_missing")
        for field in ("prompt", "binary_rule"):
            check_binding(
                blockers,
                label=f"quality_judge_{field}",
                reference=judge.get(f"{field}_reference"),
                expected_sha256=judge.get(f"{field}_sha256"),
                workspace=workspace,
            )
        if not is_nonempty_string(judge.get("human_audit_manifest_reference")):
            blockers.append("quality_judge_human_audit_manifest_missing")

    governance = freeze.get("governance", {})
    if governance.get("required_gate_count_per_dataset") != 10:
        blockers.append("governance_per_dataset_gate_count_drift")
    if governance.get("required_total_gate_count") != 40:
        blockers.append("governance_total_gate_count_drift")
    readiness_path = resolve_workspace_reference(governance.get("readiness_report_reference"), workspace)
    check_binding(
        blockers,
        label="governance_readiness_report",
        reference=governance.get("readiness_report_reference"),
        expected_sha256=governance.get("readiness_report_sha256"),
        workspace=workspace,
    )
    check_readiness_report(blockers, freeze=freeze, path=readiness_path)
    activation_path = resolve_workspace_reference(governance.get("activation_record_reference"), workspace)
    check_binding(
        blockers,
        label="activation_record",
        reference=governance.get("activation_record_reference"),
        expected_sha256=governance.get("activation_record_sha256"),
        workspace=workspace,
    )
    check_activation_record(blockers, freeze=freeze, path=activation_path)

    implementation = freeze.get("implementation", {})
    for stem in ("formal_runner", "independent_finalizer"):
        check_binding(
            blockers,
            label=stem,
            reference=implementation.get(f"{stem}_reference"),
            expected_sha256=implementation.get(f"{stem}_sha256"),
            workspace=workspace,
        )
    output_root = resolve_workspace_reference(implementation.get("output_root"), workspace)
    storage_root = (workspace / "Storage").resolve()
    if output_root is None:
        blockers.append("formal_output_root_missing_or_outside_workspace")
    else:
        try:
            output_root.relative_to(storage_root)
        except ValueError:
            blockers.append("formal_output_root_outside_storage")
        if output_root.exists() and not allow_existing_output:
            blockers.append("formal_output_root_already_exists")
    if implementation.get("overwrite_allowed") is not False:
        blockers.append("formal_overwrite_policy_invalid")
    if implementation.get("working_output_reuse_allowed") is not False:
        blockers.append("working_output_reuse_allowed")

    return sorted(set(blockers))


def build_report(
    freeze: dict[str, Any],
    workspace: Path = WORKSPACE,
    phase: str = "complete",
    allow_existing_output: bool = False,
) -> dict[str, Any]:
    blockers = collect_blockers(freeze, workspace, phase, allow_existing_output)
    method_count = len(BASELINE_METHODS) if phase == "baseline" else len(METHODS)
    table_rows = BASELINE_TABLE_ROWS if phase == "baseline" else EXPECTED_TABLE_ROWS
    return {
        "document_type": "table3_formal_full_matrix_preflight_report",
        "preflight_version": "table3-formal-full-matrix-preflight-v1",
        "status": "passed" if not blockers else "blocked",
        "phase": phase,
        "formal_execution_allowed": not blockers,
        "corpus_payload_parsed": False,
        "reviewer_calls_made": 0,
        "dataset_count": len(DATASETS),
        "method_count": method_count,
        "model_count": len(MODELS),
        "role_count": len(ROLES),
        "repetition_count": REPETITIONS,
        "n_per_dataset": N_PER_DATASET,
        "expected_reviewer_outputs_per_repetition": EXPECTED_PER_REPETITION,
        "expected_total_reviewer_outputs": EXPECTED_TOTAL_OUTPUTS,
        "expected_table_rows": table_rows,
        "blocking_reason_count": len(blockers),
        "blocking_reason_codes": blockers,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the source-free metadata freeze for the complete Table 3 run"
    )
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--phase", choices=PHASES, default="complete")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        freeze = load_json(args.freeze.resolve())
        report = build_report(freeze, phase=args.phase)
    except FreezeError as exc:
        report = {
            "document_type": "table3_formal_full_matrix_preflight_report",
            "preflight_version": "table3-formal-full-matrix-preflight-v1",
            "status": "malformed",
            "formal_execution_allowed": False,
            "corpus_payload_parsed": False,
            "reviewer_calls_made": 0,
            "error_code": str(exc),
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["formal_execution_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
