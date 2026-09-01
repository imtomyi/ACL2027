#!/usr/bin/env python3
"""Stage authorized CANDOR Cliffhanger transcripts as restricted records.

This CANDOR-only wrapper is deliberately fail closed. It discovers only the
original BetterUp per-conversation ``transcription/transcript_cliffhanger.csv``
files, verifies an access/source manifest and an explicitly inspected adapter,
retains an allowlisted transcript subset, uses keyed HMAC pseudonyms, and keeps
every record ineligible until documented human privacy review.

It does not download CANDOR, accept media, infer a schema for an unseen release,
or claim that pattern masking makes conversational text anonymous.
"""

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


PIPELINE_VERSION = "candor-cliffhanger-1.0"
PREFERRED_FILENAME = "transcript_cliffhanger.csv"
INPUT_ROUTE = "original_betterup_per_conversation_cliffhanger_csv"
TRANSCRIPTION_ALGORITHM = "Cliffhanger"
UNASSIGNED_SPLIT = "unassigned_pending_preregistration"

DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DATASET_ROOT.parent
CANDOR_RAW_ROOT = DATASET_ROOT / "raw" / "candor"
CANDOR_OUTPUT_ROOT = DATASET_ROOT / "deidentified" / "candor"
CANDOR_FIXTURE_ROOT = DATASET_ROOT / "fixtures" / "candor_synthetic"
CANDOR_DEMO_INPUT_ROOT = CANDOR_FIXTURE_ROOT / "package"
CANDOR_DEMO_OUTPUT = PROJECT_ROOT / "Storage" / "synthetic-results" / "dataset-demos" / "candor_demo_output"

DEMO_ADAPTER_PATH = DATASET_ROOT / "manifests" / "candor_demo_adapter.json"
DEMO_SOURCE_MANIFEST_PATH = DATASET_ROOT / "manifests" / "candor_demo_source_manifest.json"
DEMO_SPLIT_MANIFEST_PATH = DATASET_ROOT / "manifests" / "candor_demo_split_manifest.json"
DEMO_ADAPTER_SHA256 = "b852b3f85528f2a5b7d51f124827d979b3a9d0a567a72fd12ea0ae475d330965"
DEMO_SOURCE_MANIFEST_SHA256 = "bf273b14869f04a1a0d3fe4760b055d4dfc69ac5b7656dd1418bbe19bc17559a"
DEMO_SPLIT_MANIFEST_SHA256 = "f56d4010df67992ed151bc2ee20f25e421690e2fc41f1126acfab591f3d483d1"

REAL_ADAPTER_NAME = "candor_adapter.local.json"
REAL_SOURCE_MANIFEST_NAME = "candor_source_manifest.local.json"
REAL_SPLIT_MANIFEST_NAME = "candor_splits.local.json"
OUTPUT_BUNDLE_NAMES = {
    "records.jsonl",
    "linkage_groups.jsonl",
    "build_report.json",
    "validation_report.json",
}

ADAPTER_KEYS = {
    "adapter_version",
    "corpus",
    "verification_status",
    "input_format",
    "input_route",
    "preferred_filename",
    "transcription_algorithm",
    "row_order_is_turn_order",
    "turn_index_policy",
    "speaker_identity_scope",
    "speaker_ids_are_person_stable_across_conversations",
    "context_turns",
    "fields",
    "verified_input_headers",
    "discarded_input_fields",
    "sampling_strata",
    "verification_notes",
}
SOURCE_MANIFEST_KEYS = {
    "manifest_version",
    "corpus",
    "package_status",
    "synthetic_fixture",
    "input_route",
    "transcription_algorithm",
    "transcript_only_processing_approved",
    "terms_review_status",
    "pii_handling_status",
    "access_approval_reference",
    "acquisition_date",
    "package_version",
    "manual_privacy_review_plan_status",
    "redistribution_status",
    "files",
    "observed_release_counts",
    "unverified_input_assumptions",
    "warning",
}
SOURCE_FILE_KEYS = {
    "file_label",
    "basename",
    "sha256",
    "size_bytes",
    "row_count",
    "headers",
}
OBSERVED_SOURCE_COUNT_KEYS = {"transcript_files", "transcript_rows"}
SPLIT_MANIFEST_KEYS = {
    "manifest_version",
    "corpus",
    "status",
    "assignment_unit",
    "assignments",
    "warning",
}
BUILD_REPORT_KEYS = {
    "pipeline_version",
    "pipeline_file",
    "pipeline_sha256",
    "corpus",
    "data_status",
    "input_route",
    "transcription_algorithm",
    "demo_mode",
    "adapter_file",
    "adapter_sha256",
    "source_manifest_file",
    "source_manifest_sha256",
    "split_manifest_file",
    "split_manifest_sha256",
    "split_manifest_applied",
    "preregistered_split_assignment_present",
    "synthetic_split_fixture_applied",
    "context_turns",
    "observed_release_counts",
    "records_written",
    "sources",
    "speakers",
    "linkage_components",
    "split_counts",
    "eligible_for_packet_sampling",
    "privacy_review_pending",
    "manual_privacy_review_required_for_all_records",
    "privacy_mask_counts",
    "unresolved_reply_references",
    "data_minimization",
    "automatic_masking_limitations",
    "warning",
}
BUILD_OBSERVED_COUNT_KEYS = {
    "transcript_files",
    "transcript_rows",
    "conversations",
    "speakers",
    "conversation_speaker_connected_components",
}
DATA_MINIMIZATION_KEYS = {
    "source_identifier_fields_written",
    "demographic_metadata_fields_written",
    "survey_fields_written",
    "audio_fields_written",
    "video_fields_written",
    "precise_timestamp_metadata_fields_written",
    "metadata_sampling_strata_written",
}

