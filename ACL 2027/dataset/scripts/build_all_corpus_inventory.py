#!/usr/bin/env python3
"""Consolidate text-free preparation statistics for every real corpus on disk."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"
OUTPUT = DATASET / "audits" / "all_corpora_20260826"


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def count_words(
    path: Path,
    *,
    eligible_only: bool,
    excluded_source_ids: set[str] | None = None,
) -> tuple[int, int]:
    records = 0
    words = 0
    excluded_source_ids = excluded_source_ids or set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            if eligible_only and not record["quality"]["eligible_for_packet_sampling"]:
                continue
            if record["source_id"] in excluded_source_ids:
                continue
            records += 1
            words += len(record["text"].split())
    return records, words


def build_rows() -> list[dict[str, object]]:
    dreaddit = load(DATASET / "deidentified" / "dreaddit" / "build_report.json")
    agyw = load(DATASET / "deidentified" / "agyw_focus_groups" / "build_report.json")
    casino = load(DATASET / "casino" / "manifests" / "casino_schema_profile.json")
    ami = load(DATASET / "ami_meetings" / "manifests" / "ami_scenario_source_manifest.json")
    kodis = load(DATASET / "audits" / "kodis_20260826" / "aggregate_metrics.json")
    dreaddit_date_quarantine = load(
        DATASET / "audits" / "dreaddit_exact_date_quarantine.json"
    )

    quarantined_dreaddit_sources = {
        match["source_id"] for match in dreaddit_date_quarantine["matches"]
    }

    dreaddit_records, dreaddit_words = count_words(
        DATASET / "deidentified" / "dreaddit" / "records.jsonl",
        eligible_only=True,
        excluded_source_ids=quarantined_dreaddit_sources,
    )
    agyw_records, agyw_words = count_words(
        DATASET / "deidentified" / "agyw_focus_groups" / "records.jsonl", eligible_only=True
    )
    assert dreaddit_records == sum(
        dreaddit_date_quarantine[
            "content_rule_eligible_after_cluster_quarantine"
        ].values()
    ) == 3516
    assert dreaddit_words == 301279
    assert agyw_records == agyw["record_counts"]["eligible_for_packet_sampling"] == 3076

    return [
        {
            "corpus": "Dreaddit",
            "current_role": "development plus in-domain audit",
            "source_units": sum(dreaddit["official_rows"].values()),
            "source_unit_label": "released segments",
            "retained_or_candidate_units": dreaddit_records,
            "candidate_unit_label": "post-quarantine candidate segments",
            "text_count": dreaddit_words,
            "text_count_label": "whitespace-delimited words",
            "machine_preparation": "processed and deterministically validated",
            "human_feedback_boundary": "two-person excerpt/privacy review and study ratings",
            "split_constraint": "official split; preserve post clusters",
        },
        {
            "corpus": "Cache2 (CaCHe)",
            "current_role": "cross-domain confirmatory candidate",
            "source_units": 11,
            "source_unit_label": "focus groups",
            "retained_or_candidate_units": agyw_records,
            "candidate_unit_label": "primary-eligible participant turns",
            "text_count": agyw_words,
            "text_count_label": "whitespace-delimited words",
            "machine_preparation": "processed and deterministically validated",
            "human_feedback_boundary": "participant reconciliation plus two-person excerpt/privacy review and study ratings",
            "split_constraint": "hold out all groups; preserve focus-group and local-speaker clusters",
        },
        {
            "corpus": "KODIS",
            "current_role": "private exploratory dialogue corpus; experimental role unassigned",
            "source_units": kodis["interaction_counts"]["human_human"],
            "source_unit_label": "human-human dyads",
            "retained_or_candidate_units": kodis["transcript_message_count"]["human_human"]["n"],
            "candidate_unit_label": "nonempty human-human dialogues",
            "text_count": kodis["transcript_word_count"]["human_human"]["sum"],
            "text_count_label": "parsed message words",
            "machine_preparation": "private exploratory turn conversion validated; one unsplit lane",
            "human_feedback_boundary": "transcript-semantics confirmation, privacy review, role assignment, and study ratings",
            "split_constraint": "one unsplit role unless provider supplies stable participant linkage",
        },
        {
            "corpus": "CaSiNo",
            "current_role": "source-only dyadic candidate",
            "source_units": casino["top_level"]["dialogue_rows"],
            "source_unit_label": "dialogues",
            "retained_or_candidate_units": casino["chat_logs"]["ordinary_message_entries"],
            "candidate_unit_label": "ordinary messages",
            "text_count": casino["chat_logs"]["ordinary_message_whitespace_words"],
            "text_count_label": "whitespace-delimited words",
            "machine_preparation": "source integrity and schema validated; transcript adapter pending",
            "human_feedback_boundary": "field allowlist, privacy review, role assignment, and study ratings",
            "split_constraint": "one unsplit role unless provider supplies stable participant linkage",
        },
        {
            "corpus": "AMI scenario",
            "current_role": "source-only multiparty candidate",
            "source_units": ami["aggregate_counts"]["scenario_meetings"],
            "source_unit_label": "meetings",
            "retained_or_candidate_units": ami["aggregate_counts"]["segment_elements"],
            "candidate_unit_label": "source speech segments",
            "text_count": ami["aggregate_counts"]["orthographic_elements"]["words"],
            "text_count_label": "orthographic <w> elements",
            "machine_preparation": "source integrity and connected components validated; transcript adapter pending",
            "human_feedback_boundary": "transcript/privacy review, role assignment, and study ratings",
            "split_constraint": "preserve all 35 meeting-speaker connected components",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build_rows()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "corpus_inventory.csv", rows)
    summary = {
        "as_of": "2026-08-26",
        "scope": "aggregate preparation accounting; no experimental outcome is implied",
        "real_corpora_on_disk": len(rows),
        "corpora": rows,
        "machine_complete": ["Dreaddit deterministic processing and exact-date cluster quarantine", "CaCHe deterministic processing", "KODIS private exploratory conversion", "CaSiNo source/schema audit", "AMI source/component audit"],
        "human_feedback_required_for_results": [
            "corpus-specific privacy and excerpt decisions",
            "independent analyst reference spaces and conceptual matches",
            "packet ratings from researchers, qualitative-methods experts, and domain experts",
            "observed review time for matched-budget routing",
            "blinded repair assessments",
        ],
    }
    (OUTPUT / "aggregate_inventory.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result_cells = [
        {"paper_location": "tab:study_summary", "needed_input": "unique raters, packet assignments, exclusions, and review times", "status": "human feedback required"},
        {"paper_location": "tab:artifact_quality_profile", "needed_input": "human ordinal ratings and analyst concept matches", "status": "human feedback required"},
        {"paper_location": "tab:role_sensitivity", "needed_input": "ratings by evaluator group and controlled failure family", "status": "human feedback required"},
        {"paper_location": "tab:routing", "needed_input": "expert decisions and observed expert minutes", "status": "human feedback required"},
        {"paper_location": "tab:repair", "needed_input": "feedback text, revision outputs, and blinded repair judgments", "status": "human feedback required"},
        {"paper_location": "tab:artifact_reliability", "needed_input": "repeated human ratings by evaluator group", "status": "human feedback required"},
        {"paper_location": "tab:transfer_ablation", "needed_input": "frozen router fit after human labels exist", "status": "human feedback required"},
        {"paper_location": "appendix selective-risk versus expert-review-coverage figure", "needed_input": "human serious-error labels, confidence or routing scores, and observed expert minutes", "status": "human feedback required"},
    ]
    write_csv(OUTPUT / "results_cell_status.csv", result_cells)


if __name__ == "__main__":
    main()
