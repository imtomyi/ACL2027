#!/usr/bin/env python3
"""Promote one Qwen3 Generalist aggregate after external authorization.

This command never opens corpus, packet, observation, truth, raw-execution, or
manuscript files.  It accepts only the source-free internal aggregate produced
by the scoring exporter, a separately supplied external-authority promotion
record, its detached Ed25519 signature, and its public key. Trust comes only
from a fixed, root-controlled authority registry, never from caller parameters.
The command writes a new aggregate-only record only after every binding and
authority check succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError as exc:  # pragma: no cover - environment preflight
    raise SystemExit("cryptography with Ed25519 support is required") from exc


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
CONTRACT = (
    RQ2_ROOT
    / "protocol"
    / "qwen3_generalist_external_score_promotion_contract_v1.md"
)
SYSTEM_TRUST_REGISTRY = Path(
    "/etc/warrantroute/qwen3_generalist_score_promotion_authorities_v1.json"
)

EXPECTED_DATASET = {
    "corpus_id": "dreaddit",
    "display_name": "Dreaddit",
    "split": "test",
    "cluster_unit": "post",
}
EXPECTED_METHOD_NAME = "Generalist"
EXPECTED_REVIEWER_ACTOR = "qwen3_8b_generalist_reviewer_v1"
EXPECTED_MODEL_ID = "qwen3:8b"
EXPECTED_MODEL_DIGEST = (
    "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
)
EXPECTED_METRIC = "error_detection_recall"
EXPECTED_PROJECT_ID = "warrant-route-acl2027"
EXPECTED_STUDY_ID = "warrantroute-rq2"
EXPECTED_ROW_ID = "table3_dreaddit_generalist_qwen3_8b"
EXPECTED_REPORTING_PURPOSE = "manuscript_reporting"

INPUT_HASH_KEYS = frozenset(
    {
        "study_freeze_sha256",
        "readiness_report_sha256",
        "packet_bank_seal_sha256",
        "truth_cluster_map_sha256",
        "observation_bundle_sha256",
        "observation_seal_sha256",
        "reviewer_component_freeze_sha256",
        "shared_rating_schema_sha256",
        "scoring_exporter_sha256",
        "scoring_contract_sha256",
        "formal_runner_sha256",
        "formal_runner_contract_sha256",
        "governance_record_sha256",
        "reviewer_registry_sha256",
        "privacy_review_log_sha256",
        "source_receipt_sha256",
        "study_manifest_sha256",
        "packet_study_freeze_sha256",
        "execution_freeze_sha256",
        "raw_execution_bundle_sha256",
        "raw_execution_seal_sha256",
    }
)


class ScorePromotionError(RuntimeError):
    """A finite, source-free promotion failure safe to report."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ScorePromotionError(code)


def exact_keys(value: Any, expected: Iterable[str], label: str) -> None:
    require(isinstance(value, dict), f"{label}_not_object")
    require(set(value) == set(expected), f"{label}_keys_invalid")


def reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"nonfinite_json_constant:{value}")


