#!/usr/bin/env python3
"""Repair historical n=100 prompt-identity drift without touching originals."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.error
from collections import Counter
from pathlib import Path
from typing import Any

import run_working_generalist_reviews as reviewer


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config/table3_n100_prompt_identity_repair_v1.json"
ANSWER_KEY_FIELDS = {
    "known_intended_flaw_type",
    "known_intended_flaw_note",
    "review_instruction",
}
FINAL_INSTRUCTION = (
    "Return exactly one JSON object. Do not mention the hidden answer key, "
    "target flaw labels, or any field not present in the task payload. "
    "Keep rationale concise, no more than 60 words."
)


class RepairError(RuntimeError):
    """Raised when the repair contract or inventory is invalid."""


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RepairError(f"json_root_not_object:{path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RepairError(f"jsonl_row_not_object:{path}:{line_number}")
            rows.append(value)
    return rows


def resolve_file(reference: str) -> Path:
    path = Path(reference)
    if not path.is_absolute():
        path = WORKSPACE / path
    path = path.resolve()
    try:
        path.relative_to(WORKSPACE.resolve())
    except ValueError as exc:
        raise RepairError(f"path_outside_workspace:{reference}") from exc
    if not path.is_file() or path.is_symlink():
        raise RepairError(f"file_missing_or_not_regular:{reference}")
    return path


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_historical_prompt(
    role_prompt: str, shared_guide: str, packet: dict[str, Any]
) -> str:
    payload = {
        key: value for key, value in packet.items() if key not in ANSWER_KEY_FIELDS
    }
    return "\n\n".join(
        [
            role_prompt.strip(),
            "Shared rater guide:",
            shared_guide.strip(),
            "Task payload JSON:",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            FINAL_INSTRUCTION,
        ]
    )


def load_and_validate_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    if config.get("document_type") != "table3_n100_prompt_identity_repair":
        raise RepairError("config_document_type_invalid")
    if config.get("status") != "working_diagnostic_only":
        raise RepairError("config_status_invalid")
    if config.get("original_outputs_overwrite_allowed") is not False:
        raise RepairError("original_output_overwrite_not_forbidden")
    if config.get("manuscript_result") is not False:
        raise RepairError("config_claims_manuscript_result")
    if config.get("manuscript_eligible") is not False:
        raise RepairError("config_claims_manuscript_eligibility")

    bindings = list(config["role_prompts"].values()) + [config["shared_rater_guide"]]
    for binding in bindings:
        asset = resolve_file(binding["path"])
        if file_sha256(asset) != binding["sha256"]:
            raise RepairError(f"asset_hash_mismatch:{binding['path']}")

    expected_n = config["expected_packet_count_per_dataset"]
    for dataset in config["datasets"]:
        packet_file = resolve_file(dataset["packet_file"])
        truth_map = resolve_file(dataset["truth_map"])
        if file_sha256(packet_file) != dataset["packet_file_sha256"]:
            raise RepairError(f"packet_file_hash_mismatch:{dataset['corpus_id']}")
        if file_sha256(truth_map) != dataset["truth_map_sha256"]:
            raise RepairError(f"truth_map_hash_mismatch:{dataset['corpus_id']}")
        packets = load_jsonl(packet_file)
        truth = load_jsonl(truth_map)
        if len(packets) != expected_n or len(truth) != expected_n:
            raise RepairError(f"n100_inventory_invalid:{dataset['corpus_id']}")
        packet_ids = {row.get("packet_id") for row in packets}
        truth_ids = {row.get("packet_id") for row in truth}
        if packet_ids != truth_ids or len(packet_ids) != expected_n:
            raise RepairError(f"packet_truth_id_mismatch:{dataset['corpus_id']}")
    return config


def prompt_assets(config: dict[str, Any]) -> tuple[dict[str, str], str]:
    prompts = {
        role: resolve_file(binding["path"]).read_text(encoding="utf-8")
        for role, binding in config["role_prompts"].items()
    }
    guide = resolve_file(config["shared_rater_guide"]["path"]).read_text(
        encoding="utf-8"
    )
    return prompts, guide


def output_path(root: Path, role: str, model: str, packet_id: str) -> Path:
    return root / role / reviewer.safe_model_dir(model) / f"{packet_id}.json"


def scan(config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prompts, guide = prompt_assets(config)
    details: list[dict[str, Any]] = []
    counts: Counter[tuple[str, str, str]] = Counter()
    target_valid = 0
    target_total = 0
    for dataset in config["datasets"]:
        bank_root = WORKSPACE / "Storage/draft_review_packets" / dataset["run_id"]
        source_root = bank_root / config["source_outputs_dir"]
        target_root = bank_root / config["repaired_outputs_dir"]
        packets = load_jsonl(resolve_file(dataset["packet_file"]))
        for role, role_prompt in prompts.items():
            for packet in packets:
                packet_id = str(packet["packet_id"])
                prompt = build_historical_prompt(role_prompt, guide, packet)
                expected_hash = reviewer.sha256_text(prompt)
                for model in config["models"]:
                    source = output_path(source_root, role, model, packet_id)
                    if not source.is_file():
                        raise RepairError(f"source_output_missing:{source}")
                    source_record = load_json(source)
                    needs_generation = not (
                        source_record.get("status") == "valid"
                        and source_record.get("prompt_sha256") == expected_hash
                    )
                    if needs_generation:
                        counts[(dataset["corpus_id"], role, model)] += 1
                        details.append(
                            {
                                "corpus_id": dataset["corpus_id"],
                                "run_id": dataset["run_id"],
                                "role": role,
                                "model": model,
                                "packet_id": packet_id,
                                "expected_prompt_sha256": expected_hash,
                                "source_output": str(source),
                            }
                        )
                    target = output_path(target_root, role, model, packet_id)
                    if target.is_file():
                        target_total += 1
                        target_record = load_json(target)
                        if (
                            target_record.get("status") == "valid"
                            and target_record.get("prompt_sha256") == expected_hash
                        ):
                            target_valid += 1
    report = {
        "document_type": "table3_n100_prompt_identity_repair_audit",
        "created_at_utc": now_utc(),
        "expected_output_count": config["expected_output_count"],
        "source_outputs_requiring_regeneration": len(details),
        "expected_preflight_regeneration_count": config[
            "expected_preflight_regeneration_count"
        ],
        "regeneration_count_matches_freeze": len(details)
        == config["expected_preflight_regeneration_count"],
        "regeneration_by_dataset_role_model": [
            {
                "corpus_id": corpus_id,
                "role": role,
                "model": model,
                "count": count,
            }
            for (corpus_id, role, model), count in sorted(counts.items())
        ],
        "target_output_count": target_total,
        "target_valid_prompt_matched_count": target_valid,
        "manuscript_result": False,
        "manuscript_eligible": False,
    }
    return report, details


def generate_record(
    *,
    dataset: dict[str, Any],
    role: str,
    model: str,
    packet: dict[str, Any],
    prompt: str,
    prompt_path: Path,
    source_output: Path,
    timeout: int,
    num_predict: int,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_schema_version": "working-role-review-output-v1-prompt-identity-repair",
        "created_at_utc": now_utc(),
        "corpus_id": packet.get("corpus_id"),
        "packet_id": packet["packet_id"],
        "output_id": packet.get("output_id"),
        "role": role,
        "model_id": model,
        "role_prompt_file": str(prompt_path),
        "role_prompt_sha256": file_sha256(prompt_path),
        "prompt_sha256": reviewer.sha256_text(prompt),
        "source_packet_file": dataset["packet_file"],
        "answer_key_fields_removed": sorted(ANSWER_KEY_FIELDS),
        "repair_source_output": str(source_output),
        "repair_reason": "historical_full_prompt_hash_mismatch",
    }
    try:
        raw, ollama_payload = reviewer.call_ollama(
            model, prompt, timeout, num_predict
        )
        parsed_raw = reviewer.extract_json_object(raw)
        parsed, normalization_notes = reviewer.normalize_rating(parsed_raw)
        validation_errors = reviewer.validate_rating(parsed)
        record.update(
            {
                "status": "valid" if not validation_errors else "schema_warning",
                "validation_errors": validation_errors,
                "normalization_notes": normalization_notes,
                "parsed_rating_raw": parsed_raw,
                "parsed_rating": parsed,
                "raw_response": raw,
                "ollama_done": ollama_payload.get("done"),
                "ollama_total_duration": ollama_payload.get("total_duration"),
                "ollama_eval_count": ollama_payload.get("eval_count"),
            }
        )
    except (
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        record.update(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
    return record


def run_repair(
    config: dict[str, Any], max_new_calls: int | None
) -> dict[str, Any]:
    report, details = scan(config)
    if not report["regeneration_count_matches_freeze"]:
        raise RepairError("preflight_regeneration_count_drift")
    prompts, guide = prompt_assets(config)
    detail_keys = {
        (row["run_id"], row["role"], row["model"], row["packet_id"])
        for row in details
    }
    generated = copied = skipped = errors = 0
    for dataset in config["datasets"]:
        bank_root = WORKSPACE / "Storage/draft_review_packets" / dataset["run_id"]
        source_root = bank_root / config["source_outputs_dir"]
        target_root = bank_root / config["repaired_outputs_dir"]
        packets = load_jsonl(resolve_file(dataset["packet_file"]))
        for role, role_prompt in prompts.items():
            prompt_path = resolve_file(config["role_prompts"][role]["path"])
            for packet in packets:
                packet_id = str(packet["packet_id"])
                prompt = build_historical_prompt(role_prompt, guide, packet)
                expected_hash = reviewer.sha256_text(prompt)
                for model in config["models"]:
                    source = output_path(source_root, role, model, packet_id)
                    target = output_path(target_root, role, model, packet_id)
                    if target.is_file():
                        existing = load_json(target)
                        if (
                            existing.get("status") == "valid"
                            and existing.get("prompt_sha256") == expected_hash
                        ):
                            skipped += 1
                            continue
                    key = (dataset["run_id"], role, model, packet_id)
                    if key not in detail_keys:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
                        copied += 1
                        continue
                    if max_new_calls is not None and generated >= max_new_calls:
                        continue
                    record = generate_record(
                        dataset=dataset,
                        role=role,
                        model=model,
                        packet=packet,
                        prompt=prompt,
                        prompt_path=prompt_path,
                        source_output=source,
                        timeout=config["generation"]["timeout_seconds"],
                        num_predict=config["generation"]["num_predict"],
                    )
                    write_json(target, record)
                    generated += 1
                    errors += record["status"] != "valid"
                    print(
                        f"{record['status']} {dataset['corpus_id']} {role} "
                        f"{model} {packet_id}",
                        flush=True,
                    )
    final_report, _ = scan(config)
    final_report.update(
        {
            "copied_this_run": copied,
            "generated_this_run": generated,
            "generation_errors_this_run": errors,
            "skipped_valid_this_run": skipped,
        }
    )
    manifest = (
        WORKSPACE
        / "Storage/draft_review_packets"
        / "table3_n100_prompt_identity_repair_v1_manifest.json"
    )
    write_json(manifest, final_report)
    return final_report


def finalize(config: dict[str, Any]) -> Path:
    report, _ = scan(config)
    if report["target_valid_prompt_matched_count"] != config["expected_output_count"]:
        raise RepairError("repair_inventory_not_complete")
    combined_rows: list[dict[str, str]] = []
    for dataset in config["datasets"]:
        bank_root = WORKSPACE / "Storage/draft_review_packets" / dataset["run_id"]
        target_root = bank_root / config["repaired_outputs_dir"]
        for role in config["role_prompts"]:
            subprocess.run(
                [
                    sys.executable,
                    str(RQ2_ROOT / "scripts/summarize_working_generalist_reviews.py"),
                    "--input-root",
                    str(target_root / role),
                    "--output-root",
                    str(target_root / role / "derived"),
                ],
                cwd=WORKSPACE,
                check=True,
            )
        export_dir = bank_root / config["table_export_dir"]
        subprocess.run(
            [
                sys.executable,
                str(RQ2_ROOT / "scripts/score_working_detection_table.py"),
                "--run-root",
                str(bank_root),
                "--truth-map",
                str(resolve_file(dataset["truth_map"])),
                "--roles",
                *config["role_prompts"].keys(),
                "--reviewer-outputs-root",
                str(target_root),
                "--fixed-role",
                config["shared_fixed_role"],
                "--baseline-only",
                "--output-dir",
                str(export_dir),
            ],
            cwd=WORKSPACE,
            check=True,
        )
        with (export_dir / "table3_manuscript.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            combined_rows.extend(csv.DictReader(handle))

    output_root = WORKSPACE / "Storage/draft_review_packets"
    combined_csv = output_root / "table3_n100_prompt_identity_repair_v1_baselines.csv"
    fieldnames = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    with combined_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_rows)
    combined_md = combined_csv.with_suffix(".md")
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join("---" for _ in fieldnames) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(row[field]) for field in fieldnames) + " |"
        for row in combined_rows
    )
    combined_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    final_manifest = output_root / "table3_n100_prompt_identity_repair_v1_final.json"
    write_json(
        final_manifest,
        {
            **report,
            "status": "validated_working_complete",
            "table_row_count": len(combined_rows),
            "expected_table_row_count": 36,
            "shared_fixed_role": config["shared_fixed_role"],
            "combined_csv": str(combined_csv),
            "combined_markdown": str(combined_md),
            "manuscript_result": False,
            "manuscript_eligible": False,
        },
    )
    return final_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "run", "finalize", "run-and-finalize"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--max-new-calls", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_and_validate_config(args.config.resolve())
    if args.command == "audit":
        report, _ = scan(config)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["regeneration_count_matches_freeze"] else 2
    if args.command in {"run", "run-and-finalize"}:
        report = run_repair(config, args.max_new_calls)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        if args.command == "run":
            return 0
    final_manifest = finalize(config)
    print(final_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
