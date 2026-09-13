"""Continue paragraph development with a bounded target of four additional rule IDs."""

import argparse
import difflib
import fcntl
import json
from pathlib import Path
import shutil
import time

import run_dreaddit_playbook_followup as previous

contract, memory, runtime, smoke = previous.contract, previous.memory, previous.runtime, previous.smoke
VERSION = "dreaddit-playbook-four-more-v1"
CODE = [*previous.CODE, Path(__file__).name]
PROTOCOL = "Storage/experiment_guidelines/dreaddit_playbook_four_more_v1.md"


def select_new_paragraphs(inputs, used):
    normalized = lambda text: " ".join(text.casefold().split())
    excluded = [e for p in inputs["dreaddit"]["evaluation"] for e in p["task"]["evidence"]]
    excluded += [e for p in used for e in p["task"]["evidence"]]
    records = {e["source_record_id"] for e in excluded}
    groups = {e["source_id"] for e in excluded}
    texts = {normalized(e["text"]) for e in excluded}
    eligible = []
    for parent in sorted(inputs["dreaddit"]["development"], key=lambda p: p["packet_id"]):
        runtime.require(runtime.digest(parent["task"]) == parent["task_sha256"], "source_task_changed")
        for excerpt in parent["task"]["evidence"]:
            if (excerpt["metadata"]["split"] != "development_train"
                    or excerpt["source_record_id"] in records or excerpt["source_id"] in groups
                    or normalized(excerpt["text"]) in texts):
                continue
            visible = {k: excerpt[k] for k in ("excerpt_id", "text", "source_id", "source_record_id")}
            task = {"claim": visible["text"], "evidence": [visible], "cited_excerpt_ids": [visible["excerpt_id"]]}
            eligible.append({"packet_id": "paragraph_" + runtime.digest(visible["source_record_id"])[:16],
                "task": task, "task_sha256": runtime.digest(task), "source_ids": [visible["source_id"]],
                "source_record_id": visible["source_record_id"], "parent_packet_id": parent["packet_id"],
                "source_excerpt_sha256": runtime.digest(excerpt)})
            records.add(visible["source_record_id"])
            groups.add(visible["source_id"])
            texts.add(normalized(visible["text"]))
    runtime.require(len(eligible) >= 4, "four_unused_development_paragraphs_required")
    return eligible[:4], len(eligible)


def new_panel_jobs(packets):
    jobs = []
    for epoch in range(1, 4):
        ordered = sorted(packets, key=lambda p: runtime.digest([VERSION, epoch, p["packet_id"]]))
        for position, packet in enumerate(ordered, 1):
            jobs.append({"id": f"development/dreaddit/E{epoch}/{packet['packet_id']}",
                "phase": "development", "dataset": "dreaddit", "epoch": epoch,
                "position": position, "packet_id": packet["packet_id"], "panel": "new_development_paragraphs"})
    return jobs


