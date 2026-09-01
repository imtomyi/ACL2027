#!/usr/bin/env python3
"""Fetch dated OpenAlex citation counts for the master evidence records.

Exact DOI lookup is preferred. Title search is accepted only at a stringent normalized
similarity threshold; otherwise the count remains explicitly unavailable.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "master_evidence.json"
OUT = ROOT / "citation_counts_20260824.json"
DATE = "2026-08-24"
UA = "ACL-ARR-scoping-review/1.0 (systematic evidence audit; mailto:research@example.invalid)"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get_json(url: str, attempts: int = 3) -> dict | None:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code not in {429, 500, 502, 503, 504}:
                return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def openalex_by_doi(doi: str) -> dict | None:
    identifier = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
    return get_json(f"https://api.openalex.org/works/{identifier}?mailto=research@example.invalid")


def openalex_by_title(title: str) -> tuple[dict | None, float]:
    query = urllib.parse.urlencode({"search": title, "per-page": 5, "mailto": "research@example.invalid"})
    payload = get_json(f"https://api.openalex.org/works?{query}") or {}
    best, score = None, 0.0
    target = norm(title)
    for candidate in payload.get("results", []):
        candidate_title = norm(candidate.get("display_name", ""))
        candidate_score = SequenceMatcher(None, target, candidate_title).ratio()
        if candidate_score > score:
            best, score = candidate, candidate_score
    return best, score


def main() -> None:
    master = json.loads(SOURCE.read_text())
    results = []
    for index, record in enumerate(master["evidence_records"], start=1):
        paper_id = record.get("Paper ID", "not reported")
        title = record.get("Title", "not reported")
        doi = str(record.get("DOI", "not reported")).strip().lower()
        if doi.startswith("https://doi.org/"):
            doi = doi.split("https://doi.org/", 1)[1]
        work = None
        method = None
        match_score = None
        if doi not in {"", "not reported", "none", "n/a"} and not doi.startswith("10.48550/arxiv."):
            work = openalex_by_doi(doi)
            method = "exact DOI"
        if work is None and title not in {"", "not reported"}:
            candidate, score = openalex_by_title(title)
            match_score = round(score, 4)
            if candidate is not None and score >= 0.94:
                work = candidate
                method = "title match >=0.94"
        if work is None:
            results.append({
                "Paper ID": paper_id,
                "Title": title,
                "Citation count": "not reported",
                "Citation count source": "OpenAlex lookup unavailable or no sufficiently exact match",
                "Retrieval date": DATE,
                "Lookup method": method or "no verified match",
                "Title match score": match_score,
            })
        else:
            results.append({
                "Paper ID": paper_id,
                "Title": title,
                "Citation count": int(work.get("cited_by_count", 0)),
                "Citation count source": "OpenAlex cited_by_count",
                "Retrieval date": DATE,
                "OpenAlex ID": work.get("id", "not reported"),
                "OpenAlex title": work.get("display_name", "not reported"),
                "Lookup method": method,
                "Title match score": match_score if match_score is not None else 1.0,
            })
        if index % 10 == 0:
            print(f"{index}/{len(master['evidence_records'])}")
        time.sleep(0.08)
    OUT.write_text(json.dumps({"retrieval_date": DATE, "source_definition": "OpenAlex cited_by_count at retrieval time; exact DOI lookup preferred; title lookup requires normalized similarity >=0.94", "records": results}, indent=2))
    print(OUT)


if __name__ == "__main__":
    main()
