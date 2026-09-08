#!/usr/bin/env python3
"""Estimate sample-size efficiency curves for working flaw detection outputs.

The script rescores an existing full packet bank at multiple nested balanced
sample sizes and optional random draws. It does not call models; it only reuses
completed reviewer outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_RUN_ROOT = WORKSPACE / "Storage" / "draft_review_packets" / "dreaddit_dev100_working_v1"
ROLES = ("generalist", "qualitative_methods", "domain")
SHARED_FIXED_ROLE = "qualitative_methods"
TABLE_METHOD_LABELS = {
    "generalist": "Generalist",
}
TARGET_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row is not an object")
            rows.append(value)
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scoring_path(reviewer_outputs_root: Path, role: str) -> Path:
    return reviewer_outputs_root / role / "derived" / "scoring_inputs.jsonl"


def load_outputs(
    reviewer_outputs_root: Path, roles: list[str]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    outputs: dict[tuple[str, str, str], dict[str, Any]] = {}
    for role in roles:
        path = scoring_path(reviewer_outputs_root, role)
        if not path.exists():
            raise FileNotFoundError(f"missing scoring inputs for role {role}: {path}")
        for row in load_jsonl(path):
            outputs[(str(row["model_id"]), role, str(row["packet_id"]))] = row
    return outputs


def flags_for(row: dict[str, Any] | None) -> set[str]:
    if not row or row.get("status") != "valid":
        return set()
    rating = row.get("rating")
    if not isinstance(rating, dict):
        return set()
    flags = rating.get("serious_error_flags")
    if not isinstance(flags, list):
        return set()
    return {str(flag) for flag in flags}


def balanced_nested_subsets(truth_rows: list[dict[str, Any]], sizes: list[int]) -> list[tuple[str, list[dict[str, Any]]]]:
    by_flaw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(truth_rows, key=lambda item: item["packet_id"]):
        by_flaw[str(row["known_intended_flaw_type"])].append(row)
    flaw_count = len(by_flaw)
    subsets: list[tuple[str, list[dict[str, Any]]]] = []
    for n in sizes:
        if n % flaw_count:
            raise ValueError(f"balanced sample size must divide by {flaw_count}: {n}")
        per_flaw = n // flaw_count
        selected: list[dict[str, Any]] = []
        for flaw_type, rows in sorted(by_flaw.items()):
            if len(rows) < per_flaw:
                raise RuntimeError(f"not enough {flaw_type} rows for n={n}")
            selected.extend(rows[:per_flaw])
        selected.sort(key=lambda item: item["packet_id"])
        subsets.append((f"balanced_n{n}", selected))
    return subsets


def random_subsets(
    truth_rows: list[dict[str, Any]],
    sizes: list[int],
    draws: int,
    seed: int,
) -> list[tuple[str, list[dict[str, Any]]]]:
    rng = random.Random(seed)
    subsets: list[tuple[str, list[dict[str, Any]]]] = []
    for n in sizes:
        if n > len(truth_rows):
            raise ValueError(f"random sample size exceeds truth rows: {n}")
        for draw in range(1, draws + 1):
            selected = rng.sample(truth_rows, n)
            selected.sort(key=lambda item: item["packet_id"])
            subsets.append((f"random_n{n}_draw_{draw:02d}", selected))
    return subsets


def score_role(
    selected: list[dict[str, Any]],
    outputs: dict[tuple[str, str, str], dict[str, Any]],
    model_id: str,
    role: str,
) -> dict[str, Any]:
    tp = 0
    valid = 0
    missing = 0
    for truth in selected:
        packet_id = str(truth["packet_id"])
        row = outputs.get((model_id, role, packet_id))
        if row is None:
            missing += 1
            continue
        if row.get("status") == "valid":
            valid += 1
        target_flag = TARGET_TO_FLAG[str(truth["known_intended_flaw_type"])]
        tp += int(target_flag in flags_for(row))
    n = len(selected)
    return {
        "tp": tp,
        "n": n,
        "valid_output_n": valid,
        "missing_output_n": missing,
        "recall": tp / n if n else None,
    }


def score_all_roles(
    selected: list[dict[str, Any]],
    outputs: dict[tuple[str, str, str], dict[str, Any]],
    model_id: str,
    roles: list[str],
) -> dict[str, Any]:
    tp = 0
    valid = 0
    missing = 0
    for truth in selected:
        packet_id = str(truth["packet_id"])
        union_flags: set[str] = set()
        for role in roles:
            row = outputs.get((model_id, role, packet_id))
            if row is None:
                missing += 1
                continue
            if row.get("status") == "valid":
                valid += 1
            union_flags.update(flags_for(row))
        target_flag = TARGET_TO_FLAG[str(truth["known_intended_flaw_type"])]
        tp += int(target_flag in union_flags)
    n = len(selected)
    return {
        "tp": tp,
        "n": n,
        "valid_output_n": valid,
        "missing_output_n": missing,
        "recall": tp / n if n else None,
    }


def efficiency_rows(
    subsets: list[tuple[str, list[dict[str, Any]]]],
    outputs: dict[tuple[str, str, str], dict[str, Any]],
    roles: list[str],
    minimum_complete_fraction: float,
    require_all_roles_for_methods: bool,
    fixed_role_by_model: dict[str, str],
    table_methods_only: bool,
) -> list[dict[str, Any]]:
    model_ids = sorted({model for model, _role, _packet in outputs})
    rows: list[dict[str, Any]] = []
    for subset_name, selected in subsets:
        n = len(selected)
        corpus_id = str(selected[0].get("corpus_id", "unknown")) if selected else "unknown"
        flaw_counts = Counter(str(row["known_intended_flaw_type"]) for row in selected)
        for model_id in model_ids:
            role_scores = {role: score_role(selected, outputs, model_id, role) for role in roles}
            for role, score in role_scores.items():
                if table_methods_only and role != "generalist":
                    continue
                complete_fraction = score["valid_output_n"] / n if n else 0
                if complete_fraction < minimum_complete_fraction:
                    continue
                rows.append(
                    {
                        "corpus_id": corpus_id,
                        "subset": subset_name,
                        "sample_n": n,
                        "method": TABLE_METHOD_LABELS.get(role, role),
                        "model_id": model_id,
                        "tp": score["tp"],
                        "tp_over_n": f"{score['tp']}/{n}",
                        "recall": score["recall"],
                        "reviewer_calls": n,
                        "recall_per_100_calls": (score["recall"] / n * 100) if n and score["recall"] is not None else None,
                        "valid_output_n": score["valid_output_n"],
                        "missing_output_n": score["missing_output_n"],
                        **{f"count_{flaw}": flaw_counts.get(flaw, 0) for flaw in TARGET_TO_FLAG},
                    }
                )
            if len(roles) > 1:
                complete_roles = [
                    role
                    for role, score in role_scores.items()
                    if (score["valid_output_n"] / n if n else 0) >= minimum_complete_fraction
                ]
                if require_all_roles_for_methods and set(complete_roles) != set(roles):
                    continue
                fixed_role = fixed_role_by_model.get(model_id)
                if fixed_role in complete_roles:
                    fixed = role_scores[fixed_role]
                    rows.append(
                        {
                            "corpus_id": corpus_id,
                            "subset": subset_name,
                            "sample_n": n,
                            "method": "Fixed role",
                            "model_id": model_id,
                            "tp": fixed["tp"],
                            "tp_over_n": f"{fixed['tp']}/{n}",
                            "recall": fixed["recall"],
                            "reviewer_calls": n,
                            "recall_per_100_calls": (fixed["recall"] / n * 100) if n and fixed["recall"] is not None else None,
                            "valid_output_n": fixed["valid_output_n"],
                            "missing_output_n": fixed["missing_output_n"],
                            "selected_role": fixed_role,
                            **{f"count_{flaw}": flaw_counts.get(flaw, 0) for flaw in TARGET_TO_FLAG},
                        }
                    )
                if complete_roles:
                    all_roles = score_all_roles(selected, outputs, model_id, complete_roles)
                    all_calls = n * len(complete_roles)
                    rows.append(
                        {
                            "corpus_id": corpus_id,
                            "subset": subset_name,
                            "sample_n": n,
                            "method": "All roles",
                            "model_id": model_id,
                            "tp": all_roles["tp"],
                            "tp_over_n": f"{all_roles['tp']}/{n}",
                            "recall": all_roles["recall"],
                            "reviewer_calls": all_calls,
                            "recall_per_100_calls": (all_roles["recall"] / all_calls * 100) if all_calls and all_roles["recall"] is not None else None,
                            "valid_output_n": all_roles["valid_output_n"],
                            "missing_output_n": all_roles["missing_output_n"],
                            "roles_included": ";".join(complete_roles),
                            **{f"count_{flaw}": flaw_counts.get(flaw, 0) for flaw in TARGET_TO_FLAG},
                        }
                    )
    return rows


def marginal_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not str(row["subset"]).startswith("balanced_n"):
            continue
        grouped[(str(row["corpus_id"]), str(row["method"]), str(row["model_id"]))].append(row)
    out: list[dict[str, Any]] = []
    for (corpus_id, method, model_id), group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda item: int(item["sample_n"]))
        previous: dict[str, Any] | None = None
        for row in ordered:
            current_recall = float(row["recall"])
            current_calls = int(row["reviewer_calls"])
            if previous is None:
                out.append(
                    {
                        "corpus_id": corpus_id,
                        "method": method,
                        "model_id": model_id,
                        "from_n": 0,
                        "to_n": row["sample_n"],
                        "delta_calls": current_calls,
                        "recall_gain": current_recall,
                        "gain_per_100_added_calls": current_recall / current_calls * 100 if current_calls else None,
                    }
                )
            else:
                previous_recall = float(previous["recall"])
                previous_calls = int(previous["reviewer_calls"])
                delta_calls = current_calls - previous_calls
                recall_gain = current_recall - previous_recall
                out.append(
                    {
                        "corpus_id": corpus_id,
                        "method": method,
                        "model_id": model_id,
                        "from_n": previous["sample_n"],
                        "to_n": row["sample_n"],
                        "delta_calls": delta_calls,
                        "recall_gain": recall_gain,
                        "gain_per_100_added_calls": recall_gain / delta_calls * 100 if delta_calls else None,
                    }
                )
            previous = row
    return out


def random_stability_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        if not str(row["subset"]).startswith("random_n"):
            continue
        grouped[(str(row["corpus_id"]), str(row["method"]), str(row["model_id"]), int(row["sample_n"]))].append(float(row["recall"]))
    out: list[dict[str, Any]] = []
    for (corpus_id, method, model_id, sample_n), values in sorted(grouped.items()):
        out.append(
            {
                "corpus_id": corpus_id,
                "method": method,
                "model_id": model_id,
                "sample_n": sample_n,
                "draws": len(values),
                "min_recall": min(values),
                "mean_recall": statistics.mean(values),
                "max_recall": max(values),
                "stdev_recall": statistics.stdev(values) if len(values) > 1 else 0.0,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--truth-map", type=Path, default=None)
    parser.add_argument("--roles", nargs="+", choices=ROLES, default=["generalist"])
    parser.add_argument("--reviewer-outputs-root", type=Path, default=None)
    parser.add_argument("--balanced-sizes", nargs="+", type=int, default=[25, 50, 75, 100])
    parser.add_argument("--random-sizes", nargs="+", type=int, default=[25, 50, 75])
    parser.add_argument("--random-draws", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--minimum-complete-fraction", type=float, default=1.0)
    parser.add_argument(
        "--fixed-role",
        choices=ROLES,
        default=SHARED_FIXED_ROLE,
        help="One development-frozen role shared by every reviewer model.",
    )
    parser.add_argument(
        "--allow-partial-role-methods",
        action="store_true",
        help="Allow Fixed role and All roles rows when only some requested roles are complete.",
    )
    parser.add_argument(
        "--fixed-role-selection-size",
        type=int,
        default=None,
        help="Development sample size recorded for the frozen shared-role choice; no reselection is performed.",
    )
    parser.add_argument(
        "--table-methods-only",
        action="store_true",
        help="Export only Generalist, Fixed role, and All roles rows.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    truth_path = args.truth_map or args.run_root / "private" / "truth_map.private.jsonl"
    output_dir = args.output_dir or args.run_root / "sample_size_efficiency"
    reviewer_outputs_root = args.reviewer_outputs_root or args.run_root / "reviewer_outputs"
    truth_rows = load_jsonl(truth_path)
    outputs = load_outputs(reviewer_outputs_root, args.roles)
    if args.fixed_role not in args.roles:
        parser.error("--fixed-role must also be present in --roles")
    fixed_role_selection_size = args.fixed_role_selection_size or len(truth_rows)
    model_ids = sorted({model for model, _role, _packet in outputs})
    fixed_role_by_model = {model_id: args.fixed_role for model_id in model_ids}
    subsets = balanced_nested_subsets(truth_rows, args.balanced_sizes)
    subsets.extend(random_subsets(truth_rows, args.random_sizes, args.random_draws, args.seed))
    rows = efficiency_rows(
        subsets,
        outputs,
        args.roles,
        args.minimum_complete_fraction,
        not args.allow_partial_role_methods,
        fixed_role_by_model,
        args.table_methods_only,
    )
    marginal = marginal_rows(rows)
    stability = random_stability_rows(rows)

    write_csv(output_dir / "efficiency_curve.csv", rows)
    write_csv(output_dir / "marginal_gain.csv", marginal)
    write_csv(output_dir / "random_stability.csv", stability)
    write_json(
        output_dir / "manifest.json",
        {
            "balanced_sizes": args.balanced_sizes,
            "corpus_id": truth_rows[0].get("corpus_id") if truth_rows else None,
            "fixed_role_by_model": fixed_role_by_model,
            "fixed_role_selection_unit": "all_reviewer_models_pooled_on_development_data",
            "shared_fixed_role": args.fixed_role,
            "fixed_role_selection_size": fixed_role_selection_size,
            "input_run_root": str(args.run_root),
            "reviewer_outputs_root": str(reviewer_outputs_root),
            "minimum_complete_fraction": args.minimum_complete_fraction,
            "output_schema_version": "warrantroute-working-sample-size-efficiency-v2",
            "random_draws": args.random_draws,
            "random_sizes": args.random_sizes,
            "roles": args.roles,
            "seed": args.seed,
            "require_all_roles_for_methods": not args.allow_partial_role_methods,
            "status": "working_not_manuscript_eligible",
            "truth_map": str(truth_path),
        },
    )
    print(output_dir)
    print(json.dumps({"rows": len(rows), "marginal_rows": len(marginal), "stability_rows": len(stability)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
