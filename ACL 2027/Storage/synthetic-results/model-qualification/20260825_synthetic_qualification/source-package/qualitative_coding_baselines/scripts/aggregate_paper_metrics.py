#!/usr/bin/env python3
"""Validate paper-aligned blinded judgments and calculate all four measures."""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "experiments" / "qualitative_coding_baselines"
RUN = ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
SCHEMA_PATH = BASE / "schemas" / "paper_metric_judge.schema.json"
GUIDE_PATH = BASE / "benchmark" / "evaluation_guide_v1.json"
BLINDED_DIR = RUN / "blinded"
JUDGE_DIR = RUN / "paper_judges"
BLIND_MAP_PATH = RUN / "blind_map_private.csv"
OBJECTIVE_PATH = RUN / "objective_metrics_long.csv"

EXPECTED_JUDGES = {
    "paper_judge_gpt-5.5.jsonl": "gpt-5.5",
    "paper_judge_gpt-5.6-sol.jsonl": "gpt-5.6-sol",
    "paper_judge_gpt-5.6-terra.jsonl": "gpt-5.6-terra",
}
MODEL_ORDER = [
    "gpt-5.6-sol",
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
]
METRICS = [
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
]
BOOTSTRAP_REPLICATES = 20_000
BOOTSTRAP_SEED = 20_260_825


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def clustered_interval(
    clusters: dict[tuple[str, int], list[dict[str, object]]],
    numerator: Callable[[list[dict[str, object]]], float],
    denominator: Callable[[list[dict[str, object]]], float],
    seed_offset: int,
) -> tuple[float, float, float]:
    keys = sorted(clusters)
    observed_num = sum(numerator(clusters[key]) for key in keys)
    observed_den = sum(denominator(clusters[key]) for key in keys)
    observed = observed_num / observed_den
    rng = random.Random(BOOTSTRAP_SEED + seed_offset)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = [rng.choice(keys) for _ in keys]
        sample_num = sum(numerator(clusters[key]) for key in sampled)
        sample_den = sum(denominator(clusters[key]) for key in sampled)
        samples.append(sample_num / sample_den)
    return observed, quantile(samples, 0.025), quantile(samples, 0.975)


