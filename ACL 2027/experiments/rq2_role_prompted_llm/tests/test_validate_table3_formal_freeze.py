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

import validate_table3_formal_freeze as preflight  # noqa: E402


class Table3FormalFreezePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template_path = (
            RQ2_ROOT / "config/table3_formal_full_matrix_v1.template.json"
        )
        cls.template = json.loads(template_path.read_text(encoding="utf-8"))

    def test_template_covers_complete_table3_matrix(self) -> None:
        report = preflight.build_report(copy.deepcopy(self.template))
        self.assertEqual(report["dataset_count"], 4)
        self.assertEqual(report["method_count"], 4)
        self.assertEqual(report["model_count"], 3)
        self.assertEqual(report["role_count"], 3)
        self.assertEqual(report["repetition_count"], 3)
        self.assertEqual(report["expected_reviewer_outputs_per_repetition"], 3600)
        self.assertEqual(report["expected_total_reviewer_outputs"], 10800)
        self.assertEqual(report["expected_table_rows"], 48)

    def test_incomplete_template_fails_closed_without_model_calls(self) -> None:
        report = preflight.build_report(copy.deepcopy(self.template))
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["formal_execution_allowed"])
        self.assertFalse(report["corpus_payload_parsed"])
        self.assertEqual(report["reviewer_calls_made"], 0)
        self.assertIn("execution_not_authorized", report["blocking_reason_codes"])
        self.assertIn(
            "governance_readiness_report_reference_missing_or_outside_workspace",
            report["blocking_reason_codes"],
        )
        self.assertIn(
            "goemotions_final_packet_manifest_reference_missing_or_outside_workspace",
            report["blocking_reason_codes"],
        )
        self.assertIn(
            "parlamint_gb_final_packet_manifest_reference_missing_or_outside_workspace",
            report["blocking_reason_codes"],
        )
        self.assertIn(
            "warrantroute_composition_not_frozen",
            report["blocking_reason_codes"],
        )

    def test_authorization_booleans_cannot_bypass_missing_evidence(self) -> None:
        freeze = copy.deepcopy(self.template)
        freeze["record_status"] = "formal_study_frozen"
        freeze["study_id"] = "table3-test"
        freeze["frozen_at_utc"] = "2026-09-02T00:00:00Z"
        freeze["frozen_by"] = "OWNER_TESTONLY"
        freeze["execution_authorized"] = True
        report = preflight.build_report(freeze)
        self.assertFalse(report["formal_execution_allowed"])
        self.assertGreater(report["blocking_reason_count"], 0)
        self.assertIn(
            "governance_readiness_report_reference_missing_or_outside_workspace",
            report["blocking_reason_codes"],
        )

    def test_output_count_drift_is_malformed(self) -> None:
        freeze = copy.deepcopy(self.template)
        freeze["scope"]["expected_total_reviewer_outputs"] = 3600
        with self.assertRaisesRegex(preflight.FreezeError, "total_output_count_drift"):
            preflight.build_report(freeze)

    def test_baseline_phase_defers_only_warrantroute_requirements(self) -> None:
        report = preflight.build_report(
            copy.deepcopy(self.template), phase="baseline"
        )
        self.assertEqual(report["phase"], "baseline")
        self.assertEqual(report["method_count"], 3)
        self.assertEqual(report["expected_table_rows"], 36)
        self.assertEqual(report["expected_total_reviewer_outputs"], 10800)
        self.assertNotIn(
            "warrantroute_composition_not_frozen",
            report["blocking_reason_codes"],
        )
        self.assertIn(
            "dreaddit_final_packet_manifest_reference_missing_or_outside_workspace",
            report["blocking_reason_codes"],
        )

    def test_fixed_role_is_shared_across_all_models(self) -> None:
        fixed = self.template["methods"]["fixed_role"]
        self.assertEqual(fixed["shared_frozen_role"], "qualitative_methods")
        self.assertEqual(
            set(fixed["frozen_role_by_model"].values()), {"qualitative_methods"}
        )
        report = preflight.build_report(copy.deepcopy(self.template), phase="baseline")
        self.assertNotIn(
            "fixed_role_selection_boundary_invalid", report["blocking_reason_codes"]
        )

    def test_model_specific_fixed_role_is_rejected(self) -> None:
        freeze = copy.deepcopy(self.template)
        freeze["methods"]["fixed_role"]["frozen_role_by_model"][
            "llama3_1_8b"
        ] = "domain"
        report = preflight.build_report(freeze, phase="baseline")
        self.assertIn(
            "fixed_role_llama3_1_8b_not_shared", report["blocking_reason_codes"]
        )


if __name__ == "__main__":
    unittest.main()
