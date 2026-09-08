#!/usr/bin/env python3
"""Tests for the working WarrantGate route builder."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/build_working_warrantgate_routes.py"
POLICY = ROOT / "experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json"
SPEC = importlib.util.spec_from_file_location("build_working_warrantgate_routes_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def rating_row(
    *,
    evidential: int = 5,
    voice: int = 5,
    scope: int = 5,
    confidence: int = 5,
    disposition: str = "accept",
    flags: list[str] | None = None,
    requested: str = "none",
) -> dict:
    return {
        "status": "valid",
        "rating": {
            "evidential_credibility": evidential,
            "voice_boundary_preservation": voice,
            "scope_calibration": scope,
            "confidence": confidence,
            "disposition": disposition,
            "cannot_judge": [],
            "serious_error_flags": flags or [],
            "requested_expertise": requested,
        },
    }


class BuildWorkingWarrantGateRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_accept_high_confidence_routes_to_generalist(self) -> None:
        features = {
            **{
                "source_concentration_signal": 0.0,
                "low_cited_source_count": 0.0,
                "speaker_or_turn_context": 0.0,
            },
            **MODULE.rating_features(rating_row()),
        }
        _components, scores = MODULE.route_scores(features, self.policy)
        self.assertEqual(MODULE.choose_route(scores, self.policy["tie_order"]), "generalist")

    def test_method_signal_routes_to_qualitative_methods(self) -> None:
        features = {
            **{
                "source_concentration_signal": 1.0,
                "low_cited_source_count": 1.0,
                "speaker_or_turn_context": 0.0,
            },
            **MODULE.rating_features(
                rating_row(
                    evidential=2,
                    scope=2,
                    confidence=3,
                    disposition="revise",
                    flags=["hidden_source_concentration"],
                    requested="qualitative_methods",
                )
            ),
        }
        _components, scores = MODULE.route_scores(features, self.policy)
        self.assertEqual(
            MODULE.choose_route(scores, self.policy["tie_order"]),
            "qualitative_methods",
        )

    def test_joint_method_domain_signal_routes_to_both(self) -> None:
        features = {
            **{
                "source_concentration_signal": 1.0,
                "low_cited_source_count": 1.0,
                "speaker_or_turn_context": 1.0,
            },
            **MODULE.rating_features(
                rating_row(
                    evidential=2,
                    voice=1,
                    scope=2,
                    confidence=2,
                    disposition="escalate",
                    flags=["unsupported_inference", "contextual_flattening"],
                    requested="both",
                )
            ),
        }
        _components, scores = MODULE.route_scores(features, self.policy)
        self.assertEqual(MODULE.choose_route(scores, self.policy["tie_order"]), "both")


if __name__ == "__main__":
    unittest.main()
