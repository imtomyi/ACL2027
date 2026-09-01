import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const NR = "not reported";
const CUTOFF = "2026-08-24";

const core = JSON.parse(fs.readFileSync(path.join(ROOT, "research/core_systems.json"), "utf8"));
const evaluation = JSON.parse(fs.readFileSync(path.join(ROOT, "research/evaluation_methodology.json"), "utf8"));
const validity = JSON.parse(fs.readFileSync(path.join(ROOT, "research/validity_ethics.json"), "utf8"));
const dorfelExtraction = JSON.parse(fs.readFileSync(path.join(ROOT, "research/dorfel_2026_evidence.json"), "utf8"));
const citationChainAudit = JSON.parse(fs.readFileSync(path.join(ROOT, "research/citation_chaining.json"), "utf8"));
const citationChainIncluded = citationChainAudit.backward_chain_candidates.filter(
  candidate => candidate.eligibility_decision === "include_core" && candidate.master_ready_record && candidate.quality_score
);

const columns = [
  "Paper ID",
  "Full citation",
  "Title",
  "Authors",
  "Year",
  "Venue",
  "Publication type",
  "Peer-reviewed status",
  "Publication history notes",
  "URL",
  "DOI",
  "Citation count, source, and retrieval date",
  "Core or adjacent classification",
  "Relationship/dependence family",
  "Research objective",
  "Claimed qualitative methodology",
  "Actual operationalized methodology",
  "Inductive, deductive, or hybrid",
  "Domain",
  "Dataset name",
  "Public or restricted data",
  "Number of documents",
  "Number of participants",
  "Approximate corpus size",
  "Document length",
  "Language",
  "Sensitive-data status",
  "Model family",
  "Exact model/version",
  "Prompting strategy",
  "Fine-tuning or adaptation",
  "Single-agent or multi-agent",
  "Agent roles",
  "Human role",
  "Unit of analysis",
  "Generated outputs",
  "Evidence/provenance mechanism",
  "Baselines",
  "Number of runs or seeds",
  "Automatic metrics",
  "Human-evaluation design",
  "Number and expertise of evaluators",
  "Inter-rater reliability",
  "Statistical analysis",
  "Principal results",
  "Efficiency or cost results",
  "Ethics and privacy treatment",
  "Reproducibility resources",
  "Author-reported limitations",
  "Additional validity concerns",
  "Relationship to prior papers",
  "Relevance to the proposed ARR project"
];

function isMissing(value) {
  return value === undefined || value === null || value === "" ||
    (typeof value === "string" && ["not reported", "n/a", "na"].includes(value.trim().toLowerCase()));
}

function flatten(value) {
  if (isMissing(value)) return NR;
  if (Array.isArray(value)) {
    const parts = value.map(flatten).filter(v => v !== NR);
    return parts.length ? [...new Set(parts)].join("; ") : NR;
  }
  if (typeof value === "object") {
    const parts = Object.entries(value)
      .filter(([, v]) => !isMissing(v))
      .map(([k, v]) => `${k.replaceAll("_", " ")}: ${flatten(v)}`);
    return parts.length ? parts.join("; ") : NR;
  }
  return String(value).replace(/\s+/g, " ").trim() || NR;
}

function valuesFrom(sourceRecords, keys) {
  const values = [];
  for (const { record } of sourceRecords) {
    for (const key of keys) {
      if (!isMissing(record[key])) {
        const value = flatten(record[key]);
        if (value !== NR && !values.includes(value)) values.push(value);
      }
    }
  }
  return values;
}

function first(sourceRecords, keys) {
  return valuesFrom(sourceRecords, keys)[0] ?? NR;
}

function combine(sourceRecords, keys) {
  const values = valuesFrom(sourceRecords, keys);
  return values.length ? values.join(" | ") : NR;
}

