#!/usr/bin/env python3
"""Validate restricted KODIS or CANDOR preprocessing output without printing text."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from prepare_dialogue_corpora import (
    DATE_RE,
    EMAIL_RE,
    FORBIDDEN_OUTPUT_KEYS,
    HANDLE_RE,
    IPV4_RE,
    PHONE_RE,
    URL_RE,
    iter_forbidden_keys,
)


REQUIRED_TOP_LEVEL = {
    "record_id",
    "corpus",
    "split",
    "source_id",
    "speaker_id",
    "text",
    "context",
    "sampling_strata",
    "provenance",
    "quality",
}
DIRECT_IDENTIFIER_PATTERNS = {
    "url": URL_RE,
    "email": EMAIL_RE,
    "ip_address": IPV4_RE,
    "handle": HANDLE_RE,
    "phone_like_number": PHONE_RE,
    "exact_date": DATE_RE,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate prepared KODIS or CANDOR records.")
    parser.add_argument("--corpus", choices=("kodis", "candor"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            require(isinstance(value, dict), f"Record line {line_number} is not an object")
            records.append(value)
    return records


def walk_strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from walk_strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def validate_record_shape(record: dict[str, Any], corpus: str) -> None:
    require(set(record) == REQUIRED_TOP_LEVEL, "Unexpected or missing top-level record fields")
    require(record["corpus"] == corpus, "Corpus field mismatch")
    require(record["record_id"].startswith(f"{corpus}_record_"), "Record ID is not project-local")
    require(record["source_id"].startswith(f"{corpus}_source_"), "Source ID is not project-local")
    require(
        isinstance(record["speaker_id"], str)
        and record["speaker_id"].startswith(f"{corpus}_speaker_"),
        "Speaker ID is missing or not project-local",
    )
    require(record["text"].strip(), "Empty text")
    require(not list(iter_forbidden_keys(record)), "Forbidden demographic or raw-ID field in output")

    context = record["context"]
    require(isinstance(context.get("preceding_record_ids"), list), "Invalid preceding context")
    require(context.get("moderator_question") is None, "Dialogue output should not contain moderator text")

    provenance = record["provenance"]
    fingerprint = provenance.get("source_text_hmac_sha256", "")
    require(len(fingerprint) == 64, "Missing keyed source-text fingerprint")
    require(provenance.get("source_row", 0) >= 1, "Missing source row")

    quality = record["quality"]
    require(quality.get("eligible_for_packet_sampling") is False, "Unreviewed record became eligible")
    require(quality.get("manual_excerpt_review_required") is True, "Manual review gate is missing")
    require(quality.get("privacy_review_status") == "pending", "Unexpected privacy-review status")
    require(
        "manual_privacy_review_pending" in quality.get("ineligible_reasons", []),
        "Pending privacy review is not recorded as an ineligibility reason",
    )

    for label, pattern in DIRECT_IDENTIFIER_PATTERNS.items():
        require(not pattern.search(record["text"]), f"Unmasked {label} pattern remains")


def validate_context(records: list[dict[str, Any]]) -> None:
    by_id = {record["record_id"]: record for record in records}
    require(len(by_id) == len(records), "Record IDs are not unique")
    seen_by_source: dict[str, set[str]] = defaultdict(set)
    for record in records:
        source_id = record["source_id"]
        for previous_id in record["context"]["preceding_record_ids"]:
            require(previous_id in by_id, "Preceding record reference is missing")
            require(by_id[previous_id]["source_id"] == source_id, "Context crosses source boundaries")
            require(previous_id in seen_by_source[source_id], "Context points forward rather than backward")
        reply_id = record["context"].get("reply_to_record_id")
        if reply_id is not None:
            require(reply_id in by_id, "Reply reference is missing")
            require(by_id[reply_id]["source_id"] == source_id, "Reply crosses source boundaries")
        seen_by_source[source_id].add(record["record_id"])


def main() -> None:
    args = parse_args()
    records_path = args.output / "records.jsonl"
    report_path = args.output / "build_report.json"
    require(records_path.is_file(), f"Missing {records_path}")
    require(report_path.is_file(), f"Missing {report_path}")
    records = read_jsonl(records_path)
    require(records, "No records were produced")
    for record in records:
        validate_record_shape(record, args.corpus)
    validate_context(records)

    with report_path.open(encoding="utf-8") as handle:
        report = json.load(handle)
    require(report["corpus"] == args.corpus, "Build-report corpus mismatch")
    require(report["records_written"] == len(records), "Build-report record count mismatch")
    require(report["eligible_for_packet_sampling"] == 0, "Build report bypasses review gate")
    require(report["privacy_review_pending"] == len(records), "Review-pending count mismatch")
    require(mode(records_path) == 0o600 and mode(report_path) == 0o600, "Output files are not mode 0600")
    require(mode(args.output) == 0o700, "Output directory is not mode 0700")

    summary = {
        "status": "ok",
        "corpus": args.corpus,
        "records": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "split_counts": dict(sorted(Counter(record["split"] for record in records).items())),
        "eligible_for_packet_sampling": 0,
        "manual_privacy_review_pending": len(records),
        "forbidden_output_key_names": sorted(FORBIDDEN_OUTPUT_KEYS),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
