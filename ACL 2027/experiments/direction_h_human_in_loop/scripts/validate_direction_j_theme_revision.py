#!/usr/bin/env python3
"""Fail-closed validation for the synthetic Direction J theme-revision lane."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from serve_direction_j_browser import (
    ACTIVATION_PATH,
    BASE_FEEDBACK_SCHEMA_PATH,
    BROWSER_FEEDBACK_SCHEMA_PATH,
    DIRECTION_ROOT,
    J_ASSIGNMENT_PATH,
    J_ITEM_SCHEMA_PATH,
    J_ITEMS_PATH,
    J_RATING_SCHEMA_PATH,
    MANIFEST_PATH as BROWSER_MANIFEST_PATH,
    TIMING_SCHEMA_PATH,
    InstrumentError,
    load_json,
    sha256_file,
    validate_activation,
    validate_prepared,
)


THEME_ROOT = DIRECTION_ROOT / "companion_j_bridge" / "theme_revision"
SCHEMA_ROOT = THEME_ROOT / "schemas"
FREEZE_TEMPLATE_PATH = THEME_ROOT / "revision_freeze.template.json"
FREEZE_PATH = THEME_ROOT / "revision_freeze.json"
FIRST_STAGE_LOCK_PATH = (
    DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_first_stage_lock.json"
)
TARGET_VERIFICATION_PATH = THEME_ROOT / "coordinator_only" / "target_verification.json"
TARGET_BRIEFS_PATH = THEME_ROOT / "coordinator_only" / "target_briefs.json"
TARGET_COMMITMENT_PATH = (
    THEME_ROOT / "coordinator_only" / "target_brief_commitment.json"
)
TARGET_TEMPLATES = (
    (
        THEME_ROOT / "coordinator_only" / "target_verification.template.json",
        "target_verification.schema.json",
        "template_incomplete",
    ),
    (
        THEME_ROOT / "coordinator_only" / "target_briefs.template.json",
        "target_briefs.schema.json",
        "template_incomplete",
    ),
    (
        THEME_ROOT / "coordinator_only" / "target_brief_commitment.template.json",
        "target_brief_commitment.schema.json",
        "template_incomplete",
    ),
)
J_REPAIR_SCHEMA_PATH = (
    DIRECTION_ROOT.parent
    / "direction_j_llm_as_rater"
    / "schemas"
    / "repair_assessment.schema.json"
)


THEME_SCHEMAS = {
    path.name: path
    for path in SCHEMA_ROOT.glob("*.schema.json")
    if path.name != "first_stage_lock.schema.json"
}


def theme_store() -> dict[str, Any]:
    paths = list(THEME_SCHEMAS.values()) + [
        J_ITEM_SCHEMA_PATH,
        J_RATING_SCHEMA_PATH,
        J_REPAIR_SCHEMA_PATH,
        BASE_FEEDBACK_SCHEMA_PATH,
        BROWSER_FEEDBACK_SCHEMA_PATH,
        TIMING_SCHEMA_PATH,
        DIRECTION_ROOT / "schemas" / "direction_j_browser_first_stage_lock.schema.json",
    ]
    store: dict[str, Any] = {}
    for path in paths:
        schema = load_json(path, f"schema {path.name}")
        Draft202012Validator.check_schema(schema)
        if "$id" in schema:
            store[schema["$id"]] = schema
    return store


def validate_theme(value: Any, schema_name: str, label: str, store: dict[str, Any]) -> None:
    schema_path = THEME_SCHEMAS[schema_name]
    schema = load_json(schema_path, f"{label} schema")
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=store),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(
            f"/{'/'.join(str(part) for part in error.path)}: {error.message}"
            for error in errors[:8]
        )
        raise InstrumentError(f"{label} fails schema: {detail}")


EXPECTED_PATHS = {
    "upstream_direction_j.evaluator_items": (
        "experiments/direction_j_llm_as_rater/runs/"
        "20260825_synthetic_paired_qualification_prepared/evaluator_items.jsonl"
    ),
    "upstream_direction_j.charlie_assignment": (
        "experiments/direction_j_llm_as_rater/runs/"
        "20260825_synthetic_paired_qualification_prepared/assignments/charlie_rep1.csv"
    ),
    "upstream_direction_j.shared_rating_schema": (
        "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json"
    ),
    "upstream_direction_j.repair_assessment_schema": (
        "experiments/direction_j_llm_as_rater/schemas/repair_assessment.schema.json"
    ),
    "browser_first_stage.manifest": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/browser/manifest.json"
    ),
    "browser_first_stage.activation_record": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/browser/activation_record.json"
    ),
    "browser_first_stage.first_stage_lock": (
        "experiments/direction_h_human_in_loop/coordinator_only/"
        "direction_j_browser_first_stage_lock.json"
    ),
    "browser_first_stage.rating_schema": (
        "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json"
    ),
    "browser_first_stage.timing_schema": (
        "experiments/direction_h_human_in_loop/schemas/"
        "direction_j_browser_timing_receipt.schema.json"
    ),
    "browser_first_stage.feedback_schema": (
        "experiments/direction_h_human_in_loop/schemas/"
        "direction_j_browser_feedback.schema.json"
    ),
    "target_gate.verification": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "coordinator_only/target_verification.json"
    ),
    "target_gate.target_briefs": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "coordinator_only/target_briefs.json"
    ),
    "target_gate.target_brief_commitment": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "coordinator_only/target_brief_commitment.json"
    ),
    "revision_prompt": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "revision_prompt.md"
    ),
    "feedback_formatter.implementation": (
        "experiments/direction_h_human_in_loop/scripts/"
        "format_direction_j_theme_feedback.py"
    ),
    "schemas.case": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "schemas/revision_case.schema.json"
    ),
    "schemas.model_output": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "schemas/model_output.schema.json"
    ),
    "schemas.revision_output": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "schemas/revision_output.schema.json"
    ),
    "schemas.repair_panel_item": (
        "experiments/direction_h_human_in_loop/companion_j_bridge/theme_revision/"
        "schemas/repair_panel_item.schema.json"
    ),
    "software.validator": (
        "experiments/direction_h_human_in_loop/scripts/"
        "validate_direction_j_theme_revision.py"
    ),
    "software.case_builder": (
        "experiments/direction_h_human_in_loop/scripts/"
        "prepare_direction_j_theme_revision_cases.py"
    ),
    "software.output_recorder": (
        "experiments/direction_h_human_in_loop/scripts/"
        "record_direction_j_theme_revision.py"
    ),
}


def nested(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        current = current[part]
    return current


def project_path(relative: str) -> Path:
    project_root = DIRECTION_ROOT.parents[1]
    candidate = project_root / relative
    if candidate.is_symlink():
        raise InstrumentError(f"frozen path may not be a symlink: {relative}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise InstrumentError(f"frozen path leaves the project root: {relative}") from exc
    return resolved


def validate_freeze(path: Path, required_status: str) -> dict[str, Any]:
    store = theme_store()
    freeze = load_json(path, "theme revision freeze")
    validate_theme(freeze, "revision_freeze.schema.json", "theme revision freeze", store)
    if freeze["status"] != required_status:
        raise InstrumentError(
            f"theme revision freeze must have status {required_status}, not {freeze['status']}"
        )
    for dotted, expected in EXPECTED_PATHS.items():
        lock = nested(freeze, dotted)
        if lock["path"] != expected:
            raise InstrumentError(f"frozen path drifted: {dotted}")
        target = project_path(expected)
        if lock["sha256"] is None:
            if required_status == "frozen":
                raise InstrumentError(f"frozen hash is missing: {dotted}")
            continue
        if not target.is_file() or sha256_file(target) != lock["sha256"]:
            raise InstrumentError(f"frozen artifact drifted or is absent: {dotted}")
    if required_status == "frozen":
        for field in ("provider", "model_id", "snapshot_id", "runtime_surface"):
            if not freeze["revision_model"][field]:
                raise InstrumentError(f"frozen revision model lacks {field}")
    return freeze


def ensure_no_live_outputs() -> None:
    output_roots = [
        THEME_ROOT / "cases",
        THEME_ROOT / "revision_outputs",
        THEME_ROOT / "repair_panel",
        THEME_ROOT / "repair_assessments",
        THEME_ROOT / "results",
    ]
    for root in output_roots:
        if not root.exists():
            continue
        unexpected = [entry for entry in root.iterdir() if entry.name != "README.md"]
        if unexpected:
            raise InstrumentError(f"prepared theme lane contains live artifacts: {root.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the synthetic exact-Direction-J theme revision extension."
    )
    parser.add_argument(
        "--prepared-only",
        action="store_true",
        help="Validate the draft contract and zero-output state without requiring review lock/freeze.",
    )
    args = parser.parse_args()
    try:
        prepared = validate_prepared()
        if args.prepared_only:
            validate_freeze(FREEZE_TEMPLATE_PATH, "draft_template")
            store = theme_store()
            for path, schema_name, expected_status in TARGET_TEMPLATES:
                value = load_json(path, f"theme gate template {path.name}")
                validate_theme(value, schema_name, f"theme gate template {path.name}", store)
                if value["status"] != expected_status:
                    raise InstrumentError(f"theme gate template is not incomplete: {path.name}")
            for live_path in (
                FREEZE_PATH,
                TARGET_VERIFICATION_PATH,
                TARGET_BRIEFS_PATH,
                TARGET_COMMITMENT_PATH,
            ):
                if live_path.exists():
                    raise InstrumentError(
                        f"prepared-only lane unexpectedly contains a live gate: {live_path.name}"
                    )
            ensure_no_live_outputs()
            result = {
                "status": "valid_prepared_not_frozen_or_run",
                "synthetic_items": len(prepared["assignments"]),
                "contains_real_source_text": False,
                "browser_responses": prepared["completed_count"],
                "revision_cases": 0,
                "revision_outputs": 0,
                "repair_assessments": 0,
                "empirical_results": 0,
            }
        else:
            validate_activation(prepared)
            validate_freeze(FREEZE_PATH, "frozen")
            result = {
                "status": "valid_frozen",
                "synthetic_items": len(prepared["assignments"]),
                "contains_real_source_text": False,
                "browser_responses": prepared["completed_count"],
            }
        print(json.dumps(result, sort_keys=True))
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
