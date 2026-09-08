#!/usr/bin/env python3
"""Repair exhausted technical failures from the frozen Table 3 quality run."""

from __future__ import annotations

import csv
import fcntl
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
from collections import defaultdict
from pathlib import Path

import run_table3_review_quality as quality
import score_working_detection_table as detection


SCRIPT = Path(__file__).resolve()
BASE = quality.BUNDLE / "runs/review_quality_n100_20260904_r2"
REPAIR = quality.BUNDLE / "repairs/review_quality_n100_20260904_r2_schema_r1"
SUFFIX = """

TECHNICAL RESPONSE REVISION
Apply every substantive definition and pass rule above without change. This
revision changes response formatting only and applies identically to all repair
units. Before returning the object, verify all of the following:
- Write each of the four required JSON keys exactly once.
- Keep each rationale to at most 45 words, providing margin under the frozen
  60-word validity limit.
- In rationales, use only CLAIM and review IDs actually present in the payload
  (R1, R2, or R3). Do not write E, S, P, D, or U identifiers; refer to the
  supplied source context in words instead. Do not invent an identifier.
"""


def verified_manifest(path: Path) -> dict:
    manifest = quality.read_json(path)
    expected = manifest.pop("contract_sha256")
    if quality.digest(quality.canonical(manifest).encode()) != expected:
        raise quality.ContractError("base_manifest_hash_changed")
    manifest["contract_sha256"] = expected
    return manifest


def load_base() -> tuple[dict, dict, dict, str, list[dict], dict[str, dict], list[dict]]:
    manifest = verified_manifest(BASE / "manifest.json")
    quality.check_hashes(manifest["bound_inputs"] + manifest["frozen_assets"])
    final = quality.read_json(BASE / "final.json")
    if final["status"] != "completed_with_unresolved_quality":
        raise quality.ContractError("base_not_completed_with_unresolved_quality")
    design = quality.read_json(BASE / "design_snapshot.json")
    schema = quality.read_json(BASE / "schema_snapshot.json")
    instruction = (BASE / "prompt_snapshot.txt").read_text()
    units = quality.repair.load_jsonl(BASE / "units.jsonl")
    records: dict[str, dict] = {}
    exhausted = []
    for unit in units:
        attempts = []
        for path in sorted((BASE / "attempts" / unit["unit_id"]).glob("*.json")):
            attempt = quality.read_json(path)
            attempts.append(attempt)
            if quality.valid_record(attempt, unit, manifest, schema, design) and unit["unit_id"] not in records:
                records[unit["unit_id"]] = attempt
        if unit["unit_id"] not in records:
            if len(attempts) != 3 or any(a.get("status") == "valid" for a in attempts):
                raise quality.ContractError("unresolved_unit_not_retry_exhausted")
            exhausted.append({**unit, "base_attempts": [
                {"attempt": a["attempt"], "status": a["status"], "errors": a.get("errors", [])}
                for a in attempts
            ]})
    if len(units) != 3600 or len(records) != 3592 or len(exhausted) != 8:
        raise quality.ContractError("unexpected_base_coverage")
    return manifest, design, schema, instruction, units, records, exhausted


def repair_request(design: dict, instruction: str, schema: dict, payload: dict) -> dict:
    request = quality.make_request(design, instruction.rstrip() + SUFFIX, schema, payload)
    request["format"] = schema
    return request


def prepare(base_manifest: dict, design: dict, schema: dict, instruction: str,
            exhausted: list[dict]) -> dict:
    runtime = quality.runtime(design["primary_judge_candidate"]["model_id"])
    if runtime != base_manifest["runtime"]:
        raise quality.ContractError("runtime_drift")
    units = []
    for unit in exhausted:
        request = repair_request(design, instruction, schema, unit["payload"])
        units.append({**unit, "repair_request_sha256": quality.digest(quality.canonical(request).encode())})
    REPAIR.mkdir(parents=True)
    quality.atomic_write(REPAIR / "units.jsonl", "".join(quality.canonical(u) + "\n" for u in units), immutable=True)
    quality.atomic_write(REPAIR / "prompt_revision.txt", instruction.rstrip() + SUFFIX, immutable=True)
    quality.write_json(REPAIR / "schema_snapshot.json", schema, immutable=True)
    manifest = {
        "schema_version": "table3-review-quality-technical-repair-v1",
        "repair_id": REPAIR.name,
        "created_at_utc": quality.now(),
        "status": "prepared",
        "base_run": str(BASE),
        "base_contract_sha256": base_manifest["contract_sha256"],
        "planned_units": 8,
        "selection_rule": "all and only base units with three exhausted technical failures",
        "substantive_rubric_changed": False,
        "technical_revision": {
            "format": "frozen JSON Schema object instead of generic json mode",
            "rationale_prompt_limit_words": 45,
            "validator_limit_words": 60,
            "rationale_identifier_policy": "CLAIM and present R IDs only",
        },
        "judge_runtime": runtime,
        "bindings": [quality.bind(p) for p in (
            SCRIPT, BASE / "manifest.json", BASE / "final.json", BASE / "units.jsonl",
            BASE / "design_snapshot.json", BASE / "schema_snapshot.json",
            BASE / "prompt_snapshot.txt", BASE / "table_before.csv", BASE / "table_before.md",
        )],
        "frozen_assets": [quality.bind(REPAIR / name) for name in (
            "units.jsonl", "prompt_revision.txt", "schema_snapshot.json")],
        "manuscript_eligible": False,
        "human_audit_status": "not_run",
    }
    manifest["contract_sha256"] = quality.digest(quality.canonical(manifest).encode())
    quality.write_json(REPAIR / "manifest.json", manifest, immutable=True)
    return manifest


