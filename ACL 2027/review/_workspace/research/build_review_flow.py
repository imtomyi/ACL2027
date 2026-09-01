#!/usr/bin/env python3
"""Build the auditable search/screening flow for the ACL 2027 scoping review.

This file deliberately separates reproducible machine triage from eligibility
decisions supported by full-text extraction.  It must not be used to describe
machine triage as independent human screening.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
CUTOFF = "2026-08-24"


def read_json(name: str):
    with (RESEARCH / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = value.replace("large language models", "large language model")
    value = value.replace("llms", "llm")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def canonical_doi(value: str | None) -> str:
    value = (value or "").strip().lower()
    value = value.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if value in {"", "not reported", "none"}:
        return ""
    return value


def arxiv_id(*values: str | None) -> str:
    text = " ".join(value or "" for value in values).lower()
    match = re.search(
        r"(?:10\.48550/arxiv\.|arxiv(?:\.org/(?:abs|pdf)/|:))(?P<id>\d{4}\.\d+)",
        text,
    )
    return match.group("id") if match else ""


def canonical_key(item: dict) -> str:
    doi = canonical_doi(item.get("doi"))
    if doi and not doi.startswith("10.48550/arxiv."):
        return "doi:" + doi
    aid = arxiv_id(doi, item.get("url"), item.get("official_url"), item.get("citation"))
    if aid:
        return "arxiv:" + aid
    return "id:" + (item.get("id") or normalize_title(item.get("citation", ""))[:100])


# Stable titles for matching inspected reports to the database union.  They are
# bibliographic labels, not inferred study findings.
TITLE_BY_ID = {
    "dai_2023_llm_in_loop": "LLM-in-the-loop: Leveraging Large Language Model for Thematic Analysis",
    "parfenova_2024_proposal": "Automating Qualitative Data Analysis with Large Language Models",
    "parfenova_2025_inductive_coding": "Text Annotation via Inductive Coding: Comparing Human Experts to LLMs in Qualitative Data Analysis",
    "parfenova_pfeffer_2025_ensemble": "Measuring What Matters: Evaluating Ensemble LLMs with Label Refinement in Inductive Coding",
    "hicode_2025": "HICode: Hierarchical Inductive Coding with LLMs",
    "quallm_2025": "QuaLLM: An LLM-based Framework to Extract Quantitative Insights from Online Forums",
    "thematic_lm_2025": "Thematic-LM: A LLM-based Multi-agent System for Large-scale Thematic Analysis",
    "lloom_2024": "Concept Induction: Analyzing Unstructured Text with High-Level Concepts Using LLooM",
    "details_2025": "DeTAILS: Deep Thematic Analysis with Iterative LLM Support",
    "chen_2026_open_code_metrics": "A Computational Method for Measuring Open Codes in Qualitative Analysis",
    "centaurta_2026": "CentaurTA: A Self-Improving Human-Agents Collaboration Framework for Thematic Analysis",
    "auto_ta_2025": "Auto-TA: Towards Scalable Automated Thematic Analysis via Multi-Agent Large Language Models with Reinforcement Learning",
    "sft_ta_2025": "SFT-TA: Supervised Fine-Tuned Agents in Multi-Agent LLMs for Automated Inductive Thematic Analysis",
    "tama_2026": "TAMA: A Human-AI Collaborative Thematic Analysis Framework Using Multi-Agent LLMs for Clinical Interviews",
    "yi_2026_provenance_refinement": "Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance",
    "llm_ta_2025": "LLM-TA: An LLM-Enhanced Thematic Analysis Pipeline for Transcripts from Parents of Children with Congenital Heart Disease",
    "position_clinical_ta_2025": "Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models",
    "qualanalyzer_2026": "Affording Process Auditability with QualAnalyzer: An Atomistic LLM Analysis Tool for Qualitative Research",
    "jowsey_2025_frankenstein": "Frankenstein, thematic analysis and generative AI",
    "hill_2026_healthcare": "Large language models for thematic analysis in healthcare research: A blinded mixed-methods comparison with human analysts",
    "montes_2025_prompting": "Large Language Models in Thematic Analysis: Prompt Engineering, Evaluation, and Guidelines",
    "perez_2026_icr": "Position: A Semiotic-Hermeneutic Approach to Qualitative Evaluation of LLMs with an Inductive Conceptual Rating Metric",
    "alghamdi_2026_convergence": "From Code Variability to Theme Convergence: Evaluating Large Language Models Against Human Thematic Analysis",
    "pi_2026_landscape": "A Landscape of Computational Approaches to Qualitative Analysis",
    "bedemariam_2025_judges": "Potential and Perils of Large Language Models as Judges of Unstructured Textual Data",
    "yu_2025_same_company": "Same Company, Same Signal: The Role of Identity in Earnings Call Transcripts",
    "ashwin_2025_serious_bias": "Using Large Language Models for Qualitative Analysis can Introduce Serious Bias",
    "mathis_2024_open_source": "Inductive thematic analysis of healthcare qualitative interviews using open-source large language models: How does it compare to traditional methods?",
    "prescott_2024_genai_human": "Comparing the Efficacy and Efficiency of Human and Generative AI: Qualitative Thematic Analyses",
    "li_2024_gpt4_human": "Comparing GPT-4 and Human Researchers in Health Care Data Analysis: Qualitative Description Study",
    "bijker_2024_content_analysis": "ChatGPT for Automated Qualitative Research: Content Analysis",
    "bennis_2025_nine_models": "Advancing AI-driven thematic analysis: a comparative study of nine generative models on Cutaneous Leishmaniasis data",
    "vikan_2025_reflexive": "Reflecting on LLM Support in Reflexive Thematic Analysis: An Exploratory Study",
    "grover_2026_preferences": "Advancing the science of qualitative patient preference assessment using large language models",
    "bai_2026_three_datasets": "Large Language Models for Qualitative Analysis of Digital Health Interviews",
    "turner_2026_dementia_trials": "Large language models for deductive qualitative content analysis in dementia-focused embedded pragmatic clinical trials: A comparative methodological study",
    "sakaguchi_2025_japanese": "Evaluating ChatGPT in Qualitative Thematic Analysis With Human Researchers in the Japanese Clinical Context and Its Cultural Interpretation Challenges",
    "wachinger_2024_prompts": "Prompts, Pearls, Imperfections: Comparing ChatGPT and a Human Researcher in Qualitative Data Analysis",
    "ronaghi_2026_large_scale": "Large Language Models for Large-Scale, Rigorous Qualitative Analysis in Applied Health Services Research",
    "elangovan_2021_leakage": "Memorization vs. Generalization: Quantifying Data Leakage in NLP Performance Evaluation",
    "liu_2024_lost_middle": "Lost in the Middle: How Language Models Use Long Contexts",
    "lu_2022_prompt_order": "Fantastically Ordered Prompts and Where to Find Them: Overcoming Few-Shot Prompt Order Sensitivity",
    "zhao_2021_calibrate": "Calibrate Before Use: Improving Few-Shot Performance of Language Models",
    "deng_2024_contamination": "Investigating Data Contamination in Modern Benchmarks for Large Language Models",
    "balloccu_2024_leak_cheat_repeat": "Leak, Cheat, Repeat: Data Contamination and Evaluation Malpractices in Closed-Source LLMs",
    "morris_2023_embeddings": "Text Embeddings Reveal (Almost) As Much As Text",
    "baroud_2025_beyond_deidentification": "Beyond De-Identification: A Structured Approach for Assessing and Reducing Privacy Risks in Clinical Text",
    "van_aken_2022_behavioral": "What Do You See in this Patient? Behavioral Testing of Clinical NLP Models",
}


def merge_full_text_tracks() -> list[dict]:
    tracks = [
        ("core_systems", read_json("core_systems.json")["studies"]),
        ("evaluation_methodology", read_json("evaluation_methodology.json")["automated_qualitative_studies"]),
        ("validity_ethics", read_json("validity_ethics.json")["papers"]),
    ]
    merged: dict[str, dict] = {}
    for track_name, records in tracks:
        for record in records:
            key = canonical_key(record)
            entry = merged.setdefault(
                key,
                {
                    "report_key": key,
                    "title": TITLE_BY_ID.get(record.get("id", ""), "not separately parsed; see full citation"),
                    "full_citation": record.get("citation", "not reported"),
                    "doi": canonical_doi(record.get("doi")) or "not reported",
                    "url": record.get("url") or record.get("official_url") or "not reported",
                    "track_ids": [],
                    "track_labels": [],
                    "evidence_locations": [],
                    "abstract_only": False,
                },
            )
            if entry["title"].startswith("not separately") and record.get("id") in TITLE_BY_ID:
                entry["title"] = TITLE_BY_ID[record["id"]]
            entry["track_ids"].append(f"{track_name}:{record.get('id', 'not reported')}")
            label = (
                record.get("decision")
                or record.get("core_or_adjacent")
                or record.get("relationship")
                or "not reported"
            )
            entry["track_labels"].append(label)
            if record.get("evidence_location"):
                entry["evidence_locations"].append(record["evidence_location"])
            entry["abstract_only"] = entry["abstract_only"] or bool(record.get("abstract_only", False))
            if entry["doi"] == "not reported" and canonical_doi(record.get("doi")):
                entry["doi"] = canonical_doi(record.get("doi"))
            if entry["url"] == "not reported":
                entry["url"] = record.get("url") or record.get("official_url") or "not reported"

    for entry in merged.values():
        labels = " ".join(entry["track_labels"]).lower()
        if "proposal" in labels or "position" in labels:
            decision = "include_contextual"
            reason = "Methodological or position contribution retained for framing/citation chasing, not pooled as a completed system effect study."
        elif "include_core" in labels or re.search(r"\bcore\b", labels):
            decision = "include_core"
            reason = "Presents or evaluates substantive computational support for qualitative coding, thematic interpretation, or code/theme evaluation."
        elif "adjacent" in labels or "landscape" in labels:
            decision = "include_adjacent"
            reason = "Directly informs evaluation, leakage, confounding, privacy, or novelty but is not itself a core qualitative-analysis system study."
        else:
            decision = "include_core"
            reason = "Presents or evaluates substantive computational support for qualitative coding, thematic interpretation, or code/theme evaluation."
        entry["decision"] = decision
        entry["decision_reason"] = reason
        entry["full_text_basis"] = (
            "Inspected full text and/or track extraction with section-level evidence location; no abstract-only methodological claim."
            if not entry["abstract_only"]
            else "Abstract only; not used for methodological claims."
        )
        entry["evidence_locations"] = sorted(set(entry["evidence_locations"])) or [
            "track report states full-text inspection; exact section not separately indexed"
        ]
        entry["track_ids"] = sorted(set(entry["track_ids"]))
        entry["track_labels"] = sorted(set(entry["track_labels"]))

    # Full texts additionally inspected by the root review and stored locally.
    additions = [
        {
            "report_key": "arxiv:2604.04479",
            "title": "How can LLMs Support Policy Researchers? Evaluating an LLM-Assisted Workflow for Large-Scale Unstructured Data",
            "full_citation": "Liu et al. (2026). How can LLMs Support Policy Researchers? Evaluating an LLM-Assisted Workflow for Large-Scale Unstructured Data. arXiv:2604.04479v2.",
            "doi": "10.48550/arxiv.2604.04479",
            "url": "https://arxiv.org/abs/2604.04479",
            "decision": "include_core",
            "decision_reason": "Evaluates an LLM-assisted workflow for qualitative analysis of large unstructured corpora.",
            "full_text_basis": "Local PDF inspected: research/fulltext/latest/2604.04479.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:2604.04479"],
            "track_labels": ["core workflow"],
            "abstract_only": False,
        },
        {
            "report_key": "arxiv:2604.10834",
            "title": "LLMs for Qualitative Data Analysis Fail on Security-specific Comments in Human Experiments",
            "full_citation": "Camporese, Massacci, and Gong (2026). LLMs for Qualitative Data Analysis Fail on Security-specific Comments in Human Experiments. arXiv:2604.10834v1.",
            "doi": "10.48550/arxiv.2604.10834",
            "url": "https://arxiv.org/abs/2604.10834",
            "decision": "include_core",
            "decision_reason": "Direct empirical failure analysis for LLM-assisted qualitative data analysis.",
            "full_text_basis": "Local PDF inspected: research/fulltext/latest/2604.10834.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:2604.10834"],
            "track_labels": ["core failure analysis"],
            "abstract_only": False,
        },
        {
            "report_key": "arxiv:2604.19309",
            "title": "Co-Refine: AI-Powered Tool Supporting Qualitative Analysis",
            "full_citation": "Jeyaganthan et al. (2026). Co-Refine: AI-Powered Tool Supporting Qualitative Analysis. arXiv:2604.19309v1.",
            "doi": "10.48550/arxiv.2604.19309",
            "url": "https://arxiv.org/abs/2604.19309",
            "decision": "include_core",
            "decision_reason": "Human-AI qualitative-analysis interface with source-grounded refinement support.",
            "full_text_basis": "Local PDF inspected: research/fulltext/latest/2604.19309.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:2604.19309"],
            "track_labels": ["core human-AI system"],
            "abstract_only": False,
        },
        {
            "report_key": "arxiv:2607.28889",
            "title": "Human-LLM Collaborative Inductive Coding for Conceptualizing K-12 Educator AI Use",
            "full_citation": "Liu et al. (2026). Human-LLM Collaborative Inductive Coding for Conceptualizing K-12 Educator AI Use. arXiv:2607.28889v1.",
            "doi": "10.48550/arxiv.2607.28889",
            "url": "https://arxiv.org/abs/2607.28889",
            "decision": "include_core",
            "decision_reason": "Direct human-LLM collaborative inductive-coding study.",
            "full_text_basis": "Local PDF inspected: research/fulltext/latest/2607.28889.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:2607.28889"],
            "track_labels": ["core collaborative coding"],
            "abstract_only": False,
        },
        {
            "report_key": "arxiv:2607.28890",
            "title": "Agreement Is Not Quality: Blind Expert Verification of Human and LLM Qualitative Coding When Human Consensus Is Not Ground Truth",
            "full_citation": "Liu et al. (2026). Agreement Is Not Quality: Blind Expert Verification of Human and LLM Qualitative Coding When Human Consensus Is Not Ground Truth. arXiv:2607.28890v1.",
            "doi": "10.48550/arxiv.2607.28890",
            "url": "https://arxiv.org/abs/2607.28890",
            "decision": "include_core",
            "decision_reason": "Direct plurality-aware evaluation of human and LLM qualitative coding.",
            "full_text_basis": "Local PDF inspected: research/fulltext/latest/2607.28890.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:2607.28890"],
            "track_labels": ["core evaluation"],
            "abstract_only": False,
        },
        {
            "report_key": "doi:10.3390/educsci16081314",
            "title": "Evaluation of Inductive Coding with LLMs",
            "full_citation": "Dörfel, Leoni, and Rieke Ammoneit. 2026. Evaluation of Inductive Coding with LLMs. Education Sciences 16(8): 1314.",
            "doi": "10.3390/educsci16081314",
            "url": "https://doi.org/10.3390/educsci16081314",
            "decision": "include_core",
            "decision_reason": "Direct comparison of iterative ChatGPT code-system induction and coding with a prior human qualitative content analysis of the same interview corpus.",
            "full_text_basis": "Publisher version of record inspected: research/fulltext/latest/education_2026_inductive_coding.pdf; 52-field extraction and exact evidence locations are in research/dorfel_2026_evidence.json.",
            "evidence_locations": [
                "§§2.1-2.3.5, pp.3-8",
                "§§3.1-3.5, pp.8-16",
                "§§4.1-5, pp.16-20",
                "Appendix A.1-A.5, pp.21-26",
            ],
            "track_ids": ["dorfel_2026_evidence:dorfel_2026_inductive_coding"],
            "track_labels": ["core inductive-coding evaluation"],
            "abstract_only": False,
        },
        {
            "report_key": "doi:10.1057/s41599-026-06508-5",
            "title": "Thematic analysis with open-source generative AI and machine learning: a new method for inductive qualitative codebook development",
            "full_citation": "Katz, Fleming, and Main (2026). Thematic analysis with open-source generative AI and machine learning: a new method for inductive qualitative codebook development. Humanities and Social Sciences Communications, 13, 209.",
            "doi": "10.1057/s41599-026-06508-5",
            "url": "https://doi.org/10.1057/s41599-026-06508-5",
            "decision": "include_core",
            "decision_reason": "Presents and evaluates the GATOS inductive codebook-development workflow.",
            "full_text_basis": "Local publisher PDF inspected: research/fulltext/latest/gatos_2026.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:gatos_2026"],
            "track_labels": ["core open-source workflow"],
            "abstract_only": False,
        },
        {
            "report_key": "doi:10.18653/v1/2026.acl-industry.131",
            "title": "Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant",
            "full_citation": "Matveyenko et al. (2026). Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant. ACL 2026 Industry Track, 1917-1932.",
            "doi": "10.18653/v1/2026.acl-industry.131",
            "url": "https://aclanthology.org/2026.acl-industry.131/",
            "decision": "include_core",
            "decision_reason": "Presents and benchmarks the Muse blended human-AI qualitative research assistant.",
            "full_text_basis": "Local ACL PDF inspected: research/fulltext/latest/matveyenko_2026_muse.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:muse_2026"],
            "track_labels": ["core system/benchmark"],
            "abstract_only": False,
        },
        {
            "report_key": "doi:10.18653/v1/2026.findings-acl.591",
            "title": "Can LLMs Understand the Impact of Trauma? Costs and Benefits of LLMs Coding the Interviews of Firearm Violence Survivors",
            "full_citation": "Zhu et al. (2026). Can LLMs Understand the Impact of Trauma? Costs and Benefits of LLMs Coding the Interviews of Firearm Violence Survivors. Findings of ACL 2026, 12174-12192.",
            "doi": "10.18653/v1/2026.findings-acl.591",
            "url": "https://aclanthology.org/2026.findings-acl.591/",
            "decision": "include_core",
            "decision_reason": "Direct evaluation of LLM coding in a sensitive qualitative interview domain.",
            "full_text_basis": "Local ACL PDF inspected: research/fulltext/latest/zhu_2026_trauma.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:zhu_2026"],
            "track_labels": ["core high-stakes evaluation"],
            "abstract_only": False,
        },
        {
            "report_key": "doi:10.1186/s12874-026-02913-1",
            "title": "The use and methodological reporting of large language models in qualitative research: a scoping review",
            "full_citation": "Kempny et al. (2026). The use and methodological reporting of large language models in qualitative research: a scoping review. BMC Medical Research Methodology, 26, 137.",
            "doi": "10.1186/s12874-026-02913-1",
            "url": "https://doi.org/10.1186/s12874-026-02913-1",
            "decision": "include_contextual",
            "decision_reason": "Secondary scoping review retained for coverage and reporting-practice context; not used as primary technical evidence.",
            "full_text_basis": "Local publisher PDF inspected: research/fulltext/latest/kempny_2026_scoping_review.pdf.",
            "evidence_locations": ["local full text"],
            "track_ids": ["root_fulltext:kempny_2026"],
            "track_labels": ["contextual secondary review"],
            "abstract_only": False,
        },
    ]
    for addition in additions:
        merged.setdefault(addition["report_key"], addition)

    # Backward-chain reports with complete full-text inspection and audited
    # 52-field extractions.  The third chain candidate (Laato et al.) is
    # deliberately absent here because its complete PDF was not reproducibly
    # retrievable; it remains in the nonretrieval count below.
    citation_audit = read_json("citation_chaining.json")
    for candidate in citation_audit["backward_chain_candidates"]:
        if candidate.get("eligibility_decision") != "include_core":
            continue
        record = candidate["master_ready_record"]
        doi = canonical_doi(record.get("DOI"))
        aid = arxiv_id(record.get("DOI"), record.get("URL"))
        key = "doi:" + doi if doi and not doi.startswith("10.48550/arxiv.") else "arxiv:" + aid
        chain_entry = {
            "report_key": key,
            "title": record["Title"],
            "full_citation": record["Full citation"],
            "doi": record["DOI"],
            "url": record["URL"],
            "decision": "include_core",
            "decision_reason": candidate["eligibility_reason"],
            "full_text_basis": candidate["full_text_evidence"],
            "evidence_locations": sorted(candidate["quality_evidence_locations"].values()),
            "track_ids": [f"citation_chain:{candidate['candidate_id']}"],
            "track_labels": ["core backward-citation-chain study"],
            "abstract_only": False,
        }
        merged.setdefault(key, chain_entry)

    return sorted(merged.values(), key=lambda row: (row["decision"], row["title"].lower()))


LLM_TERMS = [
    "large language model",
    " llm",
    "llms",
    "chatgpt",
    "gpt-",
    "gpt 4",
    "gpt4",
    "generative ai",
    "generative artificial intelligence",
    "claude",
    "gemini",
    "llama",
    "mistral",
]
TASK_TERMS = [
    "thematic analysis",
    "theme generation",
    "thematic summarization",
    "qualitative coding",
    "inductive coding",
    "open coding",
    "qualitative content analysis",
    "qualitative data analysis",
    "codebook induction",
    "codebook generation",
    "codebook refinement",
    "hierarchical inductive coding",
    "schema induction",
    "concept induction",
    "open codes",
    "axial coding",
    "qualitative analysis",
]
ADJACENT_TERMS = [
    "identity leakage",
    "speaker identity",
    "participant identity",
    "source identity",
    "spurious correlation",
    "shortcut learning",
    "data leakage",
    "data contamination",
    "privacy risk",
    "long context",
    "prompt order",
    "llm as a judge",
    "llm-as-a-judge",
    "representation confound",
]
TITLE_FALSE_FRIENDS = [
    "text-to-speech",
    "speech synthesis",
    "code generation",
    "software engineering",
    "image generation",
    "video generation",
    "thematic analysis of policy",
    "bibliometric and thematic analysis",
    "views on chatgpt",
    "attitudes toward chatgpt",
    "perceptions of chatgpt",
]


def hit_list(text: str, terms: list[str]) -> list[str]:
    return sorted({term.strip() for term in terms if term in text})


def union_record_keys(record: dict) -> set[str]:
    keys = set()
    doi = canonical_doi(record.get("doi"))
    if doi:
        keys.add("doi:" + doi)
    aid = arxiv_id(record.get("url"), record.get("doi"))
    if aid:
        keys.add("arxiv:" + aid)
    keys.add("title:" + normalize_title(record.get("title", "")))
    for child in record.get("source_records", []):
        cdoi = canonical_doi(child.get("doi"))
        if cdoi:
            keys.add("doi:" + cdoi)
        caid = arxiv_id(child.get("url"), child.get("doi"))
        if caid:
            keys.add("arxiv:" + caid)
    return keys


def screen_union(records: list[dict], full_text: list[dict]):
    known_keys = {entry["report_key"] for entry in full_text}
    known_titles = {"title:" + normalize_title(entry["title"]) for entry in full_text}
    manual_exclude_titles = {
        normalize_title("Understanding Writing Assistants for Scientific Figure Captions: A Thematic Analysis"):
            "Thematic analysis is the evaluation method used by researchers; the system does not perform qualitative coding or theme development.",
    }
    screened = []
    for index, record in enumerate(records, start=1):
        title = record.get("title", "")
        title_norm = normalize_title(title)
        title_l = " " + title.lower()
        abstract_l = " " + (record.get("abstract") or "").lower()
        combined = title_l + " " + abstract_l
        llm_title = hit_list(title_l, LLM_TERMS)
        task_title = hit_list(title_l, TASK_TERMS)
        adjacent_title = hit_list(title_l, ADJACENT_TERMS)
        llm_all = hit_list(combined, LLM_TERMS)
        task_all = hit_list(combined, TASK_TERMS)
        adjacent_all = hit_list(combined, ADJACENT_TERMS)
        false_title = hit_list(title_l, TITLE_FALSE_FRIENDS)
        record_keys = union_record_keys(record)
        known = bool(record_keys & (known_keys | known_titles))

        if title_norm in manual_exclude_titles:
            decision = "excluded"
            code = "TA_AS_RESEARCH_METHOD_ONLY"
            reason = manual_exclude_titles[title_norm]
            manual = True
        elif known:
            decision = "included"
            code = "FULL_TEXT_EVIDENCE_TRACK"
            reason = "Matched an inspected full-text report retained by at least one evidence track."
            manual = True
        elif false_title:
            decision = "excluded"
            code = "OBVIOUS_FALSE_FRIEND_TITLE"
            reason = "Title indicates a coding/speech/generation false friend or thematic analysis of AI rather than LLM-assisted qualitative analysis."
            manual = False
        elif llm_title and task_title:
            decision = "included"
            code = "DIRECT_TITLE_INTERSECTION"
            reason = "Title explicitly combines an LLM/generative-model term with a target qualitative-analysis task; advanced for manual assessment."
            manual = False
        elif adjacent_title and (llm_title or "text" in title_l or "transcript" in title_l):
            decision = "included"
            code = "DIRECT_ADJACENT_VALIDITY_TITLE"
            reason = "Title directly names a validity/leakage/confounding construct relevant to text or LLM evaluation; advanced as adjacent literature."
            manual = False
        elif (llm_all and task_all) or task_title or adjacent_all:
            decision = "uncertain"
            code = "POSSIBLE_RELEVANCE_REQUIRES_MANUAL_SCREEN"
            reason = "Record contains relevant model/task or adjacent-validity terms, but title/abstract text does not establish substantive automated qualitative analysis."
            manual = False
        else:
            decision = "excluded"
            code = "NO_TARGET_TASK_INTERSECTION"
            reason = "No deterministic title/abstract evidence of both a target qualitative-analysis contribution and an LLM/related directly relevant NLP method."
            manual = False

        screened.append(
            {
                "screen_id": f"TA-{index:04d}",
                "source": record.get("source", "not reported"),
                "sources": record.get("sources", [record.get("source", "not reported")]),
                "source_id": record.get("source_id", "not reported"),
                "title": title,
                "year": record.get("year", "not reported"),
                "doi": record.get("doi") or "not reported",
                "url": record.get("url") or "not reported",
                "decision": decision,
                "reason_code": code,
                "reason": reason,
                "manual_full_text_override": manual,
                "matched_title_terms": {
                    "llm": llm_title,
                    "qualitative_task": task_title,
                    "adjacent_validity": adjacent_title,
                    "false_friend": false_title,
                },
            }
        )
    return screened


def stripped_queries(source_file: str) -> list[dict]:
    source = read_json(source_file)
    queries = []
    for item in source.get("queries", []):
        queries.append(
            {
                key: value
                for key, value in item.items()
                if key
                in {
                    "query_id",
                    "database",
                    "search_date",
                    "endpoint",
                    "query_parameter",
                    "query",
                    "filters",
                    "reported_count",
                    "reported_total_results",
                    "retrieved",
                    "retained_after_client_filter",
                }
            }
        )
    return queries


def main():
    union = read_json("search_union_deduplicated.json")
    citation_audit = read_json("citation_chaining.json")
    full_text = merge_full_text_tracks()
    screened = screen_union(union["records"], full_text)
    triage_counts = Counter(row["decision"] for row in screened)
    reason_counts = Counter(row["reason_code"] for row in screened)

    # Link assessed reports to the union without asserting an unrecorded discovery route.
    union_key_to_ids: dict[str, list[str]] = {}
    for row in screened:
        original = union["records"][int(row["screen_id"].split("-")[1]) - 1]
        for key in union_record_keys(original):
            union_key_to_ids.setdefault(key, []).append(row["screen_id"])
    title_to_id = {"title:" + normalize_title(row["title"]): row["screen_id"] for row in screened}
    outside_union = []
    for entry in full_text:
        matches = sorted(set(union_key_to_ids.get(entry["report_key"], [])))
        if not matches:
            match = title_to_id.get("title:" + normalize_title(entry["title"]))
            if match:
                matches = [match]
        entry["linked_screen_ids"] = matches
        entry["identification_route"] = (
            "database/register union"
            if matches
            else "targeted exact-title/DOI or evidence-track search; no exact DOI/title link in the deduplicated union"
        )
        for screen_id in matches:
            screen_row = screened[int(screen_id.split("-")[1]) - 1]
            screen_row["full_text_report_key"] = entry["report_key"]
            screen_row["full_text_decision"] = entry["decision"]
        if not matches:
            outside_union.append(
                {
                    "report_key": entry["report_key"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "route": entry["identification_route"],
                }
            )

    # One inspected full-text paper was explicitly excluded from the review.
    full_text_exclusions = [
        {
            "title": "Understanding Writing Assistants for Scientific Figure Captions: A Thematic Analysis",
            "citation": "Ng et al. (2025). Understanding Writing Assistants for Scientific Figure Captions: A Thematic Analysis. In2Writing 2025.",
            "doi": "10.18653/v1/2025.in2writing-1.1",
            "url": "https://aclanthology.org/2025.in2writing-1.1/",
            "decision": "exclude",
            "reason_code": "TA_AS_RESEARCH_METHOD_ONLY",
            "reason": "The authors use thematic analysis to evaluate writing assistants; the computational system does not perform, assist, or evaluate qualitative coding/theme development.",
            "evidence_basis": "Full ACL Anthology paper inspected in the core-system screening track.",
        }
    ]

    retained_counts = Counter(row["decision"] for row in full_text)
    assessed_count = len(full_text) + len(full_text_exclusions)
    reports_not_retrieved = 2 + citation_audit["backward_chain_summary"]["reports_sought_but_not_retrieved"]
    reports_sought = assessed_count + reports_not_retrieved

    database_searches = []
    for filename in [
        "pubmed_search_records.json",
        "crossref_search_records.json",
        "acl_anthology_search_records.json",
        "openreview_search_records.json",
        "arxiv_search_records.json",
    ]:
        data = read_json(filename)
        database_searches.append(
            {
                "database": data["database"],
                "search_date": data["search_date"],
                "unique_records_contributed_before_cross_database_deduplication": (
                    data.get("unique_records") or data.get("unique_retained_records")
                ),
                "queries": stripped_queries(filename),
                "limitation": data.get("limitation", "not reported"),
                "record_file": f"research/{filename}",
            }
        )

    result = {
        "metadata": {
            "title": "PRISMA-style search, triage, screening, and exclusion audit for computational qualitative-analysis review",
            "generated_on": CUTOFF,
            "publication_cutoff": CUTOFF,
            "record_universe": "search_union_deduplicated.json",
            "flow_status": "Auditable evidence-track snapshot, not a claim of exhaustive dual-reviewer screening",
            "reviewer_model": "One reviewer/Codex-assisted. No independent duplicate screening or adjudication was performed.",
            "important_interpretation": "The 1,360 record labels are deterministic relevance triage. Only reports listed under full_text_stage have an eligibility decision supported by full-text extraction.",
        },
        "eligibility_criteria": {
            "include_core": [
                "Presents, evaluates, or substantively analyzes computational support for qualitative coding or thematic interpretation.",
                "Proposes an evaluation method directly applicable to codes or themes.",
                "Investigates human-AI qualitative analysis.",
            ],
            "include_adjacent": [
                "Directly studies a validity, representation, leakage, confounding, privacy, or evaluation issue that changes how transcript qualitative-analysis systems should be evaluated.",
                "Provides methodological guidance needed to evaluate computational qualitative-analysis claims.",
            ],
            "exclude": [
                "Topic modeling, clustering, summarization, sentiment, extraction, or fixed-label prediction with no qualitative-interpretation or directly relevant evaluation contribution.",
                "Thematic/qualitative analysis is used only to study an unrelated system or people's views of AI; the model is not the analyst.",
                "Non-scholarly product/tutorial/opinion with no relevant evidence, or unverifiable bibliographic source.",
            ],
            "methodological_incongruence_rule": "Do not exclude merely because a paper conflates thematic analysis, coding, content analysis, clustering, or grounded theory; retain it and code claimed versus operationalized method separately.",
        },
        "identification": {
            "database_searches": database_searches,
            "accessibility_log": [
                {
                    "database": "Google Scholar",
                    "attempt_date": CUTOFF,
                    "attempted_query": '"large language model" "thematic analysis"',
                    "result": "HTTP 403",
                    "retrieved": "not available",
                    "use_in_flow": "No database count; targeted web discovery cannot substitute for an auditable Scholar export.",
                },
                {
                    "database": "Semantic Scholar",
                    "attempt_date": CUTOFF,
                    "attempted_query": '"large language model" "thematic analysis"',
                    "result": "HTTP 429",
                    "retrieved": "not available",
                    "use_in_flow": "No database count and no citation-index total claimed.",
                },
                {
                    "database": "ACM Digital Library",
                    "attempt_date": CUTOFF,
                    "attempted_query": '"large language model" AND "thematic analysis"',
                    "result": "HTTP 403",
                    "retrieved": "not available",
                    "use_in_flow": "No formal ACM search count; exact known DOI/title pages were used when reachable through official records.",
                },
                {
                    "database": "IEEE Xplore",
                    "attempt_date": CUTOFF,
                    "attempted_query": '("large language model" OR LLM) AND ("thematic analysis" OR "qualitative coding")',
                    "result": "HTTP 418",
                    "retrieved": "not available",
                    "use_in_flow": "No formal IEEE search count.",
                },
                {
                    "database": "Scopus",
                    "attempt_date": CUTOFF,
                    "attempted_query": 'TITLE-ABS-KEY(("large language model" OR LLM) AND ("thematic analysis" OR "qualitative coding"))',
                    "result": "HTTP 403",
                    "retrieved": "not available",
                    "use_in_flow": "No Scopus search or citation count included.",
                },
                {
                    "database": "Web of Science",
                    "attempt_date": CUTOFF,
                    "attempted_query": 'TS=(("large language model" OR LLM) AND ("thematic analysis" OR "qualitative coding"))',
                    "result": "Landing page accessible; authenticated search unavailable",
                    "retrieved": "not available",
                    "use_in_flow": "No Web of Science search or citation count included.",
                },
            ],
            "counts": {
                "records_before_cross_database_deduplication": union["records_before_cross_database_deduplication"],
                "duplicate_records_removed": union["duplicate_records_removed"],
                "unique_records_after_exact_doi_and_title_deduplication": union[
                    "unique_records_after_exact_doi_and_normalized_title_deduplication"
                ],
                "source_record_counts": union["source_record_counts"],
            },
            "deduplication_method": union["deduplication_method"],
            "deduplication_caveat": "Venue/preprint versions can remain separate if titles differ materially; version families are reconciled again at full-text extraction.",
        },
        "triage_rule": {
            "purpose": "Reproducible relevance prioritization only; not an eligibility classifier and not a substitute for independent title/abstract screening.",
            "ordered_logic": [
                "Manual override: exclude the one inspected false-friend paper listed in the full-text exclusion log.",
                "Manual/full-text override: include exact DOI/arXiv/title matches to inspected evidence-track reports.",
                "Exclude explicit title false friends (speech/code/image/video generation or thematic analysis of AI rather than AI-assisted qualitative analysis).",
                "Include for manual assessment when the title explicitly intersects an LLM term and a qualitative-analysis task term.",
                "Include for adjacent manual assessment when the title directly names a validity/leakage/confounding construct and text/transcript/LLM context.",
                "Mark uncertain when relevant terms appear only in the abstract or otherwise do not establish substantive method fit.",
                "Exclude low-priority records with no target-task intersection.",
            ],
            "term_sets": {
                "llm": LLM_TERMS,
                "qualitative_task": TASK_TERMS,
                "adjacent_validity": ADJACENT_TERMS,
                "title_false_friends": TITLE_FALSE_FRIENDS,
            },
            "counts": dict(sorted(triage_counts.items())),
            "reason_code_counts": dict(sorted(reason_counts.items())),
        },
        "title_abstract_screening": {
            "records_screened": len(screened),
            "decision_semantics": {
                "included": "High-priority/known relevant record advanced or already assessed; not automatically a final inclusion.",
                "uncertain": "Potentially relevant but requires manual title/abstract or full-text resolution.",
                "excluded": "Low-priority or explicit false-friend result under the reproducible rule; only explicit manual overrides support an eligibility exclusion claim.",
            },
            "records": screened,
        },
        "full_text_stage": {
            "reports_sought_for_retrieval": reports_sought,
            "reports_not_retrieved": reports_not_retrieved,
            "reports_assessed": assessed_count,
            "retained_reports": len(full_text),
            "retained_by_classification": dict(sorted(retained_counts.items())),
            "full_text_exclusions": len(full_text_exclusions),
            "assessed_reports": full_text,
            "exclusion_log": full_text_exclusions,
            "abstract_only_not_assessed_as_full_text": [
                {
                    "candidate": "Psychotherapy/cultural-research paper",
                    "doi": "10.1016/j.ajp.2026.105071",
                    "decision": "not included in full-text numerator",
                    "reason": "Only the abstract was accessible in the validity track; detailed methods were not verified.",
                },
                {
                    "candidate": "Nursing interview comparison",
                    "doi": "10.1016/j.ijnurstu.2026.105584",
                    "decision": "not included in full-text numerator",
                    "reason": "Only the abstract was accessible in the validity track; detailed methods were not verified.",
                },
            ],
        },
        "citation_chaining": {
            "procedure": "Seed references, citing-title searches, newer same-group papers, and metric/system references were targeted. Interfaces did not expose stable counts and the track notes did not preserve a parent-seed field for every discovery.",
            "verified_record_level_forward_or_backward_additions": [
                {
                    "direction": "backward",
                    "parent_report": "TAMA (Xu et al., DOI 10.1145/3828752)",
                    "added_candidate": "De Paoli (2024), Further Explorations on the Use of Large Language Models for Thematic Analysis: Open-Ended Prompts, Better Terminologies and Thematic Maps",
                    "identifier": "10.17169/fqs-25.3.4196",
                    "url": "https://doi.org/10.17169/fqs-25.3.4196",
                    "verification": "Listed as reference 9 in research/fulltext/3828752__1_.txt (publisher full text).",
                    "union_status": "No exact DOI/title match in the 1,360-record union.",
                    "eligibility_status": "Citation-chain candidate only; not counted as full-text assessed or included in this flow.",
                },
                {
                    "direction": "backward",
                    "parent_report": "Muse (Matveyenko et al., DOI 10.18653/v1/2026.acl-industry.131)",
                    "added_candidate": "Borse, Subramaniam, and Rebello (2025), Investigation of the inter-rater reliability between large language models and human raters in qualitative analysis",
                    "identifier": "arXiv:2508.14764",
                    "url": "https://arxiv.org/abs/2508.14764",
                    "verification": "Listed in the reference section of research/fulltext/latest/matveyenko_2026_muse.txt.",
                    "union_status": "No exact DOI/arXiv/title match in the 1,360-record union.",
                    "eligibility_status": "Citation-chain candidate only; not counted as full-text assessed or included in this flow.",
                },
                {
                    "direction": "backward",
                    "parent_report": "Muse (Matveyenko et al., DOI 10.18653/v1/2026.acl-industry.131)",
                    "added_candidate": "Laato et al. (2025), Automating qualitative data analysis with chain-of-thought reasoning models: A study with the Gioia method",
                    "identifier": "AMCIS 2025, AISeL Paper 2130",
                    "url": "not independently verified",
                    "verification": "Listed in the reference section of research/fulltext/latest/matveyenko_2026_muse.txt.",
                    "union_status": "No exact title match in the 1,360-record union.",
                    "eligibility_status": "Citation-chain candidate only; not counted as full-text assessed or included in this flow.",
                },
            ],
            "verified_record_level_addition_count": 3,
            "verified_chain_confirmations_already_in_union_or_supplied": [
                {
                    "parent_report": "TAMA",
                    "linked_report": "Dai et al. (2023), LLM-in-the-loop",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "TAMA reference 8; already a seed and database-union report.",
                },
                {
                    "parent_report": "TAMA",
                    "linked_report": "Mathis et al. (2024), Inductive thematic analysis of healthcare qualitative interviews using open-source LLMs",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "TAMA reference 29; already retained through the health/validity evidence track.",
                },
                {
                    "parent_report": "TAMA",
                    "linked_report": "Raza et al. (2025), LLM-TA",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "TAMA reference 35; supplied full text/version family already represented.",
                },
                {
                    "parent_report": "TAMA",
                    "linked_report": "Qiao et al. (2025), Thematic-LM",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "TAMA reference 33; already in the database union.",
                },
                {
                    "parent_report": "Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models",
                    "linked_report": "Parfenova et al. (2025), Text Annotation via Inductive Coding",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "Position-paper reference 16; already a seed and database-union report.",
                },
                {
                    "parent_report": "Muse",
                    "linked_report": "Lam et al. (2024), LLooM",
                    "direction": "backward",
                    "unique_addition": False,
                    "verification": "Muse reference section; already retained in the evidence map.",
                },
            ],
            "chain_candidate_caveat": "The three additions are itemized because their parent-reference relationship is visible in an inspected full text. They are not silently counted as included studies without a separate full-text eligibility assessment.",
            "targeted_or_evidence_track_reports_without_exact_union_link": outside_union,
            "supplied_full_texts": [
                "Auto-TA (arXiv:2506.23998v2)",
                "Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models (arXiv:2509.14597v2)",
                "SFT-TA (arXiv:2509.17167v1)",
                "Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance (arXiv:2603.08989v1)",
                "TAMA (DOI 10.1145/3828752)",
            ],
            "supplied_reports_added_as_unique_records": 0,
            "supplied_reports_note": "All five supplied reports were already represented by an exact-title/DOI-equivalent record in the deduplicated union or full-text version family; they improved retrieval but do not inflate identification counts.",
            "saturation_claim": "No exhaustive citation-index saturation claim is made because Google Scholar, Semantic Scholar, Scopus, Web of Science, ACM, and IEEE could not be systematically exported in this environment.",
        },
        "prisma_style_flow": {
            "interpretation": "The standard database flow and the evidence-track full-text set are shown separately because unresolved deterministic-triage records were not silently converted into manual exclusions.",
            "database_flow": [
                {
                    "stage": "Records identified from five auditable searched sources before cross-database deduplication",
                    "count": union["records_before_cross_database_deduplication"],
                },
                {"stage": "Duplicate DOI/title records removed", "count": union["duplicate_records_removed"]},
                {
                    "stage": "Unique records receiving deterministic title/abstract triage",
                    "count": len(screened),
                },
                {"stage": "Triage: included/high priority", "count": triage_counts["included"]},
                {"stage": "Triage: uncertain/manual resolution needed", "count": triage_counts["uncertain"]},
                {"stage": "Triage: excluded/low priority or false friend", "count": triage_counts["excluded"]},
            ],
            "other_methods_flow": [
                {"stage": "Additional unique candidates identified by auditable backward citation chaining", "count": 3},
                {"stage": "Supplied reports added as new unique records", "count": 0},
                {"stage": "Citation-chain candidates with completed full-text assessment in this snapshot", "count": 2},
            ],
            "full_text_evidence_flow": [
                {"stage": "Reports sought for retrieval in the documented evidence tracks", "count": reports_sought},
                {"stage": "Reports not retrieved as full text", "count": reports_not_retrieved},
                {"stage": "Unique reports with documented full-text assessment", "count": assessed_count},
                {"stage": "Reports excluded after full-text assessment", "count": len(full_text_exclusions)},
                {"stage": "Reports retained in the review evidence map", "count": len(full_text)},
                {"stage": "Retained core reports", "count": retained_counts["include_core"]},
                {"stage": "Retained adjacent reports", "count": retained_counts["include_adjacent"]},
                {"stage": "Retained contextual/position/secondary reports", "count": retained_counts["include_contextual"]},
            ],
            "consistency_checks": {
                "identification": (
                    union["records_before_cross_database_deduplication"]
                    - union["duplicate_records_removed"]
                    == len(screened)
                ),
                "triage": sum(triage_counts.values()) == len(screened),
                "full_text": len(full_text) + len(full_text_exclusions) == assessed_count,
                "retrieval": reports_sought - reports_not_retrieved == assessed_count,
                "retained_classification": sum(retained_counts.values()) == len(full_text),
            },
        },
        "review_limitations": [
            "Screening/extraction was single-reviewer and Codex-assisted; no independent duplicate screening or adjudication was performed.",
            "Deterministic relevance labels are triage decisions. The uncertain set remains an explicit completeness limitation, not an exclusion count disguised as manual screening.",
            "Crossref is fuzzy/relevance-ranked and capped at 100 per query; arXiv identity search is capped at 200; ACL is title-only; OpenReview applies a client-side filter.",
            "Formal searches or exports were unavailable for Google Scholar, Semantic Scholar, ACM Digital Library, IEEE Xplore, Scopus, and Web of Science.",
            "Citation chaining preserves parent-seed provenance in research/citation_chaining.json, but source coverage differs and no exhaustive saturation claim is made.",
            "Publication/version families may still require manual reconciliation where titles differ between preprint and proceedings versions.",
        ],
    }

    forward_screen = citation_audit["forward_result_screening"]
    openalex_seeds = citation_audit["forward_chain_audit"]["openalex"]["seeds"]
    semantic_seeds = citation_audit["forward_chain_audit"]["semantic_scholar"]["seeds"]
    scholar_seeds = citation_audit["forward_chain_audit"]["google_scholar"]["seeds"]
    result["citation_chaining"] = {
        "artifact": "research/citation_chaining.json",
        "concise_report": "research/citation_chaining.md",
        "procedure": citation_audit["metadata"]["protocol"],
        "seed_count": citation_audit["metadata"]["seed_count"],
        "backward_chain_summary": citation_audit["backward_chain_summary"],
        "backward_chain_candidates": [
            {
                "candidate_id": row["candidate_id"],
                "parent_seed_id": row["parent_seed_id"],
                "direction": row["direction"],
                "identifier": row["identifier"],
                "official_url": row["official_url"],
                "full_text_outcome": row["full_text_outcome"],
                "eligibility_decision": row["eligibility_decision"],
                "eligibility_reason": row["eligibility_reason"],
            }
            for row in citation_audit["backward_chain_candidates"]
        ],
        "forward_source_summary": {
            "openalex": {
                "seeds_resolved": sum(row["resolution"]["status"] == "resolved" for row in openalex_seeds),
                "seed_checks": len(openalex_seeds),
                "all_confirmation_record_sets_identical": all(
                    row["confirmation_summary"]["same_record_set"] for row in openalex_seeds
                ),
                "per_seed_first_pass_retrieval_sum": sum(
                    row["first_pass"].get("retrieved_count", 0) for row in openalex_seeds
                ),
                "note": "The per-seed sum is not a unique-record count because one citing work can cite multiple seeds.",
            },
            "semantic_scholar": {
                "seeds_resolved": sum(row["resolution_status"] == "resolved" for row in semantic_seeds),
                "seed_checks": len(semantic_seeds),
                "per_seed_retrieval_sum": sum(row.get("retrieved_citation_count", 0) for row in semantic_seeds),
                "unresolved_seed_ids": [
                    row["seed_id"] for row in semantic_seeds if row["resolution_status"] != "resolved"
                ],
            },
            "google_scholar": {
                "exact_title_results_inspected": sum(
                    row.get("status") == "exact-title result inspected" for row in scholar_seeds
                ),
                "seed_checks": len(scholar_seeds),
                "blocked_or_challenged": sum(row.get("blocked_or_challenged", False) for row in scholar_seeds),
                "coverage_limit": citation_audit["forward_chain_audit"]["google_scholar"]["method_limit"],
            },
        },
        "forward_union_summary": {
            "deduplicated_forward_records": forward_screen["deduplicated_forward_record_count"],
            "exact_master_matches": forward_screen["already_in_master_count"],
            "broad_title_keyword_candidates": forward_screen["new_title_keyword_triage_candidate_count"],
            "focused_scope_title_candidates": forward_screen["new_focused_scope_title_candidate_count"],
            "screening_status": "Title-level candidates are retained in the audit for manual abstract/full-text resolution; they are not counted as eligible or included without full-text inspection.",
        },
        "confirmation_pass_result": {
            "source": "OpenAlex",
            "stable_seed_sets": sum(row["confirmation_summary"]["same_record_set"] for row in openalex_seeds),
            "seed_sets_checked": len(openalex_seeds),
            "materially_new_records_on_confirmation": sum(
                row["confirmation_summary"]["materially_new_title_level_records_on_confirmation"]
                for row in openalex_seeds
            ),
            "interpretation": "The confirmation pass added no OpenAlex records during this run; this is not evidence of cross-index saturation.",
        },
        "materially_new_eligible_studies": {
            "confirmed_after_complete_full_text": 2,
            "confirmed_ids": [
                row["candidate_id"]
                for row in citation_audit["backward_chain_candidates"]
                if row["eligibility_decision"] == "include_core"
            ],
            "forward_status": "Potentially material forward records appeared at title/index level, but no additional forward record was promoted without complete full-text inspection.",
        },
        "saturation_claim": citation_audit["metadata"]["non_saturation_statement"],
    }

    output = RESEARCH / "review_flow.json"
    with output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"wrote {output}")
    print(json.dumps(result["prisma_style_flow"], indent=2))


if __name__ == "__main__":
    main()
