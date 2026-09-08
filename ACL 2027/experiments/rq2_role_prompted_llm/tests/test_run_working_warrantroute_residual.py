#!/usr/bin/env python3
"""Tests for the WarrantRoute residual discovery working replay."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments/rq2_role_prompted_llm/scripts"
SCRIPT = SCRIPT_DIR / "run_working_warrantroute_residual.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("residual_route_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ResidualRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = {
            "kind": "hashed_bernoulli_naive_bayes",
            "feature_dimension": 128,
            "alpha": 1.0,
            "hash_salt": "test-salt",
        }
        self.residual_policy = {
            "maximum_addition_rate": 0.35,
            "threshold_tie_action": "do_not_add",
            "score_tolerance": 1e-12,
        }

    @staticmethod
    def packet(packet_id: str, word: str, answer: str) -> dict:
        return {
            "packet_id": packet_id,
            "known_intended_flaw_type": answer,
            "known_intended_flaw_note": f"answer is {answer}",
            "review_instruction": f"find {answer}",
            "llm_generated_qualitative_claim": {
                "claim": f"A {word} claim",
                "explanation": f"The evidence is {word}",
                "theme_name": "test theme",
                "boundary_conditions": [f"Except when {word}"],
            },
            "source_text_context": [
                {
                    "source_id": f"source-{packet_id}",
                    "text": f"A source discusses {word}",
                    "local_context": None,
                }
            ],
        }

    def test_answer_and_instruction_fields_never_enter_features(self) -> None:
        original = self.packet("p1", "orchid", "unsupported_evidence")
        changed = dict(original)
        changed["known_intended_flaw_type"] = "contextual_flattening"
        changed["known_intended_flaw_note"] = "different private answer"
        changed["review_instruction"] = "different instruction"
        self.assertEqual(
            MODULE.feature_strings(original), MODULE.feature_strings(changed)
        )
        self.assertEqual(
            MODULE.hashed_features(original, self.classifier),
            MODULE.hashed_features(changed, self.classifier),
        )

    def test_classifier_learns_separable_safe_text(self) -> None:
        labels = sorted(MODULE.core.TARGET_TO_FLAG)
        words = {
            label: f"marker{index}" for index, label in enumerate(labels)
        }
        packets = {}
        truth = {}
        for label in labels:
            for index in range(4):
                packet_id = f"{label}-{index}"
                packets[packet_id] = self.packet(packet_id, words[label], label)
                truth[packet_id] = label
        model = MODULE.fit_hashed_bernoulli_nb(
            packets, truth, packets.keys(), self.classifier
        )
        for label in labels:
            test = self.packet(f"test-{label}", words[label], "wrong-private-answer")
            prediction = MODULE.predict_hashed_bernoulli_nb(model, test)
            self.assertEqual(prediction["predicted_flaw_type"], label)
        self.assertFalse(model["stores_source_text_or_vocabulary"])

    def test_threshold_tie_is_not_eligible(self) -> None:
        inputs = {
            "role_rows": {
                ("m", "generalist", "p1"): {
                    "status": "valid",
                    "rating": {"serious_error_flags": []},
                }
            }
        }
        routes = [
            {
                "model_id": "m",
                "packet_id": "p1",
                "selected_roles": ["generalist"],
            }
        ]
        predictions = {
            "p1": {"probability": 0.8, "predicted_flag": "unsupported_inference"}
        }
        selected = MODULE.select_residual_keys(
            routes,
            predictions,
            inputs,
            0.8,
            {**self.residual_policy, "maximum_addition_rate": 1.0},
            "tie-seed",
        )
        self.assertEqual(selected, set())

    def test_batch_budget_caps_additions(self) -> None:
        role_rows = {}
        routes = []
        predictions = {}
        for index in range(10):
            packet_id = f"p{index}"
            role_rows[("m", "generalist", packet_id)] = {
                "status": "valid",
                "rating": {"serious_error_flags": []},
            }
            routes.append(
                {
                    "model_id": "m",
                    "packet_id": packet_id,
                    "selected_roles": ["generalist"],
                }
            )
            predictions[packet_id] = {
                "probability": 0.99 - index / 100,
                "predicted_flag": "unsupported_inference",
            }
        selected = MODULE.select_residual_keys(
            routes,
            predictions,
            {"role_rows": role_rows},
            -1.0,
            self.residual_policy,
            "budget-seed",
        )
        self.assertEqual(len(selected), 3)

    def test_residual_route_preserves_role_call_cost(self) -> None:
        source = {
            "dataset": "Dreaddit",
            "model_id": "m",
            "packet_id": "p1",
            "route": "domain",
            "selected_roles": ["generalist", "domain"],
            "acquired_specialists": ["domain"],
            "total_role_acquisitions": 2,
            "policy_id": "base",
            "fitted_policy_sha256": "base-hash",
        }
        config = {
            "experiment_id": "test-residual",
            "router_name": "WarrantRoute",
            "paper_facing_name": "WarrantRoute",
            "internal_variant_id": "residual_discovery_v1",
        }
        route = MODULE.make_residual_route(
            source,
            {"predicted_flag": "unsupported_inference", "probability": 0.9},
            True,
            0.8,
            "residual-hash",
            config,
        )
        self.assertEqual(route["total_role_acquisitions"], 2)
        self.assertEqual(route["selected_roles"], ["generalist", "domain"])
        self.assertTrue(route["residual_added"])
        self.assertFalse(route["new_llm_call"])
        self.assertTrue(route["uses_source_text_classifier"])
        self.assertEqual(route["residual_threshold"], 0.8)

    def test_shortcut_quarantine_detects_label_coded_claim_templates(self) -> None:
        packets = {}
        truth = {}
        labels = sorted(MODULE.core.TARGET_TO_FLAG)
        for label in labels:
            for index in range(3):
                packet_id = f"{label}-{index}"
                packets[packet_id] = self.packet(packet_id, f"coded-{label}", label)
                truth[packet_id] = label
        config = {
            "shortcut_quarantine": {
                "audit_fields": ["llm_generated_qualitative_claim.claim"],
                "deterministic_purity_threshold": 0.99,
                "maximum_unique_value_fraction": 0.05,
                "maximum_unique_value_floor": 20,
            }
        }
        audit = MODULE.audit_deterministic_shortcuts(packets, truth, config)
        self.assertTrue(audit["deterministic_shortcut_detected"])
        self.assertFalse(audit["scientific_interpretation_gate_passed"])
        self.assertFalse(audit["fields"][0]["raw_values_stored"])

    def test_matched_comparator_uses_all_roles_and_same_residual_head(self) -> None:
        role_rows = {
            ("m", role, "p1"): {
                "status": "valid",
                "rating": {"serious_error_flags": []},
            }
            for role in MODULE.core.ROLES
        }
        source = {
            "dataset": "CaChe",
            "model_id": "m",
            "packet_id": "p1",
            "route": "generalist",
            "selected_roles": ["generalist"],
            "acquired_specialists": [],
            "specialist_acquisitions": 0,
            "total_role_acquisitions": 1,
            "incremental_cost": 0.0,
            "total_role_cost": 1.0,
            "residual_candidate_flag": "unsupported_inference",
            "residual_candidate_probability": 0.9,
            "residual_threshold": 0.5,
            "residual_added": True,
            "residual_additions": 1,
        }
        config = {
            "batch_tie_seed": "matched-test",
            "residual_policy": {
                **self.residual_policy,
                "maximum_addition_rate": 1.0,
            },
        }
        rows = MODULE.build_matched_all_roles_residual_routes(
            [source], {"CaChe": {"role_rows": role_rows}}, config
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["selected_roles"], list(MODULE.core.ROLES))
        self.assertEqual(rows[0]["total_role_acquisitions"], 3)
        self.assertTrue(rows[0]["residual_added"])
        self.assertEqual(
            rows[0]["residual_candidate_flag"], source["residual_candidate_flag"]
        )


if __name__ == "__main__":
    unittest.main()
