#!/usr/bin/env python3
"""Collect one authorized arm-blind repair assessment and shared artifact rating.

This collector accepts only one token-bound, reviewer-specific assignment
bundle and the item files it names.  It rejects the coordinator staging panel
and never reads the private schedule, arm map, truth map, revision diagnoses,
or Charlie's feedback records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver
except ModuleNotFoundError:
    candidates = [
        Path.home() / "miniconda3" / "bin" / "python3",
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
    ]
    for candidate in candidates:
        if not candidate.is_file() or candidate.resolve() == Path(sys.executable).resolve():
            continue
        probe = subprocess.run(
            [str(candidate), "-c", "import jsonschema"],
            capture_output=True,
            check=False,
        )
        if probe.returncode == 0:
            os.execv(str(candidate), [str(candidate), __file__, *sys.argv[1:]])
    raise SystemExit(
        "This collector needs the Python 'jsonschema' package. No local Python "
        "runtime containing it was found; no assessment was written."
    )


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
PORTABLE_SCHEMA_ROOT = SCRIPT_DIR / "schemas"
PORTABLE_RUNTIME = (
    SCRIPT_DIR.name == "runtime"
    and (PORTABLE_SCHEMA_ROOT / "repair_panel_item.schema.json").is_file()
    and (PORTABLE_SCHEMA_ROOT / "repair_assessor_bundle.schema.json").is_file()
)

if PORTABLE_RUNTIME:
    # In an exported RAB-* bundle, the collector and every schema it uses live
    # together under runtime/. No shared checkout or coordinator file is needed.
    DIRECTION_ROOT = SCRIPT_DIR.parent
    PROJECT_ROOT = DIRECTION_ROOT
    PILOT_ROOT = DIRECTION_ROOT
    PANEL_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "repair_panel_item.schema.json"
    BUNDLE_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "repair_assessor_bundle.schema.json"
    ASSESSMENT_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "repair_assessment.schema.json"
    LINK_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "post_revision_rating_link.schema.json"
    PILOT_ITEM_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "pilot_item.schema.json"
    RATING_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "paper_metric_rating.schema.json"
    OUTPUT_SCHEMA_PATH = PORTABLE_SCHEMA_ROOT / "qualitative_output.schema.json"
    RUNTIME_README_PATH = SCRIPT_DIR / "README.md"
else:
    DIRECTION_ROOT = SCRIPT_PATH.parents[1]
    PROJECT_ROOT = SCRIPT_PATH.parents[3]
    PILOT_ROOT = DIRECTION_ROOT / "pilot"
    PANEL_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "repair_panel_item.schema.json"
    BUNDLE_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "repair_assessor_bundle.schema.json"
    ASSESSMENT_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "repair_assessment.schema.json"
    LINK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "post_revision_rating_link.schema.json"
    PILOT_ITEM_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
    RATING_SCHEMA_PATH = (
        PROJECT_ROOT
        / "experiments"
        / "qualitative_coding_baselines"
        / "schemas"
        / "paper_metric_rating.schema.json"
    )
    OUTPUT_SCHEMA_PATH = (
        PROJECT_ROOT
        / "experiments"
        / "qualitative_coding_baselines"
        / "schemas"
        / "qualitative_output.schema.json"
    )
    RUNTIME_README_PATH = DIRECTION_ROOT / "protocol" / "repair_assessor_runtime_README.md"
ASSIGNMENT_BUNDLE_CONTRACT_VERSION = "direction-h-repair-assessor-bundle-v1"
CHARLIE_RATER_ID = "charlie_dev_researcher_01"

EVALUATOR_GROUPS = [
    "researcher",
    "qualitative_methods_expert",
    "domain_expert",
    "dual_expertise",
]
COLLATERAL_FLAGS = [
    "new_unsupported_claim",
    "new_omission",
    "new_distortion",
    "new_wrong_attribution",
    "new_quote_integrity_error",
    "other",
]
DISPOSITIONS = [
    "accept_revision",
    "revise_again",
    "reject_revision",
    "escalate",
]
METRICS = [
    (
        "evidential_credibility",
        "Evidential credibility\n"
        "  1=absent, unverifiable, misattributed, or contradictory evidence\n"
        "  3=core meaning partly supported, but a material link or qualifier lacks evidence\n"
        "  5=every material part directly warranted by sufficient contextual evidence\n"
        "  2/4=corresponding intermediate judgment",
    ),
    (
        "voice_boundary_preservation",
        "Voice/boundary preservation\n"
        "  1=a consequential voice, counterexample, or contextual distinction is erased or reversed\n"
        "  3=main pattern retained, but a meaningful viewpoint or boundary is underplayed\n"
        "  5=all consequential variation, dissent, minority cases, and qualifications survive\n"
        "  2/4=corresponding intermediate judgment",
    ),
    (
        "scope_calibration",
        "Scope calibration\n"
        "  1=claim breadth, polarity, or causal strength is incompatible with the evidence\n"
        "  3=direction is broadly appropriate but scope or strength needs material change\n"
        "  5=participant/group/corpus scope fits, with no stronger causal or prevalence claim than warranted\n"
        "  2/4=corresponding intermediate judgment",
    ),
]
ERROR_FLAGS = [
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
    "inconsistent_codebook",
    "other",
]
RATING_DISPOSITIONS = ["accept", "revise", "reject", "escalate"]
EXPERTISE = ["none", "qualitative_methods", "domain", "both"]
RATING_FIELDS = {
    "annotation_version",
    "rater_id",
    "evaluator_group",
    "packet_id",
    "corpus_id",
    "evaluation_role",
    "output_id",
    "rated_at_utc",
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
    "cannot_judge",
    "confidence",
    "disposition",
    "serious_error_flags",
    "review_seconds",
    "requested_expertise",
    "rationale",
}

# These fields identify coordinator-only records or reveal an intervention,
# construction label, prior judgment, or model identity.  A public panel
# manifest containing any of them is not safe input for this collector.
FORBIDDEN_MANIFEST_KEYS = {
    "allocation",
    "allocation_record_sha256",
    "charlie_rating",
    "condition",
    "condition_label",
    "expected_disposition",
    "expected_outcome",
    "failure_family",
    "feedback_arm",
    "feedback_author",
    "feedback_content",
    "feedback_record_id",
    "feedback_source",
    "ground_truth",
    "intended_rater_id",
    "model_id",
    "model_identity",
    "other_assessments",
    "paired_case_group_id",
    "planted_defect",
    "planted_defect_family",
    "rater_id",
    "repair_label",
    "repeat_index",
    "revision_case_id",
    "revision_diagnosis",
    "revision_model_id",
    "target_error_flag",
    "truth",
    "truth_map",
    "truth_record",
}
FORBIDDEN_MANIFEST_VALUE_TOKENS = {
    "charlie_dev_researcher_01",
    "charlie_feedback",
    "independent_human_feedback",
    "no_feedback",
}
ALLOWED_ROW_KEYS = {
    "blinded_revision_id",
    "corpus_id",
    "data_classification",
    "display_order",
    "evaluation_role",
    "item_file",
    "packet_id",
    "repair_panel_item_version",
    "sha256",
    "starting_output_id",
    "target_assessment_reference_id",
    "task_id",
}
REQUIRED_ROW_KEYS = {
    "display_order",
    "blinded_revision_id",
    "task_id",
    "packet_id",
    "corpus_id",
    "starting_output_id",
    "evaluation_role",
    "item_file",
    "sha256",
}
ALLOWED_MANIFEST_KEYS = {
    "bundle_manifest_version",
    "study_id",
    "schedule_id",
    "bundle_id",
    "assessor_alias",
    "evaluator_group",
    "data_scope",
    "contains_real_source_text",
    "created_at_utc",
    "parent_panel_manifest_sha256",
    "frozen_instrument_hashes",
    "assignment_payload_sha256",
    "assignment_token_hash_method",
    "assignment_token_sha256",
    "rater_binding_hash_method",
    "rater_binding_sha256",
    "item_count",
    "items",
}

FROZEN_INSTRUMENT_PATHS = {
    "repair_assessment_collector_script_sha256": SCRIPT_PATH,
    "repair_panel_item_schema_sha256": PANEL_SCHEMA_PATH,
    "repair_assessor_bundle_schema_sha256": BUNDLE_SCHEMA_PATH,
    "pilot_item_schema_sha256": PILOT_ITEM_SCHEMA_PATH,
    "qualitative_output_schema_sha256": OUTPUT_SCHEMA_PATH,
    "repair_assessment_schema_sha256": ASSESSMENT_SCHEMA_PATH,
    "paper_metric_rating_schema_sha256": RATING_SCHEMA_PATH,
    "post_revision_rating_link_schema_sha256": LINK_SCHEMA_PATH,
    "repair_assessor_runtime_readme_sha256": RUNTIME_README_PATH,
}
RUNTIME_PACKAGE_PATHS = {
    "repair_assessment_collector_script_sha256": "runtime/collect_repair_assessment.py",
    "repair_panel_item_schema_sha256": "runtime/schemas/repair_panel_item.schema.json",
    "repair_assessor_bundle_schema_sha256": "runtime/schemas/repair_assessor_bundle.schema.json",
    "pilot_item_schema_sha256": "runtime/schemas/pilot_item.schema.json",
    "qualitative_output_schema_sha256": "runtime/schemas/qualitative_output.schema.json",
    "repair_assessment_schema_sha256": "runtime/schemas/repair_assessment.schema.json",
    "paper_metric_rating_schema_sha256": "runtime/schemas/paper_metric_rating.schema.json",
    "post_revision_rating_link_schema_sha256": "runtime/schemas/post_revision_rating_link.schema.json",
    "repair_assessor_runtime_readme_sha256": "runtime/README.md",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read valid JSON from {path}: {exc}. Nothing was written.") from exc


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def safe_bundle_root(path: Path) -> Path:
    if path.is_symlink():
        raise SystemExit(f"Refusing symlinked isolated bundle root: {path}. Nothing was written.")
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise SystemExit(
            f"Missing isolated assessor bundle directory: {resolved}. Nothing was written."
        )
    if not re.fullmatch(r"RAB-[0-9A-F]{20}", resolved.name):
        raise SystemExit(
            "The explicit isolated bundle root must be the delivered RAB-* directory. "
            "Nothing was written."
        )
    # Preserve the stronger checkout-local coordinator rejection when the
    # shared collector is used. A portable export has no coordinator tree.
    if not PORTABLE_RUNTIME:
        coordinator_root = (DIRECTION_ROOT / "coordinator_only").resolve()
        if resolved == coordinator_root or is_within(resolved, coordinator_root):
            raise SystemExit(
                f"Refusing coordinator-only bundle root: {resolved}. Nothing was written."
            )
    return resolved


def safe_bundle_path(
    path: Path,
    bundle_root: Path,
    label: str,
    *,
    must_exist: bool,
) -> Path:
    if path.is_symlink():
        raise SystemExit(f"Refusing symlinked {label}: {path}. Nothing was written.")
    resolved = path.expanduser().resolve()
    if not is_within(resolved, bundle_root.resolve()):
        raise SystemExit(
            f"Refusing {label} outside the explicit isolated assessor bundle: {resolved}. "
            "Nothing was written."
        )
    if must_exist and not resolved.is_file():
        raise SystemExit(f"Missing {label}: {resolved}. Nothing was written.")
    return resolved


def find_forbidden_manifest_field(value: Any, path: str = "<root>") -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_MANIFEST_KEYS:
                return f"{path}/{key}"
            found = find_forbidden_manifest_field(nested, f"{path}/{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = find_forbidden_manifest_field(nested, f"{path}/{index}")
            if found:
                return found
    elif isinstance(value, str) and value.strip().lower() in FORBIDDEN_MANIFEST_VALUE_TOKENS:
        return path
    return None


def schema_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in (
        PANEL_SCHEMA_PATH,
        BUNDLE_SCHEMA_PATH,
        PILOT_ITEM_SCHEMA_PATH,
        OUTPUT_SCHEMA_PATH,
        RATING_SCHEMA_PATH,
        ASSESSMENT_SCHEMA_PATH,
        LINK_SCHEMA_PATH,
    ):
        schema = load_json(path)
        if schema.get("$id"):
            store[schema["$id"]] = schema
    return store


def validate(instance: Any, schema_path: Path, label: str) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=schema_store()),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise SystemExit(
            f"{label} fails {schema_path.name}: {details}. Nothing was written."
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nul_hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def verify_bundle_authorization(
    manifest: dict[str, Any],
    *,
    assignment_token: str,
    rater_id: str,
    evaluator_group: str,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", assignment_token):
        raise SystemExit(
            "--assignment-token must be exactly 64 lowercase hexadecimal characters. "
            "Nothing was written."
        )
    if manifest["evaluator_group"] != evaluator_group:
        raise SystemExit(
            "Command-line evaluator group does not match the frozen assessor bundle. "
            "Nothing was written."
        )

    payload = {
        "assignment_payload_version": "direction-h-repair-assignment-payload-v1",
        "study_id": manifest["study_id"],
        "schedule_id": manifest["schedule_id"],
        "bundle_id": manifest["bundle_id"],
        "assessor_alias": manifest["assessor_alias"],
        "evaluator_group": manifest["evaluator_group"],
        "parent_panel_manifest_sha256": manifest["parent_panel_manifest_sha256"],
        "frozen_instrument_hashes": manifest["frozen_instrument_hashes"],
        "items": manifest["items"],
    }
    payload_sha256 = sha256_canonical(payload)
    if not secrets.compare_digest(payload_sha256, manifest["assignment_payload_sha256"]):
        raise SystemExit(
            "Assessor-bundle assignment payload hash mismatch. Nothing was written."
        )

    token_sha256 = nul_hash(
        "direction-h-assignment-token-v1",
        manifest["study_id"],
        manifest["schedule_id"],
        manifest["bundle_id"],
        assignment_token,
    )
    if not secrets.compare_digest(token_sha256, manifest["assignment_token_sha256"]):
        raise SystemExit("Invalid assignment token for this assessor bundle. Nothing was written.")
    binding_sha256 = nul_hash(
        "direction-h-rater-binding-v1",
        manifest["study_id"],
        manifest["schedule_id"],
        manifest["bundle_id"],
        rater_id,
        evaluator_group,
        payload_sha256,
        assignment_token,
    )
    if not secrets.compare_digest(binding_sha256, manifest["rater_binding_sha256"]):
        raise SystemExit(
            "Rater identity is not authorized for this assessor bundle. Nothing was written."
        )

    expected_instruments = {
        key: sha256_file(path) for key, path in FROZEN_INSTRUMENT_PATHS.items()
    }
    if manifest["frozen_instrument_hashes"] != expected_instruments:
        raise SystemExit(
            "A frozen repair-assessment instrument has drifted since assignment. "
            "Nothing was written."
        )


def verify_runtime_package(manifest: dict[str, Any], bundle_root: Path) -> None:
    """Verify the exact sanitized runtime shipped inside this one bundle."""

    runtime_root = safe_bundle_path(
        bundle_root / "runtime", bundle_root, "assessor runtime directory", must_exist=False
    )
    if runtime_root.is_symlink() or not runtime_root.is_dir():
        raise SystemExit("The isolated assessor runtime directory is missing. Nothing was written.")
    expected_files = set(RUNTIME_PACKAGE_PATHS.values())
    actual_files = {
        str(path.relative_to(bundle_root))
        for path in runtime_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    unsafe_entries = [
        path
        for path in runtime_root.rglob("*")
        if path.is_symlink() or (not path.is_file() and not path.is_dir())
    ]
    if unsafe_entries or actual_files != expected_files:
        raise SystemExit(
            "The isolated assessor runtime contains a missing, extra, or unsafe entry. "
            "Nothing was written."
        )
    for label, relative in RUNTIME_PACKAGE_PATHS.items():
        path = safe_bundle_path(
            bundle_root / relative,
            bundle_root,
            f"runtime instrument {label}",
            must_exist=True,
        )
        expected = manifest["frozen_instrument_hashes"].get(label)
        if not isinstance(expected, str) or not secrets.compare_digest(
            sha256_file(path), expected
        ):
            raise SystemExit(
                f"The shipped runtime instrument is missing or hash-drifted: {label}. "
                "Nothing was written."
            )


def parse_manifest(
    manifest_path: Path,
    *,
    bundle_root: Path,
    assignment_token: str,
    rater_id: str,
    evaluator_group: str,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("Assessor-bundle manifest must be a JSON object. Nothing was written.")
    if manifest.get("manifest_version") == "direction-h-repair-panel-manifest-v1":
        raise SystemExit(
            "The full repair-panel staging manifest is not a valid assessor assignment. "
            "Use only the one token-bound bundle delivered to this assessor. Nothing was written."
        )
    forbidden = find_forbidden_manifest_field(manifest)
    if forbidden:
        raise SystemExit(
            f"Assessor-bundle manifest contains a forbidden coordinator/intervention field at "
            f"{forbidden}. Nothing was written."
        )
    missing_manifest = ALLOWED_MANIFEST_KEYS - set(manifest)
    unknown_manifest = set(manifest) - ALLOWED_MANIFEST_KEYS
    if missing_manifest or unknown_manifest:
        parts = []
        if missing_manifest:
            parts.append("missing " + ", ".join(sorted(missing_manifest)))
        if unknown_manifest:
            parts.append("unexpected " + ", ".join(sorted(unknown_manifest)))
        raise SystemExit(
            "Assessor-bundle manifest has an unsafe or incomplete public shape ("
            + "; ".join(parts)
            + "). Nothing was written."
        )
    if manifest.get("bundle_manifest_version") != "direction-h-repair-assessor-bundle-v1":
        raise SystemExit("Unsupported assessor-bundle manifest version. Nothing was written.")
    validate(manifest, BUNDLE_SCHEMA_PATH, "repair-assessor bundle manifest")
    if (
        manifest_path.name != "manifest.json"
        or manifest_path.parent.resolve() != bundle_root.resolve()
        or manifest_path.parent.name != manifest["bundle_id"]
    ):
        raise SystemExit(
            "Assessor-bundle manifest path does not match its frozen bundle ID. "
            "Nothing was written."
        )
    if manifest.get("contains_real_source_text") is not False or manifest.get(
        "data_scope"
    ) != "synthetic_only":
        raise SystemExit("Assessor bundle is not synthetic-only. Nothing was written.")

    verify_runtime_package(manifest, bundle_root)
    verify_bundle_authorization(
        manifest,
        assignment_token=assignment_token,
        rater_id=rater_id,
        evaluator_group=evaluator_group,
    )
    rows = manifest["items"]

    loaded: list[tuple[dict[str, Any], Path]] = []
    seen_blind_ids: set[str] = set()
    seen_task_ids: set[str] = set()
    seen_display_orders: set[int] = set()
    display_order_by_blind_id: dict[str, int] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SystemExit(f"Manifest row {index + 1} is not an object. Nothing was written.")
        unknown = set(row) - ALLOWED_ROW_KEYS
        missing = REQUIRED_ROW_KEYS - set(row)
        if unknown or missing:
            parts = []
            if missing:
                parts.append("missing " + ", ".join(sorted(missing)))
            if unknown:
                parts.append("unexpected " + ", ".join(sorted(unknown)))
            raise SystemExit(
                f"Manifest row {index + 1} has an unsafe or incomplete public shape ("
                + "; ".join(parts)
                + "). Nothing was written."
            )
        display_order = row["display_order"]
        if display_order in seen_display_orders:
            raise SystemExit(
                f"Manifest row {index + 1} has a duplicate display_order. Nothing was written."
            )
        seen_display_orders.add(display_order)
        relative = Path(row["item_file"])
        if relative.is_absolute():
            raise SystemExit(f"Manifest row {index + 1} uses an absolute item_file. Nothing was written.")
        item_path = safe_bundle_path(
            manifest_path.parent / relative,
            bundle_root,
            f"assigned repair-panel item in row {index + 1}",
            must_exist=True,
        )
        if not is_within(item_path, manifest_path.parent):
            raise SystemExit(
                f"Manifest row {index + 1} escapes its assessor bundle. Nothing was written."
            )
        if row["sha256"] != sha256_file(item_path):
            raise SystemExit(f"Assigned item hash mismatch in row {index + 1}. Nothing was written.")
        item = load_json(item_path)
        forbidden_item = find_forbidden_manifest_field(item, f"item[{index + 1}]")
        if forbidden_item:
            raise SystemExit(
                f"Assigned item contains a forbidden coordinator/intervention field at "
                f"{forbidden_item}. Nothing was written."
            )
        validate(item, PANEL_SCHEMA_PATH, f"assigned repair-panel item {index + 1}")
        if item.get("data_classification") != "synthetic_cc0":
            raise SystemExit(
                f"Assigned repair-panel item {index + 1} is not synthetic_cc0. Nothing was written."
            )
        packet_id = item["packet_id"]
        if any(
            embedded.get("packet_id") != packet_id
            for embedded in (
                item["evidence_packet"],
                item["original_output"],
                item["revised_output"],
            )
        ):
            raise SystemExit(
                f"Assigned repair-panel item {index + 1} has inconsistent packet IDs. "
                "Nothing was written."
            )
        research_question = item["evidence_packet"]["research_question"]
        if any(
            output.get("research_question") != research_question
            for output in (item["original_output"], item["revised_output"])
        ):
            raise SystemExit(
                f"Assigned repair-panel item {index + 1} has inconsistent research questions. "
                "Nothing was written."
            )
        if item["study_id"] != manifest["study_id"]:
            raise SystemExit(f"Study ID mismatch in manifest row {index + 1}. Nothing was written.")
        for key in (
            "task_id",
            "blinded_revision_id",
            "packet_id",
            "corpus_id",
            "starting_output_id",
            "evaluation_role",
            "target_assessment_reference_id",
            "data_classification",
            "repair_panel_item_version",
        ):
            if row[key] != item[key]:
                raise SystemExit(
                    f"Manifest row {index + 1} disagrees with its item on {key}. "
                    "Nothing was written."
                )
        blind_id = item["blinded_revision_id"]
        task_id = item["task_id"]
        if blind_id in seen_blind_ids:
            raise SystemExit(
                f"Duplicate blinded_revision_id in assessor bundle: {blind_id}. "
                "Nothing was written."
            )
        if task_id in seen_task_ids:
            raise SystemExit(
                f"Assessor bundle exposes two variants of task {task_id}. Nothing was written."
            )
        seen_blind_ids.add(blind_id)
        seen_task_ids.add(task_id)
        display_order_by_blind_id[blind_id] = display_order
        loaded.append((item, item_path))

    if seen_display_orders != set(range(1, len(loaded) + 1)):
        raise SystemExit("Assessor-bundle display order is not contiguous. Nothing was written.")
    if manifest["item_count"] != len(loaded):
        raise SystemExit("Assessor-bundle item_count mismatch. Nothing was written.")
    loaded.sort(key=lambda pair: display_order_by_blind_id[pair[0]["blinded_revision_id"]])
    return manifest, loaded


def rating_key(rating: dict[str, Any]) -> dict[str, Any]:
    return {
        field: rating[field]
        for field in (
            "annotation_version",
            "rater_id",
            "packet_id",
            "corpus_id",
            "evaluation_role",
            "output_id",
            "rated_at_utc",
        )
    }


def link_id(assessment_record_id: str, blind_id: str) -> str:
    identity = "|".join(
        [
            "direction-h-post-revision-rating-link-v1",
            assessment_record_id,
            blind_id,
        ]
    )
    return "DHL-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()


def validate_bundle_records(
    assessment: dict[str, Any],
    rating: dict[str, Any],
    link: dict[str, Any],
    *,
    expected_rater_id: str,
    label: str,
) -> None:
    validate(assessment, ASSESSMENT_SCHEMA_PATH, f"{label} repair assessment")
    validate(rating, RATING_SCHEMA_PATH, f"{label} post-revision rating")
    validate(link, LINK_SCHEMA_PATH, f"{label} rating link")
    if set(rating) != RATING_FIELDS:
        missing = sorted(RATING_FIELDS - set(rating))
        extra = sorted(set(rating) - RATING_FIELDS)
        raise SystemExit(
            f"{label} post-revision rating is not the exact Direction H shared-field "
            f"projection (missing={missing}, extra={extra}). Refusing collection."
        )
    if assessment["rater_id"] != expected_rater_id or rating["rater_id"] != expected_rater_id:
        raise SystemExit(f"{label} rater identity mismatch. Refusing collection.")
    for field in ("evaluator_group", "packet_id", "evaluation_role"):
        if rating[field] != assessment[field]:
            raise SystemExit(f"{label} disagrees across records on {field}. Refusing collection.")
    if rating["output_id"] != assessment["blinded_revision_id"]:
        raise SystemExit(
            f"{label} rating output_id is not the arm-blind revision ID. Refusing collection."
        )
    if link["assessment_id"] != assessment["assessment_id"]:
        raise SystemExit(f"{label} assessment-link identity mismatch. Refusing collection.")
    if link["task_id"] != assessment["task_id"]:
        raise SystemExit(f"{label} task-link identity mismatch. Refusing collection.")
    if link["blinded_revision_id"] != assessment["blinded_revision_id"]:
        raise SystemExit(f"{label} blind-link identity mismatch. Refusing collection.")
    if link["link_id"] != link_id(assessment["assessment_id"], assessment["blinded_revision_id"]):
        raise SystemExit(f"{label} deterministic link ID mismatch. Refusing collection.")
    if link["rating_key"] != rating_key(rating):
        raise SystemExit(f"{label} rating key mismatch. Refusing collection.")
    if link["repair_assessment_record_sha256"] != sha256_canonical(assessment):
        raise SystemExit(f"{label} repair-assessment hash mismatch. Refusing collection.")
    if link["post_revision_rating_record_sha256"] != sha256_canonical(rating):
        raise SystemExit(f"{label} post-revision-rating hash mismatch. Refusing collection.")
    if link["shared_rating_schema_sha256"] != sha256_file(RATING_SCHEMA_PATH):
        raise SystemExit(f"{label} shared rating schema hash mismatch. Refusing collection.")
    timing = link["timing"]
    if timing["repair_assessment_review_seconds"] != assessment["review_seconds"]:
        raise SystemExit(f"{label} repair timing mismatch. Refusing collection.")
    if timing["post_revision_rating_review_seconds"] != rating["review_seconds"]:
        raise SystemExit(f"{label} rating timing mismatch. Refusing collection.")
    expected_increment = round(rating["review_seconds"] - assessment["review_seconds"], 3)
    if expected_increment < 0 or timing["incremental_metric_phase_seconds"] != expected_increment:
        raise SystemExit(f"{label} incremental timing mismatch. Refusing collection.")


def existing_task_ids(
    responses_root: Path, rater_id: str, bundle_root: Path
) -> set[str]:
    output_dir = (responses_root / rater_id).resolve()
    if not is_within(output_dir, responses_root.resolve()):
        raise SystemExit("Rater response path escapes the reviewer-safe response directory.")
    if not output_dir.exists():
        return set()
    if not output_dir.is_dir():
        raise SystemExit(f"Assessment output path is not a directory: {output_dir}")

    expected_names = {
        "repair_assessment.json",
        "post_revision_rating.json",
        "rating_link.json",
    }
    completed: set[str] = set()
    for bundle_path in sorted(output_dir.iterdir()):
        if bundle_path.is_symlink() or not bundle_path.is_dir():
            raise SystemExit(
                f"Unexpected response entry {bundle_path}; only complete record bundles are "
                "accepted. Refusing collection."
            )
        if not is_within(bundle_path.resolve(), output_dir):
            raise SystemExit(
                f"Existing response bundle escapes its rater directory: {bundle_path}. "
                "Refusing collection."
            )
        names = {path.name for path in bundle_path.iterdir()}
        if names != expected_names:
            raise SystemExit(
                f"Incomplete or unexpected response bundle {bundle_path.name}: found "
                f"{sorted(names)}. Refusing collection."
            )
        assessment_path = safe_bundle_path(
            bundle_path / "repair_assessment.json",
            bundle_root,
            "existing repair assessment",
            must_exist=True,
        )
        rating_path = safe_bundle_path(
            bundle_path / "post_revision_rating.json",
            bundle_root,
            "existing post-revision rating",
            must_exist=True,
        )
        link_path = safe_bundle_path(
            bundle_path / "rating_link.json",
            bundle_root,
            "existing post-revision rating link",
            must_exist=True,
        )
        assessment = load_json(assessment_path)
        rating = load_json(rating_path)
        link = load_json(link_path)
        if not all(isinstance(record, dict) for record in (assessment, rating, link)):
            raise SystemExit(
                f"Existing response bundle {bundle_path.name} contains a non-object record. "
                "Refusing collection."
            )
        validate_bundle_records(
            assessment,
            rating,
            link,
            expected_rater_id=rater_id,
            label=f"existing bundle {bundle_path.name}",
        )
        if bundle_path.name != assessment["assessment_id"]:
            raise SystemExit(
                f"Existing bundle directory does not match assessment_id: {bundle_path}. "
                "Refusing collection."
            )
        if assessment["assessment_id"] != assessment_id(
            {
                "study_id": link["study_id"],
                "task_id": assessment["task_id"],
            },
            rater_id,
        ):
            raise SystemExit(
                f"Existing bundle {bundle_path.name} has a noncanonical assessment ID. "
                "Refusing collection."
            )
        if assessment["task_id"] in completed:
            raise SystemExit(
                f"Duplicate task bundle for rater {rater_id}: {assessment['task_id']}. "
                "Refusing collection."
            )
        completed.add(assessment["task_id"])
    return completed


def choose_item(
    rows: list[tuple[dict[str, Any], Path]],
    requested_blind_id: str | None,
    completed_tasks: set[str],
) -> tuple[dict[str, Any], Path]:
    if requested_blind_id:
        matches = [pair for pair in rows if pair[0]["blinded_revision_id"] == requested_blind_id]
        if len(matches) != 1:
            raise SystemExit(f"Unknown blinded revision ID: {requested_blind_id}. Nothing was written.")
        selected = matches[0]
        if selected[0]["task_id"] in completed_tasks:
            raise SystemExit(
                f"This rater already assessed another variant of task {selected[0]['task_id']}; "
                "refusing paired-variant exposure. Nothing was written."
            )
        return selected

    for selected in rows:
        if selected[0]["task_id"] not in completed_tasks:
            return selected
    raise SystemExit("This rater has already assessed one variant of every available task.")


def decode_pointer_token(token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            decoded.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValueError(f"malformed JSON Pointer escape in token {token!r}")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"not a JSON Pointer: {pointer!r}")
    current = document
    for encoded_token in pointer[1:].split("/"):
        token = decode_pointer_token(encoded_token)
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"does not resolve: {pointer!r}")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError(f"invalid array index: {pointer!r}")
            position = int(token)
            if position >= len(current):
                raise ValueError(f"array index out of range: {pointer!r}")
            current = current[position]
        else:
            raise ValueError(f"traverses a scalar: {pointer!r}")
    return current


def validate_collateral_findings(item: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    excerpt_ids = {
        excerpt["excerpt_id"] for excerpt in item["evidence_packet"]["excerpts"]
    }
    for index, finding in enumerate(findings, start=1):
        unknown = set(finding["evidence_excerpt_ids"]) - excerpt_ids
        if unknown:
            raise SystemExit(
                f"Collateral finding {index} cites unknown excerpt ID(s): "
                + ", ".join(sorted(unknown))
                + ". Nothing was written."
            )
        for pointer in finding["revision_output_locations"]:
            try:
                resolve_json_pointer(item["revised_output"], pointer)
            except ValueError as exc:
                raise SystemExit(
                    f"Collateral finding {index} has an invalid revised-output location "
                    f"({exc}). Nothing was written."
                ) from exc


def prompt_nonempty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("A non-empty response is required.")


def prompt_choice(label: str, choices: list[str]) -> str:
    print(label)
    for index, choice in enumerate(choices, start=1):
        print(f"  {index}. {choice}")
    while True:
        value = input("Choose a number or exact label: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(choices):
            return choices[int(value) - 1]
        if value in choices:
            return value
        print("Choose one listed option.")


def prompt_tristate(label: str) -> bool | None:
    while True:
        value = input(label + " [y/n/cj]: ").strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        if value in {"cj", "cannot judge", "cannot_judge"}:
            return None
        print("Enter y, n, or cj.")


def prompt_scale(label: str) -> int:
    while True:
        value = input(label + " [1-5]: ").strip()
        if value in {"1", "2", "3", "4", "5"}:
            return int(value)
        print("Enter 1, 2, 3, 4, or 5.")


def prompt_metric_scale(label: str) -> int | None:
    while True:
        value = input(label + " [1-5 or cj]: ").strip().lower()
        if value in {"cj", "cannot judge", "cannot_judge"}:
            return None
        if value in {"1", "2", "3", "4", "5"}:
            return int(value)
        print("Enter 1, 2, 3, 4, 5, or cj.")


def prompt_many(label: str, choices: list[str]) -> list[str]:
    print(label)
    for index, choice in enumerate(choices, start=1):
        print(f"  {index}. {choice}")
    print("Enter comma-separated numbers or labels; press Enter for none.")
    while True:
        raw = input("Selection: ").strip()
        if not raw:
            return []
        selected: list[str] = []
        invalid: list[str] = []
        for part in [value.strip() for value in raw.split(",") if value.strip()]:
            if part.isdigit() and 1 <= int(part) <= len(choices):
                selected.append(choices[int(part) - 1])
            elif part in choices:
                selected.append(part)
            else:
                invalid.append(part)
        if not invalid:
            return list(dict.fromkeys(selected))
        print("Unknown selection(s): " + ", ".join(invalid))


def prompt_list(label: str, *, require_one: bool = False) -> list[str]:
    print(label)
    print("Enter one value per line; press Enter on a blank line to finish.")
    values: list[str] = []
    while True:
        value = input(f"  {len(values) + 1}> ").strip()
        if not value:
            if require_one and not values:
                print("At least one value is required.")
                continue
            return values
        if value not in values:
            values.append(value)


def render_item(item: dict[str, Any]) -> None:
    packet = item["evidence_packet"]
    print("\n" + "=" * 78)
    print(
        f"TASK {item['task_id']}  |  BLINDED REVISION {item['blinded_revision_id']}  "
        f"|  PACKET {item['packet_id']}"
    )
    print("SYNTHETIC/fictional evidence only. Feedback condition and model are blinded.")
    print("=" * 78)
    print("\nRESEARCH QUESTION\n" + packet["research_question"])
    print("\nCONTEXT NOTE\n" + packet["context_note"])
    print("\nSOURCE EXCERPTS")
    for excerpt in packet["excerpts"]:
        meta = f"{excerpt['excerpt_id']} | source={excerpt['source_id']}"
        if excerpt.get("speaker_id"):
            meta += f" | speaker={excerpt['speaker_id']}"
        print(f"\n[{meta}]")
        if excerpt.get("context"):
            print(f"Context: {excerpt['context']}")
        print(excerpt["text"])
    print("\nSTARTING OUTPUT")
    print(json.dumps(item["original_output"], ensure_ascii=False, indent=2))
    print("\nREVISED OUTPUT")
    print(json.dumps(item["revised_output"], ensure_ascii=False, indent=2))
    print("\nTARGET-ASSESSMENT BRIEF")
    print(item["target_assessment_brief"])
    print("\n" + "=" * 78)


def collect_collateral_findings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    while True:
        print(f"\nCollateral finding {len(findings) + 1}")
        collateral_flag = prompt_choice("Collateral-error family:", COLLATERAL_FLAGS)
        locations = prompt_list(
            "Revised-output JSON Pointer location(s), such as /themes/0/claim:",
            require_one=True,
        )
        evidence_ids = prompt_list(
            "Relevant supplied excerpt IDs (blank is allowed for structural issues):"
        )
        description = prompt_nonempty("Describe the new collateral error: ")
        findings.append(
            {
                "collateral_flag": collateral_flag,
                "revision_output_locations": locations,
                "evidence_excerpt_ids": evidence_ids,
                "description": description,
            }
        )
        if input("Add another collateral finding? [y/N]: ").strip().lower() not in {
            "y",
            "yes",
        }:
            return findings


def derive_success(
    target_repaired: bool | None,
    material_preserved: bool | None,
    collateral_present: bool | None,
) -> bool | None:
    if target_repaired is True and material_preserved is True and collateral_present is False:
        return True
    if target_repaired is False or material_preserved is False or collateral_present is True:
        return False
    return None


def assessment_id(item: dict[str, Any], rater_id: str) -> str:
    identity = "|".join(
        [
            "direction-h-repair-assessment-v1",
            item["study_id"],
            item["task_id"],
            rater_id,
        ]
    )
    return "DHA-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()


def validate_args(rater_id: str) -> str:
    normalized = rater_id.strip()
    if not normalized or len(normalized) > 160:
        raise SystemExit("--rater-id must contain 1-160 non-whitespace characters.")
    if normalized.lower() == CHARLIE_RATER_ID.lower():
        raise SystemExit(
            "Charlie may not assess revisions produced from his feedback; refusing this "
            "rater ID. Nothing was written."
        )
    if normalized != normalized.casefold():
        raise SystemExit(
            "--rater-id must use its canonical lowercase spelling so paired-variant "
            "checks cannot be bypassed by case changes. Nothing was written."
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,159}", normalized):
        raise SystemExit(
            "--rater-id must be a lowercase filesystem-safe pseudonym using only letters, digits, "
            "periods, underscores, or hyphens. Nothing was written."
        )
    return normalized


def write_exclusive_json(path: Path, record: dict[str, Any]) -> None:
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def commit_response_bundle(
    output_dir: Path,
    record_id: str,
    assessment: dict[str, Any],
    rating: dict[str, Any],
    link: dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / record_id
    if bundle_path.exists():
        raise SystemExit(f"Response bundle {record_id} already exists; refusing to overwrite it.")

    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    pending_path = output_dir / f".{record_id}.{token}.pending"
    pending_path.mkdir(mode=0o700)
    filenames = (
        ("repair_assessment.json", assessment),
        ("post_revision_rating.json", rating),
        ("rating_link.json", link),
    )
    published = False
    try:
        for filename, record in filenames:
            write_exclusive_json(pending_path / filename, record)
        directory_fd = os.open(pending_path, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if bundle_path.exists():
            raise FileExistsError(bundle_path)
        os.rename(pending_path, bundle_path)
        published = True
        return bundle_path
    except FileExistsError as exc:
        raise SystemExit(
            f"Response bundle {record_id} appeared; refusing to overwrite it."
        ) from exc
    finally:
        if not published and pending_path.exists():
            for filename, _ in filenames:
                (pending_path / filename).unlink(missing_ok=True)
            try:
                pending_path.rmdir()
            except OSError:
                # An unexpected entry is safer left visible for fail-closed inspection.
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect one independent, arm-blind synthetic Direction H repair assessment "
            "and one exact linked qc-paper-metrics-v1 post-revision rating."
        ),
        epilog=(
            "Use only the token-bound isolated bundle delivered to this assessor. "
            "The full staging panel, private schedule, arm map, and coordinator_only "
            "paths are rejected. The exported bundle's runtime/ collector is self-contained."
        ),
    )
    parser.add_argument("--rater-id", required=True, help="Pseudonymous independent assessor ID")
    parser.add_argument(
        "--evaluator-group",
        required=True,
        choices=EVALUATOR_GROUPS,
        help="Assessor expertise group recorded in the canonical assessment",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        required=True,
        help="Explicit path to the one delivered RAB-* directory",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Manifest from this assessor's isolated RAB-* bundle",
    )
    parser.add_argument(
        "--assignment-token",
        required=True,
        help="64-character private token delivered separately for this assessor bundle",
    )
    parser.add_argument(
        "--blind-id",
        required=True,
        help="Coordinator-assigned arm-blind ID from a frozen balanced schedule",
    )
    args = parser.parse_args()

    # Reject Charlie before opening any manifest, including a mistakenly supplied
    # coordinator path.
    rater_id = validate_args(args.rater_id)
    bundle_root = safe_bundle_root(args.bundle_root)
    manifest_path = safe_bundle_path(
        args.manifest,
        bundle_root,
        "repair-assessor bundle manifest",
        must_exist=True,
    )
    if manifest_path != bundle_root / "manifest.json":
        raise SystemExit(
            "--manifest must be exactly <bundle-root>/manifest.json. Nothing was written."
        )
    if PORTABLE_RUNTIME and SCRIPT_DIR.parent.resolve() != bundle_root:
        raise SystemExit(
            "The portable collector must run from this exact isolated bundle's runtime/ "
            "directory. Nothing was written."
        )
    _manifest, rows = parse_manifest(
        manifest_path,
        bundle_root=bundle_root,
        assignment_token=args.assignment_token,
        rater_id=rater_id,
        evaluator_group=args.evaluator_group,
    )
    responses_root = safe_bundle_path(
        manifest_path.parent / "responses",
        bundle_root,
        "repair-assessor response directory",
        must_exist=False,
    )
    output_dir = safe_bundle_path(
        responses_root / rater_id,
        bundle_root,
        "assessment output directory",
        must_exist=False,
    )
    completed_tasks = existing_task_ids(responses_root, rater_id, bundle_root)
    item, _ = choose_item(rows, args.blind_id, completed_tasks)

    record_id = assessment_id(item, rater_id)
    bundle_path = output_dir / record_id
    if bundle_path.exists():
        raise SystemExit(f"Response bundle {record_id} already exists; refusing to overwrite it.")

    print(
        f"Starting blinded assessment {item['blinded_revision_id']}. Review time begins "
        "when the complete item is displayed.\n"
        "Do not open coordinator files, feedback, revision diagnoses, arm maps, truth maps, "
        "or another assessor's response."
    )
    started = time.monotonic()
    render_item(item)

    print("\nREPAIR COMPONENTS")
    target_repaired = prompt_tristate("Is the target defect repaired?")
    material_preserved = prompt_tristate(
        "Is accurate and relevant material from the starting output preserved?"
    )
    collateral_present = prompt_tristate("Does the revision introduce a collateral error?")

    cannot_judge = []
    for field, value in (
        ("target_defect_repaired", target_repaired),
        ("accurate_relevant_material_preserved", material_preserved),
        ("collateral_error_present", collateral_present),
    ):
        if value is None:
            cannot_judge.append(field)

    findings = collect_collateral_findings() if collateral_present is True else []
    collateral_flags = list(
        dict.fromkeys(finding["collateral_flag"] for finding in findings)
    )
    confidence = prompt_scale("Confidence in this assessment (1=very uncertain, 5=very certain)")
    disposition = prompt_choice("Revision disposition:", DISPOSITIONS)
    rationale = prompt_nonempty("Concise evidence-linked assessment rationale: ")

    repair_completed = time.monotonic()
    assessed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assessment = {
        "repair_assessment_version": "direction-h-repair-assessment-v1",
        "assessment_id": record_id,
        "assessment_stage": "independent_initial",
        "rater_id": rater_id,
        "evaluator_group": args.evaluator_group,
        "evaluation_role": item["evaluation_role"],
        "task_id": item["task_id"],
        "packet_id": item["packet_id"],
        "starting_output_id": item["starting_output_id"],
        "blinded_revision_id": item["blinded_revision_id"],
        "target_assessment_reference_id": item["target_assessment_reference_id"],
        "assessed_at_utc": assessed_at,
        "target_defect_repaired": target_repaired,
        "accurate_relevant_material_preserved": material_preserved,
        "collateral_error_present": collateral_present,
        "successful_repair_without_collateral_error": derive_success(
            target_repaired, material_preserved, collateral_present
        ),
        "cannot_judge": cannot_judge,
        "collateral_error_flags": collateral_flags,
        "collateral_findings": findings,
        "confidence": confidence,
        "disposition": disposition,
        "review_seconds": round(repair_completed - started, 3),
        "rationale": rationale,
    }

    validate_collateral_findings(item, findings)
    validate(assessment, ASSESSMENT_SCHEMA_PATH, "repair assessment")
    if set(assessment["collateral_error_flags"]) != {
        finding["collateral_flag"] for finding in findings
    }:
        raise SystemExit(
            "Collateral flags do not exactly match collateral findings. Nothing was written."
        )
    if assessment["successful_repair_without_collateral_error"] != derive_success(
        assessment["target_defect_repaired"],
        assessment["accurate_relevant_material_preserved"],
        assessment["collateral_error_present"],
    ):
        raise SystemExit("Derived repair outcome mismatch. Nothing was written.")

    print(
        "\nPOST-REVISION SHARED METRICS\n"
        "Rate the revised output itself against the supplied evidence. These are separate "
        "construct ratings, not judgments of improvement from the starting output.\n"
        "1=not adequate, 2=major problems, 3=partly adequate and requiring material "
        "revision, 4=mostly adequate with only minor issues, 5=fully adequate. Use cj "
        "only when the supplied excerpts, local context, or source coverage are "
        "insufficient for that dimension."
    )
    metric_values: dict[str, int | None] = {}
    metric_cannot_judge: list[str] = []
    for metric, label in METRICS:
        value = prompt_metric_scale(label)
        metric_values[metric] = value
        if value is None:
            metric_cannot_judge.append(metric)
    metric_confidence = prompt_scale(
        "Confidence in the post-revision metric rating "
        "(1=very uncertain, 5=very certain)"
    )
    metric_disposition = prompt_choice(
        "Post-revision output disposition:", RATING_DISPOSITIONS
    )
    serious_error_flags = prompt_many(
        "Serious-error flags present in the revised output:", ERROR_FLAGS
    )
    if metric_disposition == "accept" and serious_error_flags:
        raise SystemExit(
            "An accepted post-revision output cannot also carry a serious-error flag. "
            "Restart this item and choose a compatible disposition. Nothing was written."
        )
    requested_expertise = prompt_choice("Requested expertise:", EXPERTISE)
    metric_rationale = prompt_nonempty(
        "Concise evidence-grounded rationale for the three post-revision metrics: "
    )
    rating_completed = time.monotonic()
    rated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post_revision_rating = {
        "annotation_version": "qc-paper-metrics-v1",
        "rater_id": rater_id,
        "evaluator_group": args.evaluator_group,
        "packet_id": item["packet_id"],
        "corpus_id": item["corpus_id"],
        "evaluation_role": item["evaluation_role"],
        "output_id": item["blinded_revision_id"],
        "rated_at_utc": rated_at,
        **metric_values,
        "cannot_judge": metric_cannot_judge,
        "confidence": metric_confidence,
        "disposition": metric_disposition,
        "serious_error_flags": serious_error_flags,
        "review_seconds": round(rating_completed - started, 3),
        "requested_expertise": requested_expertise,
        "rationale": metric_rationale,
    }
    rating_link = {
        "link_version": "direction-h-post-revision-rating-link-v1",
        "link_id": link_id(record_id, item["blinded_revision_id"]),
        "study_id": item["study_id"],
        "task_id": item["task_id"],
        "blinded_revision_id": item["blinded_revision_id"],
        "assessment_id": record_id,
        "rating_key": rating_key(post_revision_rating),
        "repair_assessment_record_sha256": sha256_canonical(assessment),
        "post_revision_rating_record_sha256": sha256_canonical(post_revision_rating),
        "shared_rating_schema_sha256": sha256_file(RATING_SCHEMA_PATH),
        "hash_serialization": "utf8_json_sorted_keys_compact_plus_lf_v1",
        "timing": {
            "timer_origin": "immediately_before_complete_item_display",
            "collection_order": "repair_components_then_shared_metrics",
            "repair_assessment_review_seconds": assessment["review_seconds"],
            "post_revision_rating_review_seconds": post_revision_rating["review_seconds"],
            "incremental_metric_phase_seconds": round(
                post_revision_rating["review_seconds"] - assessment["review_seconds"], 3
            ),
        },
        "linked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    validate_bundle_records(
        assessment,
        post_revision_rating,
        rating_link,
        expected_rater_id=rater_id,
        label="new response bundle",
    )

    print("\nREPAIR ASSESSMENT SUMMARY (not yet saved)")
    print(json.dumps(assessment, ensure_ascii=False, indent=2))
    print("\nPOST-REVISION SHARED RATING SUMMARY (not yet saved)")
    print(json.dumps(post_revision_rating, ensure_ascii=False, indent=2))
    print("\nLINK SUMMARY (not yet saved)")
    print(json.dumps(rating_link, ensure_ascii=False, indent=2))
    if input("Save this complete three-record response bundle? Type SAVE: ").strip() != "SAVE":
        raise SystemExit("Nothing was written.")

    # Re-check the paired-variant constraint immediately before the exclusive
    # create, so another process cannot silently create a second task variant.
    if item["task_id"] in existing_task_ids(responses_root, rater_id, bundle_root):
        raise SystemExit(
            f"Another assessment for task {item['task_id']} appeared during collection; "
            "refusing to write."
        )
    saved_bundle = commit_response_bundle(
        output_dir,
        record_id,
        assessment,
        post_revision_rating,
        rating_link,
    )
    print(f"Saved complete bundle {saved_bundle.relative_to(bundle_root)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Nothing was written.", file=sys.stderr)
        raise SystemExit(130)
