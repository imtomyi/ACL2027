#!/usr/bin/env python3
"""Collect one blinded Direction H rating and linked revision feedback record."""

from __future__ import annotations

import argparse
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
RATING_SCHEMA_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "qualitative_coding_baselines"
    / "schemas"
    / "paper_metric_rating.schema.json"
)
FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
RATER_ID = "charlie_dev_researcher_01"

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

DISPOSITIONS = ["accept", "revise", "reject", "escalate"]
EXPERTISE = ["none", "qualitative_methods", "domain", "both"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


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


def validate_findings(item: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    excerpt_ids = {
        excerpt["excerpt_id"] for excerpt in item["evidence_packet"]["excerpts"]
    }
    for finding in findings:
        unknown = set(finding["evidence_excerpt_ids"]) - excerpt_ids
        if unknown:
            raise SystemExit(
                f"Finding {finding['finding_id']} cites unknown excerpt ID(s): "
                + ", ".join(sorted(unknown))
                + ". Nothing was written."
            )
        for pointer in finding["output_locations"]:
            try:
                resolve_json_pointer(item["candidate_output"], pointer)
            except ValueError as exc:
                raise SystemExit(
                    f"Finding {finding['finding_id']} has an invalid output location ({exc}). "
                    "Nothing was written."
                ) from exc


def prompt_nonempty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("A non-empty response is required.")


def prompt_scale(label: str, allow_cannot_judge: bool = True) -> int | None:
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
    output = item["candidate_output"]
    print("\n" + "=" * 78)
    print(f"TASK {item['task_id']}  |  PACKET {item['packet_id']}  |  OUTPUT {item['output_id']}")
    print("SYNTHETIC/fictional evidence only. Model and condition are blinded.")
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
    print("\nCANDIDATE OUTPUT (complete structured record)")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("\n" + "=" * 78)


def choose_task(task_id: str | None) -> tuple[dict[str, Any], Path]:
    manifest = load_json(PILOT_ROOT / "manifest.json")
    rating_dir = PILOT_ROOT / "responses" / "ratings"
    tasks = sorted(manifest["tasks"], key=lambda row: row["display_order"])
    remaining = [row for row in tasks if not (rating_dir / f"{row['task_id']}.json").exists()]
    if not remaining:
        raise SystemExit("All pilot tasks already have locked first-pass ratings.")
    if task_id:
        matches = [row for row in tasks if row["task_id"] == task_id]
        if len(matches) != 1:
            raise SystemExit(f"Unknown task: {task_id}")
        selected = matches[0]
        if selected["task_id"] != remaining[0]["task_id"]:
            raise SystemExit(
                f"The next locked task is {remaining[0]['task_id']}; refusing out-of-order preview."
            )
    else:
        selected = remaining[0]
    rating_path = rating_dir / f"{selected['task_id']}.json"
    feedback_path = PILOT_ROOT / "responses" / "feedback" / f"{selected['task_id']}.json"
    if rating_path.exists() or feedback_path.exists():
        raise SystemExit(
            f"Task {selected['task_id']} already has a response file. Refusing to overwrite it."
        )
    return load_json(PILOT_ROOT / selected["item_file"]), PILOT_ROOT / selected["item_file"]


def collect_findings(required: bool) -> list[dict[str, Any]]:
    if not required and input("Record an actionable finding? [y/N]: ").strip().lower() not in {"y", "yes"}:
        return []
    findings: list[dict[str, Any]] = []
    while True:
        print(f"\nFinding {len(findings) + 1}")
        error_flag = prompt_choice("Error family:", ERROR_FLAGS)
        severity = prompt_choice("Finding severity:", ["minor", "material", "serious"])
        output_locations = prompt_list(
            "Output JSON Pointer location(s), such as /themes/0/claim:", require_one=True
        )
        for location in output_locations:
            if not location.startswith("/"):
                raise SystemExit(f"Output location must start with '/': {location}")
        evidence_ids = prompt_list(
            "Relevant supplied excerpt IDs (blank is allowed when the issue is structural):"
        )
        issue = prompt_nonempty("What is wrong or uncertain? ")
        requested_change = prompt_nonempty("What should the revision model change or check? ")
        findings.append(
            {
                "finding_id": f"F{len(findings) + 1:02d}",
                "error_flag": error_flag,
                "severity": severity,
                "output_locations": output_locations,
                "evidence_excerpt_ids": evidence_ids,
                "issue": issue,
                "requested_change": requested_change,
            }
        )
        if input("Add another finding? [y/N]: ").strip().lower() not in {"y", "yes"}:
            break
    return findings


def validate_record(record: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"- {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise SystemExit(f"Record failed {schema_path.name}:\n{details}")


def run_reviewer_safe_preflight() -> None:
    validator_path = DIRECTION_ROOT / "scripts" / "validate_artifacts.py"
    result = subprocess.run(
        [sys.executable, str(validator_path), "--reviewer-safe"],
        cwd=DIRECTION_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(
            "Reviewer-safe preflight failed; no item was displayed. "
            + (detail or "The validator returned a nonzero status.")
        )
    try:
        status = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SystemExit(
            "Reviewer-safe preflight returned an unreadable status; no item was displayed."
        ) from exc
    if status.get("status") != "valid" or status.get("contains_real_source_text") is not False:
        raise SystemExit(
            "Reviewer-safe preflight did not affirm a valid synthetic-only queue; "
            "no item was displayed."
        )


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


def commit_response_pair(
    rating_path: Path,
    rating: dict[str, Any],
    feedback_path: Path,
    feedback: dict[str, Any],
) -> None:
    rating_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    if rating_path.exists() or feedback_path.exists():
        raise SystemExit("A response appeared during collection; refusing to overwrite it.")

    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    pending_rating = rating_path.parent / f".{rating_path.name}.{token}.pending"
    pending_feedback = feedback_path.parent / f".{feedback_path.name}.{token}.pending"
    rating_created = False
    feedback_created = False
    try:
        write_exclusive(
            pending_rating,
            (json.dumps(rating, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        write_exclusive(
            pending_feedback,
            (json.dumps(feedback, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        os.link(pending_rating, rating_path)
        rating_created = True
        os.link(pending_feedback, feedback_path)
        feedback_created = True
    except BaseException:
        if feedback_created:
            feedback_path.unlink(missing_ok=True)
        if rating_created:
            rating_path.unlink(missing_ok=True)
        raise
    finally:
        pending_rating.unlink(missing_ok=True)
        pending_feedback.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect the next blinded synthetic Direction H review."
    )
    parser.add_argument("--task-id", help="Optional explicit task, e.g. DHQ-001")
    args = parser.parse_args()

    run_reviewer_safe_preflight()
    item, item_path = choose_task(args.task_id)
    if item["data_classification"] != "synthetic_cc0":
        raise SystemExit("Refusing to collect: item is not classified synthetic_cc0.")
    if "gpt-" in item_path.read_text(encoding="utf-8"):
        raise SystemExit("Refusing to collect: public item leaks a model identifier.")

    print(
        f"Starting {item['task_id']}. Review time begins when the complete item is displayed.\n"
        "Do not open coordinator-only files, blind maps, judge results, or other responses."
    )
    render_item(item)
    started = time.monotonic()

    scores: dict[str, int | None] = {}
    cannot_judge: list[str] = []
    print(
        "\nQUALITY RATINGS\n"
        "1=not adequate, 2=major problems, 3=partly adequate and requiring material revision, "
        "4=mostly adequate with only minor issues, 5=fully adequate\n"
        "Use cj only when the supplied excerpts, local context, or source coverage are insufficient "
        "for that dimension."
    )
    for metric, label in METRICS:
        value = prompt_scale(label)
        scores[metric] = value
        if value is None:
            cannot_judge.append(metric)
    confidence = prompt_scale(
        "Confidence in this judgment (1=very uncertain, 5=very certain)",
        allow_cannot_judge=False,
    )
    disposition = prompt_choice("Disposition:", DISPOSITIONS)
    serious_flags = prompt_many("Serious-error flags:", ERROR_FLAGS)
    requested_expertise = prompt_choice("Requested expertise:", EXPERTISE)
    rationale = prompt_nonempty("Concise evidence-linked rating rationale: ")

    # The canonical paper-metric timer stops when the rating is complete.  The
    # linked revision-feedback prompts below are a separate intervention and
    # must not inflate review_seconds or shift rated_at_utc.
    rating_completed = time.monotonic()
    rated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    review_seconds = round(rating_completed - started, 3)

    if disposition == "accept":
        feedback_status = "no_change"
    elif disposition == "revise":
        feedback_status = "actionable_revision"
    elif disposition == "reject":
        feedback_status = "reject_or_regenerate"
    else:
        feedback_status = "human_escalation"

    print("\nREVISION FEEDBACK SIDECAR")
    feedback_summary = prompt_nonempty(
        "Identity-free feedback summary (for no change, explain what should be preserved): "
    )
    if feedback_status == "no_change":
        if serious_flags:
            raise SystemExit(
                "An accept/no-change record cannot also carry a serious-error flag. "
                "Restart the item and choose a compatible disposition."
            )
        findings = []
    else:
        findings = collect_findings(
            required=feedback_status in {"actionable_revision", "reject_or_regenerate"}
        )
    preserve = prompt_list("Accurate material the revision should preserve:")
    uncertainties = prompt_list("Uncertainties the revision model should not overresolve:")

    feedback_created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rating = {
        "annotation_version": "qc-paper-metrics-v1",
        "rater_id": RATER_ID,
        "evaluator_group": "researcher",
        "packet_id": item["packet_id"],
        "corpus_id": item["corpus_id"],
        "evaluation_role": item["evaluation_role"],
        "output_id": item["output_id"],
        "rated_at_utc": rated_at,
        "evidential_credibility": scores["evidential_credibility"],
        "voice_boundary_preservation": scores["voice_boundary_preservation"],
        "scope_calibration": scores["scope_calibration"],
        "cannot_judge": cannot_judge,
        "confidence": confidence,
        "disposition": disposition,
        "serious_error_flags": serious_flags,
        "review_seconds": review_seconds,
        "requested_expertise": requested_expertise,
        "rationale": rationale,
    }
    feedback = {
        "feedback_version": "direction-h-feedback-v1",
        "feedback_id": f"DHF-{item['task_id']}-{RATER_ID}",
        "pilot_item_id": item["task_id"],
        "rating_key": {
            "annotation_version": rating["annotation_version"],
            "rater_id": rating["rater_id"],
            "packet_id": rating["packet_id"],
            "output_id": rating["output_id"],
            "rated_at_utc": rating["rated_at_utc"],
            "rating_record_sha256": sha256_canonical(rating),
        },
        "feedback_status": feedback_status,
        "model_feedback": {
            "feedback_summary": feedback_summary,
            "findings": findings,
            "preserve": preserve,
            "uncertainties": uncertainties,
        },
        "created_at_utc": feedback_created_at,
    }

    validate_record(rating, RATING_SCHEMA_PATH)
    validate_record(feedback, FEEDBACK_SCHEMA_PATH)
    validate_findings(item, findings)
    serious_finding_flags = {
        row["error_flag"] for row in findings if row["severity"] == "serious"
    }
    if set(serious_flags) != serious_finding_flags:
        raise SystemExit(
            "Core serious-error flags must exactly match feedback findings marked serious."
        )

    print("\nREVIEW SUMMARY (not yet saved)")
    print(json.dumps({"rating": rating, "feedback": feedback}, ensure_ascii=False, indent=2))
    if input("Save these as locked first-pass records? Type SAVE: ").strip() != "SAVE":
        raise SystemExit("Nothing was written.")

    rating_path = PILOT_ROOT / "responses" / "ratings" / f"{item['task_id']}.json"
    feedback_path = PILOT_ROOT / "responses" / "feedback" / f"{item['task_id']}.json"
    commit_response_pair(rating_path, rating, feedback_path, feedback)
    print(f"Saved {rating_path.relative_to(DIRECTION_ROOT)}")
    print(f"Saved {feedback_path.relative_to(DIRECTION_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Nothing was written.", file=sys.stderr)
        raise SystemExit(130)
