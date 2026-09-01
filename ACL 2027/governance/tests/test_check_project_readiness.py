from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


GOVERNANCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = GOVERNANCE_ROOT / "scripts" / "check_project_readiness.py"
TEMPLATE_PATH = GOVERNANCE_ROOT / "templates" / "project_governance.template.json"
REVIEWER_TEMPLATE_PATH = GOVERNANCE_ROOT / "templates" / "reviewer_registry.template.json"
PRIVACY_TEMPLATE_PATH = GOVERNANCE_ROOT / "templates" / "privacy_review_log.template.json"
REPORT_PATH = GOVERNANCE_ROOT / "reports" / "synthetic_only_readiness.json"

SPEC = importlib.util.spec_from_file_location("check_project_readiness", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_baseline_report() -> dict:
    record = load(TEMPLATE_PATH)
    readiness.validate_record_shape(record)
    reviewers = readiness.validate_reviewer_registry(
        load(REVIEWER_TEMPLATE_PATH), template_ok=True
    )
    privacy_records = readiness.validate_privacy_log(
        load(PRIVACY_TEMPLATE_PATH), template_ok=True
    )
    return readiness.build_report(
        record,
        readiness.sha256_path(TEMPLATE_PATH),
        readiness.parse_utc("2026-08-25T00:00:00Z", "test as-of"),
        reviewers,
        privacy_records,
    )


class ReadinessCheckerTests(unittest.TestCase):
    def test_tracked_baseline_is_exactly_four_blocked_real_lanes(self) -> None:
        report = build_baseline_report()
        self.assertEqual(tuple(report["corpora"]), readiness.CORPORA)
        self.assertTrue(report["synthetic_lane_runnable"])
        self.assertFalse(report["contains_real_source_text"])
        self.assertFalse(report["all_real_corpora_ready"])
        self.assertEqual(report["exact_required_gate_count"], 10)
        self.assertEqual(tuple(report["required_gate_ids"]), readiness.GATE_IDS)
        for corpus in report["corpora"].values():
            self.assertEqual(corpus["required_gate_count"], 10)
            self.assertEqual(corpus["completed_gate_count"], 0)
            self.assertFalse(corpus["real_text_ready"])
            self.assertTrue(
                all(gate["blocking_reason_codes"] == ["status_pending"] for gate in corpus["gates"])
            )

    def test_kodis_split_unit_is_the_participant_connected_component(self) -> None:
        record = load(TEMPLATE_PATH)
        lane = record["corpus_lanes"]["kodis"]
        expected = ["dialogue_participant_connected_component"]
        self.assertEqual(lane["required_cluster_units"], expected)
        sampling_gate = next(
            gate for gate in lane["gates"] if gate["id"] == "cluster_aware_sampling"
        )
        self.assertEqual(sampling_gate["details"]["cluster_units"], expected)

    def test_missing_gate_is_rejected(self) -> None:
        record = load(TEMPLATE_PATH)
        record["corpus_lanes"]["candor"]["gates"].pop()
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_record_shape(record)

    def test_report_labels_cannot_be_replaced_with_free_text(self) -> None:
        record = load(TEMPLATE_PATH)
        record["corpus_lanes"]["candor"]["planned_roles"] = ["uncontrolled free text"]
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_record_shape(record)

    def test_local_initialization_can_remain_synthetic_only(self) -> None:
        record = load(TEMPLATE_PATH)
        record["record_status"] = "local_evidence_record"
        record["record_id"] = "LOCAL_INITIALIZATION_PENDING"
        record["gate_mode"] = "synthetic_only"
        readiness.validate_record_shape(record)
        report = readiness.build_report(
            record,
            "b" * 64,
            readiness.parse_utc("2026-08-25T00:00:00Z", "test as-of"),
            {},
            [],
        )
        self.assertFalse(report["all_real_corpora_ready"])
        self.assertTrue(report["synthetic_lane_runnable"])
        self.assertTrue(
            all(corpus["completed_gate_count"] == 0 for corpus in report["corpora"].values())
        )

    def personal_local_record(self) -> dict:
        record = load(TEMPLATE_PATH)
        record["record_status"] = "local_evidence_record"
        record["record_id"] = "LOCAL_PERSONAL_ONLY_20260826"
        record["gate_mode"] = "personal_local_only"
        return record

    def test_personal_local_only_is_local_record_only(self) -> None:
        record = load(TEMPLATE_PATH)
        record["gate_mode"] = "personal_local_only"
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_record_shape(record)

    def test_personal_local_only_has_no_external_gates_or_external_readiness(self) -> None:
        record = self.personal_local_record()
        readiness.validate_record_shape(record)
        report = readiness.build_report(
            record,
            "c" * 64,
            readiness.parse_utc("2026-08-26T00:00:00Z", "test as-of"),
            {},
            [],
        )
        self.assertEqual(report["exact_required_gate_count"], 0)
        self.assertEqual(report["required_gate_ids"], [])
        self.assertFalse(report["all_real_corpora_ready"])
        personal = report["personal_local_only"]
        self.assertTrue(personal["scope_assessment_only"])
        self.assertFalse(personal["live_input_integrity_checked"])
        self.assertTrue(personal["execution_requires_exact_policy_validation"])
        self.assertTrue(personal["all_allowed_corpora_scope_eligible"])
        self.assertTrue(report["corpora"]["dreaddit"]["personal_local_scope_eligible"])
        self.assertTrue(
            report["corpora"]["agyw_focus_groups"]["personal_local_scope_eligible"]
        )
        self.assertFalse(report["corpora"]["kodis"]["personal_local_scope_eligible"])
        self.assertFalse(report["corpora"]["candor"]["personal_local_scope_eligible"])
        self.assertFalse(report["corpora"]["dreaddit"]["live_input_integrity_checked"])
        for corpus in report["corpora"].values():
            self.assertFalse(corpus["external_gates_applicable"])
            self.assertEqual(corpus["required_gate_count"], 0)
            self.assertEqual(corpus["gates"], [])
            self.assertFalse(corpus["real_text_ready"])

    def test_personal_local_only_capabilities_fail_closed(self) -> None:
        report = readiness.build_report(
            self.personal_local_record(),
            "d" * 64,
            readiness.parse_utc("2026-08-26T00:00:00Z", "test as-of"),
            {},
            [],
        )
        capabilities = report["personal_local_only"]["capabilities"]
        self.assertTrue(capabilities["local_single_user_processing_allowed"])
        self.assertTrue(capabilities["local_loopback_model_processing_allowed"])
        self.assertFalse(capabilities["external_or_cloud_processing_allowed"])
        self.assertFalse(capabilities["human_rater_or_reviewer_access_allowed"])
        self.assertFalse(capabilities["publication_or_submission_allowed"])
        self.assertFalse(capabilities["redistribution_or_release_allowed"])

    def test_personal_local_only_rejects_model_endpoint_profiles(self) -> None:
        record = self.personal_local_record()
        record["model_endpoint_profiles"] = [
            {
                "profile_id": "MEP_ABCDEFGH",
                "provider": "provider-reference",
            }
        ]
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_record_shape(record)

    def test_expired_gate_cannot_complete(self) -> None:
        gate = copy.deepcopy(load(TEMPLATE_PATH)["corpus_lanes"]["candor"]["gates"][0])
        gate.update(
            {
                "status": "approved",
                "evidence_reference": "RESTRICTED:EVIDENCE-1",
                "authority_id": "AUTHORITY-1",
                "evidence_version": "v1",
                "approved_at_utc": "2026-01-01T00:00:00Z",
                "expires_at_utc": "2026-08-25T00:00:00Z",
                "last_verified_at_utc": "2026-08-24T00:00:00Z",
            }
        )
        blockers = readiness.common_gate_blockers(
            gate, readiness.parse_utc("2026-08-25T00:00:00Z", "test as-of")
        )
        self.assertIn("approval_expired", blockers)

    def test_model_profile_rejects_training_and_expiry(self) -> None:
        profile = {
            "profile_id": "MEP_ABCDEFGH",
            "provider": "provider-reference",
            "account_or_tenant_reference": "tenant-reference",
            "product_or_endpoint": "endpoint-reference",
            "endpoint_region": "region-reference",
            "model_id": "model-reference",
            "model_snapshot": "snapshot-reference",
            "api_version": "api-v1",
            "provider_terms_version": "terms-v1",
            "privacy_terms_version": "privacy-v1",
            "approved_corpora": ["candor"],
            "approved_data_classification": "restricted-text",
            "training_use": "enabled",
            "retention_mode": "fixed",
            "retention_days": 0,
            "deletion_behavior": "contract-reference",
            "human_access_or_abuse_monitoring": "contract-reference",
            "subprocessors_reference": "contract-reference",
            "processing_region": "region-reference",
            "approved_at_utc": "2026-01-01T00:00:00Z",
            "expires_at_utc": "2026-08-24T00:00:00Z",
            "last_verified_at_utc": "2026-08-20T00:00:00Z",
        }
        blockers = readiness.endpoint_profile_blockers(
            profile, "candor", readiness.parse_utc("2026-08-25T00:00:00Z", "test as-of")
        )
        self.assertIn("provider_training_not_disabled", blockers)
        self.assertIn("endpoint_approval_expired", blockers)

    def test_reviewer_expiry_is_checked(self) -> None:
        reviewer = {
            "reviewer_id": "REV_ABCDEFGH",
            "status": "active",
            "roles": ["privacy_reviewer"],
            "approved_corpora": ["candor"],
            "privacy_training_version": "training-v1",
            "confidentiality_acknowledgment_version": "confidentiality-v1",
            "approved_at_utc": "2026-01-01T00:00:00Z",
            "expires_at_utc": "2026-08-24T00:00:00Z",
            "last_verified_at_utc": "2026-08-20T00:00:00Z",
        }
        blockers = readiness.reviewer_blockers(
            reviewer,
            "candor",
            readiness.parse_utc("2026-08-25T00:00:00Z", "test as-of"),
            {"privacy_reviewer"},
        )
        self.assertIn("reviewer_approval_expired", blockers)

    def test_privacy_log_rejects_duplicate_reviewers_and_raw_ids(self) -> None:
        base = load(PRIVACY_TEMPLATE_PATH)
        base["records"] = [
            {
                "corpus_id": "candor",
                "packet_id": "PKT_ABCDEFGH",
                "excerpt_id": "EXC_ABCDEFGH",
                "context_sha256": "a" * 64,
                "reviewer_ids": ["REV_ABCDEFGH", "REV_ABCDEFGH"],
                "reviewed_at_utc": "2026-08-24T00:00:00Z",
                "decision": "approved_restricted",
                "model_processing_cleared": True,
                "rater_display_cleared": True,
                "quotation_cleared": False,
            }
        ]
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_privacy_log(base, template_ok=True)

        base["records"][0]["reviewer_ids"] = ["REV_ABCDEFGH", "REV_IJKLMNOP"]
        base["records"][0]["packet_id"] = "raw-conversation-123"
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_privacy_log(base, template_ok=True)

    def test_local_evidence_requires_private_regular_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=readiness.LOCAL_ROOT) as directory:
            root = Path(directory)
            private_file = root / "evidence.json"
            private_file.write_text("{}\n", encoding="utf-8")
            os.chmod(private_file, 0o600)
            readiness.require_private_local_file(private_file, "test evidence")

            os.chmod(private_file, 0o640)
            with self.assertRaises(readiness.ReadinessError):
                readiness.require_private_local_file(private_file, "test evidence")

            os.chmod(private_file, 0o600)
            symlink = root / "evidence-link.json"
            symlink.symlink_to(private_file)
            with self.assertRaises(readiness.ReadinessError):
                readiness.require_private_local_file(symlink, "test evidence")

    def test_tracked_report_is_canonical_and_current(self) -> None:
        expected = readiness.canonical_bytes(build_baseline_report())
        self.assertEqual(REPORT_PATH.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
