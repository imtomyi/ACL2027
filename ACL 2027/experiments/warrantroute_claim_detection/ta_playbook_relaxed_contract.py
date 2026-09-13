"""V2: admit useful procedural elaborations without relaxing grounding or safety."""

import json

from jsonschema import Draft202012Validator

import ta_playbook_contract as strict

memory, base = strict.memory, strict.base
VERSION = "ta-artifact-playbook-operational-specificity-v2"
POLICY = "Useful operational detail is sufficient; a new flaw mechanism is not required."
HARD_CRITERIA = tuple(k for k in base.AUDIT_CRITERIA if k != "no_duplicate_or_contradiction") + (
    "no_contradiction", "operationally_useful")
SOFT_CRITERION = "distinct_contribution"
AUDIT_EDIT = base.obj({"patch_id": base.TEXT, **{k: base.TRI for k in (*HARD_CRITERIA, SOFT_CRITERION)},
    "reason": base.TEXT, "evidence": base.array(base.ANCHOR), "artifact_evidence": base.array(strict.ARTIFACT_ANCHOR, 2)})
KEYS = {"codes": "code_id", "subthemes": "subtheme_id", "themes": "theme_id", "source_notes": "source_record_id"}
prefix, rest = strict.COMMON.split("Keep target quotations and original-source quotations separate.", 1)
_, tail = rest.split("\nA material flaw", 1)
COMMON = prefix + """Keep target quotations and original-source quotations separate.
Source anchors use excerpt_id and an exact quote from that source. Artifact
anchors use target_slot and quote. Select a target_slot from the supplied schema;
it binds one real collection/unit/field. Quote an exact substring of that field,
or one exact member of a linked-ID list. Evidence-field quotes can locate an
assertion stored in the artifact even when it is NOT a valid source quotation.
Never switch a source, field or unit merely to obtain a quote match. An omission
must locate an existing unit whose missing support or qualification matters.
""" + "\nA material flaw" + tail
PROMPTS = {
    "online_detector": strict.PROMPTS["online_detector"],
    "online_learning": COMMON + """
You are the combined Reflector/Curator. The current review is locked. Examine
its reasoning and rule checks against the source-to-TA relation, including
negative decisions and mechanical findings. Consider evidence_to_code,
false_allegation_prevention, flaw_type_distinction, and
theme_scope_and_counterevidence. Label each reflection's opportunity. Lessons
need artifact and original-source anchors, not merely agreement with the review.

Propose zero to two reusable procedural deltas. A useful concrete specialization
of an existing rule is welcome: a new flaw class or wholly new mechanism is NOT
required. Do not add a bare paraphrase, duplicate, participant fact or case answer.
Use earlier same-artifact outcomes to avoid repeating invalid proposals. They
are fallible feedback, not gold. No scores, future items or external inspection
findings may be used. Never force a flaw or an addition to increase counts.

For add, the output has NO target_rule_id; the controller binds it to empty.
base_rule_id names a related rule, or empty for an unrelated check. For refine,
target_rule_id must name a non-seed rule. For reinforce, name an existing rule
and provide evidence/reason without rewriting its four procedural fields.
Each proposal names reflection_indices and exact source/artifact evidence.

For add/refine define these fields as plain English sentences:
applicability: an observable situation in which a reviewer should use the rule,
NOT true/false or a quality rating.
detection_check: the concrete comparison or action the reviewer should perform,
NOT a category label such as scope.
evidence_requirement: what evidence must be located to justify the finding.
countercondition: when that finding would be unwarranted, preserving uncertainty.
operational_detail: the useful concrete trigger, comparison, step or exception
added to the existing guidance; it need not be a new mechanism.
The four procedural fields together must stay within 640 characters. Keep IDs,
quotations, study findings and case-specific labels out of those fields. Put
provenance in the evidence fields. Empty patches are legitimate.
""",
    "online_audit": COMMON + """
Audit each proposed delta against sources, artifact, reflection and current
Playbook. Return one edit keyed by each patch ID, with exact source/artifact
evidence and a concise reason. The required safety/quality decisions are:
grounded_lesson: the procedure follows from the demonstrated source-to-TA relation,
not only a quotation match or agreement with the detector.
reusable_not_memorized: useful on a future case, not a participant fact, code/theme
finding or an instruction to change this one analysis.
counterconditions_preserved: preserves legitimate alternatives, scope and uncertainty.
no_unsupported_domain_inference: introduces no invented domain or clinical premise.
no_contradiction: the procedure does not conflict with retained sound guidance.
operationally_useful: an actionable check rather than a label, a participant fact,
or cosmetic restatement. IMPORTANT: overlap with a seed or existing rule is
allowed when operational_detail supplies a useful checking step, trigger or
exception. Do NOT require a new mechanism or new flaw category.
In the canonical proposal input this detail is stored under novel_condition;
that legacy field name does not restore the old mechanism-novelty requirement.
no_leakage: no case answers, source text/identifiers, participant details or
held-out/evaluator information enter reusable rule text.

distinct_contribution is a separate descriptive novelty assessment. True means
clearly distinct guidance, false means overlapping/supporting guidance, and null
means novelty is uncertain. False/null on novelty alone does NOT withhold a
grounded, safe, operationally useful procedure. Do not let a novelty assessment
excuse a failed required check. Exact duplicates are rejected by code.

For reinforce, evidence-backed support for the unchanged rule is permitted but
is not a new rule. Return false for a failed condition, null for uncertainty.
Every required condition must be true for admission; novelty is not required.
This is a fallible same-model audit,
not validation of detection accuracy. A procedure added to a Playbook is not
proof that any allegation is correct or that performance improved.
""",
}


