"""Separate development contract; never changes the completed paragraph smoke run."""

import copy
import json

from jsonschema import Draft202012Validator

import ace_online_contract as memory
import run_ace_flaw_online as runtime
import run_dreaddit_paragraph_playbook_smoke as smoke


VERSION = "dreaddit-paragraph-playbook-followup-v1"
PROMPTS = {
    "online_detector": smoke.PROMPTS["online_detector"] + """
Paragraph-specific decision boundary: distinguish a reported event, a subjective
experience, an open question, and an asserted inference before alleging a flaw.
The absence of independent corroboration for a reported event is not an internal
contradiction. A question about a possibility does not assert that possibility.
Establish a failed inferential step or consequential inconsistency in the actual
words, not a demand that every personal account contain external proof. Do not
convert an unresolved question into an established conclusion. Empty issues and
no_flaw_established are valid when no material internal flaw is established.
""",
    "online_learning": smoke.PROMPTS["online_learning"] + """
The locked detector output is fallible, not a gold label. You may reflect on an
over-detection in it and propose a bounded future checking procedure without
rewriting that output. Ground the lesson in the actual paragraph, not merely in
agreement with the detector. Keep source-specific conclusions out of the rule.
Choose the operation before filling fields. With seeds only, refine is unavailable.
To specialize a seed with a genuinely new condition, use add, target_rule_id="",
and name the seed in base_rule_id. Never rename or rewrite an initial seed. Every
add/refine requires all four nonempty reusable fields, totaling at most 640
characters, and a nonempty novel_condition. Reinforce requires empty reusable
fields and an existing target. No patches remains valid. Do not invent a lesson
to make this experiment succeed; the same evidence and novelty audit still applies.
""",
    "online_audit": smoke.PROMPTS["online_audit"] + """
Do not assume the locked detector diagnosis is correct. For a proposed exclusion
condition, check whether the paragraph actually supports that distinction and
whether the rule still permits detection of genuine internal contradictions or
failed inferences. Reject procedures that demand external proof for every personal
report or turn open questions into factual conclusions. Structural validity does
not imply semantic validity; keep false/null judgments when warranted.
""",
}


def learning_schema(data):
    schema = memory.wire_schema("online_learning", data)
    template = schema["properties"]["patches"]["items"]
    rules = data["current_playbook"]
    ids = [r["id"] for r in rules]
    learned = [r["id"] for r in rules if not r["seed"]]
    branches = []
    for operation, targets in (("add", [""]), ("refine", learned), ("reinforce", ids)):
        if not targets:
            continue
        branch = copy.deepcopy(template)
        fields = branch["properties"]
        fields["operation"] = {"const": operation}
        fields["target_rule_id"] = {"enum": targets}
        for key in (*memory.FIELDS, "novel_condition"):
            fields[key] = ({"const": ""} if operation == "reinforce" else
                           {**fields[key], "minLength": 1})
        fields["reason"] = {**fields["reason"], "minLength": 1}
        fields["evidence"]["minItems"] = 1
        branches.append(branch)
    schema["properties"]["patches"]["items"] = {"anyOf": branches}
    Draft202012Validator.check_schema(schema)
    return schema


class Client(runtime.Client):
    def request(self, role, data):
        runtime.require(role in smoke.ROLES, "followup_has_no_scoring_calls")
        runtime.require(self.config["protocol"] == VERSION, "wrong_followup_protocol")
        request, _ = super().request(role, data)
        schema = learning_schema(data) if role == "online_learning" else request["format"]
        request["format"] = schema
        request["prompt"] = (PROMPTS[role] + "\nINPUT JSON:\n"
            + json.dumps(memory.prompt_data(role, data), ensure_ascii=False, separators=(",", ":"))
            + "\nOUTPUT JSON SCHEMA:\n" + json.dumps(schema, separators=(",", ":")))
        bound = (len(request["prompt"].encode()) + len(json.dumps(schema).encode())
                 + self.config["options"]["num_predict"] + 1024)
        runtime.require(bound <= self.config["options"]["num_ctx"], "followup_context_admission_no_truncation")
        return request, bound

    def call(self, key, role, data):
        value = super().call(key, role, data)
        if role == "online_learning":
            wire_value = {**value, "patches": [
                {k: v for k, v in p.items() if k != "id"} for p in value["patches"]]}
            Draft202012Validator(learning_schema(data)).validate(wire_value)
        return value
