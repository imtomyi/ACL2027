# Core computational systems for LLM-assisted qualitative coding and thematic analysis

**Evidence report for the systematic scoping review**  
**Search and verification date:** 2026-08-24  
**Coverage:** publications and public manuscripts available by 2026-08-24  
**Track:** core systems, methods, and evaluation frameworks  

## Executive finding

The literature contains several genuinely different kinds of system that are too often grouped together: (1) one-pass open-code generators; (2) codebook-induction and hierarchical clustering pipelines; (3) mixed-initiative workbenches; (4) autonomous, role-prompted or multi-agent theme generators; and (5) evaluation frameworks. Most papers call their task *thematic analysis* or *inductive coding*, but operationalize it as generating labels for pre-segmented text, merging them by embedding or LLM similarity, and comparing the resulting labels/themes with a consensus codebook. That is closer to codebook/coding-reliability TA than to reflexive TA. Human interpretive engagement ranges from continuous (Dai; LLooM; DeTAILS; TAMA; CentaurTA) to setup-only or optional (HICode; Thematic-LM; Auto-TA).

The strongest recurring validity threats are: unsnapshotted proprietary models; same-model or same-family generation and judging; very small human evaluations; lexical overlap used as a proxy for qualitative trustworthiness; gold-codebook assumptions that conflict with inductive pluralism; ambiguous or nonstandard metrics; undisclosed prompts/hyperparameters; and dependence among studies reusing the same dataset. In particular, **LLM-TA, Auto-TA, SFT-TA, TAMA, and the 2026 provenance/refinement paper reuse the same nine AAOCA focus-group transcripts and 12 human themes and must not be counted as independent dataset-level replications**.

## Reproducible search record

Searches used exact seed-title lookup, controlled-field database queries, backward references, and forward citation/title/author searching. Official publisher or repository pages were preferred; PDFs supplied by the review team were inspected in full. Counts below are database-returned records before screening, not eligible-study counts.

### PubMed (search date 2026-08-24)

