#!/usr/bin/env python3
"""Validate a restricted KODIS bundle without printing transcript text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from prepare_kodis import (
    BUILD_REPORT_KEYS,
    CONTEXT_KEYS,
    DATASET_ROOT,
    DATE_RE,
    DEMO_ADAPTER_PATH,
    DEMO_ADAPTER_SHA256,
    DEMO_INPUT_SHA256,
    DEMO_SOURCE_MANIFEST_PATH,
    DEMO_SOURCE_MANIFEST_SHA256,
    DEMO_SPLIT_MANIFEST_PATH,
    DEMO_SPLIT_MANIFEST_SHA256,
    EMAIL_RE,
    HANDLE_RE,
    IPV4_RE,
    KODIS_DEMO_INPUT,
    KODIS_DEMO_INPUT_ROOT,
    KODIS_DEMO_OUTPUT,
    KODIS_FIXTURE_ROOT,
    KODIS_OUTPUT_ROOT,
    KODIS_RAW_ROOT,
    KODIS_TEST_OUTPUT_ROOT,
    LINKAGE_GROUP_KEYS,
    PHONE_RE,
    PIPELINE_VERSION,
    PROVENANCE_KEYS,
    PSEUDONYM_RE,
    QUALITY_KEYS,
    REAL_ADAPTER_NAME,
    REAL_SOURCE_MANIFEST_NAME,
    REAL_SPLIT_MANIFEST_NAME,
    RECORD_KEYS,
    SPLIT_RE,
    URL_RE,
    atomic_write,
    build_records,
    enforce_demo_controls,
    enforce_real_controls,
    file_digest,
    inventory_snapshots,
    is_within,
    iter_forbidden_keys,
    json_bytes,
    load_json_snapshot,
    load_secret,
    mode,
    require,
    require_clean_output_directory,
    require_private_mode,
    require_unchanged,
    sha256_bytes,
    validate_adapter,
    validate_source_manifest,
    validate_split_manifest,
)


VALIDATION_SUMMARY_KEYS = {
    "status",
    "corpus",
    "data_status",
    "authorization_status",
    "model_or_rater_processing_status",
    "records",
    "sources",
    "speakers",
    "linkage_components",
    "split_counts",
    "eligible_for_packet_sampling",
    "manual_privacy_review_pending",
    "shared_schema_valid",
    "human_human_only",
    "complete_dialogues_valid",
    "minimum_message_length_valid",
    "turn_order_valid",
    "buyer_first_valid",
    "alternating_roles_valid",
    "exact_duplicate_dialogues_absent",
    "linkage_component_integrity_valid",
    "linked_participant_split_isolation_valid",
    "split_manifest_applied",
    "preregistered_split_assignment_present",
    "synthetic_split_fixture_applied",
    "forbidden_output_fields_absent",
    "precise_timestamp_metadata_fields_absent",
    "free_text_privacy_review_pending",
    "bundle_sha256",
    "warning",
}
DATA_MINIMIZATION = {
    "raw_ids_written": False,
    "demographics_written": False,
    "surveys_written": False,
    "preference_justifications_written": False,
    "compensation_written": False,
    "precise_timestamps_written": False,
    "model_emotion_labels_written": False,
    "human_ai_text_written": False,
    "nonmessage_event_text_written": False,
}
WARNING = (
    "Processed KODIS text is restricted and pseudonymized, not anonymous; every excerpt "
    "remains ineligible pending documented human privacy review."
)
DIRECT_IDENTIFIER_PATTERNS = {
    "url": URL_RE,
    "email": EMAIL_RE,
    "ip_address": IPV4_RE,
    "handle": HANDLE_RE,
    "phone_like_number": PHONE_RE,
    "exact_date": DATE_RE,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate restricted KODIS output.")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path)
    parser.add_argument("--secret-file", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--replace-report", action="store_true")
    return parser.parse_args()


def read_jsonl_snapshot(path: Path) -> tuple[list[dict[str, Any]], str]:
    require(path.is_file() and not path.is_symlink(), f"Missing or symlinked KODIS bundle file: {path.name}")
    content = path.read_bytes()
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), f"KODIS {path.name} line {line_number} is not an object")
        values.append(value)
    require(values, f"KODIS {path.name} is empty")
    return values, sha256_bytes(content)


def validate_schema(records: list[dict[str, Any]]) -> None:
    schema = json.loads((DATASET_ROOT / "schemas" / "experiment_record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for record in records:
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        require(not errors, "KODIS record does not conform to the shared experiment schema")


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


def validate_record_shape(record: dict[str, Any], model_authorized: bool, split_applied: bool) -> None:
    require(set(record) == RECORD_KEYS, "Unexpected KODIS record fields")
    require(record.get("corpus") == "kodis", "KODIS record corpus mismatch")
    for key, prefix in (
        ("record_id", "kodis_record_"),
        ("source_id", "kodis_source_"),
        ("speaker_id", "kodis_speaker_"),
    ):
        require(isinstance(record.get(key), str) and record[key].startswith(prefix) and PSEUDONYM_RE.fullmatch(record[key]), f"Invalid KODIS {key}")
    require(isinstance(record.get("split"), str) and SPLIT_RE.fullmatch(record["split"]), "Invalid KODIS split")
    require(isinstance(record.get("text"), str) and record["text"].strip(), "Empty KODIS text")
    require(not list(iter_forbidden_keys(record)), "Forbidden metadata or raw-ID field in KODIS output")
    for label, pattern in DIRECT_IDENTIFIER_PATTERNS.items():
        require(not pattern.search(record["text"]), f"Unmasked {label} pattern remains in KODIS text")

    context = record.get("context")
    require(isinstance(context, dict) and set(context) == CONTEXT_KEYS, "Unexpected KODIS context fields")
    require(isinstance(context["preceding_record_ids"], list) and len(context["preceding_record_ids"]) == len(set(context["preceding_record_ids"])), "Invalid KODIS preceding context")
    require(context["moderator_question"] is None, "KODIS output cannot contain moderator text")
    require(context["reply_to_record_id"] is None or (isinstance(context["reply_to_record_id"], str) and PSEUDONYM_RE.fullmatch(context["reply_to_record_id"])), "Invalid KODIS reply reference")
    require(isinstance(context["turn_index"], int) and not isinstance(context["turn_index"], bool), "KODIS turn index must be an integer")

    strata = record.get("sampling_strata")
    require(isinstance(strata, dict) and set(strata) == {"speaker_role"}, "KODIS may retain only speaker_role strata")
    require(strata["speaker_role"] in {"buyer", "seller"}, "Invalid KODIS speaker role")
    provenance = record.get("provenance")
    require(isinstance(provenance, dict) and set(provenance) == PROVENANCE_KEYS, "Unexpected KODIS provenance fields")
    require(provenance["source_file_role"] == "human_human_dialogue_turns", "KODIS source role mismatch")
    require(isinstance(provenance["source_file_id"], str) and provenance["source_file_id"].startswith("kodis_file_") and PSEUDONYM_RE.fullmatch(provenance["source_file_id"]), "Invalid KODIS source-file pseudonym")
    require(isinstance(provenance["source_row"], int) and provenance["source_row"] >= 1, "Invalid KODIS source row")
    require(provenance["source_turn_index"] == context["turn_index"], "KODIS source turn lineage mismatch")
    require(isinstance(provenance["source_text_hmac_sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", provenance["source_text_hmac_sha256"]), "Invalid KODIS text HMAC")
    require(isinstance(provenance["linkage_group_id"], str) and provenance["linkage_group_id"].startswith("kodis_linkage_") and PSEUDONYM_RE.fullmatch(provenance["linkage_group_id"]), "Invalid KODIS linkage ID")

    quality = record.get("quality")
    require(isinstance(quality, dict) and set(quality) == QUALITY_KEYS, "Unexpected KODIS quality fields")
    require(quality["eligible_for_packet_sampling"] is False, "Unreviewed KODIS record became eligible")
    require(quality["manual_excerpt_review_required"] is True, "KODIS manual-review gate is missing")
    require(quality["privacy_review_status"] == "pending", "Unexpected KODIS privacy-review status")
    require(isinstance(quality["ineligible_reasons"], list) and len(quality["ineligible_reasons"]) == len(set(quality["ineligible_reasons"])), "Invalid KODIS ineligibility reasons")
    require("manual_privacy_review_pending" in quality["ineligible_reasons"], "KODIS pending privacy review is not an ineligibility reason")
    require(("model_or_rater_processing_not_authorized" not in quality["ineligible_reasons"]) is model_authorized, "KODIS model/rater authorization reason mismatch")
    require(("split_pending_preregistration" not in quality["ineligible_reasons"]) is split_applied, "KODIS split-pending reason mismatch")
    require(isinstance(quality["privacy_masks_applied"], list) and quality["privacy_masks_applied"] == sorted(set(quality["privacy_masks_applied"])), "Invalid KODIS privacy-mask labels")


def validate_dialogue_lineage(records: list[dict[str, Any]], context_turns: int, minimum_turns: int) -> None:
    by_id = {record["record_id"]: record for record in records}
    require(len(by_id) == len(records), "Duplicate KODIS record IDs")
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_source[record["source_id"]].append(record)
    for source_records in by_source.values():
        ordered = sorted(source_records, key=lambda record: record["context"]["turn_index"])
        require(len(ordered) >= minimum_turns, "KODIS complete dialogue has fewer than eight messages")
        require([record["context"]["turn_index"] for record in ordered] == list(range(1, len(ordered) + 1)), "KODIS message turns are not consecutive from one")
        require([record["provenance"]["source_row"] for record in ordered] == sorted(record["provenance"]["source_row"] for record in ordered), "KODIS source-row order conflicts with message order")
        roles = [record["sampling_strata"]["speaker_role"] for record in ordered]
        require(roles[0] == "buyer", "KODIS dialogue does not begin with buyer")
        require(set(roles) == {"buyer", "seller"}, "KODIS dialogue is not dyadic buyer/seller")
        require(all(role != roles[index - 1] for index, role in enumerate(roles[1:], start=1)), "KODIS roles do not alternate")
        seen: list[str] = []
        split = ordered[0]["split"]
        component = ordered[0]["provenance"]["linkage_group_id"]
        for record in ordered:
            require(record["split"] == split, "KODIS dialogue crosses splits")
            require(record["provenance"]["linkage_group_id"] == component, "KODIS dialogue crosses linkage components")
            require(record["context"]["preceding_record_ids"] == seen[-context_turns:] if context_turns else record["context"]["preceding_record_ids"] == [], "KODIS preceding-turn lineage mismatch")
            reply = record["context"]["reply_to_record_id"]
            if reply is not None:
                require(reply in seen and by_id[reply]["source_id"] == record["source_id"], "KODIS reply is missing, cross-dialogue, or forward")
            seen.append(record["record_id"])


def recompute_components(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_speakers: dict[str, set[str]] = defaultdict(set)
    for record in records:
        source_speakers[record["source_id"]].add(record["speaker_id"])
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source_id, speakers in source_speakers.items():
        for speaker_id in speakers:
            source_node = f"source:{source_id}"
            speaker_node = f"speaker:{speaker_id}"
            adjacency[source_node].add(speaker_node)
            adjacency[speaker_node].add(source_node)
    seen: set[str] = set()
    components = []
    for start in sorted(adjacency):
        if start in seen:
            continue
        stack = [start]
        nodes: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            nodes.add(node)
            stack.extend(sorted(adjacency[node] - seen))
        components.append(
            {
                "source_ids": sorted(node.removeprefix("source:") for node in nodes if node.startswith("source:")),
                "speaker_ids": sorted(node.removeprefix("speaker:") for node in nodes if node.startswith("speaker:")),
            }
        )
    return components


def validate_linkage(records: list[dict[str, Any]], groups: list[dict[str, Any]]) -> None:
    require(groups, "KODIS linkage bundle is empty")
    group_ids: set[str] = set()
    stored_memberships: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    group_by_id: dict[str, dict[str, Any]] = {}
    for group in groups:
        require(set(group) == LINKAGE_GROUP_KEYS, "Unexpected KODIS linkage-group fields")
        component_id = group.get("component_id")
        require(isinstance(component_id, str) and component_id.startswith("kodis_linkage_") and PSEUDONYM_RE.fullmatch(component_id), "Invalid KODIS component ID")
        require(component_id not in group_ids, "Duplicate KODIS component ID")
        group_ids.add(component_id)
        require(isinstance(group.get("source_ids"), list) and group["source_ids"] == sorted(set(group["source_ids"])), "Invalid KODIS component sources")
        require(isinstance(group.get("speaker_ids"), list) and group["speaker_ids"] == sorted(set(group["speaker_ids"])), "Invalid KODIS component speakers")
        require(all(PSEUDONYM_RE.fullmatch(value) and value.startswith("kodis_source_") for value in group["source_ids"]), "Invalid KODIS component source ID")
        require(all(PSEUDONYM_RE.fullmatch(value) and value.startswith("kodis_speaker_") for value in group["speaker_ids"]), "Invalid KODIS component speaker ID")
        require(isinstance(group.get("record_count"), int) and group["record_count"] >= 1, "Invalid KODIS component record count")
        require(isinstance(group.get("split"), str) and SPLIT_RE.fullmatch(group["split"]), "Invalid KODIS component split")
        stored_memberships.add((tuple(group["source_ids"]), tuple(group["speaker_ids"])))
        group_by_id[component_id] = group
    recomputed = {
        (tuple(component["source_ids"]), tuple(component["speaker_ids"]))
        for component in recompute_components(records)
    }
    require(stored_memberships == recomputed, "Stored KODIS linkage groups differ from conversation-participant graph")
    source_splits: dict[str, set[str]] = defaultdict(set)
    speaker_splits: dict[str, set[str]] = defaultdict(set)
    counts = Counter(record["provenance"]["linkage_group_id"] for record in records)
    for record in records:
        group = group_by_id.get(record["provenance"]["linkage_group_id"])
        require(group is not None, "KODIS record linkage component is missing")
        require(record["source_id"] in group["source_ids"] and record["speaker_id"] in group["speaker_ids"], "KODIS record/component membership mismatch")
        require(record["split"] == group["split"], "KODIS component crosses splits")
        source_splits[record["source_id"]].add(record["split"])
        speaker_splits[record["speaker_id"]].add(record["split"])
    require(all(len(values) == 1 for values in source_splits.values()), "KODIS dialogue crosses splits")
    require(all(len(values) == 1 for values in speaker_splits.values()), "Linked KODIS participant crosses splits")
    for component_id, group in group_by_id.items():
        require(group["record_count"] == counts[component_id], "KODIS component record count mismatch")


def expected_report(
    args: argparse.Namespace,
    adapter: dict[str, Any],
    adapter_digest: str,
    source_manifest: dict[str, Any],
    source_manifest_digest: str,
    split_manifest_digest: str | None,
    pipeline_digest: str,
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    selected_count: int,
) -> dict[str, Any]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_file": "prepare_kodis.py",
        "pipeline_sha256": pipeline_digest,
        "corpus": "kodis",
        "data_status": "restricted_pseudonymized_pending_manual_privacy_review",
        "authorization_status": source_manifest["status"],
        "local_preprocessing_ethics_status": source_manifest["local_preprocessing_ethics_status"],
        "model_or_rater_processing_status": source_manifest["model_or_rater_processing_status"],
        "adapter_file": args.adapter.name,
        "adapter_sha256": adapter_digest,
        "source_manifest_file": args.source_manifest.name,
        "source_manifest_sha256": source_manifest_digest,
        "split_manifest_file": None if args.split_manifest is None else args.split_manifest.name,
        "split_manifest_sha256": split_manifest_digest,
        "demo_mode": bool(args.demo),
        "synthetic_fixture": bool(args.demo),
        "input_format": adapter["input_format"],
        "selected_input_files": selected_count,
        **{key: diagnostics[key] for key in (
            "input_rows",
            "input_sources",
            "filtered_non_human_rows",
            "filtered_non_human_sources",
            "filtered_incomplete_rows",
            "filtered_incomplete_sources",
            "filtered_nonmessage_rows",
        )},
        "records_written": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "linkage_components": len(groups),
        "context_turns": adapter["context_turns"],
        "minimum_message_turns": adapter["dialogue_rules"]["minimum_message_turns"],
        "complete_dialogues_valid": True,
        "turn_order_valid": True,
        "buyer_first_valid": True,
        "alternating_roles_valid": True,
        "exact_duplicate_dialogues": diagnostics["exact_duplicate_dialogues"],
        "split_manifest_applied": args.split_manifest is not None,
        "split_counts": dict(sorted(Counter(record["split"] for record in records).items())),
        "eligible_for_packet_sampling": 0,
        "privacy_review_pending": len(records),
        "privacy_mask_counts": diagnostics["privacy_mask_counts"],
        "data_minimization": DATA_MINIMIZATION,
        "warning": WARNING,
    }


def validation_summary(
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    report: dict[str, Any],
    bundle_digests: dict[str, str],
    split_applied: bool,
    demo: bool,
) -> dict[str, Any]:
    summary = {
        "status": "ok",
        "corpus": "kodis",
        "data_status": "restricted_pseudonymized_pending_manual_privacy_review",
        "authorization_status": report["authorization_status"],
        "model_or_rater_processing_status": report["model_or_rater_processing_status"],
        "records": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "linkage_components": len(groups),
        "split_counts": dict(sorted(Counter(record["split"] for record in records).items())),
        "eligible_for_packet_sampling": 0,
        "manual_privacy_review_pending": len(records),
        "shared_schema_valid": True,
        "human_human_only": True,
        "complete_dialogues_valid": True,
        "minimum_message_length_valid": True,
        "turn_order_valid": True,
        "buyer_first_valid": True,
        "alternating_roles_valid": True,
        "exact_duplicate_dialogues_absent": True,
        "linkage_component_integrity_valid": True,
        "linked_participant_split_isolation_valid": split_applied,
        "split_manifest_applied": split_applied,
        "preregistered_split_assignment_present": split_applied and not demo,
        "synthetic_split_fixture_applied": split_applied and demo,
        "forbidden_output_fields_absent": True,
        "precise_timestamp_metadata_fields_absent": True,
        "free_text_privacy_review_pending": True,
        "bundle_sha256": dict(sorted(bundle_digests.items())),
        "warning": "Validated KODIS structure is restricted and pseudonymized, not anonymous.",
    }
    require(set(summary) == VALIDATION_SUMMARY_KEYS, "Internal KODIS validation-summary shape changed")
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.demo:
        enforce_demo_controls(args)
    else:
        enforce_real_controls(args)
    secret = load_secret(args.secret_file, args.demo)
    output = args.output.resolve()
    require(output.is_dir() and not output.is_symlink(), "KODIS output directory is missing or symlinked")
    require_clean_output_directory(output)
    validation_report_path = output / "validation_report.json"
    if args.validation_report is not None:
        require(args.validation_report.resolve() == validation_report_path, "KODIS validation report must use reserved validation_report.json path")

    records_path = output / "records.jsonl"
    groups_path = output / "linkage_groups.jsonl"
    report_path = output / "build_report.json"
    records, records_digest = read_jsonl_snapshot(records_path)
    groups, groups_digest = read_jsonl_snapshot(groups_path)
    report, report_digest = load_json_snapshot(report_path)
    require(set(report) == BUILD_REPORT_KEYS, "Unexpected KODIS build-report fields")

    existing_validation_report = None
    existing_validation_digest = None
    if validation_report_path.exists() and args.validation_report is None:
        existing_validation_report, existing_validation_digest = load_json_snapshot(validation_report_path)

    snapshots = inventory_snapshots(args.input_root.resolve(), private=not args.demo)
    adapter, adapter_digest = load_json_snapshot(args.adapter)
    source_manifest, source_manifest_digest = load_json_snapshot(args.source_manifest)
    split_manifest = None
    split_manifest_digest = None
    if args.split_manifest is not None:
        split_manifest, split_manifest_digest = load_json_snapshot(args.split_manifest)
    if args.demo:
        require(adapter_digest == DEMO_ADAPTER_SHA256, "Demo KODIS adapter checksum changed")
        require(source_manifest_digest == DEMO_SOURCE_MANIFEST_SHA256, "Demo KODIS source-manifest checksum changed")
        require(split_manifest_digest == DEMO_SPLIT_MANIFEST_SHA256, "Demo KODIS split-manifest checksum changed")
        require(len(snapshots) == 1 and snapshots[0].path.resolve() == KODIS_DEMO_INPUT.resolve() and snapshots[0].sha256 == DEMO_INPUT_SHA256, "Demo KODIS input changed")
    entries = validate_source_manifest(source_manifest, snapshots, args.demo)
    selected_paths = {entry["path"] for entry in entries if entry["selected_for_transcript_processing"]}
    selected = [snapshot for snapshot in snapshots if snapshot.relative_path in selected_paths]
    validate_adapter(adapter, selected, entries, args.demo)
    expected_records, expected_groups, diagnostics = build_records(selected, adapter, source_manifest, split_manifest, secret, args.demo)
    require(records == expected_records, "KODIS records are not bound to the authorized input and controls")
    require(groups == expected_groups, "KODIS linkage groups are not bound to the authorized input and controls")

    validate_schema(records)
    model_authorized = source_manifest["model_or_rater_processing_status"] == "documented_approved_restricted"
    for record in records:
        validate_record_shape(record, model_authorized, split_manifest is not None)
    validate_dialogue_lineage(records, adapter["context_turns"], adapter["dialogue_rules"]["minimum_message_turns"])
    validate_linkage(records, groups)
    if split_manifest is not None:
        validate_split_manifest(split_manifest, {group["component_id"] for group in groups}, args.demo)

    pipeline_path = DATASET_ROOT / "scripts" / "prepare_kodis.py"
    pipeline_digest = file_digest(pipeline_path)
    expected = expected_report(
        args,
        adapter,
        adapter_digest,
        source_manifest,
        source_manifest_digest,
        split_manifest_digest,
        pipeline_digest,
        records,
        groups,
        diagnostics,
        len(selected),
    )
    require(report == expected, "KODIS build report is not bound to the bundle, inputs, and controls")
    require(not list(iter_forbidden_keys({key: value for key, value in report.items() if key not in {"data_minimization", "privacy_mask_counts"}})), "Forbidden metadata or raw-ID key in KODIS build report")

    permission_paths = [records_path, groups_path, report_path]
    if validation_report_path.exists():
        permission_paths.append(validation_report_path)
    require_private_mode(output, "KODIS output directory")
    for path in permission_paths:
        require_private_mode(path, f"KODIS output {path.name}")
        require(mode(path) == 0o600, f"KODIS output {path.name} must be mode 0600")
    require(mode(output) == 0o700, "KODIS output directory must be mode 0700")

    for snapshot in snapshots:
        require_unchanged(snapshot.path, snapshot.sha256, "KODIS package file")
    require_unchanged(args.adapter, adapter_digest, "KODIS adapter")
    require_unchanged(args.source_manifest, source_manifest_digest, "KODIS source manifest")
    if args.split_manifest is not None and split_manifest_digest is not None:
        require_unchanged(args.split_manifest, split_manifest_digest, "KODIS split manifest")
    require_unchanged(pipeline_path, pipeline_digest, "KODIS pipeline")
    require_unchanged(records_path, records_digest, "KODIS records")
    require_unchanged(groups_path, groups_digest, "KODIS linkage groups")
    require_unchanged(report_path, report_digest, "KODIS build report")

    bundle_digests = {
        records_path.name: records_digest,
        groups_path.name: groups_digest,
        report_path.name: report_digest,
    }
    summary = validation_summary(records, groups, report, bundle_digests, split_manifest is not None, args.demo)
    if existing_validation_report is not None:
        require(existing_validation_report == summary, "Existing KODIS validation report does not match the current bundle")
        require(existing_validation_digest is not None, "Existing KODIS validation-report snapshot is missing")
        require_unchanged(validation_report_path, existing_validation_digest, "KODIS validation report")
    return summary


def main() -> None:
    args = parse_args()
    try:
        summary = run(args)
        if args.validation_report is not None:
            current_report, _ = load_json_snapshot(args.output.resolve() / "build_report.json")
            require(file_digest(args.adapter) == current_report["adapter_sha256"], "KODIS adapter changed before validation-report commit")
            require(
                file_digest(args.source_manifest) == current_report["source_manifest_sha256"],
                "KODIS source manifest changed before validation-report commit",
            )
            if args.split_manifest is not None:
                require(
                    file_digest(args.split_manifest) == current_report["split_manifest_sha256"],
                    "KODIS split manifest changed before validation-report commit",
                )
            require(
                file_digest(DATASET_ROOT / "scripts" / "prepare_kodis.py")
                == current_report["pipeline_sha256"],
                "KODIS pipeline changed before validation-report commit",
            )
            current_manifest, _ = load_json_snapshot(args.source_manifest)
            current_snapshots = inventory_snapshots(
                args.input_root.resolve(), private=not args.demo
            )
            validate_source_manifest(current_manifest, current_snapshots, args.demo)
            for filename, digest in summary["bundle_sha256"].items():
                require_unchanged(args.output.resolve() / filename, digest, "KODIS bundle file")
            atomic_write(args.validation_report.resolve(), json_bytes(summary), args.replace_report)
            require(mode(args.validation_report.resolve()) == 0o600, "KODIS validation report must be mode 0600")
        print(json.dumps(summary, indent=2, sort_keys=True))
    except (AssertionError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as exc:
        if isinstance(exc, OSError):
            print("KODIS validation failed: restricted file operation failed", file=sys.stderr)
        else:
            print(f"KODIS validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
