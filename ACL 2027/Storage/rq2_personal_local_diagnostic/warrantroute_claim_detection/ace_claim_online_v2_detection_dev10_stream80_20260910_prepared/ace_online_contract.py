"""Versioned prequential flaw-detection memory; independent of frozen v6 runs."""

import copy
import json
import re

from jsonschema import Draft202012Validator, ValidationError

import ace_flaw_contract as base


VERSION = "ace-claim-online-v2-detection"
MEMORY_BYTES = 6000
TEXT, ANCHOR, obj, array = base.TEXT, base.ANCHOR, base.obj, base.array
FIELDS = base.RULE_FIELDS
PATCH = obj({
    "operation": {"enum": ["add", "refine", "reinforce"]},
    "target_rule_id": TEXT, "base_rule_id": TEXT,
    **{key: {"type": "string", "maxLength": 240} for key in FIELDS},
    "novel_condition": TEXT, "reason": TEXT, "evidence": array(ANCHOR),
    "reflection_indices": {"type": "array", "items": {"type": "integer", "minimum": 0,
                           "maximum": 3}, "minItems": 1, "maxItems": 4, "uniqueItems": True},
})
REFLECTION = obj({"kind": {"enum": ["miss", "overclaim", "useful_check", "unresolved", "no_change"]},
                  "lesson": TEXT, "evidence": array(ANCHOR)})
LEARNING = obj({"reflection": array(REFLECTION, 4), "patches": array(PATCH, 2)})
CHECK = obj({"applicable": base.TRI,
             "outcome": {"enum": ["flaw_supported", "no_flaw_supported", "unresolved", "not_applicable"]},
             "issue_indices": {"type": "array", "items": {"type": "integer", "minimum": 0,
                               "maximum": 7}, "maxItems": 8, "uniqueItems": True},
             "evidence": array(ANCHOR), "reason": TEXT})
PROMPTS = {
    **base.PROMPTS,
    "online_detector": base.COMMON + """
In ONE response diagnose, integrate, and check material flaws against the full
original evidence. Do not rewrite the claim. An unsupported claim may establish
a flaw: do not discard a supported flaw merely because the claim is unsupported.
Use supplied Playbook rules as fallible checking procedures, never as answers.
Return the review and rule_checks keyed by EVERY supplied rule ID. A rule check
records applicability, outcome, exact evidence, reason, and zero-based issue
indices in your review. Not applicable means no linked issue and no effect.
A supported flaw check must link its issue. A missing-warrant issue may explain
whole-packet absence instead of inventing an evidence quote. Do not claim that
mentioning a rule proves it improved the diagnosis. No model-generated rule is
evidence that a flaw exists. Do not force a positive diagnosis.
Every definite material flaw asserted in your rationale must also appear in
review.issues with its correct category, target, evidence, mechanism and
consequence. An empty issues array reports no established flaw, regardless of
what the rationale says. Keep genuinely unresolved concerns in unresolved.
""",
    "online_learning": base.COMMON + """
The CURRENT prediction is immutable. You are a combined Reflector and Curator.
Reflect on this claim, full evidence, locked diagnosis, rule checks and mechanical
integrity findings. No judge score, reference inventory, expected label or future
sample is provided. Do not infer hidden labels or require a reference issue.
Identify grounded checking lessons, including defensible negative decisions and
overclaims. Then propose at most TWO reusable incremental deltas. Each delta
links zero-based reflection_indices, exact evidence, and a specific reason.
For add: target_rule_id is empty; base_rule_id identifies the rule specialized
(or empty for a new mechanism). State the NEW concrete trigger or boundary in
novel_condition. The four reusable fields together must be at most 640 characters.
For refine: name an existing NON-SEED target; preserve its sound conditions and
explain the new boundary. Seeds are immutable. For reinforce: name an existing
rule, leave the four reusable fields and novel_condition empty, and provide
evidence that it was useful in this case. Reinforcement is not a new rule.
Do not paraphrase a general seed and call that learning. For example, a reusable
check of quantifier scope must state which scope mismatch to test and when a
limited claim remains defensible; "check the warrant" adds nothing to the seed.
Do not copy packet IDs, source IDs, quotations, case-specific conclusions or
answers into reusable fields. Put provenance only in evidence and reflection.
Empty patches are legitimate. Never force an update or a favorable diagnosis.
""",
    "online_audit": base.COMMON + """
Audit each proposed memory delta separately, against the current task, grounded
reflection and current playbook. Return edits keyed by supplied patch IDs. For
each of the six criteria return true/false/null, a reason and exact evidence.
grounded_lesson requires more than an exact quotation or agreement with the
locked prediction. The proposed procedure must actually follow from the case.
For add/refine, no_duplicate_or_contradiction requires a substantive new trigger,
check or countercondition beyond the named base and retained rules, not a seed
paraphrase. For reinforce, this criterion permits evidence-backed support for
the unchanged named rule without duplicating its content. Other criteria still
apply. Uncertainty withholds only that delta, not unrelated valid siblings.
This is a fallible same-model audit, not independent proof or a quality score.
""",
}


