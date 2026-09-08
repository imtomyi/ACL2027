#!/usr/bin/env python3
"""Deterministic controller for the prospective ACE-TightLoop design.

This module performs no model calls, reads no study data, and writes no files.
It only defines the four-mode sparse agent graph and the initial bounded
accept/revise/escalate decision rule.
"""

from __future__ import annotations

from typing import Any


ROUTE_AUDITORS = {
    "generalist": ("evidence_scout",),
    "qualitative_methods": ("evidence_scout", "methods_challenger"),
    "domain": ("evidence_scout", "domain_challenger"),
    "both": ("evidence_scout", "methods_challenger", "domain_challenger"),
}

TERMINAL_STATUSES = {"accepted", "human_escalation", "quarantined"}
BLOCKING_SEVERITIES = {"material", "hard"}
NONREPAIRABLE_CHECKS = {"schema_valid", "prohibited_fields_absent", "frozen_hashes_match"}


class TightLoopContractError(ValueError):
    """Raised when a controller input violates the prospective contract."""


def required_initial_roles(route_mode: str) -> tuple[str, ...]:
    """Return the sparse initial agent set for one WarrantRoute mode."""

    try:
        auditors = ROUTE_AUDITORS[route_mode]
    except KeyError as exc:
        raise TightLoopContractError(f"unknown_route_mode:{route_mode}") from exc
    return ("proposer", *auditors)


def validate_model_family_separation(
    state: dict[str, Any], *, policy: str = "cross_family"
) -> None:
    """Enforce the default diverse assignment or an explicit same-model ablation."""

    if policy not in {"cross_family", "same_model_ablation"}:
        raise TightLoopContractError("unknown_model_assignment_policy")

    assignments = state.get("agent_assignments")
    if not isinstance(assignments, list):
        raise TightLoopContractError("agent_assignments_must_be_list")
    by_role: dict[str, dict[str, Any]] = {}
    agent_ids: set[str] = set()
    for assignment in assignments:
        if not isinstance(assignment, dict):
            raise TightLoopContractError("agent_assignment_must_be_object")
        role = str(assignment.get("role", ""))
        agent_id = str(assignment.get("agent_id", ""))
        family = str(assignment.get("model_family", ""))
        if not role or not agent_id or not family:
            raise TightLoopContractError("incomplete_agent_assignment")
        if role in by_role:
            raise TightLoopContractError(f"duplicate_agent_role:{role}")
        if agent_id in agent_ids:
            raise TightLoopContractError(f"duplicate_agent_id:{agent_id}")
        by_role[role] = assignment
        agent_ids.add(agent_id)

    required = required_initial_roles(str(state.get("route_mode", "")))
    missing = [role for role in required if role not in by_role]
    if missing:
        raise TightLoopContractError("missing_agent_assignments:" + ",".join(missing))

    if policy == "same_model_ablation":
        expected = {"proposer", "evidence_scout", "methods_challenger", "domain_challenger", "reviser"}
        models = {str(value.get("model_id", "")) for value in by_role.values()}
        families = {str(value["model_family"]) for value in by_role.values()}
        if set(by_role) != expected or len(models) != 1 or "" in models or len(families) != 1:
            raise TightLoopContractError("same_model_ablation_requires_one_model_in_every_role")
        return

    proposer_family = str(by_role["proposer"]["model_family"])
    auditor_families = {str(by_role[role]["model_family"]) for role in required[1:]}
    if auditor_families == {proposer_family}:
        raise TightLoopContractError("no_cross_family_auditor")
    if "reviser" in by_role and str(by_role["reviser"]["model_family"]) == proposer_family:
        raise TightLoopContractError("proposer_reviser_family_collision")


def failed_hard_checks(state: dict[str, Any]) -> list[str]:
    """Return deterministically failed check names in stable order."""

    checks = state.get("hard_checks")
    if not isinstance(checks, dict) or not checks:
        raise TightLoopContractError("missing_hard_checks")
    invalid = [name for name, passed in checks.items() if not isinstance(passed, bool)]
    if invalid:
        raise TightLoopContractError("non_boolean_hard_checks:" + ",".join(sorted(invalid)))
    return sorted(name for name, passed in checks.items() if not passed)


