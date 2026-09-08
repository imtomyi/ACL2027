#!/usr/bin/env python3
"""Build working packet banks for GoEmotions, AGYW, and ParlaMint-GB.

These artifacts contain source text. They are local working sets for Table 3
pipeline development and distribution sensitivity checks, not manuscript-ready
or release-ready datasets.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import tarfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_STORAGE = WORKSPACE / "Storage" / "draft_review_packets"
GOEMOTIONS_ROOT = WORKSPACE / "dataset" / "raw" / "goemotions" / "upstream"
AGYW_RECORDS = WORKSPACE / "dataset" / "deidentified" / "agyw_focus_groups" / "records.jsonl"
PARLAMINT_ARCHIVE = WORKSPACE / "dataset" / "raw" / "parlamint_gb" / "ParlaMint-GB.tgz"

FLAW_TYPES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)

RESEARCH_QUESTIONS = {
    "goemotions": "How do people express and contextualize emotion in short social media comments?",
    "agyw_focus_groups": "How do participants describe health, relationships, and community pressures in focus-group discussion?",
    "parlamint_gb": "How do parliamentary speakers frame public issues and policy disagreement in debate?",
}

DATASET_ROLES = {
    "goemotions": "development_train_working_sample; test_split_excluded",
    "agyw_focus_groups": "heldout_cross_domain_working_sample; not_for_training",
    "parlamint_gb": "heldout_cross_domain_descriptive_working_sample; not_for_training",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_hash(value: str) -> str:
    return sha256_text(value)[:16]


def normalized_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row is not an object")
            rows.append(value)
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    os.chmod(path, 0o600)
    return count


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


def file_manifest(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def goemotions_records(min_words: int) -> list[dict[str, Any]]:
    path = GOEMOTIONS_ROOT / "train.tsv"
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for row_index, line in enumerate(handle, 1):
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 3:
                raise ValueError(f"unexpected GoEmotions TSV field count on row {row_index}")
            text, labels, comment_id = fields
            text = normalized_space(text)
            word_count = len(text.split())
            if word_count < min_words:
                continue
            record_id = f"goemotions_train_{row_index:05d}"
            records.append(
                {
                    "record_id": record_id,
                    "corpus": "goemotions",
                    "split": "development_train",
                    "source_id": record_id,
                    "speaker_id": None,
                    "text": text,
                    "context": {
                        "preceding_record_ids": [],
                        "moderator_question": None,
                    },
                    "sampling_strata": {
                        "label_ids": labels.split(",") if labels else [],
                        "word_count": word_count,
                    },
                    "provenance": {
                        "source_file": "train.tsv",
                        "source_row": row_index,
                        "comment_id_sha256": sha256_text(comment_id),
                        "source_text_sha256": sha256_text(text.lower()),
                    },
                    "quality": {
                        "eligible_for_packet_sampling": True,
                        "ineligible_reasons": [],
                        "manual_excerpt_review_required": True,
                        "privacy_masks_applied": [],
                    },
                }
            )
    return records


def agyw_records() -> list[dict[str, Any]]:
    rows = load_jsonl(AGYW_RECORDS)
    return [
        row
        for row in rows
        if row.get("corpus") == "agyw_focus_groups"
        and row.get("quality", {}).get("eligible_for_packet_sampling") is True
    ]


def parlamint_text(elem: ET.Element) -> str:
    segments = []
    for seg in elem.iter():
        if seg.tag.split("}", 1)[-1] == "seg":
            segments.append(normalized_space(" ".join(seg.itertext())))
    if not segments:
        segments.append(normalized_space(" ".join(elem.itertext())))
    return normalized_space(" ".join(item for item in segments if item))


def parlamint_records(limit: int, min_words: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with tarfile.open(PARLAMINT_ARCHIVE, "r:gz") as tar:
        session_names = sorted(
            name
            for name in tar.getnames()
            if re.search(r"/ParlaMint-GB_\d{4}-.*\.xml$", name)
        )
        for name in session_names:
            if len(records) >= limit:
                break
            file_obj = tar.extractfile(name)
            if file_obj is None:
                continue
            root = ET.parse(file_obj).getroot()
            source_id = Path(name).stem
            year_match = re.search(r"_(\d{4})-", source_id)
            chamber = "commons" if "commons" in source_id else "lords" if "lords" in source_id else "unknown"
            previous_record_ids: deque[str] = deque(maxlen=3)
            turn_index = 0
            for elem in root.iter():
                if len(records) >= limit:
                    break
                if elem.tag.split("}", 1)[-1] != "u":
                    continue
                text = parlamint_text(elem)
                word_count = len(text.split())
                if word_count < min_words:
                    continue
                turn_index += 1
                record_id = f"parlamint_gb_{len(records) + 1:05d}"
                records.append(
                    {
                        "record_id": record_id,
                        "corpus": "parlamint_gb",
                        "split": "heldout_cross_domain_descriptive",
                        "source_id": source_id,
                        "speaker_id": elem.attrib.get("who"),
                        "text": text,
                        "context": {
                            "preceding_record_ids": list(previous_record_ids),
                            "moderator_question": None,
                        },
                        "sampling_strata": {
                            "chamber": chamber,
                            "year": year_match.group(1) if year_match else None,
                            "word_count": word_count,
                        },
                        "provenance": {
                            "source_archive": "ParlaMint-GB.tgz",
                            "source_file": name,
                            "source_turn_index": turn_index,
                            "source_text_sha256": sha256_text(text.lower()),
                        },
                        "quality": {
                            "eligible_for_packet_sampling": True,
                            "ineligible_reasons": [],
                            "manual_excerpt_review_required": True,
                            "privacy_masks_applied": [],
                        },
                    }
                )
                previous_record_ids.append(record_id)
    return records


def choose_records(records: list[dict[str, Any]], needed: int) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(records, key=lambda row: row["record_id"]):
        by_source[str(record["source_id"])].append(record)
    source_ids = sorted(by_source)
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < needed and source_ids:
        source_id = source_ids[cursor % len(source_ids)]
        bucket = by_source[source_id]
        if bucket:
            selected.append(bucket.pop(0))
        else:
            source_ids.remove(source_id)
            cursor -= 1
        cursor += 1
    if len(selected) != needed:
        raise RuntimeError(f"not_enough_records:{needed}>{len(selected)}")
    return selected


def excerpt(record: dict[str, Any], display_order: int) -> dict[str, Any]:
    return {
        "candidate_role": "cited" if display_order <= 2 else "context",
        "display_order": display_order,
        "excerpt_id": f"EXC_{short_hash(record['record_id'])}",
        "local_context": record.get("context"),
        "metadata": {
            "split": record.get("split"),
            **dict(record.get("sampling_strata", {})),
        },
        "source_id": record["source_id"],
        "source_record_id": record["record_id"],
        "speaker_id": record.get("speaker_id"),
        "text": record["text"],
    }


def claim_for(corpus: str, flaw_type: str, excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    cited = [excerpts[0]["excerpt_id"], excerpts[1]["excerpt_id"]]
    first = excerpts[0]["excerpt_id"]
    third = excerpts[2]["excerpt_id"]
    corpus_phrase = {
        "goemotions": "emotional expression",
        "agyw_focus_groups": "participant experience",
        "parlamint_gb": "policy debate",
    }[corpus]
    if flaw_type == "unsupported_evidence":
        claim = f"The displayed sources show that {corpus_phrase} is mainly driven by institutional procedures and formal paperwork."
        explanation = "The claim introduces a specific causal account that is not established by the displayed evidence."
        boundary = ["Other displayed sources may not support the paperwork-centered explanation."]
    elif flaw_type == "source_concentration":
        cited = [first]
        claim = f"Across the whole packet, {corpus_phrase} follows one dominant pattern shown by the cited source."
        explanation = "The synthesis makes a packet-level claim while leaning on one displayed source."
        boundary = ["The other displayed excerpts are available but are not substantively integrated."]
    elif flaw_type == "counterevidence_loss":
        claim = f"Every displayed source presents the same severe and unresolved version of {corpus_phrase}."
        explanation = "The synthesis suppresses boundary cases that should constrain the theme."
        boundary = [f"Context excerpt {third} may limit the all-sources claim."]
    elif flaw_type == "contextual_flattening":
        claim = f"The excerpts show no meaningful contextual differences in {corpus_phrase}."
        explanation = "The synthesis collapses distinct local situations into a single undifferentiated theme."
        boundary = ["Differences in source situation, speaker role, and local context are not preserved."]
    elif flaw_type == "unsupported_abstraction":
        claim = f"{corpus_phrase.capitalize()} functions as a generalized rupture in selfhood and social order across the packet."
        explanation = "The synthesis moves to an abstract theoretical category beyond what the displayed context warrants."
        boundary = ["The abstract category is not directly grounded in the displayed wording and context."]
    else:
        raise ValueError(f"unknown flaw type: {flaw_type}")
    return {
        "boundary_conditions": boundary,
        "cited_excerpt_ids": cited,
        "claim": claim,
        "explanation": explanation,
        "model_id": "deterministic_working_packet_builder_v2",
        "theme_name": f"Working {flaw_type.replace('_', ' ')} theme",
    }


def build_bank(corpus: str, records: list[dict[str, Any]], output_root: Path, packets_per_flaw: int) -> dict[str, Any]:
    total_packets = len(FLAW_TYPES) * packets_per_flaw
    selected = choose_records(records, total_packets * 4)
    packets: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    index = 0
    for flaw_type in FLAW_TYPES:
        for flaw_index in range(packets_per_flaw):
            packet_records = selected[index : index + 4]
            index += 4
            packet_id = f"PKT_{short_hash(output_root.name + corpus + flaw_type + str(flaw_index))}"
            output_id = f"OUT_{short_hash(packet_id)}"
            excerpts = [excerpt(record, display_order) for display_order, record in enumerate(packet_records, 1)]
            packet = {
                "corpus_id": corpus,
                "dataset_role": DATASET_ROLES[corpus],
                "draft_status": "working_not_manuscript_eligible",
                "flaw_taxonomy": list(FLAW_TYPES),
                "handling": {
                    "contains_source_text": True,
                    "not_for_manuscript_table": True,
                    "restricted_local_only": True,
                },
                "known_intended_flaw_note": "Working deterministic flaw injection for pipeline development.",
                "known_intended_flaw_type": flaw_type,
                "llm_generated_qualitative_claim": claim_for(corpus, flaw_type, excerpts),
                "output_id": output_id,
                "packet_id": packet_id,
                "packet_schema_version": "warrantroute-working-multicorpus-packet-v1",
                "research_question": RESEARCH_QUESTIONS[corpus],
                "review_instruction": "Review whether the qualitative claim is warranted by the displayed source text/context.",
                "source_text_context": excerpts,
            }
            packets.append(packet)
            truth_rows.append(
                {
                    "packet_id": packet_id,
                    "output_id": output_id,
                    "corpus_id": corpus,
                    "known_intended_flaw_type": flaw_type,
                    "source_record_ids": [record["record_id"] for record in packet_records],
                    "source_ids": [record["source_id"] for record in packet_records],
                    "verification_status": "working_deterministic_not_independently_verified",
                    "model_call": None,
                    "cited_excerpt_ids": packet["llm_generated_qualitative_claim"]["cited_excerpt_ids"],
                }
            )

    by_dataset = output_root / "by_dataset" / f"{corpus}.review_packets.jsonl"
    packet_file = output_root / "review_packets.jsonl"
    truth_file = output_root / "private" / "truth_map.private.jsonl"
    write_jsonl(by_dataset, packets)
    write_jsonl(packet_file, packets)
    write_jsonl(truth_file, truth_rows)
    distribution_rows = [
        {
            "corpus_id": corpus,
            "flaw_type": flaw_type,
            "count": Counter(row["known_intended_flaw_type"] for row in truth_rows)[flaw_type],
            "packet_count": len(packets),
        }
        for flaw_type in FLAW_TYPES
    ]
    write_csv(output_root / "distribution_counts.csv", distribution_rows)
    manifest = {
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "corpus_id": corpus,
        "dataset_role": DATASET_ROLES[corpus],
        "files": {
            f"by_dataset/{corpus}.review_packets.jsonl": file_manifest(by_dataset, output_root),
            "distribution_counts.csv": file_manifest(output_root / "distribution_counts.csv", output_root),
            "private/truth_map.private.jsonl": file_manifest(truth_file, output_root),
            "review_packets.jsonl": file_manifest(packet_file, output_root),
        },
        "flaw_types": list(FLAW_TYPES),
        "governance_note": "Contains source text and deterministic generated claims. Not independently verified, privacy-cleared, frozen, or manuscript-eligible.",
        "manifest_schema_version": "warrantroute-working-multicorpus-packet-manifest-v1",
        "packet_count": len(packets),
        "packets_per_flaw": packets_per_flaw,
        "run_id": output_root.name,
        "source_record_count": len(records),
        "selected_source_record_count": len(selected),
        "status": "working_not_manuscript_eligible",
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--packets-per-flaw", type=int, default=20)
    parser.add_argument(
        "--goemotions-all-eligible",
        action="store_true",
        help="Use every eligible GoEmotions train row that fits complete four-excerpt packets.",
    )
    parser.add_argument("--goemotions-min-words", type=int, default=5)
    parser.add_argument("--parlamint-min-words", type=int, default=8)
    parser.add_argument("--corpus", choices=("all", "goemotions", "agyw_focus_groups", "parlamint_gb"), default="all")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Output directory name. Only valid when --corpus selects one corpus.",
    )
    args = parser.parse_args()

    if args.run_id and args.corpus == "all":
        raise ValueError("--run-id is only valid with a single --corpus")
    if args.goemotions_all_eligible and args.corpus != "goemotions":
        raise ValueError("--goemotions-all-eligible is only valid with --corpus goemotions")

    packets_per_flaw = args.packets_per_flaw
    corpus_records: dict[str, list[dict[str, Any]]] = {}
    if args.corpus in {"all", "goemotions"}:
        corpus_records["goemotions"] = goemotions_records(args.goemotions_min_words)
        if args.goemotions_all_eligible:
            packets_per_flaw = len(corpus_records["goemotions"]) // (len(FLAW_TYPES) * 4)
            if packets_per_flaw < 1:
                raise RuntimeError("not_enough_goemotions_records_for_one_complete_packet_per_flaw")
    needed_records = len(FLAW_TYPES) * packets_per_flaw * 4
    if args.corpus in {"all", "agyw_focus_groups"}:
        corpus_records["agyw_focus_groups"] = agyw_records()
    if args.corpus in {"all", "parlamint_gb"}:
        corpus_records["parlamint_gb"] = parlamint_records(needed_records, args.parlamint_min_words)

    manifests = {}
    for corpus, records in corpus_records.items():
        packet_count = len(FLAW_TYPES) * packets_per_flaw
        if args.run_id:
            run_id = args.run_id
        elif corpus == "goemotions" and args.goemotions_all_eligible:
            run_id = "goemotions_train_all_working_v1"
        else:
            run_id = (
                f"{corpus}_dev{packet_count}_working_v1"
                if corpus == "goemotions"
                else f"{corpus}_eval{packet_count}_working_v1"
            )
        output_root = args.storage_root / run_id
        manifests[corpus] = build_bank(corpus, records, output_root, packets_per_flaw)

    print(json.dumps({corpus: {"run_id": item["run_id"], "packet_count": item["packet_count"], "source_record_count": item["source_record_count"]} for corpus, item in manifests.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
