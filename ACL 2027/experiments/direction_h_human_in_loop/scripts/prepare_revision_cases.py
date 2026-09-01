#!/usr/bin/env python3
"""Create paired revision cases after Charlie's lock and debrief validate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    raise SystemExit("No local Python runtime with jsonschema is available; no cases were written.")

from format_feedback import project_feedback
from prepare_repair_panel import (
    ALLOCATION_VERSION,
    FROZEN_ARTIFACT_ALLOWLIST,
    PackagingError,
    load_brief_commitment,
    load_target_briefs,
    verify_construction,
)


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
COORDINATOR_ROOT = DIRECTION_ROOT / "coordinator_only"
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
FREEZE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_freeze_manifest.schema.json"
CASE_SCHEMA = DIRECTION_ROOT / "schemas" / "revision_case.schema.json"
ITEM_SCHEMA = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
FEEDBACK_SCHEMA = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
DEBRIEF_SCHEMA = DIRECTION_ROOT / "schemas" / "blinding_debrief.schema.json"
OUTPUT_SCHEMA = BASELINE_ROOT / "schemas" / "qualitative_output.schema.json"
CHARLIE_RATER_ID = "charlie_dev_researcher_01"
LOCK_KEYS = {
    "review_lock_version",
    "study_id",
    "rater_id",
    "locked_at_utc",
    "task_count",
    "manifest_sha256",
    "condition_commitment_sha256",
    "records",
    "truth_opened_by_this_step",
    "ratings_or_feedback_modified_by_this_step",
    "next_step",
}
LOCK_RECORD_KEYS = {
    "task_id",
    "rating_file",
    "rating_sha256",
    "feedback_file",
    "feedback_sha256",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_regular_file_below(path: Path, root: Path, label: str) -> Path:
    """Resolve one non-symlink file within an exact reviewer-response root."""

    pilot_resolved = PILOT_ROOT.resolve()
    try:
        root.resolve().relative_to(pilot_resolved)
    except ValueError as exc:
        raise SystemExit(f"{label} root escapes the synthetic pilot: {root}") from exc
    cursor = root
    while cursor != PILOT_ROOT:
        if cursor.is_symlink():
            raise SystemExit(f"{label} root path may not contain a symlink: {cursor}")
        if cursor.parent == cursor:
            raise SystemExit(f"{label} root is not below the synthetic pilot: {root}")
        cursor = cursor.parent
    if PILOT_ROOT.is_symlink():
        raise SystemExit(f"synthetic pilot root may not be a symlink: {PILOT_ROOT}")
    if path.is_symlink():
        raise SystemExit(f"{label} may not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise SystemExit(f"{label} escapes its allowed root: {path}") from exc
    if not resolved.is_file():
        raise SystemExit(f"{label} is missing or not a regular file: {path}")
    return resolved


def has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "__REQUIRED" in value or value.startswith("FILL_") or value == "TBD"
    if isinstance(value, dict):
        return any(has_placeholder(nested) for nested in value.values())
    if isinstance(value, list):
        return any(has_placeholder(nested) for nested in value)
    return False


def schema_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in (ITEM_SCHEMA, FEEDBACK_SCHEMA, DEBRIEF_SCHEMA, OUTPUT_SCHEMA, CASE_SCHEMA):
        schema = load_json(path)
        if schema.get("$id"):
            store[schema["$id"]] = schema
    return store


def validate(instance: Any, schema_path: Path, label: str) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=schema_store()),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise SystemExit(f"{label} fails {schema_path.name}: {details}")


def verify_lock(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest_path = require_regular_file_below(
        PILOT_ROOT / "manifest.json", PILOT_ROOT, "pilot manifest"
    )
    commitment_path = require_regular_file_below(
        PILOT_ROOT / "condition_commitment.json", PILOT_ROOT, "condition commitment"
    )
    lock_path = require_regular_file_below(
        PILOT_ROOT / "review_lock.json", PILOT_ROOT, "review lock"
    )
    lock = load_json(lock_path)
    tasks = manifest.get("tasks")
    expected_task_ids = (
        [row.get("task_id") for row in tasks]
        if isinstance(tasks, list) and all(isinstance(row, dict) for row in tasks)
        else []
    )
    records = lock.get("records") if isinstance(lock, dict) else None
    if (
        not isinstance(lock, dict)
        or set(lock) != LOCK_KEYS
        or lock.get("review_lock_version") != "direction-h-review-lock-v1"
        or lock.get("study_id") != manifest.get("study_id")
        or manifest.get("intended_rater_id") != CHARLIE_RATER_ID
        or lock.get("rater_id") != CHARLIE_RATER_ID
        or len(expected_task_ids) != 4
        or len(set(expected_task_ids)) != 4
        or lock.get("task_count") != 4
        or lock.get("manifest_sha256") != sha256_file(manifest_path)
        or lock.get("condition_commitment_sha256") != sha256_file(commitment_path)
        or lock.get("truth_opened_by_this_step") is not False
        or lock.get("ratings_or_feedback_modified_by_this_step") is not False
        or not isinstance(records, list)
        or len(records) != 4
        or any(not isinstance(row, dict) or set(row) != LOCK_RECORD_KEYS for row in records)
        or [row.get("task_id") for row in records] != expected_task_ids
    ):
        raise SystemExit(
            "review lock is incomplete, altered, or inconsistent with the four-task pilot"
        )
    try:
        locked_at = datetime.fromisoformat(lock["locked_at_utc"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SystemExit("review lock locked_at_utc is not an ISO-8601 date-time") from exc
    if locked_at.tzinfo is None:
        raise SystemExit("review lock locked_at_utc must include a UTC offset")

    rating_root = PILOT_ROOT / "responses" / "ratings"
    feedback_root = PILOT_ROOT / "responses" / "feedback"
    observed_rating_files = {path.name for path in rating_root.glob("*.json")}
    observed_feedback_files = {path.name for path in feedback_root.glob("*.json")}
    expected_files = {f"{task_id}.json" for task_id in expected_task_ids}
    if observed_rating_files != expected_files or observed_feedback_files != expected_files:
        raise SystemExit("review response directories do not contain exactly the four locked tasks")

    for record in records:
        task_id = record["task_id"]
        if (
            not isinstance(record["rating_file"], str)
            or not isinstance(record["feedback_file"], str)
            or not isinstance(record["rating_sha256"], str)
            or not isinstance(record["feedback_sha256"], str)
            or len(record["rating_sha256"]) != 64
            or len(record["feedback_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in record["rating_sha256"])
            or any(character not in "0123456789abcdef" for character in record["feedback_sha256"])
        ):
            raise SystemExit(f"locked response path/hash fields are invalid for {task_id}")
        expected_rating_file = Path("responses") / "ratings" / f"{task_id}.json"
        expected_feedback_file = Path("responses") / "feedback" / f"{task_id}.json"
        if Path(record["rating_file"]) != expected_rating_file:
            raise SystemExit(f"unexpected locked rating path for {task_id}")
        if Path(record["feedback_file"]) != expected_feedback_file:
            raise SystemExit(f"unexpected locked feedback path for {task_id}")
        rating_path = require_regular_file_below(
            PILOT_ROOT / expected_rating_file, rating_root, f"locked rating {task_id}"
        )
        feedback_path = require_regular_file_below(
            PILOT_ROOT / expected_feedback_file,
            feedback_root,
            f"locked feedback {task_id}",
        )
        if record["rating_sha256"] != sha256_file(rating_path):
            raise SystemExit(f"rating changed after lock: {task_id}")
        if record["feedback_sha256"] != sha256_file(feedback_path):
            raise SystemExit(f"feedback changed after lock: {task_id}")
    return lock


def verify_blinding_debrief(manifest: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
    """Require the official post-lock masking debrief before coordinator truth opens."""

    debrief_path = require_regular_file_below(
        PILOT_ROOT / "responses" / "blinding_debrief.json",
        PILOT_ROOT / "responses",
        "post-lock blinding debrief",
    )
    debrief = load_json(debrief_path)
    validate(debrief, DEBRIEF_SCHEMA, "post-lock blinding debrief")
    if (
        debrief.get("debrief_version") != "direction-h-blinding-debrief-v1"
        or debrief.get("study_id") != manifest.get("study_id")
        or debrief.get("rater_id") != CHARLIE_RATER_ID
        or debrief.get("locked_ratings_modified") is not False
        or debrief.get("review_masking_classification") != "condition_masked"
    ):
        raise SystemExit("post-lock blinding debrief identity or official masking status differs")
    try:
        locked_at = datetime.fromisoformat(lock["locked_at_utc"].replace("Z", "+00:00"))
        completed_at = datetime.fromisoformat(
            debrief["completed_at_utc"].replace("Z", "+00:00")
        )
    except (AttributeError, ValueError) as exc:
        raise SystemExit("review lock/debrief chronology is not valid ISO-8601") from exc
    if locked_at.tzinfo is None or completed_at.tzinfo is None:
        raise SystemExit("review lock/debrief chronology must include UTC offsets")
    if completed_at <= locked_at:
        raise SystemExit("blinding debrief must be completed after the review lock")
    return debrief


def verify_public_pilot_items(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Revalidate every reviewer-safe synthetic item before coordinator access."""

    if (
        manifest.get("data_scope") != "synthetic_only"
        or manifest.get("contains_real_source_text") is not False
    ):
        raise SystemExit("public pilot manifest is not explicitly synthetic-only")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or manifest.get("task_count") != 4 or len(tasks) != 4:
        raise SystemExit("public pilot manifest does not contain exactly four tasks")
    items: dict[str, dict[str, Any]] = {}
    items_root = PILOT_ROOT / "items"
    for task in tasks:
        if not isinstance(task, dict):
            raise SystemExit("public pilot task inventory contains a non-object row")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task_id in items:
            raise SystemExit("public pilot task_id is missing or duplicated")
        expected_relative = Path("items") / f"{task_id}.json"
        item_file = task.get("item_file")
        if not isinstance(item_file, str) or Path(item_file) != expected_relative:
            raise SystemExit(f"public pilot item path is not fixed for {task_id}")
        item_path = require_regular_file_below(
            PILOT_ROOT / expected_relative, items_root, f"public pilot item {task_id}"
        )
        for hash_key in ("sha256", "evidence_packet_sha256", "candidate_output_sha256"):
            value = task.get(hash_key)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise SystemExit(f"public pilot {hash_key} is invalid for {task_id}")
        if task["sha256"] != sha256_file(item_path):
            raise SystemExit(f"public pilot item file hash drifted for {task_id}")
        item = load_json(item_path)
        validate(item, ITEM_SCHEMA, f"public pilot item {task_id}")
        validate(item["candidate_output"], OUTPUT_SCHEMA, f"candidate output {task_id}")
        if item.get("study_id") != manifest.get("study_id"):
            raise SystemExit(f"public pilot item study_id drifted for {task_id}")
        for key in (
            "task_id",
            "display_order",
            "packet_id",
            "corpus_id",
            "evaluation_role",
            "output_id",
        ):
            if item.get(key) != task.get(key):
                raise SystemExit(f"public manifest/item {key} mismatch for {task_id}")
        packet = item["evidence_packet"]
        output = item["candidate_output"]
        if task["evidence_packet_sha256"] != sha256_bytes(canonical_bytes(packet)):
            raise SystemExit(f"canonical evidence-packet hash drifted for {task_id}")
        if task["candidate_output_sha256"] != sha256_bytes(canonical_bytes(output)):
            raise SystemExit(f"canonical candidate-output hash drifted for {task_id}")
        if (
            item.get("data_classification") != "synthetic_cc0"
            or packet.get("status") != "synthetic_proxy_not_corpus_result"
            or not item["packet_id"].startswith("syn_")
            or not item["corpus_id"].startswith("synthetic_")
        ):
            raise SystemExit(f"public pilot item is outside the synthetic-only lane: {task_id}")
        if packet.get("packet_id") != item["packet_id"]:
            raise SystemExit(f"evidence packet identity drifted for {task_id}")
        if output.get("packet_id") != item["packet_id"]:
            raise SystemExit(f"candidate output packet identity drifted for {task_id}")
        if output.get("research_question") != packet.get("research_question"):
            raise SystemExit(f"candidate output research question drifted for {task_id}")
        items[task_id] = item
    return items