def slots(artifact):
    result = {}
    for collection, key in KEYS.items():
        for unit in artifact.get(collection, []):
            uid = unit[key]
            for field, value in unit.items():
                usable = isinstance(value, str) and bool(value)
                usable |= isinstance(value, list) and any(isinstance(v, str) or
                    isinstance(v, dict) and isinstance(v.get("quote"), str) for v in value)
                if not usable or field == key:
                    continue
                name = f"{collection}/{uid}/{field}"
                base.require(name not in result, "ambiguous_artifact_slot")
                result[name] = {"collection": collection, "unit_id": uid, "field": field}
    base.require(result, "no_addressable_ta_slots")
    return result


def schema(role, data):
    if role == "online_detector":
        return strict.schema(role, data)
    result = strict.schema(role, data)
    anchor = base.obj({"target_slot": {"enum": list(slots(data["task"]["artifact"]))}, "quote": base.TEXT})

    def replace_anchors(node):
        if isinstance(node, dict):
            if set(node.get("properties", {})) == {"collection", "unit_id", "field", "quote"}:
                return {"$ref": "#/$defs/ta_anchor"}
            return {k: replace_anchors(v) for k, v in node.items()}
        if isinstance(node, list):
            return [replace_anchors(v) for v in node]
        return node

    result = replace_anchors(result)
    result.setdefault("$defs", {})["ta_anchor"] = anchor
    if role == "online_audit":
        for edit in result["properties"]["edits"]["properties"].values():
            edit["properties"].pop("no_duplicate_or_contradiction")
            edit["required"].remove("no_duplicate_or_contradiction")
            for field in ("no_contradiction", "operationally_useful", SOFT_CRITERION):
                edit["properties"][field] = base.TRI
                edit["required"].append(field)
    if role == "online_learning":
        properties = result["properties"]["patches"]["items"]["properties"]
        properties["operational_detail"] = properties.pop("novel_condition")
        for field in (*memory.FIELDS, "operational_detail"):
            properties[field] = {**properties[field], "minLength": 1}
        add = {k: v for k, v in properties.items() if k != "target_rule_id"}
        add["operation"] = {"enum": ["add"]}
        variants = [base.obj(add)]
        learned = [r["id"] for r in data["current_playbook"] if not r["seed"]]
        if learned:
            refine = {**properties, "operation": {"enum": ["refine"]}, "target_rule_id": {"enum": learned}}
            variants.append(base.obj(refine))
        reinforce = {k: v for k, v in properties.items() if k not in (*memory.FIELDS, "operational_detail", "base_rule_id")}
        reinforce.update(operation={"enum": ["reinforce"]}, target_rule_id={"enum": [r["id"] for r in data["current_playbook"]]})
        variants.append(base.obj(reinforce))
        # Complete disjoint objects avoid backend ambiguity around shared anyOf properties.
        result["properties"]["patches"]["items"] = {"anyOf": variants}
    Draft202012Validator.check_schema(result)
    return result


