import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_table3_review_quality as q


class ReviewQualityTests(unittest.TestCase):
    def setUp(self):
        self.design = q.read_json(q.BUNDLE / "design.json")
        self.schema = q.read_json(q.BUNDLE / "judge_output.schema.json")
        self.packet = {
            "corpus_id": "dreaddit", "packet_id": "PKT_test", "research_question": "Question",
            "answer_key": "hidden", "source_text_context": [{
                "excerpt_id": "EXC_one", "source_id": "record_one", "source_record_id": "record_one",
                "speaker_id": "speaker_one", "text": "Original text", "candidate_role": "counterevidence",
                "local_context": {"moderator_question": "Why?", "preceding_record_ids": []},
                "metadata": {"subreddit": "context", "stress_label": 1, "split": "dev"}}],
            "llm_generated_qualitative_claim": {"claim": "Claim text", "cited_excerpt_ids": ["EXC_one"],
                                                "theme_name": "hidden_target", "explanation": "builder_hint"}}
        self.rating = {"serious_error_flags": [], "rationale": "EXC_one supports the assessment.",
                       "disposition": "accept", "cannot_judge": [], "confidence": 4}
        self.unit = {"unit_id": "one", "corpus_id": "dreaddit", "method": "Generalist",
                     "reviewer_model_id": "qwen3:8b", "request_sha256": "request",
                     "payload": {"review_bundle": [{"review_id": "R1"}], "source_context": [{"excerpt_id": "E1"}]}}

    def response(self, credibility=True, conformability=False):
        return {"model": "qwen3:8b", "done": True, "done_reason": "stop", "prompt_eval_count": 1500,
                "response": json.dumps({"credibility": credibility, "conformability": conformability,
                                        "credibility_rationale": "R1 reflects E1.",
                                        "conformability_rationale": "R1 does not ground its inference in E1."})}

    def validate(self, response):
        return q.validate_response(response, self.unit, self.schema, self.design["proposed_generation"], "qwen3:8b")

    def test_nested_allowlist_and_shared_identifier(self):
        context, aliases = q.sanitize_packet(self.packet)
        source = context["source_context"][0]
        self.assertEqual(source["text"], "Original text")
        self.assertEqual(source["source_id"], source["source_record_id"])
        self.assertEqual(source["local_context"]["moderator_question"], "Why?")
        self.assertEqual(source["metadata"], {"subreddit": "context"})
        self.assertEqual(context["reviewed_claim"]["cited_excerpt_ids"], ["E1"])
        for secret in ("hidden_target", "builder_hint", "answer_key", "counterevidence", "stress_label"):
            self.assertNotIn(secret, q.canonical(context))
        self.assertEqual(aliases["EXC_one"], "E1")

    def test_unknown_metadata_blocks(self):
        self.packet["source_text_context"][0]["metadata"]["new_answer"] = "secret"
        with self.assertRaises(q.ContractError):
            q.sanitize_packet(self.packet)

    def test_server_log_distinguishes_truncated_zero_from_real_truncation(self):
        self.assertFalse(q.log_reports_truncation("stop processing: n_tokens = 1973, truncated = 0"))
        self.assertFalse(q.log_reports_truncation("truncated = false\n[GIN] 200"))
        self.assertTrue(q.log_reports_truncation("truncated = 1"))
        self.assertTrue(q.log_reports_truncation("truncating input prompt limit=8192"))

    def test_all_roles_are_retained_without_numeric_ratings(self):
        context, aliases = q.sanitize_packet(self.packet)
        ratings = {r: {**self.rating, "rationale": r + " EXC_one"} for r in q.ROLES}
        bundle = q.review_bundle(self.packet, context, aliases, ratings, list(q.ROLES))
        self.assertEqual(len(bundle["review_bundle"]), 3)
        self.assertTrue(all("confidence" not in r for r in bundle["review_bundle"]))
        self.assertEqual(bundle, q.review_bundle(self.packet, context, aliases, ratings, list(reversed(q.ROLES))))
        self.assertNotIn("EXC_one", q.canonical(bundle))

    def test_valid_false_and_null_are_not_errors(self):
        for value in (True, False, None):
            parsed, errors = self.validate(self.response(value, value))
            self.assertEqual(errors, [])
            self.assertIs(parsed["credibility"], value)

    def test_bad_types_missing_fields_duplicates_and_nonfinite(self):
        for raw in ('{"credibility":false}', '{"credibility":true,"credibility":false}', 'NaN'):
            response = self.response()
            response["response"] = raw
            self.assertTrue(self.validate(response)[1])
        self.assertTrue(self.validate(self.response("false"))[1])

    def test_rationale_limits_ids_and_completion(self):
        for text in (" ", "R99 has support.", "word " * 61):
            response = self.response()
            decision = json.loads(response["response"])
            decision["credibility_rationale"] = text
            response["response"] = json.dumps(decision)
            self.assertTrue(self.validate(response)[1])
        for change in ({"done_reason": "length"}, {"model": "other"}, {"prompt_eval_count": 8100}):
            self.assertTrue(self.validate({**self.response(), **change})[1])

    def test_no_premature_percent_or_null_coercion(self):
        units = [{**self.unit, "unit_id": str(i)} for i in range(100)]
        records = {str(i): {"status": "valid", "decision": {"credibility": i < 60, "conformability": None}} for i in range(100)}
        summary = q.summarize(units, records)
        self.assertEqual(summary["rows"][0]["credibility"]["percent"], 60)
        self.assertIsNone(summary["rows"][0]["conformability"]["percent"])
        self.assertEqual(summary["rows"][0]["conformability"]["unresolved"], 100)
        self.assertEqual(summary["completed_binary_pairs"], 0)
        del records["99"]
        self.assertIsNone(q.summarize(units, records)["rows"][0]["credibility"]["percent"])

    def test_attempt_recovery_and_immutable_valid_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = {"unit_id": "one", "attempt": 1, "status": "in_flight",
                       "request_sha256": "request", "contract_sha256": "contract"}
            q.write_json(root / "in_flight.json", attempt)
            q.recover_interrupted_attempt(root, {"contract_sha256": "contract"}, [self.unit])
            target = root / "attempts/one/01.json"
            self.assertEqual(q.read_json(target)["status"], "transport_error")
            before = target.read_bytes()
            q.write_json(root / "in_flight.json", attempt)
            q.recover_interrupted_attempt(root, {"contract_sha256": "contract"}, [self.unit])
            self.assertEqual(target.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                q.write_json(target, {"status": "valid"}, immutable=True)

    def test_export_preserves_detection_deferred_rows_and_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [["Dataset", "Method", "Model", "TP/N", "Recall", *q.HEADERS],
                    ["Dreaddit", "Generalist", "Qwen3 8B", "50/100", "50 [40,60]", "N/A", "N/A"],
                    ["Dreaddit", "WarrantRoute", "Qwen3 8B", "40/100", "40 [30,50]", "N/A", "N/A"]]
            csv_text, md_text = q.render_table(rows)
            q.atomic_write(root / "table_before.csv", csv_text)
            q.atomic_write(root / "table_before.md", "Original notes\n\n" + md_text)
            targets = {ext: str(root / ("output." + ext)) for ext in ("csv", "md")}
            for ext, path in targets.items():
                q.atomic_write(Path(path), (root / ("table_before." + ext)).read_text())
            summary = q.summarize([self.unit], {"one": {"status": "valid", "decision": {"credibility": True, "conformability": False}}})
            manifest = {"run_id": "test", "table_paths": targets}
            self.assertEqual(q.export_tables(root, manifest, summary)["status"], "updated")
            actual = list(csv.reader(io.StringIO(Path(targets["csv"]).read_text())))
            self.assertEqual(actual[1][:5], rows[1][:5])
            self.assertEqual(actual[1][5:], ["100.0", "0.0"])
            self.assertEqual(actual[2], rows[2])
            self.assertIn("Original notes", Path(targets["md"]).read_text())
            q.atomic_write(Path(targets["csv"]), "external edit")
            self.assertEqual(q.export_tables(root, manifest, summary)["status"], "external_edit_conflict")
            self.assertEqual(Path(targets["csv"]).read_text(), "external edit")


if __name__ == "__main__":
    unittest.main()
