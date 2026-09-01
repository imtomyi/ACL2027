#!/usr/bin/env python3
"""Source-free unit tests for the final v2.2 interface diagnostic."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_personal_local_main_v22.py"
SPEC = importlib.util.spec_from_file_location("rq2_personal_local_main_v22_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
v22 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v22)


def load_static():
    config = v22.v1.load_json(v22.DEFAULT_CONFIG)
    _, _, paths, _ = v22.validate_v22_freeze(
        config, include_record_hashes=False, config_path=v22.DEFAULT_CONFIG
    )
    assets = v22.load_assets(paths)
    v22.validate_interface_assets(config, assets)
    return config, assets


def contains_exact_key(value, target):
    if isinstance(value, dict):
        return target in value or any(contains_exact_key(child, target) for child in value.values())
    if isinstance(value, list):
        return any(contains_exact_key(child, target) for child in value)
    return False


class V22StaticTests(unittest.TestCase):
    def test_import_hash_binds_v21_and_v2_core(self):
        self.assertEqual(v22.raw_sha256(v22.V21_RUNNER), v22.V21_RUNNER_SHA256)
        self.assertEqual(v22.v21.CORE_RUNNER_SHA256, v22.V2_CORE_SHA256)
        self.assertEqual(v22.raw_sha256(v22.v21.CORE_RUNNER), v22.V2_CORE_SHA256)
        self.assertEqual(v22.raw_sha256(v22.V21_CONFIG), v22.V21_CONFIG_SHA256)

    def test_source_free_validation_opens_no_storage_or_records_and_no_service(self):
        original = v22.v1.load_json
        opened = []
        hashed = []

        def tracked(path):
            opened.append(Path(path))
            return original(path)

        original_hash = v22.raw_sha256

        def tracked_hash(path):
            hashed.append(Path(path))
            return original_hash(path)

        config = original(v22.DEFAULT_CONFIG)
        with (
            mock.patch.object(v22.v1, "load_json", side_effect=tracked),
            mock.patch.object(v22, "raw_sha256", side_effect=tracked_hash),
            mock.patch.object(
                v22.v1, "load_bound_records", side_effect=AssertionError("records opened")
            ),
            mock.patch.object(
                v22.v1, "preflight_service", side_effect=AssertionError("service contacted")
            ),
        ):
            _, _, paths, excluded = v22.validate_v22_freeze(
                config, include_record_hashes=False, config_path=v22.DEFAULT_CONFIG
            )
            assets = v22.load_assets(paths)
            v22.validate_interface_assets(config, assets)
        self.assertEqual(excluded, set())
        self.assertFalse(any("Storage" in path.parts for path in opened))
        self.assertFalse(any("Storage" in path.parts for path in hashed))

    def test_only_base_admissibility_prompt_and_schema_change_from_v21(self):
        config = v22.v1.load_json(v22.DEFAULT_CONFIG)
        baseline = v22.v1.load_json(v22.V21_CONFIG)
        changed = {
            key
            for key in config["construction_assets"]
            if config["construction_assets"][key] != baseline["construction_assets"][key]
        }
        self.assertEqual(
            changed, {"prompt_base_admissibility", "schema_base_admissibility"}
        )
        self.assertEqual(config["development_qualification"], baseline["development_qualification"])
        self.assertEqual(config["outcome_policy"], baseline["outcome_policy"])
        self.assertTrue(config["final_interface_repair"])

    def test_freeze_rejects_nested_json_type_substitutions(self):
        base = v22.v1.load_json(v22.DEFAULT_CONFIG)
        mutations = []

        value = copy.deepcopy(base)
        value["development_qualification"]["minimum_admitted_bases"] = 8.0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["outcome_policy"]["semantic_retry_allowed"] = 0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["result_labels"]["confirmatory_claims_allowed"] = 0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["live_interface_canary"]["fixture_count"] = 3.0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["interface_format_gate"]["planned_slots"] = 10.0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["prior_shared_selection_runs"][0]["selection_reused"] = 0
        mutations.append(value)

        value = copy.deepcopy(base)
        value["prior_v1_outcomes_reused"] = 0
        mutations.append(value)

        for index, config in enumerate(mutations):
            with self.subTest(mutation=index):
                with self.assertRaises(v22.V22Error):
                    v22.validate_v22_freeze(
                        config,
                        include_record_hashes=False,
                        config_path=v22.DEFAULT_CONFIG,
                    )

    def test_runtime_freeze_validation_hashes_no_agyw_record(self):
        config = v22.v1.load_json(v22.DEFAULT_CONFIG)
        fake_development = ROOT / "protocol" / "execution_contract_v1.md"
        expected_development_hash = v22.v1.load_json(v22.core.V1_CONFIG)["lanes"][
            "dreaddit_development"
        ]["records_file_sha256"]
        hashed = []
        original_hash = v22.raw_sha256
        exclusions = {
            hashlib.sha256(f"excluded-{index}".encode()).hexdigest()
            for index in range(90)
        }

        def tracked_hash(path):
            path = Path(path)
            hashed.append(path)
            if path == fake_development:
                return expected_development_hash
            return original_hash(path)

        with (
            mock.patch.object(
                v22.v1,
                "validate_freeze",
                return_value={"records_dreaddit_development": fake_development},
            ) as inherited,
            mock.patch.object(v22, "raw_sha256", side_effect=tracked_hash),
            mock.patch.object(
                v22, "load_predecessor_exclusions", return_value=exclusions
            ),
        ):
            _, _, _, observed = v22.validate_v22_freeze(
                config,
                include_record_hashes=True,
                config_path=v22.DEFAULT_CONFIG,
            )
        self.assertEqual(observed, exclusions)
        self.assertEqual(inherited.call_args.kwargs["include_record_hashes"], False)
        self.assertIn(fake_development, hashed)
        self.assertFalse(any("agyw" in path.as_posix().lower() for path in hashed))

    def test_static_branch_fixtures_convert_exactly(self):
        config, assets = load_static()
        cases = assets["transport_canary_fixtures"]["fixtures"]
        self.assertEqual(len(cases), 3)
        for case in cases:
            output = v22.adapt_base_admissibility_transport_v22(
                case["transport_output"],
                transport_schema=assets["schema_base_admissibility"],
                canonical_schema=assets["canonical_base_admissibility_schema"],
                adapter_contract=assets["transport_adapter_contract"],
            )
            self.assertEqual(output, case["canonical_output"])
        self.assertEqual(config["interface_format_gate"]["required_format_valid"], 10)

    def test_canary_prompts_are_exactly_16384_source_free_bytes(self):
        _, assets = load_static()
        fixture_doc = assets["transport_canary_fixtures"]
        for case in fixture_doc["fixtures"]:
            prompt = v22.build_source_free_canary_prompt(
                fixture_doc["source_free_prompt_profile"], case["canary_instruction"]
            )
            self.assertEqual(len(prompt.encode("ascii")), 16384)
            self.assertNotIn("Storage/", prompt)


class V22AdapterAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.assets = load_static()
        cls.adapter = cls.assets["transport_adapter_contract"]
        cls.schema = cls.assets["schema_base_admissibility"]
        cls.canonical_schema = cls.assets["canonical_base_admissibility_schema"]
        cls.cases = {
            row["code"]: row["transport_output"]
            for row in cls.assets["transport_canary_fixtures"]["fixtures"]
        }

    def adapt(self, output):
        return v22.adapt_base_admissibility_transport_v22(
            output,
            transport_schema=self.schema,
            canonical_schema=self.canonical_schema,
            adapter_contract=self.adapter,
        )

    def test_schema_rejects_unknown_missing_and_nested_fields(self):
        base = self.cases["admissible_all_true_all_ready"]
        mutations = []
        value = copy.deepcopy(base)
        value["unknown"] = True
        mutations.append(value)
        value = copy.deepcopy(base)
        del value["reason_codes"]
        mutations.append(value)
        value = copy.deepcopy(base)
        value["reason_codes"] = [{"nested": "forbidden"}]
        mutations.append(value)
        for value in mutations:
            with self.assertRaisesRegex(
                v22.FormatAdapterError, "base_admissibility_transport_schema_invalid"
            ):
                self.adapt(value)

    def test_admissible_cross_field_contradictions_fail(self):
        base = self.cases["admissible_all_true_all_ready"]
        mutations = []
        value = copy.deepcopy(base)
        value["check_no_outside_facts"] = False
        mutations.append(value)
        value = copy.deepcopy(base)
        value["reason_codes"] = ["outside_fact_or_overreach"]
        mutations.append(value)
        for value in mutations:
            with self.assertRaisesRegex(
                v22.FormatAdapterError,
                "base_admissibility_status_semantics_invalid",
            ):
                self.adapt(value)

    def test_flawed_requires_false_check_and_material_defect(self):
        base = self.cases["materially_flawed_all_false_all_not_ready"]
        value = copy.deepcopy(base)
        for name in v22.CHECK_NAMES:
            value[f"check_{name}"] = True
        with self.assertRaisesRegex(
            v22.FormatAdapterError, "base_admissibility_status_semantics_invalid"
        ):
            self.adapt(value)
        value = copy.deepcopy(base)
        value["reason_codes"] = ["insufficient_displayed_information"]
        with self.assertRaisesRegex(
            v22.FormatAdapterError, "base_admissibility_status_semantics_invalid"
        ):
            self.adapt(value)

    def test_unclear_requires_false_check_and_insufficient_code(self):
        base = self.cases["unclear_all_false_all_unclear"]
        value = copy.deepcopy(base)
        value["reason_codes"] = ["material_claim_not_warranted"]
        with self.assertRaisesRegex(
            v22.FormatAdapterError, "base_admissibility_status_semantics_invalid"
        ):
            self.adapt(value)

    def test_readiness_pairs_fail_closed(self):
        base = self.cases["admissible_all_true_all_ready"]
        mutations = []
        value = copy.deepcopy(base)
        value["non_support_anchor_positions"] = []
        mutations.append(value)
        value = copy.deepcopy(base)
        value["multi_unit_support_positions"] = [1]
        mutations.append(value)
        value = copy.deepcopy(self.cases["unclear_all_false_all_unclear"])
        value["bounded_claim_positions"] = [1]
        mutations.append(value)
        for value in mutations:
            with self.assertRaisesRegex(
                v22.FormatAdapterError,
                "base_admissibility_readiness_semantics_invalid",
            ):
                self.adapt(value)

    def test_integral_float_positions_are_not_exact_integer_serialization(self):
        value = copy.deepcopy(self.cases["admissible_all_true_all_ready"])
        value["non_support_anchor_positions"] = [1.0]
        with self.assertRaisesRegex(
            v22.FormatAdapterError,
            "base_admissibility_readiness_semantics_invalid",
        ):
            self.adapt(value)

    def test_adapter_preserves_array_order_without_repair(self):
        value = copy.deepcopy(self.cases["admissible_all_true_all_ready"])
        value["multi_unit_support_positions"] = [6, 2, 4]
        output = self.adapt(value)
        self.assertEqual(
            output["readiness"]["multi_unit_support"]["evidence_positions"],
            [6, 2, 4],
        )


class V22LiveCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.assets = load_static()
        cls.v1_config = v22.v1.load_json(v22.core.V1_CONFIG)
        cls.fixtures = cls.assets["transport_canary_fixtures"]["fixtures"]

    def fake_success_api(self, calls):
        def api(endpoint, api_path, payload, *, timeout):
            self.assertEqual(endpoint, self.v1_config["service_url"])
            self.assertEqual(api_path, "/api/chat")
            self.assertEqual(timeout, 180)
            self.assertEqual(payload["model"], self.v1_config["models"]["verifier"]["model_id"])
            self.assertEqual(payload["options"], {
                "temperature": 0,
                "top_p": 1,
                "num_ctx": 8192,
                "num_predict": 768,
                "seed": 2027082699,
            })
            self.assertFalse(payload["stream"])
            self.assertFalse(payload["think"])
            self.assertNotIn("tools", payload)
            prompt = payload["messages"][-1]["content"]
            self.assertEqual(len(prompt.encode("ascii")), 16384)
            index = len(calls)
            calls.append(copy.deepcopy(payload))
            return {
                "model": payload["model"],
                "done": True,
                "done_reason": "stop",
                "message": {
                    "content": json.dumps(self.fixtures[index]["transport_output"])
                },
            }

        return api

    def test_live_canary_is_three_exact_one_attempt_write_free_calls(self):
        calls = []
        opened_hashes = []
        original_hash = v22.raw_sha256

        def tracked_hash(path):
            opened_hashes.append(Path(path))
            return original_hash(path)

        with (
            mock.patch.object(v22.v1, "api_json", side_effect=self.fake_success_api(calls)),
            mock.patch.object(v22.v1, "write_json_once", side_effect=AssertionError("wrote")),
            mock.patch.object(v22.v1, "write_bytes_once", side_effect=AssertionError("wrote")),
            mock.patch.object(v22.v1, "load_bound_records", side_effect=AssertionError("data")),
            mock.patch.object(v22, "raw_sha256", side_effect=tracked_hash),
        ):
            evidence = v22.run_live_interface_canary_v22(self.v1_config, self.assets)
        self.assertEqual(len(calls), 3)
        self.assertEqual(evidence["logical_calls"], 3)
        self.assertEqual(evidence["physical_attempts"], 3)
        self.assertFalse(evidence["model_content_retained"])
        self.assertFalse(evidence["writes_artifacts"])
        self.assertFalse(evidence["data_or_storage_opened"])
        self.assertFalse(any("Storage" in path.parts for path in opened_hashes))
        summary = v22.canary_contract_summary(evidence)
        self.assertEqual(
            set(summary),
            {"status", "case_count", "evidence_sha256", "contains_source_text"},
        )
        self.assertEqual(
            v22.validate_bound_canary_contract_summary(
                summary, self.v1_config, self.assets
            ),
            summary,
        )

    def test_well_formed_but_forged_canary_hash_is_rejected(self):
        expected = v22.canary_contract_summary(
            v22.expected_live_canary_evidence_v22(self.v1_config, self.assets)
        )
        forged = {**expected, "evidence_sha256": "0" * 64}
        with self.assertRaisesRegex(
            v22.V22Error, "v22_canary_bound_evidence_hash_mismatch"
        ):
            v22.validate_bound_canary_contract_summary(
                forged, self.v1_config, self.assets
            )

    def test_every_case_failure_is_single_attempt_and_sanitized(self):
        sentinel = "MODEL_CONTENT_SENTINEL_MUST_NOT_ESCAPE"
        for failure_index in range(3):
            calls = []

            def api(endpoint, api_path, payload, *, timeout):
                index = len(calls)
                calls.append(payload)
                if index == failure_index:
                    raise RuntimeError(sentinel)
                return {
                    "model": payload["model"],
                    "done": True,
                    "done_reason": "stop",
                    "message": {
                        "content": json.dumps(self.fixtures[index]["transport_output"])
                    },
                }

            with mock.patch.object(v22.v1, "api_json", side_effect=api):
                with self.assertRaises(v22.V22Error) as caught:
                    v22.run_live_interface_canary_v22(self.v1_config, self.assets)
            self.assertEqual(len(calls), failure_index + 1)
            self.assertNotIn(sentinel, str(caught.exception))
            self.assertRegex(str(caught.exception), r"^v22_canary_case_[a-z0-9_]+_transport_or_schema_failed$")

    def test_model_identity_and_stop_mismatch_fail_without_content(self):
        mutations = (
            {"model": "wrong:model", "done": True, "done_reason": "stop"},
            {
                "model": self.v1_config["models"]["verifier"]["model_id"],
                "done": True,
                "done_reason": "length",
            },
        )
        for fields in mutations:
            calls = []

            def api(endpoint, api_path, payload, *, timeout):
                calls.append(payload)
                return {
                    **fields,
                    "message": {"content": json.dumps(self.fixtures[0]["transport_output"])},
                }

            with mock.patch.object(v22.v1, "api_json", side_effect=api):
                with self.assertRaisesRegex(
                    v22.V22Error,
                    "v22_canary_case_admissible_all_true_all_ready_transport_or_schema_failed",
                ):
                    v22.run_live_interface_canary_v22(self.v1_config, self.assets)
            self.assertEqual(len(calls), 1)

    def test_schema_valid_cross_field_and_exact_fixture_failures_are_distinct(self):
        cross_field = copy.deepcopy(self.fixtures[0]["transport_output"])
        cross_field["check_no_outside_facts"] = False
        wrong_exact = copy.deepcopy(self.fixtures[1]["transport_output"])
        for output, expected in (
            (cross_field, "cross_field_failed"),
            (wrong_exact, "exact_fixture_failed"),
        ):
            calls = []

            def api(endpoint, api_path, payload, *, timeout):
                calls.append(payload)
                return {
                    "model": payload["model"],
                    "done": True,
                    "done_reason": "stop",
                    "message": {"content": json.dumps(output)},
                }

            with mock.patch.object(v22.v1, "api_json", side_effect=api):
                with self.assertRaises(v22.V22Error) as caught:
                    v22.run_live_interface_canary_v22(self.v1_config, self.assets)
            self.assertEqual(len(calls), 1)
            self.assertTrue(str(caught.exception).endswith(expected))

    def test_execute_canary_failure_precedes_full_validation_and_data_access(self):
        validation_modes = []
        storage_probes = []
        resolved_paths = []
        original_validate = v22.validate_v22_freeze
        original_resolve = v22.v1.resolve_workspace_path

        def validate(config, *, include_record_hashes, config_path):
            validation_modes.append(include_record_hashes)
            if include_record_hashes:
                raise AssertionError("full validation reached after canary failure")
            return original_validate(
                config,
                include_record_hashes=False,
                config_path=config_path,
            )

        with (
            mock.patch.object(v22, "validate_v22_freeze", side_effect=validate),
            mock.patch.object(
                v22.v1,
                "resolve_workspace_path",
                side_effect=lambda path: resolved_paths.append(str(path))
                or original_resolve(path),
            ),
            mock.patch.object(
                v22.v1,
                "safe_exists",
                side_effect=lambda path: storage_probes.append(Path(path)) or False,
            ),
            mock.patch.object(v22.v1, "preflight_service", return_value={}),
            mock.patch.object(
                v22,
                "run_live_interface_canary_v22",
                side_effect=v22.V22Error("v22_canary_case_01_transport_or_schema_failed"),
            ),
            mock.patch.object(
                v22.v1, "load_bound_records", side_effect=AssertionError("records opened")
            ),
            mock.patch.object(
                v22, "load_predecessor_exclusions", side_effect=AssertionError("Storage opened")
            ),
        ):
            with self.assertRaisesRegex(v22.V22Error, "v22_canary_case_01"):
                v22.execute_v22(
                    v22.DEFAULT_CONFIG,
                    "rq2plv22_20260827T120000Z_1234abcd",
                )
        self.assertEqual(validation_modes, [False])
        self.assertEqual(storage_probes, [])
        self.assertFalse(
            any(path.startswith("Storage/") or path.startswith("dataset/") for path in resolved_paths)
        )

    def test_sealed_resume_skips_service_and_live_canary(self):
        requested = "rq2plv22_20260827T120000Z_abcdef12"

        def exists(path):
            return Path(path).name == "output_seal.json"

        with (
            mock.patch.object(v22.v1, "safe_exists", side_effect=exists),
            mock.patch.object(v22, "validate_output_seal_v22", return_value={}),
            mock.patch.object(
                v22.v1, "preflight_service", side_effect=AssertionError("service contacted")
            ),
            mock.patch.object(
                v22,
                "run_live_interface_canary_v22",
                side_effect=AssertionError("canary rerun"),
            ),
        ):
            run_dir = v22.execute_v22(
                v22.DEFAULT_CONFIG, requested, resume_existing=True
            )
        self.assertEqual(run_dir, v22.V22_OUTPUT_ROOT / requested)


class V22ContractAndArtifactInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.assets = load_static()
        cls.v1_config = v22.v1.load_json(v22.core.V1_CONFIG)
        cls.run_id = "rq2plv22_20260827T120000Z_1234abcd"
        cls.run_dir = Path("/private/source-free") / cls.run_id
        cls.summary = v22.canary_contract_summary(
            v22.expected_live_canary_evidence_v22(cls.v1_config, cls.assets)
        )

    def make_service(self):
        return {
            "ollama_version": self.v1_config["ollama_version"],
            "endpoint": self.v1_config["service_url"],
            "endpoint_is_numeric_loopback": True,
            "models": {
                role: {
                    "model_id": frozen["model_id"],
                    "digest": "sha256:" + frozen["local_manifest_file_sha256"],
                    "size": index + 1,
                }
                for index, (role, frozen) in enumerate(
                    self.v1_config["models"].items()
                )
            },
        }

    def make_core_contract(self):
        return {
            "document_type": "rq2_personal_local_v2_run_contract",
            "run_id": self.run_id,
            "result_label": v22.STATUS,
            "evidence_status": v22.EVIDENCE_STATUS,
            "created_at_utc": "2026-08-27T12:00:00.123456Z",
            "v2_freeze_sha256": v22.raw_sha256(v22.DEFAULT_CONFIG),
            "v1_freeze_sha256": v22.raw_sha256(v22.core.V1_CONFIG),
            "v2_runner_sha256": self.config["runner_sha256"],
            "v1_runner_sha256": v22.core.V1_RUNNER_SHA256,
            "policy_sha256": self.v1_config["policy_file_sha256"],
            "python_version": "3.11.0",
            "service": self.make_service(),
            "boundary_checks": v22.expected_boundary_evidence_v22(
                self.v1_config, self.summary
            ),
            "lane_packet_counts": self.config["lane_packet_counts"],
            "qualification_only": True,
            "reviewer_calls_allowed": False,
            "fixed_role_selection_allowed": False,
            "dreaddit_audit_access_allowed": False,
            "agyw_heldout_access_allowed": False,
            "main_execution_requires_separate_freeze": True,
            "flaw_families": list(v22.core.FAMILY_ORDER),
            "development_qualification": self.config["development_qualification"],
            "outcome_policy": self.config["outcome_policy"],
            "v1_results_reused": False,
            "transport": "numeric_loopback_ollama_only",
            "this_manifest_contains_source_text": False,
            "sealed_run_contains_restricted_source_text": True,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
            "confirmatory_claims_allowed": False,
        }

    def snapshot_sha(self, path):
        name = Path(path).name
        values = {
            "v2_freeze_snapshot.json": v22.raw_sha256(v22.DEFAULT_CONFIG),
            "v1_freeze_snapshot.json": v22.raw_sha256(v22.core.V1_CONFIG),
            "policy_snapshot.json": self.v1_config["policy_file_sha256"],
        }
        if name not in values:
            raise AssertionError(f"unexpected hash path: {path}")
        return values[name]

    def call_cross_binding(self, interface_contract, core_contract):
        def load(path):
            name = Path(path).name
            if name == "v22_interface_contract.json":
                return interface_contract
            if name == "run_contract.json":
                return core_contract
            raise AssertionError(f"unexpected json path: {path}")

        with (
            mock.patch.object(v22.v1, "load_json", side_effect=load),
            mock.patch.object(v22.v1, "sha256_file", side_effect=self.snapshot_sha),
        ):
            return v22.validate_run_canary_cross_binding_v22(
                self.run_dir,
                self.config,
                v1_config=self.v1_config,
                assets=self.assets,
            )

    def make_gate(self, valid):
        rows = [v22._format_row(index) for index in range(1, 11)]
        for row in rows[:valid]:
            row.update(
                prerequisite_ready=True,
                base_gate_attempted=True,
                transport_completed=True,
                transport_schema_valid=True,
                cross_field_valid=True,
                format_valid=True,
                format_code="format_valid",
            )
        return v22.format_gate_aggregate(rows)

    def make_format_analysis(self, gate, operations):
        return {
            "document_type": "rq2_personal_local_v22_interface_format_analysis",
            "run_id": self.run_id,
            "run_outcome": "interface_format_failed",
            "scope": "base_admissibility_interface_format_only",
            "interface_format_gate": gate,
            "all_call_attempt_operations": operations,
            "semantic_base_labels_created": 0,
            "variant_calls": 0,
            "comparison_calls": 0,
            "reviewer_calls": 0,
            "fixed_role_selected": False,
            "heldout_lanes_opened": False,
            "retry_or_replacement_used": False,
            "boundary_checks": v22.expected_boundary_evidence_v22(
                self.v1_config, self.summary
            ),
            "contains_source_text": False,
            "contains_base_status_labels": False,
            "contains_readiness_labels": False,
            "contains_reason_codes_from_model": False,
            "result_label": v22.STATUS,
            "evidence_status": v22.EVIDENCE_STATUS,
            "qualification_is_rq2_performance_result": False,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
            "confirmatory_claims_allowed": False,
        }

    def make_selection(self):
        packets = []
        for packet_index in range(1, 11):
            commitments = [
                hashlib.sha256(
                    f"fresh-{packet_index}-{position}".encode()
                ).hexdigest()
                for position in range(1, 7)
            ]
            packet_id = f"PKT_{packet_index:016x}"
            packets.append(
                {
                    "packet_index": packet_index,
                    "packet_id": packet_id,
                    "bootstrap_cluster_id": packet_id,
                    "record_id_commitment": hashlib.sha256(
                        f"records-{packet_index}".encode()
                    ).hexdigest(),
                    "selection_cluster_commitments": commitments,
                    "record_count": 6,
                }
            )
        return {
            "document_type": "rq2_personal_local_v22_selection_commitments",
            "lane": "dreaddit_development",
            "corpus": "dreaddit",
            "split": self.v1_config["lanes"]["dreaddit_development"]["split"],
            "base_packet_count": 10,
            "excerpts_per_packet": 6,
            "excluded_prior_v1_commitment_count": 30,
            "excluded_prior_shared_v2_v21_commitment_count": 60,
            "excluded_total_commitment_count": 90,
            "prior_selection_or_outcome_reused": False,
            "packets": packets,
            "contains_source_text": False,
            "result_label": v22.STATUS,
        }

    def test_cross_binding_accepts_only_exact_full_contracts(self):
        interface_contract = v22.expected_v22_interface_contract(
            self.config, self.run_id, self.summary
        )
        core_contract = self.make_core_contract()
        self.assertEqual(
            self.call_cross_binding(interface_contract, core_contract), self.summary
        )

        for key in interface_contract:
            if key in {"run_id", "live_interface_canary"}:
                continue
            with self.subTest(interface_key_deleted=key):
                mutated = copy.deepcopy(interface_contract)
                del mutated[key]
                with self.assertRaisesRegex(
                    v22.V22Error, "v22_interface_contract_immutable_drift"
                ):
                    self.call_cross_binding(mutated, core_contract)
        mutated = copy.deepcopy(interface_contract)
        mutated["unknown"] = False
        with self.assertRaisesRegex(
            v22.V22Error, "v22_interface_contract_immutable_drift"
        ):
            self.call_cross_binding(mutated, core_contract)

        for key in core_contract:
            with self.subTest(core_key_deleted=key):
                mutated = copy.deepcopy(core_contract)
                del mutated[key]
                with self.assertRaises(v22.V22Error):
                    self.call_cross_binding(interface_contract, mutated)
        mutated = copy.deepcopy(core_contract)
        mutated["unknown"] = False
        with self.assertRaisesRegex(
            v22.V22Error, "v22_core_contract_fields_mismatch"
        ):
            self.call_cross_binding(interface_contract, mutated)

        for key in (
            "result_label",
            "evidence_status",
            "qualification_only",
            "reviewer_calls_allowed",
            "fixed_role_selection_allowed",
            "dreaddit_audit_access_allowed",
            "agyw_heldout_access_allowed",
            "main_execution_requires_separate_freeze",
            "v1_results_reused",
            "transport",
            "this_manifest_contains_source_text",
            "sealed_run_contains_restricted_source_text",
            "manuscript_eligible",
            "publication_or_release_eligible",
            "confirmatory_claims_allowed",
        ):
            with self.subTest(core_field=key):
                mutated = copy.deepcopy(core_contract)
                value = mutated[key]
                mutated[key] = not value if isinstance(value, bool) else "drift"
                with self.assertRaises(v22.V22Error):
                    self.call_cross_binding(interface_contract, mutated)

    def test_cross_binding_rejects_every_canary_boundary_mutation(self):
        interface_contract = v22.expected_v22_interface_contract(
            self.config, self.run_id, self.summary
        )
        core_contract = self.make_core_contract()
        for key, value in core_contract["boundary_checks"].items():
            with self.subTest(boundary_key=key):
                mutated = copy.deepcopy(core_contract)
                if key == "live_interface_canary_evidence_sha256":
                    mutated["boundary_checks"][key] = "0" * 64
                elif isinstance(value, bool):
                    mutated["boundary_checks"][key] = not value
                elif isinstance(value, int):
                    mutated["boundary_checks"][key] = value + 1
                else:
                    mutated["boundary_checks"][key] = "drift"
                with self.assertRaises(v22.V22Error):
                    self.call_cross_binding(interface_contract, mutated)

        mutated = copy.deepcopy(core_contract)
        mutated["run_id"] = "rq2plv22_20260827T120000Z_deadbeef"
        with self.assertRaisesRegex(
            v22.V22Error, "v22_canary_core_contract_run_id_mismatch"
        ):
            self.call_cross_binding(interface_contract, mutated)

    def test_interface_format_gate_validator_returns_once_and_is_exact(self):
        valid_gate = self.make_gate(10)
        self.assertIs(
            v22.validate_interface_format_gate_v22(
                valid_gate, expected_passed=True
            ),
            valid_gate,
        )
        failed_gate = self.make_gate(8)
        self.assertIs(
            v22.validate_interface_format_gate_v22(
                failed_gate, expected_passed=False
            ),
            failed_gate,
        )
        for key in valid_gate:
            with self.subTest(gate_key_deleted=key):
                mutated = copy.deepcopy(valid_gate)
                del mutated[key]
                with self.assertRaises(v22.V22Error):
                    v22.validate_interface_format_gate_v22(mutated)
        mutated = copy.deepcopy(valid_gate)
        mutated["unknown"] = False
        with self.assertRaisesRegex(v22.V22Error, "v22_format_gate_fields_mismatch"):
            v22.validate_interface_format_gate_v22(mutated)
        mutated = copy.deepcopy(failed_gate)
        mutated["format_code_counts"]["format_valid"] += 1
        with self.assertRaises(v22.V22Error):
            v22.validate_interface_format_gate_v22(mutated)

        for key in ("planned_slots", "required_format_valid", "reviewer_calls"):
            with self.subTest(gate_numeric_type=key):
                mutated = copy.deepcopy(valid_gate)
                mutated[key] = float(mutated[key])
                with self.assertRaises(v22.V22Error):
                    v22.validate_interface_format_gate_v22(mutated)

    def test_pre_semantic_leak_guard_rejects_every_frozen_key_and_value(self):
        for key in v22.PRE_SEMANTIC_FORBIDDEN_KEYS:
            with self.subTest(forbidden_key=key):
                with self.assertRaisesRegex(
                    v22.V22Error,
                    "v22_pre_semantic_artifact_contains_forbidden_key",
                ):
                    v22.reject_pre_semantic_payload_v22(
                        {"safe_outer": [{"safe_inner": {key: "opaque"}}]}
                    )
        for value in v22.PRE_SEMANTIC_FORBIDDEN_VALUES:
            with self.subTest(forbidden_value=value):
                with self.assertRaisesRegex(
                    v22.V22Error,
                    "v22_pre_semantic_artifact_contains_forbidden_value",
                ):
                    v22.reject_pre_semantic_payload_v22(
                        {"safe_outer": [{"safe_inner": value}]}
                    )

    def test_format_analysis_and_all_terminal_outcomes_are_exact(self):
        gate = self.make_gate(9)
        operations = {
            "logical_calls_started": 19,
            "physical_attempts": 19,
            "by_call_kind": {
                "construction": {"logical_calls": 10},
                "construction_verification": {"logical_calls": 9},
                "role_review": {"logical_calls": 0},
            },
        }
        analysis = self.make_format_analysis(gate, operations)
        boundary = analysis["boundary_checks"]
        self.assertIs(
            v22.validate_format_failure_analysis_v22(
                analysis, self.run_id, gate, boundary, operations
            ),
            analysis,
        )
        for key in analysis:
            with self.subTest(analysis_key_deleted=key):
                mutated = copy.deepcopy(analysis)
                del mutated[key]
                with self.assertRaises(v22.V22Error):
                    v22.validate_format_failure_analysis_v22(
                        mutated, self.run_id, gate, boundary, operations
                    )
        mutated = copy.deepcopy(analysis)
        mutated["unknown"] = False
        with self.assertRaisesRegex(
            v22.V22Error, "v22_format_analysis_fields_mismatch"
        ):
            v22.validate_format_failure_analysis_v22(
                mutated, self.run_id, gate, boundary, operations
            )
        for key in (
            "semantic_base_labels_created",
            "variant_calls",
            "comparison_calls",
            "reviewer_calls",
        ):
            with self.subTest(analysis_numeric_type=key):
                mutated = copy.deepcopy(analysis)
                mutated[key] = False
                with self.assertRaises(v22.V22Error):
                    v22.validate_format_failure_analysis_v22(
                        mutated, self.run_id, gate, boundary, operations
                    )

        for outcome in (
            "interface_format_failed",
            "qualification_failed",
            "qualification_passed",
        ):
            terminal = v22.expected_terminal_status_v22(self.run_id, outcome)
            self.assertIs(
                v22.validate_terminal_status_v22(
                    terminal, self.run_id, outcome
                ),
                terminal,
            )
            for key in terminal:
                with self.subTest(outcome=outcome, terminal_key_deleted=key):
                    mutated = copy.deepcopy(terminal)
                    del mutated[key]
                    with self.assertRaisesRegex(
                        v22.V22Error, "v22_terminal_status_immutable_drift"
                    ):
                        v22.validate_terminal_status_v22(
                            mutated, self.run_id, outcome
                        )
            for key in (
                "qualification_only",
                "permanent_stop",
                "same_run_continuation_allowed",
                "continuation_allowed",
                "separate_future_freeze_eligible",
                "continuation_requires_separate_bound_v2_main_freeze",
            ):
                with self.subTest(outcome=outcome, terminal_flag=key):
                    mutated = copy.deepcopy(terminal)
                    mutated[key] = not mutated[key]
                    with self.assertRaisesRegex(
                        v22.V22Error, "v22_terminal_status_immutable_drift"
                    ):
                        v22.validate_terminal_status_v22(
                            mutated, self.run_id, outcome
                        )

    def test_selection_is_exact_fresh_and_semantic_label_free(self):
        selection = self.make_selection()
        excluded = {
            hashlib.sha256(f"excluded-{index}".encode()).hexdigest()
            for index in range(90)
        }
        commitments = v22.validate_selection_v22(
            selection, self.v1_config, excluded
        )
        self.assertEqual(len(commitments), 60)
        self.assertTrue(commitments.isdisjoint(excluded))
        for key in selection:
            with self.subTest(selection_key_deleted=key):
                mutated = copy.deepcopy(selection)
                del mutated[key]
                with self.assertRaises(v22.V22Error):
                    v22.validate_selection_v22(
                        mutated, self.v1_config, excluded
                    )
        for key in selection["packets"][0]:
            with self.subTest(packet_key_deleted=key):
                mutated = copy.deepcopy(selection)
                del mutated["packets"][0][key]
                with self.assertRaises(v22.V22Error):
                    v22.validate_selection_v22(
                        mutated, self.v1_config, excluded
                    )
        mutated = copy.deepcopy(selection)
        mutated["packets"][0]["selection_cluster_commitments"][0] = next(
            iter(excluded)
        )
        with self.assertRaisesRegex(
            v22.V22Error, "v22_selection_freshness_or_uniqueness_drift"
        ):
            v22.validate_selection_v22(mutated, self.v1_config, excluded)
        mutated = copy.deepcopy(selection)
        mutated["base_packet_count"] = 10.0
        with self.assertRaises(v22.V22Error):
            v22.validate_selection_v22(mutated, self.v1_config, excluded)

    def test_base_gate_input_seal_is_exact_and_path_bound(self):
        expected_schema_hash = "a" * 64
        path = (
            self.run_dir
            / "base_gate"
            / "dreaddit_development"
            / "packet_01.input_seal.json"
        )
        seal = {
            "document_type": "rq2_personal_local_v22_base_gate_input_seal",
            "lane": "dreaddit_development",
            "packet_index": 1,
            "base_item_sha256": "b" * 64,
            "compact_view_sha256": "c" * 64,
            "transport_schema_sha256": expected_schema_hash,
            "target_free": True,
            "contains_source_text": False,
        }
        self.assertIs(
            v22.validate_base_gate_input_seal_v22(
                seal, path, self.run_dir, 1, expected_schema_hash
            ),
            seal,
        )
        for key in seal:
            with self.subTest(input_seal_key_deleted=key):
                mutated = copy.deepcopy(seal)
                del mutated[key]
                with self.assertRaises(v22.V22Error):
                    v22.validate_base_gate_input_seal_v22(
                        mutated, path, self.run_dir, 1, expected_schema_hash
                    )
        mutated = copy.deepcopy(seal)
        mutated["base_status"] = "admissible"
        with self.assertRaisesRegex(v22.V22Error, "v22_input_seal_fields_mismatch"):
            v22.validate_base_gate_input_seal_v22(
                mutated, path, self.run_dir, 1, expected_schema_hash
            )
        with self.assertRaisesRegex(v22.V22Error, "v22_input_seal_path_mismatch"):
            v22.validate_base_gate_input_seal_v22(
                seal,
                path.with_name("packet_02.input_seal.json"),
                self.run_dir,
                1,
                expected_schema_hash,
            )

    def test_core_inventory_filter_enters_exits_and_restores(self):
        inventory = [
            {"path": "run_contract.json"},
            {"path": "v22_interface_contract.json"},
            {"path": "interface_format_gate.json"},
        ]

        def fake_inventory(run_dir):
            return copy.deepcopy(inventory)

        with mock.patch.object(v22.v1, "safe_run_inventory", new=fake_inventory):
            self.assertIs(v22.v1.safe_run_inventory, fake_inventory)
            with v22._core_inventory_without_v22_extras():
                self.assertEqual(
                    v22.v1.safe_run_inventory(self.run_dir),
                    [{"path": "run_contract.json"}],
                )
            self.assertIs(v22.v1.safe_run_inventory, fake_inventory)

    def test_qualification_analysis_uses_type_exact_funnel_and_operations(self):
        gate = {"run_outcome": "qualification_passed"}
        boundary = v22.expected_boundary_evidence_v22(
            self.v1_config, self.summary
        )
        funnel = {"accepted": 30}
        operations = {"logical_calls_started": 120}
        analysis = {
            "document_type": "rq2_personal_local_v2_qualification_analysis",
            "run_id": self.run_id,
            "run_outcome": "qualification_passed",
            "scope": "construction_qualification_only",
            "result_label": v22.STATUS,
            "evidence_status": v22.EVIDENCE_STATUS,
            "metric_label": v22.core.METRIC_LABEL,
            "contains_source_text": False,
            "funnel": funnel,
            "qualification_gate": gate,
            "interface_format_gate_sha256": "d" * 64,
            "all_call_attempt_operations": operations,
            "reviewer_calls": 0,
            "fixed_role_selected": False,
            "heldout_lanes_opened": False,
            "v1_results_reused": False,
            "prior_v2_v21_results_reused": False,
            "human_ground_truth": False,
            "qualification_is_rq2_performance_result": False,
            "boundary_checks": boundary,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
            "confirmatory_claims_allowed": False,
        }
        with mock.patch.object(v22.v1, "sha256_file", return_value="d" * 64):
            self.assertIs(
                v22.validate_qualification_analysis_boundaries_v22(
                    analysis,
                    self.run_dir,
                    gate,
                    boundary,
                    funnel,
                    operations,
                ),
                analysis,
            )
            mutated = copy.deepcopy(analysis)
            mutated["funnel"]["accepted"] = 30.0
            with self.assertRaisesRegex(
                v22.V22Error, "v22_qualification_analysis_boundary_drift"
            ):
                v22.validate_qualification_analysis_boundaries_v22(
                    mutated,
                    self.run_dir,
                    gate,
                    boundary,
                    funnel,
                    operations,
                )


class V22FormatGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.assets = load_static()
        cls.valid_transport = cls.assets["transport_canary_fixtures"]["fixtures"][0][
            "transport_output"
        ]

    def phase_inputs(self):
        plan = [
            {
                "packet_index": index,
                "packet_id": f"opaque-packet-{index}",
                "bootstrap_cluster_id": f"opaque-cluster-{index}",
            }
            for index in range(1, 11)
        ]
        v1_config = {
            "lanes": {"dreaddit_development": {"corpus": "dreaddit"}}
        }
        paths = {"item_schema": Path("/source-free/item.schema.json")}
        return v1_config, paths, plan

    def common_patches(self, writes, fake_invoke, acceptance):
        return (
            mock.patch.object(v22.v1, "load_json", return_value={"type": "object"}),
            mock.patch.object(v22.v1, "excerpt_payload", return_value=[]),
            mock.patch.object(v22.core, "base_generation_user_prompt", return_value="PRIVATE"),
            mock.patch.object(
                v22.core,
                "map_positional_base_v2",
                return_value=({}, {}, {"opaque": True}),
            ),
            mock.patch.object(v22.v1, "build_item", return_value={"opaque": True}),
            mock.patch.object(v22.core, "compact_base_view", return_value={"opaque": True}),
            mock.patch.object(v22.core, "base_gate_user_prompt", return_value="PRIVATE"),
            mock.patch.object(v22.v1, "invoke_checkpointed_call", side_effect=fake_invoke),
            mock.patch.object(v22.v1, "recheck_service_identity"),
            mock.patch.object(v22.v1, "ensure_private_directory"),
            mock.patch.object(v22.v1, "sha256_file", return_value="0" * 64),
            mock.patch.object(
                v22.core,
                "write_v2_json",
                side_effect=lambda path, value: writes.append((Path(path), copy.deepcopy(value))),
            ),
            mock.patch.object(v22.core, "base_gate_acceptance", side_effect=acceptance),
            mock.patch.object(v22.core, "write_quarantine"),
        )

    def test_one_terminal_slot_blocks_every_semantic_label_and_all_variants(self):
        v1_config, paths, plan = self.phase_inputs()
        writes = []
        calls = []

        def invoke(*args, **kwargs):
            calls.append(kwargs["call_id"])
            if len(calls) <= 10:
                return {"status": "valid", "output": {"status": "constructed"}}
            if len(calls) == 20:
                return {"status": "terminal_error"}
            return {"status": "valid", "output": copy.deepcopy(self.valid_transport)}

        def forbidden_acceptance(*args, **kwargs):
            raise AssertionError("semantic acceptance reached before 10/10")

        patches = self.common_patches(writes, invoke, forbidden_acceptance)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12]:
            gate, base_rows, admitted = v22.run_base_interface_phase_v22(
                v1_config,
                paths,
                self.assets,
                Path("/private/source-free/run"),
                [],
                plan,
                service_baseline={},
            )
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["format_valid"], 9)
        self.assertEqual(base_rows, [])
        self.assertEqual(admitted, [])
        serialized = [value for _, value in writes]
        for forbidden in ("base_status", "readiness", "reason_codes"):
            self.assertFalse(contains_exact_key(serialized, forbidden), forbidden)
        self.assertFalse(any("variant" in call_id or "comparison" in call_id for call_id in calls))

    def test_semantic_acceptance_starts_only_after_twentieth_valid_call(self):
        v1_config, paths, plan = self.phase_inputs()
        writes = []
        call_count = 0
        acceptance_count = 0

        def invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 10:
                return {"status": "valid", "output": {"status": "constructed"}}
            return {"status": "valid", "output": copy.deepcopy(self.valid_transport)}

        def accept(*args, **kwargs):
            nonlocal acceptance_count
            self.assertEqual(call_count, 20)
            acceptance_count += 1
            return True, []

        patches = self.common_patches(writes, invoke, accept)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12]:
            gate, base_rows, admitted = v22.run_base_interface_phase_v22(
                v1_config,
                paths,
                self.assets,
                Path("/private/source-free/run"),
                [],
                plan,
                service_baseline={},
            )
        self.assertTrue(gate["passed"])
        self.assertEqual(acceptance_count, 10)
        self.assertEqual(len(base_rows), 10)
        self.assertEqual(len(admitted), 10)

    def test_format_aggregate_is_exact_denominator_and_source_free(self):
        rows = [v22._format_row(index) for index in range(1, 11)]
        for row in rows[:8]:
            row.update(
                prerequisite_ready=True,
                base_gate_attempted=True,
                transport_completed=True,
                transport_schema_valid=True,
                cross_field_valid=True,
                format_valid=True,
                format_code="format_valid",
            )
        gate = v22.format_gate_aggregate(rows)
        self.assertEqual(gate["planned_slots"], 10)
        self.assertEqual(gate["format_valid"], 8)
        self.assertFalse(gate["passed"])
        self.assertFalse(gate["semantic_evaluation_started"])
        self.assertFalse(contains_exact_key(gate, "base_status"))
        self.assertFalse(contains_exact_key(gate, "readiness"))
        self.assertFalse(contains_exact_key(gate, "reason_codes"))

    def test_qualification_pass_terminal_stops_same_run_but_allows_future_freeze(self):
        writes = []
        gate = {"run_outcome": "qualification_passed"}
        with (
            mock.patch.object(v22.v1, "aggregate_call_attempt_operations", return_value={}),
            mock.patch.object(v22.v1, "sha256_file", return_value="1" * 64),
            mock.patch.object(
                v22.core,
                "write_v2_json",
                side_effect=lambda path, value: writes.append((Path(path), copy.deepcopy(value))),
            ),
        ):
            v22.write_qualification_analysis_v22(
                {}, Path("/private/source-free/run"), {}, gate, {}
            )
        terminal = next(
            value for path, value in writes if path.name == "run_terminal_status.json"
        )
        self.assertTrue(terminal["permanent_stop"])
        self.assertFalse(terminal["same_run_continuation_allowed"])
        self.assertFalse(terminal["continuation_allowed"])
        self.assertTrue(terminal["separate_future_freeze_eligible"])
        self.assertTrue(terminal["continuation_requires_separate_bound_v2_main_freeze"])


class V22SelectionTests(unittest.TestCase):
    def test_fresh_selection_filters_all_ninety_predecessor_commitments(self):
        commitments = [hashlib.sha256(f"cluster-{index}".encode()).hexdigest() for index in range(150)]
        records = [
            {"record_id": f"record-{index}", "commitment": commitments[index]}
            for index in range(150)
        ]
        excluded = set(commitments[:90])
        observed_filtered = []
        writes = []

        def plan(filtered, **kwargs):
            observed_filtered.extend(row["commitment"] for row in filtered)
            self.assertEqual(len(filtered), 60)
            packets = []
            for packet_index in range(1, 11):
                selected = filtered[(packet_index - 1) * 6 : packet_index * 6]
                packets.append(
                    {
                        "packet_index": packet_index,
                        "packet_id": f"packet-{packet_index}",
                        "bootstrap_cluster_id": f"boot-{packet_index}",
                        "record_ids": [row["record_id"] for row in selected],
                        "selection_cluster_commitments": [
                            row["commitment"] for row in selected
                        ],
                    }
                )
            return packets

        v1_config = {
            "lanes": {
                "dreaddit_development": {"corpus": "dreaddit", "split": "development"}
            },
            "sampling_seed": 1,
            "excerpts_per_packet": 6,
        }
        with (
            mock.patch.object(
                v22.core,
                "cluster_commitment",
                side_effect=lambda row, corpus: row["commitment"],
            ),
            mock.patch.object(v22.v1, "deterministic_packet_plan", side_effect=plan),
            mock.patch.object(
                v22.core,
                "write_v2_json",
                side_effect=lambda path, value: writes.append(copy.deepcopy(value)),
            ),
        ):
            _, current = v22.select_lane_packets_v22(
                v1_config,
                {"qualification_only": True},
                Path("/private/source-free/run"),
                records,
                excluded_commitments=excluded,
            )
        self.assertTrue(set(observed_filtered).isdisjoint(excluded))
        self.assertTrue(current.isdisjoint(excluded))
        self.assertEqual(len(current), 60)
        self.assertEqual(writes[0]["excluded_total_commitment_count"], 90)
        self.assertFalse(writes[0]["prior_selection_or_outcome_reused"])


if __name__ == "__main__":
    unittest.main()
