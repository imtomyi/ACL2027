"""Offline v6 planning, candidate audit, and reporting checks; never runs inference."""

import argparse
import hashlib
import json
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
PLAN = PROJECT / "Storage/experiment_guidelines/warrantroute_flaw_detection_8h_v6.plan.json"
DATASETS = ["dreaddit", "goemotions", "cache", "parlamint-gb"]
AUDIT_CRITERIA = (
    "grounded_lesson", "reusable_not_memorized", "counterconditions_preserved",
    "no_unsupported_domain_inference", "no_duplicate_or_contradiction", "no_leakage",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path):
    with path.open("rb") as handle:
        hasher = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def workload(plan):
    require(plan["protocol_id"] == "warrantroute_flaw_detection_8h_v6", "Wrong protocol")
    require(plan["status"] == "design_only_not_launched", "Planner cannot launch a run")
    require(plan["task"] == "claim_sentence_flaw_detection_and_characterization", "Task drift")
    require(plan["datasets"] == DATASETS and plan["model"] == "gemma3:4b", "Scope drift")
    require(plan["method"] == "WarrantRoute-Lite", "Do not relabel Lite as full WarrantRoute")
    for key in ("paid_api_allowed", "generate_themes", "repair_claims",
                "evaluation_feedback_to_memory", "manuscript_eligible"):
        require(plan[key] is False, f"Disallowed scope: {key}")
    selection, calls, clock = plan["selection"], plan["calls"], plan["clock"]
    require(selection["policy"] == "prior_dev20_and_existing_eval100_subset", "Selection drift")
    require(selection["within_source_allowed"] == ["cache"], "Unapproved source exception")
    require(selection["development_n"] == 10 and selection["evaluation_n"] == 20
            and selection["optional_probe_n"] == 5, "Allocation drift")
    require(plan["epochs"] == 3 and plan["predictions_per_slot"] == 1, "Repetition drift")
    require(plan["core_checkpoints"] == ["E0", "E3"]
            and plan["optional_checkpoints"] == ["E1", "E2"], "Checkpoint drift")
    require(plan["optional_after_core_terminal"] is True, "Core quality must take priority")
    require(plan["quality_states"] == [True, False, None], "Unknown quality cannot be forced binary")
    require(calls == {"reference_per_unique_packet": 1, "review_per_trajectory": 2,
                      "learning_per_development": 1, "patch_audit_per_development_max": 1,
                      "combined_quality_judge_per_evaluation": 1, "retries": 0}, "Call contract drift")
    require(clock["budget_seconds"] == 28800 and clock["reset_on_resume"] is False,
            "Eight-hour persisted budget required")
    require(clock["inference_admission_stop_seconds"] + clock["finalization_reserve_seconds"]
            == clock["budget_seconds"], "Missing finalization reservation")
    require(0 < clock["development_admission_stop_seconds"]
            < clock["inference_admission_stop_seconds"] < clock["budget_seconds"],
            "Invalid phase deadlines")
    require(plan["memory"]["audit_unknown_action"] == "withhold"
            and plan["memory"]["evaluation_read_only"] is True, "Unsafe memory policy")

    n = len(plan["datasets"])
    dev_unique, eval_unique = n * selection["development_n"], n * selection["evaluation_n"]
    unique, dev = dev_unique + eval_unique, dev_unique * plan["epochs"]
    core = eval_unique * len(plan["core_checkpoints"])
    optional = n * selection["optional_probe_n"] * len(plan["optional_checkpoints"])
    refs = unique * calls["reference_per_unique_packet"]
    dev_reviews = dev * calls["review_per_trajectory"]
    learning = dev * calls["learning_per_development"]
    audit = dev * calls["patch_audit_per_development_max"]
    eval_reviews = core * calls["review_per_trajectory"]
    quality = core * calls["combined_quality_judge_per_evaluation"]
    core_calls = refs + dev_reviews + learning + audit + eval_reviews + quality
    optional_calls = optional * (calls["review_per_trajectory"]
                                 + calls["combined_quality_judge_per_evaluation"])
    counts = {
        "unique_packets": unique, "unique_development_packets": dev_unique,
        "unique_evaluation_packets": eval_unique, "development_exposures": dev,
        "core_evaluation_reviews": core, "core_quality_bundles": core,
        "optional_evaluation_reviews": optional, "reference_calls": refs,
        "development_review_calls": dev_reviews, "learning_calls": learning,
        "patch_audit_calls_max": audit, "core_evaluation_review_calls": eval_reviews,
        "core_quality_calls": quality, "core_calls_max": core_calls,
        "optional_calls_max": optional_calls, "all_calls_max": core_calls + optional_calls,
        "planned_snapshots": n * (plan["epochs"] + 1),
        "core_quality_rows": n * len(plan["core_checkpoints"]), "playbook_summary_rows": n,
    }
    require(counts == plan["expected"], "Workload arithmetic mismatch")
    return counts


