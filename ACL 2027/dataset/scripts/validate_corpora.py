#!/usr/bin/env python3
"""Validate the restricted study copies without printing source text."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = DATASET_ROOT / "deidentified"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_dreaddit() -> dict:
    records = read_jsonl(OUTPUT_ROOT / "dreaddit" / "records.jsonl")
    require(len(records) == 3553, "Dreaddit record count changed")
    ids = [record["record_id"] for record in records]
    require(len(ids) == len(set(ids)), "Dreaddit record IDs are not unique")
    require(all(record["text"].strip() for record in records), "Dreaddit has empty text")

    train = [record for record in records if record["split"] == "development_train"]
    audit = [record for record in records if record["split"] == "in_domain_audit"]
    require(len(train) == 2838 and len(audit) == 715, "Dreaddit split counts changed")
    eligible_train = [record for record in train if record["quality"]["eligible_for_packet_sampling"]]
    eligible_audit = [record for record in audit if record["quality"]["eligible_for_packet_sampling"]]
    require(len(eligible_train) == 2817, "Unexpected eligible Dreaddit train count")
    require(len(eligible_audit) == 715, "Unexpected eligible Dreaddit audit count")
    train_hashes = {record["provenance"]["source_text_sha256"] for record in eligible_train}
    audit_hashes = {record["provenance"]["source_text_sha256"] for record in eligible_audit}
    require(not train_hashes & audit_hashes, "Eligible Dreaddit splits share exact text")

    with (OUTPUT_ROOT / "dreaddit" / "provenance_map.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        provenance = list(csv.DictReader(handle))
    require(len(provenance) == len(records), "Dreaddit provenance map is incomplete")
    train_posts = {
        row["original_post_id"]
        for row in provenance
        if row["source_file"] == "dreaddit-train.csv"
    }
    test_posts = {
        row["original_post_id"]
        for row in provenance
        if row["source_file"] == "dreaddit-test.csv"
    }
    require(not train_posts & test_posts, "Dreaddit splits share original post IDs")
    return {
        "records": len(records),
        "eligible_development_train": len(eligible_train),
        "eligible_in_domain_audit": len(eligible_audit),
        "cross_split_exact_text_overlap_after_quarantine": 0,
        "cross_split_post_overlap": 0,
    }


def validate_agyw() -> dict:
    records = read_jsonl(OUTPUT_ROOT / "agyw_focus_groups" / "records.jsonl")
    require(len(records) == 3944, "AGYW retained record count changed")
    ids = [record["record_id"] for record in records]
    require(len(ids) == len(set(ids)), "AGYW record IDs are not unique")
    require(all(record["text"].strip() for record in records), "AGYW has empty text")
    require(
        all(record["split"] == "heldout_cross_domain_evaluation" for record in records),
        "AGYW split role changed",
    )
    roles = Counter(
        "participant" if record["speaker_id"] is not None else "collective"
        for record in records
    )
    eligible = [record for record in records if record["quality"]["eligible_for_packet_sampling"]]
    require(len(eligible) == 3076, "AGYW eligible turn count changed")
    require(roles == Counter({"participant": 3575, "collective": 369}), "AGYW role counts changed")
    participant_ids = {record["speaker_id"] for record in records if record["speaker_id"]}
    require(len(participant_ids) == 106, "AGYW observed participant-key count changed")
    require(
        all(speaker_id.startswith(source_id) for speaker_id, source_id in (
            (record["speaker_id"], record["source_id"])
            for record in records
            if record["speaker_id"]
        )),
        "An AGYW speaker ID is not scoped to its FGD",
    )
    with (OUTPUT_ROOT / "agyw_focus_groups" / "provenance_map.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        provenance = list(csv.DictReader(handle))
    require(len(provenance) == len(records), "AGYW provenance map is incomplete")
    return {
        "records_retained": len(records),
        "participant_turns": roles["participant"],
        "collective_turns": roles["collective"],
        "eligible_primary_turns": len(eligible),
        "observed_transcript_local_participant_keys": len(participant_ids),
        "reported_source_participants": 107,
    }


def main() -> None:
    result = {
        "agyw_focus_groups": validate_agyw(),
        "dreaddit": validate_dreaddit(),
        "status": "ok",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
