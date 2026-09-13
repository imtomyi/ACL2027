"""Bounded, local-only TA generation for the existing 12-paragraph Dreaddit panel."""

import argparse
import csv
import fcntl
import io
import json
from pathlib import Path
import shutil
import time
import urllib.request

import run_dreaddit_paragraph_playbook_smoke as smoke
import ta_generation_contract as contract

runtime = smoke.runtime
PROJECT = runtime.legacy.PROJECT
STORAGE = (PROJECT / "Storage").resolve()
CODE = list(dict.fromkeys([*smoke.CODE, "ta_generation_contract.py", Path(__file__).name]))
PROTOCOL = "Storage/experiment_guidelines/ta_generation_12_smoke_v1.md"


def check_files(folder, manifest):
    for name, expected in manifest["files"].items():
        path = (folder / name).resolve()
        runtime.require(path.is_relative_to(folder), "manifest_path_escape")
        runtime.require(runtime.file_hash(path) == expected, "frozen_file_changed:" + name)


def select_packets(rows, bank):
    runtime.require(len(rows) == 12, "exactly_twelve_paragraphs_required")
    parents = {p["packet_id"]: p for p in bank["dreaddit"]["development"]}
    excluded = [e for p in bank["dreaddit"]["evaluation"] for e in p["task"]["evidence"]]
    groups, seen_records, seen_text = {}, set(), set()
    norm = lambda s: " ".join(s.casefold().split())
    for row in rows:
        runtime.require(runtime.digest(row["task"]) == row["task_sha256"], "source_task_changed")
        runtime.require(len(row["task"]["evidence"]) == 1, "one_paragraph_per_point")
        e = row["task"]["evidence"][0]
        rid, text = e["source_record_id"], e["text"]
        runtime.require(text == row["task"]["claim"] and rid == row["source_record_id"], "paragraph_binding")
        runtime.require(rid not in seen_records and norm(text) not in seen_text, "duplicate_record_or_text")
        runtime.require(all(rid != x["source_record_id"] and e["source_id"] != x["source_id"]
                            and norm(text) != norm(x["text"]) for x in excluded), "evaluation_overlap")
        parent = parents[row["parent_packet_id"]]
        original = next(x for x in parent["task"]["evidence"] if x["source_record_id"] == rid)
        runtime.require(original["metadata"]["split"] == "development_train", "development_only")
        runtime.require(runtime.digest(original) == row["source_excerpt_sha256"], "source_excerpt_changed")
        visible = {k: original[k] for k in ("source_record_id", "source_id", "excerpt_id", "text")}
        runtime.require(visible == e, "original_text_or_identity_changed")
        groups.setdefault(parent["packet_id"], []).append(visible)
        seen_records.add(rid)
        seen_text.add(norm(text))
    runtime.require(len(groups) == 3 and all(len(v) == 4 for v in groups.values()), "preserve_three_parent_packets")
    packets = []
    for pid, sources in groups.items():
        original = parents[pid]["task"]["evidence"]
        runtime.require({e["source_record_id"] for e in sources} == {e["source_record_id"] for e in original}, "partial_parent_packet")
        order = {e["source_record_id"]: i for i, e in enumerate(original)}
        sources.sort(key=lambda e: order[e["source_record_id"]])
        packets.append({"artifact_id": "TA_" + pid, "parent_packet_id": pid,
                        "sources": sources, "source_packet_sha256": runtime.digest(sources)})
    return packets


