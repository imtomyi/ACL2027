#!/usr/bin/env python3
"""Fail-closed sealer for an authorized Dreaddit Qwen3 packet bank.

The sealer does not construct packets, grant authorization, call a model, or
score results.  It reads a source-bearing evaluator-item bank only after a
formal text-free readiness report, a text-free study freeze, and a text-free
privacy log satisfy the frozen metadata checks.  Its sole output is a
content-free integrity seal under ``Storage/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment preflight
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]

STUDY_FREEZE_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_packet_study_freeze_v1.schema.json"
)
TRUTH_MAP_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_truth_cluster_map_v1.schema.json"
)
PACKET_MANIFEST_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_packet_manifest_v1.schema.json"
)
PREACCESS_RECORD_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_preaccess_record_v1.schema.json"
)
VERIFICATION_BUNDLE_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_verification_bundle_v1.schema.json"
)
VERIFICATION_SEAL_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_verification_seal_v1.schema.json"
)
EVALUATOR_ITEM_SCHEMA = (
    WORKSPACE
    / "experiments"
    / "direction_j_llm_as_rater"
    / "schemas"
    / "evaluator_item.schema.json"
)
GENERALIST_COMPONENT_FREEZE = (
    RQ2_ROOT / "config" / "qwen3_generalist_reviewer_freeze.json"
)

EXPECTED_GATE_IDS = (
    "institutional_determination",
    "source_platform_authorization",
    "provider_model_processing",
    "exact_corpus_input_contract",
    "two_person_excerpt_privacy_review",
    "cluster_aware_sampling",
    "frozen_study_manifest",
    "rater_and_service_access_controls",
    "retention_deletion_controls",
    "release_controls",
)
EXPECTED_FAMILY_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}
EXPECTED_REVIEWER = {
    "actor_id": "qwen3_8b_generalist_reviewer_v1",
    "task_role": "reviewer",
    "prompted_role": "generalist",
    "model_id": "qwen3:8b",
}
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
PRIVACY_LOG_KEYS = {
    "document_type",
    "log_version",
    "record_status",
    "contains_source_text",
    "minimum_distinct_reviewers_per_excerpt",
    "records",
    "template_notice",
}
PRIVACY_RECORD_KEYS = {
    "corpus_id",
    "packet_id",
    "excerpt_id",
    "context_sha256",
    "reviewer_ids",
    "reviewed_at_utc",
    "decision",
    "model_processing_cleared",
    "rater_display_cleared",
    "quotation_cleared",
}
FORBIDDEN_ITEM_KEYS = {
    "adjudication",
    "answer_key",
    "base_packet_id",
    "cluster_id",
    "construction_note",
    "error_family",
    "generator_actor_id",
    "required_flag",
    "route",
    "target_flaw",
    "truth",
    "verifier_output",
}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
REVIEWER_ID_RE = re.compile(r"^REV_[A-Z0-9]{8,32}$")
REVIEWER_REGISTRY_KEYS = {
    "document_type",
    "registry_version",
    "record_status",
    "contains_direct_identifiers",
    "reviewer_id_format",
    "identity_crosswalk_reference",
    "reviewers",
    "template_notice",
}
REVIEWER_KEYS = {
    "reviewer_id",
    "status",
    "roles",
    "approved_corpora",
    "privacy_training_version",
    "confidentiality_acknowledgment_version",
    "approved_at_utc",
    "expires_at_utc",
    "last_verified_at_utc",
}


class PacketSealError(RuntimeError):
    """Finite content-free failure suitable for a terminal report."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PacketSealError(code)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file_bytes(value: bytes) -> str:
    return sha256_bytes(value)


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
    required_mode: int | None,
    code_prefix: str,
) -> None:
    require(path.is_absolute(), f"{code_prefix}_path_not_absolute")
    require(path.resolve(strict=False) == path, f"{code_prefix}_path_resolution_drift")
    require(is_within(path, allowed_root), f"{code_prefix}_path_outside_allowed_root")
    require(not path.is_symlink(), f"{code_prefix}_path_is_symlink")
    require(path.is_file(), f"{code_prefix}_file_missing")
    if required_mode is not None:
        require(
            stat.S_IMODE(path.stat().st_mode) == required_mode,
            f"{code_prefix}_file_mode_invalid",
        )


