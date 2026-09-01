#!/usr/bin/env python3
"""Source-free tests for the v2.1 compatibility adapter and canary."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CANARY_SCRIPT = ROOT / "scripts" / "run_personal_local_main_v21_canary.py"
SPEC = importlib.util.spec_from_file_location(
    "rq2_personal_local_main_v21_canary_tests", CANARY_SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
canary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(canary)
adapter = canary.adapter
core = canary.core


class V21CompatibilityTests(unittest.TestCase):
    def test_adapter_hash_verifies_frozen_v2_core_and_patches_only_entry_globals(self):
        self.assertEqual(adapter.raw_sha256(adapter.CORE_RUNNER), adapter.CORE_RUNNER_SHA256)
        self.assertEqual(
            adapter.CORE_RUNNER_SHA256,
            "7fbbafc74f3ad40b2041b054bb72ae84c66214c84ef882d0f3a08d21c00caa64",
        )
        self.assertEqual(core.DEFAULT_CONFIG, adapter.COMPAT_CONFIG)
        self.assertEqual(core.SCRIPT, adapter.SCRIPT)
        self.assertEqual(
            adapter.raw_sha256(ROOT / "scripts" / "run_personal_local_main.py"),
            core.V1_RUNNER_SHA256,
        )

    def test_compat_freeze_validates_without_records_service_or_prior_run_access(self):
        original_load_json = core.v1.load_json
        opened: list[Path] = []

        def tracked_load_json(path):
            opened.append(Path(path))
            return original_load_json(path)

        with (
            mock.patch.object(core.v1, "load_json", side_effect=tracked_load_json),
            mock.patch.object(
                core.v1,
                "load_bound_records",
                side_effect=AssertionError("record loader called"),
            ),
            mock.patch.object(
                core.v1,
                "preflight_service",
                side_effect=AssertionError("service contacted"),
            ),
        ):
            _, _, config = canary.validate_static()
        self.assertEqual(config["runner_file"], adapter.SCRIPT.relative_to(core.WORKSPACE).as_posix())
        self.assertFalse(
            any("Storage" in path.parts for path in opened)
        )

    def test_compat_freeze_uses_only_v21_prompts_and_schemas(self):
        config = core.v1.load_json(adapter.COMPAT_CONFIG)
        assets = config["construction_assets"]
        for key, row in assets.items():
            if key.startswith("prompt_") or key.startswith("schema_"):
                self.assertIn("_v2_1.", row["file"], key)
        self.assertEqual(
            {
                key
                for key in assets
                if key.startswith("rule_")
            },
            {
                "rule_base_admissibility",
                "rule_family_edit_contract",
                "rule_construction_comparison_acceptance",
                "rule_construction_qualification_thresholds",
            },
        )

    def test_every_v21_schema_is_closed_fully_required_subset(self):
        _, assets, _ = canary.validate_static()
        for case in canary.CANARY_CASES:
            schema = assets[case["schema_key"]]
            canary.validate_ollama_schema_subset(schema)
            canary.jsonschema.validate(case["expected"], schema)

    def test_schema_subset_rejects_advanced_or_optional_fields(self):
        _, assets, _ = canary.validate_static()
        advanced = copy.deepcopy(assets["schema_base_generation"])
        advanced["oneOf"] = []
        with self.assertRaisesRegex(canary.CanaryError, "schema_keyword_not_allowed"):
            canary.validate_ollama_schema_subset(advanced)

        optional = copy.deepcopy(assets["schema_base_generation"])
        optional["required"].remove("reason_codes")
        with self.assertRaisesRegex(
            canary.CanaryError, "schema_object_not_closed_or_fully_required"
        ):
            canary.validate_ollama_schema_subset(optional)

    def test_config_rejects_prompt_or_schema_hash_drift(self):
        config = core.v1.load_json(adapter.COMPAT_CONFIG)
        mutated = copy.deepcopy(config)
        mutated["construction_assets"]["schema_base_generation"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(canary.CanaryError, "compat_asset_hash_mismatch"):
            canary.validate_compat_config_source_free(mutated)

    def test_history_is_exactly_source_free_and_non_reused(self):
        history = core.v1.load_json(
            ROOT / "protocol" / "personal_local_main_v2_compat_history.json"
        )
        self.assertEqual(history, canary.EXPECTED_HISTORY)
        self.assertFalse(history["contains_source_text"])
        self.assertFalse(history["prior_results_reused"])
        self.assertFalse(history["historical_paths_opened_by_compat_runner"])

    def test_live_canary_path_is_single_attempt_schema_valid_and_write_free(self):
        v1_config, assets, config = canary.validate_static()
        expected_by_prompt = {
            case["user_prompt"]: case["expected"] for case in canary.CANARY_CASES
        }
        calls: list[str] = []

        def fake_api(endpoint, api_path, payload, *, timeout):
            self.assertEqual(api_path, "/api/chat")
            prompt = payload["messages"][-1]["content"]
            calls.append(prompt)
            return {
                "model": payload["model"],
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps(expected_by_prompt[prompt])},
            }

        with (
            mock.patch.object(canary, "validate_static", return_value=(v1_config, assets, config)),
            mock.patch.object(core.v1, "preflight_service", return_value={}),
            mock.patch.object(core.v1, "api_json", side_effect=fake_api),
            mock.patch.object(
                core.v1,
                "write_json_once",
                side_effect=AssertionError("canary wrote an artifact"),
            ),
            mock.patch.object(
                core.v1,
                "write_bytes_once",
                side_effect=AssertionError("canary wrote an artifact"),
            ),
        ):
            statuses = canary.run_live_canary()
        self.assertEqual(len(calls), len(canary.CANARY_CASES))
        self.assertEqual(len(calls), len(set(calls)))
        self.assertEqual(
            statuses,
            {
                case["code"]: case["expected"][case["status_field"]]
                for case in canary.CANARY_CASES
            },
        )

    def test_layer_two_rejects_additional_finite_codes_not_requested_by_canary(self):
        additions = {
            "base_generation": ("reason_codes", "no_genuine_counterevidence"),
            "base_admissibility": (
                "reason_codes",
                "independent_support_units_insufficient",
            ),
            "contextual_flattening_edit": (
                "reason_codes",
                "no_consequential_local_distinction",
            ),
            "unsupported_abstraction_edit": (
                "reason_codes",
                "one_level_broadening_not_possible",
            ),
            "construction_comparison": (
                "uncertainty_codes",
                "diff_not_semantically_clear",
            ),
        }
        _, assets, _ = canary.validate_static()
        for case in canary.CANARY_CASES:
            output = copy.deepcopy(case["expected"])
            field, addition = additions[case["code"]]
            output[field].append(addition)
            canary.jsonschema.validate(output, assets[case["schema_key"]])
            with self.assertRaisesRegex(
                canary.CanaryError,
                rf"canary_{case['code']}_layer_2_semantic_failure",
            ):
                canary.validate_case_semantics(case, output)

    def test_base_admissibility_requires_all_not_ready_with_empty_positions(self):
        case = next(
            row for row in canary.CANARY_CASES if row["code"] == "base_admissibility"
        )
        output = copy.deepcopy(case["expected"])
        _, assets, _ = canary.validate_static()
        canary.jsonschema.validate(output, assets[case["schema_key"]])
        canary.validate_case_semantics(case, output)

        output["readiness"]["bounded_claim"]["status"] = "unclear"
        canary.jsonschema.validate(output, assets[case["schema_key"]])
        with self.assertRaisesRegex(
            canary.CanaryError,
            "canary_base_admissibility_layer_2_semantic_failure",
        ):
            canary.validate_case_semantics(case, output)

    def test_layer_two_rejects_schema_valid_wrong_branches(self):
        mutations = {
            "base_generation": {"status": "constructed"},
            "base_admissibility": {"base_status": "admissible"},
            "contextual_flattening_edit": {"status": "proposed"},
            "unsupported_abstraction_edit": {"status": "proposed"},
            "construction_comparison": {"comparison_clarity": "clear"},
        }
        _, assets, _ = canary.validate_static()
        for case in canary.CANARY_CASES:
            output = copy.deepcopy(case["expected"])
            output.update(mutations[case["code"]])
            canary.jsonschema.validate(output, assets[case["schema_key"]])
            with self.assertRaisesRegex(
                canary.CanaryError,
                rf"canary_{case['code']}_layer_2_semantic_failure",
            ):
                canary.validate_case_semantics(case, output)

    def test_layer_two_rejects_schema_valid_cross_field_contradictions(self):
        cases = {case["code"]: case for case in canary.CANARY_CASES}
        mutations = {}

        output = copy.deepcopy(cases["base_generation"]["expected"])
        output["role_plan"][0]["role"] = "support"
        mutations["base_generation"] = output

        output = copy.deepcopy(cases["base_admissibility"]["expected"])
        output["readiness"]["non_support_anchor"]["status"] = "ready"
        mutations["base_admissibility"] = output

        output = copy.deepcopy(cases["contextual_flattening_edit"]["expected"])
        output["patch"]["edit_field"] = "claim"
        mutations["contextual_flattening_edit"] = output

        output = copy.deepcopy(cases["unsupported_abstraction_edit"]["expected"])
        output["patch"]["edit_field"] = "claim"
        mutations["unsupported_abstraction_edit"] = output

        output = copy.deepcopy(cases["construction_comparison"]["expected"])
        output["single_material_difference"] = True
        mutations["construction_comparison"] = output

        _, assets, _ = canary.validate_static()
        for code, output in mutations.items():
            case = cases[code]
            canary.jsonschema.validate(output, assets[case["schema_key"]])
            with self.assertRaisesRegex(
                canary.CanaryError,
                rf"canary_{code}_layer_2_semantic_failure",
            ):
                canary.validate_case_semantics(case, output)

    def test_canary_runtime_failure_output_does_not_echo_response(self):
        sentinel = "SOURCE_TEXT_SENTINEL_MUST_NOT_PRINT"
        with (
            mock.patch.object(canary, "parse_args", return_value=mock.Mock(command="run")),
            mock.patch.object(
                canary,
                "run_live_canary",
                side_effect=RuntimeError(sentinel),
            ),
            tempfile.TemporaryFile(mode="w+") as captured,
            mock.patch.object(canary.sys, "stderr", captured),
        ):
            self.assertEqual(canary.main(), 2)
            captured.seek(0)
            output = captured.read()
        self.assertNotIn(sentinel, output)
        self.assertIn("canary_runtime_failure", output)


if __name__ == "__main__":
    unittest.main()
