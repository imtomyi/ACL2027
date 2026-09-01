#!/usr/bin/env python3
"""Produce a deterministic, text-free WarrantRoute governance readiness report.

This checker reads governance metadata only. It never discovers or opens corpus
inputs, processed records, prompts, ratings, or source-derived text. Tracked
templates are intentionally blocked; non-template evidence records must live in
``governance/local`` with local-user-only permissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
GOVERNANCE_ROOT = SCRIPT_PATH.parents[1]
LOCAL_ROOT = GOVERNANCE_ROOT / "local"

GOVERNANCE_VERSION = "warrantroute-project-governance-v1"
REPORT_VERSION = "warrantroute-readiness-report-v1"
CORPORA = ("dreaddit", "agyw_focus_groups", "kodis", "candor")
PERSONAL_LOCAL_CORPORA = ("dreaddit", "agyw_focus_groups")
PERSONAL_LOCAL_RESULT_LABEL = "private_personal_exploratory_not_for_publication"
PERSONAL_LOCAL_CAPABILITIES = {
    "local_single_user_processing_allowed": True,
    "local_loopback_model_processing_allowed": True,
    "external_or_cloud_processing_allowed": False,
    "human_rater_or_reviewer_access_allowed": False,
    "publication_or_submission_allowed": False,
    "redistribution_or_release_allowed": False,
}
PLANNED_ROLES = {
    "dreaddit": ("development", "in_domain_audit"),
    "agyw_focus_groups": ("cross_domain_confirmatory",),
    "kodis": ("optional_sensitivity",),
    "candor": ("optional_sensitivity",),
}
DECLARED_REAL_INPUT_STATUSES = {
    "dreaddit": "restricted_source_and_working_copy_present_governance_blocked",
    "agyw_focus_groups": "restricted_source_and_working_copy_present_governance_blocked",
    "kodis": "authorized_real_distribution_absent",
    "candor": "authorized_real_distribution_absent",
}
REQUIRED_CLUSTER_UNITS = {
    "dreaddit": ("post",),
    "agyw_focus_groups": ("focus_group", "transcript_local_speaker"),
    "kodis": ("dialogue_participant_connected_component",),
    "candor": ("conversation_speaker_connected_component",),
}
GATE_IDS = (
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
ALLOWED_STATUSES = {"pending", "approved", "rejected", "expired"}

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
REVIEWER_ID_RE = re.compile(r"^REV_[A-Z0-9]{8,32}$")
PROFILE_ID_RE = re.compile(r"^MEP_[A-Z0-9]{8,32}$")
PACKET_ID_RE = re.compile(r"^PKT_[A-Z0-9]{8,32}$")
EXCERPT_ID_RE = re.compile(r"^EXC_[A-Z0-9]{8,32}$")
OWNER_ID_RE = re.compile(r"^OWNER_[A-Z0-9]{8,32}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")

TOP_LEVEL_KEYS = {
    "document_type",
    "governance_version",
    "record_status",
    "record_id",
    "gate_mode",
    "assessment_as_of_utc",
    "responsible_owner_id",
    "synthetic_lane",
    "corpus_lanes",
    "model_endpoint_profiles",
    "reviewer_registry_reference",
    "privacy_review_log_reference",
    "template_notice",
}
SYNTHETIC_KEYS = {
    "runnable",
    "contains_protected_real_text",
    "independently_authored_fictional_text_required",
    "result_label",
}
LANE_KEYS = {
    "corpus_id",
    "planned_roles",
    "declared_real_input_status",
    "source_receipt_reference",
    "real_text_runnable",
    "required_cluster_units",
    "gates",
}
GATE_KEYS = {
    "id",
    "status",
    "evidence_reference",
    "authority_id",
    "evidence_version",
    "approved_at_utc",
    "expires_at_utc",
    "last_verified_at_utc",
    "details",
}
MODEL_PROFILE_KEYS = {
    "profile_id",
    "provider",
    "account_or_tenant_reference",
    "product_or_endpoint",
    "endpoint_region",
    "model_id",
    "model_snapshot",
    "api_version",
    "provider_terms_version",
    "privacy_terms_version",
    "approved_corpora",
    "approved_data_classification",
    "training_use",
    "retention_mode",
    "retention_days",
    "deletion_behavior",
    "human_access_or_abuse_monitoring",
    "subprocessors_reference",
    "processing_region",
    "approved_at_utc",
    "expires_at_utc",
    "last_verified_at_utc",
}

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


class ReadinessError(RuntimeError):
    """Raised when a governance metadata contract is malformed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReadinessError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"Expected a JSON object in {path.name}")
    return value


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_utc(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label} must be UTC with Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReadinessError(f"{label} is not a valid timestamp") from exc
    require(parsed.tzinfo is not None, f"{label} lacks a timezone")
    return parsed.astimezone(timezone.utc)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def require_private_local_file(path: Path, label: str) -> None:
    require(is_within(path, LOCAL_ROOT), f"{label} must stay under governance/local")
    require(path.is_file() and not path.is_symlink(), f"{label} must be a regular file")
    require(path.stat().st_mode & 0o077 == 0, f"{label} must deny group/other access")