def open_blocking_issues(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return open material or hard issues without accepting self-resolution."""

    issues = state.get("issues", [])
    if not isinstance(issues, list):
        raise TightLoopContractError("issues_must_be_list")
    blocking: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            raise TightLoopContractError("issue_must_be_object")
        if issue.get("severity") in BLOCKING_SEVERITIES and issue.get("status") != "resolved":
            blocking.append(issue)
    return blocking


def recheck_roles(state: dict[str, Any], blocking: list[dict[str, Any]]) -> tuple[str, ...]:
    """Recheck evidence plus only the agents that own unresolved objections."""

    owners = {str(issue.get("owner_role", "")) for issue in blocking}
    owners.discard("")
    owners.add("evidence_scout")
    allowed = set(ROUTE_AUDITORS[state["route_mode"]])
    invalid = sorted(owners - allowed)
    if invalid:
        raise TightLoopContractError("issue_owner_not_active:" + ",".join(invalid))
    return tuple(role for role in ROUTE_AUDITORS[state["route_mode"]] if role in owners)


def decide_next(state: dict[str, Any], *, model_assignment_policy: str = "cross_family") -> dict[str, Any]:
    """Choose wait, accept, revise, or human escalation for a locked state."""

    route_mode = str(state.get("route_mode", ""))
    required = required_initial_roles(route_mode)
    validate_model_family_separation(state, policy=model_assignment_policy)
    status = str(state.get("status", ""))
    if status in TERMINAL_STATUSES:
        return {
            "action": "wait",
            "reason_codes": ["terminal_state_is_immutable"],
            "missing_agent_roles": [],
            "required_additional_calls": 0,
        }

    completed_raw = state.get("completed_agent_roles", [])
    if not isinstance(completed_raw, list):
        raise TightLoopContractError("completed_agent_roles_must_be_list")
    completed = {str(role) for role in completed_raw}
    missing = [role for role in required if role not in completed]
    if missing:
        return {
            "action": "wait",
            "reason_codes": ["required_initial_agents_incomplete"],
            "missing_agent_roles": missing,
            "required_additional_calls": len(missing),
        }

    budget = state.get("budget")
    if not isinstance(budget, dict):
        raise TightLoopContractError("missing_budget")
    try:
        calls_used = int(budget["agent_calls_used"])
        max_calls = int(budget["max_agent_calls"])
        max_rounds = int(budget["max_revision_rounds"])
        revision_round = int(state["revision_round"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TightLoopContractError("invalid_budget_or_round") from exc
    if min(calls_used, max_calls, max_rounds, revision_round) < 0:
        raise TightLoopContractError("negative_budget_or_round")
    if calls_used > max_calls:
        raise TightLoopContractError("agent_calls_exceed_budget")
    if revision_round > max_rounds:
        raise TightLoopContractError("revision_round_exceeds_limit")

    failed_checks = failed_hard_checks(state)
    blocking = open_blocking_issues(state)
    nonrepairable = sorted(set(failed_checks) & NONREPAIRABLE_CHECKS)
    if nonrepairable:
        return {
            "action": "quarantine",
            "reason_codes": [f"nonrepairable_check_failed:{name}" for name in nonrepairable],
            "missing_agent_roles": [],
            "required_additional_calls": 0,
        }
    if not failed_checks and not blocking:
        return {
            "action": "accept",
            "reason_codes": ["hard_checks_passed", "no_open_blocking_issue"],
            "missing_agent_roles": [],
            "required_additional_calls": 0,
        }

    reasons = []
    if failed_checks:
        reasons.extend(f"hard_check_failed:{name}" for name in failed_checks)
    if blocking:
        reasons.append("open_blocking_issues")

    if revision_round >= max_rounds:
        return {
            "action": "human_escalation",
            "reason_codes": [*reasons, "revision_round_limit_reached"],
            "missing_agent_roles": [],
            "required_additional_calls": 0,
        }

    owners = recheck_roles(state, blocking) if blocking else ("evidence_scout",)
    required_calls = 1 + len(owners)
    if calls_used + required_calls > max_calls:
        return {
            "action": "human_escalation",
            "reason_codes": [*reasons, "agent_call_budget_insufficient"],
            "missing_agent_roles": [],
            "required_additional_calls": required_calls,
        }

    return {
        "action": "revise",
        "reason_codes": reasons,
        "missing_agent_roles": [],
        "required_additional_calls": required_calls,
    }
