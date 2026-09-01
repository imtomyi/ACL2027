#!/usr/bin/env python3
"""Source-free tests for the Qwen3 Generalist private-local pilot."""

from __future__ import annotations

import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_qwen3_generalist_private_pilot.py"
)
SPEC = importlib.util.spec_from_file_location("qwen3_generalist_private_pilot", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PILOT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PILOT
SPEC.loader.exec_module(PILOT)


def minimal_plan_config() -> dict:
    return {
        "dataset": {
            "local_split": "in_domain_audit",
            "excerpts_per_base_packet": 6,
        },
        "sampling": {
            "sampling_seed": 2027082801,
            "candidate_pool_size": 15,
            "excluded_prior_audit_cluster_commitments": [
                PILOT.sha256_bytes(b"excluded-source")
            ],
        },
    }


def inert_records(count: int = 100) -> list[dict]:
    rows = []
    for index in range(count):
        source_id = "excluded-source" if index == 0 else f"inert-source-{index:03d}"
        rows.append(
            {
                "record_id": f"inert-record-{index:03d}",
                "source_id": source_id,
                "split": "in_domain_audit",
                "text": f"INERT_{index:03d}",
                "quality": {"eligible_for_packet_sampling": True},
            }
        )
    return rows


def valid_rating(flags: list[str], cannot_judge: list[str] | None = None) -> dict:
    return {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": 2,
        "voice_boundary_preservation": 2,
        "scope_calibration": 2,
        "cannot_judge": [] if cannot_judge is None else cannot_judge,
        "confidence": 4,
        "disposition": "revise",
        "requested_expertise": "none",
        "serious_error_flags": flags,
        "rationale": "INERT rationale.",
    }


class PrivatePilotTests(unittest.TestCase):
    def test_family_assignment_is_three_complete_frozen_rounds(self) -> None:
        observed = [PILOT.family_for_candidate_slot(slot) for slot in range(1, 16)]
        expected = [
            (family, round_number)
            for round_number in (1, 2, 3)
            for family in PILOT.FAMILY_ORDER
        ]
        self.assertEqual(observed, expected)

    def test_candidate_plan_is_fresh_balanced_and_component_disjoint(self) -> None:
        config = minimal_plan_config()
        plan = PILOT.build_candidate_plan(inert_records(), config)
        self.assertEqual(len(plan), 15)
        self.assertEqual(
            {family: sum(row["family"] == family for row in plan) for family in PILOT.FAMILY_ORDER},
            {family: 3 for family in PILOT.FAMILY_ORDER},
        )
        commitments = [value for row in plan for value in row["source_cluster_commitments"]]
        self.assertEqual(len(commitments), 90)
        self.assertEqual(len(set(commitments)), 90)
        self.assertNotIn(PILOT.sha256_bytes(b"excluded-source"), commitments)
        self.assertTrue(all(len(row["records"]) == 6 for row in plan))

    def test_candidate_plan_does_not_adapt_or_replace(self) -> None:
        public = PILOT.source_free_plan(PILOT.build_candidate_plan(inert_records(), minimal_plan_config()))
        self.assertFalse(public["adaptive_stopping_allowed"])
        self.assertFalse(public["replacement_allowed"])
        self.assertEqual(len(public["candidates"]), 15)

    def test_base_schema_restricts_references_to_displayed_excerpt_ids(self) -> None:
        packet = {"packet_id": "PKT_INERT", "records": inert_records(7)[1:7]}
        excerpts = PILOT.packet_excerpts(packet)
        schema = PILOT.base_schema_for_excerpts(excerpts)
        expected = [row["excerpt_id"] for row in excerpts]
        self.assertEqual(
            schema["properties"]["support_excerpt_ids"]["items"]["enum"],
            expected,
        )
        self.assertEqual(
            schema["properties"]["counterevidence_excerpt_ids"]["items"]["enum"],
            expected,
        )
        invalid = {
            "theme_name": "INERT",
            "claim": "INERT",
            "explanation": "INERT",
            "support_excerpt_ids": [expected[0], "UNKNOWN"],
            "counterevidence_excerpt_ids": [expected[1]],
            "boundary_conditions": ["INERT"],
        }
        with self.assertRaises(PILOT.jsonschema.ValidationError):
            PILOT.jsonschema.Draft202012Validator(schema).validate(invalid)

    def test_split_index_uses_records_sha256_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row = {
                "record_id": "inert-record",
                "source_id": "inert-source",
                "split": "in_domain_audit",
                "text": "INERT_TEXT",
            }
            raw = PILOT.canonical_bytes(row) + b"\n"
            records_path = root / "records.jsonl"
            records_path.write_bytes(raw)
            records_path.chmod(0o600)
            records_sha256 = PILOT.sha256_file(records_path)
            index = {
                "records_sha256": records_sha256,
                "splits": {
                    "in_domain_audit": [
                        {
                            "line_number": 1,
                            "byte_offset": 0,
                            "byte_length": len(raw),
                            "line_sha256": PILOT.sha256_bytes(raw),
                        }
                    ]
                },
            }
            index_path = root / "records.split_index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            index_path.chmod(0o600)
            observed = PILOT.load_test_records(
                {
                    "dataset": {
                        "local_split": "in_domain_audit",
                        "records_file_sha256": records_sha256,
                    }
                },
                {"records_path": records_path, "split_index_path": index_path},
            )
            self.assertEqual(observed, [row])

    def test_review_gate_requires_five_items_and_all_families(self) -> None:
        all_families = [
            {"target_flaw": family, "item_id": f"item-{index}"}
            for index, family in enumerate(PILOT.FAMILY_ORDER)
        ]
        self.assertTrue(PILOT.review_gate_passes(all_families))
        self.assertFalse(PILOT.review_gate_passes(all_families[:-1]))
        repeated = [{"target_flaw": PILOT.FAMILY_ORDER[0]} for _ in range(8)]
        self.assertFalse(PILOT.review_gate_passes(repeated))

    def test_exact_frozen_flag_is_a_hit(self) -> None:
        observation = {
            "status": "valid",
            "rating": valid_rating(["unsupported_inference", "other"]),
        }
        self.assertTrue(
            PILOT.valid_exact_flag_hit(observation, "unsupported_inference")
        )
        self.assertFalse(
            PILOT.valid_exact_flag_hit(observation, "contextual_flattening")
        )

    def test_every_failure_and_cannot_judge_is_a_miss(self) -> None:
        self.assertFalse(PILOT.valid_exact_flag_hit(None, "unsupported_inference"))
        self.assertFalse(
            PILOT.valid_exact_flag_hit(
                {"status": "terminal_failure", "rating": None},
                "unsupported_inference",
            )
        )
        self.assertFalse(
            PILOT.valid_exact_flag_hit(
                {
                    "status": "valid",
                    "rating": valid_rating(
                        ["unsupported_inference"],
                        ["evidential_credibility"],
                    ),
                },
                "unsupported_inference",
            )
        )

    def test_component_bootstrap_is_deterministic(self) -> None:
        rows = [
            {"component_id": f"component-{index}", "hit": index < 3}
            for index in range(5)
        ]
        first = PILOT.component_bootstrap_interval(rows, resamples=10000, seed=20270826)
        second = PILOT.component_bootstrap_interval(rows, resamples=10000, seed=20270826)
        self.assertEqual(first, second)
        self.assertTrue(0.0 <= first[0] <= 0.6 <= first[1] <= 1.0)

    def test_bootstrap_rejects_reused_component(self) -> None:
        with self.assertRaisesRegex(PILOT.PilotError, "bootstrap_components_not_unique"):
            PILOT.component_bootstrap_interval(
                [
                    {"component_id": "same", "hit": True},
                    {"component_id": "same", "hit": False},
                ]
            )

    def test_qwen_requests_are_stateless_hardened_and_use_exact_seeds(self) -> None:
        config = {
            "models": {"generalist_reviewer": {"model_id": "qwen3:8b"}},
            "decoding": {
                "generalist_reviewer": {
                    "temperature": 0.2,
                    "top_p": 1,
                    "num_ctx": 16384,
                    "max_output_tokens": 512,
                    "repetition_seeds": [2027082601, 2027082602, 2027082603],
                }
            },
        }
        for repetition, seed in enumerate((2027082601, 2027082602, 2027082603), 1):
            request = PILOT.build_request(
                config,
                model_role="generalist_reviewer",
                system_prompt="INERT SYSTEM",
                user_prompt="INERT USER",
                output_schema={"type": "object"},
                repetition=repetition,
            )
            self.assertEqual(request["options"]["seed"], seed)
            self.assertFalse(request["truncate"])
            self.assertFalse(request["shift"])
            self.assertFalse(request["stream"])
            self.assertFalse(request["think"])
            self.assertNotIn("tools", request)
            self.assertEqual(len(request["messages"]), 2)

    def test_private_writer_enforces_modes_and_root(self) -> None:
        original_root = PILOT.EXPECTED_OUTPUT_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "private-root"
            PILOT.EXPECTED_OUTPUT_ROOT = root
            try:
                target = root / "run" / "artifact.json"
                PILOT.write_private_json_once(target, {"inert": True})
                self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
                self.assertEqual(json.loads(target.read_text()), {"inert": True})
                with self.assertRaisesRegex(PILOT.PilotError, "outside_private_root"):
                    PILOT.write_private_json_once(Path(temporary) / "escape.json", {})
            finally:
                PILOT.EXPECTED_OUTPUT_ROOT = original_root

    def test_source_free_plan_contains_no_record_or_text_fields(self) -> None:
        public = PILOT.source_free_plan(PILOT.build_candidate_plan(inert_records(), minimal_plan_config()))
        serialized = json.dumps(public, sort_keys=True)
        self.assertNotIn("INERT_", serialized)
        self.assertNotIn('"records"', serialized)
        self.assertFalse(public["contains_source_text"])

    def test_all_five_controlled_families_pass_structural_and_exact_verifier_rule(self) -> None:
        packet = {
            "packet_id": "PKT_INERT",
            "records": inert_records(7)[1:7],
        }
        excerpts = PILOT.packet_excerpts(packet)
        base = {
            "theme_name": "Inert theme",
            "claim": "The displayed inert packet contains a bounded pattern.",
            "explanation": "Two inert positions support the bounded pattern.",
            "support_excerpt_ids": [excerpts[0]["excerpt_id"], excerpts[1]["excerpt_id"]],
            "counterevidence_excerpt_ids": [excerpts[2]["excerpt_id"]],
            "boundary_conditions": ["One inert position is a boundary case."],
        }
        roles = PILOT.base_roles(base, excerpts)
        base_item = PILOT.build_item(packet, base, roles, excerpts, "base")
        for family in PILOT.FAMILY_ORDER:
            with self.subTest(family=family):
                planned = PILOT.controlled_roles(family, excerpts, roles)
                variant = {
                    "theme_name": base["theme_name"],
                    "claim": base["claim"] + f" Changed for {family}.",
                    "explanation": base["explanation"],
                    "boundary_conditions": base["boundary_conditions"],
                    "construction_note": "INERT",
                }
                variant_item = PILOT.build_item(
                    packet, variant, planned, excerpts, f"variant-{family}"
                )
                structural = PILOT.construction_invariants(
                    family, base_item, variant_item, planned
                )
                self.assertTrue(structural["passed"], structural)
                verifier = {
                    "verification_schema_version": "rq2-construction-verification-v1",
                    "base_status": "warranted",
                    "comparison_clarity": "clear",
                    "present_flaws": [family],
                    "other_material_flaw": False,
                    "single_material_difference": True,
                    "anchors": [
                        {
                            "flaw_family": family,
                            "excerpt_ids": [excerpts[0]["excerpt_id"]],
                            "interpretation_fields": ["claim"],
                            "reason_code": PILOT.REASON_BY_FAMILY[family],
                        }
                    ],
                }
                accepted, reasons = PILOT.verifier_acceptance(
                    family, variant_item, structural, verifier
                )
                self.assertTrue(accepted, reasons)

    def test_completed_call_checkpoint_is_reused_without_transport(self) -> None:
        original_root = PILOT.EXPECTED_OUTPUT_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "private-root"
            PILOT.EXPECTED_OUTPUT_ROOT = root
            try:
                run_dir = root / "rq2qgpl_20260828T000000Z_00000000"
                call_dir = run_dir / "raw" / "calls" / "review_inert_r1"
                PILOT.ensure_private_directory(call_dir)
                config = {
                    "models": {"generalist_reviewer": {"model_id": "qwen3:8b"}},
                    "decoding": {
                        "generalist_reviewer": {
                            "temperature": 0.2,
                            "top_p": 1,
                            "num_ctx": 16384,
                            "max_output_tokens": 512,
                            "repetition_seeds": [2027082601, 2027082602, 2027082603],
                        },
                        "safety_margin_tokens": 512,
                    },
                }
                schema = {
                    "type": "object",
                    "required": ["value"],
                    "properties": {"value": {"const": "INERT"}},
                    "additionalProperties": False,
                }
                request = PILOT.build_request(
                    config,
                    model_role="generalist_reviewer",
                    system_prompt="INERT SYSTEM",
                    user_prompt="INERT USER",
                    output_schema=schema,
                    repetition=1,
                )
                response = {
                    "model": "qwen3:8b",
                    "done": True,
                    "done_reason": "stop",
                    "message": {"content": '{"value":"INERT"}'},
                    "prompt_eval_count": 10,
                    "eval_count": 2,
                    "created_at": "INERT",
                    "total_duration": 1,
                }
                request_path = call_dir / "request.private.json"
                response_path = call_dir / "response.private.json"
                PILOT.write_private_json_once(request_path, request)
                PILOT.write_private_json_once(response_path, response)
                output, execution = PILOT.parse_response(
                    response,
                    expected_model="qwen3:8b",
                    validation_schema=schema,
                    profile=config["decoding"]["generalist_reviewer"],
                    safety_margin=512,
                )
                final = {
                    "status": "valid",
                    "call_id": "review_inert_r1",
                    "model_role": "generalist_reviewer",
                    "model_id": "qwen3:8b",
                    "repetition": 1,
                    "request_sha256": PILOT.sha256_file(request_path),
                    "response_sha256": PILOT.sha256_file(response_path),
                    "transport_error_sha256": None,
                    "output": output,
                    "execution": {"elapsed_seconds": 0.1, **execution},
                    "error_code": None,
                    "retry_count": 0,
                }
                PILOT.write_private_json_once(call_dir / "final.private.json", final)
                observed = PILOT.invoke_once(
                    config,
                    run_dir,
                    call_id="review_inert_r1",
                    model_role="generalist_reviewer",
                    system_prompt="INERT SYSTEM",
                    user_prompt="INERT USER",
                    output_schema=schema,
                    repetition=1,
                )
                self.assertEqual(observed, final)
            finally:
                PILOT.EXPECTED_OUTPUT_ROOT = original_root

    def test_interrupted_request_is_closed_without_reissue(self) -> None:
        original_root = PILOT.EXPECTED_OUTPUT_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "private-root"
            PILOT.EXPECTED_OUTPUT_ROOT = root
            try:
                run_dir = root / "rq2qgpl_20260828T000000Z_00000000"
                call_dir = run_dir / "raw" / "calls" / "review_inert_r1"
                PILOT.ensure_private_directory(call_dir)
                config = {
                    "models": {"generalist_reviewer": {"model_id": "qwen3:8b"}},
                    "decoding": {
                        "generalist_reviewer": {
                            "temperature": 0.2,
                            "top_p": 1,
                            "num_ctx": 16384,
                            "max_output_tokens": 512,
                            "repetition_seeds": [2027082601, 2027082602, 2027082603],
                        },
                        "safety_margin_tokens": 512,
                    },
                }
                schema = {"type": "object"}
                request = PILOT.build_request(
                    config,
                    model_role="generalist_reviewer",
                    system_prompt="INERT SYSTEM",
                    user_prompt="INERT USER",
                    output_schema=schema,
                    repetition=1,
                )
                PILOT.write_private_json_once(call_dir / "request.private.json", request)
                observed = PILOT.invoke_once(
                    config,
                    run_dir,
                    call_id="review_inert_r1",
                    model_role="generalist_reviewer",
                    system_prompt="INERT SYSTEM",
                    user_prompt="INERT USER",
                    output_schema=schema,
                    repetition=1,
                )
                self.assertEqual(observed["status"], "terminal_failure")
                self.assertEqual(
                    observed["error_code"], "interrupted_before_response_checkpoint"
                )
                self.assertEqual(observed["retry_count"], 0)
                self.assertFalse((call_dir / "response.private.json").exists())
            finally:
                PILOT.EXPECTED_OUTPUT_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
