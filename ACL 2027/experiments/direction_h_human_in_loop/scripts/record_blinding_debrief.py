#!/usr/bin/env python3
"""Record a post-lock blinding-integrity debrief without changing ratings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
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
    raise SystemExit("No local Python runtime with jsonschema is available; no debrief was written.")


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
OUTPUT_PATH = PILOT_ROOT / "responses" / "blinding_debrief.json"
SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "blinding_debrief.schema.json"
TASKS = ["DHQ-001", "DHQ-002", "DHQ-003", "DHQ-004"]


def yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt + " [y/n]: ").strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter y or n.")


def disclosure(prompt: str) -> dict[str, Any]:
    occurred = yes_no(prompt)
    details = input("Details: ").strip() if occurred else ""
    while occurred and not details:
        details = input("Details are required when yes: ").strip()
    return {"occurred": occurred, "details": details}


def task_ids(prompt: str) -> list[str]:
    print(prompt + " Enter comma-separated task IDs, or press Enter for none.")
    while True:
        raw = input("Task IDs: ").strip()
        if not raw:
            return []
        values = list(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))
        if all(value in TASKS for value in values):
            return values
        print("Use only: " + ", ".join(TASKS))


def main() -> int:
    if not (PILOT_ROOT / "review_lock.json").is_file():
        raise SystemExit("Review lock is missing; debrief only after all ratings are locked.")
    if OUTPUT_PATH.exists():
        raise SystemExit("Blinding debrief already exists; refusing to overwrite it.")
    access_separated = yes_no(
        "As far as you know, before and during rating was access to every coordinator/private map technically separated? This self-report does not establish the official classification."
    )
    recognized = task_ids("Did you recognize any item or remember seeing it before rating?")
    remembered = disclosure("Did you remember construction details relevant to a rating?")
    inferred = disclosure("Did you infer a model, condition, planted target, or paired twin?")
    exposures: list[dict[str, Any]] = []
    exposure_types = [
        "model_identity",
        "condition_or_target",
        "paired_twin",
        "prior_rating_or_score",
        "revision_outcome",
        "protected_text",
        "other",
    ]
    while yes_no("Was there an accidental label/data exposure to record?"):
        task = input("Affected task ID (blank if session-wide): ").strip() or None
        if task is not None and task not in TASKS:
            raise SystemExit("Unknown task ID; nothing was written.")
        print("Exposure types: " + ", ".join(exposure_types))
        exposure_type = input("Exposure type: ").strip()
        if exposure_type not in exposure_types:
            raise SystemExit("Unknown exposure type; nothing was written.")
        details = input("Details: ").strip()
        if not details:
            raise SystemExit("Exposure details are required; nothing was written.")
        exposures.append({"task_id": task, "exposure_type": exposure_type, "details": details})
    interruptions: list[dict[str, str]] = []
    while yes_no("Was a task timer materially interrupted?"):
        task = input("Affected task ID: ").strip()
        if task not in TASKS:
            raise SystemExit("Unknown task ID; nothing was written.")
        details = input("Interruption details: ").strip()
        if not details:
            raise SystemExit("Interruption details are required; nothing was written.")
        interruptions.append({"task_id": task, "details": details})
    other_notes = input("Other blinding-integrity notes (optional): ").strip()
    record = {
        "debrief_version": "direction-h-blinding-debrief-v1",
        "study_id": "direction-h-synthetic-pilot-v1",
        "rater_id": "charlie_dev_researcher_01",
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "private_map_access_separated": access_separated,
        # The v1 shared-workspace pilot has no independent access-control
        # attestation.  Charlie's answer remains exposure metadata and cannot
        # promote the official classification.
        "review_masking_classification": "condition_masked",
        "recognized_task_ids": recognized,
        "remembered_construction_details": remembered,
        "inferred_hidden_information": inferred,
        "accidental_exposures": exposures,
        "timing_interruptions": interruptions,
        "other_notes": other_notes,
        "locked_ratings_modified": False
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise SystemExit(f"Debrief failed validation; nothing was written: {details}")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if input("Save this post-lock debrief? Type SAVE: ").strip() != "SAVE":
        raise SystemExit("Nothing was written.")
    OUTPUT_PATH.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {OUTPUT_PATH.relative_to(DIRECTION_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
