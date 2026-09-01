#!/usr/bin/env python3
"""Regression tests for fail-closed Dreaddit/AGYW review preparation."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


DATASET_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = DATASET_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

import prepare_dreaddit_agyw_review as review  # noqa: E402
import validate_dreaddit_agyw_review as validator  # noqa: E402


DUMMY_SHA = "a" * 64


def dreaddit_record(
    record_id: str,
    source_id: str,
    text: str,
    *,
    split: str = "development_train",
    eligible: bool = True,
) -> dict:
    return {
        "record_id": record_id,
        "corpus": "dreaddit",
        "split": split,
        "source_id": source_id,
        "speaker_id": None,
        "text": text,
        "context": {"preceding_record_ids": [], "moderator_question": None},
        "quality": {
            "eligible_for_packet_sampling": eligible,
            "ineligible_reasons": [] if eligible else ["fixture_ineligible"],
            "privacy_masks_applied": [],
            "manual_excerpt_review_required": True,
        },
    }


def agyw_record(
    record_id: str,
    source_id: str,
    speaker_suffix: str | None,
    text: str,
    *,
    preceding: list[str] | None = None,
    moderator: str | None = None,
    eligible: bool = True,
) -> dict:
    return {
        "record_id": record_id,
        "corpus": "agyw_focus_groups",
        "split": "heldout_cross_domain_evaluation",
        "source_id": source_id,
        "speaker_id": f"{source_id}_{speaker_suffix}" if speaker_suffix is not None else None,
        "text": text,
        "context": {
            "preceding_record_ids": preceding or [],
            "moderator_question": moderator,
        },
        "quality": {
            "eligible_for_packet_sampling": eligible and speaker_suffix is not None,
            "ineligible_reasons": [] if eligible and speaker_suffix is not None else ["fixture_context"],
            "privacy_masks_applied": [],
            "manual_excerpt_review_required": True,
        },
    }


def approved_review(reviewer_id: str, *, quotation: bool = False) -> dict:
    return {
        "reviewer_id": reviewer_id,
        "reviewed_at_utc": "2026-08-25T20:00:00Z",
        "decision": "approved_restricted",
        "direct_identifiers_resolved": True,
        "contextual_risk_resolved": True,
        "model_processing_cleared": True,
        "rater_display_cleared": True,
        "quotation_cleared": quotation,
        "notes_reference": "review_note_a1b2c3d4e5f6a7b8",
    }


class DreadditAgywReviewTests(unittest.TestCase):
    def build_dreaddit_candidate(self, records: list[dict], clusters: int = 1) -> dict:
        return review.build_candidate_manifest(
            records,
            corpus="dreaddit",
            split="development_train",
            requested_clusters=clusters,
            sampling_seed="fixture-seed",
            records_sha256=DUMMY_SHA,
            source_manifest_sha256="b" * 64,
            selection_control_file="fixture.local.json",
            selection_control_sha256="c" * 64,
        )

    def build_agyw_candidate(self, records: list[dict], clusters: int) -> dict:
        return review.build_candidate_manifest(
            records,
            corpus="agyw_focus_groups",
            split="heldout_cross_domain_evaluation",
            requested_clusters=clusters,
            sampling_seed="fixture-heldout-seed",
            records_sha256=DUMMY_SHA,
            source_manifest_sha256="b" * 64,
            selection_control_file="fixture.local.json",
            selection_control_sha256="c" * 64,
        )

    def test_exact_date_quarantines_entire_dreaddit_post_cluster(self) -> None:
        records = [
            dreaddit_record("dreaddit_train_00001", "dreaddit_train_post_00001", "ordinary first segment"),
            dreaddit_record("dreaddit_train_00002", "dreaddit_train_post_00001", "event on 2025-04-03"),
            dreaddit_record("dreaddit_train_00003", "dreaddit_train_post_00002", "ordinary second post"),
        ]
        manifest = self.build_dreaddit_candidate(records)
        quarantine = manifest["exact_date_quarantine"]
        self.assertEqual(quarantine["clusters"], 1)
        self.assertEqual(quarantine["records"], 2)
        self.assertEqual(
            quarantine["quarantined_clusters"][0]["record_ids"],
            ["dreaddit_train_00001", "dreaddit_train_00002"],
        )
        self.assertEqual(manifest["clusters"][0]["record_ids"], ["dreaddit_train_00003"])
        self.assertFalse(manifest["experiment_use_ready"])

    def test_month_name_exact_date_is_quarantined(self) -> None:
        records = [
            dreaddit_record(
                "dreaddit_train_00001",
                "dreaddit_train_post_00001",
                "fictional event on Sept. 18, 2011",
            ),
            dreaddit_record(
                "dreaddit_train_00002",
                "dreaddit_train_post_00002",
                "ordinary second post",
            ),
        ]
        manifest = self.build_dreaddit_candidate(records)
        self.assertEqual(manifest["exact_date_quarantine"]["clusters"], 1)
        self.assertEqual(
            manifest["exact_date_quarantine"]["pattern_version"],
            "numeric-and-month-name-exact-date-v2",
        )

    def test_exact_date_in_displayed_context_quarantines_agyw_speaker_cluster(self) -> None:
        records = [
            agyw_record(
                "agyw_fgd_01_turn_0001",
                "agyw_fgd_01",
                None,
                "context dated 2025-04-03",
                eligible=False,
            ),
            agyw_record(
                "agyw_fgd_01_turn_0002",
                "agyw_fgd_01",
                "r1",
                "eligible answer",
                preceding=["agyw_fgd_01_turn_0001"],
            ),
            agyw_record(
                "agyw_fgd_01_turn_0003",
                "agyw_fgd_01",
                "r2",
                "clean speaker answer",
            ),
        ]
        manifest = self.build_agyw_candidate(records, clusters=1)
        self.assertEqual(manifest["exact_date_quarantine"]["clusters"], 1)
        self.assertEqual(
            manifest["clusters"][0]["record_ids"], ["agyw_fgd_01_turn_0003"]
        )

    def test_date_audit_subtracts_entire_post_cluster(self) -> None:
        records = [
            dreaddit_record(
                "dreaddit_train_00001",
                "dreaddit_train_post_00001",
                "fictional event on April 3rd, 2018",
            ),
            dreaddit_record(
                "dreaddit_train_00002",
                "dreaddit_train_post_00001",
                "ordinary second segment from the same post",
            ),
        ]
        audit = review.build_dreaddit_exact_date_audit(records, DUMMY_SHA)
        self.assertEqual(audit["matched_records"], 1)
        self.assertEqual(
            audit["content_rule_eligible_quarantined_by_cluster"],
            {"development_train": 2},
        )
        self.assertEqual(
            audit["content_rule_eligible_after_cluster_quarantine"],
            {"development_train": 0},
        )

    def test_ineligible_dated_segment_quarantines_eligible_post_segment(self) -> None:
        records = [
            dreaddit_record(
                "dreaddit_train_00001",
                "dreaddit_train_post_00001",
                "ineligible segment dated 2025-04-03",
                eligible=False,
            ),
            dreaddit_record(
                "dreaddit_train_00002",
                "dreaddit_train_post_00001",
                "eligible clean segment from the same post",
            ),
            dreaddit_record(
                "dreaddit_train_00003",
                "dreaddit_train_post_00002",
                "eligible clean second post",
            ),
        ]
        manifest = self.build_dreaddit_candidate(records)
        self.assertEqual(manifest["exact_date_quarantine"]["clusters"], 1)
        self.assertEqual(
            manifest["exact_date_quarantine"]["quarantined_clusters"][0]["record_ids"],
            ["dreaddit_train_00002"],
        )
        self.assertEqual(
            manifest["clusters"][0]["record_ids"], ["dreaddit_train_00003"]
        )

    def test_agyw_sampling_keeps_focus_group_speaker_clusters_intact(self) -> None:
        records = [
            agyw_record("agyw_fgd_01_turn_0001", "agyw_fgd_01", "r1", "first answer"),
            agyw_record(
                "agyw_fgd_01_turn_0002",
                "agyw_fgd_01",
                "r1",
                "second answer",
                preceding=["agyw_fgd_01_turn_0001"],
            ),
            agyw_record("agyw_fgd_01_turn_0003", "agyw_fgd_01", "r2", "another speaker"),
            agyw_record("agyw_fgd_02_turn_0001", "agyw_fgd_02", "r1", "same label new group"),
            agyw_record(
                "agyw_fgd_02_turn_0002",
                "agyw_fgd_02",
                None,
                "collective context",
                eligible=False,
            ),
        ]
        manifest = self.build_agyw_candidate(records, clusters=3)
        record_groups = {tuple(entry["record_ids"]) for entry in manifest["clusters"]}
        self.assertIn(
            ("agyw_fgd_01_turn_0001", "agyw_fgd_01_turn_0002"), record_groups
        )
        self.assertIn(("agyw_fgd_01_turn_0003",), record_groups)
        self.assertIn(("agyw_fgd_02_turn_0001",), record_groups)
        self.assertNotIn(("agyw_fgd_02_turn_0002",), record_groups)
        self.assertEqual(manifest["cluster_unit"], "focus_group_and_transcript_local_speaker")

    def test_sampling_is_byte_deterministic_for_same_seed(self) -> None:
        records = [
            dreaddit_record(f"dreaddit_train_{index:05d}", f"dreaddit_train_post_{index:05d}", f"fixture {index}")
            for index in range(1, 5)
        ]
        first = self.build_dreaddit_candidate(records, clusters=2)
        second = self.build_dreaddit_candidate(copy.deepcopy(records), clusters=2)
        self.assertEqual(review.canonical_json_bytes(first), review.canonical_json_bytes(second))

    def test_pending_heldout_control_blocks_before_records_access(self) -> None:
        template_path = DATASET_ROOT / "manifests" / "dreaddit_agyw_heldout_freeze.template.json"
        with mock.patch.object(
            review,
            "read_records_snapshot",
            side_effect=AssertionError("protected records were opened"),
        ) as protected_read:
            with self.assertRaisesRegex(ValueError, "not authorized"):
                review.prepare_candidate_from_paths(
                    corpus="agyw_focus_groups",
                    split="heldout_cross_domain_evaluation",
                    requested_clusters=1,
                    sampling_seed="fixture-heldout-seed",
                    selection_control_path=template_path,
                )
        protected_read.assert_not_called()

    def test_heldout_control_requires_clean_preaccess_freeze(self) -> None:
        source_sha = review.file_sha256(
            review.CORPORA["agyw_focus_groups"]["source_manifest"]
        )
        control = {
            "document_type": "dreaddit_agyw_selection_control",
            "schema_version": "1.0",
            "status": "authorized_for_local_candidate_selection",
            "corpus": "agyw_focus_groups",
            "split": "heldout_cross_domain_evaluation",
            "local_candidate_selection_authorized": True,
            "authorization_reference": "fixture-authorization",
            "authorized_by": "fixture-authority",
            "authorized_at_utc": "2026-08-25T20:00:00Z",
            "records_sha256": DUMMY_SHA,
            "source_manifest_sha256": source_sha,
            "requested_cluster_count": 1,
            "sampling_seed_sha256": review.sha256_bytes(b"fixture-heldout-seed"),
            "sampling_plan_sha256": "d" * 64,
            "heldout": {
                "is_heldout": True,
                "freeze_status": "pending_not_frozen",
                "frozen_at_utc": None,
                "heldout_access_log_clean": False,
                "packet_rules_sha256": None,
                "prompt_sha256": None,
                "model_snapshot": None,
                "outcomes_sha256": None,
                "analysis_code_sha256": None,
            },
            "warning": review.SELECTION_CONTROL_WARNING,
        }
        with self.assertRaisesRegex(ValueError, "not frozen"):
            review.validate_selection_control_before_record_access(
                control,
                corpus="agyw_focus_groups",
                split="heldout_cross_domain_evaluation",
                requested_clusters=1,
                sampling_seed_sha256=review.sha256_bytes(b"fixture-heldout-seed"),
                expected_source_manifest_sha256=source_sha,
            )

    def test_review_bundle_starts_pending_and_ledger_contains_no_text(self) -> None:
        records = [
            agyw_record(
                "agyw_fgd_01_turn_0001",
                "agyw_fgd_01",
                "r1",
                "fictional review excerpt",
                moderator="fictional moderator context",
            )
        ]
        candidate = self.build_agyw_candidate(records, clusters=1)
        packets, ledger = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        self.assertEqual(len(packets), 1)
        self.assertEqual(ledger["status"], "pending_two_person_privacy_review")
        self.assertEqual(ledger["entries"][0]["reviews"], [])
        self.assertFalse(ledger["entries"][0]["privacy_review_complete"])
        self.assertFalse(ledger["experiment_use_ready"])
        serialized_ledger = json.dumps(ledger, sort_keys=True)
        self.assertNotIn('"text":', serialized_ledger)
        self.assertNotIn('"source_id":', serialized_ledger)

    def test_free_form_review_notes_are_rejected(self) -> None:
        records = [
            dreaddit_record(
                "dreaddit_train_00001",
                "dreaddit_train_post_00001",
                "fictional excerpt",
            )
        ]
        candidate = self.build_dreaddit_candidate(records)
        packets, ledger = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        unsafe_review = approved_review("REV_A1B2C3D4")
        unsafe_review["notes_reference"] = "free-form detail from the excerpt"
        ledger["entries"][0]["reviews"] = [unsafe_review]
        with self.assertRaisesRegex(ValueError, "opaque"):
            review.validate_ledger_shape_and_reviews(ledger, packets)

    def test_two_distinct_reviewers_complete_only_local_privacy_gate(self) -> None:
        records = [
            dreaddit_record("dreaddit_train_00001", "dreaddit_train_post_00001", "fictional excerpt")
        ]
        candidate = self.build_dreaddit_candidate(records)
        packets, ledger = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        entry = ledger["entries"][0]
        entry["reviews"] = [approved_review("REV_A1B2C3D4"), approved_review("REV_E5F6A7B8")]
        entry["privacy_review_complete"] = True
        entry["permitted_uses"] = {
            "model_processing": True,
            "rater_display": True,
            "quotation": False,
        }
        ledger["status"] = "privacy_review_complete_local_governance_still_required"
        summary = review.validate_ledger_shape_and_reviews(ledger, packets)
        self.assertEqual(summary["privacy_review_complete"], 1)
        self.assertEqual(summary["experiment_use_ready"], 0)
        self.assertFalse(entry["experiment_use_ready"])
        self.assertFalse(ledger["experiment_use_ready"])

    def test_duplicate_reviewer_cannot_satisfy_two_person_gate(self) -> None:
        records = [
            dreaddit_record("dreaddit_train_00001", "dreaddit_train_post_00001", "fictional excerpt")
        ]
        candidate = self.build_dreaddit_candidate(records)
        packets, ledger = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        entry = ledger["entries"][0]
        entry["reviews"] = [approved_review("REV_A1B2C3D4"), approved_review("REV_A1B2C3D4")]
        with self.assertRaisesRegex(ValueError, "distinct"):
            review.validate_ledger_shape_and_reviews(ledger, packets)

    def test_single_reviewer_cannot_set_completion_true(self) -> None:
        records = [
            dreaddit_record("dreaddit_train_00001", "dreaddit_train_post_00001", "fictional excerpt")
        ]
        candidate = self.build_dreaddit_candidate(records)
        packets, ledger = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        entry = ledger["entries"][0]
        entry["reviews"] = [approved_review("REV_A1B2C3D4")]
        entry["privacy_review_complete"] = True
        with self.assertRaisesRegex(ValueError, "completion"):
            review.validate_ledger_shape_and_reviews(ledger, packets)

    def test_exact_date_cannot_be_tampered_into_review_packet(self) -> None:
        records = [
            dreaddit_record("dreaddit_train_00001", "dreaddit_train_post_00001", "fictional excerpt")
        ]
        candidate = self.build_dreaddit_candidate(records)
        packets, _ = review.build_review_bundle(
            records,
            candidate,
            candidate_file="candidate_manifest.json",
            candidate_sha256="e" * 64,
        )
        packets[0]["review_content"]["text"] = "tampered on 2026-08-25"
        packets[0]["content_sha256"] = review.sha256_bytes(
            review.canonical_compact_bytes(packets[0]["review_content"])
        )
        with self.assertRaisesRegex(ValueError, "exact date"):
            review.validate_packet_shapes(packets)

    def test_private_writer_sets_0700_and_0600(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "restricted" / "artifact.json"
            review.atomic_write_private(target, b"{}\n", replace=False)
            self.assertEqual(review.mode(target.parent), 0o700)
            self.assertEqual(review.mode(target), 0o600)

    def test_checked_in_audits_match_current_immutable_bundles(self) -> None:
        summary = validator.validate_canonical_audits()
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["dreaddit_exact_date_quarantine"]["matched_records"], 13)
        self.assertEqual(
            summary["agyw_participant_reconciliation"]["observed_transcript_local_speaker_keys"],
            106,
        )
        self.assertEqual(
            summary["agyw_participant_reconciliation"]["reported_source_participants"],
            107,
        )

    def test_audit_validation_does_not_open_heldout_agyw_records(self) -> None:
        original_reader = validator.read_records_snapshot

        def guarded_reader(path: Path) -> tuple[list[dict], str]:
            if path == review.CORPORA["agyw_focus_groups"]["records"]:
                raise AssertionError("held-out AGYW records were opened")
            return original_reader(path)

        with mock.patch.object(
            validator, "read_records_snapshot", side_effect=guarded_reader
        ):
            summary = validator.validate_canonical_audits()
        self.assertEqual(summary["status"], "ok")

    def test_real_records_remain_unapproved(self) -> None:
        for corpus in ("dreaddit", "agyw_focus_groups"):
            records, _ = review.read_records_snapshot(review.CORPORA[corpus]["records"])
            for record in records:
                self.assertTrue(record["quality"]["manual_excerpt_review_required"])
                self.assertIn(record["quality"].get("privacy_review_status"), (None, "pending"))


if __name__ == "__main__":
    unittest.main()