function normalizeDoi(raw, record) {
  let doi = flatten(raw).toLowerCase().replace(/^https?:\/\/doi\.org\//, "");
  if (doi === NR) doi = "";
  if (!doi) {
    const url = flatten(record.url ?? record.official_url);
    const match = url.match(/arxiv\.org\/(?:abs|pdf)\/(\d+\.\d+)/i);
    if (match) doi = `10.48550/arxiv.${match[1]}`;
  }
  return doi || NR;
}

function canonicalKey(record) {
  const doi = normalizeDoi(record.doi, record);
  return doi !== NR ? `doi:${doi}` : `id:${record.id}`;
}

const latestStudies = [
  {
    id: "matveyenko_2026_muse",
    citation: "Matveyenko, Joseph; Liu, James; Parsons, John David; Brown, Ryan A.; Palimaru, Alina I.; Gupta, Vipul; Puri, Prateek. 2026. Development and Benchmarking of a Blended Human-AI Qualitative Research Assistant. ACL 2026 Industry Track, 1917–1932.",
    year: 2026,
    venue: "ACL 2026 Industry Track",
    status: "peer-reviewed conference industry-track paper",
    publication_type: "conference/proceedings paper",
    doi: "10.18653/v1/2026.acl-industry.131",
    url: "https://aclanthology.org/2026.acl-industry.131/",
    claimed_method: "blended human–AI qualitative research supporting inductive codebook generation and deductive code application",
    operationalized_method: "interactive multi-stage codebook induction plus single-code and multi-code excerpt classification; coding-reliability evaluation rather than full reflexive thematic analysis",
    tasks: ["codebook generation", "hierarchical parent-code generation", "code refinement", "single-code application", "multi-code distribution", "error auditing"],
    architecture: "interactive production system; progressive segment coding and LLM consolidation/refinement for codebooks; embedding/MMR support checks; LLM excerpt classifiers with user-editable definitions, inclusion/exclusion criteria, and feedback examples",
    models: ["gpt-4.1-2025-04-14-global", "o3-2025-04-16-global", "gpt-5-2025-08-07-us", "gpt-4o-2024-08-06-us", "Grok-3", "gpt-oss-120b", "DeepSeek V3/R1", "Llama Nemotron variants", "EmbeddingGemma", "all-MiniLM-L6-v2"],
    model_versions: "Exact identifiers are reported for the principal benchmarked models in Tables 2 and 6; some provider deployment suffixes are reported.",
    prompting: "approximately 80-word segments; code definition plus inclusion/exclusion criteria; 0/2/4 few-shot examples; binary versus 1–10 scoring; with/without short chain-of-thought; batch sizes 5/10/20; per-code confidence thresholds",
    fine_tuning: "no LLM weight fine-tuning reported; per-code threshold tuning and user feedback examples adapt code application",
    human_role: "researchers steer, edit, split/merge, define and test codebooks, supply feedback, and choose application mode; survey and design feedback from more than 100 qualitative researchers; two experienced qualitative researchers independently coded sampled errors",
    datasets: ["11 publicly available human-coded datasets spanning interviews, social media, survey responses, discussion, legal, scientific and sustainability text", "arXiv codebook-generation benchmark: 1,000 abstracts sampled from three parent categories, yielding 22–52-code reference codebooks", "12 well-specified codes used for LLM-versus-supervised-ML comparison"],
    chunking: "documents segmented into approximately 80-word excerpts for code application; codebook generation uses progressive segments and consolidation",
    metrics: ["Cohen kappa with 95% confidence intervals", "F1", "custom semantic-plus-structural codebook similarity with Hungarian matching", "latency", "input/output tokens", "qualitative error taxonomy"],
    runs_or_seeds: "supervised-ML baselines averaged over 20 iterations; other replicate counts/seeds not reported",
    baselines: ["BERTopic for codebook similarity", "TF-IDF, SBERT, and EmbeddingGemma with LogisticRegression/LinearSVC", "human coding"],
    results: ["Across 12 well-specified codes, the tuned GPT-4.1+o3+Grok-3 ensemble reached kappa .703 and its untuned version .660; tuned GPT-4.1 reached .693.", "Per-code threshold tuning raises observed agreement and therefore should not be read as held-out generalization.", "Multi-code application used roughly 45–55% of input tokens and 55–65% of time per excerpt compared with single-code application, but usually reduced kappa.", "Many sampled disagreements were attributed to under-specified codebooks or inconsistent human annotations."],
    efficiency: "Latency and token trade-offs are reported by application mode and batch size; Muse is deployed to more than 400 users across 600+ projects.",
    ethics: "Eleven public datasets were used for benchmarking; dedicated participant-data ethics and proprietary-API governance reporting are not reported in the inspected paper.",
    reproducibility: "Evaluation dataset: https://github.com/jdmatv/muse-eval-dataset; prompts and detailed benchmark tables are included in appendices.",
    limitations: "Codebook similarity remains an open measurement problem; results vary by code definition and dataset quality; code-tuned thresholds may be optimistic; interpretive codes had lower agreement; most exact run seeds were not reported.",
    validity_concerns: "The strongest kappa uses thresholds tuned separately for each code against human labels, and agreement with a human codebook does not establish interpretive validity or plurality.",
    domain: "multi-domain qualitative research"
  },
  {
    id: "katz_2026_gatos",
    citation: "Katz, Andrew; Coloyan Fleming, Gabriella; Main, Joyce B. 2026. Thematic Analysis with Open-Source Generative AI and Machine Learning: A New Method for Inductive Qualitative Codebook Development. Humanities and Social Sciences Communications, 13, 209.",
    year: 2026,
    venue: "Humanities and Social Sciences Communications",
    status: "peer-reviewed journal article",
    publication_type: "journal article",
    doi: "10.1057/s41599-026-06508-5",
    url: "https://www.nature.com/articles/s41599-026-06508-5",
    claimed_method: "GATOS workflow approximating selected thematic-analysis steps for inductive qualitative codebook development; explicitly not reflexive thematic analysis",
    operationalized_method: "LLM extraction of atomic summary points, embeddings and dimensionality reduction, clustering, RAG-assisted iterative code induction, redundant-code consolidation, and theme generation",
    tasks: ["information extraction", "embedding and clustering", "inductive code generation", "codebook redundancy reduction", "theme generation", "manual reference matching"],
    architecture: "single workflow combining open-weight generative models with embeddings, clustering and retrieval augmentation; no multi-agent deliberation",
    models: ["Mistral-small-22b-2409 for GATOS", "Llama-3.1-70B and Mistral-nemo-12b for synthetic-data generation"],
    model_versions: "Mistral-small-22b-2409; Llama-3.1-70B; Mistral-nemo-12b",
    prompting: "research-question-conditioned extraction; nearest-code RAG with typically k=2–4; code-creation/no-new-code reasoning; prompts supplied in online supplementary material; model temperature reported as 0 in the discussion",
    human_role: "researchers specify questions/criteria, inspect synthetic data, and manually judge theme/subtheme matches as good, partial, or none; number and independence of match raters not reported",
    datasets: ["synthetic teammate feedback: 854 responses, mean 194 words", "synthetic organizational ethical culture: 823 responses, mean 129 words", "synthetic return-to-work perspectives: 1,110 responses, mean 131 words"],
    chunking: "one short synthetic open-ended response as the original unit; atomic summary points clustered before code induction",
    metrics: ["manual good/partial/no-match judgments", "embedding cosine similarity", "code and theme counts", "code-creation rate"],
    results: ["GATOS produced 249 codes/89 themes, 246/75, and 314/110 across the three datasets.", "Teammate feedback recovered 54 of 60 subthemes as good and 6 as partial; ethical culture recovered 52 of 64 as good, 9 partial and 3 none; return-to-work recovered 60 of 63 as good and 3 partial.", "All eight top-level themes in each synthetic dataset had at least one good match."],
    baselines: "prior thematic-analysis workflows are compared conceptually; no human analysis of natural qualitative data is an experimental baseline",
    runs_or_seeds: "not reported",
    ethics: "No ethics approval or consent was obtained because all study data were synthetic; authors disclose the synthetic-data limitation.",
    reproducibility: "Synthetic data are stated to be available at https://github.com/andrewskatz; prompts are in the supplementary material.",
    limitations: "Validation uses synthetic LLM-generated data that may remain distributionally easy; near-redundant codes remain; abstraction level and scaling are unresolved; full interviews and natural qualitative data were not tested.",
    validity_concerns: "The generator–analyzer ecosystem may share distributional/model priors, and a single embedded reference-theme universe does not test interpretive plurality or minority-case preservation.",
    domain: "synthetic social-science open-ended responses"
  },
  {
    id: "liu_2026_agreement_not_quality",
    citation: "Liu, Alex; Esbenshade, Lief; Xiao, Michael; Tian, Victor; Zhang, Zachary; He, Kevin; Sun, Min. 2026. Agreement Is Not Quality: Blind Expert Verification of Human and LLM Qualitative Coding When Human Consensus Is Not Ground Truth. arXiv:2607.28890.",
    year: 2026,
    venue: "arXiv",
    status: "arXiv preprint; peer-reviewed venue not verified",
    publication_type: "preprint",
    doi: "10.48550/arXiv.2607.28890",
    url: "https://arxiv.org/abs/2607.28890",
    claimed_method: "source-symmetric evaluation of deductive qualitative coding without presuming human consensus is ground truth",
    operationalized_method: "five LLMs and three trained humans apply a 72-item hierarchical multi-label codebook; one independent domain expert blindly judges randomized pairwise code-set comparisons",
    tasks: ["deductive multi-label code assignment", "agreement analysis", "blind pairwise verification", "code-level division-of-labor classification"],
    architecture: "single-call deductive coding per message for each model; no agent workflow",
    models: ["Claude Opus 4.8", "Claude Haiku 4.5", "Gemini 3.5 Flash", "GPT-4o", "GPT-5.5"],
    model_versions: "full API strings and access dates are reported in Appendix C; focal model names are reported in the main text",
    prompting: "identical chain-of-thought structured prompt, complete 72-item codebook, JSON output, temperature zero/minimal thinking, no session memory, one message per API call",
    human_role: "three trained education-domain coders apply the complete codebook; one independent doctoral education/K-12 expert blindly verifies 855 pairwise comparisons",
    datasets: "2,560 educator messages from 500 K-12 educator–AI conversations, June 2025–June 2026; 2,494 messages after removal of 66 platform trigger phrases for LLM coding",
    chunking: "one educator message per independent API call",
    metrics: ["Jaccard", "directional hit rates", "exact match", "Cohen kappa", "binomial tests", "Bradley–Terry model", "bootstrap confidence intervals", "per-code endorsement", "position-bias test"],
    results: ["Mean human–LLM Jaccard was .30 versus human–human .52.", "Among 515 decisive human–LLM comparisons, the verifier preferred humans 51.5% and LLMs 48.5% (p=.537; 95% CI .470–.559).", "GPT-5.5 and Gemini Flash ranked above two of three human coders, while GPT-4o ranked below all human coders in the Bradley–Terry analysis.", "Four-model repeat runs yielded exact match 71.1%–99.2% and kappa .871–.995, showing stability can coexist with disagreement and bias."],
    baselines: "three trained human coders are evaluated symmetrically with the five focal LLMs; human–human and LLM–LLM comparisons are included",
    runs_or_seeds: "four focal models were run twice; pair order was randomized; random seed not reported",
    ethics: "PII removed; institutional IRB approval reported with institution redacted; enterprise APIs contractually excluded training on submitted data.",
    reproducibility: "full prompt/model configurations and the 72-item codebook are included in appendices; data/code availability statement not reported in the inspected preprint",
    limitations: "one codebook/dataset; one independent verifier; model rankings are time-specific; temperature-zero prompting only; verification covers a selected five-model subset.",
    validity_concerns: "The blind verifier is independent and source-blinded but singular, so normative judgments lack inter-verifier reliability and may not generalize beyond this domain expert.",
    domain: "K-12 educator use of an AI platform"
  },
  {
    id: "liu_2026_human_llm_inductive",
    citation: "Liu, Alex; Sun, Min; Esbenshade, Lief; Xiao, Michael; Tian, Victor; Zhang, Zachary; He, Kevin. 2026. Human-LLM Collaborative Inductive Coding for Conceptualizing K-12 Educator AI Use. arXiv:2607.28889.",
    year: 2026,
    venue: "arXiv",
    status: "arXiv preprint; peer-reviewed venue not verified",
    publication_type: "preprint",
    doi: "10.48550/arXiv.2607.28889",
    url: "https://arxiv.org/abs/2607.28889",
    claimed_method: "grounded-theory-descended open, axial, and selective coding adapted to human–LLM collaborative hierarchical codebook development; goal is an instrument, not theory generation",
    operationalized_method: "LLMs generate candidate themes/structured annotations across three phases while researchers read raw data, memo, decide every merge/category, and validate/extend the codebook on an independent human-coded sample",
    tasks: ["open coding", "axial category development", "selective closed-vocabulary coding", "hierarchical codebook construction", "human validation and refinement"],
    architecture: "three sequential human–LLM phases plus an independent human-coding phase; LLM treated as a labeling instrument, not an autonomous interpretive agent",
    models: ["claude-3-sonnet-20240229", "claude-3-5-haiku-20241022"],
    model_versions: "claude-3-sonnet-20240229; claude-3-5-haiku-20241022",
    prompting: "full open/axial/selective prompts archived; strict JSON; no session memory; individual overlapping three-message conversation windows; 'Other' plus rationale preserved inductive additions",
    human_role: "two researchers review and memo LLM outputs and retain conceptual authority; three trained education-domain coders calibrate and apply the resulting codebook to independent data, adding five missed codes",
    datasets: "45,000 educator/AI messages overall; 256 randomly selected trios for open-coding pilot; 9,352 trios axial; 11,539 trios selective; independent validation sample 2,560 messages from 500 conversations; no message/conversation overlap",
    chunking: "overlapping three-message windows (educator prompt, AI response, educator follow-up); independent message-level human validation",
    metrics: ["pairwise Jaccard at item/category/domain granularity", "code frequency", "semantic distinctiveness", "coverage gaps"],
    results: ["LLM-assisted phases yielded 67 items in 18 categories and six domains; human validation added five items, yielding 72 items in 19 categories/six domains.", "Three coders achieved mean pairwise Jaccard .52 on a 289-message overlap set; 2,560 validation messages received 5,237 code applications.", "Human coding surfaced culturally relevant pedagogy, language acquisition, proactive behavior support, collaborative professional work, and budgeting/resource-allocation codes absent from the LLM-assisted phases."],
    baselines: "independent trained-human application of the generated instrument on a temporally and conversationally separate validation sample",
    runs_or_seeds: "each trio submitted independently with no session memory; stochastic reruns and seeds not reported",
    ethics: "IRB approval reported with institution redacted; platform terms authorized deidentified research use; PII removed; enterprise APIs prohibited model training; potential student-writing excerpts are explicitly discussed.",
    reproducibility: "full codebook, prompts, and synthetic-data replication scripts: https://osf.io/ju59q/overview?view_only=96afb71945044b8794e113f9763cc74a; raw conversations restricted; coding results by request.",
    limitations: "one platform; commercial model outputs not strictly reproducible; human Jaccard leaves room for improvement; observed requests do not establish classroom implementation.",
    validity_concerns: "Human review is constitutive and well documented, but model-proposed labels may still anchor the analytic vocabulary and no counterfactual fully human codebook-development baseline is reported.",
    domain: "K-12 educator–AI interactions"
  },
  {
    id: "camporese_2026_security_comments",
    citation: "Camporese, Maria; Massacci, Fabio; Gong, Yuanjun. 2026. LLMs for Qualitative Data Analysis Fail on Security-specific Comments in Human Experiments. Proceedings of the 34th IEEE/ACM International Conference on Program Comprehension (ICPC 2026), 14 pages.",
    year: 2026,
    venue: "ICPC 2026",
    status: "peer-reviewed conference paper",
    publication_type: "conference/proceedings paper",
    doi: "10.1145/3794763.3798172",
    url: "https://doi.org/10.1145/3794763.3798172",
    claimed_method: "deductive thematic annotation of security-specific free-text comments",
    operationalized_method: "four LLMs replace one of four human annotators for nine sparse security codes under progressively richer codebook/example prompts",
    tasks: ["deductive code assignment", "prompt refinement", "human-replacement assessment", "failure-case analysis"],
    architecture: "single-model spreadsheet annotation; no agents",
    models: ["GPT-5", "Claude-4", "DeepSeek-V3.2", "Qwen3-Max"],
    model_versions: "provider chat/subscription versions at experiment time; exact snapshot strings not reported",
    prompting: "P1 task plus code names; P2 formal definitions/examples; P3 other-annotator few-shot labels; P3+ contrastive/conflicting examples and researcher clarifications; GPT-4o used only for prompt pilot",
    human_role: "four annotators each code one quarter and review another annotator; final reviewer-corrected labels form the comparison reference",
    datasets: "263 unpublished free-text comments from Computer Science master's students explaining vulnerability judgments on six code snippets; 13 codes annotated, nine evaluated",
    chunking: "one short participant comment with associated spreadsheet context",
    metrics: ["precision", "recall", "accuracy", "Cohen kappa/Heidke chance-corrected accuracy", "Wilcoxon paired tests", "Bonferroni correction", "token effort"],
    results: ["With the final prompt, average kappa was .26 GPT-5, .30 Claude-4, .53 DeepSeek-V3.2, and .61 Qwen3-Max.", "Prompt refinement improved kappa from approximately .37 to .42 after formal definitions, then plateaued; corrected prompt comparisons were not significant.", "Performance remained code-specific and inadequate to replace human security annotators."],
    baselines: "each replaced human annotator and reviewer-corrected human labels; four LLM families",
    runs_or_seeds: "model × prompt × code × annotator comparisons; stochastic reruns/seeds not reported",
    ethics: "The paper uses unpublished human-experiment comments supplied by the original researchers; ethics approval, consent, deidentification and vendor-data governance are not reported in the inspected paper.",
    reproducibility: "Data and implementation: https://zenodo.org/records/18742065.",
    limitations: "one security experiment, nine codes, CS master's-student comments rather than real developers, selected available models, spreadsheet-output failures excluded several models, and prompting choices are subjective.",
    validity_concerns: "Consensus/reviewer labels remain the assumed reference; sparse-code kappa is appropriate for agreement but cannot establish interpretive validity or detect shared human error.",
    domain: "software security and program comprehension"
  },
  {
    id: "liu_2026_policy_workflow",
    citation: "Liu, Yuhan; Zhou, Shuyao; Kaiser, Jakob; Colby, Ella; Okwara, Jennifer; Wang, Maggie; Rao, Varun Nagaraj; Monroy-Hernández, Andrés. 2026. How Can LLMs Support Policy Researchers? Evaluating an LLM-Assisted Workflow for Large-Scale Unstructured Data. arXiv:2604.04479v2.",
    year: 2026,
    venue: "arXiv",
    status: "arXiv preprint; peer-reviewed venue not verified",
    publication_type: "preprint",
    doi: "10.48550/arXiv.2604.04479",
    url: "https://arxiv.org/abs/2604.04479",
    claimed_method: "LLM-assisted thematic analysis for early-stage policy sensemaking, explicitly complementary to traditional policy research",
    operationalized_method: "QuaLLM-derived four-stage data collection, quote extraction, high-level classification/bottom-up subtheme generation, prevalence mapping and report generation with multiple human review points",
    tasks: ["data-source selection", "quote extraction", "theme generation", "quote-to-theme mapping", "prevalence estimation", "report generation", "workflow usability evaluation"],
    architecture: "single-model multi-prompt workflow with user interface and human approvals; not a multi-agent system",
    models: ["GPT-4", "gpt-4o-mini-2025-03-01", "gpt-4o-2024-05-13 for chatbot interviews"],
    model_versions: "GPT-4 exact snapshot not reported; gpt-4o-mini-2025-03-01; gpt-4o-2024-05-13",
    prompting: "researcher-defined high-level themes, iterative quote-extraction checks, relevance-prompt tuning on different 100-subreddit samples until kappa .7, structured quote/subtheme mapping; prompts included in appendices",
    human_role: "11 experienced policy researchers compare the tool with their own non-AI approach; researchers frame scope and review outputs; two researchers plus a polling expert review/synthesize themes; one researcher validates sampled quotes",
    datasets: ["Study 1: Reddit topics and 11 policy researchers", "Study 2 Reddit: 5,491,991 entries across 288 selected subreddits, yielding 122,191 relevant quotes", "Study 2 interviews: 1,058 U.S. adults; 27,042 question units and 16,029 retained human-message quotes", "six authoritative policy reports yielding 22 reference themes"],
    chunking: "Reddit discussion entries with linearized comments; interview question–answer units combining consecutive human messages after each chatbot question; theme work at quote level",
    metrics: ["Cohen kappa for subreddit relevance prompt calibration", "theme overlap/coverage", "theme counts under timed user tasks", "qualitative user-study themes", "quote fidelity checks", "cost and processing time"],
    results: ["Seven of 11 policy researchers rated speed/efficiency positively and participants gathered about two more themes in the timed tool condition.", "Reddit and interview outputs each matched 16 of 22 authoritative-report themes; across 35 total themes, 31 appeared in Reddit or interviews.", "The workflow processed about 1,000 quotes per 10 minutes and a 10,000-post report cost about $150–$300."],
    baselines: ["participants' own non-AI expert approach", "six authoritative policy reports", "Reddit versus chatbot-led interview source comparison", "TopicGPT/LLooM conceptual comparisons"],
    runs_or_seeds: "iterative prompt calibration used a different random sample of 100 subreddits per iteration; exact iteration count and seeds not reported",
    ethics: "Study 1 and interview study report IRB approval; interview participants consented and were paid; PII screening/anonymization and instructions not to disclose sensitive data are reported; Reddit representativeness, consent and platform governance are discussed.",
    reproducibility: "prompts are included in appendices; raw data/code availability is not reported in the inspected preprint",
    limitations: "Reddit and interview samples are not population representative; three U.S. topics only; chatbot interviews may be shallower; prompt tuning may propagate errors; QuaLLM only.",
    validity_concerns: "Authoritative reports address overlapping but nonidentical questions, provenance links to original Reddit posts were unavailable, and theme overlap cannot distinguish missing minority perspectives or interpretive equivalence.",
    domain: "U.S. policy research and public opinion"
  },
  {
    id: "jeyaganthan_2026_corefine",
    citation: "Jeyaganthan, Athikash; Xu, Kai; Becker, Franziska; Koch, Steffen. 2026. Co-Refine: AI-Powered Tool Supporting Qualitative Analysis. arXiv:2604.19309v1.",
    year: 2026,
    venue: "arXiv",
    status: "arXiv preprint; peer-reviewed venue not verified",
    publication_type: "preprint",
    doi: "10.48550/arXiv.2604.19309",
    url: "https://arxiv.org/abs/2604.19309",
    claimed_method: "human-controlled qualitative coding/reflexive thematic-analysis support for temporal drift and intra-coder consistency",
    operationalized_method: "three-stage real-time audit combining deterministic embedding scores, LLM explanations constrained within ±.15 of those scores, and evolving code definitions derived from prior segments",
    tasks: ["intra-code consistency scoring", "temporal-drift detection", "semantic code-overlap detection", "grounded feedback", "code reflection", "ICR disagreement support", "audit logging"],
    architecture: "interactive client-server system with deterministic stage, GPT-5.2 audit/reflection stage, append-only audit records, per-user vector retrieval, and researcher override",
    models: ["text-embedding-3-small", "GPT-5.2 via Azure OpenAI", "fast Azure OpenAI model for chat/facet labels not reported"],
    model_versions: "text-embedding-3-small; GPT-5.2; fast deployment not reported",
    prompting: "Stage-2 LLM receives deterministic scores, local context, MMR/recency-sampled prior segments and prior code reflection; consistency score constrained to ±.15; Stage 3 triggers at three segments and every three additions, sampling up to 30 segments",
    human_role: "researcher performs all coding, can inspect/override alerts and configure thresholds; requirements interviews with three qualitative researchers; formative study with five participants",
    datasets: "controlled synthetic consistency segments plus a resampled subset of the SemEval-2016 English hotel-review ABSA dataset; exact document count not reported",
    chunking: "researcher-selected text spans; audit retrieval over prior coded segments",
    metrics: ["centroid cosine similarity", "temporal drift", "code-overlap thresholds", "constraint adherence", "modified 9-item System Usability Scale", "Cohen/Fleiss kappa and Krippendorff alpha as interface features"],
    results: ["All test alerts matched expected controlled classifications and LLM consistency scores stayed within ±.15 of deterministic scores.", "Five-person modified SUS mean was 77.77; qualitative feedback emphasized trust through grounding, reflective friction, and need for deeper theoretical grounding."],
    baselines: "feature comparison with NVivo/ATLAS.ti, CollabCoder, CoAIcoder, PaTAT and Cody; no controlled comparative outcome study",
    runs_or_seeds: "software unit/integration/end-to-end tests and one 30–45 minute task per formative participant; stochastic runs/seeds not reported",
    ethics: "Consent, ethics approval, and data governance for the requirements/formative studies are not reported in the inspected preprint.",
    reproducibility: "source code, prompts, evaluation data, SUS and thematic-analysis materials are available on reasonable request; no public repository URL reported",
    limitations: "text only; embedding dependence; possible misleading explanations; N=3 requirements and N=5 convenience user study; controlled/synthetic pipeline testing; no longitudinal real-world drift-reduction comparison.",
    validity_concerns: "A deterministic similarity anchor constrains score hallucination but does not validate that semantic consistency equals qualitative coherence, appropriate reflexive change, or interpretive quality.",
    domain: "qualitative coding workbench; formative hotel-review task"
  },
  {
    id: "zhu_2026_trauma",
    citation: "Zhu, Jessica H.; Stringfield, Shayla; Zaprosyan, Vahe; Wagner, Michael; Cukier, Michel; Richardson, Joseph B. Jr. 2026. Can LLMs Understand the Impact of Trauma? Costs and Benefits of LLMs Coding the Interviews of Firearm Violence Survivors. Findings of ACL 2026, 12174–12192.",
    year: 2026,
    venue: "Findings of the Association for Computational Linguistics: ACL 2026",
    status: "peer-reviewed ACL Findings paper",
    publication_type: "conference/proceedings paper",
    doi: "10.18653/v1/2026.findings-acl.591",
    url: "https://aclanthology.org/2026.findings-acl.591/",
    objective: "assess whether locally run open-source LLMs can inductively code long-form interviews with Black men who survived community firearm violence, and quantify accuracy, processing sensitivity, refusals, and ethical harms relative to human coding",
    claimed_method: "grounded-theory-informed inductive thematic coding compared with automated LLM-assisted qualitative coding",
    operationalized_method: "zero-shot Llama code generation over full, paired-turn, or question-conditioned chunks, followed by BERTopic consolidation and embedding-threshold comparison with a human-developed codebook",
    tasks: ["interview chunking", "inductive code generation", "BERTopic code consolidation", "human-code matching", "refusal and narrative-erasure analysis", "source-excerpt audit"],
    architecture: "single-model, non-agent pipeline combining local Llama generation, sentence-transformer routing/matching, and BERTopic clustering",
    models: ["Llama-3.2-1B-Instruct", "Llama-3.1-8B-Instruct", "all-mpnet-base-v2", "multi-qa-MiniLM-L6-cos-v1", "BERTopic"],
    model_versions: "Llama-3.2-1B-Instruct; Llama-3.1-8B-Instruct; all-mpnet-base-v2; multi-qa-MiniLM-L6-cos-v1",
    prompting: "zero-shot identity and context variants; prompts use the term themes rather than codes; prompt templates are in Appendix A",
    human_role: "three Black/African-American women (one undergraduate and two research staff, one with more than two years' experience) inductively coded the interviews; member checking and principal-investigator review refined the human codebook; large-scale machine-code matching used embeddings rather than full human validation",
    datasets: "21 deidentified interviews with Black/African-American men who survived community firearm violence; approximately 60 minutes and mean 11,503 words per interview",
    number_documents: "21 interviews",
    number_participants: "21 Black/African-American men who survived community firearm violence",
    document_length: "approximately 60 minutes and mean 11,503 words per interview",
    chunking: "maximum 256-token chunks; paired interviewer–participant turns, question-conditioned response groups, and full-interview input for the 1B model",
    metrics: ["Percent Captured", "Percent Relevant", "embedding cosine similarity at a 0.6 match threshold", "silhouette score", "refusal rate", "Wilcoxon signed-rank tests", "Pearson correlation"],
    baselines: "human inductive coding and formal human codebook; Llama 1B versus Llama 8B; full-text, paired-turn, and question-conditioned processing variants",
    runs_or_seeds: "118 machine-coding experiments across model, chunking, identity, and context settings; random seeds not reported",
    results: ["Across experiments, Percent Captured averaged 71% (SD 18%) and Percent Relevant averaged 10% (SD 5%); the best initial configurations captured all 11 formal human codes but remained low in relevance.", "Prompts refused on average 44% (SD 25%) of requests, disproportionately erasing graphic violence, sexual activity, race, and African American English content.", "Clustering reduced thousands of initial codes to fewer than 60 but often reduced capture and introduced tenuous, stereotypical, or unsupported formal codes."],
    efficiency: "Human coding took about 35 total hours; 118 machine experiments averaged 3.4 hours (SD 3.3), with processing time strongly dependent on chunking; formal-code clustering took under five minutes on average.",
    ethics: "IRB protocol 343085-1; participants volunteered and received $50; transcripts were manually deidentified and pseudonymized; models ran on university hardware; data will not be released; output codes were manually checked for identifiability; narrative erasure, stereotyping, and misrepresentation are analyzed explicitly.",
    reproducibility: "code at https://github.com/jhzsquared/AIvsHumanCoding; prompts and parameter tables in appendices; interview data withheld to protect participants",
    limitations: "one Washington, DC-area sample and one regional African American English pattern; possible transcription error; limited prompting; no full human validation of the embedding match pipeline; only two Llama sizes/families; no quantization comparison.",
    validity_concerns: "Human codes are treated as ground truth despite acknowledged possible novel machine codes, and the 0.6 embedding threshold was sample-checked rather than independently validated; extensive configuration search and refusal-driven missingness complicate generalization.",
    domain: "sensitive trauma interviews with Black men who survived community firearm violence",
    language: "English; African American English"
  }
];

const excludedLowerPriorityAdjacentIds = new Set(["moverscore_2019", "bleurt_2020", "geval_2023"]);

const sourceRows = [];
for (const record of core.studies) sourceRows.push({source: "core_systems", section: "studies", record});
for (const record of evaluation.automated_qualitative_studies) sourceRows.push({source: "evaluation_methodology", section: "automated_qualitative_studies", record});
for (const record of evaluation.foundational_sources) sourceRows.push({source: "evaluation_methodology", section: "foundational_sources", record});
for (const record of evaluation.general_evaluation_sources) {
  if (!excludedLowerPriorityAdjacentIds.has(record.id)) sourceRows.push({source: "evaluation_methodology", section: "general_evaluation_sources", record});
}
for (const record of validity.papers) sourceRows.push({source: "validity_ethics", section: "papers", record});
for (const record of latestStudies) sourceRows.push({source: "latest_full_text", section: "latestStudies", record});

const grouped = new Map();
for (const item of sourceRows) {
  const key = canonicalKey(item.record);
  if (!grouped.has(key)) grouped.set(key, []);
  grouped.get(key).push(item);
}

const titleOverrides = {
  qualanalyzer_2026: "QualAnalyzer: A Transparent and Auditable LLM-Assisted Qualitative Analysis Framework",
  bai_2026_three_datasets: "A Multimodule Large Language Model Pipeline for Inductive Thematic Analysis Across Three Health Care Interview Datasets",
  rouge_2004: "ROUGE: A Package for Automatic Evaluation of Summaries",
  bertscore_2020: "BERTScore: Evaluating Text Generation with BERT",
  moverscore_2019: "MoverScore: Text Generation Evaluating with Contextualized Embeddings and Earth Mover Distance",
  bleurt_2020: "BLEURT: Learning Robust Metrics for Text Generation",
  red_faced_rouge_2019: "Red-faced ROUGE: Examining the Suitability of ROUGE for Opinion Summary Evaluation",
  geval_2023: "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment",
  wang_2024_order_bias: "Large Language Models are not Fair Evaluators",
  jacobs_wallach_2021: "Measurement and Fairness",
  van_der_lee_2019: "Best practices for the human evaluation of automatically generated text",
  howcroft_2020: "Twenty Years of Confusion in Human Evaluation: NLG Needs Evaluation Sheets and Standardised Definitions"
};

const authorOverrides = {
  rouge_2004: "Chin-Yew Lin",
  bertscore_2020: "Tianyi Zhang; Varsha Kishore; Felix Wu; Kilian Q. Weinberger; Yoav Artzi",
  moverscore_2019: "Wei Zhao; Maxime Peyrard; Fei Liu; Yang Gao; Christian M. Meyer; Steffen Eger",
  bleurt_2020: "Thibault Sellam; Dipanjan Das; Ankur P. Parikh",
  red_faced_rouge_2019: "Wenyi Tay; Aditya Joshi; Xiuzhen Zhang; Sarvnaz Karimi; Stephen Wan",
  geval_2023: "Yang Liu; Dan Iter; Yichong Xu; Shuohang Wang; Ruochen Xu; Chenguang Zhu",
  wang_2024_order_bias: "Peiyi Wang; Lei Li; Liang Chen; Zefan Cai; Dawei Zhu; Binghuai Lin; Yunbo Cao; Lingpeng Kong; Qi Liu; Tianyu Liu; Zhifang Sui",
  jacobs_wallach_2021: "Abigail Z. Jacobs; Hanna Wallach",
  van_der_lee_2019: "Chris van der Lee; Albert Gatt; Emiel van Miltenburg; Sander Wubben; Emiel Krahmer",
  howcroft_2020: "David M. Howcroft et al.",
  bai_2026_three_datasets: "Bai; Finkelstein"
};

const yearOverrides = {
  rouge_2004: "2004", bertscore_2020: "2020", moverscore_2019: "2019", bleurt_2020: "2020",
  red_faced_rouge_2019: "2019", geval_2023: "2023", wang_2024_order_bias: "2024",
  jacobs_wallach_2021: "2021", van_der_lee_2019: "2019", howcroft_2020: "2020"
};

const venueOverrides = {
  rouge_2004: "Workshop on Text Summarization Branches Out",
  bertscore_2020: "ICLR 2020",
  moverscore_2019: "EMNLP-IJCNLP 2019",
  bleurt_2020: "ACL 2020",
  red_faced_rouge_2019: "Australasian Language Technology Association Workshop 2019",
  geval_2023: "EMNLP 2023",
  wang_2024_order_bias: "ACL 2024",
  jacobs_wallach_2021: "FAccT 2021",
  van_der_lee_2019: "INLG 2019",
  howcroft_2020: "INLG 2020",
  bai_2026_three_datasets: "JMIR Medical Informatics"
};

function parseCitation(citation, id) {
  const out = {authors: NR, year: NR, title: NR, venue: NR};
  if (isMissing(citation)) return out;
  const c = flatten(citation);
  let match = c.match(/^(.+?)\s+\((19\d{2}|20\d{2})\)\.\s+(.+?)\.\s+(.+)$/);
  if (match) return {authors: match[1], year: match[2], title: match[3], venue: match[4]};
  match = c.match(/^(.+?)\.\s+(19\d{2}|20\d{2})\.\s+(.+?)\.\s+(.+)$/);
  if (match) return {authors: match[1], year: match[2], title: match[3], venue: match[4]};
  match = c.match(/^(.+?)\.\s+(.+?)\.\s+(.+)$/);
  if (match) {
    out.authors = match[1];
    out.title = match[2];
    out.venue = match[3];
    const ym = c.match(/(?:^|\D)(19\d{2}|20\d{2})(?:\D|$)/);
    if (ym) out.year = ym[1];
  }
  if (titleOverrides[id]) out.title = titleOverrides[id];
  if (authorOverrides[id]) out.authors = authorOverrides[id];
  if (yearOverrides[id]) out.year = yearOverrides[id];
  if (venueOverrides[id]) out.venue = venueOverrides[id];
  return out;
}

const coreIds = new Set([
  "dai_2023_llm_in_loop", "parfenova_2025_inductive_coding", "parfenova_pfeffer_2025_ensemble",
  "hicode_2025", "quallm_2025", "thematic_lm_2025", "lloom_2024", "details_2025",
  "chen_2026_open_code_metrics", "centaurta_2026", "auto_ta_2025", "sft_ta_2025", "tama_2026",
  "yi_2026_provenance_refinement", "llm_ta_2025", "qualanalyzer_2026", "jowsey_2025_frankenstein",
  "hill_2026_healthcare", "montes_2025_prompting", "perez_2026_icr", "alghamdi_2026_convergence",
  "ashwin_2025_serious_bias", "mathis_2024_open_source", "prescott_2024_genai_human",
  "li_2024_gpt4_human", "bijker_2024_content_analysis", "bennis_2025_nine_models",
  "vikan_2025_reflexive", "grover_2026_preferences", "bai_2026_three_datasets",
  "turner_2026_dementia_trials", "sakaguchi_2025_japanese", "wachinger_2024_prompts",
  "zhu_2026_trauma", "matveyenko_2026_muse", "katz_2026_gatos",
  "liu_2026_agreement_not_quality", "liu_2026_human_llm_inductive",
  "camporese_2026_security_comments", "liu_2026_policy_workflow", "jeyaganthan_2026_corefine",
  "dorfel_2026_inductive_coding", "depaoli_2024_further_explorations", "borse_2025_inter_rater_reliability"
]);

const classificationOverrides = {
  parfenova_2024_proposal: "adjacent — research proposal without completed system evaluation",
  position_clinical_ta_2025: "adjacent — position/review/evaluation agenda",
  pi_2026_landscape: "adjacent — conceptual landscape and novelty check",
  bedemariam_2025_judges: "adjacent — LLM-as-judge evaluation",
  lloom_2024: "core-adjacent — mixed-initiative concept induction",
  perez_2026_icr: "core — evaluation/position study",
  prescott_2024_genai_human: "core — proxy-data thematic-analysis comparison",
  wachinger_2024_prompts: "core — failure-mode experiment on proxy data",
  ronaghi_2026_large_scale: "adjacent — bibliographic lead; detailed full-text extraction not verified"
};

const foundationalIds = new Set(evaluation.foundational_sources.map(r => r.id));
const metricIds = new Set(evaluation.general_evaluation_sources.map(r => r.id));
const adjacentValidityIds = new Set(validity.papers.filter(r => r.relationship === "adjacent").map(r => r.id));

function classification(id) {
  if (classificationOverrides[id]) return classificationOverrides[id];
  if (coreIds.has(id)) return "core";
  if (foundationalIds.has(id)) return "adjacent — qualitative-methodological foundation";
  if (metricIds.has(id)) return "adjacent — evaluation/construct-validity method";
  if (adjacentValidityIds.has(id)) return "adjacent — validity, confounding, or privacy evidence";
  return "adjacent";
}

const relationshipFamily = {
  auto_ta_2025: "AAOCA-9/42/12 family — same 9 focus groups, 42 participants, and 12 published reference themes as LLM-TA, SFT-TA, TAMA, and the provenance paper; not an independent dataset replication",
  sft_ta_2025: "AAOCA-9/42/12 family — same 9 focus groups, 42 participants, and 12 published reference themes; 10 of 12 themes also shape fine-tuning data",
  tama_2026: "AAOCA-9/42/12 family — same 9 focus groups, 42 participants, and 12 published reference themes as four related system papers; not an independent dataset replication",
  yi_2026_provenance_refinement: "AAOCA-9/42/12 family — reuses AAOCA alongside four added corpora and inherits the Auto-TA/LOGOS pipeline lineage",
  llm_ta_2025: "AAOCA-9/42/12 family — first system paper in this extracted clinical benchmark lineage",
  position_clinical_ta_2025: "AAOCA research-group position/evaluation agenda; no independent system experiment",
  parfenova_2024_proposal: "Parfenova qualitative-coding program — proposal antecedent to the 2025 inductive-coding and ensemble-refinement papers",
  parfenova_2025_inductive_coding: "Parfenova qualitative-coding program — empirical sentence-level coding paper preceding ensemble refinement",
  parfenova_pfeffer_2025_ensemble: "Parfenova qualitative-coding program — extends the earlier quote/code setup with candidate-model moderation and label refinement",
  details_2025: "DeTAILS version family — peer-reviewed CUI 2025 short paper plus a distinct expanded arXiv manuscript; evidence must be attributed to the correct version",
  braun_clarke_2021_quality: "Braun–Clarke reflexive thematic-analysis methodology family",
  braun_clarke_2021_can_i_use: "Braun–Clarke reflexive thematic-analysis methodology family",
  rouge_2004: "General text-generation metric transfer family; not originally validated for qualitative interpretive equivalence",
  bertscore_2020: "General text-generation metric transfer family; not originally validated for qualitative interpretive equivalence",
  moverscore_2019: "General text-generation metric transfer family; not originally validated for qualitative interpretive equivalence",
  bleurt_2020: "General text-generation metric transfer family; not originally validated for qualitative interpretive equivalence",
  red_faced_rouge_2019: "ROUGE construct-validity/failure-mode family",
  geval_2023: "LLM-as-judge method/bias family",
  wang_2024_order_bias: "LLM-as-judge method/bias family",
  van_der_lee_2019: "Human-evaluation reporting-method family",
  howcroft_2020: "Human-evaluation reporting-method family"
  ,liu_2026_human_llm_inductive: "UW/Colleague K-12 educator-AI family — develops the 72-item codebook from 45,000 messages and validates it on the same independent 2,560-message sample used by Agreement Is Not Quality"
  ,liu_2026_agreement_not_quality: "UW/Colleague K-12 educator-AI family — reuses the 72-item codebook and 2,560-message validation corpus created in the companion inductive-coding paper; not an independent dataset replication"
  ,liu_2026_policy_workflow: "QuaLLM lineage — adapts Rao et al. 2025 to policy research, adding practitioner evaluation, interviews, source comparison and manual report review"
  ,camporese_2026_security_comments: "Unpublished security-experiment annotation family — human comment/code data supplied from the Papotti et al. research line and deliberately withheld from prior publication to reduce contamination risk"
};

const domainOverrides = {
  dai_2023_llm_in_loop: "consumer-product and UX survey responses",
  parfenova_2024_proposal: "social-science interview quotations (proposed)",
  parfenova_2025_inductive_coding: "social-science quotations and product reviews",
  parfenova_pfeffer_2025_ensemble: "social-science quotations and product reviews",
  hicode_2025: "history, astronomy, values, and OCR corpora",
  quallm_2025: "online forums/Reddit",
  thematic_lm_2025: "Reddit stress and climate discourse",
  lloom_2024: "multi-domain text corpora",
  details_2025: "Reddit; qualitative-research workbench study",
  chen_2026_open_code_metrics: "online physics-education community",
  centaurta_2026: "social-science and Reddit qualitative corpora",
  auto_ta_2025: "clinical congenital-heart-disease parent focus groups",
  sft_ta_2025: "clinical congenital-heart-disease parent focus groups",
  tama_2026: "clinical congenital-heart-disease parent focus groups",
  yi_2026_provenance_refinement: "clinical interviews plus public interview/Reddit corpora",
  llm_ta_2025: "clinical congenital-heart-disease parent focus groups",
  position_clinical_ta_2025: "clinical qualitative transcripts",
  qualanalyzer_2026: "qualitative interview transcripts",
  jowsey_2025_frankenstein: "five published qualitative datasets",
  hill_2026_healthcare: "health care; people with long-term conditions",
  perez_2026_icr: "open-survey datasets",
  pi_2026_landscape: "computational qualitative-analysis literature",
  bedemariam_2025_judges: "evaluation of thematic summaries"
};

const inductiveOverrides = {
  dai_2023_llm_in_loop: "hybrid",
  parfenova_2024_proposal: "inductive",
  parfenova_2025_inductive_coding: "inductive",
  parfenova_pfeffer_2025_ensemble: "inductive",
  hicode_2025: "inductive",
  quallm_2025: "hybrid",
  thematic_lm_2025: "inductive",
  lloom_2024: "inductive",
  details_2025: "hybrid",
  chen_2026_open_code_metrics: "inductive",
  centaurta_2026: "inductive",
  auto_ta_2025: "inductive",
  sft_ta_2025: "inductive (but supervised toward a fixed reference-theme universe)",
  tama_2026: "inductive/codebook hybrid",
  yi_2026_provenance_refinement: "inductive",
  llm_ta_2025: "inductive",
  position_clinical_ta_2025: "not applicable — review/position paper",
  qualanalyzer_2026: "deductive coding case study",
  jowsey_2025_frankenstein: "inductive comparison",
  hill_2026_healthcare: "hybrid",
  montes_2025_prompting: "inductive",
  perez_2026_icr: "inductive",
  alghamdi_2026_convergence: "inductive comparison",
  ashwin_2025_serious_bias: "deductive",
  mathis_2024_open_source: "inductive",
  prescott_2024_genai_human: "hybrid",
  li_2024_gpt4_human: "not reported",
  bijker_2024_content_analysis: "hybrid",
  bennis_2025_nine_models: "hybrid",
  vikan_2025_reflexive: "inductive/reflexive",
  grover_2026_preferences: "inductive",
  bai_2026_three_datasets: "inductive",
  turner_2026_dementia_trials: "deductive",
  sakaguchi_2025_japanese: "inductive/reflexive",
  wachinger_2024_prompts: "inductive plus method-prompt variants",
  ronaghi_2026_large_scale: "hybrid"
  ,matveyenko_2026_muse: "hybrid — inductive codebook generation plus deductive code application"
  ,katz_2026_gatos: "inductive"
  ,liu_2026_agreement_not_quality: "deductive"
  ,liu_2026_human_llm_inductive: "inductive development plus deductive human validation"
  ,camporese_2026_security_comments: "deductive"
  ,liu_2026_policy_workflow: "hybrid"
  ,jeyaganthan_2026_corefine: "not applicable to code induction — supports consistency during researcher-led coding"
};

const sensitiveStatusOverrides = {
  zhu_2026_trauma: "highly sensitive trauma interviews involving firearm-violence survivors; transcripts were deidentified and withheld"
};

function publicationType(status, id, sourceRecords) {
  const explicit = first(sourceRecords, ["publication_type"]);
  if (explicit !== NR) return explicit;
  const s = status.toLowerCase();
  if (id === "parfenova_2024_proposal") return "doctoral/student research proposal";
  if (id === "position_clinical_ta_2025" || id === "perez_2026_icr") return "position paper";
  if (s.includes("preprint") || s.includes("arxiv")) return "preprint/manuscript";
  if (s.includes("journal")) return "journal article";
  if (s.includes("conference") || s.includes("findings") || s.includes("proceedings")) return "conference/proceedings paper";
  if (foundationalIds.has(id)) return "methodological/guidance article";
  if (metricIds.has(id)) return "evaluation-method paper";
  return NR;
}

function peerReview(status, id) {
  const s = status.toLowerCase();
  // Negative/unverified clauses take precedence over the literal phrase
  // "peer-reviewed" (for example, "peer-reviewed venue not verified").
  if (s.includes("acceptance not verified") || s.includes("not verified") || s.includes("not independently verified") || s.includes("final archival status not verified")) {
    return "preprint/manuscript; peer review not verified";
  }
  if (s.includes("preprint") || s.includes("arxiv") || s.includes("manuscript")) {
    if (!(s.includes("peer-reviewed") || s.includes("peer reviewed"))) return "preprint/manuscript; peer review not verified";
    if (s.includes("plus distinct") || s.includes("peer-reviewed version plus")) return "mixed: peer-reviewed version plus non-peer-reviewed version";
  }
  if (s.includes("peer-reviewed") || s.includes("peer reviewed")) {
    if (s.includes("plus distinct") || s.includes("plus") && s.includes("preprint")) return "mixed: peer-reviewed version plus non-peer-reviewed version";
    return "peer reviewed";
  }
  if (s.includes("preprint") || s.includes("arxiv") || s.includes("manuscript")) return "preprint/manuscript; peer review not verified";
  if (foundationalIds.has(id) || metricIds.has(id)) return s.includes("peer") ? "peer reviewed" : NR;
  return NR;
}

function corpusText(sourceRecords) {
  // Keep analytic tasks out of the dataset fields.  Several source records store
  // rich corpus descriptions rather than a short proper name, so those
  // descriptions are retained verbatim instead of guessing a dataset name.
  return combine(sourceRecords, ["datasets", "dataset", "sample"]);
}

function extractMatches(text, patterns) {
  if (text === NR) return NR;
  const hits = [];
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      const hit = (match[1] ?? match[0]).replace(/\s+/g, " ").trim();
      if (hit && !hits.includes(hit)) hits.push(hit);
    }
  }
  return hits.length ? hits.join("; ") : NR;
}

