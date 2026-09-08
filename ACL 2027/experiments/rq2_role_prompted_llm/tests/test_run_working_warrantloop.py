#!/usr/bin/env python3
"""Tests for the development-only WarrantLoop offline replay."""

from __future__ import annotations

import importlib.util
import inspect
import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments/rq2_role_prompted_llm/scripts"
SCRIPT = SCRIPT_DIR / "run_working_warrantloop.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("run_working_warrantloop_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_projection() -> dict[str, float]:
    return {
        name: 1.0 if name == "valid_generalist" else 0.0
        for name in MODULE.RATING_FEATURE_ORDER
    }


def constant_transition(improvement: float, harm: float) -> dict:
    return {
        "feature_order": [],
        "improvement_model": {"kind": "constant", "probability": improvement},
        "harm_model": {"kind": "constant", "probability": harm},
    }


class WorkingWarrantLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(
            (
                ROOT
                / "experiments/rq2_role_prompted_llm/config/working_warrantloop_v0_policy.json"
            ).read_text(encoding="utf-8")
        )
        cls.gate_policy = json.loads(
            (
                ROOT
                / "experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json"
            ).read_text(encoding="utf-8")
        )
        cls.cascade_config = json.loads(
            (
                ROOT
                / "experiments/rq2_role_prompted_llm/config/working_warrantloop_calibrated_cascade_v1_policy.json"
            ).read_text(encoding="utf-8")
        )
        cls.breakpoint_config = json.loads(
            (
                ROOT
                / "experiments/rq2_role_prompted_llm/config/working_warrantloop_calibrated_cascade_v2_policy.json"
            ).read_text(encoding="utf-8")
        )

    def test_logistic_pair_learns_ordered_probabilities(self) -> None:
        examples = [{"x": 0.0}] * 20 + [{"x": 1.0}] * 20
        labels = [0] * 20 + [1] * 20
        model = MODULE.fit_binary_logistic(
            examples, labels, ["x"], self.config["estimator"]
        )
        self.assertEqual(model["kind"], "logistic")
        self.assertLess(
            MODULE.predict_binary(model, {"x": 0.0}),
            MODULE.predict_binary(model, {"x": 1.0}),
        )

    def test_constant_target_uses_smoothed_probability(self) -> None:
        model = MODULE.fit_binary_logistic(
            [{"x": 0.0}] * 8,
            [0] * 8,
            ["x"],
            self.config["estimator"],
        )
        self.assertEqual(model["kind"], "constant")
        self.assertAlmostEqual(model["probability"], 0.1)

    def test_rare_event_uses_declared_constant_fallback(self) -> None:
        model = MODULE.fit_binary_logistic(
            [{"x": float(index % 2)} for index in range(20)],
            [1] + [0] * 19,
            ["x"],
            self.config["estimator"],
        )
        self.assertEqual(model["kind"], "constant")
        self.assertEqual(model["fallback_reason"], "minimum_class_count_not_met")

    def test_controller_acquires_one_specialist_then_stops(self) -> None:
        models = {
            "GM": constant_transition(0.9, 0.1),
            "GD": constant_transition(0.2, 0.1),
            "GB": constant_transition(0.2, 0.1),
            "MB": constant_transition(0.05, 0.0),
            "DB": constant_transition(0.05, 0.0),
        }
        packet_features = {name: 0.0 for name in MODULE.SOURCE_FEATURE_ORDER}
        projections = {role: valid_projection() for role in MODULE.ROLES}
        route = MODULE.route_packet(
            "PKT_TEST",
            "model:test",
            packet_features,
            projections,
            models,
            0.0,
            self.config,
            self.gate_policy,
        )
        self.assertEqual(route["route"], "qualitative_methods")
        self.assertEqual(route["specialist_acquisitions"], 1)
        self.assertEqual([row["decision"] for row in route["trace"]], ["ACQUIRE_M", "STOP_M"])

    def test_controller_is_finite_when_both_are_acquired(self) -> None:
        models = {
            transition: constant_transition(0.9 if transition == "GB" else 0.1, 0.0)
            for transition in MODULE.TRANSITIONS
        }
        packet_features = {name: 0.0 for name in MODULE.SOURCE_FEATURE_ORDER}
        projections = {role: valid_projection() for role in MODULE.ROLES}
        route = MODULE.route_packet(
            "PKT_TEST",
            "model:test",
            packet_features,
            projections,
            models,
            0.0,
            self.config,
            self.gate_policy,
        )
        self.assertEqual(route["route"], "both")
        self.assertEqual(route["specialist_acquisitions"], 2)
        self.assertEqual(route["stop_reason"], "both_specialists_acquired")

    def test_split_is_balanced_and_nonoverlapping(self) -> None:
        packet_ids = [f"PKT_{index:03d}" for index in range(100)]
        split = MODULE.deterministic_split(packet_ids, self.config)
        self.assertEqual({name: len(ids) for name, ids in split.items()}, {
            "train": 75,
            "validation": 15,
            "smoke_test": 10,
        })
        self.assertEqual(len(set().union(*map(set, split.values()))), 100)

    def test_route_application_interface_cannot_accept_truth(self) -> None:
        self.assertNotIn("truth", inspect.signature(MODULE.route_packet).parameters)
        self.assertNotIn("truth", inspect.signature(MODULE.apply_policy).parameters)
        self.assertEqual(MODULE.forbidden_keys({"trace": [], "route": "generalist"}), set())
        self.assertEqual(
            MODULE.forbidden_keys({"trace": [{"known_intended_flaw_type": "x"}]}),
            {"known_intended_flaw_type"},
        )

    def test_nonconverged_logistic_blocks_completion(self) -> None:
        fitted = {
            "model_policies": {
                "model:test": {
                    "final_transition_models": {
                        "GM": {
                            "improvement_model": {
                                "kind": "logistic",
                                "converged": False,
                            },
                            "harm_model": {"kind": "constant"},
                        }
                    }
                }
            }
        }
        self.assertFalse(MODULE.all_estimators_converged(fitted))

    def test_cumulative_modes_always_retain_generalist(self) -> None:
        self.assertEqual(
            MODULE.roles_for_mode("qualitative_methods", True),
            ("generalist", "qualitative_methods"),
        )
        self.assertEqual(
            MODULE.roles_for_mode("domain", True),
            ("generalist", "domain"),
        )
        self.assertEqual(
            MODULE.roles_for_mode("both", True),
            ("generalist", "qualitative_methods", "domain"),
        )

    def test_cumulative_detection_cannot_erase_generalist_true_positive(self) -> None:
        rows = {
            "generalist": {
                "status": "valid",
                "rating": {"serious_error_flags": ["lost_negative_case"]},
            },
            "qualitative_methods": {
                "status": "valid",
                "rating": {"serious_error_flags": []},
            },
            "domain": {
                "status": "valid",
                "rating": {"serious_error_flags": []},
            },
        }
        self.assertTrue(
            MODULE.mode_detected(
                "qualitative_methods", rows, "lost_negative_case", True
            )
        )
        self.assertTrue(MODULE.mode_detected("both", rows, "lost_negative_case", True))

    def test_near_tied_transition_uses_declared_order(self) -> None:
        predictions = {
            "GM": {"net_value": 0.32},
            "GD": {"net_value": 0.32000000000000006},
            "GB": {"net_value": 0.1},
        }
        selected, tied = MODULE.select_transition(predictions, self.cascade_config)
        self.assertEqual(selected, "GM")
        self.assertEqual(tied, ["GM", "GD"])

    def test_validation_score_breakpoints_expand_threshold_grid(self) -> None:
        score = 0.456789
        tolerance = MODULE.routing_score_tolerance(self.cascade_config)
        boundary = score - tolerance
        candidates = MODULE.threshold_candidate_values(
            self.cascade_config, [score]
        )
        self.assertIn(boundary, candidates)
        self.assertIn(math.nextafter(boundary, -math.inf), candidates)
        self.assertGreater(len(candidates), len(self.cascade_config["threshold_selection"]["candidates"]))

    def test_threshold_boundary_prefers_stop_within_tolerance(self) -> None:
        self.assertFalse(
            MODULE.should_acquire(0.1000000005, 0.1, self.cascade_config)
        )
        self.assertTrue(MODULE.should_acquire(0.100000002, 0.1, self.cascade_config))

    def test_threshold_selection_maximizes_recall_inside_call_budget(self) -> None:
        candidates = [
            {
                "threshold": -0.1,
                "recall": 0.9,
                "mean_total_role_acquisitions": 2.0,
                "mean_incremental_cost": 1.0,
            },
            {
                "threshold": 0.0,
                "recall": 0.8,
                "mean_total_role_acquisitions": 1.7,
                "mean_incremental_cost": 0.7,
            },
            {
                "threshold": 0.1,
                "recall": 0.8,
                "mean_total_role_acquisitions": 1.4,
                "mean_incremental_cost": 0.4,
            },
        ]
        selected = MODULE.select_threshold_candidate(candidates, self.cascade_config)
        self.assertEqual(selected["threshold"], 0.1)

    def test_budgeted_config_has_no_acquisition_fallback_threshold(self) -> None:
        MODULE.validate_policy_config(self.cascade_config)
        invalid = json.loads(json.dumps(self.cascade_config))
        invalid["threshold_selection"]["candidates"] = [0.0, 0.4]
        with self.assertRaisesRegex(
            ValueError, "call_budget_requires_no_acquisition_fallback_threshold"
        ):
            MODULE.validate_policy_config(invalid)

    def test_breakpoint_search_represents_both_sides_of_decision_boundary(self) -> None:
        tolerance = MODULE.routing_score_tolerance(self.breakpoint_config)
        candidates = MODULE.threshold_candidate_values(
            self.breakpoint_config, [0.45]
        )
        boundary = 0.45 - tolerance
        lower = boundary - max(4.0 * MODULE.math.ulp(boundary), 1e-15)
        self.assertIn(boundary, candidates)
        self.assertIn(lower, candidates)
        self.assertFalse(
            MODULE.should_acquire(0.45, boundary, self.breakpoint_config)
        )
        self.assertTrue(
            MODULE.should_acquire(
                0.45,
                lower,
                self.breakpoint_config,
            )
        )

    def test_cascade_route_records_cumulative_roles_and_total_cost(self) -> None:
        models = {
            "GM": constant_transition(0.9, 0.0),
            "GD": constant_transition(0.1, 0.0),
            "GB": constant_transition(0.1, 0.0),
            "MB": constant_transition(0.0, 0.0),
            "DB": constant_transition(0.0, 0.0),
        }
        packet_features = {name: 0.0 for name in MODULE.SOURCE_FEATURE_ORDER}
        projections = {role: valid_projection() for role in MODULE.ROLES}
        route = MODULE.route_packet(
            "PKT_TEST",
            "model:test",
            packet_features,
            projections,
            models,
            0.0,
            self.cascade_config,
            self.gate_policy,
        )
        self.assertEqual(route["selected_roles"], ["generalist", "qualitative_methods"])
        self.assertEqual(route["total_role_acquisitions"], 2)
        self.assertEqual(route["total_role_cost"], 2.0)


if __name__ == "__main__":
    unittest.main()
