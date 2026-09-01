#!/usr/bin/env python3
"""Build a non-destructive, two-tier reading library from local paper PDFs."""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECENT = ROOT / "recent papers"
LOW = ROOT / "low priority"


# Reading order, source path, readable destination name, title, venue.
MUST_READ = [
    (1, "research/fulltext/latest/2604.10834.pdf", "2026_Camporese_Security_Comments_ICPC.pdf", "LLMs for Qualitative Data Analysis Fail on Security-specific Comments in Human Experiments", "ICPC 2026"),
    (2, "research/fulltext/latest/chen_2026_open_codes.pdf", "2026_Chen_Open_Code_Metrics_ACL.pdf", "A Computational Method for Measuring Open Codes in Qualitative Analysis", "Findings of ACL 2026"),
    (3, "research/fulltext/latest/education_2026_inductive_coding.pdf", "2026_Dorfel_Inductive_Coding_Education_Sciences.pdf", "Evaluation of Inductive Coding with LLMs", "Education Sciences"),
    (4, "research/fulltext/latest/gatos_2026.pdf", "2026_Katz_GATOS_HSSC.pdf", "Thematic Analysis with Open-Source Generative AI and Machine Learning", "Humanities and Social Sciences Communications"),
    (6, "research/fulltext/latest/matveyenko_2026_muse.pdf", "2026_Matveyenko_Muse_ACL.pdf", "Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant", "ACL 2026 Industry Track"),
    (7, "research/fulltext/latest/wang_2026_centaurta.pdf", "2026_Wang_CentaurTA_ACL.pdf", "CentaurTA: A Self-Improving Human-Agents Collaboration Framework", "Findings of ACL 2026"),
    (8, "research/fulltext/latest/zhu_2026_trauma.pdf", "2026_Zhu_Trauma_ACL.pdf", "Can LLMs Understand the Impact of Trauma?", "Findings of ACL 2026"),
    (10, "research/fulltext/screening_2020_2024/2304.07366.pdf", "2024_Gao_CollabCoder_CHI.pdf", "CollabCoder: A Lower-barrier, Rigorous Workflow for Inductive Collaborative Qualitative Analysis", "CHI 2024"),
    (11, "research/fulltext/screening_2020_2024/2305.13014.pdf", "2024_De_Paoli_Inductive_Thematic_Analysis_SSCR.pdf", "Performing an Inductive Thematic Analysis of Semi-Structured Interviews With an LLM", "Social Science Computer Review"),
    (12, "tmp/pdfs/dai2023.pdf", "2023_Dai_LLM_in_the_Loop_EMNLP.pdf", "LLM-in-the-loop: Leveraging Large Language Models for Thematic Analysis", "Findings of EMNLP 2023"),
    (13, "research/fulltext/screening_2020_2024/2309.17447.pdf", "2024_Parker_Educational_Survey_Feedback_IJAIED.pdf", "A Large Language Model Approach to Educational Survey Feedback Analysis", "International Journal of Artificial Intelligence in Education"),
    (14, "research/fulltext/screening_2020_2024/2405.05758.pdf", "2026_Meng_Human_LLM_Synergy_TOCHI.pdf", "Exploring the Human-LLM Synergy in Advancing Theory-driven Qualitative Analysis", "ACM TOCHI"),
    (15, "research/fulltext/screening_2020_2024/FC_prompting_panacea_edm2024.pdf", "2024_Ganesh_Prompting_as_Panacea_EDM.pdf", "Prompting as Panacea? A Case Study for Qualitative Coding of Classroom Dialog", "EDM 2024"),
    (16, "research/fulltext/screening_2020_2024/TA-0901_repository.pdf", "2024_Liu_Potential_and_Limits_ICQE.pdf", "Assessing the Potential and Limits of Large Language Models in Qualitative Coding", "Advances in Quantitative Ethnography"),
    (17, "research/fulltext/screening_2020_2024/TA-0954_fischer-biemann-2024-exploring.pdf", "2024_Fischer_Exploring_LLMs_for_QDA_NLP4DH.pdf", "Exploring Large Language Models for Qualitative Data Analysis", "NLP4DH 2024"),
    (19, "research/fulltext/screening_2020_2024/TA-1114_repository.pdf", "2023_Spinoso_Qualitative_Code_Suggestion_EMNLP.pdf", "Qualitative Code Suggestion: A Human-Centric Approach", "Findings of EMNLP 2023"),
    (20, "research/fulltext/screening_2020_2024/TA-1291_openalex.pdf", "2025_Islam_Latent_Themes_ICWSM.pdf", "Discovering Latent Themes in Social Media Messaging", "ICWSM 2025"),
    (21, "research/fulltext/screening_2020_2024/TA-1307_openalex.pdf", "2026_Object_Axial_Coding_ECIR.pdf", "From Quotes to Concepts: Axial Coding of Political Debates with Ensemble LMs", "ECIR 2026"),
    (24, "my papers/3828752 (1).pdf", "2026_Yi_TAMA_ACM_TCH.pdf", "TAMA: A Human-AI Collaborative Thematic Analysis Framework", "ACM Transactions on Computing for Healthcare"),
    (25, "tmp/pdfs/hicode2025.pdf", "2025_Zhong_HICode_EMNLP.pdf", "HICode: Hierarchical Inductive Coding with LLMs", "EMNLP 2025"),
    (26, "tmp/pdfs/details2025full.pdf", "2025_Sharma_DeTAILS_CUI.pdf", "DeTAILS: Deep Thematic Analysis with Iterative LLM Support", "ACM CUI 2025"),
    (27, "tmp/pdfs/lloom2024.pdf", "2024_Lam_LLooM_CHI.pdf", "Concept Induction with LLooM", "CHI 2024"),
    (28, "tmp/pdfs/quallm2025.pdf", "2025_Rao_QuaLLM_NAACL.pdf", "QuaLLM: Extracting Quantitative Insights from Online Forums", "Findings of NAACL 2025"),
    (29, "tmp/pdfs/parfenova2025.pdf", "2025_Parfenova_Text_Annotation_Inductive_Coding_NAACL.pdf", "Text Annotation via Inductive Coding: Comparing Human Experts to LLMs", "Findings of NAACL 2025"),
    (30, "tmp/pdfs/parfenova_eval2025.pdf", "2025_Parfenova_Measuring_What_Matters_ACL.pdf", "Measuring What Matters: Ensemble LLMs with Label Refinement", "Findings of ACL 2025"),
    (31, "tmp/pdfs/ashwin2025.pdf", "2025_Ashwin_Serious_Bias_SMR.pdf", "Using Large Language Models for Qualitative Analysis Can Introduce Serious Bias", "Sociological Methods & Research"),
    (32, "research/fulltext/second_pass_2026/FC-03_2601.15445.pdf", "2026_Ye_Reflexis_CHI.pdf", "Reflexis: Supporting Reflexivity and Rigor through Design for Deliberation", "CHI 2026"),
    (33, "research/fulltext/second_pass_2026/FC-12_2402.06124.pdf", "2026_Lee_Teleoscope_CHI.pdf", "Crystallizing Schemas with Teleoscope", "CHI 2026"),
    (34, "research/fulltext/second_pass_2026/FC-11_author.pdf", "2026_Beltran_Manifold_Thematic_Analysis_CCIS.pdf", "Manifold-Based Clustering for Inductive Thematic Analysis", "Springer CCIS / SEET"),
    (35, "research/fulltext/second_pass_2026/FC-15_author.pdf", "2026_Li_Confidence_Calibration_AIED.pdf", "Evaluating and Improving LLM Confidence Calibration in Educational Dialogue Coding", "AIED 2026"),
    (34, "research/fulltext/second_pass_2026/TA-0054_publisher.pdf", "2026_Berkmortel_Nurse_Sentiment_JMIR.pdf", "Comparative Content Analysis of GPT-5, Gemini, and Human Coding", "Journal of Medical Internet Research"),
    (35, "research/fulltext/second_pass_2026/TA-0077_official.pdf", "2026_Wahbeh_AutoTheme_HICSS.pdf", "AutoTheme: A Multi-Agent Framework for Inductive Thematic Analysis", "HICSS 2026"),
    (36, "research/fulltext/second_pass_2026/TA-0120_official.pdf", "2026_Hutchinson_AI_vs_Human_Coding_OJPHI.pdf", "Comparison of AI Tools With Human Coding for Public Health Data", "Online Journal of Public Health Informatics"),
    (37, "research/fulltext/second_pass_2026/TA-0151_2601.12618.pdf", "2026_Tajik_Disagreement_as_Data_LAK.pdf", "Disagreement as Data: Reasoning Trace Analytics", "LAK 2026"),
    (38, "research/fulltext/second_pass_2026/TA-0264_publisher.pdf", "2026_Xu_Autism_Annotation_JMIR.pdf", "LLM-Assisted Annotation for Online Autism Communities", "Journal of Medical Internet Research"),
    (39, "research/fulltext/second_pass_2026/TA-0336_osf.pdf", "2026_Nguyen_NITA_QRP.pdf", "Narrative-Integrated Thematic Analysis: Theme Generation Without Coding", "Qualitative Research in Psychology"),
    (40, "research/fulltext/second_pass_2026/TA-0338_2601.12181.pdf", "2026_Ma_AI_Companions_CHI.pdf", "Negotiating Digital Identities with AI Companions", "CHI 2026"),
    (40, "research/fulltext/second_pass_2026/TA-0345_author.pdf", "2026_Habib_Cochlear_Implant_Human_LLM_AJA.pdf", "Patient Experiences in the Cochlear Implant Reddit Community", "American Journal of Audiology"),
    (41, "research/fulltext/second_pass_2026/TA-0351_official.pdf", "2026_Fischer_Perspectives_NLP4DH.pdf", "Perspectives: Interactive Document Clustering for Qualitative Data Analysis", "NLP4DH 2026"),
    (42, "research/fulltext/second_pass_2026/TA-0360_arxiv.pdf", "2026_Khalid_Prompt_Engineering_SSCR.pdf", "Prompt Engineering for LLM-Assisted Inductive Thematic Analysis", "Social Science Computer Review"),
    (43, "research/fulltext/second_pass_2026/TA-0370_arxiv.pdf", "2026_Ngo_Open_Source_Qualitative_Coding_CHI.pdf", "Qualitative Coding Through Open-Source LLMs", "CHI 2026 Extended Abstracts"),
    (44, "research/fulltext/second_pass_2026/TA-0382_arxiv.pdf", "2026_Chen_RAEC_PSB.pdf", "Retrieval-Augmented Guardrails for AI-Drafted Patient Messages", "Pacific Symposium on Biocomputing"),
    (44, "research/fulltext/second_pass_2026/TA-0453_publisher.pdf", "2026_Galatzer_Levy_Veteran_Narratives_JMIR.pdf", "LLM Analysis of Veteran Transition Stress Narratives", "JMIR Mental Health"),
    (45, "research/fulltext/second_pass_2026/TA-0460_publisher.pdf", "2026_Kivity_Chronic_Illness_Thematic_Analysis_JMIR.pdf", "LLM-Supported Thematic Analysis of Chronic Illness Experiences", "Journal of Medical Internet Research"),
    (46, "tmp/pdfs/yu2025.pdf", "2025_Yu_Same_Company_Same_Signal_ACL.pdf", "Same Company, Same Signal: Identity Confounds in Earnings Calls", "Findings of ACL 2025"),
]

