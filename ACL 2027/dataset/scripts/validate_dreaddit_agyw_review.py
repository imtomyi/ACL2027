#!/usr/bin/env python3
"""Validate Dreaddit/AGYW readiness audits and restricted review artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from prepare_dreaddit_agyw_review import (
    CORPORA,
    DATASET_ROOT,
    build_agyw_reconciliation_audit,
    build_dreaddit_exact_date_audit,
    build_review_bundle,
    canonical_jsonl_bytes,
    corpus_config,
    enforce_control_path,
    enforce_runtime_candidate,
    mode,
    prepare_candidate_from_paths,
    read_json_snapshot,
    read_jsonl_snapshot,
    read_records_snapshot,
    require,
    require_private_file,
    sha256_bytes,
    validate_ledger_shape_and_reviews,
    validate_packet_shapes,
)


AGYW_AUDIT_PATH = DATASET_ROOT / "audits" / "agyw_participant_reconciliation.json"
DREADDIT_DATE_AUDIT_PATH = DATASET_ROOT / "audits" / "dreaddit_exact_date_quarantine.json"


def validate_canonical_audits() -> dict[str, Any]:
    dreaddit_config = CORPORA["dreaddit"]
    dreaddit_records, dreaddit_sha = read_records_snapshot(dreaddit_config["records"])
    expected_date_audit = build_dreaddit_exact_date_audit(dreaddit_records, dreaddit_sha)
    actual_date_audit, _ = read_json_snapshot(DREADDIT_DATE_AUDIT_PATH)
    require(actual_date_audit == expected_date_audit, "Dreaddit date-quarantine audit is stale")

    agyw_config = CORPORA["agyw_focus_groups"]
    agyw_build_report, agyw_build_report_sha = read_json_snapshot(
        agyw_config["build_report"]
    )
    source_manifest, source_manifest_sha = read_json_snapshot(agyw_config["source_manifest"])
    expected_reconciliation = build_agyw_reconciliation_audit(
        agyw_build_report,
        agyw_build_report_sha,
        source_manifest,
        source_manifest_sha,
    )
    actual_reconciliation, _ = read_json_snapshot(AGYW_AUDIT_PATH)
    require(actual_reconciliation == expected_reconciliation, "AGYW reconciliation audit is stale")
    return {
        "status": "ok",
        "dreaddit_exact_date_quarantine": {
            "matched_records": actual_date_audit["matched_records"],
            "matched_post_clusters": actual_date_audit["matched_post_clusters"],
            "records_rewritten": False,
            "experiment_use_ready": False,
        },
        "agyw_participant_reconciliation": {
            "observed_transcript_local_speaker_keys": actual_reconciliation[
                "observed_transcript_local_speaker_keys"
            ],
            "reported_source_participants": actual_reconciliation[
                "reported_source_participants"
            ],
            "status": actual_reconciliation["status"],
            "experiment_use_ready": False,
        },
    }


def expected_candidate(args: argparse.Namespace) -> tuple[dict[str, Any], Path, str]:
    control_path = enforce_control_path(args.selection_control)
    candidate_path = enforce_runtime_candidate(args.candidate_manifest, args.corpus)
    candidate, candidate_sha = read_json_snapshot(candidate_path)
    expected = prepare_candidate_from_paths(
        corpus=args.corpus,
        split=args.split,
        requested_clusters=args.clusters,
        sampling_seed=args.seed,
        selection_control_path=control_path,
    )
    require(candidate == expected, "Candidate manifest differs from current inputs/control/seed")
    require(mode(candidate_path.parent) == 0o700, "Candidate directory must be mode 0700")
    require_private_file(candidate_path, "candidate manifest")
    return candidate, candidate_path, candidate_sha


def validate_candidate(args: argparse.Namespace) -> dict[str, Any]:
    candidate, _, _ = expected_candidate(args)
    return {
        "status": "ok",
        "corpus": candidate["corpus"],
        "split": candidate["split"],
        "selected": candidate["selected"],
        "exact_date_quarantine": {
            "clusters": candidate["exact_date_quarantine"]["clusters"],
            "records": candidate["exact_date_quarantine"]["records"],
        },
        "manual_privacy_review_required": True,
        "experiment_use_ready": False,
    }


def validate_ledger(args: argparse.Namespace) -> dict[str, Any]:
    candidate, candidate_path, candidate_sha = expected_candidate(args)
    config, _ = corpus_config(args.corpus, args.split)
    records, records_sha = read_records_snapshot(config["records"])
    require(records_sha == candidate["records_sha256"], "Records changed during validation")
    expected_packets, initial_ledger = build_review_bundle(
        records,
        candidate,
        candidate_file=candidate_path.name,
        candidate_sha256=candidate_sha,
    )

    packet_path = candidate_path.parent / "privacy_review_packets.jsonl"
    ledger_path = candidate_path.parent / "privacy_review_ledger.json"
    require_private_file(packet_path, "privacy review packets")
    require_private_file(ledger_path, "privacy review ledger")
    packets, packet_sha = read_jsonl_snapshot(packet_path)
    ledger, _ = read_json_snapshot(ledger_path)
    require(packets == expected_packets, "Review packets differ from candidate/current records")
    require(packet_sha == sha256_bytes(canonical_jsonl_bytes(expected_packets)), "Packet hash mismatch")
    for key, expected_value in initial_ledger.items():
        if key not in {"status", "entries"}:
            require(ledger.get(key) == expected_value, f"Ledger field {key} changed")
    require(len(ledger.get("entries", [])) == len(initial_ledger["entries"]), "Ledger coverage changed")
    for actual, initial in zip(ledger["entries"], initial_ledger["entries"]):
        for key, expected_value in initial.items():
            if key not in {"reviews", "privacy_review_complete", "permitted_uses"}:
                require(actual.get(key) == expected_value, f"Ledger entry field {key} changed")
    validate_packet_shapes(packets)
    summary = validate_ledger_shape_and_reviews(ledger, packets)
    return {
        "status": "ok",
        "corpus": ledger["corpus"],
        "split": ledger["split"],
        **summary,
        "experiment_use_ready": False,
        "warning": "Privacy-review validation is not external governance clearance.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audits", help="Validate the checked-in text-free readiness audits")
    for name in ("candidate", "ledger"):
        command = subparsers.add_parser(name)
        command.add_argument("--corpus", choices=tuple(CORPORA), required=True)
        command.add_argument("--split", required=True)
        command.add_argument("--clusters", type=int, required=True)
        command.add_argument("--seed", required=True)
        command.add_argument("--selection-control", type=Path, required=True)
        command.add_argument("--candidate-manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.command == "audits":
            result = validate_canonical_audits()
        elif args.command == "candidate":
            result = validate_candidate(args)
        elif args.command == "ledger":
            result = validate_ledger(args)
        else:  # pragma: no cover
            raise ValueError("Unknown command")
        print(json.dumps(result, indent=2, sort_keys=True))
    except (AssertionError, json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        if isinstance(exc, OSError):
            print("Dreaddit/AGYW review validation failed: restricted file operation failed", file=sys.stderr)
        else:
            print(f"Dreaddit/AGYW review validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