def atomic_private_write(path: Path, content: bytes) -> None:
    require(is_within(path, LOCAL_ROOT), "Readiness output must stay under governance/local")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def validate_record_shape(record: dict[str, Any]) -> None:
    require(set(record) == TOP_LEVEL_KEYS, "Unexpected project-governance fields")
    require(
        record.get("document_type") == "warrantroute_project_governance_record",
        "Governance document type mismatch",
    )
    require(record.get("governance_version") == GOVERNANCE_VERSION, "Governance version mismatch")
    require(record.get("record_status") in {"template_not_approved", "local_evidence_record"}, "Invalid record status")
    require(
        record.get("gate_mode")
        in {"synthetic_only", "real_text_candidate", "personal_local_only"},
        "Invalid gate mode",
    )
    if record.get("gate_mode") == "personal_local_only":
        require(
            record.get("record_status") == "local_evidence_record",
            "Personal-local mode is permitted only in a restricted local record",
        )

    synthetic = record.get("synthetic_lane")
    require(isinstance(synthetic, dict) and set(synthetic) == SYNTHETIC_KEYS, "Invalid synthetic lane")
    require(synthetic.get("contains_protected_real_text") is False, "Synthetic lane contains real text")
    require(
        synthetic.get("independently_authored_fictional_text_required") is True,
        "Synthetic lane permits source-derived fixtures",
    )
    require(synthetic.get("result_label") == "synthetic_only", "Synthetic result label changed")

    lanes = record.get("corpus_lanes")
    require(isinstance(lanes, dict) and set(lanes) == set(CORPORA), "Corpus lane set mismatch")
    for corpus_id in CORPORA:
        lane = lanes[corpus_id]
        require(isinstance(lane, dict) and set(lane) == LANE_KEYS, f"Invalid {corpus_id} lane")
        require(lane.get("corpus_id") == corpus_id, f"{corpus_id} lane ID mismatch")
        require(
            lane.get("planned_roles") == list(PLANNED_ROLES[corpus_id]),
            f"{corpus_id} planned roles changed outside governance version",
        )
        require(
            lane.get("declared_real_input_status") == DECLARED_REAL_INPUT_STATUSES[corpus_id],
            f"{corpus_id} declared input status changed outside governance version",
        )
        require(lane.get("real_text_runnable") is False, f"Tracked/local record cannot predeclare {corpus_id} runnable")
        require(
            lane.get("required_cluster_units") == list(REQUIRED_CLUSTER_UNITS[corpus_id]),
            f"{corpus_id} cluster units changed outside governance version",
        )
        gates = lane.get("gates")
        require(isinstance(gates, list) and len(gates) == 10, f"{corpus_id} must have exactly ten gates")
        require(tuple(gate.get("id") for gate in gates if isinstance(gate, dict)) == GATE_IDS, f"{corpus_id} gate IDs/order mismatch")
        for gate in gates:
            require(isinstance(gate, dict) and set(gate) == GATE_KEYS, f"Invalid {corpus_id} gate shape")
            require(gate.get("status") in ALLOWED_STATUSES, f"Invalid {corpus_id} gate status")
            require(isinstance(gate.get("details"), dict), f"Invalid {corpus_id} gate details")

    profiles = record.get("model_endpoint_profiles")
    require(isinstance(profiles, list), "Model endpoint profiles must be a list")
    if record.get("gate_mode") == "personal_local_only":
        require(
            profiles == [],
            "Personal-local mode cannot authorize provider or cloud endpoint profiles",
        )
    seen: set[str] = set()
    for profile in profiles:
        require(isinstance(profile, dict) and set(profile) == MODEL_PROFILE_KEYS, "Invalid model endpoint profile")
        profile_id = profile.get("profile_id")
        require(isinstance(profile_id, str) and PROFILE_ID_RE.fullmatch(profile_id), "Invalid model endpoint profile ID")
        require(profile_id not in seen, "Duplicate model endpoint profile ID")
        seen.add(profile_id)
        approved_corpora = profile.get("approved_corpora")
        require(
            isinstance(approved_corpora, list)
            and all(isinstance(value, str) for value in approved_corpora)
            and len(approved_corpora) == len(set(approved_corpora))
            and set(approved_corpora).issubset(CORPORA),
            "Invalid model endpoint corpus scope",
        )
    owner_id = record.get("responsible_owner_id")
    require(
        owner_id is None
        or (isinstance(owner_id, str) and OWNER_ID_RE.fullmatch(owner_id)),
        "Responsible owner ID must be pseudonymous",
    )


