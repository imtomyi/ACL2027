"""Contract tests for live execution, original-claim scoring and restart behavior."""

from __future__ import annotations

import copy
import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import warrantroute_loop_runtime as runtime
import run_warrantroute_loop_n100 as runner


def packet():
    return {
        "packet_id": "PKT_TEST", "corpus_id": "dreaddit", "research_question": "Contract test only",
        "known_intended_flaw_type": "SECRET_LABEL", "review_instruction": "SECRET_INSTRUCTION",
        "source_text_context": [
            {"excerpt_id": "E1", "source_id": "S1", "speaker_id": "SP1", "text": "Test fixture",
             "local_context": "", "metadata": {"answer_key": "SECRET_METADATA"}}
        ],
        "llm_generated_qualitative_claim": {
            "claim": "Contract fixture claim", "explanation": "Test only", "theme_name": "Test",
            "boundary_conditions": "Fixture", "cited_excerpt_ids": ["E1"], "model_id": "SECRET_MODEL",
        },
    }


def report(flag=None, resolved=(), requested="none"):
    return {
        "rating": {
            "rating_schema_version": "direction-j-shared-rating-v1",
            **{field: 3 if flag else 5 for field in runtime.QUALITY_FIELDS},
            "cannot_judge": [], "confidence": 4,
            "disposition": "escalate" if requested != "none" else "revise" if flag else "accept",
            "requested_expertise": requested, "serious_error_flags": [flag] if flag else [],
            "rationale": "Fixture audit",
        },
        "support_ids": ["E1"], "counterevidence_ids": [], "alternative_interpretation": "",
        "issues": [{"flag": flag, "evidence_ids": ["E1"], "diagnosis": "Fixture issue",
                    "requested_change": "Revise scope"}] if flag else [],
        "resolved_issue_ids": list(resolved),
    }


class FakeClient:
    def __init__(self, config, responder):
        self.config = config
        self.assignment = config["configurations"]["qwen_led"]
        self.prompt = "Test fixture prompt"
        self.records = []
        self.requests = []
        self.responder = responder

    def call(self, role, stage, payload, schema):
        self.requests.append((role, stage, copy.deepcopy(payload)))
        self.records.append({"role": role, "prompt_eval_count": 10, "eval_count": 10, "wall_seconds": 0.1})
        response = self.responder(role, stage, payload)
        if role != "reviser":
            response["rating"].pop("serious_error_flags", None)
        return response