def prepare(run, prior):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    runtime.require(run.is_relative_to(storage) and prior.is_relative_to(storage), "private_storage_only")
    previous.verify(prior)
    final = runtime.read(prior / "final_manifest.json")
    runtime.require(final["status"] == "stopped_update_delivery_verified", "verified_parent_required")
    previous.check_files(prior, final)
    initial = runtime.read(prior / "playbooks/dreaddit/current.json")
    memory.visible_rules(initial)
    used = runtime.read(prior / "inputs.private.json")
    for packet in used:
        runtime.require(runtime.digest(packet["task"]) == packet["task_sha256"], "paragraph_hash_changed")
    source = Path(runtime.read(prior / "config.json")["source_run"])
    runtime.require(source.is_relative_to(storage), "private_source_only")
    previous.check_files(source, runtime.read(source / "manifest.json"))
    packets, eligible_n = select_new_paragraphs(runtime.read(source / "inputs.private.json"), used)
    source_schedule = runtime.read(prior / "schedule.json")
    completed = final["completed_queries"]
    last = runtime.load_record(prior / "results" / source_schedule[completed - 1]["id"] / "result.json")
    runtime.require(last["value"]["state_after"] == initial, "parent_state_binding")
    jobs = new_panel_jobs(packets)
    total = runtime.read(prior / "status.json")["cumulative_query_exposures"]
    config = {**runtime.read(prior / "config.json"), "controller_protocol": VERSION,
        "prior_run": str(prior), "prior_final_manifest_sha256": runtime.file_hash(prior / "final_manifest.json"),
        "prior_completed_queries": total, "additional_epochs": sorted({j["epoch"] for j in jobs}),
        "target_additional_rule_ids": 4, "budget_seconds": 600, "call_ceiling": 36,
        "initial_rule_ids": [r["id"] for r in initial["rules"]],
        "initial_rule_quality": "Inherited same-model-admitted rule has documented semantic limitations; not requalified.",
        "selection": "First four eligible unused development paragraphs in canonical source packet/excerpt order, before outcomes.",
        "source_inputs_sha256": runtime.file_hash(source / "inputs.private.json"),
        "eligible_unused_paragraphs_before_selection": eligible_n,
        "prior_unique_paragraphs": len(used), "new_unique_paragraphs": 4,
        "inference_authorization": "User requested four more flaw-detection Playbook guidelines.",
        "stop_rule": "Four additional distinct admitted rule IDs, each delivered in a later valid detector request; otherwise 12 queries or 600 seconds.",
        "interpretation": "Outcome-stopped development debugging; new development paragraphs with unchanged prompts, model, and admission criteria."}
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
        "controller_protocol": VERSION, "created_at": runtime.legacy.now(),
        "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in sorted(files)}})
    return report(run, "prepared_not_started")


def verify(run):
    manifest = previous.verify(run)
    runtime.require(manifest["controller_protocol"] == VERSION, "wrong_growth_controller")
    runtime.require(runtime.file_hash(Path(__file__)) == manifest["files"][Path(__file__).name],
                    "growth_implementation_changed")
    return manifest


def growth_counts(run):
    initial = runtime.read(run / "initial_state.json")
    initial_ids = {r["id"] for r in initial["rules"]}
    added, delivered = [], set()
    state = initial
    for job in runtime.read(run / "schedule.json"):
        path = run / "results" / job["id"] / "result.json"
        if not path.exists():
            break
        row = runtime.load_record(path)["value"]
        pred = row["predictions"]["online"]
        if pred["status"] == "valid":
            request_path = run / "calls" / job["id"] / "online/detector/request.json"
            if request_path.exists():
                sent = runtime.read(request_path)
                runtime.require(runtime.digest(sent["request"]) == sent["request_sha256"], "growth_request_hash_changed")
                prompt = sent["request"]["prompt"]
                runtime.require(prompt.startswith(contract.PROMPTS["online_detector"]), "growth_prompt_changed")
                wire = json.loads(prompt.split("\nINPUT JSON:\n", 1)[1].split("\nOUTPUT JSON SCHEMA:\n", 1)[0])
                expected = memory.prompt_data("online_detector", {"playbook": pred["value"]["retrieved_rules"]})["playbook"]
                runtime.require(wire["playbook"] == expected, "growth_wire_memory_mismatch")
                delivered.update(r["id"] for r in pred["value"]["retrieved_rules"] if r["id"] in added)
        for receipt in row["learning"].get("value", {}).get("receipts", []):
            if receipt["outcome"] == "added":
                key = receipt["rule_id"]
                runtime.require(key not in initial_ids and key not in added, "added_id_not_new")
                added.append(key)
        state = row["state_after"]
    target = runtime.read(run / "config.json")["target_additional_rule_ids"]
    return {"initial_rule_count": len(initial["rules"]), "current_rule_count": len(state["rules"]),
        "new_rule_ids": added, "new_rule_text_ids": [state["text_ids"][k] for k in added],
        "additional_rules_admitted": len(added), "additional_rules_delivered": len(delivered),
        "target_additional_rule_ids": target,
        "target_delivered": len(added) >= target and set(added[:target]) <= delivered}


