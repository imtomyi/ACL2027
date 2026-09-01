#!/usr/bin/env python3
"""Freeze balanced repair-assessor assignments and isolated reviewer bundles.

The coordinator-only builder consumes the private repair-panel arm map, the
hash-locked reviewer-safe panel, and an explicit independent-reviewer roster.
It never creates ratings.  It writes one reviewer-safe subset per assessor and
one private schedule containing the alias/arm/token joins.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import warnings
from collections import Counter, defaultdict
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
            [str(candidate), "-c", "import jsonschema"],
            capture_output=True,
            check=False,
        ).returncode == 0:
            os.execv(str(candidate), [str(candidate), __file__, *sys.argv[1:]])
    raise SystemExit(
        "No local Python runtime with jsonschema is available; no assignments were written."
    )


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
COORDINATOR_ROOT = DIRECTION_ROOT / "coordinator_only"
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"

PANEL_ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_panel_item.schema.json"
PILOT_ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
QUALITATIVE_OUTPUT_SCHEMA = BASELINE_ROOT / "schemas" / "qualitative_output.schema.json"
ROSTER_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_assessor_roster.schema.json"
BUNDLE_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_assessor_bundle.schema.json"
SCHEDULE_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_assignment_schedule.schema.json"
REPAIR_ASSESSMENT_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_assessment.schema.json"
PAPER_METRIC_SCHEMA = BASELINE_ROOT / "schemas" / "paper_metric_rating.schema.json"
POST_RATING_LINK_SCHEMA = DIRECTION_ROOT / "schemas" / "post_revision_rating_link.schema.json"
REPAIR_LOCK_SCHEMA = DIRECTION_ROOT / "schemas" / "repair_assessment_lock.schema.json"
REPAIR_COLLECTOR = DIRECTION_ROOT / "scripts" / "collect_repair_assessment.py"
REPAIR_LOCK_SCRIPT = DIRECTION_ROOT / "scripts" / "lock_repair_assessments.py"
RUNTIME_README = DIRECTION_ROOT / "protocol" / "repair_assessor_runtime_README.md"
BUILDER_SCRIPT = Path(__file__).resolve()

CHARLIE_RATER_ID = "charlie_dev_researcher_01"
PUBLIC_MANIFEST_KEYS = {
    "manifest_version",
    "study_id",
    "data_scope",
    "contains_real_source_text",
    "item_count",
    "items",
}
PUBLIC_ROW_KEYS = {
    "display_order",
    "blinded_revision_id",
    "task_id",
    "packet_id",
    "corpus_id",
    "starting_output_id",
    "evaluation_role",
    "item_file",
    "sha256",
}
PRIVATE_BUNDLE_KEYS = {
    "allocation",
    "assignment_seed_hex",
    "assignment_token",
    "charlie_rating",
    "condition",
    "condition_label",
    "feedback_arm",
    "feedback_author",
    "feedback_content",
    "feedback_record_id",
    "model_id",
    "model_identity",
    "paired_case_group_id",
    "rater_id",
    "repeat_index",
    "revision_case_id",
    "revision_diagnosis",
    "source_blinded_revision_id",
    "source_task_id",
    "truth",
    "truth_map",
}
INSTRUMENT_PATHS = {
    "repair_assessment_collector_script_sha256": REPAIR_COLLECTOR,
    "repair_panel_item_schema_sha256": PANEL_ITEM_SCHEMA,
    "repair_assessor_bundle_schema_sha256": BUNDLE_SCHEMA,
    "pilot_item_schema_sha256": PILOT_ITEM_SCHEMA,
    "qualitative_output_schema_sha256": QUALITATIVE_OUTPUT_SCHEMA,
    "repair_assessment_schema_sha256": REPAIR_ASSESSMENT_SCHEMA,
    "paper_metric_rating_schema_sha256": PAPER_METRIC_SCHEMA,
    "post_revision_rating_link_schema_sha256": POST_RATING_LINK_SCHEMA,
    "repair_assessor_runtime_readme_sha256": RUNTIME_README,
}
RUNTIME_PACKAGE_PATHS = {
    "repair_assessment_collector_script_sha256": "runtime/collect_repair_assessment.py",
    "repair_panel_item_schema_sha256": "runtime/schemas/repair_panel_item.schema.json",
    "repair_assessor_bundle_schema_sha256": "runtime/schemas/repair_assessor_bundle.schema.json",
    "pilot_item_schema_sha256": "runtime/schemas/pilot_item.schema.json",
    "qualitative_output_schema_sha256": "runtime/schemas/qualitative_output.schema.json",
    "repair_assessment_schema_sha256": "runtime/schemas/repair_assessment.schema.json",
    "paper_metric_rating_schema_sha256": "runtime/schemas/paper_metric_rating.schema.json",
    "post_revision_rating_link_schema_sha256": "runtime/schemas/post_revision_rating_link.schema.json",
    "repair_assessor_runtime_readme_sha256": "runtime/README.md",
}
COLLECTOR_CONTRACT_DECLARATION = (
    'ASSIGNMENT_BUNDLE_CONTRACT_VERSION = "direction-h-repair-assessor-bundle-v1"'
)


class AssignmentError(Exception):
    """A fail-closed assignment precondition or construction error."""


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise AssignmentError(f"{label} is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve file context
        raise AssignmentError(f"cannot read {label} as JSON ({path}): {exc}") from exc


def rendered_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def nul_hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def derived_hex(seed: bytes, label: str, length: int = 20) -> str:
    return hmac.new(seed, label.encode("utf-8"), hashlib.sha256).hexdigest()[:length].upper()


def keyed_order(seed: bytes, label: str) -> str:
    return hmac.new(seed, label.encode("utf-8"), hashlib.sha256).hexdigest()


def has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return "__required" in lowered or value.startswith("FILL_") or value == "TBD"
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


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not is_within(resolved, root.resolve()):
        raise AssignmentError(f"{label} must stay under {root}: {path}")
    return resolved


def require_file(path: Path, root: Path, label: str) -> Path:
    if path.is_symlink():
        raise AssignmentError(f"{label} may not be a symlink: {path}")
    resolved = require_within(path, root, label)
    if not resolved.is_file():
        raise AssignmentError(f"{label} is missing or not a regular file: {path}")
    return resolved


def schema_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in (
        PANEL_ITEM_SCHEMA,
        PILOT_ITEM_SCHEMA,
        QUALITATIVE_OUTPUT_SCHEMA,
        ROSTER_SCHEMA,
        BUNDLE_SCHEMA,
        SCHEDULE_SCHEMA,
        REPAIR_ASSESSMENT_SCHEMA,
        PAPER_METRIC_SCHEMA,
        POST_RATING_LINK_SCHEMA,
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
        raise AssignmentError(f"{label} fails {schema_path.name}: {rendered}")


def parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise AssignmentError(f"{label} is not an ISO-8601 date-time") from exc
    if parsed.tzinfo is None:
        raise AssignmentError(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def load_panel(manifest_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = require_file(manifest_path, PILOT_ROOT, "public repair-panel manifest")
    manifest = load_json(manifest_path, "public repair-panel manifest")
    if not isinstance(manifest, dict) or set(manifest) != PUBLIC_MANIFEST_KEYS:
        raise AssignmentError("public repair-panel manifest has an unexpected top-level shape")
    if manifest.get("manifest_version") != "direction-h-repair-panel-manifest-v1":
        raise AssignmentError("unsupported public repair-panel manifest version")
    if manifest.get("data_scope") != "synthetic_only" or manifest.get(
        "contains_real_source_text"
    ) is not False:
        raise AssignmentError("assignment builder version 1 accepts synthetic-only panels")
    rows = manifest.get("items")
    if not isinstance(rows, list) or not rows:
        raise AssignmentError("public repair-panel manifest has no items")
    if manifest.get("item_count") != len(rows):
        raise AssignmentError("public repair-panel manifest item_count mismatch")

    loaded: dict[str, dict[str, Any]] = {}
    orders: set[int] = set()
    panel_dir = manifest_path.parent.resolve()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != PUBLIC_ROW_KEYS:
            raise AssignmentError(f"public repair-panel row {index} has an unexpected shape")
        order = row["display_order"]
        if not isinstance(order, int) or isinstance(order, bool) or order < 1 or order in orders:
            raise AssignmentError(f"public repair-panel row {index} has invalid display_order")
        orders.add(order)
        blind_id = row["blinded_revision_id"]
        if not isinstance(blind_id, str) or not blind_id or blind_id in loaded:
            raise AssignmentError(f"public repair-panel row {index} has duplicate/invalid blind ID")
        relative = Path(row["item_file"])
        if relative.is_absolute() or relative.name != f"{blind_id}.json":
            raise AssignmentError(f"public repair-panel row {index} has an unsafe item_file")
        item_path = require_file(panel_dir / relative, panel_dir, f"panel item {blind_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row["sha256"])):
            raise AssignmentError(f"public repair-panel row {index} has invalid sha256")
        if sha256_file(item_path) != row["sha256"]:
            raise AssignmentError(f"public repair-panel item hash mismatch: {blind_id}")
        item = load_json(item_path, f"panel item {blind_id}")
        validate(item, PANEL_ITEM_SCHEMA, f"panel item {blind_id}")
        if item.get("data_classification") != "synthetic_cc0":
            raise AssignmentError(f"panel item {blind_id} is not synthetic_cc0")
        for key in (
            "blinded_revision_id",
            "task_id",
            "packet_id",
            "corpus_id",
            "starting_output_id",
            "evaluation_role",
        ):
            if row[key] != item[key]:
                raise AssignmentError(f"panel row/item mismatch for {blind_id}: {key}")
        if item["study_id"] != manifest["study_id"]:
            raise AssignmentError(f"panel item {blind_id} has the wrong study_id")
        loaded[blind_id] = {"row": row, "item": item, "path": item_path}
    if orders != set(range(1, len(rows) + 1)):
        raise AssignmentError("public repair-panel display_order must be contiguous from 1")
    return manifest, loaded


def join_private_arms(
    arm_map_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    panel: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    arm_map_path = require_file(arm_map_path, COORDINATOR_ROOT, "private repair-panel arm map")
    arm_map = load_json(arm_map_path, "private repair-panel arm map")
    if not isinstance(arm_map, dict):
        raise AssignmentError("private repair-panel arm map must be an object")
    if arm_map.get("arm_map_version") != "direction-h-repair-panel-arm-map-v1":
        raise AssignmentError("unsupported private repair-panel arm-map version")
    if arm_map.get("study_id") != manifest["study_id"]:
        raise AssignmentError("private arm map and public panel study_id differ")
    if arm_map.get("data_scope") != "synthetic_only" or arm_map.get(
        "contains_protected_text"
    ) is not False:
        raise AssignmentError("private arm map is not asserted synthetic-only")
    if arm_map.get("public_manifest_sha256") != sha256_file(manifest_path):
        raise AssignmentError("private arm map does not pin the exact public manifest")
    selected = arm_map.get("selected")
    if not isinstance(selected, list) or not selected:
        raise AssignmentError("private arm map has no selected panel items")

    joined: list[dict[str, Any]] = []
    seen: set[str] = set()
    required = {
        "blinded_revision_id",
        "task_id",
        "revision_case_id",
        "repeat_index",
        "feedback_arm",
        "panel_item_file",
        "panel_item_sha256",
        "target_assessment_reference_id",
    }
    for index, private in enumerate(selected, start=1):
        if not isinstance(private, dict) or not required <= set(private):
            raise AssignmentError(f"private arm-map selected row {index} is incomplete")
        blind_id = private["blinded_revision_id"]
        if blind_id in seen or blind_id not in panel:
            raise AssignmentError(f"private arm-map selected row {index} has unknown/duplicate ID")
        seen.add(blind_id)
        source = panel[blind_id]
        row = source["row"]
        item = source["item"]
        if private["task_id"] != row["task_id"]:
            raise AssignmentError(f"private/public task mismatch for {blind_id}")
        if private["panel_item_file"] != row["item_file"]:
            raise AssignmentError(f"private/public item-file mismatch for {blind_id}")
        if private["panel_item_sha256"] != row["sha256"]:
            raise AssignmentError(f"private/public item hash mismatch for {blind_id}")
        if private["target_assessment_reference_id"] != item[
            "target_assessment_reference_id"
        ]:
            raise AssignmentError(f"private/public target-reference mismatch for {blind_id}")
        if not isinstance(private["feedback_arm"], str) or not private["feedback_arm"]:
            raise AssignmentError(f"private arm label is invalid for {blind_id}")
        if not isinstance(private["repeat_index"], int) or isinstance(
            private["repeat_index"], bool
        ) or private["repeat_index"] < 0:
            raise AssignmentError(f"private repeat_index is invalid for {blind_id}")
        joined.append({**source, "private": private, "arm": private["feedback_arm"]})
    if seen != set(panel):
        raise AssignmentError("private selected arm rows do not exactly cover the public panel")
    observed_arms = sorted({entry["arm"] for entry in joined})
    unavailable = arm_map.get("unavailable_target_cases")
    inventory = arm_map.get("attempt_inventory")
    if not isinstance(unavailable, list) or not isinstance(inventory, list):
        raise AssignmentError(
            "private arm map lacks unavailable-case or attempt-inventory accounting"
        )
    if arm_map.get("panel_item_count") != len(joined):
        raise AssignmentError("private arm-map panel_item_count mismatch")
    if arm_map.get("unavailable_target_case_count") != len(unavailable):
        raise AssignmentError("private arm-map unavailable_target_case_count mismatch")

    inventory_by_case: dict[str, dict[str, Any]] = {}
    for row in inventory:
        if not isinstance(row, dict) or not {
            "revision_case_id",
            "task_id",
            "repeat_index",
            "feedback_arm",
            "attempts",
        } <= set(row):
            raise AssignmentError("private arm-map attempt inventory has an incomplete row")
        case_id = row["revision_case_id"]
        if case_id in inventory_by_case:
            raise AssignmentError(f"duplicate attempt inventory case: {case_id}")
        inventory_by_case[case_id] = row

    allocated_rows: list[dict[str, Any]] = [entry["private"] for entry in joined]
    selected_case_ids = {row["revision_case_id"] for row in allocated_rows}
    unavailable_case_ids: set[str] = set()
    exact_unavailable_reason = (
        "no_schema_valid_hard_gate_passing_completion_under_frozen_retry_rule"
    )
    for row in unavailable:
        if not isinstance(row, dict) or set(row) != {
            "revision_case_id",
            "task_id",
            "repeat_index",
            "feedback_arm",
            "reason",
        }:
            raise AssignmentError("private arm-map unavailable target row has an unsafe shape")
        case_id = row["revision_case_id"]
        if case_id in unavailable_case_ids or case_id in selected_case_ids:
            raise AssignmentError(f"duplicate selected/unavailable target case: {case_id}")
        unavailable_case_ids.add(case_id)
        if row["reason"] != exact_unavailable_reason:
            raise AssignmentError(f"unrecognized unavailable target-case reason: {case_id}")
        inventory_row = inventory_by_case.get(case_id)
        if inventory_row is None:
            raise AssignmentError(f"unavailable target case lacks attempt inventory: {case_id}")
        for key in ("task_id", "repeat_index", "feedback_arm"):
            if inventory_row[key] != row[key]:
                raise AssignmentError(
                    f"unavailable target case and attempt inventory differ on {key}: {case_id}"
                )
        attempts = inventory_row["attempts"]
        if not isinstance(attempts, list) or not attempts:
            raise AssignmentError(f"unavailable target case has no retained attempts: {case_id}")
        if any(
            not isinstance(attempt, dict)
            or not {"attempt_index", "completion_status", "hard_gate_pass"} <= set(attempt)
            for attempt in attempts
        ):
            raise AssignmentError(
                f"unavailable target case has an incomplete retained attempt: {case_id}"
            )
        if any(
            attempt.get("completion_status") == "complete"
            and attempt.get("hard_gate_pass") is True
            for attempt in attempts
        ):
            raise AssignmentError(
                f"unavailable target case contains an eligible completed attempt: {case_id}"
            )
        allocated_rows.append(row)

    if arm_map.get("verified_target_case_count") != len(allocated_rows):
        raise AssignmentError("private arm-map verified target ITT denominator mismatch")
    allocated_arms = sorted({row["feedback_arm"] for row in allocated_rows})
    if len(allocated_arms) < 2 or "no_feedback" not in allocated_arms:
        raise AssignmentError(
            "private arm map does not prove the allocated no-feedback comparison"
        )
    arms_by_pair: dict[tuple[str, int], set[str]] = defaultdict(set)
    case_identity: set[tuple[str, int, str]] = set()
    for row in allocated_rows:
        identity = (row["task_id"], row["repeat_index"], row["feedback_arm"])
        if identity in case_identity:
            raise AssignmentError(f"duplicate allocated target identity: {identity}")
        case_identity.add(identity)
        arms_by_pair[(row["task_id"], row["repeat_index"])].add(row["feedback_arm"])
    for pair, pair_arms in arms_by_pair.items():
        if pair_arms != set(allocated_arms):
            raise AssignmentError(
                f"private arm map does not prove a complete allocated arm block for {pair}"
            )
    if not set(observed_arms) <= set(allocated_arms):
        raise AssignmentError("observed repair-panel arm is absent from allocated arms")
    missing_arms = sorted(set(allocated_arms) - set(observed_arms))
    if missing_arms and not unavailable:
        raise AssignmentError("an allocated arm is unobserved without terminal-unavailable cases")
    availability = {
        "allocated_feedback_arms": allocated_arms,
        "observed_feedback_arms": observed_arms,
        "unavailable_target_case_count": len(unavailable),
        "unavailable_target_cases_sha256": sha256_bytes(canonical_bytes(unavailable)),
        "single_observed_arm_qualification": (
            "allowed_only_because_missing_paired_cases_terminal_unavailable"
            if len(observed_arms) == 1
            else "not_needed_multiple_allocated_arms_observed"
        ),
    }
    return arm_map, joined, availability


def load_roster(
    roster_path: Path, study_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    roster_path = require_file(roster_path, COORDINATOR_ROOT, "repair-assessor roster")
    roster = load_json(roster_path, "repair-assessor roster")
    if has_placeholder(roster):
        raise AssignmentError("repair-assessor roster still contains template placeholders")
    validate(roster, ROSTER_SCHEMA, "repair-assessor roster")
    if roster["study_id"] != study_id:
        raise AssignmentError("repair-assessor roster and panel study_id differ")
    if parse_utc(roster["prepared_at_utc"], "roster prepared_at_utc") > datetime.now(
        timezone.utc
    ):
        raise AssignmentError("repair-assessor roster prepared_at_utc is in the future")

    targets: dict[str, int] = {}
    for target in roster["assignment_targets"]:
        group = target["evaluator_group"]
        if group in targets:
            raise AssignmentError(f"duplicate assignment target for evaluator group {group}")
        targets[group] = target["assessments_per_panel_item"]

    reviewers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for reviewer in roster["reviewers"]:
        rater_id = reviewer["rater_id"]
        if rater_id.casefold() != rater_id or rater_id.casefold() in seen_ids:
            raise AssignmentError(f"duplicate or noncanonical reviewer pseudonym: {rater_id}")
        if rater_id == CHARLIE_RATER_ID:
            raise AssignmentError("Charlie cannot enter the independent repair-assessor roster")
        if reviewer["evaluator_group"] not in targets:
            raise AssignmentError(
                f"reviewer {rater_id} belongs to a group without an assignment target"
            )
        seen_ids.add(rater_id)
        reviewers.append(reviewer)
    present_groups = {reviewer["evaluator_group"] for reviewer in reviewers}
    if present_groups != set(targets):
        raise AssignmentError("every assignment-target group must have rostered reviewers")
    if roster["prepared_by_id"].casefold() in seen_ids:
        raise AssignmentError(
            "the roster/schedule coordinator may not also be a blinded repair assessor"
        )
    return roster, reviewers, targets


def instrument_hashes() -> dict[str, str]:
    collector_source = require_file(
        REPAIR_COLLECTOR, DIRECTION_ROOT / "scripts", "repair-assessment collector"
    ).read_text(encoding="utf-8")
    required_contract_signals = {
        COLLECTOR_CONTRACT_DECLARATION,
        '"--bundle-root"',
        '"--assignment-token"',
        '"assignment_payload_sha256"',
        '"assignment_token_sha256"',
        '"rater_binding_sha256"',
    }
    missing_signals = sorted(
        signal for signal in required_contract_signals if signal not in collector_source
    )
    if missing_signals:
        raise AssignmentError(
            "repair-assessment collector has not implemented the frozen isolated-bundle "
            "authorization contract; missing: " + ", ".join(missing_signals)
        )
    hashes: dict[str, str] = {}
    for label, path in INSTRUMENT_PATHS.items():
        require_file(path, DIRECTION_ROOT if path.is_relative_to(DIRECTION_ROOT) else PROJECT_ROOT, label)
        hashes[label] = sha256_file(path)
    return hashes


def feasible_or_raise(
    entries: list[dict[str, Any]], reviewers: list[dict[str, Any]], targets: dict[str, int]
) -> None:
    variants_by_task = Counter(entry["row"]["task_id"] for entry in entries)
    for group, replication in targets.items():
        group_size = sum(1 for reviewer in reviewers if reviewer["evaluator_group"] == group)
        required_for_largest_task = max(variants_by_task.values()) * replication
        total_assignments = len(entries) * replication
        if group_size < required_for_largest_task:
            raise AssignmentError(
                f"evaluator group {group} needs at least {required_for_largest_task} reviewers "
                "to give every item its target coverage without exposing any reviewer to two "
                "variants of one task"
            )
        if group_size > total_assignments:
            raise AssignmentError(
                f"evaluator group {group} has {group_size} reviewers but only "
                f"{total_assignments} assignments; reduce the roster or raise replication so "
                "every rostered reviewer receives at least one item"
            )


def one_balance_trial(
    entries: list[dict[str, Any]],
    reviewers: list[dict[str, Any]],
    targets: dict[str, int],
    arms: list[str],
    seed: bytes,
    trial: int,
) -> dict[str, list[dict[str, Any]]] | None:
    result: dict[str, list[dict[str, Any]]] = {reviewer["rater_id"]: [] for reviewer in reviewers}
    task_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        task_entries[entry["row"]["task_id"]].append(entry)

    for group, replication in sorted(targets.items()):
        rater_ids = sorted(
            reviewer["rater_id"]
            for reviewer in reviewers
            if reviewer["evaluator_group"] == group
        )
        load = Counter({rater_id: 0 for rater_id in rater_ids})
        arm_counts = {
            rater_id: Counter({arm: 0 for arm in arms}) for rater_id in rater_ids
        }
        task_order = sorted(
            task_entries,
            key=lambda task: keyed_order(seed, f"trial|{trial}|{group}|task|{task}"),
        )
        for task_id in task_order:
            slots = [
                (entry, replicate)
                for entry in task_entries[task_id]
                for replicate in range(replication)
            ]
            slots.sort(
                key=lambda pair: keyed_order(
                    seed,
                    f"trial|{trial}|{group}|task|{task_id}|item|"
                    f"{pair[0]['row']['blinded_revision_id']}|rep|{pair[1]}",
                )
            )
            used_for_task: set[str] = set()
            for entry, replicate in slots:
                arm = entry["arm"]
                candidates = [rater_id for rater_id in rater_ids if rater_id not in used_for_task]
                if not candidates:
                    return None

                def score(rater_id: str) -> tuple[int, int, int, str]:
                    projected = dict(arm_counts[rater_id])
                    projected[arm] += 1
                    imbalance = max(projected.values()) - min(projected.values())
                    tie = keyed_order(
                        seed,
                        f"trial|{trial}|{group}|task|{task_id}|item|"
                        f"{entry['row']['blinded_revision_id']}|rep|{replicate}|rater|{rater_id}",
                    )
                    return load[rater_id], arm_counts[rater_id][arm], imbalance, tie

                chosen = min(candidates, key=score)
                result[chosen].append(entry)
                used_for_task.add(chosen)
                load[chosen] += 1
                arm_counts[chosen][arm] += 1

        workloads = [load[rater_id] for rater_id in rater_ids]
        if max(workloads) - min(workloads) > 1 or min(workloads) < 1:
            return None
        for rater_id in rater_ids:
            counts = [arm_counts[rater_id][arm] for arm in arms]
            if max(counts) - min(counts) > 1:
                return None
    return result


def freeze_balanced_assignments(
    entries: list[dict[str, Any]],
    reviewers: list[dict[str, Any]],
    targets: dict[str, int],
    arms: list[str],
    seed: bytes,
    max_trials: int,
) -> tuple[int, dict[str, list[dict[str, Any]]]]:
    feasible_or_raise(entries, reviewers, targets)
    for trial in range(max_trials):
        assignment = one_balance_trial(entries, reviewers, targets, arms, seed, trial)
        if assignment is not None:
            return trial, assignment
    raise AssignmentError(
        f"no schedule satisfied the frozen exact-coverage, one-variant-per-task, workload, "
        f"and within-rater arm-balance rules in {max_trials} deterministic trials; change the "
        "roster/replication target or deliberately revise the design before collection"
    )


def validate_assignment(
    assignment: dict[str, list[dict[str, Any]]],
    reviewers: list[dict[str, Any]],
    targets: dict[str, int],
    entries: list[dict[str, Any]],
    arms: list[str],
) -> None:
    by_rater = {reviewer["rater_id"]: reviewer for reviewer in reviewers}
    coverage: Counter[tuple[str, str]] = Counter()
    group_loads: dict[str, list[int]] = defaultdict(list)
    for rater_id, assigned in assignment.items():
        reviewer = by_rater[rater_id]
        group = reviewer["evaluator_group"]
        tasks = [entry["row"]["task_id"] for entry in assigned]
        if len(tasks) != len(set(tasks)):
            raise AssignmentError(f"internal error: {rater_id} received two variants of one task")
        arm_counts = Counter(entry["arm"] for entry in assigned)
        if max(arm_counts[arm] for arm in arms) - min(arm_counts[arm] for arm in arms) > 1:
            raise AssignmentError(f"internal error: arm counts are not balanced for {rater_id}")
        group_loads[group].append(len(assigned))
        for entry in assigned:
            coverage[(group, entry["row"]["blinded_revision_id"])] += 1
    for group, loads in group_loads.items():
        if max(loads) - min(loads) > 1:
            raise AssignmentError(f"internal error: workload is not balanced in {group}")
    for group, replication in targets.items():
        for entry in entries:
            key = (group, entry["row"]["blinded_revision_id"])
            if coverage[key] != replication:
                raise AssignmentError(f"internal error: exact item coverage failed for {key}")


def make_aliases(seed: bytes, entry: dict[str, Any]) -> tuple[str, str, str]:
    """Return stable aliases keyed only by the underlying panel identities.

    Reusing the same alias across isolated bundles is required for item-level
    comparisons of exact qc-paper-metrics-v1 rows.  Bundle membership remains
    private; aliases do not encode an arm, rater, model, repeat, or condition.
    """
    blind_id = entry["row"]["blinded_revision_id"]
    task_id = entry["row"]["task_id"]
    reference_id = entry["item"]["target_assessment_reference_id"]
    item_alias = "RAI-" + derived_hex(seed, f"item|{blind_id}")
    task_alias = "RAT-" + derived_hex(seed, f"task|{task_id}")
    reference_alias = "RAREF-" + derived_hex(seed, f"target-reference|{reference_id}")
    return item_alias, task_alias, reference_alias


def build_bundle_products(
    study_id: str,
    schedule_id: str,
    created_at: str,
    public_manifest_sha256: str,
    instruments: dict[str, str],
    reviewers: list[dict[str, Any]],
    assignment: dict[str, list[dict[str, Any]]],
    arms: list[str],
    seed: bytes,
) -> tuple[dict[str, dict[str, bytes]], list[dict[str, Any]]]:
    bundle_products: dict[str, dict[str, bytes]] = {}
    private_rows: list[dict[str, Any]] = []
    used_bundle_ids: set[str] = set()
    used_assessor_aliases: set[str] = set()
    item_alias_sources: dict[str, str] = {}
    task_alias_sources: dict[str, str] = {}
    reference_alias_sources: dict[str, str] = {}

    for reviewer in sorted(reviewers, key=lambda row: row["rater_id"]):
        rater_id = reviewer["rater_id"]
        evaluator_group = reviewer["evaluator_group"]
        bundle_id = "RAB-" + derived_hex(seed, f"bundle|{rater_id}")
        assessor_alias = "RAA-" + derived_hex(seed, f"assessor|{rater_id}")
        token = hmac.new(seed, f"token|{rater_id}".encode("utf-8"), hashlib.sha256).hexdigest()
        if bundle_id in used_bundle_ids or assessor_alias in used_assessor_aliases:
            raise AssignmentError("derived bundle or assessor alias collision")
        used_bundle_ids.add(bundle_id)
        used_assessor_aliases.add(assessor_alias)

        assigned = sorted(
            assignment[rater_id],
            key=lambda entry: keyed_order(
                seed,
                f"display|{rater_id}|{entry['row']['blinded_revision_id']}",
            ),
        )
        file_payloads: dict[str, bytes] = {
            RUNTIME_PACKAGE_PATHS[label]: require_file(
                source,
                DIRECTION_ROOT if source.is_relative_to(DIRECTION_ROOT) else PROJECT_ROOT,
                f"runtime instrument {label}",
            ).read_bytes()
            for label, source in INSTRUMENT_PATHS.items()
        }
        for label, relative in RUNTIME_PACKAGE_PATHS.items():
            if sha256_bytes(file_payloads[relative]) != instruments[label]:
                raise AssignmentError(
                    f"runtime instrument changed during bundle construction: {label}"
                )
        manifest_rows: list[dict[str, Any]] = []
        private_assignments: list[dict[str, Any]] = []
        for display_order, entry in enumerate(assigned, start=1):
            item_alias, task_alias, reference_alias = make_aliases(seed, entry)
            for alias, source, registry, label in (
                (
                    item_alias,
                    entry["row"]["blinded_revision_id"],
                    item_alias_sources,
                    "item",
                ),
                (task_alias, entry["row"]["task_id"], task_alias_sources, "task"),
                (
                    reference_alias,
                    entry["item"]["target_assessment_reference_id"],
                    reference_alias_sources,
                    "target-reference",
                ),
            ):
                prior = registry.setdefault(alias, source)
                if prior != source:
                    raise AssignmentError(f"derived {label} alias collision")

            assigned_item = copy.deepcopy(entry["item"])
            assigned_item["blinded_revision_id"] = item_alias
            assigned_item["task_id"] = task_alias
            assigned_item["target_assessment_reference_id"] = reference_alias
            validate(assigned_item, PANEL_ITEM_SCHEMA, f"assigned panel item {item_alias}")
            leaked = PRIVATE_BUNDLE_KEYS & set(walk_keys(assigned_item))
            if leaked:
                raise AssignmentError(
                    f"private field leaked into assigned panel item {item_alias}: "
                    + ", ".join(sorted(leaked))
                )
            item_file = f"items/{item_alias}.json"
            payload = rendered_bytes(assigned_item)
            file_payloads[item_file] = payload
            row = {
                "display_order": display_order,
                "blinded_revision_id": item_alias,
                "task_id": task_alias,
                "corpus_id": assigned_item["corpus_id"],
                "packet_id": assigned_item["packet_id"],
                "starting_output_id": assigned_item["starting_output_id"],
                "evaluation_role": assigned_item["evaluation_role"],
                "target_assessment_reference_id": reference_alias,
                "data_classification": assigned_item["data_classification"],
                "repair_panel_item_version": assigned_item["repair_panel_item_version"],
                "item_file": item_file,
                "sha256": sha256_bytes(payload),
            }
            manifest_rows.append(row)
            private = entry["private"]
            private_assignments.append(
                {
                    "display_order": display_order,
                    "feedback_arm": entry["arm"],
                    "source_blinded_revision_id": entry["row"]["blinded_revision_id"],
                    "source_task_id": entry["row"]["task_id"],
                    "source_revision_case_id": private["revision_case_id"],
                    "source_repeat_index": private["repeat_index"],
                    "source_target_assessment_reference_id": entry["item"][
                        "target_assessment_reference_id"
                    ],
                    "source_panel_item_sha256": entry["row"]["sha256"],
                    "assigned_blinded_revision_id": item_alias,
                    "assigned_task_id": task_alias,
                    "assigned_target_assessment_reference_id": reference_alias,
                    "corpus_id": assigned_item["corpus_id"],
                    "assigned_item_file": item_file,
                    "assigned_item_sha256": sha256_bytes(payload),
                }
            )

        assignment_payload = {
            "assignment_payload_version": "direction-h-repair-assignment-payload-v1",
            "study_id": study_id,
            "schedule_id": schedule_id,
            "bundle_id": bundle_id,
            "assessor_alias": assessor_alias,
            "evaluator_group": evaluator_group,
            "parent_panel_manifest_sha256": public_manifest_sha256,
            "frozen_instrument_hashes": instruments,
            "items": manifest_rows,
        }
        assignment_payload_sha256 = sha256_bytes(canonical_bytes(assignment_payload))
        token_sha256 = nul_hash(
            "direction-h-assignment-token-v1",
            study_id,
            schedule_id,
            bundle_id,
            token,
        )
        rater_binding_sha256 = nul_hash(
            "direction-h-rater-binding-v1",
            study_id,
            schedule_id,
            bundle_id,
            rater_id,
            evaluator_group,
            assignment_payload_sha256,
            token,
        )
        bundle_manifest = {
            "bundle_manifest_version": "direction-h-repair-assessor-bundle-v1",
            "study_id": study_id,
            "schedule_id": schedule_id,
            "bundle_id": bundle_id,
            "assessor_alias": assessor_alias,
            "evaluator_group": evaluator_group,
            "data_scope": "synthetic_only",
            "contains_real_source_text": False,
            "created_at_utc": created_at,
            "parent_panel_manifest_sha256": public_manifest_sha256,
            "frozen_instrument_hashes": instruments,
            "assignment_payload_sha256": assignment_payload_sha256,
            "assignment_token_hash_method": (
                "sha256_utf8_nul_direction_h_assignment_token_v1"
            ),
            "assignment_token_sha256": token_sha256,
            "rater_binding_hash_method": "sha256_utf8_nul_direction_h_rater_binding_v1",
            "rater_binding_sha256": rater_binding_sha256,
            "item_count": len(manifest_rows),
            "items": manifest_rows,
        }
        validate(bundle_manifest, BUNDLE_SCHEMA, f"assessor bundle {bundle_id}")
        leaked = PRIVATE_BUNDLE_KEYS & set(walk_keys(bundle_manifest))
        if leaked:
            raise AssignmentError(
                f"private field leaked into assessor bundle {bundle_id}: "
                + ", ".join(sorted(leaked))
            )
        file_payloads["manifest.json"] = rendered_bytes(bundle_manifest)
        tree_map = {
            relative: sha256_bytes(payload)
            for relative, payload in sorted(file_payloads.items())
        }
        bundle_tree_sha256 = sha256_bytes(canonical_bytes(tree_map))
        bundle_products[bundle_id] = file_payloads
        private_rows.append(
            {
                "rater_id": rater_id,
                "evaluator_group": evaluator_group,
                "assessor_alias": assessor_alias,
                "bundle_id": bundle_id,
                "assignment_token": token,
                "assignment_token_sha256": token_sha256,
                "rater_binding_sha256": rater_binding_sha256,
                "bundle_directory": f"pilot/repair_assessor_bundles/{bundle_id}",
                "bundle_manifest_sha256": sha256_bytes(file_payloads["manifest.json"]),
                "bundle_tree_sha256": bundle_tree_sha256,
                "workload_count": len(private_assignments),
                "arm_counts": {
                    arm: sum(1 for row in private_assignments if row["feedback_arm"] == arm)
                    for arm in arms
                },
                "assignments": private_assignments,
            }
        )
    return bundle_products, private_rows


def build_schedule(
    study_id: str,
    schedule_id: str,
    created_at: str,
    seed: bytes,
    manifest_path: Path,
    arm_map_path: Path,
    roster_path: Path,
    roster: dict[str, Any],
    instruments: dict[str, str],
    availability: dict[str, Any],
    entries: list[dict[str, Any]],
    trial: int,
    private_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    schedule = {
        "assignment_schedule_version": "direction-h-repair-assignment-schedule-v1",
        "study_id": study_id,
        "schedule_id": schedule_id,
        "status": "frozen",
        "visibility": "coordinator_only_until_all_repair_assessments_lock",
        "data_scope": "synthetic_only",
        "contains_protected_text": False,
        "created_at_utc": created_at,
        "assignment_seed_hex": seed.hex(),
        "input_hashes": {
            "public_panel_manifest_sha256": sha256_file(manifest_path),
            "private_arm_map_sha256": sha256_file(arm_map_path),
            "reviewer_roster_sha256": sha256_file(roster_path),
            "reviewer_roster_schema_sha256": sha256_file(ROSTER_SCHEMA),
            "assessor_bundle_schema_sha256": sha256_file(BUNDLE_SCHEMA),
            "repair_panel_item_schema_sha256": sha256_file(PANEL_ITEM_SCHEMA),
            "assignment_builder_script_sha256": sha256_file(BUILDER_SCRIPT),
            "repair_assessment_lock_script_sha256": sha256_file(REPAIR_LOCK_SCRIPT),
            "repair_assessment_lock_schema_sha256": sha256_file(REPAIR_LOCK_SCHEMA),
            **instruments,
        },
        "design": {
            "assignment_targets": roster["assignment_targets"],
            **availability,
            "panel_item_count": len(entries),
            "total_assignment_count": sum(row["workload_count"] for row in private_rows),
            "selected_balance_trial": trial,
            "every_item_exact_target_coverage_verified": True,
            "no_more_than_one_variant_per_task_per_rater_verified": True,
            "within_stratum_workload_difference_at_most_one_verified": True,
            "within_rater_arm_count_difference_at_most_one_verified": True,
            "fresh_aliases_verified": True,
            "isolated_bundle_subset_verified": True,
        },
        "reviewers": private_rows,
    }
    validate(schedule, SCHEDULE_SCHEMA, "private repair-assessor assignment schedule")
    return schedule


def commit_products(
    output_root: Path,
    schedule_path: Path,
    bundle_products: dict[str, dict[str, bytes]],
    schedule: dict[str, Any],
) -> None:
    output_root = require_within(output_root, PILOT_ROOT, "assessor-bundle output root")
    schedule_path = require_within(schedule_path, COORDINATOR_ROOT, "private schedule output")
    if output_root.exists() or schedule_path.exists():
        raise AssignmentError("an assignment output already exists; refusing to overwrite")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=".repair_assessor_bundles_", dir=output_root.parent)
    )
    schedule_temp: Path | None = None
    output_committed = False
    schedule_committed = False
    try:
        os.chmod(staging, 0o700)
        for bundle_id, files in sorted(bundle_products.items()):
            bundle_dir = staging / bundle_id
            (bundle_dir / "items").mkdir(parents=True, mode=0o700)
            os.chmod(bundle_dir, 0o700)
            os.chmod(bundle_dir / "items", 0o700)
            for relative, payload in sorted(files.items()):
                target = bundle_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                current = target.parent
                while current != bundle_dir:
                    os.chmod(current, 0o700)
                    current = current.parent
                target.write_bytes(payload)
                os.chmod(target, 0o600)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{schedule_path.name}.",
            suffix=".tmp",
            dir=schedule_path.parent,
            delete=False,
        ) as handle:
            schedule_temp = Path(handle.name)
            handle.write(rendered_bytes(schedule))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(schedule_temp, 0o600)
        if output_root.exists() or schedule_path.exists():
            raise AssignmentError("an assignment output appeared during staging")
        os.replace(staging, output_root)
        output_committed = True
        os.link(schedule_temp, schedule_path)
        schedule_committed = True
        os.chmod(schedule_path, 0o600)
    except Exception:
        if schedule_committed and schedule_path.exists():
            schedule_path.unlink()
        if output_committed and output_root.exists():
            shutil.rmtree(output_root, ignore_errors=True)
        raise
    finally:
        if schedule_temp is not None and schedule_temp.exists():
            schedule_temp.unlink()
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1 or parsed > 200000:
        raise argparse.ArgumentTypeError("must be between 1 and 200000")
    return parsed


def seed_hex(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise argparse.ArgumentTypeError("must be exactly 64 lowercase hexadecimal characters")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze balanced independent repair-assessor assignments and create one "
            "token-bound, arm-blind subset bundle per rostered assessor."
        )
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=PILOT_ROOT / "repair_panel" / "manifest.json",
        help="Reviewer-safe repair-panel manifest.",
    )
    parser.add_argument(
        "--arm-map",
        type=Path,
        default=COORDINATOR_ROOT / "repair_panel_arm_map.json",
        help="Private arm map emitted with the exact panel.",
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=COORDINATOR_ROOT / "repair_assessor_roster.json",
        help="Completed independent-reviewer roster (not the template).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PILOT_ROOT / "repair_assessor_bundles",
        help="New root containing one isolated reviewer-safe directory per assessor alias.",
    )
    parser.add_argument(
        "--schedule",
        type=Path,
        default=COORDINATOR_ROOT / "repair_assessor_schedule.json",
        help="New coordinator-only frozen schedule with private joins and tokens.",
    )
    parser.add_argument(
        "--seed-hex",
        type=seed_hex,
        help=(
            "Optional private 256-bit lowercase hexadecimal seed for an audited rerun. "
            "If omitted, the builder generates one and records it only in the private schedule."
        ),
    )
    parser.add_argument(
        "--max-balance-trials",
        type=positive_int,
        default=20000,
        help="Maximum deterministic balance-search trials (default: 20000).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest_path = require_file(
            args.panel_manifest, PILOT_ROOT, "public repair-panel manifest"
        )
        arm_map_path = require_file(args.arm_map, COORDINATOR_ROOT, "private arm map")
        roster_path = require_file(args.roster, COORDINATOR_ROOT, "reviewer roster")
        require_within(args.output_root, PILOT_ROOT, "assessor-bundle output root")
        require_within(args.schedule, COORDINATOR_ROOT, "private schedule output")
        if args.output_root.exists() or args.schedule.exists():
            raise AssignmentError("an assignment output already exists; refusing to overwrite")

        manifest, panel = load_panel(manifest_path)
        _, entries, availability = join_private_arms(
            arm_map_path, manifest_path, manifest, panel
        )
        observed_arms = availability["observed_feedback_arms"]
        roster, reviewers, targets = load_roster(roster_path, manifest["study_id"])
        instruments = instrument_hashes()
        seed = bytes.fromhex(args.seed_hex) if args.seed_hex else secrets.token_bytes(32)
        trial, assignment = freeze_balanced_assignments(
            entries,
            reviewers,
            targets,
            observed_arms,
            seed,
            args.max_balance_trials,
        )
        validate_assignment(assignment, reviewers, targets, entries, observed_arms)
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        schedule_id = "RASCH-" + derived_hex(
            seed,
            "schedule|"
            + manifest["study_id"]
            + "|"
            + sha256_file(manifest_path)
            + "|"
            + sha256_file(arm_map_path)
            + "|"
            + sha256_file(roster_path),
        )
        bundle_products, private_rows = build_bundle_products(
            manifest["study_id"],
            schedule_id,
            created_at,
            sha256_file(manifest_path),
            instruments,
            reviewers,
            assignment,
            observed_arms,
            seed,
        )
        schedule = build_schedule(
            manifest["study_id"],
            schedule_id,
            created_at,
            seed,
            manifest_path,
            arm_map_path,
            roster_path,
            roster,
            instruments,
            availability,
            entries,
            trial,
            private_rows,
        )
        commit_products(args.output_root, args.schedule, bundle_products, schedule)
    except AssignmentError as exc:
        raise SystemExit(f"ASSIGNMENT BLOCKED: {exc}. Nothing was written.") from exc
    except OSError as exc:
        raise SystemExit(
            f"ASSIGNMENT BLOCKED by a filesystem error: {exc}. Inspect only the exact "
            "requested assignment output paths before retrying."
        ) from exc

    print(
        json.dumps(
            {
                "status": "repair_assessor_assignments_frozen",
                "schedule_id": schedule_id,
                "assessor_count": len(private_rows),
                "assignment_count": schedule["design"]["total_assignment_count"],
                "balanced": True,
                "contains_real_source_text": False,
                "reviewer_bundles": str(args.output_root),
                "coordinator_schedule": str(args.schedule),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