def load_repair_records(manifest: dict, units: list[dict], schema: dict,
                        design: dict) -> tuple[dict[str, dict], list[dict]]:
    records, attempts = {}, []
    for unit in units:
        for path in sorted((REPAIR / "attempts" / unit["unit_id"]).glob("*.json")):
            attempt = quality.read_json(path)
            if (attempt.get("repair_contract_sha256") != manifest["contract_sha256"]
                    or attempt.get("request_sha256") != unit["repair_request_sha256"]):
                raise quality.ContractError("repair_attempt_identity_mismatch")
            attempts.append(attempt)
            parsed, errors = quality.validate_response(
                attempt.get("ollama_response", {}), unit, schema,
                design["proposed_generation"], design["primary_judge_candidate"]["model_id"])
            if attempt.get("status") == "valid":
                if errors or parsed != attempt.get("decision"):
                    raise quality.ContractError("saved_repair_output_failed_validation")
                records.setdefault(unit["unit_id"], attempt)
    return records, attempts


def export_complete(base_manifest: dict, summary: dict, repair_manifest: dict) -> None:
    rows = list(csv.reader(io.StringIO((BASE / "table_before.csv").read_text())))
    by_key = {(detection.DATASET_LABELS[r["corpus_id"]], r["method"],
               detection.MODEL_LABELS[r["reviewer_model_id"]]): r for r in summary["rows"]}
    for row in rows[1:]:
        item = by_key.get(tuple(row[:3]))
        if item:
            for index, metric in enumerate(quality.METRICS, 5):
                if item[metric]["percent"] is None:
                    raise quality.ContractError("repair_did_not_complete_all_quality_cells")
                row[index] = f"{item[metric]['percent']:.1f}"
    csv_text, table_md = quality.render_table(rows)
    original_md = (BASE / "table_before.md").read_text().split("\n## Review-Quality Audit\n", 1)[0]
    original_md = original_md.replace("## Quality Metric Status", "## Historical Quality Status (Before This Audit)")
    pattern = r"(?m)^\| Dataset \|[^\n]*\n(?:\|[^\n]*\n)+"
    matches = list(re.finditer(pattern, original_md))
    if len(matches) != 1:
        raise quality.ContractError("markdown_table_not_uniquely_identified")
    md_text = original_md[:matches[0].start()] + table_md + original_md[matches[0].end():]
    md_text += ("\n## Review-Quality Audit\n\n"
                f"Base run: `{BASE.name}`. Technical repair: `{REPAIR.name}`. Judge: `qwen3:8b`. "
                "Binary decisions: 3,600/3,600 for each metric.\n\n"
                "The repair re-evaluated only eight units that had exhausted the frozen technical retry limit. "
                "It used the same substantive rubric and judge with JSON Schema constrained output, a 45-word "
                "prompt margin under the 60-word validator limit, and restricted rationale identifiers. "
                "The original failed attempts remain preserved.\n\n"
                "Credibility and Conformability are review-level LLM-judged rubric pass rates, not independent "
                "expert ground truth. TP/N and Recall are preserved historical values. WarrantRoute quality remains "
                "deferred. Working diagnostic only; not manuscript-eligible. Human audit has not run.\n\n"
                f"Base provenance: `{BASE / 'manifest.json'}`. Repair provenance: `{REPAIR / 'manifest.json'}`.\n")
    quality.atomic_write(REPAIR / "table3_review_quality_complete.csv", csv_text)
    quality.atomic_write(REPAIR / "table3_review_quality_complete.md", md_text)
    current_csv = Path(base_manifest["table_paths"]["csv"])
    current_md = Path(base_manifest["table_paths"]["md"])
    receipt = quality.read_json(BASE / "export_receipt.json")
    if quality.file_hash(current_csv) != receipt["expected_hashes"]["csv"] or quality.file_hash(current_md) != receipt["expected_hashes"]["md"]:
        raise quality.ContractError("shared_table_changed_after_base_export")
    quality.atomic_write(current_csv, csv_text)
    quality.atomic_write(current_md, md_text)
    quality.write_json(REPAIR / "export_receipt.json", {
        "updated_at_utc": quality.now(),
        "targets": {"csv": str(current_csv), "md": str(current_md)},
        "hashes": {"csv": quality.digest(csv_text.encode()), "md": quality.digest(md_text.encode())},
        "preserved_columns": ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"],
        "deferred_method": "WarrantRoute",
    })


