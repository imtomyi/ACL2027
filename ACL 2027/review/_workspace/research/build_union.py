#!/usr/bin/env python3
"""Create a reproducible cross-database search union and exact deduplication log."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def norm_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\b(preprint|extended abstract|poster)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def norm_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip(" .")


sources = [
    ("PubMed", "pubmed_search_records.json"),
    ("Crossref", "crossref_search_records.json"),
    ("ACL Anthology", "acl_anthology_search_records.json"),
    ("OpenReview", "openreview_search_records.json"),
    ("arXiv", "arxiv_search_records.json"),
]

records = []
for source, filename in sources:
    payload = json.loads((ROOT / filename).read_text())
    for rec in payload["records"]:
        title = (rec.get("title") or "").strip()
        doi = norm_doi(rec.get("doi") or "")
        url = rec.get("url") or rec.get("pdf_url") or ""
        abstract = rec.get("abstract") or ""
        year = rec.get("year") or (str(rec.get("published") or "")[:4] or None)
        records.append({
            "source": source,
            "source_id": str(rec.get("pmid") or rec.get("anthology_bibkey") or rec.get("openreview_id") or rec.get("arxiv_id") or doi or title),
            "title": title,
            "title_norm": norm_title(title),
            "doi": doi,
            "url": url,
            "year": year,
            "authors": rec.get("authors") or [],
            "venue": rec.get("venue") or rec.get("journal") or rec.get("journal_ref") or "",
            "abstract": abstract,
        })

# Union-find joins exact DOI matches and normalized exact-title matches.
parent = list(range(len(records)))


def find(i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def union(a: int, b: int) -> None:
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


doi_seen, title_seen = {}, {}
for idx, rec in enumerate(records):
    if rec["doi"]:
        if rec["doi"] in doi_seen:
            union(idx, doi_seen[rec["doi"]])
        else:
            doi_seen[rec["doi"]] = idx
    if rec["title_norm"]:
        if rec["title_norm"] in title_seen:
            union(idx, title_seen[rec["title_norm"]])
        else:
            title_seen[rec["title_norm"]] = idx

groups = defaultdict(list)
for i, rec in enumerate(records):
    groups[find(i)].append(rec)

priority = {"ACL Anthology": 0, "PubMed": 1, "Crossref": 2, "OpenReview": 3, "arXiv": 4}
unique = []
for members in groups.values():
    members.sort(key=lambda r: (priority[r["source"]], -len(r["abstract"]), -len(r["title"])))
    base = dict(members[0])
    base["sources"] = sorted({m["source"] for m in members}, key=priority.get)
    base["source_records"] = [{"source": m["source"], "source_id": m["source_id"], "url": m["url"]} for m in members]
    base["duplicate_records_removed"] = len(members) - 1
    if not base["doi"]:
        base["doi"] = next((m["doi"] for m in members if m["doi"]), "")
    if not base["abstract"]:
        base["abstract"] = next((m["abstract"] for m in members if m["abstract"]), "")
    unique.append(base)

unique.sort(key=lambda r: (-(int(r["year"]) if str(r["year"]).isdigit() else 0), r["title_norm"]))
summary = {
    "generated_from": [filename for _, filename in sources],
    "source_record_counts": dict(Counter(r["source"] for r in records)),
    "records_before_cross_database_deduplication": len(records),
    "unique_records_after_exact_doi_and_normalized_title_deduplication": len(unique),
    "duplicate_records_removed": len(records) - len(unique),
    "deduplication_method": "Union by normalized exact DOI or normalized exact title; venue/preprint versions may remain separate if titles differ materially.",
    "records": unique,
}
(ROOT / "search_union_deduplicated.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print(json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=2))
