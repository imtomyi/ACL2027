#!/usr/bin/env python3
"""Source-free portability tests for the WarrantRoute reviewer adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_warrantroute_multimodel.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/warrantroute_multimodel_adapter_freeze.json"
SPEC = importlib.util.spec_from_file_location("warrantroute_multimodel_tests", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

ITEM_ID = "DJI_0000000000000001"
ITEM_SHA = "1" * 64


def digest(*parts: object) -> str:
    payload = json.dumps(parts, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def observation(
    profile: dict,
    role: str,
    repetition: int,
    *,
    status: str = "valid",
) -> dict:
    flags = {
        "researcher": ["unsupported_inference"],
        "qualitative_methods": ["lost_negative_case"],
        "domain": ["contextual_flattening"],
    }
    rating = {"cannot_judge": [], "serious_error_flags": flags[role]} if status == "valid" else None
    return {
        "actor_id": profile["actor_ids"][role],
        "prompted_role": role,
        "model_id": profile["model_id"],
        "model_snapshot_sha256": profile["model_manifest_sha256"],
        "rating_repetition": repetition,
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "observation_status": status,
        "rating": rating,
        "observation_sha256": digest(profile["profile_id"], role, repetition, status),
    }


def matrix(profile: dict, adapter: object) -> dict:
    return {
        "matrix_schema_version": "warrantroute-reviewer-matrix-v1",
        "reviewer_profile_id": profile["profile_id"],
        "adapter_freeze_sha256": adapter.adapter_freeze_sha256,
        "reviewer_profile_sha256": adapter.profile_sha256,
        "study_id": "source_free_contract",
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "reviewer_model": {
            "model_id": profile["model_id"],
            "model_snapshot_sha256": profile["model_manifest_sha256"],
        },
        "role_observations": {
            role: [observation(profile, role, repetition) for repetition in (1, 2, 3)]
            for role in MODULE.ROLE_ORDER
        },
        "contains_source_text": False,
        "contains_rationale": False,
        "software_contract_fixture": True,
        "manuscript_eligible": False,
    }


class WarrantRouteMultimodelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = MODULE.load_json(CONFIG)
        cls.adapters = {
            profile_id: MODULE.load_validated_adapter(CONFIG, profile_id)
            for profile_id in MODULE.PROFILE_ORDER
        }
        cls.schemas = {
            "reviewer_matrix_schema": cls.adapters["qwen3_8b"].matrix_schema(),
            "result_schema": cls.adapters["qwen3_8b"].result_schema(),
        }

    def profile(self, profile_id: str) -> dict:
        return MODULE.select_reviewer_profile(self.config, profile_id)

    def adapter(self, profile_id: str) -> object:
        return self.adapters[profile_id]

    def reduce(self, profile: dict, route: str, aggregation: str, value: dict | None = None) -> dict:
        adapter = self.adapter(profile["profile_id"])
        return MODULE.reduce_reviewer_matrix_contract_fixture(
            value or matrix(profile, adapter),
            route=route,
            aggregation=aggregation,
            adapter=adapter,
        )

    def test_registry_has_qwen_primary_and_unbound_llama_gemma_templates(self) -> None:
        self.assertEqual(tuple(self.config["reviewer_profiles"]), MODULE.PROFILE_ORDER)
        self.assertEqual(self.config["primary_reviewer_profile_id"], "qwen3_8b")
        self.assertEqual(self.profile("qwen3_8b")["model_id"], "qwen3:8b")
        self.assertEqual(self.profile("llama3_1_8b")["model_id"], "llama3.1:8b")
        self.assertEqual(self.profile("gemma3_4b")["model_id"], "gemma3:4b")
        self.assertEqual(self.profile("gemma3_4b")["minimum_num_ctx"], 16384)
        for profile_id in ("llama3_1_8b", "gemma3_4b"):
            self.assertEqual(self.profile(profile_id)["status"], "adapter_template_unbound")
            self.assertEqual(
                self.profile(profile_id)["reviewer_canary_status"],
                "required_before_activation",
            )

    def test_exact_profile_selection_rejects_unknown_and_implicit_fallback(self) -> None:
        for profile_id in MODULE.PROFILE_ORDER:
            self.assertEqual(MODULE.select_reviewer_profile(self.config, profile_id)["profile_id"], profile_id)
        for invalid in ("", "QWEN3_8B", " qwen3_8b", "qwen3:8b", "unknown"):
            with self.assertRaises(MODULE.MultimodelAdapterError):
                MODULE.select_reviewer_profile(self.config, invalid)
        for invalid in (None, 1, []):
            with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "reviewer_profile_id_invalid"):
                MODULE.select_reviewer_profile(self.config, invalid)

    def test_profile_registry_rejects_duplicate_or_missing_actors(self) -> None:
        duplicate = copy.deepcopy(self.config)
        duplicate["reviewer_profiles"]["gemma3_4b"]["actor_ids"]["domain"] = duplicate[
            "reviewer_profiles"
        ]["llama3_1_8b"]["actor_ids"]["domain"]
        with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "reviewer_actor_cross_profile_duplicate"):
            MODULE.validate_freeze(duplicate, selected_profile_id="qwen3_8b")
        missing = copy.deepcopy(self.config)
        del missing["reviewer_profiles"]["llama3_1_8b"]["actor_ids"]["domain"]
        with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "reviewer_profile_schema_invalid"):
            MODULE.validate_freeze(missing, selected_profile_id="qwen3_8b")

    def test_one_shared_schema_accepts_all_three_profiles(self) -> None:
        serialized_schemas = json.dumps(
            {
                "matrix": self.schemas["reviewer_matrix_schema"],
                "result": self.schemas["result_schema"],
            },
            sort_keys=True,
        )
        for literal in ("qwen3:8b", "llama3.1:8b", "gemma3:4b", "qwen3_8b_researcher"):
            self.assertNotIn(literal, serialized_schemas)
        for profile_id in MODULE.PROFILE_ORDER:
            profile = self.profile(profile_id)
            adapter = self.adapter(profile_id)
            MODULE.validate_reviewer_matrix(
                matrix(profile, adapter),
                adapter=adapter,
            )

    def test_model_actor_and_snapshot_are_bound_to_selected_profile(self) -> None:
        for index, profile_id in enumerate(MODULE.PROFILE_ORDER):
            profile = self.profile(profile_id)
            adapter = self.adapter(profile_id)
            other = self.profile(MODULE.PROFILE_ORDER[(index + 1) % len(MODULE.PROFILE_ORDER)])
            top_model = matrix(profile, adapter)
            top_model["reviewer_model"]["model_id"] = other["model_id"]
            role_actor = matrix(profile, adapter)
            role_actor["role_observations"]["domain"][0]["actor_id"] = other["actor_ids"]["domain"]
            role_model = matrix(profile, adapter)
            role_model["role_observations"]["researcher"][0]["model_id"] = other["model_id"]
            role_snapshot = matrix(profile, adapter)
            role_snapshot["role_observations"]["qualitative_methods"][0][
                "model_snapshot_sha256"
            ] = other["model_manifest_sha256"]
            cases = (
                (top_model, "matrix_model_drift"),
                (role_actor, "matrix_actor_drift:domain"),
                (role_model, "matrix_model_drift:researcher"),
                (role_snapshot, "matrix_snapshot_drift:qualitative_methods"),
            )
            for value, code in cases:
                with self.assertRaisesRegex(MODULE.MultimodelAdapterError, code):
                    MODULE.validate_reviewer_matrix(
                        value,
                        adapter=adapter,
                    )

    def test_matrix_binds_exact_adapter_freeze_and_profile(self) -> None:
        adapter = self.adapter("qwen3_8b")
        freeze_drift = matrix(self.profile("qwen3_8b"), adapter)
        freeze_drift["adapter_freeze_sha256"] = "0" * 64
        profile_drift = matrix(self.profile("qwen3_8b"), adapter)
        profile_drift["reviewer_profile_sha256"] = "0" * 64
        for value, code in (
            (freeze_drift, "matrix_adapter_freeze_drift"),
            (profile_drift, "matrix_profile_hash_drift"),
        ):
            with self.assertRaisesRegex(MODULE.MultimodelAdapterError, code):
                MODULE.validate_reviewer_matrix(value, adapter=adapter)

        forged_profile = {
            **self.profile("qwen3_8b"),
            "profile_id": "forged_model",
            "model_id": "forged:1b",
        }
        forged_adapter = replace(
            adapter,
            profile_id="forged_model",
            profile_sha256=MODULE.sha256_bytes(MODULE.canonical_bytes(forged_profile)),
            profile_json=MODULE.canonical_bytes(forged_profile).decode("utf-8"),
        )
        with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "unknown_reviewer_profile"):
            MODULE.validate_reviewer_matrix(freeze_drift, adapter=forged_adapter)

        forged_schema_adapter = replace(adapter, matrix_schema_json="{}\n")
        with self.assertRaisesRegex(
            MODULE.MultimodelAdapterError,
            "validated_adapter_drift",
        ):
            MODULE.validate_reviewer_matrix(
                matrix(self.profile("qwen3_8b"), adapter),
                adapter=forged_schema_adapter,
            )

    def test_adapter_handle_cannot_bypass_selected_manifest_revalidation(self) -> None:
        adapter = self.adapter("qwen3_8b")
        selected_manifest = Path(self.profile("qwen3_8b")["model_manifest_path"])
        original = MODULE.read_regular_bytes

        def guarded(path: Path) -> bytes:
            if path == selected_manifest:
                raise MODULE.MultimodelAdapterError("selected_manifest_revalidation_observed")
            return original(path)

        with mock.patch.object(MODULE, "read_regular_bytes", side_effect=guarded):
            with self.assertRaisesRegex(
                MODULE.MultimodelAdapterError,
                "selected_manifest_revalidation_observed",
            ):
                MODULE.verify_adapter_binding(adapter)

    def test_route_reduction_is_identical_across_profiles(self) -> None:
        fields = (
            "route",
            "selected_roles",
            "selected_serious_error_flags",
            "selected_role_failures",
            "aggregation",
            "fallback_used",
            "merged_rating_created",
        )
        for route in MODULE.ROUTE_ORDER:
            for aggregation in ("repetition_1", "two_of_three"):
                semantic_results = []
                for profile_id in MODULE.PROFILE_ORDER:
                    result = self.reduce(self.profile(profile_id), route, aggregation)
                    semantic_results.append({field: result[field] for field in fields})
                self.assertEqual(semantic_results[1:], semantic_results[:-1])

    def test_failures_never_trigger_cross_role_fallback(self) -> None:
        for profile_id in MODULE.PROFILE_ORDER:
            profile = self.profile(profile_id)
            value = matrix(profile, self.adapter(profile_id))
            value["role_observations"]["qualitative_methods"][0] = observation(
                profile, "qualitative_methods", 1, status="timeout"
            )
            result = self.reduce(profile, "both", "repetition_1", value)
            self.assertEqual(result["selected_serious_error_flags"], ["contextual_flattening"])
            self.assertEqual(result["selected_role_failures"], ["qualitative_methods"])
            self.assertFalse(result["fallback_used"])
            self.assertNotIn("unsupported_inference", result["selected_serious_error_flags"])

    def test_result_schema_enforces_route_role_invariants(self) -> None:
        result = self.reduce(self.profile("qwen3_8b"), "domain", "repetition_1")
        result["selected_roles"] = ["researcher"]
        with self.assertRaisesRegex(
            MODULE.MultimodelAdapterError, "model_neutral_result_schema_invalid"
        ):
            MODULE._schema_validate(
                result,
                self.adapter("qwen3_8b").result_schema(),
                "model_neutral_result_schema_invalid",
            )

    def test_train_and_run_block_for_every_profile_before_source_or_service(self) -> None:
        original = MODULE.read_regular_bytes
        observed: list[Path] = []

        def guarded(path: Path) -> bytes:
            observed.append(path)
            if (
                "/dataset/" in str(path)
                or "/Storage/" in str(path)
                or "/.ollama/" in str(path)
            ):
                raise AssertionError("source path opened")
            return original(path)

        with mock.patch.object(MODULE, "read_regular_bytes", side_effect=guarded):
            for profile_id in MODULE.PROFILE_ORDER:
                for command, code in (
                    ("train", "router_training_not_authorized"),
                    ("run", "source_bearing_execution_not_authorized"),
                ):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        status = MODULE.main([command, "--reviewer-profile", profile_id])
                    self.assertEqual(status, 2)
                    self.assertIn(code, output.getvalue())
        self.assertFalse(
            any(
                "/dataset/" in str(path)
                or "/Storage/" in str(path)
                or "/.ollama/" in str(path)
                for path in observed
            )
        )

    def test_asset_and_manifest_drift_fail_closed(self) -> None:
        asset = copy.deepcopy(self.config)
        asset["assets"]["result_schema"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "result_schema_hash_drift"):
            MODULE.validate_freeze(asset, selected_profile_id="qwen3_8b")
        manifest = copy.deepcopy(self.config)
        manifest["reviewer_profiles"]["llama3_1_8b"]["model_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.MultimodelAdapterError, "reviewer_manifest:llama3_1_8b_hash_drift"):
            MODULE.validate_freeze(manifest, selected_profile_id="llama3_1_8b")

    def test_unused_profile_manifest_drift_does_not_break_selected_profile(self) -> None:
        unused_drift = copy.deepcopy(self.config)
        unused_drift["reviewer_profiles"]["llama3_1_8b"]["model_manifest_sha256"] = "0" * 64
        MODULE.validate_freeze(unused_drift, selected_profile_id="qwen3_8b")

    def test_manifest_path_cannot_be_redirected_into_workspace(self) -> None:
        redirected = copy.deepcopy(self.config)
        redirected["reviewer_profiles"]["qwen3_8b"]["model_manifest_path"] = str(
            ROOT / "dataset/manifests/dreaddit_source_manifest.json"
        )
        opened: list[Path] = []
        original = MODULE.read_regular_bytes

        def guarded(path: Path) -> bytes:
            opened.append(path)
            if "/dataset/" in str(path):
                raise AssertionError("dataset path opened")
            return original(path)

        with mock.patch.object(MODULE, "read_regular_bytes", side_effect=guarded):
            with self.assertRaisesRegex(
                MODULE.MultimodelAdapterError,
                "reviewer_manifest_path_drift:qwen3_8b",
            ):
                MODULE.validate_freeze(redirected, selected_profile_id="qwen3_8b")
        self.assertFalse(any("/dataset/" in str(path) for path in opened))

    def test_cli_dry_run_reports_selected_profile_without_contacting_model(self) -> None:
        for profile_id in MODULE.PROFILE_ORDER:
            output = io.StringIO()
            with redirect_stdout(output):
                status = MODULE.main(["dry-run", "--reviewer-profile", profile_id])
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["selected_reviewer_profile_id"], profile_id)
            self.assertFalse(payload["model_service_contacted"])
            self.assertFalse(payload["source_text_accessed"])


if __name__ == "__main__":
    unittest.main()
