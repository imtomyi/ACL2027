#!/usr/bin/env python3
"""Tests for the four-corpus WarrantLoop working replay."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments/rq2_role_prompted_llm/scripts"
SCRIPT = SCRIPT_DIR / "run_working_warrantloop_multicorpus.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "run_working_warrantloop_multicorpus_tests", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkingWarrantLoopMulticorpusTests(unittest.TestCase):
    def test_outer_folds_cover_each_packet_once(self) -> None:
        packet_ids = [f"PKT_{index:03d}" for index in range(100)]
        folds = MODULE.assign_outer_folds(packet_ids, 5, "seed")
        self.assertEqual([len(folds[index]) for index in range(5)], [20] * 5)
        flattened = [packet_id for ids in folds.values() for packet_id in ids]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(set(flattened), set(packet_ids))

    def test_inner_split_has_expected_inventory(self) -> None:
        packet_ids = [f"PKT_{index:03d}" for index in range(80)]
        train, validation = MODULE.inner_split(packet_ids, 0.2, "seed")
        self.assertEqual((len(train), len(validation)), (64, 16))
        self.assertFalse(set(train) & set(validation))
        self.assertEqual(set(train) | set(validation), set(packet_ids))

    def test_source_overlap_between_outer_folds_is_rejected(self) -> None:
        inputs = {
            "source_groups": {
                "PKT_A": frozenset({"SRC_SHARED"}),
                "PKT_B": frozenset({"SRC_SHARED"}),
            }
        }
        with self.assertRaisesRegex(ValueError, "outer_fold_source_overlap"):
            MODULE.validate_fold_source_separation(inputs, {0: ["PKT_A"], 1: ["PKT_B"]})

    def test_combined_table_adds_twelve_rows_without_mutating_original(self) -> None:
        datasets = ["Dreaddit", "GoEmotion", "CaChe", "ParlaMint-GB"]
        original = []
        for dataset in datasets:
            for method in ["Generalist", "Fixed role", "All roles", "WarrantRoute"]:
                for model in MODULE.MODEL_DISPLAY_ORDER:
                    original.append(
                        {
                            "Dataset": dataset,
                            "Method": method,
                            "Model": model,
                            "TP/N": "1/100",
                            "Recall (%) ↑": "1.0 [0.2, 5.4]",
                        }
                    )
        original_snapshot = [dict(row) for row in original]
        metrics = []
        reverse_model = {value: key for key, value in MODULE.MODEL_DISPLAY.items()}
        for dataset in datasets:
            for model in MODULE.MODEL_DISPLAY_ORDER:
                metrics.append(
                    {
                        "dataset": dataset,
                        "model_id": reverse_model[model],
                        "tp": 2,
                        "n": 100,
                        "recall": 0.02,
                        "recall_wilson_95_low": 0.0055,
                        "recall_wilson_95_high": 0.0700,
                    }
                )
        combined = MODULE.build_comparison_rows(original, metrics, datasets)
        self.assertEqual(len(combined), 60)
        self.assertEqual(sum(row["Method"] == "WarrantRoute-S" for row in combined), 12)
        self.assertEqual(original, original_snapshot)

    def test_candidate_monotonicity_check_rejects_generalist_regression(self) -> None:
        comparison = [
            {
                "Dataset": "Dreaddit",
                "Method": "Generalist",
                "Model": "Gemma 3 4B",
                "TP/N": "5/10",
                "Recall (%) ↑": "50.0",
            }
        ]
        metric = [
            {
                "dataset": "Dreaddit",
                "model_id": "gemma3:4b",
                "tp": 4,
                "n": 10,
            }
        ]
        self.assertFalse(MODULE.candidate_not_below_generalist(comparison, metric))
        metric[0]["tp"] = 5
        self.assertTrue(MODULE.candidate_not_below_generalist(comparison, metric))

    def test_selected_threshold_budget_audit(self) -> None:
        policy_config = {
            "threshold_selection": {
                "objective": "maximum_validation_recall_subject_to_mean_total_role_acquisitions_budget",
                "maximum_mean_total_role_acquisitions": 1.75,
                "budget_tolerance": 1e-12,
            }
        }
        policy = {
            "model_policies": {
                "model:test": {
                    "selected_threshold": 0.1,
                    "threshold_candidates": [
                        {
                            "threshold": 0.1,
                            "mean_total_role_acquisitions": 1.7,
                        }
                    ],
                }
            }
        }
        self.assertTrue(
            MODULE.selected_thresholds_respect_budget([policy], policy_config)
        )
        policy["model_policies"]["model:test"]["threshold_candidates"][0][
            "mean_total_role_acquisitions"
        ] = 1.8
        self.assertFalse(
            MODULE.selected_thresholds_respect_budget([policy], policy_config)
        )


if __name__ == "__main__":
    unittest.main()