function documentCounts(text) {
  return extractMatches(text, [
    /([^;|]{0,55}\b\d[\d,]*(?:\s*[-–/]\s*\d[\d,]*)?\s+(?:documents?|docs?|transcripts?|interviews?|focus groups?|posts?|submissions?|reviews?|answers?|quotations?|abstracts?|threads?|messages?|records?)[^;|]{0,35})/gi,
    /([^;|]{0,40}(?:documents?|docs?|transcripts?|interviews?|focus groups?|posts?|submissions?|reviews?|answers?|quotations?|abstracts?|threads?|messages?|records?)\s*[:=]\s*\d[\d,]*[^;|]{0,35})/gi
  ]);
}

function participantCounts(text) {
  return extractMatches(text, [
    /([^;|]{0,40}\b\d[\d,]*\s+(?:participants?|parents?|adults?|people|clients?|clinicians?|students?|coders?|respondents?|raters?)[^;|]{0,30})/gi
  ]);
}

function documentLength(text) {
  return extractMatches(text, [
    /([^;|]{0,35}\b\d[\d,.]*(?:\s*[-–/]\s*\d[\d,.]*)?\s+(?:words?|pages?|minutes?|hours?|characters?|tokens?)[^;|]{0,30})/gi
  ]);
}

function language(text) {
  const known = ["English", "Japanese", "Norwegian", "Bengali", "Rohingya", "French", "Finnish", "Italian"];
  const found = known.filter(name => new RegExp(`\\b${name}\\b`, "i").test(text));
  return found.length ? found.join("; ") : NR;
}

