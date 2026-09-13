"""TXT memory-format checks using offline fixtures only."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ace_flaw_contract as base
import ace_online_contract as contract
import run_ace_flaw_online as runtime
from test_ace_online import FakeClient, audit, learning, packet


class TextContractTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.state = packet(), contract.seed_state()

    def add_rule(self, state=None):
        proposal = learning(self.packet)
        return contract.apply_audited(state or self.state, proposal, audit(proposal), self.packet)[0]

    def test_seed_format_has_stable_ids_and_final_newline(self):
        text = contract.playbook_text(contract.visible_rules(self.state))
        self.assertTrue(text.startswith("## STRATEGIES AND HARD RULES\n\n[shr-00001]"))
        self.assertIn("[shr-00002]", text)
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(len(text.splitlines()), 4)

    def test_added_rule_gets_new_number_without_renumbering_seeds(self):
        after = self.add_rule()
        self.assertEqual(after["text_ids"][after["rules"][-1]["id"]], "shr-00003")
        self.assertEqual({k: after["text_ids"][k] for k in self.state["text_ids"]}, self.state["text_ids"])
        self.assertIn("[shr-00003]", contract.playbook_text(contract.visible_rules(after)))

    def test_refinement_and_reinforcement_preserve_rule_identity(self):
        state = self.add_rule()
        proposal = learning(self.packet)
        rule_id = state["rules"][-1]["id"]
        proposal["patches"][0].update(operation="refine", target_rule_id=rule_id,
            countercondition="An explicitly limited claim can admit other topics.")
        refined, _ = contract.apply_audited(state, proposal, audit(proposal), self.packet)
        self.assertEqual(refined["text_ids"], state["text_ids"])
        self.assertNotEqual(contract.playbook_text(contract.visible_rules(refined)), contract.playbook_text(contract.visible_rules(state)))
        item = proposal["patches"][0]
        item.update(operation="reinforce", novel_condition="", **{k: "" for k in base.RULE_FIELDS})
        reinforced, _ = contract.apply_audited(refined, proposal, audit(proposal), packet(pid="new_packet", text="Another account mentions school stress."))
        self.assertEqual(reinforced["text_ids"], refined["text_ids"])
        self.assertEqual(contract.playbook_text(contract.visible_rules(reinforced)), contract.playbook_text(contract.visible_rules(refined)))

    def test_withheld_or_duplicate_patch_does_not_grow_txt(self):
        proposal = learning(self.packet)
        after, _ = contract.apply_audited(self.state, proposal, audit(proposal, False), self.packet)
        self.assertEqual(after, self.state)
        state = self.add_rule()
        eligible, _ = contract.eligible_patches(proposal, self.packet, state)
        self.assertFalse(eligible["patches"])
        self.assertEqual(len(state["text_ids"]), 3)

    def test_multiline_fields_cannot_create_extra_rule_lines(self):
        rules = contract.visible_rules(self.state)
        rules[0]["detection_check"] += "\n\nCheck a second condition."
        text = contract.playbook_text(rules)
        self.assertEqual(len(text.splitlines()), 4)
        self.assertIn("Check a second condition.", text)

    def test_alias_collision_is_rejected(self):
        self.state["text_ids"]["seed-context"] = "shr-00001"
        with self.assertRaisesRegex(ValueError, "text_id_identity"):
            contract.visible_rules(self.state)

    def test_actual_detector_prompt_contains_same_txt_projection(self):
        state = self.add_rule()
        rules = contract.retrieve(state, self.packet["task"])
        data = {"task": self.packet["task"], "playbook": rules}
        saved = copy.deepcopy(data)
        config = {"model": runtime.legacy.MODEL, "options": runtime.OPTIONS,
                  "base_url": runtime.legacy.BASE, "paid_api_allowed": False}
        request, _ = runtime.build_request(config, "online_detector", data)
        encoded = request["prompt"].split("\nINPUT JSON:\n", 1)[1].split("\nOUTPUT JSON SCHEMA:\n", 1)[0]
        actual = json.loads(encoded)
        self.assertEqual(actual["playbook"]["text"], contract.playbook_text(rules))
        self.assertEqual(actual["playbook"]["rule_index"][-1]["text_id"], "shr-00003")
        self.assertEqual(data, saved)

    def test_refining_an_older_rule_does_not_renumber_later_rules(self):
        first = self.add_rule()
        proposal = learning(self.packet)
        proposal["patches"][0]["detection_check"] = "Inspect differences between universal and explicitly restricted coverage."
        second, _ = contract.apply_audited(first, proposal, audit(proposal), self.packet)
        first_id = first["rules"][-1]["id"]
        proposal["patches"][0].update(operation="refine", target_rule_id=first_id,
            detection_check="Inspect universal topic scope against each relevant countercase.")
        after, _ = contract.apply_audited(second, proposal, audit(proposal), self.packet)
        self.assertEqual(after["text_ids"], second["text_ids"])
        text = contract.playbook_text(contract.visible_rules(after))
        self.assertLess(text.index("[shr-00003]"), text.index("[shr-00004]"))


class TextPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=runtime.legacy.PROJECT / "Storage")
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.root = self.run / "playbooks/dreaddit"
        self.packet = packet()
        self.job = {"id": "development/dreaddit/E1/packet_alpha", "phase": "development", "dataset": "dreaddit",
                    "epoch": 1, "position": 1, "packet_id": self.packet["packet_id"]}
        self.client = FakeClient(self.run)

    def test_committed_result_publishes_txt_and_preserves_previous_revision(self):
        state = contract.seed_state()
        runtime.publish_playbook(self.run, "dreaddit", state)
        seed_hash = runtime.file_hash(self.root / "history/revision-00000.txt")
        after, parent = runtime.process_job(self.client, self.job, self.packet, state, None)
        self.assertIn("[shr-00003]", (self.root / "current.txt").read_text())
        self.assertEqual(runtime.file_hash(self.root / "history/revision-00000.txt"), seed_hash)
        manifest = runtime.read(self.root / "current.manifest.json")
        self.assertEqual(manifest["last_completed_job_sha256"], parent)
        self.assertEqual(manifest["state_sha256"], runtime.digest(after))
        self.assertEqual(manifest["txt_sha256"], runtime.file_hash(self.root / "current.txt"))

    def test_next_query_receives_admitted_txt_rule(self):
        state, _ = runtime.process_job(self.client, self.job, self.packet, contract.seed_state(), None)
        next_item = packet(pid="packet_beta", text="A different account reports school stress.")
        next_job = {**self.job, "id": "development/dreaddit/E1/packet_beta", "packet_id": "packet_beta"}
        pred = runtime.prediction(self.client, next_job, next_item, state, "online")
        self.assertIn("[shr-00003]", pred["value"]["retrieved_playbook_text"])
        self.assertEqual(pred["value"]["retrieved_playbook_text"], (self.root / "current.txt").read_text())

    def test_crash_during_txt_publication_replays_without_model_redraw(self):
        original = runtime.write_text
        def fail_current(path, text, replace=False):
            if path.name == "current.txt":
                raise OSError("offline publication interruption")
            return original(path, text, replace)
        with patch.object(runtime, "write_text", side_effect=fail_current):
            with self.assertRaisesRegex(OSError, "publication interruption"):
                runtime.process_job(self.client, self.job, self.packet, contract.seed_state(), None)
        calls = len(self.client.calls)
        runtime.process_job(self.client, self.job, self.packet, contract.seed_state(), None)
        self.assertEqual(len(self.client.calls), calls)
        self.assertTrue((self.root / "current.txt").exists())

    def test_history_tampering_is_not_silently_overwritten(self):
        runtime.publish_playbook(self.run, "dreaddit", contract.seed_state())
        path = self.root / "history/revision-00000.txt"
        runtime.write_text(path, "deliberately changed fixture\n", replace=True)
        with self.assertRaisesRegex(runtime.FrozenError, "immutable_playbook_text_changed"):
            runtime.publish_playbook(self.run, "dreaddit", contract.seed_state())
        self.assertEqual(path.read_text(), "deliberately changed fixture\n")

    def test_replay_leaves_current_manifest_and_txt_identical(self):
        runtime.process_job(self.client, self.job, self.packet, contract.seed_state(), None)
        paths = [self.root / "current.txt", self.root / "current.manifest.json"]
        hashes = [runtime.file_hash(p) for p in paths]
        runtime.process_job(self.client, self.job, self.packet, contract.seed_state(), None)
        self.assertEqual([runtime.file_hash(p) for p in paths], hashes)


if __name__ == "__main__":
    unittest.main()
