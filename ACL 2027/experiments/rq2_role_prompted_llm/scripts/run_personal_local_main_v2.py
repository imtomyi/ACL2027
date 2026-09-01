#!/usr/bin/env python3
"""Run the separately frozen v2 personal-local RQ2 diagnostic.

V2 is an orchestration amendment.  It imports the byte-frozen v1 helper module,
but it has a separate freeze, run namespace, qualification gate, lifecycle
ledger, completeness rules, and output seal.  It never resumes or mutates a v1
run.  All outputs remain private personal diagnostics and are ineligible for a
manuscript, publication, release, redistribution, or human review.

``dry-run`` and ``preflight-service`` do not open either records file.  Only the
explicit ``run`` subcommand may parse source-bearing records.  Source text is
never printed and never appears in lifecycle summaries, qualification records,
manifests, or seals.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import stat
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment preflight
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
V1_SCRIPT = SCRIPT.with_name("run_personal_local_main.py")
V1_CONFIG = RQ2_ROOT / "config" / "personal_local_main_freeze.json"
DEFAULT_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v2_freeze.json"
V1_RUNNER_SHA256 = "8048a824dceead18e8cb037f87a3a5f58a9e9a466d6dfd41f9043489bef13c32"
V1_FREEZE_SHA256 = "f1f6fde0f9659228bac35af6844030f88c1d67333e695b08d228d52226f0e6ed"
RUN_ID_RE = re.compile(r"^rq2plv2_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
STATUS = "private_personal_exploratory_not_for_publication"
EVIDENCE_STATUS = "diagnostic_not_manuscript_evidence"
VERIFICATION_LABEL = "frozen_local_model_screened_not_human_ground_truth"
METRIC_LABEL = "automated-target recall among Gemma-screened variants"
LANE_ORDER = ("dreaddit_development", "dreaddit_audit", "agyw_heldout")
ROLE_ORDER = ("generalist", "methods", "domain")
FAMILY_ORDER = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)
DETERMINISTIC_FAMILIES = FAMILY_ORDER[:3]
GENERATED_EDIT_FAMILIES = FAMILY_ORDER[3:]
V2_OUTPUT_ROOT = WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "v2_runs"
V1_SELECTION_RELATIVE = (
    "Storage/rq2_personal_local_diagnostic/"
    "rq2pl_20260827T015148Z_8f3c1a7b/selection/dreaddit_development.json"
)
V1_SELECTION_SHA256 = "a38506be58b0d24d7690038243bb5bae110186eed4c88d8726cb4b0b8ff22883"


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_frozen_v1() -> Any:
    """Verify v1 bytes before importing its read-only helper namespace."""

    if _raw_sha256(V1_SCRIPT) != V1_RUNNER_SHA256:
        raise SystemExit("v1_runner_hash_drift")
    spec = importlib.util.spec_from_file_location("rq2_personal_local_main_v1_frozen", V1_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit("v1_runner_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = load_frozen_v1()


class V2Error(v1.PersonalLocalError):
    """A finite source-free v2 error safe to expose on stderr."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise V2Error(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slot_id(lane_name: str, packet_id: str, kind: str) -> str:
    return v1.opaque_id("SLT", lane_name, packet_id, kind)


def finite_schema_error(exc: jsonschema.ValidationError) -> str:
    """Return only a finite code; ValidationError text may contain source."""

    validator = exc.validator if isinstance(exc.validator, str) else "unknown"
    return f"schema_{validator}_invalid"


def asset_paths(config: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    assets = config.get("construction_assets", {})
    require(isinstance(assets, dict), "v2_assets_invalid")
    for name, row in assets.items():
        require(
            isinstance(name, str)
            and isinstance(row, dict)
            and set(row) == {"file", "sha256"},
            "v2_asset_binding_invalid",
        )
        paths[name] = v1.resolve_workspace_path(row["file"])
    return paths


def validate_v2_freeze(
    config: dict[str, Any], *, include_record_hashes: bool, config_path: Path
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Path], set[str]]:
    """Validate the v2 overlay and the complete untouched v1 boundary."""

    v1.reject_symlink_components(config_path, anchor=WORKSPACE)
    require(config_path == DEFAULT_CONFIG, "only_exact_v2_freeze_allowed")
    expected_fields = {
        "document_type",
        "freeze_version",
        "status",
        "execution_class",
        "created_at_utc",
        "v1_freeze_file",
        "v1_freeze_sha256",
        "v1_runner_file",
        "v1_runner_sha256",
        "prior_v1_development_selection_file",
        "prior_v1_development_selection_sha256",
        "prior_v1_outcomes_reused",
        "output_root",
        "run_id_prefix",
        "lane_packet_counts",
        "qualification_only",
        "reviewer_calls_allowed",
        "fixed_role_selection_allowed",
        "dreaddit_audit_access_allowed",
        "agyw_heldout_access_allowed",
        "main_execution_requires_separate_freeze",
        "development_qualification",
        "outcome_policy",
        "construction_assets",
        "protocol_file",
        "protocol_sha256",
        "runner_file",
        "runner_sha256",
        "result_labels",
    }
    require(set(config) == expected_fields, "v2_freeze_top_level_fields_mismatch")
    require(config.get("document_type") == "rq2_personal_local_main_v2_freeze", "v2_freeze_type_mismatch")
    require(config.get("freeze_version") == "rq2-personal-local-main-v2", "v2_freeze_version_mismatch")
    require(config.get("status") == STATUS, "v2_freeze_status_mismatch")
    require(config.get("execution_class") == "personal_local_diagnostic", "v2_freeze_class_mismatch")
    require(config.get("created_at_utc") == "2026-08-27T00:00:00Z", "v2_freeze_timestamp_mismatch")
    require(
        config.get("v1_freeze_file")
        == "experiments/rq2_role_prompted_llm/config/personal_local_main_freeze.json"
        and config.get("v1_freeze_sha256") == V1_FREEZE_SHA256,
        "v1_freeze_binding_mismatch",
    )
    require(
        config.get("v1_runner_file")
        == "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py"
        and config.get("v1_runner_sha256") == V1_RUNNER_SHA256,
        "v1_runner_binding_mismatch",
    )
    require(
        config.get("prior_v1_development_selection_file") == V1_SELECTION_RELATIVE
        and config.get("prior_v1_development_selection_sha256") == V1_SELECTION_SHA256
        and config.get("prior_v1_outcomes_reused") is False,
        "v1_selection_exclusion_binding_mismatch",
    )
    require(
        config.get("output_root")
        == "Storage/rq2_personal_local_diagnostic/v2_runs"
        and config.get("run_id_prefix") == "rq2plv2_",
        "v2_output_namespace_mismatch",
    )
    require(
        config.get("lane_packet_counts")
        == {"dreaddit_development": 10, "dreaddit_audit": 5, "agyw_heldout": 5},
        "v2_lane_packet_counts_mismatch",
    )
    require(config.get("qualification_only") is True, "v2_qualification_only_not_enforced")
    require(config.get("reviewer_calls_allowed") is False, "v2_reviewer_calls_enabled")
    require(
        config.get("fixed_role_selection_allowed") is False,
        "v2_fixed_role_selection_enabled",
    )
    require(
        config.get("dreaddit_audit_access_allowed") is False,
        "v2_dreaddit_audit_access_enabled",
    )
    require(
        config.get("agyw_heldout_access_allowed") is False,
        "v2_agyw_heldout_access_enabled",
    )
    require(
        config.get("main_execution_requires_separate_freeze") is True,
        "v2_separate_main_freeze_not_required",
    )
    qualification = config.get("development_qualification")
    require(
        qualification
        == {
            "minimum_admitted_bases": 8,
            "maximum_base_unclear": 2,
            "maximum_comparison_unclear_per_family": 2,
            "minimum_accepted_per_family": 5,
            "minimum_accepted_clusters_per_family": 5,
            "minimum_overall_accepted": 30,
            "fatal_terminal_variant_count": 0,
            "fatal_deterministic_invariant_count": 0,
            "on_failure": "seal_qualification_failed_before_review_or_heldout",
        },
        "v2_qualification_threshold_mismatch",
    )
    outcome_policy = config.get("outcome_policy")
    require(
        outcome_policy
        == {
            "invalid_base": "quarantine_and_skip_all_dependent_variants",
            "terminal_variant": "quarantine_without_retry_or_replacement",
            "semantic_retry_allowed": False,
            "transport_retry_allowed": False,
            "regeneration_allowed": False,
            "replacement_allowed": False,
            "manual_override_allowed": False,
            "cherry_picking_allowed": False,
        },
        "v2_outcome_policy_mismatch",
    )
    labels = config.get("result_labels")
    require(
        labels
        == {
            "result_label": STATUS,
            "evidence_status": EVIDENCE_STATUS,
            "verification_label": VERIFICATION_LABEL,
            "metric_label": METRIC_LABEL,
            "confirmatory_claims_allowed": False,
            "manuscript_use_allowed": False,
            "publication_or_release_allowed": False,
        },
        "v2_result_labels_mismatch",
    )

    v1_config = v1.load_json(V1_CONFIG)
    require(_raw_sha256(V1_CONFIG) == V1_FREEZE_SHA256, "live_v1_freeze_hash_drift")
    v1_paths = v1.validate_freeze(
        v1_config,
        include_record_hashes=include_record_hashes,
        config_path=V1_CONFIG,
    )

    paths = asset_paths(config)
    paths.update(
        {
            "v1_selection": v1.resolve_workspace_path(config["prior_v1_development_selection_file"]),
            "protocol": v1.resolve_workspace_path(config["protocol_file"]),
            "runner_v2": v1.resolve_workspace_path(config["runner_file"]),
            "output_root_v2": v1.resolve_workspace_path(config["output_root"]),
        }
    )
    require(paths["output_root_v2"] == V2_OUTPUT_ROOT, "v2_output_root_resolution_drift")
    expected_hashes = {
        name: row["sha256"] for name, row in config["construction_assets"].items()
    }
    expected_hashes.update(
        {
            "v1_selection": config["prior_v1_development_selection_sha256"],
            "protocol": config["protocol_sha256"],
            "runner_v2": config["runner_sha256"],
        }
    )
    for name, expected in expected_hashes.items():
        require(isinstance(expected, str) and SHA_RE.fullmatch(expected) is not None, f"v2_hash_invalid:{name}")
        path = paths[name]
        require(path.is_file() and not path.is_symlink(), f"v2_static_file_missing:{name}")
        require(v1.sha256_file(path) == expected, f"v2_static_hash_mismatch:{name}")

    acceptance_rule = v1.load_json(paths["rule_construction_comparison_acceptance"])
    require(
        isinstance(acceptance_rule, dict)
        and acceptance_rule.get("verification_label") == VERIFICATION_LABEL
        and labels["verification_label"] == acceptance_rule["verification_label"],
        "v2_verification_label_rule_mismatch",
    )

    old_selection = v1.load_json(paths["v1_selection"])
    require(old_selection.get("contains_source_text") is False, "v1_selection_not_source_free")
    require(old_selection.get("lane") == "dreaddit_development", "v1_selection_lane_mismatch")
    packets = old_selection.get("packets")
    require(isinstance(packets, list) and len(packets) == 5, "v1_selection_packet_count_mismatch")
    excluded_commitments = {
        commitment
        for packet in packets
        if isinstance(packet, dict)
        for commitment in packet.get("selection_cluster_commitments", [])
        if isinstance(commitment, str) and SHA_RE.fullmatch(commitment)
    }
    require(len(excluded_commitments) == 30, "v1_selection_commitment_count_mismatch")
    return v1_config, v1_paths, paths, excluded_commitments


