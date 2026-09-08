"""Offline implementation probes, not scientific results or model evaluations.

Uses existing synthetic test fixtures and temporary run directories. Never calls
an LLM, loads a corpus, changes experiment code, or updates an existing run.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, SchemaError

PROJECT = Path(__file__).resolve().parents[2]
EXPERIMENT = PROJECT / "experiments/rq2_role_prompted_llm"
sys.path.insert(0, str(EXPERIMENT / "scripts"))
sys.path.insert(0, str(EXPERIMENT / "tests"))
import run_warrantroute_loop_n100 as runner
import test_warrantroute_loop_n100 as fixture
import warrantroute_loop_runtime as runtime


def revision(payload, claim="Revised contract fixture"):
    return {
        "claim": claim, "central_concept": "Fixture", "scope": "Fixture",
        "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Fixture",
        "issue_responses": {row["issue_id"]: "Fixture response" for row in payload["issues"]},
    }


def main():
    config = runner.read_json(runner.DEFAULT_CONFIG)
    config["configurations"]["qwen_led"] = config["configurations"]["qwen_only"]
    policy = runner.read_json(PROJECT / config["gate_policy"])
    pb_config = runner.read_json(EXPERIMENT / "config/warrantroute_loop_n100_same_model_playbook_v1.json")
    bundle = runtime.load_playbook_bundle(pb_config)
    probes = {}

    retrieval = []
    for corpus in bundle["adapters"]:
        for role in runtime.ROLES:
            first = runtime.retrieve_playbook_bullets(bundle, role, corpus, {
                "stage": "initial", "candidate": {"claim": "Contract fixture A"}, "issues": [],
            })
            second = runtime.retrieve_playbook_bullets(bundle, role, corpus, {
                "stage": "recheck-2", "candidate": {"claim": "Contract fixture B"},
                "issues": [{"flag": "sensitive_or_diagnostic_inference"}],
            })
            retrieval.append({"corpus": corpus, "role": role, "same": first == second,
                              "supplied_ids": [row["bullet_id"] for row in first]})
    probes["retrieval_ignores_payload"] = retrieval

    def one_round(role, stage, payload):
        if role == "reviser":
            return revision(payload)
        if stage == "initial":
            return fixture.report("unsupported_inference" if role == "evidence_scout" else None)
        return fixture.report(resolved=[row["issue_id"] for row in payload["assigned_issues"]])

    client = fixture.FakeClient(config, one_round)
    result = runtime.run_packet(fixture.packet(), client, policy, "always_on")
    latest = {row["role"]: row["candidate_id"] for row in result["audit_history"] if row["role"] != "reviser"}
    probes["accepted_with_stale_audits"] = {
        "status": result["status"], "final_candidate_id": result["final_candidate"]["candidate_id"],
        "latest_reviewed_candidate_by_role": latest,
    }

    def two_rounds(role, stage, payload):
        if role == "reviser":
            claim = "First fixture revision" if stage == "revision-1" else fixture.packet()["llm_generated_qualitative_claim"]["claim"]
            return revision(payload, claim)
        if stage == "initial":
            flag = {"methods_challenger": "lost_negative_case", "domain_challenger": "unsupported_inference"}.get(role)
            return fixture.report(flag)
        resolved = [row["issue_id"] for row in payload["assigned_issues"]]
        if role == "methods_challenger" and stage == "recheck-1":
            resolved = []
        return fixture.report(resolved=resolved)

    result = runtime.run_packet(fixture.packet(), fixture.FakeClient(config, two_rounds), policy, "always_on")
    probes["resolved_issue_not_invalidated_after_later_edit"] = {
        "status": result["status"], "rounds": result["revision_rounds"],
        "final_equals_original_claim": result["final_candidate"]["claim"] == result["original_candidate"]["claim"],
        "domain_reviewed_candidates": [row["candidate_id"] for row in result["audit_history"] if row["role"] == "domain_challenger"],
        "domain_issue_statuses": [row["status"] for row in result["issues"] if row["owner_role"] == "domain_challenger"],
    }

    class PlaybookClient(fixture.FakeClient):
        playbook = bundle

        def attach_playbook(self, role, payload):
            bullets = runtime.retrieve_playbook_bullets(bundle, role, "dreaddit", payload)
            return {**payload, "playbook_bullets": bullets}, {row["bullet_id"] for row in bullets}

    def with_playbook(role, stage, payload):
        response = one_round(role, stage, payload)
        response["playbook_bullet_ids"] = [payload["playbook_bullets"][0]["bullet_id"]]
        return response

    result = runtime.run_packet(fixture.packet(), PlaybookClient(config, with_playbook), policy)
    probes["revision_citation_overwritten"] = {
        "status": result["status"], "final_candidate_ids": result["final_candidate"]["playbook_bullet_ids"],
        "revision_history_ids": [row["report"]["playbook_bullet_ids"] for row in result["audit_history"] if row["role"] == "reviser"],
        "aggregate_used_ids": result["playbook"]["used_bullet_ids"],
    }

    modified = copy.deepcopy(bundle)
    modified["bullets"][0]["exceptions"].append("E999 S999 SP999 PKT_FIXTURE_LEAK_TEST")
    Draft202012Validator(runner.read_json(PROJECT / pb_config["playbook"]["bullet_schema"])).validate(modified["bullets"][0])
    runtime.validate_playbook_bundle(modified)
    probes["source_id_scan_omits_exceptions"] = {"known_source_like_ids_in_exceptions_accepted": True}

    try:
        Draft202012Validator.check_schema(runtime.audit_output_schema({"E1"}, set(), set()))
        empty_schema = "valid_under_installed_jsonschema"
    except SchemaError:
        empty_schema = "invalid_under_installed_jsonschema"
    probes["empty_playbook_enum"] = empty_schema

    supplied = fixture.packet()
    supplied["analytic_contract"] = {"method": "framework", "unit_of_analysis": "participant"}
    supplied["codebook"] = {"version": 1, "codes": []}
    probes["analytic_state_not_forwarded"] = {
        "analytic_contract_forwarded": "analytic_contract" in runtime.packet_payload(supplied),
        "codebook_forwarded": "codebook" in runtime.packet_payload(supplied),
    }

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        local_config = copy.deepcopy(config)
        local_config["output_root"] = str(base)
        config_path = base / "config-source.json"
        runner.write_json(config_path, local_config)
        truth = base / "truth.jsonl"
        runner.atomic_text(truth, json.dumps({"packet_id": "PKT_TEST", "known_intended_flaw_type": "unsupported_evidence"}) + "\n")
        rows = {"dreaddit": [{"packet_id": "PKT_TEST", "corpus_id": "dreaddit", **runtime.packet_payload(fixture.packet())}]}
        bindings = {"dreaddit": {"source_file": str(truth), "source_sha256": runner.sha_file(truth),
                                 "truth_file": str(truth), "truth_sha256": runner.sha_file(truth),
                                 "packet_count": 1, "available_packet_count": 100}}
        args = argparse.Namespace(command="prepare", config=config_path, datasets=["dreaddit"],
                                  configurations=["qwen_only"], sample_n=1, methods=["warrantroute"],
                                  repetitions=1, run_dir=base / "prepared", max_packets=None)
        received = []

        def intercepted_client(*arguments):
            received.append(len(arguments) > 9 and bool(arguments[9]))
            return fixture.FakeClient(local_config, lambda *_: fixture.report())

        with patch.object(runner, "OUTPUT_ROOT", base), \
             patch.object(runner, "verify_models", return_value={}), \
             patch.object(runner, "inputs_for", return_value=(rows, bindings)), \
             patch.object(runtime, "AgentClient", side_effect=intercepted_client), \
             patch.object(runtime, "ollama_transport", side_effect=AssertionError("No model calls permitted")), \
             contextlib.redirect_stdout(io.StringIO()):
            runner.prepare(args)
            frozen = runner.read_json(args.run_dir / "manifest.json")
            runner.write_json(args.run_dir / "playbook_bundle.json", bundle)
            runner.load_run(args.run_dir)
            outcome = runner.execute(args)
        probes["unbound_playbook_file_activates_client_path"] = {
            "config_enabled": runtime.playbook_enabled(local_config),
            "bundle_in_manifest_assets": "playbook_bundle.json" in frozen["assets"],
            "manifest_hash_unchanged": frozen["plan_sha256"] == runner.read_json(args.run_dir / "manifest.json")["plan_sha256"],
            "bundle_passed_to_client": any(received), "fake_execution_status": outcome["status"],
        }

    print(json.dumps({"purpose": "synthetic_offline_implementation_probes_not_scientific_results",
                      "model_calls": 0, "real_corpus_records_read": 0, "probes": probes}, indent=2))


if __name__ == "__main__":
    main()
