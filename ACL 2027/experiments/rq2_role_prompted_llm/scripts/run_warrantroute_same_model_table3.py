#!/usr/bin/env python3
"""Frozen same-model live loops, secondary review-quality audit, Storage export."""

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
from pathlib import Path

import run_warrantroute_loop_n100 as loop
import run_table3_review_quality as quality

ROOT = loop.ROOT
WORKSPACE = loop.WORKSPACE
SCRIPT = Path(__file__).resolve()
CONFIG = ROOT / "config/warrantroute_loop_n100_same_model_v1.json"
PROTOCOL = ROOT / "protocol/warrantroute_same_model_quality_v1.md"
BASE = quality.BUNDLE / "runs/review_quality_n100_20260904_r2"
TABLE = WORKSPACE / "Storage/draft_review_packets/table3_warrantroute_n100_final"
LABELS = {"dreaddit": "Dreaddit", "goemotions": "GoEmotion", "cache": "CaChe", "parlamint-gb": "ParlaMint-GB"}
MODELS = {"qwen_only": "Qwen3 8B", "llama_only": "Llama 3.1 8B", "gemma_only": "Gemma 3 4B"}
SUFFIX = """

FIXED TECHNICAL RESPONSE RULES
Apply every substantive rubric condition above without change. R4 is a valid
review identifier when present. Write each required JSON key exactly once.
Keep each rationale to at most 45 words, below the 60-word validity ceiling.
In rationales use only CLAIM and review IDs present in the payload (R1 through
R4). Refer to source context in words instead of E, S, P, D or U identifiers.
Do not invent identifiers. Return only the required JSON object.
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise quality.ContractError(message)


def seal(path: Path, value: dict, *, immutable: bool = True) -> dict:
    value = {key: item for key, item in value.items() if key != "sha256"}
    value["sha256"] = loop.runtime.digest(value)
    quality.write_json(path, value, immutable=immutable)
    return value


def unseal(path: Path) -> dict:
    value = quality.read_json(path)
    require(value.get("sha256") == loop.runtime.digest({key: item for key, item in value.items() if key != "sha256"}),
            f"record_hash_mismatch:{path}")
    return value


def normalized_runtime(value: dict) -> dict:
    value = dict(value)
    # Ollama can reorder parameter lines without changing any parameter value.
    value["parameters"] = sorted((value.get("parameters") or "").splitlines())
    return value


def prepare(run_dir: Path) -> dict:
    args = argparse.Namespace(command="prepare", config=CONFIG, datasets=None,
                              configurations=None, sample_n=None, methods=None,
                              repetitions=1, run_dir=run_dir)
    loop.prepare(args)
    config, manifest, packets = loop.load_run(run_dir)
    require(manifest["expected_trajectories"] == 1200, "expected_1200_trajectories")
    audit = run_dir / "quality"
    audit.mkdir(mode=0o700)
    source_packets = {}
    for dataset, binding in manifest["datasets"].items():
        source = Path(binding["source_file"])
        require(quality.file_hash(source) == binding["source_sha256"], "source_packet_hash_changed")
        originals = {row["packet_id"]: row for row in loop.read_jsonl(source)}
        source_packets[dataset] = {}
        for packet in packets[dataset]:
            original = originals[packet["packet_id"]]
            require(loop.runtime.packet_payload(original) == loop.runtime.packet_payload(packet), "loop_judge_packet_mismatch")
            context, aliases = quality.sanitize_packet(original)
            source_packets[dataset][packet["packet_id"]] = {"context": context, "aliases": aliases}
    old_design = quality.read_json(BASE / "design_snapshot.json")
    design = {"primary_judge_candidate": old_design["primary_judge_candidate"],
              "proposed_generation": {**old_design["proposed_generation"], "explicit_think": False,
                                      "format": "json_schema"}}
    prompt = (BASE / "prompt_snapshot.txt").read_text()
    prompt = prompt.replace("members R1, R2, or R3", "members R1, R2, R3, or R4")
    prompt = prompt.replace("R1/R2/R3", "R1/R2/R3/R4").rstrip() + SUFFIX
    quality.atomic_write(audit / "prompt.txt", prompt, immutable=True)
    for name, path in {"schema.json": BASE / "schema_snapshot.json", "protocol.md": PROTOCOL,
                       "table_before.csv": TABLE.with_suffix(".csv"),
                       "table_before.md": TABLE.with_suffix(".md")}.items():
        quality.atomic_write(audit / name, path.read_text(), immutable=True)
    quality.write_json(audit / "design.json", design, immutable=True)
    quality.write_json(audit / "packets.private.json", source_packets, immutable=True)
    judge = design["primary_judge_candidate"]
    environment = normalized_runtime(quality.runtime(judge["model_id"]))
    require(environment["model"]["digest"] == judge["observed_local_digest"], "judge_digest_changed")
    sources = [SCRIPT, Path(quality.__file__), Path(quality.repair.__file__),
               Path(quality.reviewer.__file__), Path(quality.detection.__file__), PROTOCOL]
    bindings = [quality.bind(path) for path in sources]
    for path in sources:
        snapshot = audit / "implementation" / path.relative_to(WORKSPACE)
        quality.atomic_write(snapshot, path.read_text(), immutable=True)
        bindings.append(quality.bind(snapshot))
    bindings += [quality.bind(audit / name) for name in (
        "prompt.txt", "schema.json", "protocol.md", "table_before.csv", "table_before.md", "design.json", "packets.private.json")]
    contract = seal(audit / "manifest.json", {
        "protocol": "warrantroute-same-model-review-quality-v1", "created_at": quality.now(),
        "loop_plan_sha256": manifest["plan_sha256"], "bindings": bindings,
        "judge_runtime": environment, "planned_units": 1200, "table_row_count": 48,
        "judge_attempt_limit": 3, "human_audit_status": "pending", "manuscript_eligible": False,
        "original_table_hashes": {ext: quality.file_hash(TABLE.with_suffix('.' + ext)) for ext in ("csv", "md")},
    })
    return {"status": "prepared", "run_dir": str(run_dir), "quality_contract": contract["sha256"],
            "trajectories": 1200, "quality_units": 1200, "new_model_calls": 0}


def load(run_dir: Path):
    config, manifest, packets = loop.load_run(run_dir)
    audit = run_dir / "quality"
    contract = unseal(audit / "manifest.json")
    require(contract["loop_plan_sha256"] == manifest["plan_sha256"], "quality_loop_plan_mismatch")
    quality.check_hashes(contract["bindings"])
    return config, manifest, packets, contract


def make_unit(job: tuple, result: dict, inputs: dict, config: dict) -> dict:
    dataset, seed, name, method, packet = job
    rows = [row for row in result["audit_history"] if row["stage"] == "initial"]
    ratings = {row["role"]: row["report"]["rating"] for row in rows}
    required = set(loop.runtime.required_initial_roles(result["route"]))
    complete = required == set(ratings) and len(rows) == len(ratings)
    stored = inputs[dataset][packet["packet_id"]]
    payload = quality.review_bundle(packet, stored["context"], stored["aliases"], ratings, list(ratings))
    unit = {"dataset": dataset, "corpus_id": packet["corpus_id"], "packet_id": packet["packet_id"],
            "configuration": name, "seed": seed, "method": "WarrantRoute",
            "reviewer_model_id": config["configurations"][name]["proposer"],
            "loop_result_sha256": result["result_sha256"], "initial_bundle_complete": complete,
            "payload": payload}
    unit["unit_id"] = loop.runtime.digest([dataset, seed, name, method, packet["packet_id"]])
    return unit


def judge_request(audit: Path, unit: dict, design: dict, schema: dict) -> dict:
    request = quality.make_request(design, (audit / "prompt.txt").read_text(), schema, unit["payload"])
    request["format"] = schema
    return request


def judge_one(audit: Path, contract: dict, unit: dict, design: dict, schema: dict) -> dict:
    directory = audit / "units" / unit["unit_id"]
    request = judge_request(audit, unit, design, schema)
    request_hash = loop.runtime.digest(request)
    identity = {"unit_id": unit["unit_id"], "contract_sha256": contract["sha256"],
                "request_sha256": request_hash, "unit_sha256": loop.runtime.digest(unit)}
    final_path = directory / "result.json"
    if final_path.exists():
        final = unseal(final_path)
        require(all(final.get(key) == value for key, value in identity.items()), "saved_quality_identity_mismatch")
        if final["status"] == "valid":
            decision, errors = quality.validate_response(final["response"], unit, schema,
                                                         design["proposed_generation"], request["model"])
            require(not errors and decision == final["decision"], "saved_quality_validation_failed")
        return final
    input_path = directory / "input.private.json"
    if input_path.exists():
        require(unseal(input_path)["unit"] == unit, "quality_input_changed")
    else:
        seal(input_path, {"unit": unit, "request": request})
    if not unit["initial_bundle_complete"]:
        return seal(final_path, {**identity, "status": "missing_initial_reviews", "decision": None})
    generation = design["proposed_generation"]
    for number in range(1, contract["judge_attempt_limit"] + 1):
        attempt_path = directory / "attempts" / f"{number:02d}.json"
        if attempt_path.exists():
            record = unseal(attempt_path)
            require(all(record.get(key) == value for key, value in identity.items()), "attempt_identity_changed")
            if record["status"] == "in_flight":
                seal(directory / "attempts" / f"{number:02d}.interrupted.json",
                     {**identity, "status": "interrupted_outcome_unknown"}, immutable=not (directory / "attempts" / f"{number:02d}.interrupted.json").exists())
            if record["status"] != "valid":
                continue
        else:
            record = {**identity, "attempt": number, "status": "in_flight", "started_at": quality.now()}
            seal(attempt_path, record)
            start = time.monotonic()
            try:
                position = quality.log_position()
                response = quality.api("generate", request, timeout=generation["timeout_seconds"])
                record["response"] = response
                decision, errors = quality.validate_response(response, unit, schema, generation, request["model"])
                if quality.truncation_since(position):
                    errors.append("server_reported_context_truncation")
                record.update(status="schema_error" if errors else "valid", decision=decision, errors=errors)
            except Exception as exc:
                record.update(status="transport_error", errors=[f"{type(exc).__name__}:{str(exc)[:300]}"])
            record["wall_seconds"] = time.monotonic() - start
            record["completed_at"] = quality.now()
            seal(attempt_path, record, immutable=False)
        if record["status"] == "valid":
            decision, errors = quality.validate_response(record["response"], unit, schema, generation, request["model"])
            require(not errors and decision == record["decision"], "cached_attempt_validation_failed")
            return seal(final_path, record)
    return seal(final_path, {**identity, "status": "technical_attempts_exhausted", "decision": None})


def inventory(run_dir: Path, manifest: dict, packets: dict):
    results = []
    for job in loop.jobs(manifest, packets):
        path = loop.result_dir(run_dir, *job) / "result.json"
        if path.exists():
            results.append((job, loop.read_result(path, manifest, *job)))
    return results


def technical_failure(result: dict) -> bool:
    return (result.get("error") or "").startswith(("CallFailure:", "ValueError:", "ValidationError:", "TightLoopContractError:"))


def status(run_dir: Path) -> dict:
    _config, manifest, packets, _contract = load(run_dir)
    results = inventory(run_dir, manifest, packets)
    cells = []
    for dataset in manifest["datasets"]:
        for name in manifest["configurations"]:
            selected = [result for job, result in results if job[0] == dataset and job[2] == name]
            cells.append({"dataset": dataset, "configuration": name, "completed": len(selected),
                          "technical_failures": sum(map(technical_failure, selected))})
    quality_results = [unseal(path) for path in (run_dir / "quality/units").glob("*/result.json")]
    by_model = {}
    for name in manifest["configurations"]:
        selected = [row["cost"]["wall_seconds"] for job, row in results if job[2] == name]
        by_model[name] = {"remaining": 400 - len(selected),
                          "observed_mean_seconds": statistics.mean(selected) if selected else None}
    loop_eta = (sum(row["remaining"] * row["observed_mean_seconds"] for row in by_model.values())
                if all(row["observed_mean_seconds"] is not None for row in by_model.values()) else None)
    judge_times = [row["wall_seconds"] for row in quality_results if row.get("wall_seconds")]
    return {"updated_at": quality.now(), "completed_trajectories": len(results), "expected_trajectories": 1200,
            "loop_progress_percent": round(len(results) / 12, 2), "cells": cells,
            "quality_terminal_units": len(quality_results),
            "quality_binary_pairs": sum(all(type((row.get("decision") or {}).get(m)) is bool for m in quality.METRICS)
                                        for row in quality_results),
            "remaining_by_model": by_model,
            "loop_eta_hours_extrapolated": loop_eta / 3600 if loop_eta is not None else None,
            "quality_eta_hours_extrapolated": ((1200 - len(quality_results)) * statistics.mean(judge_times) / 3600
                                               if judge_times else None),
            "eta_note": "Early means may be unstable; loop ETA excludes judging and scoring.",
            "manuscript_eligible": False}


def export_rows(original: list[list[str]], metrics: list[dict], summary: dict) -> list[list[str]]:
    require(len(original) == 49 and len({tuple(row[:3]) for row in original[1:]}) == 48, "invalid_table_inventory")
    require(len(metrics) == 12 and len(summary["rows"]) == 12, "missing_comparison_cells")
    output = [list(row) for row in original]
    detections = {(LABELS[row["dataset"]], MODELS[row["configuration"]]): row for row in metrics}
    judged = {(quality.detection.DATASET_LABELS[row["corpus_id"]], quality.detection.MODEL_LABELS[row["reviewer_model_id"]]): row
              for row in summary["rows"]}
    changed = 0
    for row in output[1:]:
        if row[1] != "WarrantRoute":
            continue
        key = (row[0], row[2])
        detection, audit = detections[key], judged[key]
        require(detection["n"] == audit["planned"] == 100, "row_denominator_mismatch")
        row[3] = f"{detection['tp']}/100"
        ci = detection["recall_cluster_interval"]
        row[4] = f"{100 * detection['recall']:.1f}" + (f" [{100 * ci[0]:.1f}, {100 * ci[1]:.1f}]" if ci else " [CI N/A]")
        for index, metric in enumerate(quality.METRICS, 5):
            counts = audit[metric]
            require(sum(counts[key] for key in ("true", "false", "unresolved")) == 100, "metric_counts_do_not_sum_to_100")
            row[index] = "N/A" if counts["percent"] is None else f"{counts['percent']:.1f}"
        changed += 1
    require(changed == 12, "expected_12_warrantroute_rows")
    require([r for r in original[1:] if r[1] != "WarrantRoute"] == [r for r in output[1:] if r[1] != "WarrantRoute"],
            "baseline_rows_changed")
    return output


def export(run_dir: Path, manifest: dict, contract: dict, summary: dict) -> dict:
    audit = run_dir / "quality"
    comparison = quality.read_json(run_dir / "comparison.json")
    original = list(csv.reader(io.StringIO((audit / "table_before.csv").read_text())))
    rows = export_rows(original, comparison["metrics"], summary)
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
        "not independent repair quality. All 100 decisions must be binary for a percentage. "
        "N/A retains unresolved cases, detailed in the linked summary. Human validation is pending.\n\n"
        f"[Run manifest]({run_dir / 'manifest.json'}) | "
        f"[Quality summary]({audit / 'summary.json'}) | [Protocol]({audit / 'protocol.md'})\n\n"
        "Private working packets with controlled flaw templates; not manuscript-eligible. "
        "Historical baseline comparisons are not a newly matched prompt experiment.\n\n"
        "## Historical Table Notes (Superseded for WarrantRoute)\n\n" + historical_notes + "\n")
    targets = {"csv": csv_text, "md": md_text}
    journal_path = audit / "export_plan.json"
    hashes = {ext: quality.digest(text.encode()) for ext, text in targets.items()}
    if journal_path.exists():
        require(unseal(journal_path)["after"] == hashes, "export_content_changed")
    else:
        seal(journal_path, {"before": contract["original_table_hashes"], "after": hashes})
    # Check both files before replacing either; resume allows either old or new hash.
    for ext in targets:
        require(quality.file_hash(TABLE.with_suffix('.' + ext)) in {hashes[ext], contract["original_table_hashes"][ext]},
                f"concurrent_table_edit:{ext}")
    for ext, content in targets.items():
        quality.atomic_write(audit / f"table3_export.{ext}", content)
        quality.atomic_write(TABLE.with_suffix('.' + ext), content)
        require(quality.file_hash(TABLE.with_suffix('.' + ext)) == hashes[ext], "export_verification_failed")
    final = {"status": "export_verified_complete" if summary["completed_binary_pairs"] == 1200 else "completed_with_unresolved_quality",
             "completed_at": quality.now(), "table_row_count": 48, "replaced_warrantroute_rows": 12,
             "preserved_baseline_rows": 36, "loop_plan_sha256": manifest["plan_sha256"],
             "quality_contract_sha256": contract["sha256"], "table_hashes": hashes,
             "quality_binary_pairs": summary["completed_binary_pairs"], "human_audit_status": "pending",
             "manuscript_eligible": False}
    return seal(audit / "final_manifest.json", final, immutable=False)


def run(run_dir: Path) -> dict:
    config, manifest, packets, contract = load(run_dir)
    audit = run_dir / "quality"
    design = quality.read_json(audit / "design.json")
    schema = quality.read_json(audit / "schema.json")
    inputs = quality.read_json(audit / "packets.private.json")
    judge = design["primary_judge_candidate"]["model_id"]
    with (run_dir / "table3_supervisor.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(normalized_runtime(quality.runtime(judge)) == contract["judge_runtime"], "judge_runtime_changed")
        while True:
            current = loop.progress(run_dir, manifest, packets)
            results = inventory(run_dir, manifest, packets)
            if len(results) <= 12:
                failed_judgments = 0
                for job, result in results:
                    unit = make_unit(job, result, inputs, config)
                    record = judge_one(audit, contract, unit, design, schema)
                    failed_judgments += record["status"] == "technical_attempts_exhausted"
                require(failed_judgments < 5, "quality_canary_technical_failure")
            if len(results) >= 12:
                require(sum(technical_failure(row) for _, row in results[:12]) < 3,
                        "technical_canary_failed:inspect_preserved_results_before_new_run")
            if current["status"] == "complete":
                break
            load(run_dir)
            loop.execute(argparse.Namespace(run_dir=run_dir, max_packets=1))
            report = status(run_dir)
            quality.write_json(run_dir / "table3_progress.json", report)
            print(json.dumps({"phase": "loop", **report}), flush=True)
        loop.score(argparse.Namespace(run_dir=run_dir))
        require(normalized_runtime(quality.runtime(judge)) == contract["judge_runtime"], "judge_runtime_changed")
        units, records, human = [], {}, []
        human_ids = {dataset: set(sorted(rows, key=lambda pid: loop.runtime.digest([20260904, dataset, pid]))[:10])
                     for dataset, rows in inputs.items()}
        results = inventory(run_dir, manifest, packets)
        results.sort(key=lambda pair: loop.runtime.digest([20260904, pair[0][0], pair[0][2], pair[0][4]["packet_id"]]))
        consecutive_failures = 0
        for job, result in results:
            unit = make_unit(job, result, inputs, config)
            record = judge_one(audit, contract, unit, design, schema)
            units.append(unit)
            records[unit["unit_id"]] = record
            if unit["packet_id"] in human_ids[unit["dataset"]]:
                human.append({"audit_id": unit["unit_id"], "payload": unit["payload"], "human_assessment": None})
            consecutive_failures = consecutive_failures + 1 if record["status"] == "technical_attempts_exhausted" else 0
            summary = quality.summarize(units, records)
            summary.update(status="in_progress", total_planned_units=1200, human_audit_status="pending")
            quality.write_json(audit / "summary.partial.json", summary)
            print(json.dumps({"phase": "quality", "processed_units": len(units), "planned_units": 1200,
                              "binary_pairs": summary["completed_binary_pairs"], "last_status": record["status"]}), flush=True)
            require(consecutive_failures < 5, "repeated_judge_technical_failure")
            if len(units) % 100 == 0:
                load(run_dir)
                require(normalized_runtime(quality.runtime(judge)) == contract["judge_runtime"], "judge_runtime_changed")
                quality.write_json(run_dir / "table3_progress.json", status(run_dir))
        require(len(units) == 1200 and len(records) == 1200 and len(human) == 120, "final_quality_inventory_mismatch")
        summary = quality.summarize(units, records)
        summary.update(status="all_planned_units_terminal", human_audit_status="pending", manuscript_eligible=False)
        quality.write_json(audit / "summary.json", summary)
        quality.write_json(audit / "human_audit.private.json", {"status": "pending", "units": human})
        load(run_dir)
        final = export(run_dir, manifest, contract, summary)
        quality.write_json(run_dir / "table3_progress.json", status(run_dir))
        return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "status"))
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = quality.inside_storage(args.run_dir)
    try:
        output = {"prepare": prepare, "run": run, "status": status}[args.command](run_dir)
        print(json.dumps(output, indent=2), flush=True)
        return 0
    except Exception as exc:
        failure = {"status": "blocked", "at": quality.now(), "error": f"{type(exc).__name__}:{str(exc)[:500]}"}
        if args.command == "run" and run_dir.exists():
            quality.write_json(run_dir / "table3_supervisor_error.json", failure)
        print(json.dumps(failure), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