def verify_frozen_artifacts(freeze: dict[str, Any]) -> None:
    if freeze.get("status") != "frozen":
        raise SystemExit("revision manifest status must be frozen")
    if freeze.get("freeze_scope") != "synthetic_pilot":
        raise SystemExit("this case builder accepts only a synthetic_pilot freeze")
    if has_placeholder(freeze):
        raise SystemExit("revision manifest still contains a required placeholder")
    validate(freeze, FREEZE_SCHEMA, "revision freeze")
    for key, (expected_version, expected_path) in FROZEN_ARTIFACT_ALLOWLIST.items():
        artifact = freeze[key]
        if artifact["version"] != expected_version or artifact["path"] != expected_path:
            raise SystemExit(f"frozen artifact path/version is not allowlisted: {key}")
        path = PROJECT_ROOT / artifact["path"]
        if not path.is_file() or artifact["sha256"] != sha256_file(path):
            raise SystemExit(f"frozen artifact is missing or hash-drifted: {key}")
    if freeze["data_governance"]["contains_protected_text"] is not False:
        raise SystemExit("synthetic revision freeze must contain no protected text")


def write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing file: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--freeze",
        type=Path,
        default=PILOT_ROOT / "revision_freeze.json",
        help="Completed frozen manifest; templates are rejected.",
    )
    parser.add_argument(
        "--construction-verification",
        type=Path,
        default=COORDINATOR_ROOT / "construction_verification.json",
        help="Completed independent itemwise construction verification.",
    )
    parser.add_argument(
        "--target-briefs",
        type=Path,
        default=COORDINATOR_ROOT / "target_assessment_briefs.json",
        help="Completed arm-blind target-assessment briefs.",
    )
    parser.add_argument(
        "--target-briefs-commitment",
        type=Path,
        default=COORDINATOR_ROOT / "target_assessment_briefs.commitment.json",
        help="Immutable commitment to the exact completed briefs.",
    )
    args = parser.parse_args()
    manifest_path = require_regular_file_below(
        PILOT_ROOT / "manifest.json", PILOT_ROOT, "pilot manifest"
    )
    manifest = load_json(manifest_path)
    if manifest.get("contains_real_source_text") is not False:
        raise SystemExit("public pilot manifest is not synthetic-only")
    review_lock = verify_lock(manifest)
    verify_blinding_debrief(manifest, review_lock)
    public_items = verify_public_pilot_items(manifest)
    if not args.freeze.is_file():
        raise SystemExit(f"frozen revision manifest is missing: {args.freeze}")
    freeze = load_json(args.freeze)
    verify_frozen_artifacts(freeze)
    if freeze["study_id"] != manifest["study_id"]:
        raise SystemExit("freeze and pilot study_id differ")
    try:
        verification, _, target_tasks, excluded_items = verify_construction(
            args.construction_verification, manifest
        )
        _, briefs = load_target_briefs(
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
    except PackagingError as exc:
        raise SystemExit(f"revision case preparation blocked: {exc}") from exc

    repeats = int(freeze["repeat_policy"]["repeats_per_arm"])
    arms = list(freeze["arm_policy"]["arms"])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if datetime.fromisoformat(now.replace("Z", "+00:00")) <= datetime.fromisoformat(
        brief_commitment["committed_at_utc"].replace("Z", "+00:00")
    ):
        raise SystemExit("revision cases must be created after the target briefs are committed")
    allocation_rows: list[dict[str, Any]] = []
    eligible_manifest_tasks = [
        task for task in manifest["tasks"] if task["task_id"] in target_tasks
    ]
    for task in eligible_manifest_tasks:
        for repeat_index in range(1, repeats + 1):
            for arm in arms:
                digest = hashlib.sha256(
                    f"direction-h-allocation-v2|{freeze['freeze_id']}|{task['task_id']}|{repeat_index}|{arm}".encode()
                ).hexdigest()
                pair_digest = hashlib.sha256(
                    f"direction-h-pair-v1|{freeze['freeze_id']}|{task['task_id']}|{repeat_index}".encode()
                ).hexdigest()
                allocation_rows.append(
                    {
                        "execution_sort": digest,
                        "revision_case_id": f"RVC-{digest[:12].upper()}",
                        "blinded_revision_id": f"RBI-{digest[12:24].upper()}",
                        "model_blinded_case_id": f"RMI-{pair_digest[12:24].upper()}",
                        "paired_case_group_id": f"RPG-{pair_digest[:12].upper()}",
                        "task_id": task["task_id"],
                        "repeat_index": repeat_index,
                        "feedback_arm": arm,
                    }
                )
    allocation_rows.sort(key=lambda row: row["execution_sort"])
    allocation = {
        "allocation_version": ALLOCATION_VERSION,
        "study_id": manifest["study_id"],
        "freeze_id": freeze["freeze_id"],
        "created_at_utc": now,
        "execution_order_balanced_by": "sha256 of frozen case identity",
        "eligibility_rule": (
            "committed controlled_defect AND item disposition verified_for_detection"
        ),
        "construction_overall_disposition": verification["overall_disposition"],
        "construction_verification_file_sha256": sha256_file(
            args.construction_verification
        ),
        "target_briefs_file_sha256": sha256_file(args.target_briefs),
        "target_briefs_commitment_file_sha256": sha256_file(
            args.target_briefs_commitment
        ),
        "target_briefs_committed_at_utc": brief_commitment["committed_at_utc"],
        "eligible_target_task_ids": sorted(target_tasks),
        "excluded_items": excluded_items,
        "cases": allocation_rows,
    }
    allocation_hash = sha256_bytes(canonical_bytes(allocation))
    allocation_path = COORDINATOR_ROOT / "revision_allocation.json"
    if allocation_path.exists():
        raise SystemExit("coordinator revision allocation already exists; refusing to overwrite")

    case_dir = COORDINATOR_ROOT / "revision_cases"
    input_dir = PILOT_ROOT / "revision_model_inputs"
    if case_dir.exists() or input_dir.exists():
        raise SystemExit("revision case/input directory already exists; refusing to overwrite")

    built_cases: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []
    for row in allocation_rows:
        item = public_items[row["task_id"]]
        feedback_record = load_json(
            PILOT_ROOT / "responses" / "feedback" / f"{row['task_id']}.json"
        )
        if row["feedback_arm"] == "no_feedback":
            projected_feedback = project_feedback(None)
            feedback_record_id = None
        elif row["feedback_arm"] == "charlie_feedback":
            projected_feedback = project_feedback(feedback_record)
            feedback_record_id = feedback_record["feedback_id"]
        else:
            raise SystemExit(f"unsupported pilot arm: {row['feedback_arm']}")
        model_input = {
            "input_version": "direction-h-revision-input-v1",
            "blinded_case_id": row["model_blinded_case_id"],
            "analytic_contract_version": "qc-analytic-contract-v1",
            "evidence_packet": item["evidence_packet"],
            "original_output": item["candidate_output"],
            "reviewer_feedback": projected_feedback,
        }
        serialized_input = canonical_bytes(model_input).decode("utf-8").lower()
        if "charlie" in serialized_input or '"rater_id"' in serialized_input:
            raise SystemExit(f"rater identity leaked into model input for {row['task_id']}")
        case = {
            "revision_case_version": "direction-h-revision-case-v1",
            "revision_case_id": row["revision_case_id"],
            "paired_case_group_id": row["paired_case_group_id"],
            "repeat_index": row["repeat_index"],
            "task_id": row["task_id"],
            "packet_id": item["packet_id"],
            "output_id": item["output_id"],
            "freeze_id": freeze["freeze_id"],
            "feedback_arm": row["feedback_arm"],
            "feedback_record_id": feedback_record_id,
            "model_input": model_input,
            "model_input_sha256": sha256_bytes(canonical_bytes(model_input)),
            "allocation_record_sha256": allocation_hash,
            "contains_target_truth": False,
            "contains_rater_identity": False,
            "created_at_utc": now,
        }
        validate(case, CASE_SCHEMA, row["revision_case_id"])
        built_cases.append(
            (
                case_dir / f"{row['revision_case_id']}.json",
                case,
                input_dir / f"{row['revision_case_id']}.json",
                model_input,
            )
        )

    paired_inputs: dict[str, list[dict[str, Any]]] = {}
    for _, case, _, model_input in built_cases:
        paired_inputs.setdefault(case["paired_case_group_id"], []).append(model_input)
    for pair_id, model_inputs in paired_inputs.items():
        if len(model_inputs) != len(arms):
            raise SystemExit(f"paired revision group {pair_id} does not cover every frozen arm")
        projections = []
        for model_input in model_inputs:
            projection = dict(model_input)
            projection.pop("reviewer_feedback")
            projections.append(projection)
        if any(projection != projections[0] for projection in projections[1:]):
            raise SystemExit(
                f"paired model inputs differ outside reviewer_feedback for {pair_id}"
            )

    write_json_new(allocation_path, allocation)
    for case_path, case, input_path, model_input in built_cases:
        write_json_new(case_path, case)
        write_json_new(input_path, model_input)
    print(
        json.dumps(
            {
                "status": "revision_cases_ready",
                "paired_items": len(eligible_manifest_tasks),
                "excluded_item_count": len(excluded_items),
                "repeats_per_arm": repeats,
                "case_count": len(built_cases),
                "contains_target_truth": False,
                "model_inputs_contain_arm_labels": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
