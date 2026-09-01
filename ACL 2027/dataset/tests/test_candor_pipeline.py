#!/usr/bin/env python3
"""Regression tests for the CANDOR-only restricted transcript lane."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DATASET_ROOT.parent
SCRIPTS_ROOT = DATASET_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from prepare_candor import (  # noqa: E402
    CANDOR_FIXTURE_ROOT,
    discover_transcripts,
    enforce_path_policy,
    inventory_transcripts,
    load_json,
    validate_adapter,
    validate_source_manifest,
)
from validate_candor import (  # noqa: E402
    read_jsonl,
    run as run_validation,
    validate_linkage_groups,
    validate_record_shape,
)


OUTPUT = PROJECT_ROOT / "Storage" / "synthetic-results" / "dataset-demos" / "candor_demo_output"
ADAPTER = DATASET_ROOT / "manifests" / "candor_demo_adapter.json"
SOURCE_MANIFEST = DATASET_ROOT / "manifests" / "candor_demo_source_manifest.json"
SPLIT_MANIFEST = DATASET_ROOT / "manifests" / "candor_demo_split_manifest.json"


class CandorPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = read_jsonl(OUTPUT / "records.jsonl")
        cls.groups = read_jsonl(OUTPUT / "linkage_groups.jsonl")

    def test_checked_demo_passes_full_validation(self) -> None:
        args = argparse.Namespace(
            output=OUTPUT,
            adapter=ADAPTER,
            source_manifest=SOURCE_MANIFEST,
            split_manifest=SPLIT_MANIFEST,
            demo=True,
            validation_report=None,
            replace_report=False,
        )
        summary = run_validation(args)
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["records"], 9)
        self.assertEqual(summary["sources"], 3)
        self.assertEqual(summary["speakers"], 5)
        self.assertEqual(summary["linkage_components"], 2)
        self.assertEqual(summary["eligible_for_packet_sampling"], 0)

    def test_linked_speaker_keeps_two_conversations_together(self) -> None:
        linked = [group for group in self.groups if group["source_count"] == 2]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["record_count"], 6)
        self.assertEqual(linked[0]["speaker_count"], 3)
        speaker_sources: dict[str, set[str]] = defaultdict(set)
        speaker_splits: dict[str, set[str]] = defaultdict(set)
        for record in self.records:
            speaker_sources[record["speaker_id"]].add(record["source_id"])
            speaker_splits[record["speaker_id"]].add(record["split"])
        repeated = [speaker for speaker, sources in speaker_sources.items() if len(sources) == 2]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(len(speaker_splits[repeated[0]]), 1)

    def test_deliberate_cross_split_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.records)
        speaker_sources: dict[str, set[str]] = defaultdict(set)
        for record in tampered:
            speaker_sources[record["speaker_id"]].add(record["source_id"])
        repeated_speaker = next(
            speaker for speaker, sources in speaker_sources.items() if len(sources) > 1
        )
        next(record for record in tampered if record["speaker_id"] == repeated_speaker)[
            "split"
        ] = "leaking_demo_split"
        with self.assertRaisesRegex(ValueError, "Component spans splits"):
            validate_linkage_groups(tampered, self.groups)

    def test_timestamp_like_turn_index_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.records[0])
        tampered["context"]["turn_index"] = "2026-08-25T09:00:00Z"
        with self.assertRaisesRegex(ValueError, "derived ordinal"):
            validate_record_shape(tampered)

    def test_raw_and_discarded_fixture_values_are_absent(self) -> None:
        serialized = (OUTPUT / "records.jsonl").read_text(encoding="utf-8")
        for forbidden_value in (
            "fixture-person-",
            "raw-demo-conversation-",
            "synthetic-survey-",
            "2026-08-25T",
            "audio/demo-",
            "video/demo-",
            "participant_age",
            "post_conversation_survey",
            "raw_conversation_id",
        ):
            self.assertNotIn(forbidden_value, serialized)
        for record in self.records:
            self.assertEqual(record["sampling_strata"], {})
            self.assertIsInstance(record["context"]["turn_index"], int)

    def test_every_record_remains_pending_and_ineligible(self) -> None:
        for record in self.records:
            quality = record["quality"]
            self.assertFalse(quality["eligible_for_packet_sampling"])
            self.assertTrue(quality["manual_excerpt_review_required"])
            self.assertEqual(quality["privacy_review_status"], "pending")
            self.assertEqual(
                quality["ineligible_reasons"], ["manual_privacy_review_pending"]
            )

    def test_demo_input_guard_rejects_arbitrary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "restricted to"):
                enforce_path_policy(Path(temporary), None, demo=True)

    def test_missing_preferred_cliffhanger_files_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            with self.assertRaisesRegex(ValueError, "No authorized BetterUp"):
                discover_transcripts(Path(temporary))

    def test_exact_cliffhanger_path_wins_over_fallback_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            root = Path(temporary)
            transcription = root / "fictional-conversation" / "transcription"
            transcription.mkdir(parents=True)
            preferred = transcription / "transcript_cliffhanger.csv"
            preferred.write_text("speaker,text\nfixture-a,hello\n", encoding="utf-8")
            (transcription / "transcript.csv").write_text(
                "speaker,text\nfixture-b,fallback\n", encoding="utf-8"
            )
            (root / "utterances.jsonl").write_text(
                '{"text":"derived fallback"}\n', encoding="utf-8"
            )
            self.assertEqual(discover_transcripts(root), [preferred.resolve()])

    def test_demo_receipt_is_bound_to_fixture_checksums(self) -> None:
        inventory = inventory_transcripts(CANDOR_FIXTURE_ROOT / "package")
        manifest = load_json(SOURCE_MANIFEST)
        validate_source_manifest(manifest, inventory, demo=True)
        tampered = copy.deepcopy(manifest)
        tampered["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_source_manifest(tampered, inventory, demo=True)

    def test_adapter_field_roles_must_be_distinct(self) -> None:
        inventory = inventory_transcripts(CANDOR_FIXTURE_ROOT / "package")
        adapter = load_json(ADAPTER)
        adapter["fields"]["text"] = adapter["fields"]["speaker_id"]
        with self.assertRaisesRegex(ValueError, "distinct CSV columns"):
            validate_adapter(adapter, inventory, demo=True)

    def test_fresh_build_is_valid_and_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            generated = Path(temporary)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_ROOT / "prepare_candor.py"),
                    "build",
                    "--input-root",
                    str(CANDOR_FIXTURE_ROOT / "package"),
                    "--adapter",
                    str(ADAPTER),
                    "--source-manifest",
                    str(SOURCE_MANIFEST),
                    "--split-manifest",
                    str(SPLIT_MANIFEST),
                    "--output",
                    str(generated),
                    "--demo",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for filename in ("records.jsonl", "linkage_groups.jsonl", "build_report.json"):
                self.assertEqual(
                    (generated / filename).read_bytes(),
                    (OUTPUT / filename).read_bytes(),
                    filename,
                )
            args = argparse.Namespace(
                output=generated,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            self.assertEqual(run_validation(args)["status"], "ok")

    def test_phone_mask_preserves_word_boundary(self) -> None:
        phone_record = next(
            record
            for record in self.records
            if "phone_like_number" in record["quality"]["privacy_masks_applied"]
        )
        self.assertEqual(phone_record["text"], "Call [PHONE] on [DATE].")

    def test_existing_validation_report_must_match_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            copied = Path(temporary)
            for filename in (
                "records.jsonl",
                "linkage_groups.jsonl",
                "build_report.json",
                "validation_report.json",
            ):
                shutil.copy2(OUTPUT / filename, copied / filename)
            stale = json.loads((copied / "validation_report.json").read_text(encoding="utf-8"))
            stale["raw_conversation_id"] = "must-not-be-accepted"
            (copied / "validation_report.json").write_text(
                json.dumps(stale), encoding="utf-8"
            )
            args = argparse.Namespace(
                output=copied,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                run_validation(args)

    def test_unexpected_output_sidecar_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            copied = Path(temporary)
            for filename in ("records.jsonl", "linkage_groups.jsonl", "build_report.json"):
                shutil.copy2(OUTPUT / filename, copied / filename)
            (copied / "audio.wav").write_bytes(b"synthetic forbidden sidecar")
            args = argparse.Namespace(
                output=copied,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            with self.assertRaisesRegex(ValueError, "Unexpected file"):
                run_validation(args)

    def test_output_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            copied = Path(temporary)
            for filename in ("records.jsonl", "linkage_groups.jsonl", "build_report.json"):
                shutil.copy2(OUTPUT / filename, copied / filename)
            (copied / "validation_report.json").symlink_to(copied / "records.jsonl")
            args = argparse.Namespace(
                output=copied,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            with self.assertRaisesRegex(ValueError, "cannot contain symlinks"):
                run_validation(args)

    def test_validation_report_must_be_private(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            copied = Path(temporary)
            for filename in (
                "records.jsonl",
                "linkage_groups.jsonl",
                "build_report.json",
                "validation_report.json",
            ):
                shutil.copy2(OUTPUT / filename, copied / filename)
            (copied / "validation_report.json").chmod(0o644)
            args = argparse.Namespace(
                output=copied,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            with self.assertRaisesRegex(ValueError, "mode 0600"):
                run_validation(args)

    def test_build_report_context_window_must_match_adapter(self) -> None:
        with tempfile.TemporaryDirectory(dir=CANDOR_FIXTURE_ROOT) as temporary:
            copied = Path(temporary)
            for filename in ("records.jsonl", "linkage_groups.jsonl", "build_report.json"):
                shutil.copy2(OUTPUT / filename, copied / filename)
            report = json.loads((copied / "build_report.json").read_text(encoding="utf-8"))
            report["context_turns"] = 999
            (copied / "build_report.json").write_text(
                json.dumps(report), encoding="utf-8"
            )
            args = argparse.Namespace(
                output=copied,
                adapter=ADAPTER,
                source_manifest=SOURCE_MANIFEST,
                split_manifest=SPLIT_MANIFEST,
                demo=True,
                validation_report=None,
                replace_report=False,
            )
            with self.assertRaisesRegex(ValueError, "Context-window report mismatch"):
                run_validation(args)

    def test_build_report_contains_aggregates_not_text(self) -> None:
        report_text = (OUTPUT / "build_report.json").read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["records_written"], 9)
        self.assertEqual(report["privacy_review_pending"], 9)
        self.assertEqual(report["eligible_for_packet_sampling"], 0)
        self.assertEqual(report["transcription_algorithm"], "Cliffhanger")
        self.assertEqual(
            report["privacy_mask_counts"],
            {
                "email": 1,
                "exact_date": 1,
                "handle": 1,
                "ip_address": 1,
                "phone_like_number": 1,
                "url": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
