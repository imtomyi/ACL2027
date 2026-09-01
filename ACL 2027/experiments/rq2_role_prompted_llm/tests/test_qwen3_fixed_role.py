#!/usr/bin/env python3
"""Source-free tests for the Qwen3 fixed-role component."""

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
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/qwen3_fixed_role_freeze.json"
SPEC = importlib.util.spec_from_file_location("qwen3_fixed_role_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_rating() -> dict:
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
    *,
    item_hash: str,
    observation_index: int,
    flags: list[str] | None = None,
    cannot_judge: list[str] | None = None,
    status: str = "valid",
) -> dict:
    actor = MODULE.CONFIG_FOR_TESTS["reviewer_actors"][role]
    return {
        "actor_id": actor["actor_id"],
        "model_id": "qwen3:8b",
        "model_snapshot_sha256": actor["local_manifest_file_sha256"],
        "rating_repetition": 1,
        "evaluator_item_sha256": item_hash,
        "observation_status": status,
        "rating": (
            {
                "cannot_judge": cannot_judge or [],
                "serious_error_flags": flags or [],
            }
            if status == "valid"
            else None
        ),
        "observation_sha256": f"{observation_index:064x}",
    }


def development_input(role_hits: dict[str, set[str]] | None = None) -> dict:
    role_hits = role_hits or {role: set() for role in MODULE.ROLE_ORDER}
    items = []
    observation_index = 1
    for index, family in enumerate(MODULE.ERROR_FAMILIES, start=1):
        item_hash = f"{1000 + index:064x}"
        required = MODULE.TARGET_TO_FLAG[family]
        roles = {}
        item_id = f"DJI_{index:016x}"
        for role in MODULE.ROLE_ORDER:
            roles[role] = observation(
                role,
                item_hash=item_hash,
                observation_index=observation_index,
                flags=[required] if family in role_hits.get(role, set()) else [],
            )
            observation_index += 1
        items.append(
            {
                "item_id": item_id,
                "cluster_id": f"CLUSTER_{index}",
                "error_family": family,
                "required_flag": required,
                "evaluator_item_sha256": item_hash,
                "role_observations": roles,
            }
        )
    snapshot = MODULE.CONFIG_FOR_TESTS["reviewer_actors"]["researcher"][
        "local_manifest_file_sha256"
    ]
    return {
        "input_schema_version": "rq2-fixed-role-development-input-v1",
        "study_id": "source-free-software-test",
        "lane": {
            "corpus": "dreaddit",
            "split": "official_train",
            "experimental_role": "development",
            "heldout": False,
        },
        "qualification_gate_passed": True,
        "qualification_seal_sha256": "a" * 64,
        "heldout_accessed_before_selection": False,
        "reviewer_model": {
            "model_id": "qwen3:8b",
            "model_snapshot_sha256": snapshot,
        },
        "primary_repetition": 1,
        "minimum_items_per_family": 1,
        "minimum_independent_clusters_per_family": 1,
        "items": items,
    }


