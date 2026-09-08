#!/usr/bin/env python3
"""Build distribution-specific working packet sets from a packet bank.

The outputs copy restricted packet text from the input bank and are therefore
local draft artifacts only. They are designed for sensitivity analyses over
flaw-type prevalence, not for manuscript-ready claims.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_BANK_ROOT = WORKSPACE / "Storage" / "draft_review_packets" / "dreaddit_dev100_working_v1"

FLAW_TYPES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)

PROFILE_COUNTS: dict[str, dict[str, int]] = {
    "balanced_diagnostic_50": {
        "unsupported_evidence": 10,
        "source_concentration": 10,
        "counterevidence_loss": 10,
        "contextual_flattening": 10,
        "unsupported_abstraction": 10,
    },
    "qualitative_paper_expert_skew_60": {
        "unsupported_evidence": 9,
        "source_concentration": 6,
        "counterevidence_loss": 12,
        "contextual_flattening": 15,
        "unsupported_abstraction": 18,
    },
    "methods_review_skew_60": {
        "unsupported_evidence": 9,
        "source_concentration": 12,
        "counterevidence_loss": 18,
        "contextual_flattening": 15,
        "unsupported_abstraction": 6,
    },
    "evidence_audit_skew_60": {
        "unsupported_evidence": 18,
        "source_concentration": 15,
        "counterevidence_loss": 12,
        "contextual_flattening": 9,
        "unsupported_abstraction": 6,
    },
}

PROFILE_PURPOSES = {
    "balanced_diagnostic_50": (
        "Smaller balanced diagnostic set for quick checks with equal flaw prevalence."
    ),
    "qualitative_paper_expert_skew_60": (
        "Expertise-sensitive mix for qualitative or domain papers, emphasizing "
        "abstraction, contextual nuance, and counterevidence."
    ),
    "methods_review_skew_60": (
        "Qualitative-methods review mix emphasizing negative-case loss, context, "
        "and source-balance failures."
    ),
    "evidence_audit_skew_60": (
        "Evidence-audit mix emphasizing unsupported evidence and source "
        "concentration."
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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


def pct(count: int, total: int) -> str:
    return f"{count / total:.4f}" if total else "0.0000"


def summarize_counts(profile_name: str, purpose: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row["known_intended_flaw_type"] for row in rows)
    total = len(rows)
    summary_rows: list[dict[str, Any]] = []
    for flaw_type in FLAW_TYPES:
        count = counts[flaw_type]
        summary_rows.append(
            {
                "profile": profile_name,
                "purpose": purpose,
                "n": total,
                "flaw_type": flaw_type,
                "count": count,
                "proportion": pct(count, total),
            }
        )
    return summary_rows


def select_profile(
    grouped_truth: dict[str, list[dict[str, Any]]],
    counts: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for flaw_type, needed in counts.items():
        available = list(grouped_truth[flaw_type])
        if len(available) < needed:
            raise RuntimeError(f"not_enough_packets:{flaw_type}:{needed}>{len(available)}")
        selected.extend(rng.sample(available, needed))
    selected.sort(key=lambda row: row["packet_id"])
    return selected


def write_profile(
    output_root: Path,
    profile_name: str,
    purpose: str,
    selected_truth: list[dict[str, Any]],
    packets_by_id: dict[str, dict[str, Any]],
    bank_root: Path,
    bank_manifest: dict[str, Any],
    created_at_utc: str,
) -> list[dict[str, Any]]:
    corpus_id = str(bank_manifest.get("corpus_id", "dreaddit"))
    profile_root = output_root / "profiles" / profile_name
    packet_rows = [packets_by_id[row["packet_id"]] for row in selected_truth]
    truth_rows = [dict(row) for row in selected_truth]
    for row in truth_rows:
        row["distribution_profile"] = profile_name
        row["distribution_profile_purpose"] = purpose

    packet_path = profile_root / "review_packets.jsonl"
    by_dataset_path = profile_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"
    truth_path = profile_root / "private" / "truth_map.private.jsonl"
    write_jsonl(packet_path, packet_rows)
    write_jsonl(by_dataset_path, packet_rows)
    write_jsonl(truth_path, truth_rows)

    profile_summary = summarize_counts(profile_name, purpose, truth_rows)
    write_csv(profile_root / "distribution_counts.csv", profile_summary)
    write_json(
        profile_root / "profile_manifest.json",
        {
            "created_at_utc": created_at_utc,
            "derived_from_bank": str(bank_root),
            "derived_from_bank_run_id": bank_manifest.get("run_id"),
            "distribution_profile": profile_name,
            "flaw_counts": {
                row["flaw_type"]: row["count"]
                for row in profile_summary
            },
            "governance_note": (
                "Copies restricted source-text packets from the working bank. "
                "Not independently verified, privacy-cleared, frozen, or manuscript-eligible."
            ),
            "manifest_schema_version": "warrantroute-working-distribution-profile-v1",
            "packet_count": len(packet_rows),
            "purpose": purpose,
            "status": "working_distribution_subset_not_manuscript_eligible",
            "files": {
                "review_packets.jsonl": file_manifest(packet_path, profile_root),
                f"by_dataset/{corpus_id}.review_packets.jsonl": file_manifest(by_dataset_path, profile_root),
                "private/truth_map.private.jsonl": file_manifest(truth_path, profile_root),
                "distribution_counts.csv": file_manifest(profile_root / "distribution_counts.csv", profile_root),
            },
        },
    )
    return profile_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", type=Path, default=DEFAULT_BANK_ROOT)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--random-draws", type=int, default=20)
    parser.add_argument("--random-n", type=int, default=60)
    args = parser.parse_args()

    output_root = args.output_root or args.bank_root / "distribution_experiments"
    packet_path = args.bank_root / "review_packets.jsonl"
    truth_path = args.bank_root / "private" / "truth_map.private.jsonl"
    bank_manifest_path = args.bank_root / "manifest.json"
    bank_manifest = load_json(bank_manifest_path)
    packets = load_jsonl(packet_path)
    truth_rows = load_jsonl(truth_path)
    packets_by_id = {row["packet_id"]: row for row in packets}
    if len(packets_by_id) != len(packets):
        raise RuntimeError("duplicate_packet_ids")
    if {row["packet_id"] for row in truth_rows} - set(packets_by_id):
        raise RuntimeError("truth_packet_missing_from_bank")

    grouped_truth: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in truth_rows:
        grouped_truth[str(row["known_intended_flaw_type"])].append(row)
    if set(grouped_truth) != set(FLAW_TYPES):
        raise RuntimeError("unexpected_flaw_type_set")

    rng = random.Random(args.seed)
    created_at_utc = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    all_summary_rows: list[dict[str, Any]] = []

    for profile_name, counts in PROFILE_COUNTS.items():
        selected = select_profile(grouped_truth, counts, rng)
        all_summary_rows.extend(
            write_profile(
                output_root,
                profile_name,
                PROFILE_PURPOSES[profile_name],
                selected,
                packets_by_id,
                args.bank_root,
                bank_manifest,
                created_at_utc,
            )
        )

    all_truth = list(truth_rows)
    for draw_index in range(1, args.random_draws + 1):
        if len(all_truth) < args.random_n:
            raise RuntimeError("random_n_exceeds_bank")
        selected = rng.sample(all_truth, args.random_n)
        selected.sort(key=lambda row: row["packet_id"])
        profile_name = f"random_unstratified_{args.random_n}_seed_{args.seed}_draw_{draw_index:02d}"
        purpose = (
            "Random unstratified subset from the working bank; records the observed "
            "flaw mix without forcing equal category counts."
        )
        all_summary_rows.extend(
            write_profile(
                output_root,
                profile_name,
                purpose,
                selected,
                packets_by_id,
                args.bank_root,
                bank_manifest,
                created_at_utc,
            )
        )

    write_csv(output_root / "distribution_summary.csv", all_summary_rows)
    write_json(
        output_root / "manifest.json",
        {
            "created_at_utc": created_at_utc,
            "derived_from_bank": str(args.bank_root),
            "derived_from_bank_manifest": str(bank_manifest_path),
            "fixed_profiles": sorted(PROFILE_COUNTS),
            "governance_note": (
                "Each profile directory may contain copied source text in review_packets.jsonl. "
                "Use locally only until governance, privacy review, and verification are complete."
            ),
            "manifest_schema_version": "warrantroute-working-distribution-experiments-v1",
            "random_draw_count": args.random_draws,
            "random_n": args.random_n,
            "seed": args.seed,
            "status": "working_distribution_subsets_not_manuscript_eligible",
            "summary_csv": str(output_root / "distribution_summary.csv"),
        },
    )
    print(output_root)
    print(json.dumps({"profiles": len(PROFILE_COUNTS) + args.random_draws, "summary_rows": len(all_summary_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
