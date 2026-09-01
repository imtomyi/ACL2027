#!/usr/bin/env python3
"""Fail-closed formal Qwen3 Generalist runner for the Dreaddit test row.

The runner remains unusable until a formal readiness report, an authorized
scoring study freeze, a packet-bank integrity seal, and a runner execution
freeze agree exactly.  It validates all source-free metadata before checking
or opening the source-bearing packet bank and before contacting Ollama.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import stat
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment preflight
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
CONTRACT = RQ2_ROOT / "protocol" / "qwen3_generalist_formal_run_contract_v1.md"
PACKET_STUDY_FREEZE_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_packet_study_freeze_v1.schema.json"
)
PACKET_TRUTH_MAP_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_truth_cluster_map_v1.schema.json"
)
DEFAULT_READINESS = WORKSPACE / "governance" / "local" / "readiness_report.local.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_qwen3_generalist_score as scoring  # noqa: E402
import run_qwen3_generalist_reviewer as reviewer  # noqa: E402


EXPECTED_REVIEWER_ACTOR = "qwen3_8b_generalist_reviewer_v1"
EXPECTED_MODEL_ID = "qwen3:8b"
EXPECTED_CORPUS_ID = "dreaddit"
EXPECTED_SPLIT = "test"
EXPECTED_EVALUATION_ROLE = "in_domain_audit"
EXPECTED_METHOD = "Generalist"
EXPECTED_PRIMARY_REPETITION = 1
EXPECTED_RATING_REPETITIONS = 3
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_NETWORK_CAPABILITY = object()

PACKET_BANK_KEYS = {
    "document_type",
    "schema_version",
    "study_id",
    "corpus_id",
    "official_source_split",
    "evaluation_role",
    "privacy_clearance_status",
    "items",
}
PACKET_SEAL_KEYS = {
    "document_type",
    "seal_version",
    "seal_id",
    "seal_status",
    "authorization_claimed_by_this_seal",
    "contains_source_text",
    "manuscript_result",
    "study_id",
    "corpus_id",
    "official_source_split",
    "evaluation_role",
    "reviewer_actor_id",
    "reviewer_model_id",
    "reviewer_model_snapshot_sha256",
    "candidate_generator_actor_id",
    "candidate_generator_model_id",
    "candidate_generator_snapshot_sha256",
    "candidate_generator_prompt_sha256",
    "fixed_n",
    "item_count",
    "item_id_set_sha256",
    "packet_bank_complete",
    "privacy_cleared",
    "family_counts",
    "post_cluster_count",
    "privacy_cleared_excerpt_count",
    "formal_dreaddit_gates_verified",
    "bindings",
    "warning",
}
PACKET_SEAL_BINDING_KEYS = {
    "study_freeze_sha256",
    "packet_study_freeze_sha256",
    "study_design_freeze_sha256",
    "readiness_report_sha256",
    "governance_record_sha256",
    "governance_source_record_sha256",
    "reviewer_registry_sha256",
    "privacy_review_log_sha256",
    "packet_manifest_sha256",
    "source_receipt_sha256",
    "source_test_file_sha256",
    "preaccess_record_sha256",
    "verification_bundle_sha256",
    "verification_seal_sha256",
    "candidate_generator_snapshot_sha256",
    "candidate_generator_prompt_sha256",
    "reviewer_model_snapshot_sha256",
    "packet_bank_sha256",
    "truth_cluster_map_sha256",
    "study_freeze_schema_sha256",
    "truth_cluster_map_schema_sha256",
    "packet_manifest_schema_sha256",
    "preaccess_record_schema_sha256",
    "verification_bundle_schema_sha256",
    "verification_seal_schema_sha256",
    "evaluator_item_schema_sha256",
    "generalist_component_freeze_sha256",
    "scoring_contract_sha256",
    "analysis_code_sha256",
    "heldout_preaccess_record_sha256",
}
EXECUTION_FREEZE_KEYS = {
    "document_type",
    "execution_version",
    "status",
    "frozen_at_utc",
    "contains_source_text",
    "study_freeze_sha256",
    "readiness_report_sha256",
    "packet_bank_seal_sha256",
    "packet_bank_sha256",
    "packet_bank_item_count",
    "item_id_set_sha256",
    "runner_sha256",
    "runner_contract_sha256",
    "primary_repetition",
    "failure_policy",
    "output_policy",
    "packet_seal_bindings",
    "raw_retention_deletion_scope",
}
OUTPUT_POLICY = {
    "directory_class": "private_storage_only",
    "scoring_bundle_contains_source_text": False,
    "raw_execution_bundle_contains_source_text": True,
    "overwrite_allowed": False,
    "raw_requests_retained": True,
    "raw_responses_retained": True,
    "raw_execution_access": "restricted_mode_0600_storage",
    "rationale_projection": "fixed_source_free_redaction",
}


class FormalRunnerError(RuntimeError):
    """Finite content-free failure suitable for a terminal report."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FormalRunnerError(code)


def exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value),
        f"{label}_sha256_invalid",
    )
    return value


def parse_utc(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label}_utc_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FormalRunnerError(f"{label}_utc_invalid") from exc
    require(parsed.tzinfo is not None, f"{label}_utc_invalid")
    return parsed.astimezone(timezone.utc)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_absolute_regular_file(
    path: Path,
    *,
    allowed_root: Path,
    code_prefix: str,
    required_mode: int = 0o600,
) -> None:
    require(path.is_absolute(), f"{code_prefix}_path_not_absolute")
    require(path.resolve(strict=False) == path, f"{code_prefix}_path_resolution_drift")
    require(is_within(path, allowed_root), f"{code_prefix}_outside_allowed_root")
    require(not path.is_symlink(), f"{code_prefix}_path_is_symlink")
    require(path.is_file(), f"{code_prefix}_file_missing")
    require(
        stat.S_IMODE(path.stat().st_mode) == required_mode,
        f"{code_prefix}_file_mode_invalid",
    )
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"{code_prefix}_parent_invalid")
    require(
        stat.S_IMODE(path.parent.stat().st_mode) == 0o700,
        f"{code_prefix}_parent_mode_invalid",
    )


