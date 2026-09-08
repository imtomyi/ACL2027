#!/usr/bin/env python3
"""Add a leakage-controlled residual flaw detector to frozen WarrantRoute routes."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import run_working_warrantloop as core
import run_working_warrantloop_multicorpus as multicorpus
import run_working_warrantroute_cascade as cumulative


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
DEFAULT_CONFIG = RQ2_ROOT / "config" / "working_warrantroute_residual_discovery_v1.json"
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE / "Storage" / "rq2_personal_local_diagnostic" / "warrantloop_working"
)
WORD_RE = re.compile(r"[a-z0-9]+")
SAFE_TEXT_FIELDS = (
    "llm_generated_qualitative_claim.claim",
    "llm_generated_qualitative_claim.explanation",
    "llm_generated_qualitative_claim.boundary_conditions",
    "llm_generated_qualitative_claim.theme_name",
    "source_text_context.text",
    "source_text_context.local_context",
)


def resolve_workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE / path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_packet_map(path: Path) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        packet_id = str(row.get("packet_id", ""))
        if not packet_id or packet_id in packets:
            raise ValueError(f"duplicate_or_missing_packet_id:{packet_id}")
        packets[packet_id] = row
    if not packets:
        raise ValueError(f"empty_packet_file:{path}")
    return packets


def validate_config(config: dict[str, Any]) -> None:
    if any(
        config.get(key) is not False
        for key in ("new_llm_calls_allowed", "formal_run_enabled", "manuscript_eligible")
    ):
        raise ValueError("residual_working_replay_must_fail_closed")
    classifier = config["classifier"]
    if classifier.get("kind") != "hashed_bernoulli_naive_bayes":
        raise ValueError("unsupported_residual_classifier")
    if int(classifier.get("feature_dimension", 0)) < 64:
        raise ValueError("residual_feature_dimension_too_small")
    if float(classifier.get("alpha", 0.0)) <= 0.0:
        raise ValueError("residual_alpha_must_be_positive")
    if tuple(classifier.get("safe_text_fields", ())) != SAFE_TEXT_FIELDS:
        raise ValueError("residual_safe_text_field_contract_drift")
    residual = config["residual_policy"]
    rate = float(residual.get("maximum_addition_rate", -1.0))
    if not 0.0 <= rate <= 1.0:
        raise ValueError("invalid_residual_addition_rate")
    if residual.get("threshold_tie_action") != "do_not_add":
        raise ValueError("residual_threshold_tie_must_fail_closed")


def safe_text_segments(packet: dict[str, Any]) -> list[tuple[str, str]]:
    """Project only predeclared source/claim text fields; never project answer fields."""
    segments: list[tuple[str, str]] = []
    claim = packet.get("llm_generated_qualitative_claim")
    if isinstance(claim, dict):
        for key in ("claim", "explanation", "theme_name"):
            value = claim.get(key)
            if isinstance(value, str) and value.strip():
                segments.append((f"claim_{key}", value))
        boundaries = claim.get("boundary_conditions")
        if isinstance(boundaries, list):
            for value in boundaries:
                if isinstance(value, str) and value.strip():
                    segments.append(("claim_boundary", value))
    contexts = packet.get("source_text_context")
    if isinstance(contexts, list):
        for context in contexts:
            if not isinstance(context, dict):
                continue
            for key in ("text", "local_context"):
                value = context.get(key)
                if isinstance(value, str) and value.strip():
                    segments.append((f"source_{key}", value))
    return segments


def feature_strings(packet: dict[str, Any]) -> set[str]:
    segments = safe_text_segments(packet)
    features: set[str] = set()
    total_tokens = 0
    for field, value in segments:
        tokens = WORD_RE.findall(value.lower())
        total_tokens += len(tokens)
        features.update(f"{field}:u:{token}" for token in tokens)
        features.update(
            f"{field}:b:{left}_{right}" for left, right in zip(tokens, tokens[1:])
        )
    context_count = sum(1 for field, _value in segments if field.startswith("source_"))
    features.add(f"shape:segments:{min(len(segments), 20)}")
    features.add(f"shape:contexts:{min(context_count, 20)}")
    features.add(f"shape:tokens20:{min(total_tokens // 20, 50)}")
    return features


def hashed_features(packet: dict[str, Any], classifier: dict[str, Any]) -> frozenset[int]:
    dimension = int(classifier["feature_dimension"])
    salt = str(classifier["hash_salt"])
    buckets = {
        int.from_bytes(
            hashlib.sha256(f"{salt}\x1f{feature}".encode("utf-8")).digest()[:8],
            "big",
        )
        % dimension
        for feature in feature_strings(packet)
    }
    return frozenset(buckets)


def fit_hashed_bernoulli_nb(
    packets: dict[str, dict[str, Any]],
    truth: dict[str, str],
    training_ids: Iterable[str],
    classifier: dict[str, Any],
) -> dict[str, Any]:
    ids = sorted(set(training_ids))
    if not ids:
        raise ValueError("empty_residual_training_set")
    classes = sorted(core.TARGET_TO_FLAG)
    dimension = int(classifier["feature_dimension"])
    alpha = float(classifier["alpha"])
    class_counts = Counter(truth[packet_id] for packet_id in ids)
    if set(class_counts) != set(classes):
        raise ValueError(f"residual_training_missing_class:{dict(class_counts)}")
    document_frequencies = {label: [0] * dimension for label in classes}
    for packet_id in ids:
        label = truth[packet_id]
        for bucket in hashed_features(packets[packet_id], classifier):
            document_frequencies[label][bucket] += 1

    log_bases: dict[str, float] = {}
    log_odds_deltas: dict[str, list[float]] = {}
    total = len(ids)
    for label in classes:
        label_n = class_counts[label]
        prior = (label_n + alpha) / (total + alpha * len(classes))
        base = math.log(prior)
        deltas: list[float] = []
        for count in document_frequencies[label]:
            probability = (count + alpha) / (label_n + 2.0 * alpha)
            base += math.log1p(-probability)
            deltas.append(math.log(probability) - math.log1p(-probability))
        log_bases[label] = base
        log_odds_deltas[label] = deltas
    return {
        "classifier_schema_version": "hashed-bernoulli-naive-bayes-v1",
        "kind": "hashed_bernoulli_naive_bayes",
        "class_labels": classes,
        "class_document_counts": dict(sorted(class_counts.items())),
        "training_document_count": total,
        "training_inventory_sha256": core.sha256_bytes(
            "\n".join(ids).encode("utf-8")
        ),
        "feature_dimension": dimension,
        "alpha": alpha,
        "hash_salt": str(classifier["hash_salt"]),
        "feature_projection": "safe_source_and_claim_text_only",
        "class_log_score_bases": log_bases,
        "class_log_odds_deltas": log_odds_deltas,
        "stores_source_text_or_vocabulary": False,
    }


def predict_hashed_bernoulli_nb(
    model: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    classifier = {
        "feature_dimension": model["feature_dimension"],
        "hash_salt": model["hash_salt"],
    }
    active = hashed_features(packet, classifier)
    scores = {
        label: float(model["class_log_score_bases"][label])
        + sum(float(model["class_log_odds_deltas"][label][bucket]) for bucket in active)
        for label in model["class_labels"]
    }
    best = max(sorted(scores), key=lambda label: scores[label])
    maximum = max(scores.values())
    denominator = sum(math.exp(score - maximum) for score in scores.values())
    probabilities = {
        label: math.exp(score - maximum) / denominator for label, score in scores.items()
    }
    return {
        "predicted_flaw_type": best,
        "predicted_flag": core.TARGET_TO_FLAG[best],
        "probability": probabilities[best],
        "posterior": probabilities,
    }


def packet_predictions(
    model: dict[str, Any], packets: dict[str, dict[str, Any]], packet_ids: Iterable[str]
) -> dict[str, dict[str, Any]]:
    return {
        packet_id: predict_hashed_bernoulli_nb(model, packets[packet_id])
        for packet_id in sorted(set(packet_ids))
    }


def normalized_shortcut_value(packet: dict[str, Any], field: str) -> str:
    claim = packet.get("llm_generated_qualitative_claim")
    if not isinstance(claim, dict):
        return ""
    key = field.rsplit(".", maxsplit=1)[-1]
    value = claim.get(key)
    if isinstance(value, list):
        text = "\n".join(str(item) for item in value)
    elif isinstance(value, str):
        text = value
    else:
        text = ""
    return " ".join(WORD_RE.findall(text.lower()))


def audit_deterministic_shortcuts(
    packets: dict[str, dict[str, Any]],
    truth: dict[str, str],
    config: dict[str, Any],
) -> dict[str, Any]:
    quarantine = config["shortcut_quarantine"]
    purity_threshold = float(quarantine["deterministic_purity_threshold"])
    unique_limit = max(
        int(quarantine["maximum_unique_value_floor"]),
        int(math.floor(len(packets) * float(quarantine["maximum_unique_value_fraction"]))),
    )
    field_rows: list[dict[str, Any]] = []
    for field in quarantine["audit_fields"]:
        value_labels: dict[str, Counter[str]] = defaultdict(Counter)
        empty_count = 0
        for packet_id, packet in packets.items():
            value = normalized_shortcut_value(packet, str(field))
            if not value:
                empty_count += 1
            digest = core.sha256_bytes(value.encode("utf-8"))
            value_labels[digest][truth[packet_id]] += 1
        majority_correct = sum(max(counts.values()) for counts in value_labels.values())
        purity = majority_correct / len(packets)
        unique_count = len(value_labels)
        detected = purity >= purity_threshold and unique_count <= unique_limit
        field_rows.append(
            {
                "field": field,
                "n": len(packets),
                "empty_count": empty_count,
                "unique_value_count": unique_count,
                "unique_value_fraction": unique_count / len(packets),
                "label_prediction_purity_from_exact_value": purity,
                "deterministic_shortcut_detected": detected,
                "raw_values_stored": False,
            }
        )
    detected_fields = [
        str(row["field"])
        for row in field_rows
        if row["deterministic_shortcut_detected"]
    ]
    return {
        "audit_schema_version": "working-warrantroute-shortcut-quarantine-v1",
        "development_packet_count": len(packets),
        "deterministic_purity_threshold": purity_threshold,
        "unique_value_count_limit": unique_limit,
        "fields": field_rows,
        "deterministic_shortcut_fields": detected_fields,
        "deterministic_shortcut_detected": bool(detected_fields),
        "scientific_interpretation_gate_passed": not detected_fields,
        "action": (
            "quarantine_working_result_and_require_independently_generated_claims"
            if detected_fields
            else "no_exact_value_shortcut_detected"
        ),
        "manuscript_eligible": False,
    }


def classifier_artifact_is_safe(classifier: dict[str, Any]) -> bool:
    if classifier.get("stores_source_text_or_vocabulary") is not False:
        return False
    dimension = int(classifier.get("feature_dimension", -1))
    labels = classifier.get("class_labels")
    deltas = classifier.get("class_log_odds_deltas")
    if not isinstance(labels, list) or not isinstance(deltas, dict):
        return False
    if set(labels) != set(core.TARGET_TO_FLAG) or set(deltas) != set(labels):
        return False
    return all(
        isinstance(values, list)
        and len(values) == dimension
        and all(isinstance(value, (int, float)) for value in values)
        for values in deltas.values()
    )


def fitted_policy_artifacts_are_safe(
    oof_policy_index: list[dict[str, Any]], transfer_policy_artifact: dict[str, Any]
) -> bool:
    paths = [Path(str(row["path"])) for row in oof_policy_index]
    paths.append(Path(str(transfer_policy_artifact["path"])))
    return all(
        classifier_artifact_is_safe(core.load_json(path)["classifier"])
        for path in paths
    )


def selected_flags(route: dict[str, Any], inputs: dict[str, Any]) -> set[str]:
    model_id = str(route["model_id"])
    packet_id = str(route["packet_id"])
    flags: set[str] = set()
    for role in route["selected_roles"]:
        flags.update(
            core.normalized_flags(inputs["role_rows"][(model_id, str(role), packet_id)])
        )
    return flags


def residual_budget_count(route_count: int, maximum_rate: float) -> int:
    return int(math.floor(route_count * maximum_rate + 1e-12))


def select_residual_keys(
    routes: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
    threshold: float,
    residual_policy: dict[str, Any],
    tie_seed: str,
) -> set[tuple[str, str]]:
    tolerance = float(residual_policy.get("score_tolerance", 1e-12))
    maximum = residual_budget_count(
        len(routes), float(residual_policy["maximum_addition_rate"])
    )
    eligible: list[tuple[float, str, str]] = []
    for route in routes:
        packet_id = str(route["packet_id"])
        model_id = str(route["model_id"])
        prediction = predictions[packet_id]
        if float(prediction["probability"]) <= threshold + tolerance:
            continue
        if str(prediction["predicted_flag"]) in selected_flags(route, inputs):
            continue
        tie = core.stable_digest(tie_seed, model_id, packet_id)
        eligible.append((-float(prediction["probability"]), tie, packet_id))
    eligible.sort()
    return {
        (str(routes[0]["model_id"]), packet_id)
        for _negative_probability, _tie, packet_id in eligible[:maximum]
    } if routes else set()


def threshold_candidates(
    routes: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
    tolerance: float,
) -> list[float]:
    probabilities = {
        float(predictions[str(route["packet_id"])]["probability"])
        for route in routes
        if str(predictions[str(route["packet_id"])]["predicted_flag"])
        not in selected_flags(route, inputs)
    }
    return sorted({-2.0 * tolerance, 1.0, *probabilities})


def detected_with_residual(
    route: dict[str, Any],
    inputs: dict[str, Any],
    truth: dict[str, str],
    prediction: dict[str, Any],
    add_residual: bool,
) -> tuple[bool, bool]:
    packet_id = str(route["packet_id"])
    target_flag = core.TARGET_TO_FLAG[truth[packet_id]]
    before = target_flag in selected_flags(route, inputs)
    after = before or (
        add_residual and str(prediction["predicted_flag"]) == target_flag
    )
    return before, after


def select_threshold(
    routes: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
    validation_truth: dict[str, str],
    residual_policy: dict[str, Any],
    tie_seed: str,
) -> tuple[float, list[dict[str, Any]]]:
    tolerance = float(residual_policy.get("score_tolerance", 1e-12))
    diagnostics: list[dict[str, Any]] = []
    for threshold in threshold_candidates(routes, predictions, inputs, tolerance):
        selected = select_residual_keys(
            routes, predictions, inputs, threshold, residual_policy, tie_seed
        )
        before_tp = 0
        final_tp = 0
        for route in routes:
            key = (str(route["model_id"]), str(route["packet_id"]))
            before, after = detected_with_residual(
                route,
                inputs,
                validation_truth,
                predictions[str(route["packet_id"])],
                key in selected,
            )
            before_tp += int(before)
            final_tp += int(after)
        diagnostics.append(
            {
                "threshold": threshold,
                "validation_n": len(routes),
                "validation_tp_before": before_tp,
                "validation_tp_after": final_tp,
                "validation_tp_recovered": final_tp - before_tp,
                "residual_additions": len(selected),
                "maximum_residual_additions": residual_budget_count(
                    len(routes), float(residual_policy["maximum_addition_rate"])
                ),
            }
        )
    winner = max(
        diagnostics,
        key=lambda row: (
            int(row["validation_tp_after"]),
            -int(row["residual_additions"]),
            float(row["threshold"]),
        ),
    )
    return float(winner["threshold"]), diagnostics


def make_residual_route(
    source: dict[str, Any],
    prediction: dict[str, Any],
    add_residual: bool,
    threshold: float,
    fitted_policy_hash: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    row = dict(source)
    row.update(
        {
            "route_record_schema_version": "working-warrantroute-residual-route-v1",
            "source_policy_id": source["policy_id"],
            "source_fitted_policy_sha256": source.get("fitted_policy_sha256"),
            "policy_id": config["experiment_id"],
            "router_name": config["router_name"],
            "paper_facing_name": config["paper_facing_name"],
            "internal_variant_id": config["internal_variant_id"],
            "fitted_residual_policy_sha256": fitted_policy_hash,
            "residual_candidate_flag": prediction["predicted_flag"],
            "residual_candidate_probability": prediction["probability"],
            "residual_threshold": threshold,
            "residual_added": bool(add_residual),
            "residual_additions": int(add_residual),
            "residual_classifier_calls": 1,
            "residual_decision_basis": "threshold_plus_batch_budget_without_evaluation_truth",
            "uses_source_text": True,
            "uses_source_text_classifier": True,
            "uses_known_intended_flaw_type": False,
            "new_llm_call": False,
            "created_at_utc": core.now_utc(),
            "manuscript_eligible": False,
        }
    )
    leaked = core.forbidden_keys(row)
    if leaked:
        raise ValueError(f"forbidden_residual_route_keys:{sorted(leaked)}")
    return row


def apply_residual_batch(
    routes: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
    threshold: float,
    fitted_policy_hash: str,
    config: dict[str, Any],
    tie_scope: str,
) -> list[dict[str, Any]]:
    if not routes:
        return []
    model_ids = {str(route["model_id"]) for route in routes}
    if len(model_ids) != 1:
        raise ValueError("residual_batch_mixes_models")
    selected = select_residual_keys(
        routes,
        predictions,
        inputs,
        threshold,
        config["residual_policy"],
        f"{config['batch_tie_seed']}:{tie_scope}",
    )
    return [
        make_residual_route(
            route,
            predictions[str(route["packet_id"])],
            (str(route["model_id"]), str(route["packet_id"])) in selected,
            threshold,
            fitted_policy_hash,
            config,
        )
        for route in routes
    ]


def excluded_source_groups(
    packet_ids: Iterable[str], packets: dict[str, dict[str, Any]]
) -> set[str]:
    groups: set[str] = set()
    for packet_id in packet_ids:
        groups.update(core.source_groups(packets[packet_id]))
    return groups


def training_ids_without_sources(
    packets: dict[str, dict[str, Any]], excluded_groups: set[str]
) -> list[str]:
    return sorted(
        packet_id
        for packet_id, packet in packets.items()
        if not (set(core.source_groups(packet)) & excluded_groups)
    )


def fit_dreaddit_oof(
    source_routes: list[dict[str, Any]],
    inputs: dict[str, Any],
    sample_packets: dict[str, dict[str, Any]],
    full_packets: dict[str, dict[str, Any]],
    full_truth: dict[str, str],
    sample_truth: dict[str, str],
    config: dict[str, Any],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    routes_by_fold: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for route in source_routes:
        fold = route.get("outer_fold")
        if not isinstance(fold, int):
            raise ValueError("dreaddit_route_missing_outer_fold")
        routes_by_fold[fold].append(route)
    all_sample_ids = set(sample_packets)
    policies_dir = output_dir / "policies"
    core.secure_mkdir(policies_dir)
    final_routes: list[dict[str, Any]] = []
    oof_predictions: dict[str, dict[str, Any]] = {}
    policy_index: list[dict[str, Any]] = []
    for fold in sorted(routes_by_fold):
        fold_routes = routes_by_fold[fold]
        test_ids = sorted({str(route["packet_id"]) for route in fold_routes})
        outer_train = sorted(all_sample_ids - set(test_ids))
        _inner_train, validation_ids = multicorpus.inner_split(
            outer_train,
            float(config["inner_validation_fraction"]),
            f"{config['inner_split_seed']}:{fold}",
        )
        excluded = excluded_source_groups(test_ids + validation_ids, sample_packets)
        training_ids = training_ids_without_sources(full_packets, excluded)
        if set(training_ids) & (set(test_ids) | set(validation_ids)):
            raise ValueError(f"residual_fold_packet_leakage:{fold}")
        model = fit_hashed_bernoulli_nb(
            full_packets, full_truth, training_ids, config["classifier"]
        )
        validation_predictions = packet_predictions(
            model, sample_packets, validation_ids
        )
        test_predictions = packet_predictions(model, sample_packets, test_ids)
        overlap = set(oof_predictions) & set(test_predictions)
        if overlap:
            raise ValueError(f"duplicate_oof_residual_prediction:{sorted(overlap)}")
        oof_predictions.update(test_predictions)

        thresholds: dict[str, float] = {}
        threshold_diagnostics: dict[str, list[dict[str, Any]]] = {}
        for model_id in inputs["models"]:
            validation_routes = [
                route
                for route in source_routes
                if str(route["model_id"]) == model_id
                and str(route["packet_id"]) in set(validation_ids)
            ]
            threshold, diagnostics = select_threshold(
                validation_routes,
                validation_predictions,
                inputs,
                {packet_id: sample_truth[packet_id] for packet_id in validation_ids},
                config["residual_policy"],
                f"{config['batch_tie_seed']}:validation:{fold}:{model_id}",
            )
            thresholds[model_id] = threshold
            threshold_diagnostics[model_id] = diagnostics
        policy = {
            "policy_schema_version": "working-warrantroute-residual-oof-policy-v1",
            "created_at_utc": core.now_utc(),
            "policy_id": f"{config['experiment_id']}:dreaddit:fold:{fold}",
            "paper_facing_name": config["paper_facing_name"],
            "internal_variant_id": config["internal_variant_id"],
            "fit_scope": "dreaddit_full_bank_excluding_outer_test_and_inner_validation_sources",
            "outer_fold": fold,
            "training_document_count": len(training_ids),
            "validation_document_count": len(validation_ids),
            "outer_test_document_count": len(test_ids),
            "excluded_source_group_count": len(excluded),
            "training_source_overlap_with_validation_or_test": False,
            "classifier": model,
            "selected_thresholds": thresholds,
            "threshold_diagnostics": threshold_diagnostics,
            "test_truth_used_for_fit_or_threshold": False,
            "stores_source_text_or_vocabulary": False,
            "manuscript_eligible": False,
        }
        policy_path = policies_dir / f"dreaddit_oof_fold_{fold}.json"
        core.write_json(policy_path, policy)
        policy_hash = core.sha256_file(policy_path)
        policy_index.append(
            {
                "outer_fold": fold,
                "path": str(policy_path),
                "sha256": policy_hash,
                "training_document_count": len(training_ids),
            }
        )
        for model_id in inputs["models"]:
            test_routes = [
                route for route in fold_routes if str(route["model_id"]) == model_id
            ]
            final_routes.extend(
                apply_residual_batch(
                    test_routes,
                    test_predictions,
                    inputs,
                    thresholds[model_id],
                    policy_hash,
                    config,
                    f"dreaddit:{fold}:{model_id}",
                )
            )
    if set(oof_predictions) != all_sample_ids:
        raise ValueError("incomplete_dreaddit_oof_residual_predictions")
    return final_routes, oof_predictions, policy_index


def fit_transfer_and_apply(
    source_routes: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
    packets_by_dataset: dict[str, dict[str, dict[str, Any]]],
    full_packets: dict[str, dict[str, Any]],
    full_truth: dict[str, str],
    dreaddit_truth: dict[str, str],
    dreaddit_oof_predictions: dict[str, dict[str, Any]],
    config: dict[str, Any],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dreaddit_inputs = inputs_by_dataset["Dreaddit"]
    dreaddit_routes = [route for route in source_routes if route["dataset"] == "Dreaddit"]
    transfer_thresholds: dict[str, float] = {}
    threshold_diagnostics: dict[str, list[dict[str, Any]]] = {}
    for model_id in dreaddit_inputs["models"]:
        model_routes = [
            route for route in dreaddit_routes if str(route["model_id"]) == model_id
        ]
        threshold, diagnostics = select_threshold(
            model_routes,
            dreaddit_oof_predictions,
            dreaddit_inputs,
            dreaddit_truth,
            config["residual_policy"],
            f"{config['batch_tie_seed']}:transfer-threshold:{model_id}",
        )
        transfer_thresholds[model_id] = threshold
        threshold_diagnostics[model_id] = diagnostics

    model = fit_hashed_bernoulli_nb(
        full_packets, full_truth, full_packets.keys(), config["classifier"]
    )
    policy = {
        "policy_schema_version": "working-warrantroute-residual-transfer-policy-v1",
        "created_at_utc": core.now_utc(),
        "policy_id": f"{config['experiment_id']}:dreaddit-transfer",
        "paper_facing_name": config["paper_facing_name"],
        "internal_variant_id": config["internal_variant_id"],
        "fit_scope": "all_dreaddit_development_bank",
        "threshold_scope": "dreaddit_cross_fitted_predictions_only",
        "classifier": model,
        "selected_thresholds": transfer_thresholds,
        "threshold_diagnostics": threshold_diagnostics,
        "external_evaluation_truth_used_for_fit_or_threshold": False,
        "stores_source_text_or_vocabulary": False,
        "manuscript_eligible": False,
    }
    policy_path = output_dir / "policies" / "dreaddit_transfer_residual_policy.json"
    core.write_json(policy_path, policy)
    policy_hash = core.sha256_file(policy_path)

    final_routes: list[dict[str, Any]] = []
    for dataset, inputs in inputs_by_dataset.items():
        if dataset == "Dreaddit":
            continue
        predictions = packet_predictions(
            model, packets_by_dataset[dataset], inputs["packet_ids"]
        )
        dataset_routes = [route for route in source_routes if route["dataset"] == dataset]
        for model_id in inputs["models"]:
            model_routes = [
                route for route in dataset_routes if str(route["model_id"]) == model_id
            ]
            final_routes.extend(
                apply_residual_batch(
                    model_routes,
                    predictions,
                    inputs,
                    transfer_thresholds[model_id],
                    policy_hash,
                    config,
                    f"{dataset}:{model_id}",
                )
            )
    artifact = {
        "path": str(policy_path),
        "sha256": policy_hash,
        "training_document_count": len(full_packets),
    }
    return final_routes, artifact


def score_residual_routes(
    route_rows: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
    *,
    method_name: str = "WarrantRoute",
    internal_variant_id: str = "residual_discovery_v1",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    details: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    truth_hashes: dict[str, str] = {}
    for dataset, inputs in inputs_by_dataset.items():
        truth = core.load_truth_subset(inputs["truth_path"], set(inputs["packet_ids"]))
        truth_hashes[dataset] = core.sha256_file(inputs["truth_path"])
        dataset_routes = [route for route in route_rows if route["dataset"] == dataset]
        for route in dataset_routes:
            packet_id = str(route["packet_id"])
            target = truth[packet_id]
            target_flag = core.TARGET_TO_FLAG[target]
            before = target_flag in selected_flags(route, inputs)
            added = bool(route["residual_added"])
            after = before or (added and route["residual_candidate_flag"] == target_flag)
            details.append(
                {
                    "dataset": dataset,
                    "corpus_id": inputs["corpus_id"],
                    "evaluation_mode": inputs["dataset_spec"]["evaluation_mode"],
                    "model_id": route["model_id"],
                    "packet_id": packet_id,
                    "target_flaw": target,
                    "route": route["route"],
                    "detected_before_residual": before,
                    "detected": after,
                    "residual_added": added,
                    "residual_recovered": bool(after and not before),
                    "residual_candidate_correct": route["residual_candidate_flag"] == target_flag,
                    "residual_candidate_probability": route[
                        "residual_candidate_probability"
                    ],
                    "specialist_acquisitions": route["specialist_acquisitions"],
                    "total_role_acquisitions": route["total_role_acquisitions"],
                    "incremental_cost": route["incremental_cost"],
                    "total_role_cost": route["total_role_cost"],
                    "private_working_score": True,
                    "manuscript_eligible": False,
                }
            )
        for model_id in inputs["models"]:
            selected = [
                row
                for row in details
                if row["dataset"] == dataset and row["model_id"] == model_id
            ]
            tp = sum(bool(row["detected"]) for row in selected)
            before_tp = sum(bool(row["detected_before_residual"]) for row in selected)
            n = len(selected)
            lower, upper = core.wilson_interval(tp, n)
            metrics.append(
                {
                    "method": method_name,
                    "paper_facing_name": method_name,
                    "internal_variant_id": internal_variant_id,
                    "dataset": dataset,
                    "corpus_id": inputs["corpus_id"],
                    "evaluation_mode": inputs["dataset_spec"]["evaluation_mode"],
                    "model_id": model_id,
                    "tp_before_residual": before_tp,
                    "tp": tp,
                    "tp_recovered_by_residual": tp - before_tp,
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
                    "mean_residual_additions": statistics.fmean(
                        float(row["residual_added"]) for row in selected
                    ),
                    "mean_residual_classifier_calls": 1.0,
                    "result_label": "private_personal_exploratory_not_for_publication",
                    "manuscript_eligible": False,
                }
            )
    return details, metrics, truth_hashes


def build_matched_all_roles_residual_routes(
    route_rows: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, Any], list[dict[str, Any]]] = defaultdict(list)
    for route in route_rows:
        fold_scope = route.get("outer_fold") if route["dataset"] == "Dreaddit" else None
        grouped[(str(route["dataset"]), str(route["model_id"]), fold_scope)].append(route)
    matched: list[dict[str, Any]] = []
    for (dataset, model_id, fold_scope), rows in sorted(grouped.items()):
        all_role_rows: list[dict[str, Any]] = []
        predictions: dict[str, dict[str, Any]] = {}
        thresholds = {float(row["residual_threshold"]) for row in rows}
        if len(thresholds) != 1:
            raise ValueError("matched_residual_threshold_drift")
        threshold = next(iter(thresholds))
        for source in rows:
            packet_id = str(source["packet_id"])
            row = dict(source)
            row.update(
                {
                    "route_record_schema_version": "working-matched-all-roles-residual-route-v1",
                    "route": "both",
                    "selected_roles": list(core.ROLES),
                    "acquired_specialists": ["qualitative_methods", "domain"],
                    "specialist_acquisitions": 2,
                    "total_role_acquisitions": 3,
                    "incremental_cost": 2.0,
                    "total_role_cost": 3.0,
                    "stop_reason": "matched_all_roles_residual_comparator",
                    "router_name": "All roles + matched residual",
                    "paper_facing_name": "All roles + matched residual",
                    "internal_variant_id": "matched_all_roles_residual_v1",
                    "comparison_only": True,
                    "residual_added": False,
                    "residual_additions": 0,
                    "created_at_utc": core.now_utc(),
                    "manuscript_eligible": False,
                }
            )
            all_role_rows.append(row)
            predictions[packet_id] = {
                "predicted_flag": source["residual_candidate_flag"],
                "probability": source["residual_candidate_probability"],
            }
        selected = select_residual_keys(
            all_role_rows,
            predictions,
            inputs_by_dataset[dataset],
            threshold,
            config["residual_policy"],
            f"{config['batch_tie_seed']}:matched-all:{dataset}:{model_id}:{fold_scope}",
        )
        for row in all_role_rows:
            key = (str(row["model_id"]), str(row["packet_id"]))
            row["residual_added"] = key in selected
            row["residual_additions"] = int(key in selected)
            leaked = core.forbidden_keys(row)
            if leaked:
                raise ValueError(f"forbidden_matched_route_keys:{sorted(leaked)}")
        matched.extend(all_role_rows)
    matched.sort(
        key=lambda row: (str(row["dataset"]), str(row["model_id"]), str(row["packet_id"]))
    )
    return matched


def independently_score_residual_routes(
    route_rows: list[dict[str, Any]],
    detail_rows: list[dict[str, Any]],
    inputs_by_dataset: dict[str, dict[str, Any]],
) -> bool:
    observed = {
        (str(row["dataset"]), str(row["model_id"]), str(row["packet_id"])): bool(
            row["detected"]
        )
        for row in detail_rows
    }
    for dataset, inputs in inputs_by_dataset.items():
        truth = core.load_truth_subset(inputs["truth_path"], set(inputs["packet_ids"]))
        for route in (row for row in route_rows if row["dataset"] == dataset):
            packet_id = str(route["packet_id"])
            target_flag = core.TARGET_TO_FLAG[truth[packet_id]]
            flags = selected_flags(route, inputs)
            if route["residual_added"]:
                flags.add(str(route["residual_candidate_flag"]))
            key = (dataset, str(route["model_id"]), packet_id)
            if observed.get(key) != (target_flag in flags):
                return False
    return len(observed) == len(route_rows)


def residual_budget_respected(route_rows: list[dict[str, Any]], config: dict[str, Any]) -> bool:
    grouped: dict[tuple[str, str, Any], list[dict[str, Any]]] = defaultdict(list)
    for route in route_rows:
        fold_scope = route.get("outer_fold") if route["dataset"] == "Dreaddit" else None
        grouped[(str(route["dataset"]), str(route["model_id"]), fold_scope)].append(route)
    rate = float(config["residual_policy"]["maximum_addition_rate"])
    return all(
        sum(bool(row["residual_added"]) for row in rows)
        <= residual_budget_count(len(rows), rate)
        for rows in grouped.values()
    )


def build_quality_cost_rows(
    comparison_rows: list[dict[str, str]],
    prior_metric_rows: list[dict[str, str]],
    metric_rows: list[dict[str, Any]],
    matched_metric_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prior = {
        (str(row["dataset"]), multicorpus.MODEL_DISPLAY[str(row["model_id"])]): row
        for row in prior_metric_rows
    }
    current = {
        (str(row["dataset"]), multicorpus.MODEL_DISPLAY[str(row["model_id"])]): row
        for row in metric_rows
    }
    matched = {
        (str(row["dataset"]), multicorpus.MODEL_DISPLAY[str(row["model_id"])]): row
        for row in matched_metric_rows
    }
    rows: list[dict[str, Any]] = []
    datasets = list(dict.fromkeys(row["Dataset"] for row in comparison_rows))
    for dataset in datasets:
        for model in multicorpus.MODEL_DISPLAY_ORDER:
            for method, calls in (("Generalist", 1.0), ("Fixed role", 1.0), ("All roles", 3.0)):
                tp, n = multicorpus.parse_tp_n(
                    multicorpus.baseline_row(comparison_rows, dataset, method, model)["TP/N"]
                )
                rows.append(
                    {
                        "dataset": dataset,
                        "model": model,
                        "method": method,
                        "internal_variant_id": "table3_baseline",
                        "tp": tp,
                        "n": n,
                        "recall": tp / n,
                        "mean_total_role_calls": calls,
                        "mean_residual_additions": 0.0,
                    }
                )
            for variant, metric in (
                ("cumulative_output_v1", prior[(dataset, model)]),
                ("residual_discovery_v1", current[(dataset, model)]),
                ("matched_all_roles_residual_v1", matched[(dataset, model)]),
            ):
                rows.append(
                    {
                        "dataset": dataset,
                        "model": model,
                        "method": (
                            "All roles + matched residual"
                            if variant == "matched_all_roles_residual_v1"
                            else "WarrantRoute"
                        ),
                        "internal_variant_id": variant,
                        "tp": int(metric["tp"]),
                        "n": int(metric["n"]),
                        "recall": float(metric["recall"]),
                        "mean_total_role_calls": float(
                            metric["mean_total_role_acquisitions"]
                        ),
                        "mean_residual_additions": float(
                            metric.get("mean_residual_additions", 0.0)
                        ),
                    }
                )
    return rows


def write_residual_markdown_table(
    path: Path,
    rows: list[dict[str, str]],
    shortcut_audit: dict[str, Any],
) -> None:
    fields = ["Dataset", "Method", "Model", "TP/N", "Recall (%) ↑"]
    gate = (
        "FAILED"
        if shortcut_audit["deterministic_shortcut_detected"]
        else "PASSED"
    )
    lines = [
        "# Working Table 3 with WarrantRoute residual discovery",
        "",
        "Retrospective personal-local diagnostic only. Not manuscript eligible.",
        "",
        f"Scientific interpretation gate: **{gate}**. The development claims contain "
        "deterministic flaw-label templates, so these values are pipeline diagnostics, "
        "not evidence that WarrantRoute is superior.",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[field]) for field in fields) + " |")
    core.secure_write_text(path, "\n".join(lines) + "\n")


def build_pareto_analysis(
    comparison_rows: list[dict[str, str]],
    metric_rows: list[dict[str, Any]],
    matched_metric_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
    shortcut_audit: dict[str, Any],
) -> dict[str, Any]:
    fixed_tp = sum(
        multicorpus.parse_tp_n(row["TP/N"])[0]
        for row in comparison_rows
        if row["Method"] == "Fixed role"
    )
    all_roles_tp = sum(
        multicorpus.parse_tp_n(row["TP/N"])[0]
        for row in comparison_rows
        if row["Method"] == "All roles"
    )
    candidate_tp = sum(int(row["tp"]) for row in metric_rows)
    before_tp = sum(int(row["tp_before_residual"]) for row in metric_rows)
    matched_tp = sum(int(row["tp"]) for row in matched_metric_rows)
    n = sum(int(row["n"]) for row in metric_rows)
    calls = statistics.fmean(float(row["total_role_acquisitions"]) for row in route_rows)
    residual_additions = statistics.fmean(float(row["residual_added"]) for row in route_rows)
    interpolation_weight = min(1.0, max(0.0, (calls - 1.0) / 2.0))
    randomized_mix_tp = fixed_tp + interpolation_weight * (all_roles_tp - fixed_tp)
    strict_pareto_minimum = math.floor(randomized_mix_tp + 1e-12) + 1
    return {
        "analysis_schema_version": "working-warrantroute-pareto-analysis-v1",
        "candidate_tp": candidate_tp,
        "candidate_tp_before_residual": before_tp,
        "candidate_tp_recovered": candidate_tp - before_tp,
        "candidate_n": n,
        "candidate_mean_total_role_calls": calls,
        "candidate_mean_residual_additions": residual_additions,
        "fixed_role_total_tp": fixed_tp,
        "all_roles_total_tp": all_roles_tp,
        "fixed_all_randomized_mix_expected_tp_at_candidate_role_cost": randomized_mix_tp,
        "minimum_tp_for_strict_pareto_efficiency": strict_pareto_minimum,
        "strictly_pareto_efficient_vs_fixed_all_mix": candidate_tp >= strict_pareto_minimum,
        "minimum_tp_to_exceed_all_roles": all_roles_tp + 1,
        "exceeds_all_roles_total_tp": candidate_tp > all_roles_tp,
        "matched_all_roles_plus_same_residual_tp": matched_tp,
        "exceeds_matched_all_roles_plus_same_residual": candidate_tp > matched_tp,
        "matched_comparator_mean_total_role_calls": 3.0,
        "role_call_cost_unchanged_by_residual_layer": True,
        "residual_computation_reported_separately": True,
        "deterministic_shortcut_detected": shortcut_audit[
            "deterministic_shortcut_detected"
        ],
        "scientific_interpretation_gate_passed": shortcut_audit[
            "scientific_interpretation_gate_passed"
        ],
        "valid_superiority_claim": False,
        "interpretation": "all-positive recall-only feasibility diagnostic, not quality evidence",
        "manuscript_eligible": False,
    }


def source_decisions_unchanged(
    source_routes: list[dict[str, Any]], route_rows: list[dict[str, Any]]
) -> bool:
    fields = (
        "dataset",
        "model_id",
        "packet_id",
        "route",
        "selected_roles",
        "acquired_specialists",
        "total_role_acquisitions",
    )
    old = {
        (str(row["dataset"]), str(row["model_id"]), str(row["packet_id"])): row
        for row in source_routes
    }
    for row in route_rows:
        key = (str(row["dataset"]), str(row["model_id"]), str(row["packet_id"]))
        if key not in old or any(row.get(field) != old[key].get(field) for field in fields):
            return False
    return len(old) == len(route_rows)


def load_runtime_inputs(
    config: dict[str, Any]
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[str, Any]],
]:
    _source_manifest, _source_path, source_routes = cumulative.validate_source(config)
    base_experiment, inputs_by_dataset = cumulative.load_inputs(config)
    packets_by_dataset = {
        dataset: load_packet_map(inputs["packet_path"])
        for dataset, inputs in inputs_by_dataset.items()
    }
    full_packets = load_packet_map(
        resolve_workspace_path(str(config["dreaddit_full_packets"]))
    )
    return (
        base_experiment,
        inputs_by_dataset,
        source_routes,
        packets_by_dataset,
        full_packets,
    )


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    source_manifest, source_path, _routes = cumulative.validate_source(config)
    base_experiment, inputs_by_dataset, source_routes, packets_by_dataset, full_packets = (
        load_runtime_inputs(config)
    )
    return {
        "status": "ready_for_residual_working_replay",
        "experiment_id": config["experiment_id"],
        "source_status": source_manifest["status"],
        "source_routes": str(source_path),
        "source_route_count": len(source_routes),
        "dataset_packet_counts": {
            dataset: len(packets) for dataset, packets in packets_by_dataset.items()
        },
        "full_dreaddit_training_bank_count": len(full_packets),
        "model_count": len(base_experiment["expected_models"]),
        "maximum_residual_addition_rate": config["residual_policy"][
            "maximum_addition_rate"
        ],
        "new_llm_calls_required": False,
        "formal_run_enabled": False,
        "manuscript_eligible": False,
    }


def run_working(args: argparse.Namespace) -> int:
    config = core.load_json(args.config)
    validate_config(config)
    source_manifest, source_path, source_routes = cumulative.validate_source(config)
    base_experiment, inputs_by_dataset = cumulative.load_inputs(config)
    packets_by_dataset = {
        dataset: load_packet_map(inputs["packet_path"])
        for dataset, inputs in inputs_by_dataset.items()
    }
    full_packets_path = resolve_workspace_path(str(config["dreaddit_full_packets"]))
    full_truth_path = resolve_workspace_path(str(config["dreaddit_full_truth"]))
    full_packets = load_packet_map(full_packets_path)
    if len(full_packets) != int(config["expected_full_dreaddit_packets"]):
        raise ValueError("full_dreaddit_packet_count_mismatch")
    full_truth = core.load_truth_subset(full_truth_path, set(full_packets))
    dreaddit_inputs = inputs_by_dataset["Dreaddit"]
    dreaddit_truth = core.load_truth_subset(
        dreaddit_inputs["truth_path"], set(dreaddit_inputs["packet_ids"])
    )
    if any(full_truth[packet_id] != label for packet_id, label in dreaddit_truth.items()):
        raise ValueError("dreaddit_full_and_sample_truth_mismatch")

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_ROOT
        / f"multicorpus_n100_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_warrantroute_residual_v1"
    )
    if not output_dir.resolve().is_relative_to(DEFAULT_OUTPUT_ROOT.resolve()):
        raise ValueError("output_outside_personal_local_root")
    core.require_new_output_dir(output_dir)

    shortcut_audit = audit_deterministic_shortcuts(full_packets, full_truth, config)
    shortcut_path = output_dir / "shortcut_quarantine_audit.json"
    core.write_json(shortcut_path, shortcut_audit)

    dreaddit_source = [route for route in source_routes if route["dataset"] == "Dreaddit"]
    dreaddit_routes, oof_predictions, oof_policy_index = fit_dreaddit_oof(
        dreaddit_source,
        dreaddit_inputs,
        packets_by_dataset["Dreaddit"],
        full_packets,
        full_truth,
        dreaddit_truth,
        config,
        output_dir,
    )
    external_routes, transfer_policy_artifact = fit_transfer_and_apply(
        source_routes,
        inputs_by_dataset,
        packets_by_dataset,
        full_packets,
        full_truth,
        dreaddit_truth,
        oof_predictions,
        config,
        output_dir,
    )
    route_rows = dreaddit_routes + external_routes
    route_rows.sort(
        key=lambda row: (
            [str(spec["display_label"]) for spec in base_experiment["datasets"]].index(
                str(row["dataset"])
            ),
            str(row["model_id"]),
            str(row["packet_id"]),
        )
    )
    route_path = output_dir / "routes.jsonl"
    core.write_jsonl(route_path, route_rows)

    matched_route_rows = build_matched_all_roles_residual_routes(
        route_rows, inputs_by_dataset, config
    )
    matched_route_path = output_dir / "matched_all_roles_residual_routes.jsonl"
    core.write_jsonl(matched_route_path, matched_route_rows)

    # Evaluation-corpus truth labels are parsed only after both route files are immutable.
    detail_rows, metric_rows, truth_hashes = score_residual_routes(
        route_rows, inputs_by_dataset
    )
    matched_detail_rows, matched_metric_rows, matched_truth_hashes = (
        score_residual_routes(
            matched_route_rows,
            inputs_by_dataset,
            method_name="All roles + matched residual",
            internal_variant_id="matched_all_roles_residual_v1",
        )
    )
    detail_path = output_dir / "scores.private.csv"
    metric_path = output_dir / "residual_metrics.csv"
    matched_detail_path = output_dir / "matched_all_roles_residual_scores.private.csv"
    matched_metric_path = output_dir / "matched_all_roles_residual_metrics.csv"
    core.write_csv(detail_path, detail_rows)
    core.write_csv(metric_path, metric_rows)
    core.write_csv(matched_detail_path, matched_detail_rows)
    core.write_csv(matched_metric_path, matched_metric_rows)

    comparison_path = resolve_workspace_path(str(config["comparison_source"]))
    with comparison_path.open("r", encoding="utf-8", newline="") as handle:
        comparison_rows = list(csv.DictReader(handle))
    combined_rows = cumulative.build_revised_table(
        comparison_rows, metric_rows, str(config["paper_facing_name"])
    )
    combined_csv_path = output_dir / "table3_warrantroute_residual_working.csv"
    combined_md_path = output_dir / "table3_warrantroute_residual_working.md"
    core.write_csv(combined_csv_path, combined_rows)
    write_residual_markdown_table(combined_md_path, combined_rows, shortcut_audit)

    prior_metrics_path = resolve_workspace_path(str(config["prior_candidate_metrics"]))
    with prior_metrics_path.open("r", encoding="utf-8", newline="") as handle:
        prior_metric_rows = list(csv.DictReader(handle))
    quality_cost_rows = build_quality_cost_rows(
        comparison_rows, prior_metric_rows, metric_rows, matched_metric_rows
    )
    quality_cost_path = output_dir / "quality_cost_comparison.csv"
    core.write_csv(quality_cost_path, quality_cost_rows)

    pareto = build_pareto_analysis(
        comparison_rows,
        metric_rows,
        matched_metric_rows,
        route_rows,
        shortcut_audit,
    )
    pareto_path = output_dir / "pareto_analysis.json"
    core.write_json(pareto_path, pareto)

    checks = {
        "source_run_validated": source_manifest["status"] == "validated_working_complete",
        "source_route_hash_matches": core.sha256_file(source_path)
        == config["expected_source_routes_sha256"],
        "route_count_matches": len(route_rows) == int(config["expected_route_count"]),
        "source_decisions_and_role_calls_unchanged": source_decisions_unchanged(
            source_routes, route_rows
        ),
        "residual_budget_respected": residual_budget_respected(route_rows, config),
        "matched_all_roles_residual_budget_respected": residual_budget_respected(
            matched_route_rows, config
        ),
        "residual_never_duplicates_observed_flag": all(
            not row["residual_added"]
            or row["residual_candidate_flag"]
            not in selected_flags(row, inputs_by_dataset[str(row["dataset"])])
            for row in route_rows
        ),
        "candidate_not_below_pre_residual_in_any_cell": all(
            int(row["tp"]) >= int(row["tp_before_residual"]) for row in metric_rows
        ),
        "independent_route_scoring_matches": independently_score_residual_routes(
            route_rows, detail_rows, inputs_by_dataset
        ),
        "independent_matched_route_scoring_matches": (
            independently_score_residual_routes(
                matched_route_rows, matched_detail_rows, inputs_by_dataset
            )
        ),
        "candidate_and_matched_truth_hashes_agree": truth_hashes
        == matched_truth_hashes,
        "comparison_source_row_count_matches": len(comparison_rows)
        == int(config["expected_comparison_source_rows"]),
        "combined_table_row_count_matches": len(combined_rows)
        == int(config["expected_combined_rows"]),
        "no_forbidden_route_keys": not any(core.forbidden_keys(row) for row in route_rows),
        "no_forbidden_matched_route_keys": not any(
            core.forbidden_keys(row) for row in matched_route_rows
        ),
        "all_fitted_models_store_no_source_text_or_vocabulary": (
            fitted_policy_artifacts_are_safe(
                oof_policy_index, transfer_policy_artifact
            )
        ),
        "routes_written_before_external_truth_label_loading": (
            route_path.is_file() and matched_route_path.is_file()
        ),
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
        if all(positive_checks.values())
        else "working_validation_failed"
    )
    manifest = {
        "manifest_schema_version": "working-warrantroute-residual-manifest-v1",
        "created_at_utc": core.now_utc(),
        "status": status,
        "experiment_id": config["experiment_id"],
        "paper_facing_name": config["paper_facing_name"],
        "internal_variant_id": config["internal_variant_id"],
        "result_label": "private_personal_exploratory_not_for_publication",
        "checks": checks,
        "route_count": len(route_rows),
        "private_score_count": len(detail_rows),
        "metric_row_count": len(metric_rows),
        "matched_route_count": len(matched_route_rows),
        "matched_private_score_count": len(matched_detail_rows),
        "matched_metric_row_count": len(matched_metric_rows),
        "combined_table_row_count": len(combined_rows),
        "truth_hashes_used_by_post_route_scorers": truth_hashes,
        "development_inputs": {
            "full_dreaddit_packets": {
                "path": str(full_packets_path),
                "sha256": core.sha256_file(full_packets_path),
                "count": len(full_packets),
            },
            "full_dreaddit_truth": {
                "path": str(full_truth_path),
                "sha256": core.sha256_file(full_truth_path),
            },
        },
        "source_artifact": {
            "manifest": str(resolve_workspace_path(str(config["source_manifest"]))),
            "routes": str(source_path),
            "routes_sha256": core.sha256_file(source_path),
        },
        "fitted_policies": {
            "dreaddit_oof": oof_policy_index,
            "dreaddit_transfer": transfer_policy_artifact,
        },
        "pareto_analysis": pareto,
        "scientific_qualification": {
            "shortcut_quarantine": shortcut_audit,
            "all_positive_recall_only": True,
            "valid_superiority_claim": False,
            "required_before_formal_use": [
                "independently_generated_lexically_varied_claims",
                "clean_no_flaw_negative_packets",
                "frozen_disjoint_heldout_corpora",
                "precision_f1_and_false_positive_rate_reporting",
            ],
        },
        "artifacts": {
            "routes": {"path": str(route_path), "sha256": core.sha256_file(route_path)},
            "matched_all_roles_residual_routes": {
                "path": str(matched_route_path),
                "sha256": core.sha256_file(matched_route_path),
            },
            "private_scores": {
                "path": str(detail_path),
                "sha256": core.sha256_file(detail_path),
            },
            "metrics": {"path": str(metric_path), "sha256": core.sha256_file(metric_path)},
            "matched_all_roles_residual_private_scores": {
                "path": str(matched_detail_path),
                "sha256": core.sha256_file(matched_detail_path),
            },
            "matched_all_roles_residual_metrics": {
                "path": str(matched_metric_path),
                "sha256": core.sha256_file(matched_metric_path),
            },
            "combined_table_csv": {
                "path": str(combined_csv_path),
                "sha256": core.sha256_file(combined_csv_path),
            },
            "combined_table_markdown": {
                "path": str(combined_md_path),
                "sha256": core.sha256_file(combined_md_path),
            },
            "quality_cost_comparison": {
                "path": str(quality_cost_path),
                "sha256": core.sha256_file(quality_cost_path),
            },
            "pareto_analysis": {
                "path": str(pareto_path),
                "sha256": core.sha256_file(pareto_path),
            },
            "shortcut_quarantine_audit": {
                "path": str(shortcut_path),
                "sha256": core.sha256_file(shortcut_path),
            },
        },
        "limitations": [
            "all_positive_recall_only_benchmark_cannot_measure_false_positives",
            "residual_classifier_can_exploit_synthetic_packet_generation_regularities",
            "external_corpora_are_retrospective_working_transfer_not_frozen_formal_evaluation",
            "hashed_classifier_compute_is_reported_separately_from_role_llm_calls",
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
                "candidate_tp": pareto["candidate_tp"],
                "candidate_tp_recovered": pareto["candidate_tp_recovered"],
                "mean_total_role_calls": pareto["candidate_mean_total_role_calls"],
                "mean_residual_additions": pareto["candidate_mean_residual_additions"],
                "strictly_pareto_efficient_vs_fixed_all_mix": pareto[
                    "strictly_pareto_efficient_vs_fixed_all_mix"
                ],
                "exceeds_all_roles_total_tp": pareto["exceeds_all_roles_total_tp"],
                "matched_all_roles_plus_same_residual_tp": pareto[
                    "matched_all_roles_plus_same_residual_tp"
                ],
                "exceeds_matched_all_roles_plus_same_residual": pareto[
                    "exceeds_matched_all_roles_plus_same_residual"
                ],
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
    run_parser.add_argument("--output-dir", type=Path)
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
            raise RuntimeError(
                "formal_run_blocked:positive-only retrospective residual diagnostic"
            )
        raise RuntimeError(f"unknown_command:{args.command}")
    except Exception as exc:
        print(f"WarrantRoute residual {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
