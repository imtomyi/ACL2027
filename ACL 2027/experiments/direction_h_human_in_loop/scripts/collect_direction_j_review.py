#!/usr/bin/env python3
"""Collect one exact Direction J rating plus Direction H feedback and receipt.

This reviewer-side collector never opens Direction J's private item key. It is
prepared for a prospective bridge activation; running it creates real study
observations and must not be done merely to test the software.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        "This collector needs local jsonschema and referencing packages. "
        "Do not begin rating until the reviewer-safe preflight works."
    )


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRIDGE_ROOT = DIRECTION_ROOT / "companion_j_bridge"
MANIFEST_PATH = BRIDGE_ROOT / "manifest.json"
RESPONSE_ROOT = BRIDGE_ROOT / "responses"
J_ROOT = PROJECT_ROOT / "experiments" / "direction_j_llm_as_rater"
J_RUN_ROOT = J_ROOT / "runs" / "20260825_synthetic_paired_qualification_prepared"
ITEMS_PATH = J_RUN_ROOT / "evaluator_items.jsonl"
ASSIGNMENT_PATH = J_RUN_ROOT / "assignments" / "charlie_rep1.csv"
GUIDE_PATH = J_ROOT / "protocol" / "shared_rater_guide_v1.md"
RATING_SCHEMA_PATH = J_ROOT / "schemas" / "shared_rating.schema.json"
H_FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_feedback_record.schema.json"
RECEIPT_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_review_receipt.schema.json"
ACTIVATION_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_bridge_activation.schema.json"
INSTRUMENT_PATH = DIRECTION_ROOT / "protocol" / "direction_j_charlie_instrument_v1.md"

METRICS = [
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
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

DISPOSITIONS = ["accept", "revise", "reject", "escalate"]
EXPERTISE = ["none", "qualitative_methods", "domain", "both"]

STATUS_BY_DISPOSITION = {
    "accept": "no_change",
    "revise": "actionable_revision",
    "reject": "reject_or_regenerate",
    "escalate": "human_escalation",
}

# The terminal cannot implement Direction J's visibility/idle timing contract,
# and the theme-level downstream intervention has not been prospectively frozen.
# A new version must replace this constant and its frozen gate together before
# any observation is collected; never bypass it with a runtime flag.
COLLECTION_BLOCKED = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_items() -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(ITEMS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        item = json.loads(line)
        item_id = item["item_id"]
        if item_id in items:
            raise SystemExit(f"Duplicate item_id on evaluator-items line {number}.")
        items[item_id] = item
    return items


def load_assignments() -> list[dict[str, str]]:
    with ASSIGNMENT_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted(rows, key=lambda row: int(row["sequence"]))


def validate_record(
    value: dict[str, Any],
    schema_path: Path,
    *,
    registry: Registry | None = None,
) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        registry=registry or Registry(),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        detail = "\n".join(
            f"- {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise SystemExit(f"Record fails {schema_path.name}:\n{detail}")


def run_reviewer_safe_preflight() -> None:
    validator_path = DIRECTION_ROOT / "scripts" / "validate_direction_j_bridge.py"
    result = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=DIRECTION_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(
            "Direction J bridge preflight failed; no guide or item was displayed. "
            + (detail or "The validator returned a nonzero status.")
        )
    try:
        status = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SystemExit(
            "Direction J bridge preflight returned an unreadable status; no item was displayed."
        ) from exc
    if (
        status.get("status") != "valid"
        or status.get("contains_real_source_text") is not False
        or status.get("item_count") != 24
        or status.get("assignment_count") != 24
    ):
        raise SystemExit(
            "Direction J bridge preflight did not affirm the frozen synthetic queue; "
            "no item was displayed."
        )


def require_coordinator_activation() -> None:
    activation_path = BRIDGE_ROOT / "activation_record.json"
    if not activation_path.is_file():
        raise SystemExit(
            "COLLECTION BLOCKED: no coordinator activation_record.json exists. "
            "Charlie cannot self-authorize. Nothing was displayed or written."
        )
    activation = load_json(activation_path)
    validate_record(activation, ACTIVATION_SCHEMA_PATH)
    if activation["record_status"] != "activated":
        raise SystemExit("COLLECTION BLOCKED: coordinator activation is not active.")
    expected_locks = {
        "bridge_manifest_sha256": sha256_file(MANIFEST_PATH),
        "human_instrument_sha256": sha256_file(INSTRUMENT_PATH),
        "charlie_assignment_sha256": sha256_file(ASSIGNMENT_PATH),
        "evaluator_items_sha256": sha256_file(ITEMS_PATH),
        "shared_rating_schema_sha256": sha256_file(RATING_SCHEMA_PATH),
        "downstream_gate_sha256": sha256_file(BRIDGE_ROOT / "downstream_gate.json"),
    }
    if activation["locks"] != expected_locks:
        raise SystemExit(
            "COLLECTION BLOCKED: coordinator activation hashes do not match this bridge."
        )


def response_stem(row: dict[str, str]) -> str:
    return f"{int(row['sequence']):03d}_{row['item_id']}"


def response_paths(row: dict[str, str]) -> tuple[Path, Path, Path]:
    stem = response_stem(row)
    return (
        RESPONSE_ROOT / "ratings" / f"{stem}.json",
        RESPONSE_ROOT / "feedback" / f"{stem}.json",
        RESPONSE_ROOT / "receipts" / f"{stem}.json",
    )


def choose_assignment(sequence: int | None) -> tuple[dict[str, str], dict[str, Any]]:
    assignments = load_assignments()
    items = load_items()
    first_missing: dict[str, str] | None = None
    gap_seen = False
    for row in assignments:
        paths = response_paths(row)
        existence = [path.exists() for path in paths]
        if any(existence) and not all(existence):
            raise SystemExit(
                f"Partial response triplet exists for sequence {row['sequence']}; "
                "stop and preserve it for coordinator review."
            )
        if all(existence):
            if gap_seen:
                raise SystemExit("Completed response appears after a sequence gap; refusing collection.")
        else:
            gap_seen = True
            if first_missing is None:
                first_missing = row
    if first_missing is None:
        raise SystemExit("All 24 Charlie assignments already have complete response triplets.")
    if sequence is not None and int(first_missing["sequence"]) != sequence:
        raise SystemExit(
            f"The next frozen assignment is sequence {first_missing['sequence']}; "
            "refusing an out-of-order preview."
        )
    return first_missing, items[first_missing["item_id"]]


def prompt_nonempty(prompt: str, *, maximum: int | None = None) -> str:
    while True:
        value = input(prompt).strip()
        if not value:
            print("A non-empty response is required.")
            continue
        if maximum is not None and len(value) > maximum:
            print(f"Keep this response at or below {maximum} characters.")
            continue
        return value


def prompt_scale(label: str, *, allow_cannot_judge: bool = True) -> int | None:
    suffix = " [1-5 or cj]: " if allow_cannot_judge else " [1-5]: "
    while True:
        value = input(label + suffix).strip().lower()
        if allow_cannot_judge and value in {"cj", "cannot judge", "cannot_judge"}:
            return None
        if value in {"1", "2", "3", "4", "5"}:
            return int(value)
        print("Enter 1, 2, 3, 4, 5" + (", or cj." if allow_cannot_judge else "."))


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
        for part in [piece.strip() for piece in raw.split(",") if piece.strip()]:
            if part.isdigit() and 1 <= int(part) <= len(choices):
                selected.append(choices[int(part) - 1])
            elif part in choices:
                selected.append(part)
            else:
                invalid.append(part)
        if not invalid:
            return list(dict.fromkeys(selected))
        print("Unknown selection(s): " + ", ".join(invalid))


def prompt_list(label: str, *, require_one: bool = False, maximum: int = 12) -> list[str]:
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
        if len(values) >= maximum:
            return values


def decode_pointer_token(token: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            output.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValueError(f"malformed JSON Pointer escape in {token!r}")
        output.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(output)


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError("pointer must begin with '/'")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = decode_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"key {token!r} does not exist")
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError(f"invalid array index {token!r}")
            position = int(token)
            if position >= len(current):
                raise ValueError(f"array index {position} is out of range")
            current = current[position]
        else:
            raise ValueError("pointer traverses a scalar")
    return current


def collect_findings(*, required: bool) -> list[dict[str, Any]]:
    if not required:
        answer = input("Record an actionable feedback finding? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            return []
    findings: list[dict[str, Any]] = []
    while True:
        print(f"\nFinding {len(findings) + 1}")
        finding = {
            "finding_id": f"F{len(findings) + 1:02d}",
            "error_flag": prompt_choice("Error family:", ERROR_FLAGS),
            "severity": prompt_choice("Finding severity:", ["minor", "material", "serious"]),
            "output_locations": prompt_list(
                "JSON Pointer location(s) relative to proposed_interpretation, e.g. /claim:",
                require_one=True,
            ),
            "evidence_excerpt_ids": prompt_list(
                "Relevant displayed excerpt IDs (blank is allowed for a structural issue):",
                maximum=20,
            ),
            "issue": prompt_nonempty("What is wrong or uncertain? ", maximum=2000),
            "requested_change": prompt_nonempty(
                "What should the frozen revision model change or check? ", maximum=2000
            ),
        }
        findings.append(finding)
        if len(findings) >= 12:
            break
        if input("Add another finding? [y/N]: ").strip().lower() not in {"y", "yes"}:
            break
    return findings


def validate_findings(item: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    excerpt_ids = {row["excerpt_id"] for row in item["evidence"]}
    for finding in findings:
        unknown = set(finding["evidence_excerpt_ids"]) - excerpt_ids
        if unknown:
            raise SystemExit(
                f"Finding {finding['finding_id']} cites unknown excerpt ID(s): "
                + ", ".join(sorted(unknown))
            )
        for pointer in finding["output_locations"]:
            try:
                resolve_pointer(item["proposed_interpretation"], pointer)
            except ValueError as exc:
                raise SystemExit(
                    f"Finding {finding['finding_id']} has an invalid proposed-interpretation "
                    f"location {pointer!r}: {exc}"
                ) from exc


def render_input(row: dict[str, str], item: dict[str, Any]) -> None:
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    print("\n" + "=" * 78)
    print("FROZEN DIRECTION J SHARED RATER GUIDE — COMPLETE")
    print("=" * 78)
    print(guide, end="" if guide.endswith("\n") else "\n")
    print("\n" + "=" * 78)
    print(
        f"FROZEN CHARLIE ASSIGNMENT {row['sequence']}/24 | "
        f"ITEM {item['item_id']}"
    )
    print("Synthetic fictional evidence. Candidate identity and condition are omitted.")
    print("The JSON object below is the complete canonical evaluator item.")
    print("=" * 78)
    print(json.dumps(item, ensure_ascii=False, indent=2))
    print("=" * 78)
    sys.stdout.flush()


def write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def commit_triplet(paths: tuple[Path, Path, Path], payloads: tuple[bytes, bytes, bytes]) -> None:
    if any(path.exists() for path in paths):
        raise SystemExit("A response file appeared during collection; refusing to overwrite it.")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    pending = [path.parent / f".{path.name}.{token}.pending" for path in paths]
    committed: list[Path] = []
    try:
        for path, payload in zip(pending, payloads, strict=True):
            write_exclusive(path, payload)
        for source, target in zip(pending, paths, strict=True):
            os.link(source, target)
            committed.append(target)
    except BaseException:
        for target in committed:
            target.unlink(missing_ok=True)
        raise
    finally:
        for path in pending:
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect the next exact Direction J Charlie rating plus Direction H feedback. "
            "Do not run until the bridge has been prospectively activated."
        )
    )
    parser.add_argument(
        "--sequence",
        type=int,
        choices=range(1, 25),
        metavar="1..24",
        help="Optional explicit sequence; it must be the next frozen assignment.",
    )
    args = parser.parse_args()

    run_reviewer_safe_preflight()
    manifest = load_json(MANIFEST_PATH)
    if manifest["status"] != "prepared_not_activated_or_run":
        raise SystemExit("Unexpected bridge status; no item was displayed.")
    gate = load_json(BRIDGE_ROOT / "downstream_gate.json")
    if COLLECTION_BLOCKED or gate["first_stage_collection_allowed"] is not True:
        raise SystemExit(
            "COLLECTION BLOCKED before guide/item display: Direction J timing requires a "
            "visibility- and idle-aware human instrument, and no prospective theme-level "
            "feedback-versus-no-feedback revision/repair contract is frozen. Create a new "
            "version; do not edit or bypass this v1 gate. Nothing was displayed or written."
        )
    require_coordinator_activation()
    row, item = choose_assignment(args.sequence)
    if row["actor_id"] != "charlie" or row["actor_kind"] != "human":
        raise SystemExit("The selected assignment is not the frozen Charlie human assignment.")

    render_input(row, item)
    started_at = utc_now()
    rating_started_monotonic = time.monotonic()

    print(
        "\nEXACT DIRECTION J SHARED RATING\n"
        "Use the complete guide above. Use cj only when that construct cannot be judged."
    )
    scores: dict[str, int | None] = {}
    cannot_judge: list[str] = []
    for metric in METRICS:
        value = prompt_scale(metric)
        scores[metric] = value
        if value is None:
            cannot_judge.append(metric)
    confidence = prompt_scale(
        "confidence in this judgment (1=very uncertain, 5=very certain)",
        allow_cannot_judge=False,
    )
    disposition = prompt_choice("Disposition:", DISPOSITIONS)
    requested_expertise = prompt_choice("Requested expertise:", EXPERTISE)
    serious_flags = prompt_many("Serious-error flags:", ERROR_FLAGS)
    rationale = prompt_nonempty("Concise source-grounded rationale: ", maximum=1000)

    rating_completed_at = utc_now()
    rating_completed_monotonic = time.monotonic()
    rating_wall_seconds = round(rating_completed_monotonic - rating_started_monotonic, 3)
    rating = {
        "rating_schema_version": "direction-j-shared-rating-v1",
        "evidential_credibility": scores["evidential_credibility"],
        "voice_boundary_preservation": scores["voice_boundary_preservation"],
        "scope_calibration": scores["scope_calibration"],
        "cannot_judge": cannot_judge,
        "confidence": confidence,
        "disposition": disposition,
        "requested_expertise": requested_expertise,
        "serious_error_flags": serious_flags,
        "rationale": rationale,
    }
    validate_record(rating, RATING_SCHEMA_PATH)

    print(
        "\nDIRECTION H FEEDBACK SIDECAR\n"
        "Rating time has stopped. Feedback time is measured separately."
    )
    feedback_started_monotonic = time.monotonic()
    feedback_status = STATUS_BY_DISPOSITION[disposition]
    feedback_summary = prompt_nonempty(
        "Identity-free feedback summary (for no change, say what to preserve): ",
        maximum=3000,
    )
    if feedback_status == "no_change":
        findings: list[dict[str, Any]] = []
    else:
        findings = collect_findings(
            required=feedback_status in {"actionable_revision", "reject_or_regenerate"}
        )
    preserve = prompt_list("Accurate material the revision should preserve:")
    uncertainties = prompt_list("Uncertainties the revision should not overresolve:")
    feedback_completed_at = utc_now()
    feedback_completed_monotonic = time.monotonic()
    feedback_wall_seconds = round(feedback_completed_monotonic - feedback_started_monotonic, 3)

    rating_hash = sha256_bytes(canonical_bytes(rating))
    feedback_id = "DHJF_" + hashlib.sha256(
        ("direction-h-direction-j-feedback-v1|" + row["assignment_id"]).encode("utf-8")
    ).hexdigest()[:16]
    feedback = {
        "feedback_version": "direction-h-direction-j-feedback-v1",
        "feedback_id": feedback_id,
        "bridge_id": "direction-h-direction-j-synthetic-qualification-v1",
        "assignment_id": row["assignment_id"],
        "item_id": row["item_id"],
        "rating_key": {
            "rating_schema_version": "direction-j-shared-rating-v1",
            "rating_record_sha256": rating_hash,
            "actor_id": "charlie",
            "rating_repetition": 1,
            "item_id": row["item_id"],
            "packet_id": row["packet_id"],
            "output_id": row["output_id"],
        },
        "feedback_status": feedback_status,
        "model_feedback": {
            "feedback_summary": feedback_summary,
            "findings": findings,
            "preserve": preserve,
            "uncertainties": uncertainties,
        },
        "created_at_utc": feedback_completed_at,
    }
    h_feedback_schema = load_json(H_FEEDBACK_SCHEMA_PATH)
    registry = Registry().with_resource(
        h_feedback_schema["$id"], Resource.from_contents(h_feedback_schema)
    )
    validate_record(feedback, FEEDBACK_SCHEMA_PATH, registry=registry)
    validate_findings(item, findings)
    serious_finding_flags = {
        finding["error_flag"] for finding in findings if finding["severity"] == "serious"
    }
    if serious_finding_flags != set(serious_flags):
        raise SystemExit(
            "Shared serious_error_flags must exactly equal feedback findings marked serious. "
            "Nothing was written."
        )

    feedback_hash = sha256_bytes(canonical_bytes(feedback))
    receipt = {
        "receipt_version": "direction-h-direction-j-review-receipt-v1",
        "bridge_id": "direction-h-direction-j-synthetic-qualification-v1",
        "study_id": "direction-j-v1",
        "run_id": "20260825_synthetic_paired_qualification_prepared",
        "assignment_id": row["assignment_id"],
        "sequence": int(row["sequence"]),
        "item_id": row["item_id"],
        "packet_id": row["packet_id"],
        "output_id": row["output_id"],
        "corpus_id": row["corpus_id"],
        "evaluation_role": row["evaluation_role"],
        "actor_id": "charlie",
        "actor_kind": "human",
        "rating_repetition": 1,
        "direction_h_case": {
            "case_id": "charlie_dev_researcher_01",
            "evaluator_group": "researcher",
            "case_role": "developer_researcher_case_baseline",
            "construction_involved": True,
            "independent_human_pool_eligible": False,
            "universal_ground_truth": False,
        },
        "item_payload_sha256": row["item_payload_sha256"],
        "interface_version": row["interface_version"],
        "shared_rater_guide_version": row["shared_rater_guide_version"],
        "shared_rater_guide_sha256": row["shared_rater_guide_sha256"],
        "semantic_input_sha256": row["semantic_input_sha256"],
        "prompt_or_instrument_version": "direction-h-direction-j-charlie-instrument-v1",
        "prompt_or_instrument_sha256": sha256_file(INSTRUMENT_PATH),
        "started_at_utc": started_at,
        "rating_completed_at_utc": rating_completed_at,
        "feedback_completed_at_utc": feedback_completed_at,
        "rating_wall_seconds": max(rating_wall_seconds, 0.001),
        "feedback_wall_seconds": max(feedback_wall_seconds, 0.0),
        "timing_method": {
            "start_event": "complete_shared_guide_and_item_rendered",
            "rating_stop_event": "last_exact_rating_field_received_before_feedback",
            "feedback_stop_event": "last_feedback_field_received",
            "measurement": "continuous_cli_wall_elapsed",
            "visibility_tracking_available": False,
            "idle_pause_rule_available": False,
            "direction_j_review_seconds_eligible": False,
        },
        "rating_record_sha256": rating_hash,
        "feedback_record_sha256": feedback_hash,
        "blinding": {
            "presented_item_omits_candidate_identity": True,
            "presented_item_omits_condition": True,
            "presented_item_omits_other_ratings": True,
            "workspace_classification": "condition_masked_developer",
            "private_map_access_separated": False,
            "unblinded_at_utc": None,
        },
        "paired_observation_status": "pending_coordinator_private_join",
    }
    validate_record(receipt, RECEIPT_SCHEMA_PATH)

    print("\nREVIEW SUMMARY (not yet saved)")
    print(json.dumps({"rating": rating, "feedback": feedback, "receipt": receipt}, indent=2))
    if input("Save the immutable three-record first pass? Type SAVE: ").strip() != "SAVE":
        raise SystemExit("Nothing was written.")

    paths = response_paths(row)
    commit_triplet(
        paths,
        (canonical_bytes(rating), canonical_bytes(feedback), canonical_bytes(receipt)),
    )
    print("Saved one atomic rating/feedback/receipt triplet:")
    for path in paths:
        print(f"- {path.relative_to(DIRECTION_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Nothing was written.", file=sys.stderr)
        raise SystemExit(130)