def run() -> int:
    base_manifest, design, schema, instruction, units, base_records, exhausted = load_base()
    if not REPAIR.exists():
        manifest = prepare(base_manifest, design, schema, instruction, exhausted)
    else:
        manifest = verified_manifest(REPAIR / "manifest.json")
    quality.check_hashes(manifest["bindings"] + manifest["frozen_assets"])
    if quality.runtime(design["primary_judge_candidate"]["model_id"]) != manifest["judge_runtime"]:
        raise quality.ContractError("runtime_drift")
    repair_units = quality.repair.load_jsonl(REPAIR / "units.jsonl")
    repair_records, attempts = load_repair_records(manifest, repair_units, schema, design)
    model = design["primary_judge_candidate"]["model_id"]
    generation = design["proposed_generation"]
    for unit in repair_units:
        uid = unit["unit_id"]
        if uid in repair_records:
            continue
        prior = [a for a in attempts if a["unit_id"] == uid]
        request = repair_request(design, instruction, schema, unit["payload"])
        if quality.digest(quality.canonical(request).encode()) != unit["repair_request_sha256"]:
            raise quality.ContractError("repair_request_hash_changed")
        for number in range(len(prior) + 1, 4):
            position = quality.log_position()
            started = time.monotonic()
            attempt = {
                **{k: unit[k] for k in ("unit_id", "corpus_id", "packet_id", "reviewer_model_id", "method")},
                "attempt": number, "created_at_utc": quality.now(),
                "repair_contract_sha256": manifest["contract_sha256"],
                "base_contract_sha256": manifest["base_contract_sha256"],
                "request_sha256": unit["repair_request_sha256"], "status": "in_flight",
                "judge_model_id": model,
            }
            try:
                response = quality.api("generate", request, generation["timeout_seconds"])
                kept = {k: v for k, v in response.items() if k not in {"thinking", "context", "logprobs"}}
                kept["thinking_character_count"] = len(response.get("thinking", ""))
                decision, errors = quality.validate_response(response, unit, schema, generation, model)
                if quality.truncation_since(position):
                    errors.append("server_reported_truncation")
                attempt.update(status="valid" if not errors else "schema_error", decision=decision,
                               errors=errors, ollama_response=kept)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, quality.ContractError) as exc:
                attempt.update(status="transport_error", errors=[type(exc).__name__ + ":" + str(exc)])
            attempt["wall_seconds"] = round(time.monotonic() - started, 4)
            quality.write_json(REPAIR / "attempts" / uid / f"{number:02d}.json", attempt, immutable=True)
            attempts.append(attempt)
            print(f"{quality.now()} {attempt['status']} {unit['corpus_id']} {unit['method']} {unit['reviewer_model_id']} attempt={number}", flush=True)
            if attempt["status"] == "valid":
                repair_records[uid] = attempt
                break
            if number < 3:
                time.sleep(1)
    combined = dict(base_records)
    combined.update(repair_records)
    summary = quality.summarize(units, combined)
    status = "repaired_complete" if len(combined) == 3600 and summary["completed_binary_pairs"] == 3600 else "repair_incomplete"
    result = {
        **summary, "status": status, "repair_id": REPAIR.name,
        "base_valid_records": len(base_records), "repair_valid_records": len(repair_records),
        "repair_attempts": len(attempts),
        "repair_error_attempts": sum(a.get("status") != "valid" for a in attempts),
        "repair_median_wall_seconds": statistics.median([a["wall_seconds"] for a in attempts if a.get("status") == "valid"]) if repair_records else None,
        "completed_at_utc": quality.now(), "human_audit_status": "not_run",
        "manuscript_eligible": False, "deferred_methods": ["WarrantRoute"],
    }
    if status == "repaired_complete":
        export_complete(base_manifest, summary, manifest)
        result["quality_complete_rows"] = 36
    quality.write_json(REPAIR / "final.json", result)
    return 0 if status == "repaired_complete" else 2


def main() -> int:
    quality.BUNDLE.mkdir(parents=True, exist_ok=True)
    with (quality.BUNDLE / ".repair.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another review-quality repair worker holds the lock.")
        try:
            return run()
        except Exception as exc:
            if REPAIR.exists():
                quality.write_json(REPAIR / "fatal_error.json", {
                    "status": "blocked", "at_utc": quality.now(),
                    "error": type(exc).__name__ + ":" + str(exc),
                })
            raise


if __name__ == "__main__":
    raise SystemExit(main())
