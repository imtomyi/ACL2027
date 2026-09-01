#!/usr/bin/env python3
"""Run the arXiv API portion of the review search with dated raw counts."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


SEARCH_DATE = "2026-08-24"
MAX_RESULTS = 200
DATE_CLAUSE = "submittedDate:[202001010000 TO 202608242359]"
QUERIES = {
    "ARXIV_Q1": 'all:LLM AND all:"thematic analysis"',
    "ARXIV_Q2": 'all:LLM AND (all:"qualitative coding" OR all:"inductive coding" OR all:"open coding")',
    "ARXIV_Q3": 'all:LLM AND (all:"qualitative content analysis" OR all:"qualitative data analysis")',
    "ARXIV_Q4": '(all:"human-AI collaboration" OR all:"human-in-the-loop") AND (all:"thematic analysis" OR all:"qualitative research")',
    "ARXIV_Q5": '(all:"multi-agent" OR all:"LLM agent") AND (all:"thematic analysis" OR all:"qualitative coding")',
    "ARXIV_Q6": 'all:LLM AND (all:"codebook induction" OR all:"codebook generation" OR all:"codebook refinement")',
    "ARXIV_Q7": 'all:LLM AND (all:"clinical transcript" OR all:"patient interview")',
    "ARXIV_Q8": '(all:"identity leakage" OR all:"speaker identity" OR all:"shortcut learning") AND all:text',
}
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch(query: str) -> ET.Element:
    full_query = f"({query}) AND {DATE_CLAUSE}"
    params = {
        "search_query": full_query,
        "start": 0,
        "max_results": MAX_RESULTS,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "ACLQualReview/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return ET.fromstring(response.read())
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(4 + attempt * 2)
    raise RuntimeError("unreachable")


def text(node: ET.Element | None) -> str:
    return (node.text or "").strip() if node is not None else ""


def main() -> None:
    query_log = []
    records: dict[str, dict] = {}
    for index, (query_id, query) in enumerate(QUERIES.items()):
        root = fetch(query)
        total = int(text(root.find("opensearch:totalResults", NS)) or 0)
        entries = root.findall("atom:entry", NS)
        for entry in entries:
            arxiv_url = text(entry.find("atom:id", NS))
            arxiv_id = arxiv_url.rsplit("/", 1)[-1]
            record = records.setdefault(arxiv_id, {
                "arxiv_id": arxiv_id,
                "title": " ".join(text(entry.find("atom:title", NS)).split()),
                "authors": [text(author.find("atom:name", NS)) for author in entry.findall("atom:author", NS)],
                "published": text(entry.find("atom:published", NS)),
                "updated": text(entry.find("atom:updated", NS)),
                "abstract": " ".join(text(entry.find("atom:summary", NS)).split()),
                "categories": [node.attrib.get("term", "") for node in entry.findall("atom:category", NS)],
                "doi": text(entry.find("arxiv:doi", NS)),
                "journal_ref": text(entry.find("arxiv:journal_ref", NS)),
                "url": arxiv_url,
                "pdf_url": next((link.attrib.get("href", "") for link in entry.findall("atom:link", NS) if link.attrib.get("title") == "pdf"), ""),
                "matched_queries": [],
            })
            record["matched_queries"].append(query_id)
        query_log.append({
            "query_id": query_id,
            "database": "arXiv",
            "search_date": SEARCH_DATE,
            "query": f"({query}) AND {DATE_CLAUSE}",
            "filters": "Submitted 2020-01-01 through 2026-08-24; relevance sort; maximum 200 records",
            "reported_count": total,
            "retrieved": len(entries),
        })
        if index < len(QUERIES) - 1:
            time.sleep(3.1)

    payload = {
        "database": "arXiv",
        "search_date": SEARCH_DATE,
        "queries": query_log,
        "unique_records": len(records),
        "records": sorted(records.values(), key=lambda item: (item["published"], item["title"]), reverse=True),
        "limitation": "arXiv searches use its fielded API syntax and the acronym LLM; queries with more than 200 hits are truncated to 200 relevance-ranked records.",
    }
    output = Path(__file__).with_name("arxiv_search_records.json")
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "queries": [{"id": q["query_id"], "count": q["reported_count"], "retrieved": q["retrieved"]} for q in query_log],
        "unique_records": len(records),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
