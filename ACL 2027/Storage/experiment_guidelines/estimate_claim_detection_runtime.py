"""Compare prospective call-budget designs using journals; no inference/writes."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")
ROLES = ("proposer", "evidence_scout", "methods_challenger",
         "domain_challenger", "reviser")
DESIGNS = ("v2", "merged_review", "merged_review_and_learning")


def historical_rates(results):
    by_model = defaultdict(list)
    by_role = defaultdict(lambda: defaultdict(list))
    for path in sorted(results.glob("**/calls/*.json")):
        record = json.loads(path.read_text())
        model = record.get("model")
        if record.get("status") != "complete" or model not in MODELS:
            continue
        duration = record.get("total_duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            continue
        seconds = duration / 1e9
        by_model[model].append(seconds)
        by_role[model][record["role"]].append(seconds)

    rates = {}
    for model in MODELS:
        if not by_model[model]:
            raise ValueError(f"No complete service-duration records for {model}")
        measured = {role: statistics.mean(values)
                    for role, values in by_role[model].items()}
        fallback = max(measured.values())
        role_means = {role: measured.get(role, fallback) for role in ROLES}
        p, s, m, d, r = (role_means[role] for role in ROLES)
        mean = statistics.mean(by_model[model])
        rates[model] = {
            "complete_calls": len(by_model[model]),
            "mean_seconds": mean,
            "median_seconds": statistics.median(by_model[model]),
            "role_mean_seconds": role_means,
            "role_counts": {role: len(by_role[model][role]) for role in ROLES},
            "fallback_roles": [role for role in ROLES if role not in measured],
            "warrant_seconds": p + 2 * s + m + d + r,
            "baseline_group_seconds": 2 * p + 2 * m + d + r,
            "development_seconds_excluding_feedback": p + 2 * s + m + d + r + 2 * mean,
        }
    return rates


def estimate(rates, development_per_corpus, evaluation_per_corpus, probe, middle,
             design="v2", epochs=1, full_checkpoints=2):
    if design not in DESIGNS:
        raise ValueError(f"Unknown design: {design}")
    for name, value in (("epochs", epochs), ("full_checkpoints", full_checkpoints)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    corpora, models = 4, len(MODELS)
    merge_review = design != "v2"
    merge_learning = design == "merged_review_and_learning"
    development_episodes = corpora * models * development_per_corpus * epochs
    baseline_outputs = corpora * models * evaluation_per_corpus * 3
    warrant_per_cell = full_checkpoints * evaluation_per_corpus + middle * probe
    warrant_outputs = corpora * models * warrant_per_cell
    evaluation_outputs = baseline_outputs + warrant_outputs
    development_feedback_calls = 0 if merge_learning else development_episodes
    quality_bundles = evaluation_outputs + development_feedback_calls
    unique_packets = corpora * (development_per_corpus + evaluation_per_corpus)
    generation = 0.0
    for rate in rates.values():
        warrant = rate["warrant_seconds"]
        if merge_review:
            scout = rate["role_mean_seconds"]["evidence_scout"]
            reviser = rate["role_mean_seconds"]["reviser"]
            # The combined output may be longer than either historical stage.
            warrant = warrant - scout - reviser + 1.25 * max(scout, reviser)
        learning = (1.5 if merge_learning else 2.0) * rate["mean_seconds"]
        generation += corpora * (
            warrant_per_cell * warrant
            + evaluation_per_corpus * rate["baseline_group_seconds"]
            + development_per_corpus * epochs * (warrant + learning)
        )
    reference = unique_packets * sum(
        rates[model]["role_mean_seconds"]["proposer"] for model in MODELS[:2]
    )
    lower = (generation + reference + quality_bundles * 15) / 3600
    upper = (1.75 * (generation + reference) + quality_bundles * 45) / 3600
    review_calls = 5 if merge_review else 6
    learning_calls = 1 if merge_learning else 3
    max_semantic_calls = (corpora * models * evaluation_per_corpus * 6
                          + warrant_outputs * review_calls
                          + development_episodes * (review_calls + learning_calls)
                          + evaluation_outputs + 2 * unique_packets)
    return {
        "design": design,
        "epochs": epochs,
        "full_checkpoints": full_checkpoints,
        "unique_packets": unique_packets,
        "development_episodes": development_episodes,
        "baseline_outputs": baseline_outputs,
        "warrantroute_outputs": warrant_outputs,
        "evaluation_outputs": evaluation_outputs,
        "quality_bundles_including_development": quality_bundles,
        "separate_development_feedback_calls": development_feedback_calls,
        "integrated_learning_calls": development_episodes if merge_learning else 0,
        "reference_calls": 2 * unique_packets,
        "max_warrantroute_calls_per_packet": review_calls,
        "max_development_calls_per_episode": review_calls + learning_calls,
        "max_total_semantic_calls": max_semantic_calls,
        "generation_proxy_hours": generation / 3600,
        "reference_proxy_hours": reference / 3600,
        "judging_hours_at_15_seconds": quality_bundles * 15 / 3600,
        "judging_hours_at_45_seconds": quality_bundles * 45 / 3600,
        "lower_planning_hours": lower,
        "upper_planning_hours": upper,
    }


def main():
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=project / (
        "Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/"
        "n100_same_model_table3_20260905_v2/results"))
    args = parser.parse_args()
    if not args.results.is_dir():
        parser.error(f"Historical results directory not found: {args.results}")
    rates = historical_rates(args.results)
    main_run = estimate(rates, development_per_corpus=20,
                        evaluation_per_corpus=100, probe=20, middle=3)
    pilot = estimate(rates, development_per_corpus=2,
                     evaluation_per_corpus=4, probe=0, middle=0)
    assert main_run["evaluation_outputs"] == 6720
    assert main_run["reference_calls"] == 960
    assert pilot["evaluation_outputs"] == 240
    assert pilot["reference_calls"] == 48
    comparisons = {
        design: {
            "pilot": estimate(rates, 2, 4, 0, 0, design=design),
            "main_experiment": estimate(rates, 20, 100, 20, 3, design=design),
        }
        for design in DESIGNS
    }
    assert main_run["max_total_semantic_calls"] == 35760
    assert comparisons["merged_review"]["main_experiment"]["max_total_semantic_calls"] == 32400
    assert comparisons["merged_review_and_learning"]["main_experiment"]["max_total_semantic_calls"] == 31920
    multi_epoch = {
        design: estimate(rates, 20, 100, 20, 1, design=design,
                         epochs=3, full_checkpoints=3)
        for design in DESIGNS[1:]
    }
    for result in multi_epoch.values():
        assert result["unique_packets"] == 480
        assert result["development_episodes"] == 720
        assert result["evaluation_outputs"] == 7440
        assert result["reference_calls"] == 960
    print(json.dumps({
        "status": "prospective_estimate_not_live_eta",
        "current_design": "merged_review",
        "current_schedule": "v4_three_epochs_E0_E1_E2probe_E3",
        "candidate_not_adopted": "merged_review_and_learning",
        "source": str(args.results.resolve()),
        "assumptions": {
            "execution": "serial local inference",
            "generation_reference_multiplier": [1.0, 1.75],
            "judge_seconds_per_bundle": [15, 45],
            "merged_review_proxy": "1.25 * max(scout_mean, reviser_mean)",
            "merged_learning_proxy": "1.5 * overall_model_call_mean",
            "merged_stage_warning": "Unmeasured assumptions; fewer calls may not reduce wall time",
            "excluded": ["implementation", "eligibility remediation",
                         "unbounded retries", "machine downtime"],
            "warning": "Planning scenarios, not confidence intervals or upper guarantees",
        },
        "historical_rates": rates,
        "pilot": pilot,
        "main_experiment": main_run,
        "legacy_top_level_scope": "v2 retained for reproducibility; see design_comparisons for changes",
        "design_comparisons": comparisons,
        "multi_epoch_v4": multi_epoch,
        "multi_epoch_pilot_v4": {
            design: estimate(rates, 2, 4, 0, 0, design=design,
                             epochs=3, full_checkpoints=4)
            for design in DESIGNS[1:]
        },
    }, indent=2))


if __name__ == "__main__":
    main()
