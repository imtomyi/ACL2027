"""Offline planning fixtures, not experiment results or runtime integration tests."""

import copy
import unittest

import plan_gemma_8h as design


class EightHourPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = design.read(design.PLAN)

    def test_counts_include_judging_and_patch_audits(self):
        result = design.workload(self.plan)
        self.assertEqual(result["core_calls_max"], 1080)
        self.assertEqual(result["all_calls_max"], 1200)
        self.assertEqual(result["core_quality_bundles"], 160)
        self.assertEqual(result["patch_audit_calls_max"], 120)

    def test_unsafe_scope_is_rejected(self):
        for key in ("generate_themes", "evaluation_feedback_to_memory", "paid_api_allowed"):
            changed = copy.deepcopy(self.plan)
            changed[key] = True
            with self.assertRaises(ValueError):
                design.workload(changed)

    def test_null_and_technical_do_not_become_false(self):
        counts = design.quality_counts([True, False, None, "technical_failure"], 5)
        self.assertEqual((counts["true"], counts["false"], counts["null"], counts["E"]), (1, 1, 1, 2))
        self.assertEqual(counts["resolved_case_pct"], 50)
        self.assertEqual(counts["binary_coverage_pct"], 40)
        self.assertIsNone(counts["full_panel_pct"])
        self.assertEqual(counts["missingness_bound_not_ci"], [20, 80])

    def test_complete_quality_panel(self):
        counts = design.quality_counts([True] * 17 + [False] * 3, 20)
        self.assertEqual(counts["full_panel_pct"], 85)
        self.assertEqual(counts["binary_coverage_pct"], 100)

    def test_empty_quality_is_not_a_pass(self):
        counts = design.quality_counts([], 20)
        self.assertIsNone(counts["resolved_case_pct"])
        self.assertIsNone(counts["full_panel_pct"])
        self.assertEqual(counts["binary_coverage_pct"], 0)

    def test_invalid_quality_values_rejected(self):
        for values in ([1], ["true"], [False] * 21):
            with self.assertRaises(ValueError):
                design.quality_counts(values, 20)

    def test_patch_needs_every_criterion_true(self):
        audit = {key: True for key in design.AUDIT_CRITERIA}
        self.assertTrue(design.can_commit_patch_batch(True, [audit], 1))
        for bad in (False, None, 1):
            changed = dict(audit, grounded_lesson=bad)
            self.assertFalse(design.can_commit_patch_batch(True, [changed], 1))
        self.assertFalse(design.can_commit_patch_batch(False, [audit], 1))
        self.assertFalse(design.can_commit_patch_batch(True, [], 0))

    def test_batch_is_atomic(self):
        audit = {key: True for key in design.AUDIT_CRITERIA}
        bad = dict(audit, no_leakage=False)
        self.assertFalse(design.can_commit_patch_batch(True, [audit, bad], 2))

    def test_common_epoch_not_best_per_corpus(self):
        epochs = {ds: {0, 1, 2, 3} for ds in design.DATASETS}
        epochs["cache"] = {0, 1}
        result = design.selected_checkpoint(epochs, self.plan)
        self.assertEqual(result["label"], "budget_limited_E1")
        self.assertFalse(result["adaptation_completed"])

    def test_no_adaptation_is_labeled(self):
        result = design.selected_checkpoint({ds: {0} for ds in design.DATASETS}, self.plan)
        self.assertEqual(result["label"], "budget_limited_E0")

    def test_invalid_epoch_chain_rejected(self):
        epochs = {ds: {0, 2} for ds in design.DATASETS}
        with self.assertRaises(ValueError):
            design.selected_checkpoint(epochs, self.plan)

    def test_core_priority_and_finalization(self):
        self.assertEqual(design.next_phase(27000, False, True, self.plan), "mandatory_core")
        self.assertEqual(design.next_phase(27900, False, True, self.plan), "finalize_only")
        self.assertEqual(design.next_phase(28800, True, True, self.plan), "stopped_at_budget")
        self.assertEqual(design.next_phase(24000, True, False, self.plan), "finalize_only")

    def test_core_schedule_is_paired_and_balanced(self):
        panels = {ds: [f"{ds}-packet-{i}" for i in range(20)] for ds in design.DATASETS}
        jobs = design.evaluation_schedule(panels, 3, self.plan)
        self.assertEqual(len(jobs), 160)
        self.assertEqual(len({j["id"] for j in jobs}), 160)
        self.assertEqual([j["epoch"] for j in jobs[:8]], [0, 3] * 4)
        self.assertEqual([j["dataset"] for j in jobs[:8:2]], design.DATASETS)
        self.assertTrue(all(j["judge_immediately"] for j in jobs))

    def test_seed_only_fallback_is_not_rerun_as_adapted(self):
        panels = {ds: [f"{ds}-packet-{i}" for i in range(20)] for ds in design.DATASETS}
        jobs = design.evaluation_schedule(panels, 0, self.plan)
        self.assertEqual(len(jobs), 80)

    def test_invalid_checkpoint_is_rejected(self):
        panels = {ds: [f"{ds}-packet-{i}" for i in range(20)] for ds in design.DATASETS}
        for checkpoint in (-1, 4, True):
            with self.assertRaises(ValueError):
                design.evaluation_schedule(panels, checkpoint, self.plan)


if __name__ == "__main__":
    unittest.main()
