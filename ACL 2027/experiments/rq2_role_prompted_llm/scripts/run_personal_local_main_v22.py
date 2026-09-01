#!/usr/bin/env python3
"""Run the frozen v2.2 final base-admissibility interface diagnostic.

The runner is qualification-only.  It selects ten fresh Dreaddit development
packets, excludes both predecessor selection sets, and changes only the
serialization of the base-admissibility response.  Ten of ten responses must
pass transport, JSON-schema, and deterministic cross-field validation before
any semantic base label or variant is produced.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import platform
import re
import stat
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

import jsonschema


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = RQ2_ROOT.parents[1]
V21_RUNNER = SCRIPT.with_name("run_personal_local_main_v21.py")
V21_RUNNER_SHA256 = "9cf46518f47edf25b2fbaab75e58815dbcc1acb8da60bb059bc867abf8122856"
V21_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v2_compat_freeze.json"
V21_CONFIG_SHA256 = "62e4c2e4293a5acd7fe6191b519e82fe1686f389d2bc52c007aae2ea0a8152da"
V2_CORE_SHA256 = "7fbbafc74f3ad40b2041b054bb72ae84c66214c84ef882d0f3a08d21c00caa64"
DEFAULT_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v22_freeze.json"
V22_OUTPUT_ROOT = WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "v22_runs"
RUN_ID_RE = re.compile(r"rq2plv22_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}")

STATUS = "private_personal_exploratory_not_for_publication"
EVIDENCE_STATUS = "diagnostic_not_manuscript_evidence"
VERIFICATION_LABEL = "frozen_local_model_screened_not_human_ground_truth"

PRIOR_V1_SELECTION = (
    "Storage/rq2_personal_local_diagnostic/"
    "rq2pl_20260827T015148Z_8f3c1a7b/selection/dreaddit_development.json"
)
PRIOR_V1_SELECTION_SHA256 = "a38506be58b0d24d7690038243bb5bae110186eed4c88d8726cb4b0b8ff22883"
PRIOR_SHARED_SELECTION = (
    "Storage/rq2_personal_local_diagnostic/v2_runs/"
    "rq2plv2_20260827T042210Z_75d589be/selection/dreaddit_development.json"
)
PRIOR_SHARED_SELECTION_SHA256 = "f5fd72c5aa3a67b27a8bf1bbce896c20a508d5bf5cb586f28d82fd657e7c3c89"

CHECK_NAMES = (
    "all_material_claims_warranted",
    "support_roles_accurate",
    "independent_support_units_sufficient",
    "counter_roles_genuine",
    "boundary_links_consequential_and_preserved",
    "claim_scope_packet_bounded",
    "no_outside_facts",
    "no_other_material_flaw",
)
READINESS_NAMES = (
    "non_support_anchor",
    "multi_unit_support",
    "consequential_counter",
    "local_distinction",
    "bounded_claim",
)
DEFECT_REASON_CODES = {
    "material_claim_not_warranted",
    "support_role_mismatch",
    "independent_support_units_insufficient",
    "counterevidence_not_genuine",
    "boundary_condition_not_consequential_or_preserved",
    "claim_scope_not_packet_bounded",
    "outside_fact_or_overreach",
    "other_material_flaw",
}
INSUFFICIENT_REASON_CODE = "insufficient_displayed_information"

EXPECTED_CONSTRUCTION_ASSET_FILES = {
    "prompt_base_generation": "experiments/rq2_role_prompted_llm/prompts/base_generation_v2_1.md",
    "schema_base_generation": "experiments/rq2_role_prompted_llm/schemas/base_generation_v2_1.schema.json",
    "prompt_base_admissibility": "experiments/rq2_role_prompted_llm/prompts/base_admissibility_v2_2.md",
    "schema_base_admissibility": "experiments/rq2_role_prompted_llm/schemas/base_admissibility_v2_2_flat.schema.json",
    "rule_base_admissibility": "experiments/rq2_role_prompted_llm/protocol/base_admissibility_rule_v2.json",
    "rule_family_edit_contract": "experiments/rq2_role_prompted_llm/protocol/family_edit_contract_v2.json",
    "prompt_contextual_flattening_edit": "experiments/rq2_role_prompted_llm/prompts/contextual_flattening_edit_v2_1.md",
    "schema_contextual_flattening_edit": "experiments/rq2_role_prompted_llm/schemas/contextual_flattening_edit_v2_1.schema.json",
    "prompt_unsupported_abstraction_edit": "experiments/rq2_role_prompted_llm/prompts/unsupported_abstraction_edit_v2_1.md",
    "schema_unsupported_abstraction_edit": "experiments/rq2_role_prompted_llm/schemas/unsupported_abstraction_edit_v2_1.schema.json",
    "prompt_construction_comparison": "experiments/rq2_role_prompted_llm/prompts/construction_comparison_v2_1.md",
    "schema_construction_comparison": "experiments/rq2_role_prompted_llm/schemas/construction_comparison_v2_1.schema.json",
    "rule_construction_comparison_acceptance": "experiments/rq2_role_prompted_llm/protocol/construction_comparison_acceptance_rule_v2.json",
    "rule_construction_qualification_thresholds": "experiments/rq2_role_prompted_llm/protocol/construction_qualification_thresholds_v2.json",
    "frozen_v2_core_runner": "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py",
    "compat_canary": "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v21_canary.py",
    "compat_history": "experiments/rq2_role_prompted_llm/protocol/personal_local_main_v2_compat_history.json",
}
EXPECTED_INTERFACE_ASSET_FILES = {
    "transport_adapter_contract": "experiments/rq2_role_prompted_llm/protocol/base_admissibility_transport_adapter_v2_2.json",
    "transport_canary_fixtures": "experiments/rq2_role_prompted_llm/protocol/base_admissibility_canary_fixtures_v2_2.json",
    "canonical_base_admissibility_schema": "experiments/rq2_role_prompted_llm/schemas/base_admissibility_v2.schema.json",
}


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_v21() -> Any:
    if raw_sha256(V21_RUNNER) != V21_RUNNER_SHA256:
        raise SystemExit("v22_v21_runner_hash_drift")
    spec = importlib.util.spec_from_file_location(
        "rq2_personal_local_main_v21_frozen_for_v22", V21_RUNNER
    )
    if spec is None or spec.loader is None:
        raise SystemExit("v22_v21_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.CORE_RUNNER_SHA256 != V2_CORE_SHA256:
        raise SystemExit("v22_v2_core_binding_drift")
    if raw_sha256(module.CORE_RUNNER) != V2_CORE_SHA256:
        raise SystemExit("v22_v2_core_hash_drift")
    return module


v21 = load_v21()
core = v21.core
v1 = core.v1

# V2 helper writers and completeness functions are deliberately reused in a
# separate subdirectory.  No predecessor file is mutated.
core.V2_OUTPUT_ROOT = V22_OUTPUT_ROOT
core.RUN_ID_RE = RUN_ID_RE
core.SCRIPT = SCRIPT


class V22Error(RuntimeError):
    """Finite fail-closed v2.2 error."""


class FormatAdapterError(V22Error):
    """Finite cross-field transport-format failure."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise V22Error(code)


def strict_equal_v22(observed: Any, expected: Any) -> bool:
    """JSON equality that also rejects bool/int/float type substitution."""

    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            strict_equal_v22(observed[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            strict_equal_v22(left, right)
            for left, right in zip(observed, expected)
        )
    return observed == expected


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_run_id(requested: str | None) -> str:
    if requested is None:
        requested = (
            "rq2plv22_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "_"
            + v1.sha256_bytes(os.urandom(32))[:8]
        )
    require(RUN_ID_RE.fullmatch(requested) is not None, "v22_run_id_invalid")
    return requested


def resolve_bound_path(relative: str, *, allow_storage: bool) -> Path:
    path = v1.resolve_workspace_path(relative)
    if not allow_storage:
        require("Storage" not in path.relative_to(WORKSPACE).parts, "v22_static_path_in_storage")
    return path


def validate_asset_bindings(
    rows: Any, expected_files: dict[str, str]
) -> dict[str, Path]:
    require(isinstance(rows, dict) and set(rows) == set(expected_files), "v22_asset_set_mismatch")
    paths: dict[str, Path] = {}
    for key, expected_file in expected_files.items():
        row = rows.get(key)
        require(
            isinstance(row, dict)
            and set(row) == {"file", "sha256"}
            and row.get("file") == expected_file
            and isinstance(row.get("sha256"), str)
            and core.SHA_RE.fullmatch(row["sha256"]) is not None,
            f"v22_asset_binding_invalid:{key}",
        )
        path = resolve_bound_path(expected_file, allow_storage=False)
        require(path.is_file() and not path.is_symlink(), f"v22_asset_missing:{key}")
        require(raw_sha256(path) == row["sha256"], f"v22_asset_hash_mismatch:{key}")
        paths[key] = path
    return paths


def validate_v22_freeze(
    config: dict[str, Any], *, include_record_hashes: bool, config_path: Path
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Path], set[str]]:
    """Validate v2.2; dry-run mode opens no data or Storage path."""

    v1.reject_symlink_components(config_path, anchor=WORKSPACE)
    require(config_path == DEFAULT_CONFIG, "only_exact_v22_freeze_allowed")
    require(
        strict_equal_v22(config, v1.load_json(config_path)),
        "v22_config_object_file_drift",
    )
    require(raw_sha256(V21_CONFIG) == V21_CONFIG_SHA256, "v22_v21_config_hash_drift")
    baseline = v1.load_json(V21_CONFIG)
    extra_fields = {
        "predecessor_v21_config_file",
        "predecessor_v21_config_sha256",
        "predecessor_v21_runner_file",
        "predecessor_v21_runner_sha256",
        "frozen_v2_core_runner_file",
        "frozen_v2_core_runner_sha256",
        "prior_shared_development_selection_file",
        "prior_shared_development_selection_sha256",
        "prior_shared_selection_runs",
        "interface_assets",
        "live_interface_canary",
        "interface_format_gate",
        "final_interface_repair",
    }
    require(set(config) == set(baseline) | extra_fields, "v22_freeze_fields_mismatch")

    invariant_changes = {
        "document_type",
        "freeze_version",
        "created_at_utc",
        "output_root",
        "run_id_prefix",
        "construction_assets",
        "protocol_file",
        "protocol_sha256",
        "runner_file",
        "runner_sha256",
    }
    require(
        all(
            strict_equal_v22(config[key], baseline[key])
            for key in set(baseline) - invariant_changes
        ),
        "v22_inherited_semantic_invariant_drift",
    )
    require(config.get("document_type") == "rq2_personal_local_main_v22_freeze", "v22_freeze_type_mismatch")
    require(config.get("freeze_version") == "rq2-personal-local-main-v2.2", "v22_freeze_version_mismatch")
    require(config.get("created_at_utc") == "2026-08-27T00:00:00Z", "v22_freeze_timestamp_mismatch")
    require(
        config.get("output_root") == "Storage/rq2_personal_local_diagnostic/v22_runs"
        and config.get("run_id_prefix") == "rq2plv22_",
        "v22_output_namespace_mismatch",
    )
    require(config.get("qualification_only") is True, "v22_not_qualification_only")
    for key in (
        "reviewer_calls_allowed",
        "fixed_role_selection_allowed",
        "dreaddit_audit_access_allowed",
        "agyw_heldout_access_allowed",
    ):
        require(config.get(key) is False, f"v22_forbidden_capability:{key}")
    require(config.get("main_execution_requires_separate_freeze") is True, "v22_main_freeze_not_required")
    require(
        strict_equal_v22(
            config.get("development_qualification"),
            baseline["development_qualification"],
        ),
        "v22_threshold_drift",
    )
    require(
        strict_equal_v22(config.get("outcome_policy"), baseline["outcome_policy"]),
        "v22_outcome_policy_drift",
    )
    require(
        strict_equal_v22(config.get("result_labels"), baseline["result_labels"]),
        "v22_result_label_drift",
    )
    require(config.get("final_interface_repair") is True, "v22_not_final_interface_repair")
    require(
        strict_equal_v22(
            config.get("live_interface_canary"),
            {
            "required_before_data_or_storage_access": True,
            "fixture_count": 3,
            "prompt_bytes_each": 16384,
            "model_role": "verifier",
            "physical_attempts_per_fixture": 1,
            "writes_allowed": False,
            "response_content_emission_allowed": False,
            "on_failure": "stop_before_data_or_storage_without_retry",
            "sealed_resume_reexecutes_canary": False,
            },
        ),
        "v22_live_canary_policy_mismatch",
    )

    require(
        config.get("predecessor_v21_config_file")
        == "experiments/rq2_role_prompted_llm/config/personal_local_main_v2_compat_freeze.json"
        and config.get("predecessor_v21_config_sha256") == V21_CONFIG_SHA256,
        "v22_v21_config_binding_mismatch",
    )
    require(
        config.get("predecessor_v21_runner_file")
        == "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v21.py"
        and config.get("predecessor_v21_runner_sha256") == V21_RUNNER_SHA256,
        "v22_v21_runner_binding_mismatch",
    )
    require(
        config.get("frozen_v2_core_runner_file")
        == "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py"
        and config.get("frozen_v2_core_runner_sha256") == V2_CORE_SHA256,
        "v22_v2_core_binding_mismatch",
    )
    require(
        config.get("prior_v1_development_selection_file") == PRIOR_V1_SELECTION
        and config.get("prior_v1_development_selection_sha256") == PRIOR_V1_SELECTION_SHA256,
        "v22_v1_selection_binding_mismatch",
    )
    require(
        config.get("prior_shared_development_selection_file") == PRIOR_SHARED_SELECTION
        and config.get("prior_shared_development_selection_sha256")
        == PRIOR_SHARED_SELECTION_SHA256,
        "v22_shared_selection_binding_mismatch",
    )
    expected_prior_runs = [
        {
            "run_id": "rq2plv2_20260827T033053Z_4c9e7a12",
            "selection_sha256": PRIOR_SHARED_SELECTION_SHA256,
            "selection_reused": False,
            "outcomes_reused": False,
        },
        {
            "run_id": "rq2plv2_20260827T042210Z_75d589be",
            "selection_sha256": PRIOR_SHARED_SELECTION_SHA256,
            "selection_reused": False,
            "outcomes_reused": False,
        },
    ]
    require(
        strict_equal_v22(
            config.get("prior_shared_selection_runs"), expected_prior_runs
        ),
        "v22_shared_history_binding_mismatch",
    )

    interface_gate = config.get("interface_format_gate")
    require(
        strict_equal_v22(
            interface_gate,
            {
            "planned_slots": 10,
            "required_format_valid": 10,
            "transport_schema_cross_field_only": True,
            "semantic_evaluation_before_pass_allowed": False,
            "variant_calls_before_pass_allowed": False,
            "on_failure": "seal_interface_format_failed_and_stop_permanently",
            "transport_retry_allowed": False,
            "semantic_retry_allowed": False,
            "regeneration_allowed": False,
            "replacement_allowed": False,
            "manual_override_allowed": False,
            },
        ),
        "v22_interface_gate_policy_mismatch",
    )

    assets = config.get("construction_assets")
    baseline_assets = baseline["construction_assets"]
    require(isinstance(assets, dict), "v22_construction_assets_invalid")
    require(set(assets) == set(EXPECTED_CONSTRUCTION_ASSET_FILES), "v22_construction_asset_set_mismatch")
    changed_assets = {"prompt_base_admissibility", "schema_base_admissibility"}
    require(
        all(
            strict_equal_v22(assets[key], baseline_assets[key])
            for key in set(assets) - changed_assets
        ),
        "v22_nonserialization_asset_drift",
    )
    paths = validate_asset_bindings(assets, EXPECTED_CONSTRUCTION_ASSET_FILES)
    paths.update(validate_asset_bindings(config.get("interface_assets"), EXPECTED_INTERFACE_ASSET_FILES))

    protocol_path = resolve_bound_path(config["protocol_file"], allow_storage=False)
    runner_path = resolve_bound_path(config["runner_file"], allow_storage=False)
    require(
        config["protocol_file"]
        == "experiments/rq2_role_prompted_llm/protocol/personal_local_main_contract_v4.md"
        and raw_sha256(protocol_path) == config["protocol_sha256"],
        "v22_protocol_binding_mismatch",
    )
    require(
        config["runner_file"]
        == "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v22.py"
        and raw_sha256(runner_path) == config["runner_sha256"],
        "v22_runner_binding_mismatch",
    )
    paths["protocol"] = protocol_path
    paths["runner_v22"] = runner_path
    paths["output_root_v22"] = V22_OUTPUT_ROOT

    v1_config = v1.load_json(core.V1_CONFIG)
    require(raw_sha256(core.V1_CONFIG) == core.V1_FREEZE_SHA256, "v22_v1_freeze_hash_drift")
    if include_record_hashes:
        # The inherited validator checks every static contract but is invoked
        # with record hashing disabled. V2.2 then binds only the Dreaddit file
        # used by this development-only qualification. The AGYW records path is
        # neither hashed nor opened.
        v1_paths = v1.validate_freeze(
            v1_config,
            include_record_hashes=False,
            config_path=core.V1_CONFIG,
        )
        development_path = v1_paths["records_dreaddit_development"]
        require(
            development_path.is_file()
            and not development_path.is_symlink()
            and raw_sha256(development_path)
            == v1_config["lanes"]["dreaddit_development"]["records_file_sha256"],
            "v22_development_records_hash_mismatch",
        )
        paths["prior_v1_selection"] = resolve_bound_path(
            PRIOR_V1_SELECTION, allow_storage=True
        )
        paths["prior_shared_selection"] = resolve_bound_path(
            PRIOR_SHARED_SELECTION, allow_storage=True
        )
    else:
        # No dataset or Storage path is even resolved before the live canary.
        # The source-free caller needs only the frozen v1 object.
        v1_paths = {}
    excluded: set[str] = set()
    if include_record_hashes:
        excluded = load_predecessor_exclusions(paths)
    return v1_config, v1_paths, paths, excluded


