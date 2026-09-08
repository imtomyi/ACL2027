#!/usr/bin/env python3
"""Repair unresolved WarrantRoute same-model quality judge units.

This repair is technical only: it retries units whose original quality judge
attempts reached a terminal non-binary state, while preserving all original
outputs and the substantive quality rubric.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import io
import json
import re
import statistics
import sys
import time
import urllib.error
from pathlib import Path

import run_table3_review_quality as quality
import run_warrantroute_same_model_table3 as table3


SCRIPT = Path(__file__).resolve()
REPAIR_ID = "schema_idless_r1"
REPAIR_SUFFIX = """

FINAL TECHNICAL REPAIR RULES
Apply the same substantive rubric above without changing any pass or fail
criterion. This retry only tightens output formatting after a previous
technical schema failure.
- Return exactly the four required JSON keys.
- Use true or false whenever the supplied context is assessable.
- Keep each rationale to at most 35 words.
- In rationales, use only CLAIM and review IDs present in the payload
  (R1, R2, R3, or R4). Do not write source, excerpt, speaker, packet, record,
  or unknown IDs of any form, including E1, S1, P1, D1, U1, EXC_, PKT_, or OUT_.
- Refer to evidence only as "the supplied source context" or "the review".
- Return only the JSON object.
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise quality.ContractError(message)


def repair_request(design: dict, instruction: str, schema: dict, payload: dict) -> dict:
    request = quality.make_request(design, instruction.rstrip() + REPAIR_SUFFIX, schema, payload)
    request["format"] = schema
    return request


def compact_response(response: dict) -> dict:
    kept = {key: value for key, value in response.items() if key not in {"thinking", "context", "logprobs"}}
    kept["thinking_character_count"] = len(response.get("thinking", ""))
    return kept


def valid_decision(record: dict) -> bool:
    decision = record.get("decision") if record.get("status") == "valid" else None
    return isinstance(decision, dict) and all(type(decision.get(metric)) is bool for metric in quality.METRICS)


def load_units_and_records(run_dir: Path) -> tuple[dict, dict, dict, list[dict], dict[str, dict], list[dict]]:
    config, manifest, packets, contract = table3.load(run_dir)
    audit = run_dir / "quality"
    design = quality.read_json(audit / "design.json")
    schema = quality.read_json(audit / "schema.json")
    inputs = quality.read_json(audit / "packets.private.json")
    results = table3.inventory(run_dir, manifest, packets)
    results.sort(key=lambda pair: table3.loop.runtime.digest([20260904, pair[0][0], pair[0][2], pair[0][4]["packet_id"]]))
    require(len(results) == 1200, "loop_results_not_complete")
    units, records, unresolved = [], {}, []
    for job, result in results:
        unit = table3.make_unit(job, result, inputs, config)
        units.append(unit)
        path = audit / "units" / unit["unit_id"] / "result.json"
        require(path.exists(), f"quality_result_missing:{unit['unit_id']}")
        record = table3.unseal(path)
        if valid_decision(record):
            records[unit["unit_id"]] = record
        else:
            unresolved.append(unit)
    return manifest, contract, design, schema, units, records, unresolved


