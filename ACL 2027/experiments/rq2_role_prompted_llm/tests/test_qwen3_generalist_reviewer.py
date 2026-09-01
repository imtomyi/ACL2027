#!/usr/bin/env python3
"""Source-free tests for the Qwen3 Generalist reviewer component."""

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
SCRIPT = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_reviewer.py"
CONFIG = ROOT / "experiments/rq2_role_prompted_llm/config/qwen3_generalist_reviewer_freeze.json"
SPEC = importlib.util.spec_from_file_location("qwen3_generalist_reviewer_tests", SCRIPT)
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
        "created_at": "2026-08-28T00:00:00Z",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(rating)},
        "prompt_eval_count": 1200,
        "eval_count": 80,
    }


class Qwen3GeneralistReviewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = MODULE.load_json(CONFIG)
        cls.assets = MODULE.validate_freeze(cls.config)

    def test_static_contract_binds_qwen_as_generalist_reviewer(self) -> None:
        actor = self.config["reviewer_actor"]
        self.assertEqual(actor["model_id"], "qwen3:8b")
        self.assertEqual(actor["task_role"], "reviewer")
        self.assertEqual(actor["prompted_role"], "generalist")
        self.assertFalse(self.config["source_bearing_execution_allowed"])
        self.assertFalse(self.config["manuscript_eligible"])

    def test_request_is_hardened_blinded_and_seeded(self) -> None:
        item = MODULE.inert_canary_item()
        request = MODULE.build_rating_request(
            self.config,
            self.assets,
            item,
            repetition=1,
        )
        self.assertEqual(request["model"], "qwen3:8b")
        self.assertEqual(request["options"]["seed"], 2027082601)
        self.assertEqual(request["options"]["num_ctx"], 8192)
        self.assertEqual(request["options"]["num_predict"], 512)
        self.assertFalse(request["think"])
        self.assertFalse(request["truncate"])
        self.assertFalse(request["shift"])
        self.assertNotIn("tools", request)
        self.assertEqual(
            request["format"],
            self.assets["shared_rating_transport_schema"],
        )
        self.assertNotIn("allOf", request["format"])
        payload = request["messages"][1]["content"]
        self.assertIn("PKT_SOURCE_FREE_CANARY", payload)
        for forbidden in MODULE.FORBIDDEN_ITEM_KEYS:
            self.assertNotIn(f'"{forbidden}"', payload)

    def test_all_three_repetitions_use_distinct_frozen_seeds(self) -> None:
        item = MODULE.inert_canary_item()
        observed = [
            MODULE.build_rating_request(
                self.config,
                self.assets,
                item,
                repetition=repetition,
            )["options"]["seed"]
            for repetition in (1, 2, 3)
        ]
        self.assertEqual(observed, [2027082601, 2027082602, 2027082603])

    def test_valid_response_passes_full_shared_schema(self) -> None:
        rating, context = MODULE.parse_rating_response(
            ollama_response(valid_rating()),
            expected_model="qwen3:8b",
            rating_schema=self.assets["shared_rating_schema"],
            config=self.config,
        )
        self.assertEqual(rating, valid_rating())
        self.assertEqual(context["prompt_eval_count"], 1200)
        self.assertFalse(
            MODULE.detection_hit(
                rating,
                "unsupported_inference",
                self.assets["shared_rating_schema"],
            )
        )

    def test_schema_errors_model_drift_and_truncation_fail_closed(self) -> None:
        cases = []
        missing = valid_rating()
        del missing["rationale"]
        cases.append(ollama_response(missing))
        contradiction = valid_rating()
        contradiction["evidential_credibility"] = None
        contradiction["cannot_judge"] = ["evidential_credibility"]
        contradiction["disposition"] = "accept"
        cases.append(ollama_response(contradiction))
        cases.append(ollama_response(valid_rating(), model="llama3.1:8b"))
        truncated = ollama_response(valid_rating())
        truncated["done_reason"] = "length"
        cases.append(truncated)
        for response in cases:
            with self.subTest(response=response.get("done_reason")):
                with self.assertRaises(MODULE.ResponseValidationError):
                    MODULE.parse_rating_response(
                        response,
                        expected_model="qwen3:8b",
                        rating_schema=self.assets["shared_rating_schema"],
                        config=self.config,
                    )

    def test_cannot_judge_and_terminal_failure_are_misses(self) -> None:
        cannot = valid_rating()
        cannot.update(
            {
                "evidential_credibility": None,
                "cannot_judge": ["evidential_credibility"],
                "disposition": "escalate",
                "requested_expertise": "qualitative_methods",
                "serious_error_flags": ["unsupported_inference"],
            }
        )
        self.assertFalse(
            MODULE.detection_hit(
                cannot,
                "unsupported_inference",
                self.assets["shared_rating_schema"],
            )
        )
        self.assertFalse(
            MODULE.detection_hit(
                None,
                "unsupported_inference",
                self.assets["shared_rating_schema"],
            )
        )
        hit = valid_rating()
        hit.update(
            {
                "evidential_credibility": 2,
                "disposition": "revise",
                "serious_error_flags": ["unsupported_inference"],
            }
        )
        self.assertTrue(
            MODULE.detection_hit(
                hit,
                "unsupported_inference",
                self.assets["shared_rating_schema"],
            )
        )
        self.assertFalse(
            MODULE.detection_hit(
                {
                    "cannot_judge": [],
                    "serious_error_flags": ["unsupported_inference"],
                },
                "unsupported_inference",
                self.assets["shared_rating_schema"],
            )
        )
        with self.assertRaisesRegex(
            MODULE.GeneralistReviewerError,
            "required_flag_not_in_frozen_enum",
        ):
            MODULE.detection_hit(
                hit,
                "not_a_frozen_flag",
                self.assets["shared_rating_schema"],
            )

    def test_generator_and_non_generalist_bindings_are_rejected(self) -> None:
        generator = copy.deepcopy(self.config)
        generator["reviewer_actor"]["task_role"] = "generator"
        with self.assertRaisesRegex(MODULE.GeneralistReviewerError, "qwen_generator_role_rejected"):
            MODULE.validate_freeze(generator)
        methods = copy.deepcopy(self.config)
        methods["reviewer_actor"]["prompted_role"] = "methods"
        with self.assertRaisesRegex(MODULE.GeneralistReviewerError, "non_generalist_role_rejected"):
            MODULE.validate_freeze(methods)
        actor_drift = copy.deepcopy(self.config)
        actor_drift["reviewer_actor"]["actor_id"] = "changed_actor"
        with self.assertRaisesRegex(MODULE.GeneralistReviewerError, "reviewer_actor_id_drift"):
            MODULE.validate_freeze(actor_drift)
        version_drift = copy.deepcopy(self.config)
        version_drift["service"]["ollama_version"] = "changed"
        with self.assertRaisesRegex(MODULE.GeneralistReviewerError, "service_version_drift"):
            MODULE.validate_freeze(version_drift)
        path_drift = copy.deepcopy(self.config)
        path_drift["assets"]["generalist_prompt"]["file"] = (
            "experiments/rq2_role_prompted_llm/prompts/methods_v1.md"
        )
        with self.assertRaisesRegex(MODULE.GeneralistReviewerError, "generalist_prompt_path_drift"):
            MODULE.validate_freeze(path_drift)

    def test_hash_drift_fails_before_service_contact(self) -> None:
        drifted = copy.deepcopy(self.config)
        drifted["assets"]["generalist_prompt"]["sha256"] = "0" * 64
        with mock.patch.object(
            MODULE,
            "_get_service_json",
            side_effect=AssertionError("service contacted"),
        ):
            with self.assertRaisesRegex(
                MODULE.GeneralistReviewerError,
                "generalist_prompt_configured_hash_drift",
            ):
                MODULE.validate_freeze(drifted)

    def test_dry_run_reads_no_corpus_or_storage_and_writes_nothing(self) -> None:
        original = MODULE.read_regular_bytes
        observed: list[Path] = []

        def guarded(path: Path) -> bytes:
            observed.append(path)
            text = str(path)
            if "/dataset/" in text or "/Storage/" in text or text.endswith(".jsonl"):
                raise AssertionError("source-bearing path opened")
            return original(path)

        with (
            mock.patch.object(MODULE, "read_regular_bytes", side_effect=guarded),
            mock.patch.object(MODULE, "_get_service_json", side_effect=AssertionError("service contacted")),
            mock.patch.object(MODULE, "_post_source_free_canary", side_effect=AssertionError("service contacted")),
            mock.patch.object(sys, "argv", [str(SCRIPT), "dry-run"]),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(MODULE.main(), 0)
        self.assertTrue(observed)
        self.assertFalse(any("/dataset/" in str(path) for path in observed))
        self.assertFalse(any("/Storage/" in str(path) for path in observed))

    def test_source_bearing_run_is_blocked_before_service(self) -> None:
        with (
            mock.patch.object(MODULE, "_get_service_json", side_effect=AssertionError("service contacted")),
            mock.patch.object(MODULE, "_post_source_free_canary", side_effect=AssertionError("service contacted")),
            mock.patch.object(sys, "argv", [str(SCRIPT), "run"]),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(MODULE.main(), 2)

    def test_source_free_canary_exercises_actual_request_and_schema_path(self) -> None:
        baseline = {
            "status": "passed",
            "endpoint": "http://127.0.0.1:11434",
            "ollama_version": "0.18.0",
            "model_id": "qwen3:8b",
            "model_digest": self.config["reviewer_actor"]["local_manifest_file_sha256"],
            "source_text_accessed": False,
        }
        expected_request = MODULE.build_rating_request(
            self.config,
            self.assets,
            MODULE.inert_canary_item(),
            repetition=1,
        )
        with (
            mock.patch.object(MODULE, "preflight_service", side_effect=[baseline, baseline]),
            mock.patch.object(
                MODULE,
                "_post_source_free_canary",
                return_value=(expected_request, ollama_response(valid_rating())),
            ),
        ):
            result = MODULE.run_source_free_canary()
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["canary_rating_schema_valid"])
        self.assertFalse(result["source_text_accessed"])
        self.assertFalse(result["outputs_written"])
        self.assertEqual(expected_request["model"], "qwen3:8b")
        self.assertFalse(expected_request["truncate"])
        self.assertFalse(expected_request["shift"])
        self.assertEqual(result["model_id"], "qwen3:8b")
        self.assertEqual(result["rating_repetition"], 1)
        self.assertEqual(result["seed"], 2027082601)
        self.assertEqual(len(result["request_sha256"]), 64)
        self.assertEqual(len(result["validation_schema_sha256"]), 64)

    def test_only_post_function_constructs_exact_canary_and_accepts_no_payload(self) -> None:
        self.assertFalse(hasattr(MODULE, "_http_json"))
        self.assertEqual(
            set(inspect.signature(MODULE._post_source_free_canary).parameters),
            set(),
        )

        expected_response = ollama_response(valid_rating())

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def geturl(self):
                return "http://127.0.0.1:11434/api/chat"

            def read(self):
                return json.dumps(expected_response).encode("utf-8")

        with mock.patch.object(
            MODULE.LOCAL_ONLY_OPENER,
            "open",
            return_value=FakeResponse(),
        ) as opened:
            request_payload, response_payload = MODULE._post_source_free_canary()
        self.assertEqual(response_payload, expected_response)
        self.assertEqual(
            request_payload,
            MODULE.build_rating_request(
                self.config,
                self.assets,
                MODULE.inert_canary_item(),
                repetition=1,
            ),
        )
        sent_request = opened.call_args.args[0]
        self.assertEqual(json.loads(sent_request.data), request_payload)
        sent_payload_text = sent_request.data.decode("utf-8")
        self.assertIn("PKT_SOURCE_FREE_CANARY", sent_payload_text)
        self.assertNotIn("target_flaw", sent_payload_text)


if __name__ == "__main__":
    unittest.main()