def selection_commitments(
    selection: dict[str, Any], *, packet_count: int, commitment_count: int, code: str
) -> set[str]:
    require(selection.get("contains_source_text") is False, f"{code}_not_source_free")
    require(selection.get("lane") == "dreaddit_development", f"{code}_lane_mismatch")
    packets = selection.get("packets")
    require(isinstance(packets, list) and len(packets) == packet_count, f"{code}_packet_count_mismatch")
    values = [
        value
        for packet in packets
        if isinstance(packet, dict)
        for value in packet.get("selection_cluster_commitments", [])
    ]
    require(
        len(values) == commitment_count
        and len(set(values)) == commitment_count
        and all(isinstance(value, str) and core.SHA_RE.fullmatch(value) for value in values),
        f"{code}_commitment_count_mismatch",
    )
    return set(values)


def load_predecessor_exclusions(paths: dict[str, Path]) -> set[str]:
    v1_path = paths["prior_v1_selection"]
    shared_path = paths["prior_shared_selection"]
    require(raw_sha256(v1_path) == PRIOR_V1_SELECTION_SHA256, "v22_v1_selection_hash_drift")
    require(raw_sha256(shared_path) == PRIOR_SHARED_SELECTION_SHA256, "v22_shared_selection_hash_drift")
    v1_values = selection_commitments(
        v1.load_json(v1_path), packet_count=5, commitment_count=30, code="v22_v1_selection"
    )
    shared_values = selection_commitments(
        v1.load_json(shared_path), packet_count=10, commitment_count=60, code="v22_shared_selection"
    )
    require(v1_values.isdisjoint(shared_values), "v22_predecessor_selection_overlap")
    result = v1_values | shared_values
    require(len(result) == 90, "v22_predecessor_exclusion_count_mismatch")
    return result


def load_assets(paths: dict[str, Path]) -> dict[str, Any]:
    assets = core.load_assets(paths)
    assets["transport_adapter_contract"] = v1.load_json(paths["transport_adapter_contract"])
    assets["transport_canary_fixtures"] = v1.load_json(paths["transport_canary_fixtures"])
    assets["canonical_base_admissibility_schema"] = v1.load_json(
        paths["canonical_base_admissibility_schema"]
    )
    return assets


