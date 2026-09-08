#!/usr/bin/env python3
"""Tests for working Table 3 detection scoring helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py"
SPEC = importlib.util.spec_from_file_location("score_working_detection_table_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def row(role: str, flags: list[str], requested_expertise: str = "none") -> dict:
    return {
        "packet_id": "PKT_1",
        "role": role,
        "model_id": "qwen3:8b",
        "status": "valid",
        "rating": {
            "requested_expertise": requested_expertise,
            "serious_error_flags": flags,
        },
    }


class ScoreWorkingDetectionTableTests(unittest.TestCase):
    def test_fixed_role_is_one_shared_role(self) -> None:
        self.assertEqual(MODULE.SHARED_FIXED_ROLE, "qualitative_methods")

    def test_warrantroute_uses_generalist_for_none(self) -> None:
        outputs = {
            ("qwen3:8b", "generalist", "PKT_1"): row(
                "generalist", ["unsupported_inference"], "none"
            ),
            ("qwen3:8b", "qualitative_methods", "PKT_1"): row(
                "qualitative_methods", ["lost_negative_case"]
            ),
            ("qwen3:8b", "domain", "PKT_1"): row(
                "domain", ["contextual_flattening"]
            ),
        }
        route, selected_roles, flags, status = MODULE.routed_flags(
            outputs, {}, "qwen3:8b", "PKT_1"
        )
        self.assertEqual(route, "none")
        self.assertEqual(selected_roles, "generalist")
        self.assertEqual(flags, {"unsupported_inference"})
        self.assertEqual(status, "generalist_requested_expertise_proxy;generalist:valid")

    def test_warrantroute_maps_specialist_routes(self) -> None:
        for requested, expected_flags in [
            ("qualitative_methods", {"lost_negative_case"}),
            ("domain", {"contextual_flattening"}),
            ("both", {"lost_negative_case", "contextual_flattening"}),
        ]:
            with self.subTest(requested=requested):
                outputs = {
                    ("qwen3:8b", "generalist", "PKT_1"): row(
                        "generalist", ["unsupported_inference"], requested
                    ),
                    ("qwen3:8b", "qualitative_methods", "PKT_1"): row(
                        "qualitative_methods", ["lost_negative_case"]
                    ),
                    ("qwen3:8b", "domain", "PKT_1"): row(
                        "domain", ["contextual_flattening"]
                    ),
                }
                route, selected_roles, flags, status = MODULE.routed_flags(
                    outputs, {}, "qwen3:8b", "PKT_1"
                )
                self.assertEqual(route, requested)
                self.assertEqual(
                    selected_roles,
                    {
                        "qualitative_methods": "qualitative_methods",
                        "domain": "domain",
                        "both": "qualitative_methods;domain",
                    }[requested],
                )
                self.assertEqual(flags, expected_flags)
                self.assertIn("generalist:valid", status)

    def test_invalid_generalist_route_falls_back_to_none_proxy(self) -> None:
        outputs = {
            ("qwen3:8b", "generalist", "PKT_1"): {
                **row("generalist", ["unsupported_inference"], "domain"),
                "status": "schema_warning",
            },
            ("qwen3:8b", "domain", "PKT_1"): row(
                "domain", ["contextual_flattening"]
            ),
        }
        route, selected_roles, flags, status = MODULE.routed_flags(
            outputs, {}, "qwen3:8b", "PKT_1"
        )
        self.assertEqual(route, "domain")
        self.assertEqual(selected_roles, "domain")
        self.assertEqual(flags, {"contextual_flattening"})
        self.assertEqual(
            status,
            "generalist_requested_expertise_proxy;generalist:schema_warning;domain:valid",
        )

    def test_warrantgate_route_records_override_proxy(self) -> None:
        outputs = {
            ("qwen3:8b", "generalist", "PKT_1"): row(
                "generalist", ["unsupported_inference"], "none"
            ),
            ("qwen3:8b", "qualitative_methods", "PKT_1"): row(
                "qualitative_methods", ["lost_negative_case"]
            ),
        }
        routes = {
            ("qwen3:8b", "PKT_1"): {
                "policy_id": "working_warrantgate_v0",
                "route": "qualitative_methods",
            }
        }
        route, selected_roles, flags, status = MODULE.routed_flags(
            outputs, routes, "qwen3:8b", "PKT_1"
        )
        self.assertEqual(route, "qualitative_methods")
        self.assertEqual(selected_roles, "qualitative_methods")
        self.assertEqual(flags, {"lost_negative_case"})
        self.assertEqual(
            status,
            "working_warrantgate_v0;generalist:valid;qualitative_methods:valid",
        )

    def test_adaptive_route_records_can_select_domain(self) -> None:
        outputs = {
            ("qwen3:8b", "generalist", "PKT_1"): row(
                "generalist", ["unsupported_inference"], "none"
            ),
            ("qwen3:8b", "domain", "PKT_1"): row(
                "domain", ["contextual_flattening"]
            ),
        }
        adaptive_routes = {
            ("qwen3:8b", "PKT_1"): {
                "policy_id": "working_warrantgate_adaptive_v0",
                "route": "domain",
                "segment_routes": [{"segment_id": "seg_1", "route": "domain"}],
            }
        }
        route, selected_roles, flags, status = MODULE.routed_flags(
            outputs, adaptive_routes, "qwen3:8b", "PKT_1"
        )
        self.assertEqual(route, "domain")
        self.assertEqual(selected_roles, "domain")
        self.assertEqual(flags, {"contextual_flattening"})
        self.assertEqual(
            status,
            "working_warrantgate_adaptive_v0;generalist:valid;domain:valid",
        )


if __name__ == "__main__":
    unittest.main()