class Qwen3FixedRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = MODULE.runtime.load_json(CONFIG)
        MODULE.CONFIG_FOR_TESTS = cls.config
        cls.assets = MODULE.validate_freeze(cls.config)

    def test_contract_binds_qwen_to_all_three_roles(self) -> None:
        self.assertEqual(tuple(self.config["reviewer_actors"]), MODULE.ROLE_ORDER)
        self.assertTrue(
            all(
                actor["model_id"] == "qwen3:8b"
                for actor in self.config["reviewer_actors"].values()
            )
        )
        self.assertFalse(self.config["fixed_role_selection_allowed"])
        self.assertFalse(self.config["source_bearing_execution_allowed"])

    def test_source_free_plan_builds_nine_hardened_requests(self) -> None:
        plan = MODULE.source_free_request_plan(self.config, self.assets)
        self.assertEqual(plan["request_count"], 9)
        self.assertFalse(plan["source_text_accessed"])
        self.assertFalse(plan["model_service_contacted"])
        self.assertEqual(
            [row["seed"] for row in plan["requests"][:3]],
            [2027082601, 2027082602, 2027082603],
        )
        item = MODULE.runtime.inert_canary_item()
        for role in MODULE.ROLE_ORDER:
            request = MODULE.build_rating_request(
                self.config, self.assets, item, role=role, repetition=1
            )
            self.assertEqual(request["model"], "qwen3:8b")
            self.assertFalse(request["think"])
            self.assertFalse(request["truncate"])
            self.assertFalse(request["shift"])
            self.assertNotIn("tools", request)
            self.assertEqual(request["format"], self.assets["shared_rating_transport_schema"])
            self.assertNotEqual(request["format"], self.assets["shared_rating_schema"])

    def test_unique_winner_uses_repetition_one_micro_recall(self) -> None:
        value = development_input(
            {
                "researcher": {MODULE.ERROR_FAMILIES[0]},
                "qualitative_methods": set(MODULE.ERROR_FAMILIES[:4]),
                "domain": set(MODULE.ERROR_FAMILIES[:2]),
            }
        )
        selection = MODULE.select_fixed_role(value, config=self.config, assets=self.assets)
        self.assertEqual(selection["selected_role"], "qualitative_methods")
        self.assertEqual(selection["development_role_summary"]["qualitative_methods"]["tp"], 4)
        self.assertFalse(selection["reselection_allowed"])

    def test_exact_ties_follow_researcher_methods_domain_order(self) -> None:
        all_tie = development_input(
            {role: {MODULE.ERROR_FAMILIES[0]} for role in MODULE.ROLE_ORDER}
        )
        self.assertEqual(
            MODULE.select_fixed_role(all_tie, config=self.config, assets=self.assets)[
                "selected_role"
            ],
            "researcher",
        )
        methods_domain_tie = development_input(
            {
                "researcher": set(),
                "qualitative_methods": {MODULE.ERROR_FAMILIES[0]},
                "domain": {MODULE.ERROR_FAMILIES[0]},
            }
        )
        self.assertEqual(
            MODULE.select_fixed_role(
                methods_domain_tie, config=self.config, assets=self.assets
            )["selected_role"],
            "qualitative_methods",
        )

    def test_zero_items_and_unbalanced_families_fail_closed(self) -> None:
        empty = development_input()
        empty["items"] = []
        with self.assertRaisesRegex(MODULE.FixedRoleError, "development_input_schema_invalid"):
            MODULE.select_fixed_role(empty, config=self.config, assets=self.assets)
        unbalanced = development_input()
        duplicate = copy.deepcopy(unbalanced["items"][0])
        duplicate["item_id"] = "DJI_00000000000000ff"
        duplicate["cluster_id"] = "CLUSTER_EXTRA"
        duplicate["evaluator_item_sha256"] = "f" * 64
        for index, role in enumerate(MODULE.ROLE_ORDER, start=100):
            duplicate["role_observations"][role]["evaluator_item_sha256"] = "f" * 64
            duplicate["role_observations"][role]["observation_sha256"] = f"{index:064x}"
        unbalanced["items"].append(duplicate)
        with self.assertRaisesRegex(MODULE.FixedRoleError, "development_family_unbalanced"):
            MODULE.select_fixed_role(unbalanced, config=self.config, assets=self.assets)

    def test_duplicate_items_and_observations_are_rejected(self) -> None:
        duplicate_item = development_input()
        duplicate_item["items"][1]["item_id"] = duplicate_item["items"][0]["item_id"]
        with self.assertRaisesRegex(MODULE.FixedRoleError, "development_item_duplicate"):
            MODULE.select_fixed_role(duplicate_item, config=self.config, assets=self.assets)
        duplicate_observation = development_input()
        duplicate_observation["items"][1]["role_observations"]["researcher"][
            "observation_sha256"
        ] = duplicate_observation["items"][0]["role_observations"]["researcher"][
            "observation_sha256"
        ]
        with self.assertRaisesRegex(MODULE.FixedRoleError, "observation_duplicate"):
            MODULE.select_fixed_role(
                duplicate_observation, config=self.config, assets=self.assets
            )
        duplicate_evaluator = development_input()
        duplicate_evaluator["items"][1]["evaluator_item_sha256"] = duplicate_evaluator[
            "items"
        ][0]["evaluator_item_sha256"]
        for role in MODULE.ROLE_ORDER:
            duplicate_evaluator["items"][1]["role_observations"][role][
                "evaluator_item_sha256"
            ] = duplicate_evaluator["items"][1]["evaluator_item_sha256"]
        with self.assertRaisesRegex(MODULE.FixedRoleError, "evaluator_item_duplicate"):
            MODULE.select_fixed_role(
                duplicate_evaluator, config=self.config, assets=self.assets
            )

    def test_invalid_and_cannot_judge_observations_are_misses(self) -> None:
        value = development_input()
        first = value["items"][0]
        target = first["required_flag"]
        first["role_observations"]["researcher"] = observation(
            "researcher", item_hash=first["evaluator_item_sha256"],
            observation_index=500, flags=[target], cannot_judge=["scope_calibration"]
        )
        first["role_observations"]["qualitative_methods"] = observation(
            "qualitative_methods", item_hash=first["evaluator_item_sha256"],
            observation_index=501, status="timeout"
        )
        first["role_observations"]["domain"] = observation(
            "domain", item_hash=first["evaluator_item_sha256"],
            observation_index=502, flags=[target]
        )
        selection = MODULE.select_fixed_role(value, config=self.config, assets=self.assets)
        self.assertEqual(selection["development_role_summary"]["researcher"]["tp"], 0)
        self.assertEqual(selection["development_role_summary"]["qualitative_methods"]["tp"], 0)
        self.assertEqual(selection["development_role_summary"]["domain"]["tp"], 1)

    def test_failed_qualification_or_heldout_input_is_rejected(self) -> None:
        failed = development_input()
        failed["qualification_gate_passed"] = False
        with self.assertRaisesRegex(MODULE.FixedRoleError, "development_input_schema_invalid"):
            MODULE.select_fixed_role(failed, config=self.config, assets=self.assets)
        heldout = development_input()
        heldout["lane"]["split"] = "official_test"
        heldout["lane"]["heldout"] = True
        with self.assertRaisesRegex(MODULE.FixedRoleError, "development_input_schema_invalid"):
            MODULE.select_fixed_role(heldout, config=self.config, assets=self.assets)

    def test_minima_and_reviewer_identity_drift_fail_closed(self) -> None:
        below_minimum = development_input()
        below_minimum["minimum_items_per_family"] = 2
        with self.assertRaisesRegex(MODULE.FixedRoleError, "minimum_items_per_family_not_met"):
            MODULE.select_fixed_role(
                below_minimum, config=self.config, assets=self.assets
            )
        actor_drift = development_input()
        actor_drift["items"][0]["role_observations"]["domain"]["actor_id"] = "changed"
        with self.assertRaisesRegex(MODULE.FixedRoleError, "reviewer_actor_drift"):
            MODULE.select_fixed_role(actor_drift, config=self.config, assets=self.assets)
        snapshot_drift = development_input()
        snapshot_drift["items"][0]["role_observations"]["researcher"][
            "model_snapshot_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(MODULE.FixedRoleError, "reviewer_snapshot_drift"):
            MODULE.select_fixed_role(
                snapshot_drift, config=self.config, assets=self.assets
            )

    def test_runtime_rejects_nested_private_keys_and_bad_responses(self) -> None:
        with self.assertRaisesRegex(
            MODULE.runtime.FixedRoleRuntimeError,
            "blinded_item_contains_private_key",
        ):
            MODULE.runtime.validate_evaluator_item(
                {"safe": {"truth": "hidden"}},
                {"type": "object"},
            )
        wrong_model = ollama_response(valid_rating(), model="other:8b")
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
        no_headroom = ollama_response(valid_rating())
        no_headroom["prompt_eval_count"] = 8000
        with self.assertRaisesRegex(
            MODULE.runtime.ResponseValidationError,
            "rating_response_invalid",
        ):
            MODULE.runtime.parse_rating_response(
                no_headroom,
                expected_model="qwen3:8b",
                rating_schema=self.assets["shared_rating_schema"],
                config=self.config,
            )

    def test_canary_interface_accepts_only_a_frozen_role(self) -> None:
        self.assertEqual(
            set(inspect.signature(MODULE._post_source_free_role_canary).parameters),
            {"role"},
        )
        with self.assertRaisesRegex(MODULE.FixedRoleError, "canary_role_not_frozen"):
            MODULE._post_source_free_role_canary("unfrozen")

    def test_preflight_rejects_version_model_and_digest_drift(self) -> None:
        valid_tags = {
            "models": [
                {
                    "name": "qwen3:8b",
                    "digest": self.config["reviewer_actors"]["researcher"][
                        "local_manifest_file_sha256"
                    ],
                }
            ]
        }
        with mock.patch.object(
            MODULE.runtime,
            "api_json",
            side_effect=[{"version": "wrong"}, valid_tags],
        ):
            with self.assertRaisesRegex(
                MODULE.runtime.FixedRoleRuntimeError, "ollama_version_drift"
            ):
                MODULE.runtime.preflight_service(self.config)
        duplicate_tags = {"models": valid_tags["models"] * 2}
        with mock.patch.object(
            MODULE.runtime,
            "api_json",
            side_effect=[{"version": "0.18.0"}, duplicate_tags],
        ):
            with self.assertRaisesRegex(
                MODULE.runtime.FixedRoleRuntimeError,
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
                MODULE.runtime.FixedRoleRuntimeError, "qwen_model_digest_drift"
            ):
                MODULE.runtime.preflight_service(self.config)

    def test_selection_seal_binds_choice_and_nonzero_denominator(self) -> None:
        selection = MODULE.select_fixed_role(
            development_input(), config=self.config, assets=self.assets
        )
        seal = MODULE.build_selection_seal(
            selection,
            freeze_sha256="b" * 64,
            selection_schema=self.assets["selection_schema"],
        )
        self.assertEqual(seal["selected_role"], "researcher")
        self.assertTrue(seal["sealed_before_heldout_access"])
        self.assertFalse(seal["manuscript_eligible"])
        broken = copy.deepcopy(selection)
        broken["development_role_summary"]["researcher"]["n"] = 0
        with self.assertRaisesRegex(MODULE.FixedRoleError, "selection_record_schema_invalid"):
            MODULE.build_selection_seal(
                broken,
                freeze_sha256="b" * 64,
                selection_schema=self.assets["selection_schema"],
            )
        wrong_winner = copy.deepcopy(selection)
        wrong_winner["selected_role"] = "domain"
        with self.assertRaisesRegex(MODULE.FixedRoleError, "selection_role_not_reproducible"):
            MODULE.build_selection_seal(
                wrong_winner,
                freeze_sha256="b" * 64,
                selection_schema=self.assets["selection_schema"],
            )
        wrong_recall = copy.deepcopy(selection)
        wrong_recall["development_role_summary"]["researcher"]["recall"] = 0.5
        with self.assertRaisesRegex(MODULE.FixedRoleError, "selection_recall_invalid"):
            MODULE.build_selection_seal(
                wrong_recall,
                freeze_sha256="b" * 64,
                selection_schema=self.assets["selection_schema"],
            )

    def test_hash_drift_and_source_run_fail_before_service_or_data(self) -> None:
        drifted = copy.deepcopy(self.config)
        drifted["roles"]["researcher"]["prompt"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.FixedRoleError, "researcher_prompt_hash_drift"):
            MODULE.validate_freeze(drifted)
        actor_drift = copy.deepcopy(self.config)
        actor_drift["reviewer_actors"]["researcher"]["actor_id"] = ""
        with self.assertRaisesRegex(MODULE.FixedRoleError, "reviewer_actor_id_drift"):
            MODULE.validate_freeze(actor_drift)
        label_drift = copy.deepcopy(self.config)
        label_drift["roles"]["researcher"]["display_name"] = ""
        with self.assertRaisesRegex(MODULE.FixedRoleError, "role_label_invalid"):
            MODULE.validate_freeze(label_drift)
        path_drift = copy.deepcopy(self.config)
        path_drift["assets"]["fixed_role_runtime"]["file"] = path_drift["assets"][
            "prompt_limit_guard"
        ]["file"]
        with self.assertRaisesRegex(MODULE.FixedRoleError, "fixed_role_runtime_path_drift"):
            MODULE.validate_freeze(path_drift)
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
            any("/dataset/" in str(call.args[0]) or "/Storage/" in str(call.args[0]) for call in reads.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