def strict_json_loads(data: bytes) -> dict[str, Any]:
    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate_json_key:{key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=object_from_pairs,
            parse_constant=reject_nonfinite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScorePromotionError("invalid_or_ambiguous_json") from exc
    require(isinstance(value, dict), "json_root_not_object")
    return value


def canonical_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ScorePromotionError("value_not_canonical_json") from exc
    return (encoded + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        f"{label}_sha256_invalid",
    )
    return value


def parse_utc(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label}_utc_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ScorePromotionError(f"{label}_utc_invalid") from exc
    require(parsed.tzinfo is not None, f"{label}_utc_invalid")
    return parsed.astimezone(timezone.utc)


def require_nonempty_identifier(value: Any, label: str) -> str:
    require(isinstance(value, str), f"{label}_invalid")
    require(value == value.strip() and 1 <= len(value) <= 200, f"{label}_invalid")
    require(all(character.isalnum() or character in "._:-/" for character in value), f"{label}_invalid")
    return value


def require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{label}_invalid")
    require(value >= minimum, f"{label}_invalid")
    return value


def require_number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label}_invalid")
    converted = float(value)
    require(math.isfinite(converted), f"{label}_invalid")
    return converted


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def read_regular_bytes(path: Path) -> bytes:
    path = path.resolve(strict=False)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ScorePromotionError("required_file_unavailable") from exc
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "read_target_not_regular_file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def require_private_input_path(path: Path, *, root: Path, label: str) -> None:
    require(path.is_absolute(), f"{label}_path_not_absolute")
    require(path.resolve(strict=False) == path, f"{label}_path_resolution_drift")
    require(is_within(path, root), f"{label}_outside_required_root")
    require(path.exists() and not path.is_symlink(), f"{label}_missing_or_symlink")
    require(path.is_file(), f"{label}_not_regular_file")
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, f"{label}_mode_invalid")
    require(
        path.parent.is_dir()
        and not path.parent.is_symlink()
        and stat.S_IMODE(path.parent.stat().st_mode) == 0o700,
        f"{label}_parent_mode_invalid",
    )


def require_storage_output_path(path: Path, *, workspace: Path) -> None:
    storage = workspace / "Storage"
    require(path.is_absolute(), "output_path_not_absolute")
    require(path.resolve(strict=False) == path, "output_path_resolution_drift")
    require(is_within(path, storage), "output_outside_storage")
    require(not path.exists() and not path.is_symlink(), "output_exists_or_symlink")
    require(
        path.parent.is_dir()
        and not path.parent.is_symlink()
        and stat.S_IMODE(path.parent.stat().st_mode) == 0o700,
        "output_parent_mode_invalid",
    )


def require_non_operator_controlled_registry_path(path: Path) -> Path:
    """Require a fixed root-owned registry that the invoking user cannot edit."""

    require(path == SYSTEM_TRUST_REGISTRY, "trusted_registry_path_not_fixed")
    require(path.is_absolute(), "trusted_registry_path_not_absolute")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ScorePromotionError("trusted_authority_registry_unavailable") from exc
    require(path.exists() and path.is_file() and not path.is_symlink(), "trusted_registry_not_regular_file")
    file_stat = resolved.stat()
    require(file_stat.st_uid == 0, "trusted_registry_not_root_owned")
    require(stat.S_IMODE(file_stat.st_mode) & 0o222 == 0, "trusted_registry_is_writable")
    for ancestor in (resolved.parent, *resolved.parents):
        ancestor_stat = ancestor.stat()
        require(ancestor_stat.st_uid == 0, "trusted_registry_ancestor_not_root_owned")
        require(
            stat.S_IMODE(ancestor_stat.st_mode) & 0o022 == 0,
            "trusted_registry_ancestor_operator_writable",
        )
    return resolved


def expected_promotion_scope() -> dict[str, Any]:
    return {
        "project_id": EXPECTED_PROJECT_ID,
        "study_id": EXPECTED_STUDY_ID,
        "row_id": EXPECTED_ROW_ID,
        "reporting_purpose": EXPECTED_REPORTING_PURPOSE,
        "dataset": EXPECTED_DATASET,
        "method_name": EXPECTED_METHOD_NAME,
        "reviewer_actor_id": EXPECTED_REVIEWER_ACTOR,
        "model_id": EXPECTED_MODEL_ID,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "metric_name": EXPECTED_METRIC,
    }


def load_private_json(path: Path, *, root: Path, label: str) -> tuple[dict[str, Any], bytes]:
    require_private_input_path(path, root=root, label=label)
    data = read_regular_bytes(path)
    return strict_json_loads(data), data