def validate_reviewer_registry(registry: dict[str, Any], template_ok: bool) -> dict[str, dict[str, Any]]:
    require(set(registry) == REVIEWER_REGISTRY_KEYS, "Unexpected reviewer-registry fields")
    require(registry.get("document_type") == "warrantroute_reviewer_registry", "Reviewer registry type mismatch")
    require(registry.get("registry_version") == "warrantroute-reviewer-registry-v1", "Reviewer registry version mismatch")
    require(registry.get("contains_direct_identifiers") is False, "Reviewer registry claims direct identifiers")
    require(registry.get("reviewer_id_format") == "REV_[A-Z0-9]{8,32}", "Reviewer ID format mismatch")
    if template_ok:
        require(registry.get("record_status") == "template_not_approved", "Tracked reviewer registry is not an unapproved template")
        require(registry.get("identity_crosswalk_reference") is None, "Tracked reviewer template references an identity crosswalk")
    else:
        require(registry.get("record_status") == "local_evidence_record", "Reviewer registry is not a local evidence record")
    reviewers = registry.get("reviewers")
    require(isinstance(reviewers, list), "Reviewer list must be an array")
    result: dict[str, dict[str, Any]] = {}
    for reviewer in reviewers:
        require(isinstance(reviewer, dict) and set(reviewer) == REVIEWER_KEYS, "Invalid reviewer record")
        reviewer_id = reviewer.get("reviewer_id")
        require(isinstance(reviewer_id, str) and REVIEWER_ID_RE.fullmatch(reviewer_id), "Reviewer ID is not pseudonymous")
        require(reviewer_id not in result, "Duplicate reviewer ID")
        require(reviewer.get("status") in {"pending", "active", "expired", "withdrawn"}, "Invalid reviewer status")
        roles = reviewer.get("roles")
        require(
            isinstance(roles, list)
            and all(nonempty(role) for role in roles)
            and len(roles) == len(set(roles)),
            "Reviewer roles must be unique nonempty strings",
        )
        approved_corpora = reviewer.get("approved_corpora")
        require(
            isinstance(approved_corpora, list)
            and all(isinstance(value, str) for value in approved_corpora)
            and len(approved_corpora) == len(set(approved_corpora))
            and set(approved_corpora).issubset(CORPORA),
            "Invalid reviewer corpus scope",
        )
        result[reviewer_id] = reviewer
    if not template_ok and result:
        require(nonempty(registry.get("identity_crosswalk_reference")), "Reviewer identity crosswalk reference missing")
    return result


