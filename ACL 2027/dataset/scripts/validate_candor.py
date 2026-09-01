#!/usr/bin/env python3
"""Validate CANDOR staging without printing transcript text or raw identifiers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from prepare_candor import (
    ADAPTER_KEYS,
    AUTOMATIC_MASKING_LIMITATIONS,
    BUILD_OBSERVED_COUNT_KEYS,
    BUILD_REPORT_KEYS,
    BUILD_WARNING,
    CANDOR_DEMO_INPUT_ROOT,
    CANDOR_DEMO_OUTPUT,
    CANDOR_FIXTURE_ROOT,
    CANDOR_OUTPUT_ROOT,
    CANDOR_RAW_ROOT,
    DATA_MINIMIZATION_KEYS,
    DATE_RE,
    DEMO_ADAPTER_NOTE,
    DEMO_ADAPTER_PATH,
    DEMO_ADAPTER_SHA256,
    DEMO_SOURCE_MANIFEST_PATH,
    DEMO_SOURCE_MANIFEST_SHA256,
    DEMO_SOURCE_WARNING,
    DEMO_SPLIT_MANIFEST_PATH,
    DEMO_SPLIT_MANIFEST_SHA256,
    DEMO_SPLIT_WARNING,
    EMAIL_RE,
    HANDLE_RE,
    INPUT_ROUTE,
    IPV4_RE,
    OBSERVED_SOURCE_COUNT_KEYS,
    PHONE_RE,
    PIPELINE_VERSION,
    PREFERRED_FILENAME,
    REAL_ADAPTER_NAME,
    REAL_ADAPTER_NOTE,
    REAL_SOURCE_MANIFEST_NAME,
    REAL_SOURCE_WARNING,
    REAL_SPLIT_MANIFEST_NAME,
    REAL_SPLIT_WARNING,
    SHA256_RE,
    SOURCE_FILE_KEYS,
    SOURCE_MANIFEST_KEYS,
    SPLIT_MANIFEST_KEYS,
    TRANSCRIPTION_ALGORITHM,
    URL_RE,
    UNASSIGNED_SPLIT,
    DisjointSet,
    atomic_write,
    enforce_control_path,
    file_digest,
    is_within,
    iter_forbidden_keys,
    json_bytes,
    load_json,
    load_json_snapshot,
    require,
    require_clean_output_directory,
    require_private_mode,
    require_unchanged,
)


DATASET_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = DATASET_ROOT / "schemas" / "experiment_record.schema.json"

RECORD_ID_RE = re.compile(r"^candor_record_[a-f0-9]{16}$")
SOURCE_ID_RE = re.compile(r"^candor_source_[a-f0-9]{16}$")
SPEAKER_ID_RE = re.compile(r"^candor_speaker_[a-f0-9]{16}$")
COMPONENT_ID_RE = re.compile(r"^candor_linkage_[a-f0-9]{16}$")

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
CONTEXT_KEYS = {
    "preceding_record_ids",
    "moderator_question",
    "reply_to_record_id",
    "turn_index",
}
PROVENANCE_KEYS = {
    "source_text_hmac_sha256",
    "source_row",
    "source_turn_index",
    "source_file_role",
    "linkage_group_id",
}
QUALITY_KEYS = {
    "eligible_for_packet_sampling",
    "ineligible_reasons",
    "privacy_masks_applied",
    "manual_excerpt_review_required",
    "privacy_review_status",
}
GROUP_KEYS = {
    "component_id",
    "source_ids",
    "speaker_ids",
    "split",
    "source_count",
    "speaker_count",
    "record_count",
}
ALLOWED_MASKS = {
    "url",
    "email",
    "ip_address",
    "handle",
    "exact_date",
    "phone_like_number",
}
DIRECT_IDENTIFIER_PATTERNS = {
    "url": URL_RE,
    "email": EMAIL_RE,
    "ip_address": IPV4_RE,
    "handle": HANDLE_RE,
    "exact_date": DATE_RE,
    "phone_like_number": PHONE_RE,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate restricted CANDOR Cliffhanger staging output."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--replace-report", action="store_true")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            require(isinstance(value, dict), f"JSONL line {line_number} is not an object")
            values.append(value)
    return values


def read_jsonl_snapshot(path: Path) -> tuple[list[dict[str, Any]], str]:
    content = path.read_bytes()
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), f"JSONL line {line_number} is not an object")
        values.append(value)
    return values, hashlib.sha256(content).hexdigest()


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def validate_schema(records: list[dict[str, Any]]) -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    for index, record in enumerate(records, start=1):
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        if errors:
            error = errors[0]
            location = ".".join(str(part) for part in error.path) or "<record>"
            raise ValueError(
                f"Record {index} violates the shared schema at {location} ({error.validator})"
            )


def validate_record_shape(record: dict[str, Any]) -> None:
    require(set(record) == REQUIRED_TOP_LEVEL, "Unexpected or missing top-level record fields")
    require(record.get("corpus") == "candor", "Record corpus mismatch")
    require(bool(RECORD_ID_RE.fullmatch(str(record.get("record_id", "")))), "Invalid record ID")
    require(bool(SOURCE_ID_RE.fullmatch(str(record.get("source_id", "")))), "Invalid source ID")
    require(bool(SPEAKER_ID_RE.fullmatch(str(record.get("speaker_id", "")))), "Invalid speaker ID")
    require(isinstance(record.get("split"), str) and bool(record["split"]), "Invalid split")
    require(isinstance(record.get("text"), str) and bool(record["text"].strip()), "Empty text")
    require(not list(iter_forbidden_keys(record)), "Forbidden media/metadata/raw-ID key in output")
    require(record.get("sampling_strata") == {}, "CANDOR sampling_strata must remain empty")

    context = record.get("context")
    require(isinstance(context, dict) and set(context) == CONTEXT_KEYS, "Invalid context shape")
    require(context.get("moderator_question") is None, "Unexpected moderator text")
    require(isinstance(context.get("preceding_record_ids"), list), "Invalid prior context")
    turn_index = context.get("turn_index")
    require(
        isinstance(turn_index, int) and not isinstance(turn_index, bool) and turn_index >= 1,
        "Turn index must be a positive derived ordinal",
    )

    provenance = record.get("provenance")
    require(
        isinstance(provenance, dict) and set(provenance) == PROVENANCE_KEYS,
        "Invalid provenance shape",
    )
    require(
        bool(SHA256_RE.fullmatch(str(provenance.get("source_text_hmac_sha256", "")))),
        "Invalid keyed text fingerprint",
    )
    require(
        provenance.get("source_row") == turn_index
        and provenance.get("source_turn_index") == turn_index,
        "Source row/turn lineage must equal the derived ordinal",
    )
    require(
        provenance.get("source_file_role") == "betterup_cliffhanger_transcript_turn",
        "Unexpected source file role",
    )
    require(
        bool(COMPONENT_ID_RE.fullmatch(str(provenance.get("linkage_group_id", "")))),
        "Invalid linkage group ID",
    )

    quality = record.get("quality")
    require(isinstance(quality, dict) and set(quality) == QUALITY_KEYS, "Invalid quality shape")
    require(quality.get("eligible_for_packet_sampling") is False, "Pending record became eligible")
    require(
        quality.get("ineligible_reasons") == ["manual_privacy_review_pending"],
        "Privacy-review ineligibility gate changed",
    )
    require(quality.get("manual_excerpt_review_required") is True, "Manual review gate missing")
    require(quality.get("privacy_review_status") == "pending", "Unexpected review status")
    masks = quality.get("privacy_masks_applied")
    require(
        isinstance(masks, list)
        and masks == sorted(set(masks))
        and set(masks).issubset(ALLOWED_MASKS),
        "Invalid privacy mask audit trail",
    )
    for label, pattern in DIRECT_IDENTIFIER_PATTERNS.items():
        require(not pattern.search(record["text"]), f"Residual {label} pattern in staged text")


def validate_turn_lineage(records: list[dict[str, Any]], context_turns: int) -> None:
    by_id = {record["record_id"]: record for record in records}
    require(len(by_id) == len(records), "Record IDs are not unique")
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_source[record["source_id"]].append(record)

    expected_output_order: list[str] = []
    for source_id in sorted(by_source):
        source_records = by_source[source_id]
        turns = [record["context"]["turn_index"] for record in source_records]
        require(turns == list(range(1, len(source_records) + 1)), "Turn ordinals are not exact/unique")
        expected_output_order.extend(record["record_id"] for record in source_records)
        for index, record in enumerate(source_records):
            expected_preceding = [
                previous["record_id"]
                for previous in source_records[max(0, index - context_turns) : index]
            ]
            require(
                record["context"]["preceding_record_ids"] == expected_preceding,
                "Preceding context window is incomplete or out of order",
            )
            reply_id = record["context"]["reply_to_record_id"]
            if reply_id is not None:
                require(reply_id in by_id, "Reply target is missing")
                target = by_id[reply_id]
                require(target["source_id"] == source_id, "Reply crosses conversations")
                require(
                    target["context"]["turn_index"] < record["context"]["turn_index"],
                    "Reply points forward",
                )
    require(
        [record["record_id"] for record in records] == expected_output_order,
        "Record output order does not preserve deterministic conversation/turn lineage",
    )


def graph_components(records: list[dict[str, Any]]) -> list[dict[str, set[str]]]:
    graph = DisjointSet()
    for record in records:
        source_node = f"source:{record['source_id']}"
        speaker_node = f"speaker:{record['speaker_id']}"
        graph.add(source_node)
        graph.add(speaker_node)
        graph.union(source_node, speaker_node)
    members: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"source_ids": set(), "speaker_ids": set()}
    )
    for node in graph.parent:
        root = graph.find(node)
        kind, value = node.split(":", 1)
        members[root][f"{kind}_ids"].add(value)
    return list(members.values())


def validate_linkage_groups(
    records: list[dict[str, Any]], groups: list[dict[str, Any]]
) -> None:
    require(groups, "No linkage groups were written")
    component_ids: set[str] = set()
    source_to_group: dict[str, str] = {}
    speaker_to_group: dict[str, str] = {}
    group_member_sets: set[tuple[frozenset[str], frozenset[str]]] = set()
    record_counts = Counter(record["provenance"]["linkage_group_id"] for record in records)
    for group in groups:
        require(set(group) == GROUP_KEYS, "Unexpected linkage-group shape")
        component_id = group.get("component_id")
        require(bool(COMPONENT_ID_RE.fullmatch(str(component_id))), "Invalid component ID")
        require(component_id not in component_ids, "Duplicate component ID")
        component_ids.add(component_id)
        sources = group.get("source_ids")
        speakers = group.get("speaker_ids")
        require(
            isinstance(sources, list) and sources == sorted(set(sources)) and sources,
            "Invalid component sources",
        )
        require(
            isinstance(speakers, list) and speakers == sorted(set(speakers)) and speakers,
            "Invalid component speakers",
        )
        require(all(SOURCE_ID_RE.fullmatch(value) for value in sources), "Invalid group source ID")
        require(all(SPEAKER_ID_RE.fullmatch(value) for value in speakers), "Invalid group speaker ID")
        require(group.get("source_count") == len(sources), "Group source count mismatch")
        require(group.get("speaker_count") == len(speakers), "Group speaker count mismatch")
        require(group.get("record_count") == record_counts[component_id], "Group record count mismatch")
        require(isinstance(group.get("split"), str) and bool(group["split"]), "Invalid group split")
        for source_id in sources:
            require(source_id not in source_to_group, "Conversation appears in multiple components")
            source_to_group[source_id] = component_id
        for speaker_id in speakers:
            require(speaker_id not in speaker_to_group, "Speaker appears in multiple components")
            speaker_to_group[speaker_id] = component_id
        group_member_sets.add((frozenset(sources), frozenset(speakers)))

    recomputed = {
        (frozenset(component["source_ids"]), frozenset(component["speaker_ids"]))
        for component in graph_components(records)
    }
    require(group_member_sets == recomputed, "Stored linkage groups differ from graph components")
    group_by_id = {group["component_id"]: group for group in groups}
    source_splits: dict[str, set[str]] = defaultdict(set)
    speaker_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        source_id = record["source_id"]
        speaker_id = record["speaker_id"]
        component_id = record["provenance"]["linkage_group_id"]
        require(source_to_group.get(source_id) == component_id, "Record/source component mismatch")
        require(speaker_to_group.get(speaker_id) == component_id, "Record/speaker component mismatch")
        require(group_by_id[component_id]["split"] == record["split"], "Component spans splits")
        source_splits[source_id].add(record["split"])
        speaker_splits[speaker_id].add(record["split"])
    require(all(len(values) == 1 for values in source_splits.values()), "Conversation crosses splits")
    require(all(len(values) == 1 for values in speaker_splits.values()), "Linked speaker crosses splits")


def validate_report(
    report: dict[str, Any],
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    adapter: dict[str, Any],
    source_manifest: dict[str, Any],
    split_manifest: dict[str, Any] | None,
    adapter_digest: str,
    source_manifest_digest: str,
    split_manifest_digest: str | None,
    pipeline_digest: str,
    args: argparse.Namespace,
) -> None:
    require(set(report) == BUILD_REPORT_KEYS, "Unexpected build-report fields")
    report_without_mask_labels = {
        key: value for key, value in report.items() if key != "privacy_mask_counts"
    }
    require(
        not list(iter_forbidden_keys(report_without_mask_labels)),
        "Forbidden raw/metadata key in build report",
    )
    require(report.get("pipeline_version") == PIPELINE_VERSION, "Pipeline-version mismatch")
    require(report.get("pipeline_file") == "prepare_candor.py", "Pipeline filename mismatch")
    require(report.get("pipeline_sha256") == pipeline_digest, "Pipeline hash mismatch")
    context_turns = adapter.get("context_turns")
    require(
        isinstance(context_turns, int)
        and not isinstance(context_turns, bool)
        and 0 <= context_turns <= 20,
        "Adapter context_turns is invalid",
    )
    require(report.get("context_turns") == context_turns, "Context-window report mismatch")
    require(report.get("corpus") == "candor", "Build-report corpus mismatch")
    require(
        report.get("data_status") == "restricted_pseudonymized_pending_manual_privacy_review",
        "Build-report privacy status mismatch",
    )
    require(report.get("input_route") == INPUT_ROUTE, "Build-report route mismatch")
    require(
        report.get("transcription_algorithm") == TRANSCRIPTION_ALGORITHM,
        "Build report does not assert Cliffhanger",
    )
    require(report.get("demo_mode") is args.demo, "Demo-mode mismatch")
    require(report.get("adapter_file") == args.adapter.name, "Adapter filename mismatch")
    require(report.get("adapter_sha256") == adapter_digest, "Adapter hash mismatch")
    require(
        report.get("source_manifest_file") == args.source_manifest.name,
        "Source-manifest filename mismatch",
    )
    require(
        report.get("source_manifest_sha256") == source_manifest_digest,
        "Source-manifest hash mismatch",
    )
    if args.split_manifest is None:
        require(report.get("split_manifest_file") is None, "Unexpected split manifest")
        require(report.get("split_manifest_sha256") is None, "Unexpected split-manifest hash")
    else:
        require(
            report.get("split_manifest_file") == args.split_manifest.name,
            "Split-manifest filename mismatch",
        )
        require(
            report.get("split_manifest_sha256") == split_manifest_digest,
            "Split-manifest hash mismatch",
        )
    split_applied = split_manifest is not None
    require(report.get("split_manifest_applied") is split_applied, "Split-presence mismatch")
    require(
        report.get("preregistered_split_assignment_present") is (split_applied and not args.demo),
        "Preregistered split indicator mismatch",
    )
    require(
        report.get("synthetic_split_fixture_applied") is (split_applied and args.demo),
        "Synthetic split indicator mismatch",
    )

    record_count = len(records)
    source_count = len({record["source_id"] for record in records})
    speaker_count = len({record["speaker_id"] for record in records})
    split_counts = dict(sorted(Counter(record["split"] for record in records).items()))
    require(report.get("records_written") == record_count, "Record count mismatch")
    require(report.get("sources") == source_count, "Source count mismatch")
    require(report.get("speakers") == speaker_count, "Speaker count mismatch")
    require(report.get("linkage_components") == len(groups), "Component count mismatch")
    require(report.get("split_counts") == split_counts, "Split counts mismatch")
    require(report.get("eligible_for_packet_sampling") == 0, "Eligibility gate bypassed")
    require(report.get("privacy_review_pending") == record_count, "Review count mismatch")
    require(
        report.get("manual_privacy_review_required_for_all_records") is True,
        "Manual-review report gate missing",
    )
    require(report.get("unresolved_reply_references") == 0, "Unresolved replies reported")
    observed_masks = Counter(
        mask
        for record in records
        for mask in record["quality"]["privacy_masks_applied"]
    )
    require(
        report.get("privacy_mask_counts") == dict(sorted(observed_masks.items())),
        "Privacy-mask counts do not match records",
    )
    require(
        set(report["privacy_mask_counts"]).issubset(ALLOWED_MASKS)
        and all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in report["privacy_mask_counts"].values()
        ),
        "Invalid privacy-mask aggregate",
    )

    observed = report.get("observed_release_counts")
    source_observed = source_manifest.get("observed_release_counts")
    require(
        isinstance(observed, dict) and set(observed) == BUILD_OBSERVED_COUNT_KEYS,
        "Invalid build observed counts",
    )
    require(
        isinstance(source_observed, dict)
        and set(source_observed) == OBSERVED_SOURCE_COUNT_KEYS,
        "Invalid source observed counts",
    )
    require(
        observed.get("transcript_files") == source_observed.get("transcript_files"),
        "Observed file count mismatch",
    )
    require(
        observed.get("transcript_rows") == source_observed.get("transcript_rows") == record_count,
        "Observed transcript-row count mismatch",
    )
    require(observed.get("conversations") == source_count, "Observed conversation count mismatch")
    require(observed.get("speakers") == speaker_count, "Observed speaker count mismatch")
    require(
        observed.get("conversation_speaker_connected_components") == len(groups),
        "Observed component count mismatch",
    )
    source_files = source_manifest.get("files")
    require(isinstance(source_files, list) and source_files, "Source receipt is empty")
    require(len(source_files) == source_observed.get("transcript_files"), "Receipt file count mismatch")
    for entry in source_files:
        require(isinstance(entry, dict), "Invalid source receipt entry")
        require(set(entry) == SOURCE_FILE_KEYS, "Unexpected source receipt fields")
        require(entry.get("basename") == PREFERRED_FILENAME, "Receipt contains fallback input")
        require(bool(SHA256_RE.fullmatch(str(entry.get("sha256", "")))), "Invalid receipt hash")
        require(
            not {"path", "relative_path", "conversation_id", "speaker_id"}.intersection(entry),
            "Source receipt contains raw paths or identifiers",
        )
    require(
        sum(entry.get("row_count", -1) for entry in source_files)
        == source_observed.get("transcript_rows"),
        "Receipt row count mismatch",
    )

    minimization = report.get("data_minimization")
    require(
        isinstance(minimization, dict) and set(minimization) == DATA_MINIMIZATION_KEYS,
        "Invalid minimization audit",
    )
    require(all(value is False for value in minimization.values()), "Excluded data reached output")
    require(
        report.get("automatic_masking_limitations") == AUTOMATIC_MASKING_LIMITATIONS,
        "Automatic-masking limitations changed",
    )
    require(report.get("warning") == BUILD_WARNING, "Privacy warning changed")
    require(set(adapter) == ADAPTER_KEYS, "Unexpected adapter fields")
    require(adapter.get("adapter_version") == "1.0", "Unsupported adapter version")
    require(adapter.get("sampling_strata") == {}, "Adapter retains metadata strata")
    require(adapter.get("input_route") == INPUT_ROUTE, "Adapter route mismatch")
    require(
        adapter.get("transcription_algorithm") == TRANSCRIPTION_ALGORITHM,
        "Adapter does not assert Cliffhanger",
    )
    require(adapter.get("row_order_is_turn_order") is True, "Adapter row order is unverified")
    require(
        adapter.get("speaker_ids_are_person_stable_across_conversations") is True,
        "Adapter speaker linkage is unverified",
    )
    fields = adapter.get("fields")
    require(
        isinstance(fields, dict)
        and set(fields) == {"speaker_id", "text", "record_id", "reply_to"},
        "Invalid adapter field roles",
    )
    mapped_fields = [value for value in fields.values() if value is not None]
    require(
        all(isinstance(value, str) and value for value in mapped_fields)
        and len(mapped_fields) == len(set(mapped_fields)),
        "Adapter field roles are missing or not distinct",
    )
    verified_headers = adapter.get("verified_input_headers")
    discarded_fields = adapter.get("discarded_input_fields")
    require(
        isinstance(verified_headers, list)
        and verified_headers
        and len(verified_headers) == len(set(verified_headers)),
        "Invalid verified input headers",
    )
    require(
        isinstance(discarded_fields, list)
        and set(discarded_fields) == set(verified_headers) - set(mapped_fields),
        "Adapter discard allowlist mismatch",
    )
    require(set(source_manifest) == SOURCE_MANIFEST_KEYS, "Unexpected source-manifest fields")
    require(
        source_manifest.get("manifest_version") == "1.0",
        "Unsupported source-manifest version",
    )
    require(source_manifest.get("input_route") == INPUT_ROUTE, "Source-manifest route mismatch")
    require(
        source_manifest.get("transcription_algorithm") == TRANSCRIPTION_ALGORITHM,
        "Source manifest does not assert Cliffhanger",
    )
    if args.demo:
        require(adapter.get("verification_status") == "synthetic_fixture_verified", "Invalid demo adapter")
        require(adapter.get("verification_notes") == DEMO_ADAPTER_NOTE, "Demo adapter note changed")
        require(source_manifest.get("package_status") == "synthetic_fixture", "Invalid demo receipt")
        require(source_manifest.get("synthetic_fixture") is True, "Missing demo receipt marker")
        require(
            source_manifest.get("unverified_input_assumptions") == [],
            "Demo receipt contains unresolved assumptions",
        )
        require(source_manifest.get("warning") == DEMO_SOURCE_WARNING, "Demo receipt warning changed")
    else:
        require(
            adapter.get("verification_status") == "verified_against_authorized_package",
            "Real adapter remains unverified",
        )
        require(adapter.get("verification_notes") == REAL_ADAPTER_NOTE, "Real adapter note changed")
        require(
            source_manifest.get("package_status") == "authorized_for_restricted_processing",
            "Source package is not authorized",
        )
        require(
            source_manifest.get("transcript_only_processing_approved") is True,
            "Transcript-only approval is missing",
        )
        require(
            source_manifest.get("terms_review_status") == "approved_for_this_processing",
            "Terms review is incomplete",
        )
        require(
            source_manifest.get("pii_handling_status") == "approved_restricted_controls",
            "PII-handling controls are not approved",
        )
        require(
            isinstance(source_manifest.get("access_approval_reference"), str)
            and bool(source_manifest["access_approval_reference"].strip()),
            "Access approval reference is missing",
        )
        require(
            isinstance(source_manifest.get("acquisition_date"), str)
            and bool(source_manifest["acquisition_date"].strip()),
            "Acquisition date is missing",
        )
        require(
            isinstance(source_manifest.get("package_version"), str)
            and bool(source_manifest["package_version"].strip()),
            "Package version is missing",
        )
        require(
            source_manifest.get("manual_privacy_review_plan_status") == "documented",
            "Manual privacy-review plan is missing",
        )
        require(
            source_manifest.get("redistribution_status") == "not_cleared",
            "Redistribution status is not fail closed",
        )
        require(source_manifest.get("synthetic_fixture") is False, "Real receipt is synthetic")
        require(
            source_manifest.get("unverified_input_assumptions") == [],
            "Real input assumptions remain unresolved",
        )
        require(source_manifest.get("warning") == REAL_SOURCE_WARNING, "Source warning changed")

    group_assignments = {group["component_id"]: group["split"] for group in groups}
    if split_manifest is None:
        require(
            set(group_assignments.values()) == {UNASSIGNED_SPLIT},
            "Components were assigned without a split manifest",
        )
    else:
        require(set(split_manifest) == SPLIT_MANIFEST_KEYS, "Unexpected split-manifest fields")
        require(
            split_manifest.get("manifest_version") == "1.0",
            "Unsupported split-manifest version",
        )
        expected_status = "synthetic_demo" if args.demo else "preregistered"
        require(split_manifest.get("status") == expected_status, "Split-manifest status mismatch")
        require(
            split_manifest.get("assignment_unit")
            == "conversation_speaker_connected_component",
            "Split assignment unit is not a connected component",
        )
        expected_warning = DEMO_SPLIT_WARNING if args.demo else REAL_SPLIT_WARNING
        require(split_manifest.get("warning") == expected_warning, "Split warning changed")
        require(split_manifest.get("assignments") == group_assignments, "Split assignment mismatch")


def validate_permissions(output: Path, bundle_paths: list[Path]) -> None:
    require(mode(output) == 0o700, "CANDOR output directory must be mode 0700")
    for path in bundle_paths:
        require(mode(path) == 0o600, f"CANDOR output file must be mode 0600: {path.name}")


def validation_summary(
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    bundle_digests: dict[str, str],
    split_manifest_applied: bool,
    demo: bool,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "corpus": "candor",
        "data_status": "restricted_pseudonymized_pending_manual_privacy_review",
        "records": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "linkage_components": len(groups),
        "split_counts": dict(sorted(Counter(record["split"] for record in records).items())),
        "eligible_for_packet_sampling": 0,
        "manual_privacy_review_pending": len(records),
        "shared_schema_valid": True,
        "turn_lineage_valid": True,
        "linkage_component_integrity_valid": True,
        "split_manifest_applied": split_manifest_applied,
        "linked_speaker_split_isolation_valid": split_manifest_applied,
        "preregistered_split_assignment_present": split_manifest_applied and not demo,
        "synthetic_split_fixture_applied": split_manifest_applied and demo,
        "forbidden_output_fields_absent": True,
        "precise_timestamp_metadata_fields_absent": True,
        "free_text_privacy_review_pending": True,
        "bundle_sha256": dict(sorted(bundle_digests.items())),
        "warning": "Validated structure is restricted and pseudonymized, not anonymous.",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    validation_report_path = output / "validation_report.json"
    if args.validation_report is not None:
        require(
            args.validation_report.resolve() == validation_report_path,
            "Validation report must use the reserved validation_report.json path",
        )
    if args.demo:
        allowed_canonical = output == CANDOR_DEMO_OUTPUT.resolve()
        allowed_test = is_within(output, CANDOR_FIXTURE_ROOT) and not is_within(
            output, CANDOR_DEMO_INPUT_ROOT
        )
        require(
            allowed_canonical or allowed_test,
            "Demo output must remain in the dedicated CANDOR fixture area",
        )
        enforce_control_path(args.adapter, args.adapter.name, DEMO_ADAPTER_PATH)
        enforce_control_path(
            args.source_manifest, args.source_manifest.name, DEMO_SOURCE_MANIFEST_PATH
        )
        if args.split_manifest is not None:
            enforce_control_path(
                args.split_manifest, args.split_manifest.name, DEMO_SPLIT_MANIFEST_PATH
            )
    else:
        require(is_within(output, CANDOR_OUTPUT_ROOT), "Real output is outside CANDOR restricted root")
        for control_path, expected_name, label in (
            (args.adapter, REAL_ADAPTER_NAME, "CANDOR adapter"),
            (args.source_manifest, REAL_SOURCE_MANIFEST_NAME, "CANDOR source manifest"),
            (args.split_manifest, REAL_SPLIT_MANIFEST_NAME, "CANDOR split manifest"),
        ):
            if control_path is not None:
                enforce_control_path(control_path, expected_name, None)
                require_private_mode(control_path, label)
    require(output.is_dir(), "CANDOR output directory is missing")
    require_clean_output_directory(output)
    records_path = output / "records.jsonl"
    groups_path = output / "linkage_groups.jsonl"
    report_path = output / "build_report.json"
    bundle_paths = [records_path, groups_path, report_path]
    require(all(path.is_file() for path in bundle_paths), "CANDOR output bundle is incomplete")

    existing_validation_report: dict[str, Any] | None = None
    existing_validation_digest: str | None = None
    if validation_report_path.exists():
        require(validation_report_path.is_file(), "Invalid CANDOR validation-report entry")
        if args.validation_report is None:
            existing_validation_report, existing_validation_digest = load_json_snapshot(
                validation_report_path
            )

    records, records_digest = read_jsonl_snapshot(records_path)
    groups, groups_digest = read_jsonl_snapshot(groups_path)
    report, report_digest = load_json_snapshot(report_path)
    adapter, adapter_digest = load_json_snapshot(args.adapter)
    source_manifest, source_manifest_digest = load_json_snapshot(args.source_manifest)
    split_manifest: dict[str, Any] | None = None
    split_manifest_digest: str | None = None
    if args.split_manifest is not None:
        split_manifest, split_manifest_digest = load_json_snapshot(args.split_manifest)
    if args.demo:
        require(adapter_digest == DEMO_ADAPTER_SHA256, "Demo adapter checksum changed")
        require(
            source_manifest_digest == DEMO_SOURCE_MANIFEST_SHA256,
            "Demo source-manifest checksum changed",
        )
        if args.split_manifest is not None:
            require(
                split_manifest_digest == DEMO_SPLIT_MANIFEST_SHA256,
                "Demo split-manifest checksum changed",
            )
    pipeline_path = DATASET_ROOT / "scripts" / "prepare_candor.py"
    pipeline_digest = file_digest(pipeline_path)
    require(records, "No staged CANDOR records")
    validate_schema(records)
    for record in records:
        validate_record_shape(record)
    context_turns = adapter.get("context_turns")
    require(
        isinstance(context_turns, int)
        and not isinstance(context_turns, bool)
        and 0 <= context_turns <= 20,
        "Adapter context_turns is invalid",
    )
    validate_turn_lineage(records, context_turns)
    validate_linkage_groups(records, groups)
    validate_report(
        report,
        records,
        groups,
        adapter,
        source_manifest,
        split_manifest,
        adapter_digest,
        source_manifest_digest,
        split_manifest_digest,
        pipeline_digest,
        args,
    )
    permission_paths = list(bundle_paths)
    if validation_report_path.exists():
        permission_paths.append(validation_report_path)
    validate_permissions(output, permission_paths)
    require_unchanged(records_path, records_digest, "CANDOR records")
    require_unchanged(groups_path, groups_digest, "CANDOR linkage groups")
    require_unchanged(report_path, report_digest, "CANDOR build report")
    require_unchanged(args.adapter, adapter_digest, "CANDOR adapter")
    require_unchanged(
        args.source_manifest, source_manifest_digest, "CANDOR source manifest"
    )
    if args.split_manifest is not None and split_manifest_digest is not None:
        require_unchanged(
            args.split_manifest, split_manifest_digest, "CANDOR split manifest"
        )
    require_unchanged(pipeline_path, pipeline_digest, "CANDOR pipeline")
    bundle_digests = {
        records_path.name: records_digest,
        groups_path.name: groups_digest,
        report_path.name: report_digest,
    }
    summary = validation_summary(
        records,
        groups,
        bundle_digests,
        split_manifest_applied=split_manifest is not None,
        demo=args.demo,
    )
    if existing_validation_report is not None:
        require(
            existing_validation_report == summary,
            "Existing validation report does not match the current CANDOR bundle",
        )
        require(
            existing_validation_digest is not None,
            "Existing validation-report snapshot is missing",
        )
        require_unchanged(
            validation_report_path,
            existing_validation_digest,
            "CANDOR validation report",
        )
    return summary


def main() -> None:
    args = parse_args()
    try:
        summary = run(args)
        if args.validation_report is not None:
            target = args.validation_report.resolve()
            for filename, digest in summary["bundle_sha256"].items():
                require_unchanged(args.output.resolve() / filename, digest, "CANDOR bundle file")
            atomic_write(target, json_bytes(summary), args.replace_report)
            require(mode(target) == 0o600, "Validation report must be mode 0600")
        print(json.dumps(summary, indent=2, sort_keys=True))
    except (AssertionError, KeyError, TypeError, json.JSONDecodeError, OSError, ValueError) as exc:
        if isinstance(exc, OSError):
            print("CANDOR validation failed: restricted file operation failed", file=sys.stderr)
        else:
            print(f"CANDOR validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