def adapt_base_admissibility_transport_v22(
    transport: dict[str, Any],
    *,
    transport_schema: dict[str, Any],
    canonical_schema: dict[str, Any],
    adapter_contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate and convert the flat transport object without semantic repair."""

    try:
        jsonschema.validate(transport, transport_schema)
    except jsonschema.ValidationError as exc:
        raise FormatAdapterError("base_admissibility_transport_schema_invalid") from exc

    interface = adapter_contract["transport_interface"]
    if transport.get(interface["required_version_field"]) != interface["required_version_value"]:
        raise FormatAdapterError("base_admissibility_transport_schema_invalid")

    check_map = adapter_contract["canonical_interface"]["check_field_map"]
    readiness_map = adapter_contract["canonical_interface"]["readiness_field_map"]
    checks = {canonical: transport[source] for source, canonical in check_map.items()}
    status = transport["base_status"]
    reasons = transport["reason_codes"]
    false_checks = sum(value is False for value in checks.values())
    if status == "admissible":
        status_valid = all(value is True for value in checks.values()) and reasons == []
    elif status == "materially_flawed":
        status_valid = false_checks >= 1 and bool(set(reasons) & DEFECT_REASON_CODES)
    elif status == "unclear":
        status_valid = false_checks >= 1 and INSUFFICIENT_REASON_CODE in reasons
    else:
        status_valid = False
    if not status_valid:
        raise FormatAdapterError("base_admissibility_status_semantics_invalid")

    readiness: dict[str, dict[str, Any]] = {}
    allowed_positions = set(
        adapter_contract["cross_field_semantics"]["readiness_pairs"]["allowed_positions"]
    )
    for canonical_name, fields in readiness_map.items():
        readiness_status = transport[fields["status"]]
        positions = transport[fields["evidence_positions"]]
        positions_valid = (
            isinstance(positions, list)
            and all(type(position) is int for position in positions)
            and len(positions) == len(set(positions))
            and set(positions) <= allowed_positions
        )
        if readiness_status == "ready":
            minimum = 2 if canonical_name == "multi_unit_support" else 1
            pair_valid = positions_valid and len(positions) >= minimum
        elif readiness_status in {"not_ready", "unclear"}:
            pair_valid = positions_valid and positions == []
        else:
            pair_valid = False
        if not pair_valid:
            raise FormatAdapterError("base_admissibility_readiness_semantics_invalid")
        readiness[canonical_name] = {
            "status": readiness_status,
            "evidence_positions": list(positions),
        }

    canonical = {
        "admissibility_schema_version": adapter_contract["canonical_interface"][
            "constant_fields"
        ]["admissibility_schema_version"],
        "base_status": status,
        "checks": checks,
        "readiness": readiness,
        "reason_codes": list(reasons),
    }
    try:
        jsonschema.validate(canonical, canonical_schema)
    except jsonschema.ValidationError as exc:
        raise FormatAdapterError("base_admissibility_canonical_schema_invalid") from exc
    return canonical


def build_source_free_canary_prompt(profile: dict[str, Any], instruction: str) -> str:
    prefix = profile["prefix"]
    atom = profile["padding_atom"]
    target = profile["target_user_prompt_bytes"]
    base = prefix + instruction + "\n"
    require(base.isascii() and atom.isascii(), "v22_canary_non_ascii")
    require(len(base.encode("ascii")) >= profile["minimum_nonpadding_instruction_bytes"], "v22_canary_instruction_too_short")
    require(len(base.encode("ascii")) <= target, "v22_canary_instruction_too_long")
    repeats = (target - len(base.encode("ascii")) + len(atom) - 1) // len(atom)
    prompt = (base + atom * repeats).encode("ascii")[:target].decode("ascii")
    require(len(prompt.encode("ascii")) == target, "v22_canary_length_invalid")
    return prompt


def validate_interface_assets(config: dict[str, Any], assets: dict[str, Any]) -> None:
    adapter = assets["transport_adapter_contract"]
    fixtures = assets["transport_canary_fixtures"]
    schema = assets["schema_base_admissibility"]
    canonical_schema = assets["canonical_base_admissibility_schema"]
    rows = config["construction_assets"] | config["interface_assets"]
    require(
        adapter.get("adapter_spec_version")
        == "rq2-base-admissibility-transport-adapter-v2.2"
        and adapter.get("semantic_change_allowed") is False,
        "v22_adapter_contract_identity_invalid",
    )
    bindings = adapter.get("bindings", {})
    require(
        bindings.get("transport_prompt") == config["construction_assets"]["prompt_base_admissibility"]
        and bindings.get("transport_schema")
        == config["construction_assets"]["schema_base_admissibility"]
        and bindings.get("canonical_schema")
        == config["interface_assets"]["canonical_base_admissibility_schema"]
        and bindings.get("canonical_semantic_rule")
        == config["construction_assets"]["rule_base_admissibility"],
        "v22_adapter_transitive_binding_invalid",
    )
    require(
        adapter.get("finite_failure_codes")
        == [
            "base_admissibility_transport_schema_invalid",
            "base_admissibility_status_semantics_invalid",
            "base_admissibility_readiness_semantics_invalid",
            "base_admissibility_canonical_schema_invalid",
        ],
        "v22_adapter_failure_codes_drift",
    )
    failure = adapter.get("failure_behavior", {})
    require(
        failure.get("fail_closed") is True
        and failure.get("semantic_retry_allowed") is False
        and failure.get("repair_allowed") is False
        and failure.get("regeneration_allowed") is False
        and failure.get("manual_override_allowed") is False
        and failure.get("partial_canonical_object_allowed") is False
        and failure.get("model_response_content_may_appear_in_failure_output") is False,
        "v22_adapter_failure_policy_drift",
    )
    invariants = adapter.get("invariants", {})
    require(
        all(
            invariants.get(key) is True
            for key in (
                "gemma_model_and_decoding_unchanged",
                "compact_base_input_unchanged",
                "canonical_decision_meaning_unchanged",
                "canonical_base_acceptance_rule_unchanged",
                "generator_assets_unchanged",
                "variant_assets_unchanged",
                "comparison_assets_unchanged",
                "qualification_thresholds_unchanged",
            )
        ),
        "v22_adapter_semantic_invariant_drift",
    )
    fixture_bindings = fixtures.get("bindings", {})
    require(
        fixture_bindings.get("transport_prompt") == rows["prompt_base_admissibility"]
        and fixture_bindings.get("transport_schema") == rows["schema_base_admissibility"]
        and fixture_bindings.get("adapter_spec") == rows["transport_adapter_contract"],
        "v22_fixture_transitive_binding_invalid",
    )
    cases = fixtures.get("fixtures")
    require(isinstance(cases, list) and len(cases) == 3, "v22_fixture_count_invalid")
    require(
        {case.get("code") for case in cases}
        == {
            "admissible_all_true_all_ready",
            "materially_flawed_all_false_all_not_ready",
            "unclear_all_false_all_unclear",
        },
        "v22_fixture_coverage_invalid",
    )
    for case in cases:
        build_source_free_canary_prompt(fixtures["source_free_prompt_profile"], case["canary_instruction"])
        converted = adapt_base_admissibility_transport_v22(
            case["transport_output"],
            transport_schema=schema,
            canonical_schema=canonical_schema,
            adapter_contract=adapter,
        )
        require(
            strict_equal_v22(converted, case["canonical_output"]),
            "v22_fixture_conversion_drift",
        )


def canonical_canary_call_id(case_code: str) -> str:
    require(
        case_code
        in {
            "admissible_all_true_all_ready",
            "materially_flawed_all_false_all_not_ready",
            "unclear_all_false_all_unclear",
        },
        "v22_canary_case_unknown",
    )
    return f"v22_source_free_canary_{case_code}"


def prepare_live_interface_canary_v22(
    v1_config: dict[str, Any], assets: dict[str, Any]
) -> list[dict[str, Any]]:
    fixture_doc = assets["transport_canary_fixtures"]
    profile = fixture_doc["source_free_prompt_profile"]
    fixtures = fixture_doc["fixtures"]
    require(len(fixtures) == 3, "v22_canary_fixture_count_invalid")
    prepared: list[dict[str, Any]] = []
    for case in fixtures:
        code = case["code"]
        call_id = canonical_canary_call_id(code)
        prompt = build_source_free_canary_prompt(profile, case["canary_instruction"])
        request = v1.build_model_request(
            v1_config,
            model_role="verifier",
            system_prompt=assets["prompt_base_admissibility"],
            user_prompt=prompt,
            output_schema=assets["schema_base_admissibility"],
            rating_call=False,
            rating_repetition=None,
        )
        require(
            request.get("model") == v1_config["models"]["verifier"]["model_id"]
            and request.get("stream") is False
            and request.get("tools") is None
            and request.get("think") is False,
            "v22_canary_request_contract_invalid",
        )
        prepared.append({"case": case, "call_id": call_id, "request": request})
    require(
        len({row["call_id"] for row in prepared}) == len(prepared) == 3,
        "v22_canary_call_id_set_invalid",
    )
    return prepared


def expected_live_canary_evidence_v22(
    v1_config: dict[str, Any], assets: dict[str, Any]
) -> dict[str, Any]:
    prepared = prepare_live_interface_canary_v22(v1_config, assets)
    request_hashes = [
        v1.sha256_bytes(v1.canonical_bytes(row["request"])) for row in prepared
    ]
    require(len(request_hashes) == 3, "v22_canary_request_hash_count_invalid")
    call_ids = [row["call_id"] for row in prepared]
    return {
        "document_type": "rq2_personal_local_v22_live_interface_canary_evidence",
        "status": "passed",
        "case_count": 3,
        "logical_calls": 3,
        "physical_attempts": 3,
        "required_prompt_bytes_each": 16384,
        "call_id_set_sha256": v1.sha256_bytes(v1.canonical_bytes(sorted(call_ids))),
        "request_set_sha256": v1.sha256_bytes(v1.canonical_bytes(request_hashes)),
        "fixture_asset_sha256": raw_sha256(
            RQ2_ROOT / "protocol" / "base_admissibility_canary_fixtures_v2_2.json"
        ),
        "model_role": "verifier",
        "model_id": v1_config["models"]["verifier"]["model_id"],
        "one_attempt_per_case": True,
        "model_content_retained": False,
        "writes_artifacts": False,
        "data_or_storage_opened": False,
        "contains_source_text": False,
        "contains_base_status_labels": False,
        "contains_readiness_labels": False,
        "contains_reason_codes_from_model": False,
    }


def run_live_interface_canary_v22(
    v1_config: dict[str, Any], assets: dict[str, Any]
) -> dict[str, Any]:
    """Run three source-free Gemma interface calls without writes or logging."""

    prepared = prepare_live_interface_canary_v22(v1_config, assets)
    for row in prepared:
        case = row["case"]
        code = case["code"]
        request = row["request"]
        try:
            response = v1.api_json(
                v1_config["service_url"], "/api/chat", request, timeout=180
            )
            transport, _ = v1.parse_model_response(
                response,
                expected_model=v1_config["models"]["verifier"]["model_id"],
                output_schema=assets["schema_base_admissibility"],
            )
        except Exception:
            raise V22Error(f"v22_canary_case_{code}_transport_or_schema_failed") from None
        try:
            canonical = adapt_base_admissibility_transport_v22(
                transport,
                transport_schema=assets["schema_base_admissibility"],
                canonical_schema=assets["canonical_base_admissibility_schema"],
                adapter_contract=assets["transport_adapter_contract"],
            )
        except FormatAdapterError:
            raise V22Error(f"v22_canary_case_{code}_cross_field_failed") from None
        if not strict_equal_v22(canonical, case["canonical_output"]):
            raise V22Error(f"v22_canary_case_{code}_exact_fixture_failed")
    return expected_live_canary_evidence_v22(v1_config, assets)


def canary_evidence_sha256(evidence: dict[str, Any]) -> str:
    require(
        evidence.get("status") == "passed"
        and type(evidence.get("case_count")) is int
        and evidence.get("case_count") == 3
        and type(evidence.get("logical_calls")) is int
        and evidence.get("logical_calls") == 3
        and type(evidence.get("physical_attempts")) is int
        and evidence.get("physical_attempts") == 3
        and evidence.get("one_attempt_per_case") is True
        and evidence.get("model_content_retained") is False
        and evidence.get("writes_artifacts") is False
        and evidence.get("data_or_storage_opened") is False
        and evidence.get("contains_source_text") is False,
        "v22_canary_pass_evidence_invalid",
    )
    return v1.sha256_bytes(v1.canonical_bytes(evidence))


def canary_contract_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "passed",
        "case_count": 3,
        "evidence_sha256": canary_evidence_sha256(evidence),
        "contains_source_text": False,
    }


def validate_canary_contract_summary(summary: Any) -> dict[str, Any]:
    require(
        isinstance(summary, dict)
        and set(summary)
        == {"status", "case_count", "evidence_sha256", "contains_source_text"}
        and summary.get("status") == "passed"
        and type(summary.get("case_count")) is int
        and summary.get("case_count") == 3
        and isinstance(summary.get("evidence_sha256"), str)
        and core.SHA_RE.fullmatch(summary["evidence_sha256"]) is not None
        and summary.get("contains_source_text") is False,
        "v22_canary_contract_summary_invalid",
    )
    return summary


def validate_bound_canary_contract_summary(
    summary: Any, v1_config: dict[str, Any], assets: dict[str, Any]
) -> dict[str, Any]:
    observed = validate_canary_contract_summary(summary)
    expected = canary_contract_summary(
        expected_live_canary_evidence_v22(v1_config, assets)
    )
    require(
        strict_equal_v22(observed, expected),
        "v22_canary_bound_evidence_hash_mismatch",
    )
    return observed


def expected_boundary_evidence_v22(
    v1_config: dict[str, Any], live_canary_summary: dict[str, Any]
) -> dict[str, Any]:
    """Return the only boundary record permitted by the v2.2 freeze."""

    summary = validate_canary_contract_summary(live_canary_summary)
    return {
        "readiness_scope_assessment_status": "passed",
        "readiness_scope_assessment_only": True,
        "readiness_report_sha256": v1_config["readiness_report_file_sha256"],
        "policy_boundary_status": "static_boundary_passed",
        "policy_validator_executed": False,
        "policy_validator_sha256": v1_config["policy_validator_file_sha256"],
        "policy_sha256": v1_config["policy_file_sha256"],
        "dreaddit_development_record_hash_verified": True,
        "agyw_record_opened": False,
        "live_interface_canary_passed_before_data_access": True,
        "live_interface_canary_evidence_sha256": summary["evidence_sha256"],
        "v1_runner_hash_verified_before_import": True,
        "v2_core_hash_verified_before_import": True,
        "v21_adapter_hash_verified_before_import": True,
        "v1_results_reused": False,
        "prior_v2_v21_results_reused": False,
        "prior_selection_commitments_used_only_for_exclusion": True,
        "prior_excluded_commitment_count": 90,
        "qualification_only": True,
        "contains_source_text": False,
    }


def expected_v22_interface_contract(
    config: dict[str, Any], run_id: str, live_canary_summary: dict[str, Any]
) -> dict[str, Any]:
    """Build the exact immutable interface contract for one run."""

    return {
        "document_type": "rq2_personal_local_v22_interface_contract",
        "run_id": run_id,
        "v22_runner_sha256": config["runner_sha256"],
        "v21_runner_sha256": V21_RUNNER_SHA256,
        "v21_config_sha256": V21_CONFIG_SHA256,
        "v2_core_runner_sha256": V2_CORE_SHA256,
        "prior_v1_selection_sha256": PRIOR_V1_SELECTION_SHA256,
        "prior_shared_selection_sha256": PRIOR_SHARED_SELECTION_SHA256,
        "predecessor_commitments_excluded": 90,
        "fresh_packet_count": 10,
        "required_format_valid": 10,
        "live_interface_canary": validate_canary_contract_summary(
            live_canary_summary
        ),
        "semantic_evaluation_before_format_pass_allowed": False,
        "variant_calls_before_format_pass_allowed": False,
        "transport_retry_allowed": False,
        "semantic_retry_allowed": False,
        "replacement_allowed": False,
        "manual_override_allowed": False,
        "reviewer_calls_allowed": False,
        "fixed_role_selection_allowed": False,
        "dreaddit_audit_access_allowed": False,
        "agyw_heldout_access_allowed": False,
        "contains_source_text": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
    }


def validate_service_contract_v22(
    service: Any, v1_config: dict[str, Any]
) -> dict[str, Any]:
    """Validate stored service identity without contacting the service."""

    require(
        isinstance(service, dict)
        and set(service)
        == {"ollama_version", "endpoint", "endpoint_is_numeric_loopback", "models"}
        and service.get("ollama_version") == v1_config["ollama_version"]
        and service.get("endpoint") == v1_config["service_url"]
        and service.get("endpoint_is_numeric_loopback") is True,
        "v22_core_service_contract_invalid",
    )
    models = service.get("models")
    require(
        isinstance(models, dict) and set(models) == set(v1_config["models"]),
        "v22_core_service_models_invalid",
    )
    for role, frozen in v1_config["models"].items():
        observed = models.get(role)
        require(
            isinstance(observed, dict)
            and set(observed) == {"model_id", "digest", "size"}
            and observed.get("model_id") == frozen["model_id"]
            and isinstance(observed.get("digest"), str)
            and observed["digest"].removeprefix("sha256:")
            == frozen["local_manifest_file_sha256"]
            and isinstance(observed.get("size"), int)
            and not isinstance(observed["size"], bool)
            and observed["size"] > 0,
            f"v22_core_service_model_invalid:{role}",
        )
    return service


def validate_v22_interface_contract(
    contract: Any,
    config: dict[str, Any],
    run_id: str,
    v1_config: dict[str, Any],
    assets: dict[str, Any],
) -> dict[str, Any]:
    """Require the complete interface contract, not only its canary field."""

    require(isinstance(contract, dict), "v22_interface_contract_not_object")
    summary = validate_bound_canary_contract_summary(
        contract.get("live_interface_canary"), v1_config, assets
    )
    expected = expected_v22_interface_contract(config, run_id, summary)
    require(
        strict_equal_v22(contract, expected),
        "v22_interface_contract_immutable_drift",
    )
    return summary


def validate_core_run_contract_v22(
    contract: Any,
    run_dir: Path,
    config: dict[str, Any],
    v1_config: dict[str, Any],
    live_canary_summary: dict[str, Any],
) -> dict[str, Any]:
    """Require all immutable core-contract fields and v2.2 boundaries."""

    require(isinstance(contract, dict), "v22_core_contract_not_object")
    expected_fields = {
        "document_type",
        "run_id",
        "result_label",
        "evidence_status",
        "created_at_utc",
        "v2_freeze_sha256",
        "v1_freeze_sha256",
        "v2_runner_sha256",
        "v1_runner_sha256",
        "policy_sha256",
        "python_version",
        "service",
        "boundary_checks",
        "lane_packet_counts",
        "qualification_only",
        "reviewer_calls_allowed",
        "fixed_role_selection_allowed",
        "dreaddit_audit_access_allowed",
        "agyw_heldout_access_allowed",
        "main_execution_requires_separate_freeze",
        "flaw_families",
        "development_qualification",
        "outcome_policy",
        "v1_results_reused",
        "transport",
        "this_manifest_contains_source_text",
        "sealed_run_contains_restricted_source_text",
        "manuscript_eligible",
        "publication_or_release_eligible",
        "confirmatory_claims_allowed",
    }
    require(set(contract) == expected_fields, "v22_core_contract_fields_mismatch")
    created_at = contract.get("created_at_utc")
    require(
        isinstance(created_at, str)
        and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            created_at,
        )
        is not None,
        "v22_core_contract_created_at_invalid",
    )
    python_version = contract.get("python_version")
    require(
        isinstance(python_version, str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_version) is not None,
        "v22_core_contract_python_version_invalid",
    )
    service = validate_service_contract_v22(contract.get("service"), v1_config)
    expected_boundary = expected_boundary_evidence_v22(
        v1_config, live_canary_summary
    )
    require(
        strict_equal_v22(contract.get("boundary_checks"), expected_boundary),
        "v22_core_contract_boundary_drift",
    )
    v22_snapshot = run_dir / "v2_freeze_snapshot.json"
    v1_snapshot = run_dir / "v1_freeze_snapshot.json"
    policy_snapshot = run_dir / "policy_snapshot.json"
    expected = {
        "document_type": "rq2_personal_local_v2_run_contract",
        "run_id": run_dir.name,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "created_at_utc": created_at,
        "v2_freeze_sha256": v1.sha256_file(v22_snapshot),
        "v1_freeze_sha256": v1.sha256_file(v1_snapshot),
        "v2_runner_sha256": config["runner_sha256"],
        "v1_runner_sha256": core.V1_RUNNER_SHA256,
        "policy_sha256": v1.sha256_file(policy_snapshot),
        "python_version": python_version,
        "service": service,
        "boundary_checks": expected_boundary,
        "lane_packet_counts": config["lane_packet_counts"],
        "qualification_only": True,
        "reviewer_calls_allowed": False,
        "fixed_role_selection_allowed": False,
        "dreaddit_audit_access_allowed": False,
        "agyw_heldout_access_allowed": False,
        "main_execution_requires_separate_freeze": True,
        "flaw_families": list(core.FAMILY_ORDER),
        "development_qualification": config["development_qualification"],
        "outcome_policy": config["outcome_policy"],
        "v1_results_reused": False,
        "transport": "numeric_loopback_ollama_only",
        "this_manifest_contains_source_text": False,
        "sealed_run_contains_restricted_source_text": True,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    require(
        strict_equal_v22(contract, expected),
        "v22_core_contract_immutable_drift",
    )
    require(
        expected["v2_freeze_sha256"] == raw_sha256(DEFAULT_CONFIG)
        and expected["v1_freeze_sha256"] == raw_sha256(core.V1_CONFIG)
        and expected["policy_sha256"] == v1_config["policy_file_sha256"],
        "v22_core_contract_snapshot_binding_drift",
    )
    return expected_boundary


def validate_run_canary_cross_binding_v22(
    run_dir: Path,
    config: dict[str, Any],
    *,
    v1_config: dict[str, Any] | None = None,
    assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-bind the deterministic canary pass in both immutable contracts."""

    if v1_config is None or assets is None:
        static_v1_config, _, static_paths, _ = validate_v22_freeze(
            config,
            include_record_hashes=False,
            config_path=DEFAULT_CONFIG,
        )
        static_assets = load_assets(static_paths)
    else:
        static_v1_config = v1_config
        static_assets = assets
    interface_contract = v1.load_json(run_dir / "v22_interface_contract.json")
    require(
        isinstance(interface_contract, dict)
        and interface_contract.get("run_id") == run_dir.name,
        "v22_canary_interface_contract_run_id_mismatch",
    )
    summary = validate_v22_interface_contract(
        interface_contract,
        config,
        run_dir.name,
        static_v1_config,
        static_assets,
    )
    core_contract = v1.load_json(run_dir / "run_contract.json")
    require(
        isinstance(core_contract, dict)
        and core_contract.get("run_id") == run_dir.name,
        "v22_canary_core_contract_run_id_mismatch",
    )
    core_boundary = core_contract.get("boundary_checks")
    require(
        isinstance(core_boundary, dict)
        and core_boundary.get("live_interface_canary_passed_before_data_access")
        is True,
        "v22_canary_core_pass_flag_mismatch",
    )
    require(
        core_boundary.get("live_interface_canary_evidence_sha256")
        == summary["evidence_sha256"],
        "v22_canary_core_evidence_hash_mismatch",
    )
    boundary = validate_core_run_contract_v22(
        core_contract, run_dir, config, static_v1_config, summary
    )
    require(
        boundary["live_interface_canary_passed_before_data_access"] is True,
        "v22_canary_core_pass_flag_mismatch",
    )
    require(
        boundary["live_interface_canary_evidence_sha256"]
        == summary["evidence_sha256"],
        "v22_canary_core_evidence_hash_mismatch",
    )
    return summary


def select_lane_packets_v22(
    v1_config: dict[str, Any],
    v22_config: dict[str, Any],
    run_dir: Path,
    records: Sequence[dict[str, Any]],
    *,
    excluded_commitments: set[str],
) -> tuple[list[dict[str, Any]], set[str]]:
    require(len(excluded_commitments) == 90, "v22_exclusion_denominator_invalid")
    lane_name = "dreaddit_development"
    lane = v1_config["lanes"][lane_name]
    filtered = [
        row
        for row in records
        if core.cluster_commitment(row, lane["corpus"]) not in excluded_commitments
    ]
    plan = v1.deterministic_packet_plan(
        filtered,
        lane_name=lane_name,
        lane=lane,
        seed=int(v1_config["sampling_seed"]),
        packet_count=10,
        excerpts_per_packet=int(v1_config["excerpts_per_packet"]),
    )
    packets = [v1.source_free_selection_record(packet) for packet in plan]
    commitments = {
        value for packet in packets for value in packet["selection_cluster_commitments"]
    }
    require(len(plan) == 10 and len(commitments) == 60, "v22_fresh_selection_count_invalid")
    require(commitments.isdisjoint(excluded_commitments), "v22_predecessor_commitment_overlap")
    selection = {
        "document_type": "rq2_personal_local_v22_selection_commitments",
        "lane": lane_name,
        "corpus": lane["corpus"],
        "split": lane["split"],
        "base_packet_count": 10,
        "excerpts_per_packet": v1_config["excerpts_per_packet"],
        "excluded_prior_v1_commitment_count": 30,
        "excluded_prior_shared_v2_v21_commitment_count": 60,
        "excluded_total_commitment_count": 90,
        "prior_selection_or_outcome_reused": False,
        "packets": packets,
        "contains_source_text": False,
        "result_label": STATUS,
    }
    core.write_v2_json(run_dir / "selection" / f"{lane_name}.json", selection)
    return plan, commitments


def initialize_run_v22(
    config: dict[str, Any],
    config_path: Path,
    v1_config: dict[str, Any],
    v1_paths: dict[str, Path],
    run_id: str,
    service: dict[str, Any],
    boundary_evidence: dict[str, Any],
    live_canary_summary: dict[str, Any],
) -> Path:
    run_dir = core.initialize_run_v2(
        config,
        config_path,
        v1_config,
        v1_paths,
        run_id,
        service,
        boundary_evidence,
    )
    contract = expected_v22_interface_contract(
        config, run_id, live_canary_summary
    )
    core.write_v2_json(run_dir / "v22_interface_contract.json", contract)
    return run_dir


FORMAT_CODES = {
    "format_valid",
    "base_generation_terminal",
    "base_construction_unavailable",
    "base_gate_transport_terminal",
    "base_admissibility_transport_schema_invalid",
    "base_admissibility_status_semantics_invalid",
    "base_admissibility_readiness_semantics_invalid",
    "base_admissibility_canonical_schema_invalid",
}

FORMAT_GATE_FIELDS = {
    "document_type",
    "scope",
    "planned_slots",
    "prerequisite_ready",
    "base_gate_attempted",
    "transport_completed",
    "transport_schema_valid",
    "cross_field_valid",
    "format_valid",
    "required_format_valid",
    "format_code_counts",
    "passed",
    "run_outcome_if_terminal",
    "semantic_evaluation_started",
    "variant_calls_started",
    "reviewer_calls",
    "fixed_role_selected",
    "dreaddit_audit_opened",
    "agyw_heldout_opened",
    "retry_or_replacement_used",
    "contains_source_text",
    "contains_base_status_labels",
    "contains_readiness_labels",
    "contains_reason_codes_from_model",
    "result_label",
    "evidence_status",
    "manuscript_eligible",
    "publication_or_release_eligible",
}

PRE_SEMANTIC_FORBIDDEN_KEYS = {
    "transport_schema_version",
    "admissibility_schema_version",
    "base_status",
    "checks",
    "status",
    "readiness",
    "reason_codes",
    "canonical_output",
    "canonical_gate_output",
    "output",
    "admitted",
    "semantic_status",
    "semantic_label",
    "semantic_labels",
    "evidence_positions",
    "gate_status",
    "rows",
    "construction_status",
    "verification_status",
    "comparison_schema_version",
    "comparison_clarity",
    "accepted",
    "present_flaws",
    "other_material_flaw",
    "single_material_difference",
    "anchors",
    "flaw_family",
    "interpretation_fields",
    "reason_code",
    "uncertainty_codes",
    "funnel",
    "qualification_gate",
    "family_checks",
    *CHECK_NAMES,
    *(f"check_{name}" for name in CHECK_NAMES),
    *READINESS_NAMES,
    *(f"{name}_status" for name in READINESS_NAMES),
    *(f"{name}_positions" for name in READINESS_NAMES),
}

PRE_SEMANTIC_FORBIDDEN_VALUES = {
    "admissible",
    "materially_flawed",
    "unclear",
    "ready",
    "not_ready",
    "admitted",
    "base_gate_unclear",
    "base_gate_rejected",
    "constructed_pending_gate",
    "semantic_invalid",
    "generator_not_constructable",
    "base_gate_terminal",
    "generation_terminal",
    "not_constructable",
    "rq2-base-admissibility-flat-v2.2",
    "rq2-base-admissibility-v2",
    "rq2-construction-comparison-v2.1",
    "clear",
    "qualification_passed",
    "qualification_failed",
    *core.FAMILY_ORDER,
    *core.TARGET_REASON_CODE.values(),
    "insufficient_displayed_context",
    "diff_not_semantically_clear",
    "multiple_plausible_classifications",
    "anchor_not_identifiable",
    "base_seal_or_diff_incomplete",
    *DEFECT_REASON_CODES,
    INSUFFICIENT_REASON_CODE,
}


def reject_pre_semantic_payload_v22(value: Any) -> None:
    """Recursively reject semantic labels from source-free gate artifacts."""

    if isinstance(value, dict):
        require(
            not (set(value) & PRE_SEMANTIC_FORBIDDEN_KEYS),
            "v22_pre_semantic_artifact_contains_forbidden_key",
        )
        for child in value.values():
            reject_pre_semantic_payload_v22(child)
    elif isinstance(value, list):
        for child in value:
            reject_pre_semantic_payload_v22(child)
    elif isinstance(value, str):
        require(
            value not in PRE_SEMANTIC_FORBIDDEN_VALUES,
            "v22_pre_semantic_artifact_contains_forbidden_value",
        )


def validate_interface_format_gate_v22(
    gate: Any, *, expected_passed: bool | None = None
) -> dict[str, Any]:
    """Validate the exact source-free aggregate emitted before semantics."""

    require(
        isinstance(gate, dict) and set(gate) == FORMAT_GATE_FIELDS,
        "v22_format_gate_fields_mismatch",
    )
    require(
        gate.get("document_type")
        == "rq2_personal_local_v22_interface_format_gate"
        and gate.get("scope")
        == "ten_fresh_dreaddit_development_base_admissibility_slots"
        and type(gate.get("planned_slots")) is int
        and gate.get("planned_slots") == 10
        and type(gate.get("required_format_valid")) is int
        and gate.get("required_format_valid") == 10,
        "v22_format_gate_identity_drift",
    )
    count_fields = (
        "prerequisite_ready",
        "base_gate_attempted",
        "transport_completed",
        "transport_schema_valid",
        "cross_field_valid",
        "format_valid",
    )
    require(
        all(
            isinstance(gate.get(key), int)
            and not isinstance(gate[key], bool)
            and 0 <= gate[key] <= 10
            for key in count_fields
        ),
        "v22_format_gate_count_invalid",
    )
    counts = gate.get("format_code_counts")
    require(
        isinstance(counts, dict)
        and counts
        and set(counts) <= FORMAT_CODES
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
            for value in counts.values()
        )
        and sum(counts.values()) == 10,
        "v22_format_gate_code_counts_invalid",
    )
    expected_prerequisite = 10 - counts.get("base_generation_terminal", 0) - counts.get(
        "base_construction_unavailable", 0
    )
    expected_transport_completed = (
        counts.get("base_admissibility_transport_schema_invalid", 0)
        + counts.get("base_admissibility_status_semantics_invalid", 0)
        + counts.get("base_admissibility_readiness_semantics_invalid", 0)
        + counts.get("base_admissibility_canonical_schema_invalid", 0)
        + counts.get("format_valid", 0)
    )
    expected_transport_schema_valid = (
        counts.get("base_admissibility_status_semantics_invalid", 0)
        + counts.get("base_admissibility_readiness_semantics_invalid", 0)
        + counts.get("base_admissibility_canonical_schema_invalid", 0)
        + counts.get("format_valid", 0)
    )
    expected_valid = counts.get("format_valid", 0)
    require(
        gate["prerequisite_ready"] == expected_prerequisite
        and gate["base_gate_attempted"] == expected_prerequisite
        and gate["transport_completed"] == expected_transport_completed
        and gate["transport_schema_valid"] == expected_transport_schema_valid
        and gate["cross_field_valid"] == expected_valid
        and gate["format_valid"] == expected_valid,
        "v22_format_gate_count_reconciliation_drift",
    )
    passed = expected_valid == 10
    require(
        gate.get("passed") is passed
        and gate.get("run_outcome_if_terminal")
        == (None if passed else "interface_format_failed")
        and gate.get("semantic_evaluation_started") is False
        and gate.get("variant_calls_started") is False
        and type(gate.get("reviewer_calls")) is int
        and gate.get("reviewer_calls") == 0
        and gate.get("fixed_role_selected") is False
        and gate.get("dreaddit_audit_opened") is False
        and gate.get("agyw_heldout_opened") is False
        and gate.get("retry_or_replacement_used") is False
        and gate.get("contains_source_text") is False
        and gate.get("contains_base_status_labels") is False
        and gate.get("contains_readiness_labels") is False
        and gate.get("contains_reason_codes_from_model") is False
        and gate.get("result_label") == STATUS
        and gate.get("evidence_status") == EVIDENCE_STATUS
        and gate.get("manuscript_eligible") is False
        and gate.get("publication_or_release_eligible") is False,
        "v22_format_gate_boundary_drift",
    )
    if expected_passed is not None:
        require(
            passed is expected_passed,
            "v22_format_gate_unexpected_outcome",
        )
    reject_pre_semantic_payload_v22(gate)
    return gate


