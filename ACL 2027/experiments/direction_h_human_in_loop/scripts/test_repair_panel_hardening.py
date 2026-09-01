#!/usr/bin/env python3
"""Ephemeral regression checks for repair-panel disclosure and isolation gates.

The checks use only the checked-in fictional pilot item and temporary
directories. They deliberately stop before collection and create no study
bundle, assessment, rating, lock, or result in the workspace.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_repair_assessor_assignments as assignments  # noqa: E402
import lock_repair_assessments as assessment_lock  # noqa: E402
import prepare_repair_panel as panel  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def disclosure_checks() -> None:
    freeze = {
        "revision_model": {
            "model_id": "frozen-model-2026",
            "snapshot_id": "snapshot-immutable-01",
        }
    }
    evidence = {"context_note": "Ordinary discussion of feedback is allowed."}
    original = {"analysis_summary": "The participant moved an arm after a lesson."}

    findings = panel.disclosure_screen_findings(
        {"analysis_summary": "I used Charlie_feedback for this revision."},
        evidence,
        original,
        freeze,
    )
    require(any(row["code"] == "feedback_arm_label" for row in findings), "arm label missed")

    findings = panel.disclosure_screen_findings(
        {"analysis_summary": "As an AI language model, I revised this answer."},
        evidence,
        original,
        freeze,
    )
    require(
        any(row["code"] == "model_self_identification" for row in findings),
        "model self-identification missed",
    )
    named_model = panel.disclosure_screen_findings(
        {"analysis_summary": "I am ChatGPT and revised this output."},
        evidence,
        original,
        freeze,
    )
    require(
        any(row["code"] == "model_self_identification" for row in named_model),
        "named model self-identification missed",
    )

    inherited_evidence = {
        "excerpts": [{"text": "As an AI language model, I cannot feel fatigue."}]
    }
    inherited = panel.disclosure_screen_findings(
        {"negative_cases": [{"quote": "As an AI language model, I cannot feel fatigue."}]},
        inherited_evidence,
        original,
        freeze,
    )
    require(
        not any(row["code"] == "model_self_identification" for row in inherited),
        "inherited exact source phrase was misclassified",
    )

    ordinary = panel.disclosure_screen_findings(
        {"analysis_summary": "The participant adjusted her arm after feedback from a coach."},
        evidence,
        original,
        freeze,
    )
    require(not ordinary, f"ordinary content triggered the screen: {ordinary}")

    exact_model = panel.disclosure_screen_findings(
        {"analysis_summary": "This was produced with frozen-model-2026."},
        evidence,
        original,
        freeze,
    )
    require(
        any(row["code"] == "frozen_model_id_disclosure" for row in exact_model),
        "frozen model identity missed",
    )

    record = {
        "revision_output_id": "fixture-output",
        "revised_output": {"analysis_summary": "No-feedback arm."},
    }
    case = {"model_input": {"evidence_packet": evidence, "original_output": original}}
    try:
        panel.screen_revised_output_disclosures(record, case, freeze)
    except panel.PackagingError as exc:
        require("protocol deviation" in str(exc), "blocked disclosure lacks deviation diagnostic")
        require("do not redact" in str(exc), "blocked disclosure lacks frozen handling")
    else:
        raise AssertionError("disclosure screen did not fail closed")


def assigned_item() -> dict:
    source = assignments.load_json(
        assignments.PILOT_ROOT / "items" / "DHQ-001.json", "fictional pilot fixture"
    )
    candidate = copy.deepcopy(source["candidate_output"])
    return {
        "repair_panel_item_version": "direction-h-repair-panel-item-v1",
        "study_id": source["study_id"],
        "task_id": "RAT-" + "B" * 20,
        "blinded_revision_id": "RAI-" + "A" * 20,
        "packet_id": source["packet_id"],
        "corpus_id": source["corpus_id"],
        "starting_output_id": source["output_id"],
        "evaluation_role": source["evaluation_role"],
        "data_classification": "synthetic_cc0",
        "evidence_packet": source["evidence_packet"],
        "original_output": candidate,
        "revised_output": candidate,
        "target_assessment_reference_id": "RAREF-" + "C" * 20,
        "target_assessment_brief": (
            "Assess whether the stated target issue is repaired while warranted material is preserved."
        ),
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(assignments.rendered_bytes(value))


def build_ephemeral_bundle(root: Path) -> tuple[str, str, str]:
    item = assigned_item()
    assignments.validate(item, assignments.PANEL_ITEM_SCHEMA, "ephemeral assigned item")
    item_relative = f"items/{item['blinded_revision_id']}.json"
    item_payload = assignments.rendered_bytes(item)
    (root / "items").mkdir(parents=True)
    (root / item_relative).write_bytes(item_payload)

    instruments = assignments.instrument_hashes()
    for label, relative in assignments.RUNTIME_PACKAGE_PATHS.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(assignments.INSTRUMENT_PATHS[label], target)
        require(assignments.sha256_file(target) == instruments[label], f"runtime copy drift: {label}")

    row = {
        "display_order": 1,
        "blinded_revision_id": item["blinded_revision_id"],
        "task_id": item["task_id"],
        "corpus_id": item["corpus_id"],
        "packet_id": item["packet_id"],
        "starting_output_id": item["starting_output_id"],
        "evaluation_role": item["evaluation_role"],
        "target_assessment_reference_id": item["target_assessment_reference_id"],
        "data_classification": item["data_classification"],
        "repair_panel_item_version": item["repair_panel_item_version"],
        "item_file": item_relative,
        "sha256": assignments.sha256_bytes(item_payload),
    }
    study_id = item["study_id"]
    schedule_id = "RASCH-" + "D" * 20
    bundle_id = root.name
    assessor_alias = "RAA-" + "F" * 20
    evaluator_group = "researcher"
    rater_id = "independent_reviewer_01"
    token = "a" * 64
    payload = {
        "assignment_payload_version": "direction-h-repair-assignment-payload-v1",
        "study_id": study_id,
        "schedule_id": schedule_id,
        "bundle_id": bundle_id,
        "assessor_alias": assessor_alias,
        "evaluator_group": evaluator_group,
        "parent_panel_manifest_sha256": "0" * 64,
        "frozen_instrument_hashes": instruments,
        "items": [row],
    }
    payload_hash = assignments.sha256_bytes(assignments.canonical_bytes(payload))
    manifest = {
        "bundle_manifest_version": "direction-h-repair-assessor-bundle-v1",
        "study_id": study_id,
        "schedule_id": schedule_id,
        "bundle_id": bundle_id,
        "assessor_alias": assessor_alias,
        "evaluator_group": evaluator_group,
        "data_scope": "synthetic_only",
        "contains_real_source_text": False,
        "created_at_utc": "2026-08-25T12:00:00Z",
        "parent_panel_manifest_sha256": "0" * 64,
        "frozen_instrument_hashes": instruments,
        "assignment_payload_sha256": payload_hash,
        "assignment_token_hash_method": "sha256_utf8_nul_direction_h_assignment_token_v1",
        "assignment_token_sha256": assignments.nul_hash(
            "direction-h-assignment-token-v1", study_id, schedule_id, bundle_id, token
        ),
        "rater_binding_hash_method": "sha256_utf8_nul_direction_h_rater_binding_v1",
        "rater_binding_sha256": assignments.nul_hash(
            "direction-h-rater-binding-v1",
            study_id,
            schedule_id,
            bundle_id,
            rater_id,
            evaluator_group,
            payload_hash,
            token,
        ),
        "item_count": 1,
        "items": [row],
    }
    assignments.validate(manifest, assignments.BUNDLE_SCHEMA, "ephemeral bundle manifest")
    write_json(root / "manifest.json", manifest)
    return token, rater_id, evaluator_group


def run_collector(
    collector: Path,
    root: Path,
    token: str,
    rater_id: str,
    evaluator_group: str,
    blind_id: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(collector),
            "--bundle-root",
            str(root),
            "--manifest",
            str(root / "manifest.json"),
            "--rater-id",
            rater_id,
            "--evaluator-group",
            evaluator_group,
            "--assignment-token",
            token,
            "--blind-id",
            blind_id,
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def isolation_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="direction_h_repair_hardening_") as temporary:
        temp_root = Path(temporary)
        bundle = temp_root / ("RAB-" + "E" * 20)
        bundle.mkdir()
        token, rater_id, evaluator_group = build_ephemeral_bundle(bundle)
        portable_collector = bundle / assignments.RUNTIME_PACKAGE_PATHS[
            "repair_assessment_collector_script_sha256"
        ]

        manifest = assignments.load_json(bundle / "manifest.json", "ephemeral manifest")
        manifest_row = manifest["items"][0]
        tree_map = {
            str(file.relative_to(bundle)): assignments.sha256_file(file)
            for file in bundle.rglob("*")
            if file.is_file()
        }
        reviewer = {
            "rater_id": rater_id,
            "evaluator_group": evaluator_group,
            "assessor_alias": manifest["assessor_alias"],
            "bundle_id": manifest["bundle_id"],
            "assignment_token": token,
            "assignment_token_sha256": manifest["assignment_token_sha256"],
            "rater_binding_sha256": manifest["rater_binding_sha256"],
            "bundle_manifest_sha256": assignments.sha256_file(bundle / "manifest.json"),
            "bundle_tree_sha256": assignments.sha256_bytes(
                assignments.canonical_bytes(dict(sorted(tree_map.items())))
            ),
            "workload_count": 1,
            "assignments": [
                {
                    "assigned_blinded_revision_id": manifest_row["blinded_revision_id"],
                    "assigned_task_id": manifest_row["task_id"],
                    "assigned_target_assessment_reference_id": manifest_row[
                        "target_assessment_reference_id"
                    ],
                    "corpus_id": manifest_row["corpus_id"],
                    "assigned_item_sha256": manifest_row["sha256"],
                }
            ],
        }
        schedule = {
            "study_id": manifest["study_id"],
            "schedule_id": manifest["schedule_id"],
        }
        locked_manifest, locked_items, locked_root = assessment_lock.verify_bundle(
            schedule,
            reviewer,
            bundle.parent,
            manifest["frozen_instrument_hashes"],
        )
        require(locked_manifest == manifest, "coordinator lock changed the bundle manifest")
        require(
            set(locked_items) == {manifest_row["blinded_revision_id"]},
            "coordinator lock did not recover the exact assigned item",
        )
        require(
            locked_root == bundle.resolve(),
            "coordinator lock resolved the wrong bundle root",
        )

        authorized = run_collector(
            portable_collector,
            bundle,
            token,
            rater_id,
            evaluator_group,
            "RAI-" + "9" * 20,
        )
        require(authorized.returncode != 0, "unknown test blind ID unexpectedly collected")
        require(
            "Unknown blinded revision ID" in authorized.stderr + authorized.stdout,
            "portable runtime did not reach the authorized isolated assignment gate",
        )
        require(not (bundle / "responses").exists(), "authorized dry check wrote responses")

        invalid_token = run_collector(
            portable_collector,
            bundle,
            "b" * 64,
            rater_id,
            evaluator_group,
            "RAI-" + "A" * 20,
        )
        require(invalid_token.returncode != 0, "invalid token unexpectedly authorized")
        require(
            "Invalid assignment token" in invalid_token.stderr + invalid_token.stdout,
            "invalid-token diagnostic missing",
        )
        require(not (bundle / "responses").exists(), "invalid-token path wrote responses")

        drifted_schema = bundle / assignments.RUNTIME_PACKAGE_PATHS[
            "repair_assessment_schema_sha256"
        ]
        drifted_schema.write_bytes(drifted_schema.read_bytes() + b"\n")
        drifted = run_collector(
            portable_collector,
            bundle,
            token,
            rater_id,
            evaluator_group,
            "RAI-" + "A" * 20,
        )
        require(drifted.returncode != 0, "drifted runtime unexpectedly authorized")
        require(
            "hash-drifted" in drifted.stderr + drifted.stdout
            or "instrument has drifted" in drifted.stderr + drifted.stdout,
            "runtime-drift diagnostic missing",
        )
        require(not (bundle / "responses").exists(), "runtime-drift path wrote responses")

        staging = temp_root / ("RAB-" + "1" * 20)
        staging.mkdir()
        write_json(
            staging / "manifest.json",
            {"manifest_version": "direction-h-repair-panel-manifest-v1"},
        )
        staging_check = run_collector(
            assignments.REPAIR_COLLECTOR,
            staging,
            token,
            rater_id,
            evaluator_group,
            "RAI-" + "A" * 20,
        )
        require(staging_check.returncode != 0, "full staging manifest unexpectedly authorized")
        require(
            "full repair-panel staging manifest" in staging_check.stderr + staging_check.stdout,
            "full-staging rejection diagnostic missing",
        )
        require(not (staging / "responses").exists(), "staging rejection wrote responses")


def main() -> int:
    disclosure_checks()
    isolation_checks()
    print(
        json.dumps(
            {
                "status": "repair_panel_hardening_checks_passed",
                "fixture_scope": "temporary_synthetic_only",
                "live_assessments_created": 0,
                "live_results_created": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
