#!/usr/bin/env python3
"""Build two non-destructive recent-publication libraries.

The first library is organized by peer-review state and conservative venue tier.
The second contains the same locally usable paper set in year-level chronological
order.  Source PDFs are copied, never moved, because the review evidence graph
refers to their original paths.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = ROOT / "research/recent_publication_inventory.json"
MASTER_PATH = ROOT / "research/master_evidence.json"

VENUE_LIBRARY = ROOT / "recent relevant publications (2023-2026)"
CHRONO_LIBRARY = ROOT / "recent relevant publications - chronological (2023-2026)"
REVIEW_CUTOFF = "2026-08-24"


CATEGORIES = {
    "A1": {
        "folder": "01_peer-reviewed__main_ACL-EMNLP-NAACL-EACL",
        "label": "Peer-reviewed main-track NLP conferences",
        "description": (
            "Established ACL/EMNLP/NAACL/EACL main-track papers. This is a venue "
            "classification, not a paper-quality score."
        ),
    },
    "A2": {
        "folder": "02_peer-reviewed__ACL-Findings-and-Industry",
        "label": "Peer-reviewed ACL-family Findings and Industry papers",
        "description": (
            "Peer-reviewed archival Findings or Industry-track papers, kept separate "
            "from the ACL/EMNLP/NAACL/EACL main conference track."
        ),
    },
    "B": {
        "folder": "03_peer-reviewed__reputable-journals",
        "label": "Peer-reviewed reputable or established journals",
        "description": (
            "Journal versions of record or publication families supported by an "
            "established journal record. Publisher identity alone was not used as a "
            "quality signal."
        ),
    },
    "C1": {
        "folder": "04_peer-reviewed__other-reputable-AI-HCI-conferences",
        "label": "Peer-reviewed reputable specialist/full conferences",
        "description": (
            "Full papers in established adjacent venues such as CHI, The Web "
            "Conference, ICWSM, ECIR, LAK, HICSS, ICPC, and Learning at Scale. "
            "These are reputable but are not labeled as equivalent to an NLP main track."
        ),
    },
    "C2": {
        "folder": "05_peer-reviewed__specialist-workshop-short-form",
        "label": "Peer-reviewed specialist, workshop, or short-form papers",
        "description": (
            "Peer-reviewed workshops, student papers, posters, extended abstracts, "
            "or limited specialist proceedings. Publication status does not imply a "
            "full main-conference empirical paper."
        ),
    },
    "D": {
        "folder": "06_not-peer-reviewed__preprints-manuscripts-unverified",
        "label": "Not peer-reviewed or archival peer review unverified",
        "description": (
            "Preprints, manuscripts, software documentation, or accepted/presented "
            "work for which a final archival peer-reviewed record was not verified by "
            "the review cutoff."
        ),
    },
    "E": {
        "folder": "07_status-or-venue-needs-caution",
        "label": "Mixed version families or lower-confidence venue/status evidence",
        "description": (
            "Items needing careful interpretation because the local artifact and "
            "peer-reviewed version differ, or because venue/review evidence is "
            "insufficient. This folder does not label a venue as predatory or poor."
        ),
    },
    "CTX": {
        "folder": "08_contextual-peer-reviewed-review__outside-evidence-map",
        "label": "Peer-reviewed contextual review outside the canonical evidence map",
        "description": (
            "A directly relevant scoping review retained as context, but deliberately "
            "not represented as one of the canonical 237 evidence records."
        ),
    },
}


A1_IDS = {"hicode_2025"}

A2_IDS = {
    "chen_2026_open_code_metrics",
    "zhu_2026_trauma",
    "centaurta_2026",
    "matveyenko_2026_muse",
    "parfenova_pfeffer_2025_ensemble",
    "quallm_2025",
    "yu_2025_same_company",
    "parfenova_2025_inductive_coding",
    "dai_2023_llm_in_loop",
    "spinoso_2023_qualitative_code_suggestion",
}

C2_IDS = {
    "ta_0351_2026_fischer",
    "parfenova_2024_proposal",
    "fischer_biemann_2024_qda",
    "kousa_2023_chatgpt_finnish_content_analysis",
    "chen_et_al_2025_processes_matter_open_coding",
    "ganesh_2024_prompting_panacea",
    "fc_11_2026_beltran",
    "ta_0175_2026_saranto",
    "ta_0370_2026_ngo",
}

D_EXTRA_IDS = {
    "fc_15_2026_li",
    "chen_2024_prompts_matter",
}

E_IDS = {
    "details_2025",
    "khan_2024_controversial_topics",
}

B_EXTRA_IDS = {"ashwin_2025_serious_bias"}


SPECIAL_VENUE = {
    "ta_0385_2026_garces": "Learning at Scale 2026 (peer-reviewed paper; local/canonical URL is arXiv)",
    "ashwin_2025_serious_bias": "Sociological Methods & Research (OnlineFirst, 27 May 2025)",
}


MANUSCRIPT_OF_REVIEWED_FAMILY = {
    "ta_0955_2026_meng": "Earlier manuscript copy of the later peer-reviewed ACM TOCHI publication family.",
    "nguyen_trung_nguyen_2026_nita": "OSF/prepublication copy of the later peer-reviewed Qualitative Research in Psychology publication family.",
    "ta_0360_2026_khalid": "arXiv/author copy of a later peer-reviewed Social Science Computer Review publication family.",
    "zhang_et_al_2025_harnessing_ai_qualitative_research": "Earlier manuscript copy of the later peer-reviewed journal publication family.",
    "ashwin_2025_serious_bias": "Local arXiv/manuscript copy; the canonical work is a 2025 SAGE journal article, not this file-level version of record.",
}


EXTERNAL_STATUS_NOTES = {
    "ashwin_2025_serious_bias": (
        "Official SAGE article page checked 2026-08-25; it identifies an Original "
        "Article first published online 2025-05-27, DOI 10.1177/00491241251338246."
    ),
    "thematic_lm_2025": (
        "DBLP/ACM metadata checked 2026-08-25; WWW 2025, pp. 649-658, "
        "DOI 10.1145/3696410.3714595."
    ),
}


KEMPNY = {
    "paper_id": "context_kempny_2026_scoping_review",
    "title": "The use and methodological reporting of large language models in qualitative research: a scoping review",
    "authors": "Christian Kempny; Julian Frings; Paul Rust; Sven Meister; Leonard Fehring",
    "year": "2026",
    "venue": "BMC Medical Research Methodology 26, Article 137",
    "publication_type": "peer-reviewed journal scoping review",
    "canonical_peer_review_status": "peer reviewed",
    "publication_history_notes": "Open-access peer-reviewed journal version of record.",
    "evidence_classification": "contextual; deliberately outside the 237-record canonical evidence map",
    "doi": "10.1186/s12874-026-02913-1",
    "url": "https://doi.org/10.1186/s12874-026-02913-1",
    "source_path": "research/fulltext/latest/kempny_2026_scoping_review.pdf",
    "category": "CTX",
    "peer_review_state": "PR_YES",
}


MANIFEST_FIELDS = [
    "record_scope",
    "paper_id",
    "title",
    "authors",
    "year",
    "venue",
    "publication_type",
    "evidence_classification",
    "peer_review_state",
    "peer_review_explanation",
    "venue_class",
    "venue_tier_note",
    "canonical_peer_review_status",
    "publication_history_notes",
    "external_status_check",
    "local_artifact_status",
    "local_pdf_pages",
    "source_path",
    "venue_library_destination",
    "chronological_destination",
    "copy_action",
    "sha256",
    "non_pdf_asset_sha256",
    "doi",
    "url",
    "review_cutoff",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_pages(path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Not a parseable PDF: {path.relative_to(ROOT)}")
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise RuntimeError(f"PDF has no readable pages: {path.relative_to(ROOT)}")
    return int(match.group(1))


def safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return re.sub(r"-+", "-", value).strip("-_")


def title_sort_key(value: str) -> str:
    """Alphabetize quoted titles under their first alphanumeric word."""
    return re.sub(r"^[^A-Za-z0-9]+", "", value).casefold()


def first_year(value: Any) -> int | None:
    match = re.search(r"\b(20\d{2})\b", str(value))
    return int(match.group(1)) if match else None


def copy_checked(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"Refusing to overwrite a different file: {destination}")
        return "already_present_identical"
    shutil.copy2(source, destination)
    return "copied"


def write_generated(path: Path, content: str) -> None:
    marker = "<!-- Generated by research/build_recent_publication_library.py -->"
    text = f"{marker}\n{content.rstrip()}\n"
    if path.exists() and marker not in path.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"Refusing to overwrite a non-generated file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def category_for(item: dict[str, Any], source_group: str) -> str:
    paper_id = item["paper_id"]
    if paper_id in A1_IDS:
        return "A1"
    if paper_id in A2_IDS:
        return "A2"
    if paper_id in C2_IDS:
        return "C2"
    if paper_id in D_EXTRA_IDS:
        return "D"
    if paper_id in E_IDS:
        return "E"
    if paper_id in B_EXTRA_IDS:
        return "B"
    if source_group == "peer_reviewed_reputable_journals":
        return "B"
    if source_group == "peer_reviewed_other_reputable_conferences":
        return "C1"
    if source_group == "non_peer_reviewed_or_unverified":
        return "D"
    raise RuntimeError(f"No conservative category assigned for {paper_id} ({source_group})")


def peer_review_state(paper_id: str, category: str) -> tuple[str, str]:
    if paper_id == "ashwin_2025_serious_bias":
        return (
            "PR_VENUE_SUPPORTED",
            "Published as a 2025 Original Article in Sociological Methods & Research; the canonical extraction did not record peer-review status, so this is venue-supported rather than inherited from that field.",
        )
    if category in {"A1", "A2", "B", "C1", "C2", "CTX"}:
        return "PR_YES", "Canonical review evidence identifies a peer-reviewed archival publication."
    if paper_id in {"fc_15_2026_li", "chen_2024_prompts_matter"}:
        return (
            "PR_ACCEPTED_NO_VOR",
            "Acceptance or presentation is reported, but no final archival peer-reviewed record was verified by the review cutoff.",
        )
    if paper_id == "details_2025":
        return (
            "PR_MIXED",
            "The short CUI paper is peer reviewed, while the local expanded manuscript is a distinct non-peer-reviewed version; review status is not transferred to the expansion.",
        )
    if paper_id == "khan_2024_controversial_topics":
        return (
            "PR_UNKNOWN",
            "A journal reference is reported, but peer review and venue standing were not independently verified.",
        )
    return (
        "PR_NO",
        "Preprint/manuscript or non-peer-reviewed output as of 2026-08-24; no peer-reviewed archival version was verified.",
    )


def tier_note(paper_id: str, category: str) -> str:
    if category == "A1":
        return "Established main-track NLP conference."
    if category == "A2":
        return "Peer-reviewed archival Findings/Industry paper; listed separately from the ACL/EMNLP/NAACL main conference track."
    if category == "B":
        if paper_id == "dorfel_2026_inductive_coding":
            return "Peer-reviewed journal version of record; included conservatively without treating publisher identity as evidence of flagship quality."
        return "Established or reputable peer-reviewed journal; venue status is not a paper-quality ranking."
    if category == "C1":
        return "Established peer-reviewed specialist/full conference; reputable, but not presented as equivalent to a main NLP track."
    if category == "C2":
        return "Peer-reviewed workshop/proceedings/short-format paper; not equivalent to a main-conference full paper."
    if category == "D":
        if paper_id in D_EXTRA_IDS:
            return "Accepted/presented status is kept separate from verified archival peer review."
        return "Non-peer-reviewed or archival review status unverified; retained because it is directly relevant, not because of venue prestige."
    if category == "E":
        return "Local evidence is insufficient for a confident venue/status classification; this does not mean the venue is predatory or poor."
    return "Peer-reviewed contextual review, kept outside the canonical evidence-map count."


def local_artifact_status(item: dict[str, Any], category: str) -> str:
    paper_id = item["paper_id"]
    source = item["source_path"]
    if paper_id == "thematic_lm_2025":
        return (
            "No paper-level PDF copied. The local www2025-proceedings.pdf is a 112-page front-matter/table-of-contents file, not the 10-page paper. Public author-copy download attempts returned HTTP 403 on 2026-08-25."
        )
    if paper_id in MANUSCRIPT_OF_REVIEWED_FAMILY:
        return MANUSCRIPT_OF_REVIEWED_FAMILY[paper_id]
    lower = source.lower()
    stem = Path(source).stem.lower()
    manuscript_hint = (
        "arxiv" in lower
        or "_author" in lower
        or "_osf" in lower
        or "openalex" in lower
        or re.search(r"(?:^|[_-])\d{4}\.\d{4,6}(?:v\d+)?(?:$|[_-])", stem) is not None
    )
    if category in {"A1", "A2", "B", "C1", "C2"} and manuscript_hint:
        return "Author/preprint/repository copy of a peer-reviewed publication family; the local file is not asserted to be the publisher version of record."
    if category == "D":
        return "Local inspected preprint, manuscript, repository file, or non-peer-reviewed research output."
    if category == "E":
        return "Local artifact has a mixed or unverified relationship to the claimed publication record; see peer_review_explanation."
    return "Local paper-level PDF parsed successfully; exact file-level version-of-record status was not independently reverified."


def status_code(state: str, category: str, paper_id: str = "") -> str:
    if paper_id == "matveyenko_2026_muse":
        return "PR-ACL-INDUSTRY"
    if paper_id == "ta_0373_2026_maerz":
        return "NON-PR-OTHER"
    return {
        "A1": "PR-MAIN-NLP",
        "A2": "PR-ACL-FINDINGS",
        "B": "PR-JOURNAL",
        "C1": "PR-OTHER-CONF",
        "C2": "PR-SHORT-SPECIALIST",
        "CTX": "PR-CONTEXT",
    }.get(category, {
        "PR_NO": "PREPRINT",
        "PR_ACCEPTED_NO_VOR": "ACCEPTED-NO-VOR",
        "PR_MIXED": "MIXED-STATUS",
        "PR_UNKNOWN": "VERIFY-STATUS",
    }.get(state, "VERIFY-STATUS"))


def build_base_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    master_by_id = {record["Paper ID"]: record for record in master["evidence_records"]}
    records: list[dict[str, Any]] = []

    for source_group, items in inventory["groups"].items():
        for item in items:
            paper_id = item["paper_id"]
            if paper_id not in master_by_id:
                raise RuntimeError(f"Inventory paper missing from canonical master: {paper_id}")
            canonical = master_by_id[paper_id]
            category = category_for(item, source_group)
            state, explanation = peer_review_state(paper_id, category)
            source_path = item["source_path"]
            records.append({
                "record_scope": "canonical evidence record",
                "paper_id": paper_id,
                "title": canonical["Title"],
                "authors": canonical["Authors"],
                "year": str(first_year(canonical["Year"]) or item["year"]),
                "venue": SPECIAL_VENUE.get(paper_id, canonical["Venue"]),
                "publication_type": canonical["Publication type"],
                "evidence_classification": canonical["Core or adjacent classification"],
                "peer_review_state": state,
                "peer_review_explanation": explanation,
                "venue_class": category,
                "venue_tier_note": tier_note(paper_id, category),
                "canonical_peer_review_status": canonical["Peer-reviewed status"],
                "publication_history_notes": canonical["Publication history notes"],
                "external_status_check": EXTERNAL_STATUS_NOTES.get(
                    paper_id,
                    "Canonical review status retained; no separate web re-verification performed for this record on 2026-08-25.",
                ),
                "local_artifact_status": local_artifact_status(item, category),
                "source_path": source_path,
                "source_sha256": item["sha256"],
                "doi": canonical["DOI"],
                "url": canonical["URL"],
                "category": category,
            })

    if len(records) != 101 or len({record["paper_id"] for record in records}) != 101:
        raise RuntimeError("Expected exactly 101 unique canonical inventory records")

    expected_categories = {"A1": 1, "A2": 10, "B": 20, "C1": 15, "C2": 9, "D": 44, "E": 2}
    actual_categories = Counter(record["category"] for record in records)
    if dict(actual_categories) != expected_categories:
        raise RuntimeError(f"Category counts changed: {dict(actual_categories)}")

    return records, master_by_id, inventory


def add_contextual_record(records: list[dict[str, Any]], inventory: dict[str, Any]) -> None:
    ledger = inventory["local_path_ledger"]["contextual_publications_outside_master"]
    if len(ledger) != 1 or ledger[0]["source_path"] != KEMPNY["source_path"]:
        raise RuntimeError("Contextual Kempny ledger changed")
    records.append({
        "record_scope": "contextual publication outside canonical evidence map",
        **KEMPNY,
        "peer_review_explanation": "The publisher PDF identifies an open-access 2026 BMC Medical Research Methodology research article.",
        "venue_class": "CTX",
        "venue_tier_note": tier_note(KEMPNY["paper_id"], "CTX"),
        "external_status_check": "Local publisher PDF inspected; DOI and journal metadata appear on page 1.",
        "local_artifact_status": "Publisher journal PDF; parsed successfully.",
        "source_sha256": ledger[0]["sha256"],
    })


def materialize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for info in CATEGORIES.values():
        (VENUE_LIBRARY / info["folder"]).mkdir(parents=True, exist_ok=True)
    for year in range(2023, 2027):
        (CHRONO_LIBRARY / f"{year}").mkdir(parents=True, exist_ok=True)

    chronological = sorted(
        records,
        key=lambda record: (int(record["year"]), record["title"].casefold(), record["paper_id"]),
    )
    per_year_position: dict[str, int] = defaultdict(int)

    for record in chronological:
        category = record["category"]
        year = record["year"]
        paper_id = record["paper_id"]
        per_year_position[year] += 1
        position = per_year_position[year]
        source = ROOT / record["source_path"]

        if paper_id == "thematic_lm_2025":
            record.update({
                "local_pdf_pages": "",
                "venue_library_destination": "",
                "chronological_destination": "",
                "copy_action": "not copied: local artifact is proceedings front matter, not the paper",
                "sha256": "",
                "non_pdf_asset_sha256": "",
            })
            notice = (
                "# Thematic-LM full text is not local\n\n"
                "The local `tmp/pdfs/www2025-proceedings.pdf` is a 112-page table-of-contents/front-matter file, not the paper on printed pages 649-658. It was not copied as if it were the article.\n\n"
                "- Official DOI: https://doi.org/10.1145/3696410.3714595\n"
                "- Public author-copy record: https://openreview.net/forum?id=jiv0Gl6sto\n"
                "- Status: peer-reviewed The Web Conference 2025 full paper\n"
                "- Local download attempts on 2026-08-25 returned HTTP 403.\n"
            )
            venue_notice = VENUE_LIBRARY / CATEGORIES[category]["folder"] / "2025__thematic_lm_2025__FULL-TEXT-NOT-LOCAL.md"
            chrono_notice = CHRONO_LIBRARY / "2025" / f"{position:03d}__PR-OTHER-CONF__thematic_lm_2025__FULL-TEXT-NOT-LOCAL.md"
            write_generated(venue_notice, notice)
            write_generated(chrono_notice, notice)
            if sha256(venue_notice) != sha256(chrono_notice):
                raise RuntimeError("Thematic-LM notice copies differ")
            record.update({
                "venue_library_destination": str(venue_notice.relative_to(ROOT)),
                "chronological_destination": str(chrono_notice.relative_to(ROOT)),
                "copy_action": "paper_level_notice_created; no PDF copied",
                "non_pdf_asset_sha256": sha256(venue_notice),
            })
            continue

        if not source.is_file():
            raise RuntimeError(f"Missing source: {record['source_path']}")
        pages = pdf_pages(source)
        digest = sha256(source)
        if digest != record["source_sha256"]:
            raise RuntimeError(f"Source SHA changed: {record['source_path']}")

        filename = f"{year}__{safe_id(paper_id)}.pdf"
        venue_destination = VENUE_LIBRARY / CATEGORIES[category]["folder"] / filename
        chrono_filename = f"{position:03d}__{status_code(record['peer_review_state'], category, paper_id)}__{safe_id(paper_id)}.pdf"
        chrono_destination = CHRONO_LIBRARY / year / chrono_filename
        copy_checked(source, venue_destination)
        copy_checked(source, chrono_destination)
        record.update({
            "local_pdf_pages": pages,
            "venue_library_destination": str(venue_destination.relative_to(ROOT)),
            "chronological_destination": str(chrono_destination.relative_to(ROOT)),
            "copy_action": "copied_or_verified_identical_in_both_libraries",
            "sha256": digest,
            "non_pdf_asset_sha256": "",
        })

    return chronological


def render_category_readmes(records: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(record)

    for key, info in CATEGORIES.items():
        items = sorted(grouped[key], key=lambda row: (int(row["year"]), row["title"].casefold()))
        lines = [
            f"# {info['label']}",
            "",
            info["description"],
            "",
            f"Records: {len(items)}. Paper-level PDFs copied: {sum(bool(row.get('sha256')) for row in items)}.",
            "",
        ]
        for row in items:
            lines.append(f"- **{row['year']} - {row['title']}**")
            lines.append(f"  - Venue: {row['venue']}")
            lines.append(f"  - Status: {row['peer_review_state']} - {row['peer_review_explanation']}")
            if row.get("venue_library_destination"):
                lines.append(f"  - File: `{Path(row['venue_library_destination']).name}`")
            else:
                lines.append("  - File: paper-level PDF is not locally available; see the notice file.")
        lines.extend(["", "See `../publication_manifest.csv` for DOI, source, version, and audit details."])
        write_generated(VENUE_LIBRARY / info["folder"] / "README.md", "\n".join(lines))


def render_venue_root_readme(records: list[dict[str, Any]], inventory: dict[str, Any]) -> None:
    category_counts = Counter(row["category"] for row in records)
    copied_count = sum(bool(row.get("sha256")) for row in records)
    peer_reviewed_count = sum(
        row["peer_review_state"] in {"PR_YES", "PR_VENUE_SUPPORTED"} for row in records
    )
    lines = [
        "# Recent relevant publications, organized by status and venue (2023-2026)",
        "",
        f"This library contains **{copied_count} paper PDFs** plus one paper-level full-text notice. Of the {len(records)} represented publication records, **{peer_reviewed_count} are classified as peer reviewed or venue-supported**, and the remainder are visibly separated as preprints, accepted-without-verified-VOR items, or status/venue edge cases.",
        "",
        "Original files were copied, not moved, so the literature-review provenance paths remain intact.",
        "",
        "## How to interpret the folders",
        "",
        "Peer review and venue standing are separate fields. A paper can be peer reviewed without being a flagship venue, and a local PDF can be an author manuscript even when the canonical publication family later appeared in a peer-reviewed venue.",
        "",
        "- `PR_YES`: the canonical review identifies a peer-reviewed archival publication.",
        "- `PR_VENUE_SUPPORTED`: an established publisher/venue record supports publication status, but the old canonical peer-review field was not explicit.",
        "- `PR_NO`: preprint, manuscript, or non-peer-reviewed output at the cutoff.",
        "- `PR_ACCEPTED_NO_VOR`: acceptance/presentation was reported, but no archival version of record was verified at the cutoff.",
        "- `PR_MIXED`: a peer-reviewed short version and a separate non-peer-reviewed expansion coexist.",
        "- `PR_UNKNOWN`: local evidence is insufficient; this is not a claim that the venue is poor or predatory.",
        "",
        "## Counts",
        "",
        "| Class | Records | Meaning |",
        "|---|---:|---|",
    ]
    for key in ("A1", "A2", "B", "C1", "C2", "D", "E", "CTX"):
        lines.append(f"| {key} | {category_counts[key]} | {CATEGORIES[key]['label']} |")
    lines.extend([
        "",
        "## Important boundaries",
        "",
        "- Findings papers are peer reviewed and archival, but are not labeled as ACL/EMNLP/NAACL main-track papers.",
        "- Workshop, poster, proposal, protocol, and extended-abstract status remains visible; peer review does not turn these into full empirical main-conference papers.",
        "- MDPI or any other publisher identity was neither a promotion rule nor an exclusion rule.",
        "- Preprints with a later verified journal/conference version are counted once as one publication family; the manifest identifies when the local PDF is still a manuscript copy.",
        f"- Classification cutoff: **{REVIEW_CUTOFF}**. Records can change after that date.",
        "- Thematic-LM is confirmed as a peer-reviewed WWW 2025 paper, but the local file is only proceedings front matter; it is represented by a notice instead of a misleading 112-page copy.",
        "",
        "## Audit files",
        "",
        "- `publication_manifest.csv`: paper-by-paper status, venue class, DOI, local artifact type, sources, hashes, and both destinations.",
        "- `canonical_records_not_copied.csv`: recent canonical records for which no preferred local paper-level PDF was copied.",
        "- `source_file_ledger.csv`: exact duplicates, superseded versions, exclusions, invalid download stubs, and the out-of-window record.",
        "",
        f"Inventory SHA-256: `{sha256(INVENTORY_PATH)}`  ",
        f"Canonical master SHA-256: `{sha256(MASTER_PATH)}`",
    ])
    write_generated(VENUE_LIBRARY / "README.md", "\n".join(lines))


def render_chronological(records: list[dict[str, Any]]) -> None:
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_year[record["year"]].append(record)

    progression = {
        "2023": "Early work centered on LLM-in-the-loop coding and human-facing code suggestion, establishing feasibility while keeping analysts close to the process.",
        "2024": "The field broadened into collaborative interfaces, concept induction, saturation experiments, multilingual coding, and early multi-agent pipelines; many contributions were still preprints.",
        "2025": "Research moved toward hierarchical and ensemble coding, larger-scale automation, explicit bias tests, and stronger human comparisons. Multi-agent systems also grew quickly.",
        "2026": "The literature shifted from basic feasibility toward provenance, reflexivity, source/participant coverage, disagreement, calibration, sensitive-domain failures, and purpose-built evaluation—including direct evidence that agreement need not imply quality. Peer-reviewed studies increased, but a large preprint frontier remains.",
    }
    lines = [
        "# Chronological reading library: how the field progressed (2023-2026)",
        "",
        "Papers are grouped by publication year from oldest to newest. Within a year they follow a deterministic title sort (including any leading punctuation) because exact publication months are not consistently verified across all records. The filename includes a status code so chronology never obscures peer-review status.",
        "",
        "**Scope:** this is a timeline of the **102 locally represented records**, not the entire 237-record evidence map. There are **119 additional recent canonical records not represented by a local asset**. In total, 120 canonical records lack a copied paper PDF (2023: 1; 2024: 13; 2025: 70; 2026: 36), because Thematic-LM is represented here by a notice rather than a PDF. See `full_canonical_metadata_timeline.csv` and `canonical_records_not_copied.csv`. Progression statements below describe the local corpus only.",
        "",
        "**Artifact warning:** filename status describes the canonical publication family. At least 17 `PR-*` files are author, preprint, or repository copies of later peer-reviewed works rather than publisher versions of record; consult `local_artifact_status` in the manifest.",
        "",
        "## Status codes in filenames",
        "",
        "- `PR-MAIN-NLP`, `PR-ACL-FINDINGS`, `PR-JOURNAL`, `PR-OTHER-CONF`, `PR-SHORT-SPECIALIST`, `PR-CONTEXT`: peer-reviewed categories.",
        "- `PR-ACL-INDUSTRY`: peer-reviewed ACL Industry Track, kept distinct from both main track and Findings.",
        "- `PREPRINT`: not peer reviewed or archival status unverified at the cutoff.",
        "- `NON-PR-OTHER`: non-peer-reviewed output that is not a research preprint (for example software/package documentation).",
        "- `ACCEPTED-NO-VOR`: acceptance/presentation reported, final archival record not verified.",
        "- `MIXED-STATUS`: peer-reviewed short paper plus a separate non-peer-reviewed expansion.",
        "- `VERIFY-STATUS`: venue or peer-review evidence remains uncertain.",
        "",
        "## Progression at a glance",
        "",
    ]
    for year in ("2023", "2024", "2025", "2026"):
        items = sorted(by_year[year], key=lambda row: (row["title"].casefold(), row["paper_id"]))
        reviewed = sum(row["peer_review_state"] in {"PR_YES", "PR_VENUE_SUPPORTED"} for row in items)
        copied = sum(bool(row.get("sha256")) for row in items)
        lines.extend([
            f"### {year}",
            "",
            progression[year],
            "",
            f"Represented records: {len(items)}; peer-reviewed/venue-supported: {reviewed}; paper PDFs copied: {copied}.",
            "",
        ])
        for row in items:
            token = status_code(row["peer_review_state"], row["category"], row["paper_id"])
            lines.append(f"- **[{token}] {row['title']}** - {row['venue']}")
        lines.append("")

        year_lines = [
            f"# {year}",
            "",
            progression[year],
            "",
            "Files are alphabetized by title, not by an invented month/day. Status is encoded in every filename.",
            "",
        ]
        for row in items:
            token = status_code(row["peer_review_state"], row["category"], row["paper_id"])
            year_lines.append(f"- **[{token}] {row['title']}** - {row['venue']}")
            if row.get("chronological_destination"):
                year_lines.append(f"  - `{Path(row['chronological_destination']).name}`")
            else:
                year_lines.append("  - Paper-level PDF unavailable locally; see the notice file.")
        write_generated(CHRONO_LIBRARY / year / "README.md", "\n".join(year_lines))

    lines.extend([
        "## Interpretation caution",
        "",
        "The timeline shows publication activity, not cumulative proof that automated thematic analysis became valid. The main progression is from feasibility and workflow building toward harder questions about construct validity, provenance, omission, participant/source coverage, disagreement, and calibrated human oversight.",
        "",
        "See `chronological_manifest.csv` for the exact status and venue classification behind every filename.",
        "",
        "For a year-ordered metadata index of all 220 canonical 2023-2026 records—including the 119 without any local asset—see `full_canonical_metadata_timeline.csv`.",
    ])
    write_generated(CHRONO_LIBRARY / "README.md", "\n".join(lines))


def write_manifests(
    records: list[dict[str, Any]],
    master_by_id: dict[str, dict[str, Any]],
    inventory: dict[str, Any],
) -> None:
    manifest_rows = []
    for record in sorted(records, key=lambda row: (int(row["year"]), row["title"].casefold())):
        manifest_rows.append({
            key: record.get(key, "")
            for key in MANIFEST_FIELDS
        } | {"review_cutoff": REVIEW_CUTOFF})
    write_csv(VENUE_LIBRARY / "publication_manifest.csv", manifest_rows, MANIFEST_FIELDS)
    write_csv(CHRONO_LIBRARY / "chronological_manifest.csv", manifest_rows, MANIFEST_FIELDS)

    represented_by_id = {
        row["paper_id"]: row
        for row in records
        if row["record_scope"] == "canonical evidence record"
    }
    full_timeline_rows: list[dict[str, Any]] = []
    for paper_id, row in master_by_id.items():
        year = first_year(row["Year"])
        if year is None or not 2023 <= year <= 2026:
            continue
        represented = represented_by_id.get(paper_id)
        if represented is None:
            local_status = "no local asset in the organized library"
            destination = ""
        elif paper_id == "thematic_lm_2025":
            local_status = "notice only; no paper-level PDF"
            destination = represented.get("chronological_destination", "")
        else:
            local_status = "paper PDF copied"
            destination = represented.get("chronological_destination", "")
        full_timeline_rows.append({
            "paper_id": paper_id,
            "year": year,
            "title": row["Title"],
            "authors": row["Authors"],
            "venue": row["Venue"],
            "publication_type": row["Publication type"],
            "peer_review_status": row["Peer-reviewed status"],
            "evidence_classification": row["Core or adjacent classification"],
            "doi": row["DOI"],
            "url": row["URL"],
            "local_library_status": local_status,
            "chronological_destination": destination,
        })
    full_timeline_rows.sort(key=lambda row: (int(row["year"]), row["title"].casefold(), row["paper_id"]))
    for sequence, row in enumerate(full_timeline_rows, start=1):
        row["sequence"] = sequence
    full_timeline_fields = [
        "sequence", "paper_id", "year", "title", "authors", "venue",
        "publication_type", "peer_review_status", "evidence_classification",
        "doi", "url", "local_library_status", "chronological_destination",
    ]
    write_csv(
        CHRONO_LIBRARY / "full_canonical_metadata_timeline.csv",
        full_timeline_rows,
        full_timeline_fields,
    )

    inventoried_ids = {row["paper_id"] for row in records if row["record_scope"] == "canonical evidence record"}
    missing_rows = []
    thematic = master_by_id["thematic_lm_2025"]
    missing_rows.append({
        "paper_id": thematic["Paper ID"],
        "title": thematic["Title"],
        "year": thematic["Year"],
        "venue": thematic["Venue"],
        "peer_review_status": thematic["Peer-reviewed status"],
        "doi": thematic["DOI"],
        "url": thematic["URL"],
        "reason": "Inventory path is proceedings front matter/table of contents, not a paper-level PDF; public author-copy download returned HTTP 403.",
    })
    for paper_id, row in master_by_id.items():
        year = first_year(row["Year"])
        if year is None or not 2023 <= year <= 2026 or paper_id in inventoried_ids:
            continue
        missing_rows.append({
            "paper_id": paper_id,
            "title": row["Title"],
            "year": year,
            "venue": row["Venue"],
            "peer_review_status": row["Peer-reviewed status"],
            "doi": row["DOI"],
            "url": row["URL"],
            "reason": "No preferred paper-level PDF was present in the inventoried local source roots at organization time.",
        })
    missing_fields = ["paper_id", "title", "year", "venue", "peer_review_status", "doi", "url", "reason"]
    missing_rows.sort(key=lambda row: (int(first_year(row["year"]) or 9999), row["title"].casefold()))
    write_csv(VENUE_LIBRARY / "canonical_records_not_copied.csv", missing_rows, missing_fields)
    write_csv(CHRONO_LIBRARY / "canonical_records_not_copied.csv", missing_rows, missing_fields)

    ledger_rows: list[dict[str, Any]] = []
    for ledger_type, items in inventory["local_path_ledger"].items():
        if ledger_type == "contextual_publications_outside_master":
            continue
        for item in items:
            ledger_rows.append({
                "ledger_type": ledger_type,
                "source_path": item.get("source_path", item.get("duplicate_source_path", "")),
                "preferred_source_path": item.get("preferred_source_path", ""),
                "paper_id": item.get("paper_id", ""),
                "title": item.get("title", ""),
                "decision": item.get("decision", ""),
                "reason": item.get("reason", ""),
                "sha256": item.get("sha256", ""),
            })
    ledger_fields = ["ledger_type", "source_path", "preferred_source_path", "paper_id", "title", "decision", "reason", "sha256"]
    ledger_rows.sort(key=lambda row: (row["ledger_type"], row["source_path"]))
    write_csv(VENUE_LIBRARY / "source_file_ledger.csv", ledger_rows, ledger_fields)


def validate(records: list[dict[str, Any]]) -> dict[str, Any]:
    copied = [record for record in records if record.get("sha256")]
    if len(copied) != 101:
        raise RuntimeError(f"Expected 101 copied PDFs including Kempny, found {len(copied)}")
    if len(records) != 102:
        raise RuntimeError(f"Expected 102 represented records including Kempny, found {len(records)}")
    if len({record["paper_id"] for record in records}) != len(records):
        raise RuntimeError("Duplicate paper IDs in final library")

    destination_hashes: dict[str, str] = {}
    for record in copied:
        source_digest = record["sha256"]
        for field in ("venue_library_destination", "chronological_destination"):
            destination = ROOT / record[field]
            pages = pdf_pages(destination)
            if pages != int(record["local_pdf_pages"]):
                raise RuntimeError(f"Page-count mismatch at {destination}")
            digest = sha256(destination)
            if digest != source_digest:
                raise RuntimeError(f"Copy hash mismatch at {destination}")
            if str(destination) in destination_hashes:
                raise RuntimeError(f"Duplicate destination path: {destination}")
            destination_hashes[str(destination)] = digest

    thematic = next(record for record in records if record["paper_id"] == "thematic_lm_2025")
    for field in ("venue_library_destination", "chronological_destination"):
        notice_path = ROOT / thematic[field]
        if not notice_path.is_file() or sha256(notice_path) != thematic["non_pdf_asset_sha256"]:
            raise RuntimeError(f"Thematic-LM notice validation failed: {notice_path}")

    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    eligible_recent_ids = {
        row["Paper ID"]
        for row in master["evidence_records"]
        if (year := first_year(row["Year"])) is not None and 2023 <= year <= 2026
    }
    represented_canonical_ids = {
        row["paper_id"] for row in records if row["record_scope"] == "canonical evidence record"
    }
    unrepresented_ids = eligible_recent_ids - represented_canonical_ids
    if len(eligible_recent_ids) != 220 or len(unrepresented_ids) != 119:
        raise RuntimeError("Canonical recent-record coverage counts changed")

    category_counts = Counter(record["category"] for record in records)
    peer_states = Counter(record["peer_review_state"] for record in records)
    return {
        "represented_record_count": len(records),
        "represented_canonical_record_count": 101,
        "eligible_recent_canonical_record_count": 220,
        "unrepresented_recent_canonical_record_count": 119,
        "canonical_without_copied_paper_pdf_count": 120,
        "contextual_record_count": 1,
        "paper_pdf_count_per_library": len(copied),
        "paper_level_notice_count_per_library": 1,
        "category_counts": dict(sorted(category_counts.items())),
        "peer_review_state_counts": dict(sorted(peer_states.items())),
        "all_copied_pdf_hashes_match_sources": True,
        "all_copied_pdfs_have_at_least_one_page": True,
        "original_sources_moved": False,
        "classification_cutoff": REVIEW_CUTOFF,
        "inventory_sha256": sha256(INVENTORY_PATH),
        "master_sha256": sha256(MASTER_PATH),
    }


def main() -> None:
    records, master_by_id, inventory = build_base_records()
    add_contextual_record(records, inventory)
    chronological = materialize(records)
    render_category_readmes(chronological)
    render_venue_root_readme(chronological, inventory)
    render_chronological(chronological)
    write_manifests(chronological, master_by_id, inventory)
    validation = validate(chronological)
    validation_text = json.dumps(validation, indent=2, ensure_ascii=False) + "\n"
    (VENUE_LIBRARY / "validation_summary.json").write_text(validation_text, encoding="utf-8")
    (CHRONO_LIBRARY / "validation_summary.json").write_text(validation_text, encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
