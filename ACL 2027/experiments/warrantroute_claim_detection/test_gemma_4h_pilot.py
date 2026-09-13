"""Offline software fixtures only, never experimental evidence."""

import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import gemma_4h_pilot as pilot


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.task = {"claim": "Every account blames work.", "evidence": [
            {"excerpt_id": "e1", "text": "I was worried about school.", "source_id": "s1"}]}
        self.review = {"decision": "established_flaw", "issues": [{
            "id": "i1", "category": "unsupported_inference", "target_kind": "assertion",
            "claim_quote": "Every account blames work.",
            "evidence": [{"excerpt_id": "e1", "quote": "worried about school"}],
            "mechanism": "The cited source concerns school, not work.",
            "material_consequence": "The asserted universal explanation is unwarranted."}],
            "rationale": "The claim is not warranted by the supplied account."}

    def test_exact_spans_and_original_preservation(self):
        before = copy.deepcopy(self.review)
        result = pilot.canonical_review(self.review, self.task)
        self.assertEqual(self.review, before)
        span = result["issues"][0]["evidence"][0]["span"]
        self.assertEqual(self.task["evidence"][0]["text"][slice(*span)], "worried about school")

    def test_reject_invalid_quote_and_duplicate_ids(self):
        changed = copy.deepcopy(self.review)
        changed["issues"][0]["evidence"][0]["quote"] = "fabricated quotation"
        with self.assertRaises(ValueError):
            pilot.canonical_review(changed, self.task)
        changed = copy.deepcopy(self.review)
        changed["issues"].append(copy.deepcopy(changed["issues"][0]))
        with self.assertRaises(ValueError):
            pilot.canonical_review(changed, self.task)

    def test_no_flaw_is_not_technical_failure(self):
        review = {"decision": "no_flaw_established", "issues": [], "rationale": "No material defect established."}
        self.assertEqual(pilot.canonical_review(review, self.task)["issues"], [])

    def test_omission_requires_evidence_but_not_literal_claim_span(self):
        changed = copy.deepcopy(self.review)
        changed["issues"][0].update(target_kind="omission", claim_quote="")
        self.assertIsNone(pilot.canonical_review(changed, self.task)["issues"][0]["claim_span"])
        changed["issues"][0]["evidence"] = []
        with self.assertRaises(ValueError):
            pilot.canonical_review(changed, self.task)

    def patch(self):
        return {"feedback": "Check universality.", "patches": [{"operation": "add", "target_rule_id": "",
            "applicability": "Universal explanations", "check": "Compare the proposed cause with every relevant account.",
            "countercondition": "Do not assume an uncited account contradicts the claim.",
            "reference_issue_ids": ["i1"], "reason": "A missing warrant matters."}], "self_check": "This is a general procedure."}

    def test_atomic_patch_rejection_and_seed_immutability(self):
        memory = copy.deepcopy(pilot.SEED)
        patch = self.patch()
        patch["patches"][0].update(operation="replace", target_rule_id=memory[0]["id"])
        with self.assertRaises(ValueError):
            pilot.apply_patches(memory, patch, self.task, self.review, "p1")
        self.assertEqual(memory, pilot.SEED)

    def test_repeated_support_is_not_new_independent_packet(self):
        patch = self.patch()
        memory = pilot.apply_patches(pilot.SEED, patch, self.task, self.review, "p1")
        patch["patches"][0].update(operation="replace", target_rule_id=memory[-1]["id"])
        later = pilot.apply_patches(memory, patch, self.task, self.review, "p1")
        self.assertEqual(later[-1]["support_packets"], ["p1"])
        self.assertFalse(any("support_packets" in rule for rule in pilot.retrieve(later, self.task)))

    def test_direct_identifiers_and_unknown_reference_rejected(self):
        for field, value in (("check", "Copy p1"), ("reference_issue_ids", ["missing"])):
            patch = self.patch()
            patch["patches"][0][field] = value
            with self.assertRaises(ValueError):
                pilot.apply_patches(pilot.SEED, patch, self.task, self.review, "p1")

    def test_schedule_count_fairness_and_probe_identity(self):
        data = {ds: {"development": [{"packet_id": f"{ds}-dev-{i}"} for i in range(5)],
                     "evaluation": [{"packet_id": f"{ds}-ev-{i}"} for i in range(15)]} for ds in pilot.DATASETS}
        jobs = pilot.schedule(data)
        self.assertEqual(len(jobs), 180)
        self.assertEqual(sum(j["phase"] == "development" for j in jobs), 60)
        self.assertEqual(len({j["id"] for j in jobs}), 180)
        self.assertEqual([j["dataset"] for j in jobs[:4]], list(pilot.DATASETS))
        for ds in pilot.DATASETS:
            probes = [{j["packet_id"] for j in jobs if j["dataset"] == ds and j["phase"] == "evaluation"
                       and j["epoch"] == epoch and j["position"] <= 5} for epoch in range(4)]
            self.assertTrue(all(p == probes[0] for p in probes))

    def test_immutable_file_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"record.json"
            pilot.write_json(path, {"original": True})
            with self.assertRaises(FileExistsError):
                pilot.write_json(path, {"original": False})
            self.assertEqual(pilot.read(path), {"original": True})

    def test_expired_budget_makes_no_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = pilot.Client(Path(tmp), time.time()-1)
            with self.assertRaises(pilot.BudgetStop):
                client.call("test", "detector", {}, pilot.REVIEW)
            self.assertFalse((Path(tmp)/"calls").exists())

    def test_ambiguous_transport_call_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = pilot.Client(Path(tmp), time.time()+60)
            with patch.object(pilot.urllib.request, "urlopen", side_effect=TimeoutError("test timeout")) as http:
                with self.assertRaises(pilot.AmbiguousCall):
                    client.call("test", "detector", {"task": self.task}, pilot.REVIEW)
                with self.assertRaises(pilot.AmbiguousCall):
                    client.call("test", "detector", {"task": self.task}, pilot.REVIEW)
                self.assertEqual(http.call_count, 1)
            self.assertTrue((Path(tmp)/"calls/test/request.json").exists())
            self.assertFalse((Path(tmp)/"calls/test/response.json").exists())


if __name__ == "__main__":
    unittest.main()
