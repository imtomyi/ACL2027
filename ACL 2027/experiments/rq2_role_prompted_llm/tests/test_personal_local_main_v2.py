#!/usr/bin/env python3
"""Source-free unit tests for the separate v2 qualification wrapper."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_personal_local_main_v2.py"
SPEC = importlib.util.spec_from_file_location("rq2_personal_local_main_v2_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_row(packet_index: int, *, admitted: bool) -> dict:
    packet_id = f"PKT_{packet_index:016x}"
    return {
        "slot_id": runner.slot_id("dreaddit_development", packet_id, "base"),
        "lane": "dreaddit_development",
        "packet_index": packet_index,
        "packet_id": packet_id,
        "bootstrap_cluster_id": f"CLU_{packet_index:016x}",
        "generation_call_id": f"generate_dreaddit_development_packet_{packet_index:02d}_base_v2",
        "generation_status": "valid",
        "semantic_status": "valid" if admitted else "invalid",
        "gate_call_id": (
            f"verify_dreaddit_development_packet_{packet_index:02d}_base_admissibility_v2"
            if admitted
            else None
        ),
        "gate_status": "valid" if admitted else "not_attempted",
        "base_status": "admitted" if admitted else "semantic_invalid",
        "reason_codes": [] if admitted else ["base_support_units_not_independent"],
        "base_item_sha256": "a" * 64 if admitted else None,
        "contains_source_text": False,
    }


def variant_row(
    packet_index: int,
    family_index: int,
    *,
    accepted: bool = True,
    skipped: bool = False,
    terminal: bool = False,
) -> dict:
    family = runner.FAMILY_ORDER[family_index - 1]
    packet_id = f"PKT_{packet_index:016x}"
    constructed = not skipped and not terminal
    if skipped:
        reason_codes = ["base_not_admitted"]
    elif terminal:
        reason_codes = ["targeted_edit_terminal"]
    elif accepted:
        reason_codes = []
    else:
        reason_codes = ["comparison_unclear"]
    return {
        "slot_id": runner.slot_id("dreaddit_development", packet_id, family),
        "lane": "dreaddit_development",
        "packet_index": packet_index,
        "packet_id": packet_id,
        "bootstrap_cluster_id": f"CLU_{packet_index:016x}",
        "family_index": family_index,
        "family": family,
        "base_status": "semantic_invalid" if skipped else "admitted",
        "attempted": not skipped,
        "construction_mode": (
            "deterministic_only" if family_index <= 3 else "targeted_model_patch"
        ),
        "generation_call_id": (
            f"generate_dreaddit_development_packet_{packet_index:02d}_edit_{family_index:02d}_v2"
            if family_index >= 4 and not skipped
            else None
        ),
        "construction_status": (
            "skipped_invalid_base"
            if skipped
            else "generation_terminal"
            if terminal
            else "constructed"
        ),
        "structural_pass": constructed,
        "verification_call_id": (
            f"verify_dreaddit_development_packet_{packet_index:02d}_comparison_{family_index:02d}_v2"
            if constructed
            else None
        ),
        "verification_status": "valid" if constructed else "not_attempted",
        "comparison_clarity": "clear" if constructed else None,
        "accepted": accepted if constructed else False,
        "item_id": f"DJI_{packet_index:08x}{family_index:08x}" if constructed else None,
        "reason_codes": reason_codes,
        "fatal_terminal": terminal,
        "fatal_invariant": False,
        "contains_source_text": False,
    }


def admitted_entry() -> dict:
    excerpts = [
        {
            "display_order": position,
            "excerpt_id": f"EXC_{position:016x}",
            "source_id": f"SRC_{position:016x}",
            "speaker_id": None,
            "local_context": None,
            "text": f"Internal fixture evidence position {position}.",
        }
        for position in range(1, 7)
    ]
    roles = {
        excerpts[0]["excerpt_id"]: ("support", "Fixture support."),
        excerpts[1]["excerpt_id"]: ("support", "Fixture support."),
        excerpts[2]["excerpt_id"]: ("counterevidence", "Fixture countercase."),
        excerpts[3]["excerpt_id"]: ("context_only", None),
        excerpts[4]["excerpt_id"]: ("context_only", None),
        excerpts[5]["excerpt_id"]: ("context_only", None),
    }
    interpretation = {
        "theme_name": "Fixture theme",
        "claim": "Within this displayed fixture packet, two positions support a bounded claim.",
        "explanation": "The fixture interpretation preserves one countercase.",
        "boundary_conditions": ["The third position is a fixture countercase."],
    }
    item = runner.v1.build_item(
        lane_name="dreaddit_development",
        corpus="dreaddit",
        packet_id="PKT_0000000000000001",
        output_key="fixture-base",
        interpretation=interpretation,
        roles=roles,
        excerpts=excerpts,
    )
    metadata = {
        "position_to_excerpt_id": {
            str(position): excerpts[position - 1]["excerpt_id"] for position in range(1, 7)
        },
        "role_by_position": {
            "1": "support",
            "2": "support",
            "3": "counterevidence",
            "4": "context_only",
            "5": "context_only",
            "6": "context_only",
        },
        "counter_boundary_links": [{"counter_position": 3, "boundary_slot": 1}],
    }
    checks = {
        "all_material_claims_warranted": True,
        "support_roles_accurate": True,
        "independent_support_units_sufficient": True,
        "counter_roles_genuine": True,
        "boundary_links_consequential_and_preserved": True,
        "claim_scope_packet_bounded": True,
        "no_outside_facts": True,
        "no_other_material_flaw": True,
    }
    gate_output = {
        "admissibility_schema_version": "rq2-base-admissibility-v2",
        "base_status": "admissible",
        "checks": checks,
        "readiness": {
            "non_support_anchor": {"status": "ready", "evidence_positions": [4]},
            "multi_unit_support": {"status": "ready", "evidence_positions": [1, 2]},
            "consequential_counter": {"status": "ready", "evidence_positions": [3]},
            "local_distinction": {"status": "ready", "evidence_positions": [1]},
            "bounded_claim": {"status": "ready", "evidence_positions": [1]},
        },
        "reason_codes": [],
    }
    row = base_row(1, admitted=True)
    return {
        "row": row,
        "base_item": item,
        "metadata": metadata,
        "excerpts": excerpts,
        "base_gate_output": gate_output,
        "base_gate_report_sha256": "b" * 64,
    }


class V2QualificationTests(unittest.TestCase):
    def test_v1_bytes_remain_exactly_frozen(self):
        self.assertEqual(file_sha256(runner.V1_SCRIPT), runner.V1_RUNNER_SHA256)
        self.assertEqual(file_sha256(runner.V1_CONFIG), runner.V1_FREEZE_SHA256)

    def test_static_v2_freeze_passes_without_record_loading(self):
        config = runner.v1.load_json(runner.DEFAULT_CONFIG)
        with mock.patch.object(
            runner.v1, "load_bound_records", side_effect=AssertionError("records opened")
        ):
            _, _, _, excluded = runner.validate_v2_freeze(
                config, include_record_hashes=False, config_path=runner.DEFAULT_CONFIG
            )
        self.assertEqual(len(excluded), 30)
        comparison_rule = runner.v1.load_json(
            runner.RQ2_ROOT
            / "protocol"
            / "construction_comparison_acceptance_rule_v2.json"
        )
        self.assertEqual(
            config["result_labels"]["verification_label"],
            comparison_rule["verification_label"],
        )
        self.assertEqual(runner.VERIFICATION_LABEL, comparison_rule["verification_label"])

    def test_fail_closed_qualification_permissions_cannot_be_enabled(self):
        original = runner.v1.load_json(runner.DEFAULT_CONFIG)
        forbidden_true = (
            "reviewer_calls_allowed",
            "fixed_role_selection_allowed",
            "dreaddit_audit_access_allowed",
            "agyw_heldout_access_allowed",
        )
        for key in forbidden_true:
            mutated = dict(original)
            mutated[key] = True
            with self.assertRaises(runner.V2Error, msg=key):
                runner.validate_v2_freeze(
                    mutated, include_record_hashes=False, config_path=runner.DEFAULT_CONFIG
                )
        for key in ("qualification_only", "main_execution_requires_separate_freeze"):
            mutated = dict(original)
            mutated[key] = False
            with self.assertRaises(runner.V2Error, msg=key):
                runner.validate_v2_freeze(
                    mutated, include_record_hashes=False, config_path=runner.DEFAULT_CONFIG
                )

    def test_selection_helper_rejects_heldout_lane_in_qualification_freeze(self):
        v1_config = runner.v1.load_json(runner.V1_CONFIG)
        v2_config = runner.v1.load_json(runner.DEFAULT_CONFIG)
        with self.assertRaisesRegex(
            runner.V2Error, "v2_qualification_heldout_selection_forbidden"
        ):
            runner.select_lane_packets_v2(
                v1_config,
                v2_config,
                runner.V2_OUTPUT_ROOT / "rq2plv2_20260827T000000Z_ffffffff",
                "dreaddit_audit",
                [],
                excluded_commitments=set(),
            )

    def test_schema_valid_semantic_invalid_base_has_finite_code(self):
        entry = admitted_entry()
        excerpts = entry["excerpts"]
        generated = {
            "generation_schema_version": "rq2-base-generation-v2",
            "status": "constructed",
            "theme_name": "Fixture",
            "claim": "Fixture claim",
            "explanation": "Fixture explanation",
            "claim_scope": "displayed_packet_only",
            "role_plan": [
                {"position": position, "role": "support" if position in (1, 2) else "counterevidence"}
                for position in range(1, 7)
            ],
            "boundary_conditions": [
                {"counter_position": position, "text": "Fixture boundary"}
                for position in range(3, 7)
            ],
        }
        with self.assertRaisesRegex(runner.V2Error, "base_context_count_insufficient"):
            runner.map_positional_base_v2(generated, excerpts)

    def test_invalid_base_creates_five_skips_and_no_calls(self):
        config = runner.v1.load_json(runner.V1_CONFIG)
        row = base_row(1, admitted=False)
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_00000000"
            paths = {"item_schema": runner.v1.resolve_workspace_path(config["evaluator_item_schema_file"])}
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(
                    runner.v1,
                    "invoke_checkpointed_call",
                    side_effect=AssertionError("dependent call made"),
                ),
            ):
                rows, truths, summary = runner.run_variant_and_comparison_phases_v2(
                    config,
                    paths,
                    {"schema_construction_comparison": {}},
                    run_dir,
                    "dreaddit_development",
                    [row],
                    [],
                )
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(value["construction_status"] == "skipped_invalid_base" for value in rows))
            self.assertEqual(summary["planned"], 5)
            self.assertEqual(summary["skipped_invalid_base"], 5)
            self.assertEqual(summary["attempted"], 0)
            self.assertEqual(truths, [])

    def test_terminal_targeted_edits_are_quarantined_once_without_retry(self):
        config = runner.v1.load_json(runner.V1_CONFIG)
        entry = admitted_entry()
        item_schema = runner.v1.resolve_workspace_path(config["evaluator_item_schema_file"])
        schemas = {
            "contextual_flattening": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "contextual_flattening_edit_v2.schema.json"
            ),
            "unsupported_abstraction": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "unsupported_abstraction_edit_v2.schema.json"
            ),
            "comparison": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "construction_comparison_v2.schema.json"
            ),
        }
        seen: list[tuple[str, bool]] = []

        def fake_call(*args, **kwargs):
            call_id = kwargs["call_id"]
            seen.append((call_id, kwargs["retry_transport_on_explicit_resume"]))
            if call_id.startswith("generate_"):
                return {
                    "status": "terminal_error",
                    "error": {"stage": "response_validation", "type": "FixtureTerminal"},
                    "execution": {},
                }
            family_index = int(call_id.split("_comparison_")[1][:2])
            family = runner.FAMILY_ORDER[family_index - 1]
            anchors = {
                "unsupported_evidence": [4],
                "source_concentration": [1, 2],
                "counterevidence_loss": [3],
            }[family]
            return {
                "status": "valid",
                "output": {
                    "comparison_schema_version": "rq2-construction-comparison-v2",
                    "comparison_clarity": "clear",
                    "present_flaws": [family],
                    "other_material_flaw": False,
                    "single_material_difference": True,
                    "anchors": [
                        {
                            "flaw_family": family,
                            "evidence_positions": anchors,
                            "interpretation_fields": [next(iter(runner.ALLOWED_ANCHOR_FIELDS[family]))],
                            "reason_code": runner.TARGET_REASON_CODE[family],
                        }
                    ],
                    "uncertainty_codes": [],
                },
                "execution": {},
            }

        assets = {
            "prompt_contextual_flattening_edit": "fixture",
            "schema_contextual_flattening_edit": schemas["contextual_flattening"],
            "prompt_unsupported_abstraction_edit": "fixture",
            "schema_unsupported_abstraction_edit": schemas["unsupported_abstraction"],
            "prompt_construction_comparison": "fixture",
            "schema_construction_comparison": schemas["comparison"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_11111111"
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(runner.v1, "invoke_checkpointed_call", side_effect=fake_call),
            ):
                rows, truths, summary = runner.run_variant_and_comparison_phases_v2(
                    config,
                    {"item_schema": item_schema},
                    assets,
                    run_dir,
                    "dreaddit_development",
                    [entry["row"]],
                    [entry],
                )
        generated = [row for row in rows if row["family"] in runner.GENERATED_EDIT_FAMILIES]
        self.assertTrue(all(row["construction_status"] == "generation_terminal" for row in generated))
        self.assertTrue(all(row["fatal_terminal"] for row in generated))
        self.assertEqual(summary["fatal_terminal"], 2)
        self.assertEqual(len(truths), 3)
        self.assertTrue(all(retry is False for _, retry in seen))
        self.assertEqual(len([call for call, _ in seen if call.startswith("generate_")]), 2)

    def test_reconciliation_equations_and_family_sums(self):
        bases = [base_row(index, admitted=index <= 8) for index in range(1, 11)]
        rows = []
        for packet_index in range(1, 11):
            for family_index in range(1, 6):
                rows.append(
                    variant_row(
                        packet_index,
                        family_index,
                        skipped=packet_index > 8,
                        terminal=packet_index == 8 and family_index == 5,
                    )
                )
        summary = runner.reconcile_lane_funnel_v2(bases, rows)
        self.assertEqual(summary["planned"], 50)
        self.assertEqual(summary["skipped_invalid_base"], 10)
        self.assertEqual(summary["attempted"], 40)
        self.assertEqual(summary["constructed"], 39)
        self.assertEqual(summary["verification_attempted"], 39)
        self.assertEqual(summary["fatal_terminal"], 1)
        self.assertEqual(sum(value["planned"] for value in summary["by_family"].values()), 50)

    def test_reconciliation_enforces_base_to_variant_lifecycle(self):
        bases = [base_row(1, admitted=False)]
        rows = [variant_row(1, family_index, skipped=True) for family_index in range(1, 6)]
        rows[0]["attempted"] = True
        with self.assertRaisesRegex(
            runner.V2Error, "v2_variant_base_lifecycle_mismatch"
        ):
            runner.reconcile_lane_funnel_v2(bases, rows)

    def test_reconciliation_binds_family_position_and_slot(self):
        bases = [base_row(1, admitted=True)]
        rows = [variant_row(1, family_index) for family_index in range(1, 6)]
        wrong_family = [dict(row) for row in rows]
        wrong_family[0]["family"] = runner.FAMILY_ORDER[1]
        with self.assertRaisesRegex(
            runner.V2Error, "v2_variant_family_position_mismatch"
        ):
            runner.reconcile_lane_funnel_v2(bases, wrong_family)

        wrong_slot = [dict(row) for row in rows]
        wrong_slot[0]["slot_id"] = "SLT_tampered"
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_slot_id_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, wrong_slot)

    def test_reconciliation_recomputes_variant_call_ids(self):
        bases = [base_row(1, admitted=True)]
        rows = [variant_row(1, family_index) for family_index in range(1, 6)]
        rows[3]["generation_call_id"] = "generate_tampered"
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_call_id_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, rows)

    def test_quarantine_rejects_unbounded_reason_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_44444444"
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                self.assertRaisesRegex(runner.V2Error, "v2_reason_code_invalid"),
            ):
                runner.write_quarantine(
                    run_dir,
                    lane_name="dreaddit_development",
                    packet_index=1,
                    packet_id="PKT_0000000000000001",
                    family_index=None,
                    family=None,
                    outcome="semantic_invalid",
                    reason_codes=["raw exception text must not serialize"],
                    call_id=runner.canonical_base_generation_call_id(
                        "dreaddit_development", 1
                    ),
                )

    def test_qualification_pass_and_fail_both_stop_before_downstream(self):
        config = runner.v1.load_json(runner.DEFAULT_CONFIG)
        bases = [base_row(index, admitted=True) for index in range(1, 11)]
        passing_rows = [
            variant_row(packet_index, family_index)
            for packet_index in range(1, 11)
            for family_index in range(1, 6)
        ]
        passing = runner.reconcile_lane_funnel_v2(bases, passing_rows)
        failing_rows = [dict(row) for row in passing_rows]
        failing_row = failing_rows[3]
        failing_row["construction_status"] = "generation_terminal"
        failing_row["structural_pass"] = False
        failing_row["verification_call_id"] = None
        failing_row["verification_status"] = "not_attempted"
        failing_row["comparison_clarity"] = None
        failing_row["accepted"] = False
        failing_row["item_id"] = None
        failing_row["reason_codes"] = ["targeted_edit_terminal"]
        failing_row["fatal_terminal"] = True
        failing = runner.reconcile_lane_funnel_v2(bases, failing_rows)
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            with mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root):
                passed_dir = output_root / "rq2plv2_20260827T000000Z_22222222"
                failed_dir = output_root / "rq2plv2_20260827T000000Z_33333333"
                runner.write_v2_bytes(passed_dir / "v2_freeze_snapshot.json", b"fixture\n")
                runner.write_v2_bytes(failed_dir / "v2_freeze_snapshot.json", b"fixture\n")
                passed_gate = runner.evaluate_development_qualification_v2(
                    config, passed_dir, passing
                )
                failed_gate = runner.evaluate_development_qualification_v2(
                    config, failed_dir, failing
                )
        self.assertTrue(passed_gate["passed"])
        self.assertFalse(failed_gate["passed"])
        for gate in (passed_gate, failed_gate):
            self.assertTrue(gate["no_reviewer_calls_allowed_in_this_freeze"])
            self.assertTrue(gate["no_heldout_access_allowed_in_this_freeze"])
            self.assertTrue(gate["continuation_requires_separate_bound_v2_main_freeze"])


if __name__ == "__main__":
    unittest.main()