def wire_schema(role, data):
    if role == "online_detector":
        review = copy.deepcopy(base.REVIEW)
        review["properties"]["issues"]["items"] = base.without_id(base.ISSUE)
        schema = obj({"review": review, "rule_checks": obj({r["id"]: {"$ref": "#/$defs/rule_check"} for r in data["playbook"]})})
        schema["$defs"] = {"rule_check": CHECK}
        return schema
    if role == "online_learning":
        schema = copy.deepcopy(LEARNING)
        patch = schema["properties"]["patches"]["items"]["properties"]
        ids = [r["id"] for r in data["current_playbook"]]
        patch["target_rule_id"] = {"enum": ["", *ids]}
        patch["base_rule_id"] = {"enum": ["", *ids]}
        return schema
    if role == "online_audit":
        return base.wire_schema("patch_audit", data)
    return base.wire_schema(role, data)


def decode_wire(role, value, data):
    if not role.startswith("online_"):
        return base.decode_wire(role, value, data)
    Draft202012Validator(wire_schema(role, data)).validate(value)
    value = copy.deepcopy(value)
    if role == "online_detector":
        value["review"]["issues"] = [{**i, "id": f"issue_{n}"}
                                     for n, i in enumerate(value["review"]["issues"], 1)]
    elif role == "online_learning":
        value["patches"] = [{**p, "id": f"patch_{n}"} for n, p in enumerate(value["patches"], 1)]
    elif role == "online_audit":
        value = {"edits": [{"patch_id": key, **edit} for key, edit in value["edits"].items()]}
        Draft202012Validator(base.AUDIT).validate(value)
    return value


def seed_state():
    return {"revision": 0, "rules": copy.deepcopy(base.SEED), "support": {}}


def content_hash(state):
    return base.digest(base.visible_memory(state["rules"]))


def retrieve(state, task):
    """Keep four learned slots, including deterministic recent-rule fallback."""
    words = lambda s: set(re.findall(r"[^\W_]+", s.casefold()))
    query = words(task["claim"] + " " + " ".join(e["text"] for e in task["evidence"]))
    learned = [r for r in state["rules"] if not r["seed"]]
    learned.sort(key=lambda r: (-len(query & words(" ".join(r[k] for k in FIELDS))),
                               -r.get("last_changed_revision", 0), r["id"]))
    return base.visible_memory([r for r in state["rules"] if r["seed"]] + learned[:4])


def check_detection(value, task, retrieved):
    checks = base.check_review(value["review"], task)
    checks["rule_integrity_findings"] = []
    base.require(set(value["rule_checks"]) == {r["id"] for r in retrieved}, "rule_check_coverage")
    issue_n = len(value["review"]["issues"])
    for key, check in value["rule_checks"].items():
        Draft202012Validator(CHECK).validate(check)
        base.require(check["reason"].strip(), "empty_rule_check_reason")
        _, errors = base.anchors_checked(check["evidence"], task)
        findings = [{"rule_id": key, **e} for e in errors]
        indices = check["issue_indices"]
        if any(i >= issue_n for i in indices):
            findings.append({"rule_id": key, "kind": "rule_issue_link_out_of_range"})
        if ((check["outcome"] == "flaw_supported" and not indices)
                or (check["outcome"] == "not_applicable" and (indices or check["applicable"] is not False))
                or (check["applicable"] is False and check["outcome"] != "not_applicable")):
            findings.append({"rule_id": key, "kind": "rule_check_contradiction"})
        checks["rule_integrity_findings"].extend(findings)
    return checks