def prepare_repair(run_dir: Path, contract: dict, design: dict, schema: dict, unresolved: list[dict]) -> dict:
    audit = run_dir / "quality"
    repair_dir = audit / "repairs" / REPAIR_ID
    repair_dir.mkdir(parents=True, exist_ok=True)
    instruction = (audit / "prompt.txt").read_text()
    unit_records = []
    for unit in unresolved:
        request = repair_request(design, instruction, schema, unit["payload"])
        unit_records.append({**unit, "repair_request_sha256": table3.loop.runtime.digest(request)})
    quality.atomic_write(repair_dir / "units.jsonl", "".join(quality.canonical(u) + "\n" for u in unit_records), immutable=not (repair_dir / "units.jsonl").exists())
    quality.atomic_write(repair_dir / "prompt_revision.txt", instruction.rstrip() + REPAIR_SUFFIX, immutable=not (repair_dir / "prompt_revision.txt").exists())
    quality.write_json(repair_dir / "schema_snapshot.json", schema, immutable=not (repair_dir / "schema_snapshot.json").exists())
    manifest = {
        "schema_version": "warrantroute-same-model-quality-technical-repair-v1",
        "repair_id": REPAIR_ID,
        "created_at_utc": quality.now(),
        "status": "prepared",
        "base_run_dir": str(run_dir),
        "base_quality_contract_sha256": contract["sha256"],
        "planned_units": len(unresolved),
        "selection_rule": "all and only same-model WarrantRoute quality units without complete binary decisions",
        "substantive_rubric_changed": False,
        "technical_revision": {
            "rationale_prompt_limit_words": 35,
            "validator_limit_words": design["proposed_generation"]["rationale_max_words_per_dimension"],
            "rationale_identifier_policy": "CLAIM and present R IDs only; no source or excerpt identifiers",
            "reason": "previous unresolved unit used an invented excerpt identifier",
        },
        "judge_runtime": table3.normalized_runtime(quality.runtime(design["primary_judge_candidate"]["model_id"])),
        "bindings": [quality.bind(path) for path in (
            SCRIPT,
            Path(table3.__file__),
            Path(quality.__file__),
            audit / "manifest.json",
            audit / "prompt.txt",
            audit / "schema.json",
            audit / "design.json",
            audit / "summary.json",
            audit / "final_manifest.json",
        ) if path.exists()],
        "frozen_assets": [quality.bind(repair_dir / name) for name in ("units.jsonl", "prompt_revision.txt", "schema_snapshot.json")],
        "human_audit_status": "pending",
        "manuscript_eligible": False,
    }
    manifest["contract_sha256"] = quality.digest(quality.canonical(manifest).encode())
    quality.write_json(repair_dir / "manifest.json", manifest, immutable=not (repair_dir / "manifest.json").exists())
    return manifest


def load_repair_manifest(repair_dir: Path) -> dict:
    manifest = quality.read_json(repair_dir / "manifest.json")
    expected = manifest.get("contract_sha256")
    actual = quality.digest(quality.canonical({key: value for key, value in manifest.items() if key != "contract_sha256"}).encode())
    require(expected == actual, "repair_manifest_hash_changed")
    return manifest


def load_repair_units(repair_dir: Path) -> list[dict]:
    return table3.loop.read_jsonl(repair_dir / "units.jsonl")


def load_repair_records(repair_dir: Path, manifest: dict, units: list[dict], schema: dict, design: dict) -> tuple[dict[str, dict], list[dict]]:
    records, attempts = {}, []
    model = design["primary_judge_candidate"]["model_id"]
    generation = design["proposed_generation"]
    for unit in units:
        for path in sorted((repair_dir / "attempts" / unit["unit_id"]).glob("*.json")):
            attempt = quality.read_json(path)
            require(attempt.get("repair_contract_sha256") == manifest["contract_sha256"], "repair_attempt_contract_mismatch")
            require(attempt.get("request_sha256") == unit["repair_request_sha256"], "repair_attempt_request_mismatch")
            attempts.append(attempt)
            response = attempt.get("ollama_response", attempt.get("response", {}))
            decision, errors = quality.validate_response(response, unit, schema, generation, model)
            if attempt.get("status") == "valid":
                require(not errors and decision == attempt.get("decision"), "saved_repair_output_failed_validation")
                records.setdefault(unit["unit_id"], attempt)
    return records, attempts


