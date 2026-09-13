"""Offline ancestry, new-data coverage, and full-panel stopping tests."""

import copy
import unittest
from unittest.mock import patch

import run_dreaddit_playbook_panel as panel
import test_paragraph_followup as fixtures
from test_paragraph_growth import GrowthFixture


class PanelTests(unittest.TestCase):
    def setUp(self):
        inputs = fixtures.source_inputs()
        original = inputs["dreaddit"]["development"][0]
        for batch in range(4):
            extra = copy.deepcopy(original)
            extra["packet_id"] = f"parent_zeta_{batch}"
            for index, excerpt in enumerate(extra["task"]["evidence"]):
                excerpt.update(excerpt_id=f"extra_{batch}_{index}", source_id=f"source_{batch}_{index}",
                    source_record_id=f"record_{batch}_{index}", text=excerpt["text"] + f" Additional panel {batch}.")
            extra["task"]["cited_excerpt_ids"] = [f"extra_{batch}_0"]
            extra["task_sha256"] = panel.runtime.digest(extra["task"])
            inputs["dreaddit"]["development"].append(extra)
        setup = fixtures.FollowupExecutionTests()
        with patch.object(fixtures, "source_inputs", return_value=inputs):
            setup.setUp()
        self.addCleanup(setup.doCleanups)
        self.prior, self.run = setup.root / "growth", setup.root / "panel"
        with patch("builtins.print"), patch.object(panel.runtime.urllib.request, "urlopen", side_effect=AssertionError("offline only")):
            panel.growth.previous.worker(setup.run, fixtures.JournalFixture(setup.run, True))
            panel.growth.prepare(self.prior, setup.run)
            panel.growth.worker(self.prior, fixtures.JournalFixture(self.prior, False))
            panel.prepare(self.run, self.prior)

    def test_twelve_new_paragraphs_exclude_entire_ancestry(self):
        used, lineage = panel.ancestry(self.prior)
        selected = panel.runtime.read(self.run / "inputs.private.json")
        self.assertEqual(len(used), 8)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len(lineage), 3)
        self.assertFalse({p["source_record_id"] for p in used} & {p["source_record_id"] for p in selected})
        self.assertTrue(all(p["task"]["claim"] == p["task"]["evidence"][0]["text"] for p in selected))
        self.assertTrue((self.run / "data_points.md").exists())
        config = panel.runtime.read(self.run / "config.json")
        self.assertEqual((config["paragraph_n"], config["call_ceiling"], config["budget_seconds"]), (12, 108, 1200))
        self.assertEqual(panel.runtime.read(self.run / "initial_state.json"),
                         panel.runtime.read(self.prior / "playbooks/dreaddit/current.json"))
        panel.verify(self.run)

    def test_each_paragraph_has_three_epoch_slots(self):
        jobs = panel.runtime.read(self.run / "schedule.json")
        self.assertEqual(len(jobs), 36)
        ids = {j["packet_id"] for j in jobs}
        self.assertEqual(len(ids), 12)
        self.assertTrue(all({j["epoch"] for j in jobs if j["packet_id"] == key} == {1, 2, 3} for key in ids))

    def test_four_rule_target_cannot_skip_the_remaining_new_data(self):
        with patch("builtins.print"):
            result = panel.worker(self.run, GrowthFixture(self.run, "add"))
        self.assertEqual(result["status"], "stopped_panel_covered_and_target_delivered")
        self.assertEqual(result["completed_queries"], 12)
        self.assertEqual(result["distinct_paragraphs_completed"], 12)
        self.assertEqual(result["additional_rules_admitted"], 4)
        self.assertTrue(result["ready_to_stop"])
        panel.verify(self.run)

    def test_no_change_finishes_all_thirty_six_without_invented_rules(self):
        with patch("builtins.print"):
            result = panel.worker(self.run, fixtures.JournalFixture(self.run, False))
        self.assertEqual(result["status"], "stopped_epoch_cap")
        self.assertEqual(result["completed_queries"], 36)
        self.assertEqual(result["distinct_paragraphs_completed"], 12)
        self.assertEqual(result["additional_rules_admitted"], 0)
        self.assertIsNone(result["detection_accuracy"])
        self.assertEqual((self.run / "playbook_comparison/changes.diff").read_text(), "")
        panel.verify(self.run)

    def test_modified_ancestor_manifest_artifact_is_not_accepted(self):
        panel.runtime.write_text(self.prior / "summary.md", "changed", replace=True)
        with self.assertRaisesRegex(ValueError, "frozen_file_changed"):
            panel.ancestry(self.prior)


if __name__ == "__main__":
    unittest.main()
