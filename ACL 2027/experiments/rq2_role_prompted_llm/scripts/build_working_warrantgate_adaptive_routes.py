#!/usr/bin/env python3
"""Build working adaptive WarrantGate route records from generalist outputs."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any

from build_working_warrantgate_routes import (
    DEFAULT_RUN_ROOT,
    RQ2_ROOT,
    choose_route,
    clamp01,
    load_json,
    load_jsonl,
    packet_file_for,
    rating_features,
    selected_roles,
    source_free_packet_features,
    weighted_sum,
)


DEFAULT_ADAPTIVE_POLICY = RQ2_ROOT / "config" / "working_warrantgate_adaptive_v0_policy.json"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ordered_segments(packet: dict[str, Any]) -> list[dict[str, Any]]:
    contexts = packet.get("source_text_context", [])
    if not isinstance(contexts, list) or not contexts:
        return [
            {
                "segment_id": f"{packet['packet_id']}::packet",
                "display_order": 1,
                "source_id": None,
                "speaker_id": None,
                "local_context": None,
            }
        ]
    cleaned = [row for row in contexts if isinstance(row, dict)]
    return sorted(
        cleaned,
        key=lambda row: (
            row.get("display_order") if isinstance(row.get("display_order"), int) else 10**9,
            str(row.get("excerpt_id", "")),
        ),
    )


def segment_id(packet_id: str, segment: dict[str, Any], index: int) -> str:
    raw = segment.get("excerpt_id")
    if raw is not None:
        return str(raw)
    return f"{packet_id}::segment_{index + 1:04d}"


def source_free_segment_features(
    packet: dict[str, Any], segment: dict[str, Any], index: int, total: int
) -> dict[str, float]:
    base = source_free_packet_features(packet)
    source_id = segment.get("source_id")
    speaker_id = segment.get("speaker_id")
    candidate_role = str(segment.get("candidate_role", ""))
    contexts = ordered_segments(packet)
    source_run = sum(1 for row in contexts if row.get("source_id") == source_id) if source_id else 0
    speaker_run = (
        sum(1 for row in contexts if row.get("speaker_id") == speaker_id) if speaker_id else 0
    )
    local_context_present = 1.0 if segment.get("local_context") else 0.0
    structural = {
        "segment_position_norm": 0.0 if total <= 1 else index / (total - 1),
        "segment_is_first": 1.0 if index == 0 else 0.0,
        "segment_is_last": 1.0 if index == total - 1 else 0.0,
        "segment_source_repetition_norm": clamp01(source_run / max(total, 1)),
        "segment_speaker_repetition_norm": clamp01(speaker_run / max(total, 1)),
        "segment_has_speaker": 1.0 if speaker_id else 0.0,
        "segment_has_local_context": local_context_present,
        "segment_role_cited_or_support": 1.0
        if candidate_role in {"cited", "support"}
        else 0.0,
        "segment_role_context": 1.0
        if candidate_role in {"context", "context_only"}
        else 0.0,
    }
    router_features = segment.get("router_features")
    if isinstance(router_features, dict):
        for name, value in router_features.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                structural[str(name)] = clamp01(float(value))
    return {**base, **structural}


def adjusted_scores(
    scores: dict[str, float], previous_route: str | None, switch_penalty: float
) -> dict[str, float]:
    if previous_route is None:
        return dict(scores)
    return {
        route: score - (switch_penalty if route != previous_route else 0.0)
        for route, score in scores.items()
    }


def segment_route_scores(
    features: dict[str, float],
    base_policy: dict[str, Any],
    adaptive_policy: dict[str, Any],
) -> tuple[dict[str, float], dict[str, float]]:
    weights = base_policy["weights"]
    costs = base_policy["costs"]
    adjustments = adaptive_policy.get("segment_adjustments", {})
    if not isinstance(adjustments, dict):
        adjustments = {}

    g = weighted_sum(features, weights["generalist_sufficiency"])
    m = weighted_sum(features, weights["method_need"])
    d = weighted_sum(features, weights["domain_need"])

    for component_name, current in [
        ("generalist_sufficiency", g),
        ("method_need", m),
        ("domain_need", d),
    ]:
        component_adjustments = adjustments.get(component_name, {})
        if isinstance(component_adjustments, dict):
            current += weighted_sum(features, component_adjustments)
        if component_name == "generalist_sufficiency":
            g = current
        elif component_name == "method_need":
            m = current
        else:
            d = current

    interaction_features = {
        **features,
        "method_and_domain_scores": min(m, d),
        "method_flag_and_domain_flag": min(features["method_flag"], features["domain_flag"]),
        "low_scope_and_low_voice": min(
            features["low_scope_calibration"], features["low_voice_boundary"]
        ),
    }
    interaction_raw = weighted_sum(interaction_features, weights["interaction"])
    interaction_adjustments = adjustments.get("interaction", {})
    if isinstance(interaction_adjustments, dict):
        interaction_raw += weighted_sum(features, interaction_adjustments)

    components = {
        "generalist_sufficiency": g,
        "method_need": m,
        "domain_need": d,
        "interaction": interaction_raw,
    }
    scores = {
        "generalist": g,
        "qualitative_methods": m - float(costs["qualitative_methods"]),
        "domain": d - float(costs["domain"]),
        "both": min(m, d)
        + interaction_raw
        - float(costs["qualitative_methods"])
        - float(costs["domain"])
        - float(costs["both_coordination"]),
    }
    return components, scores


def choose_adaptive_sequence(
    segment_score_rows: list[dict[str, Any]], adaptive_policy: dict[str, Any]
) -> list[dict[str, Any]]:
    switching = adaptive_policy["switching"]
    previous_route: str | None = None
    run_length = 0
    routed: list[dict[str, Any]] = []
    for row in segment_score_rows:
        scores = row["scores"]
        adjusted = adjusted_scores(scores, previous_route, float(switching["switch_penalty"]))
        candidate = choose_route(adjusted, list(adaptive_policy["actions"]))
        changed = bool(previous_route and candidate != previous_route)
        if previous_route and candidate != previous_route:
            improvement = scores[candidate] - scores[previous_route]
            if improvement < float(switching["switch_margin"]):
                candidate = previous_route
                changed = False
            elif run_length < int(switching["minimum_dwell_segments"]):
                candidate = previous_route
                changed = False
        if previous_route == candidate:
            run_length += 1
        else:
            run_length = 1
        previous_route = candidate
        routed.append(
            {
                **row,
                "adjusted_scores": adjusted,
                "route": candidate,
                "selected_roles": selected_roles(candidate),
                "changed_from_previous_segment": changed,
            }
        )
    return routed


def aggregate_segment_routes(segment_routes: list[dict[str, Any]], adaptive_policy: dict[str, Any]) -> str:
    rules = adaptive_policy["packet_aggregation"]
    needs_method = any(
        route["route"] in {"qualitative_methods", "both"} for route in segment_routes
    )
    needs_domain = any(route["route"] in {"domain", "both"} for route in segment_routes)
    if needs_method and needs_domain:
        return str(rules["method_and_domain_route"])
    if needs_method:
        return str(rules["method_only_route"])
    if needs_domain:
        return str(rules["domain_only_route"])
    return str(rules["generalist_only_route"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--adaptive-policy", type=Path, default=DEFAULT_ADAPTIVE_POLICY)
    parser.add_argument("--base-policy", type=Path, default=None)
    parser.add_argument("--packet-file", type=Path, default=None)
    parser.add_argument("--generalist-scoring", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    adaptive_policy = load_json(args.adaptive_policy)
    base_policy_path = args.base_policy or RQ2_ROOT / str(adaptive_policy["base_policy"]).split(
        "experiments/rq2_role_prompted_llm/", 1
    )[-1]
    base_policy = load_json(base_policy_path)
    packet_file = args.packet_file or packet_file_for(args.run_root)
    scoring_file = (
        args.generalist_scoring
        or args.run_root / "reviewer_outputs" / "generalist" / "derived" / "scoring_inputs.jsonl"
    )
    output_dir = args.output_dir or args.run_root / "warrantgate" / adaptive_policy["policy_id"]

    packets = {str(row["packet_id"]): row for row in load_jsonl(packet_file)}
    rows: list[dict[str, Any]] = []
    by_model: dict[str, Counter[str]] = {}
    switch_counts: dict[str, int] = Counter()
    skipped_without_packet_metadata = 0

    for row in load_jsonl(scoring_file):
        packet_id = str(row["packet_id"])
        packet = packets.get(packet_id)
        if packet is None:
            skipped_without_packet_metadata += 1
            continue
        model_id = str(row["model_id"])
        rating = rating_features(row)
        segments = ordered_segments(packet)
        segment_score_rows: list[dict[str, Any]] = []
        for index, segment in enumerate(segments):
            features = {
                **source_free_segment_features(packet, segment, index, len(segments)),
                **rating,
            }
            components, scores = segment_route_scores(features, base_policy, adaptive_policy)
            segment_score_rows.append(
                {
                    "segment_id": segment_id(packet_id, segment, index),
                    "segment_index": index,
                    "components": components,
                    "scores": scores,
                    "features": features,
                    "contains_source_text": False,
                }
            )
        if rating["valid_generalist"]:
            segment_routes = choose_adaptive_sequence(segment_score_rows, adaptive_policy)
            route = aggregate_segment_routes(segment_routes, adaptive_policy)
        else:
            fallback = str(adaptive_policy["switching"]["failure_action"])
            segment_routes = [
                {
                    **segment_row,
                    "adjusted_scores": dict(segment_row["scores"]),
                    "route": fallback,
                    "selected_roles": selected_roles(fallback),
                    "changed_from_previous_segment": False,
                }
                for segment_row in segment_score_rows
            ]
            route = fallback
        by_model.setdefault(model_id, Counter())[route] += 1
        switch_counts[model_id] += sum(
            1 for segment_route in segment_routes if segment_route["changed_from_previous_segment"]
        )
        rows.append(
            {
                "route_record_schema_version": "working-warrantgate-adaptive-route-v0",
                "created_at_utc": now_utc(),
                "policy_id": adaptive_policy["policy_id"],
                "base_policy_id": base_policy["policy_id"],
                "router_name": adaptive_policy["router_name"],
                "router_formulation": adaptive_policy["router_formulation"],
                "corpus_id": row.get("corpus_id"),
                "model_id": model_id,
                "packet_id": packet_id,
                "source_generalist_scoring_file": str(scoring_file),
                "route": route,
                "selected_roles": selected_roles(route),
                "segment_count": len(segment_routes),
                "segment_switch_count": sum(
                    1
                    for segment_route in segment_routes
                    if segment_route["changed_from_previous_segment"]
                ),
                "segment_routes": segment_routes,
                "contains_source_text": False,
                "uses_known_intended_flaw_type": False,
                "uses_specialist_outputs": False,
                "manuscript_eligible": False,
            }
        )

    summary_rows: list[dict[str, Any]] = []
    for model_id, counter in sorted(by_model.items()):
        total = sum(counter.values())
        for route in adaptive_policy["actions"]:
            count = counter.get(route, 0)
            summary_rows.append(
                {
                    "policy_id": adaptive_policy["policy_id"],
                    "model_id": model_id,
                    "route": route,
                    "n": count,
                    "share": count / total if total else None,
                    "segment_switch_count": switch_counts.get(model_id, 0),
                }
            )

    write_jsonl(output_dir / "routes.jsonl", rows)
    write_csv(output_dir / "route_summary.csv", summary_rows)
    write_json(
        output_dir / "manifest.json",
        {
            "manifest_schema_version": "working-warrantgate-adaptive-route-manifest-v0",
            "created_at_utc": now_utc(),
            "adaptive_policy": str(args.adaptive_policy),
            "base_policy": str(base_policy_path),
            "run_root": str(args.run_root),
            "packet_file": str(packet_file),
            "generalist_scoring": str(scoring_file),
            "route_records": str(output_dir / "routes.jsonl"),
            "route_summary": str(output_dir / "route_summary.csv"),
            "record_count": len(rows),
            "skipped_without_packet_metadata": skipped_without_packet_metadata,
            "source_text_written": False,
            "known_intended_flaw_type_used": False,
            "specialist_outputs_used": False,
            "manuscript_eligible": False,
        },
    )
    print(output_dir / "routes.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
