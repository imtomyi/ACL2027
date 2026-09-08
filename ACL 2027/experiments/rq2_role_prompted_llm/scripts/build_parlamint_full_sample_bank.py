#!/usr/bin/env python3
"""Build a ParlaMint-GB packet bank sampled from the full usable population.

The output packet files contain source text. They are local working artifacts
for sample-size efficiency checks, not manuscript-ready or release artifacts.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import random
import re
import tarfile
import xml.etree.ElementTree as ET
from collections import Counter, deque
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_ARCHIVE = WORKSPACE / "dataset" / "raw" / "parlamint_gb" / "ParlaMint-GB.tgz"
DEFAULT_STORAGE = WORKSPACE / "Storage" / "draft_review_packets"

FLAW_TYPES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)

RESEARCH_QUESTION = (
    "How do parliamentary speakers frame public issues and policy disagreement "
    "in debate?"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_hash(value: str) -> str:
    return sha256_text(value)[:16]


def normalized_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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


def member_is_session_xml(name: str) -> bool:
    return bool(re.search(r"/ParlaMint-GB_\d{4}-.*\.xml$", name))


def elem_text(elem: ET.Element) -> str:
    segments = []
    for seg in elem.iter():
        if seg.tag.split("}", 1)[-1] == "seg":
            segments.append(normalized_space(" ".join(seg.itertext())))
    if segments:
        return normalized_space(" ".join(item for item in segments if item))
    return normalized_space(" ".join(elem.itertext()))


def record_from_turn(
    elem: ET.Element,
    *,
    source_file: str,
    source_id: str,
    turn_index: int,
    eligible_index: int,
    previous_record_ids: deque[str],
) -> dict[str, Any]:
    year_match = re.search(r"_(\d{4})-", source_id)
    chamber = "commons" if "commons" in source_id else "lords" if "lords" in source_id else "unknown"
    text = elem_text(elem)
    word_count = len(text.split())
    record_id = f"parlamint_gb_full_{eligible_index:07d}"
    return {
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
            "source_file": source_file,
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


def iter_session_records(
    archive_path: Path,
    *,
    min_words: int,
    max_words: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stream the tgz once and keep only reviewer-usable records."""
    prompt_usable: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    chamber_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    word_bucket_counts: Counter[str] = Counter()
    word_counts: list[int] = []

    with tarfile.open(archive_path, "r|gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            counts["tar_file_members"] += 1
            if member.name.endswith(".xml"):
                counts["xml_files"] += 1
            if not member_is_session_xml(member.name):
                continue
            counts["session_xml_files"] += 1
            file_obj = tar.extractfile(member)
            if file_obj is None:
                continue
            root = ET.parse(file_obj).getroot()
            source_id = Path(member.name).stem
            previous_record_ids: deque[str] = deque(maxlen=3)
            turn_index = 0
            for elem in root.iter():
                if elem.tag.split("}", 1)[-1] != "u":
                    continue
                counts["speaker_turns"] += 1
                text = elem_text(elem)
                word_count = len(text.split())
                if word_count < min_words:
                    counts["excluded_below_min_words"] += 1
                    continue
                counts["eligible_min_words"] += 1
                word_counts.append(word_count)
                if word_count > max_words:
                    counts["excluded_above_max_words"] += 1
                    continue
                counts["prompt_usable_records"] += 1
                turn_index += 1
                record = record_from_turn(
                    elem,
                    source_file=member.name,
                    source_id=source_id,
                    turn_index=turn_index,
                    eligible_index=counts["prompt_usable_records"],
                    previous_record_ids=previous_record_ids,
                )
                prompt_usable.append(record)
                chamber = str(record["sampling_strata"]["chamber"])
                year = str(record["sampling_strata"]["year"])
                chamber_counts[chamber] += 1
                year_counts[year] += 1
                if word_count <= 128:
                    word_bucket_counts["008_128"] += 1
                elif word_count <= 256:
                    word_bucket_counts["129_256"] += 1
                elif word_count <= 512:
                    word_bucket_counts["257_512"] += 1
                else:
                    word_bucket_counts["513_max"] += 1
                previous_record_ids.append(record["record_id"])

    word_counts.sort()

    def percentile(p: float) -> int | None:
        if not word_counts:
            return None
        return word_counts[int((len(word_counts) - 1) * p)]

    profile = {
        "chamber_counts_prompt_usable": dict(sorted(chamber_counts.items())),
        "counts": dict(counts),
        "year_counts_prompt_usable": dict(sorted(year_counts.items())),
        "word_bucket_counts_prompt_usable": dict(sorted(word_bucket_counts.items())),
        "word_count_profile_min_words_population": {
            "min": word_counts[0] if word_counts else None,
            "p25": percentile(0.25),
            "median": percentile(0.50),
            "p75": percentile(0.75),
            "p95": percentile(0.95),
            "max": word_counts[-1] if word_counts else None,
        },
    }
    return prompt_usable, profile


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


def claim_for(flaw_type: str, excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    cited = [excerpts[0]["excerpt_id"], excerpts[1]["excerpt_id"]]
    first = excerpts[0]["excerpt_id"]
    third = excerpts[2]["excerpt_id"]
    if flaw_type == "unsupported_evidence":
        claim = (
            "The displayed sources show that policy debate is mainly driven by "
            "institutional procedures and formal paperwork."
        )
        explanation = "The claim introduces a specific causal account not established by the displayed evidence."
        boundary = ["Other displayed sources may not support the paperwork-centered explanation."]
    elif flaw_type == "source_concentration":
        cited = [first]
        claim = "Across the whole packet, policy debate follows one dominant pattern shown by the cited source."
        explanation = "The synthesis makes a packet-level claim while leaning on one displayed source."
        boundary = ["The other displayed excerpts are available but are not substantively integrated."]
    elif flaw_type == "counterevidence_loss":
        claim = "Every displayed source presents the same severe and unresolved version of policy debate."
        explanation = "The synthesis suppresses boundary cases that should constrain the theme."
        boundary = [f"Context excerpt {third} may limit the all-sources claim."]
    elif flaw_type == "contextual_flattening":
        claim = "The excerpts show no meaningful contextual differences in policy debate."
        explanation = "The synthesis collapses distinct local situations into a single undifferentiated theme."
        boundary = ["Differences in chamber, speaker role, issue, and local context are not preserved."]
    elif flaw_type == "unsupported_abstraction":
        claim = "Policy debate functions as a generalized rupture in civic selfhood and social order across the packet."
        explanation = "The synthesis moves to an abstract theoretical category beyond the displayed context."
        boundary = ["The abstract category is not directly grounded in the displayed wording and context."]
    else:
        raise ValueError(f"unknown flaw type: {flaw_type}")
    return {
        "boundary_conditions": boundary,
        "cited_excerpt_ids": cited,
        "claim": claim,
        "explanation": explanation,
        "model_id": "deterministic_working_packet_builder_v3",
        "theme_name": f"Working {flaw_type.replace('_', ' ')} theme",
    }


def balanced_records(records: list[dict[str, Any]], needed: int, seed: int) -> list[dict[str, Any]]:
    if len(records) < needed:
        raise RuntimeError(f"not_enough_prompt_usable_records:{needed}>{len(records)}")
    rng = random.Random(seed)
    selected = rng.sample(records, needed)
    selected.sort(
        key=lambda row: (
            str(row["sampling_strata"].get("year")),
            str(row["sampling_strata"].get("chamber")),
            str(row["source_id"]),
            str(row["record_id"]),
        )
    )
    return selected


def build_bank(
    *,
    records: list[dict[str, Any]],
    output_root: Path,
    packets_per_flaw: int,
    population_profile: dict[str, Any],
    seed: int,
    min_words: int,
    max_words: int,
) -> dict[str, Any]:
    total_packets = len(FLAW_TYPES) * packets_per_flaw
    selected = balanced_records(records, total_packets * 4, seed)
    packets: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    index = 0
    for flaw_type in FLAW_TYPES:
        for flaw_index in range(packets_per_flaw):
            packet_records = selected[index : index + 4]
            index += 4
            packet_id = f"PKT_{short_hash(output_root.name + flaw_type + str(flaw_index))}"
            output_id = f"OUT_{short_hash(packet_id)}"
            excerpts = [excerpt(record, display_order) for display_order, record in enumerate(packet_records, 1)]
            packet = {
                "corpus_id": "parlamint_gb",
                "dataset_role": "heldout_cross_domain_descriptive_working_sample; not_for_training",
                "draft_status": "working_not_manuscript_eligible",
                "flaw_taxonomy": list(FLAW_TYPES),
                "handling": {
                    "contains_source_text": True,
                    "not_for_manuscript_table": True,
                    "restricted_local_only": True,
                },
                "known_intended_flaw_note": "Working deterministic flaw injection for pipeline development.",
                "known_intended_flaw_type": flaw_type,
                "llm_generated_qualitative_claim": claim_for(flaw_type, excerpts),
                "output_id": output_id,
                "packet_id": packet_id,
                "packet_schema_version": "warrantroute-working-parlamint-full-sample-packet-v1",
                "research_question": RESEARCH_QUESTION,
                "review_instruction": "Review whether the qualitative claim is warranted by the displayed source text/context.",
                "source_text_context": excerpts,
            }
            packets.append(packet)
            truth_rows.append(
                {
                    "packet_id": packet_id,
                    "output_id": output_id,
                    "corpus_id": "parlamint_gb",
                    "known_intended_flaw_type": flaw_type,
                    "source_record_ids": [record["record_id"] for record in packet_records],
                    "source_ids": [record["source_id"] for record in packet_records],
                    "verification_status": "working_deterministic_not_independently_verified",
                    "model_call": None,
                    "cited_excerpt_ids": packet["llm_generated_qualitative_claim"]["cited_excerpt_ids"],
                }
            )

    by_dataset = output_root / "by_dataset" / "parlamint_gb.review_packets.jsonl"
    packet_file = output_root / "review_packets.jsonl"
    truth_file = output_root / "private" / "truth_map.private.jsonl"
    write_jsonl(by_dataset, packets)
    write_jsonl(packet_file, packets)
    write_jsonl(truth_file, truth_rows)

    distribution_rows = [
        {
            "corpus_id": "parlamint_gb",
            "flaw_type": flaw_type,
            "count": Counter(row["known_intended_flaw_type"] for row in truth_rows)[flaw_type],
            "packet_count": len(packets),
        }
        for flaw_type in FLAW_TYPES
    ]
    write_csv(output_root / "distribution_counts.csv", distribution_rows)

    selected_chambers = Counter(
        str(excerpt_row["metadata"].get("chamber"))
        for packet in packets
        for excerpt_row in packet["source_text_context"]
    )
    selected_years = Counter(
        str(excerpt_row["metadata"].get("year"))
        for packet in packets
        for excerpt_row in packet["source_text_context"]
    )
    manifest = {
        "balanced_sample_sizes_supported": [25, 50, 75, 100]
        if total_packets >= 100
        else [size for size in [25, 50, 75, 100] if size <= total_packets],
        "corpus_id": "parlamint_gb",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_role": "heldout_cross_domain_descriptive_working_sample; not_for_training",
        "files": {
            "by_dataset/parlamint_gb.review_packets.jsonl": file_manifest(by_dataset, output_root),
            "distribution_counts.csv": file_manifest(output_root / "distribution_counts.csv", output_root),
            "private/truth_map.private.jsonl": file_manifest(truth_file, output_root),
            "review_packets.jsonl": file_manifest(packet_file, output_root),
        },
        "flaw_types": list(FLAW_TYPES),
        "governance_note": "Contains source text and deterministic generated claims. Not independently verified, privacy-cleared, frozen, or manuscript-eligible.",
        "manifest_schema_version": "warrantroute-working-parlamint-full-sample-manifest-v1",
        "packet_count": len(packets),
        "packets_per_flaw": packets_per_flaw,
        "population_profile": population_profile,
        "prompt_usable_filter": {
            "min_words": min_words,
            "max_words": max_words,
            "reason": "Keep four-excerpt reviewer packets inside the local 8192-token context budget.",
        },
        "random_seed": seed,
        "run_id": output_root.name,
        "selected_source_chamber_counts": dict(sorted(selected_chambers.items())),
        "selected_source_record_count": total_packets * 4,
        "selected_source_year_counts": dict(sorted(selected_years.items())),
        "status": "working_not_manuscript_eligible",
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--run-id", default="parlamint_gb_fullsample_eval100_working_v1")
    parser.add_argument("--packets-per-flaw", type=int, default=20)
    parser.add_argument("--min-words", type=int, default=8)
    parser.add_argument("--max-words", type=int, default=800)
    parser.add_argument("--seed", type=int, default=20260901)
    args = parser.parse_args()

    records, profile = iter_session_records(
        args.archive,
        min_words=args.min_words,
        max_words=args.max_words,
    )
    output_root = args.storage_root / args.run_id
    manifest = build_bank(
        records=records,
        output_root=output_root,
        packets_per_flaw=args.packets_per_flaw,
        population_profile=profile,
        seed=args.seed,
        min_words=args.min_words,
        max_words=args.max_words,
    )
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "packet_count": manifest["packet_count"],
                "selected_source_record_count": manifest["selected_source_record_count"],
                "population_counts": manifest["population_profile"]["counts"],
                "output_root": str(output_root),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
