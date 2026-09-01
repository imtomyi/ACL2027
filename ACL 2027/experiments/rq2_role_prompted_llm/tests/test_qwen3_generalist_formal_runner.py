#!/usr/bin/env python3
"""Source-free tests for the formal Qwen3 Generalist runner."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_formal.py"
SPEC = importlib.util.spec_from_file_location("qwen3_generalist_formal_runner_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def private_write(path: Path, value: dict) -> bytes:
    payload = MODULE.canonical_bytes(value)
    path.write_bytes(payload)
    os.chmod(path, 0o600)
    return payload


def valid_rating(*, rationale: str = "SOURCE FREE TEST RATIONALE") -> dict:
    return {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 4,
        "voice_boundary_preservation": 4,
        "scope_calibration": 4,
        "cannot_judge": [],
        "confidence": 4,
        "disposition": "accept",
        "requested_expertise": "none",
        "serious_error_flags": [],
        "rationale": rationale,
    }


def ollama_response(rating: dict) -> bytes:
    return MODULE.canonical_bytes(
        {
            "model": "qwen3:8b",
            "created_at": "2026-08-28T00:00:00Z",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(rating)},
            "prompt_eval_count": 1200,
            "eval_count": 80,
        }
    )


class FormalGeneralistRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.component, cls.assets, cls.component_hash = MODULE.scoring.load_component()

    def make_private_roots(self, root: Path) -> tuple[Path, Path]:
        local = root / "governance" / "local"
        storage = root / "Storage" / "private_run"
        local.mkdir(parents=True)
        storage.mkdir(parents=True)
        os.chmod(local, 0o700)
        os.chmod(storage, 0o700)
        return local, storage

    def test_current_zero_gate_status_reads_no_packet_and_contacts_no_model(self) -> None:
        with (
            mock.patch.object(
                MODULE,
                "open_and_validate_packet_bank",
                side_effect=AssertionError("packet accessed"),
            ),
            mock.patch.object(
                MODULE.reviewer,
                "preflight_service",
                side_effect=AssertionError("model contacted"),
            ),
        ):
            result = MODULE.source_free_dry_run()
        self.assertEqual(result["gate_mode"], "personal_local_only")
        self.assertEqual(result["dreaddit_completed_gate_count"], 0)
        self.assertFalse(result["formal_execution_ready"])
        self.assertFalse(result["packet_bank_accessed"])
        self.assertFalse(result["model_service_contacted"])

    def test_readiness_failure_precedes_packet_access_and_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            local, storage = self.make_private_roots(workspace)
            execution_path = local / "execution.json"
            study_path = local / "study.json"
            readiness_path = local / "readiness.json"
            packet_seal_path = storage / "packet_seal.json"
            private_write(execution_path, {})
            private_write(study_path, {})
            current = json.loads(MODULE.DEFAULT_READINESS.read_text())
            private_write(readiness_path, current)
            private_write(packet_seal_path, {})

            with (
                mock.patch.object(
                    MODULE.scoring,
                    "load_component",
                    return_value=(self.component, self.assets, self.component_hash),
                ),
                mock.patch.object(
                    MODULE.scoring,
                    "validate_study_freeze",
                    return_value={"frozen_at": datetime(2026, 8, 28, tzinfo=timezone.utc)},
                ),
                mock.patch.object(
                    MODULE,
                    "open_and_validate_packet_bank",
                    side_effect=AssertionError("packet accessed"),
                ),
                mock.patch.object(
                    MODULE.reviewer,
                    "preflight_service",
                    side_effect=AssertionError("model contacted"),
                ),
            ):
                with self.assertRaisesRegex(MODULE.FormalRunnerError, "formal_metadata_invalid"):
                    MODULE.run_formal(
                        execution_freeze_path=execution_path,
                        study_freeze_path=study_path,
                        readiness_report_path=readiness_path,
                        packet_bank_seal_path=packet_seal_path,
                        packet_bank_path=storage / "must_not_be_checked.json",
                        observation_bundle_path=storage / "observations.json",
                        observation_seal_path=storage / "observation_seal.json",
                        raw_execution_bundle_path=storage / "raw_executions.json",
                        raw_execution_seal_path=storage / "raw_execution_seal.json",
                        sealed_at_utc="2026-08-28T03:00:00Z",
                        workspace=workspace,
                    )

    def test_packet_seal_failure_precedes_packet_access_and_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            local, storage = self.make_private_roots(workspace)
            execution_path = local / "execution.json"
            study_path = local / "study.json"
            readiness_path = local / "readiness.json"
            packet_seal_path = storage / "packet_seal.json"
            private_write(execution_path, {})
            private_write(study_path, {})
            private_write(readiness_path, {})
            private_write(packet_seal_path, {})
            frozen_at = datetime(2026, 8, 28, tzinfo=timezone.utc)

            with (
                mock.patch.object(
                    MODULE.scoring,
                    "load_component",
                    return_value=(self.component, self.assets, self.component_hash),
                ),
                mock.patch.object(
                    MODULE.scoring,
                    "validate_study_freeze",
                    return_value={"frozen_at": frozen_at},
                ),
                mock.patch.object(
                    MODULE.scoring,
                    "validate_readiness_report",
                    return_value="a" * 64,
                ),
                mock.patch.object(
                    MODULE,
                    "open_and_validate_packet_bank",
                    side_effect=AssertionError("packet accessed"),
                ),
                mock.patch.object(
                    MODULE.reviewer,
                    "preflight_service",
                    side_effect=AssertionError("model contacted"),
                ),
            ):
                with self.assertRaisesRegex(MODULE.FormalRunnerError, "packet_seal_keys_invalid"):
                    MODULE.run_formal(
                        execution_freeze_path=execution_path,
                        study_freeze_path=study_path,
                        readiness_report_path=readiness_path,
                        packet_bank_seal_path=packet_seal_path,
                        packet_bank_path=storage / "must_not_be_checked.json",
                        observation_bundle_path=storage / "observations.json",
                        observation_seal_path=storage / "observation_seal.json",
                        raw_execution_bundle_path=storage / "raw_executions.json",
                        raw_execution_seal_path=storage / "raw_execution_seal.json",
                        sealed_at_utc="2026-08-28T03:00:00Z",
                        workspace=workspace,
                    )

    def test_valid_rating_projection_removes_free_text_rationale(self) -> None:
        item = copy.deepcopy(MODULE.reviewer.inert_canary_item())
        item["item_id"] = "DJI_0000000000000001"
        item["corpus_id"] = "dreaddit"
        metadata = {"component": self.component, "component_assets": self.assets}
        request_bytes = MODULE.canonical_bytes(
            MODULE.reviewer.build_rating_request(
                self.component,
                self.assets,
                item,
                repetition=1,
            )
        )
        raw_rationale = "A phrase that must not persist in the observation bundle."
        with mock.patch.object(
            MODULE,
            "_post_frozen_request",
            return_value=(ollama_response(valid_rating(rationale=raw_rationale)), 200),
        ):
            raw_record, record = MODULE.execute_repetition(
                item,
                repetition=1,
                request_bytes=request_bytes,
                metadata=metadata,
            )
        self.assertIsNotNone(record)
        self.assertEqual(record["terminal_status"], "valid_rating")
        self.assertNotEqual(record["rating"]["rationale"], raw_rationale)
        self.assertEqual(
            record["rating"]["rationale"],
            "Rationale withheld from the source-free scoring bundle.",
        )
        self.assertRegex(record["private_execution_record_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(
            record["private_execution_record_sha256"],
            MODULE.sha256_bytes(MODULE.canonical_bytes(raw_record)),
        )

    def test_network_helper_rejects_calls_without_formal_capability(self) -> None:
        item = copy.deepcopy(MODULE.reviewer.inert_canary_item())
        request_bytes = MODULE.canonical_bytes(
            MODULE.reviewer.build_rating_request(
                self.component,
                self.assets,
                item,
                repetition=1,
            )
        )
        metadata = {
            "component": self.component,
            "component_assets": self.assets,
            "authorized_request_sha256s": {
                f"{item['item_id']}:1": MODULE.sha256_bytes(request_bytes)
            },
        }
        with mock.patch.object(
            MODULE.reviewer.LOCAL_ONLY_OPENER,
            "open",
            side_effect=AssertionError("network contacted"),
        ):
            with self.assertRaisesRegex(MODULE.FormalRunnerError, "formal_network_capability_missing"):
                MODULE._post_frozen_request(
                    item["item_id"],
                    repetition=1,
                    request_bytes=request_bytes,
                    metadata=metadata,
                    capability=object(),
                )

    def test_execution_freeze_binds_every_packet_seal_hash_and_raw_retention_scope(self) -> None:
        bindings = {
            key: f"{index + 1:x}" * 64
            for index, key in enumerate(sorted(MODULE.PACKET_SEAL_BINDING_KEYS))
        }
        study = {
            "frozen_at_utc": "2026-08-28T01:00:00Z",
            "authorization": {
                "approval_record_id": "APPROVAL_SOURCE_FREE_TEST",
                "approval_record_sha256": "e" * 64,
            },
        }
        study_bytes = MODULE.canonical_bytes(study)
        readiness_bytes = b"source-free-readiness-fixture\n"
        packet_seal_bytes = b"source-free-packet-seal-fixture\n"
        packet_metadata = {
            "packet_bank_sha256": "a" * 64,
            "item_count": 5,
            "item_id_set_sha256": "b" * 64,
            "bindings": bindings,
        }
        execution = {
            "document_type": "warrantroute_qwen3_generalist_execution_freeze_v1",
            "execution_version": "source-free-test-v1",
            "status": "bound_to_authorized_study_freeze",
            "frozen_at_utc": "2026-08-28T02:00:00Z",
            "contains_source_text": False,
            "study_freeze_sha256": MODULE.sha256_bytes(study_bytes),
            "readiness_report_sha256": MODULE.sha256_bytes(readiness_bytes),
            "packet_bank_seal_sha256": MODULE.sha256_bytes(packet_seal_bytes),
            "packet_bank_sha256": "a" * 64,
            "packet_bank_item_count": 5,
            "item_id_set_sha256": "b" * 64,
            "runner_sha256": MODULE.sha256_bytes(MODULE.read_regular_bytes(SCRIPT, code_prefix="test_runner")),
            "runner_contract_sha256": MODULE.sha256_bytes(
                MODULE.read_regular_bytes(MODULE.CONTRACT, code_prefix="test_contract")
            ),
            "primary_repetition": 1,
            "failure_policy": "one_attempt_per_item_all_failures_retained_as_misses",
            "output_policy": copy.deepcopy(MODULE.OUTPUT_POLICY),
            "packet_seal_bindings": copy.deepcopy(bindings),
            "raw_retention_deletion_scope": {
                "approval_record_id": "APPROVAL_SOURCE_FREE_TEST",
                "approval_record_sha256": "e" * 64,
                "readiness_gate_id": "retention_deletion_controls",
                "storage_scope": "restricted_mode_0600_storage",
                "raw_source_bearing_records_approved": True,
                "authorized_accessor_group_id": "ACCESS_GROUP_SOURCE_FREE_TEST",
                "retention_until_utc": "2027-08-28T00:00:00Z",
                "deletion_required": True,
                "deletion_record_required": True,
            },
        }
        MODULE.validate_execution_freeze(
            execution,
            study_freeze=study,
            study_freeze_bytes=study_bytes,
            readiness_bytes=readiness_bytes,
            packet_seal_bytes=packet_seal_bytes,
            packet_seal_metadata=packet_metadata,
        )
        for key in MODULE.PACKET_SEAL_BINDING_KEYS:
            drifted = copy.deepcopy(execution)
            drifted["packet_seal_bindings"][key] = MODULE.sha256_bytes(
                f"drift:{key}".encode("utf-8")
            )
            with self.subTest(binding=key):
                with self.assertRaisesRegex(
                    MODULE.FormalRunnerError,
                    "execution_packet_seal_bindings_drift",
                ):
                    MODULE.validate_execution_freeze(
                        drifted,
                        study_freeze=study,
                        study_freeze_bytes=study_bytes,
                        readiness_bytes=readiness_bytes,
                        packet_seal_bytes=packet_seal_bytes,
                        packet_seal_metadata=packet_metadata,
                    )
        unapproved = copy.deepcopy(execution)
        unapproved["raw_retention_deletion_scope"]["raw_source_bearing_records_approved"] = False
        with self.assertRaisesRegex(MODULE.FormalRunnerError, "raw_retention_not_approved"):
            MODULE.validate_execution_freeze(
                unapproved,
                study_freeze=study,
                study_freeze_bytes=study_bytes,
                readiness_bytes=readiness_bytes,
                packet_seal_bytes=packet_seal_bytes,
                packet_seal_metadata=packet_metadata,
            )

    def test_successful_inert_path_writes_only_sealed_storage_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            _, storage = self.make_private_roots(workspace)
            bundle_path = storage / "observations.json"
            seal_path = storage / "observation_seal.json"
            raw_bundle_path = storage / "raw_executions.json"
            raw_seal_path = storage / "raw_execution_seal.json"
            item = copy.deepcopy(MODULE.reviewer.inert_canary_item())
            item["item_id"] = "DJI_0000000000000001"
            item["corpus_id"] = "dreaddit"
            metadata = {
                "component": self.component,
                "component_assets": self.assets,
                "study_freeze_sha256": "1" * 64,
                "execution_freeze_sha256": "2" * 64,
                "packet_seal_sha256": "3" * 64,
                "frozen_at": datetime(2026, 8, 28, tzinfo=timezone.utc),
                "execution_freeze": {
                    "runner_sha256": "4" * 64,
                    "runner_contract_sha256": "5" * 64,
                    "raw_retention_deletion_scope": {
                        "retention_until_utc": "2027-08-28T00:00:00Z"
                    },
                },
            }
            identity = {
                "status": "passed",
                "endpoint": "http://127.0.0.1:11434",
                "ollama_version": "0.18.0",
                "model_id": "qwen3:8b",
                "model_digest": MODULE.reviewer.EXPECTED_MODEL_DIGEST,
                "source_text_accessed": False,
            }
            with (
                mock.patch.object(MODULE, "validate_metadata", return_value=metadata),
                mock.patch.object(MODULE, "open_and_validate_packet_bank", return_value=[item]),
                mock.patch.object(MODULE.reviewer, "preflight_service", side_effect=[identity, identity]),
                mock.patch.object(
                    MODULE.reviewer,
                    "build_rating_request",
                    wraps=MODULE.reviewer.build_rating_request,
                ) as build,
                mock.patch.object(
                    MODULE,
                    "_post_frozen_request",
                    return_value=(ollama_response(valid_rating()), 200),
                ) as post,
            ):
                result = MODULE.run_formal(
                    execution_freeze_path=workspace / "unused_execution.json",
                    study_freeze_path=workspace / "unused_study.json",
                    readiness_report_path=workspace / "unused_readiness.json",
                    packet_bank_seal_path=workspace / "unused_packet_seal.json",
                    packet_bank_path=workspace / "unused_packet_bank.json",
                    observation_bundle_path=bundle_path,
                    observation_seal_path=seal_path,
                    raw_execution_bundle_path=raw_bundle_path,
                    raw_execution_seal_path=raw_seal_path,
                    sealed_at_utc="2026-08-28T03:00:00Z",
                    workspace=workspace,
                )
            self.assertEqual(build.call_count, 3)
            self.assertEqual(post.call_count, 3)
            self.assertEqual(result["status"], "complete")
            self.assertFalse(result["manuscript_value_created"])
            bundle = json.loads(bundle_path.read_text())
            seal = json.loads(seal_path.read_text())
            raw_bundle = json.loads(raw_bundle_path.read_text())
            raw_seal = json.loads(raw_seal_path.read_text())
            self.assertEqual(len(bundle["records"]), 1)
            self.assertEqual(len(raw_bundle["records"]), 3)
            self.assertEqual(
                [row["rating_repetition"] for row in raw_bundle["records"]],
                [1, 2, 3],
            )
            self.assertEqual(
                [row["seed"] for row in raw_bundle["records"]],
                [2027082601, 2027082602, 2027082603],
            )
            self.assertEqual(bundle["records"][0]["terminal_status"], "valid_rating")
            self.assertNotIn("SOURCE FREE TEST RATIONALE", bundle_path.read_text())
            self.assertIn("SOURCE FREE TEST RATIONALE", raw_bundle_path.read_text())
            self.assertFalse(seal["source_text_included"])
            self.assertEqual(
                seal["document_type"],
                "warrantroute_qwen3_generalist_observation_seal_v2",
            )
            self.assertEqual(seal["seal_version"], "qwen3-generalist-observation-seal-v2")
            self.assertTrue(raw_bundle["contains_source_text"])
            self.assertFalse(raw_seal["contains_source_text"])
            self.assertTrue(raw_seal["sealed_bundle_contains_source_text"])
            self.assertEqual(
                raw_seal["raw_execution_bundle_sha256"],
                MODULE.sha256_bytes(raw_bundle_path.read_bytes()),
            )
            self.assertEqual(
                bundle["records"][0]["private_execution_record_sha256"],
                MODULE.sha256_bytes(MODULE.canonical_bytes(raw_bundle["records"][0])),
            )
            self.assertEqual(seal["observation_bundle_sha256"], MODULE.sha256_bytes(bundle_path.read_bytes()))
            self.assertEqual(seal["execution_freeze_sha256"], "2" * 64)
            self.assertEqual(seal["packet_bank_seal_sha256"], "3" * 64)
            self.assertEqual(seal["runner_sha256"], "4" * 64)
            self.assertEqual(seal["runner_contract_sha256"], "5" * 64)
            self.assertEqual(
                seal["raw_execution_bundle_sha256"],
                MODULE.sha256_bytes(raw_bundle_path.read_bytes()),
            )
            self.assertEqual(
                seal["raw_execution_seal_sha256"],
                MODULE.sha256_bytes(raw_seal_path.read_bytes()),
            )
            primary_map = {
                bundle["records"][0]["item_id"]:
                bundle["records"][0]["private_execution_record_sha256"]
            }
            self.assertEqual(
                seal["primary_raw_record_hash_map_sha256"],
                MODULE.sha256_bytes(MODULE.canonical_bytes(primary_map)),
            )
            self.assertEqual(
                seal["primary_raw_record_hash_set_sha256"],
                MODULE.sha256_bytes(
                    MODULE.canonical_bytes(sorted(primary_map.values()))
                ),
            )
            self.assertEqual(os.stat(bundle_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(seal_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(raw_bundle_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(raw_seal_path).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
