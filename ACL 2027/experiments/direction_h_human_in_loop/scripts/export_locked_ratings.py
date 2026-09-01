#!/usr/bin/env python3
"""Export locked Charlie records for exact item-level companion comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
DEFAULT_RATINGS = PILOT_ROOT / "exports" / "charlie_ratings.qc-paper-metrics-v1.jsonl"
DEFAULT_FEEDBACK = PILOT_ROOT / "exports" / "charlie_feedback.direction-h-feedback-v1.jsonl"


def write_new(path: Path, lines: list[str]) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing export: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export the complete locked canonical ratings as direct JSONL objects and "
            "their linked Direction H feedback in a separate JSONL file."
        )
    )
    parser.add_argument("--ratings-output", type=Path, default=DEFAULT_RATINGS)
    parser.add_argument("--feedback-output", type=Path, default=DEFAULT_FEEDBACK)
    args = parser.parse_args()

    if not (PILOT_ROOT / "review_lock.json").is_file():
        raise SystemExit("review lock is missing; no export was written")
    validation = subprocess.run(
        [
            sys.executable,
            str(DIRECTION_ROOT / "scripts" / "validate_artifacts.py"),
            "--reviewer-safe",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if validation.returncode != 0:
        print(validation.stdout, end="")
        print(validation.stderr, end="", file=sys.stderr)
        raise SystemExit("locked records failed reviewer-safe validation; no export was written")

    manifest = json.loads((PILOT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    tasks = sorted(manifest["tasks"], key=lambda row: row["display_order"])
    rating_lines: list[str] = []
    feedback_lines: list[str] = []
    for task in tasks:
        task_id = task["task_id"]
        rating = json.loads(
            (PILOT_ROOT / "responses" / "ratings" / f"{task_id}.json").read_text(
                encoding="utf-8"
            )
        )
        feedback = json.loads(
            (PILOT_ROOT / "responses" / "feedback" / f"{task_id}.json").read_text(
                encoding="utf-8"
            )
        )
        rating_lines.append(json.dumps(rating, ensure_ascii=False, separators=(",", ":")))
        feedback_lines.append(json.dumps(feedback, ensure_ascii=False, separators=(",", ":")))

    if args.ratings_output.resolve() == args.feedback_output.resolve():
        raise SystemExit("ratings and feedback exports must use different paths")
    if args.ratings_output.exists() or args.feedback_output.exists():
        raise SystemExit("an export target already exists; no export was written")
    write_new(args.ratings_output, rating_lines)
    try:
        write_new(args.feedback_output, feedback_lines)
    except Exception:
        args.ratings_output.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "status": "exported",
                "rating_records": len(rating_lines),
                "feedback_records": len(feedback_lines),
                "rating_annotation_version": "qc-paper-metrics-v1",
                "ratings_output": str(args.ratings_output),
                "feedback_output": str(args.feedback_output),
                "truth_opened": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