def load_inputs() -> tuple[
    dict[str, object],
    dict[str, list[str]],
    dict[tuple[str, int], dict[str, object]],
    dict[tuple[str, int, str], str],
    dict[tuple[str, int, str], dict[str, set[str]]],
]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    guide = json.loads(GUIDE_PATH.read_text(encoding="utf-8"))
    reference_ids = {
        packet["packet_id"]: [
            f"R{index:02d}"
            for index, _ in enumerate(packet["designed_constructs"], start=1)
        ]
        for packet in guide["packets"]
    }

    bundles: dict[tuple[str, int], dict[str, object]] = {}
    candidate_ids: dict[tuple[str, int, str], dict[str, set[str]]] = {}
    for path in sorted(BLINDED_DIR.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        key = (bundle["packet_id"], int(bundle["run_index"]))
        bundles[key] = bundle
        for candidate in bundle["candidates"]:
            blind_id = candidate["blind_id"]
            output = candidate["output"]
            candidate_ids[(key[0], key[1], blind_id)] = {
                "code": {item["code_id"] for item in output["codes"]},
                "theme": {item["theme_id"] for item in output["themes"]},
            }

    blind_map = {
        (row["packet_id"], int(row["run_index"]), row["blind_id"]): row[
            "model_id"
        ]
        for row in read_csv(BLIND_MAP_PATH)
    }
    return schema, reference_ids, bundles, blind_map, candidate_ids


def validate_and_flatten() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    schema, reference_ids, bundles, blind_map, candidate_ids = load_inputs()
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: list[dict[str, object]] = []
    ratings: list[dict[str, object]] = []
    matches: list[dict[str, object]] = []
    record_keys: set[tuple[str, str, int]] = set()

    def issue(file: str, line: int, kind: str, detail: str) -> None:
        issues.append(
            {"source_file": file, "line_number": line, "issue": kind, "detail": detail}
        )

    for filename, expected_judge in EXPECTED_JUDGES.items():
        path = JUDGE_DIR / filename
        if not path.exists():
            issue(filename, 0, "missing_file", "Expected judge output is absent")
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        if len(lines) != 12:
            issue(filename, 0, "record_count", f"Expected 12 records, found {len(lines)}")
        for line_number, line in enumerate(lines, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                issue(filename, line_number, "invalid_json", str(exc))
                continue
            schema_errors = sorted(validator.iter_errors(record), key=lambda err: list(err.path))
            for error in schema_errors:
                issue(
                    filename,
                    line_number,
                    "schema_error",
                    f"{'/'.join(map(str, error.path))}: {error.message}",
                )
            if schema_errors:
                continue
            if record["judge_model_id"] != expected_judge:
                issue(filename, line_number, "judge_id", "Judge ID does not match filename")
            packet_id = record["packet_id"]
            run_index = int(record["run_index"])
            bundle_key = (packet_id, run_index)
            if bundle_key not in bundles:
                issue(filename, line_number, "unknown_bundle", str(bundle_key))
                continue
            record_key = (expected_judge, packet_id, run_index)
            if record_key in record_keys:
                issue(filename, line_number, "duplicate_record", str(record_key))
            record_keys.add(record_key)

            scores = record["candidate_scores"]
            blind_ids = [score["blind_id"] for score in scores]
            if sorted(blind_ids) != ["B1", "B2", "B3", "B4", "B5"]:
                issue(filename, line_number, "blind_coverage", str(blind_ids))
            for score in scores:
                blind_id = score["blind_id"]
                candidate_key = (packet_id, run_index, blind_id)
                if candidate_key not in blind_map or candidate_key not in candidate_ids:
                    issue(filename, line_number, "unknown_candidate", str(candidate_key))
                    continue
                model_id = blind_map[candidate_key]
                cannot = set(score["cannot_judge"])
                for metric in METRICS:
                    is_null = score[metric] is None
                    if is_null != (metric in cannot):
                        issue(
                            filename,
                            line_number,
                            "cannot_judge_mismatch",
                            f"{blind_id}:{metric}",
                        )
                output_id = f"{packet_id}__run{run_index}__{model_id}"
                ratings.append(
                    {
                        "judge_model_id": expected_judge,
                        "packet_id": packet_id,
                        "run_index": run_index,
                        "blind_id": blind_id,
                        "model_id": model_id,
                        "output_id": output_id,
                        "evidential_credibility": score["evidential_credibility"],
                        "voice_boundary_preservation": score[
                            "voice_boundary_preservation"
                        ],
                        "scope_calibration": score["scope_calibration"],
                        "cannot_judge": "|".join(score["cannot_judge"]),
                        "confidence": int(score["confidence"]),
                        "serious_error_count": len(score["serious_error_flags"]),
                        "serious_error_flags": "|".join(score["serious_error_flags"]),
                        "rationale": score["rationale"],
                    }
                )
                expected_refs = reference_ids[packet_id]
                for level in ("code", "theme"):
                    field = f"{level}_reference_matches"
                    reference_matches = score[field]
                    found_refs = [match["reference_concept_id"] for match in reference_matches]
                    if sorted(found_refs) != sorted(expected_refs):
                        issue(
                            filename,
                            line_number,
                            "reference_coverage",
                            f"{blind_id}:{level}: expected {expected_refs}, found {found_refs}",
                        )
                    valid_ids = candidate_ids[candidate_key][level]
                    expected_prefix = "C" if level == "code" else "T"
                    for match in reference_matches:
                        generated_ids = match["generated_concept_ids"]
                        if any(not item.startswith(expected_prefix) for item in generated_ids):
                            issue(
                                filename,
                                line_number,
                                "wrong_concept_level",
                                f"{blind_id}:{level}:{generated_ids}",
                            )
                        unknown = sorted(set(generated_ids) - valid_ids)
                        if unknown:
                            issue(
                                filename,
                                line_number,
                                "unknown_generated_concept",
                                f"{blind_id}:{level}:{unknown}",
                            )
                        matches.append(
                            {
                                "judge_model_id": expected_judge,
                                "packet_id": packet_id,
                                "run_index": run_index,
                                "blind_id": blind_id,
                                "model_id": model_id,
                                "output_id": output_id,
                                "output_level": level,
                                "reference_concept_id": match["reference_concept_id"],
                                "match_status": match["match_status"],
                                "generated_concept_ids": "|".join(generated_ids),
                                "rationale": match["rationale"],
                            }
                        )

    expected_record_keys = {
        (judge, packet_id, run_index)
        for judge in EXPECTED_JUDGES.values()
        for packet_id, run_index in bundles
    }
    for missing in sorted(expected_record_keys - record_keys):
        issue("", 0, "missing_record", str(missing))
    if len(ratings) != 180:
        issue("", 0, "rating_count", f"Expected 180, found {len(ratings)}")
    expected_match_rows = 3 * 5 * 3 * 2 * sum(len(v) for v in reference_ids.values())
    if len(matches) != expected_match_rows:
        issue(
            "",
            0,
            "match_count",
            f"Expected {expected_match_rows}, found {len(matches)}",
        )
    return ratings, matches, issues


def panel_adjudicate(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, int, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in matches:
        grouped[
            (
                str(row["model_id"]),
                str(row["packet_id"]),
                int(row["run_index"]),
                str(row["output_level"]),
                str(row["reference_concept_id"]),
            )
        ].append(row)
    panel: list[dict[str, object]] = []
    for key, rows in sorted(grouped.items()):
        counts = defaultdict(int)
        for row in rows:
            counts[str(row["match_status"])] += 1
        if counts["recovered"] >= 2:
            status = "recovered"
        elif counts["unmatched"] >= 2:
            status = "unmatched"
        else:
            status = "cannot_judge"
        panel.append(
            {
                "model_id": key[0],
                "packet_id": key[1],
                "run_index": key[2],
                "output_id": f"{key[1]}__run{key[2]}__{key[0]}",
                "output_level": key[3],
                "reference_concept_id": key[4],
                "recovered_votes": counts["recovered"],
                "unmatched_votes": counts["unmatched"],
                "cannot_judge_votes": counts["cannot_judge"],
                "panel_status": status,
                "unanimous": int(max(counts.values()) == 3),
            }
        )
    return panel


def summarize(
    ratings: list[dict[str, object]],
    panel: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    objective = {
        (row["model_id"], row["packet_id"], int(row["run_index"])): row
        for row in read_csv(OBJECTIVE_PATH)
    }

    def make_summary(model_id: str, packet_id: str | None, seed_base: int) -> dict[str, object]:
        selected_ratings = [
            row
            for row in ratings
            if row["model_id"] == model_id
            and (packet_id is None or row["packet_id"] == packet_id)
        ]
        clusters: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
        for row in selected_ratings:
            clusters[(str(row["packet_id"]), int(row["run_index"]))].append(row)

        result: dict[str, object] = {
            "model_id": model_id,
            "packet_id": packet_id or "ALL",
            "synthetic_outputs": len(clusters),
            "judge_ratings": len(selected_ratings),
        }
        integrity_rows = [
            row
            for key, row in objective.items()
            if key[0] == model_id and (packet_id is None or key[1] == packet_id)
        ]
        result["integrity_gate_pass_n"] = sum(
            int(float(row["hard_gate_pass"])) for row in integrity_rows
        )
        result["integrity_gate_total"] = len(integrity_rows)
        result["integrity_gate_rate"] = result["integrity_gate_pass_n"] / len(
            integrity_rows
        )

        for metric_index, metric in enumerate(METRICS):
            evaluable = [row for row in selected_ratings if row[metric] is not None]
            result[f"{metric}_mean"] = sum(float(row[metric]) for row in evaluable) / len(
                evaluable
            )
            interval = clustered_interval(
                clusters,
                lambda rows, metric=metric: sum(
                    int(row[metric] is not None and int(row[metric]) >= 4) for row in rows
                ),
                lambda rows, metric=metric: sum(row[metric] is not None for row in rows),
                seed_base + metric_index,
            )
            result[f"{metric}_adequacy_rate"] = interval[0]
            result[f"{metric}_adequacy_ci_low"] = interval[1]
            result[f"{metric}_adequacy_ci_high"] = interval[2]
            result[f"{metric}_cannot_judge_rate"] = 1 - len(evaluable) / len(
                selected_ratings
            )
            leave_self = [
                row
                for row in evaluable
                if row["judge_model_id"] != row["model_id"]
            ]
            result[f"{metric}_adequacy_leave_self_judge_out"] = (
                sum(int(int(row[metric]) >= 4) for row in leave_self) / len(leave_self)
                if leave_self
                else "not_applicable"
            )

        serious = clustered_interval(
            clusters,
            lambda rows: sum(int(int(row["serious_error_count"]) > 0) for row in rows),
            lambda rows: len(rows),
            seed_base + 10,
        )
        result["serious_error_rate"] = serious[0]
        result["serious_error_ci_low"] = serious[1]
        result["serious_error_ci_high"] = serious[2]

        selected_panel = [
            row
            for row in panel
            if row["model_id"] == model_id
            and (packet_id is None or row["packet_id"] == packet_id)
        ]
        for level_index, level in enumerate(("code", "theme")):
            level_clusters: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
            for row in selected_panel:
                if row["output_level"] == level:
                    level_clusters[(str(row["packet_id"]), int(row["run_index"]))].append(row)
            interval = clustered_interval(
                level_clusters,
                lambda rows: sum(row["panel_status"] == "recovered" for row in rows),
                lambda rows: sum(row["panel_status"] != "cannot_judge" for row in rows),
                seed_base + 20 + level_index,
            )
            result[f"{level}_plural_reference_coverage"] = interval[0]
            result[f"{level}_plural_reference_coverage_ci_low"] = interval[1]
            result[f"{level}_plural_reference_coverage_ci_high"] = interval[2]
            result[f"{level}_reference_opportunities"] = sum(
                row["panel_status"] != "cannot_judge" for rows in level_clusters.values() for row in rows
            )
            result[f"{level}_match_unanimity_rate"] = sum(
                int(row["unanimous"]) for rows in level_clusters.values() for row in rows
            ) / sum(len(rows) for rows in level_clusters.values())
        result["evidence_source"] = (
            "three_blinded_same_vendor_model_judges_on_entirely_fictional_packets"
        )
        result["manuscript_status"] = "synthetic_measurement_pilot_not_confirmatory"
        return result

    overall = [
        make_summary(model_id, None, 100 * model_index)
        for model_index, model_id in enumerate(MODEL_ORDER, start=1)
    ]
    packet_order = ["syn_dreaddit_01", "syn_agyw_01", "syn_kodis_01", "syn_candor_01"]
    by_packet = [
        make_summary(model_id, packet_id, 10_000 + 100 * model_index + packet_index * 10)
        for model_index, model_id in enumerate(MODEL_ORDER, start=1)
        for packet_index, packet_id in enumerate(packet_order, start=1)
    ]
    return overall, by_packet


def percent(value: object) -> str:
    return f"{100 * float(value):.1f}"


def latex_interval(row: dict[str, object], stem: str) -> str:
    ci_stem = stem
    if stem + "_ci_low" not in row and stem.endswith("_rate"):
        ci_stem = stem[: -len("_rate")]
    return (
        f"{percent(row[stem])} "
        f"[{percent(row[ci_stem + '_ci_low'])}, {percent(row[ci_stem + '_ci_high'])}]"
    )


def write_latex_table(rows: list[dict[str, object]]) -> None:
    path = ROOT / "overleaf" / "tables" / "synthetic_paper_metrics.tex"
    lines = [
        "% Generated by aggregate_paper_metrics.py from validated blinded records.",
        "\\begin{table*}[t]",
        "\\centering",
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{2.3pt}",
        "\\begin{tabular}{lrrrrrrr}",
        "\\toprule",
        "Model & \\shortstack{Integrity\\\\pass} & \\shortstack{Evidential\\\\adequacy} & \\shortstack{Voice/boundary\\\\adequacy} & \\shortstack{Scope\\\\adequacy} & \\shortstack{Code\\\\coverage} & \\shortstack{Theme\\\\coverage} & \\shortstack{Serious\\\\error} \\\\",
        "\\midrule",
    ]
    for row in rows:
        label = str(row["model_id"]).replace("gpt-", "GPT-")
        label = label.replace("-sol", " Sol").replace("-luna", " Luna").replace(
            "-terra", " Terra"
        )
        integrity = f"{row['integrity_gate_pass_n']}/{row['integrity_gate_total']}"
        lines.append(
            " & ".join(
                [
                    label,
                    integrity,
                    latex_interval(row, "evidential_credibility_adequacy_rate"),
                    latex_interval(row, "voice_boundary_preservation_adequacy_rate"),
                    latex_interval(row, "scope_calibration_adequacy_rate"),
                    latex_interval(row, "code_plural_reference_coverage"),
                    latex_interval(row, "theme_plural_reference_coverage"),
                    latex_interval(row, "serious_error_rate"),
                ]
            )
            + " \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\caption{Paper-aligned measurement pilot on entirely fictional packets. Ordinal columns report the percentage of 36 blinded model-judge ratings per model scored 4 or 5. Code and theme coverage report panel-majority recovery across 63 frozen reference opportunities per level and model. Brackets are 95\\% packet-by-run cluster-bootstrap intervals. Integrity is deterministic. All three judges and candidates are from one provider; these are measurement-pipeline results, not real-corpus or human-evaluation results.}",
            "\\label{tab:synthetic_paper_metrics}",
            "\\end{table*}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ratings, matches, issues = validate_and_flatten()
    issue_path = RUN / "paper_metric_validation_issues.csv"
    if issues:
        write_csv(issue_path, issues)
        summary = {
            "complete": False,
            "issue_count": len(issues),
            "ratings": len(ratings),
            "matches": len(matches),
        }
        (RUN / "paper_metric_validation_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, sort_keys=True))
        raise SystemExit(1)
    issue_path.write_text("source_file,line_number,issue,detail\n", encoding="utf-8")
    panel = panel_adjudicate(matches)
    overall, by_packet = summarize(ratings, panel)
    write_csv(RUN / "paper_metric_ratings_long.csv", ratings)
    write_csv(RUN / "paper_metric_matches_long.csv", matches)
    write_csv(RUN / "paper_metric_panel_matches.csv", panel)
    write_csv(RUN / "paper_metric_model_summary.csv", overall)
    write_csv(RUN / "paper_metric_model_dataset_summary.csv", by_packet)
    write_latex_table(overall)
    summary = {
        "complete": True,
        "judge_records": 36,
        "candidate_ratings": len(ratings),
        "concept_match_rows": len(matches),
        "panel_match_rows": len(panel),
        "models": len(overall),
        "model_dataset_rows": len(by_packet),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "issue_count": 0,
    }
    (RUN / "paper_metric_validation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
