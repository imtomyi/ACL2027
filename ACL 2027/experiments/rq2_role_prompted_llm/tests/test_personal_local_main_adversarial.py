from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py"
SPEC = importlib.util.spec_from_file_location("rq2_personal_local_main_adversarial", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def synthetic_config() -> dict[str, object]:
    return {
        "service_url": "http://127.0.0.1:11434",
        "models": {
            "generator": {"model_id": "qwen-synthetic"},
            "verifier": {"model_id": "gemma-synthetic"},
            "reviewer": {"model_id": "llama-synthetic"},
        },
        "decoding": {
            "generator": {
                "temperature": 0,
                "top_p": 1,
                "num_ctx": 2048,
                "max_output_tokens": 128,
                "seed": 101,
            },
            "verifier": {
                "temperature": 0,
                "top_p": 1,
                "num_ctx": 2048,
                "max_output_tokens": 128,
                "seed": 202,
            },
            "reviewer": {
                "temperature": 0,
                "top_p": 1,
                "num_ctx": 2048,
                "max_output_tokens": 128,
                "repetition_seeds": [301],
            },
        },
        "rating_repetitions": 1,
    }


def valid_response(model_id: str, output: dict[str, object], *, prompt_tokens: int = 11,
                   output_tokens: int = 5) -> dict[str, object]:
    return {
        "model": model_id,
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps(output, sort_keys=True)},
        "created_at": "synthetic",
        "total_duration": 10,
        "load_duration": 1,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": 2,
        "eval_count": output_tokens,
        "eval_duration": 3,
    }


@contextlib.contextmanager
def isolated_output_root():
    storage = ROOT / "Storage"
    storage.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rq2-adversarial-", dir=storage) as temporary:
        private_root = Path(temporary)
        private_root.chmod(0o700)
        with mock.patch.object(MODULE, "PERSONAL_OUTPUT_ROOT", private_root):
            yield private_root