def quality_counts(states, planned_n):
    """Keep semantic unknown, technical failure, and unprocessed work distinct."""
    require(type(planned_n) is int and planned_n > 0, "Invalid planned denominator")
    require(len(states) <= planned_n, "More outcomes than scheduled items")
    true = false = unknown = technical = 0
    for state in states:
        if state is True:
            true += 1
        elif state is False:
            false += 1
        elif state is None:
            unknown += 1
        elif type(state) is str and state == "technical_failure":
            technical += 1
        else:
            raise ValueError("Unknown quality outcome")
    unprocessed = planned_n - len(states)
    missing = technical + unprocessed
    binary = true + false
    return {
        "planned_n": planned_n, "true": true, "false": false, "null": unknown,
        "technical": technical, "unprocessed": unprocessed, "E": missing,
        "binary_n": binary, "resolved_case_pct": 100 * true / binary if binary else None,
        "binary_coverage_pct": 100 * binary / planned_n,
        "full_panel_pct": 100 * true / planned_n if unknown + missing == 0 else None,
        "missingness_bound_not_ci": [100 * true / planned_n,
                                     100 * (true + unknown + missing) / planned_n],
    }


def can_commit_patch_batch(code_checks_passed, audits, proposed_count):
    require(type(proposed_count) is int and 0 <= proposed_count <= 2, "Invalid patch count")
    if not proposed_count or code_checks_passed is not True or len(audits) != proposed_count:
        return False
    return all(set(audit) == set(AUDIT_CRITERIA)
               and all(audit[key] is True for key in AUDIT_CRITERIA) for audit in audits)


def selected_checkpoint(completed_epochs_by_dataset, plan):
    require(set(completed_epochs_by_dataset) == set(plan["datasets"]), "Missing corpus epochs")
    for values in completed_epochs_by_dataset.values():
        require(values and 0 in values and set(values) == set(range(max(values) + 1))
                and max(values) <= plan["epochs"], "Incomplete epoch chain")
    epoch = min(max(values) for values in completed_epochs_by_dataset.values())
    return {"epoch": epoch, "label": "E3" if epoch == 3 else f"budget_limited_E{epoch}",
            "adaptation_completed": epoch == plan["epochs"]}


def next_phase(elapsed_seconds, core_terminal, optional_fits, plan):
    require(math.isfinite(elapsed_seconds) and elapsed_seconds >= 0, "Invalid elapsed time")
    clock = plan["clock"]
    if elapsed_seconds >= clock["budget_seconds"]:
        return "stopped_at_budget"
    if elapsed_seconds >= clock["inference_admission_stop_seconds"]:
        return "finalize_only"
    if not core_terminal:
        return "mandatory_core"
    return "optional_probes" if optional_fits else "finalize_only"


def evaluation_schedule(selected_ids, checkpoint, plan):
    """Pair checkpoint reviews in corpus round-robin order, with immediate judging."""
    require(type(checkpoint) is int and 0 <= checkpoint <= plan["epochs"], "Invalid checkpoint")
    require(set(selected_ids) == set(plan["datasets"]), "Missing corpus panel")
    for ids in selected_ids.values():
        require(len(ids) == plan["selection"]["evaluation_n"] and len(set(ids)) == len(ids),
                "Invalid evaluation panel")
    jobs = []
    for position in range(plan["selection"]["evaluation_n"]):
        for ds in plan["datasets"]:
            for epoch in sorted({0, checkpoint}):
                packet_id = selected_ids[ds][position]
                jobs.append({"dataset": ds, "packet_id": packet_id, "epoch": epoch,
                             "judge_immediately": True, "position": position + 1,
                             "id": f"core/{ds}/E{epoch}/{packet_id}"})
    return jobs


