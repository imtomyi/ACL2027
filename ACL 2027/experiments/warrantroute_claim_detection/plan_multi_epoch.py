"""Build candidate job identities for claim detection. No LLM calls or execution."""

import argparse
import hashlib
import json
from pathlib import Path


DATASETS = ("dreaddit", "goemotions", "cache", "parlamint-gb")
MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def packet_ids(rows, expected):
    ids = [row["packet_id"] if isinstance(row, dict) else row for row in rows]
    if any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("Packet IDs must be nonempty strings")
    if len(ids) != expected or len(set(ids)) != expected:
        raise ValueError("Wrong packet count or duplicate packet ID")
    return sorted(ids)


def validate_config(config):
    if config["protocol"] != "claim_detection_multi_epoch_v4":
        raise ValueError("Unexpected protocol")
    if tuple(config["datasets"]) != DATASETS or tuple(config["models"]) != MODELS:
        raise ValueError("Dataset/model conditions must match v4")
    for key in ("epochs", "development_n", "evaluation_n", "probe_n"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"Invalid positive integer: {key}")
    if config["probe_n"] > config["evaluation_n"]:
        raise ValueError("Probe exceeds evaluation panel")
    if type(config["order_seed"]) is not int:
        raise ValueError("Invalid order seed")
    if (config["playbook_reset_between_epochs"] is not False
            or config["evaluation_feedback_to_memory"] is not False
            or config["score_based_early_stopping"] is not False):
        raise ValueError("Forbidden memory reset, feedback leakage or score-based stopping")
    if (config["review_policy"] != "merged_review"
            or config["learning_policy"] != "three_call_feedback_updater_guard"):
        raise ValueError("Unadopted call policy requires a separately revised protocol")
    checkpoints = config["checkpoints"]
    if [cp["after_epoch"] for cp in checkpoints] != list(range(config["epochs"] + 1)):
        raise ValueError("Exactly one ordered checkpoint per epoch, including E0, required")
    for cp in checkpoints:
        if (type(cp["after_epoch"]) is not int
                or cp["id"] != f'E{cp["after_epoch"]}'
                or cp["scope"] not in ("full", "probe")):
            raise ValueError("Invalid checkpoint")
    by_id = {cp["id"]: cp for cp in checkpoints}
    for key in ("primary_comparison", "secondary_comparison"):
        pair = config[key]
        if len(pair) != 2 or len(set(pair)) != 2:
            raise ValueError("A paired contrast requires two distinct checkpoints")
        if any(cp not in by_id or by_id[cp]["scope"] != "full" for cp in pair):
            raise ValueError("Primary/secondary contrasts require full matched panels")


