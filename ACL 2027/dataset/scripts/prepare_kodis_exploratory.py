#!/usr/bin/env python3
"""Build a minimal, private exploratory KODIS dataset from the received XLSX.

This is deliberately separate from ``prepare_kodis.py``.  It does not change or
relax the governed real-data workflow.  It supports only the observed one-row-
per-dyad KODIS workbook, retains nonempty human-human transcript rows,
drops transcript timestamps and all survey/demographic fields, and assigns the
entire output to one exploratory (unsplit) lane.

The dialogue and turn files contain restricted transcript data.  The aggregate
and build reports contain counts, hashes, and schema descriptions only; they
never contain transcript excerpts or raw dyad identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from openpyxl import load_workbook


PIPELINE_VERSION = "1.0"
CORPUS = "kodis"
ANALYSIS_STATUS = "private_exploratory"
SPLIT = "exploratory_unsplit"
EXPECTED_OUTPUT_FILES = {
    "dialogues.jsonl",
    "turns.jsonl",
    "aggregate_report.json",
    "build_report.json",
}
REQUIRED_COLUMNS = {
    "dyad_id",
    "formattedChat",
    "Outcome",
    "buyer_is_AI",
    "seller_is_AI",
}
LINE_RE = re.compile(r"^(?P<time>nan|\d+)\s+(?P<role>Buyer|Seller):\s*(?P<text>.*)$")
WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)


@dataclass(frozen=True)
class SourceRow:
    """Only the five source fields needed during exploratory preprocessing."""

    source_row: int
    dyad_id: str
    formatted_chat: str | None
    outcome: Any
    buyer_is_ai: Any
    seller_is_ai: Any


@dataclass(frozen=True)
class WorkbookSnapshot:
    source_file: str
    worksheet: str
    source_rows: int
    source_columns: int
    rows: tuple[SourceRow, ...]


@dataclass(frozen=True)
class ParsedChat:
    messages: tuple[tuple[str, str], ...]
    continuation_lines: int
    unparsable_leading_lines: int
    contains_nan_timestamp: bool


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def jsonl_bytes(values: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for value in values
    )


def parse_bool(value: Any, *, field: str, source_row: int) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
    raise ValueError(f"Source row {source_row} has an invalid {field} value")


def parse_chat(chat: str) -> ParsedChat:
    messages: list[tuple[str, str]] = []
    continuation_lines = 0
    unparsable_leading_lines = 0
    contains_nan_timestamp = False
    for raw_line in chat.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if match:
            role = match.group("role").lower()
            text = match.group("text").strip()
            messages.append((role, text))
            contains_nan_timestamp = contains_nan_timestamp or match.group("time") == "nan"
        elif messages:
            role, prior = messages[-1]
            messages[-1] = (role, f"{prior} {line}".strip())
            continuation_lines += 1
        else:
            unparsable_leading_lines += 1
    return ParsedChat(
        messages=tuple(messages),
        continuation_lines=continuation_lines,
        unparsable_leading_lines=unparsable_leading_lines,
        contains_nan_timestamp=contains_nan_timestamp,
    )


def normalize_headers(values: Sequence[Any]) -> tuple[str, ...]:
    headers = ["dyad_id" if index == 0 and value is None else str(value) for index, value in enumerate(values)]
    require(len(headers) == len(set(headers)), "Workbook contains duplicate column headers")
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    require(not missing, f"Workbook is missing required columns: {missing}")
    return tuple(headers)


def read_minimized_snapshot(workbook_path: Path) -> WorkbookSnapshot:
    require(workbook_path.exists(), f"Workbook does not exist: {workbook_path}")
    require(workbook_path.is_file(), f"Workbook is not a regular file: {workbook_path}")
    require(not workbook_path.is_symlink(), "Refusing a symlinked KODIS workbook")
    require(workbook_path.suffix.lower() == ".xlsx", "Exploratory KODIS input must be an XLSX workbook")

    workbook = load_workbook(workbook_path, read_only=True, data_only=True, keep_links=False)
    try:
        require(bool(workbook.sheetnames), "Workbook has no worksheets")
        worksheet = workbook[workbook.sheetnames[0]]
        row_iterator = worksheet.iter_rows(values_only=True)
        try:
            raw_headers = next(row_iterator)
        except StopIteration as error:
            raise ValueError("Workbook is empty") from error
        headers = normalize_headers(raw_headers)
        index = {header: position for position, header in enumerate(headers)}
        rows: list[SourceRow] = []
        for source_row, values in enumerate(row_iterator, start=2):
            rows.append(
                SourceRow(
                    source_row=source_row,
                    dyad_id=str(values[index["dyad_id"]]),
                    formatted_chat=values[index["formattedChat"]],
                    outcome=values[index["Outcome"]],
                    buyer_is_ai=values[index["buyer_is_AI"]],
                    seller_is_ai=values[index["seller_is_AI"]],
                )
            )
        return WorkbookSnapshot(
            source_file=workbook_path.name,
            worksheet=worksheet.title,
            source_rows=len(rows),
            source_columns=len(headers),
            rows=tuple(rows),
        )
    finally:
        workbook.close()


def percentile(values: Sequence[int], proportion: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values: Sequence[int]) -> dict[str, int | float | None]:
    return {
        "n": len(values),
        "sum": sum(values),
        "min": min(values) if values else None,
        "p25": percentile(values, 0.25),
        "median": statistics.median(values) if values else None,
        "p75": percentile(values, 0.75),
        "max": max(values) if values else None,
        "mean": statistics.fmean(values) if values else None,
    }


def outcome_label(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "missing"
    return str(value).strip()


def transform(
    snapshot: WorkbookSnapshot,
    *,
    source_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    dyad_ids = [row.dyad_id for row in snapshot.rows]
    require(len(dyad_ids) == len(set(dyad_ids)), "Duplicate source dyad identifiers detected")

    interaction_counts: Counter[str] = Counter()
    included_outcomes: Counter[str] = Counter()
    excluded_missing_outcomes: Counter[str] = Counter()
    exact_chat_hashes: Counter[str] = Counter()
    message_counts: list[int] = []
    word_counts: list[int] = []
    character_counts: list[int] = []
    dialogues: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    missing_human_human = 0
    seller_first_dialogues = 0
    repeated_role_dialogues = 0
    repeated_role_transitions = 0
    dialogues_missing_a_role = 0
    continuation_line_dialogues = 0
    continuation_lines = 0
    nan_timestamp_dialogues = 0
    empty_message_turns = 0

    for row in snapshot.rows:
        buyer_ai = parse_bool(row.buyer_is_ai, field="buyer_is_AI", source_row=row.source_row)
        seller_ai = parse_bool(row.seller_is_ai, field="seller_is_AI", source_row=row.source_row)
        lane = "human_human" if not buyer_ai and not seller_ai else "human_ai" if buyer_ai ^ seller_ai else "ai_ai"
        interaction_counts[lane] += 1
        if lane != "human_human":
            continue
        if not isinstance(row.formatted_chat, str) or not row.formatted_chat.strip():
            missing_human_human += 1
            excluded_missing_outcomes[outcome_label(row.outcome)] += 1
            continue

        parsed = parse_chat(row.formatted_chat)
        require(
            parsed.unparsable_leading_lines == 0,
            f"Source row {row.source_row} has unparsable text before its first Buyer/Seller message",
        )
        require(parsed.messages, f"Source row {row.source_row} has no parsed Buyer/Seller messages")
        roles = [role for role, _ in parsed.messages]
        repeat_count = sum(roles[index] == roles[index - 1] for index in range(1, len(roles)))
        word_count = sum(len(WORD_RE.findall(text)) for _, text in parsed.messages)
        character_count = sum(len(text) for _, text in parsed.messages)
        dialogue_id = f"kodis_exploratory_dialogue_{row.source_row:06d}"

        dialogues.append(
            {
                "analysis_status": ANALYSIS_STATUS,
                "character_count": character_count,
                "corpus": CORPUS,
                "dialogue_id": dialogue_id,
                "first_role": roles[0],
                "outcome": outcome_label(row.outcome),
                "repeated_role_transition_count": repeat_count,
                "source_row": row.source_row,
                "split": SPLIT,
                "turn_count": len(parsed.messages),
                "word_count": word_count,
            }
        )
        previous_turn_id: str | None = None
        for turn_index, (role, text) in enumerate(parsed.messages, start=1):
            turn_id = f"{dialogue_id}_turn_{turn_index:04d}"
            turns.append(
                {
                    "corpus": CORPUS,
                    "dialogue_id": dialogue_id,
                    "preceding_turn_id": previous_turn_id,
                    "role": role,
                    "text": text,
                    "turn_id": turn_id,
                    "turn_index": turn_index,
                }
            )
            previous_turn_id = turn_id
            empty_message_turns += int(not text)

        included_outcomes[outcome_label(row.outcome)] += 1
        exact_chat_hashes[hashlib.sha256(row.formatted_chat.encode("utf-8")).hexdigest()] += 1
        message_counts.append(len(parsed.messages))
        word_counts.append(word_count)
        character_counts.append(character_count)
        seller_first_dialogues += int(roles[0] == "seller")
        repeated_role_dialogues += int(repeat_count > 0)
        repeated_role_transitions += repeat_count
        dialogues_missing_a_role += int(set(roles) != {"buyer", "seller"})
        continuation_line_dialogues += int(parsed.continuation_lines > 0)
        continuation_lines += parsed.continuation_lines
        nan_timestamp_dialogues += int(parsed.contains_nan_timestamp)

    duplicate_groups = [count for count in exact_chat_hashes.values() if count > 1]
    report = {
        "report_version": "1.0",
        "corpus": CORPUS,
        "analysis_status": ANALYSIS_STATUS,
        "use_scope": "private exploratory analysis only",
        "source": {
            "file": snapshot.source_file,
            "sha256": source_sha256,
            "worksheet": snapshot.worksheet,
            "rows": snapshot.source_rows,
            "columns": snapshot.source_columns,
        },
        "filtering": {
            "interaction_counts": dict(sorted(interaction_counts.items())),
            "excluded_non_human_dialogues": interaction_counts["human_ai"] + interaction_counts["ai_ai"],
            "excluded_missing_human_human_transcripts": missing_human_human,
            "included_human_human_dialogues": len(dialogues),
            "included_outcome_counts": dict(sorted(included_outcomes.items())),
            "excluded_missing_transcript_outcome_counts": dict(sorted(excluded_missing_outcomes.items())),
        },
        "records": {
            "dialogue_records": len(dialogues),
            "turn_records": len(turns),
            "message_count": distribution(message_counts),
            "word_count": distribution(word_counts),
            "character_count": distribution(character_counts),
        },
        "structure": {
            "buyer_first_dialogues": len(dialogues) - seller_first_dialogues,
            "seller_first_dialogues": seller_first_dialogues,
            "dialogues_with_repeated_role_transitions": repeated_role_dialogues,
            "repeated_role_transitions": repeated_role_transitions,
            "dialogues_missing_buyer_or_seller": dialogues_missing_a_role,
            "dialogues_with_continuation_lines": continuation_line_dialogues,
            "continuation_lines": continuation_lines,
            "dialogues_with_nan_timestamps": nan_timestamp_dialogues,
            "empty_message_turns": empty_message_turns,
            "exact_duplicate_transcript_groups": len(duplicate_groups),
            "dialogues_in_exact_duplicate_transcript_groups": sum(duplicate_groups),
        },
        "data_minimization": {
            "source_fields_read": ["dyad_id", "formattedChat", "Outcome", "buyer_is_AI", "seller_is_AI"],
            "source_fields_written_to_records": ["formattedChat-derived message text", "Outcome"],
            "dyad_id_policy": "checked for uniqueness in memory; never written",
            "transcript_timestamp_policy": "parsed only to identify message boundaries; never written",
            "discarded_source_column_count": snapshot.source_columns - 5,
            "dialogue_output_fields": [
                "dialogue_id",
                "source_row",
                "outcome",
                "turn_count",
                "word_count",
                "character_count",
                "first_role",
                "repeated_role_transition_count",
            ],
            "turn_output_fields": [
                "turn_id",
                "dialogue_id",
                "turn_index",
                "role",
                "text",
                "preceding_turn_id",
            ],
            "aggregate_reports_contain_transcript_text": False,
        },
        "experimental_constraints": {
            "split": SPLIT,
            "cross_dialogue_participant_ids_available": False,
            "participant_disjoint_split_supported": False,
            "seller_first_dialogues_retained": True,
            "repeated_role_dialogues_retained": True,
            "human_ai_dialogues_retained": False,
            "missing_transcripts_retained": False,
        },
        "warning": (
            "Restricted transcript-bearing output: not anonymous and not suitable for participant-disjoint "
            "train/test claims. Keep local; do not publish, redistribute, or upload to an external service "
            "without separate authorization."
        ),
    }
    return dialogues, turns, report


def ensure_output_location(workbook_path: Path, output_dir: Path, *, replace: bool) -> None:
    workbook_resolved = workbook_path.resolve()
    output_resolved = output_dir.resolve()
    require(
        not output_resolved.is_relative_to(workbook_resolved.parent),
        "Output must be outside the raw KODIS landing directory",
    )
    require(not workbook_resolved.is_relative_to(output_resolved), "Output directory cannot contain the source workbook")
    if output_dir.exists():
        require(output_dir.is_dir(), "Output path exists and is not a directory")
        require(not output_dir.is_symlink(), "Refusing a symlinked output directory")
        names = {path.name for path in output_dir.iterdir()}
        unknown = sorted(names - EXPECTED_OUTPUT_FILES)
        require(not unknown, f"Output contains unexpected files: {unknown}")
        if names and not replace:
            raise ValueError("Output already exists; pass --replace to overwrite the known exploratory bundle")
    else:
        output_dir.mkdir(parents=True, mode=0o700)
    os.chmod(output_dir, 0o700)


def write_private(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    os.chmod(path, 0o600)


def validate_bundle(
    output_dir: Path,
    *,
    report: dict[str, Any],
    expected_dialogues: int,
    expected_turns: int,
) -> dict[str, Any]:
    require((output_dir.stat().st_mode & 0o077) == 0, "Exploratory output directory permits group/other access")
    require({path.name for path in output_dir.iterdir()} == EXPECTED_OUTPUT_FILES, "Exploratory bundle is incomplete")
    for path in output_dir.iterdir():
        require(path.is_file() and not path.is_symlink(), f"Invalid exploratory output entry: {path.name}")
        require((path.stat().st_mode & 0o077) == 0, f"Exploratory output file permits group/other access: {path.name}")

    dialogue_rows = [json.loads(line) for line in (output_dir / "dialogues.jsonl").read_text(encoding="utf-8").splitlines() if line]
    turn_rows = [json.loads(line) for line in (output_dir / "turns.jsonl").read_text(encoding="utf-8").splitlines() if line]
    require(len(dialogue_rows) == expected_dialogues, "Dialogue output count differs from the build")
    require(len(turn_rows) == expected_turns, "Turn output count differs from the build")
    expected_dialogue_keys = {
        "analysis_status",
        "character_count",
        "corpus",
        "dialogue_id",
        "first_role",
        "outcome",
        "repeated_role_transition_count",
        "source_row",
        "split",
        "turn_count",
        "word_count",
    }
    expected_turn_keys = {
        "corpus",
        "dialogue_id",
        "preceding_turn_id",
        "role",
        "text",
        "turn_id",
        "turn_index",
    }
    require(all(set(row) == expected_dialogue_keys for row in dialogue_rows), "Unexpected dialogue output field")
    require(all(set(row) == expected_turn_keys for row in turn_rows), "Unexpected turn output field")
    dialogue_ids = {row["dialogue_id"] for row in dialogue_rows}
    require(len(dialogue_ids) == len(dialogue_rows), "Dialogue IDs are not unique")
    require(all(row["split"] == SPLIT for row in dialogue_rows), "Exploratory dialogues must remain unsplit")
    require(all(row["dialogue_id"] in dialogue_ids for row in turn_rows), "A turn references an unknown dialogue")
    require(len({row["turn_id"] for row in turn_rows}) == len(turn_rows), "Turn IDs are not unique")
    require(all(row["role"] in {"buyer", "seller"} for row in turn_rows), "Unexpected turn role")
    turns_by_dialogue: dict[str, list[dict[str, Any]]] = {dialogue_id: [] for dialogue_id in dialogue_ids}
    for row in turn_rows:
        turns_by_dialogue[row["dialogue_id"]].append(row)
    for dialogue in dialogue_rows:
        ordered = sorted(turns_by_dialogue[dialogue["dialogue_id"]], key=lambda row: row["turn_index"])
        require(len(ordered) == dialogue["turn_count"], "Dialogue turn count does not match turn records")
        require(
            [row["turn_index"] for row in ordered] == list(range(1, len(ordered) + 1)),
            "Turn indices are not consecutive from one",
        )
        expected_preceding = [None] + [row["turn_id"] for row in ordered[:-1]]
        require(
            [row["preceding_turn_id"] for row in ordered] == expected_preceding,
            "Preceding-turn lineage is inconsistent",
        )

    report_on_disk = json.loads((output_dir / "aggregate_report.json").read_text(encoding="utf-8"))
    require(report_on_disk == report, "Aggregate report differs from the verified build")
    require(
        report_on_disk["data_minimization"]["aggregate_reports_contain_transcript_text"] is False,
        "Aggregate report must declare that it contains no transcript text",
    )
    build_report = json.loads((output_dir / "build_report.json").read_text(encoding="utf-8"))
    require(build_report["source_preserved"] is True, "Build report does not preserve the source workbook")
    for name in ("dialogues.jsonl", "turns.jsonl", "aggregate_report.json"):
        entry = build_report["output_files"][name]
        require(sha256_file(output_dir / name) == entry["sha256"], f"Output checksum mismatch: {name}")
        require((output_dir / name).stat().st_size == entry["bytes"], f"Output byte count mismatch: {name}")
    return {
        "status": "ok",
        "dialogues": len(dialogue_rows),
        "turns": len(turn_rows),
        "split": SPLIT,
    }


def build(workbook_path: Path, output_dir: Path, *, replace: bool = False) -> dict[str, Any]:
    workbook_path = workbook_path.resolve()
    source_sha256_before = sha256_file(workbook_path)
    snapshot = read_minimized_snapshot(workbook_path)
    dialogues, turns, report = transform(snapshot, source_sha256=source_sha256_before)
    source_sha256_after = sha256_file(workbook_path)
    require(source_sha256_after == source_sha256_before, "Source workbook changed during preprocessing")

    ensure_output_location(workbook_path, output_dir, replace=replace)
    dialogue_content = jsonl_bytes(dialogues)
    turn_content = jsonl_bytes(turns)
    aggregate_content = json_bytes(report)
    write_private(output_dir / "dialogues.jsonl", dialogue_content)
    write_private(output_dir / "turns.jsonl", turn_content)
    write_private(output_dir / "aggregate_report.json", aggregate_content)

    pipeline_path = Path(__file__).resolve()
    build_report = {
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_file": pipeline_path.name,
        "pipeline_sha256": sha256_file(pipeline_path),
        "corpus": CORPUS,
        "analysis_status": ANALYSIS_STATUS,
        "source_file": snapshot.source_file,
        "source_sha256_before": source_sha256_before,
        "source_sha256_after": source_sha256_after,
        "source_preserved": source_sha256_before == source_sha256_after,
        "output_directory_policy": "private mode 0700; files mode 0600",
        "output_files": {
            "dialogues.jsonl": {
                "bytes": len(dialogue_content),
                "records": len(dialogues),
                "sha256": hashlib.sha256(dialogue_content).hexdigest(),
                "contains_restricted_transcript_text": False,
            },
            "turns.jsonl": {
                "bytes": len(turn_content),
                "records": len(turns),
                "sha256": hashlib.sha256(turn_content).hexdigest(),
                "contains_restricted_transcript_text": True,
            },
            "aggregate_report.json": {
                "bytes": len(aggregate_content),
                "sha256": hashlib.sha256(aggregate_content).hexdigest(),
                "contains_restricted_transcript_text": False,
            },
        },
        "governed_pipeline_relationship": "standalone; does not import or modify prepare_kodis.py",
        "validation": "performed during build",
    }
    write_private(output_dir / "build_report.json", json_bytes(build_report))
    validation = validate_bundle(
        output_dir,
        report=report,
        expected_dialogues=len(dialogues),
        expected_turns=len(turns),
    )
    return {**validation, "aggregate_report": report, "build_report": build_report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build private exploratory KODIS dialogue and turn records.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build(args.workbook, args.output, replace=args.replace)
    summary = {
        "status": result["status"],
        "dialogues": result["dialogues"],
        "turns": result["turns"],
        "split": result["split"],
        "output": str(args.output),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