REAL_ADAPTER_NOTE = (
    "Verified against the authorized package; this adapter records field names only and no "
    "source values."
)
DEMO_ADAPTER_NOTE = (
    "Fictional fixture contract only; it is not evidence about an authorized CANDOR package."
)
REAL_SOURCE_WARNING = (
    "Restricted local receipt only; no source text, raw paths, or participant values are recorded."
)
DEMO_SOURCE_WARNING = (
    "This receipt describes fictional test data only and is not evidence about the real CANDOR corpus."
)
REAL_SPLIT_WARNING = (
    "Preregistered component assignments only; this manifest contains pseudonymous component IDs "
    "and split labels."
)
DEMO_SPLIT_WARNING = (
    "Synthetic split fixture only. These labels and proportions are not an experimental split "
    "decision for the real CANDOR corpus."
)
AUTOMATIC_MASKING_LIMITATIONS = [
    "Names, places, employers, schools, and street addresses are not reliably detected.",
    "Demographic facts and precise times stated inside transcript text are not reliably detected.",
    "Quasi-identifying biographies and searchable phrasing are not reliably detected.",
    "Pattern masking does not replace manual contextual privacy review.",
]
BUILD_WARNING = (
    "Output is restricted and pseudonymized, not anonymous. Every excerpt remains ineligible "
    "pending documented human privacy review and permissions clearance."
)

DEMO_SECRET = b"WarrantRoute CANDOR synthetic fixture secret only"
PSEUDONYM_RE = re.compile(r"^candor_(?:source|speaker|record|linkage)_[a-f0-9]{16}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
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

FORBIDDEN_OUTPUT_KEYS = {
    "address",
    "age",
    "audio",
    "audio_path",
    "country",
    "culture_cluster",
    "demographics",
    "education",
    "email",
    "employment",
    "employer",
    "end_time",
    "gender",
    "ip_address",
    "location",
    "name",
    "participant_id",
    "phone",
    "politics",
    "race",
    "raw_conversation_id",
    "school",
    "sex",
    "speaker_demographics",
    "start_time",
    "survey",
    "survey_responses",
    "timestamp",
    "timestamps",
    "video",
    "video_path",
    "worker_id",
}


@dataclass(frozen=True)
class TranscriptInventory:
    path: Path
    content: bytes = field(repr=False)
    file_label: str
    basename: str
    sha256: str
    size_bytes: int
    row_count: int
    headers: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        """Return receipt information without a raw conversation path."""
        return {
            "file_label": self.file_label,
            "basename": self.basename,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "row_count": self.row_count,
            "headers": list(self.headers),
        }


class DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, value: str) -> None:
        self.parent.setdefault(value, value)

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            if left_root < right_root:
                self.parent[right_root] = left_root
            else:
                self.parent[left_root] = right_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or stage authorized CANDOR Cliffhanger transcript CSVs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Create a text-free draft receipt from exact Cliffhanger CSV files.",
    )
    inspect_parser.add_argument("--input-root", type=Path, required=True)
    inspect_parser.add_argument("--output", type=Path, required=True)
    inspect_parser.add_argument("--replace", action="store_true")

    build_parser = subparsers.add_parser(
        "build",
        help="Build restricted pseudonymized records after manifest verification.",
    )
    build_parser.add_argument("--input-root", type=Path, required=True)
    build_parser.add_argument("--adapter", type=Path, required=True)
    build_parser.add_argument("--source-manifest", type=Path, required=True)
    build_parser.add_argument("--split-manifest", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--secret-file", type=Path)
    build_parser.add_argument(
        "--demo",
        action="store_true",
        help="Use the public secret, only with dataset/fixtures/candor_synthetic/.",
    )
    build_parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"Expected a JSON object in {path.name}")
    return value


def load_json_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_bytes()
    value = json.loads(content.decode("utf-8"))
    require(isinstance(value, dict), f"Expected a JSON object in {path.name}")
    return value, hashlib.sha256(content).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_unchanged(path: Path, expected_digest: str, label: str) -> None:
    require(file_digest(path) == expected_digest, f"{label} changed during CANDOR processing")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def jsonl_bytes(values: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        for value in values
    )


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def require_clean_output_directory(path: Path) -> None:
    for entry in path.iterdir():
        require(not entry.is_symlink(), "CANDOR output cannot contain symlinks")
        require(entry.is_file(), "CANDOR output cannot contain subdirectories")
        require(entry.name in OUTPUT_BUNDLE_NAMES, "Unexpected file in CANDOR output bundle")


def require_private_mode(path: Path, label: str) -> None:
    require(path.exists(), f"Missing {label}")
    require(
        path.stat().st_mode & 0o077 == 0,
        f"{label} permits group/other access; restrict it before CANDOR processing",
    )


