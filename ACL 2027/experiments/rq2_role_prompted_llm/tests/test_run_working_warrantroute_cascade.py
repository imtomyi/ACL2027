#!/usr/bin/env python3
"""Tests for cumulative replay of frozen WarrantRoute-S decisions."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments/rq2_role_prompted_llm/scripts"
SCRIPT = SCRIPT_DIR / "run_working_warrantroute_cascade.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("cascade_replay_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CascadeReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "experiment_id": "test_cascade",
            "router_name": "test-router",
            "paper_facing_name": "test-cascade",
            "internal_variant_id": "cumulative_output_v1",
        }

    def source_route(self, route: str, specialists: list[str]) -> dict:
        return {
            "route": route,
            "packet_id": "PKT_TEST",
            "policy_id": "source-policy",
            "fitted_policy_sha256": "abc",
            "acquired_specialists": specialists,
            "specialist_acquisitions": len(specialists),
            "total_role_acquisitions": 1 + len(specialists),
            "incremental_cost": float(len(specialists)),
        }

    def test_specialist_route_retains_generalist_without_new_call(self) -> None:
        source = self.source_route("domain", ["domain"])
        replay = MODULE.cascade_route(source, self.config)
        self.assertEqual(replay["selected_roles"], ["generalist", "domain"])
        self.assertEqual(replay["total_role_acquisitions"], 2)
        self.assertEqual(replay["acquired_specialists"], ["domain"])

    def test_both_route_uses_canonical_cumulative_union(self) -> None:
        source = self.source_route(
            "both", ["domain", "qualitative_methods"]
        )
        replay = MODULE.cascade_route(source, self.config)
        self.assertEqual(
            replay["selected_roles"],
            ["generalist", "qualitative_methods", "domain"],
        )

    def test_mismatched_source_route_fails_closed(self) -> None:
        source = self.source_route("domain", ["qualitative_methods"])
        with self.assertRaisesRegex(ValueError, "source_route_specialist_mismatch"):
            MODULE.cascade_route(source, self.config)

    def test_revised_table_replaces_warrantroute_without_adding_a_row(self) -> None:
        original = [
            {
                "Dataset": "Dreaddit",
                "Method": "WarrantRoute",
                "Model": "Gemma 3 4B",
                "TP/N": "1/100",
                "Recall (%) ↑": "1.0",
            },
            {
                "Dataset": "Dreaddit",
                "Method": "Generalist",
                "Model": "Gemma 3 4B",
                "TP/N": "2/100",
                "Recall (%) ↑": "2.0",
            },
        ]
        metrics = [
            {
                "dataset": "Dreaddit",
                "model_id": "gemma3:4b",
                "tp": 3,
                "n": 100,
                "recall": 0.03,
                "recall_wilson_95_low": 0.01,
                "recall_wilson_95_high": 0.08,
            }
        ]
        revised = MODULE.build_revised_table(original, metrics)
        self.assertEqual(len(revised), len(original))
        self.assertEqual(revised[0]["Method"], "WarrantRoute")
        self.assertEqual(revised[0]["TP/N"], "3/100")
        self.assertEqual(revised[1], original[1])


if __name__ == "__main__":
    unittest.main()