function dataAccess(sourceRecords) {
  const corpus = combine(sourceRecords, ["datasets", "dataset", "sample"]);
  const governance = combine(sourceRecords, ["ethics", "ethics_privacy"]);
  const resources = combine(sourceRecords, ["reproducibility"]);
  const text = `${corpus} | ${governance} | ${resources}`;
  if (/\bnot publicly released\b/i.test(text)) return "restricted/not publicly released";
  if (/\brestricted raw transcripts?\b/i.test(text)) return "restricted raw transcripts";
  if (/\bdata access requires REB\b/i.test(text)) return "restricted; data access requires research-ethics-board approval";
  if (/\bdata(?:set)?\/code unavailable, access by request\b/i.test(text)) return "restricted/request-based access";
  if (/\b(?:anonymized|deidentified|de-identified) data (?:available )?(?:upon|on) request\b/i.test(text)) return "restricted/request-based access to anonymized data";
  if (/\bdata(?:set)? (?:are|is) restricted\b/i.test(text)) return "restricted";
  if (/\bconfidential transcripts?\b/i.test(text)) return "restricted/confidential";
  if (/\btranscript (?:is )?withheld\b/i.test(text)) return "restricted; transcript withheld for residual identifiability";
  if (/\braw clinical transcripts? (?:are )?not public\b/i.test(text)) return "restricted raw clinical transcripts";
  if (/\bdata will not be released\b/i.test(text)) return "restricted; data withheld to protect participants";
  if (/\bpublicly available (?:human-coded )?datasets?\b/i.test(corpus)) return "public source datasets";
  if (/\bpublic (?:non-sensitive )?data\b/i.test(text)) return "public data";
  if (/\bopen forum posts?\b/i.test(corpus) || /\bpublic[- ]forums?\b/i.test(text)) return "public online-forum data";
  if (/\bReddit\b/i.test(corpus) && !/\brestricted\b/i.test(text)) return "public online-forum data";
  if (/\bpublic (?:Physics Lab )?community messages?\b/i.test(corpus)) return "public community-message data";
  if (/\bpublic\/benchmark sources?\b/i.test(governance)) return "public benchmark/source data";
  return NR;
}

