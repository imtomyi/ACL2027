#!/usr/bin/env python3
"""Build a reproducible citation-chaining audit for the supplied review seeds.

The script never edits ``master_evidence.json``.  It resolves every supplied seed in
OpenAlex and Semantic Scholar where possible, records a first and confirmation pass
through OpenAlex's forward-citation index, samples the first Google Scholar cited-by
page when the public HTML interface exposes one, and records official-page access.

Database coverage is deliberately reported source by source.  A successful repeated
OpenAlex query is not treated as evidence that all citation indexes are saturated.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "master_evidence.json"
OUT = ROOT / "citation_chaining.json"
OUT_MD = ROOT / "citation_chaining.md"
SEARCH_CUTOFF = "2026-08-24"
USER_AGENT = (
    "ACL-ARR-scoping-review-citation-audit/1.0 "
    "(reproducible scholarly metadata audit; no authentication)"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"}


SEEDS = [
    {
        "seed_id": "dai_2023_llm_in_loop",
        "title": "LLM-in-the-loop: Leveraging Large Language Model for Thematic Analysis",
        "doi": "10.18653/v1/2023.findings-emnlp.669",
        "official_url": "https://aclanthology.org/2023.findings-emnlp.669/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "ARXIV:2310.15100",
    },
    {
        "seed_id": "parfenova_2024_proposal",
        "title": "Automating Qualitative Data Analysis with Large Language Models",
        "doi": "10.18653/v1/2024.acl-srw.17",
        "official_url": "https://aclanthology.org/2024.acl-srw.17/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2024.acl-srw.17",
    },
    {
        "seed_id": "parfenova_2025_inductive_coding",
        "title": "Text Annotation via Inductive Coding: Comparing Human Experts to LLMs in Qualitative Data Analysis",
        "doi": "10.18653/v1/2025.findings-naacl.361",
        "official_url": "https://aclanthology.org/2025.findings-naacl.361/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2025.findings-naacl.361",
    },
    {
        "seed_id": "hicode_2025",
        "title": "HICode: Hierarchical Inductive Coding with LLMs",
        "doi": "10.18653/v1/2025.emnlp-main.1580",
        "official_url": "https://aclanthology.org/2025.emnlp-main.1580/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2025.emnlp-main.1580",
    },
    {
        "seed_id": "quallm_2025",
        "title": "QuaLLM: An LLM-based Framework to Extract Quantitative Insights from Online Forums",
        "doi": "10.18653/v1/2025.findings-naacl.74",
        "official_url": "https://aclanthology.org/2025.findings-naacl.74/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2025.findings-naacl.74",
    },
    {
        "seed_id": "thematic_lm_2025",
        "title": "Thematic-LM: A Multi-Agent Large Language Model Framework for Enhancing Automated Thematic Analysis",
        "doi": "10.1145/3696410.3714595",
        "official_url": "https://dl.acm.org/doi/10.1145/3696410.3714595",
        "official_provider": "ACM Digital Library",
        "semantic_scholar_id": "DOI:10.1145/3696410.3714595",
    },
    {
        "seed_id": "lloom_2024",
        "title": "Concept Induction: Analyzing Unstructured Text with High-Level Concepts Using LLooM",
        "doi": "10.1145/3613904.3642830",
        "official_url": "https://dl.acm.org/doi/10.1145/3613904.3642830",
        "official_provider": "ACM Digital Library",
        "semantic_scholar_id": "DOI:10.1145/3613904.3642830",
    },
    {
        "seed_id": "details_2025",
        "title": "DeTAILS: Deep Thematic Analysis with Iterative LLM Support",
        "doi": "10.1145/3719160.3735657",
        "official_url": "https://dl.acm.org/doi/10.1145/3719160.3735657",
        "official_provider": "ACM Digital Library",
        "semantic_scholar_id": "DOI:10.1145/3719160.3735657",
        "version_note": "Expanded preprint family: arXiv:2510.17575.",
    },
    {
        "seed_id": "chen_2026_open_code_metrics",
        "title": "A Computational Method for Measuring ‘Open Codes’ in Qualitative Analysis",
        "doi": "10.18653/v1/2026.findings-acl.2073",
        "official_url": "https://aclanthology.org/2026.findings-acl.2073/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2026.findings-acl.2073",
    },
    {
        "seed_id": "yu_2025_same_company",
        "title": "Same Company, Same Signal: The Role of Identity in Earnings Call Transcripts",
        "doi": "10.18653/v1/2025.findings-acl.946",
        "official_url": "https://aclanthology.org/2025.findings-acl.946/",
        "official_provider": "ACL Anthology",
        "semantic_scholar_id": "DOI:10.18653/v1/2025.findings-acl.946",
    },
    {
        "seed_id": "tama_2026",
        "title": "TAMA: A Human-AI Collaborative Thematic Analysis Framework Using Multi-Agent LLMs for Clinical Interviews",
        "doi": "10.1145/3828752",
        "official_url": "https://doi.org/10.1145/3828752",
        "official_provider": "ACM Digital Library via DOI",
        "semantic_scholar_id": "DOI:10.1145/3828752",
    },
    {
        "seed_id": "auto_ta_2025",
        "title": "Auto-TA: Towards Scalable Automated Thematic Analysis via Multi-Agent Large Language Models with Reinforcement Learning",
        "doi": "10.48550/arxiv.2506.23998",
        "official_url": "https://arxiv.org/abs/2506.23998",
        "official_provider": "arXiv",
        "semantic_scholar_id": "ARXIV:2506.23998",
    },
    {
        "seed_id": "sft_ta_2025",
        "title": "SFT-TA: Supervised Fine-Tuned Agents in Multi-Agent LLMs for Automated Inductive Thematic Analysis",
        "doi": "10.48550/arxiv.2509.17167",
        "official_url": "https://arxiv.org/abs/2509.17167",
        "official_provider": "arXiv",
        "semantic_scholar_id": "ARXIV:2509.17167",
    },
    {
        "seed_id": "position_clinical_ta_2025",
        "title": "Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models",
        "doi": "10.48550/arxiv.2509.14597",
        "official_url": "https://arxiv.org/abs/2509.14597",
        "official_provider": "arXiv",
        "semantic_scholar_id": "ARXIV:2509.14597",
    },
    {
        "seed_id": "yi_2026_provenance_refinement",
        "title": "Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance",
        "doi": "10.48550/arxiv.2603.08989",
        "official_url": "https://arxiv.org/abs/2603.08989",
        "official_provider": "arXiv",
        "semantic_scholar_id": "ARXIV:2603.08989",
    },
]


DEPAOLI_RECORD = {
    "Paper ID": "depaoli_2024_further_explorations",
    "Full citation": "De Paoli, Stefano. (2024). Further Explorations on the Use of Large Language Models for Thematic Analysis: Open-Ended Prompts, Better Terminologies and Thematic Maps. Forum Qualitative Sozialforschung / Forum: Qualitative Social Research, 25(3), Article 5. https://doi.org/10.17169/fqs-25.3.4196",
    "Title": "Further Explorations on the Use of Large Language Models for Thematic Analysis: Open-Ended Prompts, Better Terminologies and Thematic Maps",
    "Authors": "Stefano De Paoli",
    "Year": "2024",
    "Venue": "Forum Qualitative Sozialforschung / Forum: Qualitative Social Research, 25(3), Article 5",
    "Publication type": "journal article",
    "Peer-reviewed status": "peer reviewed",
    "Publication history notes": "Published 2024-09-29. The official landing page and issue identify DOI 10.17169/fqs-25.3.4196; the final citation line inside the PDF prints 10.17169/fqs-25.2.4196, an internal inconsistency, so the official landing-page DOI is preserved.",
    "URL": "https://www.qualitative-research.net/index.php/fqs/article/view/4196",
    "DOI": "10.17169/fqs-25.3.4196",
    "Citation count, source, and retrieval date": "7; OpenAlex cited_by_count; retrieved 2026-08-24; OpenAlex W6887505737",
    "Core or adjacent classification": "core",
    "Relationship/dependence family": "De Paoli thematic-analysis workflow family; extends De Paoli (2023) and De Paoli and Mathis (2024). Backward-chained from TAMA. It is not part of the AAOCA/Auto-TA/SFT-TA/TAMA shared clinical-data family.",
    "Research objective": "Develop and demonstrate open-ended, thematic-analysis-specific prompts for initial coding, cumulative duplicate removal, theme generation, thematic maps, and comparison with human-produced themes.",
    "Claimed qualitative methodology": "Thematic analysis following Braun and Clarke's six-phase account; the study explicitly focuses on Phase 2 (initial coding) and Phase 3 (theme generation). It does not label the implementation reflexive, codebook, or coding-reliability thematic analysis.",
    "Actual operationalized methodology": "GPT-3.5-Turbo-16k codes each interview independently, emits code names/descriptions/source quotations, compares new codes against a cumulative codebook to remove duplicates, groups unique codes into themes, and derives theme maps from shared code indices. A second dataset supplies previously published human themes for semantic comparison.",
    "Inductive, deductive, or hybrid": "inductive",
    "Domain": "open qualitative research practices; teaching data science",
    "Dataset name": "Fostering Cultures of Open Qualitative Research: Dataset 2—Interview Transcripts; Teaching Undergraduates with Quantitative Data in the Social Sciences at University of California Santa Barbara",
    "Public or restricted data": "public/open-access data",
    "Number of documents": "24 interviews total: 15 for coding/theme/map demonstration and a separate 9-interview dataset for evaluation",
    "Number of participants": "not reported",
    "Approximate corpus size": "not reported",
    "Document length": "not reported",
    "Language": "not reported",
    "Sensitive-data status": "not reported",
    "Model family": "GPT for generation; SBERT plus Mistral and Llama for evaluation",
    "Exact model/version": "GPT-3.5-Turbo-16k; SBERT model variant not reported; Mistral-7B-Instruct-v0.2; Meta-Llama-3-8B-Instruct",
    "Prompting strategy": "Custom open-ended prompts developed by trial and error with thematic-analysis terminology. Prompt_1 requests code name, description, and quotation in JSON; Prompt_2 compares each new code with the cumulative codebook; Prompt_3 produces themes and code-index memberships. Generation temperature is 0.",
    "Fine-tuning or adaptation": "No weight fine-tuning reported; adaptation is prompt engineering and cumulative codebook processing.",
    "Single-agent or multi-agent": "single-model, non-agent analysis workflow with separate evaluation models",
    "Agent roles": "No agents are defined. GPT-3.5 performs coding, duplicate comparison, theme generation, and map inputs; SBERT and two independent open-weight LLMs evaluate theme similarity.",
    "Human role": "The researcher engineers prompts, operates the pipeline, manually pairs/reorders themes after similarity calculation, selects how shared-code connections are interpreted in maps, and compares outputs with human themes published in an earlier report.",
    "Unit of analysis": "Relevant interview passages/quotations for initial codes; cumulative code entries for duplicate reduction and theme generation; theme pairs for evaluation.",
    "Generated outputs": "JSON initial codes with names, descriptions, and quotations; cumulative deduplicated codebooks; themes with descriptions and code indices; shared-code thematic maps; semantic-similarity and LLM-judge scores.",
    "Evidence/provenance mechanism": "Every initial code includes a source quotation; each theme lists numeric indices that link back to entries in the code dataframe, and maps are constructed from shared code indices.",
    "Baselines": "Previously published human themes for the 9-interview Teaching Data Science dataset; the author's older fixed-seven-theme prompt; evaluation models distinct from the GPT-3.5 generator.",
    "Number of runs or seeds": "For each of the 40-word and 15-word codebook variants, one base theme-generation run plus three additional iterations are reported. The human-theme evaluation uses one Prompt_3 iteration. Random seeds are not reported.",
    "Automatic metrics": "Inductive Thematic Saturation ratio from unique/total code counts; SBERT cosine similarity; 0–1 semantic-equivalence ratings and justifications from Mistral-7B-Instruct-v0.2 and Meta-Llama-3-8B-Instruct.",
    "Human-evaluation design": "No new blinded human evaluation is reported. LLM themes are compared with five human themes taken from a previously published report, after the author manually pairs/reorders themes.",
    "Number and expertise of evaluators": "No new human evaluators; the number and expertise of the analysts who produced the reference report themes are not reported in this paper.",
    "Inter-rater reliability": "not reported",
    "Statistical analysis": "No inferential statistical test or uncertainty interval reported; descriptive code counts, similarity matrices, and repeated theme lists are presented.",
    "Principal results": "The 15-interview workflow produced 183 total/93 unique codes with 40-word descriptions and 211 total/144 unique codes with 15-word descriptions. Repeated theme generations showed both recurring and variable themes. For five manually paired human/LLM themes, SBERT similarities ranged 0.61–0.82; both independent LLM judges rated four of five pairs above 0.8, while one pair was rated substantially lower.",
    "Efficiency or cost results": "No measured time or monetary cost is reported; the discussion notes that larger-context models cost more and frames the workflow as practically deployable.",
    "Ethics and privacy treatment": "The paper uses open-access interview datasets and supplies a data-availability statement. It does not report a dedicated consent/IRB analysis, API data-retention discussion, or responsible-research assessment for sending interview text to a commercial model.",
    "Reproducibility resources": "Official open-access article and full prompts in the paper; both datasets are cited as open-access Figshare/Zenodo resources; exact generator and evaluator model names and temperature are reported. No code repository or random seeds are reported.",
    "Author-reported limitations": "Prompt wording and requested description length change code quantity; repeated theme runs vary; shared-code thematic maps and prompt alignment require further refinement; optimal codebook size is unresolved; only Phases 2 and 3 are implemented; further models, datasets, and validity testing are needed.",
    "Additional validity concerns": "The 'good enough' conclusion rests on semantic similarity and LLM-as-judge ratings rather than blinded qualitative-expert assessment; one human theme set is treated as the comparator; theme pairing is manually reordered after similarity calculation; semantic likeness cannot establish interpretive equivalence; and no uncertainty estimates are reported.",
    "Relationship to prior papers": "Extends De Paoli's earlier GPT-based thematic-analysis procedure with open-ended TA terminology, cumulative duplicate removal, repeated theme generation, and thematic maps; uses the Inductive Thematic Saturation proposal from De Paoli and Mathis (2024).",
    "Relevance to the proposed ARR project": "Direct evidence for open coding, theme induction, quotation provenance, prompt/run sensitivity, and the construct-validity limits of embedding similarity and LLM judges; it motivates plurality-aware, evidence-aware evaluation rather than single-reference theme matching.",
}


BORSE_RECORD = {
    "Paper ID": "borse_2025_inter_rater_reliability",
    "Full citation": "Borse, Nikhil Sanjay, Ravishankar Chatta Subramaniam, and N. Sanjay Rebello. (2025). Investigation of the Inter-Rater Reliability between Large Language Models and Human Raters in Qualitative Analysis. arXiv:2508.14764v2. https://doi.org/10.48550/arXiv.2508.14764",
    "Title": "Investigation of the Inter-Rater Reliability between Large Language Models and Human Raters in Qualitative Analysis",
    "Authors": "Nikhil Sanjay Borse; Ravishankar Chatta Subramaniam; N. Sanjay Rebello",
    "Year": "2025",
    "Venue": "arXiv (physics.ed-ph); comments identify Physics Education Research Conference 2025",
    "Publication type": "arXiv preprint (v2)",
    "Peer-reviewed status": "preprint; peer review not verified",
    "Publication history notes": "arXiv v1 submitted 2025-08-20; v2 revised 2025-08-31. The arXiv comments say 'Physics Education Research Conference 2025', but a separate official proceedings record was not verified, so the evidence status remains preprint.",
    "URL": "https://arxiv.org/abs/2508.14764",
    "DOI": "10.48550/arxiv.2508.14764",
    "Citation count, source, and retrieval date": "1; OpenAlex cited_by_count; retrieved 2026-08-24; OpenAlex W4415240959",
    "Core or adjacent classification": "core",
    "Relationship/dependence family": "Purdue physics-education inter-rater-reliability study; backward-chained from Muse. It is not part of the AAOCA/Auto-TA/SFT-TA/TAMA shared clinical-data family.",
    "Research objective": "Measure agreement between human consensus coding and GPT-4o/GPT-4.5-preview on physics-education discussion segments and test whether prompt engineering and temperature/top-p optimization improve agreement.",
    "Claimed qualitative methodology": "Qualitative coding/thematic coding of STEM Ways of Thinking, with dependability and trustworthiness attributed to Guba and Lincoln; no specific inductive thematic-analysis tradition is claimed.",
    "Actual operationalized methodology": "Two humans assign a fixed four-code rubric to transcript segments and resolve labels to consensus. Each LLM then performs decomposed binary classification for each code, using zero-shot and few-shot/polished prompts and tuned API sampling parameters. Human-consensus versus LLM agreement is quantified.",
    "Inductive, deductive, or hybrid": "deductive",
    "Domain": "undergraduate physics education; engineering-design project discussions",
    "Dataset name": "Engineering Design project peer-interaction transcripts from one calculus-based physics laboratory section",
    "Public or restricted data": "not reported",
    "Number of documents": "14 group-discussion transcripts",
    "Number of participants": "42 undergraduate students, reported as 14 groups of three",
    "Approximate corpus size": "204 text segments, excluding prompt-example segments",
    "Document length": "Each group was asked to record at least five minutes of discussion; transcript word lengths are not reported.",
    "Language": "not reported",
    "Sensitive-data status": "Student audio/transcript data; anonymized under Institutional Review Board guidance.",
    "Model family": "OpenAI GPT",
    "Exact model/version": "GPT-4o; GPT-4.5-preview; exact dated snapshots not reported",
    "Prompting strategy": "Zero-shot was tested, then decomposed few-shot binary classification used a role instruction, code criteria, typically three positive and three negative examples, and one target segment. GPT-4o polished the prompts; temperature and top-p were swept/tuned by code.",
    "Fine-tuning or adaptation": "No model weight fine-tuning reported; adaptation consists of prompt polishing, few-shot examples, model selection, and dataset/theme-specific temperature and top-p tuning.",
    "Single-agent or multi-agent": "single-model classifier per run; not an agent architecture",
    "Agent roles": "not applicable",
    "Human role": "Humans transcribe/clean the recordings, develop/apply the four-code rubric, code all transcripts with two coders, discuss to consensus, supply example quotations, and serve as the reference rater; the authors recommend continuing human oversight.",
    "Unit of analysis": "Transcript text segment, classified independently for each of four non-exclusive codes",
    "Generated outputs": "Binary labels for Engineering Design, Physics Concepts, Math Constructs, and Metacognitive Thinking",
    "Evidence/provenance mechanism": "Each prediction is attached to its input segment and code criterion; prompts include exemplar quotations. No additional source-to-label evidence artifact or audit log is reported.",
    "Baselines": "Two-human consensus labels; GPT-4o with default temperature/top-p and an unpolished prompt; zero-shot versus few-shot/polished prompting; GPT-4o versus GPT-4.5-preview.",
    "Number of runs or seeds": "Five runs per theme for default and optimized comparisons; reported hyperparameter values are averaged over five runs per value. Random seeds are not reported.",
    "Automatic metrics": "Cohen's kappa between human-consensus and LLM labels",
    "Human-evaluation design": "Two humans code the 14 transcripts, review disagreements, and reach consensus; that consensus is treated as one rater and compared with each LLM. Blinding and an untouched held-out evaluation split are not reported.",
    "Number and expertise of evaluators": "Two human coders; expertise is not reported.",
    "Inter-rater reliability": "Human-human pre-consensus reliability is not reported. Human-consensus versus optimized LLM kappa exceeds 0.6 for three codes and is 0.55 for Metacognitive Thinking; Physics Concepts reaches 0.70 and Engineering Design reaches 0.60.",
    "Statistical analysis": "Mann-Whitney test for the average kappa improvement across themes (mean increase 0.14; p < 0.02). Confidence intervals and a multiple-testing adjustment are not reported.",
    "Principal results": "After optimization, one of GPT-4o or GPT-4.5-preview exceeded kappa 0.6 for Engineering Design, Physics Concepts, and Math Constructs; Physics Concepts reached 0.70, Engineering Design 0.60 after a 0.15 gain, and Metacognitive Thinking remained at 0.55. The average gain was 0.14 (p < 0.02), with weaker performance on the more domain-general construct.",
    "Efficiency or cost results": "The authors describe prompt polishing as low-cost and argue that LLMs could scale coding, but report no measured time or monetary savings. They note that proprietary OpenAI API access requires a subscription and may be inequitable.",
    "Ethics and privacy treatment": "Institutional Review Board approval/guidance and anonymization are reported; human oversight is described as necessary for reliable and ethical rating. API data retention and governance are not reported, and proprietary-model accessibility is noted.",
    "Reproducibility resources": "arXiv v2 full text; four-code rubric, example prompt, optimal model/temperature/top-p table, and run count are reported. No public code, data, complete prompt package, dated model snapshots, or seeds are reported.",
    "Author-reported limitations": "Small single-section sample; optimized hyperparameters may overfit and may not generalize; only OpenAI models are studied; proprietary API cost/access is limiting; traditional machine learning is not compared; larger and more diverse datasets are future work.",
    "Additional validity concerns": "Human consensus is used as a single ground truth and hides interpretive disagreement; human labels also provide few-shot examples; preliminary prompt testing used three of the fourteen transcripts and no held-out test partition is described; the study evaluates four fixed codes rather than inductive theme discovery; and repeated tuning on one corpus risks selection bias.",
    "Relationship to prior papers": "Extends LLM-assisted deductive coding work by systematically varying prompt form, model, temperature, and top-p; cited by the later Muse benchmarking paper as related reliability evidence.",
    "Relevance to the proposed ARR project": "Provides a compact design for repeated-run human–LLM agreement evaluation and shows that model/prompt/hyperparameter optimization can materially change kappa, while also illustrating why consensus agreement alone is not qualitative quality or cross-domain validity.",
}


QUALITY_CAUTION = "The total is a compact audit aid, not a ranking of study quality; dimensions must be interpreted individually against each paper's stated claim."


DEPAOLI_QUALITY = {
    "Paper ID": "depaoli_2024_further_explorations",
    "Title": DEPAOLI_RECORD["Title"],
    "Core or adjacent classification": "core",
    "Dimension scores": {
        "Clarity of its qualitative methodology": {"score": 2, "rationale": "Adequate: the paper explicitly anchors the workflow in Braun and Clarke's six phases and states that it operationalizes initial coding and theme generation, while not claiming completion of all phases."},
        "Appropriateness of its dataset": {"score": 1, "rationale": "Partial: two authentic open interview datasets support demonstration and comparison, but sample/context detail and participant counts are limited and only one dataset has reference themes."},
        "Transparency of its computational workflow": {"score": 2, "rationale": "Adequate: the generator model, temperature, prompts, cumulative duplicate-removal procedure, JSON outputs, theme indices, evaluation models, and iteration counts are described in the full text."},
        "Strength and independence of its baselines": {"score": 1, "rationale": "Partial: an earlier fixed-theme prompt and independently produced human themes are compared, but there is no competing system/model baseline and the author manually pairs themes after similarity calculation."},
        "Adequacy of its human evaluation": {"score": 0, "rationale": "Absent/inadequate: no new blinded qualitative-expert evaluation is conducted; the evaluation reuses five themes from a prior report and does not report those analysts' number or expertise."},
        "Validity of its automatic metrics": {"score": 1, "rationale": "Partial: SBERT similarity and independent LLM ratings are transparently reported, but neither is validated here against human judgments of interpretive equivalence and no uncertainty analysis is supplied."},
        "Treatment of interpretive plurality": {"score": 1, "rationale": "Partial: open-ended prompting, multiple runs, and explicit human choice in interpreting maps acknowledge variability, yet the evaluation still treats one five-theme human account as its comparison target."},
        "Evidence grounding and traceability": {"score": 2, "rationale": "Adequate: each code contains a source quotation and theme memberships preserve numeric indices back to the code dataframe, enabling source-to-code-to-theme tracing."},
        "Stability and reproducibility testing": {"score": 1, "rationale": "Partial: a base run and three additional iterations are compared for each of two codebook variants, but seeds, quantitative stability estimates, and independent reruns are not reported."},
        "Ethics, privacy, and responsible-research reporting": {"score": 1, "rationale": "Partial: open datasets and data availability are reported, but consent/IRB provenance, commercial-API retention, and responsible-use risks are not substantively assessed."},
        "Availability of data, prompts, code, and model versions": {"score": 1, "rationale": "Partial: the datasets, full prompt text, model names, and temperature are available, but no code repository, seeds, or fully dated proprietary model snapshot is provided."},
        "Whether conclusions are proportionate to the evidence": {"score": 1, "rationale": "Partial: the author repeatedly frames the work as a demonstration and lists prompt/mapping limitations, but the 'good enough' theme-quality claim exceeds what semantic similarity and LLM judges alone establish."},
    },
    "Total": 14,
    "Interpretation caution": QUALITY_CAUTION,
}


BORSE_QUALITY = {
    "Paper ID": "borse_2025_inter_rater_reliability",
    "Title": BORSE_RECORD["Title"],
    "Core or adjacent classification": "core",
    "Dimension scores": {
        "Clarity of its qualitative methodology": {"score": 1, "rationale": "Partial: the fixed four-code, consensus-coding procedure is clear, but the paper uses broad qualitative/thematic language without distinguishing a specific qualitative-analysis tradition."},
        "Appropriateness of its dataset": {"score": 1, "rationale": "Partial: authentic student discussion transcripts fit the four Ways-of-Thinking codes, but the corpus is a small subset from one lab section and lacks a held-out generalization sample."},
        "Transparency of its computational workflow": {"score": 2, "rationale": "Adequate: models, API use, decomposed binary task, prompt construction/polishing, exemplar structure, parameter values, and repeated-run design are reported."},
        "Strength and independence of its baselines": {"score": 1, "rationale": "Partial: human consensus, two models, default settings, and zero/few-shot variants provide comparators, but the same human-coded corpus informs examples and tuning and no untouched external baseline is used."},
        "Adequacy of its human evaluation": {"score": 1, "rationale": "Partial: two humans code and adjudicate all transcripts, but expertise, blinding, pre-consensus reliability, and independent held-out assessment are not reported."},
        "Validity of its automatic metrics": {"score": 1, "rationale": "Partial: Cohen's kappa is appropriate for binary label agreement, but consensus is treated as ground truth, confidence intervals are absent, and metric validity for qualitative quality is not tested."},
        "Treatment of interpretive plurality": {"score": 0, "rationale": "Absent/inadequate: disagreement is collapsed to one consensus reference and the fixed four-code evaluation does not preserve or evaluate alternative interpretations."},
        "Evidence grounding and traceability": {"score": 1, "rationale": "Partial: every prediction is attached to a source segment and rubric criterion, but no separate rationale/evidence audit trail or public annotation artifact is reported."},
        "Stability and reproducibility testing": {"score": 2, "rationale": "Adequate: performance is averaged across five runs and the study systematically varies prompting, model, temperature, and top-p, although random seeds are not provided."},
        "Ethics, privacy, and responsible-research reporting": {"score": 2, "rationale": "Adequate: IRB guidance, anonymization, the need for human oversight, and proprietary-access inequity are explicitly discussed for student-recording data."},
        "Availability of data, prompts, code, and model versions": {"score": 1, "rationale": "Partial: the rubric, an example prompt, model labels, parameters, and run count are reported, but data, code, full prompts, seeds, and dated model snapshots are unavailable."},
        "Whether conclusions are proportionate to the evidence": {"score": 1, "rationale": "Partial: small-sample, overfitting, model, and access limitations are acknowledged, but claims about scaling without sacrificing rigor/nuance are broader than this single fixed-code corpus supports."},
    },
    "Total": 14,
    "Interpretation caution": QUALITY_CAUTION,
}


BACKWARD_CHAIN_CANDIDATES = [
    {
        "candidate_id": "depaoli_2024_further_explorations",
        "parent_seed_id": "tama_2026",
        "parent_seed": "TAMA: A Human-AI Collaborative Thematic Analysis Framework Using Multi-Agent LLMs for Clinical Interviews",
        "direction": "backward",
        "reference_verification": "Reference 9 in research/fulltext/3828752__1_.txt (publisher full text).",
        "identifier": "10.17169/fqs-25.3.4196",
        "official_url": "https://www.qualitative-research.net/index.php/fqs/article/view/4196",
        "full_text_url": "https://www.qualitative-research.net/index.php/fqs/article/download/4196/5130/19336",
        "official_identity_status": "verified on the FQS landing page; peer-reviewed journal article; published 2024-09-29",
        "full_text_outcome": "retrieved and inspected",
        "full_text_evidence": "Official FQS PDF, 35 pages; Methods pp. 5–13, Results pp. 14–30, Discussion pp. 31–33, Data Availability p. 33.",
        "eligibility_decision": "include_core",
        "eligibility_reason": "Presents and evaluates an LLM workflow for inductive initial coding, theme generation, thematic mapping, and human-theme comparison.",
        "union_status_at_discovery": "No exact DOI/title match in the 1,360-record search union.",
        "master_ready_record": DEPAOLI_RECORD,
        "quality_score": DEPAOLI_QUALITY,
        "quality_evidence_locations": {
            "methodology_and_workflow": "Official PDF pp. 5–13 (Sections 3.0–3.5; Boxes 1–3; Figures 1–5)",
            "dataset": "Official PDF pp. 13–14 (Section 3.5 and start of Results)",
            "provenance": "Official PDF pp. 7–13 (code quotations, code dataframe indices, theme-code relationships)",
            "runs_and_metrics": "Official PDF pp. 18–19, 25–26, and 27–30 (Tables 5/8; Section 4.4; Figures 9–10; Table 11)",
            "results_and_limitations": "Official PDF pp. 27–33 (evaluation, Discussion/Conclusion, Data Availability)",
            "publication_identity": "Official landing page DOI/published metadata; PDF p. 35 internal citation line documents the 25.2/25.3 DOI inconsistency",
        },
    },
    {
        "candidate_id": "borse_2025_inter_rater_reliability",
        "parent_seed_id": "matveyenko_2026_muse",
        "parent_seed": "Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant (Muse)",
        "direction": "backward",
        "reference_verification": "Reference section of research/fulltext/latest/matveyenko_2026_muse.txt.",
        "identifier": "arXiv:2508.14764",
        "official_url": "https://arxiv.org/abs/2508.14764",
        "full_text_url": "https://arxiv.org/pdf/2508.14764",
        "official_identity_status": "verified on arXiv; v1 2025-08-20, v2 2025-08-31; peer review not verified",
        "full_text_outcome": "retrieved and inspected",
        "full_text_evidence": "Official arXiv v2 PDF, 7 pages; Methods pp. 2–3, Results pp. 3–5, Conclusion/Limitations p. 5.",
        "eligibility_decision": "include_core",
        "eligibility_reason": "Empirically evaluates LLM deductive coding against human consensus with repeated prompt/model/hyperparameter comparisons.",
        "union_status_at_discovery": "No exact DOI/arXiv/title match in the 1,360-record search union.",
        "master_ready_record": BORSE_RECORD,
        "quality_score": BORSE_QUALITY,
        "quality_evidence_locations": {
            "methodology_dataset_and_ethics": "arXiv v2 PDF p. 2 (Section II: sample, rubric, two-human consensus, IRB/anonymization)",
            "workflow_and_prompting": "arXiv v2 PDF pp. 2–3 (Figure 1, prompt design, decomposed coding, API and parameter tuning)",
            "runs_metrics_and_results": "arXiv v2 PDF pp. 3–5 (five-run means, Figures 3–4, Table II, kappas and Mann–Whitney test)",
            "limitations_and_responsible_use": "arXiv v2 PDF p. 5 (human oversight, API access, small sample, overfitting and model limitations)",
            "publication_identity": "arXiv landing page and PDF p. 1",
        },
    },
    {
        "candidate_id": "laato_2025_gioia_cot",
        "parent_seed_id": "matveyenko_2026_muse",
        "parent_seed": "Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant (Muse)",
        "direction": "backward",
        "reference_verification": "Reference section of research/fulltext/latest/matveyenko_2026_muse.txt.",
        "identifier": "AMCIS 2025 paper 2130; AISeL article 1249; no DOI reported",
        "official_url": "https://aisel.aisnet.org/amcis2025/data_science/sig_dsa/1/",
        "repository_record_url": "https://research.abo.fi/en/publications/automating-qualitative-data-analysis-with-chain-of-thought-reason/",
        "official_identity_status": "Official AISeL page and university repository records verify a complete peer-reviewed AMCIS 2025 paper, pp. 1942–1951.",
        "abstract_level_scope_evidence": "DeepSeek R1 chain-of-thought pipeline applied to 17 expert interviews using the Gioia method, Levenshtein quotation checks, and comparison with an earlier human analysis; the official abstract reports inaccurate/non-informative higher-order results and nine challenges.",
        "full_text_outcome": "sought but not reproducibly retrieved",
        "retrieval_attempts": [
            "AISeL publisher PDF endpoint returned HTTP 403 to scripted retrieval and an internal-server-error page in the interactive browser.",
            "The Åbo Akademi repository PDF URL indexed by web search returned HTTP 403 and, after the browser's security verification, a page-not-found response.",
            "Search-engine and ResearchGate indexes exposed substantial snippets from multiple sections, but not a complete, locally inspectable 10-page file; snippets were not treated as full text.",
        ],
        "eligibility_decision": "awaiting_full_text",
        "eligibility_reason": "Likely core from official abstract/metadata, but protocol forbids methodological extraction or inclusion without complete full-text inspection.",
        "union_status_at_discovery": "No exact title match in the 1,360-record search union.",
        "master_ready_record": None,
        "quality_score": None,
    },
]


RELEVANCE_TERMS = re.compile(
    r"(?:qualitative|thematic|theme(?:s|d|atic)?|codebook|coding|coded|coder|"
    r"inductive|deductive|open[ -]cod|axial|grounded theory|gioia|content analysis|"
    r"human.?ai|large language model|\bllm\b|concept induction|inter.?rater)",
    re.I,
)

FOCUSED_RELEVANCE_TERMS = re.compile(
    r"(?:thematic analysis|thematic coding|thematic curation|"
    r"qualitative (?:data )?(?:analysis|coding|research|content analysis)|"
    r"qualitative codebook|inductive (?:qualitative )?coding|"
    r"deductive (?:qualitative )?coding|open qualitative coding|axial coding|"
    r"grounded theory|concept induction|human.?ai collaboration.*thematic|"
    r"coding.*dialogue|dialogue coding)",
    re.I,
)


def norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def canonical_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value if value.startswith("10.") else None


def clean_index_title(value: str | None) -> str:
    """Remove interface-only labels without rewriting the scholarly title."""
    value = value or ""
    value = re.sub(r"^(?:\[(?:html|pdf)\]\s*)+", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def identifiers_from_url(value: str | None) -> tuple[str | None, str | None]:
    """Recover identifiers exposed in Scholar result URLs when possible."""
    if not value:
        return None, None
    doi_match = re.search(r"(?:doi/(?:abs/)?|article/)(10\.[^?#]+)", value, re.I)
    if doi_match:
        return canonical_doi(doi_match.group(1)), None
    nature_match = re.search(r"nature\.com/articles/(s[0-9-]+)", value, re.I)
    if nature_match:
        return canonical_doi(f"10.1038/{nature_match.group(1)}"), None
    arxiv_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", value, re.I)
    if arxiv_match:
        return None, arxiv_match.group(1)
    return None, None


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    attempts: int = 3,
) -> tuple[int | None, Any | None, str | None]:
    last_status: int | None = None
    last_error: str | None = None
    for attempt in range(attempts):
        try:
            response = session.request(method, url, json=body, headers=HEADERS, timeout=45)
            last_status = response.status_code
            if response.status_code == 200:
                return response.status_code, response.json(), None
            last_error = f"HTTP {response.status_code}: {response.text[:240].strip()}"
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(1.2 * (attempt + 1))
    return last_status, None, last_error


def openalex_resolve(session: requests.Session, seed: dict[str, Any]) -> dict[str, Any]:
    doi = quote(f"https://doi.org/{seed['doi']}", safe="")
    exact_url = f"https://api.openalex.org/works/{doi}?mailto=research@example.invalid"
    status, payload, error = request_json(session, "GET", exact_url)
    method = "exact DOI"
    score = 1.0 if payload else None
    lookup_url = exact_url
    if payload is None:
        query = urlencode(
            {
                "search": seed["title"],
                "per-page": 5,
                "mailto": "research@example.invalid",
            }
        )
        lookup_url = f"https://api.openalex.org/works?{query}"
        status, search, error = request_json(session, "GET", lookup_url)
        best, best_score = None, 0.0
        for candidate in (search or {}).get("results", []):
            candidate_score = SequenceMatcher(
                None, norm(seed["title"]), norm(candidate.get("display_name"))
            ).ratio()
            if candidate_score > best_score:
                best, best_score = candidate, candidate_score
        if best is not None and best_score >= 0.94:
            payload, score, method, error = best, round(best_score, 4), "title match >=0.94", None
        else:
            payload = None
            score = round(best_score, 4) if best is not None else None
            method = "unresolved; exact DOI then title search"
    if payload is None:
        return {
            "status": "unresolved",
            "http_status": status,
            "lookup_method": method,
            "lookup_url": lookup_url,
            "title_match_score": score,
            "error": error or "No sufficiently exact OpenAlex record.",
        }
    return {
        "status": "resolved",
        "http_status": status,
        "lookup_method": method,
        "lookup_url": lookup_url,
        "title_match_score": score,
        "openalex_id": payload.get("id"),
        "openalex_title": payload.get("display_name"),
        "openalex_doi": canonical_doi(payload.get("doi")),
        "publication_year": payload.get("publication_year"),
        "reported_cited_by_count": payload.get("cited_by_count"),
    }


def compact_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    authors = [
        ((a.get("author") or {}).get("display_name"))
        for a in work.get("authorships", [])
        if ((a.get("author") or {}).get("display_name"))
    ]
    return {
        "id": work.get("id"),
        "doi": canonical_doi(work.get("doi")),
        "title": work.get("display_name"),
        "year": work.get("publication_year"),
        "type": work.get("type"),
        "authors": authors,
        "source": source.get("display_name"),
        "landing_page_url": location.get("landing_page_url"),
    }


def openalex_citing_pass(
    session: requests.Session, openalex_id: str, pass_number: int
) -> dict[str, Any]:
    short_id = openalex_id.rsplit("/", 1)[-1]
    cursor = "*"
    works: list[dict[str, Any]] = []
    page_count = 0
    reported_filter_count = None
    urls: list[str] = []
    started = now_utc()
    error = None
    while cursor:
        query = urlencode(
            {
                "filter": f"cites:{short_id}",
                "per-page": 200,
                "cursor": cursor,
                "mailto": "research@example.invalid",
            }
        )
        url = f"https://api.openalex.org/works?{query}"
        urls.append(url)
        status, payload, call_error = request_json(session, "GET", url)
        if payload is None:
            error = call_error or f"HTTP {status}"
            break
        page_count += 1
        if reported_filter_count is None:
            reported_filter_count = (payload.get("meta") or {}).get("count")
        page_results = payload.get("results", [])
        works.extend(compact_openalex_work(work) for work in page_results)
        next_cursor = (payload.get("meta") or {}).get("next_cursor")
        if not page_results or not next_cursor:
            break
        cursor = next_cursor
        time.sleep(0.08)
    return {
        "pass": pass_number,
        "started_utc": started,
        "completed_utc": now_utc(),
        "status": "complete" if error is None else "incomplete",
        "page_count": page_count,
        "reported_filter_count": reported_filter_count,
        "retrieved_count": len(works),
        "request_urls": urls,
        "error": error,
        "works": works,
    }


def semantic_scholar_audit(
    session: requests.Session, seeds: list[dict[str, Any]]
) -> dict[str, Any]:
    ids = [seed["semantic_scholar_id"] for seed in seeds]
    fields = "paperId,title,year,citationCount,externalIds,url"
    batch_url = f"https://api.semanticscholar.org/graph/v1/paper/batch?fields={fields}"
    batch_started = now_utc()
    status, payload, error = request_json(session, "POST", batch_url, body={"ids": ids})
    records: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        payload = [None] * len(seeds)
    for seed, resolved in zip(seeds, payload):
        item: dict[str, Any] = {
            "seed_id": seed["seed_id"],
            "requested_id": seed["semantic_scholar_id"],
        }
        if not resolved:
            item.update(
                {
                    "resolution_status": "unresolved",
                    "citation_query_status": "not run because seed did not resolve",
                    "error": error or "Batch endpoint returned null for this identifier.",
                }
            )
            records.append(item)
            continue
        item.update(
            {
                "resolution_status": "resolved",
                "paper_id": resolved.get("paperId"),
                "matched_title": resolved.get("title"),
                "year": resolved.get("year"),
                "external_ids": resolved.get("externalIds"),
                "semantic_scholar_url": resolved.get("url"),
                "reported_citation_count": resolved.get("citationCount"),
            }
        )
        citation_fields = (
            "citingPaper.paperId,citingPaper.title,citingPaper.year,"
            "citingPaper.externalIds,citingPaper.url,isInfluential"
        )
        citation_url = (
            "https://api.semanticscholar.org/graph/v1/paper/"
            f"{resolved['paperId']}/citations?limit=1000&fields={citation_fields}"
        )
        cite_status, cites, cite_error = request_json(session, "GET", citation_url)
        citing_records = []
        for row in (cites or {}).get("data", []):
            paper = row.get("citingPaper") or {}
            ext = paper.get("externalIds") or {}
            citing_records.append(
                {
                    "id": paper.get("paperId"),
                    "doi": canonical_doi(ext.get("DOI")),
                    "arxiv": ext.get("ArXiv"),
                    "title": paper.get("title"),
                    "year": paper.get("year"),
                    "url": paper.get("url"),
                    "is_influential": row.get("isInfluential"),
                    "external_ids": ext,
                }
            )
        item.update(
            {
                "citation_query_status": "complete" if cites is not None else "failed",
                "citation_query_http_status": cite_status,
                "citation_query_url": citation_url,
                "retrieved_citation_count": len(citing_records),
                "error": cite_error,
                "citing_works": citing_records,
            }
        )
        records.append(item)
        time.sleep(0.12)
    return {
        "source": "Semantic Scholar Academic Graph API",
        "retrieval_started_utc": batch_started,
        "retrieval_completed_utc": now_utc(),
        "batch_http_status": status,
        "batch_url": batch_url,
        "batch_error": error,
        "coverage_note": (
            "The unauthenticated API was queried by DOI or arXiv identifier. Null resolutions "
            "and HTTP failures are retained rather than replaced by inferred records. The citations "
            "endpoint permits up to 1,000 records per request; no supplied seed approached that cap."
        ),
        "seeds": records,
    }


def official_page_check(session: requests.Session, seed: dict[str, Any]) -> dict[str, Any]:
    started = now_utc()
    try:
        response = session.get(seed["official_url"], headers=HEADERS, timeout=45, allow_redirects=True)
        content_type = response.headers.get("content-type", "not reported")
        return {
            "seed_id": seed["seed_id"],
            "provider": seed["official_provider"],
            "requested_url": seed["official_url"],
            "checked_utc": started,
            "http_status": response.status_code,
            "resolved_url": response.url,
            "content_type": content_type,
            "landing_record_accessible": response.status_code == 200,
            "forward_list_status": "not exposed as a stable machine-readable citing-work export",
            "note": (
                "The official source was used to verify the seed/version. Forward citing-work "
                "enumeration therefore used citation indexes and is reported separately."
            ),
        }
    except requests.RequestException as exc:
        return {
            "seed_id": seed["seed_id"],
            "provider": seed["official_provider"],
            "requested_url": seed["official_url"],
            "checked_utc": started,
            "http_status": None,
            "landing_record_accessible": False,
            "forward_list_status": "not checked because the official page request failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def scholar_audit(session: requests.Session, seed: dict[str, Any]) -> dict[str, Any]:
    query_url = "https://scholar.google.com/scholar?" + urlencode(
        {"q": f'"{seed["title"]}"', "hl": "en", "as_sdt": "0,44"}
    )
    checked = now_utc()
    try:
        response = session.get(query_url, headers=HEADERS, timeout=45)
    except requests.RequestException as exc:
        return {
            "seed_id": seed["seed_id"],
            "query_url": query_url,
            "checked_utc": checked,
            "status": "request failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
    blocked = bool(re.search(r"unusual traffic|captcha", response.text, re.I))
    base = {
        "seed_id": seed["seed_id"],
        "query_url": query_url,
        "checked_utc": checked,
        "http_status": response.status_code,
        "blocked_or_challenged": blocked,
        "method_limit": (
            "Google Scholar has no supported public bulk API in this environment. The audit records "
            "an exact-title landing result and, when exposed, only the first public cited-by page. "
            "This is a diagnostic sample, not a complete export."
        ),
    }
    if response.status_code != 200 or blocked:
        base.update({"status": "unavailable", "error": "HTML request failed or was challenged."})
        return base
    soup = BeautifulSoup(response.text, "html.parser")
    best = None
    best_score = 0.0
    for result in soup.select(".gs_ri"):
        title_node = result.select_one(".gs_rt")
        if not title_node:
            continue
        result_title = title_node.get_text(" ", strip=True)
        score = SequenceMatcher(None, norm(seed["title"]), norm(result_title)).ratio()
        if score > best_score:
            best, best_score = result, score
    if best is None or best_score < 0.82:
        base.update(
            {
                "status": "no sufficiently exact title result",
                "best_title_score": round(best_score, 4),
            }
        )
        return base
    matched_title = best.select_one(".gs_rt").get_text(" ", strip=True)
    cited_by_count = None
    cited_by_url = None
    for link in best.select(".gs_fl a"):
        text = link.get_text(" ", strip=True)
        match = re.fullmatch(r"Cited by ([0-9,]+)", text)
        if match:
            cited_by_count = int(match.group(1).replace(",", ""))
            cited_by_url = urljoin("https://scholar.google.com", link.get("href"))
            break
    base.update(
        {
            "status": "exact-title result inspected",
            "matched_title": matched_title,
            "title_match_score": round(best_score, 4),
            "reported_cited_by_count": cited_by_count,
            "cited_by_url": cited_by_url,
        }
    )
    if not cited_by_url:
        base.update(
            {
                "first_cited_by_page_status": "not available; no cited-by link was exposed",
                "first_cited_by_page_records": [],
            }
        )
        return base
    time.sleep(0.3)
    try:
        cited = session.get(cited_by_url, headers=HEADERS, timeout=45)
        cited_blocked = bool(re.search(r"unusual traffic|captcha", cited.text, re.I))
        rows = []
        if cited.status_code == 200 and not cited_blocked:
            cited_soup = BeautifulSoup(cited.text, "html.parser")
            for result in cited_soup.select(".gs_ri"):
                title_node = result.select_one(".gs_rt")
                if not title_node:
                    continue
                anchor = title_node.select_one("a")
                rows.append(
                    {
                        "title": title_node.get_text(" ", strip=True),
                        "url": anchor.get("href") if anchor else None,
                        "publication_line": (
                            result.select_one(".gs_a").get_text(" ", strip=True)
                            if result.select_one(".gs_a")
                            else None
                        ),
                    }
                )
        base.update(
            {
                "first_cited_by_page_http_status": cited.status_code,
                "first_cited_by_page_blocked_or_challenged": cited_blocked,
                "first_cited_by_page_status": (
                    "sample retrieved" if rows else "no records retrieved"
                ),
                "first_cited_by_page_record_count": len(rows),
                "first_cited_by_page_records": rows,
            }
        )
    except requests.RequestException as exc:
        base.update(
            {
                "first_cited_by_page_status": "request failed",
                "first_cited_by_page_records": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    return base


def master_sets() -> tuple[set[str], set[str]]:
    if not MASTER.exists():
        return set(), set()
    data = json.loads(MASTER.read_text())
    dois, titles = set(), set()
    for record in data.get("evidence_records", []):
        doi = canonical_doi(record.get("DOI"))
        if doi:
            dois.add(doi)
        title = norm(record.get("Title"))
        if title:
            titles.add(title)
    return dois, titles


def triage_union(
    openalex: list[dict[str, Any]], semantic: dict[str, Any], scholar: list[dict[str, Any]]
) -> dict[str, Any]:
    master_dois, master_titles = master_sets()
    aggregate: dict[str, dict[str, Any]] = {}
    doi_index: dict[str, str] = {}
    arxiv_index: dict[str, str] = {}
    title_index: dict[str, str] = {}

    def add(
        *,
        source: str,
        seed_id: str,
        title: str | None,
        doi: str | None = None,
        arxiv: str | None = None,
        identifier: str | None = None,
        year: int | None = None,
        url: str | None = None,
    ) -> None:
        if not title:
            return
        title = clean_index_title(title)
        doi = canonical_doi(doi)
        arxiv = arxiv.lower() if arxiv else None
        normalized_title = norm(title)
        key = (
            (doi_index.get(doi) if doi else None)
            or (arxiv_index.get(arxiv) if arxiv else None)
            or title_index.get(normalized_title)
        )
        if key is None:
            if doi:
                key = f"doi:{doi}"
            elif arxiv:
                key = f"arxiv:{arxiv}"
            elif identifier:
                key = f"id:{identifier}"
            else:
                key = f"title:{normalized_title}"
        row = aggregate.setdefault(
            key,
            {
                "deduplication_key": key,
                "title": title,
                "doi": doi,
                "arxiv": arxiv,
                "year": year,
                "url": url,
                "parent_seed_ids": set(),
                "sources": set(),
            },
        )
        row["parent_seed_ids"].add(seed_id)
        row["sources"].add(source)
        if not row.get("doi") and doi:
            row["doi"] = doi
        if not row.get("arxiv") and arxiv:
            row["arxiv"] = arxiv
        if not row.get("url") and url:
            row["url"] = url
        if doi:
            doi_index[doi] = key
        if arxiv:
            arxiv_index[arxiv] = key
        if normalized_title:
            title_index[normalized_title] = key

    for seed in openalex:
        for work in (seed.get("first_pass") or {}).get("works", []):
            add(
                source="OpenAlex",
                seed_id=seed["seed_id"],
                title=work.get("title"),
                doi=work.get("doi"),
                identifier=work.get("id"),
                year=work.get("year"),
                url=work.get("landing_page_url") or work.get("id"),
            )
    for seed in semantic.get("seeds", []):
        for work in seed.get("citing_works", []):
            add(
                source="Semantic Scholar",
                seed_id=seed["seed_id"],
                title=work.get("title"),
                doi=work.get("doi"),
                arxiv=work.get("arxiv"),
                identifier=work.get("id"),
                year=work.get("year"),
                url=work.get("url"),
            )
    for seed in scholar:
        for work in seed.get("first_cited_by_page_records", []):
            recovered_doi, recovered_arxiv = identifiers_from_url(work.get("url"))
            add(
                source="Google Scholar first-page sample",
                seed_id=seed["seed_id"],
                title=work.get("title"),
                doi=recovered_doi,
                arxiv=recovered_arxiv,
                url=work.get("url"),
            )

    rows = []
    for row in aggregate.values():
        row["parent_seed_ids"] = sorted(row["parent_seed_ids"])
        row["sources"] = sorted(row["sources"])
        row["already_in_master_by_exact_doi_or_normalized_title"] = bool(
            (row.get("doi") and row["doi"] in master_dois) or norm(row["title"]) in master_titles
        )
        row["title_keyword_triage"] = bool(RELEVANCE_TERMS.search(row["title"]))
        row["focused_scope_title_triage"] = bool(FOCUSED_RELEVANCE_TERMS.search(row["title"]))
        rows.append(row)
    rows.sort(key=lambda row: ((row.get("year") or 0), norm(row["title"])), reverse=True)
    candidates = [
        row
        for row in rows
        if row["title_keyword_triage"]
        and not row["already_in_master_by_exact_doi_or_normalized_title"]
    ]
    focused_candidates = [
        row
        for row in rows
        if row["focused_scope_title_triage"]
        and not row["already_in_master_by_exact_doi_or_normalized_title"]
    ]
    return {
        "deduplicated_forward_record_count": len(rows),
        "already_in_master_count": sum(
            row["already_in_master_by_exact_doi_or_normalized_title"] for row in rows
        ),
        "new_title_keyword_triage_candidate_count": len(candidates),
        "new_focused_scope_title_candidate_count": len(focused_candidates),
        "triage_definition": (
            "Mechanical high-recall title filter only; inclusion was not inferred from keywords. "
            "Every retained candidate still requires abstract and full-text eligibility assessment."
        ),
        "all_deduplicated_records": rows,
        "new_title_keyword_triage_candidates": candidates,
        "new_focused_scope_title_candidates": focused_candidates,
    }


def reviewer_screen_forward(screening: dict[str, Any]) -> dict[str, Any]:
    """Apply a conservative title-level decision to every focused candidate.

    These decisions route retrieval; they are not full-text eligibility decisions.
    The default is intentionally to seek full text when the title directly names a
    target computational qualitative-analysis task.
    """
    version_family = {
        "CentaurTA Studio: A Self-Improving Human-Agent Collaboration System for Thematic Analysis": (
            "Existing CentaurTA publication family represented in master as 10.18653/v1/2026.findings-acl.778; "
            "the arXiv title is retained as a version-family link, not a new study."
        ),
    }
    exclude_rules = [
        (
            re.compile(r"^QuaRUM:", re.I),
            "NON_TARGET_OUTPUT",
            "The title describes UML domain-model retrieval/generation from requirements rather than qualitative coding or thematic interpretation as the research contribution.",
        ),
        (
            re.compile(r"Hidden Curriculum|Fostering Critical Engagement.*Andragogy", re.I),
            "QUALITATIVE_RESEARCH_EDUCATION_ONLY",
            "The title signals education or critical engagement about GenAI use, not a system/method that performs or evaluates qualitative analysis.",
        ),
        (
            re.compile(r"Simulacrum of Stories", re.I),
            "LLM_AS_RESEARCH_PARTICIPANT",
            "The LLM is studied as a qualitative-research participant, not used to code or interpret qualitative data.",
        ),
        (
            re.compile(r"AI-Generated Follow-Up Questions", re.I),
            "DATA_COLLECTION_NOT_ANALYSIS",
            "The title concerns semi-structured interview follow-up-question generation, not qualitative-data analysis.",
        ),
        (
            re.compile(r"Use large language models .*supporting qualitative research: A phenomenological study", re.I),
            "AI_USE_AS_STUDY_TOPIC",
            "The phenomenological study concerns researchers' experiences of LLM tools rather than an evaluated computational qualitative-analysis contribution.",
        ),
        (
            re.compile(r"^Future Directions in Qualitative Research$", re.I),
            "NO_COMPUTATIONAL_METHOD_IN_TITLE",
            "The title does not establish an LLM/NLP qualitative-analysis method or directly relevant evaluation contribution.",
        ),
    ]
    adjacent_rules = [
        (
            re.compile(r"Reflexis:|Trustworthy Are LLM-as-Judge|GenAI Is No Silver Bullet|From Variance to Invariance", re.I),
            "ADJACENT_VALIDITY_OR_HUMAN_PROCESS",
            "Directly relevant to reflexivity, evaluator validity, failure modes, or structured qualitative annotation; full text is needed to decide core versus adjacent status.",
        ),
        (
            re.compile(r"Comparing qualitative thematic analysis and machine-based topic modelling|From Transformers Come Themes", re.I),
            "ADJACENT_COMPARATIVE_NLP",
            "Compares or evaluates a non-LLM topic-modeling approach against qualitative analysis; potentially useful adjacent evidence but not a core LLM study from title alone.",
        ),
        (
            re.compile(r"Addressing the Efficacy of Quality|Large Language Models in Qualitative Research: Uses|COREQ\+LLM|Can machines perform|Computer-assisted qualitative visual analysis", re.I),
            "CONTEXTUAL_OR_METHODOLOGICAL",
            "The title indicates reporting guidance, conceptual debate, qualitative-method context, or non-text historical automation; retain for contextual/full-text assessment rather than core inclusion.",
        ),
        (
            re.compile(r"Harnessing the power of AI in qualitative research: Exploring|From Assistance to Autonomy", re.I),
            "HUMAN_AI_WORKFLOW_STUDY",
            "Potentially relevant human–AI workflow evidence, but the title does not establish that the evaluated contribution itself performs qualitative coding; full text is required.",
        ),
    ]
    rows = []
    for candidate in screening["new_focused_scope_title_candidates"]:
        title = candidate["title"]
        if title in version_family:
            outcome = "existing_master_version_family"
            reason_code = "VERSION_FAMILY_ALREADY_REPRESENTED"
            reason = version_family[title]
        else:
            matched = next((rule for rule in exclude_rules if rule[0].search(title)), None)
            if matched:
                outcome = "exclude_at_title"
                _, reason_code, reason = matched
            else:
                matched = next((rule for rule in adjacent_rules if rule[0].search(title)), None)
                if matched:
                    outcome = "seek_full_text_adjacent_or_contextual"
                    _, reason_code, reason = matched
                else:
                    outcome = "seek_full_text_potential_core"
                    reason_code = "DIRECT_TARGET_TASK_TITLE"
                    reason = (
                        "The title directly names automated/assisted thematic analysis, qualitative coding, "
                        "codebook/schema induction, qualitative-analysis evaluation, or a human–AI analysis workflow; "
                        "eligibility and extraction require complete full text."
                    )
        if not candidate.get("doi") and not candidate.get("arxiv"):
            identity_status = "citation-index record only; official identifier not reported"
        else:
            identity_status = "identifier supplied by at least one citation index; official-page verification still required before inclusion"
        rows.append(
            {
                "title": title,
                "year": candidate.get("year") if candidate.get("year") is not None else "not reported",
                "doi": candidate.get("doi") or "not reported",
                "arxiv": candidate.get("arxiv") or "not reported",
                "url": candidate.get("url") or "not reported",
                "parent_seed_ids": candidate["parent_seed_ids"],
                "citation_index_sources": candidate["sources"],
                "identity_status": identity_status,
                "title_screen_outcome": outcome,
                "reason_code": reason_code,
                "reason": reason,
                "full_text_status": "not inspected in this forward-chain pass",
                "master_inclusion_status": "not included from title/index evidence",
            }
        )
    counts = dict(sorted((key, sum(row["title_screen_outcome"] == key for row in rows)) for key in {
        row["title_screen_outcome"] for row in rows
    }))
    return {
        "scope_count": len(rows),
        "scope_definition": "Every forward record not exactly in master that passed the focused qualitative-analysis title filter.",
        "decision_counts": counts,
        "decisions": rows,
        "materiality_interpretation": (
            "The forward indexes produced title-level records that could be materially eligible, so no stopping/saturation "
            "claim is justified. None is promoted to the evidence table until its official identity and complete full text are inspected."
        ),
    }


def run() -> dict[str, Any]:
    session = requests.Session()
    started = now_utc()

    official_checks = []
    for seed in SEEDS:
        official_checks.append(official_page_check(session, seed))
        time.sleep(0.05)

    openalex_results = []
    for seed in SEEDS:
        resolution = openalex_resolve(session, seed)
        row: dict[str, Any] = {"seed_id": seed["seed_id"], "resolution": resolution}
        if resolution.get("status") == "resolved":
            row["first_pass"] = openalex_citing_pass(session, resolution["openalex_id"], 1)
        else:
            row["first_pass"] = {
                "pass": 1,
                "status": "not run because seed did not resolve",
                "retrieved_count": 0,
                "works": [],
            }
        openalex_results.append(row)
        time.sleep(0.08)

    confirmation_started = now_utc()
    for row in openalex_results:
        resolution = row["resolution"]
        if resolution.get("status") == "resolved":
            second = openalex_citing_pass(session, resolution["openalex_id"], 2)
        else:
            second = {
                "pass": 2,
                "status": "not run because seed did not resolve",
                "retrieved_count": 0,
                "works": [],
            }
        first_ids = {work.get("id") for work in row["first_pass"].get("works", [])}
        second_ids = {work.get("id") for work in second.get("works", [])}
        second["same_record_set_as_first_pass"] = first_ids == second_ids
        second["added_since_first_pass"] = sorted(x for x in second_ids - first_ids if x)
        second["missing_since_first_pass"] = sorted(x for x in first_ids - second_ids if x)
        row["confirmation_pass"] = second
        row["confirmation_summary"] = {
            "first_count": row["first_pass"].get("retrieved_count"),
            "second_count": second.get("retrieved_count"),
            "same_record_set": first_ids == second_ids,
            "materially_new_title_level_records_on_confirmation": len(second_ids - first_ids),
        }
        # Keep full records once; the pass-2 identifiers and differences are sufficient to reproduce comparison.
        second.pop("works", None)
        time.sleep(0.08)

    semantic = semantic_scholar_audit(session, SEEDS)

    scholar_results = []
    for seed in SEEDS:
        scholar_results.append(scholar_audit(session, seed))
        time.sleep(0.35)

    screening = triage_union(openalex_results, semantic, scholar_results)
    reviewer_screening = reviewer_screen_forward(screening)

    return {
        "metadata": {
            "title": "Backward and forward citation-chaining audit for supplied seed papers",
            "search_cutoff": SEARCH_CUTOFF,
            "generated_utc": now_utc(),
            "run_started_utc": started,
            "confirmation_pass_started_utc": confirmation_started,
            "seed_count": len(SEEDS),
            "reviewer_count": 1,
            "protocol": (
                "Inspect the three reference-derived backward candidates; query every supplied seed "
                "in OpenAlex, Semantic Scholar, Google Scholar's public HTML interface, and its "
                "official source; repeat OpenAlex; deduplicate by DOI/title; and require inspected "
                "full text before evidence-table inclusion."
            ),
            "non_saturation_statement": (
                "No citation-index saturation claim is made. A stable OpenAlex confirmation pass "
                "shows only that this source returned the same records during this run. Google "
                "Scholar was not bulk-exportable, Semantic Scholar has index-specific omissions, "
                "and Scopus/Web of Science were not available."
            ),
        },
        "seed_papers": SEEDS,
        "backward_chain_candidates": BACKWARD_CHAIN_CANDIDATES,
        "backward_chain_summary": {
            "candidate_count": len(BACKWARD_CHAIN_CANDIDATES),
            "full_text_retrieved_and_inspected": sum(
                row["full_text_outcome"] == "retrieved and inspected"
                for row in BACKWARD_CHAIN_CANDIDATES
            ),
            "reports_sought_but_not_retrieved": sum(
                row["full_text_outcome"] == "sought but not reproducibly retrieved"
                for row in BACKWARD_CHAIN_CANDIDATES
            ),
            "eligible_core_after_full_text": sum(
                row["eligibility_decision"] == "include_core"
                for row in BACKWARD_CHAIN_CANDIDATES
            ),
            "excluded_after_full_text": 0,
            "master_ready_record_count": sum(
                row.get("master_ready_record") is not None
                for row in BACKWARD_CHAIN_CANDIDATES
            ),
        },
        "forward_chain_audit": {
            "official_source_checks": official_checks,
            "openalex": {
                "source": "OpenAlex API",
                "method": (
                    "Exact DOI resolution was preferred; normalized title similarity >=0.94 was "
                    "required as fallback. All citing records were cursor-paginated at 200/page."
                ),
                "seeds": openalex_results,
            },
            "semantic_scholar": semantic,
            "google_scholar": {
                "source": "Google Scholar public HTML interface",
                "method_limit": (
                    "No supported public bulk API was available. Exact-title result counts and at "
                    "most the first cited-by page were recorded; these samples are not exhaustive."
                ),
                "seeds": scholar_results,
            },
        },
        "forward_result_screening": screening,
        "reviewer_screening_decisions": reviewer_screening,
        "flow_reconciliation": {
            "baseline_source": "research/review_flow.json after the Dörfel 2026 evidence-track merge",
            "baseline": {
                "reports_sought_for_retrieval": 61,
                "reports_not_retrieved": 2,
                "reports_assessed": 59,
                "full_text_exclusions": 1,
                "retained_reports": 58,
                "retained_by_classification": {"core": 42, "adjacent": 12, "contextual": 4},
            },
            "citation_chain_changes": {
                "new_reports_sought": 3,
                "new_reports_not_retrieved": 1,
                "new_reports_assessed": 2,
                "new_full_text_exclusions": 0,
                "new_retained_reports": 2,
                "new_retained_core": 2,
            },
            "reconciled": {
                "reports_sought_for_retrieval": 64,
                "reports_not_retrieved": 3,
                "reports_assessed": 61,
                "full_text_exclusions": 1,
                "retained_reports": 60,
                "retained_by_classification": {"core": 44, "adjacent": 12, "contextual": 4},
            },
            "identities": [
                "64 sought - 3 not retrieved = 61 assessed",
                "61 assessed - 1 excluded = 60 retained",
                "44 core + 12 adjacent + 4 contextual = 60 retained",
            ],
            "master_projection_after_safe_merge": {
                "evidence_records": 73,
                "core_quality_scores": 44,
                "note": "Current validated master before these chain additions contains 71 records and 42 core quality rows; only De Paoli and Borse are master-ready.",
            },
        },
        "limitations": [
            "One reviewer performed citation screening and extraction.",
            "Citation indexes differ in coverage and merge preprint/published versions differently.",
            "Google Scholar offered no supported reproducible bulk export; only diagnostic first-page samples were retained.",
            "Official publisher pages verify seed identity/version but generally do not expose stable machine-readable forward-citation lists.",
            "A title-keyword triage is deliberately high recall and is not an eligibility decision.",
            "A paper is not counted as included from title or abstract evidence alone.",
        ],
    }


def write_markdown(data: dict[str, Any]) -> None:
    oa = data["forward_chain_audit"]["openalex"]["seeds"]
    ss = data["forward_chain_audit"]["semantic_scholar"]["seeds"]
    scholar = data["forward_chain_audit"]["google_scholar"]["seeds"]
    lines = [
        "# Citation-chaining audit",
        "",
        f"Search cutoff: {SEARCH_CUTOFF}. Seeds checked: {len(SEEDS)}. Reviewer: one.",
        "",
        "## Forward checks by seed",
        "",
        "| Seed | OpenAlex pass 1 / pass 2 | Stable set? | Semantic Scholar retrieved | Google Scholar diagnostic |",
        "|---|---:|:---:|---:|---:|",
    ]
    ss_by = {row["seed_id"]: row for row in ss}
    gs_by = {row["seed_id"]: row for row in scholar}
    for row in oa:
        seed_id = row["seed_id"]
        first = row["first_pass"].get("retrieved_count", 0)
        second = row["confirmation_pass"].get("retrieved_count", 0)
        stable = "yes" if row["confirmation_summary"]["same_record_set"] else "no"
        ss_count = ss_by.get(seed_id, {}).get("retrieved_citation_count", "not available")
        gs_count = gs_by.get(seed_id, {}).get("reported_cited_by_count", "not available")
        lines.append(f"| `{seed_id}` | {first} / {second} | {stable} | {ss_count} | {gs_count} |")
    lines.extend(
        [
            "",
            "## Backward-chain outcomes",
            "",
            "| Candidate | Parent seed | Full-text outcome | Eligibility outcome |",
            "|---|---|---|---|",
        ]
    )
    for row in data["backward_chain_candidates"]:
        label = (
            row.get("master_ready_record", {}).get("Title")
            if row.get("master_ready_record")
            else row["candidate_id"].replace("_", " ")
        )
        lines.append(
            f"| {label} | `{row['parent_seed_id']}` | "
            f"{row['full_text_outcome']} | {row['eligibility_decision']} |"
        )
    backward = data["backward_chain_summary"]
    lines.extend(
        [
            "",
            f"Two candidates were reproducibly retrieved, inspected in full, and retained as core evidence "
            f"({backward['eligible_core_after_full_text']} total): De Paoli (2024) and Borse et al. (2025). "
            "Laato et al. (2025) remains explicitly sought but not retrieved and was not added to the master evidence table.",
        ]
    )
    screen = data["forward_result_screening"]
    reviewer = data["reviewer_screening_decisions"]
    decision_counts = ", ".join(
        f"{key}={value}" for key, value in reviewer["decision_counts"].items()
    )
    lines.extend(
        [
            "",
            "## Screening state",
            "",
            f"The API/sample union contains {screen['deduplicated_forward_record_count']} deduplicated records; "
            f"{screen['already_in_master_count']} exactly match a current master DOI/title and "
            f"{screen['new_title_keyword_triage_candidate_count']} new records passed the deliberately broad title-keyword triage.",
            "",
            "The generated JSON is the audit source of truth. It preserves per-seed parentage, source-specific failures, "
            "the complete OpenAlex first-pass records, Semantic Scholar records, confirmation differences, and Google Scholar samples.",
            "",
            f"All {reviewer['scope_count']} focused-scope forward records received a conservative title-level routing decision "
            f"({decision_counts}). These are retrieval decisions, not full-text inclusion decisions; no forward record was "
            "promoted to the master evidence table without complete full-text inspection.",
            "",
            "## Interpretation limit",
            "",
            data["metadata"]["non_saturation_statement"],
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines))


def main() -> None:
    data = run()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    write_markdown(data)
    print(OUT)
    print(OUT_MD)


if __name__ == "__main__":
    main()
