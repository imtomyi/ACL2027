#!/usr/bin/env python3
"""Build preview-only final evidence and review-flow consolidation artifacts.

This script deliberately never writes master_evidence.json, review_flow.json, the
report, or the workbook. It validates completed year companions against the
current master schema, removes duplicate publications deterministically, keeps
all full-text-inspected evidence classes, keeps quality rows for core evidence
only, and reconciles the complete database and citation-chain screening flow.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"

MASTER = RESEARCH / "master_evidence.json"
Y2020_2024 = RESEARCH / "screening_2020_2024_resolution.json"
Y2025 = RESEARCH / "screening_2025_fulltext_extractions.json"
Y2025_RESOLUTION = RESEARCH / "screening_2025_resolution.json"
Y2025_FORWARD = RESEARCH / "screening_2025_forward_chain_resolution.json"
Y2026 = RESEARCH / "screening_2026_fulltext_outcomes.json"
RONAGHI = RESEARCH / "ronaghi_2026_evidence.json"
FLOW = RESEARCH / "review_flow.json"
UNION = RESEARCH / "search_union_deduplicated.json"
CHAIN = RESEARCH / "citation_chaining.json"

PREVIEW_OUT = RESEARCH / "final_consolidation_preview.json"
CONFLICT_OUT = RESEARCH / "final_consolidation_conflict_audit.json"
FLOW_OUT = RESEARCH / "final_review_flow_preview.json"
SUMMARY_OUT = RESEARCH / "final_consolidation_preview.md"

MISSING_IDENTIFIERS = {
    "",
    "not reported",
    "not assigned",
    "none",
    "n/a",
    "not applicable",
    "unknown",
    "unavailable",
    "no doi",
}
MISSING_VALUES = {"", "not reported", "not available", "unknown", "n/a", "null"}

# High-similarity pairs that were inspected during consolidation. These are
# dependence/adjacency relationships, not duplicate publications.
PAIR_DISPOSITIONS = {
    tuple(sorted(("parfenova_2024_proposal", "ta_0373_2026_maerz"))): {
        "decision": "retain_both_distinct",
        "rationale": "Generic title similarity only: different authors and identifiers, and a 2024 research proposal versus a 2026 CRAN software-package manual.",
    },
    tuple(sorted(("sankaranarayanan_et_al_2025_ta_mas", "ta_0151_2026_tajik"))): {
        "decision": "retain_both_distinct_but_dependency_visible",
        "rationale": "Overlapping team but distinct contributions, identifiers, datasets, and models: end-to-end Claude thematic analysis of CSCL survey responses versus DeepSeek reasoning-trace disagreement triage for tutor-dialogue coding.",
    },
    tuple(sorted(("chen_2024_prompts_matter", "chen_et_al_2025_processes_matter_open_coding"))): {
        "decision": "retain_both_distinct_but_dependency_visible",
        "rationale": "The 2025 paper explicitly reuses the 2024 corpus/codebooks but reports a distinct contribution-analysis study and publication identifier; it is not a duplicate version.",
    },
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


def normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = text.rstrip(".,; )]}\t\n")
    return "" if text in MISSING_IDENTIFIERS else text


def normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def class_bucket(value: Any) -> str:
    text = normalize_text(value).lower()
    if text.startswith("core"):
        return "core"
    if text.startswith("adjacent"):
        return "adjacent"
    if text.startswith("context") or "contextual" in text:
        return "contextual"
    return "unknown"


def extract_arxiv_ids(text: Any) -> set[str]:
    value = str(text or "").lower()
    return set(re.findall(r"(?:arxiv(?:\.org/(?:abs|pdf)/|[:\s.])|10\.48550/arxiv\.)(\d{4}\.\d{4,5})", value))


def extract_dois(text: Any) -> set[str]:
    values = set()
    for raw in re.findall(r"10\.\d{4,9}/[^\s\"'<>]+", str(text or ""), flags=re.I):
        value = normalize_doi(raw)
        if value:
            values.add(value)
    return values


def source_manifest(label: str, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
        "evidence_records": len(data.get("evidence_records", [])),
        "quality_scores_supplied": len(data.get("quality_scores", [])),
    }


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def record_rank(candidate: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    record = candidate["record"]
    status = normalize_text(record["Peer-reviewed status"]).lower()
    publication_type = normalize_text(record["Publication type"]).lower()
    history = normalize_text(record["Publication history notes"]).lower()
    negative_peer = any(term in status for term in ("not peer", "not verified", "preprint"))
    verified_peer = int(("peer reviewed" in status or "peer-reviewed" in status) and not negative_peer)
    accepted = int("accepted" in status or "accepted" in history)
    primary_doi = normalize_doi(record["DOI"])
    publisher_doi = int(bool(primary_doi) and not any(token in primary_doi for token in ("10.48550/arxiv", "10.2139/ssrn", "10.35542/osf", "10.5281/zenodo")))
    non_preprint = int("preprint" not in publication_type and "arxiv" not in publication_type)
    completeness = sum(normalize_text(value).lower() not in MISSING_VALUES for value in record.values())
    source_priority = candidate["source_priority"]
    return verified_peer, accepted, publisher_doi, non_preprint, completeness, source_priority


def validate_quality(
    quality: dict[str, Any],
    dimensions: list[str],
    source: str,
    issues: list[dict[str, Any]],
) -> bool:
    paper_id = quality.get("Paper ID", "not reported")
    valid = True
    scores = quality.get("Dimension scores")
    if not isinstance(scores, dict) or set(scores) != set(dimensions):
        issues.append({
            "severity": "fatal",
            "code": "QUALITY_DIMENSION_MISMATCH",
            "source": source,
            "paper_id": paper_id,
            "expected": dimensions,
            "actual": list(scores) if isinstance(scores, dict) else type(scores).__name__,
        })
        return False
    for dimension in dimensions:
        item = scores[dimension]
        if not isinstance(item, dict) or item.get("score") not in (0, 1, 2) or not normalize_text(item.get("rationale")):
            issues.append({
                "severity": "fatal",
                "code": "INVALID_QUALITY_SCORE",
                "source": source,
                "paper_id": paper_id,
                "dimension": dimension,
                "value": item,
            })
            valid = False
    if valid:
        calculated = sum(scores[name]["score"] for name in dimensions)
        if quality.get("Total") != calculated:
            issues.append({
                "severity": "fatal",
                "code": "QUALITY_TOTAL_MISMATCH",
                "source": source,
                "paper_id": paper_id,
                "reported": quality.get("Total"),
                "calculated": calculated,
            })
            valid = False
    return valid


def collect_candidates(
    sources: list[tuple[str, Path, int]],
    columns: list[str],
    dimensions: list[str],
    issues: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    quality_actions: list[dict[str, Any]] = []
    for label, path, priority in sources:
        if not path.exists():
            issues.append({"severity": "fatal", "code": "MISSING_REQUIRED_SOURCE", "source": label, "path": str(path)})
            continue
        data = load(path)
        manifests.append(source_manifest(label, path, data))
        evidence = data.get("evidence_records")
        qualities = data.get("quality_scores")
        if not isinstance(evidence, list) or not isinstance(qualities, list):
            issues.append({"severity": "fatal", "code": "SOURCE_ARRAY_MISSING", "source": label})
            continue
        by_quality: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for quality in qualities:
            by_quality[str(quality.get("Paper ID", ""))].append(quality)
        evidence_ids = [str(record.get("Paper ID", "")) for record in evidence]
        for paper_id, count in Counter(evidence_ids).items():
            if not paper_id or count != 1:
                issues.append({
                    "severity": "fatal",
                    "code": "DUPLICATE_OR_EMPTY_PAPER_ID_WITHIN_SOURCE",
                    "source": label,
                    "paper_id": paper_id or "not reported",
                    "count": count,
                })
        evidence_id_set = set(evidence_ids)
        for paper_id in sorted(set(by_quality) - evidence_id_set):
            issues.append({
                "severity": "warning",
                "code": "ORPHAN_QUALITY_ROW_DROPPED",
                "source": label,
                "paper_id": paper_id,
                "count": len(by_quality[paper_id]),
            })
        for index, original_record in enumerate(evidence):
            record = copy.deepcopy(original_record)
            paper_id = str(record.get("Paper ID", ""))
            if set(record) != set(columns) or len(record) != len(columns):
                issues.append({
                    "severity": "fatal",
                    "code": "EVIDENCE_SCHEMA_MISMATCH",
                    "source": label,
                    "paper_id": paper_id,
                    "field_count": len(record),
                    "missing_fields": sorted(set(columns) - set(record)),
                    "extra_fields": sorted(set(record) - set(columns)),
                })
                continue
            scalar_normalizations = []
            invalid_values = []
            for key, value in list(record.items()):
                if isinstance(value, str):
                    if not value.strip():
                        invalid_values.append(key)
                elif isinstance(value, (int, float, bool)):
                    record[key] = str(value)
                    scalar_normalizations.append({"field": key, "from_type": type(value).__name__, "to_value": record[key]})
                else:
                    invalid_values.append(key)
            if scalar_normalizations:
                issues.append({
                    "severity": "warning",
                    "code": "SCALAR_EVIDENCE_VALUE_NORMALIZED_TO_STRING",
                    "source": label,
                    "paper_id": paper_id,
                    "normalizations": scalar_normalizations,
                })
            if invalid_values:
                issues.append({
                    "severity": "fatal",
                    "code": "EMPTY_OR_NONSTRING_EVIDENCE_VALUE",
                    "source": label,
                    "paper_id": paper_id,
                    "fields": invalid_values,
                })
                continue
            bucket = class_bucket(record["Core or adjacent classification"])
            if bucket == "unknown":
                issues.append({
                    "severity": "fatal",
                    "code": "UNKNOWN_EVIDENCE_CLASS",
                    "source": label,
                    "paper_id": paper_id,
                    "classification": record["Core or adjacent classification"],
                })
                continue
            supplied = by_quality.get(paper_id, [])
            valid_quality = None
            if bucket == "core":
                if len(supplied) != 1:
                    issues.append({
                        "severity": "fatal",
                        "code": "CORE_QUALITY_CARDINALITY",
                        "source": label,
                        "paper_id": paper_id,
                        "count": len(supplied),
                    })
                elif validate_quality(supplied[0], dimensions, label, issues):
                    valid_quality = supplied[0]
            elif supplied:
                for quality in supplied:
                    validate_quality(quality, dimensions, label, issues)
                quality_actions.append({
                    "action": "drop_noncore_quality",
                    "source": label,
                    "paper_id": paper_id,
                    "classification": record["Core or adjacent classification"],
                    "rows_dropped": len(supplied),
                    "reason": "Quality scores are retained for core evidence only; the evidence record remains retained.",
                })
            candidates.append({
                "candidate_id": f"{label}:{index}:{paper_id}",
                "source": label,
                "source_path": str(path.relative_to(ROOT)),
                "source_priority": priority,
                "source_index": index,
                "record": record,
                "quality": valid_quality,
                "class_bucket": bucket,
            })
    return candidates, manifests, quality_actions


def identifier_keys(record: dict[str, str]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    doi = normalize_doi(record["DOI"])
    if doi:
        keys.append(("doi", doi))
    title = normalize_title(record["Title"])
    if title:
        keys.append(("normalized_title", title))
    own_blob = " ".join([
        record["DOI"],
        record["URL"],
        record["Full citation"],
    ])
    for arxiv_id in sorted(extract_arxiv_ids(own_blob)):
        keys.append(("arxiv_family", arxiv_id))
    relation_blob = " ".join([
        record["Full citation"],
        record["Publication history notes"],
        record["Relationship/dependence family"],
        record["Relationship to prior papers"],
    ])
    if re.search(r"publication family|version family|count once|same (?:paper|article|record)|supersed|journal (?:version|vor)|preprint.*(?:journal|conference)", relation_blob, flags=re.I):
        for related_doi in sorted(extract_dois(relation_blob)):
            keys.append(("declared_version_identifier", related_doi))
        for arxiv_id in sorted(extract_arxiv_ids(relation_blob)):
            keys.append(("declared_version_arxiv", arxiv_id))
    return keys


def consolidate_evidence(
    candidates: list[dict[str, Any]],
    columns: list[str],
    dimensions: list[str],
    issues: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    uf = UnionFind(len(candidates))
    seen: dict[tuple[str, str], int] = {}
    match_reasons: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        for kind, key in identifier_keys(candidate["record"]):
            # Primary and declared version identifiers intentionally share the
            # same DOI/ArXiv namespace so a VOR can join its preprint.
            namespace = "doi" if "identifier" in kind or kind == "doi" else "arxiv" if "arxiv" in kind else kind
            lookup = (namespace, key)
            if lookup in seen:
                other = seen[lookup]
                uf.union(index, other)
                pair = tuple(sorted((index, other)))
                match_reasons[pair].append({"kind": kind, "value": key})
            else:
                seen[lookup] = index
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(candidates)):
        groups[uf.find(index)].append(index)

    evidence: list[dict[str, str]] = []
    qualities: list[dict[str, Any]] = []
    duplicate_clusters: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for indices in sorted(groups.values(), key=lambda values: min(values)):
        ranked = sorted(indices, key=lambda idx: (record_rank(candidates[idx]), -idx), reverse=True)
        selected_index = ranked[0]
        selected = candidates[selected_index]
        selected_record = copy.deepcopy(selected["record"])
        member_buckets = sorted({candidates[idx]["class_bucket"] for idx in indices})
        if len(member_buckets) > 1:
            issues.append({
                "severity": "warning",
                "code": "DUPLICATE_FAMILY_CLASSIFICATION_CONFLICT",
                "selected_paper_id": selected_record["Paper ID"],
                "classifications": [
                    {
                        "source": candidates[idx]["source"],
                        "paper_id": candidates[idx]["record"]["Paper ID"],
                        "classification": candidates[idx]["record"]["Core or adjacent classification"],
                    }
                    for idx in indices
                ],
            })
        selected_quality = selected["quality"]
        if selected["class_bucket"] == "core" and selected_quality is None:
            quality_candidates = [candidates[idx] for idx in ranked if candidates[idx]["quality"] is not None]
            if quality_candidates:
                donor = quality_candidates[0]
                selected_quality = copy.deepcopy(donor["quality"])
                selected_quality["Paper ID"] = selected_record["Paper ID"]
                selected_quality["Title"] = selected_record["Title"]
                selected_quality["Core or adjacent classification"] = selected_record["Core or adjacent classification"]
                issues.append({
                    "severity": "warning",
                    "code": "QUALITY_TRANSFERRED_WITHIN_PUBLICATION_FAMILY",
                    "selected_paper_id": selected_record["Paper ID"],
                    "donor_source": donor["source"],
                    "donor_paper_id": donor["record"]["Paper ID"],
                })
            else:
                issues.append({
                    "severity": "fatal",
                    "code": "CONSOLIDATED_CORE_MISSING_QUALITY",
                    "selected_paper_id": selected_record["Paper ID"],
                    "members": [candidates[idx]["candidate_id"] for idx in indices],
                })
        evidence.append(selected_record)
        if selected["class_bucket"] == "core" and selected_quality is not None:
            qualities.append(copy.deepcopy(selected_quality))
        provenance.append({
            "Paper ID": selected_record["Paper ID"],
            "selected_source": selected["source"],
            "selected_source_path": selected["source_path"],
            "deduplicated_member_count": len(indices),
            "members": [
                {
                    "source": candidates[idx]["source"],
                    "paper_id": candidates[idx]["record"]["Paper ID"],
                    "doi": candidates[idx]["record"]["DOI"],
                    "title": candidates[idx]["record"]["Title"],
                }
                for idx in indices
            ],
        })
        if len(indices) > 1:
            field_conflicts = []
            for column in columns:
                values = sorted({normalize_text(candidates[idx]["record"][column]) for idx in indices})
                if len(values) > 1:
                    field_conflicts.append({"field": column, "values": values})
            duplicate_clusters.append({
                "selected_source": selected["source"],
                "selected_paper_id": selected_record["Paper ID"],
                "members": [candidates[idx]["candidate_id"] for idx in indices],
                "match_reasons": [
                    {"members": [candidates[left]["candidate_id"], candidates[right]["candidate_id"]], "keys": reasons}
                    for (left, right), reasons in match_reasons.items()
                    if left in indices and right in indices
                ],
                "field_conflicts": field_conflicts,
                "selection_rule": "verified publication status, accepted status, publisher DOI, non-preprint status, completeness, then source priority",
            })

    evidence_ids = [record["Paper ID"] for record in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        for paper_id, count in Counter(evidence_ids).items():
            if count > 1:
                issues.append({"severity": "fatal", "code": "DUPLICATE_FINAL_PAPER_ID", "paper_id": paper_id, "count": count})
    quality_ids = [quality["Paper ID"] for quality in qualities]
    core_ids = {record["Paper ID"] for record in evidence if class_bucket(record["Core or adjacent classification"]) == "core"}
    if Counter(quality_ids) != Counter(core_ids):
        issues.append({
            "severity": "fatal",
            "code": "FINAL_CORE_QUALITY_MISMATCH",
            "missing_quality": sorted(core_ids - set(quality_ids)),
            "extra_or_duplicate_quality": sorted(set(quality_ids) - core_ids),
            "duplicate_quality_ids": sorted(paper_id for paper_id, count in Counter(quality_ids).items() if count > 1),
        })
    assert all(set(record) == set(columns) for record in evidence)
    assert all(set(quality["Dimension scores"]) == set(dimensions) for quality in qualities)
    return evidence, qualities, duplicate_clusters, provenance


def author_tokens(value: str) -> set[str]:
    stop = {"et", "al", "and", "the"}
    return {token for token in normalize_title(value).split() if len(token) > 1 and token not in stop}


def possible_family_pairs(evidence: list[dict[str, str]]) -> list[dict[str, Any]]:
    pairs = []
    for left in range(len(evidence)):
        for right in range(left + 1, len(evidence)):
            a, b = evidence[left], evidence[right]
            title_similarity = difflib.SequenceMatcher(None, normalize_title(a["Title"]), normalize_title(b["Title"])).ratio()
            a_authors, b_authors = author_tokens(a["Authors"]), author_tokens(b["Authors"])
            author_overlap = len(a_authors & b_authors) / max(1, min(len(a_authors), len(b_authors)))
            try:
                year_distance = abs(int(a["Year"]) - int(b["Year"]))
            except (TypeError, ValueError):
                year_distance = None
            if title_similarity >= 0.82 or (title_similarity >= 0.58 and author_overlap >= 0.60 and (year_distance is None or year_distance <= 2)):
                disposition = PAIR_DISPOSITIONS.get(tuple(sorted((a["Paper ID"], b["Paper ID"]))))
                pairs.append({
                    "left_paper_id": a["Paper ID"],
                    "right_paper_id": b["Paper ID"],
                    "title_similarity": round(title_similarity, 3),
                    "author_token_overlap": round(author_overlap, 3),
                    "year_distance": year_distance if year_distance is not None else "not reported",
                    "left_relationship": a["Relationship/dependence family"],
                    "right_relationship": b["Relationship/dependence family"],
                    "automatic_action": "none — fuzzy similarity never triggers deduplication",
                    "reviewer_disposition": disposition or {"decision": "pending_manual_review", "rationale": "No explicit reviewer disposition is encoded."},
                })
    return sorted(pairs, key=lambda row: (row["title_similarity"], row["author_token_overlap"]), reverse=True)


def fulltext_overlay_maps(y2025_resolution: dict[str, Any], y2026: dict[str, Any]) -> dict[str, dict[str, Any]]:
    overlays: dict[str, dict[str, Any]] = {}
    for row in y2025_resolution["cross_stream_2025_handoffs"]["records"]:
        overlays[row["screen_id"]] = {
            "terminal_decision": row["final_full_text_decision"],
            "retrieval_status": "resolved in 2025 cross-stream full-text artifact",
            "reason": row["version_family"],
            "source_artifact": "research/screening_2025_resolution.json",
        }
    for row in y2026["cross_stream_handoffs"]:
        outcome = row["full_text_outcome"]
        overlays[row["screen_id"]] = {
            "terminal_decision": row["second_pass_decision"],
            "retrieval_status": outcome["retrieval_status"],
            "reason": outcome["decision_reason"],
            "source_artifact": "research/screening_2026_fulltext_outcomes.json",
        }
    return overlays


def normalize_chain_title_decision(value: Any) -> str:
    decision = normalize_text(value).lower()
    if any(token in decision for token in ("exclude", "not_applicable", "not applicable")):
        return "exclude_title_abstract"
    if any(token in decision for token in ("advance", "seek_full_text", "potential_core", "potential_adjacent", "potential_contextual")):
        return "advance_to_full_text"
    return "advance_to_full_text"


def outcome_group(decision: Any) -> str:
    value = normalize_text(decision).lower()
    if value.startswith("include_core"):
        return "include_core"
    if value.startswith("include_adjacent"):
        return "include_adjacent"
    if value.startswith("include_contextual"):
        return "include_contextual"
    if "not_retrieved" in value or "not retrieved" in value or "unavailable" in value:
        return "not_retrieved_after_attempts"
    if value.startswith("exclude"):
        return "exclude_after_full_text"
    if "version" in value or "family" in value or "existing_master" in value or "already_assessed" in value:
        return "publication_or_version_family_resolution"
    if "pending" in value or "handoff" in value:
        return "pending_cross_year_handoff"
    return value or "missing"


def build_review_flow_preview(
    flow: dict[str, Any],
    union: dict[str, Any],
    y2020: dict[str, Any],
    y2025_resolution: dict[str, Any],
    y2025_forward: dict[str, Any],
    y2026: dict[str, Any],
    chain: dict[str, Any],
    consolidated_evidence: list[dict[str, str]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    y2020_map = {row["screen_id"]: row for row in y2020["database_union_resolution"]}
    y2025_map = {row["screen_id"]: row for row in y2025_resolution["database_records"]}
    y2026_map = {row["screen_id"]: row for row in y2026["database_union_resolution"]}
    overlays = fulltext_overlay_maps(y2025_resolution, y2026)
    assessed_by_screen: dict[str, dict[str, Any]] = {}
    for report in flow["full_text_stage"]["assessed_reports"]:
        for screen_id in report.get("linked_screen_ids", []):
            assessed_by_screen[screen_id] = report

    records = []
    for original in flow["title_abstract_screening"]["records"]:
        screen_id = original["screen_id"]
        title_decision: str
        reason: str
        provenance: str
        fulltext: dict[str, Any]
        if screen_id in y2020_map:
            row = y2020_map[screen_id]
            second = row["second_pass_decision"]
            title_decision = "exclude_title_abstract" if second == "exclude_title_abstract" else "advance_to_full_text"
            reason = row["specific_reason"]
            provenance = "research/screening_2020_2024_resolution.json"
            if title_decision == "advance_to_full_text":
                fulltext = overlays.get(screen_id, {
                    "terminal_decision": second,
                    "retrieval_status": row["full_text_retrieval_outcome"],
                    "reason": row["specific_reason"],
                    "source_artifact": provenance,
                })
            else:
                fulltext = {"terminal_decision": "not_required_after_title_abstract_exclusion", "retrieval_status": "not required", "reason": reason, "source_artifact": provenance}
        elif screen_id in y2025_map:
            row = y2025_map[screen_id]
            title_decision = "advance_to_full_text" if row["second_pass_decision"].startswith("advance_") else "exclude_title_abstract"
            reason = row["eligibility_reason"]
            provenance = "research/screening_2025_resolution.json"
            followup = row["full_text_followup"]
            if title_decision == "advance_to_full_text":
                if followup["status"] == "not_retrieved":
                    terminal = "not_retrieved_after_attempts"
                else:
                    terminal = followup.get("final_full_text_decision") or "missing"
                fulltext = {
                    "terminal_decision": terminal,
                    "retrieval_status": followup["status"],
                    "reason": followup.get("reason", row["eligibility_reason"]),
                    "retrieval_attempts": followup.get("retrieval_attempts", []),
                    "source_artifact": provenance,
                }
            else:
                fulltext = {"terminal_decision": "not_required_after_title_abstract_exclusion", "retrieval_status": "not required", "reason": reason, "source_artifact": provenance}
        elif screen_id in y2026_map:
            row = y2026_map[screen_id]
            title_decision = row["title_abstract_decision"]
            reason = row["reason"]
            provenance = "research/screening_2026_fulltext_outcomes.json"
            if title_decision == "advance_to_full_text":
                outcome = row["full_text_outcome"]
                fulltext = {
                    "terminal_decision": row["second_pass_decision"],
                    "retrieval_status": outcome["retrieval_status"],
                    "reason": outcome["decision_reason"],
                    "retrieval_attempts": outcome.get("retrieval_attempts", []),
                    "source_artifact": provenance,
                }
            else:
                fulltext = {"terminal_decision": "not_required_after_title_abstract_exclusion", "retrieval_status": "not required", "reason": reason, "source_artifact": provenance}
        elif original.get("terminal_title_abstract_disposition") in ("advance_to_full_text", "exclude_title_abstract"):
            # Idempotent rebuild from an already-published canonical flow. The
            # year companions remain authoritative above; records outside those
            # year scopes retain their previously audited terminal overlay.
            title_decision = original["terminal_title_abstract_disposition"]
            reason = original.get("terminal_title_abstract_reason", original.get("reason", "not reported"))
            provenance = original.get("terminal_decision_provenance", "research/review_flow.json canonical terminal overlay")
            fulltext = copy.deepcopy(original.get("terminal_full_text_outcome", {
                "terminal_decision": "not_required_after_title_abstract_exclusion" if title_decision == "exclude_title_abstract" else "missing",
                "retrieval_status": "not required" if title_decision == "exclude_title_abstract" else "not reported",
                "reason": reason,
                "source_artifact": "research/review_flow.json canonical terminal overlay",
            }))
        elif original["decision"] == "excluded":
            title_decision = "exclude_title_abstract"
            reason = original["reason"]
            provenance = "research/review_flow.json deterministic exclusion retained as terminal title/abstract disposition"
            fulltext = {"terminal_decision": "not_required_after_title_abstract_exclusion", "retrieval_status": "not required", "reason": reason, "source_artifact": "research/review_flow.json"}
        elif original["decision"] == "included" and screen_id in assessed_by_screen:
            report = assessed_by_screen[screen_id]
            title_decision = "advance_to_full_text"
            reason = original["reason"]
            provenance = "research/review_flow.json existing linked assessed report"
            fulltext = {
                "terminal_decision": report["decision"],
                "retrieval_status": "retrieved_and_assessed",
                "reason": report["decision_reason"],
                "report_key": report["report_key"],
                "source_artifact": "research/review_flow.json",
            }
        else:
            title_decision = "missing"
            reason = original.get("reason", "not reported")
            provenance = "unresolved"
            fulltext = {"terminal_decision": "missing", "retrieval_status": "missing", "reason": "No terminal artifact mapping found.", "source_artifact": "not reported"}
            issues.append({"severity": "fatal", "code": "DATABASE_RECORD_WITHOUT_TERMINAL_SCREEN", "screen_id": screen_id})
        records.append({
            "screen_id": screen_id,
            "source_id": original["source_id"],
            "title": original["title"],
            "year": original.get("year") if original.get("year") is not None else "not reported",
            "doi": original.get("doi") or "not reported",
            "original_triage_decision": original["decision"],
            "terminal_title_abstract_disposition": title_decision,
            "title_abstract_reason": reason,
            "decision_provenance": provenance,
            "full_text_outcome": fulltext,
        })

    advanced = [row for row in records if row["terminal_title_abstract_disposition"] == "advance_to_full_text"]
    missing_fulltext = [row["screen_id"] for row in advanced if row["full_text_outcome"]["terminal_decision"] in ("missing", "pending", None)]
    if len(records) != 1360:
        issues.append({"severity": "fatal", "code": "DATABASE_UNIVERSE_COUNT_MISMATCH", "expected": 1360, "actual": len(records)})
    if missing_fulltext:
        issues.append({"severity": "fatal", "code": "ADVANCED_DATABASE_FULLTEXT_OUTCOME_MISSING", "screen_ids": missing_fulltext})

    # Resolve every new focused forward-chain candidate either through the
    # database flow or its year-specific outside-union companion.
    database_by_doi: dict[str, dict[str, Any]] = {}
    database_by_title: dict[str, dict[str, Any]] = {}
    for row in records:
        doi = normalize_doi(row["doi"])
        title = normalize_title(row["title"])
        if doi:
            database_by_doi[doi] = row
        if title:
            database_by_title[title] = row

    outside_rows: list[tuple[str, dict[str, Any]]] = []
    outside_rows.extend(("research/screening_2020_2024_resolution.json", row) for row in y2020["forward_chain_outside_union_resolution"])
    outside_rows.extend(("research/screening_2025_forward_chain_resolution.json", row) for row in y2025_forward["records"])
    outside_rows.extend(("research/screening_2026_fulltext_outcomes.json", row) for row in y2026["forward_chain_outside_union_resolution"])
    outside_rows.extend(
        ("research/screening_2026_fulltext_outcomes.json cross-stream handoff", row)
        for row in y2026["cross_stream_handoffs"]
        if str(row.get("screen_id", "")).startswith("FC-")
    )
    outside_by_doi: dict[str, tuple[str, dict[str, Any]]] = {}
    outside_by_title: dict[str, tuple[str, dict[str, Any]]] = {}
    for artifact, row in outside_rows:
        doi = normalize_doi(row.get("doi") or row.get("doi_as_indexed") or row.get("official_identifier"))
        title = normalize_title(row["title"])
        if doi:
            outside_by_doi[doi] = (artifact, row)
        if title:
            outside_by_title[title] = (artifact, row)

    forward_rows = []
    for candidate in chain["forward_result_screening"]["new_focused_scope_title_candidates"]:
        doi, title = normalize_doi(candidate.get("doi")), normalize_title(candidate["title"])
        database_match = database_by_doi.get(doi) if doi else None
        database_match = database_match or database_by_title.get(title)
        if database_match:
            forward_rows.append({
                "deduplication_key": candidate["deduplication_key"],
                "title": candidate["title"],
                "year": candidate.get("year") if candidate.get("year") is not None else "not reported",
                "doi": candidate.get("doi") or "not reported",
                "parent_seed_ids": candidate["parent_seed_ids"],
                "citation_index_sources": candidate["sources"],
                "resolution_route": "exact DOI or normalized-title link to database union",
                "linked_screen_id": database_match["screen_id"],
                "terminal_title_abstract_disposition": database_match["terminal_title_abstract_disposition"],
                "full_text_outcome": database_match["full_text_outcome"],
            })
            continue
        outside_match = outside_by_doi.get(doi) if doi else None
        outside_match = outside_match or outside_by_title.get(title)
        if outside_match:
            artifact, row = outside_match
            raw_title_decision = row.get("title_abstract_decision") or row.get("index_title_screen_outcome") or row.get("title_screen_outcome")
            decision = row.get("second_pass_decision") or row.get("full_text_decision") or "missing"
            if decision in ("not_applicable", "exclude_title_abstract"):
                title_decision = "exclude_title_abstract"
            elif (
                decision.startswith("include_")
                or decision.startswith("not_retrieved_after_attempts")
                or decision.startswith("exclude_after_full_text")
                or decision.startswith("resolved_outside_year_batch_handoff_")
                or decision == "not_assessed_advance_core"
            ):
                title_decision = "advance_to_full_text"
            else:
                title_decision = normalize_chain_title_decision(raw_title_decision)
            retrieval = row.get("full_text_outcome") or row.get("full_text_retrieval_outcome") or row.get("retrieval") or "not reported"
            if title_decision == "exclude_title_abstract":
                terminal_decision = "not_required_after_title_abstract_exclusion"
            elif decision == "not_assessed_advance_core" and isinstance(row.get("retrieval"), dict) and row["retrieval"].get("status") == "sought_not_retrieved":
                terminal_decision = "not_retrieved_after_attempts"
            elif decision.startswith("resolved_outside_year_batch_handoff_"):
                terminal_decision = "pending_cross_year_handoff"
                issues.append({
                    "severity": "fatal",
                    "code": "FORWARD_CHAIN_CROSS_YEAR_HANDOFF_PENDING",
                    "title": row["title"],
                    "source_artifact": artifact,
                    "handoff_decision": decision,
                })
            else:
                terminal_decision = decision
            forward_rows.append({
                "deduplication_key": candidate["deduplication_key"],
                "title": candidate["title"],
                "year": candidate.get("year") if candidate.get("year") is not None else "not reported",
                "doi": candidate.get("doi") or "not reported",
                "parent_seed_ids": candidate["parent_seed_ids"],
                "citation_index_sources": candidate["sources"],
                "resolution_route": artifact,
                "linked_screen_id": row.get("screen_id", "not reported"),
                "terminal_title_abstract_disposition": title_decision,
                "full_text_outcome": {"terminal_decision": terminal_decision, "retrieval": retrieval, "raw_source_decision": decision},
            })
            continue
        issues.append({
            "severity": "fatal",
            "code": "FOCUSED_FORWARD_CHAIN_RECORD_UNRESOLVED",
            "deduplication_key": candidate["deduplication_key"],
            "title": candidate["title"],
        })

    backward_rows = []
    for row in chain["backward_chain_candidates"]:
        terminal_backward = row["eligibility_decision"]
        if terminal_backward == "awaiting_full_text" and "sought" in normalize_text(row["full_text_outcome"]).lower():
            terminal_backward = "not_retrieved_after_attempts"
        backward_rows.append({
            "candidate_id": row["candidate_id"],
            "parent_seed_id": row["parent_seed_id"],
            "direction": "backward",
            "title_or_identifier": row["identifier"],
            "full_text_outcome": row["full_text_outcome"],
            "terminal_eligibility_decision": terminal_backward,
            "raw_source_eligibility_decision": row["eligibility_decision"],
            "eligibility_reason": row["eligibility_reason"],
        })

    evidence_by_doi = {normalize_doi(record["DOI"]): record for record in consolidated_evidence if normalize_doi(record["DOI"])}
    evidence_by_title = {normalize_title(record["Title"]): record for record in consolidated_evidence}
    seed_rows = []
    for seed in chain["seed_papers"]:
        match = evidence_by_doi.get(normalize_doi(seed.get("doi"))) or evidence_by_title.get(normalize_title(seed["title"]))
        seed_rows.append({
            "seed_id": seed["seed_id"],
            "title": seed["title"],
            "doi": seed.get("doi") or "not reported",
            "terminal_status": "represented_in_consolidated_full_text_evidence" if match else "not_matched_to_consolidated_evidence",
            "matched_paper_id": match["Paper ID"] if match else "not reported",
        })
    unmatched_seeds = [row["seed_id"] for row in seed_rows if row["terminal_status"] != "represented_in_consolidated_full_text_evidence"]
    if unmatched_seeds:
        issues.append({"severity": "warning", "code": "CHAIN_SEED_NOT_MATCHED_TO_CONSOLIDATED_EVIDENCE", "seed_ids": unmatched_seeds})

    if len(forward_rows) != chain["forward_result_screening"]["new_focused_scope_title_candidate_count"]:
        issues.append({
            "severity": "fatal",
            "code": "FOCUSED_FORWARD_CHAIN_COUNT_MISMATCH",
            "expected": chain["forward_result_screening"]["new_focused_scope_title_candidate_count"],
            "actual": len(forward_rows),
        })

    title_counts = dict(sorted(Counter(row["terminal_title_abstract_disposition"] for row in records).items()))
    fulltext_counts = dict(sorted(Counter(row["full_text_outcome"]["terminal_decision"] for row in advanced).items()))
    fulltext_group_counts = dict(sorted(Counter(outcome_group(row["full_text_outcome"]["terminal_decision"]) for row in advanced).items()))
    forward_title_counts = dict(sorted(Counter(row["terminal_title_abstract_disposition"] for row in forward_rows).items()))
    forward_advanced = [row for row in forward_rows if row["terminal_title_abstract_disposition"] == "advance_to_full_text"]
    forward_counts = dict(sorted(Counter(row["full_text_outcome"]["terminal_decision"] for row in forward_advanced).items()))
    forward_group_counts = dict(sorted(Counter(outcome_group(row["full_text_outcome"]["terminal_decision"]) for row in forward_advanced).items()))
    pending_forward = [row["title"] for row in forward_advanced if outcome_group(row["full_text_outcome"]["terminal_decision"]) == "pending_cross_year_handoff"]
    backward_counts = dict(sorted(Counter(row["terminal_eligibility_decision"] for row in backward_rows).items()))
    return {
        "metadata": {
            "title": "Preview-only terminal review-flow consolidation",
            "generated_utc": utc_now(),
            "database_universe": "research/search_union_deduplicated.json",
            "database_record_count": len(records),
            "interpretation": "Every database record has a terminal title/abstract disposition. Every advanced database record and every focused citation-chain candidate has a terminal full-text outcome, including explicit nonretrieval or publication-family resolution.",
            "write_scope": "Preview only; review_flow.json is not overwritten.",
        },
        "counts": {
            "database_records": len(records),
            "database_terminal_title_abstract_dispositions": title_counts,
            "database_advanced_to_full_text": len(advanced),
            "database_advanced_full_text_outcomes": fulltext_counts,
            "database_advanced_full_text_outcome_groups": fulltext_group_counts,
            "database_advanced_missing_full_text_outcomes": len(missing_fulltext),
            "citation_seed_records": len(seed_rows),
            "backward_chain_candidates": len(backward_rows),
            "backward_chain_full_text_outcomes": backward_counts,
            "forward_deduplicated_records_identified": chain["forward_result_screening"]["deduplicated_forward_record_count"],
            "new_focused_forward_candidates": len(forward_rows),
            "new_focused_forward_title_abstract_dispositions": forward_title_counts,
            "new_focused_forward_advanced_to_full_text": len(forward_advanced),
            "new_focused_forward_full_text_outcomes": forward_counts,
            "new_focused_forward_full_text_outcome_groups": forward_group_counts,
            "new_focused_forward_pending_cross_year_handoffs": len(pending_forward),
        },
        "database_records": records,
        "citation_seed_records": seed_rows,
        "backward_chain_records": backward_rows,
        "focused_forward_chain_records": forward_rows,
        "consistency_checks": {
            "database_count_is_1360": len(records) == 1360,
            "every_database_title_abstract_disposition_terminal": all(row["terminal_title_abstract_disposition"] != "missing" for row in records),
            "every_advanced_database_record_has_terminal_full_text_outcome": not missing_fulltext,
            "every_new_focused_forward_candidate_mapped": len(forward_rows) == chain["forward_result_screening"]["new_focused_scope_title_candidate_count"],
            "every_advanced_focused_forward_candidate_has_terminal_full_text_outcome": not pending_forward,
            "all_backward_candidates_have_outcomes": all(row["full_text_outcome"] for row in backward_rows),
        },
    }


def declared_family_audit(y2020: dict[str, Any], y2025: dict[str, Any], y2026: dict[str, Any]) -> dict[str, Any]:
    suppression_events = []
    for row in y2020["database_union_resolution"]:
        decision = row["second_pass_decision"]
        if "version" in decision or "family" in decision:
            suppression_events.append({
                "screen_id": row["screen_id"],
                "decision": decision,
                "title": row["title"],
                "reason": row["specific_reason"],
                "source_artifact": "research/screening_2020_2024_resolution.json",
            })
    for row in y2025["database_records"]:
        followup = row["full_text_followup"]
        decision = followup.get("final_full_text_decision")
        if decision and ("duplicate" in decision or "version" in decision):
            suppression_events.append({
                "screen_id": row["screen_id"],
                "decision": decision,
                "title": row["title"],
                "reason": followup.get("reason", row["eligibility_reason"]),
                "source_artifact": "research/screening_2025_resolution.json",
            })
    seen_2026 = set()
    for row in y2026["database_union_resolution"] + y2026["cross_stream_handoffs"]:
        decision = row["second_pass_decision"]
        if "duplicate" in decision or "existing_master" in decision:
            key = (row["screen_id"], decision)
            if key in seen_2026:
                continue
            seen_2026.add(key)
            outcome = row.get("full_text_outcome", {})
            suppression_events.append({
                "screen_id": row["screen_id"],
                "decision": decision,
                "title": row["title"],
                "reason": outcome.get("decision_reason", row.get("reason", "not reported")),
                "source_artifact": "research/screening_2026_fulltext_outcomes.json",
            })
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in suppression_events:
        grouped[event["screen_id"]].append(event)
    suppressions = []
    for screen_id, events in sorted(grouped.items()):
        preferred = events[-1]
        suppressions.append({
            "screen_id": screen_id,
            "title": preferred["title"],
            "terminal_decision": preferred["decision"],
            "terminal_reason": preferred["reason"],
            "decision_history": [
                {
                    "decision": event["decision"],
                    "reason": event["reason"],
                    "source_artifact": event["source_artifact"],
                }
                for event in events
            ],
            "counting_rule": "one publication/evidence identity; decision history does not create additional records",
        })
    return {
        "terminal_publication_family_or_existing_evidence_resolutions": suppressions,
        "resolution_identity_count": len(suppressions),
        "resolution_event_count_before_identity_collapse": len(suppression_events),
        "2025_declared_cross_year_collision": load(Y2025).get("metadata", {}).get("cross_year_collision", "not reported"),
        "2025_declared_publication_and_dependency_flags": load(Y2025).get("metadata", {}).get("publication_family_flags", []),
        "interpretation": "A declared dependency family is not automatically a duplicate publication. Only exact identifiers/titles, explicit version identifiers, and terminal duplicate-family decisions suppress evidence rows.",
    }


def markdown_summary(preview: dict[str, Any], audit: dict[str, Any], flow_preview: dict[str, Any]) -> str:
    counts = preview["metadata"]["consolidation_counts"]
    flow_counts = flow_preview["counts"]
    return f"""# Final consolidation preview

