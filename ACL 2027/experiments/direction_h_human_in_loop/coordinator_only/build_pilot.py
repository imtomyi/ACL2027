#!/usr/bin/env python3
"""Build the synthetic-only Direction H workflow-qualification pilot.

Coordinator-only: this file discloses the planted-defect conditions. It reads
only the CC0 synthetic benchmark's blinded output bundles. It never reads a
real, de-identified, raw, or deployed-app item bank.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
RUN_ROOT = BASELINE_ROOT / "runs" / "20260825_synthetic_qualification"
BLINDED_ROOT = RUN_ROOT / "blinded"
PILOT_ROOT = DIRECTION_ROOT / "pilot"
ITEM_ROOT = PILOT_ROOT / "items"
STUDY_ID = "direction-h-synthetic-pilot-v1"
CREATED_AT = "2026-08-25T00:00:00-05:00"
ORDER_SEED = "direction-h-charlie-pilot-order-v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def select_candidate(packet_id: str, run_index: int, blind_id: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
    bundle_path = BLINDED_ROOT / f"{packet_id}_run{run_index}.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle["packet_id"] != packet_id or int(bundle["run_index"]) != run_index:
        raise ValueError(f"bundle identity mismatch: {bundle_path}")
    matches = [c for c in bundle["candidates"] if c["blind_id"] == blind_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {blind_id} in {bundle_path}")
    return copy.deepcopy(bundle["packet"]), copy.deepcopy(matches[0]["output"]), bundle_path


def no_planted_defect(output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    return output, None


def plant_unsupported_abstraction(output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    theme = next((t for t in output["themes"] if t["theme_id"] == "T02"), None)
    if not theme or "graded rather than uniform" not in theme["name"].lower():
        raise ValueError("unexpected Dreaddit source output; refusing to plant defect")
    original = theme["claim"]
    theme["claim"] = (
        "Interpersonal help, routines, humor, boundaries, sequencing, and "
        "institutional resolution reliably reduce stress for people facing hardship."
    )
    return output, {
        "target_flag": "unsupported_abstraction",
        "primary_construct": "scope_calibration",
        "target_location": "candidate_output.themes[T02].claim",
        "original_value_sha256": sha256_bytes(original.encode("utf-8")),
        "transformation": (
            "Replaced a packet-bounded, graded claim with a population-level, "
            "uniform effectiveness claim while leaving the cited excerpts unchanged."
        ),
    }


def plant_unsupported_inference(output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    theme = next((t for t in output["themes"] if t["theme_id"] == "T01"), None)
    if not theme or "accountable next steps" not in theme["name"].lower():
        raise ValueError("unexpected KODIS source output; refusing to plant defect")
    original = theme["claim"]
    theme["claim"] = original.rstrip(".") + " because clear options lower defensiveness."
    return output, {
        "target_flag": "unsupported_inference",
        "primary_construct": "evidential_credibility",
        "target_location": "candidate_output.themes[T01].claim",
        "original_value_sha256": sha256_bytes(original.encode("utf-8")),
        "transformation": (
            "Added an unobserved causal mechanism about internal defensiveness to an "
            "otherwise source-linked interactional claim."
        ),
    }


def plant_lost_negative_case(output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target_excerpt = "AG_E10"
    theme = next((t for t in output["themes"] if t["theme_id"] == "T01"), None)
    if not theme:
        raise ValueError("unexpected AGYW source output; missing T01")
    counter_before = len(theme["counterevidence"])
    theme["counterevidence"] = [
        row for row in theme["counterevidence"] if row["excerpt_id"] != target_excerpt
    ]
    if len(theme["counterevidence"]) != counter_before - 1:
        raise ValueError("expected AG_E10 counterevidence exactly once")
    support_theme = next((t for t in output["themes"] if t["theme_id"] == "T02"), None)
    replacement = next(
        (
            copy.deepcopy(row)
            for row in (support_theme or {}).get("evidence", [])
            if row["excerpt_id"] == "AG_E07"
        ),
        None,
    )
    if not replacement:
        raise ValueError("expected AG_E07 evidence for schema-valid countercase replacement")
    replacement["warrant"] = (
        "Adjusted timing and a private door show that a tailored service change can "
        "make an otherwise difficult route usable."
    )
    theme["counterevidence"] = [replacement]
    theme["boundary_conditions"] = [
        boundary
        for boundary in theme["boundary_conditions"]
        if "not evidence that every participant" not in boundary
    ]
    if not theme["boundary_conditions"]:
        raise ValueError("lost all T01 boundary conditions")
    theme["source_ids"] = [sid for sid in theme["source_ids"] if sid != "AG_FGD_07"]
    if replacement["source_id"] not in theme["source_ids"]:
        theme["source_ids"].append(replacement["source_id"])
    negatives_before = len(output["negative_cases"])
    output["negative_cases"] = [
        row for row in output["negative_cases"] if row["excerpt_id"] != target_excerpt
    ]
    if len(output["negative_cases"]) != negatives_before - 1:
        raise ValueError("expected AG_E10 negative case exactly once")
    assignment = next(
        (row for row in output["assignments"] if row["excerpt_id"] == target_excerpt),
        None,
    )
    if not assignment:
        raise ValueError("expected AG_E10 assignment")
    assignment["code_ids"] = []
    assignment["not_coded"] = True
    assignment["rationale"] = (
        "This continuity account is outside the cross-case interpretation retained here."
    )
    original_summary = output["analysis_summary"]
    output["analysis_summary"] = (
        "Participants describe schooling and health-information access as constrained by "
        "income needs, transport and data costs, shared devices, care and household duties, "
        "conflicting schedules, and anticipated observation. Supports include friends "
        "sharing notes, peer information, and adjusted appointment conditions. The exchange "
        "also contests an adult framing of disrupted schooling as lost focus, replacing it "
        "in one participant's account with care, money, and time constraints."
    )
    return output, {
        "target_flag": "lost_negative_case",
        "primary_construct": "voice_boundary_preservation",
        "target_location": (
            "candidate_output.analysis_summary; assignments[AG_E10]; "
            "themes[T01].counterevidence; negative_cases[AG_E10]"
        ),
        "original_value_sha256": sha256_bytes(original_summary.encode("utf-8")),
        "transformation": (
            "Removed a materially supported continuity case from the summary, theme "
            "counterevidence, boundary condition, negative-case inventory, and coding."
        ),
    }


Transform = Callable[[dict[str, Any]], tuple[dict[str, Any], dict[str, Any] | None]]


# Exactly one output is shown per synthetic evidence packet. The source candidates
# were selected from integrity-gate-passing blinded bundles. No model name is
# copied into any public pilot artifact.
SELECTIONS: list[dict[str, Any]] = [
    {
        "task_id": "DHQ-001",
        "display_order": 4,
        "packet_id": "syn_candor_01",
        "corpus_id": "synthetic_candor_proxy",
        "run_index": 1,
        "blind_id": "B2",
        "output_id": "DHO-K7R4",
        "transform": no_planted_defect,
        "condition": "no_planted_defect_control",
    },
    {
        "task_id": "DHQ-002",
        "display_order": 2,
        "packet_id": "syn_kodis_01",
        "corpus_id": "synthetic_kodis_proxy",
        "run_index": 3,
        "blind_id": "B2",
        "output_id": "DHO-P2M9",
        "transform": plant_unsupported_inference,
        "condition": "controlled_defect",
    },
    {
        "task_id": "DHQ-003",
        "display_order": 3,
        "packet_id": "syn_dreaddit_01",
        "corpus_id": "synthetic_dreaddit_proxy",
        "run_index": 1,
        "blind_id": "B3",
        "output_id": "DHO-V8C3",
        "transform": plant_unsupported_abstraction,
        "condition": "controlled_defect",
    },
    {
        "task_id": "DHQ-004",
        "display_order": 1,
        "packet_id": "syn_agyw_01",
        "corpus_id": "synthetic_agyw_proxy",
        "run_index": 1,
        "blind_id": "B3",
        "output_id": "DHO-F5N1",
        "transform": plant_lost_negative_case,
        "condition": "controlled_defect",
    },
]


def main() -> int:
    expected_task_order = sorted(
        (spec["task_id"] for spec in SELECTIONS),
        key=lambda task_id: hashlib.sha256(
            f"{ORDER_SEED}|{task_id}".encode("utf-8")
        ).hexdigest(),
    )
    actual_task_order = [
        spec["task_id"] for spec in sorted(SELECTIONS, key=lambda row: row["display_order"])
    ]
    if actual_task_order != expected_task_order:
        raise SystemExit("Frozen pilot presentation order does not match its SHA-256 seed rule")
    protected_targets = [
        PILOT_ROOT / "manifest.json",
        PILOT_ROOT / "task_index.csv",
        PILOT_ROOT / "condition_commitment.json",
        DIRECTION_ROOT / "coordinator_only" / "truth_map.json",
        *(ITEM_ROOT / f"{spec['task_id']}.json" for spec in SELECTIONS),
    ]
    existing = [path for path in protected_targets if path.exists()]
    if existing:
        raise SystemExit(
            "Refusing to overwrite an existing committed pilot artifact: "
            + ", ".join(str(path.relative_to(DIRECTION_ROOT)) for path in existing)
        )
    ITEM_ROOT.mkdir(parents=True, exist_ok=True)
    public_rows: list[dict[str, Any]] = []
    public_items: list[dict[str, Any]] = []
    truth_items: list[dict[str, Any]] = []

    for spec in SELECTIONS:
        packet, source_output, bundle_path = select_candidate(
            spec["packet_id"], spec["run_index"], spec["blind_id"]
        )
        source_output_hash = sha256_bytes(canonical_bytes(source_output))
        transformed_output, planted = spec["transform"](copy.deepcopy(source_output))
        item = {
            "pilot_item_version": "direction-h-pilot-item-v1",
            "study_id": STUDY_ID,
            "task_id": spec["task_id"],
            "display_order": spec["display_order"],
            "packet_id": spec["packet_id"],
            "corpus_id": spec["corpus_id"],
            "evaluation_role": "development",
            "output_id": spec["output_id"],
            "data_classification": "synthetic_cc0",
            "evidence_packet": packet,
            "candidate_output": transformed_output,
        }
        item_path = ITEM_ROOT / f"{spec['task_id']}.json"
        write_json(item_path, item)
        item_hash = sha256_file(item_path)
        public_items.append(
            {
                "task_id": spec["task_id"],
                "display_order": spec["display_order"],
                "packet_id": spec["packet_id"],
                "corpus_id": spec["corpus_id"],
                "evaluation_role": "development",
                "output_id": spec["output_id"],
                "item_file": f"items/{spec['task_id']}.json",
                "sha256": item_hash,
                "evidence_packet_sha256": sha256_bytes(canonical_bytes(packet)),
                "candidate_output_sha256": sha256_bytes(canonical_bytes(transformed_output)),
            }
        )
        public_rows.append(
            {
                "display_order": spec["display_order"],
                "task_id": spec["task_id"],
                "packet_id": spec["packet_id"],
                "corpus_id": spec["corpus_id"],
                "evaluation_role": "development",
                "output_id": spec["output_id"],
                "item_file": f"items/{spec['task_id']}.json",
                "review_status": "not_started",
            }
        )
        truth_items.append(
            {
                "task_id": spec["task_id"],
                "packet_id": spec["packet_id"],
                "output_id": spec["output_id"],
                "source_bundle": str(bundle_path.relative_to(PROJECT_ROOT)),
                "source_bundle_sha256": sha256_file(bundle_path),
                "source_blind_id": spec["blind_id"],
                "source_output_sha256": source_output_hash,
                "condition": spec["condition"],
                "planted_defect": planted,
                "background_error_status": (
                    "not_universal_clean_truth; source candidate passed deterministic "
                    "integrity gates, but interpretive adequacy remains reviewable"
                ),
            }
        )

    schema_path = BASELINE_ROOT / "schemas" / "paper_metric_rating.schema.json"
    contract_path = BASELINE_ROOT / "protocol" / "paper_metric_data_contract.md"
    benchmark_path = BASELINE_ROOT / "benchmark" / "synthetic_packets_v1.json"
    manifest = {
        "manifest_version": "direction-h-pilot-manifest-v1",
        "study_id": STUDY_ID,
        "created_at": CREATED_AT,
        "status": "ready_for_synthetic_workflow_qualification",
        "data_scope": "synthetic_only",
        "contains_real_source_text": False,
        "intended_rater_id": "charlie_dev_researcher_01",
        "intended_evaluator_group": "researcher",
        "case_role": "developer_researcher",
        "primary_analysis_inclusion": "case_only_exclude_from_independent_human_pool",
        "canonical_rating_contract": {
            "annotation_version": "qc-paper-metrics-v1",
            "schema_path": str(schema_path.relative_to(PROJECT_ROOT)),
            "schema_sha256": sha256_file(schema_path),
            "contract_path": str(contract_path.relative_to(PROJECT_ROOT)),
            "contract_sha256": sha256_file(contract_path),
        },
        "synthetic_source": {
            "benchmark_path": str(benchmark_path.relative_to(PROJECT_ROOT)),
            "benchmark_sha256": sha256_file(benchmark_path),
            "benchmark_license": "CC0-1.0",
            "source_run_provenance": "coordinator_only",
        },
        "blinding": {
            "hidden_from_rater": [
                "model_identity",
                "source_run_index",
                "source_blind_id",
                "condition",
                "planted_defect_family",
                "historical_automatic_or_judge_results",
                "other_ratings",
                "revision_outcomes",
            ],
            "one_item_per_evidence_packet": True,
            "ratings_locked_before_unblinding": True,
        },
        "presentation_order": {
            "method": "ascending_sha256(seed|task_id)",
            "seed": ORDER_SEED,
            "frozen_before_review": True,
        },
        "task_count": len(public_items),
        "tasks": public_items,
        "outcome_status": "not_collected",
        "interpretation_limit": (
            "Synthetic developer-researcher case baseline only; not universal human "
            "ground truth and not an estimate of independent reviewer performance."
        ),
    }
    write_json(PILOT_ROOT / "manifest.json", manifest)

    index_path = PILOT_ROOT / "task_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(public_rows[0]))
        writer.writeheader()
        writer.writerows(sorted(public_rows, key=lambda row: row["display_order"]))

    truth_map = {
        "truth_map_version": "direction-h-synthetic-truth-v1",
        "study_id": STUDY_ID,
        "created_at": CREATED_AT,
        "access": "coordinator_only_until_ratings_and_feedback_lock",
        "label_semantics": (
            "Labels identify only predeclared synthetic manipulations. They do not assert "
            "that an unmodified output is universally correct or that no other defensible "
            "errors exist."
        ),
        "items": truth_items,
    }
    truth_path = DIRECTION_ROOT / "coordinator_only" / "truth_map.json"
    write_json(truth_path, truth_map)
    commitment = {
        "commitment_version": "direction-h-condition-commitment-v1",
        "study_id": STUDY_ID,
        "algorithm": "sha256(canonical-json-with-final-newline)",
        "truth_map_sha256": sha256_bytes(canonical_bytes(truth_map)),
        "committed_at": CREATED_AT,
        "unblind_rule": (
            "Open only after all core ratings and feedback records validate and their "
            "lock manifest has been written."
        ),
    }
    write_json(PILOT_ROOT / "condition_commitment.json", commitment)
    print(
        json.dumps(
            {
                "study_id": STUDY_ID,
                "items_written": len(public_items),
                "contains_real_source_text": False,
                "ratings_written": 0,
                "outcomes_written": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