def build_plan(config, inputs):
    validate_config(config)
    config_hash = digest(config)
    selection = {}
    for ds in DATASETS:
        dev = packet_ids(inputs[ds]["development"], config["development_n"])
        evaluation = packet_ids(inputs[ds]["evaluation"], config["evaluation_n"])
        if set(dev) & set(evaluation):
            raise ValueError(f"Development/evaluation ID overlap: {ds}")
        rank = lambda packet: digest([config["order_seed"], ds, "probe", packet])
        selection[ds] = {
            "development": dev,
            "evaluation": evaluation,
            "probe": sorted(evaluation, key=rank)[:config["probe_n"]],
        }
    selection_hash = digest(selection)
    namespace = digest([config_hash, selection_hash])
    jobs = []
    snapshots = []
    for ds in DATASETS:
        for model in MODELS:
            previous = f"seed:{namespace}:{ds}:{model}"
            endpoints = {0: previous}
            for epoch in range(1, config["epochs"] + 1):
                order = sorted(selection[ds]["development"], key=lambda packet: digest(
                    [config["order_seed"], ds, "development", epoch, packet]))
                for position, packet in enumerate(order, 1):
                    job_id = digest([namespace, ds, model, "development", epoch, packet])
                    jobs.append({
                        "job_id": job_id, "phase": "development", "dataset": ds,
                        "model": model, "packet_id": packet, "epoch": epoch,
                        "position": position, "exposure_index":
                            (epoch - 1) * config["development_n"] + position,
                        "previous_memory_event": previous,
                        "lock_prediction_before_reference": True,
                        "memory_updates_allowed": True,
                    })
                    previous = job_id
                endpoints[epoch] = previous
            for cp in config["checkpoints"]:
                snapshot_id = digest([namespace, ds, model, "snapshot", cp["id"]])
                snapshots.append({
                    "snapshot_id": snapshot_id, "dataset": ds, "model": model,
                    "checkpoint": cp["id"], "after_epoch": cp["after_epoch"],
                    "after_memory_event": endpoints[cp["after_epoch"]],
                })
                panel = selection[ds]["evaluation" if cp["scope"] == "full" else "probe"]
                for packet in panel:
                    jobs.append({
                        "job_id": digest([namespace, ds, model, "evaluation",
                                          "warrantroute", cp["id"], packet]),
                        "phase": "evaluation", "dataset": ds, "model": model,
                        "method": "warrantroute", "packet_id": packet,
                        "checkpoint": cp["id"], "snapshot_id": snapshot_id,
                        "memory_updates_allowed": False,
                    })
            for method in ("generalist", "qualitative_methods", "all_roles"):
                for packet in selection[ds]["evaluation"]:
                    jobs.append({
                        "job_id": digest([namespace, ds, model, "evaluation", method, packet]),
                        "phase": "evaluation", "dataset": ds, "model": model,
                        "method": method, "packet_id": packet,
                        "memory_updates_allowed": False,
                    })
    # The serialized order cannot accidentally interleave evaluation feedback with adaptation.
    jobs.sort(key=lambda job: job["phase"] != "development")
    if len({job["job_id"] for job in jobs}) != len(jobs):
        raise ValueError("Duplicate job identity")
    dev_count = sum(job["phase"] == "development" for job in jobs)
    eval_count = len(jobs) - dev_count
    return {
        "status": "candidate_schedule_only_not_runnable",
        "protocol": config["protocol"], "config_sha256": config_hash,
        "selection_sha256": selection_hash, "job_namespace": namespace,
        "eligibility": "claim_text_source_overlap_and_probe_source_balance_reaudit_required",
        "reference_preparation_and_judging": "separate_required_jobs_not_in_this_schedule",
        "candidate_packet_ids": selection,
        "counts": {
            "unique_packets": sum(len(s["development"]) + len(s["evaluation"])
                                  for s in selection.values()),
            "development_episodes": dev_count, "evaluation_outputs": eval_count,
            "review_and_development_jobs": len(jobs), "snapshots": len(snapshots),
            "external_evaluation_judgments_required": eval_count,
        },
        "snapshots": snapshots,
        "jobs": jobs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).with_name("multi_epoch_v4.json"))
    parser.add_argument("--candidate-inputs", type=Path, required=True,
                        help="Read only packet IDs from a historical candidate input inventory")
    parser.add_argument("--output", type=Path, help="New candidate plan file; never overwrite")
    args = parser.parse_args()
    inventory_bytes = args.candidate_inputs.read_bytes()
    plan = build_plan(json.loads(args.config.read_text()), json.loads(inventory_bytes))
    plan["candidate_inventory_sha256"] = hashlib.sha256(inventory_bytes).hexdigest()
    plan["candidate_inventory_path"] = str(args.candidate_inputs.resolve())
    plan["planner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan["plan_sha256"] = digest(plan)
    if args.output:
        storage = Path(__file__).resolve().parents[2] / "Storage"
        if not args.output.resolve().is_relative_to(storage.resolve()):
            parser.error("Candidate schedules must be written under project Storage")
        with args.output.open("x") as handle:
            json.dump(plan, handle, indent=2)
            handle.write("\n")
    print(json.dumps({"status": plan["status"], "counts": plan["counts"],
                      "plan_sha256": plan["plan_sha256"],
                      "output": str(args.output.resolve()) if args.output else None}, indent=2))


if __name__ == "__main__":
    main()
