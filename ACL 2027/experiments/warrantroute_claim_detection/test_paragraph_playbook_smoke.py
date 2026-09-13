"""Offline fixtures for the unscored, paragraph-native development smoke test."""

import fcntl
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ace_online_contract as memory
import run_ace_flaw_online as runtime
import run_dreaddit_paragraph_playbook_smoke as smoke
from test_ace_online import FakeClient


def source_inputs():
    evidence = [{"excerpt_id": f"excerpt_{i}", "source_id": f"source_{i}", "source_record_id": f"record_{i}",
        "text": f"Every account concerns work. One participant reports school stress. Account number {i}.",
        "metadata": {"split": "development_train", "stress_label": 1}} for i in range(4)]
    task = {"claim": "UNUSED constructed claim", "evidence": evidence, "cited_excerpt_ids": ["excerpt_0"]}
    parent = {"packet_id": "parent_alpha", "task": task, "task_sha256": runtime.digest(task)}
    return {"dreaddit": {"development": [parent], "evaluation": [{"task": {"evidence": [
        {"text": "Unrelated evaluation text.", "source_id": "heldout_source", "source_record_id": "heldout_record"}]}}]}}


class ParagraphTests(unittest.TestCase):
    def test_four_paragraphs_are_four_queries_not_four_packets_of_four(self):
        packets = smoke.select_paragraphs(source_inputs())
        self.assertEqual(len(packets), 4)
        self.assertTrue(all(len(p["task"]["evidence"]) == 1 for p in packets))
        self.assertTrue(all(p["task"]["claim"] == p["task"]["evidence"][0]["text"] for p in packets))

    def test_builder_claim_and_stress_label_are_not_model_inputs(self):
        packets = smoke.select_paragraphs(source_inputs())
        for item in packets:
            self.assertNotIn("UNUSED", item["task"]["claim"])
            self.assertNotIn("metadata", item["task"]["evidence"][0])

    def test_heldout_records_are_excluded(self):
        data = source_inputs()
        data["dreaddit"]["evaluation"][0]["task"]["evidence"][0]["source_record_id"] = "record_0"
        with self.assertRaisesRegex(ValueError, "evaluation_record_overlap"):
            smoke.select_paragraphs(data)

    def test_source_mutation_is_not_silently_accepted(self):
        data = source_inputs()
        data["dreaddit"]["development"][0]["task"]["evidence"][0]["text"] = "changed"
        with self.assertRaisesRegex(ValueError, "source_task_changed"):
            smoke.select_paragraphs(data)

    def test_prompt_is_paragraph_native_and_never_treats_echo_as_corroboration(self):
        with tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage") as tmp:
            root = Path(tmp)
            runtime.write_json(root / "config.json", {"protocol": smoke.VERSION, "model": runtime.legacy.MODEL,
                "options": runtime.OPTIONS, "base_url": runtime.legacy.BASE, "paid_api_allowed": False})
            packet = smoke.select_paragraphs(source_inputs())[0]
            data = {"task": packet["task"], "playbook": memory.retrieve(memory.seed_state(), packet["task"])}
            with patch.object(runtime.urllib.request, "urlopen") as api:
                request, _ = smoke.ParagraphClient(root, 0).request("online_detector", data)
            api.assert_not_called()
            self.assertNotIn("claim SENTENCE", request["prompt"])
            self.assertIn("NOT independent corroboration", request["prompt"])
            self.assertIn("[shr-00001]", request["prompt"])


class SmokeExecutionTests(unittest.TestCase):
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
        self.run = self.root / "smoke"
        with patch.object(runtime.urllib.request, "urlopen", side_effect=AssertionError("No inference during preparation")):
            self.prepared = smoke.prepare(self.run, source)

    def test_prepare_freezes_twelve_exposures_and_calls_no_model(self):
        self.assertEqual(self.prepared["completed_queries"], 0)
        self.assertEqual(self.prepared["local_model_calls"], 0)
        jobs = runtime.read(self.run / "schedule.json")
        self.assertEqual(len(jobs), 12)
        self.assertEqual({j["epoch"] for j in jobs}, {1, 2, 3})
        self.assertTrue(all(sum(j["packet_id"] == p["packet_id"] for j in jobs) == 3
                            for p in runtime.read(self.run / "inputs.private.json")))
        self.assertFalse((self.run / "clock.json").exists())
        smoke.verify(self.run)

    def test_worker_retains_all_twelve_outcomes_without_inventing_accuracy(self):
        client = FakeClient(self.run)
        with patch("builtins.print"):
            result = smoke.worker(self.run, client)
        self.assertEqual(result["completed_queries"], 12)
        self.assertIsNone(result["detection_accuracy"])
        self.assertIsNone(result["credibility"])
        self.assertEqual(result["status"], "completed_without_demonstrated_update_chain")
        self.assertLessEqual(len(client.calls), 36)
        self.assertNotIn("quality", {role for _, role, _ in client.calls})
        self.assertTrue((self.run / "query_progress.csv").exists())

    def test_shared_lock_blocks_before_server_or_model_contact(self):
        folder = self.root / "Storage/rq2_personal_local_diagnostic"
        folder.mkdir(parents=True)
        with (folder / "ace_flaw_8h.lock").open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(runtime.legacy, "PROJECT", self.root), patch.object(smoke, "local_server") as server:
                with self.assertRaises(BlockingIOError):
                    smoke.run_local(self.run)
            server.assert_not_called()

    def test_reuses_existing_server_without_spawning_or_stopping_it(self):
        with patch.object(smoke, "model_tags", return_value={"models": []}), \
                patch.object(smoke.subprocess, "Popen") as spawn:
            with smoke.local_server(self.run) as tags:
                self.assertEqual(tags, {"models": []})
        spawn.assert_not_called()

    def test_modified_frozen_inputs_block_execution(self):
        value = runtime.read(self.run / "inputs.private.json")
        value[0]["task"]["claim"] = "changed"
        runtime.write_json(self.run / "inputs.private.json", value, replace=True)
        with self.assertRaisesRegex(ValueError, "frozen_file_changed"):
            smoke.verify(self.run)


if __name__ == "__main__":
    unittest.main()