def decode(role, value, data):
    if role == "online_detector":
        return strict.decode(role, value, data)
    Draft202012Validator(schema(role, data)).validate(value)
    mapping = slots(data["task"]["artifact"])

    def expand(node):
        if isinstance(node, dict):
            if set(node) == {"target_slot", "quote"}:
                return {**mapping[node["target_slot"]], "quote": node["quote"]}
            return {k: expand(v) for k, v in node.items()}
        if isinstance(node, list):
            return [expand(v) for v in node]
        return node

    canonical = expand(value)
    if role == "online_audit":
        audit = {"edits": [{"patch_id": key, **edit} for key, edit in canonical["edits"].items()]}
        Draft202012Validator(base.obj({"edits": base.array(AUDIT_EDIT, 2)})).validate(audit)
        return audit
    if role == "online_learning":
        for patch in canonical["patches"]:
            if patch["operation"] == "add":
                patch["target_rule_id"] = ""
            if patch["operation"] == "reinforce":
                patch.update({k: "" for k in (*memory.FIELDS, "novel_condition", "base_rule_id")})
            else:
                patch["novel_condition"] = patch.pop("operational_detail")
    return strict.decode(role, canonical, data)


def request(config, role, data):
    if role == "online_detector":
        return strict.request(config, role, data)
    base.require(role in PROMPTS and config["paid_api_allowed"] is False
                 and config["base_url"] == "http://127.0.0.1:11434", "local_review_roles_only")
    wire = schema(role, data)
    allowed = {"task", "current_playbook", "locked_prediction", "rule_checks", "integrity_findings", "learning", "previous_learning"}
    payload = {k: data[k] for k in allowed if k in data}
    rendered_schema = json.dumps(wire, separators=(",", ":"))
    prompt = (PROMPTS[role] + "\nINPUT JSON:\n" + json.dumps(memory.prompt_data(role, payload),
        ensure_ascii=False, separators=(",", ":")) + "\nOUTPUT JSON SCHEMA:\n" + rendered_schema)
    bound = len(prompt.encode()) + len(rendered_schema.encode()) + config["options"]["num_predict"] + 1024
    base.require(bound <= config["options"]["num_ctx"], "ta_context_admission_no_truncation")
    return {"model": config["model"], "prompt": prompt, "format": wire, "stream": False,
            "keep_alive": "5m", "options": config["options"]}, bound


def eligible(value, packet, state):
    accepted, receipts = strict.eligible(value, packet, state)
    kept = []
    for patch in accepted["patches"]:
        placeholders = {"true", "false", "null", "none", "yes", "no", "scope", "check"}
        if patch["operation"] != "reinforce" and any(patch[k].strip().casefold() in placeholders for k in memory.FIELDS):
            receipts.append({"patch_id": patch["id"], "outcome": "withheld_integrity", "reason": "nonprocedural_placeholder_text"})
        else:
            kept.append(patch)
    return {**accepted, "patches": kept}, receipts


check_review = strict.check_review


def apply(state, learning, audit, packet):
    """Map passed V2 safety gates to the unchanged reducer; never rewrite raw audits."""
    Draft202012Validator(base.obj({"edits": base.array(AUDIT_EDIT, 2)})).validate(audit)
    by_id = {e["patch_id"]: e for e in audit["edits"]}
    base.require(len(by_id) == len(audit["edits"]) and set(by_id) == {p["id"] for p in learning["patches"]}, "audit_coverage")
    eligible_learning, receipts = eligible(learning, packet, state)
    patches, mapped = [], []
    for patch in eligible_learning["patches"]:
        edit = by_id[patch["id"]]
        failed = [k for k in HARD_CRITERIA if edit[k] is not True]
        if failed:
            receipts.append({"patch_id": patch["id"], "outcome": "withheld", "reason": "required_audit_condition_not_true",
                             "failed_criteria": failed})
            continue
        patches.append(patch)
        mapped.append({k: edit[k] for k in ("patch_id", "reason", "evidence", "artifact_evidence",
            *(k for k in base.AUDIT_CRITERIA if k != "no_duplicate_or_contradiction"))} |
            {"no_duplicate_or_contradiction": True})
    if patches:
        state, results = strict.apply(state, {**learning, "patches": patches}, {"edits": mapped}, packet)
        receipts += results
    for receipt in receipts:
        receipt.update(admission_policy=VERSION, distinct_contribution=by_id[receipt["patch_id"]][SOFT_CRITERION])
        if receipt["outcome"] in ("added", "refined"):
            receipt["admitted_without_established_novelty"] = receipt["distinct_contribution"] is not True
            receipt["reducer_adapter"] = "V2 no_contradiction and operationally_useful passed; exact-duplicate guard retained. Raw novelty verdict not changed."
    return state, receipts
