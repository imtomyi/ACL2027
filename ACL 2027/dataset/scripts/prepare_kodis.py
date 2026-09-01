#!/usr/bin/env python3
"""Fail-closed KODIS inventory and restricted transcript preprocessing."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


PIPELINE_VERSION = "2.0"
DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DATASET_ROOT.parent
KODIS_RAW_ROOT = DATASET_ROOT / "raw" / "kodis"
KODIS_OUTPUT_ROOT = DATASET_ROOT / "deidentified" / "kodis"
KODIS_FIXTURE_ROOT = DATASET_ROOT / "fixtures" / "kodis_synthetic"
KODIS_DEMO_INPUT_ROOT = KODIS_FIXTURE_ROOT / "package"
KODIS_DEMO_INPUT = KODIS_DEMO_INPUT_ROOT / "kodis_dialogue_turns.jsonl"
KODIS_DEMO_OUTPUT = PROJECT_ROOT / "Storage" / "synthetic-results" / "dataset-demos" / "kodis_demo"
KODIS_TEST_OUTPUT_ROOT = KODIS_FIXTURE_ROOT / "test_outputs"

DEMO_ADAPTER_PATH = DATASET_ROOT / "manifests" / "kodis_demo_adapter.json"
DEMO_SOURCE_MANIFEST_PATH = DATASET_ROOT / "manifests" / "kodis_demo_source_manifest.json"
DEMO_SPLIT_MANIFEST_PATH = DATASET_ROOT / "manifests" / "kodis_demo_split_manifest.json"
DEMO_ADAPTER_SHA256 = "c031e32bf67b7cd6031d587be6bce7c9d84b389b052b0d116a4cda021ef15bec"
DEMO_SOURCE_MANIFEST_SHA256 = "af57e16bd966972510852c226cfb66e5fca1067aa66a9e8627fe065c6c606e97"
DEMO_SPLIT_MANIFEST_SHA256 = "ac48b389ecdfe770f7a1f8edecb1fa7f3be20c682a8879aa45a68fb4d5aa078f"
DEMO_INPUT_SHA256 = "9ec8e1932e550d4c97243995d8036fe498e04e688457d80d16b647fb05e9e697"
DEMO_SECRET = b"WarrantRoute KODIS synthetic fixture secret only"

REAL_ADAPTER_NAME = "kodis_adapter.local.json"
REAL_SOURCE_MANIFEST_NAME = "kodis_source_manifest.local.json"
REAL_SPLIT_MANIFEST_NAME = "kodis_splits.local.json"
OUTPUT_BUNDLE_NAMES = {
    "records.jsonl",
    "linkage_groups.jsonl",
    "build_report.json",
    "validation_report.json",
}
RAW_CONTROL_NAMES = {
    "README.md",
    REAL_ADAPTER_NAME,
    REAL_SOURCE_MANIFEST_NAME,
    REAL_SPLIT_MANIFEST_NAME,
}

ADAPTER_KEYS = {
    "adapter_version",
    "corpus",
    "verification_status",
    "input_format",
    "source_file_role",
    "input_files",
    "context_turns",
    "row_order_policy",
    "speaker_identity_scope",
    "speaker_ids_are_person_stable_across_conversations",
    "fields",
    "filters",
    "dialogue_rules",
    "role_value_map",
    "sampling_strata",
    "verified_input_fields",
    "discarded_input_fields",
    "verification_notes",
}
FIELD_ROLES = {
    "source_id",
    "record_id",
    "speaker_id",
    "speaker_role",
    "text",
    "turn_index",
    "reply_to",
    "interaction_type",
    "dialogue_complete",
    "event_type",
}
FILTER_KEYS = {
    "interaction_type_allow",
    "dialogue_complete_allow",
    "event_type_allow",
}
DIALOGUE_RULE_KEYS = {
    "minimum_message_turns",
    "turn_index_policy",
    "required_roles",
    "buyer_first",
    "alternating_roles",
    "reject_exact_duplicate_dialogues",
}
SOURCE_MANIFEST_KEYS = {
    "manifest_version",
    "corpus",
    "status",
    "created_by",
    "access_method",
    "authorization_reference",
    "agreement_version",
    "agreement_accepted_date",
    "receipt_date",
    "package_version",
    "approved_users_or_team",
    "noncommercial_research_only_acknowledged",
    "redistribution_restrictions_reviewed",
    "identity_protection_requirements_reviewed",
    "local_preprocessing_authorized",
    "local_preprocessing_ethics_status",
    "model_or_rater_processing_status",
    "manual_privacy_review_plan_status",
    "file_inventory",
}
INVENTORY_ENTRY_KEYS = {
    "path",
    "sha256",
    "bytes",
    "rows",
    "input_format",
    "content_role",
    "selected_for_transcript_processing",
}
SPLIT_MANIFEST_KEYS = {
    "split_manifest_version",
    "corpus",
    "status",
    "assignment_unit",
    "assignments",
    "notes",
}
LINKAGE_GROUP_KEYS = {"component_id", "source_ids", "speaker_ids", "record_count", "split"}
BUILD_REPORT_KEYS = {
    "pipeline_version",
    "pipeline_file",
    "pipeline_sha256",
    "corpus",
    "data_status",
    "authorization_status",
    "local_preprocessing_ethics_status",
    "model_or_rater_processing_status",
    "adapter_file",
    "adapter_sha256",
    "source_manifest_file",
    "source_manifest_sha256",
    "split_manifest_file",
    "split_manifest_sha256",
    "demo_mode",
    "synthetic_fixture",
    "input_format",
    "selected_input_files",
    "input_rows",
    "input_sources",
    "filtered_non_human_rows",
    "filtered_non_human_sources",
    "filtered_incomplete_rows",
    "filtered_incomplete_sources",
    "filtered_nonmessage_rows",
    "records_written",
    "sources",
    "speakers",
    "linkage_components",
    "context_turns",
    "minimum_message_turns",
    "complete_dialogues_valid",
    "turn_order_valid",
    "buyer_first_valid",
    "alternating_roles_valid",
    "exact_duplicate_dialogues",
    "split_manifest_applied",
    "split_counts",
    "eligible_for_packet_sampling",
    "privacy_review_pending",
    "privacy_mask_counts",
    "data_minimization",
    "warning",
}

RECORD_KEYS = {
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
CONTEXT_KEYS = {"preceding_record_ids", "moderator_question", "reply_to_record_id", "turn_index"}
PROVENANCE_KEYS = {
    "source_file_role",
    "source_file_id",
    "source_row",
    "source_turn_index",
    "source_text_hmac_sha256",
    "linkage_group_id",
}
QUALITY_KEYS = {
    "eligible_for_packet_sampling",
    "ineligible_reasons",
    "privacy_masks_applied",
    "manual_excerpt_review_required",
    "privacy_review_status",
}

REAL_ADAPTER_NOTE = (
    "Verified against the authorized KODIS package: selected transcript files, exact fields, "
    "human-human and completeness markers, message-event filter, consecutive message order, "
    "buyer/seller role mapping, and globally person-stable participant linkage were manually confirmed."
)
DEMO_ADAPTER_NOTE = (
    "Synthetic KODIS fixture only: mappings, human-human and completion markers, message order, "
    "dyadic roles, and globally stable fictional participant keys were verified against the shipped fixture."
)

SPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,}")
PHONE_RE = re.compile(r"(?<!\d)\+?\d(?:[\s().-]*\d){6,14}(?!\d)")
IPV4_RE = re.compile(
    r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)"
)
DATE_RE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])(?!\d)"
    r"|(?<!\d)(?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.](?:19|20)?\d{2}(?!\d)"
)
DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
PSEUDONYM_RE = re.compile(r"^kodis_(?:file|source|speaker|record|linkage)_[a-f0-9]{16}$")
SPLIT_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
FORBIDDEN_OUTPUT_KEYS = {
    "address",
    "age",
    "audio",
    "compensation",
    "country",
    "culture_cluster",
    "demographics",
    "education",
    "email",
    "employment",
    "employer",
    "gender",
    "ip_address",
    "location",
    "model_emotion_label",
    "name",
    "participant_id",
    "phone",
    "preference_justification",
    "race",
    "raw_conversation_id",
    "school",
    "sex",
    "survey",
    "survey_response",
    "survey_responses",
    "timestamp",
    "timestamps",
    "worker_id",
}
FORBIDDEN_TEXT_COLUMN_TOKENS = {
    "age",
    "country",
    "culture",
    "demographic",
    "education",
    "emotion",
    "gender",
    "ip",
    "location",
    "personality",
    "preference",
    "survey",
    "timestamp",
    "worker",
}


@dataclass(frozen=True)
class InputSnapshot:
    path: Path
    relative_path: str
    content: bytes = field(repr=False)
    sha256: str
    size: int
    rows: tuple[dict[str, Any], ...] = field(repr=False)
    input_format: str
    fields: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory or prepare restricted KODIS transcripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="Create a pending restricted package receipt.")
    inspect_parser.add_argument("--input-root", type=Path, required=True)
    inspect_parser.add_argument("--output", type=Path, required=True)
    inspect_parser.add_argument("--replace", action="store_true")

    build_parser = subparsers.add_parser("build", help="Build pseudonymized KODIS records.")
    build_parser.add_argument("--input-root", type=Path, required=True)
    build_parser.add_argument("--adapter", type=Path, required=True)
    build_parser.add_argument("--source-manifest", type=Path, required=True)
    build_parser.add_argument("--split-manifest", type=Path)
    build_parser.add_argument("--secret-file", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--demo", action="store_true")
    build_parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def require_private_mode(path: Path, label: str) -> None:
    require(path.exists(), f"Missing {label}")
    require(not path.is_symlink(), f"{label} cannot be a symlink")
    require(mode(path) & 0o077 == 0, f"{label} permits group/other access")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def require_exact_path(path: Path, expected: Path, label: str) -> None:
    require(path.resolve() == expected.resolve(), f"{label} must use {expected}")


def require_safe_relative_path(value: str) -> None:
    path = Path(value)
    require(value and not path.is_absolute(), "Inventory path must be relative")
    require(".." not in path.parts and "." not in path.parts, "Unsafe inventory path")
    require(not value.startswith("/"), "Unsafe inventory path")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def jsonl_bytes(values: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        for value in values
    )


def load_json_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    require(path.is_file() and not path.is_symlink(), f"Missing or symlinked JSON control: {path.name}")
    content = path.read_bytes()
    value = json.loads(content.decode("utf-8"))
    require(isinstance(value, dict), f"{path.name} must contain a JSON object")
    return value, sha256_bytes(content)


def require_unchanged(path: Path, expected_digest: str, label: str) -> None:
    require(file_digest(path) == expected_digest, f"{label} changed during KODIS processing")


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def require_clean_output_directory(path: Path) -> None:
    for entry in path.iterdir():
        require(not entry.is_symlink(), "KODIS output cannot contain symlinks")
        require(entry.is_file(), "KODIS output cannot contain subdirectories")
        require(entry.name in OUTPUT_BUNDLE_NAMES, "Unexpected file in KODIS output bundle")


def atomic_write(path: Path, content: bytes, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(f"Refusing to replace {path}; add --replace after review")
    ensure_private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def infer_input_format(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".csv":
        return "csv"
    return "uninspected"


def parse_rows(content: bytes, input_format: str, label: str) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    if input_format == "jsonl":
        text = content.decode("utf-8")
        rows: list[dict[str, Any]] = []
        fields: tuple[str, ...] | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            require(isinstance(value, dict), f"{label} line {line_number} is not an object")
            current = tuple(value.keys())
            if fields is None:
                fields = current
            require(set(current) == set(fields), f"{label} has inconsistent JSONL fields")
            rows.append(value)
        require(rows, f"{label} has no data rows")
        return tuple(rows), fields or ()
    if input_format == "csv":
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        parsed = list(reader)
        require(parsed, f"{label} has no CSV header")
        headers = parsed[0]
        require(headers and all(value.strip() for value in headers), f"{label} has an empty CSV header")
        require(len(headers) == len(set(headers)), f"{label} has duplicate CSV headers")
        rows = []
        for row_number, values in enumerate(parsed[1:], start=2):
            require(len(values) == len(headers), f"{label} row {row_number} has the wrong width")
            rows.append(dict(zip(headers, values, strict=True)))
        require(rows, f"{label} has no data rows")
        return tuple(rows), tuple(headers)
    return (), ()


def snapshot_file(path: Path, input_root: Path, require_parsed: bool = False) -> InputSnapshot:
    require(path.is_file() and not path.is_symlink(), "KODIS package entry is not a regular file")
    require(is_within(path, input_root), "KODIS package entry escapes input root")
    relative_path = path.resolve().relative_to(input_root.resolve()).as_posix()
    require_safe_relative_path(relative_path)
    content = path.read_bytes()
    input_format = infer_input_format(path)
    require(not require_parsed or input_format in {"jsonl", "csv"}, "Selected transcript file must be JSONL or CSV")
    rows, fields = parse_rows(content, input_format, relative_path)
    return InputSnapshot(
        path=path,
        relative_path=relative_path,
        content=content,
        sha256=sha256_bytes(content),
        size=len(content),
        rows=rows,
        input_format=input_format,
        fields=fields,
    )


def inventory_snapshots(input_root: Path, private: bool) -> list[InputSnapshot]:
    require(input_root.is_dir() and not input_root.is_symlink(), "KODIS input root is missing or symlinked")
    if private:
        require_private_mode(input_root, "KODIS input root")
    snapshots: list[InputSnapshot] = []
    for entry in sorted(input_root.rglob("*"), key=lambda value: value.as_posix()):
        require(not entry.is_symlink(), "KODIS input package cannot contain symlinks")
        if entry.is_dir():
            if private:
                require_private_mode(entry, "KODIS input directory")
            continue
        require(entry.is_file(), "KODIS input package contains a non-file entry")
        relative = entry.resolve().relative_to(input_root.resolve()).as_posix()
        if "/" not in relative and entry.name in RAW_CONTROL_NAMES:
            continue
        if private:
            require_private_mode(entry, "KODIS input file")
        snapshots.append(snapshot_file(entry, input_root))
    return snapshots


def inventory_entry(snapshot: InputSnapshot, selected: bool = False, content_role: str = "pending-authorized-inspection") -> dict[str, Any]:
    return {
        "path": snapshot.relative_path,
        "sha256": snapshot.sha256,
        "bytes": snapshot.size,
        "rows": len(snapshot.rows) if snapshot.input_format in {"jsonl", "csv"} else None,
        "input_format": snapshot.input_format,
        "content_role": content_role,
        "selected_for_transcript_processing": selected,
    }


def validate_inventory_entries(entries: Any) -> list[dict[str, Any]]:
    require(isinstance(entries, list) and entries, "KODIS source receipt has no file inventory")
    paths: set[str] = set()
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == INVENTORY_ENTRY_KEYS, "Invalid KODIS inventory entry")
        path = entry.get("path")
        require(isinstance(path, str), "Invalid KODIS inventory path")
        require_safe_relative_path(path)
        require(path not in paths, "Duplicate KODIS inventory path")
        paths.add(path)
        require(isinstance(entry.get("sha256"), str) and SHA256_RE.fullmatch(entry["sha256"]), "Invalid inventory SHA-256")
        require(isinstance(entry.get("bytes"), int) and not isinstance(entry["bytes"], bool) and entry["bytes"] >= 0, "Invalid inventory size")
        require(entry.get("rows") is None or (isinstance(entry["rows"], int) and not isinstance(entry["rows"], bool) and entry["rows"] >= 0), "Invalid inventory row count")
        require(entry.get("input_format") in {"jsonl", "csv", "uninspected"}, "Invalid inventory input format")
        require(isinstance(entry.get("content_role"), str) and entry["content_role"], "Missing inventory content role")
        require(isinstance(entry.get("selected_for_transcript_processing"), bool), "Invalid inventory selection flag")
    return entries


def validate_source_manifest(manifest: dict[str, Any], snapshots: list[InputSnapshot], demo: bool) -> list[dict[str, Any]]:
    require(set(manifest) == SOURCE_MANIFEST_KEYS, "Unexpected KODIS source-receipt fields")
    require(manifest.get("manifest_version") == "1.0", "Unsupported KODIS source-receipt version")
    require(manifest.get("corpus") == "kodis", "KODIS source-receipt corpus mismatch")
    entries = validate_inventory_entries(manifest.get("file_inventory"))
    observed = {snapshot.relative_path: inventory_entry(snapshot) for snapshot in snapshots}
    require(set(observed) == {entry["path"] for entry in entries}, "KODIS package inventory differs from receipt")
    for entry in entries:
        snapshot = next(item for item in snapshots if item.relative_path == entry["path"])
        require(entry["sha256"] == snapshot.sha256, "KODIS package checksum differs from receipt")
        require(entry["bytes"] == snapshot.size, "KODIS package size differs from receipt")
        expected_rows = len(snapshot.rows) if snapshot.input_format in {"jsonl", "csv"} else None
        require(entry["rows"] == expected_rows, "KODIS package row count differs from receipt")
        require(entry["input_format"] == snapshot.input_format, "KODIS package format differs from receipt")
    if demo:
        require(manifest.get("status") == "synthetic_fixture_verified", "Demo KODIS receipt status changed")
        require(manifest.get("access_method") == "synthetic_fixture", "Demo KODIS receipt route changed")
        require(manifest.get("authorization_reference") == "synthetic-fixture-no-human-data", "Demo authorization label changed")
        require(manifest.get("local_preprocessing_ethics_status") == "not-applicable-synthetic-fixture", "Demo ethics label changed")
        require(manifest.get("model_or_rater_processing_status") == "not-authorized-synthetic-demo-only", "Demo model/rater label changed")
    else:
        require(manifest.get("status") == "authorized_for_restricted_local_preprocessing", "KODIS package is not authorized for restricted local preprocessing")
        require(manifest.get("access_method") == "request_only_authorized_distribution", "KODIS access method is not verified")
        for key in (
            "authorization_reference",
            "agreement_version",
            "package_version",
            "approved_users_or_team",
        ):
            require(isinstance(manifest.get(key), str) and manifest[key].strip(), f"Missing KODIS authorization field: {key}")
        for key in ("agreement_accepted_date", "receipt_date"):
            require(isinstance(manifest.get(key), str) and DATE_VALUE_RE.fullmatch(manifest[key]), f"Invalid KODIS receipt date: {key}")
        for key in (
            "noncommercial_research_only_acknowledged",
            "redistribution_restrictions_reviewed",
            "identity_protection_requirements_reviewed",
            "local_preprocessing_authorized",
        ):
            require(manifest.get(key) is True, f"Unresolved KODIS authorization gate: {key}")
        require(
            manifest.get("local_preprocessing_ethics_status")
            in {
                "documented_institutional_determination",
                "documented_irb_or_ethics_approval",
                "documented_not_human_subjects_research",
            },
            "KODIS local-preprocessing ethics determination is unresolved",
        )
        require(
            manifest.get("model_or_rater_processing_status")
            in {"pending_separate_written_confirmation", "documented_approved_restricted"},
            "Invalid KODIS model/rater authorization status",
        )
        require(
            manifest.get("manual_privacy_review_plan_status") == "documented_two_person_review_required",
            "KODIS two-person privacy-review plan is not documented",
        )
    return entries


def metadata_like_text_column(name: str) -> bool:
    tokens = {token for token in re.split(r"[^a-z0-9]+", name.casefold()) if token}
    return bool(tokens & FORBIDDEN_TEXT_COLUMN_TOKENS)


def validate_adapter(adapter: dict[str, Any], selected: list[InputSnapshot], entries: list[dict[str, Any]], demo: bool) -> dict[str, Any]:
    require(set(adapter) == ADAPTER_KEYS, "Unexpected KODIS adapter fields")
    require(adapter.get("adapter_version") == "1.0", "Unsupported KODIS adapter version")
    require(adapter.get("corpus") == "kodis", "KODIS adapter corpus mismatch")
    if demo:
        require(adapter.get("verification_status") == "synthetic_fixture_verified", "Demo KODIS adapter is not verified")
        require(adapter.get("verification_notes") == DEMO_ADAPTER_NOTE, "Demo KODIS adapter note changed")
    else:
        require(adapter.get("verification_status") == "verified_against_authorized_package", "Real KODIS adapter mapping remains unverified")
        require(adapter.get("verification_notes") == REAL_ADAPTER_NOTE, "Real KODIS adapter note changed")
    require(adapter.get("input_format") in {"jsonl", "csv"}, "KODIS adapter input format remains unverified")
    require(adapter.get("source_file_role") == "human_human_dialogue_turns", "KODIS source-file role mismatch")
    input_files = adapter.get("input_files")
    require(isinstance(input_files, list) and input_files and all(isinstance(value, str) for value in input_files), "KODIS adapter has no selected transcript files")
    require(len(input_files) == len(set(input_files)), "Duplicate KODIS adapter input file")
    for value in input_files:
        require_safe_relative_path(value)
    selected_entries = [entry for entry in entries if entry["selected_for_transcript_processing"]]
    require(set(input_files) == {entry["path"] for entry in selected_entries}, "Adapter transcript files differ from authorized receipt selection")
    require(set(input_files) == {snapshot.relative_path for snapshot in selected}, "Adapter transcript files differ from loaded files")
    require(all(snapshot.input_format == adapter["input_format"] for snapshot in selected), "Selected KODIS file format differs from adapter")
    for entry in selected_entries:
        expected_role = "verified-synthetic-dialogue-and-quarantine-rows" if demo else "verified-dialogue-export-with-interaction-completion-and-event-markers"
        require(entry["content_role"] == expected_role, "Selected KODIS inventory content role remains unverified")

    context_turns = adapter.get("context_turns")
    require(isinstance(context_turns, int) and not isinstance(context_turns, bool) and 0 <= context_turns <= 20, "Invalid KODIS context_turns")
    require(adapter.get("row_order_policy") == "verified_integer_message_turn_index", "KODIS message order remains unverified")
    require(adapter.get("speaker_identity_scope") == "global_person_stable", "KODIS requires a global person-stable speaker key")
    require(adapter.get("speaker_ids_are_person_stable_across_conversations") is True, "KODIS cross-dialogue participant stability is unverified")

    fields = adapter.get("fields")
    require(isinstance(fields, dict) and set(fields) == FIELD_ROLES, "Unexpected KODIS adapter field roles")
    for role in FIELD_ROLES - {"reply_to"}:
        require(isinstance(fields.get(role), str) and fields[role].strip(), f"KODIS field role {role} is not mapped")
    require(fields.get("reply_to") is None or isinstance(fields["reply_to"], str), "Invalid KODIS reply mapping")
    mapped = [value for value in fields.values() if value is not None]
    require(len(mapped) == len(set(mapped)), "KODIS adapter field roles must map to distinct input fields")
    require(not metadata_like_text_column(fields["text"]), "KODIS text role is mapped to an obvious metadata field")

    verified = adapter.get("verified_input_fields")
    require(isinstance(verified, list) and verified and all(isinstance(value, str) and value for value in verified), "KODIS verified input fields are missing")
    require(len(verified) == len(set(verified)), "Duplicate KODIS verified input field")
    for snapshot in selected:
        require(set(snapshot.fields) == set(verified), "KODIS input fields differ from verified adapter")
    require(set(mapped) <= set(verified), "Mapped KODIS field is absent from verified input fields")
    discarded = adapter.get("discarded_input_fields")
    require(isinstance(discarded, list) and len(discarded) == len(set(discarded)), "Invalid KODIS discarded field list")
    require(set(discarded) == set(verified) - set(mapped), "Every nonretained KODIS input field must be explicitly discarded")

    filters = adapter.get("filters")
    require(isinstance(filters, dict) and set(filters) == FILTER_KEYS, "Unexpected KODIS filter fields")
    require(isinstance(filters["interaction_type_allow"], list) and filters["interaction_type_allow"], "KODIS human-human filter is missing")
    require(isinstance(filters["dialogue_complete_allow"], list) and filters["dialogue_complete_allow"], "KODIS completion filter is missing")
    require(isinstance(filters["event_type_allow"], list) and filters["event_type_allow"], "KODIS message-event filter is missing")
    require(all(isinstance(value, (str, int, bool)) for values in filters.values() for value in values), "Invalid KODIS filter value")
    forbidden_interactions = {str(value).casefold() for value in filters["interaction_type_allow"]}
    require(not any(any(token in value for token in ("human_ai", "gpt", "model", "bot")) for value in forbidden_interactions), "KODIS interaction allowlist includes a human-AI value")

    rules = adapter.get("dialogue_rules")
    require(isinstance(rules, dict) and set(rules) == DIALOGUE_RULE_KEYS, "Unexpected KODIS dialogue rules")
    require(rules.get("minimum_message_turns") == 8, "KODIS minimum complete-dialogue length must be eight messages")
    require(rules.get("turn_index_policy") == "consecutive_integer_starting_at_one", "KODIS turn-index policy mismatch")
    require(rules.get("required_roles") == ["buyer", "seller"], "KODIS required roles mismatch")
    require(rules.get("buyer_first") is True, "KODIS buyer-first rule is not verified")
    require(rules.get("alternating_roles") is True, "KODIS alternating-role rule is not verified")
    require(rules.get("reject_exact_duplicate_dialogues") is True, "KODIS duplicate-dialogue rejection must remain enabled")
    role_map = adapter.get("role_value_map")
    require(isinstance(role_map, dict) and set(role_map.values()) == {"buyer", "seller"} and len(role_map) == 2, "KODIS buyer/seller value map is invalid")
    require(all(isinstance(key, str) and key for key in role_map), "Invalid KODIS raw role value")
    require(adapter.get("sampling_strata") == {"speaker_role": fields["speaker_role"]}, "KODIS may retain only normalized speaker role as sampling strata")
    return fields


def validate_split_manifest(manifest: dict[str, Any], component_ids: set[str], demo: bool) -> dict[str, str]:
    require(set(manifest) == SPLIT_MANIFEST_KEYS, "Unexpected KODIS split-manifest fields")
    require(manifest.get("split_manifest_version") == "1.0", "Unsupported KODIS split-manifest version")
    require(manifest.get("corpus") == "kodis", "KODIS split-manifest corpus mismatch")
    require(manifest.get("assignment_unit") == "dialogue_participant_connected_component", "KODIS split assignment unit mismatch")
    expected_status = "synthetic_fixture_verified" if demo else "preregistered_component_assignments"
    require(manifest.get("status") == expected_status, "KODIS split-manifest status mismatch")
    assignments = manifest.get("assignments")
    require(isinstance(assignments, dict), "KODIS split assignments must be an object")
    require(set(assignments) == component_ids, "KODIS split manifest must cover every linkage component exactly")
    for component_id, split in assignments.items():
        require(PSEUDONYM_RE.fullmatch(component_id) and component_id.startswith("kodis_linkage_"), "Invalid KODIS linkage component ID")
        require(isinstance(split, str) and SPLIT_RE.fullmatch(split), "Invalid KODIS split name")
        require(split != "unassigned_pending_preregistration", "KODIS assigned split cannot remain pending")
    return assignments


def stable_hmac(secret: bytes, namespace: str, value: str) -> str:
    return hmac.new(secret, f"{namespace}\x00{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def pseudonym(secret: bytes, kind: str, value: str) -> str:
    return f"kodis_{kind}_{stable_hmac(secret, f'kodis:{kind}', value)[:16]}"


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).strip())


def privacy_mask(text: str) -> tuple[str, list[str]]:
    substitutions = (
        (URL_RE, "[URL]", "url"),
        (EMAIL_RE, "[EMAIL]", "email"),
        (IPV4_RE, "[IP_ADDRESS]", "ip_address"),
        (HANDLE_RE, "[HANDLE]", "handle"),
        (DATE_RE, "[DATE]", "exact_date"),
        (PHONE_RE, "[PHONE]", "phone_like_number"),
    )
    masked = normalize_text(text)
    flags: list[str] = []
    for pattern, replacement, label in substitutions:
        masked, count = pattern.subn(replacement, masked)
        if count:
            flags.append(label)
    return masked, sorted(flags)


def required_cell(row: dict[str, Any], field_name: str, label: str, row_number: int) -> Any:
    value = row.get(field_name)
    require(value is not None and (not isinstance(value, str) or value.strip()), f"KODIS input row {row_number} is missing {label}")
    return value


def canonical_filter_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def value_allowed(value: Any, allowed: list[Any]) -> bool:
    return canonical_filter_value(value) in {canonical_filter_value(item) for item in allowed}


def iter_forbidden_keys(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            lowered = key.casefold()
            if lowered in FORBIDDEN_OUTPUT_KEYS or lowered.startswith(("raw_", "original_")):
                yield path
            yield from iter_forbidden_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_forbidden_keys(child, f"{prefix}[{index}]")


def load_secret(secret_file: Path | None, demo: bool) -> bytes:
    if demo:
        require(secret_file is None, "--demo cannot accept a real KODIS secret file")
        return DEMO_SECRET
    require(secret_file is not None, "Real KODIS processing requires --secret-file")
    require(secret_file.is_file(), "KODIS secret file is missing")
    require_private_mode(secret_file, "KODIS secret file")
    require(not is_within(secret_file, DATASET_ROOT), "KODIS secret file must remain outside dataset/")
    secret = secret_file.read_bytes().strip()
    require(len(secret) >= 32, "KODIS secret must contain at least 32 bytes")
    return secret


def linkage_components(source_speakers: dict[str, set[str]], secret: bytes) -> list[dict[str, Any]]:
    source_nodes = {f"source:{value}" for value in source_speakers}
    speaker_nodes = {f"speaker:{value}" for values in source_speakers.values() for value in values}
    adjacency: dict[str, set[str]] = {value: set() for value in source_nodes | speaker_nodes}
    for source_id, speaker_ids in source_speakers.items():
        for speaker_id in speaker_ids:
            source_node = f"source:{source_id}"
            speaker_node = f"speaker:{speaker_id}"
            adjacency[source_node].add(speaker_node)
            adjacency[speaker_node].add(source_node)
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
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
        sources = sorted(node.removeprefix("source:") for node in nodes if node.startswith("source:"))
        speakers = sorted(node.removeprefix("speaker:") for node in nodes if node.startswith("speaker:"))
        canonical = "\x1f".join(["sources", *sources, "speakers", *speakers])
        components.append(
            {
                "component_id": pseudonym(secret, "linkage", canonical),
                "source_ids": sources,
                "speaker_ids": speakers,
            }
        )
    return sorted(components, key=lambda value: value["component_id"])


def build_records(
    selected: list[InputSnapshot],
    adapter: dict[str, Any],
    source_manifest: dict[str, Any],
    split_manifest: dict[str, Any] | None,
    secret: bytes,
    demo: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fields = adapter["fields"]
    filters = adapter["filters"]
    rules = adapter["dialogue_rules"]
    role_map = adapter["role_value_map"]
    verified_fields = set(adapter["verified_input_fields"])
    rows_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_rows = 0
    for snapshot in selected:
        file_id = pseudonym(secret, "file", snapshot.relative_path)
        for row_number, row in enumerate(snapshot.rows, start=1):
            total_rows += 1
            require(set(row) == verified_fields, "KODIS input row fields changed after adapter verification")
            source_raw = str(required_cell(row, fields["source_id"], "source identifier", row_number))
            interaction = required_cell(row, fields["interaction_type"], "interaction type", row_number)
            complete = required_cell(row, fields["dialogue_complete"], "completion marker", row_number)
            event_type = required_cell(row, fields["event_type"], "event type", row_number)
            rows_by_source[source_raw].append(
                {
                    "row": row,
                    "source_raw": source_raw,
                    "interaction": interaction,
                    "complete": complete,
                    "event_type": event_type,
                    "source_row": row_number,
                    "source_file_id": file_id,
                    "source_file_path": snapshot.relative_path,
                }
            )

    filtered_non_human_rows = 0
    filtered_non_human_sources = 0
    filtered_incomplete_rows = 0
    filtered_incomplete_sources = 0
    filtered_nonmessage_rows = 0
    selected_sources: list[tuple[str, list[dict[str, Any]]]] = []
    for source_raw, wrappers in rows_by_source.items():
        require(len({item["source_file_path"] for item in wrappers}) == 1, "A KODIS dialogue spans multiple package files")
        interactions = {canonical_filter_value(item["interaction"]) for item in wrappers}
        completions = {canonical_filter_value(item["complete"]) for item in wrappers}
        require(len(interactions) == 1, "KODIS dialogue has inconsistent interaction types")
        require(len(completions) == 1, "KODIS dialogue has inconsistent completion markers")
        if not value_allowed(wrappers[0]["interaction"], filters["interaction_type_allow"]):
            filtered_non_human_sources += 1
            filtered_non_human_rows += len(wrappers)
            continue
        if not value_allowed(wrappers[0]["complete"], filters["dialogue_complete_allow"]):
            filtered_incomplete_sources += 1
            filtered_incomplete_rows += len(wrappers)
            continue
        message_rows = [item for item in wrappers if value_allowed(item["event_type"], filters["event_type_allow"])]
        filtered_nonmessage_rows += len(wrappers) - len(message_rows)
        require(message_rows, "Complete human-human KODIS dialogue has no verified message rows")
        selected_sources.append((source_raw, message_rows))

    internal_dialogues: list[dict[str, Any]] = []
    dialogue_fingerprints: dict[str, str] = {}
    mask_counts = Counter()
    for source_raw, wrappers in selected_sources:
        prepared: list[dict[str, Any]] = []
        for wrapper in wrappers:
            row = wrapper["row"]
            turn_value = required_cell(row, fields["turn_index"], "message turn index", wrapper["source_row"])
            require(isinstance(turn_value, int) and not isinstance(turn_value, bool), "KODIS message turn index must be an integer")
            raw_role = str(required_cell(row, fields["speaker_role"], "speaker role", wrapper["source_row"]))
            require(raw_role in role_map, "KODIS message has an unmapped speaker role")
            text_raw = str(required_cell(row, fields["text"], "message text", wrapper["source_row"]))
            speaker_raw = str(required_cell(row, fields["speaker_id"], "speaker identifier", wrapper["source_row"]))
            record_raw = str(required_cell(row, fields["record_id"], "record identifier", wrapper["source_row"]))
            reply_value = row.get(fields["reply_to"]) if fields["reply_to"] is not None else None
            masked_text, masks = privacy_mask(text_raw)
            require(masked_text, "KODIS message became empty after normalization")
            mask_counts.update(masks)
            prepared.append(
                {
                    **wrapper,
                    "turn_index": turn_value,
                    "role": role_map[raw_role],
                    "text_raw": text_raw,
                    "text": masked_text,
                    "speaker_raw": speaker_raw,
                    "record_raw": record_raw,
                    "reply_raw": None if reply_value is None or str(reply_value).strip() == "" else str(reply_value),
                    "masks": masks,
                }
            )
        prepared.sort(key=lambda item: item["turn_index"])
        require([item["turn_index"] for item in prepared] == list(range(1, len(prepared) + 1)), "KODIS complete dialogue message turns must be consecutive from one")
        require(len(prepared) >= rules["minimum_message_turns"], "KODIS complete dialogue has fewer than eight verified messages")
        roles = [item["role"] for item in prepared]
        require(set(roles) == {"buyer", "seller"}, "KODIS complete dialogue is not dyadic buyer/seller")
        require(roles[0] == "buyer", "KODIS human-human dialogue does not begin with buyer")
        require(all(role != roles[index - 1] for index, role in enumerate(roles[1:], start=1)), "KODIS human-human dialogue roles do not alternate")
        record_keys = [item["record_raw"] for item in prepared]
        require(len(record_keys) == len(set(record_keys)), "Duplicate KODIS record identifier within dialogue")
        fingerprint_value = "\x1e".join(f"{item['role']}\x1f{normalize_text(item['text_raw'])}" for item in prepared)
        fingerprint = stable_hmac(secret, "kodis:dialogue-text", fingerprint_value)
        require(fingerprint not in dialogue_fingerprints, "Exact duplicate complete KODIS dialogue detected")
        dialogue_fingerprints[fingerprint] = source_raw
        internal_dialogues.append({"source_raw": source_raw, "messages": prepared})

    require(internal_dialogues, "No complete human-human KODIS dialogues remained after filtering")
    source_speakers: dict[str, set[str]] = defaultdict(set)
    for dialogue in internal_dialogues:
        source_id = pseudonym(secret, "source", dialogue["source_raw"])
        dialogue["source_id"] = source_id
        for item in dialogue["messages"]:
            speaker_id = pseudonym(secret, "speaker", item["speaker_raw"])
            item["speaker_id"] = speaker_id
            source_speakers[source_id].add(speaker_id)
    components = linkage_components(source_speakers, secret)
    source_to_component = {
        source_id: component["component_id"]
        for component in components
        for source_id in component["source_ids"]
    }
    if split_manifest is None:
        assignments = {component["component_id"]: "unassigned_pending_preregistration" for component in components}
    else:
        assignments = validate_split_manifest(split_manifest, {item["component_id"] for item in components}, demo)

    model_authorized = source_manifest["model_or_rater_processing_status"] == "documented_approved_restricted"
    records: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    for dialogue in sorted(internal_dialogues, key=lambda value: value["source_id"]):
        source_id = dialogue["source_id"]
        component_id = source_to_component[source_id]
        split = assignments[component_id]
        raw_to_record = {
            item["record_raw"]: pseudonym(secret, "record", f"{dialogue['source_raw']}\x00{item['record_raw']}")
            for item in dialogue["messages"]
        }
        preceding: deque[str] = deque(maxlen=adapter["context_turns"])
        seen_raw: set[str] = set()
        for item in dialogue["messages"]:
            record_id = raw_to_record[item["record_raw"]]
            require(record_id not in record_ids, "Duplicate KODIS pseudonymous record ID")
            record_ids.add(record_id)
            reply_id = None
            if item["reply_raw"] is not None:
                require(item["reply_raw"] in raw_to_record, "KODIS reply points outside the retained dialogue")
                require(item["reply_raw"] in seen_raw, "KODIS reply points forward")
                reply_id = raw_to_record[item["reply_raw"]]
            reasons = ["manual_privacy_review_pending"]
            if split == "unassigned_pending_preregistration":
                reasons.append("split_pending_preregistration")
            if not model_authorized:
                reasons.append("model_or_rater_processing_not_authorized")
            record = {
                "record_id": record_id,
                "corpus": "kodis",
                "split": split,
                "source_id": source_id,
                "speaker_id": item["speaker_id"],
                "text": item["text"],
                "context": {
                    "preceding_record_ids": list(preceding),
                    "moderator_question": None,
                    "reply_to_record_id": reply_id,
                    "turn_index": item["turn_index"],
                },
                "sampling_strata": {"speaker_role": item["role"]},
                "provenance": {
                    "source_file_role": "human_human_dialogue_turns",
                    "source_file_id": item["source_file_id"],
                    "source_row": item["source_row"],
                    "source_turn_index": item["turn_index"],
                    "source_text_hmac_sha256": stable_hmac(secret, "kodis:text", normalize_text(item["text_raw"])),
                    "linkage_group_id": component_id,
                },
                "quality": {
                    "eligible_for_packet_sampling": False,
                    "ineligible_reasons": sorted(reasons),
                    "privacy_masks_applied": item["masks"],
                    "manual_excerpt_review_required": True,
                    "privacy_review_status": "pending",
                },
            }
            require(set(record) == RECORD_KEYS, "Internal KODIS record shape changed")
            require(not list(iter_forbidden_keys(record)), "Forbidden metadata or raw-ID field reached KODIS output")
            records.append(record)
            preceding.append(record_id)
            seen_raw.add(item["record_raw"])

    counts_by_source = Counter(record["source_id"] for record in records)
    groups = []
    for component in components:
        group = {
            **component,
            "record_count": sum(counts_by_source[source_id] for source_id in component["source_ids"]),
            "split": assignments[component["component_id"]],
        }
        require(set(group) == LINKAGE_GROUP_KEYS, "Internal KODIS linkage-group shape changed")
        groups.append(group)
    diagnostics = {
        "input_rows": total_rows,
        "input_sources": len(rows_by_source),
        "filtered_non_human_rows": filtered_non_human_rows,
        "filtered_non_human_sources": filtered_non_human_sources,
        "filtered_incomplete_rows": filtered_incomplete_rows,
        "filtered_incomplete_sources": filtered_incomplete_sources,
        "filtered_nonmessage_rows": filtered_nonmessage_rows,
        "privacy_mask_counts": dict(sorted(mask_counts.items())),
        "exact_duplicate_dialogues": 0,
    }
    return records, groups, diagnostics


def enforce_demo_controls(args: argparse.Namespace) -> None:
    require_exact_path(args.input_root, KODIS_DEMO_INPUT_ROOT, "Demo KODIS input root")
    require_exact_path(args.adapter, DEMO_ADAPTER_PATH, "Demo KODIS adapter")
    require_exact_path(args.source_manifest, DEMO_SOURCE_MANIFEST_PATH, "Demo KODIS source manifest")
    require(args.split_manifest is not None, "Demo KODIS build requires its synthetic split manifest")
    require_exact_path(args.split_manifest, DEMO_SPLIT_MANIFEST_PATH, "Demo KODIS split manifest")
    output = args.output.resolve()
    allowed_test = is_within(output, KODIS_TEST_OUTPUT_ROOT)
    require(output == KODIS_DEMO_OUTPUT.resolve() or allowed_test, "Demo KODIS output must remain in the dedicated synthetic output area")


def enforce_real_controls(args: argparse.Namespace) -> None:
    require_exact_path(args.input_root, KODIS_RAW_ROOT, "Real KODIS input root")
    require_exact_path(args.adapter, KODIS_RAW_ROOT / REAL_ADAPTER_NAME, "Real KODIS adapter")
    require_exact_path(args.source_manifest, KODIS_RAW_ROOT / REAL_SOURCE_MANIFEST_NAME, "Real KODIS source manifest")
    if args.split_manifest is not None:
        require_exact_path(args.split_manifest, KODIS_RAW_ROOT / REAL_SPLIT_MANIFEST_NAME, "Real KODIS split manifest")
    require_exact_path(args.output, KODIS_OUTPUT_ROOT, "Real KODIS output")
    require_private_mode(args.input_root, "KODIS input root")
    require_private_mode(args.adapter, "KODIS adapter")
    require_private_mode(args.source_manifest, "KODIS source manifest")
    if args.split_manifest is not None:
        require_private_mode(args.split_manifest, "KODIS split manifest")


def run_inspect(args: argparse.Namespace) -> dict[str, Any]:
    require_exact_path(args.input_root, KODIS_RAW_ROOT, "KODIS inspection input root")
    require_exact_path(args.output, KODIS_RAW_ROOT / REAL_SOURCE_MANIFEST_NAME, "KODIS inspection receipt")
    snapshots = inventory_snapshots(args.input_root.resolve(), private=True)
    require(snapshots, "No authorized KODIS package files found; refusing to infer or reconstruct the corpus")
    manifest = {
        "manifest_version": "1.0",
        "corpus": "kodis",
        "status": "inventory_pending_authorization_review",
        "created_by": "prepare_kodis.py inspect",
        "access_method": "request_only_pending_verification",
        "authorization_reference": None,
        "agreement_version": None,
        "agreement_accepted_date": None,
        "receipt_date": None,
        "package_version": None,
        "approved_users_or_team": None,
        "noncommercial_research_only_acknowledged": False,
        "redistribution_restrictions_reviewed": False,
        "identity_protection_requirements_reviewed": False,
        "local_preprocessing_authorized": False,
        "local_preprocessing_ethics_status": "pending_institutional_determination",
        "model_or_rater_processing_status": "pending_separate_written_confirmation",
        "manual_privacy_review_plan_status": "pending",
        "file_inventory": [inventory_entry(snapshot) for snapshot in snapshots],
    }
    atomic_write(args.output.resolve(), json_bytes(manifest), args.replace)
    summary = {
        "status": "inventory_created_pending_authorization_review",
        "corpus": "kodis",
        "files": len(snapshots),
        "parseable_tabular_files": sum(item.input_format in {"jsonl", "csv"} for item in snapshots),
        "rows_in_parseable_files": sum(len(item.rows) for item in snapshots),
        "warning": "No KODIS field mapping, authorization, split, privacy clearance, or experimental result is implied.",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def run_build(args: argparse.Namespace) -> dict[str, Any]:
    if args.demo:
        enforce_demo_controls(args)
    else:
        enforce_real_controls(args)
    secret = load_secret(args.secret_file, args.demo)
    input_root = args.input_root.resolve()
    snapshots = inventory_snapshots(input_root, private=not args.demo)
    require(snapshots, "No authorized KODIS package files found")
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
        require(len(snapshots) == 1 and snapshots[0].relative_path == KODIS_DEMO_INPUT.name, "Demo KODIS package inventory changed")
        require(snapshots[0].sha256 == DEMO_INPUT_SHA256, "Demo KODIS input checksum changed")
    entries = validate_source_manifest(source_manifest, snapshots, args.demo)
    selected_paths = {entry["path"] for entry in entries if entry["selected_for_transcript_processing"]}
    selected = [snapshot for snapshot in snapshots if snapshot.relative_path in selected_paths]
    require(selected, "KODIS source receipt selects no transcript files")
    validate_adapter(adapter, selected, entries, args.demo)
    records, groups, diagnostics = build_records(selected, adapter, source_manifest, split_manifest, secret, args.demo)
    pipeline_path = Path(__file__).resolve()
    pipeline_digest = file_digest(pipeline_path)
    split_counts = dict(sorted(Counter(record["split"] for record in records).items()))
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_file": pipeline_path.name,
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
        "selected_input_files": len(selected),
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
        "split_manifest_applied": split_manifest is not None,
        "split_counts": split_counts,
        "eligible_for_packet_sampling": 0,
        "privacy_review_pending": len(records),
        "privacy_mask_counts": diagnostics["privacy_mask_counts"],
        "data_minimization": {
            "raw_ids_written": False,
            "demographics_written": False,
            "surveys_written": False,
            "preference_justifications_written": False,
            "compensation_written": False,
            "precise_timestamps_written": False,
            "model_emotion_labels_written": False,
            "human_ai_text_written": False,
            "nonmessage_event_text_written": False,
        },
        "warning": "Processed KODIS text is restricted and pseudonymized, not anonymous; every excerpt remains ineligible pending documented human privacy review.",
    }
    require(set(report) == BUILD_REPORT_KEYS, "Internal KODIS build-report shape changed")
    for snapshot in snapshots:
        require_unchanged(snapshot.path, snapshot.sha256, "KODIS package file")
    require_unchanged(args.adapter, adapter_digest, "KODIS adapter")
    require_unchanged(args.source_manifest, source_manifest_digest, "KODIS source manifest")
    if args.split_manifest is not None and split_manifest_digest is not None:
        require_unchanged(args.split_manifest, split_manifest_digest, "KODIS split manifest")
    require_unchanged(pipeline_path, pipeline_digest, "KODIS pipeline")

    output = args.output.resolve()
    ensure_private_directory(output)
    require_clean_output_directory(output)
    paths_and_content = {
        output / "records.jsonl": jsonl_bytes(records),
        output / "linkage_groups.jsonl": jsonl_bytes(groups),
        output / "build_report.json": json_bytes(report),
    }
    validation_report_path = output / "validation_report.json"
    if not args.replace:
        require(not any(path.exists() for path in paths_and_content), "Refusing partial replacement of existing KODIS outputs")
        require(not validation_report_path.exists(), "Refusing a new KODIS build beside a stale validation report")
    elif validation_report_path.exists():
        invalidation = {
            "status": "invalidated_by_rebuild",
            "corpus": "kodis",
            "warning": "Run validate_kodis.py before relying on this rebuilt bundle.",
        }
        atomic_write(validation_report_path, json_bytes(invalidation), replace=True)
    for path, content in paths_and_content.items():
        atomic_write(path, content, args.replace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    args = parse_args()
    try:
        if args.command == "inspect":
            run_inspect(args)
        else:
            run_build(args)
    except (AssertionError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as exc:
        if isinstance(exc, OSError):
            print("KODIS preprocessing blocked: restricted file operation failed", file=sys.stderr)
        else:
            print(f"KODIS preprocessing blocked: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
