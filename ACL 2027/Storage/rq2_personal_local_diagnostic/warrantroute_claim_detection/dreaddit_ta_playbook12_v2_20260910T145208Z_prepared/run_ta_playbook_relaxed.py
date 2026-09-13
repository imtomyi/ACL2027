"""Separately frozen V2 continuation with operational-specificity admission."""

import argparse
import copy
import csv
import difflib
import fcntl
import io
import json
from pathlib import Path
import shutil
import time
import urllib.request

import run_ta_generation_smoke as generation
import ta_playbook_relaxed_contract as contract

runtime, memory = generation.runtime, contract.memory
PROJECT, STORAGE = generation.PROJECT, generation.STORAGE
CODE = list(dict.fromkeys([*generation.CODE, "ta_playbook_contract.py", "ta_playbook_relaxed_contract.py", Path(__file__).name]))
PROTOCOL = "Storage/experiment_guidelines/ta_playbook_12_relaxed_v2.md"


def prepare(run, source):
    runtime.require(run.is_relative_to(STORAGE) and source.is_relative_to(STORAGE), "private_storage_only")
    generation.verify(source)
    final = runtime.read(source / "final_manifest.json")
    runtime.require(final["generated_packets"] == 3 and final["generated_source_records"] == 12,
                    "complete_twelve_point_ta_bank_required")
    packets, bindings = [], {}
    for row in runtime.read(source / "inputs.private.json"):
        path = source / "ta_artifacts" / row["artifact_id"] / "artifact.locked.json"
        artifact = runtime.read(path)
        runtime.require(runtime.digest(artifact["content"]) == artifact["content_sha256"], "ta_content_binding")
        runtime.require(runtime.digest(row["sources"]) == artifact["source_packet_sha256"], "ta_source_binding")
        bindings[str(path)] = runtime.file_hash(path)
        task = {"research_question": artifact["research_question"], "analytic_contract": artifact["analytic_contract"],
                "artifact": artifact["content"], "evidence": row["sources"],
                "artifact_integrity_flags": artifact["integrity"]["flags"]}
        packets.append({"packet_id": row["artifact_id"], "source_ids": [e["source_id"] for e in row["sources"]],
            "task": task, "task_sha256": runtime.digest(task), "artifact_sha256": runtime.file_hash(path)})
    prior = runtime.read(source / "config.json")
    config = {"protocol": contract.VERSION, "source_run": str(source), "model": prior["model"],
        "model_digest": prior["model_digest"], "options": {**prior["options"], "num_ctx": 49152, "num_predict": 4096},
        "base_url": runtime.legacy.BASE, "paid_api_allowed": False, "manuscript_eligible": False,
        "epochs": 3, "paragraph_n": 12, "artifact_n": 3, "planned_queries": 9,
        "budget_seconds": 1800, "timeout_seconds": 180, "call_ceiling": 27,
        "authorization": "User authorized policy/interface changes. A new run needs a separate explicit launch request and the local-inference CLI flag.",
        "admission_policy": contract.POLICY,
        "seed_policy": "Fresh copy of two original generic warrant/context seeds, explicitly scoped to TA targets by the frozen prompts. No paragraph-learned or manual rules imported.",
        "interpretation": "Previously exposed development-only V2. Both learning interface and novelty criterion changed; do not attribute differences to admission alone. No gold, scoring, repair or manuscript use.",
        "source_files": {**bindings, str(source / "manifest.json"): runtime.file_hash(source / "manifest.json"),
                         str(source / "final_manifest.json"): runtime.file_hash(source / "final_manifest.json")}}
    jobs = [{"id": f"E{epoch}/{p['packet_id']}", "epoch": epoch, "packet_id": p["packet_id"]}
            for epoch in (1, 2, 3) for p in packets]
    state = memory.seed_state()
    for packet in packets:
        contract.request(config, "online_detector", {"task": packet["task"], "playbook": memory.visible_rules(state)})
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inputs.private.json", packets), ("initial_state.json", state),
                         ("schedule.json", jobs), ("prompts.json", contract.PROMPTS)):
        runtime.write_json(run / name, value)
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    shutil.copyfile(PROJECT / PROTOCOL, run / "protocol.md")
    runtime.publish_playbook(run, "dreaddit", state)
    runtime.write_text(run / "playbook_comparison/playbook_initial.txt", memory.playbook_text(memory.visible_rules(state)))
    frozen = [p for p in run.iterdir() if p.is_file()] + [run / "playbook_comparison/playbook_initial.txt"]
    runtime.write_json(run / "manifest.json", {"protocol": contract.VERSION, "created_at": runtime.legacy.now(),
        "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in frozen}})
    return report(run, "prepared_not_started")


def verify(run):
    runtime.require(run.is_relative_to(STORAGE), "private_storage_only")
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["protocol"] == contract.VERSION, "wrong_ta_learning_protocol")
    generation.check_files(run, manifest)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name], "source_code_changed:" + name)
    config = runtime.read(run / "config.json")
    generation.verify(Path(config["source_run"]))
    for path, expected in config["source_files"].items():
        runtime.require(runtime.file_hash(Path(path)) == expected, "frozen_ta_source_changed")
    if (run / "final_manifest.json").exists():
        generation.check_files(run, runtime.read(run / "final_manifest.json"))


