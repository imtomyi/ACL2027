#!/usr/bin/env python3
"""Build a Dreaddit development-only working packet bank."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_RECORDS = WORKSPACE / "dataset" / "deidentified" / "dreaddit" / "records.jsonl"
DEFAULT_STORAGE = WORKSPACE / "Storage" / "draft_review_packets"
FLAW_TYPES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_hash(value: str) -> str:
    return sha256_text(value)[:16]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def eligible_development_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("corpus") == "dreaddit"
        and record.get("split") == "development_train"
        and record.get("quality", {}).get("eligible_for_packet_sampling") is True
    ]


def choose_records(records: list[dict[str, Any]], needed: int) -> list[dict[str, Any]]:
    ordered = sorted(records, key=lambda row: row["record_id"])
    selected: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for record in ordered:
        source_id = record["source_id"]
        if source_id in seen_sources:
            continue
        selected.append(record)
        seen_sources.add(source_id)
        if len(selected) == needed:
            break
    if len(selected) != needed:
        raise RuntimeError("not_enough_unique_development_records")
    return selected


def excerpt(record: dict[str, Any], display_order: int) -> dict[str, Any]:
    strata = record.get("sampling_strata", {})
    return {
        "candidate_role": "cited" if display_order <= 2 else "context",
        "display_order": display_order,
        "excerpt_id": f"EXC_{short_hash(record['record_id'])}",
        "local_context": None,
        "metadata": {
            "split": "development_train",
            "stress_label": strata.get("stress_label"),
            "subreddit": strata.get("community"),
        },
        "source_id": record["source_id"],
        "source_record_id": record["record_id"],
        "speaker_id": record.get("speaker_id"),
        "text": record["text"],
    }


def claim_for(packet_id: str, flaw_type: str, excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    cited = [excerpts[0]["excerpt_id"], excerpts[1]["excerpt_id"]]
    first = excerpts[0]["excerpt_id"]
    third = excerpts[2]["excerpt_id"]
    if flaw_type == "unsupported_evidence":
        claim = "People describe stress as mainly a consequence of workplace deadlines and institutional paperwork."
        explanation = "The claim introduces a specific causal account that is not established by the displayed evidence."
        boundary = ["Other stress contexts in the packet may not fit the workplace-and-paperwork account."]
    elif flaw_type == "source_concentration":
        cited = [first]
        claim = "Across the packet, stress is best understood as a single pattern of urgent health-related self-monitoring."
        explanation = "The synthesis makes a packet-level claim while leaning on one displayed source."
        boundary = ["The other displayed excerpts are available as context but are not substantively integrated."]
    elif flaw_type == "counterevidence_loss":
        claim = "Every displayed source presents stress as constant, severe, and unresolved."
        explanation = "The synthesis suppresses countervailing or boundary cases that should constrain the theme."
        boundary = [f"Context excerpt {third} may limit the all-sources claim."]
    elif flaw_type == "contextual_flattening":
        claim = "The excerpts show the same kind of stress experience with no meaningful contextual differences."
        explanation = "The synthesis collapses distinct local situations into a single undifferentiated theme."
        boundary = ["Differences in speaker situation, stress source, and local context are not preserved."]
    elif flaw_type == "unsupported_abstraction":
        claim = "Stress functions as a generalized rupture in selfhood and social order across the packet."
        explanation = "The synthesis moves to an abstract theoretical category beyond what the displayed context warrants."
        boundary = ["The abstract category is not directly grounded in the displayed wording and context."]
    else:
        raise ValueError(f"unknown flaw type: {flaw_type}")
    return {
        "boundary_conditions": boundary,
        "cited_excerpt_ids": cited,
        "claim": claim,
        "explanation": explanation,
        "model_id": "deterministic_working_packet_builder_v1",
        "theme_name": f"Working {flaw_type.replace('_', ' ')} theme",
    }


def file_manifest(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "path": str(path.relative_to(root)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--packets-per-flaw", type=int, default=5)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    total_packets = len(FLAW_TYPES) * args.packets_per_flaw
    records = eligible_development_records(load_jsonl(args.records))
    selected = choose_records(records, total_packets * 4)
    run_id = args.run_id or f"dreaddit_dev{total_packets}_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    output_root = args.storage_root / run_id
    if output_root.exists() and not args.replace:
        raise RuntimeError("output_exists_use_replace")

    packets: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    index = 0
    for flaw_type in FLAW_TYPES:
        for flaw_index in range(args.packets_per_flaw):
            packet_records = selected[index : index + 4]
            index += 4
            packet_id = f"PKT_{short_hash(run_id + flaw_type + str(flaw_index))}"
            output_id = f"OUT_{short_hash(packet_id)}"
            excerpts = [
                excerpt(record, display_order)
                for display_order, record in enumerate(packet_records, 1)
            ]
            packet = {
                "corpus_id": "dreaddit",
                "dataset_role": "development_only_working_sample; in_domain_audit_excluded",
                "draft_status": "working_development_only_not_manuscript_eligible",
                "flaw_taxonomy": list(FLAW_TYPES),
                "handling": {
                    "contains_source_text": True,
                    "not_for_manuscript_table": True,
                    "restricted_local_only": True,
                    "in_domain_audit_excluded": True,
                },
                "known_intended_flaw_note": "Working deterministic flaw injection for development-only evaluation.",
                "known_intended_flaw_type": flaw_type,
                "llm_generated_qualitative_claim": claim_for(packet_id, flaw_type, excerpts),
                "output_id": output_id,
                "packet_id": packet_id,
                "packet_schema_version": "warrantroute-working-dreaddit-packet-v1",
                "research_question": "How do people describe and contextualize experiences of stress?",
                "review_instruction": "Review whether the qualitative claim is warranted by the displayed source text/context.",
                "source_text_context": excerpts,
            }
            packets.append(packet)
            truth_rows.append(
                {
                    "packet_id": packet_id,
                    "output_id": output_id,
                    "corpus_id": "dreaddit",
                    "known_intended_flaw_type": flaw_type,
                    "source_record_ids": [record["record_id"] for record in packet_records],
                    "verification_status": "working_deterministic_development_only",
                    "model_call": None,
                    "cited_excerpt_ids": packet["llm_generated_qualitative_claim"]["cited_excerpt_ids"],
                }
            )

    by_dataset = output_root / "by_dataset" / "dreaddit.review_packets.jsonl"
    packet_file = output_root / "review_packets.jsonl"
    truth_file = output_root / "private" / "truth_map.private.jsonl"
    write_jsonl(by_dataset, packets)
    write_jsonl(packet_file, packets)
    write_jsonl(truth_file, truth_rows)
    manifest = {
        "manifest_schema_version": "warrantroute-working-dreaddit-dev-packet-manifest-v1",
        "run_id": run_id,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "working_development_only_not_manuscript_eligible",
        "corpus_id": "dreaddit",
        "source_records": str(args.records),
        "source_split": "development_train",
        "excluded_splits": ["in_domain_audit"],
        "packet_count": len(packets),
        "packets_per_flaw": args.packets_per_flaw,
        "flaw_types": list(FLAW_TYPES),
        "source_record_count": len(records),
        "files": {
            "by_dataset/dreaddit.review_packets.jsonl": file_manifest(by_dataset, output_root),
            "review_packets.jsonl": file_manifest(packet_file, output_root),
            "private/truth_map.private.jsonl": file_manifest(truth_file, output_root),
        },
    }
    write_json(output_root / "manifest.json", manifest)
    print(output_root)
    print(json.dumps({"packet_count": len(packets), "source_split": "development_train"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