This is a preview-only consolidation. It does not overwrite `master_evidence.json`, `review_flow.json`, the report, or the workbook.

## Evidence outcome

- Raw source evidence rows: {counts['raw_evidence_rows']}.
- Deduplicated retained evidence rows: {counts['retained_evidence_rows']}.
- Core records and quality rows: {counts['core_records']} / {counts['quality_rows']}.
- Adjacent/contextual records retained without quality rows: {counts['noncore_records']}.
- Exact DOI/title/version-family duplicate clusters removed at this layer: {counts['duplicate_rows_removed']}.
- Non-core quality rows intentionally dropped: {counts['noncore_quality_rows_dropped']}.
- Fatal validation conflicts: {audit['summary']['fatal_conflicts']}.

NITA is present once as the 2025-companion journal version of record. The 2026 TA-0336 duplicate was suppressed upstream; input overlap shown by this idempotence rebuild reflects already-published canonical rows re-entering alongside their year companions, not duplicate rows in the canonical master.

## Review-flow outcome

- Database records with terminal title/abstract dispositions: {flow_counts['database_records']}.
- Advanced database records with terminal full-text outcomes: {flow_counts['database_advanced_to_full_text']}; missing outcomes: {flow_counts['database_advanced_missing_full_text_outcomes']}.
- Focused forward-chain candidates mapped: {flow_counts['new_focused_forward_candidates']}; advanced to full text: {flow_counts['new_focused_forward_advanced_to_full_text']}; pending cross-year handoffs: {flow_counts['new_focused_forward_pending_cross_year_handoffs']}.
- Backward-chain candidates resolved: {flow_counts['backward_chain_candidates']}.

