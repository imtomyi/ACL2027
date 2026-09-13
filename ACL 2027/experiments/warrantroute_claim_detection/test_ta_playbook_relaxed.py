"""Source-free V2 interface/admission fixtures; no semantic evaluation claims."""

import copy
import unittest

from jsonschema import Draft202012Validator, ValidationError

import ta_playbook_relaxed_contract as c
from test_ta_playbook import fixture, config


def input_data(state=None):
    packet, learning, audit = fixture()
    for edit in audit["edits"]:
        edit.pop("no_duplicate_or_contradiction")
        edit.update(no_contradiction=True, operationally_useful=True, distinct_contribution=True)
    state = state or c.memory.seed_state()
    return packet, learning, audit, {"task": packet["task"], "current_playbook": c.memory.visible_rules(state), "learning": learning}


def as_wire(value):
    if isinstance(value, list):
        return [as_wire(v) for v in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"collection", "unit_id", "field", "quote"}:
        return {"target_slot": f"{value['collection']}/{value['unit_id']}/{value['field']}", "quote": value["quote"]}
    result = {k: as_wire(v) for k, v in value.items()}
    if "operation" in result:
        result.pop("id", None)
        if result["operation"] == "add":
            result.pop("target_rule_id")
        if result["operation"] == "reinforce":
            for k in (*c.memory.FIELDS, "novel_condition", "base_rule_id"):
                result.pop(k, None)
        else:
            result["operational_detail"] = result.pop("novel_condition")
    return result


