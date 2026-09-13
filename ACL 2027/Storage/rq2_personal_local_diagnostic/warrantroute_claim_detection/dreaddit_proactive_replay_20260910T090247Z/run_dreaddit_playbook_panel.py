"""Configurable new-data development panels with frozen ancestry and bounded execution."""

import argparse
import difflib
import fcntl
import json
from pathlib import Path
import shutil
import time

import run_dreaddit_playbook_growth as growth

contract, memory, runtime, smoke = growth.contract, growth.memory, growth.runtime, growth.smoke
VERSION = "dreaddit-new-paragraph-panel-v1"
CODE = [*growth.CODE, Path(__file__).name]
PROTOCOL = "Storage/experiment_guidelines/dreaddit_new_paragraph_panel_v1.md"


def ancestry(prior):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    rows, seen, lineage = {}, set(), []
    current = prior
    while current is not None:
        current = current.resolve()
        runtime.require(current.is_relative_to(storage) and current not in seen, "invalid_panel_ancestry")
        seen.add(current)
        for name in ("manifest.json", "final_manifest.json"):
            growth.previous.check_files(current, runtime.read(current / name))
        for packet in runtime.read(current / "inputs.private.json"):
            runtime.require(runtime.digest(packet["task"]) == packet["task_sha256"], "ancestral_task_changed")
            if packet["packet_id"] in rows:
                runtime.require(rows[packet["packet_id"]] == packet, "ancestral_paragraph_identity_changed")
            rows[packet["packet_id"]] = packet
        lineage.append({"run": str(current), "final_manifest_sha256": runtime.file_hash(current / "final_manifest.json")})
        path = runtime.read(current / "config.json").get("prior_run")
        current = Path(path) if path else None
    return list(rows.values()), lineage


def select_panel(inputs, used, size):
    runtime.require(4 <= size <= 64 and size % 4 == 0, "panel_size_must_be_a_multiple_of_four")
    selected, eligible = [], None
    for _ in range(size // 4):
        batch, remaining = growth.select_new_paragraphs(inputs, [*used, *selected])
        if eligible is None:
            eligible = remaining
        selected.extend(batch)
    return selected, eligible


def prepare(run, prior, size=12, epochs=3, budget_seconds=1200, target=4):
    storage = (runtime.legacy.PROJECT / "Storage").resolve()
    runtime.require(run.is_relative_to(storage), "private_storage_only")
    runtime.require(epochs in (1, 3) and 600 <= budget_seconds <= 1800 and 1 <= target <= 12, "bounded_panel_parameters")
    used, lineage = ancestry(prior)
    config = runtime.read(prior / "config.json")
    source = Path(config["source_run"]).resolve()
    runtime.require(source.is_relative_to(storage), "private_source_only")
    growth.previous.check_files(source, runtime.read(source / "manifest.json"))
    selected, eligible = select_panel(runtime.read(source / "inputs.private.json"), used, size)
    initial = runtime.read(prior / "playbooks/dreaddit/current.json")
    memory.visible_rules(initial)
    final = runtime.read(prior / "final_manifest.json")
    prior_jobs = runtime.read(prior / "schedule.json")
    last = runtime.load_record(prior / "results" / prior_jobs[final["completed_queries"] - 1]["id"] / "result.json")
    runtime.require(last["value"]["state_after"] == initial, "parent_memory_binding")
    jobs = [j for j in growth.new_panel_jobs(selected) if j["epoch"] <= epochs]
    config.update(controller_protocol=VERSION, prior_run=str(prior),
        prior_final_manifest_sha256=runtime.file_hash(prior / "final_manifest.json"),
        prior_completed_queries=runtime.read(prior / "status.json")["cumulative_query_exposures"],
        prior_unique_paragraphs=len(used), new_unique_paragraphs=size,
        paragraph_n=size, epochs=epochs, additional_epochs=list(range(1, epochs + 1)),
        target_additional_rule_ids=target, budget_seconds=budget_seconds, call_ceiling=len(jobs) * 3,
        initial_rule_ids=[r["id"] for r in initial["rules"]],
        source_inputs_sha256=runtime.file_hash(source / "inputs.private.json"),
        eligible_unused_paragraphs_before_selection=eligible,
        selection=f"First {size} unused eligible original paragraphs in canonical source order, before outcomes.",
        inference_authorization=f"User requested {size} additional Dreaddit data points, not other corpora.",
        stop_rule="After every new paragraph has completed at least one query, stop if target new rule IDs were admitted and delivered later; otherwise stop at the frozen query/time limit.")
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inputs.private.json", selected),
                        ("initial_state.json", initial), ("schedule.json", jobs),
                        ("prompts.json", contract.PROMPTS), ("ancestry.json", lineage)):
        runtime.write_json(run / name, value)
    text = ["# New Dreaddit Data Points", "", "Source data, not operational instructions. Original text is retained in inputs.private.json.", ""]
    for packet in selected:
        text.extend([f"## {packet['source_record_id']}", "", f"Parent packet: `{packet['parent_packet_id']}`.", ""])
        text.extend("> " + line for line in packet["task"]["claim"].splitlines())
        text.append("")
    runtime.write_text(run / "data_points.md", "\n".join(text) + "\n")
    shutil.copyfile(runtime.legacy.PROJECT / PROTOCOL, run / "protocol.md")
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    runtime.publish_playbook(run, "dreaddit", initial)
    runtime.write_text(run / "playbook_comparison/playbook_initial.txt", memory.playbook_text(memory.visible_rules(initial)))
    files = [p for p in run.iterdir() if p.is_file()]
    files.append(run / "playbook_comparison/playbook_initial.txt")
    runtime.write_json(run / "manifest.json", {"protocol": contract.VERSION, "controller_protocol": VERSION,
        "created_at": runtime.legacy.now(), "files": {str(p.relative_to(run)): runtime.file_hash(p) for p in sorted(files)}})
    return report(run, "prepared_not_started")