def atomic_write(path: Path, content: bytes, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(f"Refusing to replace {path}; add --replace after review")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def enforce_path_policy(input_root: Path, output: Path | None, demo: bool) -> None:
    if demo:
        require(
            input_root.resolve() == CANDOR_DEMO_INPUT_ROOT.resolve(),
            "--demo is restricted to the shipped CANDOR synthetic package",
        )
        if output is not None:
            output_resolved = output.resolve()
            allowed_canonical = output_resolved == CANDOR_DEMO_OUTPUT.resolve()
            allowed_test = is_within(output_resolved, CANDOR_FIXTURE_ROOT) and not is_within(
                output_resolved, CANDOR_DEMO_INPUT_ROOT
            )
            require(
                allowed_canonical or allowed_test,
                "Demo output must remain in the dedicated CANDOR fixture area",
            )
        return
    require(
        is_within(input_root, CANDOR_RAW_ROOT),
        "Real CANDOR input must remain under dataset/raw/candor",
    )
    if output is not None:
        require(
            is_within(output, CANDOR_OUTPUT_ROOT),
            "Real CANDOR records must remain under dataset/deidentified/candor",
        )


def enforce_control_path(path: Path, expected_name: str, demo_path: Path | None) -> None:
    if demo_path is not None:
        require(path.resolve() == demo_path.resolve(), "Demo control file is not the shipped fixture")
        return
    require(
        path.resolve().parent == CANDOR_RAW_ROOT.resolve() and path.name == expected_name,
        f"Real {expected_name} must use the fixed name in dataset/raw/candor",
    )


def discover_transcripts(input_root: Path) -> list[Path]:
    root = input_root.resolve()
    require(root.is_dir(), "CANDOR input root is not a directory")
    candidates: list[Path] = []
    for path in root.rglob(PREFERRED_FILENAME):
        require(not path.is_symlink(), "Refusing a symlinked CANDOR transcript input")
        resolved = path.resolve()
        require(is_within(resolved, root), "CANDOR transcript escapes the input root")
        if resolved.is_file() and resolved.parent.name == "transcription":
            candidates.append(resolved)
    require(
        candidates,
        "No authorized BetterUp */transcription/transcript_cliffhanger.csv files found; "
        "refusing to substitute TalkBank ASR, media, or a derived dump",
    )
    return sorted(candidates, key=lambda path: path.relative_to(root).as_posix())


def csv_headers_and_rows(content: bytes) -> tuple[tuple[str, ...], int]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    require(reader.fieldnames is not None, f"Missing CSV header in {PREFERRED_FILENAME}")
    headers = tuple(header.strip() for header in reader.fieldnames)
    require(all(headers), f"Blank CSV header in {PREFERRED_FILENAME}")
    require(len(headers) == len(set(headers)), f"Duplicate CSV header in {PREFERRED_FILENAME}")
    row_count = sum(1 for _ in reader)
    require(row_count > 0, f"No transcript rows in {PREFERRED_FILENAME}")
    return headers, row_count


def inventory_transcripts(input_root: Path) -> list[TranscriptInventory]:
    internal: list[tuple[Path, bytes, str, int, int, tuple[str, ...]]] = []
    for path in discover_transcripts(input_root):
        content = path.read_bytes()
        headers, row_count = csv_headers_and_rows(content)
        internal.append(
            (path, content, hashlib.sha256(content).hexdigest(), len(content), row_count, headers)
        )
    internal.sort(key=lambda item: (item[2], item[3], item[0].as_posix()))
    digests = [item[2] for item in internal]
    require(len(digests) == len(set(digests)), "Duplicate transcript-file content detected")
    return [
        TranscriptInventory(
            path=path,
            content=content,
            file_label=f"candor_transcript_{index:06d}",
            basename=PREFERRED_FILENAME,
            sha256=digest,
            size_bytes=size_bytes,
            row_count=row_count,
            headers=headers,
        )
        for index, (path, content, digest, size_bytes, row_count, headers) in enumerate(
            internal, start=1
        )
    ]


def inspection_manifest(inventory: list[TranscriptInventory]) -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "corpus": "candor",
        "package_status": "inspection_only_pending_authorization_confirmation",
        "synthetic_fixture": False,
        "input_route": INPUT_ROUTE,
        "transcription_algorithm": TRANSCRIPTION_ALGORITHM,
        "transcript_only_processing_approved": False,
        "terms_review_status": "pending",
        "pii_handling_status": "pending",
        "access_approval_reference": None,
        "acquisition_date": None,
        "package_version": None,
        "manual_privacy_review_plan_status": "pending",
        "redistribution_status": "not_cleared",
        "files": [item.public_dict() for item in inventory],
        "observed_release_counts": {
            "transcript_files": len(inventory),
            "transcript_rows": sum(item.row_count for item in inventory),
        },
        "unverified_input_assumptions": [
            "CSV text and speaker columns have not been mapped.",
            "CSV row order has not been confirmed as Cliffhanger turn order.",
            "Speaker keys have not been confirmed as person-stable across conversations.",
            "Package version, access scope, and PII-handling terms require manual confirmation.",
        ],
        "warning": (
            "This is a text-free file inventory, not a completed CANDOR build or privacy review."
        ),
    }


