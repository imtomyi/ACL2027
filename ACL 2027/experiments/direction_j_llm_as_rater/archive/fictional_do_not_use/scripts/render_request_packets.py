#!/usr/bin/env python3
"""Render or verify frozen, provider-neutral Direction J request packets.

This program is deliberately offline and stdlib-only.  It reads only a fixed
allowlist of public synthetic-qualification artifacts.  The default action is
a dry run; writing requires an explicit ``--write`` path in the frozen run's
``request-packets`` directory.  It never renders a provider wire request.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Iterable, NoReturn


class PacketError(RuntimeError):
    """A fail-closed lineage, scope, or canonicalization error."""


def fail(message: str) -> NoReturn:
    raise PacketError(message)


SCRIPT_PATH = Path(os.path.abspath(__file__))
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
RUN_ID = "20260825_synthetic_paired_qualification_prepared"
RUN_ROOT = DIRECTION_ROOT / "runs" / RUN_ID
REQUEST_PACKETS_DIR = RUN_ROOT / "request-packets"
REQUEST_PACKET_FILENAME = "request_packets_v1.jsonl"

FREEZE_PATH = DIRECTION_ROOT / "config" / "freeze_v1.json"
PROMPT_PATH = DIRECTION_ROOT / "protocol" / "llm_judge_prompt_v1.md"
GUIDE_PATH = DIRECTION_ROOT / "protocol" / "shared_rater_guide_v1.md"
RATING_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "shared_rating.schema.json"
RUN_MANIFEST_PATH = RUN_ROOT / "run_manifest.json"
BUILD_REPORT_PATH = RUN_ROOT / "build_report.json"
ITEM_BANK_PATH = RUN_ROOT / "evaluator_items.jsonl"
ASSIGNMENTS_ROOT = RUN_ROOT / "assignments"

ASSIGNMENT_SPECS = (
    ("J_PRIMARY_rep1.csv", "J_PRIMARY", 1, "primary"),
    ("J_PRIMARY_rep2.csv", "J_PRIMARY", 2, "primary"),
    ("J_PRIMARY_rep3.csv", "J_PRIMARY", 3, "primary"),
    ("J_SENS_GEMINI_rep1.csv", "J_SENS_GEMINI", 1, "cross_family_sensitivity"),
)

READ_ALLOWLIST = frozenset(
    {
        FREEZE_PATH,
        PROMPT_PATH,
        GUIDE_PATH,
        RATING_SCHEMA_PATH,
        RUN_MANIFEST_PATH,
        BUILD_REPORT_PATH,
        ITEM_BANK_PATH,
        *(ASSIGNMENTS_ROOT / name for name, _actor, _rep, _role in ASSIGNMENT_SPECS),
    }
)

INTERFACE_VERSION = "direction-j-shared-interface-v1"
ITEM_SCHEMA_VERSION = "direction-j-evaluator-item-v1"
RATING_SCHEMA_VERSION = "direction-j-shared-rating-v1"
GUIDE_VERSION = "direction-j-rater-guide-v1"
PROMPT_VERSION = "direction-j-judge-prompt-v1"
PACKET_VERSION = "direction-j-provider-neutral-request-v1"
TRANSPORT_SCHEMA_ID = (
    "https://warrantroute.local/schemas/direction-j/"
    "shared-rating-transport-v1.json"
)
WIRE_STATUS = "pending_provider_profile_and_wire_validation"
REPAIR_MESSAGE_VERSION = "direction-j-format-repair-message-v1"
REPAIR_PACKET_VERSION = "direction-j-format-repair-packet-v2"
REPAIR_INSTRUCTION = (
    "The preceding response failed format validation. Using only the exact "
    "invalid response and validator diagnostics below, return one corrected "
    "shared rating JSON object. Do not change the item, use outside information, "
    "or add commentary."
)
REPAIR_ERROR_FIELDS = (
    "instance_path",
    "schema_path",
    "keyword",
    "message",
)
REPAIR_TEST_VECTOR_SHA256 = (
    "f6ed7b374a8b67b7bd22426ba27d670ac066145df10fb74ff05ca8f972cbfbac"
)
GOLDEN_SYSTEM_SHA256 = (
    "cab0c33a18371c39e30c4516020ba71a6ca2efef05af998cc10f0d357520efbf"
)
GOLDEN_DEVELOPER_SHA256 = (
    "348cd32ef88dd175e2a810407adf1bac4028d9ddea114030e5f33c82be41b5bc"
)
GOLDEN_GUIDE_SHA256 = (
    "ab0e8dfb1992927e8b2202353da55eba47f45a691222275c3feab42d53a46b4f"
)
GOLDEN_ITEM_ID = "DJI_182867ba6d054a6e"
GOLDEN_ITEM_SHA256 = (
    "e5cba4ac9484e8773113e16151d040af704d6d6b906eb1e51c7674c2090d029e"
)
GOLDEN_USER_SHA256 = (
    "019d8cb64539ec5d2e8c59dc169aee5b8987fbca5be1aa70ffe8167c1fc58f9d"
)

BEGIN_SYSTEM = b"<!-- BEGIN DIRECTION-J SYSTEM MESSAGE -->"
END_SYSTEM = b"<!-- END DIRECTION-J SYSTEM MESSAGE -->"
BEGIN_DEVELOPER = b"<!-- BEGIN DIRECTION-J DEVELOPER MESSAGE -->"
END_DEVELOPER = b"<!-- END DIRECTION-J DEVELOPER MESSAGE -->"

ASSIGNMENT_FIELDS = (
    "assignment_id",
    "actor_id",
    "actor_kind",
    "rating_repetition",
    "sequence",
    "item_id",
    "item_payload_sha256",
    "interface_version",
    "shared_rater_guide_version",
    "shared_rater_guide_sha256",
    "semantic_input_sha256",
    "packet_id",
    "output_id",
    "corpus_id",
    "evaluation_role",
)

FORBIDDEN_PATH_PARTS = frozenset(
    {
        "dataset",
        "datasets",
        "private",
        "private_maps",
        "blind_maps",
        "raw_model_responses",
        "ratings",
    }
)
FORBIDDEN_ITEM_KEYS = frozenset(
    {
        "condition",
        "candidate_model_id",
        "candidate_provider",
        "candidate_model_family",
        "candidate_condition",
        "base_packet_id",
        "parent_natural_item_sha256",
        "planted_serious_error_flags",
        "planted_error_flags",
        "planted_error_family",
        "baseline_blind_id",
        "baseline_theme_id",
        "truth_scope",
        "private_item_key",
        "answer_guide",
        "reference_answer",
        "adjudication",
        "prior_rating",
        "charlie_feedback",
    }
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def lexical_absolute(path: Path) -> Path:
    """Normalize ``.``/``..`` lexically without following symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


def has_forbidden_part(path: Path) -> bool:
    return any(part.casefold() in FORBIDDEN_PATH_PARTS for part in path.parts)


def reject_symlink_components(path: Path) -> None:
    absolute = lexical_absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            fail(f"symlink/path substitution rejected: {current}")


def assert_static_input(path: Path) -> None:
    path = lexical_absolute(path)
    if path not in {lexical_absolute(candidate) for candidate in READ_ALLOWLIST}:
        fail(f"input is not on the frozen public allowlist: {path}")
    if has_forbidden_part(path.relative_to(PROJECT_ROOT)):
        fail(f"private, dataset, result, or raw-response path rejected: {path}")
    reject_symlink_components(path)