class LiveLoopTests(unittest.TestCase):
    def setUp(self):
        self.config = runner.read_json(runner.ROOT / "config/warrantroute_loop_n100_v1.json")
        self.policy = runner.read_json(runtime.WORKSPACE / self.config["gate_policy"])

    def test_payload_excludes_labels_metadata_and_generator_identity(self):
        payload = runtime.packet_payload(packet())
        self.assertNotIn("SECRET", json.dumps(payload))
        self.assertEqual(payload["source_text_context"][0]["excerpt_id"], "E1")

    def test_initial_passes_are_independent_and_zero_revision_can_accept(self):
        client = FakeClient(self.config, lambda *args: report())
        result = runtime.run_packet(packet(), client, self.policy)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["revision_rounds"], 0)
        self.assertEqual(result["cost"]["agent_calls"], 2)
        for _role, _stage, payload in client.requests[:2]:
            self.assertNotIn("locked_initial_assessments", payload)
        self.assertIsNone(result["semantic_repair_quality"])

    def test_revision_keeps_original_detection_and_requires_owner_recheck(self):
        def respond(role, stage, payload):
            if stage == "initial":
                return report("unsupported_inference") if role == "evidence_scout" else report()
            if role == "reviser":
                return {"claim": "Narrower fixture claim", "central_concept": "Test", "scope": "One source",
                        "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Limited scope",
                        "issue_responses": {issue["issue_id"]: "Scope narrowed" for issue in payload["issues"]}}
            return report(resolved=[issue["issue_id"] for issue in payload["assigned_issues"]])
        client = FakeClient(self.config, respond)
        result = runtime.run_packet(packet(), client, self.policy)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["revision_rounds"], 1)
        self.assertEqual(result["original_detected_flags"], ["unsupported_inference"])
        self.assertEqual(result["final_candidate"]["claim"], "Narrower fixture claim")
        self.assertEqual(result["issues"][0]["status"], "resolved")

    def test_specialist_request_promotes_mode(self):
        client = FakeClient(self.config, lambda role, *_: report(requested="domain") if role == "evidence_scout" else report())
        result = runtime.run_packet(packet(), client, self.policy)
        self.assertEqual(result["route"], "domain")
        self.assertIn("domain_challenger", [row[0] for row in client.requests])

    def test_recheck_cannot_claim_another_agents_issue(self):
        with self.assertRaisesRegex(ValueError, "unowned_issue"):
            runtime.validate_audit(report(resolved=["someone-elses-issue"]), {"E1"}, set())

    def test_unsupported_evidence_id_quarantines(self):
        def respond(*_):
            value = report("unsupported_inference")
            value["issues"][0]["evidence_ids"] = ["MISSING"]
            return value
        result = runtime.run_packet(packet(), FakeClient(self.config, respond), self.policy)
        self.assertEqual(result["status"], "quarantined")
        self.assertEqual(result["original_detected_flags"], [])

    def test_no_revision_ablation_preserves_detections(self):
        client = FakeClient(self.config, lambda *_: report("unsupported_inference"))
        result = runtime.run_packet(packet(), client, self.policy, "no_revision")
        self.assertEqual(result["status"], "human_escalation")
        self.assertEqual(result["revision_rounds"], 0)
        self.assertNotIn("reviser", [row[0] for row in client.requests])
        self.assertIn("unsupported_inference", result["original_detected_flags"])

    def test_always_on_runs_all_initial_agents(self):
        client = FakeClient(self.config, lambda *_: report())
        result = runtime.run_packet(packet(), client, self.policy, "always_on")
        self.assertEqual(result["route"], "both")
        self.assertEqual(result["cost"]["agent_calls"], 4)

    def test_persistent_disagreement_stops_within_twelve_calls(self):
        def respond(role, stage, payload):
            if role == "reviser":
                return {"claim": "Narrower fixture claim", "central_concept": "Test", "scope": "One source",
                        "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Limited scope",
                        "issue_responses": {issue["issue_id"]: "Attempted repair" for issue in payload["issues"]}}
            return report("unsupported_inference")
        result = runtime.run_packet(packet(), FakeClient(self.config, respond), self.policy, "always_on")
        self.assertEqual(result["status"], "human_escalation")
        self.assertEqual(result["revision_rounds"], 2)
        self.assertEqual(result["cost"]["agent_calls"], 12)

    def test_new_revision_issue_is_not_original_detection_credit(self):
        def respond(role, stage, payload):
            if role == "reviser":
                return {"claim": "Revised fixture claim", "central_concept": "Test", "scope": "One source",
                        "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Limited scope",
                        "issue_responses": {issue["issue_id"]: "Attempted repair" for issue in payload["issues"]}}
            return report("unsupported_inference" if stage == "initial" else "lost_negative_case")
        result = runtime.run_packet(packet(), FakeClient(self.config, respond), self.policy)
        self.assertEqual(result["original_detected_flags"], ["unsupported_inference"])
        self.assertTrue(any(row["flag"] == "lost_negative_case" for row in result["issue_archive"]))

    def test_revision_must_address_every_issue(self):
        revision = {"claim": "Text", "central_concept": "Text", "scope": "Text", "evidence_ids": ["E1"],
                    "counterevidence_ids": [], "uncertainty": "Text", "issue_responses": {}}
        with self.assertRaisesRegex(ValueError, "inventory_mismatch"):
            runtime.validate_revision(revision, {"E1"}, {"ISSUE"})

    def test_repeat_call_uses_cache_without_contacting_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []
            def transport(request, timeout):
                calls.append(request)
                response = report()
                response["rating"].pop("serious_error_flags")
                return {"done": True, "done_reason": "stop", "response": json.dumps(response),
                        "prompt_eval_count": 10, "eval_count": 20}
            def client():
                return runtime.AgentClient(self.config, self.config["configurations"]["qwen_led"],
                                           1, "Prompt", "Guide", Path(temporary), runner.write_json, transport)
            for _ in range(2):
                client().call("proposer", "initial", {"text": "fixture"}, runtime.AUDIT_SCHEMA)
            self.assertEqual(len(calls), 1)
            self.assertIs(calls[0]["think"], False)
            with self.assertRaisesRegex(runtime.CallFailure, "identity_mismatch"):
                client().call("proposer", "initial", {"text": "changed"}, runtime.AUDIT_SCHEMA)

    def test_incomplete_call_never_silently_retries(self):
        with tempfile.TemporaryDirectory() as temporary:
            def broken(*_):
                raise TimeoutError("fixture timeout")
            client = runtime.AgentClient(self.config, self.config["configurations"]["qwen_led"],
                                         1, "Prompt", "Guide", Path(temporary), runner.write_json, broken)
            with self.assertRaises(runtime.CallFailure):
                client.call("proposer", "initial", {}, runtime.AUDIT_SCHEMA)
            self.assertFalse(runtime.summarize_cost(client.records)["usage_complete"])
            with self.assertRaisesRegex(runtime.CallFailure, "previous_call_error"):
                client.call("proposer", "initial", {}, runtime.AUDIT_SCHEMA)

    def test_shared_source_components_merge_transitively(self):
        rows = [packet() for _ in range(3)]
        for index, row in enumerate(rows):
            row["packet_id"] = f"P{index}"
        rows[1]["source_text_context"].append({"source_id": "S2"})
        rows[2]["source_text_context"] = [{"source_id": "S2"}]
        self.assertEqual(len(set(runner.cluster_components(rows).values())), 1)

    def test_dynamic_schema_binds_expertise_request_to_escalation(self):
        from jsonschema import Draft202012Validator, ValidationError

        validator = Draft202012Validator(runtime.audit_output_schema({"E1"}, set()))
        output = report("unsupported_inference", requested="domain")
        output["rating"].pop("serious_error_flags")
        validator.validate(output)
        output["rating"]["disposition"] = "revise"
        with self.assertRaises(ValidationError):
            validator.validate(output)
        output["rating"]["requested_expertise"] = "none"
        validator.validate(output)
        output["rating"]["disposition"] = "accept"
        with self.assertRaises(ValidationError):
            validator.validate(output)

    def test_dynamic_schema_disallows_initial_resolutions_and_unknown_ids(self):
        from jsonschema import Draft202012Validator, ValidationError
        value = report()
        value["rating"].pop("serious_error_flags")
        validator = Draft202012Validator(runtime.audit_output_schema({"E1"}, set()))
        validator.validate(value)
        value["resolved_issue_ids"] = ["E1"]
        with self.assertRaises(ValidationError):
            validator.validate(value)
        value["resolved_issue_ids"] = []
        value["support_ids"] = ["NEW"]
        with self.assertRaises(ValidationError):
            validator.validate(value)

    def test_action_request_without_issue_is_not_accepted(self):
        def respond(*_):
            value = report()
            value["rating"]["disposition"] = "revise"
            value["rating"]["evidential_credibility"] = 3
            return value
        result = runtime.run_packet(packet(), FakeClient(self.config, respond), self.policy)
        self.assertEqual(result["status"], "human_escalation")
        self.assertEqual(result["error"], "auditor_requested_action_without_located_issue")

    def test_prepare_run_resume_score_and_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config = copy.deepcopy(self.config)
            config["output_root"] = str(base)
            config_path = base / "config-source.json"
            runner.write_json(config_path, config)
            truth = base / "truth.jsonl"
            runner.atomic_text(truth, json.dumps({"packet_id": "PKT_TEST", "known_intended_flaw_type": "unsupported_evidence"}) + "\n")
            rows = {"dreaddit": [{"packet_id": "PKT_TEST", "corpus_id": "dreaddit", **runtime.packet_payload(packet())}]}
            bindings = {"dreaddit": {"source_file": str(truth), "source_sha256": runner.sha_file(truth),
                                     "truth_file": str(truth), "truth_sha256": runner.sha_file(truth),
                                     "packet_count": 1, "available_packet_count": 100}}
            args = argparse.Namespace(command="prepare", config=config_path, datasets=["dreaddit"],
                                      configurations=["qwen_led"], sample_n=1, methods=["warrantroute"],
                                      repetitions=1, run_dir=base / "prepared", max_packets=None)
            clients = []
            def fake_client(*arguments):
                client = FakeClient(config, lambda *_: report())
                clients.append(client)
                return client
            with patch.object(runner, "OUTPUT_ROOT", base), \
                 patch.object(runner, "verify_models", return_value={}), \
                 patch.object(runner, "inputs_for", return_value=(rows, bindings)), \
                 patch.object(runtime, "AgentClient", side_effect=fake_client), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.prepare(args)["status"], "prepared")
                self.assertEqual(runner.execute(args)["status"], "complete")
                self.assertEqual(runner.execute(args)["status"], "complete")
                self.assertEqual(len(clients), 1)
                self.assertEqual(runner.score(args)["status"], "scored_working_results")
                row = runner.read_json(args.run_dir / "comparison.json")["metrics"][0]
                self.assertEqual(row["n"], 1)
                self.assertEqual(row["tp"], 0)
                self.assertIsNone(row["repair_quality"])
                path = next(args.run_dir.glob("results/**/result.json"))
                result = runner.read_json(path)
                result["original_detected_flags"] = ["unsupported_inference"]
                runner.write_json(path, result)
                with self.assertRaisesRegex(ValueError, "integrity_mismatch"):
                    runner.score(args)


