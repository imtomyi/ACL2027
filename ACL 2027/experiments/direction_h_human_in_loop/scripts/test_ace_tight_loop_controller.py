#!/usr/bin/env python3
"""Unit tests for the source-text-free ACE-TightLoop controller."""

from __future__ import annotations

import unittest

from ace_tight_loop_controller import (
    TightLoopContractError,
    decide_next,
    required_initial_roles,
)


def base_state(route_mode: str = "both") -> dict:
    required = list(required_initial_roles(route_mode))
    family_by_role = {
        "proposer": "qwen3",
        "evidence_scout": "gemma3",
        "methods_challenger": "llama3",
        "domain_challenger": "gemma3",
        "reviser": "llama3",
    }
    return {
        "route_mode": route_mode,
        "status": "awaiting_selected_auditors",
        "revision_round": 0,
        "budget": {
            "max_agent_calls": 10,
            "agent_calls_used": len(required),
            "max_revision_rounds": 2,
        },
        "agent_assignments": [
            {
                "agent_id": f"{role}-agent",
                "role": role,
                "model_family": family_by_role[role],
            }
            for role in [*required, "reviser"]
        ],
        "completed_agent_roles": required,
        "issues": [],
        "hard_checks": {
            "schema_valid": True,
            "evidence_ids_valid": True,
            "quotation_fidelity": True,
            "source_counts_reconcile": True,
            "prohibited_fields_absent": True,
            "protected_inference_absent": True,
            "frozen_hashes_match": True,
        },
    }


class TightLoopControllerTests(unittest.TestCase):
    def test_four_modes_have_sparse_requirements(self) -> None:
        self.assertEqual(required_initial_roles("generalist"), ("proposer", "evidence_scout"))
        self.assertEqual(
            required_initial_roles("qualitative_methods"),
            ("proposer", "evidence_scout", "methods_challenger"),
        )
        self.assertEqual(
            required_initial_roles("domain"),
            ("proposer", "evidence_scout", "domain_challenger"),
        )
        self.assertEqual(
            required_initial_roles("both"),
            ("proposer", "evidence_scout", "methods_challenger", "domain_challenger"),
        )

    def test_missing_agent_blocks_decision(self) -> None:
        state = base_state("both")
        state["completed_agent_roles"].remove("domain_challenger")
        decision = decide_next(state)
        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["missing_agent_roles"], ["domain_challenger"])

    def test_clean_candidate_is_accepted(self) -> None:
        self.assertEqual(decide_next(base_state())["action"], "accept")

    def test_minor_issue_does_not_veto(self) -> None:
        state = base_state()
        state["issues"] = [
            {
                "issue_id": "ISSUE-1",
                "owner_role": "methods_challenger",
                "severity": "minor",
                "status": "open",
            }
        ]
        self.assertEqual(decide_next(state)["action"], "accept")

    def test_material_issue_triggers_issue_owner_recheck(self) -> None:
        state = base_state()
        state["issues"] = [
            {
                "issue_id": "ISSUE-2",
                "owner_role": "methods_challenger",
                "severity": "material",
                "status": "open",
            }
        ]
        decision = decide_next(state)
        self.assertEqual(decision["action"], "revise")
        self.assertEqual(decision["required_additional_calls"], 3)

    def test_hard_check_failure_triggers_revision(self) -> None:
        state = base_state("generalist")
        state["hard_checks"]["quotation_fidelity"] = False
        decision = decide_next(state)
        self.assertEqual(decision["action"], "revise")
        self.assertIn("hard_check_failed:quotation_fidelity", decision["reason_codes"])

    def test_frozen_hash_failure_quarantines(self) -> None:
        state = base_state("generalist")
        state["hard_checks"]["frozen_hashes_match"] = False
        decision = decide_next(state)
        self.assertEqual(decision["action"], "quarantine")

    def test_proposer_reviser_must_use_different_families(self) -> None:
        state = base_state("generalist")
        for assignment in state["agent_assignments"]:
            if assignment["role"] == "reviser":
                assignment["model_family"] = "qwen3"
        with self.assertRaisesRegex(TightLoopContractError, "family_collision"):
            decide_next(state)

    def test_round_limit_escalates(self) -> None:
        state = base_state()
        state["revision_round"] = 2
        state["issues"] = [
            {
                "issue_id": "ISSUE-3",
                "owner_role": "domain_challenger",
                "severity": "hard",
                "status": "human_hold",
            }
        ]
        self.assertEqual(decide_next(state)["action"], "human_escalation")

    def test_call_budget_escalates(self) -> None:
        state = base_state("domain")
        state["budget"]["max_agent_calls"] = 4
        state["budget"]["agent_calls_used"] = 3
        state["issues"] = [
            {
                "issue_id": "ISSUE-4",
                "owner_role": "domain_challenger",
                "severity": "material",
                "status": "open",
            }
        ]
        decision = decide_next(state)
        self.assertEqual(decision["action"], "human_escalation")
        self.assertIn("agent_call_budget_insufficient", decision["reason_codes"])


if __name__ == "__main__":
    unittest.main()
