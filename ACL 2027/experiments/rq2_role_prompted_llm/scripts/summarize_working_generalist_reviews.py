#!/usr/bin/env python3
"""Create source-free summary exports for working generalist review outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_INPUT_ROOT = (
    WORKSPACE
    / "Storage"
    / "draft_review_packets"
    / "draftpkt_20260901T052834Z"
    / "reviewer_outputs"
    / "generalist"
)
DEFAULT_OUTPUT_ROOT = DEFAULT_INPUT_ROOT / "derived"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def iter_output_files(input_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(input_root.glob("*/*.json")):
        if path.parent.name == "derived":
            continue
        if path.name == "run_manifest.json":
            continue
        files.append(path)
    return files


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def normalize_rating(record: dict[str, Any]) -> dict[str, Any]:
    rating = record.get("parsed_rating")
    if not isinstance(rating, dict):
        rating = {}
    return {
        "evidential_credibility": rating.get("evidential_credibility"),
        "voice_boundary_preservation": rating.get("voice_boundary_preservation"),
        "scope_calibration": rating.get("scope_calibration"),
        "cannot_judge": as_list(rating.get("cannot_judge")),
        "confidence": rating.get("confidence"),
        "disposition": rating.get("disposition"),
        "requested_expertise": rating.get("requested_expertise"),
        "serious_error_flags": as_list(rating.get("serious_error_flags")),
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    index_rows: list[dict[str, Any]] = []
    scoring_rows: list[dict[str, Any]] = []
    status_by_model: dict[str, Counter[str]] = defaultdict(Counter)

    for path in iter_output_files(args.input_root):
        record = load_json(path)
        rating = normalize_rating(record)
        model_id = str(record.get("model_id"))
        status = str(record.get("status"))
        status_by_model[model_id][status] += 1
        validation_errors = as_list(record.get("validation_errors"))
        output_path = str(path)

        index_rows.append(
            {
                "model_id": model_id,
                "model_dir": path.parent.name,
                "corpus_id": record.get("corpus_id"),
                "packet_id": record.get("packet_id"),
                "status": status,
                "validation_errors": ";".join(str(item) for item in validation_errors),
                "disposition": rating["disposition"],
                "requested_expertise": rating["requested_expertise"],
                "confidence": rating["confidence"],
                "serious_error_flags": ";".join(
                    str(item) for item in rating["serious_error_flags"]
                ),
                "output_file": output_path,
            }
        )
        scoring_rows.append(
            {
                "record_schema_version": "working-generalist-scoring-input-v1",
                "corpus_id": record.get("corpus_id"),
                "packet_id": record.get("packet_id"),
                "output_id": record.get("output_id"),
                "role": record.get("role"),
                "model_id": model_id,
                "status": status,
                "validation_errors": validation_errors,
                "rating": rating,
                "source_output_file": output_path,
            }
        )

    args.output_root.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_root / "output_index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "model_id",
            "model_dir",
            "corpus_id",
            "packet_id",
            "status",
            "validation_errors",
            "disposition",
            "requested_expertise",
            "confidence",
            "serious_error_flags",
            "output_file",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(index_rows)

    write_jsonl(args.output_root / "scoring_inputs.jsonl", scoring_rows)
    write_json(
        args.output_root / "status_by_model.json",
        {
            "summary_schema_version": "working-generalist-status-summary-v1",
            "input_root": str(args.input_root),
            "record_count": len(index_rows),
            "models": {
                model: dict(counter)
                for model, counter in sorted(status_by_model.items(), key=lambda item: item[0])
            },
            "exports": {
                "output_index_csv": str(csv_path),
                "scoring_inputs_jsonl": str(args.output_root / "scoring_inputs.jsonl"),
            },
        },
    )
    print(f"wrote {len(index_rows)} rows to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