def candidate_audit(plan):
    """Inspect proposed ID subsets without freezing inputs or sending source text."""
    source = PROJECT / plan["candidate_run"]
    manifest, inputs = read(source / "manifest.json"), read(source / "inputs.private.json")
    require(file_hash(source / "inputs.private.json") == manifest["files"]["inputs.private.json"],
            "Candidate manifest/input hash mismatch")
    reports = {}
    for ds in plan["datasets"]:
        picked, ids_by_phase, input_hashes = {}, {}, {}
        for phase in ("development", "evaluation"):
            path = Path(manifest["splits"][ds][phase + "_file"])
            actual = file_hash(path)
            require(actual == manifest["splits"][ds][phase + "_file_sha256"], "Bank hash changed")
            ids = [packet["packet_id"] for packet in inputs[ds][phase]]
            require(len(ids) == len(set(ids)), "Duplicate candidate packet ID")
            ids = sorted(ids, key=lambda packet_id: digest([
                plan["selection"]["order_seed"], "gemma8h-v6", ds, phase, packet_id]))
            ids = ids[:plan["selection"][phase + "_n"]]
            require(len(ids) == plan["selection"][phase + "_n"], "Insufficient candidates")
            chosen = set(ids)
            rows = {}
            with path.open() as handle:
                for line in handle:
                    if line.strip():
                        row = json.loads(line)
                        if row["packet_id"] in chosen:
                            require(row["packet_id"] not in rows, "Duplicate selected packet in bank")
                            rows[row["packet_id"]] = row
            require(set(rows) == chosen, "Missing selected packet")
            picked[phase] = [rows[packet_id] for packet_id in ids]
            ids_by_phase[phase] = ids
            input_hashes[phase] = actual
        require(not set(ids_by_phase["development"]) & set(ids_by_phase["evaluation"]),
                "Packet overlap")

        def values(phase, key):
            return {str(s[key]) for row in picked[phase] for s in row["source_text_context"]
                    if s.get(key) not in (None, "")}

        overlap = {key: len(values("development", key) & values("evaluation", key))
                   for key in ("text", "source_record_id", "source_id")}
        missing_source = sum(not s.get("source_id") for rows in picked.values()
                             for row in rows for s in row["source_text_context"])
        require(not overlap["text"] and not overlap["source_record_id"], "Record/text overlap")
        require(ds in plan["selection"]["within_source_allowed"] or not overlap["source_id"],
                "Unapproved within-source split")
        require(missing_source == 0, "Missing source identity")
        reports[ds] = {
            "candidate_ids_not_frozen": ids_by_phase, "source_file_hashes": input_hashes,
            "overlap": overlap, "missing_source_ids": missing_source,
            "split_label": "within_source_diagnostic" if overlap["source_id"] else "recorded_source_disjoint",
            "unique_claim_sentences": len({row["llm_generated_qualitative_claim"]["claim"]
                                            for rows in picked.values() for row in rows}),
            "selection_hash": digest(ids_by_phase),
        }
    return {"status": "candidate_audit_only_not_frozen_or_authorized",
            "evaluation_reuse_authorized": plan["selection"]["evaluation_panel_reuse_authorized"],
            "datasets": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-candidates", action="store_true")
    parser.add_argument("--output", type=Path, help="New planning JSON under Storage; refuses overwrite")
    args = parser.parse_args()
    plan = read(PLAN)
    result = {"status": "offline_plan_not_inference", "plan_sha256": file_hash(PLAN),
              "workload": workload(plan), "panel_decision": plan["selection"]["decision"],
              "timing_scenarios_not_eta": {
                  str(s): {"core_hours": plan["expected"]["core_calls_max"] * s / 3600,
                           "with_optional_hours": plan["expected"]["all_calls_max"] * s / 3600}
                  for s in (15, 20, 25)}}
    if args.audit_candidates:
        result["candidate_audit"] = candidate_audit(plan)
    if args.output:
        path = args.output.resolve()
        require(path.is_relative_to((PROJECT / "Storage").resolve()), "Output must be private Storage")
        with path.open("x") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
