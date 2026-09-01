#!/usr/bin/env python3
"""Confirmation retrieval pass using official repositories and OA metadata."""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SCREEN = ROOT / "screening_2020_2024_resolution.json"
LOG = ROOT / "screening_2020_2024_retrieval_log.json"
OUT_DIR = ROOT / "fulltext" / "screening_2020_2024"

CUSTOM_PDFS = {
    "TA-0901": "https://learninganalytics.upenn.edu/ryanbaker/paper_3699.pdf",
    "TA-1096": "https://aclanthology.org/2023.nlp4dh-1.12.pdf",
    "TA-1114": "https://aclanthology.org/2023.findings-emnlp.993.pdf",
}


def attempt(url: str, kind: str) -> tuple[dict, requests.Response | None]:
    try:
        r = requests.get(
            url,
            timeout=50,
            allow_redirects=True,
            headers={
                "User-Agent": "EvidenceSynthesisAudit/1.0 (research.audit@example.com)",
                "Accept": "application/pdf, application/xml;q=0.9, application/json;q=0.8, text/html;q=0.7",
            },
        )
        is_pdf = r.content.startswith(b"%PDF") and len(r.content) >= 10_000
        return ({
            "attempt_type": kind,
            "requested_url": url,
            "http_status": r.status_code,
            "resolved_url": r.url,
            "content_type": r.headers.get("content-type", "not reported").split(";")[0],
            "bytes_received": len(r.content),
            "pdf_full_text": is_pdf,
            "outcome": "retrieved_pdf" if is_pdf else ("metadata_or_landing_only" if r.ok else "http_failure"),
        }, r)
    except Exception as exc:
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


def save_pdf(sid: str, response: requests.Response, label: str) -> tuple[str, str]:
    pdf = OUT_DIR / f"{sid}_{label}.pdf"
    pdf.write_bytes(response.content)
    txt = pdf.with_suffix(".txt")
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True, timeout=60)
    return str(pdf.relative_to(ROOT.parent)), str(txt.relative_to(ROOT.parent))


def save_xml_text(sid: str, response: requests.Response, label: str) -> tuple[str, str]:
    xml = OUT_DIR / f"{sid}_{label}.xml"
    xml.write_bytes(response.content)
    soup = BeautifulSoup(response.content, "xml")
    txt = xml.with_suffix(".txt")
    txt.write_text("\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip()))
    return str(xml.relative_to(ROOT.parent)), str(txt.relative_to(ROOT.parent))


def openalex_pdf(row: dict, attempts: list[dict]) -> str | None:
    if row.get("doi") and row["doi"] != "not reported":
        api = f"https://api.openalex.org/works/https://doi.org/{quote(row['doi'], safe='')}?mailto=research.audit@example.com"
    else:
        api = f"https://api.openalex.org/works?search={quote(row['title'])}&per-page=5&mailto=research.audit@example.com"
    detail, response = attempt(api, "openalex_oa_metadata_lookup")
    attempts.append(detail)
    if not response or not response.ok:
        return None
    try:
        data = response.json()
    except Exception:
        return None
    works = data.get("results", []) if isinstance(data, dict) and "results" in data else [data]
    target = re.sub(r"[^a-z0-9]", "", row["title"].lower())
    for work in works:
        candidate = re.sub(r"[^a-z0-9]", "", (work.get("title") or "").lower())
        if target and candidate and not (target == candidate or target[:60] == candidate[:60]):
            continue
        for loc in [work.get("best_oa_location"), work.get("primary_location"), *(work.get("locations") or [])]:
            if isinstance(loc, dict) and loc.get("pdf_url"):
                return loc["pdf_url"]
    return None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    screen = json.loads(SCREEN.read_text())
    old_log = json.loads(LOG.read_text())
    by_id = {r["screen_id"]: r for r in old_log["records"]}
    rows = {r["screen_id"]: r for r in screen["database_union_resolution"]}
    for sid, entry in sorted(by_id.items()):
        if entry["terminal_retrieval_outcome"] == "retrieved_pdf":
            continue
        row = rows[sid]
        attempts = entry["attempts"]
        saved = None

        # Official PMC/Europe PMC full-text route for PubMed records.
        if row["source"] == "PubMed":
            lookup_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{quote(row['source_id'])}&format=json"
            detail, response = attempt(lookup_url, "europe_pmc_confirmation_lookup")
            attempts.append(detail)
            if response and response.ok:
                try:
                    results = response.json().get("resultList", {}).get("result", [])
                except Exception:
                    results = []
                pmcid = next((r.get("pmcid") for r in results if r.get("pmcid")), None)
                if pmcid:
                    xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
                    detail, xml_response = attempt(xml_url, "official_europe_pmc_full_text_xml")
                    attempts.append(detail)
                    if xml_response and xml_response.ok and b"<article" in xml_response.content and len(xml_response.content) >= 10_000:
                        detail["outcome"] = "retrieved_full_text_xml"
                        saved = save_xml_text(sid, xml_response, pmcid)

        if not saved and sid in CUSTOM_PDFS:
            detail, response = attempt(CUSTOM_PDFS[sid], "author_or_official_repository_pdf")
            attempts.append(detail)
            if response and detail["pdf_full_text"]:
                saved = save_pdf(sid, response, "repository")

        if not saved:
            pdf_url = openalex_pdf(row, attempts)
            if pdf_url:
                detail, response = attempt(pdf_url, "openalex_resolved_oa_pdf")
                attempts.append(detail)
                if response and detail["pdf_full_text"]:
                    saved = save_pdf(sid, response, "openalex")

        if saved:
            entry["terminal_retrieval_outcome"] = "retrieved_full_text"
            entry["local_pdf_path"] = saved[0]
            entry["local_text_path"] = saved[1]
        entry["confirmation_attempted_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        print(sid, entry["terminal_retrieval_outcome"], entry["local_text_path"])
        time.sleep(0.08)

    old_log["metadata"]["confirmation_pass_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    old_log["metadata"]["confirmation_routes"] = "Official Europe PMC full-text XML, author/ACL repository PDFs, and OpenAlex OA-location metadata."
    LOG.write_text(json.dumps(old_log, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
