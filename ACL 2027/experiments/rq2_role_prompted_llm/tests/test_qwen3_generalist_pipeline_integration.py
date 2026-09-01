#!/usr/bin/env python3
"""Inert cross-component tests for the formal Generalist pipeline."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SEALER_TEST = load_module(
    "qwen3_pipeline_sealer_fixture",
    ROOT
    / "experiments/rq2_role_prompted_llm/tests/test_qwen3_generalist_packet_bank_sealer.py",
)
RUNNER = load_module(
    "qwen3_pipeline_runner",
    ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_formal.py",
)
SCORER = load_module(
    "qwen3_pipeline_scorer",
    ROOT / "experiments/rq2_role_prompted_llm/scripts/export_qwen3_generalist_score.py",
)


def inert_rating() -> dict:
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
        "rationale": "INERT PIPELINE SOFTWARE TEST RATIONALE",
    }


def ollama_response() -> bytes:
    return RUNNER.canonical_bytes(
        {
            "model": RUNNER.EXPECTED_MODEL_ID,
            "created_at": "2026-08-28T00:00:00Z",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(inert_rating())},
            "prompt_eval_count": 1200,
            "eval_count": 80,
        }
    )


class LatestPipelineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = SEALER_TEST.PacketSealFixture(
            Path(self.temporary.name).resolve()
        )
        self.fixture.seal()
        self.packet_seal_bytes = self.fixture.output_path.read_bytes()
        self.packet_seal = json.loads(self.packet_seal_bytes)
        self.component, self.assets, self.component_hash = RUNNER.scoring.load_component()
        bindings = self.packet_seal["bindings"]
        self.study = {
            "frozen_at_utc": "2026-08-28T04:00:00Z",
            "authorization": {
                "approval_record_id": "APPROVAL_SOURCE_FREE_PIPELINE_TEST",
                "approval_record_sha256": "e" * 64,
            },
            "candidate_generation_separation": {
                "candidate_generator_actor_id": self.packet_seal[
                    "candidate_generator_actor_id"
                ],
                "candidate_generator_snapshot_sha256": self.packet_seal[
                    "candidate_generator_snapshot_sha256"
                ],
            },
            "packet_bank": {
                "seal_id": self.packet_seal["seal_id"],
                "seal_sha256": RUNNER.sha256_bytes(self.packet_seal_bytes),
                "item_count": self.packet_seal["item_count"],
                "item_id_set_sha256": self.packet_seal["item_id_set_sha256"],
            },
            "evidence_records": {
                "packet_study_freeze_sha256": bindings[
                    "packet_study_freeze_sha256"
                ],
                "governance_record_sha256": bindings["governance_record_sha256"],
                "reviewer_registry_sha256": bindings["reviewer_registry_sha256"],
                "privacy_review_log_sha256": bindings["privacy_review_log_sha256"],
                "source_receipt_sha256": bindings["source_receipt_sha256"],
            },
            "preaccess": {"record_sha256": bindings["preaccess_record_sha256"]},
            "assets": {
                "scoring_contract_sha256": bindings["scoring_contract_sha256"],
                "scoring_exporter_sha256": bindings["analysis_code_sha256"],
            },
        }
        self.study_bytes = RUNNER.canonical_bytes(self.study)
        self.readiness_bytes = self.fixture.readiness_path.read_bytes()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate_latest_packet_seal(self) -> dict:
        bindings = self.packet_seal["bindings"]
        metadata = RUNNER.validate_packet_seal(
            self.packet_seal,
            seal_bytes=self.packet_seal_bytes,
            freeze=self.study,
            readiness_hash=RUNNER.sha256_bytes(self.readiness_bytes),
            component_hash=self.component_hash,
            evaluator_schema_hash=self.component["assets"]["evaluator_item_schema"][
                "sha256"
            ],
        )
        SCORER.validate_packet_bank_seal(
            self.packet_seal,
            seal_bytes=self.packet_seal_bytes,
            freeze=self.study,
            readiness_report_hash=bindings["readiness_report_sha256"],
            truth_map_hash=bindings["truth_cluster_map_sha256"],
            component_hash=self.component_hash,
            evaluator_schema_hash=bindings["evaluator_item_schema_sha256"],
            truth_schema_hash=bindings["truth_cluster_map_schema_sha256"],
            packet_freeze_schema_hash=bindings["study_freeze_schema_sha256"],
        )
        return metadata

    def execution_freeze(self, packet_metadata: dict) -> dict:
        retention = {
            "approval_record_id": self.study["authorization"]["approval_record_id"],
            "approval_record_sha256": self.study["authorization"][
                "approval_record_sha256"
            ],
            "readiness_gate_id": "retention_deletion_controls",
            "storage_scope": "restricted_mode_0600_storage",
            "raw_source_bearing_records_approved": True,
            "authorized_accessor_group_id": "ACCESS_GROUP_SOURCE_FREE_PIPELINE_TEST",
            "retention_until_utc": "2027-08-28T00:00:00Z",
            "deletion_required": True,
            "deletion_record_required": True,
        }
        return {
            "document_type": "warrantroute_qwen3_generalist_execution_freeze_v1",
            "execution_version": "qwen3-generalist-formal-execution-v1",
            "status": "bound_to_authorized_study_freeze",
            "frozen_at_utc": "2026-08-28T05:00:00Z",
            "contains_source_text": False,
            "study_freeze_sha256": RUNNER.sha256_bytes(self.study_bytes),
            "readiness_report_sha256": RUNNER.sha256_bytes(self.readiness_bytes),
            "packet_bank_seal_sha256": RUNNER.sha256_bytes(self.packet_seal_bytes),
            "packet_bank_sha256": packet_metadata["packet_bank_sha256"],
            "packet_bank_item_count": packet_metadata["item_count"],
            "item_id_set_sha256": packet_metadata["item_id_set_sha256"],
            "runner_sha256": RUNNER.sha256_bytes(
                RUNNER.read_regular_bytes(RUNNER.SCRIPT, code_prefix="integration_runner")
            ),
            "runner_contract_sha256": RUNNER.sha256_bytes(
                RUNNER.read_regular_bytes(
                    RUNNER.CONTRACT, code_prefix="integration_contract"
                )
            ),
            "primary_repetition": 1,
            "failure_policy": "one_attempt_per_item_all_failures_retained_as_misses",
            "output_policy": copy.deepcopy(RUNNER.OUTPUT_POLICY),
            "packet_seal_bindings": copy.deepcopy(packet_metadata["bindings"]),
            "raw_retention_deletion_scope": retention,
        }

    def run_inert_pipeline(self) -> dict:
        packet_metadata = self.validate_latest_packet_seal()
        execution = self.execution_freeze(packet_metadata)
        execution_bytes = RUNNER.canonical_bytes(execution)
        RUNNER.validate_execution_freeze(
            execution,
            study_freeze=self.study,
            study_freeze_bytes=self.study_bytes,
            readiness_bytes=self.readiness_bytes,
            packet_seal_bytes=self.packet_seal_bytes,
            packet_seal_metadata=packet_metadata,
        )
        storage = self.fixture.storage_run
        paths = {
            "bundle": storage / "pipeline_observations.json",
            "seal": storage / "pipeline_observation_seal.json",
            "raw_bundle": storage / "pipeline_raw_executions.json",
            "raw_seal": storage / "pipeline_raw_execution_seal.json",
        }
        metadata = {
            "component": self.component,
            "component_assets": self.assets,
            "study_freeze_sha256": RUNNER.sha256_bytes(self.study_bytes),
            "execution_freeze_sha256": RUNNER.sha256_bytes(execution_bytes),
            "packet_seal_sha256": RUNNER.sha256_bytes(self.packet_seal_bytes),
            "frozen_at": datetime(2026, 8, 28, 4, tzinfo=timezone.utc),
            "execution_freeze": execution,
        }
        identity = {
            "status": "passed",
            "endpoint": "http://127.0.0.1:11434",
            "ollama_version": RUNNER.reviewer.EXPECTED_OLLAMA_VERSION,
            "model_id": RUNNER.EXPECTED_MODEL_ID,
            "model_digest": RUNNER.reviewer.EXPECTED_MODEL_DIGEST,
            "source_text_accessed": False,
        }
        with (
            mock.patch.object(RUNNER, "validate_metadata", return_value=metadata),
            mock.patch.object(
                RUNNER,
                "open_and_validate_packet_bank",
                return_value=copy.deepcopy(self.fixture.items),
            ),
            mock.patch.object(
                RUNNER.reviewer, "preflight_service", side_effect=[identity, identity]
            ),
            mock.patch.object(
                RUNNER, "_post_frozen_request", return_value=(ollama_response(), 200)
            ),
        ):
            RUNNER.run_formal(
                execution_freeze_path=Path("unused_execution"),
                study_freeze_path=Path("unused_study"),
                readiness_report_path=Path("unused_readiness"),
                packet_bank_seal_path=Path("unused_packet_seal"),
                packet_bank_path=Path("unused_packet_bank"),
                observation_bundle_path=paths["bundle"],
                observation_seal_path=paths["seal"],
                raw_execution_bundle_path=paths["raw_bundle"],
                raw_execution_seal_path=paths["raw_seal"],
                sealed_at_utc="2026-08-28T06:00:00Z",
                workspace=self.fixture.root,
            )
        bundle_bytes = paths["bundle"].read_bytes()
        bundle = json.loads(bundle_bytes)
        observations = SCORER.validate_observation_bundle(
            bundle,
            freeze=self.study,
            freeze_hash=RUNNER.sha256_bytes(self.study_bytes),
            rating_schema=self.assets["shared_rating_schema"],
        )
        seal_bytes = paths["seal"].read_bytes()
        observation_seal = json.loads(seal_bytes)
        SCORER.validate_observation_seal(
            observation_seal,
            seal_bytes=seal_bytes,
            bundle_bytes=bundle_bytes,
            freeze=self.study,
            freeze_hash=RUNNER.sha256_bytes(self.study_bytes),
            frozen_at=datetime(2026, 8, 28, 4, tzinfo=timezone.utc),
        )
        raw_bundle_bytes = paths["raw_bundle"].read_bytes()
        raw_seal_bytes = paths["raw_seal"].read_bytes()
        chain = {
            "execution_freeze": execution,
            "execution_freeze_bytes": execution_bytes,
            "study_freeze": self.study,
            "study_freeze_bytes": self.study_bytes,
            "readiness_bytes": self.readiness_bytes,
            "packet_seal": self.packet_seal,
            "packet_seal_bytes": self.packet_seal_bytes,
            "raw_bundle": json.loads(raw_bundle_bytes),
            "raw_bundle_bytes": raw_bundle_bytes,
            "raw_seal": json.loads(raw_seal_bytes),
            "raw_seal_bytes": raw_seal_bytes,
            "observations": observations,
            "observation_seal": observation_seal,
            "rating_schema": self.assets["shared_rating_schema"],
            "component": self.component,
        }
        SCORER.validate_execution_chain(**chain)
        return chain

    def test_latest_sealer_runner_scorer_chain_is_compatible(self) -> None:
        chain = self.run_inert_pipeline()
        self.assertEqual(len(chain["observations"]), self.packet_seal["item_count"])
        self.assertEqual(
            len(chain["raw_bundle"]["records"]), self.packet_seal["item_count"] * 3
        )

    def test_latest_shape_and_commitment_mutations_fail_closed(self) -> None:
        missing = copy.deepcopy(self.packet_seal)
        del missing["candidate_generator_prompt_sha256"]
        with self.assertRaisesRegex(RUNNER.FormalRunnerError, "packet_seal_keys_invalid"):
            RUNNER.validate_packet_seal(
                missing,
                seal_bytes=self.packet_seal_bytes,
                freeze=self.study,
                readiness_hash=RUNNER.sha256_bytes(self.readiness_bytes),
                component_hash=self.component_hash,
                evaluator_schema_hash=self.component["assets"][
                    "evaluator_item_schema"
                ]["sha256"],
            )
        chain = self.run_inert_pipeline()
        chain["observation_seal"] = copy.deepcopy(chain["observation_seal"])
        chain["observation_seal"]["primary_raw_record_hash_set_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            SCORER.ScoringExportError, "observation_seal_primary_raw_set_drift"
        ):
            SCORER.validate_execution_chain(**chain)


if __name__ == "__main__":
    unittest.main()
