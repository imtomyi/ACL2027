#!/usr/bin/env python3
"""Run relevance-ranked Crossref searches for the qualitative-analysis review."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


SEARCH_DATE = "2026-08-24"
ROWS = 100
QUERIES = {
    "CROSSREF_Q1": "large language model thematic analysis theme generation",
    "CROSSREF_Q2": "large language model qualitative coding inductive coding open coding",
    "CROSSREF_Q3": "large language model qualitative content analysis qualitative data analysis",
    "CROSSREF_Q4": "human AI collaboration human in the loop thematic analysis qualitative research",
    "CROSSREF_Q5": "multi-agent LLM agent thematic analysis qualitative coding",
    "CROSSREF_Q6": "codebook induction codebook generation codebook refinement LLM",
    "CROSSREF_Q7": "clinical transcript patient interview large language model automated coding",
}


def first(value, default=""):
    if isinstance(value, list) and value:
        return value[0]
    return default


def issued_year(item):
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return parts[0][0]
    return ""


def main() -> None:
    query_log = []
    works: dict[str, dict] = {}
    for query_id, query in QUERIES.items():
        params = {
            "query.title": query,
            "filter": "from-pub-date:2020-01-01,until-pub-date:2026-08-24",
            "rows": str(ROWS),
            "select": "DOI,title,author,published,published-print,published-online,issued,created,container-title,type,URL,score,references-count,is-referenced-by-count,abstract",
            "mailto": "review@example.invalid",
        }
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "ACLQualReview/1.0 (mailto:review@example.invalid)"})
        with urllib.request.urlopen(request, timeout=90) as response:
            message = json.load(response)["message"]
        items = message.get("items", [])
        query_log.append({
            "query_id": query_id,
            "database": "Crossref",
            "search_date": SEARCH_DATE,
            "query_parameter": "query.title",
            "query": query,
            "filters": "from-pub-date:2020-01-01, until-pub-date:2026-08-24; relevance sort; rows=100",
            "retrieved": len(items),
            "reported_total_results": message.get("total-results", 0),
        })
        for item in items:
            doi = item.get("DOI", "").lower()
            title = first(item.get("title"), "")
            key = doi or title.lower()
            authors = []
            for author in item.get("author", []):
                name = " ".join(filter(None, [author.get("given", ""), author.get("family", "")]))
                if name:
                    authors.append(name)
            if key not in works:
                works[key] = {
                    "doi": doi,
                    "title": title,
                    "authors": authors,
                    "year": issued_year(item),
                    "venue": first(item.get("container-title"), ""),
                    "type": item.get("type", ""),
                    "url": item.get("URL", ""),
                    "abstract": item.get("abstract", ""),
                    "crossref_citation_count": item.get("is-referenced-by-count", 0),
                    "matched_queries": [],
                    "best_score": item.get("score", 0),
                }
            works[key]["matched_queries"].append(query_id)
            works[key]["best_score"] = max(works[key]["best_score"], item.get("score", 0))
        time.sleep(0.2)

    payload = {
        "database": "Crossref",
        "search_date": SEARCH_DATE,
        "queries": query_log,
        "unique_records": len(works),
        "records": sorted(works.values(), key=lambda x: (-x["best_score"], x["title"])),
        "limitation": "Crossref query.title is relevance-ranked and fuzzy rather than Boolean; reported total-results are not treated as screened records. The first 100 results per query were retrieved and screened.",
    }
    output = Path(__file__).with_name("crossref_search_records.json")
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "query_retrievals": {item["query_id"]: item["retrieved"] for item in query_log},
        "unique_records": len(works),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