function sensitiveStatus(sourceRecords) {
  const text = combine(sourceRecords, ["ethics", "ethics_privacy", "domain", "dataset", "datasets"]);
  if (text === NR) return NR;
  if (/(confidential|restricted|clinical transcript|patient|health|refugee|mental illness|deidentified|de-identified|sensitive)/i.test(text)) {
    return extractMatches(text, [/([^;|]{0,65}(?:confidential|restricted|deidentified|de-identified|clinical|patient|health|refugee|sensitive)[^;|]{0,65})/gi]);
  }
  if (/(public|reddit|open forum|corporate transcript)/i.test(text)) return "public/nonclinical source described; sensitive-data risks not reported as material";
  return NR;
}

function adaptation(sourceRecords) {
  const explicit = combine(sourceRecords, ["fine_tuning", "fine_tuning_or_adaptation"]);
  if (explicit !== NR) return explicit;
  const text = combine(sourceRecords, ["models", "model", "prompting", "architecture", "conditions"]);
  if (text === NR) return NR;
  const mechanisms = [];
  const lora = text.match(/\bLoRA\b[^;|.]*/i)?.[0];
  if (lora) mechanisms.push(lora.trim());
  if (/\bfine[- ]?tun|\bSFT\b/i.test(text)) mechanisms.push("supervised fine-tuning (SFT)");
  if (/\bRAG\b|\bretrieval[- ]?augmented/i.test(text)) mechanisms.push("retrieval-augmented generation (RAG)");
  if (/\breinforcement learning\b|\bPPO\b/i.test(text)) mechanisms.push("reinforcement-learning/PPO adaptation");
  if (/\bGPT augmentation\b/i.test(text)) mechanisms.push("GPT-based training-data augmentation");
  return mechanisms.length ? [...new Set(mechanisms)].join("; ") : NR;
}

function architectureType(sourceRecords) {
  const a = combine(sourceRecords, ["architecture", "workflow"]);
  if (a === NR) return NR;
  if (/\bno (?:[^;|]{0,45})?agents?\b|\bno (?:[^;|]{0,45})?multi-agent\b|\bnot (?:[^;|]{0,45})?(?:agent|multi-agent)|\bsingle LLM\b/i.test(a)) return `single-model or non-agent pipeline — ${a}`;
  if (/multi-agent|multiple candidate|coder.*aggregator|actor.*critic|\bagents?\b/i.test(a)) return `multi-role/multi-agent as reported — ${a}`;
  return `single-model or non-agent pipeline — ${a}`;
}

function agentRoles(sourceRecords) {
  const a = combine(sourceRecords, ["architecture"]);
  if (a === NR || /\bno (?:[^;|]{0,45})?agents?\b|\bno (?:[^;|]{0,45})?multi-agent\b|\bnot (?:[^;|]{0,45})?(?:agent|multi-agent)|\bsingle LLM\b/i.test(a)) return NR;
  return /multi-agent|multiple candidate|coder.*aggregator|actor.*critic|\bagents?\b/i.test(a) ? a : NR;
}

