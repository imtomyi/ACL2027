#!/usr/bin/env python3
"""Prepare restricted KODIS or CANDOR transcript records.

This pipeline deliberately excludes demographics, surveys, media, raw source IDs,
and precise timestamps. Automatic masking is only a first pass. Every natural
language excerpt remains ineligible until a documented human privacy review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


PIPELINE_VERSION = "1.0"
DATASET_ROOT = Path(__file__).resolve().parents[1]

SPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){7,15}(?!\d)")
IPV4_RE = re.compile(
    r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)"
)
DATE_RE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])(?!\d)"
    r"|(?<!\d)(?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.](?:19|20)?\d{2}(?!\d)"
)

FORBIDDEN_OUTPUT_KEYS = {
    "age",
    "country",
    "culture_cluster",
    "demographics",
    "education",
    "employment",
    "gender",
    "ip_address",
    "location",
    "politics",
    "race",
    "sex",
    "survey",
    "survey_responses",
    "timestamp",
    "worker_id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build restricted, pseudonymized dialogue records for KODIS or CANDOR."
    )
    parser.add_argument("--corpus", choices=("kodis", "candor"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--secret-file",
        type=Path,
        help="File containing a stable project secret. Never commit this file.",
    )
    parser.add_argument(
        "--redaction-list",
        type=Path,
        help="Optional UTF-8 file with one project-approved masking term per line.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use the public synthetic-demo secret. Never use this flag on real data.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing generated files in the output directory.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def file_digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_secret(args: argparse.Namespace) -> bytes:
    if args.demo:
        return b"WarrantRoute synthetic fixture secret only"
    if args.secret_file:
        secret = args.secret_file.read_bytes().strip()
    else:
        secret = os.environ.get("WARRANTROUTE_PSEUDONYM_KEY", "").encode("utf-8")
    if len(secret) < 16:
        raise ValueError(
            "Real-data processing requires a stable secret of at least 16 bytes via "
            "--secret-file or WARRANTROUTE_PSEUDONYM_KEY."
        )
    return secret


def stable_hmac(secret: bytes, namespace: str, value: str) -> str:
    message = f"{namespace}\x00{value}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def pseudonym(secret: bytes, corpus: str, kind: str, value: str) -> str:
    return f"{corpus}_{kind}_{stable_hmac(secret, f'{corpus}:{kind}', value)[:16]}"


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).strip())


def get_path(row: dict[str, Any], dotted_path: str | None) -> Any:
    if dotted_path is None:
        return None
    value: Any = row
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def required_value(row: dict[str, Any], path: str | None, label: str, row_number: int) -> Any:
    value = get_path(row, path)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Input row {row_number} is missing required field {label!r} at {path!r}")
    return value


def load_rows(path: Path, input_format: str) -> list[dict[str, Any]]:
    if input_format == "jsonl":
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL line {line_number} is not an object")
                rows.append(value)
        return rows
    if input_format == "csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError(f"Unsupported input_format {input_format!r}; use jsonl or csv")


def load_redaction_terms(path: Path | None) -> list[str]:
    if path is None:
        return []
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return sorted(set(terms), key=lambda value: (-len(value), value.casefold()))


def privacy_mask(text: str, redaction_terms: list[str]) -> tuple[str, list[str]]:
    """Mask direct identifier patterns without claiming anonymization."""
    substitutions = (
        (URL_RE, "[URL]", "url"),
        (EMAIL_RE, "[EMAIL]", "email"),
        (IPV4_RE, "[IP_ADDRESS]", "ip_address"),
        (HANDLE_RE, "[HANDLE]", "handle"),
        (PHONE_RE, "[PHONE]", "phone_like_number"),
        (DATE_RE, "[DATE]", "exact_date"),
    )
    masked = normalize_text(text)
    flags: list[str] = []
    for pattern, replacement, label in substitutions:
        masked, count = pattern.subn(replacement, masked)
        if count:
            flags.append(label)
    for term in redaction_terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        masked, count = pattern.subn("[REDACTED_TERM]", masked)
        if count:
            flags.append("approved_redaction_term")
    return masked, sorted(set(flags))


def natural_turn_key(value: Any, source_row: int) -> tuple[int, float | str, int]:
    if isinstance(value, (int, float)):
        return (0, float(value), source_row)
    if value is not None:
        text = str(value).strip()
        try:
            return (0, float(text), source_row)
        except ValueError:
            return (1, text.casefold(), source_row)
    return (2, "", source_row)


def iter_forbidden_keys(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key.casefold() in FORBIDDEN_OUTPUT_KEYS or key.casefold().startswith(("raw_", "original_")):
                yield path
            yield from iter_forbidden_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_forbidden_keys(child, f"{prefix}[{index}]")


def prepare_records(
    rows: list[dict[str, Any]],
    adapter: dict[str, Any],
    secret: bytes,
    redaction_terms: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corpus = adapter["corpus"]
    fields = adapter["fields"]
    speaker_scope = adapter.get("speaker_scope", "global")
    if speaker_scope not in {"global", "source"}:
        raise ValueError("speaker_scope must be 'global' or 'source'")

    interaction_field = fields.get("interaction_type")
    interaction_allow = adapter.get("filters", {}).get("interaction_type_allow")
    if corpus == "kodis" and (not interaction_field or not interaction_allow):
        raise ValueError("KODIS must define and filter an interaction_type field")

    internal: list[dict[str, Any]] = []
    excluded_by_filter = Counter()
    for source_row, row in enumerate(rows, start=1):
        if interaction_allow:
            interaction_type = get_path(row, interaction_field)
            if interaction_type is None:
                raise ValueError(
                    f"Input row {source_row} has no interaction type; refusing to risk human-AI inclusion"
                )
            if str(interaction_type) not in {str(value) for value in interaction_allow}:
                excluded_by_filter[str(interaction_type)] += 1
                continue

        source_raw = str(required_value(row, fields["source_id"], "source_id", source_row))
        record_raw = str(required_value(row, fields["record_id"], "record_id", source_row))
        speaker_raw = str(required_value(row, fields["speaker_id"], "speaker_id", source_row))
        text_raw = str(required_value(row, fields["text"], "text", source_row))
        turn_index = get_path(row, fields.get("turn_index"))
        if turn_index is None:
            raise ValueError(f"Input row {source_row} has no turn index; dialogue order is required")
        reply_raw = get_path(row, fields.get("reply_to"))
        speaker_role = get_path(row, fields.get("speaker_role"))

        source_id = pseudonym(secret, corpus, "source", source_raw)
        speaker_key = speaker_raw if speaker_scope == "global" else f"{source_raw}\x00{speaker_raw}"
        speaker_id = pseudonym(secret, corpus, "speaker", speaker_key)
        record_id = pseudonym(secret, corpus, "record", f"{source_raw}\x00{record_raw}")
        masked_text, mask_flags = privacy_mask(text_raw, redaction_terms)
        if not masked_text:
            raise ValueError(f"Input row {source_row} became empty after normalization")

        strata = {}
        for output_name, source_path in adapter.get("sampling_strata", {}).items():
            value = get_path(row, source_path)
            if value is not None and str(value).strip():
                strata[output_name] = value
        if speaker_role is not None and "speaker_role" not in strata:
            strata["speaker_role"] = speaker_role

        internal.append(
            {
                "source_row": source_row,
                "source_raw": source_raw,
                "record_raw": record_raw,
                "reply_raw": None if reply_raw is None else str(reply_raw),
                "turn_index": turn_index,
                "source_id": source_id,
                "speaker_id": speaker_id,
                "record_id": record_id,
                "text": masked_text,
                "text_hmac": stable_hmac(secret, f"{corpus}:text", normalize_text(text_raw)),
                "mask_flags": mask_flags,
                "sampling_strata": strata,
            }
        )

    record_lookup = {
        (item["source_raw"], item["record_raw"]): item["record_id"] for item in internal
    }
    if len(record_lookup) != len(internal):
        raise ValueError("Duplicate source and record identifiers in input")

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in internal:
        by_source[item["source_id"]].append(item)

    records: list[dict[str, Any]] = []
    mask_counts = Counter()
    text_first_record: dict[str, str] = {}
    duplicate_rows = 0
    unresolved_replies = 0
    context_turns = int(adapter.get("context_turns", 3))
    for source_id in sorted(by_source):
        items = sorted(
            by_source[source_id],
            key=lambda item: natural_turn_key(item["turn_index"], item["source_row"]),
        )
        preceding: deque[str] = deque(maxlen=context_turns)
        for item in items:
            reasons = ["manual_privacy_review_pending"]
            first_record = text_first_record.get(item["text_hmac"])
            if first_record is not None:
                reasons.append("later_exact_duplicate_text")
                duplicate_rows += 1
            else:
                text_first_record[item["text_hmac"]] = item["record_id"]

            reply_to_record_id = None
            if item["reply_raw"] is not None:
                reply_to_record_id = record_lookup.get((item["source_raw"], item["reply_raw"]))
                if reply_to_record_id is None:
                    reasons.append("unresolved_reply_reference")
                    unresolved_replies += 1

            mask_counts.update(item["mask_flags"])
            record = {
                "record_id": item["record_id"],
                "corpus": corpus,
                "split": adapter.get("split", "unassigned_pending_preregistration"),
                "source_id": source_id,
                "speaker_id": item["speaker_id"],
                "text": item["text"],
                "context": {
                    "preceding_record_ids": list(preceding),
                    "moderator_question": None,
                    "reply_to_record_id": reply_to_record_id,
                    "turn_index": item["turn_index"],
                },
                "sampling_strata": item["sampling_strata"],
                "provenance": {
                    "source_text_hmac_sha256": item["text_hmac"],
                    "source_row": item["source_row"],
                    "source_turn_index": item["turn_index"],
                    "source_file_role": adapter["source_file_role"],
                },
                "quality": {
                    "eligible_for_packet_sampling": False,
                    "ineligible_reasons": sorted(set(reasons)),
                    "privacy_masks_applied": item["mask_flags"],
                    "manual_excerpt_review_required": True,
                    "privacy_review_status": "pending",
                },
            }
            forbidden = list(iter_forbidden_keys(record))
            if forbidden:
                raise ValueError(f"Forbidden fields reached output: {forbidden}")
            records.append(record)
            preceding.append(item["record_id"])

    report = {
        "pipeline_version": PIPELINE_VERSION,
        "corpus": corpus,
        "input_rows": len(rows),
        "filtered_rows": sum(excluded_by_filter.values()),
        "filter_counts": dict(sorted(excluded_by_filter.items())),
        "records_written": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "split": adapter.get("split", "unassigned_pending_preregistration"),
        "eligible_for_packet_sampling": 0,
        "privacy_review_pending": len(records),
        "privacy_mask_counts": dict(sorted(mask_counts.items())),
        "later_exact_duplicate_rows": duplicate_rows,
        "unresolved_reply_references": unresolved_replies,
        "data_minimization": {
            "raw_ids_written": False,
            "demographics_written": False,
            "surveys_written": False,
            "media_written": False,
            "precise_timestamps_written": False,
        },
        "warning": (
            "Processed text is pseudonymized and pattern-masked, not anonymous. "
            "Every excerpt requires documented human privacy review."
        ),
    }
    return records, report


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(records: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        for record in records
    )


def atomic_write(path: Path, content: bytes, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if path.exists() and not replace:
        raise FileExistsError(f"Refusing to replace {path}; rerun with --replace after review")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main() -> None:
    args = parse_args()
    adapter = load_json(args.adapter)
    if adapter.get("corpus") != args.corpus:
        raise ValueError("Adapter corpus does not match --corpus")
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    secret = load_secret(args)
    redaction_terms = load_redaction_terms(args.redaction_list)
    rows = load_rows(args.input, adapter["input_format"])
    records, report = prepare_records(rows, adapter, secret, redaction_terms)
    report["input_file"] = args.input.name
    report["input_sha256"] = file_digest(args.input)
    report["adapter_file"] = args.adapter.name
    report["adapter_sha256"] = file_digest(args.adapter)
    report["demo_mode"] = bool(args.demo)

    output = args.output.resolve()
    try:
        output.relative_to(DATASET_ROOT.resolve())
    except ValueError:
        print(
            "Warning: output is outside dataset/. Verify access controls manually.",
            file=sys.stderr,
        )
    atomic_write(output / "records.jsonl", jsonl_bytes(records), args.replace)
    atomic_write(output / "build_report.json", json_bytes(report), args.replace)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
