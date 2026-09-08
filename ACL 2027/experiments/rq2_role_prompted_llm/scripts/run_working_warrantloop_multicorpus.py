#!/usr/bin/env python3
"""Run the retrospective four-corpus WarrantLoop working replay."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import run_working_warrantloop as core


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_EXPERIMENT_CONFIG = (
    RQ2_ROOT / "config" / "working_warrantloop_multicorpus_v0.json"
)
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "warrantloop_working"
)
MODEL_DISPLAY = {
    "qwen3:8b": "Qwen3 8B",
    "llama3.1:8b": "Llama 3.1 8B",
    "gemma3:4b": "Gemma 3 4B",
}
MODEL_DISPLAY_ORDER = ("Qwen3 8B", "Llama 3.1 8B", "Gemma 3 4B")


def resolve_workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE / path


def stable_digest(*values: str) -> str:
    return hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()


def assign_outer_folds(
    packet_ids: list[str], fold_count: int, seed: str
) -> dict[int, list[str]]:
    if fold_count < 2 or len(packet_ids) < fold_count:
        raise ValueError("invalid_outer_fold_count")
    ordered = sorted(packet_ids, key=lambda packet_id: stable_digest(seed, packet_id))
    folds = {index: [] for index in range(fold_count)}
    for index, packet_id in enumerate(ordered):
        folds[index % fold_count].append(packet_id)
    for packet_ids_for_fold in folds.values():
        packet_ids_for_fold.sort()
    flattened = [packet_id for ids in folds.values() for packet_id in ids]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(packet_ids):
        raise ValueError("outer_fold_overlap_or_omission")
    return folds


def inner_split(
    packet_ids: list[str], validation_fraction: float, seed: str
) -> tuple[list[str], list[str]]:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("invalid_inner_validation_fraction")
    ordered = sorted(packet_ids, key=lambda packet_id: stable_digest(seed, packet_id))
    validation_n = max(1, int(round(len(ordered) * validation_fraction)))
    train_n = len(ordered) - validation_n
    if train_n <= 0:
        raise ValueError("empty_inner_train")
    return sorted(ordered[:train_n]), sorted(ordered[train_n:])


def source_set(inputs: dict[str, Any], packet_ids: list[str]) -> set[str]:
    return set().union(*(inputs["source_groups"][packet_id] for packet_id in packet_ids))


def validate_fold_source_separation(
    inputs: dict[str, Any], folds: dict[int, list[str]]
) -> None:
    source_sets = {index: source_set(inputs, ids) for index, ids in folds.items()}
    for left in range(len(folds)):
        for right in range(left + 1, len(folds)):
            if source_sets[left] & source_sets[right]:
                raise ValueError(f"outer_fold_source_overlap:{left}:{right}")


def minimum_flaw_count(
    packet_ids: list[str], truth: dict[str, str], minimum: int
) -> None:
    counts = Counter(truth[packet_id] for packet_id in packet_ids)
    if any(counts[flaw] < minimum for flaw in core.TARGET_TO_FLAG):
        raise ValueError(f"minimum_training_flaw_count_not_met:{dict(counts)}")


def load_all_inputs(
    experiment: dict[str, Any], policy_config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    base = WORKSPACE / "Storage" / "draft_review_packets"
    loaded: dict[str, dict[str, Any]] = {}
    expected_models = sorted(str(value) for value in experiment["expected_models"])
    for dataset in experiment["datasets"]:
        label = str(dataset["display_label"])
        run_root = base / str(dataset["run_root_name"])
        require_development = dataset["corpus_id"] == policy_config["development"][
            "allowed_corpus_id"
        ]
        inputs = core.load_working_inputs(
            run_root,
            str(experiment["packet_set"]),
            policy_config,
            require_development_lane=require_development,
        )
        if inputs["corpus_id"] != dataset["corpus_id"]:
            raise ValueError(f"corpus_binding_mismatch:{label}:{inputs['corpus_id']}")
        if len(inputs["packet_ids"]) != int(experiment["expected_packets_per_dataset"]):
            raise ValueError(f"packet_count_mismatch:{label}:{len(inputs['packet_ids'])}")
        if inputs["models"] != expected_models:
            raise ValueError(f"model_inventory_mismatch:{label}:{inputs['models']}")
        if any(inputs["invalid_by_role"].values()):
            raise ValueError(f"nonvalid_role_projection:{label}:{inputs['invalid_by_role']}")
        inputs["dataset_spec"] = dataset
        loaded[label] = inputs
    if list(loaded) != [str(row["display_label"]) for row in experiment["datasets"]]:
        raise ValueError("dataset_order_drift")
    return loaded


def preflight_report(
    experiment: dict[str, Any], inputs_by_dataset: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "status": "ready_for_retrospective_working_replay",
        "experiment_id": experiment["experiment_id"],
        "datasets": {
            label: {
                "corpus_id": inputs["corpus_id"],
                "packet_count": len(inputs["packet_ids"]),
                "role_projection_count": len(inputs["role_rows"]),
                "invalid_by_role": inputs["invalid_by_role"],
                "evaluation_mode": inputs["dataset_spec"]["evaluation_mode"],
            }
            for label, inputs in inputs_by_dataset.items()
        },
        "expected_route_count": sum(
            len(inputs["packet_ids"]) * len(inputs["models"])
            for inputs in inputs_by_dataset.values()
        ),
        "new_llm_calls_required": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }


def add_route_metadata(
    routes: list[dict[str, Any]],
    *,
    dataset_label: str,
    corpus_id: str,
    evaluation_mode: str,
    outer_fold: int | None,
    policy_kind: str,
) -> None:
    for row in routes:
        row.update(
            {
                "dataset": dataset_label,
                "corpus_id": corpus_id,
                "evaluation_mode": evaluation_mode,
                "outer_fold": outer_fold,
                "policy_kind": policy_kind,
            }
        )


def fit_cross_fitted_routes(
    development_inputs: dict[str, Any],
    development_truth: dict[str, str],
    experiment: dict[str, Any],
    policy_config: dict[str, Any],
    gate_policy: dict[str, Any],
    policy_config_path: Path,
    gate_policy_path: Path,
    output_dir: Path,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    fold_count = int(experiment["outer_folds"])
    folds = assign_outer_folds(
        development_inputs["packet_ids"],
        fold_count,
        str(experiment["outer_fold_seed"]),
    )
    validate_fold_source_separation(development_inputs, folds)
    minimum = int(policy_config["development"]["minimum_train_packets_per_flaw"])
    policies: dict[int, dict[str, Any]] = {}
    all_routes: list[dict[str, Any]] = []
    for fold_index in range(fold_count):
        outer_test = folds[fold_index]
        outer_train = sorted(
            packet_id
            for index, ids in folds.items()
            if index != fold_index
            for packet_id in ids
        )
        train_ids, validation_ids = inner_split(
            outer_train,
            float(experiment["inner_validation_fraction"]),
            f"{experiment['inner_split_seed']}:{fold_index}",
        )
        minimum_flaw_count(train_ids, development_truth, minimum)
        fitting_ids = set(train_ids + validation_ids)
        fitting_truth = {
            packet_id: development_truth[packet_id] for packet_id in fitting_ids
        }
        split = {
            "train": train_ids,
            "validation": validation_ids,
            "smoke_test": outer_test,
        }
        policy = core.fit_policy_artifact(
            development_inputs,
            fitting_truth,
            split,
            policy_config,
            gate_policy,
            policy_config_path,
            gate_policy_path,
        )
        policy.update(
            {
                "policy_kind": "development_outer_fold",
                "outer_fold": fold_index,
                "outer_fold_count": fold_count,
                "orchestrator_sha256": core.sha256_file(SCRIPT),
            }
        )
        policy_path = output_dir / "policies" / f"dreaddit_outer_fold_{fold_index}.json"
        core.write_json(policy_path, policy)
        policy_hash = core.sha256_file(policy_path)
        routes = core.apply_policy(
            development_inputs["packet_projections"],
            development_inputs["role_projections"],
            development_inputs["models"],
            outer_test,
            policy,
            policy_hash,
            policy_config,
            gate_policy,
        )
        add_route_metadata(
            routes,
            dataset_label="Dreaddit",
            corpus_id=development_inputs["corpus_id"],
            evaluation_mode="five_fold_out_of_fold_development",
            outer_fold=fold_index,
            policy_kind="development_outer_fold",
        )
        all_routes.extend(routes)
        policies[fold_index] = {
            "path": str(policy_path),
            "sha256": policy_hash,
            "train_n": len(train_ids),
            "validation_n": len(validation_ids),
            "test_n": len(outer_test),
            "train_ids": train_ids,
            "validation_ids": validation_ids,
            "test_ids": outer_test,
        }
    expected = len(development_inputs["packet_ids"]) * len(development_inputs["models"])
    if len(all_routes) != expected:
        raise ValueError(f"development_oof_route_count_mismatch:{len(all_routes)}:{expected}")
    identities = {(row["model_id"], row["packet_id"]) for row in all_routes}
    if len(identities) != expected:
        raise ValueError("development_oof_route_duplicate")
    return all_routes, policies


def fit_transfer_policy(
    development_inputs: dict[str, Any],
    development_truth: dict[str, str],
    experiment: dict[str, Any],
    policy_config: dict[str, Any],
    gate_policy: dict[str, Any],
    policy_config_path: Path,
    gate_policy_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], Path, str]:
    train_ids, validation_ids = inner_split(
        development_inputs["packet_ids"],
        float(experiment["inner_validation_fraction"]),
        f"{experiment['inner_split_seed']}:transfer",
    )
    minimum_flaw_count(
        train_ids,
        development_truth,
        int(policy_config["development"]["minimum_train_packets_per_flaw"]),
    )
    split = {"train": train_ids, "validation": validation_ids, "smoke_test": []}
    policy = core.fit_policy_artifact(
        development_inputs,
        development_truth,
        split,
        policy_config,
        gate_policy,
        policy_config_path,
        gate_policy_path,
    )
    policy.update(
        {
            "policy_kind": "dreaddit_full_development_transfer",
            "transfer_training_corpus": "dreaddit",
            "transfer_training_n": len(development_inputs["packet_ids"]),
            "orchestrator_sha256": core.sha256_file(SCRIPT),
        }
    )
    path = output_dir / "policies" / "dreaddit_transfer_policy.json"
    core.write_json(path, policy)
    return policy, path, core.sha256_file(path)


def apply_transfer_policy(
    inputs_by_dataset: dict[str, dict[str, Any]],
    transfer_policy: dict[str, Any],
    transfer_policy_hash: str,
    policy_config: dict[str, Any],
    gate_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, inputs in inputs_by_dataset.items():
        if label == "Dreaddit":
            continue
        routes = core.apply_policy(
            inputs["packet_projections"],
            inputs["role_projections"],
            inputs["models"],
            inputs["packet_ids"],
            transfer_policy,
            transfer_policy_hash,
            policy_config,
            gate_policy,
        )
        add_route_metadata(
            routes,
            dataset_label=label,
            corpus_id=inputs["corpus_id"],
            evaluation_mode=str(inputs["dataset_spec"]["evaluation_mode"]),
            outer_fold=None,
            policy_kind="dreaddit_full_development_transfer",
        )
        rows.extend(routes)
    return rows


def score_all_routes(
    route_rows: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    detail_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    truth_hashes: dict[str, str] = {}
    for label, inputs in inputs_by_dataset.items():
        selected_routes = [row for row in route_rows if row["dataset"] == label]
        truth = core.load_truth_subset(inputs["truth_path"], set(inputs["packet_ids"]))
        truth_hashes[label] = core.sha256_file(inputs["truth_path"])
        detail, aggregates = core.score_routes(selected_routes, inputs, truth)
        for row in detail:
            row.update(
                {
                    "dataset": label,
                    "corpus_id": inputs["corpus_id"],
                    "evaluation_mode": inputs["dataset_spec"]["evaluation_mode"],
                }
            )
        for row in aggregates:
            row.update(
                {
                    "dataset": label,
                    "corpus_id": inputs["corpus_id"],
                    "evaluation_mode": inputs["dataset_spec"]["evaluation_mode"],
                }
            )
        detail_rows.extend(detail)
        metric_rows.extend(aggregates)
    return detail_rows, metric_rows, truth_hashes


def format_recall(row: dict[str, Any]) -> str:
    recall = 100.0 * float(row["recall"])
    lower = 100.0 * float(row["recall_wilson_95_low"])
    upper = 100.0 * float(row["recall_wilson_95_high"])
    return f"{recall:.1f} [{lower:.1f}, {upper:.1f}]"


def build_comparison_rows(
    original_rows: list[dict[str, str]],
    metric_rows: list[dict[str, Any]],
    dataset_order: list[str],
    method_name: str = "WarrantRoute-S",
) -> list[dict[str, str]]:
    by_key = {
        (str(row["dataset"]), MODEL_DISPLAY[str(row["model_id"])]): row
        for row in metric_rows
    }
    combined: list[dict[str, str]] = []
    for dataset in dataset_order:
        combined.extend(row for row in original_rows if row["Dataset"] == dataset)
        for model_display in MODEL_DISPLAY_ORDER:
            metric = by_key[(dataset, model_display)]
            combined.append(
                {
                    "Dataset": dataset,
                    "Method": method_name,
                    "Model": model_display,
                    "TP/N": f"{metric['tp']}/{metric['n']}",
                    "Recall (%) ↑": format_recall(metric),
                }
            )
    return combined


def write_markdown_table(
    path: Path, rows: list[dict[str, str]], method_name: str = "WarrantRoute-S"
) -> None:
    fields = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    lines = [
        f"# Working Table 3 plus {method_name}",
        "",
        "Retrospective personal-local diagnostic only. Not manuscript eligible.",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[field]) for field in fields) + " |")
    core.secure_write_text(path, "\n".join(lines) + "\n")


def parse_tp_n(value: str) -> tuple[int, int]:
    parts = value.split("/", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"invalid_tp_n:{value}")
    return int(parts[0]), int(parts[1])


def baseline_row(
    rows: list[dict[str, str]], dataset: str, method: str, model: str
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row["Dataset"] == dataset
        and row["Method"] == method
        and row["Model"] == model
    ]
    if len(matches) != 1:
        raise ValueError(f"baseline_row_inventory:{dataset}:{method}:{model}:{len(matches)}")
    return matches[0]


def candidate_not_below_generalist(
    comparison_rows: list[dict[str, str]], metric_rows: list[dict[str, Any]]
) -> bool:
    for metric in metric_rows:
        dataset = str(metric["dataset"])
        model = MODEL_DISPLAY[str(metric["model_id"])]
        generalist_tp, generalist_n = parse_tp_n(
            baseline_row(comparison_rows, dataset, "Generalist", model)["TP/N"]
        )
        if int(metric["n"]) != generalist_n or int(metric["tp"]) < generalist_tp:
            return False
    return True


def selected_thresholds_respect_budget(
    policies: list[dict[str, Any]], policy_config: dict[str, Any]
) -> bool:
    selection = policy_config["threshold_selection"]
    if selection["objective"] != (
        "maximum_validation_recall_subject_to_mean_total_role_acquisitions_budget"
    ):
        return True
    budget = float(selection["maximum_mean_total_role_acquisitions"])
    tolerance = float(selection.get("budget_tolerance", 1e-12))
    for policy in policies:
        for model_policy in policy["model_policies"].values():
            threshold = float(model_policy["selected_threshold"])
            matches = [
                row
                for row in model_policy["threshold_candidates"]
                if float(row["threshold"]) == threshold
            ]
            if len(matches) != 1:
                return False
            if float(matches[0]["mean_total_role_acquisitions"]) > budget + tolerance:
                return False
    return True


def independently_score_routes(
    route_rows: list[dict[str, Any]],
    detail_rows: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
) -> bool:
    scored = {
        (str(row["dataset"]), str(row["model_id"]), str(row["packet_id"])): bool(
            row["detected"]
        )
        for row in detail_rows
    }
    truth_by_dataset = {
        dataset: core.load_truth_subset(
            inputs["truth_path"], set(inputs["packet_ids"])
        )
        for dataset, inputs in inputs_by_dataset.items()
    }
    for route in route_rows:
        dataset = str(route["dataset"])
        model_id = str(route["model_id"])
        packet_id = str(route["packet_id"])
        inputs = inputs_by_dataset[dataset]
        target_flag = core.TARGET_TO_FLAG[truth_by_dataset[dataset][packet_id]]
        flags: set[str] = set()
        for role in route["selected_roles"]:
            row = inputs["role_rows"][(model_id, str(role), packet_id)]
            rating = row.get("rating") if row.get("status") == "valid" else None
            values = rating.get("serious_error_flags") if isinstance(rating, dict) else None
            if isinstance(values, list):
                flags.update(str(value) for value in values)
        key = (dataset, model_id, packet_id)
        if scored.get(key) != (target_flag in flags):
            return False
    return len(scored) == len(route_rows)


def build_quality_cost_rows(
    comparison_rows: list[dict[str, str]],
    metric_rows: list[dict[str, Any]],
    prior_metric_rows: list[dict[str, str]],
    dataset_order: list[str],
    candidate_name: str,
) -> list[dict[str, Any]]:
    current = {
        (str(row["dataset"]), MODEL_DISPLAY[str(row["model_id"])]): row
        for row in metric_rows
    }
    prior = {
        (str(row["dataset"]), MODEL_DISPLAY[str(row["model_id"])]): row
        for row in prior_metric_rows
    }
    rows: list[dict[str, Any]] = []
    for dataset in dataset_order:
        for model in MODEL_DISPLAY_ORDER:
            all_tp, n = parse_tp_n(
                baseline_row(comparison_rows, dataset, "All roles", model)["TP/N"]
            )
            for method, calls in (("Generalist", 1.0), ("Fixed role", 1.0), ("All roles", 3.0)):
                tp, method_n = parse_tp_n(
                    baseline_row(comparison_rows, dataset, method, model)["TP/N"]
                )
                if method_n != n:
                    raise ValueError("quality_cost_denominator_mismatch")
                rows.append(
                    {
                        "dataset": dataset,
                        "model": model,
                        "method": method,
                        "tp": tp,
                        "n": n,
                        "recall": tp / n,
                        "mean_total_role_calls": calls,
                        "all_roles_tp_recovered": tp / all_tp if all_tp else None,
                    }
                )
            for method, metric in (
                ("WarrantRoute-S", prior[(dataset, model)]),
                (candidate_name, current[(dataset, model)]),
            ):
                tp = int(metric["tp"])
                method_n = int(metric["n"])
                if method_n != n:
                    raise ValueError("quality_cost_candidate_denominator_mismatch")
                rows.append(
                    {
                        "dataset": dataset,
                        "model": model,
                        "method": method,
                        "tp": tp,
                        "n": n,
                        "recall": tp / n,
                        "mean_total_role_calls": float(
                            metric["mean_total_role_acquisitions"]
                        ),
                        "all_roles_tp_recovered": tp / all_tp if all_tp else None,
                    }
                )
    return rows


def run_preflight(args: argparse.Namespace) -> int:
    experiment = core.load_json(args.experiment_config)
    policy_config_path = resolve_workspace_path(str(experiment["policy_config"]))
    policy_config = core.load_json(policy_config_path)
    core.validate_policy_config(policy_config)
    inputs_by_dataset = load_all_inputs(experiment, policy_config)
    print(json.dumps(preflight_report(experiment, inputs_by_dataset), indent=2, sort_keys=True))
    return 0


def run_working(args: argparse.Namespace) -> int:
    experiment = core.load_json(args.experiment_config)
    if (
        experiment.get("new_llm_calls_allowed") is not False
        or experiment.get("formal_run_enabled") is not False
        or experiment.get("manuscript_eligible") is not False
    ):
        raise ValueError("working_experiment_must_fail_closed")
    policy_config_path = resolve_workspace_path(str(experiment["policy_config"]))
    policy_config = core.load_json(policy_config_path)
    core.validate_policy_config(policy_config)
    gate_policy_path = core.DEFAULT_GATE_POLICY
    gate_policy = core.load_json(gate_policy_path)
    inputs_by_dataset = load_all_inputs(experiment, policy_config)
    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_ROOT
        / f"multicorpus_n100_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    if not output_dir.resolve().is_relative_to(DEFAULT_OUTPUT_ROOT.resolve()):
        raise ValueError(f"output_outside_personal_local_root:{output_dir}")
    core.require_new_output_dir(output_dir)

    development = inputs_by_dataset["Dreaddit"]
    development_truth = core.load_truth_subset(
        development["truth_path"], set(development["packet_ids"])
    )
    oof_routes, fold_policies = fit_cross_fitted_routes(
        development,
        development_truth,
        experiment,
        policy_config,
        gate_policy,
        policy_config_path,
        gate_policy_path,
        output_dir,
    )
    transfer_policy, transfer_policy_path, transfer_policy_hash = fit_transfer_policy(
        development,
        development_truth,
        experiment,
        policy_config,
        gate_policy,
        policy_config_path,
        gate_policy_path,
        output_dir,
    )
    transfer_routes = apply_transfer_policy(
        inputs_by_dataset,
        transfer_policy,
        transfer_policy_hash,
        policy_config,
        gate_policy,
    )
    route_rows = oof_routes + transfer_routes
    route_path = output_dir / "routes.jsonl"
    core.write_jsonl(route_path, route_rows)

    # Every route is complete before any evaluation-corpus truth map is loaded.
    detail_rows, metric_rows, truth_hashes = score_all_routes(
        route_rows, inputs_by_dataset
    )
    detail_path = output_dir / "scores.private.csv"
    metrics_path = output_dir / "warrantloop_metrics.csv"
    core.write_csv(detail_path, detail_rows)
    core.write_csv(metrics_path, metric_rows)

    comparison_path = resolve_workspace_path(str(experiment["comparison_source"]))
    with comparison_path.open("r", encoding="utf-8", newline="") as handle:
        original_rows = list(csv.DictReader(handle))
    dataset_order = [str(row["display_label"]) for row in experiment["datasets"]]
    method_name = str(policy_config["paper_facing_name"])
    combined_rows = build_comparison_rows(
        original_rows, metric_rows, dataset_order, method_name
    )
    output_stem = str(
        experiment.get(
            "comparison_output_stem", "table3_plus_warrantroute_s_working"
        )
    )
    if Path(output_stem).name != output_stem:
        raise ValueError("invalid_comparison_output_stem")
    combined_path = output_dir / f"{output_stem}.csv"
    markdown_path = output_dir / f"{output_stem}.md"
    core.write_csv(combined_path, combined_rows)
    write_markdown_table(markdown_path, combined_rows, method_name)

    quality_cost_rows: list[dict[str, Any]] = []
    quality_cost_path: Path | None = None
    prior_metrics_value = experiment.get("prior_candidate_metrics")
    if prior_metrics_value:
        prior_metrics_path = resolve_workspace_path(str(prior_metrics_value))
        with prior_metrics_path.open("r", encoding="utf-8", newline="") as handle:
            prior_metric_rows = list(csv.DictReader(handle))
        quality_cost_rows = build_quality_cost_rows(
            original_rows,
            metric_rows,
            prior_metric_rows,
            dataset_order,
            method_name,
        )
        quality_cost_path = output_dir / "quality_cost_comparison.csv"
        core.write_csv(quality_cost_path, quality_cost_rows)

    expected_route_count = (
        len(experiment["datasets"])
        * int(experiment["expected_packets_per_dataset"])
        * len(experiment["expected_models"])
    )
    route_identities = {
        (row["dataset"], row["model_id"], row["packet_id"]) for row in route_rows
    }
    metric_keys = {(row["dataset"], row["model_id"]) for row in metric_rows}
    expected_comparison_rows = int(experiment.get("comparison_source_expected_rows", 48))
    expected_combined_rows = int(
        experiment.get(
            "expected_combined_rows",
            expected_comparison_rows + len(experiment["datasets"]) * len(experiment["expected_models"]),
        )
    )
    cumulative = core.retain_generalist_output(policy_config)
    fitted_policies = [
        core.load_json(Path(item["path"])) for item in fold_policies.values()
    ] + [transfer_policy]
    checks = {
        "all_input_role_outputs_valid": all(
            not any(inputs["invalid_by_role"].values())
            for inputs in inputs_by_dataset.values()
        ),
        "route_count_matches": len(route_rows) == expected_route_count,
        "route_identity_unique": len(route_identities) == expected_route_count,
        "all_routes_terminate": all(bool(row["stop_reason"]) for row in route_rows),
        "specialist_budget_respected": all(
            int(row["specialist_acquisitions"])
            <= int(policy_config["maximum_specialist_acquisitions"])
            for row in route_rows
        ),
        "no_forbidden_route_keys": not any(core.forbidden_keys(row) for row in route_rows),
        "all_fitted_estimators_converged_or_constant": all(
            core.all_estimators_converged(policy) for policy in fitted_policies
        ),
        "selected_thresholds_respect_development_call_budget": (
            selected_thresholds_respect_budget(fitted_policies, policy_config)
        ),
        "metric_count_matches": len(metric_rows) == len(experiment["datasets"])
        * len(experiment["expected_models"]),
        "metric_identity_unique": len(metric_keys) == len(metric_rows),
        "all_metric_denominators_100": all(
            int(row["n"]) == int(experiment["expected_packets_per_dataset"])
            for row in metric_rows
        ),
        "comparison_source_row_count_preserved": len(original_rows)
        == expected_comparison_rows,
        "combined_table_row_count_matches": len(combined_rows)
        == expected_combined_rows,
        "generalist_retained_on_all_routes": (not cumulative)
        or all("generalist" in row["selected_roles"] for row in route_rows),
        "route_call_accounting_exact": all(
            int(row["total_role_acquisitions"])
            == 1 + int(row["specialist_acquisitions"])
            for row in route_rows
        ),
        "candidate_not_below_generalist_in_any_cell": (not cumulative)
        or candidate_not_below_generalist(original_rows, metric_rows),
        "independent_route_scoring_matches": independently_score_routes(
            route_rows, detail_rows, inputs_by_dataset
        ),
        "dreaddit_routes_out_of_fold": all(
            row["evaluation_mode"] == "five_fold_out_of_fold_development"
            for row in route_rows
            if row["dataset"] == "Dreaddit"
        ),
        "external_routes_use_dreaddit_transfer_policy": all(
            row["policy_kind"] == "dreaddit_full_development_transfer"
            for row in route_rows
            if row["dataset"] != "Dreaddit"
        ),
        "routes_written_before_scoring": route_path.is_file(),
        "new_llm_calls_made": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }
    positive_checks = {
        key: value
        for key, value in checks.items()
        if key not in {"new_llm_calls_made", "formal_run_enabled", "manuscript_eligible"}
    }
    status = (
        "validated_working_complete"
        if all(value is True for value in positive_checks.values())
        and checks["new_llm_calls_made"] is False
        and checks["formal_run_enabled"] is False
        and checks["manuscript_eligible"] is False
        else "working_validation_failed"
    )
    fold_manifest_path = output_dir / "fold_manifest.json"
    core.write_json(
        fold_manifest_path,
        {
            "schema_version": "working-warrantloop-fold-manifest-v0",
            "outer_fold_seed": experiment["outer_fold_seed"],
            "inner_split_seed": experiment["inner_split_seed"],
            "folds": fold_policies,
            "contains_source_text": False,
            "contains_item_truth": False,
            "manuscript_eligible": False,
        },
    )
    manifest = {
        "manifest_schema_version": "working-warrantloop-multicorpus-manifest-v0",
        "created_at_utc": core.now_utc(),
        "status": status,
        "experiment_id": experiment["experiment_id"],
        "result_label": "private_personal_exploratory_not_for_publication",
        "preflight": preflight_report(experiment, inputs_by_dataset),
        "checks": checks,
        "route_count": len(route_rows),
        "private_score_count": len(detail_rows),
        "metric_row_count": len(metric_rows),
        "combined_table_row_count": len(combined_rows),
        "quality_cost_row_count": len(quality_cost_rows),
        "input_hashes": {
            label: inputs["input_hashes"] for label, inputs in inputs_by_dataset.items()
        },
        "truth_hashes_opened_after_routes": truth_hashes,
        "artifacts": {
            "routes": {"path": str(route_path), "sha256": core.sha256_file(route_path)},
            "private_scores": {
                "path": str(detail_path),
                "sha256": core.sha256_file(detail_path),
            },
            "warrantloop_metrics": {
                "path": str(metrics_path),
                "sha256": core.sha256_file(metrics_path),
            },
            "combined_table_csv": {
                "path": str(combined_path),
                "sha256": core.sha256_file(combined_path),
            },
            "combined_table_markdown": {
                "path": str(markdown_path),
                "sha256": core.sha256_file(markdown_path),
            },
            "fold_manifest": {
                "path": str(fold_manifest_path),
                "sha256": core.sha256_file(fold_manifest_path),
            },
            "transfer_policy": {
                "path": str(transfer_policy_path),
                "sha256": transfer_policy_hash,
            },
        },
        "limitations": [
            "retrospective_working_replay_not_prospective",
            "heldout_outcomes_were_already_opened_by_the_prior_table3_working_run",
            "not_a_replacement_for_the_original_48_row_table3",
            "not_manuscript_evidence",
        ],
        "new_llm_calls_made": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }
    if quality_cost_path is not None:
        manifest["artifacts"]["quality_cost_comparison"] = {
            "path": str(quality_cost_path),
            "sha256": core.sha256_file(quality_cost_path),
        }
    manifest_path = output_dir / "manifest.json"
    core.write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "route_count": len(route_rows),
                "metric_row_count": len(metric_rows),
                "combined_table_row_count": len(combined_rows),
                "new_llm_calls_made": False,
                "manuscript_eligible": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "validated_working_complete" else 2


def run_formal(args: argparse.Namespace) -> int:
    del args
    raise RuntimeError(
        "formal_run_blocked:retrospective working replay is not a successor study freeze"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-config", type=Path, default=DEFAULT_EXPERIMENT_CONFIG
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    run_parser = subparsers.add_parser("run-working")
    run_parser.add_argument("--output-dir", type=Path, default=None)
    subparsers.add_parser("formal-run")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "preflight":
            return run_preflight(args)
        if args.command == "run-working":
            return run_working(args)
        if args.command == "formal-run":
            return run_formal(args)
        raise RuntimeError(f"unknown_command:{args.command}")
    except Exception as exc:
        print(f"WarrantLoop multicorpus {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
