from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = DATASET_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from prepare_kodis import (  # noqa: E402
    KODIS_DEMO_INPUT_ROOT,
    KODIS_DEMO_OUTPUT,
    KODIS_FIXTURE_ROOT,
    KODIS_RAW_ROOT,
    KODIS_TEST_OUTPUT_ROOT,
    build_records,
    enforce_demo_controls,
    inventory_snapshots,
    json_bytes,
    load_json_snapshot,
    require_private_mode,
    run_build,
    run_inspect,
    validate_adapter,
    validate_source_manifest,
    validate_split_manifest,
)
from validate_kodis import (  # noqa: E402
    run as run_validation,
    validate_linkage,
    validate_schema,
)


ADAPTER = DATASET_ROOT / "manifests" / "kodis_demo_adapter.json"
SOURCE_MANIFEST = DATASET_ROOT / "manifests" / "kodis_demo_source_manifest.json"
SPLIT_MANIFEST = DATASET_ROOT / "manifests" / "kodis_demo_split_manifest.json"
TEMPLATE_ADAPTER = DATASET_ROOT / "manifests" / "kodis_adapter.template.json"


class KodisPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = json.loads(ADAPTER.read_text(encoding="utf-8"))
        cls.source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        cls.split_manifest = json.loads(SPLIT_MANIFEST.read_text(encoding="utf-8"))
        cls.snapshots = inventory_snapshots(KODIS_DEMO_INPUT_ROOT, private=False)
        cls.entries = validate_source_manifest(cls.source_manifest, cls.snapshots, demo=True)
        cls.selected = [snapshot for snapshot in cls.snapshots if snapshot.relative_path == "kodis_dialogue_turns.jsonl"]
        cls.records = [
            json.loads(line)
            for line in (KODIS_DEMO_OUTPUT / "records.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.groups = [
            json.loads(line)
            for line in (KODIS_DEMO_OUTPUT / "linkage_groups.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        KODIS_TEST_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        os.chmod(KODIS_TEST_OUTPUT_ROOT, 0o700)

    def build_args(self, output: Path) -> argparse.Namespace:
        return argparse.Namespace(
            input_root=KODIS_DEMO_INPUT_ROOT,
            adapter=ADAPTER,
            source_manifest=SOURCE_MANIFEST,
            split_manifest=SPLIT_MANIFEST,
            secret_file=None,
            output=output,
            demo=True,
            replace=True,
        )

    def validation_args(
        self,
        output: Path,
        validation_report: Path | None = None,
        replace_report: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            input_root=KODIS_DEMO_INPUT_ROOT,
            output=output,
            adapter=ADAPTER,
            source_manifest=SOURCE_MANIFEST,
            split_manifest=SPLIT_MANIFEST,
            secret_file=None,
            demo=True,
            validation_report=validation_report,
            replace_report=replace_report,
        )

    def copy_bundle(self, target: Path, include_validation: bool = True) -> None:
        names = ["records.jsonl", "linkage_groups.jsonl", "build_report.json"]
        if include_validation:
            names.append("validation_report.json")
        for name in names:
            shutil.copy2(KODIS_DEMO_OUTPUT / name, target / name)
        os.chmod(target, 0o700)

    def modified_snapshot(self, transform) -> list:
        rows = [copy.deepcopy(row) for row in self.selected[0].rows]
        transform(rows)
        return [replace(self.selected[0], rows=tuple(rows))]

    def test_checked_demo_passes_full_validation(self) -> None:
        summary = run_validation(self.validation_args(KODIS_DEMO_OUTPUT))
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["records"], 24)
        self.assertEqual(summary["sources"], 3)
        self.assertEqual(summary["speakers"], 5)
        self.assertEqual(summary["linkage_components"], 2)
        self.assertEqual(summary["eligible_for_packet_sampling"], 0)

    def test_fresh_build_is_valid_and_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            with contextlib.redirect_stdout(io.StringIO()):
                run_build(self.build_args(output))
            for name in ("records.jsonl", "linkage_groups.jsonl", "build_report.json"):
                self.assertEqual((output / name).read_bytes(), (KODIS_DEMO_OUTPUT / name).read_bytes())
            summary = run_validation(
                self.validation_args(
                    output,
                    validation_report=output / "validation_report.json",
                    replace_report=True,
                )
            )
            self.assertEqual(summary["status"], "ok")
            self.assertEqual(
                json_bytes(summary),
                (KODIS_DEMO_OUTPUT / "validation_report.json").read_bytes(),
            )

    def test_human_ai_incomplete_and_nonmessage_rows_are_quarantined(self) -> None:
        report = json.loads((KODIS_DEMO_OUTPUT / "build_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["input_rows"], 29)
        self.assertEqual(report["input_sources"], 5)
        self.assertEqual(report["filtered_non_human_rows"], 2)
        self.assertEqual(report["filtered_non_human_sources"], 1)
        self.assertEqual(report["filtered_incomplete_rows"], 2)
        self.assertEqual(report["filtered_incomplete_sources"], 1)
        self.assertEqual(report["filtered_nonmessage_rows"], 1)
        self.assertEqual(report["records_written"], 24)

    def test_linked_participant_keeps_two_dialogues_in_one_component(self) -> None:
        linked = next(group for group in self.groups if len(group["source_ids"]) == 2)
        self.assertEqual(len(linked["speaker_ids"]), 3)
        self.assertEqual(linked["record_count"], 16)
        self.assertEqual(linked["split"], "development_demo")

    def test_cross_split_linkage_tamper_is_rejected(self) -> None:
        records = copy.deepcopy(self.records)
        groups = copy.deepcopy(self.groups)
        linked = next(group for group in groups if len(group["source_ids"]) == 2)
        record = next(value for value in records if value["source_id"] == linked["source_ids"][0])
        record["split"] = "heldout_demo"
        with self.assertRaisesRegex(ValueError, "component crosses splits"):
            validate_linkage(records, groups)

    def test_split_manifest_requires_exact_component_coverage(self) -> None:
        manifest = copy.deepcopy(self.split_manifest)
        manifest["assignments"].pop(next(iter(manifest["assignments"])))
        with self.assertRaisesRegex(ValueError, "cover every linkage component"):
            validate_split_manifest(manifest, {group["component_id"] for group in self.groups}, demo=True)

    def test_split_manifest_names_the_dialogue_participant_component_unit(self) -> None:
        self.assertEqual(
            self.split_manifest["assignment_unit"],
            "dialogue_participant_connected_component",
        )
        manifest = copy.deepcopy(self.split_manifest)
        manifest["assignment_unit"] = "conversation_speaker_connected_component"
        with self.assertRaisesRegex(ValueError, "assignment unit mismatch"):
            validate_split_manifest(
                manifest,
                {group["component_id"] for group in self.groups},
                demo=True,
            )

    def test_every_record_remains_pending_and_ineligible(self) -> None:
        for record in self.records:
            quality = record["quality"]
            self.assertFalse(quality["eligible_for_packet_sampling"])
            self.assertTrue(quality["manual_excerpt_review_required"])
            self.assertEqual(quality["privacy_review_status"], "pending")
            self.assertIn("manual_privacy_review_pending", quality["ineligible_reasons"])
            self.assertIn("model_or_rater_processing_not_authorized", quality["ineligible_reasons"])

    def test_raw_and_discarded_fixture_values_are_absent(self) -> None:
        staged = (KODIS_DEMO_OUTPUT / "records.jsonl").read_text(encoding="utf-8")
        linkage = (KODIS_DEMO_OUTPUT / "linkage_groups.jsonl").read_text(encoding="utf-8")
        combined = staged + linkage
        for forbidden in (
            "fixture-person-",
            "fixture-worker-",
            "fixture-dialogue-",
            "Syntheticland",
            "fixture-survey-",
            "2026-08-25T",
            "fixture-only private goal",
            "This fictional human-to-AI row",
            "This fictional incomplete dialogue",
            "Synthetic system event",
        ):
            self.assertNotIn(forbidden, combined)

    def test_phone_mask_preserves_word_boundaries(self) -> None:
        record = next(
            value
            for value in self.records
            if "phone_like_number" in value["quality"]["privacy_masks_applied"]
        )
        self.assertEqual(record["text"], "Call [PHONE] on [DATE].")

    def test_pending_template_is_rejected_for_real_processing(self) -> None:
        template = json.loads(TEMPLATE_ADAPTER.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "mapping remains unverified"):
            validate_adapter(template, self.selected, self.entries, demo=False)

    def test_adapter_text_cannot_map_to_obvious_metadata(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["fields"]["text"] = "country"
        adapter["discarded_input_fields"].remove("country")
        adapter["discarded_input_fields"].append("text")
        with self.assertRaisesRegex(ValueError, "obvious metadata field"):
            validate_adapter(adapter, self.selected, self.entries, demo=True)

    def test_adapter_field_roles_must_be_distinct(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["fields"]["text"] = adapter["fields"]["speaker_id"]
        with self.assertRaisesRegex(ValueError, "distinct input fields"):
            validate_adapter(adapter, self.selected, self.entries, demo=True)

    def test_demo_guard_rejects_arbitrary_input(self) -> None:
        args = self.build_args(KODIS_DEMO_OUTPUT)
        args.input_root = DATASET_ROOT / "fixtures"
        with self.assertRaisesRegex(ValueError, "input root"):
            enforce_demo_controls(args)

    def test_received_access_inspection_refuses_receipt_overwrite(self) -> None:
        output = KODIS_RAW_ROOT / "kodis_source_manifest.local.json"
        self.assertTrue(output.exists())
        before = output.read_bytes()
        args = argparse.Namespace(input_root=KODIS_RAW_ROOT, output=output, replace=False)
        with self.assertRaisesRegex(FileExistsError, "Refusing to replace"):
            run_inspect(args)
        self.assertEqual(output.read_bytes(), before)

    def test_missing_interaction_marker_fails_closed(self) -> None:
        selected = self.modified_snapshot(lambda rows: rows[0].__setitem__("interaction_type", None))
        with self.assertRaisesRegex(ValueError, "missing interaction type"):
            build_records(selected, self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_missing_completion_marker_fails_closed(self) -> None:
        selected = self.modified_snapshot(lambda rows: rows[0].__setitem__("dialogue_complete", None))
        with self.assertRaisesRegex(ValueError, "missing completion marker"):
            build_records(selected, self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_turn_gap_is_rejected(self) -> None:
        def change(rows):
            next(row for row in rows if row["turn_id"] == "c-8")["turn_index"] = 9

        with self.assertRaisesRegex(ValueError, "consecutive from one"):
            build_records(self.modified_snapshot(change), self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_short_complete_dialogue_is_rejected(self) -> None:
        def change(rows):
            next(row for row in rows if row["turn_id"] == "c-8")["event_type"] = "system"

        with self.assertRaisesRegex(ValueError, "fewer than eight"):
            build_records(self.modified_snapshot(change), self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_buyer_first_and_alternation_are_enforced(self) -> None:
        def change(rows):
            next(row for row in rows if row["turn_id"] == "c-1")["role"] = "seller"

        with self.assertRaisesRegex(ValueError, "begin with buyer|do not alternate"):
            build_records(self.modified_snapshot(change), self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_exact_duplicate_complete_dialogue_is_rejected(self) -> None:
        def change(rows):
            source = [row for row in rows if row["session_id"] == "fixture-dialogue-a" and row["event_type"] == "message"]
            target = [row for row in rows if row["session_id"] == "fixture-dialogue-c"]
            for source_row, target_row in zip(source, target, strict=True):
                target_row["text"] = source_row["text"]

        with self.assertRaisesRegex(ValueError, "Exact duplicate complete"):
            build_records(self.modified_snapshot(change), self.adapter, self.source_manifest, self.split_manifest, b"WarrantRoute KODIS synthetic fixture secret only", True)

    def test_source_receipt_checksum_binding(self) -> None:
        snapshots = [replace(self.selected[0], sha256="0" * 64)]
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            validate_source_manifest(self.source_manifest, snapshots, demo=True)

    def test_build_report_hash_binding_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            self.copy_bundle(output, include_validation=False)
            report = json.loads((output / "build_report.json").read_text(encoding="utf-8"))
            report["adapter_sha256"] = "0" * 64
            (output / "build_report.json").write_text(json.dumps(report), encoding="utf-8")
            os.chmod(output / "build_report.json", 0o600)
            with self.assertRaisesRegex(ValueError, "build report is not bound"):
                run_validation(self.validation_args(output))

    def test_shared_schema_tamper_is_rejected(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["raw_conversation_id"] = "must-not-pass"
        with self.assertRaisesRegex(ValueError, "shared experiment schema"):
            validate_schema(records)

    def test_private_output_modes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            self.copy_bundle(output, include_validation=False)
            os.chmod(output / "records.jsonl", 0o644)
            with self.assertRaisesRegex(ValueError, "permits group/other access"):
                run_validation(self.validation_args(output))

    def test_private_mode_helper_rejects_public_control(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            control = Path(temporary) / "control.json"
            control.write_text("{}", encoding="utf-8")
            os.chmod(control, 0o644)
            with self.assertRaisesRegex(ValueError, "permits group/other access"):
                require_private_mode(control, "test KODIS control")

    def test_unknown_output_sidecar_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            self.copy_bundle(output, include_validation=False)
            (output / "raw_ids.csv").write_text("forbidden", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected file"):
                run_validation(self.validation_args(output))

    def test_output_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            self.copy_bundle(output, include_validation=False)
            (output / "validation_report.json").symlink_to(output / "build_report.json")
            with self.assertRaisesRegex(ValueError, "cannot contain symlinks"):
                run_validation(self.validation_args(output))

    def test_existing_validation_report_must_match_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=KODIS_TEST_OUTPUT_ROOT) as temporary:
            output = Path(temporary)
            self.copy_bundle(output, include_validation=True)
            stale = json.loads((output / "validation_report.json").read_text(encoding="utf-8"))
            stale["raw_conversation_id"] = "must-not-be-accepted"
            (output / "validation_report.json").write_text(json.dumps(stale), encoding="utf-8")
            os.chmod(output / "validation_report.json", 0o600)
            with self.assertRaisesRegex(ValueError, "does not match"):
                run_validation(self.validation_args(output))


if __name__ == "__main__":
    unittest.main()