def validate_privacy_log(log: dict[str, Any], template_ok: bool) -> list[dict[str, Any]]:
    require(set(log) == PRIVACY_LOG_KEYS, "Unexpected privacy-log fields")
    require(log.get("document_type") == "warrantroute_privacy_review_log", "Privacy log type mismatch")
    require(log.get("log_version") == "warrantroute-privacy-review-log-v1", "Privacy log version mismatch")
    require(log.get("contains_source_text") is False, "Privacy log must be text-free")
    require(log.get("minimum_distinct_reviewers_per_excerpt") == 2, "Privacy log must require two reviewers")
    if template_ok:
        require(log.get("record_status") == "template_not_approved", "Tracked privacy log is not an unapproved template")
    else:
        require(log.get("record_status") == "local_evidence_record", "Privacy log is not a local evidence record")
    records = log.get("records")
    require(isinstance(records, list), "Privacy review records must be an array")
    seen_excerpts: set[tuple[str, str]] = set()
    for item in records:
        require(isinstance(item, dict) and set(item) == PRIVACY_RECORD_KEYS, "Invalid privacy review record")
        require(item.get("corpus_id") in CORPORA, "Invalid privacy review corpus")
        require(
            isinstance(item.get("packet_id"), str) and PACKET_ID_RE.fullmatch(item["packet_id"]),
            "Privacy review packet ID is not pseudonymous",
        )
        require(
            isinstance(item.get("excerpt_id"), str) and EXCERPT_ID_RE.fullmatch(item["excerpt_id"]),
            "Privacy review excerpt ID is not pseudonymous",
        )
        excerpt_key = (item["corpus_id"], item["excerpt_id"])
        require(excerpt_key not in seen_excerpts, "Duplicate privacy review excerpt record")
        seen_excerpts.add(excerpt_key)
        require(valid_sha(item.get("context_sha256")), "Privacy review context hash invalid")
        reviewer_ids = item.get("reviewer_ids")
        require(
            isinstance(reviewer_ids, list)
            and len(reviewer_ids) >= 2
            and all(isinstance(value, str) and REVIEWER_ID_RE.fullmatch(value) for value in reviewer_ids)
            and len(reviewer_ids) == len(set(reviewer_ids)),
            "Privacy review requires distinct pseudonymous reviewer IDs",
        )
        parse_utc(item.get("reviewed_at_utc"), "privacy review reviewed_at_utc")
        require(item.get("decision") in {"approved_restricted", "approved_for_release", "rejected"}, "Invalid privacy review decision")
        for key in ("model_processing_cleared", "rater_display_cleared", "quotation_cleared"):
            require(isinstance(item.get(key), bool), f"Privacy review {key} must be boolean")
    return records


def common_gate_blockers(gate: dict[str, Any], as_of: datetime) -> list[str]:
    status = gate["status"]
    if status != "approved":
        return [f"status_{status}"]
    blockers: list[str] = []
    for key in ("evidence_reference", "authority_id", "evidence_version"):
        if not nonempty(gate.get(key)):
            blockers.append(f"missing_{key}")
    dates: dict[str, datetime] = {}
    for key in ("approved_at_utc", "expires_at_utc", "last_verified_at_utc"):
        try:
            dates[key] = parse_utc(gate.get(key), key)
        except ReadinessError:
            blockers.append(f"invalid_{key}")
    if len(dates) == 3:
        if dates["approved_at_utc"] > as_of:
            blockers.append("approval_not_yet_effective")
        if dates["expires_at_utc"] <= as_of:
            blockers.append("approval_expired")
        if dates["last_verified_at_utc"] > as_of:
            blockers.append("verification_timestamp_in_future")
        if dates["last_verified_at_utc"] < dates["approved_at_utc"]:
            blockers.append("version_not_verified_after_approval")
    return blockers


