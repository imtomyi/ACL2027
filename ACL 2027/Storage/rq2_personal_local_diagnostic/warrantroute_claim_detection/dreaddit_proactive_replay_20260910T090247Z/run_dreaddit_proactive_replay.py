"""Fixed 36-query replay with active candidate discovery, isolated from its comparator."""

import argparse
import difflib
import fcntl
import json
from pathlib import Path
import shutil
import time

import paragraph_proactive_contract as contract
import run_dreaddit_playbook_panel as panel

memory, runtime, smoke = contract.memory, contract.runtime, contract.smoke
VERSION = "dreaddit-proactive-replay-v1"
CODE = [*panel.CODE, "paragraph_proactive_contract.py", Path(__file__).name]
PROTOCOL = "Storage/experiment_guidelines/dreaddit_proactive_replay_v1.md"


def prepare(run, comparator):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    runtime.require(run.is_relative_to(storage) and comparator.is_relative_to(storage), "private_storage_only")
    panel.verify(comparator)
    config = runtime.read(comparator / "config.json")
    final = runtime.read(comparator / "final_manifest.json")
    jobs = runtime.read(comparator / "schedule.json")
    packets = runtime.read(comparator / "inputs.private.json")
    runtime.require(final["completed_queries"] == len(jobs) == 36 and len(packets) == 12,
                    "completed_twelve_paragraph_three_epoch_comparator_required")
    runtime.require(config["epochs"] == 3 and all(j["phase"] == "development" for j in jobs), "development_replay_only")
    runtime.require(len({p["source_record_id"] for p in packets}) == 12, "distinct_paragraphs_required")
    for packet in packets:
        runtime.require(runtime.digest(packet["task"]) == packet["task_sha256"], "replay_task_changed")
        runtime.require({j["epoch"] for j in jobs if j["packet_id"] == packet["packet_id"]} == {1, 2, 3}, "replay_epoch_coverage")
    initial = runtime.read(comparator / "initial_state.json")
    memory.visible_rules(initial)
    for obsolete in ("prior_run", "prior_final_manifest_sha256", "prior_completed_queries", "prior_unique_paragraphs",
                     "eligible_unused_paragraphs_before_selection", "new_unique_paragraphs", "additional_epochs"):
        config.pop(obsolete, None)
    config.update(protocol=contract.VERSION, controller_protocol=VERSION, comparator_run=str(comparator),
        comparator_manifest_sha256=runtime.file_hash(comparator / "manifest.json"),
        comparator_final_manifest_sha256=runtime.file_hash(comparator / "final_manifest.json"),
        budget_seconds=5400, call_ceiling=108, stop_rule="Complete all 36 scheduled exposures regardless of additions; bounded by 108 calls, 90 minutes, or an explicit pause.",
        inference_authorization="User requested proactive learning changes and replay of the same 36 exposures.",
        selection="Exact comparator inputs, schedule and initial memory, copied byte-for-byte; no new data.",
        interpretation="Paired-input development debugging, not independent accuracy evaluation. Only learning prompt/schema and same-paragraph feedback change.")
    run.mkdir(parents=True, exist_ok=False)
    for name in ("inputs.private.json", "initial_state.json", "schedule.json", "data_points.md"):
        shutil.copyfile(comparator / name, run / name)
    runtime.write_json(run / "config.json", config)
    runtime.write_json(run / "prompts.json", contract.PROMPTS)
    shutil.copyfile(runtime.legacy.PROJECT / PROTOCOL, run / "protocol.md")
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    runtime.publish_playbook(run, "dreaddit", initial)
    runtime.write_text(run / "playbook_comparison/playbook_initial.txt", memory.playbook_text(memory.visible_rules(initial)))
    files = [p for p in run.iterdir() if p.is_file()] + [run / "playbook_comparison/playbook_initial.txt"]
    runtime.write_json(run / "manifest.json", {"protocol": contract.VERSION, "controller_protocol": VERSION,
        "created_at": runtime.legacy.now(), "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in sorted(files)}})
    return report(run, "prepared_not_started")


def verify(run):
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["controller_protocol"] == VERSION, "wrong_proactive_controller")
    panel.growth.previous.check_files(run, manifest)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name], "proactive_source_changed:" + name)
    config = runtime.read(run / "config.json")
    comparator = Path(config["comparator_run"])
    for name in ("manifest.json", "final_manifest.json"):
        runtime.require(runtime.file_hash(comparator / name) == config["comparator_" + name.replace(".json", "") + "_sha256"], "comparator_manifest_changed")
        panel.growth.previous.check_files(comparator, runtime.read(comparator / name))
    for name in ("inputs.private.json", "initial_state.json", "schedule.json"):
        runtime.require(runtime.file_hash(run / name) == runtime.file_hash(comparator / name), "paired_replay_mismatch:" + name)
    if (run / "final_manifest.json").exists():
        panel.growth.previous.check_files(run, runtime.read(run / "final_manifest.json"))