class RelaxedTests(unittest.TestCase):
    def test_schema_for_add_and_two_candidate_audit(self):
        _, learning, _, data = input_data()
        learning["patches"].append({**copy.deepcopy(learning["patches"][0]), "id": "patch_2"})
        for role in ("online_learning", "online_audit"):
            wire = c.schema(role, data)
            Draft202012Validator.check_schema(wire)
            self.assertIn("ta_anchor", wire["$defs"])

    def test_add_without_target_decodes_losslessly(self):
        _, learning, _, data = input_data()
        wire = as_wire(learning)
        original = copy.deepcopy(wire)
        value = c.decode("online_learning", wire, data)
        self.assertEqual(value, learning)
        self.assertEqual(wire, original)
        self.assertEqual(value["patches"][0]["target_rule_id"], "")

    def test_add_with_target_rejected_at_schema_not_silently_fixed(self):
        _, learning, _, data = input_data()
        wire = as_wire(learning)
        wire["patches"][0]["target_rule_id"] = "seed-context"
        with self.assertRaises(ValidationError):
            c.decode("online_learning", wire, data)

    def test_refine_cannot_target_seed(self):
        _, learning, _, data = input_data()
        wire = as_wire(learning)
        wire["patches"][0].update(operation="refine", target_rule_id="seed-context")
        with self.assertRaises(ValidationError):
            c.decode("online_learning", wire, data)

    def test_refine_can_target_learned_rule(self):
        packet, learning, audit, _ = input_data()
        state, _ = c.apply(c.memory.seed_state(), learning, audit, packet)
        _, _, _, data = input_data(state)
        wire = as_wire(learning)
        wire["patches"][0].update(operation="refine", target_rule_id=state["rules"][-1]["id"])
        decoded = c.decode("online_learning", wire, data)
        self.assertEqual(decoded["patches"][0]["target_rule_id"], state["rules"][-1]["id"])

    def test_reinforce_does_not_generate_replacement_text(self):
        _, learning, _, data = input_data()
        learning["patches"][0].update(operation="reinforce", target_rule_id="seed-context")
        decoded = c.decode("online_learning", as_wire(learning), data)
        self.assertTrue(all(decoded["patches"][0][k] == "" for k in c.memory.FIELDS))
        self.assertEqual(decoded["patches"][0]["base_rule_id"], "")

    def test_unknown_slot_rejected_but_bad_quote_not_rewritten(self):
        packet, learning, _, data = input_data()
        wire = as_wire(learning)
        wire["patches"][0]["artifact_evidence"][0]["target_slot"] = "codes/C001/negative_cases"
        with self.assertRaises(ValidationError):
            c.decode("online_learning", wire, data)
        wire = as_wire(learning)
        wire["patches"][0]["artifact_evidence"][0]["quote"] = "Not in that artifact field."
        decoded = c.decode("online_learning", wire, data)
        eligible, receipts = c.eligible(decoded, packet, c.memory.seed_state())
        self.assertEqual(decoded["patches"][0]["artifact_evidence"][0]["quote"], "Not in that artifact field.")
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "withheld_integrity")

    def test_audit_slot_decode_preserves_decisions(self):
        _, _, audit, data = input_data()
        wire = {"edits": {row["patch_id"]: as_wire({k: v for k, v in row.items() if k != "patch_id"}) for row in audit["edits"]}}
        self.assertEqual(c.decode("online_audit", wire, data), audit)

    def test_all_required_failures_and_unknowns_still_withhold(self):
        packet, learning, audit, _ = input_data()
        for key in c.HARD_CRITERIA:
            for verdict in (False, None):
                with self.subTest(key=key, verdict=verdict):
                    changed = copy.deepcopy(audit)
                    changed["edits"][0][key] = verdict
                    state = c.memory.seed_state()
                    after, receipts = c.apply(state, learning, changed, packet)
                    self.assertEqual(after, state)
                    self.assertEqual(receipts[0]["outcome"], "withheld")

    def test_grounded_operational_elaboration_can_be_admitted(self):
        packet, learning, audit, _ = input_data()
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertEqual(receipts, [])
        after, receipts = c.apply(c.memory.seed_state(), eligible, audit, packet)
        self.assertEqual(receipts[0]["outcome"], "added")
        self.assertEqual(len(after["rules"]), 3)
        self.assertIn("Do NOT require a new mechanism", c.PROMPTS["online_audit"])
        self.assertIn("novelty is not required", c.PROMPTS["online_audit"])

    def test_false_or_unknown_novelty_alone_no_longer_blocks(self):
        for verdict in (False, None):
            with self.subTest(verdict=verdict):
                packet, learning, audit, _ = input_data()
                audit["edits"][0]["distinct_contribution"] = verdict
                original = copy.deepcopy(audit)
                after, receipts = c.apply(c.memory.seed_state(), learning, audit, packet)
                self.assertEqual(len(after["rules"]), 3)
                self.assertEqual(audit, original)
                self.assertEqual(receipts[0]["outcome"], "added")
                self.assertIs(receipts[0]["distinct_contribution"], verdict)
                self.assertTrue(receipts[0]["admitted_without_established_novelty"])

    def test_exact_duplicate_and_placeholder_not_added(self):
        packet, learning, _, _ = input_data()
        duplicate = copy.deepcopy(learning)
        duplicate["patches"][0].update({k: c.base.SEED[0][k] for k in c.memory.FIELDS})
        eligible, receipts = c.eligible(duplicate, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "duplicate_noop")
        learning["patches"][0]["applicability"] = "true"
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["reason"], "nonprocedural_placeholder_text")

    def test_source_quote_and_identity_protections_unchanged(self):
        packet, learning, _, _ = input_data()
        learning["patches"][0]["evidence"][0]["quote"] = "fabricated"
        eligible, receipts = c.eligible(learning, packet, c.memory.seed_state())
        self.assertFalse(eligible["patches"])
        self.assertEqual(receipts[0]["outcome"], "withheld_integrity")

    def test_detector_request_unchanged_and_learning_schema_visible(self):
        packet, _, _, data = input_data()
        detector = {"task": packet["task"], "playbook": c.memory.visible_rules(c.memory.seed_state())}
        self.assertEqual(c.request(config(), "online_detector", detector), c.strict.request(config(), "online_detector", detector))
        req, bound = c.request(config(), "online_learning", {**data, "gold": "DO_NOT_SEND", "inspection_notes": "DO_NOT_SEND"})
        self.assertIn("OUTPUT JSON SCHEMA", req["prompt"])
        self.assertIn("operational_detail", req["prompt"])
        self.assertNotIn("DO_NOT_SEND", req["prompt"])
        self.assertLessEqual(bound, 49152)

    def test_no_change_and_no_paid_calls(self):
        _, _, _, data = input_data()
        self.assertEqual(c.decode("online_learning", {"reflection": [], "patches": []}, data), {"reflection": [], "patches": []})
        settings = config()
        settings["paid_api_allowed"] = True
        with self.assertRaisesRegex(ValueError, "local_review_roles_only"):
            c.request(settings, "online_learning", data)


if __name__ == "__main__":
    unittest.main()