def required_detail_strings(details: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [f"missing_{key}" for key in keys if not nonempty(details.get(key))]


def endpoint_profile_blockers(profile: dict[str, Any], corpus_id: str, as_of: datetime) -> list[str]:
    blockers: list[str] = []
    strings = (
        "provider",
        "account_or_tenant_reference",
        "product_or_endpoint",
        "endpoint_region",
        "model_id",
        "model_snapshot",
        "api_version",
        "provider_terms_version",
        "privacy_terms_version",
        "approved_data_classification",
        "retention_mode",
        "deletion_behavior",
        "human_access_or_abuse_monitoring",
        "subprocessors_reference",
        "processing_region",
    )
    blockers.extend(required_detail_strings(profile, strings))
    if corpus_id not in profile.get("approved_corpora", []):
        blockers.append("endpoint_not_approved_for_corpus")
    if profile.get("training_use") != "disabled":
        blockers.append("provider_training_not_disabled")
    days = profile.get("retention_days")
    if not isinstance(days, int) or isinstance(days, bool) or days < 0:
        blockers.append("invalid_provider_retention_days")
    try:
        approved = parse_utc(profile.get("approved_at_utc"), "endpoint approved_at_utc")
        expires = parse_utc(profile.get("expires_at_utc"), "endpoint expires_at_utc")
        verified = parse_utc(profile.get("last_verified_at_utc"), "endpoint last_verified_at_utc")
        if approved > as_of:
            blockers.append("endpoint_approval_not_yet_effective")
        if expires <= as_of:
            blockers.append("endpoint_approval_expired")
        if verified > as_of or verified < approved:
            blockers.append("endpoint_version_verification_invalid")
    except ReadinessError:
        blockers.append("invalid_endpoint_approval_dates")
    return blockers


def reviewer_blockers(
    reviewer: dict[str, Any],
    corpus_id: str,
    as_of: datetime,
    required_roles: set[str],
) -> list[str]:
    blockers: list[str] = []
    if reviewer.get("status") != "active":
        blockers.append("reviewer_not_active")
    if corpus_id not in reviewer.get("approved_corpora", []):
        blockers.append("reviewer_not_approved_for_corpus")
    if not required_roles.intersection(reviewer.get("roles", [])):
        blockers.append("reviewer_role_not_approved")
    for key in ("privacy_training_version", "confidentiality_acknowledgment_version"):
        if not nonempty(reviewer.get(key)):
            blockers.append(f"missing_reviewer_{key}")
    try:
        approved = parse_utc(reviewer.get("approved_at_utc"), "reviewer approved_at_utc")
        expires = parse_utc(reviewer.get("expires_at_utc"), "reviewer expires_at_utc")
        verified = parse_utc(reviewer.get("last_verified_at_utc"), "reviewer last_verified_at_utc")
        if approved > as_of:
            blockers.append("reviewer_approval_not_yet_effective")
        if expires <= as_of:
            blockers.append("reviewer_approval_expired")
        if verified > as_of or verified < approved:
            blockers.append("reviewer_version_verification_invalid")
    except ReadinessError:
        blockers.append("invalid_reviewer_approval_dates")
    return blockers


def gate_specific_blockers(
    gate: dict[str, Any],
    lane: dict[str, Any],
    corpus_id: str,
    as_of: datetime,
    profiles: dict[str, dict[str, Any]],
    reviewers: dict[str, dict[str, Any]],
    privacy_records: list[dict[str, Any]],
) -> list[str]:
    if gate["status"] != "approved":
        return []
    details = gate["details"]
    gate_id = gate["id"]
    blockers: list[str] = []

    if gate_id == "institutional_determination":
        blockers.extend(required_detail_strings(details, ("determination_reference", "determination_version", "determination_type")))
        for key in ("secondary_use", "model_processing", "human_rater_exposure", "release_review_scope"):
            if details.get(key) is not True:
                blockers.append(f"institutional_scope_missing_{key}")
    elif gate_id == "source_platform_authorization":
        blockers.extend(required_detail_strings(details, ("source_name", "source_version", "source_terms_version", "platform_terms_version")))
        uses = details.get("approved_uses")
        required_uses = {"restricted_preprocessing", "model_processing", "rater_display", "quotation", "release_review"}
        if not isinstance(uses, dict) or set(uses) != required_uses:
            blockers.append("invalid_source_approved_uses")
        elif not all(value is True for value in uses.values()):
            blockers.append("source_use_scope_incomplete")
    elif gate_id == "provider_model_processing":
        profile_ids = details.get("model_endpoint_profile_ids")
        if (
            not isinstance(profile_ids, list)
            or not profile_ids
            or not all(
                isinstance(profile_id, str) and PROFILE_ID_RE.fullmatch(profile_id)
                for profile_id in profile_ids
            )
            or len(profile_ids) != len(set(profile_ids))
        ):
            blockers.append("missing_model_endpoint_profiles")
        else:
            for profile_id in profile_ids:
                profile = profiles.get(profile_id)
                if profile is None:
                    blockers.append("unknown_model_endpoint_profile")
                else:
                    blockers.extend(endpoint_profile_blockers(profile, corpus_id, as_of))
    elif gate_id == "exact_corpus_input_contract":
        blockers.extend(required_detail_strings(details, ("received_version", "source_receipt_reference", "source_receipt_sha256", "split", "experimental_role", "approved_processing_purpose")))
        if details.get("source_receipt_sha256") is not None and not valid_sha(details.get("source_receipt_sha256")):
            blockers.append("invalid_source_receipt_sha256")
        for key in ("allowed_fields", "prohibited_fields"):
            values = details.get(key)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and SAFE_TOKEN_RE.fullmatch(value) for value in values)
                or len(values) != len(set(values))
            ):
                blockers.append(f"missing_{key}")
    elif gate_id == "two_person_excerpt_privacy_review":
        packet_hash = details.get("packet_manifest_sha256")
        if not valid_sha(packet_hash):
            blockers.append("invalid_packet_manifest_sha256")
        relevant = [row for row in privacy_records if row["corpus_id"] == corpus_id]
        if not relevant:
            blockers.append("no_privacy_review_records")
        for row in relevant:
            if parse_utc(row["reviewed_at_utc"], "privacy review reviewed_at_utc") > as_of:
                blockers.append("privacy_review_timestamp_in_future")
            for reviewer_id in row["reviewer_ids"]:
                reviewer = reviewers.get(reviewer_id)
                if reviewer is None:
                    blockers.append("unknown_privacy_reviewer")
                else:
                    blockers.extend(
                        reviewer_blockers(
                            reviewer, corpus_id, as_of, {"privacy_reviewer"}
                        )
                    )
            if row["decision"] == "rejected":
                blockers.append("rejected_excerpt_in_review_log")
            if not row["model_processing_cleared"] or not row["rater_display_cleared"]:
                blockers.append("excerpt_use_permissions_incomplete")
    elif gate_id == "cluster_aware_sampling":
        blockers.extend(required_detail_strings(details, ("sampling_plan_reference", "sampling_plan_sha256", "sampling_plan_version")))
        if details.get("sampling_plan_sha256") is not None and not valid_sha(details.get("sampling_plan_sha256")):
            blockers.append("invalid_sampling_plan_sha256")
        if details.get("cluster_units") != lane["required_cluster_units"]:
            blockers.append("cluster_units_do_not_match_lane")
        if details.get("complete_clusters_preserved") is not True:
            blockers.append("complete_clusters_not_preserved")
    elif gate_id == "frozen_study_manifest":
        blockers.extend(required_detail_strings(details, ("study_manifest_reference", "study_manifest_sha256", "study_manifest_version", "frozen_at_utc")))
        if details.get("study_manifest_sha256") is not None and not valid_sha(details.get("study_manifest_sha256")):
            blockers.append("invalid_study_manifest_sha256")
    elif gate_id == "rater_and_service_access_controls":
        blockers.extend(required_detail_strings(details, ("rater_protocol_version", "consent_version", "access_control_version", "withdrawal_procedure_reference")))
        approved_roles = details.get("approved_roles")
        if (
            not isinstance(approved_roles, list)
            or not approved_roles
            or not all(isinstance(role, str) and SAFE_TOKEN_RE.fullmatch(role) for role in approved_roles)
            or len(approved_roles) != len(set(approved_roles))
        ):
            blockers.append("missing_approved_rater_roles")
            approved_role_set: set[str] = set()
        else:
            approved_role_set = set(approved_roles)
        if not reviewers:
            blockers.append("reviewer_registry_empty")
        eligible_reviewers = 0
        for reviewer in reviewers.values():
            reviewer_reasons = reviewer_blockers(
                reviewer, corpus_id, as_of, approved_role_set
            )
            if not reviewer_reasons:
                eligible_reviewers += 1
        if reviewers and eligible_reviewers == 0:
            blockers.append("no_current_reviewer_for_approved_role_and_corpus")
        for key in ("least_privilege_confirmed", "encryption_in_transit", "encryption_at_rest", "access_logging_enabled"):
            if details.get(key) is not True:
                blockers.append(f"rater_control_missing_{key}")
    elif gate_id == "retention_deletion_controls":
        blockers.extend(required_detail_strings(details, ("retention_schedule_version", "project_delete_by_utc", "provider_delete_by_utc", "deletion_procedure_reference", "deletion_verification_method", "incident_response_reference", "responsible_owner_id")))
        for key in ("project_delete_by_utc", "provider_delete_by_utc"):
            try:
                if parse_utc(details.get(key), key) <= as_of:
                    blockers.append(f"{key}_not_future")
            except ReadinessError:
                blockers.append(f"invalid_{key}")
        owner_id = details.get("responsible_owner_id")
        if owner_id is not None and not (
            isinstance(owner_id, str) and OWNER_ID_RE.fullmatch(owner_id)
        ):
            blockers.append("responsible_owner_id_not_pseudonymous")
    elif gate_id == "release_controls":
        blockers.extend(required_detail_strings(details, ("release_manifest_reference", "release_manifest_sha256", "release_manifest_version")))
        if details.get("release_manifest_sha256") is not None and not valid_sha(details.get("release_manifest_sha256")):
            blockers.append("invalid_release_manifest_sha256")
        artifact_classes = details.get("permitted_artifact_classes")
        if (
            not isinstance(artifact_classes, list)
            or not artifact_classes
            or not all(
                isinstance(value, str) and SAFE_TOKEN_RE.fullmatch(value)
                for value in artifact_classes
            )
            or len(artifact_classes) != len(set(artifact_classes))
        ):
            blockers.append("missing_permitted_artifact_classes")
        for key in ("privacy_review_complete", "license_and_attribution_complete"):
            if details.get(key) is not True:
                blockers.append(f"release_{key}_false")
    return sorted(set(blockers))