def expected_terminal_status_v22(run_id: str, run_outcome: str) -> dict[str, Any]:
    """Build the exact terminal record for each v2.2 outcome."""

    require(
        run_outcome
        in {"interface_format_failed", "qualification_failed", "qualification_passed"},
        "v22_terminal_outcome_invalid",
    )
    format_passed = run_outcome != "interface_format_failed"
    future_eligible = run_outcome == "qualification_passed"
    return {
        "document_type": "rq2_personal_local_v22_terminal_status",
        "run_id": run_id,
        "run_outcome": run_outcome,
        "format_gate_passed": format_passed,
        "semantic_evaluation_started": format_passed,
        "qualification_only": True,
        "permanent_stop": True,
        "same_run_continuation_allowed": False,
        "continuation_allowed": False,
        "separate_future_freeze_eligible": future_eligible,
        "continuation_requires_separate_bound_v2_main_freeze": future_eligible,
        "contains_source_text": False,
        "result_label": STATUS,
    }


def validate_terminal_status_v22(
    terminal: Any, run_id: str, run_outcome: str
) -> dict[str, Any]:
    require(
        strict_equal_v22(
            terminal, expected_terminal_status_v22(run_id, run_outcome)
        ),
        "v22_terminal_status_immutable_drift",
    )
    if run_outcome == "interface_format_failed":
        reject_pre_semantic_payload_v22(terminal)
    return terminal