class SameModelComparisonTests(unittest.TestCase):
    def setUp(self):
        self.config = runner.read_json(runner.DEFAULT_CONFIG)
        self.policy = runner.read_json(runtime.WORKSPACE / self.config["gate_policy"])

    def test_default_launch_selects_three_single_model_conditions(self):
        args = runner.parser().parse_args(["prepare"])
        self.assertEqual(args.config, runner.DEFAULT_CONFIG)
        self.assertEqual(self.config["model_assignment_policy"], "same_model_ablation")
        expected = {"qwen_only": "qwen3:8b", "llama_only": "llama3.1:8b", "gemma_only": "gemma3:4b"}
        self.assertEqual(set(self.config["default_configurations"]), set(expected))
        for name, model in expected.items():
            self.assertEqual(set(self.config["configurations"][name]), set(runtime.ROLES))
            self.assertEqual(set(self.config["configurations"][name].values()), {model})

    def test_every_role_revision_and_recheck_uses_the_condition_model(self):
        for name in self.config["default_configurations"]:
            with self.subTest(configuration=name), tempfile.TemporaryDirectory() as temporary:
                requests = []

                def transport(request, timeout):
                    requests.append(request)
                    payload = json.loads(request["prompt"].rsplit("\n\n", 1)[1])
                    if "Assigned role: reviser." in request["prompt"]:
                        value = {"claim": "Revised fixture", "central_concept": "Test", "scope": "Fixture",
                                 "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Limited",
                                 "issue_responses": {issue["issue_id"]: "Attempted repair" for issue in payload["issues"]}}
                    else:
                        value = report("unsupported_inference")
                        value["rating"].pop("serious_error_flags")
                    return {"done": True, "done_reason": "stop", "response": json.dumps(value),
                            "prompt_eval_count": 10, "eval_count": 20}

                assignment = self.config["configurations"][name]
                client = runtime.AgentClient(self.config, assignment, 20260905, "Prompt", "Guide",
                                             Path(temporary), runner.write_json, transport)
                result = runtime.run_packet(packet(), client, self.policy, "always_on")
                self.assertIsNone(result["error"])
                self.assertEqual(result["revision_rounds"], 2)
                self.assertEqual(result["cost"]["agent_calls"], 12)
                self.assertEqual({request["model"] for request in requests}, {assignment["proposer"]})
                self.assertEqual({row["role"] for row in client.records}, set(runtime.ROLES))
                self.assertTrue(any(row["stage"] == "recheck-2" for row in client.records))

    def test_mixed_assignment_is_rejected_before_any_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            assignment = dict(self.config["configurations"]["qwen_only"])
            assignment["reviser"] = "llama3.1:8b"
            with patch.object(runtime, "ollama_transport") as transport:
                client = runtime.AgentClient(self.config, assignment, 1, "Prompt", "Guide",
                                             Path(temporary), runner.write_json, transport)
                result = runtime.run_packet(packet(), client, self.policy)
                transport.assert_not_called()
            self.assertEqual(result["status"], "quarantined")
            self.assertIn("same_model_ablation_requires_one_model_in_every_role", result["error"])
            self.assertEqual(result["cost"]["agent_calls"], 0)


if __name__ == "__main__":
    unittest.main()