def build_report(
    record: dict[str, Any],
    record_digest: str,
    as_of: datetime,
    reviewers: dict[str, dict[str, Any]],
    privacy_records: list[dict[str, Any]],
) -> dict[str, Any]:
    profiles = {profile["profile_id"]: profile for profile in record["model_endpoint_profiles"]}
    personal_mode = record.get("gate_mode") == "personal_local_only"
    corpus_reports: dict[str, Any] = {}
    all_ready = True
    for corpus_id in CORPORA:
        lane = record["corpus_lanes"][corpus_id]
        if personal_mode:
            gate_results = []
            completed = 0
            required_gate_count = 0
        else:
            gate_results = []
            for gate in lane["gates"]:
                reasons = common_gate_blockers(gate, as_of)
                reasons.extend(
                    gate_specific_blockers(
                        gate,
                        lane,
                        corpus_id,
                        as_of,
                        profiles,
                        reviewers,
                        privacy_records,
                    )
                )
                reasons = sorted(set(reasons))
                gate_results.append(
                    {
                        "id": gate["id"],
                        "complete": not reasons,
                        "blocking_reason_codes": reasons,
                    }
                )
            completed = sum(result["complete"] for result in gate_results)
            required_gate_count = len(GATE_IDS)
        ready = (
            not personal_mode
            and completed == len(GATE_IDS)
            and record.get("gate_mode") == "real_text_candidate"
        )
        personal_scope_eligible = (
            personal_mode
            and record.get("record_status") == "local_evidence_record"
            and corpus_id in PERSONAL_LOCAL_CORPORA
            and lane.get("declared_real_input_status")
            == "restricted_source_and_working_copy_present_governance_blocked"
            and nonempty(lane.get("source_receipt_reference"))
        )
        all_ready = all_ready and ready
        corpus_report = {
            "declared_real_input_status": lane["declared_real_input_status"],
            "planned_roles": lane["planned_roles"],
            "required_gate_count": required_gate_count,
            "completed_gate_count": completed,
            "real_text_ready": ready,
            "gates": gate_results,
        }
        if personal_mode:
            corpus_report.update(
                {
                    "external_gates_applicable": False,
                    "personal_local_scope_eligible": personal_scope_eligible,
                    "live_input_integrity_checked": False,
                }
            )
        corpus_reports[corpus_id] = corpus_report

    template = record.get("record_status") == "template_not_approved"
    if template:
        all_ready = False
    report = {
        "document_type": "warrantroute_readiness_report",
        "report_version": REPORT_VERSION,
        "assessment_as_of_utc": as_of.isoformat().replace("+00:00", "Z"),
        "source_record_sha256": record_digest,
        "record_status": record["record_status"],
        "gate_mode": record["gate_mode"],
        "synthetic_lane_runnable": bool(record["synthetic_lane"]["runnable"]),
        "contains_real_source_text": False,
        "exact_required_gate_count": 0 if personal_mode else len(GATE_IDS),
        "required_gate_ids": [] if personal_mode else list(GATE_IDS),
        "all_real_corpora_ready": all_ready,
        "corpora": corpus_reports,
        "reviewer_registry": {
            "record_count": len(reviewers),
            "direct_identifiers_in_report": False,
        },
        "privacy_review_log": {
            "record_count": len(privacy_records),
            "source_text_in_report": False,
        },
        "warning_codes": (
            [
                "private_personal_exploratory_only",
                "not_institutional_or_external_approval",
                "not_for_publication_submission_or_redistribution",
                "formal_real_text_ready_remains_false",
            ]
            if personal_mode
            else [
                "mechanical_check_not_approval",
                "synthetic_and_real_results_must_remain_separate",
                "underlying_documentary_evidence_required",
            ]
        ),
    }
    if personal_mode:
        report["personal_local_only"] = {
            "active": True,
            "scope_assessment_only": True,
            "live_input_integrity_checked": False,
            "execution_requires_exact_policy_validation": True,
            "result_label": PERSONAL_LOCAL_RESULT_LABEL,
            "allowed_corpora": list(PERSONAL_LOCAL_CORPORA),
            "capabilities": dict(PERSONAL_LOCAL_CAPABILITIES),
            "all_allowed_corpora_scope_eligible": all(
                corpus_reports[corpus_id]["personal_local_scope_eligible"]
                for corpus_id in PERSONAL_LOCAL_CORPORA
            ),
        }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check all four WarrantRoute corpus governance lanes")
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--reviewer-registry", type=Path)
    parser.add_argument("--privacy-log", type=Path)
    parser.add_argument("--as-of", required=True, help="Deterministic UTC assessment timestamp ending in Z")
    parser.add_argument("--output", type=Path, help="Optional restricted local JSON report")
    return parser.parse_args()


