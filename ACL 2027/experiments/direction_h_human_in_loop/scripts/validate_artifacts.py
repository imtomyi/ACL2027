#!/usr/bin/env python3
"""Fail-closed validation for Direction H study artifacts and collected records."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Iterable

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
        "This validator needs the Python 'jsonschema' package. No local Python "
        "runtime containing it was found; do not begin rating until the preflight works."
    )


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = DIRECTION_ROOT / "pilot"
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
RATING_SCHEMA_PATH = BASELINE_ROOT / "schemas" / "paper_metric_rating.schema.json"
OUTPUT_SCHEMA_PATH = BASELINE_ROOT / "schemas" / "qualitative_output.schema.json"
INTEGRITY_SCRIPT_PATH = BASELINE_ROOT / "scripts" / "validate_and_score.py"
PILOT_ITEM_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "pilot_item.schema.json"
FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
FREEZE_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "revision_freeze_manifest.schema.json"
FREEZE_TEMPLATE_PATH = PILOT_ROOT / "revision_freeze.template.json"
EXPECTED_RATER = "charlie_dev_researcher_01"

DISPOSITION_TO_FEEDBACK_STATUS = {
    "accept": "no_change",
    "revise": "actionable_revision",
    "reject": "reject_or_regenerate",
    "escalate": "human_escalation",
}

PRIVATE_KEYS = {
    "model_id",
    "judge_model_id",
    "generation_run_index",
    "run_index",
    "blind_id",
    "condition",
    "truth_record",
    "target_defect",
    "target_status",
    "primary_error_flag",
    "accepted_detection_flags",
}

FORBIDDEN_PUBLIC_PATH_FRAGMENTS = {
    "dataset/raw",
    "dataset/deidentified",
    "app/feedback-collector-demo/lib/study-data.ts",
    "blind_map_private.csv",
    "/judges/",
}


class ValidationFailure(Exception):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report file context
        raise ValidationFailure(f"cannot read JSON {path}: {exc}") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


def decode_pointer_token(token: str) -> str:
    """Decode one RFC 6901 token and reject malformed escape sequences."""
    decoded: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            decoded.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValidationFailure(f"malformed JSON Pointer escape in token {token!r}")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve a non-root JSON Pointer into a stored candidate output."""
    if not pointer.startswith("/"):
        raise ValidationFailure(f"output location is not a JSON Pointer: {pointer!r}")
    current = document
    for encoded_token in pointer[1:].split("/"):
        token = decode_pointer_token(encoded_token)
        if isinstance(current, dict):
            if token not in current:
                raise ValidationFailure(f"JSON Pointer does not resolve: {pointer!r}")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValidationFailure(f"invalid array index in JSON Pointer: {pointer!r}")
            position = int(token)
            if position >= len(current):
                raise ValidationFailure(f"JSON Pointer array index is out of range: {pointer!r}")
            current = current[position]
        else:
            raise ValidationFailure(f"JSON Pointer traverses a scalar: {pointer!r}")
    return current


def validator_for(schema: dict[str, Any], store: dict[str, Any] | None = None) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    resolver = RefResolver.from_schema(schema, store=store or {})
    return Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=FormatChecker(),
    )


def validate_instance(
    instance: Any,
    schema_path: Path,
    label: str,
    store: dict[str, Any] | None = None,
) -> None:
    schema = load_json(schema_path)
    errors = sorted(
        validator_for(schema, store).iter_errors(instance), key=lambda error: list(error.path)
    )
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise ValidationFailure(f"{label} fails {schema_path.name}: {rendered}")