SELECTION_FIELDS = {
    "document_type",
    "lane",
    "corpus",
    "split",
    "base_packet_count",
    "excerpts_per_packet",
    "excluded_prior_v1_commitment_count",
    "excluded_prior_shared_v2_v21_commitment_count",
    "excluded_total_commitment_count",
    "prior_selection_or_outcome_reused",
    "packets",
    "contains_source_text",
    "result_label",
}

SELECTION_PACKET_FIELDS = {
    "packet_index",
    "packet_id",
    "bootstrap_cluster_id",
    "record_id_commitment",
    "selection_cluster_commitments",
    "record_count",
}


def validate_selection_v22(
    selection: Any,
    v1_config: dict[str, Any],
    excluded_commitments: set[str],
) -> set[str]:
    """Validate the exact source-free fresh-selection commitment artifact."""

    lane = v1_config["lanes"]["dreaddit_development"]
    require(
        isinstance(selection, dict) and set(selection) == SELECTION_FIELDS,
        "v22_selection_fields_mismatch",
    )
    require(
        selection.get("document_type")
        == "rq2_personal_local_v22_selection_commitments"
        and selection.get("lane") == "dreaddit_development"
        and selection.get("corpus") == lane["corpus"] == "dreaddit"
        and selection.get("split") == lane["split"]
        and type(selection.get("base_packet_count")) is int
        and selection.get("base_packet_count") == 10
        and type(selection.get("excerpts_per_packet")) is int
        and selection.get("excerpts_per_packet") == 6
        and selection.get("excerpts_per_packet")
        == v1_config["excerpts_per_packet"]
        and type(selection.get("excluded_prior_v1_commitment_count")) is int
        and selection.get("excluded_prior_v1_commitment_count") == 30
        and type(
            selection.get("excluded_prior_shared_v2_v21_commitment_count")
        )
        is int
        and selection.get("excluded_prior_shared_v2_v21_commitment_count") == 60
        and type(selection.get("excluded_total_commitment_count")) is int
        and selection.get("excluded_total_commitment_count") == 90
        and selection.get("prior_selection_or_outcome_reused") is False
        and selection.get("contains_source_text") is False
        and selection.get("result_label") == STATUS,
        "v22_selection_identity_or_boundary_drift",
    )
    packets = selection.get("packets")
    require(
        isinstance(packets, list) and len(packets) == 10,
        "v22_selection_packet_count_invalid",
    )
    packet_ids: set[str] = set()
    commitments: list[str] = []
    for expected_index, packet in enumerate(packets, 1):
        require(
            isinstance(packet, dict) and set(packet) == SELECTION_PACKET_FIELDS,
            "v22_selection_packet_fields_mismatch",
        )
        packet_id = packet.get("packet_id")
        packet_commitments = packet.get("selection_cluster_commitments")
        require(
            type(packet.get("packet_index")) is int
            and packet.get("packet_index") == expected_index
            and isinstance(packet_id, str)
            and re.fullmatch(r"PKT_[0-9a-f]{16}", packet_id) is not None
            and packet.get("bootstrap_cluster_id") == packet_id
            and isinstance(packet.get("record_id_commitment"), str)
            and core.SHA_RE.fullmatch(packet["record_id_commitment"]) is not None
            and type(packet.get("record_count")) is int
            and packet.get("record_count") == 6
            and isinstance(packet_commitments, list)
            and len(packet_commitments) == 6
            and len(set(packet_commitments)) == 6
            and all(
                isinstance(value, str)
                and core.SHA_RE.fullmatch(value) is not None
                for value in packet_commitments
            ),
            "v22_selection_packet_invariant_drift",
        )
        packet_ids.add(packet_id)
        commitments.extend(packet_commitments)
    require(
        len(packet_ids) == 10
        and len(commitments) == 60
        and len(set(commitments)) == 60
        and len(excluded_commitments) == 90
        and set(commitments).isdisjoint(excluded_commitments),
        "v22_selection_freshness_or_uniqueness_drift",
    )
    reject_pre_semantic_payload_v22(selection)
    return set(commitments)


INPUT_SEAL_FIELDS = {
    "document_type",
    "lane",
    "packet_index",
    "base_item_sha256",
    "compact_view_sha256",
    "transport_schema_sha256",
    "target_free",
    "contains_source_text",
}


def validate_base_gate_input_seal_v22(
    input_seal: Any,
    input_seal_path: Path,
    run_dir: Path,
    packet_index: int,
    expected_transport_schema_sha256: str,
) -> dict[str, Any]:
    """Validate one exact source-free pre-semantic base-gate input seal."""

    expected_path = (
        run_dir
        / "base_gate"
        / "dreaddit_development"
        / f"packet_{packet_index:02d}.input_seal.json"
    )
    require(
        input_seal_path == expected_path,
        "v22_input_seal_path_mismatch",
    )
    require(
        isinstance(input_seal, dict) and set(input_seal) == INPUT_SEAL_FIELDS,
        "v22_input_seal_fields_mismatch",
    )
    require(
        input_seal.get("document_type")
        == "rq2_personal_local_v22_base_gate_input_seal"
        and input_seal.get("lane") == "dreaddit_development"
        and type(input_seal.get("packet_index")) is int
        and input_seal.get("packet_index") == packet_index
        and isinstance(input_seal.get("base_item_sha256"), str)
        and core.SHA_RE.fullmatch(input_seal["base_item_sha256"]) is not None
        and isinstance(input_seal.get("compact_view_sha256"), str)
        and core.SHA_RE.fullmatch(input_seal["compact_view_sha256"]) is not None
        and isinstance(input_seal.get("transport_schema_sha256"), str)
        and input_seal.get("transport_schema_sha256")
        == expected_transport_schema_sha256
        and core.SHA_RE.fullmatch(expected_transport_schema_sha256) is not None
        and input_seal.get("target_free") is True
        and input_seal.get("contains_source_text") is False,
        "v22_input_seal_invariant_drift",
    )
    reject_pre_semantic_payload_v22(input_seal)
    return input_seal


def load_source_free_pre_semantic_context_v22(
    config: dict[str, Any], run_dir: Path
) -> tuple[dict[str, Any], set[str], str]:
    """Load only bound source-free context needed to validate public artifacts."""

    v1_config = v1.load_json(core.V1_CONFIG)
    prior_paths = {
        "prior_v1_selection": resolve_bound_path(
            config["prior_v1_development_selection_file"], allow_storage=True
        ),
        "prior_shared_selection": resolve_bound_path(
            config["prior_shared_development_selection_file"], allow_storage=True
        ),
    }
    excluded_commitments = load_predecessor_exclusions(prior_paths)
    selection = v1.load_json(
        run_dir / "selection" / "dreaddit_development.json"
    )
    validate_selection_v22(selection, v1_config, excluded_commitments)
    schema_binding = config["construction_assets"]["schema_base_admissibility"]
    schema_path = resolve_bound_path(schema_binding["file"], allow_storage=False)
    require(
        raw_sha256(schema_path) == schema_binding["sha256"],
        "v22_input_seal_transport_schema_binding_drift",
    )
    transport_schema = v1.load_json(schema_path)
    transport_schema_sha256 = v1.sha256_bytes(
        v1.canonical_bytes(transport_schema)
    )
    return v1_config, excluded_commitments, transport_schema_sha256


def _format_row(packet_index: int) -> dict[str, Any]:
    return {
        "packet_index": packet_index,
        "prerequisite_ready": False,
        "base_gate_attempted": False,
        "transport_completed": False,
        "transport_schema_valid": False,
        "cross_field_valid": False,
        "format_valid": False,
        "format_code": "base_construction_unavailable",
    }


def format_gate_aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    require(len(rows) == 10, "v22_format_row_denominator_invalid")
    require(
        [row.get("packet_index") for row in rows] == list(range(1, 11)),
        "v22_format_row_sequence_invalid",
    )
    require(
        all(row.get("format_code") in FORMAT_CODES for row in rows),
        "v22_format_code_invalid",
    )
    for row in rows:
        chain = (
            row["format_valid"],
            row["cross_field_valid"],
            row["transport_schema_valid"],
            row["transport_completed"],
            row["base_gate_attempted"],
            row["prerequisite_ready"],
        )
        require(
            all(not chain[index] or chain[index + 1] for index in range(len(chain) - 1)),
            "v22_format_state_chain_invalid",
        )
        require(
            (row["format_code"] == "format_valid") is row["format_valid"],
            "v22_format_code_state_mismatch",
        )
    counts = collections.Counter(row["format_code"] for row in rows)
    valid = sum(row["format_valid"] is True for row in rows)
    gate = {
        "document_type": "rq2_personal_local_v22_interface_format_gate",
        "scope": "ten_fresh_dreaddit_development_base_admissibility_slots",
        "planned_slots": 10,
        "prerequisite_ready": sum(row["prerequisite_ready"] is True for row in rows),
        "base_gate_attempted": sum(row["base_gate_attempted"] is True for row in rows),
        "transport_completed": sum(row["transport_completed"] is True for row in rows),
        "transport_schema_valid": sum(row["transport_schema_valid"] is True for row in rows),
        "cross_field_valid": sum(row["cross_field_valid"] is True for row in rows),
        "format_valid": valid,
        "required_format_valid": 10,
        "format_code_counts": {key: counts[key] for key in sorted(counts)},
        "passed": valid == 10,
        "run_outcome_if_terminal": None if valid == 10 else "interface_format_failed",
        "semantic_evaluation_started": False,
        "variant_calls_started": False,
        "reviewer_calls": 0,
        "fixed_role_selected": False,
        "dreaddit_audit_opened": False,
        "agyw_heldout_opened": False,
        "retry_or_replacement_used": False,
        "contains_source_text": False,
        "contains_base_status_labels": False,
        "contains_readiness_labels": False,
        "contains_reason_codes_from_model": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }
    return validate_interface_format_gate_v22(gate)


