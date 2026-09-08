#!/usr/bin/env python3
"""Run resumable working Table 3 reviews, summaries, and scoring exports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
STORAGE = WORKSPACE / "Storage" / "draft_review_packets"

DEFAULT_BANKS = {
    "dreaddit": STORAGE / "dreaddit_dev100_working_v1",
    "goemotions": STORAGE / "goemotions_dev100_working_v1",
    "agyw_focus_groups": STORAGE / "agyw_focus_groups_eval100_working_v1",
    "parlamint_gb": STORAGE / "parlamint_gb_eval100_working_v1",
}
DEFAULT_ROLES = ("generalist", "qualitative_methods", "domain")
DEFAULT_MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def packet_file_for_bank(bank_root: Path, corpus_id: str) -> Path:
    path = bank_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"
    if not path.exists():
        candidates = sorted((bank_root / "by_dataset").glob("*.review_packets.jsonl"))
        if len(candidates) == 1:
            return candidates[0]
    return path


def expected_packet_count(packet_file: Path) -> int:
    with packet_file.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def output_count(output_root: Path, model: str) -> int:
    model_dir = model.replace(":", "_").replace(".", "_")
    path = output_root / model_dir
    if not path.exists():
        return 0
    return len(list(path.glob("PKT_*.json")))


def run_command(command: list[str], *, dry_run: bool) -> None:
    print(" ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpora",
        nargs="+",
        choices=sorted(DEFAULT_BANKS),
        default=list(DEFAULT_BANKS),
        help="Corpus banks to run.",
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        choices=DEFAULT_ROLES,
        default=list(DEFAULT_ROLES),
        help="Role prompts to run before scoring.",
    )
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Only rebuild summaries and Table 3 exports from existing outputs.",
    )
    parser.add_argument(
        "--include-adaptive-warrantgate",
        action="store_true",
        help="Also build segment-aware WarrantGate routes and add an Adaptive WarrantRoute row.",
    )
    args = parser.parse_args()

    runner = RQ2_ROOT / "scripts" / "run_working_generalist_reviews.py"
    summarizer = RQ2_ROOT / "scripts" / "summarize_working_generalist_reviews.py"
    scorer = RQ2_ROOT / "scripts" / "score_working_detection_table.py"
    warrantgate = RQ2_ROOT / "scripts" / "build_working_warrantgate_routes.py"
    adaptive_warrantgate = RQ2_ROOT / "scripts" / "build_working_warrantgate_adaptive_routes.py"

    for corpus_id in args.corpora:
        bank_root = DEFAULT_BANKS[corpus_id]
        manifest = load_json(bank_root / "manifest.json")
        packet_file = packet_file_for_bank(bank_root, str(manifest.get("corpus_id", corpus_id)))
        expected = expected_packet_count(packet_file)
        print(f"\n== {corpus_id} ({expected} packets) ==")

        for role in args.roles:
            output_root = bank_root / "reviewer_outputs" / role
            missing = {
                model: expected - output_count(output_root, model) for model in args.models
            }
            runnable_models = [model for model, count in missing.items() if count > 0]
            if runnable_models and not args.score_only:
                print(f"missing {role}: {missing}")
                run_command(
                    [
                        sys.executable,
                        str(runner),
                        "--packet-file",
                        str(packet_file),
                        "--output-root",
                        str(output_root),
                        "--role",
                        role,
                        "--models",
                        *runnable_models,
                        "--timeout",
                        str(args.timeout),
                    ],
                    dry_run=args.dry_run,
                )
            else:
                print(f"complete or score-only {role}: {missing}")

            run_command(
                [
                    sys.executable,
                    str(summarizer),
                    "--input-root",
                    str(output_root),
                    "--output-root",
                    str(output_root / "derived"),
                ],
                dry_run=args.dry_run,
            )

        warrantgate_routes = bank_root / "warrantgate" / "working_warrantgate_v0" / "routes.jsonl"
        if "generalist" in args.roles:
            run_command(
                [
                    sys.executable,
                    str(warrantgate),
                    "--run-root",
                    str(bank_root),
                    "--packet-file",
                    str(packet_file),
                    "--output-dir",
                    str(warrantgate_routes.parent),
                ],
                dry_run=args.dry_run,
            )

        adaptive_routes = (
            bank_root / "warrantgate" / "working_warrantgate_adaptive_v0" / "routes.jsonl"
        )
        if args.include_adaptive_warrantgate and "generalist" in args.roles:
            run_command(
                [
                    sys.executable,
                    str(adaptive_warrantgate),
                    "--run-root",
                    str(bank_root),
                    "--packet-file",
                    str(packet_file),
                    "--output-dir",
                    str(adaptive_routes.parent),
                ],
                dry_run=args.dry_run,
            )

        score_command = [
            sys.executable,
            str(scorer),
            "--run-root",
            str(bank_root),
            "--roles",
            *args.roles,
            "--warrantgate-routes",
            str(warrantgate_routes),
            "--output-dir",
            str(bank_root / "table_exports" / "table3_working"),
        ]
        if args.include_adaptive_warrantgate:
            score_command.extend(["--adaptive-warrantgate-routes", str(adaptive_routes)])
        run_command(score_command, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