## Artifacts

- `research/final_consolidation_preview.json`
- `research/final_consolidation_conflict_audit.json`
- `research/final_review_flow_preview.json`

Quality totals remain audit aids and are not study rankings. Fuzzy title/author pairs in the conflict audit are manual-review prompts only and are never automatically deduplicated.
"""


def run() -> None:
    master = load(MASTER)
    columns = master["metadata"]["extraction_columns"]
    dimensions = master["quality_dimensions"]
    if len(columns) != 52:
        raise RuntimeError(f"Master schema has {len(columns)} extraction columns, expected 52")
    if len(dimensions) != 12:
        raise RuntimeError(f"Master quality schema has {len(dimensions)} dimensions, expected 12")

    sources = [
        ("current_master", MASTER, 10),
        ("screening_2020_2024", Y2020_2024, 20),
        ("screening_2025", Y2025, 30),
        ("screening_2026", Y2026, 40),
        ("ronaghi_fulltext_correction", RONAGHI, 50),
    ]
    issues: list[dict[str, Any]] = []
    candidates, manifests, quality_actions = collect_candidates(sources, columns, dimensions, issues)
    evidence, qualities, duplicate_clusters, provenance = consolidate_evidence(candidates, columns, dimensions, issues)
    family_pairs = possible_family_pairs(evidence)

    logic_paths = [FLOW, UNION, CHAIN, Y2025_RESOLUTION, Y2025_FORWARD]
    logic_initial_hashes = {path: sha256(path) for path in logic_paths}
    y2020 = load(Y2020_2024)
    y2025_resolution = load(Y2025_RESOLUTION)
    y2025_forward = load(Y2025_FORWARD)
    y2026 = load(Y2026)
    flow = load(FLOW)
    union = load(UNION)
    chain = load(CHAIN)
    flow_preview = build_review_flow_preview(
        flow,
        union,
        y2020,
        y2025_resolution,
        y2025_forward,
        y2026,
        chain,
        evidence,
        issues,
    )
    family_audit = declared_family_audit(y2020, y2025_resolution, y2026)

    # Detect a companion being replaced while this preview is running. This is
    # especially important during parallel year-batch consolidation.
    for manifest in manifests:
        current_hash = sha256(ROOT / manifest["path"])
        if current_hash != manifest["sha256"]:
            issues.append({
                "severity": "fatal",
                "code": "SOURCE_CHANGED_DURING_CONSOLIDATION",
                "source": manifest["label"],
                "path": manifest["path"],
                "initial_sha256": manifest["sha256"],
                "final_sha256": current_hash,
            })
    logic_manifests = []
    for path in logic_paths:
        final_hash = sha256(path)
        logic_manifests.append({
            "path": str(path.relative_to(ROOT)),
            "sha256": logic_initial_hashes[path],
            "size_bytes": path.stat().st_size,
        })
        if final_hash != logic_initial_hashes[path]:
            issues.append({
                "severity": "fatal",
                "code": "SOURCE_CHANGED_DURING_CONSOLIDATION",
                "path": str(path.relative_to(ROOT)),
                "initial_sha256": logic_initial_hashes[path],
                "final_sha256": final_hash,
            })

    fatal = [issue for issue in issues if issue["severity"] == "fatal"]
    warnings = [issue for issue in issues if issue["severity"] == "warning"]
    core_count = sum(class_bucket(record["Core or adjacent classification"]) == "core" for record in evidence)
    noncore_count = len(evidence) - core_count
    preview = {
        "metadata": {
            "title": "Preview-only final evidence consolidation",
            "generated_utc": utc_now(),
            "mode": "preview_only_no_shared_artifact_overwrite",
            "validation_status": "pass" if not fatal else "blocked_by_fatal_conflicts",
            "deduplication_order": [
                "normalized exact DOI",
                "normalized exact title",
                "shared arXiv identifier",
                "explicitly declared version-family DOI/arXiv identifier",
            ],
            "canonical_selection_rule": "Prefer verified peer-reviewed/accepted publication, publisher DOI, non-preprint form, completeness, then later source priority; never merge fields across records.",
            "extraction_columns": columns,
            "consolidation_counts": {
                "raw_evidence_rows": len(candidates),
                "retained_evidence_rows": len(evidence),
                "duplicate_rows_removed": len(candidates) - len(evidence),
                "core_records": core_count,
                "noncore_records": noncore_count,
                "quality_rows": len(qualities),
                "noncore_quality_rows_dropped": sum(action["rows_dropped"] for action in quality_actions),
            },
            "interpretation_caution": "Quality totals are audit aids, not study rankings. Adjacent/contextual evidence is retained for synthesis but intentionally unscored.",
        },
        "evidence_records": evidence,
        "quality_dimensions": dimensions,
        "quality_scores": qualities,
        "source_provenance": provenance,
    }
    audit = {
        "metadata": {
            "title": "Final evidence consolidation conflict and provenance audit",
            "generated_utc": utc_now(),
            "preview_artifact": str(PREVIEW_OUT.relative_to(ROOT)),
        },
        "summary": {
            "input_sources": len(manifests),
            "raw_evidence_rows": len(candidates),
            "retained_evidence_rows": len(evidence),
            "duplicate_clusters": len(duplicate_clusters),
            "duplicate_rows_removed": len(candidates) - len(evidence),
            "noncore_quality_rows_dropped": sum(action["rows_dropped"] for action in quality_actions),
            "similarity_pairs_audited": len(family_pairs),
            "possible_publication_family_pairs_for_manual_review": sum(pair["reviewer_disposition"]["decision"] == "pending_manual_review" for pair in family_pairs),
            "fatal_conflicts": len(fatal),
            "warnings": len(warnings),
        },
        "source_manifests": manifests,
        "review_logic_source_manifests": logic_manifests,
        "duplicate_clusters": duplicate_clusters,
        "quality_row_actions": quality_actions,
        "declared_family_audit": family_audit,
        "possible_publication_family_pairs": family_pairs,
        "validation_issues": issues,
    }

    PREVIEW_OUT.write_text(json.dumps(preview, indent=2, ensure_ascii=False) + "\n")
    CONFLICT_OUT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    FLOW_OUT.write_text(json.dumps(flow_preview, indent=2, ensure_ascii=False) + "\n")
    SUMMARY_OUT.write_text(markdown_summary(preview, audit, flow_preview))

    print(json.dumps({
        "validation_status": preview["metadata"]["validation_status"],
        "consolidation_counts": preview["metadata"]["consolidation_counts"],
        "conflict_summary": audit["summary"],
        "review_flow_counts": flow_preview["counts"],
        "outputs": [str(path) for path in (PREVIEW_OUT, CONFLICT_OUT, FLOW_OUT, SUMMARY_OUT)],
    }, indent=2, ensure_ascii=False))
    if fatal:
        raise SystemExit(2)


if __name__ == "__main__":
    run()