def load_assets(paths: dict[str, Path]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, path in paths.items():
        if key.startswith("schema_") or key.startswith("rule_"):
            result[key] = v1.load_json(path)
        elif key.startswith("prompt_"):
            result[key] = path.read_text(encoding="utf-8")
    return result


def build_run_id_v2(requested: str | None) -> str:
    if requested is None:
        requested = (
            "rq2plv2_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "_"
            + v1.sha256_bytes(os.urandom(32))[:8]
        )
    require(RUN_ID_RE.fullmatch(requested) is not None, "v2_run_id_invalid")
    return requested


def ensure_v2_path(path: Path) -> None:
    lexical = path.absolute()
    require(lexical == V2_OUTPUT_ROOT or V2_OUTPUT_ROOT in lexical.parents, "v2_path_escape")
    v1.guard_output_path(lexical)


def write_v2_json(path: Path, value: Any) -> None:
    ensure_v2_path(path)
    v1.write_json_once(path, value)


def write_v2_bytes(path: Path, value: bytes) -> None:
    ensure_v2_path(path)
    v1.write_bytes_once(path, value)


def initialize_run_v2(
    config: dict[str, Any],
    config_path: Path,
    v1_config: dict[str, Any],
    v1_paths: dict[str, Path],
    run_id: str,
    service: dict[str, Any],
    boundary_evidence: dict[str, Any],
) -> Path:
    v1.ensure_private_directory(V2_OUTPUT_ROOT)
    run_dir = V2_OUTPUT_ROOT / run_id
    ensure_v2_path(run_dir)
    v1.ensure_private_directory(run_dir)
    for relative in (
        "raw/calls",
        "selection",
        "items",
        "base_gate",
        "construction",
        "verification",
        "quarantine",
        "truth",
        "observations",
        "analysis",
    ):
        v1.ensure_private_directory(run_dir / relative)
    v2_freeze_bytes = config_path.read_bytes()
    v1_freeze_bytes = V1_CONFIG.read_bytes()
    policy_bytes = v1_paths["policy"].read_bytes()
    write_v2_bytes(run_dir / "v2_freeze_snapshot.json", v2_freeze_bytes)
    write_v2_bytes(run_dir / "v1_freeze_snapshot.json", v1_freeze_bytes)
    write_v2_bytes(run_dir / "policy_snapshot.json", policy_bytes)
    contract = {
        "document_type": "rq2_personal_local_v2_run_contract",
        "run_id": run_id,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "created_at_utc": utc_now(),
        "v2_freeze_sha256": v1.sha256_bytes(v2_freeze_bytes),
        "v1_freeze_sha256": v1.sha256_bytes(v1_freeze_bytes),
        "v2_runner_sha256": v1.sha256_file(SCRIPT),
        "v1_runner_sha256": V1_RUNNER_SHA256,
        "policy_sha256": v1.sha256_bytes(policy_bytes),
        "python_version": platform.python_version(),
        "service": service,
        "boundary_checks": boundary_evidence,
        "lane_packet_counts": config["lane_packet_counts"],
        "qualification_only": config["qualification_only"],
        "reviewer_calls_allowed": config["reviewer_calls_allowed"],
        "fixed_role_selection_allowed": config["fixed_role_selection_allowed"],
        "dreaddit_audit_access_allowed": config["dreaddit_audit_access_allowed"],
        "agyw_heldout_access_allowed": config["agyw_heldout_access_allowed"],
        "main_execution_requires_separate_freeze": config[
            "main_execution_requires_separate_freeze"
        ],
        "flaw_families": list(FAMILY_ORDER),
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
    contract_path = run_dir / "run_contract.json"
    if v1.safe_exists(contract_path):
        existing = v1.load_json(contract_path)
        for key in (
            "run_id",
            "v2_freeze_sha256",
            "v1_freeze_sha256",
            "v2_runner_sha256",
            "v1_runner_sha256",
            "policy_sha256",
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
        ):
            require(existing.get(key) == contract.get(key), f"v2_resume_contract_drift:{key}")
    else:
        write_v2_json(contract_path, contract)
    return run_dir


def cluster_commitment(record: dict[str, Any], corpus: str) -> str:
    if corpus == "dreaddit":
        raw = record["source_id"]
    else:
        require(isinstance(record.get("speaker_id"), str) and record["speaker_id"], "v2_missing_speaker")
        raw = record["source_id"] + chr(31) + record["speaker_id"]
    return v1.sha256_bytes(raw.encode("utf-8"))


def select_lane_packets_v2(
    v1_config: dict[str, Any],
    v2_config: dict[str, Any],
    run_dir: Path,
    lane_name: str,
    records: Sequence[dict[str, Any]],
    *,
    excluded_commitments: set[str],
    forbidden_current_commitments: set[str] | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    require(
        v2_config.get("qualification_only") is True
        and lane_name == "dreaddit_development",
        "v2_qualification_heldout_selection_forbidden",
    )
    lane = v1_config["lanes"][lane_name]
    filtered = [
        row
        for row in records
        if cluster_commitment(row, lane["corpus"]) not in excluded_commitments
    ]
    plan = v1.deterministic_packet_plan(
        filtered,
        lane_name=lane_name,
        lane=lane,
        seed=int(v1_config["sampling_seed"]),
        packet_count=int(v2_config["lane_packet_counts"][lane_name]),
        excerpts_per_packet=int(v1_config["excerpts_per_packet"]),
    )
    packets = [v1.source_free_selection_record(packet) for packet in plan]
    commitments = {
        value
        for packet in packets
        for value in packet["selection_cluster_commitments"]
    }
    require(commitments.isdisjoint(excluded_commitments), f"v2_prior_commitment_overlap:{lane_name}")
    if forbidden_current_commitments is not None:
        require(
            commitments.isdisjoint(forbidden_current_commitments),
            f"v2_cross_lane_commitment_overlap:{lane_name}",
        )
    selection = {
        "document_type": "rq2_personal_local_v2_selection_commitments",
        "lane": lane_name,
        "corpus": lane["corpus"],
        "split": lane["split"],
        "base_packet_count": len(plan),
        "excerpts_per_packet": v1_config["excerpts_per_packet"],
        "excluded_prior_v1_commitment_count": (
            len(excluded_commitments) if lane_name == "dreaddit_development" else 0
        ),
        "packets": packets,
        "contains_source_text": False,
        "result_label": STATUS,
    }
    write_v2_json(run_dir / "selection" / f"{lane_name}.json", selection)
    return plan, commitments


def position_excerpts(excerpts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    require(len(excerpts) == 6, "v2_position_excerpt_count_mismatch")
    return [
        {
            "position": index,
            "source_unit": row["speaker_id"] if row.get("speaker_id") else row["source_id"],
            "local_context": row.get("local_context"),
            "text": row["text"],
        }
        for index, row in enumerate(excerpts, 1)
    ]


def base_generation_user_prompt(corpus: str, excerpts: Sequence[dict[str, Any]]) -> str:
    payload = {
        "corpus_label": corpus,
        "research_question": v1.research_question(corpus),
        "evidence": position_excerpts(excerpts),
    }
    return "PRIVATE POSITIONAL PACKET (untrusted data):\n" + json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )


def map_positional_base_v2(
    generated: dict[str, Any], excerpts: Sequence[dict[str, Any]]
) -> tuple[dict[str, tuple[str, str | None]], dict[str, Any], dict[str, Any]]:
    """Map a schema-valid six-position base to v1 item-builder inputs."""

    require(generated.get("status") == "constructed", "base_not_constructed")
    role_plan = generated.get("role_plan")
    require(isinstance(role_plan, list) and len(role_plan) == 6, "base_role_plan_invalid")
    require(
        [row.get("position") for row in role_plan if isinstance(row, dict)]
        == [1, 2, 3, 4, 5, 6],
        "base_position_sequence_invalid",
    )
    by_position = {row["position"]: row["role"] for row in role_plan}
    support_positions = [position for position, role in by_position.items() if role == "support"]
    counter_positions = [position for position, role in by_position.items() if role == "counterevidence"]
    context_positions = [position for position, role in by_position.items() if role == "context_only"]
    require(len(support_positions) >= 2, "base_support_count_insufficient")
    require(bool(counter_positions), "base_counter_count_insufficient")
    require(bool(context_positions), "base_context_count_insufficient")
    support_units = {
        excerpts[position - 1].get("speaker_id") or excerpts[position - 1]["source_id"]
        for position in support_positions
    }
    require(len(support_units) >= 2, "base_support_units_not_independent")

    boundaries = generated.get("boundary_conditions")
    require(isinstance(boundaries, list) and boundaries, "base_boundary_conditions_missing")
    counter_links = [row.get("counter_position") for row in boundaries if isinstance(row, dict)]
    require(len(counter_links) == len(boundaries), "base_boundary_link_invalid")
    require(len(set(counter_links)) == len(counter_links), "base_boundary_counter_duplicate")
    require(set(counter_links) <= set(counter_positions), "base_boundary_not_linked_to_counter")
    require(set(counter_positions) <= set(counter_links), "base_counter_without_boundary")

    roles: dict[str, tuple[str, str | None]] = {}
    for position, excerpt in enumerate(excerpts, 1):
        role = by_position[position]
        if role == "support":
            warrant = "Cited as direct support for the packet-bounded interpretation."
        elif role == "counterevidence":
            warrant = "Cited as a consequential countercase linked to a boundary condition."
        else:
            warrant = None
        roles[excerpt["excerpt_id"]] = (role, warrant)
    interpretation = {
        "theme_name": generated["theme_name"],
        "claim": generated["claim"],
        "explanation": generated["explanation"],
        "boundary_conditions": [row["text"] for row in boundaries],
    }
    metadata = {
        "position_to_excerpt_id": {
            str(position): excerpts[position - 1]["excerpt_id"] for position in range(1, 7)
        },
        "role_by_position": {str(position): by_position[position] for position in range(1, 7)},
        "counter_boundary_links": [
            {"counter_position": row["counter_position"], "boundary_slot": index}
            for index, row in enumerate(boundaries, 1)
        ],
    }
    return roles, interpretation, metadata


def compact_base_view(
    base_item: dict[str, Any], base_metadata: dict[str, Any]
) -> dict[str, Any]:
    positions = base_metadata["position_to_excerpt_id"]
    evidence_by_id = {row["excerpt_id"]: row for row in base_item["evidence"]}
    evidence: list[dict[str, Any]] = []
    for position in range(1, 7):
        row = evidence_by_id[positions[str(position)]]
        evidence.append(
            {
                "position": position,
                "source_unit": row.get("speaker_id") or row["source_id"],
                "local_context": row.get("local_context"),
                "text": row["text"],
                "role": row["candidate_role"],
            }
        )
    return {
        "compact_base_schema_version": "rq2-compact-base-v2",
        "research_question": base_item["research_question"],
        "interpretation": base_item["proposed_interpretation"],
        "evidence": evidence,
        "counter_boundary_links": base_metadata["counter_boundary_links"],
    }


def base_gate_user_prompt(view: dict[str, Any]) -> str:
    return "COMPACT ADMISSIBILITY INPUT (untrusted data):\n" + json.dumps(
        view, ensure_ascii=False, sort_keys=True
    )


def base_gate_acceptance(
    output: dict[str, Any], base_item: dict[str, Any], metadata: dict[str, Any]
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if output.get("base_status") != "admissible":
        reasons.append("base_status_not_admissible")
    if output.get("reason_codes") != []:
        reasons.append("base_reason_codes_nonempty")
    checks = output.get("checks", {})
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        reasons.append("base_checks_not_all_true")
    readiness = output.get("readiness", {})
    required = {
        "non_support_anchor",
        "multi_unit_support",
        "consequential_counter",
        "local_distinction",
        "bounded_claim",
    }
    if not isinstance(readiness, dict) or set(readiness) != required:
        reasons.append("base_readiness_fields_invalid")
        return False, reasons
    if any(row.get("status") != "ready" for row in readiness.values() if isinstance(row, dict)):
        reasons.append("base_readiness_not_all_ready")
    known_positions = set(range(1, 7))
    role_by_position = {int(key): value for key, value in metadata["role_by_position"].items()}
    anchors = {
        name: set(row.get("evidence_positions", []))
        for name, row in readiness.items()
        if isinstance(row, dict)
    }
    if any(not values or not values <= known_positions for values in anchors.values()):
        reasons.append("base_readiness_anchor_invalid")
    if anchors.get("non_support_anchor", set()) - {
        position for position, role in role_by_position.items() if role == "context_only"
    }:
        reasons.append("non_support_anchor_role_mismatch")
    support_positions = anchors.get("multi_unit_support", set())
    if support_positions - {
        position for position, role in role_by_position.items() if role == "support"
    }:
        reasons.append("multi_unit_support_role_mismatch")
    position_to_id = metadata["position_to_excerpt_id"]
    evidence_by_id = {row["excerpt_id"]: row for row in base_item["evidence"]}
    support_units = {
        evidence_by_id[position_to_id[str(position)]].get("speaker_id")
        or evidence_by_id[position_to_id[str(position)]]["source_id"]
        for position in support_positions
        if str(position) in position_to_id
    }
    if len(support_units) < 2:
        reasons.append("multi_unit_support_not_independent")
    linked_counters = {row["counter_position"] for row in metadata["counter_boundary_links"]}
    if anchors.get("consequential_counter", set()) - linked_counters:
        reasons.append("consequential_counter_not_boundary_linked")
    if anchors.get("bounded_claim", set()) - {
        position for position, role in role_by_position.items() if role == "support"
    }:
        reasons.append("bounded_claim_anchor_role_mismatch")
    return not reasons, sorted(set(reasons))


def quarantine_path(
    run_dir: Path,
    lane_name: str,
    packet_index: int,
    family_index: int | None,
) -> Path:
    suffix = "base" if family_index is None else f"variant_{family_index:02d}"
    return run_dir / "quarantine" / lane_name / f"packet_{packet_index:02d}_{suffix}.json"


def write_quarantine(
    run_dir: Path,
    *,
    lane_name: str,
    packet_index: int,
    packet_id: str,
    family_index: int | None,
    family: str | None,
    outcome: str,
    reason_codes: Sequence[str],
    call_id: str | None,
) -> None:
    validated_reasons = validate_quarantine_reason_codes(
        scope="base" if family is None else "variant",
        outcome=outcome,
        reason_codes=reason_codes,
    )
    write_v2_json(
        quarantine_path(run_dir, lane_name, packet_index, family_index),
        {
            "document_type": "rq2_personal_local_v2_quarantine_outcome",
            "slot_id": slot_id(lane_name, packet_id, "base" if family is None else family),
            "lane": lane_name,
            "packet_index": packet_index,
            "family_index": family_index,
            "family": family,
            "outcome": outcome,
            "reason_codes": validated_reasons,
            "call_id": call_id,
            "contains_source_text": False,
            "result_label": STATUS,
        },
    )


BASE_SEMANTIC_CODES = {
    "base_not_constructed",
    "base_role_plan_invalid",
    "base_position_sequence_invalid",
    "base_support_count_insufficient",
    "base_counter_count_insufficient",
    "base_context_count_insufficient",
    "base_support_units_not_independent",
    "base_boundary_conditions_missing",
    "base_boundary_link_invalid",
    "base_boundary_counter_duplicate",
    "base_boundary_not_linked_to_counter",
    "base_counter_without_boundary",
}


def run_base_phase_v2(
    v1_config: dict[str, Any],
    paths: dict[str, Path],
    assets: dict[str, Any],
    run_dir: Path,
    lane_name: str,
    records: Sequence[dict[str, Any]],
    plan: Sequence[dict[str, Any]],
    *,
    service_baseline: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate every base, then run the separate compact admissibility gate."""

    lane = v1_config["lanes"][lane_name]
    records_by_id = {row["record_id"]: row for row in records}
    item_schema = v1.load_json(paths["item_schema"])
    base_schema = assets["schema_base_generation"]
    gate_schema = assets["schema_base_admissibility"]
    base_rows: list[dict[str, Any]] = []
    constructed: list[dict[str, Any]] = []
    for packet in plan:
        packet_index = packet["packet_index"]
        packet_id = packet["packet_id"]
        print(
            f"RQ2 v2 private qualification base generation: {lane_name} {packet_index}/{len(plan)}",
            flush=True,
        )
        excerpts = v1.excerpt_payload(packet, lane_name, records_by_id)
        call_id = canonical_base_generation_call_id(lane_name, packet_index)
        result = v1.invoke_checkpointed_call(
            v1_config,
            run_dir,
            call_id=call_id,
            model_role="generator",
            system_prompt=assets["prompt_base_generation"],
            user_prompt=base_generation_user_prompt(lane["corpus"], excerpts),
            output_schema=base_schema,
            rating_call=False,
            rating_repetition=None,
            retry_transport_on_explicit_resume=False,
        )
        row = {
            "slot_id": slot_id(lane_name, packet_id, "base"),
            "lane": lane_name,
            "packet_index": packet_index,
            "packet_id": packet_id,
            "bootstrap_cluster_id": packet["bootstrap_cluster_id"],
            "generation_call_id": call_id,
            "generation_status": result["status"],
            "semantic_status": None,
            "gate_call_id": None,
            "gate_status": "not_attempted",
            "base_status": "generation_terminal",
            "reason_codes": [],
            "base_item_sha256": None,
            "contains_source_text": False,
        }
        if result["status"] != "valid":
            row["reason_codes"] = ["base_generation_terminal"]
            write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=packet_id,
                family_index=None,
                family=None,
                outcome=row["base_status"],
                reason_codes=row["reason_codes"],
                call_id=call_id,
            )
            base_rows.append(row)
            continue
        generated = result["output"]
        if generated.get("status") != "constructed":
            row["semantic_status"] = "not_constructable"
            row["base_status"] = "generator_not_constructable"
            row["reason_codes"] = ["base_generator_not_constructable"] + list(
                generated.get("reason_codes", [])
            )
            write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=packet_id,
                family_index=None,
                family=None,
                outcome=row["base_status"],
                reason_codes=row["reason_codes"],
                call_id=call_id,
            )
            base_rows.append(row)
            continue
        try:
            roles, interpretation, metadata = map_positional_base_v2(generated, excerpts)
        except v1.PersonalLocalError as exc:
            code = str(exc)
            if code not in BASE_SEMANTIC_CODES:
                raise
            row["semantic_status"] = "invalid"
            row["base_status"] = "semantic_invalid"
            row["reason_codes"] = [code]
            write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=packet_id,
                family_index=None,
                family=None,
                outcome=row["base_status"],
                reason_codes=row["reason_codes"],
                call_id=call_id,
            )
            base_rows.append(row)
            continue
        base_item = v1.build_item(
            lane_name=lane_name,
            corpus=lane["corpus"],
            packet_id=packet_id,
            output_key=f"v2-packet-{packet_index}:base",
            interpretation=interpretation,
            roles=roles,
            excerpts=excerpts,
        )
        try:
            jsonschema.validate(base_item, item_schema)
        except jsonschema.ValidationError as exc:
            raise V2Error(f"deterministic_base_item_{finite_schema_error(exc)}") from None
        packet_dir = run_dir / "items" / lane_name / f"packet_{packet_index:02d}"
        v1.ensure_private_directory(packet_dir)
        base_path = packet_dir / "base_item.json"
        metadata_path = packet_dir / "base_mapping.private.json"
        write_v2_json(base_path, base_item)
        write_v2_json(metadata_path, metadata)
        row["semantic_status"] = "valid"
        row["base_status"] = "constructed_pending_gate"
        row["base_item_sha256"] = v1.sha256_file(base_path)
        constructed.append(
            {
                "row": row,
                "base_item": base_item,
                "metadata": metadata,
                "excerpts": excerpts,
            }
        )
        base_rows.append(row)

    # Base admissibility is a separate model phase and sees only compact views.
    if service_baseline is not None:
        v1.recheck_service_identity(v1_config, service_baseline)
    for entry in constructed:
        row = entry["row"]
        packet_index = row["packet_index"]
        packet_id = row["packet_id"]
        call_id = canonical_base_gate_call_id(lane_name, packet_index)
        row["gate_call_id"] = call_id
        view = compact_base_view(entry["base_item"], entry["metadata"])
        input_seal_path = run_dir / "base_gate" / lane_name / f"packet_{packet_index:02d}.input_seal.json"
        write_v2_json(
            input_seal_path,
            {
                "document_type": "rq2_personal_local_v2_base_gate_input_seal",
                "lane": lane_name,
                "packet_index": packet_index,
                "base_item_sha256": v1.sha256_bytes(v1.canonical_bytes(entry["base_item"])),
                "compact_view_sha256": v1.sha256_bytes(v1.canonical_bytes(view)),
                "target_free": True,
                "contains_source_text": False,
            },
        )
        result = v1.invoke_checkpointed_call(
            v1_config,
            run_dir,
            call_id=call_id,
            model_role="verifier",
            system_prompt=assets["prompt_base_admissibility"],
            user_prompt=base_gate_user_prompt(view),
            output_schema=gate_schema,
            rating_call=False,
            rating_repetition=None,
            retry_transport_on_explicit_resume=False,
        )
        output = result.get("output") if result["status"] == "valid" else None
        if output is None:
            admitted = False
            reasons = ["base_gate_terminal"]
            row["base_status"] = "base_gate_terminal"
        else:
            admitted, reasons = base_gate_acceptance(
                output, entry["base_item"], entry["metadata"]
            )
            if admitted:
                row["base_status"] = "admitted"
            elif output.get("base_status") == "unclear":
                row["base_status"] = "base_gate_unclear"
            else:
                row["base_status"] = "base_gate_rejected"
        row["gate_status"] = result["status"]
        row["reason_codes"] = reasons
        report = {
            "document_type": "rq2_personal_local_v2_base_admissibility",
            "lane": lane_name,
            "packet_index": packet_index,
            "slot_id": row["slot_id"],
            "call_id": call_id,
            "status": result["status"],
            "output": output,
            "admitted": admitted,
            "reason_codes": reasons,
            "input_seal_sha256": v1.sha256_file(input_seal_path),
            "contains_source_text": False,
            "verification_label": VERIFICATION_LABEL,
        }
        report_path = run_dir / "base_gate" / lane_name / f"packet_{packet_index:02d}.json"
        write_v2_json(report_path, report)
        if admitted:
            entry["base_gate_output"] = output
            entry["base_gate_report_sha256"] = v1.sha256_file(report_path)
        else:
            write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=packet_id,
                family_index=None,
                family=None,
                outcome=row["base_status"],
                reason_codes=reasons,
                call_id=call_id,
            )

    admitted_entries = [entry for entry in constructed if entry["row"]["base_status"] == "admitted"]
    base_ledger = {
        "document_type": "rq2_personal_local_v2_base_lifecycle",
        "lane": lane_name,
        "planned": len(plan),
        "generation_attempted": len(base_rows),
        "generation_valid": sum(row["generation_status"] == "valid" for row in base_rows),
        "semantic_valid": sum(row["semantic_status"] == "valid" for row in base_rows),
        "base_gate_attempted": sum(row["gate_call_id"] is not None for row in base_rows),
        "base_gate_verified": sum(row["gate_status"] == "valid" for row in base_rows),
        "admitted": len(admitted_entries),
        "unclear": sum(row["base_status"] == "base_gate_unclear" for row in base_rows),
        "rows": base_rows,
        "contains_source_text": False,
        "result_label": STATUS,
    }
    write_v2_json(run_dir / "construction" / f"{lane_name}_bases.json", base_ledger)
    return base_rows, admitted_entries


READINESS_BY_FAMILY = {
    "unsupported_evidence": "non_support_anchor",
    "source_concentration": "multi_unit_support",
    "counterevidence_loss": "consequential_counter",
    "contextual_flattening": "local_distinction",
    "unsupported_abstraction": "bounded_claim",
}


ATOMIC_DIFF_CODE = {
    "unsupported_evidence": "one_preverified_non_support_position_promoted",
    "source_concentration": "multi_unit_support_reduced_to_one_cited_unit",
    "counterevidence_loss": "one_counter_role_and_its_linked_qualification_removed",
    "contextual_flattening": "one_preverified_local_distinction_collapsed",
    "unsupported_abstraction": "bounded_claim_broadened_one_unsupported_level",
}


TARGET_REASON_CODE = {
    "unsupported_evidence": "cited_position_does_not_support_material_claim",
    "source_concentration": "claim_generalizes_beyond_single_cited_unit",
    "counterevidence_loss": "consequential_countercase_qualification_omitted",
    "contextual_flattening": "locally_stated_noncontradictory_distinction_collapsed",
    "unsupported_abstraction": "claim_scope_or_strength_exceeds_displayed_evidence",
}


ALLOWED_ANCHOR_FIELDS = {
    "unsupported_evidence": {"claim", "explanation", "evidence_roles"},
    "source_concentration": {"claim", "explanation", "evidence_roles"},
    "counterevidence_loss": {"boundary_conditions", "evidence_roles"},
    "contextual_flattening": {"claim", "explanation", "boundary_conditions"},
    "unsupported_abstraction": {"claim"},
}

EDIT_SEMANTIC_CODES = {
    "unsupported_ready_role_invalid",
    "concentration_ready_role_invalid",
    "counter_ready_role_invalid",
    "counter_ready_boundary_missing",
    "counter_boundary_slot_invalid",
    "family_readiness_invalid",
    "targeted_edit_not_proposed",
    "targeted_edit_anchor_outside_readiness",
    "flattening_intent_code_invalid",
    "flattening_boundary_slot_invalid",
    "flattening_replacement_unchanged",
    "flattening_field_invalid",
    "abstraction_patch_invalid",
    "abstraction_replacement_unchanged",
}

BASE_GENERATOR_NOT_CONSTRUCTABLE_CODES = {
    "insufficient_independent_support",
    "no_genuine_counterevidence",
    "no_context_only_candidate",
    "cannot_form_packet_bounded_claim",
    "ambiguous_evidence_roles",
    "outside_inference_would_be_required",
}

BASE_GATE_REJECTION_CODES = {
    "base_status_not_admissible",
    "base_reason_codes_nonempty",
    "base_checks_not_all_true",
    "base_readiness_fields_invalid",
    "base_readiness_not_all_ready",
    "base_readiness_anchor_invalid",
    "non_support_anchor_role_mismatch",
    "multi_unit_support_role_mismatch",
    "multi_unit_support_not_independent",
    "consequential_counter_not_boundary_linked",
    "bounded_claim_anchor_role_mismatch",
}

TARGETED_NOT_CONSTRUCTABLE_CODES = {
    "no_consequential_local_distinction",
    "atomic_replacement_not_possible",
    "edit_would_introduce_second_flaw",
    "distinction_anchor_unclear",
    "bounded_claim_not_clear",
    "one_level_broadening_not_possible",
    "outside_fact_would_be_required",
}

STRUCTURAL_REASON_CODES = {
    "structural:packet_unchanged",
    "structural:corpus_unchanged",
    "structural:theme_name_unchanged",
    "structural:evidence_identity_text_context_and_provenance_unchanged",
    "structural:variant_attribution_and_coverage_consistent",
    "structural:anchor_positions_valid",
    "structural:family_signature_exact",
}

COMPARISON_REJECTION_CODES = {
    "family_edit_contract_failed",
    "comparison_terminal_failure",
    "comparison_unclear",
    "present_flaws_not_exact_singleton_target",
    "other_material_flaw",
    "not_single_material_difference",
    "target_anchor_invalid",
    "uncertainty_codes_nonempty",
}


def validate_quarantine_reason_codes(
    *, scope: str, outcome: str, reason_codes: Sequence[str]
) -> list[str]:
    """Reject unbounded error text before any quarantine serialization."""

    allowed_by_outcome = {
        ("base", "generation_terminal"): {"base_generation_terminal"},
        ("base", "generator_not_constructable"): {
            "base_generator_not_constructable",
            *BASE_GENERATOR_NOT_CONSTRUCTABLE_CODES,
        },
        ("base", "semantic_invalid"): BASE_SEMANTIC_CODES,
        ("base", "base_gate_terminal"): {"base_gate_terminal"},
        ("base", "base_gate_unclear"): BASE_GATE_REJECTION_CODES,
        ("base", "base_gate_rejected"): BASE_GATE_REJECTION_CODES,
        ("variant", "skipped_invalid_base"): {"base_not_admitted"},
        ("variant", "generation_terminal"): {"targeted_edit_terminal"},
        ("variant", "not_constructable"): {
            "targeted_edit_not_constructable",
            *TARGETED_NOT_CONSTRUCTABLE_CODES,
        },
        ("variant", "structural_invalid"): (
            EDIT_SEMANTIC_CODES | STRUCTURAL_REASON_CODES
        ),
        ("variant", "rejected_after_comparison"): COMPARISON_REJECTION_CODES,
    }
    key = (scope, outcome)
    require(key in allowed_by_outcome, "v2_reason_code_invalid")
    require(
        not isinstance(reason_codes, (str, bytes))
        and bool(reason_codes)
        and all(isinstance(code, str) for code in reason_codes),
        "v2_reason_code_invalid",
    )
    normalized = sorted(set(reason_codes))
    require(
        bool(normalized) and set(normalized) <= allowed_by_outcome[key],
        "v2_reason_code_invalid",
    )
    return normalized


def canonical_base_generation_call_id(lane_name: str, packet_index: int) -> str:
    return f"generate_{lane_name}_packet_{packet_index:02d}_base_v2"


def canonical_base_gate_call_id(lane_name: str, packet_index: int) -> str:
    return f"verify_{lane_name}_packet_{packet_index:02d}_base_admissibility_v2"


def canonical_targeted_edit_call_id(
    lane_name: str, packet_index: int, family_index: int
) -> str:
    require(family_index in (4, 5), "v2_targeted_edit_family_index_invalid")
    return f"generate_{lane_name}_packet_{packet_index:02d}_edit_{family_index:02d}_v2"


def canonical_comparison_call_id(
    lane_name: str, packet_index: int, family_index: int
) -> str:
    require(1 <= family_index <= len(FAMILY_ORDER), "v2_comparison_family_index_invalid")
    return f"verify_{lane_name}_packet_{packet_index:02d}_comparison_{family_index:02d}_v2"


def interpretation_from_item(item: dict[str, Any]) -> dict[str, Any]:
    value = item["proposed_interpretation"]
    return {
        "theme_name": value["theme_name"],
        "claim": value["claim"],
        "explanation": value["explanation"],
        "boundary_conditions": list(value["boundary_conditions"]),
    }


def role_positions(
    roles: dict[str, tuple[str, str | None]], metadata: dict[str, Any]
) -> dict[int, tuple[str, str | None]]:
    return {
        position: roles[metadata["position_to_excerpt_id"][str(position)]]
        for position in range(1, 7)
    }


def roles_from_positions(
    positioned: dict[int, tuple[str, str | None]], metadata: dict[str, Any]
) -> dict[str, tuple[str, str | None]]:
    return {
        metadata["position_to_excerpt_id"][str(position)]: positioned[position]
        for position in range(1, 7)
    }


def readiness_positions(entry: dict[str, Any], family: str) -> list[int]:
    output = entry["base_gate_output"]
    readiness = output["readiness"][READINESS_BY_FAMILY[family]]
    positions = readiness["evidence_positions"]
    require(
        readiness["status"] == "ready"
        and isinstance(positions, list)
        and positions
        and all(position in range(1, 7) for position in positions),
        "family_readiness_invalid",
    )
    return sorted(positions)


def deterministic_family_edit(
    family: str, entry: dict[str, Any]
) -> tuple[dict[str, tuple[str, str | None]], dict[str, Any], list[int]]:
    require(family in DETERMINISTIC_FAMILIES, "deterministic_family_unknown")
    base_item = entry["base_item"]
    metadata = entry["metadata"]
    roles = role_positions(v1.item_roles(base_item), metadata)
    interpretation = interpretation_from_item(base_item)
    ready = readiness_positions(entry, family)
    if family == "unsupported_evidence":
        selected = ready[0]
        require(roles[selected][0] == "context_only", "unsupported_ready_role_invalid")
        roles[selected] = (
            "support",
            "Presented as direct support for a material claim by the controlled candidate.",
        )
        anchors = [selected]
    elif family == "source_concentration":
        support = [position for position in range(1, 7) if roles[position][0] == "support"]
        require(set(ready) <= set(support) and len(ready) >= 2, "concentration_ready_role_invalid")
        retained = ready[0]
        for position in support:
            if position == retained:
                roles[position] = (
                    "support",
                    "Presented as the sole cited unit for a broader packet-level claim.",
                )
            else:
                roles[position] = ("context_only", None)
        anchors = sorted(support)
    else:
        selected = ready[0]
        require(roles[selected][0] == "counterevidence", "counter_ready_role_invalid")
        links = {
            row["counter_position"]: row["boundary_slot"]
            for row in metadata["counter_boundary_links"]
        }
        require(selected in links, "counter_ready_boundary_missing")
        boundary_slot = links[selected]
        require(
            1 <= boundary_slot <= len(interpretation["boundary_conditions"]),
            "counter_boundary_slot_invalid",
        )
        roles[selected] = ("context_only", None)
        interpretation["boundary_conditions"] = [
            value
            for index, value in enumerate(interpretation["boundary_conditions"], 1)
            if index != boundary_slot
        ]
        anchors = [selected]
    return roles_from_positions(roles, metadata), interpretation, anchors


def targeted_edit_user_prompt(entry: dict[str, Any], family: str) -> str:
    payload = {
        "compact_base": compact_base_view(entry["base_item"], entry["metadata"]),
        "preverified_positions": readiness_positions(entry, family),
    }
    return "ATOMIC EDIT INPUT (untrusted data):\n" + json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )


def apply_targeted_patch(
    family: str,
    entry: dict[str, Any],
    output: dict[str, Any],
) -> tuple[dict[str, tuple[str, str | None]], dict[str, Any], list[int]]:
    require(output.get("status") == "proposed", "targeted_edit_not_proposed")
    patch = output["patch"]
    ready = set(readiness_positions(entry, family))
    anchors = set(patch["evidence_positions"])
    require(bool(anchors) and anchors <= ready, "targeted_edit_anchor_outside_readiness")
    interpretation = interpretation_from_item(entry["base_item"])
    replacement = patch["replacement_text"]
    edit_field = patch["edit_field"]
    if family == "contextual_flattening":
        require(
            patch["edit_intent_code"] == "collapse_one_local_noncontradictory_distinction",
            "flattening_intent_code_invalid",
        )
        if edit_field == "boundary_condition":
            slot = patch["boundary_slot"]
            require(
                1 <= slot <= len(interpretation["boundary_conditions"]),
                "flattening_boundary_slot_invalid",
            )
            require(
                replacement != interpretation["boundary_conditions"][slot - 1],
                "flattening_replacement_unchanged",
            )
            interpretation["boundary_conditions"][slot - 1] = replacement
        else:
            require(edit_field in {"claim", "explanation"}, "flattening_field_invalid")
            require(replacement != interpretation[edit_field], "flattening_replacement_unchanged")
            interpretation[edit_field] = replacement
    else:
        require(family == "unsupported_abstraction", "targeted_family_unknown")
        require(
            edit_field == "claim"
            and patch["edit_intent_code"] == "broaden_claim_exactly_one_unsupported_level",
            "abstraction_patch_invalid",
        )
        require(replacement != interpretation["claim"], "abstraction_replacement_unchanged")
        interpretation["claim"] = replacement
    return v1.item_roles(entry["base_item"]), interpretation, sorted(anchors)


def construction_signature_v2(
    family: str,
    base_item: dict[str, Any],
    variant_item: dict[str, Any],
    anchor_positions: Sequence[int],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    base_interp = interpretation_from_item(base_item)
    variant_interp = interpretation_from_item(variant_item)
    base_roles = role_positions(v1.item_roles(base_item), metadata)
    variant_roles = role_positions(v1.item_roles(variant_item), metadata)
    immutable_evidence_keys = (
        "display_order",
        "excerpt_id",
        "source_id",
        "speaker_id",
        "local_context",
        "text",
    )
    checks: dict[str, bool] = {
        "packet_unchanged": base_item["packet_id"] == variant_item["packet_id"],
        "corpus_unchanged": base_item["corpus_id"] == variant_item["corpus_id"],
        "theme_name_unchanged": base_interp["theme_name"] == variant_interp["theme_name"],
        "evidence_identity_text_context_and_provenance_unchanged": all(
            all(base.get(key) == variant.get(key) for key in immutable_evidence_keys)
            for base, variant in zip(base_item["evidence"], variant_item["evidence"])
        ),
        "variant_attribution_and_coverage_consistent": v1.item_attribution_and_coverage_consistent(
            variant_item
        ),
        "anchor_positions_valid": bool(anchor_positions)
        and set(anchor_positions) <= set(range(1, 7)),
    }
    changed_roles = {
        position
        for position in range(1, 7)
        if base_roles[position][0] != variant_roles[position][0]
    }
    changed_fields = {
        field
        for field in ("claim", "explanation", "boundary_conditions")
        if base_interp[field] != variant_interp[field]
    }
    if family == "unsupported_evidence":
        selected = anchor_positions[0]
        checks["family_signature_exact"] = (
            changed_roles == {selected}
            and base_roles[selected][0] == "context_only"
            and variant_roles[selected][0] == "support"
            and not changed_fields
        )
    elif family == "source_concentration":
        base_support = {
            position for position in range(1, 7) if base_roles[position][0] == "support"
        }
        variant_support = {
            position for position in range(1, 7) if variant_roles[position][0] == "support"
        }
        base_counter = {
            position for position in range(1, 7) if base_roles[position][0] == "counterevidence"
        }
        variant_counter = {
            position for position in range(1, 7) if variant_roles[position][0] == "counterevidence"
        }
        checks["family_signature_exact"] = (
            len(base_support) >= 2
            and len(variant_support) == 1
            and variant_support <= base_support
            and changed_roles == base_support - variant_support
            and base_counter == variant_counter
            and not changed_fields
        )
    elif family == "counterevidence_loss":
        selected = anchor_positions[0]
        checks["family_signature_exact"] = (
            changed_roles == {selected}
            and base_roles[selected][0] == "counterevidence"
            and variant_roles[selected][0] == "context_only"
            and changed_fields == {"boundary_conditions"}
            and len(base_interp["boundary_conditions"])
            == len(variant_interp["boundary_conditions"]) + 1
        )
    elif family == "contextual_flattening":
        checks["family_signature_exact"] = (
            not changed_roles and len(changed_fields) == 1
        )
    elif family == "unsupported_abstraction":
        checks["family_signature_exact"] = (
            not changed_roles and changed_fields == {"claim"}
        )
    else:
        raise V2Error("family_signature_unknown")
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_check_codes": sorted(key for key, value in checks.items() if not value),
        "atomic_diff_code": ATOMIC_DIFF_CODE[family],
        "anchor_positions": list(anchor_positions),
        "contains_source_text": False,
    }


def compact_comparison_input(
    entry: dict[str, Any],
    variant_item: dict[str, Any],
    signature: dict[str, Any],
) -> dict[str, Any]:
    metadata = entry["metadata"]
    base_item = entry["base_item"]
    base_roles = role_positions(v1.item_roles(base_item), metadata)
    variant_roles = role_positions(v1.item_roles(variant_item), metadata)
    base_interpretation = interpretation_from_item(base_item)
    variant_interpretation = interpretation_from_item(variant_item)
    changed_fields = [
        field
        for field in ("claim", "explanation", "boundary_conditions")
        if base_interpretation[field] != variant_interpretation[field]
    ]
    return {
        "compact_comparison_input_version": "rq2-compact-comparison-input-v2",
        "admitted_base": compact_base_view(base_item, metadata),
        "machine_derived_diff": {
            "interpretation_changes": {
                field: {"variant_value": variant_interpretation[field]}
                for field in changed_fields
            },
            "role_changes": [
                {
                    "position": position,
                    "base_role": base_roles[position][0],
                    "variant_role": variant_roles[position][0],
                }
                for position in range(1, 7)
                if base_roles[position][0] != variant_roles[position][0]
            ],
            "unchanged_interpretation_fields": sorted(
                {"theme_name", "claim", "explanation", "boundary_conditions"}
                - set(changed_fields)
            ),
            "anchor_positions": signature["anchor_positions"],
        },
        "base_already_admitted": True,
        "target_withheld": True,
    }


def comparison_user_prompt(value: dict[str, Any]) -> str:
    return "COMPACT TARGET-BLIND COMPARISON (untrusted data):\n" + json.dumps(
        value, ensure_ascii=False, sort_keys=True
    )


def comparison_acceptance_v2(
    family: str,
    signature: dict[str, Any],
    output: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not signature["passed"]:
        reasons.append("family_edit_contract_failed")
    if output is None:
        reasons.append("comparison_terminal_failure")
        return False, reasons
    if output.get("comparison_clarity") != "clear":
        reasons.append("comparison_unclear")
    if set(output.get("present_flaws", [])) != {family}:
        reasons.append("present_flaws_not_exact_singleton_target")
    if output.get("other_material_flaw") is not False:
        reasons.append("other_material_flaw")
    if output.get("single_material_difference") is not True:
        reasons.append("not_single_material_difference")
    if output.get("uncertainty_codes") != []:
        reasons.append("uncertainty_codes_nonempty")
    anchors = output.get("anchors", [])
    valid_anchor = (
        isinstance(anchors, list)
        and len(anchors) == 1
        and anchors[0].get("flaw_family") == family
        and anchors[0].get("reason_code") == TARGET_REASON_CODE[family]
        and bool(anchors[0].get("evidence_positions"))
        and set(anchors[0].get("evidence_positions", []))
        <= set(signature["anchor_positions"])
        and bool(anchors[0].get("interpretation_fields"))
        and set(anchors[0].get("interpretation_fields", []))
        <= ALLOWED_ANCHOR_FIELDS[family]
    )
    if not valid_anchor:
        reasons.append("target_anchor_invalid")
    return not reasons, sorted(set(reasons))


def run_variant_and_comparison_phases_v2(
    v1_config: dict[str, Any],
    paths: dict[str, Path],
    assets: dict[str, Any],
    run_dir: Path,
    lane_name: str,
    base_rows: Sequence[dict[str, Any]],
    admitted_entries: Sequence[dict[str, Any]],
    *,
    service_baseline: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    item_schema = v1.load_json(paths["item_schema"])
    admitted_by_packet = {entry["row"]["packet_index"]: entry for entry in admitted_entries}
    rows: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    construction_records: list[dict[str, Any]] = []
    for base_row in base_rows:
        packet_index = base_row["packet_index"]
        packet_id = base_row["packet_id"]
        entry = admitted_by_packet.get(packet_index)
        for family_index, family in enumerate(FAMILY_ORDER, 1):
            row = {
                "slot_id": slot_id(lane_name, packet_id, family),
                "lane": lane_name,
                "packet_index": packet_index,
                "packet_id": packet_id,
                "bootstrap_cluster_id": base_row["bootstrap_cluster_id"],
                "family_index": family_index,
                "family": family,
                "base_status": base_row["base_status"],
                "attempted": False,
                "construction_mode": (
                    "deterministic_only" if family in DETERMINISTIC_FAMILIES else "targeted_model_patch"
                ),
                "generation_call_id": None,
                "construction_status": "skipped_invalid_base",
                "structural_pass": False,
                "verification_call_id": None,
                "verification_status": "not_attempted",
                "comparison_clarity": None,
                "accepted": False,
                "item_id": None,
                "reason_codes": ["base_not_admitted"],
                "fatal_terminal": False,
                "fatal_invariant": False,
                "contains_source_text": False,
            }
            if entry is None:
                write_quarantine(
                    run_dir,
                    lane_name=lane_name,
                    packet_index=packet_index,
                    packet_id=packet_id,
                    family_index=family_index,
                    family=family,
                    outcome="skipped_invalid_base",
                    reason_codes=row["reason_codes"],
                    call_id=None,
                )
                rows.append(row)
                continue

            row["attempted"] = True
            try:
                if family in DETERMINISTIC_FAMILIES:
                    roles, interpretation, anchors = deterministic_family_edit(family, entry)
                    model_result: dict[str, Any] | None = None
                else:
                    call_id = canonical_targeted_edit_call_id(
                        lane_name, packet_index, family_index
                    )
                    row["generation_call_id"] = call_id
                    print(
                        "RQ2 v2 private qualification targeted edit: "
                        f"{lane_name} packet {packet_index} family {family_index}",
                        flush=True,
                    )
                    key = (
                        "contextual_flattening"
                        if family == "contextual_flattening"
                        else "unsupported_abstraction"
                    )
                    model_result = v1.invoke_checkpointed_call(
                        v1_config,
                        run_dir,
                        call_id=call_id,
                        model_role="generator",
                        system_prompt=assets[f"prompt_{key}_edit"],
                        user_prompt=targeted_edit_user_prompt(entry, family),
                        output_schema=assets[f"schema_{key}_edit"],
                        rating_call=False,
                        rating_repetition=None,
                        retry_transport_on_explicit_resume=False,
                    )
                    if model_result["status"] != "valid":
                        row["construction_status"] = "generation_terminal"
                        row["fatal_terminal"] = True
                        row["reason_codes"] = ["targeted_edit_terminal"]
                        write_quarantine(
                            run_dir,
                            lane_name=lane_name,
                            packet_index=packet_index,
                            packet_id=packet_id,
                            family_index=family_index,
                            family=family,
                            outcome=row["construction_status"],
                            reason_codes=row["reason_codes"],
                            call_id=call_id,
                        )
                        rows.append(row)
                        continue
                    edit_output = model_result["output"]
                    if edit_output.get("status") != "proposed":
                        row["construction_status"] = "not_constructable"
                        row["reason_codes"] = ["targeted_edit_not_constructable"] + list(
                            edit_output.get("reason_codes", [])
                        )
                        write_quarantine(
                            run_dir,
                            lane_name=lane_name,
                            packet_index=packet_index,
                            packet_id=packet_id,
                            family_index=family_index,
                            family=family,
                            outcome=row["construction_status"],
                            reason_codes=row["reason_codes"],
                            call_id=call_id,
                        )
                        rows.append(row)
                        continue
                    roles, interpretation, anchors = apply_targeted_patch(
                        family, entry, edit_output
                    )
            except v1.PersonalLocalError as exc:
                # At this point every model output is schema-valid.  A finite
                # family edit/mapping failure is recorded and fails the gate;
                # integrity/checkpoint/service failures are never caught here.
                code = str(exc)
                if code not in EDIT_SEMANTIC_CODES:
                    raise
                row["construction_status"] = "structural_invalid"
                row["fatal_invariant"] = True
                row["reason_codes"] = [code]
                write_quarantine(
                    run_dir,
                    lane_name=lane_name,
                    packet_index=packet_index,
                    packet_id=packet_id,
                    family_index=family_index,
                    family=family,
                    outcome=row["construction_status"],
                    reason_codes=row["reason_codes"],
                    call_id=row["generation_call_id"],
                )
                rows.append(row)
                continue

            variant_item = v1.build_item(
                lane_name=lane_name,
                corpus=v1_config["lanes"][lane_name]["corpus"],
                packet_id=packet_id,
                output_key=f"v2-packet-{packet_index}:{family}",
                interpretation=interpretation,
                roles=roles,
                excerpts=entry["excerpts"],
            )
            try:
                jsonschema.validate(variant_item, item_schema)
            except jsonschema.ValidationError as exc:
                raise V2Error(f"deterministic_variant_item_{finite_schema_error(exc)}") from None
            signature = construction_signature_v2(
                family, entry["base_item"], variant_item, anchors, entry["metadata"]
            )
            row["structural_pass"] = signature["passed"]
            if not signature["passed"]:
                row["construction_status"] = "structural_invalid"
                row["fatal_invariant"] = True
                row["reason_codes"] = [
                    f"structural:{code}" for code in signature["failed_check_codes"]
                ]
                write_quarantine(
                    run_dir,
                    lane_name=lane_name,
                    packet_index=packet_index,
                    packet_id=packet_id,
                    family_index=family_index,
                    family=family,
                    outcome=row["construction_status"],
                    reason_codes=row["reason_codes"],
                    call_id=row["generation_call_id"],
                )
                rows.append(row)
                continue
            packet_dir = run_dir / "items" / lane_name / f"packet_{packet_index:02d}"
            variant_path = packet_dir / f"variant_{family_index:02d}.json"
            construction_path = packet_dir / f"variant_{family_index:02d}.construction.private.json"
            construction = {
                "slot_id": row["slot_id"],
                "item_id": variant_item["item_id"],
                "family": family,
                "family_index": family_index,
                "construction_mode": row["construction_mode"],
                "generation_call_id": row["generation_call_id"],
                "atomic_diff_code": signature["atomic_diff_code"],
                "anchor_positions": signature["anchor_positions"],
                "structural_signature": signature,
                "base_gate_report_sha256": entry["base_gate_report_sha256"],
                "contains_source_text": False,
            }
            write_v2_json(variant_path, variant_item)
            write_v2_json(construction_path, construction)
            row["construction_status"] = "constructed"
            row["item_id"] = variant_item["item_id"]
            row["reason_codes"] = []
            construction_records.append(construction)
            cases.append(
                {
                    "row": row,
                    "entry": entry,
                    "variant_item": variant_item,
                    "signature": signature,
                    "variant_path": variant_path,
                }
            )
            rows.append(row)

    write_v2_json(
        run_dir / "construction" / f"{lane_name}.private.json",
        {
            "document_type": "rq2_personal_local_v2_finite_constructions",
            "lane": lane_name,
            "records": construction_records,
            "contains_source_text": False,
            "result_label": STATUS,
        },
    )

    if service_baseline is not None:
        v1.recheck_service_identity(v1_config, service_baseline)
    comparison_schema = assets["schema_construction_comparison"]
    accepted_truths: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for index, case in enumerate(cases, 1):
        row = case["row"]
        packet_index = row["packet_index"]
        family_index = row["family_index"]
        family = row["family"]
        call_id = canonical_comparison_call_id(lane_name, packet_index, family_index)
        row["verification_call_id"] = call_id
        comparison_input = compact_comparison_input(
            case["entry"], case["variant_item"], case["signature"]
        )
        input_seal_path = (
            run_dir
            / "verification"
            / lane_name
            / f"packet_{packet_index:02d}_variant_{family_index:02d}.input_seal.json"
        )
        write_v2_json(
            input_seal_path,
            {
                "document_type": "rq2_personal_local_v2_comparison_input_seal",
                "slot_id": row["slot_id"],
                "base_gate_report_sha256": case["entry"]["base_gate_report_sha256"],
                "variant_item_sha256": v1.sha256_file(case["variant_path"]),
                "compact_comparison_input_sha256": v1.sha256_bytes(
                    v1.canonical_bytes(comparison_input)
                ),
                "target_withheld_from_verifier": True,
                "contains_source_text": False,
            },
        )
        print(
            f"RQ2 v2 private qualification comparison: {lane_name} {index}/{len(cases)}",
            flush=True,
        )
        result = v1.invoke_checkpointed_call(
            v1_config,
            run_dir,
            call_id=call_id,
            model_role="verifier",
            system_prompt=assets["prompt_construction_comparison"],
            user_prompt=comparison_user_prompt(comparison_input),
            output_schema=comparison_schema,
            rating_call=False,
            rating_repetition=None,
            retry_transport_on_explicit_resume=False,
        )
        output = result.get("output") if result["status"] == "valid" else None
        accepted, reasons = comparison_acceptance_v2(family, case["signature"], output)
        row["verification_status"] = result["status"]
        row["comparison_clarity"] = output.get("comparison_clarity") if output else None
        row["accepted"] = accepted
        row["reason_codes"] = reasons
        if result["status"] != "valid":
            row["fatal_terminal"] = True
        report = {
            "document_type": "rq2_personal_local_v2_construction_comparison",
            "slot_id": row["slot_id"],
            "lane": lane_name,
            "packet_index": packet_index,
            "family_index": family_index,
            "call_id": call_id,
            "status": result["status"],
            "output": output,
            "accepted": accepted,
            "reason_codes": reasons,
            "input_seal_sha256": v1.sha256_file(input_seal_path),
            "target_withheld_from_verifier": True,
            "contains_source_text": False,
            "verification_label": VERIFICATION_LABEL,
        }
        report_path = (
            run_dir
            / "verification"
            / lane_name
            / f"packet_{packet_index:02d}_variant_{family_index:02d}.json"
        )
        write_v2_json(report_path, report)
        reports.append(report)
        if accepted:
            accepted_truths.append(
                {
                    "item_id": row["item_id"],
                    "slot_id": row["slot_id"],
                    "packet_id": row["packet_id"],
                    "lane": lane_name,
                    "target_flaw": family,
                    "required_flag": v1_config["target_to_flag_mapping"][family],
                    "bootstrap_cluster_id": row["bootstrap_cluster_id"],
                    "verification_status": VERIFICATION_LABEL,
                    "verification_artifact_sha256": v1.sha256_file(report_path),
                }
            )
        else:
            write_quarantine(
                run_dir,
                lane_name=lane_name,
                packet_index=packet_index,
                packet_id=row["packet_id"],
                family_index=family_index,
                family=family,
                outcome="rejected_after_comparison",
                reason_codes=reasons,
                call_id=call_id,
            )

    summary = reconcile_lane_funnel_v2(base_rows, rows)
    write_v2_json(
        run_dir / "construction" / f"{lane_name}_variants.json",
        {
            "document_type": "rq2_personal_local_v2_variant_lifecycle",
            "lane": lane_name,
            "rows": rows,
            "summary": summary,
            "contains_source_text": False,
            "result_label": STATUS,
        },
    )
    write_v2_json(
        run_dir / "verification" / f"{lane_name}_summary.json",
        {
            "document_type": "rq2_personal_local_v2_comparison_summary",
            "lane": lane_name,
            **summary,
            "verification_label": VERIFICATION_LABEL,
            "metric_label": METRIC_LABEL,
            "contains_source_text": False,
        },
    )
    write_v2_json(
        run_dir / "truth" / f"{lane_name}.private.json",
        {
            "document_type": "rq2_personal_local_v2_accepted_qualification_truth",
            "lane": lane_name,
            "records": accepted_truths,
            "verification_label": VERIFICATION_LABEL,
            "human_ground_truth": False,
            "result_label": STATUS,
        },
    )
    return rows, accepted_truths, summary


def reconcile_lane_funnel_v2(
    base_rows: Sequence[dict[str, Any]], variant_rows: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    require(bool(base_rows), "v2_base_rows_empty")
    require(
        all(type(row.get("packet_index")) is int for row in base_rows),
        "v2_base_packet_index_invalid",
    )
    require(
        len({row["packet_index"] for row in base_rows}) == len(base_rows),
        "v2_base_packet_duplicate",
    )
    require(
        {row["packet_index"] for row in base_rows}
        == set(range(1, len(base_rows) + 1)),
        "v2_base_packet_sequence_invalid",
    )
    base_by_packet = {row["packet_index"]: row for row in base_rows}
    base_statuses = {
        "generation_terminal",
        "generator_not_constructable",
        "semantic_invalid",
        "base_gate_terminal",
        "base_gate_unclear",
        "base_gate_rejected",
        "admitted",
    }
    for base in base_rows:
        lane_name = base.get("lane")
        packet_index = base["packet_index"]
        packet_id = base.get("packet_id")
        require(lane_name == "dreaddit_development", "v2_base_lane_mismatch")
        require(isinstance(packet_id, str) and bool(packet_id), "v2_base_packet_id_invalid")
        require(
            base.get("slot_id") == slot_id(lane_name, packet_id, "base"),
            "v2_base_slot_id_mismatch",
        )
        require(
            base.get("generation_call_id")
            == canonical_base_generation_call_id(lane_name, packet_index),
            "v2_base_call_id_mismatch",
        )
        semantic_valid = base.get("semantic_status") == "valid"
        expected_gate_call = (
            canonical_base_gate_call_id(lane_name, packet_index)
            if semantic_valid
            else None
        )
        require(base.get("gate_call_id") == expected_gate_call, "v2_base_call_id_mismatch")
        require(
            (base.get("base_item_sha256") is not None) is semantic_valid,
            "v2_base_item_lifecycle_mismatch",
        )
        base_status = base.get("base_status")
        require(base_status in base_statuses, "v2_base_status_invalid")
        if base_status == "admitted":
            require(
                base.get("generation_status") == "valid"
                and semantic_valid
                and base.get("gate_status") == "valid"
                and base.get("reason_codes") == [],
                "v2_base_admission_lifecycle_mismatch",
            )
        else:
            validate_quarantine_reason_codes(
                scope="base",
                outcome=base_status,
                reason_codes=base.get("reason_codes", []),
            )

    require(
        all(type(row.get("family_index")) is int for row in variant_rows),
        "v2_variant_family_position_mismatch",
    )
    for row in variant_rows:
        packet_index = row.get("packet_index")
        family_index = row["family_index"]
        require(packet_index in base_by_packet, "v2_variant_base_lifecycle_mismatch")
        require(
            1 <= family_index <= len(FAMILY_ORDER),
            "v2_variant_family_position_mismatch",
        )
        family = FAMILY_ORDER[family_index - 1]
        require(row.get("family") == family, "v2_variant_family_position_mismatch")
        base = base_by_packet[packet_index]
        require(
            row.get("lane") == base.get("lane")
            and row.get("packet_id") == base.get("packet_id")
            and row.get("bootstrap_cluster_id") == base.get("bootstrap_cluster_id")
            and row.get("base_status") == base.get("base_status"),
            "v2_variant_base_lifecycle_mismatch",
        )
        require(
            row.get("slot_id")
            == slot_id(base["lane"], base["packet_id"], family),
            "v2_variant_slot_id_mismatch",
        )
        expected_mode = (
            "deterministic_only"
            if family in DETERMINISTIC_FAMILIES
            else "targeted_model_patch"
        )
        require(
            row.get("construction_mode") == expected_mode,
            "v2_variant_family_position_mismatch",
        )

        if base["base_status"] != "admitted":
            require(
                row.get("attempted") is False
                and row.get("construction_status") == "skipped_invalid_base"
                and row.get("structural_pass") is False
                and row.get("generation_call_id") is None
                and row.get("verification_call_id") is None
                and row.get("verification_status") == "not_attempted"
                and row.get("comparison_clarity") is None
                and row.get("accepted") is False
                and row.get("item_id") is None
                and row.get("reason_codes") == ["base_not_admitted"]
                and row.get("fatal_terminal") is False
                and row.get("fatal_invariant") is False,
                "v2_variant_base_lifecycle_mismatch",
            )
            continue

        require(
            row.get("attempted") is True
            and row.get("construction_status") != "skipped_invalid_base",
            "v2_variant_base_lifecycle_mismatch",
        )
        expected_generation_call = (
            canonical_targeted_edit_call_id(
                base["lane"], packet_index, family_index
            )
            if family in GENERATED_EDIT_FAMILIES
            else None
        )
        require(
            row.get("generation_call_id") == expected_generation_call,
            "v2_variant_call_id_mismatch",
        )
        construction_status = row.get("construction_status")
        require(
            construction_status
            in {"generation_terminal", "not_constructable", "structural_invalid", "constructed"},
            "v2_variant_construction_status_invalid",
        )
        if construction_status == "constructed":
            require(
                row.get("verification_call_id")
                == canonical_comparison_call_id(
                    base["lane"], packet_index, family_index
                ),
                "v2_variant_call_id_mismatch",
            )
            require(
                row.get("structural_pass") is True
                and isinstance(row.get("item_id"), str)
                and bool(row.get("item_id"))
                and row.get("verification_status") != "not_attempted"
                and row.get("fatal_invariant") is False,
                "v2_variant_base_lifecycle_mismatch",
            )
            if row.get("accepted") is True:
                require(
                    row.get("verification_status") == "valid"
                    and row.get("comparison_clarity") == "clear"
                    and row.get("reason_codes") == []
                    and row.get("fatal_terminal") is False,
                    "v2_variant_base_lifecycle_mismatch",
                )
            else:
                validate_quarantine_reason_codes(
                    scope="variant",
                    outcome="rejected_after_comparison",
                    reason_codes=row.get("reason_codes", []),
                )
                require(
                    row.get("fatal_terminal")
                    is (row.get("verification_status") != "valid"),
                    "v2_variant_base_lifecycle_mismatch",
                )
        else:
            require(
                row.get("verification_call_id") is None
                and row.get("verification_status") == "not_attempted"
                and row.get("comparison_clarity") is None
                and row.get("accepted") is False
                and row.get("item_id") is None
                and row.get("structural_pass") is False,
                "v2_variant_base_lifecycle_mismatch",
            )
            validate_quarantine_reason_codes(
                scope="variant",
                outcome=construction_status,
                reason_codes=row.get("reason_codes", []),
            )
            require(
                row.get("fatal_terminal") is (construction_status == "generation_terminal")
                and row.get("fatal_invariant") is (construction_status == "structural_invalid"),
                "v2_variant_base_lifecycle_mismatch",
            )

    expected_slots = {
        (base["packet_index"], family_index)
        for base in base_rows
        for family_index in range(1, len(FAMILY_ORDER) + 1)
    }
    observed_slots = {(row["packet_index"], row["family_index"]) for row in variant_rows}
    require(
        len(variant_rows) == len(expected_slots) and observed_slots == expected_slots,
        "v2_variant_slot_grid_mismatch",
    )
    require(len({row["slot_id"] for row in variant_rows}) == len(variant_rows), "v2_variant_slot_id_duplicate")

    def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
        planned = len(rows)
        skipped = sum(row["construction_status"] == "skipped_invalid_base" for row in rows)
        attempted = sum(row["attempted"] is True for row in rows)
        constructed = sum(row["construction_status"] == "constructed" for row in rows)
        preverification = sum(
            row["attempted"] is True and row["construction_status"] != "constructed"
            for row in rows
        )
        verification_attempted = sum(row["verification_call_id"] is not None for row in rows)
        verified = sum(row["verification_status"] == "valid" for row in rows)
        verifier_terminal = sum(
            row["verification_call_id"] is not None and row["verification_status"] != "valid"
            for row in rows
        )
        accepted = sum(row["accepted"] is True for row in rows)
        valid_rejected = sum(
            row["verification_status"] == "valid" and row["accepted"] is not True
            for row in rows
        )
        require(planned == skipped + attempted, "v2_funnel_planned_equation_failed")
        require(attempted == constructed + preverification, "v2_funnel_attempted_equation_failed")
        require(constructed == verification_attempted, "v2_funnel_constructed_equation_failed")
        require(
            verification_attempted == verified + verifier_terminal,
            "v2_funnel_verification_equation_failed",
        )
        require(verified == accepted + valid_rejected, "v2_funnel_verified_equation_failed")
        return {
            "planned": planned,
            "skipped_invalid_base": skipped,
            "attempted": attempted,
            "constructed": constructed,
            "preverification_quarantined": preverification,
            "verification_attempted": verification_attempted,
            "verified": verified,
            "verifier_terminal": verifier_terminal,
            "verifier_valid_rejected": valid_rejected,
            "accepted": accepted,
            "accepted_independent_clusters": len(
                {row["bootstrap_cluster_id"] for row in rows if row["accepted"] is True}
            ),
            "comparison_unclear": sum(row["comparison_clarity"] == "unclear" for row in rows),
            "fatal_terminal": sum(row["fatal_terminal"] is True for row in rows),
            "fatal_invariant": sum(row["fatal_invariant"] is True for row in rows),
            "reviewed": 0,
            "analyzed": 0,
        }

    overall = summarize(variant_rows)
    by_family = {
        family: summarize([row for row in variant_rows if row["family"] == family])
        for family in FAMILY_ORDER
    }
    for key in (
        "planned",
        "skipped_invalid_base",
        "attempted",
        "constructed",
        "preverification_quarantined",
        "verification_attempted",
        "verified",
        "verifier_terminal",
        "verifier_valid_rejected",
        "accepted",
        "comparison_unclear",
        "fatal_terminal",
        "fatal_invariant",
        "reviewed",
        "analyzed",
    ):
        require(
            overall[key] == sum(row[key] for row in by_family.values()),
            f"v2_family_sum_mismatch:{key}",
        )
    return {
        **overall,
        "by_family": by_family,
        "base_funnel": {
            "planned": len(base_rows),
            "generation_attempted": len(base_rows),
            "generation_valid": sum(row["generation_status"] == "valid" for row in base_rows),
            "semantic_valid": sum(row["semantic_status"] == "valid" for row in base_rows),
            "base_gate_attempted": sum(row["gate_call_id"] is not None for row in base_rows),
            "base_gate_verified": sum(row["gate_status"] == "valid" for row in base_rows),
            "admitted": sum(row["base_status"] == "admitted" for row in base_rows),
            "unclear": sum(row["base_status"] == "base_gate_unclear" for row in base_rows),
            "terminal": sum(
                row["base_status"] in {"generation_terminal", "base_gate_terminal"}
                for row in base_rows
            ),
        },
    }


def evaluate_development_qualification_v2(
    config: dict[str, Any],
    run_dir: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    thresholds = config["development_qualification"]
    base = summary["base_funnel"]
    checks: dict[str, dict[str, Any]] = {
        "minimum_admitted_bases": {
            "observed": base["admitted"],
            "operator": ">=",
            "required": thresholds["minimum_admitted_bases"],
            "passed": base["admitted"] >= thresholds["minimum_admitted_bases"],
        },
        "maximum_base_unclear": {
            "observed": base["unclear"],
            "operator": "<=",
            "required": thresholds["maximum_base_unclear"],
            "passed": base["unclear"] <= thresholds["maximum_base_unclear"],
        },
        "fatal_terminal_count": {
            "observed": base["terminal"] + summary["fatal_terminal"],
            "operator": "==",
            "required": thresholds["fatal_terminal_variant_count"],
            "passed": base["terminal"] + summary["fatal_terminal"]
            == thresholds["fatal_terminal_variant_count"],
        },
        "fatal_deterministic_invariant_count": {
            "observed": summary["fatal_invariant"],
            "operator": "==",
            "required": thresholds["fatal_deterministic_invariant_count"],
            "passed": summary["fatal_invariant"]
            == thresholds["fatal_deterministic_invariant_count"],
        },
        "minimum_overall_accepted": {
            "observed": summary["accepted"],
            "operator": ">=",
            "required": thresholds["minimum_overall_accepted"],
            "passed": summary["accepted"] >= thresholds["minimum_overall_accepted"],
        },
    }
    family_checks: dict[str, Any] = {}
    for family in FAMILY_ORDER:
        values = summary["by_family"][family]
        family_checks[family] = {
            "maximum_comparison_unclear": {
                "observed": values["comparison_unclear"],
                "operator": "<=",
                "required": thresholds["maximum_comparison_unclear_per_family"],
                "passed": values["comparison_unclear"]
                <= thresholds["maximum_comparison_unclear_per_family"],
            },
            "minimum_accepted": {
                "observed": values["accepted"],
                "operator": ">=",
                "required": thresholds["minimum_accepted_per_family"],
                "passed": values["accepted"] >= thresholds["minimum_accepted_per_family"],
            },
            "minimum_accepted_clusters": {
                "observed": values["accepted_independent_clusters"],
                "operator": ">=",
                "required": thresholds["minimum_accepted_clusters_per_family"],
                "passed": values["accepted_independent_clusters"]
                >= thresholds["minimum_accepted_clusters_per_family"],
            },
        }
    passed = all(row["passed"] for row in checks.values()) and all(
        row["passed"] for family in family_checks.values() for row in family.values()
    )
    gate = {
        "document_type": "rq2_personal_local_v2_development_qualification_gate",
        "scope": "fresh_dreaddit_development_qualification_only",
        "passed": passed,
        "run_outcome": "qualification_passed" if passed else "qualification_failed",
        "checks": checks,
        "family_checks": family_checks,
        "funnel_sha256": v1.sha256_bytes(v1.canonical_bytes(summary)),
        "no_reviewer_calls_allowed_in_this_freeze": True,
        "no_fixed_role_selection_allowed_in_this_freeze": True,
        "no_heldout_access_allowed_in_this_freeze": True,
        "continuation_requires_separate_bound_v2_main_freeze": True,
        "contains_source_text": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    gate_path = run_dir / "qualification_gate.json"
    write_v2_json(gate_path, gate)
    gate_seal = {
        "document_type": "rq2_personal_local_v2_development_qualification_gate_seal",
        "run_id": run_dir.name,
        "qualification_gate_sha256": v1.sha256_file(gate_path),
        "v2_freeze_sha256": v1.sha256_file(run_dir / "v2_freeze_snapshot.json"),
        "run_outcome": gate["run_outcome"],
        "contains_source_text": False,
        "result_label": STATUS,
    }
    write_v2_json(run_dir / "qualification_gate.seal.json", gate_seal)
    return gate


def write_qualification_analysis_v2(
    config: dict[str, Any],
    run_dir: Path,
    summary: dict[str, Any],
    gate: dict[str, Any],
    boundary_evidence: dict[str, Any],
) -> dict[str, Any]:
    operations = v1.aggregate_call_attempt_operations(run_dir)
    result = {
        "document_type": "rq2_personal_local_v2_qualification_analysis",
        "run_id": run_dir.name,
        "run_outcome": gate["run_outcome"],
        "scope": "construction_qualification_only",
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "metric_label": METRIC_LABEL,
        "contains_source_text": False,
        "funnel": summary,
        "qualification_gate": gate,
        "all_call_attempt_operations": operations,
        "reviewer_calls": 0,
        "fixed_role_selected": False,
        "heldout_lanes_opened": False,
        "v1_results_reused": False,
        "human_ground_truth": False,
        "qualification_is_rq2_performance_result": False,
        "boundary_checks": boundary_evidence,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    write_v2_json(run_dir / "analysis" / "qualification_results.json", result)
    write_v2_json(
        run_dir / "run_terminal_status.json",
        {
            "document_type": "rq2_personal_local_v2_terminal_status",
            "run_id": run_dir.name,
            "run_outcome": gate["run_outcome"],
            "qualification_only": True,
            "continuation_requires_separate_bound_v2_main_freeze": True,
            "contains_source_text": False,
            "result_label": STATUS,
        },
    )
    return result


def validate_run_completeness_v2(run_dir: Path, config: dict[str, Any]) -> None:
    require(RUN_ID_RE.fullmatch(run_dir.name) is not None, "v2_completeness_run_id_invalid")
    base_ledger = v1.load_json(run_dir / "construction" / "dreaddit_development_bases.json")
    variant_ledger = v1.load_json(
        run_dir / "construction" / "dreaddit_development_variants.json"
    )
    base_rows = base_ledger.get("rows")
    variant_rows = variant_ledger.get("rows")
    require(isinstance(base_rows, list) and len(base_rows) == 10, "v2_seal_base_rows_invalid")
    require(isinstance(variant_rows, list) and len(variant_rows) == 50, "v2_seal_variant_rows_invalid")
    summary = reconcile_lane_funnel_v2(base_rows, variant_rows)
    require(variant_ledger.get("summary") == summary, "v2_variant_summary_drift")
    require(base_ledger.get("planned") == 10, "v2_base_ledger_planned_drift")

    gate_path = run_dir / "qualification_gate.json"
    gate = v1.load_json(gate_path)
    require(
        gate.get("run_outcome") in {"qualification_passed", "qualification_failed"},
        "v2_gate_outcome_invalid",
    )
    require(
        gate.get("funnel_sha256") == v1.sha256_bytes(v1.canonical_bytes(summary)),
        "v2_gate_funnel_hash_drift",
    )
    gate_seal = v1.load_json(run_dir / "qualification_gate.seal.json")
    require(
        gate_seal.get("qualification_gate_sha256") == v1.sha256_file(gate_path)
        and gate_seal.get("run_outcome") == gate["run_outcome"],
        "v2_gate_seal_drift",
    )
    analysis = v1.load_json(run_dir / "analysis" / "qualification_results.json")
    require(
        analysis.get("funnel") == summary
        and analysis.get("qualification_gate") == gate
        and analysis.get("reviewer_calls") == 0
        and analysis.get("fixed_role_selected") is False
        and analysis.get("heldout_lanes_opened") is False,
        "v2_qualification_analysis_drift",
    )
    terminal = v1.load_json(run_dir / "run_terminal_status.json")
    require(
        terminal.get("run_outcome") == gate["run_outcome"]
        and terminal.get("qualification_only") is True,
        "v2_terminal_status_drift",
    )
    truth = v1.load_json(run_dir / "truth" / "dreaddit_development.private.json")
    truth_rows = truth.get("records")
    require(isinstance(truth_rows, list), "v2_truth_records_invalid")
    accepted_slots = {row["slot_id"] for row in variant_rows if row["accepted"] is True}
    require(
        {row.get("slot_id") for row in truth_rows} == accepted_slots
        and len(truth_rows) == summary["accepted"],
        "v2_truth_acceptance_mismatch",
    )

    expected_files = {
        "v2_freeze_snapshot.json",
        "v1_freeze_snapshot.json",
        "policy_snapshot.json",
        "run_contract.json",
        "selection/dreaddit_development.json",
        "construction/dreaddit_development_bases.json",
        "construction/dreaddit_development_variants.json",
        "construction/dreaddit_development.private.json",
        "verification/dreaddit_development_summary.json",
        "truth/dreaddit_development.private.json",
        "qualification_gate.json",
        "qualification_gate.seal.json",
        "analysis/qualification_results.json",
        "run_terminal_status.json",
    }
    expected_call_ids: set[str] = set()
    base_by_packet = {row["packet_index"]: row for row in base_rows}
    for row in base_rows:
        packet_index = row["packet_index"]
        lane_name = row["lane"]
        expected_call_ids.add(
            canonical_base_generation_call_id(lane_name, packet_index)
        )
        if row["semantic_status"] == "valid":
            expected_files.update(
                {
                    f"items/dreaddit_development/packet_{packet_index:02d}/base_item.json",
                    f"items/dreaddit_development/packet_{packet_index:02d}/base_mapping.private.json",
                }
            )
            expected_call_ids.add(canonical_base_gate_call_id(lane_name, packet_index))
            expected_files.update(
                {
                    f"base_gate/dreaddit_development/packet_{packet_index:02d}.input_seal.json",
                    f"base_gate/dreaddit_development/packet_{packet_index:02d}.json",
                }
            )
        if row["base_status"] != "admitted":
            expected_files.add(
                f"quarantine/dreaddit_development/packet_{packet_index:02d}_base.json"
            )
    for row in variant_rows:
        packet_index = row["packet_index"]
        family_index = row["family_index"]
        base = base_by_packet[packet_index]
        if (
            base["base_status"] == "admitted"
            and FAMILY_ORDER[family_index - 1] in GENERATED_EDIT_FAMILIES
        ):
            expected_call_ids.add(
                canonical_targeted_edit_call_id(
                    base["lane"], packet_index, family_index
                )
            )
        if row["construction_status"] == "constructed":
            expected_files.update(
                {
                    f"items/dreaddit_development/packet_{packet_index:02d}/variant_{family_index:02d}.json",
                    f"items/dreaddit_development/packet_{packet_index:02d}/variant_{family_index:02d}.construction.private.json",
                    f"verification/dreaddit_development/packet_{packet_index:02d}_variant_{family_index:02d}.input_seal.json",
                    f"verification/dreaddit_development/packet_{packet_index:02d}_variant_{family_index:02d}.json",
                }
            )
            expected_call_ids.add(
                canonical_comparison_call_id(
                    base["lane"], packet_index, family_index
                )
            )
        if row["accepted"] is not True:
            expected_files.add(
                "quarantine/dreaddit_development/"
                f"packet_{packet_index:02d}_variant_{family_index:02d}.json"
            )

    calls_root = run_dir / "raw" / "calls"
    with os.scandir(calls_root) as entries:
        call_entries = sorted(entries, key=lambda value: value.name)
    require(
        {entry.name for entry in call_entries} == expected_call_ids,
        "v2_raw_call_id_set_mismatch",
    )
    for entry in call_entries:
        require(stat.S_ISDIR(entry.stat(follow_symlinks=False).st_mode), "v2_call_entry_not_directory")
        call_dir = calls_root / entry.name
        contract = v1.load_json(call_dir / "call_contract.json")
        require(
            contract.get("call_id") == entry.name
            and contract.get("lane") == "dreaddit_development"
            and contract.get("call_kind") in {"construction", "construction_verification"}
            and contract.get("retry_transport_on_explicit_resume") is False,
            "v2_call_contract_drift",
        )
        names = v1.regular_child_names(call_dir)
        allowed = re.compile(
            r"^(?:call_contract|success|attempt_01_(?:request|response|error))\.json$"
        )
        require(all(allowed.fullmatch(name) for name in names), "v2_call_checkpoint_file_invalid")
        require(
            "attempt_01_request.json" in names and "attempt_01_response.json" in names,
            "v2_call_attempt_incomplete",
        )
        require(
            ("success.json" in names) ^ ("attempt_01_error.json" in names),
            "v2_call_final_state_invalid",
        )
        for name in names:
            expected_files.add(f"raw/calls/{entry.name}/{name}")

    inventory_paths = {row["path"] for row in v1.safe_run_inventory(run_dir)}
    require(inventory_paths == expected_files, "v2_sealed_inventory_path_mismatch")
    require(
        not any(
            path.startswith("observations/")
            or "fixed_role" in path
            or "dreaddit_audit" in path
            or "agyw_heldout" in path
            for path in inventory_paths
        ),
        "v2_qualification_contains_forbidden_downstream_artifact",
    )
    operations = v1.aggregate_call_attempt_operations(run_dir)
    require(
        operations["logical_calls_started"] == len(expected_call_ids)
        and operations["physical_attempts"] == len(expected_call_ids)
        and operations["by_call_kind"]["role_review"]["logical_calls"] == 0,
        "v2_operation_call_count_mismatch",
    )
    require(
        analysis.get("all_call_attempt_operations") == operations,
        "v2_analysis_operation_summary_drift",
    )


def validate_output_seal_v2(run_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    seal_path = run_dir / "output_seal.json"
    require(v1.safe_exists(seal_path), "v2_output_seal_missing")
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
            "qualification_gate_sha256",
            "qualification_results_sha256",
            "this_manifest_contains_source_text",
            "sealed_run_contains_restricted_source_text",
            "qualification_only",
            "manuscript_eligible",
            "publication_or_release_eligible",
            "confirmatory_claims_allowed",
        },
        "v2_seal_fields_mismatch",
    )
    require(
        seal.get("document_type") == "rq2_personal_local_v2_qualification_output_seal"
        and seal.get("run_id") == run_dir.name
        and seal.get("run_outcome")
        == v1.load_json(run_dir / "qualification_gate.json")["run_outcome"],
        "v2_seal_identity_drift",
    )
    entries = seal.get("files")
    require(isinstance(entries, list), "v2_seal_inventory_invalid")
    require(entries == v1.safe_run_inventory(run_dir), "v2_seal_inventory_or_hash_mismatch")
    require(
        seal.get("seal_payload_sha256") == v1.sha256_bytes(v1.canonical_bytes(entries)),
        "v2_seal_payload_hash_mismatch",
    )
    require(
        seal.get("qualification_gate_sha256")
        == v1.sha256_file(run_dir / "qualification_gate.json")
        and seal.get("qualification_results_sha256")
        == v1.sha256_file(run_dir / "analysis" / "qualification_results.json"),
        "v2_seal_result_hash_mismatch",
    )
    require(
        seal.get("result_label") == STATUS
        and seal.get("evidence_status") == EVIDENCE_STATUS
        and seal.get("this_manifest_contains_source_text") is False
        and seal.get("sealed_run_contains_restricted_source_text") is True
        and seal.get("qualification_only") is True
        and seal.get("manuscript_eligible") is False
        and seal.get("publication_or_release_eligible") is False
        and seal.get("confirmatory_claims_allowed") is False,
        "v2_seal_boundary_flags_drift",
    )
    validate_run_completeness_v2(run_dir, config)
    return seal


def seal_run_v2(run_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    seal_path = run_dir / "output_seal.json"
    if v1.safe_exists(seal_path):
        return validate_output_seal_v2(run_dir, config)
    validate_run_completeness_v2(run_dir, config)
    entries = v1.safe_run_inventory(run_dir)
    gate = v1.load_json(run_dir / "qualification_gate.json")
    seal = {
        "document_type": "rq2_personal_local_v2_qualification_output_seal",
        "run_id": run_dir.name,
        "run_outcome": gate["run_outcome"],
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "sealed_at_utc": utc_now(),
        "files": entries,
        "seal_payload_sha256": v1.sha256_bytes(v1.canonical_bytes(entries)),
        "qualification_gate_sha256": v1.sha256_file(run_dir / "qualification_gate.json"),
        "qualification_results_sha256": v1.sha256_file(
            run_dir / "analysis" / "qualification_results.json"
        ),
        "this_manifest_contains_source_text": False,
        "sealed_run_contains_restricted_source_text": True,
        "qualification_only": True,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
        "confirmatory_claims_allowed": False,
    }
    write_v2_json(seal_path, seal)
    return validate_output_seal_v2(run_dir, config)


def execute_v2(config_path: Path, requested_run_id: str | None) -> Path:
    os.umask(0o077)
    config = v1.load_json(config_path)
    v1_config, v1_paths, paths, excluded_commitments = validate_v2_freeze(
        config,
        include_record_hashes=True,
        config_path=config_path,
    )
    policy_evidence = v1.run_exact_policy_validator(
        v1_paths, v1_config["policy_file_sha256"]
    )
    boundary_evidence = {
        "readiness_scope_assessment_status": "passed",
        "readiness_scope_assessment_only": True,
        "readiness_report_sha256": v1_config["readiness_report_file_sha256"],
        "policy_validator_status": policy_evidence["policy_check_status"],
        "policy_validator_sha256": v1_config["policy_validator_file_sha256"],
        "policy_sha256": policy_evidence["policy_sha256"],
        "exact_policy_bound_input_hashes_verified": policy_evidence[
            "bound_input_hashes_verified"
        ],
        "independent_runner_bound_input_hashes_verified": True,
        "v1_runner_hash_verified_before_import": True,
        "v1_results_reused": False,
        "prior_selection_commitments_used_only_for_exclusion": True,
        "qualification_only": True,
        "contains_source_text": False,
    }
    service = v1.preflight_service(v1_config)
    run_id = build_run_id_v2(requested_run_id)
    run_dir = initialize_run_v2(
        config,
        config_path,
        v1_config,
        v1_paths,
        run_id,
        service,
        boundary_evidence,
    )
    if v1.safe_exists(run_dir / "output_seal.json"):
        validate_output_seal_v2(run_dir, config)
        # Continue through exact checkpoint reconstruction.  An inventory seal
        # is not a substitute for rebuilding frozen request semantics.

    assets = load_assets(paths)
    required_assets = {
        "prompt_base_generation",
        "schema_base_generation",
        "prompt_base_admissibility",
        "schema_base_admissibility",
        "rule_base_admissibility",
        "rule_family_edit_contract",
        "prompt_contextual_flattening_edit",
        "schema_contextual_flattening_edit",
        "prompt_unsupported_abstraction_edit",
        "schema_unsupported_abstraction_edit",
        "prompt_construction_comparison",
        "schema_construction_comparison",
        "rule_construction_comparison_acceptance",
        "rule_construction_qualification_thresholds",
    }
    require(required_assets <= set(assets), "v2_runtime_asset_set_incomplete")

    # The qualification freeze never opens either held-out lane.
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
    plan, _ = select_lane_packets_v2(
        v1_config,
        config,
        run_dir,
        lane_name,
        records,
        excluded_commitments=excluded_commitments,
    )
    v1.recheck_service_identity(v1_config, service)
    base_rows, admitted_entries = run_base_phase_v2(
        v1_config,
        v1_paths,
        assets,
        run_dir,
        lane_name,
        records,
        plan,
        service_baseline=service,
    )
    v1.recheck_service_identity(v1_config, service)
    _, _, summary = run_variant_and_comparison_phases_v2(
        v1_config,
        v1_paths,
        assets,
        run_dir,
        lane_name,
        base_rows,
        admitted_entries,
        service_baseline=service,
    )
    del records
    del admitted_entries
    gate = evaluate_development_qualification_v2(config, run_dir, summary)
    write_qualification_analysis_v2(config, run_dir, summary, gate, boundary_evidence)
    v1.recheck_service_identity(v1_config, service)
    seal_run_v2(run_dir, config)
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "dry-run",
        help="Validate frozen source-free artifacts; do not open records or contact Ollama.",
    )
    subparsers.add_parser(
        "preflight-service",
        help="Validate source-free artifacts and local Ollama metadata; do not open records.",
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Execute or resume only the fresh ten-packet development qualification.",
    )
    run_parser.add_argument("--run-id", help="Existing or new rq2plv2_YYYYMMDDTHHMMSSZ_abcdefgh ID")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.absolute()
    try:
        config = v1.load_json(config_path)
        if args.command == "dry-run":
            validate_v2_freeze(config, include_record_hashes=False, config_path=config_path)
            print("RQ2 v2 source-free qualification dry run passed.")
            return 0
        if args.command == "preflight-service":
            v1_config, _, _, _ = validate_v2_freeze(
                config, include_record_hashes=False, config_path=config_path
            )
            report = v1.preflight_service(v1_config)
            source_free = {
                "status": "passed",
                "endpoint": report["endpoint"],
                "endpoint_is_numeric_loopback": report["endpoint_is_numeric_loopback"],
                "ollama_version": report["ollama_version"],
                "models": {
                    role: {"model_id": row["model_id"], "digest": row["digest"]}
                    for role, row in report["models"].items()
                },
                "qualification_only": True,
                "contains_source_text": False,
            }
            print(json.dumps(source_free, sort_keys=True))
            return 0
        run_dir = execute_v2(config_path, args.run_id)
        outcome = v1.load_json(run_dir / "qualification_gate.json")["run_outcome"]
        print(f"RQ2 v2 private qualification sealed: {run_dir.name} {outcome}")
        return 0
    except (v1.PersonalLocalError, V2Error) as exc:
        print(f"RQ2 v2 qualification stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