def validate_source_manifest(
    manifest: dict[str, Any], inventory: list[TranscriptInventory], demo: bool
) -> None:
    require(set(manifest) == SOURCE_MANIFEST_KEYS, "Unexpected source-manifest fields")
    require(manifest.get("manifest_version") == "1.0", "Unsupported source-manifest version")
    require(manifest.get("corpus") == "candor", "Source-manifest corpus mismatch")
    require(manifest.get("input_route") == INPUT_ROUTE, "Nonpreferred input route")
    require(
        manifest.get("transcription_algorithm") == TRANSCRIPTION_ALGORITHM,
        "Source manifest must assert the Cliffhanger transcription algorithm",
    )
    if demo:
        require(manifest.get("package_status") == "synthetic_fixture", "Invalid demo manifest")
        require(manifest.get("synthetic_fixture") is True, "Demo manifest lacks fixture marker")
        require(manifest.get("unverified_input_assumptions") == [], "Demo receipt has assumptions")
        require(manifest.get("warning") == DEMO_SOURCE_WARNING, "Demo receipt warning changed")
    else:
        require(
            manifest.get("package_status") == "authorized_for_restricted_processing",
            "Authorized-package status is not approved",
        )
        require(
            manifest.get("transcript_only_processing_approved") is True,
            "Transcript-only processing approval is missing",
        )
        require(
            manifest.get("terms_review_status") == "approved_for_this_processing",
            "Provider/TalkBank terms review is incomplete",
        )
        require(
            manifest.get("pii_handling_status") == "approved_restricted_controls",
            "PII-handling controls are not approved",
        )
        require(
            isinstance(manifest.get("access_approval_reference"), str)
            and bool(manifest["access_approval_reference"].strip()),
            "Access approval reference is missing",
        )
        require(
            isinstance(manifest.get("acquisition_date"), str)
            and bool(manifest["acquisition_date"].strip()),
            "Acquisition date is missing",
        )
        require(
            isinstance(manifest.get("package_version"), str)
            and bool(manifest["package_version"].strip()),
            "Received package version is missing",
        )
        require(
            manifest.get("manual_privacy_review_plan_status") == "documented",
            "Manual privacy-review plan is not documented",
        )
        require(
            manifest.get("redistribution_status") == "not_cleared",
            "CANDOR redistribution must remain not cleared at staging",
        )
        require(manifest.get("synthetic_fixture") is False, "Real receipt is marked synthetic")
        require(
            manifest.get("unverified_input_assumptions") == [],
            "Real input assumptions remain unresolved",
        )
        require(manifest.get("warning") == REAL_SOURCE_WARNING, "Source receipt warning changed")

    manifest_files = manifest.get("files")
    require(isinstance(manifest_files, list) and manifest_files, "Source file inventory is empty")
    for entry in manifest_files:
        require(isinstance(entry, dict), "Invalid source file receipt")
        require(set(entry) == SOURCE_FILE_KEYS, "Unexpected source file receipt fields")
        require(entry.get("basename") == PREFERRED_FILENAME, "Unexpected transcript filename")
        require(bool(SHA256_RE.fullmatch(str(entry.get("sha256", "")))), "Invalid file SHA-256")

    expected_files = [item.public_dict() for item in inventory]
    require(manifest_files == expected_files, "Source receipt does not match observed transcript files")
    counts = manifest.get("observed_release_counts")
    require(
        isinstance(counts, dict) and set(counts) == OBSERVED_SOURCE_COUNT_KEYS,
        "Invalid observed release counts",
    )
    require(counts.get("transcript_files") == len(inventory), "Transcript-file count mismatch")
    require(
        counts.get("transcript_rows") == sum(item.row_count for item in inventory),
        "Transcript-row count mismatch",
    )