def run(args: argparse.Namespace) -> dict[str, Any]:
    record = load_json(args.record)
    validate_record_shape(record)
    template = record["record_status"] == "template_not_approved"
    if not template:
        require_private_local_file(args.record, "Governance evidence record")
        require(record.get("record_id") is not None, "Local evidence record ID is missing")
    else:
        require(record.get("gate_mode") == "synthetic_only", "Tracked template must remain synthetic-only")
        require(all(gate["status"] == "pending" for lane in record["corpus_lanes"].values() for gate in lane["gates"]), "Tracked template gate is not pending")

    reviewers: dict[str, dict[str, Any]] = {}
    if args.reviewer_registry is not None:
        if not template:
            require_private_local_file(args.reviewer_registry, "Reviewer registry")
        registry = load_json(args.reviewer_registry)
        reviewers = validate_reviewer_registry(registry, template_ok=template)
    privacy_records: list[dict[str, Any]] = []
    if args.privacy_log is not None:
        if not template:
            require_private_local_file(args.privacy_log, "Privacy review log")
        log = load_json(args.privacy_log)
        privacy_records = validate_privacy_log(log, template_ok=template)

    as_of = parse_utc(args.as_of, "--as-of")
    report = build_report(record, sha256_path(args.record), as_of, reviewers, privacy_records)
    if args.output is not None:
        require(not args.output.is_symlink(), "Readiness output must not be a symlink")
        atomic_private_write(args.output.resolve(), canonical_bytes(report))
    return report


def main() -> None:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, json.JSONDecodeError, ReadinessError) as exc:
        if isinstance(exc, OSError):
            print("Project readiness check failed: restricted file operation failed", file=sys.stderr)
        else:
            print(f"Project readiness check failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
