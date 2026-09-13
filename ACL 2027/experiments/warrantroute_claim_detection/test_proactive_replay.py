"""Offline-only proactive replay tests; fixtures are not experimental results."""

import copy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

import run_dreaddit_proactive_replay as replay
import test_dreaddit_panel as panel_tests
import test_paragraph_followup as fixtures

contract, memory, runtime = replay.contract, replay.memory, replay.runtime


class ProactiveFixture:
    def __init__(self, run, additions=0, reject=False):
        self.run, self.additions, self.reject, self.learned = run, additions, reject, 0

    def call(self, key, role, data):
        if role == "online_learning":
            data = {**data, "adaptation_context": contract.adaptation_context(self.run, key)}
        request, _ = contract.Client(self.run, 0).request(role, data)
        runtime.write_json(self.run / "calls" / key / "request.json", {
            "request": request, "request_sha256": runtime.digest(request), "offline_fixture": True})
        excerpt = data["task"]["evidence"][0]
        anchor = {"excerpt_id": excerpt["excerpt_id"], "quote": excerpt["text"]}
        if role == "online_detector":
            value = {"review": {"decision": "no_flaw_established", "issues": [],
                "unresolved": [], "rationale": "Offline fixture, not a scored diagnosis."},
                "rule_checks": {r["id"]: {"applicable": True, "outcome": "no_flaw_supported",
                    "issue_indices": [], "evidence": [anchor], "reason": "Offline trace."} for r in data["playbook"]}}
        elif role == "online_learning":
            value = fixtures.learning({"task": data["task"]})
            value["reflection"] = [{"kind": "useful_check", "lesson": name + ": Offline testing lesson.",
                "evidence": [anchor]} for name in contract.LENSES]
            item = value["patches"][0]
            item.update(evidence=[anchor], applicability=f"Offline condition class {self.learned} is present.")
            item.pop("id")
            if self.learned >= self.additions:
                value["patches"] = []
            self.learned += 1
            Draft202012Validator(contract.learning_schema(data)).validate(value)
        else:
            assessment = fixtures.audit(data["learning"])
            if self.reject:
                for edit in assessment["edits"]:
                    edit["reusable_not_memorized"] = False
                    edit["reason"] = "Offline reusable-procedure rejection."
            value = {"edits": {edit["patch_id"]: {k: v for k, v in edit.items() if k != "patch_id"}
                for edit in assessment["edits"]}}
        return memory.decode_wire(role, value, data)