def validate_adapter(
    adapter: dict[str, Any], inventory: list[TranscriptInventory], demo: bool
) -> dict[str, str | None]:
    require(set(adapter) == ADAPTER_KEYS, "Unexpected adapter fields")
    require(adapter.get("adapter_version") == "1.0", "Unsupported adapter version")
    require(adapter.get("corpus") == "candor", "Adapter corpus mismatch")
    require(adapter.get("input_format") == "csv", "CANDOR Cliffhanger adapter must use CSV")
    require(adapter.get("input_route") == INPUT_ROUTE, "Adapter input route mismatch")
    require(
        adapter.get("preferred_filename") == PREFERRED_FILENAME,
        "Adapter must prefer transcript_cliffhanger.csv",
    )
    require(
        adapter.get("transcription_algorithm") == TRANSCRIPTION_ALGORITHM,
        "Adapter must assert the Cliffhanger transcription algorithm",
    )
    if demo:
        require(
            adapter.get("verification_status") == "synthetic_fixture_verified",
            "Demo adapter is not fixture-verified",
        )
        require(adapter.get("verification_notes") == DEMO_ADAPTER_NOTE, "Demo adapter note changed")
    else:
        require(
            adapter.get("verification_status") == "verified_against_authorized_package",
            "Real adapter mapping remains unverified",
        )
        require(adapter.get("verification_notes") == REAL_ADAPTER_NOTE, "Real adapter note changed")
    require(
        adapter.get("row_order_is_turn_order") is True,
        "CSV row order must be manually verified as turn order",
    )
    require(
        adapter.get("turn_index_policy") == "derived_ordinal_from_verified_row_order",
        "Turn indices must be derived ordinals, never timestamps",
    )
    require(
        adapter.get("speaker_identity_scope") == "global_person_stable",
        "A verified person-stable speaker key is required for linked-speaker splits",
    )
    require(
        adapter.get("speaker_ids_are_person_stable_across_conversations") is True,
        "Cross-conversation speaker stability is not verified",
    )
    context_turns = adapter.get("context_turns")
    require(
        isinstance(context_turns, int)
        and not isinstance(context_turns, bool)
        and 0 <= context_turns <= 20,
        "Invalid context_turns",
    )

    fields = adapter.get("fields")
    require(isinstance(fields, dict), "Missing adapter field mapping")
    require(set(fields) == {"speaker_id", "text", "record_id", "reply_to"}, "Unexpected field roles")
    require(isinstance(fields.get("speaker_id"), str), "Speaker field is not mapped")
    require(isinstance(fields.get("text"), str), "Text field is not mapped")
    for optional in ("record_id", "reply_to"):
        require(
            fields.get(optional) is None or isinstance(fields.get(optional), str),
            f"Invalid optional mapping for {optional}",
        )
    require(
        fields.get("reply_to") is None or fields.get("record_id") is not None,
        "reply_to requires a record_id mapping",
    )
    mapped_role_fields = [value for value in fields.values() if value is not None]
    require(
        len(mapped_role_fields) == len(set(mapped_role_fields)),
        "Adapter field roles must map to distinct CSV columns",
    )

    verified_headers = adapter.get("verified_input_headers")
    require(
        isinstance(verified_headers, list)
        and verified_headers
        and all(isinstance(value, str) for value in verified_headers),
        "Verified input headers are missing",
    )
    require(len(verified_headers) == len(set(verified_headers)), "Duplicate verified header")
    for item in inventory:
        require(list(item.headers) == verified_headers, "Transcript header differs from verified adapter")
    for source_field in fields.values():
        if source_field is not None:
            require(source_field in verified_headers, f"Mapped field {source_field!r} is absent")

    mapped_fields = {value for value in fields.values() if value is not None}
    discarded_fields = adapter.get("discarded_input_fields")
    require(isinstance(discarded_fields, list), "discarded_input_fields must be a list")
    require(
        set(discarded_fields) == set(verified_headers) - mapped_fields,
        "Every nonretained CSV column must be explicitly listed as discarded",
    )
    require(adapter.get("sampling_strata") == {}, "CANDOR staging cannot retain metadata strata")
    return fields


def load_secret(secret_file: Path | None, demo: bool) -> bytes:
    if demo:
        require(secret_file is None, "--demo cannot accept a real secret file")
        return DEMO_SECRET
    if secret_file is not None:
        require(secret_file.is_file(), "CANDOR secret file not found")
        require_private_mode(secret_file, "CANDOR secret file")
        secret = secret_file.read_bytes().strip()
    else:
        secret = os.environ.get("WARRANTROUTE_CANDOR_PSEUDONYM_KEY", "").encode("utf-8")
    require(
        len(secret) >= 32,
        "Real processing requires a stable secret of at least 32 bytes via --secret-file "
        "or WARRANTROUTE_CANDOR_PSEUDONYM_KEY",
    )
    return secret


def stable_hmac(secret: bytes, namespace: str, value: str) -> str:
    message = f"{namespace}\x00{value}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def pseudonym(secret: bytes, kind: str, value: str) -> str:
    return f"candor_{kind}_{stable_hmac(secret, f'candor:{kind}', value)[:16]}"


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).strip())


def privacy_mask(text: str) -> tuple[str, list[str]]:
    """Mask deterministic direct-identifier patterns without claiming completeness."""
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
    return masked, sorted(set(flags))


def required_cell(row: dict[str, str | None], field: str, role: str, row_number: int) -> str:
    value = row.get(field)
    require(
        isinstance(value, str) and bool(value.strip()),
        f"Transcript row {row_number} is missing required {role} field {field!r}",
    )
    return value.strip()


def read_internal_rows(
    inventory: list[TranscriptInventory],
    fields: dict[str, str | None],
    secret: bytes,
) -> list[dict[str, Any]]:
    internal: list[dict[str, Any]] = []
    for item in inventory:
        source_key = item.sha256
        source_id = pseudonym(secret, "source", source_key)
        seen_record_keys: set[str] = set()
        reader = csv.DictReader(
            io.StringIO(item.content.decode("utf-8-sig"), newline="")
        )
        for ordinal, row in enumerate(reader, start=1):
            require(None not in row, f"Transcript row {ordinal} has extra CSV columns")
            require(
                set(row) == set(item.headers) and all(value is not None for value in row.values()),
                f"Transcript row {ordinal} does not match the verified CSV width",
            )
            speaker_raw = required_cell(row, str(fields["speaker_id"]), "speaker_id", ordinal)
            text_raw = required_cell(row, str(fields["text"]), "text", ordinal)
            record_field = fields.get("record_id")
            record_raw = (
                required_cell(row, str(record_field), "record_id", ordinal)
                if record_field is not None
                else f"derived-row-{ordinal}"
            )
            require(
                record_raw not in seen_record_keys,
                f"Duplicate record key within {PREFERRED_FILENAME} at row {ordinal}",
            )
            seen_record_keys.add(record_raw)
            reply_field = fields.get("reply_to")
            reply_value = row.get(str(reply_field)) if reply_field is not None else None
            reply_raw = (
                reply_value.strip()
                if isinstance(reply_value, str) and reply_value.strip()
                else None
            )
            masked_text, masks = privacy_mask(text_raw)
            require(masked_text, f"Transcript row {ordinal} became empty after normalization")
            internal.append(
                {
                    "file_label": item.file_label,
                    "source_key": source_key,
                    "source_id": source_id,
                    "source_row": ordinal,
                    "turn_index": ordinal,
                    "record_raw": record_raw,
                    "record_id": pseudonym(secret, "record", f"{source_key}\x00{record_raw}"),
                    "speaker_id": pseudonym(secret, "speaker", speaker_raw),
                    "reply_raw": reply_raw,
                    "text": masked_text,
                    "text_hmac": stable_hmac(
                        secret, "candor:text", normalize_text(text_raw)
                    ),
                    "mask_flags": masks,
                }
            )
    require(internal, "No CANDOR records were produced")
    return internal


