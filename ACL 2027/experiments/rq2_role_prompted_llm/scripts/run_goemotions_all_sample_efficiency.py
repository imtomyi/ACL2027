#!/usr/bin/env python3
"""Run staged GoEmotions role-review efficiency experiments.

The full usable GoEmotions train split is the sampling frame. The script builds
or reuses a full local working packet bank, then evaluates nested balanced
sample sizes so the cost/quality curve can be inspected before spending the
full run budget.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
RQ2_ROOT = SCRIPT.parents[1]
RUN_ROOT = WORKSPACE / "Storage" / "draft_review_packets" / "goemotions_train_all_working_v1"
PACKET_FILE = RUN_ROOT / "by_dataset" / "goemotions.review_packets.jsonl"
TRUTH_FILE = RUN_ROOT / "private" / "truth_map.private.jsonl"
DEFAULT_MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")
DEFAULT_ROLES = ("generalist", "qualitative_methods", "domain")
DEFAULT_STAGES = (100, 250, 500, 1000, 2000, 4000, 6000, 8000, 9540)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row is not an object")
            rows.append(value)
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def command_to_text(command: list[str]) -> str:
    return " ".join(subprocess.list2cmdline([part]) for part in command)


def run_command(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{now_utc()}] $ {command_to_text(command)}\n")
        log.flush()
        completed = subprocess.run(
            command,
            cwd=WORKSPACE,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        log.write(f"[{now_utc()}] exit_code={completed.returncode}\n")
        if completed.returncode:
            raise subprocess.CalledProcessError(completed.returncode, command)


def wait_for_pid(pid: int, poll_seconds: int) -> None:
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(poll_seconds)


def safe_model_dir(model: str) -> str:
    return model.replace(":", "_").replace(".", "_")


def ensure_full_bank(log_path: Path) -> dict[str, Any]:
    if (RUN_ROOT / "manifest.json").exists() and PACKET_FILE.exists() and TRUTH_FILE.exists():
        return load_json(RUN_ROOT / "manifest.json")
    run_command(
        [
            "python3",
            str(RQ2_ROOT / "scripts" / "build_working_multicorpus_packet_banks.py"),
            "--corpus",
            "goemotions",
            "--goemotions-all-eligible",
        ],
        log_path,
    )
    return load_json(RUN_ROOT / "manifest.json")


def balanced_packet_subset(sample_n: int) -> tuple[Path, Path]:
    packets = {str(row["packet_id"]): row for row in load_jsonl(PACKET_FILE)}
    truth_rows = load_jsonl(TRUTH_FILE)
    by_flaw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(truth_rows, key=lambda item: item["packet_id"]):
        by_flaw[str(row["known_intended_flaw_type"])].append(row)
    if sample_n % len(by_flaw):
        raise ValueError(f"sample size must divide by {len(by_flaw)} flaw types: {sample_n}")
    per_flaw = sample_n // len(by_flaw)
    selected_truth: list[dict[str, Any]] = []
    for flaw_type, rows in sorted(by_flaw.items()):
        if len(rows) < per_flaw:
            raise ValueError(f"not enough {flaw_type} packets for n={sample_n}")
        selected_truth.extend(rows[:per_flaw])
    selected_truth.sort(key=lambda row: row["packet_id"])
    subset_root = RUN_ROOT / "sample_packets" / f"balanced_n{sample_n}"
    subset_packet_file = subset_root / "by_dataset" / "goemotions.review_packets.jsonl"
    subset_truth_file = subset_root / "private" / "truth_map.private.jsonl"
    write_jsonl(subset_packet_file, [packets[str(row["packet_id"])] for row in selected_truth])
    write_jsonl(subset_truth_file, selected_truth)
    write_json(
        subset_root / "manifest.json",
        {
            "created_at_utc": now_utc(),
            "corpus_id": "goemotions",
            "full_run_root": str(RUN_ROOT),
            "packet_file": str(subset_packet_file),
            "sample_n": sample_n,
            "sample_type": "nested_balanced",
            "truth_map": str(subset_truth_file),
        },
    )
    return subset_packet_file, subset_truth_file


def output_counts(role: str, models: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in models:
        model_dir = RUN_ROOT / "reviewer_outputs" / role / safe_model_dir(model)
        counts[model] = len(list(model_dir.glob("PKT_*.json"))) if model_dir.exists() else 0
    return counts


def summarize_role(role: str, log_path: Path) -> None:
    role_root = RUN_ROOT / "reviewer_outputs" / role
    run_command(
        [
            "python3",
            str(RQ2_ROOT / "scripts" / "summarize_working_generalist_reviews.py"),
            "--input-root",
            str(role_root),
            "--output-root",
            str(role_root / "derived"),
        ],
        log_path,
    )


def score_stage(sample_n: int, stages: list[int], roles: list[str], log_path: Path) -> None:
    eligible_sizes = [str(size) for size in stages if size <= sample_n]
    output_dir = RUN_ROOT / "sample_size_efficiency" / f"staged_through_n{sample_n}"
    run_command(
        [
            "python3",
            str(RQ2_ROOT / "scripts" / "score_working_sample_size_efficiency.py"),
            "--run-root",
            str(RUN_ROOT),
            "--roles",
            *roles,
            "--balanced-sizes",
            *eligible_sizes,
            "--random-sizes",
            "100",
            "--random-draws",
            "0",
            "--output-dir",
            str(output_dir),
        ],
        log_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--roles", nargs="+", default=list(DEFAULT_ROLES), choices=list(DEFAULT_ROLES))
    parser.add_argument("--stages", nargs="+", type=int, default=list(DEFAULT_STAGES))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--num-predict", type=int, default=256)
    parser.add_argument("--wait-for-pid", type=int, default=None)
    parser.add_argument("--wait-poll-seconds", type=int, default=60)
    parser.add_argument(
        "--loop-order",
        choices=("model_major", "role_major"),
        default="model_major",
        help="Use model_major for earlier complete per-model tables; role_major preserves the original role-first order.",
    )
    args = parser.parse_args()

    log_path = RUN_ROOT / "logs" / "goemotions_all_sample_efficiency.log"
    if args.wait_for_pid is not None:
        wait_for_pid(args.wait_for_pid, args.wait_poll_seconds)

    manifest = ensure_full_bank(log_path)
    status_csv = RUN_ROOT / "sample_size_efficiency" / "stage_progress.csv"
    stage_summary: list[dict[str, Any]] = []

    def run_role(sample_n: int, subset_packet_file: Path, role: str, models: list[str]) -> None:
        role_root = RUN_ROOT / "reviewer_outputs" / role
        run_command(
            [
                "python3",
                str(RQ2_ROOT / "scripts" / "run_working_generalist_reviews.py"),
                "--packet-file",
                str(subset_packet_file),
                "--output-root",
                str(role_root),
                "--role",
                role,
                "--models",
                *models,
                "--timeout",
                str(args.timeout),
                "--num-predict",
                str(args.num_predict),
            ],
            log_path,
        )
        summarize_role(role, log_path)
        counts = output_counts(role, args.models)
        progress_row = {
            "updated_at_utc": now_utc(),
            "corpus_id": "goemotions",
            "sample_n": sample_n,
            "role": role,
            "models": ";".join(models),
            "counts_by_model": json.dumps(counts, sort_keys=True),
            "expected_per_model_for_stage": sample_n,
        }
        append_csv(status_csv, progress_row)
        stage_summary.append(progress_row)

    for sample_n in args.stages:
        if sample_n > int(manifest["packet_count"]):
            raise ValueError(f"sample stage exceeds packet count: {sample_n}>{manifest['packet_count']}")
        subset_packet_file, _subset_truth_file = balanced_packet_subset(sample_n)
        if args.loop_order == "model_major":
            for model in args.models:
                for role in args.roles:
                    run_role(sample_n, subset_packet_file, role, [model])
                score_stage(sample_n, args.stages, args.roles, log_path)
        else:
            for role in args.roles:
                run_role(sample_n, subset_packet_file, role, args.models)

            score_stage(sample_n, args.stages, args.roles, log_path)

    wrote_full_table = False
    if set(args.roles) == set(DEFAULT_ROLES) and max(args.stages) >= int(manifest["packet_count"]):
        run_command(
            [
                "python3",
                str(RQ2_ROOT / "scripts" / "score_working_detection_table.py"),
                "--run-root",
                str(RUN_ROOT),
                "--roles",
                *args.roles,
                "--output-dir",
                str(RUN_ROOT / "table_exports" / "role_methods_staged"),
            ],
            log_path,
        )
        wrote_full_table = True

    write_json(
        RUN_ROOT / "sample_size_efficiency" / "staged_run_manifest.json",
        {
            "completed_at_utc": now_utc(),
            "full_manifest": str(RUN_ROOT / "manifest.json"),
            "models": args.models,
            "roles": args.roles,
            "stages": args.stages,
            "loop_order": args.loop_order,
            "status_csv": str(status_csv),
            "stage_summary": stage_summary,
            "wrote_full_table": wrote_full_table,
        },
    )
    print(RUN_ROOT)
    print(status_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
