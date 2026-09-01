#!/usr/bin/env python3
"""Build the auditable second-pass resolution for 2020--2024/undated records.

The artifact keeps the source abstract verbatim, applies explicit reviewer decisions,
and distinguishes title/abstract routing from full-text inclusion. It also resolves the
six <=2024/undated focused forward-chain records that were not exact union matches.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from screening_2020_2024_inclusions import inclusion_quality_scores, inclusion_records

ROOT = Path(__file__).resolve().parent
FLOW = ROOT / "review_flow.json"
UNION = ROOT / "search_union_deduplicated.json"
MASTER = ROOT / "master_evidence.json"
CHAIN = ROOT / "citation_chaining.json"
OUT = ROOT / "screening_2020_2024_resolution.json"
RETRIEVAL_LOG = ROOT / "screening_2020_2024_retrieval_log.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def in_year_scope(value: object) -> bool:
    try:
        return 2020 <= int(value) <= 2024
    except (TypeError, ValueError):
        return True


# Manually reviewed after reading the union title and abstract. These are routing
# decisions only unless a master-ready extraction is attached below.
POTENTIAL_CORE = {
    "TA-0889", "TA-0890", "TA-0891", "TA-0892", "TA-0901", "TA-0910",
    "TA-0915", "TA-0916", "TA-0918", "TA-0922", "TA-0953", "TA-0954",
    "TA-0956", "TA-0971", "TA-0981", "TA-0982", "TA-0985", "TA-1018",
    "TA-1026", "TA-1038", "TA-1049", "TA-1053", "TA-1057", "TA-1069",
    "TA-1078", "TA-1095", "TA-1096", "TA-1114", "TA-1121", "TA-1132",
    "TA-1141", "TA-1145", "TA-1230", "TA-1270", "TA-1278", "TA-1288",
    "TA-1291", "TA-1307", "TA-1310", "TA-1319", "TA-1329", "TA-1331",
    "TA-1332", "TA-1334", "TA-1335", "TA-1337", "TA-1351", "TA-1356",
}

POTENTIAL_ADJACENT = {
    "TA-0921": "The abstract combines LDA with structured qualitative analysis; it is computationally adjacent but the LLM is the topic of the corpus rather than the analyst.",
    "TA-0929": "The title directly proposes temporal-pattern support for qualitative data analysis, but the missing union abstract requires full-text assessment of whether this is qualitative interpretation or topic discovery.",
    "TA-0965": "The abstract studies gender/queer dialect bias in language-model harmful-speech detection, which is adjacent evidence on identity-linked representation confounding rather than a qualitative-analysis system.",
    "TA-0995": "The abstract evaluates BERTopic, LDA, and NMF with qualitative researchers; this is adjacent topic-model support and is not itself an LLM coding or theme-induction method.",
    "TA-1003": "The abstract presents a shortcut-learning benchmark for text classification; this directly informs RQ6 but does not perform qualitative coding.",
    "TA-1019": "The abstract introduces reflexive content analysis and is relevant methodological guidance, but it contains no computational contribution.",
    "TA-1036": "The abstract evaluates cultural and gender bias in open-ended LLM generation, making it adjacent responsible-research evidence rather than qualitative analysis automation.",
    "TA-1080": "The abstract operationalizes 'thematic analysis' as supervised multilabel poem-topic classification, making it useful evidence of methodological conflation but not a core qualitative-analysis study.",
    "TA-1142": "The title links a reproducible open-coding kit with epistemic-network analysis; it is a pre-LLM computational qualitative method requiring full-text assessment.",
    "TA-1236": "The title proposes word-association theme detection, a related non-LLM computational method whose interpretive status requires full text.",
    "TA-1248": "The title is directly relevant methodological guidance on inter-rater reliability in qualitative coding, but the union supplies no abstract and it is not a computational system.",
    "TA-1275": "The abstract reports LLM analysis of Nobel literature; full text is required to determine whether the output is qualitative interpretation or only topic/label extraction.",
    "TA-1292": "The abstract compares GPT-4 and human-client content, which may inform qualitative-output validity but is not clearly a qualitative-analysis method.",
    "TA-1314": "The abstract describes image embeddings with human-in-the-loop analysis of social-movement messages; it is adjacent multimodal evidence rather than text qualitative coding.",
    "TA-1316": "The abstract describes large-scale topic/sentiment analysis of news with generative AI; it is adjacent computational corpus interpretation, not clearly qualitative methodology.",
    "TA-1317": "The abstract describes LLM-based topics and sentiments in global news; it is adjacent computational corpus interpretation, not clearly qualitative methodology.",
    "TA-1327": "The abstract presents an LLM-labeled clustering pipeline for interpretable themes; it is adjacent because themes originate from clustering rather than an identified qualitative tradition.",
    "TA-1339": "The abstract reports mixed computational and qualitative content analysis of policy discourse; full text is needed to establish the role of NLP/LLMs in interpretation.",
    "TA-1353": "The abstract proposes qualitative fairness analysis of LLM depression predictions, directly relevant to high-stakes validity but not a qualitative-coding system.",
    "TA-1354": "The abstract primarily evaluates sentiment classifiers and only then performs thematic analysis; full text is needed to determine whether an LLM performed the qualitative step.",
    "TA-1355": "The abstract uses BERTopic to assist thematic analysis and Qwen for sentiment labeling; it is adjacent topic-model support rather than LLM qualitative coding.",
}

# These two records had already received complete-text extraction before the
# 67-record terminal-disposition pass requested for the remaining advances.
PRIOR_READY_IDS = {"TA-1078", "TA-1230"}

VERSION_FAMILIES = {
    "TA-0955": (
        "later_peer_reviewed_version_identified",
        "The 2024 arXiv record was updated in November 2025 and published as Meng et al., ACM TOCHI 33(1), 2026, DOI 10.1145/3778354; resolve and extract the peer-reviewed 2026 version in the 2026 evidence track.",
    ),
    "TA-1113": (
        "earlier_version_family",
        "This QualiGPT arXiv paper is an earlier version/tool-family record of the later 2024 QualiGPT study at TA-1049; it is not counted as a separate independent study without a dependence audit.",
    ),
    "TA-1273": (
        "duplicate_version_family",
        "This title and abstract duplicate TA-1060 ('Always Nice and Confident, Sometimes Wrong'); both study developers' experiences with LLM tools rather than automated qualitative analysis.",
    ),
    "TA-1285": (
        "existing_master_version_family",
        "CentaurTA Studio is the arXiv/system version of the CentaurTA publication family already represented in master evidence as centaurta_2026; it is not a new independent study.",
    ),
    "TA-1299": (
        "earlier_version_family",
        "This CHALET case-study title is an earlier publication-family version of TA-0955; the later peer-reviewed 2026 TOCHI version is the preferred record.",
    ),
    "TA-1271": (
        "earlier_version_family",
        "Agent-as-Peer-Debriefer and TA-1319 LLM-as-Peer-Debriefer report the same three-dataset, three-model multi-perspective framework; TA-1319 is retained as the preferred current title pending full-text/version verification.",
    ),
}


# Terminal decisions after inspecting the complete locally retrieved text.  These
# are intentionally paper-specific: adjacent value alone does not make a record an
# eligible study when the computational task is not qualitative interpretation.
FULL_TEXT_TERMINAL = {
    "TA-0921": (
        "exclude_after_full_text",
        "AI_AS_STUDY_TOPIC_AFTER_FULL_TEXT",
        "The complete article uses human thematic analysis of clinician interviews to study ethical concerns about LLM adoption; an LLM is the study topic, not the qualitative analyst.",
    ),
    "TA-0929": (
        "exclude_after_full_text",
        "NON_LLM_TEMPORAL_CLASSIFICATION_AFTER_FULL_TEXT",
        "The complete ACL demo paper classifies sentences against researcher-specified concepts and visualizes their prevalence over time; it does not generate or evaluate qualitative codes or themes with an LLM.",
    ),
    "TA-0965": (
        "exclude_after_full_text",
        "HARMFUL_SPEECH_CLASSIFICATION_AFTER_FULL_TEXT",
        "The complete paper audits dialect and gender bias in harmful-speech classifiers; it does not perform or evaluate qualitative coding or thematic interpretation.",
    ),
    "TA-0995": (
        "exclude_after_full_text",
        "TOPIC_MODEL_COMPARISON_AFTER_FULL_TEXT",
        "The complete paper compares LDA, NMF, and BERTopic for corpus topic discovery and researcher usability, without an LLM-based qualitative coding or theme-generation method.",
    ),
    "TA-1003": (
        "exclude_after_full_text",
        "TEXT_CLASSIFICATION_VALIDITY_AFTER_FULL_TEXT",
        "The complete paper is a shortcut-learning benchmark for supervised text classification; its validity findings are general NLP evidence rather than a qualitative-analysis study.",
    ),
    "TA-1036": (
        "exclude_after_full_text",
        "OPEN_ENDED_GENERATION_BIAS_AFTER_FULL_TEXT",
        "The complete paper audits cultural and gender stereotypes in open-ended LLM generation; it does not use an LLM to code or interpret qualitative data.",
    ),
    "TA-1095": (
        "exclude_after_full_text",
        "DOWNSTREAM_PERSONA_GENERATION_AFTER_FULL_TEXT",
        "The complete paper evaluates LLM generation of user personas from interview-derived material; persona authoring is a downstream design task, not a study of qualitative coding or theme induction.",
    ),
    "TA-1145": (
        "exclude_after_full_text",
        "DOWNSTREAM_PERSONA_GENERATION_AFTER_FULL_TEXT",
        "The complete paper tests phase-six persona writing after thematic-analysis inputs have already been produced; it does not evaluate the LLM as the qualitative coder or theme analyst.",
    ),
    "TA-1316": (
        "earlier_version_family",
        "VERSION_OR_PUBLICATION_FAMILY",
        "The complete arXiv text, authors, 24,827-article dataset, methods, and results match TA-1317; TA-1317 is the ICWSM 2024 proceedings version and is the preferred family record.",
    ),
    "TA-1317": (
        "exclude_after_full_text",
        "TOPIC_SENTIMENT_NEWS_ANALYSIS_AFTER_FULL_TEXT",
        "The preferred ICWSM full text uses BERTopic, lexicon sentiment analysis, and a human-built codebook to characterize news coverage; it does not evaluate an LLM-supported qualitative-analysis workflow.",
    ),
    "TA-1121": (
        "later_peer_reviewed_version_identified",
        "VERSION_OR_PUBLICATION_FAMILY",
        "The inspected 2023 arXiv manuscript was later published under the title 'Harnessing the power of AI in qualitative research: Exploring, using and redesigning ChatGPT' in Computers in Human Behavior: Artificial Humans (2025), DOI 10.1016/j.chbah.2025.100144; the peer-reviewed version belongs in the 2025 track.",
    ),
    "TA-1307": (
        "resolved_outside_year_batch_handoff_2026",
        "INDEX_YEAR_RESOLVED_FROM_FULL_TEXT",
        "The retrieved full text is arXiv:2601.15338v1, submitted 20 January 2026; it is a 2026 axial-coding study and is handed to the 2026 evidence track rather than counted in this <=2024 batch.",
    ),
    "TA-1327": (
        "resolved_outside_year_batch_handoff_2026",
        "INDEX_YEAR_RESOLVED_FROM_FULL_TEXT",
        "The retrieved full text is arXiv:2601.13317v2, updated 24 June 2026 and analyzing data through September 2025; it is handed to the 2026 evidence track.",
    ),
    "TA-1332": (
        "resolved_outside_year_batch_handoff_2025",
        "INDEX_YEAR_RESOLVED_FROM_FULL_TEXT",
        "The retrieved proceedings text is explicitly paginated in the CSCL 2025 Proceedings (pages 415–418); it is handed to the 2025 evidence track and not counted as an undated <=2024 inclusion.",
    ),
    "TA-1339": (
        "exclude_after_full_text",
        "HUMAN_QUALITATIVE_ANALYSIS_AI_AS_TOPIC",
        "The complete 2024 manuscript uses three human coders for qualitative content analysis of 74 Swedish opinion articles and explicitly rejects an LLM approach after a brief Gemma experiment; ChatGPT is the debate topic, not the analyst.",
    ),
    "TA-1354": (
        "resolved_outside_year_batch_handoff_2025",
        "INDEX_YEAR_RESOLVED_FROM_FULL_TEXT",
        "The retrieved version of record is in the Proceedings of the 58th Hawaii International Conference on System Sciences (HICSS 2025); it is handed to the 2025 track.",
    ),
    "TA-1355": (
        "resolved_outside_year_batch_handoff_2025",
        "INDEX_YEAR_RESOLVED_FROM_FULL_TEXT",
        "The retrieved manuscript is arXiv:2510.06788v1, submitted 8 October 2025; it is handed to the 2025 track rather than treated as an undated <=2024 record.",
    ),
}

LOCAL_FULL_TEXT = {
    "TA-0889": "research/fulltext/screening_2020_2024/2401.03481.txt",
    "TA-0910": "research/fulltext/screening_2020_2024/2405.06919.txt",
    "TA-0916": "research/fulltext/screening_2020_2024/2402.01386.txt",
    "TA-0953": "research/fulltext/screening_2020_2024/2401.04138.txt",
    "TA-0955": "research/fulltext/screening_2020_2024/2405.05758.txt",
    "TA-0981": "research/fulltext/screening_2020_2024/2408.05126.txt",
    "TA-1018": "research/fulltext/screening_2020_2024/2401.03239.txt",
    "TA-1026": "research/fulltext/screening_2020_2024/2401.15170.txt",
    "TA-1038": "research/fulltext/screening_2020_2024/2404.08488.txt",
    "TA-1049": "research/fulltext/screening_2020_2024/2407.14925.txt",
    "TA-1053": "research/fulltext/screening_2020_2024/2309.17447.txt",
    "TA-1069": "research/fulltext/screening_2020_2024/2305.13014.txt",
    "TA-1078": "research/fulltext/screening_2020_2024/2304.07366.txt",
    "TA-1095": "research/fulltext/screening_2020_2024/2310.06391.txt",
    "TA-1113": "research/fulltext/screening_2020_2024/2310.07061.txt",
    "TA-1121": "research/fulltext/screening_2020_2024/2309.10771.txt",
    "TA-1145": "research/fulltext/screening_2020_2024/2305.18099.txt",
    "TA-1230": "research/fulltext/screening_2020_2024/2102.03702.txt",
}


def excluded_reason(title: str, abstract: str) -> tuple[str, str]:
    text = f"{title} {abstract}".lower()
    if re.search(r"speech|voice|audio|speaker|phoneme|prosod|accent conversion|talking head|face perception|eeg|foley|tts|asr", text):
        return "FALSE_FRIEND_SPEECH_OR_MULTIMODAL", "The title/abstract concerns speech, audio, face, gesture, or physiological representation rather than qualitative coding or thematic interpretation."
    if re.search(r"uml|smart contract|code generation|code authoring|programming assistant|generated code|software systems|inference engines", text):
        return "PROGRAMMING_CODE_FALSE_FRIEND", "Here 'code' denotes software/programming or system behavior, not qualitative coding."
    if re.search(r"beam codebook|stochastic codebook|object categorization|visual question|image representation|vision-language representation", text):
        return "TECHNICAL_CODEBOOK_FALSE_FRIEND", "Here 'codebook' or representation is a technical signal/vision construct, not a qualitative codebook."
    if re.search(r"chapter|qualitative data analysis plan|doing qualitative data analysis|secondary qualitative data analysis|teaching qualitative|principles of qualitative|procedures of qualitative|qualitative data analysis strategies", title.lower()):
        return "GENERIC_METHODS_NO_COMPUTATIONAL_CONTRIBUTION", "The title/abstract is general qualitative-method instruction and does not present computational support or a uniquely needed evaluation/validity contribution."
    if re.search(r"perceptions|experiences|perspectives|voices|attitudes|awareness|mixed.methods|qualitative comparison", title.lower()) and not re.search(r"qualitative (?:data )?(?:analysis|coding).*?(?:llm|gpt|artificial intelligence)|(?:llm|gpt|artificial intelligence).*?qualitative (?:data )?(?:analysis|coding)", text):
        return "AI_AS_STUDY_TOPIC", "The abstract uses qualitative analysis to study people's experiences or perceptions of an AI application; it does not contribute an automated qualitative-analysis method."
    if re.search(r"diagnostic|patient education|clinical summar|trial eligibility|chatbot|tutor|mentor|robot|vignette|reflection|follow-up question", title.lower()):
        return "NON_TARGET_LLM_APPLICATION", "The LLM application is diagnosis, summarization, education, dialogue, or another non-target task rather than qualitative-data analysis."
    if not re.search(r"llm|large language|chatgpt|gpt-|generative ai|artificial intelligence|machine learning|computational|automat|natural language|nlp", text):
        return "NO_COMPUTATIONAL_CONTRIBUTION", "Neither the title nor the supplied abstract describes an LLM/NLP/computational contribution to qualitative analysis."
    return "NO_TARGET_TASK_INTERSECTION_AFTER_ABSTRACT", "After review of the supplied title and abstract, the computational contribution does not perform, assist, or evaluate qualitative coding/thematic interpretation; any qualitative term is incidental or only a study method."


def routing_reason(title: str, abstract: str) -> str:
    task_terms = []
    for label, pattern in [
        ("open/inductive coding", r"open coding|inductive coding"),
        ("deductive coding", r"deductive coding"),
        ("codebook development", r"codebook"),
        ("thematic analysis/theme generation", r"thematic analysis|theme generation|themes"),
        ("qualitative-analysis workflow", r"qualitative (?:data )?analysis"),
    ]:
        if re.search(pattern, f"{title} {abstract}", re.I):
            task_terms.append(label)
    named = ", ".join(task_terms[:3]) or "a directly named qualitative-analysis task"
    if abstract:
        return f"The supplied abstract describes an LLM/NLP contribution to {named}; full text is required before methodological extraction or inclusion."
    return f"The title directly names {named}, but the union has no abstract; full text is required before eligibility can be decided."


def blank_record(columns: list[str], values: dict[str, str]) -> dict[str, str]:
    row = {column: "not reported" for column in columns}
    row.update(values)
    assert set(row) == set(columns)
    return row


def master_ready_records(columns: list[str]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    records["TA-1078"] = blank_record(columns, {
        "Paper ID": "gao_2024_collabcoder",
        "Full citation": "Gao, J., Guo, Y., Lim, G., Zhang, T., Zhang, Z., Li, T. J.-J., & Perrault, S. T. (2024). CollabCoder: A Lower-barrier, Rigorous Workflow for Inductive Collaborative Qualitative Analysis with Large Language Models. Proceedings of the 2024 CHI Conference on Human Factors in Computing Systems, Article 11, 1–29. https://doi.org/10.1145/3613904.3642002",
        "Title": "CollabCoder: A Lower-barrier, Rigorous Workflow for Inductive Collaborative Qualitative Analysis with Large Language Models",
        "Authors": "Jie Gao; Yuchen Guo; Gionnieve Lim; Tianqin Zhang; Zheng Zhang; Toby Jia-Jun Li; Simon Tangi Perrault",
        "Year": "2024",
        "Venue": "Proceedings of the 2024 CHI Conference on Human Factors in Computing Systems (CHI '24)",
        "Publication type": "peer-reviewed conference paper",
        "Peer-reviewed status": "peer reviewed",
        "Publication history notes": "arXiv:2304.07366v1 (2023); inspected arXiv v4 dated 22 January 2024; official CHI 2024 version DOI 10.1145/3613904.3642002",
        "URL": "https://doi.org/10.1145/3613904.3642002",
        "DOI": "10.1145/3613904.3642002",
        "Citation count, source, and retrieval date": "not reported",
        "Core or adjacent classification": "core",
        "Relationship/dependence family": "CollabCoder/CoAIcoder collaborative-coding tool family; distinct from the later software-code-generation system with the same CollabCoder name",
        "Research objective": "Design and evaluate an LLM-assisted workflow that lowers the barrier to rigorous collaborative qualitative analysis while preserving independent coding, discussion, and codebook development.",
        "Claimed qualitative methodology": "collaborative qualitative analysis grounded in Grounded Theory and Thematic Analysis practices",
        "Actual operationalized methodology": "Three stages: independent open coding with optional suggestions, coder comparison/discussion with agreement displays and suggested decisions, then human refinement of GPT-proposed code groups.",
        "Inductive, deductive, or hybrid": "inductive",
        "Domain": "HCI tool evaluation using consumer book reviews",
        "Dataset name": "Amazon US Reviews, Books_v1_00 category (Business and History subsets)",
        "Public or restricted data": "public Hugging Face Amazon US Reviews dataset",
        "Number of documents": "30 reviews (15 in each of two subsets)",
        "Number of participants": "5 formative interview participants and 16 user-evaluation participants (8 pairs); overlap not reported",
        "Approximate corpus size": "30 reviews, each filtered to 400–700 characters",
        "Document length": "400–700 characters per review",
        "Language": "not reported",
        "Sensitive-data status": "book reviews are non-clinical; user-study recordings and interviews involved consent",
        "Model family": "OpenAI GPT; sentence-transformer semantic similarity",
        "Exact model/version": "gpt-3.5-turbo; exact snapshot not reported",
        "Prompting strategy": "Role prompt as a helpful qualitative-analysis assistant; stage-specific prompts for codes, decision suggestions, and code groups; full prompt examples in appendix; temperature 0.7.",
        "Fine-tuning or adaptation": "no model fine-tuning reported",
        "Single-agent or multi-agent": "single-model interactive assistant embedded in a two-human collaborative workflow",
        "Agent roles": "suggestion provider during open coding; mediator/facilitator during discussion; preliminary code-group generator",
        "Human role": "Two humans code independently, decide whether to request/use suggestions, discuss disagreements, make final code decisions, and revise/approve code groups.",
        "Unit of analysis": "sentence- or paragraph-level review segment",
        "Generated outputs": "candidate codes, relevant prior-code suggestions, candidate consensus decisions, and preliminary code groups/themes",
        "Evidence/provenance mechanism": "Code decisions retain links to raw text; users can hover to inspect originating data, store keyword supports/certainty, and compare each coder's codes before final decisions.",
        "Baselines": "Within-subject comparison with Atlas.ti Web; presentation order and materials counterbalanced with a Latin square.",
        "Number of runs or seeds": "not reported for GPT generation",
        "Automatic metrics": "sentence-transformer semantic similarity; Cohen's kappa; agreement rate using a similarity threshold above 0.8; suggestion-use proportions",
        "Human-evaluation design": "Within-subject remote study; eight participant pairs used CollabCoder and Atlas.ti Web on two datasets, then completed Likert questionnaires and semi-structured interviews; sessions lasted about 2–3 hours.",
        "Number and expertise of evaluators": "16 participants: 2 self-described experts, 3 intermediate, 4 beginners, and 7 with no qualitative-analysis experience",
        "Inter-rater reliability": "The system calculates Cohen's kappa and an embedding-threshold agreement rate; no independent reliability estimate for the researchers' thematic analysis of evaluation interviews is reported.",
        "Statistical analysis": "descriptive Likert responses, usage proportions, similarity/agreement displays, and thematic analysis; inferential statistical testing not reported",
        "Principal results": "Participants generally preferred the integrated workflow and reported that it aided independence, disagreement identification, discussion, and codebook formation; the paper also observed risks that time pressure and GPT groupings could dominate human discussion.",
        "Efficiency or cost results": "Study sessions lasted about 2–3 hours and participants described reduced cognitive burden; controlled task-time savings and API cost were not reported.",
        "Ethics and privacy treatment": "Local IRB approval, participant consent for recordings, and compensation of about US$22.30 are reported.",
        "Reproducibility resources": "Prompt templates and output examples are included in the appendix; public dataset link and project page are reported; a fixed GPT model snapshot and repeated-generation seeds are not reported.",
        "Author-reported limitations": "Idealized semantically independent units, two-person teams, and single-semantics units; no automatic segmentation; the process by which users select/edit suggestions and optimal autonomy/reliance balance were not studied.",
        "Additional validity concerns": "Small artificial review subsets and mostly inexperienced participants limit transfer to real, sensitive, longitudinal qualitative projects; consensus and semantic similarity do not establish interpretive validity; stochastic stability was not tested.",
        "Relationship to prior papers": "Builds on CoAIcoder and earlier collaborative-coding/CAQDAS work; provides a fuller three-stage workflow rather than an independent study of automated end-to-end thematic validity.",
        "Relevance to the proposed ARR project": "Strong human-workflow, provenance, and over-reliance comparator; motivates evaluating disagreement and independent human agency rather than agreement alone.",
    })

    records["TA-1230"] = blank_record(columns, {
        "Paper ID": "jiang_2021_supporting_serendipity",
        "Full citation": "Jiang, J. A., Wade, K., Fiesler, C., & Brubaker, J. R. (2021). Supporting Serendipity: Opportunities and Challenges for Human-AI Collaboration in Qualitative Analysis. Proceedings of the ACM on Human-Computer Interaction, 5(CSCW1), Article 94, 1–23. https://doi.org/10.1145/3449168",
        "Title": "Supporting Serendipity: Opportunities and Challenges for Human-AI Collaboration in Qualitative Analysis",
        "Authors": "Jialun Aaron Jiang; Kandrea Wade; Casey Fiesler; Jed R. Brubaker",
        "Year": "2021",
        "Venue": "Proceedings of the ACM on Human-Computer Interaction, CSCW1",
        "Publication type": "peer-reviewed journal/proceedings article",
        "Peer-reviewed status": "peer reviewed",
        "Publication history notes": "official version published April 2021; arXiv:2102.03702v1 dated 7 February 2021",
        "URL": "https://doi.org/10.1145/3449168",
        "DOI": "10.1145/3449168",
        "Citation count, source, and retrieval date": "not reported",
        "Core or adjacent classification": "core",
        "Relationship/dependence family": "Seminal empirical needs/delegability study for human–AI qualitative analysis; no implemented LLM system",
        "Research objective": "Characterize qualitative researchers' work practices and determine where AI assistance may or may not be appropriate while preserving agency, uncertainty, ambiguity, and serendipity.",
        "Claimed qualitative methodology": "qualitative inductive methods; thematic analysis of semi-structured interviews",
        "Actual operationalized methodology": "Seventeen semi-structured interviews were transcribed and anonymized; one author open-coded, a second discussed emerging groups, two further iterative coding rounds formed categories, and all authors iteratively reviewed grounded theme memos.",
        "Inductive, deductive, or hybrid": "inductive",
        "Domain": "CSCW/HCI qualitative-research practice",
        "Dataset name": "semi-structured interviews with qualitative researchers",
        "Public or restricted data": "restricted human-participant interview transcripts",
        "Number of documents": "17 interview transcripts",
        "Number of participants": "17 qualitative researchers",
        "Approximate corpus size": "17 interviews lasting 20–70 minutes each",
        "Document length": "20–70 minute interviews",
        "Language": "not reported",
        "Sensitive-data status": "human-participant data; transcripts anonymized and individual demographics not fully linked to protect identifiability",
        "Model family": "no computational model implemented or evaluated",
        "Exact model/version": "not applicable",
        "Prompting strategy": "not applicable",
        "Fine-tuning or adaptation": "not applicable",
        "Single-agent or multi-agent": "not applicable; empirical human-research study",
        "Agent roles": "The paper theorizes an assistive AI that surfaces ambiguity or relationships on demand rather than acting as an answer provider.",
        "Human role": "Human qualitative researcher remains primary analyst and retains full agency; participants opposed delegating interpretation to AI.",
        "Unit of analysis": "interview transcript segments and researcher-reported practices",
        "Generated outputs": "five themes/findings and design implications for human–AI qualitative-analysis tools",
        "Evidence/provenance mechanism": "Descriptive theme memos grounded categories in transcripts, and the paper reports anonymized participant quotations for claims.",
        "Baselines": "not reported",
        "Number of runs or seeds": "not applicable",
        "Automatic metrics": "not reported",
        "Human-evaluation design": "Exploratory semi-structured interview study rather than evaluation of a working AI system.",
        "Number and expertise of evaluators": "17 active qualitative researchers from Information Science, Anthropology, HCI, Communication, Linguistics, and Journalism; most were junior scholars.",
        "Inter-rater reliability": "not reported; the authors explicitly discuss why consensus and IRR may be methodologically nuanced",
        "Statistical analysis": "not reported; qualitative thematic analysis only",
        "Principal results": "Researchers wanted help managing and seeing relationships in data but valued ambiguity, doubt, agency, and serendipity; the authors argue AI should scaffold reflection and collaboration rather than arbitrate codes or remove uncertainty.",
        "Efficiency or cost results": "not evaluated",
        "Ethics and privacy treatment": "Institutional IRB approval, anonymization, demographic non-linkage for identifiability, and US$30 participant compensation are reported.",
        "Reproducibility resources": "Interview protocol content is summarized; transcripts and a public data/code package are not reported.",
        "Author-reported limitations": "Most participants were junior; reported practices were predominantly individual and text-based; no specific model, algorithm, or deployed system was evaluated.",
        "Additional validity concerns": "Snowball/convenience recruitment centered on one institution and CSCW community limits transfer; first-author-led coding may shape themes, and independent coding/reliability was not reported.",
        "Relationship to prior papers": "Predates the reviewed LLM systems and provides empirical requirements against which later claims of human-in-the-loop collaboration can be judged.",
        "Relevance to the proposed ARR project": "Foundational evidence that ambiguity and disagreement are analytic resources; supports an ARR design that preserves human agency and evaluates whether automation suppresses minority or unexpected interpretations.",
    })

    records["FC-prompting-panacea"] = blank_record(columns, {
        "Paper ID": "ganesh_2024_prompting_panacea",
        "Full citation": "Ganesh, A., Chandler, C., D'Mello, S., Palmer, M., & von der Wense, K. (2024). Prompting as Panacea? A Case Study of In-Context Learning Performance for Qualitative Coding of Classroom Dialog. Proceedings of the 17th International Conference on Educational Data Mining, 835–843. https://doi.org/10.5281/zenodo.12729966",
        "Title": "Prompting as Panacea? A Case Study of In-Context Learning Performance for Qualitative Coding of Classroom Dialog",
        "Authors": "Ananya Ganesh; Chelsea Chandler; Sidney D'Mello; Martha Palmer; Katharina von der Wense",
        "Year": "2024",
        "Venue": "Proceedings of the 17th International Conference on Educational Data Mining (EDM 2024)",
        "Publication type": "peer-reviewed conference paper/poster",
        "Peer-reviewed status": "peer reviewed",
        "Publication history notes": "Official EDM proceedings paper, pages 835–843; the PDF's footer abbreviates the final author as K. Kann while the title page and official proceedings page use Katharina von der Wense.",
        "URL": "https://www.educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.95/",
        "DOI": "10.5281/zenodo.12729966",
        "Citation count, source, and retrieval date": "not reported",
        "Core or adjacent classification": "core",
        "Relationship/dependence family": "Backward/forward-chain comparator from Dai 2023; distinct educational-dialog classification benchmark",
        "Research objective": "Compare off-the-shelf LLM in-context learning with task-specific fine-tuning for theoretically motivated qualitative coding of classroom dialogue under different data regimes.",
        "Claimed qualitative methodology": "automated qualitative coding framed as supervised text classification",
        "Actual operationalized methodology": "Nine fixed-label utterance-classification tasks across five educational-dialog datasets; zero/few-shot GPT-4 and Mistral are compared with full/few-shot RoBERTa and Mistral-embedding classifiers.",
        "Inductive, deductive, or hybrid": "deductive fixed-code assignment",
        "Domain": "education; K–12 and tutoring dialogue",
        "Dataset name": "CPS Minecraft; CPS Sensor Immersion; TalkMoves; NCTE; CIMA",
        "Public or restricted data": "mixture; datasets are open or described in prior work, while Sensor Immersion is access-restricted and was not sent to GPT-4",
        "Number of documents": "five datasets and nine classification tasks",
        "Number of participants": "not reported for the reused source datasets",
        "Approximate corpus size": "datasets range from about 2,500 to 50,000 utterance examples",
        "Document length": "utterance-level; preceding teacher utterance is context for TalkMoves",
        "Language": "not reported",
        "Sensitive-data status": "classroom/tutoring dialogue; Sensor Immersion was withheld from the proprietary GPT-4 API because of privacy/access restrictions",
        "Model family": "GPT-4; Mistral-7B; RoBERTa-base; logistic regression on Mistral embeddings",
        "Exact model/version": "GPT-4 snapshot not reported; Mistral-7B; RoBERTa-base (125M)",
        "Prompting strategy": "Zero-shot and 5-shot GPT-4; zero-, 5-, and 20-shot Mistral; role/scenario prompts and fixed output labels; temperature 0; prompt templates in appendix.",
        "Fine-tuning or adaptation": "RoBERTa full-data and 5/20-shot fine-tuning; logistic regression on averaged normalized Mistral hidden-state embeddings; no GPT-4 fine-tuning.",
        "Single-agent or multi-agent": "single-model classifiers",
        "Agent roles": "not applicable",
        "Human role": "Humans created the original labeled datasets/codebooks; no human is in the inference loop or new qualitative adjudication study.",
        "Unit of analysis": "student utterance, sometimes with preceding teacher utterance as context",
        "Generated outputs": "one fixed qualitative-code/class label per task instance",
        "Evidence/provenance mechanism": "not reported beyond fixed labels and prompts; no source-to-interpretation rationale is evaluated",
        "Baselines": "label-distribution random baseline; full-data and few-shot RoBERTa; Mistral-embedding logistic regression; zero/few-shot GPT-4 and Mistral cross-comparisons",
        "Number of runs or seeds": "three randomly sampled demonstration sets for each k-shot condition; repeated stochastic inference beyond those samples not reported",
        "Automatic metrics": "positive-class F1 for binary tasks; macro-F1 for multiclass tasks",
        "Human-evaluation design": "no new human evaluation; performance is measured against existing annotated labels",
        "Number and expertise of evaluators": "not reported for original annotations in this paper",
        "Inter-rater reliability": "not reported",
        "Statistical analysis": "descriptive F1 comparisons; uncertainty intervals and inferential tests not reported",
        "Principal results": "Full-data fine-tuned RoBERTa performed best across tasks; GPT-4 beat chance on most evaluated zero-shot tasks but was task-sensitive, and few-shot prompting sometimes reduced performance; task-specific fine-tuning remained valuable.",
        "Efficiency or cost results": "API cost constrained GPT-4 to 5-shot experiments; aggregate monetary cost and wall-clock time were not reported.",
        "Ethics and privacy treatment": "The paper identifies proprietary-API privacy/storage risks and does not run GPT-4 on restricted Sensor Immersion transcripts; broader consent/governance for reused datasets is not reported.",
        "Reproducibility resources": "Full prompt templates and label-distribution figures are in the appendix; datasets/models are named; source code and exact GPT-4 snapshot are not reported.",
        "Author-reported limitations": "Prompt choice and demonstration selection can change results; GPT-4 cost restricted exploration; possible pretraining exposure to public benchmarks; Sensor Immersion could not be evaluated with GPT-4; label imbalance was out of scope.",
        "Additional validity concerns": "Fixed labels turn qualitative coding into single-answer classification; F1 does not test interpretive plurality, rationale grounding, minority-case preservation, or whether shortcuts such as cue words drive apparent success.",
        "Relationship to prior papers": "Contrasts LLM prompting with smaller task-specific models and cites Dai et al. as a collaborative/thematic alternative.",
        "Relevance to the proposed ARR project": "High-value baseline showing that controlled supervised models can outperform general LLM prompting and that prompt sensitivity, privacy exclusions, and fixed-label construct validity must be audited.",
    })
    overlap = set(records) & set(inclusion_records(columns))
    assert not overlap, f"Duplicate companion extraction keys: {sorted(overlap)}"
    records.update(inclusion_records(columns))
    return records


def quality_scores() -> dict[str, dict]:
    caution = "The total is a compact audit aid, not a ranking; interpret every dimension against the paper's claim and study design."
    raw = {
        "TA-1078": {
            "Paper ID": "gao_2024_collabcoder", "Title": "CollabCoder: A Lower-barrier, Rigorous Workflow for Inductive Collaborative Qualitative Analysis with Large Language Models",
            "scores": [
                (2, "The paper explicitly grounds the three-stage workflow in collaborative qualitative analysis, Grounded Theory, and thematic-analysis practices."),
                (1, "Two 15-review subsets support a controlled usability comparison but are small, artificial, and unlike real sensitive research corpora."),
                (2, "The system stages, gpt-3.5-turbo role, temperature, prompts, preprocessing, similarity calculations, and interfaces are described in detail."),
                (1, "Atlas.ti Web is a useful independent system comparator, but the design does not isolate every LLM contribution from workflow/interface differences."),
                (2, "A counterbalanced within-subject study with 16 participants in eight pairs, questionnaires, observations, and interviews directly evaluates the workflow."),
                (1, "Cohen's kappa and semantic-similarity agreement are reported, but the 0.8 threshold and their relation to interpretive quality are not validated."),
                (1, "Independent coding and discussion preserve some plurality, yet the workflow still emphasizes consensus and participants reported possible GPT dominance."),
                (2, "Users can trace codes and decisions to raw data, record keyword supports/certainty, and inspect both coders' contributions."),
                (0, "No repeated GPT runs, seeds, or robustness analysis is reported."),
                (2, "The study reports IRB approval, consent for recording, participant compensation, and a non-sensitive public task corpus."),
                (1, "Prompt templates, public data, model name, and a project page are available, but a fixed model snapshot and complete reproducible run package are not reported."),
                (2, "Conclusions are bounded to workflow support and usability, and the authors explicitly discuss idealized tasks, reliance, and GPT-dominance risks."),
            ],
        },
        "TA-1230": {
            "Paper ID": "jiang_2021_supporting_serendipity", "Title": "Supporting Serendipity: Opportunities and Challenges for Human-AI Collaboration in Qualitative Analysis",
            "scores": [
                (2, "The interview, open-coding, iterative category formation, grounded memo, and all-author review process is clearly described."),
                (1, "Seventeen active qualitative researchers provide relevant evidence, but the sample is institution/CSCW-centered and mostly junior."),
                (0, "No computational system, model, or operational AI workflow is implemented."),
                (0, "No system baseline or independent computational comparator is evaluated."),
                (1, "The 17-participant interview study is appropriate for formative requirements, but it does not evaluate actual use of an AI tool."),
                (0, "No automatic metric is proposed or validated."),
                (2, "The central analysis treats ambiguity, disagreement, doubt, and serendipity as valuable rather than errors to eliminate."),
                (2, "Theme memos and reported participant quotations visibly ground the interpretive claims in source interviews."),
                (0, "No repeated analysis, independent recoding, or stability assessment is reported."),
                (2, "IRB approval, anonymization, demographic non-linkage, and participant compensation are reported."),
                (0, "Interview transcripts, analysis materials, and code are not reported as openly available."),
                (2, "The authors limit claims to formative implications and explicitly state that no model, algorithm, or deployed system was evaluated."),
            ],
        },
        "FC-prompting-panacea": {
            "Paper ID": "ganesh_2024_prompting_panacea", "Title": "Prompting as Panacea? A Case Study of In-Context Learning Performance for Qualitative Coding of Classroom Dialog",
            "scores": [
                (1, "The paper clearly defines fixed-label educational coding tasks but operationalizes qualitative coding as classification rather than an interpretive methodology."),
                (2, "Five established classroom/tutoring datasets spanning nine tasks and roughly 2,500–50,000 examples provide a strong task-specific test bed."),
                (2, "Models, prompt regimes, temperature, fine-tuning procedures, classifiers, hardware, and full prompt templates are reported."),
                (2, "Random, RoBERTa, Mistral-embedding, zero-shot, few-shot, and full-data comparisons provide strong independent baselines."),
                (1, "Existing human labels anchor performance, but no new expert assessment of model rationales or interpretive validity is conducted."),
                (1, "F1 is suitable for fixed-label classification but is not validated as a measure of qualitative interpretation and lacks uncertainty estimates."),
                (0, "Each instance is treated as having a correct fixed label; alternative interpretations are not evaluated."),
                (0, "The paper evaluates labels rather than source-grounded explanations or traceable qualitative evidence."),
                (1, "Three demonstration samples test some few-shot variability, but complete repeated-run and prompt-robustness testing is absent."),
                (1, "The paper identifies API privacy/storage risk and withholds restricted data from GPT-4, but broader dataset consent/governance reporting is limited."),
                (1, "Prompts, datasets, and model families are documented, while source code and the exact GPT-4 snapshot are not reported."),
                (2, "The cautious conclusion that fine-tuning remains valuable is supported across tasks, and prompt, cost, privacy, and contamination limits are acknowledged."),
            ],
        },
    }
    dimensions = json.loads(MASTER.read_text())["quality_dimensions"]
    names = [d["dimension"] if isinstance(d, dict) else d for d in dimensions]
    out = {}
    for key, item in raw.items():
        assert len(item["scores"]) == len(names) == 12
        score_map = {name: {"score": score, "rationale": rationale} for name, (score, rationale) in zip(names, item["scores"])}
        out[key] = {
            "Paper ID": item["Paper ID"],
            "Title": item["Title"],
            "Core or adjacent classification": "core",
            "Dimension scores": score_map,
            "Total": sum(value["score"] for value in score_map.values()),
            "Interpretation caution": caution,
        }
    additions = inclusion_quality_scores(names)
    overlap = set(out) & set(additions)
    assert not overlap, f"Duplicate quality-score keys: {sorted(overlap)}"
    out.update(additions)
    return out


FORWARD_METADATA = {
    "Prompting as Panacea? A Case Study of In-Context Learning Performance for Qualitative Coding of Classroom Dialog": {
        "resolved_year": 2024,
        "official_url": "https://www.educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.95/",
        "official_identifier": "10.5281/zenodo.12729966",
        "abstract": "The paper compares LLM in-context learning with task-specific fine-tuning for qualitative coding of classroom dialogue across five datasets and finds that task-specific fine-tuning strongly outperforms in-context learning.",
        "decision": "include_core_after_full_text",
        "reason": "The official nine-page EDM proceedings paper was retrieved and inspected; it directly evaluates LLM and supervised baselines for qualitative coding.",
        "full_text_status": "retrieved and inspected",
        "full_text_path": "research/fulltext/screening_2020_2024/FC_prompting_panacea_edm2024.txt",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "official EDM 2024 proceedings record and proceedings PDF",
                "outcome": "complete nine-page paper retrieved and converted to local text",
            }
        ],
    },
    "From Words to Themes: AI-Powered Qualitative Data Coding and Analysis": {
        "resolved_year": 2024,
        "official_url": "https://link.springer.com/chapter/10.1007/978-3-031-65735-1_19",
        "official_identifier": "10.1007/978-3-031-65735-1_19",
        "abstract": "The official Springer abstract describes generative and lexico-semantic bottom-up interview coding with ChatGPT/NLP to automate codebook construction.",
        "decision": "not_retrieved_after_attempts_core",
        "reason": "Official metadata and abstract establish direct scope, but Springer exposed only a subscription preview; methodological claims were not extracted from complete full text.",
        "full_text_status": "sought but not retrieved",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "official Springer chapter landing page and citation_pdf_url",
                "outcome": "landing page/abstract available; PDF route returned an HTML subscription preview rather than complete PDF",
            }
        ],
    },
    "Computer-assisted qualitative visual analysis: Automating thematic analysis of images": {
        "resolved_year": "2022 in Crossref issued field; record created 2024 and GPT-4 content makes the year metadata internally inconsistent",
        "official_url": "https://doi.org/10.1386/iscc_00058_1",
        "official_identifier": "10.1386/iscc_00058_1",
        "abstract": "Crossref's publisher-deposited abstract describes GPT-4 Turbo and Google Cloud Vision applied to 1,000 advertisements with human validation of clusters and themes.",
        "decision": "not_retrieved_after_attempts_adjacent",
        "reason": "The method directly automates qualitative visual rather than textual analysis, but the publisher PDF returned HTTP 403 and complete full text was not inspected.",
        "full_text_status": "sought but not retrieved; publisher crawler PDF returned HTTP 403",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "DOI resolution and official Intellect publisher record",
                "outcome": "publisher route returned HTTP 403; Crossref publisher-deposited abstract remained available",
            }
        ],
    },
    "Use large language models (LLMs) tools for supporting qualitative research: A phenomenological study of Chinese clinical researchers’ experiences and perceptions (Preprint)": {
        "resolved_year": 2024,
        "official_url": "https://doi.org/10.2196/preprints.64392",
        "official_identifier": "10.2196/preprints.64392",
        "abstract": "The Crossref abstract reports interviews with ten Chinese clinical researchers about their experiences using LLM tools and Colaizzi thematic analysis of those interviews.",
        "decision": "exclude_title_abstract",
        "reason": "LLM use is the phenomenon studied and human phenomenological analysis is the method; the paper does not present or evaluate a computational qualitative-analysis contribution.",
        "full_text_status": "not required for exclusion; official preprint identity and full structured abstract verified",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "DOI/Crossref and official JMIR preprint record",
                "outcome": "official identity and structured abstract verified; full text not required for scope exclusion",
            }
        ],
    },
    "Future Directions in Qualitative Research": {
        "resolved_year": 2024,
        "official_url": "https://link.springer.com/chapter/10.1007/978-3-031-60533-8_14",
        "official_identifier": "10.1007/978-3-031-60533-8_14",
        "abstract": "Available bibliographic metadata describes a book chapter discussing opportunities, risks, and limitations of LLMs in qualitative research and ChatGPT for analysis/theory formulation.",
        "decision": "not_retrieved_after_attempts_adjacent",
        "reason": "The chapter is potentially useful methodological context, but complete full text was not available through the official Springer record and no system evaluation is established.",
        "full_text_status": "sought but not retrieved",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "official Springer chapter landing page and citation_pdf_url",
                "outcome": "bibliographic page/preview available; PDF route returned an HTML subscription preview rather than complete PDF",
            }
        ],
    },
    "LLMs and Coding in Qualitative Research: Advancements and Opportunities for Social Verbatim as an Integral Qualitative Tool": {
        "resolved_year": 2026,
        "official_url": "https://doi.org/10.54790/rccs.176",
        "official_identifier": "10.54790/rccs.176",
        "abstract": "The official journal PDF identifies this as a 2026 debate article on LLMs, qualitative coding, and the Social Verbatim tool.",
        "decision": "resolved_outside_year_batch_handoff_2026",
        "reason": "The previously undated citation-index record resolves to a 2026 article, so it is preserved with parentage and handed to the separately assigned 2026 screen rather than silently treated as <=2024.",
        "full_text_status": "official DOI and journal metadata located; detailed assessment assigned to 2026 track",
        "retrieval_attempts": [
            {
                "attempt_date": "2026-08-24",
                "route": "DOI resolution and official journal record",
                "outcome": "publication year resolved to 2026; publisher route returned HTTP 403 during confirmation, so no <=2024 extraction was attempted",
            }
        ],
    },
}


def run() -> dict:
    flow = json.loads(FLOW.read_text())
    union = json.loads(UNION.read_text())
    master = json.loads(MASTER.read_text())
    chain = json.loads(CHAIN.read_text())
    retrieval_log = json.loads(RETRIEVAL_LOG.read_text()) if RETRIEVAL_LOG.exists() else {"records": []}
    retrieval_by_id = {record["screen_id"]: record for record in retrieval_log["records"]}
    columns = master["metadata"]["extraction_columns"]
    ready = master_ready_records(columns)
    qualities = quality_scores()
    by_source = {record["source_id"]: record for record in union["records"]}
    assessed_ids = {
        sid
        for report in flow["full_text_stage"]["assessed_reports"]
        for sid in report.get("linked_screen_ids", [])
    }
    scope = [
        record for record in flow["title_abstract_screening"]["records"]
        if in_year_scope(record.get("year"))
        and (
            record["decision"] == "uncertain"
            or (record["decision"] == "included" and record["screen_id"] not in assessed_ids)
        )
    ]
    assert len(scope) == 239, f"Expected 239 database records, found {len(scope)}"
    rows = []
    for screen in scope:
        source = by_source.get(screen["source_id"])
        assert source is not None, screen["screen_id"]
        abstract = clean_markup(source.get("abstract", ""))
        sid = screen["screen_id"]
        if sid in VERSION_FAMILIES:
            decision, reason = VERSION_FAMILIES[sid]
            reason_code = "VERSION_OR_PUBLICATION_FAMILY"
        elif sid in FULL_TEXT_TERMINAL:
            decision, reason_code, reason = FULL_TEXT_TERMINAL[sid]
        elif sid in ready:
            classification = ready[sid]["Core or adjacent classification"]
            decision = f"include_{classification}_after_full_text"
            reason_code = f"FULL_TEXT_INSPECTED_{classification.upper()}"
            if classification == "core":
                reason = "Complete official/preprint full text was inspected and a 52-field extraction plus 12-dimension quality assessment is attached."
            else:
                reason = "Complete official/preprint full text was inspected and a 52-field adjacent-evidence extraction is attached; it is not scored as a core effectiveness study."
        elif sid in POTENTIAL_CORE:
            decision = "potential_core_full_text_required"
            reason_code = "DIRECT_COMPUTATIONAL_QDA_SCOPE"
            reason = routing_reason(screen["title"], abstract)
        elif sid in POTENTIAL_ADJACENT:
            decision = "potential_adjacent_full_text_required"
            reason_code = "DIRECT_ADJACENT_METHOD_OR_VALIDITY_SCOPE"
            reason = POTENTIAL_ADJACENT[sid]
        else:
            decision = "exclude_title_abstract"
            reason_code, reason = excluded_reason(screen["title"], abstract)

        retrieval_record = retrieval_by_id.get(sid)
        local_path = LOCAL_FULL_TEXT.get(sid)
        if not local_path and retrieval_record and retrieval_record.get("local_text_path") != "not reported":
            local_path = retrieval_record["local_text_path"]
        retrieval_attempts = retrieval_record.get("attempts", []) if retrieval_record else []
        if (
            decision.startswith("potential_")
            and retrieval_record
            and retrieval_record.get("terminal_retrieval_outcome") == "not_retrieved_after_attempts"
        ):
            prior_reason = reason
            decision = "not_retrieved_after_attempts"
            reason_code = "FULL_TEXT_NOT_RETRIEVED"
            attempted_routes = sorted({attempt.get("attempt_type", "unspecified route") for attempt in retrieval_attempts})
            reason = (
                f"The record remained plausibly eligible at title/abstract screening, but full text was not retrieved after "
                f"{len(retrieval_attempts)} documented attempts ({'; '.join(attempted_routes)}). It is not included. "
                f"Routing basis: {prior_reason}"
            )
        if sid in ready:
            retrieval = "retrieved, inspected, and extracted"
        elif local_path and sid in FULL_TEXT_TERMINAL:
            retrieval = "complete full text retrieved and inspected; terminal eligibility decision recorded"
        elif local_path:
            retrieval = "complete full text retrieved locally; detailed 52-field extraction is pending in the current checkpoint"
        elif decision == "not_retrieved_after_attempts":
            retrieval = f"not retrieved after {len(retrieval_attempts)} documented attempts; see retrieval_attempts"
        elif "version" in decision or "handoff" in decision:
            retrieval = "resolved through publication/version-family evidence; see decision reason"
        else:
            retrieval = "full text not required for title/abstract exclusion"
        rows.append({
            "screen_id": sid,
            "source": screen["source"],
            "sources": screen["sources"],
            "source_id": screen["source_id"],
            "title": screen["title"],
            "year_as_indexed": screen.get("year") if screen.get("year") is not None else "not reported",
            "doi": screen.get("doi") or "not reported",
            "url": screen.get("url") or "not reported",
            "prior_deterministic_decision": screen["decision"],
            "prior_reason_code": screen["reason_code"],
            "union_abstract": abstract or "not reported",
            "abstract_available": bool(abstract),
            "second_pass_decision": decision,
            "second_pass_reason_code": reason_code,
            "specific_reason": reason,
            "evidence_basis": "title and actual union abstract" if abstract else "title only; union abstract not reported",
            "full_text_retrieval_outcome": retrieval,
            "retrieval_attempts": retrieval_attempts,
            "local_full_text_path": local_path or "not reported",
            "master_inclusion_status": "master-ready companion extraction; not merged in this concurrent-safe pass" if sid in ready else "not added to master",
            "master_ready_record": ready.get(sid),
            "quality_score": qualities.get(sid),
        })

    union_dois = {norm(r.get("doi", "")) for r in union["records"] if r.get("doi")}
    union_titles = {norm(r["title"]) for r in union["records"]}
    forward_scope = []
    for item in chain["reviewer_screening_decisions"]["decisions"]:
        if not in_year_scope(item.get("year")):
            continue
        doi_match = item.get("doi") not in (None, "not reported") and norm(item["doi"]) in union_dois
        if doi_match or norm(item["title"]) in union_titles:
            continue
        metadata = FORWARD_METADATA.get(item["title"])
        assert metadata is not None, item["title"]
        key = "FC-prompting-panacea" if item["title"].startswith("Prompting as Panacea") else None
        forward_scope.append({
            "title": item["title"],
            "year_as_indexed": item["year"],
            "resolved_year": metadata["resolved_year"],
            "doi_as_indexed": item["doi"],
            "official_identifier": metadata["official_identifier"],
            "official_url": metadata["official_url"],
            "parent_seed_ids": item["parent_seed_ids"],
            "citation_index_sources": item["citation_index_sources"],
            "index_title_screen_outcome": item["title_screen_outcome"],
            "abstract_or_scope_evidence": metadata["abstract"],
            "second_pass_decision": metadata["decision"],
            "specific_reason": metadata["reason"],
            "full_text_retrieval_outcome": metadata["full_text_status"],
            "retrieval_attempts": metadata["retrieval_attempts"],
            "local_full_text_path": metadata.get("full_text_path", "not reported"),
            "master_inclusion_status": "master-ready companion extraction; not merged in this concurrent-safe pass" if key else "not added to master",
            "master_ready_record": ready.get(key) if key else None,
            "quality_score": qualities.get(key) if key else None,
        })
    assert len(forward_scope) == 6, f"Expected 6 forward-only records, found {len(forward_scope)}"

    decision_counts = dict(sorted(Counter(r["second_pass_decision"] for r in rows).items()))
    forward_counts = dict(sorted(Counter(r["second_pass_decision"] for r in forward_scope).items()))
    initial_advance_ids = (POTENTIAL_CORE | set(POTENTIAL_ADJACENT)) - PRIOR_READY_IDS
    initial_advance_rows = [record for record in rows if record["screen_id"] in initial_advance_ids]
    initial_advance_counts = dict(sorted(Counter(r["second_pass_decision"] for r in initial_advance_rows).items()))
    assert len(initial_advance_rows) == len(initial_advance_ids) == 67, "Expected 67 initially advanced database records"
    assert not any(r["second_pass_decision"].startswith("potential_") for r in initial_advance_rows), "An initially advanced record lacks a terminal disposition"
    assert not any(r["second_pass_decision"].startswith("potential_") for r in rows), "Database full-text routing is not terminal"
    assert not any(r["second_pass_decision"].startswith("potential_") for r in forward_scope), "Forward-chain routing is not terminal"
    assert all(r["retrieval_attempts"] for r in rows if r["second_pass_decision"] == "not_retrieved_after_attempts"), "A database nonretrieval lacks documented attempts"
    assert all(r["retrieval_attempts"] for r in forward_scope if r["second_pass_decision"].startswith("not_retrieved_after_attempts")), "A forward-chain nonretrieval lacks documented attempts"
    assert all(set(record) == set(columns) for record in ready.values()), "Every evidence record must have exactly the 52 master fields"
    core_ready = {key for key, record in ready.items() if record["Core or adjacent classification"] == "core"}
    assert set(qualities) == core_ready, f"Core/quality mismatch: core-only={sorted(core_ready - set(qualities))}; score-only={sorted(set(qualities) - core_ready)}"
    quality_names = set(master["quality_dimensions"])
    for key, score in qualities.items():
        assert set(score["Dimension scores"]) == quality_names, f"Quality dimensions mismatch for {key}"
        assert all(item["score"] in (0, 1, 2) for item in score["Dimension scores"].values()), key
        assert score["Total"] == sum(item["score"] for item in score["Dimension scores"].values()), key
        assert score["Paper ID"] == ready[key]["Paper ID"], key
    evidence_titles = [norm(record["Title"]) for record in ready.values()]
    evidence_dois = [norm(record["DOI"]) for record in ready.values() if record["DOI"] != "not reported"]
    assert len(evidence_titles) == len(set(evidence_titles)), "Duplicate evidence title"
    assert len(evidence_dois) == len(set(evidence_dois)), "Duplicate evidence DOI"
    return {
        "metadata": {
            "title": "Second-pass title/abstract eligibility resolution for 2020–2024 and undated/nonstandard-year records",
            "generated_utc": utc_now(),
            "search_cutoff": "2026-08-24",
            "reviewer_count": 1,
            "database_scope_definition": "Every review_flow title/abstract record indexed 2020–2024 or with missing/non-integer year whose prior decision was uncertain, plus every included/high-priority record in that year scope not linked to an assessed full-text report.",
            "forward_scope_definition": "Every <=2024/undated focused forward-chain candidate in citation_chaining.json that did not exactly match the database union by normalized DOI/title.",
            "decision_semantics": "Every database record routed to full text now has a terminal disposition: included with an inspected extraction, excluded after inspection, resolved to a publication/version family, or not retrieved after documented attempts. Title/abstract exclusions remain distinct from full-text exclusions.",
            "review_limit": "One reviewer performed this pass. Explicit nonretrievals are not evidence-table inclusions and may be revisited if full text later becomes available.",
        },
        "counts": {
            "database_records_resolved": len(rows),
            "database_prior_uncertain": sum(r["prior_deterministic_decision"] == "uncertain" for r in rows),
            "database_prior_included_unlinked": sum(r["prior_deterministic_decision"] == "included" for r in rows),
            "database_abstracts_available": sum(r["abstract_available"] for r in rows),
            "database_decisions": decision_counts,
            "initial_database_full_text_advances_terminalized": len(initial_advance_rows),
            "initial_database_full_text_advance_dispositions": initial_advance_counts,
            "forward_only_records_resolved": len(forward_scope),
            "forward_only_decisions": forward_counts,
            "master_ready_evidence_records": len(ready),
            "master_ready_core_extractions": sum(record["Core or adjacent classification"] == "core" for record in ready.values()),
            "master_ready_adjacent_extractions": sum(record["Core or adjacent classification"] == "adjacent" for record in ready.values()),
            "quality_scores_attached": len(qualities),
        },
        "database_union_resolution": rows,
        "forward_chain_outside_union_resolution": forward_scope,
        "evidence_records": list(ready.values()),
        "quality_dimensions": master["quality_dimensions"],
        "quality_scores": list(qualities.values()),
        "limitations": [
            "All included evidence records are based on inspected complete text; title/abstract screening alone was never used for extraction.",
            "The union contains 38 scoped records without abstracts; no-abstract titles that plausibly met scope were routed to retrieval, and no extraction was made from title evidence alone.",
            "Records whose complete text could not be retrieved remain explicit nonretrievals and are not counted as included.",
            "Subscription and access failures prevented complete inspection of several forward-chain candidates.",
            "Publication-family links are reviewer judgments based on matching titles, abstracts, methods, and official publication histories and should remain visible in downstream deduplication.",
        ],
    }


if __name__ == "__main__":
    data = run()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(OUT)
    print(json.dumps(data["counts"], indent=2))