def read_regular_bytes(path: Path, *, code_prefix: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PacketSealError(f"{code_prefix}_file_unavailable") from exc
    try:
        require(
            stat.S_ISREG(os.fstat(descriptor).st_mode),
            f"{code_prefix}_not_regular_file",
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


def load_json_bytes(value: bytes, *, code_prefix: str) -> dict[str, Any]:
    try:
        result = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PacketSealError(f"{code_prefix}_invalid_json") from exc
    require(isinstance(result, dict), f"{code_prefix}_root_not_object")
    return result


def load_public_json(
    path: Path, *, allowed_root: Path = WORKSPACE, code_prefix: str
) -> tuple[dict[str, Any], bytes]:
    require_absolute_regular_file(
        path,
        allowed_root=allowed_root,
        required_mode=None,
        code_prefix=code_prefix,
    )
    data = read_regular_bytes(path, code_prefix=code_prefix)
    return load_json_bytes(data, code_prefix=code_prefix), data


def validate_against_schema(
    value: dict[str, Any], schema: dict[str, Any], *, code: str
) -> None:
    try:
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(value)
    except jsonschema.ValidationError as exc:
        raise PacketSealError(code) from exc


def parse_utc(value: Any, *, code: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), code)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PacketSealError(code) from exc
    require(parsed.tzinfo is not None, code)
    return parsed.astimezone(timezone.utc)


def validate_formal_readiness(report: dict[str, Any]) -> dict[str, Any]:
    require(
        report.get("document_type") == "warrantroute_readiness_report",
        "readiness_document_type_invalid",
    )
    require(
        report.get("report_version") == "warrantroute-readiness-report-v1",
        "readiness_version_invalid",
    )
    require(report.get("record_status") == "local_evidence_record", "readiness_record_invalid")
    require(report.get("gate_mode") == "real_text_candidate", "formal_gate_mode_invalid")
    require(report.get("exact_required_gate_count") == 10, "formal_gate_count_invalid")
    require(report.get("contains_real_source_text") is False, "readiness_contains_source_text")
    require("personal_local_only" not in report, "personal_local_readiness_forbidden")
    source_record_sha256 = report.get("source_record_sha256")
    require(
        isinstance(source_record_sha256, str) and SHA256_RE.fullmatch(source_record_sha256),
        "governance_source_record_sha256_invalid",
    )

    corpora = report.get("corpora")
    require(isinstance(corpora, dict), "readiness_corpora_invalid")
    dreaddit = corpora.get("dreaddit")
    require(isinstance(dreaddit, dict), "dreaddit_readiness_missing")
    require(dreaddit.get("external_gates_applicable") is True, "formal_gates_not_applicable")
    require(dreaddit.get("required_gate_count") == 10, "dreaddit_required_gate_count_invalid")
    require(dreaddit.get("completed_gate_count") == 10, "dreaddit_completed_gate_count_invalid")
    require(dreaddit.get("real_text_ready") is True, "dreaddit_not_real_text_ready")
    gates = dreaddit.get("gates")
    require(isinstance(gates, list) and len(gates) == 10, "dreaddit_gate_records_invalid")
    require(
        tuple(gate.get("id") for gate in gates if isinstance(gate, dict))
        == EXPECTED_GATE_IDS,
        "dreaddit_gate_ids_invalid",
    )
    for gate in gates:
        require(isinstance(gate, dict), "dreaddit_gate_record_invalid")
        require(gate.get("complete") is True, "dreaddit_gate_incomplete")
        require(gate.get("blocking_reason_codes") == [], "dreaddit_gate_has_blockers")
    warnings = report.get("warning_codes", [])
    require(isinstance(warnings, list), "readiness_warning_codes_invalid")
    forbidden_warnings = {
        "private_personal_exploratory_only",
        "not_institutional_or_external_approval",
        "not_for_publication_submission_or_redistribution",
        "formal_real_text_ready_remains_false",
    }
    require(not forbidden_warnings.intersection(warnings), "readiness_has_ineligible_warning")
    return dreaddit


def validate_governance_record(
    record: dict[str, Any],
    *,
    source_receipt_sha256: str,
    packet_manifest_sha256: str,
    readiness_assessed_at: datetime,
    study_frozen_at: datetime,
) -> None:
    require(
        record.get("document_type") == "warrantroute_project_governance_record",
        "governance_record_type_invalid",
    )
    require(
        record.get("governance_version") == "warrantroute-project-governance-v1",
        "governance_record_version_invalid",
    )
    require(record.get("record_status") == "local_evidence_record", "governance_record_status_invalid")
    require(record.get("gate_mode") == "real_text_candidate", "governance_record_not_formal")
    governance_assessed_at = parse_utc(
        record.get("assessment_as_of_utc"), code="governance_assessment_time_invalid"
    )
    require(
        governance_assessed_at <= readiness_assessed_at <= study_frozen_at,
        "governance_readiness_freeze_timeline_invalid",
    )
    lanes = record.get("corpus_lanes")
    require(isinstance(lanes, dict), "governance_corpus_lanes_invalid")
    dreaddit = lanes.get("dreaddit")
    require(isinstance(dreaddit, dict), "governance_dreaddit_lane_missing")
    require(dreaddit.get("corpus_id") == "dreaddit", "governance_dreaddit_corpus_invalid")
    require(dreaddit.get("real_text_runnable") is True, "governance_dreaddit_not_runnable")
    require(dreaddit.get("required_cluster_units") == ["post"], "governance_cluster_unit_invalid")
    gates = dreaddit.get("gates")
    require(isinstance(gates, list) and len(gates) == 10, "governance_gate_records_invalid")
    require(
        tuple(gate.get("id") for gate in gates if isinstance(gate, dict))
        == EXPECTED_GATE_IDS,
        "governance_gate_ids_invalid",
    )
    by_id: dict[str, dict[str, Any]] = {}
    for gate in gates:
        require(isinstance(gate, dict), "governance_gate_record_invalid")
        require(gate.get("status") == "approved", "governance_gate_not_approved")
        require(isinstance(gate.get("evidence_reference"), str) and gate["evidence_reference"], "governance_gate_evidence_missing")
        require(isinstance(gate.get("authority_id"), str) and gate["authority_id"], "governance_gate_authority_missing")
        approved_at = parse_utc(
            gate.get("approved_at_utc"), code="governance_gate_approved_at_invalid"
        )
        expires_at = parse_utc(
            gate.get("expires_at_utc"), code="governance_gate_expires_at_invalid"
        )
        verified_at = parse_utc(
            gate.get("last_verified_at_utc"), code="governance_gate_verified_at_invalid"
        )
        require(
            approved_at <= verified_at <= governance_assessed_at <= study_frozen_at < expires_at,
            "governance_gate_not_current_for_freeze",
        )
        by_id[gate["id"]] = gate
    input_details = by_id["exact_corpus_input_contract"].get("details")
    require(isinstance(input_details, dict), "governance_input_contract_details_invalid")
    require(
        input_details.get("source_receipt_sha256") == source_receipt_sha256,
        "governance_source_receipt_hash_mismatch",
    )
    privacy_details = by_id["two_person_excerpt_privacy_review"].get("details")
    require(isinstance(privacy_details, dict), "governance_privacy_gate_details_invalid")
    require(
        privacy_details.get("packet_manifest_sha256") == packet_manifest_sha256,
        "governance_packet_manifest_hash_mismatch",
    )


def validate_reviewer_registry(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(set(registry) == REVIEWER_REGISTRY_KEYS, "reviewer_registry_shape_invalid")
    require(
        registry.get("document_type") == "warrantroute_reviewer_registry",
        "reviewer_registry_type_invalid",
    )
    require(
        registry.get("registry_version") == "warrantroute-reviewer-registry-v1",
        "reviewer_registry_version_invalid",
    )
    require(registry.get("record_status") == "local_evidence_record", "reviewer_registry_status_invalid")
    require(registry.get("contains_direct_identifiers") is False, "reviewer_registry_has_identifiers")
    require(
        registry.get("reviewer_id_format") == "REV_[A-Z0-9]{8,32}",
        "reviewer_registry_id_format_invalid",
    )
    require(
        isinstance(registry.get("identity_crosswalk_reference"), str)
        and registry["identity_crosswalk_reference"],
        "reviewer_identity_crosswalk_missing",
    )
    rows = registry.get("reviewers")
    require(isinstance(rows, list) and rows, "reviewer_registry_empty")
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == REVIEWER_KEYS, "reviewer_record_shape_invalid")
        reviewer_id = row.get("reviewer_id")
        require(
            isinstance(reviewer_id, str) and REVIEWER_ID_RE.fullmatch(reviewer_id),
            "reviewer_id_invalid",
        )
        require(reviewer_id not in by_id, "duplicate_reviewer_id")
        require(row.get("status") == "active", "reviewer_not_active")
        require(
            isinstance(row.get("roles"), list) and row["roles"],
            "reviewer_roles_invalid",
        )
        require(
            isinstance(row.get("approved_corpora"), list) and "dreaddit" in row["approved_corpora"],
            "reviewer_not_approved_for_dreaddit",
        )
        for key in ("privacy_training_version", "confidentiality_acknowledgment_version"):
            require(isinstance(row.get(key), str) and row[key], f"reviewer_{key}_missing")
        approved = parse_utc(row.get("approved_at_utc"), code="reviewer_approved_at_invalid")
        expires = parse_utc(row.get("expires_at_utc"), code="reviewer_expires_at_invalid")
        verified = parse_utc(row.get("last_verified_at_utc"), code="reviewer_verified_at_invalid")
        require(approved <= verified < expires, "reviewer_approval_timeline_invalid")
        by_id[reviewer_id] = row
    return by_id


def validate_privacy_reviewer_scope(
    records: list[dict[str, Any]], reviewers: dict[str, dict[str, Any]]
) -> None:
    for row in records:
        if row.get("corpus_id") != "dreaddit":
            continue
        reviewed_at = parse_utc(row.get("reviewed_at_utc"), code="privacy_reviewed_at_invalid")
        for reviewer_id in row["reviewer_ids"]:
            reviewer = reviewers.get(reviewer_id)
            require(reviewer is not None, "privacy_reviewer_not_in_registry")
            require("privacy_reviewer" in reviewer["roles"], "privacy_reviewer_role_missing")
            approved = parse_utc(reviewer["approved_at_utc"], code="reviewer_approved_at_invalid")
            expires = parse_utc(reviewer["expires_at_utc"], code="reviewer_expires_at_invalid")
            verified = parse_utc(reviewer["last_verified_at_utc"], code="reviewer_verified_at_invalid")
            require(approved <= verified <= reviewed_at < expires, "privacy_reviewer_not_current_at_review")


def validate_privacy_log(log: dict[str, Any]) -> list[dict[str, Any]]:
    require(set(log) == PRIVACY_LOG_KEYS, "privacy_log_shape_invalid")
    require(
        log.get("document_type") == "warrantroute_privacy_review_log",
        "privacy_log_type_invalid",
    )
    require(
        log.get("log_version") == "warrantroute-privacy-review-log-v1",
        "privacy_log_version_invalid",
    )
    require(log.get("record_status") == "local_evidence_record", "privacy_log_status_invalid")
    require(log.get("contains_source_text") is False, "privacy_log_contains_source_text")
    require(
        log.get("minimum_distinct_reviewers_per_excerpt") == 2,
        "privacy_log_reviewer_minimum_invalid",
    )
    records = log.get("records")
    require(isinstance(records, list), "privacy_records_invalid")
    for row in records:
        require(isinstance(row, dict) and set(row) == PRIVACY_RECORD_KEYS, "privacy_record_shape_invalid")
        require(
            isinstance(row.get("context_sha256"), str)
            and SHA256_RE.fullmatch(row["context_sha256"]),
            "privacy_context_sha256_invalid",
        )
        reviewers = row.get("reviewer_ids")
        require(
            isinstance(reviewers, list)
            and len(reviewers) >= 2
            and len(reviewers) == len(set(reviewers))
            and all(isinstance(value, str) and REVIEWER_ID_RE.fullmatch(value) for value in reviewers),
            "privacy_reviewer_ids_invalid",
        )
    return records


def validate_source_receipt(receipt: dict[str, Any]) -> str:
    require(receipt.get("schema_version") == "1.0", "source_receipt_schema_version_invalid")
    require(receipt.get("corpus_id") == "dreaddit", "source_receipt_corpus_invalid")
    require(isinstance(receipt.get("version"), str) and receipt["version"], "source_receipt_version_missing")
    files = receipt.get("files")
    require(isinstance(files, list), "source_receipt_files_invalid")
    test_rows = [
        row
        for row in files
        if isinstance(row, dict)
        and row.get("name") == "dreaddit-test.csv"
        and row.get("official_split") == "test"
    ]
    require(len(test_rows) == 1, "source_receipt_test_binding_missing")
    test_sha256 = test_rows[0].get("sha256")
    require(
        isinstance(test_sha256, str) and SHA256_RE.fullmatch(test_sha256),
        "source_receipt_test_hash_invalid",
    )
    return test_sha256


def validate_packet_manifest(
    manifest: dict[str, Any],
    *,
    schema: dict[str, Any],
    freeze: dict[str, Any],
    source_receipt_sha256: str,
    source_test_file_sha256: str,
    privacy_log_sha256: str,
    packet_bank_sha256: str,
    truth_map_sha256: str,
) -> None:
    validate_against_schema(manifest, schema, code="packet_manifest_schema_invalid")
    require(manifest["study_id"] == freeze["study_id"], "packet_manifest_study_id_mismatch")
    require(
        manifest["reviewer_actor_id"] == freeze["actors"]["reviewer"]["actor_id"],
        "packet_manifest_reviewer_mismatch",
    )
    require(
        manifest["candidate_generator_actor_id"]
        == freeze["actors"]["candidate_generator"]["actor_id"],
        "packet_manifest_generator_mismatch",
    )
    require(manifest["source_receipt_sha256"] == source_receipt_sha256, "packet_manifest_source_receipt_mismatch")
    require(manifest["source_test_file_sha256"] == source_test_file_sha256, "packet_manifest_test_file_mismatch")
    require(manifest["privacy_review_log_sha256"] == privacy_log_sha256, "packet_manifest_privacy_log_mismatch")
    require(manifest["packet_bank_sha256"] == packet_bank_sha256, "packet_manifest_packet_bank_mismatch")
    require(manifest["truth_cluster_map_sha256"] == truth_map_sha256, "packet_manifest_truth_map_mismatch")
    require(manifest["item_count"] == freeze["design"]["fixed_n"], "packet_manifest_fixed_n_mismatch")
    approved_at = parse_utc(manifest["approved_at_utc"], code="packet_manifest_approved_at_invalid")
    frozen_at = parse_utc(freeze["frozen_at_utc"], code="study_freeze_frozen_at_invalid")
    require(approved_at <= frozen_at, "packet_manifest_approved_after_freeze")


def validate_preaccess_record(
    record: dict[str, Any],
    *,
    schema: dict[str, Any],
    freeze: dict[str, Any],
    source_receipt_sha256: str,
    packet_manifest_sha256: str,
    readiness_assessed_at: datetime,
    packet_manifest_approved_at: datetime,
) -> None:
    validate_against_schema(record, schema, code="preaccess_record_schema_invalid")
    require(record["study_id"] == freeze["study_id"], "preaccess_study_id_mismatch")
    require(record["source_receipt_sha256"] == source_receipt_sha256, "preaccess_source_receipt_mismatch")
    require(record["packet_manifest_sha256"] == packet_manifest_sha256, "preaccess_packet_manifest_mismatch")
    require(
        record["study_design_freeze_sha256"]
        == freeze["bindings"]["study_design_freeze_sha256"],
        "preaccess_study_design_freeze_mismatch",
    )
    design_frozen = parse_utc(record["design_frozen_at_utc"], code="preaccess_design_frozen_at_invalid")
    first_access = parse_utc(record["first_heldout_access_at_utc"], code="preaccess_first_access_invalid")
    construction_complete = parse_utc(
        record["packet_construction_completed_at_utc"],
        code="preaccess_construction_completed_invalid",
    )
    recorded_at = parse_utc(record["recorded_at_utc"], code="preaccess_recorded_at_invalid")
    study_frozen = parse_utc(freeze["frozen_at_utc"], code="study_freeze_frozen_at_invalid")
    require(
        design_frozen
        < first_access
        <= construction_complete
        <= packet_manifest_approved_at
        <= readiness_assessed_at
        <= recorded_at
        <= study_frozen,
        "preaccess_timeline_invalid",
    )


def validate_verification_metadata(
    bundle: dict[str, Any],
    seal: dict[str, Any],
    *,
    bundle_bytes: bytes,
    bundle_schema: dict[str, Any],
    seal_schema: dict[str, Any],
    freeze: dict[str, Any],
) -> None:
    """Validate text-free verification evidence before any packet-bank access."""

    validate_against_schema(bundle, bundle_schema, code="verification_bundle_schema_invalid")
    validate_against_schema(seal, seal_schema, code="verification_seal_schema_invalid")
    require(bundle["study_id"] == freeze["study_id"], "verification_bundle_study_id_mismatch")
    require(seal["study_id"] == freeze["study_id"], "verification_seal_study_id_mismatch")
    require(
        bundle["candidate_generator_actor_id"]
        == freeze["actors"]["candidate_generator"]["actor_id"],
        "verification_generator_mismatch",
    )
    require(
        bundle["reviewer_actor_id"] == freeze["actors"]["reviewer"]["actor_id"],
        "verification_reviewer_mismatch",
    )
    require(
        seal["verification_bundle_sha256"] == sha256_file_bytes(bundle_bytes),
        "verification_seal_bundle_hash_mismatch",
    )
    require(
        seal["item_count"] == freeze["design"]["fixed_n"],
        "verification_seal_fixed_n_mismatch",
    )
    require(
        parse_utc(seal["sealed_at_utc"], code="verification_sealed_at_invalid")
        <= parse_utc(freeze["frozen_at_utc"], code="study_freeze_frozen_at_invalid"),
        "verification_sealed_after_study_freeze",
    )


def validate_verification_bundle_and_seal(
    bundle: dict[str, Any],
    seal: dict[str, Any],
    *,
    bundle_bytes: bytes,
    bundle_schema: dict[str, Any],
    seal_schema: dict[str, Any],
    freeze: dict[str, Any],
    items_by_id: dict[str, dict[str, Any]],
    truth_rows_by_id: dict[str, dict[str, Any]],
) -> None:
    validate_verification_metadata(
        bundle,
        seal,
        bundle_bytes=bundle_bytes,
        bundle_schema=bundle_schema,
        seal_schema=seal_schema,
        freeze=freeze,
    )
    generator_id = freeze["actors"]["candidate_generator"]["actor_id"]
    reviewer_id = freeze["actors"]["reviewer"]["actor_id"]
    rows = bundle["items"]
    require(len(rows) == freeze["design"]["fixed_n"], "verification_bundle_fixed_n_mismatch")
    row_ids = [row["item_id"] for row in rows]
    require(len(row_ids) == len(set(row_ids)), "duplicate_verification_item_id")
    require(set(row_ids) == set(items_by_id), "verification_item_bijection_mismatch")
    require(seal["item_count"] == len(rows), "verification_seal_item_count_mismatch")
    require(
        seal["item_id_set_sha256"] == sha256_bytes(canonical_bytes(sorted(row_ids))),
        "verification_seal_item_set_mismatch",
    )
    minimum_verifiers = freeze["design"]["minimum_distinct_verifiers_per_item"]
    study_frozen = parse_utc(freeze["frozen_at_utc"], code="study_freeze_frozen_at_invalid")
    sealed_at = parse_utc(seal["sealed_at_utc"], code="verification_sealed_at_invalid")
    for row in rows:
        item = items_by_id[row["item_id"]]
        truth = truth_rows_by_id[row["item_id"]]
        item_hash = sha256_bytes(canonical_bytes(item))
        require(row["evaluator_item_sha256"] == item_hash, "verification_item_hash_mismatch")
        require(row["error_family"] == truth["error_family"], "verification_error_family_mismatch")
        require(row["required_flag"] == truth["required_flag"], "verification_required_flag_mismatch")
        require(
            truth["verification_record_sha256"] == sha256_bytes(canonical_bytes(row)),
            "truth_verification_item_hash_mismatch",
        )
        verifier_ids = [entry["verifier_actor_id"] for entry in row["verifications"]]
        require(len(verifier_ids) == len(set(verifier_ids)), "duplicate_verifier_for_item")
        require(len(verifier_ids) >= minimum_verifiers, "insufficient_distinct_verifiers")
        require(generator_id not in verifier_ids, "candidate_generator_used_as_verifier")
        require(reviewer_id not in verifier_ids, "qwen_reviewer_used_as_verifier")
        for verification in row["verifications"]:
            require(verification["evaluator_item_sha256"] == item_hash, "verification_record_item_hash_mismatch")
            require(verification["error_family"] == truth["error_family"], "verification_record_family_mismatch")
            require(verification["required_flag"] == truth["required_flag"], "verification_record_flag_mismatch")
            require(
                parse_utc(verification["reviewed_at_utc"], code="verification_reviewed_at_invalid")
                <= sealed_at,
                "verification_after_seal",
            )


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(walk_keys(child))
    return keys


def privacy_context_sha256(item: dict[str, Any], evidence: dict[str, Any]) -> str:
    payload = {
        "packet_id": item["packet_id"],
        "excerpt_id": evidence["excerpt_id"],
        "source_id": evidence["source_id"],
        "speaker_id": evidence["speaker_id"],
        "local_context": evidence["local_context"],
        "text": evidence["text"],
    }
    return sha256_bytes(canonical_bytes(payload))


def validate_packet_bank(
    bank: dict[str, Any],
    *,
    freeze: dict[str, Any],
    evaluator_schema: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require(set(bank) == PACKET_BANK_KEYS, "packet_bank_shape_invalid")
    require(
        bank.get("document_type") == "warrantroute_qwen3_generalist_evaluator_item_bank",
        "packet_bank_type_invalid",
    )
    require(
        bank.get("schema_version") == "qwen3-generalist-evaluator-item-bank-v1",
        "packet_bank_version_invalid",
    )
    require(bank.get("study_id") == freeze["study_id"], "packet_bank_study_id_mismatch")
    require(bank.get("corpus_id") == "dreaddit", "packet_bank_corpus_mismatch")
    require(bank.get("official_source_split") == "test", "packet_bank_split_mismatch")
    require(bank.get("evaluation_role") == "in_domain_audit", "packet_bank_role_mismatch")
    require(
        bank.get("privacy_clearance_status") == "cleared_for_bound_model_and_rater_display",
        "packet_bank_privacy_status_invalid",
    )
    items = bank.get("items")
    require(isinstance(items, list), "packet_bank_items_invalid")
    require(len(items) == freeze["design"]["fixed_n"], "packet_bank_fixed_n_mismatch")
    by_id: dict[str, dict[str, Any]] = {}
    packet_ids: set[str] = set()
    for item in items:
        require(isinstance(item, dict), "evaluator_item_not_object")
        validate_against_schema(item, evaluator_schema, code="evaluator_item_schema_invalid")
        require(item.get("corpus_id") == "dreaddit", "evaluator_item_corpus_mismatch")
        require(not FORBIDDEN_ITEM_KEYS.intersection(walk_keys(item)), "evaluator_item_leakage_key")
        item_id = item["item_id"]
        packet_id = item["packet_id"]
        require(item_id not in by_id, "duplicate_evaluator_item_id")
        require(packet_id not in packet_ids, "duplicate_evaluator_packet_id")
        by_id[item_id] = item
        packet_ids.add(packet_id)

        evidence = item["evidence"]
        display_orders = [row["display_order"] for row in evidence]
        require(display_orders == list(range(1, len(evidence) + 1)), "evidence_display_order_invalid")
        excerpt_ids = [row["excerpt_id"] for row in evidence]
        require(len(excerpt_ids) == len(set(excerpt_ids)), "duplicate_evidence_excerpt_id")
        source_ids = {row["source_id"] for row in evidence}
        coverage = item["source_coverage"]
        require(
            coverage["presented_excerpt_count"] == len(evidence),
            "presented_excerpt_count_mismatch",
        )
        require(
            coverage["presented_source_count"] == len(source_ids),
            "presented_source_count_mismatch",
        )
        distribution = coverage["source_distribution"]
        require(
            {row["source_id"] for row in distribution} == source_ids,
            "source_distribution_ids_mismatch",
        )
        for row in distribution:
            presented = sum(1 for entry in evidence if entry["source_id"] == row["source_id"])
            cited = sum(
                1
                for entry in evidence
                if entry["source_id"] == row["source_id"]
                and entry["candidate_role"] != "context_only"
            )
            require(row["presented_excerpt_count"] == presented, "source_distribution_count_mismatch")
            require(row["candidate_cited_excerpt_count"] == cited, "source_distribution_cited_mismatch")
    return by_id


def validate_truth_map(
    truth: dict[str, Any],
    *,
    freeze: dict[str, Any],
    truth_schema: dict[str, Any],
    items_by_id: dict[str, dict[str, Any]],
) -> tuple[Counter[str], int, dict[str, dict[str, Any]]]:
    validate_against_schema(truth, truth_schema, code="truth_cluster_map_schema_invalid")
    require(truth["study_id"] == freeze["study_id"], "truth_map_study_id_mismatch")
    truth_items = truth["items"]
    require(len(truth_items) == freeze["design"]["fixed_n"], "truth_map_fixed_n_mismatch")
    truth_ids = [row["item_id"] for row in truth_items]
    require(len(truth_ids) == len(set(truth_ids)), "duplicate_truth_item_id")
    require(set(truth_ids) == set(items_by_id), "item_truth_bijection_mismatch")

    generator = freeze["actors"]["candidate_generator"]
    reviewer = freeze["actors"]["reviewer"]
    require(generator["actor_id"] != reviewer["actor_id"], "candidate_generator_is_reviewer")

    base_packet_ids: set[str] = set()
    all_cluster_ids: set[str] = set()
    all_post_member_hashes: set[str] = set()
    family_counts: Counter[str] = Counter()
    for row in truth_items:
        item = items_by_id[row["item_id"]]
        require(row["packet_id"] == item["packet_id"], "truth_packet_id_mismatch")
        require(row["output_id"] == item["output_id"], "truth_output_id_mismatch")
        require(
            row["candidate_generator_actor_id"] == generator["actor_id"],
            "truth_generator_actor_mismatch",
        )
        require(
            row["evaluator_item_sha256"] == sha256_bytes(canonical_bytes(item)),
            "truth_evaluator_item_hash_mismatch",
        )
        family = row["error_family"]
        require(
            row["required_flag"] == EXPECTED_FAMILY_TO_FLAG[family],
            "target_to_flag_mapping_mismatch",
        )
        family_counts[family] += 1
        base_packet_id = row["base_packet_id"]
        require(base_packet_id not in base_packet_ids, "multiple_versions_for_base_packet")
        base_packet_ids.add(base_packet_id)
        for cluster in row["post_clusters"]:
            cluster_id = cluster["cluster_id"]
            require(cluster_id not in all_cluster_ids, "post_cluster_reused_across_items")
            all_cluster_ids.add(cluster_id)
            frame_members = cluster["sampling_frame_member_sha256s"]
            packet_members = cluster["packet_member_sha256s"]
            require(
                len(frame_members) == len(packet_members)
                and set(frame_members) == set(packet_members),
                "incomplete_post_cluster",
            )
            for member_hash in set(frame_members):
                require(
                    member_hash not in all_post_member_hashes,
                    "post_member_reused_under_renamed_cluster",
                )
                all_post_member_hashes.add(member_hash)

    require(set(family_counts) == set(EXPECTED_FAMILY_TO_FLAG), "five_family_coverage_missing")
    balance = freeze["design"]["family_balance"]
    if balance["frozen"]:
        expected = Counter(balance["expected_counts"])
        require(family_counts == expected, "frozen_family_balance_mismatch")
        require(sum(expected.values()) == freeze["design"]["fixed_n"], "family_balance_n_mismatch")
    return family_counts, len(all_cluster_ids), {
        row["item_id"]: row for row in truth_items
    }


def validate_privacy_coverage(
    records: list[dict[str, Any]], items_by_id: dict[str, dict[str, Any]]
) -> int:
    relevant: dict[tuple[str, str], dict[str, Any]] = {}
    for row in records:
        if row.get("corpus_id") != "dreaddit":
            continue
        key = (row.get("packet_id"), row.get("excerpt_id"))
        require(key not in relevant, "duplicate_privacy_excerpt_record")
        relevant[key] = row

    expected_count = 0
    for item in items_by_id.values():
        for evidence in item["evidence"]:
            expected_count += 1
            key = (item["packet_id"], evidence["excerpt_id"])
            row = relevant.get(key)
            require(row is not None, "privacy_review_coverage_missing")
            require(
                row["context_sha256"] == privacy_context_sha256(item, evidence),
                "privacy_context_hash_mismatch",
            )
            require(
                row["decision"] in {"approved_restricted", "approved_for_release"},
                "privacy_review_not_approved",
            )
            require(row["model_processing_cleared"] is True, "privacy_model_processing_not_cleared")
            require(row["rater_display_cleared"] is True, "privacy_rater_display_not_cleared")
    return expected_count


def require_private_metadata_file(path: Path, *, workspace: Path, code_prefix: str) -> None:
    local_root = workspace / "governance" / "local"
    require_absolute_regular_file(
        path,
        allowed_root=local_root,
        required_mode=0o600,
        code_prefix=code_prefix,
    )
    require(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, f"{code_prefix}_parent_mode_invalid")


def require_source_receipt_file(path: Path, *, workspace: Path) -> None:
    require_absolute_regular_file(
        path,
        allowed_root=workspace / "dataset" / "manifests",
        required_mode=None,
        code_prefix="source_receipt",
    )


def require_storage_file(path: Path, *, workspace: Path, code_prefix: str) -> None:
    storage_root = workspace / "Storage"
    require_absolute_regular_file(
        path,
        allowed_root=storage_root,
        required_mode=0o600,
        code_prefix=code_prefix,
    )
    require(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, f"{code_prefix}_parent_mode_invalid")


def require_output_path(path: Path, *, workspace: Path) -> None:
    storage_root = workspace / "Storage"
    require(path.is_absolute(), "output_path_not_absolute")
    require(path.resolve(strict=False) == path, "output_path_resolution_drift")
    require(is_within(path, storage_root), "output_path_outside_storage")
    require(not path.exists(), "output_already_exists")
    require(not path.is_symlink(), "output_path_is_symlink")
    require(path.parent.is_dir() and not path.parent.is_symlink(), "output_parent_invalid")
    require(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, "output_parent_mode_invalid")


def write_exclusive(path: Path, payload: bytes) -> None:
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
        raise PacketSealError("output_create_failed") from exc
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, "output_file_mode_invalid")


def seal_packet_bank(
    *,
    study_freeze_path: Path,
    readiness_report_path: Path,
    governance_record_path: Path,
    reviewer_registry_path: Path,
    privacy_log_path: Path,
    packet_manifest_path: Path,
    source_receipt_path: Path,
    preaccess_record_path: Path,
    verification_bundle_path: Path,
    verification_seal_path: Path,
    packet_bank_path: Path,
    truth_map_path: Path,
    output_path: Path,
    workspace: Path = WORKSPACE,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    require_private_metadata_file(study_freeze_path, workspace=workspace, code_prefix="study_freeze")
    require_private_metadata_file(readiness_report_path, workspace=workspace, code_prefix="readiness")
    require_private_metadata_file(governance_record_path, workspace=workspace, code_prefix="governance")
    require_private_metadata_file(reviewer_registry_path, workspace=workspace, code_prefix="reviewer_registry")
    require_private_metadata_file(privacy_log_path, workspace=workspace, code_prefix="privacy_log")
    require_private_metadata_file(packet_manifest_path, workspace=workspace, code_prefix="packet_manifest")
    require_private_metadata_file(preaccess_record_path, workspace=workspace, code_prefix="preaccess")
    require_source_receipt_file(source_receipt_path, workspace=workspace)
    require_storage_file(
        verification_bundle_path, workspace=workspace, code_prefix="verification_bundle"
    )
    require_storage_file(
        verification_seal_path, workspace=workspace, code_prefix="verification_seal"
    )

    freeze_bytes = read_regular_bytes(study_freeze_path, code_prefix="study_freeze")
    readiness_bytes = read_regular_bytes(readiness_report_path, code_prefix="readiness")
    governance_bytes = read_regular_bytes(governance_record_path, code_prefix="governance")
    reviewer_registry_bytes = read_regular_bytes(
        reviewer_registry_path, code_prefix="reviewer_registry"
    )
    privacy_bytes = read_regular_bytes(privacy_log_path, code_prefix="privacy_log")
    packet_manifest_bytes = read_regular_bytes(packet_manifest_path, code_prefix="packet_manifest")
    source_receipt_bytes = read_regular_bytes(source_receipt_path, code_prefix="source_receipt")
    preaccess_bytes = read_regular_bytes(preaccess_record_path, code_prefix="preaccess")
    verification_bundle_bytes = read_regular_bytes(
        verification_bundle_path, code_prefix="verification_bundle"
    )
    verification_seal_bytes = read_regular_bytes(
        verification_seal_path, code_prefix="verification_seal"
    )
    freeze = load_json_bytes(freeze_bytes, code_prefix="study_freeze")
    readiness = load_json_bytes(readiness_bytes, code_prefix="readiness")
    governance = load_json_bytes(governance_bytes, code_prefix="governance")
    reviewer_registry = load_json_bytes(
        reviewer_registry_bytes, code_prefix="reviewer_registry"
    )
    privacy_log = load_json_bytes(privacy_bytes, code_prefix="privacy_log")
    packet_manifest = load_json_bytes(packet_manifest_bytes, code_prefix="packet_manifest")
    source_receipt = load_json_bytes(source_receipt_bytes, code_prefix="source_receipt")
    preaccess_record = load_json_bytes(preaccess_bytes, code_prefix="preaccess")
    verification_bundle = load_json_bytes(
        verification_bundle_bytes, code_prefix="verification_bundle"
    )
    verification_seal = load_json_bytes(
        verification_seal_bytes, code_prefix="verification_seal"
    )

    schema_root = workspace / "experiments" / "rq2_role_prompted_llm" / "schemas"
    freeze_schema_path = schema_root / STUDY_FREEZE_SCHEMA.name
    truth_schema_path = schema_root / TRUTH_MAP_SCHEMA.name
    packet_manifest_schema_path = schema_root / PACKET_MANIFEST_SCHEMA.name
    preaccess_schema_path = schema_root / PREACCESS_RECORD_SCHEMA.name
    verification_bundle_schema_path = schema_root / VERIFICATION_BUNDLE_SCHEMA.name
    verification_seal_schema_path = schema_root / VERIFICATION_SEAL_SCHEMA.name
    evaluator_schema_path = (
        workspace
        / "experiments"
        / "direction_j_llm_as_rater"
        / "schemas"
        / EVALUATOR_ITEM_SCHEMA.name
    )
    component_path = (
        workspace
        / "experiments"
        / "rq2_role_prompted_llm"
        / "config"
        / GENERALIST_COMPONENT_FREEZE.name
    )
    freeze_schema, freeze_schema_bytes = load_public_json(
        freeze_schema_path,
        allowed_root=workspace,
        code_prefix="study_freeze_schema",
    )
    truth_schema, truth_schema_bytes = load_public_json(
        truth_schema_path,
        allowed_root=workspace,
        code_prefix="truth_map_schema",
    )
    packet_manifest_schema, packet_manifest_schema_bytes = load_public_json(
        packet_manifest_schema_path,
        allowed_root=workspace,
        code_prefix="packet_manifest_schema",
    )
    preaccess_schema, preaccess_schema_bytes = load_public_json(
        preaccess_schema_path,
        allowed_root=workspace,
        code_prefix="preaccess_record_schema",
    )
    verification_bundle_schema, verification_bundle_schema_bytes = load_public_json(
        verification_bundle_schema_path,
        allowed_root=workspace,
        code_prefix="verification_bundle_schema",
    )
    verification_seal_schema, verification_seal_schema_bytes = load_public_json(
        verification_seal_schema_path,
        allowed_root=workspace,
        code_prefix="verification_seal_schema",
    )
    evaluator_schema, evaluator_schema_bytes = load_public_json(
        evaluator_schema_path,
        allowed_root=workspace,
        code_prefix="evaluator_item_schema",
    )
    component, component_bytes = load_public_json(
        component_path,
        allowed_root=workspace,
        code_prefix="generalist_component",
    )

    for schema in (
        freeze_schema,
        truth_schema,
        packet_manifest_schema,
        preaccess_schema,
        verification_bundle_schema,
        verification_seal_schema,
        evaluator_schema,
    ):
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            raise PacketSealError("packet_sealer_schema_invalid") from exc

    validate_against_schema(freeze, freeze_schema, code="study_freeze_schema_invalid")
    dreaddit_readiness = validate_formal_readiness(readiness)
    readiness_assessed_at = parse_utc(
        readiness.get("assessment_as_of_utc"), code="readiness_assessment_time_invalid"
    )
    study_frozen_at = parse_utc(
        freeze.get("frozen_at_utc"), code="study_freeze_frozen_at_invalid"
    )
    privacy_records = validate_privacy_log(privacy_log)
    reviewers = validate_reviewer_registry(reviewer_registry)

    bindings = freeze["bindings"]
    require(
        sha256_file_bytes(readiness_bytes) == bindings["readiness_report_sha256"],
        "readiness_report_hash_mismatch",
    )
    require(
        sha256_file_bytes(governance_bytes) == bindings["governance_record_sha256"],
        "governance_record_hash_mismatch",
    )
    require(
        bindings["governance_record_sha256"]
        == bindings["governance_source_record_sha256"]
        == readiness["source_record_sha256"],
        "governance_source_record_binding_mismatch",
    )
    require(
        sha256_file_bytes(reviewer_registry_bytes) == bindings["reviewer_registry_sha256"],
        "reviewer_registry_hash_mismatch",
    )
    require(
        sha256_file_bytes(privacy_bytes) == bindings["privacy_review_log_sha256"],
        "privacy_log_hash_mismatch",
    )
    require(
        sha256_file_bytes(packet_manifest_bytes) == bindings["packet_manifest_sha256"],
        "packet_manifest_hash_mismatch",
    )
    require(
        sha256_file_bytes(source_receipt_bytes) == bindings["source_receipt_sha256"],
        "source_receipt_hash_mismatch",
    )
    require(
        sha256_file_bytes(preaccess_bytes) == bindings["heldout_preaccess_record_sha256"],
        "preaccess_record_hash_mismatch",
    )
    require(
        sha256_file_bytes(verification_bundle_bytes) == bindings["verification_bundle_sha256"],
        "verification_bundle_hash_mismatch",
    )
    require(
        sha256_file_bytes(verification_seal_bytes) == bindings["verification_seal_sha256"],
        "verification_seal_hash_mismatch",
    )
    require(
        sha256_file_bytes(evaluator_schema_bytes) == bindings["evaluator_item_schema_sha256"],
        "evaluator_item_schema_hash_mismatch",
    )
    require(
        sha256_file_bytes(component_bytes)
        == freeze["actors"]["reviewer"]["component_freeze_sha256"],
        "generalist_component_hash_mismatch",
    )
    require(
        {
            "actor_id": component.get("reviewer_actor", {}).get("actor_id"),
            "task_role": component.get("reviewer_actor", {}).get("task_role"),
            "prompted_role": component.get("reviewer_actor", {}).get("prompted_role"),
            "model_id": component.get("reviewer_actor", {}).get("model_id"),
        }
        == EXPECTED_REVIEWER,
        "generalist_component_actor_binding_invalid",
    )
    require(
        all(
            freeze["actors"]["reviewer"].get(key) == value
            for key, value in EXPECTED_REVIEWER.items()
        ),
        "reviewer_binding_invalid",
    )
    reviewer_snapshot_sha256 = component.get("reviewer_actor", {}).get(
        "local_manifest_file_sha256"
    )
    require(
        freeze["actors"]["reviewer"].get("model_snapshot_sha256")
        == reviewer_snapshot_sha256,
        "reviewer_snapshot_binding_invalid",
    )
    generator = freeze["actors"]["candidate_generator"]
    require(
        generator["actor_id"] != freeze["actors"]["reviewer"]["actor_id"],
        "candidate_generator_is_reviewer",
    )
    require(
        generator["model_id"].strip().casefold()
        != freeze["actors"]["reviewer"]["model_id"].strip().casefold(),
        "candidate_generator_model_is_reviewer_model",
    )
    require(
        generator["snapshot_sha256"] != reviewer_snapshot_sha256,
        "candidate_generator_snapshot_is_reviewer_snapshot",
    )

    require(
        readiness.get("privacy_review_log", {}).get("record_count")
        == len(privacy_records),
        "readiness_privacy_record_count_mismatch",
    )
    require(
        readiness.get("reviewer_registry", {}).get("record_count") == len(reviewers),
        "readiness_reviewer_record_count_mismatch",
    )
    require(
        dreaddit_readiness.get("live_input_integrity_checked") is True,
        "dreaddit_live_input_integrity_not_checked",
    )
    validate_privacy_reviewer_scope(privacy_records, reviewers)

    source_test_file_sha256 = validate_source_receipt(source_receipt)
    packet_manifest_sha256 = sha256_file_bytes(packet_manifest_bytes)
    source_receipt_sha256 = sha256_file_bytes(source_receipt_bytes)
    validate_packet_manifest(
        packet_manifest,
        schema=packet_manifest_schema,
        freeze=freeze,
        source_receipt_sha256=source_receipt_sha256,
        source_test_file_sha256=source_test_file_sha256,
        privacy_log_sha256=sha256_file_bytes(privacy_bytes),
        packet_bank_sha256=bindings["packet_bank_sha256"],
        truth_map_sha256=bindings["truth_cluster_map_sha256"],
    )
    validate_governance_record(
        governance,
        source_receipt_sha256=source_receipt_sha256,
        packet_manifest_sha256=packet_manifest_sha256,
        readiness_assessed_at=readiness_assessed_at,
        study_frozen_at=study_frozen_at,
    )
    validate_preaccess_record(
        preaccess_record,
        schema=preaccess_schema,
        freeze=freeze,
        source_receipt_sha256=source_receipt_sha256,
        packet_manifest_sha256=packet_manifest_sha256,
        readiness_assessed_at=readiness_assessed_at,
        packet_manifest_approved_at=parse_utc(
            packet_manifest["approved_at_utc"], code="packet_manifest_approved_at_invalid"
        ),
    )
    validate_verification_metadata(
        verification_bundle,
        verification_seal,
        bundle_bytes=verification_bundle_bytes,
        bundle_schema=verification_bundle_schema,
        seal_schema=verification_seal_schema,
        freeze=freeze,
    )

    # No source-bearing file is checked or opened before every formal record,
    # registry scope, manifest, receipt, preaccess statement, and independent
    # verification seal above has passed.
    require_storage_file(packet_bank_path, workspace=workspace, code_prefix="packet_bank")
    require_storage_file(truth_map_path, workspace=workspace, code_prefix="truth_map")
    packet_bytes = read_regular_bytes(packet_bank_path, code_prefix="packet_bank")
    truth_bytes = read_regular_bytes(truth_map_path, code_prefix="truth_map")
    require(
        sha256_file_bytes(packet_bytes) == bindings["packet_bank_sha256"],
        "packet_bank_hash_mismatch",
    )
    require(
        sha256_file_bytes(truth_bytes) == bindings["truth_cluster_map_sha256"],
        "truth_map_hash_mismatch",
    )
    packet_bank = load_json_bytes(packet_bytes, code_prefix="packet_bank")
    truth_map = load_json_bytes(truth_bytes, code_prefix="truth_map")
    items_by_id = validate_packet_bank(
        packet_bank,
        freeze=freeze,
        evaluator_schema=evaluator_schema,
    )
    family_counts, cluster_count, truth_rows_by_id = validate_truth_map(
        truth_map,
        freeze=freeze,
        truth_schema=truth_schema,
        items_by_id=items_by_id,
    )
    privacy_excerpt_count = validate_privacy_coverage(privacy_records, items_by_id)
    validate_verification_bundle_and_seal(
        verification_bundle,
        verification_seal,
        bundle_bytes=verification_bundle_bytes,
        bundle_schema=verification_bundle_schema,
        seal_schema=verification_seal_schema,
        freeze=freeze,
        items_by_id=items_by_id,
        truth_rows_by_id=truth_rows_by_id,
    )

    require_output_path(output_path, workspace=workspace)
    packet_bank_hash = sha256_file_bytes(packet_bytes)
    item_id_set_hash = sha256_bytes(canonical_bytes(sorted(items_by_id)))
    require(
        packet_manifest["item_id_set_sha256"] == item_id_set_hash,
        "packet_manifest_item_set_mismatch",
    )
    packet_study_freeze_hash = sha256_file_bytes(freeze_bytes)
    seal = {
        "document_type": "warrantroute_qwen3_generalist_packet_bank_seal",
        "seal_version": "qwen3-generalist-packet-bank-seal-v1",
        "seal_id": f"QGPB_{packet_bank_hash[:16].upper()}",
        "seal_status": "integrity_validated_not_authorization",
        "authorization_claimed_by_this_seal": False,
        "contains_source_text": False,
        "manuscript_result": False,
        "study_id": freeze["study_id"],
        "corpus_id": "dreaddit",
        "official_source_split": "test",
        "evaluation_role": "in_domain_audit",
        "reviewer_actor_id": EXPECTED_REVIEWER["actor_id"],
        "reviewer_model_id": EXPECTED_REVIEWER["model_id"],
        "reviewer_model_snapshot_sha256": reviewer_snapshot_sha256,
        "candidate_generator_actor_id": generator["actor_id"],
        "candidate_generator_model_id": generator["model_id"],
        "candidate_generator_snapshot_sha256": generator["snapshot_sha256"],
        "candidate_generator_prompt_sha256": generator["prompt_sha256"],
        "fixed_n": freeze["design"]["fixed_n"],
        "item_count": freeze["design"]["fixed_n"],
        "item_id_set_sha256": item_id_set_hash,
        "packet_bank_complete": True,
        "privacy_cleared": True,
        "family_counts": dict(sorted(family_counts.items())),
        "post_cluster_count": cluster_count,
        "privacy_cleared_excerpt_count": privacy_excerpt_count,
        "formal_dreaddit_gates_verified": "10/10",
        "bindings": {
            "study_freeze_sha256": packet_study_freeze_hash,
            "packet_study_freeze_sha256": packet_study_freeze_hash,
            "study_design_freeze_sha256": bindings["study_design_freeze_sha256"],
            "readiness_report_sha256": sha256_file_bytes(readiness_bytes),
            "governance_record_sha256": sha256_file_bytes(governance_bytes),
            "governance_source_record_sha256": sha256_file_bytes(governance_bytes),
            "reviewer_registry_sha256": sha256_file_bytes(reviewer_registry_bytes),
            "privacy_review_log_sha256": sha256_file_bytes(privacy_bytes),
            "packet_manifest_sha256": packet_manifest_sha256,
            "source_receipt_sha256": source_receipt_sha256,
            "source_test_file_sha256": source_test_file_sha256,
            "preaccess_record_sha256": sha256_file_bytes(preaccess_bytes),
            "verification_bundle_sha256": sha256_file_bytes(verification_bundle_bytes),
            "verification_seal_sha256": sha256_file_bytes(verification_seal_bytes),
            "candidate_generator_snapshot_sha256": generator["snapshot_sha256"],
            "candidate_generator_prompt_sha256": generator["prompt_sha256"],
            "reviewer_model_snapshot_sha256": reviewer_snapshot_sha256,
            "packet_bank_sha256": packet_bank_hash,
            "truth_cluster_map_sha256": sha256_file_bytes(truth_bytes),
            "study_freeze_schema_sha256": sha256_file_bytes(freeze_schema_bytes),
            "truth_cluster_map_schema_sha256": sha256_file_bytes(truth_schema_bytes),
            "packet_manifest_schema_sha256": sha256_file_bytes(packet_manifest_schema_bytes),
            "preaccess_record_schema_sha256": sha256_file_bytes(preaccess_schema_bytes),
            "verification_bundle_schema_sha256": sha256_file_bytes(
                verification_bundle_schema_bytes
            ),
            "verification_seal_schema_sha256": sha256_file_bytes(
                verification_seal_schema_bytes
            ),
            "evaluator_item_schema_sha256": sha256_file_bytes(evaluator_schema_bytes),
            "generalist_component_freeze_sha256": sha256_file_bytes(component_bytes),
            "scoring_contract_sha256": bindings["scoring_contract_sha256"],
            "analysis_code_sha256": bindings["analysis_code_sha256"],
            "heldout_preaccess_record_sha256": bindings["heldout_preaccess_record_sha256"],
        },
        "warning": (
            "This seal confirms integrity and declared coverage only. It does not grant "
            "authorization and is not a score, result, or manuscript value."
        ),
    }
    seal_bytes = canonical_bytes(seal)
    write_exclusive(output_path, seal_bytes)
    return {
        "status": "sealed",
        "output_sha256": sha256_file_bytes(seal_bytes),
        "fixed_n": seal["fixed_n"],
        "contains_source_text": False,
        "authorization_claimed_by_this_seal": False,
        "manuscript_result": False,
    }


def source_free_dry_run(*, workspace: Path = WORKSPACE) -> dict[str, Any]:
    """Validate static assets and report current metadata readiness without packets."""

    workspace = workspace.resolve()
    schema_root = workspace / "experiments" / "rq2_role_prompted_llm" / "schemas"
    schemas: list[dict[str, Any]] = []
    for schema_path, code_prefix in (
        (schema_root / STUDY_FREEZE_SCHEMA.name, "study_freeze_schema"),
        (schema_root / TRUTH_MAP_SCHEMA.name, "truth_map_schema"),
        (schema_root / PACKET_MANIFEST_SCHEMA.name, "packet_manifest_schema"),
        (schema_root / PREACCESS_RECORD_SCHEMA.name, "preaccess_record_schema"),
        (schema_root / VERIFICATION_BUNDLE_SCHEMA.name, "verification_bundle_schema"),
        (schema_root / VERIFICATION_SEAL_SCHEMA.name, "verification_seal_schema"),
    ):
        schema, _ = load_public_json(
            schema_path,
            allowed_root=workspace,
            code_prefix=code_prefix,
        )
        schemas.append(schema)
    try:
        for schema in schemas:
            jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        raise PacketSealError("packet_sealer_schema_invalid") from exc

    component_path = (
        workspace
        / "experiments"
        / "rq2_role_prompted_llm"
        / "config"
        / GENERALIST_COMPONENT_FREEZE.name
    )
    component, _ = load_public_json(
        component_path,
        allowed_root=workspace,
        code_prefix="generalist_component",
    )
    observed_reviewer = {
        "actor_id": component.get("reviewer_actor", {}).get("actor_id"),
        "task_role": component.get("reviewer_actor", {}).get("task_role"),
        "prompted_role": component.get("reviewer_actor", {}).get("prompted_role"),
        "model_id": component.get("reviewer_actor", {}).get("model_id"),
    }
    require(observed_reviewer == EXPECTED_REVIEWER, "generalist_component_actor_binding_invalid")

    readiness_path = workspace / "governance" / "local" / "readiness_report.local.json"
    require_private_metadata_file(
        readiness_path,
        workspace=workspace,
        code_prefix="readiness",
    )
    readiness_bytes = read_regular_bytes(readiness_path, code_prefix="readiness")
    readiness = load_json_bytes(readiness_bytes, code_prefix="readiness")
    require(
        readiness.get("document_type") == "warrantroute_readiness_report",
        "readiness_document_type_invalid",
    )
    require(readiness.get("contains_real_source_text") is False, "readiness_contains_source_text")
    dreaddit = readiness.get("corpora", {}).get("dreaddit", {})
    require(isinstance(dreaddit, dict), "dreaddit_readiness_missing")
    return {
        "status": "passed_source_free_dry_run",
        "reviewer_actor_id": EXPECTED_REVIEWER["actor_id"],
        "reviewer_model_id": EXPECTED_REVIEWER["model_id"],
        "gate_mode": readiness.get("gate_mode"),
        "dreaddit_completed_gate_count": dreaddit.get("completed_gate_count"),
        "dreaddit_required_gate_count": dreaddit.get("required_gate_count"),
        "dreaddit_real_text_ready": dreaddit.get("real_text_ready") is True,
        "packet_bank_accessed": False,
        "truth_map_accessed": False,
        "model_service_contacted": False,
        "seal_written": False,
        "authorization_claimed_by_this_check": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seal an already authorized and privacy-cleared Dreaddit Qwen3 packet bank."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "dry-run",
        help="Validate schemas, reviewer binding, and current text-free readiness metadata only.",
    )
    seal = commands.add_parser(
        "seal",
        help="Validate and seal an already authorized, privacy-cleared private packet bank.",
    )
    seal.add_argument("--study-freeze", type=Path, required=True)
    seal.add_argument("--readiness-report", type=Path, required=True)
    seal.add_argument("--governance-record", type=Path, required=True)
    seal.add_argument("--reviewer-registry", type=Path, required=True)
    seal.add_argument("--privacy-log", type=Path, required=True)
    seal.add_argument("--packet-manifest", type=Path, required=True)
    seal.add_argument("--source-receipt", type=Path, required=True)
    seal.add_argument("--preaccess-record", type=Path, required=True)
    seal.add_argument("--verification-bundle", type=Path, required=True)
    seal.add_argument("--verification-seal", type=Path, required=True)
    seal.add_argument("--packet-bank", type=Path, required=True)
    seal.add_argument("--truth-map", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "dry-run":
            result = source_free_dry_run()
        else:
            result = seal_packet_bank(
                study_freeze_path=args.study_freeze,
                readiness_report_path=args.readiness_report,
                governance_record_path=args.governance_record,
                reviewer_registry_path=args.reviewer_registry,
                privacy_log_path=args.privacy_log,
                packet_manifest_path=args.packet_manifest,
                source_receipt_path=args.source_receipt,
                preaccess_record_path=args.preaccess_record,
                verification_bundle_path=args.verification_bundle,
                verification_seal_path=args.verification_seal,
                packet_bank_path=args.packet_bank,
                truth_map_path=args.truth_map,
                output_path=args.output,
            )
    except PacketSealError as exc:
        print(json.dumps({"status": "blocked", "error_code": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
