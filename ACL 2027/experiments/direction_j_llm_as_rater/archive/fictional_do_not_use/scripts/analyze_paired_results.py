#!/usr/bin/env python3
"""Validate and descriptively analyze locked Direction J paired observations.

The utility is intentionally synthetic-only in v1. It accepts one analysis lock
manifest, verifies hashes before parsing any study record, and refuses to write
a result file unless the complete primary pair and one locked expert
adjudication per item are present. It never backfills a missing rating,
adjudication, cost, or latency value and never combines the three quality
constructs into an omnibus score.

Required lock-manifest shape (paths are relative to the lock file):

  analysis_input_lock_version: direction-j-analysis-input-lock-v1
  status: locked_for_analysis
  study_id: direction-j-v1
  evaluation_role: synthetic_qualification
  qualification_scope: synthetic_only
  contains_real_source_text: false
  result_label: synthetic_qualification_only
  locked_at_utc: RFC-3339 timestamp
  observations_locked: true
  adjudications_locked: true
  actor_registry_locked: true
  expected_item_count: positive integer
  primary_pair:
    left_actor_id, right_actor_id,
    left_rating_repetition: 1, right_rating_repetition: 1
  first_stage_actor_repetitions: {actor_id: [positive repetitions]}
  expert_actor_ids: [at least two registered human experts]
  files:
    run_manifest, actor_registry, observations, expert_adjudications
    Each descriptor contains exactly {path, sha256}.

The lock file and all locked inputs must live directly in the one frozen
Direction J synthetic run directory. Analysis also verifies the current freeze,
build-report, evaluator-bank, and fictional-source-receipt hashes. No path
containing a dataset/datasets component is accepted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
RUNS_ROOT = DIRECTION_ROOT / "runs"
FROZEN_RUN_ID = "20260825_synthetic_paired_qualification_prepared"
FROZEN_RUN_ROOT = RUNS_ROOT / FROZEN_RUN_ID
FREEZE_PATH = DIRECTION_ROOT / "config" / "freeze_v1.json"
EVALUATOR_ITEMS_PATH = FROZEN_RUN_ROOT / "evaluator_items.jsonl"
BUILD_REPORT_PATH = FROZEN_RUN_ROOT / "build_report.json"
SCHEMAS_ROOT = DIRECTION_ROOT / "schemas"
OBSERVATION_SCHEMA_PATH = SCHEMAS_ROOT / "paired_observation.schema.json"
RATING_SCHEMA_PATH = SCHEMAS_ROOT / "shared_rating.schema.json"
RATER_GUIDE_PATH = DIRECTION_ROOT / "protocol" / "shared_rater_guide_v1.md"

ANALYSIS_VERSION = "direction-j-paired-descriptive-analysis-v1"
LOCK_VERSION = "direction-j-analysis-input-lock-v1"
OBSERVATION_VERSION = "direction-j-paired-observation-v1"
RATING_VERSION = "direction-j-shared-rating-v1"
ADJUDICATION_VERSION = "direction-j-expert-adjudication-v1"
ACTOR_REGISTRY_VERSION = "direction-j-actor-registry-v1"
INTERFACE_VERSION = "direction-j-shared-interface-v1"
RATER_GUIDE_VERSION = "direction-j-rater-guide-v1"

SYNTHETIC_ROLE = "synthetic_qualification"
SYNTHETIC_SCOPE = "synthetic_only"
SYNTHETIC_LABEL = "synthetic_qualification_only"

CONSTRUCTS = [
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
]
DISPOSITIONS = ["accept", "revise", "reject", "escalate"]
REQUESTED_EXPERTISE = ["none", "qualitative_methods", "domain", "both"]
SERIOUS_ERROR_FLAGS = [
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
    "inconsistent_codebook",
    "other",
]
ADJUDICATED_ACTIONS = ["accept", "expert_review", "plural_ambiguous"]
SEVERITIES = ["none", "minor", "material", "high_consequence"]
OBSERVATION_STATUSES = [
    "valid",
    "invalid_output",
    "timeout",
    "provider_error",
    "content_filtered",
]
TERMINAL_FAILURE_STATUSES = set(OBSERVATION_STATUSES) - {"valid"}
ATTEMPT_STATUSES = [
    "schema_valid_output",
    "invalid_json",
    "invalid_schema",
    "timeout",
    "provider_error",
    "content_filtered",
]
FILTER_STATUSES = [
    "not_reported",
    "not_filtered",
    "partially_filtered",
    "filtered",
]
FROZEN_ITEM_BINDING_FIELDS = {
    "item_id",
    "packet_id",
    "output_id",
    "corpus_id",
    "item_payload_sha256",
    "interface_version",
    "shared_rater_guide_version",
    "shared_rater_guide_sha256",
    "semantic_input_sha256",
}
ASSIGNMENT_FIELDS = {
    "assignment_id",
    "actor_id",
    "actor_kind",
    "rating_repetition",
    "sequence",
    *FROZEN_ITEM_BINDING_FIELDS,
    "evaluation_role",
}
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
ITEM_RE = re.compile(r"^DJI_[a-f0-9]{16}$")

LOCK_REQUIRED = {
    "analysis_input_lock_version",
    "status",
    "study_id",
    "evaluation_role",
    "qualification_scope",
    "contains_real_source_text",
    "result_label",
    "locked_at_utc",
    "observations_locked",
    "adjudications_locked",
    "actor_registry_locked",
    "expected_item_count",
    "primary_pair",
    "first_stage_actor_repetitions",
    "expert_actor_ids",
    "files",
}
LOCK_FILE_KEYS = {
    "run_manifest",
    "actor_registry",
    "observations",
    "expert_adjudications",
}
OBSERVATION_FIELDS = {
    "observation_schema_version",
    "observation_id",
    "study_id",
    "evaluation_role",
    "item_id",
    "packet_id",
    "output_id",
    "corpus_id",
    "candidate_generation_run_id",
    "candidate_generation_repetition",
    "actor_id",
    "actor_kind",
    "rating_repetition",
    "item_payload_sha256",
    "interface_version",
    "shared_rater_guide_version",
    "shared_rater_guide_sha256",
    "semantic_input_sha256",
    "prompt_or_instrument_version",
    "prompt_or_instrument_sha256",
    "started_at_utc",
    "completed_at_utc",
    "review_seconds",
    "observation_status",
    "rating",
    "blinding",
    "execution",
}
RATING_FIELDS = {
    "rating_schema_version",
    *CONSTRUCTS,
    "cannot_judge",
    "confidence",
    "disposition",
    "requested_expertise",
    "serious_error_flags",
    "rationale",
}
BLINDING_FIELDS = {
    "blind_id",
    "candidate_identity_hidden",
    "condition_hidden",
    "other_ratings_hidden",
    "unblinded_at_utc",
}
EXECUTION_FIELDS = {
    "retry_count",
    "attempts",
    "token_usage_available",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens_available",
    "reasoning_tokens",
    "cost_available",
    "cost_amount",
    "cost_currency",
    "pricing_snapshot_id",
}
ATTEMPT_FIELDS = {
    "attempt_index",
    "attempt_kind",
    "started_at_utc",
    "completed_at_utc",
    "attempt_status",
    "raw_request_artifact_id",
    "raw_request_sha256",
    "raw_response_artifact_id",
    "raw_response_sha256",
    "provider_request_id",
    "provider_response_id",
    "provider_returned_model_id",
    "provider_returned_model_version",
    "provider_region",
    "finish_reason",
    "filter_status",
    "schema_error_summary",
    "token_usage_available",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens_available",
    "reasoning_tokens",
}
ADJUDICATION_FIELDS = {
    "adjudication_version",
    "item_id",
    "panel_id",
    "locked_individual_observation_ids",
    "adjudicated_at_utc",
    "operational_action",
    "severity",
    "serious_error_flags",
    "error_locations",
    "requested_expertise",
    "rationale",
    "locked_before_private_unblind",
}


class AnalysisInputError(ValueError):
    """Raised before any results are written when a locked input is unusable."""


def fail(message: str) -> None:
    raise AnalysisInputError(message)


def validate_frozen_schema_contract() -> None:
    """Fail if the checked-in schemas drift beyond this stdlib validator."""

    try:
        observation_schema = json.loads(OBSERVATION_SCHEMA_PATH.read_text(encoding="utf-8"))
        rating_schema = json.loads(RATING_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisInputError(f"cannot read the frozen Direction J schemas: {error}") from error
    checks = [
        (
            set(observation_schema.get("required", [])),
            OBSERVATION_FIELDS,
            "paired-observation required fields",
        ),
        (
            set(
                observation_schema.get("properties", {})
                .get("execution", {})
                .get("required", [])
            ),
            EXECUTION_FIELDS,
            "execution required fields",
        ),
        (
            set(
                observation_schema.get("$defs", {})
                .get("executionAttempt", {})
                .get("required", [])
            ),
            ATTEMPT_FIELDS,
            "execution-attempt required fields",
        ),
        (set(rating_schema.get("required", [])), RATING_FIELDS, "shared-rating required fields"),
        (
            set(
                observation_schema.get("properties", {})
                .get("observation_status", {})
                .get("enum", [])
            ),
            set(OBSERVATION_STATUSES),
            "observation statuses",
        ),
        (
            set(
                observation_schema.get("$defs", {})
                .get("executionAttempt", {})
                .get("properties", {})
                .get("attempt_status", {})
                .get("enum", [])
            ),
            set(ATTEMPT_STATUSES),
            "attempt statuses",
        ),
    ]
    for observed, expected, label in checks:
        if observed != expected:
            fail(
                f"checked-in {label} drifted beyond this analyzer; "
                f"missing={sorted(expected - observed)}; extra={sorted(observed - expected)}"
            )
    guide_const = (
        observation_schema.get("properties", {})
        .get("shared_rater_guide_version", {})
        .get("const")
    )
    if guide_const != RATER_GUIDE_VERSION:
        fail("checked-in shared-rater-guide version differs from this analyzer")


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def require_exact_fields(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be an object")
    observed = set(value)
    missing = sorted(fields - observed)
    extra = sorted(observed - fields)
    if missing or extra:
        fail(f"{label} fields differ from the frozen contract; missing={missing}; extra={extra}")
    return value


def require_nonempty_string(value: Any, label: str, maximum: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a nonblank string")
    if maximum is not None and len(value) > maximum:
        fail(f"{label} exceeds {maximum} characters")
    return value


def require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        fail(f"{label} must be a lowercase SHA-256 digest")
    return value


def parse_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        fail(f"{label} must be an RFC-3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise AnalysisInputError(f"{label} is not a valid RFC-3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        fail(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def has_forbidden_path_component(path: Path) -> bool:
    return any(part.casefold() in {"dataset", "datasets"} for part in path.resolve().parts)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_semantic_input_sha256(
    item_payload_sha256: str, shared_rater_guide_sha256: str
) -> str:
    manifest = {
        "interface_version": INTERFACE_VERSION,
        "item_payload_sha256": item_payload_sha256,
        "shared_rater_guide_sha256": shared_rater_guide_sha256,
        "shared_rater_guide_version": RATER_GUIDE_VERSION,
    }
    canonical = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return sha256_bytes(canonical)


def checked_in_rater_guide_sha256() -> str:
    try:
        return sha256_bytes(RATER_GUIDE_PATH.read_bytes())
    except OSError as error:
        raise AnalysisInputError(f"cannot read the frozen shared rater guide: {error}") from error


def read_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisInputError(f"{label} is not valid UTF-8 JSON: {error}") from error


def read_jsonl_bytes(data: bytes, label: str) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AnalysisInputError(f"{label} is not UTF-8") from error
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise AnalysisInputError(f"{label}:{line_number} is invalid JSON: {error}") from error
        if not isinstance(record, dict):
            fail(f"{label}:{line_number} must contain an object")
        records.append(record)
    return records


def validate_lock(lock: Any) -> dict[str, Any]:
    lock = require_exact_fields(lock, LOCK_REQUIRED, "analysis input lock")
    if lock["analysis_input_lock_version"] != LOCK_VERSION:
        fail("analysis input lock version is not direction-j-analysis-input-lock-v1")
    if lock["status"] != "locked_for_analysis":
        fail("analysis input lock status must be locked_for_analysis")
    if lock["evaluation_role"] != SYNTHETIC_ROLE:
        fail("v1 analysis accepts synthetic_qualification only")
    if lock["qualification_scope"] != SYNTHETIC_SCOPE:
        fail("v1 analysis accepts synthetic_only inputs only")
    if lock["contains_real_source_text"] is not False:
        fail("analysis lock must explicitly state contains_real_source_text=false")
    if lock["result_label"] != SYNTHETIC_LABEL:
        fail("synthetic analysis result_label must be synthetic_qualification_only")
    for field in ["observations_locked", "adjudications_locked", "actor_registry_locked"]:
        if lock[field] is not True:
            fail(f"{field} must be true")
    parse_datetime(lock["locked_at_utc"], "analysis input lock locked_at_utc")
    if not isinstance(lock["expected_item_count"], int) or isinstance(
        lock["expected_item_count"], bool
    ) or lock["expected_item_count"] < 1:
        fail("expected_item_count must be a positive integer")

    pair_fields = {
        "left_actor_id",
        "right_actor_id",
        "left_rating_repetition",
        "right_rating_repetition",
    }
    pair = require_exact_fields(lock["primary_pair"], pair_fields, "primary_pair")
    left = require_nonempty_string(pair["left_actor_id"], "primary_pair.left_actor_id")
    right = require_nonempty_string(pair["right_actor_id"], "primary_pair.right_actor_id")
    if left == right:
        fail("primary pair actors must be distinct")
    if pair["left_rating_repetition"] != 1 or pair["right_rating_repetition"] != 1:
        fail("the frozen primary comparison must use rating repetition 1 for both actors")

    repetitions = lock["first_stage_actor_repetitions"]
    if not isinstance(repetitions, dict) or not repetitions:
        fail("first_stage_actor_repetitions must be a nonempty object")
    for actor_id, values in repetitions.items():
        require_nonempty_string(actor_id, "first-stage actor ID")
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in values)
            or len(values) != len(set(values))
            or values != sorted(values)
        ):
            fail(f"first-stage repetitions for {actor_id} must be sorted unique positive integers")
        if 1 not in values:
            fail(f"first-stage actor {actor_id} lacks primary repetition 1")
    if left not in repetitions or right not in repetitions:
        fail("both primary actors must appear in first_stage_actor_repetitions")

    experts = lock["expert_actor_ids"]
    if (
        not isinstance(experts, list)
        or len(experts) < 2
        or len(experts) != len(set(experts))
        or any(not isinstance(item, str) or not item for item in experts)
    ):
        fail("expert_actor_ids must contain at least two unique actor IDs")
    if set(experts) & set(repetitions):
        fail("expert actors and first-stage actors must be disjoint")

    files = lock["files"]
    if not isinstance(files, dict) or set(files) != LOCK_FILE_KEYS:
        fail(f"files must contain exactly {sorted(LOCK_FILE_KEYS)}")
    for name, descriptor in files.items():
        descriptor = require_exact_fields(descriptor, {"path", "sha256"}, f"files.{name}")
        require_nonempty_string(descriptor["path"], f"files.{name}.path")
        require_hash(descriptor["sha256"], f"files.{name}.sha256")
    return lock


def resolve_locked_path(lock_dir: Path, raw_path: str, label: str) -> Path:
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (lock_dir / candidate).resolve()
    if has_forbidden_path_component(resolved):
        fail(f"{label} contains a forbidden dataset path component")
    if not is_relative_to(resolved, lock_dir.resolve()):
        fail(f"{label} must remain inside the locked run directory")
    if not resolved.is_file():
        fail(f"{label} does not exist: {resolved}")
    return resolved


def build_frozen_item_bindings(evaluator_bytes: bytes) -> dict[str, dict[str, str]]:
    items = read_jsonl_bytes(evaluator_bytes, "frozen evaluator bank")
    if not items:
        fail("frozen evaluator bank is empty")
    guide_sha256 = checked_in_rater_guide_sha256()
    bindings: dict[str, dict[str, str]] = {}
    for index, item in enumerate(items, start=1):
        label = f"frozen evaluator item[{index}]"
        for field in ["item_id", "packet_id", "output_id", "corpus_id"]:
            require_nonempty_string(item.get(field), f"{label}.{field}")
        item_id = item["item_id"]
        if ITEM_RE.fullmatch(item_id) is None:
            fail(f"{label}.item_id does not match the Direction J opaque-item format")
        if item_id in bindings:
            fail(f"duplicate item_id in frozen evaluator bank: {item_id}")
        item_payload_sha256 = sha256_bytes(canonical_bytes(item))
        bindings[item_id] = {
            "item_id": item_id,
            "packet_id": item["packet_id"],
            "output_id": item["output_id"],
            "corpus_id": item["corpus_id"],
            "item_payload_sha256": item_payload_sha256,
            "interface_version": INTERFACE_VERSION,
            "shared_rater_guide_version": RATER_GUIDE_VERSION,
            "shared_rater_guide_sha256": guide_sha256,
            "semantic_input_sha256": canonical_semantic_input_sha256(
                item_payload_sha256, guide_sha256
            ),
        }
    return bindings


def build_frozen_assignment_bindings(
    build: Mapping[str, Any],
    run_manifest: Mapping[str, Any],
    item_bindings: Mapping[str, Mapping[str, str]],
) -> tuple[dict[str, dict[str, dict[str, dict[str, str]]]], dict[str, str]]:
    reports = build.get("assignment_files")
    if not isinstance(reports, dict) or not reports:
        fail("synthetic build report lacks frozen assignment manifests")
    if run_manifest.get("assignment_manifest_count") != len(reports):
        fail("run manifest assignment count differs from the synthetic build report")
    assignment_dir = FROZEN_RUN_ROOT / "assignments"
    bindings: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    observed_hashes: dict[str, str] = {}
    assignment_ids: set[str] = set()
    for filename in sorted(reports):
        if Path(filename).name != filename or re.fullmatch(
            r"[A-Za-z0-9_]+_rep[1-9][0-9]*\.csv", filename
        ) is None:
            fail(f"invalid frozen assignment filename: {filename}")
        report = reports[filename]
        if not isinstance(report, dict) or set(report) != {"rows", "sha256"}:
            fail(f"frozen assignment report has invalid fields: {filename}")
        path = assignment_dir / filename
        if not path.is_file():
            fail(f"frozen assignment is missing: {path}")
        data = path.read_bytes()
        observed_hash = sha256_bytes(data)
        if observed_hash != report["sha256"]:
            fail(f"frozen assignment SHA-256 differs from its build receipt: {filename}")
        observed_hashes[filename] = observed_hash
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AnalysisInputError(f"frozen assignment is not UTF-8: {filename}") from error
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames is None or set(reader.fieldnames) != ASSIGNMENT_FIELDS:
            fail(f"frozen assignment fields differ from the shared interface: {filename}")
        rows = list(reader)
        try:
            expected_rows = int(report["rows"])
        except (TypeError, ValueError) as error:
            raise AnalysisInputError(
                f"frozen assignment row receipt is invalid: {filename}"
            ) from error
        if expected_rows != len(rows) or len(rows) != len(item_bindings):
            fail(f"frozen assignment does not contain the complete evaluator bank: {filename}")
        file_actor: str | None = None
        file_repetition: int | None = None
        seen_items: set[str] = set()
        sequences: set[int] = set()
        for row_index, row in enumerate(rows, start=1):
            label = f"{filename}:{row_index + 1}"
            if set(row) != ASSIGNMENT_FIELDS or any(value is None for value in row.values()):
                fail(f"{label} fields differ from the frozen assignment contract")
            actor_id = require_nonempty_string(row["actor_id"], f"{label}.actor_id")
            actor_kind = row["actor_kind"]
            if actor_kind not in {"human", "llm"}:
                fail(f"{label}.actor_kind is invalid")
            try:
                repetition = int(row["rating_repetition"])
                sequence = int(row["sequence"])
            except ValueError as error:
                raise AnalysisInputError(f"{label} repetition/sequence is invalid") from error
            if repetition < 1 or sequence < 1:
                fail(f"{label} repetition/sequence must be positive")
            if file_actor is None:
                file_actor = actor_id
                file_repetition = repetition
            elif actor_id != file_actor or repetition != file_repetition:
                fail(f"{filename} mixes actors or rating repetitions")
            if filename != f"{actor_id}_rep{repetition}.csv":
                fail(f"{label} actor/repetition differs from its assignment filename")
            item_id = row["item_id"]
            if item_id in seen_items or item_id not in item_bindings:
                fail(f"{label} item is duplicated or absent from the frozen evaluator bank")
            seen_items.add(item_id)
            sequences.add(sequence)
            assignment_id = require_nonempty_string(
                row["assignment_id"], f"{label}.assignment_id"
            )
            if assignment_id in assignment_ids:
                fail(f"duplicate frozen assignment_id: {assignment_id}")
            assignment_ids.add(assignment_id)
            expected_item = item_bindings[item_id]
            for field in FROZEN_ITEM_BINDING_FIELDS:
                if row[field] != expected_item[field]:
                    fail(f"{label}.{field} differs from the frozen evaluator bank")
            if row["evaluation_role"] != SYNTHETIC_ROLE:
                fail(f"{label}.evaluation_role is not synthetic_qualification")
            actor_bindings = bindings.setdefault(actor_id, {})
            repetition_bindings = actor_bindings.setdefault(str(repetition), {})
            repetition_bindings[item_id] = {
                **{field: row[field] for field in FROZEN_ITEM_BINDING_FIELDS},
                "actor_kind": actor_kind,
                "assignment_id": assignment_id,
                "sequence": str(sequence),
            }
        if seen_items != set(item_bindings) or sequences != set(range(1, len(rows) + 1)):
            fail(f"{filename} is not a complete one-to-one frozen assignment")
    return bindings, observed_hashes


def validate_frozen_source_lineage(
    lock_dir: Path, run_manifest: Mapping[str, Any]
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, str]],
    dict[str, dict[str, dict[str, dict[str, str]]]],
]:
    """Bind analysis to the one frozen fictional bank and its source receipt."""

    if lock_dir.resolve() != FROZEN_RUN_ROOT.resolve():
        fail(f"analysis lock must live directly in the frozen run {FROZEN_RUN_ID}")
    for path, label in (
        (FREEZE_PATH, "Direction J freeze"),
        (BUILD_REPORT_PATH, "synthetic build report"),
        (EVALUATOR_ITEMS_PATH, "frozen evaluator bank"),
    ):
        if not path.is_file():
            fail(f"{label} is missing: {path}")

    freeze_bytes = FREEZE_PATH.read_bytes()
    build_bytes = BUILD_REPORT_PATH.read_bytes()
    evaluator_bytes = EVALUATOR_ITEMS_PATH.read_bytes()
    freeze_sha256 = sha256_bytes(freeze_bytes)
    build_sha256 = sha256_bytes(build_bytes)
    evaluator_sha256 = sha256_bytes(evaluator_bytes)
    freeze = read_json_bytes(freeze_bytes, "Direction J freeze")
    build = read_json_bytes(build_bytes, "synthetic build report")
    if not isinstance(freeze, dict) or not isinstance(build, dict):
        fail("frozen lineage records must be JSON objects")

    if run_manifest.get("run_id") != FROZEN_RUN_ID:
        fail("run manifest is not the frozen Direction J synthetic run")
    if run_manifest.get("freeze_path") != "../../config/freeze_v1.json":
        fail("run manifest freeze path changed")
    if run_manifest.get("freeze_sha256") != freeze_sha256:
        fail("run manifest is not bound to the current Direction J freeze")
    if run_manifest.get("build_report_sha256") != build_sha256:
        fail("run manifest is not bound to the frozen synthetic build report")
    if run_manifest.get("evaluator_items_sha256") != evaluator_sha256:
        fail("run manifest is not bound to the frozen evaluator bank")
    if build.get("output_hashes", {}).get("evaluator_items.jsonl") != evaluator_sha256:
        fail("build report evaluator-bank hash differs from the frozen bank")
    if build.get("input_hashes", {}).get("direction_j_freeze") != freeze_sha256:
        fail("build report is not bound to the current Direction J freeze")

    source_receipt = build.get("source_receipt")
    if not isinstance(source_receipt, dict):
        fail("build report lacks a synthetic source receipt")
    source_receipt_sha256 = sha256_bytes(canonical_bytes(source_receipt))
    if build.get("source_receipt_sha256") != source_receipt_sha256:
        fail("synthetic source receipt hash differs from its canonical contents")
    if run_manifest.get("source_receipt_sha256") != source_receipt_sha256:
        fail("run manifest is not bound to the synthetic source receipt")
    if (
        source_receipt.get("independently_authored_fictional_text") is not True
        or source_receipt.get("contains_real_source_text") is not False
    ):
        fail("synthetic source receipt lacks fail-closed fictional provenance")
    frozen_sources = freeze.get("source_evidence", {})
    if (
        source_receipt.get("baseline_run_manifest_sha256")
        != frozen_sources.get("legacy_run_manifest", {}).get("sha256")
        or build.get("input_hashes", {}).get("baseline_run_manifest")
        != frozen_sources.get("legacy_run_manifest", {}).get("sha256")
        or build.get("input_hashes", {}).get("baseline_blind_map")
        != frozen_sources.get("legacy_private_blind_map", {}).get("sha256")
        or build.get("input_hashes", {}).get("synthetic_benchmark")
        != frozen_sources.get("synthetic_benchmark", {}).get("sha256")
        or build.get("input_hashes", {}).get("blinded_bundle_fileset")
        != frozen_sources.get("blinded_bundle_fileset_sha256")
        or build.get("input_hashes", {}).get("shared_rater_guide")
        != checked_in_rater_guide_sha256()
    ):
        fail("synthetic build inputs differ from the frozen source and guide lineage")
    if (
        source_receipt.get("synthetic_benchmark_sha256")
        != frozen_sources.get("synthetic_benchmark", {}).get("sha256")
        or source_receipt.get("blinded_bundle_fileset_sha256")
        != frozen_sources.get("blinded_bundle_fileset_sha256")
        or source_receipt.get("blinded_bundle_sha256")
        != frozen_sources.get("blinded_bundle_sha256")
    ):
        fail("synthetic source receipt differs from the frozen input lineage")
    if (
        freeze.get("scope", {}).get("contains_real_source_text") is not False
        or freeze.get("scope", {}).get("runnable_lane")
        != "synthetic_qualification_only"
    ):
        fail("current Direction J freeze is not synthetic-only")
    item_bindings = build_frozen_item_bindings(evaluator_bytes)
    assignment_bindings, assignment_hashes = build_frozen_assignment_bindings(
        build, run_manifest, item_bindings
    )
    guide_sha256 = checked_in_rater_guide_sha256()
    if (
        run_manifest.get("interface_version") != INTERFACE_VERSION
        or run_manifest.get("shared_rater_guide_version") != RATER_GUIDE_VERSION
        or run_manifest.get("shared_rater_guide_sha256") != guide_sha256
        or run_manifest.get("semantic_input_hash_rule") != "canonical_manifest_v1"
    ):
        fail("run manifest does not bind the shared semantic-input contract")
    summary: dict[str, Any] = {
        "run_id": FROZEN_RUN_ID,
        "freeze_sha256": freeze_sha256,
        "build_report_sha256": build_sha256,
        "evaluator_items_sha256": evaluator_sha256,
        "source_receipt_sha256": source_receipt_sha256,
        "frozen_item_count": len(item_bindings),
        "assignment_manifest_count": len(assignment_hashes),
        "assignment_fileset_sha256": sha256_bytes(canonical_bytes(assignment_hashes)),
    }
    return summary, item_bindings, assignment_bindings


def load_locked_inputs(lock_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved_lock = lock_path.resolve()
    if has_forbidden_path_component(resolved_lock):
        fail("lock manifest path contains a forbidden dataset component")
    if not is_relative_to(resolved_lock, RUNS_ROOT.resolve()):
        fail("lock manifest must live under experiments/direction_j_llm_as_rater/runs")
    if not resolved_lock.is_file():
        fail(f"lock manifest does not exist: {resolved_lock}")
    lock_bytes = resolved_lock.read_bytes()
    lock = validate_lock(read_json_bytes(lock_bytes, "analysis input lock"))
    lock_dir = resolved_lock.parent

    loaded: dict[str, Any] = {}
    input_files: dict[str, dict[str, str]] = {}
    source_lineage: dict[str, Any] | None = None
    frozen_item_bindings: dict[str, dict[str, str]] | None = None
    frozen_assignment_bindings: (
        dict[str, dict[str, dict[str, dict[str, str]]]] | None
    ) = None
    for name in (
        "run_manifest",
        "actor_registry",
        "observations",
        "expert_adjudications",
    ):
        descriptor = lock["files"][name]
        path = resolve_locked_path(lock_dir, descriptor["path"], f"files.{name}.path")
        data = path.read_bytes()
        observed = sha256_bytes(data)
        if observed != descriptor["sha256"]:
            fail(f"files.{name} SHA-256 differs from the locked digest")
        if name in {"observations", "expert_adjudications"}:
            loaded[name] = read_jsonl_bytes(data, name)
        else:
            loaded[name] = read_json_bytes(data, name)
        input_files[name] = {
            "path": path.relative_to(lock_dir).as_posix(),
            "sha256": observed,
        }
        if name == "run_manifest":
            (
                source_lineage,
                frozen_item_bindings,
                frozen_assignment_bindings,
            ) = validate_frozen_source_lineage(
                lock_dir, loaded["run_manifest"]
            )
    if (
        source_lineage is None
        or frozen_item_bindings is None
        or frozen_assignment_bindings is None
    ):
        fail("frozen source lineage was not checked before analysis inputs")
    loaded["frozen_item_bindings"] = frozen_item_bindings
    loaded["frozen_assignment_bindings"] = frozen_assignment_bindings
    loaded["input_provenance"] = {
        "analysis_lock_path": resolved_lock.relative_to(lock_dir).as_posix(),
        "analysis_lock_sha256": sha256_bytes(lock_bytes),
        "locked_files": input_files,
        "frozen_source_lineage": source_lineage,
    }
    return lock, loaded


def validate_actor_registry(registry: Any) -> dict[str, dict[str, Any]]:
    registry = require_exact_fields(
        registry,
        {"actor_registry_schema_version", "registry_id", "frozen_at_utc", "actors"},
        "actor registry",
    )
    if registry["actor_registry_schema_version"] != ACTOR_REGISTRY_VERSION:
        fail("actor registry version mismatch")
    require_nonempty_string(registry["registry_id"], "actor registry ID")
    parse_datetime(registry["frozen_at_utc"], "actor registry frozen_at_utc")
    if not isinstance(registry["actors"], list) or not registry["actors"]:
        fail("actor registry must contain actors")
    actors: dict[str, dict[str, Any]] = {}
    for index, actor in enumerate(registry["actors"], start=1):
        if not isinstance(actor, dict):
            fail(f"actor {index} must be an object")
        required = {"actor_id", "actor_kind", "analysis_status", "exclusion_reason"}
        optional = {"human_profile", "llm_profile"}
        if not required <= set(actor) or set(actor) - required - optional:
            fail(f"actor {index} fields differ from the actor registry contract")
        actor_id = require_nonempty_string(actor["actor_id"], f"actor {index} ID")
        if actor_id in actors:
            fail(f"duplicate actor_id: {actor_id}")
        if actor["actor_kind"] not in {"human", "llm"}:
            fail(f"actor {actor_id} has invalid actor_kind")
        if actor["analysis_status"] not in {"primary", "sensitivity_only", "excluded"}:
            fail(f"actor {actor_id} has invalid analysis_status")
        if actor["analysis_status"] == "excluded":
            require_nonempty_string(actor["exclusion_reason"], f"actor {actor_id} exclusion_reason")
        elif actor["exclusion_reason"] is not None:
            fail(f"nonexcluded actor {actor_id} must have exclusion_reason=null")
        if actor["actor_kind"] == "human":
            if "human_profile" not in actor or "llm_profile" in actor:
                fail(f"human actor {actor_id} must have only human_profile")
            profile = actor["human_profile"]
            required_profile = {
                "evaluator_group",
                "helped_construct",
                "independence_eligibility",
                "qualifications_recorded",
                "tutorial_version",
                "comprehension_check_status",
                "corpus_familiarity",
            }
            require_exact_fields(profile, required_profile, f"human profile {actor_id}")
            if profile["evaluator_group"] not in {
                "researcher",
                "qualitative_methods_expert",
                "domain_expert",
                "dual_expertise",
            }:
                fail(f"human actor {actor_id} has invalid evaluator_group")
        else:
            if "llm_profile" not in actor or "human_profile" in actor:
                fail(f"LLM actor {actor_id} must have only llm_profile")
            required_profile = {
                "provider",
                "model_id",
                "model_family",
                "model_snapshot",
                "surface",
                "reasoning_mode",
                "reasoning_effort",
                "temperature",
                "top_p",
                "seed",
                "max_output_tokens",
                "response_count",
                "structured_output",
                "tools_enabled",
                "web_enabled",
                "function_calling_enabled",
                "retrieval_enabled",
                "url_context_enabled",
                "code_execution_enabled",
                "memory_enabled",
                "judge_role",
                "candidate_family_overlap",
                "data_processing_scope",
                "provider_processing_profile_id",
            }
            profile = require_exact_fields(actor["llm_profile"], required_profile, f"LLM profile {actor_id}")
            if profile["data_processing_scope"] != SYNTHETIC_SCOPE:
                fail(f"LLM actor {actor_id} is not restricted to synthetic_only")
            disabled_capabilities = [
                "tools_enabled",
                "web_enabled",
                "function_calling_enabled",
                "retrieval_enabled",
                "url_context_enabled",
                "code_execution_enabled",
                "memory_enabled",
            ]
            if any(profile[field] is not False for field in disabled_capabilities):
                fail(f"LLM actor {actor_id} must have external capabilities disabled")
            if profile["response_count"] != 1 or profile["structured_output"] is not True:
                fail(f"LLM actor {actor_id} must use one structured response")
            role = profile["judge_role"]
            overlap = profile["candidate_family_overlap"]
            if actor["analysis_status"] == "primary" and role != "primary":
                fail(f"primary LLM actor {actor_id} does not have judge_role=primary")
            if actor["analysis_status"] == "sensitivity_only" and role == "primary":
                fail(f"sensitivity-only LLM actor {actor_id} has judge_role=primary")
            if role in {"primary", "cross_family_sensitivity"} and overlap is not False:
                fail(f"LLM actor {actor_id} has contradictory family-overlap metadata")
            if role == "same_family_sensitivity" and overlap is not True:
                fail(f"LLM actor {actor_id} has contradictory family-overlap metadata")
            for field in ["provider", "model_id", "model_family", "model_snapshot", "surface", "provider_processing_profile_id"]:
                require_nonempty_string(profile[field], f"LLM actor {actor_id} {field}")
        actors[actor_id] = actor
    return actors


def validate_rating(rating: Any, label: str) -> dict[str, Any]:
    rating = require_exact_fields(rating, RATING_FIELDS, label)
    if rating["rating_schema_version"] != RATING_VERSION:
        fail(f"{label} has the wrong rating_schema_version")
    cannot = rating["cannot_judge"]
    if (
        not isinstance(cannot, list)
        or len(cannot) != len(set(cannot))
        or any(field not in CONSTRUCTS for field in cannot)
    ):
        fail(f"{label}.cannot_judge is invalid")
    for construct in CONSTRUCTS:
        value = rating[construct]
        if construct in cannot:
            if value is not None:
                fail(f"{label}.{construct} must be null when cannot_judge contains it")
        elif not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            fail(f"{label}.{construct} must be an integer 1-5 when evaluable")
    confidence = rating["confidence"]
    if not isinstance(confidence, int) or isinstance(confidence, bool) or not 1 <= confidence <= 5:
        fail(f"{label}.confidence must be an integer 1-5")
    if rating["disposition"] not in DISPOSITIONS:
        fail(f"{label}.disposition is invalid")
    if rating["requested_expertise"] not in REQUESTED_EXPERTISE:
        fail(f"{label}.requested_expertise is invalid")
    if cannot and rating["disposition"] != "escalate":
        fail(f"{label} abstains but does not escalate")
    if rating["disposition"] == "escalate":
        if rating["requested_expertise"] == "none":
            fail(f"{label} escalates without requested expertise")
    elif rating["requested_expertise"] != "none":
        fail(f"{label} requests expertise without escalation")
    flags = rating["serious_error_flags"]
    if (
        not isinstance(flags, list)
        or len(flags) != len(set(flags))
        or any(flag not in SERIOUS_ERROR_FLAGS for flag in flags)
    ):
        fail(f"{label}.serious_error_flags is invalid")
    if flags and rating["disposition"] not in {"revise", "reject", "escalate"}:
        fail(f"{label} reports a serious error but has an accept disposition")
    if rating["disposition"] == "accept":
        if flags or any(rating[construct] is None or rating[construct] < 4 for construct in CONSTRUCTS):
            fail(f"{label} accept requires three evaluable ratings of 4-5 and no serious errors")
    require_nonempty_string(rating["rationale"], f"{label}.rationale", maximum=1000)
    return rating


def validate_nullable_string(value: Any, label: str) -> None:
    if value is not None:
        require_nonempty_string(value, label)


def validate_nullable_nonnegative_integer(value: Any, label: str) -> None:
    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool) or value < 0
    ):
        fail(f"{label} must be null or a nonnegative integer")


def validate_attempt(
    attempt: Any,
    label: str,
    expected_index: int,
    observation_started: datetime,
    observation_completed: datetime,
) -> dict[str, Any]:
    attempt = require_exact_fields(attempt, ATTEMPT_FIELDS, label)
    if attempt["attempt_index"] != expected_index:
        fail(f"{label}.attempt_index must be {expected_index}")
    expected_kind = "initial" if expected_index == 1 else "format_only_repair"
    if attempt["attempt_kind"] != expected_kind:
        fail(f"{label}.attempt_kind must be {expected_kind}")
    started = parse_datetime(attempt["started_at_utc"], f"{label}.started_at_utc")
    completed = parse_datetime(attempt["completed_at_utc"], f"{label}.completed_at_utc")
    if completed < started:
        fail(f"{label} completed before it started")
    if started < observation_started or completed > observation_completed:
        fail(f"{label} timestamps fall outside the observation timing envelope")
    status = attempt["attempt_status"]
    if status not in ATTEMPT_STATUSES:
        fail(f"{label}.attempt_status is invalid")
    require_nonempty_string(attempt["raw_request_artifact_id"], f"{label}.raw_request_artifact_id")
    require_hash(attempt["raw_request_sha256"], f"{label}.raw_request_sha256")
    for field in [
        "raw_response_artifact_id",
        "provider_request_id",
        "provider_response_id",
        "provider_returned_model_id",
        "provider_returned_model_version",
        "provider_region",
        "finish_reason",
    ]:
        validate_nullable_string(attempt[field], f"{label}.{field}")
    response_id = attempt["raw_response_artifact_id"]
    response_hash = attempt["raw_response_sha256"]
    if (response_id is None) != (response_hash is None):
        fail(f"{label} raw response ID and hash must be jointly present or jointly null")
    if response_hash is not None:
        require_hash(response_hash, f"{label}.raw_response_sha256")
    if status in {"schema_valid_output", "invalid_json", "invalid_schema", "content_filtered"}:
        if response_id is None:
            fail(f"{label} status {status} requires a stored raw response")
    if attempt["filter_status"] not in FILTER_STATUSES:
        fail(f"{label}.filter_status is invalid")
    if status == "content_filtered":
        if attempt["filter_status"] not in {"partially_filtered", "filtered"}:
            fail(f"{label} content_filtered requires a filtered filter_status")
    elif attempt["filter_status"] not in {"not_reported", "not_filtered"}:
        fail(f"{label} non-filter terminal state cannot report filtered content")
    schema_error = attempt["schema_error_summary"]
    if status in {"invalid_json", "invalid_schema"}:
        require_nonempty_string(schema_error, f"{label}.schema_error_summary", maximum=2000)
    elif schema_error is not None:
        fail(f"{label}.schema_error_summary must be null outside JSON/schema failures")

    for flag in ["token_usage_available", "reasoning_tokens_available"]:
        if not isinstance(attempt[flag], bool):
            fail(f"{label}.{flag} must be boolean")
    token_fields = ["input_tokens", "output_tokens", "cached_input_tokens"]
    if attempt["token_usage_available"]:
        for field in ["input_tokens", "output_tokens"]:
            value = attempt[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                fail(f"{label}.{field} must be a nonnegative integer when usage is available")
        validate_nullable_nonnegative_integer(
            attempt["cached_input_tokens"], f"{label}.cached_input_tokens"
        )
    else:
        if any(attempt[field] is not None for field in token_fields):
            fail(f"{label} has token values while token_usage_available=false")
        if attempt["reasoning_tokens_available"] is not False:
            fail(f"{label} cannot expose reasoning tokens without aggregate token usage")
    if attempt["reasoning_tokens_available"]:
        if not attempt["token_usage_available"]:
            fail(f"{label} reasoning token availability requires token usage availability")
        value = attempt["reasoning_tokens"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail(f"{label}.reasoning_tokens must be a nonnegative integer when available")
    elif attempt["reasoning_tokens"] is not None:
        fail(f"{label} has reasoning_tokens while reasoning_tokens_available=false")
    return attempt


def validate_execution(
    execution: Any,
    actor_kind: str,
    observation_status: str,
    observation_started: datetime,
    observation_completed: datetime,
    label: str,
) -> dict[str, Any]:
    execution = require_exact_fields(execution, EXECUTION_FIELDS, label)
    retry_count = execution["retry_count"]
    if (
        not isinstance(retry_count, int)
        or isinstance(retry_count, bool)
        or retry_count not in {0, 1}
    ):
        fail(f"{label}.retry_count must be 0 or 1")
    attempts = execution["attempts"]
    if not isinstance(attempts, list) or len(attempts) > 2:
        fail(f"{label}.attempts must be an array with at most two calls")
    if actor_kind == "human":
        if observation_status != "valid" or retry_count != 0 or attempts:
            fail(f"{label} human execution must be valid with zero retries and no provider attempts")
    else:
        if len(attempts) != retry_count + 1:
            fail(f"{label} LLM attempts must equal retry_count + 1")
    validated_attempts = [
        validate_attempt(
            attempt,
            f"{label}.attempts[{index}]",
            index,
            observation_started,
            observation_completed,
        )
        for index, attempt in enumerate(attempts, start=1)
    ]
    for previous, current in zip(validated_attempts, validated_attempts[1:]):
        previous_completed = parse_datetime(previous["completed_at_utc"], "previous attempt completion")
        current_started = parse_datetime(current["started_at_utc"], "current attempt start")
        if current_started < previous_completed:
            fail(f"{label}.attempts overlap or are out of order")
    if retry_count == 1 and validated_attempts[0]["attempt_status"] not in {
        "invalid_json",
        "invalid_schema",
    }:
        fail(f"{label} format-only repair is allowed only after invalid JSON/schema")
    if actor_kind == "llm":
        final_status = validated_attempts[-1]["attempt_status"]
        expected_final = {
            "valid": {"schema_valid_output"},
            "invalid_output": {"invalid_json", "invalid_schema"},
            "timeout": {"timeout"},
            "provider_error": {"provider_error"},
            "content_filtered": {"content_filtered"},
        }[observation_status]
        if final_status not in expected_final:
            fail(f"{label} final attempt does not match observation_status={observation_status}")

    for flag in ["token_usage_available", "reasoning_tokens_available", "cost_available"]:
        if not isinstance(execution[flag], bool):
            fail(f"{label}.{flag} must be boolean")
    token_fields = ["input_tokens", "output_tokens", "cached_input_tokens"]
    if execution["token_usage_available"]:
        for field in ["input_tokens", "output_tokens"]:
            value = execution[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                fail(f"{label}.{field} must be a nonnegative integer when usage is available")
        validate_nullable_nonnegative_integer(
            execution["cached_input_tokens"], f"{label}.cached_input_tokens"
        )
        if any(not attempt["token_usage_available"] for attempt in validated_attempts):
            fail(f"{label} aggregate token usage requires usage for every attempt")
        for field in ["input_tokens", "output_tokens"]:
            if execution[field] != sum(attempt[field] for attempt in validated_attempts):
                fail(f"{label}.{field} does not equal the sum across attempts")
        cached_values = [attempt["cached_input_tokens"] for attempt in validated_attempts]
        if execution["cached_input_tokens"] is not None:
            if any(value is None for value in cached_values) or execution[
                "cached_input_tokens"
            ] != sum(cached_values):
                fail(f"{label}.cached_input_tokens is not a valid complete attempt sum")
    elif any(execution[field] is not None for field in token_fields):
        fail(f"{label} has token values while token_usage_available=false")
    if execution["reasoning_tokens_available"]:
        if not execution["token_usage_available"]:
            fail(f"{label} reasoning token availability requires token usage availability")
        if any(not attempt["reasoning_tokens_available"] for attempt in validated_attempts):
            fail(f"{label} aggregate reasoning usage requires reasoning usage for every attempt")
        value = execution["reasoning_tokens"]
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value != sum(attempt["reasoning_tokens"] for attempt in validated_attempts)
        ):
            fail(f"{label}.reasoning_tokens does not equal the complete attempt sum")
    elif execution["reasoning_tokens"] is not None:
        fail(f"{label} has reasoning_tokens while reasoning_tokens_available=false")
    if not execution["token_usage_available"] and execution["reasoning_tokens_available"]:
        fail(f"{label} cannot expose aggregate reasoning usage without aggregate token usage")
    if execution["cost_available"]:
        if not is_number(execution["cost_amount"]) or execution["cost_amount"] < 0:
            fail(f"{label}.cost_amount must be nonnegative when cost is available")
        if (
            not isinstance(execution["cost_currency"], str)
            or re.fullmatch(r"[A-Z]{3}", execution["cost_currency"]) is None
        ):
            fail(f"{label}.cost_currency must be an ISO-like three-letter code")
        require_nonempty_string(execution["pricing_snapshot_id"], f"{label}.pricing_snapshot_id")
    elif any(
        execution[field] is not None
        for field in ["cost_amount", "cost_currency", "pricing_snapshot_id"]
    ):
        fail(f"{label} has cost values while cost_available=false")
    return execution


def validate_observation(
    observation: Any,
    actors: Mapping[str, dict[str, Any]],
    lock: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    observation = require_exact_fields(observation, OBSERVATION_FIELDS, label)
    if observation["observation_schema_version"] != OBSERVATION_VERSION:
        fail(f"{label} has the wrong observation_schema_version")
    if observation["study_id"] != lock["study_id"]:
        fail(f"{label} study_id differs from the lock")
    if observation["evaluation_role"] != SYNTHETIC_ROLE:
        fail(f"{label} is not a synthetic_qualification observation")
    for field in ["observation_id", "item_id", "packet_id", "output_id", "corpus_id", "candidate_generation_run_id", "actor_id", "prompt_or_instrument_version"]:
        require_nonempty_string(observation[field], f"{label}.{field}")
    if ITEM_RE.fullmatch(observation["item_id"]) is None:
        fail(f"{label}.item_id does not match the Direction J opaque-item format")
    if observation["actor_id"] not in actors:
        fail(f"{label} references an unknown actor")
    if observation["actor_kind"] != actors[observation["actor_id"]]["actor_kind"]:
        fail(f"{label} actor_kind differs from the actor registry")
    for field in ["candidate_generation_repetition", "rating_repetition"]:
        value = observation[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            fail(f"{label}.{field} must be a positive integer")
    require_hash(observation["item_payload_sha256"], f"{label}.item_payload_sha256")
    require_hash(
        observation["shared_rater_guide_sha256"],
        f"{label}.shared_rater_guide_sha256",
    )
    require_hash(observation["semantic_input_sha256"], f"{label}.semantic_input_sha256")
    expected_guide_hash = checked_in_rater_guide_sha256()
    if observation["shared_rater_guide_sha256"] != expected_guide_hash:
        fail(f"{label}.shared_rater_guide_sha256 differs from the checked-in complete guide bytes")
    expected_semantic_hash = canonical_semantic_input_sha256(
        observation["item_payload_sha256"], observation["shared_rater_guide_sha256"]
    )
    if observation["semantic_input_sha256"] != expected_semantic_hash:
        fail(f"{label}.semantic_input_sha256 differs from the frozen canonical manifest")
    require_hash(
        observation["prompt_or_instrument_sha256"],
        f"{label}.prompt_or_instrument_sha256",
    )
    if observation["interface_version"] != INTERFACE_VERSION:
        fail(f"{label} interface_version mismatch")
    if observation["shared_rater_guide_version"] != RATER_GUIDE_VERSION:
        fail(f"{label} shared_rater_guide_version mismatch")
    started = parse_datetime(observation["started_at_utc"], f"{label}.started_at_utc")
    completed = parse_datetime(observation["completed_at_utc"], f"{label}.completed_at_utc")
    if completed < started:
        fail(f"{label} completed before it started")
    if not is_number(observation["review_seconds"]) or observation["review_seconds"] < 0:
        fail(f"{label}.review_seconds must be a nonnegative finite number")
    status = observation["observation_status"]
    if status not in OBSERVATION_STATUSES:
        fail(f"{label}.observation_status is invalid")
    if status == "valid":
        validate_rating(observation["rating"], f"{label}.rating")
    elif observation["rating"] is not None:
        fail(f"{label}.rating must be null for terminal execution status {status}")

    blinding = require_exact_fields(observation["blinding"], BLINDING_FIELDS, f"{label}.blinding")
    require_nonempty_string(blinding["blind_id"], f"{label}.blinding.blind_id")
    for field in ["candidate_identity_hidden", "condition_hidden", "other_ratings_hidden"]:
        if blinding[field] is not True:
            fail(f"{label}.blinding.{field} must be true")
    if blinding["unblinded_at_utc"] is not None:
        unblinded = parse_datetime(blinding["unblinded_at_utc"], f"{label}.blinding.unblinded_at_utc")
        if unblinded < completed:
            fail(f"{label} was unblinded before completion")
    validate_execution(
        observation["execution"],
        observation["actor_kind"],
        status,
        started,
        completed,
        f"{label}.execution",
    )
    return observation


def validate_adjudication(value: Any, label: str) -> dict[str, Any]:
    value = require_exact_fields(value, ADJUDICATION_FIELDS, label)
    if value["adjudication_version"] != ADJUDICATION_VERSION:
        fail(f"{label} has the wrong adjudication_version")
    if not isinstance(value["item_id"], str) or ITEM_RE.fullmatch(value["item_id"]) is None:
        fail(f"{label}.item_id is invalid")
    require_nonempty_string(value["panel_id"], f"{label}.panel_id")
    ids = value["locked_individual_observation_ids"]
    if (
        not isinstance(ids, list)
        or len(ids) < 2
        or len(ids) != len(set(ids))
        or any(not isinstance(item, str) or not item for item in ids)
    ):
        fail(f"{label}.locked_individual_observation_ids must contain at least two unique IDs")
    parse_datetime(value["adjudicated_at_utc"], f"{label}.adjudicated_at_utc")
    if value["operational_action"] not in ADJUDICATED_ACTIONS:
        fail(f"{label}.operational_action is invalid")
    if value["severity"] not in SEVERITIES:
        fail(f"{label}.severity is invalid")
    if value["requested_expertise"] not in REQUESTED_EXPERTISE:
        fail(f"{label}.requested_expertise is invalid")
    action = value["operational_action"]
    if action == "accept":
        if value["severity"] not in {"none", "minor"} or value["requested_expertise"] != "none":
            fail(f"{label} accept action conflicts with severity or requested expertise")
    elif action == "expert_review":
        if value["severity"] not in {"material", "high_consequence"}:
            fail(f"{label} expert_review requires material or high_consequence severity")
        if value["requested_expertise"] == "none":
            fail(f"{label} expert_review requires requested expertise")
    elif value["requested_expertise"] == "none":
        fail(f"{label} plural_ambiguous requires requested expertise")
    flags = value["serious_error_flags"]
    if (
        not isinstance(flags, list)
        or len(flags) != len(set(flags))
        or any(flag not in SERIOUS_ERROR_FLAGS for flag in flags)
    ):
        fail(f"{label}.serious_error_flags is invalid")
    if not isinstance(value["error_locations"], list):
        fail(f"{label}.error_locations must be an array")
    for index, location in enumerate(value["error_locations"], start=1):
        location_label = f"{label}.error_locations[{index}]"
        location = require_exact_fields(
            location,
            {"flag", "excerpt_ids", "source_ids", "output_location", "explanation"},
            location_label,
        )
        if location["flag"] not in flags:
            fail(f"{location_label}.flag is absent from adjudicated serious_error_flags")
        for field in ["excerpt_ids", "source_ids"]:
            entries = location[field]
            if (
                not isinstance(entries, list)
                or len(entries) != len(set(entries))
                or any(not isinstance(item, str) or not item for item in entries)
            ):
                fail(f"{location_label}.{field} is invalid")
        if location["output_location"] is not None:
            require_nonempty_string(location["output_location"], f"{location_label}.output_location")
        require_nonempty_string(location["explanation"], f"{location_label}.explanation", maximum=2000)
    located_flags = {location["flag"] for location in value["error_locations"]}
    if located_flags != set(flags):
        fail(f"{label}.error_locations must cover every and only adjudicated error flag")
    require_nonempty_string(value["rationale"], f"{label}.rationale", maximum=4000)
    if value["locked_before_private_unblind"] is not True:
        fail(f"{label} was not locked before private unblinding")
    return value


def validate_run_manifest(
    manifest: Any,
    lock: Mapping[str, Any],
    observation_count: int,
) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        fail("run manifest must be an object")
    required = {
        "run_manifest_version",
        "run_id",
        "status",
        "study_id",
        "evaluation_role",
        "qualification_scope",
        "contains_real_source_text",
        "independently_authored_fictional_text",
        "freeze_path",
        "freeze_sha256",
        "build_report_sha256",
        "evaluator_items_sha256",
        "source_receipt_sha256",
        "synthetic_benchmark_sha256",
        "blinded_bundle_fileset_sha256",
        "ratings_collected",
        "outcomes_available",
        "expected_observations",
        "result_label",
    }
    missing = sorted(required - set(manifest))
    if missing:
        fail(f"run manifest is missing required analysis fields: {missing}")
    if manifest["status"] not in {"locked_for_analysis", "complete_locked"}:
        fail("run manifest is not locked_for_analysis or complete_locked")
    if manifest["run_id"] != FROZEN_RUN_ID:
        fail("run manifest run_id is not the frozen synthetic qualification")
    if manifest["study_id"] != lock["study_id"]:
        fail("run manifest study_id differs from the analysis lock")
    if manifest["evaluation_role"] != SYNTHETIC_ROLE:
        fail("run manifest evaluation_role is not synthetic_qualification")
    if manifest["qualification_scope"] != SYNTHETIC_SCOPE:
        fail("run manifest qualification_scope is not synthetic_only")
    if manifest["contains_real_source_text"] is not False:
        fail("run manifest does not explicitly exclude real source text")
    if manifest["independently_authored_fictional_text"] is not True:
        fail("run manifest lacks independent-fictional-authorship provenance")
    if manifest["result_label"] != SYNTHETIC_LABEL:
        fail("run manifest result label is not synthetic_qualification_only")
    if manifest["outcomes_available"] is not True:
        fail("run manifest says outcomes are unavailable")
    if manifest["ratings_collected"] != observation_count:
        fail("run manifest ratings_collected differs from the locked observation count")
    if not isinstance(manifest["expected_observations"], dict):
        fail("run manifest expected_observations must be an object")
    return manifest


def item_signature(observation: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        observation["study_id"],
        observation["item_id"],
        observation["packet_id"],
        observation["output_id"],
        observation["corpus_id"],
        observation["candidate_generation_run_id"],
        observation["candidate_generation_repetition"],
        observation["item_payload_sha256"],
        observation["interface_version"],
        observation["shared_rater_guide_version"],
        observation["shared_rater_guide_sha256"],
        observation["semantic_input_sha256"],
    )


def validate_complete_inputs(
    lock: Mapping[str, Any], loaded: Mapping[str, Any]
) -> dict[str, Any]:
    validate_frozen_schema_contract()
    actors = validate_actor_registry(loaded["actor_registry"])
    observations_raw = loaded["observations"]
    adjudications_raw = loaded["expert_adjudications"]
    if not isinstance(observations_raw, list):
        fail("locked observations must be a JSONL record sequence")
    if not isinstance(adjudications_raw, list):
        fail("locked expert adjudications must be a JSONL record sequence")
    if not observations_raw:
        fail("locked observations are absent; no results were emitted")
    if not adjudications_raw:
        fail("locked expert adjudications are absent; no results were emitted")
    frozen_item_bindings = loaded.get("frozen_item_bindings")
    frozen_assignment_bindings = loaded.get("frozen_assignment_bindings")
    if not isinstance(frozen_item_bindings, dict) or not frozen_item_bindings:
        fail("parsed frozen evaluator-bank bindings are absent")
    if not isinstance(frozen_assignment_bindings, dict) or not frozen_assignment_bindings:
        fail("parsed frozen assignment bindings are absent")
    run_manifest = validate_run_manifest(loaded["run_manifest"], lock, len(observations_raw))

    locked_at = parse_datetime(lock["locked_at_utc"], "analysis input lock locked_at_utc")
    registry_frozen_at = parse_datetime(
        loaded["actor_registry"]["frozen_at_utc"], "actor registry frozen_at_utc"
    )
    observations: list[dict[str, Any]] = []
    by_observation_id: dict[str, dict[str, Any]] = {}
    by_actor_rep_item: dict[tuple[str, int, str], dict[str, Any]] = {}
    signatures: dict[str, tuple[Any, ...]] = {}
    for index, raw in enumerate(observations_raw, start=1):
        observation = validate_observation(raw, actors, lock, f"observation[{index}]")
        observation_id = observation["observation_id"]
        frozen_item = frozen_item_bindings.get(observation["item_id"])
        if not isinstance(frozen_item, dict):
            fail(f"observation {observation_id} is absent from the frozen evaluator bank")
        for field in FROZEN_ITEM_BINDING_FIELDS:
            if observation[field] != frozen_item.get(field):
                fail(
                    f"observation {observation_id}.{field} differs from the frozen "
                    "evaluator bank"
                )
        assignment = (
            frozen_assignment_bindings.get(observation["actor_id"], {})
            .get(str(observation["rating_repetition"]), {})
            .get(observation["item_id"])
        )
        if not isinstance(assignment, dict):
            fail(
                f"observation {observation_id} is absent from its frozen "
                "actor/repetition assignment"
            )
        if assignment.get("actor_kind") != observation["actor_kind"]:
            fail(f"observation {observation_id} actor kind differs from its frozen assignment")
        for field in FROZEN_ITEM_BINDING_FIELDS:
            if observation[field] != assignment.get(field):
                fail(
                    f"observation {observation_id}.{field} differs from its frozen assignment"
                )
        if observation_id in by_observation_id:
            fail(f"duplicate observation_id: {observation_id}")
        key = (
            observation["actor_id"],
            observation["rating_repetition"],
            observation["item_id"],
        )
        if key in by_actor_rep_item:
            fail(f"duplicate actor/repetition/item observation: {key}")
        signature = item_signature(observation)
        prior = signatures.get(observation["item_id"])
        if prior is not None and prior != signature:
            fail(f"paired item identity/hash mismatch for {observation['item_id']}")
        signatures[observation["item_id"]] = signature
        if parse_datetime(observation["completed_at_utc"], f"observation[{index}].completed_at_utc") > locked_at:
            fail(f"observation {observation_id} completed after the analysis lock")
        if parse_datetime(observation["started_at_utc"], f"observation[{index}].started_at_utc") < registry_frozen_at:
            fail(f"observation {observation_id} started before the actor registry was frozen")
        observations.append(observation)
        by_observation_id[observation_id] = observation
        by_actor_rep_item[key] = observation

    repetitions = lock["first_stage_actor_repetitions"]
    expert_actor_ids = set(lock["expert_actor_ids"])
    for actor_id in list(repetitions) + list(expert_actor_ids):
        if actor_id not in actors:
            fail(f"locked actor {actor_id} is absent from the actor registry")
        if actors[actor_id]["analysis_status"] == "excluded":
            fail(f"locked analysis actor {actor_id} is excluded in the registry")
    pair = lock["primary_pair"]
    left_actor = pair["left_actor_id"]
    right_actor = pair["right_actor_id"]
    if actors[left_actor]["actor_kind"] != "human":
        fail("primary pair left actor must be registered as human")
    if actors[right_actor]["actor_kind"] != "llm":
        fail("primary pair right actor must be registered as llm")
    for expert_id in expert_actor_ids:
        actor = actors[expert_id]
        if actor["actor_kind"] != "human":
            fail(f"expert actor {expert_id} is not human")
        profile = actor["human_profile"]
        if profile["evaluator_group"] not in {
            "qualitative_methods_expert",
            "domain_expert",
            "dual_expertise",
        }:
            fail(f"expert actor {expert_id} lacks a recorded expert evaluator group")
        if profile["helped_construct"] is not False:
            fail(f"expert actor {expert_id} helped construct the rated items")
        if profile["independence_eligibility"] != "eligible_primary":
            fail(f"expert actor {expert_id} is not independently eligible")

    left_items = {
        item_id
        for actor_id, repetition, item_id in by_actor_rep_item
        if actor_id == left_actor and repetition == 1
    }
    right_items = {
        item_id
        for actor_id, repetition, item_id in by_actor_rep_item
        if actor_id == right_actor and repetition == 1
    }
    if left_items != right_items:
        fail("primary actors do not have the same complete item set")
    if len(left_items) != lock["expected_item_count"]:
        fail("complete primary pair count differs from expected_item_count")
    if left_items != set(frozen_item_bindings):
        fail("primary paired item set is not the complete frozen evaluator bank")
    if not left_items:
        fail("complete primary paired observations are absent")
    for actor_id, expected_repetitions in repetitions.items():
        observed_repetitions = {
            repetition
            for observed_actor, repetition, _item_id in by_actor_rep_item
            if observed_actor == actor_id
        }
        if observed_repetitions != set(expected_repetitions):
            fail(
                f"actor {actor_id} repetitions differ from the locked plan; "
                f"expected={expected_repetitions}; observed={sorted(observed_repetitions)}"
            )
        for repetition in expected_repetitions:
            item_set = {
                item_id
                for observed_actor, observed_rep, item_id in by_actor_rep_item
                if observed_actor == actor_id and observed_rep == repetition
            }
            if item_set != left_items:
                fail(f"actor {actor_id} repetition {repetition} is not complete on the paired item set")

    expected_observations = run_manifest["expected_observations"]
    actor_counts = Counter(observation["actor_id"] for observation in observations)
    for actor_id, expected in expected_observations.items():
        if isinstance(expected, int) and not isinstance(expected, bool):
            if actor_counts[actor_id] != expected:
                fail(
                    f"run manifest expected {expected} observations for {actor_id}, "
                    f"found {actor_counts[actor_id]}"
                )

    adjudications: list[dict[str, Any]] = []
    adjudication_by_item: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(adjudications_raw, start=1):
        adjudication = validate_adjudication(raw, f"adjudication[{index}]")
        item_id = adjudication["item_id"]
        if item_id in adjudication_by_item:
            fail(f"duplicate expert adjudication for {item_id}")
        adjudicated_at = parse_datetime(
            adjudication["adjudicated_at_utc"], f"adjudication[{index}].adjudicated_at_utc"
        )
        if adjudicated_at > locked_at:
            fail(f"adjudication for {item_id} occurred after the analysis lock")
        referenced_actors: set[str] = set()
        for observation_id in adjudication["locked_individual_observation_ids"]:
            if observation_id not in by_observation_id:
                fail(f"adjudication {item_id} references missing observation {observation_id}")
            expert_observation = by_observation_id[observation_id]
            if expert_observation["item_id"] != item_id:
                fail(f"adjudication {item_id} references an observation for another item")
            if expert_observation["actor_id"] not in expert_actor_ids:
                fail(f"adjudication {item_id} references a nonexpert actor")
            referenced_actors.add(expert_observation["actor_id"])
            completed = parse_datetime(
                expert_observation["completed_at_utc"],
                f"expert observation {observation_id}.completed_at_utc",
            )
            if completed > adjudicated_at:
                fail(f"adjudication {item_id} predates a locked individual expert rating")
            expert_unblinded_raw = expert_observation["blinding"]["unblinded_at_utc"]
            if expert_unblinded_raw is not None and parse_datetime(
                expert_unblinded_raw,
                f"expert observation {observation_id}.unblinded_at_utc",
            ) < adjudicated_at:
                fail(f"expert observation for {item_id} was unblinded before adjudication")
        if len(referenced_actors) < 2:
            fail(f"adjudication {item_id} lacks two distinct expert actors")
        for actor_id, repetitions_for_actor in repetitions.items():
            for repetition in repetitions_for_actor:
                first_stage = by_actor_rep_item[(actor_id, repetition, item_id)]
                completed = parse_datetime(
                    first_stage["completed_at_utc"],
                    f"first-stage observation {first_stage['observation_id']}.completed_at_utc",
                )
                if completed > adjudicated_at:
                    fail(f"adjudication {item_id} predates a first-stage observation")
                unblinded_raw = first_stage["blinding"]["unblinded_at_utc"]
                if unblinded_raw is not None and parse_datetime(
                    unblinded_raw,
                    f"first-stage observation {first_stage['observation_id']}.unblinded_at_utc",
                ) < adjudicated_at:
                    fail(f"first-stage observation for {item_id} was unblinded before adjudication")
        adjudications.append(adjudication)
        adjudication_by_item[item_id] = adjudication

    if set(adjudication_by_item) != left_items:
        missing = sorted(left_items - set(adjudication_by_item))
        extra = sorted(set(adjudication_by_item) - left_items)
        fail(f"expert adjudication set is not identical to the paired item set; missing={missing}; extra={extra}")

    return {
        "actors": actors,
        "observations": observations,
        "by_observation_id": by_observation_id,
        "by_actor_rep_item": by_actor_rep_item,
        "adjudications": adjudications,
        "adjudication_by_item": adjudication_by_item,
        "item_ids": sorted(left_items),
        "run_manifest": run_manifest,
        "actor_counts": dict(sorted(actor_counts.items())),
    }


def rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 12)


def rate(numerator: int, denominator: int) -> float | None:
    return rounded(numerator / denominator) if denominator else None


def mean(values: Sequence[float]) -> float | None:
    return rounded(statistics.fmean(values)) if values else None


def quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return rounded(ordered[lower])
    fraction = position - lower
    return rounded(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def numeric_summary(values: Iterable[float]) -> dict[str, Any]:
    finite = [float(value) for value in values if is_number(value)]
    return {
        "n": len(finite),
        "mean": mean(finite),
        "median": quantile(finite, 0.5),
        "q1": quantile(finite, 0.25),
        "q3": quantile(finite, 0.75),
        "p90": quantile(finite, 0.90),
        "p95": quantile(finite, 0.95),
        "minimum": rounded(min(finite)) if finite else None,
        "maximum": rounded(max(finite)) if finite else None,
        "total": rounded(sum(finite)) if finite else None,
    }


def quadratic_weighted_kappa(pairs: Sequence[tuple[int, int]]) -> float | None:
    if not pairs:
        return None
    categories = range(1, 6)
    observed = Counter(pairs)
    left = Counter(value for value, _ in pairs)
    right = Counter(value for _, value in pairs)
    n = len(pairs)
    observed_disagreement = sum(
        (((i - j) ** 2) / 16) * observed[(i, j)] for i in categories for j in categories
    ) / n
    expected_disagreement = sum(
        (((i - j) ** 2) / 16) * (left[i] * right[j] / n)
        for i in categories
        for j in categories
    ) / n
    if expected_disagreement == 0:
        return None
    return rounded(1 - observed_disagreement / expected_disagreement)


def cross_tab(left: Sequence[str], right: Sequence[str], values: Sequence[str]) -> dict[str, dict[str, int]]:
    counts = Counter(zip(left, right))
    return {
        left_value: {right_value: counts[(left_value, right_value)] for right_value in values}
        for left_value in values
    }


def construct_agreement(
    left_records: Sequence[Mapping[str, Any]],
    right_records: Sequence[Mapping[str, Any]],
    construct: str,
) -> dict[str, Any]:
    values: list[tuple[int, int]] = []
    left_evaluable: list[int] = []
    right_evaluable: list[int] = []
    left_abstain = 0
    right_abstain = 0
    left_terminal = 0
    right_terminal = 0
    both_valid = 0
    for left_record, right_record in zip(left_records, right_records):
        left_valid = is_valid_observation(left_record)
        right_valid = is_valid_observation(right_record)
        left_value = left_record["rating"][construct] if left_valid else None
        right_value = right_record["rating"][construct] if right_valid else None
        if not left_valid:
            left_terminal += 1
        elif left_value is None:
            left_abstain += 1
        else:
            left_evaluable.append(left_value)
        if not right_valid:
            right_terminal += 1
        elif right_value is None:
            right_abstain += 1
        else:
            right_evaluable.append(right_value)
        if left_valid and right_valid:
            both_valid += 1
        if left_valid and right_valid and left_value is not None and right_value is not None:
            values.append((left_value, right_value))
    differences = Counter(right - left for left, right in values)
    paired_left = [str(left) for left, _ in values]
    paired_right = [str(right) for _, right in values]
    cannot_judge_pairs = [
        (
            left_record["rating"][construct] is None,
            right_record["rating"][construct] is None,
        )
        for left_record, right_record in zip(left_records, right_records)
        if is_valid_observation(left_record) and is_valid_observation(right_record)
    ]
    cannot_judge_counts = Counter(cannot_judge_pairs)
    return {
        "construct": construct,
        "paired_item_count": len(left_records),
        "both_valid_observation_n": both_valid,
        "either_terminal_failure_n": sum(
            not is_valid_observation(left) or not is_valid_observation(right)
            for left, right in zip(left_records, right_records)
        ),
        "left_terminal_failure_n": left_terminal,
        "right_terminal_failure_n": right_terminal,
        "both_evaluable_n": len(values),
        "left_cannot_judge_n": left_abstain,
        "right_cannot_judge_n": right_abstain,
        "cannot_judge_agreement_among_both_valid": {
            "both_cannot_judge": cannot_judge_counts[(True, True)],
            "left_only_cannot_judge": cannot_judge_counts[(True, False)],
            "right_only_cannot_judge": cannot_judge_counts[(False, True)],
            "neither_cannot_judge": cannot_judge_counts[(False, False)],
            "agreement_rate": rate(
                cannot_judge_counts[(True, True)] + cannot_judge_counts[(False, False)],
                len(cannot_judge_pairs),
            ),
        },
        "left_adequacy": {
            "evaluable_n": len(left_evaluable),
            "adequate_n": sum(value >= 4 for value in left_evaluable),
            "adequacy_rate": rate(sum(value >= 4 for value in left_evaluable), len(left_evaluable)),
        },
        "right_adequacy": {
            "evaluable_n": len(right_evaluable),
            "adequate_n": sum(value >= 4 for value in right_evaluable),
            "adequacy_rate": rate(sum(value >= 4 for value in right_evaluable), len(right_evaluable)),
        },
        "exact_agreement_n": sum(left == right for left, right in values),
        "exact_agreement_rate": rate(sum(left == right for left, right in values), len(values)),
        "within_one_agreement_n": sum(abs(left - right) <= 1 for left, right in values),
        "within_one_agreement_rate": rate(
            sum(abs(left - right) <= 1 for left, right in values), len(values)
        ),
        "quadratic_weighted_kappa": quadratic_weighted_kappa(values),
        "mean_signed_difference_right_minus_left": mean([right - left for left, right in values]),
        "signed_difference_distribution": {
            str(value): differences[value] for value in range(-4, 5)
        },
        "cross_tabulation": cross_tab(paired_left, paired_right, [str(value) for value in range(1, 6)]),
    }


def collapse_disposition(value: str) -> str:
    return "pass" if value == "accept" else "needs_action"


def is_valid_observation(record: Mapping[str, Any]) -> bool:
    return record["observation_status"] == "valid"


def is_terminal_failure(record: Mapping[str, Any]) -> bool:
    return record["observation_status"] in TERMINAL_FAILURE_STATUSES


def operational_disposition(record: Mapping[str, Any]) -> str:
    """Map a terminal model execution to escalation without inventing a rating."""

    return record["rating"]["disposition"] if is_valid_observation(record) else "escalate"


def operational_flags(record: Mapping[str, Any]) -> set[str]:
    """Terminal failure detects no error family; the missing rating stays null."""

    return set(record["rating"]["serious_error_flags"]) if is_valid_observation(record) else set()


def observation_status_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(record["observation_status"] for record in records)
    return {status: counts[status] for status in OBSERVATION_STATUSES}


def disposition_agreement(
    left_records: Sequence[Mapping[str, Any]], right_records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    left = [operational_disposition(record) for record in left_records]
    right = [operational_disposition(record) for record in right_records]
    left_collapsed = [collapse_disposition(value) for value in left]
    right_collapsed = [collapse_disposition(value) for value in right]
    valid_pairs = [
        (left_record, right_record)
        for left_record, right_record in zip(left_records, right_records)
        if is_valid_observation(left_record) and is_valid_observation(right_record)
    ]
    explicit_escalation_pairs = [
        (
            left_record["rating"]["disposition"] == "escalate",
            right_record["rating"]["disposition"] == "escalate",
        )
        for left_record, right_record in valid_pairs
    ]
    operational_escalation_pairs = [
        (left_value == "escalate", right_value == "escalate")
        for left_value, right_value in zip(left, right)
    ]
    return {
        "paired_item_count": len(left),
        "terminal_failure_operational_mapping": "escalate; rating remains null",
        "left_observation_status_counts": observation_status_counts(left_records),
        "right_observation_status_counts": observation_status_counts(right_records),
        "both_valid_observation_n": len(valid_pairs),
        "submitted_disposition_exact_agreement_n_among_both_valid": sum(
            left_record["rating"]["disposition"] == right_record["rating"]["disposition"]
            for left_record, right_record in valid_pairs
        ),
        "submitted_disposition_exact_agreement_rate_among_both_valid": rate(
            sum(
                left_record["rating"]["disposition"] == right_record["rating"]["disposition"]
                for left_record, right_record in valid_pairs
            ),
            len(valid_pairs),
        ),
        "explicit_escalation_agreement_rate_among_both_valid": rate(
            sum(a == b for a, b in explicit_escalation_pairs),
            len(explicit_escalation_pairs),
        ),
        "operational_escalation_agreement_rate_all_pairs": rate(
            sum(a == b for a, b in operational_escalation_pairs),
            len(operational_escalation_pairs),
        ),
        "agreement_denominator": "all paired items using operational disposition",
        "exact_agreement_n": sum(a == b for a, b in zip(left, right)),
        "exact_agreement_rate": rate(sum(a == b for a, b in zip(left, right)), len(left)),
        "cross_tabulation": cross_tab(left, right, DISPOSITIONS),
        "pass_needs_action_agreement_n": sum(
            a == b for a, b in zip(left_collapsed, right_collapsed)
        ),
        "pass_needs_action_agreement_rate": rate(
            sum(a == b for a, b in zip(left_collapsed, right_collapsed)), len(left)
        ),
        "pass_needs_action_cross_tabulation": cross_tab(
            left_collapsed, right_collapsed, ["pass", "needs_action"]
        ),
    }


def positive_agreement(both: int, left_only: int, right_only: int) -> float | None:
    return rate(2 * both, 2 * both + left_only + right_only)


def flag_agreement(
    left_records: Sequence[Mapping[str, Any]], right_records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    per_flag: dict[str, Any] = {}
    item_jaccard: list[float] = []
    both_empty = 0
    valid_pair_jaccard: list[float] = []
    for left_record, right_record in zip(left_records, right_records):
        left_set = operational_flags(left_record)
        right_set = operational_flags(right_record)
        union = left_set | right_set
        if not union:
            both_empty += 1
            item_jaccard.append(1.0)
        else:
            item_jaccard.append(len(left_set & right_set) / len(union))
        if is_valid_observation(left_record) and is_valid_observation(right_record):
            valid_pair_jaccard.append(
                1.0 if not union else len(left_set & right_set) / len(union)
            )
    for flag in SERIOUS_ERROR_FLAGS:
        both = left_only = right_only = neither = 0
        for left_record, right_record in zip(left_records, right_records):
            left_positive = flag in operational_flags(left_record)
            right_positive = flag in operational_flags(right_record)
            if left_positive and right_positive:
                both += 1
            elif left_positive:
                left_only += 1
            elif right_positive:
                right_only += 1
            else:
                neither += 1
        per_flag[flag] = {
            "both_positive": both,
            "left_only_positive": left_only,
            "right_only_positive": right_only,
            "both_negative": neither,
            "positive_agreement": positive_agreement(both, left_only, right_only),
            "raw_agreement": rate(both + neither, both + left_only + right_only + neither),
        }
    return {
        "paired_item_count": len(left_records),
        "terminal_failure_detection_rule": (
            "terminal failure has no submitted flag and is counted as no detection; "
            "the missing rating is not recoded"
        ),
        "left_terminal_failure_n": sum(is_terminal_failure(record) for record in left_records),
        "right_terminal_failure_n": sum(is_terminal_failure(record) for record in right_records),
        "both_valid_observation_n": sum(
            is_valid_observation(left) and is_valid_observation(right)
            for left, right in zip(left_records, right_records)
        ),
        "both_sets_empty_n": both_empty,
        "mean_item_set_jaccard_empty_empty_equals_one": mean(item_jaccard),
        "mean_item_set_jaccard_among_both_valid": mean(valid_pair_jaccard),
        "per_flag": per_flag,
    }


def primary_correct(disposition: str, adjudicated_action: str) -> bool:
    if adjudicated_action == "accept":
        return disposition == "accept"
    if adjudicated_action == "expert_review":
        return disposition in {"revise", "reject", "escalate"}
    return disposition == "escalate"


def observation_primary_correct(
    record: Mapping[str, Any], adjudicated_action: str
) -> bool:
    """Terminal executions are task failures even when routed as escalations."""

    return is_valid_observation(record) and primary_correct(
        record["rating"]["disposition"], adjudicated_action
    )


def binary_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    precision = rate(tp, tp + fp)
    recall = rate(tp, tp + fn)
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
        "f1": (
            rounded(2 * precision * recall / (precision + recall))
            if precision is not None and recall is not None and precision + recall > 0
            else None
        ),
        "false_positive_rate": rate(fp, fp + tn),
        "specificity": rate(tn, tn + fp),
    }


def expert_reference_outcomes(
    records: Sequence[Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]],
    actor_id: str,
) -> dict[str, Any]:
    per_flag: dict[str, Any] = {}
    for flag in SERIOUS_ERROR_FLAGS:
        tp = fp = fn = tn = 0
        for record in records:
            truth = flag in adjudications[record["item_id"]]["serious_error_flags"]
            predicted = flag in operational_flags(record)
            if truth and predicted:
                tp += 1
            elif predicted:
                fp += 1
            elif truth:
                fn += 1
            else:
                tn += 1
        per_flag[flag] = binary_metrics(tp, fp, fn, tn)

    truth_any = [bool(adjudications[record["item_id"]]["serious_error_flags"]) for record in records]
    pred_any = [bool(operational_flags(record)) for record in records]
    any_tp = sum(truth and pred for truth, pred in zip(truth_any, pred_any))
    any_fp = sum(not truth and pred for truth, pred in zip(truth_any, pred_any))
    any_fn = sum(truth and not pred for truth, pred in zip(truth_any, pred_any))
    any_tn = sum(not truth and not pred for truth, pred in zip(truth_any, pred_any))

    false_acceptance = 0
    false_rejection = 0
    unnecessary_escalation = 0
    explicit_unnecessary_escalation = 0
    unnecessary_action = 0
    correctness: list[bool] = []
    material_high: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    high_only: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for record in records:
        adjudication = adjudications[record["item_id"]]
        disposition = operational_disposition(record)
        correctness.append(observation_primary_correct(record, adjudication["operational_action"]))
        if is_valid_observation(record) and disposition == "accept" and adjudication["operational_action"] != "accept":
            false_acceptance += 1
        if is_valid_observation(record) and disposition == "reject" and adjudication["operational_action"] == "accept":
            false_rejection += 1
        if disposition == "escalate" and adjudication["operational_action"] == "accept":
            unnecessary_escalation += 1
            if is_valid_observation(record):
                explicit_unnecessary_escalation += 1
        if disposition != "accept" and adjudication["operational_action"] == "accept":
            unnecessary_action += 1
        if adjudication["severity"] in {"material", "high_consequence"}:
            material_high.append((record, adjudication))
        if adjudication["severity"] == "high_consequence":
            high_only.append((record, adjudication))

    def severity_detection(rows: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]) -> dict[str, Any]:
        family_overlap = sum(
            bool(operational_flags(record) & set(adjudication["serious_error_flags"]))
            for record, adjudication in rows
        )
        any_flag = sum(bool(operational_flags(record)) for record, _ in rows)
        accepted = sum(
            is_valid_observation(record) and record["rating"]["disposition"] == "accept"
            for record, _ in rows
        )
        terminal_failures = sum(is_terminal_failure(record) for record, _ in rows)
        return {
            "reference_n": len(rows),
            "terminal_task_failure_n": terminal_failures,
            "correct_family_overlap_n": family_overlap,
            "correct_family_overlap_recall": rate(family_overlap, len(rows)),
            "any_flag_alert_n": any_flag,
            "any_flag_alert_rate": rate(any_flag, len(rows)),
            "false_acceptance_n": accepted,
            "false_acceptance_rate": rate(accepted, len(rows)),
        }

    n = len(records)
    return {
        "actor_id": actor_id,
        "rating_repetition": 1,
        "item_count": n,
        "valid_rating_n": sum(is_valid_observation(record) for record in records),
        "terminal_task_failure_n": sum(is_terminal_failure(record) for record in records),
        "observation_status_counts": observation_status_counts(records),
        "terminal_failure_rule": (
            "operational escalation, no submitted error flags, and primary task failure"
        ),
        "primary_decision_correct_n": sum(correctness),
        "primary_decision_accuracy": rate(sum(correctness), n),
        "false_acceptance_n": false_acceptance,
        "false_acceptance_rate": rate(false_acceptance, n),
        "false_rejection_n": false_rejection,
        "false_rejection_rate": rate(false_rejection, n),
        "unnecessary_escalation_n": unnecessary_escalation,
        "unnecessary_escalation_rate": rate(unnecessary_escalation, n),
        "explicit_unnecessary_escalation_n": explicit_unnecessary_escalation,
        "explicit_unnecessary_escalation_rate": rate(explicit_unnecessary_escalation, n),
        "any_unnecessary_action_on_adjudicated_accept_n": unnecessary_action,
        "any_unnecessary_action_on_adjudicated_accept_rate": rate(unnecessary_action, n),
        "any_serious_error": binary_metrics(any_tp, any_fp, any_fn, any_tn),
        "per_serious_error_flag": per_flag,
        "material_or_high_consequence": severity_detection(material_high),
        "high_consequence": severity_detection(high_only),
    }


def calibration_outcomes(
    records: Sequence[Mapping[str, Any]], adjudications: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    rows: list[tuple[int, float, int]] = []
    for record in records:
        if not is_valid_observation(record):
            continue
        confidence = record["rating"]["confidence"]
        probability = confidence / 5
        correct = int(
            observation_primary_correct(
                record, adjudications[record["item_id"]]["operational_action"]
            )
        )
        rows.append((confidence, probability, correct))
    brier = mean([(probability - correct) ** 2 for _level, probability, correct in rows])
    log_losses: list[float] = []
    reliability: dict[str, Any] = {}
    ece_total = 0.0
    for level in range(1, 6):
        subset = [(probability, correct) for observed, probability, correct in rows if observed == level]
        empirical = mean([correct for _probability, correct in subset])
        predicted = level / 5
        gap = abs(empirical - predicted) if empirical is not None else None
        if gap is not None:
            ece_total += len(subset) / len(rows) * gap
        reliability[str(level)] = {
            "n": len(subset),
            "mapped_probability": rounded(predicted),
            "observed_correct_rate": empirical,
            "absolute_calibration_gap": rounded(gap),
        }
    for _level, probability, correct in rows:
        clipped = min(0.999, max(0.001, probability))
        log_losses.append(-(correct * math.log(clipped) + (1 - correct) * math.log(1 - clipped)))
    return {
        "item_count": len(records),
        "scored_valid_confidence_n": len(rows),
        "terminal_task_failure_n": sum(is_terminal_failure(record) for record in records),
        "terminal_failure_handling": (
            "retained in the overall task-failure count but excluded from calibration "
            "because no confidence was submitted"
        ),
        "confidence_mapping": "p=confidence/5",
        "brier_score": brier,
        "expected_calibration_error_fixed_five_bins": (
            rounded(ece_total) if rows else None
        ),
        "log_loss_secondary_clipped_0.001_0.999": mean(log_losses),
        "reliability_by_confidence_level": reliability,
    }


def selective_risk_outcomes(
    records: Sequence[Mapping[str, Any]], adjudications: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = len(records)
    total_high = sum(
        adjudications[record["item_id"]]["severity"] == "high_consequence"
        for record in records
    )
    for threshold in range(5, 0, -1):
        retained = [
            record
            for record in records
            if is_valid_observation(record)
            and record["rating"]["confidence"] >= threshold
            and record["rating"]["disposition"] != "escalate"
        ]
        errors = sum(
            not observation_primary_correct(
                record,
                adjudications[record["item_id"]]["operational_action"],
            )
            for record in retained
        )
        false_accepts = sum(
            record["rating"]["disposition"] == "accept"
            and adjudications[record["item_id"]]["operational_action"] != "accept"
            for record in retained
        )
        retained_high = [
            record
            for record in retained
            if adjudications[record["item_id"]]["severity"] == "high_consequence"
        ]
        high_misses = sum(
            not bool(
                operational_flags(record)
                & set(adjudications[record["item_id"]]["serious_error_flags"])
            )
            for record in retained_high
        )
        rows.append(
            {
                "minimum_confidence": threshold,
                "retained_automatic_action_n": len(retained),
                "coverage": rate(len(retained), total),
                "primary_decision_error_n": errors,
                "primary_decision_risk": rate(errors, len(retained)),
                "false_acceptance_n": false_accepts,
                "false_acceptance_risk": rate(false_accepts, len(retained)),
                "retained_high_consequence_n": len(retained_high),
                "high_consequence_correct_family_miss_n": high_misses,
                "high_consequence_miss_rate_among_retained_high_consequence": rate(
                    high_misses, len(retained_high)
                ),
                "high_consequence_miss_rate_over_all_high_consequence_items": rate(
                    high_misses, total_high
                ),
            }
        )
    return {
        "automatic_action_definition": "confidence_at_or_above_threshold and disposition_not_escalate",
        "coverage_denominator": (
            "all locked items; terminal failures have no confidence, are operationally "
            "escalated/task failures, and are never retained"
        ),
        "high_consequence_miss_definition": "no overlap between predicted and adjudicated serious-error families",
        "total_items": total,
        "terminal_task_failure_n": sum(is_terminal_failure(record) for record in records),
        "total_high_consequence_items": total_high,
        "thresholds": rows,
    }


def abstention_escalation_outcomes(
    records: Sequence[Mapping[str, Any]], adjudications: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    valid_records = [record for record in records if is_valid_observation(record)]
    dimension_counts = {
        construct: sum(construct in record["rating"]["cannot_judge"] for record in valid_records)
        for construct in CONSTRUCTS
    }
    any_abstention = sum(bool(record["rating"]["cannot_judge"]) for record in valid_records)
    explicit_escalation = [
        is_valid_observation(record) and record["rating"]["disposition"] == "escalate"
        for record in records
    ]
    operational_escalation = [operational_disposition(record) == "escalate" for record in records]
    truth_needs_specialist = [
        adjudications[record["item_id"]]["requested_expertise"] != "none" for record in records
    ]
    def routing_metrics(predictions: Sequence[bool]) -> dict[str, Any]:
        tp = sum(pred and truth for pred, truth in zip(predictions, truth_needs_specialist))
        fp = sum(pred and not truth for pred, truth in zip(predictions, truth_needs_specialist))
        fn = sum(not pred and truth for pred, truth in zip(predictions, truth_needs_specialist))
        tn = sum(not pred and not truth for pred, truth in zip(predictions, truth_needs_specialist))
        return binary_metrics(tp, fp, fn, tn)

    plural = [
        record
        for record in records
        if adjudications[record["item_id"]]["operational_action"] == "plural_ambiguous"
    ]
    return {
        "item_count": len(records),
        "valid_rating_n": len(valid_records),
        "terminal_task_failure_n": len(records) - len(valid_records),
        "terminal_failure_operational_mapping": (
            "operational escalation without a fabricated cannot-judge dimension, "
            "requested expertise, confidence, or rating"
        ),
        "dimension_cannot_judge": {
            construct: {
                "n": dimension_counts[construct],
                "rate_among_valid_ratings": rate(dimension_counts[construct], len(valid_records)),
                "rate_over_all_locked_items": rate(dimension_counts[construct], len(records)),
            }
            for construct in CONSTRUCTS
        },
        "any_cannot_judge_n": any_abstention,
        "any_cannot_judge_rate_among_valid_ratings": rate(any_abstention, len(valid_records)),
        "explicit_escalation_n": sum(explicit_escalation),
        "explicit_escalation_rate": rate(sum(explicit_escalation), len(records)),
        "operational_escalation_n": sum(operational_escalation),
        "operational_escalation_rate": rate(sum(operational_escalation), len(records)),
        "requested_expertise_counts": {
            key: sum(record["rating"]["requested_expertise"] == key for record in valid_records)
            for key in REQUESTED_EXPERTISE
        },
        "requested_expertise_not_submitted_terminal_failure_n": len(records) - len(valid_records),
        "explicit_specialist_routing": routing_metrics(explicit_escalation),
        "operational_specialist_routing_including_terminal_failures": routing_metrics(
            operational_escalation
        ),
        "plural_ambiguous_n": len(plural),
        "plural_ambiguous_explicitly_escalated_n": sum(
            is_valid_observation(record) and record["rating"]["disposition"] == "escalate"
            for record in plural
        ),
        "plural_ambiguous_explicit_escalation_recall": rate(
            sum(
                is_valid_observation(record)
                and record["rating"]["disposition"] == "escalate"
                for record in plural
            ),
            len(plural),
        ),
        "plural_ambiguous_operationally_escalated_n": sum(
            operational_disposition(record) == "escalate" for record in plural
        ),
    }


def latency_cost_outcomes(
    records: Sequence[Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    cost_records = [record for record in records if record["execution"]["cost_available"]]
    by_currency: dict[str, list[float]] = defaultdict(list)
    pricing_ids: dict[str, set[str]] = defaultdict(set)
    for record in cost_records:
        currency = record["execution"]["cost_currency"]
        by_currency[currency].append(record["execution"]["cost_amount"])
        pricing_ids[currency].add(record["execution"]["pricing_snapshot_id"])
    token_records = [record for record in records if record["execution"]["token_usage_available"]]
    high_detected = sum(
        adjudications[record["item_id"]]["severity"] == "high_consequence"
        and bool(
            operational_flags(record)
            & set(adjudications[record["item_id"]]["serious_error_flags"])
        )
        for record in records
    )
    complete_cost = len(cost_records) == len(records) and len(by_currency) == 1
    if complete_cost and high_detected:
        currency = next(iter(by_currency))
        cost_per_high = {
            "available": True,
            "currency": currency,
            "correctly_detected_high_consequence_n": high_detected,
            "amount": rounded(sum(by_currency[currency]) / high_detected),
        }
    else:
        reason = (
            "cost_missing_for_one_or_more_items"
            if len(cost_records) != len(records)
            else "multiple_currencies"
            if len(by_currency) != 1
            else "no_correctly_detected_high_consequence_error"
        )
        cost_per_high = {
            "available": False,
            "reason": reason,
            "correctly_detected_high_consequence_n": high_detected,
            "amount": None,
            "currency": None,
        }
    reasoning_records = [
        record for record in records if record["execution"]["reasoning_tokens_available"]
    ]
    attempts = [
        attempt for record in records for attempt in record["execution"]["attempts"]
    ]
    return {
        "item_count": len(records),
        "observation_status_counts": observation_status_counts(records),
        "terminal_task_failure_n": sum(is_terminal_failure(record) for record in records),
        "review_seconds": numeric_summary(record["review_seconds"] for record in records),
        "retry_count": numeric_summary(record["execution"]["retry_count"] for record in records),
        "provider_attempt_count": numeric_summary(
            len(record["execution"]["attempts"]) for record in records
        ),
        "attempt_status_counts": {
            status: sum(attempt["attempt_status"] == status for attempt in attempts)
            for status in ATTEMPT_STATUSES
        },
        "provider_metadata_availability": {
            field: {
                "available_n": sum(attempt[field] is not None for attempt in attempts),
                "attempt_n": len(attempts),
            }
            for field in [
                "provider_request_id",
                "provider_response_id",
                "provider_returned_model_id",
                "provider_returned_model_version",
                "provider_region",
                "finish_reason",
            ]
        },
        "token_usage_available_n": len(token_records),
        "token_usage_missing_n": len(records) - len(token_records),
        "tokens_when_available": {
            field: numeric_summary(record["execution"][field] for record in token_records if record["execution"][field] is not None)
            for field in ["input_tokens", "output_tokens", "cached_input_tokens"]
        },
        "reasoning_tokens_available_n": len(reasoning_records),
        "reasoning_tokens_missing_n": len(records) - len(reasoning_records),
        "reasoning_tokens_when_available": numeric_summary(
            record["execution"]["reasoning_tokens"] for record in reasoning_records
        ),
        "cost_available_n": len(cost_records),
        "cost_missing_n": len(records) - len(cost_records),
        "cost_by_currency": {
            currency: {
                **numeric_summary(values),
                "pricing_snapshot_ids": sorted(pricing_ids[currency]),
            }
            for currency, values in sorted(by_currency.items())
        },
        "cost_per_correctly_detected_high_consequence_error": cost_per_high,
    }


def paired_expert_differences(
    left_records: Sequence[Mapping[str, Any]],
    right_records: Sequence[Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    correctness = Counter()
    false_acceptance = Counter()
    per_flag: dict[str, Any] = {}
    for left, right in zip(left_records, right_records):
        adjudication = adjudications[left["item_id"]]
        left_correct = observation_primary_correct(left, adjudication["operational_action"])
        right_correct = observation_primary_correct(right, adjudication["operational_action"])
        correctness[(left_correct, right_correct)] += 1
        left_false_accept = (
            is_valid_observation(left)
            and left["rating"]["disposition"] == "accept"
            and adjudication["operational_action"] != "accept"
        )
        right_false_accept = (
            is_valid_observation(right)
            and right["rating"]["disposition"] == "accept"
            and adjudication["operational_action"] != "accept"
        )
        false_acceptance[(left_false_accept, right_false_accept)] += 1
    for flag in SERIOUS_ERROR_FLAGS:
        truth_rows = [
            (left, right)
            for left, right in zip(left_records, right_records)
            if flag in adjudications[left["item_id"]]["serious_error_flags"]
        ]
        counts = Counter(
            (
                flag in operational_flags(left),
                flag in operational_flags(right),
            )
            for left, right in truth_rows
        )
        per_flag[flag] = {
            "adjudicated_positive_n": len(truth_rows),
            "both_detect": counts[(True, True)],
            "left_only_detects": counts[(True, False)],
            "right_only_detects": counts[(False, True)],
            "neither_detects": counts[(False, False)],
        }
    def discordance(counts: Counter[tuple[bool, bool]]) -> dict[str, int]:
        return {
            "both_true": counts[(True, True)],
            "left_only_true": counts[(True, False)],
            "right_only_true": counts[(False, True)],
            "both_false": counts[(False, False)],
        }
    return {
        "left_terminal_task_failure_n": sum(is_terminal_failure(record) for record in left_records),
        "right_terminal_task_failure_n": sum(is_terminal_failure(record) for record in right_records),
        "terminal_failure_rule": (
            "task-incorrect, never a false acceptance, and no serious-error family detected"
        ),
        "primary_decision_correctness_discordance": discordance(correctness),
        "false_acceptance_discordance": discordance(false_acceptance),
        "serious_error_detection_discordance_on_adjudicated_positive_items": per_flag,
    }


def individual_expert_agreement(
    lock: Mapping[str, Any],
    item_ids: Sequence[str],
    by_actor_rep_item: Mapping[tuple[str, int, str], Mapping[str, Any]],
    by_observation_id: Mapping[str, Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    referenced_ids = {
        observation_id
        for adjudication in adjudications.values()
        for observation_id in adjudication["locked_individual_observation_ids"]
    }
    expert_records: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for observation_id in referenced_ids:
        observation = by_observation_id[observation_id]
        expert_records[observation["actor_id"]][observation["item_id"]] = observation
    output: dict[str, Any] = {}
    for actor_id in sorted(lock["first_stage_actor_repetitions"]):
        output[actor_id] = {}
        for expert_id in sorted(lock["expert_actor_ids"]):
            overlap = sorted(set(item_ids) & set(expert_records.get(expert_id, {})))
            first_stage = [by_actor_rep_item[(actor_id, 1, item_id)] for item_id in overlap]
            expert = [expert_records[expert_id][item_id] for item_id in overlap]
            output[actor_id][expert_id] = {
                "paired_item_count": len(overlap),
                "construct_agreement": {
                    construct: construct_agreement(first_stage, expert, construct)
                    for construct in CONSTRUCTS
                },
                "disposition_agreement": disposition_agreement(first_stage, expert),
                "serious_error_flag_agreement": flag_agreement(first_stage, expert),
                "interpretation": (
                    "Agreement with one locked independent expert rating; this is not "
                    "the adjudicated validity reference."
                ),
            }
    return output


def repetition_stability(
    actor_id: str,
    repetitions: Sequence[int],
    item_ids: Sequence[str],
    by_actor_rep_item: Mapping[tuple[str, int, str], Mapping[str, Any]],
) -> dict[str, Any]:
    if len(repetitions) < 2:
        return {"available": False, "reason": "only_one_locked_rating_repetition"}
    constructs: dict[str, Any] = {}
    for construct in CONSTRUCTS:
        all_exact = 0
        all_evaluable = 0
        any_abstention = 0
        any_terminal = 0
        ranges: list[int] = []
        modal_shares: list[float] = []
        for item_id in item_ids:
            records = [
                by_actor_rep_item[(actor_id, repetition, item_id)] for repetition in repetitions
            ]
            if any(is_terminal_failure(record) for record in records):
                any_terminal += 1
                continue
            values = [record["rating"][construct] for record in records]
            if len(set(values)) == 1:
                all_exact += 1
            if any(value is None for value in values):
                any_abstention += 1
            else:
                all_evaluable += 1
                ranges.append(max(values) - min(values))
                modal_shares.append(max(Counter(values).values()) / len(values))
        constructs[construct] = {
            "item_count": len(item_ids),
            "all_repetitions_valid_n": len(item_ids) - any_terminal,
            "any_terminal_failure_n": any_terminal,
            "all_repetitions_exact_n": all_exact,
            "all_repetitions_exact_rate_among_all_valid": rate(
                all_exact, len(item_ids) - any_terminal
            ),
            "all_repetitions_evaluable_n": all_evaluable,
            "any_repetition_abstains_n": any_abstention,
            "range_distribution_when_all_evaluable": {
                str(value): Counter(ranges)[value] for value in range(0, 5)
            },
            "mean_range_when_all_evaluable": mean(ranges),
            "mean_modal_share_when_all_evaluable": mean(modal_shares),
        }
    disposition_exact = 0
    collapsed_exact = 0
    flag_set_exact = 0
    observation_status_exact = 0
    any_terminal_failure = 0
    all_terminal_failure = 0
    material_change = 0
    for item_id in item_ids:
        records = [by_actor_rep_item[(actor_id, repetition, item_id)] for repetition in repetitions]
        statuses = [record["observation_status"] for record in records]
        if len(set(statuses)) == 1:
            observation_status_exact += 1
        if any(is_terminal_failure(record) for record in records):
            any_terminal_failure += 1
        if all(is_terminal_failure(record) for record in records):
            all_terminal_failure += 1
        dispositions = [operational_disposition(record) for record in records]
        if len(set(dispositions)) == 1:
            disposition_exact += 1
        if len({collapse_disposition(value) for value in dispositions}) == 1:
            collapsed_exact += 1
        flag_sets = [tuple(sorted(operational_flags(record))) for record in records]
        if len(set(flag_sets)) == 1:
            flag_set_exact += 1
        construct_large_change = any(
            all(
                is_valid_observation(record) and record["rating"][construct] is not None
                for record in records
            )
            and max(record["rating"][construct] for record in records)
            - min(record["rating"][construct] for record in records)
            >= 2
            for construct in CONSTRUCTS
        )
        abstention_change = len(
            {
                tuple(sorted(record["rating"]["cannot_judge"]))
                for record in records
                if is_valid_observation(record)
            }
        ) > 1
        if (
            len(set(statuses)) > 1
            or len({collapse_disposition(value) for value in dispositions}) > 1
            or construct_large_change
            or abstention_change
            or len(set(flag_sets)) > 1
        ):
            material_change += 1
    return {
        "available": True,
        "actor_id": actor_id,
        "rating_repetitions": list(repetitions),
        "item_count": len(item_ids),
        "observation_status_all_repetitions_exact_rate": rate(
            observation_status_exact, len(item_ids)
        ),
        "any_terminal_failure_n": any_terminal_failure,
        "all_repetitions_terminal_failure_n": all_terminal_failure,
        "constructs": constructs,
        "disposition_all_repetitions_exact_rate": rate(disposition_exact, len(item_ids)),
        "pass_needs_action_all_repetitions_exact_rate": rate(collapsed_exact, len(item_ids)),
        "serious_error_set_all_repetitions_exact_rate": rate(flag_set_exact, len(item_ids)),
        "any_material_decision_change_definition": (
            "terminal-status change, pass/needs-action change, construct range >=2, "
            "abstention-set change, or serious-error-set change"
        ),
        "any_material_decision_change_n": material_change,
        "any_material_decision_change_rate": rate(material_change, len(item_ids)),
    }


def analyze_locked_records(
    lock: Mapping[str, Any], loaded: Mapping[str, Any]
) -> dict[str, Any]:
    validated = validate_complete_inputs(lock, loaded)
    item_ids = validated["item_ids"]
    by_key = validated["by_actor_rep_item"]
    adjudications = validated["adjudication_by_item"]
    pair = lock["primary_pair"]
    left_actor = pair["left_actor_id"]
    right_actor = pair["right_actor_id"]
    left_records = [by_key[(left_actor, 1, item_id)] for item_id in item_ids]
    right_records = [by_key[(right_actor, 1, item_id)] for item_id in item_ids]

    actor_results: dict[str, Any] = {}
    for actor_id in sorted(lock["first_stage_actor_repetitions"]):
        records = [by_key[(actor_id, 1, item_id)] for item_id in item_ids]
        actor_results[actor_id] = {
            "expert_reference": expert_reference_outcomes(records, adjudications, actor_id),
            "calibration": calibration_outcomes(records, adjudications),
            "selective_risk": selective_risk_outcomes(records, adjudications),
            "abstention_and_escalation": abstention_escalation_outcomes(records, adjudications),
            "latency_cost_and_usage": latency_cost_outcomes(records, adjudications),
        }

    result = {
        "analysis_version": ANALYSIS_VERSION,
        "status": "descriptive_results_from_complete_locked_synthetic_inputs",
        "result_label": SYNTHETIC_LABEL,
        "study_id": lock["study_id"],
        "evaluation_role": SYNTHETIC_ROLE,
        "qualification_scope": SYNTHETIC_SCOPE,
        "contains_real_source_text": False,
        "no_omnibus_quality_score": True,
        "input_provenance": loaded.get("input_provenance", {"fixture": "in_memory_self_test"}),
        "analysis_contract_provenance": {
            "analyzer_sha256": sha256_bytes(SCRIPT_PATH.read_bytes()),
            "paired_observation_schema_sha256": sha256_bytes(
                OBSERVATION_SCHEMA_PATH.read_bytes()
            ),
            "shared_rating_schema_sha256": sha256_bytes(RATING_SCHEMA_PATH.read_bytes()),
            "shared_rater_guide_sha256": checked_in_rater_guide_sha256(),
        },
        "validation": {
            "expected_item_count": lock["expected_item_count"],
            "complete_primary_pair_count": len(item_ids),
            "locked_observation_count": len(validated["observations"]),
            "locked_adjudication_count": len(validated["adjudications"]),
            "observation_counts_by_actor": validated["actor_counts"],
            "observation_status_counts_by_actor": {
                actor_id: observation_status_counts(
                    [
                        record
                        for record in validated["observations"]
                        if record["actor_id"] == actor_id
                    ]
                )
                for actor_id in sorted(validated["actor_counts"])
            },
            "missing_primary_pairs": 0,
            "missing_expert_adjudications": 0,
            "all_item_hashes_match_across_actors": True,
            "all_semantic_input_hashes_match_across_actors": True,
            "all_adjudications_locked_before_private_unblind": True,
        },
        "primary_pair": {
            "left_actor_id": left_actor,
            "right_actor_id": right_actor,
            "rating_repetition": 1,
            "construct_agreement": {
                construct: construct_agreement(left_records, right_records, construct)
                for construct in CONSTRUCTS
            },
            "disposition_agreement": disposition_agreement(left_records, right_records),
            "serious_error_flag_agreement": flag_agreement(left_records, right_records),
            "paired_expert_reference_differences": paired_expert_differences(
                left_records, right_records, adjudications
            ),
        },
        "first_stage_actor_outcomes": actor_results,
        "first_stage_vs_individual_expert_agreement": individual_expert_agreement(
            lock,
            item_ids,
            by_key,
            validated["by_observation_id"],
            adjudications,
        ),
        "primary_llm_repetition_stability": repetition_stability(
            right_actor,
            lock["first_stage_actor_repetitions"][right_actor],
            item_ids,
            by_key,
        ),
        "adjudication_reference_distribution": {
            "operational_action": {
                value: sum(
                    adjudication["operational_action"] == value
                    for adjudication in adjudications.values()
                )
                for value in ADJUDICATED_ACTIONS
            },
            "severity": {
                value: sum(
                    adjudication["severity"] == value
                    for adjudication in adjudications.values()
                )
                for value in SEVERITIES
            },
        },
        "outcome_definitions": {
            "primary_correctness": (
                "accept iff adjudicated accept; revise/reject/escalate iff expert_review; "
                "escalate only iff plural_ambiguous"
            ),
            "false_acceptance": (
                "first-stage accept on adjudicated expert_review or plural_ambiguous"
            ),
            "confidence_probability": "confidence / 5",
            "terminal_execution_failure": (
                "operational escalation and primary task failure; rating, confidence, "
                "cannot-judge dimensions, expertise request, and error flags remain unsubmitted"
            ),
            "adequacy": "construct rating 4 or 5 among evaluable ratings",
            "cannot_judge": "reported separately and never recoded",
        },
        "interpretation_limits": [
            "These are synthetic engineering qualification results only.",
            "Agreement is not validity; expert adjudication is a contract-relative operational reference, not universal qualitative truth.",
            "The three quality constructs are reported separately; no omnibus quality score is calculated.",
            "Missing token or cost telemetry remains missing and is not imputed.",
            "Terminal model failures remain in operational error, routing, and coverage denominators; calibration and construct agreement use only actually submitted fields.",
            "This stdlib descriptive utility does not emit confirmatory p-values or bootstrap intervals.",
        ],
    }
    return result


def profile_human(group: str) -> dict[str, Any]:
    return {
        "evaluator_group": group,
        "helped_construct": False,
        "independence_eligibility": "eligible_primary",
        "qualifications_recorded": True,
        "tutorial_version": "fixture-guide-v1",
        "comprehension_check_status": "passed",
        "corpus_familiarity": [],
    }


def fixture_rating(
    disposition: str,
    confidence: int,
    flags: list[str],
    values: tuple[int | None, int | None, int | None] = (4, 4, 4),
) -> dict[str, Any]:
    cannot = [construct for construct, value in zip(CONSTRUCTS, values) if value is None]
    return {
        "rating_schema_version": RATING_VERSION,
        "evidential_credibility": values[0],
        "voice_boundary_preservation": values[1],
        "scope_calibration": values[2],
        "cannot_judge": cannot,
        "confidence": confidence,
        "disposition": disposition,
        "requested_expertise": "qualitative_methods" if disposition == "escalate" else "none",
        "serious_error_flags": flags,
        "rationale": "Synthetic fixture rationale linked to the displayed evidence.",
    }


def fixture_observation(
    item_index: int,
    actor_id: str,
    actor_kind: str,
    repetition: int,
    rating: dict[str, Any],
    observation_id: str,
) -> dict[str, Any]:
    llm = actor_kind == "llm"
    item_hash = f"{item_index:064x}"
    guide_hash = checked_in_rater_guide_sha256()
    return {
        "observation_schema_version": OBSERVATION_VERSION,
        "observation_id": observation_id,
        "study_id": "direction-j-v1",
        "evaluation_role": SYNTHETIC_ROLE,
        "item_id": f"DJI_{item_index:016x}",
        "packet_id": f"SYN_PACKET_{item_index}",
        "output_id": f"SYN_OUTPUT_{item_index}",
        "corpus_id": "synthetic_proxy",
        "candidate_generation_run_id": f"synthetic:run:{item_index}",
        "candidate_generation_repetition": 1,
        "actor_id": actor_id,
        "actor_kind": actor_kind,
        "rating_repetition": repetition,
        "item_payload_sha256": item_hash,
        "interface_version": INTERFACE_VERSION,
        "shared_rater_guide_version": RATER_GUIDE_VERSION,
        "shared_rater_guide_sha256": guide_hash,
        "semantic_input_sha256": canonical_semantic_input_sha256(item_hash, guide_hash),
        "prompt_or_instrument_version": "fixture-instrument-v1",
        "prompt_or_instrument_sha256": "b" * 64,
        "started_at_utc": "2026-08-25T10:00:00Z",
        "completed_at_utc": "2026-08-25T10:00:10Z",
        "review_seconds": 10 + item_index + repetition,
        "observation_status": "valid",
        "rating": rating,
        "blinding": {
            "blind_id": f"BLIND_{item_index}",
            "candidate_identity_hidden": True,
            "condition_hidden": True,
            "other_ratings_hidden": True,
            "unblinded_at_utc": None,
        },
        "execution": {
            "retry_count": 0,
            "attempts": (
                [
                    {
                        "attempt_index": 1,
                        "attempt_kind": "initial",
                        "started_at_utc": "2026-08-25T10:00:00Z",
                        "completed_at_utc": "2026-08-25T10:00:10Z",
                        "attempt_status": "schema_valid_output",
                        "raw_request_artifact_id": f"RAW_REQUEST_{observation_id}",
                        "raw_request_sha256": "d" * 64,
                        "raw_response_artifact_id": f"RAW_RESPONSE_{observation_id}",
                        "raw_response_sha256": "e" * 64,
                        "provider_request_id": None,
                        "provider_response_id": None,
                        "provider_returned_model_id": "fixture-model",
                        "provider_returned_model_version": "fixture-snapshot",
                        "provider_region": None,
                        "finish_reason": "stop",
                        "filter_status": "not_filtered",
                        "schema_error_summary": None,
                        "token_usage_available": True,
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "cached_input_tokens": 0,
                        "reasoning_tokens_available": True,
                        "reasoning_tokens": 5,
                    }
                ]
                if llm
                else []
            ),
            "token_usage_available": llm,
            "input_tokens": 100 if llm else None,
            "output_tokens": 20 if llm else None,
            "cached_input_tokens": 0 if llm else None,
            "reasoning_tokens_available": llm,
            "reasoning_tokens": 5 if llm else None,
            "cost_available": llm,
            "cost_amount": 0.01 if llm else None,
            "cost_currency": "USD" if llm else None,
            "pricing_snapshot_id": "fixture-pricing-v1" if llm else None,
        },
    }


def build_self_test_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    actors = [
        {
            "actor_id": "charlie",
            "actor_kind": "human",
            "analysis_status": "primary",
            "exclusion_reason": None,
            "human_profile": profile_human("researcher"),
        },
        {
            "actor_id": "J_PRIMARY",
            "actor_kind": "llm",
            "analysis_status": "primary",
            "exclusion_reason": None,
            "llm_profile": {
                "provider": "fixture-provider",
                "model_id": "fixture-model",
                "model_family": "fixture-family",
                "model_snapshot": "fixture-snapshot",
                "surface": "fixture",
                "reasoning_mode": "fixture",
                "reasoning_effort": "high",
                "temperature": None,
                "top_p": None,
                "seed": None,
                "max_output_tokens": 1000,
                "response_count": 1,
                "structured_output": True,
                "tools_enabled": False,
                "web_enabled": False,
                "function_calling_enabled": False,
                "retrieval_enabled": False,
                "url_context_enabled": False,
                "code_execution_enabled": False,
                "memory_enabled": False,
                "judge_role": "primary",
                "candidate_family_overlap": False,
                "data_processing_scope": SYNTHETIC_SCOPE,
                "provider_processing_profile_id": "fixture-processing-v1",
            },
        },
        {
            "actor_id": "EXP_QM",
            "actor_kind": "human",
            "analysis_status": "primary",
            "exclusion_reason": None,
            "human_profile": profile_human("qualitative_methods_expert"),
        },
        {
            "actor_id": "EXP_DOMAIN",
            "actor_kind": "human",
            "analysis_status": "primary",
            "exclusion_reason": None,
            "human_profile": profile_human("domain_expert"),
        },
    ]
    registry = {
        "actor_registry_schema_version": ACTOR_REGISTRY_VERSION,
        "registry_id": "fixture-registry-v1",
        "frozen_at_utc": "2026-08-25T09:00:00Z",
        "actors": actors,
    }
    adjudication_specs = [
        ("accept", "none", [], "none"),
        ("expert_review", "material", ["unsupported_inference"], "qualitative_methods"),
        ("plural_ambiguous", "minor", ["lost_negative_case"], "domain"),
        ("expert_review", "high_consequence", ["wrong_attribution"], "both"),
    ]
    charlie_ratings = [
        fixture_rating("accept", 5, [], (5, 5, 5)),
        fixture_rating("revise", 4, ["unsupported_inference"], (3, 4, 3)),
        fixture_rating("escalate", 3, ["lost_negative_case"], (4, 4, None)),
        fixture_rating("accept", 4, [], (4, 4, 4)),
    ]
    primary_ratings = [
        fixture_rating("accept", 4, [], (5, 4, 5)),
        fixture_rating("accept", 5, [], (4, 4, 4)),
        fixture_rating("escalate", 2, ["lost_negative_case"], (4, None, 3)),
        fixture_rating("reject", 5, ["wrong_attribution"], (2, 3, 2)),
    ]
    observations: list[dict[str, Any]] = []
    adjudications: list[dict[str, Any]] = []
    for offset in range(4):
        item_index = offset + 1
        observations.append(
            fixture_observation(
                item_index,
                "charlie",
                "human",
                1,
                charlie_ratings[offset],
                f"OBS_CHARLIE_{item_index}",
            )
        )
        for repetition in [1, 2, 3]:
            rating = json.loads(json.dumps(primary_ratings[offset]))
            if repetition == 2 and offset == 1:
                rating = fixture_rating("revise", 4, ["unsupported_inference"], (3, 4, 3))
            if repetition == 3 and offset == 3:
                rating = fixture_rating("escalate", 4, ["wrong_attribution"], (2, None, 2))
            observations.append(
                fixture_observation(
                    item_index,
                    "J_PRIMARY",
                    "llm",
                    repetition,
                    rating,
                    f"OBS_PRIMARY_{item_index}_{repetition}",
                )
            )
        expert_ids: list[str] = []
        for expert_id in ["EXP_QM", "EXP_DOMAIN"]:
            observation_id = f"OBS_{expert_id}_{item_index}"
            expert_ids.append(observation_id)
            observations.append(
                fixture_observation(
                    item_index,
                    expert_id,
                    "human",
                    1,
                    fixture_rating("accept", 4, [], (4, 4, 4)),
                    observation_id,
                )
            )
        action, severity, flags, expertise = adjudication_specs[offset]
        adjudications.append(
            {
                "adjudication_version": ADJUDICATION_VERSION,
                "item_id": f"DJI_{item_index:016x}",
                "panel_id": "FIXTURE_PANEL",
                "locked_individual_observation_ids": expert_ids,
                "adjudicated_at_utc": "2026-08-25T11:00:00Z",
                "operational_action": action,
                "severity": severity,
                "serious_error_flags": flags,
                "error_locations": [
                    {
                        "flag": flag,
                        "excerpt_ids": [],
                        "source_ids": [],
                        "output_location": "proposed_interpretation.claim",
                        "explanation": "Synthetic fixture error location.",
                    }
                    for flag in flags
                ],
                "requested_expertise": expertise,
                "rationale": "Synthetic fixture adjudication rationale.",
                "locked_before_private_unblind": True,
            }
        )
    lock = {
        "analysis_input_lock_version": LOCK_VERSION,
        "status": "locked_for_analysis",
        "study_id": "direction-j-v1",
        "evaluation_role": SYNTHETIC_ROLE,
        "qualification_scope": SYNTHETIC_SCOPE,
        "contains_real_source_text": False,
        "result_label": SYNTHETIC_LABEL,
        "locked_at_utc": "2026-08-25T12:00:00Z",
        "observations_locked": True,
        "adjudications_locked": True,
        "actor_registry_locked": True,
        "expected_item_count": 4,
        "primary_pair": {
            "left_actor_id": "charlie",
            "right_actor_id": "J_PRIMARY",
            "left_rating_repetition": 1,
            "right_rating_repetition": 1,
        },
        "first_stage_actor_repetitions": {"charlie": [1], "J_PRIMARY": [1, 2, 3]},
        "expert_actor_ids": ["EXP_QM", "EXP_DOMAIN"],
        "files": {
            name: {"path": f"{name}.json", "sha256": "a" * 64}
            for name in LOCK_FILE_KEYS
        },
    }
    fixture_item_bindings: dict[str, dict[str, str]] = {}
    fixture_assignment_bindings: dict[
        str, dict[str, dict[str, dict[str, str]]]
    ] = {}
    for observation in observations:
        item_id = observation["item_id"]
        fixture_item_bindings.setdefault(
            item_id,
            {field: observation[field] for field in FROZEN_ITEM_BINDING_FIELDS},
        )
        fixture_assignment_bindings.setdefault(observation["actor_id"], {}).setdefault(
            str(observation["rating_repetition"]), {}
        )[item_id] = {
            **{field: observation[field] for field in FROZEN_ITEM_BINDING_FIELDS},
            "actor_kind": observation["actor_kind"],
            "assignment_id": f"FIXTURE_ASSIGNMENT_{observation['observation_id']}",
            "sequence": str(len(fixture_assignment_bindings.get(observation["actor_id"], {}).get(str(observation["rating_repetition"]), {})) + 1),
        }
    loaded = {
        "actor_registry": registry,
        "observations": observations,
        "expert_adjudications": adjudications,
        "frozen_item_bindings": fixture_item_bindings,
        "frozen_assignment_bindings": fixture_assignment_bindings,
        "run_manifest": {
            "run_manifest_version": "direction-j-run-manifest-v1",
            "run_id": FROZEN_RUN_ID,
            "status": "locked_for_analysis",
            "study_id": "direction-j-v1",
            "evaluation_role": SYNTHETIC_ROLE,
            "qualification_scope": SYNTHETIC_SCOPE,
            "contains_real_source_text": False,
            "independently_authored_fictional_text": True,
            "freeze_path": "../../config/freeze_v1.json",
            "freeze_sha256": "1" * 64,
            "build_report_sha256": "2" * 64,
            "evaluator_items_sha256": "3" * 64,
            "source_receipt_sha256": "4" * 64,
            "synthetic_benchmark_sha256": "5" * 64,
            "blinded_bundle_fileset_sha256": "6" * 64,
            "ratings_collected": len(observations),
            "outcomes_available": True,
            "expected_observations": {"charlie": 4, "J_PRIMARY": 12},
            "result_label": SYNTHETIC_LABEL,
        },
    }
    return lock, loaded


def run_self_test() -> None:
    lock, loaded = build_self_test_fixture()
    validate_lock(lock)
    result = analyze_locked_records(lock, loaded)
    assert result["no_omnibus_quality_score"] is True
    assert result["validation"]["complete_primary_pair_count"] == 4
    assert result["validation"]["missing_expert_adjudications"] == 0
    assert set(result["primary_pair"]["construct_agreement"]) == set(CONSTRUCTS)
    assert result["first_stage_actor_outcomes"]["J_PRIMARY"]["calibration"]["brier_score"] is not None
    assert result["first_stage_actor_outcomes"]["J_PRIMARY"]["latency_cost_and_usage"]["cost_available_n"] == 4
    assert "first_stage_vs_individual_expert_agreement" in result

    terminal_loaded = json.loads(json.dumps(loaded))
    terminal_record = next(
        observation
        for observation in terminal_loaded["observations"]
        if observation["actor_id"] == "J_PRIMARY"
        and observation["rating_repetition"] == 1
        and observation["item_id"] == "DJI_0000000000000002"
    )
    terminal_record["observation_status"] = "invalid_output"
    terminal_record["rating"] = None
    terminal_attempt = terminal_record["execution"]["attempts"][0]
    terminal_attempt["attempt_status"] = "invalid_schema"
    terminal_attempt["schema_error_summary"] = "Synthetic fixture schema violation."
    terminal_result = analyze_locked_records(lock, terminal_loaded)
    terminal_actor = terminal_result["first_stage_actor_outcomes"]["J_PRIMARY"]
    assert terminal_actor["expert_reference"]["terminal_task_failure_n"] == 1
    assert terminal_actor["expert_reference"]["item_count"] == 4
    assert terminal_actor["calibration"]["scored_valid_confidence_n"] == 3
    assert terminal_actor["calibration"]["terminal_task_failure_n"] == 1
    assert terminal_actor["selective_risk"]["total_items"] == 4
    assert terminal_actor["selective_risk"]["terminal_task_failure_n"] == 1
    assert terminal_actor["abstention_and_escalation"]["operational_escalation_n"] >= 1
    assert terminal_actor["latency_cost_and_usage"]["item_count"] == 4
    assert terminal_actor["latency_cost_and_usage"]["terminal_task_failure_n"] == 1
    assert terminal_result["primary_pair"]["construct_agreement"][
        "evidential_credibility"
    ]["right_terminal_failure_n"] == 1
    zero_confidence_calibration = calibration_outcomes(
        [terminal_record],
        {row["item_id"]: row for row in terminal_loaded["expert_adjudications"]},
    )
    assert zero_confidence_calibration["scored_valid_confidence_n"] == 0
    assert zero_confidence_calibration["expected_calibration_error_fixed_five_bins"] is None

    missing_observation = json.loads(json.dumps(loaded))
    missing_observation["observations"] = [
        observation
        for observation in missing_observation["observations"]
        if observation["observation_id"] != "OBS_PRIMARY_4_1"
    ]
    missing_observation["run_manifest"]["ratings_collected"] -= 1
    missing_observation["run_manifest"]["expected_observations"]["J_PRIMARY"] -= 1
    try:
        analyze_locked_records(lock, missing_observation)
    except AnalysisInputError:
        pass
    else:
        raise AssertionError("missing locked primary observation did not fail closed")

    missing_adjudication = dict(loaded)
    missing_adjudication["expert_adjudications"] = loaded["expert_adjudications"][:-1]
    try:
        analyze_locked_records(lock, missing_adjudication)
    except AnalysisInputError:
        pass
    else:
        raise AssertionError("missing adjudication did not fail closed")
    mismatched = json.loads(json.dumps(loaded))
    for observation in mismatched["observations"]:
        if observation["actor_id"] == "J_PRIMARY" and observation["rating_repetition"] == 1:
            observation["item_payload_sha256"] = "f" * 64
            break
    try:
        analyze_locked_records(lock, mismatched)
    except AnalysisInputError:
        pass
    else:
        raise AssertionError("paired item hash mismatch did not fail closed")
    bank_mismatched = json.loads(json.dumps(loaded))
    for observation in bank_mismatched["observations"]:
        if observation["item_id"] == "DJI_0000000000000001":
            observation["output_id"] = "SYN_OUTPUT_NOT_IN_FROZEN_BANK"
    try:
        analyze_locked_records(lock, bank_mismatched)
    except AnalysisInputError as error:
        if "frozen evaluator bank" not in str(error):
            raise AssertionError("frozen-bank mismatch failed for the wrong reason") from error
    else:
        raise AssertionError("internally paired but frozen-bank-mismatched records were accepted")
    assignment_mismatched = json.loads(json.dumps(loaded))
    del assignment_mismatched["frozen_assignment_bindings"]["J_PRIMARY"]["1"][
        "DJI_0000000000000001"
    ]
    try:
        analyze_locked_records(lock, assignment_mismatched)
    except AnalysisInputError as error:
        if "frozen actor/repetition assignment" not in str(error):
            raise AssertionError("frozen-assignment mismatch failed for the wrong reason") from error
    else:
        raise AssertionError("record absent from its frozen assignment was accepted")
    print(
        json.dumps(
            {
                "self_test": "passed",
                "fixture_scope": SYNTHETIC_SCOPE,
                "fixture_results_are_study_results": False,
                "missing_adjudication_rejected": True,
                "missing_primary_observation_rejected": True,
                "paired_hash_mismatch_rejected": True,
                "frozen_bank_identity_mismatch_rejected": True,
                "frozen_assignment_mismatch_rejected": True,
                "terminal_failure_denominators_verified": True,
                "zero_confidence_calibration_is_null": True,
            },
            sort_keys=True,
        )
    )


def resolve_output(raw: str, lock_dir: Path) -> Path:
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
    if has_forbidden_path_component(resolved):
        fail("output path contains a forbidden dataset component")
    if not is_relative_to(resolved, lock_dir.resolve()):
        fail("output must remain inside the locked Direction J run directory")
    return resolved


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    parser = argparse.ArgumentParser(
        description="Analyze complete locked synthetic Direction J paired records."
    )
    parser.add_argument("--lock-manifest", type=Path)
    parser.add_argument("--output")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate complete locked inputs without writing or printing outcome values.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run in-memory synthetic fixtures, including fail-closed checks.",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        if args.lock_manifest or args.output or args.validate_only:
            parser.error("--self-test cannot be combined with run inputs")
        run_self_test()
        return 0
    if args.lock_manifest is None:
        parser.error("--lock-manifest is required unless --self-test is used")
    if not args.validate_only and not args.output:
        parser.error("--output is required unless --validate-only is used")
    try:
        lock, loaded = load_locked_inputs(args.lock_manifest)
        result = analyze_locked_records(lock, loaded)
        if args.validate_only:
            print(
                json.dumps(
                    {
                        "validation": "passed",
                        "result_file_written": False,
                        "synthetic_only": True,
                        "complete_primary_pair_count": result["validation"][
                            "complete_primary_pair_count"
                        ],
                        "locked_adjudication_count": result["validation"][
                            "locked_adjudication_count"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        output_path = resolve_output(args.output, args.lock_manifest.resolve().parent)
        locked_inputs = {
            Path(descriptor["path"]).resolve()
            if Path(descriptor["path"]).is_absolute()
            else (args.lock_manifest.resolve().parent / descriptor["path"]).resolve()
            for descriptor in lock["files"].values()
        }
        if output_path in locked_inputs or output_path == args.lock_manifest.resolve():
            fail("output path may not overwrite a locked input")
        write_json_atomic(output_path, result)
        print(
            json.dumps(
                {
                    "output": output_path.relative_to(args.lock_manifest.resolve().parent).as_posix(),
                    "result_label": SYNTHETIC_LABEL,
                    "complete_primary_pair_count": result["validation"][
                        "complete_primary_pair_count"
                    ],
                },
                sort_keys=True,
            )
        )
        return 0
    except AnalysisInputError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("No result file was emitted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
