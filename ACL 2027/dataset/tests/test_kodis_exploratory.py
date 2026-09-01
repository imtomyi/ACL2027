from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = DATASET_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from prepare_kodis_exploratory import (  # noqa: E402
    ANALYSIS_STATUS,
    EXPECTED_OUTPUT_FILES,
    SPLIT,
    SourceRow,
    WorkbookSnapshot,
    parse_bool,
    parse_chat,
    transform,
    validate_bundle,
    write_private,
)


class KodisExploratoryTests(unittest.TestCase):
    def snapshot(self) -> WorkbookSnapshot:
        return WorkbookSnapshot(
            source_file="fixture.xlsx",
            worksheet="Sheet1",
            source_rows=4,
            source_columns=8,
            rows=(
                SourceRow(
                    source_row=2,
                    dyad_id="raw-dyad-seller-first",
                    formatted_chat=(
                        "1 Seller: I am opening this conversation.\n"
                        "2 Seller: This is a valid repeated-role follow-up.\n"
                        "3 Buyer: I can respond now."
                    ),
                    outcome="Resolution",
                    buyer_is_ai=False,
                    seller_is_ai=False,
                ),
                SourceRow(
                    source_row=3,
                    dyad_id="raw-dyad-buyer-first",
                    formatted_chat=(
                        "1 Buyer: The first physical line starts here.\n"
                        "and this continuation belongs to the same message.\n"
                        "2 Seller: Understood."
                    ),
                    outcome="Impass",
                    buyer_is_ai="false",
                    seller_is_ai=0,
                ),
                SourceRow(
                    source_row=4,
                    dyad_id="raw-dyad-human-ai",
                    formatted_chat="nan Buyer: Human text that must be excluded.\nnan Seller: AI text that must be excluded.",
                    outcome="Resolution",
                    buyer_is_ai=False,
                    seller_is_ai=True,
                ),
                SourceRow(
                    source_row=5,
                    dyad_id="raw-dyad-missing",
                    formatted_chat=None,
                    outcome="Resolution",
                    buyer_is_ai=False,
                    seller_is_ai=False,
                ),
            ),
        )

    def test_parser_accepts_seller_first_and_repeated_roles(self) -> None:
        parsed = parse_chat(
            "1 Seller: Opening.\n2 Seller: More detail.\n3 Buyer: Reply."
        )
        self.assertEqual([role for role, _ in parsed.messages], ["seller", "seller", "buyer"])
        self.assertEqual(parsed.unparsable_leading_lines, 0)

    def test_parser_merges_continuation_and_drops_timestamp(self) -> None:
        parsed = parse_chat("10 Buyer: First line.\ncontinued here\n11 Seller: Reply.")
        self.assertEqual(parsed.messages[0], ("buyer", "First line. continued here"))
        self.assertEqual(parsed.continuation_lines, 1)
        self.assertNotIn("10", parsed.messages[0][1])

    def test_transform_filters_human_ai_and_missing_transcript(self) -> None:
        dialogues, turns, report = transform(self.snapshot(), source_sha256="a" * 64)
        self.assertEqual(len(dialogues), 2)
        self.assertEqual(len(turns), 5)
        self.assertEqual(report["filtering"]["excluded_non_human_dialogues"], 1)
        self.assertEqual(report["filtering"]["excluded_missing_human_human_transcripts"], 1)
        self.assertEqual(report["structure"]["seller_first_dialogues"], 1)
        self.assertEqual(report["structure"]["dialogues_with_repeated_role_transitions"], 1)
        self.assertEqual(report["structure"]["dialogues_with_continuation_lines"], 1)
        self.assertTrue(all(row["analysis_status"] == ANALYSIS_STATUS for row in dialogues))
        self.assertTrue(all(row["split"] == SPLIT for row in dialogues))

    def test_outputs_omit_raw_ids_ai_text_and_source_metadata(self) -> None:
        dialogues, turns, report = transform(self.snapshot(), source_sha256="a" * 64)
        rendered_dialogues = json.dumps(dialogues)
        rendered_turns = json.dumps(turns)
        rendered_report = json.dumps(report)
        record_files = rendered_dialogues + rendered_turns
        combined = record_files + rendered_report
        for forbidden in (
            "raw-dyad-",
            "Human text that must be excluded",
            "AI text that must be excluded",
            "b_country",
            "b_Gender",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("buyer_is_AI", record_files)
        self.assertNotIn("seller_is_AI", record_files)
        self.assertNotIn("I am opening this conversation", rendered_report)

    def test_reports_and_dialogue_index_contain_no_transcript_text(self) -> None:
        dialogues, _, report = transform(self.snapshot(), source_sha256="a" * 64)
        source_messages = [
            text
            for source_row in self.snapshot().rows
            if source_row.formatted_chat
            for _, text in parse_chat(source_row.formatted_chat).messages
        ]
        summary = json.dumps({"dialogues": dialogues, "report": report})
        for message in source_messages:
            self.assertNotIn(message, summary)

    def test_invalid_ai_flag_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid buyer_is_AI"):
            parse_bool("unknown", field="buyer_is_AI", source_row=2)

    def test_duplicate_dyad_ids_fail(self) -> None:
        snapshot = self.snapshot()
        duplicate = WorkbookSnapshot(
            source_file=snapshot.source_file,
            worksheet=snapshot.worksheet,
            source_rows=2,
            source_columns=snapshot.source_columns,
            rows=(snapshot.rows[0], snapshot.rows[0]),
        )
        with self.assertRaisesRegex(ValueError, "Duplicate source dyad"):
            transform(duplicate, source_sha256="a" * 64)

    def test_private_bundle_validation(self) -> None:
        dialogues, turns, report = transform(self.snapshot(), source_sha256="a" * 64)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "kodis_exploratory_private"
            output.mkdir(mode=0o700)
            for name, value in (
                ("dialogues.jsonl", dialogues),
                ("turns.jsonl", turns),
            ):
                content = b"".join(
                    (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    for row in value
                )
                write_private(output / name, content)
            write_private(output / "aggregate_report.json", (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            output_files = {}
            for name in ("dialogues.jsonl", "turns.jsonl", "aggregate_report.json"):
                path = output / name
                output_files[name] = {
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            write_private(
                output / "build_report.json",
                (json.dumps({"source_preserved": True, "output_files": output_files}) + "\n").encode("utf-8"),
            )
            self.assertEqual({path.name for path in output.iterdir()}, EXPECTED_OUTPUT_FILES)
            result = validate_bundle(
                output,
                report=report,
                expected_dialogues=len(dialogues),
                expected_turns=len(turns),
            )
            self.assertEqual(result["status"], "ok")
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o700)
            self.assertTrue(all((os.stat(path).st_mode & 0o777) == 0o600 for path in output.iterdir()))


if __name__ == "__main__":
    unittest.main()
