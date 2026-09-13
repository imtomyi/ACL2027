"""Offline protocol tests. These do not test an inference runner or scorer."""

import copy
import json
import unittest

from check_design_v5 import PLAN, verify_plan


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(PLAN.read_text())

    def test_exact_workload(self):
        result = verify_plan(self.plan)
        self.assertEqual(result["main"]["max_semantic_calls"], 62640)
        self.assertEqual(result["pilot"]["max_semantic_calls"], 465)
        self.assertEqual(result["main"]["evaluation_outputs"], 9840)

    def test_does_not_mutate_plan(self):
        before = copy.deepcopy(self.plan)
        verify_plan(self.plan)
        self.assertEqual(before, self.plan)

    def test_rejects_theme_generation(self):
        self.plan["generate_themes"] = True
        with self.assertRaisesRegex(ValueError, "generate_themes"):
            verify_plan(self.plan)

    def test_rejects_evaluation_learning(self):
        self.plan["evaluation_feedback_to_memory"] = True
        with self.assertRaisesRegex(ValueError, "evaluation_feedback"):
            verify_plan(self.plan)

    def test_rejects_unapproved_source_exception(self):
        self.plan["pilot"]["within_source_allowed"].append("parlamint-gb")
        with self.assertRaisesRegex(ValueError, "Source exception"):
            verify_plan(self.plan)

    def test_rejects_forced_binary_quality(self):
        self.plan["pilot"]["quality_states"] = [True, False]
        with self.assertRaisesRegex(ValueError, "Unknown judgments"):
            verify_plan(self.plan)

    def test_rejects_wrong_checkpoint_control(self):
        self.plan["main"]["arms"][3]["reuse"] = "full:E3"
        with self.assertRaisesRegex(ValueError, "checkpoint reuse"):
            verify_plan(self.plan)

    def test_rejects_unequal_learning_epochs(self):
        self.plan["main"]["arms"][1]["epochs"] = 1
        with self.assertRaisesRegex(ValueError, "Unmatched"):
            verify_plan(self.plan)

    def test_rejects_unfair_update_control(self):
        self.plan["main"]["arms"][2]["explicit_reflection"] = False
        with self.assertRaisesRegex(ValueError, "Delta ablation"):
            verify_plan(self.plan)

    def test_rejects_wrong_call_count(self):
        self.plan["main"]["expected"]["max_semantic_calls"] -= 1
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            verify_plan(self.plan)


if __name__ == "__main__":
    unittest.main()
