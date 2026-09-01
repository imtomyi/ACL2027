#!/usr/bin/env python3
"""Source-free tests for the v2.3 prompt-limit diagnostic."""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_personal_local_main_v23.py"
SPEC = importlib.util.spec_from_file_location("rq2_personal_local_main_v23_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
v23 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v23
SPEC.loader.exec_module(v23)


def load_static():
    config = v23.v1.load_json(v23.DEFAULT_CONFIG)
    v1_config, assets = v23.validate_v23_freeze(
        config, config_path=v23.DEFAULT_CONFIG
    )
    return config, v1_config, assets


def overflow_error():
    body = json.dumps(
        {"error": "the input length exceeds the context length"},
        separators=(",", ":"),
    ).encode("utf-8")
    return v23.v1.TransportError(
        error_type="LocalHTTPError",
        raw={
            "http_status": 400,
            "body_base64": base64.b64encode(body).decode("ascii"),
            "body_sha256": v23.guard.sha256_bytes(body),
            "body_size_bytes": len(body),
        },
    )


def response_for(output, *, prompt_tokens=4096):
    return {
        "model": "gemma3:4b",
        "created_at": "source-free-test",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(output)},
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": 1,
        "eval_count": 32,
        "eval_duration": 1,
        "total_duration": 2,
        "load_duration": 0,
    }


class PromptLimitGuardTests(unittest.TestCase):
    def test_exact_limit_stays_single_and_one_byte_over_chunks(self):
        fixed = "RULE\n"
        exact = v23.guard.build_chunk_plan(
            fixed_prefix=fixed,
            chunkable_payload="x" * 11,
            max_user_prompt_bytes=16,
            max_chunks=4,
        )
        over = v23.guard.build_chunk_plan(
            fixed_prefix=fixed,
            chunkable_payload="x" * 12,
            max_user_prompt_bytes=16,
            max_chunks=4,
        )
        self.assertEqual(exact.chunk_count, 1)
        self.assertEqual(over.chunk_count, 2)
        self.assertEqual("".join(over.payload_chunks), "x" * 12)

    def test_utf8_chunks_are_lossless_and_do_not_split_codepoints(self):
        text = "alpha βeta\n" * 9
        chunks = v23.guard.split_utf8_exact(text, 13)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk.encode("utf-8")) <= 13 for chunk in chunks))
        self.assertTrue(all(chunk.encode("utf-8").decode("utf-8") == chunk for chunk in chunks))

    def test_fixed_instruction_overhead_fails_before_planning(self):
        with self.assertRaisesRegex(
            v23.guard.PromptLimitError, "fixed_prefix_exceeds_budget"
        ):
            v23.guard.build_chunk_plan(
                fixed_prefix="complete instruction",
                chunkable_payload="padding",
                max_user_prompt_bytes=10,
                max_chunks=4,
            )

    def test_only_explicit_source_free_consensus_scope_is_approved(self):
        v23.guard.require_approved_chunking_scope(
            component="source_free_inert_padding_only", reducer="exact_consensus"
        )
        with self.assertRaisesRegex(
            v23.guard.PromptLimitError, "semantic_chunk_contract_required"
        ):
            v23.guard.require_approved_chunking_scope(
                component="real_six_excerpt_packet", reducer="majority_vote"
            )

    def test_hardened_request_disables_truncation_and_shift(self):
        original = {"model": "local", "options": {"num_ctx": 8192}}
        hardened = v23.guard.harden_ollama_request(original, num_ctx=16384)
        self.assertEqual(original["options"]["num_ctx"], 8192)
        self.assertEqual(hardened["options"]["num_ctx"], 16384)
        self.assertIs(hardened["truncate"], False)
        self.assertIs(hardened["shift"], False)

    def test_exact_ollama_overflow_is_narrowly_recognized(self):
        self.assertTrue(v23.guard.is_ollama_context_overflow(overflow_error()))
        other = overflow_error()
        other.raw["http_status"] = 500
        self.assertFalse(v23.guard.is_ollama_context_overflow(other))

    def test_context_accounting_requires_output_headroom(self):
        accepted = v23.guard.validate_successful_context_use(
            {"prompt_eval_count": 4096, "eval_count": 20},
            num_ctx=8192,
            reserved_output_tokens=768,
            safety_margin_tokens=512,
        )
        self.assertEqual(accepted["prompt_eval_count"], 4096)
        with self.assertRaisesRegex(
            v23.guard.PromptLimitError, "output_headroom_insufficient"
        ):
            v23.guard.validate_successful_context_use(
                {"prompt_eval_count": 7100, "eval_count": 20},
                num_ctx=8192,
                reserved_output_tokens=768,
                safety_margin_tokens=512,
            )
        with self.assertRaisesRegex(
            v23.guard.PromptLimitError, "prompt_token_count_missing"
        ):
            v23.guard.validate_successful_context_use(
                {"eval_count": 20},
                num_ctx=8192,
                reserved_output_tokens=768,
                safety_margin_tokens=512,
            )

    def test_exact_consensus_has_no_majority_fallback(self):
        self.assertEqual(v23.guard.exact_consensus([{"x": True}, {"x": True}]), {"x": True})
        with self.assertRaisesRegex(
            v23.guard.PromptLimitError, "exact_consensus_failed"
        ):
            v23.guard.exact_consensus([{"x": True}, {"x": True}, {"x": False}])


