#!/usr/bin/env python3
"""Independent synthetic audit of the v2.1 schemas and source-free canary."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CANARY_SCRIPT = ROOT / "scripts" / "run_personal_local_main_v21_canary.py"
SPEC = importlib.util.spec_from_file_location(
    "rq2_personal_local_main_v21_independent_adversarial", CANARY_SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
canary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(canary)
core = canary.core


EXPECTED_HASHES = {
    "compat_freeze": "62e4c2e4293a5acd7fe6191b519e82fe1686f389d2bc52c007aae2ea0a8152da",
    "adapter": "9cf46518f47edf25b2fbaab75e58815dbcc1acb8da60bb059bc867abf8122856",
    "canary": "f5ac075a6b0f5c2dd562790f88c66811139b4be5c21c7913539ae8e6dccf8b1f",
    "history": "4c9748180517088f474fcee3453ebc65119cdc528a20ff7576035713504b49b6",
}


def assert_schema_rejects(test: unittest.TestCase, value: dict, schema: dict) -> None:
    with test.assertRaises(canary.jsonschema.ValidationError):
        canary.jsonschema.validate(value, schema)


def comparison_anchor(position: int) -> dict:
    return {
        "flaw_family": "unsupported_evidence",
        "evidence_positions": [position],
        "interpretation_fields": ["claim"],
        "reason_code": "cited_position_does_not_support_material_claim",
    }


class V21IndependentAdversarialTests(unittest.TestCase):
    def test_exact_compatibility_bytes_are_bound(self):
        self.assertEqual(canary.raw_sha256(canary.COMPAT_CONFIG), EXPECTED_HASHES["compat_freeze"])
        self.assertEqual(canary.raw_sha256(canary.ADAPTER), EXPECTED_HASHES["adapter"])
        self.assertEqual(canary.raw_sha256(CANARY_SCRIPT), EXPECTED_HASHES["canary"])
        history = ROOT / "protocol" / "personal_local_main_v2_compat_history.json"
        self.assertEqual(canary.raw_sha256(history), EXPECTED_HASHES["history"])

        config = core.v1.load_json(canary.COMPAT_CONFIG)
        self.assertEqual(
            config["construction_assets"]["compat_canary"]["sha256"],
            EXPECTED_HASHES["canary"],
        )
        self.assertEqual(config["runner_sha256"], EXPECTED_HASHES["adapter"])

    def test_every_schema_uses_only_the_closed_simple_subset(self):
        _, assets, _ = canary.validate_static()
        prohibited = {
            "$ref",
            "$defs",
            "definitions",
            "const",
            "oneOf",
            "anyOf",
            "allOf",
            "if",
            "then",
            "else",
            "not",
            "prefixItems",
            "dependentSchemas",
            "patternProperties",
        }

        def visit(node):
            if isinstance(node, dict):
                self.assertTrue(set(node).isdisjoint(prohibited))
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        for case in canary.CANARY_CASES:
            schema = assets[case["schema_key"]]
            canary.validate_ollama_schema_subset(schema)
            canary.jsonschema.Draft202012Validator.check_schema(schema)
            visit(schema)

    def test_all_schemas_reject_root_and_nested_source_identifiers(self):
        _, assets, _ = canary.validate_static()
        for case in canary.CANARY_CASES:
            with self.subTest(case=case["code"], location="root"):
                schema = assets[case["schema_key"]]
                root_injected = copy.deepcopy(case["expected"])
                root_injected["source_id"] = "SRC_SYNTHETIC"
                assert_schema_rejects(self, root_injected, schema)

            nested = copy.deepcopy(case["expected"])
            if case["code"] == "base_generation":
                nested["role_plan"][0]["excerpt_id"] = "EXC_SYNTHETIC"
            elif case["code"] == "base_admissibility":
                nested["readiness"]["non_support_anchor"]["source_id"] = "SRC_SYNTHETIC"
            elif case["code"] in {
                "contextual_flattening_edit",
                "unsupported_abstraction_edit",
            }:
                nested["patch"]["excerpt_id"] = "EXC_SYNTHETIC"
            else:
                nested["comparison_clarity"] = "clear"
                nested["uncertainty_codes"] = []
                nested["present_flaws"] = ["unsupported_evidence"]
                nested["single_material_difference"] = True
                nested["anchors"] = [comparison_anchor(1)]
                nested["anchors"][0]["source_id"] = "SRC_SYNTHETIC"
            with self.subTest(case=case["code"], location="nested"):
                assert_schema_rejects(self, nested, assets[case["schema_key"]])

    def test_all_position_bearing_schemas_reject_position_seven(self):
        _, assets, _ = canary.validate_static()
        mutations: dict[str, dict] = {}
        for case in canary.CANARY_CASES:
            value = copy.deepcopy(case["expected"])
            if case["code"] == "base_generation":
                value["role_plan"][-1]["position"] = 7
            elif case["code"] == "base_admissibility":
                value["readiness"]["non_support_anchor"]["evidence_positions"] = [7]
            elif case["code"] in {
                "contextual_flattening_edit",
                "unsupported_abstraction_edit",
            }:
                value["patch"]["evidence_positions"] = [7]
            else:
                value["comparison_clarity"] = "clear"
                value["present_flaws"] = ["unsupported_evidence"]
                value["single_material_difference"] = True
                value["anchors"] = [comparison_anchor(7)]
                value["uncertainty_codes"] = []
            mutations[case["code"]] = value

        for case in canary.CANARY_CASES:
            with self.subTest(case=case["code"]):
                assert_schema_rejects(
                    self, mutations[case["code"]], assets[case["schema_key"]]
                )

    def test_simple_schema_status_flexibility_is_closed_by_runtime_semantics(self):
        _, assets, _ = canary.validate_static()
        malformed_constructed = copy.deepcopy(canary.CANARY_CASES[0]["expected"])
        malformed_constructed.update(
            {
                "status": "constructed",
                "theme_name": "Synthetic",
                "claim": "Synthetic",
                "explanation": "Synthetic",
                "claim_scope": "displayed_packet_only",
                "reason_codes": [],
            }
        )
        # The deliberately simple Ollama schema cannot express this cross-field
        # constraint, so the deterministic runtime mapper must reject it.
        canary.jsonschema.validate(malformed_constructed, assets["schema_base_generation"])
        excerpts = [
            {
                "excerpt_id": f"EXC_{position:016x}",
                "source_id": f"SRC_{position:016x}",
                "speaker_id": None,
            }
            for position in range(1, 7)
        ]
        with self.assertRaises(core.V2Error):
            core.map_positional_base_v2(malformed_constructed, excerpts)

        unclear_with_flaw = copy.deepcopy(canary.CANARY_CASES[-1]["expected"])
        unclear_with_flaw["present_flaws"] = ["unsupported_evidence"]
        unclear_with_flaw["anchors"] = [comparison_anchor(1)]
        canary.jsonschema.validate(
            unclear_with_flaw, assets["schema_construction_comparison"]
        )
        accepted, reasons = core.comparison_acceptance_v2(
            "unsupported_evidence",
            {"passed": True, "anchor_positions": [1]},
            unclear_with_flaw,
        )
        self.assertFalse(accepted)
        self.assertIn("comparison_unclear", reasons)
        self.assertIn("uncertainty_codes_nonempty", reasons)

    def test_comparison_canary_and_prompt_preserve_target_blinding(self):
        _, assets, _ = canary.validate_static()
        comparison_case = next(
            case for case in canary.CANARY_CASES if case["code"] == "construction_comparison"
        )
        user_prompt = comparison_case["user_prompt"]
        self.assertNotIn("target_flaw", user_prompt)
        self.assertNotIn("family_index", user_prompt)
        self.assertNotIn("truth", user_prompt.lower())
        self.assertNotIn("reviewer", user_prompt.lower())
        system_prompt = assets[comparison_case["prompt_key"]]
        self.assertIn("target-blind", system_prompt)
        self.assertIn("intended target", system_prompt)
        self.assertIn("withheld", system_prompt)
        self.assertNotIn("construction note", user_prompt.lower())

    def test_static_canary_opens_no_dataset_or_storage_path(self):
        opened: list[Path] = []
        original_path_open = Path.open
        original_read_regular = core.v1.read_regular_bytes

        def reject_forbidden(path: Path) -> None:
            absolute = Path(path).absolute()
            relative_parts = absolute.parts
            if "Storage" in relative_parts or "dataset" in relative_parts or absolute.suffix == ".jsonl":
                raise AssertionError(f"forbidden canary read: {absolute.name}")
            opened.append(absolute)

        def guarded_path_open(path_self, *args, **kwargs):
            reject_forbidden(Path(path_self))
            return original_path_open(path_self, *args, **kwargs)

        def guarded_read_regular(path):
            reject_forbidden(Path(path))
            return original_read_regular(path)

        with (
            mock.patch.object(Path, "open", guarded_path_open),
            mock.patch.object(core.v1, "read_regular_bytes", side_effect=guarded_read_regular),
            mock.patch.object(
                core.v1,
                "load_bound_records",
                side_effect=AssertionError("record loader called"),
            ),
            mock.patch.object(
                core.v1,
                "preflight_service",
                side_effect=AssertionError("Ollama contacted"),
            ),
            mock.patch.object(
                core.v1,
                "api_json",
                side_effect=AssertionError("model endpoint contacted"),
            ),
        ):
            canary.validate_static()
        self.assertTrue(opened)
        self.assertFalse(any("Storage" in path.parts for path in opened))
        self.assertFalse(any("dataset" in path.parts for path in opened))

    def test_schema_valid_model_content_never_reaches_canary_output(self):
        v1_config, assets, config = canary.validate_static()
        sentinel = "SYNTHETIC_MODEL_CONTENT_MUST_NOT_PRINT"
        unexpected = copy.deepcopy(canary.CANARY_CASES[0]["expected"])
        unexpected["theme_name"] = sentinel
        canary.jsonschema.validate(unexpected, assets["schema_base_generation"])

        def fake_api(endpoint, api_path, payload, *, timeout):
            self.assertEqual(api_path, "/api/chat")
            return {
                "model": payload["model"],
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps(unexpected)},
            }

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                canary, "parse_args", return_value=types.SimpleNamespace(command="run")
            ),
            mock.patch.object(
                canary, "validate_static", return_value=(v1_config, assets, config)
            ),
            mock.patch.object(core.v1, "preflight_service", return_value={}),
            mock.patch.object(core.v1, "api_json", side_effect=fake_api),
            mock.patch.object(
                core.v1,
                "load_bound_records",
                side_effect=AssertionError("record loader called"),
            ),
            mock.patch.object(
                core.v1,
                "write_json_once",
                side_effect=AssertionError("canary wrote JSON"),
            ),
            mock.patch.object(
                core.v1,
                "write_bytes_once",
                side_effect=AssertionError("canary wrote bytes"),
            ),
            mock.patch.object(canary.sys, "stdout", stdout),
            mock.patch.object(canary.sys, "stderr", stderr),
        ):
            self.assertEqual(canary.main(), 2)
        emitted = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(sentinel, emitted)
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["canary_status"], "failed")
        self.assertEqual(
            payload["failure_code"],
            "canary_base_generation_layer_2_semantic_failure",
        )
        self.assertEqual(set(payload), {"canary_status", "failure_code"})

    def test_schema_invalid_content_maps_to_finite_case_layer_one_code(self):
        v1_config, assets, config = canary.validate_static()
        sentinel = "SCHEMA_INVALID_MODEL_CONTENT_MUST_NOT_PRINT"
        invalid = copy.deepcopy(canary.CANARY_CASES[0]["expected"])
        invalid["unexpected_field"] = sentinel

        def fake_api(endpoint, api_path, payload, *, timeout):
            self.assertEqual(api_path, "/api/chat")
            return {
                "model": payload["model"],
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps(invalid)},
            }

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                canary, "parse_args", return_value=types.SimpleNamespace(command="run")
            ),
            mock.patch.object(
                canary, "validate_static", return_value=(v1_config, assets, config)
            ),
            mock.patch.object(core.v1, "preflight_service", return_value={}),
            mock.patch.object(core.v1, "api_json", side_effect=fake_api),
            mock.patch.object(canary.sys, "stdout", stdout),
            mock.patch.object(canary.sys, "stderr", stderr),
        ):
            self.assertEqual(canary.main(), 2)
        emitted = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(sentinel, emitted)
        payload = json.loads(stderr.getvalue())
        self.assertEqual(
            payload,
            {
                "canary_status": "failed",
                "failure_code": (
                    "canary_base_generation_layer_1_compatibility_failure"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