def read_regular_nofollow(path: Path, label: str) -> bytes:
    """Read one immutable regular-file snapshot without following the final link."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot open {label} without following links: {path}: {exc}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail(f"{label} is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity:
        fail(f"{label} changed while being read: {path}")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        fail(f"{label} size changed while being read: {path}")
    return data


def read_static_bytes(path: Path) -> bytes:
    assert_static_input(path)
    return read_regular_nofollow(path, "frozen public input")


def read_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        fail(f"{label} must be BOM-free UTF-8 with LF newlines")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{label} is not valid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def require_sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        fail(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def extract_marked_message(
    raw: bytes, begin_marker: bytes, end_marker: bytes, label: str
) -> bytes:
    """Extract exact bytes after BEGIN LF and before LF END."""

    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        fail("judge prompt must be BOM-free UTF-8 with LF newlines")
    begin = begin_marker + b"\n"
    end = b"\n" + end_marker + b"\n"
    if raw.count(begin_marker) != 1 or raw.count(end_marker) != 1:
        fail(f"judge prompt must contain exactly one {label} marker pair")
    start = raw.find(begin)
    if start < 0:
        fail(f"{label} BEGIN marker is not an exact standalone LF line")
    start += len(begin)
    stop = raw.find(end, start)
    if stop < 0:
        fail(f"{label} END marker is not an exact standalone LF line")
    message = raw[start:stop]
    if not message or begin_marker in message or end_marker in message:
        fail(f"{label} marked message is empty or nested")
    try:
        message.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{label} marked message is not UTF-8: {exc}")
    return message


def find_forbidden_keys(value: Any, location: str = "item") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_ITEM_KEYS:
                findings.append(f"{location}.{key}")
            findings.extend(find_forbidden_keys(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_keys(child, f"{location}[{index}]"))
    return findings


def semantic_input_sha256(item_hash: str, guide_hash: str) -> str:
    return sha256_bytes(
        canonical_bytes(
            {
                "interface_version": INTERFACE_VERSION,
                "item_payload_sha256": item_hash,
                "shared_rater_guide_sha256": guide_hash,
                "shared_rater_guide_version": GUIDE_VERSION,
            }
        )
    )


def parse_item_bank(raw: bytes) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        fail("evaluator bank must be canonical BOM-free UTF-8 JSONL with LF newlines")
    if not raw or not raw.endswith(b"\n"):
        fail("evaluator bank must be nonempty and end with LF")
    objects: dict[str, dict[str, Any]] = {}
    canonical_lines: dict[str, bytes] = {}
    for line_number, line_with_lf in enumerate(raw.splitlines(keepends=True), 1):
        if not line_with_lf.endswith(b"\n") or line_with_lf == b"\n":
            fail(f"evaluator bank line {line_number} is blank or lacks LF")
        try:
            value = json.loads(line_with_lf[:-1].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"evaluator bank line {line_number} is invalid: {exc}")
        if not isinstance(value, dict) or canonical_bytes(value) != line_with_lf:
            fail(f"evaluator bank line {line_number} is not canonical JSONL")
        if value.get("item_schema_version") != ITEM_SCHEMA_VERSION:
            fail(f"evaluator bank line {line_number} has stale item schema version")
        if value.get("corpus_id") != "synthetic_proxy":
            fail(f"evaluator bank line {line_number} is outside synthetic_proxy scope")
        findings = find_forbidden_keys(value)
        if findings:
            fail(f"evaluator item exposes private-map fields: {', '.join(findings)}")
        item_id = value.get("item_id")
        if not isinstance(item_id, str) or not item_id.startswith("DJI_"):
            fail(f"evaluator bank line {line_number} has invalid item_id")
        if item_id in objects:
            fail(f"duplicate evaluator item_id: {item_id}")
        for key, prefix in (("packet_id", "DJP_"), ("output_id", "DJO_")):
            if not isinstance(value.get(key), str) or not value[key].startswith(prefix):
                fail(f"evaluator item {item_id} has invalid {key}")
        objects[item_id] = value
        canonical_lines[item_id] = line_with_lf
    if len(objects) != 24:
        fail(f"frozen evaluator bank must contain 24 items, found {len(objects)}")
    return objects, canonical_lines


def project_transport_schema(full_schema: dict[str, Any]) -> dict[str, Any]:
    """Create the frozen structural decoding projection from the full schema.

    The projection deliberately omits bounds, uniqueness, patterns, conditionals,
    and cross-field semantics.  Those remain mandatory post-validation rules in
    ``full_schema``.
    """

    required = full_schema.get("required")
    properties = full_schema.get("properties")
    expected = [
        "rating_schema_version",
        "evidential_credibility",
        "voice_boundary_preservation",
        "scope_calibration",
        "cannot_judge",
        "confidence",
        "disposition",
        "requested_expertise",
        "serious_error_flags",
        "rationale",
    ]
    if required != expected or not isinstance(properties, dict):
        fail("full shared-rating schema no longer has the frozen ten-field interface")
    if full_schema.get("additionalProperties") is not False:
        fail("full shared-rating schema must prohibit additional properties")

    def enum_of(field: str) -> list[Any]:
        value = properties.get(field, {}).get("enum")
        if not isinstance(value, list) or not value:
            fail(f"full shared-rating schema lacks {field} enum")
        return value

    def item_enum_of(field: str) -> list[Any]:
        value = properties.get(field, {}).get("items", {}).get("enum")
        if not isinstance(value, list) or not value:
            fail(f"full shared-rating schema lacks {field} item enum")
        return value

    version = properties.get("rating_schema_version", {}).get("const")
    if version != RATING_SCHEMA_VERSION:
        fail("full shared-rating schema has stale rating_schema_version")
    for field in (
        "evidential_credibility",
        "voice_boundary_preservation",
        "scope_calibration",
    ):
        if properties.get(field, {}).get("type") != ["integer", "null"]:
            fail(f"full shared-rating schema has unexpected {field} type")
    if properties.get("confidence", {}).get("type") != "integer":
        fail("full shared-rating schema has unexpected confidence type")
    if properties.get("rationale", {}).get("type") != "string":
        fail("full shared-rating schema has unexpected rationale type")
    for field in ("cannot_judge", "serious_error_flags"):
        if properties.get(field, {}).get("type") != "array":
            fail(f"full shared-rating schema has unexpected {field} type")

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": TRANSPORT_SCHEMA_ID,
        "title": "Direction J shared-rating structural transport projection",
        "description": (
            "Provider-neutral structural decoding only; the frozen full shared-rating "
            "schema remains authoritative and MUST be applied after decoding."
        ),
        "type": "object",
        "required": expected,
        "properties": {
            "rating_schema_version": {
                "type": "string",
                "enum": [RATING_SCHEMA_VERSION],
            },
            "evidential_credibility": {"type": ["integer", "null"]},
            "voice_boundary_preservation": {"type": ["integer", "null"]},
            "scope_calibration": {"type": ["integer", "null"]},
            "cannot_judge": {
                "type": "array",
                "items": {"type": "string", "enum": item_enum_of("cannot_judge")},
            },
            "confidence": {"type": "integer"},
            "disposition": {
                "type": "string",
                "enum": enum_of("disposition"),
            },
            "requested_expertise": {
                "type": "string",
                "enum": enum_of("requested_expertise"),
            },
            "serious_error_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": item_enum_of("serious_error_flags"),
                },
            },
            "rationale": {"type": "string"},
        },
        "additionalProperties": False,
    }


def parse_assignment_bytes(
    raw: bytes,
    *,
    label: str,
    expected_actor: str,
    expected_repetition: int,
    items: dict[str, dict[str, Any]],
    item_lines: dict[str, bytes],
    guide_hash: str,
) -> list[dict[str, Any]]:
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(f"{label} must be BOM-free UTF-8 CSV")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{label} is not UTF-8: {exc}")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != ASSIGNMENT_FIELDS:
        fail(f"{label} has a stale or reordered assignment interface")
    rows: list[dict[str, Any]] = []
    seen_assignments: set[str] = set()
    seen_items: set[str] = set()
    seen_sequences: set[int] = set()
    for row_number, row in enumerate(reader, 2):
        if None in row or set(row) != set(ASSIGNMENT_FIELDS):
            fail(f"{label} row {row_number} has extra or missing columns")
        if row["actor_kind"] != "llm":
            fail(f"{label} row {row_number} is a human/non-LLM assignment")
        if row["actor_id"] != expected_actor:
            fail(f"{label} row {row_number} has unexpected actor_id")
        try:
            repetition = int(row["rating_repetition"])
            sequence = int(row["sequence"])
        except (TypeError, ValueError):
            fail(f"{label} row {row_number} has non-integer repetition/sequence")
        if repetition != expected_repetition or repetition < 1 or sequence < 1:
            fail(f"{label} row {row_number} has stale repetition/sequence")
        item_id = row["item_id"]
        if item_id not in items:
            fail(f"{label} row {row_number} references an unknown frozen item")
        item = items[item_id]
        expected_item_hash = sha256_bytes(item_lines[item_id])
        expected_semantic_hash = semantic_input_sha256(expected_item_hash, guide_hash)
        expected_values = {
            "item_payload_sha256": expected_item_hash,
            "interface_version": INTERFACE_VERSION,
            "shared_rater_guide_version": GUIDE_VERSION,
            "shared_rater_guide_sha256": guide_hash,
            "semantic_input_sha256": expected_semantic_hash,
            "packet_id": item["packet_id"],
            "output_id": item["output_id"],
            "corpus_id": "synthetic_proxy",
            "evaluation_role": "synthetic_qualification",
        }
        for key, expected in expected_values.items():
            if row[key] != expected:
                fail(f"{label} row {row_number} has stale or substituted {key}")
        assignment_id = row["assignment_id"]
        if not isinstance(assignment_id, str) or not assignment_id.startswith("DJA_"):
            fail(f"{label} row {row_number} has invalid assignment_id")
        if assignment_id in seen_assignments:
            fail(f"{label} has duplicate assignment_id {assignment_id}")
        if item_id in seen_items:
            fail(f"{label} assigns frozen item {item_id} more than once")
        if sequence in seen_sequences:
            fail(f"{label} has duplicate sequence {sequence}")
        seen_assignments.add(assignment_id)
        seen_items.add(item_id)
        seen_sequences.add(sequence)
        typed = dict(row)
        typed["rating_repetition"] = repetition
        typed["sequence"] = sequence
        rows.append(typed)
    if len(rows) != len(items) or seen_items != set(items):
        fail(f"{label} must assign every frozen item exactly once")
    if seen_sequences != set(range(1, len(items) + 1)):
        fail(f"{label} sequences must be exactly 1..{len(items)}")
    return sorted(rows, key=lambda row: row["sequence"])


def validate_model_settings(
    settings: Any, actor_id: str, expected_repetitions: int
) -> dict[str, Any]:
    if not isinstance(settings, dict):
        fail(f"freeze lacks model settings for {actor_id}")
    if settings.get("actor_id") != actor_id or settings.get("actor_kind") != "llm":
        fail(f"frozen settings for {actor_id} are not an LLM actor")
    if settings.get("rating_repetitions") != expected_repetitions:
        fail(f"frozen repetition count changed for {actor_id}")
    if settings.get("candidate_family_overlap_for_qualification") is not False:
        fail(f"{actor_id} is not frozen family-disjoint for qualification")
    if settings.get("structured_output") is not True:
        fail(f"{actor_id} is not frozen for structured output")
    for field in (
        "tools_enabled",
        "web_enabled",
        "function_calling_enabled",
        "retrieval_enabled",
        "url_context_enabled",
        "code_execution_enabled",
        "memory_enabled",
    ):
        if settings.get(field) is not False:
            fail(f"{actor_id}.{field} must remain disabled")
    if settings.get("response_count") != 1:
        fail(f"{actor_id} must request exactly one response")
    if settings.get("execution_status") != (
        "pending_provider_profile_budget_and_raw_capture_confirmation"
    ):
        fail(f"{actor_id} execution status changed; refreeze before rendering")
    return settings


def assert_synthetic_scope(
    freeze: dict[str, Any],
    run: dict[str, Any],
    build: dict[str, Any],
    source_receipt: dict[str, Any],
) -> None:
    scope = freeze.get("scope", {})
    if (
        scope.get("runnable_lane") != "synthetic_qualification_only"
        or scope.get("contains_real_source_text") is not False
        or scope.get("real_text_execution") != "blocked"
        or scope.get("confirmatory_inference_allowed") is not False
        or run.get("evaluation_role") != "synthetic_qualification"
        or run.get("qualification_scope") != "synthetic_only"
        or run.get("contains_real_source_text") is not False
        or run.get("independently_authored_fictional_text") is not True
        or build.get("qualification_scope") != "synthetic_only"
        or build.get("contains_real_source_text") is not False
        or source_receipt.get("contains_real_source_text") is not False
        or source_receipt.get("independently_authored_fictional_text") is not True
    ):
        fail("request rendering is restricted to independently authored synthetic text")


def load_and_validate_sources() -> dict[str, Any]:
    """Load the exact frozen public inputs and reject any lineage/scope drift."""

    raw = {path: read_static_bytes(path) for path in READ_ALLOWLIST}
    freeze = read_json_bytes(raw[FREEZE_PATH], "Direction J freeze")
    run = read_json_bytes(raw[RUN_MANIFEST_PATH], "synthetic run manifest")
    build = read_json_bytes(raw[BUILD_REPORT_PATH], "synthetic build report")
    full_schema = read_json_bytes(
        raw[RATING_SCHEMA_PATH], "full shared-rating post-validation schema"
    )

    freeze_hash = sha256_bytes(raw[FREEZE_PATH])
    build_hash = sha256_bytes(raw[BUILD_REPORT_PATH])
    item_bank_hash = sha256_bytes(raw[ITEM_BANK_PATH])
    prompt_hash = sha256_bytes(raw[PROMPT_PATH])
    guide_hash = sha256_bytes(raw[GUIDE_PATH])
    full_schema_hash = sha256_bytes(raw[RATING_SCHEMA_PATH])

    if freeze.get("study_id") != "direction-j-v1":
        fail("freeze has an unexpected study_id")
    if freeze.get("freeze_schema_version") != "direction-j-freeze-v1":
        fail("freeze schema version changed")
    if freeze.get("status") != "synthetic_design_frozen_execution_pending":
        fail("freeze is not in the expected pre-execution state")
    scope = freeze.get("scope", {})
    first_run = freeze.get("first_run", {})
    if (
        first_run.get("run_id") != RUN_ID
        or first_run.get("status") != "prepared_not_executed"
        or first_run.get("expected_items") != 24
        or first_run.get("ratings_collected") != 0
        or first_run.get("empirical_results_available") is not False
        or first_run.get("advance_to_real_data_without_governance_approval") is not False
    ):
        fail("freeze first-run state is stale or no longer pre-execution synthetic-only")

    if (
        run.get("run_id") != RUN_ID
        or run.get("study_id") != "direction-j-v1"
        or run.get("status") != "prepared_not_run"
        or run.get("evaluation_role") != "synthetic_qualification"
        or run.get("qualification_scope") != "synthetic_only"
        or run.get("contains_real_source_text") is not False
        or run.get("independently_authored_fictional_text") is not True
        or run.get("ratings_collected") != 0
        or run.get("outcomes_available") is not False
    ):
        fail("run manifest is not the untouched synthetic pre-execution run")
    if run.get("freeze_path") != "../../config/freeze_v1.json":
        fail("run manifest freeze path was substituted")
    if run.get("freeze_sha256") != freeze_hash:
        fail("run manifest has a stale freeze hash")
    if run.get("build_report_sha256") != build_hash:
        fail("run manifest has a stale build-report hash")
    if run.get("evaluator_items_path") != "evaluator_items.jsonl":
        fail("run manifest evaluator bank path was substituted")
    if run.get("evaluator_items_sha256") != item_bank_hash:
        fail("run manifest has a stale evaluator-bank hash")
    if run.get("assignment_manifest_count") != 7:
        fail("run manifest assignment count changed")
    if run.get("semantic_input_hash_rule") != "canonical_manifest_v1":
        fail("run manifest semantic-input hash rule changed")

    if (
        build.get("status") != "prepared_not_run"
        or build.get("qualification_scope") != "synthetic_only"
        or build.get("contains_real_source_text") is not False
        or build.get("evaluator_items") != 24
        or build.get("selection_uses_legacy_judge_scores") is not False
    ):
        fail("build report is not the frozen synthetic pre-execution build")
    if build.get("input_hashes", {}).get("direction_j_freeze") != freeze_hash:
        fail("build report has a stale freeze hash")
    if build.get("output_hashes", {}).get("evaluator_items.jsonl") != item_bank_hash:
        fail("build report has a stale evaluator-bank hash")
    source_receipt = build.get("source_receipt")
    if not isinstance(source_receipt, dict):
        fail("build report lacks its canonical synthetic source receipt")
    assert_synthetic_scope(freeze, run, build, source_receipt)
    source_receipt_hash = sha256_bytes(canonical_bytes(source_receipt))
    if (
        source_receipt.get("contains_real_source_text") is not False
        or source_receipt.get("independently_authored_fictional_text") is not True
        or build.get("source_receipt_sha256") != source_receipt_hash
        or run.get("source_receipt_sha256") != source_receipt_hash
    ):
        fail("synthetic source receipt is stale or permits real text")

    interface = freeze.get("shared_interface", {})
    files = interface.get("files", {})
    expected_interface = {
        "interface_version": INTERFACE_VERSION,
        "item_schema_version": ITEM_SCHEMA_VERSION,
        "rating_schema_version": RATING_SCHEMA_VERSION,
        "rater_guide_version": GUIDE_VERSION,
        "llm_prompt_version": PROMPT_VERSION,
    }
    for field, expected in expected_interface.items():
        if interface.get(field) != expected:
            fail(f"freeze has stale shared-interface field {field}")
    file_pins = {
        "protocol/llm_judge_prompt_v1.md": prompt_hash,
        "protocol/shared_rater_guide_v1.md": guide_hash,
        "schemas/shared_rating.schema.json": full_schema_hash,
    }
    for relative_path, actual_hash in file_pins.items():
        if files.get(relative_path) != actual_hash:
            fail(f"freeze has stale hash for {relative_path}")
    if (
        run.get("interface_version") != INTERFACE_VERSION
        or run.get("shared_rater_guide_version") != GUIDE_VERSION
        or run.get("shared_rater_guide_sha256") != guide_hash
        or build.get("input_hashes", {}).get("shared_rater_guide") != guide_hash
    ):
        fail("run/build shared-interface lineage is stale")

    guide_bytes = raw[GUIDE_PATH]
    if (
        guide_bytes.startswith(b"\xef\xbb\xbf")
        or b"\r" in guide_bytes
        or not guide_bytes.endswith(b"\n")
    ):
        fail("shared rater guide must be complete BOM-free UTF-8 ending in LF")
    try:
        guide_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"shared rater guide is not UTF-8: {exc}")
    system_bytes = extract_marked_message(
        raw[PROMPT_PATH], BEGIN_SYSTEM, END_SYSTEM, "system"
    )
    developer_bytes = extract_marked_message(
        raw[PROMPT_PATH], BEGIN_DEVELOPER, END_DEVELOPER, "developer"
    )

    items, item_lines = parse_item_bank(raw[ITEM_BANK_PATH])
    golden_hashes = {
        "system": (sha256_bytes(system_bytes), GOLDEN_SYSTEM_SHA256),
        "developer": (sha256_bytes(developer_bytes), GOLDEN_DEVELOPER_SHA256),
        "guide": (guide_hash, GOLDEN_GUIDE_SHA256),
    }
    for label, (actual, expected) in golden_hashes.items():
        if actual != expected:
            fail(f"Bohr golden {label} bytes changed: expected {expected}, got {actual}")
    if GOLDEN_ITEM_ID not in item_lines:
        fail(f"Bohr golden item is missing: {GOLDEN_ITEM_ID}")
    golden_item_hash = sha256_bytes(item_lines[GOLDEN_ITEM_ID])
    if golden_item_hash != GOLDEN_ITEM_SHA256:
        fail("Bohr golden canonical item bytes changed")
    golden_user_hash = sha256_bytes(
        render_user_message(guide_bytes, item_lines[GOLDEN_ITEM_ID])
    )
    if golden_user_hash != GOLDEN_USER_SHA256:
        fail("Bohr golden rendered user bytes changed")
    transport_schema = project_transport_schema(full_schema)
    transport_schema_hash = sha256_bytes(canonical_bytes(transport_schema))

    judges = freeze.get("judges", {})
    model_settings = {
        "J_PRIMARY": validate_model_settings(judges.get("primary"), "J_PRIMARY", 3),
        "J_SENS_GEMINI": validate_model_settings(
            judges.get("cross_family_sensitivity"), "J_SENS_GEMINI", 1
        ),
    }
    prompting = freeze.get("prompting")
    if not isinstance(prompting, dict):
        fail("freeze lacks prompting policy")
    required_prompting = {
        "items_per_call": 1,
        "stateless_requests": True,
        "llm_output_is_shared_rating_only": True,
        "hidden_chain_of_thought_requested": False,
        "answer_guide_visible": False,
        "other_candidate_outputs_visible": False,
        "prior_ratings_visible": False,
        "automatic_transport_retries": 0,
        "format_only_retry_count": 1,
        "substantive_manual_edit_allowed": False,
    }
    for key, expected in required_prompting.items():
        if prompting.get(key) != expected:
            fail(f"frozen prompting policy changed at {key}")

    assignment_receipts = build.get("assignment_files")
    if not isinstance(assignment_receipts, dict) or len(assignment_receipts) != 7:
        fail("build report assignment receipts are incomplete")
    assignments: list[tuple[dict[str, Any], str]] = []
    for filename, actor_id, repetition, role in ASSIGNMENT_SPECS:
        path = ASSIGNMENTS_ROOT / filename
        receipt = assignment_receipts.get(filename)
        assignment_raw = raw[path]
        if not isinstance(receipt, dict):
            fail(f"build report lacks receipt for {filename}")
        if receipt.get("sha256") != sha256_bytes(assignment_raw):
            fail(f"stale assignment hash for {filename}")
        if receipt.get("rows") != "24":
            fail(f"stale assignment row count for {filename}")
        rows = parse_assignment_bytes(
            assignment_raw,
            label=filename,
            expected_actor=actor_id,
            expected_repetition=repetition,
            items=items,
            item_lines=item_lines,
            guide_hash=guide_hash,
        )
        if model_settings[actor_id].get("judge_role") != role:
            fail(f"frozen judge role differs from {filename}")
        assignments.extend((row, filename) for row in rows)
    if len(assignments) != 96:
        fail(f"expected 96 LLM assignments, found {len(assignments)}")
    expected_observations = run.get("expected_observations", {})
    if (
        expected_observations.get("J_PRIMARY") != 72
        or expected_observations.get("J_SENS_GEMINI") != 24
    ):
        fail("run manifest LLM observation counts changed")

    return {
        "freeze": freeze,
        "run": run,
        "build": build,
        "items": items,
        "item_lines": item_lines,
        "assignments": assignments,
        "model_settings": model_settings,
        "prompting": prompting,
        "system_bytes": system_bytes,
        "developer_bytes": developer_bytes,
        "guide_bytes": guide_bytes,
        "full_schema": full_schema,
        "transport_schema": transport_schema,
        "freeze_hash": freeze_hash,
        "build_hash": build_hash,
        "item_bank_hash": item_bank_hash,
        "prompt_hash": prompt_hash,
        "guide_hash": guide_hash,
        "full_schema_hash": full_schema_hash,
        "transport_schema_hash": transport_schema_hash,
        "source_receipt_hash": source_receipt_hash,
    }


def render_user_message(guide_bytes: bytes, item_bytes: bytes) -> bytes:
    if not guide_bytes.endswith(b"\n") or not item_bytes.endswith(b"\n"):
        fail("guide and canonical evaluator item must each end with LF")
    user_bytes = (
        b"SHARED RATER GUIDE\n"
        + guide_bytes
        + b"\nBEGIN EVALUATOR ITEM\n"
        + item_bytes
        + b"END EVALUATOR ITEM\n\n"
        + b"Return the shared rating JSON object only.\n"
    )
    try:
        user_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"rendered user message is not UTF-8: {exc}")
    return user_bytes


def canonicalize_schema_errors(
    schema_errors: Any, *, failure_class: str
) -> list[dict[str, str]]:
    if not isinstance(schema_errors, list):
        fail("repair schema_errors must be a list")
    canonical: list[dict[str, str]] = []
    for index, record in enumerate(schema_errors):
        if (
            not isinstance(record, dict)
            or not all(isinstance(key, str) for key in record)
            or set(record) != set(REPAIR_ERROR_FIELDS)
        ):
            fail(f"repair schema error {index} has unexpected fields")
        normalized: dict[str, str] = {}
        for field in REPAIR_ERROR_FIELDS:
            value = record[field]
            if not isinstance(value, str):
                fail(f"repair schema error {index}.{field} must be a string")
            if "\x00" in value or "\r" in value:
                fail(f"repair schema error {index}.{field} has forbidden bytes")
            normalized[field] = value
        canonical.append(normalized)
    if failure_class == "invalid_schema" and not canonical:
        fail("invalid_schema repair requires at least one schema-error record")
    canonical.sort(key=canonical_bytes)
    if len({canonical_bytes(record) for record in canonical}) != len(canonical):
        fail("repair schema-error records must not contain duplicates")
    return canonical


def render_repair_instruction(
    *,
    invalid_response_bytes: bytes,
    schema_errors: Any,
    failure_class: str,
    attempt_number: int = 2,
) -> tuple[str, str]:
    """Render the sole new message allowed for the format-only second attempt."""

    if failure_class not in {"invalid_json", "invalid_schema"}:
        fail("format-only repair is allowed only after invalid_json/invalid_schema")
    if attempt_number != 2:
        fail("format-only repair is frozen to attempt 2; no later retry is allowed")
    if not isinstance(invalid_response_bytes, bytes):
        fail("invalid response must be supplied as exact bytes")
    errors = canonicalize_schema_errors(
        schema_errors, failure_class=failure_class
    )
    payload = {
        "attempt_number": 2,
        "failure_class": failure_class,
        "instruction": REPAIR_INSTRUCTION,
        "invalid_response_base64": base64.b64encode(invalid_response_bytes).decode(
            "ascii"
        ),
        "invalid_response_length_bytes": len(invalid_response_bytes),
        "invalid_response_sha256": sha256_bytes(invalid_response_bytes),
        "repair_message_version": REPAIR_MESSAGE_VERSION,
        "schema_errors": errors,
    }
    message_bytes = b"DIRECTION-J FORMAT-ONLY REPAIR\n" + canonical_bytes(payload)
    return message_bytes.decode("utf-8"), sha256_bytes(message_bytes)


def render_repair_packet(
    original_packet: dict[str, Any],
    *,
    invalid_response_bytes: bytes,
    schema_errors: Any,
    failure_class: str,
    attempt_number: int = 2,
) -> dict[str, Any]:
    """Build a provider-neutral repair packet without accepting semantic inputs."""

    if not isinstance(original_packet, dict):
        fail("repair source must be a complete initial request packet object")
    supplied_request_id = original_packet.get("request_packet_id")
    if not isinstance(supplied_request_id, str) or not supplied_request_id:
        fail("repair source lacks request_packet_id")

    frozen_bundle = load_and_validate_sources()
    frozen_packets, _frozen_jsonl = render_packets(frozen_bundle)
    frozen_by_id = {
        packet["request_packet_id"]: packet for packet in frozen_packets
    }
    if len(frozen_by_id) != len(frozen_packets):
        fail("frozen request packet bank contains a request_packet_id collision")
    canonical_initial = frozen_by_id.get(supplied_request_id)
    if canonical_initial is None:
        fail("repair request_packet_id does not resolve in the frozen request bank")
    try:
        supplied_bytes = canonical_bytes(original_packet)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        fail(f"repair source cannot be canonically serialized: {exc}")
    canonical_initial_bytes = canonical_bytes(canonical_initial)
    if supplied_bytes != canonical_initial_bytes:
        fail(
            "repair source differs from the complete reconstructed frozen initial packet"
        )
    original_packet = canonical_initial

    if (
        original_packet.get("request_packet_version") != PACKET_VERSION
        or original_packet.get("actor_kind") != "llm"
        or original_packet.get("qualification_scope") != "synthetic_only"
        or original_packet.get("contains_real_source_text") is not False
        or original_packet.get("wire_adapter_status") != WIRE_STATUS
    ):
        fail("repair source is not a frozen synthetic initial request packet")
    for field in ("request_packet_id", "actor_id", "assignment_id"):
        if not isinstance(original_packet.get(field), str) or not original_packet[field]:
            fail(f"repair source lacks {field}")
    for field in ("rating_repetition", "sequence"):
        if not isinstance(original_packet.get(field), int) or original_packet[field] < 1:
            fail(f"repair source has invalid {field}")
    for field in ("response_schema_sha256", "post_validation_schema_sha256"):
        require_sha(original_packet.get(field), f"repair source {field}")
    messages = original_packet.get("messages")
    message_hashes = original_packet.get("message_sha256")
    if (
        not isinstance(messages, dict)
        or set(messages) != {"system", "developer", "user"}
        or not isinstance(message_hashes, dict)
        or set(message_hashes) != {"system", "developer", "user"}
    ):
        fail("repair source lacks the frozen three-message interface")
    for role in ("system", "developer", "user"):
        value = messages[role]
        if not isinstance(value, str):
            fail(f"repair source {role} message is not a string")
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            fail(f"repair source {role} message is not valid UTF-8: {exc}")
        if sha256_bytes(encoded) != message_hashes[role]:
            fail(f"repair source {role} message hash is stale")
    repair_message, repair_hash = render_repair_instruction(
        invalid_response_bytes=invalid_response_bytes,
        schema_errors=schema_errors,
        failure_class=failure_class,
        attempt_number=attempt_number,
    )
    logical_messages = [
        {
            "position": 1,
            "logical_message_id": "initial_system",
            "role": "system",
            "content": messages["system"],
            "content_sha256": message_hashes["system"],
        },
        {
            "position": 2,
            "logical_message_id": "initial_developer",
            "role": "developer",
            "content": messages["developer"],
            "content_sha256": message_hashes["developer"],
        },
        {
            "position": 3,
            "logical_message_id": "initial_user",
            "role": "user",
            "content": messages["user"],
            "content_sha256": message_hashes["user"],
        },
        {
            "position": 4,
            "logical_message_id": "format_repair",
            "role": "user",
            "content": repair_message,
            "content_sha256": repair_hash,
        },
    ]
    return {
        "repair_packet_version": REPAIR_PACKET_VERSION,
        "repair_message_version": REPAIR_MESSAGE_VERSION,
        "original_request_packet_id": original_packet["request_packet_id"],
        "canonical_initial_packet_sha256": sha256_bytes(canonical_initial_bytes),
        "actor_id": original_packet["actor_id"],
        "assignment_id": original_packet["assignment_id"],
        "rating_repetition": original_packet["rating_repetition"],
        "sequence": original_packet["sequence"],
        "attempt_number": 2,
        "failure_class": failure_class,
        "logical_message_order": [
            "initial_system",
            "initial_developer",
            "initial_user",
            "format_repair",
        ],
        "logical_messages": logical_messages,
        "messages_repeated_unchanged": {
            "system": messages["system"],
            "developer": messages["developer"],
            "user": messages["user"],
        },
        "original_message_sha256": {
            "system": message_hashes["system"],
            "developer": message_hashes["developer"],
            "user": message_hashes["user"],
        },
        "appended_repair_message": repair_message,
        "appended_repair_message_sha256": repair_hash,
        "appended_repair_message_logical_role": "user",
        "appended_repair_message_position": 4,
        "response_schema_sha256": original_packet["response_schema_sha256"],
        "post_validation_schema_sha256": original_packet[
            "post_validation_schema_sha256"
        ],
        "post_validation_required": True,
        "wire_adapter_status": WIRE_STATUS,
        "provider_wire_request_rendered": False,
        "network_dispatch_authorized": False,
    }


def request_packet_id(row: dict[str, Any], prompt_hash: str) -> str:
    identity = {
        "actor_id": row["actor_id"],
        "assignment_id": row["assignment_id"],
        "item_id": row["item_id"],
        "prompt_sha256": prompt_hash,
        "rating_repetition": row["rating_repetition"],
        "run_id": RUN_ID,
        "semantic_input_sha256": row["semantic_input_sha256"],
        "sequence": row["sequence"],
    }
    return f"DJREQ_{sha256_bytes(canonical_bytes(identity))[:16]}"


def render_packets(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], bytes]:
    system_bytes = bundle["system_bytes"]
    developer_bytes = bundle["developer_bytes"]
    system = system_bytes.decode("utf-8")
    developer = developer_bytes.decode("utf-8")
    packets: list[dict[str, Any]] = []
    packet_ids: set[str] = set()

    for row, assignment_filename in bundle["assignments"]:
        actor_id = row["actor_id"]
        item_bytes = bundle["item_lines"][row["item_id"]]
        user_bytes = render_user_message(bundle["guide_bytes"], item_bytes)
        user = user_bytes.decode("utf-8")
        model_settings = bundle["model_settings"][actor_id]
        packet_id = request_packet_id(row, bundle["prompt_hash"])
        if packet_id in packet_ids:
            fail(f"request-packet ID collision: {packet_id}")
        packet_ids.add(packet_id)
        assignment_receipt = bundle["build"]["assignment_files"][
            assignment_filename
        ]
        packet = {
            "request_packet_version": PACKET_VERSION,
            "request_packet_id": packet_id,
            "study_id": "direction-j-v1",
            "run_id": RUN_ID,
            "qualification_scope": "synthetic_only",
            "contains_real_source_text": False,
            "evaluation_role": "synthetic_qualification",
            "actor_id": actor_id,
            "actor_kind": "llm",
            "assignment_id": row["assignment_id"],
            "rating_repetition": row["rating_repetition"],
            "sequence": row["sequence"],
            "item_id": row["item_id"],
            "packet_id": row["packet_id"],
            "output_id": row["output_id"],
            "corpus_id": row["corpus_id"],
            "interface_version": INTERFACE_VERSION,
            "item_schema_version": ITEM_SCHEMA_VERSION,
            "rating_schema_version": RATING_SCHEMA_VERSION,
            "shared_rater_guide_version": GUIDE_VERSION,
            "prompt_version": PROMPT_VERSION,
            "item_payload_sha256": row["item_payload_sha256"],
            "semantic_input_sha256": row["semantic_input_sha256"],
            "shared_rater_guide_sha256": bundle["guide_hash"],
            "prompt_source_sha256": bundle["prompt_hash"],
            "messages": {
                "system": system,
                "developer": developer,
                "user": user,
            },
            "message_sha256": {
                "system": sha256_bytes(system_bytes),
                "developer": sha256_bytes(developer_bytes),
                "user": sha256_bytes(user_bytes),
            },
            "rendered_messages_sha256": sha256_bytes(
                canonical_bytes(
                    {"system": system, "developer": developer, "user": user}
                )
            ),
            "response_schema": bundle["transport_schema"],
            "response_schema_sha256": bundle["transport_schema_hash"],
            "response_schema_hash_rule": "sha256(canonical_json_utf8_lf)",
            "post_validation_schema": bundle["full_schema"],
            "post_validation_schema_sha256": bundle["full_schema_hash"],
            "post_validation_schema_hash_rule": "sha256(checked_in_file_bytes)",
            "post_validation_required": True,
            "structured_decoding_replaces_post_validation": False,
            "frozen_model_settings": model_settings,
            "frozen_model_settings_sha256": sha256_bytes(
                canonical_bytes(model_settings)
            ),
            "frozen_prompting_policy": bundle["prompting"],
            "frozen_prompting_policy_sha256": sha256_bytes(
                canonical_bytes(bundle["prompting"])
            ),
            "wire_adapter_status": WIRE_STATUS,
            "provider_wire_adapter": {
                "wire_adapter_status": WIRE_STATUS,
                "provider_wire_request": None,
                "provider_wire_request_rendered": False,
                "network_dispatch_authorized": False,
                "credential_access_authorized": False,
            },
            "lineage": {
                "freeze_sha256": bundle["freeze_hash"],
                "build_report_sha256": bundle["build_hash"],
                "source_receipt_sha256": bundle["source_receipt_hash"],
                "evaluator_items_sha256": bundle["item_bank_hash"],
                "assignment_manifest": f"assignments/{assignment_filename}",
                "assignment_manifest_sha256": assignment_receipt["sha256"],
            },
        }
        packets.append(packet)

    packets.sort(
        key=lambda packet: (
            packet["actor_id"],
            packet["rating_repetition"],
            packet["sequence"],
        )
    )
    rendered = b"".join(canonical_bytes(packet) for packet in packets)
    return packets, rendered


def packet_output_path(raw_path: str, *, must_exist: bool) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    candidate = lexical_absolute(candidate)
    allowed_root = lexical_absolute(REQUEST_PACKETS_DIR)
    if candidate.parent != allowed_root:
        fail(
            "request packet path must be a direct child of the frozen run's "
            "request-packets directory"
        )
    if candidate.name != REQUEST_PACKET_FILENAME:
        fail(f"request packet filename must be exactly {REQUEST_PACKET_FILENAME}")
    if candidate.suffix != ".jsonl" or candidate.name.startswith("."):
        fail("request packet filename must be a non-hidden .jsonl file")
    if has_forbidden_part(candidate.relative_to(PROJECT_ROOT)):
        fail("request packet path contains a forbidden private/result component")
    reject_symlink_components(candidate)
    return candidate


def validate_candidate_jsonl(candidate: bytes, expected: bytes) -> int:
    if candidate.startswith(b"\xef\xbb\xbf") or b"\r" in candidate:
        fail("request packet JSONL must be BOM-free UTF-8 with LF newlines")
    if not candidate or not candidate.endswith(b"\n"):
        fail("request packet JSONL must be nonempty and end with LF")
    count = 0
    for line_number, line in enumerate(candidate.splitlines(keepends=True), 1):
        if line == b"\n" or not line.endswith(b"\n"):
            fail(f"request packet JSONL line {line_number} is blank or lacks LF")
        try:
            value = json.loads(line[:-1].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"request packet JSONL line {line_number} is invalid: {exc}")
        if not isinstance(value, dict) or canonical_bytes(value) != line:
            fail(f"request packet JSONL line {line_number} is not canonical JSON")
        count += 1
    if candidate != expected:
        fail("request packet JSONL differs byte-for-byte from frozen deterministic render")
    return count


def open_request_packets_dir(*, create: bool) -> int:
    """Open the exact output directory by descriptor without following it."""

    reject_symlink_components(RUN_ROOT)
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    try:
        run_descriptor = os.open(RUN_ROOT, directory_flags)
    except OSError as exc:
        fail(f"cannot open frozen run root without following links: {exc}")
    try:
        run_stat = os.fstat(run_descriptor)
        if not stat.S_ISDIR(run_stat.st_mode):
            fail("frozen run root is not a directory")
        try:
            output_descriptor = os.open(
                REQUEST_PACKETS_DIR.name,
                directory_flags,
                dir_fd=run_descriptor,
            )
        except FileNotFoundError:
            if not create:
                fail("request-packets directory does not exist")
            try:
                os.mkdir(REQUEST_PACKETS_DIR.name, mode=0o750, dir_fd=run_descriptor)
            except FileExistsError:
                pass
            except OSError as exc:
                fail(f"cannot create request-packets directory safely: {exc}")
            try:
                output_descriptor = os.open(
                    REQUEST_PACKETS_DIR.name,
                    directory_flags,
                    dir_fd=run_descriptor,
                )
            except OSError as exc:
                fail(f"cannot open newly created request-packets directory: {exc}")
        except OSError as exc:
            fail(f"cannot open request-packets directory without following links: {exc}")
    finally:
        os.close(run_descriptor)
    output_stat = os.fstat(output_descriptor)
    if not stat.S_ISDIR(output_stat.st_mode):
        os.close(output_descriptor)
        fail("request-packets output root is not a directory")
    return output_descriptor


def read_output_relative(directory_descriptor: int, filename: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(filename, flags, dir_fd=directory_descriptor)
    except OSError as exc:
        fail(f"cannot open request packet output without following links: {exc}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail("request packet output is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        fail("request packet output changed while being read")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        fail("request packet output size changed while being read")
    return data


def read_output_packet(path: Path) -> bytes:
    if path.name != REQUEST_PACKET_FILENAME:
        fail("request packet output filename changed after validation")
    directory_descriptor = open_request_packets_dir(create=False)
    try:
        return read_output_relative(directory_descriptor, path.name)
    finally:
        os.close(directory_descriptor)


def write_idempotently(path: Path, rendered: bytes) -> str:
    if path.name != REQUEST_PACKET_FILENAME:
        fail("request packet output filename changed after validation")
    directory_descriptor = open_request_packets_dir(create=True)
    read_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        read_flags |= os.O_NOFOLLOW
    try:
        try:
            existing_descriptor = os.open(
                path.name, read_flags, dir_fd=directory_descriptor
            )
        except FileNotFoundError:
            existing_descriptor = None
        except OSError as exc:
            fail(f"cannot inspect existing request packet output safely: {exc}")
        if existing_descriptor is not None:
            os.close(existing_descriptor)
            existing = read_output_relative(directory_descriptor, path.name)
            validate_candidate_jsonl(existing, rendered)
            return "unchanged_existing"

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(
                path.name,
                flags,
                0o600,
                dir_fd=directory_descriptor,
            )
        except FileExistsError:
            existing = read_output_relative(directory_descriptor, path.name)
            validate_candidate_jsonl(existing, rendered)
            return "unchanged_existing"
        except OSError as exc:
            fail(f"cannot create request packet output safely: {exc}")
        created = True
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                fail("new request packet output is not a regular file")
            view = memoryview(rendered)
            written = 0
            while written < len(view):
                count = os.write(descriptor, view[written:])
                if count <= 0:
                    fail("short write while creating request packet output")
                written += count
            os.fsync(descriptor)
            finished = os.fstat(descriptor)
            if finished.st_size != len(rendered):
                fail("request packet output size differs after write")
            os.fchmod(descriptor, 0o440)
            os.fsync(descriptor)
            before_readback = os.fstat(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            readback_chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                readback_chunks.append(chunk)
            after_readback = os.fstat(descriptor)
            if (
                before_readback.st_dev,
                before_readback.st_ino,
                before_readback.st_size,
                before_readback.st_mtime_ns,
            ) != (
                after_readback.st_dev,
                after_readback.st_ino,
                after_readback.st_size,
                after_readback.st_mtime_ns,
            ):
                fail("request packet output changed during creation readback")
            if b"".join(readback_chunks) != rendered:
                fail("request packet output differs during creation readback")
        except BaseException:
            os.close(descriptor)
            if created:
                try:
                    os.unlink(path.name, dir_fd=directory_descriptor)
                except OSError:
                    pass
            raise
        else:
            os.close(descriptor)
        return "created"
    finally:
        os.close(directory_descriptor)


def summary(packets: list[dict[str, Any]], rendered: bytes, action: str) -> dict[str, Any]:
    by_actor: dict[str, int] = {}
    by_actor_repetition: dict[str, int] = {}
    for packet in packets:
        actor = packet["actor_id"]
        by_actor[actor] = by_actor.get(actor, 0) + 1
        key = f"{actor}:rep{packet['rating_repetition']}"
        by_actor_repetition[key] = by_actor_repetition.get(key, 0) + 1
    return {
        "action": action,
        "contains_real_source_text": False,
        "empirical_results_emitted": False,
        "packet_count": len(packets),
        "packets_by_actor": dict(sorted(by_actor.items())),
        "packets_by_actor_repetition": dict(sorted(by_actor_repetition.items())),
        "request_packets_sha256": sha256_bytes(rendered),
        "wire_adapter_status": WIRE_STATUS,
    }


def expect_failure(label: str, function: Any) -> str:
    try:
        function()
    except PacketError:
        return label
    fail(f"self-test negative probe did not fail: {label}")


def self_test() -> dict[str, Any]:
    bundle = load_and_validate_sources()
    packets, rendered = render_packets(bundle)
    if len(packets) != 96:
        fail("self-test render did not produce 96 packets")
    if sum(packet["actor_id"] == "J_PRIMARY" for packet in packets) != 72:
        fail("self-test primary packet count mismatch")
    if sum(packet["actor_id"] == "J_SENS_GEMINI" for packet in packets) != 24:
        fail("self-test sensitivity packet count mismatch")
    if any(packet["wire_adapter_status"] != WIRE_STATUS for packet in packets):
        fail("self-test found a packet marked ready for provider dispatch")
    if any(packet["post_validation_required"] is not True for packet in packets):
        fail("self-test found a packet without authoritative post-validation")
    transport = bundle["transport_schema"]
    if "allOf" in transport or len(transport.get("required", [])) != 10:
        fail("self-test structural transport projection is not minimal/frozen")
    validate_candidate_jsonl(rendered, rendered)

    repair_invalid = (
        b'{"confidence":6,"rating_schema_version":'
        b'"direction-j-shared-rating-v1"}\n'
    )
    repair_errors = [
        {
            "instance_path": "/confidence",
            "schema_path": "/properties/confidence/maximum",
            "keyword": "maximum",
            "message": "6 exceeds maximum 5",
        },
        {
            "instance_path": "",
            "schema_path": "/required",
            "keyword": "required",
            "message": "missing required fields",
        },
    ]
    repair_message, repair_hash = render_repair_instruction(
        invalid_response_bytes=repair_invalid,
        schema_errors=repair_errors,
        failure_class="invalid_schema",
    )
    if repair_hash != REPAIR_TEST_VECTOR_SHA256:
        fail("format-repair test vector hash changed")
    repair_packet = render_repair_packet(
        packets[0],
        invalid_response_bytes=repair_invalid,
        schema_errors=list(reversed(repair_errors)),
        failure_class="invalid_schema",
    )
    if (
        repair_packet["messages_repeated_unchanged"] != packets[0]["messages"]
        or repair_packet["appended_repair_message"] != repair_message
        or repair_packet["appended_repair_message_sha256"] != repair_hash
        or repair_packet["attempt_number"] != 2
    ):
        fail("format-repair packet changed original messages or deterministic vector")

    first_spec = ASSIGNMENT_SPECS[0]
    first_path = ASSIGNMENTS_ROOT / first_spec[0]
    assignment_raw = read_static_bytes(first_path)
    first_item_hash = next(iter(bundle["item_lines"].values()))
    first_item_hash = sha256_bytes(first_item_hash)

    def parse_probe(raw: bytes) -> None:
        parse_assignment_bytes(
            raw,
            label="self-test assignment probe",
            expected_actor=first_spec[1],
            expected_repetition=first_spec[2],
            items=bundle["items"],
            item_lines=bundle["item_lines"],
            guide_hash=bundle["guide_hash"],
        )

    def parse_probe_with_lines(lines: dict[str, bytes]) -> None:
        parse_assignment_bytes(
            assignment_raw,
            label="self-test assignment/item probe",
            expected_actor=first_spec[1],
            expected_repetition=first_spec[2],
            items=bundle["items"],
            item_lines=lines,
            guide_hash=bundle["guide_hash"],
        )

    prompt_bytes = read_static_bytes(PROMPT_PATH)
    golden_item = bundle["items"][GOLDEN_ITEM_ID]
    alternate_serialization = (
        json.dumps(golden_item, sort_keys=True, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )
        + b"\n"
        + b"".join(
            line
            for item_id, line in bundle["item_lines"].items()
            if item_id != GOLDEN_ITEM_ID
        )
    )
    reordered_item = json.loads(json.dumps(golden_item))
    reordered_item["evidence"] = list(reversed(reordered_item["evidence"]))
    reordered_lines = dict(bundle["item_lines"])
    reordered_lines[GOLDEN_ITEM_ID] = canonical_bytes(reordered_item)
    private_item = json.loads(json.dumps(golden_item))
    private_item["condition"] = "forbidden_private_probe"
    private_bank = b"".join(
        canonical_bytes(private_item if item_id == GOLDEN_ITEM_ID else item)
        for item_id, item in bundle["items"].items()
    )

    probes = [
        expect_failure(
            "human_assignment_rejected",
            lambda: parse_probe(assignment_raw.replace(b",llm,", b",human,", 1)),
        ),
        expect_failure(
            "stale_item_hash_rejected",
            lambda: parse_probe(
                assignment_raw.replace(
                    first_item_hash.encode("ascii"), b"0" * 64, 1
                )
            ),
        ),
        expect_failure(
            "prompt_newline_drift_rejected",
            lambda: extract_marked_message(
                prompt_bytes.replace(b"\n", b"\r\n"),
                BEGIN_SYSTEM,
                END_SYSTEM,
                "system",
            ),
        ),
        expect_failure(
            "prompt_bom_rejected",
            lambda: extract_marked_message(
                b"\xef\xbb\xbf" + prompt_bytes,
                BEGIN_SYSTEM,
                END_SYSTEM,
                "system",
            ),
        ),
        expect_failure(
            "duplicate_prompt_marker_rejected",
            lambda: extract_marked_message(
                prompt_bytes + BEGIN_SYSTEM + b"\n",
                BEGIN_SYSTEM,
                END_SYSTEM,
                "system",
            ),
        ),
        expect_failure(
            "missing_prompt_marker_rejected",
            lambda: extract_marked_message(
                prompt_bytes.replace(BEGIN_SYSTEM, b"", 1),
                BEGIN_SYSTEM,
                END_SYSTEM,
                "system",
            ),
        ),
        expect_failure(
            "guide_final_lf_loss_rejected",
            lambda: render_user_message(
                bundle["guide_bytes"][:-1], bundle["item_lines"][GOLDEN_ITEM_ID]
            ),
        ),
        expect_failure(
            "alternate_item_serialization_rejected",
            lambda: parse_item_bank(alternate_serialization),
        ),
        expect_failure(
            "evidence_reorder_rejected",
            lambda: parse_probe_with_lines(reordered_lines),
        ),
        expect_failure(
            "private_item_field_rejected",
            lambda: parse_item_bank(private_bank),
        ),
        expect_failure(
            "private_path_rejected",
            lambda: packet_output_path(
                str(RUN_ROOT / "private" / "probe.jsonl"), must_exist=False
            ),
        ),
        expect_failure(
            "private_map_input_rejected",
            lambda: assert_static_input(RUN_ROOT / "private" / "item_key.jsonl"),
        ),
        expect_failure(
            "output_escape_rejected",
            lambda: packet_output_path(
                str(RUN_ROOT / "probe.jsonl"), must_exist=False
            ),
        ),
        expect_failure(
            "output_filename_substitution_rejected",
            lambda: packet_output_path(
                str(REQUEST_PACKETS_DIR / "substituted.jsonl"), must_exist=False
            ),
        ),
        expect_failure(
            "static_input_path_substitution_rejected",
            lambda: assert_static_input(DIRECTION_ROOT / "protocol" / "prompt-copy.md"),
        ),
    ]

    mutated_scope = json.loads(json.dumps(bundle["freeze"]))
    mutated_scope["scope"]["contains_real_source_text"] = True
    probes.append(
        expect_failure(
            "real_text_scope_rejected",
            lambda: assert_synthetic_scope(
                mutated_scope,
                bundle["run"],
                bundle["build"],
                bundle["build"]["source_receipt"],
            ),
        )
    )
    relaxed_full_schema = json.loads(json.dumps(bundle["full_schema"]))
    relaxed_full_schema["additionalProperties"] = True
    probes.append(
        expect_failure(
            "transport_schema_relaxation_rejected",
            lambda: project_transport_schema(relaxed_full_schema),
        )
    )
    extra_message_packet = json.loads(json.dumps(packets[0]))
    extra_message_packet["messages"]["assistant"] = "prior conversation reuse"
    extra_message_bytes = canonical_bytes(extra_message_packet) + b"".join(
        canonical_bytes(packet) for packet in packets[1:]
    )
    probes.append(
        expect_failure(
            "extra_message_or_conversation_reuse_rejected",
            lambda: validate_candidate_jsonl(extra_message_bytes, rendered),
        )
    )
    first_packet = json.loads(json.dumps(packets[0]))
    first_packet["wire_adapter_status"] = "ready"
    changed = canonical_bytes(first_packet) + b"".join(
        canonical_bytes(packet) for packet in packets[1:]
    )
    probes.append(
        expect_failure(
            "noncanonical_or_changed_packet_rejected",
            lambda: validate_candidate_jsonl(changed, rendered),
        )
    )
    probes.extend(
        [
            expect_failure(
                "repair_third_attempt_rejected",
                lambda: render_repair_instruction(
                    invalid_response_bytes=repair_invalid,
                    schema_errors=repair_errors,
                    failure_class="invalid_schema",
                    attempt_number=3,
                ),
            ),
            expect_failure(
                "repair_nonformat_failure_rejected",
                lambda: render_repair_instruction(
                    invalid_response_bytes=repair_invalid,
                    schema_errors=repair_errors,
                    failure_class="wrong_answer",
                ),
            ),
            expect_failure(
                "repair_empty_schema_errors_rejected",
                lambda: render_repair_instruction(
                    invalid_response_bytes=repair_invalid,
                    schema_errors=[],
                    failure_class="invalid_schema",
                ),
            ),
        ]
    )
    tampered_original = json.loads(json.dumps(packets[0]))
    tampered_original["messages"]["user"] += "substitution"
    probes.append(
        expect_failure(
            "repair_original_message_substitution_rejected",
            lambda: render_repair_packet(
                tampered_original,
                invalid_response_bytes=repair_invalid,
                schema_errors=repair_errors,
                failure_class="invalid_schema",
            ),
        )
    )

    result = summary(packets, rendered, "self_test")
    result["negative_probes_passed"] = probes
    result["bohr_golden_vector_asserted"] = {
        "developer_sha256": GOLDEN_DEVELOPER_SHA256,
        "guide_sha256": GOLDEN_GUIDE_SHA256,
        "item_id": GOLDEN_ITEM_ID,
        "item_sha256": GOLDEN_ITEM_SHA256,
        "system_sha256": GOLDEN_SYSTEM_SHA256,
        "user_sha256": GOLDEN_USER_SHA256,
    }
    result["repair_message_test_vector_sha256"] = REPAIR_TEST_VECTOR_SHA256
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline deterministic renderer/verifier for frozen synthetic "
            "Direction J provider-neutral request packets."
        )
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--write",
        metavar="REQUEST_PACKETS_JSONL",
        help=(
            "write idempotently to the frozen run's exact "
            "request-packets/request_packets_v1.jsonl path"
        ),
    )
    action.add_argument(
        "--verify",
        metavar="REQUEST_PACKETS_JSONL",
        help="verify an existing request-packets JSONL byte-for-byte",
    )
    action.add_argument(
        "--self-test",
        action="store_true",
        help="run positive and fail-closed negative probes without writing",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    try:
        reject_symlink_components(SCRIPT_PATH)
        args = parse_args(argv)
        if args.self_test:
            result = self_test()
        else:
            bundle = load_and_validate_sources()
            packets, rendered = render_packets(bundle)
            if args.verify:
                path = packet_output_path(args.verify, must_exist=True)
                count = validate_candidate_jsonl(read_output_packet(path), rendered)
                if count != len(packets):
                    fail("verified request packet count differs from frozen render")
                result = summary(packets, rendered, "verified")
                result["request_packets_path"] = str(path.relative_to(PROJECT_ROOT))
            elif args.write:
                path = packet_output_path(args.write, must_exist=False)
                write_status = write_idempotently(path, rendered)
                result = summary(packets, rendered, write_status)
                result["request_packets_path"] = str(path.relative_to(PROJECT_ROOT))
            else:
                result = summary(packets, rendered, "dry_run_no_write")
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except PacketError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
