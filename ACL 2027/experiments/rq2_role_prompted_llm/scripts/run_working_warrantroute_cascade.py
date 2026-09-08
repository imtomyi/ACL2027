#!/usr/bin/env python3
"""Replay frozen WarrantRoute-S decisions with cumulative output composition."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import run_working_warrantloop as core
import run_working_warrantloop_multicorpus as multicorpus


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "working_warrantroute_cascade_replay_v1.json"
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "warrantloop_working"
)


def resolve_workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE / path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_revised_table(
    original_rows: list[dict[str, str]],
    metric_rows: list[dict[str, Any]],
    method_name: str = "WarrantRoute",
) -> list[dict[str, str]]:
    by_key = {
        (str(row["dataset"]), multicorpus.MODEL_DISPLAY[str(row["model_id"])]): row
        for row in metric_rows
    }
    revised: list[dict[str, str]] = []
    replaced = 0
    for source in original_rows:
        row = dict(source)
        if row["Method"] == method_name:
            metric = by_key[(row["Dataset"], row["Model"])]
            row["TP/N"] = f"{metric['tp']}/{metric['n']}"
            row["Recall (%) ↑"] = multicorpus.format_recall(metric)
            replaced += 1
        revised.append(row)
    if replaced != len(metric_rows):
        raise ValueError(f"warrantroute_replacement_count_mismatch:{replaced}")
    return revised


def cascade_route(source: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    route = str(source["route"])
    expected_specialists = [
        role for role in core.roles_for_mode(route, True) if role != "generalist"
    ]
    acquired = [str(role) for role in source["acquired_specialists"]]
    if sorted(acquired) != sorted(expected_specialists):
        raise ValueError(f"source_route_specialist_mismatch:{source['packet_id']}")
    if int(source["specialist_acquisitions"]) != len(acquired):
        raise ValueError(f"source_specialist_count_mismatch:{source['packet_id']}")
    if int(source["total_role_acquisitions"]) != 1 + len(acquired):
        raise ValueError(f"source_total_call_count_mismatch:{source['packet_id']}")
    row = dict(source)
    row.update(
        {
            "route_record_schema_version": "working-warrantroute-cumulative-output-route-v1",
            "source_policy_id": source["policy_id"],
            "source_fitted_policy_sha256": source["fitted_policy_sha256"],
            "policy_id": config["experiment_id"],
            "router_name": config["router_name"],
            "paper_facing_name": config["paper_facing_name"],
            "internal_variant_id": config["internal_variant_id"],
            "selected_roles": list(core.roles_for_mode(route, True)),
            "total_role_cost": 1.0 + float(source["incremental_cost"]),
            "retain_generalist_output": True,
            "composition_change_only": True,
            "created_at_utc": core.now_utc(),
            "manuscript_eligible": False,
        }
    )
    return row


def validate_source(
    config: dict[str, Any]
) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
    manifest_path = resolve_workspace_path(str(config["source_manifest"]))
    route_path = resolve_workspace_path(str(config["source_routes"]))
    manifest = core.load_json(manifest_path)
    expected_hash = str(config["expected_source_routes_sha256"])
    if manifest.get("status") != "validated_working_complete":
        raise ValueError("source_run_not_validated_complete")
    if manifest["artifacts"]["routes"]["sha256"] != expected_hash:
        raise ValueError("source_manifest_route_hash_mismatch")
    if core.sha256_file(route_path) != expected_hash:
        raise ValueError("source_route_file_hash_mismatch")
    routes = read_jsonl(route_path)
    if len(routes) != int(config["expected_route_count"]):
        raise ValueError("source_route_count_mismatch")
    return manifest, route_path, routes


def load_inputs(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    base_experiment = core.load_json(
        resolve_workspace_path(str(config["base_experiment_config"]))
    )
    policy_config = core.load_json(
        resolve_workspace_path(str(base_experiment["policy_config"]))
    )
    return base_experiment, multicorpus.load_all_inputs(base_experiment, policy_config)


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    source_manifest, source_path, routes = validate_source(config)
    base_experiment, inputs = load_inputs(config)
    return {
        "status": "ready_for_cumulative_working_replay",
        "experiment_id": config["experiment_id"],
        "source_status": source_manifest["status"],
        "source_routes": str(source_path),
        "source_route_count": len(routes),
        "dataset_count": len(inputs),
        "model_count": len(base_experiment["expected_models"]),
        "new_llm_calls_required": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }


def run_working(args: argparse.Namespace) -> int:
    config = core.load_json(args.config)
    if any(
        config.get(key) is not False
        for key in ("new_llm_calls_allowed", "formal_run_enabled", "manuscript_eligible")
    ):
        raise ValueError("cascade_working_replay_must_fail_closed")
    source_manifest, source_path, source_routes = validate_source(config)
    base_experiment, inputs_by_dataset = load_inputs(config)
    output_dir = args.output_dir
    if not output_dir.resolve().is_relative_to(DEFAULT_OUTPUT_ROOT.resolve()):
        raise ValueError("output_outside_personal_local_root")
    core.require_new_output_dir(output_dir)

    route_rows = [cascade_route(row, config) for row in source_routes]
    route_path = output_dir / "routes.jsonl"
    core.write_jsonl(route_path, route_rows)

    detail_rows, metric_rows, truth_hashes = multicorpus.score_all_routes(
        route_rows, inputs_by_dataset
    )
    detail_path = output_dir / "scores.private.csv"
    metric_path = output_dir / "cascade_metrics.csv"
    core.write_csv(detail_path, detail_rows)
    core.write_csv(metric_path, metric_rows)

    comparison_path = resolve_workspace_path(str(config["comparison_source"]))
    with comparison_path.open("r", encoding="utf-8", newline="") as handle:
        comparison_rows = list(csv.DictReader(handle))
    dataset_order = [str(row["display_label"]) for row in base_experiment["datasets"]]
    method_name = str(config["paper_facing_name"])
    combined_rows = build_revised_table(
        comparison_rows, metric_rows, method_name
    )
    combined_csv_path = output_dir / "table3_warrantroute_improved_working.csv"
    combined_md_path = output_dir / "table3_warrantroute_improved_working.md"
    core.write_csv(combined_csv_path, combined_rows)
    multicorpus.write_markdown_table(combined_md_path, combined_rows, method_name)

    prior_metrics_path = resolve_workspace_path(str(config["prior_candidate_metrics"]))
    with prior_metrics_path.open("r", encoding="utf-8", newline="") as handle:
        prior_metric_rows = list(csv.DictReader(handle))
    quality_cost_rows = multicorpus.build_quality_cost_rows(
        comparison_rows,
        metric_rows,
        prior_metric_rows,
        dataset_order,
        method_name,
    )
    quality_cost_path = output_dir / "quality_cost_comparison.csv"
    core.write_csv(quality_cost_path, quality_cost_rows)

    source_decisions_unchanged = all(
        (new["dataset"], new["model_id"], new["packet_id"], new["route"], new["acquired_specialists"])
        == (old["dataset"], old["model_id"], old["packet_id"], old["route"], old["acquired_specialists"])
        for new, old in zip(route_rows, source_routes)
    )
    checks = {
        "source_run_validated": source_manifest["status"] == "validated_working_complete",
        "source_route_hash_matches": core.sha256_file(source_path)
        == config["expected_source_routes_sha256"],
        "route_count_matches": len(route_rows) == int(config["expected_route_count"]),
        "source_decisions_unchanged": source_decisions_unchanged,
        "generalist_retained_on_all_routes": all(
            "generalist" in row["selected_roles"] for row in route_rows
        ),
        "call_counts_unchanged": all(
            new["total_role_acquisitions"] == old["total_role_acquisitions"]
            for new, old in zip(route_rows, source_routes)
        ),
        "candidate_not_below_generalist_in_any_cell": (
            multicorpus.candidate_not_below_generalist(comparison_rows, metric_rows)
        ),
        "independent_route_scoring_matches": multicorpus.independently_score_routes(
            route_rows, detail_rows, inputs_by_dataset
        ),
        "comparison_source_row_count_matches": len(comparison_rows)
        == int(config["expected_comparison_source_rows"]),
        "combined_table_row_count_matches": len(combined_rows)
        == int(config["expected_combined_rows"]),
        "no_forbidden_route_keys": not any(core.forbidden_keys(row) for row in route_rows),
        "routes_written_before_scoring": route_path.is_file(),
        "new_llm_calls_made": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }
    positive = {
        key: value
        for key, value in checks.items()
        if key not in {"new_llm_calls_made", "formal_run_enabled", "manuscript_eligible"}
    }
    status = "validated_working_complete" if all(positive.values()) else "working_validation_failed"
    manifest = {
        "manifest_schema_version": "working-warrantroute-cumulative-output-manifest-v1",
        "created_at_utc": core.now_utc(),
        "status": status,
        "experiment_id": config["experiment_id"],
        "result_label": "private_personal_exploratory_not_for_publication",
        "checks": checks,
        "route_count": len(route_rows),
        "private_score_count": len(detail_rows),
        "metric_row_count": len(metric_rows),
        "combined_table_row_count": len(combined_rows),
        "truth_hashes_opened_after_routes": truth_hashes,
        "source_artifact": {
            "manifest": str(resolve_workspace_path(str(config["source_manifest"]))),
            "routes": str(source_path),
            "routes_sha256": core.sha256_file(source_path),
        },
        "artifacts": {
            "routes": {"path": str(route_path), "sha256": core.sha256_file(route_path)},
            "private_scores": {"path": str(detail_path), "sha256": core.sha256_file(detail_path)},
            "metrics": {"path": str(metric_path), "sha256": core.sha256_file(metric_path)},
            "combined_table_csv": {"path": str(combined_csv_path), "sha256": core.sha256_file(combined_csv_path)},
            "combined_table_markdown": {"path": str(combined_md_path), "sha256": core.sha256_file(combined_md_path)},
            "quality_cost_comparison": {"path": str(quality_cost_path), "sha256": core.sha256_file(quality_cost_path)},
        },
        "limitations": [
            "retrospective_composition_replay_of_existing_route_decisions",
            "not_a_newly_fitted_router",
            "all_positive_recall_only_benchmark",
            "not_manuscript_evidence",
        ],
        "new_llm_calls_made": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    run_parser = subparsers.add_parser("run-working")
    run_parser.add_argument("--output-dir", type=Path, required=True)
    subparsers.add_parser("formal-run")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = core.load_json(args.config)
        if args.command == "preflight":
            print(json.dumps(preflight(config), indent=2, sort_keys=True))
            return 0
        if args.command == "run-working":
            return run_working(args)
        if args.command == "formal-run":
            raise RuntimeError("formal_run_blocked:retrospective cascade replay")
        raise RuntimeError(f"unknown_command:{args.command}")
    except Exception as exc:
        print(f"WarrantRoute cascade {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