def dump_direct(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


class CheckpointIntegrityTests(unittest.TestCase):
    def test_tampered_call_request_checkpoint_fails_before_another_call(self):
        config = synthetic_config()
        schema = {
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
            "additionalProperties": False,
        }
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            with mock.patch.object(
                MODULE,
                "api_json",
                return_value=valid_response("qwen-synthetic", {"answer": "ok"}),
            ):
                result = MODULE.invoke_checkpointed_call(
                    config,
                    run_dir,
                    call_id="generate_dreaddit_development_packet_01_base",
                    model_role="generator",
                    system_prompt="synthetic system",
                    user_prompt="synthetic input",
                    output_schema=schema,
                    rating_call=False,
                    rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
            self.assertEqual(result["status"], "valid")

            request_path = (
                run_dir
                / "raw/calls/generate_dreaddit_development_packet_01_base"
                / "attempt_01_request.json"
            )
            tampered = MODULE.load_json(request_path)
            tampered["messages"][1]["content"] = "tampered synthetic input"
            dump_direct(request_path, tampered)

            with mock.patch.object(MODULE, "api_json") as network_call:
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError, "checkpoint_request_semantic_drift"
                ):
                    MODULE.invoke_checkpointed_call(
                        config,
                        run_dir,
                        call_id="generate_dreaddit_development_packet_01_base",
                        model_role="generator",
                        system_prompt="synthetic system",
                        user_prompt="synthetic input",
                        output_schema=schema,
                        rating_call=False,
                        rating_repetition=None,
                        retry_transport_on_explicit_resume=True,
                    )
            network_call.assert_not_called()

    def test_forged_second_attempt_on_nonretryable_verifier_is_rejected(self):
        config = synthetic_config()
        schema = {
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
            "additionalProperties": False,
        }
        call_id = "verify_dreaddit_development_ITEM_SYNTHETIC"
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            with mock.patch.object(
                MODULE,
                "api_json",
                side_effect=MODULE.TransportError(
                    error_type="SyntheticTransport",
                    raw={"synthetic_transport_failure": True},
                ),
            ):
                first = MODULE.invoke_checkpointed_call(
                    config,
                    run_dir,
                    call_id=call_id,
                    model_role="verifier",
                    system_prompt="synthetic system",
                    user_prompt="synthetic input",
                    output_schema=schema,
                    rating_call=False,
                    rating_repetition=None,
                    retry_transport_on_explicit_resume=False,
                )
            self.assertEqual(first["status"], "terminal_error")

            call_dir = run_dir / "raw" / "calls" / call_id
            request = MODULE.load_json(call_dir / "attempt_01_request.json")
            response = valid_response("gemma-synthetic", {"answer": "forged"})
            request_path = call_dir / "attempt_02_request.json"
            response_path = call_dir / "attempt_02_response.json"
            MODULE.write_json_once(request_path, request)
            MODULE.write_json_once(response_path, response)
            output, execution = MODULE.parse_model_response(
                response,
                expected_model="gemma-synthetic",
                output_schema=schema,
            )
            execution["elapsed_seconds"] = 0.01
            MODULE.write_json_once(
                call_dir / "success.json",
                {
                    "status": "valid",
                    "call_id": call_id,
                    "attempt": 2,
                    "model_role": "verifier",
                    "model_id": "gemma-synthetic",
                    "request_artifact_sha256": MODULE.sha256_file(request_path),
                    "response_artifact_sha256": MODULE.sha256_file(response_path),
                    "execution": execution,
                    "output": output,
                },
            )

            with mock.patch.object(MODULE, "api_json") as network_call:
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError,
                    "multiple_attempts_for_nonretryable_call",
                ):
                    MODULE.invoke_checkpointed_call(
                        config,
                        run_dir,
                        call_id=call_id,
                        model_role="verifier",
                        system_prompt="synthetic system",
                        user_prompt="synthetic input",
                        output_schema=schema,
                        rating_call=False,
                        rating_repetition=None,
                        retry_transport_on_explicit_resume=False,
                    )
            network_call.assert_not_called()

    def test_tampered_item_checkpoint_is_rejected_on_reconstruction(self):
        config = {
            **synthetic_config(),
            "sampling_seed": 7,
            "base_packets_per_lane": 1,
            "excerpts_per_packet": 1,
            "flaw_families": ["unsupported_evidence"],
            "target_to_flag_mapping": {"unsupported_evidence": "unsupported_inference"},
            "lanes": {
                "dreaddit_development": {
                    "corpus": "dreaddit",
                    "split": "development_train",
                }
            },
        }
        plan = [{
            "packet_index": 1,
            "packet_id": "PACKET_SYNTHETIC",
            "bootstrap_cluster_id": "CLUSTER_SYNTHETIC",
            "record_ids": ["RECORD_SYNTHETIC"],
            "selection_cluster_commitments": ["COMMITMENT_SYNTHETIC"],
        }]

        def invoke_stub(*args, **kwargs):
            if kwargs["call_id"].endswith("_base"):
                return {"status": "valid", "output": {"kind": "base"}}
            return {
                "status": "valid",
                "output": {"kind": "variant", "construction_note": "synthetic note"},
            }

        def build_item_stub(*, output_key, **kwargs):
            return {
                "item_id": "ITEM_BASE" if output_key.endswith(":base") else "ITEM_VARIANT",
                "output_key": output_key,
            }

        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            item_schema = private_root / "synthetic_item_schema.json"
            MODULE.write_json_once(item_schema, {})
            paths = {"item_schema": item_schema}
            patches = (
                mock.patch.object(MODULE, "deterministic_packet_plan", return_value=plan),
                mock.patch.object(MODULE, "excerpt_payload", return_value=[]),
                mock.patch.object(MODULE, "invoke_checkpointed_call", side_effect=invoke_stub),
                mock.patch.object(MODULE, "roles_from_base", return_value={}),
                mock.patch.object(MODULE, "deterministic_variant_roles", return_value={}),
                mock.patch.object(MODULE, "build_item", side_effect=build_item_stub),
                mock.patch.object(
                    MODULE,
                    "construction_invariants",
                    return_value={"passed": True, "failed_check_codes": [], "checks": {}},
                ),
            )
            with contextlib.ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                MODULE.prepare_lane_items(
                    config, paths, run_dir, "dreaddit_development", records=[]
                )
                variant_path = (
                    run_dir
                    / "items/dreaddit_development/packet_01/variant_01.json"
                )
                dump_direct(variant_path, {"item_id": "ITEM_TAMPERED"})
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError, "checkpoint_content_drift"
                ):
                    MODULE.prepare_lane_items(
                        config, paths, run_dir, "dreaddit_development", records=[]
                    )

    def test_tampered_observation_checkpoint_is_rejected_on_reconstruction(self):
        config = {
            **synthetic_config(),
            "prompt_sha256": {"generalist": "a" * 64},
            "shared_rater_guide_sha256": "b" * 64,
        }
        result = {
            "status": "valid",
            "output": {
                "cannot_judge": [],
                "serious_error_flags": [],
                "requested_expertise": "none",
            },
            "execution": {"elapsed_seconds": 0.25},
        }
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            guide = private_root / "guide.txt"
            prompt = private_root / "prompt.txt"
            rating_schema = private_root / "rating.schema.json"
            guide.write_text("synthetic guide", encoding="utf-8")
            prompt.write_text("synthetic prompt", encoding="utf-8")
            MODULE.write_json_once(rating_schema, {})
            paths = {
                "guide": guide,
                "prompt_generalist": prompt,
                "rating_schema": rating_schema,
            }
            item = {"item_id": "ITEM_SYNTHETIC", "payload": "synthetic"}
            with mock.patch.object(
                MODULE, "invoke_checkpointed_call", return_value=result
            ):
                MODULE.collect_role_lane_reviews(
                    config,
                    paths,
                    run_dir,
                    "dreaddit_development",
                    [item],
                    "generalist",
                )
                observation_path = next(
                    (run_dir / "observations/dreaddit_development").glob("*.json")
                )
                tampered = MODULE.load_json(observation_path)
                tampered["item_id"] = "ITEM_TAMPERED"
                dump_direct(observation_path, tampered)
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError, "checkpoint_content_drift"
                ):
                    MODULE.collect_role_lane_reviews(
                        config,
                        paths,
                        run_dir,
                        "dreaddit_development",
                        [item],
                        "generalist",
                    )


