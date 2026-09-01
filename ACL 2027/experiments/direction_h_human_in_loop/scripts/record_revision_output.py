#!/usr/bin/env python3
"""Record one frozen synthetic Direction H revision attempt without calling a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver
except ModuleNotFoundError:
    candidates = [
        Path.home() / "miniconda3" / "bin" / "python3",
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
    ]
    for candidate in candidates:
        if not candidate.is_file() or candidate.resolve() == Path(sys.executable).resolve():
            continue
        if subprocess.run(
            [str(candidate), "-c", "import jsonschema"], capture_output=True, check=False
        ).returncode == 0:
            os.execv(str(candidate), [str(candidate), __file__, *sys.argv[1:]])
    raise SystemExit(
        "No local Python runtime with jsonschema is available; no revision output was written."
    )


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
COORDINATOR_ROOT = DIRECTION_ROOT / "coordinator_only"
CASE_ROOT = COORDINATOR_ROOT / "revision_cases"
RAW_RESPONSE_ROOT = COORDINATOR_ROOT / "revision_raw_responses"
OUTPUT_ROOT = COORDINATOR_ROOT / "revision_outputs"
DEFAULT_ALLOCATION = COORDINATOR_ROOT / "revision_allocation.json"
DEFAULT_FREEZE = PILOT_ROOT / "revision_freeze.json"

BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
QUALITATIVE_SCHEMA = BASELINE_ROOT / "schemas" / "qualitative_output.schema.json"
PILOT_ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
FEEDBACK_SCHEMA = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
CASE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_case.schema.json"
FREEZE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_freeze_manifest.schema.json"
REVISION_OUTPUT_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_output.schema.json"
CONSTRUCTION_VERIFICATION = COORDINATOR_ROOT / "construction_verification.json"
TARGET_BRIEFS = COORDINATOR_ROOT / "target_assessment_briefs.json"
TARGET_BRIEFS_COMMITMENT = COORDINATOR_ROOT / "target_assessment_briefs.commitment.json"

EXPECTED_FROZEN_ARTIFACTS = {
    "analytic_contract": BASELINE_ROOT / "protocol" / "analytic_contract.md",
    "revision_prompt": DIRECTION_ROOT / "protocol" / "revision_prompt.md",
    "feedback_formatter": DIRECTION_ROOT / "scripts" / "format_feedback.py",
    "input_schema": CASE_SCHEMA,
    "output_schema": REVISION_OUTPUT_SCHEMA,
    "integrity_validator": BASELINE_ROOT / "scripts" / "validate_and_score.py",
    "revision_output_recorder": Path(__file__).resolve(),
    "repair_panel_packager": DIRECTION_ROOT / "scripts" / "prepare_repair_panel.py",
}

ALLOCATION_VERSION = "direction-h-revision-allocation-v2"

ALLOCATION_KEYS = {
    "execution_sort",
    "revision_case_id",
    "blinded_revision_id",
    "model_blinded_case_id",
    "paired_case_group_id",
    "task_id",
    "repeat_index",
    "feedback_arm",
}
ALLOCATION_TOP_KEYS = {
    "allocation_version",
    "study_id",
    "freeze_id",
    "created_at_utc",
    "execution_order_balanced_by",
    "eligibility_rule",
    "construction_overall_disposition",
    "construction_verification_file_sha256",
    "target_briefs_file_sha256",
    "target_briefs_commitment_file_sha256",
    "target_briefs_committed_at_utc",
    "eligible_target_task_ids",
    "excluded_items",
    "cases",
}
EXCLUSION_KEYS = {
    "task_id",
    "committed_condition",
    "committed_target_flag",
    "construction_disposition",
    "exclusion_reason",
}
BRIEF_COMMITMENT_KEYS = {
    "commitment_version",
    "study_id",
    "visibility",
    "target_briefs_path",
    "target_briefs_file_sha256",
    "construction_verification_file_sha256",
    "committed_by_id",
    "committed_by_is_charlie",
    "committed_at_utc",
    "briefs_complete",
    "immutable_before_revision_generation",
}

FORBIDDEN_MODEL_INPUT_KEYS = {
    "accepted_detection_flags",
    "condition",
    "failure_family",
    "feedback_arm",
    "model_id",
    "primary_error_flag",
    "rater_id",
    "target_defect",
    "target_status",
    "truth_record",
}

RUNTIME_FAILURE_DETAILS = {
    "transport_failure": "Transport failed before a usable model response was captured.",
    "empty_response": "The runtime returned no usable model response bytes.",
}

FEEDBACK_FIELDS_IN_ORDER = ["feedback_summary", "findings", "preserve", "uncertainties"]
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class RecorderBlocked(Exception):
    """A fail-closed precondition prevented a write."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(file_path: Path) -> str:
    return sha256_bytes(file_path.read_bytes())


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonstandard_number(token: str) -> None:
    raise ValueError(f"non-standard JSON number: {token}")


def parse_json_bytes(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} is not UTF-8 JSON") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_number,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label} is not strict JSON: {error}") from error


def load_json(file_path: Path, label: str) -> Any:
    try:
        return parse_json_bytes(file_path.read_bytes(), label)
    except ValueError as error:
        raise RecorderBlocked(str(error)) from error
    except OSError as error:
        raise RecorderBlocked(f"cannot read {label}: {error}") from error


def ensure_file_below(file_path: Path, allowed_root: Path, label: str) -> Path:
    if allowed_root.is_symlink():
        raise RecorderBlocked(f"{label} root must not be a symlink: {allowed_root}")
    resolved = file_path.expanduser().resolve()
    root = allowed_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RecorderBlocked(f"{label} must stay below {root}") from error
    if file_path.is_symlink() or not resolved.is_file():
        raise RecorderBlocked(f"{label} is missing, not regular, or a symlink: {file_path}")
    return resolved


def has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "__REQUIRED" in value or value.startswith("FILL_") or value == "TBD"
    if isinstance(value, dict):
        return any(has_placeholder(nested) for nested in value.values())
    if isinstance(value, list):
        return any(has_placeholder(nested) for nested in value)
    return False


