#!/usr/bin/env python3
"""Fail-closed, reviewer-safe validation of the Direction H/J compatibility bridge.

This script never opens Direction J's private item key, model assignments,
ratings directory, builder, legacy blind map, or historical judge outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
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
            [str(candidate), "-c", "import jsonschema, referencing"],
            capture_output=True,
            check=False,
        )
        if probe.returncode == 0:
            os.execv(str(candidate), [str(candidate), __file__, *sys.argv[1:]])
    raise SystemExit(
        "This validator needs local jsonschema and referencing packages. "
        "Do not begin review until validation can run."
    )


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
BRIDGE_ROOT = DIRECTION_ROOT / "companion_j_bridge"
MANIFEST_PATH = BRIDGE_ROOT / "manifest.json"
J_ROOT = PROJECT_ROOT / "experiments" / "direction_j_llm_as_rater"
J_RUN_ROOT = J_ROOT / "runs" / "20260825_synthetic_paired_qualification_prepared"

PATHS = {
    "run_manifest": J_RUN_ROOT / "run_manifest.json",
    "freeze": J_ROOT / "config" / "freeze_v1.json",
    "evaluator_items": J_RUN_ROOT / "evaluator_items.jsonl",
    "charlie_assignment": J_RUN_ROOT / "assignments" / "charlie_rep1.csv",
    "evaluator_item_schema": J_ROOT / "schemas" / "evaluator_item.schema.json",
    "shared_rating_schema": J_ROOT / "schemas" / "shared_rating.schema.json",
    "shared_rater_guide": J_ROOT / "protocol" / "shared_rater_guide_v1.md",
    "human_instrument": DIRECTION_ROOT / "protocol" / "direction_j_charlie_instrument_v1.md",
    "bridge_manifest_schema": DIRECTION_ROOT / "schemas" / "direction_j_bridge_manifest.schema.json",
    "base_direction_h_feedback_schema": DIRECTION_ROOT / "schemas" / "feedback_record.schema.json",
    "feedback_schema": DIRECTION_ROOT / "schemas" / "direction_j_feedback_record.schema.json",
    "review_receipt_schema": DIRECTION_ROOT / "schemas" / "direction_j_review_receipt.schema.json",
    "collector": DIRECTION_ROOT / "scripts" / "collect_direction_j_review.py",
    "validator": SCRIPT_PATH,
    "protocol": BRIDGE_ROOT / "README.md",
    "downstream_gate_schema": DIRECTION_ROOT / "schemas" / "direction_j_downstream_gate.schema.json",
    "downstream_gate": BRIDGE_ROOT / "downstream_gate.json",
    "activation_schema": DIRECTION_ROOT / "schemas" / "direction_j_bridge_activation.schema.json",
    "activation_template": BRIDGE_ROOT / "activation_record.template.json",
}

UPSTREAM_MANIFEST_KEYS = {
    "run_manifest",
    "freeze",
    "evaluator_items",
    "charlie_assignment",
}

CONTRACT_KEYS = set(PATHS) - UPSTREAM_MANIFEST_KEYS

EXPECTED_ASSIGNMENT_FIELDS = [
    "assignment_id",
    "actor_id",
    "actor_kind",
    "rating_repetition",
    "sequence",
    "item_id",
    "item_payload_sha256",
    "interface_version",
    "shared_rater_guide_version",
    "shared_rater_guide_sha256",
    "semantic_input_sha256",
    "packet_id",
    "output_id",
    "corpus_id",
    "evaluation_role",
]

PUBLIC_FORBIDDEN_KEYS = {
    "base_packet_id",
    "baseline_packet_id",
    "baseline_blind_id",
    "baseline_theme_id",
    "blind_id",
    "candidate_model_id",
    "candidate_provider",
    "condition",
    "generation_model_id",
    "model_id",
    "parent_natural_item_sha256",
    "planted_serious_error_flags",
    "provider",
    "truth_scope",
}

RESULT_NAME_FRAGMENTS = {
    "paired_observation",
    "revision_case",
    "revision_output",
    "repair_assessment",
    "repair_panel",
    "outcome",
    "results",
}


class BridgeValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BridgeValidationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve file context
        raise BridgeValidationError(f"Cannot read JSON {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def make_validator(
    schema_path: Path,
    *,
    registry: Registry | None = None,
) -> Draft202012Validator:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        registry=registry or Registry(),
        format_checker=FormatChecker(),
    )


def assert_valid(
    validator: Draft202012Validator,
    value: Any,
    label: str,
) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise BridgeValidationError(f"{label} fails schema: {rendered}")


def check_manifest_and_locks() -> dict[str, Any]:
    for label, path in PATHS.items():
        require(path.is_file(), f"Required {label} file is missing: {path}")
    require(MANIFEST_PATH.is_file(), f"Bridge manifest is missing: {MANIFEST_PATH}")
    manifest = load_json(MANIFEST_PATH)
    assert_valid(make_validator(PATHS["bridge_manifest_schema"]), manifest, "Bridge manifest")

    upstream = manifest["upstream_direction_j"]
    contracts = manifest["contracts"]
    require(set(upstream) >= UPSTREAM_MANIFEST_KEYS, "Manifest lacks an upstream file lock")
    require(set(contracts) >= CONTRACT_KEYS, "Manifest lacks a local contract file lock")

    for key in sorted(UPSTREAM_MANIFEST_KEYS):
        lock = upstream[key]
        expected_path = PATHS[key].relative_to(PROJECT_ROOT).as_posix()
        require(lock["path"] == expected_path, f"Unexpected frozen path for {key}")
        require(lock["sha256"] == sha256_file(PATHS[key]), f"Hash drift for {key}")
    for key in sorted(CONTRACT_KEYS):
        lock = contracts[key]
        expected_path = PATHS[key].relative_to(PROJECT_ROOT).as_posix()
        require(lock["path"] == expected_path, f"Unexpected frozen path for {key}")
        require(lock["sha256"] == sha256_file(PATHS[key]), f"Hash drift for {key}")

    require(manifest["contains_real_source_text"] is False, "Bridge is not synthetic-only")
    require(manifest["ratings_collected"] == 0, "Prepared manifest claims ratings")
    require(manifest["outcomes_available"] is False, "Prepared manifest claims outcomes")
    require(
        manifest["non_overlap"]["same_charlie_may_run_both_in_one_phase"] is False,
        "Bridge permits overlapping Charlie queues",
    )
    return manifest


def check_upstream_run(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    run = load_json(PATHS["run_manifest"])
    freeze = load_json(PATHS["freeze"])
    expected = manifest["upstream_direction_j"]
    require(run["study_id"] == expected["study_id"] == "direction-j-v1", "Study ID drift")
    require(run["run_id"] == expected["run_id"], "Run ID drift")
    require(run["status"] == "prepared_not_run", "Direction J run is no longer prepared/not run")
    require(run["qualification_scope"] == "synthetic_only", "Direction J scope is not synthetic")
    require(run["contains_real_source_text"] is False, "Direction J run claims real source text")
    require(run["independently_authored_fictional_text"] is True, "Fictional authorship not affirmed")
    require(run["ratings_collected"] == 0, "Direction J run contains ratings")
    require(run["outcomes_available"] is False, "Direction J run contains outcomes")
    require(run["evaluator_items_sha256"] == sha256_file(PATHS["evaluator_items"]), "Evaluator bank drift")
    require(run["freeze_sha256"] == sha256_file(PATHS["freeze"]), "Direction J freeze drift")
    require(run["expected_observations"]["charlie"] == 24, "Unexpected Charlie observation count")
    require(run["interface_version"] == "direction-j-shared-interface-v1", "Interface drift")
    require(run["shared_rater_guide_version"] == "direction-j-rater-guide-v1", "Guide version drift")
    require(run["shared_rater_guide_sha256"] == sha256_file(PATHS["shared_rater_guide"]), "Guide drift")
    require(
        run["qualification_blinding_strength"]
        == "operational_mount_isolation_not_secure_against_workspace_reader",
        "Unexpected qualification blinding classification",
    )

    require(freeze["study_id"] == "direction-j-v1", "Freeze study drift")
    require(freeze["scope"]["contains_real_source_text"] is False, "Freeze allows real text")
    require(freeze["first_run"]["status"] == "prepared_not_executed", "Freeze first run is not prepared")
    require(freeze["first_run"]["ratings_collected"] == 0, "Freeze claims ratings")
    require(freeze["first_run"]["empirical_results_available"] is False, "Freeze claims results")
    require(freeze["item_selection"]["item_count"] == 24, "Freeze item count drift")
    shared = freeze["shared_interface"]
    require(shared["rating_schema_version"] == "direction-j-shared-rating-v1", "Rating version drift")
    require(
        shared["files"]["schemas/shared_rating.schema.json"]
        == sha256_file(PATHS["shared_rating_schema"]),
        "Frozen shared-rating hash drift",
    )
    require(
        shared["files"]["schemas/evaluator_item.schema.json"]
        == sha256_file(PATHS["evaluator_item_schema"]),
        "Frozen evaluator-item hash drift",
    )
    return run, freeze


def load_and_check_items() -> dict[str, dict[str, Any]]:
    item_validator = make_validator(PATHS["evaluator_item_schema"])
    lines = PATHS["evaluator_items"].read_bytes().splitlines(keepends=True)
    require(len(lines) == 24, f"Expected 24 evaluator items; found {len(lines)}")
    items: dict[str, dict[str, Any]] = {}
    for number, raw in enumerate(lines, start=1):
        require(raw.endswith(b"\n"), f"Evaluator item line {number} lacks final LF")
        item = json.loads(raw)
        require(raw == canonical_bytes(item), f"Evaluator item line {number} is not canonical")
        assert_valid(item_validator, item, f"Evaluator item line {number}")
        item_id = item["item_id"]
        require(item_id not in items, f"Duplicate item_id: {item_id}")
        leaked = PUBLIC_FORBIDDEN_KEYS.intersection(walk_keys(item))
        require(not leaked, f"Evaluator item {item_id} leaks private keys: {sorted(leaked)}")

        evidence = item["evidence"]
        excerpt_ids = [row["excerpt_id"] for row in evidence]
        display_orders = [row["display_order"] for row in evidence]
        source_ids = [row["source_id"] for row in evidence]
        require(len(excerpt_ids) == len(set(excerpt_ids)), f"Duplicate excerpt ID in {item_id}")
        require(len(display_orders) == len(set(display_orders)), f"Duplicate display order in {item_id}")
        require(display_orders == list(range(1, len(evidence) + 1)), f"Noncontiguous evidence order in {item_id}")

        coverage = item["source_coverage"]
        require(coverage["presented_excerpt_count"] == len(evidence), f"Presented excerpt count mismatch in {item_id}")
        require(coverage["presented_source_count"] == len(set(source_ids)), f"Presented source count mismatch in {item_id}")
        candidate_rows = [row for row in evidence if row["candidate_role"] != "context_only"]
        candidate_sources = [row["candidate_attributed_source_id"] for row in candidate_rows]
        require(coverage["candidate_cited_excerpt_count"] == len(candidate_rows), f"Candidate citation count mismatch in {item_id}")
        require(coverage["candidate_cited_source_count"] == len(set(candidate_sources)), f"Candidate source count mismatch in {item_id}")
        require(set(candidate_sources) <= set(source_ids), f"Candidate source absent from display in {item_id}")

        presented_counts = Counter(source_ids)
        cited_counts = Counter(candidate_sources)
        distribution = coverage["source_distribution"]
        require(len(distribution) == len(set(source_ids)), f"Source distribution length mismatch in {item_id}")
        require(
            {row["source_id"] for row in distribution} == set(source_ids),
            f"Source distribution IDs mismatch in {item_id}",
        )
        for row in distribution:
            source_id = row["source_id"]
            require(row["presented_excerpt_count"] == presented_counts[source_id], f"Presented distribution mismatch in {item_id}")
            require(row["candidate_cited_excerpt_count"] == cited_counts[source_id], f"Cited distribution mismatch in {item_id}")

        by_excerpt = {row["excerpt_id"]: row for row in evidence}
        for row in candidate_rows:
            attributed_id = row["candidate_attributed_excerpt_id"]
            require(attributed_id in by_excerpt, f"Unknown candidate-attributed excerpt in {item_id}")
            # Do not "repair" or reject a mismatch here. Candidate-attributed
            # provenance and quotes are claims under review; controlled items
            # may deliberately make either claim wrong. Public validation only
            # requires that both layers remain present and independently visible.
        items[item_id] = item
    return items


def check_assignments(items: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    with PATHS["charlie_assignment"].open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == EXPECTED_ASSIGNMENT_FIELDS, "Charlie assignment columns drifted")
        rows = list(reader)
    require(len(rows) == 24, f"Expected 24 Charlie assignments; found {len(rows)}")
    require([int(row["sequence"]) for row in rows] == list(range(1, 25)), "Charlie sequence is not 1..24")
    require(len({row["assignment_id"] for row in rows}) == 24, "Duplicate Charlie assignment ID")
    require(len({row["item_id"] for row in rows}) == 24, "Duplicate Charlie item assignment")
    require({row["item_id"] for row in rows} == set(items), "Charlie assignment does not cover exact evaluator bank")

    guide_hash = sha256_file(PATHS["shared_rater_guide"])
    for row in rows:
        item = items[row["item_id"]]
        require(row["actor_id"] == "charlie", "Assignment actor is not Charlie")
        require(row["actor_kind"] == "human", "Charlie assignment actor kind is not human")
        require(row["rating_repetition"] == "1", "Charlie rating repetition is not one")
        require(row["interface_version"] == "direction-j-shared-interface-v1", "Assignment interface drift")
        require(row["shared_rater_guide_version"] == "direction-j-rater-guide-v1", "Assignment guide version drift")
        require(row["shared_rater_guide_sha256"] == guide_hash, "Assignment guide hash drift")
        require(row["evaluation_role"] == "synthetic_qualification", "Assignment role drift")
        for field in ("packet_id", "output_id", "corpus_id"):
            require(row[field] == item[field], f"Assignment {field} mismatch for {row['item_id']}")
        item_hash = hashlib.sha256(canonical_bytes(item)).hexdigest()
        require(row["item_payload_sha256"] == item_hash, f"Item payload hash mismatch for {row['item_id']}")
        semantic = {
            "interface_version": row["interface_version"],
            "item_payload_sha256": item_hash,
            "shared_rater_guide_sha256": guide_hash,
            "shared_rater_guide_version": row["shared_rater_guide_version"],
        }
        semantic_hash = hashlib.sha256(canonical_bytes(semantic)).hexdigest()
        require(row["semantic_input_sha256"] == semantic_hash, f"Semantic input hash mismatch for {row['item_id']}")
    return rows


def check_local_schemas_and_gate() -> None:
    base_feedback = load_json(PATHS["base_direction_h_feedback_schema"])
    registry = Registry().with_resource(
        base_feedback["$id"], Resource.from_contents(base_feedback)
    )
    for key in (
        "base_direction_h_feedback_schema",
        "feedback_schema",
        "review_receipt_schema",
        "downstream_gate_schema",
        "activation_schema",
    ):
        schema = load_json(PATHS[key])
        Draft202012Validator.check_schema(schema)
    feedback_schema = load_json(PATHS["feedback_schema"])
    # Resolving this reference now catches a missing or drifted base feedback schema.
    make_validator(PATHS["feedback_schema"], registry=registry)
    require(
        feedback_schema["properties"]["model_feedback"]["$ref"]
        == base_feedback["$id"] + "#/$defs/modelFeedback",
        "Bridge feedback no longer reuses the exact Direction H model_feedback structure",
    )

    gate = load_json(PATHS["downstream_gate"])
    assert_valid(make_validator(PATHS["downstream_gate_schema"]), gate, "Downstream gate")
    require(gate["first_stage_collection_allowed"] is False, "v1 unexpectedly permits collection")
    require(gate["model_calls_allowed"] is False, "v1 unexpectedly permits model calls")
    require(gate["empirical_feedback_effect_claims_allowed"] is False, "v1 unexpectedly permits claims")
    require(gate["old_direction_h_full_output_revision_compatible"] is False, "v1 routes to old H revision schema")

    activation_template = load_json(PATHS["activation_template"])
    assert_valid(make_validator(PATHS["activation_schema"]), activation_template, "Activation template")
    require(activation_template["record_status"] == "template_incomplete", "Activation template is not incomplete")
    require(not (BRIDGE_ROOT / "activation_record.json").exists(), "Unexpected completed activation record exists")


def check_no_outputs(prepared_only: bool) -> int:
    response_root = BRIDGE_ROOT / "responses"
    response_json = sorted(response_root.rglob("*.json"))
    require(not response_json, "Blocked v1 contains response JSON records")
    require(prepared_only or not response_json, "Response records exist")

    for path in BRIDGE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(BRIDGE_ROOT)
        if relative.parts and relative.parts[0] in {"browser", "theme_revision"}:
            # These are separately frozen successors with their own validators.
            continue
        lower = path.name.lower()
        if path in {PATHS["downstream_gate"], PATHS["activation_template"], MANIFEST_PATH}:
            continue
        require(
            not any(fragment in lower for fragment in RESULT_NAME_FRAGMENTS),
            f"Unexpected result-like artifact in qualification-only bridge: {path}",
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the synthetic, prepared-only Direction H/J bridge without private files."
    )
    parser.add_argument(
        "--prepared-only",
        action="store_true",
        help="Explicitly require zero response records (also required by this blocked v1).",
    )
    args = parser.parse_args()

    manifest = check_manifest_and_locks()
    check_upstream_run(manifest)
    items = load_and_check_items()
    rows = check_assignments(items)
    check_local_schemas_and_gate()
    response_count = check_no_outputs(args.prepared_only)
    print(
        json.dumps(
            {
                "status": "valid",
                "bridge_id": manifest["bridge_id"],
                "scope": "synthetic_qualification_only",
                "contains_real_source_text": False,
                "item_count": len(items),
                "assignment_count": len(rows),
                "response_triplet_count": response_count,
                "collection_allowed": False,
                "model_calls_allowed": False,
                "empirical_feedback_effect_claims_allowed": False,
                "private_item_key_opened": False,
                "timing_status": "blocked_pending_visibility_and_idle_aware_instrument",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BridgeValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
