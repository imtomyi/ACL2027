#!/usr/bin/env python3
"""Hash and lock a complete four-item Charlie pilot without opening truth labels."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
LOCK_PATH = PILOT_ROOT / "review_lock.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if LOCK_PATH.exists():
        raise SystemExit(f"Review lock already exists; refusing to overwrite {LOCK_PATH}")
    validation = subprocess.run(
        [sys.executable, str(DIRECTION_ROOT / "scripts" / "validate_artifacts.py"), "--reviewer-safe"],
        check=False,
        capture_output=True,
        text=True,
    )
    if validation.returncode != 0:
        print(validation.stdout, end="")
        print(validation.stderr, end="", file=sys.stderr)
        raise SystemExit("Reviewer-safe validation failed; no lock was written.")
    manifest_path = PILOT_ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = [row["task_id"] for row in manifest["tasks"]]
    ratings = PILOT_ROOT / "responses" / "ratings"
    feedback = PILOT_ROOT / "responses" / "feedback"
    missing = [
        task_id
        for task_id in expected
        if not (ratings / f"{task_id}.json").is_file()
        or not (feedback / f"{task_id}.json").is_file()
    ]
    if missing:
        raise SystemExit(
            "Pilot is incomplete; no lock was written. Missing paired records for: "
            + ", ".join(missing)
        )
    unexpected = sorted(
        ({path.stem for path in ratings.glob("*.json")} | {path.stem for path in feedback.glob("*.json")})
        - set(expected)
    )
    if unexpected:
        raise SystemExit("Unexpected response task IDs; no lock was written: " + ", ".join(unexpected))
    records = []
    for task_id in expected:
        rating_path = ratings / f"{task_id}.json"
        feedback_path = feedback / f"{task_id}.json"
        records.append(
            {
                "task_id": task_id,
                "rating_file": str(rating_path.relative_to(PILOT_ROOT)),
                "rating_sha256": sha256_file(rating_path),
                "feedback_file": str(feedback_path.relative_to(PILOT_ROOT)),
                "feedback_sha256": sha256_file(feedback_path),
            }
        )
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lock = {
        "review_lock_version": "direction-h-review-lock-v1",
        "study_id": manifest["study_id"],
        "rater_id": manifest["intended_rater_id"],
        "locked_at_utc": now,
        "task_count": len(expected),
        "manifest_sha256": sha256_file(manifest_path),
        "condition_commitment_sha256": sha256_file(PILOT_ROOT / "condition_commitment.json"),
        "records": records,
        "truth_opened_by_this_step": False,
        "ratings_or_feedback_modified_by_this_step": False,
        "next_step": (
            "Coordinator verifies the revision freeze, prepares paired no-feedback and "
            "Charlie-feedback cases, and keeps condition truth hidden from the revision model."
        ),
    }
    write_json(LOCK_PATH, lock)
    print(
        json.dumps(
            {
                "status": "locked",
                "task_count": len(expected),
                "truth_opened_by_this_step": False,
                "lock": str(LOCK_PATH),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
