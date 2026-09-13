"""Private four-paragraph development smoke test, not a scored Table 3 run."""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request

import ace_flaw_contract as base
import ace_online_contract as memory
import run_ace_flaw_online as runtime


VERSION = "dreaddit-four-paragraph-playbook-smoke-v1"
PROTOCOL = "Storage/experiment_guidelines/dreaddit_four_paragraph_smoke_v1.md"
CODE = [*runtime.CODE, Path(__file__).name]
ROLES = ("online_detector", "online_learning", "online_audit")
ORIGINAL_SCOPE = "Assess ONLY the supplied original claim SENTENCE against ALL supplied evidence."
PARAGRAPH_SCOPE = """Assess one ORIGINAL Dreaddit paragraph for material internal inferential
or contextual flaws. task.claim contains the complete paragraph, not a generated
summary. task.evidence contains that SAME paragraph solely as an exact-quotation
anchor container. Its repetition is NOT independent corroboration. Inspect the
paragraph's actual assertions, qualifications, hypotheses and questions. Do not
invent a separate claim or import external facts. Self-reported emotions, missing
external corroboration, rhetorical questions, uncertainty and hypothetical
possibilities are not automatically flaws. Do not diagnose the writer or judge
their character. An established flaw requires a specific internal failed warrant,
overclaim or consequential contextual contradiction, with a located target and
an explanation beyond merely quoting that target. Otherwise give an honest
negative or unresolved diagnosis. Useful bounded checking procedures can be
learned from defensible negative cases too; do not invent flaws to justify a
Playbook update. Never require or fabricate a new rule on every exposure."""
runtime.require(base.COMMON.startswith(ORIGINAL_SCOPE), "paragraph_prompt_template_changed")
PROMPTS = {role: memory.PROMPTS[role].replace(ORIGINAL_SCOPE, PARAGRAPH_SCOPE, 1) for role in ROLES}


class ParagraphClient(runtime.Client):
    def request(self, role, data):
        runtime.require(role in ROLES, "smoke_has_no_reference_or_quality_calls")
        runtime.require(self.config["protocol"] == VERSION, "wrong_smoke_protocol")
        request, _ = super().request(role, data)
        runtime.require(request["prompt"].startswith(memory.PROMPTS[role]), "unexpected_prompt_template")
        request["prompt"] = PROMPTS[role] + request["prompt"][len(memory.PROMPTS[role]):]
        bound = (len(request["prompt"].encode()) + len(json.dumps(request["format"]).encode())
                 + self.config["options"]["num_predict"] + 1024)
        runtime.require(bound <= self.config["options"]["num_ctx"], "paragraph_context_admission_no_truncation")
        return request, bound


def select_paragraphs(inputs):
    development = inputs["dreaddit"]["development"]
    parent = sorted(development, key=lambda p: p["packet_id"])[0]
    runtime.require(runtime.digest(parent["task"]) == parent["task_sha256"], "source_task_changed")
    records = parent["task"]["evidence"]
    runtime.require(len(records) == 4, "four_source_paragraphs_required")
    excluded = [e for p in inputs["dreaddit"]["evaluation"] for e in p["task"]["evidence"]]
    normalized = lambda text: " ".join(text.casefold().split())
    runtime.require(not {e["source_record_id"] for e in records} & {e["source_record_id"] for e in excluded}, "evaluation_record_overlap")
    runtime.require(not {e["source_id"] for e in records} & {e["source_id"] for e in excluded}, "evaluation_source_overlap")
    runtime.require(not {normalized(e["text"]) for e in records} & {normalized(e["text"]) for e in excluded}, "evaluation_text_overlap")
    runtime.require(len({normalized(e["text"]) for e in records}) == 4, "duplicate_paragraph_text")
    packets = []
    for excerpt in records:
        runtime.require(excerpt["metadata"]["split"] == "development_train", "development_only")
        visible = {key: excerpt[key] for key in ("excerpt_id", "text", "source_id", "source_record_id")}
        task = {"claim": visible["text"], "evidence": [visible], "cited_excerpt_ids": [visible["excerpt_id"]]}
        packets.append({"packet_id": "paragraph_" + runtime.digest(visible["source_record_id"])[:16],
            "task": task, "task_sha256": runtime.digest(task), "source_ids": [visible["source_id"]],
            "source_record_id": visible["source_record_id"], "parent_packet_id": parent["packet_id"],
            "source_excerpt_sha256": runtime.digest(excerpt)})
    runtime.require(len({p["source_record_id"] for p in packets}) == 4, "duplicate_paragraph_record")
    return packets


