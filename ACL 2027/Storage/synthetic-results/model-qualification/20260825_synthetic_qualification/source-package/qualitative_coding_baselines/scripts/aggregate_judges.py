#!/usr/bin/env python3
"""Validate blinded model-judge records and aggregate diagnostic comparisons."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
DEFAULT_RUN_DIR = PROJECT_ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
JUDGE_SCHEMA = ROOT / "schemas" / "judge_output.schema.json"
MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4"]
JUDGES = ["gpt-5.6-sol", "gpt-5.5", "gpt-5.4"]
PACKETS = ["syn_dreaddit_01", "syn_agyw_01", "syn_kodis_01", "syn_candor_01"]
SCORE_FIELDS = [
    "evidential_support",
    "quote_attribution_fidelity",
    "voice_context_preservation",
    "negative_case_preservation",
    "analytic_contract_fit",
    "codebook_usability",
    "interpretive_usefulness",
    "parsimony",
    "overall_quality",
]


def avg(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bradley_terry_strength(
    wins: dict[tuple[str, str], float], comparisons: dict[tuple[str, str], float]
) -> dict[str, float]:
    """Regularized MM estimate; ties enter as half a win for each model."""
    strength = {model: 1.0 for model in MODELS}
    adjusted_wins = {model: 0.0 for model in MODELS}
    adjusted_n: dict[tuple[str, str], float] = {}
    for left, right in itertools.combinations(MODELS, 2):
        key = tuple(sorted((left, right)))
        n = comparisons.get(key, 0.0) + 1.0
        adjusted_n[key] = n
        adjusted_wins[left] += wins.get((left, right), 0.0) + 0.5
        adjusted_wins[right] += wins.get((right, left), 0.0) + 0.5
    for _ in range(1000):
        next_strength: dict[str, float] = {}
        for model in MODELS:
            denominator = 0.0
            for other in MODELS:
                if other == model:
                    continue
                key = tuple(sorted((model, other)))
                denominator += adjusted_n[key] / (strength[model] + strength[other])
            next_strength[model] = adjusted_wins[model] / denominator if denominator else 1.0
        geometric_mean = math.exp(avg([math.log(max(value, 1e-12)) for value in next_strength.values()]))
        next_strength = {key: value / geometric_mean for key, value in next_strength.items()}
        if max(abs(next_strength[key] - strength[key]) for key in MODELS) < 1e-10:
            strength = next_strength
            break
        strength = next_strength
    return strength


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    judge_dir = run_dir / "judges"
    schema = json.loads(JUDGE_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    map_rows = read_csv(run_dir / "blind_map_private.csv")
    blind_map = {
        (row["packet_id"], int(row["run_index"]), row["blind_id"]): row["model_id"]
        for row in map_rows
    }

    issues: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    preference_records: list[tuple[str, str, int, dict[str, int]]] = []
    record_keys: set[tuple[str, str, int]] = set()

    for path in sorted(judge_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    issues.append({"file": path.name, "line": line_number, "kind": "json_parse", "detail": str(error)})
                    continue
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
                for error in errors:
                    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
                    issues.append(
                        {
                            "file": path.name,
                            "line": line_number,
                            "kind": "schema",
                            "detail": f"{location}: {error.message}",
                        }
                    )
                judge_id = record.get("judge_model_id", "")
                packet_id = record.get("packet_id", "")
                run_index = int(record.get("run_index", 0))
                key = (judge_id, packet_id, run_index)
                if key in record_keys:
                    issues.append({"file": path.name, "line": line_number, "kind": "duplicate_record", "detail": str(key)})
                record_keys.add(key)
                seen_blinds: list[str] = []
                for candidate in record.get("candidate_scores", []):
                    blind_id = candidate.get("blind_id", "")
                    seen_blinds.append(blind_id)
                    model_id = blind_map.get((packet_id, run_index, blind_id), "")
                    if not model_id:
                        issues.append(
                            {
                                "file": path.name,
                                "line": line_number,
                                "kind": "blind_map_missing",
                                "detail": str((packet_id, run_index, blind_id)),
                            }
                        )
                    row: dict[str, Any] = {
                        "judge_model_id": judge_id,
                        "packet_id": packet_id,
                        "run_index": run_index,
                        "blind_id": blind_id,
                        "model_id": model_id,
                    }
                    for field in SCORE_FIELDS:
                        row[field] = candidate.get(field)
                    flags = candidate.get("serious_error_flags", [])
                    row["serious_error_count"] = len(flags)
                    row["serious_error_flags"] = "|".join(flags)
                    row["disposition"] = candidate.get("disposition", "")
                    row["confidence"] = candidate.get("confidence")
                    row["rationale"] = candidate.get("rationale", "")
                    score_rows.append(row)
                if sorted(seen_blinds) != ["B1", "B2", "B3", "B4", "B5"]:
                    issues.append(
                        {
                            "file": path.name,
                            "line": line_number,
                            "kind": "candidate_coverage",
                            "detail": str(seen_blinds),
                        }
                    )
                ranks: dict[str, int] = {}
                flattened: list[str] = []
                for rank, group in enumerate(record.get("preference_groups", []), start=1):
                    for blind_id in group:
                        flattened.append(blind_id)
                        model_id = blind_map.get((packet_id, run_index, blind_id), "")
                        if model_id:
                            ranks[model_id] = rank
                if sorted(flattened) != ["B1", "B2", "B3", "B4", "B5"]:
                    issues.append(
                        {
                            "file": path.name,
                            "line": line_number,
                            "kind": "preference_coverage",
                            "detail": str(flattened),
                        }
                    )
                preference_records.append((judge_id, packet_id, run_index, ranks))

    expected_keys = {(judge, packet, run) for judge in JUDGES for packet in PACKETS for run in (1, 2, 3)}
    missing_keys = sorted(expected_keys - record_keys)
    extra_keys = sorted(record_keys - expected_keys)
    if missing_keys:
        issues.append({"file": "", "line": "", "kind": "missing_judge_records", "detail": json.dumps(missing_keys)})
    if extra_keys:
        issues.append({"file": "", "line": "", "kind": "unexpected_judge_records", "detail": json.dumps(extra_keys)})

    score_fields = [
        "judge_model_id",
        "packet_id",
        "run_index",
        "blind_id",
        "model_id",
        *SCORE_FIELDS,
        "serious_error_count",
        "serious_error_flags",
        "disposition",
        "confidence",
        "rationale",
    ]
    write_csv(run_dir / "judge_scores_long.csv", score_rows, score_fields)
    write_csv(run_dir / "judge_validation_issues.csv", issues, ["file", "line", "kind", "detail"])

    grouped_scores: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        grouped_scores[row["model_id"]].append(row)
    summary_rows: list[dict[str, Any]] = []
    for model_id in MODELS:
        rows = grouped_scores[model_id]
        result: dict[str, Any] = {"model_id": model_id, "judge_ratings": len(rows)}
        for field in SCORE_FIELDS:
            result[f"mean_{field}"] = avg([float(row[field]) for row in rows])
        result["mean_serious_error_count"] = avg([float(row["serious_error_count"]) for row in rows])
        result["serious_error_flag_rate"] = avg([1.0 if row["serious_error_count"] else 0.0 for row in rows])
        dispositions = Counter(row["disposition"] for row in rows)
        for disposition in ["accept", "revise", "reject", "escalate"]:
            result[f"{disposition}_rate"] = dispositions[disposition] / len(rows) if rows else 0.0
        summary_rows.append(result)

    wins: dict[tuple[str, str], float] = defaultdict(float)
    comparisons: dict[tuple[str, str], float] = defaultdict(float)
    for _judge, _packet, _run, ranks in preference_records:
        for left, right in itertools.combinations(MODELS, 2):
            if left not in ranks or right not in ranks:
                continue
            key = tuple(sorted((left, right)))
            comparisons[key] += 1.0
            if ranks[left] < ranks[right]:
                wins[(left, right)] += 1.0
            elif ranks[right] < ranks[left]:
                wins[(right, left)] += 1.0
            else:
                wins[(left, right)] += 0.5
                wins[(right, left)] += 0.5
    strengths = bradley_terry_strength(wins, comparisons)
    for row in summary_rows:
        model_id = row["model_id"]
        total_points = 0.0
        total_comparisons = 0.0
        for other in MODELS:
            if other == model_id:
                continue
            key = tuple(sorted((model_id, other)))
            total_points += wins.get((model_id, other), 0.0)
            total_comparisons += comparisons.get(key, 0.0)
        row["pairwise_preference_rate"] = total_points / total_comparisons if total_comparisons else 0.0
        row["regularized_bradley_terry_strength"] = strengths[model_id]
    write_csv(run_dir / "judge_model_summary.csv", summary_rows, list(summary_rows[0]))

    objective = {row["model_id"]: row for row in read_csv(run_dir / "model_objective_summary.csv")}
    objective_long = read_csv(run_dir / "objective_metrics_long.csv")
    stability_rows = read_csv(run_dir / "stability_by_model_packet.csv")
    stability_by_model: dict[str, list[float]] = defaultdict(list)
    for row in stability_rows:
        stability_by_model[row["model_id"]].append(float(row["mean_cited_excerpt_jaccard"]))

    corpus_proxy = {
        "syn_dreaddit_01": "dreaddit",
        "syn_agyw_01": "agyw_focus_groups",
        "syn_kodis_01": "kodis",
        "syn_candor_01": "candor",
    }
    objective_by_model_packet: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in objective_long:
        objective_by_model_packet[(row["model_id"], row["packet_id"])].append(row)
    judge_by_model_packet: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        judge_by_model_packet[(row["model_id"], row["packet_id"])].append(row)
    stability_lookup = {
        (row["model_id"], row["packet_id"]): row for row in stability_rows
    }
    dataset_rows: list[dict[str, Any]] = []
    for model_id in MODELS:
        for packet_id in PACKETS:
            objective_rows = objective_by_model_packet[(model_id, packet_id)]
            judge_rows = judge_by_model_packet[(model_id, packet_id)]
            stability = stability_lookup[(model_id, packet_id)]
            dataset_rows.append(
                {
                    "model_id": model_id,
                    "packet_id": packet_id,
                    "corpus_proxy": corpus_proxy[packet_id],
                    "result_scope": "synthetic_proxy_not_corpus_result",
                    "generation_records": len(objective_rows),
                    "hard_gate_pass_rate": avg([float(row["hard_gate_pass"]) for row in objective_rows]),
                    "schema_valid_rate": avg([float(row["schema_valid"]) for row in objective_rows]),
                    "exact_quote_rate": avg([float(row["exact_quote_rate"]) for row in objective_rows]),
                    "attribution_validity": avg([float(row["attribution_validity"]) for row in objective_rows]),
                    "assignment_completeness": avg([float(row["assignment_completeness"]) for row in objective_rows]),
                    "cited_excerpt_coverage": avg([float(row["cited_excerpt_coverage"]) for row in objective_rows]),
                    "cited_source_coverage": avg([float(row["cited_source_coverage"]) for row in objective_rows]),
                    "theme_multi_source_rate": avg([float(row["theme_multi_source_rate"]) for row in objective_rows]),
                    "mean_theme_source_concentration": avg(
                        [float(row["mean_theme_source_concentration"]) for row in objective_rows]
                    ),
                    "judge_ratings": len(judge_rows),
                    "mean_judge_evidential_support": avg(
                        [float(row["evidential_support"]) for row in judge_rows]
                    ),
                    "mean_judge_voice_context": avg(
                        [float(row["voice_context_preservation"]) for row in judge_rows]
                    ),
                    "mean_judge_negative_case": avg(
                        [float(row["negative_case_preservation"]) for row in judge_rows]
                    ),
                    "mean_judge_codebook_usability": avg(
                        [float(row["codebook_usability"]) for row in judge_rows]
                    ),
                    "mean_judge_overall_quality": avg(
                        [float(row["overall_quality"]) for row in judge_rows]
                    ),
                    "judge_serious_error_flag_rate": avg(
                        [1.0 if row["serious_error_count"] else 0.0 for row in judge_rows]
                    ),
                    "judge_accept_rate": avg(
                        [1.0 if row["disposition"] == "accept" else 0.0 for row in judge_rows]
                    ),
                    "mean_cited_excerpt_jaccard": float(stability["mean_cited_excerpt_jaccard"]),
                    "mean_negative_case_jaccard": float(stability["mean_negative_case_jaccard"]),
                }
            )
    write_csv(run_dir / "model_dataset_summary.csv", dataset_rows, list(dataset_rows[0]))
    strict_pass = [
        model
        for model in MODELS
        if objective.get(model, {}).get("all_records_hard_gate_pass") == "1"
    ]
    judge_summary = {row["model_id"]: row for row in summary_rows}
    if strict_pass:
        candidate = max(
            strict_pass,
            key=lambda model: (
                float(judge_summary[model]["mean_overall_quality"]),
                float(judge_summary[model]["pairwise_preference_rate"]),
                avg(stability_by_model[model]),
            ),
        )
    else:
        # No candidate clears every run-level gate. Preserve the lexicographic
        # rule by prioritizing the automatic hard-gate pass rate before the
        # supplementary judge scores. This is a remediation candidate, not a
        # declaration that a failed gate has become acceptable.
        candidate = max(
            MODELS,
            key=lambda model: (
                float(objective[model]["mean_hard_gate_pass"]),
                float(objective[model]["mean_exact_quote_rate"]),
                float(objective[model]["mean_attribution_validity"]),
                float(judge_summary[model]["mean_overall_quality"]),
                float(judge_summary[model]["pairwise_preference_rate"]),
                avg(stability_by_model[model]),
            ),
        )
    selection = {
        "scope": "synthetic_engineering_qualification_only",
        "strict_gate_models": strict_pass,
        "provisional_candidate": candidate,
        "selection_status": (
            "provisional_candidate_passed_all_automatic_hard_gates"
            if candidate in strict_pass
            else "no_model_passed_all_automatic_hard_gates_highest_gate_rate_is_remediation_candidate"
        ),
        "basis": [
            "automatic integrity gates",
            "three-model same-vendor blinded judge panel",
            "three independent generations per model and packet",
        ],
        "not_available": [
            "independent qualified human judgments",
            "provider token usage, latency, and cost",
            "cross-provider judge independence",
            "authorized Dreaddit development tournament",
        ],
        "paper_model_selected": False,
        "next_required_step": "Obtain governance clearance, run blinded expert selection on eligible Dreaddit development packets, and freeze before Dreaddit test or AGYW inference.",
    }
    (run_dir / "selection.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "judge_records": len(record_keys),
        "expected_judge_records": len(expected_keys),
        "score_rows": len(score_rows),
        "issue_count": len(issues),
        "complete": record_keys == expected_keys and not issues,
        "provisional_candidate": candidate,
        "strict_gate_models": strict_pass,
    }
    (run_dir / "judge_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