def learning_input(packet, locked, state):
    # Explicit allowlist: evaluator/reference outputs and future packets cannot enter this payload.
    return {"task": packet["task"], "locked_prediction": locked["review"],
            "rule_checks": locked["rule_checks"], "integrity_findings": [
                *locked["checks"]["integrity_findings"], *locked["checks"].get("rule_integrity_findings", [])],
            "current_playbook": base.visible_memory(state["rules"])}


def normalized(rule):
    return tuple(" ".join(rule[k].casefold().split()) for k in FIELDS)


def validate_patch(patch, learning, packet, state):
    Draft202012Validator(PATCH).validate({k: v for k, v in patch.items() if k != "id"})
    base.require(patch["reason"].strip(), "missing_patch_reason")
    _, errors = base.anchors_checked(patch["evidence"], packet["task"])
    base.require(patch["evidence"] and not errors, "invalid_patch_evidence")
    for index in patch["reflection_indices"]:
        base.require(index < len(learning["reflection"]), "invalid_reflection_link")
        reflection = learning["reflection"][index]
        Draft202012Validator(REFLECTION).validate(reflection)
        _, errors = base.anchors_checked(reflection["evidence"], packet["task"])
        base.require(reflection["lesson"].strip() and reflection["evidence"] and not errors,
                     "ungrounded_reflection")
    rules = {r["id"]: r for r in state["rules"]}
    operation, target = patch["operation"], patch["target_rule_id"]
    base.require(not patch["base_rule_id"] or patch["base_rule_id"] in rules, "missing_base_rule")
    fields = {k: patch[k].strip() for k in FIELDS}
    if operation == "reinforce":
        base.require(target in rules and not any(fields.values()) and not patch["novel_condition"].strip(),
                     "reinforce_must_not_change_content")
        return fields
    base.require(all(fields.values()) and sum(map(len, fields.values())) <= 640, "rule_text_budget")
    base.require(patch["novel_condition"].strip(), "missing_novel_condition")
    if operation == "add":
        base.require(not target, "add_target_not_empty")
    else:
        base.require(target in rules and not rules[target]["seed"], "seed_or_missing_rule_refinement")
    text = " ".join(fields.values()).casefold()
    forbidden = [packet["packet_id"], *packet["source_ids"], *(e["excerpt_id"] for e in packet["task"]["evidence"])]
    base.require(not any(str(i).casefold() in text for i in forbidden if i), "identifier_leakage")
    text = " ".join(text.split())
    for source in packet["task"]["evidence"]:
        words = source["text"].casefold().split()
        base.require(not any(" ".join(words[n:n+8]) in text for n in range(max(0, len(words)-7))),
                     "source_quote_leakage")
    return fields


def eligible_patches(learning, packet, state):
    """Reject individual malformed edits without discarding valid siblings."""
    accepted, receipts = [], []
    ids = [p.get("id") for p in learning["patches"]]
    base.require(all(ids) and len(ids) == len(set(ids)), "duplicate_patch_identity")
    for patch in learning["patches"]:
        try:
            validate_patch(patch, learning, packet, state)
        except (ValueError, KeyError, TypeError, IndexError, ValidationError) as exc:
            receipts.append({"patch_id": patch["id"], "outcome": "withheld_integrity", "reason": str(exc)})
        else:
            # Do not send exact duplicate content as a novel rule to the auditor.
            duplicate = next((r for r in state["rules"] if normalized(r) == normalized(patch)), None)
            if patch["operation"] != "reinforce" and duplicate:
                receipts.append({"patch_id": patch["id"], "outcome": "duplicate_noop",
                                 "rule_id": duplicate["id"], "reason": "Explicit grounded reinforcement is required."})
            else:
                accepted.append(patch)
    return {"reflection": learning["reflection"], "patches": accepted}, receipts