def normalize_rfc3339_utc(value: str, label: str) -> str:
    if not RFC3339_RE.fullmatch(value):
        raise RecorderBlocked(f"{label} must be an RFC 3339 date-time with a UTC offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RecorderBlocked(f"{label} is not a real calendar date-time") from error
    if parsed.tzinfo is None:
        raise RecorderBlocked(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def schema_documents() -> tuple[dict[Path, dict[str, Any]], dict[str, Any]]:
    schema_paths = (
        QUALITATIVE_SCHEMA,
        PILOT_ITEM_SCHEMA,
        FEEDBACK_SCHEMA,
        CASE_SCHEMA,
        FREEZE_SCHEMA,
        REVISION_OUTPUT_SCHEMA,
    )
    documents: dict[Path, dict[str, Any]] = {}
    store: dict[str, Any] = {}
    for schema_path in schema_paths:
        document = load_json(schema_path, schema_path.name)
        Draft202012Validator.check_schema(document)
        documents[schema_path] = document
        if document.get("$id"):
            store[document["$id"]] = document
    return documents, store


def validation_errors(
    instance: Any,
    schema: dict[str, Any],
    store: dict[str, Any],
) -> list[Any]:
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=store),
        format_checker=FormatChecker(),
    )
    return sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))


def validate_or_block(
    instance: Any,
    schema: dict[str, Any],
    store: dict[str, Any],
    label: str,
) -> None:
    errors = validation_errors(instance, schema, store)
    if not errors:
        return
    rendered = "; ".join(
        f"{json_pointer(error.absolute_path)} ({error.validator})" for error in errors[:12]
    )
    raise RecorderBlocked(f"{label} fails schema at {rendered}")


