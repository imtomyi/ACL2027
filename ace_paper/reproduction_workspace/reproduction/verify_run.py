#!/usr/bin/env python3
"""Verify the artifacts and core ACE loop evidence from the latest local run."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
UPSTREAM = ROOT / "upstream"
UPSTREAM_COMMIT = "82709de050e1db6e6ef2f07bcb0393560b94992a"


def main() -> int:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True
    ).strip()
    if revision != UPSTREAM_COMMIT:
        raise AssertionError(f"Unexpected upstream revision: {revision}")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=UPSTREAM, text=True
    ).strip()
    if dirty:
        raise AssertionError("The official upstream checkout was modified")

    latest_path = RESULTS_DIR / "latest_run.json"
    if not latest_path.exists():
        raise SystemExit("No latest run found. Execute reproduction/run_smoke.py first.")
    summary = json.loads(latest_path.read_text(encoding="utf-8"))
    run_dir = Path(summary["run_directory"])

    required = [
        "run_config.json",
        "final_results.json",
        "initial_test_results.json",
        "final_test_results.json",
        "pre_train_post_train_results.json",
        "final_playbook.txt",
        "best_playbook.txt",
        "bullet_usage_log.jsonl",
        "curator_operations_diff.jsonl",
        "reproduction_summary.json",
    ]
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        raise AssertionError(f"Missing run artifacts: {missing}")

    playbook = (run_dir / "final_playbook.txt").read_text(encoding="utf-8")
    bullets = re.findall(r"^\[[^\]]+\]\s+helpful=\d+\s+harmful=\d+\s+::", playbook, re.MULTILINE)
    if not bullets:
        raise AssertionError("Curator produced no structured playbook bullets")

    operation_lines = (run_dir / "curator_operations_diff.jsonl").read_text(encoding="utf-8").splitlines()
    operations = [json.loads(line) for line in operation_lines if line]
    if not any(item.get("operation_type") == "ADD" for item in operations):
        raise AssertionError("No applied ADD delta was logged")

    roles = set()
    for log_path in (run_dir / "detailed_llm_logs").glob("*.json"):
        roles.add(json.loads(log_path.read_text(encoding="utf-8")).get("role"))
    expected_roles = {"generator", "reflector", "curator"}
    if not expected_roles.issubset(roles):
        raise AssertionError(f"Missing LLM role logs: {sorted(expected_roles - roles)}")

    checks = {
        "upstream_commit": revision,
        "upstream_checkout_clean": True,
        "run_directory": str(run_dir),
        "required_artifacts": len(required),
        "structured_playbook_bullets": len(bullets),
        "logged_curator_operations": len(operations),
        "llm_roles_observed": sorted(roles),
        "initial_test_accuracy": summary["initial_test_accuracy"],
        "final_test_accuracy": summary["final_test_accuracy"],
    }
    print(json.dumps(checks, indent=2))
    print("VERIFIED: Generator -> Reflector -> Curator -> delta merge completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
