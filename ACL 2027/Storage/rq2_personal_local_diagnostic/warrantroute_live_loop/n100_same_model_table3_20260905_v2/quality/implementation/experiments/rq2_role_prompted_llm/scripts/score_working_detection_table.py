#!/usr/bin/env python3
"""Score working role-prompted flaw detection outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_RUN_ROOT = WORKSPACE / "Storage" / "draft_review_packets" / "dreaddit_dev100_working_v1"
ROLES = ("generalist", "qualitative_methods", "domain")
SHARED_FIXED_ROLE = "qualitative_methods"
TARGET_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}
ROUTE_TO_ROLES = {
    "none": ("generalist",),
    "generalist": ("generalist",),
    "qualitative_methods": ("qualitative_methods",),
    "domain": ("domain",),
    "both": ("qualitative_methods", "domain"),
}
DATASET_LABELS = {
    "dreaddit": "Dreaddit",
    "goemotions": "GoEmotion",
    "agyw_focus_groups": "CaChe",
    "parlamint_gb": "ParlaMint-GB",
}
DATASET_ORDER = {
    "dreaddit": 0,
    "goemotions": 1,
    "agyw_focus_groups": 2,
    "parlamint_gb": 3,
}
METHOD_ORDER = {
    "Generalist": 0,
    "Fixed role": 1,
    "All roles": 2,
    "WarrantRoute": 3,
}
MODEL_LABELS = {
    "qwen3:8b": "Qwen3 8B",
    "llama3.1:8b": "Llama 3.1 8B",
    "gemma3:4b": "Gemma 3 4B",
}
MODEL_ORDER = {
    "qwen3:8b": 0,
    "llama3.1:8b": 1,
    "gemma3:4b": 2,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}: JSONL row is not an object")
                rows.append(value)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def wilson_ci(numerator: int, denominator: int, z: float = 1.96) -> tuple[float, float] | None:
    if denominator == 0:
        return None
    phat = numerator / denominator
    z2 = z * z
    denom = 1 + z2 / denominator
    centre = phat + z2 / (2 * denominator)
    margin = z * math.sqrt((phat * (1 - phat) + z2 / (4 * denominator)) / denominator)
    return ((centre - margin) / denom, (centre + margin) / denom)


def format_recall_with_ci(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    recall = 100 * numerator / denominator
    ci = wilson_ci(numerator, denominator)
    if ci is None:
        return f"{recall:.1f}"
    low, high = ci
    return f"{recall:.1f} [{100 * low:.1f}, {100 * high:.1f}]"


def load_quality_summary(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def role_scoring_path(reviewer_outputs_root: Path, role: str) -> Path:
    return reviewer_outputs_root / role / "derived" / "scoring_inputs.jsonl"


def normalized_flags(row: dict[str, Any] | None) -> set[str]:
    if not row:
        return set()
    rating = row.get("rating", {})
    if not isinstance(rating, dict):
        return set()
    flags = rating.get("serious_error_flags", [])
    if not isinstance(flags, list):
        return set()
    validation_errors = row.get("validation_errors", [])
    if not isinstance(validation_errors, list):
        validation_errors = []
    usable_schema_warning = (
        row.get("status") == "schema_warning"
        and set(validation_errors).issubset({"cannot_judge_invalid"})
    )
    if row.get("status") != "valid" and not usable_schema_warning:
        return set()
    return {str(flag) for flag in flags}


def output_status(row: dict[str, Any] | None) -> str:
    if not row:
        return "missing"
    return str(row.get("status"))


def load_warrantgate_routes(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None:
        return {}
    routes: dict[tuple[str, str], dict[str, Any]] = {}
    for row in load_jsonl(path):
        key = (str(row["model_id"]), str(row["packet_id"]))
        route = str(row["route"])
        if route not in ROUTE_TO_ROLES:
            raise ValueError(f"{path}: invalid route {route!r}")
        routes[key] = row
    return routes


def requested_expertise_route(row: dict[str, Any] | None) -> str:
    if not row:
        return "none"
    rating = row.get("rating", {})
    if not isinstance(rating, dict):
        return "none"
    route = str(rating.get("requested_expertise"))
    return route if route in ROUTE_TO_ROLES else "none"


def routed_flags(
    outputs: dict[tuple[str, str, str], dict[str, Any]],
    routes: dict[tuple[str, str], dict[str, Any]],
    model_id: str,
    packet_id: str,
) -> tuple[str, str, set[str], str]:
    route_record = routes.get((model_id, packet_id))
    if route_record:
        route = str(route_record["route"])
        route_source = str(route_record.get("policy_id", "warrantgate"))
    else:
        route = requested_expertise_route(outputs.get((model_id, "generalist", packet_id)))
        route_source = "generalist_requested_expertise_proxy"
    selected = ROUTE_TO_ROLES[route]
    flags: set[str] = set()
    statuses: list[str] = [
        f"generalist:{output_status(outputs.get((model_id, 'generalist', packet_id)))}"
    ]
    for role in selected:
        row = outputs.get((model_id, role, packet_id))
        flags.update(normalized_flags(row))
        if role != "generalist":
            statuses.append(f"{role}:{output_status(row)}")
    return route, ";".join(selected), flags, f"{route_source};" + ";".join(statuses)


def aggregate_detail_rows(detail_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in detail_rows:
        grouped[(row["corpus_id"], row["method"], row["model_id"], row["target_flaw"])].append(row)
        grouped[(row["corpus_id"], row["method"], row["model_id"], "ALL")].append(row)

    aggregate_rows: list[dict[str, Any]] = []
    for (corpus_id, method, model_id, flaw_type), rows in sorted(grouped.items()):
        tp = sum(1 for row in rows if row["detected"])
        n = len(rows)
        aggregate_rows.append(
            {
                "corpus_id": corpus_id,
                "method": method,
                "model_id": model_id,
                "flaw_type": flaw_type,
                "tp": tp,
                "n": n,
                "tp_over_n": f"{tp}/{n}",
                "recall": safe_ratio(tp, n),
                "credibility_success_rate": None,
                "conformability_success_rate": None,
                "quality_judge_valid_n": None,
            }
        )
    return aggregate_rows


def table3_sort_key(row: dict[str, Any]) -> tuple[int, str, int, str, int, str]:
    corpus_id = str(row["corpus_id"])
    method = str(row["method"])
    model_id = str(row["model_id"])
    return (
        DATASET_ORDER.get(corpus_id, 99),
        corpus_id,
        METHOD_ORDER.get(method, 99),
        method,
        MODEL_ORDER.get(model_id, 99),
        model_id,
    )


def build_table3_rows(aggregate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in sorted(aggregate_rows, key=table3_sort_key):
        if row["flaw_type"] != "ALL":
            continue
        method = str(row["method"])
        if method not in METHOD_ORDER:
            continue
        corpus_id = str(row["corpus_id"])
        model_id = str(row["model_id"])
        tp = int(row["tp"])
        n = int(row["n"])
        rows.append(
            {
                "Dataset": DATASET_LABELS.get(corpus_id, corpus_id),
                "Method": method,
                "Model": MODEL_LABELS.get(model_id, model_id),
                "TP/N": f"{tp}/{n}",
                "Recall (%) ↑": format_recall_with_ci(tp, n),
            }
        )
    return rows


def manuscript_table3_rows(table3_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows: list[dict[str, Any]] = []
    last_dataset = None
    last_method_by_dataset: dict[str, str | None] = {}
    for row in table3_rows:
        dataset = str(row["Dataset"])
        method = str(row["Method"])
        display_rows.append(
            {
                "Dataset": dataset if dataset != last_dataset else "",
                "Method": method if method != last_method_by_dataset.get(dataset) else "",
                "Model": row["Model"],
                "TP/N": row["TP/N"],
                "Recall (%) ↑": row["Recall (%) ↑"],
            }
        )
        last_dataset = dataset
        last_method_by_dataset[dataset] = method
    return display_rows


def write_markdown_table(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--truth-map", type=Path, default=None)
    parser.add_argument("--roles", nargs="+", choices=ROLES, default=list(ROLES))
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--reviewer-outputs-root", type=Path, default=None)
    parser.add_argument(
        "--fixed-role",
        choices=ROLES,
        default=SHARED_FIXED_ROLE,
        help="One development-frozen role shared by every reviewer model.",
    )
    parser.add_argument("--warrantgate-routes", type=Path, default=None)
    parser.add_argument("--adaptive-warrantgate-routes", type=Path, default=None)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--quality-summary", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    truth_path = args.truth_map or args.run_root / "private" / "truth_map.private.jsonl"
    quality_path = (
        args.quality_summary
        or args.run_root
        / "quality_judge"
        / "credibility_conformability"
        / "run_summary.json"
    )
    output_dir = args.output_dir or args.run_root / "table_exports" / "role_methods"
    reviewer_outputs_root = args.reviewer_outputs_root or args.run_root / "reviewer_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    truth_rows = load_jsonl(truth_path)
    warrantgate_routes = load_warrantgate_routes(args.warrantgate_routes)
    adaptive_warrantgate_routes = load_warrantgate_routes(args.adaptive_warrantgate_routes)
    outputs: dict[tuple[str, str, str], dict[str, Any]] = {}
    scoring_paths: dict[str, str] = {}
    for role in args.roles:
        path = role_scoring_path(reviewer_outputs_root, role)
        scoring_paths[role] = str(path)
        for row in load_jsonl(path):
            outputs[(str(row["model_id"]), role, str(row["packet_id"]))] = row

    model_ids = sorted({model_id for model_id, _role, _packet_id in outputs})
    if args.models:
        requested_models = set(args.models)
        model_ids = [model_id for model_id in model_ids if model_id in requested_models]
    if args.fixed_role not in args.roles:
        parser.error("--fixed-role must also be present in --roles")
    role_rows: list[dict[str, Any]] = []
    for model_id in model_ids:
        for role in args.roles:
            for truth in truth_rows:
                packet_id = truth["packet_id"]
                target_flaw = truth["known_intended_flaw_type"]
                target_flag = TARGET_TO_FLAG[target_flaw]
                row = outputs.get((model_id, role, packet_id))
                flags = normalized_flags(row)
                role_rows.append(
                    {
                        "corpus_id": truth.get("corpus_id", "unknown"),
                        "method": role,
                        "role": role,
                        "model_id": model_id,
                        "packet_id": packet_id,
                        "target_flaw": target_flaw,
                        "target_flag": target_flag,
                        "status": output_status(row),
                        "detected": target_flag in flags,
                        "serious_error_flags": ";".join(sorted(flags)),
                    }
                )

    role_aggregate_rows = aggregate_detail_rows(role_rows)
    fixed_role_by_model = {model_id: args.fixed_role for model_id in model_ids}
    fixed_role_diagnostics: list[dict[str, Any]] = []
    for model_id in model_ids:
        candidates = [
            row
            for row in role_aggregate_rows
            if row["model_id"] == model_id and row["flaw_type"] == "ALL"
        ]
        for row in candidates:
            fixed_role_diagnostics.append(
                {
                    "model_id": model_id,
                    "role": row["method"],
                    "tp_over_n": row["tp_over_n"],
                    "recall": row["recall"],
                    "selected_fixed_role": row["method"] == args.fixed_role,
                }
            )

    method_rows: list[dict[str, Any]] = []
    for model_id in model_ids:
        fixed_role = fixed_role_by_model[model_id]
        for truth in truth_rows:
            packet_id = truth["packet_id"]
            target_flaw = truth["known_intended_flaw_type"]
            target_flag = TARGET_TO_FLAG[target_flaw]
            generalist_row = outputs.get((model_id, "generalist", packet_id))
            fixed_row = outputs.get((model_id, fixed_role, packet_id))
            all_role_flags: set[str] = set()
            all_statuses: list[str] = []
            for role in args.roles:
                row = outputs.get((model_id, role, packet_id))
                all_role_flags.update(normalized_flags(row))
                all_statuses.append(f"{role}:{output_status(row)}")
            route, selected_roles, wr_flags, wr_status = routed_flags(
                outputs, warrantgate_routes, model_id, packet_id
            )
            adaptive_route, adaptive_selected_roles, adaptive_flags, adaptive_status = routed_flags(
                outputs, adaptive_warrantgate_routes, model_id, packet_id
            )
            method_specs = [
                (
                    "Generalist",
                    "generalist",
                    "generalist",
                    "generalist",
                    normalized_flags(generalist_row),
                    output_status(generalist_row),
                ),
                (
                    "Fixed role",
                    fixed_role,
                    "fixed",
                    fixed_role,
                    normalized_flags(fixed_row),
                    output_status(fixed_row),
                ),
                (
                    "All roles",
                    "union",
                    "all",
                    ";".join(args.roles),
                    all_role_flags,
                    ";".join(all_statuses),
                ),
            ]
            if not args.baseline_only:
                method_specs.append(
                    (
                        "WarrantRoute",
                        "routed",
                        route,
                        selected_roles,
                        wr_flags,
                        wr_status,
                    )
                )
            if adaptive_warrantgate_routes and not args.baseline_only:
                method_specs.append(
                    (
                        "Adaptive WarrantRoute",
                        "adaptive_routed",
                        adaptive_route,
                        adaptive_selected_roles,
                        adaptive_flags,
                        adaptive_status,
                    )
                )
            for method, role, route, selected_roles, flags, status in method_specs:
                method_rows.append(
                    {
                        "corpus_id": truth.get("corpus_id", "unknown"),
                        "method": method,
                        "role": role,
                        "route": route,
                        "selected_roles": selected_roles,
                        "model_id": model_id,
                        "packet_id": packet_id,
                        "target_flaw": target_flaw,
                        "target_flag": target_flag,
                        "status": status,
                        "detected": target_flag in flags,
                        "serious_error_flags": ";".join(sorted(flags)),
                    }
                )

    aggregate_rows = aggregate_detail_rows(method_rows)
    quality_summary = load_quality_summary(quality_path)
    quality_record_count = None
    credibility_success_rate = None
    conformability_success_rate = None
    if quality_summary:
        quality_record_count = quality_summary.get("valid_count")
        credibility_success_rate = quality_summary.get("credibility_success_rate")
        conformability_success_rate = quality_summary.get("conformability_success_rate")
    for row in aggregate_rows:
        if row["flaw_type"] == "ALL":
            row["credibility_success_rate"] = credibility_success_rate
            row["conformability_success_rate"] = conformability_success_rate
            row["quality_judge_valid_n"] = quality_record_count

    role_detail_csv = output_dir / "role_detection_detail.csv"
    role_aggregate_csv = output_dir / "role_metrics.csv"
    fixed_role_csv = output_dir / "fixed_role_selection.csv"
    detail_csv = output_dir / "method_detection_detail.csv"
    aggregate_csv = output_dir / "table_metrics.csv"
    table3_csv = output_dir / "table3_fill.csv"
    table3_manuscript_csv = output_dir / "table3_manuscript.csv"
    table3_md = output_dir / "table3_fill.md"
    table3_rows = build_table3_rows(aggregate_rows)
    table3_manuscript_rows = manuscript_table3_rows(table3_rows)
    write_csv(role_detail_csv, role_rows)
    write_csv(role_aggregate_csv, role_aggregate_rows)
    write_csv(fixed_role_csv, fixed_role_diagnostics)
    write_csv(detail_csv, method_rows)
    write_csv(aggregate_csv, aggregate_rows)
    write_csv(table3_csv, table3_rows)
    write_csv(table3_manuscript_csv, table3_manuscript_rows)
    write_markdown_table(table3_md, table3_manuscript_rows)

    method_definitions = {
        "Generalist": "Uses the generalist role output only.",
        "Fixed role": "Uses one development-frozen role shared by every reviewer model; this scorer does not reselect it from evaluation outcomes.",
        "All roles": "Counts a flaw as detected when any available role output flags the mapped flaw type.",
    }
    if not args.baseline_only:
        method_definitions["WarrantRoute"] = (
            "Uses --warrantgate-routes when provided; otherwise falls back to "
            "the generalist requested_expertise proxy."
        )
    if adaptive_warrantgate_routes and not args.baseline_only:
        method_definitions["Adaptive WarrantRoute"] = (
            "Optional segment-aware WarrantGate route sequence collapsed to a packet-level role union when --adaptive-warrantgate-routes is provided."
        )

    write_json(
        output_dir / "table_metrics.json",
        {
            "summary_schema_version": "working-role-method-table-metrics-v2",
            "run_root": str(args.run_root),
            "truth_map": str(truth_path),
            "reviewer_outputs_root": str(reviewer_outputs_root),
            "scoring_inputs": scoring_paths,
            "quality_summary": str(quality_path) if quality_summary else None,
            "contamination_control": {
                "included_split": "development_train",
                "excluded_split": "in_domain_audit",
            },
            "method_definitions": method_definitions,
            "baseline_only": args.baseline_only,
            "warrantgate_routes": str(args.warrantgate_routes) if args.warrantgate_routes else None,
            "adaptive_warrantgate_routes": (
                str(args.adaptive_warrantgate_routes)
                if args.adaptive_warrantgate_routes
                else None
            ),
            "fixed_role_selection_unit": "all_reviewer_models_pooled_on_development_data",
            "shared_fixed_role": args.fixed_role,
            "fixed_role_by_model": fixed_role_by_model,
            "metrics": {
                "tp_over_n": "true positives over evaluated packet count",
                "recall": "tp / n",
                "credibility_success_rate": "binary LLM-as-Judge success rate, Qiao et al. 2025 definition",
                "conformability_success_rate": "binary LLM-as-Judge success rate, Qiao et al. 2025 definition",
            },
            "aggregate_rows": aggregate_rows,
            "role_aggregate_rows": role_aggregate_rows,
            "fixed_role_diagnostics": fixed_role_diagnostics,
            "detail_csv": str(detail_csv),
            "aggregate_csv": str(aggregate_csv),
            "table3_csv": str(table3_csv),
            "table3_manuscript_csv": str(table3_manuscript_csv),
            "table3_md": str(table3_md),
            "table3_rows": table3_rows,
            "role_detail_csv": str(role_detail_csv),
            "role_aggregate_csv": str(role_aggregate_csv),
            "fixed_role_selection_csv": str(fixed_role_csv),
        },
    )
    print(aggregate_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