class V23StaticContractTests(unittest.TestCase):
    def test_frozen_predecessor_is_byte_identical(self):
        self.assertEqual(v23._raw_sha256(v23.V22_RUNNER), v23.V22_RUNNER_SHA256)
        self.assertEqual(v23._raw_sha256(v23.V22_CONFIG), v23.V22_CONFIG_SHA256)
        self.assertEqual(v23._raw_sha256(v23.PROMPT_GUARD), v23.PROMPT_GUARD_SHA256)

    def test_validation_opens_no_records_storage_or_service(self):
        config = v23.v1.load_json(v23.DEFAULT_CONFIG)
        with (
            mock.patch.object(
                v23.v1, "load_bound_records", side_effect=AssertionError("records opened")
            ),
            mock.patch.object(
                v23.v1, "preflight_service", side_effect=AssertionError("service contacted")
            ),
        ):
            v1_config, assets = v23.validate_v23_freeze(
                config, config_path=v23.DEFAULT_CONFIG
            )
            summary = v23.static_summary(config, v1_config, assets)
        self.assertEqual(summary["v23_static_status"], "passed")
        self.assertFalse(summary["data_opened"])
        self.assertFalse(summary["storage_opened"])
        self.assertFalse(summary["service_contacted"])

    def test_canary_plan_is_lossless_and_repeats_full_instruction(self):
        config, v1_config, assets = load_static()
        rows = v23.prepare_chunked_canary(config, v1_config, assets)
        self.assertEqual(len(rows), 3)
        for row in rows:
            fixed, payload = v23._fixed_and_chunkable_canary(assets, row["case"])
            plan = row["plan"]
            self.assertEqual(plan.chunk_count, 3)
            self.assertEqual("".join(plan.payload_chunks), payload)
            self.assertTrue(all(value.startswith(fixed) for value in plan.user_prompts))
            self.assertTrue(all(size <= 8192 for size in plan.user_prompt_bytes))
            self.assertTrue(
                all(request["truncate"] is False for request in row["requests"])
            )
            self.assertTrue(all(request["shift"] is False for request in row["requests"]))


class V23ChunkedCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.v1_config, cls.assets = load_static()

    def fixture_response(self, request):
        user = request["messages"][-1]["content"]
        for case in self.assets["transport_canary_fixtures"]["fixtures"]:
            if case["canary_instruction"] in user:
                return response_for(case["transport_output"])
        raise AssertionError("unknown source-free fixture")

    def test_all_nine_chunks_pass_with_exact_consensus_and_no_writes(self):
        calls = []

        def api(endpoint, path, request, *, timeout):
            calls.append(copy.deepcopy(request))
            return self.fixture_response(request)

        with (
            mock.patch.object(v23.v1, "api_json", side_effect=api),
            mock.patch.object(
                v23.v1, "write_json_once", side_effect=AssertionError("write attempted")
            ),
            mock.patch.object(
                v23.v1, "load_bound_records", side_effect=AssertionError("records opened")
            ),
        ):
            result = v23.run_chunked_canary(
                self.config, self.v1_config, self.assets
            )
        self.assertEqual(len(calls), 9)
        self.assertEqual(result["generated_physical_attempts"], 9)
        self.assertEqual(result["pre_generation_overflow_rejections"], 0)
        self.assertEqual(set(result["chunk_counts"].values()), {3})
        self.assertTrue(result["automatic_chunking_used"])
        self.assertFalse(result["model_content_retained"])
        self.assertTrue(all(call["truncate"] is False for call in calls))
        self.assertTrue(all(call["shift"] is False for call in calls))

    def test_exact_overflow_replans_before_generation(self):
        calls = 0

        def api(endpoint, path, request, *, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise overflow_error()
            return self.fixture_response(request)

        with mock.patch.object(v23.v1, "api_json", side_effect=api):
            result = v23.run_chunked_canary(
                self.config, self.v1_config, self.assets
            )
        self.assertEqual(result["pre_generation_overflow_rejections"], 1)
        self.assertEqual(
            calls,
            result["generated_physical_attempts"]
            + result["pre_generation_overflow_rejections"],
        )
        first_code = "admissible_all_true_all_ready"
        self.assertGreater(result["chunk_counts"][first_code], 3)

    def test_different_chunk_output_stops_without_majority_vote(self):
        calls = 0

        def api(endpoint, path, request, *, timeout):
            nonlocal calls
            calls += 1
            response = self.fixture_response(request)
            if calls == 2:
                case = self.assets["transport_canary_fixtures"]["fixtures"][1]
                response = response_for(case["transport_output"])
            return response

        with mock.patch.object(v23.v1, "api_json", side_effect=api):
            with self.assertRaisesRegex(v23.V23Error, "chunk_02"):
                v23.run_chunked_canary(self.config, self.v1_config, self.assets)
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
