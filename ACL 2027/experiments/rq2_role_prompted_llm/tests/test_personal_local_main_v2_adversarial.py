#!/usr/bin/env python3
"""Adversarial, source-free tests for the isolated v2 qualification runner.

Every fixture in this module is synthetic.  The tests never open a corpus record
or any artifact below a prior run directory.
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_personal_local_main_v2.py"
SPEC = importlib.util.spec_from_file_location(
    "rq2_personal_local_main_v2_adversarial_tests", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def base_row(packet_index: int, *, admitted: bool) -> dict:
    packet_id = f"PKT_{packet_index:016x}"
    return {
        "slot_id": runner.slot_id("dreaddit_development", packet_id, "base"),
        "lane": "dreaddit_development",
        "packet_index": packet_index,
        "packet_id": packet_id,
        "bootstrap_cluster_id": f"CLU_{packet_index:016x}",
        "generation_call_id": (
            f"generate_dreaddit_development_packet_{packet_index:02d}_base_v2"
        ),
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
        "reason_codes": (
            []
            if accepted and constructed
            else ["base_not_admitted"]
            if skipped
            else ["targeted_edit_terminal", "response_validation", "SyntheticTerminal"]
            if terminal
            else ["present_flaws_not_exact_singleton_target"]
        ),
        "fatal_terminal": terminal,
        "fatal_invariant": False,
        "contains_source_text": False,
    }


def grid(base_rows: list[dict]) -> list[dict]:
    return [
        variant_row(
            base["packet_index"],
            family_index,
            skipped=base["base_status"] != "admitted",
        )
        for base in base_rows
        for family_index in range(1, 6)
    ]


def admitted_entry() -> dict:
    excerpts = [
        {
            "display_order": position,
            "excerpt_id": f"EXC_{position:016x}",
            "source_id": f"SRC_{position:016x}",
            "speaker_id": None,
            "local_context": None,
            "text": f"Synthetic evidence position {position}.",
        }
        for position in range(1, 7)
    ]
    roles = {
        excerpts[0]["excerpt_id"]: ("support", "Synthetic support."),
        excerpts[1]["excerpt_id"]: ("support", "Synthetic support."),
        excerpts[2]["excerpt_id"]: ("counterevidence", "Synthetic countercase."),
        excerpts[3]["excerpt_id"]: ("context_only", None),
        excerpts[4]["excerpt_id"]: ("context_only", None),
        excerpts[5]["excerpt_id"]: ("context_only", None),
    }
    interpretation = {
        "theme_name": "Synthetic theme",
        "claim": "Two displayed synthetic positions support a bounded claim.",
        "explanation": "The synthetic interpretation retains one countercase.",
        "boundary_conditions": ["The third synthetic position is a countercase."],
    }
    item = runner.v1.build_item(
        lane_name="dreaddit_development",
        corpus="dreaddit",
        packet_id="PKT_0000000000000001",
        output_key="synthetic-base",
        interpretation=interpretation,
        roles=roles,
        excerpts=excerpts,
    )
    metadata = {
        "position_to_excerpt_id": {
            str(position): excerpts[position - 1]["excerpt_id"]
            for position in range(1, 7)
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
    return {
        "row": base_row(1, admitted=True),
        "base_item": item,
        "metadata": metadata,
        "excerpts": excerpts,
        "base_gate_output": gate_output,
        "base_gate_report_sha256": "b" * 64,
    }


def comparison_output(family: str, positions: list[int]) -> dict:
    return {
        "comparison_schema_version": "rq2-construction-comparison-v2",
        "comparison_clarity": "clear",
        "present_flaws": [family],
        "other_material_flaw": False,
        "single_material_difference": True,
        "anchors": [
            {
                "flaw_family": family,
                "evidence_positions": positions,
                "interpretation_fields": [
                    sorted(runner.ALLOWED_ANCHOR_FIELDS[family])[0]
                ],
                "reason_code": runner.TARGET_REASON_CODE[family],
            }
        ],
        "uncertainty_codes": [],
    }


class V2AdversarialTests(unittest.TestCase):
    def test_lifecycle_reconciliation_accepts_only_exact_equations(self):
        bases = [base_row(1, admitted=True), base_row(2, admitted=False)]
        rows = grid(bases)
        summary = runner.reconcile_lane_funnel_v2(bases, rows)
        self.assertEqual(summary["planned"], 10)
        self.assertEqual(summary["attempted"], 5)
        self.assertEqual(summary["skipped_invalid_base"], 5)
        self.assertEqual(summary["accepted"], 5)

        broken = copy.deepcopy(rows)
        broken[0]["verification_status"] = "not_attempted"
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_base_lifecycle_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, broken)

    def test_reconciliation_rejects_invalid_base_with_attempted_dependents(self):
        bases = [base_row(1, admitted=False)]
        attempted = [variant_row(1, family_index) for family_index in range(1, 6)]
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_base_lifecycle_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, attempted)

    def test_reconciliation_rejects_family_index_drift(self):
        bases = [base_row(1, admitted=True)]
        rows = grid(bases)
        family_drift = copy.deepcopy(rows)
        family_drift[0]["family"] = "source_concentration"
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_family_position_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, family_drift)

    def test_reconciliation_rejects_noncanonical_slot_id(self):
        bases = [base_row(1, admitted=True)]
        rows = grid(bases)
        slot_drift = copy.deepcopy(rows)
        slot_drift[0]["slot_id"] = runner.v1.opaque_id(
            "SLT", "dreaddit_development", "wrong-packet", "unsupported_evidence"
        )
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_slot_id_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, slot_drift)

    def test_reconciliation_rejects_call_id_semantic_drift(self):
        bases = [base_row(1, admitted=True)]
        rows = grid(bases)
        rows[0]["verification_call_id"] = (
            "verify_dreaddit_development_packet_99_comparison_01_v2"
        )
        with self.assertRaisesRegex(runner.V2Error, "v2_variant_call_id_mismatch"):
            runner.reconcile_lane_funnel_v2(bases, rows)

    def test_invalid_base_creates_exactly_five_skips_without_calls(self):
        v1_config = runner.v1.load_json(runner.V1_CONFIG)
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_10000000"
            paths = {
                "item_schema": runner.v1.resolve_workspace_path(
                    v1_config["evaluator_item_schema_file"]
                )
            }
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(
                    runner.v1,
                    "invoke_checkpointed_call",
                    side_effect=AssertionError("dependent model call made"),
                ) as invoke,
            ):
                rows, truths, summary = runner.run_variant_and_comparison_phases_v2(
                    v1_config,
                    paths,
                    {"schema_construction_comparison": {}},
                    run_dir,
                    "dreaddit_development",
                    [base_row(1, admitted=False)],
                    [],
                )
            self.assertEqual(invoke.call_count, 0)
            self.assertEqual(len(rows), 5)
            self.assertEqual(summary["skipped_invalid_base"], 5)
            self.assertEqual(summary["attempted"], 0)
            self.assertEqual(truths, [])
            quarantine = run_dir / "quarantine" / "dreaddit_development"
            self.assertEqual(len(list(quarantine.glob("packet_01_variant_*.json"))), 5)

    def test_terminal_targeted_edits_are_quarantined_once_without_retry(self):
        v1_config = runner.v1.load_json(runner.V1_CONFIG)
        entry = admitted_entry()
        seen: list[tuple[str, bool]] = []

        def fake_call(*args, **kwargs):
            call_id = kwargs["call_id"]
            seen.append((call_id, kwargs["retry_transport_on_explicit_resume"]))
            if call_id.startswith("generate_"):
                return {
                    "status": "terminal_error",
                    "error": {"stage": "response_validation", "type": "SyntheticTerminal"},
                    "execution": {},
                }
            family_index = int(call_id.split("_comparison_")[1][:2])
            family = runner.FAMILY_ORDER[family_index - 1]
            positions = {
                "unsupported_evidence": [4],
                "source_concentration": [1, 2],
                "counterevidence_loss": [3],
            }[family]
            return {
                "status": "valid",
                "output": comparison_output(family, positions),
                "execution": {},
            }

        assets = {
            "prompt_contextual_flattening_edit": "synthetic",
            "schema_contextual_flattening_edit": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "contextual_flattening_edit_v2.schema.json"
            ),
            "prompt_unsupported_abstraction_edit": "synthetic",
            "schema_unsupported_abstraction_edit": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "unsupported_abstraction_edit_v2.schema.json"
            ),
            "prompt_construction_comparison": "synthetic",
            "schema_construction_comparison": runner.v1.load_json(
                runner.RQ2_ROOT / "schemas" / "construction_comparison_v2.schema.json"
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_20000000"
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(runner.v1, "invoke_checkpointed_call", side_effect=fake_call),
            ):
                rows, truths, summary = runner.run_variant_and_comparison_phases_v2(
                    v1_config,
                    {
                        "item_schema": runner.v1.resolve_workspace_path(
                            v1_config["evaluator_item_schema_file"]
                        )
                    },
                    assets,
                    run_dir,
                    "dreaddit_development",
                    [entry["row"]],
                    [entry],
                )
            targeted = [row for row in rows if row["family"] in runner.GENERATED_EDIT_FAMILIES]
            self.assertEqual(len(targeted), 2)
            self.assertTrue(all(row["construction_status"] == "generation_terminal" for row in targeted))
            self.assertTrue(all(row["fatal_terminal"] for row in targeted))
            self.assertEqual(summary["fatal_terminal"], 2)
            self.assertEqual(len(truths), 3)
            generator_calls = [call_id for call_id, _ in seen if call_id.startswith("generate_")]
            self.assertEqual(len(generator_calls), 2)
            self.assertEqual(len(generator_calls), len(set(generator_calls)))
            self.assertTrue(all(retry is False for _, retry in seen))

    def test_failed_gate_execution_never_enters_review_fixed_role_or_heldout(self):
        summary = runner.reconcile_lane_funnel_v2(
            [base_row(index, admitted=False) for index in range(1, 11)],
            grid([base_row(index, admitted=False) for index in range(1, 11)]),
        )
        failed_gate = {
            "run_outcome": "qualification_failed",
            "passed": False,
            "contains_source_text": False,
        }
        events: list[str] = []
        v1_config = {
            "policy_file_sha256": "a" * 64,
            "readiness_report_file_sha256": "b" * 64,
            "policy_validator_file_sha256": "c" * 64,
            "lanes": {
                "dreaddit_development": {
                    "corpus": "dreaddit",
                    "records_file_sha256": "d" * 64,
                    "split": "development_train",
                }
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "freeze.json"
            split_path = root / "split.json"
            config_path.write_text("{}\n", encoding="utf-8")
            split_path.write_text("{}\n", encoding="utf-8")
            run_dir = root / "rq2plv2_20260827T000000Z_30000000"
            paths = {
                "split_index": split_path,
                "records_dreaddit_development": root / "records-never-opened.jsonl",
            }

            def load_records(path, corpus, expected_hash, split, **kwargs):
                self.assertEqual(corpus, "dreaddit")
                self.assertEqual(split, "development_train")
                events.append("records:development")
                return []

            with (
                mock.patch.object(
                    runner,
                    "validate_v2_freeze",
                    return_value=(v1_config, paths, {}, set()),
                ),
                mock.patch.object(
                    runner.v1,
                    "run_exact_policy_validator",
                    return_value={
                        "policy_check_status": "passed",
                        "policy_sha256": "e" * 64,
                        "bound_input_hashes_verified": True,
                    },
                ),
                mock.patch.object(runner.v1, "preflight_service", return_value={"service": "synthetic"}),
                mock.patch.object(runner, "initialize_run_v2", return_value=run_dir),
                mock.patch.object(runner, "load_assets", return_value={key: {} for key in {
                    "prompt_base_generation", "schema_base_generation",
                    "prompt_base_admissibility", "schema_base_admissibility",
                    "rule_base_admissibility", "rule_family_edit_contract",
                    "prompt_contextual_flattening_edit", "schema_contextual_flattening_edit",
                    "prompt_unsupported_abstraction_edit", "schema_unsupported_abstraction_edit",
                    "prompt_construction_comparison", "schema_construction_comparison",
                    "rule_construction_comparison_acceptance",
                    "rule_construction_qualification_thresholds",
                }}),
                mock.patch.object(runner.v1, "recheck_service_identity"),
                mock.patch.object(runner.v1, "load_bound_records", side_effect=load_records),
                mock.patch.object(runner, "select_lane_packets_v2", return_value=([], set())),
                mock.patch.object(runner, "run_base_phase_v2", return_value=([], [])),
                mock.patch.object(
                    runner,
                    "run_variant_and_comparison_phases_v2",
                    return_value=([], [], summary),
                ),
                mock.patch.object(
                    runner,
                    "evaluate_development_qualification_v2",
                    side_effect=lambda *args: events.append("gate:failed") or failed_gate,
                ),
                mock.patch.object(
                    runner,
                    "write_qualification_analysis_v2",
                    side_effect=lambda *args: events.append("analysis") or {},
                ),
                mock.patch.object(
                    runner,
                    "seal_run_v2",
                    side_effect=lambda *args: events.append("seal") or {},
                ),
                mock.patch.object(
                    runner.v1,
                    "collect_role_lane_reviews",
                    side_effect=AssertionError("development review entered"),
                ),
                mock.patch.object(
                    runner.v1,
                    "freeze_fixed_role_checkpoint",
                    side_effect=AssertionError("fixed-role selection entered"),
                ),
            ):
                result = runner.execute_v2(config_path, "rq2plv2_20260827T000000Z_30000000")
            self.assertEqual(result, run_dir)
            self.assertEqual(events, ["records:development", "gate:failed", "analysis", "seal"])

    def test_accepted_set_is_preserved_while_reviews_remain_forbidden(self):
        bases = [base_row(index, admitted=True) for index in range(1, 7)]
        summary = runner.reconcile_lane_funnel_v2(bases, grid(bases))
        self.assertEqual(summary["accepted"], 30)
        self.assertEqual(summary["reviewed"], 0)
        self.assertEqual(summary["analyzed"], 0)
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_40000000"
            gate = {"run_outcome": "qualification_passed", "contains_source_text": False}
            operations = {"logical_calls_started": 0}
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(
                    runner.v1, "aggregate_call_attempt_operations", return_value=operations
                ),
            ):
                result = runner.write_qualification_analysis_v2(
                    {}, run_dir, summary, gate, {"contains_source_text": False}
                )
            self.assertEqual(result["funnel"]["accepted"], 30)
            self.assertEqual(result["reviewer_calls"], 0)
            self.assertFalse(result["fixed_role_selected"])
            self.assertFalse(result["heldout_lanes_opened"])
            self.assertFalse((run_dir / "observations").exists())

    def test_old_run_namespace_is_write_protected(self):
        old_run_target = (
            runner.WORKSPACE
            / "Storage"
            / "rq2_personal_local_diagnostic"
            / "rq2pl_20260827T015148Z_8f3c1a7b"
            / "adversarial-probe-never-written.json"
        )
        with self.assertRaisesRegex(runner.V2Error, "v2_path_escape"):
            runner.ensure_v2_path(old_run_target)

    def test_prior_commitments_are_excluded_before_selection(self):
        records = [
            {"record_id": f"REC_{index}", "source_id": f"SRC_{index}"}
            for index in range(1, 8)
        ]
        excluded = {runner.cluster_commitment(records[0], "dreaddit")}
        captured: list[dict] = []

        def fake_plan(filtered, **kwargs):
            captured.extend(filtered)
            return [{"packet_index": 1, "packet_id": "PKT_1"}]

        selected_commitment = runner.cluster_commitment(records[1], "dreaddit")
        packet_view = {
            "selection_cluster_commitments": [selected_commitment],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_50000000"
            with (
                mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root),
                mock.patch.object(runner.v1, "deterministic_packet_plan", side_effect=fake_plan),
                mock.patch.object(runner.v1, "source_free_selection_record", return_value=packet_view),
            ):
                _, commitments = runner.select_lane_packets_v2(
                    {
                        "sampling_seed": 1,
                        "excerpts_per_packet": 6,
                        "lanes": {
                            "dreaddit_development": {
                                "corpus": "dreaddit",
                                "split": "development_train",
                            }
                        },
                    },
                    {
                        "qualification_only": True,
                        "lane_packet_counts": {"dreaddit_development": 1},
                    },
                    run_dir,
                    "dreaddit_development",
                    records,
                    excluded_commitments=excluded,
                )
            self.assertNotIn(records[0], captured)
            self.assertTrue(commitments.isdisjoint(excluded))

    def test_exact_raw_call_set_rejects_extra_call_directory(self):
        bases = [base_row(index, admitted=False) for index in range(1, 11)]
        rows = grid(bases)
        summary = runner.reconcile_lane_funnel_v2(bases, rows)
        gate = {
            "run_outcome": "qualification_failed",
            "funnel_sha256": runner.v1.sha256_bytes(runner.v1.canonical_bytes(summary)),
        }
        mapping = {
            "construction/dreaddit_development_bases.json": {
                "planned": 10,
                "rows": bases,
            },
            "construction/dreaddit_development_variants.json": {
                "rows": rows,
                "summary": summary,
            },
            "qualification_gate.json": gate,
            "qualification_gate.seal.json": {
                "qualification_gate_sha256": "f" * 64,
                "run_outcome": "qualification_failed",
            },
            "analysis/qualification_results.json": {
                "funnel": summary,
                "qualification_gate": gate,
                "reviewer_calls": 0,
                "fixed_role_selected": False,
                "heldout_lanes_opened": False,
            },
            "run_terminal_status.json": {
                "run_outcome": "qualification_failed",
                "qualification_only": True,
            },
            "truth/dreaddit_development.private.json": {"records": []},
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "rq2plv2_20260827T000000Z_60000000"
            calls = run_dir / "raw" / "calls"
            calls.mkdir(parents=True)
            for row in bases:
                (calls / row["generation_call_id"]).mkdir()
            (calls / "generate_dreaddit_development_packet_99_base_v2").mkdir()

            def fake_load(path: Path):
                return mapping[path.relative_to(run_dir).as_posix()]

            with (
                mock.patch.object(runner.v1, "load_json", side_effect=fake_load),
                mock.patch.object(runner.v1, "sha256_file", return_value="f" * 64),
            ):
                with self.assertRaisesRegex(runner.V2Error, "v2_raw_call_id_set_mismatch"):
                    runner.validate_run_completeness_v2(run_dir, {})

    def test_ledger_and_gate_seal_tamper_are_rejected(self):
        bases = [base_row(index, admitted=False) for index in range(1, 11)]
        rows = grid(bases)
        summary = runner.reconcile_lane_funnel_v2(bases, rows)
        tampered_summary = copy.deepcopy(summary)
        tampered_summary["accepted"] = 1
        mapping = {
            "construction/dreaddit_development_bases.json": {"planned": 10, "rows": bases},
            "construction/dreaddit_development_variants.json": {
                "rows": rows,
                "summary": tampered_summary,
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "rq2plv2_20260827T000000Z_70000000"

            def fake_load(path: Path):
                return mapping[path.relative_to(run_dir).as_posix()]

            with mock.patch.object(runner.v1, "load_json", side_effect=fake_load):
                with self.assertRaisesRegex(runner.V2Error, "v2_variant_summary_drift"):
                    runner.validate_run_completeness_v2(run_dir, {})

        gate = {
            "run_outcome": "qualification_failed",
            "funnel_sha256": runner.v1.sha256_bytes(runner.v1.canonical_bytes(summary)),
        }
        mapping = {
            "construction/dreaddit_development_bases.json": {"planned": 10, "rows": bases},
            "construction/dreaddit_development_variants.json": {
                "rows": rows,
                "summary": summary,
            },
            "qualification_gate.json": gate,
            "qualification_gate.seal.json": {
                "qualification_gate_sha256": "0" * 64,
                "run_outcome": "qualification_failed",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "rq2plv2_20260827T000000Z_71000000"

            def fake_load(path: Path):
                return mapping[path.relative_to(run_dir).as_posix()]

            with (
                mock.patch.object(runner.v1, "load_json", side_effect=fake_load),
                mock.patch.object(runner.v1, "sha256_file", return_value="f" * 64),
            ):
                with self.assertRaisesRegex(runner.V2Error, "v2_gate_seal_drift"):
                    runner.validate_run_completeness_v2(run_dir, {})

    def test_output_seal_inventory_tamper_is_rejected(self):
        seal = {
            "document_type": "rq2_personal_local_v2_qualification_output_seal",
            "run_id": "rq2plv2_20260827T000000Z_80000000",
            "run_outcome": "qualification_failed",
            "result_label": runner.STATUS,
            "evidence_status": runner.EVIDENCE_STATUS,
            "sealed_at_utc": "synthetic",
            "files": [],
            "seal_payload_sha256": runner.v1.sha256_bytes(runner.v1.canonical_bytes([])),
            "qualification_gate_sha256": "a" * 64,
            "qualification_results_sha256": "b" * 64,
            "this_manifest_contains_source_text": False,
            "sealed_run_contains_restricted_source_text": True,
            "qualification_only": True,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
            "confirmatory_claims_allowed": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / seal["run_id"]

            def fake_load(path: Path):
                if path.name == "output_seal.json":
                    return seal
                if path.name == "qualification_gate.json":
                    return {"run_outcome": "qualification_failed"}
                raise AssertionError(path)

            with (
                mock.patch.object(runner.v1, "safe_exists", return_value=True),
                mock.patch.object(runner.v1, "load_json", side_effect=fake_load),
                mock.patch.object(
                    runner.v1,
                    "safe_run_inventory",
                    return_value=[{"path": "rogue.json", "size_bytes": 1, "sha256": "c" * 64}],
                ),
            ):
                with self.assertRaisesRegex(runner.V2Error, "v2_seal_inventory_or_hash_mismatch"):
                    runner.validate_output_seal_v2(run_dir, {})

    def test_source_free_quarantine_rejects_unbounded_reason_text(self):
        sentinel = "SYNTHETIC_SOURCE_SENTINEL_SHOULD_NEVER_ENTER_A_MANIFEST"
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_dir = output_root / "rq2plv2_20260827T000000Z_90000000"
            with mock.patch.object(runner, "V2_OUTPUT_ROOT", output_root):
                with self.assertRaisesRegex(runner.V2Error, "v2_reason_code_invalid"):
                    runner.write_quarantine(
                        run_dir,
                        lane_name="dreaddit_development",
                        packet_index=1,
                        packet_id="PKT_0000000000000001",
                        family_index=None,
                        family=None,
                        outcome="semantic_invalid",
                        reason_codes=[sentinel],
                        call_id=None,
                    )

    def test_positional_schemas_reject_opaque_or_source_identifiers(self):
        base_schema = runner.v1.load_json(
            runner.RQ2_ROOT / "schemas" / "base_generation_v2.schema.json"
        )
        generated = {
            "generation_schema_version": "rq2-base-generation-v2",
            "status": "constructed",
            "theme_name": "Synthetic theme",
            "claim": "Synthetic bounded claim",
            "explanation": "Synthetic explanation",
            "claim_scope": "displayed_packet_only",
            "role_plan": [
                {
                    "position": position,
                    "role": (
                        "support"
                        if position in (1, 2)
                        else "counterevidence"
                        if position == 3
                        else "context_only"
                    ),
                }
                for position in range(1, 7)
            ],
            "boundary_conditions": [
                {"counter_position": 3, "text": "Synthetic counter boundary"}
            ],
        }
        injected = copy.deepcopy(generated)
        injected["role_plan"][0]["excerpt_id"] = "EXC_0000000000000001"
        with self.assertRaises(runner.jsonschema.ValidationError):
            runner.jsonschema.validate(injected, base_schema)

        comparison_schema = runner.v1.load_json(
            runner.RQ2_ROOT / "schemas" / "construction_comparison_v2.schema.json"
        )
        output = comparison_output("unsupported_evidence", [4])
        output["anchors"][0]["source_id"] = "SRC_0000000000000001"
        with self.assertRaises(runner.jsonschema.ValidationError):
            runner.jsonschema.validate(output, comparison_schema)

    def test_comparison_request_is_target_blind(self):
        entry = admitted_entry()
        family = "unsupported_evidence"
        roles, interpretation, anchors = runner.deterministic_family_edit(family, entry)
        variant = runner.v1.build_item(
            lane_name="dreaddit_development",
            corpus="dreaddit",
            packet_id=entry["row"]["packet_id"],
            output_key="synthetic-target-blind",
            interpretation=interpretation,
            roles=roles,
            excerpts=entry["excerpts"],
        )
        signature = runner.construction_signature_v2(
            family, entry["base_item"], variant, anchors, entry["metadata"]
        )
        compact = runner.compact_comparison_input(entry, variant, signature)
        serialized = json.dumps(compact, sort_keys=True)
        self.assertTrue(compact["target_withheld"])
        self.assertNotIn("target_flaw", serialized)
        self.assertNotIn("family_index", serialized)
        self.assertNotIn(family, serialized)
        self.assertNotIn(runner.TARGET_REASON_CODE[family], serialized)
        self.assertNotIn("construction_note", serialized)
        self.assertNotIn("truth", serialized)
        self.assertNotIn("reviewer", serialized)

    def test_dry_run_and_preflight_never_open_records(self):
        original_read = runner.v1.read_regular_bytes
        record_reads: list[Path] = []

        def guarded_read(path: Path):
            if path.suffix == ".jsonl":
                record_reads.append(path)
                raise AssertionError("record file opened")
            return original_read(path)

        synthetic_v1 = {"synthetic": True}
        service = {
            "endpoint": "http://127.0.0.1:11434",
            "endpoint_is_numeric_loopback": True,
            "ollama_version": "synthetic",
            "models": {
                role: {"model_id": f"synthetic-{role}", "digest": "a" * 64}
                for role in ("generator", "reviewer", "verifier")
            },
        }
        for command in ("dry-run", "preflight-service"):
            with self.subTest(command=command):
                args = types.SimpleNamespace(config=runner.DEFAULT_CONFIG, command=command)
                output = io.StringIO()
                with (
                    mock.patch.object(runner, "parse_args", return_value=args),
                    mock.patch.object(runner.v1, "read_regular_bytes", side_effect=guarded_read),
                    mock.patch.object(
                        runner,
                        "validate_v2_freeze",
                        return_value=(synthetic_v1, {}, {}, set()),
                    ),
                    mock.patch.object(runner.v1, "preflight_service", return_value=service),
                    mock.patch.object(
                        runner.v1,
                        "load_bound_records",
                        side_effect=AssertionError("record loader called"),
                    ),
                    mock.patch("sys.stdout", output),
                ):
                    self.assertEqual(runner.main(), 0)
        self.assertEqual(record_reads, [])


if __name__ == "__main__":
    unittest.main()
