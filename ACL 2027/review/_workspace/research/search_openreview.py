#!/usr/bin/env python3
"""Reproducible OpenReview phrase search with task-specific client filtering."""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


SEARCH_DATE = "2026-08-24"
CUTOFF_MS = int(dt.datetime(2026, 8, 25, tzinfo=dt.timezone.utc).timestamp() * 1000) - 1
LIMIT = 1000
QUERIES = {
    "OPENREVIEW_Q1": '"thematic analysis"',
    "OPENREVIEW_Q2": '"qualitative coding"',
    "OPENREVIEW_Q3": '"inductive coding"',
    "OPENREVIEW_Q4": '"open coding"',
    "OPENREVIEW_Q5": '"qualitative data analysis"',
    "OPENREVIEW_Q6": '"qualitative content analysis"',
    "OPENREVIEW_Q7": '"codebook generation"',
    "OPENREVIEW_Q8": '"codebook refinement"',
    "OPENREVIEW_Q9": '"clinical transcript"',
}
LLM_TERMS = (
    "llm", "large language model", "generative ai", "generative artificial intelligence",
    "chatgpt", "gpt-", "gpt ", "multi-agent", "multi agent", "language-model",
)
TASK_TERMS = (
    "thematic analysis", "qualitative coding", "inductive coding", "open coding",
    "qualitative data analysis", "qualitative content analysis", "codebook",
)


def value(content: dict, key: str, default=""):
    item = content.get(key, default)
    if isinstance(item, dict) and "value" in item:
        return item["value"]
    return item


def text_blob(content: dict) -> str:
    pieces = []
    for key in ("title", "abstract", "TLDR", "keywords"):
        item = value(content, key, "")
        if isinstance(item, list):
            pieces.extend(str(part) for part in item)
        else:
            pieces.append(str(item))
    return re.sub(r"\s+", " ", " ".join(pieces)).lower()


def main() -> None:
    query_log = []
    records: dict[str, dict] = {}
    for query_id, term in QUERIES.items():
        params = urllib.parse.urlencode({"term": term, "limit": LIMIT, "offset": 0})
        url = "https://api2.openreview.net/notes/search?" + params
        request = urllib.request.Request(url, headers={"User-Agent": "ACLQualReview/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
        notes = data.get("notes", [])
        kept = 0
        for note in notes:
            created = note.get("cdate") or note.get("pdate") or 0
            if created and created > CUTOFF_MS:
                continue
            content = note.get("content", {})
            blob = text_blob(content)
            if not (any(term in blob for term in LLM_TERMS) and any(term in blob for term in TASK_TERMS)):
                continue
            kept += 1
            title = str(value(content, "title", "")).strip()
            key = note.get("forum") or note.get("id") or title.lower()
            pdf = str(value(content, "pdf", ""))
            if pdf.startswith("/"):
                pdf = "https://openreview.net" + pdf
            authors = value(content, "authors", [])
            if not isinstance(authors, list):
                authors = [str(authors)] if authors else []
            venue = value(content, "venue", "")
            keywords = value(content, "keywords", [])
            record = records.setdefault(key, {
                "openreview_id": note.get("forum") or note.get("id", ""),
                "title": title,
                "authors": authors,
                "venue": venue,
                "abstract": str(value(content, "abstract", "")),
                "keywords": keywords if isinstance(keywords, list) else [str(keywords)],
                "url": f"https://openreview.net/forum?id={note.get('forum') or note.get('id', '')}",
                "pdf_url": pdf,
                "created_ms": created,
                "matched_queries": [],
            })
            record["matched_queries"].append(query_id)
        query_log.append({
            "query_id": query_id,
            "database": "OpenReview",
            "search_date": SEARCH_DATE,
            "endpoint": "https://api2.openreview.net/notes/search",
            "query": term,
            "filters": "phrase search; first 1,000 relevance-ranked results; created by 2026-08-24; client filter requires an LLM term and qualitative-analysis task term",
            "reported_count": data.get("count", 0),
            "retrieved": len(notes),
            "retained_after_client_filter": kept,
        })
        time.sleep(0.5)

    payload = {
        "database": "OpenReview",
        "search_date": SEARCH_DATE,
        "queries": query_log,
        "unique_retained_records": len(records),
        "records": sorted(records.values(), key=lambda item: item["title"]),
        "limitation": "OpenReview's public search endpoint supports phrase retrieval but not the full Boolean syntax in the protocol. Task phrases were searched separately and LLM/task criteria were applied reproducibly client-side. Queries with more than 1,000 hits are truncated to the first 1,000 relevance-ranked notes.",
    }
    output = Path(__file__).with_name("openreview_search_records.json")
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "queries": [{"id": q["query_id"], "count": q["reported_count"], "retrieved": q["retrieved"], "retained": q["retained_after_client_filter"]} for q in query_log],
        "unique_retained_records": len(records),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
