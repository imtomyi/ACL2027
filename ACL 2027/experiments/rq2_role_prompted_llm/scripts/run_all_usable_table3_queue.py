#!/usr/bin/env python3
"""Queue all usable working corpora for Table 3 role-method experiments.

The queue runs sequentially, resumes from existing JSON outputs, and writes
stage-level Table 3 exports for Generalist, Fixed role, and All roles.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
STORAGE = WORKSPACE / "Storage" / "draft_review_packets"
REVIEWER_OUTPUTS_DIR = "reviewer_outputs_prompt_suite_v2"
TABLE_EXPORTS_DIR = "table_exports_prompt_suite_v2"
WARRANTGATE_DIR = "warrantgate_prompt_suite_v2"
SAMPLE_EFFICIENCY_DIR = "sample_size_efficiency_prompt_suite_v2"

ROLES = ("generalist", "qualitative_methods", "domain")
MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")
QUALITY_JUDGE_MODEL = "qwen3:8b"
BANKS = (
    {
        "run_id": "dreaddit_dev580_working_v1",
        "corpus_id": "dreaddit",
        "stages": (100, 250, 500, 580),
    },
    {
        "run_id": "goemotions_train_all_working_v1",
        "corpus_id": "goemotions",
        "stages": (100, 250, 500, 1000, 2000, 4000, 6000, 8000, 9540),
    },
    {
        "run_id": "agyw_focus_groups_eval765_working_v1",
        "corpus_id": "agyw_focus_groups",
        "stages": (100, 250, 500, 765),
    },
    {
        "run_id": "parlamint_gb_fullsample_eval100_working_v1",
        "corpus_id": "parlamint_gb",
        "stages": (100,),
    },
)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_table(path: Path, rows: list[dict[str, str]]) -> None:
    headers = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_combined_table3_snapshot(
    queue_name: str,
    banks: tuple[dict[str, Any], ...],
    stage_n: int,
) -> None:
    rows: list[dict[str, str]] = []
    for bank in banks:
        export_root = STORAGE / str(bank["run_id"]) / TABLE_EXPORTS_DIR
        candidate_paths = [
            export_root / f"table3_methods_n{int(size)}" / "table3_manuscript.csv"
            for size in bank["stages"]
            if int(size) <= stage_n
        ]
        existing_paths = [path for path in candidate_paths if path.exists()]
        if not existing_paths:
            continue
        path = existing_paths[-1]
        rows.extend(read_csv(path))
    if not rows:
        return
    csv_path = STORAGE / f"{queue_name}_table3_combined.csv"
    md_path = STORAGE / f"{queue_name}_table3_combined.md"
    write_csv(csv_path, rows)
    write_markdown_table(md_path, rows)


def append_progress(
    queue_log: Path,
    *,
    run_id: str,
    corpus_id: str,
    stage_n: int,
    event: str,
    role: str = "",
    model: str = "",
    target_n: int | None = None,
    existing_n: int | None = None,
    missing_n: int | None = None,
    completed_n: int | None = None,
    note: str = "",
) -> None:
    append_csv(
        queue_log.with_suffix(".csv"),
        {
            "timestamp_utc": now_utc(),
            "run_id": run_id,
            "corpus_id": corpus_id,
            "stage_n": stage_n,
            "event": event,
            "role": role,
            "model": model,
            "target_n": target_n,
            "existing_n": existing_n,
            "missing_n": missing_n,
            "completed_n": completed_n,
            "note": note,
        },
    )


def exception_note(error: BaseException) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        return f"exit_code={error.returncode}; command={subprocess.list2cmdline(error.cmd)}"
    return f"{type(error).__name__}: {error}"


def safe_model_dir(model: str) -> str:
    return model.replace(":", "_").replace(".", "_")


def reviewer_running() -> bool:
    current_pid = os.getpid()
    result = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, args = stripped.partition(" ")
        if not pid_text.isdigit() or int(pid_text) == current_pid:
            continue
        if "run_working_generalist_reviews.py" not in args:
            continue
        if "python" not in args.lower():
            continue
        return True
    return False


def wait_for_slot(log_path: Path, poll_seconds: int) -> None:
    while reviewer_running():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"[{now_utc()}] waiting_for_existing_reviewer\n")
        time.sleep(poll_seconds)


def run_command(command: list[str], log_path: Path, dry_run: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{now_utc()}] $ {' '.join(subprocess.list2cmdline([part]) for part in command)}\n")
        log.flush()
        if dry_run:
            log.write(f"[{now_utc()}] dry_run\n")
            return
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


def packet_file_for(bank_root: Path, corpus_id: str) -> Path:
    return bank_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"


def truth_file_for(bank_root: Path) -> Path:
    return bank_root / "private" / "truth_map.private.jsonl"


def balanced_subset(bank_root: Path, corpus_id: str, sample_n: int) -> tuple[Path, Path]:
    full_packets = {str(row["packet_id"]): row for row in load_jsonl(packet_file_for(bank_root, corpus_id))}
    truth_rows = load_jsonl(truth_file_for(bank_root))
    by_flaw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(truth_rows, key=lambda item: item["packet_id"]):
        by_flaw[str(row["known_intended_flaw_type"])].append(row)
    if sample_n % len(by_flaw):
        raise ValueError(f"{bank_root.name}: sample_n must divide {len(by_flaw)} flaw types: {sample_n}")
    selected: list[dict[str, Any]] = []
    per_flaw = sample_n // len(by_flaw)
    for flaw_type, rows in sorted(by_flaw.items()):
        if len(rows) < per_flaw:
            raise ValueError(f"{bank_root.name}: not enough rows for {flaw_type} n={sample_n}")
        selected.extend(rows[:per_flaw])
    selected.sort(key=lambda row: row["packet_id"])

    subset_root = bank_root / "sample_packets" / f"balanced_n{sample_n}"
    subset_packet_file = subset_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"
    subset_truth_file = subset_root / "private" / "truth_map.private.jsonl"
    write_jsonl(subset_packet_file, [full_packets[str(row["packet_id"])] for row in selected])
    write_jsonl(subset_truth_file, selected)
    write_json(
        subset_root / "manifest.json",
        {
            "corpus_id": corpus_id,
            "created_at_utc": now_utc(),
            "full_run_root": str(bank_root),
            "packet_file": str(subset_packet_file),
            "sample_n": sample_n,
            "sample_type": "nested_balanced",
            "truth_map": str(subset_truth_file),
        },
    )
    return subset_packet_file, subset_truth_file


def output_count(bank_root: Path, role: str, model: str, packet_ids: set[str]) -> int:
    model_dir = bank_root / REVIEWER_OUTPUTS_DIR / role / safe_model_dir(model)
    if not model_dir.exists():
        return 0
    return sum(1 for packet_id in packet_ids if (model_dir / f"{packet_id}.json").exists())


def summarize_role(bank_root: Path, role: str, log_path: Path, dry_run: bool) -> None:
    role_root = bank_root / REVIEWER_OUTPUTS_DIR / role
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "summarize_working_generalist_reviews.py"),
            "--input-root",
            str(role_root),
            "--output-root",
            str(role_root / "derived"),
        ],
        log_path,
        dry_run,
    )


def run_quality_judge(
    bank_root: Path,
    packet_file: Path,
    args: argparse.Namespace,
    log_path: Path,
) -> Path | None:
    if args.skip_quality_judge:
        return None
    output_root = bank_root / "quality_judge" / "credibility_conformability"
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "run_working_quality_judge.py"),
            "--packet-file",
            str(packet_file),
            "--output-root",
            str(output_root),
            "--judge-model",
            args.quality_judge_model,
            "--timeout",
            str(args.timeout),
        ],
        log_path,
        args.dry_run,
    )
    return output_root / "run_summary.json"


def score_stage(
    bank_root: Path,
    corpus_id: str,
    stage_n: int,
    packet_file: Path,
    completed_stages: list[int],
    truth_file: Path,
    quality_summary: Path | None,
    log_path: Path,
    dry_run: bool,
    include_adaptive_warrantgate: bool,
) -> None:
    stage_sizes = [str(size) for size in completed_stages if size <= stage_n]
    fixed_size = 100 if stage_n >= 100 else stage_n
    reviewer_outputs_root = bank_root / REVIEWER_OUTPUTS_DIR
    warrantgate_dir = bank_root / WARRANTGATE_DIR / f"working_warrantgate_v0_n{stage_n}"
    warrantgate_routes = warrantgate_dir / "routes.jsonl"
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "build_working_warrantgate_routes.py"),
            "--run-root",
            str(bank_root),
            "--packet-file",
            str(packet_file),
            "--generalist-scoring",
            str(reviewer_outputs_root / "generalist" / "derived" / "scoring_inputs.jsonl"),
            "--output-dir",
            str(warrantgate_dir),
        ],
        log_path,
        dry_run,
    )
    adaptive_warrantgate_dir = (
        bank_root / WARRANTGATE_DIR / f"working_warrantgate_adaptive_v0_n{stage_n}"
    )
    adaptive_warrantgate_routes = adaptive_warrantgate_dir / "routes.jsonl"
    if include_adaptive_warrantgate:
        run_command(
            [
                sys.executable,
                str(RQ2_ROOT / "scripts" / "build_working_warrantgate_adaptive_routes.py"),
                "--run-root",
                str(bank_root),
                "--packet-file",
                str(packet_file),
                "--generalist-scoring",
                str(reviewer_outputs_root / "generalist" / "derived" / "scoring_inputs.jsonl"),
                "--output-dir",
                str(adaptive_warrantgate_dir),
            ],
            log_path,
            dry_run,
        )
    detection_command = [
        sys.executable,
        str(RQ2_ROOT / "scripts" / "score_working_detection_table.py"),
        "--run-root",
        str(bank_root),
        "--truth-map",
        str(truth_file),
        "--roles",
        *ROLES,
        "--reviewer-outputs-root",
        str(reviewer_outputs_root),
        "--fixed-role",
        "qualitative_methods",
        "--warrantgate-routes",
        str(warrantgate_routes),
        "--output-dir",
        str(bank_root / TABLE_EXPORTS_DIR / f"table3_methods_n{stage_n}"),
    ]
    if include_adaptive_warrantgate:
        detection_command.extend(
            ["--adaptive-warrantgate-routes", str(adaptive_warrantgate_routes)]
        )
    if quality_summary is not None:
        detection_command.extend(["--quality-summary", str(quality_summary)])
    run_command(detection_command, log_path, dry_run)
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "score_working_sample_size_efficiency.py"),
            "--run-root",
            str(bank_root),
            "--roles",
            *ROLES,
            "--reviewer-outputs-root",
            str(reviewer_outputs_root),
            "--balanced-sizes",
            *stage_sizes,
            "--random-sizes",
            "25",
            "--random-draws",
            "0",
            "--minimum-complete-fraction",
            "0.9",
            "--fixed-role",
            "qualitative_methods",
            "--fixed-role-selection-size",
            str(fixed_size),
            "--table-methods-only",
            "--output-dir",
            str(bank_root / SAMPLE_EFFICIENCY_DIR / f"table3_methods_through_n{stage_n}"),
        ],
        log_path,
        dry_run,
    )


def run_bank(bank: dict[str, Any], args: argparse.Namespace, queue_log: Path) -> None:
    bank_root = STORAGE / str(bank["run_id"])
    corpus_id = str(bank["corpus_id"])
    completed_stages: list[int] = []
    stages = [
        int(stage_n)
        for stage_n in bank["stages"]
        if args.max_stage is None or int(stage_n) <= args.max_stage
    ]
    if not stages:
        stages = [min(int(stage_n) for stage_n in bank["stages"])]
    for stage_n in stages:
        stage_log = bank_root / "logs" / f"all_usable_table3_n{stage_n}.log"
        try:
            packet_file, truth_file = balanced_subset(bank_root, corpus_id, int(stage_n))
            truth_rows = load_jsonl(truth_file)
            packet_ids = {str(row["packet_id"]) for row in truth_rows}
        except Exception as error:
            append_progress(
                queue_log,
                run_id=bank_root.name,
                corpus_id=corpus_id,
                stage_n=stage_n,
                event="stage_prepare_failed",
                note=exception_note(error),
            )
            if args.fail_fast:
                raise
            continue
        append_progress(
            queue_log,
            run_id=bank_root.name,
            corpus_id=corpus_id,
            stage_n=stage_n,
            event="stage_start",
            target_n=len(packet_ids),
        )
        for role in ROLES:
            for model in args.models:
                existing_n = output_count(bank_root, role, model, packet_ids)
                missing_n = max(0, len(packet_ids) - existing_n)
                if missing_n == 0:
                    append_progress(
                        queue_log,
                        run_id=bank_root.name,
                        corpus_id=corpus_id,
                        stage_n=stage_n,
                        event="role_model_skip_complete",
                        role=role,
                        model=model,
                        target_n=len(packet_ids),
                        existing_n=existing_n,
                        missing_n=0,
                        completed_n=existing_n,
                        note="existing_outputs_reused",
                    )
                    continue
                append_progress(
                    queue_log,
                    run_id=bank_root.name,
                    corpus_id=corpus_id,
                    stage_n=stage_n,
                    event="role_model_start",
                    role=role,
                    model=model,
                    target_n=len(packet_ids),
                    existing_n=existing_n,
                    missing_n=missing_n,
                    completed_n=existing_n,
                )
                if not args.dry_run:
                    wait_for_slot(queue_log, args.poll_seconds)
                try:
                    run_command(
                        [
                            sys.executable,
                            str(RQ2_ROOT / "scripts" / "run_working_generalist_reviews.py"),
                            "--packet-file",
                            str(packet_file),
                            "--output-root",
                            str(bank_root / REVIEWER_OUTPUTS_DIR / role),
                            "--role",
                            role,
                            "--models",
                            model,
                            "--timeout",
                            str(args.timeout),
                            "--num-predict",
                            str(args.num_predict),
                        ],
                        stage_log,
                        args.dry_run,
                    )
                except Exception as error:
                    completed_n = output_count(bank_root, role, model, packet_ids)
                    append_progress(
                        queue_log,
                        run_id=bank_root.name,
                        corpus_id=corpus_id,
                        stage_n=stage_n,
                        event="role_model_failed",
                        role=role,
                        model=model,
                        target_n=len(packet_ids),
                        existing_n=existing_n,
                        missing_n=missing_n,
                        completed_n=completed_n,
                        note=exception_note(error),
                    )
                    if args.fail_fast:
                        raise
                    continue
                completed_n = output_count(bank_root, role, model, packet_ids)
                append_progress(
                    queue_log,
                    run_id=bank_root.name,
                    corpus_id=corpus_id,
                    stage_n=stage_n,
                    event="role_model_complete",
                    role=role,
                    model=model,
                    target_n=len(packet_ids),
                    existing_n=existing_n,
                    missing_n=missing_n,
                    completed_n=completed_n,
                )
            try:
                summarize_role(bank_root, role, stage_log, args.dry_run)
            except Exception as error:
                append_progress(
                    queue_log,
                    run_id=bank_root.name,
                    corpus_id=corpus_id,
                    stage_n=stage_n,
                    event="summarize_role_failed",
                    role=role,
                    target_n=len(packet_ids),
                    note=exception_note(error),
                )
                if args.fail_fast:
                    raise
        completed_stages.append(int(stage_n))
        append_progress(
            queue_log,
            run_id=bank_root.name,
            corpus_id=corpus_id,
            stage_n=stage_n,
            event="quality_judge_start",
            role="judge",
            model=args.quality_judge_model if not args.skip_quality_judge else "",
            target_n=len(packet_ids),
        )
        try:
            quality_summary = run_quality_judge(bank_root, packet_file, args, stage_log)
            append_progress(
                queue_log,
                run_id=bank_root.name,
                corpus_id=corpus_id,
                stage_n=stage_n,
                event="quality_judge_complete",
                role="judge",
                model=args.quality_judge_model if not args.skip_quality_judge else "",
                target_n=len(packet_ids),
                note=str(quality_summary) if quality_summary else "skipped",
            )
        except Exception as error:
            quality_summary = None
            append_progress(
                queue_log,
                run_id=bank_root.name,
                corpus_id=corpus_id,
                stage_n=stage_n,
                event="quality_judge_failed",
                role="judge",
                model=args.quality_judge_model if not args.skip_quality_judge else "",
                target_n=len(packet_ids),
                note=exception_note(error),
            )
            if args.fail_fast:
                raise
        try:
            score_stage(
                bank_root,
                corpus_id,
                int(stage_n),
                packet_file,
                completed_stages,
                truth_file,
                quality_summary,
                stage_log,
                args.dry_run,
                args.include_adaptive_warrantgate,
            )
        except Exception as error:
            append_progress(
                queue_log,
                run_id=bank_root.name,
                corpus_id=corpus_id,
                stage_n=stage_n,
                event="score_stage_failed",
                target_n=len(packet_ids),
                note=exception_note(error),
            )
            if args.fail_fast:
                raise
        try:
            write_combined_table3_snapshot(args.queue_name, BANKS, int(stage_n))
        except Exception as error:
            append_progress(
                queue_log,
                run_id=bank_root.name,
                corpus_id=corpus_id,
                stage_n=stage_n,
                event="combined_table3_snapshot_failed",
                target_n=len(packet_ids),
                note=exception_note(error),
            )
            if args.fail_fast:
                raise
        append_progress(
            queue_log,
            run_id=bank_root.name,
            corpus_id=corpus_id,
            stage_n=stage_n,
            event="stage_complete",
            target_n=len(packet_ids),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=list(MODELS))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--num-predict", type=int, default=256)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--quality-judge-model", default=QUALITY_JUDGE_MODEL)
    parser.add_argument("--skip-quality-judge", action="store_true")
    parser.add_argument("--include-adaptive-warrantgate", action="store_true")
    parser.add_argument("--max-stage", type=int, default=None)
    parser.add_argument("--queue-name", default="all_usable_table3_prompt_suite_v2_queue")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    queue_log = STORAGE / f"{args.queue_name}.log"
    write_json(
        STORAGE / f"{args.queue_name}_manifest.json",
        {
            "banks": BANKS,
            "created_at_utc": now_utc(),
            "max_stage": args.max_stage,
            "models": args.models,
            "num_predict": args.num_predict,
            "quality_judge_model": None if args.skip_quality_judge else args.quality_judge_model,
            "roles": ROLES,
            "prompt_suite": "table3-baseline-prompt-suite-v2",
            "reviewer_outputs_dir": REVIEWER_OUTPUTS_DIR,
            "table_exports_dir": TABLE_EXPORTS_DIR,
            "shared_fixed_role": "qualitative_methods",
            "status": "queued",
            "table_methods": [
                "Generalist",
                "Fixed role",
                "All roles",
                "WarrantRoute",
                *(
                    ["Adaptive WarrantRoute"]
                    if args.include_adaptive_warrantgate
                    else []
                ),
            ],
            "warrantroute_policy": "working_warrantgate_v0",
            "adaptive_warrantroute_policy": (
                "working_warrantgate_adaptive_v0"
                if args.include_adaptive_warrantgate
                else None
            ),
        },
    )
    with queue_log.open("a", encoding="utf-8") as log:
        log.write(f"[{now_utc()}] all_usable_table3_queue_start\n")
    for bank in BANKS:
        try:
            run_bank(bank, args, queue_log)
        except Exception as error:
            append_progress(
                queue_log,
                run_id=str(bank["run_id"]),
                corpus_id=str(bank["corpus_id"]),
                stage_n=0,
                event="bank_failed",
                note=exception_note(error),
            )
            if args.fail_fast:
                raise
    with queue_log.open("a", encoding="utf-8") as log:
        log.write(f"[{now_utc()}] all_usable_table3_queue_complete\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
