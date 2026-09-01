#!/usr/bin/env python3
"""Source-free tests for the Qwen3 WarrantRoute component."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_warrantroute.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/qwen3_warrantroute_freeze.json"
SPEC = importlib.util.spec_from_file_location("qwen3_warrantroute_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


LANE = {
    "corpus": "dreaddit",
    "source_split": "official_train",
    "internal_lane": "development_train",
    "experimental_role": "development_diagnostic",
    "heldout": False,
}
ITEM_ID = "DJI_0000000000000001"
ITEM_SHA = "1" * 64


def observation(
    role: str,
    repetition: int,
    index: int,
    *,
    flags: list[str] | None = None,
    cannot_judge: list[str] | None = None,
    status: str = "valid",
) -> dict:
    return {
        "actor_id": MODULE.EXPECTED_ACTOR_IDS[role],
        "prompted_role": role,
        "model_id": "qwen3:8b",
        "model_snapshot_sha256": MODULE.CONFIG_FOR_TESTS["qwen_reviewer"][
            "model_manifest_sha256"
        ],
        "rating_repetition": repetition,
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "observation_status": status,
        "rating": (
            {
                "cannot_judge": cannot_judge or [],
                "serious_error_flags": flags or [],
            }
            if status == "valid"
            else None
        ),
        "observation_sha256": f"{index:064x}",
    }


def route_record(route: str) -> dict:
    return {
        "route_record_version": "warrantroute-route-record-v1",
        "study_id": "source-free-software-contract",
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "lane": copy.deepcopy(LANE),
        "router_input_sha256": "2" * 64,
        "policy_manifest_sha256": "3" * 64,
        "policy_asset_sha256": "4" * 64,
        "route": route,
        "selected_roles": list(MODULE.ROUTE_TO_ROLES[route]),
        "route_source": "frozen_policy",
        "policy_frozen_before_heldout_access": True,
        "route_changed_after_freeze": False,
        "contains_source_text": False,
        "manuscript_eligible": False,
    }


def application(route: str) -> dict:
    role_flags = {
        "researcher": ["unsupported_inference"],
        "qualitative_methods": ["lost_negative_case"],
        "domain": ["contextual_flattening"],
    }
    rows = {}
    index = 1
    for role in MODULE.ROLE_ORDER:
        rows[role] = []
        for repetition in (1, 2, 3):
            rows[role].append(
                observation(
                    role,
                    repetition,
                    index,
                    flags=role_flags[role],
                )
            )
            index += 1
    record = route_record(route)
    seal = {
        "document_type": "warrantroute_route_seal",
        "seal_version": "warrantroute-route-seal-v1",
        "route_record_sha256": MODULE.sha256_bytes(MODULE.canonical_bytes(record)),
        "policy_manifest_sha256": record["policy_manifest_sha256"],
        "freeze_sha256": MODULE.sha256_bytes(MODULE.runtime.read_regular_bytes(CONFIG)),
        "item_id": ITEM_ID,
        "route": route,
        "sealed_before_specialist_observations": True,
        "sealed_before_heldout_access": True,
        "contains_source_text": False,
        "manuscript_eligible": False,
    }
    return {
        "application_schema_version": "warrantroute-route-application-v1",
        "study_id": "source-free-software-contract",
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "lane": copy.deepcopy(LANE),
        "route_record": record,
        "route_seal": seal,
        "reviewer_model": {
            "model_id": "qwen3:8b",
            "model_snapshot_sha256": MODULE.CONFIG_FOR_TESTS["qwen_reviewer"][
                "model_manifest_sha256"
            ],
        },
        "role_observations": rows,
        "contains_source_text": False,
        "contains_router_training_label": False,
        "contains_verified_error": False,
    }


def router_input() -> dict:
    return {
        "input_schema_version": "warrantroute-router-input-v1",
        "study_id": "source-free-software-contract",
        "item_id": ITEM_ID,
        "evaluator_item_sha256": ITEM_SHA,
        "lane": copy.deepcopy(LANE),
        "researcher_observation": {
            "actor_id": "qwen3_8b_researcher_reviewer_v1",
            "model_id": "qwen3:8b",
            "model_snapshot_sha256": MODULE.CONFIG_FOR_TESTS["qwen_reviewer"][
                "model_manifest_sha256"
            ],
            "prompted_role": "researcher",
            "rating_repetition": 1,
            "evaluator_item_sha256": ITEM_SHA,
            "observation_status": "valid",
            "rating": {
                "evidential_credibility": 4,
                "voice_boundary_preservation": 4,
                "scope_calibration": 4,
                "cannot_judge": [],
                "confidence": 4,
                "disposition": "accept",
                "requested_expertise": "none",
            },
            "observation_sha256": "5" * 64,
        },
        "feature_projection": {
            "feature_set_id": "not-yet-frozen",
            "feature_set_sha256": "6" * 64,
            "numeric": {},
            "boolean": {},
            "categorical_codes": {},
        },
        "pre_specialist_only": True,
        "heldout_accessed_before_policy_freeze": False,
        "contains_source_text": False,
        "contains_protected_attributes": False,
        "contains_verified_error": False,
        "contains_specialist_outcomes": False,
    }


def policy_manifest() -> dict:
    return {
        "policy_schema_version": "warrantroute-policy-manifest-v1",
        "policy_id": "source-free-policy-envelope",
        "status": "prospectively_frozen",
        "router_formulation": "unbound-source-free-contract",
        "policy_asset": {"file": "Storage/policy.private.json", "sha256": "7" * 64},
        "implementation_asset": {"file": "Storage/router.private.py", "sha256": "8" * 64},
        "feature_set": {
            "feature_set_id": "not-yet-frozen",
            "feature_set_sha256": "6" * 64,
            "ordered_feature_names": ["source_count"],
        },
        "development_projection_sha256": "9" * 64,
        "qualification_gate": {
            "file": "Storage/qualification_gate.json",
            "sha256": "a" * 64,
            "passed": True,
            "admitted_base_count": 1,
            "accepted_variant_count": 1,
        },
        "preprocessing_sha256": "b" * 64,
        "regularization_sha256": "c" * 64,
        "budget_and_cost_sha256": "d" * 64,
        "threshold_rule_sha256": "e" * 64,
        "route_values": list(MODULE.ROUTE_ORDER),
        "route_tie_order": list(MODULE.ROUTE_ORDER),
        "inference_failure_action": "block",
        "heldout_accessed_before_freeze": False,
        "contains_source_text": False,
        "contains_protected_attributes": False,
        "manuscript_eligible": False,
    }


class Qwen3WarrantRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = MODULE.runtime.load_json(CONFIG)
        MODULE.CONFIG_FOR_TESTS = cls.config
        cls.assets = MODULE.validate_freeze(cls.config)

    def test_freeze_binds_qwen_and_blocks_scientific_execution(self) -> None:
        self.assertEqual(self.config["qwen_reviewer"]["model_id"], "qwen3:8b")
        self.assertEqual(tuple(self.config["qwen_reviewer"]["roles"]), MODULE.ROLE_ORDER)
        self.assertFalse(self.config["routing_policy_bound"])
        self.assertFalse(self.config["router_training_allowed"])
        self.assertFalse(self.config["heldout_access_allowed"])
        self.assertFalse(self.config["source_bearing_execution_allowed"])

    def test_all_four_route_mappings_are_exact(self) -> None:
        flags = {
            "researcher": {"unsupported_inference"},
            "qualitative_methods": {"lost_negative_case"},
            "domain": {"contextual_flattening"},
        }
        self.assertEqual(
            MODULE.combine_route_flags("none", flags), {"unsupported_inference"}
        )
        self.assertEqual(
            MODULE.combine_route_flags("qualitative_methods", flags),
            {"lost_negative_case"},
        )
        self.assertEqual(
            MODULE.combine_route_flags("domain", flags), {"contextual_flattening"}
        )
        self.assertEqual(
            MODULE.combine_route_flags("both", flags),
            {"lost_negative_case", "contextual_flattening"},
        )

    def test_primary_application_uses_only_selected_roles(self) -> None:
        expected = {
            "none": ["unsupported_inference"],
            "qualitative_methods": ["lost_negative_case"],
            "domain": ["contextual_flattening"],
            "both": ["lost_negative_case", "contextual_flattening"],
        }
        for route in MODULE.ROUTE_ORDER:
            result = MODULE._apply_route_projection_for_contract_test(
                application(route),
                aggregation="repetition_1",
                config=self.config,
                assets=self.assets,
            )
            self.assertEqual(result["selected_serious_error_flags"], expected[route])
            self.assertEqual(result["selected_roles"], list(MODULE.ROUTE_TO_ROLES[route]))
            self.assertFalse(result["fallback_used"])
            self.assertFalse(result["merged_rating_created"])

    def test_both_retains_valid_role_and_never_falls_back(self) -> None:
        value = application("both")
        value["role_observations"]["qualitative_methods"][0] = observation(
            "qualitative_methods", 1, 50, status="timeout"
        )
        result = MODULE._apply_route_projection_for_contract_test(
            value,
            aggregation="repetition_1",
            config=self.config,
            assets=self.assets,
        )
        self.assertEqual(result["selected_serious_error_flags"], ["contextual_flattening"])
        self.assertEqual(result["selected_role_failures"], ["qualitative_methods"])
        self.assertNotIn("unsupported_inference", result["selected_serious_error_flags"])
        self.assertFalse(result["fallback_used"])

    def test_two_of_three_votes_within_role_then_reuses_route(self) -> None:
        value = application("qualitative_methods")
        rows = value["role_observations"]["qualitative_methods"]
        rows[0]["rating"]["serious_error_flags"] = ["lost_negative_case"]
        rows[1]["rating"]["serious_error_flags"] = ["lost_negative_case"]
        rows[2]["rating"]["serious_error_flags"] = ["unsupported_inference"]
        result = MODULE._apply_route_projection_for_contract_test(
            value,
            aggregation="two_of_three",
            config=self.config,
            assets=self.assets,
        )
        self.assertEqual(result["route"], "qualitative_methods")
        self.assertEqual(result["selected_serious_error_flags"], ["lost_negative_case"])
        self.assertEqual(len(result["selected_observation_sha256"]), 3)

    def test_cannot_judge_is_unusable_and_does_not_trigger_fallback(self) -> None:
        value = application("domain")
        value["role_observations"]["domain"][0]["rating"]["cannot_judge"] = [
            "scope_calibration"
        ]
        result = MODULE._apply_route_projection_for_contract_test(
            value,
            aggregation="repetition_1",
            config=self.config,
            assets=self.assets,
        )
        self.assertEqual(result["selected_serious_error_flags"], [])
        self.assertEqual(result["selected_role_failures"], ["domain"])
        self.assertFalse(result["fallback_used"])

    def test_repetition_actor_item_snapshot_and_hash_drift_are_rejected(self) -> None:
        cases = []
        repetition = application("none")
        repetition["role_observations"]["researcher"][2]["rating_repetition"] = 2
        cases.append((repetition, "application_repetition_grid_invalid"))
        actor = application("none")
        actor["role_observations"]["domain"][0]["actor_id"] = MODULE.EXPECTED_ACTOR_IDS[
            "researcher"
        ]
        cases.append((actor, "application_actor_drift"))
        item = application("none")
        item["role_observations"]["researcher"][0]["item_id"] = "DJI_0000000000000002"
        cases.append((item, "application_item_drift"))
        snapshot = application("none")
        snapshot["role_observations"]["researcher"][0]["model_snapshot_sha256"] = "0" * 64
        cases.append((snapshot, "application_snapshot_drift"))
        duplicate = application("none")
        duplicate["role_observations"]["domain"][0]["observation_sha256"] = duplicate[
            "role_observations"
        ]["researcher"][0]["observation_sha256"]
        cases.append((duplicate, "application_observation_duplicate"))
        for value, code in cases:
            with self.assertRaisesRegex(MODULE.WarrantRouteError, code):
                MODULE._validate_application_projection_contract(
                    value, config=self.config, assets=self.assets
                )

    def test_lane_aliases_and_route_role_mismatch_are_rejected(self) -> None:
        alias = application("none")
        alias["lane"]["source_split"] = "development_train"
        alias["route_record"]["lane"] = copy.deepcopy(alias["lane"])
        with self.assertRaisesRegex(
            MODULE.WarrantRouteError, "route_application_schema_invalid"
        ):
            MODULE._validate_application_projection_contract(
                alias, config=self.config, assets=self.assets
            )
        mismatch = route_record("both")
        mismatch["selected_roles"] = ["researcher"]
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "route_record_schema_invalid"):
            MODULE.validate_route_record(
                mismatch, schema=self.assets["route_record_schema"]
            )

    def test_router_projection_rejects_leakage_and_unfrozen_features(self) -> None:
        clean = router_input()
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "router_feature_set_not_frozen"):
            MODULE.validate_router_input(
                clean, config=self.config, schema=self.assets["router_input_schema"]
            )
        leaked = router_input()
        leaked["feature_projection"]["numeric"]["truth"] = 1
        with self.assertRaisesRegex(
            MODULE.WarrantRouteError, "router_input_contains_forbidden_key"
        ):
            MODULE.validate_router_input(
                leaked, config=self.config, schema=self.assets["router_input_schema"]
            )
        nonfinite = router_input()
        nonfinite["feature_projection"]["numeric"]["source_count"] = float("nan")
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "nonfinite"):
            MODULE.validate_router_input(
                nonfinite, config=self.config, schema=self.assets["router_input_schema"]
            )
        cross_item = router_input()
        cross_item["researcher_observation"]["evaluator_item_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            MODULE.WarrantRouteError, "router_researcher_packet_hash_drift"
        ):
            MODULE.validate_router_input(
                cross_item,
                config=self.config,
                schema=self.assets["router_input_schema"],
            )

    def test_policy_and_route_inference_remain_blocked(self) -> None:
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "routing_policy_not_bound"):
            MODULE.validate_policy_manifest(
                policy_manifest(),
                config=self.config,
                schema=self.assets["policy_manifest_schema"],
            )
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "router_feature_set_not_frozen"):
            MODULE.build_route_record(
                router_input(),
                policy_manifest(),
                config=self.config,
                assets=self.assets,
            )
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "routing_policy_not_bound"):
            MODULE.apply_frozen_route(
                application("domain"),
                aggregation="repetition_1",
                config=self.config,
                assets=self.assets,
            )
        forged_bound_config = copy.deepcopy(self.config)
        forged_bound_config["routing_policy_bound"] = True
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "unexpected_routing_policy"):
            MODULE.validate_policy_manifest(
                policy_manifest(),
                config=forged_bound_config,
                schema=self.assets["policy_manifest_schema"],
            )

    def test_route_seal_binds_record_and_rejects_malformed_record(self) -> None:
        record = route_record("domain")
        seal = MODULE._build_route_seal_projection_for_contract_test(
            record,
            route_schema=self.assets["route_record_schema"],
            freeze_sha256="f" * 64,
        )
        self.assertEqual(seal["route"], "domain")
        self.assertTrue(seal["sealed_before_heldout_access"])
        malformed = copy.deepcopy(record)
        malformed["route_changed_after_freeze"] = True
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "route_record_schema_invalid"):
            MODULE._build_route_seal_projection_for_contract_test(
                malformed,
                route_schema=self.assets["route_record_schema"],
                freeze_sha256="f" * 64,
            )

        with self.assertRaisesRegex(
            MODULE.WarrantRouteError,
            "route_sealing_not_authorized_in_source_free_freeze",
        ):
            MODULE.build_route_seal(
                record,
                route_schema=self.assets["route_record_schema"],
                freeze_sha256="f" * 64,
                config=self.config,
            )

        tampered_application = application("domain")
        tampered_application["route_seal"]["route"] = "none"
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "application_route_seal_route_drift"):
            MODULE._apply_route_projection_for_contract_test(
                tampered_application,
                aggregation="repetition_1",
                config=self.config,
                assets=self.assets,
            )

    def test_asset_drift_and_blocked_commands_fail_before_data_or_service(self) -> None:
        drifted = copy.deepcopy(self.config)
        drifted["assets"]["route_record_schema"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.WarrantRouteError, "route_record_schema_hash_drift"):
            MODULE.validate_freeze(drifted)

        observed: list[Path] = []
        original = MODULE.runtime.read_regular_bytes

        def guarded(path: Path) -> bytes:
            observed.append(path)
            if "/dataset/" in str(path) or "/Storage/" in str(path):
                raise AssertionError("source path opened")
            return original(path)

        for command, expected_error in (
            ("train", "router_training_not_authorized"),
            ("run", "source_bearing_execution_not_authorized"),
        ):
            with (
                mock.patch.object(MODULE.runtime, "read_regular_bytes", side_effect=guarded),
                mock.patch.object(
                    MODULE.runtime,
                    "api_json",
                    side_effect=AssertionError("model service contacted"),
                ),
                mock.patch.object(sys, "argv", [str(SCRIPT), command]),
                mock.patch("builtins.print"),
            ):
                self.assertEqual(MODULE.main(), 2)
        self.assertTrue(observed)
        self.assertFalse(any("/dataset/" in str(path) for path in observed))
        self.assertFalse(any("/Storage/" in str(path) for path in observed))


if __name__ == "__main__":
    unittest.main()
