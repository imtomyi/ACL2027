#!/usr/bin/env python3
"""Tests for the working adaptive WarrantGate route builder."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments/rq2_role_prompted_llm/scripts"
SCRIPT = SCRIPT_DIR / "build_working_warrantgate_adaptive_routes.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "build_working_warrantgate_adaptive_routes_tests", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def score_row(segment_id: str, scores: dict[str, float]) -> dict:
    return {
        "segment_id": segment_id,
        "segment_index": int(segment_id.rsplit("_", 1)[-1]),
        "components": {},
        "scores": scores,
        "features": {},
        "contains_source_text": False,
    }


class BuildWorkingWarrantGateAdaptiveRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = {
            "actions": ["generalist", "qualitative_methods", "domain", "both"],
            "switching": {
                "switch_penalty": 0.05,
                "switch_margin": 0.04,
                "minimum_dwell_segments": 1,
            },
            "packet_aggregation": {
                "generalist_only_route": "generalist",
                "method_only_route": "qualitative_methods",
                "domain_only_route": "domain",
                "method_and_domain_route": "both",
            },
        }

    def test_switches_when_new_mode_clearly_wins(self) -> None:
        routed = MODULE.choose_adaptive_sequence(
            [
                score_row(
                    "seg_0",
                    {
                        "generalist": 0.70,
                        "qualitative_methods": 0.20,
                        "domain": 0.15,
                        "both": 0.10,
                    },
                ),
                score_row(
                    "seg_1",
                    {
                        "generalist": 0.30,
                        "qualitative_methods": 0.85,
                        "domain": 0.20,
                        "both": 0.40,
                    },
                ),
            ],
            self.policy,
        )
        self.assertEqual([row["route"] for row in routed], ["generalist", "qualitative_methods"])
        self.assertTrue(routed[1]["changed_from_previous_segment"])

    def test_margin_blocks_noisy_switch(self) -> None:
        routed = MODULE.choose_adaptive_sequence(
            [
                score_row(
                    "seg_0",
                    {
                        "generalist": 0.70,
                        "qualitative_methods": 0.20,
                        "domain": 0.15,
                        "both": 0.10,
                    },
                ),
                score_row(
                    "seg_1",
                    {
                        "generalist": 0.70,
                        "qualitative_methods": 0.73,
                        "domain": 0.15,
                        "both": 0.10,
                    },
                ),
            ],
            self.policy,
        )
        self.assertEqual([row["route"] for row in routed], ["generalist", "generalist"])
        self.assertFalse(routed[1]["changed_from_previous_segment"])

    def test_segment_routes_collapse_to_both_when_needed(self) -> None:
        route = MODULE.aggregate_segment_routes(
            [
                {"route": "generalist"},
                {"route": "qualitative_methods"},
                {"route": "domain"},
            ],
            self.policy,
        )
        self.assertEqual(route, "both")

    def test_segment_adjustments_change_local_scores(self) -> None:
        base_policy = MODULE.load_json(
            ROOT / "experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json"
        )
        adaptive_policy = {
            "segment_adjustments": {
                "generalist_sufficiency": {},
                "method_need": {},
                "domain_need": {"segment_has_speaker": 1.0},
                "interaction": {},
            }
        }
        features = {
            "accept": 0.0,
            "high_confidence": 0.0,
            "no_cannot_judge": 1.0,
            "no_serious_flags": 1.0,
            "low_evidential_credibility": 0.0,
            "low_scope_calibration": 0.0,
            "low_voice_boundary": 0.0,
            "cannot_judge_present": 0.0,
            "method_flag": 0.0,
            "domain_flag": 0.0,
            "requested_method_or_both": 0.0,
            "requested_domain_or_both": 0.0,
            "requested_both": 0.0,
            "segment_has_speaker": 1.0,
        }
        components, scores = MODULE.segment_route_scores(
            features, base_policy, adaptive_policy
        )
        self.assertGreaterEqual(components["domain_need"], 1.0)
        self.assertGreater(scores["domain"], scores["generalist"])


if __name__ == "__main__":
    unittest.main()
