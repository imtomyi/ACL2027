#!/usr/bin/env python3
"""Source-free tests for the private one-packet v2.4 smoke runner."""

from __future__ import annotations

import copy
import importlib.util
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_personal_local_real_smoke_v24.py"
SPEC = importlib.util.spec_from_file_location("rq2_real_smoke_v24_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
v24 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v24
SPEC.loader.exec_module(v24)


def constructed_output() -> dict:
    return {
        "generation_schema_version": "rq2-base-generation-v2.1",
        "status": "constructed",
        "theme_name": "Bounded theme",
        "claim": "A packet-bounded claim",
        "explanation": "A bounded explanation",
        "claim_scope": "displayed_packet_only",
        "role_plan": [
            {"position": 1, "role": "support"},
            {"position": 2, "role": "support"},
            {"position": 3, "role": "counterevidence"},
            {"position": 4, "role": "context_only"},
            {"position": 5, "role": "context_only"},
            {"position": 6, "role": "context_only"},
        ],
        "boundary_conditions": [
            {"counter_position": 3, "text": "A bounded condition"}
        ],
        "reason_codes": [],
    }


class V24StaticBoundaryTests(unittest.TestCase):
    def test_static_validation_opens_no_records_or_service(self):
        config = v24.v1.load_json(v24.DEFAULT_CONFIG)
        with (
            mock.patch.object(
                v24.v1,
                "load_bound_records",
                side_effect=AssertionError("records opened"),
            ),
            mock.patch.object(
                v24.v1,
                "preflight_service",
                side_effect=AssertionError("service contacted"),
            ),
            mock.patch.object(
                v24.v1,
                "run_exact_policy_validator",
                side_effect=AssertionError("policy validator executed"),
            ),
            mock.patch.object(
                v24.v1,
                "api_json",
                side_effect=AssertionError("service contacted"),
            ),
        ):
            _, _ = v24.validate_v24_freeze(
                config, config_path=v24.DEFAULT_CONFIG
            )
            summary = v24.static_summary(config)
        self.assertEqual(summary["v24_static_status"], "passed")
        self.assertFalse(summary["data_opened"])
        self.assertFalse(summary["storage_opened"])
        self.assertFalse(summary["service_contacted"])

    def test_real_scope_is_one_atomic_packet(self):
        config = v24.v1.load_json(v24.DEFAULT_CONFIG)
        self.assertEqual(config["input"]["packet_count"], 1)
        self.assertEqual(config["input"]["excerpts_per_packet"], 6)
        self.assertEqual(config["input"]["smoke_selection_rank"], 11)
        self.assertFalse(config["process"]["real_packet_chunking_allowed"])
        self.assertEqual(config["prompt_limit_policy"]["request_num_ctx"], 16384)
        self.assertIs(config["prompt_limit_policy"]["truncate"], False)
        self.assertIs(config["prompt_limit_policy"]["shift"], False)

    def test_runner_does_not_use_unsafe_checkpoint_or_chunk_helpers(self):
        source = inspect.getsource(v24.execute)
        self.assertNotIn("invoke_checkpointed_call", source)
        self.assertNotIn("run_base_phase_v2", source)
        self.assertNotIn("run_base_interface_phase_v22", source)
        self.assertNotIn("split_utf8_exact", source)
        self.assertNotIn("build_chunk_plan", source)
        hardened = inspect.getsource(v24.invoke_hardened_call)
        self.assertIn("harden_ollama_request", hardened)
        self.assertIn('execution.get("done_reason") == "stop"', hardened)

    def test_nondefault_config_is_rejected_before_open(self):
        with (
            mock.patch.object(
                sys,
                "argv",
                [str(SCRIPT), "--config", "/tmp/not-the-freeze.json", "dry-run"],
            ),
            mock.patch.object(
                v24.v1,
                "load_json",
                side_effect=AssertionError("nondefault config opened"),
            ),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(v24.main(), 2)


class GenerationConventionTests(unittest.TestCase):
    def test_constructed_conventions_pass(self):
        v24.validate_generation_cross_fields(constructed_output())

    def test_constructed_with_not_constructed_scope_is_rejected(self):
        value = constructed_output()
        value["claim_scope"] = "not_constructed"
        with self.assertRaisesRegex(v24.V24Error, "claim_scope_invalid"):
            v24.validate_generation_cross_fields(value)

    def test_constructed_with_reason_code_is_rejected(self):
        value = constructed_output()
        value["reason_codes"] = ["ambiguous_evidence_roles"]
        with self.assertRaisesRegex(v24.V24Error, "reason_codes_nonempty"):
            v24.validate_generation_cross_fields(value)

    def test_not_constructable_conventions_pass_and_contradictions_fail(self):
        value = constructed_output()
        value.update(
            {
                "status": "not_constructable",
                "theme_name": "NOT_CONSTRUCTED",
                "claim": "NOT_CONSTRUCTED",
                "explanation": "NOT_CONSTRUCTED",
                "claim_scope": "not_constructed",
                "role_plan": [
                    {"position": position, "role": "unassigned"}
                    for position in range(1, 7)
                ],
                "boundary_conditions": [],
                "reason_codes": ["ambiguous_evidence_roles"],
            }
        )
        v24.validate_generation_cross_fields(value)
        contradictory = copy.deepcopy(value)
        contradictory["boundary_conditions"] = [
            {"counter_position": 3, "text": "Contradiction"}
        ]
        with self.assertRaisesRegex(v24.V24Error, "boundaries_invalid"):
            v24.validate_generation_cross_fields(contradictory)


if __name__ == "__main__":
    unittest.main()
