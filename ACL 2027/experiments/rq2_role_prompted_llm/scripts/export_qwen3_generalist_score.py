#!/usr/bin/env python3
"""Build a fail-closed Qwen3 Generalist manuscript scoring export.

The exporter never reads an evaluator packet or corpus file. It consumes a
text-free study freeze, a sealed observation bundle, and a separate private
truth/cluster map. All non-valid observations remain in the denominator and
count as misses. The command writes an aggregate export only after every
eligibility and integrity check passes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
import random
import stat
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment preflight
    raise SystemExit("jsonschema is required") from exc


SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_qwen3_generalist_reviewer as reviewer  # noqa: E402


COMPONENT_FREEZE = RQ2_ROOT / "config" / "qwen3_generalist_reviewer_freeze.json"
CONTRACT = RQ2_ROOT / "protocol" / "qwen3_generalist_scoring_export_contract_v1.md"
TRUTH_MAP_SCHEMA = RQ2_ROOT / "schemas" / "qwen3_generalist_truth_cluster_map_v1.schema.json"
PACKET_STUDY_FREEZE_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_packet_study_freeze_v1.schema.json"
)
PACKET_MANIFEST_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_packet_manifest_v1.schema.json"
)
PREACCESS_RECORD_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_preaccess_record_v1.schema.json"
)
VERIFICATION_BUNDLE_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_verification_bundle_v1.schema.json"
)
VERIFICATION_SEAL_SCHEMA = (
    RQ2_ROOT / "schemas" / "qwen3_generalist_verification_seal_v1.schema.json"
)
FORMAL_RUNNER = RQ2_ROOT / "scripts" / "run_qwen3_generalist_formal.py"
FORMAL_RUNNER_CONTRACT = RQ2_ROOT / "protocol" / "qwen3_generalist_formal_run_contract_v1.md"
READINESS_CHECKER = WORKSPACE / "governance" / "scripts" / "check_project_readiness.py"
EXPECTED_CORPUS_ID = "dreaddit"
EXPECTED_DATASET_DISPLAY = "Dreaddit"
EXPECTED_SPLIT = "test"
EXPECTED_CLUSTER_UNIT = "post"
EXPECTED_BOOTSTRAP_CLUSTER_UNIT = "base_packet_connected_component"
EXPECTED_METHOD = "Generalist"
EXPECTED_REVIEWER_ACTOR = "qwen3_8b_generalist_reviewer_v1"
EXPECTED_MODEL_ID = "qwen3:8b"
EXPECTED_MODEL_DIGEST = reviewer.EXPECTED_MODEL_DIGEST
EXPECTED_PRIMARY_REPETITION = 1
EXPECTED_METRIC = "error_detection_recall"
EXPECTED_RESAMPLES = 10_000
EXPECTED_BOOTSTRAP_SEED = 20_270_826
EXPECTED_MINIMUM_CLUSTERS = 5
REQUIRED_GATE_IDS = (
    "institutional_determination",
    "source_platform_authorization",
    "provider_model_processing",
    "exact_corpus_input_contract",
    "two_person_excerpt_privacy_review",
    "cluster_aware_sampling",
    "frozen_study_manifest",
    "rater_and_service_access_controls",
    "retention_deletion_controls",
    "release_controls",
)
FORMAL_WARNING_CODES = (
    "mechanical_check_not_approval",
    "synthetic_and_real_results_must_remain_separate",
    "underlying_documentary_evidence_required",
)
EXPECTED_FAMILY_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}

TERMINAL_STATUSES = frozenset(
    {
        "valid_rating",
        "invalid_json",
        "schema_failure",
        "truncated",
        "context_overflow",
        "timeout",
        "service_failure",
        "model_identity_failure",
        "abstention",
        "other_terminal_failure",
    }
)
FORMAL_OUTPUT_POLICY = {
    "directory_class": "private_storage_only",
    "scoring_bundle_contains_source_text": False,
    "raw_execution_bundle_contains_source_text": True,
    "overwrite_allowed": False,
    "raw_requests_retained": True,
    "raw_responses_retained": True,
    "raw_execution_access": "restricted_mode_0600_storage",
    "rationale_projection": "fixed_source_free_redaction",
}


class ScoringExportError(RuntimeError):
    """A finite, source-free failure safe to report."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ScoringExportError(code)


def exact_keys(value: dict[str, Any], expected: Iterable[str], label: str) -> None:
    require(set(value) == set(expected), f"{label}_keys_invalid")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value),
        f"{label}_sha256_invalid",
    )
    return value


def item_id_set_sha256(item_ids: Iterable[str]) -> str:
    ordered = sorted(item_ids)
    require(bool(ordered), "item_id_set_empty")
    require(len(ordered) == len(set(ordered)), "item_id_set_duplicate")
    return sha256_bytes(canonical_bytes(ordered))


def read_regular_bytes(path: Path) -> bytes:
    path = path.resolve(strict=False)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ScoringExportError("required_file_unavailable") from exc
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


def load_json_with_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    data = read_regular_bytes(path)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScoringExportError("invalid_json_file") from exc
    require(isinstance(value, dict), "json_root_not_object")
    return value, data


def parse_utc(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label}_utc_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ScoringExportError(f"{label}_utc_invalid") from exc
    require(parsed.tzinfo is not None, f"{label}_utc_invalid")
    return parsed.astimezone(timezone.utc)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_private_input_path(
    path: Path,
    *,
    root: Path,
    label: str,
) -> None:
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


def require_bound_manifest_path(path: Path, *, workspace: Path, label: str) -> None:
    require(path.is_absolute(), f"{label}_path_not_absolute")
    require(path.resolve(strict=False) == path, f"{label}_path_resolution_drift")
    require(is_within(path, workspace), f"{label}_outside_workspace")
    require(path.exists() and path.is_file() and not path.is_symlink(), f"{label}_invalid")


def require_storage_output_path(path: Path, *, workspace: Path) -> None:
    storage = workspace / "Storage"
    require(path.is_absolute(), "output_path_not_absolute")
    require(not path.exists() and not path.is_symlink(), "output_exists_or_symlink")
    require(path.resolve(strict=False) == path, "output_path_resolution_drift")
    require(is_within(path, storage), "output_outside_storage")
    require(
        path.parent.is_dir()
        and not path.parent.is_symlink()
        and stat.S_IMODE(path.parent.stat().st_mode) == 0o700,
        "output_parent_mode_invalid",
    )


def load_component() -> tuple[dict[str, Any], dict[str, Any], str]:
    config = reviewer.load_json(COMPONENT_FREEZE)
    try:
        assets = reviewer.validate_freeze(config, config_path=COMPONENT_FREEZE)
    except reviewer.GeneralistReviewerError as exc:
        raise ScoringExportError(f"reviewer_component_invalid:{exc}") from exc
    component_hash = sha256_bytes(read_regular_bytes(COMPONENT_FREEZE))
    return config, assets, component_hash