| ID | Exact query | Returned |
|---|---|---:|
| PUBMED_Q1 | `(("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "generative AI"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "theme generation"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 229 |
| PUBMED_Q2 | `(("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative coding"[Title/Abstract] OR "inductive coding"[Title/Abstract] OR "open coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 8 |
| PUBMED_Q3 | `(("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative content analysis"[Title/Abstract] OR "qualitative data analysis"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 25 |
| PUBMED_Q4 | `(("human-AI collaboration"[Title/Abstract] OR "human-in-the-loop"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative research"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 47 |
| PUBMED_Q5 | `(("multi-agent"[Title/Abstract] OR "LLM agent"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 2 |
| PUBMED_Q6 | `(("codebook induction"[Title/Abstract] OR "codebook generation"[Title/Abstract] OR "codebook refinement"[Title/Abstract]) AND (LLM[Title/Abstract] OR "large language model"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 0 |
| PUBMED_Q7 | `(("clinical transcript"[Title/Abstract] OR "patient interview"[Title/Abstract]) AND ("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "automated coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])` | 1 |

PubMed returned 295 unique PMIDs after deduplication. The record-level export is `research/pubmed_search_records.json`.

### ACL Anthology and Crossref

ACL Anthology literal-title searches returned: Dai title 1; Parfenova proposal 3; Parfenova NAACL title 4; HICode 0; QuaLLM 0; Thematic-LM 0; Chen 0. A supplemental title search for thematic/qualitative coding, QDA, inductive coding, or open codes returned 12, producing 13 unique ACL records. Zero does not mean absence: the local literal index did not normalize all punctuation/token forms. Full queries and records are in `research/acl_anthology_search_records.json`.

Crossref `query.title` searches (100 records retained per query) returned fuzzy totals of 4,486,053; 2,166,019; 5,301,761; 4,336,991; 3,396,027; 362,153; and 2,945,555 for the seven seed-title strings. These enormous totals are Crossref relevance-search totals, **not exact matches or eligible hits**. There were 688 unique items among the first 100 results per query. Exact query strings and results are in `research/crossref_search_records.json`.

### Other title/citation searches

Exact-title and citation-chain queries included `"HICode: Hierarchical Inductive Coding with LLMs"`, `"QuaLLM" LLM framework online forums`, `"Thematic-LM"`, `"DeTAILS" thematic analysis`, `"A Computational Method for Measuring Open Codes"`, `"Concept Induction" LLooM`, `"CentaurTA"`, `"SCALE" qualitative coding LLM`, `"CollabCoder"`, `"CoAIcoder"`, `"LOGOS" grounded theory`, and the five supplied-PDF titles. The web interfaces used did not expose stable result counts; count is therefore **not reported** rather than estimated. Search date was 2026-08-24. ArXiv, OpenReview, and the deduplicated union are preserved in `research/arxiv_search_records.json`, `research/openreview_search_records.json`, and `research/search_union_deduplicated.json`.

## Supplied PDFs and version control

| Supplied file | Identified work | Status at cutoff | Key version caveat |
|---|---|---|---|
| `2506.23998v2.pdf` | Yi et al., **Auto-TA** | arXiv:2506.23998v2, 2025-08-08 | RLHF/PPO is proposed/work in progress; no RL results. |
| `2509.14597v2.pdf` | Yi et al., **Position: Thematic Analysis of Unstructured Clinical Transcripts with LLMs** | arXiv:2509.14597v2, workshop manuscript, 2025-09-28 | Position/review paper, not a primary system evaluation; archival proceedings status not verified. |
| `2509.17167v1.pdf` | Yi et al., **SFT-TA** | arXiv:2509.17167v1; ML4H 2025 manuscript | PDF says PMLR `XXX`; a final PMLR volume record was not verified. |
| `2603.08989v1.pdf` | Yi et al., **Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance** | arXiv:2603.08989v1, 2026-03-09 | No peer-reviewed venue verified. |
| `3828752 (1).pdf` | Xu et al., **TAMA** | ACM Transactions on Computing for Healthcare, 2026, DOI [10.1145/3828752](https://doi.org/10.1145/3828752) | Published journal article; same AAOCA corpus/reference themes as several preprints. |

## Comparative evidence map

| Work | What is actually operationalized | Human role | Evaluation/data | Publication/resources |
|---|---|---|---|---|
| Dai et al. 2023 | Iterative human–LLM codebook creation and deductive assignment | Human coder supplies examples, edits with rationales, accepts/stops; third coder evaluates | Two survey datasets; kappa, embeddings, accuracy/recall | EMNLP Findings; [paper](https://aclanthology.org/2023.findings-emnlp.669/), [code](https://github.com/sjdai/LLM-thematic-analysis) |
| Parfenova et al. 2024 | Proposed open/axial coding research agenda, not implemented evaluation | Experts proposed for labels/evaluation | Dataset/model sizes/results not reported | ACL SRW; [paper](https://aclanthology.org/2024.acl-srw.17/) |
| Parfenova et al. 2025 | Supervised short-label generation for presegmented quotes | Three researchers in 15-item evaluation | 1,000 quote–code pairs; ROUGE/BERTScore; alpha | NAACL Findings; [paper](https://aclanthology.org/2025.findings-naacl.361/) |
| Parfenova & Pfeffer 2025 | Candidate-code ensemble, moderator selection, embedding-based reuse | Small human correlation check; number of experts not reported | 100 reviews; composite gold-dependent score | ACL Findings; [paper](https://aclanthology.org/2025.findings-acl.563/) |
| HICode 2025 | Fine labels followed by repeated hierarchical LLM synthesis | Goal/background input; no analyst in evaluated pipeline | 4 corpora, up to 163,173 segments; theme/segment P/R | EMNLP; [paper](https://aclanthology.org/2025.emnlp-main.1580/), [code](https://github.com/mianzg/HICode) |
| QuaLLM 2025 | Concern extraction, classification, aggregation/ranking, prevalence estimation | Defines top categories and representative quotes | 65,377 posts + 1,392,776 comments; small factuality/classification audits | NAACL Findings; [paper](https://aclanthology.org/2025.findings-naacl.74/) |
| Thematic-LM 2025 | Autonomous coder/aggregator/reviewer agents with adaptive codebook | No independent analyst in main pipeline | Dreaddit and climate Reddit corpora; GPT-4o self-evaluation, ROUGE stability | WWW; [DOI](https://doi.org/10.1145/3696410.3714595); code not found |
| LLooM 2024 | Mixed-initiative concept induction: filter, cluster, synthesize, score, loop | Analyst inspects/edits/merges/splits/rescores | Two benchmarks + four scenarios + 2 expert sessions | CHI; [DOI](https://doi.org/10.1145/3613904.3642830), [code](https://github.com/michelle123lam/lloom) |
| DeTAILS 2025 | Interactive RAG-assisted codebook, global coding, clustering, themes | Analyst revises at every stage | Expanded preprint: 18 researchers, 30 Reddit threads each | CUI short paper [DOI](https://doi.org/10.1145/3719160.3735657); expanded arXiv; [code](https://github.com/DaemonOnCode/DeTAILS) |
| Chen et al. 2026 | Team-relative measurement of aggregate open-code spaces, not code generation | Four human and four prompted machine coders provide codebooks | First 127 community messages; simulations and 10-run stability | ACL Findings; [paper](https://aclanthology.org/2026.findings-acl.2073/) |
| CentaurTA 2026 | Actor–critic code/theme generation plus feedback-to-prompt-principle optimization | Six paid participants provide iterative feedback/rubric ratings | Three corpora, 1,944 sentences; rubric and judge metrics | ACL Findings; [paper](https://aclanthology.org/2026.findings-acl.778/), [code](https://github.com/Tom-Owl/CentaurTA) |
| Auto-TA 2025 | Sequential role-prompted code/theme/critic pipeline | None in main run; optional future RLHF | Nine AAOCA groups; overlap/stability/transfer metrics | arXiv only; no code located |
| SFT-TA 2025 | Fine-tuned coding/theme agents inside a sequential multi-agent pipeline | Removes off-topic output; four human raters | Same AAOCA corpus; automatic + human ratings | arXiv/ML4H manuscript; data/code unavailable |
| TAMA 2026 | Sequential generation/evaluation/refinement roles, with expert stopping | Cardiac expert provides background/rubric, reviews each iteration | Same AAOCA corpus; nonstandard pair-threshold and coverage metrics | ACM TCH; [DOI](https://doi.org/10.1145/3828752), [code](https://github.com/Charlie-Yi-SJ/TAMA) |
| Yi et al. 2026 provenance | Graph-based codebook induction/refinement with quote-to-theme ledger | Pipeline mostly automated; independent human validation absent | Five corpora; 5 repetitions; LLM-scored composite | arXiv only; code/prompts not located |
| LLM-TA 2025 | Sequential coding, merging, theme generation on clinical transcripts | Clinician-derived reference themes used for evaluation | Same AAOCA corpus; overlap and trustworthiness proxies | arXiv/workshop; [arXiv](https://arxiv.org/abs/2502.01620), [code](https://github.com/jiaweixu98/LLM-TA) |

## Detailed evidence cards

### Dai, Shih-Chieh; Xiong, Aiping; Ku, Lun-Wei (2023), “LLM-in-the-loop: Leveraging Large Language Model for Thematic Analysis”

- **Verified citation/status:** Findings of EMNLP 2023, pp. 9993–10001, DOI [10.18653/v1/2023.findings-emnlp.669](https://doi.org/10.18653/v1/2023.findings-emnlp.669).
- **Claim versus operation:** framed as thematic analysis; operationally, a human and machine iteratively build a relatively stable codebook and then assign codes. This is codebook/coding-reliability TA rather than fully reflexive TA.
- **Architecture/task:** after familiarization, the human coder supplies 4–8 in-context examples; `gpt-3.5-turbo-16k` generates fine-grained codes and groups themes. The human edits and gives rationales; the model agrees/disagrees; iteration ends when the human is satisfied. Human, machine, and an independent third coder then apply the codebook. No agent orchestration.
- **Prompting/settings:** few-shot in-context prompts; temperature 0; remaining defaults; full prompts in Appendix D. Model snapshot not reported.
- **Data:** Music Shuffle: 397 participants/four questions, with 35 answers to the first question analyzed. Password Manager: 277 participants/eight questions; 280 answers to one question; 100 used for codebook development, followed by 20 seen and 20 unseen cases.
- **Metrics/results:** human–machine kappa .87 (Music) and .81 (Password) versus .66/.77 against original-author labels. Third-coder–machine kappa .54/.47; third-coder–human .62/.43. Password seen/unseen kappa .80/.82. Embedding cosine (`text-embedding-ada-002`) .8864/.8895; accuracy .84/.83; recall .72/.87. Error audit: ambiguity 5/22 and 9/30, granularity 8/22 and 7/30, distinction 9/22 and 14/30.
- **Ethics/reproducibility/limitations:** public non-sensitive data; warns about API disclosure and IRB issues. Music data could have appeared in pretraining. Proprietary unsnapshotted model and tiny evaluation samples. Original-author codes are treated as gold despite interpretive plurality. Code is public.
- **Evidence locations:** paper §§3–6, Tables 1–3, Appendix D.

### Parfenova, Angelina; Denzler, Alexander; Pfeffer, Juergen (2024), “Automating Qualitative Data Analysis with Large Language Models”

- **Verified citation/status:** ACL 2024 Student Research Workshop, pp. 83–91, DOI [10.18653/v1/2024.acl-srw.17](https://doi.org/10.18653/v1/2024.acl-srw.17). Peer-reviewed PhD proposal, not a completed system study.
- **Claim versus operation:** proposes grounded-theory-inspired open and axial coding. Open coding would summarize each sentence’s main idea; axial coding would have an LLM group codes using the research goal, hypotheses, interview guide, and theory without fixing the number of categories.
- **Models/prompts/data/results:** several LoRA-fine-tuned LLMs and zero-/few-shot settings are proposed, but exact models, data size, prompts, chunking, agents, hyperparameters, and empirical results are **not reported**.
- **Planned evaluation/human role:** experts create/assess labels; ROUGE/BERTScore for code text, Krippendorff alpha versus expert consensus, and bias-distance measures are proposed. Concept mapping is future work.
- **Ethics/limitations:** discusses anonymization, consent, regulation, bias/fairness/transparency, displacement, opacity, limited data, nuance loss, and environmental cost.
- **Evidence locations:** abstract; §§3–5. The body contains an apparent “quantitative data” typo where context indicates qualitative data.

### Parfenova, Angelina; Marfurt, Andreas; Denzler, Alexander; Pfeffer, Juergen (2025), “Text Annotation via Inductive Coding: Comparing Human Experts to LLMs in Qualitative Data Analysis”

- **Verified citation/status:** Findings of NAACL 2025, pp. 6471–6484, DOI [10.18653/v1/2025.findings-naacl.361](https://doi.org/10.18653/v1/2025.findings-naacl.361).
- **Claim versus operation:** described as inductive/open coding, but operationalized as supervised sequence-to-sequence generation of one short code for an already segmented quote/sentence. Axial/thematic construction is not evaluated.
- **Data:** 600 social-science quote–code pairs across nine sources plus 400 SemEval reviews. Train/test 900/100: social-science 550/50 and SemEval 350/50. There are 680 unique codes overall, 624 train and 94 test. No validation split; hyperparameter choice on training data.
- **Models/settings:** `meta-llama/Meta-Llama-3-8B-Instruct`, `tiiuae/falcon-7b-instruct`, `mistralai/Mistral-7B-Instruct-v0.2`, `lmsys/vicuna-7b-v1.5`, `google/gemma-7b-it`, `TinyLlama/TinyLlama-1.1B-Chat-v1.0`. Zero-shot and 1/3/5-shot. LoRA rank 16, alpha 32, dropout .05 on gate/up/down projections, no bias; `max_new_tokens=15`, temperature .7, top-p .7, one generation. Six prompt variants and punctuation variants are documented.
- **Evaluation/results:** ROUGE and BERTScore. Best reported training/augmented performance is around BERTScore F1 .766 for Falcon/Mistral; TinyLlama five-shot reaches .755. Figure suggests saturation after roughly 100 examples, without inferential statistics. Three researchers code 15 selected sentences, judge difficulty, and rate outputs 1–5; Krippendorff alpha is .20. LLMs do better on easy items, humans on difficult ones, but the evaluation is too small to support broad parity claims.
- **Ethics/reproducibility/limitations:** consent/responsible-use discussion; code and machine-readable data release not reported. Consensus “gold” is questionable given low human agreement.
- **Evidence locations:** §§3–6, Tables 1–3, Figures 2–4, appendices.

### Parfenova, Angelina; Pfeffer, Jürgen (2025), “Measuring What Matters: Evaluating Ensemble LLMs with Label Refinement in Inductive Coding”

- **Verified citation/status:** Findings of ACL 2025, pp. 10803–10816, DOI [10.18653/v1/2025.findings-acl.563](https://doi.org/10.18653/v1/2025.findings-acl.563).
- **Operation:** three smaller LoRA models generate code candidates; moderator models select or create a code; sequential embedding refinement reuses an earlier code above a method-specific threshold. It extends the earlier 1,000-pair setup and evaluates on a separate 100-review set manually coded as reference.
- **Models:** Falcon/Mistral/Llama-family models plus Mixtral 8×7B, Llama 3.3 70B, GPT-4 and GPT-4o moderators/ensembles. Exact proprietary snapshots are not reported. LoRA and generation settings largely follow the NAACL paper.
- **Metric/results:** an equally weighted composite of normalized embedding cosine, METEOR, code-length penalty, and Jensen–Shannon divergence. Refined Mixtral ensemble scores .99 at threshold .7 versus .33 standalone; refined Llama-70B .74 versus .38; it produces 71/53 unique codes versus 47 human codes. GPT-4 refinement falls from .74 to .54. A very small human validation on 10 items yields Spearman .73, p=.039; number of experts is not reported.
- **Caveat:** the composite requires reference labels and is a post-hoc benchmark, not a deployable no-gold validation method. No validation set and unclear threshold-selection basis create optimism risk.
- **Ethics/reproducibility:** anonymized data, bias and oversight discussion; code/data release not reported.
- **Evidence locations:** §§3–6, Tables 2–5, appendices.

### Zhong, Mian; Wang, Pristina; Field, Anjalie (2025), “HICode: Hierarchical Inductive Coding with LLMs”

- **Verified citation/status:** EMNLP 2025, pp. 31060–31078, DOI [10.18653/v1/2025.emnlp-main.1580](https://doi.org/10.18653/v1/2025.emnlp-main.1580).
- **Claim versus operation:** inspired by qualitative inductive coding but explicitly optimized for automation, not replication of human iteration. User supplies background/goal; every segment receives multiple labels of at most five words or “irrelevant”; random batches of 100 labels are repeatedly clustered/synthesized until a maximum iteration or convergence. Long documents are paragraph-segmented. This is targeted hierarchical schema induction.
- **Models/baselines:** main model GPT-4o-mini; ablations use Llama 3.2 3B, Llama 3.1 8B, GPT-4o-mini, GPT-4o, Claude and Mixtral Large (exact Claude/Mixtral versions not reported). Baselines TopicGPT, LLooM, and a custom incremental method use GPT-4o-mini. Five runs. Temperature and embedding model are not reported; prompts are in Appendix A.
- **Data:** Frame 11,903 documents/112,585 paragraphs/15 gold themes; Astro 369 documents/segments/9 themes; Values 100 documents/2,157 snippets/82 themes; OIDA case 3,861 documents/163,173 OCR segments.
- **Metrics/results:** embedding-matched many-to-many theme and segment precision/recall at .4/.45/.5. At .4 HICode theme P/R: Values .96/.57; Astro .53/.51; Frame .68/.81. Human Astro .72/.74 versus TopicGPT .18/.33. Two original Astro annotators recoded three runs each; alpha .31. OIDA generates about 70,000 labels over five clustering iterations, 17 themes, and marks 65,642 segments irrelevant.
- **Human/ethics/limits:** after goal/background setup, no analyst intervenes in the evaluated pipeline, although output navigation is supported. Main limitations: imperfect embedding metrics, plurality of valid schemas, limited domains/model configurations, and prompt/model dependence. Public code.
- **Evidence locations:** §§2–6, Tables 1–5, Appendix A.

### Rao, Varun Nagaraj; Agarwal, Eesha; Dalal, Samantha; Calacci, Dana; Monroy-Hernández, Andrés (2025), “QuaLLM: An LLM-based Framework to Extract Quantitative Insights from Online Forums”

- **Verified citation/status:** Findings of NAACL 2025, pp. 1355–1369, DOI [10.18653/v1/2025.findings-naacl.74](https://doi.org/10.18653/v1/2025.findings-naacl.74).
- **Claim versus operation:** a positivist, quantitative workflow rather than reflexive TA: generate a concern and quote; classify it into human-defined top categories; aggregate/rank five subthemes; classify prevalence.
- **Architecture/settings:** a single GPT-4-Turbo deployment through Azure, snapshot not reported. Five Reddit submissions with comments per call; structured seven-step JSON prompt says not to use outside knowledge. Temperature, seeds, and replicate runs not reported. Researchers define four/five top categories and manually choose representative quotes.
- **Data/results:** 2019–2022 r/UberDrivers and r/LyftDrivers: 65,377 submissions and 1,392,776 comments. Eleven percent API failure; 58,728 concerns retained. Transparency 24,721 (42%), predictability 12,728 (22%), safety 6,144 (10.5%), fairness 4,280 (7%), other 18.5%.
- **Evaluation:** generation reference: 125 submissions + 2,511 comments, jointly coded by two researchers; factuality .55, completeness .78. Classification and prevalence use 100 each, accuracy .74/.82. Appendix instead reports three trained annotators, Fleiss kappa .59/.63 and human–LLM .54/.61; this reporting discrepancy needs clarification. BERTopic on 47,873 concerns yields distinctness .80 and coverage@1 .95/@2 1.00. UMAP: 15 neighbors, 10 dimensions, min-distance 0, cosine, seed 42; BERTopic minimum topic size 100, 1–2 grams, automatic topic count.
- **Cost/ethics/limits:** $1,662.30; 135.12M input and 10.37M output tokens. Public-forum ethics, profanity/API selection bias, misinformation, prompt/model bias, stochasticity, small evaluation, hyperparameter sensitivity, and the positivist trade-off are acknowledged. Code/data resource not reported.
- **Evidence locations:** §§3–7, Tables 1–3, Appendices A–D.

### Qiao, Tingrui; Walker, Caroline; Cunningham, Chris; Koh, Yun Sing (2025), “Thematic-LM: A Multi-Agent Large Language Model Framework for Enhancing Automated Thematic Analysis”

- **Verified citation/status:** The Web Conference 2025, pp. 649–658, DOI [10.1145/3696410.3714595](https://doi.org/10.1145/3696410.3714595), published 2025-04-22.
- **Architecture:** AutoGen with coder, aggregator, and reviewer roles. Coders produce 1–3 codes with representative quote/ID; an aggregator merges; the reviewer maintains an adaptive codebook with codes/quotes/IDs, retrieves the top 10 similar entries using SentenceTransformer embeddings, and merges/updates. For themes, LLMLingua compresses the codebook; theme coders and aggregator synthesize themes. At most 20 quotes are retained per code/theme. Coder-identity prompt variants are tested.
- **Settings/data:** GPT-4o, default temperature 1/top-p 1, JSON mode; main system uses two code coders and two theme coders. Snapshot and random seeds not reported. Three complete runs and a 50/50 split evaluation. Dreaddit has >190,000 posts and the climate Reddit source >4.6M posts/comments, but exact processed counts are not reported.
- **Evaluation/results:** no independent human evaluation. The same GPT-4o family judges quote consistency as “credibility/confirmability”; mean bidirectional ROUGE-1/2 across runs is “dependability” and across random halves is “transferability.” Dreaddit C/D/T: single .63/.45/.41; single+codebook .75/.61/.67; system-1 .92/.81/.86; system-2 .94/.78/.87. Climate: .66/.56/.73; .74/.69/.78; .96/.84/.90; .98/.86/.89.
- **Identity experiment:** human-driven, natural-cycle, progressive, conservative, and Indigenous identities reduce pairwise ROUGE and yield 15 climate themes versus eight without identity. This demonstrates output sensitivity, not validity of represented perspectives; the identities may encode prompt stereotypes.
- **Ethics/reproducibility/limits:** ethics and limitations sections are absent; code release was not located. Unsnapshotted proprietary generator/evaluator, non-independent self-evaluation, weak construct mapping of ROUGE to qualitative trustworthiness, and Reddit-scale processed sample uncertainty.
- **Evidence locations:** ACM full text pp. 649–658, §§3–5, Tables 3–5.

### Lam, Michelle S.; Teoh, Janice; Landay, James A.; Heer, Jeffrey; Bernstein, Michael S. (2024), “Concept Induction: Analyzing Unstructured Text with High-Level Concepts Using LLooM”

- **Verified citation/status:** CHI 2024, DOI [10.1145/3613904.3642830](https://doi.org/10.1145/3613904.3642830). Author PDF and [public code](https://github.com/michelle123lam/lloom) verified.
- **Claim versus operation:** concept induction, not formal Braun–Clarke TA. `Distill` filters exact quotes and summarizes bullets with GPT-3.5; `Cluster` uses `text-embedding-ada-002` and HDBSCAN; `Synthesize` uses GPT-4 to name concepts, specify criteria, and select representative IDs; `Score` uses batched zero-shot multiple choice/rationales with GPT-3.5 or PaLM `chat-bison-001`; optional `Seed` and `Loop` cover missed/generic examples.
- **Settings/chunking:** `gpt-3.5-turbo` and GPT-4 snapshots not reported, temperature 0; prompts in Appendix A. Main induction uses at most 200 items and 20 concepts. No autonomous agents. The workbench lets analysts inspect, edit, add, merge, split, and rescore concepts.
- **Data:** scenarios: 496 toxic-comment cluster items; 405 partisan Facebook posts; 210 UIST abstracts sampled from 1,733; 300 NeurIPS-impact abstracts. Benchmarks: Wikipedia 14,290 items/15 topics, sampled 205; Congressional bills 32,661/28 topics, sampled 213; 10 trials. Synthetic evaluation: four conditions × 40 documents = 160.
- **Metrics/results:** coverage: bills .74 versus GPT-4-Turbo .56; Wikipedia .81 versus GPT-4 .83/Turbo .82. Synthetic specific concepts .71 versus Turbo .55; generic .98 tie. GPT-3.5 judged coverage; manual check of 16 trials has MAE .07. Concept classification mean accuracy .91, precision .70, recall .59, F1 .59; human–human kappa .64 and LLooM–annotator .63/.645. Two experts used the workbench for one hour each and were paid $45. Exact classification-test N is not reported here.
- **Cost/limits/ethics:** average scenario run $1.44, 848,323 tokens, 13.7 minutes; scoring is 79.9% of cost and 58.4% of time. Limitations include untested defaults, absent verification steps, stochastic/domain variation, hallucination, proprietary opacity/version drift, cost, and analyst anchoring/bias. Human inspection is the primary mitigation.
- **Evidence locations:** §§3–7, Figures 9–16, Appendices A–C.

### Sharma, Ansh; Wallace, James R. (2025), “DeTAILS: Deep Thematic Analysis with Iterative LLM Support”

- **Version/status:** peer-reviewed seven-page CUI 2025 paper, pp. 1–7, DOI [10.1145/3719160.3735657](https://doi.org/10.1145/3719160.3735657), describes the system and planned evaluation. The later expanded arXiv:2510.17575v2 adds Karen Cochrane and the 18-participant evaluation but is a separate non-peer-reviewed manuscript with template placeholders (including year 2018 and placeholder DOI/conference). Results below come from that expanded preprint and are not attributed to the short CUI paper.
- **Claim versus operation:** invokes reflexive TA but stabilizes an editable codebook and globally applies it, making the implemented workflow hybrid/codebook TA. Electron/React interface, Python backend, ChromaDB RAG, Ollama, and LangChain adapters for OpenAI, Vertex/Google AI, and Ollama. Researchers upload papers/questions; RAG generates concepts; a subset seeds a codebook; humans edit; global coding requires exact-quote verification; LLM clustering/review and theme buckets produce a CSV report. Human revision and backtracking are available throughout.
- **Expanded evaluation:** 18 researchers: six novice, six proficient, six expert. Each analyzes 30 Reddit threads, then browses a precomputed December 2024 corpus. Sessions last about 2–2.25 hours. Gemini-2.5-Pro-preview-03-25 through Vertex AI on an M1 MacBook; chain-of-thought is mentioned, but exact prompts, temperatures and token limits are not reported.
- **Results/caveat:** alignment between suggestions and participants’ later refinements—not truth—has weighted F1 .86 related concepts, .98 concept outline, .90 initial coding, .97 global coding, .90 macro review-code, and 1.00 themes. NASA-TLX 26.3/100; usefulness 4.21/5. No comparator. High F1 can reflect acceptance/anchoring as well as validity.
- **Ethics/limits/resources:** consent and institutional REB; short sessions, Reddit-only data, small expertise-stratified sample, one model configuration, and no NVivo/ATLAS.ti comparator. [Code](https://github.com/DaemonOnCode/DeTAILS).
- **Evidence locations:** CUI paper throughout; expanded arXiv §§3–8, Figures 2–6.

### Chen, John; Lotsos, Alexandros; Cheng, Sihan; Zhao, Lexie; Zhang, Yanjia; Hullman, Jessica; Sherin, Bruce L.; Wilensky, Uri J.; Horn, Michael S. (2026), “A Computational Method for Measuring ‘Open Codes’ in Qualitative Analysis”

- **Verified citation/status:** Findings of ACL 2026, pp. 41740–41758, DOI [10.18653/v1/2026.findings-acl.2073](https://doi.org/10.18653/v1/2026.findings-acl.2073).
- **Scope:** an evaluation method, not a generator. It builds an aggregate code space by unioning labels, strict embedding merging, generating definitions from label/examples and LLM merging, then iterative two-threshold merging with penalties. It reports Coverage, Overlap, Novelty and Divergence/Jensen–Shannon distance without requiring a single gold coder.
- **Data/models:** first 127 messages from an anonymized public Physics Lab teacher/design group. Four human coders (three PhD, one undergraduate) and four machine coders using the same LLM with varied prompts answer “How did Physics Lab’s online community emerge?” Machine coding uses Gemma-3-27B, temperature .5; embeddings `mxbai-embed-large`. Merge-model comparisons: Gemma-3-27B, Qwen QwQ-32B, GPT-4.1, Gemini-2.5-Pro. Ten runs per condition/model; approximately 8M tokens/$20. Strict/upper thresholds .32/.55.
- **Results:** stages 3–4 materially change metrics; coefficients of variation <.1 and adjusted R² >.91, except some Gemini deviation. Simulations: flooding coverage 78.7, overlap 57.9, novelty 68.1, divergence 67.3 versus baseline divergence 64.9; hallucination coverage 35.6, overlap 15.6, divergence 75.7; combined flooding/hallucination yields 1,775 versus 514 codes and divergence 76.3 versus 64.9.
- **Interpretation/ethics/resources:** team-relative metrics can miss shared omissions and may reward flooding; no universal quality threshold; diagnostic only. One domain and simulated extreme failures. IRB/anonymization, local models prioritized, cloud/privacy warning, explicit warning against metric reification and automation bias. Paper claims a CC BY-NC 4.0 package/data/documentation, but the repository URL is not visible in the inspected text and is therefore **not reported**.
- **Evidence locations:** §§3–7, Tables 1–4, ethics appendix.

### Wang, Lei; Huang, Min; Dragut, Eduard (2026), “CentaurTA: A Self-Improving Human-Agents Collaboration Framework for Thematic Analysis”

- **Verified citation/status:** Findings of ACL 2026, pp. 15871–15884, DOI [10.18653/v1/2026.findings-acl.778](https://doi.org/10.18653/v1/2026.findings-acl.778); [code](https://github.com/Tom-Owl/CentaurTA).
- **Architecture:** open coding and theme construction use sequential Actor/Critic agents. Human feedback is distilled into natural-language principles that update Actor/Critic prompts—no model weights are updated. Documents are batched as 10 contiguous sentences. In stage 1, GPT-5.2 acts as a “simulated expert” drafting labels/rationales; domain experts finalize them, and only final human labels supervise the prompt optimizer.
- **Data/humans:** USRS: 12 Chinese reflections, 25,718 words/471 sentences; ASP: 15 English narratives, 12,678/651; Dreaddit: 214 posts, 19,358/822. Six paid participants (two expert, four intermediate): three iterative-feedback rounds on two domains and three rubric panels; panel kappa .78; $20/hour. First two datasets IRB-approved/anonymized.
- **Models/evaluation:** GPT-5 and GPT-5.2 are named; snapshots, temperatures, seeds, and token limits are not reported. Baselines MindCoder and ATLAS.ti AI Coding. Rubric has 18 code constraints (6 general, 7 format, 5 domain) and 12 theme constraints (4/4/4). GPT-based binary judge also maps to credibility/conformability.
- **Results:** >90% batch accuracy after about 20 feedback instances; rubric scores peak near 10 iterations then decline. On 300 human-labeled USRS codes, LLM-judge rubric accuracy 90 versus human 89, kappa .68. Ablation: full 90%/25 min/10 rounds; no iterative learning 81%; human-only 90%/42 min; simulated-only 85%/7 min/5 rounds.
- **Limits:** open models not evaluated; rubric cannot exhaust interpretive quality; small human sample and limited human-centered error/interpretability evidence. “Self-improving” means persistent prompt-principle updating, not fine-tuning.
- **Evidence locations:** §§3–7, Tables 1–4, appendices.

### Yi, Seungjun et al. (2025), “Auto-TA: Towards Scalable Automated Thematic Analysis via Multi-Agent Large Language Models with Reinforcement Learning”

- **Status:** arXiv:2506.23998v2, 2025-08-08; peer-reviewed publication **not verified**.
- **Claim versus operation:** claims automated end-to-end/reflexive Steps 1–3 and RLHF, but the evaluated system is a sequential role-prompt pipeline with no inter-agent dialogue. RLHF/PPO is explicitly “currently in progress”; no reinforcement-learning results are presented.
- **Architecture/settings:** four GPT-4o code agents, then theme agents and a critic that scores credibility/dependability/transferability and issues ADD/SPLIT/COMBINE/DELETE. Temperature 0. Chunks ≤1,500 (the unit is not consistently clear). Credibility <.7 triggers ADD and description similarity <.20 triggers COMBINE. The text gives conflicting maximum refinements: three in §3.1 and five in the workflow. Role identities also conflict: Physician/Surgeon/Researcher/Layperson in methods versus Cardiac Surgeon/Qualitative Researcher/Medical Doctor/Psychologist in results. Snapshot, seeds, prompts, and costs not fully reported.
- **Data/evaluation:** nine AAOCA focus groups, 42 parents, mean 10,987 words; seven train/two validation groups across all 36 splits; 12 human themes. An appendix instead calls the subset 85 participants. Dependability uses 10 generations/transcript. “Credibility” formula `|Qref|/|Q| × 100` measures quote coverage, not the prose claim of theme–quote consistency. Dependability uses bidirectional ROUGE-1/2; transferability uses the same metric across internal splits. Embeddings `all-mpnet-base-v2`; also Levenshtein/BLEU.
- **Results:** baseline C/D/T .8213/.400/.308; surgeon .9841/.395/.318; qualitative researcher .9756/.397/.324; medical doctor .9683/.389/.334; psychologist .9367/.359/.325. Theme-reference cosine is baseline .132 versus identity variants .107–.121—numerically worse despite qualitative claims.
- **Ethics/limits/resources:** IRB 2019080031; NCT04613934. One domain, prompt sensitivity, no agent interaction, one principal comparator, and multiple valid TA interpretations. No code/data availability statement found. Claimed <10 minutes per 10k-word transcript without distribution/cost.
- **Evidence locations:** supplied PDF §§3–7, Tables 2–4, Appendices A/F.

### Yi, Seungjun et al. (2025), “SFT-TA: Supervised Fine-Tuned Agents in Multi-Agent LLMs for Automated Inductive Thematic Analysis”

- **Status:** arXiv:2509.17167v1, 2025-09-21; ML4H 2025 manuscript. PDF contains PMLR volume placeholder `XXX`; final archival status **not verified**.
- **Architecture/settings:** sequential coder agents, code aggregator, theme agents/aggregator, one supervised-fine-tuned agent at coding and one at theme generation, evaluation/refinement agents for three rounds, plus limited human removal of off-topic output. GPT-4o is fine-tuned through OpenAI; exact snapshot, training hyperparameters, temperature and seeds are not reported. Chain-of-thought, structured tags, qualitative-researcher identity, exactly 12 output themes, and eight clinician criteria are prompted.
- **Training/data leakage:** same nine AAOCA transcripts and 12 human themes. Ten themes are designated “train,” two “validation”; each of the ten is paraphrased 30 ways by GPT-4o, o4-mini-high, Gemini-2.5-Flash and TextGrad, with GPT-4o variants selected, producing 300 training points. Evaluation then compares generated themes to **all 12 reference themes**, so 10/12 references directly shaped fine-tuning. This is reference leakage, not held-out theme generalization.
- **Evaluation/results:** automatic fuzzy/cosine/BLEU/METEOR use maximum pair matching; credibility uses an LLM quote-consistency evaluator; dependability five runs via ROUGE; transferability all 36 seven/two splits. Four blinded method raters (surgeon, qualitative analyst, two laypeople), but inter-rater reliability not reported. Full SFT coding+theme generation: fuzzy .560 (+.103), cosine .268 (+.153), BLEU .080, METEOR .348 (+.228), credibility .783 (+.226), dependability .394 (−.013), transferability .303 (−.005). Human ratings: coverage 5.00, actionability 4.28, distinctiveness 4.35, relevance 4.63.
- **Ethics/resources/limits:** IRB; transcripts/code unavailable for privacy, access “by request.” One corpus, non-exhaustive reference themes, narrow baselines, and disagreement between automatic and human metrics.
- **Evidence locations:** supplied PDF §§3–4, Tables 1–3, data/code statement.

### Xu, Huimin et al. (2026), “TAMA: A Human-AI Collaborative Thematic Analysis Framework Using Multi-Agent LLMs for Clinical Interviews”

- **Verified citation/status:** ACM Transactions on Computing for Healthcare, July 2026, DOI [10.1145/3828752](https://doi.org/10.1145/3828752). Published journal article.
- **Claim versus operation:** the paper explicitly notes that the system is not a contemporary interacting multi-agent architecture; it is sequential role prompting for generation, evaluation, and refinement. A cardiac expert supplies context/rubric, reviews each iteration, and stops. A proposed automatic 4.5/5 stopping threshold failed because scores plateaued near 4 and over-refinement occurred.
- **Data/settings:** same nine AAOCA groups/42 parents/mean 10,987 words. Twelve reference themes were produced by a surgeon and two qualitative coders, around 30 hours/person. `RecursiveCharacterTextSplitter` creates ≤1,500-word chunks at paragraph/line/interviewer boundaries, 75 chunks. GPT-4o temperature 0, snapshot not reported; Llama-3.1-8B via Ollama. `all-MiniLM` embeddings on the first description sentence, threshold .60.
- **Metrics/results:** the named “Jaccard” is actually the fraction of all human×LLM theme pairs above .60, not set Jaccard; hit rate is human-theme coverage; MICS measures within-set similarity. Ten-thousand bootstrap/permutation samples. GPT-4o single: .42/.83/.57; TAMA: .29/.92/.55; human: .33/1.00/.53. Llama single: .20/.12/.34; TAMA: .68/.08/.35. The manuscript sometimes calls hit rate “alignment,” so metric labels must be quoted carefully.
- **Hallucination/human validity:** one-transcript audit by GPT-4o-mini (same family) finds 0/13 hallucinated themes, average grounding .95 and five quotes/theme; circularity is acknowledged. The expert was also an original coder, increasing confirmation risk. Five independent lay reviewers are mentioned without sufficient procedural/results detail. No independent domain expert evaluation.
- **Ethics/resources/limits:** de-identified clinical interviews; an IRB identifier is not reported in this paper. Proprietary API privacy risk, one dataset/model family, non-unique “ground truth.” [Code](https://github.com/Charlie-Yi-SJ/TAMA).
- **Evidence locations:** supplied journal PDF §§3–5, Tables 1–3.

### Yi, Seungjun et al. (2026), “Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance”

- **Status:** arXiv:2603.08989v1, 2026-03-09; peer-reviewed publication **not verified**.
- **Architecture:** stable speaker-turn IDs and chunks (default 8,000 characters); quote extraction; LOGOS-style induction (default 20 codes/chunk, labels 5–12 words, descriptions 40–80 words); normalization/deduplication; LLM relations equivalent/subordinate/reverse/orthogonal; graph cleanup; Auto-TA subthemes/themes; reviewer-driven refinements; ledger from theme → subtheme → code → quote → turn. This is a substantive provenance design.
- **Data:** AAOCA 9 groups/42 participants/mean 10,987 words; SVCHD 28 interviews/11,198 mean; Ali Abdaal 163 transcripts/6,477 mean; Sheffield 15/6,927 mean; Dreaddit 3,553 posts/~318k words.
- **Experiment/settings:** GPT-4o-mini for all methods; 2,048-word chunks with 200 overlap; 80/20 split, seed 42; MiniLM embeddings. Five repetitions, seeds 42–46, up to 10 refinements. GPT-4o-mini evaluator temperature .3 on five sampled test chunks. Other generation temperatures/snapshots and full prompts are not reported.
- **Metrics/results:** Reusability, LLM-scored fitness/coverage, parsimony, consistency `1−JSD`, equal-weight composite. The “Best” LOGOS condition chooses the maximum composite during iterative refinement **on held-out test data**, creating adaptive test leakage. Best composite in 4/5: AAOCA .509, SVCHD .688, Ali .533, Dreaddit .462; Sheffield Thematic-LM .629 versus LOGOS .571. Reported p<.01 and effect d>2.7 for four. Human-theme cosine AAOCA .487/SVCHD .494.
- **Validity/ethics/resources:** generator/judge same model; baselines are reimplementations; no independent human validation; broad themes can score topical cosine. Clinical IRB and request-only access. No public code, prompts, or generated ledgers located, so “full provenance” is an architecture claim not externally reproducible audit evidence.
- **Evidence locations:** supplied PDF Methods–Conclusion, Tables 1–2.

### Raza, Muhammad Zain et al. (2025), “LLM-TA: An LLM-Enhanced Thematic Analysis Pipeline for Transcripts from Parents of Children with Congenital Heart Disease”

- **Status:** arXiv:2502.01620v1; accepted to the Generative AI for Health workshop at AAAI 2025 according to the manuscript. No separate archival proceedings record/DOI verified. [Code](https://github.com/jiaweixu98/LLM-TA).
- **Operation:** sequential LLM coding, code merging and theme generation for clinical transcripts, evaluated against clinician/qualitative-coder reference themes. This is an important precursor in the AAOCA family but not an independent corpus replication.
- **Models/prompts/chunking:** GPT-family pipeline; exact API snapshot and all decoding settings should be treated as **not reported** unless extracted from the linked code at a pinned commit. No interacting agent deliberation.
- **Data/evaluation:** nine focus groups with 42 AAOCA parents and the same 12 reference themes used later by Auto-TA/SFT-TA/TAMA. The paper maps automatic similarity and within/across-run overlap to alignment/trustworthiness; independent prospective clinical utility is not tested.
- **Limits/ethics:** single rare-disease corpus, consensus-reference assumption, proprietary-model reproducibility and familial dependence with later studies. Clinical governance is described in the source study; exact system-paper IRB wording should be checked at extraction.
- **Evidence locations:** arXiv full text; methods, experiments, limitations; linked repository.

## Adjacent and historical systems

- **Gao et al. (2023), CoAIcoder**, ACM TOCHI 31(1), Article 6, DOI [10.1145/3617362](https://doi.org/10.1145/3617362), pp. 1–38: mixed-initiative qualitative coding precursor using Rasa NLU/pretrained embeddings, **not an LLM system**; include as historical comparator, exclude from LLM-only synthesis.
- **Gao et al. (2024), CollabCoder**, arXiv:2304.07366: GPT-assisted independent coding, merging and theme generation; peer-reviewed venue/status **not verified**. Candidate core inclusion if preprints are eligible.
- **Zhao et al. (2025), SCALE**, ACL 2025 long paper, DOI [10.18653/v1/2025.acl-long.416](https://doi.org/10.18653/v1/2025.acl-long.416), pp. 8473–8503; [code](https://github.com/ChengshuaiZhao/SCALE). Include for scalable LLM-assisted corpus/code analysis if its qualitative coding task meets the protocol after full-text screening.
- **LOGOS**, “LLM-driven End-to-End Grounded Theory Development and Schema Induction for Qualitative Research,” arXiv:2509.24294: ICLR 2026 under review at the inspected version, hence non-peer-reviewed. Candidate for grounded-theory/schema-induction synthesis; do not label accepted.
- **De Paoli (2024)**, “Performing an Inductive Thematic Analysis of Semi-Structured Interviews With a Large Language Model: An Exploration and Provocation on the Limits of the Approach,” *Social Science Computer Review*, DOI [10.1177/08944393231220483](https://doi.org/10.1177/08944393231220483): core empirical/methodological candidate; full extraction assigned to another track to avoid duplicate effort.
- **Misra et al. (2026)**, DOI [10.1177/16094069261426100](https://doi.org/10.1177/16094069261426100): qualitative-methods/LLM candidate requiring full-text eligibility confirmation.

## Included position/review paper (not a system)

Yi et al. (2025), “Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models,” arXiv:2509.14597v2, reports a review of 56 papers (August 2022–August 2025) and a two-hour clinician interview. It searched arXiv metadata through 2025-08-15 with a case-insensitive title/abstract dictionary, then Elicit/manual Google Scholar/PubMed/Scopus/Web of Science. It reports core TA 381, inductive 14, deductive 3, core TA+LLM 45 plus 11 external, healthcare 3, and total TA 428. Exact Elicit prompt is supplied, but there is no PRISMA diagram, deduplication log, or complete record list. Table 2 also places “few-shot” under TA types. No consent/IRB statement for the clinician interview was found. Retain for background and citation chasing; exclude from primary-system effect synthesis.

## Cross-study methodological synthesis

1. **Labels are not themes.** Parfenova 2025 evaluates one short label per segmented quote; HICode and LLooM induce hierarchical concepts; QuaLLM counts concerns; Chen evaluates code spaces. These should not be pooled as end-to-end TA.
2. **Reflexive terminology often exceeds implementation.** Autonomous pipelines cannot reproduce sustained researcher familiarization, positionality, reflexive memoing, negative-case interrogation, and interpretive writing merely by assigning role prompts. DeTAILS, Dai, LLooM, TAMA and CentaurTA provide more real analyst control, but still often stabilize codebooks.
3. **“Multi-agent” is heterogeneous.** Thematic-LM uses AutoGen roles and adaptive memory; TAMA/Auto-TA/SFT-TA are chiefly sequential role prompts; CentaurTA persists human feedback as prompt principles. The label alone is not an architectural feature.
4. **Clinical evidence is clustered, not independent.** Five systems share AAOCA data/reference themes. Improvements across those papers largely compare pipeline variants on one benchmark. SFT-TA additionally trains on paraphrases of 10/12 reference themes and evaluates against all 12.
5. **Trustworthiness metrics have weak construct validity.** ROUGE stability is not dependability in the qualitative-methodological sense; random internal splits are not transferability to a new setting/population; model-rated quote consistency is not credibility; and TAMA’s “Jaccard” is not Jaccard. Auto-TA’s credibility formula measures quote coverage. DeTAILS F1 measures suggestion–revision alignment, potentially including anchoring. Chen’s no-gold metrics improve the framing but remain team-relative and vulnerable to shared omissions/flooding.
6. **Evaluation circularity is common.** Thematic-LM and the 2026 provenance paper use GPT-4o-family judging for GPT-4o-family generation. TAMA’s hallucination check uses GPT-4o-mini on GPT-4o output. Reference authors often participate in later evaluation.
7. **Reproducibility remains uneven.** Dai, HICode, LLooM, DeTAILS, CentaurTA, TAMA and LLM-TA expose code. Several clinical preprints do not expose prompts, pinned environments, audit ledgers, or data; some data restrictions are appropriate but synthetic fixtures and hashed ledgers could still be released.

## Defensible open gaps after the 2026 literature

- Independent, prospective, multi-site workflow evaluation with analysts who did not create the reference themes.
- Validated measures of speaker/participant coverage, contradictory cases, negative evidence, and source-to-theme provenance—not merely existence of a provenance architecture.
- Cross-model, cross-language, cross-domain, and temporal stability under pinned snapshots and multiple seeds.
- Independent hallucination/quote-entailment adjudication and clinically actionable specificity, rather than same-family LLM judging.
- Principled stopping criteria for iterative agents; TAMA empirically shows fixed score thresholds can over-refine.
- Human-centered evaluation of anchoring, automation bias, positionality, identity-role prompt confounding, learning, and actual analyst burden.
- Construct validation of no-gold code-space metrics. Chen et al. is an important start, but shared omissions and flooding remain unresolved.
- Independent replication of persistent human-feedback optimization. CentaurTA establishes feasibility; generalization and true burden reduction are still open.
- Release of runnable prompts/configurations, synthetic evaluation fixtures, and complete audit logs when raw qualitative data cannot be shared.

## Screening ledger for discovered candidates

| Record | Decision | Reason |
|---|---|---|
| Dai 2023 | Include core | LLM-assisted codebook/coding workflow with empirical evaluation. |
| Parfenova 2024 | Include context/proposal | Directly scoped, but proposed rather than operationalized. |
| Parfenova 2025 NAACL | Include core | Empirical inductive open-code generation. |
| Parfenova & Pfeffer 2025 ACL | Include core | Ensemble/refinement evaluation of inductive labels. |
| HICode 2025 | Include core | Hierarchical inductive coding at corpus scale. |
| QuaLLM 2025 | Include core with method tag | Concern extraction/quantification; not reflexive TA. |
| Thematic-LM 2025 | Include core | Automated multi-agent code/theme workflow. |
| LLooM 2024 | Include core-adjacent | Concept induction and mixed-initiative coding, not formal TA. |
| DeTAILS CUI/expanded preprint | Include; keep versions separate | Interactive TA system; evaluation only in expanded preprint. |
| Chen et al. 2026 | Include evaluation-method stratum | Measures code spaces; does not generate codes. |
| CentaurTA 2026 | Include core | Iterative human-feedback agent framework. |
| LLM-TA, Auto-TA, SFT-TA, TAMA, Yi 2026 provenance | Include; cluster as related family | Same AAOCA benchmark/reference themes; dependent evidence. |
| Position paper 2025 | Exclude from primary system synthesis; retain background | Review/position, no evaluated system. |
| CoAIcoder 2023 | Historical comparator; exclude LLM-only pool | Pretrained embedding/Rasa NLU rather than LLM generation. |
| CollabCoder | Candidate include | Direct GPT-assisted workflow; venue status uncertain. |
| SCALE | Candidate pending full-text task fit | Scalable LLM corpus/code analysis. |
| LOGOS | Candidate include if preprints eligible | Direct grounded-theory/schema induction; under-review status only. |
| Kousa et al. 2023 | Candidate pending full text | ACL-title search hit related to qualitative analysis; scope not established here. |
| Spinoso-Di Piano et al. 2023 | Candidate pending full text | ACL-title search hit; verify whether LLM performs coding or only analyzes qualitative outcomes. |
| Fischer et al., “Concepts Over Time” | Candidate pending full text | Potential corpus concept induction; TA eligibility uncertain. |
| Fischer & Biemann, “Exploring LLMs for Qualitative Data Analysis” | Candidate include | Directly scoped; extract in general-method track. |
| Fischer & Biemann, “Perspectives…” 2026 | Candidate include/context | Direct QDA perspective/evaluation paper. |
| Ng et al. captions paper | Exclude | Uses thematic analysis to evaluate captions; LLM does not automate qualitative coding. |
| De Paoli 2024 | Candidate include core | Direct LLM inductive TA; full extraction elsewhere. |
| Misra et al. 2026 | Candidate pending full text | Direct qualitative-methods/LLM candidate; eligibility not yet confirmed. |
| WSESE 2026, DOI 10.1145/3786149.3788305 | Context/review candidate | Review/secondary research, not primary system. |

## Evidence boundaries

This report does not infer missing proprietary model snapshots, temperatures, prompt text, participant counts, venue acceptance, or code availability. “Not reported” means it was absent from the inspected full text or official record; “not verified” means an author claim or search lead lacked a confirming official record at the cutoff. Web search result counts were not exposed and were not approximated. Forward-citation coverage is therefore best described as targeted citation chaining, not exhaustive citation-index enumeration.
