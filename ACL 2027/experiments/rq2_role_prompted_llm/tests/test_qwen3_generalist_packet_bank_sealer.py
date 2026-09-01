#!/usr/bin/env python3
"""Source-free tests for the Qwen3 Generalist packet-bank sealer."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    ROOT
    / "experiments"
    / "rq2_role_prompted_llm"
    / "scripts"
    / "seal_qwen3_generalist_packet_bank.py"
)
SPEC = importlib.util.spec_from_file_location("qwen3_packet_bank_sealer_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


FAMILIES = tuple(MODULE.EXPECTED_FAMILY_TO_FLAG)


def file_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_private_json(path: Path, value: dict) -> None:
    path.write_bytes(file_bytes(value))
    os.chmod(path, 0o600)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inert_item(index: int) -> dict:
    excerpt_id = f"EXC_{index:08d}"
    source_id = f"SRC_{index:08d}"
    return {
        "item_schema_version": "direction-j-evaluator-item-v1",
        "item_id": f"DJI_{index:016x}",
        "packet_id": f"PKT_{index:08d}",
        "output_id": f"OUT_{index:08d}",
        "corpus_id": "dreaddit",
        "research_question": "Source-free software interface fixture question.",
        "analytic_contract": {
            "contract_id": "source_free_test_contract",
            "contract_version": "v1",
            "task_description": "Validate a software interface fixture.",
            "validity_rules": ["Use only the inert fixture payload."],
        },
        "context_note": "This is inert software-test material, not corpus text.",
        "proposed_interpretation": {
            "theme_id": f"T{index:02d}",
            "theme_name": "Interface fixture",
            "claim": "The fixture contains a bounded software-test statement.",
            "explanation": "The statement is limited to the fixture.",
            "boundary_conditions": ["No empirical meaning is assigned."],
        },
        "evidence": [
            {
                "display_order": 1,
                "excerpt_id": excerpt_id,
                "source_id": source_id,
                "speaker_id": None,
                "local_context": "Inert interface-fixture context.",
                "text": "Inert interface-fixture evidence.",
                "candidate_role": "support",
                "candidate_attributed_excerpt_id": excerpt_id,
                "candidate_attributed_source_id": source_id,
                "candidate_attributed_speaker_id": None,
                "candidate_quote": "Inert interface-fixture evidence.",
                "candidate_warrant": "The fixture supports only the interface check.",
            }
        ],
        "source_coverage": {
            "presented_excerpt_count": 1,
            "presented_source_count": 1,
            "candidate_cited_excerpt_count": 1,
            "candidate_cited_source_count": 1,
            "sampling_frame_excerpt_count": 1,
            "sampling_frame_source_count": 1,
            "source_distribution": [
                {
                    "source_id": source_id,
                    "presented_excerpt_count": 1,
                    "candidate_cited_excerpt_count": 1,
                }
            ],
            "coverage_note": "Source-free interface fixture only.",
        },
    }


class PacketSealFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.governance_local = root / "governance" / "local"
        self.storage_run = root / "Storage" / "authorized_packet_fixture"
        self.dataset_manifests = root / "dataset" / "manifests"
        self.governance_local.mkdir(parents=True)
        self.storage_run.mkdir(parents=True)
        self.dataset_manifests.mkdir(parents=True)
        os.chmod(self.governance_local, 0o700)
        os.chmod(self.storage_run, 0o700)
        self._copy_public_assets()

        self.study_id = "rq2_dreaddit_qwen3_fixture"
        self.study_design_freeze_sha256 = "7" * 64
        self.items = [inert_item(index) for index in range(1, 6)]
        self.packet_bank = {
            "document_type": "warrantroute_qwen3_generalist_evaluator_item_bank",
            "schema_version": "qwen3-generalist-evaluator-item-bank-v1",
            "study_id": self.study_id,
            "corpus_id": "dreaddit",
            "official_source_split": "test",
            "evaluation_role": "in_domain_audit",
            "privacy_clearance_status": "cleared_for_bound_model_and_rater_display",
            "items": self.items,
        }
        self.truth_map = {
            "document_type": "warrantroute_qwen3_generalist_truth_cluster_map",
            "schema_version": "qwen3-generalist-truth-cluster-map-v1",
            "study_id": self.study_id,
            "corpus_id": "dreaddit",
            "official_source_split": "test",
            "evaluation_role": "in_domain_audit",
            "cluster_unit": "post",
            "contains_source_text": False,
            "access": "coordinator_only_until_scoring_lock",
            "items": [self._truth_item(index, family) for index, family in enumerate(FAMILIES, 1)],
        }
        self.privacy_log = {
            "document_type": "warrantroute_privacy_review_log",
            "log_version": "warrantroute-privacy-review-log-v1",
            "record_status": "local_evidence_record",
            "contains_source_text": False,
            "minimum_distinct_reviewers_per_excerpt": 2,
            "records": [self._privacy_row(item) for item in self.items],
            "template_notice": "Ephemeral source-free software fixture.",
        }
        self.reviewer_registry = self._reviewer_registry()
        self.source_receipt = {
            "schema_version": "1.0",
            "corpus_id": "dreaddit",
            "version": "source-free-fixture-v1",
            "files": [
                {
                    "name": "dreaddit-test.csv",
                    "official_split": "test",
                    "sha256": "a" * 64,
                }
            ],
        }
        self.verification_bundle = self._verification_bundle()
        for truth, verification in zip(
            self.truth_map["items"], self.verification_bundle["items"], strict=True
        ):
            truth["verification_record_sha256"] = MODULE.sha256_bytes(
                MODULE.canonical_bytes(verification)
            )
        self.verification_seal = self._verification_seal()

        self.packet_path = self.storage_run / "evaluator_items.private.json"
        self.truth_path = self.storage_run / "truth_cluster_map.private.json"
        self.verification_bundle_path = self.storage_run / "verification_bundle.private.json"
        self.verification_seal_path = self.storage_run / "verification_seal.private.json"
        self.privacy_path = self.governance_local / "privacy_review_log.local.json"
        self.reviewer_registry_path = self.governance_local / "reviewer_registry.local.json"
        self.governance_path = self.governance_local / "project_governance.local.json"
        self.packet_manifest_path = self.governance_local / "packet_manifest.local.json"
        self.preaccess_path = self.governance_local / "preaccess_record.local.json"
        self.readiness_path = self.governance_local / "readiness_report.local.json"
        self.freeze_path = self.governance_local / "rq2_packet_study_freeze.local.json"
        self.source_receipt_path = self.dataset_manifests / "dreaddit_source_manifest.json"
        self.output_path = self.storage_run / "packet_bank_seal.json"
        self.rebuild_chain()

    def _copy_public_assets(self) -> None:
        paths = [
            (
                ROOT
                / "experiments"
                / "rq2_role_prompted_llm"
                / "schemas"
                / "qwen3_generalist_packet_study_freeze_v1.schema.json",
                self.root
                / "experiments"
                / "rq2_role_prompted_llm"
                / "schemas"
                / "qwen3_generalist_packet_study_freeze_v1.schema.json",
            ),
            (
                ROOT
                / "experiments"
                / "rq2_role_prompted_llm"
                / "schemas"
                / "qwen3_generalist_truth_cluster_map_v1.schema.json",
                self.root
                / "experiments"
                / "rq2_role_prompted_llm"
                / "schemas"
                / "qwen3_generalist_truth_cluster_map_v1.schema.json",
            ),
            *[
                (
                    ROOT
                    / "experiments"
                    / "rq2_role_prompted_llm"
                    / "schemas"
                    / name,
                    self.root
                    / "experiments"
                    / "rq2_role_prompted_llm"
                    / "schemas"
                    / name,
                )
                for name in (
                    "qwen3_generalist_packet_manifest_v1.schema.json",
                    "qwen3_generalist_preaccess_record_v1.schema.json",
                    "qwen3_generalist_verification_bundle_v1.schema.json",
                    "qwen3_generalist_verification_seal_v1.schema.json",
                )
            ],
            (
                ROOT
                / "experiments"
                / "direction_j_llm_as_rater"
                / "schemas"
                / "evaluator_item.schema.json",
                self.root
                / "experiments"
                / "direction_j_llm_as_rater"
                / "schemas"
                / "evaluator_item.schema.json",
            ),
            (
                ROOT
                / "experiments"
                / "rq2_role_prompted_llm"
                / "config"
                / "qwen3_generalist_reviewer_freeze.json",
                self.root
                / "experiments"
                / "rq2_role_prompted_llm"
                / "config"
                / "qwen3_generalist_reviewer_freeze.json",
            ),
        ]
        for source, target in paths:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def _truth_item(self, index: int, family: str) -> dict:
        member_hash = hashlib.sha256(f"source-free-member-{index}".encode()).hexdigest()
        item = self.items[index - 1]
        return {
            "item_id": item["item_id"],
            "packet_id": item["packet_id"],
            "output_id": item["output_id"],
            "base_packet_id": f"BASE_{index:08d}",
            "candidate_generator_actor_id": "independent_generator_fixture_v1",
            "evaluator_item_sha256": MODULE.sha256_bytes(MODULE.canonical_bytes(item)),
            "error_family": family,
            "required_flag": MODULE.EXPECTED_FAMILY_TO_FLAG[family],
            "verification_record_sha256": hashlib.sha256(
                f"verification-{index}".encode()
            ).hexdigest(),
            "controlled_variant_verified": True,
            "single_target_error_verified": True,
            "no_second_manipulation_verified": True,
            "post_clusters": [
                {
                    "cluster_id": f"PST_{index:08d}",
                    "sampling_frame_member_sha256s": [member_hash],
                    "packet_member_sha256s": [member_hash],
                    "complete": True,
                }
            ],
        }

    def _privacy_row(self, item: dict) -> dict:
        evidence = item["evidence"][0]
        return {
            "corpus_id": "dreaddit",
            "packet_id": item["packet_id"],
            "excerpt_id": evidence["excerpt_id"],
            "context_sha256": MODULE.privacy_context_sha256(item, evidence),
            "reviewer_ids": ["REV_FIXTURE01", "REV_FIXTURE02"],
            "reviewed_at_utc": "2026-08-28T03:05:00Z",
            "decision": "approved_restricted",
            "model_processing_cleared": True,
            "rater_display_cleared": True,
            "quotation_cleared": False,
        }

    def _reviewer_registry(self) -> dict:
        reviewers = []
        for reviewer_id in ("REV_FIXTURE01", "REV_FIXTURE02"):
            reviewers.append(
                {
                    "reviewer_id": reviewer_id,
                    "status": "active",
                    "roles": ["privacy_reviewer"],
                    "approved_corpora": ["dreaddit"],
                    "privacy_training_version": "fixture-v1",
                    "confidentiality_acknowledgment_version": "fixture-v1",
                    "approved_at_utc": "2026-08-27T00:00:00Z",
                    "expires_at_utc": "2027-08-28T00:00:00Z",
                    "last_verified_at_utc": "2026-08-28T03:00:00Z",
                }
            )
        return {
            "document_type": "warrantroute_reviewer_registry",
            "registry_version": "warrantroute-reviewer-registry-v1",
            "record_status": "local_evidence_record",
            "contains_direct_identifiers": False,
            "reviewer_id_format": "REV_[A-Z0-9]{8,32}",
            "identity_crosswalk_reference": "restricted-fixture-crosswalk",
            "reviewers": reviewers,
            "template_notice": "Ephemeral source-free software fixture.",
        }

    def _verification_bundle(self) -> dict:
        rows = []
        for item, truth in zip(self.items, self.truth_map["items"], strict=True):
            item_hash = MODULE.sha256_bytes(MODULE.canonical_bytes(item))
            verifications = []
            for suffix in ("a", "b"):
                verifications.append(
                    {
                        "verifier_actor_id": f"verifier_fixture_{suffix}",
                        "verifier_kind": "llm",
                        "reviewed_at_utc": "2026-08-28T03:30:00Z",
                        "decision": "verified_single_target_error_no_second_manipulation",
                        "evaluator_item_sha256": item_hash,
                        "error_family": truth["error_family"],
                        "required_flag": truth["required_flag"],
                        "independent_of_candidate_generator": True,
                        "independent_of_reviewer": True,
                        "verification_payload_sha256": hashlib.sha256(
                            f"payload-{item['item_id']}-{suffix}".encode()
                        ).hexdigest(),
                    }
                )
            rows.append(
                {
                    "item_id": item["item_id"],
                    "evaluator_item_sha256": item_hash,
                    "error_family": truth["error_family"],
                    "required_flag": truth["required_flag"],
                    "verifications": verifications,
                }
            )
        return {
            "document_type": "warrantroute_qwen3_generalist_verification_bundle",
            "bundle_version": "qwen3-generalist-verification-bundle-v1",
            "study_id": self.study_id,
            "contains_source_text": False,
            "corpus_id": "dreaddit",
            "official_source_split": "test",
            "candidate_generator_actor_id": "independent_generator_fixture_v1",
            "reviewer_actor_id": MODULE.EXPECTED_REVIEWER["actor_id"],
            "items": rows,
        }

    def _verification_seal(self) -> dict:
        item_ids = sorted(item["item_id"] for item in self.items)
        return {
            "document_type": "warrantroute_qwen3_generalist_verification_seal",
            "seal_version": "qwen3-generalist-verification-seal-v1",
            "seal_id": "VERIFY_FIXTURE_V1",
            "study_id": self.study_id,
            "status": "complete",
            "contains_source_text": False,
            "verification_bundle_sha256": MODULE.sha256_bytes(
                file_bytes(self.verification_bundle)
            ),
            "item_count": len(self.items),
            "item_id_set_sha256": MODULE.sha256_bytes(MODULE.canonical_bytes(item_ids)),
            "all_items_verified": True,
            "sealed_at_utc": "2026-08-28T03:40:00Z",
            "sealed_by_authority_id": "AUTH_FIXTURE01",
        }

    def _packet_manifest(self) -> dict:
        return {
            "document_type": "warrantroute_qwen3_generalist_packet_manifest",
            "manifest_version": "qwen3-generalist-packet-manifest-v1",
            "status": "approved_for_bound_reviewer_execution",
            "study_id": self.study_id,
            "contains_source_text": False,
            "corpus_id": "dreaddit",
            "official_source_split": "test",
            "evaluation_role": "in_domain_audit",
            "reviewer_actor_id": MODULE.EXPECTED_REVIEWER["actor_id"],
            "candidate_generator_actor_id": "independent_generator_fixture_v1",
            "source_receipt_sha256": sha256_path(self.source_receipt_path),
            "source_test_file_sha256": "a" * 64,
            "packet_bank_sha256": sha256_path(self.packet_path),
            "truth_cluster_map_sha256": sha256_path(self.truth_path),
            "privacy_review_log_sha256": sha256_path(self.privacy_path),
            "item_count": len(self.items),
            "item_id_set_sha256": MODULE.sha256_bytes(
                MODULE.canonical_bytes(sorted(item["item_id"] for item in self.items))
            ),
            "approved_at_utc": "2026-08-28T03:10:00Z",
            "approved_by_authority_id": "AUTH_FIXTURE01",
        }

    def _governance(self) -> dict:
        gates = []
        for gate_id in MODULE.EXPECTED_GATE_IDS:
            details = {}
            if gate_id == "exact_corpus_input_contract":
                details["source_receipt_sha256"] = sha256_path(self.source_receipt_path)
            if gate_id == "two_person_excerpt_privacy_review":
                details["packet_manifest_sha256"] = sha256_path(self.packet_manifest_path)
            gates.append(
                {
                    "id": gate_id,
                    "status": "approved",
                    "evidence_reference": f"restricted-fixture-{gate_id}",
                    "authority_id": "AUTH_FIXTURE01",
                    "approved_at_utc": "2026-08-28T03:10:00Z",
                    "expires_at_utc": "2027-08-28T00:00:00Z",
                    "last_verified_at_utc": "2026-08-28T03:15:00Z",
                    "details": details,
                }
            )
        return {
            "document_type": "warrantroute_project_governance_record",
            "governance_version": "warrantroute-project-governance-v1",
            "record_status": "local_evidence_record",
            "gate_mode": "real_text_candidate",
            "assessment_as_of_utc": "2026-08-28T03:15:00Z",
            "corpus_lanes": {
                "dreaddit": {
                    "corpus_id": "dreaddit",
                    "real_text_runnable": True,
                    "required_cluster_units": ["post"],
                    "gates": gates,
                }
            },
        }

    def _readiness(self) -> dict:
        gates = [
            {"id": gate_id, "complete": True, "blocking_reason_codes": []}
            for gate_id in MODULE.EXPECTED_GATE_IDS
        ]
        return {
            "document_type": "warrantroute_readiness_report",
            "report_version": "warrantroute-readiness-report-v1",
            "record_status": "local_evidence_record",
            "gate_mode": "real_text_candidate",
            "contains_real_source_text": False,
            "exact_required_gate_count": 10,
            "assessment_as_of_utc": "2026-08-28T03:20:00Z",
            "source_record_sha256": sha256_path(self.governance_path),
            "corpora": {
                "dreaddit": {
                    "external_gates_applicable": True,
                    "required_gate_count": 10,
                    "completed_gate_count": 10,
                    "real_text_ready": True,
                    "live_input_integrity_checked": True,
                    "gates": gates,
                }
            },
            "privacy_review_log": {"record_count": 5, "source_text_in_report": False},
            "reviewer_registry": {
                "record_count": 2,
                "direct_identifiers_in_report": False,
            },
            "warning_codes": [],
        }

    def _preaccess(self) -> dict:
        return {
            "document_type": "warrantroute_qwen3_generalist_preaccess_record",
            "record_version": "qwen3-generalist-preaccess-record-v1",
            "status": "sealed_clean_before_reviewer_execution",
            "study_id": self.study_id,
            "contains_source_text": False,
            "corpus_id": "dreaddit",
            "official_source_split": "test",
            "study_design_freeze_sha256": self.study_design_freeze_sha256,
            "source_receipt_sha256": sha256_path(self.source_receipt_path),
            "packet_manifest_sha256": sha256_path(self.packet_manifest_path),
            "design_frozen_at_utc": "2026-08-28T01:00:00Z",
            "first_heldout_access_at_utc": "2026-08-28T02:00:00Z",
            "packet_construction_completed_at_utc": "2026-08-28T03:00:00Z",
            "recorded_at_utc": "2026-08-28T03:25:00Z",
            "reviewer_execution_started_at_utc": None,
            "reviewer_outputs_observed": False,
            "test_outcomes_observed": False,
            "recorded_by_authority_id": "AUTH_FIXTURE01",
        }

    def _freeze(self) -> dict:
        evaluator_schema = (
            self.root
            / "experiments"
            / "direction_j_llm_as_rater"
            / "schemas"
            / "evaluator_item.schema.json"
        )
        component = (
            self.root
            / "experiments"
            / "rq2_role_prompted_llm"
            / "config"
            / "qwen3_generalist_reviewer_freeze.json"
        )
        return {
            "document_type": "warrantroute_qwen3_generalist_packet_study_freeze",
            "freeze_version": "qwen3-generalist-packet-study-freeze-v1",
            "record_status": "formal_packet_execution_metadata_frozen",
            "study_id": self.study_id,
            "frozen_at_utc": "2026-08-28T04:00:00Z",
            "frozen_by_authority_id": "AUTH_FIXTURE01",
            "corpus": {
                "corpus_id": "dreaddit",
                "official_source_split": "test",
                "evaluation_role": "in_domain_audit",
                "cluster_unit": "post",
            },
            "design": {
                "fixed_n": 5,
                "one_version_per_base_packet": True,
                "complete_post_clusters_required": True,
                "post_clusters_disjoint_across_items": True,
                "privacy_log_full_coverage_required": True,
                "minimum_distinct_verifiers_per_item": 2,
                "family_balance": {
                    "frozen": True,
                    "expected_counts": {family: 1 for family in FAMILIES},
                },
            },
            "actors": {
                "candidate_generator": {
                    "actor_id": "independent_generator_fixture_v1",
                    "task_role": "candidate_generator",
                    "model_id": "independent-source-free-fixture",
                    "snapshot_sha256": "2" * 64,
                    "prompt_sha256": "3" * 64,
                },
                "reviewer": {
                    **MODULE.EXPECTED_REVIEWER,
                    "model_snapshot_sha256": json.loads(component.read_text())[
                        "reviewer_actor"
                    ]["local_manifest_file_sha256"],
                    "component_freeze_sha256": sha256_path(component),
                },
            },
            "bindings": {
                "readiness_report_sha256": sha256_path(self.readiness_path),
                "governance_source_record_sha256": sha256_path(self.governance_path),
                "governance_record_sha256": sha256_path(self.governance_path),
                "reviewer_registry_sha256": sha256_path(self.reviewer_registry_path),
                "privacy_review_log_sha256": sha256_path(self.privacy_path),
                "packet_manifest_sha256": sha256_path(self.packet_manifest_path),
                "source_receipt_sha256": sha256_path(self.source_receipt_path),
                "verification_bundle_sha256": sha256_path(self.verification_bundle_path),
                "verification_seal_sha256": sha256_path(self.verification_seal_path),
                "study_design_freeze_sha256": self.study_design_freeze_sha256,
                "packet_bank_sha256": sha256_path(self.packet_path),
                "truth_cluster_map_sha256": sha256_path(self.truth_path),
                "evaluator_item_schema_sha256": sha256_path(evaluator_schema),
                "scoring_contract_sha256": "4" * 64,
                "analysis_code_sha256": "5" * 64,
                "heldout_preaccess_record_sha256": sha256_path(self.preaccess_path),
            },
            "warning": (
                "This frozen metadata record and any packet-bank seal validate bindings only. "
                "They do not independently grant data access, model processing, publication, "
                "or release authorization."
            ),
        }

    def rewrite_freeze(self) -> None:
        write_private_json(self.freeze_path, self.freeze)

    def rebuild_chain(self) -> None:
        write_private_json(self.packet_path, self.packet_bank)
        write_private_json(self.truth_path, self.truth_map)
        write_private_json(self.privacy_path, self.privacy_log)
        write_private_json(self.reviewer_registry_path, self.reviewer_registry)
        self.source_receipt_path.write_bytes(file_bytes(self.source_receipt))
        write_private_json(self.verification_bundle_path, self.verification_bundle)
        self.verification_seal["verification_bundle_sha256"] = sha256_path(
            self.verification_bundle_path
        )
        write_private_json(self.verification_seal_path, self.verification_seal)
        self.packet_manifest = self._packet_manifest()
        write_private_json(self.packet_manifest_path, self.packet_manifest)
        self.governance = self._governance()
        write_private_json(self.governance_path, self.governance)
        self.readiness = self._readiness()
        write_private_json(self.readiness_path, self.readiness)
        self.preaccess = self._preaccess()
        write_private_json(self.preaccess_path, self.preaccess)
        self.freeze = self._freeze()
        write_private_json(self.freeze_path, self.freeze)

    def relink_verification(self) -> None:
        for truth, verification in zip(
            self.truth_map["items"], self.verification_bundle["items"], strict=True
        ):
            truth["verification_record_sha256"] = MODULE.sha256_bytes(
                MODULE.canonical_bytes(verification)
            )
        self.rebuild_chain()

    def seal(self) -> dict:
        return MODULE.seal_packet_bank(
            study_freeze_path=self.freeze_path,
            readiness_report_path=self.readiness_path,
            governance_record_path=self.governance_path,
            reviewer_registry_path=self.reviewer_registry_path,
            privacy_log_path=self.privacy_path,
            packet_manifest_path=self.packet_manifest_path,
            source_receipt_path=self.source_receipt_path,
            preaccess_record_path=self.preaccess_path,
            verification_bundle_path=self.verification_bundle_path,
            verification_seal_path=self.verification_seal_path,
            packet_bank_path=self.packet_path,
            truth_map_path=self.truth_path,
            output_path=self.output_path,
            workspace=self.root,
        )


class Qwen3PacketBankSealerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = PacketSealFixture(Path(self.temp.name).resolve())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_source_free_dry_run_opens_no_packet_or_truth_file(self) -> None:
        self.fixture.packet_path.unlink()
        self.fixture.truth_path.unlink()
        result = MODULE.source_free_dry_run(workspace=self.fixture.root)
        self.assertEqual(result["status"], "passed_source_free_dry_run")
        self.assertFalse(result["packet_bank_accessed"])
        self.assertFalse(result["truth_map_accessed"])
        self.assertFalse(result["model_service_contacted"])
        self.assertFalse(result["seal_written"])
        self.assertFalse(result["authorization_claimed_by_this_check"])

    def test_valid_bundle_writes_only_text_free_non_authorizing_seal(self) -> None:
        result = self.fixture.seal()
        self.assertEqual(result["status"], "sealed")
        self.assertFalse(result["contains_source_text"])
        self.assertFalse(result["authorization_claimed_by_this_seal"])
        self.assertFalse(result["manuscript_result"])
        seal_text = self.fixture.output_path.read_text()
        seal = json.loads(seal_text)
        self.assertEqual(seal["formal_dreaddit_gates_verified"], "10/10")
        self.assertEqual(seal["fixed_n"], 5)
        self.assertEqual(seal["item_count"], 5)
        packet_hash = sha256_path(self.fixture.packet_path)
        expected_item_set_hash = MODULE.sha256_bytes(
            MODULE.canonical_bytes(sorted(item["item_id"] for item in self.fixture.items))
        )
        self.assertEqual(seal["seal_id"], f"QGPB_{packet_hash[:16].upper()}")
        self.assertEqual(seal["item_id_set_sha256"], expected_item_set_hash)
        self.assertTrue(seal["packet_bank_complete"])
        self.assertTrue(seal["privacy_cleared"])
        self.assertEqual(set(seal["family_counts"]), set(FAMILIES))
        self.assertEqual(
            seal["bindings"]["packet_study_freeze_sha256"],
            sha256_path(self.fixture.freeze_path),
        )
        self.assertEqual(
            seal["bindings"]["packet_manifest_sha256"],
            sha256_path(self.fixture.packet_manifest_path),
        )
        self.assertEqual(
            seal["bindings"]["source_receipt_sha256"],
            sha256_path(self.fixture.source_receipt_path),
        )
        self.assertEqual(
            seal["candidate_generator_snapshot_sha256"],
            self.fixture.freeze["actors"]["candidate_generator"]["snapshot_sha256"],
        )
        self.assertEqual(
            seal["candidate_generator_prompt_sha256"],
            self.fixture.freeze["actors"]["candidate_generator"]["prompt_sha256"],
        )
        self.assertNotIn("Inert interface-fixture evidence.", seal_text)
        self.assertNotIn("proposed_interpretation", seal_text)
        self.assertEqual(self.fixture.output_path.stat().st_mode & 0o777, 0o600)

    def test_formal_readiness_blocks_before_packet_path_is_touched(self) -> None:
        self.fixture.readiness["gate_mode"] = "personal_local_only"
        self.fixture.readiness["personal_local_only"] = {"active": True}
        write_private_json(self.fixture.readiness_path, self.fixture.readiness)
        self.fixture.packet_path.unlink()
        self.fixture.truth_path.unlink()
        with self.assertRaisesRegex(MODULE.PacketSealError, "formal_gate_mode_invalid"):
            self.fixture.seal()

    def test_nine_of_ten_gates_is_rejected(self) -> None:
        dreaddit = self.fixture.readiness["corpora"]["dreaddit"]
        dreaddit["completed_gate_count"] = 9
        dreaddit["gates"][-1]["complete"] = False
        dreaddit["gates"][-1]["blocking_reason_codes"] = ["status_pending"]
        write_private_json(self.fixture.readiness_path, self.fixture.readiness)
        self.fixture.freeze["bindings"]["readiness_report_sha256"] = sha256_path(
            self.fixture.readiness_path
        )
        self.fixture.rewrite_freeze()
        with self.assertRaisesRegex(MODULE.PacketSealError, "dreaddit_completed_gate_count_invalid"):
            self.fixture.seal()

    def test_candidate_generator_must_be_distinct_from_qwen_reviewer(self) -> None:
        self.fixture.freeze["actors"]["candidate_generator"]["actor_id"] = (
            "qwen3_8b_generalist_reviewer_v1"
        )
        self.fixture.rewrite_freeze()
        with self.assertRaisesRegex(MODULE.PacketSealError, "candidate_generator_is_reviewer"):
            self.fixture.seal()

    def test_candidate_generator_model_must_differ_from_reviewer(self) -> None:
        self.fixture.freeze["actors"]["candidate_generator"]["model_id"] = "qwen3:8b"
        self.fixture.rewrite_freeze()
        with self.assertRaisesRegex(
            MODULE.PacketSealError, "candidate_generator_model_is_reviewer_model"
        ):
            self.fixture.seal()

    def test_candidate_generator_snapshot_must_differ_from_reviewer(self) -> None:
        self.fixture.freeze["actors"]["candidate_generator"]["snapshot_sha256"] = (
            self.fixture.freeze["actors"]["reviewer"]["model_snapshot_sha256"]
        )
        self.fixture.rewrite_freeze()
        with self.assertRaisesRegex(
            MODULE.PacketSealError, "candidate_generator_snapshot_is_reviewer_snapshot"
        ):
            self.fixture.seal()

    def test_exact_governance_record_is_bound_before_packet_access(self) -> None:
        self.fixture.governance["assessment_as_of_utc"] = "2026-08-28T03:16:00Z"
        write_private_json(self.fixture.governance_path, self.fixture.governance)
        self.fixture.packet_path.unlink()
        self.fixture.truth_path.unlink()
        with self.assertRaisesRegex(MODULE.PacketSealError, "governance_record_hash_mismatch"):
            self.fixture.seal()

    def test_privacy_reviewer_requires_registered_scope(self) -> None:
        self.fixture.reviewer_registry["reviewers"][0]["roles"] = ["study_rater"]
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "privacy_reviewer_role_missing"):
            self.fixture.seal()

    def test_source_receipt_is_bound_before_packet_access(self) -> None:
        self.fixture.source_receipt["version"] = "changed-after-freeze"
        self.fixture.source_receipt_path.write_bytes(file_bytes(self.fixture.source_receipt))
        self.fixture.packet_path.unlink()
        self.fixture.truth_path.unlink()
        with self.assertRaisesRegex(MODULE.PacketSealError, "source_receipt_hash_mismatch"):
            self.fixture.seal()

    def test_preaccess_timeline_is_fail_closed(self) -> None:
        self.fixture.preaccess["first_heldout_access_at_utc"] = "2026-08-28T00:30:00Z"
        write_private_json(self.fixture.preaccess_path, self.fixture.preaccess)
        self.fixture.freeze["bindings"]["heldout_preaccess_record_sha256"] = sha256_path(
            self.fixture.preaccess_path
        )
        self.fixture.rewrite_freeze()
        with self.assertRaisesRegex(MODULE.PacketSealError, "preaccess_timeline_invalid"):
            self.fixture.seal()

    def test_independent_verifier_cannot_be_candidate_generator(self) -> None:
        self.fixture.verification_bundle["items"][0]["verifications"][0][
            "verifier_actor_id"
        ] = "independent_generator_fixture_v1"
        self.fixture.relink_verification()
        with self.assertRaisesRegex(MODULE.PacketSealError, "candidate_generator_used_as_verifier"):
            self.fixture.seal()

    def test_verification_bundle_is_bound_to_exact_evaluator_item(self) -> None:
        self.fixture.verification_bundle["items"][0]["evaluator_item_sha256"] = "8" * 64
        self.fixture.relink_verification()
        with self.assertRaisesRegex(MODULE.PacketSealError, "verification_item_hash_mismatch"):
            self.fixture.seal()

    def test_item_truth_bijection_is_exact(self) -> None:
        self.fixture.truth_map["items"][0]["item_id"] = "DJI_ffffffffffffffff"
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "item_truth_bijection_mismatch"):
            self.fixture.seal()

    def test_only_one_version_per_base_packet_is_allowed(self) -> None:
        self.fixture.truth_map["items"][1]["base_packet_id"] = self.fixture.truth_map["items"][0][
            "base_packet_id"
        ]
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "multiple_versions_for_base_packet"):
            self.fixture.seal()

    def test_complete_post_membership_must_match(self) -> None:
        self.fixture.truth_map["items"][0]["post_clusters"][0]["packet_member_sha256s"] = [
            "9" * 64
        ]
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "incomplete_post_cluster"):
            self.fixture.seal()

    def test_post_members_cannot_reappear_under_renamed_cluster(self) -> None:
        first = self.fixture.truth_map["items"][0]["post_clusters"][0]
        second = self.fixture.truth_map["items"][1]["post_clusters"][0]
        second["sampling_frame_member_sha256s"] = list(
            first["sampling_frame_member_sha256s"]
        )
        second["packet_member_sha256s"] = list(first["packet_member_sha256s"])
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(
            MODULE.PacketSealError, "post_member_reused_under_renamed_cluster"
        ):
            self.fixture.seal()

    def test_privacy_log_must_cover_exact_displayed_context(self) -> None:
        self.fixture.privacy_log["records"][0]["context_sha256"] = "8" * 64
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "privacy_context_hash_mismatch"):
            self.fixture.seal()

    def test_packet_hash_drift_is_rejected(self) -> None:
        self.fixture.packet_bank["items"][0]["context_note"] = "Changed after the freeze."
        write_private_json(self.fixture.packet_path, self.fixture.packet_bank)
        with self.assertRaisesRegex(MODULE.PacketSealError, "packet_bank_hash_mismatch"):
            self.fixture.seal()

    def test_fixed_five_family_counts_are_enforced(self) -> None:
        row = self.fixture.truth_map["items"][0]
        row["error_family"] = "source_concentration"
        row["required_flag"] = "hidden_source_concentration"
        self.fixture.rebuild_chain()
        with self.assertRaisesRegex(MODULE.PacketSealError, "five_family_coverage_missing"):
            self.fixture.seal()


if __name__ == "__main__":
    unittest.main()