class OutputBoundaryTests(unittest.TestCase):
    @staticmethod
    def _seal_payload(run_dir: Path, entries: list[dict[str, object]]) -> dict[str, object]:
        return {
            "document_type": "rq2_personal_local_diagnostic_output_seal",
            "run_id": run_dir.name,
            "result_label": MODULE.STATUS,
            "evidence_status": MODULE.EVIDENCE_STATUS,
            "sealed_at_utc": "synthetic",
            "files": entries,
            "seal_payload_sha256": MODULE.sha256_bytes(MODULE.canonical_bytes(entries)),
            "aggregate_results_sha256": MODULE.sha256_file(
                run_dir / "analysis/aggregate_results.json"
            ),
            "this_manifest_contains_source_text": False,
            "sealed_run_contains_restricted_source_text": True,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
            "confirmatory_claims_allowed": False,
        }

    def test_self_consistent_fake_seal_cannot_bypass_completeness(self):
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            MODULE.write_json_once(
                run_dir / "analysis/aggregate_results.json", {"synthetic": True}
            )
            entries = MODULE.safe_run_inventory(run_dir)
            MODULE.write_json_once(
                run_dir / "output_seal.json", self._seal_payload(run_dir, entries)
            )
            with self.assertRaisesRegex(
                MODULE.PersonalLocalError,
                "sealed_run_(?:expected|required)_file_missing",
            ):
                MODULE.validate_output_seal(
                    run_dir,
                    {
                        **synthetic_config(),
                        "base_packets_per_lane": 0,
                        "flaw_families": [],
                    },
                )

    def test_seal_cannot_claim_manuscript_publication_or_confirmatory_eligibility(self):
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            MODULE.write_json_once(
                run_dir / "analysis/aggregate_results.json", {"synthetic": True}
            )
            entries = MODULE.safe_run_inventory(run_dir)
            for field in (
                "manuscript_eligible",
                "publication_or_release_eligible",
                "confirmatory_claims_allowed",
            ):
                seal = self._seal_payload(run_dir, entries)
                seal[field] = True
                seal_path = run_dir / "output_seal.json"
                if seal_path.exists():
                    seal_path.unlink()
                MODULE.write_json_once(seal_path, seal)
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError, "seal_eligibility_flags_mismatch"
                ):
                    MODULE.validate_output_seal(run_dir, synthetic_config())

    def test_mutated_artifact_invalidates_existing_seal(self):
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            MODULE.write_json_once(
                run_dir / "analysis/aggregate_results.json", {"synthetic": True}
            )
            filler = run_dir / "synthetic_artifact.json"
            MODULE.write_json_once(filler, {"state": "original"})
            entries = MODULE.safe_run_inventory(run_dir)
            MODULE.write_json_once(
                run_dir / "output_seal.json", self._seal_payload(run_dir, entries)
            )
            dump_direct(filler, {"state": "mutated"})
            with self.assertRaisesRegex(
                MODULE.PersonalLocalError, "seal_inventory_or_hash_mismatch"
            ):
                MODULE.validate_output_seal(run_dir, synthetic_config())

    def test_incomplete_seal_inventory_is_rejected(self):
        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            MODULE.write_json_once(
                run_dir / "analysis/aggregate_results.json", {"synthetic": True}
            )
            MODULE.write_json_once(run_dir / "omitted.json", {"synthetic": True})
            entries = [
                row
                for row in MODULE.safe_run_inventory(run_dir)
                if row["path"] != "omitted.json"
            ]
            MODULE.write_json_once(
                run_dir / "output_seal.json", self._seal_payload(run_dir, entries)
            )
            with self.assertRaisesRegex(
                MODULE.PersonalLocalError, "seal_inventory_or_hash_mismatch"
            ):
                MODULE.validate_output_seal(run_dir, synthetic_config())

    def test_ancestor_final_and_broken_symlinks_are_rejected(self):
        with isolated_output_root() as private_root:
            real_directory = private_root / "real"
            MODULE.ensure_private_directory(real_directory)
            target = real_directory / "target.json"
            MODULE.write_json_once(target, {"synthetic": True})

            ancestor = private_root / "ancestor"
            ancestor.symlink_to(real_directory, target_is_directory=True)
            final = private_root / "final.json"
            final.symlink_to(target)
            broken = private_root / "broken.json"
            broken.symlink_to(private_root / "does-not-exist.json")

            for candidate in (ancestor / "target.json", final, broken):
                with self.subTest(candidate=candidate.name):
                    with self.assertRaisesRegex(
                        MODULE.PersonalLocalError, "workspace_path_symlink_rejected"
                    ):
                        MODULE.safe_exists(candidate)