class Client:
    def __init__(self, run, deadline):
        self.run, self.deadline = run, deadline
        self.config = runtime.read(run / "config.json")

    def call(self, key, role, data):
        request, bound = contract.request(self.config, role, data)
        folder = self.run / "calls" / key
        sent, received = folder / "request.json", folder / "response.json"
        if sent.exists():
            if runtime.read(sent)["request_sha256"] != runtime.digest(request):
                raise runtime.FrozenError("request_identity_changed")
            if not received.exists():
                raise runtime.AmbiguousCall("missing_response_no_retry:" + key)
            response = runtime.read(received)
        else:
            if self.deadline - time.time() < self.config["timeout_seconds"] + 1:
                raise runtime.BudgetStop("inference_admission_closed")
            if len(list((self.run / "calls").glob("**/request.json"))) >= self.config["call_ceiling"]:
                raise runtime.BudgetStop("call_ceiling")
            runtime.write_json(sent, {"request": request, "request_sha256": runtime.digest(request), "role": role,
                                      "started_at": runtime.legacy.now(), "conservative_context_bound": bound})
            runtime.write_json(self.run / "active_call.json", {"key": key, "role": role, "started_at": runtime.legacy.now()}, replace=True)
            started = time.monotonic()
            try:
                req = urllib.request.Request(self.config["base_url"] + "/api/generate", json.dumps(request).encode(),
                                             {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.config["timeout_seconds"]) as handle:
                    body = json.load(handle)
            except Exception as exc:
                runtime.write_json(folder / "transport_error.json", {"at": runtime.legacy.now(), "error": str(exc)})
                raise runtime.AmbiguousCall(key) from exc
            response = {"body": body, "body_sha256": runtime.digest(body), "request_sha256": runtime.digest(request),
                        "wall_seconds": time.monotonic() - started, "completed_at": runtime.legacy.now()}
            runtime.write_json(received, response)
            runtime.write_json(self.run / "active_call.json", {"status": "idle", "at": runtime.legacy.now()}, replace=True)
        if runtime.digest(response["body"]) != response["body_sha256"] or response["request_sha256"] != runtime.digest(request):
            raise runtime.FrozenError("response_binding")
        body = response["body"]
        runtime.require(body.get("done") is True and body.get("done_reason") != "length", "incomplete_generation")
        return contract.decode(role, json.loads(body["response"]), data)


def prior_learning(run, job):
    if job["epoch"] == 1:
        return None
    previous = runtime.load_record(run / "results" / f"E{job['epoch'] - 1}" / job["packet_id"] / "result.json")
    value = previous["value"]["learning"].get("value", {})
    proposal = value.get("proposal", {"patches": []})
    receipts = {r["patch_id"]: r for r in value.get("receipts", [])}
    return {"prior_record_sha256": previous["sha256"], "epoch": job["epoch"] - 1,
        "projection": "Same-artifact candidate procedures and outcomes only; full prior reflection and audit remain on disk.",
        "candidates": [{**{k: p[k] for k in ("operation", *memory.FIELDS)}, "receipt": receipts.get(p["id"])}
                       for p in proposal["patches"]]}


def process(run, client, job, packet, state, parent):
    result_path = run / "results" / job["id"] / "result.json"
    if result_path.exists():
        record = runtime.load_record(result_path)
        value = record["value"]
        runtime.require(value["parent_record_sha256"] == parent and value["state_before_sha256"] == runtime.digest(state), "result_chain_changed")
        generation.check_files(run, {"files": value["artifacts"]})
        return value["state_after"], record["sha256"]
    rules = memory.visible_rules(state)
    def detect():
        value = client.call(job["id"] + "/detector", "online_detector", {"task": packet["task"], "playbook": rules})
        return {**value, "integrity_findings": contract.check_review(value, packet, rules),
            "retrieved_rules": rules, "retrieved_playbook_text": memory.playbook_text(rules),
            "task_sha256": packet["task_sha256"]}
    prediction = runtime.step(run, run / "predictions" / job["id"] / "review.locked.json", detect)
    before = copy.deepcopy(state)
    def learn():
        locked = prediction["value"]
        data = {"task": packet["task"], "locked_prediction": locked["review"], "rule_checks": locked["rule_checks"],
                "integrity_findings": locked["integrity_findings"], "current_playbook": rules,
                "previous_learning": prior_learning(run, job)}
        proposal = client.call(job["id"] + "/learner", "online_learning", data)
        runtime.immutable(run / "candidates" / job["id"] / "proposal.json", proposal)
        eligible, receipts = contract.eligible(proposal, packet, state)
        next_state, audit = state, None
        if eligible["patches"]:
            audit = client.call(job["id"] + "/auditor", "online_audit",
                {"task": packet["task"], "current_playbook": rules, "learning": eligible})
            next_state, audited = contract.apply(state, eligible, audit, packet)
            receipts += audited
        return {"proposal": proposal, "audit": audit, "receipts": receipts, "state_after": next_state}
    learning = (runtime.step(run, run / "deltas" / job["id"] / "learning.json", learn)
                if prediction["status"] == "valid" else {"status": "skipped_invalid_prediction"})
    if learning["status"] == "valid":
        state = learning["value"]["state_after"]
    files = []
    for folder in ("predictions", "deltas", "candidates", "calls"):
        files.extend((run / folder / job["id"]).rglob("*.json"))
    value = {**job, "task_sha256": packet["task_sha256"], "artifact_sha256": packet["artifact_sha256"],
        "parent_record_sha256": parent, "state_before_sha256": runtime.digest(before),
        "prediction": prediction, "learning": learning, "state_after": state,
        "artifacts": {str(p.relative_to(run)): runtime.file_hash(p) for p in files}}
    record = {"value": value, "sha256": runtime.digest(value)}
    runtime.immutable(result_path, record)
    runtime.publish_playbook(run, "dreaddit", state, job["id"], record["sha256"])
    return state, record["sha256"]


def report(run, status, terminal=False):
    records = [runtime.load_record(p)["value"] for j in runtime.read(run / "schedule.json")
               if (p := run / "results" / j["id"] / "result.json").exists()]
    state = records[-1]["state_after"] if records else runtime.read(run / "initial_state.json")
    initial = runtime.read(run / "initial_state.json")
    added = {r["id"] for r in state["rules"]} - {r["id"] for r in initial["rules"]}
    delivered, rows, candidates = set(), [], []
    for r in records:
        prediction = r["prediction"].get("value", {})
        learning = r["learning"].get("value", {})
        proposal_path = run / "candidates" / r["id"] / "proposal.json"
        proposal = learning.get("proposal") or (runtime.read(proposal_path) if proposal_path.exists() else {"patches": []})
        retrieved = {rule["id"] for rule in prediction.get("retrieved_rules", [])}
        delivered |= added & retrieved
        receipts = learning.get("receipts", [])
        for patch in proposal["patches"]:
            candidates.append({"job_id": r["id"], "candidate_id": "cand-" + runtime.digest(
                {k: patch[k] for k in ("operation", *memory.FIELDS)})[:16], "proposal": patch,
                "receipt": next((x for x in receipts if x["patch_id"] == patch["id"]), None)})
        rows.append({"epoch": r["epoch"], "artifact_id": r["packet_id"], "review_status": r["prediction"]["status"],
            "decision": prediction.get("review", {}).get("decision"), "allegations": len(prediction.get("review", {}).get("issues", [])),
            "review_integrity_flags": len(prediction.get("integrity_findings", [])),
            "learning_status": r["learning"]["status"], "candidates": len(proposal["patches"]),
            "added": sum(x["outcome"] == "added" for x in receipts),
            "added_without_established_novelty": sum(x["outcome"] == "added" and x.get("admitted_without_established_novelty", False) for x in receipts),
            "active_rules_after": len(r["state_after"]["rules"])})
    failures = sum(r["prediction"]["status"] == "technical_failure" or r["learning"]["status"] == "technical_failure" for r in records)
    result = {"at": runtime.legacy.now(), "status": status, "completed_queries": len(records), "planned_queries": 9,
        "source_paragraphs": 12, "locked_ta_artifacts": 3, "epochs": 3, "initial_rules": len(initial["rules"]),
        "current_rules": len(state["rules"]), "new_rule_ids": len(added), "new_rules_delivered_later": len(delivered),
        "candidate_occurrences": len(candidates), "distinct_candidate_contents": len({c["candidate_id"] for c in candidates}),
        "addition_events_without_established_novelty": sum(r["added_without_established_novelty"] for r in rows),
        "technical_failures": failures, "local_calls": len(list((run / "calls").glob("**/request.json"))),
        "paid_calls": 0, "scoring": "No gold: detection accuracy and C/F unassessed", "manuscript_eligible": False}
    runtime.write_json(run / "status.json", result, replace=True)
    runtime.write_json(run / "candidates/current.json", candidates, replace=True)
    candidate_text = ["## CANDIDATE RULES", "", "Proposals and admission outcomes, not all active rules.", ""]
    candidate_text.extend(f"[{c['candidate_id']}] {c['job_id']} | {c['proposal']['operation']} | " +
        " | ".join(f"{k}: {c['proposal'][k]}" for k in memory.FIELDS) + " | " + json.dumps(c["receipt"]) for c in candidates)
    runtime.write_text(run / "candidates/current.txt", "\n".join(candidate_text) + "\n", replace=True)
    before, after = memory.playbook_text(memory.visible_rules(initial)), memory.playbook_text(memory.visible_rules(state))
    runtime.write_text(run / "playbook_comparison/playbook_after.txt", after, replace=True)
    runtime.write_text(run / "playbook_comparison/changes.diff", "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile="initial", tofile="after")), replace=True)
    csv_file = io.StringIO()
    fields = ["epoch", "artifact_id", "review_status", "decision", "allegations", "review_integrity_flags",
              "learning_status", "candidates", "added", "added_without_established_novelty", "active_rules_after"]
    writer = csv.DictWriter(csv_file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    runtime.write_text(run / "query_progress.csv", csv_file.getvalue(), replace=True)
    lines = ["# TA Playbook: Operational-Specificity V2", "", f"Status: {status}.", "",
        f"Completed: {len(records)}/9 reviews; the same 3 locked TA artifacts across 3 epochs, from 12 source paragraphs.",
        f"Rules: {len(initial['rules'])} initial, {len(state['rules'])} current. New IDs: {len(added)}; delivered in a later review: {len(delivered)}.",
        f"Candidate occurrences: {len(candidates)}. Technical failures: {failures}. Paid calls: 0.", "",
        "[Initial Playbook](playbook_comparison/playbook_initial.txt) | [After Playbook](playbook_comparison/playbook_after.txt)",
        "", "[Changes](playbook_comparison/changes.diff) | [Candidates](candidates/current.txt) | [Query CSV](query_progress.csv)", "",
        "The initial rules are two generic warrant/context seeds, scoped to TA by the new contract. No learned paragraph or manual rule is imported.",
        "V2 permits useful operational detail overlapping an existing rule; it keeps grounding, reuse, counterconditions, no invention/leakage and no contradictions mandatory.",
        "Novelty is descriptive, not an admission gate. Admissions with false/unknown novelty are separately counted and are not discoveries of new mechanisms.",
        "Per-query updates may legitimately retain the same rules. Same-model admission, allegation counts and prompt delivery do not prove improved detection.",
        "No gold, quality judge, baseline comparison, manuscript output or TA regeneration. Assistant inspection notes are not model inputs.", "",
        "## Locked Reviews", ""]
    for r in records:
        lines.append(f"- [{r['id']}](predictions/{r['id']}/review.locked.json)")
    runtime.write_text(run / "summary.md", "\n".join(lines) + "\n", replace=True)
    if terminal:
        files = [p for p in run.rglob("*") if p.is_file() and p.name not in
                 {"final_manifest.json", "worker.lock", "ollama_server.log", "owned_server.json", "active_call.json"}]
        runtime.immutable(run / "final_manifest.json", {**result,
            "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in files}})
    return result


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_run_no_rerun")
    config = runtime.read(run / "config.json")
    packets = {p["packet_id"]: p for p in runtime.read(run / "inputs.private.json")}
    state, parent = runtime.read(run / "initial_state.json"), None
    with (STORAGE / "rq2_personal_local_diagnostic/ace_flaw_8h.lock").open("a") as shared, (run / "worker.lock").open("a") as local:
        fcntl.flock(shared, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(local, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with generation.smoke.local_server(run) as tags:
                installed = next((m for m in tags["models"] if m["name"] == config["model"]), None)
                runtime.require(installed is not None and installed["digest"] == config["model_digest"], "pinned_model_unavailable_no_download")
                if not (run / "clock.json").exists():
                    runtime.write_json(run / "clock.json", {"deadline_unix": time.time() + config["budget_seconds"]})
                client = Client(run, runtime.read(run / "clock.json")["deadline_unix"])
                for job in runtime.read(run / "schedule.json"):
                    complete = (run / "results" / job["id"] / "result.json").exists()
                    if not complete and (run / "PAUSE.request.json").exists():
                        return report(run, "paused_at_query_boundary")
                    runtime.write_json(run / "phase.json", job, replace=True)
                    state, parent = process(run, client, job, packets[job["packet_id"]], state, parent)
                    print(json.dumps(report(run, "running")), flush=True)
        except Exception as exc:
            runtime.write_json(run / "supervisor_error.json", {"at": runtime.legacy.now(), "error": str(exc)}, replace=True)
            report(run, "needs_attention_no_automatic_retry")
            raise
    counts = report(run, "finalizing")
    return report(run, "completed_with_technical_failures" if counts["technical_failures"] else "completed_unscored_development", terminal=True)


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
        runtime.require(args.authorize_local_inference, "local_inference_authorization_required")
        value = run_local(run)
    else:
        verify(run)
        if args.command == "pause":
            runtime.require(not (run / "final_manifest.json").exists(), "already_terminal")
            runtime.immutable(run / "PAUSE.request.json", {"reason": "explicit_user_pause"})
        value = runtime.read(run / "status.json")
    print(json.dumps(value, indent=2), flush=True)


if __name__ == "__main__":
    main()