def prepare(run, source):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    runtime.require(run.is_relative_to(storage) and source.is_relative_to(storage), "private_storage_only")
    source_manifest = runtime.read(source / "manifest.json")
    for name, expected in source_manifest["files"].items():
        runtime.require(runtime.file_hash(source / name) == expected, "source_frozen_file_changed:" + name)
    packets = select_paragraphs(runtime.read(source / "inputs.private.json"))
    config = {"protocol": VERSION, "model": runtime.legacy.MODEL,
        "model_digest": runtime.read(source / "config.json")["model_digest"], "options": runtime.OPTIONS,
        "base_url": runtime.legacy.BASE, "paid_api_allowed": False, "manuscript_eligible": False,
        "epochs": 3, "paragraph_n": 4, "call_ceiling": 36, "budget_seconds": 1200,
        "inference_authorization": "User requested a temporary four-Dreaddit-datapoint Playbook experiment.",
        "scoring": "No gold inventory: detection accuracy and C/F are not assessed.",
        "selection": "Four evidence paragraphs from the lexicographically first existing Dreaddit development packet.",
        "source_run": str(source), "source_manifest_sha256": runtime.file_hash(source / "manifest.json")}
    jobs = []
    for epoch in range(1, 4):
        order = sorted(packets, key=lambda p: runtime.digest([VERSION, epoch, p["packet_id"]]))
        for position, packet in enumerate(order, 1):
            jobs.append({"id": f"development/dreaddit/E{epoch}/{packet['packet_id']}", "phase": "development",
                "dataset": "dreaddit", "epoch": epoch, "position": position, "packet_id": packet["packet_id"]})
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inputs.private.json", packets), ("schedule.json", jobs), ("prompts.json", PROMPTS)):
        runtime.write_json(run / name, value)
    shutil.copyfile(runtime.legacy.PROJECT / PROTOCOL, run / "protocol.md")
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    runtime.write_json(run / "manifest.json", {"protocol": VERSION, "created_at": runtime.legacy.now(),
        "files": {p.name: runtime.file_hash(p) for p in sorted(run.iterdir()) if p.is_file()}})
    runtime.publish_playbook(run, "dreaddit", memory.seed_state())
    return report(run, "prepared_not_started")


def verify(run):
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["protocol"] == VERSION, "wrong_smoke_protocol")
    for name, expected in manifest["files"].items():
        runtime.require(runtime.file_hash(run / name) == expected, "frozen_file_changed:" + name)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name], "source_implementation_changed:" + name)
    return manifest


def model_tags():
    with urllib.request.urlopen(runtime.legacy.BASE + "/api/tags", timeout=2) as response:
        return json.load(response)


