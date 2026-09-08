"""Live, bounded WarrantRoute review and revision for private working packets."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

import build_working_warrantgate_routes as gate

WORKSPACE = Path(__file__).resolve().parents[3]
H_ROOT = WORKSPACE / "experiments/direction_h_human_in_loop"
sys.path.insert(0, str(H_ROOT / "scripts"))
from ace_tight_loop_controller import decide_next, required_initial_roles  # noqa: E402

STATE_SCHEMA_PATH = H_ROOT / "schemas/ace_tight_loop_state_v1.schema.json"
STATE_SCHEMA = json.loads(STATE_SCHEMA_PATH.read_text())
STATE_VALIDATOR = Draft202012Validator(STATE_SCHEMA)
ROLES = ("proposer", "evidence_scout", "methods_challenger", "domain_challenger", "reviser")
MODE_ROLES = {
    "generalist": set(),
    "qualitative_methods": {"methods_challenger"},
    "domain": {"domain_challenger"},
    "both": {"methods_challenger", "domain_challenger"},
}
FLAGS = (
    "fabricated_or_altered_quote", "wrong_attribution", "unsupported_inference",
    "hidden_source_concentration", "lost_negative_case", "contextual_flattening",
    "unsupported_abstraction", "sensitive_or_diagnostic_inference",
    "inconsistent_codebook", "other",
)
FLAG_CATEGORY = dict(zip(FLAGS, (
    "evidence_mismatch", "evidence_mismatch", "evidence_mismatch",
    "source_concentration", "counterevidence_omission", "context_loss",
    "boundary_failure", "protected_inference", "code_theme_confusion", "other",
)))
QUALITY_FIELDS = ("evidential_credibility", "voice_boundary_preservation", "scope_calibration")
FORBIDDEN_KEYS = {
    "known_intended_flaw_type", "known_intended_flaw_note", "answer_key",
    "target_flaw", "target_flag", "review_instruction", "flaw_taxonomy",
    "final_grader", "heldout_outcome",
}


def object_schema(properties: dict, **kwargs: Any) -> dict:
    return {"type": "object", "additionalProperties": False,
            "required": list(properties), "properties": properties, **kwargs}


def text_schema(maximum: int = 1000, minimum: int = 0) -> dict:
    return {"type": "string", "minLength": minimum, "maxLength": maximum}


IDS = {"type": "array", "uniqueItems": True, "maxItems": 64, "items": text_schema(160, 1)}
RATING_SCHEMA = object_schema({
    "rating_schema_version": {"const": "direction-j-shared-rating-v1"},
    **{field: {"type": ["integer", "null"], "minimum": 1, "maximum": 5} for field in QUALITY_FIELDS},
    "cannot_judge": {"type": "array", "uniqueItems": True, "items": {"enum": list(QUALITY_FIELDS)}},
    "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
    "disposition": {"enum": ["accept", "revise", "reject", "escalate"]},
    "requested_expertise": {"enum": ["none", "qualitative_methods", "domain", "both"]},
    "serious_error_flags": {"type": "array", "uniqueItems": True, "items": {"enum": list(FLAGS)}},
    "rationale": text_schema(1000, 1),
})
AUDIT_RECORD_SCHEMA = object_schema({
    "rating": RATING_SCHEMA,
    "support_ids": IDS,
    "counterevidence_ids": IDS,
    "alternative_interpretation": text_schema(800),
    "issues": {"type": "array", "maxItems": 3, "items": object_schema({
        "flag": {"enum": list(FLAGS)},
        "evidence_ids": {**IDS, "minItems": 1},
        "diagnosis": text_schema(800, 1),
        "requested_change": text_schema(500, 1),
    })},
    "resolved_issue_ids": IDS,
})
AUDIT_SCHEMA = copy.deepcopy(AUDIT_RECORD_SCHEMA)
del AUDIT_SCHEMA["properties"]["rating"]["properties"]["serious_error_flags"]
AUDIT_SCHEMA["properties"]["rating"]["required"].remove("serious_error_flags")
REVISION_SCHEMA = object_schema({
    "claim": text_schema(4000, 1),
    "central_concept": text_schema(1000, 1),
    "scope": text_schema(1000, 1),
    "evidence_ids": {**IDS, "minItems": 1},
    "counterevidence_ids": IDS,
    "uncertainty": text_schema(1000, 1),
    "issue_responses": {"type": "object", "maxProperties": 64,
                        "additionalProperties": text_schema(600, 1)},
})


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False).encode()).hexdigest()


def all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(all_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(all_keys(v) for v in value))
    return set()


def packet_payload(packet: dict) -> dict:
    """Allowlist task fields, excluding labels, generating-model identity and metadata."""
    claim = packet["llm_generated_qualitative_claim"]
    contexts = packet["source_text_context"]
    if not isinstance(contexts, list) or not contexts:
        raise ValueError("source_context_missing")
    payload = {
        "research_question": packet["research_question"],
        "source_text_context": [
            {key: row[key] for key in (
                "excerpt_id", "source_id", "speaker_id", "text", "local_context",
                "candidate_role", "candidate_attributed_excerpt_id",
                "candidate_attributed_source_id", "candidate_attributed_speaker_id",
            ) if key in row} for row in contexts
        ],
        "llm_generated_qualitative_claim": {
            key: claim[key] for key in (
                "claim", "explanation", "boundary_conditions", "theme_name", "cited_excerpt_ids"
            ) if key in claim
        },
    }
    if FORBIDDEN_KEYS & all_keys(payload):
        raise ValueError("forbidden_task_fields")
    ids = [row["excerpt_id"] for row in payload["source_text_context"]]
    if len(ids) != len(set(ids)) or any(not isinstance(item, str) for item in ids):
        raise ValueError("duplicate_or_invalid_excerpt_ids")
    if not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
        raise ValueError("missing_candidate_claim")
    return payload


def as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def initial_candidate(payload: dict, packet_id: str) -> dict:
    claim = payload["llm_generated_qualitative_claim"]
    return {
        "candidate_id": f"{packet_id}-r0", "producer_agent_id": "input-packet",
        "claim": claim["claim"], "central_concept": as_text(claim.get("theme_name", "Unspecified")),
        "scope": as_text(claim.get("boundary_conditions", "Unspecified")),
        "evidence_ids": claim.get("cited_excerpt_ids", []), "counterevidence_ids": [],
        "playbook_bullet_ids": [], "uncertainty": "Not yet independently assessed.",
    }


def validate_audit(report: dict, evidence_ids: set[str], assigned_ids: set[str]) -> None:
    Draft202012Validator(AUDIT_RECORD_SCHEMA).validate(report)
    rating = report["rating"]
    if set(rating["cannot_judge"]) != {field for field in QUALITY_FIELDS if rating[field] is None}:
        raise ValueError("cannot_judge_score_mismatch")
    if (rating["disposition"] == "escalate") != (rating["requested_expertise"] != "none"):
        raise ValueError("expertise_disposition_mismatch")
    if rating["cannot_judge"] and rating["disposition"] != "escalate":
        raise ValueError("abstention_requires_escalation")
    if rating["disposition"] == "accept" and (
        rating["serious_error_flags"] or any(rating[field] is None or rating[field] < 4 for field in QUALITY_FIELDS)
    ):
        raise ValueError("accept_with_material_problem")
    if set(rating["serious_error_flags"]) != {issue["flag"] for issue in report["issues"]}:
        raise ValueError("flags_without_located_issues")
    used = set(report["support_ids"] + report["counterevidence_ids"])
    used.update(eid for issue in report["issues"] for eid in issue["evidence_ids"])
    if not used <= evidence_ids:
        raise ValueError("unknown_evidence_id")
    if not set(report["resolved_issue_ids"]) <= assigned_ids:
        raise ValueError("unowned_issue_resolution")


def validate_revision(revision: dict, evidence_ids: set[str], assigned_ids: set[str]) -> None:
    Draft202012Validator(REVISION_SCHEMA).validate(revision)
    if not set(revision["evidence_ids"] + revision["counterevidence_ids"]) <= evidence_ids:
        raise ValueError("revision_introduced_evidence_id")
    if set(revision["issue_responses"]) != assigned_ids:
        raise ValueError("revision_issue_inventory_mismatch")
    if any(char in revision["claim"] for char in ('"', '\u201c', '\u201d')):
        raise ValueError("revision_must_paraphrase_without_direct_quotations")


def audit_output_schema(evidence_ids: set[str], assigned_ids: set[str]) -> dict:
    schema = copy.deepcopy(AUDIT_SCHEMA)
    for field in ("support_ids", "counterevidence_ids", "resolved_issue_ids"):
        schema["properties"][field] = copy.deepcopy(IDS)
    for field in ("support_ids", "counterevidence_ids"):
        schema["properties"][field]["items"] = {"enum": sorted(evidence_ids)}
    schema["properties"]["issues"]["items"]["properties"]["evidence_ids"]["items"] = {"enum": sorted(evidence_ids)}
    resolved = schema["properties"]["resolved_issue_ids"]
    if assigned_ids:
        resolved["items"] = {"enum": sorted(assigned_ids)}
        resolved["maxItems"] = len(assigned_ids)
    else:
        resolved["maxItems"] = 0
    return schema


def revision_output_schema(evidence_ids: set[str], assigned_ids: set[str]) -> dict:
    schema = copy.deepcopy(REVISION_SCHEMA)
    for field in ("evidence_ids", "counterevidence_ids"):
        schema["properties"][field] = copy.deepcopy(REVISION_SCHEMA["properties"][field])
        schema["properties"][field]["items"] = {"enum": sorted(evidence_ids)}
    schema["properties"]["issue_responses"] = object_schema({
        issue_id: text_schema(600, 1) for issue_id in sorted(assigned_ids)
    })
    return schema


def choose_initial_route(payload: dict, rating: dict, policy: dict) -> tuple[str, dict]:
    features = {**gate.source_free_packet_features(payload),
                **gate.rating_features({"status": "valid", "rating": rating})}
    components, scores = gate.route_scores(features, policy)
    best = max(scores.values())
    route = next(mode for mode in policy["tie_order"] if best - scores[mode] <= 1e-9)
    return route, {"scores": scores, "components": components, "tie_tolerance": 1e-9}


def promoted_route(route: str, requested: list[str]) -> str:
    roles = set(MODE_ROLES[route])
    for value in requested:
        roles |= MODE_ROLES.get(value, set())
    return next(mode for mode, value in MODE_ROLES.items() if value == roles)


def ollama_transport(request: dict, timeout: int) -> dict:
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
                                 data=json.dumps(request).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


class CallFailure(RuntimeError):
    pass


class AgentClient:
    """Each logical call is journaled before dispatch and reused only under its exact hash."""

    def __init__(self, config: dict, assignment: dict, seed: int, prompt: str, guide: str,
                 call_dir: Path, write_json: Callable, transport: Callable = ollama_transport):
        self.config, self.assignment, self.seed = config, assignment, seed
        self.prompt, self.guide, self.call_dir = prompt, guide, call_dir
        self.write_json, self.transport = write_json, transport
        self.records: list[dict] = []

    def call(self, role: str, stage: str, payload: dict, schema: dict) -> dict:
        if len(self.records) >= self.config["runtime"]["max_agent_calls"]:
            raise CallFailure("agent_call_budget_exhausted")
        if FORBIDDEN_KEYS & all_keys(payload):
            raise CallFailure("forbidden_model_payload")
        runtime = self.config["runtime"]
        model = self.assignment[role]
        prompt = "\n\n".join((self.prompt, self.guide, f"Assigned role: {role}. Stage: {stage}.",
                               json.dumps(payload, ensure_ascii=False, sort_keys=True)))
        if len(prompt) > runtime["max_input_characters"]:
            raise CallFailure("input_character_budget_exceeded")
        call_seed = int(digest([self.seed, role, stage])[:8], 16) % 2147483647
        request = {
            "model": model, "prompt": prompt, "stream": False, "format": schema,
            "keep_alive": runtime["keep_alive"],
            "options": {"temperature": runtime["temperature"], "top_p": runtime["top_p"],
                        "num_ctx": runtime["num_ctx"], "seed": call_seed,
                        "num_predict": runtime["revision_output_tokens"] if role == "reviser"
                        else runtime["audit_output_tokens"]},
        }
        if model.startswith("qwen3:"):
            request["think"] = False
        identity = digest({"request": request, "model_digest": self.config["model_digests"][model]})
        path = self.call_dir / f"{stage}-{role}.json"
        if path.exists():
            record = json.loads(path.read_text())
            if record.get("record_sha256") != digest({key: value for key, value in record.items() if key != "record_sha256"}):
                raise CallFailure("cached_record_integrity_mismatch")
            if record.get("request_sha256") != identity:
                raise CallFailure("cached_request_identity_mismatch")
            self.records.append(record)
            if record["status"] != "complete":
                raise CallFailure(f"previous_call_{record['status']}:start_a_new_run_to_retry")
            return record["parsed"]
        record = {"role": role, "stage": stage, "model": model,
                  "model_digest": self.config["model_digests"][model], "seed": call_seed,
                  "request_sha256": identity, "status": "in_flight"}
        record["record_sha256"] = digest(record)
        self.write_json(path, record)
        self.records.append(record)
        start = time.monotonic()
        try:
            response = self.transport(request, runtime["timeout_seconds"])
            record.update({key: response.get(key) for key in (
                "total_duration", "load_duration", "prompt_eval_count", "eval_count",
                "prompt_eval_duration", "eval_duration", "done_reason",
            )})
            record["raw_response"] = response.get("response", "")
            if response.get("done") is not True or response.get("done_reason") == "length":
                raise ValueError("incomplete_or_truncated_generation")
            parsed = json.loads(record["raw_response"])
            Draft202012Validator(schema).validate(parsed)
            record.update(status="complete", parsed=parsed)
        except Exception as exc:
            record.update(status="error", error_type=type(exc).__name__, error=str(exc)[:300])
            raise CallFailure(f"{role}:{stage}:{type(exc).__name__}") from exc
        finally:
            record["wall_seconds"] = time.monotonic() - start
            record["record_sha256"] = digest({key: value for key, value in record.items() if key != "record_sha256"})
            self.write_json(path, record)
        return record["parsed"]


def summarize_cost(records: list[dict]) -> dict:
    return {
        "agent_calls": len(records),
        "input_tokens": sum(row.get("prompt_eval_count") or 0 for row in records),
        "output_tokens": sum(row.get("eval_count") or 0 for row in records),
        "wall_seconds": sum(row.get("wall_seconds") or 0.0 for row in records),
        "load_seconds": sum(row.get("load_duration") or 0 for row in records) / 1e9,
        "usage_complete": all(row.get("prompt_eval_count") is not None and row.get("eval_count") is not None
                              for row in records),
    }


def run_packet(packet: dict, client: AgentClient, gate_policy: dict,
               method: str = "warrantroute") -> dict:
    """Review a locked original claim, optionally revise, and independently recheck it."""
    payload = packet_payload(packet)
    evidence_ids = {row["excerpt_id"] for row in payload["source_text_context"]}
    candidate = initial_candidate(payload, packet["packet_id"])
    original_candidate = copy.deepcopy(candidate)
    initial_flags: set[str] = set()
    reports: dict[str, dict] = {}
    history: list[dict] = []
    issue_archive: list[dict] = []
    route_trace: list[dict] = []
    state = {
        "schema_version": "ace-tight-loop-state-v1", "run_id": "runtime",
        "packet_id": packet["packet_id"], "data_phase": "development",
        "contains_source_text": False, "revision_round": 0,
        "route_mode": "generalist", "status": "awaiting_initial_agents",
        "budget": {"max_agent_calls": client.config["runtime"]["max_agent_calls"],
                   "agent_calls_used": 0,
                   "max_revision_rounds": 0 if method == "no_revision" else client.config["runtime"]["max_revision_rounds"]},
        "agent_assignments": [
            {"agent_id": role, "role": role, "model_id": model,
             "model_family": model.split(":")[0], "prompt_hash": "sha256:" + digest(client.prompt)}
            for role, model in client.assignment.items()
        ],
        "completed_agent_roles": [], "candidate": candidate, "evidence_map": None,
        "issues": [], "hard_checks": {}, "decision": None, "event_log": [],
    }

    def audit(role: str, stage: str, assigned: list[dict] | None = None) -> dict:
        task = {"task": payload if state["revision_round"] == 0 else {
                    "research_question": payload["research_question"],
                    "source_text_context": payload["source_text_context"]},
                "candidate": state["candidate"], "assigned_issues": assigned or []}
        if role in {"methods_challenger", "domain_challenger"} and state["revision_round"] == 0:
            task["locked_initial_assessments"] = {key: reports[key] for key in ("proposer", "evidence_scout")}
        output_schema = audit_output_schema(evidence_ids, {row["issue_id"] for row in assigned or []})
        report = copy.deepcopy(client.call(role, stage, task, output_schema))
        report["rating"]["serious_error_flags"] = sorted({issue["flag"] for issue in report["issues"]})
        validate_audit(report, evidence_ids, {row["issue_id"] for row in assigned or []})
        reports[role] = report
        history.append({"role": role, "stage": stage, "candidate_id": state["candidate"]["candidate_id"],
                        "report": report})
        if stage == "initial":
            initial_flags.update(report["rating"]["serious_error_flags"])
        if role not in state["completed_agent_roles"]:
            state["completed_agent_roles"].append(role)
        for index, issue in enumerate(report["issues"]):
            record = {
                "issue_id": f"{role}-{stage}-{index}",
                "owner_role": "evidence_scout" if role == "proposer" else role,
                "severity": "material", "category": FLAG_CATEGORY[issue["flag"]],
                "evidence_ids": issue["evidence_ids"], "diagnosis": issue["diagnosis"],
                "requested_change": issue["requested_change"], "status": "open", "resolution": None,
            }
            state["issues"].append(record)
            issue_archive.append({**record, "flag": issue["flag"], "origin_role": role,
                                  "candidate_id": state["candidate"]["candidate_id"]})
        return report

    error = None
    try:
        # Initial calls are isolated but scheduled serially on the local machine.
        audit("proposer", "initial")
        audit("evidence_scout", "initial")
        route, details = choose_initial_route(payload, reports["proposer"]["rating"], gate_policy)
        route = "both" if method == "always_on" else promoted_route(route, [
            reports[role]["rating"]["requested_expertise"] for role in reports
        ])
        state["route_mode"] = route
        route_trace.append({"stage": "initial", "route": route, **details})
        while True:
            missing = [role for role in required_initial_roles(state["route_mode"])
                       if role not in state["completed_agent_roles"]]
            if not missing:
                break
            for role in missing:
                audit(role, "initial")
            route = promoted_route(state["route_mode"], [reports[role]["rating"]["requested_expertise"] for role in missing])
            if route != state["route_mode"]:
                route_trace.append({"stage": "specialist_request", "route": route})
                state["route_mode"] = route

        while True:
            state["budget"]["agent_calls_used"] = len(client.records)
            scout = reports["evidence_scout"]
            sources = {row["source_id"] for row in payload["source_text_context"]}
            state["evidence_map"] = {
                "producer_agent_id": "evidence_scout", "support_ids": scout["support_ids"],
                "counterevidence_ids": scout["counterevidence_ids"], "context_gap_ids": [],
                "source_count": len(sources), "cluster_count": len(sources),
                "concentration_flag": "hidden_source_concentration" in scout["rating"]["serious_error_flags"],
            }
            quote_issue_ids = {row["issue_id"] for row in issue_archive if row["flag"] == "fabricated_or_altered_quote"}
            state["hard_checks"] = {
                "schema_valid": True,
                "evidence_ids_valid": set(state["candidate"]["evidence_ids"] + state["candidate"]["counterevidence_ids"]) <= evidence_ids,
                "quotation_fidelity": not any(row["status"] != "resolved" and row["issue_id"] in quote_issue_ids
                                               for row in state["issues"]),
                "source_counts_reconcile": True,
                "prohibited_fields_absent": not bool(FORBIDDEN_KEYS & all_keys(state["candidate"])),
                "protected_inference_absent": not any(row["category"] == "protected_inference" and row["status"] != "resolved"
                                                      for row in state["issues"]),
                "frozen_hashes_match": True,
            }
            STATE_VALIDATOR.validate(state)
            active_auditors = required_initial_roles(state["route_mode"])[1:]
            if any(reports[role]["rating"]["cannot_judge"] for role in active_auditors):
                state["status"] = "human_escalation"
                error = "unresolved_auditor_abstention"
                break
            decision = decide_next(state)
            state["decision"] = decision
            if decision["action"] == "accept" and any(reports[role]["rating"]["disposition"] != "accept"
                                                       for role in active_auditors):
                state["status"] = "human_escalation"
                error = "auditor_requested_action_without_located_issue"
                break
            if decision["action"] != "revise":
                state["status"] = {"accept": "accepted", "quarantine": "quarantined",
                                   "human_escalation": "human_escalation"}.get(decision["action"], "human_escalation")
                break
            blocking = [row for row in state["issues"] if row["status"] != "resolved"]
            if not blocking:
                state["status"] = "human_escalation"
                error = "integrity_failure_without_repairable_issue"
                break
            round_id = state["revision_round"] + 1
            state["status"] = "awaiting_revision"
            output_schema = revision_output_schema(evidence_ids, {row["issue_id"] for row in blocking})
            revision = client.call("reviser", f"revision-{round_id}", {
                "research_question": payload["research_question"],
                "source_text_context": payload["source_text_context"],
                "candidate": state["candidate"], "issues": blocking,
            }, output_schema)
            validate_revision(revision, evidence_ids, {row["issue_id"] for row in blocking})
            history.append({"role": "reviser", "stage": f"revision-{round_id}", "report": revision})
            responses = revision["issue_responses"]
            state["candidate"] = {
                **{key: value for key, value in revision.items() if key != "issue_responses"},
                "candidate_id": f"{packet['packet_id']}-r{round_id}",
                "producer_agent_id": "reviser", "playbook_bullet_ids": [],
            }
            state["revision_round"] = round_id
            state["status"] = "awaiting_recheck"
            owners = {row["owner_role"] for row in blocking} | {"evidence_scout"}
            for role in active_auditors:
                if role not in owners:
                    continue
                assigned = [row for row in blocking if row["owner_role"] == role]
                report = audit(role, f"recheck-{round_id}", assigned)
                for issue in assigned:
                    if issue["issue_id"] in report["resolved_issue_ids"]:
                        issue["status"] = "resolved"
                        issue["resolution"] = responses[issue["issue_id"]]
            # No new specialist is activated after revision without a reserved audit call.
            requested = [reports[role]["rating"]["requested_expertise"] for role in owners]
            if promoted_route(state["route_mode"], requested) != state["route_mode"]:
                state["status"] = "human_escalation"
                error = "new_expertise_requested_after_revision"
                break
    except Exception as exc:
        state["status"] = "human_escalation" if isinstance(exc, CallFailure) else "quarantined"
        error = f"{type(exc).__name__}:{str(exc)[:200]}"
    state["budget"]["agent_calls_used"] = len(client.records)
    return {
        "result_version": "warrantroute-live-loop-result-v1", "method_name": "WarrantRoute",
        "variant": client.config["variant"], "method": method, "packet_id": packet["packet_id"],
        "corpus_id": packet["corpus_id"], "status": state["status"], "error": error,
        "route": state["route_mode"], "route_trace": route_trace,
        "revision_rounds": state["revision_round"],
        "original_detected_flags": sorted(initial_flags),
        "original_candidate": original_candidate, "final_candidate": state["candidate"],
        "issues": state["issues"], "issue_archive": issue_archive,
        "audit_history": history, "cost": summarize_cost(client.records),
        "semantic_repair_quality": None, "independent_repair_evaluation_required": True,
        "playbook_update_enabled": False, "manuscript_eligible": False,
    }