def prepare(run, source):
    runtime.require(run.is_relative_to(STORAGE) and source.is_relative_to(STORAGE), "private_storage_only")
    for name in ("manifest.json", "final_manifest.json"):
        check_files(source, runtime.read(source / name))
    prior = runtime.read(source / "config.json")
    upstream = Path(prior["source_run"]).resolve()
    runtime.require(upstream.is_relative_to(STORAGE), "private_upstream_only")
    check_files(upstream, runtime.read(upstream / "manifest.json"))
    packets = select_packets(runtime.read(source / "inputs.private.json"), runtime.read(upstream / "inputs.private.json"))
    config = {"protocol": contract.VERSION, "source_run": str(source), "upstream_run": str(upstream),
        "model": "gemma3:4b", "model_digest": prior["model_digest"],
        "options": {**prior["options"], "num_predict": 8192},
        "base_url": runtime.legacy.BASE, "paid_api_allowed": False, "manuscript_eligible": False,
        "paragraph_n": 12, "analysis_packet_n": 3, "generation_repeats": 1,
        "call_ceiling": 3, "budget_seconds": 1200, "timeout_seconds": 300,
        "research_question": contract.QUESTION, "analytic_contract": contract.ORIENTATION,
        "research_question_source": "experiments/rq2_role_prompted_llm/scripts/build_working_dreaddit_packet_bank.py",
        "authorization": "User requested a codes-and-themes test run with 12 data points.",
        "selection": "Same previously exposed 12 Dreaddit development paragraphs; preserve all three original four-record packet memberships and order.",
        "scope": "TA construction only. No flaw detection, quality judging, Playbook updates or epochs. Not manuscript evidence.",
        "source_files": {str(p): runtime.file_hash(p) for p in
            (source / "inputs.private.json", source / "manifest.json", source / "final_manifest.json", upstream / "inputs.private.json")}}
    for packet in packets:
        contract.request(config, packet)
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inputs.private.json", packets),
                         ("prompts.json", {"ta_analyst": contract.PROMPT}), ("schema.json", contract.SCHEMA)):
        runtime.write_json(run / name, value)
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    shutil.copyfile(PROJECT / PROTOCOL, run / "protocol.md")
    runtime.write_json(run / "manifest.json", {"protocol": contract.VERSION, "created_at": runtime.legacy.now(),
        "files": {p.name: runtime.file_hash(p) for p in run.iterdir() if p.is_file()}})
    return report(run, "prepared_not_started")


def verify(run):
    runtime.require(run.is_relative_to(STORAGE), "private_storage_only")
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["protocol"] == contract.VERSION, "wrong_protocol")
    check_files(run, manifest)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name], "source_code_changed:" + name)
    for name, expected in runtime.read(run / "config.json")["source_files"].items():
        runtime.require(runtime.file_hash(Path(name)) == expected, "input_provenance_changed")
    if (run / "final_manifest.json").exists():
        check_files(run, runtime.read(run / "final_manifest.json"))


