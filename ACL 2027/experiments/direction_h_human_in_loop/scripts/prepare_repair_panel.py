#!/usr/bin/env python3
"""Package frozen revision outputs for arm-blind independent repair review.

This coordinator-only builder reads synthetic Direction H artifacts, validates
the frozen retry chain and every cross-record identity, and writes two separate
products: a reviewer-safe panel bundle and a coordinator-only arm map. It never
calls a model, invents a target brief, or creates an assessment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import warnings
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
        "No local Python runtime with jsonschema is available; no panel files were written."
    )

from format_feedback import project_feedback
from record_revision_output import (
    deterministic_output_id,
    expected_allocation_row,
    integrity_check as recorder_integrity_check,
)


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
COORDINATOR_ROOT = DIRECTION_ROOT / "coordinator_only"
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"

FREEZE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_freeze_manifest.schema.json"
CASE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_case.schema.json"
REVISION_OUTPUT_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_output.schema.json"
PANEL_ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_panel_item.schema.json"
PILOT_ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
CONSTRUCTION_SCHEMA = DIRECTION_ROOT / "schemas" / "construction_verification.schema.json"
TRUTH_SCHEMA = DIRECTION_ROOT / "schemas" / "truth_map.schema.json"
FEEDBACK_SCHEMA = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
QUALITATIVE_OUTPUT_SCHEMA = BASELINE_ROOT / "schemas" / "qualitative_output.schema.json"
RATING_SCHEMA = BASELINE_ROOT / "schemas" / "paper_metric_rating.schema.json"
RECORDER_SCRIPT = DIRECTION_ROOT / "scripts" / "record_revision_output.py"
PACKAGER_SCRIPT = Path(__file__).resolve()

FROZEN_ARTIFACT_ALLOWLIST = {
    "analytic_contract": (
        "qc-analytic-contract-v1",
        "experiments/qualitative_coding_baselines/protocol/analytic_contract.md",
    ),
    "revision_prompt": (
        "direction-h-revision-prompt-v1",
        "experiments/direction_h_human_in_loop/protocol/revision_prompt.md",
    ),
    "feedback_formatter": (
        "direction-h-feedback-formatter-v1",
        "experiments/direction_h_human_in_loop/scripts/format_feedback.py",
    ),
    "input_schema": (
        "direction-h-revision-case-v1",
        "experiments/direction_h_human_in_loop/schemas/revision_case.schema.json",
    ),
    "output_schema": (
        "direction-h-revision-output-v1",
        "experiments/direction_h_human_in_loop/schemas/revision_output.schema.json",
    ),
    "integrity_validator": (
        "qc-integrity-validator-v1",
        "experiments/qualitative_coding_baselines/scripts/validate_and_score.py",
    ),
    "revision_output_recorder": (
        "direction-h-revision-output-recorder-v1",
        "experiments/direction_h_human_in_loop/scripts/record_revision_output.py",
    ),
    "repair_panel_packager": (
        "direction-h-repair-panel-packager-v1",
        "experiments/direction_h_human_in_loop/scripts/prepare_repair_panel.py",
    ),
}

CHARLIE_RATER_ID = "charlie_dev_researcher_01"
RETRY_REASON_BY_FAILURE_CODE = {
    "no_response": "empty_response",
    "runtime_error": "transport_failure",
    "invalid_json": "invalid_json",
    "schema_invalid": "schema_invalid",
}
EXPECTED_FAILURE_CODES = {
    "parse_failure": {"invalid_json"},
    "schema_failure": {"schema_invalid"},
    "runtime_failure": {"no_response", "runtime_error", "recording_error"},
}
PUBLIC_FORBIDDEN_KEYS = {
    "feedback_arm",
    "feedback_record_id",
    "rater_id",
    "generator_model_id",
    "model_snapshot_id",
    "revision_case_id",
    "paired_case_group_id",
    "repeat_index",
    "attempt_index",
    "freeze_id",
    "completion_status",
    "revision_diagnosis",
    "failure_record",
    "integrity_validation",
    "condition",
    "truth_record",
    "target_defect",
}
BRIEF_FORBIDDEN_TOKENS = {
    "charlie",
    "no_feedback",
    "charlie_feedback",
    "independent_human_feedback",
    "controlled_defect",
    "no_planted_defect_control",
    "planted defect",
    "revision_diagnosis",
}

# These expressions target workflow self-disclosures, not ordinary discussion
# of feedback, people, arms, or models. Exact frozen arm/field labels are
# always diagnostic. Natural-language and model-identity matches are treated
# as disclosures only when the matched phrase was not already present in the
# reviewer-visible evidence packet or starting output; this prevents an exact
# source quote about (for example) an AI model from being mistaken for revision
# system leakage.
ALWAYS_BLOCK_DISCLOSURE_PATTERNS = (
    (
        "feedback_arm_label",
        re.compile(
            r"(?<![\w])(?:charlie|no|independent[\s_-]+human|reviewer)[\s_-]+feedback(?![\w])",
            re.IGNORECASE,
        ),
    ),
    (
        "feedback_arm_field",
        re.compile(r"(?<![\w])feedback[\s_-]+arm(?![\w])", re.IGNORECASE),
    ),
)
CONTEXTUAL_DISCLOSURE_PATTERNS = (
    (
        "charlie_identity_token",
        re.compile(r"\bcharlie\b", re.IGNORECASE),
    ),
    (
        "feedback_author_disclosure",
        re.compile(
            r"\b(?:charlie(?:['’]s)?\s+(?:feedback|comments?|suggestions?|instructions?)|"
            r"(?:feedback|comments?|suggestions?|instructions?)\s+(?:from|by|provided\s+by)\s+charlie)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "feedback_receipt_disclosure",
        re.compile(
            r"\b(?:based\s+on|following|after\s+receiving|in\s+response\s+to|"
            r"incorporat(?:e|ed|ing))\s+(?:the\s+)?reviewer(?:['’]s)?\s+feedback\b",
            re.IGNORECASE,
        ),
    ),
    (
        "arm_assignment_disclosure",
        re.compile(
            r"\b(?:assigned|allocated|placed)\s+(?:to|in)\s+(?:the\s+)?"
            r"(?:no[-\s]+feedback|charlie[-\s]+feedback|reviewer[-\s]+feedback|"
            r"feedback|treatment|experimental|revision)\s+(?:arm|condition)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "model_self_identification",
        re.compile(
            r"\b(?:as\s+an?\s+(?:ai|artificial[-\s]+intelligence|language\s+model)|"
            r"i\s+(?:am|['’]m)\s+an?\s+(?:ai|artificial[-\s]+intelligence|language\s+model)|"
            r"(?:as|i\s+(?:am|['’]m))\s+(?:chatgpt|claude|gemini|copilot|"
            r"gpt[-\s]*[0-9][\w.-]*)|"
            r"this\s+(?:answer|analysis|output|response|revision)\s+(?:was\s+)?"
            r"(?:generated|produced|written|revised)\s+by\s+an?\s+"
            r"(?:ai|artificial[-\s]+intelligence|language\s+model))\b",
            re.IGNORECASE,
        ),
    ),
)
ALLOCATION_VERSION = "direction-h-revision-allocation-v2"
ALLOCATION_ROW_KEYS = {
    "execution_sort",
    "revision_case_id",
    "blinded_revision_id",
    "model_blinded_case_id",
    "paired_case_group_id",
    "task_id",
    "repeat_index",
    "feedback_arm",
}
EXCLUSION_ROW_KEYS = {
    "task_id",
    "committed_condition",
    "committed_target_flag",
    "construction_disposition",
    "exclusion_reason",
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


class PackagingError(Exception):
    """A fail-closed precondition or packaging error."""


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise PackagingError(f"{label} is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - retain file context
        raise PackagingError(f"cannot read {label} as JSON ({path}): {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def rendered_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise PackagingError(f"{label} is not an ISO-8601 date-time") from exc
    if parsed.tzinfo is None:
        raise PackagingError(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "__REQUIRED" in value or value.startswith("FILL_") or value == "TBD"
    if isinstance(value, dict):
        return any(has_placeholder(nested) for nested in value.values())
    if isinstance(value, list):
        return any(has_placeholder(nested) for nested in value)
    return False


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def walk_string_values(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """Yield every string leaf with a deterministic JSON Pointer location."""

    if isinstance(value, dict):
        for key in sorted(value):
            yield from walk_string_values(
                value[key], f"{path}/{pointer_token(str(key))}"
            )
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from walk_string_values(nested, f"{path}/{index}")
    elif isinstance(value, str):
        yield path or "/", value


def normalize_disclosure_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def disclosure_screen_findings(
    revised_output: dict[str, Any],
    evidence_packet: dict[str, Any],
    original_output: dict[str, Any],
    freeze: dict[str, Any],
) -> list[dict[str, str]]:
    """Return diagnostic arm/author/model disclosures in a revised output.

    This is intentionally a narrow value-level screen. Machine-like arm labels
    block regardless of provenance. Contextual phrases and exact model
    identities block only when newly introduced by the revision; exact phrases
    already visible in the evidence/starting output are classified as inherited
    source content instead of model self-disclosure.
    """

    inherited_values = [
        normalize_disclosure_text(text)
        for source in (evidence_packet, original_output)
        for _, text in walk_string_values(source)
    ]

    dynamic_patterns: list[tuple[str, re.Pattern[str]]] = []
    for key in ("model_id", "snapshot_id"):
        identifier = str(freeze["revision_model"].get(key, "")).strip()
        if identifier and not has_placeholder(identifier):
            dynamic_patterns.append(
                (
                    f"frozen_{key}_disclosure",
                    re.compile(
                        rf"(?<![\w]){re.escape(normalize_disclosure_text(identifier))}(?![\w])",
                        re.IGNORECASE,
                    ),
                )
            )

    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for pointer, raw_text in walk_string_values(revised_output):
        text = normalize_disclosure_text(raw_text)
        for code, pattern in ALWAYS_BLOCK_DISCLOSURE_PATTERNS:
            for match in pattern.finditer(text):
                matched = match.group(0)
                inherited = any(matched in source for source in inherited_values)
                key = (code, pointer, matched)
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        {
                            "code": code,
                            "location": pointer,
                            "provenance": (
                                "also_present_in_evidence_or_starting_output"
                                if inherited
                                else "introduced_or_modified_in_revision"
                            ),
                        }
                    )
        for code, pattern in (*CONTEXTUAL_DISCLOSURE_PATTERNS, *dynamic_patterns):
            for match in pattern.finditer(text):
                matched = match.group(0)
                if any(matched in source for source in inherited_values):
                    continue
                key = (code, pointer, matched)
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        {
                            "code": code,
                            "location": pointer,
                            "provenance": "introduced_or_modified_in_revision",
                        }
                    )
    return sorted(
        findings,
        key=lambda row: (row["location"], row["code"], row["provenance"]),
    )


def screen_revised_output_disclosures(
    record: dict[str, Any], case: dict[str, Any], freeze: dict[str, Any]
) -> None:
    """Fail closed on a public-blinding disclosure; never redact or substitute."""

    findings = disclosure_screen_findings(
        record["revised_output"],
        case["model_input"]["evidence_packet"],
        case["model_input"]["original_output"],
        freeze,
    )
    if not findings:
        return
    diagnostic = ", ".join(
        f"{row['code']}@{row['location']}[{row['provenance']}]"
        for row in findings[:12]
    )
    if len(findings) > 12:
        diagnostic += f", plus {len(findings) - 12} additional match(es)"
    raise PackagingError(
        f"revision output {record['revision_output_id']} contains diagnostic "
        f"arm/author/model disclosure(s): {diagnostic}. Treat this as a protocol "
        "deviation under the frozen handling rule; do not redact, rewrite, or "
        "substitute another attempt/repeat"
    )


def require_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise PackagingError(f"{label} must stay under {root}: {path}") from exc
    return resolved


def require_regular_file(path: Path, root: Path, label: str) -> Path:
    if path.is_symlink():
        raise PackagingError(f"{label} may not be a symlink: {path}")
    resolved = require_within(path, root, label)
    if not resolved.is_file():
        raise PackagingError(f"{label} is missing or not a regular file: {path}")
    return resolved


def project_path(relative_path: str, label: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        raise PackagingError(f"frozen {label} path must be project-relative")
    return require_within(PROJECT_ROOT / path, PROJECT_ROOT, f"frozen {label}")


def schema_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in (
        FREEZE_SCHEMA,
        CASE_SCHEMA,
        REVISION_OUTPUT_SCHEMA,
        PANEL_ITEM_SCHEMA,
        PILOT_ITEM_SCHEMA,
        CONSTRUCTION_SCHEMA,
        TRUTH_SCHEMA,
        FEEDBACK_SCHEMA,
        QUALITATIVE_OUTPUT_SCHEMA,
        RATING_SCHEMA,
    ):
        schema = load_json(path, f"schema {path.name}")
        if schema.get("$id"):
            store[schema["$id"]] = schema
    return store


def validate(instance: Any, schema_path: Path, label: str) -> None:
    schema = load_json(schema_path, f"schema {schema_path.name}")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=schema_store()),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise PackagingError(f"{label} fails {schema_path.name}: {rendered}")


def verify_freeze(path: Path) -> dict[str, Any]:
    path = require_regular_file(path, DIRECTION_ROOT, "revision freeze")
    freeze = load_json(path, "revision freeze")
    if has_placeholder(freeze):
        raise PackagingError("revision freeze contains a required placeholder")
    validate(freeze, FREEZE_SCHEMA, "revision freeze")
    if freeze["status"] != "frozen" or freeze["freeze_scope"] != "synthetic_pilot":
        raise PackagingError("repair-panel v1 requires a frozen synthetic_pilot manifest")
    governance = freeze["data_governance"]
    if governance["data_scope"] != "synthetic_only" or governance["contains_protected_text"] is not False:
        raise PackagingError("repair-panel v1 refuses protected or non-synthetic material")
    for key, (allowed_version, allowed_path) in FROZEN_ARTIFACT_ALLOWLIST.items():
        artifact = freeze[key]
        if artifact["version"] != allowed_version or artifact["path"] != allowed_path:
            raise PackagingError(
                f"frozen {key} must use the approved synthetic path and version"
            )
        artifact_path = project_path(artifact["path"], key)
        artifact_path = require_regular_file(artifact_path, PROJECT_ROOT, f"frozen {key}")
        if sha256_file(artifact_path) != artifact["sha256"]:
            raise PackagingError(f"frozen artifact is missing or hash-drifted: {key}")
    return freeze


def load_public_pilot() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = require_regular_file(
        PILOT_ROOT / "manifest.json", PILOT_ROOT, "public pilot manifest"
    )
    manifest = load_json(manifest_path, "public pilot manifest")
    if manifest.get("data_scope") != "synthetic_only" or manifest.get("contains_real_source_text") is not False:
        raise PackagingError("public pilot manifest is not explicitly synthetic-only")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or manifest.get("task_count") != len(tasks) or not tasks:
        raise PackagingError("public pilot manifest has an invalid task inventory")
    items: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task_id in items:
            raise PackagingError("public pilot manifest has a missing or duplicate task_id")
        item_path = require_regular_file(
            PILOT_ROOT / str(task.get("item_file", "")), PILOT_ROOT / "items", task_id
        )
        if task.get("sha256") != sha256_file(item_path):
            raise PackagingError(f"public pilot item hash drifted: {task_id}")
        item = load_json(item_path, f"public pilot item {task_id}")
        validate(item, PILOT_ITEM_SCHEMA, f"public pilot item {task_id}")
        component_hashes = {
            "evidence_packet_sha256": sha256_bytes(
                canonical_bytes(item["evidence_packet"])
            ),
            "candidate_output_sha256": sha256_bytes(
                canonical_bytes(item["candidate_output"])
            ),
        }
        for key, expected_hash in component_hashes.items():
            if task.get(key) != expected_hash:
                raise PackagingError(
                    f"public pilot component hash is missing or drifted for {task_id}: {key}"
                )
        if item["data_classification"] != "synthetic_cc0":
            raise PackagingError(f"public pilot item is not synthetic_cc0: {task_id}")
        for key in ("task_id", "packet_id", "corpus_id", "evaluation_role", "output_id"):
            if item.get(key) != task.get(key):
                raise PackagingError(f"public manifest/item {key} mismatch for {task_id}")
        packet = item["evidence_packet"]
        output = item["candidate_output"]
        if packet["packet_id"] != item["packet_id"] or output["packet_id"] != item["packet_id"]:
            raise PackagingError(f"packet identity mismatch in public item {task_id}")
        if output["research_question"] != packet["research_question"]:
            raise PackagingError(f"research-question drift in public item {task_id}")
        items[task_id] = item
    return manifest, items


def verify_review_lock(manifest: dict[str, Any]) -> dict[str, Any]:
    lock_path = require_regular_file(
        PILOT_ROOT / "review_lock.json", PILOT_ROOT, "Charlie review lock"
    )
    lock = load_json(lock_path, "Charlie review lock")
    expected_task_ids = [row["task_id"] for row in manifest["tasks"]]
    condition_commitment_path = require_regular_file(
        PILOT_ROOT / "condition_commitment.json",
        PILOT_ROOT,
        "public condition commitment",
    )
    expected = {
        "review_lock_version": "direction-h-review-lock-v1",
        "study_id": manifest["study_id"],
        "rater_id": CHARLIE_RATER_ID,
        "task_count": len(expected_task_ids),
        "manifest_sha256": sha256_file(PILOT_ROOT / "manifest.json"),
        "condition_commitment_sha256": sha256_file(condition_commitment_path),
        "truth_opened_by_this_step": False,
        "ratings_or_feedback_modified_by_this_step": False,
    }
    for key, expected_value in expected.items():
        if lock.get(key) != expected_value:
            raise PackagingError(f"review lock is missing or drifted at {key}")
    records = lock.get("records")
    if not isinstance(records, list) or [row.get("task_id") for row in records] != expected_task_ids:
        raise PackagingError("review lock task order or coverage differs from the pilot")
    for row in records:
        task_id = row["task_id"]
        expected_rating = Path("responses") / "ratings" / f"{task_id}.json"
        expected_feedback = Path("responses") / "feedback" / f"{task_id}.json"
        if Path(str(row.get("rating_file", ""))) != expected_rating:
            raise PackagingError(f"unexpected locked rating path for {task_id}")
        if Path(str(row.get("feedback_file", ""))) != expected_feedback:
            raise PackagingError(f"unexpected locked feedback path for {task_id}")
        rating_path = require_regular_file(
            PILOT_ROOT / expected_rating, PILOT_ROOT / "responses" / "ratings", "locked rating"
        )
        feedback_path = require_regular_file(
            PILOT_ROOT / expected_feedback,
            PILOT_ROOT / "responses" / "feedback",
            "locked feedback",
        )
        if row.get("rating_sha256") != sha256_file(rating_path):
            raise PackagingError(f"locked rating is missing or drifted for {task_id}")
        if row.get("feedback_sha256") != sha256_file(feedback_path):
            raise PackagingError(f"locked feedback is missing or drifted for {task_id}")
    return lock


def verify_construction(
    path: Path, manifest: dict[str, Any]
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    set[str],
    list[dict[str, Any]],
]:
    path = require_regular_file(path, COORDINATOR_ROOT, "construction verification")
    verification = load_json(path, "independent construction verification")
    if has_placeholder(verification):
        raise PackagingError("construction verification still contains placeholders")
    validate(verification, CONSTRUCTION_SCHEMA, "independent construction verification")
    if verification["study_id"] != manifest["study_id"]:
        raise PackagingError("construction verification and pilot study_id differ")
    if (
        str(verification["verifier_id"]).strip().casefold()
        == CHARLIE_RATER_ID.casefold()
        or verification["verifier_is_charlie"] is not False
        or verification["verifier_helped_construct_items"] is not False
    ):
        raise PackagingError("target briefs require a non-Charlie independent constructor check")
    truth_path = require_regular_file(
        COORDINATOR_ROOT / "truth_map.json", COORDINATOR_ROOT, "coordinator truth map"
    )
    commitment_path = require_regular_file(
        PILOT_ROOT / "condition_commitment.json", PILOT_ROOT, "public condition commitment"
    )
    truth = load_json(truth_path, "coordinator truth map")
    commitment = load_json(commitment_path, "public condition commitment")
    validate(truth, TRUTH_SCHEMA, "coordinator truth map")
    truth_hash = sha256_bytes(canonical_bytes(truth))
    if commitment.get("truth_map_sha256") != truth_hash:
        raise PackagingError("truth map does not match the pre-rating public commitment")
    if verification["truth_map_sha256"] != truth_hash:
        raise PackagingError("construction verification cites a different truth map")
    if truth["study_id"] != manifest["study_id"]:
        raise PackagingError("truth map and pilot study_id differ")

    truth_by_task = {row["task_id"]: row for row in truth["items"]}
    verification_by_task = {row["task_id"]: row for row in verification["items"]}
    manifest_tasks = {row["task_id"] for row in manifest["tasks"]}
    if set(truth_by_task) != manifest_tasks or set(verification_by_task) != manifest_tasks:
        raise PackagingError("pilot, truth-map, and construction-verification task sets differ")

    target_tasks: set[str] = set()
    excluded_items: list[dict[str, Any]] = []
    for task_id in sorted(manifest_tasks):
        truth_row = truth_by_task[task_id]
        checked = verification_by_task[task_id]
        expected_flag = (
            truth_row["planted_defect"]["target_flag"]
            if truth_row["planted_defect"] is not None
            else None
        )
        if checked["intended_condition"] != truth_row["condition"]:
            raise PackagingError(f"verified condition does not match committed truth: {task_id}")
        if checked["intended_target_flag"] != expected_flag:
            raise PackagingError(f"verified target flag does not match committed truth: {task_id}")
        is_verified_target = (
            truth_row["condition"] == "controlled_defect"
            and checked["disposition"] == "verified_for_detection"
        )
        if is_verified_target:
            target_tasks.add(task_id)
        else:
            if checked["disposition"] == "workflow_only":
                reason = "construction_workflow_only"
            elif checked["disposition"] == "reject_item":
                reason = "construction_reject_item"
            else:
                reason = "verified_no_planted_defect_control_not_target_repair"
            excluded_items.append(
                {
                    "task_id": task_id,
                    "committed_condition": truth_row["condition"],
                    "committed_target_flag": expected_flag,
                    "construction_disposition": checked["disposition"],
                    "exclusion_reason": reason,
                }
            )
    if not target_tasks:
        raise PackagingError("construction verification contains no eligible target-defect task")
    return verification, verification_by_task, target_tasks, excluded_items


def load_target_briefs(
    path: Path,
    verification_path: Path,
    verification: dict[str, Any],
    study_id: str,
    target_tasks: set[str],
    freeze: dict[str, Any],
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    path = require_regular_file(path, COORDINATOR_ROOT, "target-assessment briefs")
    briefs = load_json(path, "target-assessment briefs")
    required = {
        "target_briefs_version",
        "study_id",
        "construction_verification_file_sha256",
        "prepared_by_id",
        "prepared_by_is_charlie",
        "prepared_at_utc",
        "contains_feedback_arm",
        "contains_model_identity",
        "items",
    }
    if not isinstance(briefs, dict) or set(briefs) != required:
        raise PackagingError(
            "target-assessment briefs must contain exactly: " + ", ".join(sorted(required))
        )
    if briefs["target_briefs_version"] != "direction-h-target-assessment-briefs-v1":
        raise PackagingError("unsupported target-assessment brief version")
    if briefs["study_id"] != study_id:
        raise PackagingError("target briefs and pilot study_id differ")
    if briefs["construction_verification_file_sha256"] != sha256_file(verification_path):
        raise PackagingError("target briefs do not cite the exact construction-verification file")
    if (
        str(briefs["prepared_by_id"]).strip().casefold()
        == CHARLIE_RATER_ID.casefold()
        or briefs["prepared_by_is_charlie"] is not False
    ):
        raise PackagingError("Charlie may not prepare target-assessment briefs for this panel")
    if briefs["contains_feedback_arm"] is not False or briefs["contains_model_identity"] is not False:
        raise PackagingError("target-assessment briefs assert a prohibited disclosure")
    if parse_datetime(briefs["prepared_at_utc"], "target briefs prepared_at_utc") < parse_datetime(
        verification["verified_at_utc"], "construction verified_at_utc"
    ):
        raise PackagingError("target-assessment briefs predate independent construction verification")
    if has_placeholder(briefs):
        raise PackagingError("target-assessment briefs still contain placeholders")
    rows = briefs["items"]
    if not isinstance(rows, list) or not rows:
        raise PackagingError("target-assessment briefs must contain a non-empty items array")
    by_task: dict[str, dict[str, str]] = {}
    reference_ids: set[str] = set()
    expected_row_keys = {
        "task_id",
        "target_assessment_reference_id",
        "target_assessment_brief",
    }
    forbidden_tokens = set(BRIEF_FORBIDDEN_TOKENS)
    for model_key in ("provider", "model_id", "snapshot_id"):
        token = str(freeze["revision_model"][model_key]).strip().casefold()
        if len(token) >= 4:
            forbidden_tokens.add(token)
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_row_keys:
            raise PackagingError("each target brief row must contain exactly the three documented fields")
        task_id = row["task_id"]
        reference_id = row["target_assessment_reference_id"]
        brief = row["target_assessment_brief"]
        if task_id in by_task or not isinstance(task_id, str):
            raise PackagingError("target briefs contain a missing or duplicate task_id")
        if not isinstance(reference_id, str) or not re.fullmatch(
            r"TAR-[A-F0-9]{16}", reference_id
        ):
            raise PackagingError(
                f"target_assessment_reference_id for {task_id} must be opaque TAR- plus 16 hex characters"
            )
        if reference_id in reference_ids:
            raise PackagingError(f"duplicate target_assessment_reference_id: {reference_id}")
        if not isinstance(brief, str) or not 1 <= len(brief.strip()) <= 3000:
            raise PackagingError(f"invalid target_assessment_brief for {task_id}")
        lowered = brief.casefold()
        lowered_reference = reference_id.casefold()
        leaked = sorted(
            token
            for token in forbidden_tokens
            if token in lowered or token in lowered_reference
        )
        if leaked:
            raise PackagingError(f"target brief {task_id} contains prohibited disclosure token(s)")
        reference_ids.add(reference_id)
        by_task[task_id] = {
            "target_assessment_reference_id": reference_id,
            "target_assessment_brief": brief.strip(),
        }
    if set(by_task) != target_tasks:
        raise PackagingError("target briefs must cover exactly the independently verified defect tasks")
    return by_task, briefs


def load_brief_commitment(
    path: Path,
    briefs_path: Path,
    verification_path: Path,
    briefs: dict[str, Any],
    verification: dict[str, Any],
    study_id: str,
) -> dict[str, Any]:
    """Verify the immutable, pre-revision commitment to the completed briefs."""

    path = require_regular_file(path, COORDINATOR_ROOT, "target-brief commitment")
    commitment = load_json(path, "target-brief commitment")
    if not isinstance(commitment, dict) or set(commitment) != BRIEF_COMMITMENT_KEYS:
        raise PackagingError(
            "target-brief commitment must contain exactly: "
            + ", ".join(sorted(BRIEF_COMMITMENT_KEYS))
        )
    if has_placeholder(commitment):
        raise PackagingError("target-brief commitment still contains placeholders")
    if commitment["commitment_version"] != "direction-h-target-assessment-briefs-commitment-v1":
        raise PackagingError("unsupported target-brief commitment version")
    if commitment["study_id"] != study_id or commitment["visibility"] != "coordinator_only":
        raise PackagingError("target-brief commitment identity or visibility differs")
    expected_briefs_path = str(briefs_path.resolve().relative_to(DIRECTION_ROOT.resolve()))
    if commitment["target_briefs_path"] != expected_briefs_path:
        raise PackagingError("target-brief commitment cites a different briefs path")
    if commitment["target_briefs_file_sha256"] != sha256_file(briefs_path):
        raise PackagingError("completed target briefs differ from their committed hash")
    if commitment["construction_verification_file_sha256"] != sha256_file(
        verification_path
    ):
        raise PackagingError("target-brief commitment cites a different verification file")
    committed_by_id = commitment["committed_by_id"]
    if (
        not isinstance(committed_by_id, str)
        or not 1 <= len(committed_by_id.strip()) <= 160
        or committed_by_id.strip().casefold() == CHARLIE_RATER_ID.casefold()
        or commitment["committed_by_is_charlie"] is not False
    ):
        raise PackagingError("target-assessment briefs require a non-Charlie committer pseudonym")
    if commitment["briefs_complete"] is not True or commitment[
        "immutable_before_revision_generation"
    ] is not True:
        raise PackagingError("target-brief commitment does not freeze a complete pre-revision file")
    verified_at = parse_datetime(
        verification["verified_at_utc"], "construction verified_at_utc"
    )
    prepared_at = parse_datetime(briefs["prepared_at_utc"], "target briefs prepared_at_utc")
    committed_at = parse_datetime(
        commitment["committed_at_utc"], "target briefs committed_at_utc"
    )
    if prepared_at < verified_at:
        raise PackagingError("target-assessment briefs predate construction verification")
    if committed_at < prepared_at:
        raise PackagingError("target-brief commitment predates brief preparation")
    return commitment


def load_allocation_and_cases(
    freeze: dict[str, Any],
    manifest: dict[str, Any],
    public_items: dict[str, dict[str, Any]],
    review_lock: dict[str, Any],
    verification: dict[str, Any],
    verification_path: Path,
    briefs_path: Path,
    brief_commitment: dict[str, Any],
    brief_commitment_path: Path,
    target_tasks: set[str],
    excluded_items: list[dict[str, Any]],
) -> tuple[dict[str, Any], str, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    allocation_path = require_regular_file(
        COORDINATOR_ROOT / "revision_allocation.json",
        COORDINATOR_ROOT,
        "revision allocation",
    )
    allocation = load_json(allocation_path, "revision allocation")
    if not isinstance(allocation, dict) or set(allocation) != ALLOCATION_TOP_KEYS:
        raise PackagingError("revision allocation top-level fields differ from the v2 contract")
    if allocation.get("allocation_version") != ALLOCATION_VERSION:
        raise PackagingError("unsupported revision allocation version")
    if allocation.get("study_id") != manifest["study_id"] or allocation.get("freeze_id") != freeze["freeze_id"]:
        raise PackagingError("revision allocation identity differs from pilot/freeze")
    rows = allocation.get("cases")
    if not isinstance(rows, list) or not rows:
        raise PackagingError("revision allocation has no cases")
    expected_metadata = {
        "construction_overall_disposition": verification["overall_disposition"],
        "construction_verification_file_sha256": sha256_file(verification_path),
        "target_briefs_file_sha256": sha256_file(briefs_path),
        "target_briefs_commitment_file_sha256": sha256_file(brief_commitment_path),
        "target_briefs_committed_at_utc": brief_commitment["committed_at_utc"],
        "eligible_target_task_ids": sorted(target_tasks),
        "excluded_items": excluded_items,
        "eligibility_rule": (
            "committed controlled_defect AND item disposition verified_for_detection"
        ),
        "execution_order_balanced_by": "sha256 of frozen case identity",
    }
    for key, expected_value in expected_metadata.items():
        if allocation.get(key) != expected_value:
            raise PackagingError(f"revision allocation eligibility metadata drifted: {key}")
    if parse_datetime(
        allocation["created_at_utc"], "revision allocation created_at_utc"
    ) <= parse_datetime(
        brief_commitment["committed_at_utc"], "target briefs committed_at_utc"
    ):
        raise PackagingError("revision allocation was not created after the target briefs froze")
    allocation_hash = sha256_bytes(canonical_bytes(allocation))
    arms = list(freeze["arm_policy"]["arms"])
    repeats = int(freeze["repeat_policy"]["repeats_per_arm"])
    expected = {
        (task_id, repeat_index, arm)
        for task_id in target_tasks
        for repeat_index in range(1, repeats + 1)
        for arm in arms
    }
    observed: set[tuple[str, int, str]] = set()
    rows_by_case: dict[str, dict[str, Any]] = {}
    blind_ids: set[str] = set()
    pairs: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != ALLOCATION_ROW_KEYS:
            raise PackagingError("revision allocation row differs from the v2 contract")
        identity = (row["task_id"], row["repeat_index"], row["feedback_arm"])
        if row != expected_allocation_row(
            freeze["freeze_id"], row["task_id"], row["repeat_index"], row["feedback_arm"]
        ):
            raise PackagingError(f"revision allocation row is hash-inconsistent: {identity}")
        if identity in observed:
            raise PackagingError(f"duplicate revision allocation identity: {identity}")
        observed.add(identity)
        case_id = row["revision_case_id"]
        if case_id in rows_by_case:
            raise PackagingError(f"duplicate revision_case_id: {case_id}")
        if row["blinded_revision_id"] in blind_ids:
            raise PackagingError(f"duplicate blinded_revision_id: {row['blinded_revision_id']}")
        rows_by_case[case_id] = row
        blind_ids.add(row["blinded_revision_id"])
        pairs.setdefault((row["task_id"], row["repeat_index"]), []).append(row)
    if observed != expected:
        raise PackagingError(
            "revision allocation does not cover the eligible-target/repeat/arm product"
        )
    for pair_key, pair_rows in pairs.items():
        if {row["feedback_arm"] for row in pair_rows} != set(arms):
            raise PackagingError(f"revision pair does not cover every arm: {pair_key}")
        if len({row["paired_case_group_id"] for row in pair_rows}) != 1:
            raise PackagingError(f"paired_case_group_id differs within pair: {pair_key}")
        if len({row["model_blinded_case_id"] for row in pair_rows}) != 1:
            raise PackagingError(f"model_blinded_case_id differs within pair: {pair_key}")

    feedback_by_task: dict[str, dict[str, Any]] = {}
    for lock_row in review_lock["records"]:
        task_id = lock_row["task_id"]
        rating_path = require_regular_file(
            PILOT_ROOT / lock_row["rating_file"],
            PILOT_ROOT / "responses" / "ratings",
            f"locked rating {task_id}",
        )
        feedback_path = require_regular_file(
            PILOT_ROOT / lock_row["feedback_file"],
            PILOT_ROOT / "responses" / "feedback",
            f"locked feedback {task_id}",
        )
        if sha256_file(rating_path) != lock_row["rating_sha256"]:
            raise PackagingError(f"locked rating drifted before case verification: {task_id}")
        if sha256_file(feedback_path) != lock_row["feedback_sha256"]:
            raise PackagingError(f"locked feedback drifted before case verification: {task_id}")
        rating = load_json(rating_path, f"locked rating {task_id}")
        feedback = load_json(feedback_path, f"locked feedback {task_id}")
        validate(rating, RATING_SCHEMA, f"locked rating {task_id}")
        validate(feedback, FEEDBACK_SCHEMA, f"locked feedback {task_id}")
        item = public_items[task_id]
        if feedback.get("pilot_item_id") != task_id:
            raise PackagingError(f"locked feedback pilot_item_id mismatch: {task_id}")
        rating_key = feedback["rating_key"]
        for key in ("annotation_version", "rater_id", "packet_id", "output_id", "rated_at_utc"):
            if rating_key.get(key) != rating.get(key):
                raise PackagingError(
                    f"locked feedback/rating linkage mismatch for {task_id}: {key}"
                )
        if rating_key.get("rating_record_sha256") != sha256_bytes(canonical_bytes(rating)):
            raise PackagingError(f"locked feedback canonical rating hash mismatch: {task_id}")
        if (
            rating.get("rater_id") != CHARLIE_RATER_ID
            or rating.get("packet_id") != item["packet_id"]
            or rating.get("output_id") != item["output_id"]
        ):
            raise PackagingError(f"locked rating/item linkage mismatch: {task_id}")
        feedback_by_task[task_id] = feedback

    case_dir = COORDINATOR_ROOT / "revision_cases"
    if case_dir.is_symlink() or not case_dir.is_dir():
        raise PackagingError(f"revision case directory is missing: {case_dir}")
    case_paths = sorted(case_dir.glob("*.json"))
    cases: dict[str, dict[str, Any]] = {}
    for path in case_paths:
        path = require_regular_file(path, case_dir, f"revision case {path.name}")
        case = load_json(path, f"revision case {path.name}")
        validate(case, CASE_SCHEMA, f"revision case {path.name}")
        case_id = case["revision_case_id"]
        if case_id in cases:
            raise PackagingError(f"duplicate stored revision case: {case_id}")
        cases[case_id] = case
    if set(cases) != set(rows_by_case):
        raise PackagingError("stored revision-case set differs from the frozen allocation")

    for case_id, case in cases.items():
        row = rows_by_case[case_id]
        item = public_items[row["task_id"]]
        expected_fields = {
            "revision_case_id": row["revision_case_id"],
            "paired_case_group_id": row["paired_case_group_id"],
            "repeat_index": row["repeat_index"],
            "task_id": row["task_id"],
            "packet_id": item["packet_id"],
            "output_id": item["output_id"],
            "freeze_id": freeze["freeze_id"],
            "feedback_arm": row["feedback_arm"],
        }
        for key, expected_value in expected_fields.items():
            if case.get(key) != expected_value:
                raise PackagingError(f"revision case/allocation mismatch for {case_id}: {key}")
        if case["allocation_record_sha256"] != allocation_hash:
            raise PackagingError(f"revision case cites a different allocation: {case_id}")
        if case["model_input_sha256"] != sha256_bytes(canonical_bytes(case["model_input"])):
            raise PackagingError(f"revision case model_input hash mismatch: {case_id}")
        model_input = case["model_input"]
        if model_input["blinded_case_id"] != row["model_blinded_case_id"]:
            raise PackagingError(f"model blind ID mismatch: {case_id}")
        if model_input["evidence_packet"] != item["evidence_packet"]:
            raise PackagingError(f"revision case evidence packet drift: {case_id}")
        if model_input["original_output"] != item["candidate_output"]:
            raise PackagingError(f"revision case original output drift: {case_id}")
        if case["feedback_arm"] == "no_feedback":
            expected_feedback = None
            expected_feedback_id = None
        elif case["feedback_arm"] == "charlie_feedback":
            feedback_record = feedback_by_task[case["task_id"]]
            try:
                expected_feedback = project_feedback(feedback_record)
            except ValueError as exc:
                raise PackagingError(
                    f"locked feedback cannot be projected by the frozen formatter: {case_id}"
                ) from exc
            expected_feedback_id = feedback_record["feedback_id"]
        else:
            raise PackagingError(f"unsupported synthetic-pilot feedback arm: {case_id}")
        if case["feedback_record_id"] != expected_feedback_id:
            raise PackagingError(f"revision case feedback_record_id drift: {case_id}")
        if model_input["reviewer_feedback"] != expected_feedback:
            raise PackagingError(f"revision case feedback projection drift: {case_id}")
        materialized_path = require_regular_file(
            PILOT_ROOT / "revision_model_inputs" / f"{case_id}.json",
            PILOT_ROOT / "revision_model_inputs",
            f"materialized revision model input {case_id}",
        )
        if load_json(materialized_path, f"materialized model input {case_id}") != model_input:
            raise PackagingError(f"materialized model input differs from coordinator case: {case_id}")
        serialized_input = canonical_bytes(model_input).decode("utf-8").casefold()
        if "charlie" in serialized_input or '"rater_id"' in serialized_input:
            raise PackagingError(f"rater identity leaked into model input: {case_id}")

    for pair_key, pair_rows in pairs.items():
        projections: list[dict[str, Any]] = []
        for row in pair_rows:
            projection = dict(cases[row["revision_case_id"]]["model_input"])
            projection.pop("reviewer_feedback")
            projections.append(projection)
        if any(value != projections[0] for value in projections[1:]):
            raise PackagingError(f"paired model inputs differ outside reviewer_feedback: {pair_key}")
    return allocation, allocation_hash, rows_by_case, cases


def load_revision_outputs(
    output_dir: Path,
    freeze: dict[str, Any],
    rows_by_case: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    target_tasks: set[str],
    brief_commitment: dict[str, Any],
) -> tuple[
    dict[str, tuple[dict[str, Any], Path]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    require_within(output_dir, COORDINATOR_ROOT, "revision-output directory")
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise PackagingError(f"revision-output directory is missing: {output_dir}")
    paths = sorted(output_dir.glob("*.json"))
    if not paths:
        raise PackagingError(f"revision-output directory contains no JSON envelopes: {output_dir}")
    maximum_attempts = int(freeze["retry_policy"]["maximum_attempts"])
    outputs_by_case: dict[str, list[tuple[dict[str, Any], Path]]] = {}
    revision_output_ids: set[str] = set()
    attempt_keys: set[tuple[str, int]] = set()
    for path in paths:
        path = require_regular_file(path, output_dir, f"revision output {path.name}")
        record = load_json(path, f"revision output {path.name}")
        validate(record, REVISION_OUTPUT_SCHEMA, f"revision output {path.name}")
        output_id = record["revision_output_id"]
        case_id = record["revision_case_id"]
        if output_id in revision_output_ids:
            raise PackagingError(f"duplicate revision_output_id: {output_id}")
        if case_id not in cases:
            raise PackagingError(f"revision output cites an unknown revision case: {output_id}")
        expected_output_id = deterministic_output_id(
            freeze["freeze_id"], case_id, record["attempt_index"]
        )
        expected_filename = f"{case_id}.attempt-{record['attempt_index']:03d}.json"
        if output_id != expected_output_id or path.name != expected_filename:
            raise PackagingError(
                f"revision output deterministic ID/file name mismatch: {output_id}"
            )
        attempt_key = (case_id, record["attempt_index"])
        if attempt_key in attempt_keys:
            raise PackagingError(f"duplicate revision attempt: {attempt_key}")
        revision_output_ids.add(output_id)
        attempt_keys.add(attempt_key)
        if record["attempt_index"] > maximum_attempts:
            raise PackagingError(f"revision attempt exceeds frozen maximum: {output_id}")
        case = cases[case_id]
        allocation = rows_by_case[case_id]
        expected_fields = {
            "blinded_revision_id": allocation["blinded_revision_id"],
            "paired_case_group_id": case["paired_case_group_id"],
            "repeat_index": case["repeat_index"],
            "task_id": case["task_id"],
            "packet_id": case["packet_id"],
            "starting_output_id": case["output_id"],
            "freeze_id": freeze["freeze_id"],
            "feedback_arm": case["feedback_arm"],
            "generator_model_id": freeze["revision_model"]["model_id"],
            "model_snapshot_id": freeze["revision_model"]["snapshot_id"],
        }
        for key, expected_value in expected_fields.items():
            if record.get(key) != expected_value:
                raise PackagingError(f"revision output/case mismatch for {output_id}: {key}")
        generated_at = parse_datetime(
            record["generated_at_utc"], f"{output_id} generated_at_utc"
        )
        validated_at = parse_datetime(
            record["integrity_validation"]["validated_at_utc"],
            f"{output_id} integrity validated_at_utc",
        )
        if generated_at < parse_datetime(freeze["frozen_at_utc"], "freeze frozen_at_utc"):
            raise PackagingError(f"revision output predates its freeze: {output_id}")
        if generated_at <= parse_datetime(
            brief_commitment["committed_at_utc"], "target briefs committed_at_utc"
        ):
            raise PackagingError(
                f"revision output does not postdate the frozen target briefs: {output_id}"
            )
        if generated_at <= parse_datetime(case["created_at_utc"], f"{case_id} created_at_utc"):
            raise PackagingError(f"revision output does not postdate its case: {output_id}")
        if validated_at < generated_at:
            raise PackagingError(f"revision integrity validation predates generation: {output_id}")
        if record["completion_status"] == "complete":
            revised = record["revised_output"]
            packet = case["model_input"]["evidence_packet"]
            if record["revised_output_sha256"] != sha256_bytes(canonical_bytes(revised)):
                raise PackagingError(f"revised output hash mismatch: {output_id}")
            if revised["packet_id"] != packet["packet_id"]:
                raise PackagingError(f"revised output packet_id drift: {output_id}")
            if revised["research_question"] != packet["research_question"]:
                raise PackagingError(f"revised output research-question drift: {output_id}")
            # Screen every complete envelope before attempt selection. A
            # disclosure is a protocol deviation, not a reason to redact or to
            # choose a different attempt/repeat that happens to look safer.
            screen_revised_output_disclosures(record, case, freeze)
            recomputed_issues, recomputed_hard_gate = recorder_integrity_check(
                {
                    "revision_diagnosis": record["revision_diagnosis"],
                    "revised_output": revised,
                },
                case,
            )
            stored_integrity = record["integrity_validation"]
            if stored_integrity["hard_gate_pass"] is not recomputed_hard_gate:
                raise PackagingError(
                    f"stored/recomputed hard-gate status differs for {output_id}: "
                    + (", ".join(recomputed_issues) if recomputed_issues else "stored false")
                )
            if stored_integrity["issue_codes"] != recomputed_issues:
                raise PackagingError(
                    f"stored/recomputed integrity issue codes differ for {output_id}"
                )
        else:
            failure_code = record["failure_record"]["failure_code"]
            expected_codes = EXPECTED_FAILURE_CODES[record["completion_status"]]
            if failure_code not in expected_codes:
                raise PackagingError(f"failure envelope status/code mismatch: {output_id}")
        outputs_by_case.setdefault(case_id, []).append((record, path))

    missing_cases = set(cases) - set(outputs_by_case)
    if missing_cases:
        raise PackagingError(
            "allocated revision cases lack attempt envelopes: "
            + ", ".join(sorted(missing_cases))
        )

    selected: dict[str, tuple[dict[str, Any], Path]] = {}
    inventory: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    allowed_reasons = set(freeze["retry_policy"]["allowed_retry_reasons"])
    for case_id, attempts in sorted(outputs_by_case.items()):
        attempts.sort(key=lambda pair: pair[0]["attempt_index"])
        indices = [pair[0]["attempt_index"] for pair in attempts]
        if indices != list(range(1, len(indices) + 1)):
            raise PackagingError(f"revision attempt indices are not contiguous from 1: {case_id}")
        for (prior, _), (later, _) in zip(attempts, attempts[1:]):
            prior_generated = parse_datetime(
                prior["generated_at_utc"], f"{prior['revision_output_id']} generated_at_utc"
            )
            prior_validated = parse_datetime(
                prior["integrity_validation"]["validated_at_utc"],
                f"{prior['revision_output_id']} validated_at_utc",
            )
            later_generated = parse_datetime(
                later["generated_at_utc"], f"{later['revision_output_id']} generated_at_utc"
            )
            if later_generated <= prior_generated or later_generated < prior_validated:
                raise PackagingError(f"revision retry timestamps are not causal: {case_id}")
        for position, (record, _) in enumerate(attempts[:-1]):
            if record["completion_status"] == "complete":
                raise PackagingError(f"retry occurred after a complete attempt: {case_id}")
            failure_code = record["failure_record"]["failure_code"]
            retry_reason = RETRY_REASON_BY_FAILURE_CODE.get(failure_code)
            if retry_reason not in allowed_reasons:
                raise PackagingError(
                    f"retry followed a reason not allowed by the frozen policy: {case_id}"
                )
            if attempts[position + 1][0]["attempt_index"] != record["attempt_index"] + 1:
                raise PackagingError(f"revision retry chain has a gap: {case_id}")
        final_record = attempts[-1][0]
        if final_record["completion_status"] != "complete":
            final_code = final_record["failure_record"]["failure_code"]
            final_reason = RETRY_REASON_BY_FAILURE_CODE.get(final_code)
            if final_record["attempt_index"] < maximum_attempts and final_reason in allowed_reasons:
                raise PackagingError(
                    f"revision retry chain is not terminal under the frozen policy: {case_id}"
                )
        chosen: tuple[dict[str, Any], Path] | None = None
        for record, path in attempts:
            if (
                record["completion_status"] == "complete"
                and record["integrity_validation"]["schema_valid"] is True
                and record["integrity_validation"]["hard_gate_pass"] is True
            ):
                chosen = (record, path)
                break
        case = cases[case_id]
        inventory.append(
            {
                "revision_case_id": case_id,
                "task_id": case["task_id"],
                "repeat_index": case["repeat_index"],
                "feedback_arm": case["feedback_arm"],
                "attempts": [
                    {
                        "attempt_index": record["attempt_index"],
                        "revision_output_id": record["revision_output_id"],
                        "completion_status": record["completion_status"],
                        "hard_gate_pass": record["integrity_validation"]["hard_gate_pass"],
                        "source_file": str(path.relative_to(DIRECTION_ROOT)),
                        "source_file_sha256": sha256_file(path),
                    }
                    for record, path in attempts
                ],
            }
        )
        if chosen is not None:
            selected[case_id] = chosen
        elif case["task_id"] in target_tasks:
            unavailable.append(
                {
                    "revision_case_id": case_id,
                    "task_id": case["task_id"],
                    "repeat_index": case["repeat_index"],
                    "feedback_arm": case["feedback_arm"],
                    "reason": "no_schema_valid_hard_gate_passing_completion_under_frozen_retry_rule",
                }
            )
    return selected, inventory, unavailable


def build_products(
    freeze: dict[str, Any],
    manifest: dict[str, Any],
    public_items: dict[str, dict[str, Any]],
    freeze_path: Path,
    verification_path: Path,
    verification: dict[str, Any],
    briefs_path: Path,
    brief_commitment_path: Path,
    briefs_by_task: dict[str, dict[str, str]],
    allocation_path: Path,
    rows_by_case: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    selected: dict[str, tuple[dict[str, Any], Path]],
    inventory: list[dict[str, Any]],
    unavailable: list[dict[str, Any]],
    target_tasks: set[str],
    construction_excluded_items: list[dict[str, Any]],
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    candidates: list[tuple[str, str, dict[str, Any], dict[str, Any], Path]] = []
    excluded_non_target: list[dict[str, Any]] = []
    panel_blind_ids: set[str] = set()
    for case_id, (record, source_path) in sorted(selected.items()):
        case = cases[case_id]
        if case["task_id"] not in target_tasks:
            excluded_non_target.append(
                {
                    "revision_case_id": case_id,
                    "task_id": case["task_id"],
                    "repeat_index": case["repeat_index"],
                    "feedback_arm": case["feedback_arm"],
                    "reason": "no_independently_verified_target_defect",
                }
            )
            continue
        item = public_items[case["task_id"]]
        brief = briefs_by_task[case["task_id"]]
        source_blind_id = record["blinded_revision_id"]
        if Path(source_blind_id).name != source_blind_id or any(
            separator in source_blind_id for separator in ("/", "\\")
        ):
            raise PackagingError(
                f"source revision blind ID is not filename-safe: {source_blind_id}"
            )
        while True:
            blind_id = "RPI-" + secrets.token_hex(8).upper()
            if blind_id not in panel_blind_ids:
                panel_blind_ids.add(blind_id)
                break
        panel_item = {
            "repair_panel_item_version": "direction-h-repair-panel-item-v1",
            "study_id": manifest["study_id"],
            "task_id": case["task_id"],
            "blinded_revision_id": blind_id,
            "packet_id": case["packet_id"],
            "corpus_id": item["corpus_id"],
            "starting_output_id": case["output_id"],
            "evaluation_role": item["evaluation_role"],
            "data_classification": "synthetic_cc0",
            "evidence_packet": case["model_input"]["evidence_packet"],
            "original_output": case["model_input"]["original_output"],
            "revised_output": record["revised_output"],
            "target_assessment_reference_id": brief["target_assessment_reference_id"],
            "target_assessment_brief": brief["target_assessment_brief"],
        }
        validate(panel_item, PANEL_ITEM_SCHEMA, f"repair-panel item {blind_id}")
        leaked_keys = PUBLIC_FORBIDDEN_KEYS & set(walk_keys(panel_item))
        if leaked_keys:
            raise PackagingError(
                f"private key leaked into panel item {blind_id}: "
                + ", ".join(sorted(leaked_keys))
            )
        order_hash = sha256_bytes(
            f"direction-h-panel-order-v1|{blind_id}".encode()
        )
        candidates.append((order_hash, case_id, panel_item, record, source_path))
    if not candidates:
        raise PackagingError("no eligible completed revision is available for repair-panel review")
    candidates.sort(key=lambda row: row[0])

    item_files: dict[str, bytes] = {}
    manifest_rows: list[dict[str, Any]] = []
    arm_rows: list[dict[str, Any]] = []
    for display_order, (_, case_id, panel_item, record, source_path) in enumerate(
        candidates, start=1
    ):
        filename = f"items/{panel_item['blinded_revision_id']}.json"
        payload = rendered_bytes(panel_item)
        item_files[filename] = payload
        manifest_rows.append(
            {
                "display_order": display_order,
                "blinded_revision_id": panel_item["blinded_revision_id"],
                "task_id": panel_item["task_id"],
                "packet_id": panel_item["packet_id"],
                "corpus_id": panel_item["corpus_id"],
                "starting_output_id": panel_item["starting_output_id"],
                "evaluation_role": panel_item["evaluation_role"],
                "item_file": filename,
                "sha256": sha256_bytes(payload),
            }
        )
        case = cases[case_id]
        arm_rows.append(
            {
                "blinded_revision_id": panel_item["blinded_revision_id"],
                "source_revision_blinded_id": record["blinded_revision_id"],
                "task_id": case["task_id"],
                "revision_case_id": case_id,
                "paired_case_group_id": case["paired_case_group_id"],
                "repeat_index": case["repeat_index"],
                "feedback_arm": case["feedback_arm"],
                "revision_output_id": record["revision_output_id"],
                "selected_attempt_index": record["attempt_index"],
                "revision_output_file": str(source_path.relative_to(DIRECTION_ROOT)),
                "revision_output_file_sha256": sha256_file(source_path),
                "panel_item_file": filename,
                "panel_item_sha256": sha256_bytes(item_files[filename]),
                "target_assessment_reference_id": panel_item[
                    "target_assessment_reference_id"
                ],
            }
        )

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    public_manifest = {
        "manifest_version": "direction-h-repair-panel-manifest-v1",
        "study_id": manifest["study_id"],
        "data_scope": "synthetic_only",
        "contains_real_source_text": False,
        "item_count": len(manifest_rows),
        "items": manifest_rows,
    }
    public_manifest_bytes = rendered_bytes(public_manifest)
    arm_map = {
        "arm_map_version": "direction-h-repair-panel-arm-map-v1",
        "study_id": manifest["study_id"],
        "freeze_id": freeze["freeze_id"],
        "created_at_utc": now,
        "visibility": "coordinator_only_until_assessment_lock",
        "data_scope": "synthetic_only",
        "contains_protected_text": False,
        "pipeline_itt_denominator_rule": (
            "every independently verified target revision case remains in the "
            "pipeline denominator even when no repair-panel item can be emitted"
        ),
        "verified_target_case_count": sum(
            1 for case in cases.values() if case["task_id"] in target_tasks
        ),
        "panel_item_count": len(arm_rows),
        "unavailable_target_case_count": len(unavailable),
        "attempt_selection_rule": (
            "retain every attempt; within each frozen revision case select the first "
            "complete schema-valid hard-gate-passing attempt reached only through allowed "
            "contiguous retries; never select among preregistered repeats"
        ),
        "reviewer_assignment_rule": (
            "freeze a balanced arm-blind blinded_revision_id schedule before review; "
            "pass the assigned ID explicitly to collect_repair_assessment.py; assign "
            "no rater more than one variant of a task"
        ),
        "revision_freeze_file_sha256": sha256_file(freeze_path),
        "revision_allocation_file_sha256": sha256_file(allocation_path),
        "construction_verification_file_sha256": sha256_file(verification_path),
        "target_briefs_file_sha256": sha256_file(briefs_path),
        "target_briefs_commitment_file_sha256": sha256_file(brief_commitment_path),
        "construction_overall_disposition": verification["overall_disposition"],
        "eligible_target_task_ids": sorted(target_tasks),
        "construction_excluded_items": construction_excluded_items,
        "repair_panel_item_schema_sha256": sha256_file(PANEL_ITEM_SCHEMA),
        "revision_output_recorder_script_sha256": sha256_file(
            require_regular_file(
                RECORDER_SCRIPT, DIRECTION_ROOT / "scripts", "revision-output recorder"
            )
        ),
        "repair_panel_packager_script_sha256": sha256_file(
            require_regular_file(
                PACKAGER_SCRIPT, DIRECTION_ROOT / "scripts", "repair-panel packager"
            )
        ),
        "public_manifest_sha256": sha256_bytes(public_manifest_bytes),
        "selected": arm_rows,
        "unavailable_target_cases": unavailable,
        "excluded_non_target_cases": excluded_non_target,
        "attempt_inventory": inventory,
    }
    return item_files, public_manifest, arm_map


def commit_products(
    panel_dir: Path,
    arm_map_path: Path,
    item_files: dict[str, bytes],
    public_manifest: dict[str, Any],
    arm_map: dict[str, Any],
) -> None:
    require_within(panel_dir, PILOT_ROOT, "reviewer panel output")
    require_within(arm_map_path, COORDINATOR_ROOT, "coordinator arm map output")
    if panel_dir.exists():
        raise PackagingError(f"refusing to overwrite reviewer panel directory: {panel_dir}")
    if arm_map_path.exists():
        raise PackagingError(f"refusing to overwrite coordinator arm map: {arm_map_path}")
    panel_dir.parent.mkdir(parents=True, exist_ok=True)
    arm_map_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".repair_panel_staging_", dir=panel_dir.parent))
    os.chmod(staging, 0o700)
    arm_temp: Path | None = None
    arm_fd: int | None = None
    arm_committed = False
    panel_committed = False
    try:
        for relative, payload in item_files.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        (staging / "manifest.json").write_bytes(rendered_bytes(public_manifest))
        arm_fd, arm_temp_name = tempfile.mkstemp(
            prefix=f".{arm_map_path.name}.", suffix=".tmp", dir=arm_map_path.parent
        )
        arm_temp = Path(arm_temp_name)
        os.fchmod(arm_fd, 0o600)
        arm_handle = os.fdopen(arm_fd, "wb")
        arm_fd = None
        with arm_handle as handle:
            handle.write(rendered_bytes(arm_map))
        if panel_dir.exists() or arm_map_path.exists():
            raise PackagingError("output appeared during packaging; refusing to overwrite")
        os.link(arm_temp, arm_map_path)
        os.chmod(arm_map_path, 0o600)
        arm_committed = True
        staging.rename(panel_dir)
        panel_committed = True
    except BaseException:
        if panel_committed and panel_dir.exists():
            shutil.rmtree(panel_dir, ignore_errors=True)
        if arm_committed and arm_map_path.exists():
            try:
                arm_map_path.unlink()
            except OSError:
                pass
        raise
    finally:
        if arm_fd is not None:
            try:
                os.close(arm_fd)
            except OSError:
                pass
        if arm_temp is not None and arm_temp.exists():
            try:
                arm_temp.unlink()
            except OSError:
                pass
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    epilog = """Target-brief input (coordinator-only, exact keys):
{
  "target_briefs_version": "direction-h-target-assessment-briefs-v1",
  "study_id": "direction-h-synthetic-pilot-v1",
  "construction_verification_file_sha256": "<sha256 of exact file>",
  "prepared_by_id": "<non-Charlie pseudonym>",
  "prepared_by_is_charlie": false,
  "prepared_at_utc": "<ISO-8601 with offset>",
  "contains_feedback_arm": false,
  "contains_model_identity": false,
  "items": [{
    "task_id": "<verified target task>",
    "target_assessment_reference_id": "TAR-<16 random uppercase hex characters>",
    "target_assessment_brief": "<minimal frozen repair criterion>"
  }]
}
"""
    parser = argparse.ArgumentParser(
        description=(
            "Build a synthetic-only, arm-blind repair-panel bundle after frozen "
            "revision attempts and independent construction verification."
        ),
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--freeze",
        type=Path,
        default=PILOT_ROOT / "revision_freeze.json",
        help="Completed frozen synthetic revision manifest.",
    )
    parser.add_argument(
        "--revision-output-dir",
        type=Path,
        default=COORDINATOR_ROOT / "revision_outputs",
        help="Coordinator directory containing one revision-output envelope per JSON file.",
    )
    parser.add_argument(
        "--construction-verification",
        type=Path,
        default=COORDINATOR_ROOT / "construction_verification.json",
        help="Completed non-Charlie independent construction verification.",
    )
    parser.add_argument(
        "--target-briefs",
        type=Path,
        default=COORDINATOR_ROOT / "target_assessment_briefs.json",
        help="Coordinator-only arm-blind briefs linked to the exact verification file.",
    )
    parser.add_argument(
        "--target-briefs-commitment",
        type=Path,
        default=COORDINATOR_ROOT / "target_assessment_briefs.commitment.json",
        help="Pre-revision commitment to the exact completed target-brief file.",
    )
    parser.add_argument(
        "--panel-dir",
        type=Path,
        default=PILOT_ROOT / "repair_panel",
        help="New reviewer-safe output directory; existing paths are never overwritten.",
    )
    parser.add_argument(
        "--arm-map",
        type=Path,
        default=COORDINATOR_ROOT / "repair_panel_arm_map.json",
        help="New coordinator-only arm map; existing paths are never overwritten.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        require_within(args.freeze, DIRECTION_ROOT, "revision freeze")
        require_within(args.revision_output_dir, COORDINATOR_ROOT, "revision-output directory")
        require_within(
            args.construction_verification, COORDINATOR_ROOT, "construction verification"
        )
        require_within(args.target_briefs, COORDINATOR_ROOT, "target-assessment briefs")
        require_within(
            args.target_briefs_commitment,
            COORDINATOR_ROOT,
            "target-assessment brief commitment",
        )
        require_within(args.panel_dir, PILOT_ROOT, "reviewer panel output")
        require_within(args.arm_map, COORDINATOR_ROOT, "coordinator arm map output")
        if args.panel_dir.exists() or args.arm_map.exists():
            raise PackagingError("a requested output already exists; refusing to overwrite")

        freeze = verify_freeze(args.freeze)
        manifest, public_items = load_public_pilot()
        if freeze["study_id"] != manifest["study_id"]:
            raise PackagingError("revision freeze and public pilot study_id differ")
        review_lock = verify_review_lock(manifest)
        verification, _, target_tasks, construction_excluded_items = verify_construction(
            args.construction_verification, manifest
        )
        briefs_by_task, briefs = load_target_briefs(
            args.target_briefs,
            args.construction_verification,
            verification,
            manifest["study_id"],
            target_tasks,
            freeze,
        )
        brief_commitment = load_brief_commitment(
            args.target_briefs_commitment,
            args.target_briefs,
            args.construction_verification,
            briefs,
            verification,
            manifest["study_id"],
        )
        allocation_path = COORDINATOR_ROOT / "revision_allocation.json"
        _, _, rows_by_case, cases = load_allocation_and_cases(
            freeze,
            manifest,
            public_items,
            review_lock,
            verification,
            args.construction_verification,
            args.target_briefs,
            brief_commitment,
            args.target_briefs_commitment,
            target_tasks,
            construction_excluded_items,
        )
        selected, inventory, unavailable = load_revision_outputs(
            args.revision_output_dir,
            freeze,
            rows_by_case,
            cases,
            target_tasks,
            brief_commitment,
        )
        item_files, public_manifest, arm_map = build_products(
            freeze,
            manifest,
            public_items,
            args.freeze,
            args.construction_verification,
            verification,
            args.target_briefs,
            args.target_briefs_commitment,
            briefs_by_task,
            allocation_path,
            rows_by_case,
            cases,
            selected,
            inventory,
            unavailable,
            target_tasks,
            construction_excluded_items,
        )
        commit_products(args.panel_dir, args.arm_map, item_files, public_manifest, arm_map)
    except PackagingError as exc:
        raise SystemExit(f"PREPARATION BLOCKED: {exc}. Nothing was written.") from exc
    except OSError as exc:
        raise SystemExit(
            f"PREPARATION BLOCKED by a filesystem error: {exc}. Inspect output paths before retrying; "
            "the script will never overwrite them."
        ) from exc

    print(
        json.dumps(
            {
                "status": "repair_panel_ready",
                "reviewer_item_count": public_manifest["item_count"],
                "unavailable_target_case_count": len(unavailable),
                "contains_real_source_text": False,
                "contains_feedback_arm_in_reviewer_bundle": False,
                "panel_dir": str(args.panel_dir),
                "coordinator_arm_map": str(args.arm_map),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