def json_pointer(parts: Iterable[Any]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"


def decode_pointer_token(token: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            result.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValueError("malformed JSON Pointer escape")
        result.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(result)


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError("pointer must be non-root and begin with slash")
    current = document
    for encoded in pointer[1:].split("/"):
        token = decode_pointer_token(encoded)
        if isinstance(current, dict):
            if token not in current:
                raise ValueError("object key does not exist")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token.isdigit() or (
                len(token) > 1 and token.startswith("0")
            ):
                raise ValueError("invalid array index")
            position = int(token)
            if position >= len(current):
                raise ValueError("array index is out of range")
            current = current[position]
        else:
            raise ValueError("pointer traverses a scalar")
    return current


def verify_freeze(
    freeze: dict[str, Any],
    freeze_path: Path,
    documents: dict[Path, dict[str, Any]],
    store: dict[str, Any],
) -> None:
    validate_or_block(freeze, documents[FREEZE_SCHEMA], store, "revision freeze")
    if freeze_path.name != "revision_freeze.json":
        raise RecorderBlocked("the completed freeze must be named revision_freeze.json")
    if freeze.get("status") != "frozen" or has_placeholder(freeze):
        raise RecorderBlocked("revision freeze is not immutable and complete")
    if freeze.get("freeze_scope") != "synthetic_pilot":
        raise RecorderBlocked("this recorder is synthetic-pilot-only")
    governance = freeze.get("data_governance", {})
    if governance.get("data_scope") != "synthetic_only" or governance.get(
        "contains_protected_text"
    ) is not False:
        raise RecorderBlocked("protected or non-synthetic revision data are not accepted")
    for key, expected_path in EXPECTED_FROZEN_ARTIFACTS.items():
        artifact = freeze[key]
        declared_path = (PROJECT_ROOT / artifact["path"]).resolve()
        if declared_path != expected_path.resolve():
            raise RecorderBlocked(f"frozen {key} path is not the allowlisted project artifact")
        if (
            expected_path.is_symlink()
            or not declared_path.is_file()
            or artifact["sha256"] != sha256_file(declared_path)
        ):
            raise RecorderBlocked(f"frozen {key} artifact is missing or hash-drifted")


def verify_public_item(
    case: dict[str, Any],
    freeze: dict[str, Any],
    documents: dict[Path, dict[str, Any]],
    store: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = PILOT_ROOT / "manifest.json"
    manifest = load_json(manifest_path, "pilot manifest")
    if manifest.get("study_id") != freeze.get("study_id"):
        raise RecorderBlocked("pilot manifest and freeze study_id differ")
    if manifest.get("data_scope") != "synthetic_only" or manifest.get(
        "contains_real_source_text"
    ) is not False:
        raise RecorderBlocked("pilot manifest is not reviewer-safe synthetic data")
    matches = [row for row in manifest.get("tasks", []) if row.get("task_id") == case["task_id"]]
    if len(matches) != 1:
        raise RecorderBlocked("case task_id does not resolve uniquely in the pilot manifest")
    task = matches[0]
    item_path = ensure_file_below(PILOT_ROOT / task["item_file"], PILOT_ROOT / "items", "pilot item")
    if task.get("sha256") != sha256_file(item_path):
        raise RecorderBlocked("pilot item hash differs from the frozen reviewer manifest")
    item = load_json(item_path, "reviewer-safe pilot item")
    validate_or_block(item, documents[PILOT_ITEM_SCHEMA], store, "reviewer-safe pilot item")
    if item.get("data_classification") != "synthetic_cc0":
        raise RecorderBlocked("pilot item is not classified synthetic_cc0")
    if item.get("packet_id", "").startswith("syn_") is False:
        raise RecorderBlocked("pilot item packet_id is outside the synthetic namespace")
    if item.get("evidence_packet", {}).get("status") != "synthetic_proxy_not_corpus_result":
        raise RecorderBlocked("pilot evidence packet is not an allowed synthetic proxy")
    expected_case_fields = {
        "task_id": item["task_id"],
        "packet_id": item["packet_id"],
        "output_id": item["output_id"],
    }
    for key, expected in expected_case_fields.items():
        if case.get(key) != expected:
            raise RecorderBlocked(f"case and reviewer item differ on {key}")
    model_input = case["model_input"]
    if model_input.get("evidence_packet") != item.get("evidence_packet"):
        raise RecorderBlocked("case evidence differs from the hashed reviewer-safe item")
    if model_input.get("original_output") != item.get("candidate_output"):
        raise RecorderBlocked("case starting output differs from the hashed reviewer-safe item")

    review_lock_path = ensure_file_below(
        PILOT_ROOT / "review_lock.json", PILOT_ROOT, "review lock"
    )
    review_lock = load_json(review_lock_path, "review lock")
    expected_task_ids = [row["task_id"] for row in manifest["tasks"]]
    lock_records = review_lock.get("records")
    commitment_path = ensure_file_below(
        PILOT_ROOT / "condition_commitment.json", PILOT_ROOT, "condition commitment"
    )
    lock_record_keys = {
        "task_id",
        "rating_file",
        "rating_sha256",
        "feedback_file",
        "feedback_sha256",
    }
    if (
        review_lock.get("review_lock_version") != "direction-h-review-lock-v1"
        or review_lock.get("study_id") != manifest.get("study_id")
        or review_lock.get("rater_id") != manifest.get("intended_rater_id")
        or review_lock.get("task_count") != len(expected_task_ids)
        or review_lock.get("manifest_sha256") != sha256_file(manifest_path)
        or review_lock.get("condition_commitment_sha256")
        != sha256_file(commitment_path)
        or review_lock.get("truth_opened_by_this_step") is not False
        or review_lock.get("ratings_or_feedback_modified_by_this_step") is not False
        or not isinstance(lock_records, list)
        or any(not isinstance(row, dict) or set(row) != lock_record_keys for row in lock_records)
        or [row.get("task_id") for row in lock_records] != expected_task_ids
    ):
        raise RecorderBlocked("review lock is incomplete, altered, or inconsistent with the pilot")
    locked_feedback: dict[str, dict[str, Any]] = {}
    for record in lock_records:
        task_id = record["task_id"]
        rating_path = ensure_file_below(
            PILOT_ROOT / record["rating_file"],
            PILOT_ROOT / "responses" / "ratings",
            f"locked rating {task_id}",
        )
        feedback_path = ensure_file_below(
            PILOT_ROOT / record["feedback_file"],
            PILOT_ROOT / "responses" / "feedback",
            f"locked feedback {task_id}",
        )
        if record.get("rating_sha256") != sha256_file(rating_path):
            raise RecorderBlocked(f"locked rating hash drifted for {task_id}")
        if record.get("feedback_sha256") != sha256_file(feedback_path):
            raise RecorderBlocked(f"locked feedback hash drifted for {task_id}")
        feedback = load_json(feedback_path, f"locked feedback {task_id}")
        validate_or_block(
            feedback,
            documents[FEEDBACK_SCHEMA],
            store,
            f"locked feedback {task_id}",
        )
        locked_feedback[task_id] = feedback

    if case["feedback_arm"] == "no_feedback":
        if case.get("feedback_record_id") is not None or model_input.get(
            "reviewer_feedback"
        ) is not None:
            raise RecorderBlocked("no-feedback case must have null linkage and model payload")
    elif case["feedback_arm"] == "charlie_feedback":
        feedback = locked_feedback[case["task_id"]]
        projected = feedback.get("model_feedback")
        if not isinstance(projected, dict) or list(projected) != FEEDBACK_FIELDS_IN_ORDER:
            raise RecorderBlocked("locked feedback does not match the frozen formatter order")
        if case.get("feedback_record_id") != feedback.get("feedback_id"):
            raise RecorderBlocked("case feedback_record_id differs from the locked sidecar")
        if model_input.get("reviewer_feedback") != projected:
            raise RecorderBlocked("case feedback projection differs from the locked sidecar")
    else:
        raise RecorderBlocked("synthetic pilot recorder accepts only the two frozen pilot arms")
    return manifest, item


def expected_allocation_row(
    freeze_id: str,
    task_id: str,
    repeat_index: int,
    arm: str,
) -> dict[str, Any]:
    digest = hashlib.sha256(
        f"direction-h-allocation-v2|{freeze_id}|{task_id}|{repeat_index}|{arm}".encode()
    ).hexdigest()
    pair_digest = hashlib.sha256(
        f"direction-h-pair-v1|{freeze_id}|{task_id}|{repeat_index}".encode()
    ).hexdigest()
    return {
        "execution_sort": digest,
        "revision_case_id": f"RVC-{digest[:12].upper()}",
        "blinded_revision_id": f"RBI-{digest[12:24].upper()}",
        "model_blinded_case_id": f"RMI-{pair_digest[12:24].upper()}",
        "paired_case_group_id": f"RPG-{pair_digest[:12].upper()}",
        "task_id": task_id,
        "repeat_index": repeat_index,
        "feedback_arm": arm,
    }


def verify_allocation(
    allocation: dict[str, Any],
    case: dict[str, Any],
    freeze: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(allocation, dict) or set(allocation) != ALLOCATION_TOP_KEYS:
        raise RecorderBlocked("allocation top-level fields differ from the v2 contract")
    if allocation.get("allocation_version") != ALLOCATION_VERSION:
        raise RecorderBlocked("unsupported revision allocation version")
    if allocation.get("study_id") != freeze.get("study_id"):
        raise RecorderBlocked("allocation and freeze study_id differ")
    if allocation.get("freeze_id") != freeze.get("freeze_id"):
        raise RecorderBlocked("allocation and freeze freeze_id differ")
    if allocation.get("eligibility_rule") != (
        "committed controlled_defect AND item disposition verified_for_detection"
    ):
        raise RecorderBlocked("allocation eligibility rule differs from the frozen contract")
    if allocation.get("execution_order_balanced_by") != "sha256 of frozen case identity":
        raise RecorderBlocked("allocation execution-order rule differs from the frozen contract")
    rows = allocation.get("cases")
    if not isinstance(rows, list) or not rows:
        raise RecorderBlocked("allocation has no cases")
    if any(not isinstance(row, dict) or set(row) != ALLOCATION_KEYS for row in rows):
        raise RecorderBlocked("allocation row fields differ from the frozen builder contract")
    if rows != sorted(rows, key=lambda row: row["execution_sort"]):
        raise RecorderBlocked("allocation execution order is not its committed hash order")

    verification_path = ensure_file_below(
        CONSTRUCTION_VERIFICATION, COORDINATOR_ROOT, "construction verification"
    )
    briefs_path = ensure_file_below(TARGET_BRIEFS, COORDINATOR_ROOT, "target briefs")
    commitment_path = ensure_file_below(
        TARGET_BRIEFS_COMMITMENT, COORDINATOR_ROOT, "target-brief commitment"
    )
    truth_path = ensure_file_below(
        COORDINATOR_ROOT / "truth_map.json", COORDINATOR_ROOT, "truth map"
    )
    condition_commitment_path = ensure_file_below(
        PILOT_ROOT / "condition_commitment.json", PILOT_ROOT, "condition commitment"
    )
    verification = load_json(verification_path, "construction verification")
    briefs = load_json(briefs_path, "target briefs")
    brief_commitment = load_json(commitment_path, "target-brief commitment")
    truth = load_json(truth_path, "truth map")
    condition_commitment = load_json(condition_commitment_path, "condition commitment")
    if has_placeholder(verification) or has_placeholder(briefs) or has_placeholder(brief_commitment):
        raise RecorderBlocked("construction, target briefs, or commitment is incomplete")
    if not isinstance(brief_commitment, dict) or set(brief_commitment) != BRIEF_COMMITMENT_KEYS:
        raise RecorderBlocked("target-brief commitment fields differ from the frozen contract")
    expected_artifact_hashes = {
        "construction_verification_file_sha256": sha256_file(verification_path),
        "target_briefs_file_sha256": sha256_file(briefs_path),
        "target_briefs_commitment_file_sha256": sha256_file(commitment_path),
    }
    for key, expected_hash in expected_artifact_hashes.items():
        if allocation.get(key) != expected_hash:
            raise RecorderBlocked(f"allocation eligibility artifact hash drifted: {key}")
    if (
        brief_commitment.get("commitment_version")
        != "direction-h-target-assessment-briefs-commitment-v1"
        or brief_commitment.get("study_id") != manifest.get("study_id")
        or brief_commitment.get("visibility") != "coordinator_only"
        or brief_commitment.get("target_briefs_path")
        != "coordinator_only/target_assessment_briefs.json"
        or brief_commitment.get("target_briefs_file_sha256") != sha256_file(briefs_path)
        or brief_commitment.get("construction_verification_file_sha256")
        != sha256_file(verification_path)
        or not isinstance(brief_commitment.get("committed_by_id"), str)
        or not 1 <= len(brief_commitment.get("committed_by_id", "").strip()) <= 160
        or brief_commitment.get("committed_by_id", "").strip().casefold()
        == "charlie_dev_researcher_01"
        or brief_commitment.get("committed_by_is_charlie") is not False
        or brief_commitment.get("briefs_complete") is not True
        or brief_commitment.get("immutable_before_revision_generation") is not True
    ):
        raise RecorderBlocked("target-brief commitment is incomplete or hash-inconsistent")
    committed_at = normalize_rfc3339_utc(
        brief_commitment.get("committed_at_utc"), "target briefs committed_at_utc"
    )
    if allocation.get("target_briefs_committed_at_utc") != brief_commitment.get(
        "committed_at_utc"
    ):
        raise RecorderBlocked("allocation target-brief commitment time drifted")
    if datetime.fromisoformat(
        normalize_rfc3339_utc(allocation.get("created_at_utc"), "allocation created_at_utc").replace(
            "Z", "+00:00"
        )
    ) <= datetime.fromisoformat(committed_at.replace("Z", "+00:00")):
        raise RecorderBlocked("allocation was not created after target briefs froze")

    truth_hash = sha256_bytes(canonical_bytes(truth))
    if (
        condition_commitment.get("truth_map_sha256") != truth_hash
        or verification.get("truth_map_sha256") != truth_hash
        or verification.get("study_id") != manifest.get("study_id")
        or allocation.get("construction_overall_disposition")
        != verification.get("overall_disposition")
    ):
        raise RecorderBlocked("allocation construction truth linkage drifted")
    manifest_ids = {task["task_id"] for task in manifest["tasks"]}
    truth_rows = {row.get("task_id"): row for row in truth.get("items", [])}
    verified_rows = {row.get("task_id"): row for row in verification.get("items", [])}
    if set(truth_rows) != manifest_ids or set(verified_rows) != manifest_ids:
        raise RecorderBlocked("construction task inventory differs from the pilot")
    eligible_ids: set[str] = set()
    expected_exclusions: list[dict[str, Any]] = []
    for task_id in sorted(manifest_ids):
        truth_row = truth_rows[task_id]
        checked = verified_rows[task_id]
        target_flag = (
            truth_row["planted_defect"]["target_flag"]
            if truth_row.get("planted_defect") is not None
            else None
        )
        if (
            checked.get("intended_condition") != truth_row.get("condition")
            or checked.get("intended_target_flag") != target_flag
        ):
            raise RecorderBlocked(f"construction verification changed committed truth: {task_id}")
        if (
            truth_row.get("condition") == "controlled_defect"
            and checked.get("disposition") == "verified_for_detection"
        ):
            eligible_ids.add(task_id)
            continue
        if checked.get("disposition") == "workflow_only":
            reason = "construction_workflow_only"
        elif checked.get("disposition") == "reject_item":
            reason = "construction_reject_item"
        else:
            reason = "verified_no_planted_defect_control_not_target_repair"
        expected_exclusions.append(
            {
                "task_id": task_id,
                "committed_condition": truth_row.get("condition"),
                "committed_target_flag": target_flag,
                "construction_disposition": checked.get("disposition"),
                "exclusion_reason": reason,
            }
        )
    if not eligible_ids:
        raise RecorderBlocked("construction verification has no eligible controlled target")
    if allocation.get("eligible_target_task_ids") != sorted(eligible_ids):
        raise RecorderBlocked("allocation eligible target task set drifted")
    if allocation.get("excluded_items") != expected_exclusions or any(
        not isinstance(row, dict) or set(row) != EXCLUSION_KEYS
        for row in allocation.get("excluded_items", [])
    ):
        raise RecorderBlocked("allocation private item-exclusion accounting drifted")
    brief_ids = {row.get("task_id") for row in briefs.get("items", [])}
    if brief_ids != eligible_ids or len(briefs.get("items", [])) != len(eligible_ids):
        raise RecorderBlocked("target briefs do not cover exactly the eligible targets")

    frozen_arms = list(freeze["arm_policy"]["arms"])
    repeats = int(freeze["repeat_policy"]["repeats_per_arm"])
    expected_rows = {
        (task["task_id"], repeat_index, arm): expected_allocation_row(
            freeze["freeze_id"], task["task_id"], repeat_index, arm
        )
        for task in manifest["tasks"]
        if task["task_id"] in eligible_ids
        for repeat_index in range(1, repeats + 1)
        for arm in frozen_arms
    }
    observed_keys: set[tuple[str, int, str]] = set()
    for row in rows:
        key = (row["task_id"], row["repeat_index"], row["feedback_arm"])
        if key in observed_keys or expected_rows.get(key) != row:
            raise RecorderBlocked("allocation is duplicate, incomplete, unexpected, or hash-inconsistent")
        observed_keys.add(key)
    if observed_keys != set(expected_rows):
        raise RecorderBlocked("allocation does not cover every eligible target, repeat, and arm")
    if len({row["revision_case_id"] for row in rows}) != len(rows):
        raise RecorderBlocked("allocation has duplicate revision_case_id values")
    if len({row["blinded_revision_id"] for row in rows}) != len(rows):
        raise RecorderBlocked("allocation has duplicate blinded_revision_id values")
    matches = [row for row in rows if row["revision_case_id"] == case["revision_case_id"]]
    if len(matches) != 1:
        raise RecorderBlocked("case does not resolve uniquely in the frozen allocation")
    row = matches[0]
    case_to_row = {
        "paired_case_group_id": "paired_case_group_id",
        "repeat_index": "repeat_index",
        "task_id": "task_id",
        "feedback_arm": "feedback_arm",
    }
    for case_key, row_key in case_to_row.items():
        if case.get(case_key) != row.get(row_key):
            raise RecorderBlocked(f"case and allocation differ on {case_key}")
    if case["model_input"].get("blinded_case_id") != row["model_blinded_case_id"]:
        raise RecorderBlocked("case model blind ID differs from allocation")
    if case.get("allocation_record_sha256") != sha256_bytes(canonical_bytes(allocation)):
        raise RecorderBlocked("case does not carry the canonical allocation hash")
    return row


def verify_case(
    case: dict[str, Any],
    freeze: dict[str, Any],
    documents: dict[Path, dict[str, Any]],
    store: dict[str, Any],
) -> None:
    validate_or_block(case, documents[CASE_SCHEMA], store, "revision case")
    if case.get("freeze_id") != freeze.get("freeze_id"):
        raise RecorderBlocked("case and freeze freeze_id differ")
    if case.get("contains_target_truth") is not False or case.get(
        "contains_rater_identity"
    ) is not False:
        raise RecorderBlocked("case is not truth- and identity-blind")
    if case.get("model_input_sha256") != sha256_bytes(canonical_bytes(case["model_input"])):
        raise RecorderBlocked("case model_input hash mismatch")
    model_input_path = ensure_file_below(
        PILOT_ROOT / "revision_model_inputs" / f"{case['revision_case_id']}.json",
        PILOT_ROOT / "revision_model_inputs",
        "frozen model input",
    )
    if load_json(model_input_path, "frozen model input") != case["model_input"]:
        raise RecorderBlocked("model-facing input differs from the validated coordinator case")
    leaked_keys = sorted(FORBIDDEN_MODEL_INPUT_KEYS & set(walk_keys(case["model_input"])))
    if leaked_keys:
        raise RecorderBlocked("forbidden key in model input: " + ", ".join(leaked_keys))
    serialized = canonical_bytes(case["model_input"]).decode("utf-8").lower()
    if "charlie" in serialized or '"rater_id"' in serialized:
        raise RecorderBlocked("rater identity appears in model input")


def add_issue(
    issues: list[str],
    hard_issues: set[str],
    code: str,
    locator: str = "",
    *,
    hard: bool = True,
) -> None:
    rendered = f"{code}:{locator}" if locator else code
    rendered = rendered[:300]
    if rendered not in issues:
        issues.append(rendered)
    if hard:
        hard_issues.add(rendered)


def iter_citations(output: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for code_index, code in enumerate(output.get("codes", [])):
        for citation_index, citation in enumerate(code.get("exemplars", [])):
            yield f"codes/{code_index}/exemplars/{citation_index}", citation
    for theme_index, theme in enumerate(output.get("themes", [])):
        for field in ("evidence", "counterevidence"):
            for citation_index, citation in enumerate(theme.get(field, [])):
                yield f"themes/{theme_index}/{field}/{citation_index}", citation
    for citation_index, citation in enumerate(output.get("negative_cases", [])):
        yield f"negative_cases/{citation_index}", citation


def integrity_check(
    response: dict[str, Any],
    case: dict[str, Any],
) -> tuple[list[str], bool]:
    """Apply the baseline hard gates plus revision-diagnosis linkage checks."""
    issues: list[str] = []
    hard_issues: set[str] = set()
    packet = case["model_input"]["evidence_packet"]
    original = case["model_input"]["original_output"]
    output = response["revised_output"]
    diagnosis = response["revision_diagnosis"]

    if output.get("packet_id") != packet.get("packet_id"):
        add_issue(issues, hard_issues, "packet_id_mismatch")
    if output.get("research_question") != packet.get("research_question"):
        add_issue(issues, hard_issues, "research_question_mismatch")

    excerpt_rows = packet.get("excerpts", [])
    excerpts = {row["excerpt_id"]: row for row in excerpt_rows}
    if len(excerpts) != len(excerpt_rows):
        add_issue(issues, hard_issues, "duplicate_packet_excerpt_id")
    sources = {row["source_id"] for row in excerpt_rows}

    code_ids = [row.get("code_id") for row in output.get("codes", [])]
    code_set = set(code_ids)
    if len(code_ids) != len(code_set):
        add_issue(issues, hard_issues, "duplicate_code_id")
    theme_ids = [row.get("theme_id") for row in output.get("themes", [])]
    if len(theme_ids) != len(set(theme_ids)):
        add_issue(issues, hard_issues, "duplicate_theme_id")

    assignments = output.get("assignments", [])
    assigned_ids = [row.get("excerpt_id") for row in assignments]
    counts = Counter(assigned_ids)
    for excerpt_id in sorted(set(excerpts) - set(assigned_ids)):
        add_issue(issues, hard_issues, "missing_assignment", str(excerpt_id))
    for excerpt_id in sorted(set(assigned_ids) - set(excerpts)):
        add_issue(issues, hard_issues, "unknown_assignment_excerpt", str(excerpt_id))
    for excerpt_id, count in sorted(counts.items(), key=lambda item: str(item[0])):
        if count > 1:
            add_issue(issues, hard_issues, "duplicate_assignment", str(excerpt_id))
    for assignment_index, assignment in enumerate(assignments):
        refs = assignment.get("code_ids", [])
        for code_id in refs:
            if code_id not in code_set:
                add_issue(
                    issues,
                    hard_issues,
                    "unknown_assignment_code",
                    f"{assignment_index}/{code_id}",
                )
        if bool(assignment.get("not_coded")) == bool(refs):
            add_issue(
                issues, hard_issues, "not_coded_inconsistent", str(assignment_index)
            )

    for locator, citation in iter_citations(output):
        excerpt = excerpts.get(citation.get("excerpt_id"))
        if excerpt is None:
            add_issue(issues, hard_issues, "unknown_citation_excerpt", locator)
        if citation.get("source_id") not in sources:
            add_issue(issues, hard_issues, "unknown_citation_source", locator)
        if excerpt is not None and citation.get("source_id") != excerpt.get("source_id"):
            add_issue(issues, hard_issues, "citation_attribution_mismatch", locator)
        quote = citation.get("quote")
        if excerpt is None or not isinstance(quote, str) or quote not in excerpt.get("text", ""):
            add_issue(issues, hard_issues, "non_exact_quote", locator)

    for theme_index, theme in enumerate(output.get("themes", [])):
        for code_id in theme.get("code_ids", []):
            if code_id not in code_set:
                add_issue(
                    issues, hard_issues, "unknown_theme_code", f"{theme_index}/{code_id}"
                )
        evidence_sources = {
            row.get("source_id") for row in theme.get("evidence", []) if row.get("source_id")
        }
        if len(evidence_sources) < 2:
            add_issue(issues, hard_issues, "single_source_theme", str(theme_index))
        declared_sources = set(theme.get("source_ids", []))
        for source_id in sorted(declared_sources - sources):
            add_issue(
                issues,
                hard_issues,
                "unknown_theme_source",
                f"{theme_index}/{source_id}",
            )
        represented_sources = evidence_sources | {
            row.get("source_id")
            for row in theme.get("counterevidence", [])
            if row.get("source_id")
        }
        if declared_sources != represented_sources:
            add_issue(
                issues,
                hard_issues,
                "theme_source_list_mismatch",
                str(theme_index),
                hard=False,
            )

    detected_flags = set(diagnosis.get("detected_error_flags", []))
    finding_flags = {row.get("error_flag") for row in diagnosis.get("findings", [])}
    if detected_flags != finding_flags:
        add_issue(issues, hard_issues, "diagnosis_flag_finding_mismatch")
    for finding_index, finding in enumerate(diagnosis.get("findings", [])):
        for pointer_index, pointer in enumerate(finding.get("output_locations", [])):
            try:
                resolve_pointer(original, pointer)
            except ValueError:
                add_issue(
                    issues,
                    hard_issues,
                    "diagnosis_pointer_unresolved",
                    f"{finding_index}/{pointer_index}",
                )
        for excerpt_id in finding.get("evidence_excerpt_ids", []):
            if excerpt_id not in excerpts:
                add_issue(
                    issues,
                    hard_issues,
                    "diagnosis_unknown_excerpt",
                    f"{finding_index}/{excerpt_id}",
                )

    if len(issues) > 100:
        overflow_hard = bool(hard_issues - set(issues[:99]))
        issues = issues[:99] + ["issue_limit_exceeded"]
        if overflow_hard:
            hard_issues.add("issue_limit_exceeded")
    return issues, not hard_issues


def retry_reason(record: dict[str, Any]) -> str | None:
    status = record.get("completion_status")
    failure = record.get("failure_record") or {}
    code = failure.get("failure_code")
    if status == "runtime_failure" and code == "runtime_error":
        return "transport_failure"
    if code == "no_response":
        return "empty_response"
    if status == "parse_failure" and code == "invalid_json":
        return "invalid_json"
    if status == "schema_failure" and code == "schema_invalid":
        return "schema_invalid"
    return None


def deterministic_output_id(freeze_id: str, case_id: str, attempt_index: int) -> str:
    digest = hashlib.sha256(
        f"direction-h-revision-output-v1|{freeze_id}|{case_id}|{attempt_index}".encode()
    ).hexdigest()
    return f"RVO-{digest[:16].upper()}"


def verify_attempt_sequence(
    case: dict[str, Any],
    allocation_row: dict[str, Any],
    freeze: dict[str, Any],
    attempt_index: int,
    documents: dict[Path, dict[str, Any]],
    store: dict[str, Any],
) -> Path:
    maximum = int(freeze["retry_policy"]["maximum_attempts"])
    if attempt_index > maximum:
        raise RecorderBlocked("attempt_index exceeds the frozen maximum_attempts")
    case_id = case["revision_case_id"]
    output_path = OUTPUT_ROOT / f"{case_id}.attempt-{attempt_index:03d}.json"
    if OUTPUT_ROOT.is_symlink():
        raise RecorderBlocked("revision output directory must not be a symlink")
    if OUTPUT_ROOT.exists() and not OUTPUT_ROOT.is_dir():
        raise RecorderBlocked("revision output path exists but is not a directory")
    try:
        OUTPUT_ROOT.resolve().relative_to(COORDINATOR_ROOT.resolve())
    except ValueError as error:
        raise RecorderBlocked("revision output directory escapes coordinator_only") from error
    if output_path.exists():
        raise RecorderBlocked(f"refusing to overwrite existing attempt: {output_path}")
    existing: dict[int, dict[str, Any]] = {}
    if OUTPUT_ROOT.exists():
        for candidate in OUTPUT_ROOT.glob(f"{case_id}.attempt-*.json"):
            suffix = candidate.stem.rsplit("attempt-", 1)[-1]
            if not suffix.isdigit():
                raise RecorderBlocked(f"unrecognized attempt filename for case {case_id}")
            number = int(suffix)
            record = load_json(candidate, f"prior attempt {number}")
            validate_or_block(
                record,
                documents[REVISION_OUTPUT_SCHEMA],
                store,
                f"prior attempt {number}",
            )
            if number in existing:
                raise RecorderBlocked("duplicate prior attempt index")
            expected_identity = {
                "revision_case_id": case_id,
                "freeze_id": freeze["freeze_id"],
                "feedback_arm": case["feedback_arm"],
                "model_snapshot_id": freeze["revision_model"]["snapshot_id"],
                "generator_model_id": freeze["revision_model"]["model_id"],
                "blinded_revision_id": allocation_row["blinded_revision_id"],
                "attempt_index": number,
                "revision_output_id": deterministic_output_id(
                    freeze["freeze_id"], case_id, number
                ),
            }
            if any(record.get(key) != value for key, value in expected_identity.items()):
                raise RecorderBlocked(f"prior attempt {number} has provenance drift")
            existing[number] = record
    expected_prior = set(range(1, attempt_index))
    if set(existing) != expected_prior:
        raise RecorderBlocked("attempts must be recorded once, consecutively, and in order")
    if attempt_index > 1:
        previous = existing[attempt_index - 1]
        if previous["completion_status"] == "complete":
            raise RecorderBlocked("a complete response cannot be retried")
        reason = retry_reason(previous)
        if reason not in freeze["retry_policy"]["allowed_retry_reasons"]:
            raise RecorderBlocked(
                "the immediately preceding failure is not retryable under the frozen policy"
            )
    return output_path


def failure_detail_from_errors(errors: list[Any]) -> str:
    codes = [
        f"{json_pointer(error.absolute_path)} ({error.validator})" for error in errors[:12]
    ]
    return "model response failed the exact two-field schema at " + ", ".join(codes)


def build_envelope(
    args: argparse.Namespace,
    case: dict[str, Any],
    allocation_row: dict[str, Any],
    freeze: dict[str, Any],
    documents: dict[Path, dict[str, Any]],
    store: dict[str, Any],
) -> dict[str, Any]:
    validated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    raw_hash: str | None = None
    revised_hash: str | None = None
    diagnosis: dict[str, Any] | None = None
    revised_output: dict[str, Any] | None = None
    failure: dict[str, str] | None = None
    schema_valid = False
    hard_gate_pass = False
    issue_codes: list[str] = []

    if args.runtime_failure:
        completion_status = "runtime_failure"
        failure_code = "runtime_error" if args.runtime_failure == "transport_failure" else "no_response"
        failure = {
            "failure_code": failure_code,
            "failure_detail": RUNTIME_FAILURE_DETAILS[args.runtime_failure],
        }
        issue_codes = [args.runtime_failure]
    else:
        raw_path = ensure_file_below(
            args.raw_response, RAW_RESPONSE_ROOT, "raw model response"
        )
        expected_raw_name = (
            f"{case['revision_case_id']}.attempt-{args.attempt_index:03d}.raw.json"
        )
        if raw_path.name != expected_raw_name:
            raise RecorderBlocked(
                "raw response filename must bind the frozen case and attempt: "
                + expected_raw_name
            )
        try:
            raw = raw_path.read_bytes()
        except OSError as error:
            raise RecorderBlocked(f"cannot read raw model response: {error}") from error
        raw_hash = sha256_bytes(raw)
        if not raw.strip():
            completion_status = "runtime_failure"
            failure = {
                "failure_code": "no_response",
                "failure_detail": "raw model response contained no non-whitespace bytes",
            }
            issue_codes = ["empty_response"]
        else:
            try:
                response = parse_json_bytes(raw, "raw model response")
            except ValueError as error:
                completion_status = "parse_failure"
                failure = {
                    "failure_code": "invalid_json",
                    "failure_detail": str(error)[:3000],
                }
                issue_codes = ["invalid_json"]
            else:
                response_ref = {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": (
                        documents[REVISION_OUTPUT_SCHEMA]["$id"] + "#/$defs/modelResponse"
                    ),
                }
                errors = validation_errors(response, response_ref, store)
                if errors:
                    completion_status = "schema_failure"
                    failure = {
                        "failure_code": "schema_invalid",
                        "failure_detail": failure_detail_from_errors(errors)[:3000],
                    }
                    issue_codes = []
                    for error in errors[:100]:
                        code = (
                            f"model_response_schema:{json_pointer(error.absolute_path)}:"
                            f"{error.validator}"
                        )[:300]
                        if code not in issue_codes:
                            issue_codes.append(code)
                else:
                    completion_status = "complete"
                    schema_valid = True
                    diagnosis = response["revision_diagnosis"]
                    revised_output = response["revised_output"]
                    revised_hash = sha256_bytes(canonical_bytes(revised_output))
                    issue_codes, hard_gate_pass = integrity_check(response, case)

    envelope: dict[str, Any] = {
        "revision_output_version": "direction-h-revision-output-v1",
        "revision_output_id": deterministic_output_id(
            freeze["freeze_id"], case["revision_case_id"], args.attempt_index
        ),
        "blinded_revision_id": allocation_row["blinded_revision_id"],
        "revision_case_id": case["revision_case_id"],
        "paired_case_group_id": case["paired_case_group_id"],
        "repeat_index": case["repeat_index"],
        "task_id": case["task_id"],
        "packet_id": case["packet_id"],
        "starting_output_id": case["output_id"],
        "freeze_id": freeze["freeze_id"],
        "feedback_arm": case["feedback_arm"],
        "completion_status": completion_status,
        "generator_model_id": freeze["revision_model"]["model_id"],
        "model_snapshot_id": freeze["revision_model"]["snapshot_id"],
        "attempt_index": args.attempt_index,
        "generated_at_utc": args.generated_at_utc,
        "raw_output_sha256": raw_hash,
        "revised_output_sha256": revised_hash,
        "revision_diagnosis": diagnosis,
        "revised_output": revised_output,
        "failure_record": failure,
        "integrity_validation": {
            "schema_valid": schema_valid,
            "hard_gate_pass": hard_gate_pass,
            "issue_codes": issue_codes,
            "validated_at_utc": validated_at,
        },
    }
    for argument, field in (
        (args.latency_ms, "latency_ms"),
        (args.input_tokens, "input_tokens"),
        (args.output_tokens, "output_tokens"),
    ):
        if argument is not None:
            envelope[field] = argument
    return envelope


def write_json_new(output_path: Path, value: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError as error:
        raise RecorderBlocked(f"refusing to overwrite existing attempt: {output_path}") from error
    except OSError as error:
        raise RecorderBlocked(f"could not write revision attempt: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and record one already-run synthetic Direction H revision attempt; "
            "this command never calls a model."
        )
    )
    parser.add_argument("--case", type=Path, required=True, help="Frozen revision case JSON")
    parser.add_argument(
        "--allocation",
        type=Path,
        default=DEFAULT_ALLOCATION,
        help="Frozen coordinator allocation JSON",
    )
    parser.add_argument(
        "--freeze",
        type=Path,
        default=DEFAULT_FREEZE,
        help="Completed frozen revision manifest",
    )
    parser.add_argument("--attempt-index", type=int, required=True, help="One-based attempt index")
    parser.add_argument(
        "--runtime-model-id",
        required=True,
        help="Model ID reported for the actual runtime invocation; must match the freeze",
    )
    parser.add_argument(
        "--runtime-snapshot-id",
        required=True,
        help="Immutable snapshot ID reported for the invocation; must match the freeze",
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Actual invocation completion time as an RFC 3339 date-time",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--raw-response",
        type=Path,
        help="Verbatim UTF-8 response below coordinator_only/revision_raw_responses/",
    )
    source.add_argument(
        "--runtime-failure",
        choices=("transport_failure", "empty_response"),
        help="Explicit failure observed before a usable response was captured",
    )
    parser.add_argument("--latency-ms", type=int)
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    args = parser.parse_args()

    if args.attempt_index < 1:
        raise RecorderBlocked("attempt_index must be at least 1")
    args.generated_at_utc = normalize_rfc3339_utc(
        args.generated_at_utc, "generated_at_utc"
    )
    for value, label in (
        (args.latency_ms, "latency_ms"),
        (args.input_tokens, "input_tokens"),
        (args.output_tokens, "output_tokens"),
    ):
        if value is not None and value < 0:
            raise RecorderBlocked(f"{label} must be nonnegative")
    case_path = ensure_file_below(args.case, CASE_ROOT, "revision case")
    allocation_path = ensure_file_below(
        args.allocation, COORDINATOR_ROOT, "revision allocation"
    )
    freeze_path = ensure_file_below(args.freeze, PILOT_ROOT, "revision freeze")
    documents, store = schema_documents()
    freeze = load_json(freeze_path, "revision freeze")
    verify_freeze(freeze, freeze_path, documents, store)
    frozen_at = normalize_rfc3339_utc(freeze["frozen_at_utc"], "freeze frozen_at_utc")
    if datetime.fromisoformat(args.generated_at_utc.replace("Z", "+00:00")) < datetime.fromisoformat(
        frozen_at.replace("Z", "+00:00")
    ):
        raise RecorderBlocked("actual invocation completion predates the revision freeze")
    if args.runtime_model_id != freeze["revision_model"]["model_id"]:
        raise RecorderBlocked("runtime model ID does not match the frozen model ID")
    if args.runtime_snapshot_id != freeze["revision_model"]["snapshot_id"]:
        raise RecorderBlocked("runtime snapshot ID does not match the frozen snapshot ID")
    case = load_json(case_path, "revision case")
    verify_case(case, freeze, documents, store)
    if datetime.fromisoformat(args.generated_at_utc.replace("Z", "+00:00")) <= datetime.fromisoformat(
        normalize_rfc3339_utc(case["created_at_utc"], "revision case created_at_utc").replace(
            "Z", "+00:00"
        )
    ):
        raise RecorderBlocked("actual invocation completion must postdate revision case creation")
    manifest, _ = verify_public_item(case, freeze, documents, store)
    allocation = load_json(allocation_path, "revision allocation")
    allocation_row = verify_allocation(allocation, case, freeze, manifest)
    if datetime.fromisoformat(args.generated_at_utc.replace("Z", "+00:00")) <= datetime.fromisoformat(
        normalize_rfc3339_utc(
            allocation["target_briefs_committed_at_utc"],
            "target briefs committed_at_utc",
        ).replace("Z", "+00:00")
    ):
        raise RecorderBlocked("actual invocation completion must postdate the frozen target briefs")
    output_path = verify_attempt_sequence(
        case,
        allocation_row,
        freeze,
        args.attempt_index,
        documents,
        store,
    )
    envelope = build_envelope(args, case, allocation_row, freeze, documents, store)
    validate_or_block(
        envelope,
        documents[REVISION_OUTPUT_SCHEMA],
        store,
        "revision output envelope",
    )
    write_json_new(output_path, envelope)
    print(
        json.dumps(
            {
                "status": "revision_attempt_recorded",
                "revision_case_id": case["revision_case_id"],
                "attempt_index": args.attempt_index,
                "completion_status": envelope["completion_status"],
                "schema_valid": envelope["integrity_validation"]["schema_valid"],
                "hard_gate_pass": envelope["integrity_validation"]["hard_gate_pass"],
                "issue_count": len(envelope["integrity_validation"]["issue_codes"]),
                "output_file": str(output_path.relative_to(DIRECTION_ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RecorderBlocked as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
