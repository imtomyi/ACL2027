"""Identity-bound transport regression fixtures, not experiment evidence."""

import copy
import itertools
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

import ace_flaw_contract as c
import run_ace_flaw_8h as run
import test_ace_8h_runtime as fixtures


class WireTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.RuntimeTests()
        fixture.setUp()
        self.fixture = fixture
        self.task, self.review = fixture.task, fixture.review

    def final_wire(self, decisions):
        issues = [{**self.fixture.issue, "id": f"candidate-{i}"} for i in range(len(decisions))]
        draft = {**self.review, "issues": issues}
        assessments = {}
        for issue, decision in zip(issues, decisions):
            fields = {"decision": decision, "reason": "Grounded assessment."}
            if decision == "retain":
                fields["issue"] = {k: v for k, v in issue.items() if k != "id"}
            assessments[issue["id"]] = fields
        return {"assessments": assessments, "no_retained_decision": "cannot_judge",
                "unresolved": [], "rationale": "Scoped conclusion."}, {"candidate": draft, "task": self.task}

    def test_all_disposition_combinations_preserve_exact_ids(self):
        for choices in itertools.product(("retain", "discard", "unresolved"), repeat=3):
            wire, data = self.final_wire(choices)
            final = c.decode_wire("finalizer", wire, data)
            c.check_final(final, data["candidate"], self.task)
            self.assertEqual([i["id"] for i in final["review"]["issues"]],
                             [f"candidate-{i}" for i, choice in enumerate(choices) if choice == "retain"])

    def test_empty_candidate_finalizes_without_invented_ids(self):
        wire, data = self.final_wire([])
        final = c.decode_wire("finalizer", wire, data)
        c.check_final(final, data["candidate"], self.task)
        self.assertEqual(final["review"]["decision"], "cannot_judge")

    def test_discard_cannot_emit_retained_issue(self):
        wire, data = self.final_wire(["retain"])
        wire["assessments"]["candidate-0"]["decision"] = "discard"
        with self.assertRaises(ValidationError):
            c.decode_wire("finalizer", wire, data)

    def test_unknown_or_missing_candidate_rejected(self):
        for newkey in ("unrelated", None):
            wire, data = self.final_wire(["retain"])
            assessment = wire["assessments"].pop("candidate-0")
            if newkey:
                wire["assessments"][newkey] = assessment
            with self.assertRaises(ValidationError):
                c.decode_wire("finalizer", wire, data)

    def test_generated_issue_ids_are_positional_not_model_copied(self):
        wire = copy.deepcopy(self.review)
        wire["issues"] = [{k: v for k, v in self.fixture.issue.items() if k != "id"}] * 2
        parsed = c.decode_wire("detector", wire, {"task": self.task})
        self.assertEqual([i["id"] for i in parsed["issues"]], ["issue_1", "issue_2"])

    def test_repeated_unbounded_text_is_rejected(self):
        wire, data = self.final_wire([])
        wire["rationale"] = "No new response is required. " * 100
        with self.assertRaises(ValidationError):
            c.decode_wire("finalizer", wire, data)

    def test_quality_coverage_is_bound_and_false_null_preserved(self):
        quality = copy.deepcopy(self.fixture.quality)
        quality.update(credibility=False, conformability=None)
        quality["allegations"] = {a["prediction_id"]: {k: v for k, v in a.items() if k != "prediction_id"}
                                  for a in quality["allegations"]}
        data = {"review": self.review, "provisional_reference": self.review}
        parsed = c.decode_wire("quality", quality, data)
        c.check_quality(parsed, self.review, self.review)
        self.assertIs(parsed["credibility"], False)
        self.assertIsNone(parsed["conformability"])
        quality["allegations"] = {}
        with self.assertRaises(ValidationError):
            c.decode_wire("quality", quality, data)

    def test_no_reference_disables_matches_and_patch_proposals(self):
        empty = {**self.review, "decision": "no_flaw_established", "issues": []}
        schema = c.wire_schema("learning", {"provisional_reference": empty})
        self.assertEqual(schema["properties"]["patches"]["maxItems"], 0)
        schema = c.wire_schema("quality", {"review": self.review, "provisional_reference": None})
        self.assertEqual(schema["properties"]["matches"]["maxItems"], 0)

    def test_patch_audit_covers_exact_proposal(self):
        wire = {"edits": {a["patch_id"]: {k: v for k, v in a.items() if k != "patch_id"}
                           for a in self.fixture.audit["edits"]}}
        parsed = c.decode_wire("patch_audit", wire, {"learning": self.fixture.learning})
        self.assertEqual(parsed, self.fixture.audit)

    def test_add_target_is_empty_and_seed_replacement_is_impossible(self):
        wire = copy.deepcopy(self.fixture.learning)
        wire["patches"] = [{k: v for k, v in p.items() if k != "id"} for p in wire["patches"]]
        data = {"provisional_reference": self.review, "current_playbook": c.visible_memory(c.SEED)}
        parsed = c.decode_wire("learning", wire, data)
        self.assertEqual(parsed["patches"][0]["id"], "patch_1")
        for operation in ("add", "replace"):
            wire["patches"][0].update(operation=operation, target_rule_id="seed-warrant")
            with self.assertRaises(ValidationError):
                c.decode_wire("learning", wire, data)

    def test_audit_rejection_without_quotes_withholds_without_error(self):
        for vote in (False, None, True):
            audit = copy.deepcopy(self.fixture.audit)
            audit["edits"][0].update(grounded_lesson=vote, evidence=[])
            self.assertFalse(c.audit_approved(audit, self.fixture.learning, self.task))

    def test_audit_bad_quote_never_approves_even_with_true_votes(self):
        audit = copy.deepcopy(self.fixture.audit)
        audit["edits"][0]["evidence"][0]["quote"] = "Fabricated support."
        self.assertFalse(c.audit_approved(audit, self.fixture.learning, self.task))

    def test_audit_rejection_is_not_a_technical_trajectory(self):
        audit = copy.deepcopy(self.fixture.audit)
        audit["edits"][0].update(grounded_lesson=False, evidence=[])
        with tempfile.TemporaryDirectory() as temp:
            result = run.execute_job(self.fixture.client(temp, patch_audit=audit),
                                     self.fixture.job(), self.fixture.packet(), c.SEED)
            self.assertFalse(result["technical_trajectory"])
            self.assertEqual(result["learning_status"], "withheld_semantic_audit")
            self.assertEqual(result["memory_after"], c.SEED)

    def test_returned_length_limit_is_preserved_never_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            client = run.Client(Path(temp), time.time() + 500)
            body = {"done": True, "done_reason": "length", "response": "{incomplete"}
            class Reply:
                def __enter__(self):
                    import io
                    return io.StringIO(json.dumps(body))
                def __exit__(self, *args):
                    pass
            with patch.object(run.urllib.request, "urlopen", return_value=Reply()) as http:
                for _ in range(2):
                    with self.assertRaisesRegex(ValueError, "incomplete_generation"):
                        client.call("test", "detector", {"task": self.task})
                self.assertEqual(http.call_count, 1)
            self.assertEqual(run.read(Path(temp)/"calls/test/response.json")["body"], body)

    def test_upstream_failure_does_not_claim_learning_failed(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run.execute_job(self.fixture.client(temp, detector=ValueError("incomplete_generation")),
                                     self.fixture.job(), self.fixture.packet(), c.SEED)
            self.assertEqual(result["error_stage"], "diagnosis")
            self.assertEqual(result["learning_status"], "not_reached")
            self.assertEqual(result["memory_after"], c.SEED)


if __name__ == "__main__":
    unittest.main()
