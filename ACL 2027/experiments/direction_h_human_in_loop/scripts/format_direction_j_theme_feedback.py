#!/usr/bin/env python3
"""Emit the frozen identity-free feedback payload for one Direction J theme case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from serve_direction_j_browser import (
    BROWSER_FEEDBACK_SCHEMA_PATH,
    InstrumentError,
    load_json,
    schema_store,
    validate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a locked Direction H browser feedback record and print only its "
            "identity-free model_feedback object in frozen field order."
        )
    )
    parser.add_argument("feedback", type=Path)
    args = parser.parse_args()
    try:
        record = load_json(args.feedback.resolve(), "locked browser feedback")
        validate(
            record,
            BROWSER_FEEDBACK_SCHEMA_PATH,
            "locked browser feedback",
            schema_store(),
        )
        source = record["model_feedback"]
        projection = {
            "feedback_summary": source["feedback_summary"],
            "findings": source["findings"],
            "preserve": source["preserve"],
            "uncertainties": source["uncertainties"],
        }
        print(
            json.dumps(
                projection,
                ensure_ascii=False,
                sort_keys=False,
                separators=(",", ":"),
            )
        )
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
