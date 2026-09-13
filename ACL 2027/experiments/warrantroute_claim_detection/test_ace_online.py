"""Offline fixtures for online memory and orchestration; never call a live model."""

import copy
import fcntl
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import ace_flaw_contract as base
import ace_online_contract as contract
import run_ace_flaw_online as runtime


def packet(pid="packet_alpha", source="source_alpha", text="One participant reports school stress."):
    task = {"claim": "Every account concerns work.", "cited_excerpt_ids": ["excerpt_alpha"],
            "evidence": [{"excerpt_id": "excerpt_alpha", "text": text, "source_id": source,
                          "source_record_id": pid + "_record"}]}
    return {"packet_id": pid, "task": task, "task_sha256": base.digest(task), "source_ids": [source]}


def learning(task_packet=None):
    task_packet = task_packet or packet()
    evidence = [{"excerpt_id": "excerpt_alpha", "quote": task_packet["task"]["evidence"][0]["text"]}]
    return {"reflection": [{"kind": "useful_check", "lesson": "Check universal scope against supplied countercases.",
                            "evidence": evidence}],
            "patches": [{"id": "patch_1", "operation": "add", "target_rule_id": "", "base_rule_id": "seed-warrant",
                         "applicability": "Universal topic claims across accounts",
                         "detection_check": "Test every/all quantifiers against accounts describing a different topic.",
                         "evidence_requirement": "Locate the claim quantifier and a consequential supplied countercase.",
                         "countercondition": "A claim limited to some accounts permits other topics.",
                         "novel_condition": "A universal quantifier and incompatible topic activate this scope check.",
                         "reflection_indices": [0], "evidence": evidence,
                         "reason": "A specific quantifier check operationalizes the broad warrant seed."}]}


def audit(proposal, value=True):
    return {"edits": [{"patch_id": p["id"], **{k: value for k in base.AUDIT_CRITERIA},
                       "reason": "The scope check is supported by the quoted countercase.",
                       "evidence": p["evidence"]} for p in proposal["patches"]]}


def wire_review():
    return {"decision": "established_flaw", "unresolved": [], "rationale": "The universal topic claim excludes a supplied countercase.",
            "issues": [{"category": "unsupported_inference", "target_kind": "assertion", "claim_quote": "Every account concerns work.",
                        "evidence": [{"excerpt_id": "excerpt_alpha", "quote": "school stress"}],
                        "whole_packet_no_support": "", "mechanism": "A universal claim excludes a different topic.",
                        "material_consequence": "The stated topic coverage is unsupported.", "counterconditions": "A limited claim could be defensible."}]}


