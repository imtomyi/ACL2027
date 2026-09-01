#!/usr/bin/env python3
"""Source-free tests for the external Qwen3 Generalist score gate."""

from __future__ import annotations

import copy
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/promote_qwen3_generalist_score.py"
SPEC = importlib.util.spec_from_file_location("qwen3_score_promotion_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
REAL_REGISTRY_GUARD = MODULE.require_non_operator_controlled_registry_path


def inert_internal_export() -> dict:
    input_hashes = {
        key: MODULE.sha256_bytes(f"INERT:{key}".encode("utf-8"))
        for key in MODULE.INPUT_HASH_KEYS
    }
    return {
        "document_type": "warrantroute_qwen3_generalist_scoring_export_v1",
        "export_version": "qwen3-generalist-score-v1",
        "created_at_utc": "2026-08-28T03:00:00Z",
        "status": "complete_internal_only",
        "manuscript_eligible": False,
        "dataset": copy.deepcopy(MODULE.EXPECTED_DATASET),
        "method": {
            "name": MODULE.EXPECTED_METHOD_NAME,
            "reviewer_actor_id": MODULE.EXPECTED_REVIEWER_ACTOR,
            "model_id": MODULE.EXPECTED_MODEL_ID,
            "model_digest": MODULE.EXPECTED_MODEL_DIGEST,
            "primary_repetition": 1,
        },
        "candidate_generation": {
            "model_id": "inert-independent-generator",
            "snapshot_sha256": "1" * 64,
            "prompt_sha256": "2" * 64,
        },
        "metric": {
            "name": MODULE.EXPECTED_METRIC,
            "tp": 3,
            "fn": 2,
            "n": 5,
            "tp_over_n": "3/5",
            "recall": 0.6,
            "recall_percent": 60.0,
            "confidence_level": 0.95,
            "ci_method": "cluster_bootstrap_percentile",
            "recall_95_ci": [0.2, 1.0],
            "recall_95_ci_percent": [20.0, 100.0],
            "source_cluster_unit": "post",
            "bootstrap_cluster_unit": "base_packet_connected_component",
            "independent_cluster_count": 5,
            "bootstrap_resamples": 10_000,
            "bootstrap_seed": 20_270_826,
        },
        "eligibility": {
            "authorization_record_id": "INERT_LOCAL_RECORD",
            "authorization_record_sha256": "3" * 64,
            "privacy_cleared_packet_bank": True,
            "clean_preaccess_record": True,
            "formal_readiness_report_passed": True,
            "candidate_generator_distinct_from_reviewer": True,
            "complete_fixed_denominator": True,
            "all_failures_retained_as_misses": True,
            "ci_estimable": True,
            "exact_local_authority_and_evidence_records_verified": True,
            "external_authority_signature_verified": False,
            "external_authority_gate_satisfied": False,
            "manuscript_eligibility_blockers": [
                "external_authority_signature_not_verified"
            ],
            "authority_limitation": "INERT TEST: external authority remains absent.",
        },
        "input_hashes": input_hashes,
    }


def signed_record(
    internal: dict,
    *,
    internal_file_hash: str,
    authority_id: str,
    key_fingerprint: str,
) -> dict:
    bindings = MODULE.expected_signed_bindings(internal, internal_file_hash)
    return {
        "document_type": "warrantroute_qwen3_generalist_external_score_promotion_v1",
        "promotion_version": "qwen3-generalist-external-promotion-v1",
        "authority": {
            "authority_id": authority_id,
            "authority_role": "manuscript_reporting_authority",
            "trusted_public_key_spki_sha256": key_fingerprint,
        },
        "decision": {
            "decision_id": "INERT_DECISION_001",
            "decision_status": "approved",
            "manuscript_reporting_authorized": True,
        },
        "validity": {
            "approved_at_utc": "2026-08-28T05:00:00Z",
            "not_before_utc": "2026-08-28T04:00:00Z",
            "expires_at_utc": "2026-09-28T04:00:00Z",
        },
        "scope": {
            "project_id": MODULE.EXPECTED_PROJECT_ID,
            "study_id": MODULE.EXPECTED_STUDY_ID,
            "row_id": MODULE.EXPECTED_ROW_ID,
            "reporting_purpose": MODULE.EXPECTED_REPORTING_PURPOSE,
            "dataset": copy.deepcopy(MODULE.EXPECTED_DATASET),
            "method_name": MODULE.EXPECTED_METHOD_NAME,
            "reviewer_actor_id": MODULE.EXPECTED_REVIEWER_ACTOR,
            "model_id": MODULE.EXPECTED_MODEL_ID,
            "model_digest": MODULE.EXPECTED_MODEL_DIGEST,
            "metric_name": MODULE.EXPECTED_METRIC,
        },
        **bindings,
        "attestations": {
            "aggregate_only_reviewed": True,
            "source_text_absent_from_promotion_record": True,
            "scope_limited_to_bound_score": True,
        },
    }


class PromotionFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name).resolve()
        self.storage_dir = self.workspace / "Storage" / "promotion"
        self.authority_dir = self.workspace / "governance" / "local" / "promotion"
        for directory in (self.storage_dir, self.authority_dir):
            directory.mkdir(parents=True)
            os.chmod(directory, 0o700)

        self.internal = inert_internal_export()
        self.internal_path = self.storage_dir / "internal.json"
        self.record_path = self.authority_dir / "record.json"
        self.signature_path = self.authority_dir / "record.sig"
        self.key_path = self.authority_dir / "authority.pem"
        self.output_path = self.storage_dir / "promoted.json"
        self.authority_id = "INERT_EXTERNAL_AUTHORITY"

        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.key_der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.key_fingerprint = MODULE.sha256_bytes(self.key_der)
        self.registry_dir = self.workspace / "isolated-test-trust"
        self.registry_dir.mkdir()
        os.chmod(self.registry_dir, 0o700)
        self.registry_path = self.registry_dir / "registry.json"
        self.registry = {
            "document_type": "warrantroute_qwen3_generalist_trusted_authority_registry_v1",
            "registry_version": "qwen3-generalist-trusted-authority-registry-v1",
            "registry_id": "INERT_TEST_REGISTRY",
            "status": "active",
            "issued_at_utc": "2026-08-28T01:00:00Z",
            "authorities": [
                {
                    "authority_id": self.authority_id,
                    "authority_role": "manuscript_reporting_authority",
                    "public_key_spki_sha256": self.key_fingerprint,
                    "active_from_utc": "2026-08-28T02:00:00Z",
                    "active_until_utc": "2026-10-28T02:00:00Z",
                    "allowed_scope": MODULE.expected_promotion_scope(),
                }
            ],
        }
        self.write_file(self.registry_path, MODULE.canonical_bytes(self.registry))
        self.write_file(self.key_path, self.key_pem)
        self.rewrite_internal(self.internal)
        internal_hash = MODULE.sha256_bytes(MODULE.canonical_bytes(self.internal))
        self.record = signed_record(
            self.internal,
            internal_file_hash=internal_hash,
            authority_id=self.authority_id,
            key_fingerprint=self.key_fingerprint,
        )
        self.resign_record()

    @staticmethod
    def write_file(path: Path, data: bytes) -> None:
        path.write_bytes(data)
        os.chmod(path, 0o600)

    def rewrite_internal(self, value: dict) -> None:
        self.write_file(self.internal_path, MODULE.canonical_bytes(value))

    def resign_record(self) -> None:
        payload = MODULE.canonical_bytes(self.record)
        self.write_file(self.record_path, payload)
        self.write_file(self.signature_path, self.private_key.sign(payload))

    def promote(self, *, checked_at: str = "2026-08-28T06:00:00Z") -> dict:
        return MODULE.promote_score(
            internal_export_path=self.internal_path,
            promotion_record_path=self.record_path,
            detached_signature_path=self.signature_path,
            trusted_public_key_path=self.key_path,
            trusted_authority_id=self.authority_id,
            output_path=self.output_path,
            workspace=self.workspace,
            verification_time=datetime.fromisoformat(
                checked_at[:-1] + "+00:00"
            ).astimezone(timezone.utc),
        )

    def close(self) -> None:
        self.temporary.cleanup()


class ScorePromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = PromotionFixture()
        # Production has no override. Tests patch the fixed path and its
        # root-ownership check only inside this isolated process.
        self.registry_path_patch = mock.patch.object(
            MODULE, "SYSTEM_TRUST_REGISTRY", self.fixture.registry_path
        )
        self.registry_guard_patch = mock.patch.object(
            MODULE,
            "require_non_operator_controlled_registry_path",
            side_effect=lambda path: path.resolve(strict=True),
        )
        self.registry_path_patch.start()
        self.registry_guard_patch.start()

    def tearDown(self) -> None:
        self.registry_guard_patch.stop()
        self.registry_path_patch.stop()
        self.fixture.close()

    def test_valid_external_record_produces_private_aggregate_only_output(self) -> None:
        result = self.fixture.promote()
        self.assertTrue(result["manuscript_eligible"])
        self.assertTrue(result["aggregate_only"])
        self.assertFalse(result["contains_source_text"])
        self.assertEqual(
            result["authorization"]["trusted_authority_registry_id"],
            "INERT_TEST_REGISTRY",
        )
        self.assertEqual(stat_mode(self.fixture.output_path), 0o600)
        written = MODULE.strict_json_loads(self.fixture.output_path.read_bytes())
        forbidden_keys = {
            "item_id",
            "excerpt",
            "rationale",
            "records",
            "rating",
            "required_flag",
            "packet_text",
            "theme_statement",
        }

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(written)

    def test_forged_detached_signature_is_rejected_without_output(self) -> None:
        signature = bytearray(self.fixture.signature_path.read_bytes())
        signature[0] ^= 1
        self.fixture.write_file(self.fixture.signature_path, bytes(signature))
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "detached_signature_invalid"):
            self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_changed_internal_export_breaks_signed_binding(self) -> None:
        changed = copy.deepcopy(self.fixture.internal)
        changed["input_hashes"]["study_freeze_sha256"] = "f" * 64
        self.fixture.rewrite_internal(changed)
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "signed_aggregate_binding_mismatch"):
            self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_expired_authorization_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "promotion_expired"):
            self.fixture.promote(checked_at="2026-09-29T00:00:00Z")
        self.assertFalse(self.fixture.output_path.exists())

    def test_wrong_scope_is_rejected_even_with_valid_signature(self) -> None:
        self.fixture.record["scope"]["dataset"]["split"] = "train"
        self.fixture.resign_record()
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "promotion_scope_mismatch"):
            self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_wrong_authority_id_is_rejected_even_with_valid_signature(self) -> None:
        self.fixture.record["authority"]["authority_id"] = "INERT_OTHER_AUTHORITY"
        self.fixture.resign_record()
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "authority_id_mismatch"):
            self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_local_key_and_arbitrary_authority_cannot_establish_trust(self) -> None:
        missing_registry = self.fixture.workspace / "operator-cannot-install-here.json"
        with mock.patch.object(MODULE, "SYSTEM_TRUST_REGISTRY", missing_registry), mock.patch.object(
            MODULE,
            "require_non_operator_controlled_registry_path",
            REAL_REGISTRY_GUARD,
        ):
            with self.assertRaisesRegex(
                MODULE.ScorePromotionError,
                "trusted_authority_registry_unavailable",
            ):
                self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_operator_writable_registry_cannot_establish_trust(self) -> None:
        with mock.patch.object(
            MODULE, "SYSTEM_TRUST_REGISTRY", self.fixture.registry_path
        ), mock.patch.object(
            MODULE,
            "require_non_operator_controlled_registry_path",
            REAL_REGISTRY_GUARD,
        ):
            with self.assertRaisesRegex(
                MODULE.ScorePromotionError,
                "trusted_registry_(not_root_owned|is_writable)",
            ):
                self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_reporting_permission_must_be_explicit(self) -> None:
        self.fixture.record["decision"]["manuscript_reporting_authorized"] = False
        self.fixture.resign_record()
        with self.assertRaisesRegex(MODULE.ScorePromotionError, "manuscript_reporting_not_authorized"):
            self.fixture.promote()
        self.assertFalse(self.fixture.output_path.exists())

    def test_contract_and_dry_run_keep_authority_gate_closed(self) -> None:
        contract = MODULE.CONTRACT.read_text(encoding="utf-8")
        self.assertIn("detached Ed25519 signature", contract)
        self.assertIn("all 21 evidence-chain hashes", contract)
        summary = MODULE.source_free_summary()
        self.assertFalse(summary["manuscript_eligible"])
        self.assertTrue(summary["system_trust_registry_present"])
        self.assertFalse(summary["outputs_written"])


def stat_mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
