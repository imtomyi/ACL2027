"""Candidate-focused learning adapter; detector, auditor and admission stay frozen."""

import copy
import json

from jsonschema import Draft202012Validator

import paragraph_followup_contract as previous

memory, runtime, smoke = previous.memory, previous.runtime, previous.smoke
VERSION = "dreaddit-paragraph-proactive-learning-v1"
LENSES = ("flaw_detection", "false_positive_prevention", "category_disambiguation", "evidence_sufficiency")
PROMPTS = {
    **previous.PROMPTS,
    "online_learning": previous.PROMPTS["online_learning"] + """
ACTIVE CANDIDATE DISCOVERY
In this same response, examine exactly FOUR learning opportunities, in order:
0. flaw_detection: a concrete test of an asserted inference or inconsistency;
1. false_positive_prevention: a boundary that prevents a false allegation;
2. category_disambiguation: how to distinguish plausible flaw categories;
3. evidence_sufficiency: what textual anchors would support or defeat a concern.
Use one reflection entry per opportunity. Begin its lesson with the opportunity
name. Briefly state the observed condition, checking lesson, and whether a novel
delta is justified. Ground each entry in a short exact quote. Use no_change or
unresolved with a specific reason when the text yields no defensible new lesson.

Actively turn the strongest uncovered lessons into up to TWO distinct patches.
Useful negative-case procedures count: a paragraph need not contain a confirmed
flaw to teach a discriminating check. Do not stop at a generic reflection when
an observable, reusable condition is absent from the current Playbook. Prefer a
substantive add over merely reinforcing a broad seed, but refine a learned rule
when the lesson repairs its existing boundary instead of duplicating it.
Before submitting, compare each candidate with every retained rule and with its
sibling. Specify the new trigger or diagnostic step in novel_condition. Do not
split a single procedure into cosmetic variants to inflate the rule count.

Write applicability as an OBSERVABLE linguistic or inferential input condition,
never a detector verdict such as no_flaw_established. Write detection_check as
an action comparing actual statements, scope, attribution, timing or qualifiers.
Write evidence_requirement as the textual support needed to establish a flaw,
not the conclusion 'there is no inconsistency'. Write countercondition as a
general exception that preserves genuine flaw detection, not a detail from this
author's story. Keep all four fields compact: aim for 320-480 characters total,
never exceed the existing 640-character limit. Provenance stays only in quotes
and reasons, never in reusable fields. No special domain knowledge is assumed.

MULTI-EPOCH REFINEMENT
adaptation_context contains only this run's most recent completed exposure of
THIS paragraph, if any. These are fallible local learning decisions, not gold
labels. Use rejection reasons to fix the underlying deficiency before proposing
a materially revised candidate; do not repeat a rejected rule unchanged. If no
safe revision is supported, explore another of the four opportunities or report
no_change. Do not invent a flaw, evidence, rule or claimed improvement to obtain
an addition. A zero-patch response remains valid after this explicit search.
""",
}


def learning_schema(data):
    schema = previous.learning_schema(data)
    reflections = schema["properties"]["reflection"]
    reflections["minItems"] = reflections["maxItems"] = len(LENSES)
    fields = reflections["items"]["properties"]
    fields["lesson"] = {"type": "string", "minLength": 1, "maxLength": 360}
    fields["evidence"].update(minItems=1, maxItems=2)
    Draft202012Validator.check_schema(schema)
    return schema


def candidate_id(patch):
    # Content identity is stable across repeated queries; it does not certify novelty.
    fields = {key: " ".join(patch[key].casefold().split()) for key in memory.FIELDS}
    return "cand-" + runtime.digest({"operation": patch["operation"],
        "target_rule_id": patch["target_rule_id"], **fields})[:16]


def adaptation_context(run, key):
    jobs = runtime.read(run / "schedule.json")
    job_id = key.rsplit("/", 1)[0]
    index = next((n for n, job in enumerate(jobs) if job["id"] == job_id), None)
    runtime.require(index is not None, "learning_job_not_in_frozen_schedule")
    job = jobs[index]
    context = {"epoch": job["epoch"], "opportunities": list(LENSES),
        "history_scope": "Latest earlier committed exposure of this paragraph in this run only; no gold or baseline outputs.",
        "previous_exposure": None}
    for prior in reversed(jobs[:index]):
        if prior["packet_id"] != job["packet_id"]:
            continue
        path = run / "results" / prior["id"] / "result.json"
        runtime.require(path.exists(), "missing_prior_exposure")
        record = runtime.load_record(path)
        value = record["value"]
        for name, expected in value["artifacts"].items():
            runtime.require(runtime.file_hash(run / name) == expected, "prior_learning_artifact_changed")
        learning = value["learning"].get("value", {})
        proposal = learning.get("proposal", {})
        audits = {item["patch_id"]: item for item in (learning.get("audit") or {}).get("edits", [])}
        receipts = {item["patch_id"]: item for item in learning.get("receipts", [])}
        candidates = []
        for patch in proposal.get("patches", []):
            audit = audits.get(patch["id"], {})
            candidates.append({"candidate_id": candidate_id(patch),
                **{name: patch[name] for name in ("operation", "target_rule_id", *memory.FIELDS, "novel_condition")},
                "receipt": receipts.get(patch["id"]), "audit_reason": audit.get("reason"),
                "audit_not_true": [name for name in memory.base.AUDIT_CRITERIA if audit and audit.get(name) is not True]})
        context["previous_exposure"] = {"epoch": prior["epoch"], "record_sha256": record["sha256"],
            "learning_status": value["learning"]["status"],
            "reflection": proposal.get("reflection", []), "candidates": candidates}
        break
    return context


class Client(previous.Client):
    def request(self, role, data):
        runtime.require(role in smoke.ROLES, "proactive_has_no_scoring_calls")
        runtime.require(self.config["protocol"] == VERSION, "wrong_proactive_protocol")
        request, _ = runtime.Client.request(self, role, data)
        schema = learning_schema(data) if role == "online_learning" else request["format"]
        request["format"] = schema
        request["prompt"] = (PROMPTS[role] + "\nINPUT JSON:\n"
            + json.dumps(memory.prompt_data(role, data), ensure_ascii=False, separators=(",", ":"))
            + "\nOUTPUT JSON SCHEMA:\n" + json.dumps(schema, separators=(",", ":")))
        bound = (len(request["prompt"].encode()) + len(json.dumps(schema).encode())
                 + self.config["options"]["num_predict"] + 1024)
        runtime.require(bound <= self.config["options"]["num_ctx"], "proactive_context_admission_no_truncation")
        return request, bound

    def call(self, key, role, data):
        if role == "online_learning":
            data = {**data, "adaptation_context": adaptation_context(self.run, key)}
        value = super().call(key, role, data)
        if role == "online_learning":
            wire = copy.deepcopy(value)
            for patch in wire["patches"]:
                patch.pop("id", None)
            Draft202012Validator(learning_schema(data)).validate(wire)
        return value
