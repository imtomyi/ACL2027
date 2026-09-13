"""Read-only v5 design consistency checks. No inference or experiment writes."""

import argparse
import json
from pathlib import Path


PLAN = Path(__file__).resolve().parents[2] / (
    "Storage/experiment_guidelines/warrantroute_flaw_detection_v5.plan.json"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_plan(plan):
    require(plan["protocol_id"] == "warrantroute_flaw_detection_v5", "Wrong protocol")
    require(plan["status"] == "design_finalized_not_authorized_for_inference",
            "A design check must not authorize inference")
    require(plan["task"] == "detect_and_characterize_flaws_in_supplied_claims",
            "Task must remain flaw detection")
    for key in ("generate_themes", "repair_claims", "evaluation_feedback_to_memory",
                "paid_api_allowed", "manuscript_eligible_with_current_candidates"):
        require(plan[key] is False, f"Disallowed scope change: {key}")

    pilot, main = plan["pilot"], plan["main"]
    require(pilot["datasets"] == ["dreaddit", "goemotions", "cache"],
            "Pilot source exception cannot be silently expanded")
    require(pilot["models"] == ["gemma3:4b"], "Pilot must be Gemma only")
    require(pilot["deferred_dataset"] == "parlamint-gb", "Missing pilot deferral")
    require(pilot["budget_seconds"] == 14400, "Pilot must retain four-hour cap")
    require(main["datasets"] == ["dreaddit", "goemotions", "cache", "parlamint-gb"],
            "Main corpus inventory changed")
    require(main["models"] == ["qwen3:8b", "llama3.1:8b", "gemma3:4b"],
            "Main model inventory changed")
    require(main["methods"] == ["generalist", "fixed_role", "all_roles", "warrantroute"],
            "Main method inventory changed")
    require(main["fixed_role"] == "qualitative_methods", "Fixed role drift")
    require(main["baseline_calls"] == {"generalist": 1, "fixed_role": 1, "all_roles": 4},
            "Baseline call contract changed")
    require(main["order_realizations"] == main["predictions_per_slot"] == 1,
            "Epochs must not be counted as independent replications")
    require(main["retries"] == 0, "Retry policy changed")
    require(main["reference_calls_per_packet"] == 3, "Reference preparation changed")
    require(main["reference_proposers"] == ["qwen3:8b", "llama3.1:8b"]
            and main["reference_reconciler"] == "gemma3:4b", "Reference model drift")
    require(main["quality_judge"] == "qwen3:8b", "Judge identity drift")
    require(main["max_review_calls"] == 5 and pilot["review_calls"] == 2,
            "Main and Lite review contracts must stay distinct")

    for scope in (pilot, main):
        require(scope["within_source_allowed"] == ["cache"], "Source exception drift")
        require(scope["quality_states"] == [True, False, None], "Unknown judgments lost")
        require(scope["epochs"] == 3 and scope["learning_calls"] == 1,
                "Learning contract changed")
        require(scope["judge_calls_per_output"] == 1, "Judge-call count changed")
        require(0 < scope["probe_n"] <= scope["evaluation_n"], "Invalid probe size")
    require(pilot["development_n"] == 5 and pilot["evaluation_n"] == 15,
            "Pilot sample allocation changed")
    require(main["development_n"] == 20 and main["evaluation_n"] == 100,
            "Main sample allocation changed")
    require(pilot["checkpoints"] == {"E0": 5, "E1": 5, "E2": 5, "E3": 15},
            "Pilot matched-probe schedule changed")
    require(main["memory"] == {"active_rules_max": 40, "retrieval_max": 6,
                               "immutable_seed_rules": 2, "delta_operations_max": 2,
                               "reset_between_epochs": False}, "Memory contract drift")

    arms = {arm["id"]: arm for arm in main["arms"]}
    require(len(arms) == len(main["arms"]) == 5, "Duplicate or missing arm")
    require(set(arms) == {"full", "no_explicit_reflection", "full_memory_rewrite",
                          "one_epoch", "frozen_seed"}, "Ablation inventory changed")
    learned = [arm for arm in arms.values() if arm["learned"]]
    require(len(learned) == 3, "Checkpoint controls must not be extra learned runs")
    require(arms["one_epoch"]["reuse"] == "full:E1"
            and arms["frozen_seed"]["reuse"] == "full:E0", "Incorrect checkpoint reuse")
    require(arms["full"]["evaluation"] == {"E0": 100, "E1": 100, "E2": 20, "E3": 100},
            "Main matched-panel schedule changed")
    for arm in learned:
        require(arm["epochs"] == main["epochs"], "Unmatched learned-arm epochs")
        if arm["id"] != "full":
            require(arm["evaluation"] == {"E3": 100}, "Ablation evaluation drift")
    require(arms["full"]["explicit_reflection"] is True
            and arms["full"]["update"] == "delta", "Full arm drift")
    require(arms["no_explicit_reflection"]["explicit_reflection"] is False
            and arms["no_explicit_reflection"]["update"] == "delta", "Reflection ablation drift")
    require(arms["full_memory_rewrite"]["explicit_reflection"] is True
            and arms["full_memory_rewrite"]["update"] == "rewrite", "Delta ablation drift")
    require(main["component_contrasts"] == [
        ["full:E3", "no_explicit_reflection:E3"],
        ["full:E3", "full:E1"],
        ["full:E3", "full_memory_rewrite:E3"],
    ], "Component contrasts changed")

    p = len(pilot["datasets"])
    unique = p * (pilot["development_n"] + pilot["evaluation_n"])
    dev = p * pilot["development_n"] * pilot["epochs"]
    evaluation = p * sum(pilot["checkpoints"].values())
    reference = unique * pilot["reference_calls_per_packet"]
    judge = evaluation * pilot["judge_calls_per_output"]
    pilot_counts = {
        "unique_packets": unique, "development_episodes": dev,
        "evaluation_outputs": evaluation, "judge_calls": judge, "reference_calls": reference,
        "max_semantic_calls": reference + judge + evaluation * pilot["review_calls"]
        + dev * (pilot["review_calls"] + pilot["learning_calls"]),
    }

    corpora = len(main["datasets"])
    cells = corpora * len(main["models"])
    unique = corpora * (main["development_n"] + main["evaluation_n"])
    dev = cells * main["development_n"] * sum(arm["epochs"] for arm in learned)
    full = cells * sum(arms["full"]["evaluation"].values())
    warrant = cells * sum(sum(arm["evaluation"].values()) for arm in learned)
    baseline = cells * main["evaluation_n"] * len(main["baseline_calls"])
    baseline_calls = cells * main["evaluation_n"] * sum(main["baseline_calls"].values())
    evaluation = warrant + baseline
    judge = evaluation * main["judge_calls_per_output"]
    reference = unique * main["reference_calls_per_packet"]
    warrant_calls = warrant * main["max_review_calls"]
    dev_calls = dev * (main["max_review_calls"] + main["learning_calls"])
    main_counts = {
        "unique_packets": unique, "learned_memory_branches": cells * len(learned),
        "development_episodes": dev, "full_evaluation_outputs": full,
        "additional_ablation_outputs": warrant - full,
        "warrantroute_evaluation_outputs": warrant, "baseline_outputs": baseline,
        "evaluation_outputs": evaluation, "judge_calls": judge, "reference_calls": reference,
        "baseline_generation_calls": baseline_calls,
        "max_warrantroute_evaluation_calls": warrant_calls, "max_development_calls": dev_calls,
        "max_semantic_calls": reference + judge + warrant_calls + baseline_calls + dev_calls,
        "snapshots": cells * (1 + sum(arm["epochs"] for arm in learned)),
        "final_table_rows": cells * len(main["methods"]),
        "ablation_comparison_rows": cells * len(main["component_contrasts"]),
        "fixed_probe_curve_rows": cells * len(arms["full"]["evaluation"]),
    }
    require(pilot_counts == pilot["expected"], "Pilot workload arithmetic mismatch")
    require(main_counts == main["expected"], "Main workload arithmetic mismatch")
    return {"status": "design_checks_passed_not_execution_validation",
            "pilot": pilot_counts, "main": main_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args()
    print(json.dumps(verify_plan(json.loads(args.plan.read_text())), indent=2))


if __name__ == "__main__":
    main()