def apply_audited(state, learning, audit, packet):
    """One atomic delta result, with per-edit admission and unique-case support."""
    Draft202012Validator(base.AUDIT).validate(audit)
    ids = [e["patch_id"] for e in audit["edits"]]
    base.require(len(ids) == len(set(ids)) and set(ids) == {p["id"] for p in learning["patches"]},
                 "patch_audit_coverage")
    edits = {e["patch_id"]: e for e in audit["edits"]}
    updated, receipts, touched = copy.deepcopy(state), [], set()
    case_key = base.digest([packet["task"]["claim"], sorted(e["text"] for e in packet["task"]["evidence"])])
    for patch in learning["patches"]:
        receipt = {"patch_id": patch["id"]}
        before_patch = copy.deepcopy(updated)
        try:
            fields = validate_patch(patch, learning, packet, updated)
            edit = edits[patch["id"]]
            _, errors = base.anchors_checked(edit["evidence"], packet["task"])
            base.require(not errors and edit["evidence"] and edit["reason"].strip()
                         and all(edit[k] is True for k in base.AUDIT_CRITERIA), "semantic_audit_not_approved")
            target = patch["target_rule_id"]
            if patch["operation"] == "add":
                base.require(not any(normalized(r) == normalized(fields) for r in updated["rules"]), "duplicate_noop")
                base.require(len(updated["rules"]) < 40, "memory_capacity")
                target = "learned-" + base.digest(fields)[:16]
            base.require(target not in touched, "same_rule_twice_in_batch")
            if patch["operation"] == "refine":
                base.require(not any(normalized(r) == normalized(fields) for r in updated["rules"]), "duplicate_noop")
            if patch["operation"] != "reinforce":
                previous = next((r for r in updated["rules"] if r["id"] == target), None)
                rule = {"id": target, "version": previous["version"] + 1 if previous else 1, "seed": False,
                        **fields, "support_packets": list(previous["support_packets"]) if previous else [],
                        "support_sources": list(previous["support_sources"]) if previous else [],
                        "last_changed_revision": state["revision"] + 1,
                        "base_rule_id": patch["base_rule_id"], "novel_condition": patch["novel_condition"]}
                updated["rules"] = [r for r in updated["rules"] if r["id"] != target] + [rule]
                base.require(len(json.dumps(base.visible_memory(updated["rules"]), ensure_ascii=False,
                                            separators=(",", ":")).encode()) <= MEMORY_BYTES, "memory_context_capacity")
            support = updated["support"].get(target, {"case_keys": [], "packet_ids": [], "source_ids": []})
            fresh = case_key not in support["case_keys"]
            if fresh:
                support = {"case_keys": sorted([*support["case_keys"], case_key]),
                           "packet_ids": sorted(set(support["packet_ids"]) | {packet["packet_id"]}),
                           "source_ids": sorted(set(support["source_ids"]) | set(packet["source_ids"]))}
                updated["support"][target] = support
            for rule in updated["rules"]:
                if rule["id"] == target and not rule["seed"]:
                    rule["support_packets"], rule["support_sources"] = support["packet_ids"], support["source_ids"]
            outcome = {"add": "added", "refine": "refined", "reinforce": "reinforced" if fresh else "repeated_support_noop"}[patch["operation"]]
            receipt.update(outcome=outcome, rule_id=target, novel_case_support=fresh)
            touched.add(target)
        except (ValueError, KeyError, TypeError, IndexError, ValidationError) as exc:
            updated = before_patch
            receipt.update(outcome="withheld", reason=str(exc))
        receipts.append(receipt)
    base.require([r for r in updated["rules"] if r["seed"]] == base.SEED, "seed_mutation")
    if updated != state:
        updated["revision"] = state["revision"] + 1
    return updated, receipts