# Keep the displayed reading order contiguous after editorial changes above.
MUST_READ = [
    (order, source, filename, title, venue)
    for order, (_, source, filename, title, venue) in enumerate(MUST_READ, start=1)
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_pdf(path: Path) -> bool:
    return subprocess.run(
        ["pdfinfo", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def low_name(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.parts[0] == "research" and len(rel.parts) >= 4:
        bucket = rel.parts[2]
    else:
        bucket = rel.parts[0].replace(" ", "_")
    return f"{bucket}__{path.name}"


def copy_checked(source: Path, destination: Path) -> None:
    if destination.exists():
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"Refusing to overwrite a different file: {destination}")
        return
    shutil.copy2(source, destination)


def main() -> None:
    RECENT.mkdir(exist_ok=True)
    LOW.mkdir(exist_ok=True)

    must_by_path = {source: (order, filename, title, venue) for order, source, filename, title, venue in MUST_READ}
    for source in must_by_path:
        path = ROOT / source
        if not path.is_file() or not is_pdf(path):
            raise RuntimeError(f"Missing or invalid MUST READ source: {source}")

    sources = []
    for base in (ROOT / "research/fulltext", ROOT / "my papers", ROOT / "tmp/pdfs"):
        sources.extend(sorted(base.rglob("*.pdf")))

    groups: dict[str, list[Path]] = {}
    invalid: list[Path] = []
    for path in sources:
        if not is_pdf(path):
            invalid.append(path)
            continue
        groups.setdefault(sha256(path), []).append(path)

    rows = []
    recent_entries = []
    recent_count = 0
    low_count = 0
    duplicate_count = 0

    for digest, paths in sorted(groups.items(), key=lambda item: min(str(p) for p in item[1])):
        rels = [str(path.relative_to(ROOT)) for path in paths]
        must_sources = [rel for rel in rels if rel in must_by_path]
        if must_sources:
            representative_rel = min(must_sources, key=lambda rel: must_by_path[rel][0])
            order, filename, title, venue = must_by_path[representative_rel]
            destination = RECENT / f"{order:02d}_{filename}"
            priority = "MUST READ"
            note = f"Selected: relevant peer-reviewed paper in {venue}."
            recent_entries.append((order, title, venue, destination.name))
            recent_count += 1
        else:
            representative_rel = min(rels)
            destination = LOW / low_name(ROOT / representative_rel)
            priority = "low priority"
            note = "Not selected for the 45-paper reputable-venue reading list."
            low_count += 1

        representative = ROOT / representative_rel
        copy_checked(representative, destination)
        for path in paths:
            rel = str(path.relative_to(ROOT))
            is_rep = path == representative
            if not is_rep:
                duplicate_count += 1
            rows.append({
                "source_path": rel,
                "sha256": digest,
                "priority": priority,
                "action": "copied" if is_rep else "exact duplicate; not copied again",
                "destination": str(destination.relative_to(ROOT)),
                "note": note if is_rep else f"Exact duplicate of {representative_rel}.",
            })

    for path in invalid:
        rows.append({
            "source_path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "priority": "not a valid paper PDF",
            "action": "skipped",
            "destination": "",
            "note": "The file has a .pdf name but does not contain PDF data (download/error stub).",
        })

    if recent_count != len(MUST_READ):
        raise RuntimeError(f"Expected {len(MUST_READ)} MUST READ copies, found {recent_count}")

    manifest = ROOT / "paper_organization_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_path", "sha256", "priority", "action", "destination", "note"])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["source_path"]))

    recent_lines = [
        "# MUST READ — reputable conference and journal papers",
        "",
        f"This folder contains {recent_count} selected papers. Most are from 2024–2026; a few earlier papers are retained as foundations.",
        "",
        "Selection rule: directly relevant to LLM-assisted qualitative analysis, peer-reviewed or formally published/accepted, and placed in an established journal or conference. Original source files remain in place so the review archive stays reproducible.",
        "",
        "## Suggested reading order",
        "",
    ]
    for order, title, venue, filename in sorted(recent_entries):
        recent_lines.append(f"{order}. **{title}** — {venue}  ")
        recent_lines.append(f"   `{filename}`")
    recent_lines.extend(["", "See `../paper_organization_manifest.csv` for source paths and hashes.", ""])
    (RECENT / "README.md").write_text("\n".join(recent_lines), encoding="utf-8")

    low_lines = [
        "# Low-priority papers",
        "",
        f"This folder contains {low_count} other unique, valid paper PDFs.",
        "",
        "These include preprints, background or adjacent studies, less central applications, older/alternate versions, and papers outside the 45-item reputable-venue reading list. They are retained for reference, not rejected as invalid scholarship.",
        "",
        "Original source files remain in place. See `../paper_organization_manifest.csv` for source paths, hashes, duplicate handling, and skipped download-error stubs.",
        "",
    ]
    (LOW / "README.md").write_text("\n".join(low_lines), encoding="utf-8")

    print(f"MUST READ copied: {recent_count}")
    print(f"Low priority copied: {low_count}")
    print(f"Exact duplicate source copies skipped: {duplicate_count}")
    print(f"Invalid .pdf download stubs skipped: {len(invalid)}")


if __name__ == "__main__":
    main()
