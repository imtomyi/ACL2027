"""Offline scoring fixtures, not experiment observations or gold annotations."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ace_flaw_contract as base
import strict_flaw_scoring as scoring
import ace_online_contract as online
import run_ace_flaw_online as runtime
from test_ace_online import FakeClient, packet, wire_review


def review():
    return base.decode_wire("detector", wire_review(), {})


def gold_for(item, negative=False):
    value = review()
    if negative:
        value.update(decision="no_flaw_established", issues=[])
    return {"packet_id": item["packet_id"], "task_sha256": base.digest(item["task"]),
        "annotation_status": "adjudicated", "inventory_complete": True, "verified_negative": negative,
        "adjudicator": "OFFLINE FIXTURE ONLY", "adjudication_record": "Not real annotation evidence",
        "review": value}


def assessment(data, unknown=False):
    return {"pairs": {p["key"]: {**{k: None if unknown else True for k in scoring.CRITERIA},
        "reason": "The scope and target match in this fixture.",
        "evidence": [{"excerpt_id": "excerpt_alpha", "quote": "school stress"}],
        "whole_packet_reason": ""} for p in data["candidate_pairs"]},
        "credibility": True, "conformability": True,
        "credibility_reason": "Fixture diagnosis is grounded.", "conformability_reason": "Fixture preserves context."}


class StrictScoringTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.review = packet(), review()
        self.gold = gold_for(self.packet)

    def receipt(self, unknown=False):
        preliminary = scoring.score_packet(self.packet, self.review, self.gold)
        data = scoring.judge_input(self.packet, self.review, self.gold, preliminary)
        return scoring.judge_receipt(self.packet, self.review, self.gold, data, assessment(data, unknown), "fixture", "fixture")

    def score(self, receipt=None, quality=None):
        return scoring.score_packet(self.packet, self.review, self.gold, receipt, quality)

    def test_correct_type_target_and_grounding_is_tp(self):
        result = self.score(self.receipt(), {"credibility": True, "conformability": True})
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 0, 0))
        self.assertTrue(result["exact_packet_correct"])
        self.assertTrue(result["detection_gated_credibility"])

    def test_wrong_type_is_fp_and_fn_even_with_positive_quality(self):
        self.review["issues"][0]["category"] = "contextual_flattening"
        result = self.score(quality={"credibility": True, "conformability": True})
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 1, 1))
        self.assertFalse(result["detection_gated_credibility"])
        self.assertEqual(next(t for t in result["by_type"] if t["category"] == "contextual_flattening")["fp"], 1)
        self.assertEqual(next(t for t in result["by_type"] if t["category"] == "unsupported_inference")["fn"], 1)

    def test_each_semantic_criterion_is_required(self):
        for criterion in scoring.CRITERIA:
            with self.subTest(criterion=criterion):
                receipt = self.receipt()
                receipt["pairs"][0][criterion] = False
                result = self.score(receipt)
                self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 1, 1))

    def test_duplicate_detection_receives_only_one_match(self):
        self.review["issues"].append({**copy.deepcopy(self.review["issues"][0]), "id": "issue_2"})
        result = self.score(self.receipt())
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 1, 0))
        self.assertFalse(result["exact_packet_correct"])

    def test_empty_output_does_not_get_credit_from_rationale_or_quality(self):
        self.review.update(decision="no_flaw_established", issues=[], rationale="There is unsupported inference.")
        result = self.score(quality={"credibility": True, "conformability": True})
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 0, 1))
        self.assertFalse(result["detection_gated_conformability"])

    def test_bad_evidence_or_target_cannot_match(self):
        for field in ("claim_quote", "evidence"):
            self.review = review()
            self.review["issues"][0][field] = "fabricated" if field == "claim_quote" else [{"excerpt_id": "excerpt_alpha", "quote": "fabricated"}]
            result = self.score()
            self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 1, 1))

    def test_other_category_is_not_a_wildcard(self):
        self.review["issues"][0]["category"] = "other_material_flaw"
        self.assertEqual(self.score()["tp"], 0)

    def test_uncertain_match_stays_unresolved(self):
        result = self.score(self.receipt(unknown=True))
        self.assertEqual(result["status"], "pair_adjudication_pending")
        self.assertIsNone(result["tp"])

    def test_grounded_false_criterion_outweighs_unknown(self):
        receipt = self.receipt(unknown=True)
        receipt["pairs"][0]["same_target"] = False
        self.assertEqual(self.score(receipt)["tp"], 0)

    def test_judge_fabricated_evidence_is_not_accepted(self):
        receipt = self.receipt()
        receipt["pairs"][0]["evidence"][0]["quote"] = "invented"
        self.assertIsNone(self.score(receipt)["tp"])

    def test_receipt_identity_and_complete_pair_coverage_required(self):
        for field in ("task_sha256", "prediction_sha256", "gold_sha256", "pairs"):
            receipt = self.receipt()
            receipt[field] = [] if field == "pairs" else "wrong"
            with self.assertRaises(ValueError):
                self.score(receipt)

    def test_unqualified_gold_is_not_scored(self):
        self.gold["annotation_status"] = "intended_only"
        result = self.score()
        self.assertEqual(result["status"], "gold_unavailable")
        self.assertIsNone(result["exact_packet_correct"])

    def test_gold_task_and_integrity_are_checked(self):
        self.gold["task_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "gold_task_binding"):
            self.score()
        self.gold = gold_for(self.packet)
        self.gold["review"]["issues"][0]["claim_quote"] = "invented"
        with self.assertRaisesRegex(ValueError, "gold_integrity_failure"):
            self.score()

    def test_verified_negative_only_can_be_true_negative(self):
        self.gold = gold_for(self.packet, negative=True)
        self.review.update(decision="no_flaw_established", issues=[])
        result = self.score()
        self.assertTrue(result["true_negative"])
        self.assertIsNone(result["recall"])
        self.assertEqual(scoring.aggregate([result], 1)["specificity"], 1)

    def test_abstention_or_failure_is_never_a_true_negative(self):
        self.gold = gold_for(self.packet, negative=True)
        self.review.update(decision="cannot_judge", issues=[])
        self.assertFalse(self.score()["true_negative"])
        failure = scoring.score_packet(self.packet, None, self.gold, execution_status="technical_failure")
        self.assertFalse(failure["true_negative"])

    def test_technical_failure_on_positive_retains_fn(self):
        result = scoring.score_packet(self.packet, None, self.gold, execution_status="technical_failure")
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (0, 0, 1))
        self.assertFalse(result["exact_packet_correct"])

    def test_failures_cannot_discard_existing_review(self):
        with self.assertRaisesRegex(ValueError, "must_not_discard"):
            scoring.score_packet(self.packet, self.review, self.gold, execution_status="technical_failure")

    def test_partial_coverage_does_not_report_selected_subset_as_100_percent(self):
        row = self.score(self.receipt(), {"credibility": True})
        result = scoring.aggregate([row], 2)
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["detection_gated_credibility"]["success_rate"])
        self.assertEqual(result["confirmed_exact_correct_fraction_of_plan"], .5)

    def test_full_coverage_aggregates_types_and_keeps_zero_denominator_unknown(self):
        result = scoring.aggregate([self.score(self.receipt())], 1)
        self.assertEqual(result["macro_f1_over_gold_supported_types"], 1)
        self.assertIsNone(result["specificity"])
        self.assertIsNone(next(t for t in result["by_type"] if t["category"] == "contextual_flattening")["recall"])

    def test_bank_requires_exact_coverage(self):
        inputs = {"dreaddit": {"evaluation": [self.packet]}}
        bank = {"protocol": scoring.VERSION, "items": [{"dataset": "dreaddit", **self.gold}]}
        self.assertEqual(len(scoring.validate_bank(bank, inputs)), 1)
        bank["items"].append(copy.deepcopy(bank["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicates"):
            scoring.validate_bank(bank, inputs)

    def test_taxonomy_bridge_is_fixed(self):
        self.assertEqual(scoring.INTENDED_TO_CATEGORY["source_concentration"], "hidden_source_concentration")
        self.assertEqual(scoring.INTENDED_TO_CATEGORY["counterevidence_loss"], "lost_negative_case")
        self.assertEqual(len(scoring.INTENDED_TO_CATEGORY), 5)

    def test_maximum_matching_not_greedy_first_match(self):
        self.review["issues"].append({**copy.deepcopy(self.review["issues"][0]), "id": "issue_2"})
        self.gold["review"]["issues"].append({**copy.deepcopy(self.gold["review"]["issues"][0]), "id": "gold_2"})
        receipt = self.receipt()
        for pair in receipt["pairs"]:
            if pair["prediction_id"] == "issue_2" and pair["gold_id"] == "gold_2":
                pair["same_target"] = False
        self.assertEqual(self.score(receipt)["tp"], 2)


class DetectionClient(FakeClient):
    def __init__(self, root):
        super().__init__(root)
        self.mode = "correct"

    def call(self, key, role, data):
        if role == "flaw_judge":
            self.calls.append((key, role, copy.deepcopy(data)))
            if self.mode == "judge_failure":
                raise ValueError("offline_assessment_failure")
            value = assessment(data, unknown=self.mode == "unknown")
            return scoring.decode_judge(value, data)
        value = super().call(key, role, data)
        if role == "online_detector" and self.mode == "empty":
            value["review"].update(decision="no_flaw_established", issues=[])
            for check in value["rule_checks"].values():
                check.update(outcome="no_flaw_supported", issue_indices=[])
        return value


class StrictRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = {ds: {"development": [packet(ds + "_dev", ds + "_dev_source", ds + " dev school stress")],
                         "evaluation": [packet(ds + "_stream", ds + "_stream_source", ds + " stream school stress")]}
                     for ds in runtime.DATASETS}
        self.jobs = runtime.schedule(self.data, 0)
        self.config = {"protocol": online.VERSION, "scoring_profile": scoring.VERSION,
            "gold_status": "complete_adjudicated_inventory", "networkx_version": scoring.nx.__version__,
            "development_n": 1, "stream_n": 1, "epochs": 0, "options": runtime.OPTIONS,
            "base_url": runtime.legacy.BASE, "paid_api_allowed": False, "model": runtime.legacy.MODEL,
            "call_ceiling": 24}
        self.bank = {"protocol": scoring.VERSION, "items": [
            {"dataset": ds, **gold_for(p)} for ds, phases in self.data.items() for p in phases["evaluation"]]}
        for name, value in (("inputs.private.json", self.data), ("schedule.json", self.jobs),
                            ("config.json", self.config), ("gold.private.json", self.bank)):
            runtime.write_json(self.root / name, value)
        self.client = DetectionClient(self.root)

    def job(self):
        job = self.jobs[0]
        return job, self.data[job["dataset"]]["evaluation"][0]

    def test_strict_flow_locks_both_predictions_and_isolates_gold(self):
        job, item = self.job()
        runtime.process_job(self.client, job, item, online.seed_state(), None)
        self.assertEqual([role for _, role, _ in self.client.calls],
            ["online_detector", "online_detector", "flaw_judge", "flaw_judge", "online_learning", "online_audit"])
        for _, role, data in self.client.calls:
            if role in ("online_detector", "online_learning", "online_audit"):
                self.assertNotIn("gold_review", data)
                self.assertNotIn("candidate_pairs", data)
                self.assertNotIn("credibility", data)
            if role == "flaw_judge":
                self.assertEqual(set(data), {"task", "review", "gold_review", "integrity_findings", "candidate_pairs"})
        n = len(self.client.calls)
        runtime.process_job(self.client, job, item, online.seed_state(), None)
        self.assertEqual(len(self.client.calls), n)

    def test_full_detection_exports_use_strict_denominators(self):
        status = runtime.worker(self.root, self.client)
        self.assertEqual(status["scored_detection_packets"], 8)
        self.assertEqual(status["binary_quality_pairs"], 8)
        self.assertEqual(len(self.client.calls), 24)
        self.assertEqual(runtime.read(self.root / "final_manifest.json")["status"], "completed_detection_scored")
        with (self.root / "results_table_online.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["confirmed_tp"] == "1" for r in rows))
        self.assertNotIn("credibility_success_pct_binary", rows[0])
        self.assertIn("detection_gated_credibility_success_rate", rows[0])
        with (self.root / "detection_by_type.csv").open() as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 48)

    def test_empty_reviews_cannot_earn_quality_success_or_trigger_quality_redraw(self):
        self.client.mode = "empty"
        runtime.worker(self.root, self.client)
        self.assertNotIn("flaw_judge", [role for _, role, _ in self.client.calls])
        row = runtime.load_record(self.root / "results" / self.jobs[0]["id"] / "result.json")["value"]
        self.assertEqual(row["detection"]["online"]["fn"], 1)
        self.assertIs(row["quality"]["online"]["value"]["credibility"], False)

    def test_unknown_pair_has_no_headline_accuracy_and_no_false_complete(self):
        self.client.mode = "unknown"
        status = runtime.worker(self.root, self.client)
        self.assertEqual(status["scored_detection_packets"], 0)
        self.assertEqual(runtime.read(self.root / "final_manifest.json")["status"], "completed_with_unresolved_detection_or_quality")
        with (self.root / "results_table_online.csv").open() as handle:
            self.assertTrue(all(r["exact_packet_accuracy"] == "" for r in csv.DictReader(handle)))

    def test_assessment_failure_preserves_predictions_and_reports_unresolved(self):
        self.client.mode = "judge_failure"
        status = runtime.worker(self.root, self.client)
        self.assertEqual(status["scored_detection_packets"], 0)
        self.assertEqual(status["technical_failures_by_stage"]["flaw_judge"], 8)
        self.assertEqual(len(list((self.root / "predictions").glob("**/*.locked.json"))), 8)

    def test_missing_gold_blocks_worker_before_first_call(self):
        self.config["gold_status"] = "missing_blocks_inference"
        runtime.write_json(self.root / "config.json", self.config, replace=True)
        with self.assertRaisesRegex(ValueError, "adjudicated_gold_required"):
            runtime.worker(self.root, self.client)
        self.assertFalse(self.client.calls)

    def test_missing_gold_blocks_launch_before_model_contact(self):
        self.config["gold_status"] = "missing_blocks_inference"
        runtime.write_json(self.root / "config.json", self.config, replace=True)
        (self.root / "Storage/rq2_personal_local_diagnostic").mkdir(parents=True)
        with patch.object(runtime, "verify", return_value={"project_root": str(self.root)}), \
                patch.object(runtime.legacy, "model_identity") as identity:
            with self.assertRaisesRegex(ValueError, "adjudicated_gold_required"):
                runtime.run_local(self.root)
        identity.assert_not_called()

    def test_missing_bank_rows_block_before_first_call(self):
        self.bank["items"].pop()
        runtime.write_json(self.root / "gold.private.json", self.bank, replace=True)
        with self.assertRaisesRegex(ValueError, "gold_bank_incomplete"):
            runtime.worker(self.root, self.client)
        self.assertFalse(self.client.calls)

    def test_combined_judge_request_is_local_and_schema_bound(self):
        job, item = self.job()
        gold = gold_for(item)
        preliminary = scoring.score_packet(item, review(), gold)
        data = scoring.judge_input(item, review(), gold, preliminary)
        request, bound = runtime.build_request(self.config, "flaw_judge", data)
        self.assertLess(bound, self.config["options"]["num_ctx"])
        self.assertIn("pair_1", request["format"]["properties"]["pairs"]["properties"])
        self.assertNotIn("playbook", data)

    def test_prepare_with_gold_is_offline_and_freezes_bank(self):
        source = self.root / "source"
        source.mkdir()
        runtime.write_json(source / "inputs.private.json", self.data)
        runtime.write_json(source / "manifest.json", {"model_digest": "fixture",
            "files": {"inputs.private.json": runtime.file_hash(source / "inputs.private.json")}})
        prepared = self.root / "prepared"
        with patch.object(runtime.urllib.request, "urlopen", side_effect=AssertionError("No network")):
            status = runtime.prepare(prepared, source, 0, self.root / "gold.private.json")
        self.assertFalse(status["inference_blocked"])
        self.assertIn("gold.private.json", runtime.verify(prepared)["files"])
        self.assertFalse((prepared / "clock.json").exists())


if __name__ == "__main__":
    unittest.main()
