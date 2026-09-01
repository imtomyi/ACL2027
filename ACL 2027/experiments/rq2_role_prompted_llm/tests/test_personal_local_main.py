from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/personal_local_main_freeze.json"
SPEC = importlib.util.spec_from_file_location("rq2_personal_local_main", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_observation(item_id: str, role: str, repetition: int, flags: list[str], route: str = "none"):
    return {
        "item_id": item_id,
        "prompted_role": role,
        "rating_repetition": repetition,
        "status": "valid",
        "rating": {
            "cannot_judge": [],
            "serious_error_flags": flags,
            "requested_expertise": route,
        },
    }


class PersonalLocalMainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_dreaddit_sampling_is_deterministic_and_disjoint(self):
        records = [
            {
                "record_id": f"r{i}",
                "source_id": f"s{i}",
                "split": "development_train",
                "quality": {"eligible_for_packet_sampling": True},
            }
            for i in range(40)
        ]
        lane = {"corpus": "dreaddit", "split": "development_train"}
        first = MODULE.deterministic_packet_plan(
            records, lane_name="dreaddit_development", lane=lane,
            seed=20260826, packet_count=5, excerpts_per_packet=6,
        )
        second = MODULE.deterministic_packet_plan(
            records, lane_name="dreaddit_development", lane=lane,
            seed=20260826, packet_count=5, excerpts_per_packet=6,
        )
        self.assertEqual(first, second)
        commitments = [value for packet in first for value in packet["selection_cluster_commitments"]]
        self.assertEqual(len(commitments), 30)
        self.assertEqual(len(set(commitments)), 30)

    def test_agyw_sampling_uses_five_disjoint_focus_groups(self):
        records = []
        for group in range(6):
            for speaker in range(7):
                records.append({
                    "record_id": f"r{group}_{speaker}",
                    "source_id": f"fg{group}",
                    "speaker_id": f"sp{speaker}",
                    "split": "heldout_cross_domain_evaluation",
                    "quality": {"eligible_for_packet_sampling": True},
                })
        lane = {"corpus": "agyw_focus_groups", "split": "heldout_cross_domain_evaluation"}
        plan = MODULE.deterministic_packet_plan(
            records, lane_name="agyw_heldout", lane=lane,
            seed=20260826, packet_count=5, excerpts_per_packet=6,
        )
        self.assertEqual(len({row["bootstrap_cluster_id"] for row in plan}), 5)
        commitments = [value for packet in plan for value in packet["selection_cluster_commitments"]]
        self.assertEqual(len(set(commitments)), 30)

    def test_strict_detection_and_two_of_three(self):
        hit = valid_observation("i", "generalist", 1, ["unsupported_inference"])
        self.assertTrue(MODULE.strict_detection(hit, "unsupported_inference"))
        cannot = copy.deepcopy(hit)
        cannot["rating"]["cannot_judge"] = ["insufficient_context"]
        self.assertFalse(MODULE.strict_detection(cannot, "unsupported_inference"))
        self.assertFalse(MODULE.strict_detection({"status": "terminal_error"}, "unsupported_inference"))
        flags = MODULE.ensemble_flags([
            hit,
            valid_observation("i", "generalist", 2, ["unsupported_inference"]),
            valid_observation("i", "generalist", 3, []),
        ])
        self.assertEqual(flags, {"unsupported_inference"})

    def test_fixed_role_tie_order_and_router_proxy(self):
        truths = [{"item_id": "i", "required_flag": "lost_negative_case"}]
        observations = [
            valid_observation("i", role, 1, ["lost_negative_case"], "both")
            for role in MODULE.ROLE_ORDER
        ]
        selected = MODULE.choose_fixed_role(observations, truths, MODULE.ROLE_ORDER)
        self.assertEqual(selected["selected_role"], "generalist")
        self.assertEqual(MODULE.diagnostic_route_proxy(observations[0]), "both")
        routed = MODULE.route_flags(
            "both", {"generalist": set(), "methods": {"a"}, "domain": {"b"}}
        )
        self.assertEqual(routed, {"a", "b"})

    def test_bootstrap_minimum_and_seeded_interval(self):
        few = [{"cluster_id": str(i), "x": True, "warrantroute_proxy": True, "fixed_role": False}
               for i in range(4)]
        self.assertFalse(MODULE.cluster_bootstrap_intervals(
            few, metric_keys=["x"], resamples=20, seed=20270826, minimum_clusters=5
        )["estimable"])
        enough = few + [{"cluster_id": "4", "x": False, "warrantroute_proxy": False, "fixed_role": True}]
        first = MODULE.cluster_bootstrap_intervals(
            enough, metric_keys=["x"], resamples=50, seed=20270826, minimum_clusters=5
        )
        second = MODULE.cluster_bootstrap_intervals(
            enough, metric_keys=["x"], resamples=50, seed=20270826, minimum_clusters=5
        )
        self.assertTrue(first["estimable"])
        self.assertEqual(first, second)

    def test_frozen_decoding_uses_distinct_repetition_seeds(self):
        seeds = self.config["decoding"]["reviewer"]["repetition_seeds"]
        self.assertEqual(seeds, [2027082601, 2027082602, 2027082603])
        self.assertEqual(len(set(seeds)), 3)
        observed = []
        for repetition in (1, 2, 3):
            request = MODULE.build_model_request(
                self.config, model_role="reviewer", system_prompt="guide",
                user_prompt="item", output_schema={"type": "object"},
                rating_call=True, rating_repetition=repetition,
            )
            observed.append(request["options"]["seed"])
            self.assertEqual(request["options"]["num_predict"], 512)
            self.assertFalse(request["think"])
        self.assertEqual(observed, seeds)
        generator = MODULE.build_model_request(
            self.config, model_role="generator", system_prompt="guide",
            user_prompt="item", output_schema={"type": "object"},
            rating_call=False, rating_repetition=None,
        )
        self.assertEqual(generator["options"]["num_predict"], 1536)
        self.assertNotIn("seed", generator["options"])
        self.assertFalse(generator["think"])
        verifier = MODULE.build_model_request(
            self.config, model_role="verifier", system_prompt="guide",
            user_prompt="blinded pair", output_schema={"type": "object"},
            rating_call=False, rating_repetition=None,
        )
        self.assertEqual(verifier["model"], "gemma3:4b")
        self.assertEqual(verifier["options"]["seed"], 2027082699)
        self.assertEqual(verifier["options"]["num_predict"], 768)
        self.assertFalse(verifier["think"])

    def test_family_topologies_and_blinded_acceptance(self):
        excerpts = [
            {
                "display_order": i + 1,
                "excerpt_id": f"EXC_{i:016x}",
                "source_id": f"SRC_{i:016x}",
                "speaker_id": None,
                "local_context": None,
                "text": f"SOURCE_FREE_TEST_{i}",
            }
            for i in range(6)
        ]
        base_roles = {
            excerpts[0]["excerpt_id"]: ("support", "support"),
            excerpts[1]["excerpt_id"]: ("support", "support"),
            excerpts[2]["excerpt_id"]: ("counterevidence", "counter"),
            **{row["excerpt_id"]: ("context_only", None) for row in excerpts[3:]},
        }
        base = MODULE.build_item(
            lane_name="dreaddit_development", corpus="dreaddit", packet_id="PKT_test",
            output_key="base", interpretation={
                "theme_name": "Theme", "claim": "Base claim", "explanation": "Base explanation",
                "boundary_conditions": ["Base boundary"],
            }, roles=base_roles, excerpts=excerpts,
        )
        for family in MODULE.FAMILY_ORDER:
            roles = MODULE.deterministic_variant_roles(family, excerpts, base_roles)
            variant = MODULE.build_item(
                lane_name="dreaddit_development", corpus="dreaddit", packet_id="PKT_test",
                output_key=family, interpretation={
                    "theme_name": "Theme", "claim": f"Changed {family}",
                    "explanation": "Changed explanation", "boundary_conditions": [],
                }, roles=roles, excerpts=excerpts,
            )
            structural = MODULE.construction_invariants(family, base, variant, roles)
            self.assertTrue(structural["passed"], structural)
            output = {
                "verification_schema_version": "rq2-construction-verification-v1",
                "base_status": "warranted",
                "comparison_clarity": "clear",
                "present_flaws": [family],
                "other_material_flaw": False,
                "single_material_difference": True,
                "anchors": [{
                    "flaw_family": family,
                    "excerpt_ids": [excerpts[0]["excerpt_id"]],
                    "interpretation_fields": ["claim"],
                    "reason_code": MODULE.REASON_BY_FAMILY[family],
                }],
            }
            accepted, reasons = MODULE.verifier_acceptance(family, variant, structural, output)
            self.assertTrue(accepted, reasons)
            other_family = next(value for value in MODULE.FAMILY_ORDER if value != family)
            output["present_flaws"] = [family, other_family]
            accepted, _ = MODULE.verifier_acceptance(family, variant, structural, output)
            self.assertFalse(accepted)

    def test_truncation_is_terminal_validation_failure(self):
        with self.assertRaises(MODULE.ResponseValidationError):
            MODULE.parse_model_response(
                {"model": "llama3.1:8b", "done": True, "done_reason": "length",
                 "message": {"content": "{}"}},
                expected_model="llama3.1:8b", output_schema={"type": "object"},
            )

    def test_indexed_loader_never_decodes_nonrequested_line(self):
        record = {
            "record_id": "fixture-record",
            "corpus": "dreaddit",
            "split": "development_train",
            "source_id": "fixture-source",
            "speaker_id": None,
            "text": "SOURCE_FREE_TEST_ONLY",
            "context": {},
            "quality": {"eligible_for_packet_sampling": True},
        }
        first = (json.dumps(record, sort_keys=True) + "\n").encode()
        second = b"INTENTIONALLY_NOT_JSON_AND_MUST_NOT_BE_DECODED\n"
        payload = first + second
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_bytes(payload)
            index = {
                "document_type": "rq2_source_free_jsonl_split_index",
                "index_version": "rq2-source-free-split-index-v1",
                "records_path": "dataset/deidentified/dreaddit/records.jsonl",
                "records_sha256": hashlib.sha256(payload).hexdigest(),
                "file_size_bytes": len(payload),
                "line_count": 2,
                "splits": {
                    "development_train": [{
                        "line_number": 1, "byte_offset": 0, "byte_length": len(first),
                        "line_sha256": hashlib.sha256(first).hexdigest(),
                    }],
                    "in_domain_audit": [{
                        "line_number": 2, "byte_offset": len(first), "byte_length": len(second),
                        "line_sha256": hashlib.sha256(second).hexdigest(),
                    }],
                },
                "contains_source_text": False,
                "stored_fields": ["split", "line_number", "byte_offset", "byte_length", "line_sha256"],
            }
            loaded = MODULE.load_bound_records(
                path, "dreaddit", hashlib.sha256(payload).hexdigest(),
                "development_train", split_index=index,
            )
        self.assertEqual([row["record_id"] for row in loaded], ["fixture-record"])

    def test_protocol_mutations_fail_before_any_corpus_access(self):
        for key, value, marker in (
            ("sampling_seed", 1, "sampling_seed_mismatch"),
            ("flaw_families", ["unsupported_evidence"], "flaw_family_freeze_mismatch"),
        ):
            changed = copy.deepcopy(self.config)
            changed[key] = value
            with self.assertRaisesRegex(MODULE.PersonalLocalError, marker):
                MODULE.validate_freeze(changed, include_record_hashes=False, config_path=CONFIG)

    def test_success_resume_and_request_only_attempt_accounting(self):
        schema = {
            "type": "object", "required": ["value"],
            "properties": {"value": {"type": "string"}}, "additionalProperties": False,
        }
        response = {
            "model": "qwen3:8b", "done": True, "done_reason": "stop",
            "message": {"content": json.dumps({"value": "ok"})},
            "prompt_eval_count": 4, "eval_count": 2,
        }
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            call_id = "generate_dreaddit_development_fixture"
            with mock.patch.object(MODULE, "api_json", return_value=response) as api:
                first = MODULE.invoke_checkpointed_call(
                    self.config, run_dir, call_id=call_id, model_role="generator",
                    system_prompt="system", user_prompt="user", output_schema=schema,
                    rating_call=False, rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
            self.assertEqual(first["attempt"], 1)
            self.assertEqual(api.call_count, 1)
            with mock.patch.object(MODULE, "api_json", side_effect=AssertionError("resume called API")):
                resumed = MODULE.invoke_checkpointed_call(
                    self.config, run_dir, call_id=call_id, model_role="generator",
                    system_prompt="system", user_prompt="user", output_schema=schema,
                    rating_call=False, rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
            self.assertEqual(resumed, first)

            second_call = "generate_dreaddit_development_interrupted"
            request = MODULE.build_model_request(
                self.config, model_role="generator", system_prompt="system",
                user_prompt="user", output_schema=schema, rating_call=False,
                rating_repetition=None,
            )
            call_dir = run_dir / "raw" / "calls" / second_call
            MODULE.ensure_private_directory(call_dir)
            MODULE.write_json_once(call_dir / "attempt_01_request.json", request)
            with mock.patch.object(MODULE, "api_json", return_value=response):
                recovered = MODULE.invoke_checkpointed_call(
                    self.config, run_dir, call_id=second_call, model_role="generator",
                    system_prompt="system", user_prompt="user", output_schema=schema,
                    rating_call=False, rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
            self.assertEqual(recovered["attempt"], 2)
            operations = MODULE.aggregate_call_attempt_operations(run_dir)
            self.assertEqual(operations["logical_calls_started"], 2)
            self.assertEqual(operations["physical_attempts"], 3)
            self.assertEqual(operations["retry_or_resume_attempts"], 1)
            self.assertEqual(operations["interrupted_attempts"], 1)

    def test_request_only_verifier_checkpoint_is_terminal_without_retry(self):
        schema = {
            "type": "object", "required": ["value"],
            "properties": {"value": {"type": "string"}}, "additionalProperties": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            call_id = "verify_dreaddit_development_DJI_0000000000000000"
            request = MODULE.build_model_request(
                self.config, model_role="verifier", system_prompt="system",
                user_prompt="blinded pair", output_schema=schema,
                rating_call=False, rating_repetition=None,
            )
            call_dir = run_dir / "raw" / "calls" / call_id
            MODULE.ensure_private_directory(call_dir)
            MODULE.write_json_once(call_dir / "attempt_01_request.json", request)
            with mock.patch.object(
                MODULE, "api_json", side_effect=AssertionError("verifier retry dispatched")
            ) as api:
                result = MODULE.invoke_checkpointed_call(
                    self.config, run_dir, call_id=call_id, model_role="verifier",
                    system_prompt="system", user_prompt="blinded pair", output_schema=schema,
                    rating_call=False, rating_repetition=None,
                    retry_transport_on_explicit_resume=False,
                )
            self.assertEqual(result["status"], "terminal_error")
            self.assertEqual(result["error"]["stage"], "interrupted")
            self.assertEqual(api.call_count, 0)
            self.assertFalse((call_dir / "attempt_02_request.json").exists())


if __name__ == "__main__":
    unittest.main()