class SplitIsolationAndAccountingTests(unittest.TestCase):
    def test_indexed_loader_never_decodes_nonrequested_json_lines(self):
        requested = {
            "record_id": "RECORD_SYNTHETIC",
            "corpus": "dreaddit",
            "split": "development_train",
            "source_id": "SOURCE_SYNTHETIC",
            "speaker_id": None,
            "text": "synthetic requested record",
            "context": {},
            "quality": {},
        }
        requested_line = (json.dumps(requested, sort_keys=True) + "\n").encode("utf-8")
        nonrequested_invalid_line = b"{synthetic-nonrequested-invalid-json}\n"
        payload = requested_line + nonrequested_invalid_line
        with isolated_output_root() as private_root:
            records_path = private_root / "synthetic_records.jsonl"
            records_path.write_bytes(payload)
            records_path.chmod(0o600)
            digest = hashlib.sha256(payload).hexdigest()
            index = {
                "document_type": "rq2_source_free_jsonl_split_index",
                "index_version": "rq2-source-free-split-index-v1",
                "records_path": "dataset/deidentified/dreaddit/records.jsonl",
                "records_sha256": digest,
                "contains_source_text": False,
                "stored_fields": [
                    "split",
                    "line_number",
                    "byte_offset",
                    "byte_length",
                    "line_sha256",
                ],
                "file_size_bytes": len(payload),
                "line_count": 2,
                "splits": {
                    "development_train": [{
                        "line_number": 1,
                        "byte_offset": 0,
                        "byte_length": len(requested_line),
                        "line_sha256": hashlib.sha256(requested_line).hexdigest(),
                    }],
                    "in_domain_audit": [{
                        "line_number": 2,
                        "byte_offset": len(requested_line),
                        "byte_length": len(nonrequested_invalid_line),
                        "line_sha256": hashlib.sha256(nonrequested_invalid_line).hexdigest(),
                    }],
                },
            }
            original_loads = json.loads
            with mock.patch.object(MODULE.json, "loads", wraps=original_loads) as decoder:
                records = MODULE.load_bound_records(
                    records_path,
                    "dreaddit",
                    digest,
                    "development_train",
                    split_index=index,
                )
            self.assertEqual(records, [requested])
            self.assertEqual(decoder.call_count, 1)
            self.assertEqual(decoder.call_args.args[0], requested_line)

    def test_all_attempt_accounting_includes_response_bearing_failure_and_retry(self):
        config = synthetic_config()
        schema = {
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
            "additionalProperties": False,
        }
        failed_response = {
            "synthetic_transport_failure": True,
            "prompt_eval_count": 7,
            "eval_count": 3,
        }
        successful_response = valid_response(
            "qwen-synthetic", {"answer": "ok"}, prompt_tokens=11, output_tokens=5
        )
        responses: list[object] = [
            MODULE.TransportError(error_type="SyntheticTransport", raw=failed_response),
            successful_response,
        ]

        def api_stub(*args, **kwargs):
            next_value = responses.pop(0)
            if isinstance(next_value, Exception):
                raise next_value
            return next_value

        with isolated_output_root() as private_root:
            run_dir = private_root / "synthetic_run"
            with mock.patch.object(MODULE, "api_json", side_effect=api_stub):
                first = MODULE.invoke_checkpointed_call(
                    config,
                    run_dir,
                    call_id="generate_dreaddit_development_packet_01_base",
                    model_role="generator",
                    system_prompt="synthetic system",
                    user_prompt="synthetic input",
                    output_schema=schema,
                    rating_call=False,
                    rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
                second = MODULE.invoke_checkpointed_call(
                    config,
                    run_dir,
                    call_id="generate_dreaddit_development_packet_01_base",
                    model_role="generator",
                    system_prompt="synthetic system",
                    user_prompt="synthetic input",
                    output_schema=schema,
                    rating_call=False,
                    rating_repetition=None,
                    retry_transport_on_explicit_resume=True,
                )
            self.assertEqual(first["status"], "terminal_error")
            self.assertEqual(second["status"], "valid")
            operations = MODULE.aggregate_call_attempt_operations(run_dir)
            self.assertEqual(operations["logical_calls_started"], 1)
            self.assertEqual(operations["logical_calls_final_valid"], 1)
            self.assertEqual(operations["physical_attempts"], 2)
            self.assertEqual(operations["retry_or_resume_attempts"], 1)
            self.assertEqual(operations["input_tokens_prompt_eval_count_all_attempts"], 18)
            self.assertEqual(operations["output_tokens_eval_count_all_attempts"], 8)
            self.assertEqual(
                operations["attempt_failures"],
                [{"stage": "transport", "type": "SyntheticTransport", "count": 1}],
            )


class PhaseAndDenominatorTests(unittest.TestCase):
    def test_execute_batches_model_phases_and_rechecks_identity_at_boundaries(self):
        config = {
            "readiness_report_file_sha256": "a" * 64,
            "policy_validator_file_sha256": "b" * 64,
            "policy_file_sha256": "c" * 64,
            "pre_run_boundary_incidents": {
                "status": "recorded",
                "incident_count": 2,
                "file_sha256": "d" * 64,
            },
            "lanes": {
                "dreaddit_development": {
                    "corpus": "dreaddit",
                    "split": "development_train",
                    "records_file_sha256": "e" * 64,
                },
                "dreaddit_audit": {
                    "corpus": "dreaddit",
                    "split": "in_domain_audit",
                    "records_file_sha256": "e" * 64,
                },
                "agyw_heldout": {
                    "corpus": "agyw_focus_groups",
                    "split": "heldout_cross_domain_evaluation",
                    "records_file_sha256": "f" * 64,
                },
            },
        }
        events: list[str] = []
        synthetic_paths = {
            "split_index": Path("/synthetic/split-index.json"),
            "records_dreaddit_development": Path("/synthetic/development.jsonl"),
            "records_dreaddit_audit": Path("/synthetic/audit.jsonl"),
            "records_agyw_heldout": Path("/synthetic/agyw.jsonl"),
        }
        run_dir = Path("/synthetic/rq2pl_20260826T000000Z_deadbeef")

        def prepare_stub(config, paths, observed_run_dir, lane_name, records, **kwargs):
            events.append(f"Q:{lane_name}")
            return (
                [{"item_id": f"constructed-{lane_name}"}],
                [{"item_id": f"truth-{lane_name}"}],
                [{"item_id": f"case-{lane_name}"}],
                {f"commitment-{lane_name}"},
            )

        def verify_stub(config, paths, observed_run_dir, lane_name, items, truths, cases):
            events.append(f"G:{lane_name}")
            return (
                [{"item_id": f"accepted-{lane_name}"}],
                [{"item_id": f"truth-{lane_name}"}],
                {"lane": lane_name},
            )

        def review_stub(config, paths, observed_run_dir, lane_name, items, role):
            events.append(f"L:{role}:{lane_name}")
            return [{"lane": lane_name, "prompted_role": role}]

        def load_json_stub(path):
            return config if path == Path("/synthetic/config.json") else {}

        patches = (
            mock.patch.object(MODULE.os, "umask"),
            mock.patch.object(MODULE, "load_json", side_effect=load_json_stub),
            mock.patch.object(MODULE, "validate_freeze", return_value=synthetic_paths),
            mock.patch.object(
                MODULE,
                "run_exact_policy_validator",
                return_value={
                    "policy_check_status": "passed",
                    "policy_sha256": "c" * 64,
                    "bound_input_hashes_verified": True,
                },
            ),
            mock.patch.object(MODULE, "preflight_service", return_value={"identity": "baseline"}),
            mock.patch.object(MODULE, "initialize_run", return_value=run_dir),
            mock.patch.object(MODULE, "safe_exists", return_value=False),
            mock.patch.object(
                MODULE,
                "recheck_service_identity",
                side_effect=lambda *args: events.append("I"),
            ),
            mock.patch.object(MODULE, "load_bound_records", return_value=[]),
            mock.patch.object(MODULE, "prepare_lane_items", side_effect=prepare_stub),
            mock.patch.object(MODULE, "verify_lane_items", side_effect=verify_stub),
            mock.patch.object(MODULE, "collect_role_lane_reviews", side_effect=review_stub),
            mock.patch.object(
                MODULE,
                "freeze_fixed_role_checkpoint",
                side_effect=lambda *args: events.append("F") or {"selected_role": "generalist"},
            ),
            mock.patch.object(
                MODULE,
                "analyze_run",
                side_effect=lambda *args: events.append("A") or {"synthetic": True},
            ),
            mock.patch.object(
                MODULE,
                "seal_run",
                side_effect=lambda *args: events.append("S") or {"sealed": True},
            ),
        )
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            returned = MODULE.execute(
                Path("/synthetic/config.json"), "rq2pl_20260826T000000Z_deadbeef"
            )
        self.assertEqual(returned, run_dir)
        self.assertEqual(
            events,
            [
                "I",
                "Q:dreaddit_development",
                "I",
                "G:dreaddit_development",
                "I",
                "L:generalist:dreaddit_development",
                "I",
                "L:methods:dreaddit_development",
                "I",
                "L:domain:dreaddit_development",
                "F",
                "I",
                "Q:dreaddit_audit",
                "I",
                "Q:agyw_heldout",
                "I",
                "G:dreaddit_audit",
                "I",
                "G:agyw_heldout",
                "I",
                "L:generalist:dreaddit_audit",
                "L:generalist:agyw_heldout",
                "I",
                "L:methods:dreaddit_audit",
                "L:methods:agyw_heldout",
                "I",
                "L:domain:dreaddit_audit",
                "L:domain:agyw_heldout",
                "A",
                "I",
                "S",
            ],
        )

    def test_model_identity_drift_is_rejected(self):
        baseline = {"identity": "baseline"}
        with mock.patch.object(
            MODULE, "preflight_service", return_value={"identity": "changed"}
        ):
            with self.assertRaisesRegex(
                MODULE.PersonalLocalError,
                "model_service_identity_changed_between_phases",
            ):
                MODULE.recheck_service_identity(synthetic_config(), baseline)

    def test_cross_lane_dreaddit_commitment_overlap_is_rejected(self):
        config = {
            **synthetic_config(),
            "sampling_seed": 7,
            "base_packets_per_lane": 1,
            "excerpts_per_packet": 1,
            "lanes": {
                "dreaddit_audit": {
                    "corpus": "dreaddit",
                    "split": "in_domain_audit",
                }
            },
        }
        plan = [{
            "packet_index": 1,
            "packet_id": "PACKET_SYNTHETIC",
            "bootstrap_cluster_id": "CLUSTER_SYNTHETIC",
            "record_ids": ["RECORD_SYNTHETIC"],
            "selection_cluster_commitments": ["COMMITMENT_OVERLAP"],
        }]
        with isolated_output_root() as private_root:
            with mock.patch.object(
                MODULE, "deterministic_packet_plan", return_value=plan
            ):
                with self.assertRaisesRegex(
                    MODULE.PersonalLocalError, "cross_lane_dreaddit_cluster_overlap"
                ):
                    MODULE.prepare_lane_items(
                        config,
                        {},
                        private_root / "synthetic_run",
                        "dreaddit_audit",
                        records=[],
                        forbidden_cluster_commitments={"COMMITMENT_OVERLAP"},
                    )

    @staticmethod
    def _build_complete_zero_construction_run(private_root: Path):
        run_dir = private_root / "synthetic_run"
        config = {
            "base_packets_per_lane": 0,
            "flaw_families": [],
            "rating_repetitions": 1,
        }
        for relative in (
            "raw/calls",
            "selection",
            "items",
            "truth",
            "construction",
            "verification",
            "quarantine",
            "observations",
            "analysis",
        ):
            MODULE.ensure_private_directory(run_dir / relative)
        for name in (
            "freeze_snapshot.json",
            "policy_snapshot.json",
            "run_contract.json",
            "analysis/aggregate_results.json",
            "analysis/fixed_role_selection.json",
            "analysis/fixed_role_selection.seal.json",
        ):
            MODULE.write_json_once(run_dir / name, {"synthetic": True})

        for lane_name in MODULE.LANE_ORDER:
            MODULE.ensure_private_directory(run_dir / "verification" / lane_name)
            MODULE.ensure_private_directory(run_dir / "quarantine" / lane_name)
            MODULE.ensure_private_directory(run_dir / "observations" / lane_name)
            truth_row = {
                "item_id": f"ITEM_{lane_name}",
                "verification_status": MODULE.VERIFICATION_LABEL,
            }
            MODULE.write_json_once(
                run_dir / "selection" / f"{lane_name}.json", {"synthetic": True}
            )
            MODULE.write_json_once(
                run_dir / "truth" / f"{lane_name}.private.json",
                {"records": [truth_row]},
            )
            MODULE.write_json_once(
                run_dir / "construction" / f"{lane_name}.private.json",
                {"records": []},
            )
            MODULE.write_json_once(
                run_dir / "verification" / f"{lane_name}_summary.json",
                {
                    "lane": lane_name,
                    "accepted_for_review_and_analysis": 1,
                    "gemma_screened": 1,
                    "excluded_before_review": 0,
                },
            )
            MODULE.write_json_once(
                run_dir / "analysis" / f"{lane_name}.json",
                {
                    "construction_verification": {
                        "accepted_for_review_and_analysis": 1
                    },
                    "primary_repetition_1": {"eligible_items": 1},
                    "sensitivity_two_of_three": {"eligible_items": 1},
                },
            )
            for role in MODULE.ROLE_ORDER:
                call_id = f"review_{lane_name}_ITEM_{lane_name}_{role}_r1"
                call_dir = run_dir / "raw/calls" / call_id
                MODULE.write_json_once(
                    call_dir / "call_contract.json",
                    {
                        "call_id": call_id,
                        "call_kind": "role_review",
                        "lane": lane_name,
                    },
                )
                MODULE.write_json_once(
                    call_dir / "attempt_01_error.json",
                    {"status": "terminal_error"},
                )
                MODULE.write_json_once(
                    run_dir
                    / "observations"
                    / lane_name
                    / (
                        "OBS_"
                        + hashlib.sha256(f"{lane_name}:{role}".encode("utf-8")).hexdigest()[:16]
                        + ".json"
                    ),
                    {"item_id": truth_row["item_id"], "prompted_role": role},
                )
        return run_dir, config

    def test_accepted_set_denominator_parity_is_enforced(self):
        with isolated_output_root() as private_root:
            run_dir, config = self._build_complete_zero_construction_run(private_root)
            MODULE.validate_run_completeness(run_dir, config)

            verification_path = (
                run_dir / "verification/dreaddit_development_summary.json"
            )
            verification = MODULE.load_json(verification_path)
            verification["accepted_for_review_and_analysis"] = 0
            dump_direct(verification_path, verification)
            with self.assertRaises(MODULE.PersonalLocalError):
                MODULE.validate_run_completeness(run_dir, config)

            verification["accepted_for_review_and_analysis"] = 1
            dump_direct(verification_path, verification)
            analysis_path = run_dir / "analysis/dreaddit_development.json"
            analysis = MODULE.load_json(analysis_path)
            analysis["primary_repetition_1"]["eligible_items"] = 0
            dump_direct(analysis_path, analysis)
            with self.assertRaises(MODULE.PersonalLocalError):
                MODULE.validate_run_completeness(run_dir, config)

    def test_sealed_nonretryable_call_rejects_forged_second_attempt(self):
        with isolated_output_root() as private_root:
            run_dir, config = self._build_complete_zero_construction_run(private_root)
            MODULE.validate_run_completeness(run_dir, config)

            call_id = (
                "review_dreaddit_development_ITEM_dreaddit_development_generalist_r1"
            )
            call_dir = run_dir / "raw" / "calls" / call_id
            contract_path = call_dir / "call_contract.json"
            contract = MODULE.load_json(contract_path)
            contract["retry_transport_on_explicit_resume"] = False
            dump_direct(contract_path, contract)
            MODULE.write_json_once(call_dir / "attempt_01_request.json", {})
            MODULE.write_json_once(call_dir / "attempt_02_request.json", {})

            with self.assertRaisesRegex(
                MODULE.PersonalLocalError,
                "sealed_nonretryable_call_has_multiple_attempts",
            ):
                MODULE.validate_run_completeness(run_dir, config)


if __name__ == "__main__":
    unittest.main()