function evidenceMechanism(sourceRecords) {
  const explicit = combine(sourceRecords, ["evidence_provenance"]);
  if (explicit !== NR) return explicit;
  const text = combine(sourceRecords, ["workflow", "operationalized_method", "tasks", "human_reference", "validity_concerns", "validity_concern"]);
  if (text === NR) return NR;
  const mechanisms = [];
  if (/parent[- ]ID/i.test(text)) mechanisms.push("parent-ID links from themes to codes and source units");
  if (/persistent evidence graph/i.test(text)) mechanisms.push("persistent evidence graph");
  if (/action ledger|provenance ledger/i.test(text)) mechanisms.push("action/provenance ledger");
  if (/full provenance/i.test(text)) mechanisms.push("full-provenance records");
  if (/quote plus segment ID|quote\s*\+\s*segment ID/i.test(text)) mechanisms.push("source quotation plus segment ID");
  else if (/exact[- ]quote|quote-grounded|coding with quotes?|concern extraction with quote|quote extraction|quotations?|source[- ]excerpt audit/i.test(text)) mechanisms.push("source quotations/excerpts retained with analytic outputs");
  if (/append-only audit records?|audit log/i.test(text)) mechanisms.push("append-only audit log");
  if (/grounded feedback.*prior coded segments|retrieval over prior coded segments/i.test(text)) mechanisms.push("feedback grounded in retrieved prior coded segments");
  return mechanisms.length ? [...new Set(mechanisms)].join("; ") : NR;
}

const baselineOverrides = {
  dai_2023_llm_in_loop: "original human coding and an independent third human coder",
  parfenova_2025_inductive_coding: "human-expert codes and ratings; zero-shot and few-shot model variants",
  hicode_2025: "human Astro coding and TopicGPT",
  thematic_lm_2025: "single-model pipeline and random-half comparisons",
  lloom_2024: "direct GPT-4/GPT-4-Turbo concept induction and human coding",
  auto_ta_2025: "reported single-model baseline and published human reference themes",
  sft_ta_2025: "unspecialized LLM/TextGrad variants and published human reference themes; most evaluation themes also shaped fine-tuning",
  tama_2026: "single-model GPT-4o/Llama variants and published human reference themes",
  ashwin_2025_serious_bias: "supervised iQual, iQual with GPT augmentation, and four LLM variants",
  hill_2026_healthcare: "mutually blinded human analysts and three LLM systems",
  turner_2026_dementia_trials: "four human coders using the same 11-code codebook and two GPT-4o variants",
  sakaguchi_2025_japanese: "independent human reflexive thematic analysis and repeated GPT-4o analyses",
  bijker_2024_content_analysis: "human verification on a 20% subset and repeated ChatGPT coding schemes",
  li_2024_gpt4_human: "human qualitative analysis and repeated GPT-4 analysis",
  prescott_2024_genai_human: "human thematic analysis, ChatGPT/GPT-3.5, and Bard/PaLM 2",
  mathis_2024_open_source: "traditional human thematic analysis compared with local LLaMA-2-70B-Instruct"
};

function automaticMetrics(sourceRecords) {
  const direct = combine(sourceRecords, ["metrics", "automatic_metrics", "metrics_results", "metrics_statistics"]);
  if (direct !== NR) return direct;
  return filteredEvidence(
    sourceRecords,
    ["evaluation", "principal_results", "principal_evidence"],
    /(?:\bF1\b|precision|recall|accuracy|ROUGE|BLEU|METEOR|BERTScore|Jaccard|cosine|kappa|Krippendorff|Gwet|correlation|regression|Levenshtein|MICS|hallucination|agreement)/i
  );
}

function humanEvaluation(sourceRecords) {
  return combine(sourceRecords, ["human_evaluation", "human_reference", "human_role"]);
}

function evaluatorDescription(human) {
  if (human === NR) return NR;
  return /(?:\b\d+\b|\bone\b|\btwo\b|\bthree\b|\bfour\b|\bfive\b|\bsix\b|\bexpert|researcher|analyst|coder|rater|participant|clinician|domain)/i.test(human) ? human : NR;
}

function filteredEvidence(sourceRecords, keys, pattern) {
  const text = combine(sourceRecords, keys);
  if (text === NR) return NR;
  const parts = text.split(/(?<=[.;|])\s+/).filter(s => pattern.test(s));
  return parts.length ? parts.join(" ") : NR;
}

function citationCount(sourceRecords) {
  for (const {record} of sourceRecords) {
    if (typeof record.crossref_citation_count === "object" && record.crossref_citation_count.count !== undefined) {
      return `${record.crossref_citation_count.count}; Crossref is-referenced-by count; retrieved ${record.crossref_citation_count.retrieved ?? CUTOFF}; dynamic`;
    }
    if (!isMissing(record.citation_count)) {
      const value = flatten(record.citation_count);
      if (value !== NR) return `${value}; source as recorded in source extraction; retrieved ${CUTOFF}`;
    }
  }
  return NR;
}

function relevance(id, cls, sourceRecords) {
  if (relationshipFamily[id]?.startsWith("AAOCA")) return "Critical for avoiding pseudoreplication and reference-theme leakage in the proposed evaluation; report this family as dependent evidence.";
  const implication = first(sourceRecords, ["review_implication"]);
  if (implication !== NR) return implication;
  if (foundationalIds.has(id)) return "Defines the method-specific analytic contract against which computational claims and evaluation criteria should be judged.";
  if (metricIds.has(id)) return "Supplies an evaluation operation or documented failure mode that must be validated before transfer to codes and themes.";
  if (adjacentValidityIds.has(id)) return "Directly motivates controlled tests for identity, leakage, long-context, prompt-order, contamination, or privacy confounds in the ARR design.";
  if (cls.startsWith("core")) return "Candidate system/evaluation baseline and source of unresolved design requirements for plurality-aware, provenance-aware evaluation.";
  return "Novelty and methodological-context check for the proposed ARR project.";
}

const records = [];
for (const sourceRecords of grouped.values()) {
  // Rich system extractions precede evaluation-only and adjacent records by construction.
  const id = sourceRecords[0].record.id;
  const citation = first(sourceRecords, ["citation"]);
  const parsed = parseCitation(citation, id);
  const status = combine(sourceRecords, ["status", "peer_review_status"]);
  const cls = classification(id);
  const dataset = corpusText(sourceRecords);
  const models = combine(sourceRecords, ["models", "model"]);
  const exactModels = combine(sourceRecords, ["model_versions", "models", "model"]);
  const metrics = automaticMetrics(sourceRecords);
  const human = combine(sourceRecords, ["human_role", "human_reference", "human_evaluation"]);
  const principal = combine(sourceRecords, ["results", "principal_results", "principal_result", "principal_evidence", "metrics_results"]);
  const ethics = combine(sourceRecords, ["ethics", "ethics_privacy", "accountability"]);
  const repro = combine(sourceRecords, ["reproducibility", "code_url", "code_data_url", "reproducibility_url", "accepted_manuscript_url"]);
  const validityConcerns = combine(sourceRecords, ["construct_validity", "validity_concerns", "validity_concern", "review_implication", "full_text_uncertainty"]);
  const authors = authorOverrides[id] ?? parsed.authors;
  const year = first(sourceRecords, ["year"]) !== NR ? first(sourceRecords, ["year"]) : (yearOverrides[id] ?? parsed.year);
  const title = titleOverrides[id] ?? parsed.title;
  const venue = first(sourceRecords, ["venue"]) !== NR ? first(sourceRecords, ["venue"]) : (venueOverrides[id] ?? parsed.venue);
  const doi = normalizeDoi(first(sourceRecords, ["doi"]), sourceRecords[0].record);
  const url = first(sourceRecords, ["url", "official_url"]);
  const architecture = combine(sourceRecords, ["architecture", "workflow"]);
  const prompts = combine(sourceRecords, ["prompting", "parameters", "conditions"]);
  const runs = combine(sourceRecords, ["runs_or_seeds", "runs_seeds_hardware", "runs_prompts_seeds", "run_design"]);
  const runFallback = filteredEvidence(sourceRecords, ["results", "reproducibility", "prompting", "principal_results", "principal_evidence"], /\b(?:runs?|seeds?|iterations?|times|sessions|conversations|evaluations)\b/i);
  const humanDesign = humanEvaluation(sourceRecords);
  const irr = filteredEvidence(sourceRecords, ["metrics", "results", "principal_results", "principal_evidence", "metrics_results", "metrics_statistics"], /(kappa|alpha|inter-rater|interrater|agreement)/i);
  const statistics = filteredEvidence(sourceRecords, ["results", "principal_results", "metrics_results", "metrics_statistics", "evaluation"], /(\bp\s*[=<]|confidence interval|\bCI\b|bootstrap|permutation|Spearman|Pearson|correlation|chi-square|F-test|noninferior|standard deviation|\bSD\b)/i);
  const efficiency = combine(sourceRecords, ["efficiency", "efficiency_cost"]);
  const efficiencyFallback = filteredEvidence(sourceRecords, ["results", "principal_results", "principal_evidence"], /(cost|US\$|\$|minutes?|hours?|tokens?|time saving|workload)/i);
  const fineTune = adaptation(sourceRecords);
  const objective = first(sourceRecords, ["objective", "research_objective"]);
  const claimed = combine(sourceRecords, ["claimed_method", "methodology_claimed"]);
  const actual = combine(sourceRecords, ["operationalized_method", "workflow"]);
  const tasks = combine(sourceRecords, ["tasks"]);
  const limitations = combine(sourceRecords, ["limitations"]);
  const relationship = relationshipFamily[id] ?? first(sourceRecords, ["relationship", "dependency_cluster"]);
  const domain = first(sourceRecords, ["domain"]) !== NR ? first(sourceRecords, ["domain"]) : (domainOverrides[id] ?? NR);
  const pubType = publicationType(status, id, sourceRecords);
  const publicationHistory = status !== NR ? status : `${pubType}; publication history beyond the linked record ${NR}`;
  const row = {
    "Paper ID": id,
    "Full citation": citation !== NR ? citation : `${authors}. ${year}. ${title}. ${venue}.`,
    "Title": title,
    "Authors": authors,
    "Year": year,
    "Venue": venue,
    "Publication type": pubType,
    "Peer-reviewed status": peerReview(status !== NR ? status : pubType, id),
    "Publication history notes": publicationHistory,
    "URL": url,
    "DOI": doi,
    "Citation count, source, and retrieval date": citationCount(sourceRecords),
    "Core or adjacent classification": cls,
    "Relationship/dependence family": relationship,
    "Research objective": objective,
    "Claimed qualitative methodology": claimed,
    "Actual operationalized methodology": actual,
    "Inductive, deductive, or hybrid": inductiveOverrides[id] ?? (coreIds.has(id) ? NR : "not applicable — adjacent methodological/evaluation source"),
    "Domain": domain,
    "Dataset name": dataset,
    "Public or restricted data": dataAccess(sourceRecords),
    "Number of documents": first(sourceRecords, ["number_documents"]) !== NR ? first(sourceRecords, ["number_documents"]) : documentCounts(dataset),
    "Number of participants": first(sourceRecords, ["number_participants"]) !== NR ? first(sourceRecords, ["number_participants"]) : participantCounts(dataset),
    "Approximate corpus size": dataset,
    "Document length": first(sourceRecords, ["document_length"]) !== NR ? first(sourceRecords, ["document_length"]) : documentLength(dataset),
    "Language": first(sourceRecords, ["language"]) !== NR ? first(sourceRecords, ["language"]) : language(`${dataset} ${ethics}`),
    "Sensitive-data status": sensitiveStatusOverrides[id] ?? sensitiveStatus(sourceRecords),
    "Model family": models,
    "Exact model/version": exactModels,
    "Prompting strategy": prompts,
    "Fine-tuning or adaptation": fineTune,
    "Single-agent or multi-agent": architectureType(sourceRecords),
    "Agent roles": agentRoles(sourceRecords),
    "Human role": human,
    "Unit of analysis": combine(sourceRecords, ["chunking", "unit_of_analysis"]),
    "Generated outputs": tasks,
    "Evidence/provenance mechanism": evidenceMechanism(sourceRecords),
    "Baselines": baselineOverrides[id] ?? combine(sourceRecords, ["baselines"]),
    "Number of runs or seeds": runs !== NR ? runs : runFallback,
    "Automatic metrics": metrics,
    "Human-evaluation design": humanDesign,
    "Number and expertise of evaluators": evaluatorDescription(humanDesign),
    "Inter-rater reliability": irr,
    "Statistical analysis": statistics,
    "Principal results": principal,
    "Efficiency or cost results": efficiency !== NR ? efficiency : efficiencyFallback,
    "Ethics and privacy treatment": ethics,
    "Reproducibility resources": repro,
    "Author-reported limitations": limitations,
    "Additional validity concerns": validityConcerns,
    "Relationship to prior papers": relationship,
    "Relevance to the proposed ARR project": relevance(id, cls, sourceRecords)
  };
  for (const column of columns) if (isMissing(row[column])) row[column] = NR;
  records.push(row);
}

