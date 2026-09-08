#!/usr/bin/env python3
"""Validate the isolated ACE paper-reproduction inputs without calling an LLM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACE_ROOT = ROOT.parent
RUNS = ROOT / "runs"

EXPECTED_REPOSITORIES = {
    "ace": (ACE_ROOT / "upstream", "82709de050e1db6e6ef2f07bcb0393560b94992a"),
    "ace-appworld-pinned": (
        ACE_ROOT / "upstream" / "ace-appworld",
        "9f3e92155345a9159f3a8b25abc334eeca05b545",
    ),
    "ace-appworld-latest": (
        ROOT / "sources" / "ace-appworld-latest",
        "928e86877d34cd10eaba159606386f93a1765090",
    ),
    "stream-bench": (
        ROOT / "sources" / "stream-bench",
        "cf72f26f033cfa35ad209f087df8d8b1a1b4cbae",
    ),
    "gepa-appworld": (
        ROOT / "sources" / "gepa-appworld",
        "c9532248b2810eee17bb24d6b9779b897570ca48",
    ),
    "ace-project-page": (
        ROOT / "sources" / "project-page",
        "743d2626165ee71ae26c40c2f539cba68f606ebe",
    ),
}

FINANCE_SPLITS = {
    "finer_train": ("finer_train_batched_1000_samples.jsonl", 1000),
    "finer_validation": ("finer_val_batched_500_samples.jsonl", 500),
    "finer_test": ("finer_test_subset_006_seed42.jsonl", 441),
    "formula_train": ("formula_train_subset_500.jsonl", 500),
    "formula_validation": ("formula_val_subset_300.jsonl", 300),
    "formula_test": ("formula_test.jsonl", 200),
}


def git_head(path: Path) -> str | None:
    if not path.exists():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def nonempty_line_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return sum(bool(line.strip()) for line in handle)


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-api",
        action="store_true",
        help="fail unless the exact-paper SambaNova credential is present",
    )
    args = parser.parse_args()

    repository_checks = {}
    for name, (path, expected) in EXPECTED_REPOSITORIES.items():
        actual = git_head(path)
        repository_checks[name] = {
            "path": str(path),
            "expected_commit": expected,
            "actual_commit": actual,
            "ok": actual == expected,
        }

    finance_dir = ACE_ROOT / "upstream" / "eval" / "finance" / "data"
    finance_checks = {}
    for name, (filename, expected_count) in FINANCE_SPLITS.items():
        path = finance_dir / filename
        actual_count = nonempty_line_count(path)
        finance_checks[name] = {
            "path": str(path),
            "expected_records": expected_count,
            "actual_records": actual_count,
            "ok": actual_count == expected_count,
        }

    appworld = ROOT / "sources" / "ace-appworld-latest"
    appworld_splits = {}
    for split in ("train", "dev", "test_normal", "test_challenge"):
        path = appworld / "data" / "datasets" / f"{split}.txt"
        count = nonempty_line_count(path)
        appworld_splits[split] = {
            "path": str(path),
            "records": count,
            "ok": count is not None and count > 0,
        }

    playbook_dir = appworld / "experiments" / "playbooks"
    playbooks = {}
    for filename in (
        "appworld_initial_playbook.txt",
        "appworld_offline_trained_no_gt_playbook.txt",
        "appworld_offline_trained_with_gt_playbook.txt",
        "appworld_online_trained_playbook.txt",
    ):
        path = playbook_dir / filename
        playbooks[filename] = {
            "path": str(path),
            "bytes": path.stat().st_size if path.is_file() else None,
            "exists": path.is_file(),
        }

    paper_path = ROOT / "paper" / "ace_arxiv_2510.04618.pdf"
    expected_paper_sha = (
        "51050ced82df75c143b151262d5af8763916968ca50374bd8ff778f40552b0ad"
    )
    actual_paper_sha = sha256(paper_path)

    environment_source = appworld / "src" / "appworld" / "environment.py"
    patch_present = (
        environment_source.is_file()
        and "test_tracker, _ = appworld.evaluator.evaluate_task(" in environment_source.read_text(
            encoding="utf-8"
        )
    )
    api = {
        name: bool(os.environ.get(name))
        for name in ("SAMBANOVA_API_KEY", "TOGETHER_API_KEY", "OPENAI_API_KEY")
    }

    structural_ok = all(item["ok"] for item in repository_checks.values())
    structural_ok &= all(item["ok"] for item in finance_checks.values())
    structural_ok &= all(item["ok"] for item in appworld_splits.values())
    structural_ok &= actual_paper_sha == expected_paper_sha
    structural_ok &= (ROOT / ".hf").is_dir()
    structural_ok &= patch_present

    report = {
        "scope": str(ACE_ROOT),
        "structural_ok": structural_ok,
        "exact_deepseek_execution_ready": api["SAMBANOVA_API_KEY"],
        "paper": {
            "path": str(paper_path),
            "expected_sha256": expected_paper_sha,
            "actual_sha256": actual_paper_sha,
            "ok": actual_paper_sha == expected_paper_sha,
        },
        "repositories": repository_checks,
        "finance_splits": finance_checks,
        "appworld_splits": appworld_splits,
        "released_appworld_playbooks": playbooks,
        "appworld_evaluate_patch_present": patch_present,
        "embedding_cache_present": (ROOT / ".hf").is_dir(),
        "api_keys_present": api,
    }

    RUNS.mkdir(parents=True, exist_ok=True)
    output_path = RUNS / "preflight.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {output_path}")

    if not structural_ok:
        return 1
    if args.require_api and not api["SAMBANOVA_API_KEY"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
