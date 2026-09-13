"""Source-free contract tests; fixtures are not experiment results."""

import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import run_ta_playbook_smoke as runner
import ta_playbook_contract as c


def fixture():
    evidence = {"excerpt_id": "E_TEST", "source_id": "SOURCE_TEST", "source_record_id": "RECORD_TEST",
                "text": "A software fixture does not establish a population claim."}
    unit = {"code_id": "C001", "definition": "Everybody has this property.", "label": "Software fixture",
            "evidence": [{"source_record_id": "RECORD_TEST", "quote": evidence["text"]}]}
    artifact = {"codes": [unit], "subthemes": [], "themes": [], "source_notes": []}
    packet = {"packet_id": "TA_TEST", "source_ids": ["SOURCE_TEST"],
              "task": {"artifact": artifact, "evidence": [evidence]}}
    aa = {"collection": "codes", "unit_id": "C001", "field": "definition", "quote": unit["definition"]}
    sa = {"excerpt_id": "E_TEST", "quote": "does not establish a population claim"}
    reflection = {"kind": "useful_check", "lesson": "Fixture lesson only.", "evidence": [sa],
                  "artifact_evidence": [aa], "opportunity": "theme_scope_and_counterevidence"}
    proposal = {"id": "patch_1", "operation": "add", "target_rule_id": "", "base_rule_id": "seed-context",
        "applicability": "A code changes a bounded account into a universal population assertion.",
        "detection_check": "Compare the code's explicit population quantifier with the source's sampling scope.",
        "evidence_requirement": "Locate both the quantifier and the scope of the source account.",
        "countercondition": "A clearly bounded within-case interpretation is not a population claim.",
        "novel_condition": "Universal quantifier at the source-to-code boundary.", "reason": "Fixture lesson only.",
        "evidence": [sa], "artifact_evidence": [aa], "reflection_indices": [0]}
    learning = {"reflection": [reflection], "patches": [proposal]}
    audit = {"edits": [{"patch_id": "patch_1", **{k: True for k in c.base.AUDIT_CRITERIA},
                        "reason": "Software admission fixture, not semantic validation.", "evidence": [sa], "artifact_evidence": [aa]}]}
    return packet, learning, audit


def config():
    return {"model": "gemma3:4b", "paid_api_allowed": False, "base_url": runner.runtime.legacy.BASE,
            "options": {"num_ctx": 49152, "num_predict": 4096}, "call_ceiling": 27, "timeout_seconds": 180}


class TATests(unittest.TestCase):
    def test_separate_artifact_and_source_anchors(self):
        packet, learning, _ = fixture()
        aa = learning["patches"][0]["artifact_evidence"]
        self.assertEqual(c.artifact_findings(aa, packet["task"]["artifact"]), [])
        wrong = copy.deepcopy(aa)
        wrong[0]["quote"] = packet["task"]["evidence"][0]["text"]
        self.assertTrue(c.artifact_findings(wrong, packet["task"]["artifact"]))

    def test_schema_valid_for_two_patch_audit(self):
        packet, learning, _ = fixture()
        learning["patches"].append({**copy.deepcopy(learning["patches"][0]), "id": "patch_2"})
        state = c.memory.seed_state()
        for role in c.PROMPTS:
            data = {"task": packet["task"], "playbook": c.memory.visible_rules(state),
                    "current_playbook": c.memory.visible_rules(state), "learning": learning}
            Draft202012Validator.check_schema(c.schema(role, data))
        self.assertEqual(c.memory.LEARNING["properties"]["reflection"]["items"]["required"], ["kind", "lesson", "evidence"])

    def test_admission_ids_and_next_query_delivery(self):
        packet, learning, audit = fixture()
        initial = c.memory.seed_state()
        eligible, receipts = c.eligible(learning, packet, initial)
        self.assertEqual(receipts, [])
        updated, receipts = c.apply(initial, eligible, audit, packet)
        self.assertEqual(receipts[0]["outcome"], "added")
        self.assertEqual(len(initial["rules"]), 2)
        self.assertEqual(len(updated["rules"]), 3)
        text = c.memory.playbook_text(c.memory.visible_rules(updated))
        self.assertIn("[shr-00003]", text)
        request, _ = c.request(config(), "online_detector", {"task": packet["task"], "playbook": c.memory.visible_rules(updated)})
        self.assertIn("shr-00003", request["prompt"])
        self.assertIn(learning["patches"][0]["detection_check"], request["prompt"])

    def test_bad_artifact_anchor_withheld(self):
        packet, learning, _ = fixture()
        learning["patches"][0]["artifact_evidence"][0]["unit_id"] = "C999"
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "withheld_integrity")

    def test_bad_source_anchor_withheld(self):
        packet, learning, _ = fixture()
        learning["patches"][0]["evidence"][0]["quote"] = "not present"
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "withheld_integrity")

    def test_rejected_audit_does_not_add(self):
        packet, learning, audit = fixture()
        audit["edits"][0][c.base.AUDIT_CRITERIA[0]] = False
        state = c.memory.seed_state()
        after, receipts = c.apply(state, learning, audit, packet)
        self.assertEqual(after, state)
        self.assertEqual(receipts[0]["outcome"], "withheld")

    def test_artifact_id_leakage_withheld(self):
        packet, learning, _ = fixture()
        learning["patches"][0]["detection_check"] = "Examine C001 every time."
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["reason"], "ta_identifier_leakage")

    def test_empty_update_is_valid(self):
        packet, _, _ = fixture()
        eligible, receipts = c.eligible({"reflection": [], "patches": []}, packet, c.memory.seed_state())
        self.assertEqual(eligible["patches"], [])
        self.assertEqual(receipts, [])

    def test_prompt_has_no_paragraph_scope_or_external_feedback(self):
        packet, learning, _ = fixture()
        data = {"task": packet["task"], "current_playbook": c.memory.visible_rules(c.memory.seed_state()),
                "learning": learning, "gold": "FORBIDDEN", "inspection_notes": "FORBIDDEN", "scores": "FORBIDDEN"}
        for role in ("online_learning", "online_audit"):
            request, bound = c.request(config(), role, data)
            self.assertNotIn("FORBIDDEN", request["prompt"])
            self.assertNotIn("Assess ONLY the supplied original claim SENTENCE", request["prompt"])
            self.assertLessEqual(bound, 49152)
            self.assertIn("LOCKED TA ARTIFACT", request["prompt"])

    def test_missing_response_never_resends(self):
        packet, _, _ = fixture()
        data = {"task": packet["task"], "playbook": c.memory.visible_rules(c.memory.seed_state())}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            runner.runtime.write_json(run / "config.json", config())
            request, _ = c.request(config(), "online_detector", data)
            runner.runtime.write_json(run / "calls/test/request.json", {"request_sha256": runner.runtime.digest(request)})
            with patch("urllib.request.urlopen") as send:
                with self.assertRaises(runner.runtime.AmbiguousCall):
                    runner.Client(run, time.time() + 600).call("test", "online_detector", data)
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
