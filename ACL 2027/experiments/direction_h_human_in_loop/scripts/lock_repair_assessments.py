#!/usr/bin/env python3
"""Validate and lock every planned repair-panel response before unblinding.

This coordinator-only command reads the frozen private assignment schedule and
the isolated reviewer bundle directories. It requires one complete three-file
response for every planned assignment, rejects extras or drift, and writes a
hash-only lock. It never creates or changes an assessment or rating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_repair_assessor_assignments import (
    BUNDLE_SCHEMA,
    BUILDER_SCRIPT,
    COORDINATOR_ROOT,
    DIRECTION_ROOT,
    INSTRUMENT_PATHS,
    PANEL_ITEM_SCHEMA,
    PAPER_METRIC_SCHEMA,
    PILOT_ROOT,
    POST_RATING_LINK_SCHEMA,
    REPAIR_ASSESSMENT_SCHEMA,
    REPAIR_COLLECTOR,
    REPAIR_LOCK_SCHEMA,
    REPAIR_LOCK_SCRIPT,
    RUNTIME_PACKAGE_PATHS,
    ROSTER_SCHEMA,
    SCHEDULE_SCHEMA,
    AssignmentError,
    canonical_bytes,
    is_within,
    join_private_arms,
    load_json,
    load_panel,
    load_roster,
    make_aliases,
    nul_hash,
    require_file,
    require_within,
    sha256_bytes,
    sha256_file,
    validate,
)


LOCK_SCHEMA = REPAIR_LOCK_SCHEMA
LOCK_SCRIPT = Path(__file__).resolve()
RATING_FIELDS = {
    "annotation_version",
    "rater_id",
    "evaluator_group",
    "packet_id",
    "corpus_id",
    "evaluation_role",
    "output_id",
    "rated_at_utc",
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
    "cannot_judge",
    "confidence",
    "disposition",
    "serious_error_flags",
    "review_seconds",
    "requested_expertise",
    "rationale",
}
RESPONSE_FILENAMES = {
    "repair_assessment.json",
    "post_revision_rating.json",
    "rating_link.json",
}
PRIVATE_RESPONSE_KEYS = {
    "assignment_token",
    "condition",
    "feedback_arm",
    "feedback_author",
    "feedback_content",
    "model_identity",
    "paired_case_group_id",
    "repeat_index",
    "revision_case_id",
    "revision_diagnosis",
    "source_blinded_revision_id",
    "truth_map",
}


def walk_keys(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def canonical_record_sha256(record: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(record))


def assessment_id(study_id: str, task_id: str, rater_id: str) -> str:
    identity = "|".join(
        ["direction-h-repair-assessment-v1", study_id, task_id, rater_id]
    )
    return "DHA-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()


def link_id(assessment_record_id: str, blind_id: str) -> str:
    identity = "|".join(
        ["direction-h-post-revision-rating-link-v1", assessment_record_id, blind_id]
    )
    return "DHL-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()


def rating_key(rating: dict[str, Any]) -> dict[str, Any]:
    return {
        key: rating[key]
        for key in (
            "annotation_version",
            "rater_id",
            "packet_id",
            "corpus_id",
            "evaluation_role",
            "output_id",
            "rated_at_utc",
        )
    }


def decode_pointer_token(token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            decoded.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise AssignmentError(f"malformed JSON Pointer token: {token!r}")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise AssignmentError(f"not a JSON Pointer: {pointer!r}")
    current = document
    for encoded in pointer[1:].split("/"):
        token = decode_pointer_token(encoded)
        if isinstance(current, dict):
            if token not in current:
                raise AssignmentError(f"JSON Pointer does not resolve: {pointer!r}")
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise AssignmentError(f"invalid JSON Pointer array index: {pointer!r}")
            index = int(token)
            if index >= len(current):
                raise AssignmentError(f"JSON Pointer array index out of range: {pointer!r}")
            current = current[index]
        else:
            raise AssignmentError(f"JSON Pointer traverses a scalar: {pointer!r}")
    return current


def current_instrument_hashes() -> dict[str, str]:
    return {label: sha256_file(path) for label, path in INSTRUMENT_PATHS.items()}


def reconstruct_assignment_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "assignment_payload_version": "direction-h-repair-assignment-payload-v1",
        "study_id": manifest["study_id"],
        "schedule_id": manifest["schedule_id"],
        "bundle_id": manifest["bundle_id"],
        "assessor_alias": manifest["assessor_alias"],
        "evaluator_group": manifest["evaluator_group"],
        "parent_panel_manifest_sha256": manifest["parent_panel_manifest_sha256"],
        "frozen_instrument_hashes": manifest["frozen_instrument_hashes"],
        "items": manifest["items"],
    }


def verify_schedule_inputs(
    schedule: dict[str, Any],
    panel_manifest: Path,
    arm_map: Path,
    roster: Path,
) -> dict[str, str]:
    validate(schedule, SCHEDULE_SCHEMA, "private repair-assessor schedule")
    if schedule["status"] != "frozen" or schedule["data_scope"] != "synthetic_only":
        raise AssignmentError("repair-assessor schedule is not a frozen synthetic schedule")
    expected = {
        "public_panel_manifest_sha256": sha256_file(
            require_file(panel_manifest, PILOT_ROOT, "public panel manifest")
        ),
        "private_arm_map_sha256": sha256_file(
            require_file(arm_map, COORDINATOR_ROOT, "private arm map")
        ),
        "reviewer_roster_sha256": sha256_file(
            require_file(roster, COORDINATOR_ROOT, "reviewer roster")
        ),
        "reviewer_roster_schema_sha256": sha256_file(ROSTER_SCHEMA),
        "assessor_bundle_schema_sha256": sha256_file(BUNDLE_SCHEMA),
        "repair_panel_item_schema_sha256": sha256_file(PANEL_ITEM_SCHEMA),
        "assignment_builder_script_sha256": sha256_file(BUILDER_SCRIPT),
        "repair_assessment_lock_script_sha256": sha256_file(REPAIR_LOCK_SCRIPT),
        "repair_assessment_lock_schema_sha256": sha256_file(REPAIR_LOCK_SCHEMA),
        **current_instrument_hashes(),
    }
    for key, digest in expected.items():
        if schedule["input_hashes"].get(key) != digest:
            raise AssignmentError(f"frozen assignment input/instrument drift: {key}")

    manifest, panel = load_panel(panel_manifest)
    _, entries, availability = join_private_arms(
        arm_map, panel_manifest, manifest, panel
    )
    roster_record, roster_reviewers, targets = load_roster(
        roster, manifest["study_id"]
    )
    if schedule["study_id"] != manifest["study_id"]:
        raise AssignmentError("assignment schedule and repair panel study_id differ")
    if schedule["design"]["assignment_targets"] != roster_record["assignment_targets"]:
        raise AssignmentError("assignment schedule replication targets drifted from the roster")
    for key, value in availability.items():
        if schedule["design"].get(key) != value:
            raise AssignmentError(f"assignment schedule availability accounting drift: {key}")
    if schedule["design"]["panel_item_count"] != len(entries):
        raise AssignmentError("assignment schedule panel_item_count drifted")

    roster_by_id = {row["rater_id"]: row for row in roster_reviewers}
    schedule_by_id = {row["rater_id"]: row for row in schedule["reviewers"]}
    if len(schedule_by_id) != len(schedule["reviewers"]) or set(schedule_by_id) != set(
        roster_by_id
    ):
        raise AssignmentError("assignment schedule reviewer roster drifted")
    source_by_blind_id = {entry["row"]["blinded_revision_id"]: entry for entry in entries}
    observed_arms = availability["observed_feedback_arms"]
    seed = bytes.fromhex(schedule["assignment_seed_hex"])
    coverage: Counter[tuple[str, str]] = Counter()
    workloads_by_group: dict[str, list[int]] = defaultdict(list)
    total_assignments = 0
    for rater_id, reviewer in schedule_by_id.items():
        group = reviewer["evaluator_group"]
        if roster_by_id[rater_id]["evaluator_group"] != group:
            raise AssignmentError(f"assignment schedule evaluator group drifted: {rater_id}")
        assignments = reviewer["assignments"]
        if reviewer["workload_count"] != len(assignments) or not assignments:
            raise AssignmentError(f"assignment schedule workload mismatch: {rater_id}")
        source_tasks: set[str] = set()
        source_items: set[str] = set()
        recomputed_arm_counts = Counter({arm: 0 for arm in observed_arms})
        for assigned in assignments:
            source_id = assigned["source_blinded_revision_id"]
            if source_id in source_items or source_id not in source_by_blind_id:
                raise AssignmentError(
                    f"assignment schedule has a duplicate/unknown source item: {rater_id}"
                )
            source_items.add(source_id)
            entry = source_by_blind_id[source_id]
            private = entry["private"]
            source_task = entry["row"]["task_id"]
            if source_task in source_tasks:
                raise AssignmentError(
                    f"assignment schedule exposes two variants of one task: {rater_id}"
                )
            source_tasks.add(source_task)
            expected_fields = {
                "source_task_id": source_task,
                "source_revision_case_id": private["revision_case_id"],
                "source_repeat_index": private["repeat_index"],
                "source_target_assessment_reference_id": entry["item"][
                    "target_assessment_reference_id"
                ],
                "source_panel_item_sha256": entry["row"]["sha256"],
                "corpus_id": entry["item"]["corpus_id"],
                "feedback_arm": entry["arm"],
            }
            for field, expected_value in expected_fields.items():
                if assigned[field] != expected_value:
                    raise AssignmentError(
                        f"assignment schedule source/arm join drifted on {field}: {rater_id}"
                    )
            item_alias, task_alias, reference_alias = make_aliases(seed, entry)
            expected_aliases = {
                "assigned_blinded_revision_id": item_alias,
                "assigned_task_id": task_alias,
                "assigned_target_assessment_reference_id": reference_alias,
                "assigned_item_file": f"items/{item_alias}.json",
            }
            for field, expected_value in expected_aliases.items():
                if assigned[field] != expected_value:
                    raise AssignmentError(
                        f"assignment schedule stable alias drifted on {field}: {rater_id}"
                    )
            recomputed_arm_counts[entry["arm"]] += 1
            coverage[(group, source_id)] += 1
        if set(reviewer["arm_counts"]) != set(observed_arms) or dict(
            recomputed_arm_counts
        ) != reviewer["arm_counts"]:
            raise AssignmentError(f"assignment schedule arm counts drifted: {rater_id}")
        counts = [recomputed_arm_counts[arm] for arm in observed_arms]
        if max(counts) - min(counts) > 1:
            raise AssignmentError(f"assignment schedule arm balance failed: {rater_id}")
        workloads_by_group[group].append(len(assignments))
        total_assignments += len(assignments)
    for group, workloads in workloads_by_group.items():
        if max(workloads) - min(workloads) > 1:
            raise AssignmentError(f"assignment schedule workload balance failed: {group}")
    for group, replication in targets.items():
        for source_id in source_by_blind_id:
            if coverage[(group, source_id)] != replication:
                raise AssignmentError(
                    f"assignment schedule exact coverage failed: {group}/{source_id}"
                )
    if schedule["design"]["total_assignment_count"] != total_assignments:
        raise AssignmentError("assignment schedule total assignment count drifted")
    return current_instrument_hashes()


def verify_bundle(
    schedule: dict[str, Any],
    reviewer: dict[str, Any],
    bundle_root: Path,
    instruments: dict[str, str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], Path]:
    bundle_id = reviewer["bundle_id"]
    rater_id = reviewer["rater_id"]
    bundle_dir = require_within(bundle_root / bundle_id, bundle_root, f"bundle {bundle_id}")
    if bundle_dir.is_symlink() or not bundle_dir.is_dir():
        raise AssignmentError(f"isolated assessor bundle is missing: {bundle_id}")
    allowed_root_entries = {"manifest.json", "items", "runtime", "responses"}
    root_entries = {path.name for path in bundle_dir.iterdir()}
    if not root_entries <= allowed_root_entries or not {
        "manifest.json",
        "items",
        "runtime",
    } <= root_entries:
        raise AssignmentError(f"bundle {bundle_id} contains an unexpected root entry")
    manifest_path = require_file(bundle_dir / "manifest.json", bundle_dir, "bundle manifest")
    if sha256_file(manifest_path) != reviewer["bundle_manifest_sha256"]:
        raise AssignmentError(f"bundle-manifest hash drift: {bundle_id}")
    manifest = load_json(manifest_path, f"bundle manifest {bundle_id}")
    validate(manifest, BUNDLE_SCHEMA, f"bundle manifest {bundle_id}")
    if manifest["study_id"] != schedule["study_id"] or manifest["schedule_id"] != schedule[
        "schedule_id"
    ]:
        raise AssignmentError(f"bundle {bundle_id} has the wrong study/schedule identity")
    for key in ("bundle_id", "assessor_alias", "evaluator_group"):
        if manifest[key] != reviewer[key]:
            raise AssignmentError(f"bundle/schedule mismatch for {bundle_id}: {key}")
    if manifest["frozen_instrument_hashes"] != instruments:
        raise AssignmentError(f"bundle {bundle_id} instrument hashes drifted")
    payload_sha = sha256_bytes(canonical_bytes(reconstruct_assignment_payload(manifest)))
    if payload_sha != manifest["assignment_payload_sha256"]:
        raise AssignmentError(f"bundle {bundle_id} assignment payload hash mismatch")
    token_sha = nul_hash(
        "direction-h-assignment-token-v1",
        schedule["study_id"],
        schedule["schedule_id"],
        bundle_id,
        reviewer["assignment_token"],
    )
    binding_sha = nul_hash(
        "direction-h-rater-binding-v1",
        schedule["study_id"],
        schedule["schedule_id"],
        bundle_id,
        rater_id,
        reviewer["evaluator_group"],
        payload_sha,
        reviewer["assignment_token"],
    )
    if token_sha != manifest["assignment_token_sha256"] or token_sha != reviewer[
        "assignment_token_sha256"
    ]:
        raise AssignmentError(f"bundle {bundle_id} assignment-token hash mismatch")
    if binding_sha != manifest["rater_binding_sha256"] or binding_sha != reviewer[
        "rater_binding_sha256"
    ]:
        raise AssignmentError(f"bundle {bundle_id} rater binding mismatch")

    scheduled_by_alias = {
        row["assigned_blinded_revision_id"]: row for row in reviewer["assignments"]
    }
    if len(scheduled_by_alias) != len(reviewer["assignments"]):
        raise AssignmentError(f"bundle {bundle_id} has duplicate scheduled item aliases")
    manifest_by_alias = {row["blinded_revision_id"]: row for row in manifest["items"]}
    if set(manifest_by_alias) != set(scheduled_by_alias):
        raise AssignmentError(f"bundle {bundle_id} manifest/schedule item set differs")
    if manifest["item_count"] != reviewer["workload_count"]:
        raise AssignmentError(f"bundle {bundle_id} workload count differs")

    item_dir = bundle_dir / "items"
    if item_dir.is_symlink() or not item_dir.is_dir():
        raise AssignmentError(f"bundle {bundle_id} items directory is missing")
    expected_item_names = {Path(row["item_file"]).name for row in manifest["items"]}
    actual_item_names = {path.name for path in item_dir.iterdir()}
    if actual_item_names != expected_item_names:
        raise AssignmentError(f"bundle {bundle_id} item directory differs from its manifest")
    tree_map = {"manifest.json": sha256_file(manifest_path)}
    expected_runtime_files = set(RUNTIME_PACKAGE_PATHS.values())
    runtime_root = bundle_dir / "runtime"
    if runtime_root.is_symlink() or not runtime_root.is_dir():
        raise AssignmentError(f"bundle {bundle_id} runtime directory is missing")
    actual_runtime_files = {
        str(path.relative_to(bundle_dir))
        for path in runtime_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    unsafe_runtime_entries = [
        path
        for path in runtime_root.rglob("*")
        if path.is_symlink() or (not path.is_file() and not path.is_dir())
    ]
    if unsafe_runtime_entries or actual_runtime_files != expected_runtime_files:
        raise AssignmentError(f"bundle {bundle_id} runtime package differs from its contract")
    for label, relative in RUNTIME_PACKAGE_PATHS.items():
        runtime_path = require_file(
            bundle_dir / relative, bundle_dir, f"runtime instrument {label}"
        )
        digest = sha256_file(runtime_path)
        if (
            digest != instruments[label]
            or digest != manifest["frozen_instrument_hashes"][label]
        ):
            raise AssignmentError(f"bundle {bundle_id} runtime instrument drift: {label}")
        tree_map[relative] = digest
    assigned_items: dict[str, dict[str, Any]] = {}
    for alias, row in manifest_by_alias.items():
        item_path = require_file(bundle_dir / row["item_file"], bundle_dir, f"assigned item {alias}")
        if sha256_file(item_path) != row["sha256"]:
            raise AssignmentError(f"assigned item hash mismatch: {alias}")
        tree_map[row["item_file"]] = row["sha256"]
        item = load_json(item_path, f"assigned item {alias}")
        validate(item, PANEL_ITEM_SCHEMA, f"assigned item {alias}")
        scheduled = scheduled_by_alias[alias]
        for row_key, item_key in (
            ("blinded_revision_id", "blinded_revision_id"),
            ("task_id", "task_id"),
            ("corpus_id", "corpus_id"),
            ("packet_id", "packet_id"),
            ("starting_output_id", "starting_output_id"),
            ("evaluation_role", "evaluation_role"),
            ("target_assessment_reference_id", "target_assessment_reference_id"),
        ):
            if row[row_key] != item[item_key]:
                raise AssignmentError(f"assigned manifest/item mismatch for {alias}: {row_key}")
        if scheduled["assigned_task_id"] != item["task_id"] or scheduled[
            "assigned_target_assessment_reference_id"
        ] != item["target_assessment_reference_id"]:
            raise AssignmentError(f"assigned schedule/item alias mismatch for {alias}")
        if scheduled["corpus_id"] != item["corpus_id"] or scheduled[
            "assigned_item_sha256"
        ] != row["sha256"]:
            raise AssignmentError(f"assigned schedule/item identity mismatch for {alias}")
        assigned_items[alias] = item
    if sha256_bytes(canonical_bytes(dict(sorted(tree_map.items())))) != reviewer[
        "bundle_tree_sha256"
    ]:
        raise AssignmentError(f"bundle {bundle_id} tree hash mismatch")
    return manifest, assigned_items, bundle_dir


def validate_response_triple(
    schedule: dict[str, Any],
    reviewer: dict[str, Any],
    private_assignment: dict[str, Any],
    item: dict[str, Any],
    response_dir: Path,
) -> dict[str, Any]:
    expected_assessment_id = assessment_id(
        schedule["study_id"], item["task_id"], reviewer["rater_id"]
    )
    if response_dir.name != expected_assessment_id:
        raise AssignmentError(f"response directory has noncanonical assessment ID: {response_dir}")
    if response_dir.is_symlink() or not response_dir.is_dir():
        raise AssignmentError(f"missing response bundle: {response_dir}")
    names = {path.name for path in response_dir.iterdir()}
    if names != RESPONSE_FILENAMES:
        raise AssignmentError(
            f"response bundle {expected_assessment_id} is not an exact three-record bundle"
        )
    paths = {
        name: require_file(response_dir / name, response_dir, f"response {name}")
        for name in RESPONSE_FILENAMES
    }
    assessment = load_json(paths["repair_assessment.json"], "repair assessment")
    rating = load_json(paths["post_revision_rating.json"], "post-revision rating")
    link = load_json(paths["rating_link.json"], "post-revision rating link")
    if not all(isinstance(record, dict) for record in (assessment, rating, link)):
        raise AssignmentError(f"response bundle {expected_assessment_id} contains a non-object")
    validate(assessment, REPAIR_ASSESSMENT_SCHEMA, "locked repair assessment")
    validate(rating, PAPER_METRIC_SCHEMA, "locked post-revision rating")
    validate(link, POST_RATING_LINK_SCHEMA, "locked post-revision rating link")
    for record in (assessment, rating, link):
        leaked = PRIVATE_RESPONSE_KEYS & set(walk_keys(record))
        if leaked:
            raise AssignmentError(
                f"private assignment field leaked into response {expected_assessment_id}: "
                + ", ".join(sorted(leaked))
            )
    if set(rating) != RATING_FIELDS:
        raise AssignmentError(f"post-revision rating is not the exact shared-field projection")

    expected_assessment = {
        "assessment_id": expected_assessment_id,
        "assessment_stage": "independent_initial",
        "rater_id": reviewer["rater_id"],
        "evaluator_group": reviewer["evaluator_group"],
        "evaluation_role": item["evaluation_role"],
        "task_id": item["task_id"],
        "packet_id": item["packet_id"],
        "starting_output_id": item["starting_output_id"],
        "blinded_revision_id": item["blinded_revision_id"],
        "target_assessment_reference_id": item["target_assessment_reference_id"],
    }
    for key, expected in expected_assessment.items():
        if assessment.get(key) != expected:
            raise AssignmentError(f"repair-assessment identity mismatch on {key}")
    expected_rating = {
        "annotation_version": "qc-paper-metrics-v1",
        "rater_id": reviewer["rater_id"],
        "evaluator_group": reviewer["evaluator_group"],
        "packet_id": item["packet_id"],
        "corpus_id": item["corpus_id"],
        "evaluation_role": item["evaluation_role"],
        "output_id": item["blinded_revision_id"],
    }
    for key, expected in expected_rating.items():
        if rating.get(key) != expected:
            raise AssignmentError(f"post-revision rating identity mismatch on {key}")

    finding_flags = {finding["collateral_flag"] for finding in assessment["collateral_findings"]}
    if set(assessment["collateral_error_flags"]) != finding_flags:
        raise AssignmentError("repair collateral flags/findings differ")
    excerpt_ids = {row["excerpt_id"] for row in item["evidence_packet"]["excerpts"]}
    for finding in assessment["collateral_findings"]:
        if not set(finding["evidence_excerpt_ids"]) <= excerpt_ids:
            raise AssignmentError("repair collateral finding cites an unknown excerpt")
        for pointer in finding["revision_output_locations"]:
            resolve_pointer(item["revised_output"], pointer)

    if link["study_id"] != schedule["study_id"]:
        raise AssignmentError("rating link study_id mismatch")
    if link["assessment_id"] != assessment["assessment_id"]:
        raise AssignmentError("rating link assessment_id mismatch")
    if link["task_id"] != assessment["task_id"] or link[
        "blinded_revision_id"
    ] != assessment["blinded_revision_id"]:
        raise AssignmentError("rating link assigned identity mismatch")
    if link["link_id"] != link_id(assessment["assessment_id"], item["blinded_revision_id"]):
        raise AssignmentError("rating link has a noncanonical link_id")
    if link["rating_key"] != rating_key(rating):
        raise AssignmentError("rating link rating_key mismatch")
    assessment_record_hash = canonical_record_sha256(assessment)
    rating_record_hash = canonical_record_sha256(rating)
    if link["repair_assessment_record_sha256"] != assessment_record_hash:
        raise AssignmentError("rating link repair-assessment hash mismatch")
    if link["post_revision_rating_record_sha256"] != rating_record_hash:
        raise AssignmentError("rating link post-revision-rating hash mismatch")
    if link["shared_rating_schema_sha256"] != sha256_file(PAPER_METRIC_SCHEMA):
        raise AssignmentError("rating link shared schema hash drift")
    timing = link["timing"]
    if timing["repair_assessment_review_seconds"] != assessment["review_seconds"]:
        raise AssignmentError("rating link repair timing mismatch")
    if timing["post_revision_rating_review_seconds"] != rating["review_seconds"]:
        raise AssignmentError("rating link rating timing mismatch")
    expected_increment = round(rating["review_seconds"] - assessment["review_seconds"], 3)
    if expected_increment < 0 or timing["incremental_metric_phase_seconds"] != expected_increment:
        raise AssignmentError("rating link incremental timing mismatch")

    relative_dir = response_dir.relative_to(DIRECTION_ROOT)
    return {
        "rater_id": reviewer["rater_id"],
        "evaluator_group": reviewer["evaluator_group"],
        "bundle_id": reviewer["bundle_id"],
        "assessment_id": assessment["assessment_id"],
        "assigned_task_id": private_assignment["assigned_task_id"],
        "assigned_blinded_revision_id": private_assignment["assigned_blinded_revision_id"],
        "corpus_id": private_assignment["corpus_id"],
        "response_bundle_directory": str(relative_dir),
        "repair_assessment_file_sha256": sha256_file(paths["repair_assessment.json"]),
        "repair_assessment_record_sha256": assessment_record_hash,
        "post_revision_rating_file_sha256": sha256_file(
            paths["post_revision_rating.json"]
        ),
        "post_revision_rating_record_sha256": rating_record_hash,
        "rating_link_file_sha256": sha256_file(paths["rating_link.json"]),
        "rating_link_record_sha256": canonical_record_sha256(link),
    }


def collect_locked_records(
    schedule: dict[str, Any], bundle_root: Path, instruments: dict[str, str]
) -> list[dict[str, Any]]:
    bundle_root = require_within(bundle_root, PILOT_ROOT, "isolated bundle root")
    if bundle_root.is_symlink() or not bundle_root.is_dir():
        raise AssignmentError("isolated bundle root is missing")
    expected_bundles = {reviewer["bundle_id"] for reviewer in schedule["reviewers"]}
    actual_bundles = {path.name for path in bundle_root.iterdir()}
    if actual_bundles != expected_bundles:
        raise AssignmentError("isolated bundle root contains a missing or unexpected bundle")

    locked: list[dict[str, Any]] = []
    seen_assessments: set[str] = set()
    for reviewer in schedule["reviewers"]:
        manifest, items, bundle_dir = verify_bundle(
            schedule, reviewer, bundle_root, instruments
        )
        responses_root = bundle_dir / "responses"
        if responses_root.is_symlink() or not responses_root.is_dir():
            raise AssignmentError(f"responses are incomplete for bundle {reviewer['bundle_id']}")
        rater_dirs = {path.name for path in responses_root.iterdir()}
        if rater_dirs != {reviewer["rater_id"]}:
            raise AssignmentError(
                f"bundle {reviewer['bundle_id']} has a missing or unexpected rater response directory"
            )
        rater_dir = responses_root / reviewer["rater_id"]
        if rater_dir.is_symlink() or not rater_dir.is_dir():
            raise AssignmentError(f"invalid rater response directory: {rater_dir}")
        expected_ids = {
            assessment_id(schedule["study_id"], row["assigned_task_id"], reviewer["rater_id"])
            for row in reviewer["assignments"]
        }
        actual_ids = {path.name for path in rater_dir.iterdir()}
        if actual_ids != expected_ids:
            raise AssignmentError(
                f"rater {reviewer['rater_id']} has a missing, duplicate, pending, or unexpected response"
            )
        for private_assignment in reviewer["assignments"]:
            alias = private_assignment["assigned_blinded_revision_id"]
            item = items[alias]
            expected_id = assessment_id(
                schedule["study_id"], item["task_id"], reviewer["rater_id"]
            )
            record = validate_response_triple(
                schedule,
                reviewer,
                private_assignment,
                item,
                rater_dir / expected_id,
            )
            if record["assessment_id"] in seen_assessments:
                raise AssignmentError("duplicate assessment identity across isolated bundles")
            seen_assessments.add(record["assessment_id"])
            locked.append(record)
    return sorted(locked, key=lambda row: (row["rater_id"], row["assigned_task_id"]))


def write_lock(path: Path, record: dict[str, Any]) -> None:
    path = require_within(path, COORDINATOR_ROOT, "repair-assessment lock output")
    if path.exists():
        raise AssignmentError("repair-assessment lock already exists; refusing to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed unless every frozen repair-assessor assignment has exactly one "
            "valid assessment/shared-rating/link triple, then write the unblinding gate lock."
        )
    )
    parser.add_argument(
        "--schedule",
        type=Path,
        default=COORDINATOR_ROOT / "repair_assessor_schedule.json",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=PILOT_ROOT / "repair_assessor_bundles",
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=PILOT_ROOT / "repair_panel" / "manifest.json",
    )
    parser.add_argument(
        "--arm-map",
        type=Path,
        default=COORDINATOR_ROOT / "repair_panel_arm_map.json",
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=COORDINATOR_ROOT / "repair_assessor_roster.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=COORDINATOR_ROOT / "repair_assessment_lock.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        schedule_path = require_file(args.schedule, COORDINATOR_ROOT, "assignment schedule")
        require_within(args.output, COORDINATOR_ROOT, "repair-assessment lock output")
        if args.output.exists():
            raise AssignmentError("repair-assessment lock already exists; refusing to overwrite")
        schedule = load_json(schedule_path, "assignment schedule")
        instruments = verify_schedule_inputs(
            schedule, args.panel_manifest, args.arm_map, args.roster
        )
        locked_records = collect_locked_records(schedule, args.bundle_root, instruments)
        planned = schedule["design"]["total_assignment_count"]
        if len(locked_records) != planned:
            raise AssignmentError(
                f"expected {planned} complete response bundles but validated {len(locked_records)}"
            )
        lock = {
            "repair_assessment_lock_version": "direction-h-repair-assessment-lock-v1",
            "study_id": schedule["study_id"],
            "schedule_id": schedule["schedule_id"],
            "status": "locked",
            "visibility": "coordinator_only",
            "data_scope": "synthetic_only",
            "contains_protected_text": False,
            "locked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "assignment_schedule_sha256": sha256_file(schedule_path),
            "lock_builder_script_sha256": sha256_file(LOCK_SCRIPT),
            "repair_assessment_lock_schema_sha256": sha256_file(LOCK_SCHEMA),
            "hash_serialization": "utf8_json_sorted_keys_compact_plus_lf_v1",
            "frozen_instrument_hashes": instruments,
            "planned_response_bundle_count": planned,
            "locked_response_bundle_count": len(locked_records),
            "unexpected_response_entry_count": 0,
            "unblinding_ready": True,
            "records": locked_records,
        }
        validate(lock, LOCK_SCHEMA, "repair-assessment lock")
        if lock["planned_response_bundle_count"] != lock["locked_response_bundle_count"]:
            raise AssignmentError("planned and locked response counts differ")
        write_lock(args.output, lock)
    except AssignmentError as exc:
        raise SystemExit(f"LOCK BLOCKED: {exc}. Nothing was written.") from exc
    except OSError as exc:
        raise SystemExit(
            f"LOCK BLOCKED by a filesystem error: {exc}. No lock was intentionally written."
        ) from exc

    print(
        json.dumps(
            {
                "status": "repair_assessments_locked",
                "schedule_id": schedule["schedule_id"],
                "locked_response_bundle_count": len(locked_records),
                "unblinding_ready": True,
                "contains_real_source_text": False,
                "lock_file": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
