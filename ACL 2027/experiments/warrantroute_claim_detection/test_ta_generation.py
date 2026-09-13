"""Source-free software fixtures, never experimental or manuscript evidence."""

import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

import run_ta_generation_smoke as runner
import ta_generation_contract as c


def fixture():
    source = {"source_record_id": "fixture_record", "source_id": "fixture_source",
              "excerpt_id": "fixture_excerpt", "text": "The test fixture mentions an uncertain plan."}
    packet = {"artifact_id": "TA_FIXTURE", "sources": [source],
              "source_packet_sha256": runner.runtime.digest([source])}
    anchor = {"source_record_id": "fixture_record", "quote": "uncertain plan"}
    value = {"codes": [{"code_id": "C001", "label": "Fixture uncertainty",
        "definition": "Source-free software example.", "scope": "Fixture only.",
        "evidence": [anchor], "rationale": "Tests exact source linkage."}],
        "subthemes": [], "themes": [], "source_notes": [{"source_record_id": "fixture_record",
        "code_ids": ["C001"], "note": "Fixture only."}], "limitations": ["Software fixture."],
        "theme_status": "codes_only", "theme_status_reason": "Single fixture, not a TA study."}
    return packet, value


def config():
    return {"model": "gemma3:4b", "model_digest": "fixture_digest", "base_url": runner.runtime.legacy.BASE,
        "paid_api_allowed": False, "options": {"num_ctx": 32768, "num_predict": 8192},
        "call_ceiling": 3, "timeout_seconds": 300, "research_question": c.QUESTION,
        "analytic_contract": c.ORIENTATION}


class ContractTests(unittest.TestCase):
    def test_codes_only_and_exact_offsets(self):
        packet, value = fixture()
        result = c.inspect(value, packet)
        self.assertEqual(result["flags"], [])
        a = result["resolved_anchors"][0]
        span = a["offsets"][0]
        self.assertEqual(packet["sources"][0]["text"][span["start"]:span["end"]], a["quote"])
        self.assertEqual(result["sources_with_exact_code_anchor"], ["fixture_record"])

    def test_faulty_quote_is_retained_and_flagged(self):
        packet, value = fixture()
        value["codes"][0]["evidence"][0]["quote"] = "Not actually in the source."
        original = copy.deepcopy(value)
        result = c.inspect(value, packet)
        self.assertEqual(value, original)
        self.assertEqual(result["flags"][0]["kind"], "source_anchor_unresolved")

    def test_repeated_quote_is_ambiguous(self):
        packet, value = fixture()
        packet["sources"][0]["text"] = "uncertain plan; uncertain plan"
        result = c.inspect(value, packet)
        self.assertEqual(len(result["resolved_anchors"][0]["offsets"]), 2)
        self.assertEqual(result["flags"][0]["kind"], "source_anchor_ambiguous")

    def test_invalid_graph_and_duplicate_ids(self):
        packet, value = fixture()
        value["codes"].append(copy.deepcopy(value["codes"][0]))
        value["themes"] = [{"theme_id": "T001", "name": "Fixture", "organizing_concept": "Fixture",
            "analytic_claim": "Fixture", "code_ids": ["C999"], "subtheme_ids": ["S999"],
            "evidence": [], "scope": "Fixture", "negative_cases": [], "qualifications": []}]
        kinds = {f["kind"] for f in c.inspect(value, packet)["flags"]}
        self.assertTrue({"duplicate_unit_ids", "missing_or_unknown_code_link", "unknown_subtheme_link",
                         "theme_status_mismatch", "missing_evidence"} <= kinds)

    def test_schema_failure_is_not_empty_analysis(self):
        packet, _ = fixture()
        with self.assertRaises(ValidationError):
            c.inspect({}, packet)

    def test_no_reference_or_memory_leakage(self):
        packet, _ = fixture()
        packet.update(claim="DO_NOT_SEND", gold="DO_NOT_SEND", playbook="DO_NOT_SEND")
        request, bound = c.request(config(), packet)
        self.assertNotIn("DO_NOT_SEND", request["prompt"])
        self.assertLessEqual(bound, 32768)
        self.assertIn(packet["sources"][0]["text"], request["prompt"])

    def test_context_overflow_and_paid_api_fail_closed(self):
        packet, _ = fixture()
        settings = config()
        settings["options"]["num_ctx"] = 100
        with self.assertRaisesRegex(ValueError, "context_admission"):
            c.request(settings, packet)
        settings = config()
        settings["paid_api_allowed"] = True
        with self.assertRaisesRegex(ValueError, "local_only"):
            c.request(settings, packet)

    def test_request_without_response_never_retries(self):
        packet, _ = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            req, _ = c.request(config(), packet)
            runner.runtime.write_json(run / "calls/TA_FIXTURE/request.json", {"request_sha256": runner.runtime.digest(req)})
            with patch("urllib.request.urlopen") as send:
                with self.assertRaises(runner.runtime.AmbiguousCall):
                    runner.generate(run, config(), packet, time.time() + 600)
                send.assert_not_called()

    def test_reuse_preserves_model_output_without_calls(self):
        packet, value = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            req, _ = c.request(config(), packet)
            folder = run / "calls/TA_FIXTURE"
            body = {"done": True, "done_reason": "stop", "response": json.dumps(value)}
            runner.runtime.write_json(folder / "request.json", {"request_sha256": runner.runtime.digest(req)})
            runner.runtime.write_json(folder / "response.json", {"request_sha256": runner.runtime.digest(req),
                "body_sha256": runner.runtime.digest(body), "body": body, "wall_seconds": 1})
            with patch("urllib.request.urlopen") as send:
                first = runner.generate(run, config(), packet, time.time() + 600)
                second = runner.generate(run, config(), packet, time.time() + 600)
                self.assertEqual(first, second)
                send.assert_not_called()
            artifact = runner.runtime.read(run / "ta_artifacts/TA_FIXTURE/artifact.locked.json")
            self.assertEqual(artifact["content"], value)

    def test_incomplete_generation_does_not_create_artifact(self):
        packet, value = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            req, _ = c.request(config(), packet)
            folder = run / "calls/TA_FIXTURE"
            body = {"done": True, "done_reason": "length", "response": json.dumps(value)}
            runner.runtime.write_json(folder / "request.json", {"request_sha256": runner.runtime.digest(req)})
            runner.runtime.write_json(folder / "response.json", {"request_sha256": runner.runtime.digest(req),
                "body_sha256": runner.runtime.digest(body), "body": body, "wall_seconds": 1})
            with self.assertRaisesRegex(ValueError, "incomplete_generation"):
                runner.generate(run, config(), packet, time.time() + 600)
            self.assertFalse((run / "ta_artifacts").exists())


if __name__ == "__main__":
    unittest.main()
