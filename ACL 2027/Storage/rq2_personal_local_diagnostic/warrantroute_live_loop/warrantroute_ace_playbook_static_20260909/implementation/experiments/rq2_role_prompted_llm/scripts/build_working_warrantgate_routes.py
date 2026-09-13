#!/usr/bin/env python3
"""Build working WarrantGate route records from generalist outputs."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_POLICY = RQ2_ROOT / "config" / "working_warrantgate_v0_policy.json"
DEFAULT_RUN_ROOT = WORKSPACE / "Storage" / "draft_review_packets" / "dreaddit_dev100_working_v1"
METHOD_FLAGS = {
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "unsupported_abstraction",
    "inconsistent_codebook",
}
DOMAIN_FLAGS = {
    "contextual_flattening",
    "sensitive_or_diagnostic_inference",
    "wrong_attribution",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


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


def packet_file_for(run_root: Path) -> Path:
    candidates = sorted((run_root / "by_dataset").glob("*.review_packets.jsonl"))
    if len(candidates) != 1:
        raise ValueError(f"{run_root}: expected one packet file, found {len(candidates)}")
    return candidates[0]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def low_score(value: Any) -> float:
    if not isinstance(value, int):
        return 1.0
    return clamp01((5 - value) / 4)


def high_confidence(value: Any) -> float:
    if not isinstance(value, int):
        return 0.0
    return clamp01((value - 1) / 4)


def source_free_packet_features(packet: dict[str, Any]) -> dict[str, float]:
    contexts = packet.get("source_text_context", [])
    if not isinstance(contexts, list):
        contexts = []
    source_ids = {
        str(row.get("source_id"))
        for row in contexts
        if isinstance(row, dict) and row.get("source_id") is not None
    }
    speaker_ids = {
        str(row.get("speaker_id"))
        for row in contexts
        if isinstance(row, dict) and row.get("speaker_id") is not None
    }
    claim = packet.get("llm_generated_qualitative_claim", {})
    cited = claim.get("cited_excerpt_ids", []) if isinstance(claim, dict) else []
    cited_count = len(cited) if isinstance(cited, list) else 0
    source_count = len(source_ids)
    excerpt_count = len(contexts)
    return {
        "excerpt_count_norm": clamp01(excerpt_count / 8),
        "source_count_norm": clamp01(source_count / 6),
        "speaker_count_norm": clamp01(len(speaker_ids) / 6),
        "low_cited_source_count": 1.0 if cited_count <= 1 else 0.0,
        "source_concentration_signal": 1.0 if source_count <= 1 and excerpt_count >= 3 else 0.0,
        "speaker_or_turn_context": 1.0 if speaker_ids else 0.0,
    }


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def rating_features(row: dict[str, Any]) -> dict[str, float]:
    rating = row.get("rating", {})
    if row.get("status") != "valid" or not isinstance(rating, dict):
        return {
            "valid_generalist": 0.0,
            "accept": 0.0,
            "high_confidence": 0.0,
            "no_cannot_judge": 0.0,
            "no_serious_flags": 0.0,
            "low_evidential_credibility": 1.0,
            "low_scope_calibration": 1.0,
            "low_voice_boundary": 1.0,
            "cannot_judge_present": 1.0,
            "method_flag": 0.0,
            "domain_flag": 0.0,
            "requested_method_or_both": 0.0,
            "requested_domain_or_both": 0.0,
            "requested_both": 0.0,
        }
    flags = {str(flag) for flag in as_list(rating.get("serious_error_flags"))}
    cannot_judge = as_list(rating.get("cannot_judge"))
    requested = str(rating.get("requested_expertise"))
    return {
        "valid_generalist": 1.0,
        "accept": 1.0 if rating.get("disposition") == "accept" else 0.0,
        "high_confidence": high_confidence(rating.get("confidence")),
        "no_cannot_judge": 1.0 if not cannot_judge else 0.0,
        "no_serious_flags": 1.0 if not flags else 0.0,
        "low_evidential_credibility": low_score(rating.get("evidential_credibility")),
        "low_scope_calibration": low_score(rating.get("scope_calibration")),
        "low_voice_boundary": low_score(rating.get("voice_boundary_preservation")),
        "cannot_judge_present": 1.0 if cannot_judge else 0.0,
        "method_flag": 1.0 if flags & METHOD_FLAGS else 0.0,
        "domain_flag": 1.0 if flags & DOMAIN_FLAGS else 0.0,
        "requested_method_or_both": 1.0 if requested in {"qualitative_methods", "both"} else 0.0,
        "requested_domain_or_both": 1.0 if requested in {"domain", "both"} else 0.0,
        "requested_both": 1.0 if requested == "both" else 0.0,
    }


def weighted_sum(features: dict[str, float], weights: dict[str, float]) -> float:
    return sum(float(weight) * float(features.get(name, 0.0)) for name, weight in weights.items())


def route_scores(
    features: dict[str, float], policy: dict[str, Any]
) -> tuple[dict[str, float], dict[str, float]]:
    weights = policy["weights"]
    costs = policy["costs"]
    g = weighted_sum(features, weights["generalist_sufficiency"])
    m = weighted_sum(features, weights["method_need"])
    d = weighted_sum(features, weights["domain_need"])
    interaction_raw = weighted_sum(
        {
            **features,
            "method_and_domain_scores": min(m, d),
            "method_flag_and_domain_flag": min(features["method_flag"], features["domain_flag"]),
            "low_scope_and_low_voice": min(
                features["low_scope_calibration"], features["low_voice_boundary"]
            ),
        },
        weights["interaction"],
    )
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


def choose_route(scores: dict[str, float], tie_order: list[str]) -> str:
    order = {name: index for index, name in enumerate(tie_order)}
    return max(scores, key=lambda key: (scores[key], -order.get(key, 99)))


def selected_roles(route: str) -> list[str]:
    return {
        "generalist": ["generalist"],
        "qualitative_methods": ["qualitative_methods"],
        "domain": ["domain"],
        "both": ["qualitative_methods", "domain"],
    }[route]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--packet-file", type=Path, default=None)
    parser.add_argument("--generalist-scoring", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    policy = load_json(args.policy)
    packet_file = args.packet_file or packet_file_for(args.run_root)
    scoring_file = (
        args.generalist_scoring
        or args.run_root / "reviewer_outputs" / "generalist" / "derived" / "scoring_inputs.jsonl"
    )
    output_dir = args.output_dir or args.run_root / "warrantgate" / policy["policy_id"]

    packets = {str(row["packet_id"]): row for row in load_jsonl(packet_file)}
    rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    by_model: dict[str, Counter[str]] = {}
    skipped_without_packet_metadata = 0

    for row in load_jsonl(scoring_file):
        packet_id = str(row["packet_id"])
        packet = packets.get(packet_id)
        if packet is None:
            skipped_without_packet_metadata += 1
            continue
        features = {**source_free_packet_features(packet), **rating_features(row)}
        components, scores = route_scores(features, policy)
        route = (
            choose_route(scores, list(policy["tie_order"]))
            if features["valid_generalist"]
            else str(policy["inference_failure_action"])
        )
        model_id = str(row["model_id"])
        by_model.setdefault(model_id, Counter())[route] += 1
        rows.append(
            {
                "route_record_schema_version": "working-warrantgate-route-v0",
                "created_at_utc": now_utc(),
                "policy_id": policy["policy_id"],
                "router_name": policy["router_name"],
                "router_formulation": policy["router_formulation"],
                "corpus_id": row.get("corpus_id"),
                "model_id": model_id,
                "packet_id": packet_id,
                "source_generalist_scoring_file": str(scoring_file),
                "route": route,
                "selected_roles": selected_roles(route),
                "components": components,
                "scores": scores,
                "features": features,
                "contains_source_text": False,
                "uses_known_intended_flaw_type": False,
                "uses_specialist_outputs": False,
                "manuscript_eligible": False,
            }
        )

    for model_id, counter in sorted(by_model.items()):
        total = sum(counter.values())
        for route in policy["actions"]:
            count = counter.get(route, 0)
            summary_rows.append(
                {
                    "policy_id": policy["policy_id"],
                    "model_id": model_id,
                    "route": route,
                    "n": count,
                    "share": count / total if total else None,
                }
            )

    write_jsonl(output_dir / "routes.jsonl", rows)
    write_csv(output_dir / "route_summary.csv", summary_rows)
    write_json(
        output_dir / "manifest.json",
        {
            "manifest_schema_version": "working-warrantgate-route-manifest-v0",
            "created_at_utc": now_utc(),
            "policy": str(args.policy),
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
