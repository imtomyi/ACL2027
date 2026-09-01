#!/usr/bin/env python3
"""Source-free tests for the Qwen3 All roles component."""

from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/qwen3_all_roles_freeze.json"
SPEC = importlib.util.spec_from_file_location("qwen3_all_roles_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_full_rating() -> dict:
    return {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 4,
        "voice_boundary_preservation": 4,
        "scope_calibration": 4,
        "cannot_judge": [],
        "confidence": 4,
        "disposition": "accept",
        "requested_expertise": "none",
        "serious_error_flags": [],
        "rationale": "The inert claim is limited to the displayed inert evidence.",
    }


def ollama_response(rating: dict, *, model: str = "qwen3:8b") -> dict:
    return {
        "model": model,
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(rating)},
        "prompt_eval_count": 1200,
        "eval_count": 80,
    }


def observation(
    role: str,
    repetition: int,
    *,
    item_hash: str,
    observation_index: int,
    flags: list[str] | None = None,
    cannot_judge: list[str] | None = None,
    status: str = "valid",
) -> dict:
    actor = MODULE.CONFIG_FOR_TESTS["reviewer_actors"][role]
    role_prompt = MODULE.CONFIG_FOR_TESTS["roles"][role]["prompt"]
    flags = flags or []
    cannot_judge = cannot_judge or []
    if cannot_judge:
        disposition = "escalate"
    elif flags:
        disposition = "revise"
    else:
        disposition = "accept"
    return {
        "actor_id": actor["actor_id"],
        "model_id": "qwen3:8b",
        "model_snapshot_sha256": actor["local_manifest_file_sha256"],
        "role_prompt_sha256": role_prompt["sha256"],
        "rating_repetition": repetition,
        "evaluator_item_sha256": item_hash,
        "observation_status": status,
        "rating": (
            {
                "disposition": disposition,
                "cannot_judge": cannot_judge,
                "serious_error_flags": flags,
            }
            if status == "valid"
            else None
        ),
        "fixture_observation_sha256": f"{observation_index:064x}",
    }


def analysis_input(
    *,
    cell_flags: dict[tuple[int, str, int], list[str]] | None = None,
    cell_status: dict[tuple[int, str, int], str] | None = None,
    cell_cannot_judge: dict[tuple[int, str, int], list[str]] | None = None,
    item_count: int = 1,
) -> dict:
    cell_flags = cell_flags or {}
    cell_status = cell_status or {}
    cell_cannot_judge = cell_cannot_judge or {}
    items = []
    observation_index = 1
    for item_index in range(item_count):
        family = MODULE.ERROR_FAMILIES[item_index % len(MODULE.ERROR_FAMILIES)]
        required_flag = MODULE.TARGET_TO_FLAG[family]
        item_hash = f"{1000 + item_index:064x}"
        role_observations = {}
        for role in MODULE.ROLE_ORDER:
            role_observations[role] = []
            for repetition in MODULE.REPETITIONS:
                key = (item_index, role, repetition)
                role_observations[role].append(
                    observation(
                        role,
                        repetition,
                        item_hash=item_hash,
                        observation_index=observation_index,
                        flags=cell_flags.get(key),
                        cannot_judge=cell_cannot_judge.get(key),
                        status=cell_status.get(key, "valid"),
                    )
                )
                observation_index += 1
        items.append(
            {
                "item_id": f"DJI_{item_index + 1:016x}",
                "cluster_id": f"CLUSTER_{item_index + 1}",
                "error_family": family,
                "required_flag": required_flag,
                "evaluator_item_sha256": item_hash,
                "role_observations": role_observations,
            }
        )
    snapshot = MODULE.CONFIG_FOR_TESTS["reviewer_actors"]["researcher"][
        "local_manifest_file_sha256"
    ]
    value = {
        "input_schema_version": "rq2-all-roles-input-v1",
        "study_id": "source-free-software-test",
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
            "model_id": "qwen3:8b",
            "model_snapshot_sha256": snapshot,
        },
        "items": items,
    }
    return MODULE.seal_fixture_observations(value)