if (Object.keys(dorfelExtraction.record).length !== columns.length ||
    columns.some(column => !(column in dorfelExtraction.record))) {
  throw new Error("Dörfel supplemental extraction does not match the 52-column master schema");
}
records.push({...dorfelExtraction.record});

for (const candidate of citationChainIncluded) {
  const record = candidate.master_ready_record;
  if (Object.keys(record).length !== columns.length || columns.some(column => !(column in record))) {
    throw new Error(`Citation-chain extraction ${candidate.candidate_id} does not match the 52-column master schema`);
  }
  records.push(structuredClone(record));
}

records.sort((a, b) => {
  const ac = a["Core or adjacent classification"].startsWith("core") ? 0 : 1;
  const bc = b["Core or adjacent classification"].startsWith("core") ? 0 : 1;
  return ac - bc || Number(b.Year === NR ? 0 : b.Year) - Number(a.Year === NR ? 0 : a.Year) || a.Title.localeCompare(b.Title);
});

const dimensions = [
  "Clarity of its qualitative methodology",
  "Appropriateness of its dataset",
  "Transparency of its computational workflow",
  "Strength and independence of its baselines",
  "Adequacy of its human evaluation",
  "Validity of its automatic metrics",
  "Treatment of interpretive plurality",
  "Evidence grounding and traceability",
  "Stability and reproducibility testing",
  "Ethics, privacy, and responsible-research reporting",
  "Availability of data, prompts, code, and model versions",
  "Whether conclusions are proportionate to the evidence"
];

const scoreMap = {
  dai_2023_llm_in_loop:                 [1,1,2,1,1,1,0,1,1,1,2,1],
  parfenova_2025_inductive_coding:      [1,1,2,1,1,1,1,1,1,1,1,1],
  parfenova_pfeffer_2025_ensemble:      [1,1,1,1,0,0,0,0,1,1,0,1],
  hicode_2025:                          [1,2,2,2,1,1,1,1,1,1,2,1],
  quallm_2025:                          [1,2,1,1,1,1,0,2,0,2,1,1],
  thematic_lm_2025:                     [1,1,1,0,0,0,0,1,1,0,0,0],
  lloom_2024:                           [1,2,2,2,1,1,1,1,1,1,2,1],
  details_2025:                         [1,1,1,0,1,0,1,1,0,2,1,1],
  chen_2026_open_code_metrics:          [2,1,2,2,1,1,2,1,2,2,2,2],
  centaurta_2026:                       [1,1,1,1,1,0,1,1,1,2,1,1],
  auto_ta_2025:                         [0,1,0,1,0,0,0,1,1,1,0,0],
  sft_ta_2025:                          [0,0,0,1,1,0,0,1,1,1,0,0],
  tama_2026:                            [1,1,1,1,1,0,0,1,1,1,1,1],
  yi_2026_provenance_refinement:        [1,2,1,1,0,0,0,2,1,1,0,0],
  llm_ta_2025:                          [1,1,1,1,1,0,0,1,1,1,2,1],
  qualanalyzer_2026:                    [1,1,2,0,0,1,0,2,2,1,2,1],
  jowsey_2025_frankenstein:             [1,2,1,1,0,1,1,2,0,1,1,2],
  hill_2026_healthcare:                 [0,0,2,2,2,1,1,2,0,2,2,2],
  montes_2025_prompting:                [1,1,1,0,1,0,0,1,0,1,0,1],
  perez_2026_icr:                       [2,1,1,1,1,0,2,1,2,0,1,1],
  alghamdi_2026_convergence:            [1,1,1,1,0,0,0,1,2,0,2,1],
  ashwin_2025_serious_bias:             [2,2,2,2,2,1,1,1,2,2,2,2],
  mathis_2024_open_source:              [1,1,1,1,1,0,0,1,1,2,1,1],
  prescott_2024_genai_human:            [1,0,1,1,1,0,0,1,0,2,1,2],
  li_2024_gpt4_human:                   [1,1,1,1,1,1,0,1,2,2,0,2],
  bijker_2024_content_analysis:         [2,2,2,1,2,1,0,1,2,2,2,2],
  bennis_2025_nine_models:              [1,1,1,1,1,0,0,1,2,2,1,1],
  vikan_2025_reflexive:                 [2,1,2,0,2,1,2,2,2,2,1,2],
  grover_2026_preferences:              [1,1,2,1,0,0,0,1,2,2,1,2],
  bai_2026_three_datasets:              [1,2,2,2,0,0,0,2,0,1,1,1],
  turner_2026_dementia_trials:          [2,1,2,2,1,1,0,2,2,1,2,1],
  sakaguchi_2025_japanese:              [2,1,2,1,2,1,2,1,2,2,1,2],
  wachinger_2024_prompts:               [1,0,2,1,1,2,1,2,2,1,0,2],
  zhu_2026_trauma:                      [2,2,2,1,1,1,1,2,2,2,2,2]
  ,matveyenko_2026_muse:                [1,2,2,2,1,1,1,2,2,1,2,1]
  ,katz_2026_gatos:                     [2,1,2,1,1,0,0,1,0,2,2,2]
  ,liu_2026_agreement_not_quality:      [2,1,2,2,2,2,2,1,2,2,1,2]
  ,liu_2026_human_llm_inductive:        [2,2,2,1,2,1,1,2,1,2,2,2]
  ,camporese_2026_security_comments:    [2,1,2,2,2,2,0,2,1,1,2,2]
  ,liu_2026_policy_workflow:            [1,2,2,2,2,1,1,1,1,2,1,2]
  ,jeyaganthan_2026_corefine:           [2,0,2,1,1,1,2,2,1,0,1,2]
};

function positiveParts(value) {
  if (isMissing(value)) return [];
  const parts = flatten(value).split(/\s*\|\s*|;\s+/).map(v => v.trim()).filter(Boolean);
  const positive = parts.filter(v => !/\bnot reported\b|\bnot visible\b|\bnot located\b|\buncertain\b|\bno [^;|]{0,80} reported\b/i.test(v));
  return positive.length ? [...new Set(positive)] : [];
}

function hasPositive(value) {
  return positiveParts(value).length > 0;
}

function snippet(value, max = 210) {
  const parts = positiveParts(value);
  if (!parts.length) return NR;
  let text = parts.join("; ").replace(/\.\s+/g, "; ").replace(/[!?]\s+/g, "; ").replace(/\s+/g, " ").replace(/[.;:,\s]+$/, "").trim();
  if (text.length > max) text = `${text.slice(0, max - 1).trim()}…`;
  return text;
}

function scoreWord(score) {
  return score === 2 ? "Adequate" : score === 1 ? "Partial" : "Absent/inadequate";
}

function auditScores(row, proposed) {
  const scores = [...proposed];
  const cap = (i, maximum) => { scores[i] = Math.min(scores[i], maximum); };

  const claimed = hasPositive(row["Claimed qualitative methodology"]);
  const actual = hasPositive(row["Actual operationalized methodology"]);
  if (!claimed && !actual) scores[0] = 0;
  else if (!claimed || !actual) cap(0, 1);

  if (!hasPositive(row["Approximate corpus size"])) scores[1] = 0;

  const workflowParts = [row["Exact model/version"], row["Prompting strategy"], row["Single-agent or multi-agent"]].filter(hasPositive).length;
  if (!workflowParts) scores[2] = 0;
  else if (workflowParts < 2) cap(2, 1);

  if (!hasPositive(row.Baselines)) scores[3] = 0;
  else if (/no (?:controlled|experimental|independent|human)|conceptual|published human reference|historical analysis|reference leakage/i.test(row.Baselines)) cap(3, 1);

  const human = row["Human-evaluation design"];
  if (!hasPositive(human) || /^(?:none|mostly automated)|no independent (?:human|analyst)|none in (?:the )?main/i.test(human)) scores[4] = 0;
  else if (!hasPositive(row["Number and expertise of evaluators"])) cap(4, 1);

  if (!hasPositive(row["Automatic metrics"])) scores[5] = 0;

  const pluralityText = `${row.Title}; ${row["Claimed qualitative methodology"]}; ${row["Actual operationalized methodology"]}; ${human}; ${row["Author-reported limitations"]}; ${row["Additional validity concerns"]}; ${row["Principal results"]}`;
  const explicitPlurality = /reflexiv|plural|no-gold|not ground truth|alternative interpretation|multiple valid|situated|cultural|low-frequency|researcher override|division.of.labor/i.test(pluralityText);
  const weakPlurality = explicitPlurality || /independent|blinded|disagreement|multiple analysts?|human.{0,12}(?:LLM|machine)|(?:LLM|machine).{0,12}human/i.test(pluralityText);
  if (!weakPlurality) scores[6] = 0;
  else if (!explicitPlurality) cap(6, 1);

  if (!hasPositive(row["Evidence/provenance mechanism"])) scores[7] = 0;
  else if (!/(?:ID|ledger|graph|audit|provenance)/i.test(row["Evidence/provenance mechanism"])) cap(7, 1);

  if (!hasPositive(row["Number of runs or seeds"])) scores[8] = 0;

  if (!hasPositive(row["Ethics and privacy treatment"])) scores[9] = 0;
  else if (/\bnot reported\b/i.test(row["Ethics and privacy treatment"])) cap(9, 1);

  const resources = snippet(row["Reproducibility resources"], 500);
  const versions = snippet(row["Exact model/version"], 500);
  const usableResources = resources !== NR && !/^(?:no code|code not located|data\/code unavailable)/i.test(resources);
  if (!usableResources && versions === NR) scores[10] = 0;
  else if (!usableResources || versions === NR) cap(10, 1);
  else if (/\bnot reported\b|\bmissing\b|\bunsnapshotted\b/i.test(row["Exact model/version"])) cap(10, 1);

  const limitations = hasPositive(row["Author-reported limitations"]);
  const concerns = hasPositive(row["Additional validity concerns"]);
  if (!limitations && !concerns) scores[11] = 0;
  else if (!limitations) cap(11, 1);

  return scores;
}