def report(run, status, terminal=False):
    result = smoke.report(run, status)
    config = runtime.read(run / "config.json")
    counts = growth_counts(run)
    result.pop("epochs")
    result.update(counts, controller_protocol=VERSION,
        learned_rules=counts["current_rule_count"] - len(memory.base.SEED),
        scheduled_epoch_labels=config["additional_epochs"],
        prior_completed_queries=config["prior_completed_queries"],
        cumulative_query_exposures=config["prior_completed_queries"] + result["completed_queries"],
        interpretation=config["interpretation"])
    runtime.write_json(run / "status.json", result, replace=True)
    folder = run / "playbook_comparison"
    initial, after = (folder / "playbook_initial.txt").read_text(), (run / "playbooks/dreaddit/current.txt").read_text()
    runtime.write_text(folder / "playbook_after.txt", after, replace=True)
    difference = "".join(difflib.unified_diff(initial.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="playbook_initial.txt", tofile="playbook_after.txt"))
    runtime.write_text(folder / "changes.diff", difference, replace=True)
    lines = ["# Four More Detection Guidelines", "", f"Status: `{status}`.", "",
        f"Additional query exposures: {result['completed_queries']}/12 of four NEW original development paragraphs, up to three epochs.",
        f"Cumulative exposures including preceding runs: {result['cumulative_query_exposures']}; not independent data points.",
        f"New distinct admitted rules: {counts['additional_rules_admitted']}/4.",
        f"New distinct rules delivered in a later detector request: {counts['additional_rules_delivered']}.",
        f"Total rules: {counts['initial_rule_count']} initially, {counts['current_rule_count']} currently.",
        f"New TXT IDs: {', '.join(counts['new_rule_text_ids']) or 'none'}.",
        f"Transport/schema errors: {result['technical_failures']}. Local calls: {result['local_model_calls']}. Paid calls: 0.", "",
        "Only newly admitted canonical rule IDs count toward four. Refinement, reinforcement, replay, and inherited rules do not.",
        "A query can admit two rules, so the target can be exceeded; valid outputs are never selectively discarded.", "",
        "## Comparison", "",
        "- [Initial Playbook](playbook_comparison/playbook_initial.txt)",
        "- [After Playbook](playbook_comparison/playbook_after.txt)",
        "- [Exact changes](playbook_comparison/changes.diff)",
        "- [Per-query outcomes](query_progress.csv)", "",
        "## Interpretation", "",
        "These are flaw-detection and categorization guidelines, not experiment-management instructions or answer keys.",
        "The model, prompts, operation-dependent schema, and six admission criteria are unchanged from the prior follow-up.",
        "New source paragraphs exclude the evaluation panel and prior-used records, source groups, and normalized text.",
        "The inherited rule has documented semantic and application concerns. Carrying it forward does not validate it.",
        "New rules are also fallible same-model-admitted proposals. Delivery is not proof of correct use or better detection.",
        "This is outcome-stopped development debugging, not an unbiased performance experiment.",
        "Accuracy, precision, recall, Credibility, and Conformability are unassessed without adjudicated gold.",
        "All no-change, rejected, and failed outcomes remain. Original runs, Table 3, and manuscript files are unchanged.", ""]
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if terminal:
        files = ["status.json", "summary.md", "playbook_comparison/playbook_initial.txt",
            "playbook_comparison/playbook_after.txt", "playbook_comparison/changes.diff",
            "playbooks/dreaddit/current.txt", "playbooks/dreaddit/current.json", "playbooks/dreaddit/current.manifest.json"]
        if (run / "query_progress.csv").exists():
            files.append("query_progress.csv")
        runtime.immutable(run / "final_manifest.json", {"status": status,
            "completed_queries": result["completed_queries"], "planned_queries": 12,
            **counts, "manuscript_eligible": False,
            "files": {name: runtime.file_hash(run / name) for name in files}})
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
        if progress["target_delivered"]:
            return report(run, "stopped_four_additional_rules_delivered", terminal=True)
    return report(run, "stopped_query_cap_target_incomplete", terminal=True)


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_growth_not_resumable")
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