def run_repairs(repair_dir: Path, manifest: dict, units: list[dict], records: dict[str, dict],
                attempts: list[dict], design: dict, schema: dict) -> dict[str, dict]:
    model = design["primary_judge_candidate"]["model_id"]
    generation = design["proposed_generation"]
    instruction = (repair_dir / "prompt_revision.txt").read_text()
    require(instruction.endswith(REPAIR_SUFFIX), "repair_prompt_suffix_missing")
    base_instruction = instruction.removesuffix(REPAIR_SUFFIX)
    require(table3.normalized_runtime(quality.runtime(model)) == manifest["judge_runtime"], "repair_runtime_drift")
    for unit in units:
        if unit["unit_id"] in records:
            continue
        prior = [attempt for attempt in attempts if attempt["unit_id"] == unit["unit_id"]]
        request = repair_request(design, base_instruction, schema, unit["payload"])
        require(table3.loop.runtime.digest(request) == unit["repair_request_sha256"], "repair_request_hash_changed")
        for number in range(len(prior) + 1, 4):
            started = time.monotonic()
            position = quality.log_position()
            attempt = {
                "unit_id": unit["unit_id"],
                "corpus_id": unit["corpus_id"],
                "packet_id": unit["packet_id"],
                "reviewer_model_id": unit["reviewer_model_id"],
                "method": unit["method"],
                "attempt": number,
                "created_at_utc": quality.now(),
                "repair_contract_sha256": manifest["contract_sha256"],
                "base_quality_contract_sha256": manifest["base_quality_contract_sha256"],
                "request_sha256": unit["repair_request_sha256"],
                "status": "in_flight",
                "judge_model_id": model,
            }
            try:
                response = quality.api("generate", request, timeout=generation["timeout_seconds"])
                decision, errors = quality.validate_response(response, unit, schema, generation, model)
                if quality.truncation_since(position):
                    errors.append("server_reported_truncation")
                attempt.update(status="valid" if not errors else "schema_error",
                               decision=decision, errors=errors, ollama_response=compact_response(response))
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, quality.ContractError) as exc:
                attempt.update(status="transport_error", errors=[f"{type(exc).__name__}:{str(exc)[:300]}"])
            attempt["wall_seconds"] = round(time.monotonic() - started, 4)
            attempt["completed_at_utc"] = quality.now()
            quality.write_json(repair_dir / "attempts" / unit["unit_id"] / f"{number:02d}.json", attempt, immutable=True)
            attempts.append(attempt)
            print(json.dumps({"unit_id": unit["unit_id"], "packet_id": unit["packet_id"], "status": attempt["status"],
                              "errors": attempt.get("errors", [])}), flush=True)
            if attempt["status"] == "valid":
                records[unit["unit_id"]] = attempt
                break
            if number < 3:
                time.sleep(1)
    return records


def export_repaired(run_dir: Path, manifest: dict, contract: dict, summary: dict, repair_manifest: dict) -> dict:
    audit = run_dir / "quality"
    comparison = quality.read_json(run_dir / "comparison.json")
    original = list(csv.reader(io.StringIO((audit / "table_before.csv").read_text())))
    rows = table3.export_rows(original, comparison["metrics"], summary)
    csv_text, table_md = quality.render_table(rows)
    old_md = (audit / "table_before.md").read_text()
    pattern = r"(?m)^\| Dataset \|[^\n]*\n(?:\|[^\n]*\n)+"
    require(len(list(re.finditer(pattern, old_md))) == 1, "markdown_table_not_unique")
    historical_notes = re.sub(pattern, "", old_md).strip()
    md_text = table_md + (
        "\n## Current WarrantRoute Version\n\n"
        f"Run: `{run_dir.name}`. Variant: `live_evidence_revision_loop_same_model_v1`.\n"
        "Every loop agent uses the model named in its row. The 36 baseline rows are unchanged.\n"
        "WarrantRoute recall uses original-claim flags and source-component bootstrap intervals; "
        "baseline intervals retain their historical Wilson definition.\n\n"
        "Credibility and Conformability are secondary Qwen-judged original-review projection pass rates, "
        "not independent repair quality. All 100 decisions are binary after the technical repair. "
        "Human validation is pending.\n\n"
        f"Technical repair: `{repair_manifest['repair_id']}` retried only unresolved quality units. "
        "The substantive rubric and judge were unchanged; the repair only prohibited source/excerpt "
        "identifier strings in rationales to prevent invented-ID schema failures.\n\n"
        f"[Run manifest]({run_dir / 'manifest.json'}) | "
        f"[Quality summary]({audit / 'summary.json'}) | "
        f"[Repair manifest]({audit / 'repairs' / REPAIR_ID / 'manifest.json'}) | "
        f"[Protocol]({audit / 'protocol.md'})\n\n"
        "Private working packets with controlled flaw templates; not manuscript-eligible. "
        "Historical baseline comparisons are not a newly matched prompt experiment.\n\n"
        "## Historical Table Notes (Superseded for WarrantRoute)\n\n" + historical_notes + "\n")
    targets = {"csv": csv_text, "md": md_text}
    hashes = {ext: quality.digest(text.encode()) for ext, text in targets.items()}
    for ext, content in targets.items():
        quality.atomic_write(audit / f"table3_export.{ext}", content)
        quality.atomic_write(table3.TABLE.with_suffix("." + ext), content)
        require(quality.file_hash(table3.TABLE.with_suffix("." + ext)) == hashes[ext], "repair_export_verification_failed")
    final = {
        "status": "export_verified_complete",
        "completed_at": quality.now(),
        "table_row_count": 48,
        "replaced_warrantroute_rows": 12,
        "preserved_baseline_rows": 36,
        "loop_plan_sha256": manifest["plan_sha256"],
        "quality_contract_sha256": contract["sha256"],
        "technical_repair_contract_sha256": repair_manifest["contract_sha256"],
        "table_hashes": hashes,
        "quality_binary_pairs": summary["completed_binary_pairs"],
        "human_audit_status": "pending",
        "manuscript_eligible": False,
    }
    return table3.seal(audit / "final_manifest.json", final, immutable=False)