def validate_study_freeze(
    freeze: dict[str, Any],
    *,
    component_hash: str,
    rating_schema_hash: str,
) -> dict[str, Any]:
    exact_keys(
        freeze,
        {
            "document_type",
            "freeze_version",
            "status",
            "frozen_at_utc",
            "manuscript_eligible",
            "dataset",
            "method",
            "candidate_generation_separation",
            "authorization",
            "preaccess",
            "packet_bank",
            "truth_cluster_map",
            "evidence_records",
            "scoring",
            "assets",
        },
        "study_freeze",
    )
    require(
        freeze["document_type"] == "warrantroute_qwen3_generalist_scoring_freeze_v1",
        "study_freeze_document_type_invalid",
    )
    require(
        isinstance(freeze["freeze_version"], str) and freeze["freeze_version"],
        "study_freeze_version_invalid",
    )
    require(freeze["status"] == "authorized_frozen", "study_freeze_not_authorized")
    require(freeze["manuscript_eligible"] is True, "study_freeze_not_manuscript_eligible")
    frozen_at = parse_utc(freeze["frozen_at_utc"], "frozen_at")

    dataset = freeze["dataset"]
    exact_keys(dataset, {"corpus_id", "display_name", "split", "cluster_unit"}, "dataset")
    require(dataset["corpus_id"] == EXPECTED_CORPUS_ID, "corpus_not_dreaddit")
    require(dataset["display_name"] == EXPECTED_DATASET_DISPLAY, "dataset_display_name_invalid")
    require(dataset["split"] == EXPECTED_SPLIT, "split_not_frozen_test")
    require(dataset["cluster_unit"] == EXPECTED_CLUSTER_UNIT, "cluster_unit_not_post")

    method = freeze["method"]
    exact_keys(
        method,
        {"name", "reviewer_actor_id", "model_id", "model_digest", "primary_repetition"},
        "method",
    )
    require(method["name"] == EXPECTED_METHOD, "method_not_generalist")
    require(method["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "reviewer_actor_drift")
    require(method["model_id"] == EXPECTED_MODEL_ID, "reviewer_model_drift")
    require(method["model_digest"] == EXPECTED_MODEL_DIGEST, "reviewer_model_digest_drift")
    require(
        method["primary_repetition"] == EXPECTED_PRIMARY_REPETITION,
        "primary_repetition_drift",
    )

    separation = freeze["candidate_generation_separation"]
    exact_keys(
        separation,
        {
            "candidate_generator_actor_id",
            "candidate_generator_snapshot_sha256",
            "reviewer_generated_no_scored_items",
        },
        "candidate_generation_separation",
    )
    require(
        isinstance(separation["candidate_generator_actor_id"], str)
        and separation["candidate_generator_actor_id"]
        and separation["candidate_generator_actor_id"] != EXPECTED_REVIEWER_ACTOR,
        "candidate_generator_not_distinct",
    )
    require_sha256(
        separation["candidate_generator_snapshot_sha256"],
        "candidate_generator_snapshot",
    )
    require(
        separation["reviewer_generated_no_scored_items"] is True,
        "reviewer_generation_separation_not_attested",
    )

    authorization = freeze["authorization"]
    exact_keys(
        authorization,
        {
            "approval_record_id",
            "approval_record_sha256",
            "readiness_report_sha256",
            "approved_at_utc",
            "corpus_use_approved",
            "privacy_clearance_approved",
            "provider_scope_approved",
            "manuscript_reporting_approved",
        },
        "authorization",
    )
    require(
        isinstance(authorization["approval_record_id"], str)
        and authorization["approval_record_id"],
        "approval_record_id_missing",
    )
    require_sha256(authorization["approval_record_sha256"], "approval_record")
    require_sha256(authorization["readiness_report_sha256"], "readiness_report")
    approved_at = parse_utc(authorization["approved_at_utc"], "approved_at")
    require(approved_at <= frozen_at, "approval_after_study_freeze")
    for key in (
        "corpus_use_approved",
        "privacy_clearance_approved",
        "provider_scope_approved",
        "manuscript_reporting_approved",
    ):
        require(authorization[key] is True, f"authorization_gate_failed:{key}")

    preaccess = freeze["preaccess"]
    exact_keys(
        preaccess,
        {
            "record_id",
            "record_sha256",
            "recorded_at_utc",
            "heldout_unopened",
            "recorded_before_first_access",
        },
        "preaccess",
    )
    require(
        isinstance(preaccess["record_id"], str) and preaccess["record_id"],
        "preaccess_record_id_missing",
    )
    require_sha256(preaccess["record_sha256"], "preaccess_record")
    preaccess_at = parse_utc(preaccess["recorded_at_utc"], "preaccess_recorded_at")
    require(preaccess_at <= frozen_at, "preaccess_record_after_study_freeze")
    require(preaccess["heldout_unopened"] is True, "heldout_not_clean_at_freeze")
    require(
        preaccess["recorded_before_first_access"] is True,
        "preaccess_timing_not_attested",
    )

    packet_bank = freeze["packet_bank"]
    exact_keys(
        packet_bank,
        {
            "seal_id",
            "seal_sha256",
            "item_count",
            "item_id_set_sha256",
            "privacy_cleared",
            "complete",
        },
        "packet_bank",
    )
    require(
        isinstance(packet_bank["seal_id"], str) and packet_bank["seal_id"],
        "packet_bank_seal_id_missing",
    )
    require_sha256(packet_bank["seal_sha256"], "packet_bank_seal")
    require(
        isinstance(packet_bank["item_count"], int) and packet_bank["item_count"] > 0,
        "packet_bank_item_count_invalid",
    )
    require_sha256(packet_bank["item_id_set_sha256"], "packet_bank_item_id_set")
    require(packet_bank["privacy_cleared"] is True, "packet_bank_not_privacy_cleared")
    require(packet_bank["complete"] is True, "packet_bank_incomplete")

    truth = freeze["truth_cluster_map"]
    exact_keys(truth, {"sha256", "item_count", "sealed"}, "truth_cluster_map")
    require_sha256(truth["sha256"], "truth_cluster_map")
    require(truth["item_count"] == packet_bank["item_count"], "truth_item_count_drift")
    require(truth["sealed"] is True, "truth_cluster_map_unsealed")

    evidence = freeze["evidence_records"]
    exact_keys(
        evidence,
        {
            "governance_record_sha256",
            "reviewer_registry_sha256",
            "privacy_review_log_sha256",
            "source_receipt_sha256",
            "study_manifest_sha256",
            "packet_study_freeze_sha256",
        },
        "evidence_records",
    )
    for key, value in evidence.items():
        require_sha256(value, f"evidence_record:{key}")
    require(
        evidence["governance_record_sha256"] == authorization["approval_record_sha256"],
        "governance_authorization_hash_drift",
    )

    scoring = freeze["scoring"]
    exact_keys(
        scoring,
        {
            "metric",
            "denominator",
            "hit_rule",
            "failure_rule",
            "ci_method",
            "confidence_level",
            "bootstrap_resamples",
            "bootstrap_seed",
            "bootstrap_cluster_unit",
            "minimum_independent_clusters",
        },
        "scoring",
    )
    require(scoring["metric"] == EXPECTED_METRIC, "metric_drift")
    require(scoring["denominator"] == "all_frozen_items", "denominator_drift")
    require(
        scoring["hit_rule"] == "valid_empty_cannot_judge_and_required_flag_present",
        "hit_rule_drift",
    )
    require(
        scoring["failure_rule"] == "all_other_outcomes_are_misses_without_replacement",
        "failure_rule_drift",
    )
    require(scoring["ci_method"] == "cluster_bootstrap_percentile", "ci_method_drift")
    require(scoring["confidence_level"] == 0.95, "confidence_level_drift")
    require(scoring["bootstrap_resamples"] == EXPECTED_RESAMPLES, "resample_count_drift")
    require(scoring["bootstrap_seed"] == EXPECTED_BOOTSTRAP_SEED, "bootstrap_seed_drift")
    require(
        scoring["bootstrap_cluster_unit"] == EXPECTED_BOOTSTRAP_CLUSTER_UNIT,
        "bootstrap_cluster_unit_drift",
    )
    require(
        scoring["minimum_independent_clusters"] == EXPECTED_MINIMUM_CLUSTERS,
        "minimum_cluster_count_drift",
    )

    assets = freeze["assets"]
    exact_keys(
        assets,
        {
            "reviewer_component_freeze_sha256",
            "shared_rating_schema_sha256",
            "scoring_exporter_sha256",
            "scoring_contract_sha256",
            "formal_runner_sha256",
            "formal_runner_contract_sha256",
        },
        "assets",
    )
    require(
        require_sha256(assets["reviewer_component_freeze_sha256"], "component_freeze")
        == component_hash,
        "component_freeze_hash_drift",
    )
    require(
        require_sha256(assets["shared_rating_schema_sha256"], "rating_schema")
        == rating_schema_hash,
        "rating_schema_hash_drift",
    )
    require(
        require_sha256(assets["scoring_exporter_sha256"], "scoring_exporter")
        == sha256_bytes(read_regular_bytes(SCRIPT)),
        "scoring_exporter_hash_drift",
    )
    require(
        require_sha256(assets["scoring_contract_sha256"], "scoring_contract")
        == sha256_bytes(read_regular_bytes(CONTRACT)),
        "scoring_contract_hash_drift",
    )
    require(
        require_sha256(assets["formal_runner_sha256"], "formal_runner")
        == sha256_bytes(read_regular_bytes(FORMAL_RUNNER)),
        "formal_runner_hash_drift",
    )
    require(
        require_sha256(assets["formal_runner_contract_sha256"], "formal_runner_contract")
        == sha256_bytes(read_regular_bytes(FORMAL_RUNNER_CONTRACT)),
        "formal_runner_contract_hash_drift",
    )
    return {"frozen_at": frozen_at}


def validate_readiness_report(
    report: dict[str, Any],
    *,
    report_bytes: bytes,
    freeze: dict[str, Any],
    frozen_at: datetime,
) -> str:
    exact_keys(
        report,
        {
            "document_type",
            "report_version",
            "assessment_as_of_utc",
            "source_record_sha256",
            "record_status",
            "gate_mode",
            "synthetic_lane_runnable",
            "contains_real_source_text",
            "exact_required_gate_count",
            "required_gate_ids",
            "all_real_corpora_ready",
            "corpora",
            "reviewer_registry",
            "privacy_review_log",
            "warning_codes",
        },
        "readiness_report",
    )
    require(
        report["document_type"] == "warrantroute_readiness_report",
        "readiness_document_type_invalid",
    )
    require(
        report["report_version"] == "warrantroute-readiness-report-v1",
        "readiness_report_version_invalid",
    )
    require(report["gate_mode"] == "real_text_candidate", "readiness_not_formal_mode")
    require(report["record_status"] == "local_evidence_record", "readiness_not_local_evidence")
    require(report["contains_real_source_text"] is False, "readiness_report_contains_source_text")
    require(
        parse_utc(report["assessment_as_of_utc"], "readiness_assessment_as_of") <= frozen_at,
        "readiness_assessment_after_study_freeze",
    )
    report_hash = sha256_bytes(report_bytes)
    require(
        report_hash == freeze["authorization"]["readiness_report_sha256"],
        "readiness_report_hash_drift",
    )
    source_record_hash = require_sha256(
        report["source_record_sha256"],
        "readiness_source_record",
    )
    require(
        source_record_hash == freeze["authorization"]["approval_record_sha256"],
        "readiness_source_record_not_authorization_record",
    )
    require(
        report["exact_required_gate_count"] == len(REQUIRED_GATE_IDS),
        "readiness_exact_gate_count_drift",
    )
    require(
        report["required_gate_ids"] == list(REQUIRED_GATE_IDS),
        "readiness_required_gate_ids_drift",
    )
    require(
        report["warning_codes"] == list(FORMAL_WARNING_CODES),
        "readiness_warning_codes_not_formal",
    )
    require("personal_local_only" not in report, "personal_local_readiness_rejected")

    corpora = report["corpora"]
    require(isinstance(corpora, dict), "readiness_corpora_invalid")
    dreaddit = corpora.get(EXPECTED_CORPUS_ID)
    require(isinstance(dreaddit, dict), "dreaddit_readiness_missing")
    require(dreaddit.get("required_gate_count") == 10, "dreaddit_required_gate_count_not_10")
    require(dreaddit.get("completed_gate_count") == 10, "dreaddit_completed_gate_count_not_10")
    require(dreaddit.get("real_text_ready") is True, "dreaddit_real_text_not_ready")
    gates = dreaddit.get("gates")
    require(isinstance(gates, list) and len(gates) == 10, "dreaddit_gate_records_not_10")
    observed_ids: list[str] = []
    for index, gate in enumerate(gates):
        require(isinstance(gate, dict), f"dreaddit_gate_not_object:{index}")
        exact_keys(
            gate,
            {"id", "complete", "blocking_reason_codes"},
            f"dreaddit_gate:{index}",
        )
        gate_id = gate["id"]
        require(isinstance(gate_id, str), f"dreaddit_gate_id_invalid:{index}")
        observed_ids.append(gate_id)
        require(gate["complete"] is True, f"dreaddit_gate_incomplete:{gate_id}")
        require(gate["blocking_reason_codes"] == [], f"dreaddit_gate_blocked:{gate_id}")
    require(len(set(observed_ids)) == 10, "dreaddit_gate_ids_not_unique")
    require(set(observed_ids) == set(REQUIRED_GATE_IDS), "dreaddit_gate_ids_incorrect")
    return report_hash


def load_readiness_checker() -> Any:
    spec = importlib.util.spec_from_file_location(
        "warrantroute_scoring_readiness_checker",
        READINESS_CHECKER,
    )
    require(spec is not None and spec.loader is not None, "readiness_checker_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rerun_formal_readiness(
    *,
    governance_record: dict[str, Any],
    governance_record_hash: str,
    reviewer_registry: dict[str, Any],
    privacy_log: dict[str, Any],
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    checker = load_readiness_checker()
    try:
        checker.validate_record_shape(governance_record)
        reviewers = checker.validate_reviewer_registry(reviewer_registry, template_ok=False)
        privacy_records = checker.validate_privacy_log(privacy_log, template_ok=False)
        assessment = checker.parse_utc(
            readiness_report["assessment_as_of_utc"],
            "scoring readiness assessment",
        )
        regenerated = checker.build_report(
            governance_record,
            governance_record_hash,
            assessment,
            reviewers,
            privacy_records,
        )
    except Exception as exc:
        raise ScoringExportError("readiness_evidence_rerun_failed") from exc
    require(regenerated == readiness_report, "readiness_report_not_reproducible")
    return regenerated


def validate_evidence_records(
    *,
    freeze: dict[str, Any],
    readiness_report: dict[str, Any],
    governance_record: dict[str, Any],
    governance_bytes: bytes,
    reviewer_registry: dict[str, Any],
    reviewer_registry_bytes: bytes,
    privacy_log: dict[str, Any],
    privacy_log_bytes: bytes,
    preaccess_record: dict[str, Any],
    preaccess_bytes: bytes,
    source_receipt_path: Path,
    source_receipt_bytes: bytes,
    study_manifest_path: Path,
    study_manifest_bytes: bytes,
    packet_study_freeze: dict[str, Any],
    packet_study_freeze_bytes: bytes,
    packet_study_freeze_schema: dict[str, Any],
    packet_seal: dict[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    evidence = freeze["evidence_records"]
    observed_hashes = {
        "governance_record_sha256": sha256_bytes(governance_bytes),
        "reviewer_registry_sha256": sha256_bytes(reviewer_registry_bytes),
        "privacy_review_log_sha256": sha256_bytes(privacy_log_bytes),
        "source_receipt_sha256": sha256_bytes(source_receipt_bytes),
        "study_manifest_sha256": sha256_bytes(study_manifest_bytes),
        "packet_study_freeze_sha256": sha256_bytes(packet_study_freeze_bytes),
    }
    require(observed_hashes == evidence, "evidence_record_hash_drift")
    require(
        observed_hashes["governance_record_sha256"]
        == readiness_report["source_record_sha256"]
        == freeze["authorization"]["approval_record_sha256"],
        "governance_record_chain_drift",
    )
    require(
        governance_record.get("record_status") == "local_evidence_record"
        and governance_record.get("gate_mode") == "real_text_candidate",
        "governance_record_not_formal",
    )
    require(
        governance_record.get("record_id") == freeze["authorization"]["approval_record_id"],
        "governance_record_id_drift",
    )
    rerun_formal_readiness(
        governance_record=governance_record,
        governance_record_hash=observed_hashes["governance_record_sha256"],
        reviewer_registry=reviewer_registry,
        privacy_log=privacy_log,
        readiness_report=readiness_report,
    )

    lane = governance_record.get("corpus_lanes", {}).get(EXPECTED_CORPUS_ID)
    require(isinstance(lane, dict), "governance_dreaddit_lane_missing")
    gates = {gate.get("id"): gate for gate in lane.get("gates", []) if isinstance(gate, dict)}
    input_gate = gates.get("exact_corpus_input_contract")
    manifest_gate = gates.get("frozen_study_manifest")
    require(isinstance(input_gate, dict), "source_receipt_gate_missing")
    require(isinstance(manifest_gate, dict), "study_manifest_gate_missing")
    input_details = input_gate.get("details", {})
    manifest_details = manifest_gate.get("details", {})
    require(
        input_details.get("source_receipt_sha256")
        == observed_hashes["source_receipt_sha256"],
        "source_receipt_governance_hash_drift",
    )
    require(
        manifest_details.get("study_manifest_sha256")
        == observed_hashes["study_manifest_sha256"],
        "study_manifest_governance_hash_drift",
    )
    source_reference = str(source_receipt_path.relative_to(workspace))
    manifest_reference = str(study_manifest_path.relative_to(workspace))
    require(
        input_details.get("source_receipt_reference") == source_reference
        and lane.get("source_receipt_reference") == source_reference,
        "source_receipt_reference_drift",
    )
    require(
        manifest_details.get("study_manifest_reference") == manifest_reference,
        "study_manifest_reference_drift",
    )

    require(
        packet_seal["bindings"]["privacy_review_log_sha256"]
        == observed_hashes["privacy_review_log_sha256"],
        "packet_seal_privacy_log_drift",
    )
    try:
        jsonschema.Draft202012Validator(packet_study_freeze_schema).validate(
            packet_study_freeze
        )
    except jsonschema.ValidationError as exc:
        raise ScoringExportError("packet_study_freeze_schema_invalid") from exc
    require(
        packet_seal["bindings"]["study_freeze_sha256"]
        == observed_hashes["packet_study_freeze_sha256"],
        "packet_seal_study_freeze_drift",
    )
    require(
        packet_seal["bindings"]["packet_study_freeze_sha256"]
        == observed_hashes["packet_study_freeze_sha256"],
        "packet_seal_packet_study_freeze_drift",
    )
    require(
        packet_seal["bindings"]["governance_record_sha256"]
        == observed_hashes["governance_record_sha256"]
        == packet_seal["bindings"]["governance_source_record_sha256"],
        "packet_seal_governance_record_drift",
    )
    require(
        packet_seal["bindings"]["reviewer_registry_sha256"]
        == observed_hashes["reviewer_registry_sha256"],
        "packet_seal_reviewer_registry_drift",
    )
    require(
        packet_seal["bindings"]["source_receipt_sha256"]
        == observed_hashes["source_receipt_sha256"],
        "packet_seal_source_receipt_drift",
    )
    require(
        packet_seal["bindings"]["packet_manifest_sha256"]
        == observed_hashes["study_manifest_sha256"],
        "packet_seal_manifest_drift",
    )
    require(
        packet_seal["bindings"]["preaccess_record_sha256"]
        == freeze["preaccess"]["record_sha256"],
        "packet_seal_preaccess_record_drift",
    )
    require(
        packet_study_freeze["bindings"]["readiness_report_sha256"]
        == freeze["authorization"]["readiness_report_sha256"],
        "packet_study_freeze_readiness_drift",
    )
    require(
        packet_study_freeze["bindings"]["governance_source_record_sha256"]
        == observed_hashes["governance_record_sha256"],
        "packet_study_freeze_governance_drift",
    )
    require(
        packet_study_freeze["bindings"]["privacy_review_log_sha256"]
        == observed_hashes["privacy_review_log_sha256"],
        "packet_study_freeze_privacy_drift",
    )
    require(
        packet_study_freeze["bindings"]["governance_record_sha256"]
        == observed_hashes["governance_record_sha256"],
        "packet_study_freeze_governance_record_drift",
    )
    require(
        packet_study_freeze["bindings"]["reviewer_registry_sha256"]
        == observed_hashes["reviewer_registry_sha256"],
        "packet_study_freeze_reviewer_registry_drift",
    )
    require(
        packet_study_freeze["bindings"]["source_receipt_sha256"]
        == observed_hashes["source_receipt_sha256"],
        "packet_study_freeze_source_receipt_drift",
    )
    require(
        packet_study_freeze["bindings"]["packet_manifest_sha256"]
        == observed_hashes["study_manifest_sha256"],
        "packet_study_freeze_manifest_drift",
    )
    require(
        packet_study_freeze["bindings"]["packet_bank_sha256"]
        == packet_seal["bindings"]["packet_bank_sha256"],
        "packet_study_freeze_packet_bank_drift",
    )
    require(
        packet_study_freeze["bindings"]["truth_cluster_map_sha256"]
        == packet_seal["bindings"]["truth_cluster_map_sha256"],
        "packet_study_freeze_truth_map_drift",
    )
    require(
        packet_study_freeze["bindings"]["heldout_preaccess_record_sha256"]
        == freeze["preaccess"]["record_sha256"],
        "packet_study_freeze_preaccess_drift",
    )
    generator = packet_study_freeze["actors"]["candidate_generator"]
    require(
        generator["actor_id"]
        == freeze["candidate_generation_separation"]["candidate_generator_actor_id"]
        == packet_seal["candidate_generator_actor_id"],
        "candidate_generator_actor_chain_drift",
    )
    require(
        generator["snapshot_sha256"]
        == freeze["candidate_generation_separation"]["candidate_generator_snapshot_sha256"],
        "candidate_generator_snapshot_chain_drift",
    )
    require_sha256(generator["prompt_sha256"], "candidate_generator_prompt")
    require(isinstance(generator["model_id"], str) and generator["model_id"], "candidate_generator_model_missing")
    require(
        packet_seal["candidate_generator_model_id"] == generator["model_id"],
        "candidate_generator_model_chain_drift",
    )
    require(
        packet_seal["candidate_generator_snapshot_sha256"]
        == generator["snapshot_sha256"],
        "candidate_generator_snapshot_seal_drift",
    )
    require(
        packet_seal["candidate_generator_prompt_sha256"]
        == generator["prompt_sha256"],
        "candidate_generator_prompt_chain_drift",
    )
    require(
        packet_study_freeze["actors"]["reviewer"]["model_snapshot_sha256"]
        == packet_seal["reviewer_model_snapshot_sha256"]
        == EXPECTED_MODEL_DIGEST,
        "reviewer_model_snapshot_chain_drift",
    )

    exact_keys(
        preaccess_record,
        {
            "document_type",
            "record_id",
            "recorded_at_utc",
            "contains_source_text",
            "heldout_unopened",
            "recorded_before_first_access",
            "study_id",
            "packet_bank_sha256",
        },
        "preaccess_record",
    )
    require(
        preaccess_record["document_type"] == "warrantroute_heldout_preaccess_record_v1",
        "preaccess_document_type_invalid",
    )
    require(sha256_bytes(preaccess_bytes) == freeze["preaccess"]["record_sha256"], "preaccess_hash_drift")
    require(preaccess_record["record_id"] == freeze["preaccess"]["record_id"], "preaccess_id_drift")
    require(preaccess_record["recorded_at_utc"] == freeze["preaccess"]["recorded_at_utc"], "preaccess_time_drift")
    require(preaccess_record["contains_source_text"] is False, "preaccess_contains_source_text")
    require(preaccess_record["heldout_unopened"] is True, "preaccess_not_clean")
    require(preaccess_record["recorded_before_first_access"] is True, "preaccess_not_before_access")
    require(preaccess_record["study_id"] == packet_seal["study_id"], "preaccess_study_id_drift")
    require(
        preaccess_record["packet_bank_sha256"] == packet_seal["bindings"]["packet_bank_sha256"],
        "preaccess_packet_bank_drift",
    )
    return {
        **observed_hashes,
        "candidate_generator_model_id": generator["model_id"],
        "candidate_generator_snapshot_sha256": generator["snapshot_sha256"],
        "candidate_generator_prompt_sha256": generator["prompt_sha256"],
        "external_signature_verified": False,
    }


def validate_packet_bank_seal(
    seal: dict[str, Any],
    *,
    seal_bytes: bytes,
    freeze: dict[str, Any],
    readiness_report_hash: str,
    truth_map_hash: str,
    component_hash: str,
    evaluator_schema_hash: str,
    truth_schema_hash: str,
    packet_freeze_schema_hash: str,
) -> str:
    exact_keys(
        seal,
        {
            "document_type",
            "seal_version",
            "seal_id",
            "seal_status",
            "authorization_claimed_by_this_seal",
            "contains_source_text",
            "manuscript_result",
            "study_id",
            "corpus_id",
            "official_source_split",
            "evaluation_role",
            "reviewer_actor_id",
            "reviewer_model_id",
            "reviewer_model_snapshot_sha256",
            "candidate_generator_actor_id",
            "candidate_generator_model_id",
            "candidate_generator_snapshot_sha256",
            "candidate_generator_prompt_sha256",
            "fixed_n",
            "item_count",
            "item_id_set_sha256",
            "packet_bank_complete",
            "privacy_cleared",
            "family_counts",
            "post_cluster_count",
            "privacy_cleared_excerpt_count",
            "formal_dreaddit_gates_verified",
            "bindings",
            "warning",
        },
        "packet_bank_seal",
    )
    require(
        seal["document_type"] == "warrantroute_qwen3_generalist_packet_bank_seal",
        "packet_seal_document_type_invalid",
    )
    require(
        seal["seal_version"] == "qwen3-generalist-packet-bank-seal-v1",
        "packet_seal_version_invalid",
    )
    require(
        sha256_bytes(seal_bytes) == freeze["packet_bank"]["seal_sha256"],
        "packet_seal_hash_drift",
    )
    bindings = seal["bindings"]
    exact_keys(
        bindings,
        {
            "study_freeze_sha256",
            "packet_study_freeze_sha256",
            "study_design_freeze_sha256",
            "readiness_report_sha256",
            "governance_record_sha256",
            "governance_source_record_sha256",
            "reviewer_registry_sha256",
            "privacy_review_log_sha256",
            "packet_manifest_sha256",
            "source_receipt_sha256",
            "source_test_file_sha256",
            "preaccess_record_sha256",
            "verification_bundle_sha256",
            "verification_seal_sha256",
            "candidate_generator_snapshot_sha256",
            "candidate_generator_prompt_sha256",
            "reviewer_model_snapshot_sha256",
            "packet_bank_sha256",
            "truth_cluster_map_sha256",
            "study_freeze_schema_sha256",
            "truth_cluster_map_schema_sha256",
            "packet_manifest_schema_sha256",
            "preaccess_record_schema_sha256",
            "verification_bundle_schema_sha256",
            "verification_seal_schema_sha256",
            "evaluator_item_schema_sha256",
            "generalist_component_freeze_sha256",
            "scoring_contract_sha256",
            "analysis_code_sha256",
            "heldout_preaccess_record_sha256",
        },
        "packet_seal_bindings",
    )
    for key, value in bindings.items():
        require_sha256(value, f"packet_seal_binding:{key}")
    expected_seal_id = f"QGPB_{bindings['packet_bank_sha256'][:16].upper()}"
    require(seal["seal_id"] == expected_seal_id, "packet_seal_id_not_deterministic")
    require(seal["seal_id"] == freeze["packet_bank"]["seal_id"], "packet_seal_id_drift")
    require(
        seal["seal_status"] == "integrity_validated_not_authorization",
        "packet_seal_status_invalid",
    )
    require(
        seal["authorization_claimed_by_this_seal"] is False,
        "packet_seal_claims_authorization",
    )
    require(seal["contains_source_text"] is False, "packet_seal_contains_source_text")
    require(seal["manuscript_result"] is False, "packet_seal_claims_result")
    require(isinstance(seal["study_id"], str) and seal["study_id"], "packet_seal_study_id_invalid")
    require(seal["corpus_id"] == EXPECTED_CORPUS_ID, "packet_seal_corpus_drift")
    require(seal["official_source_split"] == EXPECTED_SPLIT, "packet_seal_split_drift")
    require(seal["evaluation_role"] == "in_domain_audit", "packet_seal_role_drift")
    require(seal["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "packet_seal_reviewer_drift")
    require(seal["reviewer_model_id"] == EXPECTED_MODEL_ID, "packet_seal_model_drift")
    require(
        seal["reviewer_model_snapshot_sha256"] == EXPECTED_MODEL_DIGEST,
        "packet_seal_reviewer_snapshot_drift",
    )
    require(
        seal["candidate_generator_actor_id"]
        == freeze["candidate_generation_separation"]["candidate_generator_actor_id"],
        "packet_seal_generator_drift",
    )
    require(
        seal["candidate_generator_snapshot_sha256"]
        == freeze["candidate_generation_separation"][
            "candidate_generator_snapshot_sha256"
        ],
        "packet_seal_generator_snapshot_drift",
    )
    require(
        isinstance(seal["candidate_generator_model_id"], str)
        and seal["candidate_generator_model_id"],
        "packet_seal_generator_model_missing",
    )
    require_sha256(
        seal["candidate_generator_prompt_sha256"],
        "packet_seal_generator_prompt",
    )
    expected_n = freeze["packet_bank"]["item_count"]
    require(seal["fixed_n"] == expected_n, "packet_seal_fixed_n_drift")
    require(seal["item_count"] == expected_n, "packet_seal_item_count_drift")
    require(
        seal["item_id_set_sha256"] == freeze["packet_bank"]["item_id_set_sha256"],
        "packet_seal_item_set_drift",
    )
    require_sha256(seal["item_id_set_sha256"], "packet_seal_item_id_set")
    require(seal["packet_bank_complete"] is True, "packet_seal_bank_incomplete")
    require(seal["privacy_cleared"] is True, "packet_seal_privacy_not_cleared")
    family_counts = seal["family_counts"]
    require(isinstance(family_counts, dict), "packet_seal_family_counts_invalid")
    require(set(family_counts) == set(EXPECTED_FAMILY_TO_FLAG), "packet_seal_family_set_invalid")
    require(
        all(isinstance(value, int) and value >= 1 for value in family_counts.values()),
        "packet_seal_family_count_invalid",
    )
    require(sum(family_counts.values()) == expected_n, "packet_seal_family_count_sum_drift")
    require(
        isinstance(seal["post_cluster_count"], int)
        and seal["post_cluster_count"] >= expected_n,
        "packet_seal_post_cluster_count_invalid",
    )
    require(
        isinstance(seal["privacy_cleared_excerpt_count"], int)
        and seal["privacy_cleared_excerpt_count"] >= expected_n,
        "packet_seal_privacy_excerpt_count_invalid",
    )
    require(
        seal["formal_dreaddit_gates_verified"] == "10/10",
        "packet_seal_formal_gate_attestation_invalid",
    )
    require(bindings["readiness_report_sha256"] == readiness_report_hash, "packet_seal_readiness_drift")
    require(bindings["truth_cluster_map_sha256"] == truth_map_hash, "packet_seal_truth_map_drift")
    require(
        bindings["generalist_component_freeze_sha256"] == component_hash,
        "packet_seal_component_drift",
    )
    require(
        bindings["scoring_contract_sha256"] == freeze["assets"]["scoring_contract_sha256"],
        "packet_seal_scoring_contract_drift",
    )
    require(
        bindings["analysis_code_sha256"] == freeze["assets"]["scoring_exporter_sha256"],
        "packet_seal_analysis_code_drift",
    )
    require(
        bindings["heldout_preaccess_record_sha256"] == freeze["preaccess"]["record_sha256"],
        "packet_seal_preaccess_drift",
    )
    require(
        bindings["evaluator_item_schema_sha256"] == evaluator_schema_hash,
        "packet_seal_evaluator_schema_drift",
    )
    require(
        bindings["truth_cluster_map_schema_sha256"] == truth_schema_hash,
        "packet_seal_truth_schema_drift",
    )
    require(
        bindings["study_freeze_schema_sha256"] == packet_freeze_schema_hash,
        "packet_seal_study_freeze_schema_drift",
    )
    require(
        bindings["packet_study_freeze_sha256"]
        == bindings["study_freeze_sha256"],
        "packet_seal_packet_study_freeze_alias_drift",
    )
    require(
        bindings["governance_source_record_sha256"]
        == bindings["governance_record_sha256"],
        "packet_seal_governance_alias_drift",
    )
    require(
        bindings["preaccess_record_sha256"]
        == bindings["heldout_preaccess_record_sha256"],
        "packet_seal_preaccess_alias_drift",
    )
    require(
        bindings["candidate_generator_snapshot_sha256"]
        == seal["candidate_generator_snapshot_sha256"],
        "packet_seal_generator_snapshot_binding_drift",
    )
    require(
        bindings["candidate_generator_prompt_sha256"]
        == seal["candidate_generator_prompt_sha256"],
        "packet_seal_generator_prompt_binding_drift",
    )
    require(
        bindings["reviewer_model_snapshot_sha256"]
        == seal["reviewer_model_snapshot_sha256"],
        "packet_seal_reviewer_snapshot_binding_drift",
    )
    require(
        bindings["packet_manifest_schema_sha256"]
        == sha256_bytes(read_regular_bytes(PACKET_MANIFEST_SCHEMA)),
        "packet_seal_manifest_schema_drift",
    )
    require(
        bindings["preaccess_record_schema_sha256"]
        == sha256_bytes(read_regular_bytes(PREACCESS_RECORD_SCHEMA)),
        "packet_seal_preaccess_schema_drift",
    )
    require(
        bindings["verification_bundle_schema_sha256"]
        == sha256_bytes(read_regular_bytes(VERIFICATION_BUNDLE_SCHEMA)),
        "packet_seal_verification_bundle_schema_drift",
    )
    require(
        bindings["verification_seal_schema_sha256"]
        == sha256_bytes(read_regular_bytes(VERIFICATION_SEAL_SCHEMA)),
        "packet_seal_verification_seal_schema_drift",
    )
    require(
        seal["warning"]
        == (
            "This seal confirms integrity and declared coverage only. It does not grant "
            "authorization and is not a score, result, or manuscript value."
        ),
        "packet_seal_warning_drift",
    )
    return sha256_bytes(seal_bytes)


def validate_truth_map(
    truth: dict[str, Any],
    *,
    freeze: dict[str, Any],
    truth_bytes: bytes,
    truth_schema: dict[str, Any],
    packet_seal: dict[str, Any],
    allowed_flags: set[str],
) -> list[dict[str, str]]:
    try:
        jsonschema.Draft202012Validator(truth_schema).validate(truth)
    except jsonschema.ValidationError as exc:
        raise ScoringExportError("truth_cluster_map_schema_invalid") from exc
    require(
        truth["document_type"] == "warrantroute_qwen3_generalist_truth_cluster_map",
        "truth_map_document_type_invalid",
    )
    require(
        truth["schema_version"] == "qwen3-generalist-truth-cluster-map-v1",
        "truth_map_schema_version_invalid",
    )
    require(truth["study_id"] == packet_seal["study_id"], "truth_map_study_id_drift")
    require(truth["corpus_id"] == EXPECTED_CORPUS_ID, "truth_corpus_drift")
    require(truth["official_source_split"] == EXPECTED_SPLIT, "truth_split_drift")
    require(truth["evaluation_role"] == "in_domain_audit", "truth_evaluation_role_drift")
    require(truth["cluster_unit"] == EXPECTED_CLUSTER_UNIT, "truth_cluster_unit_drift")
    require(truth["contains_source_text"] is False, "truth_map_contains_source_text")
    require(
        truth["access"] == "coordinator_only_until_scoring_lock",
        "truth_map_access_status_drift",
    )
    truth_hash = sha256_bytes(truth_bytes)
    require(
        truth_hash == freeze["truth_cluster_map"]["sha256"],
        "truth_map_hash_drift",
    )
    require(
        truth_hash == packet_seal["bindings"]["truth_cluster_map_sha256"],
        "truth_map_not_bound_by_packet_seal",
    )
    records = truth["items"]
    require(isinstance(records, list) and records, "truth_records_empty")
    require(
        len(records) == freeze["truth_cluster_map"]["item_count"],
        "truth_record_count_drift",
    )
    normalized: list[dict[str, str]] = []
    item_ids: set[str] = set()
    base_packet_ids: set[str] = set()
    post_cluster_ids: set[str] = set()
    family_counts: Counter[str] = Counter()
    for index, row in enumerate(records):
        item_id = row["item_id"]
        base_packet_id = row["base_packet_id"]
        family = row["error_family"]
        required_flag = row["required_flag"]
        require(item_id not in item_ids, "truth_item_id_duplicate")
        require(required_flag in allowed_flags, f"required_flag_invalid:{index}")
        require(
            required_flag == EXPECTED_FAMILY_TO_FLAG[family],
            f"truth_family_to_flag_mapping_invalid:{index}",
        )
        require(
            row["candidate_generator_actor_id"]
            == freeze["candidate_generation_separation"]["candidate_generator_actor_id"],
            f"truth_candidate_generator_drift:{index}",
        )
        require(base_packet_id not in base_packet_ids, "truth_base_packet_id_duplicate")
        for cluster in row["post_clusters"]:
            cluster_id = cluster["cluster_id"]
            require(cluster_id not in post_cluster_ids, "truth_post_cluster_reused")
            require(
                set(cluster["sampling_frame_member_sha256s"])
                == set(cluster["packet_member_sha256s"]),
                "truth_incomplete_post_cluster",
            )
            post_cluster_ids.add(cluster_id)
        item_ids.add(item_id)
        base_packet_ids.add(base_packet_id)
        family_counts[family] += 1
        normalized.append(
            {
                "item_id": item_id,
                "cluster_id": base_packet_id,
                "required_flag": required_flag,
            }
        )
    require(
        item_id_set_sha256(item_ids) == packet_seal["item_id_set_sha256"],
        "truth_packet_bank_item_set_mismatch",
    )
    require(
        dict(sorted(family_counts.items())) == packet_seal["family_counts"],
        "truth_packet_seal_family_counts_mismatch",
    )
    require(
        len(post_cluster_ids) == packet_seal["post_cluster_count"],
        "truth_packet_seal_post_cluster_count_mismatch",
    )
    require(
        len(base_packet_ids) >= freeze["scoring"]["minimum_independent_clusters"],
        "fewer_than_minimum_independent_clusters",
    )
    return normalized


def validate_observation_bundle(
    bundle: dict[str, Any],
    *,
    freeze: dict[str, Any],
    freeze_hash: str,
    rating_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    exact_keys(
        bundle,
        {
            "document_type",
            "study_freeze_sha256",
            "corpus_id",
            "split",
            "method",
            "reviewer_actor_id",
            "model_id",
            "model_digest",
            "primary_repetition",
            "records",
        },
        "observation_bundle",
    )
    require(
        bundle["document_type"] == "warrantroute_qwen3_generalist_observation_bundle_v1",
        "observation_bundle_document_type_invalid",
    )
    require(bundle["study_freeze_sha256"] == freeze_hash, "observation_freeze_hash_drift")
    require(bundle["corpus_id"] == EXPECTED_CORPUS_ID, "observation_corpus_drift")
    require(bundle["split"] == EXPECTED_SPLIT, "observation_split_drift")
    require(bundle["method"] == EXPECTED_METHOD, "observation_method_drift")
    require(bundle["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "observation_actor_drift")
    require(bundle["model_id"] == EXPECTED_MODEL_ID, "observation_model_drift")
    require(bundle["model_digest"] == EXPECTED_MODEL_DIGEST, "observation_model_digest_drift")
    require(
        bundle["primary_repetition"] == EXPECTED_PRIMARY_REPETITION,
        "observation_primary_repetition_drift",
    )
    records = bundle["records"]
    require(isinstance(records, list) and records, "observation_records_empty")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    validator = jsonschema.Draft202012Validator(rating_schema)
    for index, row in enumerate(records):
        require(isinstance(row, dict), f"observation_record_not_object:{index}")
        exact_keys(
            row,
            {
                "item_id",
                "rating_repetition",
                "terminal_status",
                "rating",
                "private_execution_record_sha256",
            },
            f"observation_record:{index}",
        )
        item_id = row["item_id"]
        status = row["terminal_status"]
        require(isinstance(item_id, str) and item_id, f"observation_item_id_invalid:{index}")
        require(item_id not in seen, "observation_item_id_duplicate")
        require(
            row["rating_repetition"] == EXPECTED_PRIMARY_REPETITION,
            "nonprimary_observation_in_scoring_bundle",
        )
        require(status in TERMINAL_STATUSES, f"terminal_status_invalid:{index}")
        require_sha256(row["private_execution_record_sha256"], "private_execution_record")
        rating = row["rating"]
        if status == "valid_rating":
            require(isinstance(rating, dict), "valid_status_without_rating")
            try:
                validator.validate(rating)
            except jsonschema.ValidationError as exc:
                raise ScoringExportError("valid_status_rating_schema_failure") from exc
        else:
            require(rating is None, "failed_status_contains_rating")
        seen.add(item_id)
        normalized.append(
            {
                "item_id": item_id,
                "rating_repetition": row["rating_repetition"],
                "terminal_status": status,
                "rating": rating,
                "private_execution_record_sha256": row[
                    "private_execution_record_sha256"
                ],
            }
        )
    require(
        len(normalized) == freeze["packet_bank"]["item_count"],
        "observation_record_count_drift",
    )
    return normalized


def validate_observation_seal(
    seal: dict[str, Any],
    *,
    seal_bytes: bytes,
    bundle_bytes: bytes,
    freeze: dict[str, Any],
    freeze_hash: str,
    frozen_at: datetime,
) -> str:
    exact_keys(
        seal,
        {
            "document_type",
            "seal_version",
            "seal_id",
            "status",
            "sealed_at_utc",
            "study_freeze_sha256",
            "execution_freeze_sha256",
            "packet_bank_seal_sha256",
            "raw_execution_bundle_sha256",
            "raw_execution_seal_sha256",
            "runner_sha256",
            "runner_contract_sha256",
            "primary_raw_record_hash_map_sha256",
            "primary_raw_record_hash_set_sha256",
            "observation_bundle_sha256",
            "record_count",
            "all_frozen_items_terminal",
            "source_text_included",
        },
        "observation_seal",
    )
    require(
        seal["document_type"] == "warrantroute_qwen3_generalist_observation_seal_v2",
        "observation_seal_document_type_invalid",
    )
    require(
        seal["seal_version"] == "qwen3-generalist-observation-seal-v2",
        "observation_seal_version_invalid",
    )
    require(isinstance(seal["seal_id"], str) and seal["seal_id"], "observation_seal_id_missing")
    require(seal["status"] == "complete", "observation_seal_incomplete")
    require(parse_utc(seal["sealed_at_utc"], "observation_sealed_at") >= frozen_at, "observations_sealed_before_freeze")
    require(seal["study_freeze_sha256"] == freeze_hash, "observation_seal_freeze_hash_drift")
    for key in (
        "execution_freeze_sha256",
        "packet_bank_seal_sha256",
        "raw_execution_bundle_sha256",
        "raw_execution_seal_sha256",
        "runner_sha256",
        "runner_contract_sha256",
        "primary_raw_record_hash_map_sha256",
        "primary_raw_record_hash_set_sha256",
    ):
        require_sha256(seal[key], f"observation_seal:{key}")
    bundle_hash = sha256_bytes(bundle_bytes)
    require(
        require_sha256(seal["observation_bundle_sha256"], "observation_bundle")
        == bundle_hash,
        "observation_bundle_hash_drift",
    )
    require(
        seal["record_count"] == freeze["packet_bank"]["item_count"],
        "observation_seal_record_count_drift",
    )
    require(seal["all_frozen_items_terminal"] is True, "observation_set_not_terminal")
    require(seal["source_text_included"] is False, "observation_seal_contains_source_text")
    require(
        seal["seal_id"] == f"QGOS_{bundle_hash[:16].upper()}",
        "observation_seal_id_not_deterministic",
    )
    return sha256_bytes(seal_bytes)


def validate_execution_chain(
    *,
    execution_freeze: dict[str, Any],
    execution_freeze_bytes: bytes,
    study_freeze: dict[str, Any],
    study_freeze_bytes: bytes,
    readiness_bytes: bytes,
    packet_seal: dict[str, Any],
    packet_seal_bytes: bytes,
    raw_bundle: dict[str, Any],
    raw_bundle_bytes: bytes,
    raw_seal: dict[str, Any],
    raw_seal_bytes: bytes,
    observations: Sequence[dict[str, Any]],
    observation_seal: dict[str, Any],
    rating_schema: dict[str, Any],
    component: dict[str, Any],
) -> dict[str, str]:
    exact_keys(
        execution_freeze,
        {
            "document_type",
            "execution_version",
            "status",
            "frozen_at_utc",
            "contains_source_text",
            "study_freeze_sha256",
            "readiness_report_sha256",
            "packet_bank_seal_sha256",
            "packet_bank_sha256",
            "packet_bank_item_count",
            "item_id_set_sha256",
            "runner_sha256",
            "runner_contract_sha256",
            "primary_repetition",
            "failure_policy",
            "output_policy",
            "packet_seal_bindings",
            "raw_retention_deletion_scope",
        },
        "execution_freeze",
    )
    require(
        execution_freeze["document_type"]
        == "warrantroute_qwen3_generalist_execution_freeze_v1",
        "execution_freeze_document_type_invalid",
    )
    require(execution_freeze["status"] == "bound_to_authorized_study_freeze", "execution_freeze_status_invalid")
    require(execution_freeze["contains_source_text"] is False, "execution_freeze_contains_source_text")
    require(
        execution_freeze["study_freeze_sha256"] == sha256_bytes(study_freeze_bytes),
        "execution_study_freeze_hash_drift",
    )
    require(
        execution_freeze["readiness_report_sha256"] == sha256_bytes(readiness_bytes),
        "execution_readiness_hash_drift",
    )
    require(
        execution_freeze["packet_bank_seal_sha256"] == sha256_bytes(packet_seal_bytes),
        "execution_packet_seal_hash_drift",
    )
    require(
        execution_freeze["packet_bank_sha256"] == packet_seal["bindings"]["packet_bank_sha256"],
        "execution_packet_bank_hash_drift",
    )
    require(
        execution_freeze["packet_bank_item_count"] == packet_seal["item_count"],
        "execution_item_count_drift",
    )
    require(
        execution_freeze["item_id_set_sha256"] == packet_seal["item_id_set_sha256"],
        "execution_item_set_drift",
    )
    require(
        execution_freeze["runner_sha256"] == sha256_bytes(read_regular_bytes(FORMAL_RUNNER)),
        "execution_runner_hash_drift",
    )
    require(
        execution_freeze["runner_contract_sha256"]
        == sha256_bytes(read_regular_bytes(FORMAL_RUNNER_CONTRACT)),
        "execution_runner_contract_hash_drift",
    )
    require(execution_freeze["primary_repetition"] == 1, "execution_primary_repetition_drift")
    require(
        execution_freeze["failure_policy"]
        == "one_attempt_per_item_all_failures_retained_as_misses",
        "execution_failure_policy_drift",
    )
    require(execution_freeze["output_policy"] == FORMAL_OUTPUT_POLICY, "execution_output_policy_drift")
    require(
        isinstance(execution_freeze["packet_seal_bindings"], dict),
        "execution_packet_seal_bindings_invalid",
    )
    require(
        execution_freeze["packet_seal_bindings"] == packet_seal["bindings"],
        "execution_packet_seal_bindings_drift",
    )
    retention = execution_freeze["raw_retention_deletion_scope"]
    require(isinstance(retention, dict), "raw_retention_scope_invalid")
    exact_keys(
        retention,
        {
            "approval_record_id",
            "approval_record_sha256",
            "readiness_gate_id",
            "storage_scope",
            "raw_source_bearing_records_approved",
            "authorized_accessor_group_id",
            "retention_until_utc",
            "deletion_required",
            "deletion_record_required",
        },
        "raw_retention_scope",
    )
    authorization = study_freeze["authorization"]
    require(
        retention["approval_record_id"] == authorization["approval_record_id"],
        "raw_retention_approval_id_drift",
    )
    require(
        retention["approval_record_sha256"] == authorization["approval_record_sha256"],
        "raw_retention_approval_hash_drift",
    )
    require(retention["readiness_gate_id"] == "retention_deletion_controls", "raw_retention_gate_invalid")
    require(retention["storage_scope"] == "restricted_mode_0600_storage", "raw_retention_storage_scope_invalid")
    require(retention["raw_source_bearing_records_approved"] is True, "raw_retention_not_approved")
    require(
        isinstance(retention["authorized_accessor_group_id"], str)
        and bool(retention["authorized_accessor_group_id"]),
        "raw_retention_accessor_group_missing",
    )
    execution_at = parse_utc(execution_freeze["frozen_at_utc"], "execution_frozen_at")
    require(
        parse_utc(retention["retention_until_utc"], "raw_retention_until") > execution_at,
        "raw_retention_window_invalid",
    )
    require(retention["deletion_required"] is True, "raw_deletion_not_required")
    require(retention["deletion_record_required"] is True, "raw_deletion_record_not_required")

    exact_keys(
        raw_bundle,
        {
            "document_type",
            "study_freeze_sha256",
            "execution_freeze_sha256",
            "packet_bank_seal_sha256",
            "corpus_id",
            "split",
            "method",
            "reviewer_actor_id",
            "model_id",
            "model_digest",
            "rating_repetitions",
            "primary_repetition",
            "contains_source_text",
            "storage_class",
            "records",
        },
        "raw_execution_bundle",
    )
    study_hash = sha256_bytes(study_freeze_bytes)
    execution_hash = sha256_bytes(execution_freeze_bytes)
    packet_seal_hash = sha256_bytes(packet_seal_bytes)
    require(raw_bundle["document_type"] == "warrantroute_qwen3_generalist_raw_execution_bundle_v1", "raw_bundle_document_type_invalid")
    require(raw_bundle["study_freeze_sha256"] == study_hash, "raw_bundle_study_freeze_drift")
    require(raw_bundle["execution_freeze_sha256"] == execution_hash, "raw_bundle_execution_freeze_drift")
    require(raw_bundle["packet_bank_seal_sha256"] == packet_seal_hash, "raw_bundle_packet_seal_drift")
    require(raw_bundle["corpus_id"] == EXPECTED_CORPUS_ID and raw_bundle["split"] == EXPECTED_SPLIT, "raw_bundle_dataset_drift")
    require(raw_bundle["method"] == EXPECTED_METHOD, "raw_bundle_method_drift")
    require(raw_bundle["reviewer_actor_id"] == EXPECTED_REVIEWER_ACTOR, "raw_bundle_actor_drift")
    require(raw_bundle["model_id"] == EXPECTED_MODEL_ID, "raw_bundle_model_drift")
    require(raw_bundle["model_digest"] == EXPECTED_MODEL_DIGEST, "raw_bundle_model_digest_drift")
    require(raw_bundle["rating_repetitions"] == 3 and raw_bundle["primary_repetition"] == 1, "raw_bundle_repetition_drift")
    require(raw_bundle["contains_source_text"] is True, "raw_bundle_source_attestation_invalid")
    require(raw_bundle["storage_class"] == "restricted_mode_0600_storage", "raw_bundle_storage_class_invalid")
    raw_records = raw_bundle["records"]
    expected_n = packet_seal["item_count"]
    require(isinstance(raw_records, list) and len(raw_records) == expected_n * 3, "raw_record_count_drift")
    raw_map: dict[tuple[str, int], dict[str, Any]] = {}
    validator = jsonschema.Draft202012Validator(rating_schema)
    allowed_item_ids = {row["item_id"] for row in observations}
    for index, record in enumerate(raw_records):
        require(isinstance(record, dict), f"raw_record_not_object:{index}")
        exact_keys(
            record,
            {
                "record_version",
                "item_id",
                "rating_repetition",
                "seed",
                "terminal_status",
                "http_status",
                "request_body_base64",
                "response_body_base64",
                "original_rating",
            },
            f"raw_record:{index}",
        )
        require(record["record_version"] == "qwen3-generalist-raw-execution-record-v1", f"raw_record_version_drift:{index}")
        item_id = record["item_id"]
        repetition = record["rating_repetition"]
        require(item_id in allowed_item_ids and repetition in (1, 2, 3), f"raw_record_identity_invalid:{index}")
        require((item_id, repetition) not in raw_map, "raw_record_duplicate")
        require(record["seed"] == component["repetition_seeds"][repetition - 1], f"raw_record_seed_drift:{index}")
        require(record["terminal_status"] in TERMINAL_STATUSES, f"raw_record_status_invalid:{index}")
        try:
            request_bytes = base64.b64decode(record["request_body_base64"], validate=True)
            request = json.loads(request_bytes.decode("utf-8"))
        except Exception as exc:
            raise ScoringExportError(f"raw_request_invalid:{index}") from exc
        require(isinstance(request, dict) and request.get("model") == EXPECTED_MODEL_ID, f"raw_request_model_drift:{index}")
        require(request.get("options", {}).get("seed") == record["seed"], f"raw_request_seed_drift:{index}")
        if record["response_body_base64"] is not None:
            try:
                base64.b64decode(record["response_body_base64"], validate=True)
            except Exception as exc:
                raise ScoringExportError(f"raw_response_invalid:{index}") from exc
        original = record["original_rating"]
        if record["terminal_status"] == "valid_rating":
            require(isinstance(original, dict), f"raw_valid_rating_missing:{index}")
            try:
                validator.validate(original)
            except jsonschema.ValidationError as exc:
                raise ScoringExportError(f"raw_rating_schema_invalid:{index}") from exc
        else:
            require(original is None, f"raw_failed_record_contains_rating:{index}")
        raw_map[(item_id, repetition)] = record
    require(
        set(raw_map) == {(item_id, repetition) for item_id in allowed_item_ids for repetition in (1, 2, 3)},
        "raw_record_grid_incomplete",
    )
    for observation in observations:
        raw_record = raw_map[(observation["item_id"], 1)]
        require(
            observation["private_execution_record_sha256"]
            == sha256_bytes(canonical_bytes(raw_record)),
            "observation_private_execution_hash_drift",
        )
        require(observation["terminal_status"] == raw_record["terminal_status"], "observation_raw_status_drift")
        original = raw_record["original_rating"]
        if original is None:
            require(observation["rating"] is None, "observation_raw_rating_drift")
        else:
            projected = dict(original)
            projected["rationale"] = "Rationale withheld from the source-free scoring bundle."
            require(observation["rating"] == projected, "observation_projection_drift")

    raw_bundle_hash = sha256_bytes(raw_bundle_bytes)
    primary_raw_hash_map = {
        item_id: sha256_bytes(canonical_bytes(raw_map[(item_id, 1)]))
        for item_id in sorted(allowed_item_ids)
    }
    primary_raw_hash_map_hash = sha256_bytes(canonical_bytes(primary_raw_hash_map))
    primary_raw_hash_set_hash = sha256_bytes(
        canonical_bytes(sorted(primary_raw_hash_map.values()))
    )
    exact_keys(
        raw_seal,
        {
            "document_type",
            "seal_id",
            "status",
            "sealed_at_utc",
            "study_freeze_sha256",
            "execution_freeze_sha256",
            "packet_bank_seal_sha256",
            "raw_execution_bundle_sha256",
            "runner_sha256",
            "runner_contract_sha256",
            "raw_retention_deletion_scope_sha256",
            "item_count",
            "rating_repetitions",
            "record_count",
            "all_frozen_item_repetitions_terminal",
            "contains_source_text",
            "sealed_bundle_contains_source_text",
            "restricted_storage",
        },
        "raw_execution_seal",
    )
    require(raw_seal["document_type"] == "warrantroute_qwen3_generalist_raw_execution_seal_v1", "raw_seal_document_type_invalid")
    require(raw_seal["seal_id"] == f"QGRES_{raw_bundle_hash[:16].upper()}", "raw_seal_id_not_deterministic")
    require(raw_seal["status"] == "complete", "raw_seal_incomplete")
    require(raw_seal["study_freeze_sha256"] == study_hash, "raw_seal_study_drift")
    require(raw_seal["execution_freeze_sha256"] == execution_hash, "raw_seal_execution_drift")
    require(raw_seal["packet_bank_seal_sha256"] == packet_seal_hash, "raw_seal_packet_drift")
    require(raw_seal["raw_execution_bundle_sha256"] == raw_bundle_hash, "raw_seal_bundle_drift")
    require(raw_seal["runner_sha256"] == execution_freeze["runner_sha256"], "raw_seal_runner_drift")
    require(
        raw_seal["runner_contract_sha256"] == execution_freeze["runner_contract_sha256"],
        "raw_seal_runner_contract_drift",
    )
    require(
        raw_seal["raw_retention_deletion_scope_sha256"]
        == sha256_bytes(canonical_bytes(retention)),
        "raw_seal_retention_scope_drift",
    )
    require(raw_seal["item_count"] == expected_n and raw_seal["record_count"] == expected_n * 3, "raw_seal_count_drift")
    require(raw_seal["rating_repetitions"] == 3, "raw_seal_repetition_drift")
    require(raw_seal["all_frozen_item_repetitions_terminal"] is True, "raw_seal_terminal_attestation_missing")
    require(raw_seal["contains_source_text"] is False and raw_seal["sealed_bundle_contains_source_text"] is True, "raw_seal_source_attestation_invalid")
    require(raw_seal["restricted_storage"] is True, "raw_seal_storage_attestation_invalid")
    require(
        parse_utc(raw_seal["sealed_at_utc"], "raw_sealed_at")
        == parse_utc(observation_seal["sealed_at_utc"], "observation_sealed_at"),
        "raw_observation_seal_time_drift",
    )
    raw_seal_hash = sha256_bytes(raw_seal_bytes)
    require(observation_seal["execution_freeze_sha256"] == execution_hash, "observation_seal_execution_drift")
    require(observation_seal["packet_bank_seal_sha256"] == packet_seal_hash, "observation_seal_packet_drift")
    require(observation_seal["raw_execution_bundle_sha256"] == raw_bundle_hash, "observation_seal_raw_bundle_drift")
    require(observation_seal["raw_execution_seal_sha256"] == raw_seal_hash, "observation_seal_raw_seal_drift")
    require(observation_seal["runner_sha256"] == execution_freeze["runner_sha256"], "observation_seal_runner_drift")
    require(
        observation_seal["runner_contract_sha256"]
        == execution_freeze["runner_contract_sha256"],
        "observation_seal_runner_contract_drift",
    )
    require(
        observation_seal["primary_raw_record_hash_map_sha256"]
        == primary_raw_hash_map_hash,
        "observation_seal_primary_raw_map_drift",
    )
    require(
        observation_seal["primary_raw_record_hash_set_sha256"]
        == primary_raw_hash_set_hash,
        "observation_seal_primary_raw_set_drift",
    )
    return {
        "execution_freeze_sha256": execution_hash,
        "raw_execution_bundle_sha256": raw_bundle_hash,
        "raw_execution_seal_sha256": raw_seal_hash,
    }


def percentile(values: Sequence[float], probability: float) -> float:
    require(bool(values), "percentile_empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def score_rows(
    observations: Sequence[dict[str, Any]],
    truths: Sequence[dict[str, str]],
) -> list[dict[str, Any]]:
    observation_map = {row["item_id"]: row for row in observations}
    truth_ids = {row["item_id"] for row in truths}
    require(set(observation_map) == truth_ids, "observation_truth_item_set_mismatch")
    rows: list[dict[str, Any]] = []
    for truth in truths:
        observation = observation_map[truth["item_id"]]
        rating = observation["rating"] if observation["terminal_status"] == "valid_rating" else None
        hit = bool(
            rating is not None
            and rating["cannot_judge"] == []
            and truth["required_flag"] in rating["serious_error_flags"]
        )
        rows.append({"cluster_id": truth["cluster_id"], "hit": hit})
    return rows


def cluster_bootstrap_ci(
    rows: Sequence[dict[str, Any]],
    *,
    resamples: int,
    seed: int,
    minimum_clusters: int,
) -> tuple[list[float], int]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["cluster_id"]].append(row)
    cluster_ids = sorted(grouped)
    require(len(cluster_ids) >= minimum_clusters, "ci_not_estimable")
    rng = random.Random(seed)
    distribution: list[float] = []
    for _ in range(resamples):
        sampled: list[dict[str, Any]] = []
        for cluster_id in rng.choices(cluster_ids, k=len(cluster_ids)):
            sampled.extend(grouped[cluster_id])
        require(bool(sampled), "bootstrap_sample_empty")
        distribution.append(sum(bool(row["hit"]) for row in sampled) / len(sampled))
    return [percentile(distribution, 0.025), percentile(distribution, 0.975)], len(cluster_ids)


def build_export(
    *,
    freeze: dict[str, Any],
    freeze_hash: str,
    observation_bundle_hash: str,
    observation_seal_hash: str,
    truth_map_hash: str,
    readiness_report_hash: str,
    evidence_metadata: dict[str, Any],
    execution_metadata: dict[str, str],
    rows: Sequence[dict[str, Any]],
    created_at_utc: str,
) -> dict[str, Any]:
    created_at = parse_utc(created_at_utc, "export_created_at")
    require(created_at >= parse_utc(freeze["frozen_at_utc"], "frozen_at"), "export_created_before_freeze")
    n = len(rows)
    require(n == freeze["packet_bank"]["item_count"] and n > 0, "final_denominator_drift")
    tp = sum(bool(row["hit"]) for row in rows)
    recall = tp / n
    ci, cluster_count = cluster_bootstrap_ci(
        rows,
        resamples=freeze["scoring"]["bootstrap_resamples"],
        seed=freeze["scoring"]["bootstrap_seed"],
        minimum_clusters=freeze["scoring"]["minimum_independent_clusters"],
    )
    external_authority_verified = bool(
        evidence_metadata["external_signature_verified"]
    )
    return {
        "document_type": "warrantroute_qwen3_generalist_scoring_export_v1",
        "export_version": "qwen3-generalist-score-v1",
        "created_at_utc": created_at_utc,
        "status": "complete_internal_only",
        "manuscript_eligible": external_authority_verified,
        "dataset": dict(freeze["dataset"]),
        "method": dict(freeze["method"]),
        "candidate_generation": {
            "model_id": evidence_metadata["candidate_generator_model_id"],
            "snapshot_sha256": evidence_metadata[
                "candidate_generator_snapshot_sha256"
            ],
            "prompt_sha256": evidence_metadata[
                "candidate_generator_prompt_sha256"
            ],
        },
        "metric": {
            "name": EXPECTED_METRIC,
            "tp": tp,
            "fn": n - tp,
            "n": n,
            "tp_over_n": f"{tp}/{n}",
            "recall": recall,
            "recall_percent": 100 * recall,
            "confidence_level": 0.95,
            "ci_method": "cluster_bootstrap_percentile",
            "recall_95_ci": ci,
            "recall_95_ci_percent": [100 * value for value in ci],
            "source_cluster_unit": EXPECTED_CLUSTER_UNIT,
            "bootstrap_cluster_unit": EXPECTED_BOOTSTRAP_CLUSTER_UNIT,
            "independent_cluster_count": cluster_count,
            "bootstrap_resamples": freeze["scoring"]["bootstrap_resamples"],
            "bootstrap_seed": freeze["scoring"]["bootstrap_seed"],
        },
        "eligibility": {
            "authorization_record_id": freeze["authorization"]["approval_record_id"],
            "authorization_record_sha256": freeze["authorization"]["approval_record_sha256"],
            "privacy_cleared_packet_bank": True,
            "clean_preaccess_record": True,
            "formal_readiness_report_passed": True,
            "candidate_generator_distinct_from_reviewer": True,
            "complete_fixed_denominator": True,
            "all_failures_retained_as_misses": True,
            "ci_estimable": True,
            "exact_local_authority_and_evidence_records_verified": True,
            "external_authority_signature_verified": external_authority_verified,
            "external_authority_gate_satisfied": external_authority_verified,
            "manuscript_eligibility_blockers": (
                []
                if external_authority_verified
                else ["external_authority_signature_not_verified"]
            ),
            "authority_limitation": (
                "No independently verifiable external authority signature is available. "
                "Exact local governance and evidence records were checked and the formal "
                "readiness report was reproduced, but this aggregate remains ineligible "
                "for manuscript use until the external-authority gate is satisfied."
            ),
        },
        "input_hashes": {
            "study_freeze_sha256": freeze_hash,
            "readiness_report_sha256": readiness_report_hash,
            "packet_bank_seal_sha256": freeze["packet_bank"]["seal_sha256"],
            "truth_cluster_map_sha256": truth_map_hash,
            "observation_bundle_sha256": observation_bundle_hash,
            "observation_seal_sha256": observation_seal_hash,
            "reviewer_component_freeze_sha256": freeze["assets"]["reviewer_component_freeze_sha256"],
            "shared_rating_schema_sha256": freeze["assets"]["shared_rating_schema_sha256"],
            "scoring_exporter_sha256": freeze["assets"]["scoring_exporter_sha256"],
            "scoring_contract_sha256": freeze["assets"]["scoring_contract_sha256"],
            "formal_runner_sha256": freeze["assets"]["formal_runner_sha256"],
            "formal_runner_contract_sha256": freeze["assets"][
                "formal_runner_contract_sha256"
            ],
            "governance_record_sha256": evidence_metadata[
                "governance_record_sha256"
            ],
            "reviewer_registry_sha256": evidence_metadata[
                "reviewer_registry_sha256"
            ],
            "privacy_review_log_sha256": evidence_metadata[
                "privacy_review_log_sha256"
            ],
            "source_receipt_sha256": evidence_metadata["source_receipt_sha256"],
            "study_manifest_sha256": evidence_metadata["study_manifest_sha256"],
            "packet_study_freeze_sha256": evidence_metadata[
                "packet_study_freeze_sha256"
            ],
            **execution_metadata,
        },
    }


def write_new_private_json(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve(strict=False)
    require(path.parent.is_dir(), "output_parent_missing")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ScoringExportError("output_exists") from exc
    except OSError as exc:
        raise ScoringExportError("output_unavailable") from exc
    try:
        payload = canonical_bytes(value)
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def export_score(
    *,
    study_freeze_path: Path,
    readiness_report_path: Path,
    governance_record_path: Path,
    reviewer_registry_path: Path,
    privacy_log_path: Path,
    preaccess_record_path: Path,
    source_receipt_path: Path,
    study_manifest_path: Path,
    packet_study_freeze_path: Path,
    packet_bank_seal_path: Path,
    execution_freeze_path: Path,
    observation_bundle_path: Path,
    observation_seal_path: Path,
    raw_execution_bundle_path: Path,
    raw_execution_seal_path: Path,
    truth_map_path: Path,
    output_path: Path,
    created_at_utc: str | None = None,
    workspace: Path = WORKSPACE,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    governance_local = workspace / "governance" / "local"
    storage = workspace / "Storage"
    for path, label in (
        (study_freeze_path, "study_freeze"),
        (readiness_report_path, "readiness_report"),
        (governance_record_path, "governance_record"),
        (reviewer_registry_path, "reviewer_registry"),
        (privacy_log_path, "privacy_log"),
        (preaccess_record_path, "preaccess_record"),
        (packet_study_freeze_path, "packet_study_freeze"),
        (execution_freeze_path, "execution_freeze"),
    ):
        require_private_input_path(path, root=governance_local, label=label)
    for path, label in (
        (packet_bank_seal_path, "packet_bank_seal"),
        (observation_bundle_path, "observation_bundle"),
        (observation_seal_path, "observation_seal"),
        (raw_execution_bundle_path, "raw_execution_bundle"),
        (raw_execution_seal_path, "raw_execution_seal"),
        (truth_map_path, "truth_map"),
    ):
        require_private_input_path(path, root=storage, label=label)
    require_bound_manifest_path(
        source_receipt_path,
        workspace=workspace,
        label="source_receipt",
    )
    require_bound_manifest_path(
        study_manifest_path,
        workspace=workspace,
        label="study_manifest",
    )
    require_storage_output_path(output_path, workspace=workspace)

    component, component_assets, component_hash = load_component()
    rating_schema_path = reviewer.workspace_path(
        component["assets"]["shared_rating_schema"]["file"]
    )
    rating_schema_hash = sha256_bytes(read_regular_bytes(rating_schema_path))

    freeze, freeze_bytes = load_json_with_bytes(study_freeze_path)
    metadata = validate_study_freeze(
        freeze,
        component_hash=component_hash,
        rating_schema_hash=rating_schema_hash,
    )
    freeze_hash = sha256_bytes(freeze_bytes)

    readiness_report, readiness_report_bytes = load_json_with_bytes(readiness_report_path)
    readiness_report_hash = validate_readiness_report(
        readiness_report,
        report_bytes=readiness_report_bytes,
        freeze=freeze,
        frozen_at=metadata["frozen_at"],
    )

    governance_record, governance_bytes = load_json_with_bytes(governance_record_path)
    reviewer_registry, reviewer_registry_bytes = load_json_with_bytes(
        reviewer_registry_path
    )
    privacy_log, privacy_log_bytes = load_json_with_bytes(privacy_log_path)
    preaccess_record, preaccess_bytes = load_json_with_bytes(preaccess_record_path)
    source_receipt, source_receipt_bytes = load_json_with_bytes(source_receipt_path)
    study_manifest, study_manifest_bytes = load_json_with_bytes(study_manifest_path)
    require(bool(source_receipt), "source_receipt_empty")
    require(bool(study_manifest), "study_manifest_empty")
    packet_study_freeze, packet_study_freeze_bytes = load_json_with_bytes(
        packet_study_freeze_path
    )

    truth, truth_bytes = load_json_with_bytes(truth_map_path)
    truth_schema, truth_schema_bytes = load_json_with_bytes(TRUTH_MAP_SCHEMA)
    packet_freeze_schema, packet_freeze_schema_bytes = load_json_with_bytes(
        PACKET_STUDY_FREEZE_SCHEMA
    )
    try:
        jsonschema.Draft202012Validator.check_schema(truth_schema)
    except jsonschema.SchemaError as exc:
        raise ScoringExportError("truth_cluster_map_schema_definition_invalid") from exc
    packet_seal, packet_seal_bytes = load_json_with_bytes(packet_bank_seal_path)
    packet_seal_hash = validate_packet_bank_seal(
        packet_seal,
        seal_bytes=packet_seal_bytes,
        freeze=freeze,
        readiness_report_hash=readiness_report_hash,
        truth_map_hash=sha256_bytes(truth_bytes),
        component_hash=component_hash,
        evaluator_schema_hash=component["assets"]["evaluator_item_schema"]["sha256"],
        truth_schema_hash=sha256_bytes(truth_schema_bytes),
        packet_freeze_schema_hash=sha256_bytes(packet_freeze_schema_bytes),
    )
    require(
        packet_seal_hash == freeze["packet_bank"]["seal_sha256"],
        "packet_seal_final_hash_drift",
    )
    evidence_metadata = validate_evidence_records(
        freeze=freeze,
        readiness_report=readiness_report,
        governance_record=governance_record,
        governance_bytes=governance_bytes,
        reviewer_registry=reviewer_registry,
        reviewer_registry_bytes=reviewer_registry_bytes,
        privacy_log=privacy_log,
        privacy_log_bytes=privacy_log_bytes,
        preaccess_record=preaccess_record,
        preaccess_bytes=preaccess_bytes,
        source_receipt_path=source_receipt_path,
        source_receipt_bytes=source_receipt_bytes,
        study_manifest_path=study_manifest_path,
        study_manifest_bytes=study_manifest_bytes,
        packet_study_freeze=packet_study_freeze,
        packet_study_freeze_bytes=packet_study_freeze_bytes,
        packet_study_freeze_schema=packet_freeze_schema,
        packet_seal=packet_seal,
        workspace=workspace,
    )
    allowed_flags = set(
        component_assets["shared_rating_schema"]["properties"]["serious_error_flags"]["items"]["enum"]
    )
    truth_records = validate_truth_map(
        truth,
        freeze=freeze,
        truth_bytes=truth_bytes,
        truth_schema=truth_schema,
        packet_seal=packet_seal,
        allowed_flags=allowed_flags,
    )

    bundle, bundle_bytes = load_json_with_bytes(observation_bundle_path)
    observation_records = validate_observation_bundle(
        bundle,
        freeze=freeze,
        freeze_hash=freeze_hash,
        rating_schema=component_assets["shared_rating_schema"],
    )

    seal, seal_bytes = load_json_with_bytes(observation_seal_path)
    seal_hash = validate_observation_seal(
        seal,
        seal_bytes=seal_bytes,
        bundle_bytes=bundle_bytes,
        freeze=freeze,
        freeze_hash=freeze_hash,
        frozen_at=metadata["frozen_at"],
    )
    require(seal["record_count"] == len(observation_records), "seal_bundle_record_count_drift")

    execution_freeze, execution_freeze_bytes = load_json_with_bytes(
        execution_freeze_path
    )
    raw_bundle, raw_bundle_bytes = load_json_with_bytes(raw_execution_bundle_path)
    raw_seal, raw_seal_bytes = load_json_with_bytes(raw_execution_seal_path)
    execution_metadata = validate_execution_chain(
        execution_freeze=execution_freeze,
        execution_freeze_bytes=execution_freeze_bytes,
        study_freeze=freeze,
        study_freeze_bytes=freeze_bytes,
        readiness_bytes=readiness_report_bytes,
        packet_seal=packet_seal,
        packet_seal_bytes=packet_seal_bytes,
        raw_bundle=raw_bundle,
        raw_bundle_bytes=raw_bundle_bytes,
        raw_seal=raw_seal,
        raw_seal_bytes=raw_seal_bytes,
        observations=observation_records,
        observation_seal=seal,
        rating_schema=component_assets["shared_rating_schema"],
        component=component,
    )

    rows = score_rows(observation_records, truth_records)
    timestamp = created_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    export = build_export(
        freeze=freeze,
        freeze_hash=freeze_hash,
        observation_bundle_hash=sha256_bytes(bundle_bytes),
        observation_seal_hash=seal_hash,
        truth_map_hash=sha256_bytes(truth_bytes),
        readiness_report_hash=readiness_report_hash,
        evidence_metadata=evidence_metadata,
        execution_metadata=execution_metadata,
        rows=rows,
        created_at_utc=timestamp,
    )
    write_new_private_json(output_path, export)
    return export


def source_free_summary() -> dict[str, Any]:
    _, assets, component_hash = load_component()
    return {
        "component": "qwen3-generalist-score-v1",
        "status": "passed",
        "source_text_accessed": False,
        "outputs_written": False,
        "manuscript_eligible": False,
        "reviewer_component_freeze_sha256": component_hash,
        "shared_rating_schema_id": assets["shared_rating_schema"].get("$id"),
        "scoring_exporter_sha256": sha256_bytes(read_regular_bytes(SCRIPT)),
        "scoring_contract_sha256": sha256_bytes(read_regular_bytes(CONTRACT)),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    subparsers.add_parser("dry-run")
    export = subparsers.add_parser("export")
    export.add_argument("--study-freeze", type=Path, required=True)
    export.add_argument("--readiness-report", type=Path, required=True)
    export.add_argument("--governance-record", type=Path, required=True)
    export.add_argument("--reviewer-registry", type=Path, required=True)
    export.add_argument("--privacy-log", type=Path, required=True)
    export.add_argument("--preaccess-record", type=Path, required=True)
    export.add_argument("--source-receipt", type=Path, required=True)
    export.add_argument("--study-manifest", type=Path, required=True)
    export.add_argument("--packet-study-freeze", type=Path, required=True)
    export.add_argument("--packet-bank-seal", type=Path, required=True)
    export.add_argument("--execution-freeze", type=Path, required=True)
    export.add_argument("--observation-bundle", type=Path, required=True)
    export.add_argument("--observation-seal", type=Path, required=True)
    export.add_argument("--raw-execution-bundle", type=Path, required=True)
    export.add_argument("--raw-execution-seal", type=Path, required=True)
    export.add_argument("--truth-map", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "dry-run":
            result = source_free_summary()
        else:
            result = export_score(
                study_freeze_path=args.study_freeze,
                readiness_report_path=args.readiness_report,
                governance_record_path=args.governance_record,
                reviewer_registry_path=args.reviewer_registry,
                privacy_log_path=args.privacy_log,
                preaccess_record_path=args.preaccess_record,
                source_receipt_path=args.source_receipt,
                study_manifest_path=args.study_manifest,
                packet_study_freeze_path=args.packet_study_freeze,
                packet_bank_seal_path=args.packet_bank_seal,
                execution_freeze_path=args.execution_freeze,
                observation_bundle_path=args.observation_bundle,
                observation_seal_path=args.observation_seal,
                raw_execution_bundle_path=args.raw_execution_bundle,
                raw_execution_seal_path=args.raw_execution_seal,
                truth_map_path=args.truth_map,
                output_path=args.output,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ScoringExportError, reviewer.GeneralistReviewerError) as exc:
        print(
            json.dumps(
                {
                    "component": "qwen3-generalist-score-v1",
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
