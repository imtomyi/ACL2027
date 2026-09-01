#!/usr/bin/env python3
"""Run the text-free project governance checker for Direction H's two real corpora."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHECKER = PROJECT_ROOT / "governance" / "scripts" / "check_project_readiness.py"
RECORD = PROJECT_ROOT / "governance" / "local" / "project_governance.local.json"
REGISTRY = PROJECT_ROOT / "governance" / "local" / "reviewer_registry.local.json"
PRIVACY_LOG = PROJECT_ROOT / "governance" / "local" / "privacy_review_log.local.json"
TARGETS = ("dreaddit", "agyw_focus_groups")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Direction H real-data governance without opening corpus files."
    )
    parser.add_argument(
        "--as-of",
        required=True,
        help="Explicit deterministic UTC timestamp ending in Z.",
    )
    args = parser.parse_args()
    if not args.as_of.endswith("Z"):
        print("BLOCKED: --as-of must be an explicit UTC timestamp ending in Z", file=sys.stderr)
        return 2
    for path in (CHECKER, RECORD, REGISTRY, PRIVACY_LOG):
        if path.is_symlink() or not path.is_file():
            print(f"BLOCKED: missing or unsafe governance artifact: {path}", file=sys.stderr)
            return 2
    command = [
        sys.executable,
        str(CHECKER),
        "--record",
        str(RECORD),
        "--reviewer-registry",
        str(REGISTRY),
        "--privacy-log",
        str(PRIVACY_LOG),
        "--as-of",
        args.as_of,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        print("BLOCKED: project governance checker did not validate", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)
        return 2
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("BLOCKED: governance checker returned unreadable output", file=sys.stderr)
        return 2
    if report.get("contains_real_source_text") is not False:
        print("BLOCKED: readiness report is not text-free", file=sys.stderr)
        return 2
    corpora = report.get("corpora", {})
    if any(corpus not in corpora for corpus in TARGETS):
        print("BLOCKED: readiness report lacks a target corpus", file=sys.stderr)
        return 2
    selected = {
        corpus: {
            "completed_gate_count": corpora[corpus]["completed_gate_count"],
            "required_gate_count": corpora[corpus]["required_gate_count"],
            "real_text_ready": corpora[corpus]["real_text_ready"],
            "blocking_gate_ids": [
                gate["id"] for gate in corpora[corpus]["gates"] if not gate["complete"]
            ],
        }
        for corpus in TARGETS
    }
    ready = all(value["real_text_ready"] for value in selected.values())
    print(
        json.dumps(
            {
                "status": "ready_for_restricted_next_step" if ready else "blocked_before_text_access",
                "assessment_as_of_utc": report["assessment_as_of_utc"],
                "contains_real_source_text": False,
                "fictional_or_synthetic_data_authorized": False,
                "corpora": selected,
            },
            sort_keys=True,
        )
    )
    return 0 if ready else 3


if __name__ == "__main__":
    raise SystemExit(main())