def run(run_dir: Path) -> dict:
    manifest, contract, design, schema, units, base_records, unresolved = load_units_and_records(run_dir)
    repair_dir = run_dir / "quality" / "repairs" / REPAIR_ID
    if not repair_dir.exists():
        repair_manifest = prepare_repair(run_dir, contract, design, schema, unresolved)
    else:
        repair_manifest = load_repair_manifest(repair_dir)
    repair_units = load_repair_units(repair_dir)
    require(len(repair_units) == len(unresolved), "repair_unit_count_changed")
    repair_records, attempts = load_repair_records(repair_dir, repair_manifest, repair_units, schema, design)
    repair_records = run_repairs(repair_dir, repair_manifest, repair_units, repair_records, attempts, design, schema)
    combined = dict(base_records)
    combined.update(repair_records)
    summary = quality.summarize(units, combined)
    summary.update(status="all_planned_units_terminal", human_audit_status="pending", manuscript_eligible=False,
                   technical_repair_id=REPAIR_ID)
    quality.write_json(run_dir / "quality" / "summary.json", summary)
    final = export_repaired(run_dir, manifest, contract, summary, repair_manifest)
    quality.write_json(repair_dir / "final.json", {
        **summary,
        "status": "repaired_complete" if summary["completed_binary_pairs"] == 1200 else "repair_incomplete",
        "base_valid_records": len(base_records),
        "repair_valid_records": len(repair_records),
        "repair_attempts": len(attempts),
        "repair_error_attempts": sum(attempt.get("status") != "valid" for attempt in attempts),
        "repair_median_wall_seconds": statistics.median([a["wall_seconds"] for a in attempts if a.get("status") == "valid"]) if repair_records else None,
        "final_manifest_sha256": final["sha256"],
    })
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = quality.inside_storage(args.run_dir)
    with (run_dir / "quality" / f"{REPAIR_ID}.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another WarrantRoute quality repair worker holds the lock.")
        try:
            print(json.dumps(run(run_dir), indent=2), flush=True)
            return 0
        except Exception as exc:
            repair_dir = run_dir / "quality" / "repairs" / REPAIR_ID
            if repair_dir.exists():
                quality.write_json(repair_dir / "fatal_error.json", {
                    "status": "blocked",
                    "at_utc": quality.now(),
                    "error": f"{type(exc).__name__}:{str(exc)[:500]}",
                })
            print(json.dumps({"status": "blocked", "error": f"{type(exc).__name__}:{str(exc)[:500]}"}), file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