class ProactiveTests(unittest.TestCase):
    def setUp(self):
        setup = panel_tests.PanelTests()
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        self.comparator = setup.run
        self.run = setup.run.parent / "proactive"
        with patch("builtins.print"), patch.object(runtime.urllib.request, "urlopen", side_effect=AssertionError("offline only")):
            replay.panel.worker(self.comparator, fixtures.JournalFixture(self.comparator, False))
            replay.prepare(self.run, self.comparator)

    def test_pairing_and_prompts_are_frozen(self):
        for name in ("inputs.private.json", "initial_state.json", "schedule.json"):
            self.assertEqual((self.run / name).read_bytes(), (self.comparator / name).read_bytes())
        for role in ("online_detector", "online_audit"):
            self.assertEqual(contract.PROMPTS[role], contract.previous.PROMPTS[role])
        replay.verify(self.run)

    def test_four_opportunities_required_but_zero_patches_allowed(self):
        data = {"current_playbook": memory.visible_rules(memory.seed_state())}
        schema = contract.learning_schema(data)
        value = {"reflection": [{"kind": "no_change", "lesson": lens + ": No novel lesson.",
            "evidence": [{"excerpt_id": "example", "quote": "Text"}]} for lens in contract.LENSES], "patches": []}
        Draft202012Validator(schema).validate(value)
        value["reflection"].pop()
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(value)

    def test_full_run_does_not_stop_at_four_additions(self):
        with patch("builtins.print"):
            result = replay.worker(self.run, ProactiveFixture(self.run, 4))
        self.assertEqual(result["status"], "completed_36_exposures")
        self.assertEqual(result["completed_queries"], 36)
        self.assertEqual(result["additional_rules_admitted"], 4)
        self.assertEqual(result["additional_rules_delivered"], 4)
        self.assertEqual(result["candidate_occurrences"], 4)
        self.assertEqual(result["distinct_candidate_contents"], 4)
        self.assertEqual(result["detector_txt_requests_verified"], 36)
        self.assertIsNone(result["detection_accuracy"])
        self.assertIn("[shr-00007]", (self.run / "playbooks/dreaddit/current.txt").read_text())
        replay.verify(self.run)
        replay.panel.verify(self.comparator)
        with patch.object(replay.smoke, "local_server") as server:
            with self.assertRaisesRegex(ValueError, "terminal_replay_not_resumable"):
                replay.run_local(self.run)
        server.assert_not_called()

    def test_rejection_remains_in_candidate_register_not_active_memory(self):
        with patch("builtins.print"):
            result = replay.worker(self.run, ProactiveFixture(self.run, 1, reject=True))
        self.assertEqual(result["additional_rules_admitted"], 0)
        self.assertEqual(result["candidate_occurrences"], 1)
        self.assertIn("withheld", (self.run / "candidates/current.txt").read_text())
        self.assertEqual((self.run / "playbook_comparison/changes.diff").read_text(), "")
        replay.verify(self.run)

    def test_history_is_previous_same_paragraph_only_and_reaches_wire(self):
        with patch("builtins.print"):
            replay.worker(self.run, ProactiveFixture(self.run, 1, reject=True))
        jobs = runtime.read(self.run / "schedule.json")
        packet_id = jobs[0]["packet_id"]
        for job in jobs:
            sent = runtime.read(self.run / "calls" / job["id"] / "learning/request.json")
            data = json.loads(sent["request"]["prompt"].split("\nINPUT JSON:\n")[1].split("\nOUTPUT JSON SCHEMA:\n")[0])
            context = data["adaptation_context"]
            previous = context["previous_exposure"]
            if job["epoch"] == 1:
                self.assertIsNone(previous)
            else:
                self.assertEqual(previous["epoch"], job["epoch"] - 1)
            if job["epoch"] == 2 and job["packet_id"] == packet_id:
                self.assertEqual(previous["candidates"][0]["audit_not_true"], ["reusable_not_memorized"])
            if job["epoch"] == 2 and job["packet_id"] != packet_id:
                self.assertEqual(previous["candidates"], [])
            self.assertNotIn("comparator_run", data)

    def test_ids_are_stable_and_semantics_not_inferred_from_counts(self):
        item = fixtures.learning()["patches"][0]
        repeated = copy.deepcopy(item)
        repeated.update(id="another_occurrence", reason="Other case")
        self.assertEqual(contract.candidate_id(item), contract.candidate_id(repeated))
        repeated["detection_check"] += " A distinct check."
        self.assertNotEqual(contract.candidate_id(item), contract.candidate_id(repeated))

    def test_wire_schema_matches_prompt(self):
        data = {"current_playbook": memory.visible_rules(memory.seed_state())}
        with patch.object(runtime.urllib.request, "urlopen") as api:
            request, bound = contract.Client(self.run, 0).request("online_learning", data)
        api.assert_not_called()
        self.assertEqual(json.loads(request["prompt"].split("\nOUTPUT JSON SCHEMA:\n")[1]), request["format"])
        self.assertLessEqual(bound, runtime.OPTIONS["num_ctx"])

    def test_pause_before_next_query(self):
        runtime.write_json(self.run / "PAUSE.request.json", {"reason": "offline pause"})
        status = replay.worker(self.run, ProactiveFixture(self.run))
        self.assertEqual(status["status"], "paused_at_query_boundary")
        self.assertEqual(status["local_model_calls"], 0)

    def test_modified_comparator_is_blocked(self):
        runtime.write_text(self.comparator / "summary.md", "changed", replace=True)
        with self.assertRaisesRegex(ValueError, "frozen_file_changed"):
            replay.verify(self.run)

    def test_compact_schema_preserves_operation_constraints(self):
        state = runtime.read(self.run / "initial_state.json")
        data = {"current_playbook": memory.visible_rules(state)}
        original = Draft202012Validator(contract.learning_schema(data))
        compact_schema = contract.compact_learning_schema(data)
        compact = Draft202012Validator(compact_schema)
        self.assertLess(len(json.dumps(compact_schema)), len(json.dumps(original.schema)))
        for branch in compact_schema["properties"]["patches"]["items"]["anyOf"]:
            self.assertEqual(branch["type"], "object")
            self.assertFalse(branch["additionalProperties"])
        for operation in ("add", "refine", "reinforce"):
            for target in ("", "seed-warrant", state["rules"][-1]["id"], "absent"):
                for empty in (False, True):
                    value = fixtures.learning()
                    value["reflection"] *= 4
                    item = value["patches"][0]
                    item.pop("id")
                    item.update(operation=operation, target_rule_id=target)
                    if empty:
                        item.update({k: "" for k in (*memory.FIELDS, "novel_condition")})
                    self.assertEqual(original.is_valid(value), compact.is_valid(value))

    def test_reuse_keeps_prefix_and_does_not_redraw_it(self):
        source = self.run
        jobs = runtime.read(source / "schedule.json")
        fixture = ProactiveFixture(source)
        original_call = fixture.call
        def blocked_call(key, role, data):
            if key == jobs[12]["id"] + "/learning":
                runtime.write_json(source / "PAUSE.request.json", {"reason": "offline pre-call failure"})
                raise ValueError("proactive_context_admission_no_truncation")
            return original_call(key, role, data)
        with patch("builtins.print"), patch.object(fixture, "call", side_effect=blocked_call):
            result = replay.worker(source, fixture)
        self.assertEqual(result["completed_queries"], 13)
        target = source.parent / "repaired"
        replay.prepare(target, self.comparator, source)
        copied = runtime.read(target / "reuse_prefix.json")
        self.assertEqual(copied["reused_queries"], 12)
        for name in copied["files"]:
            self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
        with patch("builtins.print"):
            result = replay.worker(target, ProactiveFixture(target))
        self.assertEqual(result["completed_queries"], 36)
        self.assertEqual(result["reused_local_model_calls"], 24)
        self.assertEqual(result["newly_executed_local_model_calls"], 48)
        self.assertEqual(result["technical_failures"], 0)
        replay.verify(target)


if __name__ == "__main__":
    unittest.main()
