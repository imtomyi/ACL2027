#!/usr/bin/env python3
"""Record one frozen theme-revision attempt; this script never calls a model."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from serve_direction_j_browser import (
    J_ITEM_SCHEMA_PATH,
    InstrumentError,
    canonical_bytes,
    editable_pointer,
    load_json,
    parse_utc,
    resolve_pointer,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate,
)
from validate_direction_j_theme_revision import (
    FREEZE_PATH,
    THEME_ROOT,
    theme_store,
    validate_freeze,
    validate_theme,
)


CASE_ROOT = THEME_ROOT / "cases"
RAW_ROOT = THEME_ROOT / "raw_responses"
OUTPUT_ROOT = THEME_ROOT / "revision_outputs"
FAILURES = {"runtime_failure", "timeout"}
CANDIDATE_FIELDS = (
    "display_order",
    "excerpt_id",
    "candidate_attributed_excerpt_id",
    "candidate_attributed_source_id",
    "candidate_attributed_speaker_id",
    "candidate_quote",
    "candidate_role",
    "candidate_warrant",
)


def short_id(prefix: str, *parts: str) -> str:
    return prefix + hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]


def safe_case(case_id: str) -> tuple[Path, dict[str, Any]]:
    if not re.fullmatch(r"DHJRC_[a-f0-9]{20}", case_id):
        raise InstrumentError("case ID is malformed")
    path = CASE_ROOT / "records" / f"{case_id}.json"
    if path.is_symlink() or not path.is_file():
        raise InstrumentError("frozen revision case is missing or unsafe")
    case = load_json(path, "frozen theme revision case")
    validate_theme(case, "revision_case.schema.json", "frozen theme revision case", theme_store())
    if case["revision_case_id"] != case_id:
        raise InstrumentError("case filename/internal ID mismatch")
    if case["freeze_sha256"] != sha256_file(FREEZE_PATH):
        raise InstrumentError("case freeze hash drifted")
    if case["model_input_sha256"] != sha256_bytes(canonical_bytes(case["model_input"])):
        raise InstrumentError("case model-input hash drifted")
    input_path = CASE_ROOT / "model_inputs" / f"{case_id}.json"
    if input_path.is_symlink() or not input_path.is_file():
        raise InstrumentError("separately materialized model input is missing or unsafe")
    if load_json(input_path, "materialized model input") != case["model_input"]:
        raise InstrumentError("materialized model input differs from the frozen case")
    return path, case


def safe_raw(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise InstrumentError("raw response is missing or unsafe")
    resolved = path.resolve()
    try:
        resolved.relative_to(RAW_ROOT.resolve())
    except ValueError as exc:
        raise InstrumentError("raw response must stay under theme_revision/raw_responses") from exc
    if resolved.stat().st_size > 1_000_000:
        raise InstrumentError("raw response exceeds the frozen one-megabyte cap")
    return resolved


def recompute_coverage(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item["evidence"]
    presented = Counter(row["source_id"] for row in evidence)
    cited_rows = [row for row in evidence if row["candidate_role"] != "context_only"]
    cited = Counter(row["candidate_attributed_source_id"] for row in cited_rows)
    original = item["source_coverage"]
    return {
        "presented_excerpt_count": len(evidence),
        "presented_source_count": len(presented),
        "candidate_cited_excerpt_count": len(cited_rows),
        "candidate_cited_source_count": len(cited),
        "sampling_frame_excerpt_count": original["sampling_frame_excerpt_count"],
        "sampling_frame_source_count": original["sampling_frame_source_count"],
        "source_distribution": [
            {
                "source_id": source_id,
                "presented_excerpt_count": presented[source_id],
                "candidate_cited_excerpt_count": cited[source_id],
            }
            for source_id in dict.fromkeys(row["source_id"] for row in evidence)
        ],
        "coverage_note": original["coverage_note"],
    }


def all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_strings(child)


def reconstruct(
    original: dict[str, Any], payload: dict[str, Any], store: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    interpretation = payload["revised_proposed_interpretation"]
    assertions = payload["revised_candidate_assertions"]
    if interpretation["theme_id"] != original["proposed_interpretation"]["theme_id"]:
        raise InstrumentError("revised theme ID differs from the immutable item")
    if len(assertions) != len(original["evidence"]):
        raise InstrumentError("revised assertion rows do not exactly cover displayed evidence")
    seen: set[str] = set()
    quote_mismatches: list[str] = []
    attribution_mismatches: list[str] = []
    reconstructed = copy.deepcopy(original)
    reconstructed["proposed_interpretation"] = interpretation
    for index, (source, assertion) in enumerate(zip(original["evidence"], assertions), start=1):
        if set(assertion) != set(CANDIDATE_FIELDS):
            raise InstrumentError("revised assertion field set drifted")
        if assertion["display_order"] != index or assertion["excerpt_id"] != source["excerpt_id"]:
            raise InstrumentError("revised assertion identity/order drifted")
        if assertion["excerpt_id"] in seen:
            raise InstrumentError("revised assertions duplicate an excerpt ID")
        seen.add(assertion["excerpt_id"])
        if assertion["candidate_role"] != "context_only":
            if assertion["candidate_attributed_excerpt_id"] != source["excerpt_id"] or assertion[
                "candidate_attributed_source_id"
            ] != source["source_id"]:
                attribution_mismatches.append(source["excerpt_id"])
            speaker = assertion["candidate_attributed_speaker_id"]
            if speaker is not None and speaker != source["speaker_id"]:
                attribution_mismatches.append(source["excerpt_id"])
            quote = assertion["candidate_quote"]
            if not isinstance(quote, str) or quote not in source["text"]:
                quote_mismatches.append(source["excerpt_id"])
        target = reconstructed["evidence"][index - 1]
        for field in CANDIDATE_FIELDS[2:]:
            target[field] = assertion[field]
    reconstructed["source_coverage"] = recompute_coverage(reconstructed)
    validate(reconstructed, J_ITEM_SCHEMA_PATH, "reconstructed Direction J item", store)

    diagnosis = payload["revision_diagnosis"]
    finding_flags = {finding["error_flag"] for finding in diagnosis["findings"]}
    if set(diagnosis["detected_error_flags"]) != finding_flags:
        raise InstrumentError("diagnosis flags do not exactly match diagnostic findings")
    excerpt_ids = {row["excerpt_id"] for row in original["evidence"]}
    for finding in diagnosis["findings"]:
        if not set(finding["evidence_excerpt_ids"]).issubset(excerpt_ids):
            raise InstrumentError("diagnosis cites an unknown displayed excerpt")
        for pointer in finding["item_locations"]:
            if not editable_pointer(pointer):
                raise InstrumentError("diagnosis targets an immutable/noncandidate field")
            resolve_pointer(original, pointer)

    visible_text = "\n".join(
        all_strings(
            {
                "diagnosis": diagnosis,
                "proposed_interpretation": interpretation,
                "candidate_warrants": [
                    row["candidate_warrant"] for row in assertions if row["candidate_warrant"]
                ],
            }
        )
    )
    forbidden = (
        r"\bcharlie\b|\bdeveloper[- ]researcher\b|\bplanted\b|\bmanipulation\b|"
        r"\bcontrolled condition\b|\bnatural condition\b|\bfeedback arm\b|"
        r"\bno[- ]feedback arm\b|\b(?:openai|anthropic|google deepmind|meta ai)\b|"
        r"\b(?:gpt|claude|gemini|llama|qwen)(?:[- .]?\w+)*\b"
    )
    if re.search(forbidden, visible_text, flags=re.IGNORECASE):
        raise InstrumentError("revised output self-discloses arm, author, target, or model identity")
    if quote_mismatches or attribution_mismatches:
        detail = ", ".join(sorted(set(quote_mismatches + attribution_mismatches)))
        raise InstrumentError(f"revised evidence integrity failed at excerpt(s): {detail}")
    integrity = {
        "schema_valid": True,
        "immutable_item_fields_preserved": True,
        "immutable_evidence_layer_preserved": True,
        "assertion_rows_match_original": True,
        "assertion_references_resolve": True,
        "source_coverage_recomputed": True,
        "hard_gate_pass": True,
        "nonexact_candidate_quote_excerpt_ids": [],
        "candidate_attribution_mismatch_excerpt_ids": [],
    }
    return reconstructed, integrity


def failed_integrity() -> dict[str, Any]:
    return {
        "schema_valid": False,
        "immutable_item_fields_preserved": False,
        "immutable_evidence_layer_preserved": False,
        "assertion_rows_match_original": False,
        "assertion_references_resolve": False,
        "source_coverage_recomputed": False,
        "hard_gate_pass": False,
        "nonexact_candidate_quote_excerpt_ids": [],
        "candidate_attribution_mismatch_excerpt_ids": [],
    }


def build_record(args: argparse.Namespace) -> dict[str, Any]:
    freeze = validate_freeze(FREEZE_PATH, "frozen")
    _, case = safe_case(args.case_id)
    for field, actual in (
        ("provider", args.provider),
        ("model_id", args.model_id),
        ("snapshot_id", args.snapshot_id),
    ):
        if freeze["revision_model"][field] != actual:
            raise InstrumentError(f"actual runtime {field} differs from the completed freeze")
    generated = parse_utc(args.generated_at_utc, "model generation time")
    if generated <= parse_utc(case["created_at_utc"], "case creation time"):
        raise InstrumentError("model generation must follow case creation")
    if generated > datetime.now(timezone.utc):
        raise InstrumentError("model generation time is in the future")

    raw_path = safe_raw(args.raw_response) if args.raw_response else None
    raw_hash = sha256_file(raw_path) if raw_path else None
    status: str
    payload: dict[str, Any] | None = None
    reconstructed: dict[str, Any] | None = None
    payload_hash: str | None = None
    reconstructed_hash: str | None = None
    failure: dict[str, str] | None = None
    integrity = failed_integrity()
    store = theme_store()
    if args.failure:
        status = args.failure
        failure = {
            "failure_type": args.failure,
            "message": args.failure_message.strip(),
        }
    else:
        if raw_path is None:
            raise InstrumentError("a raw response is required unless a runtime/timeout failure is declared")
        try:
            parsed = json.loads(raw_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            status = "invalid_json"
            failure = {"failure_type": status, "message": str(exc)[:3000]}
        else:
            try:
                validate_theme(parsed, "model_output.schema.json", "revision model output", store)
            except InstrumentError as exc:
                status = "schema_invalid"
                failure = {"failure_type": status, "message": str(exc)[:3000]}
            else:
                try:
                    candidate, candidate_integrity = reconstruct(
                        case["model_input"]["evaluator_item"], parsed, store
                    )
                except InstrumentError as exc:
                    status = "integrity_invalid"
                    failure = {"failure_type": status, "message": str(exc)[:3000]}
                else:
                    status = "complete"
                    payload = parsed
                    reconstructed = candidate
                    integrity = candidate_integrity
                    payload_hash = sha256_bytes(canonical_bytes(payload))
                    reconstructed_hash = sha256_bytes(canonical_bytes(reconstructed))
    if args.failure and not args.failure_message.strip():
        raise InstrumentError("declared runtime/timeout failure requires a message")

    revision_id = short_id("DHJRV_", case["revision_case_id"], case["freeze_sha256"])
    record = {
        "revision_output_version": "direction-h-j-theme-revision-output-v1",
        "revision_id": revision_id,
        "blinded_revision_id": short_id("DHJBR_", revision_id, "coordinator-blind"),
        "revision_case_id": case["revision_case_id"],
        "paired_case_group_id": case["paired_case_group_id"],
        "repeat_index": case["repeat_index"],
        "item_id": case["item_id"],
        "freeze_id": case["freeze_id"],
        "feedback_arm": case["feedback_arm"],
        "completion_status": status,
        "attempt_count": 1,
        "generated_at_utc": args.generated_at_utc,
        "raw_response_sha256": raw_hash,
        "model_payload_sha256": payload_hash,
        "reconstructed_item_sha256": reconstructed_hash,
        "model_payload": payload,
        "reconstructed_evaluator_item": reconstructed,
        "failure_record": failure,
        "integrity_validation": integrity,
        "execution_metadata": {
            "provider": args.provider,
            "model_id": args.model_id,
            "snapshot_id": args.snapshot_id,
            "latency_ms": args.latency_ms,
            "input_tokens": args.input_tokens,
            "output_tokens": args.output_tokens,
        },
    }
    validate_theme(
        record,
        "revision_output.schema.json",
        "theme revision output envelope",
        store,
    )
    return record


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record one retained frozen-model attempt; this command never calls a model."
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--raw-response", type=Path)
    parser.add_argument("--failure", choices=sorted(FAILURES))
    parser.add_argument("--failure-message", default="")
    parser.add_argument("--latency-ms", type=int)
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    args = parser.parse_args()
    try:
        for label in ("latency_ms", "input_tokens", "output_tokens"):
            value = getattr(args, label)
            if value is not None and value < 0:
                raise InstrumentError(f"{label} cannot be negative")
        record = build_record(args)
        destination = OUTPUT_ROOT / f"{args.case_id}.json"
        if destination.exists():
            raise InstrumentError("refusing to overwrite a retained revision attempt")
        write_exclusive(destination, record)
        print(
            json.dumps(
                {
                    "status": record["completion_status"],
                    "case_id": args.case_id,
                    "path": str(destination),
                    "empirical_result_computed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