def candidate_register(run, records):
    candidates, occurrences, no_patch = {}, 0, 0
    for row in records:
        learning = row["learning"].get("value", {})
        if not learning:
            continue
        proposal = learning["proposal"]
        no_patch += not proposal["patches"]
        receipts = {p["patch_id"]: p for p in learning["receipts"]}
        audit = {p["patch_id"]: p for p in (learning.get("audit") or {}).get("edits", [])}
        event = {"job_id": row["id"], "reflection": proposal["reflection"], "candidates": []}
        for patch in proposal["patches"]:
            key = contract.candidate_id(patch)
            item = {"candidate_id": key, "patch": patch, "receipt": receipts.get(patch["id"]), "audit": audit.get(patch["id"])}
            event["candidates"].append(item)
            if key not in candidates:
                candidates[key] = {"candidate_id": key, "operation": patch["operation"],
                    **{name: patch[name] for name in memory.FIELDS}, "occurrences": []}
            candidates[key]["occurrences"].append({"job_id": row["id"], "patch_id": patch["id"], **(receipts.get(patch["id"]) or {})})
            occurrences += 1
        runtime.immutable(run / "candidates/history" / row["id"] / "candidates.json", event)
    runtime.write_json(run / "candidates/current.json", list(candidates.values()), replace=True)
    lines = ["## CANDIDATE RULES", "", "Proposals only. Active admitted rules are in playbooks/dreaddit/current.txt.", ""]
    for item in candidates.values():
        outcomes = sorted({p.get("outcome", "unresolved") for p in item["occurrences"]})
        fields = " | ".join(f"{name}: {' '.join(item[name].split())}" for name in memory.FIELDS)
        lines.append(f"[{item['candidate_id']}] {item['operation']} | outcomes: {', '.join(outcomes)} | {fields}")
    runtime.write_text(run / "candidates/current.txt", "\n".join(lines) + "\n", replace=True)
    return {"candidate_occurrences": occurrences, "distinct_candidate_contents": len(candidates), "queries_without_patches": no_patch}


def report(run, status, terminal=False):
    result = smoke.report(run, status)
    jobs = runtime.read(run / "schedule.json")
    records = [runtime.load_record(path)["value"] for j in jobs if (path := run / "results" / j["id"] / "result.json").exists()]
    counts = panel.growth.growth_counts(run)
    result.update({**counts, **candidate_register(run, records)}, unique_paragraphs=12, epochs=3,
        distinct_paragraphs_completed=len({r["packet_id"] for r in records}),
        learned_rules=counts["current_rule_count"] - len(memory.base.SEED), controller_protocol=VERSION,
        ready_to_stop=len(records) == len(jobs))
    runtime.write_json(run / "status.json", result, replace=True)
    folder = run / "playbook_comparison"
    initial = (folder / "playbook_initial.txt").read_text()
    after = (run / "playbooks/dreaddit/current.txt").read_text()
    runtime.write_text(folder / "playbook_after.txt", after, replace=True)
    runtime.write_text(folder / "changes.diff", "".join(difflib.unified_diff(initial.splitlines(keepends=True),
        after.splitlines(keepends=True), fromfile="playbook_initial.txt", tofile="playbook_after.txt")), replace=True)
    lines = ["# Proactive Dreaddit Replay", "", f"Status: `{status}`.", "",
        f"Completed exposures: {len(records)}/36, using the same 12 paragraphs over 3 epochs.",
        f"Distinct candidate contents: {result['distinct_candidate_contents']}; candidate occurrences: {result['candidate_occurrences']}.",
        f"New admitted rule IDs: {counts['additional_rules_admitted']}; delivered in later detector calls: {counts['additional_rules_delivered']}.",
        f"Active rules: {counts['initial_rule_count']} initially, {counts['current_rule_count']} currently.",
        f"Technical failures: {result['technical_failures']}; local calls: {result['local_model_calls']}; paid calls: 0.", "",
        "## Files", "", "- [Inputs](data_points.md)", "- [Per-query outcomes](query_progress.csv)",
        "- [Candidate register](candidates/current.txt)", "- [Initial Playbook](playbook_comparison/playbook_initial.txt)",
        "- [After Playbook](playbook_comparison/playbook_after.txt)", "- [Exact changes](playbook_comparison/changes.diff)", "",
        "## Interpretation", "", "Candidate IDs are content identities, not proof of distinct useful lessons. Rejections remain visible.",
        "All 36 exposures are scheduled regardless of rule growth. Refine, reinforce and repeated delivery do not count as new rules.",
        "Detector, auditor, model/options, admission criteria, retrieval and memory capacity are unchanged.",
        "Learning now searches four opportunities and uses the latest prior same-paragraph learning decision within this run.",
        "No prior comparator outputs, held-out items, gold labels or quality judgments enter the learning prompt.",
        "Same-model admission and reported rule use do not establish semantic correctness or improved detection.",
        "Inherited rule limitations remain; this is an unscored development replay, not independent evaluation.",
        "Accuracy, Credibility and Conformability remain unassessed. Manuscript and Table 3 are untouched.", ""]
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if terminal:
        names = ["status.json", "summary.md", "playbook_comparison/playbook_initial.txt",
            "playbook_comparison/playbook_after.txt", "playbook_comparison/changes.diff",
            "playbooks/dreaddit/current.txt", "playbooks/dreaddit/current.json", "playbooks/dreaddit/current.manifest.json",
            "candidates/current.txt", "candidates/current.json"]
        if (run / "query_progress.csv").exists():
            names.append("query_progress.csv")
        runtime.immutable(run / "final_manifest.json", {"status": status, "completed_queries": len(records),
            "planned_queries": len(jobs), **counts, "manuscript_eligible": False,
            "files": {name: runtime.file_hash(run / name) for name in names}})
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
    return report(run, "completed_36_with_technical_failures" if progress["technical_failures"] else "completed_36_exposures", terminal=True)


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_replay_not_resumable")
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
                return report(run, "stopped_budget_incomplete", terminal=True)
            except Exception as exc:
                runtime.write_json(run / "supervisor_error.json", {"at": runtime.legacy.now(), "error": str(exc)}, replace=True)
                report(run, "needs_attention_no_automatic_retry")
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "status"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--comparator-run", type=Path)
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        runtime.require(args.comparator_run is not None, "comparator_required")
        result = prepare(run, args.comparator_run.resolve())
    elif args.command == "status":
        verify(run)
        result = runtime.read(run / "status.json")
    else:
        runtime.require(args.authorize_local_inference, "explicit_local_inference_authorization_required")
        result = run_local(run)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
