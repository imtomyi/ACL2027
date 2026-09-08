#!/usr/bin/env python3
"""Tests for the strict WarrantRoute Table 3 finalizer."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/finalize_table3_warrantroute.py"
SPEC = importlib.util.spec_from_file_location("finalize_table3_warrantroute_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_rows(dataset: str = "Dreaddit", sample_n: int = 100) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for method in MODULE.METHODS:
        for model in MODULE.MODELS:
            tp = 50
            rows.append(
                {
                    "Dataset": dataset,
                    "Method": method,
                    "Model": MODULE.MODEL_LABELS[model],
                    "TP/N": f"{tp}/{sample_n}",
                    "Recall (%) ↑": "50.0 [40.4, 59.6]",
                }
            )
    return rows


class FinalizeTable3WarrantRouteTests(unittest.TestCase):
    def test_valid_table_has_all_twelve_combinations(self) -> None:
        rows = valid_rows()
        self.assertEqual(
            MODULE.validate_table_rows(rows, dataset="Dreaddit", sample_n=100),
            rows,
        )

    def test_recall_must_match_tp_over_n(self) -> None:
        rows = valid_rows()
        rows[0]["Recall (%) ↑"] = "51.0 [40.4, 59.6]"
        with self.assertRaises(MODULE.IntegrityError):
            MODULE.validate_table_rows(rows, dataset="Dreaddit", sample_n=100)

    def test_duplicate_method_model_is_rejected(self) -> None:
        rows = valid_rows()
        rows[-1] = dict(rows[0])
        with self.assertRaises(MODULE.IntegrityError):
            MODULE.validate_table_rows(rows, dataset="Dreaddit", sample_n=100)

    def test_tie_order_prefers_generalist(self) -> None:
        scores = {
            "generalist": 0.5,
            "qualitative_methods": 0.5,
            "domain": 0.5,
            "both": 0.5,
        }
        self.assertEqual(
            MODULE.choose_route(
                scores,
                ["generalist", "qualitative_methods", "domain", "both"],
            ),
            "generalist",
        )

    def test_manuscript_rows_blank_repeated_labels_only(self) -> None:
        rows = valid_rows()
        display = MODULE.manuscript_rows(rows)
        self.assertEqual(display[0]["Dataset"], "Dreaddit")
        self.assertEqual(display[1]["Dataset"], "")
        self.assertEqual(display[0]["Method"], "Generalist")
        self.assertEqual(display[1]["Method"], "")
        self.assertEqual(display[3]["Method"], "Fixed role")


if __name__ == "__main__":
    unittest.main()

