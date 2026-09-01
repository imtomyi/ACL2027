#!/usr/bin/env python3
"""Build restricted, provenance-preserving study copies of Dreaddit and AGYW.

The generated JSONL files still contain sensitive natural-language text.  They are
written under dataset/deidentified only to distinguish them from untouched source
files; they are not anonymous and must remain access controlled.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATASET_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_ROOT = DATASET_ROOT / "manifests"

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
REDDIT_USER_RE = re.compile(r"(?<!\w)u/[A-Za-z0-9_-]+", re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){7,15}(?!\d)")
SPACE_RE = re.compile(r"\s+")
SPEAKER_RE = re.compile(
    r"^(M|R\s*\d+|P\s*\d+|ALL|CHORUS|RS?|R)\s*:\s*(.*)$",
    re.IGNORECASE,
)
PARTICIPANT_RE = re.compile(r"^[RP]\d+$")
COLLECTIVE_LABELS = {"R", "RS", "ALL", "CHORUS"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def normalized_text(text: str) -> str:
    return SPACE_RE.sub(" ", text.strip().lower())


def text_hash(text: str) -> str:
    return hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()


def privacy_mask(text: str) -> tuple[str, list[str]]:
    """Mask obvious direct identifiers without claiming full de-identification."""
    flags: list[str] = []
    substitutions = (
        (URL_RE, "[URL]", "url"),
        (EMAIL_RE, "[EMAIL]", "email"),
        (REDDIT_USER_RE, "[REDDIT_USER]", "reddit_user"),
        (HANDLE_RE, "[HANDLE]", "handle"),
        (PHONE_RE, "[PHONE]", "phone_like_number"),
    )
    masked = text
    for pattern, replacement, label in substitutions:
        masked, count = pattern.subn(replacement, masked)
        if count:
            flags.extend([label] * count)
    return masked, sorted(set(flags))


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    os.chmod(path, 0o600)
    return count


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.chmod(path, 0o600)


def verify_file(path: Path, expected: str, algorithm: str) -> None:
    actual = digest(path, algorithm)
    if actual != expected:
        raise ValueError(f"Checksum mismatch for {path.name}: expected {expected}, got {actual}")


def prepare_dreaddit(source_dir: Path, output_root: Path) -> dict:
    manifest = load_json(MANIFEST_ROOT / "dreaddit_source_manifest.json")
    file_specs = {entry["name"]: entry for entry in manifest["files"]}
    train_path = source_dir / "dreaddit-train.csv"
    test_path = source_dir / "dreaddit-test.csv"
    verify_file(train_path, file_specs[train_path.name]["sha256"], "sha256")
    verify_file(test_path, file_specs[test_path.name]["sha256"], "sha256")

    def read_csv(path: Path) -> list[dict]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    splits = {"train": read_csv(train_path), "test": read_csv(test_path)}
    if set(row["post_id"] for row in splits["train"]) & set(
        row["post_id"] for row in splits["test"]
    ):
        raise ValueError("Dreaddit official splits unexpectedly share post_id values")

    test_hashes = {text_hash(row["text"]) for row in splits["test"]}
    output_records: list[dict] = []
    provenance_rows: list[dict] = []
    report: dict = {
        "corpus": "dreaddit",
        "source_manifest": "dataset/manifests/dreaddit_source_manifest.json",
        "official_rows": {},
        "eligible_rows": {},
        "ineligible_reasons": Counter(),
        "masked_identifier_rows": 0,
        "communities": {},
        "labels": {},
    }

    for split_name, rows in splits.items():
        post_order: dict[str, str] = {}
        seen_text: set[str] = set()
        split_records: list[dict] = []
        report["official_rows"][split_name] = len(rows)

        for row_index, row in enumerate(rows, start=1):
            source_post = row["post_id"]
            if source_post not in post_order:
                post_order[source_post] = (
                    f"dreaddit_{split_name}_post_{len(post_order) + 1:05d}"
                )
            source_id = post_order[source_post]
            record_id = f"dreaddit_{split_name}_{row_index:05d}"
            source_text_hash = text_hash(row["text"])
            reasons: list[str] = []
            if split_name == "train" and source_text_hash in test_hashes:
                reasons.append("exact_text_overlap_with_test")
            if source_text_hash in seen_text:
                reasons.append("later_exact_duplicate_within_split")
            seen_text.add(source_text_hash)

            masked_text, privacy_flags = privacy_mask(row["text"])
            if privacy_flags:
                report["masked_identifier_rows"] += 1
            for reason in reasons:
                report["ineligible_reasons"][reason] += 1

            record = {
                "record_id": record_id,
                "corpus": "dreaddit",
                "split": (
                    "development_train" if split_name == "train" else "in_domain_audit"
                ),
                "source_id": source_id,
                "speaker_id": None,
                "text": masked_text,
                "context": {
                    "sentence_range": row["sentence_range"],
                    "preceding_record_ids": [],
                    "moderator_question": None,
                },
                "sampling_strata": {
                    "community": row["subreddit"],
                    "stress_label": int(row["label"]),
                },
                "provenance": {
                    "source_text_sha256": source_text_hash,
                    "source_row": row_index,
                    "source_file_role": split_name,
                },
                "quality": {
                    "eligible_for_packet_sampling": not reasons,
                    "ineligible_reasons": reasons,
                    "privacy_masks_applied": privacy_flags,
                    "manual_excerpt_review_required": True,
                },
            }
            split_records.append(record)
            provenance_rows.append(
                {
                    "record_id": record_id,
                    "source_id": source_id,
                    "source_file": path_name_for_split(split_name),
                    "source_row": row_index,
                    "original_post_id": source_post,
                    "original_segment_id": row["id"],
                    "source_text_sha256": source_text_hash,
                }
            )

        output_records.extend(split_records)
        report["eligible_rows"][split_name] = sum(
            item["quality"]["eligible_for_packet_sampling"] for item in split_records
        )
        report["communities"][split_name] = dict(
            sorted(Counter(row["subreddit"] for row in rows).items())
        )
        report["labels"][split_name] = dict(
            sorted(Counter(row["label"] for row in rows).items())
        )

    report["ineligible_reasons"] = dict(sorted(report["ineligible_reasons"].items()))
    target = output_root / "dreaddit"
    write_jsonl(target / "records.jsonl", output_records)
    write_json(target / "build_report.json", report)
    write_provenance_csv(target / "provenance_map.csv", provenance_rows)
    return report


def path_name_for_split(split_name: str) -> str:
    return f"dreaddit-{split_name}.csv"


def write_provenance_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


@dataclass
class TranscriptEvent:
    speaker_raw: str
    speaker: str
    role: str
    text: str
    source_language_text: str | None
    translation_status: str
    line_start: int
    line_end: int


def normalize_speaker(label: str) -> str:
    return re.sub(r"\s+", "", label).upper()


def speaker_role(label: str) -> str:
    if label == "M":
        return "moderator"
    if PARTICIPANT_RE.match(label):
        return "participant"
    if label in COLLECTIVE_LABELS:
        return "collective"
    return "unclassified"


def transcript_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="strict")
    else:
        text = raw.decode("utf-16-le", errors="strict")
    return text.lstrip("\ufeff").splitlines()


def parsed_line(line: str) -> tuple[str, str, str, str] | None:
    match = SPEAKER_RE.match(line.strip())
    if not match:
        return None
    raw_label = match.group(1).strip()
    label = normalize_speaker(raw_label)
    return raw_label, label, speaker_role(label), match.group(2).strip()


def next_nonempty(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def parse_english_only(lines: list[str]) -> tuple[list[TranscriptEvent], int]:
    events: list[TranscriptEvent] = []
    unparsed = 0
    for index, line in enumerate(lines):
        parsed = parsed_line(line)
        if parsed is None:
            if line.strip():
                unparsed += 1
            continue
        raw_label, label, role, text = parsed
        if text:
            events.append(
                TranscriptEvent(
                    raw_label, label, role, text, None, "english_source", index + 1, index + 1
                )
            )
    return events, unparsed


def parse_duplicate_bilingual(lines: list[str]) -> tuple[list[TranscriptEvent], int]:
    events: list[TranscriptEvent] = []
    consumed: set[int] = set()
    unparsed = 0
    index = 0
    while index < len(lines):
        if index in consumed:
            index += 1
            continue
        first = parsed_line(lines[index])
        if first is None:
            if lines[index].strip():
                unparsed += 1
            index += 1
            continue
        raw_label, label, role, source_text = first
        second_index = next_nonempty(lines, index + 1)
        second = parsed_line(lines[second_index]) if second_index is not None else None
        if second is not None and second[1] == label:
            _, _, _, english_text = second
            consumed.add(second_index)
            events.append(
                TranscriptEvent(
                    raw_label,
                    label,
                    role,
                    english_text or source_text,
                    source_text or None,
                    "paired_translation",
                    index + 1,
                    second_index + 1,
                )
            )
            index = second_index + 1
            continue
        if source_text:
            events.append(
                TranscriptEvent(
                    raw_label,
                    label,
                    role,
                    source_text,
                    None,
                    "unpaired_language_uncertain",
                    index + 1,
                    index + 1,
                )
            )
        index += 1
    return events, unparsed


def parse_alternating_bilingual(lines: list[str]) -> tuple[list[TranscriptEvent], int]:
    events: list[TranscriptEvent] = []
    consumed: set[int] = set()
    unparsed = 0
    index = 0
    while index < len(lines):
        if index in consumed:
            index += 1
            continue
        first = parsed_line(lines[index])
        if first is None:
            if lines[index].strip():
                unparsed += 1
            index += 1
            continue
        raw_label, label, role, source_text = first
        second_index = next_nonempty(lines, index + 1)
        english_text = None
        if second_index is not None and parsed_line(lines[second_index]) is None:
            english_text = lines[second_index].strip()
            consumed.add(second_index)
        events.append(
            TranscriptEvent(
                raw_label,
                label,
                role,
                english_text or source_text,
                source_text or None,
                "paired_translation" if english_text else "unpaired_language_uncertain",
                index + 1,
                (second_index + 1) if english_text else (index + 1),
            )
        )
        index = (second_index + 1) if english_text else (index + 1)
    return events, unparsed


def prepare_agyw(source_dir: Path, output_root: Path) -> dict:
    manifest = load_json(MANIFEST_ROOT / "agyw_source_manifest.json")
    records: list[dict] = []
    provenance_rows: list[dict] = []
    report: dict = {
        "corpus": "agyw_focus_groups",
        "source_manifest": "dataset/manifests/agyw_source_manifest.json",
        "files": {},
        "record_counts": Counter(),
        "observed_participant_keys": 0,
        "reported_participants": manifest["reported_collection"]["participants"],
        "masked_identifier_records": 0,
        "date_conflicts_or_questions": [],
    }
    participant_keys: set[str] = set()

    parsers = {
        "english_only": parse_english_only,
        "duplicate_bilingual": parse_duplicate_bilingual,
        "alternating_bilingual": parse_alternating_bilingual,
    }

    for file_spec in manifest["files"]:
        path = source_dir / file_spec["name"]
        verify_file(path, file_spec["md5"], "md5")
        lines = transcript_lines(path)
        events, unparsed = parsers[file_spec["format"]](lines)
        previous_record_ids: deque[str] = deque(maxlen=3)
        last_moderator_text: str | None = None
        output_turn_index = 0
        file_counts = Counter()

        if file_spec.get("date_status"):
            report["date_conflicts_or_questions"].append(
                {"doc_id": file_spec["doc_id"], "status": file_spec["date_status"]}
            )

        for event_index, event in enumerate(events, start=1):
            masked_text, privacy_flags = privacy_mask(event.text)
            if event.role == "moderator":
                last_moderator_text, _ = privacy_mask(event.text)
                file_counts["moderator_events"] += 1
                continue
            if event.role not in {"participant", "collective"}:
                file_counts["unclassified_events"] += 1
                continue
            output_turn_index += 1
            record_id = f"{file_spec['doc_id']}_turn_{output_turn_index:04d}"
            speaker_id = (
                f"{file_spec['doc_id']}_{event.speaker.lower()}"
                if event.role == "participant"
                else None
            )
            if speaker_id:
                participant_keys.add(speaker_id)
            word_count = len(masked_text.split())
            eligible = event.role == "participant" and word_count >= 3
            ineligible_reasons: list[str] = []
            if event.role == "collective":
                ineligible_reasons.append("collective_turn_retained_for_context")
            if word_count < 3:
                ineligible_reasons.append("short_turn_retained_for_context")
            if privacy_flags:
                report["masked_identifier_records"] += 1

            record = {
                "record_id": record_id,
                "corpus": "agyw_focus_groups",
                "split": "heldout_cross_domain_evaluation",
                "source_id": file_spec["doc_id"],
                "speaker_id": speaker_id,
                "text": masked_text,
                "context": {
                    "moderator_question": last_moderator_text,
                    "preceding_record_ids": list(previous_record_ids),
                },
                "sampling_strata": {
                    "participant_group": file_spec["participant_group"],
                },
                "provenance": {
                    "source_text_sha256": text_hash(event.text),
                    "source_line_start": event.line_start,
                    "source_line_end": event.line_end,
                    "source_turn_index": event_index,
                    "speaker_label_normalized": event.speaker,
                    "translation_status": event.translation_status,
                },
                "quality": {
                    "eligible_for_packet_sampling": eligible,
                    "ineligible_reasons": ineligible_reasons,
                    "privacy_masks_applied": privacy_flags,
                    "manual_excerpt_review_required": True,
                },
            }
            records.append(record)
            previous_record_ids.append(record_id)
            file_counts[event.role] += 1
            file_counts["eligible_for_packet_sampling"] += int(eligible)
            file_counts["short_turns"] += int(word_count < 3)
            file_counts[f"translation_{event.translation_status}"] += 1
            report["record_counts"][event.role] += 1
            report["record_counts"]["eligible_for_packet_sampling"] += int(eligible)
            report["record_counts"]["short_turns"] += int(word_count < 3)
            provenance_rows.append(
                {
                    "record_id": record_id,
                    "source_id": file_spec["doc_id"],
                    "source_file": file_spec["name"],
                    "source_md5": file_spec["md5"],
                    "source_line_start": event.line_start,
                    "source_line_end": event.line_end,
                    "speaker_label_raw": event.speaker_raw,
                    "speaker_label_normalized": event.speaker,
                    "source_text_sha256": text_hash(event.text),
                }
            )

        file_counts["unparsed_nonempty_lines"] = unparsed
        report["files"][file_spec["doc_id"]] = dict(sorted(file_counts.items()))

    report["record_counts"] = dict(sorted(report["record_counts"].items()))
    report["observed_participant_keys"] = len(participant_keys)
    report["participant_count_warning"] = (
        "The source paper reports 107 participants, while normalized transcript-local "
        f"speaker labels yield {len(participant_keys)} observed participant keys. "
        "Do not claim complete participant coverage until this is reconciled."
    )
    target = output_root / "agyw_focus_groups"
    write_jsonl(target / "records.jsonl", records)
    write_json(target / "build_report.json", report)
    write_provenance_csv(target / "provenance_map.csv", provenance_rows)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dreaddit-dir",
        type=Path,
        default=DATASET_ROOT / "raw" / "dreaddit",
    )
    parser.add_argument(
        "--agyw-dir",
        type=Path,
        default=DATASET_ROOT / "agyw_focus_groups",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATASET_ROOT / "deidentified",
    )
    parser.add_argument(
        "--corpus",
        choices=("all", "dreaddit", "agyw"),
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reports: dict[str, dict] = {}
    if args.corpus in {"all", "dreaddit"}:
        reports["dreaddit"] = prepare_dreaddit(args.dreaddit_dir, args.output_dir)
    if args.corpus in {"all", "agyw"}:
        reports["agyw_focus_groups"] = prepare_agyw(args.agyw_dir, args.output_dir)
    summary = {
        name: {
            "eligible_rows": report.get("eligible_rows"),
            "record_counts": report.get("record_counts"),
        }
        for name, report in reports.items()
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
