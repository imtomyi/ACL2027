#!/usr/bin/env python3
"""Reviewer-safe preflight for the exact Direction J browser instrument."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from serve_direction_j_browser import InstrumentError, validate_activation, validate_prepared


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the synthetic Direction J Charlie browser queue without displaying an item."
    )
    parser.add_argument(
        "--prepared-only",
        action="store_true",
        help="Do not require the non-Charlie activation and qualification records.",
    )
    args = parser.parse_args()
    try:
        prepared = validate_prepared()
        locked_root = (
            Path(__file__).resolve().parents[1]
            / "companion_j_bridge"
            / "browser"
            / "responses"
            / "locked"
        )
        locked_directories = (
            [entry for entry in locked_root.iterdir() if entry.is_dir()]
            if locked_root.exists()
            else []
        )
        result = {
            "status": "valid_prepared_not_activated",
            "instrument_version": "direction-h-direction-j-browser-v1",
            "synthetic_items": 24,
            "contains_real_source_text": False,
            "completed_ratings": sum(
                (directory / "rating.json").is_file()
                for directory in locked_directories
            ),
            "completed_feedback": prepared["completed_count"],
            "activation_required": True,
            "ratings_or_results_created_by_preflight": False,
        }
        if not args.prepared_only:
            validate_activation(prepared)
            result["status"] = "valid_activated"
            result["activation_required"] = False
        print(json.dumps(result, sort_keys=True))
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