class Qwen3AllRolesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = MODULE.runtime.load_json(CONFIG)
        MODULE.CONFIG_FOR_TESTS = cls.config
        cls.assets = MODULE.validate_freeze(cls.config)
        cls.context = MODULE.load_frozen_context()

    def aggregate(self, value: dict) -> dict:
        fixture = MODULE.validate_fixture(value, self.context)
        return MODULE.aggregate_all_roles(fixture, self.context)

    def test_freeze_binds_three_qwen_roles_and_no_fourth_actor(self) -> None:
        self.assertEqual(tuple(self.config["reviewer_actors"]), MODULE.ROLE_ORDER)
        self.assertTrue(
            all(
                actor["model_id"] == "qwen3:8b"
                for actor in self.config["reviewer_actors"].values()
            )
        )
        self.assertNotIn("all_roles", self.config["reviewer_actors"])
        self.assertNotIn("all_roles", self.config["roles"])
        self.assertFalse(self.config["source_bearing_execution_allowed"])
        self.assertFalse(self.config["all_roles_real_derivation_allowed"])

    def test_lane_matches_warrantroute_canonical_identity(self) -> None:
        self.assertEqual(
            analysis_input()["lane"],
            {
                "corpus": "dreaddit",
                "source_split": "official_train",
                "internal_lane": "development_train",
                "experimental_role": "development_diagnostic",
                "heldout": False,
            },
        )

    def test_request_plan_is_exact_three_by_three_hardened_matrix(self) -> None:
        plan = MODULE.source_free_request_plan(self.config, self.assets)
        self.assertEqual(plan["request_count"], 9)
        self.assertEqual(plan["reviewer_role_count"], 3)
        self.assertFalse(plan["fourth_all_roles_actor_created"])
        self.assertEqual(
            len({row["evaluator_item_sha256"] for row in plan["requests"]}),
            1,
        )
        self.assertEqual(
            [row["seed"] for row in plan["requests"][:3]],
            [2027082601, 2027082602, 2027082603],
        )
        item = MODULE.runtime.inert_canary_item()
        for role in MODULE.ROLE_ORDER:
            request = MODULE.build_rating_request(
                self.config,
                self.assets,
                item,
                role=role,
                repetition=1,
            )
            self.assertEqual(request["model"], "qwen3:8b")
            self.assertFalse(request["think"])
            self.assertFalse(request["truncate"])
            self.assertFalse(request["shift"])
            self.assertNotIn("tools", request)
            self.assertEqual(request["format"], self.assets["shared_rating_transport_schema"])
            self.assertNotEqual(request["format"], self.assets["shared_rating_schema"])

    def test_primary_is_or_across_roles_and_overlaps_count_once(self) -> None:
        target = MODULE.TARGET_TO_FLAG[MODULE.ERROR_FAMILIES[0]]
        for role in MODULE.ROLE_ORDER:
            result = self.aggregate(
                analysis_input(cell_flags={(0, role, 1): [target]})
            )
            self.assertTrue(result["items"][0]["primary_all_roles_hit"])
            self.assertTrue(result["items"][0]["primary_role_hits"][role])
            self.assertEqual(result["primary_summary"], {"tp": 1, "fn": 0, "n": 1, "recall": 1.0})
        all_hit = {
            (0, role, 1): [target] for role in MODULE.ROLE_ORDER
        }
        result = self.aggregate(analysis_input(cell_flags=all_hit))
        self.assertEqual(result["primary_summary"]["tp"], 1)
        self.assertEqual(result["primary_summary"]["n"], 1)

    def test_exact_target_flag_controls_detection(self) -> None:
        target = MODULE.TARGET_TO_FLAG[MODULE.ERROR_FAMILIES[0]]
        wrong = "wrong_attribution"
        miss = self.aggregate(
            analysis_input(cell_flags={(0, "researcher", 1): [wrong]})
        )
        self.assertFalse(miss["items"][0]["primary_all_roles_hit"])
        hit = self.aggregate(
            analysis_input(cell_flags={(0, "researcher", 1): [wrong, target]})
        )
        self.assertTrue(hit["items"][0]["primary_all_roles_hit"])

    def test_repetitions_do_not_rescue_primary_and_stability_reduces_within_role(self) -> None:
        target = MODULE.TARGET_TO_FLAG[MODULE.ERROR_FAMILIES[0]]
        same_role = self.aggregate(
            analysis_input(
                cell_flags={
                    (0, "researcher", 2): [target],
                    (0, "researcher", 3): [target],
                }
            )
        )
        self.assertFalse(same_role["items"][0]["primary_all_roles_hit"])
        self.assertTrue(same_role["items"][0]["stability_all_roles_hit"])
        split_roles = self.aggregate(
            analysis_input(
                cell_flags={
                    (0, "researcher", 1): [target],
                    (0, "domain", 2): [target],
                }
            )
        )
        self.assertTrue(split_roles["items"][0]["primary_all_roles_hit"])
        self.assertFalse(split_roles["items"][0]["stability_all_roles_hit"])

    def test_failure_cannot_judge_and_explicit_missing_are_empty_role_flags(self) -> None:
        target = MODULE.TARGET_TO_FLAG[MODULE.ERROR_FAMILIES[0]]
        result = self.aggregate(
            analysis_input(
                cell_flags={
                    (0, "researcher", 1): [target],
                    (0, "domain", 1): [target],
                },
                cell_status={(0, "researcher", 1): "missing"},
                cell_cannot_judge={
                    (0, "domain", 1): ["scope_calibration"]
                },
            )
        )
        self.assertFalse(result["items"][0]["primary_all_roles_hit"])
        self.assertEqual(result["primary_summary"], {"tp": 0, "fn": 1, "n": 1, "recall": 0.0})
        rescued_by_other_role = self.aggregate(
            analysis_input(
                cell_flags={(0, "qualitative_methods", 1): [target]},
                cell_status={(0, "researcher", 1): "terminal_failure"},
            )
        )
        self.assertTrue(rescued_by_other_role["items"][0]["primary_all_roles_hit"])

    def test_absent_role_or_repetition_is_malformed_but_explicit_missing_is_complete(self) -> None:
        missing_role = analysis_input()
        del missing_role["items"][0]["role_observations"]["domain"]
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(missing_role)
        missing_repetition = analysis_input()
        missing_repetition["items"][0]["role_observations"]["researcher"].pop()
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(missing_repetition)
        explicit = analysis_input(cell_status={(0, "researcher", 1): "missing"})
        self.assertEqual(self.aggregate(explicit)["primary_summary"]["n"], 1)

    def test_duplicate_items_evaluator_hashes_and_observation_hashes_are_rejected(self) -> None:
        duplicate_item = analysis_input(item_count=2)
        duplicate_item["items"][1]["item_id"] = duplicate_item["items"][0]["item_id"]
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_item_duplicate"):
            self.aggregate(duplicate_item)
        duplicate_evaluator = analysis_input(item_count=2)
        duplicate_evaluator["items"][1]["evaluator_item_sha256"] = duplicate_evaluator[
            "items"
        ][0]["evaluator_item_sha256"]
        for role in MODULE.ROLE_ORDER:
            for row in duplicate_evaluator["items"][1]["role_observations"][role]:
                row["evaluator_item_sha256"] = duplicate_evaluator["items"][1][
                    "evaluator_item_sha256"
                ]
        with self.assertRaisesRegex(MODULE.AllRolesError, "evaluator_item_duplicate"):
            self.aggregate(duplicate_evaluator)
        duplicate_observation = analysis_input()
        duplicate_observation["items"][0]["role_observations"]["domain"][0][
            "fixture_observation_sha256"
        ] = duplicate_observation["items"][0]["role_observations"]["researcher"][0][
            "fixture_observation_sha256"
        ]
        with self.assertRaisesRegex(MODULE.AllRolesError, "observation_hash_duplicate"):
            self.aggregate(duplicate_observation)

    def test_observation_commitments_bind_rating_item_role_and_repetition(self) -> None:
        value = analysis_input()
        all_hashes = [
            observation["fixture_observation_sha256"]
            for role in MODULE.ROLE_ORDER
            for observation in value["items"][0]["role_observations"][role]
        ]
        self.assertEqual(len(all_hashes), len(set(all_hashes)))
        changed_rating = copy.deepcopy(value)
        rating = changed_rating["items"][0]["role_observations"]["researcher"][0][
            "rating"
        ]
        rating["disposition"] = "revise"
        rating["serious_error_flags"] = ["unsupported_inference"]
        with self.assertRaisesRegex(MODULE.AllRolesError, "observation_hash_mismatch"):
            self.aggregate(changed_rating)

    def test_projection_rejects_source_like_study_id_and_inconsistent_cannot_judge(self) -> None:
        source_like_id = analysis_input()
        source_like_id["study_id"] = "raw source sentence"
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(source_like_id)

        inconsistent = analysis_input()
        rating = inconsistent["items"][0]["role_observations"]["researcher"][0][
            "rating"
        ]
        rating["cannot_judge"] = ["scope_calibration"]
        rating["disposition"] = "accept"
        inconsistent = MODULE.seal_fixture_observations(inconsistent)
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(inconsistent)

    def test_validated_fixture_is_immutable_and_external_references_stay_unverified(self) -> None:
        value = analysis_input()
        fixture = MODULE.validate_fixture(value, self.context)
        before = MODULE.aggregate_all_roles(fixture, self.context)
        value["external_study_references"]["review_matrix_seal_sha256"] = "d" * 64
        value["items"][0]["role_observations"]["researcher"][0]["rating"] = None
        after = MODULE.aggregate_all_roles(fixture, self.context)
        self.assertEqual(before, after)

        reference_variant = analysis_input()
        reference_variant["external_study_references"][
            "review_matrix_seal_sha256"
        ] = "d" * 64
        variant_fixture = MODULE.validate_fixture(reference_variant, self.context)
        variant_result = MODULE.aggregate_all_roles(variant_fixture, self.context)
        self.assertNotEqual(fixture.input_sha256, variant_fixture.input_sha256)
        self.assertEqual(
            fixture.fixture_matrix_sha256,
            variant_fixture.fixture_matrix_sha256,
        )
        self.assertFalse(variant_result["external_references_verified"])

    def test_repetition_actor_prompt_snapshot_and_item_hash_drift_are_rejected(self) -> None:
        reordered = analysis_input()
        observations = reordered["items"][0]["role_observations"]["researcher"]
        observations[0], observations[1] = observations[1], observations[0]
        with self.assertRaisesRegex(MODULE.AllRolesError, "role_repetition_order_invalid"):
            self.aggregate(reordered)
        actor = analysis_input()
        actor["items"][0]["role_observations"]["domain"][0]["actor_id"] = "changed"
        with self.assertRaisesRegex(MODULE.AllRolesError, "reviewer_actor_drift"):
            self.aggregate(actor)
        prompt = analysis_input()
        prompt["items"][0]["role_observations"]["researcher"][0][
            "role_prompt_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(MODULE.AllRolesError, "reviewer_prompt_drift"):
            self.aggregate(prompt)
        snapshot = analysis_input()
        snapshot["items"][0]["role_observations"]["researcher"][0][
            "model_snapshot_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(MODULE.AllRolesError, "reviewer_snapshot_drift"):
            self.aggregate(snapshot)
        item_hash = analysis_input()
        item_hash["items"][0]["role_observations"]["researcher"][0][
            "evaluator_item_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(MODULE.AllRolesError, "evaluator_item_hash_drift"):
            self.aggregate(item_hash)

    def test_empty_failed_qualification_bad_lane_and_route_field_fail_closed(self) -> None:
        empty = analysis_input()
        empty["items"] = []
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(empty)
        failed = analysis_input()
        failed["fixture_assumptions"]["qualification_gate_passed"] = False
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(failed)
        real_projection = analysis_input()
        real_projection["contains_real_observations"] = True
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(real_projection)
        wrong_lane = analysis_input()
        wrong_lane["lane"]["source_split"] = "official_test"
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(wrong_lane)
        routed = analysis_input()
        routed["items"][0]["route"] = "both"
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_input_schema_invalid"):
            self.aggregate(routed)

    def test_result_links_observations_and_seal_rejects_tampering(self) -> None:
        target = MODULE.TARGET_TO_FLAG[MODULE.ERROR_FAMILIES[0]]
        value = analysis_input(cell_flags={(0, "researcher", 1): [target]})
        fixture = MODULE.validate_fixture(value, self.context)
        result = MODULE.aggregate_all_roles(fixture, self.context)
        hashes = result["items"][0]["fixture_observation_hashes"]
        self.assertEqual(set(hashes), set(MODULE.ROLE_ORDER))
        self.assertTrue(all(len(hashes[role]) == 3 for role in MODULE.ROLE_ORDER))
        seal = MODULE.build_result_seal(fixture, result, self.context)
        self.assertEqual(seal["item_count"], 1)
        self.assertFalse(seal["manuscript_eligible"])
        self.assertFalse(seal["external_references_verified"])
        self.assertEqual(
            seal["freeze_sha256"],
            MODULE.sha256_bytes(MODULE.runtime.read_regular_bytes(CONFIG)),
        )
        self.assertFalse(result["primary_interval"]["estimable"])
        self.assertEqual(
            result["primary_interval"]["reason"],
            "fewer_than_minimum_independent_clusters",
        )
        arithmetic = copy.deepcopy(result)
        arithmetic["primary_summary"]["tp"] = 0
        with self.assertRaisesRegex(
            MODULE.AllRolesError,
            "result_not_derived_from_bound_fixture",
        ):
            MODULE.build_result_seal(fixture, arithmetic, self.context)
        union = copy.deepcopy(result)
        union["items"][0]["primary_all_roles_hit"] = False
        with self.assertRaisesRegex(
            MODULE.AllRolesError,
            "result_not_derived_from_bound_fixture",
        ):
            MODULE.build_result_seal(fixture, union, self.context)
        role_hit = copy.deepcopy(result)
        role_hit["items"][0]["primary_role_hits"]["researcher"] = False
        with self.assertRaisesRegex(
            MODULE.AllRolesError,
            "result_not_derived_from_bound_fixture",
        ):
            MODULE.build_result_seal(fixture, role_hit, self.context)
        coherent_forgery = copy.deepcopy(result)
        forged_item = coherent_forgery["items"][0]
        forged_item["primary_role_flags"]["researcher"] = []
        forged_item["primary_role_hits"]["researcher"] = False
        forged_item["primary_all_roles_flags"] = []
        forged_item["primary_all_roles_hit"] = False
        coherent_forgery["primary_summary"] = {
            "tp": 0,
            "fn": 1,
            "n": 1,
            "recall": 0.0,
        }
        MODULE.validate_all_roles_result(
            coherent_forgery,
            schema=self.context.result_schema(),
        )
        with self.assertRaisesRegex(
            MODULE.AllRolesError,
            "result_not_derived_from_bound_fixture",
        ):
            MODULE.build_result_seal(fixture, coherent_forgery, self.context)
        changed_seal = copy.deepcopy(seal)
        changed_seal["item_count"] = 2
        with self.assertRaisesRegex(MODULE.AllRolesError, "result_seal_invalid"):
            MODULE.validate_result_seal(
                fixture,
                result,
                changed_seal,
                self.context,
            )

    def test_cluster_bootstrap_is_fixed_and_marks_degenerate_intervals(self) -> None:
        flags = {}
        for item_index in (0, 1):
            family = MODULE.ERROR_FAMILIES[item_index]
            flags[(item_index, "researcher", 1)] = [
                MODULE.TARGET_TO_FLAG[family]
            ]
        result = self.aggregate(analysis_input(cell_flags=flags, item_count=5))
        interval = result["primary_interval"]
        self.assertTrue(interval["estimable"])
        self.assertEqual(interval["resamples"], 10000)
        self.assertEqual(interval["seed"], 20270826)
        self.assertLessEqual(interval["lower"], result["primary_summary"]["recall"])
        self.assertGreaterEqual(interval["upper"], result["primary_summary"]["recall"])
        self.assertFalse(result["stability_interval"]["estimable"])
        self.assertEqual(
            result["stability_interval"]["reason"],
            "degenerate_bootstrap_distribution",
        )
        repeated = MODULE.cluster_bootstrap_interval(
            result["items"],
            hit_key="primary_all_roles_hit",
            bootstrap=result["bootstrap"],
        )
        self.assertEqual(interval, repeated)

    def test_freeze_identity_rule_path_and_hash_drift_fail_closed(self) -> None:
        actor = copy.deepcopy(self.config)
        actor["reviewer_actors"]["researcher"]["actor_id"] = ""
        with self.assertRaisesRegex(MODULE.AllRolesError, "reviewer_actor_id_drift"):
            MODULE.validate_freeze(actor)
        fourth = copy.deepcopy(self.config)
        fourth["reviewer_actors"]["all_roles"] = copy.deepcopy(
            fourth["reviewer_actors"]["researcher"]
        )
        with self.assertRaisesRegex(MODULE.AllRolesError, "reviewer_actor_order_invalid"):
            MODULE.validate_freeze(fourth)
        rule = copy.deepcopy(self.config)
        rule["all_roles_rule"]["primary_operation"] = "majority_vote"
        with self.assertRaisesRegex(MODULE.AllRolesError, "all_roles_rule_invalid"):
            MODULE.validate_freeze(rule)
        path = copy.deepcopy(self.config)
        path["assets"]["runtime"]["file"] = path["assets"]["prompt_limit_guard"]["file"]
        with self.assertRaisesRegex(MODULE.AllRolesError, "runtime_path_drift"):
            MODULE.validate_freeze(path)
        hashed = copy.deepcopy(self.config)
        hashed["roles"]["researcher"]["prompt"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.AllRolesError, "researcher_prompt_hash_drift"):
            MODULE.validate_freeze(hashed)

    def test_runtime_rejects_private_keys_and_invalid_responses(self) -> None:
        with self.assertRaisesRegex(
            MODULE.runtime.AllRolesRuntimeError,
            "blinded_item_contains_private_key",
        ):
            MODULE.runtime.validate_evaluator_item(
                {"safe": {"truth": "hidden"}},
                {"type": "object"},
            )
        wrong_model = ollama_response(valid_full_rating(), model="other:8b")
        with self.assertRaisesRegex(
            MODULE.runtime.ResponseValidationError,
            "rating_response_invalid",
        ):
            MODULE.runtime.parse_rating_response(
                wrong_model,
                expected_model="qwen3:8b",
                rating_schema=self.assets["shared_rating_schema"],
                config=self.config,
            )

    def test_preflight_rejects_version_duplicate_model_and_digest_drift(self) -> None:
        valid_tags = {
            "models": [
                {
                    "name": "qwen3:8b",
                    "digest": MODULE.EXPECTED_MODEL_MANIFEST_SHA256,
                }
            ]
        }
        with mock.patch.object(
            MODULE.runtime,
            "api_json",
            side_effect=[{"version": "wrong"}, valid_tags],
        ):
            with self.assertRaisesRegex(
                MODULE.runtime.AllRolesRuntimeError,
                "ollama_version_drift",
            ):
                MODULE.runtime.preflight_service(self.config)
        with mock.patch.object(
            MODULE.runtime,
            "api_json",
            side_effect=[{"version": "0.18.0"}, {"models": valid_tags["models"] * 2}],
        ):
            with self.assertRaisesRegex(
                MODULE.runtime.AllRolesRuntimeError,
                "qwen_model_not_uniquely_available",
            ):
                MODULE.runtime.preflight_service(self.config)
        wrong_digest = copy.deepcopy(valid_tags)
        wrong_digest["models"][0]["digest"] = "0" * 64
        with mock.patch.object(
            MODULE.runtime,
            "api_json",
            side_effect=[{"version": "0.18.0"}, wrong_digest],
        ):
            with self.assertRaisesRegex(
                MODULE.runtime.AllRolesRuntimeError,
                "qwen_model_digest_drift",
            ):
                MODULE.runtime.preflight_service(self.config)

    def test_canary_accepts_only_a_frozen_role(self) -> None:
        self.assertEqual(
            set(inspect.signature(MODULE._post_source_free_role_canary).parameters),
            {"role"},
        )
        with self.assertRaisesRegex(MODULE.AllRolesError, "canary_role_not_frozen"):
            MODULE._post_source_free_role_canary("all_roles")

    def test_source_bearing_run_blocks_before_service_or_data_access(self) -> None:
        with (
            mock.patch.object(
                MODULE,
                "_post_source_free_role_canary",
                side_effect=AssertionError("service contacted"),
            ),
            mock.patch.object(
                MODULE.runtime,
                "read_regular_bytes",
                wraps=MODULE.runtime.read_regular_bytes,
            ) as reads,
            mock.patch.object(sys, "argv", [str(SCRIPT), "run"]),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(MODULE.main(), 2)
        self.assertFalse(
            any(
                "/dataset/" in str(call.args[0])
                or "/Storage/" in str(call.args[0])
                or str(call.args[0]).endswith(".jsonl")
                for call in reads.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
