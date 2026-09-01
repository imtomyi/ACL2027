#!/usr/bin/env python3
"""Build paired theme-level revision cases after every prospective gate passes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from finalize_direction_j_charlie_observations import verify_lock
from serve_direction_j_browser import (
    DIRECTION_ROOT,
    J_RUN_MANIFEST,
    J_RUN_ROOT,
    InstrumentError,
    canonical_bytes,
    load_json,
    parse_utc,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_activation,
    validate_prepared,
)
from validate_direction_j_theme_revision import (
    FREEZE_PATH,
    TARGET_BRIEFS_PATH,
    TARGET_COMMITMENT_PATH,
    TARGET_VERIFICATION_PATH,
    THEME_ROOT,
    theme_store,
    validate_freeze,
    validate_theme,
)


OUTPUT_ROOT = THEME_ROOT / "cases"
ARMS = ("no_feedback", "charlie_feedback")
TASK = (
    "Revise one proposed qualitative interpretation and its candidate evidence "
    "assertions using only the displayed synthetic item and the frozen analytic contract."
)


def short_id(prefix: str, *parts: str) -> str:
    material = "\0".join(parts).encode("utf-8")
    return prefix + hashlib.sha256(material).hexdigest()[:20]


def exact_locked_path(relative: str) -> Path:
    path = DIRECTION_ROOT / relative
    if path.is_symlink():
        raise InstrumentError(f"locked response path is a symlink: {relative}")
    resolved = path.resolve()
    try:
        resolved.relative_to(DIRECTION_ROOT.resolve())
    except ValueError as exc:
        raise InstrumentError(f"locked response path leaves Direction H: {relative}") from exc
    if not resolved.is_file():
        raise InstrumentError(f"locked response path is missing: {relative}")
    return resolved


def validate_target_gate(
    prepared: dict[str, Any], lock: dict[str, Any], freeze: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    store = theme_store()
    verification = load_json(TARGET_VERIFICATION_PATH, "theme target verification")
    briefs = load_json(TARGET_BRIEFS_PATH, "theme target briefs")
    commitment = load_json(TARGET_COMMITMENT_PATH, "theme target-brief commitment")
    validate_theme(
        verification,
        "target_verification.schema.json",
        "theme target verification",
        store,
    )
    validate_theme(briefs, "target_briefs.schema.json", "theme target briefs", store)
    validate_theme(
        commitment,
        "target_brief_commitment.schema.json",
        "theme target-brief commitment",
        store,
    )
    if verification["status"] != "complete":
        raise InstrumentError("independent itemwise target verification is incomplete")
    if briefs["status"] != "complete" or commitment["status"] != "committed":
        raise InstrumentError("target briefs are not completed and prospectively committed")
    if verification["first_stage_lock_sha256"] != sha256_file(
        DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_first_stage_lock.json"
    ):
        raise InstrumentError("target verification is not bound to the current first-stage lock")
    run_manifest = load_json(J_RUN_MANIFEST, "Direction J run manifest")
    private_relative = run_manifest.get("private_key_path")
    if private_relative != "private/item_key.jsonl":
        raise InstrumentError("Direction J private-key path drifted")
    private_path = J_RUN_ROOT / private_relative
    if private_path.is_symlink() or not private_path.is_file():
        raise InstrumentError("Direction J private synthetic key is missing or unsafe")
    private_hash = sha256_file(private_path)
    if private_hash != run_manifest.get("private_key_sha256") or private_hash != verification[
        "private_item_key_sha256"
    ]:
        raise InstrumentError("target verification is not bound to the frozen private key")
    private_record_hashes: dict[str, str] = {}
    for line in private_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        private_record = json.loads(line)
        item_id = private_record.get("item_id")
        if not isinstance(item_id, str) or item_id in private_record_hashes:
            raise InstrumentError("Direction J private key contains an invalid item identity")
        private_record_hashes[item_id] = sha256_bytes(canonical_bytes(private_record))
    if briefs["verification_sha256"] != sha256_file(TARGET_VERIFICATION_PATH):
        raise InstrumentError("target briefs are not bound to the current verification")
    if commitment["target_briefs_sha256"] != sha256_file(TARGET_BRIEFS_PATH):
        raise InstrumentError("target-brief commitment hash does not match the brief file")
    if freeze["target_gate"]["verification"]["sha256"] != sha256_file(
        TARGET_VERIFICATION_PATH
    ) or freeze["target_gate"]["target_briefs"]["sha256"] != sha256_file(
        TARGET_BRIEFS_PATH
    ) or freeze["target_gate"]["target_brief_commitment"]["sha256"] != sha256_file(
        TARGET_COMMITMENT_PATH
    ):
        raise InstrumentError("revision freeze target-gate hashes drifted")

    assigned_ids = {row["item_id"] for row in prepared["assignments"]}
    verification_by_id: dict[str, dict[str, Any]] = {}
    for item in verification["items"]:
        item_id = item["item_id"]
        if item_id in verification_by_id or item_id not in assigned_ids:
            raise InstrumentError("target verification has a duplicate or unassigned item")
        if sha256_bytes(canonical_bytes(prepared["items"][item_id])) != item[
            "item_payload_sha256"
        ]:
            raise InstrumentError(f"target verification item hash drifted: {item_id}")
        if private_record_hashes.get(item_id) != item["private_truth_record_sha256"]:
            raise InstrumentError(f"target verification truth-record hash drifted: {item_id}")
        if item["classification"] == "verified_defective":
            if item["repair_feedback_eligible"] is not True:
                raise InstrumentError(
                    f"verified defective item is inconsistently marked ineligible: {item_id}"
                )
        elif item["repair_feedback_eligible"] is not False:
            raise InstrumentError(
                f"nondefective/workflow item is inconsistently marked eligible: {item_id}"
            )
        verification_by_id[item_id] = item

    eligible = [
        item
        for item in verification["items"]
        if item["classification"] == "verified_defective"
        and item["repair_feedback_eligible"] is True
    ]
    if not eligible:
        raise InstrumentError("no independently verified defective item is eligible")
    eligible_ids = [item["item_id"] for item in eligible]
    brief_by_id = {brief["item_id"]: brief for brief in briefs["items"]}
    if len(brief_by_id) != len(briefs["items"]) or set(brief_by_id) != set(eligible_ids):
        raise InstrumentError("target briefs do not exactly cover eligible defective items")
    if commitment["item_ids"] != eligible_ids:
        raise InstrumentError("target-brief commitment item order/coverage drifted")
    for item in eligible:
        brief = brief_by_id[item["item_id"]]
        if set(brief["target_item_locations"]) != set(item["target_item_locations"]):
            raise InstrumentError("target brief locations drift from independent verification")
        if set(brief["target_evidence_excerpt_ids"]) != set(
            item["target_evidence_excerpt_ids"]
        ):
            raise InstrumentError("target brief evidence IDs drift from verification")

    lock_time = parse_utc(lock["locked_at_utc"], "browser first-stage lock time")
    verification_time = parse_utc(verification["verified_at_utc"], "verification time")
    brief_time = parse_utc(briefs["created_at_utc"], "target brief time")
    commitment_time = parse_utc(commitment["committed_at_utc"], "brief commitment time")
    freeze_time = parse_utc(freeze["frozen_at_utc"], "revision freeze time")
    if not lock_time < verification_time <= brief_time <= commitment_time <= freeze_time:
        raise InstrumentError("target verification/brief/freeze chronology is not prospective")
    return eligible, verification_by_id, commitment


def build_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prepared = validate_prepared()
    validate_activation(prepared)
    lock = verify_lock(prepared)
    freeze = validate_freeze(FREEZE_PATH, "frozen")
    eligible, verification_by_id, commitment = validate_target_gate(
        prepared, lock, freeze
    )
    if OUTPUT_ROOT.exists():
        raise InstrumentError("refusing to overwrite an existing theme revision case set")
    freeze_hash = sha256_file(FREEZE_PATH)
    freeze_time = parse_utc(freeze["frozen_at_utc"], "revision freeze time")
    created_at = utc_now()
    if parse_utc(created_at, "case creation time") <= freeze_time:
        raise InstrumentError("revision cases must be created after the completed freeze")
    locked_by_item = {entry["item_id"]: entry for entry in lock["records"]}
    assignment_by_item = {row["item_id"]: row for row in prepared["assignments"]}
    eligible_by_id = {item["item_id"]: item for item in eligible}
    cases: list[dict[str, Any]] = []
    for row in prepared["assignments"]:
        item_id = row["item_id"]
        if item_id not in eligible_by_id:
            continue
        item = prepared["items"][item_id]
        verification_item = eligible_by_id[item_id]
        locked = locked_by_item[item_id]
        feedback_path = exact_locked_path(locked["feedback_path"])
        feedback = load_json(feedback_path, "locked identity-free browser feedback")
        pair_id = short_id("DHJPG_", freeze_hash, item_id, "1")
        blinded_input_id = short_id("DHJBI_", pair_id, "model-visible-pair")
        for arm in ARMS:
            reviewer_feedback = feedback["model_feedback"] if arm == "charlie_feedback" else None
            model_input = {
                "input_version": "direction-h-j-theme-revision-input-v1",
                "blinded_case_id": blinded_input_id,
                "task": TASK,
                "evaluator_item": item,
                "reviewer_feedback": reviewer_feedback,
            }
            case = {
                "revision_case_version": "direction-h-j-theme-revision-case-v1",
                "revision_case_id": short_id("DHJRC_", pair_id, arm),
                "paired_case_group_id": pair_id,
                "repeat_index": 1,
                "item_id": item_id,
                "assignment_id": assignment_by_item[item_id]["assignment_id"],
                "item_payload_sha256": row["item_payload_sha256"],
                "rating_record_sha256": locked["rating_sha256"],
                "timing_receipt_sha256": locked["timing_receipt_sha256"],
                "feedback_record_sha256": sha256_file(feedback_path)
                if arm == "charlie_feedback"
                else None,
                "freeze_id": freeze["freeze_id"],
                "freeze_sha256": freeze_hash,
                "feedback_arm": arm,
                "feedback_record_id": feedback["feedback_id"]
                if arm == "charlie_feedback"
                else None,
                "target_verification_item_sha256": sha256_bytes(
                    canonical_bytes(verification_item)
                ),
                "target_brief_commitment_sha256": sha256_file(TARGET_COMMITMENT_PATH),
                "model_input": model_input,
                "model_input_sha256": sha256_bytes(canonical_bytes(model_input)),
                "contains_target_truth": False,
                "contains_condition_label": False,
                "contains_feedback_author_identity": False,
                "created_at_utc": created_at,
            }
            validate_theme(
                case,
                "revision_case.schema.json",
                f"theme revision case {case['revision_case_id']}",
                theme_store(),
            )
            cases.append(case)
    for index in range(0, len(cases), 2):
        left = cases[index]["model_input"].copy()
        right = cases[index + 1]["model_input"].copy()
        left.pop("reviewer_feedback")
        right.pop("reviewer_feedback")
        if left != right:
            raise InstrumentError("paired model inputs differ outside reviewer feedback")
    exclusions = [
        {
            "item_id": row["item_id"],
            "classification": verification_by_id.get(row["item_id"], {}).get(
                "classification", "not_independently_verified"
            ),
            "included": row["item_id"] in eligible_by_id,
        }
        for row in prepared["assignments"]
    ]
    manifest = {
        "manifest_version": "direction-h-j-theme-revision-case-manifest-v1",
        "freeze_id": freeze["freeze_id"],
        "freeze_sha256": freeze_hash,
        "first_stage_lock_sha256": sha256_file(
            DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_first_stage_lock.json"
        ),
        "target_verification_sha256": sha256_file(TARGET_VERIFICATION_PATH),
        "target_briefs_sha256": commitment["target_briefs_sha256"],
        "target_brief_commitment_sha256": sha256_file(TARGET_COMMITMENT_PATH),
        "created_at_utc": created_at,
        "eligible_item_count": len(eligible),
        "allocated_case_count": len(cases),
        "arms": list(ARMS),
        "repeats_per_arm": 1,
        "pipeline_itt_denominator": len(eligible),
        "case_ids": [case["revision_case_id"] for case in cases],
        "itemwise_accounting": exclusions,
        "contains_real_source_text": False,
        "empirical_results_computed": False,
    }
    return cases, manifest


def commit(cases: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".theme_cases.", dir=OUTPUT_ROOT.parent))
    try:
        case_dir = temporary / "records"
        input_dir = temporary / "model_inputs"
        case_dir.mkdir()
        input_dir.mkdir()
        for case in cases:
            case_path = case_dir / f"{case['revision_case_id']}.json"
            input_path = input_dir / f"{case['revision_case_id']}.json"
            case_path.write_bytes(
                (json.dumps(case, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            )
            input_path.write_bytes(
                (json.dumps(case["model_input"], ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                )
            )
        (temporary / "manifest.json").write_bytes(
            (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        os.rename(temporary, OUTPUT_ROOT)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    try:
        cases, manifest = build_cases()
        commit(cases, manifest)
        print(
            json.dumps(
                {
                    "status": "prepared",
                    "eligible_items": manifest["eligible_item_count"],
                    "paired_cases": manifest["allocated_case_count"],
                    "path": str(OUTPUT_ROOT),
                },
                sort_keys=True,
            )
        )
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
