#!/usr/bin/env python3
"""Fail-closed, read-only readiness check for Direction J synthetic execution.

This checker makes no provider calls and never writes a readiness record or
receipt. A passing record authorizes only the frozen fictional qualification
lane. It cannot authorize protected real-text access or processing.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
TEMPLATE_PATH = DIRECTION_ROOT / "config" / "execution_readiness.template.json"
GOVERNANCE_PATH = DIRECTION_ROOT / "config" / "governance_gate.template.json"
FREEZE_PATH = DIRECTION_ROOT / "config" / "freeze_v1.json"
RUN_ID = "20260825_synthetic_paired_qualification_prepared"
RUN_ROOT = DIRECTION_ROOT / "runs" / RUN_ID
RUN_MANIFEST_PATH = RUN_ROOT / "run_manifest.json"
BUILD_REPORT_PATH = RUN_ROOT / "build_report.json"
EVALUATOR_ITEMS_PATH = RUN_ROOT / "evaluator_items.jsonl"
GUIDE_PATH = DIRECTION_ROOT / "protocol" / "shared_rater_guide_v1.md"
PROMPT_PATH = DIRECTION_ROOT / "protocol" / "llm_judge_prompt_v1.md"
RATING_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "shared_rating.schema.json"
REQUEST_PACKET_RENDERER_PATH = DIRECTION_ROOT / "scripts" / "render_request_packets.py"
REQUEST_RENDERING_CONTRACT_PATH = DIRECTION_ROOT / "protocol" / "request_rendering_contract.md"
REQUEST_PACKETS_PATH = RUN_ROOT / "request-packets" / "request_packets_v1.jsonl"
ASSIGNMENT_ROOT = RUN_ROOT / "assignments"
BUNDLE_ROOT = (
    PROJECT_ROOT
    / "experiments"
    / "qualitative_coding_baselines"
    / "runs"
    / "20260825_synthetic_qualification"
    / "blinded"
)

VERSION = "direction-j-synthetic-execution-readiness-v1"
TEMPLATE_NOTICE = (
    "This tracked template is incomplete, is not an approval record, and does "
    "not authorize model calls, human rating, or any real-text access or processing."
)
GEMINI_DEADLINE = datetime(2026, 10, 16, tzinfo=timezone.utc)
EXPECTED_BENCHMARK_SHA256 = (
    "d38fbb7860edd47d21e22e51da8f44a71ec6ddcb3fc5ac217598747d54865b39"
)
EXPECTED_ASSIGNMENTS = {
    "DOMAIN_QUAL_rep1.csv",
    "J_PRIMARY_rep1.csv",
    "J_PRIMARY_rep2.csv",
    "J_PRIMARY_rep3.csv",
    "J_SENS_GEMINI_rep1.csv",
    "QME_QUAL_rep1.csv",
    "charlie_rep1.csv",
}
EXPECTED_REQUEST_PACKET_COUNT = 96
REQUEST_PACKET_WIRE_STATUS = "pending_provider_profile_and_wire_validation"
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

TOP_FIELDS = {
    "document_type",
    "readiness_version",
    "record_status",
    "record_id",
    "prepared_at_utc",
    "prepared_by",
    "approved_at_utc",
    "approved_by",
    "template_notice",
    "authorization_scope",
    "lineage",
    "human_actors",
    "human_instrument",
    "provider_profiles",
    "capture_controls",
    "budget",
    "credentials",
    "final_attestation",
}
SCOPE_FIELDS = {
    "execution_lane",
    "contains_real_source_text",
    "real_text_authorized",
    "model_calls_authorized",
    "human_rating_authorized",
}
LINEAGE_FIELDS = {
    "status",
    "run_id",
    "run_manifest_path",
    "run_manifest_sha256",
    "freeze_path",
    "freeze_sha256",
    "build_report_path",
    "build_report_sha256",
    "evaluator_items_path",
    "evaluator_items_sha256",
    "source_receipt_sha256",
    "synthetic_benchmark_sha256",
    "blinded_bundle_fileset_sha256",
    "shared_rater_guide_sha256",
    "llm_judge_prompt_sha256",
    "shared_rating_schema_sha256",
    "governance_gate_sha256",
    "request_packet_renderer_path",
    "request_packet_renderer_sha256",
    "request_rendering_contract_path",
    "request_rendering_contract_sha256",
    "request_packets_path",
    "request_packets_sha256",
    "request_packets_expected_count",
    "request_packets_wire_status",
    "assignment_sha256",
}
REQUEST_PACKET_FIELDS = {
    "request_packet_version",
    "request_packet_id",
    "study_id",
    "run_id",
    "qualification_scope",
    "contains_real_source_text",
    "evaluation_role",
    "actor_id",
    "actor_kind",
    "assignment_id",
    "rating_repetition",
    "sequence",
    "item_id",
    "packet_id",
    "output_id",
    "corpus_id",
    "interface_version",
    "item_schema_version",
    "rating_schema_version",
    "shared_rater_guide_version",
    "prompt_version",
    "item_payload_sha256",
    "semantic_input_sha256",
    "shared_rater_guide_sha256",
    "prompt_source_sha256",
    "messages",
    "message_sha256",
    "rendered_messages_sha256",
    "response_schema",
    "response_schema_sha256",
    "response_schema_hash_rule",
    "post_validation_schema",
    "post_validation_schema_sha256",
    "post_validation_schema_hash_rule",
    "post_validation_required",
    "structured_decoding_replaces_post_validation",
    "frozen_model_settings",
    "frozen_model_settings_sha256",
    "frozen_prompting_policy",
    "frozen_prompting_policy_sha256",
    "wire_adapter_status",
    "provider_wire_adapter",
    "lineage",
}
PROVIDER_NEUTRAL_WIRE_FIELDS = {
    "wire_adapter_status",
    "provider_wire_request",
    "provider_wire_request_rendered",
    "network_dispatch_authorized",
    "credential_access_authorized",
}
CHARLIE_FIELDS = {
    "status",
    "actor_id",
    "expected_role",
    "identity_or_roster_reference",
    "task_role_summary",
    "qualification_summary",
    "qualification_reference",
    "role_and_qualification_confirmed",
    "independence_relationship_classification",
    "independence_relationship_summary",
    "independence_relationship_reference",
    "primary_independence_analysis_eligible",
    "separate_nonindependent_reporting_required",
    "private_condition_blinded_until_lock",
    "other_ratings_blinded_until_lock",
    "authorized_for_synthetic_qualification",
    "authorization_or_consent_reference",
    "declared_by",
    "declared_at_utc",
}
EXPERT_FIELDS = {
    "status",
    "actor_id",
    "expected_role",
    "identity_or_roster_reference",
    "qualification_summary",
    "qualification_reference",
    "role_and_qualification_confirmed",
    "independent_from_item_construction",
    "independent_from_first_stage_rating",
    "private_condition_blinded_until_lock",
    "other_ratings_blinded_until_lock",
    "eligible_for_locked_individual_expert_rating",
    "authorized_for_synthetic_qualification",
    "authorization_or_consent_reference",
    "declared_by",
    "declared_at_utc",
}
HUMAN_INSTRUMENT_FIELDS = {
    "status",
    "receipt_version",
    "instrument_artifact_path",
    "instrument_sha256",
    "readiness_receipt_path",
    "readiness_receipt_sha256",
    "contains_real_source_text",
    "frozen_item_and_guide_semantic_rendering_validated",
    "active_timer_rule_validated",
    "response_storage_and_hash_capture_validated",
    "consent_and_authorization_flow_validated",
    "private_condition_and_other_rating_blinding_validated",
    "validated_by",
    "validated_at_utc",
}
PROVIDER_COMMON_FIELDS = {
    "status",
    "actor_id",
    "provider",
    "surface",
    "model_id",
    "model_snapshot",
    "account_or_project_reference",
    "processing_profile_reference",
    "processing_terms_version",
    "retention_and_deletion_profile",
    "training_use_profile",
    "human_access_or_abuse_monitoring_profile",
    "processing_region_or_routing_profile",
    "synthetic_processing_authorized_for_account",
    "provider_returned_model_version_capture_enabled",
    "wire_adapter_artifact_path",
    "wire_adapter_sha256",
    "request_contract_artifact_path",
    "request_contract_sha256",
    "wire_adapter_validated",
    "transport_schema_compilation_smoke_test_passed",
    "transport_schema_compilation_test_reference",
    "transport_schema_compilation_tested_at_utc",
    "shared_rating_post_validation_enabled",
    "tools_and_external_context_disabled",
    "confirmed_by",
    "confirmed_at_utc",
}
GOOGLE_EXTRA_FIELDS = {
    "execution_deadline_utc",
    "planned_completion_at_utc",
    "runner_enforces_completion_and_lock_deadline",
    "deadline_enforcement_test_reference",
    "silent_model_replacement_forbidden",
}
CAPTURE_FIELDS = {
    "status",
    "restricted_storage_reference",
    "access_control_reference",
    "capture_test_reference",
    "capture_test_passed",
    "raw_request_bytes_captured_before_send",
    "raw_response_bytes_captured_before_parse",
    "immutable_write_once_or_append_only_storage",
    "sha256_for_every_raw_artifact",
    "request_and_response_ids_captured",
    "provider_returned_model_version_captured",
    "attempt_finish_and_filter_status_captured",
    "input_output_and_reasoning_usage_captured",
    "request_start_and_response_end_timestamps_captured",
    "latency_captured",
    "cost_and_currency_captured",
    "pricing_snapshot_identifier_captured",
    "raw_artifacts_excluded_from_other_evaluator_contexts",
}
BUDGET_FIELDS = {
    "status",
    "approved",
    "currency",
    "total_maximum_amount",
    "anthropic_maximum_amount",
    "google_maximum_amount",
    "approval_reference",
    "approved_by",
    "approved_at_utc",
    "valid_through_utc",
}
CREDENTIAL_FIELDS = {
    "status",
    "values_stored_in_record",
    "values_logged",
    "runner_uses_environment_only",
    "anthropic_api_key_env",
    "google_api_key_env",
    "environment_references_confirmed_present",
    "checked_by",
    "checked_at_utc",
}
ATTESTATION_FIELDS = {
    "status",
    "all_prerequisites_reviewed",
    "direction_j_validator_passed",
    "validator_run_reference",
    "validator_run_at_utc",
    "no_real_text_read_or_processed",
    "no_model_calls_made_during_readiness_preparation",
    "calls_may_begin_only_after_checker_passes",
    "approved_by",
    "approved_at_utc",
}


class ReadinessError(RuntimeError):
    """Raised when a synthetic execution prerequisite is absent or inconsistent."""


def fail(message: str) -> None:
    raise ReadinessError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    actual = set(value)
    require(actual == fields, f"{label} fields differ; missing={sorted(fields-actual)}; unknown={sorted(actual-fields)}")
    return value


def nonblank(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonblank string")
    return value


def sha256_value(value: Any, label: str) -> str:
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{label} must be a lowercase SHA-256 digest")
    return value


def parse_time(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} must be an RFC-3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ReadinessError(f"{label} is not a valid RFC-3339 timestamp") from error
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def reject_symlinks(path: Path) -> None:
    absolute = lexical_absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            fail(f"symlinked readiness input is forbidden: {current}")


def read_regular_once(path: Path, label: str) -> bytes:
    absolute = lexical_absolute(path)
    reject_symlinks(absolute)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(absolute, flags)
    except OSError as error:
        raise ReadinessError(f"cannot open {label}: {absolute}: {error}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not a regular file: {absolute}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    require(before_identity == after_identity, f"{label} changed while being read")
    data = b"".join(chunks)
    require(len(data) == before.st_size, f"{label} size changed while being read")
    return data


def parse_json(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReadinessError(f"{label} is not valid UTF-8 JSON: {error}") from error


def project_relative_path(relative: str, label: str) -> Path:
    relative = nonblank(relative, label)
    candidate = Path(relative)
    require(not candidate.is_absolute() and ".." not in candidate.parts, f"{label} must be a project-relative path without '..'")
    forbidden = {"dataset", "datasets"}
    require(not any(part.casefold() in forbidden for part in candidate.parts), f"{label} contains a forbidden dataset component")
    require(relative != "app/feedback-collector-demo/lib/study-data.ts", f"{label} points to the protected Warrant Study item bank")
    absolute = lexical_absolute(PROJECT_ROOT / candidate)
    try:
        absolute.relative_to(lexical_absolute(PROJECT_ROOT))
    except ValueError as error:
        raise ReadinessError(f"{label} escapes the project root") from error
    return absolute


def read_project_file(relative: str, label: str) -> bytes:
    return read_regular_once(project_relative_path(relative, label), label)


def relative(path: Path) -> str:
    return lexical_absolute(path).relative_to(lexical_absolute(PROJECT_ROOT)).as_posix()


def walk_object_fields(value: Any) -> list[tuple[str, Any]]:
    fields: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            fields.append((key, child))
            fields.extend(walk_object_fields(child))
    elif isinstance(value, list):
        for child in value:
            fields.extend(walk_object_fields(child))
    return fields


def validate_request_packet_bank(
    data: bytes,
) -> dict[str, Any]:
    """Validate the provider-neutral bank without constructing a wire request."""

    require(not data.startswith(b"\xef\xbb\xbf"), "request packet bank contains a UTF-8 BOM")
    require(b"\r" not in data, "request packet bank contains noncanonical CR bytes")
    require(bool(data) and data.endswith(b"\n"), "request packet bank must be nonempty and end in LF")
    observed_sha256 = digest(data)

    packet_ids: set[str] = set()
    observed_routes: set[tuple[str, int, int]] = set()
    previous_route: tuple[str, int, int] | None = None
    lines = data.splitlines(keepends=True)
    require(
        len(lines) == EXPECTED_REQUEST_PACKET_COUNT,
        f"request packet bank must contain exactly {EXPECTED_REQUEST_PACKET_COUNT} records",
    )
    for line_number, line in enumerate(lines, 1):
        label = f"request_packets line {line_number}"
        require(line != b"\n" and line.endswith(b"\n"), f"{label} is blank or lacks LF")
        packet = parse_json(line[:-1], label)
        packet = exact_object(packet, REQUEST_PACKET_FIELDS, label)
        require(canonical_bytes(packet) == line, f"{label} is not canonical JSONL")
        require(packet["request_packet_version"] == "direction-j-provider-neutral-request-v1", f"{label} version changed")
        require(packet["study_id"] == "direction-j-v1" and packet["run_id"] == RUN_ID, f"{label} study/run changed")
        require(packet["qualification_scope"] == "synthetic_only", f"{label} is not synthetic-only")
        require(packet["contains_real_source_text"] is False, f"{label} permits real source text")
        require(packet["evaluation_role"] == "synthetic_qualification", f"{label} is not qualification-only")
        require(packet["actor_kind"] == "llm", f"{label} is not an LLM request packet")
        actor = packet["actor_id"]
        require(actor in {"J_PRIMARY", "J_SENS_GEMINI"}, f"{label} has an unexpected actor")
        repetition = packet["rating_repetition"]
        sequence = packet["sequence"]
        require(isinstance(repetition, int) and not isinstance(repetition, bool), f"{label} repetition is invalid")
        require(isinstance(sequence, int) and not isinstance(sequence, bool), f"{label} sequence is invalid")
        route = (actor, repetition, sequence)
        require(previous_route is None or previous_route < route, f"{label} is out of order or duplicated")
        previous_route = route
        observed_routes.add(route)

        request_packet_id = nonblank(packet["request_packet_id"], f"{label}.request_packet_id")
        require(request_packet_id not in packet_ids, f"{label} duplicates a request-packet ID")
        packet_ids.add(request_packet_id)
        for field in (
            "item_payload_sha256",
            "semantic_input_sha256",
            "shared_rater_guide_sha256",
            "prompt_source_sha256",
            "rendered_messages_sha256",
            "response_schema_sha256",
            "post_validation_schema_sha256",
            "frozen_model_settings_sha256",
            "frozen_prompting_policy_sha256",
        ):
            sha256_value(packet[field], f"{label}.{field}")
        messages = exact_object(packet["messages"], {"system", "developer", "user"}, f"{label}.messages")
        message_hashes = exact_object(packet["message_sha256"], {"system", "developer", "user"}, f"{label}.message_sha256")
        for message_name in ("system", "developer", "user"):
            message = nonblank(messages[message_name], f"{label}.messages.{message_name}")
            require(
                digest(message.encode("utf-8"))
                == sha256_value(message_hashes[message_name], f"{label}.message_sha256.{message_name}"),
                f"{label} {message_name} message hash differs",
            )
        require(
            digest(canonical_bytes(messages)) == packet["rendered_messages_sha256"],
            f"{label} rendered-message hash differs",
        )
        require(
            digest(canonical_bytes(packet["response_schema"])) == packet["response_schema_sha256"],
            f"{label} response-schema hash differs",
        )
        require(packet["post_validation_required"] is True, f"{label} disables full post-validation")
        require(
            packet["structured_decoding_replaces_post_validation"] is False,
            f"{label} lets structured decoding replace full post-validation",
        )
        require(packet["wire_adapter_status"] == REQUEST_PACKET_WIRE_STATUS, f"{label} wire status changed")
        wire = exact_object(
            packet["provider_wire_adapter"],
            PROVIDER_NEUTRAL_WIRE_FIELDS,
            f"{label}.provider_wire_adapter",
        )
        require(wire["wire_adapter_status"] == REQUEST_PACKET_WIRE_STATUS, f"{label} nested wire status changed")
        require(wire["provider_wire_request"] is None, f"{label} contains a provider wire request")
        require(wire["provider_wire_request_rendered"] is False, f"{label} renders a provider wire request")
        require(wire["network_dispatch_authorized"] is False, f"{label} authorizes network dispatch")
        require(wire["credential_access_authorized"] is False, f"{label} authorizes credential access")
        for key, child in walk_object_fields(packet):
            if key == "contains_real_source_text":
                require(child is False, f"{label} contains a nested real-text assertion")
            elif key == "provider_wire_request":
                require(child is None, f"{label} contains a nested provider wire request")
            elif key in {
                "provider_wire_request_rendered",
                "network_dispatch_authorized",
                "credential_access_authorized",
            }:
                require(child is False, f"{label} contains nested wire/network authorization")

    expected_routes = {
        *(('J_PRIMARY', repetition, sequence) for repetition in (1, 2, 3) for sequence in range(1, 25)),
        *(('J_SENS_GEMINI', 1, sequence) for sequence in range(1, 25)),
    }
    require(observed_routes == expected_routes, "request packet actor/repetition/sequence routes differ")
    return {
        "sha256": observed_sha256,
        "count": len(lines),
        "wire_status": REQUEST_PACKET_WIRE_STATUS,
    }


def reconstruct_request_packet_bank(renderer_bytes: bytes) -> bytes:
    """Execute the already freeze-pinned renderer bytes without reopening them."""

    namespace: dict[str, Any] = {
        "__file__": os.fspath(REQUEST_PACKET_RENDERER_PATH),
        "__name__": "direction_j_readiness_pinned_renderer",
        "__package__": None,
    }
    try:
        code = compile(
            renderer_bytes,
            os.fspath(REQUEST_PACKET_RENDERER_PATH),
            "exec",
            dont_inherit=True,
        )
        exec(code, namespace)
        load_sources = namespace.get("load_and_validate_sources")
        render_packets = namespace.get("render_packets")
        require(callable(load_sources), "pinned request renderer lacks load_and_validate_sources")
        require(callable(render_packets), "pinned request renderer lacks render_packets")
        bundle = load_sources()
        packets, rendered = render_packets(bundle)
    except ReadinessError:
        raise
    except Exception as error:
        raise ReadinessError(
            f"pinned request renderer could not reconstruct the packet bank: {error}"
        ) from error
    require(isinstance(packets, list), "pinned request renderer returned a non-list packet collection")
    require(isinstance(rendered, bytes), "pinned request renderer returned non-byte JSONL")
    require(len(packets) == EXPECTED_REQUEST_PACKET_COUNT, "pinned request renderer returned the wrong packet count")
    return rendered


def verify_empty_pre_execution_state() -> None:
    for directory_name in ("ratings", "raw_model_responses"):
        directory = RUN_ROOT / directory_name
        require(directory.is_dir(), f"missing pre-execution directory: {directory}")
        payloads = [path for path in directory.iterdir() if path.name != "README.md"]
        require(not payloads, f"{directory_name} already contains execution payloads")
    result_like = [
        path
        for path in RUN_ROOT.iterdir()
        if "result" in path.name.casefold() or "outcome" in path.name.casefold()
    ]
    require(not result_like, "prepared run already contains a result/outcome artifact")


def current_lineage() -> tuple[dict[str, Any], dict[str, Any]]:
    """Reconcile the live fictional run and return exact record values."""

    freeze_bytes = read_regular_once(FREEZE_PATH, "Direction J freeze")
    manifest_bytes = read_regular_once(RUN_MANIFEST_PATH, "prepared run manifest")
    build_bytes = read_regular_once(BUILD_REPORT_PATH, "synthetic build report")
    evaluator_bytes = read_regular_once(EVALUATOR_ITEMS_PATH, "frozen evaluator bank")
    guide_bytes = read_regular_once(GUIDE_PATH, "shared rater guide")
    prompt_bytes = read_regular_once(PROMPT_PATH, "LLM judge prompt")
    rating_schema_bytes = read_regular_once(RATING_SCHEMA_PATH, "shared rating schema")
    governance_bytes = read_regular_once(GOVERNANCE_PATH, "governance gate template")
    request_renderer_bytes = read_regular_once(
        REQUEST_PACKET_RENDERER_PATH,
        "provider-neutral request renderer",
    )
    request_contract_bytes = read_regular_once(
        REQUEST_RENDERING_CONTRACT_PATH,
        "provider-neutral request-rendering contract",
    )
    request_packets_bytes = read_regular_once(
        REQUEST_PACKETS_PATH,
        "provider-neutral request packet bank",
    )
    freeze = parse_json(freeze_bytes, "Direction J freeze")
    manifest = parse_json(manifest_bytes, "prepared run manifest")
    build = parse_json(build_bytes, "synthetic build report")
    gate = parse_json(governance_bytes, "governance gate template")

    scope = freeze.get("scope", {})
    require(scope.get("runnable_lane") == "synthetic_qualification_only", "freeze is not synthetic-only")
    require(scope.get("contains_real_source_text") is False, "freeze permits real source text")
    require(scope.get("real_text_execution") == "blocked", "freeze real-text lane is not blocked")
    require(scope.get("confirmatory_inference_allowed") is False, "freeze permits confirmatory inference")

    require(manifest.get("run_id") == RUN_ID, "prepared run ID changed")
    require(manifest.get("status") == "prepared_not_run", "run is no longer pre-execution")
    require(manifest.get("qualification_scope") == "synthetic_only", "run manifest is not synthetic-only")
    require(manifest.get("contains_real_source_text") is False, "run manifest claims real text")
    require(manifest.get("independently_authored_fictional_text") is True, "run manifest lacks fictional provenance")
    require(manifest.get("ratings_collected") == 0, "run manifest already claims ratings")
    require(manifest.get("outcomes_available") is False, "run manifest already claims outcomes")
    require(manifest.get("result_label") == "synthetic_qualification_only", "run result label changed")
    require(manifest.get("freeze_sha256") == digest(freeze_bytes), "run/freeze hash lineage differs")
    require(manifest.get("build_report_sha256") == digest(build_bytes), "run/build hash lineage differs")
    require(manifest.get("evaluator_items_sha256") == digest(evaluator_bytes), "run/evaluator-bank hash lineage differs")
    require(manifest.get("shared_rater_guide_sha256") == digest(guide_bytes), "run/guide hash lineage differs")
    require(build.get("input_hashes", {}).get("direction_j_freeze") == digest(freeze_bytes), "build/freeze hash lineage differs")
    require(build.get("output_hashes", {}).get("evaluator_items.jsonl") == digest(evaluator_bytes), "build/evaluator-bank hash lineage differs")

    receipt = build.get("source_receipt")
    require(isinstance(receipt, dict), "build report lacks a source receipt")
    receipt_sha256 = digest(canonical_bytes(receipt))
    require(build.get("source_receipt_sha256") == receipt_sha256, "source receipt hash differs from its contents")
    require(manifest.get("source_receipt_sha256") == receipt_sha256, "run/source-receipt lineage differs")
    require(receipt.get("independently_authored_fictional_text") is True, "source receipt lacks fictional authorship")
    require(receipt.get("contains_real_source_text") is False, "source receipt permits real text")
    require(receipt.get("synthetic_benchmark_sha256") == EXPECTED_BENCHMARK_SHA256, "synthetic benchmark hash changed")
    bundle_hashes = receipt.get("blinded_bundle_sha256")
    require(isinstance(bundle_hashes, dict) and len(bundle_hashes) == 12, "source receipt does not pin exactly 12 bundles")
    frozen_sources = freeze.get("source_evidence", {})
    require(bundle_hashes == frozen_sources.get("blinded_bundle_sha256"), "receipt/freeze bundle hashes differ")
    require(receipt.get("blinded_bundle_fileset_sha256") == frozen_sources.get("blinded_bundle_fileset_sha256"), "receipt/freeze bundle fileset differs")

    benchmark_record = frozen_sources.get("synthetic_benchmark", {})
    require(benchmark_record.get("sha256") == EXPECTED_BENCHMARK_SHA256, "freeze benchmark hash changed")
    benchmark_bytes = read_project_file(benchmark_record.get("path"), "frozen synthetic benchmark")
    require(digest(benchmark_bytes) == EXPECTED_BENCHMARK_SHA256, "frozen synthetic benchmark bytes changed")
    benchmark = parse_json(benchmark_bytes, "frozen synthetic benchmark")
    require(benchmark.get("provenance") == benchmark_record.get("provenance"), "benchmark provenance differs from freeze")
    for key in ("legacy_run_manifest", "legacy_private_blind_map", "legacy_judge_inventory"):
        source = frozen_sources.get(key, {})
        source_bytes = read_project_file(source.get("path"), f"frozen source evidence {key}")
        require(digest(source_bytes) == source.get("sha256"), f"frozen source evidence hash changed: {key}")
    actual_bundle_names = {path.name for path in BUNDLE_ROOT.glob("*.json")}
    require(actual_bundle_names == set(bundle_hashes), "blinded bundle file set changed")
    observed_bundle_hashes = {
        name: digest(read_regular_once(BUNDLE_ROOT / name, f"blinded bundle {name}"))
        for name in sorted(bundle_hashes)
    }
    require(observed_bundle_hashes == bundle_hashes, "a blinded bundle hash changed")
    require(digest(canonical_bytes(observed_bundle_hashes)) == receipt.get("blinded_bundle_fileset_sha256"), "blinded bundle fileset receipt changed")

    builder = freeze.get("item_selection", {})
    builder_bytes = read_project_file(builder.get("builder_path"), "frozen synthetic builder")
    require(digest(builder_bytes) == builder.get("builder_sha256"), "frozen builder hash changed")
    frozen_files = freeze.get("shared_interface", {}).get("files", {})
    require(frozen_files.get("protocol/shared_rater_guide_v1.md") == digest(guide_bytes), "freeze guide hash changed")
    require(frozen_files.get("protocol/llm_judge_prompt_v1.md") == digest(prompt_bytes), "freeze prompt hash changed")
    require(frozen_files.get("schemas/shared_rating.schema.json") == digest(rating_schema_bytes), "freeze rating-schema hash changed")
    normative_hashes = freeze.get("normative_artifact_sha256", {})
    require(
        normative_hashes.get("scripts/render_request_packets.py")
        == digest(request_renderer_bytes),
        "freeze request-renderer hash changed",
    )
    require(
        normative_hashes.get("protocol/request_rendering_contract.md")
        == digest(request_contract_bytes),
        "freeze request-rendering-contract hash changed",
    )
    execution_preparation = freeze.get("execution_preparation", {})
    require(
        execution_preparation.get("request_packet_version")
        == "direction-j-provider-neutral-request-v1",
        "freeze request-packet version changed",
    )
    require(
        execution_preparation.get("request_renderer")
        == "scripts/render_request_packets.py",
        "freeze request-renderer path changed",
    )
    require(
        execution_preparation.get("request_rendering_contract")
        == "protocol/request_rendering_contract.md",
        "freeze request-rendering-contract path changed",
    )
    require(
        execution_preparation.get("request_packets_path")
        == "runs/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl",
        "freeze request-packet-bank path changed",
    )
    require(
        execution_preparation.get("expected_request_packets")
        == EXPECTED_REQUEST_PACKET_COUNT,
        "freeze request-packet count changed",
    )
    require(
        execution_preparation.get("wire_adapter_status")
        == REQUEST_PACKET_WIRE_STATUS,
        "freeze request-packet wire status changed",
    )
    require(
        execution_preparation.get("provider_wire_request_rendered") is False
        and execution_preparation.get("network_dispatch_authorized") is False,
        "freeze renders or authorizes provider wire activity",
    )

    require(gate.get("record_status") == "template_not_approved", "real-text gate template appears approved")
    require(gate.get("gate_mode") == "synthetic_only", "governance gate is not synthetic-only")
    real_gate = gate.get("real_text_gate", {})
    require(real_gate.get("decision") == "blocked" and real_gate.get("runnable") is False, "real-text gate is open")
    require(real_gate.get("all_requirements_satisfied") is False, "real-text gate claims completion")
    requirements = real_gate.get("requirements", [])
    require(len(requirements) == 10 and all(item.get("status") == "pending" for item in requirements), "real-text requirements are not all pending")
    require(all(lane.get("runnable") is False for lane in gate.get("corpus_lanes", {}).values()), "a real corpus lane is runnable")
    require(gate.get("machine_check", {}).get("allow_operator_override") is False, "governance permits an override")

    reconstructed_packet_bytes = reconstruct_request_packet_bank(request_renderer_bytes)
    require(
        request_packets_bytes == reconstructed_packet_bytes,
        "request packet bank differs byte-for-byte from the pinned deterministic renderer",
    )
    packet_summary = validate_request_packet_bank(request_packets_bytes)

    actual_assignment_names = {path.name for path in ASSIGNMENT_ROOT.glob("*.csv")}
    require(actual_assignment_names == EXPECTED_ASSIGNMENTS, "assignment file set changed")
    assignment_sha256 = {
        name: digest(read_regular_once(ASSIGNMENT_ROOT / name, f"assignment {name}"))
        for name in sorted(EXPECTED_ASSIGNMENTS)
    }
    verify_empty_pre_execution_state()

    expected = {
        "run_id": RUN_ID,
        "run_manifest_path": relative(RUN_MANIFEST_PATH),
        "run_manifest_sha256": digest(manifest_bytes),
        "freeze_path": relative(FREEZE_PATH),
        "freeze_sha256": digest(freeze_bytes),
        "build_report_path": relative(BUILD_REPORT_PATH),
        "build_report_sha256": digest(build_bytes),
        "evaluator_items_path": relative(EVALUATOR_ITEMS_PATH),
        "evaluator_items_sha256": digest(evaluator_bytes),
        "source_receipt_sha256": receipt_sha256,
        "synthetic_benchmark_sha256": EXPECTED_BENCHMARK_SHA256,
        "blinded_bundle_fileset_sha256": receipt["blinded_bundle_fileset_sha256"],
        "shared_rater_guide_sha256": digest(guide_bytes),
        "llm_judge_prompt_sha256": digest(prompt_bytes),
        "shared_rating_schema_sha256": digest(rating_schema_bytes),
        "governance_gate_sha256": digest(governance_bytes),
        "request_packet_renderer_path": relative(REQUEST_PACKET_RENDERER_PATH),
        "request_packet_renderer_sha256": digest(request_renderer_bytes),
        "request_rendering_contract_path": relative(REQUEST_RENDERING_CONTRACT_PATH),
        "request_rendering_contract_sha256": digest(request_contract_bytes),
        "request_packets_path": relative(REQUEST_PACKETS_PATH),
        "request_packets_sha256": packet_summary["sha256"],
        "request_packets_expected_count": packet_summary["count"],
        "request_packets_wire_status": packet_summary["wire_status"],
        "assignment_sha256": assignment_sha256,
    }
    return expected, freeze


def validate_lineage(value: Any, expected: Mapping[str, Any]) -> None:
    lineage = exact_object(value, LINEAGE_FIELDS, "lineage")
    require(lineage["status"] == "confirmed", "lineage.status must be confirmed")
    for field, expected_value in expected.items():
        if field == "assignment_sha256":
            assignments = exact_object(lineage[field], EXPECTED_ASSIGNMENTS, "lineage.assignment_sha256")
            for name, expected_hash in expected_value.items():
                require(sha256_value(assignments[name], f"lineage.assignment_sha256.{name}") == expected_hash, f"assignment hash differs: {name}")
        else:
            require(lineage[field] == expected_value, f"lineage.{field} differs from the live frozen run")
            if field.endswith("_sha256"):
                sha256_value(lineage[field], f"lineage.{field}")


def validate_charlie(value: Any, approved_at: datetime) -> None:
    actor = exact_object(value, CHARLIE_FIELDS, "human_actors.charlie")
    require(actor["status"] == "confirmed", "Charlie status must be confirmed")
    require(actor["actor_id"] == "charlie" and actor["expected_role"] == "first_stage_human_comparator", "Charlie actor/role changed")
    for field in (
        "identity_or_roster_reference",
        "task_role_summary",
        "qualification_summary",
        "qualification_reference",
        "independence_relationship_summary",
        "independence_relationship_reference",
        "authorization_or_consent_reference",
        "declared_by",
    ):
        nonblank(actor[field], f"human_actors.charlie.{field}")
    for field in (
        "role_and_qualification_confirmed",
        "private_condition_blinded_until_lock",
        "other_ratings_blinded_until_lock",
        "authorized_for_synthetic_qualification",
    ):
        require(actor[field] is True, f"human_actors.charlie.{field} must be true")
    relationship = actor["independence_relationship_classification"]
    require(
        relationship in {"independent", "involved"},
        "Charlie independence relationship must be documented as independent or involved",
    )
    expected_primary_eligibility = relationship == "independent"
    expected_separate_reporting = relationship == "involved"
    require(
        actor["primary_independence_analysis_eligible"]
        is expected_primary_eligibility,
        "Charlie primary-independence eligibility is inconsistent with the documented relationship",
    )
    require(
        actor["separate_nonindependent_reporting_required"]
        is expected_separate_reporting,
        "Charlie separate-reporting requirement is inconsistent with the documented relationship",
    )
    require(parse_time(actor["declared_at_utc"], "human_actors.charlie.declared_at_utc") <= approved_at, "Charlie declaration follows approval")


def validate_expert(value: Any, actor_id: str, role: str, approved_at: datetime) -> None:
    label = f"human_actors.{actor_id}"
    actor = exact_object(value, EXPERT_FIELDS, label)
    require(actor["status"] == "confirmed", f"{label}.status must be confirmed")
    require(actor["actor_id"] == actor_id and actor["expected_role"] == role, f"{label} actor/role changed")
    for field in (
        "identity_or_roster_reference",
        "qualification_summary",
        "qualification_reference",
        "authorization_or_consent_reference",
        "declared_by",
    ):
        nonblank(actor[field], f"{label}.{field}")
    for field in (
        "role_and_qualification_confirmed",
        "independent_from_item_construction",
        "independent_from_first_stage_rating",
        "private_condition_blinded_until_lock",
        "other_ratings_blinded_until_lock",
        "eligible_for_locked_individual_expert_rating",
        "authorized_for_synthetic_qualification",
    ):
        require(actor[field] is True, f"{label}.{field} must be true")
    require(parse_time(actor["declared_at_utc"], f"{label}.declared_at_utc") <= approved_at, f"{label} declaration follows approval")


def validate_wire_artifact(path_value: Any, hash_value: Any, label: str) -> None:
    relative_path = nonblank(path_value, f"{label}.path")
    require(relative_path.startswith("experiments/direction_j_llm_as_rater/"), f"{label}.path must remain under Direction J")
    require("/runs/" not in f"/{relative_path}", f"{label}.path cannot point into a run directory")
    data = read_project_file(relative_path, f"{label} artifact")
    require(digest(data) == sha256_value(hash_value, f"{label}.sha256"), f"{label} artifact hash differs")


def validate_human_instrument(value: Any, approved_at: datetime) -> None:
    instrument = exact_object(value, HUMAN_INSTRUMENT_FIELDS, "human_instrument")
    require(instrument["status"] == "confirmed", "human_instrument.status must be confirmed")
    require(
        instrument["receipt_version"] == "direction-j-human-instrument-readiness-v1",
        "human_instrument.receipt_version changed",
    )
    instrument_path = nonblank(
        instrument["instrument_artifact_path"],
        "human_instrument.instrument_artifact_path",
    )
    receipt_path = nonblank(
        instrument["readiness_receipt_path"],
        "human_instrument.readiness_receipt_path",
    )
    require(instrument_path != receipt_path, "human instrument and readiness receipt must be distinct artifacts")
    instrument_bytes = read_project_file(instrument_path, "human instrument artifact")
    receipt_bytes = read_project_file(receipt_path, "human instrument readiness receipt")
    require(
        digest(instrument_bytes)
        == sha256_value(instrument["instrument_sha256"], "human_instrument.instrument_sha256"),
        "human instrument artifact hash differs",
    )
    require(
        digest(receipt_bytes)
        == sha256_value(
            instrument["readiness_receipt_sha256"],
            "human_instrument.readiness_receipt_sha256",
        ),
        "human instrument readiness receipt hash differs",
    )
    require(
        instrument["contains_real_source_text"] is False,
        "human instrument readiness receipt cannot contain/authorize real source text",
    )
    for field in (
        "frozen_item_and_guide_semantic_rendering_validated",
        "active_timer_rule_validated",
        "response_storage_and_hash_capture_validated",
        "consent_and_authorization_flow_validated",
        "private_condition_and_other_rating_blinding_validated",
    ):
        require(instrument[field] is True, f"human_instrument.{field} must be true")
    nonblank(instrument["validated_by"], "human_instrument.validated_by")
    require(
        parse_time(instrument["validated_at_utc"], "human_instrument.validated_at_utc")
        <= approved_at,
        "human instrument validation follows readiness approval",
    )


def validate_provider(
    value: Any,
    label: str,
    expected: Mapping[str, str],
    approved_at: datetime,
    now: datetime,
    google: bool,
) -> datetime | None:
    fields = PROVIDER_COMMON_FIELDS | (GOOGLE_EXTRA_FIELDS if google else set())
    profile = exact_object(value, fields, f"provider_profiles.{label}")
    require(profile["status"] == "confirmed", f"provider_profiles.{label}.status must be confirmed")
    for field, expected_value in expected.items():
        require(profile[field] == expected_value, f"provider_profiles.{label}.{field} differs from the freeze")
    for field in (
        "account_or_project_reference",
        "processing_profile_reference",
        "processing_terms_version",
        "retention_and_deletion_profile",
        "training_use_profile",
        "human_access_or_abuse_monitoring_profile",
        "processing_region_or_routing_profile",
        "transport_schema_compilation_test_reference",
        "confirmed_by",
    ):
        nonblank(profile[field], f"provider_profiles.{label}.{field}")
    for field in (
        "synthetic_processing_authorized_for_account",
        "provider_returned_model_version_capture_enabled",
        "wire_adapter_validated",
        "transport_schema_compilation_smoke_test_passed",
        "shared_rating_post_validation_enabled",
        "tools_and_external_context_disabled",
    ):
        require(profile[field] is True, f"provider_profiles.{label}.{field} must be true")
    validate_wire_artifact(profile["wire_adapter_artifact_path"], profile["wire_adapter_sha256"], f"provider_profiles.{label}.wire_adapter")
    validate_wire_artifact(profile["request_contract_artifact_path"], profile["request_contract_sha256"], f"provider_profiles.{label}.request_contract")
    require(profile["wire_adapter_artifact_path"] != profile["request_contract_artifact_path"], f"provider_profiles.{label} adapter and request contract must be distinct artifacts")
    smoke_at = parse_time(profile["transport_schema_compilation_tested_at_utc"], f"provider_profiles.{label}.transport_schema_compilation_tested_at_utc")
    confirmed_at = parse_time(profile["confirmed_at_utc"], f"provider_profiles.{label}.confirmed_at_utc")
    require(smoke_at <= confirmed_at <= approved_at, f"provider_profiles.{label} confirmation chronology is invalid")
    if not google:
        return None
    deadline = parse_time(profile["execution_deadline_utc"], f"provider_profiles.{label}.execution_deadline_utc")
    require(deadline == GEMINI_DEADLINE, "Gemini deadline must be 2026-10-16T00:00:00Z")
    planned = parse_time(profile["planned_completion_at_utc"], f"provider_profiles.{label}.planned_completion_at_utc")
    require(now < planned < deadline, "Gemini completion must be planned after this check and before 2026-10-16")
    require(now < deadline, "Gemini execution deadline has passed")
    require(
        profile["runner_enforces_completion_and_lock_deadline"] is True,
        "Gemini runner must enforce completion and lock before 2026-10-16",
    )
    nonblank(
        profile["deadline_enforcement_test_reference"],
        f"provider_profiles.{label}.deadline_enforcement_test_reference",
    )
    require(profile["silent_model_replacement_forbidden"] is True, "silent Gemini replacement must be forbidden")
    return planned


def validate_capture(value: Any) -> None:
    capture = exact_object(value, CAPTURE_FIELDS, "capture_controls")
    require(capture["status"] == "confirmed", "capture_controls.status must be confirmed")
    for field in ("restricted_storage_reference", "access_control_reference", "capture_test_reference"):
        nonblank(capture[field], f"capture_controls.{field}")
    for field in CAPTURE_FIELDS - {"status", "restricted_storage_reference", "access_control_reference", "capture_test_reference"}:
        require(capture[field] is True, f"capture_controls.{field} must be true")


def positive_amount(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0, f"{label} must be a positive number")
    return float(value)


def validate_budget(value: Any, approved_at: datetime, planned_gemini: datetime, now: datetime) -> None:
    budget = exact_object(value, BUDGET_FIELDS, "budget")
    require(budget["status"] == "confirmed" and budget["approved"] is True, "budget must be confirmed and approved")
    require(isinstance(budget["currency"], str) and CURRENCY_RE.fullmatch(budget["currency"]) is not None, "budget.currency must be a three-letter code")
    total = positive_amount(budget["total_maximum_amount"], "budget.total_maximum_amount")
    anthropic = positive_amount(budget["anthropic_maximum_amount"], "budget.anthropic_maximum_amount")
    google = positive_amount(budget["google_maximum_amount"], "budget.google_maximum_amount")
    require(anthropic + google <= total, "provider budget maxima exceed the approved total")
    for field in ("approval_reference", "approved_by"):
        nonblank(budget[field], f"budget.{field}")
    budget_at = parse_time(budget["approved_at_utc"], "budget.approved_at_utc")
    valid_through = parse_time(budget["valid_through_utc"], "budget.valid_through_utc")
    require(budget_at <= approved_at, "budget approval follows readiness approval")
    require(valid_through > planned_gemini and valid_through > now, "budget expires before planned Gemini completion")


def walk_strings(value: Any, path: str = "record") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        result: list[tuple[str, str]] = []
        for key, child in value.items():
            result.extend(walk_strings(child, f"{path}.{key}"))
        return result
    if isinstance(value, list):
        result = []
        for index, child in enumerate(value):
            result.extend(walk_strings(child, f"{path}[{index}]"))
        return result
    return []


def validate_credentials(
    value: Any,
    record: Mapping[str, Any],
    approved_at: datetime,
    environment: Mapping[str, str],
) -> None:
    credentials = exact_object(value, CREDENTIAL_FIELDS, "credentials")
    require(credentials["status"] == "confirmed", "credentials.status must be confirmed")
    require(credentials["values_stored_in_record"] is False, "credential values must not be stored in the record")
    require(credentials["values_logged"] is False, "credential values must not be logged")
    require(credentials["runner_uses_environment_only"] is True, "runner must use environment-only credentials")
    require(credentials["environment_references_confirmed_present"] is True, "environment credential presence is not confirmed")
    names = [credentials["anthropic_api_key_env"], credentials["google_api_key_env"]]
    for field, name in zip(("anthropic_api_key_env", "google_api_key_env"), names):
        require(isinstance(name, str) and ENV_RE.fullmatch(name) is not None, f"credentials.{field} must be an environment-variable name, never a value")
        secret = environment.get(name)
        require(isinstance(secret, str) and len(secret) >= 8, f"credential environment reference is absent or unusable: {name}")
    require(names[0] != names[1], "Anthropic and Google credential references must differ")
    nonblank(credentials["checked_by"], "credentials.checked_by")
    require(parse_time(credentials["checked_at_utc"], "credentials.checked_at_utc") <= approved_at, "credential check follows readiness approval")
    excluded_paths = {
        "record.credentials.anthropic_api_key_env",
        "record.credentials.google_api_key_env",
    }
    strings = [(path, text) for path, text in walk_strings(record) if path not in excluded_paths]
    for name in names:
        secret = environment[name]
        require(not any(secret in text for _path, text in strings), f"credential value for {name} appears inside the readiness record")


def validate_attestation(value: Any, approved_by: str, approved_at: datetime) -> None:
    attestation = exact_object(value, ATTESTATION_FIELDS, "final_attestation")
    require(attestation["status"] == "confirmed", "final_attestation.status must be confirmed")
    for field in (
        "all_prerequisites_reviewed",
        "direction_j_validator_passed",
        "no_real_text_read_or_processed",
        "no_model_calls_made_during_readiness_preparation",
        "calls_may_begin_only_after_checker_passes",
    ):
        require(attestation[field] is True, f"final_attestation.{field} must be true")
    nonblank(attestation["validator_run_reference"], "final_attestation.validator_run_reference")
    require(parse_time(attestation["validator_run_at_utc"], "final_attestation.validator_run_at_utc") <= approved_at, "validator run follows readiness approval")
    require(attestation["approved_by"] == approved_by, "final attestation approver differs from record approver")
    require(parse_time(attestation["approved_at_utc"], "final_attestation.approved_at_utc") == approved_at, "final attestation approval time differs")


def validate_record(
    value: Any,
    *,
    now: datetime | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    environment = environment if environment is not None else os.environ
    record = exact_object(value, TOP_FIELDS, "record")
    require(record["document_type"] == "direction_j_synthetic_execution_readiness", "record.document_type changed")
    require(record["readiness_version"] == VERSION, "record.readiness_version changed")
    require(record["record_status"] == "approved_for_synthetic_execution", "template/incomplete/unknown record status is not executable")
    require(record["template_notice"] == TEMPLATE_NOTICE, "record.template_notice changed")
    nonblank(record["record_id"], "record.record_id")
    prepared_at = parse_time(record["prepared_at_utc"], "record.prepared_at_utc")
    approved_at = parse_time(record["approved_at_utc"], "record.approved_at_utc")
    prepared_by = nonblank(record["prepared_by"], "record.prepared_by")
    approved_by = nonblank(record["approved_by"], "record.approved_by")
    require(prepared_at <= approved_at <= now + timedelta(minutes=5), "record preparation/approval chronology is invalid")
    require(prepared_by != "template" and approved_by != "template", "template is not an approval authority")

    scope = exact_object(record["authorization_scope"], SCOPE_FIELDS, "authorization_scope")
    require(scope["execution_lane"] == "synthetic_qualification_only", "only synthetic qualification may execute")
    require(scope["contains_real_source_text"] is False, "execution record contains/permits real text")
    require(scope["real_text_authorized"] is False, "execution readiness cannot authorize real text")
    require(scope["model_calls_authorized"] is True, "model calls are not authorized")
    require(scope["human_rating_authorized"] is True, "human rating is not authorized")

    expected_lineage, freeze = current_lineage()
    validate_lineage(record["lineage"], expected_lineage)
    humans = exact_object(record["human_actors"], {"charlie", "QME_QUAL", "DOMAIN_QUAL"}, "human_actors")
    validate_charlie(humans["charlie"], approved_at)
    validate_expert(humans["QME_QUAL"], "QME_QUAL", "qualitative_methods_expert", approved_at)
    validate_expert(humans["DOMAIN_QUAL"], "DOMAIN_QUAL", "domain_expert", approved_at)
    validate_human_instrument(record["human_instrument"], approved_at)

    profiles = exact_object(record["provider_profiles"], {"anthropic_primary", "google_sensitivity"}, "provider_profiles")
    primary = freeze["judges"]["primary"]
    sensitivity = freeze["judges"]["cross_family_sensitivity"]
    validate_provider(
        profiles["anthropic_primary"],
        "anthropic_primary",
        {field: primary[field] for field in ("actor_id", "provider", "surface", "model_id", "model_snapshot")},
        approved_at,
        now,
        False,
    )
    planned_gemini = validate_provider(
        profiles["google_sensitivity"],
        "google_sensitivity",
        {field: sensitivity[field] for field in ("actor_id", "provider", "surface", "model_id", "model_snapshot")},
        approved_at,
        now,
        True,
    )
    assert planned_gemini is not None
    validate_capture(record["capture_controls"])
    validate_budget(record["budget"], approved_at, planned_gemini, now)
    validate_credentials(record["credentials"], record, approved_at, environment)
    validate_attestation(record["final_attestation"], approved_by, approved_at)
    return {
        "readiness": "passed",
        "execution_lane": "synthetic_qualification_only",
        "run_id": RUN_ID,
        "real_text_authorized": False,
        "credentials_present": True,
        "record_id": record["record_id"],
    }


def self_test_record(now: datetime, environment: dict[str, str]) -> dict[str, Any]:
    template = parse_json(read_regular_once(TEMPLATE_PATH, "execution readiness template"), "execution readiness template")
    record = copy.deepcopy(template)
    prepared = now - timedelta(hours=2)
    approved = now - timedelta(hours=1)
    record.update(
        {
            "record_status": "approved_for_synthetic_execution",
            "record_id": "SELF_TEST_FIXTURE_NOT_AUTHORIZATION",
            "prepared_at_utc": prepared.isoformat(),
            "prepared_by": "self-test fixture preparer",
            "approved_at_utc": approved.isoformat(),
            "approved_by": "self-test fixture approver",
        }
    )
    record["authorization_scope"]["model_calls_authorized"] = True
    record["authorization_scope"]["human_rating_authorized"] = True
    expected_lineage, _freeze = current_lineage()
    record["lineage"].update(expected_lineage)
    record["lineage"]["status"] = "confirmed"
    for actor_id, actor in record["human_actors"].items():
        actor["status"] = "confirmed"
        actor["identity_or_roster_reference"] = f"self-test-only roster {actor_id}"
        actor["qualification_summary"] = f"self-test-only qualification {actor_id}"
        actor["qualification_reference"] = f"self-test-only qualification reference {actor_id}"
        actor["role_and_qualification_confirmed"] = True
        actor["private_condition_blinded_until_lock"] = True
        actor["other_ratings_blinded_until_lock"] = True
        actor["authorized_for_synthetic_qualification"] = True
        actor["authorization_or_consent_reference"] = f"self-test-only authorization {actor_id}"
        actor["declared_by"] = "self-test fixture declarer"
        actor["declared_at_utc"] = prepared.isoformat()
        if actor_id == "charlie":
            actor["task_role_summary"] = "self-test-only first-stage role"
            actor["independence_relationship_classification"] = "involved"
            actor["independence_relationship_summary"] = (
                "self-test-only involved relationship classification"
            )
            actor["independence_relationship_reference"] = (
                "self-test-only relationship evidence"
            )
            actor["primary_independence_analysis_eligible"] = False
            actor["separate_nonindependent_reporting_required"] = True
        else:
            actor["independent_from_item_construction"] = True
            actor["independent_from_first_stage_rating"] = True
            actor["eligible_for_locked_individual_expert_rating"] = True

    human_instrument = record["human_instrument"]
    human_instrument.update(
        {
            "status": "confirmed",
            "instrument_artifact_path": relative(SCRIPT_PATH),
            "instrument_sha256": digest(
                read_regular_once(SCRIPT_PATH, "self-test human instrument fixture")
            ),
            "readiness_receipt_path": relative(TEMPLATE_PATH),
            "readiness_receipt_sha256": digest(
                read_regular_once(TEMPLATE_PATH, "self-test human receipt fixture")
            ),
            "frozen_item_and_guide_semantic_rendering_validated": True,
            "active_timer_rule_validated": True,
            "response_storage_and_hash_capture_validated": True,
            "consent_and_authorization_flow_validated": True,
            "private_condition_and_other_rating_blinding_validated": True,
            "validated_by": "self-test fixture instrument validator",
            "validated_at_utc": prepared.isoformat(),
        }
    )

    adapter_path = relative(SCRIPT_PATH)
    contract_path = relative(RATING_SCHEMA_PATH)
    adapter_hash = digest(read_regular_once(SCRIPT_PATH, "self-test adapter fixture"))
    contract_hash = digest(read_regular_once(RATING_SCHEMA_PATH, "self-test contract fixture"))
    for label, profile in record["provider_profiles"].items():
        profile["status"] = "confirmed"
        for field in (
            "account_or_project_reference",
            "processing_profile_reference",
            "processing_terms_version",
            "retention_and_deletion_profile",
            "training_use_profile",
            "human_access_or_abuse_monitoring_profile",
            "processing_region_or_routing_profile",
            "transport_schema_compilation_test_reference",
        ):
            profile[field] = f"self-test-only {label} {field}"
        profile["synthetic_processing_authorized_for_account"] = True
        profile["provider_returned_model_version_capture_enabled"] = True
        profile["wire_adapter_artifact_path"] = adapter_path
        profile["wire_adapter_sha256"] = adapter_hash
        profile["request_contract_artifact_path"] = contract_path
        profile["request_contract_sha256"] = contract_hash
        profile["wire_adapter_validated"] = True
        profile["transport_schema_compilation_smoke_test_passed"] = True
        profile["transport_schema_compilation_tested_at_utc"] = prepared.isoformat()
        profile["shared_rating_post_validation_enabled"] = True
        profile["tools_and_external_context_disabled"] = True
        profile["confirmed_by"] = "self-test fixture confirmer"
        profile["confirmed_at_utc"] = prepared.isoformat()
    record["provider_profiles"]["google_sensitivity"]["planned_completion_at_utc"] = "2026-09-01T00:00:00Z"
    record["provider_profiles"]["google_sensitivity"][
        "runner_enforces_completion_and_lock_deadline"
    ] = True
    record["provider_profiles"]["google_sensitivity"][
        "deadline_enforcement_test_reference"
    ] = "self-test-only Gemini deadline enforcement test"

    capture = record["capture_controls"]
    capture["status"] = "confirmed"
    capture["restricted_storage_reference"] = "self-test-only restricted storage"
    capture["access_control_reference"] = "self-test-only access control"
    capture["capture_test_reference"] = "self-test-only capture test"
    for field in CAPTURE_FIELDS - {"status", "restricted_storage_reference", "access_control_reference", "capture_test_reference"}:
        capture[field] = True

    budget = record["budget"]
    budget.update(
        {
            "status": "confirmed",
            "approved": True,
            "currency": "USD",
            "total_maximum_amount": 3,
            "anthropic_maximum_amount": 2,
            "google_maximum_amount": 1,
            "approval_reference": "self-test-only budget approval",
            "approved_by": "self-test fixture budget approver",
            "approved_at_utc": prepared.isoformat(),
            "valid_through_utc": "2026-10-15T00:00:00Z",
        }
    )
    environment["DIRECTION_J_SELF_TEST_ANTHROPIC_KEY"] = "fixture-anthropic-secret"
    environment["DIRECTION_J_SELF_TEST_GOOGLE_KEY"] = "fixture-google-secret"
    credentials = record["credentials"]
    credentials.update(
        {
            "status": "confirmed",
            "runner_uses_environment_only": True,
            "anthropic_api_key_env": "DIRECTION_J_SELF_TEST_ANTHROPIC_KEY",
            "google_api_key_env": "DIRECTION_J_SELF_TEST_GOOGLE_KEY",
            "environment_references_confirmed_present": True,
            "checked_by": "self-test fixture credential checker",
            "checked_at_utc": prepared.isoformat(),
        }
    )
    attestation = record["final_attestation"]
    attestation.update(
        {
            "status": "confirmed",
            "all_prerequisites_reviewed": True,
            "direction_j_validator_passed": True,
            "validator_run_reference": "self-test-only validator run",
            "validator_run_at_utc": prepared.isoformat(),
            "no_real_text_read_or_processed": True,
            "no_model_calls_made_during_readiness_preparation": True,
            "approved_by": record["approved_by"],
            "approved_at_utc": record["approved_at_utc"],
        }
    )
    return record


def expect_rejected(record: dict[str, Any], now: datetime, environment: Mapping[str, str], label: str) -> None:
    try:
        validate_record(record, now=now, environment=environment)
    except ReadinessError:
        return
    raise AssertionError(f"self-test mutation was accepted: {label}")


def expect_packet_bank_rejected(data: bytes, label: str) -> None:
    try:
        validate_request_packet_bank(data)
    except ReadinessError:
        return
    raise AssertionError(f"self-test packet-bank mutation was accepted: {label}")


def run_self_test() -> None:
    now = datetime(2026, 8, 25, 20, tzinfo=timezone.utc)
    environment: dict[str, str] = {}
    record = self_test_record(now, environment)
    result = validate_record(record, now=now, environment=environment)
    assert result["readiness"] == "passed"

    mutation = copy.deepcopy(record)
    mutation["record_status"] = "template_incomplete_not_authorizing"
    expect_rejected(mutation, now, environment, "template status")
    mutation = copy.deepcopy(record)
    mutation["unknown_field"] = True
    expect_rejected(mutation, now, environment, "unknown field")
    mutation = copy.deepcopy(record)
    mutation["authorization_scope"]["contains_real_source_text"] = True
    expect_rejected(mutation, now, environment, "real text")
    mutation = copy.deepcopy(record)
    mutation["human_actors"]["QME_QUAL"]["independent_from_item_construction"] = False
    expect_rejected(mutation, now, environment, "false human prerequisite")
    mutation = copy.deepcopy(record)
    mutation["human_actors"]["charlie"]["independence_relationship_classification"] = "unknown"
    expect_rejected(mutation, now, environment, "unknown Charlie relationship")
    mutation = copy.deepcopy(record)
    mutation["human_actors"]["charlie"]["primary_independence_analysis_eligible"] = True
    expect_rejected(mutation, now, environment, "involved Charlie marked independence eligible")
    mutation = copy.deepcopy(record)
    mutation["human_actors"]["charlie"]["separate_nonindependent_reporting_required"] = False
    expect_rejected(mutation, now, environment, "involved Charlie not separately reported")
    mutation = copy.deepcopy(record)
    mutation["human_instrument"]["active_timer_rule_validated"] = False
    expect_rejected(mutation, now, environment, "human instrument timer")
    mutation = copy.deepcopy(record)
    mutation["provider_profiles"]["anthropic_primary"]["status"] = "maybe"
    expect_rejected(mutation, now, environment, "unknown status")
    mutation = copy.deepcopy(record)
    mutation["provider_profiles"]["anthropic_primary"]["wire_adapter_sha256"] = "0" * 64
    expect_rejected(mutation, now, environment, "wire adapter hash")
    mutation = copy.deepcopy(record)
    mutation["lineage"]["request_packets_sha256"] = "0" * 64
    expect_rejected(mutation, now, environment, "request packet lineage hash")
    packet_values = [
        parse_json(line[:-1], f"self-test packet {number}")
        for number, line in enumerate(
            read_regular_once(REQUEST_PACKETS_PATH, "self-test request packet bank").splitlines(
                keepends=True
            ),
            1,
        )
    ]
    packet_values[0]["provider_wire_adapter"]["network_dispatch_authorized"] = True
    expect_packet_bank_rejected(
        b"".join(canonical_bytes(packet) for packet in packet_values),
        "network dispatch authorization",
    )
    mutation = copy.deepcopy(record)
    mutation["provider_profiles"]["google_sensitivity"]["planned_completion_at_utc"] = "2026-10-16T00:00:00Z"
    expect_rejected(mutation, now, environment, "Gemini deadline")
    mutation = copy.deepcopy(record)
    mutation["provider_profiles"]["google_sensitivity"][
        "runner_enforces_completion_and_lock_deadline"
    ] = False
    expect_rejected(mutation, now, environment, "Gemini runner deadline enforcement")
    expect_rejected(copy.deepcopy(record), now, {}, "missing credential environment")
    print(
        json.dumps(
            {
                "self_test": "passed",
                "fixture_is_authorization": False,
                "template_rejected": True,
                "unknown_field_and_status_rejected": True,
                "real_text_rejected": True,
                "false_prerequisite_rejected": True,
                "charlie_relationship_classification_enforced": True,
                "human_instrument_receipt_required": True,
                "wire_hash_mismatch_rejected": True,
                "request_packet_hash_and_wire_mutations_rejected": True,
                "missing_environment_credentials_rejected": True,
                "gemini_deadline_enforced": True,
                "files_written": 0,
            },
            sort_keys=True,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    parser = argparse.ArgumentParser(
        description="Read-only, fail-closed Direction J synthetic execution-readiness check."
    )
    parser.add_argument("--record", type=Path, help="Restricted, completed local readiness record")
    parser.add_argument("--self-test", action="store_true", help="Run in-memory fail-closed regression checks")
    args = parser.parse_args(argv)
    if args.self_test:
        if args.record is not None:
            parser.error("--self-test cannot be combined with --record")
        run_self_test()
        return 0
    if args.record is None:
        parser.error("--record is required unless --self-test is used")
    try:
        record_path = lexical_absolute(args.record)
        if record_path == lexical_absolute(TEMPLATE_PATH):
            fail("the tracked execution-readiness template is never an approval record")
        record = parse_json(read_regular_once(record_path, "execution readiness record"), "execution readiness record")
        result = validate_record(record)
    except ReadinessError as error:
        print(f"execution readiness rejected: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