function rationale(dimension, score, row) {
  const prefix = scoreWord(score);
  switch (dimension) {
    case dimensions[0]:
      if (!hasPositive(row["Claimed qualitative methodology"]) && !hasPositive(row["Actual operationalized methodology"])) return `Absent/inadequate: neither a qualitative-methodology claim nor an operationalized qualitative procedure is reported in the extracted evidence.`;
      if (score === 0) return `Absent/inadequate: the reported method claim (${snippet(row["Claimed qualitative methodology"], 95)}) is not adequately aligned with the operationalized procedure (${snippet(row["Actual operationalized methodology"], 125)}).`;
      if (!hasPositive(row["Claimed qualitative methodology"]) || !hasPositive(row["Actual operationalized methodology"])) return `Partial: only one side of the method claim-to-operation link is documented (${snippet(`${row["Claimed qualitative methodology"]} | ${row["Actual operationalized methodology"]}`, 220)}).`;
      return `${prefix}: the reported method claim is ${snippet(row["Claimed qualitative methodology"], 100)}, and the operationalized procedure is ${snippet(row["Actual operationalized methodology"], 145)}.`;
    case dimensions[1]:
      if (!hasPositive(row["Approximate corpus size"])) return `Absent/inadequate: the extracted evidence does not report a dataset or corpus basis that can be assessed for appropriateness.`;
      if (score === 0) return `Absent/inadequate: the reported dataset (${snippet(row["Approximate corpus size"], 205)}) is too limited or mismatched for the stated claim.`;
      return `${prefix}: dataset appropriateness was assessed against ${snippet(row["Approximate corpus size"], 210)}.`;
    case dimensions[2]:
      if (![row["Exact model/version"], row["Prompting strategy"], row["Single-agent or multi-agent"]].some(hasPositive)) return `Absent/inadequate: model/version, prompting, and workflow architecture are not reported in the extracted evidence.`;
      if (score === 0) return `Absent/inadequate: the reported details (${snippet(`${row["Exact model/version"]} | ${row["Prompting strategy"]} | ${row["Single-agent or multi-agent"]}`, 215)}) are insufficient to reproduce the computational workflow.`;
      return `${prefix}: the computational workflow reports ${snippet(`${row["Exact model/version"]} | ${row["Prompting strategy"]} | ${row["Single-agent or multi-agent"]}`, 230)}.`;
    case dimensions[3]:
      if (!hasPositive(row.Baselines)) return `Absent/inadequate: no baseline or independent comparator is reported in the extracted evidence.`;
      if (score === 0) return `Absent/inadequate: the reported comparators (${snippet(row.Baselines, 205)}) do not provide a sufficiently strong or independent baseline.`;
      return `${prefix}: the reported comparators are ${snippet(row.Baselines, 210)}.`;
    case dimensions[4]:
      if (!hasPositive(row["Human-evaluation design"]) || /^(?:none|mostly automated)|no independent (?:human|analyst)|none in (?:the )?main/i.test(row["Human-evaluation design"])) return `Absent/inadequate: no independent human evaluation adequate for the stated claim is reported in the extracted evidence.`;
      if (score === 0) return `Absent/inadequate: the reported human involvement (${snippet(row["Human-evaluation design"], 205)}) lacks sufficient independence, scale, or evaluator documentation for the stated claim.`;
      return `${prefix}: the human-evaluation design reports ${snippet(`${row["Human-evaluation design"]} | ${row["Number and expertise of evaluators"]}`, 230)}.`;
    case dimensions[5]:
      if (!hasPositive(row["Automatic metrics"])) return `Absent/inadequate: no automatic metric is reported in the extracted evidence, so its construct validity cannot be established.`;
      if (score === 0) return `Absent/inadequate: the reported metrics (${snippet(row["Automatic metrics"], 190)}) are not validated for the study's interpretive construct.`;
      if (!hasPositive(row["Additional validity concerns"])) return `${prefix}: automatic evaluation uses ${snippet(row["Automatic metrics"], 205)}, but the extraction documents no separate construct-validity analysis.`;
      return `${prefix}: automatic evaluation uses ${snippet(row["Automatic metrics"], 175)}, assessed against the stated validity concerns ${snippet(row["Additional validity concerns"], 95)}.`;
    case dimensions[6]:
      if (score === 2) return `Adequate: the extracted evidence explicitly addresses reflexivity, alternative interpretations, disagreement, cultural nuance, or the limits of consensus as ground truth.`;
      if (score === 1) return `Partial: the design includes multiple analysts, systems, or disagreements, but only partly operationalizes interpretive plurality.`;
      return `Absent/inadequate: the extracted evidence does not document a procedure for preserving or evaluating alternative interpretations.`;
    case dimensions[7]:
      if (!hasPositive(row["Evidence/provenance mechanism"])) return `Absent/inadequate: no source-to-code or source-to-theme traceability mechanism is reported in the extracted evidence.`;
      return `${prefix}: evidence grounding is implemented through ${snippet(row["Evidence/provenance mechanism"], 220)}.`;
    case dimensions[8]:
      if (!hasPositive(row["Number of runs or seeds"])) return `Absent/inadequate: no repeated-run, seed, or sensitivity design is reported in the extracted evidence.`;
      if (score === 0) return `Absent/inadequate: the reported run design (${snippet(row["Number of runs or seeds"], 205)}) is insufficient to establish stability.`;
      if (/^\d+$/.test(row["Number of runs or seeds"].trim())) return `${prefix}: stability evidence comprises ${row["Number of runs or seeds"].trim()} repeated runs as recorded in the extraction.`;
      return `${prefix}: stability or sensitivity evidence comprises ${snippet(row["Number of runs or seeds"], 220)}.`;
    case dimensions[9]:
      if (!hasPositive(row["Ethics and privacy treatment"])) return `Absent/inadequate: ethics, privacy, and responsible-research safeguards are not reported in the extracted evidence.`;
      return `${prefix}: ethics, privacy, and governance reporting covers ${snippet(row["Ethics and privacy treatment"], 220)}.`;
    case dimensions[10]:
      if (!hasPositive(row["Reproducibility resources"]) && !hasPositive(row["Exact model/version"])) return `Absent/inadequate: reusable materials and exact model/version information are not reported in the extracted evidence.`;
      return `${prefix}: reported reproducibility assets and version information are ${snippet(`${row["Reproducibility resources"]} | ${row["Exact model/version"]}`, 230)}.`;
    case dimensions[11]:
      if (!hasPositive(row["Author-reported limitations"]) && !hasPositive(row["Additional validity concerns"])) return `Absent/inadequate: the extracted evidence reports neither author limitations nor a basis for judging claim proportionality.`;
      if (score === 0) return `Absent/inadequate: the reported limitations and validity concerns are not adequately reflected in the scope of the study's conclusions.`;
      if (!hasPositive(row["Author-reported limitations"])) return `Partial: proportionality can only be checked against reviewer-identified concerns (${snippet(row["Additional validity concerns"], 200)}) because author-reported limitations are unavailable in the extraction.`;
      if (!hasPositive(row["Additional validity concerns"])) return `${prefix}: claim proportionality was assessed against the reported limitations ${snippet(row["Author-reported limitations"], 205)}.`;
      return `${prefix}: claim proportionality was assessed against author limitations ${snippet(row["Author-reported limitations"], 115)} and reviewer-identified concerns ${snippet(row["Additional validity concerns"], 115)}.`;
    default:
      return `${prefix}: see the corresponding extraction fields.`;
  }
}

const qualityScores = records
  .filter(row => row["Core or adjacent classification"].startsWith("core"))
  .map(row => {
    if (row["Paper ID"] === dorfelExtraction.quality_score["Paper ID"]) {
      return structuredClone(dorfelExtraction.quality_score);
    }
    const chainCandidate = citationChainIncluded.find(candidate => candidate.quality_score["Paper ID"] === row["Paper ID"]);
    if (chainCandidate) return structuredClone(chainCandidate.quality_score);
    const proposed = scoreMap[row["Paper ID"]];
    if (!proposed || proposed.length !== dimensions.length) throw new Error(`Missing/invalid score vector for ${row["Paper ID"]}`);
    const scores = auditScores(row, proposed);
    const dimensionScores = {};
    dimensions.forEach((dimension, index) => {
      dimensionScores[dimension] = {score: scores[index], rationale: rationale(dimension, scores[index], row)};
    });
    return {
      "Paper ID": row["Paper ID"],
      "Title": row.Title,
      "Core or adjacent classification": row["Core or adjacent classification"],
      "Dimension scores": dimensionScores,
      "Total": scores.reduce((a, b) => a + b, 0),
      "Interpretation caution": "The total is a compact audit aid, not a ranking of study quality; dimensions must be interpreted individually against each paper's stated claim."
    };
  });

const malformed = [];
const seenDois = new Map();
const seenTitles = new Map();
for (const row of records) {
  const rowKeys = Object.keys(row);
  if (rowKeys.length !== columns.length || columns.some(c => !rowKeys.includes(c))) malformed.push(row["Paper ID"]);
  for (const column of columns) {
    if (typeof row[column] !== "string" || row[column].trim() === "") malformed.push(`${row["Paper ID"]}:${column}`);
  }
  const normalizedTitle = row.Title.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  if (seenTitles.has(normalizedTitle)) malformed.push(`duplicate-title:${seenTitles.get(normalizedTitle)}:${row["Paper ID"]}`);
  seenTitles.set(normalizedTitle, row["Paper ID"]);
  if (row.DOI !== NR) {
    const normalizedDoi = row.DOI.toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//, "");
    if (seenDois.has(normalizedDoi)) malformed.push(`duplicate-doi:${seenDois.get(normalizedDoi)}:${row["Paper ID"]}`);
    seenDois.set(normalizedDoi, row["Paper ID"]);
  }
  if (/preprint|manuscript/i.test(row["Publication type"]) && row["Peer-reviewed status"] === "peer reviewed") {
    malformed.push(`preprint-status-contradiction:${row["Paper ID"]}`);
  }
}
for (const quality of qualityScores) {
  const entries = Object.entries(quality["Dimension scores"]);
  if (entries.length !== dimensions.length || dimensions.some(d => !(d in quality["Dimension scores"]))) malformed.push(`quality-dimensions:${quality["Paper ID"]}`);
  const recomputed = entries.reduce((sum, [, value]) => sum + value.score, 0);
  if (recomputed !== quality.Total) malformed.push(`quality-total:${quality["Paper ID"]}`);
  for (const [dimension, value] of entries) {
    if (![0, 1, 2].includes(value.score) || typeof value.rationale !== "string" || !value.rationale.trim()) malformed.push(`quality-value:${quality["Paper ID"]}:${dimension}`);
    if (value.score === 2 && /\bnot reported\b|\bno [^.;]{0,100} reported\b/i.test(value.rationale)) malformed.push(`quality-contradiction:${quality["Paper ID"]}:${dimension}`);
  }
}
if (malformed.length) throw new Error(`Malformed records: ${malformed.join(", ")}`);
if (records.length < 55) throw new Error(`Expected at least 55 deduplicated records, got ${records.length}`);
if (qualityScores.length !== coreIds.size) throw new Error(`Expected ${coreIds.size} quality records, got ${qualityScores.length}`);

const output = {
  metadata: {
    title: "Master evidence extraction for LLM/NLP-assisted qualitative analysis scoping review",
    search_cutoff: CUTOFF,
    generated_from: [
      "research/core_systems.json",
      "research/evaluation_methodology.json",
      "research/validity_ethics.json",
      "research/fulltext/latest/matveyenko_2026_muse.txt",
      "research/fulltext/latest/gatos_2026.txt",
      "research/fulltext/latest/2607.28890.txt",
      "research/fulltext/latest/2607.28889.txt",
      "research/fulltext/latest/2604.10834.txt",
      "research/fulltext/latest/2604.04479.txt",
      "research/fulltext/latest/2604.19309.txt",
      "research/fulltext/latest/zhu_2026_trauma.txt",
      "research/dorfel_2026_evidence.json",
      "research/fulltext/latest/education_2026_inductive_coding.txt",
      "research/citation_chaining.json"
    ],
    deduplication: "Normalized DOI (including arXiv DOI reconstruction from official arXiv URLs); source ID used only when DOI was unavailable.",
    missing_value: NR,
    extraction_columns: columns,
    extraction_column_count: columns.length,
    record_count: records.length,
    core_record_count: qualityScores.length,
    adjacent_record_count: records.length - qualityScores.length,
    quality_scoring: "0 = absent/inadequate, 1 = partial, 2 = adequate for the study's stated claim.",
    quality_total_caution: "Totals are not study rankings; interpret every dimension separately.",
    review_note: "This is a consolidated single-reviewer extraction. Source records explicitly distinguish author-reported information from reviewer-identified validity concerns where the source extraction allowed that distinction. MoverScore, BLEURT, and G-Eval were omitted as lower-priority adjacent metric-origin records; cutoff-eligible full-text-verified core reports were retained even when resolving omissions increased the corpus beyond the initially requested 55–70-record range. Ronaghi et al. 2026 is retained only as an adjacent bibliographic lead because detailed full-text extraction was not verified.",
    quality_audit_note: "Every core-paper score was evidence-gated after the initial expert score vector: an absent supporting extraction field forces 0, partial documentation caps the score at 1, and every rationale cites the corresponding extracted evidence."
  },
  evidence_records: records,
  quality_dimensions: dimensions,
  quality_scores: qualityScores
};

fs.writeFileSync(path.join(ROOT, "research/master_evidence.json"), `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(JSON.stringify({records: records.length, core: qualityScores.length, adjacent: records.length - qualityScores.length, columns: columns.length}, null, 2));
