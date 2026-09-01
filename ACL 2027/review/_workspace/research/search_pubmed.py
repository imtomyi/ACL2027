#!/usr/bin/env python3
"""Run and preserve the PubMed portion of the 2026-08-24 review search."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


SEARCH_DATE = "2026-08-24"
DATE_FILTER = '("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])'
QUERIES = {
    "PUBMED_Q1": '("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "generative AI"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "theme generation"[Title/Abstract])',
    "PUBMED_Q2": '("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative coding"[Title/Abstract] OR "inductive coding"[Title/Abstract] OR "open coding"[Title/Abstract])',
    "PUBMED_Q3": '("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative content analysis"[Title/Abstract] OR "qualitative data analysis"[Title/Abstract])',
    "PUBMED_Q4": '("human-AI collaboration"[Title/Abstract] OR "human-in-the-loop"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative research"[Title/Abstract])',
    "PUBMED_Q5": '("multi-agent"[Title/Abstract] OR "LLM agent"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative coding"[Title/Abstract])',
    "PUBMED_Q6": '("codebook induction"[Title/Abstract] OR "codebook generation"[Title/Abstract] OR "codebook refinement"[Title/Abstract]) AND (LLM[Title/Abstract] OR "large language model"[Title/Abstract])',
    "PUBMED_Q7": '("clinical transcript"[Title/Abstract] OR "patient interview"[Title/Abstract]) AND ("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "automated coding"[Title/Abstract])',
}


def get_json(endpoint: str, params: dict[str, str]) -> dict:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        result = json.load(response)
    time.sleep(0.36)
    return result


def get_xml(endpoint: str, params: dict[str, str]) -> ET.Element:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        root = ET.fromstring(response.read())
    time.sleep(0.36)
    return root


def flatten_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def parse_article(article: ET.Element) -> dict:
    medline = article.find("MedlineCitation")
    pdata = article.find("PubmedData")
    citation = medline.find("Article") if medline is not None else None
    pmid = flatten_text(medline.find("PMID") if medline is not None else None)
    title = flatten_text(citation.find("ArticleTitle") if citation is not None else None)
    abstract_nodes = citation.findall("Abstract/AbstractText") if citation is not None else []
    abstract = " ".join(filter(None, (flatten_text(node) for node in abstract_nodes)))
    journal = flatten_text(citation.find("Journal/Title") if citation is not None else None)
    year = flatten_text(citation.find("Journal/JournalIssue/PubDate/Year") if citation is not None else None)
    if not year:
        year = flatten_text(citation.find("Journal/JournalIssue/PubDate/MedlineDate") if citation is not None else None)
    authors = []
    if citation is not None:
        for author in citation.findall("AuthorList/Author"):
            collective = flatten_text(author.find("CollectiveName"))
            personal = " ".join(filter(None, [flatten_text(author.find("ForeName")), flatten_text(author.find("LastName"))]))
            if collective or personal:
                authors.append(collective or personal)
    identifiers = {}
    if pdata is not None:
        for node in pdata.findall("ArticleIdList/ArticleId"):
            identifiers[node.attrib.get("IdType", "other")] = flatten_text(node)
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal,
        "year": year,
        "doi": identifiers.get("doi", ""),
        "pmc": identifiers.get("pmc", ""),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    }


def main() -> None:
    query_results = []
    id_to_queries: dict[str, list[str]] = {}
    for query_id, query in QUERIES.items():
        full_query = f"({query}) AND {DATE_FILTER}"
        data = get_json("esearch.fcgi", {
            "db": "pubmed",
            "term": full_query,
            "retmode": "json",
            "retmax": "10000",
            "sort": "pub date",
        })
        ids = data["esearchresult"]["idlist"]
        query_results.append({
            "query_id": query_id,
            "database": "PubMed",
            "search_date": SEARCH_DATE,
            "query": full_query,
            "filters": "Publication date 2020-01-01 through 2026-08-24; title/abstract fields as specified",
            "retrieved": int(data["esearchresult"]["count"]),
            "ids": ids,
        })
        for pmid in ids:
            id_to_queries.setdefault(pmid, []).append(query_id)

    records = []
    ids = list(id_to_queries)
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        root = get_xml("efetch.fcgi", {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        })
        for article in root.findall("PubmedArticle"):
            record = parse_article(article)
            record["matched_queries"] = id_to_queries.get(record["pmid"], [])
            records.append(record)

    payload = {
        "database": "PubMed",
        "search_date": SEARCH_DATE,
        "queries": query_results,
        "unique_records": len(records),
        "records": records,
    }
    output = Path(__file__).with_name("pubmed_search_records.json")
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "query_counts": {item["query_id"]: item["retrieved"] for item in query_results},
        "unique_records": len(records),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
