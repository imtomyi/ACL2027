"""Bounded, outcome-stopped development debugging; not an accuracy experiment."""

import argparse
import difflib
import fcntl
import json
from pathlib import Path
import shutil
import time

import ace_online_contract as memory
import paragraph_followup_contract as contract
import run_ace_flaw_online as runtime
import run_dreaddit_paragraph_playbook_smoke as smoke


CODE = [*smoke.CODE, "paragraph_followup_contract.py", Path(__file__).name]
PROTOCOL = "Storage/experiment_guidelines/dreaddit_paragraph_playbook_followup_v1.md"


def check_files(root, manifest):
    for name, expected in manifest["files"].items():
        runtime.require(runtime.file_hash(root / name) == expected, "frozen_file_changed:" + name)


def prepare(run, prior):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    runtime.require(run.is_relative_to(storage) and prior.is_relative_to(storage), "private_storage_only")
    smoke.verify(prior)
    final = runtime.read(prior / "final_manifest.json")
    check_files(prior, final)
    runtime.require(final["completed_queries"] == final["planned_queries"] == 12, "completed_parent_required")
    initial = runtime.read(prior / "playbooks/dreaddit/current.json")
    runtime.require(initial == memory.seed_state(), "this_followup_requires_unchanged_parent_seed_state")
    packets = runtime.read(prior / "inputs.private.json")
    runtime.require(len(packets) == 4, "same_four_paragraphs_required")
    for packet in packets:
        runtime.require(runtime.digest(packet["task"]) == packet["task_sha256"], "paragraph_hash_changed")
    config = {**runtime.read(prior / "config.json"), "protocol": contract.VERSION,
        "budget_seconds": 600, "call_ceiling": 36, "prior_run": str(prior),
        "prior_final_manifest_sha256": runtime.file_hash(prior / "final_manifest.json"),
        "additional_epochs": [4, 5, 6], "prior_completed_queries": 12,
        "inference_authorization": "User requested a little more local development work until an update is accepted.",
        "stop_rule": "First accepted add/refine delivered in a later valid detector request; otherwise 12 more queries or 600 seconds.",
        "interpretation": "Outcome-stopped debugging with changed prompts/schema, not an unbiased performance comparison."}
    jobs = []
    for old in runtime.read(prior / "schedule.json"):
        epoch = old["epoch"] + 3
        jobs.append({**old, "epoch": epoch,
            "id": f"development/dreaddit/E{epoch}/{old['packet_id']}"})
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inputs.private.json", packets),
                        ("initial_state.json", initial), ("schedule.json", jobs),
                        ("prompts.json", contract.PROMPTS)):
        runtime.write_json(run / name, value)
    shutil.copyfile(runtime.legacy.PROJECT / PROTOCOL, run / "protocol.md")
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    runtime.publish_playbook(run, "dreaddit", initial)
    runtime.write_text(run / "playbook_comparison/playbook_initial.txt",
                       memory.playbook_text(memory.visible_rules(initial)))
    files = [p for p in run.iterdir() if p.is_file()]
    files.append(run / "playbook_comparison/playbook_initial.txt")
    runtime.write_json(run / "manifest.json", {"protocol": contract.VERSION,
        "created_at": runtime.legacy.now(), "files": {
            str(p.relative_to(run)): runtime.file_hash(p) for p in sorted(files)}})
    return report(run, "prepared_not_started")


def verify(run):
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["protocol"] == contract.VERSION, "wrong_followup_protocol")
    check_files(run, manifest)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name],
                        "source_implementation_changed:" + name)
    if (run / "final_manifest.json").exists():
        check_files(run, runtime.read(run / "final_manifest.json"))
    return manifest


def update_delivered(status):
    return (status["accepted_add_or_refine_operations"] > 0
            and status["learned_rule_prompt_inclusions"] > 0
            and status["detector_txt_requests_verified"] == status["completed_queries"])


