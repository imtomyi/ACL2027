"""Local-only, deadline-bounded ACE-inspired flaw detection with audited memory."""

import argparse
import copy
import csv
import datetime as dt
import fcntl
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request

from jsonschema import Draft202012Validator

import ace_flaw_contract as contract
import plan_gemma_8h as design


PROJECT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:11434"
MODEL = "gemma3:4b"
METHOD = "ACE-inspired WarrantRoute-Lite"
DISPLAY = {"dreaddit": "Dreaddit", "goemotions": "GoEmotions", "cache": "CaChe", "parlamint-gb": "ParlaMint-GB"}
CODE = ["run_ace_flaw_8h.py", "ace_flaw_contract.py", "plan_gemma_8h.py"]
OPTIONS = {"temperature": 0, "seed": 20260910, "num_ctx": 32768, "num_predict": 8192}
read, digest, file_hash, require = design.read, design.digest, design.file_hash, design.require


class BudgetStop(Exception):
    pass


class AmbiguousCall(Exception):
    pass


class FrozenError(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_text(path, text, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, value, replace=False):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", replace)


def table_csv(path, rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_text(path, output.getvalue(), replace=True)


def api(path, payload=None):
    if payload is None:
        req = BASE + path
    else:
        req = urllib.request.Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as handle:
        return json.load(handle)


def model_identity():
    tag = next((m for m in api("/api/tags")["models"] if m["name"] == MODEL), None)
    require(tag, "Installed Gemma required; no model download authorized")
    return tag["digest"]


def build_inputs(plan, audit):
    previous = read(PROJECT / plan["candidate_run"] / "manifest.json")
    data = {}
    for ds in plan["datasets"]:
        data[ds] = {}
        for phase in ("development", "evaluation"):
            ids = audit["datasets"][ds]["candidate_ids_not_frozen"][phase]
            require(all(re.fullmatch(r"[A-Za-z0-9_-]+", pid) for pid in ids), "unsafe_packet_id")
            path = Path(previous["splits"][ds][phase + "_file"])
            selected = {}
            with path.open() as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row["packet_id"] not in ids:
                        continue
                    claim = row["llm_generated_qualitative_claim"]
                    evidence = [{k: s.get(k) for k in ("excerpt_id", "text", "source_id", "source_record_id",
                                 "speaker_id", "local_context", "metadata", "display_order")}
                                for s in row["source_text_context"]]
                    task = {"claim": claim["claim"], "cited_excerpt_ids": claim["cited_excerpt_ids"], "evidence": evidence}
                    require(task["claim"] and all(s["text"] for s in evidence), "empty_task")
                    require(set(task["cited_excerpt_ids"]) <= {s["excerpt_id"] for s in evidence}, "invalid_citation")
                    require(len({s["excerpt_id"] for s in evidence}) == len(evidence), "duplicate_excerpt_id")
                    # Bytes are a conservative admission bound, not a measured token count.
                    require(len(json.dumps(task, ensure_ascii=False).encode()) + 12000 < OPTIONS["num_ctx"],
                            "input_ineligible_without_truncation")
                    selected[row["packet_id"]] = {"packet_id": row["packet_id"], "task": task,
                        "task_sha256": digest(task), "original_packet_sha256": digest(row),
                        "source_ids": sorted({s["source_id"] for s in evidence})}
            require(set(selected) == set(ids), "missing_selected_input")
            data[ds][phase] = [selected[i] for i in ids]
    return data


def development_schedule(data, plan):
    jobs = []
    for epoch in range(1, plan["epochs"] + 1):
        orders = {ds: sorted(data[ds]["development"], key=lambda p: digest([
                    20260910, "gemma8h-v6", ds, epoch, p["packet_id"]])) for ds in plan["datasets"]}
        for position in range(10):
            for ds in plan["datasets"]:
                packet = orders[ds][position]
                jobs.append({"id": f"development/{ds}/E{epoch}/{packet['packet_id']}",
                    "phase": "development", "dataset": ds, "epoch": epoch,
                    "position": position + 1, "packet_id": packet["packet_id"]})
    return jobs


def memory_markdown(ds, label, memory):
    lines = [f"# {DISPLAY[ds]} Playbook {label}", "", "Private ACE-inspired flaw-detection memory.", ""]
    for rule in memory:
        lines.extend([f"## {rule['id']} v{rule['version']}", "",
                      f"Type: {'immutable seed' if rule['seed'] else 'learned rule'}.", ""])
        lines.extend(f"- {k}: {rule[k]}" for k in contract.RULE_FIELDS)
        lines.extend([f"- Distinct supporting packets: {len(rule['support_packets'])}",
                      f"- Distinct supporting source groups: {len(rule['support_sources'])}", ""])
    return "\n".join(lines) + "\n"


def snapshot(run, ds, epoch, memory):
    path = run / "playbooks" / ds / f"E{epoch}.json"
    body = {"dataset": ds, "epoch": epoch, "memory": memory, "memory_sha256": digest(memory)}
    if path.exists():
        if read(path) != body:
            raise FrozenError("snapshot_changed:" + str(path))
    else:
        write_json(path, body)
    md = path.with_suffix(".md")
    if not md.exists():
        write_text(md, memory_markdown(ds, f"E{epoch}", memory))


def prepare(run, recover_from=None, restart_from=None, smoke_report=None):
    require(run.is_relative_to((PROJECT / "Storage").resolve()), "private_storage_only")
    plan = read(design.PLAN)
    design.workload(plan)
    audit = design.candidate_audit(plan)
    data = build_inputs(plan, audit)
    identity = model_identity()
    info = api("/api/show", {"model": MODEL})
    require(info["model_info"]["gemma3.context_length"] >= OPTIONS["num_ctx"], "model_context_too_small")
    require(not (recover_from and restart_from), "recovery_and_restart_are_distinct")
    recovered, restart = None, None
    if recover_from is not None:
        recovered = recovery_inventory(recover_from, data, identity)
    elif restart_from is not None:
        restart = restart_inventory(restart_from, data, identity, smoke_report)
    else:
        require(not api("/api/ps").get("models"), "Ollama already has a loaded model; check active use before preparation")
    run.mkdir(parents=True, exist_ok=False)
    write_json(run / "plan.json", plan)
    write_json(run / "inputs.private.json", data)
    write_json(run / "selection_audit.json", {**audit, "evaluation_reuse_authorized": True,
               "authorization": "User instructed starting the proposed four-dataset eight-hour experiment on 2026-09-10."})
    write_json(run / "prompts_and_schemas.json", {"prompts": contract.PROMPTS, "schemas": contract.SCHEMAS})
    write_json(run / "runtime_config.json", {"options": OPTIONS, "model": MODEL, "method": METHOD,
        "base_url": BASE, "budget_seconds": 28800, "source_candidate_role_omitted": True,
        "claim_target": "literal_claim_sentence_only", "planned_outputs": ["results_table_ACE.csv", "results_table_ACE.md", "playbook_result.csv", "playbook_result.md"],
        "authorization_message": "Start the experiment and produce the ACE method result for each of four datasets and the playbook result.",
        "paid_api_allowed": False, "manuscript_eligible": False})
    write_json(run / "development_schedule.json", development_schedule(data, plan))
    write_json(run / "seed.json", contract.SEED)
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    shutil.copyfile(Path(__file__).with_name("ace_8h_execution.md"), run / "execution_protocol.md")
    shutil.copyfile(PROJECT / "Storage/experiment_guidelines/warrantroute_flaw_detection_8h_v6.md", run / "design_protocol.md")
    if recovered is not None:
        shutil.copytree(recover_from / "calls", run / "calls")
        shutil.copyfile(recover_from / "clock.json", run / "clock.json")
        write_json(run / "recovery_provenance.json", recovered)
    if restart is not None:
        write_json(run / "restart_provenance.json", restart)
    manifest = {"created_at": now(), "project_root": str(PROJECT), "model": MODEL, "model_digest": identity,
        "status": "prepared_authorized_private_diagnostic", "files": {p.name: file_hash(p) for p in run.iterdir() if p.is_file()},
        "expected": plan["expected"], "manuscript_eligible": False,
        "interpretation": "ACE-inspired adaptation for claim-flaw detection; not original ACE benchmark or repair validation."}
    write_json(run / "manifest.json", manifest)
    for ds in plan["datasets"]:
        snapshot(run, ds, 0, contract.SEED)
    return export(run, "prepared_not_started")


def restart_inventory(source, inputs, model_digest, smoke_report):
    require(read(source / "final_manifest.json")["status"].startswith("stopped_"), "restart_source_not_stopped")
    old = read(source / "manifest.json")
    for name, expected in old["files"].items():
        require(file_hash(source / name) == expected, "restart_source_contract_changed")
    require(read(source / "inputs.private.json") == inputs, "restart_inputs_changed")
    require(old["model_digest"] == model_digest, "restart_model_changed")
    require(all(p.with_name("response.json").exists() for p in (source / "calls").glob("**/request.json")),
            "restart_ambiguous_old_call")
    require(smoke_report is not None, "restart_requires_live_smoke_report")
    smoke = read(smoke_report)
    require(smoke["status"] == "passed" and smoke["model_digest"] == model_digest, "live_smoke_not_passed")
    require(smoke["options"] == OPTIONS, "smoke_decoding_changed")
    for name in CODE:
        require(smoke["code_sha256"][name] == file_hash(Path(__file__).with_name(name)), "smoke_code_changed")
    require(smoke["inputs_sha256"] == digest(inputs), "smoke_inputs_changed")
    require(smoke["evaluation_packets_used"] == 0 and smoke["datasets_tested"] == list(DISPLAY), "smoke_scope_incomplete")
    for relative, expected in smoke["artifact_sha256"].items():
        require(file_hash(smoke_report.parent / relative) == expected, "smoke_artifact_changed")
    return {"at": now(), "source_run": str(source), "source_manifest_sha256": file_hash(source / "manifest.json"),
            "source_final_manifest_sha256": file_hash(source / "final_manifest.json"),
            "authorization": "User explicitly requested testing errors and starting again on 2026-09-10.",
            "protocol_revision": "bounded_identity_bound_v2", "fresh_eight_hour_clock": True,
            "all_scheduled_items_run_under_new_protocol": True, "imported_experimental_calls": 0,
            "prior_run_and_smoke_excluded_from_results": True,
            "smoke_report": str(smoke_report), "smoke_report_sha256": file_hash(smoke_report)}


def recovery_inventory(source, inputs, model_digest):
    """Continue only the unfinalized startup validation failure, without new draws."""
    old = read(source / "manifest.json")
    for name, expected in old["files"].items():
        require(file_hash(source / name) == expected, "recovery_source_contract_changed")
    require(read(source / "final_manifest.json")["status"] == "stopped_error_no_automatic_retry", "recovery_source_not_stopped")
    require(old["model_digest"] == model_digest, "recovery_model_changed")
    require(read(source / "inputs.private.json") == inputs, "recovery_inputs_changed")
    require(read(source / "prompts_and_schemas.json") == {"prompts": contract.PROMPTS, "schemas": contract.SCHEMAS},
            "recovery_prompts_or_schemas_changed")
    require(read(source / "runtime_config.json")["options"] == OPTIONS, "recovery_decoding_changed")
    require(not list((source / "predictions").glob("**/locked.json")), "recovery_has_completed_diagnoses")
    previous_results = records(source)
    require(previous_results and all(r["phase"] == "development" and r.get("error") == "decision_issue_mismatch"
                                     for r in previous_results), "recovery_not_startup_classification_bug")
    requests = list((source / "calls").glob("**/request.json"))
    require(requests and all(p.with_name("response.json").exists() for p in requests), "recovery_ambiguous_call")
    clock = read(source / "clock.json")
    require(clock["deadline"] > time.time(), "recovery_budget_expired")
    return {"at": now(), "source_run": str(source), "source_manifest_sha256": file_hash(source / "manifest.json"),
            "reason": "A parseable decision/allegation contradiction was incorrectly blocked before its scheduled Finalizer.",
            "changes": "Classify contradiction as a visible semantic finding, not an unusable transport/schema response.",
            "no_new_reference_or_detector_draws_for_imported_calls": True,
            "reused_completed_calls": len(requests), "original_clock_preserved": clock,
            "imported_call_files": {str(p.relative_to(source)): file_hash(p) for p in (source / "calls").glob("**/*.json")},
            "original_failed_results": {str(p.relative_to(source)): file_hash(p) for p in (source / "results").glob("**/result.json")}}


def verify(run):
    manifest = read(run / "manifest.json")
    for name, expected in manifest["files"].items():
        if file_hash(run / name) != expected:
            raise FrozenError("frozen_file_changed:" + name)
    for name in CODE:
        if file_hash(Path(__file__).with_name(name)) != manifest["files"][name]:
            raise FrozenError("execute_frozen_code_only:" + name)
    return manifest


class Client:
    def __init__(self, run, deadline):
        self.run, self.deadline = run, deadline

    def call(self, key, role, data):
        folder = self.run / "calls" / key
        request_path, response_path = folder / "request.json", folder / "response.json"
        schema = contract.wire_schema(role, data)
        prompt = (contract.PROMPTS[role] + "\nINPUT JSON:\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                  + "\nOUTPUT JSON SCHEMA:\n" + json.dumps(schema, separators=(",", ":")))
        bound = len(prompt.encode()) + len(json.dumps(schema).encode()) + OPTIONS["num_predict"] + 1024
        if bound > OPTIONS["num_ctx"]:
            raise ValueError("conservative_context_admission_failed_no_truncation")
        request = {"model": MODEL, "prompt": prompt, "format": schema, "stream": False,
                   "keep_alive": "30m", "options": OPTIONS}
        if request_path.exists():
            if read(request_path)["request_sha256"] != digest(request):
                raise FrozenError("call_identity_changed")
            if not response_path.exists():
                raise AmbiguousCall(str(folder))
            response = read(response_path)
        else:
            if self.deadline - time.time() < 181:
                raise BudgetStop("phase_admission_closed")
            if len(list((self.run / "calls").glob("**/request.json"))) >= 1200:
                raise BudgetStop("call_ceiling")
            write_json(request_path, {"started_at": now(), "role": role, "request": request,
                                     "request_sha256": digest(request), "conservative_context_bound": bound})
            write_json(self.run / "active_call.json", {"key": key, "role": role, "started_at": now(),
                       "request_path": str(request_path), "deadline_unix": self.deadline}, replace=True)
            started = time.monotonic()
            try:
                req = urllib.request.Request(BASE + "/api/generate", json.dumps(request).encode(), {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as handle:
                    body = json.load(handle)
                response = {"status": "returned", "role": role, "body": body,
                            "wall_seconds": time.monotonic() - started, "completed_at": now(),
                            "request_sha256": digest(request)}
                write_json(response_path, response)
                write_json(self.run / "active_call.json", {"status": "idle", "last_key": key, "at": now()}, replace=True)
            except Exception as exc:
                write_json(folder / "transport_error.json", {"at": now(), "error": str(exc)})
                raise AmbiguousCall(str(folder)) from exc
        body = response["body"]
        require(body.get("done") is True and body.get("done_reason") != "length", "incomplete_generation")
        parsed = json.loads(body["response"])
        return contract.decode_wire(role, parsed, data)


def get_reference(client, ds, packet):
    path = client.run / "references" / ds / (packet["packet_id"] + ".json")
    if path.exists():
        return read(path)
    try:
        review = client.call(f"reference/{ds}/{packet['packet_id']}", "reference", {"task": packet["task"]})
        checked = contract.check_review(review, packet["task"])
        require(not checked["integrity_findings"], "reference_integrity_failure")
        result = {"status": "valid", "review": review, "checks": checked}
    except (BudgetStop, AmbiguousCall, FrozenError):
        raise
    except Exception as exc:
        result = {"status": "unavailable", "review": None, "error": str(exc)}
    write_json(path, result)
    return result


def diagnose(client, job, packet, memory):
    task, key = packet["task"], job["id"]
    retrieved = contract.retrieve(memory, task)
    draft = client.call(key + "/detector", "detector", {"task": task, "playbook": retrieved})
    contract.check_review(draft, task)
    final = client.call(key + "/finalizer", "finalizer", {"task": task, "candidate": draft})
    checks = contract.check_final(final, draft, task)
    locked = {"review": final["review"], "task_sha256": packet["task_sha256"], "checks": checks,
              "memory_sha256": digest(memory), "retrieved_rules": retrieved,
              "candidate_dispositions": final["dispositions"]}
    path = client.run / "predictions" / key / "locked.json"
    if path.exists():
        if read(path) != locked:
            raise FrozenError("locked_prediction_changed")
    else:
        write_json(path, locked)
    return locked


def execute_job(client, job, packet, memory):
    task, key, ds = packet["task"], job["id"], job["dataset"]
    result = {**job, "started_at": now(), "task_sha256": packet["task_sha256"],
        "memory_before_sha256": digest(memory), "memory_after": copy.deepcopy(memory),
        "status": "technical_failure", "technical_trajectory": False}
    stage = "reference"
    try:
        ref = get_reference(client, ds, packet)
        result.update(reference_status=ref["status"], reference_issue_n=len(ref["review"]["issues"]) if ref["review"] else None)
        stage = "diagnosis"
        locked = diagnose(client, job, packet, memory)
        result.update(status="valid", review=locked["review"], checks=locked["checks"],
                      prediction_sha256=digest(locked), retrieved_rules=locked["retrieved_rules"])
        if job["phase"] == "development":
            result["learning_status"] = "skipped_reference_unavailable"
            if ref["review"] is not None:
                stage = "learning"
                learning = client.call(key + "/learning", "learning", {"task": task,
                    "locked_prediction": locked["review"], "provisional_reference": ref["review"],
                    "current_playbook": contract.visible_memory(memory), "epoch": job["epoch"]})
                result["learning"] = learning
                if not learning["patches"]:
                    result["learning_status"] = "unchanged_no_proposal"
                else:
                    try:
                        proposed = contract.proposed_memory(memory, learning, task, ref["review"],
                                                            packet["packet_id"], packet["source_ids"])
                    except ValueError as exc:
                        result.update(learning_status="withheld_integrity", learning_error=str(exc))
                    else:
                        stage = "patch_audit"
                        audit = client.call(key + "/patch_audit", "patch_audit", {"task": task,
                            "locked_prediction": locked["review"], "provisional_reference": ref["review"],
                            "current_playbook": contract.visible_memory(memory), "learning": learning})
                        result["patch_audit"] = audit
                        if contract.audit_approved(audit, learning, task):
                            result.update(learning_status="applied", memory_after=proposed)
                            old_versions = {r["id"]: r["version"] for r in memory}
                            for rule in result["memory_after"]:
                                if not rule["seed"] and old_versions.get(rule["id"]) != rule["version"]:
                                    rule["audit_job_id"] = key
                        else:
                            result["learning_status"] = "withheld_semantic_audit"
        else:
            stage = "quality"
            quality = client.call(key + "/quality", "quality", {"task": task, "review": locked["review"],
                "integrity_findings": locked["checks"]["integrity_findings"], "provisional_reference": ref["review"]})
            result.update(quality_status="valid", quality=contract.check_quality(quality, locked["review"], ref["review"]))
    except BudgetStop:
        result.update(phase_limited=True, unfinished_stage="phase_admission_deadline")
    except (AmbiguousCall, FrozenError):
        raise
    except Exception as exc:
        result.update(error=str(exc), error_stage=stage, technical_trajectory=True)
        if job["phase"] == "development":
            result["learning_status"] = "technical_failure" if stage in ("learning", "patch_audit") else "not_reached"
        else:
            result["quality_status"] = "technical_failure" if stage == "quality" else "not_reached"
    result["memory_after_sha256"] = digest(result["memory_after"])
    result["completed_at"] = now()
    return result


def records(run):
    return [read(p) for p in sorted((run / "results").glob("**/result.json"))]


def job_result(run, client, job, packet, memory):
    path = run / "results" / job["id"] / "result.json"
    write_json(run / "phase.json", {**job, "at": now()}, replace=True)
    if path.exists():
        result = read(path)
        if result["memory_before_sha256"] != digest(memory) or result["task_sha256"] != packet["task_sha256"]:
            raise FrozenError("job_identity_or_memory_chain_changed")
    else:
        result = execute_job(client, job, packet, memory)
        write_json(path, result)
    if job["phase"] == "development":
        ds = job["dataset"]
        record = {"epoch": job["epoch"], "position": job["position"], "job_id": job["id"],
                  "memory": result["memory_after"], "memory_sha256": result["memory_after_sha256"]}
        write_json(run / "playbooks" / ds / "current.json", record, replace=True)
        write_text(run / "playbooks" / ds / "current.md",
                   memory_markdown(ds, f"E{job['epoch']} position {job['position']}", result["memory_after"]), replace=True)
        update_path = run / "playbooks" / ds / "updates" / f"E{job['epoch']}-P{job['position']:02d}.json"
        if not update_path.exists():
            before = {r["id"]: r for r in memory}
            changes = [{"before": before.get(r["id"]), "after": r} for r in result["memory_after"] if before.get(r["id"]) != r]
            write_json(update_path, {"job_id": job["id"], "status": result.get("learning_status"),
                       "parent_sha256": digest(memory), "result_sha256": result["memory_after_sha256"], "changes": changes})
    export(run)
    return result


def existing_epochs(run, plan):
    return {ds: {int(p.stem[1:]) for p in (run / "playbooks" / ds).glob("E*.json")} for ds in plan["datasets"]}


def worker(run):
    verify(run)
    with (run / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return worker_locked(run)


def worker_locked(run):
    plan, data, clock = read(run / "plan.json"), read(run / "inputs.private.json"), read(run / "clock.json")
    packets = {(ds, p["packet_id"]): p for ds, phases in data.items() for rows in phases.values() for p in rows}
    chosen_path = run / "evaluation_checkpoint.json"
    failures = 0
    if not chosen_path.exists():
        client = Client(run, clock["started_unix"] + plan["clock"]["development_admission_stop_seconds"])
        memories = {ds: copy.deepcopy(contract.SEED) for ds in plan["datasets"]}
        for job in read(run / "development_schedule.json"):
            if client.deadline - time.time() < 181:
                break
            ds = job["dataset"]
            result = job_result(run, client, job, packets[(ds, job["packet_id"])], memories[ds])
            memories[ds] = result["memory_after"]
            failures = failures + 1 if result["technical_trajectory"] else 0
            if failures >= 3:
                raise RuntimeError("three_consecutive_technical_trajectories")
            if result.get("phase_limited"):
                break
            if job["position"] == 10:
                snapshot(run, ds, job["epoch"], memories[ds])
        selected = design.selected_checkpoint(existing_epochs(run, plan), plan)
        selected["selected_at"] = now()
        write_json(chosen_path, selected)
    chosen = read(chosen_path)
    client = Client(run, clock["started_unix"] + plan["clock"]["inference_admission_stop_seconds"])
    panels = {ds: [p["packet_id"] for p in data[ds]["evaluation"]] for ds in plan["datasets"]}
    jobs = design.evaluation_schedule(panels, chosen["epoch"], plan)
    for job in jobs:
        if client.deadline - time.time() < 181:
            return export(run, "stopped_at_inference_budget")
        job["phase"] = "evaluation"
        memory_record = read(run / "playbooks" / job["dataset"] / f"E{job['epoch']}.json")
        if digest(memory_record["memory"]) != memory_record["memory_sha256"]:
            raise FrozenError("snapshot_hash_changed")
        result = job_result(run, client, job, packets[(job["dataset"], job["packet_id"])], memory_record["memory"])
        if result["memory_before_sha256"] != result["memory_after_sha256"]:
            raise FrozenError("evaluation_modified_memory")
        failures = failures + 1 if result["technical_trajectory"] else 0
        if failures >= 3:
            raise RuntimeError("three_consecutive_technical_trajectories")
        if result.get("phase_limited"):
            return export(run, "stopped_at_inference_budget")
    # Optional probes cannot displace an unprocessed core job or its judge.
    optional = []
    for epoch in (1, 2):
        if epoch == chosen["epoch"]:
            continue
        if not all((run / "playbooks" / ds / f"E{epoch}.json").exists() for ds in plan["datasets"]):
            continue
        for position in range(5):
            for ds in plan["datasets"]:
                pid = panels[ds][position]
                optional.append({"id": f"optional/{ds}/E{epoch}/{pid}", "phase": "optional",
                                 "dataset": ds, "epoch": epoch, "position": position + 1, "packet_id": pid})
    for job in optional:
        estimate = timing(run)["per_role_p75_or_proxy"]
        need = sum(estimate[r] for r in ("detector", "finalizer", "quality")) * 1.25 + 181
        if client.deadline - time.time() < need:
            break
        record = read(run / "playbooks" / job["dataset"] / f"E{job['epoch']}.json")
        if digest(record["memory"]) != record["memory_sha256"]:
            raise FrozenError("optional_snapshot_changed")
        result = job_result(run, client, job, packets[(job["dataset"], job["packet_id"])], record["memory"])
        if result.get("phase_limited"):
            break
    return export(run, "core_finished")


def timing(run):
    groups = {r: [] for r in contract.PROMPTS}
    input_tokens = output_tokens = 0
    for path in (run / "calls").glob("**/response.json"):
        r = read(path)
        groups[r["role"]].append(r["wall_seconds"])
        input_tokens += r["body"].get("prompt_eval_count", 0)
        output_tokens += r["body"].get("eval_count", 0)
    rates = {role: sorted(values)[math.ceil(0.75 * len(values)) - 1] if len(values) >= 5 else 25.0
             for role, values in groups.items()}
    return {"per_role_p75_or_proxy": rates, "observations": {r: len(v) for r, v in groups.items()},
            "proxy_roles": [r for r, v in groups.items() if len(v) < 5],
            "returned_calls": sum(map(len, groups.values())), "input_tokens": input_tokens,
            "output_tokens": output_tokens, "paid_api_usd": 0}


def quality_cell(rows, n=20):
    result = {"reviews_processed": len(rows), "reviews_valid": sum(r["status"] == "valid" for r in rows)}
    for dim in ("credibility", "conformability"):
        states = [r["quality"][dim] if r.get("quality_status") == "valid" else "technical_failure" for r in rows]
        result[dim] = design.quality_counts(states, n)
    result["reference_issues_in_judged"] = sum(r.get("reference_issue_n") or 0 for r in rows if r.get("quality_status") == "valid")
    result["grounded_matches"] = sum(len(r["quality"]["matches"]) for r in rows if r.get("quality_status") == "valid")
    return result


def formatted(q):
    rate = q["resolved_case_pct"]
    return "N/A" if rate is None else f"{rate:.1f}% ({q['true']}/{q['binary_n']} resolved)"


def export(run, terminal=None):
    plan, all_rows = read(run / "plan.json"), records(run)
    clock = read(run / "clock.json") if (run / "clock.json").exists() else None
    chosen = read(run / "evaluation_checkpoint.json") if (run / "evaluation_checkpoint.json").exists() else None
    core = [r for r in all_rows if r["phase"] == "evaluation"]
    development = [r for r in all_rows if r["phase"] == "development"]
    final_epoch = chosen["epoch"] if chosen else 3
    quality_rows, main_rows, memory_rows, details = [], [], [], {}
    for ds in plan["datasets"]:
        for epoch in sorted({0, final_epoch}):
            items = [r for r in core if r["dataset"] == ds and r["epoch"] == epoch]
            cell = quality_cell(items)
            label = f"E{epoch}" if epoch == 0 or chosen is None else chosen["label"]
            row = {"Dataset": DISPLAY[ds], "Method": METHOD, "Model": MODEL, "Checkpoint": label,
                   "Planned_N": 20, "Processed": cell["reviews_processed"], "Valid_reviews": cell["reviews_valid"]}
            for dim in ("credibility", "conformability"):
                q = cell[dim]
                for key in ("true", "false", "null", "technical", "unprocessed", "resolved_case_pct", "binary_n", "binary_coverage_pct", "full_panel_pct"):
                    row[f"{dim}_{key}"] = q[key]
            row.update(reference_issues_in_judged=cell["reference_issues_in_judged"], grounded_matches=cell["grounded_matches"],
                       Qualification="Private same-model constructed-claim diagnostic" + ("; within-source" if ds == "cache" else ""))
            quality_rows.append(row)
            if epoch == final_epoch:
                main_rows.append(row)
                details[ds] = cell
        available = sorted((run / "playbooks" / ds).glob("E*.json"), key=lambda p: int(p.stem[1:]))
        last = read(available[-1])
        current_path = run / "playbooks" / ds / "current.json"
        current = read(current_path) if current_path.exists() else last
        memory = current["memory"]
        selected_path = run / "playbooks" / ds / f"E{final_epoch}.json"
        selected_memory = read(selected_path)["memory"] if selected_path.exists() else []
        ds_dev = [r for r in development if r["dataset"] == ds]
        learned = [r for r in memory if not r["seed"]]
        selected_learned = [r for r in selected_memory if not r["seed"]]
        used = {r["id"] for result in core if result["dataset"] == ds for r in result.get("retrieved_rules", []) if not r["seed"]}
        applied = [r for r in ds_dev if r.get("learning_status") == "applied"]
        lineage_ok = all(r.get("audit_job_id") and (run / "results" / r["audit_job_id"] / "result.json").exists() for r in learned)
        state = "seed_only" if not learned else "generated_not_retrieved"
        if learned and used:
            state = "generated_retrieved_audit_complete" if lineage_ok else "provenance_incomplete"
        mrow = {"Dataset": DISPLAY[ds], "Latest_saved_epoch": last["epoch"], "Current_epoch": current["epoch"], "Evaluation_epoch": final_epoch if chosen else None,
                "Development_processed": len(ds_dev), "Development_valid": sum(r["status"] == "valid" for r in ds_dev),
                "Learned_rules_latest": len(learned), "Learned_rules_evaluated": len(selected_learned),
                "Accepted_batches": len(applied), "Proposed_edits": sum(len(r.get("learning", {}).get("patches", [])) for r in ds_dev),
                "Accepted_adds": sum(p["operation"] == "add" for r in applied for p in r["learning"]["patches"]),
                "Accepted_replacements": sum(p["operation"] == "replace" for r in applied for p in r["learning"]["patches"]),
                "Withheld_integrity": sum(r.get("learning_status") == "withheld_integrity" for r in ds_dev),
                "Withheld_semantic_audit": sum(r.get("learning_status") == "withheld_semantic_audit" for r in ds_dev),
                "Unchanged": sum(r.get("learning_status") == "unchanged_no_proposal" for r in ds_dev),
                "Learning_technical": sum(r.get("learning_status") == "technical_failure" for r in ds_dev),
                "Distinct_supporting_packets": len({p for r in learned for p in r["support_packets"]}),
                "Distinct_supporting_sources": len({p for r in learned for p in r["support_sources"]}),
                "Distinct_learned_rules_retrieved": len(used), "State": state}
        memory_rows.append(mrow)
    table_csv(run / "dataset_quality.csv", quality_rows)
    table_csv(run / "results_table_ACE.csv", main_rows)
    table_csv(run / "playbook_result.csv", memory_rows)
    paired = []
    for ds in plan["datasets"]:
        before = {r["packet_id"]: r for r in core if r["dataset"] == ds and r["epoch"] == 0}
        after = {r["packet_id"]: r for r in core if r["dataset"] == ds and r["epoch"] == final_epoch}
        for dim in ("credibility", "conformability"):
            differences = []
            if chosen and final_epoch > 0:
                for pid in before.keys() & after.keys():
                    a, b = before[pid], after[pid]
                    if (a["task_sha256"] == b["task_sha256"] and a.get("quality_status") == b.get("quality_status") == "valid"
                            and a["quality"][dim] is not None and b["quality"][dim] is not None):
                        differences.append(int(b["quality"][dim]) - int(a["quality"][dim]))
            paired.append({"Dataset": DISPLAY[ds], "Dimension": dim, "Adapted_checkpoint": chosen["label"] if chosen else "pending",
                "Joint_binary_N": len(differences), "Improved": differences.count(1), "Worsened": differences.count(-1),
                "Unchanged": differences.count(0), "Paired_change_pp": 100*sum(differences)/len(differences) if differences else None})
    table_csv(run / "paired_changes.csv", paired)
    inputs = read(run / "inputs.private.json")
    probe_rows = []
    for ds in plan["datasets"]:
        probe = {p["packet_id"] for p in inputs[ds]["evaluation"][:5]}
        for epoch in range(4):
            selected_rows = [r for r in all_rows if r["phase"] in ("evaluation", "optional")
                             and r["dataset"] == ds and r["epoch"] == epoch and r["packet_id"] in probe]
            cell = quality_cell(selected_rows, 5)
            probe_rows.append({"Dataset": DISPLAY[ds], "Checkpoint": f"E{epoch}", "Planned_N": 5,
                "Processed": len(selected_rows), "Credibility_resolved_pct": cell["credibility"]["resolved_case_pct"],
                "Credibility_binary_n": cell["credibility"]["binary_n"],
                "Conformability_resolved_pct": cell["conformability"]["resolved_case_pct"],
                "Conformability_binary_n": cell["conformability"]["binary_n"]})
    table_csv(run / "fixed_probe_curve.csv", probe_rows)
    lines = ["# Results Table: ACE-Inspired Flaw Detection", "", f"Updated: {now()}", "",
             "Private same-model diagnostic. Percentages below use resolved judgments only; they are not repair validation or manuscript-qualified results.", "",
             "| Dataset | Method | Checkpoint | Reviews / 20 | Credibility | Conformability |", "| --- | --- | --- | ---: | --- | --- |"]
    for row in main_rows:
        ds = next(k for k, v in DISPLAY.items() if v == row["Dataset"])
        cell = details[ds]
        lines.append(f"| {row['Dataset']} | {METHOD} | {row['Checkpoint']} | {row['Processed']} | {formatted(cell['credibility'])} | {formatted(cell['conformability'])} |")
    lines.extend(["", "Full scheduled-panel rates, T/F/unknown/technical counts and coverage are in results_table_ACE.csv.",
                  "Seed-control E0 rows are in dataset_quality.csv. Matched binary differences are in paired_changes.csv.",
                  "Fixed-five-packet checkpoint results are in fixed_probe_curve.csv. Missing or unresolved cells remain unavailable.",
                  "CaChe is a within-source diagnostic. E3 is a target, not a completed checkpoint, until selection and judging finish.", ""])
    write_text(run / "results_table_ACE.md", "\n".join(lines), replace=True)
    pb = ["# Playbook Result", "", f"Updated: {now()}", "",
          "More rules and audit approvals do not themselves demonstrate better detection. Each corpus has readable E0/E1/E2/E3 snapshots under playbooks/.", "",
          "| Dataset | Saved epoch | Learned rules | Accepted batches | Withheld batches | Retrieved learned rules | State |",
          "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in memory_rows:
        pb.append(f"| {r['Dataset']} | {r['Latest_saved_epoch']} | {r['Learned_rules_latest']} | {r['Accepted_batches']} | {r['Withheld_integrity']+r['Withheld_semantic_audit']} | {r['Distinct_learned_rules_retrieved']} | {r['State']} |")
    pb.extend(["", "See playbook_result.csv for update, support, failure and selected-checkpoint counts.", ""])
    write_text(run / "playbook_result.md", "\n".join(pb), replace=True)
    times = timing(run)
    rates = times["per_role_p75_or_proxy"]
    dev_left = 0 if chosen else max(0, 120 - len(development))
    core_target = 80 if chosen and chosen["epoch"] == 0 else 160
    eval_left = max(0, core_target - len(core))
    ref_left = max(0, 120 - len(list((run / "references").glob("**/*.json"))))
    dev_seconds = dev_left * sum(rates[r] for r in ("detector", "finalizer", "learning", "patch_audit"))
    quality_seconds = eval_left * rates["quality"]
    eval_seconds = eval_left * (rates["detector"] + rates["finalizer"])
    ref_seconds = ref_left * rates["reference"]
    valid_pairs = sum(r.get("quality_status") == "valid" and r["quality"]["credibility"] is not None
                      and r["quality"]["conformability"] is not None for r in core)
    state = terminal or "running"
    if terminal == "core_finished":
        if chosen["epoch"] != 3:
            state = "completed_budget_limited_checkpoint"
        elif valid_pairs != 160:
            state = "completed_with_unresolved_quality"
        else:
            state = "completed_private_diagnostic"
    status = {"updated_at": now(), "state": state, "method": METHOD, "model": MODEL,
        "development_processed": len(development), "development_planned": 120,
        "core_reviews_processed": len(core), "core_reviews_planned": 160,
        "core_reviews_valid": sum(r["status"] == "valid" for r in core),
        "core_judgments_valid": sum(r.get("quality_status") == "valid" for r in core),
        "core_binary_quality_pairs": valid_pairs, "optional_reviews_processed": sum(r["phase"] == "optional" for r in all_rows),
        "technical_trajectories": sum(r["technical_trajectory"] for r in all_rows),
        "selected_checkpoint": chosen, "datasets": details, "playbooks": memory_rows, "timing": times,
        "remaining_estimates_hours": {"development": dev_seconds/3600, "references": ref_seconds/3600,
            "core_review_generation": eval_seconds/3600, "core_judging": quality_seconds/3600,
            "core_total": (dev_seconds+ref_seconds+eval_seconds+quality_seconds)/3600,
            "qualification": "Provisional upper-quartile/proxy call workload; excludes export overhead and may count completed stages of in-flight jobs."},
        "clock": clock, "remaining_budget_seconds": max(0, clock["deadline"]-time.time()) if clock else None,
        "phase": read(run / "phase.json") if (run / "phase.json").exists() else None,
        "active_call": read(run / "active_call.json") if (run / "active_call.json").exists() else None,
        "paid_api_usd": 0, "manuscript_eligible": False}
    write_json(run / "status.json", status, replace=True)
    if terminal and terminal != "prepared_not_started":
        final = {"status": state, "at": now(), "table_rows": len(main_rows), "playbook_rows": len(memory_rows),
                 "core_expected": 160, "core_processed": len(core), "binary_pairs": valid_pairs,
                 "selected_checkpoint": chosen, "files": {p.name: file_hash(p) for p in [run / "results_table_ACE.csv", run / "results_table_ACE.md",
                    run / "playbook_result.csv", run / "playbook_result.md", run / "dataset_quality.csv",
                    run / "paired_changes.csv", run / "fixed_probe_curve.csv"]},
                 "manuscript_eligible": False}
        write_json(run / "final_manifest.json", final, replace=True)
    return status


def supervise(run):
    manifest = verify(run)
    # A project-wide lock prevents two copies with different run directory names.
    global_path = Path(manifest["project_root"]) / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    global_path.parent.mkdir(parents=True, exist_ok=True)
    with global_path.open("a") as global_lock, (run / "supervisor.lock").open("a") as lock:
        fcntl.flock(global_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return supervise_locked(run, manifest)


def supervise_locked(run, manifest):
    if (run / "final_manifest.json").exists():
        raise FrozenError("terminal_run_cannot_be_restarted")
    if model_identity() != manifest["model_digest"]:
        raise FrozenError("installed_model_digest_changed")
    if not (run / "clock.json").exists():
        start = time.time()
        write_json(run / "clock.json", {"started_at": now(), "started_unix": start,
                    "deadline": start + 28800, "deadline_utc": dt.datetime.fromtimestamp(start+28800, dt.timezone.utc).isoformat()})
    clock = read(run / "clock.json")
    if time.time() >= clock["deadline"]:
        return export(run, "stopped_at_8h_budget")
    child = subprocess.Popen([sys.executable, "-B", str(run / "run_ace_flaw_8h.py"), "worker", "--run-dir", str(run)], start_new_session=True)
    write_json(run / "supervisor.json", {"pid": os.getpid(), "worker_pid": child.pid, "started_at": now(), "deadline": clock["deadline"]}, replace=True)
    export(run)
    try:
        code = child.wait(timeout=max(1, clock["deadline"] - time.time()))
        if code and not (run / "final_manifest.json").exists():
            write_json(run / "supervisor_error.json", {"at": now(), "worker_exit_code": code}, replace=True)
            return export(run, "stopped_worker_without_terminal_export")
        return read(run / "status.json")
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        return export(run, "stopped_at_8h_budget")
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "worker", "status"))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--recover-from", type=Path, help="Only a stopped startup-classification failure with no finalized prediction")
    parser.add_argument("--restart-from", type=Path, help="Explicitly authorized new protocol run; no previous outputs imported")
    parser.add_argument("--smoke-report", type=Path, help="Passed live preflight for the exact new code, model and inputs")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        result = prepare(run, args.recover_from.resolve() if args.recover_from else None,
                         args.restart_from.resolve() if args.restart_from else None,
                         args.smoke_report.resolve() if args.smoke_report else None)
    elif args.command == "status":
        result = read(run / "status.json")
        if (run / "active_call.json").exists():
            result["active_call"] = read(run / "active_call.json")
        if result.get("clock"):
            result["remaining_budget_seconds"] = max(0, result["clock"]["deadline"]-time.time())
    elif args.command == "run":
        result = supervise(run)
    else:
        try:
            result = worker(run)
        except Exception as exc:
            write_json(run / "worker_error.json", {"at": now(), "type": type(exc).__name__, "error": str(exc)}, replace=True)
            export(run, "stopped_error_no_automatic_retry")
            raise
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
