#!/usr/bin/env python3
"""Source-free tests for the model-profiled All roles v2 component."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py"
SPEC = importlib.util.spec_from_file_location("all_roles_profiles_v2_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def full_rating(*, flags: list[str] | None = None) -> dict:
    flags = flags or []
    return {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 4,
        "voice_boundary_preservation": 4,
        "scope_calibration": 4,
        "cannot_judge": [],
        "confidence": 4,
        "disposition": "revise" if flags else "accept",
        "requested_expertise": "none",
        "serious_error_flags": flags,
        "rationale": "The inert claim is limited to the displayed inert evidence.",
    }


def response(context: MODULE.ModelContext, *, model_id: str | None = None) -> dict:
    return {
        "model": model_id or context.profile()["model_id"],
        "done": True,
        "done_reason": "stop",
        "message": {
            "role": "assistant",
            "content": json.dumps(full_rating()),
        },
        "prompt_eval_count": 1200,
        "eval_count": 80,
    }


def fixture_input(
    context: MODULE.ModelContext,
    *,
    flags: dict[tuple[int, str, int], list[str]] | None = None,
    item_count: int = 1,
) -> dict:
    flags = flags or {}
    profile = context.profile()
    config = context.config()
    items = []
    for item_index in range(item_count):
        family = MODULE.v1_core.ERROR_FAMILIES[
            item_index % len(MODULE.v1_core.ERROR_FAMILIES)
        ]
        item_hash = f"{2000 + item_index:064x}"
        role_observations = {}
        for role in MODULE.ROLE_ORDER:
            role_observations[role] = []
            for repetition in MODULE.REPETITIONS:
                selected_flags = flags.get((item_index, role, repetition), [])
                role_observations[role].append({
                    "actor_id": profile["role_actor_ids"][role],
                    "model_id": profile["model_id"],
                    "model_snapshot_sha256": profile[
                        "local_manifest_file_sha256"
                    ],
                    "role_prompt_sha256": config["roles"][role]["prompt"][
                        "sha256"
                    ],
                    "rating_repetition": repetition,
                    "evaluator_item_sha256": item_hash,
                    "observation_status": "valid",
                    "rating": {
                        "disposition": "revise" if selected_flags else "accept",
                        "cannot_judge": [],
                        "serious_error_flags": selected_flags,
                    },
                    "fixture_observation_sha256": "0" * 64,
                })
        items.append({
            "item_id": f"DJI_{item_index + 1:016x}",
            "cluster_id": f"CLUSTER_{item_index + 1}",
            "error_family": family,
            "required_flag": MODULE.v1_core.TARGET_TO_FLAG[family],
            "evaluator_item_sha256": item_hash,
            "role_observations": role_observations,
        })
    value = {
        "input_schema_version": "rq2-all-roles-profile-input-v2",
        "model_profile_id": context.model_profile_id,
        "study_id": "source-free-profile-test",
        "projection_status": "source_free_software_fixture_only",
        "contains_real_observations": False,
        "manuscript_eligible": False,
        "lane": {
            "corpus": "dreaddit",
            "source_split": "official_train",
            "internal_lane": "development_train",
            "experimental_role": "development_diagnostic",
            "heldout": False,
        },
        "fixture_assumptions": {"qualification_gate_passed": True},
        "external_study_references": {
            "verification_status": "not_verified_by_source_free_component",
            "qualification_seal_sha256": "a" * 64,
            "eligibility_truth_seal_sha256": "b" * 64,
            "review_matrix_seal_sha256": "c" * 64,
        },
        "reviewer_model": {
            "model_id": profile["model_id"],
            "model_snapshot_sha256": profile["local_manifest_file_sha256"],
        },
        "items": items,
    }
    return MODULE.seal_fixture_observations(context, value)


class AllRolesProfilesV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contexts = {
            profile_id: MODULE.load_model_context(profile_id)
            for profile_id in MODULE.EXPECTED_PROFILE_IDS
        }

    def test_registry_is_closed_unique_and_qwen_is_only_default(self) -> None:
        qwen = self.contexts[MODULE.PRIMARY_PROFILE_ID]
        registry = MODULE.validate_component_freeze(qwen.config())["registry"]
        self.assertEqual(tuple(registry["profiles"]), MODULE.EXPECTED_PROFILE_IDS)
        self.assertEqual(registry["primary_profile_id"], "qwen3_8b")
        primary = [
            key
            for key, profile in registry["profiles"].items()
            if profile["profile_status"] == "primary_source_free_canary_passed"
        ]
        self.assertEqual(primary, ["qwen3_8b"])
        self.assertEqual(
            {
                key: profile["profile_status"]
                for key, profile in registry["profiles"].items()
                if key != "qwen3_8b"
            },
            {
                "llama3_1_8b": "compatibility_source_free_canary_passed",
                "gemma3_4b": "compatibility_source_free_canary_passed",
            },
        )
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "unknown_model_profile"):
            MODULE.load_model_context("unregistered_model")

    def test_v2_schemas_have_distinct_profile_bound_ids_and_versions(self) -> None:
        for profile_id, context in self.contexts.items():
            with self.subTest(profile_id=profile_id):
                assets = context.assets()
                input_schema = MODULE._profile_schema(
                    assets["all_roles_input_schema_v1"], context, "input"
                )
                result_schema = MODULE._profile_schema(
                    assets["all_roles_result_schema_v1"], context, "result"
                )
                seal_schema = MODULE._profile_schema(
                    assets["all_roles_result_seal_schema_v1"], context, "seal"
                )
                self.assertIn(f"profile-input-v2/{profile_id}", input_schema["$id"])
                self.assertIn(f"profile-result-v2/{profile_id}", result_schema["$id"])
                self.assertIn(
                    f"profile-result-seal-v2/{profile_id}", seal_schema["$id"]
                )
                self.assertTrue(
                    input_schema["$id"].endswith(f"/{context.freeze_sha256}.json")
                )
                self.assertTrue(
                    result_schema["$id"].endswith(f"/{context.freeze_sha256}.json")
                )
                self.assertTrue(
                    seal_schema["$id"].endswith(f"/{context.freeze_sha256}.json")
                )
                self.assertEqual(
                    input_schema["properties"]["input_schema_version"]["const"],
                    "rq2-all-roles-profile-input-v2",
                )
                self.assertEqual(
                    assets["all_roles_input_schema_v1"]["properties"]
                    ["input_schema_version"]["const"],
                    "rq2-all-roles-input-v1",
                )

    def test_profile_loader_hashes_exact_small_layer_bytes(self) -> None:
        context = self.contexts["qwen3_8b"]
        profile = context.profile()
        params_path = MODULE._blob_path(
            Path(profile["local_manifest_path"]),
            profile["params_layer_digest"],
        )
        original_read = MODULE.transport_runtime.read_regular_bytes

        def altered_read(path: Path) -> bytes:
            data = original_read(path)
            if path == params_path:
                return json.dumps(json.loads(data), indent=2).encode("utf-8")
            return data

        with mock.patch.object(
            MODULE.transport_runtime,
            "read_regular_bytes",
            side_effect=altered_read,
        ):
            with self.assertRaisesRegex(
                MODULE.ProfileAllRolesError,
                "qwen3_8b_params_blob_hash_drift",
            ):
                MODULE.load_model_context("qwen3_8b")

    def test_all_profiles_build_exact_three_by_three_without_fallback(self) -> None:
        for profile_id, context in self.contexts.items():
            with self.subTest(profile_id=profile_id):
                plan = MODULE.source_free_request_plan(context)
                self.assertEqual(plan["request_count"], 9)
                self.assertEqual(plan["component_freeze_sha256"], context.freeze_sha256)
                self.assertEqual(plan["reviewer_role_count"], 3)
                self.assertFalse(plan["fourth_all_roles_actor_created"])
                self.assertFalse(plan["model_service_contacted"])
                self.assertEqual(
                    {(row["role"], row["repetition"]) for row in plan["requests"]},
                    {
                        (role, repetition)
                        for role in MODULE.ROLE_ORDER
                        for repetition in MODULE.REPETITIONS
                    },
                )

    def test_request_semantics_are_shared_and_model_transport_is_explicit(self) -> None:
        item = MODULE.transport_runtime.inert_canary_item()
        semantic_sets = []
        for context in self.contexts.values():
            semantic_sets.append([
                MODULE.request_semantics(
                    context,
                    item,
                    role=role,
                    repetition=repetition,
                )
                for role in MODULE.ROLE_ORDER
                for repetition in MODULE.REPETITIONS
            ])
            for role in MODULE.ROLE_ORDER:
                request = MODULE.build_rating_request(
                    context,
                    item,
                    role=role,
                    repetition=1,
                )
                self.assertTrue(
                    request["messages"][-1]["content"].endswith(
                        MODULE.OUTPUT_CONSISTENCY_REMINDER
                    )
                )
                self.assertFalse(request["think"])
                self.assertFalse(request["stream"])
                self.assertFalse(request["truncate"])
                self.assertFalse(request["shift"])
                self.assertNotIn("tools", request)
                self.assertEqual(request["options"]["top_k"], 20)
                self.assertEqual(request["options"]["repeat_penalty"], 1)
        self.assertEqual(semantic_sets[0], semantic_sets[1])
        self.assertEqual(semantic_sets[1], semantic_sets[2])
        self.assertEqual(
            len(MODULE.build_rating_request(
                self.contexts["gemma3_4b"],
                item,
                role="researcher",
                repetition=1,
            )["messages"]),
            1,
        )
        self.assertEqual(
            len(MODULE.build_rating_request(
                self.contexts["llama3_1_8b"],
                item,
                role="researcher",
                repetition=1,
            )["messages"]),
            2,
        )

    def test_same_logical_matrix_same_scores_but_profile_bound_commitments(self) -> None:
        results = {}
        fixtures = {}
        seals = {}
        for profile_id, context in self.contexts.items():
            target = MODULE.v1_core.TARGET_TO_FLAG[
                MODULE.v1_core.ERROR_FAMILIES[0]
            ]
            value = fixture_input(
                context,
                flags={
                    (0, "researcher", 1): [target],
                    (0, "researcher", 2): [target],
                },
            )
            fixture = MODULE.validate_fixture(context, value)
            result = MODULE.aggregate_all_roles(context, fixture)
            fixtures[profile_id] = fixture
            results[profile_id] = result
            seals[profile_id] = MODULE.build_result_seal(context, fixture, result)
        summaries = [
            (row["primary_summary"], row["stability_summary"])
            for row in results.values()
        ]
        self.assertEqual(summaries[0], summaries[1])
        self.assertEqual(summaries[1], summaries[2])
        self.assertEqual(len({row.input_sha256 for row in fixtures.values()}), 3)
        self.assertEqual(len({row.fixture_matrix_sha256 for row in fixtures.values()}), 3)
        self.assertEqual(len({row["result_sha256"] for row in seals.values()}), 3)
        self.assertTrue(all(not row["manuscript_eligible"] for row in seals.values()))

    def test_cross_profile_fixture_result_and_seal_replay_are_rejected(self) -> None:
        qwen = self.contexts["qwen3_8b"]
        llama = self.contexts["llama3_1_8b"]
        fixture = MODULE.validate_fixture(qwen, fixture_input(qwen))
        result = MODULE.aggregate_all_roles(qwen, fixture)
        seal = MODULE.build_result_seal(qwen, fixture, result)
        with self.assertRaisesRegex(
            MODULE.ProfileAllRolesError,
            "fixture_context_profile_mismatch",
        ):
            MODULE.aggregate_all_roles(llama, fixture)
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "profile_fixture_schema_invalid"):
            MODULE.validate_fixture(llama, fixture.value())
        with self.assertRaisesRegex(
            MODULE.ProfileAllRolesError,
            "fixture_context_profile_mismatch",
        ):
            MODULE.validate_result_seal(llama, fixture, result, seal)

    def test_foreign_response_model_is_rejected_for_every_ordered_profile_pair(self) -> None:
        for own_id, own_context in self.contexts.items():
            for foreign_id, foreign_context in self.contexts.items():
                if own_id == foreign_id:
                    continue
                with self.subTest(own=own_id, foreign=foreign_id):
                    with self.assertRaisesRegex(
                        MODULE.ProfileAllRolesError,
                        "rating_response_invalid",
                    ):
                        MODULE.parse_rating_response(
                            own_context,
                            response(
                                own_context,
                                model_id=foreign_context.profile()["model_id"],
                            ),
                        )

    def test_response_parser_rejects_duplicate_keys_bad_envelope_and_invalid_rating(self) -> None:
        context = self.contexts["qwen3_8b"]
        duplicate = response(context)
        duplicate["message"]["content"] = '{"a":1,"a":2}'
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "rating_response_invalid"):
            MODULE.parse_rating_response(context, duplicate)
        message_array = response(context)
        message_array["message"] = []
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "rating_response_invalid"):
            MODULE.parse_rating_response(context, message_array)
        thinking = response(context)
        thinking["message"]["thinking"] = "hidden"
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "rating_response_invalid"):
            MODULE.parse_rating_response(context, thinking)
        invalid = response(context)
        bad_rating = full_rating()
        bad_rating["confidence"] = 6
        invalid["message"]["content"] = json.dumps(bad_rating)
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "rating_response_invalid"):
            MODULE.parse_rating_response(context, invalid)
        contradictory = full_rating()
        contradictory["cannot_judge"] = ["scope_calibration"]
        MODULE.jsonschema.Draft202012Validator(
            context.assets()["shared_rating_transport_schema"]
        ).validate(contradictory)
        invalid["message"]["content"] = json.dumps(contradictory)
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "rating_response_invalid"):
            MODULE.parse_rating_response(context, invalid)

    def test_preflight_checks_only_selected_model_and_never_falls_back(self) -> None:
        context = self.contexts["gemma3_4b"]
        profile = context.profile()
        with (
            mock.patch.object(MODULE, "_verify_model_blob") as verify_blob,
            mock.patch.object(
                MODULE.transport_runtime,
                "api_json",
                side_effect=[
                    {"version": "0.18.0"},
                    {"models": [{
                        "name": profile["model_id"],
                        "digest": profile["local_manifest_file_sha256"],
                    }]},
                ],
            ) as api,
        ):
            observed = MODULE.preflight_service(context)
        self.assertEqual(observed["model_profile_id"], "gemma3_4b")
        self.assertEqual(observed["component_freeze_sha256"], context.freeze_sha256)
        self.assertEqual(observed["model_id"], "gemma3:4b")
        self.assertEqual(api.call_count, 2)
        verify_blob.assert_called_once()

        with mock.patch.object(
            MODULE.transport_runtime,
            "api_json",
            side_effect=[
                {"version": "0.18.0"},
                {"models": [{
                    "name": "qwen3:8b",
                    "digest": self.contexts["qwen3_8b"].profile()[
                        "local_manifest_file_sha256"
                    ],
                }]},
            ],
        ):
            with self.assertRaisesRegex(
                MODULE.ProfileAllRolesError,
                "selected_model_not_uniquely_available",
            ):
                MODULE.preflight_service(context)

    def test_model_blob_drift_blocks_selected_profile_preflight(self) -> None:
        context = self.contexts["llama3_1_8b"]
        profile = context.profile()
        with (
            mock.patch.object(
                MODULE.transport_runtime,
                "api_json",
                side_effect=[
                    {"version": "0.18.0"},
                    {"models": [{
                        "name": profile["model_id"],
                        "digest": profile["local_manifest_file_sha256"],
                    }]},
                ],
            ) as api,
            mock.patch.object(
                MODULE,
                "_verify_model_blob",
                side_effect=MODULE.ProfileAllRolesError("llama_model_blob_hash_drift"),
            ),
        ):
            with self.assertRaisesRegex(
                MODULE.ProfileAllRolesError,
                "llama_model_blob_hash_drift",
            ):
                MODULE.preflight_service(context)
        self.assertEqual(api.call_count, 2)

    def test_invalid_canary_response_stops_without_retry_or_fallback(self) -> None:
        context = self.contexts["gemma3_4b"]
        contradictory = full_rating()
        contradictory["cannot_judge"] = ["scope_calibration"]
        invalid = response(context)
        invalid["message"]["content"] = json.dumps(contradictory)
        baseline = {
            "status": "passed",
            "model_profile_id": "gemma3_4b",
        }
        with (
            mock.patch.object(MODULE, "preflight_service", return_value=baseline),
            mock.patch.object(
                MODULE.transport_runtime,
                "api_json",
                return_value=invalid,
            ) as api,
        ):
            with self.assertRaisesRegex(
                MODULE.ProfileAllRolesError,
                "rating_response_invalid",
            ):
                MODULE.run_source_free_canary(context)
        self.assertEqual(api.call_count, 1)

    def test_selected_profile_canary_never_reloads_qwen_default(self) -> None:
        context = self.contexts["llama3_1_8b"]
        profile = context.profile()
        chat_models = []

        def fake_api(
            config: dict,
            path: str,
            *,
            payload: dict | None = None,
            timeout: int = 30,
        ) -> dict:
            del config, timeout
            if path == "/api/version":
                return {"version": "0.18.0"}
            if path == "/api/tags":
                return {"models": [{
                    "name": profile["model_id"],
                    "digest": profile["local_manifest_file_sha256"],
                }]}
            self.assertEqual(path, "/api/chat")
            self.assertIsNotNone(payload)
            chat_models.append(payload["model"])
            return response(context)

        with (
            mock.patch.object(MODULE, "_verify_model_blob"),
            mock.patch.object(MODULE.transport_runtime, "api_json", side_effect=fake_api),
        ):
            report = MODULE.run_source_free_canary(context)
        self.assertEqual(report["model_profile_id"], "llama3_1_8b")
        self.assertEqual(report["component_freeze_sha256"], context.freeze_sha256)
        self.assertEqual(chat_models, ["llama3.1:8b"] * 3)
        self.assertFalse(report["fallback_used"])

    def test_profile_and_seal_tampering_are_rejected(self) -> None:
        context = self.contexts["qwen3_8b"]
        fixture = MODULE.validate_fixture(context, fixture_input(context))
        result = MODULE.aggregate_all_roles(context, fixture)
        seal = MODULE.build_result_seal(context, fixture, result)
        self.assertEqual(result["component_freeze_sha256"], context.freeze_sha256)
        result_schema = MODULE._profile_schema(
            context.assets()["all_roles_result_schema_v1"], context, "result"
        )
        seal_schema = MODULE._profile_schema(
            context.assets()["all_roles_result_seal_schema_v1"], context, "seal"
        )
        for field in ("component_freeze_sha256", "model_profile_sha256"):
            changed_result = copy.deepcopy(result)
            changed_result[field] = "0" * 64
            with self.assertRaises(MODULE.jsonschema.ValidationError):
                MODULE.jsonschema.Draft202012Validator(result_schema).validate(
                    changed_result
                )
        for field in ("freeze_sha256", "model_profile_sha256"):
            schema_invalid_seal = copy.deepcopy(seal)
            schema_invalid_seal[field] = "0" * 64
            with self.assertRaises(MODULE.jsonschema.ValidationError):
                MODULE.jsonschema.Draft202012Validator(seal_schema).validate(
                    schema_invalid_seal
                )
        forged_context = copy.deepcopy(context)
        object.__setattr__(forged_context, "model_profile_sha256", "0" * 64)
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "model_context_not_active"):
            MODULE.aggregate_all_roles(forged_context, fixture)
        changed_seal = copy.deepcopy(seal)
        changed_seal["model_profile_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.ProfileAllRolesError, "profile_result_seal_invalid"):
            MODULE.validate_result_seal(context, fixture, result, changed_seal)

    def test_coherent_result_forgery_is_rejected_by_profile_fixture_binding(self) -> None:
        context = self.contexts["qwen3_8b"]
        target = MODULE.v1_core.TARGET_TO_FLAG[MODULE.v1_core.ERROR_FAMILIES[0]]
        fixture = MODULE.validate_fixture(
            context,
            fixture_input(context, flags={(0, "researcher", 1): [target]}),
        )
        result = MODULE.aggregate_all_roles(context, fixture)
        forged = copy.deepcopy(result)
        item = forged["items"][0]
        item["primary_role_flags"]["researcher"] = []
        item["primary_role_hits"]["researcher"] = False
        item["primary_all_roles_flags"] = []
        item["primary_all_roles_hit"] = False
        forged["primary_summary"] = {"tp": 0, "fn": 1, "n": 1, "recall": 0.0}
        with self.assertRaisesRegex(
            MODULE.ProfileAllRolesError,
            "result_not_derived_from_profile_fixture",
        ):
            MODULE.build_result_seal(context, fixture, forged)

    def test_run_blocks_for_every_profile_before_service_dataset_or_storage(self) -> None:
        for profile_id in MODULE.EXPECTED_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                with (
                    mock.patch.object(
                        MODULE.transport_runtime,
                        "api_json",
                        side_effect=AssertionError("service contacted"),
                    ),
                    mock.patch.object(
                        MODULE.transport_runtime,
                        "read_regular_bytes",
                        wraps=MODULE.transport_runtime.read_regular_bytes,
                    ) as reads,
                    mock.patch.object(
                        sys,
                        "argv",
                        [str(SCRIPT), "--model-profile", profile_id, "run"],
                    ),
                    mock.patch("builtins.print"),
                ):
                    self.assertEqual(MODULE.main(), 2)
                self.assertFalse(any(
                    "/dataset/" in str(call.args[0])
                    or "/Storage/" in str(call.args[0])
                    or str(call.args[0]).endswith(".jsonl")
                    for call in reads.call_args_list
                ))


if __name__ == "__main__":
    unittest.main()