class FakeClient:
    def __init__(self, root, unknown=False, reference_failure=False):
        self.run, self.calls = root, []
        self.unknown, self.reference_failure = unknown, reference_failure

    def call(self, key, role, data):
        self.calls.append((key, role, copy.deepcopy(data)))
        if role == "online_detector":
            value = {"review": wire_review(), "rule_checks": {
                r["id"]: {"applicable": True, "outcome": "flaw_supported", "issue_indices": [0],
                          "evidence": [{"excerpt_id": "excerpt_alpha", "quote": "school stress"}],
                          "reason": "The account provides a countercase to universal topic coverage."} for r in data["playbook"]}}
        elif role == "online_learning":
            p = {"task": data["task"]}
            value = learning(p)
            learned = [r for r in data["current_playbook"] if not r["seed"]]
            if learned:
                item = value["patches"][0]
                item.update(operation="reinforce", target_rule_id=learned[0]["id"], novel_condition="")
                item.update({k: "" for k in base.RULE_FIELDS})
            value["patches"] = [{k: v for k, v in p.items() if k != "id"} for p in value["patches"]]
        elif role == "online_audit":
            value = {"edits": {e["patch_id"]: {k: v for k, v in e.items() if k != "patch_id"}
                               for e in audit(data["learning"])["edits"]}}
        elif role == "reference":
            if self.reference_failure:
                raise ValueError("deliberate_reference_failure")
            value = {"decision": "cannot_judge", "issues": [], "unresolved": ["Reference is incomplete."],
                     "rationale": "No defensible reference inventory in this fixture."}
        elif role == "quality":
            value = {"credibility": None if self.unknown else True, "conformability": True,
                     "credibility_reason": "The scope diagnosis is grounded.", "conformability_reason": "The evidence is faithfully quoted.",
                     "allegations": {i["id"]: {"support": "supported", "reason": "Same target and supplied evidence."} for i in data["review"]["issues"]},
                     "matches": []}
        else:
            raise AssertionError(role)
        return contract.decode_wire(role, value, data)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.state = packet(), contract.seed_state()
        self.proposal = learning(self.packet)

    def commit(self, proposal=None, state=None, item=None):
        proposal = proposal or self.proposal
        return contract.apply_audited(state or self.state, proposal, audit(proposal), item or self.packet)

    def test_grounded_add_changes_content_and_next_query_retrieval(self):
        result, receipts = self.commit()
        self.assertEqual(receipts[0]["outcome"], "added")
        self.assertNotEqual(contract.content_hash(result), contract.content_hash(self.state))
        self.assertEqual(len(contract.retrieve(result, self.packet["task"])), 3)
        self.assertEqual(self.state, contract.seed_state())

    def test_duplicate_seed_is_noop_not_rule_growth(self):
        self.proposal["patches"][0].update({k: base.SEED[0][k] for k in base.RULE_FIELDS})
        eligible, receipts = contract.eligible_patches(self.proposal, self.packet, self.state)
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "duplicate_noop")

    def test_invalid_sibling_does_not_block_valid_delta(self):
        invalid = copy.deepcopy(self.proposal["patches"][0])
        invalid.update(id="patch_2", evidence=[{"excerpt_id": "excerpt_alpha", "quote": "invented quotation"}])
        self.proposal["patches"].insert(0, invalid)
        eligible, withheld = contract.eligible_patches(self.proposal, self.packet, self.state)
        result, receipts = self.commit(eligible)
        self.assertEqual(len(result["rules"]), 3)
        self.assertEqual(withheld[0]["outcome"], "withheld_integrity")
        self.assertEqual(receipts[0]["outcome"], "added")

    def test_semantic_unknown_withholds_only_its_edit(self):
        other = copy.deepcopy(self.proposal["patches"][0])
        other.update(id="patch_2", detection_check="Inspect the scope of universal quantifiers and any exceptions.")
        self.proposal["patches"].append(other)
        assessment = audit(self.proposal)
        assessment["edits"][0][base.AUDIT_CRITERIA[0]] = None
        result, receipts = contract.apply_audited(self.state, self.proposal, assessment, self.packet)
        self.assertEqual([r["outcome"] for r in receipts], ["withheld", "added"])
        self.assertEqual(len(result["rules"]), 3)

    def test_seed_refinement_is_forbidden(self):
        self.proposal["patches"][0].update(operation="refine", target_rule_id="seed-warrant")
        eligible, receipts = contract.eligible_patches(self.proposal, self.packet, self.state)
        self.assertFalse(eligible["patches"])
        self.assertIn("seed_or_missing", receipts[0]["reason"])

    def test_explicit_reinforcement_preserves_content_and_deduplicates_epochs(self):
        patch_ = self.proposal["patches"][0]
        patch_.update(operation="reinforce", target_rule_id="seed-warrant", novel_condition="")
        patch_.update({k: "" for k in base.RULE_FIELDS})
        result, receipts = self.commit()
        again, repeated = self.commit(state=result)
        self.assertEqual(receipts[0]["outcome"], "reinforced")
        self.assertEqual(repeated[0]["outcome"], "repeated_support_noop")
        self.assertEqual(result, again)
        self.assertEqual(contract.content_hash(self.state), contract.content_hash(result))
        self.assertEqual(result["rules"], base.SEED)

    def test_same_text_different_packet_id_is_not_new_support(self):
        state, _ = self.commit()
        item = self.proposal["patches"][0]
        item.update(operation="reinforce", target_rule_id=state["rules"][-1]["id"], novel_condition="")
        item.update({k: "" for k in base.RULE_FIELDS})
        again, receipts = self.commit(state=state, item=packet(pid="another_packet"))
        self.assertEqual(receipts[0]["outcome"], "repeated_support_noop")
        self.assertEqual(state, again)

    def test_refinement_keeps_identity_and_bumps_version(self):
        state, _ = self.commit()
        self.proposal["patches"][0].update(operation="refine", target_rule_id=state["rules"][-1]["id"],
                                         countercondition="An explicit exception can preserve the scope of a limited claim.")
        after, receipts = self.commit(state=state)
        self.assertEqual(receipts[0]["outcome"], "refined")
        self.assertEqual(after["rules"][-1]["version"], 2)
        self.assertEqual(after["rules"][-1]["id"], state["rules"][-1]["id"])

    def test_bad_audit_quote_cannot_commit(self):
        value = audit(self.proposal)
        value["edits"][0]["evidence"][0]["quote"] = "fabricated"
        after, receipts = contract.apply_audited(self.state, self.proposal, value, self.packet)
        self.assertEqual(after, self.state)
        self.assertEqual(receipts[0]["outcome"], "withheld")

    def test_no_reference_required_in_learning_schema(self):
        schema = contract.wire_schema("online_learning", {"current_playbook": base.visible_memory(self.state["rules"])})
        self.assertEqual(schema["properties"]["patches"]["maxItems"], 2)
        self.assertNotIn("reference_issue_ids", schema["properties"]["patches"]["items"]["properties"])

    def test_identifier_and_quote_leakage_are_rejected(self):
        for field_value in ("Check source_alpha in later claims.", "One participant reports school stress with many repeated quoted words."):
            p = copy.deepcopy(self.proposal)
            item = packet(text="One participant reports school stress with many repeated quoted words.")
            p["patches"][0]["detection_check"] = field_value
            eligible, receipts = contract.eligible_patches(p, item, self.state)
            self.assertFalse(eligible["patches"])
            self.assertEqual(receipts[0]["outcome"], "withheld_integrity")

    def test_reference_scores_and_future_not_in_updater_payload(self):
        locked = {"review": {}, "rule_checks": {}, "checks": {"integrity_findings": []},
                  "quality": {"credibility": True}, "provisional_reference": "secret", "future": "secret"}
        payload = contract.learning_input(self.packet, locked, self.state)
        self.assertEqual(set(payload), {"task", "locked_prediction", "rule_checks", "integrity_findings", "current_playbook"})
        self.assertNotIn("secret", json.dumps(payload))

    def test_memory_capacity_rejection_rolls_back_partial_edit(self):
        with patch.object(contract, "MEMORY_BYTES", 1):
            result, receipts = self.commit()
        self.assertEqual(result, self.state)
        self.assertIn("memory_context_capacity", receipts[0]["reason"])

    def test_trace_cannot_claim_unlinked_or_fabricated_support_silently(self):
        retrieved = contract.retrieve(self.state, self.packet["task"])
        value = FakeClient(Path("unused")).call("check", "online_detector", {"task": self.packet["task"], "playbook": retrieved})
        check = value["rule_checks"]["seed-warrant"]
        check.update(issue_indices=[7], evidence=[{"excerpt_id": "excerpt_alpha", "quote": "fabricated"}])
        checked = contract.check_detection(value, self.packet["task"], retrieved)
        kinds = {f["kind"] for f in checked["rule_integrity_findings"]}
        self.assertIn("rule_issue_link_out_of_range", kinds)
        self.assertIn("invalid_evidence_quote", kinds)
        self.assertFalse(checked["integrity_findings"])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.item = packet()
        self.job = {"id": "online/dreaddit/0001-packet_alpha", "phase": "online", "dataset": "dreaddit",
                    "position": 1, "epoch": 0, "packet_id": "packet_alpha"}
        self.client = FakeClient(self.root)

    def test_order_locks_judgments_before_update_and_next_packet_uses_rule(self):
        state, parent = runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        roles = [r for _, r, _ in self.client.calls]
        self.assertEqual(roles, ["online_detector", "online_detector", "reference", "quality", "quality", "online_learning", "online_audit"])
        next_item = packet(pid="packet_beta", text="A different person reports school stress.")
        next_job = {**self.job, "id": "online/dreaddit/0002-packet_beta", "position": 2, "packet_id": "packet_beta"}
        count = len(self.client.calls)
        runtime.process_job(self.client, next_job, next_item, state, parent)
        online_call = self.client.calls[count]
        self.assertEqual(len(online_call[2]["playbook"]), 3)
        static_call = self.client.calls[count + 1]
        self.assertEqual(len(static_call[2]["playbook"]), 2)
        self.assertEqual(state["rules"][-1]["version"], 1)

    def test_reference_failure_does_not_suppress_source_grounded_learning(self):
        self.client.reference_failure = True
        state, _ = runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        self.assertEqual(len(state["rules"]), 3)
        update = next(data for _, role, data in self.client.calls if role == "online_learning")
        self.assertNotIn("provisional_reference", update)

    def test_completed_job_replay_makes_no_new_calls(self):
        state, parent = runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        n = len(self.client.calls)
        again, same_parent = runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        self.assertEqual((state, parent), (again, same_parent))
        self.assertEqual(len(self.client.calls), n)

    def test_crash_after_steps_before_commit_does_not_redraw(self):
        runtime.execute_job(self.client, self.job, self.item, contract.seed_state(), None)
        n = len(self.client.calls)
        runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        self.assertEqual(len(self.client.calls), n)

    def test_memory_chain_tampering_detected(self):
        runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        with self.assertRaises(runtime.FrozenError):
            runtime.process_job(self.client, self.job, self.item, contract.seed_state(), "wrong-parent")

    def test_locked_artifact_tampering_detected(self):
        runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        path = self.root / "predictions" / self.job["id"] / "online.locked.json"
        runtime.write_json(path, {"tampered": True}, replace=True)
        with self.assertRaises(runtime.FrozenError):
            runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)

    def test_quality_unknown_not_forced_binary(self):
        self.client.unknown = True
        runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        row = runtime.load_record(self.root / "results" / self.job["id"] / "result.json")["value"]
        counts = runtime.quality_stats([row], "online", "credibility", 80)
        self.assertEqual((counts["null"], counts["binary_n"], counts["pending"]), (1, 0, 79))
        self.assertIsNone(counts["success_pct_binary"])

    def build_schedule(self, epochs=1):
        data = {ds: {"development": [packet(ds + "_dev", ds + "_dev_source", ds + " development school stress")],
                     "evaluation": [packet(ds + "_stream", ds + "_stream_source", ds + " stream school stress")]}
                for ds in runtime.DATASETS}
        runtime.write_json(self.root / "inputs.private.json", data)
        runtime.write_json(self.root / "schedule.json", runtime.schedule(data, epochs))
        runtime.write_json(self.root / "config.json", {"development_n": 1, "stream_n": 1, "epochs": epochs,
                           "options": runtime.OPTIONS, "base_url": runtime.legacy.BASE,
                           "paid_api_allowed": False, "model": runtime.legacy.MODEL, "call_ceiling": 100})
        return data

    def test_full_four_corpus_schedule_and_final_export(self):
        self.build_schedule()
        result = runtime.worker(self.root, self.client)
        self.assertEqual(result["stream_completed"], 4)
        self.assertEqual(result["binary_quality_pairs"], 8)
        final = runtime.read(self.root / "final_manifest.json")
        self.assertEqual(final["table_rows"], 8)
        self.assertEqual(final["status"], "completed_binary_quality")
        self.assertEqual(len(self.client.calls), 40)
        self.assertTrue(all(p["learned_rules"] == 1 for p in result["playbooks"]))

    def test_unknowns_preserved_at_finalization(self):
        self.build_schedule(epochs=0)
        self.client.unknown = True
        runtime.worker(self.root, self.client)
        self.assertEqual(runtime.read(self.root / "final_manifest.json")["status"], "completed_with_unresolved_quality")

    def test_pause_after_current_item_then_replay_resume(self):
        self.build_schedule(epochs=0)
        original = self.client.call
        def trigger(key, role, data):
            if role == "online_detector" and not (self.root / "PAUSE.request.json").exists():
                runtime.write_json(self.root / "PAUSE.request.json", {"requested": True})
            return original(key, role, data)
        self.client.call = trigger
        result = runtime.worker(self.root, self.client)
        self.assertEqual(result["status"], "paused_at_item_boundary")
        self.assertEqual(result["stream_completed"], 1)
        self.assertEqual(len(self.client.calls), 7)
        self.assertTrue((self.root / "deltas" / runtime.read(self.root / "schedule.json")[0]["id"] / "decision.json").exists())
        (self.root / "PAUSE.request.json").unlink()
        self.client.call = original
        runtime.worker(self.root, self.client)
        self.assertEqual(len(self.client.calls), 28)

    def test_input_overlap_and_balance_gates(self):
        data = self.build_schedule()
        self.assertEqual(runtime.validate_inputs(data), (1, 1))
        data["dreaddit"]["evaluation"] = copy.deepcopy(data["dreaddit"]["development"])
        with self.assertRaisesRegex(ValueError, "id_overlap"):
            runtime.validate_inputs(data)

    def test_transport_replays_identical_response(self):
        self.build_schedule()
        client = runtime.Client(self.root, time.time() + 1000)
        body = {"done": True, "response": json.dumps({"decision": "cannot_judge", "issues": [], "unresolved": [], "rationale": "Incomplete evidence."})}
        with patch.object(runtime.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as send:
            first = client.call("test/reference", "reference", {"task": self.item["task"]})
            again = client.call("test/reference", "reference", {"task": self.item["task"]})
        self.assertEqual(first, again)
        self.assertEqual(send.call_count, 1)

    def test_ambiguous_dispatch_is_never_retried(self):
        self.build_schedule()
        client = runtime.Client(self.root, time.time() + 1000)
        with patch.object(runtime.urllib.request, "urlopen", side_effect=TimeoutError("timeout")) as send:
            for _ in range(2):
                with self.assertRaises(runtime.AmbiguousCall):
                    client.call("test/reference", "reference", {"task": self.item["task"]})
        self.assertEqual(send.call_count, 1)

    def test_deadline_prevents_dispatch(self):
        self.build_schedule()
        client = runtime.Client(self.root, time.time() + 1)
        with patch.object(runtime.urllib.request, "urlopen") as send:
            with self.assertRaises(runtime.BudgetStop):
                client.call("test/reference", "reference", {"task": self.item["task"]})
        send.assert_not_called()
        self.assertFalse((self.root / "calls").exists())

    def test_prepare_is_offline_and_imports_only_inputs(self):
        data = self.build_schedule()
        source = self.root / "source"
        source.mkdir()
        runtime.write_json(source / "inputs.private.json", data)
        runtime.write_json(source / "manifest.json", {"model_digest": "fixture-model",
                           "files": {"inputs.private.json": runtime.file_hash(source / "inputs.private.json")}})
        prepared = self.root / "prepared"
        with patch.object(runtime.urllib.request, "urlopen", side_effect=AssertionError("No network allowed")):
            status = runtime.prepare(prepared, source, epochs=1)
        self.assertEqual(status["status"], "prepared_not_started")
        self.assertFalse((prepared / "calls").exists())
        self.assertFalse((prepared / "clock.json").exists())
        config = runtime.read(prepared / "config.json")
        self.assertEqual(config["imported_predictions_scores_references_playbooks"], 0)
        self.assertEqual(config["call_ceiling"], 36)
        self.assertEqual(config["gold_status"], "missing_blocks_inference")
        self.assertTrue(status["inference_blocked"])
        runtime.verify(prepared)

    def test_shared_lock_blocks_before_model_contact(self):
        self.build_schedule()
        lock_path = self.root / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(runtime, "verify", return_value={"project_root": str(self.root)}), \
                    patch.object(runtime.legacy, "model_identity") as identity:
                with self.assertRaises(BlockingIOError):
                    runtime.run_local(self.root)
            identity.assert_not_called()

    def test_completed_response_corruption_is_not_replayed(self):
        self.build_schedule()
        client = runtime.Client(self.root, time.time() + 1000)
        body = {"done": True, "response": json.dumps({"decision": "cannot_judge", "issues": [], "unresolved": [], "rationale": "Incomplete evidence."})}
        with patch.object(runtime.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
            client.call("test/reference", "reference", {"task": self.item["task"]})
        path = self.root / "calls/test/reference/response.json"
        value = runtime.read(path)
        value["body"]["response"] = "changed"
        runtime.write_json(path, value, replace=True)
        with self.assertRaises(runtime.FrozenError):
            client.call("test/reference", "reference", {"task": self.item["task"]})

    def test_empty_delta_does_not_call_auditor(self):
        original = self.client.call
        def empty(key, role, data):
            if role == "online_learning":
                self.client.calls.append((key, role, data))
                return {"reflection": [], "patches": []}
            return original(key, role, data)
        self.client.call = empty
        state, _ = runtime.process_job(self.client, self.job, self.item, contract.seed_state(), None)
        self.assertEqual(state, contract.seed_state())
        self.assertNotIn("online_audit", [r for _, r, _ in self.client.calls])

    def test_judge_does_not_receive_rule_trace_method_identity(self):
        state, _ = contract.apply_audited(contract.seed_state(), learning(), audit(learning()), self.item)
        original = self.client.call
        def invalid_trace(key, role, data):
            value = original(key, role, data)
            if role == "online_detector":
                for key, check in value["rule_checks"].items():
                    if key.startswith("learned-"):
                        check["issue_indices"] = [7]
            return value
        self.client.call = invalid_trace
        runtime.process_job(self.client, self.job, self.item, state, None)
        judges = [data for _, role, data in self.client.calls if role == "quality"]
        self.assertTrue(all("learned-" not in json.dumps(data) for data in judges))
        updater = next(data for _, role, data in self.client.calls if role == "online_learning")
        self.assertTrue(any(f.get("kind") == "rule_issue_link_out_of_range" for f in updater["integrity_findings"]))

    def test_budget_aware_retrieval_is_explicit_and_keeps_all_evidence(self):
        self.build_schedule()
        state, _ = contract.apply_audited(contract.seed_state(), learning(), audit(learning()), self.item)
        config = runtime.read(self.root / "config.json")
        _, seed_bound = runtime.build_request(config, "online_detector", {
            "task": self.item["task"], "playbook": contract.retrieve(contract.seed_state(), self.item["task"])})
        config["options"] = {**config["options"], "num_ctx": seed_bound}
        runtime.write_json(self.root / "config.json", config, replace=True)
        result = runtime.prediction(self.client, self.job, self.item, state, "online")
        self.assertEqual(result["value"]["retrieval_budget_omitted"], 1)
        self.assertEqual(self.client.calls[0][2]["task"], self.item["task"])
        self.assertEqual(len(result["value"]["retrieved_rules"]), 2)
        self.assertEqual(len(state["rules"]), 3)

    def test_fifty_item_checkpoint_and_learning_curve_denominators(self):
        data = self.build_schedule(epochs=0)
        for ds in runtime.DATASETS:
            data[ds]["evaluation"] = [packet(f"{ds}_stream_{n}", f"{ds}_source_{n}",
                                             f"{ds} account {n} reports school stress.") for n in range(20)]
        jobs = runtime.schedule(data, 0)
        runtime.write_json(self.root / "inputs.private.json", data, replace=True)
        runtime.write_json(self.root / "schedule.json", jobs, replace=True)
        config = runtime.read(self.root / "config.json")
        config["stream_n"] = 20
        runtime.write_json(self.root / "config.json", config, replace=True)
        states = {ds: contract.seed_state() for ds in runtime.DATASETS}
        parents = {ds: None for ds in runtime.DATASETS}
        packets = {(ds, p["packet_id"]): p for ds in runtime.DATASETS for p in data[ds]["evaluation"]}
        for job in jobs[:50]:
            ds = job["dataset"]
            states[ds], parents[ds] = runtime.process_job(self.client, job, packets[(ds, job["packet_id"])], states[ds], parents[ds])
        status = runtime.export(self.root, "running")
        self.assertEqual(status["stream_completed"], 50)
        self.assertEqual(status["stream_expected"], 80)
        checkpoint = self.root / "checkpoints/items-0050.json"
        before = runtime.file_hash(checkpoint)
        runtime.export(self.root, "paused_at_item_boundary")
        self.assertEqual(before, runtime.file_hash(checkpoint))
        self.assertTrue((self.root / "learning_curve.csv").exists())


if __name__ == "__main__":
    unittest.main()
