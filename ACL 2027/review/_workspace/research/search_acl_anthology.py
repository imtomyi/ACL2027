#!/usr/bin/env python3
"""Title-field search of the ACL Anthology's dated BibTeX snapshot."""

from __future__ import annotations

import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path


SEARCH_DATE = "2026-08-24"
SNAPSHOT_URL = "https://aclanthology.org/anthology.bib"
QUERIES = {
    "ACL_Q1": {
        "llm": ["large language model", "llm", "generative ai", "generative artificial intelligence"],
        "task": ["thematic analysis", "theme generation"],
    },
    "ACL_Q2": {
        "llm": ["large language model", "llm"],
        "task": ["qualitative coding", "inductive coding", "open coding"],
    },
    "ACL_Q3": {
        "llm": ["large language model", "llm"],
        "task": ["qualitative content analysis", "qualitative data analysis"],
    },
    "ACL_Q4": {
        "llm": ["human-ai collaboration", "human ai collaboration", "human-in-the-loop", "human in the loop"],
        "task": ["thematic analysis", "qualitative research", "qualitative analysis"],
    },
    "ACL_Q5": {
        "llm": ["multi-agent", "multi agent", "llm agent"],
        "task": ["thematic analysis", "qualitative coding"],
    },
    "ACL_Q6": {
        "llm": ["llm", "large language model"],
        "task": ["codebook induction", "codebook generation", "codebook refinement"],
    },
    "ACL_Q7": {
        "llm": ["llm", "large language model", "automated coding"],
        "task": ["clinical transcript", "patient interview"],
    },
    "ACL_Q8_SUPPLEMENT": {
        "llm": [],
        "task": ["thematic analysis", "qualitative coding", "qualitative data analysis", "inductive coding", "open codes"],
    },
}


def clean_tex(text: str) -> str:
    text = text.replace("{", "").replace("}", "")
    text = text.replace("{--}", "-")
    return re.sub(r"\\[A-Za-z]+", "", text).strip()


def quoted_field(line: str, field: str) -> str:
    match = re.search(rf'(?:^|,){re.escape(field)} = "(.*?)"(?=,\w+ = |\}}$)', line)
    return clean_tex(match.group(1)) if match else ""


def year_field(line: str) -> str:
    match = re.search(r'(?:^|,)year = "?(\d{4})"?', line)
    return match.group(1) if match else ""


def url_field(line: str) -> str:
    match = re.search(r',url = anth # \{([^}]+)\}', line)
    return f"https://aclanthology.org/{match.group(1)}" if match else ""


def matches(title: str, query: dict[str, list[str]]) -> bool:
    normalized = re.sub(r"\s+", " ", title.lower())
    task_match = any(term in normalized for term in query["task"])
    return task_match and (not query["llm"] or any(term in normalized for term in query["llm"]))


def main() -> None:
    counts = defaultdict(int)
    records: dict[str, dict] = {}
    request = urllib.request.Request(SNAPSHOT_URL, headers={"User-Agent": "ACLQualReview/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        for raw in response:
            if not raw.startswith((b"@inproceedings{", b"@article{")):
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            key_match = re.match(r"@\w+\{([^,]+),", line)
            if not key_match:
                continue
            title = quoted_field(line, "title")
            if not title:
                continue
            year = year_field(line)
            if year and not (2020 <= int(year) <= 2026):
                continue
            matched = [query_id for query_id, query in QUERIES.items() if matches(title, query)]
            if not matched:
                continue
            key = key_match.group(1)
            for query_id in matched:
                counts[query_id] += 1
            records[key] = {
                "anthology_bibkey": key,
                "title": title,
                "authors": quoted_field(line, "author"),
                "year": year,
                "venue": quoted_field(line, "booktitle") or quoted_field(line, "journal"),
                "doi": quoted_field(line, "doi"),
                "url": url_field(line),
                "matched_queries": matched,
            }

    query_log = []
    for query_id, query in QUERIES.items():
        query_log.append({
            "query_id": query_id,
            "database": "ACL Anthology",
            "search_date": SEARCH_DATE,
            "query": f"TITLE contains any of {query['llm']} AND any of {query['task']}",
            "filters": "article/inproceedings records in ACL Anthology snapshot generated 2026-08-24; title field; case-insensitive literal matching",
            "retrieved": counts[query_id],
        })
    payload = {
        "database": "ACL Anthology",
        "search_date": SEARCH_DATE,
        "snapshot_url": SNAPSHOT_URL,
        "queries": query_log,
        "unique_records": len(records),
        "records": sorted(records.values(), key=lambda item: (item["year"], item["title"])),
        "limitation": "The downloadable Anthology BibTeX snapshot does not contain abstracts, so this reproducible pass is title-field only; seed citation chaining and site/full-text searches supplement it.",
    }
    output = Path(__file__).with_name("acl_anthology_search_records.json")
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "query_counts": dict(counts),
        "unique_records": len(records),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