def validate_internal_export(value: dict[str, Any]) -> dict[str, Any]:
    exact_keys(
        value,
        {
            "document_type",
            "export_version",
            "created_at_utc",
            "status",
            "manuscript_eligible",
            "dataset",
            "method",
            "candidate_generation",
            "metric",
            "eligibility",
            "input_hashes",
        },
        "internal_export",
    )
    require(
        value["document_type"] == "warrantroute_qwen3_generalist_scoring_export_v1",
        "internal_export_document_type_invalid",
    )
    require(value["export_version"] == "qwen3-generalist-score-v1", "internal_export_version_invalid")
    parse_utc(value["created_at_utc"], "internal_export_created_at")
    require(value["status"] == "complete_internal_only", "internal_export_status_invalid")
    require(value["manuscript_eligible"] is False, "internal_export_already_eligible")

    exact_keys(value["dataset"], EXPECTED_DATASET, "internal_dataset")
    require(value["dataset"] == EXPECTED_DATASET, "internal_dataset_scope_invalid")

    method = value["method"]
    exact_keys(
        method,
        {"name", "reviewer_actor_id", "model_id", "model_digest", "primary_repetition"},
        "internal_method",
    )
    require(method["name"] == EXPECTED_METHOD_NAME, "internal_method_name_invalid")
    require(method["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "internal_reviewer_actor_invalid")
    require(method["model_id"] == EXPECTED_MODEL_ID, "internal_model_id_invalid")
    require(method["model_digest"] == EXPECTED_MODEL_DIGEST, "internal_model_digest_invalid")
    require(method["primary_repetition"] == 1, "internal_primary_repetition_invalid")

    candidate = value["candidate_generation"]
    exact_keys(candidate, {"model_id", "snapshot_sha256", "prompt_sha256"}, "candidate_generation")
    require(isinstance(candidate["model_id"], str) and candidate["model_id"], "candidate_model_id_invalid")
    require(candidate["model_id"] != EXPECTED_MODEL_ID, "candidate_reviewer_model_not_distinct")
    require_sha256(candidate["snapshot_sha256"], "candidate_snapshot")
    require_sha256(candidate["prompt_sha256"], "candidate_prompt")

    metric = value["metric"]
    exact_keys(
        metric,
        {
            "name",
            "tp",
            "fn",
            "n",
            "tp_over_n",
            "recall",
            "recall_percent",
            "confidence_level",
            "ci_method",
            "recall_95_ci",
            "recall_95_ci_percent",
            "source_cluster_unit",
            "bootstrap_cluster_unit",
            "independent_cluster_count",
            "bootstrap_resamples",
            "bootstrap_seed",
        },
        "internal_metric",
    )
    require(metric["name"] == EXPECTED_METRIC, "metric_name_invalid")
    tp = require_int(metric["tp"], "metric_tp")
    fn = require_int(metric["fn"], "metric_fn")
    n = require_int(metric["n"], "metric_n", minimum=1)
    require(tp + fn == n, "metric_denominator_inconsistent")
    require(metric["tp_over_n"] == f"{tp}/{n}", "metric_tp_over_n_inconsistent")
    recall = require_number(metric["recall"], "metric_recall")
    recall_percent = require_number(metric["recall_percent"], "metric_recall_percent")
    require(recall == tp / n, "metric_recall_inconsistent")
    require(recall_percent == 100 * recall, "metric_recall_percent_inconsistent")
    require(metric["confidence_level"] == 0.95, "metric_confidence_level_invalid")
    require(metric["ci_method"] == "cluster_bootstrap_percentile", "metric_ci_method_invalid")
    ci = metric["recall_95_ci"]
    ci_percent = metric["recall_95_ci_percent"]
    require(isinstance(ci, list) and len(ci) == 2, "metric_ci_invalid")
    require(isinstance(ci_percent, list) and len(ci_percent) == 2, "metric_ci_percent_invalid")
    ci_values = [require_number(item, f"metric_ci_{index}") for index, item in enumerate(ci)]
    ci_percent_values = [
        require_number(item, f"metric_ci_percent_{index}")
        for index, item in enumerate(ci_percent)
    ]
    require(0 <= ci_values[0] <= ci_values[1] <= 1, "metric_ci_bounds_invalid")
    require(ci_percent_values == [100 * item for item in ci_values], "metric_ci_percent_inconsistent")
    require(metric["source_cluster_unit"] == "post", "metric_source_cluster_unit_invalid")
    require(
        metric["bootstrap_cluster_unit"] == "base_packet_connected_component",
        "metric_bootstrap_cluster_unit_invalid",
    )
    require_int(metric["independent_cluster_count"], "metric_cluster_count", minimum=5)
    require(metric["bootstrap_resamples"] == 10_000, "metric_bootstrap_resamples_invalid")
    require(metric["bootstrap_seed"] == 20_270_826, "metric_bootstrap_seed_invalid")

    eligibility = value["eligibility"]
    exact_keys(
        eligibility,
        {
            "authorization_record_id",
            "authorization_record_sha256",
            "privacy_cleared_packet_bank",
            "clean_preaccess_record",
            "formal_readiness_report_passed",
            "candidate_generator_distinct_from_reviewer",
            "complete_fixed_denominator",
            "all_failures_retained_as_misses",
            "ci_estimable",
            "exact_local_authority_and_evidence_records_verified",
            "external_authority_signature_verified",
            "external_authority_gate_satisfied",
            "manuscript_eligibility_blockers",
            "authority_limitation",
        },
        "internal_eligibility",
    )
    require_nonempty_identifier(eligibility["authorization_record_id"], "local_authorization_record_id")
    require_sha256(eligibility["authorization_record_sha256"], "local_authorization_record")
    for field in (
        "privacy_cleared_packet_bank",
        "clean_preaccess_record",
        "formal_readiness_report_passed",
        "candidate_generator_distinct_from_reviewer",
        "complete_fixed_denominator",
        "all_failures_retained_as_misses",
        "ci_estimable",
        "exact_local_authority_and_evidence_records_verified",
    ):
        require(eligibility[field] is True, f"internal_eligibility_{field}_invalid")
    require(eligibility["external_authority_signature_verified"] is False, "internal_external_gate_not_open")
    require(eligibility["external_authority_gate_satisfied"] is False, "internal_external_gate_not_open")
    require(
        eligibility["manuscript_eligibility_blockers"]
        == ["external_authority_signature_not_verified"],
        "internal_blocker_set_invalid",
    )
    require(isinstance(eligibility["authority_limitation"], str) and eligibility["authority_limitation"], "internal_authority_limitation_missing")

    hashes = value["input_hashes"]
    exact_keys(hashes, INPUT_HASH_KEYS, "internal_input_hashes")
    for key, digest in hashes.items():
        require_sha256(digest, f"input_hash:{key}")
    return value


def expected_signed_bindings(
    internal_export: dict[str, Any], internal_export_hash: str
) -> dict[str, Any]:
    return {
        "aggregate_binding": {
            "internal_aggregate_export_sha256": internal_export_hash,
            "internal_document_type": internal_export["document_type"],
            "internal_export_version": internal_export["export_version"],
            "internal_created_at_utc": internal_export["created_at_utc"],
            "dataset_sha256": sha256_bytes(canonical_bytes(internal_export["dataset"])),
            "method_sha256": sha256_bytes(canonical_bytes(internal_export["method"])),
            "candidate_generation_sha256": sha256_bytes(
                canonical_bytes(internal_export["candidate_generation"])
            ),
            "metric_sha256": sha256_bytes(canonical_bytes(internal_export["metric"])),
            "score": {
                "metric_name": internal_export["metric"]["name"],
                "tp": internal_export["metric"]["tp"],
                "fn": internal_export["metric"]["fn"],
                "n": internal_export["metric"]["n"],
                "tp_over_n": internal_export["metric"]["tp_over_n"],
                "recall": internal_export["metric"]["recall"],
                "recall_percent": internal_export["metric"]["recall_percent"],
                "recall_95_ci": list(internal_export["metric"]["recall_95_ci"]),
                "recall_95_ci_percent": list(
                    internal_export["metric"]["recall_95_ci_percent"]
                ),
            },
        },
        "evidence_chain": {
            "input_hashes_sha256": sha256_bytes(
                canonical_bytes(internal_export["input_hashes"])
            ),
            "input_hashes": dict(internal_export["input_hashes"]),
        },
    }


def load_system_trusted_authority(
    *,
    authority_id: str,
    verification_time: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load one authority from the fixed, non-operator-controlled registry."""

    require_nonempty_identifier(authority_id, "trusted_authority_id")
    registry_path = require_non_operator_controlled_registry_path(
        SYSTEM_TRUST_REGISTRY
    )
    registry_bytes = read_regular_bytes(registry_path)
    registry = strict_json_loads(registry_bytes)
    exact_keys(
        registry,
        {
            "document_type",
            "registry_version",
            "registry_id",
            "status",
            "issued_at_utc",
            "authorities",
        },
        "trusted_authority_registry",
    )
    require(
        registry["document_type"]
        == "warrantroute_qwen3_generalist_trusted_authority_registry_v1",
        "trusted_registry_document_type_invalid",
    )
    require(
        registry["registry_version"]
        == "qwen3-generalist-trusted-authority-registry-v1",
        "trusted_registry_version_invalid",
    )
    require_nonempty_identifier(registry["registry_id"], "trusted_registry_id")
    require(registry["status"] == "active", "trusted_registry_not_active")
    issued_at = parse_utc(registry["issued_at_utc"], "trusted_registry_issued_at")
    require(verification_time.tzinfo is not None, "verification_time_timezone_missing")
    checked_at = verification_time.astimezone(timezone.utc)
    require(issued_at <= checked_at, "trusted_registry_not_yet_issued")
    authorities = registry["authorities"]
    require(isinstance(authorities, list) and authorities, "trusted_registry_authorities_empty")
    seen_ids: set[str] = set()
    selected: dict[str, Any] | None = None
    for index, entry in enumerate(authorities):
        exact_keys(
            entry,
            {
                "authority_id",
                "authority_role",
                "public_key_spki_sha256",
                "active_from_utc",
                "active_until_utc",
                "allowed_scope",
            },
            f"trusted_authority:{index}",
        )
        entry_id = require_nonempty_identifier(
            entry["authority_id"], f"trusted_authority_id:{index}"
        )
        require(entry_id not in seen_ids, "trusted_registry_authority_id_duplicate")
        seen_ids.add(entry_id)
        require(
            entry["authority_role"] == "manuscript_reporting_authority",
            f"trusted_authority_role_invalid:{index}",
        )
        require_sha256(
            entry["public_key_spki_sha256"],
            f"trusted_authority_public_key:{index}",
        )
        active_from = parse_utc(
            entry["active_from_utc"], f"trusted_authority_active_from:{index}"
        )
        active_until = parse_utc(
            entry["active_until_utc"], f"trusted_authority_active_until:{index}"
        )
        require(active_from <= active_until, f"trusted_authority_dates_invalid:{index}")
        require(
            entry["allowed_scope"] == expected_promotion_scope(),
            f"trusted_authority_scope_invalid:{index}",
        )
        if entry_id == authority_id:
            require(active_from <= checked_at, "trusted_authority_not_yet_active")
            require(checked_at <= active_until, "trusted_authority_expired")
            selected = entry
    require(selected is not None, "authority_not_in_system_trust_registry")
    return selected, {
        "trusted_authority_registry_id": registry["registry_id"],
        "trusted_authority_registry_version": registry["registry_version"],
        "trusted_authority_registry_sha256": sha256_bytes(registry_bytes),
    }


def validate_promotion_record(
    record: dict[str, Any],
    *,
    internal_export: dict[str, Any],
    internal_export_hash: str,
    trusted_authority: dict[str, Any],
    verification_time: datetime,
) -> dict[str, Any]:
    exact_keys(
        record,
        {
            "document_type",
            "promotion_version",
            "authority",
            "decision",
            "validity",
            "scope",
            "aggregate_binding",
            "evidence_chain",
            "attestations",
        },
        "promotion_record",
    )
    require(
        record["document_type"]
        == "warrantroute_qwen3_generalist_external_score_promotion_v1",
        "promotion_document_type_invalid",
    )
    require(record["promotion_version"] == "qwen3-generalist-external-promotion-v1", "promotion_version_invalid")

    authority = record["authority"]
    exact_keys(
        authority,
        {"authority_id", "authority_role", "trusted_public_key_spki_sha256"},
        "promotion_authority",
    )
    require(
        authority["authority_id"] == trusted_authority["authority_id"],
        "authority_id_mismatch",
    )
    require(authority["authority_role"] == "manuscript_reporting_authority", "authority_role_invalid")
    require(
        authority["trusted_public_key_spki_sha256"]
        == trusted_authority["public_key_spki_sha256"],
        "promotion_key_fingerprint_mismatch",
    )

    decision = record["decision"]
    exact_keys(
        decision,
        {"decision_id", "decision_status", "manuscript_reporting_authorized"},
        "promotion_decision",
    )
    require_nonempty_identifier(decision["decision_id"], "decision_id")
    require(decision["decision_status"] == "approved", "promotion_not_approved")
    require(decision["manuscript_reporting_authorized"] is True, "manuscript_reporting_not_authorized")

    validity = record["validity"]
    exact_keys(
        validity,
        {"approved_at_utc", "not_before_utc", "expires_at_utc"},
        "promotion_validity",
    )
    approved_at = parse_utc(validity["approved_at_utc"], "promotion_approved_at")
    not_before = parse_utc(validity["not_before_utc"], "promotion_not_before")
    expires_at = parse_utc(validity["expires_at_utc"], "promotion_expires_at")
    internal_created = parse_utc(internal_export["created_at_utc"], "internal_export_created_at")
    require(internal_created <= approved_at, "promotion_predates_internal_export")
    require(not_before <= approved_at <= expires_at, "promotion_validity_order_invalid")
    require(verification_time.tzinfo is not None, "verification_time_timezone_missing")
    checked_at = verification_time.astimezone(timezone.utc)
    require(checked_at >= not_before, "promotion_not_yet_valid")
    require(checked_at >= approved_at, "promotion_decision_not_yet_issued")
    require(checked_at <= expires_at, "promotion_expired")

    scope = record["scope"]
    exact_keys(
        scope,
        {
            "project_id",
            "study_id",
            "row_id",
            "reporting_purpose",
            "dataset",
            "method_name",
            "reviewer_actor_id",
            "model_id",
            "model_digest",
            "metric_name",
        },
        "promotion_scope",
    )
    require(scope == expected_promotion_scope(), "promotion_scope_mismatch")

    bindings = expected_signed_bindings(internal_export, internal_export_hash)
    require(record["aggregate_binding"] == bindings["aggregate_binding"], "signed_aggregate_binding_mismatch")
    require(record["evidence_chain"] == bindings["evidence_chain"], "signed_evidence_chain_mismatch")

    attestations = record["attestations"]
    exact_keys(
        attestations,
        {
            "aggregate_only_reviewed",
            "source_text_absent_from_promotion_record",
            "scope_limited_to_bound_score",
        },
        "promotion_attestations",
    )
    require(attestations["aggregate_only_reviewed"] is True, "aggregate_only_attestation_missing")
    require(
        attestations["source_text_absent_from_promotion_record"] is True,
        "source_text_absence_attestation_missing",
    )
    require(attestations["scope_limited_to_bound_score"] is True, "scope_limitation_attestation_missing")
    return {
        "authority_id": authority["authority_id"],
        "authority_role": authority["authority_role"],
        "decision_id": decision["decision_id"],
        "approved_at_utc": validity["approved_at_utc"],
        "not_before_utc": validity["not_before_utc"],
        "expires_at_utc": validity["expires_at_utc"],
    }


def load_ed25519_public_key(data: bytes) -> tuple[Ed25519PublicKey, bytes]:
    try:
        key = serialization.load_pem_public_key(data)
    except (ValueError, TypeError) as exc:
        raise ScorePromotionError("trusted_public_key_pem_invalid") from exc
    require(isinstance(key, Ed25519PublicKey), "trusted_public_key_not_ed25519")
    spki_der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key, spki_der


def verify_detached_signature(
    *,
    public_key: Ed25519PublicKey,
    signature: bytes,
    promotion_record: dict[str, Any],
) -> str:
    require(len(signature) == 64, "detached_signature_length_invalid")
    payload = canonical_bytes(promotion_record)
    try:
        public_key.verify(signature, payload)
    except InvalidSignature as exc:
        raise ScorePromotionError("detached_signature_invalid") from exc
    return sha256_bytes(payload)


def build_promoted_export(
    *,
    internal_export: dict[str, Any],
    internal_export_file_sha256: str,
    promotion_record_file_sha256: str,
    promotion_payload_sha256: str,
    signature_sha256: str,
    public_key_file_sha256: str,
    public_key_spki_sha256: str,
    authority_metadata: dict[str, Any],
    registry_metadata: dict[str, Any],
    promoted_at_utc: str,
) -> dict[str, Any]:
    parse_utc(promoted_at_utc, "promoted_at")
    return {
        "document_type": "warrantroute_qwen3_generalist_manuscript_score_v1",
        "promotion_version": "qwen3-generalist-manuscript-score-v1",
        "promoted_at_utc": promoted_at_utc,
        "status": "externally_authorized_for_manuscript_reporting",
        "manuscript_eligible": True,
        "aggregate_only": True,
        "contains_source_text": False,
        "dataset": dict(internal_export["dataset"]),
        "method": dict(internal_export["method"]),
        "candidate_generation": dict(internal_export["candidate_generation"]),
        "metric": dict(internal_export["metric"]),
        "authorization": {
            **authority_metadata,
            "manuscript_reporting_authorized": True,
            "detached_ed25519_signature_verified": True,
            "trusted_public_key_spki_sha256": public_key_spki_sha256,
            "trusted_authority_registry_id": registry_metadata[
                "trusted_authority_registry_id"
            ],
            "scope": {
                "project_id": EXPECTED_PROJECT_ID,
                "study_id": EXPECTED_STUDY_ID,
                "row_id": EXPECTED_ROW_ID,
                "reporting_purpose": EXPECTED_REPORTING_PURPOSE,
            },
        },
        "provenance": {
            "internal_aggregate_export_sha256": internal_export_file_sha256,
            "promotion_record_file_sha256": promotion_record_file_sha256,
            "promotion_payload_sha256": promotion_payload_sha256,
            "detached_signature_sha256": signature_sha256,
            "trusted_public_key_file_sha256": public_key_file_sha256,
            "trusted_public_key_spki_sha256": public_key_spki_sha256,
            "trusted_authority_registry_version": registry_metadata[
                "trusted_authority_registry_version"
            ],
            "trusted_authority_registry_sha256": registry_metadata[
                "trusted_authority_registry_sha256"
            ],
            "input_hashes_sha256": sha256_bytes(
                canonical_bytes(internal_export["input_hashes"])
            ),
            "input_hashes": dict(internal_export["input_hashes"]),
        },
    }


def write_new_private_json(path: Path, value: dict[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ScorePromotionError("output_exists") from exc
    except OSError as exc:
        raise ScorePromotionError("output_unavailable") from exc
    try:
        os.fchmod(descriptor, 0o600)
        payload = canonical_bytes(value)
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def promote_score(
    *,
    internal_export_path: Path,
    promotion_record_path: Path,
    detached_signature_path: Path,
    trusted_public_key_path: Path,
    trusted_authority_id: str,
    output_path: Path,
    workspace: Path = WORKSPACE,
    verification_time: datetime | None = None,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    storage = workspace / "Storage"
    authority_root = workspace / "governance" / "local"
    checked_at = verification_time or datetime.now(timezone.utc)
    trusted_authority, registry_metadata = load_system_trusted_authority(
        authority_id=trusted_authority_id,
        verification_time=checked_at,
    )
    internal_export, internal_bytes = load_private_json(
        internal_export_path,
        root=storage,
        label="internal_export",
    )
    promotion_record, promotion_bytes = load_private_json(
        promotion_record_path,
        root=authority_root,
        label="promotion_record",
    )
    require_private_input_path(
        detached_signature_path,
        root=authority_root,
        label="detached_signature",
    )
    require_private_input_path(
        trusted_public_key_path,
        root=authority_root,
        label="trusted_public_key",
    )
    require_storage_output_path(output_path, workspace=workspace)

    validate_internal_export(internal_export)
    internal_hash = sha256_bytes(internal_bytes)
    key_bytes = read_regular_bytes(trusted_public_key_path)
    public_key, spki_der = load_ed25519_public_key(key_bytes)
    computed_spki_hash = sha256_bytes(spki_der)
    require(
        computed_spki_hash == trusted_authority["public_key_spki_sha256"],
        "trusted_public_key_fingerprint_mismatch",
    )

    signature = read_regular_bytes(detached_signature_path)
    payload_hash = verify_detached_signature(
        public_key=public_key,
        signature=signature,
        promotion_record=promotion_record,
    )
    authority_metadata = validate_promotion_record(
        promotion_record,
        internal_export=internal_export,
        internal_export_hash=internal_hash,
        trusted_authority=trusted_authority,
        verification_time=checked_at,
    )
    promoted_at = checked_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    promoted = build_promoted_export(
        internal_export=internal_export,
        internal_export_file_sha256=internal_hash,
        promotion_record_file_sha256=sha256_bytes(promotion_bytes),
        promotion_payload_sha256=payload_hash,
        signature_sha256=sha256_bytes(signature),
        public_key_file_sha256=sha256_bytes(key_bytes),
        public_key_spki_sha256=computed_spki_hash,
        authority_metadata=authority_metadata,
        registry_metadata=registry_metadata,
        promoted_at_utc=promoted_at,
    )
    write_new_private_json(output_path, promoted)
    return promoted


def source_free_summary() -> dict[str, Any]:
    return {
        "component": "qwen3-generalist-external-score-promotion-v1",
        "status": "passed",
        "source_text_accessed": False,
        "outputs_written": False,
        "manuscript_eligible": False,
        "system_trust_registry_path": str(SYSTEM_TRUST_REGISTRY),
        "system_trust_registry_present": SYSTEM_TRUST_REGISTRY.exists(),
        "promotion_tool_sha256": sha256_bytes(read_regular_bytes(SCRIPT)),
        "promotion_contract_sha256": sha256_bytes(read_regular_bytes(CONTRACT)),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    subparsers.add_parser("dry-run")
    promote = subparsers.add_parser("promote")
    promote.add_argument("--internal-export", type=Path, required=True)
    promote.add_argument("--promotion-record", type=Path, required=True)
    promote.add_argument("--detached-signature", type=Path, required=True)
    promote.add_argument("--trusted-public-key", type=Path, required=True)
    promote.add_argument("--trusted-authority-id", required=True)
    promote.add_argument("--output", type=Path, required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "dry-run":
            result = source_free_summary()
        else:
            result = promote_score(
                internal_export_path=args.internal_export,
                promotion_record_path=args.promotion_record,
                detached_signature_path=args.detached_signature,
                trusted_public_key_path=args.trusted_public_key,
                trusted_authority_id=args.trusted_authority_id,
                output_path=args.output,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except ScorePromotionError as exc:
        print(
            json.dumps(
                {
                    "component": "qwen3-generalist-external-score-promotion-v1",
                    "status": "blocked",
                    "error": str(exc),
                    "outputs_written": False,
                    "manuscript_eligible": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
