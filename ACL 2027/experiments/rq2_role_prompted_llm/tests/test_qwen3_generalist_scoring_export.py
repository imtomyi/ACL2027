#!/usr/bin/env python3
"""Source-free integrity tests for the Qwen3 Generalist scoring exporter."""

from __future__ import annotations

import base64
import copy
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/export_qwen3_generalist_score.py"
SPEC = importlib.util.spec_from_file_location("qwen3_scoring_export_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def inert_rating() -> dict:
    return {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 3,
        "voice_boundary_preservation": 3,
        "scope_calibration": 3,
        "cannot_judge": [],
        "confidence": 3,
        "disposition": "revise",
        "requested_expertise": "none",
        "serious_error_flags": ["unsupported_inference"],
        "rationale": "INERT RAW SOFTWARE TEST RATIONALE",
    }


def execution_fixture() -> dict:
    component, assets, _ = MODULE.load_component()
    study = {
        "fixture": "study",
        "authorization": {
            "approval_record_id": "APPROVAL_SOURCE_FREE_TEST",
            "approval_record_sha256": "e" * 64,
        },
    }
    study_bytes = MODULE.canonical_bytes(study)
    readiness_bytes = MODULE.canonical_bytes({"fixture": "readiness"})
    packet_bytes = MODULE.canonical_bytes({"fixture": "packet-seal"})
    packet_hash = "a" * 64
    binding_names = (
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
    )
    packet_bindings = {
        name: f"{index + 1:064x}" for index, name in enumerate(binding_names)
    }
    packet_bindings["packet_bank_sha256"] = packet_hash
    item_id = "DJI_0000000000000001"
    item_set_hash = MODULE.item_id_set_sha256([item_id])
    retention = {
        "approval_record_id": "APPROVAL_SOURCE_FREE_TEST",
        "approval_record_sha256": "e" * 64,
        "readiness_gate_id": "retention_deletion_controls",
        "storage_scope": "restricted_mode_0600_storage",
        "raw_source_bearing_records_approved": True,
        "authorized_accessor_group_id": "ACCESS_GROUP_SOURCE_FREE_TEST",
        "retention_until_utc": "2027-08-28T00:00:00Z",
        "deletion_required": True,
        "deletion_record_required": True,
    }
    execution = {
        "document_type": "warrantroute_qwen3_generalist_execution_freeze_v1",
        "execution_version": "qwen3-generalist-formal-execution-v1",
        "status": "bound_to_authorized_study_freeze",
        "frozen_at_utc": "2026-08-28T01:00:00Z",
        "contains_source_text": False,
        "study_freeze_sha256": MODULE.sha256_bytes(study_bytes),
        "readiness_report_sha256": MODULE.sha256_bytes(readiness_bytes),
        "packet_bank_seal_sha256": MODULE.sha256_bytes(packet_bytes),
        "packet_bank_sha256": packet_hash,
        "packet_bank_item_count": 1,
        "item_id_set_sha256": item_set_hash,
        "runner_sha256": MODULE.sha256_bytes(MODULE.read_regular_bytes(MODULE.FORMAL_RUNNER)),
        "runner_contract_sha256": MODULE.sha256_bytes(
            MODULE.read_regular_bytes(MODULE.FORMAL_RUNNER_CONTRACT)
        ),
        "primary_repetition": 1,
        "failure_policy": "one_attempt_per_item_all_failures_retained_as_misses",
        "output_policy": copy.deepcopy(MODULE.FORMAL_OUTPUT_POLICY),
        "packet_seal_bindings": copy.deepcopy(packet_bindings),
        "raw_retention_deletion_scope": retention,
    }
    execution_bytes = MODULE.canonical_bytes(execution)
    raw_records = []
    observation = None
    for repetition, seed in enumerate(component["repetition_seeds"], 1):
        original = inert_rating()
        request = {"model": MODULE.EXPECTED_MODEL_ID, "options": {"seed": seed}}
        record = {
            "record_version": "qwen3-generalist-raw-execution-record-v1",
            "item_id": item_id,
            "rating_repetition": repetition,
            "seed": seed,
            "terminal_status": "valid_rating",
            "http_status": 200,
            "request_body_base64": base64.b64encode(MODULE.canonical_bytes(request)).decode(),
            "response_body_base64": base64.b64encode(b"INERT RESPONSE").decode(),
            "original_rating": original,
        }
        raw_records.append(record)
        if repetition == 1:
            projected = copy.deepcopy(original)
            projected["rationale"] = "Rationale withheld from the source-free scoring bundle."
            observation = {
                "item_id": item_id,
                "rating_repetition": 1,
                "terminal_status": "valid_rating",
                "rating": projected,
                "private_execution_record_sha256": MODULE.sha256_bytes(
                    MODULE.canonical_bytes(record)
                ),
            }
    assert observation is not None
    raw_bundle = {
        "document_type": "warrantroute_qwen3_generalist_raw_execution_bundle_v1",
        "study_freeze_sha256": MODULE.sha256_bytes(study_bytes),
        "execution_freeze_sha256": MODULE.sha256_bytes(execution_bytes),
        "packet_bank_seal_sha256": MODULE.sha256_bytes(packet_bytes),
        "corpus_id": "dreaddit",
        "split": "test",
        "method": "Generalist",
        "reviewer_actor_id": MODULE.EXPECTED_REVIEWER_ACTOR,
        "model_id": MODULE.EXPECTED_MODEL_ID,
        "model_digest": MODULE.EXPECTED_MODEL_DIGEST,
        "rating_repetitions": 3,
        "primary_repetition": 1,
        "contains_source_text": True,
        "storage_class": "restricted_mode_0600_storage",
        "records": raw_records,
    }
    raw_bytes = MODULE.canonical_bytes(raw_bundle)
    raw_hash = MODULE.sha256_bytes(raw_bytes)
    raw_seal = {
        "document_type": "warrantroute_qwen3_generalist_raw_execution_seal_v1",
        "seal_id": f"QGRES_{raw_hash[:16].upper()}",
        "status": "complete",
        "sealed_at_utc": "2026-08-28T03:00:00Z",
        "study_freeze_sha256": MODULE.sha256_bytes(study_bytes),
        "execution_freeze_sha256": MODULE.sha256_bytes(execution_bytes),
        "packet_bank_seal_sha256": MODULE.sha256_bytes(packet_bytes),
        "raw_execution_bundle_sha256": raw_hash,
        "runner_sha256": execution["runner_sha256"],
        "runner_contract_sha256": execution["runner_contract_sha256"],
        "raw_retention_deletion_scope_sha256": MODULE.sha256_bytes(
            MODULE.canonical_bytes(retention)
        ),
        "item_count": 1,
        "rating_repetitions": 3,
        "record_count": 3,
        "all_frozen_item_repetitions_terminal": True,
        "contains_source_text": False,
        "sealed_bundle_contains_source_text": True,
        "restricted_storage": True,
    }
    raw_seal_bytes = MODULE.canonical_bytes(raw_seal)
    primary_record_hash = observation["private_execution_record_sha256"]
    return {
        "execution_freeze": execution,
        "execution_freeze_bytes": execution_bytes,
        "study_freeze": study,
        "study_freeze_bytes": study_bytes,
        "readiness_bytes": readiness_bytes,
        "packet_seal": {
            "bindings": packet_bindings,
            "item_count": 1,
            "item_id_set_sha256": item_set_hash,
        },
        "packet_seal_bytes": packet_bytes,
        "raw_bundle": raw_bundle,
        "raw_bundle_bytes": raw_bytes,
        "raw_seal": raw_seal,
        "raw_seal_bytes": raw_seal_bytes,
        "observations": [observation],
        "observation_seal": {
            "sealed_at_utc": "2026-08-28T03:00:00Z",
            "execution_freeze_sha256": MODULE.sha256_bytes(execution_bytes),
            "packet_bank_seal_sha256": MODULE.sha256_bytes(packet_bytes),
            "raw_execution_bundle_sha256": raw_hash,
            "raw_execution_seal_sha256": MODULE.sha256_bytes(raw_seal_bytes),
            "runner_sha256": execution["runner_sha256"],
            "runner_contract_sha256": execution["runner_contract_sha256"],
            "primary_raw_record_hash_map_sha256": MODULE.sha256_bytes(
                MODULE.canonical_bytes({item_id: primary_record_hash})
            ),
            "primary_raw_record_hash_set_sha256": MODULE.sha256_bytes(
                MODULE.canonical_bytes([primary_record_hash])
            ),
        },
        "rating_schema": assets["shared_rating_schema"],
        "component": component,
    }


class ScoringExporterIntegrityTests(unittest.TestCase):
    def test_exact_raw_execution_chain_is_accepted(self) -> None:
        fixture = execution_fixture()
        result = MODULE.validate_execution_chain(**fixture)
        self.assertEqual(
            result["raw_execution_bundle_sha256"],
            MODULE.sha256_bytes(fixture["raw_bundle_bytes"]),
        )

    def test_rep1_observation_hash_must_match_canonical_raw_record(self) -> None:
        fixture = execution_fixture()
        fixture["raw_bundle"]["records"][0]["http_status"] = 201
        fixture["raw_bundle_bytes"] = MODULE.canonical_bytes(fixture["raw_bundle"])
        with self.assertRaisesRegex(
            MODULE.ScoringExportError,
            "observation_private_execution_hash_drift",
        ):
            MODULE.validate_execution_chain(**fixture)

    def test_raw_seal_must_bind_exact_bundle(self) -> None:
        fixture = execution_fixture()
        fixture["raw_seal"]["raw_execution_bundle_sha256"] = "f" * 64
        fixture["raw_seal_bytes"] = MODULE.canonical_bytes(fixture["raw_seal"])
        with self.assertRaisesRegex(MODULE.ScoringExportError, "raw_seal_bundle_drift"):
            MODULE.validate_execution_chain(**fixture)

    def test_execution_binds_the_complete_packet_seal_binding_map(self) -> None:
        fixture = execution_fixture()
        fixture["execution_freeze"]["packet_seal_bindings"][
            "privacy_review_log_sha256"
        ] = "f" * 64
        with self.assertRaisesRegex(
            MODULE.ScoringExportError, "execution_packet_seal_bindings_drift"
        ):
            MODULE.validate_execution_chain(**fixture)

    def test_raw_seal_binds_runner_contract_and_retention_scope(self) -> None:
        for field, error in (
            ("runner_sha256", "raw_seal_runner_drift"),
            ("runner_contract_sha256", "raw_seal_runner_contract_drift"),
            (
                "raw_retention_deletion_scope_sha256",
                "raw_seal_retention_scope_drift",
            ),
        ):
            with self.subTest(field=field):
                fixture = execution_fixture()
                fixture["raw_seal"][field] = "f" * 64
                fixture["raw_seal_bytes"] = MODULE.canonical_bytes(
                    fixture["raw_seal"]
                )
                with self.assertRaisesRegex(MODULE.ScoringExportError, error):
                    MODULE.validate_execution_chain(**fixture)

    def test_runner_and_contract_hashes_are_not_self_asserted(self) -> None:
        for field, error in (
            ("runner_sha256", "execution_runner_hash_drift"),
            ("runner_contract_sha256", "execution_runner_contract_hash_drift"),
        ):
            with self.subTest(field=field):
                fixture = execution_fixture()
                fixture["execution_freeze"][field] = "f" * 64
                with self.assertRaisesRegex(MODULE.ScoringExportError, error):
                    MODULE.validate_execution_chain(**fixture)

    def test_output_path_is_storage_only_mode_0700_and_no_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            storage = workspace / "Storage"
            run = storage / "run"
            run.mkdir(parents=True)
            os.chmod(run, 0o700)
            allowed = run / "score.json"
            MODULE.require_storage_output_path(allowed, workspace=workspace)
            with self.assertRaisesRegex(MODULE.ScoringExportError, "output_outside_storage"):
                MODULE.require_storage_output_path(
                    workspace / "outside.json", workspace=workspace
                )
            os.chmod(run, 0o755)
            with self.assertRaisesRegex(MODULE.ScoringExportError, "output_parent_mode_invalid"):
                MODULE.require_storage_output_path(allowed, workspace=workspace)
            os.chmod(run, 0o700)
            target = run / "target.json"
            target.write_text("inert", encoding="utf-8")
            allowed.symlink_to(target)
            with self.assertRaisesRegex(MODULE.ScoringExportError, "output_exists_or_symlink"):
                MODULE.require_storage_output_path(allowed, workspace=workspace)

    def test_external_authority_remains_an_explicit_unsatisfied_gate(self) -> None:
        freeze = {
            "frozen_at_utc": "2026-08-28T01:00:00Z",
            "packet_bank": {"item_count": 5, "seal_sha256": "1" * 64},
            "scoring": {
                "bootstrap_resamples": 10_000,
                "bootstrap_seed": 20_270_826,
                "minimum_independent_clusters": 5,
            },
            "dataset": {"corpus_id": "dreaddit"},
            "method": {"name": "Generalist"},
            "authorization": {
                "approval_record_id": "LOCAL_AUTHORITY_RECORD",
                "approval_record_sha256": "2" * 64,
            },
            "assets": {
                "reviewer_component_freeze_sha256": "3" * 64,
                "shared_rating_schema_sha256": "4" * 64,
                "scoring_exporter_sha256": "5" * 64,
                "scoring_contract_sha256": "6" * 64,
                "formal_runner_sha256": "7" * 64,
                "formal_runner_contract_sha256": "8" * 64,
            },
        }
        evidence = {
            "candidate_generator_model_id": "inert-generator",
            "candidate_generator_snapshot_sha256": "9" * 64,
            "candidate_generator_prompt_sha256": "a" * 64,
            "external_signature_verified": False,
            "governance_record_sha256": "b" * 64,
            "reviewer_registry_sha256": "c" * 64,
            "privacy_review_log_sha256": "d" * 64,
            "source_receipt_sha256": "e" * 64,
            "study_manifest_sha256": "f" * 64,
            "packet_study_freeze_sha256": "0" * 64,
        }
        rows = [
            {"cluster_id": f"BASE_{index}", "hit": index < 3}
            for index in range(5)
        ]
        result = MODULE.build_export(
            freeze=freeze,
            freeze_hash="1" * 64,
            observation_bundle_hash="2" * 64,
            observation_seal_hash="3" * 64,
            truth_map_hash="4" * 64,
            readiness_report_hash="5" * 64,
            evidence_metadata=evidence,
            execution_metadata={
                "execution_freeze_sha256": "6" * 64,
                "raw_execution_bundle_sha256": "7" * 64,
                "raw_execution_seal_sha256": "8" * 64,
            },
            rows=rows,
            created_at_utc="2026-08-28T04:00:00Z",
        )
        self.assertFalse(result["manuscript_eligible"])
        self.assertEqual(
            result["eligibility"]["manuscript_eligibility_blockers"],
            ["external_authority_signature_not_verified"],
        )


if __name__ == "__main__":
    unittest.main()
