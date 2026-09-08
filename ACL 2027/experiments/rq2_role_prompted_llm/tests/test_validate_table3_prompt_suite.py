from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


TEST_FILE = Path(__file__).resolve()
RQ2_ROOT = TEST_FILE.parents[1]
SCRIPT_DIR = RQ2_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_table3_prompt_suite as validator  # noqa: E402
import run_working_generalist_reviews as working_runner  # noqa: E402


class Table3PromptSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = RQ2_ROOT / "config/table3_baseline_prompt_suite_v2.json"
        cls.suite = json.loads(path.read_text(encoding="utf-8"))
        cls.packet = {
            "packet_schema_version": "test-only-v1",
            "packet_id": "PKT_TESTONLY",
            "research_question": "What pattern is supported?",
            "source_text_context": [{"excerpt_id": "EXC_TEST", "text": "Inert fixture."}],
            "llm_generated_qualitative_claim": {"claim": "An inert test claim."},
            "known_intended_flaw_type": "must_not_reach_prompt",
            "dataset_role": "must_not_reach_prompt",
            "handling": {"draft": True},
        }

    def test_suite_is_model_and_dataset_neutral(self) -> None:
        report = validator.validate_suite(copy.deepcopy(self.suite))
        self.assertEqual(report["status"], "valid")
        self.assertFalse(report["model_specific_prompt_overrides_allowed"])
        self.assertFalse(report["dataset_specific_prompt_overrides_allowed"])
        self.assertEqual(len(set(report["role_prompt_sha256"].values())), 3)
        self.assertEqual(report["fixed_role"], "qualitative_methods")
        self.assertEqual(
            report["method_roles"],
            {
                "Generalist": ["generalist"],
                "Fixed role": ["qualitative_methods"],
                "All roles": ["generalist", "qualitative_methods", "domain"],
            },
        )

    def test_model_specific_fixed_role_override_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["method_prompt_plan"]["Fixed role"]["roles_executed"] = ["domain"]
        suite["method_prompt_plan"]["Fixed role"]["prompt_sha256_by_role"] = {
            "domain": suite["roles"]["domain"]["prompt_sha256"]
        }
        with self.assertRaisesRegex(
            validator.PromptSuiteError, "fixed_role_method_roles_invalid"
        ):
            validator.validate_suite(suite)

    def test_method_prompt_hash_drift_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["method_prompt_plan"]["All roles"]["prompt_sha256_by_role"][
            "domain"
        ] = "0" * 64
        with self.assertRaisesRegex(
            validator.PromptSuiteError, "all_roles_method_prompt_hash_drift"
        ):
            validator.validate_suite(suite)

    def test_each_method_has_identical_task_text_across_models(self) -> None:
        for method, config in self.suite["method_prompt_plan"].items():
            expected = tuple(
                validator.build_prompt(self.suite, role, self.packet)
                for role in config["roles_executed"]
            )
            prompts_by_model = {
                model: tuple(
                    validator.build_prompt(self.suite, role, self.packet)
                    for role in config["roles_executed"]
                )
                for model in validator.MODELS
            }
            with self.subTest(method=method):
                self.assertEqual(set(prompts_by_model.values()), {expected})

    def test_projection_removes_answer_and_working_metadata(self) -> None:
        payload = validator.project_reviewer_payload(self.packet, self.suite)
        self.assertEqual(tuple(payload), validator.EXPECTED_ALLOWED_FIELDS)
        self.assertNotIn("known_intended_flaw_type", payload)
        self.assertNotIn("dataset_role", payload)
        self.assertNotIn("handling", payload)

    def test_nested_answer_key_is_rejected(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["llm_generated_qualitative_claim"]["target_flaw"] = "hidden"
        with self.assertRaisesRegex(
            validator.PromptSuiteError, "forbidden_field_in_projected_payload"
        ):
            validator.project_reviewer_payload(packet, self.suite)
        with self.assertRaisesRegex(
            ValueError, "forbidden_reviewer_payload_fields:target_flaw"
        ):
            working_runner.reviewer_payload(packet)

    def test_prompt_builder_has_no_model_argument_or_metadata_leak(self) -> None:
        prompt = validator.build_prompt(self.suite, "generalist", self.packet)
        self.assertNotIn("must_not_reach_prompt", prompt)
        self.assertIn("PKT_TESTONLY", prompt)
        self.assertIn("direction-j-shared-rating-v1", prompt)

    def test_working_runner_uses_only_v2_role_prompts(self) -> None:
        self.assertEqual(
            {role: path.name for role, path in working_runner.ROLE_PROMPTS.items()},
            {
                "generalist": "generalist_v2.md",
                "qualitative_methods": "qualitative_methods_v2.md",
                "domain": "domain_v2.md",
            },
        )
        payload = working_runner.reviewer_payload(self.packet)
        self.assertEqual(tuple(payload), validator.EXPECTED_ALLOWED_FIELDS)
        self.assertNotIn("known_intended_flaw_type", payload)


if __name__ == "__main__":
    unittest.main()