def generate(run, config, packet, deadline):
    key = packet["artifact_id"]
    folder = run / "calls" / key
    output = run / "ta_artifacts" / key
    req, bound = contract.request(config, packet)
    sent, received = folder / "request.json", folder / "response.json"
    if sent.exists():
        runtime.require(runtime.read(sent)["request_sha256"] == runtime.digest(req), "call_identity_changed")
        if not received.exists():
            raise runtime.AmbiguousCall("missing_response_no_retry:" + key)
        response = runtime.read(received)
    else:
        if deadline - time.time() < config["timeout_seconds"] + 1:
            raise runtime.BudgetStop("not_enough_time_for_next_call")
        runtime.require(len(list((run / "calls").glob("*/request.json"))) < config["call_ceiling"], "call_ceiling")
        runtime.write_json(sent, {"request": req, "request_sha256": runtime.digest(req),
            "started_at": runtime.legacy.now(), "conservative_context_bound": bound})
        runtime.write_json(run / "active_call.json", {"artifact_id": key, "status": "running", "at": runtime.legacy.now()}, replace=True)
        start = time.monotonic()
        try:
            request = urllib.request.Request(config["base_url"] + "/api/generate", json.dumps(req).encode(),
                                             {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=config["timeout_seconds"]) as handle:
                body = json.load(handle)
        except Exception as exc:
            runtime.write_json(folder / "transport_error.json", {"at": runtime.legacy.now(), "error": str(exc)})
            raise runtime.AmbiguousCall("transport_uncertain_no_retry:" + key) from exc
        response = {"request_sha256": runtime.digest(req), "body": body, "body_sha256": runtime.digest(body),
                    "wall_seconds": time.monotonic() - start, "completed_at": runtime.legacy.now()}
        runtime.write_json(received, response)
        runtime.write_json(run / "active_call.json", {"status": "idle", "at": runtime.legacy.now()}, replace=True)
    runtime.require(response["request_sha256"] == runtime.digest(req) and
                    response["body_sha256"] == runtime.digest(response["body"]), "response_binding")
    body = response["body"]
    runtime.require(body.get("done") is True and body.get("done_reason") != "length", "incomplete_generation")
    value = json.loads(body["response"])
    integrity = contract.inspect(value, packet)
    artifact = {"protocol": contract.VERSION, "artifact_id": key, "dataset": "Dreaddit",
        "source_packet_sha256": packet["source_packet_sha256"], "model": config["model"],
        "model_digest": config["model_digest"], "research_question": config["research_question"],
        "analytic_contract": config["analytic_contract"], "analytic_contract_sha256": runtime.digest(config["analytic_contract"]),
        "prompt_sha256": runtime.digest(contract.PROMPT), "schema_sha256": runtime.digest(contract.SCHEMA),
        "request_sha256": runtime.digest(req), "response_sha256": response["body_sha256"],
        "content": value, "content_sha256": runtime.digest(value), "integrity": integrity,
        "offsets_are_computed_not_model_generated": True, "semantic_quality": "not_independently_assessed"}
    runtime.immutable(output / "artifact.locked.json", artifact)
    report_path = output / "codes_and_themes.md"
    rendered = contract.render(packet, value, integrity)
    if report_path.exists():
        runtime.require(report_path.read_text() == rendered, "report_changed")
    else:
        runtime.write_text(report_path, rendered)
    return {"artifact_id": key, "status": "generated_with_integrity_flags" if integrity["flags"] else "generated",
            "codes": len(value["codes"]), "subthemes": len(value["subthemes"]), "themes": len(value["themes"]),
            "source_records": len(packet["sources"]),
            "sources_with_exact_code_anchor": len(integrity["sources_with_exact_code_anchor"]),
            "integrity_flags": len(integrity["flags"]), "wall_seconds": response["wall_seconds"],
            "artifact_sha256": runtime.file_hash(output / "artifact.locked.json")}


def report(run, status, terminal=False):
    packets = runtime.read(run / "inputs.private.json")
    rows = [runtime.read(p) for packet in packets
            if (p := run / "results" / (packet["artifact_id"] + ".json")).exists()]
    good = [r for r in rows if r["status"].startswith("generated")]
    result = {"at": runtime.legacy.now(), "status": status, "planned_paragraphs": 12, "planned_packets": 3,
        "finished_packets": len(rows), "generated_packets": len(good), "generated_source_records": 4 * len(good),
        "codes": sum(r["codes"] for r in good), "subthemes": sum(r["subthemes"] for r in good),
        "themes": sum(r["themes"] for r in good), "integrity_flags": sum(r["integrity_flags"] for r in good),
        "technical_failures": len(rows) - len(good), "local_calls": len(list((run / "calls").glob("*/request.json"))),
        "paid_calls": 0, "manuscript_eligible": False, "quality_scores": "not_assessed"}
    runtime.write_json(run / "status.json", result, replace=True)
    table = io.StringIO()
    fields = ["artifact_id", "status", "source_records", "codes", "subthemes", "themes",
              "sources_with_exact_code_anchor", "integrity_flags", "wall_seconds", "error"]
    writer = csv.DictWriter(table, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    runtime.write_text(run / "generation_summary.csv", table.getvalue(), replace=True)
    lines = ["# Dreaddit Codes and Themes: 12-Point Smoke Test", "", f"Status: `{status}`.", "",
        "Twelve original paragraphs, three existing four-record packets, one TA generation per packet.",
        "Previously exposed development-only sources. No flaw scoring, Playbook updates or manuscript export.", "",
        f"Generated packets: {len(good)}/3. Codes: {result['codes']}. Subthemes: {result['subthemes']}. Themes: {result['themes']}.",
        f"Technical failures: {result['technical_failures']}. Mechanical integrity flags: {result['integrity_flags']}.",
        "Passing mechanical checks does not establish correct or high-quality TA. No Credibility/Conformability percentage is estimated.", "",
        "## Reports", ""]
    for row in rows:
        key = row["artifact_id"]
        lines.append(f"- [{key}](ta_artifacts/{key}/codes_and_themes.md)" if row in good else f"- {key}: {row.get('error', row['status'])}")
    lines.extend(["", "[Packet counts CSV](generation_summary.csv)", "", "[Frozen source data](inputs.private.json)", ""])
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if terminal:
        files = [p for p in run.rglob("*") if p.is_file() and
                 (p.relative_to(run).parts[0] in {"results", "ta_artifacts", "calls"}
                  or p.name in {"status.json", "summary.md", "generation_summary.csv"})]
        runtime.immutable(run / "final_manifest.json", {**result,
            "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in files}})
    return result


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_run_no_regeneration")
    config = runtime.read(run / "config.json")
    runtime.require(config["paid_api_allowed"] is False and config["base_url"] == runtime.legacy.BASE, "local_only")
    lock = STORAGE / "rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    with lock.open("a") as shared, (run / "worker.lock").open("a") as local:
        fcntl.flock(shared, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(local, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with smoke.local_server(run) as tags:
                model = next((m for m in tags["models"] if m["name"] == config["model"]), None)
                runtime.require(model is not None and model["digest"] == config["model_digest"], "pinned_model_unavailable_no_download")
                if not (run / "clock.json").exists():
                    runtime.write_json(run / "clock.json", {"deadline_unix": time.time() + config["budget_seconds"]})
                deadline = runtime.read(run / "clock.json")["deadline_unix"]
                for packet in runtime.read(run / "inputs.private.json"):
                    path = run / "results" / (packet["artifact_id"] + ".json")
                    if path.exists():
                        row = runtime.read(path)
                        if "artifact_sha256" in row:
                            runtime.require(runtime.file_hash(run / "ta_artifacts" / packet["artifact_id"] / "artifact.locked.json") == row["artifact_sha256"], "locked_artifact_changed")
                        continue
                    if (run / "PAUSE.request.json").exists():
                        return report(run, "paused_at_packet_boundary")
                    print(json.dumps({"status": "generating", "artifact_id": packet["artifact_id"]}), flush=True)
                    try:
                        row = generate(run, config, packet, deadline)
                    except (runtime.AmbiguousCall, runtime.BudgetStop, runtime.FrozenError):
                        raise
                    except Exception as exc:
                        row = {"artifact_id": packet["artifact_id"], "status": "technical_failure", "error": str(exc)}
                    runtime.write_json(path, row)
                    print(json.dumps(report(run, "running")), flush=True)
        except Exception as exc:
            runtime.write_json(run / "supervisor_error.json", {"error": str(exc), "at": runtime.legacy.now()}, replace=True)
            report(run, "needs_attention_no_automatic_retry")
            raise
    counts = report(run, "finalizing")
    status = "completed_with_technical_failures" if counts["technical_failures"] else "completed_generation_only"
    return report(run, status, terminal=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "status", "pause"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        runtime.require(args.source_run is not None, "source_run_required")
        value = prepare(run, args.source_run.resolve())
    elif args.command == "run":
        runtime.require(args.authorize_local_inference, "explicit_local_inference_required")
        value = run_local(run)
    else:
        verify(run)
        if args.command == "pause":
            runtime.require(not (run / "final_manifest.json").exists(), "already_terminal")
            runtime.immutable(run / "PAUSE.request.json", {"reason": "user_requested_query_boundary_pause"})
        value = runtime.read(run / "status.json")
    print(json.dumps(value, indent=2), flush=True)


if __name__ == "__main__":
    main()