def build_linkage_groups(
    internal: list[dict[str, Any]], secret: bytes
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    graph = DisjointSet()
    for item in internal:
        source_node = f"source:{item['source_id']}"
        speaker_node = f"speaker:{item['speaker_id']}"
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

    source_to_component: dict[str, str] = {}
    groups: list[dict[str, Any]] = []
    for member in members.values():
        source_ids = sorted(member["source_ids"])
        speaker_ids = sorted(member["speaker_ids"])
        material = json.dumps(
            {"source_ids": source_ids, "speaker_ids": speaker_ids},
            separators=(",", ":"),
            sort_keys=True,
        )
        component_id = pseudonym(secret, "linkage", material)
        for source_id in source_ids:
            source_to_component[source_id] = component_id
        groups.append(
            {
                "component_id": component_id,
                "source_ids": source_ids,
                "speaker_ids": speaker_ids,
            }
        )
    groups.sort(key=lambda group: group["component_id"])
    return source_to_component, groups


def load_split_assignments(
    manifest: dict[str, Any] | None,
    component_ids: set[str],
    demo: bool,
) -> dict[str, str]:
    if manifest is None:
        return {component_id: UNASSIGNED_SPLIT for component_id in component_ids}
    require(set(manifest) == SPLIT_MANIFEST_KEYS, "Unexpected split-manifest fields")
    require(manifest.get("manifest_version") == "1.0", "Unsupported split-manifest version")
    require(manifest.get("corpus") == "candor", "Split-manifest corpus mismatch")
    required_status = "synthetic_demo" if demo else "preregistered"
    require(manifest.get("status") == required_status, "Split manifest is not approved")
    expected_warning = DEMO_SPLIT_WARNING if demo else REAL_SPLIT_WARNING
    require(manifest.get("warning") == expected_warning, "Split-manifest warning changed")
    require(
        manifest.get("assignment_unit") == "conversation_speaker_connected_component",
        "Splits must be assigned by connected component",
    )
    assignments = manifest.get("assignments")
    require(isinstance(assignments, dict), "Split assignments must be an object")
    require(set(assignments) == component_ids, "Split assignments must cover exact components")
    for component_id, split in assignments.items():
        require(bool(PSEUDONYM_RE.fullmatch(component_id)), "Invalid linkage component ID")
        require(isinstance(split, str) and bool(split.strip()), "Empty experimental split")
        require(split != UNASSIGNED_SPLIT, "Approved split manifest cannot leave components unassigned")
    return dict(assignments)


def iter_forbidden_keys(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            lowered = key.casefold()
            if (
                lowered in FORBIDDEN_OUTPUT_KEYS
                or lowered.startswith(("raw_", "original_"))
                or lowered.endswith("_timestamp")
            ):
                yield path
            yield from iter_forbidden_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_forbidden_keys(child, f"{prefix}[{index}]")


def prepare_records(
    internal: list[dict[str, Any]],
    source_to_component: dict[str, str],
    groups: list[dict[str, Any]],
    assignments: dict[str, str],
    context_turns: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    record_lookup = {
        (item["source_id"], item["record_raw"]): item for item in internal
    }
    require(len(record_lookup) == len(internal), "Duplicate source/record lineage key")
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in internal:
        by_source[item["source_id"]].append(item)

    records: list[dict[str, Any]] = []
    mask_counts: Counter[str] = Counter()
    record_count_by_component: Counter[str] = Counter()
    for source_id in sorted(by_source):
        items = sorted(by_source[source_id], key=lambda item: item["turn_index"])
        require(
            [item["turn_index"] for item in items] == list(range(1, len(items) + 1)),
            "Turn ordinals are not contiguous",
        )
        preceding: deque[str] = deque(maxlen=context_turns)
        for item in items:
            reply_to_record_id = None
            if item["reply_raw"] is not None:
                target = record_lookup.get((source_id, item["reply_raw"]))
                require(target is not None, "Unresolved reply reference")
                require(
                    target["turn_index"] < item["turn_index"],
                    "Reply reference must point to an earlier turn in the same conversation",
                )
                reply_to_record_id = target["record_id"]

            component_id = source_to_component[source_id]
            split = assignments[component_id]
            mask_counts.update(item["mask_flags"])
            record_count_by_component[component_id] += 1
            record = {
                "record_id": item["record_id"],
                "corpus": "candor",
                "split": split,
                "source_id": source_id,
                "speaker_id": item["speaker_id"],
                "text": item["text"],
                "context": {
                    "preceding_record_ids": list(preceding),
                    "moderator_question": None,
                    "reply_to_record_id": reply_to_record_id,
                    "turn_index": item["turn_index"],
                },
                "sampling_strata": {},
                "provenance": {
                    "source_text_hmac_sha256": item["text_hmac"],
                    "source_row": item["source_row"],
                    "source_turn_index": item["turn_index"],
                    "source_file_role": "betterup_cliffhanger_transcript_turn",
                    "linkage_group_id": component_id,
                },
                "quality": {
                    "eligible_for_packet_sampling": False,
                    "ineligible_reasons": ["manual_privacy_review_pending"],
                    "privacy_masks_applied": item["mask_flags"],
                    "manual_excerpt_review_required": True,
                    "privacy_review_status": "pending",
                },
            }
            forbidden = list(iter_forbidden_keys(record))
            require(not forbidden, f"Forbidden fields reached CANDOR output: {forbidden}")
            records.append(record)
            preceding.append(item["record_id"])

    group_records: list[dict[str, Any]] = []
    for group in groups:
        component_id = group["component_id"]
        group_records.append(
            {
                **group,
                "split": assignments[component_id],
                "source_count": len(group["source_ids"]),
                "speaker_count": len(group["speaker_ids"]),
                "record_count": record_count_by_component[component_id],
            }
        )
    return records, group_records, mask_counts


def build_report(
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    inventory: list[TranscriptInventory],
    adapter_name: str,
    adapter_digest: str,
    source_manifest_name: str,
    source_manifest_digest: str,
    split_manifest_name: str | None,
    split_manifest_digest: str | None,
    pipeline_digest: str,
    context_turns: int,
    mask_counts: Counter[str],
    demo: bool,
) -> dict[str, Any]:
    split_counts = Counter(record["split"] for record in records)
    split_manifest_applied = split_manifest_name is not None
    return {
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_file": Path(__file__).name,
        "pipeline_sha256": pipeline_digest,
        "corpus": "candor",
        "data_status": "restricted_pseudonymized_pending_manual_privacy_review",
        "input_route": INPUT_ROUTE,
        "transcription_algorithm": TRANSCRIPTION_ALGORITHM,
        "demo_mode": demo,
        "adapter_file": adapter_name,
        "adapter_sha256": adapter_digest,
        "source_manifest_file": source_manifest_name,
        "source_manifest_sha256": source_manifest_digest,
        "split_manifest_file": split_manifest_name,
        "split_manifest_sha256": split_manifest_digest,
        "split_manifest_applied": split_manifest_applied,
        "preregistered_split_assignment_present": split_manifest_applied and not demo,
        "synthetic_split_fixture_applied": split_manifest_applied and demo,
        "context_turns": context_turns,
        "observed_release_counts": {
            "transcript_files": len(inventory),
            "transcript_rows": sum(item.row_count for item in inventory),
            "conversations": len({record["source_id"] for record in records}),
            "speakers": len({record["speaker_id"] for record in records}),
            "conversation_speaker_connected_components": len(groups),
        },
        "records_written": len(records),
        "sources": len({record["source_id"] for record in records}),
        "speakers": len({record["speaker_id"] for record in records}),
        "linkage_components": len(groups),
        "split_counts": dict(sorted(split_counts.items())),
        "eligible_for_packet_sampling": 0,
        "privacy_review_pending": len(records),
        "manual_privacy_review_required_for_all_records": True,
        "privacy_mask_counts": dict(sorted(mask_counts.items())),
        "unresolved_reply_references": 0,
        "data_minimization": {
            "source_identifier_fields_written": False,
            "demographic_metadata_fields_written": False,
            "survey_fields_written": False,
            "audio_fields_written": False,
            "video_fields_written": False,
            "precise_timestamp_metadata_fields_written": False,
            "metadata_sampling_strata_written": False,
        },
        "automatic_masking_limitations": AUTOMATIC_MASKING_LIMITATIONS,
        "warning": BUILD_WARNING,
    }


def run_inspect(args: argparse.Namespace) -> None:
    enforce_path_policy(args.input_root, None, demo=False)
    require_private_mode(args.input_root, "CANDOR input root")
    for transcript_path in discover_transcripts(args.input_root):
        require_private_mode(transcript_path, "CANDOR transcript file")
    inventory = inventory_transcripts(args.input_root)
    output = args.output.resolve()
    require(
        output.parent == CANDOR_RAW_ROOT.resolve()
        and output.name == REAL_SOURCE_MANIFEST_NAME
        and output.suffix == ".json",
        "Inspection receipt must be dataset/raw/candor/candor_source_manifest.local.json",
    )
    require(
        all(output != item.path.resolve() for item in inventory),
        "Inspection receipt cannot overwrite a transcript input",
    )
    for item in inventory:
        require_unchanged(item.path, item.sha256, "CANDOR transcript file")
    ensure_private_directory(output.parent)
    manifest = inspection_manifest(inventory)
    atomic_write(output, json_bytes(manifest), args.replace)
    print(
        json.dumps(
            {
                "status": "inspection_only_pending_manual_confirmation",
                "transcript_files": len(inventory),
                "transcript_rows": sum(item.row_count for item in inventory),
                "output": output.name,
                "real_records_written": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )


def run_build(args: argparse.Namespace) -> None:
    enforce_path_policy(args.input_root, args.output, args.demo)
    if args.demo:
        enforce_control_path(args.adapter, args.adapter.name, DEMO_ADAPTER_PATH)
        enforce_control_path(
            args.source_manifest, args.source_manifest.name, DEMO_SOURCE_MANIFEST_PATH
        )
        if args.split_manifest is not None:
            enforce_control_path(
                args.split_manifest, args.split_manifest.name, DEMO_SPLIT_MANIFEST_PATH
            )
    else:
        require_private_mode(args.input_root, "CANDOR input root")
        for transcript_path in discover_transcripts(args.input_root):
            require_private_mode(transcript_path, "CANDOR transcript file")
        for control_path, expected_name, label in (
            (args.adapter, REAL_ADAPTER_NAME, "CANDOR adapter"),
            (args.source_manifest, REAL_SOURCE_MANIFEST_NAME, "CANDOR source manifest"),
            (args.split_manifest, REAL_SPLIT_MANIFEST_NAME, "CANDOR split manifest"),
        ):
            if control_path is not None:
                enforce_control_path(control_path, expected_name, None)
                require_private_mode(control_path, label)

    inventory = inventory_transcripts(args.input_root)
    adapter, adapter_digest = load_json_snapshot(args.adapter)
    source_manifest, source_manifest_digest = load_json_snapshot(args.source_manifest)
    split_manifest: dict[str, Any] | None = None
    split_manifest_digest: str | None = None
    if args.split_manifest is not None:
        split_manifest, split_manifest_digest = load_json_snapshot(args.split_manifest)
    pipeline_path = Path(__file__).resolve()
    pipeline_digest = file_digest(pipeline_path)

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

    validate_source_manifest(source_manifest, inventory, args.demo)
    fields = validate_adapter(adapter, inventory, args.demo)
    secret = load_secret(args.secret_file, args.demo)
    internal = read_internal_rows(inventory, fields, secret)
    source_to_component, groups = build_linkage_groups(internal, secret)
    component_ids = {group["component_id"] for group in groups}
    assignments = load_split_assignments(split_manifest, component_ids, args.demo)
    records, group_records, mask_counts = prepare_records(
        internal,
        source_to_component,
        groups,
        assignments,
        int(adapter["context_turns"]),
    )
    report = build_report(
        records,
        group_records,
        inventory,
        args.adapter.name,
        adapter_digest,
        args.source_manifest.name,
        source_manifest_digest,
        args.split_manifest.name if args.split_manifest else None,
        split_manifest_digest,
        pipeline_digest,
        int(adapter["context_turns"]),
        mask_counts,
        args.demo,
    )
    require(set(report) == BUILD_REPORT_KEYS, "Internal build-report shape mismatch")
    require(
        set(report["observed_release_counts"]) == BUILD_OBSERVED_COUNT_KEYS,
        "Internal observed-count shape mismatch",
    )
    require(
        set(report["data_minimization"]) == DATA_MINIMIZATION_KEYS,
        "Internal minimization shape mismatch",
    )

    for item in inventory:
        require_unchanged(item.path, item.sha256, "CANDOR transcript file")
    require_unchanged(args.adapter, adapter_digest, "CANDOR adapter")
    require_unchanged(
        args.source_manifest, source_manifest_digest, "CANDOR source manifest"
    )
    if args.split_manifest is not None and split_manifest_digest is not None:
        require_unchanged(
            args.split_manifest, split_manifest_digest, "CANDOR split manifest"
        )
    require_unchanged(pipeline_path, pipeline_digest, "CANDOR pipeline")

    output = args.output.resolve()
    ensure_private_directory(output)
    require_clean_output_directory(output)
    paths_and_content = {
        output / "records.jsonl": jsonl_bytes(records),
        output / "linkage_groups.jsonl": jsonl_bytes(group_records),
        output / "build_report.json": json_bytes(report),
    }
    validation_report_path = output / "validation_report.json"
    if not args.replace:
        existing = [path for path in paths_and_content if path.exists()]
        require(not existing, "Refusing partial replacement of existing CANDOR outputs")
        require(
            not validation_report_path.exists(),
            "Refusing a new build beside a stale CANDOR validation report",
        )
    elif validation_report_path.exists():
        invalidation = {
            "status": "invalidated_by_rebuild",
            "corpus": "candor",
            "warning": "Run validate_candor.py before relying on this rebuilt bundle.",
        }
        atomic_write(validation_report_path, json_bytes(invalidation), replace=True)
    for path, content in paths_and_content.items():
        atomic_write(path, content, args.replace)
    print(json.dumps(report, indent=2, sort_keys=True))


def main() -> None:
    args = parse_args()
    try:
        if args.command == "inspect":
            run_inspect(args)
        elif args.command == "build":
            run_build(args)
        else:  # pragma: no cover - argparse enforces this branch
            raise ValueError(f"Unknown command: {args.command}")
    except (
        AssertionError,
        KeyError,
        TypeError,
        csv.Error,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        if isinstance(exc, OSError):
            print("CANDOR preprocessing blocked: restricted file operation failed", file=sys.stderr)
        else:
            print(f"CANDOR preprocessing blocked: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
