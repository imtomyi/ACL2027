#!/usr/bin/env python3
"""Reproducibly attempt full-text retrieval for advanced 2020--2024 records.

The script records every attempted URL and only labels a response as full text when
it is a nontrivial PDF. Landing pages remain retrieval failures for review purposes.
"""

from __future__ import annotations

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent
SCREEN = ROOT / "screening_2020_2024_resolution.json"
UNION = ROOT / "search_union_deduplicated.json"
OUT_DIR = ROOT / "fulltext" / "screening_2020_2024"
LOG = ROOT / "screening_2020_2024_retrieval_log.json"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def candidate_urls(row: dict, source: dict) -> list[tuple[str, str]]:
    source_name = row["source"]
    source_id = row["source_id"]
    doi = row.get("doi")
    urls: list[tuple[str, str]] = []
    if source_name == "arXiv":
        arxiv_id = re.sub(r"v\d+$", "", source_id)
        urls.extend([
            ("official_arxiv_pdf", f"https://arxiv.org/pdf/{arxiv_id}"),
            ("official_export_arxiv_pdf", f"https://export.arxiv.org/pdf/{arxiv_id}"),
        ])
    elif source_name == "ACL Anthology":
        page = row["url"].rstrip("/")
        urls.append(("official_acl_pdf", page + ".pdf"))
    elif source_name == "OpenReview":
        urls.append(("official_openreview_pdf", f"https://openreview.net/pdf?id={quote(source_id)}"))
    elif source_name == "PubMed":
        urls.extend([
            ("pubmed_central_id_lookup", f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pmc&id={quote(source_id)}&retmode=json"),
            ("europe_pmc_fulltext_lookup", f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{quote(source_id)}&format=json"),
        ])
    if doi and doi != "not reported":
        urls.extend([
            ("doi_content_negotiation", f"https://doi.org/{doi}"),
            ("unpaywall_lookup", f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email=research.audit@example.com"),
            ("crossref_metadata_lookup", f"https://api.crossref.org/works/{quote(doi, safe='')}"),
        ])
    if row.get("url") and row["url"] != "not reported":
        urls.append(("indexed_landing_or_file", row["url"]))
    # Stable deduplication while retaining the reason for the first attempt.
    seen = set()
    return [(kind, url) for kind, url in urls if not (url in seen or seen.add(url))]


def request_url(kind: str, url: str) -> tuple[dict, bytes | None]:
    headers = {
        "User-Agent": "EvidenceSynthesisAudit/1.0 (contact: research.audit@example.com)",
        "Accept": "application/pdf, application/json;q=0.9, text/html;q=0.8, */*;q=0.5",
    }
    try:
        response = requests.get(url, headers=headers, timeout=35, allow_redirects=True)
        body = response.content
        content_type = response.headers.get("content-type", "not reported").split(";")[0]
        is_pdf = body.startswith(b"%PDF") and len(body) >= 10_000
        result = {
            "attempt_type": kind,
            "requested_url": url,
            "http_status": response.status_code,
            "resolved_url": response.url,
            "content_type": content_type,
            "bytes_received": len(body),
            "pdf_full_text": is_pdf,
            "outcome": "retrieved_pdf" if is_pdf else ("metadata_or_landing_only" if response.ok else "http_failure"),
        }
        return result, body if is_pdf else None
    except Exception as exc:  # network errors are evidence to preserve in the log
        return ({
            "attempt_type": kind,
            "requested_url": url,
            "http_status": "not reported",
            "resolved_url": "not reported",
            "content_type": "not reported",
            "bytes_received": 0,
            "pdf_full_text": False,
            "outcome": f"request_error: {type(exc).__name__}: {str(exc)[:240]}",
        }, None)


def retrieve(row: dict, source: dict) -> dict:
    attempts = []
    pdf_path = None
    for kind, url in candidate_urls(row, source):
        attempt, body = request_url(kind, url)
        attempts.append(attempt)
        if body is not None:
            pdf_path = OUT_DIR / f"{row['screen_id']}_{safe_name(row['source_id'])}.pdf"
            pdf_path.write_bytes(body)
            break
    text_path = None
    if pdf_path:
        text_path = pdf_path.with_suffix(".txt")
        converted = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(text_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if converted.returncode != 0 or not text_path.exists():
            text_path = None
    return {
        "screen_id": row["screen_id"],
        "title": row["title"],
        "source": row["source"],
        "source_id": row["source_id"],
        "attempted_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "attempts": attempts,
        "terminal_retrieval_outcome": "retrieved_pdf" if pdf_path else "not_retrieved_after_attempts",
        "local_pdf_path": str(pdf_path.relative_to(ROOT.parent)) if pdf_path else "not reported",
        "local_text_path": str(text_path.relative_to(ROOT.parent)) if text_path else "not reported",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    screen = json.loads(SCREEN.read_text())
    union = json.loads(UNION.read_text())
    by_source = {record["source_id"]: record for record in union["records"]}
    advanced = [
        row for row in screen["database_union_resolution"]
        if row["second_pass_decision"].startswith("potential_")
        and row.get("local_full_text_path") == "not reported"
    ]
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(retrieve, row, by_source[row["source_id"]]): row for row in advanced}
        for future in as_completed(futures):
            results.append(future.result())
            result = results[-1]
            print(result["screen_id"], result["terminal_retrieval_outcome"], result["local_text_path"])
    results.sort(key=lambda item: item["screen_id"])
    LOG.write_text(json.dumps({
        "metadata": {
            "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "purpose": "Auditable retrieval attempts for advanced database records without an existing local full text",
            "success_rule": "Only a response beginning with the PDF signature and at least 10,000 bytes is treated as retrieved full text.",
        },
        "records": results,
    }, indent=2, ensure_ascii=False) + "\n")
    print(LOG)


if __name__ == "__main__":
    main()