@contextmanager
def local_server(run):
    """Reuse an available local server, or clean up only the one this run starts."""
    owned = None
    log = None
    try:
        try:
            tags = model_tags()
        except urllib.error.URLError:
            binary = shutil.which("ollama")
            runtime.require(binary is not None, "local_ollama_not_installed")
            log = (run / "ollama_server.log").open("a")
            env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_NO_CLOUD": "1",
                "OLLAMA_NOPRUNE": "1", "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1"}
            owned = subprocess.Popen([binary, "serve"], env=env, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            runtime.write_json(run / "owned_server.json", {"pid": owned.pid, "started_at": runtime.legacy.now()}, replace=True)
            deadline = time.monotonic() + 30
            while True:
                runtime.require(owned.poll() is None, "owned_ollama_server_exited")
                try:
                    tags = model_tags()
                    break
                except urllib.error.URLError:
                    runtime.require(time.monotonic() < deadline, "local_ollama_start_timeout")
                    time.sleep(.25)
        yield tags
    finally:
        if owned is not None and owned.poll() is None:
            os.killpg(owned.pid, signal.SIGTERM)
            try:
                owned.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(owned.pid, signal.SIGKILL)
                owned.wait(timeout=10)
        if log is not None:
            log.close()


def worker(run, client):
    packets = {p["packet_id"]: p for p in runtime.read(run / "inputs.private.json")}
    state, parent = memory.seed_state(), None
    for job in runtime.read(run / "schedule.json"):
        complete = (run / "results" / job["id"] / "result.json").exists()
        if not complete and (run / "PAUSE.request.json").exists():
            return report(run, "paused_at_query_boundary")
        runtime.write_json(run / "phase.json", job, replace=True)
        state, parent = runtime.process_job(client, job, packets[job["packet_id"]], state, parent)
        progress = report(run, "running")
        if not complete:
            print(json.dumps(progress), flush=True)
    return report(run, "completed")


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_smoke_not_resumable")
    config = runtime.read(run / "config.json")
    runtime.require(config["paid_api_allowed"] is False and config["base_url"] == runtime.legacy.BASE, "local_only")
    global_path = runtime.legacy.PROJECT / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    with global_path.open("a") as shared, (run / "worker.lock").open("a") as local:
        fcntl.flock(shared, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(local, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with local_server(run) as tags:
            installed = next((m for m in tags.get("models", []) if m["name"] == config["model"]), None)
            runtime.require(installed is not None and installed["digest"] == config["model_digest"], "pinned_model_unavailable_no_download")
            clock = run / "clock.json"
            if not clock.exists():
                started = time.time()
                runtime.write_json(clock, {"started_unix": started, "deadline_unix": started + config["budget_seconds"]})
            try:
                return worker(run, ParagraphClient(run, runtime.read(clock)["deadline_unix"]))
            except runtime.BudgetStop:
                return report(run, "stopped_budget_incomplete")
            except Exception as exc:
                runtime.write_json(run / "supervisor_error.json", {"at": runtime.legacy.now(), "error": str(exc)}, replace=True)
                report(run, "needs_attention_no_automatic_retry")
                raise


def report(run, status=None):
    jobs = runtime.read(run / "schedule.json")
    records = [runtime.load_record(run / "results" / j["id"] / "result.json")["value"] for j in jobs
               if (run / "results" / j["id"] / "result.json").exists()]
    state = records[-1]["state_after"] if records else memory.seed_state()
    rows, failures, changed, inclusions, applications, wire_verified = [], 0, 0, 0, 0, 0
    for row in records:
        prediction = row["predictions"]["online"]
        locked = prediction.get("value", {})
        learning = row["learning"]
        learned = [r for r in locked.get("retrieved_rules", []) if not r["seed"]]
        if prediction["status"] == "valid":
            runtime.require(locked["retrieved_playbook_text"] == memory.playbook_text(locked["retrieved_rules"]), "locked_txt_projection_changed")
            request_path = run / "calls" / row["id"] / "online/detector/request.json"
            if request_path.exists():
                sent = runtime.read(request_path)
                runtime.require(runtime.digest(sent["request"]) == sent["request_sha256"], "request_hash_changed")
                prompt = sent["request"]["prompt"]
                runtime.require(prompt.startswith(PROMPTS["online_detector"]), "paragraph_scope_not_sent")
                encoded = prompt.split("\nINPUT JSON:\n", 1)[1].split("\nOUTPUT JSON SCHEMA:\n", 1)[0]
                runtime.require(json.loads(encoded)["playbook"]["text"] == locked["retrieved_playbook_text"], "wire_txt_mismatch")
                wire_verified += 1
        included_ids = {r["id"] for r in learned}
        used = sum(check["applicable"] is True for key, check in locked.get("rule_checks", {}).items() if key in included_ids)
        receipts = learning.get("value", {}).get("receipts", [])
        edits = sum(r["outcome"] in ("added", "refined") for r in receipts)
        failures += sum(v.get("status") == "technical_failure" for v in (prediction, learning))
        changed += edits
        inclusions += len(learned)
        applications += used
        rows.append({"epoch": row["epoch"], "packet_id": row["packet_id"], "query_id": row["id"],
            "prediction_status": prediction["status"], "decision": locked.get("review", {}).get("decision"),
            "reported_flaws_not_gold_verified": len(locked.get("review", {}).get("issues", [])),
            "learning_status": learning.get("value", {}).get("status", learning["status"]),
            "added": sum(r["outcome"] == "added" for r in receipts),
            "refined": sum(r["outcome"] == "refined" for r in receipts),
            "reinforced": sum(r["outcome"] == "reinforced" for r in receipts),
            "withheld": sum(r["outcome"].startswith("withheld") for r in receipts),
            "memory_revision_after": row["state_after"]["revision"],
            "learned_rule_prompt_inclusions": len(learned), "reported_applications": used,
            "review_integrity_findings": len(locked.get("checks", {}).get("integrity_findings", [])),
            "rule_trace_integrity_findings": len(locked.get("checks", {}).get("rule_integrity_findings", []))})
    if rows:
        runtime.legacy.table_csv(run / "query_progress.csv", rows)
    previous = runtime.read(run / "status.json") if (run / "status.json").exists() else {}
    result = {"at": runtime.legacy.now(), "status": status or previous.get("status", "prepared_not_started"),
        "unique_paragraphs": 4, "epochs": 3, "completed_queries": len(records), "planned_queries": len(jobs),
        "technical_failures": failures, "learned_rules": len(state["rules"]) - len(base.SEED),
        "accepted_add_or_refine_operations": changed, "learned_rule_prompt_inclusions": inclusions,
        "detector_txt_requests_verified": wire_verified,
        "learned_rule_applications_self_reported": applications,
        "local_model_calls": len(list((run / "calls").glob("**/request.json"))),
        "paid_api_calls": 0, "detection_accuracy": None, "credibility": None, "conformability": None,
        "limitation": "Development-only operational smoke test; same-model audits are not independent semantic validation.",
        "manuscript_eligible": False}
    if status == "completed":
        result["status"] = ("completed_with_technical_failures" if failures else
            "completed_update_chain_verified" if changed and inclusions and wire_verified == len(jobs)
            else "completed_without_demonstrated_update_chain")
    runtime.write_json(run / "status.json", result, replace=True)
    lines = ["# Four-Paragraph Playbook Smoke Test", "", result["limitation"], "",
        f"Completed queries: {len(records)}/{len(jobs)} across four source paragraphs and three epochs.",
        f"Learned rules: {result['learned_rules']}. Accepted add/refine operations: {changed}.",
        f"Later learned-rule prompt inclusions: {inclusions}. Technical failures: {failures}.", "",
        "Detection accuracy and Credibility/Conformability are not assessed: no adjudicated gold inventory is available.",
        "Reported flaws and rule applications are model outputs, not verified correctness or causal benefit.", "",
        "Current Playbook: `playbooks/dreaddit/current.txt`. Revision history is retained alongside it.", ""]
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if status == "completed":
        paths = ["status.json", "summary.md", "query_progress.csv", "playbooks/dreaddit/current.txt",
                 "playbooks/dreaddit/current.json", "playbooks/dreaddit/current.manifest.json"]
        runtime.immutable(run / "final_manifest.json", {"status": result["status"], "completed_queries": len(records),
            "planned_queries": len(jobs), "manuscript_eligible": False,
            "files": {name: runtime.file_hash(run / name) for name in paths}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "status", "run"])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        runtime.require(args.source_run is not None, "source_run_required")
        result = prepare(run, args.source_run.resolve())
    elif args.command == "status":
        verify(run)
        result = runtime.read(run / "status.json")
    else:
        runtime.require(args.authorize_local_inference, "explicit_local_inference_authorization_required")
        result = run_local(run)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