def read_regular_bytes(path: Path, *, code_prefix: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise FormalRunnerError(f"{code_prefix}_file_unavailable") from exc
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), f"{code_prefix}_not_regular_file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def load_json_bytes(value: bytes, *, code_prefix: str) -> dict[str, Any]:
    try:
        result = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FormalRunnerError(f"{code_prefix}_invalid_json") from exc
    require(isinstance(result, dict), f"{code_prefix}_root_not_object")
    return result


def read_private_metadata(
    path: Path,
    *,
    workspace: Path,
    storage: bool,
    code_prefix: str,
) -> tuple[dict[str, Any], bytes]:
    root = workspace / ("Storage" if storage else "governance/local")
    require_absolute_regular_file(path, allowed_root=root, code_prefix=code_prefix)
    value = read_regular_bytes(path, code_prefix=code_prefix)
    return load_json_bytes(value, code_prefix=code_prefix), value


def validate_packet_seal(
    seal: dict[str, Any],
    *,
    seal_bytes: bytes,
    freeze: dict[str, Any],
    readiness_hash: str,
    component_hash: str,
    evaluator_schema_hash: str,
) -> dict[str, Any]:
    exact_keys(seal, PACKET_SEAL_KEYS, "packet_seal")
    require(
        seal["document_type"] == "warrantroute_qwen3_generalist_packet_bank_seal",
        "packet_seal_document_type_invalid",
    )
    require(
        seal["seal_version"] == "qwen3-generalist-packet-bank-seal-v1",
        "packet_seal_version_invalid",
    )
    require(
        seal["seal_status"] == "integrity_validated_not_authorization",
        "packet_seal_status_invalid",
    )
    require(seal["authorization_claimed_by_this_seal"] is False, "packet_seal_claims_authorization")
    require(seal["contains_source_text"] is False, "packet_seal_contains_source_text")
    require(seal["manuscript_result"] is False, "packet_seal_claims_result")
    require(seal["corpus_id"] == EXPECTED_CORPUS_ID, "packet_seal_corpus_drift")
    require(seal["official_source_split"] == EXPECTED_SPLIT, "packet_seal_split_drift")
    require(seal["evaluation_role"] == EXPECTED_EVALUATION_ROLE, "packet_seal_role_drift")
    require(seal["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "packet_seal_actor_drift")
    require(seal["reviewer_model_id"] == EXPECTED_MODEL_ID, "packet_seal_model_drift")
    require(
        seal["reviewer_model_snapshot_sha256"] == reviewer.EXPECTED_MODEL_DIGEST,
        "packet_seal_reviewer_snapshot_drift",
    )
    generator = freeze["candidate_generation_separation"]["candidate_generator_actor_id"]
    generator_snapshot = freeze["candidate_generation_separation"][
        "candidate_generator_snapshot_sha256"
    ]
    require(generator != EXPECTED_REVIEWER_ACTOR, "candidate_generator_not_distinct")
    require(seal["candidate_generator_actor_id"] == generator, "packet_seal_generator_drift")
    require(
        isinstance(seal["candidate_generator_model_id"], str)
        and seal["candidate_generator_model_id"].strip()
        and seal["candidate_generator_model_id"].strip().casefold()
        != EXPECTED_MODEL_ID.casefold(),
        "packet_seal_generator_model_invalid",
    )
    require(
        seal["candidate_generator_snapshot_sha256"] == generator_snapshot
        and generator_snapshot != reviewer.EXPECTED_MODEL_DIGEST,
        "packet_seal_generator_snapshot_drift",
    )
    require_sha256(seal["candidate_generator_prompt_sha256"], "packet_seal_generator_prompt")
    require(seal["seal_id"] == freeze["packet_bank"]["seal_id"], "packet_seal_id_drift")
    require(
        sha256_bytes(seal_bytes) == freeze["packet_bank"]["seal_sha256"],
        "packet_seal_hash_drift",
    )
    require(
        seal["fixed_n"] == seal["item_count"] == freeze["packet_bank"]["item_count"],
        "packet_seal_item_count_drift",
    )
    require(
        seal["item_id_set_sha256"] == freeze["packet_bank"]["item_id_set_sha256"],
        "packet_seal_item_set_drift",
    )
    require(seal["packet_bank_complete"] is True, "packet_seal_bank_incomplete")
    require(seal["privacy_cleared"] is True, "packet_seal_privacy_not_cleared")
    require(seal["formal_dreaddit_gates_verified"] == "10/10", "packet_seal_formal_gates_invalid")
    require(isinstance(seal["study_id"], str) and seal["study_id"], "packet_seal_study_id_invalid")
    require(isinstance(seal["family_counts"], dict) and seal["family_counts"], "packet_seal_family_counts_invalid")
    require(
        sum(seal["family_counts"].values()) == seal["item_count"]
        and all(type(value) is int and value > 0 for value in seal["family_counts"].values()),
        "packet_seal_family_counts_drift",
    )
    require(type(seal["post_cluster_count"]) is int and seal["post_cluster_count"] > 0, "packet_seal_cluster_count_invalid")
    require(
        type(seal["privacy_cleared_excerpt_count"]) is int
        and seal["privacy_cleared_excerpt_count"] >= seal["item_count"],
        "packet_seal_privacy_count_invalid",
    )
    bindings = seal["bindings"]
    require(isinstance(bindings, dict), "packet_seal_bindings_invalid")
    exact_keys(bindings, PACKET_SEAL_BINDING_KEYS, "packet_seal_bindings")
    for key, value in bindings.items():
        require_sha256(value, f"packet_seal_binding_{key}")
    require(bindings["readiness_report_sha256"] == readiness_hash, "packet_seal_readiness_drift")
    evidence = freeze.get("evidence_records", {})
    require(isinstance(evidence, dict), "study_freeze_evidence_records_invalid")
    require(
        bindings["packet_study_freeze_sha256"]
        == bindings["study_freeze_sha256"]
        == evidence.get("packet_study_freeze_sha256"),
        "packet_seal_packet_study_freeze_drift",
    )
    require(
        bindings["governance_record_sha256"]
        == bindings["governance_source_record_sha256"]
        == evidence.get("governance_record_sha256"),
        "packet_seal_governance_record_drift",
    )
    require(
        bindings["reviewer_registry_sha256"] == evidence.get("reviewer_registry_sha256"),
        "packet_seal_reviewer_registry_drift",
    )
    require(
        bindings["privacy_review_log_sha256"] == evidence.get("privacy_review_log_sha256"),
        "packet_seal_privacy_log_drift",
    )
    require(
        bindings["source_receipt_sha256"] == evidence.get("source_receipt_sha256"),
        "packet_seal_source_receipt_drift",
    )
    require(
        bindings["preaccess_record_sha256"]
        == bindings["heldout_preaccess_record_sha256"]
        == freeze["preaccess"]["record_sha256"],
        "packet_seal_preaccess_record_drift",
    )
    require(
        bindings["candidate_generator_snapshot_sha256"]
        == seal["candidate_generator_snapshot_sha256"],
        "packet_seal_generator_snapshot_binding_drift",
    )
    require(
        bindings["candidate_generator_prompt_sha256"]
        == seal["candidate_generator_prompt_sha256"],
        "packet_seal_generator_prompt_binding_drift",
    )
    require(
        bindings["reviewer_model_snapshot_sha256"]
        == seal["reviewer_model_snapshot_sha256"],
        "packet_seal_reviewer_snapshot_binding_drift",
    )
    require(
        bindings["generalist_component_freeze_sha256"] == component_hash,
        "packet_seal_component_drift",
    )
    require(
        bindings["evaluator_item_schema_sha256"] == evaluator_schema_hash,
        "packet_seal_evaluator_schema_drift",
    )
    require(
        bindings["scoring_contract_sha256"] == freeze["assets"]["scoring_contract_sha256"],
        "packet_seal_scoring_contract_drift",
    )
    require(
        bindings["study_freeze_schema_sha256"]
        == sha256_bytes(read_regular_bytes(PACKET_STUDY_FREEZE_SCHEMA, code_prefix="packet_study_schema")),
        "packet_seal_study_schema_drift",
    )
    require(
        bindings["truth_cluster_map_schema_sha256"]
        == sha256_bytes(read_regular_bytes(PACKET_TRUTH_MAP_SCHEMA, code_prefix="packet_truth_schema")),
        "packet_seal_truth_schema_drift",
    )
    require(
        bindings["analysis_code_sha256"] == freeze["assets"]["scoring_exporter_sha256"],
        "packet_seal_analysis_code_drift",
    )
    require(
        bindings["heldout_preaccess_record_sha256"] == freeze["preaccess"]["record_sha256"],
        "packet_seal_preaccess_record_drift",
    )
    return {
        "packet_bank_sha256": bindings["packet_bank_sha256"],
        "item_count": seal["item_count"],
        "item_id_set_sha256": seal["item_id_set_sha256"],
        "seal_id": seal["seal_id"],
        "bindings": dict(bindings),
    }


def validate_execution_freeze(
    execution: dict[str, Any],
    *,
    study_freeze: dict[str, Any],
    study_freeze_bytes: bytes,
    readiness_bytes: bytes,
    packet_seal_bytes: bytes,
    packet_seal_metadata: dict[str, Any],
) -> None:
    exact_keys(execution, EXECUTION_FREEZE_KEYS, "execution_freeze")
    require(
        execution["document_type"] == "warrantroute_qwen3_generalist_execution_freeze_v1",
        "execution_freeze_document_type_invalid",
    )
    require(
        isinstance(execution["execution_version"], str) and execution["execution_version"],
        "execution_freeze_version_invalid",
    )
    require(execution["status"] == "bound_to_authorized_study_freeze", "execution_freeze_status_invalid")
    require(execution["contains_source_text"] is False, "execution_freeze_contains_source_text")
    execution_at = parse_utc(execution["frozen_at_utc"], "execution_frozen_at")
    study_at = parse_utc(study_freeze["frozen_at_utc"], "study_frozen_at")
    require(execution_at >= study_at, "execution_freeze_predates_study_freeze")
    require(
        execution["study_freeze_sha256"] == sha256_bytes(study_freeze_bytes),
        "execution_study_freeze_hash_drift",
    )
    require(
        execution["readiness_report_sha256"] == sha256_bytes(readiness_bytes),
        "execution_readiness_hash_drift",
    )
    require(
        execution["packet_bank_seal_sha256"] == sha256_bytes(packet_seal_bytes),
        "execution_packet_seal_hash_drift",
    )
    require(
        execution["packet_bank_sha256"] == packet_seal_metadata["packet_bank_sha256"],
        "execution_packet_bank_hash_drift",
    )
    require(
        execution["packet_bank_item_count"] == packet_seal_metadata["item_count"],
        "execution_item_count_drift",
    )
    require(
        execution["item_id_set_sha256"] == packet_seal_metadata["item_id_set_sha256"],
        "execution_item_set_drift",
    )
    require(
        execution["runner_sha256"] == sha256_bytes(read_regular_bytes(SCRIPT, code_prefix="runner")),
        "execution_runner_hash_drift",
    )
    require(
        execution["runner_contract_sha256"]
        == sha256_bytes(read_regular_bytes(CONTRACT, code_prefix="runner_contract")),
        "execution_runner_contract_hash_drift",
    )
    require(execution["primary_repetition"] == EXPECTED_PRIMARY_REPETITION, "execution_repetition_drift")
    require(
        execution["failure_policy"] == "one_attempt_per_item_all_failures_retained_as_misses",
        "execution_failure_policy_drift",
    )
    require(execution["output_policy"] == OUTPUT_POLICY, "execution_output_policy_drift")
    packet_bindings = execution["packet_seal_bindings"]
    require(isinstance(packet_bindings, dict), "execution_packet_seal_bindings_invalid")
    exact_keys(packet_bindings, PACKET_SEAL_BINDING_KEYS, "execution_packet_seal_bindings")
    require(
        packet_bindings == packet_seal_metadata["bindings"],
        "execution_packet_seal_bindings_drift",
    )
    retention = execution["raw_retention_deletion_scope"]
    require(isinstance(retention, dict), "raw_retention_scope_invalid")
    exact_keys(
        retention,
        {
            "approval_record_id",
            "approval_record_sha256",
            "readiness_gate_id",
            "storage_scope",
            "raw_source_bearing_records_approved",
            "authorized_accessor_group_id",
            "retention_until_utc",
            "deletion_required",
            "deletion_record_required",
        },
        "raw_retention_scope",
    )
    authorization = study_freeze["authorization"]
    require(
        retention["approval_record_id"] == authorization["approval_record_id"],
        "raw_retention_approval_id_drift",
    )
    require(
        retention["approval_record_sha256"] == authorization["approval_record_sha256"],
        "raw_retention_approval_hash_drift",
    )
    require(
        retention["readiness_gate_id"] == "retention_deletion_controls",
        "raw_retention_gate_invalid",
    )
    require(
        retention["storage_scope"] == "restricted_mode_0600_storage",
        "raw_retention_storage_scope_invalid",
    )
    require(
        retention["raw_source_bearing_records_approved"] is True,
        "raw_retention_not_approved",
    )
    require(
        isinstance(retention["authorized_accessor_group_id"], str)
        and retention["authorized_accessor_group_id"],
        "raw_retention_accessor_group_missing",
    )
    require(
        parse_utc(retention["retention_until_utc"], "raw_retention_until") > execution_at,
        "raw_retention_window_invalid",
    )
    require(retention["deletion_required"] is True, "raw_deletion_not_required")
    require(retention["deletion_record_required"] is True, "raw_deletion_record_not_required")


def validate_metadata(
    *,
    execution_freeze_path: Path,
    study_freeze_path: Path,
    readiness_report_path: Path,
    packet_bank_seal_path: Path,
    workspace: Path = WORKSPACE,
) -> dict[str, Any]:
    """Validate every source-free prerequisite before source or network access."""

    workspace = workspace.resolve()
    execution, execution_bytes = read_private_metadata(
        execution_freeze_path,
        workspace=workspace,
        storage=False,
        code_prefix="execution_freeze",
    )
    study, study_bytes = read_private_metadata(
        study_freeze_path,
        workspace=workspace,
        storage=False,
        code_prefix="study_freeze",
    )
    readiness, readiness_bytes = read_private_metadata(
        readiness_report_path,
        workspace=workspace,
        storage=False,
        code_prefix="readiness",
    )
    packet_seal, packet_seal_bytes = read_private_metadata(
        packet_bank_seal_path,
        workspace=workspace,
        storage=True,
        code_prefix="packet_seal",
    )

    try:
        component, assets, component_hash = scoring.load_component()
        rating_schema_path = reviewer.workspace_path(
            component["assets"]["shared_rating_schema"]["file"]
        )
        rating_schema_hash = sha256_bytes(
            read_regular_bytes(rating_schema_path, code_prefix="rating_schema")
        )
        study_metadata = scoring.validate_study_freeze(
            study,
            component_hash=component_hash,
            rating_schema_hash=rating_schema_hash,
        )
        readiness_hash = scoring.validate_readiness_report(
            readiness,
            report_bytes=readiness_bytes,
            freeze=study,
            frozen_at=study_metadata["frozen_at"],
        )
    except (scoring.ScoringExportError, reviewer.GeneralistReviewerError) as exc:
        raise FormalRunnerError(f"formal_metadata_invalid:{exc}") from exc

    seal_metadata = validate_packet_seal(
        packet_seal,
        seal_bytes=packet_seal_bytes,
        freeze=study,
        readiness_hash=readiness_hash,
        component_hash=component_hash,
        evaluator_schema_hash=component["assets"]["evaluator_item_schema"]["sha256"],
    )
    validate_execution_freeze(
        execution,
        study_freeze=study,
        study_freeze_bytes=study_bytes,
        readiness_bytes=readiness_bytes,
        packet_seal_bytes=packet_seal_bytes,
        packet_seal_metadata=seal_metadata,
    )
    return {
        "execution_freeze": execution,
        "execution_freeze_sha256": sha256_bytes(execution_bytes),
        "study_freeze": study,
        "study_freeze_sha256": sha256_bytes(study_bytes),
        "readiness_report_sha256": readiness_hash,
        "packet_seal": packet_seal,
        "packet_seal_sha256": sha256_bytes(packet_seal_bytes),
        "packet_seal_metadata": seal_metadata,
        "component": component,
        "component_assets": assets,
        "component_hash": component_hash,
        "frozen_at": study_metadata["frozen_at"],
    }


def item_id_set_sha256(item_ids: Iterable[str]) -> str:
    ordered = sorted(item_ids)
    require(bool(ordered), "packet_bank_item_set_empty")
    require(len(ordered) == len(set(ordered)), "packet_bank_item_id_duplicate")
    return sha256_bytes(canonical_bytes(ordered))


def open_and_validate_packet_bank(
    path: Path,
    *,
    metadata: dict[str, Any],
    workspace: Path = WORKSPACE,
) -> list[dict[str, Any]]:
    """This is the first function allowed to check or open source-bearing data."""

    workspace = workspace.resolve()
    require_absolute_regular_file(
        path,
        allowed_root=workspace / "Storage",
        code_prefix="packet_bank",
    )
    bank_bytes = read_regular_bytes(path, code_prefix="packet_bank")
    expected_hash = metadata["packet_seal_metadata"]["packet_bank_sha256"]
    require(sha256_bytes(bank_bytes) == expected_hash, "packet_bank_hash_drift")
    bank = load_json_bytes(bank_bytes, code_prefix="packet_bank")
    exact_keys(bank, PACKET_BANK_KEYS, "packet_bank")
    require(
        bank["document_type"] == "warrantroute_qwen3_generalist_evaluator_item_bank",
        "packet_bank_document_type_invalid",
    )
    require(
        bank["schema_version"] == "qwen3-generalist-evaluator-item-bank-v1",
        "packet_bank_version_invalid",
    )
    require(bank["study_id"] == metadata["packet_seal"]["study_id"], "packet_bank_study_id_drift")
    require(bank["corpus_id"] == EXPECTED_CORPUS_ID, "packet_bank_corpus_drift")
    require(bank["official_source_split"] == EXPECTED_SPLIT, "packet_bank_split_drift")
    require(bank["evaluation_role"] == EXPECTED_EVALUATION_ROLE, "packet_bank_role_drift")
    require(
        bank["privacy_clearance_status"] == "cleared_for_bound_model_and_rater_display",
        "packet_bank_privacy_status_invalid",
    )
    items = bank["items"]
    require(isinstance(items, list), "packet_bank_items_invalid")
    require(
        len(items) == metadata["packet_seal_metadata"]["item_count"],
        "packet_bank_item_count_drift",
    )
    item_ids: list[str] = []
    packet_ids: set[str] = set()
    output_ids: set[str] = set()
    for index, item in enumerate(items):
        require(isinstance(item, dict), f"packet_item_not_object:{index}")
        try:
            reviewer.validate_evaluator_item(
                item,
                metadata["component_assets"]["evaluator_item_schema"],
            )
        except reviewer.GeneralistReviewerError as exc:
            raise FormalRunnerError(f"packet_item_invalid:{index}:{exc}") from exc
        require(item["corpus_id"] == EXPECTED_CORPUS_ID, f"packet_item_corpus_drift:{index}")
        require(item["packet_id"] not in packet_ids, "packet_id_duplicate")
        require(item["output_id"] not in output_ids, "output_id_duplicate")
        item_ids.append(item["item_id"])
        packet_ids.add(item["packet_id"])
        output_ids.add(item["output_id"])
    require(
        item_id_set_sha256(item_ids) == metadata["packet_seal_metadata"]["item_id_set_sha256"],
        "packet_bank_item_set_drift",
    )
    return sorted(items, key=lambda value: value["item_id"])


def prepare_frozen_requests(
    items: list[dict[str, Any]],
    *,
    metadata: dict[str, Any],
) -> dict[tuple[str, int], bytes]:
    """Build each frozen item-repetition request exactly once."""

    requests: dict[tuple[str, int], bytes] = {}
    for item in items:
        for repetition in range(1, EXPECTED_RATING_REPETITIONS + 1):
            try:
                payload = reviewer.build_rating_request(
                    metadata["component"],
                    metadata["component_assets"],
                    item,
                    repetition=repetition,
                )
            except (reviewer.GeneralistReviewerError, reviewer.PromptLimitError) as exc:
                raise FormalRunnerError(f"frozen_packet_request_invalid:{exc}") from exc
            key = (item["item_id"], repetition)
            require(key not in requests, "frozen_request_key_duplicate")
            requests[key] = canonical_bytes(payload)
    return requests


def _post_frozen_request(
    item_id: str,
    *,
    repetition: int,
    request_bytes: bytes,
    metadata: dict[str, Any],
    capability: object,
) -> tuple[bytes, int]:
    """POST exact prebuilt bytes only when their frozen hash is authorized."""

    require(capability is _NETWORK_CAPABILITY, "formal_network_capability_missing")
    request_key = f"{item_id}:{repetition}"
    authorized_requests = metadata.get("authorized_request_sha256s")
    require(
        isinstance(authorized_requests, dict)
        and authorized_requests.get(request_key) == sha256_bytes(request_bytes),
        "network_request_not_frozen",
    )
    require(1 <= repetition <= EXPECTED_RATING_REPETITIONS, "network_repetition_invalid")
    config = metadata["component"]
    url = reviewer._service_url(config, "/api/chat")
    request = urllib.request.Request(
        url,
        data=request_bytes,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with reviewer.LOCAL_ONLY_OPENER.open(request, timeout=120) as response:
            require(response.geturl() == url, "service_redirect_rejected")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(response.getcode())
    except urllib.error.HTTPError as exc:
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        status = int(exc.code)
    require(len(body) <= MAX_RESPONSE_BYTES, "service_response_too_large")
    return body, status


def source_free_rating_projection(rating: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(rating)
    projected["rationale"] = "Rationale withheld from the source-free scoring bundle."
    return projected


def execute_repetition(
    item: dict[str, Any],
    *,
    repetition: int,
    request_bytes: bytes,
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    component = metadata["component"]
    assets = metadata["component_assets"]
    require(1 <= repetition <= EXPECTED_RATING_REPETITIONS, "rating_repetition_invalid")
    response_bytes: bytes | None = None
    http_status: int | None = None
    original_rating: dict[str, Any] | None = None
    projected_rating: dict[str, Any] | None = None
    status = "other_terminal_failure"

    try:
        response_bytes, http_status = _post_frozen_request(
            item["item_id"],
            repetition=repetition,
            request_bytes=request_bytes,
            metadata=metadata,
            capability=_NETWORK_CAPABILITY,
        )
    except (TimeoutError,):
        status = "timeout"
    except (urllib.error.URLError, OSError):
        status = "service_failure"
    except FormalRunnerError as exc:
        status = "other_terminal_failure"
        if str(exc) == "service_response_too_large":
            response_bytes = None
    else:
        if http_status != 200:
            try:
                error_value = json.loads(response_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_value = None
            status = (
                "context_overflow"
                if http_status == 400
                and error_value == {"error": "the input length exceeds the context length"}
                else "service_failure"
            )
        else:
            try:
                response = json.loads(response_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                status = "invalid_json"
            else:
                if not isinstance(response, dict):
                    status = "invalid_json"
                elif response.get("model") != EXPECTED_MODEL_ID:
                    status = "model_identity_failure"
                elif response.get("done") is not True:
                    status = "other_terminal_failure"
                elif response.get("done_reason") != "stop":
                    status = (
                        "truncated"
                        if response.get("done_reason") == "length"
                        else "other_terminal_failure"
                    )
                else:
                    content = response.get("message", {}).get("content")
                    try:
                        candidate = json.loads(content) if isinstance(content, str) else None
                    except json.JSONDecodeError:
                        candidate = None
                    if candidate is None:
                        status = "invalid_json"
                    elif not isinstance(candidate, dict):
                        status = "schema_failure"
                    else:
                        try:
                            jsonschema.Draft202012Validator(
                                assets["shared_rating_schema"]
                            ).validate(candidate)
                        except jsonschema.ValidationError:
                            status = "schema_failure"
                        else:
                            try:
                                parsed, _ = reviewer.parse_rating_response(
                                    response,
                                    expected_model=EXPECTED_MODEL_ID,
                                    rating_schema=assets["shared_rating_schema"],
                                    config=component,
                                )
                            except reviewer.ResponseValidationError:
                                status = "context_overflow"
                            else:
                                original_rating = parsed
                                projected_rating = source_free_rating_projection(parsed)
                                status = "valid_rating"

    raw_record = {
        "record_version": "qwen3-generalist-raw-execution-record-v1",
        "item_id": item["item_id"],
        "rating_repetition": repetition,
        "seed": component["repetition_seeds"][repetition - 1],
        "terminal_status": status,
        "http_status": http_status,
        "request_body_base64": base64.b64encode(request_bytes).decode("ascii"),
        "response_body_base64": (
            None
            if response_bytes is None
            else base64.b64encode(response_bytes).decode("ascii")
        ),
        "original_rating": original_rating,
    }
    observation: dict[str, Any] | None = None
    if repetition == EXPECTED_PRIMARY_REPETITION:
        observation = {
            "item_id": item["item_id"],
            "rating_repetition": repetition,
            "terminal_status": status,
            "rating": projected_rating,
            "private_execution_record_sha256": sha256_bytes(canonical_bytes(raw_record)),
        }
    return raw_record, observation


def require_output_path(path: Path, *, workspace: Path, label: str) -> None:
    storage = workspace / "Storage"
    require(path.is_absolute(), f"{label}_path_not_absolute")
    require(path.resolve(strict=False) == path, f"{label}_path_resolution_drift")
    require(is_within(path, storage), f"{label}_outside_storage")
    require(not path.exists(), f"{label}_already_exists")
    require(not path.is_symlink(), f"{label}_path_is_symlink")
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"{label}_parent_invalid")
    require(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, f"{label}_parent_mode_invalid")


def write_exclusive(path: Path, payload: bytes, *, label: str) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise FormalRunnerError(f"{label}_create_failed") from exc
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, f"{label}_mode_invalid")


def write_output_set(outputs: list[tuple[Path, dict[str, Any], str]]) -> None:
    created: list[Path] = []
    try:
        for path, value, label in outputs:
            write_exclusive(path, canonical_bytes(value), label=label)
            created.append(path)
    except Exception:
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        raise


def run_formal(
    *,
    execution_freeze_path: Path,
    study_freeze_path: Path,
    readiness_report_path: Path,
    packet_bank_seal_path: Path,
    packet_bank_path: Path,
    observation_bundle_path: Path,
    observation_seal_path: Path,
    raw_execution_bundle_path: Path,
    raw_execution_seal_path: Path,
    sealed_at_utc: str,
    workspace: Path = WORKSPACE,
) -> dict[str, Any]:
    workspace = workspace.resolve()

    # This call is deliberately first.  It must finish before the packet-bank
    # path is inspected or any Ollama endpoint is contacted.
    metadata = validate_metadata(
        execution_freeze_path=execution_freeze_path,
        study_freeze_path=study_freeze_path,
        readiness_report_path=readiness_report_path,
        packet_bank_seal_path=packet_bank_seal_path,
        workspace=workspace,
    )

    require_output_path(observation_bundle_path, workspace=workspace, label="observation_bundle")
    require_output_path(observation_seal_path, workspace=workspace, label="observation_seal")
    require_output_path(raw_execution_bundle_path, workspace=workspace, label="raw_execution_bundle")
    require_output_path(raw_execution_seal_path, workspace=workspace, label="raw_execution_seal")
    output_paths = {
        observation_bundle_path,
        observation_seal_path,
        raw_execution_bundle_path,
        raw_execution_seal_path,
    }
    require(len(output_paths) == 4, "formal_output_paths_collide")
    require(
        len({path.parent for path in output_paths}) == 1,
        "formal_output_parents_differ",
    )
    sealed_at = parse_utc(sealed_at_utc, "sealed_at")
    require(sealed_at >= metadata["frozen_at"], "sealed_before_study_freeze")
    retention_until = parse_utc(
        metadata["execution_freeze"]["raw_retention_deletion_scope"]["retention_until_utc"],
        "raw_retention_until",
    )
    require(sealed_at < retention_until, "run_outside_approved_raw_retention_window")

    items = open_and_validate_packet_bank(
        packet_bank_path,
        metadata=metadata,
        workspace=workspace,
    )
    metadata = dict(metadata)
    frozen_requests = prepare_frozen_requests(items, metadata=metadata)
    metadata["authorized_request_sha256s"] = {
        f"{item_id}:{repetition}": sha256_bytes(request_bytes)
        for (item_id, repetition), request_bytes in frozen_requests.items()
    }

    try:
        baseline = reviewer.preflight_service(metadata["component"])
    except reviewer.GeneralistReviewerError as exc:
        raise FormalRunnerError(f"model_service_preflight_failed:{exc}") from exc
    require(baseline["model_id"] == EXPECTED_MODEL_ID, "preflight_model_drift")
    require(baseline["model_digest"] == reviewer.EXPECTED_MODEL_DIGEST, "preflight_digest_drift")

    raw_records: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for item in items:
        for repetition in range(1, EXPECTED_RATING_REPETITIONS + 1):
            raw_record, observation = execute_repetition(
                item,
                repetition=repetition,
                request_bytes=frozen_requests[(item["item_id"], repetition)],
                metadata=metadata,
            )
            raw_records.append(raw_record)
            if observation is not None:
                records.append(observation)

    try:
        final_identity = reviewer.preflight_service(metadata["component"])
    except reviewer.GeneralistReviewerError as exc:
        raise FormalRunnerError(f"model_service_final_check_failed:{exc}") from exc
    require(final_identity == baseline, "model_service_identity_changed")
    require(len(records) == len(items), "terminal_record_count_drift")
    require(len({row["item_id"] for row in records}) == len(items), "terminal_item_id_duplicate")
    require(
        len(raw_records) == len(items) * EXPECTED_RATING_REPETITIONS,
        "raw_execution_record_count_drift",
    )
    require(
        len({(row["item_id"], row["rating_repetition"]) for row in raw_records})
        == len(raw_records),
        "raw_execution_record_duplicate",
    )

    raw_bundle = {
        "document_type": "warrantroute_qwen3_generalist_raw_execution_bundle_v1",
        "study_freeze_sha256": metadata["study_freeze_sha256"],
        "execution_freeze_sha256": metadata["execution_freeze_sha256"],
        "packet_bank_seal_sha256": metadata["packet_seal_sha256"],
        "corpus_id": EXPECTED_CORPUS_ID,
        "split": EXPECTED_SPLIT,
        "method": EXPECTED_METHOD,
        "reviewer_actor_id": EXPECTED_REVIEWER_ACTOR,
        "model_id": EXPECTED_MODEL_ID,
        "model_digest": reviewer.EXPECTED_MODEL_DIGEST,
        "rating_repetitions": EXPECTED_RATING_REPETITIONS,
        "primary_repetition": EXPECTED_PRIMARY_REPETITION,
        "contains_source_text": True,
        "storage_class": "restricted_mode_0600_storage",
        "records": raw_records,
    }
    raw_bundle_bytes = canonical_bytes(raw_bundle)
    raw_bundle_hash = sha256_bytes(raw_bundle_bytes)
    raw_seal = {
        "document_type": "warrantroute_qwen3_generalist_raw_execution_seal_v1",
        "seal_id": f"QGRES_{raw_bundle_hash[:16].upper()}",
        "status": "complete",
        "sealed_at_utc": sealed_at_utc,
        "study_freeze_sha256": metadata["study_freeze_sha256"],
        "execution_freeze_sha256": metadata["execution_freeze_sha256"],
        "packet_bank_seal_sha256": metadata["packet_seal_sha256"],
        "raw_execution_bundle_sha256": raw_bundle_hash,
        "runner_sha256": metadata["execution_freeze"]["runner_sha256"],
        "runner_contract_sha256": metadata["execution_freeze"]["runner_contract_sha256"],
        "raw_retention_deletion_scope_sha256": sha256_bytes(
            canonical_bytes(metadata["execution_freeze"]["raw_retention_deletion_scope"])
        ),
        "item_count": len(items),
        "rating_repetitions": EXPECTED_RATING_REPETITIONS,
        "record_count": len(raw_records),
        "all_frozen_item_repetitions_terminal": True,
        "contains_source_text": False,
        "sealed_bundle_contains_source_text": True,
        "restricted_storage": True,
    }
    raw_seal_hash = sha256_bytes(canonical_bytes(raw_seal))

    primary_raw_hash_map = {
        row["item_id"]: sha256_bytes(canonical_bytes(row))
        for row in raw_records
        if row["rating_repetition"] == EXPECTED_PRIMARY_REPETITION
    }
    require(len(primary_raw_hash_map) == len(items), "primary_raw_hash_map_incomplete")
    primary_raw_hash_map_sha256 = sha256_bytes(canonical_bytes(primary_raw_hash_map))
    primary_raw_hash_set_sha256 = sha256_bytes(
        canonical_bytes(sorted(primary_raw_hash_map.values()))
    )
    require(
        all(
            row["private_execution_record_sha256"] == primary_raw_hash_map[row["item_id"]]
            for row in records
        ),
        "observation_primary_raw_hash_drift",
    )

    bundle = {
        "document_type": "warrantroute_qwen3_generalist_observation_bundle_v1",
        "study_freeze_sha256": metadata["study_freeze_sha256"],
        "corpus_id": EXPECTED_CORPUS_ID,
        "split": EXPECTED_SPLIT,
        "method": EXPECTED_METHOD,
        "reviewer_actor_id": EXPECTED_REVIEWER_ACTOR,
        "model_id": EXPECTED_MODEL_ID,
        "model_digest": reviewer.EXPECTED_MODEL_DIGEST,
        "primary_repetition": EXPECTED_PRIMARY_REPETITION,
        "records": records,
    }
    bundle_bytes = canonical_bytes(bundle)
    bundle_hash = sha256_bytes(bundle_bytes)
    seal = {
        "document_type": "warrantroute_qwen3_generalist_observation_seal_v2",
        "seal_version": "qwen3-generalist-observation-seal-v2",
        "seal_id": f"QGOS_{bundle_hash[:16].upper()}",
        "status": "complete",
        "sealed_at_utc": sealed_at_utc,
        "study_freeze_sha256": metadata["study_freeze_sha256"],
        "execution_freeze_sha256": metadata["execution_freeze_sha256"],
        "packet_bank_seal_sha256": metadata["packet_seal_sha256"],
        "raw_execution_bundle_sha256": raw_bundle_hash,
        "raw_execution_seal_sha256": raw_seal_hash,
        "runner_sha256": metadata["execution_freeze"]["runner_sha256"],
        "runner_contract_sha256": metadata["execution_freeze"]["runner_contract_sha256"],
        "primary_raw_record_hash_map_sha256": primary_raw_hash_map_sha256,
        "primary_raw_record_hash_set_sha256": primary_raw_hash_set_sha256,
        "observation_bundle_sha256": bundle_hash,
        "record_count": len(records),
        "all_frozen_items_terminal": True,
        "source_text_included": False,
    }
    write_output_set(
        [
            (raw_execution_bundle_path, raw_bundle, "raw_execution_bundle"),
            (raw_execution_seal_path, raw_seal, "raw_execution_seal"),
            (observation_bundle_path, bundle, "observation_bundle"),
            (observation_seal_path, seal, "observation_seal"),
        ]
    )
    return {
        "status": "complete",
        "record_count": len(records),
        "valid_rating_count": sum(row["terminal_status"] == "valid_rating" for row in records),
        "raw_execution_record_count": len(raw_records),
        "raw_execution_bundle_sha256": raw_bundle_hash,
        "raw_execution_seal_sha256": raw_seal_hash,
        "primary_raw_record_hash_map_sha256": primary_raw_hash_map_sha256,
        "primary_raw_record_hash_set_sha256": primary_raw_hash_set_sha256,
        "observation_bundle_sha256": bundle_hash,
        "observation_seal_sha256": sha256_bytes(canonical_bytes(seal)),
        "source_text_in_scoring_outputs": False,
        "raw_execution_outputs_restricted": True,
        "manuscript_value_created": False,
    }


def source_free_dry_run(
    *,
    readiness_report_path: Path = DEFAULT_READINESS,
    workspace: Path = WORKSPACE,
) -> dict[str, Any]:
    """Report current gate state without source access, output, or network."""

    workspace = workspace.resolve()
    readiness, _ = read_private_metadata(
        readiness_report_path,
        workspace=workspace,
        storage=False,
        code_prefix="readiness",
    )
    require(
        readiness.get("document_type") == "warrantroute_readiness_report",
        "readiness_document_type_invalid",
    )
    require(readiness.get("contains_real_source_text") is False, "readiness_contains_source_text")
    dreaddit = readiness.get("corpora", {}).get(EXPECTED_CORPUS_ID)
    require(isinstance(dreaddit, dict), "dreaddit_readiness_missing")
    completed = dreaddit.get("completed_gate_count")
    required = dreaddit.get("required_gate_count")
    formal_ready = bool(
        readiness.get("gate_mode") == "real_text_candidate"
        and completed == required == 10
        and dreaddit.get("real_text_ready") is True
    )
    return {
        "status": "source_free_check_complete",
        "gate_mode": readiness.get("gate_mode"),
        "dreaddit_completed_gate_count": completed,
        "dreaddit_required_gate_count": required,
        "formal_execution_ready": formal_ready,
        "packet_bank_accessed": False,
        "model_service_contacted": False,
        "outputs_written": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    dry = commands.add_parser("dry-run", help="Report current source-free readiness only.")
    dry.add_argument("--readiness-report", type=Path, default=DEFAULT_READINESS)
    run = commands.add_parser("run", help="Run the authorized frozen Dreaddit packet bank once.")
    run.add_argument("--execution-freeze", type=Path, required=True)
    run.add_argument("--study-freeze", type=Path, required=True)
    run.add_argument("--readiness-report", type=Path, required=True)
    run.add_argument("--packet-bank-seal", type=Path, required=True)
    run.add_argument("--packet-bank", type=Path, required=True)
    run.add_argument("--observation-bundle", type=Path, required=True)
    run.add_argument("--observation-seal", type=Path, required=True)
    run.add_argument("--raw-execution-bundle", type=Path, required=True)
    run.add_argument("--raw-execution-seal", type=Path, required=True)
    run.add_argument("--sealed-at-utc", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "dry-run":
            result = source_free_dry_run(readiness_report_path=args.readiness_report)
        else:
            result = run_formal(
                execution_freeze_path=args.execution_freeze,
                study_freeze_path=args.study_freeze,
                readiness_report_path=args.readiness_report,
                packet_bank_seal_path=args.packet_bank_seal,
                packet_bank_path=args.packet_bank,
                observation_bundle_path=args.observation_bundle,
                observation_seal_path=args.observation_seal,
                raw_execution_bundle_path=args.raw_execution_bundle,
                raw_execution_seal_path=args.raw_execution_seal,
                sealed_at_utc=args.sealed_at_utc,
            )
    except FormalRunnerError as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error_code": str(exc),
                    "manuscript_value_created": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
