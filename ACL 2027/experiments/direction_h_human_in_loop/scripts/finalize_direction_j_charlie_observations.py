#!/usr/bin/env python3
"""Create exact Direction J human observation envelopes only after review lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from serve_direction_j_browser import (
    ACTIVATION_PATH,
    ACTOR_REGISTRY_PATH,
    DIRECTION_ROOT,
    J_ASSIGNMENT_PATH,
    J_RATING_SCHEMA_PATH,
    J_RUN_MANIFEST,
    J_RUN_ROOT,
    MANIFEST_PATH,
    PROJECT_ROOT,
    TIMING_SCHEMA_PATH,
    InstrumentError,
    canonical_bytes,
    load_json,
    parse_utc,
    schema_store,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate,
    validate_activation,
    validate_prepared,
)


LOCK_PATH = DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_first_stage_lock.json"
LOCK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_first_stage_lock.schema.json"
J_OBSERVATION_SCHEMA_PATH = (
    PROJECT_ROOT / "experiments" / "direction_j_llm_as_rater" / "schemas" / "paired_observation.schema.json"
)
J_PRIVATE_KEY_PATH = J_RUN_ROOT / "private" / "item_key.jsonl"
DEFAULT_OUTPUT_DIR = DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_observations"


def safe_direction_path(relative: str) -> Path:
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


def verify_lock(prepared: dict[str, Any]) -> dict[str, Any]:
    store = schema_store()
    lock = load_json(LOCK_PATH, "browser first-stage lock")
    validate(lock, LOCK_SCHEMA_PATH, "browser first-stage lock", store)
    if lock["browser_manifest_sha256"] != sha256_file(MANIFEST_PATH):
        raise InstrumentError("first-stage lock browser manifest hash drifted")
    if lock["activation_record_sha256"] != sha256_file(ACTIVATION_PATH):
        raise InstrumentError("first-stage lock activation hash drifted")
    if lock["charlie_assignment_sha256"] != sha256_file(J_ASSIGNMENT_PATH):
        raise InstrumentError("first-stage lock assignment hash drifted")
    if sha256_bytes(canonical_bytes(lock["records"])) != lock["records_sha256"]:
        raise InstrumentError("first-stage lock records hash drifted")
    if [row["sequence"] for row in lock["records"]] != list(range(1, 25)):
        raise InstrumentError("first-stage lock order is not the exact Charlie sequence")
    assignments = {int(row["sequence"]): row for row in prepared["assignments"]}
    for record in lock["records"]:
        assignment = assignments[record["sequence"]]
        for field in ("assignment_id", "item_id", "packet_id", "output_id", "item_payload_sha256", "semantic_input_sha256"):
            expected: Any = assignment[field]
            if record[field] != expected:
                raise InstrumentError(f"first-stage lock/assignment {field} mismatch")
        for path_field, hash_field in (
            ("rating_path", "rating_sha256"),
            ("timing_receipt_path", "timing_receipt_sha256"),
            ("feedback_path", "feedback_sha256"),
        ):
            path = safe_direction_path(record[path_field])
            if sha256_file(path) != record[hash_field]:
                raise InstrumentError(f"first-stage locked file hash drifted: {path_field}")
    return lock


def load_private_key_after_lock(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    # The ordering of this function call is intentional: no private truth or
    # model identity is opened until the complete first-stage lock validates.
    run_manifest = load_json(J_RUN_MANIFEST, "Direction J run manifest")
    if run_manifest.get("private_key_path") != "private/item_key.jsonl":
        raise InstrumentError("Direction J private-key path drifted")
    if sha256_file(J_PRIVATE_KEY_PATH) != run_manifest.get("private_key_sha256"):
        raise InstrumentError("Direction J private-key hash drifted")
    rows: dict[str, dict[str, Any]] = {}
    for line in J_PRIVATE_KEY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or item_id in rows:
            raise InstrumentError("Direction J private item key contains an invalid item ID")
        rows[item_id] = row
    if len(rows) != 24:
        raise InstrumentError("Direction J private item key must contain exactly 24 rows")
    if set(rows) != {entry["item_id"] for entry in lock["records"]}:
        raise InstrumentError("private item key does not exactly cover the first-stage lock")
    return rows


def build_observations(prepared: dict[str, Any], lock: dict[str, Any]) -> list[dict[str, Any]]:
    private_rows = load_private_key_after_lock(lock)
    store = schema_store()
    # Add the exact Direction J observation schema and its shared-rating ref.
    observation_schema = load_json(J_OBSERVATION_SCHEMA_PATH, "Direction J observation schema")
    store[observation_schema["$id"]] = observation_schema
    finalized_at = utc_now()
    observations: list[dict[str, Any]] = []
    for entry in lock["records"]:
        rating = load_json(safe_direction_path(entry["rating_path"]), "locked shared rating")
        timing = load_json(safe_direction_path(entry["timing_receipt_path"]), "locked timing receipt")
        validate(rating, J_RATING_SCHEMA_PATH, "locked shared rating", store)
        validate(timing, TIMING_SCHEMA_PATH, "locked timing receipt", store)
        private = private_rows[entry["item_id"]]
        observation_id = "DHJO_" + hashlib.sha256(
            (
                "direction-h-direction-j-browser-observation-v1|"
                + entry["assignment_id"]
                + "|"
                + entry["rating_sha256"]
            ).encode("utf-8")
        ).hexdigest()[:20]
        observation = {
            "observation_schema_version": "direction-j-paired-observation-v1",
            "observation_id": observation_id,
            "study_id": "direction-j-v1",
            "evaluation_role": "synthetic_qualification",
            "item_id": entry["item_id"],
            "packet_id": entry["packet_id"],
            "output_id": entry["output_id"],
            "corpus_id": timing["corpus_id"],
            "candidate_generation_run_id": private["candidate_generation_run_id"],
            "candidate_generation_repetition": private["candidate_generation_repetition"],
            "actor_id": "charlie",
            "actor_kind": "human",
            "rating_repetition": 1,
            "item_payload_sha256": entry["item_payload_sha256"],
            "interface_version": timing["interface_version"],
            "shared_rater_guide_version": timing["shared_rater_guide_version"],
            "shared_rater_guide_sha256": timing["shared_rater_guide_sha256"],
            "semantic_input_sha256": entry["semantic_input_sha256"],
            "prompt_or_instrument_version": timing["prompt_or_instrument_version"],
            "prompt_or_instrument_sha256": timing["prompt_or_instrument_sha256"],
            "started_at_utc": timing["started_at_utc"],
            "completed_at_utc": timing["rating_submitted_at_utc"],
            "review_seconds": timing["review_seconds"],
            "observation_status": "valid",
            "rating": rating,
            "blinding": {
                "blind_id": entry["assignment_id"],
                "candidate_identity_hidden": True,
                "condition_hidden": True,
                "other_ratings_hidden": True,
                "unblinded_at_utc": finalized_at,
            },
            "execution": {
                "retry_count": 0,
                "attempts": [],
                "token_usage_available": False,
                "input_tokens": None,
                "output_tokens": None,
                "cached_input_tokens": None,
                "reasoning_tokens_available": False,
                "reasoning_tokens": None,
                "cost_available": False,
                "cost_amount": None,
                "cost_currency": None,
                "pricing_snapshot_id": None,
            },
        }
        validate(observation, J_OBSERVATION_SCHEMA_PATH, "Direction J human observation", store)
        observations.append(observation)
    return observations


def commit_output(output_dir: Path, observations: list[dict[str, Any]], lock: dict[str, Any]) -> None:
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists():
        raise InstrumentError("refusing to overwrite finalized Direction J observations")
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=parent))
    try:
        jsonl = b"".join(canonical_bytes(row) for row in observations)
        observations_path = temporary / "charlie_observations.jsonl"
        observations_path.write_bytes(jsonl)
        os.chmod(observations_path, 0o600)
        manifest = {
            "finalization_version": "direction-h-direction-j-browser-observation-finalization-v1",
            "created_at_utc": utc_now(),
            "visibility": "coordinator_only_after_first_stage_lock",
            "contains_real_source_text": False,
            "first_stage_lock_sha256": sha256_file(LOCK_PATH),
            "activation_record_sha256": sha256_file(ACTIVATION_PATH),
            "actor_registry_sha256": sha256_file(ACTOR_REGISTRY_PATH),
            "private_item_key_sha256": sha256_file(J_PRIVATE_KEY_PATH),
            "observation_count": len(observations),
            "observations_file": "charlie_observations.jsonl",
            "observations_sha256": sha256_bytes(jsonl),
            "ratings_or_outcomes_fabricated": False,
            "empirical_results_computed": False,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        os.chmod(manifest_path, 0o600)
        os.rename(temporary, output_dir)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize exact Direction J Charlie observation envelopes after the 24-item lock."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        output_dir = args.output_dir.resolve()
        try:
            output_dir.relative_to((DIRECTION_ROOT / "coordinator_only").resolve())
        except ValueError as exc:
            raise InstrumentError("finalized observations must stay under coordinator_only") from exc
        prepared = validate_prepared()
        validate_activation(prepared)
        lock = verify_lock(prepared)
        observations = build_observations(prepared, lock)
        commit_output(output_dir, observations, lock)
        print(json.dumps({"status": "finalized", "observations": 24, "path": str(output_dir)}))
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
