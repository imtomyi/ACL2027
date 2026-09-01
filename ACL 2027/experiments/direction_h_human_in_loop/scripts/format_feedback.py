#!/usr/bin/env python3
"""Frozen identity-free projection for Direction H revision feedback."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


FORMATTER_VERSION = "direction-h-feedback-formatter-v1"
FIELDS_IN_ORDER = ["feedback_summary", "findings", "preserve", "uncertainties"]
FORBIDDEN_KEYS = {
    "rating_key",
    "rater_id",
    "evaluator_group",
    "confidence",
    "review_seconds",
    "feedback_arm",
    "condition",
    "target_defect",
    "target_status",
    "model_id",
    "blind_id",
}


def walk_keys(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def project_feedback(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return only the frozen model-facing feedback object, or null for control."""
    if record is None:
        return None
    if record.get("feedback_version") != "direction-h-feedback-v1":
        raise ValueError("unsupported feedback_version")
    source = record.get("model_feedback")
    if not isinstance(source, dict) or set(source) != set(FIELDS_IN_ORDER):
        raise ValueError("model_feedback fields do not match the frozen formatter")
    projected: OrderedDict[str, Any] = OrderedDict()
    for field in FIELDS_IN_ORDER:
        projected[field] = source[field]
    leaked = FORBIDDEN_KEYS & set(walk_keys(projected))
    if leaked:
        raise ValueError("forbidden key(s) in model-facing feedback: " + ", ".join(sorted(leaked)))
    return dict(projected)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--feedback", type=Path, help="Full direction-h-feedback-v1 JSON record")
    group.add_argument("--no-feedback", action="store_true", help="Emit the no-feedback null payload")
    args = parser.parse_args()
    record = None if args.no_feedback else json.loads(args.feedback.read_text(encoding="utf-8"))
    print(json.dumps(project_feedback(record), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