def report(run, status, terminal=False):
    result = smoke.report(run, status)
    result.update(protocol=contract.VERSION, additional_epoch_labels=[4, 5, 6],
        prior_completed_queries=12, cumulative_query_exposures=12 + result["completed_queries"],
        interpretation="Outcome-stopped development debugging; no claim of detection improvement.")
    runtime.write_json(run / "status.json", result, replace=True)
    initial = (run / "playbook_comparison/playbook_initial.txt").read_text()
    after = (run / "playbooks/dreaddit/current.txt").read_text()
    runtime.write_text(run / "playbook_comparison/playbook_after.txt", after, replace=True)
    difference = "".join(difflib.unified_diff(initial.splitlines(keepends=True),
        after.splitlines(keepends=True), fromfile="playbook_initial.txt", tofile="playbook_after.txt"))
    runtime.write_text(run / "playbook_comparison/changes.diff", difference, replace=True)
    lines = ["# Paragraph Playbook Follow-up", "",
        f"Status: `{status}`.", "",
        f"Additional queries: {result['completed_queries']}/12; cumulative exposures including the prior run: {result['cumulative_query_exposures']}.",
        "The same four original paragraphs are reused across up to three additional epochs (4-6).", "",
        f"New learned rules: {result['learned_rules']}. Accepted add/refine operations: {result['accepted_add_or_refine_operations']}.",
        f"Later learned-rule prompt inclusions: {result['learned_rule_prompt_inclusions']}.",
        f"Verified actual detector TXT requests: {result['detector_txt_requests_verified']}.",
        f"Transport/schema technical failures: {result['technical_failures']}. Local calls: {result['local_model_calls']}. Paid calls: 0.", "",
        "## Comparison", "",
        "- [Initial Playbook](playbook_comparison/playbook_initial.txt)",
        "- [After Playbook](playbook_comparison/playbook_after.txt)",
        "- [Exact content differences](playbook_comparison/changes.diff)",
        "- [Per-query outcomes](query_progress.csv)", "",
        "## Limits", "",
        "Prompts and the operation-dependent schema differ from the preserved prior smoke run.",
        "The original evidence, model/options, immutable seeds, six audit criteria, and admission rules remain unchanged.",
        "Stopping after a verified update is outcome-dependent debugging, not an unbiased performance experiment.",
        "A same-model-admitted rule is not independent proof of semantic validity or improved flaw detection.",
        "No adjudicated gold is available; accuracy and Credibility/Conformability are not assessed.",
        "All failed and no-change outcomes are retained. No manuscript or Table 3 file is updated.", ""]
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if terminal:
        paths = ["status.json", "summary.md", "playbook_comparison/playbook_initial.txt",
            "playbook_comparison/playbook_after.txt", "playbook_comparison/changes.diff",
            "playbooks/dreaddit/current.txt", "playbooks/dreaddit/current.json",
            "playbooks/dreaddit/current.manifest.json"]
        if (run / "query_progress.csv").exists():
            paths.append("query_progress.csv")
        runtime.immutable(run / "final_manifest.json", {"status": status,
            "completed_queries": result["completed_queries"], "planned_queries": 12,
            "accepted_update_delivered": update_delivered(result), "manuscript_eligible": False,
            "files": {name: runtime.file_hash(run / name) for name in paths}})
    return result


def worker(run, client):
    packets = {p["packet_id"]: p for p in runtime.read(run / "inputs.private.json")}
    state, parent = runtime.read(run / "initial_state.json"), None
    for job in runtime.read(run / "schedule.json"):
        complete = (run / "results" / job["id"] / "result.json").exists()
        if not complete and (run / "PAUSE.request.json").exists():
            return report(run, "paused_at_query_boundary")
        runtime.write_json(run / "phase.json", job, replace=True)
        state, parent = runtime.process_job(client, job, packets[job["packet_id"]], state, parent)
        progress = report(run, "running")
        if not complete:
            print(json.dumps(progress), flush=True)
        if update_delivered(progress):
            return report(run, "stopped_update_delivery_verified", terminal=True)
    return report(run, "stopped_query_cap_without_verified_update", terminal=True)


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_followup_not_resumable")
    config = runtime.read(run / "config.json")
    runtime.require(config["paid_api_allowed"] is False and config["base_url"] == runtime.legacy.BASE, "local_only")
    lock = runtime.legacy.PROJECT / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    with lock.open("a") as shared, (run / "worker.lock").open("a") as local:
        fcntl.flock(shared, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(local, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with smoke.local_server(run) as tags:
            installed = next((m for m in tags.get("models", []) if m["name"] == config["model"]), None)
            runtime.require(installed is not None and installed["digest"] == config["model_digest"], "pinned_model_unavailable_no_download")
            if not (run / "clock.json").exists():
                start = time.time()
                runtime.write_json(run / "clock.json", {"started_unix": start, "deadline_unix": start + config["budget_seconds"]})
            try:
                return worker(run, contract.Client(run, runtime.read(run / "clock.json")["deadline_unix"]))
            except runtime.BudgetStop:
                return report(run, "stopped_budget", terminal=True)
            except Exception as exc:
                runtime.write_json(run / "supervisor_error.json", {"at": runtime.legacy.now(), "error": str(exc)}, replace=True)
                report(run, "needs_attention_no_automatic_retry")
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "status"])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--prior-run", type=Path)
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        runtime.require(args.prior_run is not None, "prior_run_required")
        result = prepare(run, args.prior_run.resolve())
    elif args.command == "status":
        verify(run)
        result = runtime.read(run / "status.json")
    else:
        runtime.require(args.authorize_local_inference, "explicit_local_inference_authorization_required")
        result = run_local(run)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