def validate_public_pilot() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    required = [
        PILOT_ROOT / "manifest.json",
        PILOT_ROOT / "task_index.csv",
        PILOT_ROOT / "condition_commitment.json",
        RATING_SCHEMA_PATH,
        OUTPUT_SCHEMA_PATH,
        INTEGRITY_SCRIPT_PATH,
        PILOT_ITEM_SCHEMA_PATH,
        FEEDBACK_SCHEMA_PATH,
        FREEZE_SCHEMA_PATH,
        FREEZE_TEMPLATE_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValidationFailure("required file(s) missing: " + ", ".join(missing))

    for schema_path in sorted((DIRECTION_ROOT / "schemas").glob("*.schema.json")):
        Draft202012Validator.check_schema(load_json(schema_path))

    manifest = load_json(PILOT_ROOT / "manifest.json")
    if manifest.get("contains_real_source_text") is not False:
        raise ValidationFailure("manifest must explicitly set contains_real_source_text=false")
    if manifest.get("data_scope") != "synthetic_only":
        raise ValidationFailure("manifest data_scope must be synthetic_only")
    if manifest.get("intended_rater_id") != EXPECTED_RATER:
        raise ValidationFailure("manifest intended_rater_id is not the frozen Charlie case ID")
    synthetic_source = manifest.get("synthetic_source", {})
    if synthetic_source.get("source_run_provenance") != "coordinator_only":
        raise ValidationFailure("reviewer manifest must keep source-run provenance coordinator-only")
    if any(
        key in synthetic_source
        for key in ("blinded_run_path", "source_bundle", "source_blind_id", "run_index")
    ):
        raise ValidationFailure("reviewer manifest leaks recoverable source-run provenance")
    canonical = manifest.get("canonical_rating_contract", {})
    if canonical.get("annotation_version") != "qc-paper-metrics-v1":
        raise ValidationFailure("manifest does not pin qc-paper-metrics-v1")
    if canonical.get("schema_sha256") != sha256_file(RATING_SCHEMA_PATH):
        raise ValidationFailure("canonical rating schema hash drifted; stop and reconcile companion alignment")
    contract_path = PROJECT_ROOT / canonical.get("contract_path", "")
    if not contract_path.is_file() or canonical.get("contract_sha256") != sha256_file(contract_path):
        raise ValidationFailure("canonical paper-metric contract is missing or hash-drifted")

    freeze_template = load_json(FREEZE_TEMPLATE_PATH)
    validate_instance(freeze_template, FREEZE_SCHEMA_PATH, "revision freeze template")
    if freeze_template.get("status") != "draft" or freeze_template.get("study_id") != manifest.get("study_id"):
        raise ValidationFailure("revision freeze template must remain a draft for this pilot")
    if "__REQUIRED" not in json.dumps(freeze_template):
        raise ValidationFailure("revision freeze template no longer contains explicit required placeholders")
    for key in (
        "analytic_contract",
        "revision_prompt",
        "feedback_formatter",
        "input_schema",
        "output_schema",
        "integrity_validator",
        "revision_output_recorder",
        "repair_panel_packager",
    ):
        artifact = freeze_template[key]
        artifact_path = PROJECT_ROOT / artifact["path"]
        if not artifact_path.is_file() or artifact["sha256"] != sha256_file(artifact_path):
            raise ValidationFailure(f"revision freeze template artifact is missing or hash-drifted: {key}")

    output_schema = load_json(OUTPUT_SCHEMA_PATH)
    output_schema_id = output_schema.get("$id")
    ref_store = {output_schema_id: output_schema} if output_schema_id else {}
    integrity_spec = importlib.util.spec_from_file_location(
        "direction_h_shared_integrity_validator", INTEGRITY_SCRIPT_PATH
    )
    if integrity_spec is None or integrity_spec.loader is None:
        raise ValidationFailure("cannot load the shared qualitative-output integrity validator")
    integrity_module = importlib.util.module_from_spec(integrity_spec)
    integrity_spec.loader.exec_module(integrity_module)
    integrity_validator = Draft202012Validator(output_schema)

    tasks = manifest.get("tasks", [])
    if manifest.get("task_count") != len(tasks) or not tasks:
        raise ValidationFailure("manifest task_count does not match a non-empty task list")
    order_record = manifest.get("presentation_order")
    if order_record != {
        "method": "ascending_sha256(seed|task_id)",
        "seed": "direction-h-charlie-pilot-order-v1",
        "frozen_before_review": True,
    }:
        raise ValidationFailure("pilot presentation-order commitment is missing or drifted")
    ordered_tasks = sorted(tasks, key=lambda row: row["display_order"])
    if [row["display_order"] for row in ordered_tasks] != list(range(1, len(tasks) + 1)):
        raise ValidationFailure("pilot display_order values are not unique and contiguous")
    expected_order = sorted(
        (row["task_id"] for row in tasks),
        key=lambda task_id: hashlib.sha256(
            f"{order_record['seed']}|{task_id}".encode("utf-8")
        ).hexdigest(),
    )
    if [row["task_id"] for row in ordered_tasks] != expected_order:
        raise ValidationFailure("pilot presentation order does not match its frozen seed rule")
    if len({row["packet_id"] for row in tasks}) != len(tasks):
        raise ValidationFailure("reviewer queue violates one-item-per-evidence-packet separation")
    if len({row["output_id"] for row in tasks}) != len(tasks):
        raise ValidationFailure("duplicate output_id in reviewer queue")

    items: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = task["task_id"]
        item_path = PILOT_ROOT / task["item_file"]
        if not item_path.is_file():
            raise ValidationFailure(f"missing item file for {task_id}: {item_path}")
        if task.get("sha256") != sha256_file(item_path):
            raise ValidationFailure(f"item hash mismatch for {task_id}")
        raw_text = item_path.read_text(encoding="utf-8")
        if "gpt-" in raw_text.lower():
            raise ValidationFailure(f"model identity leak in reviewer item {task_id}")
        if any(fragment in raw_text for fragment in FORBIDDEN_PUBLIC_PATH_FRAGMENTS):
            raise ValidationFailure(f"forbidden source path leak in reviewer item {task_id}")
        item = load_json(item_path)
        validate_instance(item, PILOT_ITEM_SCHEMA_PATH, task_id, ref_store)
        validate_instance(
            item["candidate_output"], OUTPUT_SCHEMA_PATH, f"{task_id}.candidate_output"
        )
        leaked_keys = sorted(PRIVATE_KEYS & set(walk_keys(item)))
        if leaked_keys:
            raise ValidationFailure(f"private key leak in {task_id}: {', '.join(leaked_keys)}")
        if item.get("data_classification") != "synthetic_cc0":
            raise ValidationFailure(f"{task_id} is not classified synthetic_cc0")
        packet = item["evidence_packet"]
        output = item["candidate_output"]
        if task.get("evidence_packet_sha256") != sha256_bytes(canonical_bytes(packet)):
            raise ValidationFailure(f"evidence-packet hash mismatch for {task_id}")
        if task.get("candidate_output_sha256") != sha256_bytes(canonical_bytes(output)):
            raise ValidationFailure(f"candidate-output hash mismatch for {task_id}")
        if packet.get("status") != "synthetic_proxy_not_corpus_result":
            raise ValidationFailure(f"{task_id} packet is not an allowed synthetic proxy")
        for key in ("task_id", "packet_id", "corpus_id", "evaluation_role", "output_id"):
            if item.get(key) != task.get(key):
                raise ValidationFailure(f"{task_id} identity mismatch for {key}")
        if packet.get("packet_id") != item["packet_id"] or output.get("packet_id") != item["packet_id"]:
            raise ValidationFailure(f"{task_id} packet/output packet_id mismatch")
        if output.get("research_question") != packet.get("research_question"):
            raise ValidationFailure(f"{task_id} research question drift")
        integrity_envelope = {
            "run_record_version": "direction-h-integrity-check-v1",
            "qualification_scope": "synthetic_only",
            "model_id": "blinded_integrity_check",
            "run_index": 1,
            "packet_id": item["packet_id"],
            "prompt_version": "qc-direct-v1",
            "schema_version": "qualitative-output-v1",
            "generated_at_utc": manifest["created_at"],
            "output": output,
        }
        metrics, integrity_issues, _ = integrity_module.validate_record(
            integrity_envelope,
            {item["packet_id"]: packet},
            integrity_validator,
            item_path.name,
            1,
        )
        if metrics.get("hard_gate_pass") != 1:
            details = ", ".join(
                f"{issue['kind']}: {issue['detail']}" for issue in integrity_issues[:12]
            )
            raise ValidationFailure(f"{task_id} fails the shared integrity gate: {details}")
        items[task_id] = item

    with (PILOT_ROOT / "task_index.csv").open(encoding="utf-8", newline="") as handle:
        index_rows = list(csv.DictReader(handle))
    if [row["task_id"] for row in index_rows] != [
        row["task_id"] for row in sorted(tasks, key=lambda row: row["display_order"])
    ]:
        raise ValidationFailure("task_index.csv order/IDs do not match manifest")
    if any(row.get("review_status") != "not_started" for row in index_rows):
        raise ValidationFailure(
            "task_index.csv is an immutable launch index; response status belongs in derived validation output"
        )
    return manifest, items


def validate_responses(manifest: dict[str, Any], items: dict[str, dict[str, Any]]) -> tuple[int, int]:
    rating_dir = PILOT_ROOT / "responses" / "ratings"
    feedback_dir = PILOT_ROOT / "responses" / "feedback"
    rating_paths = {path.stem: path for path in rating_dir.glob("*.json")} if rating_dir.exists() else {}
    feedback_paths = {path.stem: path for path in feedback_dir.glob("*.json")} if feedback_dir.exists() else {}
    if set(rating_paths) != set(feedback_paths):
        raise ValidationFailure("every submitted task must have exactly one rating and one feedback record")
    unknown = set(rating_paths) - set(items)
    if unknown:
        raise ValidationFailure("responses exist for unknown task(s): " + ", ".join(sorted(unknown)))
    seen_outputs: set[tuple[str, str, str]] = set()
    seen_feedback_ids: set[str] = set()
    for task_id in sorted(rating_paths):
        item = items[task_id]
        rating = load_json(rating_paths[task_id])
        feedback = load_json(feedback_paths[task_id])
        validate_instance(rating, RATING_SCHEMA_PATH, f"rating {task_id}")
        validate_instance(feedback, FEEDBACK_SCHEMA_PATH, f"feedback {task_id}")
        expected = {
            "rater_id": EXPECTED_RATER,
            "evaluator_group": "researcher",
            "packet_id": item["packet_id"],
            "corpus_id": item["corpus_id"],
            "evaluation_role": item["evaluation_role"],
            "output_id": item["output_id"],
        }
        for key, value in expected.items():
            if rating.get(key) != value:
                raise ValidationFailure(f"rating {task_id} has unexpected {key}")
        if "requested_expertise" not in rating:
            raise ValidationFailure(
                f"rating {task_id} omits requested_expertise required by the Direction H collection rule"
            )
        unique_key = (rating["rater_id"], rating["packet_id"], rating["output_id"])
        if unique_key in seen_outputs:
            raise ValidationFailure(f"duplicate core rating key for {task_id}")
        seen_outputs.add(unique_key)
        rating_key = feedback["rating_key"]
        for key in ("annotation_version", "rater_id", "packet_id", "output_id", "rated_at_utc"):
            if rating_key.get(key) != rating.get(key):
                raise ValidationFailure(f"feedback {task_id} rating_key mismatch for {key}")
        if rating_key.get("rating_record_sha256") != sha256_bytes(canonical_bytes(rating)):
            raise ValidationFailure(f"feedback {task_id} rating hash mismatch")
        if feedback.get("pilot_item_id") != task_id:
            raise ValidationFailure(f"feedback {task_id} pilot_item_id mismatch")
        feedback_id = feedback["feedback_id"]
        if feedback_id in seen_feedback_ids:
            raise ValidationFailure(f"duplicate feedback_id in {task_id}: {feedback_id}")
        seen_feedback_ids.add(feedback_id)
        if feedback.get("created_at_utc") != rating.get("rated_at_utc"):
            raise ValidationFailure(f"feedback {task_id} creation time differs from its linked rating")
        expected_status = DISPOSITION_TO_FEEDBACK_STATUS[rating["disposition"]]
        if feedback.get("feedback_status") != expected_status:
            raise ValidationFailure(f"feedback {task_id} status does not match rating disposition")
        excerpt_ids = {
            excerpt["excerpt_id"] for excerpt in item["evidence_packet"]["excerpts"]
        }
        finding_ids: set[str] = set()
        for finding in feedback["model_feedback"].get("findings", []):
            finding_id = finding["finding_id"]
            if finding_id in finding_ids:
                raise ValidationFailure(f"duplicate finding_id in feedback {task_id}: {finding_id}")
            finding_ids.add(finding_id)
            unknown_excerpt_ids = set(finding["evidence_excerpt_ids"]) - excerpt_ids
            if unknown_excerpt_ids:
                raise ValidationFailure(
                    f"feedback {task_id} cites unknown excerpt ID(s): "
                    + ", ".join(sorted(unknown_excerpt_ids))
                )
            for pointer in finding["output_locations"]:
                try:
                    resolve_json_pointer(item["candidate_output"], pointer)
                except ValidationFailure as exc:
                    raise ValidationFailure(
                        f"feedback {task_id} finding {finding_id}: {exc}"
                    ) from exc
        serious_finding_flags = {
            row["error_flag"]
            for row in feedback["model_feedback"].get("findings", [])
            if row["severity"] == "serious"
        }
        if set(rating["serious_error_flags"]) != serious_finding_flags:
            raise ValidationFailure(
                f"rating {task_id} serious-error flags do not exactly match serious feedback findings"
            )
    return len(rating_paths), len(feedback_paths)


def validate_lock_and_debrief(manifest: dict[str, Any]) -> tuple[bool, bool]:
    lock_path = PILOT_ROOT / "review_lock.json"
    debrief_path = PILOT_ROOT / "responses" / "blinding_debrief.json"
    if not lock_path.exists():
        if debrief_path.exists():
            raise ValidationFailure("a blinding debrief exists before the required review lock")
        return False, False
    lock = load_json(lock_path)
    expected_ids = [row["task_id"] for row in manifest["tasks"]]
    if lock.get("review_lock_version") != "direction-h-review-lock-v1":
        raise ValidationFailure("unknown review lock version")
    if lock.get("study_id") != manifest.get("study_id"):
        raise ValidationFailure("review lock study_id mismatch")
    if lock.get("rater_id") != EXPECTED_RATER:
        raise ValidationFailure("review lock rater mismatch")
    if lock.get("task_count") != len(expected_ids):
        raise ValidationFailure("review lock task count mismatch")
    if lock.get("manifest_sha256") != sha256_file(PILOT_ROOT / "manifest.json"):
        raise ValidationFailure("pilot manifest changed after review lock")
    if lock.get("condition_commitment_sha256") != sha256_file(
        PILOT_ROOT / "condition_commitment.json"
    ):
        raise ValidationFailure("condition commitment changed after review lock")
    if lock.get("truth_opened_by_this_step") is not False:
        raise ValidationFailure("review lock does not attest truth remained closed")
    if lock.get("ratings_or_feedback_modified_by_this_step") is not False:
        raise ValidationFailure("review lock reports modifying a response")
    records = lock.get("records", [])
    if [record.get("task_id") for record in records] != expected_ids:
        raise ValidationFailure("review lock task order or coverage mismatch")
    for record in records:
        task_id = record["task_id"]
        expected_rating = Path("responses") / "ratings" / f"{task_id}.json"
        expected_feedback = Path("responses") / "feedback" / f"{task_id}.json"
        if Path(record.get("rating_file", "")) != expected_rating:
            raise ValidationFailure(f"unexpected locked rating path for {task_id}")
        if Path(record.get("feedback_file", "")) != expected_feedback:
            raise ValidationFailure(f"unexpected locked feedback path for {task_id}")
        rating_path = PILOT_ROOT / expected_rating
        feedback_path = PILOT_ROOT / expected_feedback
        if not rating_path.is_file() or record.get("rating_sha256") != sha256_file(rating_path):
            raise ValidationFailure(f"locked rating is missing or drifted for {task_id}")
        if not feedback_path.is_file() or record.get("feedback_sha256") != sha256_file(feedback_path):
            raise ValidationFailure(f"locked feedback is missing or drifted for {task_id}")
    if not debrief_path.exists():
        return True, False
    debrief = load_json(debrief_path)
    validate_instance(
        debrief,
        DIRECTION_ROOT / "schemas" / "blinding_debrief.schema.json",
        "post-lock blinding debrief",
    )
    return True, True


def validate_coordinator_commitment(manifest: dict[str, Any]) -> bool:
    commitment = load_json(PILOT_ROOT / "condition_commitment.json")
    truth_path = DIRECTION_ROOT / "coordinator_only" / "truth_map.json"
    truth = load_json(truth_path)
    validate_instance(
        truth,
        DIRECTION_ROOT / "schemas" / "truth_map.schema.json",
        "coordinator truth map",
    )
    if commitment.get("study_id") != manifest.get("study_id") or truth.get("study_id") != manifest.get("study_id"):
        raise ValidationFailure("study_id mismatch across public manifest, commitment, and truth map")
    if commitment.get("truth_map_sha256") != sha256_bytes(canonical_bytes(truth)):
        raise ValidationFailure("coordinator truth map no longer matches its pre-rating commitment")
    public_ids = {row["task_id"] for row in manifest["tasks"]}
    truth_ids = {row["task_id"] for row in truth.get("items", [])}
    if public_ids != truth_ids:
        raise ValidationFailure("truth/public task sets differ")
    for row in truth["items"]:
        source_bundle = PROJECT_ROOT / row["source_bundle"]
        if not source_bundle.is_file() or row["source_bundle_sha256"] != sha256_file(source_bundle):
            raise ValidationFailure(f"source bundle missing or drifted for {row['task_id']}")
        if any(part in row["source_bundle"] for part in ("dataset/raw", "dataset/deidentified")):
            raise ValidationFailure(f"protected-data path in truth map for {row['task_id']}")
    registry = load_json(DIRECTION_ROOT / "coordinator_only" / "rater_registry.json")
    validate_instance(
        registry,
        DIRECTION_ROOT / "schemas" / "rater_registry.schema.json",
        "rater registry",
    )
    matching = [row for row in registry["raters"] if row["rater_id"] == EXPECTED_RATER]
    if len(matching) != 1 or matching[0]["include_in_primary_independent_human_pool"] is not False:
        raise ValidationFailure("Charlie registry entry is missing or not excluded from the independent-human pool")
    if matching[0]["blinding_status"] != "condition_masked_developer":
        raise ValidationFailure(
            "the v1 shared-workspace pilot cannot be promoted to technically blinded "
            "without a new instrument and independent access-control attestation"
        )
    verification_path = DIRECTION_ROOT / "coordinator_only" / "construction_verification.json"
    if not verification_path.exists():
        return False
    verification = load_json(verification_path)
    validate_instance(
        verification,
        DIRECTION_ROOT / "schemas" / "construction_verification.schema.json",
        "construction verification",
    )
    if verification["truth_map_sha256"] != commitment["truth_map_sha256"]:
        raise ValidationFailure("construction verification cites the wrong committed truth map")
    rows = verification["items"]
    if {row["task_id"] for row in rows} != {row["task_id"] for row in manifest["tasks"]}:
        raise ValidationFailure("construction verification task set differs from the pilot manifest")
    truth_by_id = {row["task_id"]: row for row in truth["items"]}
    for row in rows:
        expected = truth_by_id[row["task_id"]]
        expected_flag = (
            expected["planted_defect"]["target_flag"] if expected["planted_defect"] else None
        )
        if row["intended_condition"] != expected["condition"]:
            raise ValidationFailure(f"construction verification condition mismatch for {row['task_id']}")
        if row["intended_target_flag"] != expected_flag:
            raise ValidationFailure(f"construction verification target mismatch for {row['task_id']}")
    return any(
        truth_by_id[row["task_id"]]["condition"] == "controlled_defect"
        and row["disposition"] == "verified_for_detection"
        for row in rows
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reviewer-safe",
        action="store_true",
        help="Validate only reviewer-visible artifacts and responses; never open coordinator truth.",
    )
    args = parser.parse_args()
    try:
        manifest, items = validate_public_pilot()
        rating_count, feedback_count = validate_responses(manifest, items)
        review_lock_present, blinding_debrief_present = validate_lock_and_debrief(manifest)
        detection_analysis_ready = False
        if not args.reviewer_safe:
            detection_analysis_ready = validate_coordinator_commitment(manifest)
    except ValidationFailure as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "valid",
                "mode": "reviewer_safe" if args.reviewer_safe else "coordinator",
                "synthetic_items": len(items),
                "ratings_present": rating_count,
                "feedback_records_present": feedback_count,
                "review_lock_present": review_lock_present,
                "blinding_debrief_present": blinding_debrief_present,
                "contains_real_source_text": False,
                "empirical_results_present": False,
                "detection_analysis_ready": detection_analysis_ready,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