def verify(run):
    manifest = runtime.read(run / "manifest.json")
    runtime.require(manifest["controller_protocol"] == VERSION, "wrong_panel_controller")
    growth.previous.check_files(run, manifest)
    for name in CODE:
        runtime.require(runtime.file_hash(Path(__file__).with_name(name)) == manifest["files"][name], "panel_source_changed:" + name)
    if (run / "final_manifest.json").exists():
        growth.previous.check_files(run, runtime.read(run / "final_manifest.json"))


def report(run, status, terminal=False):
    result = smoke.report(run, status)
    config = runtime.read(run / "config.json")
    counts = growth.growth_counts(run)
    completed = [runtime.load_record(p)["value"] for j in runtime.read(run / "schedule.json")
        if (p := run / "results" / j["id"] / "result.json").exists()]
    covered = len({row["packet_id"] for row in completed})
    result.update(counts, controller_protocol=VERSION, unique_paragraphs=config["paragraph_n"],
        epochs=config["epochs"], distinct_paragraphs_completed=covered,
        panel_covered=covered == config["paragraph_n"],
        learned_rules=counts["current_rule_count"] - len(memory.base.SEED),
        prior_completed_queries=config["prior_completed_queries"],
        cumulative_query_exposures=config["prior_completed_queries"] + len(completed),
        cumulative_distinct_paragraphs_completed=config["prior_unique_paragraphs"] + covered)
    result["ready_to_stop"] = result["target_delivered"] and result["panel_covered"]
    runtime.write_json(run / "status.json", result, replace=True)
    folder = run / "playbook_comparison"
    initial, after = (folder / "playbook_initial.txt").read_text(), (run / "playbooks/dreaddit/current.txt").read_text()
    runtime.write_text(folder / "playbook_after.txt", after, replace=True)
    difference = "".join(difflib.unified_diff(initial.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="playbook_initial.txt", tofile="playbook_after.txt"))
    runtime.write_text(folder / "changes.diff", difference, replace=True)
    lines = ["# New Dreaddit Panel", "", f"Status: `{status}`.", "",
        f"New paragraphs completed at least once: {covered}/{config['paragraph_n']}.",
        f"Completed query exposures: {len(completed)}/{result['planned_queries']}; up to {config['epochs']} epochs.",
        f"New distinct admitted rules: {counts['additional_rules_admitted']}/{config['target_additional_rule_ids']}.",
        f"New rules delivered in a later detector request: {counts['additional_rules_delivered']}.",
        f"Total rule count: {counts['initial_rule_count']} initially, {counts['current_rule_count']} currently.",
        f"Transport/schema errors: {result['technical_failures']}. Local calls: {result['local_model_calls']}. Paid calls: 0.", "",
        "## Files", "",
        "- [New data points](data_points.md)", "- [Per-query outcomes](query_progress.csv)",
        "- [Initial Playbook](playbook_comparison/playbook_initial.txt)",
        "- [After Playbook](playbook_comparison/playbook_after.txt)",
        "- [Exact changes](playbook_comparison/changes.diff)", "",
        "## Interpretation", "",
        "Only Dreaddit is run. Each data point is a complete original paragraph, not a generated claim.",
        "All ancestral records, source groups, normalized texts, and the frozen evaluation panel were excluded from selection.",
        "The prior memory is carried forward unchanged initially. Prompts, model/options, and admission criteria are unchanged.",
        "Rule additions are counted by new IDs, not refinements, reinforcements, repeated delivery, or file writes.",
        "No target-based stop is allowed before every new paragraph has completed at least one query.",
        "This is outcome-stopped development debugging. A rule's storage or delivery does not prove semantic validity or better detection.",
        "The inherited rule's documented quality concerns remain. No adjudicated gold is available for scoring these inputs.",
        "Accuracy, precision, recall, Credibility, and Conformability remain unassessed. No Table 3 or manuscript file is changed.", ""]
    runtime.write_text(run / "summary.md", "\n".join(lines), replace=True)
    if terminal:
        files = ["status.json", "summary.md", "playbook_comparison/playbook_initial.txt",
            "playbook_comparison/playbook_after.txt", "playbook_comparison/changes.diff",
            "playbooks/dreaddit/current.txt", "playbooks/dreaddit/current.json", "playbooks/dreaddit/current.manifest.json"]
        if (run / "query_progress.csv").exists():
            files.append("query_progress.csv")
        runtime.immutable(run / "final_manifest.json", {"status": status,
            "completed_queries": len(completed), "planned_queries": result["planned_queries"],
            "distinct_paragraphs_completed": covered, "ready_to_stop": result["ready_to_stop"],
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
        if progress["ready_to_stop"]:
            return report(run, "stopped_panel_covered_and_target_delivered", terminal=True)
    return report(run, "stopped_epoch_cap", terminal=True)


def run_local(run):
    verify(run)
    runtime.require(not (run / "final_manifest.json").exists(), "terminal_panel_not_resumable")
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
    parser.add_argument("--paragraphs", type=int, default=12)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--budget-seconds", type=int, default=1200)
    parser.add_argument("--target-new-rules", type=int, default=4)
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        runtime.require(args.prior_run is not None, "prior_run_required")
        result = prepare(run, args.prior_run.resolve(), args.paragraphs, args.epochs, args.budget_seconds, args.target_new_rules)
    elif args.command == "status":
        verify(run)
        result = runtime.read(run / "status.json")
    else:
        runtime.require(args.authorize_local_inference, "explicit_local_inference_authorization_required")
        result = run_local(run)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
