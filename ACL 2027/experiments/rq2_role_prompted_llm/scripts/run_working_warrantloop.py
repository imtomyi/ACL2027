#!/usr/bin/env python3
"""Fit and smoke-test the development-only WarrantLoop offline replay."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import inspect
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from build_working_warrantgate_routes import (
    load_json,
    load_jsonl,
    rating_features,
    route_scores,
    source_free_packet_features,
)


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "working_warrantloop_v0_policy.json"
DEFAULT_GATE_POLICY = RQ2_ROOT / "config" / "working_warrantgate_v0_policy.json"
DEFAULT_RUN_ROOT = (
    WORKSPACE / "Storage" / "draft_review_packets" / "dreaddit_dev580_working_v1"
)
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "warrantloop_working"
)

ROLES = ("generalist", "qualitative_methods", "domain")
TRANSITIONS = ("GM", "GD", "GB", "MB", "DB")
TRANSITION_ENDPOINTS = {
    "GM": ("generalist", "qualitative_methods"),
    "GD": ("generalist", "domain"),
    "GB": ("generalist", "both"),
    "MB": ("qualitative_methods", "both"),
    "DB": ("domain", "both"),
}
TARGET_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}
SOURCE_FEATURE_ORDER = (
    "excerpt_count_norm",
    "source_count_norm",
    "speaker_count_norm",
    "low_cited_source_count",
    "source_concentration_signal",
    "speaker_or_turn_context",
)
RATING_FEATURE_ORDER = (
    "valid_generalist",
    "accept",
    "high_confidence",
    "no_cannot_judge",
    "no_serious_flags",
    "low_evidential_credibility",
    "low_scope_calibration",
    "low_voice_boundary",
    "cannot_judge_present",
    "method_flag",
    "domain_flag",
    "requested_method_or_both",
    "requested_domain_or_both",
    "requested_both",
)
INITIAL_FEATURE_ORDER = (
    *SOURCE_FEATURE_ORDER,
    *(f"generalist_{name}" for name in RATING_FEATURE_ORDER),
    "warrantgate_component_generalist_sufficiency",
    "warrantgate_component_method_need",
    "warrantgate_component_domain_need",
    "warrantgate_component_interaction",
    "warrantgate_score_generalist",
    "warrantgate_score_qualitative_methods",
    "warrantgate_score_domain",
    "warrantgate_score_both",
)
FORBIDDEN_ROUTE_KEYS = {
    "known_intended_flaw_type",
    "known_intended_flaw_note",
    "target_flaw",
    "target_flag",
    "source_text_context",
    "text",
    "claim",
    "explanation",
    "rationale",
    "raw_response",
    "human_judgment",
    "final_grader",
    "heldout_outcome",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_digest(*values: str) -> str:
    joined = "\x1f".join(values).encode("utf-8")
    return sha256_bytes(joined)


def secure_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def secure_write_text(path: Path, value: str) -> None:
    secure_mkdir(path.parent)
    path.write_text(value, encoding="utf-8")
    os.chmod(path, 0o600)


def write_json(path: Path, value: dict[str, Any]) -> None:
    secure_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    value = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    secure_write_text(path, value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    secure_mkdir(path.parent)
    if not rows:
        secure_write_text(path, "")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


def require_new_output_dir(path: Path) -> None:
    if path.exists():
        raise RuntimeError(f"output_exists_refusing_overwrite:{path}")
    secure_mkdir(path)


def packet_paths(run_root: Path, packet_set: str) -> tuple[Path, Path, Path]:
    packet_root = run_root / "sample_packets" / packet_set
    candidates = sorted((packet_root / "by_dataset").glob("*.review_packets.jsonl"))
    if len(candidates) != 1:
        raise ValueError(f"expected_one_packet_file:{packet_root}:{len(candidates)}")
    truth_path = packet_root / "private" / "truth_map.private.jsonl"
    manifest_path = packet_root / "manifest.json"
    for path in (truth_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    return candidates[0], truth_path, manifest_path


def role_scoring_path(run_root: Path, role: str) -> Path:
    path = run_root / "reviewer_outputs" / role / "derived" / "scoring_inputs.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def source_groups(packet: dict[str, Any]) -> frozenset[str]:
    contexts = packet.get("source_text_context")
    if not isinstance(contexts, list):
        raise ValueError(f"packet_context_not_list:{packet.get('packet_id')}")
    groups = {
        str(row["source_id"])
        for row in contexts
        if isinstance(row, dict) and row.get("source_id") is not None
    }
    if not groups:
        raise ValueError(f"packet_has_no_source_group:{packet.get('packet_id')}")
    return frozenset(groups)


def packet_projection(packet: dict[str, Any]) -> dict[str, float]:
    projected = source_free_packet_features(packet)
    if tuple(projected) != SOURCE_FEATURE_ORDER:
        raise ValueError("source_feature_order_drift")
    return {name: float(projected[name]) for name in SOURCE_FEATURE_ORDER}


def role_projection(row: dict[str, Any]) -> dict[str, float]:
    projected = rating_features(row)
    if tuple(projected) != RATING_FEATURE_ORDER:
        raise ValueError("rating_feature_order_drift")
    return {name: float(projected[name]) for name in RATING_FEATURE_ORDER}


def normalized_flags(row: dict[str, Any] | None) -> set[str]:
    if row is None or row.get("status") != "valid":
        return set()
    rating = row.get("rating")
    if not isinstance(rating, dict):
        return set()
    values = rating.get("serious_error_flags")
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


def roles_for_mode(
    mode: str, retain_generalist_output: bool = False
) -> tuple[str, ...]:
    if mode == "generalist":
        roles = ("generalist",)
    elif mode == "qualitative_methods":
        roles = (
            ("generalist", "qualitative_methods")
            if retain_generalist_output
            else ("qualitative_methods",)
        )
    elif mode == "domain":
        roles = (
            ("generalist", "domain")
            if retain_generalist_output
            else ("domain",)
        )
    elif mode == "both":
        roles = (
            ("generalist", "qualitative_methods", "domain")
            if retain_generalist_output
            else ("qualitative_methods", "domain")
        )
    else:
        raise ValueError(f"unknown_mode:{mode}")
    return roles


def roles_detected(
    roles: Iterable[str],
    role_rows: dict[str, dict[str, Any]],
    target_flag: str,
) -> bool:
    flags: set[str] = set()
    for role in roles:
        flags.update(normalized_flags(role_rows.get(role)))
    return target_flag in flags


def mode_detected(
    mode: str,
    role_rows: dict[str, dict[str, Any]],
    target_flag: str,
    retain_generalist_output: bool = False,
) -> bool:
    return roles_detected(
        roles_for_mode(mode, retain_generalist_output), role_rows, target_flag
    )


def retain_generalist_output(config: dict[str, Any]) -> bool:
    return bool(
        config.get("output_composition", {}).get(
            "retain_generalist_output", False
        )
    )


def load_working_inputs(
    run_root: Path,
    packet_set: str,
    config: dict[str, Any],
    *,
    require_development_lane: bool,
) -> dict[str, Any]:
    if require_development_lane:
        development = config["development"]
        if run_root.name != development["allowed_run_root_name"]:
            raise ValueError(f"development_run_root_not_bound:{run_root.name}")
        if packet_set != development["packet_set"]:
            raise ValueError(f"development_packet_set_not_bound:{packet_set}")
    packet_path, truth_path, packet_manifest_path = packet_paths(run_root, packet_set)
    packet_manifest = load_json(packet_manifest_path)
    run_manifest_path = run_root / "manifest.json"
    run_manifest = load_json(run_manifest_path)
    if require_development_lane:
        if run_manifest.get("status") != "working_development_only_not_manuscript_eligible":
            raise ValueError("development_run_manifest_status_mismatch")
        if run_manifest.get("corpus_id") != config["development"]["allowed_corpus_id"]:
            raise ValueError("development_run_manifest_corpus_mismatch")
        if run_manifest.get("source_split") != config["development"]["required_source_split"]:
            raise ValueError("development_run_manifest_split_mismatch")
        if packet_manifest.get("corpus_id") != config["development"]["allowed_corpus_id"]:
            raise ValueError("packet_manifest_corpus_mismatch")
        if int(packet_manifest.get("sample_n", -1)) != 100:
            raise ValueError("packet_manifest_sample_size_mismatch")
    packets_raw = load_jsonl(packet_path)
    if not packets_raw:
        raise ValueError("empty_packet_file")
    packet_ids: set[str] = set()
    projections: dict[str, dict[str, float]] = {}
    groups: dict[str, frozenset[str]] = {}
    for packet in packets_raw:
        packet_id = str(packet.get("packet_id"))
        if not packet_id or packet_id in packet_ids:
            raise ValueError(f"duplicate_or_missing_packet_id:{packet_id}")
        if require_development_lane:
            development = config["development"]
            if packet.get("corpus_id") != development["allowed_corpus_id"]:
                raise ValueError(f"development_corpus_mismatch:{packet_id}")
            if development["allowed_dataset_role_substring"] not in str(
                packet.get("dataset_role", "")
            ):
                raise ValueError(f"development_lane_not_declared:{packet_id}")
            contexts = packet.get("source_text_context", [])
            splits = {
                str(row.get("metadata", {}).get("split"))
                for row in contexts
                if isinstance(row, dict) and isinstance(row.get("metadata"), dict)
            }
            if splits != {development["required_source_split"]}:
                raise ValueError(f"development_split_mismatch:{packet_id}:{sorted(splits)}")
        packet_ids.add(packet_id)
        projections[packet_id] = packet_projection(packet)
        groups[packet_id] = source_groups(packet)

    if require_development_lane:
        source_owner: dict[str, str] = {}
        for packet_id, packet_groups in groups.items():
            for group in packet_groups:
                previous = source_owner.get(group)
                if previous is not None and previous != packet_id:
                    raise ValueError(f"shared_source_group:{previous}:{packet_id}")
                source_owner[group] = packet_id

    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    role_hashes: dict[str, str] = {}
    models_by_role: dict[str, set[str]] = {}
    invalid_by_role: dict[str, int] = {}
    for role in ROLES:
        path = role_scoring_path(run_root, role)
        role_hashes[role] = sha256_file(path)
        models: set[str] = set()
        invalid = 0
        for row in load_jsonl(path):
            packet_id = str(row.get("packet_id"))
            if packet_id not in packet_ids:
                continue
            model_id = str(row.get("model_id"))
            key = (model_id, role, packet_id)
            if key in rows:
                raise ValueError(f"duplicate_role_projection:{key}")
            if str(row.get("role")) != role:
                raise ValueError(f"role_projection_mismatch:{key}")
            rows[key] = row
            models.add(model_id)
            if row.get("status") != "valid":
                invalid += 1
        models_by_role[role] = models
        invalid_by_role[role] = invalid

    model_sets = list(models_by_role.values())
    models = set.intersection(*model_sets) if model_sets else set()
    if not models or any(value != models for value in model_sets):
        raise ValueError(f"role_model_inventory_mismatch:{models_by_role}")
    expected = len(packet_ids) * len(models) * len(ROLES)
    if len(rows) != expected:
        raise ValueError(f"incomplete_role_inventory:{len(rows)}:{expected}")

    role_projections = {
        key: role_projection(row)
        for key, row in rows.items()
    }
    return {
        "run_root": run_root,
        "packet_path": packet_path,
        "truth_path": truth_path,
        "packet_manifest_path": packet_manifest_path,
        "packet_manifest": packet_manifest,
        "packet_ids": sorted(packet_ids),
        "corpus_id": str(packets_raw[0].get("corpus_id")) if packets_raw else "unknown",
        "packet_projections": projections,
        "source_groups": groups,
        "role_rows": rows,
        "role_projections": role_projections,
        "models": sorted(models),
        "invalid_by_role": invalid_by_role,
        "input_hashes": {
            "packet_file": sha256_file(packet_path),
            "truth_file_private": sha256_file(truth_path),
            "packet_manifest": sha256_file(packet_manifest_path),
            "run_manifest": sha256_file(run_manifest_path),
            **{f"{role}_scoring": value for role, value in role_hashes.items()},
        },
    }


def load_truth_subset(truth_path: Path, allowed_packet_ids: set[str]) -> dict[str, str]:
    truth: dict[str, str] = {}
    with truth_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"truth_row_not_object:{line_number}")
            packet_id = str(row.get("packet_id"))
            if packet_id not in allowed_packet_ids:
                continue
            flaw = str(row.get("known_intended_flaw_type"))
            if packet_id in truth:
                raise ValueError(f"duplicate_truth:{packet_id}")
            if flaw not in TARGET_TO_FLAG:
                raise ValueError(f"unknown_truth_label:{packet_id}:{flaw}")
            truth[packet_id] = flaw
    if set(truth) != allowed_packet_ids:
        raise ValueError("truth_subset_inventory_mismatch")
    return truth


def deterministic_split(
    packet_ids: list[str],
    config: dict[str, Any],
) -> dict[str, list[str]]:
    ratios = config["development"]["split_ratios"]
    if not math.isclose(sum(float(value) for value in ratios.values()), 1.0):
        raise ValueError("split_ratios_do_not_sum_to_one")
    seed = str(config["development"]["split_seed"])
    ordered = sorted(packet_ids, key=lambda packet_id: stable_digest(seed, packet_id))
    n = len(ordered)
    train_n = int(n * float(ratios["train"]))
    validation_n = int(n * float(ratios["validation"]))
    smoke_n = n - train_n - validation_n
    if min(train_n, validation_n, smoke_n) <= 0:
        raise ValueError(f"split_partition_empty:{n}")
    result = {
        "train": ordered[:train_n],
        "validation": ordered[train_n : train_n + validation_n],
        "smoke_test": ordered[train_n + validation_n :],
    }
    for split in result:
        result[split].sort()
    flattened = [packet_id for ids in result.values() for packet_id in ids]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(packet_ids):
        raise ValueError("split_packet_overlap_or_omission")
    return result


def verify_group_disjoint(
    split: dict[str, list[str]], groups: dict[str, frozenset[str]]
) -> None:
    source_sets: dict[str, set[str]] = {}
    for name, ids in split.items():
        source_sets[name] = set().union(*(groups[packet_id] for packet_id in ids))
    names = sorted(source_sets)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if source_sets[left] & source_sets[right]:
                raise ValueError(f"source_group_split_overlap:{left}:{right}")


def prefixed(features: dict[str, float], prefix: str) -> dict[str, float]:
    return {f"{prefix}_{name}": value for name, value in features.items()}


def initial_features(
    packet_features: dict[str, float],
    generalist_features: dict[str, float],
    gate_policy: dict[str, Any],
) -> dict[str, float]:
    gate_input = {**packet_features, **generalist_features}
    components, scores = route_scores(gate_input, gate_policy)
    values = {
        **packet_features,
        **prefixed(generalist_features, "generalist"),
        **{f"warrantgate_component_{name}": float(value) for name, value in components.items()},
        **{f"warrantgate_score_{name}": float(value) for name, value in scores.items()},
    }
    if tuple(values) != INITIAL_FEATURE_ORDER:
        raise ValueError("initial_feature_order_drift")
    return values


def transition_features(
    transition: str,
    packet_features: dict[str, float],
    projections: dict[str, dict[str, float]],
    gate_policy: dict[str, Any],
) -> dict[str, float]:
    values = initial_features(packet_features, projections["generalist"], gate_policy)
    if transition == "MB":
        values.update(prefixed(projections["qualitative_methods"], "qualitative_methods"))
    elif transition == "DB":
        values.update(prefixed(projections["domain"], "domain"))
    elif transition not in {"GM", "GD", "GB"}:
        raise ValueError(f"unknown_transition:{transition}")
    return values


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def fit_binary_logistic(
    examples: list[dict[str, float]],
    labels: list[int],
    feature_order: list[str],
    estimator_config: dict[str, Any],
) -> dict[str, Any]:
    if not examples or len(examples) != len(labels):
        raise ValueError("invalid_logistic_training_inventory")
    if any(label not in {0, 1} for label in labels):
        raise ValueError("binary_labels_required")
    positives = sum(labels)
    negatives = len(labels) - positives
    smoothed = (positives + 1.0) / (len(labels) + 2.0)
    minimum_class_count = int(estimator_config["minimum_class_count_for_logistic"])
    if min(positives, negatives) < minimum_class_count:
        return {
            "kind": "constant",
            "probability": smoothed,
            "training_n": len(labels),
            "positive_n": positives,
            "negative_n": negatives,
            "fallback_reason": "minimum_class_count_not_met",
            "minimum_class_count_for_logistic": minimum_class_count,
            "smoothing": estimator_config["constant_target_smoothing"],
        }

    weights = [0.0] * len(feature_order)
    intercept = math.log(smoothed / (1.0 - smoothed))
    learning_rate = float(estimator_config["learning_rate"])
    l2 = float(estimator_config["l2"])
    tolerance = float(estimator_config["convergence_tolerance"])
    maximum_iterations = int(estimator_config["maximum_iterations"])
    rows = [[float(example[name]) for name in feature_order] for example in examples]
    converged = False
    iteration = 0
    for iteration in range(1, maximum_iterations + 1):
        grad_intercept = 0.0
        grad_weights = [0.0] * len(weights)
        for row, label in zip(rows, labels):
            prediction = sigmoid(intercept + sum(w * x for w, x in zip(weights, row)))
            error = prediction - label
            grad_intercept += error
            for index, value in enumerate(row):
                grad_weights[index] += error * value
        scale = 1.0 / len(rows)
        grad_intercept *= scale
        for index, weight in enumerate(weights):
            grad_weights[index] = grad_weights[index] * scale + l2 * weight
        delta_intercept = learning_rate * grad_intercept
        deltas = [learning_rate * value for value in grad_weights]
        intercept -= delta_intercept
        weights = [weight - delta for weight, delta in zip(weights, deltas)]
        if max([abs(delta_intercept), *(abs(value) for value in deltas)]) <= tolerance:
            converged = True
            break
    if not all(math.isfinite(value) for value in [intercept, *weights]):
        raise ValueError("nonfinite_logistic_coefficients")
    return {
        "kind": "logistic",
        "intercept": intercept,
        "weights": dict(zip(feature_order, weights)),
        "training_n": len(labels),
        "positive_n": positives,
        "iterations": iteration,
        "converged": converged,
        "l2": l2,
    }


def predict_binary(model: dict[str, Any], features: dict[str, float]) -> float:
    if model["kind"] == "constant":
        return float(model["probability"])
    value = float(model["intercept"])
    for name, weight in model["weights"].items():
        value += float(weight) * float(features[name])
    return sigmoid(value)


def brier_score(probabilities: list[float], labels: list[int]) -> float | None:
    if not labels:
        return None
    return sum((probability - label) ** 2 for probability, label in zip(probabilities, labels)) / len(
        labels
    )


def role_bundle(
    inputs: dict[str, Any], model_id: str, packet_id: str
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, Any]]]:
    projections = {
        role: inputs["role_projections"][(model_id, role, packet_id)] for role in ROLES
    }
    rows = {role: inputs["role_rows"][(model_id, role, packet_id)] for role in ROLES}
    return projections, rows


def fit_transition_models(
    inputs: dict[str, Any],
    truth: dict[str, str],
    model_id: str,
    packet_ids: list[str],
    gate_policy: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    models: dict[str, Any] = {}
    cumulative = retain_generalist_output(config)
    for transition in TRANSITIONS:
        examples: list[dict[str, float]] = []
        improve_labels: list[int] = []
        harm_labels: list[int] = []
        old_mode, new_mode = TRANSITION_ENDPOINTS[transition]
        for packet_id in packet_ids:
            projections, rows = role_bundle(inputs, model_id, packet_id)
            target_flag = TARGET_TO_FLAG[truth[packet_id]]
            old_detected = mode_detected(
                old_mode, rows, target_flag, cumulative
            )
            new_detected = mode_detected(
                new_mode, rows, target_flag, cumulative
            )
            examples.append(
                transition_features(
                    transition,
                    inputs["packet_projections"][packet_id],
                    projections,
                    gate_policy,
                )
            )
            improve_labels.append(int(new_detected and not old_detected))
            harm_labels.append(int(old_detected and not new_detected))
        feature_order = list(examples[0])
        improve_model = fit_binary_logistic(
            examples, improve_labels, feature_order, config["estimator"]
        )
        harm_model = fit_binary_logistic(
            examples, harm_labels, feature_order, config["estimator"]
        )
        models[transition] = {
            "feature_order": feature_order,
            "improvement_model": improve_model,
            "harm_model": harm_model,
        }
    return models


def transition_prediction(
    transition: str,
    transition_models: dict[str, Any],
    features: dict[str, float],
) -> dict[str, float]:
    models = transition_models[transition]
    improvement = predict_binary(models["improvement_model"], features)
    harm = predict_binary(models["harm_model"], features)
    return {
        "improvement_probability": improvement,
        "harm_probability": harm,
        "expected_detection_gain": improvement - harm,
    }


def transition_cost(transition: str, config: dict[str, Any]) -> float:
    costs = config["costs"]
    if transition in {"GM", "MB"}:
        value = float(costs["qualitative_methods"])
    elif transition in {"GD", "DB"}:
        value = float(costs["domain"])
    elif transition == "GB":
        value = (
            float(costs["qualitative_methods"])
            + float(costs["domain"])
            + float(costs["both_coordination"])
        )
    else:
        raise ValueError(f"unknown_transition:{transition}")
    if transition in {"MB", "DB"}:
        value += float(costs["both_coordination"])
    return value


def routing_score_tolerance(config: dict[str, Any]) -> float:
    tolerance = float(config.get("routing_precision", {}).get("score_tolerance", 0.0))
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("invalid_routing_score_tolerance")
    return tolerance


def select_transition(
    predictions: dict[str, dict[str, float]], config: dict[str, Any]
) -> tuple[str, list[str]]:
    order = {name: index for index, name in enumerate(config["transition_tie_order"])}
    if set(predictions) - set(order):
        raise ValueError("transition_tie_order_incomplete")
    scores = {name: float(row["net_value"]) for name, row in predictions.items()}
    if not all(math.isfinite(value) for value in scores.values()):
        raise ValueError("nonfinite_transition_score")
    best_score = max(scores.values())
    tolerance = routing_score_tolerance(config)
    tied = [
        name for name, value in scores.items() if best_score - value <= tolerance
    ]
    selected = min(tied, key=lambda name: order[name])
    return selected, sorted(tied, key=lambda name: order[name])


def should_acquire(score: float, threshold: float, config: dict[str, Any]) -> bool:
    if not math.isfinite(score) or not math.isfinite(threshold):
        raise ValueError("nonfinite_threshold_comparison")
    tolerance = routing_score_tolerance(config)
    tie_action = config.get("routing_precision", {}).get(
        "threshold_tie_action", "STOP"
    )
    if tie_action != "STOP":
        raise ValueError("unsupported_threshold_tie_action")
    return score > threshold + tolerance


def threshold_candidate_values(
    config: dict[str, Any], observed_net_values: Iterable[float]
) -> list[float]:
    selection = config["threshold_selection"]
    candidates = {float(value) for value in selection["candidates"]}
    strategy = selection.get("candidate_strategy", "declared_grid")
    if strategy == "declared_grid_plus_validation_score_breakpoints":
        tolerance = routing_score_tolerance(config)
        for score in observed_net_values:
            if not math.isfinite(score):
                raise ValueError("nonfinite_validation_transition_score")
            boundary = float(score) - tolerance
            candidates.add(boundary)
            candidates.add(math.nextafter(boundary, -math.inf))
            lower_step = max(4.0 * math.ulp(boundary), 1e-15)
            candidates.add(boundary - lower_step)
    elif strategy != "declared_grid":
        raise ValueError(f"unsupported_threshold_candidate_strategy:{strategy}")
    maximum = int(selection.get("maximum_candidate_count", 10000))
    if len(candidates) > maximum:
        raise ValueError("threshold_candidate_count_exceeded")
    return sorted(candidates)


def validation_transition_net_values(
    inputs: dict[str, Any],
    model_id: str,
    packet_ids: list[str],
    transition_models: dict[str, Any],
    config: dict[str, Any],
    gate_policy: dict[str, Any],
) -> list[float]:
    values: list[float] = []
    for packet_id in packet_ids:
        projections, _rows = role_bundle(inputs, model_id, packet_id)
        for transition in TRANSITIONS:
            features = transition_features(
                transition,
                inputs["packet_projections"][packet_id],
                projections,
                gate_policy,
            )
            prediction = transition_prediction(
                transition, transition_models, features
            )
            net_value = prediction["expected_detection_gain"] - float(
                config["costs"]["lambda"]
            ) * transition_cost(transition, config)
            values.append(net_value)
    return values


def route_packet(
    packet_id: str,
    model_id: str,
    packet_features: dict[str, float],
    projections: dict[str, dict[str, float]],
    transition_models: dict[str, Any],
    threshold: float,
    config: dict[str, Any],
    gate_policy: dict[str, Any],
) -> dict[str, Any]:
    """Apply a fitted policy. Truth is intentionally absent from this interface."""
    trace: list[dict[str, Any]] = []
    if projections["generalist"]["valid_generalist"] != 1.0:
        return {
            "packet_id": packet_id,
            "model_id": model_id,
            "route": "generalist",
            "selected_roles": ["generalist"],
            "acquired_specialists": [],
            "specialist_acquisitions": 0,
            "total_role_acquisitions": 1,
            "incremental_cost": 0.0,
            "total_role_cost": float(config["costs"].get("generalist", 0.0)),
            "retain_generalist_output": retain_generalist_output(config),
            "stop_reason": "policy_input_invalid",
            "trace": trace,
        }

    predictions: dict[str, dict[str, float]] = {}
    for transition in ("GM", "GD", "GB"):
        features = transition_features(transition, packet_features, projections, gate_policy)
        prediction = transition_prediction(transition, transition_models, features)
        prediction["incremental_cost"] = transition_cost(transition, config)
        prediction["net_value"] = prediction["expected_detection_gain"] - float(
            config["costs"]["lambda"]
        ) * prediction["incremental_cost"]
        predictions[transition] = prediction
    first, tied_transitions = select_transition(predictions, config)
    acquire_first = should_acquire(
        predictions[first]["net_value"], threshold, config
    )
    trace.append(
        {
            "step": 0,
            "observed_roles": ["generalist"],
            "available_transitions": predictions,
            "score_tolerance": routing_score_tolerance(config),
            "tied_transitions": tied_transitions,
            "decision": (
                {"GM": "ACQUIRE_M", "GD": "ACQUIRE_D", "GB": "ACQUIRE_BOTH"}[first]
                if acquire_first
                else "STOP_G"
            ),
        }
    )
    if not acquire_first:
        route = "generalist"
        acquired: list[str] = []
        stop_reason = "expected_gain_below_threshold"
    elif first == "GB":
        route = "both"
        acquired = ["qualitative_methods", "domain"]
        stop_reason = "both_specialists_acquired"
    else:
        first_role = "qualitative_methods" if first == "GM" else "domain"
        second_transition = "MB" if first == "GM" else "DB"
        second_role = "domain" if first == "GM" else "qualitative_methods"
        if projections[first_role]["valid_generalist"] != 1.0:
            route = first_role
            acquired = [first_role]
            stop_reason = "selected_observation_invalid"
            trace.append(
                {
                    "step": 1,
                    "observed_roles": ["generalist", first_role],
                    "available_transitions": {},
                    "decision": f"STOP_{'M' if first_role == 'qualitative_methods' else 'D'}",
                }
            )
        else:
            features = transition_features(
                second_transition, packet_features, projections, gate_policy
            )
            second_prediction = transition_prediction(
                second_transition, transition_models, features
            )
            second_prediction["incremental_cost"] = transition_cost(
                second_transition, config
            )
            second_prediction["net_value"] = second_prediction[
                "expected_detection_gain"
            ] - float(config["costs"]["lambda"]) * second_prediction["incremental_cost"]
            acquire_second = should_acquire(
                second_prediction["net_value"], threshold, config
            )
            trace.append(
                {
                    "step": 1,
                    "observed_roles": ["generalist", first_role],
                    "available_transitions": {second_transition: second_prediction},
                    "decision": (
                        f"ACQUIRE_{'D' if second_role == 'domain' else 'M'}_TO_B"
                        if acquire_second
                        else f"STOP_{'M' if first_role == 'qualitative_methods' else 'D'}"
                    ),
                }
            )
            if acquire_second:
                route = "both"
                acquired = [first_role, second_role]
                stop_reason = "both_specialists_acquired"
            else:
                route = first_role
                acquired = [first_role]
                stop_reason = "expected_gain_below_threshold"

    if len(acquired) > int(config["maximum_specialist_acquisitions"]):
        raise ValueError("specialist_budget_exceeded")
    selected_roles = list(
        roles_for_mode(route, retain_generalist_output(config))
    )
    incremental_cost = sum(
        float(config["costs"][role]) for role in acquired
    ) + (float(config["costs"]["both_coordination"]) if route == "both" else 0.0)
    total_role_cost = float(config["costs"].get("generalist", 0.0)) + incremental_cost
    return {
        "packet_id": packet_id,
        "model_id": model_id,
        "route": route,
        "selected_roles": selected_roles,
        "acquired_specialists": acquired,
        "specialist_acquisitions": len(acquired),
        "total_role_acquisitions": 1 + len(acquired),
        "incremental_cost": incremental_cost,
        "total_role_cost": total_role_cost,
        "retain_generalist_output": retain_generalist_output(config),
        "stop_reason": stop_reason,
        "trace": trace,
    }


def evaluate_routes_for_threshold(
    inputs: dict[str, Any],
    truth: dict[str, str],
    model_id: str,
    packet_ids: list[str],
    transition_models: dict[str, Any],
    threshold: float,
    config: dict[str, Any],
    gate_policy: dict[str, Any],
) -> dict[str, float]:
    detected = 0
    cost = 0.0
    total_role_acquisitions = 0
    total_role_cost = 0.0
    for packet_id in packet_ids:
        projections, rows = role_bundle(inputs, model_id, packet_id)
        route = route_packet(
            packet_id,
            model_id,
            inputs["packet_projections"][packet_id],
            projections,
            transition_models,
            threshold,
            config,
            gate_policy,
        )
        target_flag = TARGET_TO_FLAG[truth[packet_id]]
        detected += int(roles_detected(route["selected_roles"], rows, target_flag))
        cost += float(route["incremental_cost"])
        total_role_acquisitions += int(route["total_role_acquisitions"])
        total_role_cost += float(route["total_role_cost"])
    n = len(packet_ids)
    recall = detected / n
    mean_cost = cost / n
    mean_total_roles = total_role_acquisitions / n
    mean_total_role_cost = total_role_cost / n
    objective = recall - float(config["costs"]["lambda"]) * mean_cost
    return {
        "n": float(n),
        "tp": float(detected),
        "recall": recall,
        "mean_incremental_cost": mean_cost,
        "mean_total_role_acquisitions": mean_total_roles,
        "mean_total_role_cost": mean_total_role_cost,
        "objective": objective,
    }


def transition_validation_diagnostics(
    inputs: dict[str, Any],
    truth: dict[str, str],
    model_id: str,
    packet_ids: list[str],
    transition_models: dict[str, Any],
    gate_policy: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    cumulative = retain_generalist_output(config)
    for transition in TRANSITIONS:
        improve_probabilities: list[float] = []
        harm_probabilities: list[float] = []
        improve_labels: list[int] = []
        harm_labels: list[int] = []
        old_mode, new_mode = TRANSITION_ENDPOINTS[transition]
        for packet_id in packet_ids:
            projections, rows = role_bundle(inputs, model_id, packet_id)
            features = transition_features(
                transition,
                inputs["packet_projections"][packet_id],
                projections,
                gate_policy,
            )
            prediction = transition_prediction(transition, transition_models, features)
            target_flag = TARGET_TO_FLAG[truth[packet_id]]
            old_detected = mode_detected(
                old_mode, rows, target_flag, cumulative
            )
            new_detected = mode_detected(
                new_mode, rows, target_flag, cumulative
            )
            improve_probabilities.append(prediction["improvement_probability"])
            harm_probabilities.append(prediction["harm_probability"])
            improve_labels.append(int(new_detected and not old_detected))
            harm_labels.append(int(old_detected and not new_detected))
        diagnostics[transition] = {
            "n": len(packet_ids),
            "improvement_brier": brier_score(improve_probabilities, improve_labels),
            "harm_brier": brier_score(harm_probabilities, harm_labels),
            "improvement_positive_n": sum(improve_labels),
            "harm_positive_n": sum(harm_labels),
        }
    return diagnostics


def select_threshold_candidate(
    candidates: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    selection = config["threshold_selection"]
    objective = str(selection["objective"])
    if objective == "validation_mean_detection_minus_lambda_times_incremental_cost":
        return max(
            candidates,
            key=lambda row: (
                row["objective"],
                row["recall"],
                -row["mean_incremental_cost"],
                row["threshold"],
            ),
        )
    if objective == "maximum_validation_recall_subject_to_mean_total_role_acquisitions_budget":
        budget = float(selection["maximum_mean_total_role_acquisitions"])
        tolerance = float(selection.get("budget_tolerance", 1e-12))
        if not math.isfinite(budget) or budget < 1.0:
            raise ValueError("invalid_mean_total_role_acquisition_budget")
        feasible = [
            row
            for row in candidates
            if float(row["mean_total_role_acquisitions"]) <= budget + tolerance
        ]
        if not feasible:
            raise ValueError("no_threshold_candidate_satisfies_call_budget")
        return max(
            feasible,
            key=lambda row: (
                row["recall"],
                -row["mean_total_role_acquisitions"],
                -row["mean_incremental_cost"],
                row["threshold"],
            ),
        )
    raise ValueError(f"unsupported_threshold_selection_objective:{objective}")


def validate_policy_config(config: dict[str, Any]) -> None:
    routing_score_tolerance(config)
    if float(config["costs"]["lambda"]) < 0.0:
        raise ValueError("negative_cost_lambda")
    selection = config["threshold_selection"]
    candidates = [float(value) for value in selection["candidates"]]
    if not candidates or not all(math.isfinite(value) for value in candidates):
        raise ValueError("invalid_threshold_candidates")
    threshold_candidate_values(config, [])
    if selection["objective"] == (
        "maximum_validation_recall_subject_to_mean_total_role_acquisitions_budget"
    ):
        if max(candidates) < 1.0:
            raise ValueError("call_budget_requires_no_acquisition_fallback_threshold")
    composition = config.get("output_composition", {})
    if composition.get("retain_generalist_output") is True and composition.get(
        "combination"
    ) != "cumulative_flag_union":
        raise ValueError("invalid_generalist_retention_composition")


def fit_policy_artifact(
    inputs: dict[str, Any],
    training_truth: dict[str, str],
    split: dict[str, list[str]],
    config: dict[str, Any],
    gate_policy: dict[str, Any],
    config_path: Path,
    gate_policy_path: Path,
) -> dict[str, Any]:
    validate_policy_config(config)
    model_policies: dict[str, Any] = {}
    for model_id in inputs["models"]:
        training_models = fit_transition_models(
            inputs, training_truth, model_id, split["train"], gate_policy, config
        )
        candidates: list[dict[str, Any]] = []
        validation_scores = validation_transition_net_values(
            inputs,
            model_id,
            split["validation"],
            training_models,
            config,
            gate_policy,
        )
        threshold_values = threshold_candidate_values(config, validation_scores)
        for threshold in threshold_values:
            metrics = evaluate_routes_for_threshold(
                inputs,
                training_truth,
                model_id,
                split["validation"],
                training_models,
                float(threshold),
                config,
                gate_policy,
            )
            candidates.append({"threshold": float(threshold), **metrics})
        selected = select_threshold_candidate(candidates, config)
        final_training_ids = sorted(split["train"] + split["validation"])
        final_models = fit_transition_models(
            inputs, training_truth, model_id, final_training_ids, gate_policy, config
        )
        model_policies[model_id] = {
            "selected_threshold": selected["threshold"],
            "threshold_candidate_strategy": config["threshold_selection"].get(
                "candidate_strategy", "declared_grid"
            ),
            "threshold_candidate_count": len(candidates),
            "threshold_candidates": candidates,
            "selection_models_validation_diagnostics": transition_validation_diagnostics(
                inputs,
                training_truth,
                model_id,
                split["validation"],
                training_models,
                gate_policy,
                config,
            ),
            "final_transition_models": final_models,
            "final_training_n": len(final_training_ids),
        }
    return {
        "artifact_schema_version": config.get(
            "fitted_policy_schema_version", "working-warrantloop-fitted-policy-v0"
        ),
        "created_at_utc": now_utc(),
        "policy_id": config["policy_id"],
        "status": config["status"],
        "router_name": config["router_name"],
        "paper_facing_name": config["paper_facing_name"],
        "config_sha256": sha256_file(config_path),
        "warrantgate_policy_sha256": sha256_file(gate_policy_path),
        "implementation_sha256": sha256_file(SCRIPT),
        "development_input_hashes": inputs["input_hashes"],
        "split_counts": {name: len(ids) for name, ids in split.items()},
        "feature_order": {
            "initial": list(INITIAL_FEATURE_ORDER),
            "after_qualitative_methods": [
                *INITIAL_FEATURE_ORDER,
                *(f"qualitative_methods_{name}" for name in RATING_FEATURE_ORDER),
            ],
            "after_domain": [
                *INITIAL_FEATURE_ORDER,
                *(f"domain_{name}" for name in RATING_FEATURE_ORDER),
            ],
        },
        "costs": config["costs"],
        "output_composition": config.get(
            "output_composition",
            {"retain_generalist_output": False, "combination": "selected_role_union"},
        ),
        "routing_precision": config.get(
            "routing_precision",
            {"score_tolerance": 0.0, "threshold_tie_action": "STOP"},
        ),
        "threshold_selection_contract": config["threshold_selection"],
        "maximum_specialist_acquisitions": config["maximum_specialist_acquisitions"],
        "model_policies": model_policies,
        "contains_source_text": False,
        "contains_free_form_rationale": False,
        "contains_item_truth": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }


def forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_ROUTE_KEYS:
                found.add(str(key))
            found.update(forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(forbidden_keys(child))
    return found


def all_estimators_converged(fitted_policy: dict[str, Any]) -> bool:
    for model_policy in fitted_policy["model_policies"].values():
        for transition in model_policy["final_transition_models"].values():
            for key in ("improvement_model", "harm_model"):
                estimator = transition[key]
                if estimator["kind"] == "logistic" and estimator.get("converged") is not True:
                    return False
                if estimator["kind"] not in {"logistic", "constant"}:
                    return False
    return True


def apply_policy(
    packet_projections: dict[str, dict[str, float]],
    role_projections: dict[tuple[str, str, str], dict[str, float]],
    model_ids: list[str],
    packet_ids: list[str],
    fitted_policy: dict[str, Any],
    fitted_policy_sha256: str,
    config: dict[str, Any],
    gate_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_id in model_ids:
        model_policy = fitted_policy["model_policies"][model_id]
        for packet_id in packet_ids:
            projections = {
                role: role_projections[(model_id, role, packet_id)] for role in ROLES
            }
            route = route_packet(
                packet_id,
                model_id,
                packet_projections[packet_id],
                projections,
                model_policy["final_transition_models"],
                float(model_policy["selected_threshold"]),
                config,
                gate_policy,
            )
            route.update(
                {
                    "route_record_schema_version": config.get(
                        "route_record_schema_version", "working-warrantloop-route-v0"
                    ),
                    "created_at_utc": now_utc(),
                    "policy_id": fitted_policy["policy_id"],
                    "router_name": fitted_policy["router_name"],
                    "paper_facing_name": fitted_policy["paper_facing_name"],
                    "fitted_policy_sha256": fitted_policy_sha256,
                    "uses_source_text": False,
                    "uses_free_form_rationale": False,
                    "uses_known_intended_flaw_type": False,
                    "uses_acquired_specialist_projection": True,
                    "manuscript_eligible": False,
                }
            )
            leaked = forbidden_keys(route)
            if leaked:
                raise ValueError(f"forbidden_route_keys:{sorted(leaked)}")
            rows.append(route)
    return rows


def wilson_interval(tp: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (math.nan, math.nan)
    proportion = tp / n
    denominator = 1.0 + z * z / n
    center = (proportion + z * z / (2.0 * n)) / denominator
    half = z * math.sqrt(proportion * (1.0 - proportion) / n + z * z / (4.0 * n * n))
    half /= denominator
    return max(0.0, center - half), min(1.0, center + half)


def score_routes(
    route_rows: list[dict[str, Any]],
    inputs: dict[str, Any],
    truth: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    detail: list[dict[str, Any]] = []
    for route in route_rows:
        model_id = str(route["model_id"])
        packet_id = str(route["packet_id"])
        _projections, rows = role_bundle(inputs, model_id, packet_id)
        flaw = truth[packet_id]
        target_flag = TARGET_TO_FLAG[flaw]
        detail.append(
            {
                "model_id": model_id,
                "packet_id": packet_id,
                "target_flaw": flaw,
                "route": route["route"],
                "detected": roles_detected(
                    [str(role) for role in route["selected_roles"]], rows, target_flag
                ),
                "specialist_acquisitions": route["specialist_acquisitions"],
                "total_role_acquisitions": route["total_role_acquisitions"],
                "incremental_cost": route["incremental_cost"],
                "total_role_cost": route["total_role_cost"],
                "stop_reason": route["stop_reason"],
                "private_working_score": True,
                "manuscript_eligible": False,
            }
        )
    aggregates: list[dict[str, Any]] = []
    paper_names = {str(row.get("paper_facing_name", "WarrantRoute-S")) for row in route_rows}
    router_names = {str(row.get("router_name", "WarrantLoop")) for row in route_rows}
    if len(paper_names) != 1 or len(router_names) != 1:
        raise ValueError("mixed_router_identity_in_score_batch")
    paper_name = next(iter(paper_names))
    router_name = next(iter(router_names))
    for model_id in sorted({str(row["model_id"]) for row in detail}):
        selected = [row for row in detail if row["model_id"] == model_id]
        tp = sum(bool(row["detected"]) for row in selected)
        n = len(selected)
        lower, upper = wilson_interval(tp, n)
        route_counts = Counter(str(row["route"]) for row in selected)
        stop_counts = Counter(str(row["stop_reason"]) for row in selected)
        aggregates.append(
            {
                "method": router_name,
                "paper_facing_name": paper_name,
                "model_id": model_id,
                "tp": tp,
                "n": n,
                "recall": tp / n if n else None,
                "recall_wilson_95_low": lower,
                "recall_wilson_95_high": upper,
                "mean_specialist_acquisitions": statistics.fmean(
                    float(row["specialist_acquisitions"]) for row in selected
                ),
                "mean_total_role_acquisitions": statistics.fmean(
                    float(row["total_role_acquisitions"]) for row in selected
                ),
                "mean_incremental_cost": statistics.fmean(
                    float(row["incremental_cost"]) for row in selected
                ),
                "mean_total_role_cost": statistics.fmean(
                    float(row["total_role_cost"]) for row in selected
                ),
                "route_counts": json.dumps(dict(sorted(route_counts.items())), sort_keys=True),
                "stop_reason_counts": json.dumps(
                    dict(sorted(stop_counts.items())), sort_keys=True
                ),
                "result_label": "private_personal_exploratory_not_for_publication",
                "manuscript_eligible": False,
            }
        )
    return detail, aggregates


def preflight_report(inputs: dict[str, Any], split: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "status": "ready_for_development_smoke",
        "corpus_id": inputs["corpus_id"],
        "packet_count": len(inputs["packet_ids"]),
        "model_count": len(inputs["models"]),
        "models": inputs["models"],
        "role_count": len(ROLES),
        "role_projection_count": len(inputs["role_rows"]),
        "invalid_by_role": inputs["invalid_by_role"],
        "split_counts": {name: len(ids) for name, ids in split.items()},
        "source_groups_disjoint": True,
        "new_llm_calls_required": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }


def command_preflight(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    inputs = load_working_inputs(
        args.run_root, args.packet_set, config, require_development_lane=True
    )
    if len(inputs["packet_ids"]) < int(config["development"]["minimum_total_packets"]):
        raise ValueError("minimum_total_packets_not_met")
    split = deterministic_split(inputs["packet_ids"], config)
    verify_group_disjoint(split, inputs["source_groups"])
    fitting_ids = set(split["train"] + split["validation"])
    training_truth = load_truth_subset(inputs["truth_path"], fitting_ids)
    minimum = int(config["development"]["minimum_train_packets_per_flaw"])
    train_counts = Counter(training_truth[packet_id] for packet_id in split["train"])
    if any(train_counts[flaw] < minimum for flaw in TARGET_TO_FLAG):
        raise ValueError(f"minimum_train_cell_not_met:{dict(train_counts)}")
    print(json.dumps(preflight_report(inputs, split), indent=2, sort_keys=True))
    return 0


def command_smoke(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    gate_policy = load_json(args.gate_policy)
    if config.get("formal_run_enabled") is not False or config.get("manuscript_eligible") is not False:
        raise ValueError("working_config_must_fail_closed")
    inputs = load_working_inputs(
        args.run_root, args.packet_set, config, require_development_lane=True
    )
    if len(inputs["packet_ids"]) < int(config["development"]["minimum_total_packets"]):
        raise ValueError("minimum_total_packets_not_met")
    split = deterministic_split(inputs["packet_ids"], config)
    verify_group_disjoint(split, inputs["source_groups"])
    expected_smoke = int(config["development"]["smoke_test_packets"])
    if len(split["smoke_test"]) != expected_smoke:
        raise ValueError(f"unexpected_smoke_size:{len(split['smoke_test'])}:{expected_smoke}")

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_ROOT
        / f"smoke_{expected_smoke}_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    if not output_dir.resolve().is_relative_to(DEFAULT_OUTPUT_ROOT.resolve()):
        raise ValueError(f"output_outside_personal_local_root:{output_dir}")
    require_new_output_dir(output_dir)
    split_manifest = {
        "schema_version": "working-warrantloop-split-v0",
        "created_at_utc": now_utc(),
        "split_seed": config["development"]["split_seed"],
        "split_by": config["development"]["split_by"],
        "source_groups_disjoint": True,
        "partitions": split,
        "counts": {name: len(ids) for name, ids in split.items()},
        "contains_source_text": False,
        "contains_item_truth": False,
        "manuscript_eligible": False,
    }
    split_path = output_dir / "split_manifest.json"
    write_json(split_path, split_manifest)

    fitting_ids = set(split["train"] + split["validation"])
    training_truth = load_truth_subset(inputs["truth_path"], fitting_ids)
    minimum = int(config["development"]["minimum_train_packets_per_flaw"])
    train_counts = Counter(training_truth[packet_id] for packet_id in split["train"])
    if any(train_counts[flaw] < minimum for flaw in TARGET_TO_FLAG):
        raise ValueError(f"minimum_train_cell_not_met:{dict(train_counts)}")
    fitted_policy = fit_policy_artifact(
        inputs, training_truth, split, config, gate_policy, args.config, args.gate_policy
    )
    policy_path = output_dir / "fitted_policy.json"
    write_json(policy_path, fitted_policy)
    policy_hash = sha256_file(policy_path)

    # Route application receives projected observations and a fitted policy, not truth.
    if "truth" in inspect.signature(route_packet).parameters or "truth" in inspect.signature(
        apply_policy
    ).parameters:
        raise RuntimeError("route_application_interface_accepts_truth")
    route_rows = apply_policy(
        inputs["packet_projections"],
        inputs["role_projections"],
        inputs["models"],
        split["smoke_test"],
        fitted_policy,
        policy_hash,
        config,
        gate_policy,
    )
    route_path = output_dir / "routes.jsonl"
    write_jsonl(route_path, route_rows)
    route_hash = sha256_file(route_path)

    # The private answer sheet is used only after the complete route file exists.
    smoke_truth = load_truth_subset(inputs["truth_path"], set(split["smoke_test"]))
    detail, aggregates = score_routes(route_rows, inputs, smoke_truth)
    detail_path = output_dir / "scores.private.csv"
    aggregate_path = output_dir / "metrics.csv"
    write_csv(detail_path, detail)
    write_csv(aggregate_path, aggregates)

    expected_routes = expected_smoke * len(inputs["models"])
    checks = {
        "policy_file_exists_before_routes": policy_path.is_file(),
        "all_estimators_converged_or_constant": all_estimators_converged(fitted_policy),
        "route_count_matches": len(route_rows) == expected_routes,
        "score_count_matches": len(detail) == expected_routes,
        "all_routes_terminate": all(row["stop_reason"] for row in route_rows),
        "specialist_budget_respected": all(
            int(row["specialist_acquisitions"])
            <= int(config["maximum_specialist_acquisitions"])
            for row in route_rows
        ),
        "no_forbidden_route_keys": not any(forbidden_keys(row) for row in route_rows),
        "route_application_has_no_truth_argument": "truth"
        not in inspect.signature(route_packet).parameters
        and "truth" not in inspect.signature(apply_policy).parameters,
        "new_llm_calls_made": False,
        "source_groups_disjoint": True,
        "output_under_personal_local_root": output_dir.resolve().is_relative_to(
            DEFAULT_OUTPUT_ROOT.resolve()
        ),
    }
    status = "validated_smoke_complete" if all(
        value is True for key, value in checks.items() if key != "new_llm_calls_made"
    ) and checks["new_llm_calls_made"] is False else "smoke_failed"
    manifest = {
        "manifest_schema_version": "working-warrantloop-smoke-manifest-v0",
        "created_at_utc": now_utc(),
        "status": status,
        "result_label": "private_personal_exploratory_not_for_publication",
        "policy_id": config["policy_id"],
        "execution_contract": str(
            RQ2_ROOT / "protocol" / "working_warrantloop_v0_execution_contract.md"
        ),
        "run_root": str(args.run_root),
        "packet_set": args.packet_set,
        "preflight": preflight_report(inputs, split),
        "checks": checks,
        "artifacts": {
            "split_manifest": {"path": str(split_path), "sha256": sha256_file(split_path)},
            "fitted_policy": {"path": str(policy_path), "sha256": policy_hash},
            "routes": {"path": str(route_path), "sha256": route_hash},
            "private_scores": {
                "path": str(detail_path),
                "sha256": sha256_file(detail_path),
            },
            "metrics": {
                "path": str(aggregate_path),
                "sha256": sha256_file(aggregate_path),
            },
        },
        "route_count": len(route_rows),
        "private_score_count": len(detail),
        "metric_row_count": len(aggregates),
        "contains_source_text": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "packet_count": expected_smoke,
                "model_count": len(inputs["models"]),
                "route_count": len(route_rows),
                "metric_row_count": len(aggregates),
                "new_llm_calls_made": False,
                "formal_run_enabled": False,
                "manuscript_eligible": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "validated_smoke_complete" else 2


def command_formal_run(args: argparse.Namespace) -> int:
    del args
    raise RuntimeError(
        "formal_run_blocked:working contract is not a successor study freeze"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--gate-policy", type=Path, default=DEFAULT_GATE_POLICY)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "smoke"):
        child = subparsers.add_parser(name)
        child.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
        child.add_argument("--packet-set", default="balanced_n100")
        if name == "smoke":
            child.add_argument("--output-dir", type=Path, default=None)
    subparsers.add_parser("formal-run")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "preflight":
            return command_preflight(args)
        if args.command == "smoke":
            return command_smoke(args)
        if args.command == "formal-run":
            return command_formal_run(args)
        raise RuntimeError(f"unknown_command:{args.command}")
    except Exception as exc:
        print(f"WarrantLoop {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
