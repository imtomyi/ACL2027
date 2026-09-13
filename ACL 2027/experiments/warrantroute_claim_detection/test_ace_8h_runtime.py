"""Offline contract and execution fixtures. Never experimental evidence."""

import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import ace_flaw_contract as c
import plan_gemma_8h as plan
import run_ace_flaw_8h as run


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.task = {"claim": "Every account concerns work.", "cited_excerpt_ids": ["e1"],
                     "evidence": [{"excerpt_id": "e1", "source_id": "source-one", "text": "I worry about school."}]}
        self.issue = {"id": "issue-one", "category": "unsupported_inference", "target_kind": "assertion",
                      "claim_quote": self.task["claim"], "evidence": [{"excerpt_id": "e1", "quote": "I worry about school."}],
                      "whole_packet_no_support": "", "mechanism": "The assertion about work lacks support.",
                      "material_consequence": "The asserted topic is not warranted.", "counterconditions": "No work account is supplied."}
        self.review = {"decision": "established_flaw", "issues": [self.issue], "unresolved": [], "rationale": "The claim is unsupported."}
        self.learning = {"reflection": [{"type": "miss", "reason": "Inspect scope.", "evidence": self.issue["evidence"]}],
            "patches": [{"id": "patch-one", "operation": "add", "target_rule_id": "",
                         "applicability": "Universal topic assertions",
                         "detection_check": "Compare the claimed topic with each available account.",
                         "evidence_requirement": "Identify text about the asserted topic.",
                         "countercondition": "A topic difference alone is not always a contradiction.",
                         "reference_issue_ids": ["issue-one"], "evidence": self.issue["evidence"], "reason": "Check the warrant."}],
            "self_check": "A general checking procedure, not an answer."}
        self.audit = {"edits": [{"patch_id": "patch-one", **{k: True for k in plan.AUDIT_CRITERIA},
                                 "reason": "Grounded, reusable check.", "evidence": self.issue["evidence"]}]}
        self.quality = {"credibility": True, "conformability": None, "credibility_reason": "Grounded diagnosis.",
                        "conformability_reason": "Some premise is unresolved.",
                        "allegations": [{"prediction_id": "issue-one", "support": "supported", "reason": "A missing warrant."}],
                        "matches": [{"prediction_id": "issue-one", "reference_id": "issue-one", "category_correct": True, "reason": "Same grounded defect."}]}

    def client(self, folder, **overrides):
        responses = {"reference": self.review, "detector": self.review,
                     "finalizer": {"review": self.review, "dispositions": [{"candidate_id": "issue-one", "decision": "retain", "reason": "Grounded."}]},
                     "learning": self.learning, "patch_audit": self.audit, "quality": self.quality, **overrides}
        class Fake:
            def __init__(self):
                self.run = Path(folder)
                self.called = []
            def call(self, key, role, data):
                self.called.append(role)
                value = responses[role]
                if isinstance(value, Exception):
                    raise value
                return copy.deepcopy(value)
        return Fake()

    def job(self, phase="development"):
        return {"id": phase + "/dreaddit/E1/packet-one", "phase": phase, "dataset": "dreaddit",
                "epoch": 1, "position": 1, "packet_id": "packet-one"}

    def packet(self):
        return {"packet_id": "packet-one", "task": self.task, "task_sha256": plan.digest(self.task), "source_ids": ["source-one"]}

    def test_grounding_preserves_parseable_bad_quote(self):
        bad = copy.deepcopy(self.review)
        bad["issues"][0]["evidence"][0]["quote"] = "not in the evidence"
        checked = c.check_review(bad, self.task)
        self.assertEqual(checked["integrity_findings"][0]["kind"], "invalid_evidence_quote")
        self.assertEqual(bad["issues"][0]["evidence"][0]["quote"], "not in the evidence")

    def test_disposition_contradiction_is_a_semantic_finding(self):
        bad = copy.deepcopy(self.review)
        bad["decision"] = "no_flaw_established"
        checked = c.check_review(bad, self.task)
        self.assertEqual(checked["integrity_findings"][0]["kind"], "decision_issue_mismatch")
        self.assertEqual(bad["decision"], "no_flaw_established")

    def test_contradictory_candidate_reaches_scheduled_finalizer_without_new_draw(self):
        bad = copy.deepcopy(self.review)
        bad["decision"] = "no_flaw_established"
        with tempfile.TemporaryDirectory() as temp:
            client = self.client(temp, detector=bad)
            result = run.execute_job(client, self.job("evaluation"), self.packet(), c.SEED)
            self.assertEqual(result["status"], "valid")
            self.assertEqual(client.called.count("detector"), 1)
            self.assertEqual(client.called.count("finalizer"), 1)
            self.assertEqual(client.called.count("quality"), 1)

    def test_finalizer_cannot_add_unrelated_issue(self):
        final = {"review": copy.deepcopy(self.review), "dispositions": [{"candidate_id": "issue-one", "decision": "retain", "reason": "ok"}]}
        final["review"]["issues"][0]["id"] = "unrelated"
        with self.assertRaises(ValueError):
            c.check_final(final, self.review, self.task)

    def test_development_commits_after_audit_and_locks_prediction(self):
        with tempfile.TemporaryDirectory() as temp:
            client = self.client(temp)
            r = run.execute_job(client, self.job(), self.packet(), c.SEED)
            self.assertEqual(r["learning_status"], "applied")
            self.assertEqual(client.called, ["reference", "detector", "finalizer", "learning", "patch_audit"])
            self.assertEqual(len(r["memory_after"]), 3)
            self.assertTrue((Path(temp)/"predictions"/self.job()["id"]/"locked.json").exists())
            self.assertEqual(r["memory_after"][-1]["audit_job_id"], self.job()["id"])

    def test_audit_unknown_withholds_without_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            audit = copy.deepcopy(self.audit)
            audit["edits"][0]["grounded_lesson"] = None
            client = self.client(temp, patch_audit=audit)
            r = run.execute_job(client, self.job(), self.packet(), c.SEED)
            self.assertEqual(r["learning_status"], "withheld_semantic_audit")
            self.assertEqual(r["memory_after"], c.SEED)
            self.assertFalse(r["technical_trajectory"])
            self.assertEqual(client.called.count("patch_audit"), 1)

    def test_seed_cannot_be_replaced(self):
        learning = copy.deepcopy(self.learning)
        learning["patches"][0].update(operation="replace", target_rule_id=c.SEED[0]["id"])
        with self.assertRaises(ValueError):
            c.proposed_memory(c.SEED, learning, self.task, self.review, "packet-one", ["source-one"])

    def test_new_patch_does_not_relabel_old_rule_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            first = run.execute_job(self.client(temp), self.job(), self.packet(), c.SEED)
            changed = copy.deepcopy(self.learning)
            changed["patches"][0]["applicability"] = "Aggregate population assertions"
            job = {**self.job(), "id": "development/dreaddit/E1/packet-two", "packet_id": "packet-two", "position": 2}
            packet = {**self.packet(), "packet_id": "packet-two"}
            second = run.execute_job(self.client(temp, learning=changed), job, packet, first["memory_after"])
            old = next(r for r in second["memory_after"] if r["id"] == first["memory_after"][-1]["id"])
            self.assertEqual(old["audit_job_id"], self.job()["id"])

    def test_repeated_exposure_does_not_add_independent_support(self):
        first = c.proposed_memory(c.SEED, self.learning, self.task, self.review, "packet-one", ["source-one"])
        learning = copy.deepcopy(self.learning)
        learning["patches"][0].update(operation="replace", target_rule_id=first[-1]["id"])
        second = c.proposed_memory(first, learning, self.task, self.review, "packet-one", ["source-one"])
        self.assertEqual(second[-1]["support_packets"], ["packet-one"])
        self.assertEqual(second[-1]["support_sources"], ["source-one"])

    def test_retrieval_retains_seed_and_omits_provenance(self):
        memory = c.proposed_memory(c.SEED, self.learning, self.task, self.review, "packet-one", ["source-one"])
        retrieved = c.retrieve(memory, self.task)
        self.assertEqual([r["id"] for r in retrieved[:2]], [r["id"] for r in c.SEED])
        self.assertTrue(all("support_packets" not in r for r in retrieved))

    def test_evaluation_never_calls_learning_or_modifies_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            client = self.client(temp)
            r = run.execute_job(client, self.job("evaluation"), self.packet(), c.SEED)
            self.assertEqual(client.called, ["reference", "detector", "finalizer", "quality"])
            self.assertEqual(r["memory_before_sha256"], r["memory_after_sha256"])
            self.assertIsNone(r["quality"]["conformability"])

    def test_failed_quality_does_not_erase_review(self):
        with tempfile.TemporaryDirectory() as temp:
            r = run.execute_job(self.client(temp, quality=ValueError("bad quality schema")),
                                self.job("evaluation"), self.packet(), c.SEED)
            self.assertEqual(r["status"], "valid")
            self.assertEqual(r["quality_status"], "technical_failure")
            self.assertIn("review", r)

    def test_reference_is_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            client = self.client(temp)
            run.get_reference(client, "dreaddit", self.packet())
            run.get_reference(client, "dreaddit", self.packet())
            self.assertEqual(client.called, ["reference"])

    def test_bad_quote_reference_is_unavailable(self):
        bad = copy.deepcopy(self.review)
        bad["issues"][0]["claim_quote"] = "wrong"
        with tempfile.TemporaryDirectory() as temp:
            r = run.get_reference(self.client(temp, reference=bad), "dreaddit", self.packet())
            self.assertEqual(r["status"], "unavailable")
            self.assertIsNone(r["review"])

    def test_duplicate_matches_rejected(self):
        quality = copy.deepcopy(self.quality)
        quality["matches"].append(copy.deepcopy(quality["matches"][0]))
        with self.assertRaises(ValueError):
            c.check_quality(quality, self.review, self.review)

    def test_budget_does_not_dispatch_request(self):
        with tempfile.TemporaryDirectory() as temp:
            client = run.Client(Path(temp), time.time() + 100)
            with patch.object(run.urllib.request, "urlopen") as http:
                with self.assertRaises(run.BudgetStop):
                    client.call("test", "detector", {"task": self.task})
                http.assert_not_called()
            self.assertFalse((Path(temp)/"calls").exists())

    def test_ambiguous_request_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            client = run.Client(Path(temp), time.time() + 500)
            with patch.object(run.urllib.request, "urlopen", side_effect=TimeoutError("offline test")) as http:
                with self.assertRaises(run.AmbiguousCall):
                    client.call("test", "detector", {"task": self.task})
                with self.assertRaises(run.AmbiguousCall):
                    client.call("test", "detector", {"task": self.task})
                self.assertEqual(http.call_count, 1)

    def test_immutable_write_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"record.json"
            run.write_json(path, {"x": 1})
            with self.assertRaises(FileExistsError):
                run.write_json(path, {"x": 2})
            self.assertEqual(run.read(path), {"x": 1})

    def test_export_has_four_rows_and_separate_unknown_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = plan.read(plan.PLAN)
            run.write_json(root/"plan.json", p)
            inputs = {ds: {"evaluation": [{"packet_id": f"packet-{i}"} for i in range(20)]} for ds in p["datasets"]}
            run.write_json(root/"inputs.private.json", inputs)
            for ds in p["datasets"]:
                run.snapshot(root, ds, 0, c.SEED)
            status = run.export(root, "prepared_not_started")
            self.assertEqual(status["core_binary_quality_pairs"], 0)
            self.assertEqual(len(status["datasets"]), 4)
            self.assertEqual(status["datasets"]["dreaddit"]["credibility"]["unprocessed"], 20)
            self.assertTrue((root/"results_table_ACE.csv").exists())
            self.assertFalse((root/"final_manifest.json").exists())

    def test_complete_mocked_schedule_preserves_unknown_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = plan.read(plan.PLAN)
            run.write_json(root/"plan.json", p)
            data = {}
            for ds in p["datasets"]:
                data[ds] = {}
                for phase, n in (("development", 10), ("evaluation", 20)):
                    data[ds][phase] = [{**self.packet(), "packet_id": f"{ds}-{phase}-{i}"} for i in range(n)]
                run.snapshot(root, ds, 0, c.SEED)
            run.write_json(root/"inputs.private.json", data)
            run.write_json(root/"development_schedule.json", run.development_schedule(data, p))
            started = time.time()
            run.write_json(root/"clock.json", {"started_unix": started, "deadline": started+28800})
            empty_learning = {"reflection": [], "patches": [], "self_check": "No new lesson."}
            fake = self.client(root, learning=empty_learning)
            fake.deadline = started + 27900
            with patch.object(run, "verify", return_value={}), patch.object(run, "Client", return_value=fake):
                status = run.worker(root)
            self.assertEqual(status["state"], "completed_with_unresolved_quality")
            self.assertEqual(status["development_processed"], 120)
            self.assertEqual(status["core_reviews_processed"], 160)
            self.assertEqual(status["core_judgments_valid"], 160)
            self.assertEqual(status["core_binary_quality_pairs"], 0)
            self.assertEqual(status["optional_reviews_processed"], 40)
            self.assertEqual(status["selected_checkpoint"]["epoch"], 3)
            self.assertEqual(run.read(root/"final_manifest.json")["table_rows"], 4)


if __name__ == "__main__":
    unittest.main()