def run_base_interface_phase_v22(
    v1_config: dict[str, Any],
    paths: dict[str, Path],
    assets: dict[str, Any],
    run_dir: Path,
    records: Sequence[dict[str, Any]],
    plan: Sequence[dict[str, Any]],
    *,
    service_baseline: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run all ten format slots; semantic acceptance is a separate final block."""

    lane_name = "dreaddit_development"
    lane = v1_config["lanes"][lane_name]
    records_by_id = {row["record_id"]: row for row in records}
    item_schema = v1.load_json(paths["item_schema"])
    generation_schema = assets["schema_base_generation"]
    transport_schema = assets["schema_base_admissibility"]
    canonical_schema = assets["canonical_base_admissibility_schema"]
    adapter_contract = assets["transport_adapter_contract"]
    format_rows: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []

    # Phase 1: generate every planned base. No base semantic lifecycle is
    # serialized, and no variant can be reached from this block.
    for packet in plan:
        packet_index = packet["packet_index"]
        row = _format_row(packet_index)
        call_id = core.canonical_base_generation_call_id(lane_name, packet_index)
        excerpts = v1.excerpt_payload(packet, lane_name, records_by_id)
        result = v1.invoke_checkpointed_call(
            v1_config,
            run_dir,
            call_id=call_id,
            model_role="generator",
            system_prompt=assets["prompt_base_generation"],
            user_prompt=core.base_generation_user_prompt(lane["corpus"], excerpts),
            output_schema=generation_schema,
            rating_call=False,
            rating_repetition=None,
            retry_transport_on_explicit_resume=False,
        )
        if result["status"] != "valid":
            row["format_code"] = "base_generation_terminal"
            format_rows.append(row)
            continue
        generated = result["output"]
        if generated.get("status") != "constructed":
            row["format_code"] = "base_construction_unavailable"
            format_rows.append(row)
            continue
        try:
            roles, interpretation, metadata = core.map_positional_base_v2(generated, excerpts)
            base_item = v1.build_item(
                lane_name=lane_name,
                corpus=lane["corpus"],
                packet_id=packet["packet_id"],
                output_key=f"v2-packet-{packet_index}:base",
                interpretation=interpretation,
                roles=roles,
                excerpts=excerpts,
            )
            jsonschema.validate(base_item, item_schema)
        except (v1.PersonalLocalError, jsonschema.ValidationError):
            row["format_code"] = "base_construction_unavailable"
            format_rows.append(row)
            continue
        row["prerequisite_ready"] = True
        entries.append(
            {
                "packet": packet,
                "base_item": base_item,
                "metadata": metadata,
                "excerpts": excerpts,
                "generation_call_id": call_id,
                "format_row": row,
            }
        )
        format_rows.append(row)

    # Phase 2: invoke the flat transport interface for every available slot.
    # Adapted canonical objects remain memory-only until all ten slots pass.
    v1.recheck_service_identity(v1_config, service_baseline)
    for entry in entries:
        packet = entry["packet"]
        packet_index = packet["packet_index"]
        row = entry["format_row"]
        view = core.compact_base_view(entry["base_item"], entry["metadata"])
        input_seal_path = (
            run_dir
            / "base_gate"
            / lane_name
            / f"packet_{packet_index:02d}.input_seal.json"
        )
        core.write_v2_json(
            input_seal_path,
            {
                "document_type": "rq2_personal_local_v22_base_gate_input_seal",
                "lane": lane_name,
                "packet_index": packet_index,
                "base_item_sha256": v1.sha256_bytes(v1.canonical_bytes(entry["base_item"])),
                "compact_view_sha256": v1.sha256_bytes(v1.canonical_bytes(view)),
                "transport_schema_sha256": v1.sha256_bytes(v1.canonical_bytes(transport_schema)),
                "target_free": True,
                "contains_source_text": False,
            },
        )
        call_id = core.canonical_base_gate_call_id(lane_name, packet_index)
        row["base_gate_attempted"] = True
        result = v1.invoke_checkpointed_call(
            v1_config,
            run_dir,
            call_id=call_id,
            model_role="verifier",
            system_prompt=assets["prompt_base_admissibility"],
            user_prompt=core.base_gate_user_prompt(view),
            output_schema=transport_schema,
            rating_call=False,
            rating_repetition=None,
            retry_transport_on_explicit_resume=False,
        )
        entry["gate_call_id"] = call_id
        if result["status"] != "valid":
            stage = result.get("error", {}).get("stage")
            if stage == "response_validation":
                row["transport_completed"] = True
                row["format_code"] = "base_admissibility_transport_schema_invalid"
            else:
                row["format_code"] = "base_gate_transport_terminal"
            continue
        row["transport_completed"] = True
        row["transport_schema_valid"] = True
        try:
            canonical = adapt_base_admissibility_transport_v22(
                result["output"],
                transport_schema=transport_schema,
                canonical_schema=canonical_schema,
                adapter_contract=adapter_contract,
            )
        except FormatAdapterError as exc:
            require(str(exc) in FORMAT_CODES, "v22_adapter_failure_code_unbounded")
            row["format_code"] = str(exc)
            continue
        row["cross_field_valid"] = True
        row["format_valid"] = True
        row["format_code"] = "format_valid"
        entry["canonical_gate_output"] = canonical

    gate = format_gate_aggregate(format_rows)
    core.write_v2_json(run_dir / "interface_format_gate.json", gate)
    print(
        json.dumps(
            {
                "phase": "base_admissibility_interface_format_gate",
                "planned": gate["planned_slots"],
                "format_valid": gate["format_valid"],
                "required": gate["required_format_valid"],
                "passed": gate["passed"],
                "contains_source_text": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if not gate["passed"]:
        return gate, [], []

    # The only transition into semantics. Every canonical object is now known
    # to be transport-, schema-, and cross-field-valid.
    require(len(entries) == 10, "v22_format_pass_entry_count_invalid")
    require(
        all("canonical_gate_output" in entry for entry in entries),
        "v22_format_pass_canonical_count_invalid",
    )
    base_rows: list[dict[str, Any]] = []
    admitted_entries: list[dict[str, Any]] = []
    for entry in entries:
        packet = entry["packet"]
        packet_index = packet["packet_index"]
        packet_id = packet["packet_id"]
        packet_dir = run_dir / "items" / lane_name / f"packet_{packet_index:02d}"
        v1.ensure_private_directory(packet_dir)
        base_path = packet_dir / "base_item.json"
        metadata_path = packet_dir / "base_mapping.private.json"
        core.write_v2_json(base_path, entry["base_item"])
        core.write_v2_json(metadata_path, entry["metadata"])
        output = entry["canonical_gate_output"]
        admitted, reasons = core.base_gate_acceptance(
            output, entry["base_item"], entry["metadata"]
        )
        if admitted:
            base_status = "admitted"
        elif output.get("base_status") == "unclear":
            base_status = "base_gate_unclear"
        else:
            base_status = "base_gate_rejected"
        row = {
            "slot_id": core.slot_id(lane_name, packet_id, "base"),
            "lane": lane_name,
            "packet_index": packet_index,
            "packet_id": packet_id,
            "bootstrap_cluster_id": packet["bootstrap_cluster_id"],
            "generation_call_id": entry["generation_call_id"],
            "generation_status": "valid",
            "semantic_status": "valid",
            "gate_call_id": entry["gate_call_id"],
            "gate_status": "valid",
            "base_status": base_status,
            "reason_codes": reasons,
            "base_item_sha256": v1.sha256_file(base_path),
            "contains_source_text": False,
        }
        report = {
            "document_type": "rq2_personal_local_v22_base_admissibility",
            "lane": lane_name,
            "packet_index": packet_index,
            "slot_id": row["slot_id"],
            "call_id": entry["gate_call_id"],
            "transport_format_gate_passed_before_semantic_evaluation": True,
            "status": "valid",
            "output": output,
            "admitted": admitted,
            "reason_codes": reasons,
            "input_seal_sha256": v1.sha256_file(
                run_dir / "base_gate" / lane_name / f"packet_{packet_index:02d}.input_seal.json"
            ),
            "contains_source_text": False,
            "verification_label": VERIFICATION_LABEL,
        }
        report_path = run_dir / "base_gate" / lane_name / f"packet_{packet_index:02d}.json"
        core.write_v2_json(report_path, report)
        entry["row"] = row
        if admitted:
            entry["base_gate_output"] = output
            entry["base_gate_report_sha256"] = v1.sha256_file(report_path)
            admitted_entries.append(entry)
        else:
            core.write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=packet_id,
                family_index=None,
                family=None,
                outcome=base_status,
                reason_codes=reasons,
                call_id=entry["gate_call_id"],
            )
        base_rows.append(row)

    base_ledger = {
        "document_type": "rq2_personal_local_v2_base_lifecycle",
        "lane": lane_name,
        "planned": 10,
        "generation_attempted": 10,
        "generation_valid": 10,
        "semantic_valid": 10,
        "base_gate_attempted": 10,
        "base_gate_verified": 10,
        "admitted": len(admitted_entries),
        "unclear": sum(row["base_status"] == "base_gate_unclear" for row in base_rows),
        "interface_format_gate_sha256": v1.sha256_file(run_dir / "interface_format_gate.json"),
        "rows": base_rows,
        "contains_source_text": False,
        "result_label": STATUS,
    }
    core.write_v2_json(run_dir / "construction" / f"{lane_name}_bases.json", base_ledger)
    return gate, base_rows, admitted_entries


def write_format_failure_terminal(
    run_dir: Path,
    gate: dict[str, Any],
    boundary_evidence: dict[str, Any],
) -> None:
    require(gate.get("passed") is False, "v22_format_failure_gate_passed")
    operations = v1.aggregate_call_attempt_operations(run_dir)
    analysis = {
        "document_type": "rq2_personal_local_v22_interface_format_analysis",
        "run_id": run_dir.name,
        "run_outcome": "interface_format_failed",
        "scope": "base_admissibility_interface_format_only",
        "interface_format_gate": gate,
        "all_call_attempt_operations": operations,
        "semantic_base_labels_created": 0,
        "variant_calls": 0,
        "comparison_calls": 0,
        "reviewer_calls": 0,
        "fixed_role_selected": False,
        "heldout_lanes_opened": False,
        "retry_or_replacement_used": False,
        "boundary_checks": boundary_evidence,
        "contains_source_text": False,
        "contains_base_status_labels": False,
        "contains_readiness_labels": False,
        "contains_reason_codes_from_model": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "qualification_is_rq2_performance_result": False,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    validate_interface_format_gate_v22(gate, expected_passed=False)
    validate_format_failure_analysis_v22(
        analysis, run_dir.name, gate, boundary_evidence, operations
    )
    core.write_v2_json(run_dir / "analysis" / "interface_format_result.json", analysis)
    core.write_v2_json(
        run_dir / "run_terminal_status.json",
        expected_terminal_status_v22(run_dir.name, "interface_format_failed"),
    )


def _call_inventory_and_ids(run_dir: Path) -> tuple[set[str], set[str]]:
    calls_root = run_dir / "raw" / "calls"
    with os.scandir(calls_root) as entries:
        call_entries = sorted(entries, key=lambda entry: entry.name)
    call_ids: set[str] = set()
    file_paths: set[str] = set()
    for entry in call_entries:
        require(stat.S_ISDIR(entry.stat(follow_symlinks=False).st_mode), "v22_call_entry_not_directory")
        call_id = entry.name
        call_ids.add(call_id)
        call_dir = calls_root / call_id
        contract = v1.load_json(call_dir / "call_contract.json")
        require(
            contract.get("call_id") == call_id
            and contract.get("lane") == "dreaddit_development"
            and contract.get("call_kind") in {"construction", "construction_verification"}
            and contract.get("retry_transport_on_explicit_resume") is False,
            "v22_call_contract_drift",
        )
        names = v1.regular_child_names(call_dir)
        allowed = re.compile(r"^(?:call_contract|success|attempt_01_(?:request|response|error))\.json$")
        require(all(allowed.fullmatch(name) for name in names), "v22_call_checkpoint_file_invalid")
        require(
            "attempt_01_request.json" in names and "attempt_01_response.json" in names,
            "v22_call_attempt_incomplete",
        )
        require(
            ("success.json" in names) ^ ("attempt_01_error.json" in names),
            "v22_call_final_state_invalid",
        )
        file_paths.update(f"raw/calls/{call_id}/{name}" for name in names)
    return call_ids, file_paths


FORMAT_ANALYSIS_FIELDS = {
    "document_type",
    "run_id",
    "run_outcome",
    "scope",
    "interface_format_gate",
    "all_call_attempt_operations",
    "semantic_base_labels_created",
    "variant_calls",
    "comparison_calls",
    "reviewer_calls",
    "fixed_role_selected",
    "heldout_lanes_opened",
    "retry_or_replacement_used",
    "boundary_checks",
    "contains_source_text",
    "contains_base_status_labels",
    "contains_readiness_labels",
    "contains_reason_codes_from_model",
    "result_label",
    "evidence_status",
    "qualification_is_rq2_performance_result",
    "manuscript_eligible",
    "publication_or_release_eligible",
    "confirmatory_claims_allowed",
}


def validate_format_failure_analysis_v22(
    analysis: Any,
    run_id: str,
    gate: dict[str, Any],
    boundary_evidence: dict[str, Any],
    operations: dict[str, Any],
) -> dict[str, Any]:
    """Validate the exact no-label format-failure analysis artifact."""

    require(
        isinstance(analysis, dict) and set(analysis) == FORMAT_ANALYSIS_FIELDS,
        "v22_format_analysis_fields_mismatch",
    )
    require(
        analysis.get("document_type")
        == "rq2_personal_local_v22_interface_format_analysis"
        and analysis.get("run_id") == run_id
        and analysis.get("run_outcome") == "interface_format_failed"
        and analysis.get("scope") == "base_admissibility_interface_format_only"
        and strict_equal_v22(analysis.get("interface_format_gate"), gate)
        and strict_equal_v22(
            analysis.get("all_call_attempt_operations"), operations
        )
        and type(analysis.get("semantic_base_labels_created")) is int
        and analysis.get("semantic_base_labels_created") == 0
        and type(analysis.get("variant_calls")) is int
        and analysis.get("variant_calls") == 0
        and type(analysis.get("comparison_calls")) is int
        and analysis.get("comparison_calls") == 0
        and type(analysis.get("reviewer_calls")) is int
        and analysis.get("reviewer_calls") == 0
        and analysis.get("fixed_role_selected") is False
        and analysis.get("heldout_lanes_opened") is False
        and analysis.get("retry_or_replacement_used") is False
        and strict_equal_v22(
            analysis.get("boundary_checks"), boundary_evidence
        )
        and analysis.get("contains_source_text") is False
        and analysis.get("contains_base_status_labels") is False
        and analysis.get("contains_readiness_labels") is False
        and analysis.get("contains_reason_codes_from_model") is False
        and analysis.get("result_label") == STATUS
        and analysis.get("evidence_status") == EVIDENCE_STATUS
        and analysis.get("qualification_is_rq2_performance_result") is False
        and analysis.get("manuscript_eligible") is False
        and analysis.get("publication_or_release_eligible") is False
        and analysis.get("confirmatory_claims_allowed") is False,
        "v22_format_analysis_immutable_drift",
    )
    reject_pre_semantic_payload_v22(analysis)
    return analysis


def validate_format_failure_completeness(
    run_dir: Path, config: dict[str, Any]
) -> None:
    require(RUN_ID_RE.fullmatch(run_dir.name) is not None, "v22_format_run_id_invalid")
    canary_summary = validate_run_canary_cross_binding_v22(run_dir, config)
    gate = validate_interface_format_gate_v22(
        v1.load_json(run_dir / "interface_format_gate.json"),
        expected_passed=False,
    )
    terminal = v1.load_json(run_dir / "run_terminal_status.json")
    validate_terminal_status_v22(
        terminal, run_dir.name, "interface_format_failed"
    )
    analysis = v1.load_json(run_dir / "analysis" / "interface_format_result.json")
    core_contract = v1.load_json(run_dir / "run_contract.json")
    boundary = core_contract["boundary_checks"]
    require(
        boundary["live_interface_canary_evidence_sha256"]
        == canary_summary["evidence_sha256"],
        "v22_format_canary_boundary_drift",
    )
    _, _, transport_schema_sha256 = load_source_free_pre_semantic_context_v22(
        config, run_dir
    )

    generation_ids = {
        core.canonical_base_generation_call_id("dreaddit_development", index)
        for index in range(1, 11)
    }
    gate_id_universe = {
        core.canonical_base_gate_call_id("dreaddit_development", index)
        for index in range(1, 11)
    }
    call_ids, call_files = _call_inventory_and_ids(run_dir)
    observed_gate_ids = call_ids & gate_id_universe
    require(generation_ids <= call_ids, "v22_format_generation_call_set_incomplete")
    require(call_ids == generation_ids | observed_gate_ids, "v22_format_call_set_invalid")
    require(len(observed_gate_ids) == gate["base_gate_attempted"], "v22_format_gate_call_count_drift")
    for packet_index in range(1, 11):
        if (
            core.canonical_base_gate_call_id(
                "dreaddit_development", packet_index
            )
            not in observed_gate_ids
        ):
            continue
        input_seal_path = (
            run_dir
            / "base_gate"
            / "dreaddit_development"
            / f"packet_{packet_index:02d}.input_seal.json"
        )
        validate_base_gate_input_seal_v22(
            v1.load_json(input_seal_path),
            input_seal_path,
            run_dir,
            packet_index,
            transport_schema_sha256,
        )

    fixed_files = {
        "v2_freeze_snapshot.json",
        "v1_freeze_snapshot.json",
        "policy_snapshot.json",
        "run_contract.json",
        "v22_interface_contract.json",
        "selection/dreaddit_development.json",
        "interface_format_gate.json",
        "analysis/interface_format_result.json",
        "run_terminal_status.json",
    }
    input_seals = {
        f"base_gate/dreaddit_development/packet_{index:02d}.input_seal.json"
        for index in range(1, 11)
        if core.canonical_base_gate_call_id("dreaddit_development", index)
        in observed_gate_ids
    }
    inventory = v1.safe_run_inventory(run_dir)
    inventory_paths = {row["path"] for row in inventory}
    require(
        inventory_paths == fixed_files | input_seals | call_files,
        "v22_format_failure_inventory_path_mismatch",
    )
    require(
        not any(
            path.startswith("items/")
            or path.startswith("construction/")
            or path.startswith("verification/")
            or path.startswith("quarantine/")
            or path.startswith("truth/")
            or path.startswith("observations/")
            or "qualification_gate" in path
            or "fixed_role" in path
            or "dreaddit_audit" in path
            or "agyw_heldout" in path
            for path in inventory_paths
        ),
        "v22_format_failure_contains_semantic_or_downstream_artifact",
    )
    operations = v1.aggregate_call_attempt_operations(run_dir)
    require(
        operations["logical_calls_started"] == len(call_ids)
        and operations["physical_attempts"] == len(call_ids)
        and operations["by_call_kind"]["role_review"]["logical_calls"] == 0
        and strict_equal_v22(
            analysis.get("all_call_attempt_operations"), operations
        ),
        "v22_format_operation_count_drift",
    )
    validate_format_failure_analysis_v22(
        analysis, run_dir.name, gate, boundary, operations
    )


@contextmanager
def _core_inventory_without_v22_extras() -> Iterator[None]:
    original = v1.safe_run_inventory

    def filtered(run_dir: Path) -> list[dict[str, Any]]:
        return [
            row
            for row in original(run_dir)
            if row["path"]
            not in {"v22_interface_contract.json", "interface_format_gate.json"}
        ]

    v1.safe_run_inventory = filtered
    try:
        yield
    finally:
        v1.safe_run_inventory = original


QUALIFICATION_ANALYSIS_FIELDS = {
    "document_type",
    "run_id",
    "run_outcome",
    "scope",
    "result_label",
    "evidence_status",
    "metric_label",
    "contains_source_text",
    "funnel",
    "qualification_gate",
    "interface_format_gate_sha256",
    "all_call_attempt_operations",
    "reviewer_calls",
    "fixed_role_selected",
    "heldout_lanes_opened",
    "v1_results_reused",
    "prior_v2_v21_results_reused",
    "human_ground_truth",
    "qualification_is_rq2_performance_result",
    "boundary_checks",
    "manuscript_eligible",
    "publication_or_release_eligible",
    "confirmatory_claims_allowed",
}


def validate_qualification_analysis_boundaries_v22(
    analysis: Any,
    run_dir: Path,
    gate: dict[str, Any],
    boundary_evidence: dict[str, Any],
    expected_funnel: dict[str, Any],
    expected_operations: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(analysis, dict)
        and set(analysis) == QUALIFICATION_ANALYSIS_FIELDS,
        "v22_qualification_analysis_fields_mismatch",
    )
    require(
        analysis.get("document_type")
        == "rq2_personal_local_v2_qualification_analysis"
        and analysis.get("run_id") == run_dir.name
        and analysis.get("run_outcome") == gate.get("run_outcome")
        and analysis.get("scope") == "construction_qualification_only"
        and analysis.get("result_label") == STATUS
        and analysis.get("evidence_status") == EVIDENCE_STATUS
        and analysis.get("metric_label") == core.METRIC_LABEL
        and analysis.get("contains_source_text") is False
        and strict_equal_v22(analysis.get("funnel"), expected_funnel)
        and strict_equal_v22(analysis.get("qualification_gate"), gate)
        and analysis.get("interface_format_gate_sha256")
        == v1.sha256_file(run_dir / "interface_format_gate.json")
        and type(analysis.get("reviewer_calls")) is int
        and analysis.get("reviewer_calls") == 0
        and strict_equal_v22(
            analysis.get("all_call_attempt_operations"), expected_operations
        )
        and analysis.get("fixed_role_selected") is False
        and analysis.get("heldout_lanes_opened") is False
        and analysis.get("v1_results_reused") is False
        and analysis.get("prior_v2_v21_results_reused") is False
        and analysis.get("human_ground_truth") is False
        and analysis.get("qualification_is_rq2_performance_result") is False
        and strict_equal_v22(
            analysis.get("boundary_checks"), boundary_evidence
        )
        and analysis.get("manuscript_eligible") is False
        and analysis.get("publication_or_release_eligible") is False
        and analysis.get("confirmatory_claims_allowed") is False,
        "v22_qualification_analysis_boundary_drift",
    )
    return analysis


def validate_semantic_completeness(run_dir: Path, config: dict[str, Any]) -> None:
    canary_summary = validate_run_canary_cross_binding_v22(run_dir, config)
    format_gate = validate_interface_format_gate_v22(
        v1.load_json(run_dir / "interface_format_gate.json"),
        expected_passed=True,
    )
    _, _, transport_schema_sha256 = load_source_free_pre_semantic_context_v22(
        config, run_dir
    )
    for packet_index in range(1, 11):
        input_seal_path = (
            run_dir
            / "base_gate"
            / "dreaddit_development"
            / f"packet_{packet_index:02d}.input_seal.json"
        )
        validate_base_gate_input_seal_v22(
            v1.load_json(input_seal_path),
            input_seal_path,
            run_dir,
            packet_index,
            transport_schema_sha256,
        )
    with _core_inventory_without_v22_extras():
        core.validate_run_completeness_v2(run_dir, config)
    qualification_gate = v1.load_json(run_dir / "qualification_gate.json")
    outcome = qualification_gate.get("run_outcome")
    require(
        outcome in {"qualification_failed", "qualification_passed"},
        "v22_semantic_outcome_invalid",
    )
    terminal = v1.load_json(run_dir / "run_terminal_status.json")
    validate_terminal_status_v22(terminal, run_dir.name, outcome)
    core_contract = v1.load_json(run_dir / "run_contract.json")
    boundary = core_contract["boundary_checks"]
    require(
        boundary["live_interface_canary_evidence_sha256"]
        == canary_summary["evidence_sha256"],
        "v22_semantic_canary_boundary_drift",
    )
    analysis = v1.load_json(run_dir / "analysis" / "qualification_results.json")
    base_ledger = v1.load_json(
        run_dir / "construction" / "dreaddit_development_bases.json"
    )
    variant_ledger = v1.load_json(
        run_dir / "construction" / "dreaddit_development_variants.json"
    )
    expected_funnel = core.reconcile_lane_funnel_v2(
        base_ledger["rows"], variant_ledger["rows"]
    )
    expected_operations = v1.aggregate_call_attempt_operations(run_dir)
    validate_qualification_analysis_boundaries_v22(
        analysis,
        run_dir,
        qualification_gate,
        boundary,
        expected_funnel,
        expected_operations,
    )
    inventory_paths = {row["path"] for row in v1.safe_run_inventory(run_dir)}
    require(
        "v22_interface_contract.json" in inventory_paths
        and "interface_format_gate.json" in inventory_paths,
        "v22_semantic_interface_artifacts_missing",
    )
    require(
        not any(
            path.startswith("observations/")
            or "fixed_role" in path
            or "dreaddit_audit" in path
            or "agyw_heldout" in path
            for path in inventory_paths
        ),
        "v22_semantic_contains_forbidden_downstream_artifact",
    )


def validate_output_seal_v22(run_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    seal_path = run_dir / "output_seal.json"
    require(v1.safe_exists(seal_path), "v22_output_seal_missing")
    seal = v1.load_json(seal_path)
    require(
        set(seal)
        == {
            "document_type",
            "run_id",
            "run_outcome",
            "result_label",
            "evidence_status",
            "sealed_at_utc",
            "files",
            "seal_payload_sha256",
            "live_interface_canary_evidence_sha256",
            "interface_format_gate_sha256",
            "qualification_gate_sha256",
            "qualification_results_sha256",
            "this_manifest_contains_source_text",
            "sealed_run_contains_restricted_source_text",
            "qualification_only",
            "permanent_stop",
            "manuscript_eligible",
            "publication_or_release_eligible",
            "confirmatory_claims_allowed",
        },
        "v22_seal_fields_mismatch",
    )
    require(
        seal.get("document_type") == "rq2_personal_local_v22_output_seal"
        and seal.get("run_id") == run_dir.name
        and seal.get("run_outcome")
        in {"interface_format_failed", "qualification_failed", "qualification_passed"}
        and isinstance(seal.get("sealed_at_utc"), str)
        and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            seal["sealed_at_utc"],
        )
        is not None,
        "v22_seal_identity_invalid",
    )
    canary_summary = validate_run_canary_cross_binding_v22(run_dir, config)
    entries = seal.get("files")
    require(
        isinstance(entries, list)
        and strict_equal_v22(entries, v1.safe_run_inventory(run_dir)),
        "v22_seal_inventory_drift",
    )
    require(
        seal.get("seal_payload_sha256") == v1.sha256_bytes(v1.canonical_bytes(entries))
        and seal.get("interface_format_gate_sha256")
        == v1.sha256_file(run_dir / "interface_format_gate.json"),
        "v22_seal_payload_drift",
    )
    require(
        seal.get("live_interface_canary_evidence_sha256")
        == canary_summary["evidence_sha256"],
        "v22_seal_canary_binding_drift",
    )
    outcome = seal["run_outcome"]
    if outcome == "interface_format_failed":
        require(
            seal.get("qualification_gate_sha256") is None
            and seal.get("qualification_results_sha256") is None,
            "v22_format_seal_contains_semantic_hash",
        )
        validate_format_failure_completeness(run_dir, config)
    else:
        require(
            seal.get("qualification_gate_sha256")
            == v1.sha256_file(run_dir / "qualification_gate.json")
            and seal.get("qualification_results_sha256")
            == v1.sha256_file(run_dir / "analysis" / "qualification_results.json")
            and v1.load_json(run_dir / "qualification_gate.json")["run_outcome"] == outcome,
            "v22_semantic_seal_result_drift",
        )
        validate_semantic_completeness(run_dir, config)
    require(
        seal.get("result_label") == STATUS
        and seal.get("evidence_status") == EVIDENCE_STATUS
        and seal.get("this_manifest_contains_source_text") is False
        and seal.get("sealed_run_contains_restricted_source_text") is True
        and seal.get("qualification_only") is True
        and seal.get("permanent_stop") is True
        and seal.get("manuscript_eligible") is False
        and seal.get("publication_or_release_eligible") is False
        and seal.get("confirmatory_claims_allowed") is False,
        "v22_seal_boundary_flags_drift",
    )
    return seal


def seal_run_v22(run_dir: Path, config: dict[str, Any], run_outcome: str) -> dict[str, Any]:
    seal_path = run_dir / "output_seal.json"
    if v1.safe_exists(seal_path):
        return validate_output_seal_v22(run_dir, config)
    require(
        run_outcome
        in {"interface_format_failed", "qualification_failed", "qualification_passed"},
        "v22_seal_outcome_invalid",
    )
    canary_summary = validate_run_canary_cross_binding_v22(run_dir, config)
    if run_outcome == "interface_format_failed":
        validate_format_failure_completeness(run_dir, config)
        qualification_gate_sha256 = None
        qualification_results_sha256 = None
    else:
        validate_semantic_completeness(run_dir, config)
        require(
            v1.load_json(run_dir / "qualification_gate.json").get("run_outcome")
            == run_outcome,
            "v22_seal_semantic_outcome_mismatch",
        )
        qualification_gate_sha256 = v1.sha256_file(run_dir / "qualification_gate.json")
        qualification_results_sha256 = v1.sha256_file(
            run_dir / "analysis" / "qualification_results.json"
        )
    entries = v1.safe_run_inventory(run_dir)
    seal = {
        "document_type": "rq2_personal_local_v22_output_seal",
        "run_id": run_dir.name,
        "run_outcome": run_outcome,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "sealed_at_utc": utc_now(),
        "files": entries,
        "seal_payload_sha256": v1.sha256_bytes(v1.canonical_bytes(entries)),
        "live_interface_canary_evidence_sha256": canary_summary[
            "evidence_sha256"
        ],
        "interface_format_gate_sha256": v1.sha256_file(run_dir / "interface_format_gate.json"),
        "qualification_gate_sha256": qualification_gate_sha256,
        "qualification_results_sha256": qualification_results_sha256,
        "this_manifest_contains_source_text": False,
        "sealed_run_contains_restricted_source_text": True,
        "qualification_only": True,
        "permanent_stop": True,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    core.write_v2_json(seal_path, seal)
    return validate_output_seal_v22(run_dir, config)


def write_qualification_analysis_v22(
    config: dict[str, Any],
    run_dir: Path,
    summary: dict[str, Any],
    gate: dict[str, Any],
    boundary_evidence: dict[str, Any],
) -> None:
    operations = v1.aggregate_call_attempt_operations(run_dir)
    result = {
        "document_type": "rq2_personal_local_v2_qualification_analysis",
        "run_id": run_dir.name,
        "run_outcome": gate["run_outcome"],
        "scope": "construction_qualification_only",
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "metric_label": core.METRIC_LABEL,
        "contains_source_text": False,
        "funnel": summary,
        "qualification_gate": gate,
        "interface_format_gate_sha256": v1.sha256_file(
            run_dir / "interface_format_gate.json"
        ),
        "all_call_attempt_operations": operations,
        "reviewer_calls": 0,
        "fixed_role_selected": False,
        "heldout_lanes_opened": False,
        "v1_results_reused": False,
        "prior_v2_v21_results_reused": False,
        "human_ground_truth": False,
        "qualification_is_rq2_performance_result": False,
        "boundary_checks": boundary_evidence,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    core.write_v2_json(run_dir / "analysis" / "qualification_results.json", result)
    core.write_v2_json(
        run_dir / "run_terminal_status.json",
        expected_terminal_status_v22(run_dir.name, gate["run_outcome"]),
    )


def execute_v22(
    config_path: Path,
    requested_run_id: str | None,
    *,
    resume_existing: bool = False,
) -> Path:
    os.umask(0o077)
    config = v1.load_json(config_path)
    # First validate source-free bindings and honor an existing terminal state
    # without touching predecessor selections, records, policy subprocesses, or
    # the model service.
    static_v1_config, _, static_paths, _ = validate_v22_freeze(
        config,
        include_record_hashes=False,
        config_path=config_path,
    )
    static_assets = load_assets(static_paths)
    validate_interface_assets(config, static_assets)
    run_id = build_run_id(requested_run_id)
    candidate_run_dir = V22_OUTPUT_ROOT / run_id
    if resume_existing:
        require(requested_run_id is not None, "v22_resume_run_id_required")
        if v1.safe_exists(candidate_run_dir / "output_seal.json"):
            validate_output_seal_v22(candidate_run_dir, config)
            return candidate_run_dir
        if v1.safe_exists(candidate_run_dir / "run_terminal_status.json"):
            terminal = v1.load_json(candidate_run_dir / "run_terminal_status.json")
            outcome = terminal.get("run_outcome")
            require(
                outcome
                in {"interface_format_failed", "qualification_failed", "qualification_passed"},
                "v22_terminal_outcome_invalid",
            )
            seal_run_v22(candidate_run_dir, config, outcome)
            return candidate_run_dir
        require(
            v1.safe_exists(candidate_run_dir / "v22_interface_contract.json"),
            "v22_resume_interface_contract_missing",
        )
        require(
            v1.safe_exists(candidate_run_dir / "run_contract.json"),
            "v22_resume_core_contract_missing",
        )
        live_canary_summary = validate_run_canary_cross_binding_v22(
            candidate_run_dir,
            config,
            v1_config=static_v1_config,
            assets=static_assets,
        )
        require(
            live_canary_summary
            == canary_contract_summary(
                expected_live_canary_evidence_v22(
                    static_v1_config, static_assets
                )
            ),
            "v22_resume_canary_cross_binding_mismatch",
        )
        service = v1.preflight_service(static_v1_config)
    else:
        # New-run mode does not stat, list, read, or create any Storage path
        # until all three live canaries pass.
        service = v1.preflight_service(static_v1_config)
        live_canary_evidence = run_live_interface_canary_v22(
            static_v1_config, static_assets
        )
        live_canary_summary = canary_contract_summary(live_canary_evidence)
        require(
            not v1.safe_exists(candidate_run_dir),
            "v22_new_run_id_already_exists",
        )

    v1_config, v1_paths, paths, excluded_commitments = validate_v22_freeze(
        config,
        include_record_hashes=True,
        config_path=config_path,
    )
    require(
        strict_equal_v22(v1_config, static_v1_config),
        "v22_v1_config_changed_after_canary",
    )
    assets = load_assets(paths)
    validate_interface_assets(config, assets)
    policy = v1.load_json(v1_paths["policy"])
    require(
        raw_sha256(v1_paths["policy"]) == v1_config["policy_file_sha256"],
        "v22_policy_hash_drift",
    )
    v1.validate_policy_boundary(policy, v1_config)
    boundary_evidence = expected_boundary_evidence_v22(
        v1_config, live_canary_summary
    )
    run_dir = initialize_run_v22(
        config,
        config_path,
        v1_config,
        v1_paths,
        run_id,
        service,
        boundary_evidence,
        live_canary_summary,
    )

    lane_name = "dreaddit_development"
    lane = v1_config["lanes"][lane_name]
    split_index = v1.load_json(v1_paths["split_index"])
    v1.recheck_service_identity(v1_config, service)
    records = v1.load_bound_records(
        v1_paths[f"records_{lane_name}"],
        lane["corpus"],
        lane["records_file_sha256"],
        lane["split"],
        split_index=split_index,
    )
    plan, _ = select_lane_packets_v22(
        v1_config,
        config,
        run_dir,
        records,
        excluded_commitments=excluded_commitments,
    )
    v1.recheck_service_identity(v1_config, service)
    format_gate, base_rows, admitted_entries = run_base_interface_phase_v22(
        v1_config,
        v1_paths,
        assets,
        run_dir,
        records,
        plan,
        service_baseline=service,
    )
    del records
    if not format_gate["passed"]:
        require(base_rows == [] and admitted_entries == [], "v22_format_failure_semantic_state_leak")
        write_format_failure_terminal(run_dir, format_gate, boundary_evidence)
        v1.recheck_service_identity(v1_config, service)
        seal_run_v22(run_dir, config, "interface_format_failed")
        return run_dir

    v1.recheck_service_identity(v1_config, service)
    _, _, summary = core.run_variant_and_comparison_phases_v2(
        v1_config,
        v1_paths,
        assets,
        run_dir,
        lane_name,
        base_rows,
        admitted_entries,
        service_baseline=service,
    )
    del admitted_entries
    gate = core.evaluate_development_qualification_v2(config, run_dir, summary)
    write_qualification_analysis_v22(
        config, run_dir, summary, gate, boundary_evidence
    )
    v1.recheck_service_identity(v1_config, service)
    seal_run_v22(run_dir, config, gate["run_outcome"])
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "dry-run",
        help="Validate source-free frozen files and canary vectors without data, Storage, or Ollama.",
    )
    subparsers.add_parser(
        "preflight-service",
        help="Validate source-free files and local Ollama metadata without records.",
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Start a new final ten-packet development qualification.",
    )
    run_parser.add_argument(
        "--run-id", help="New or existing rq2plv22_YYYYMMDDTHHMMSSZ_abcdefgh identifier"
    )
    resume_parser = subparsers.add_parser(
        "resume",
        help="Validate a sealed run or reconstruct an active run with bound canary evidence.",
    )
    resume_parser.add_argument(
        "--run-id",
        required=True,
        help="Existing rq2plv22_YYYYMMDDTHHMMSSZ_abcdefgh identifier",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.absolute()
    try:
        config = v1.load_json(config_path)
        if args.command == "dry-run":
            _, _, paths, _ = validate_v22_freeze(
                config,
                include_record_hashes=False,
                config_path=config_path,
            )
            assets = load_assets(paths)
            validate_interface_assets(config, assets)
            print(
                json.dumps(
                    {
                        "v22_static_status": "passed",
                        "interface_fixture_count": 3,
                        "required_real_format_valid": 10,
                        "data_opened": False,
                        "storage_opened": False,
                        "service_contacted": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "preflight-service":
            v1_config, _, paths, _ = validate_v22_freeze(
                config,
                include_record_hashes=False,
                config_path=config_path,
            )
            assets = load_assets(paths)
            validate_interface_assets(config, assets)
            report = v1.preflight_service(v1_config)
            live_canary_summary = canary_contract_summary(
                run_live_interface_canary_v22(v1_config, assets)
            )
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "endpoint": report["endpoint"],
                        "endpoint_is_numeric_loopback": report[
                            "endpoint_is_numeric_loopback"
                        ],
                        "ollama_version": report["ollama_version"],
                        "models": {
                            role: {
                                "model_id": row["model_id"],
                                "digest": row["digest"],
                            }
                            for role, row in report["models"].items()
                        },
                        "live_interface_canary": live_canary_summary,
                        "qualification_only": True,
                        "contains_source_text": False,
                    },
                    sort_keys=True,
                )
            )
            return 0
        run_dir = execute_v22(
            config_path,
            args.run_id,
            resume_existing=args.command == "resume",
        )
        seal = v1.load_json(run_dir / "output_seal.json")
        print(
            json.dumps(
                {
                    "run_id": run_dir.name,
                    "run_outcome": seal["run_outcome"],
                    "sealed": True,
                    "qualification_only": True,
                    "contains_source_text": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (v1.PersonalLocalError, core.V2Error, V22Error) as exc:
        code = str(exc)
        if not re.fullmatch(r"[A-Za-z0-9_:.-]+", code):
            code = "v22_runtime_failure"
        print(
            json.dumps(
                {
                    "v22_status": "stopped",
                    "failure_code": code,
                    "contains_source_text": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "v22_status": "stopped",
                    "failure_code": "v22_runtime_failure",
                    "contains_source_text": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
