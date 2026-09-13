"""Offline fixtures for distinct rule-growth counting and bounded continuation."""

import copy
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import run_dreaddit_playbook_growth as growth
import test_paragraph_followup as fixtures


class GrowthFixture(fixtures.JournalFixture):
    def __init__(self, run, operation):
        super().__init__(run, False)
        self.operation, self.attempts = operation, 0
        self.initial_ids = set(growth.runtime.read(run / "config.json")["initial_rule_ids"])

    def call(self, key, role, data):
        if role != "online_learning" or self.attempts >= 4:
            return super().call(key, role, data)
        request, _ = growth.contract.Client(self.run, 0).request(role, data)
        growth.runtime.write_json(self.run / "calls" / key / "request.json", {
            "request": request, "request_sha256": growth.runtime.digest(request), "offline_fixture": True})
        self.attempts += 1
        value = fixtures.learning({"task": data["task"]})
        excerpt = data["task"]["evidence"][0]
        anchor = {"excerpt_id": excerpt["excerpt_id"], "quote": excerpt["text"]}
        value["reflection"][0]["evidence"] = [anchor]
        item = value["patches"][0]
        item.pop("id")
        item.update(evidence=[anchor], detection_check=f"Offline counting fixture boundary {self.attempts}.")
        if self.operation == "refine":
            item.update(operation="refine", target_rule_id=next(
                r["id"] for r in data["current_playbook"] if not r["seed"] and r["id"] in self.initial_ids))
        Draft202012Validator(growth.contract.learning_schema(data)).validate(value)
        return growth.memory.decode_wire(role, value, data)


class GrowthTests(unittest.TestCase):
    def setUp(self):
        setup = fixtures.FollowupExecutionTests()
        self.inputs = fixtures.source_inputs()
        extra = copy.deepcopy(self.inputs["dreaddit"]["development"][0])
        extra["packet_id"] = "parent_zeta"
        for index, excerpt in enumerate(extra["task"]["evidence"]):
            excerpt.update(excerpt_id=f"extra_excerpt_{index}", source_id=f"extra_source_{index}",
                source_record_id=f"extra_record_{index}", text=excerpt["text"] + " New development panel.")
        extra["task"]["cited_excerpt_ids"] = ["extra_excerpt_0"]
        extra["task_sha256"] = growth.runtime.digest(extra["task"])
        self.inputs["dreaddit"]["development"].append(extra)
        with patch.object(fixtures, "source_inputs", return_value=self.inputs):
            setup.setUp()
        self.addCleanup(setup.doCleanups)
        self.prior = setup.run
        self.run = setup.root / "growth"
        with patch("builtins.print"), patch.object(growth.runtime.urllib.request, "urlopen", side_effect=AssertionError("offline only")):
            growth.previous.worker(self.prior, fixtures.JournalFixture(self.prior, True))
            growth.prepare(self.run, self.prior)

    def test_initial_memory_and_prompts_carried_forward_but_new_inputs_selected(self):
        read = growth.runtime.read
        self.assertEqual(read(self.run / "initial_state.json"), read(self.prior / "playbooks/dreaddit/current.json"))
        new_inputs, old_inputs = read(self.run / "inputs.private.json"), read(self.prior / "inputs.private.json")
        self.assertFalse({p["source_record_id"] for p in new_inputs} & {p["source_record_id"] for p in old_inputs})
        self.assertEqual(len(new_inputs), 4)
        self.assertTrue(all(p["task"]["claim"] == p["task"]["evidence"][0]["text"] for p in new_inputs))
        self.assertEqual(read(self.run / "prompts.json"), read(self.prior / "prompts.json"))
        counts = growth.growth_counts(self.run)
        self.assertEqual(counts["initial_rule_count"], 3)
        self.assertEqual(counts["additional_rules_admitted"], 0)
        self.assertFalse(counts["target_delivered"])
        growth.verify(self.run)

    def test_new_panel_has_three_epochs_without_replaying_previous_data(self):
        prior_jobs = growth.runtime.read(self.prior / "schedule.json")
        jobs = growth.runtime.read(self.run / "schedule.json")
        self.assertEqual(len(jobs), 12)
        self.assertEqual({j["epoch"] for j in jobs}, {1, 2, 3})
        self.assertTrue(all(sum(j["packet_id"] == p["packet_id"] for j in jobs) == 3
            for p in growth.runtime.read(self.run / "inputs.private.json")))
        self.assertFalse({j["id"] for j in jobs} & {j["id"] for j in prior_jobs})
        self.assertEqual(len({j["id"] for j in jobs}), 12)

    def test_heldout_source_record_or_text_is_not_admitted(self):
        for field in ("source_id", "source_record_id", "text"):
            with self.subTest(field=field):
                inputs = copy.deepcopy(self.inputs)
                extra = inputs["dreaddit"]["development"][1]["task"]["evidence"][0]
                inputs["dreaddit"]["evaluation"][0]["task"]["evidence"][0][field] = extra[field]
                with self.assertRaisesRegex(ValueError, "four_unused_development_paragraphs_required"):
                    growth.select_new_paragraphs(inputs, growth.runtime.read(self.prior / "inputs.private.json"))

    def test_four_new_ids_require_a_later_wire_delivery(self):
        with patch("builtins.print"):
            result = growth.worker(self.run, GrowthFixture(self.run, "add"))
        self.assertEqual(result["status"], "stopped_four_additional_rules_delivered")
        self.assertEqual(result["completed_queries"], 5)
        self.assertEqual(result["additional_rules_admitted"], 4)
        self.assertEqual(result["additional_rules_delivered"], 4)
        self.assertEqual(result["current_rule_count"], 7)
        self.assertEqual(result["new_rule_text_ids"], [f"shr-{n:05d}" for n in range(4, 8)])
        self.assertIsNone(result["detection_accuracy"])
        growth.verify(self.run)

    def test_refinements_do_not_count_as_new_rules(self):
        with patch("builtins.print"):
            result = growth.worker(self.run, GrowthFixture(self.run, "refine"))
        self.assertEqual(result["completed_queries"], 12)
        self.assertEqual(result["accepted_add_or_refine_operations"], 4)
        self.assertEqual(result["additional_rules_admitted"], 0)
        self.assertEqual(result["current_rule_count"], 3)
        self.assertFalse(result["target_delivered"])
        growth.verify(self.run)

    def test_no_changes_stop_at_cap_and_keep_snapshots_identical(self):
        with patch("builtins.print"):
            result = growth.worker(self.run, fixtures.JournalFixture(self.run, False))
        self.assertEqual(result["status"], "stopped_query_cap_target_incomplete")
        self.assertEqual(result["additional_rules_admitted"], 0)
        self.assertEqual(result["learned_rules"], 1)
        self.assertEqual((self.run / "playbook_comparison/changes.diff").read_text(), "")
        with patch.object(growth.smoke, "local_server") as server:
            with self.assertRaisesRegex(ValueError, "terminal_growth_not_resumable"):
                growth.run_local(self.run)
        server.assert_not_called()

    def test_changed_initial_memory_is_rejected(self):
        growth.runtime.write_json(self.run / "initial_state.json", {}, replace=True)
        with self.assertRaisesRegex(ValueError, "frozen_file_changed:initial_state.json"):
            growth.verify(self.run)


if __name__ == "__main__":
    unittest.main()
