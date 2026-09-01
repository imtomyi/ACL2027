#!/usr/bin/env python3
"""Lock the complete 24-item Charlie browser queue before private unblinding."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from serve_direction_j_browser import (
    ACTIVATION_PATH,
    BROWSER_FEEDBACK_SCHEMA_PATH,
    DIRECTION_ROOT,
    J_ASSIGNMENT_PATH,
    J_RATING_SCHEMA_PATH,
    MANIFEST_PATH,
    RESPONSE_ROOT,
    TIMING_SCHEMA_PATH,
    InstrumentError,
    canonical_bytes,
    load_json,
    response_dir,
    schema_store,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate,
    validate_activation,
    validate_findings,
    validate_prepared,
    verify_timing,
)


LOCK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_first_stage_lock.schema.json"
DEFAULT_OUTPUT = DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_first_stage_lock.json"


def require_exact_directory(directory: Path, expected: set[str], label: str) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise InstrumentError(f"{label} is missing or unsafe")
    actual = {entry.name for entry in directory.iterdir()}
    if actual != expected:
        raise InstrumentError(f"{label} contains a missing or unexpected entry")
    if any(entry.is_symlink() for entry in directory.iterdir()):
        raise InstrumentError(f"{label} contains a symlink")


def build_lock(locker_id: str) -> dict[str, Any]:
    if not locker_id.strip() or locker_id.strip().casefold() in {
        "charlie", "charlie_dev_researcher_01"
    }:
        raise InstrumentError("the first-stage locker must be a non-Charlie coordinator")
    prepared = validate_prepared()
    validate_activation(prepared)
    store = schema_store()
    entries: list[dict[str, Any]] = []
    for row in prepared["assignments"]:
        directory = response_dir(row)
        require_exact_directory(
            directory,
            {"rating.json", "timing_receipt.json", "feedback_commit"},
            f"response {row['sequence']}",
        )
        feedback_dir = directory / "feedback_commit"
        require_exact_directory(feedback_dir, {"feedback.json"}, f"feedback {row['sequence']}")
        rating_path = directory / "rating.json"
        timing_path = directory / "timing_receipt.json"
        feedback_path = feedback_dir / "feedback.json"
        rating = load_json(rating_path, "locked Direction J rating")
        timing = load_json(timing_path, "locked browser timing receipt")
        feedback = load_json(feedback_path, "locked browser feedback")
        validate(rating, J_RATING_SCHEMA_PATH, "locked Direction J rating", store)
        validate(timing, TIMING_SCHEMA_PATH, "locked browser timing receipt", store)
        validate(feedback, BROWSER_FEEDBACK_SCHEMA_PATH, "locked browser feedback", store)
        verify_timing(
            {
                "started_at_utc": timing["started_at_utc"],
                "rating_submitted_at_utc": timing["rating_submitted_at_utc"],
                "timing_log": timing["timing_log"],
            }
        )
        item = prepared["items"][row["item_id"]]
        validate_findings(item, feedback, rating)
        rating_hash = sha256_bytes(canonical_bytes(rating))
        if timing["rating_record_sha256"] != rating_hash:
            raise InstrumentError(f"timing/rating hash mismatch at sequence {row['sequence']}")
        if feedback["rating_key"]["rating_record_sha256"] != rating_hash:
            raise InstrumentError(f"feedback/rating hash mismatch at sequence {row['sequence']}")
        if feedback["timing_receipt_sha256"] != sha256_file(timing_path):
            raise InstrumentError(f"feedback/timing hash mismatch at sequence {row['sequence']}")
        exact = {
            "assignment_id": row["assignment_id"],
            "sequence": int(row["sequence"]),
            "item_id": row["item_id"],
            "packet_id": row["packet_id"],
            "output_id": row["output_id"],
            "item_payload_sha256": row["item_payload_sha256"],
            "semantic_input_sha256": row["semantic_input_sha256"],
        }
        for field, expected in exact.items():
            if timing.get(field) != expected:
                raise InstrumentError(
                    f"timing/assignment {field} mismatch at sequence {row['sequence']}"
                )
        if feedback["assignment_id"] != row["assignment_id"] or feedback["item_id"] != row[
            "item_id"
        ]:
            raise InstrumentError(f"feedback assignment mismatch at sequence {row['sequence']}")
        entries.append(
            {
                "sequence": int(row["sequence"]),
                "assignment_id": row["assignment_id"],
                "item_id": row["item_id"],
                "packet_id": row["packet_id"],
                "output_id": row["output_id"],
                "item_payload_sha256": row["item_payload_sha256"],
                "semantic_input_sha256": row["semantic_input_sha256"],
                "rating_path": str(rating_path.relative_to(DIRECTION_ROOT)),
                "rating_sha256": sha256_file(rating_path),
                "timing_receipt_path": str(timing_path.relative_to(DIRECTION_ROOT)),
                "timing_receipt_sha256": sha256_file(timing_path),
                "feedback_path": str(feedback_path.relative_to(DIRECTION_ROOT)),
                "feedback_sha256": sha256_file(feedback_path),
            }
        )
    if len(entries) != 24:
        raise InstrumentError("exactly 24 complete response triplets are required")
    records_hash = sha256_bytes(canonical_bytes(entries))
    lock_id = "DHJBL_" + hashlib.sha256(
        (records_hash + "|" + sha256_file(ACTIVATION_PATH)).encode("utf-8")
    ).hexdigest()[:16]
    record = {
        "lock_version": "direction-h-direction-j-browser-first-stage-lock-v1",
        "instrument_version": "direction-h-direction-j-browser-v1",
        "bridge_id": "direction-h-direction-j-synthetic-qualification-v1",
        "lock_id": lock_id,
        "locked_at_utc": utc_now(),
        "locked_by_actor_id": locker_id.strip(),
        "locker_is_charlie": False,
        "expected_records": 24,
        "completed_records": 24,
        "write_window_closed": True,
        "ratings_mutable": False,
        "feedback_mutable": False,
        "private_map_opened": False,
        "unblinded_at_utc": None,
        "browser_manifest_sha256": sha256_file(MANIFEST_PATH),
        "activation_record_sha256": sha256_file(ACTIVATION_PATH),
        "charlie_assignment_sha256": sha256_file(J_ASSIGNMENT_PATH),
        "records": entries,
        "records_sha256": records_hash,
    }
    validate(record, LOCK_SCHEMA_PATH, "browser first-stage lock", store)
    return record


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lock all 24 exact Direction J Charlie ratings, timings, and feedback sidecars."
    )
    parser.add_argument("--locked-by", required=True, help="Non-Charlie coordinator pseudonym.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        try:
            output.relative_to((DIRECTION_ROOT / "coordinator_only").resolve())
        except ValueError as exc:
            raise InstrumentError("lock output must stay under Direction H coordinator_only") from exc
        if output.exists():
            raise InstrumentError("refusing to overwrite an existing first-stage lock")
        record = build_lock(args.locked_by)
        write_exclusive(output, record)
        print(json.dumps({"status": "locked", "records": 24, "path": str(output)}))
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
