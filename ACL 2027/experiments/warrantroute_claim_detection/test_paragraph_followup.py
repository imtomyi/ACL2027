"""Offline-only follow-up fixtures. Never report their values as live results."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

import ace_online_contract as memory
import paragraph_followup_contract as contract
import run_ace_flaw_online as runtime
import run_dreaddit_paragraph_playbook_smoke as smoke
import run_dreaddit_playbook_followup as followup
from test_ace_online import FakeClient, audit, learning, packet
from test_paragraph_playbook_smoke import source_inputs


class FollowupContractTests(unittest.TestCase):
    def setUp(self):
        self.state = memory.seed_state()
        self.data = {"current_playbook": memory.visible_rules(self.state)}
        proposal = learning()
        self.value = {**proposal, "patches": [
            {k: v for k, v in p.items() if k != "id"} for p in proposal["patches"]]}

    def validate(self):
        Draft202012Validator(contract.learning_schema(self.data)).validate(self.value)

    def test_add_and_no_change_are_both_valid(self):
        self.validate()
        self.value["patches"] = []
        self.validate()

    def test_seed_refinement_is_excluded_at_wire_boundary(self):
        self.value["patches"][0].update(operation="refine", target_rule_id="seed-warrant")
        with self.assertRaises(ValidationError):
            self.validate()

    def test_add_cannot_target_an_existing_rule(self):
        self.value["patches"][0]["target_rule_id"] = "seed-context"
        with self.assertRaises(ValidationError):
            self.validate()

    def test_each_reusable_field_must_be_nonempty(self):
        original = copy.deepcopy(self.value)
        for key in (*memory.FIELDS, "novel_condition"):
            with self.subTest(key=key):
                self.value = copy.deepcopy(original)
                self.value["patches"][0][key] = ""
                with self.assertRaises(ValidationError):
                    self.validate()

    def test_reinforcement_has_no_content_change(self):
        item = self.value["patches"][0]
        item.update(operation="reinforce", target_rule_id="seed-warrant")
        item.update({key: "" for key in (*memory.FIELDS, "novel_condition")})
        self.validate()
        item["detection_check"] = "Changed text"
        with self.assertRaises(ValidationError):
            self.validate()

    def test_only_learned_ids_can_be_refined_after_adoption(self):
        proposal = learning()
        state, _ = memory.apply_audited(self.state, proposal, audit(proposal), packet())
        self.data["current_playbook"] = memory.visible_rules(state)
        self.value["patches"][0].update(operation="refine", target_rule_id=state["rules"][-1]["id"])
        self.validate()
        self.value["patches"][0]["target_rule_id"] = "seed-context"
        with self.assertRaises(ValidationError):
            self.validate()

    def test_uncertain_audit_still_withholds_a_valid_add(self):
        proposal = learning()
        assessment = audit(proposal)
        assessment["edits"][0][memory.base.AUDIT_CRITERIA[0]] = None
        after, receipts = memory.apply_audited(self.state, proposal, assessment, packet())
        self.assertEqual(after, self.state)
        self.assertEqual(receipts[0]["outcome"], "withheld")

    def test_request_schema_matches_prompt_and_no_api_is_called(self):
        with tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage") as tmp:
            root = Path(tmp)
            runtime.write_json(root / "config.json", {"protocol": contract.VERSION,
                "model": runtime.legacy.MODEL, "options": runtime.OPTIONS,
                "base_url": runtime.legacy.BASE, "paid_api_allowed": False})
            with patch.object(runtime.urllib.request, "urlopen") as api:
                request, bound = contract.Client(root, 0).request("online_learning", self.data)
            api.assert_not_called()
            embedded = json.loads(request["prompt"].split("\nOUTPUT JSON SCHEMA:\n")[1])
            self.assertEqual(embedded, request["format"])
            self.assertLessEqual(bound, runtime.OPTIONS["num_ctx"])
            self.assertIn("No patches remains valid", request["prompt"])


class JournalFixture:
    def __init__(self, run, allow_add):
        self.run, self.allow_add = run, allow_add

    def call(self, key, role, data):
        request, _ = contract.Client(self.run, 0).request(role, data)
        runtime.write_json(self.run / "calls" / key / "request.json", {
            "request": request, "request_sha256": runtime.digest(request), "offline_fixture": True})
        excerpt = data["task"]["evidence"][0]
        anchor = {"excerpt_id": excerpt["excerpt_id"], "quote": excerpt["text"]}
        if role == "online_detector":
            value = {"review": {"decision": "no_flaw_established", "issues": [],
                "unresolved": [], "rationale": "Offline fixture for control flow, not an evaluation."},
                "rule_checks": {r["id"]: {"applicable": True, "outcome": "no_flaw_supported",
                    "issue_indices": [], "evidence": [anchor], "reason": "Offline trace."}
                    for r in data["playbook"]}}
        elif role == "online_learning":
            value = learning({"task": data["task"]})
            value["reflection"][0]["evidence"] = [anchor]
            item = value["patches"][0]
            item["evidence"] = [anchor]
            item.pop("id")
            if not self.allow_add or any(not r["seed"] for r in data["current_playbook"]):
                value["patches"] = []
            Draft202012Validator(contract.learning_schema(data)).validate(value)
        else:
            value = {"edits": {e["patch_id"]: {k: v for k, v in e.items() if k != "patch_id"}
                for e in audit(data["learning"])["edits"]}}
        return memory.decode_wire(role, value, data)


class FollowupExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        source.mkdir()
        runtime.write_json(source / "inputs.private.json", source_inputs())
        runtime.write_json(source / "config.json", {"model_digest": "offline-fixture"})
        runtime.write_json(source / "manifest.json", {"files": {
            p.name: runtime.file_hash(p) for p in source.iterdir()}})
        self.prior, self.run = self.root / "prior", self.root / "followup"
        with patch.object(runtime.urllib.request, "urlopen", side_effect=AssertionError("offline only")), patch("builtins.print"):
            smoke.prepare(self.prior, source)
            smoke.worker(self.prior, FakeClient(self.prior))
            followup.prepare(self.run, self.prior)

    def test_preparation_retains_inputs_state_limits_and_all_epoch_slots(self):
        self.assertEqual(runtime.read(self.run / "inputs.private.json"), runtime.read(self.prior / "inputs.private.json"))
        self.assertEqual(runtime.read(self.run / "initial_state.json"), runtime.read(self.prior / "playbooks/dreaddit/current.json"))
        jobs = runtime.read(self.run / "schedule.json")
        self.assertEqual(len(jobs), 12)
        self.assertEqual({j["epoch"] for j in jobs}, {4, 5, 6})
        config = runtime.read(self.run / "config.json")
        self.assertEqual((config["budget_seconds"], config["call_ceiling"]), (600, 36))
        followup.verify(self.run)

    def test_no_update_reaches_cap_without_fabricating_success(self):
        with patch("builtins.print"):
            result = followup.worker(self.run, JournalFixture(self.run, False))
        self.assertEqual(result["status"], "stopped_query_cap_without_verified_update")
        self.assertEqual(result["completed_queries"], 12)
        self.assertEqual(result["learned_rules"], 0)
        self.assertEqual((self.run / "playbook_comparison/changes.diff").read_text(), "")
        followup.verify(self.run)

    def test_stop_requires_next_actual_request_not_just_first_add(self):
        with patch("builtins.print"):
            result = followup.worker(self.run, JournalFixture(self.run, True))
        self.assertEqual(result["status"], "stopped_update_delivery_verified")
        self.assertEqual(result["completed_queries"], 2)
        self.assertEqual(result["accepted_add_or_refine_operations"], 1)
        self.assertEqual(result["detector_txt_requests_verified"], 2)
        self.assertEqual(result["learned_rule_prompt_inclusions"], 1)
        self.assertIsNone(result["detection_accuracy"])
        self.assertIn("[shr-00003]", (self.run / "playbook_comparison/playbook_after.txt").read_text())
        self.assertNotIn("[shr-00003]", (self.run / "playbook_comparison/playbook_initial.txt").read_text())
        followup.verify(self.run)
        with patch.object(smoke, "local_server") as server:
            with self.assertRaisesRegex(ValueError, "terminal_followup_not_resumable"):
                followup.run_local(self.run)
        server.assert_not_called()

    def test_mutated_frozen_prompt_is_blocked(self):
        runtime.write_json(self.run / "prompts.json", {}, replace=True)
        with self.assertRaisesRegex(ValueError, "frozen_file_changed:prompts.json"):
            followup.verify(self.run)

    def test_pause_stops_before_another_query(self):
        runtime.write_json(self.run / "PAUSE.request.json", {"reason": "offline boundary test"})
        result = followup.worker(self.run, JournalFixture(self.run, False))
        self.assertEqual(result["status"], "paused_at_query_boundary")
        self.assertEqual(result["local_model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
