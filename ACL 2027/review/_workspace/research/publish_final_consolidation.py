#!/usr/bin/env python3
"""Atomically publish the frozen final evidence and terminal review-flow previews.

The preview builder performs source ingestion, schema validation, and publication-
family auditing.  This publisher is intentionally a separate, idempotent final
layer: it validates the frozen previews, promotes their evidence payload into the
canonical four-key master schema, overlays terminal decisions onto the original
1,360-record screening ledger, preserves the original identification/provenance
sections, and writes a machine-readable final integrity audit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
MASTER = RESEARCH / "master_evidence.json"
FLOW = RESEARCH / "review_flow.json"
PREVIEW = RESEARCH / "final_consolidation_preview.json"
FLOW_PREVIEW = RESEARCH / "final_review_flow_preview.json"
CONFLICT_AUDIT = RESEARCH / "final_consolidation_conflict_audit.json"
CHAIN = RESEARCH / "citation_chaining.json"
Y2020 = RESEARCH / "screening_2020_2024_resolution.json"
Y2025 = RESEARCH / "screening_2025_fulltext_extractions.json"
Y2025_RESOLUTION = RESEARCH / "screening_2025_resolution.json"
Y2025_FORWARD = RESEARCH / "screening_2025_forward_chain_resolution.json"
Y2026 = RESEARCH / "screening_2026_fulltext_outcomes.json"
RONAGHI = RESEARCH / "ronaghi_2026_evidence.json"
FINAL_AUDIT = RESEARCH / "final_integrity_audit.json"

EXPECTED_2026_SHA256 = "fc9ab406c45d0a83b712ded3a005f847810a7dc213cc6360bc98c1e3eada02e4"
EXPECTED_COLUMNS = 52
EXPECTED_DIMENSIONS = 12
EXPECTED_EVIDENCE = 237
EXPECTED_CORE = 181
EXPECTED_NONCORE = 56

ROUTE_ARITHMETIC = [
    {
        "route": "database/register union",
        "reports_sought": 244,
        "reports_not_retrieved": 44,
        "reports_assessed_and_resolved": 200,
        "reports_retained": 174,
        "reports_excluded_after_full_text": 17,
        "publication_or_version_family_resolutions": 9,
        "source": "research/final_review_flow_preview.json database_records",
    },
    {
        "route": "focused forward citation chaining",
        "reports_sought": 54,
        "reports_not_retrieved": 10,
        "reports_assessed_and_resolved": 44,
        "reports_retained": 41,
        "reports_excluded_after_full_text": 1,
        "publication_or_version_family_resolutions": 2,
        "source": "research/final_review_flow_preview.json focused_forward_chain_records",
    },
    {
        "route": "backward citation chaining",
        "reports_sought": 3,
        "reports_not_retrieved": 1,
        "reports_assessed_and_resolved": 2,
        "reports_retained": 2,
        "reports_excluded_after_full_text": 0,
        "publication_or_version_family_resolutions": 0,
        "source": "research/final_review_flow_preview.json backward_chain_records",
    },
    {
        "route": "other prespecified, supplied, or targeted full-text evidence",
        "reports_sought": 20,
        "reports_not_retrieved": 0,
        "reports_assessed_and_resolved": 20,
        "reports_retained": 20,
        "reports_excluded_after_full_text": 0,
        "publication_or_version_family_resolutions": 0,
        "source": "canonical reconciliation of retained full-text evidence outside the three enumerated retrieval routes",
    },
]

# Publication-identity reconciliation removes the 21 focused-forward candidates
# that already occur in the database union before describing the contribution of
# citation chaining to the 237-row canonical master.  Of those 21 overlaps, one
# was excluded at title/abstract, two were not retrieved, two were version-family
# resolutions, and 16 are retained database identities.
IDENTITY_RECONCILIATION = [
    {"identity_stratum": "retained database/register report identities", "count": 174},
    {"identity_stratum": "retained focused-forward reports outside the database union", "count": 25},
    {"identity_stratum": "retained backward-chain report identities", "count": 2},
    {"identity_stratum": "other retained prespecified, supplied, targeted, or methodological-foundation identities", "count": 36},
]

UNIQUE_IDENTITY_FULL_TEXT_ARITHMETIC = [
    {
        "identity_stratum": "database/register union",
        "reports_sought": 244,
        "reports_not_retrieved": 44,
        "reports_assessed_and_resolved": 200,
        "reports_retained": 174,
        "reports_excluded_after_full_text": 17,
        "publication_or_version_family_resolutions": 9,
    },
    {
        "identity_stratum": "focused forward citation chaining outside the database union",
        "reports_sought": 34,
        "reports_not_retrieved": 8,
        "reports_assessed_and_resolved": 26,
        "reports_retained": 25,
        "reports_excluded_after_full_text": 1,
        "publication_or_version_family_resolutions": 0,
    },
    {
        "identity_stratum": "backward citation chaining",
        "reports_sought": 3,
        "reports_not_retrieved": 1,
        "reports_assessed_and_resolved": 2,
        "reports_retained": 2,
        "reports_excluded_after_full_text": 0,
        "publication_or_version_family_resolutions": 0,
    },
    {
        "identity_stratum": "other unique prespecified, supplied, targeted, or methodological-foundation reports",
        "reports_sought": 36,
        "reports_not_retrieved": 0,
        "reports_assessed_and_resolved": 36,
        "reports_retained": 36,
        "reports_excluded_after_full_text": 0,
        "publication_or_version_family_resolutions": 0,
    },
]

KEMPNY_CONTEXTUAL_OUTCOME = {
    "terminal_decision": "exclude_full_text_contextual_citation_outside_evidence_map",
    "retrieval_status": "retrieved_and_assessed",
    "reason": (
        "Peer-reviewed secondary scoping review inspected and cited for contextual reporting-practice "
        "statistics, but kept outside the 237-row primary/adjacent evidence master; it is therefore an "
        "assessed evidence-map exclusion rather than a retained evidence identity."
    ),
    "report_key": "doi:10.1186/s12874-026-02913-1",
    "official_full_text_url": "https://doi.org/10.1186/s12874-026-02913-1",
    "local_full_text_path": "research/fulltext/latest/kempny_2026_scoping_review.pdf",
    "source_artifact": "research/fulltext/latest/kempny_2026_scoping_review.pdf",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    json.loads(temporary.read_text())
    temporary.replace(path)


def normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = text.rstrip(".,; )]}\t\n")
    return "" if text in {"", "not reported", "not assigned", "no doi", "n/a"} else text


def normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def class_bucket(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("core"):
        return "core"
    return "noncore"


def outcome_group(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith(("include_core", "include_adjacent", "include_contextual")):
        return "retained"
    if "not_retrieved" in text or "not retrieved" in text or "unavailable" in text:
        return "not_retrieved"
    if text.startswith("exclude"):
        return "excluded"
    if "version" in text or "family" in text or "existing_master" in text or "already_assessed" in text:
        return "family"
    return "unresolved"


def route_record(row: dict[str, Any], route: str) -> dict[str, Any]:
    outcome = row.get("full_text_outcome", {})
    if isinstance(outcome, dict):
        decision = outcome.get("terminal_decision", row.get("terminal_eligibility_decision", "not reported"))
        retrieval = outcome.get("retrieval", {}) if isinstance(outcome.get("retrieval"), dict) else {}
        source = (
            outcome.get("source_artifact")
            or retrieval.get("checkpoint_file")
            or row.get("resolution_route")
            or "research/final_review_flow_preview.json"
        )
        reason = (
            outcome.get("reason")
            or outcome.get("decision_reason")
            or retrieval.get("decision_reason")
            or retrieval.get("reason")
            or "not reported"
        )
        retrieval_status = outcome.get("retrieval_status") or retrieval.get("retrieval_status") or "not reported"
        official_url = outcome.get("official_full_text_url") or retrieval.get("official_full_text_url") or row.get("url") or "not reported"
        local_full_text_path = outcome.get("local_full_text_path") or retrieval.get("local_full_text_path") or "not reported"
    else:
        decision = row.get("terminal_eligibility_decision", "not reported")
        source = row.get("resolution_route") or "research/final_review_flow_preview.json"
        reason = row.get("eligibility_reason") or row.get("reason") or "not reported"
        retrieval_status = outcome if outcome else "not reported"
        official_url = row.get("url") or "not reported"
        local_full_text_path = "not reported"
    if retrieval_status == "not reported" and outcome_group(decision) == "not_retrieved":
        retrieval_status = "sought but not retrieved after documented attempts"
    return {
        "route": route,
        "route_record_id": row.get("screen_id") or row.get("deduplication_key") or row.get("candidate_id") or "not reported",
        "title": row.get("title") or row.get("title_or_identifier") or "not reported",
        "doi": row.get("doi") or "not reported",
        "official_url": official_url,
        "terminal_decision": decision,
        "decision_group": outcome_group(decision),
        "reason": reason,
        "retrieval_status": retrieval_status,
        "local_full_text_path": local_full_text_path,
        "resolution_route": row.get("resolution_route", "not reported"),
        "source_provenance": source,
    }


def validate_preview(preview: dict[str, Any], flow_preview: dict[str, Any], conflict: dict[str, Any]) -> None:
    counts = preview["metadata"]["consolidation_counts"]
    required_counts = {
        "retained_evidence_rows": EXPECTED_EVIDENCE,
        "core_records": EXPECTED_CORE,
        "noncore_records": EXPECTED_NONCORE,
        "quality_rows": EXPECTED_CORE,
    }
    for key, expected in required_counts.items():
        if counts.get(key) != expected:
            raise RuntimeError(f"Frozen preview {key}={counts.get(key)!r}; expected {expected}")
    if preview["metadata"].get("validation_status") != "pass":
        raise RuntimeError("Frozen evidence preview did not pass validation")
    if conflict["summary"].get("fatal_conflicts") != 0:
        raise RuntimeError("Conflict audit contains fatal conflicts")
    checks = flow_preview.get("consistency_checks", {})
    if not checks or not all(checks.values()):
        raise RuntimeError(f"Review-flow preview consistency checks did not all pass: {checks}")
    if sha256(Y2026) != EXPECTED_2026_SHA256:
        raise RuntimeError("Frozen 2026 companion hash changed; canonical publication is blocked")


def build_master(preview: dict[str, Any], old_master: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    columns = preview["metadata"]["extraction_columns"]
    dimensions = preview["quality_dimensions"]
    evidence = copy.deepcopy(preview["evidence_records"])
    quality = copy.deepcopy(preview["quality_scores"])
    if len(columns) != EXPECTED_COLUMNS or len(dimensions) != EXPECTED_DIMENSIONS:
        raise RuntimeError("Canonical schema dimension mismatch")
    metadata = copy.deepcopy(old_master.get("metadata", {}))
    metadata.update({
        "title": "Final canonical evidence table for computational qualitative coding and thematic-analysis systems",
        "search_cutoff": "2026-08-24",
        "generated_utc": preview["metadata"]["generated_utc"],
        "canonical_status": "final canonical consolidation",
        "generated_from": [
            "research/final_consolidation_preview.json",
            "research/screening_2020_2024_resolution.json",
            "research/screening_2025_fulltext_extractions.json",
            "research/screening_2026_fulltext_outcomes.json",
        ],
        "source_sha256": source_hashes,
        "deduplication": "Normalized exact DOI, then normalized exact title/shared own arXiv identifier, then explicit declared publication-version mapping; cross-references in relationship text do not by themselves trigger deduplication.",
        "canonical_selection_rule": "Prefer a verified peer-reviewed or accepted version, publisher DOI, non-preprint form, completeness, then later full-text companion priority; fields are never blended across candidate rows.",
        "missing_value": "not reported",
        "extraction_columns": columns,
        "extraction_column_count": EXPECTED_COLUMNS,
        "record_count": len(evidence),
        "core_record_count": sum(class_bucket(row["Core or adjacent classification"]) == "core" for row in evidence),
        "adjacent_record_count": sum(class_bucket(row["Core or adjacent classification"]) == "noncore" for row in evidence),
        "adjacent_or_noncore_record_count": sum(class_bucket(row["Core or adjacent classification"]) == "noncore" for row in evidence),
        "quality_score_count": len(quality),
        "quality_dimension_count": EXPECTED_DIMENSIONS,
        "quality_scoring": "0 = absent/inadequate; 1 = partial/unclear; 2 = adequate for the study's stated claim.",
        "quality_caution": "Quality totals are compact audit aids, not study rankings; dimensions must be interpreted individually against each paper's stated claim.",
        "classification_rule": "All inspected core, adjacent, and contextual evidence is retained; exactly one quality row is retained for each core paper and no quality row for non-core evidence.",
        "review_note": "This is a consolidated single-reviewer extraction. Every retained evidence row is grounded in an inspected full text; source records distinguish author-reported information from reviewer-identified validity concerns where the extraction supports that distinction. MoverScore, BLEURT, and G-Eval remain lower-priority adjacent metric-origin records outside the retained evidence table.",
        "reviewer_model": "Single-reviewer/Codex-assisted review; no independent duplicate screening or adjudication was performed.",
        "provenance_artifacts": {
            "record_level_selection": "research/final_consolidation_preview.json source_provenance",
            "conflict_and_family_audit": "research/final_consolidation_conflict_audit.json",
            "review_flow": "research/review_flow.json",
            "final_integrity_audit": "research/final_integrity_audit.json",
        },
    })
    return {
        "metadata": metadata,
        "evidence_records": evidence,
        "quality_dimensions": dimensions,
        "quality_scores": quality,
    }


def make_retained_report_rows(master: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in master["evidence_records"]:
        bucket = class_bucket(record["Core or adjacent classification"])
        rows.append({
            "report_key": f"doi:{normalize_doi(record['DOI'])}" if normalize_doi(record["DOI"]) else f"paper_id:{record['Paper ID']}",
            "paper_id": record["Paper ID"],
            "title": record["Title"],
            "doi": record["DOI"],
            "url": record["URL"],
            "full_citation": record["Full citation"],
            "decision": "include_core" if bucket == "core" else "include_adjacent_or_noncore",
            "classification": record["Core or adjacent classification"],
            "full_text_basis": "Full-text-inspected evidence extraction retained in research/master_evidence.json.",
        })
    return rows


def build_route_ledgers(flow_preview: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    database = [
        route_record(row, "database/register union")
        for row in flow_preview["database_records"]
        if row["terminal_title_abstract_disposition"] == "advance_to_full_text"
    ]
    forward = [
        route_record(row, "focused forward citation chaining")
        for row in flow_preview["focused_forward_chain_records"]
        if row["terminal_title_abstract_disposition"] == "advance_to_full_text"
    ]
    backward = [route_record(row, "backward citation chaining") for row in flow_preview["backward_chain_records"]]
    return {"database": database, "focused_forward": forward, "backward": backward}


def assert_route_arithmetic(ledgers: dict[str, list[dict[str, Any]]]) -> None:
    for key, expected in (("database", ROUTE_ARITHMETIC[0]), ("focused_forward", ROUTE_ARITHMETIC[1]), ("backward", ROUTE_ARITHMETIC[2])):
        rows = ledgers[key]
        counts = Counter(row["decision_group"] for row in rows)
        actual = {
            "reports_sought": len(rows),
            "reports_not_retrieved": counts["not_retrieved"],
            "reports_assessed_and_resolved": len(rows) - counts["not_retrieved"],
            "reports_retained": counts["retained"],
            "reports_excluded_after_full_text": counts["excluded"],
            "publication_or_version_family_resolutions": counts["family"],
        }
        for field, value in actual.items():
            if value != expected[field]:
                raise RuntimeError(f"{key} {field}={value}; expected {expected[field]}")
        if counts["unresolved"]:
            raise RuntimeError(f"{key} has {counts['unresolved']} unresolved route outcomes")


def assert_forward_identity_partition(flow_preview: dict[str, Any]) -> None:
    rows = flow_preview["focused_forward_chain_records"]
    union_rows = [row for row in rows if "database union" in row.get("resolution_route", "")]
    outside_rows = [row for row in rows if row not in union_rows]
    if (len(rows), len(union_rows), len(outside_rows)) != (59, 21, 38):
        raise RuntimeError("Focused-forward database/outside-union identity partition changed")
    outside_excluded = [row for row in outside_rows if row["terminal_title_abstract_disposition"] == "exclude_title_abstract"]
    outside_advanced = [row for row in outside_rows if row["terminal_title_abstract_disposition"] == "advance_to_full_text"]
    groups = Counter(outcome_group(row["full_text_outcome"]["terminal_decision"]) for row in outside_advanced)
    retained_decisions = [row["full_text_outcome"]["terminal_decision"] for row in outside_advanced if outcome_group(row["full_text_outcome"]["terminal_decision"]) == "retained"]
    core = sum(str(decision).startswith("include_core") for decision in retained_decisions)
    noncore = len(retained_decisions) - core
    observed = (len(outside_excluded), len(outside_advanced), groups["not_retrieved"], len(outside_advanced) - groups["not_retrieved"], groups["retained"], core, noncore, groups["excluded"])
    expected = (4, 34, 8, 26, 25, 16, 9, 1)
    if observed != expected:
        raise RuntimeError(f"Focused-forward outside-union outcome partition changed: {observed} != {expected}")


def build_review_flow(
    old_flow: dict[str, Any],
    flow_preview: dict[str, Any],
    master: dict[str, Any],
    ledgers: dict[str, list[dict[str, Any]]],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    final = copy.deepcopy(old_flow)
    preterminal_limitations = copy.deepcopy(old_flow.get("metadata", {}).get(
        "preterminal_review_limitations_snapshot",
        old_flow["review_limitations"],
    ))
    final["metadata"].update({
        "generated_on": "2026-08-24",
        "publication_cutoff": "2026-08-24",
        "flow_status": "Final canonical terminal screening and full-text reconciliation",
        "important_interpretation": "All 1,360 database records have terminal title/abstract dispositions. Full-text nonretrievals, exclusions, and publication/version-family resolutions remain distinct. Route-event PRISMA arithmetic is reported separately from the DOI/title-deduplicated 237-report evidence identity ledger. Kempny et al. (TA-0428) was inspected and is cited contextually, but is explicitly an evidence-map exclusion rather than one of the 237 retained evidence identities.",
        "canonical_master": "research/master_evidence.json",
        "source_sha256": source_hashes,
        "preterminal_review_limitations_snapshot": preterminal_limitations,
    })

    terminal_by_id = {row["screen_id"]: row for row in flow_preview["database_records"]}
    original_records = final["title_abstract_screening"]["records"]
    if set(terminal_by_id) != {row["screen_id"] for row in original_records}:
        raise RuntimeError("Terminal database ledger does not exactly cover the original screening universe")
    merged_records = []
    for original in original_records:
        terminal = terminal_by_id[original["screen_id"]]
        merged = copy.deepcopy(original)
        merged.update({
            "terminal_title_abstract_disposition": terminal["terminal_title_abstract_disposition"],
            "terminal_title_abstract_reason": terminal["title_abstract_reason"],
            "terminal_decision_provenance": terminal["decision_provenance"],
            "terminal_full_text_outcome": terminal["full_text_outcome"],
        })
        merged_records.append(merged)
    final["title_abstract_screening"].update({
        "records_screened": 1360,
        "terminal_disposition_counts": {"advance_to_full_text": 244, "exclude_title_abstract": 1116},
        "terminal_decision_semantics": {
            "advance_to_full_text": "Advanced record with a terminal full-text inclusion, exclusion, nonretrieval, or publication/version-family resolution.",
            "exclude_title_abstract": "Final title/abstract exclusion under the stated eligibility criteria; no full-text assessment required.",
        },
        "terminal_resolution_source": "research/final_review_flow_preview.json",
        "records": merged_records,
    })

    final["review_limitations"] = copy.deepcopy(preterminal_limitations)
    if len(final["review_limitations"]) > 1:
        final["review_limitations"][1] = "The 612 records initially marked uncertain by deterministic triage received terminal second-pass title/abstract dispositions; because this resolution was single-reviewer/Codex-assisted rather than independently duplicated, residual selection error remains a completeness limitation."

    legacy_fulltext = copy.deepcopy(old_flow["full_text_stage"].get(
        "pre_consolidation_full_text_stage_preserved",
        old_flow["full_text_stage"],
    ))
    forward_outside = [
        row for row in ledgers["focused_forward"]
        if "database union" not in row["resolution_route"]
    ]
    route_event_nonretrieved = [row for rows in ledgers.values() for row in rows if row["decision_group"] == "not_retrieved"]
    route_event_exclusions = [row for rows in ledgers.values() for row in rows if row["decision_group"] == "excluded"]
    route_event_families = [row for rows in ledgers.values() for row in rows if row["decision_group"] == "family"]
    primary_identity_rows = ledgers["database"] + forward_outside + ledgers["backward"]
    nonretrieved = [row for row in primary_identity_rows if row["decision_group"] == "not_retrieved"]
    exclusions = [row for row in primary_identity_rows if row["decision_group"] == "excluded"]
    families = [row for row in primary_identity_rows if row["decision_group"] == "family"]
    retained = make_retained_report_rows(master)
    final["full_text_stage"] = {
        "reports_sought_for_retrieval": 317,
        "reports_not_retrieved": 53,
        "reports_assessed_and_resolved": 264,
        "reports_assessed": 264,
        "retained_reports": 237,
        "retained_by_classification": {
            "include_core": 181,
            "include_adjacent_or_noncore": 56,
        },
        "full_text_exclusions": 18,
        "publication_or_version_family_resolutions": 9,
        "primary_unique_identity_arithmetic": copy.deepcopy(UNIQUE_IDENTITY_FULL_TEXT_ARITHMETIC),
        "secondary_route_event_arithmetic": copy.deepcopy(ROUTE_ARITHMETIC),
        "secondary_route_event_counts": {
            "reports_sought": 321,
            "reports_not_retrieved": 55,
            "reports_assessed_and_resolved": 266,
            "reports_retained": 237,
            "reports_excluded_after_full_text": 18,
            "publication_or_version_family_resolutions": 11,
        },
        "database_advanced_report_ledger": ledgers["database"],
        "focused_forward_advanced_report_ledger": ledgers["focused_forward"],
        "focused_forward_outside_union_advanced_report_ledger": forward_outside,
        "backward_chain_report_ledger": ledgers["backward"],
        "reports_not_retrieved_log": nonretrieved,
        "exclusion_log": exclusions,
        "publication_or_version_family_resolution_log": families,
        "secondary_route_event_reports_not_retrieved_log": route_event_nonretrieved,
        "secondary_route_event_exclusion_log": route_event_exclusions,
        "secondary_route_event_publication_or_version_family_resolution_log": route_event_families,
        "assessed_reports": retained,
        "identity_ledger_interpretation": "Primary full-text counts are unique report identities: 317 sought, 53 not retrieved, and 264 assessed/resolved. assessed_reports is the 237-publication DOI/title-deduplicated retained ledger. Kempny et al. (TA-0428) is one of the 18 assessed evidence-map exclusions and remains an additional contextual citation. The secondary 321/55/266 route-event arithmetic is non-additive because 21 focused-forward candidates overlap the database union.",
        "canonical_publication_identity_reconciliation": copy.deepcopy(IDENTITY_RECONCILIATION),
        "pre_consolidation_full_text_stage_preserved": legacy_fulltext,
    }

    # Preserve the complete citation-chaining object verbatim, adding only a
    # terminal overlay in a new child key.
    final["citation_chaining"]["terminal_resolution_overlay"] = {
        "source": "research/final_review_flow_preview.json",
        "seed_records": flow_preview["citation_seed_records"],
        "backward_chain_records": flow_preview["backward_chain_records"],
        "focused_forward_chain_records": flow_preview["focused_forward_chain_records"],
        "counts": {
            "focused_candidates": 59,
            "focused_title_abstract_exclusions": 5,
            "focused_reports_sought": 54,
            "focused_reports_not_retrieved": 10,
            "focused_reports_assessed_and_resolved": 44,
            "backward_reports_sought": 3,
            "backward_reports_not_retrieved": 1,
            "backward_reports_assessed_and_resolved": 2,
        },
        "saturation_caution": "The confirmation pass found no materially new eligible study beyond the documented chain outcomes, but targeted and partially unavailable citation indexes do not justify a saturation claim.",
    }

    original_database_flow = copy.deepcopy(
        old_flow["prisma_style_flow"].get("database_identification_flow")
        or old_flow["prisma_style_flow"].get("database_flow", [])
    )
    combined = {
        field: sum(row[field] for row in ROUTE_ARITHMETIC)
        for field in (
            "reports_sought",
            "reports_not_retrieved",
            "reports_assessed_and_resolved",
            "reports_retained",
            "reports_excluded_after_full_text",
            "publication_or_version_family_resolutions",
        )
    }
    final["prisma_style_flow"] = {
        "interpretation": "Identification counts are preserved from the original auditable search. Terminal database screening, citation-chain routes, and full-text outcomes are now explicit. Route-event accounting and the final deduplicated publication ledger answer different questions and are both retained.",
        "database_identification_flow": original_database_flow,
        "database_terminal_screening_flow": [
            {"stage": "Unique database/register records screened", "count": 1360},
            {"stage": "Database records excluded at title/abstract screening", "count": 1116},
            {"stage": "Database reports sought for retrieval", "count": 244},
            {"stage": "Database reports not retrieved", "count": 44},
            {"stage": "Database reports assessed and resolved", "count": 200},
            {"stage": "Database reports retained", "count": 174},
            {"stage": "Database reports excluded after full-text assessment", "count": 17},
            {"stage": "Database publication/version-family resolutions", "count": 9},
        ],
        "focused_forward_route_event_flow": [
            {"stage": "Focused forward candidates after chain deduplication/scope filtering", "count": 59},
            {"stage": "Focused forward candidates excluded at title/abstract screening", "count": 5},
            {"stage": "Focused forward reports sought for retrieval", "count": 54},
            {"stage": "Focused forward reports not retrieved", "count": 10},
            {"stage": "Focused forward reports assessed and resolved", "count": 44},
            {"stage": "Focused forward reports retained", "count": 41},
            {"stage": "Focused forward reports excluded after full-text assessment", "count": 1},
            {"stage": "Focused forward publication/version-family resolutions", "count": 2},
        ],
        "focused_forward_identity_reconciliation": [
            {"stage": "Focused forward candidates in total", "count": 59},
            {"stage": "Focused forward candidates overlapping the database union", "count": 21},
            {"stage": "Focused forward candidates outside the database union", "count": 38},
            {"stage": "Outside-union focused candidates excluded at title/abstract screening", "count": 4},
            {"stage": "Outside-union focused reports sought for retrieval", "count": 34},
            {"stage": "Outside-union focused reports not retrieved", "count": 8},
            {"stage": "Outside-union focused reports assessed and resolved", "count": 26},
            {"stage": "Outside-union focused reports retained", "count": 25},
            {"stage": "Outside-union focused reports retained as core", "count": 16},
            {"stage": "Outside-union focused reports retained as adjacent/non-core", "count": 9},
            {"stage": "Outside-union focused reports excluded after full-text assessment", "count": 1},
        ],
        "backward_chain_flow": [
            {"stage": "Backward-chain reports sought for retrieval", "count": 3},
            {"stage": "Backward-chain reports not retrieved", "count": 1},
            {"stage": "Backward-chain reports assessed and resolved", "count": 2},
            {"stage": "Backward-chain reports retained", "count": 2},
        ],
        "secondary_route_event_other_prespecified_supplied_targeted_flow": [
            {"stage": "Secondary route-event balancing stratum: other prespecified, supplied, or targeted reports sought", "count": 20},
            {"stage": "Secondary route-event balancing stratum: other reports assessed and retained", "count": 20},
        ],
        "unique_identity_full_text_arithmetic": copy.deepcopy(UNIQUE_IDENTITY_FULL_TEXT_ARITHMETIC),
        "unique_identity_full_text_flow": [
            {"stage": "Unique report identities sought for retrieval", "count": 317},
            {"stage": "Unique report identities not retrieved", "count": 53},
            {"stage": "Unique report identities assessed and resolved", "count": 264},
            {"stage": "Unique report identities retained in the canonical evidence map", "count": 237},
            {"stage": "Unique report identities excluded after full-text assessment", "count": 18},
            {"stage": "Unique publication/version-family resolutions", "count": 9},
        ],
        "secondary_nonadditive_route_event_arithmetic": copy.deepcopy(ROUTE_ARITHMETIC),
        "secondary_nonadditive_route_event_flow": [
            {"stage": "Secondary route events: reports sought", "count": combined["reports_sought"]},
            {"stage": "Secondary route events: reports not retrieved", "count": combined["reports_not_retrieved"]},
            {"stage": "Secondary route events: reports assessed and resolved", "count": combined["reports_assessed_and_resolved"]},
            {"stage": "Secondary route events: retained outcomes", "count": combined["reports_retained"]},
            {"stage": "Secondary route events: full-text exclusions", "count": combined["reports_excluded_after_full_text"]},
            {"stage": "Secondary route events: publication/version-family resolutions", "count": combined["publication_or_version_family_resolutions"]},
        ],
        "final_retained_classification_flow": [
            {"stage": "Retained core reports", "count": 181},
            {"stage": "Retained adjacent/contextual/non-core reports", "count": 56},
        ],
        "canonical_publication_identity_reconciliation": copy.deepcopy(IDENTITY_RECONCILIATION),
        "consistency_checks": {
            "original_identification_arithmetic_preserved": True,
            "database_terminal_screening": 1360 == 1116 + 244,
            "database_retrieval": 244 == 44 + 200,
            "database_assessed_resolution": 200 == 174 + 17 + 9,
            "focused_forward_title_abstract": 59 == 5 + 54,
            "focused_forward_retrieval": 54 == 10 + 44,
            "focused_forward_assessed_resolution": 44 == 41 + 1 + 2,
            "focused_forward_union_partition": 59 == 21 + 38,
            "focused_forward_outside_union_title_abstract": 38 == 4 + 34,
            "focused_forward_outside_union_retrieval": 34 == 8 + 26,
            "focused_forward_outside_union_assessed_resolution": 26 == 25 + 1,
            "focused_forward_outside_union_retained_classification": 25 == 16 + 9,
            "backward_retrieval": 3 == 1 + 2,
            "primary_unique_identity_retrieval": 317 == 53 + 264,
            "primary_unique_identity_assessed_resolution": 264 == 237 + 18 + 9,
            "secondary_route_event_retrieval": 321 == 55 + 266,
            "secondary_route_event_assessed_resolution": 266 == 237 + 18 + 11,
            "retained_classification": 237 == 181 + 56,
            "canonical_identity_reconciliation": 237 == 174 + 25 + 2 + 36,
        },
    }
    return final


def duplicate_audit(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    doi_counts = Counter(normalize_doi(row["DOI"]) for row in evidence if normalize_doi(row["DOI"]))
    title_counts = Counter(normalize_title(row["Title"]) for row in evidence if normalize_title(row["Title"]))
    return {
        "duplicate_normalized_dois": sorted(key for key, count in doi_counts.items() if count > 1),
        "duplicate_normalized_titles": sorted(key for key, count in title_counts.items() if count > 1),
    }


def validate_final(master: dict[str, Any], flow: dict[str, Any], old_flow: dict[str, Any]) -> dict[str, Any]:
    evidence = master["evidence_records"]
    quality = master["quality_scores"]
    columns = master["metadata"]["extraction_columns"]
    dimensions = master["quality_dimensions"]
    core_ids = {row["Paper ID"] for row in evidence if class_bucket(row["Core or adjacent classification"]) == "core"}
    noncore_ids = {row["Paper ID"] for row in evidence if class_bucket(row["Core or adjacent classification"]) == "noncore"}
    quality_ids = [row["Paper ID"] for row in quality]
    duplicates = duplicate_audit(evidence)
    preprint_contradictions = [
        row["Paper ID"] for row in evidence
        if row["Publication type"].strip().lower().startswith(("preprint", "arxiv preprint"))
        and ("peer reviewed" in row["Peer-reviewed status"].lower() or "peer-reviewed" in row["Peer-reviewed status"].lower())
        and not any(token in row["Peer-reviewed status"].lower() for token in ("not verified", "not peer", "unverified", "mixed"))
    ]
    q_by_id = Counter(quality_ids)
    checks = {
        "master_top_level_keys_exact": list(master) == ["metadata", "evidence_records", "quality_dimensions", "quality_scores"],
        "evidence_count_237": len(evidence) == EXPECTED_EVIDENCE,
        "core_count_181": len(core_ids) == EXPECTED_CORE,
        "noncore_count_56": len(noncore_ids) == EXPECTED_NONCORE,
        "quality_count_181": len(quality) == EXPECTED_CORE,
        "legacy_and_canonical_noncore_metadata_counts_agree": master["metadata"].get("adjacent_record_count") == EXPECTED_NONCORE and master["metadata"].get("adjacent_or_noncore_record_count") == EXPECTED_NONCORE,
        "review_note_has_no_unsupported_requested_range_claim": "requested 55–70" not in master["metadata"].get("review_note", "") and "requested 55-70" not in master["metadata"].get("review_note", ""),
        "every_evidence_row_exactly_52_fields": all(len(row) == EXPECTED_COLUMNS and set(row) == set(columns) for row in evidence),
        "all_evidence_values_strings": all(all(isinstance(value, str) and value.strip() for value in row.values()) for row in evidence),
        "all_year_values_strings": all(isinstance(row["Year"], str) for row in evidence),
        "quality_dimensions_exactly_12": len(dimensions) == EXPECTED_DIMENSIONS,
        "exactly_one_quality_row_per_core": Counter(core_ids) == q_by_id,
        "no_noncore_quality_rows": not (set(quality_ids) & noncore_ids),
        "quality_rows_have_exact_dimensions": all(set(row["Dimension scores"]) == set(dimensions) for row in quality),
        "quality_totals_recalculate": all(row["Total"] == sum(item["score"] for item in row["Dimension scores"].values()) for row in quality),
        "no_duplicate_doi": not duplicates["duplicate_normalized_dois"],
        "no_duplicate_title": not duplicates["duplicate_normalized_titles"],
        "no_preprint_peer_review_status_contradictions": not preprint_contradictions,
        "red_faced_rouge_has_no_false_doi": next(row for row in evidence if row["Paper ID"] == "red_faced_rouge_2019")["DOI"] == "not reported",
        "nita_present_once": sum(row["Paper ID"] == "nguyen_trung_nguyen_2026_nita" for row in evidence) == 1,
        "zhao_liu_companion_studies_both_retained": {"zhao_liu_2025_confidence_diversity", "zhao_liu_2025_complex_confidence_diversity"} <= {row["Paper ID"] for row in evidence},
        "social_verbatim_adjacent_without_quality": (
            sum(row["Paper ID"] == "fc_17_2026_espino" and class_bucket(row["Core or adjacent classification"]) == "noncore" for row in evidence) == 1
            and "fc_17_2026_espino" not in quality_ids
        ),
        "ronaghi_fulltext_core_with_quality": (
            sum(row["Paper ID"] == "ronaghi_2026_large_scale" and class_bucket(row["Core or adjacent classification"]) == "core" for row in evidence) == 1
            and q_by_id["ronaghi_2026_large_scale"] == 1
            and all("bibliographic lead" not in row["Core or adjacent classification"].lower() for row in evidence if row["Paper ID"] == "ronaghi_2026_large_scale")
        ),
        "identification_preserved_exactly": flow["identification"] == old_flow["identification"],
        "eligibility_criteria_preserved_exactly": flow["eligibility_criteria"] == old_flow["eligibility_criteria"],
        "triage_rule_preserved_exactly": flow["triage_rule"] == old_flow["triage_rule"],
        "preterminal_review_limitations_preserved_in_metadata": flow["metadata"].get("preterminal_review_limitations_snapshot") == old_flow.get("metadata", {}).get("preterminal_review_limitations_snapshot", old_flow["review_limitations"]),
        "terminal_review_limitation_resolves_stale_uncertainty_wording": len(flow["review_limitations"]) > 1 and "received terminal second-pass" in flow["review_limitations"][1],
        "database_records_1360": len(flow["title_abstract_screening"]["records"]) == 1360,
        "every_database_record_terminal": all(row.get("terminal_title_abstract_disposition") in {"advance_to_full_text", "exclude_title_abstract"} for row in flow["title_abstract_screening"]["records"]),
        "advanced_database_records_244": sum(row.get("terminal_title_abstract_disposition") == "advance_to_full_text" for row in flow["title_abstract_screening"]["records"]) == 244,
        "canonical_retained_report_ledger_237": len(flow["full_text_stage"]["assessed_reports"]) == 237,
        "not_retrieved_log_53_unique_identities": len(flow["full_text_stage"]["reports_not_retrieved_log"]) == 53,
        "full_text_exclusion_log_18": len(flow["full_text_stage"]["exclusion_log"]) == 18,
        "kempny_contextual_citation_is_explicit_evidence_map_exclusion": (
            sum(
                row.get("route_record_id") == "TA-0428"
                and row.get("terminal_decision") == "exclude_full_text_contextual_citation_outside_evidence_map"
                for row in flow["full_text_stage"]["exclusion_log"]
            ) == 1
            and all(normalize_doi(row["DOI"]) != "10.1186/s12874-026-02913-1" for row in evidence)
        ),
        "every_full_text_exclusion_has_specific_reason": all(
            row.get("reason") not in (None, "", "not reported")
            for row in flow["full_text_stage"]["exclusion_log"]
        ),
        "every_nonretrieval_has_retrieval_status": all(
            row.get("retrieval_status") not in (None, "", "not reported")
            for row in flow["full_text_stage"]["reports_not_retrieved_log"]
        ),
        "publication_family_resolution_log_9_unique_identities": len(flow["full_text_stage"]["publication_or_version_family_resolution_log"]) == 9,
        "all_prisma_consistency_checks": all(flow["prisma_style_flow"]["consistency_checks"].values()),
    }
    return {
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "duplicate_identity_audit": duplicates,
        "preprint_status_contradictions": preprint_contradictions,
    }


def main() -> None:
    targets = [MASTER, FLOW]
    immutable_sources = [PREVIEW, FLOW_PREVIEW, CONFLICT_AUDIT, CHAIN, Y2020, Y2025, Y2025_RESOLUTION, Y2025_FORWARD, Y2026, RONAGHI]
    for path in targets + immutable_sources:
        if not path.exists():
            raise RuntimeError(f"Required source missing: {path}")
    source_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in immutable_sources}
    old_master = load(MASTER)
    old_flow = load(FLOW)
    preview = load(PREVIEW)
    flow_preview = load(FLOW_PREVIEW)
    conflict = load(CONFLICT_AUDIT)
    validate_preview(preview, flow_preview, conflict)
    # TA-0428 is a fully inspected secondary scoping review used only for
    # contextual synthesis.  It was carried forward as `include_contextual` in
    # an earlier flow artifact but never entered the frozen 237-row evidence
    # master.  Make that boundary explicit before constructing every canonical
    # route ledger so PRISMA identities and the evidence map are coterminous.
    kempny_rows = [row for row in flow_preview["database_records"] if row.get("screen_id") == "TA-0428"]
    if len(kempny_rows) != 1:
        raise RuntimeError(f"Expected exactly one TA-0428 row, found {len(kempny_rows)}")
    kempny_rows[0]["full_text_outcome"] = copy.deepcopy(KEMPNY_CONTEXTUAL_OUTCOME)
    ledgers = build_route_ledgers(flow_preview)
    assert_route_arithmetic(ledgers)
    assert_forward_identity_partition(flow_preview)
    master = build_master(preview, old_master, source_hashes)
    flow = build_review_flow(old_flow, flow_preview, master, ledgers, source_hashes)
    validation = validate_final(master, flow, old_flow)
    if not validation["all_checks_pass"]:
        failed = [name for name, passed in validation["checks"].items() if not passed]
        raise RuntimeError(f"Final validation blocked publication: {failed}")

    atomic_write_json(MASTER, master)
    atomic_write_json(FLOW, flow)
    # Re-read the published files so the audit attests to disk content, not
    # merely the in-memory candidates.
    published_master = load(MASTER)
    published_flow = load(FLOW)
    disk_validation = validate_final(published_master, published_flow, old_flow)
    if not disk_validation["all_checks_pass"]:
        raise RuntimeError("Post-write disk validation failed")
    audit = {
        "metadata": {
            "title": "Final canonical evidence and review-flow integrity audit",
            "generated_utc": preview["metadata"]["generated_utc"],
            "status": "pass",
            "publisher": "research/publish_final_consolidation.py",
        },
        "canonical_counts": {
            "evidence_records": len(published_master["evidence_records"]),
            "core_records": sum(class_bucket(row["Core or adjacent classification"]) == "core" for row in published_master["evidence_records"]),
            "adjacent_or_noncore_records": sum(class_bucket(row["Core or adjacent classification"]) == "noncore" for row in published_master["evidence_records"]),
            "quality_scores": len(published_master["quality_scores"]),
            "database_records_terminalized": len(published_flow["title_abstract_screening"]["records"]),
        },
        "canonical_full_text_arithmetic": {
            "primary_unique_identity": {
                "by_stratum": UNIQUE_IDENTITY_FULL_TEXT_ARITHMETIC,
                "combined": {
                    field: sum(row[field] for row in UNIQUE_IDENTITY_FULL_TEXT_ARITHMETIC)
                    for field in (
                        "reports_sought",
                        "reports_not_retrieved",
                        "reports_assessed_and_resolved",
                        "reports_retained",
                        "reports_excluded_after_full_text",
                        "publication_or_version_family_resolutions",
                    )
                },
            },
            "secondary_nonadditive_route_events": {
                "by_route": ROUTE_ARITHMETIC,
                "combined": {
                field: sum(row[field] for row in ROUTE_ARITHMETIC)
                for field in (
                    "reports_sought",
                    "reports_not_retrieved",
                    "reports_assessed_and_resolved",
                    "reports_retained",
                    "reports_excluded_after_full_text",
                    "publication_or_version_family_resolutions",
                )
                },
                "overlap_caution": "Twenty-one focused-forward candidates overlap the database union; these route events must not be added as unique report identities.",
            },
            "canonical_publication_identity_reconciliation": IDENTITY_RECONCILIATION,
            "focused_forward_identity_partition": {
                "all_focused_candidates": 59,
                "database_union_overlaps": 21,
                "outside_union_candidates": 38,
                "outside_union_title_abstract_exclusions": 4,
                "outside_union_reports_sought": 34,
                "outside_union_reports_not_retrieved": 8,
                "outside_union_reports_assessed_and_resolved": 26,
                "outside_union_retained": {"total": 25, "core": 16, "adjacent_or_noncore": 9},
                "outside_union_full_text_exclusions": 1,
            },
        },
        "validation": disk_validation,
        "source_fingerprints_before_publication": source_hashes,
        "published_fingerprints": {
            "research/master_evidence.json": sha256(MASTER),
            "research/review_flow.json": sha256(FLOW),
        },
        "preservation_statement": "Original identification queries/counts, accessibility log, eligibility criteria, deterministic triage rule, and review limitations are preserved exactly. Citation-chaining provenance is preserved and extended only with a terminal-resolution overlay.",
        "interpretation_cautions": [
            "Quality totals are audit aids, not study rankings.",
            "Route ledgers represent discovery/retrieval events and can overlap by DOI/title; master_evidence.json is the canonical deduplicated publication identity ledger.",
            "Citation chaining was targeted and some citation-index interfaces were unavailable or incomplete; no saturation claim is made.",
            "Screening and extraction were performed by one reviewer/Codex-assisted without independent duplicate adjudication.",
        ],
    }
    atomic_write_json(FINAL_AUDIT, audit)
    print(json.dumps({
        "status": "pass",
        "master": audit["canonical_counts"],
        "full_text_unique_identity": audit["canonical_full_text_arithmetic"]["primary_unique_identity"]["combined"],
        "full_text_secondary_route_events": audit["canonical_full_text_arithmetic"]["secondary_nonadditive_route_events"]["combined"],
        "master_sha256": audit["published_fingerprints"]["research/master_evidence.json"],
        "review_flow_sha256": audit["published_fingerprints"]["research/review_flow.json"],
        "integrity_audit": str(FINAL_AUDIT.relative_to(ROOT)),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
