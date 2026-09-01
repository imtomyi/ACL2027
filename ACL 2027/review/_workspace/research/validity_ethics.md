# Track 3 evidence review: validity threats, high-stakes qualitative applications, ethics, and accountability

**Review cutoff:** 2026-08-24  
**Search date:** 2026-08-24  
**Scope:** Adjacent NLP evidence on identity/source/domain confounding, shortcut learning, representation confounds, participant overlap and leakage, prompt/order sensitivity, benchmark contamination, privacy, governance, and human accountability; plus clinical or other high-stakes studies that use LLMs to code or thematically analyze interviews, focus groups, transcripts, or closely related qualitative text.  
**Relationship labels:** **Core** means the system performs qualitative coding/theme work or directly evaluates an LLM qualitative-analysis workflow. **Adjacent** means the paper supplies a validity, leakage, contamination, privacy, or evaluation result that materially changes how a core system should be designed or evaluated.  
**Reporting rule:** Missing information is written as **not reported**. Reviewer inferences are explicitly labelled and are not treated as observed results.

## Executive finding

The strongest open problem is not another demonstration that an LLM can produce plausible themes. It is a controlled audit of **whose language and which source cues drive the themes, whose evidence survives aggregation, and whether rare or contradictory cases are preserved**.

Three evidence streams converge:

1. In an adjacent prediction setting, Yu, Liu, and He show that text representations can behave mainly like repeated-source identifiers: same-company similarity is much higher than cross-company similarity, and transcript-derived predictions correlate strongly with a ticker-level historical baseline. This establishes a concrete mechanism by which apparently semantic performance can be source- or identity-driven.
2. In qualitative analysis, Ashwin, Chhabra, and Rao show that LLM coding errors are systematically associated with respondent characteristics and can distort downstream regression estimates even when aggregate classification metrics are reported. Clinical studies additionally document both loss of low-frequency/culturally specific content and overemphasis of rare dramatic events.
3. Most clinical LLM thematic-analysis papers do not test participant-, site-, interviewer-, or diagnosis-disjoint generalization; do not mask disease/source cues; do not quantify participant-level evidence coverage or negative-case survival; and do not probe whether published reference themes were memorized by closed models.

The most defensible ARR-style contribution is therefore a preregistered, contamination-aware, participant- and source-disjoint benchmark with counterfactual identity/source perturbations and controlled rare/negative-case probes. Prompt repetition alone is already crowded and has high novelty risk.

## Search and reproducibility record

### Machine-searchable sources

All searches were executed on 2026-08-24 with a publication cutoff of 2026-08-24. Full machine-readable results and scripts are stored beside this report.

| Source | Exact search design | Per-query retrieval | Unique records | Local record |
|---|---|---:|---:|---|
| PubMed | Seven title/abstract Boolean searches covering LLM/generative AI + thematic analysis; qualitative/open/inductive coding; qualitative content/data analysis; human–AI collaboration; multi-agent systems; codebook induction/refinement; and clinical transcript/patient interview | 229, 8, 25, 47, 2, 0, 1 | 295 | `research/pubmed_search_records.json` |
| ACL Anthology | Seven title-token searches aligned to the concepts above plus a broad thematic/qualitative-coding supplement | 1, 3, 4, 0, 0, 0, 0, 12 | 13 | `research/acl_anthology_search_records.json` |
| arXiv | Seven concept searches plus identity leakage/speaker identity/shortcut learning | 116, 77, 22, 29, 12, 6, 14, 200 of 241 reported | 440 | `research/arxiv_search_records.json` |
| Crossref | Seven relevance-ranked `query.title` searches, date filtered, first 100 results/query | 100 for each query | 688 | `research/crossref_search_records.json` |
| OpenReview | Nine phrase searches; first 1,000 results where available, followed by client-side LLM + qualitative-task filtering | 379/78 retained, 66/12, 33/16, 55/13, 39/10, 52/6, 52/1, 5/1, 2/0 | 120 retained after deduplication | `research/openreview_search_records.json` |

Crossref's multi-million `reported_total_results` values are fuzzy search estimates and **must not** be interpreted as eligible-record or screening counts. OpenReview's retained counts are algorithmic candidates, not inclusions. The ACL search is title-based against the 2026-08-24 Anthology snapshot and is intentionally supplemented by targeted validity searches.

### Exact PubMed queries

1. `(("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "generative AI"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "theme generation"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
2. `(("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative coding"[Title/Abstract] OR "inductive coding"[Title/Abstract] OR "open coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
3. `(("large language model"[Title/Abstract] OR LLM[Title/Abstract]) AND ("qualitative content analysis"[Title/Abstract] OR "qualitative data analysis"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
4. `(("human-AI collaboration"[Title/Abstract] OR "human-in-the-loop"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative research"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
5. `(("multi-agent"[Title/Abstract] OR "LLM agent"[Title/Abstract]) AND ("thematic analysis"[Title/Abstract] OR "qualitative coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
6. `(("codebook induction"[Title/Abstract] OR "codebook generation"[Title/Abstract] OR "codebook refinement"[Title/Abstract]) AND (LLM[Title/Abstract] OR "large language model"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`
7. `(("clinical transcript"[Title/Abstract] OR "patient interview"[Title/Abstract]) AND ("large language model"[Title/Abstract] OR LLM[Title/Abstract] OR "automated coding"[Title/Abstract])) AND ("2020/01/01"[Date - Publication] : "2026/08/24"[Date - Publication])`

### Targeted citation-chain and web searches

The following exact strings were searched on 2026-08-24 against official or primary-source targets:

- `site:aclanthology.org "Same Company, Same Signal"`
- `site:arxiv.org "Same Company, Same Signal" identity earnings call transcripts`
- `"Same Company, Same Signal" cited by`
- `"Same Company, Same Signal" transcript identity confounding`
- `site:pubmed.ncbi.nlm.nih.gov large language model qualitative analysis clinical interviews transcripts coding`
- `site:jmir.org large language model qualitative thematic analysis interview transcripts`
- `"Using Large Language Models for Qualitative Analysis can Introduce Serious Bias" official pdf`
- `site:aclanthology.org participant overlap leakage mental health text classification user split`
- `site:aclanthology.org user leakage author identity text classification train test overlap`
- `NLP mental health classification user split leakage same user train test paper`
- `patient-level split leakage clinical text classification NLP paper`
- `site:aclanthology.org "Text Embeddings Reveal" privacy`
- `site:aclanthology.org data contamination large language models benchmark 2024`

Search-result interfaces did not expose reliable total-result counts for these targeted queries. Backward chaining from Yu et al. and the core clinical papers was performed from their reference lists. No direct forward-citing research article for Yu et al. was located in the searched primary/indexed sources by the cutoff. That statement means **zero located by this search**, not zero citations globally.

### Screening boundaries and limitations

- Verification prioritized full text from ACL Anthology, PubMed Central, JMIR, ACM, PLOS, BMC/Springer, Sage, ScienceDirect/accepted manuscripts, arXiv, and DOI/Crossref metadata.
- Web of Science and Scopus were not available through institutional interfaces; citation counts are therefore **not reported** except where explicitly captured from Crossref.
- This is a focused track supplement, not a standalone PRISMA pool. One reviewer performed track-level screening and extraction; independent duplicate screening and adjudication are not reported.
- Dynamic citation count available in the local retrieval: Prescott et al., Crossref `is-referenced-by-count` 92 on 2026-08-24. Such counts are source- and date-dependent.

## Detailed evidence: core qualitative-analysis studies

### Ashwin, Chhabra, and Rao — systematic demographic error and downstream bias

**Citation and source.** Julian Ashwin, Aditya Chhabra, and Vijayendra Rao. “Using Large Language Models for Qualitative Analysis can Introduce Serious Bias.” *Sociological Methods & Research*, online first 2025; 55(3):795–839, 2026 issue. DOI [10.1177/00491241251338246](https://doi.org/10.1177/00491241251338246); primary preprint [arXiv:2309.17147](https://arxiv.org/abs/2309.17147). **Classification: Core.**

**Data and task.** The study analyzes 2,407 open-ended interviews with Rohingya refugees and Bangladeshi hosts in Cox's Bazar, comprising 32,463 question–answer pairs, with an average 12.6 question–answer pairs per interview and 13.7 words per answer. Interviews were in Bengali or Rohingya and were transcribed in Bengali, then machine-translated and corrected in English. Trained sociologists manually annotated 789 interviews (9,964 question–answer observations) for 19 binary codes. Each bespoke `iQual` model used 25 repeated fits with a randomized 200-interview test set.

**Systems and evaluation.** The current publisher version evaluates GPT-3.5-turbo, GPT-4o-mini, Llama-2-13B, and Llama-3-8B using four-shot chain-of-thought prompting, against bespoke supervised `iQual` classifiers and GPT-augmented `iQual`. Mean F1 was .542 for iQual, .541 for iQual plus GPT augmentation, .414 for GPT-3.5, .390 for GPT-4o-mini, .371 for Llama-3-8B, and .290 for Llama-2-13B. All evaluated LLMs overpredicted sparse codes.

The crucial analysis regresses coding errors on respondent attributes, including refugee status, child age and sex, respondent age/education/sex, parental refugee status, number of children, assets/income, and trauma, then uses an F-test for any association. GPT-3.5 errors were significantly associated with respondent characteristics at the 5% level for 10 of 19 codes; the bespoke model showed such an association for 1 of 19. The paper also demonstrates misleading downstream regression estimates from LLM-generated labels. The authors checked interviewer identity and did not find evidence of interviewer bias in their Figure A.4.

**Ethics/reproducibility.** Interview transcripts are confidential. Code is public at [worldbank/iQual](https://github.com/worldbank/iQual), and anonymized data are available upon request. The paper estimates expert coding of 789 interviews at about US$10,000 and model costs at study time of about US$600 for GPT-3.5, US$150 for GPT-4o-mini, and US$20,000 for GPT-4. Ethics training for interviewers is described; IRB approval and participant-consent details in the verified publisher full text are **not reported**.

**Review implication.** This is the strongest direct evidence that acceptable aggregate agreement is not enough. Error must be modeled against participant attributes and propagated into downstream estimands. It partially closes a generic “LLM bias in deductive qualitative coding” claim; an ARR paper needs to move to inductive themes, participant/source confounds, multilingual strata, rare/negative cases, or controlled perturbations.

### Xu et al. — TAMA multi-role clinical thematic analysis

**Citation and source.** Xu et al. “TAMA: A Human-AI Collaborative Thematic Analysis Framework Using Multi-Agent LLMs for Clinical Interviews.” *ACM Transactions on Computing for Healthcare* (2026). DOI [10.1145/3828752](https://doi.org/10.1145/3828752); code [Charlie-Yi-SJ/TAMA](https://github.com/Charlie-Yi-SJ/TAMA). **Classification: Core.**

**Data and task.** Nine deidentified focus-group transcripts from 42 parents of children with anomalous aortic origin of a coronary artery (AAOCA) were used. Transcripts averaged 10,987 words (SD 1,537; median 11,457) and were divided into 75 chunks of at most 1,500 words. The published human reference comprises 12 themes developed through consensus by three coders—a cardiac surgeon and two qualitative researchers—after all coders read all transcripts; the paper estimates approximately 30 hours per coder.

**System.** GPT-4o at temperature 0 is assigned sequential generation, evaluation, and refinement roles, with an expert deciding when to stop. This is a structured multi-role prompting workflow, not evidence of autonomous inter-agent organization. Llama-3.1-8B was also tested locally via Ollama.

**Evaluation and results.** Similarity uses all-MiniLM-L6-v2 with threshold .60, 10,000 bootstrap samples, permutation tests, Jaccard similarity, human-theme hit rate, and a model-generated information-content score (MICS). Human inter-coder performance was Jaccard .33 (95% CI .25–.71), hit rate 1.00, MICS .53. A single GPT-4o analysis achieved Jaccard .42 (.29–.69), hit .83 (.58–1.00), MICS .57 (.56–.66); TAMA achieved .29 (.23–.50), .92 (.75–1.00), and .55 (.55–.64). Relative to the single GPT-4o run, TAMA's Jaccard decrease was significant (p=.022; Cohen's h=.27), while the hit-rate increase was not (p=.250; 12 reference themes). Llama-3.1-8B behaved unreliably: single-agent Jaccard .20/hit .12 and TAMA .68/.08, while its evaluator accepted poor themes on the first pass at 4.40/5.

For grounding, GPT-4o-mini retrieves three to five quotations per theme and scores their support. On one transcript, the system generated 13 themes and the authors reported zero hallucinations. The authors themselves note circularity, a single structured transcript for this audit, and no external quantification of hallucination or false negatives; human review is the main safeguard.

**Ethics/reproducibility.** Data are described as deidentified; IRB, consent, proprietary-API retention, training use, security settings, and business-associate agreement are **not reported** in the verified paper. The authors suggest larger on-premises models for HIPAA-sensitive work, because the tested local 8B model was inadequate. Code is public; raw clinical transcripts are not public.

**Validity concerns.** The expert defining criteria and stopping refinement helped create the original human themes, creating acknowledged evaluator/reference nonindependence. Five lay reviewers are independent but lack stated qualitative expertise. **Reviewer-inferred contamination risk:** the reference themes were previously published from the same AAOCA corpus, the prompt supplies the disease domain, and a closed pretrained GPT-4o may have encountered public theme labels/descriptions. The paper does not test contamination. This is a risk, not evidence that memorization occurred. Theme hit rate is not participant-level evidence coverage, and no negative-case preservation metric is reported.

### Raza et al. — LLM-TA and rare-event overrepresentation

**Citation and source.** Raza et al. “LLM-TA: An LLM-Enhanced Thematic Analysis Pipeline for Transcripts from Parents of Children with Congenital Heart Disease.” arXiv preprint (2025), [arXiv:2502.01620](https://arxiv.org/abs/2502.01620); code [jiaweixu98/LLM-TA](https://github.com/jiaweixu98/LLM-TA). **Classification: Core; preprint.**

**Data/system.** This paper uses the same nine AAOCA focus groups, 42 parents, median 11,457 words/transcript, 1,500-word chunks, and 12 published human reference themes. GPT-4o-mini-2024-07-18 at temperature 0 is evaluated in zero-shot, one-shot, and Reflexion variants; a baseline uses temperature 1.0. LangChain 0.3.21 is reported. One expert from the original human analysis evaluates outputs.

**Metrics/results.** Embedding thresholds are .82 for sentence-T5-XXL, .62 for all-mpnet, and .56 for all-MiniLM; an LLM-judge threshold of .5 is also used. Under sentence-T5, the Mathis baseline without Reflexion obtained Jaccard .111/hit .667 and with Reflexion .139/.583. LLM-TA zero-shot achieved .410/1.00, one-shot .396/1.00, and one-shot plus Reflexion .222/1.00. Under the LLM judge, the corresponding LLM-TA values were .118/.750, .174/.917, and .152/.917. Most variants ran in under 10 minutes; one-shot plus Reflexion took about 90 minutes, compared with roughly 30 person-hours per human coder.

**Negative/rare cases.** Expert review found that rare dramatic experiences such as cardiac arrests and financial concerns were overrepresented, while broad themes were sometimes misinterpreted—for example, parents wanted comprehensive rather than merely simplified information. This is a representativeness failure in both directions. It should not be summarized only as “minority omission.”

**Ethics/validity.** Deidentification is reported; IRB, consent, API retention/training, and vendor security settings are **not reported**. The same public-reference contamination risk and evaluator nonindependence described for TAMA apply. No participant-level evidence matrix or controlled negative-case test is reported.

### Mathis et al. — local open-source model on mental-health interviews

**Citation and source.** Mathis et al. “Inductive thematic analysis of healthcare qualitative interviews using open-source large language models: How does it compare to traditional methods?” *Computer Methods and Programs in Biomedicine* 255 (2024):108356. DOI [10.1016/j.cmpb.2024.108356](https://doi.org/10.1016/j.cmpb.2024.108356); [accepted manuscript](https://rke.abertay.ac.uk/files/81476151/DePaoli_InductiveThematicAnalysis_Accepted_2024.pdf); PMID 39067136. **Classification: Core.**

**Data/system.** Twenty-one semi-structured interviews from a Connecticut community mental-health center include 14 clients with severe mental illness and seven clinicians. Client interviews had median duration 10.5 minutes and 1,560 words; clinician interviews 19.2 minutes and 3,244 words. Whisper transcribed the audio. Interviewer and interviewee text was merged without speaker diarization. Human analysis produced 96 client and 180 clinician codes, collapsed to 31 and 43 unique codes, and six and seven themes. A locally hosted, four-bit GPTQ-quantized LLaMA-2-70B-Instruct model ran with ExLlama on Ubuntu and dual RTX 3090 GPUs (48 GB VRAM total).

**Results and validity.** Across three evaluations, reported Jaccard similarity ranged .44–.69, characterized as moderate to substantial. Exact prompt/order sensitivity, random seeds, and run count beyond the three described evaluations are **not reported**. Merging interviewer and participant text creates an untested speaker/source confound: facilitator language could become a shortcut for themes.

**Ethics/reproducibility.** Yale determined the study exempt; the local workflow was designed around PHI/HIPAA handling. Consent details are **not reported**. Local inference is a concrete privacy-preserving alternative to third-party transmission, although local access controls and residual reidentification still require governance.

### Prescott et al. — proxy SMS study and consent boundary

**Citation and source.** Prescott et al. “Comparing the Efficacy and Efficiency of Human and Generative AI: Qualitative Thematic Analyses.” *JMIR AI* 3 (2024):e54482. DOI [10.2196/54482](https://doi.org/10.2196/54482); [official full text](https://ai.jmir.org/2024/1/e54482). **Classification: Core methods/ethics; exclude from the clinical-interview subset.** Crossref citation count captured 2026-08-24: 92.

**Data/system/results.** The data are 40 short SMS prompts authored for an intervention (5–14 words, fewer than 160 characters), not participant-generated transcripts. GPT-3.5 and Bard/PaLM 2 were compared with human coders. In inductive analysis, both models overlapped with five of seven human themes (71%); deductive overlap was six of 12 for ChatGPT (50%) and seven of 12 for Bard (58%). Coding agreement for matched themes was ChatGPT 31/66 (47%) inductive and 22/59 (37%) deductive; Bard 20/54 (37%) and 21/58 (36%). Mean analysis time was 20 minutes (SD 3.5) for GenAI versus 567 minutes (SD 106.5) for humans.

**Ethics implication.** The investigators deliberately did not upload participant-generated SMS because original consent did not authorize disclosure to third-party vendors and the tools could retain inputs for training. They used proxy messages and received an exemption because no participant data were analyzed. This is unusually clear evidence that deidentification is not blanket authorization: consent, data-use terms, processor role, and model-training/retention terms must be assessed separately.

### Li et al. — repeated GPT-4 coding of patient interviews

**Citation and source.** Li et al. “Comparing GPT-4 and Human Researchers in Health Care Data Analysis: Qualitative Description Study.” *Journal of Medical Internet Research* 26 (2024):e56500. DOI [10.2196/56500](https://doi.org/10.2196/56500); [official full text](https://www.jmir.org/2024/1/e56500). **Classification: Core.**

**Data/results.** Twenty adults with acquired buried penis were interviewed for 15–30 minutes. The sample was 85% White and 95% heterosexual, with mean age 58.8 years and mean BMI 41.1. GPT-4 used standardized prompts; humans used general qualitative description. There were 63 code-presence agreements, 14 code-absence agreements, and 23 disagreements; Cohen's kappa was .401. Repeating the same transcript ten times produced body-image and chronic-pain codes in 10/10 runs and depression in 9/10, while less common codes appeared in only six to eight runs or fewer. Human analysts produced richer subthemes.

**Ethics/reproducibility.** UCSF IRB 20-32062 and consent are reported; secondary GPT-4 analysis was exempt. A private Versa instance that did not retain/train on inputs was used during method development, followed by commercial GPT-4 only after deidentification. Commercial-service retention/settings are **not reported**. The single site, narrow demographic profile, and lack of order or participant-level rare-case tests limit generalization.

### Bijker et al. — repeated-run reliability is not validity

**Citation and source.** Bijker et al. “ChatGPT for Automated Qualitative Research: Content Analysis.” *Journal of Medical Internet Research* 26 (2024):e59050. DOI [10.2196/59050](https://doi.org/10.2196/59050); [official full text](https://www.jmir.org/2024/1/e59050). **Classification: Core, nonclinical public-text content analysis.**

**Data/system/results.** The abstract reports 537 open forum posts; the methods report 539, an internal discrepancy that should be preserved. GPT-3.5-Turbo was used through the web application on four accounts/computers between 2023-06-12 and 2023-06-18. Ten coding schemes were each applied in ten conversations; an additional structured matrix was tested. A 108-post (20%) subset supported human verification of extraction. Ten unconstrained inductive coding schemes were generated. Mechanism precision was 66%–88%. Reported kappa ranges were .72–.82 for inductive schemes and .58–.73 for deductive/structured schemes; category-level kappa ranged .67–.95 inductive and .13–.87 deductive.

**Interpretation.** The paper explicitly studies reliability/stability, not truth. Repeated-output agreement cannot establish evidential fidelity, demographic fairness, or correct interpretation. Open-access posts contained no identifiers and the study was deemed exempt; prompts and supplements are public.

### Bennis and Mouwafaq — high agreement with circularity risks

**Citation and source.** Bennis and Mouwafaq. “Advancing AI-driven thematic analysis: a comparative study of nine generative models on Cutaneous Leishmaniasis data.” *BMC Medical Informatics and Decision Making* 25 (2025):124. DOI [10.1186/s12911-025-02961-5](https://doi.org/10.1186/s12911-025-02961-5). **Classification: Core.**

**Data/system.** Of 454 students approached, 448 supplied anonymized quotations in response to one short open question; six refused. Seventy-nine students were affected by cutaneous leishmaniasis (35 female, 44 male), with 63 nonempty responses. Nine systems were used: Llama-3.1-405B, Claude 3.5, NotebookLM, Gemini 1.5 Advanced Ultra, ChatGPT o1-Pro and o1, Grok V2, DeepSeek V3, and Gemini 2.0 Advanced. Each coding scheme was run twice; theme generation had four iterations.

**Results.** External weighted kappa was .79 (.74–.85) for o1-Pro, .78 (.73–.84) for Claude, and .78 (.72–.83) for Llama; initial human kappa .74 rose to .82 after targeted recoding. o1-Pro's internal kappa for the affected subgroup was 1.00. After combining iterations, four models recovered all 24 subthemes and Jaccard 1.00. Gender comparisons used chi-square/Fisher tests, not regressions of model error on participant attributes.

**Circularity/contamination.** The human analysis had already been published. Perplexity synthesized the reference themes, NotebookLM compared model outputs, and outputs across iterations were combined. Thus “perfect” similarity is not an independent validation signal. **Reviewer-inferred risk:** a public reference and model-assisted reference/judging may enable semantic leakage or circular evaluation. No direct contamination test is reported.

**Ethics.** The original study had ethics approval; secondary analysis used anonymized data without additional approval. The authors report ephemeral storage and deletion of prompts/results after download. Supplementary data and outputs are public.

### Hill et al. — blinded healthcare comparison and speaker-attribution errors

**Citation and source.** Hill et al. “Large language models for thematic analysis in healthcare research: A blinded mixed-methods comparison with human analysts.” *PLOS Digital Health* 5(4) (2026):e0001189. DOI [10.1371/journal.pdig.0001189](https://doi.org/10.1371/journal.pdig.0001189). **Classification: Core.**

**Data/system.** One approximately two-hour focus group with seven adults living with long-term conditions yielded 12,172 words. ChatGPT-5 and Claude 4 Sonnet were run through APIs in October 2025 and QualiGPT through the web, with default temperature 1.0. A deductive codebook contained 10 codes and six themes; an expert inductive reference contained 14 codes and five themes. Human and LLM analysts were blinded to one another. Outputs had to quote segment identifiers; researcher/facilitator segments were explicitly excluded from coding.

**Results.** Deductive percent agreement was 93.5% (95% CI 92.5–94.5) for LLMs and 92.7% (91.6–93.9) for humans, but kappa was .34 (.26–.40) for each under low code prevalence (mean 7.8%, SD 3.2). Gwet AC1 was .93 (.92–.94) for LLMs and .92 (.90–.93) for humans. Only ChatGPT-5 met the inductive noninferiority test (p=.043). Strict hallucination was 1.2% (SD 2.1), expanded hallucination 8.6% (SD 5.1), and comprehensive error 12.4%, much of it coding facilitator speech. This is direct evidence that source/speaker attribution can fail despite high aggregate agreement.

**Ethics/reproducibility.** Southampton ERGO 106517 approved the study; participants gave written consent and could separately opt out of secondary use. Data were anonymized and processed in secure institutional environments. The transcript is withheld because residual identifiability remains; code and prompts are public. The authors note that the AI-in-health topic may resemble common training discourse and inflate alignment. One transcript sharply limits inference.

### Vikan et al. — reflexive thematic analysis, translation, privacy, and accountability

**Citation and source.** Vikan et al. “Reflecting on LLM Support in Reflexive Thematic Analysis: An Exploratory Study.” *Qualitative Health Research* 36(2–3) (online 2025; issue 2026):191–205. DOI [10.1177/10497323251365211](https://doi.org/10.1177/10497323251365211); [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12949038/). **Classification: Core.**

**Data/system.** One Norwegian operating-room nurse interview, 10 pages and 9,262 words, was selected from a primary corpus of 223 pages/158,865 words. Moderator speech was removed. Offline Mistral-7B ran through Ollama/HuggingFace with RAG on an RTX 4070 Ti Super system. Seven tests from 2024-11-11 through 2025-01-06 generated 50,009 words of prompts, outputs, and memos.

**Results.** Norwegian output was poor; translating to English improved performance but risked changing or losing meaning. The model omitted essential content, fabricated quotations and page/line references, renamed themes in ways that changed their meanings, and allowed theoretical documents in retrieval to dominate the analysis. No time savings were observed. Human familiarization and reflexivity remained indispensable.

**Ethics/accountability.** The Regional Committee determined the study outside Norway's Health Research Act (reference 461904); Sikt approved secondary analysis (307019). Participants received written digital information specifically explaining LLM use, privacy, and voluntariness; consent was encrypted. Processing occurred offline on a sensitive server. The paper explicitly rejects model authorship/accountability: humans remain responsible for interpretations and outputs. This is the strongest operational example of LLM-specific consent and local processing in the included evidence.

### Grover et al. — local 70B workflow and an RAG hallucination

**Citation and source.** Grover et al. “Advancing the science of qualitative patient preference assessment using large language models.” *PLOS Digital Health* 5(3) (2026):e0001263. DOI [10.1371/journal.pdig.0001263](https://doi.org/10.1371/journal.pdig.0001263). **Classification: Core.**

**Data/system.** Five pan-Canadian focus groups included 28 people with cancer history. One French-language group was translated to English. Median transcript length was 10,097 words, mean 9,491, with nearly 50,000 words total. Human themes were member-checked. Hermes-3-Llama-3.1-70B ran locally in four-bit form using LM Studio on Windows, an RTX 4070, and 64 GB RAM. Final parameters were temperature 1, top-p .15, min-p .02, repetition penalty 1.15, and top-k 40. BASE, naive RAG, and inductive thematic saturation (ITS) were compared over three iterations.

**Results.** Sentence-T5-XXL comparisons across 21 thresholds produced median cosine similarities .80/.79/.81, median Jaccard .60/.46/.64, and hit rate .86 for BASE/RAG/ITS. Overall Jaccard and hit differences were nonsignificant (p=.41 and .93); at threshold .82, Jaccard was .34/.23/.46. The RAG-versus-ITS cosine difference survived false-discovery correction (p=.03). Naive RAG generated an unrelated “compensation and incentives debate.” Analyst execution of ITS took approximately 3.5 hours.

**Ethics/limitations.** REB H20-00861 is reported; original consent explicitly allowed deidentified secondary research. Data access requires REB approval. Local processing limits vendor exposure. The study has one dataset, one model, and one embedding-based reference comparison; independent human evaluation of new themes is **not reported**. **Reviewer-inferred contamination risk:** the earlier human reference may be publicly described; the paper does not test memorization.

### Bai and Finkelstein — three clinical datasets, one run per condition

**Citation and source.** Bai and Finkelstein. “Large Language Models for Qualitative Analysis of Digital Health Interviews” (title as indexed). *JMIR Medical Informatics* 14 (2026):e96129. DOI [10.2196/96129](https://doi.org/10.2196/96129). **Classification: Core.**

**Data/system.** Three completed digital-health datasets contained 48 interviews: interstitial lung disease, 17 transcripts/169 human codes/seven themes; postural orthostatic tachycardia syndrome, 15/178/10; and COPD, 16/261/six. Transcripts were deidentified and had not been publicly released before analysis. GPT-5.2-thinking, Gemini 3 Pro, and Opus 4.6 were used through consumer web interfaces. Workflows separately tested code extraction, code combination, and theme generation, including L1/L2/L3 and direct-coding/grouping strategies. Code and quotation provenance was maintained through parent identifiers and programmatic ID validation.

**Results.** Sentence-T5-XXL embeddings, Hungarian assignment, and greedy full matching were used. Example top Opus results include .893 (SD .041) on POTS direct coding, .891 (.027) on COPD direct grouping, and .889 (.032) on ILD L3. Model output scale differed substantially: Opus produced 15–60 extraction codes and 43–153 merged codes, while Gemini produced roughly 10 and ChatGPT roughly 25, indicating model-specific output ceilings. Each model/workflow condition was run once; stability and order sensitivity are therefore unmeasured. One researcher handled outputs and formats; interrater reliability is **not reported**.

**Ethics/validity.** Secondary deidentified analysis was deemed not human-subjects research; the original University of Utah protocol was IRB 00168937 with consent. Consumer-interface retention, training use, processor terms, and enterprise protections are **not reported**. Disease background was supplied, leaving domain-cue shortcuts untested.

### Turner et al. — deductive trial interviews, recall–precision tradeoff

**Citation and source.** Turner et al. “Large language models for deductive qualitative content analysis in dementia-focused embedded pragmatic clinical trials: A comparative methodological study.” *Implementation Science Communications* 7 (2026):130. DOI [10.1186/s43058-026-00953-8](https://doi.org/10.1186/s43058-026-00953-8). **Classification: Core.**

**Data/system.** Ten deidentified six-month interviews with embedded pragmatic clinical-trial researchers ranged from 3,376 to 9,262 words, with at most two participants/transcript. Four humans double-coded an 11-code descriptive/interpretive codebook. GPT-4o-2024-08-06 and GPT-4o-mini-2024-07-18 were called via the OpenAI API at temperature 1, top-p 1, 128k context, and maximum 5,000 tokens. The V4 protocol ran each model twice.

**Results.** In the V3 five-transcript stage, the LLM captured 327/530 human excerpts (61.7%; transcript range 42.4%–72.6%). Recall was 214/336 (63.7%) for descriptive codes and 112/194 (57.7%) for interpretive codes. It also found 206 correct excerpts missed by humans, but 396/929 extracted excerpts (42.6%) were incorrect. For V4 site-characteristic extraction at an 85% combined-run threshold, GPT-4o matched 48/54 (89%) and GPT-4o-mini 37/54 (69%). Word-count correlation was r=.230 and r=−.452, respectively. Estimated time fell 97% and cost 99%; about US$1/transcript for GPT-4o and US$0.04 for mini versus an estimated US$100 and five hours for human coding.

**Validity/ethics.** Exact-quote matching prevents nonexistent evidence strings but not misclassification; the authors note arbitrary Levenshtein thresholds. Brown IRB 2011002838 covered the work. Raw transcripts are restricted; codebook, scripts, and example outputs are shared. Data were anonymized and did not include health information, but API retention, business-associate agreement, vendor-security settings, and consent for vendor processing are **not reported**. Efficiency estimates should include expert review of the 42.6% false-positive burden.

### Sakaguchi, Sakama, and Watari — low-frequency and cultural-theme loss

**Citation and source.** Sakaguchi, Sakama, and Watari. “Evaluating ChatGPT in Qualitative Thematic Analysis With Human Researchers in the Japanese Clinical Context and Its Cultural Interpretation Challenges.” *Journal of Medical Internet Research* 27 (2025):e71521. DOI [10.2196/71521](https://doi.org/10.2196/71521). **Classification: Core.**

**Data/system.** Thirty Japanese semi-structured interviews with patients and providers at urban and rural hospitals explored “sacred moments.” Average interview duration was 28.43 minutes in the urban setting and 24.33 minutes in the rural setting. GPT-4o analyzed each interview three times. Humans independently performed reflexive thematic analysis; additional prompts invoked Charmaz grounded theory and Pope's five-step framework. Human saturation was reported after 27 interviews; 20% were recoded by a second researcher and member checking was used.

**Results.** Common descriptive themes exceeded 80% agreement. Culturally nuanced or low-frequency categories—including “difficult to answer/no experience” and “fate”—were below 30%; GPT counted “fate” zero times. Less frequent themes were generally identified inconsistently. Because structured presence/absence was unavailable, no kappa was computed. Human theme-name editing complicates exact comparison.

**Ethics.** Shimane protocol KS20230706-1, written consent, reuse authorization, anonymization, and password-protected storage are reported. Vendor/API retention and transmission settings are **not reported**. This is direct evidence that majority-pattern performance can coexist with loss of culturally specific and low-frequency meaning.

### Wachinger et al. — prompt repetition, chunking, and fabricated evidence

**Citation and source.** Wachinger et al. “Prompts, Pearls, Imperfections: Comparing ChatGPT and a Human Researcher in Qualitative Data Analysis.” *Qualitative Health Research* 35(9) (online 2024; issue 2025). DOI [10.1177/10497323241244669](https://doi.org/10.1177/10497323241244669). **Classification: Core method experiment; proxy/nonparticipant corpus.**

**Data/system/results.** A single 58-minute, more-than-7,000-word English interview between coauthors about AI in clinical practice was split into six chunks through a third-party ChatGPT splitter. GPT-3.5 received a general thematic-analysis prompt three times plus Charmaz and framework-analysis prompts. Human reflexive thematic analysis served as comparison. Same-prompt repetitions showed no systematically stronger overlap. The model manufactured a transcript continuation while loading, produced two nonexistent “verbatim” quotations, altered other quotations without marking, and could convincingly impose theoretical frameworks even when they did not fit.

**Boundary.** No IRB was sought because the data were coauthor-generated. The artificial single interview cannot establish clinical performance, but it is strong failure-mode evidence for chunking, prompt instability, fabricated provenance, and theory-induced circularity.

### Ronaghi et al. — large-scale applied health-services preprint

**Citation and source.** Ronaghi et al. “Large Language Models for Large-Scale, Rigorous Qualitative Analysis in Applied Health Services Research.” arXiv preprint (2026), [arXiv:2601.14478](https://arxiv.org/abs/2601.14478); related DOI [10.21203/rs.3.rs-7794878/v1](https://doi.org/10.21203/rs.3.rs-7794878/v1). **Classification: Core preprint.**

The paper reports a human–LLM framework applied to 167 interviews from multiple federally qualified health centers concerning diabetes care, combining qualitative synthesis of researcher summaries with deductive coding to refine an intervention. Exact model versions, run counts/seeds, quantitative validity statistics, IRB/consent, API governance, and full evaluator details are **not reported in this track's verified extraction**. It is retained as a scale comparator, not as decisive validity evidence.

## Detailed evidence: adjacent NLP validity, leakage, contamination, and privacy

### Yu, Liu, and He — identity/source signal can masquerade as semantics

**Citation and source.** Ding Yu, Zhuo Liu, and Hangfeng He. “Same Company, Same Signal: The Role of Identity in Earnings Call Transcripts.” *Findings of ACL 2025*, 18403–18422. DOI [10.18653/v1/2025.findings-acl.946](https://doi.org/10.18653/v1/2025.findings-acl.946); [ACL Anthology](https://aclanthology.org/2025.findings-acl.946/); code/data [piqueyd/Same-Company-Same-Signal](https://github.com/piqueyd/Same-Company-Same-Signal). **Classification: Adjacent; pivotal validity mechanism.**

**Data.** The DEC dataset contains 1,800 earnings records from 90 U.S. tickers across 20 quarters per ticker (2019–2023) and 11 sectors, with correct before/after-market timing. The paper contrasts DEC with EC (559 earnings, 272 tickers), MAEC-15 (765, 527), and MAEC-16 (1,400, 908), where most identities have about two or fewer observations.

**Models/baselines.** GPT-4o-2024-08-06 and Gemini-1.5-Flash perform direct prediction and summary/task prompting. Embeddings include OpenAI text-embedding-3-large, Google text-embedding-005/Gecko, and Voyage-Finance-2. Identity-aware and identity-free baselines include Random(Ticker), Random(All), prior earnings volatility (PEV), and same-ticker prior earnings volatility (STPEV). GPT few-shot prediction on DEC uses eight prior same-ticker examples. Trained systems use seed 2021, dataset random state 42, and an NVIDIA L40; model evaluation was a single run.

**Results.** On DEC, direct GPT-4o and Gemini prediction had the worst MSE (.345 and .339). Embedding methods averaged .260–.269; Random(Ticker) achieved .265; STPEV(mean) was best at .252. Identity-free Random(All) and PEV(mean) were .323 and .307. Within-ticker versus full-dataset mean cosine similarities were: OpenAI vanilla .900/.700; Gecko .958/.865; GPT-4o summary .920/.685; GPT-4o task .929/.724; Gemini summary .931/.713; Gemini task .918/.728. The average was .937/.738. Transcript-derived predictions correlated with STPEV(mean) at mean r=.847 across 2021–2023, with yearly means .815, .852, and .874; Random(All) correlations were .183, .007, and .004.

**Interpretation and transfer.** The evidence shows that repeated company identity and boilerplate can dominate representations and apparently predictive outputs. It is similarity/correlation evidence, not a causal counterfactual decomposition, and finance-to-clinical transfer is not automatic. Nonetheless, it makes participant-, site-, interviewer-, diagnosis-, and source-identity ablations mandatory in clinical qualitative evaluation. Repeated participants or sites can allow source style to stand in for meaning even when outputs look semantically coherent.

### Elangovan, He, and Verspoor — similarity-stratified leakage

**Citation.** Elangovan, He, and Verspoor. “Memorization vs. Generalization: Quantifying Data Leakage in NLP Performance Evaluation.” *EACL 2021*, 1325–1335. DOI [10.18653/v1/2021.eacl-main.113](https://doi.org/10.18653/v1/2021.eacl-main.113); [ACL Anthology](https://aclanthology.org/2021.eacl-main.113/). **Classification: Adjacent.**

Across AIMed, BC2GM, ChEMU, BC3ACT, and SST-2, the paper stratifies performance by train–test similarity. One illustrative result is SST-2 accuracy rising from 85.0 in the least-overlapping input bin to 96.8 in the most-overlapping bin. The implication is to report performance by nearest training/reference similarity and require participant/source-disjoint splits rather than only random text-unit splits.

### Liu et al. — long-context position effects

**Citation.** Liu et al. “Lost in the Middle: How Language Models Use Long Contexts.” *Transactions of the ACL* 12 (2024):157–173. DOI [10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638); [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/). **Classification: Adjacent.**

Multi-document question answering and key–value retrieval experiments with MPT-30B-Instruct, LongChat-13B-16K, GPT-3.5-Turbo, and Claude 1.3 reveal a U-shaped position curve: evidence in the middle of long contexts is used less reliably than evidence near the beginning or end. Clinical audits should randomize transcript, chunk, participant, and rare-case positions and quantify whether the same evidence survives.

### Lu et al.; Zhao et al. — exemplar and prompt order instability

Lu et al., “Fantastically Ordered Prompts and Where to Find Them: Overcoming Few-Shot Prompt Order Sensitivity,” *ACL 2022*, DOI [10.18653/v1/2022.acl-long.556](https://doi.org/10.18653/v1/2022.acl-long.556), shows that ordering few-shot exemplars can range from near-state-of-the-art to near-random performance; a good order does not transfer reliably, and entropy-based selection yields a 13% relative improvement across 11 classification tasks. Zhao et al., “Calibrate Before Use: Improving Few-Shot Performance of Language Models,” *ICML 2021*, [official paper](https://proceedings.mlr.press/v139/zhao21c.html), identifies majority-label, recency, and common-token biases and proposes contextual calibration. **Classification: Adjacent.**

For qualitative workflows, order tests must include codebook definitions, demonstrations, transcript/chunk order, and theme-list order. Merely reporting temperature zero is insufficient.

### Deng et al.; Balloccu et al. — contamination and upload-created leakage

Deng et al., “Investigating Data Contamination in Modern Benchmarks for Large Language Models,” *NAACL 2024*, DOI [10.18653/v1/2024.naacl-long.482](https://doi.org/10.18653/v1/2024.naacl-long.482), use TS-Guessing; ChatGPT and GPT-4 exactly guessed a missing MMLU option in 52% and 57% of cases. **Classification: Adjacent.** The method shows how public benchmark/reference exposure can be probed rather than assumed.

Balloccu et al., “Leak, Cheat, Repeat: Data Contamination and Evaluation Malpractices in Closed-Source LLMs,” *EACL 2024*, DOI [10.18653/v1/2024.eacl-long.5](https://doi.org/10.18653/v1/2024.eacl-long.5), review 255 papers and estimate that about 4.7 million samples from 263 benchmarks were exposed to OpenAI models during the first year through API use and applicable policies, alongside broader evaluation/reproducibility problems. **Classification: Adjacent.** Uploading gold themes or evaluation data can create both privacy risk and future benchmark contamination; vendor policies must be archived as they existed at study time.

**Core-paper implication.** TAMA, LLM-TA, Bennis/Mouwafaq, and Grover reuse previously published human themes or publicly described corpora with pretrained systems. This is a **reviewer-inferred risk**, not proof of memorization. No included clinical paper performs disease-name masking, missing-theme guessing, canary/placebo probes, or fresh-reference comparison.

### Morris et al.; Baroud et al. — embeddings and indirect identifiers remain sensitive

Morris et al., “Text Embeddings Reveal (Almost) As Much As Text,” *EMNLP 2023*, DOI [10.18653/v1/2023.emnlp-main.765](https://doi.org/10.18653/v1/2023.emnlp-main.765), demonstrate `Vec2Text` reconstruction: 92% of 32-token inputs were reconstructed exactly (BLEU 97.3), and 89% of full names were recovered from embeddings of MIMIC clinical notes. **Classification: Adjacent.** Hosted embedding APIs and vector stores should be governed like sensitive text, not harmless derived data.

Baroud et al., “Beyond De-Identification: A Structured Approach for Assessing and Reducing Privacy Risks in Clinical Text,” *PrivateNLP 2025*, DOI [10.18653/v1/2025.privatenlp-main.7](https://doi.org/10.18653/v1/2025.privatenlp-main.7), annotate 6,199 indirect identifiers in 100 MIMIC-III discharge summaries across nine categories. **Classification: Adjacent.** Removing explicit PHI does not eliminate combinations of contextual clues that can reidentify a participant.

### Van Aken et al. — aggregate clinical metrics hide demographic behavior

**Citation.** Van Aken et al. “What Do You See in this Patient? Behavioral Testing of Clinical NLP Models.” *ClinicalNLP 2022*. DOI [10.18653/v1/2022.clinicalnlp-1.7](https://doi.org/10.18653/v1/2022.clinicalnlp-1.7). **Classification: Adjacent.**

Behavioral and counterfactual testing of three clinical NLP models shows that outputs can change drastically under gender, age, and ethnicity perturbations despite similar aggregate AUROC. Clinical qualitative systems likewise need counterfactual swaps and subgroup-residual tests rather than relying on aggregate theme overlap.

## Cross-paper synthesis by validity threat

### 1. Identity, source, and domain confounding

Yu et al. supply a concrete warning: within-source identity can dominate a representation and correlate with a simple identity-conditioned historical baseline. Clinical qualitative corpora are especially vulnerable because participant, interviewer, clinic, disease, and transcript template can each be repeated and correlated with the human reference.

Evidence within the core literature is thin:

- Ashwin et al. test interviewer identity and find no evidence in their dataset, but do find respondent-attribute-linked error.
- Mathis et al. merge interviewer and participant turns, making speaker cues inseparable.
- Hill et al. explicitly exclude facilitator speech yet still find that facilitator segments drive much of the comprehensive error.
- Bai/Finkelstein supply disease background, leaving diagnosis cues available.
- No included core paper reports participant-, site-, interviewer-, and diagnosis-disjoint evaluation together; source-probe accuracy; identity-counterfactual swaps; or label-blind/disease-name-masked ablations.

**Required evaluation:** derive embeddings or model representations and train a source/participant/site probe; compare theme performance before/after masking boilerplate, demographics, interviewer turns, site/disease names, and metadata; use participant/site/source-disjoint folds; evaluate temporal and cross-domain transfer. If a source probe remains strong while semantic performance collapses out of source, claims of thematic understanding should be narrowed.

### 2. Participant overlap, similarity leakage, and representation confounds

Random splits at the utterance or chunk level are invalid when the same participant, interview, clinic, or templated interviewer language can appear on both sides. Elangovan et al. show why: high-overlap strata can look dramatically better than low-overlap strata. Yu et al. show why repeated identity changes the apparent signal. Even in zero-shot evaluations, public reference themes and disease descriptions may be present in model pretraining.

**Required reporting:** participant and source identifiers used for grouping; cross-participant/site/domain folds; nearest-reference similarity distributions; duplicate/near-duplicate detection; public availability dates for corpus and gold themes; model knowledge cutoff; and whether any prompt, vendor upload, or fine-tuning step exposed evaluation material.

### 3. Minority, rare, and negative-case preservation

The literature does not support a one-directional “LLMs omit minorities” claim. Failure is bidirectional:

- Sakaguchi et al. find low-frequency and culturally specific themes, including “fate,” are missed or unstable.
- LLM-TA's expert finds rare dramatic cardiac-arrest and financial experiences overrepresented.
- Hill et al. report weaker handling of nuanced/affective content and speaker-source errors.
- Ashwin et al. show systematic respondent-linked false positives and downstream distortion.

Most papers report theme-level hit rate or semantic overlap. These can be perfect while one participant's account supplies all evidence and contradictory cases disappear. TAMA's hit rate is reference-theme coverage, not participant coverage.

**Required metrics:** participant evidence recall and precision per theme; participant coverage and concentration (including maximum-share/Gini-type measures); theme-prevalence fidelity; contradictory/negative-case survival; rare-theme precision and recall at controlled prevalence; attribution accuracy to participant and source; and performance stratified by language/demographic/site. Use controlled insertions of rare, contradictory, ironic, and culturally coded cases at beginning, middle, and end positions.

### 4. Prompt, run, chunk, and order stability

Li, Bijker, Turner, Sakaguchi, and Wachinger provide repeated-run evidence, while Lu/Zhao/Liu establish exemplar-order and context-position effects. Stability is analytically distinct from validity:

- A system can repeat the same biased code reliably.
- Combining two runs or four iterations can increase recall by unioning outputs, but can also inflate false positives and make comparison with a single human reference circular.
- Temperature zero does not remove nondeterminism, model-version drift, prompt-order effects, or hidden API changes.

**Minimum robustness suite:** at least three independent runs; exact dated model identifier; prompt/codebook/demonstration order permutations; transcript/chunk shuffles; evidence-position randomization; alternate segmentation; and reporting of both pairwise agreement and semantic/content validity. Avoid selectively publishing the best run.

### 5. Contamination and evaluation circularity

Closed models can have seen published papers, theme labels, descriptions, or public corpora. An LLM judge may share the generator's biases. Model-generated reference synthesis and unioning iterations can turn a high Jaccard score into a circularity measure.

**Audit design:** use fresh or access-controlled interviews and an unpublished codebook; register public-availability dates; blind disease, site, investigator, and paper names; paraphrase theme labels without changing definitions; insert plausible placebo themes and secret canaries; ask missing-option/reference-guessing questions that do not expose source text; compare pre- and post-publication or open/local models; use an evaluator from a different model family only as a secondary diagnostic, never the sole ground truth.

### 6. Ethics, privacy, governance, and accountability

The core literature spans a wide governance range. Vikan, Mathis, and Grover use local inference; Hill uses secure institutional environments and separate secondary-use choice; Prescott refuses to upload participant text absent consent. In contrast, multiple studies using consumer or proprietary services do not report retention, training opt-out, processor/subprocessor, security configuration, business-associate agreement, data residency, deletion evidence, or participant authorization for vendor processing.

Deidentification is not sufficient. Baroud et al. show indirect identifiers persist; Morris et al. show embeddings can be inverted. A defensible protocol should report:

- IRB/REB determination, consent language, secondary-use scope, and whether LLM/vendor processing was disclosed;
- explicit/indirect identifier assessment, small-cell and quotation reidentification risk, and speaker-linkage risk;
- deployment mode, model/version/date, processor/subprocessors, data region, encryption, retention, training use, deletion verification, and incident response;
- whether embeddings/vector stores are treated as sensitive data;
- access control and logging for local systems as well as APIs;
- what data, prompts, outputs, and logs can be shared without reidentification;
- who reviews fabricated/incorrect evidence, who can stop deployment, and who is accountable for final claims.

Human oversight must be more than a final approval click. The evaluator should be independent of the reference creator when possible; qualitative-method and domain expertise should be represented separately; participant/member validation should be used for a purposive subset; and disagreements/negative cases should be retained rather than optimized away. Vikan et al. correctly locate authorship and accountability with humans.

### 7. Efficiency claims must include audit cost

Several studies report dramatic time/cost reductions, but verification can dominate:

- Turner et al. report 42.6% incorrect extracted excerpts despite high recall.
- Hill et al. report 12.4% comprehensive error.
- LLM-TA's expert identifies plausible but substantively wrong themes.
- Vikan et al. find no time saving under rigorous reflexive use.

Future comparisons should time prompt design, cleaning/segmentation, repeat runs, provenance checking, false-positive adjudication, privacy review, documentation, and model-version reruns—not only inference latency.

## Open gaps and ARR-level project candidates

| Priority | Candidate | What remains open | Closest prior work / novelty risk | Minimum differentiator |
|---:|---|---|---|---|
| 1 | **Participant/source/domain-confound and negative-case audit for clinical thematic analysis** | No located clinical study jointly tests participant/site/interviewer/diagnosis shortcuts, source-disjoint generalization, participant evidence distribution, and controlled rare/contradictory-case survival | Yu (identity signal), Ashwin (demographic residual bias), LLM-TA (rare overemphasis), Sakaguchi (low-frequency loss). **Novelty risk: medium**, because components exist separately | Fresh/private corpus; source/identity probes and counterfactual swaps; participant/site-disjoint folds; controlled rare/negative-case sentinels; position/order perturbations; participant-level provenance/fairness metrics; independent blinded evaluation |
| 2 | **Contamination-safe clinical qualitative benchmark** | Public human themes and disease labels may be present in pretraining; no direct contamination probe was located in a clinical TA paper | Deng/Balloccu establish general contamination methods; several clinical papers reuse public references. **Novelty risk: medium** | Unpublished reference/codebook; disease/name masking; canary, placebo-theme, theme-paraphrase, and missing-theme guessing probes; pre-registration and availability timeline |
| 3 | **Privacy–utility audit of local versus approved API qualitative coding** | Local inference is demonstrated, but empirical indirect-identifier/embedding-inversion risk and governance–utility tradeoffs are not jointly measured | Mathis/Vikan/Grover already establish local workflows; Morris/Baroud establish attacks. **Novelty risk: medium–high** | Realistic privacy attacks on raw text and embeddings; local 70B versus approved enterprise API; consent/retention/processor model cards; utility and representation effects by subgroup |
| 4 | **Prompt/order stability factorial** | Order and position effects are known, but their interaction with rare/negative-case preservation in clinical TA is not | Lu/Zhao/Liu; Li/Bijker/Wachinger repeat runs. **Novelty risk: high** if only rerunning prompts | Full factorial of codebook/exemplar/transcript/chunk order × rare-case frequency/position × source cues, with preregistered stability and validity metrics |
| 5 | **Prospective accountability workflow** | HITL systems are common; evaluator independence, stopping decisions, verification burden, and downstream clinical/research decisions are rarely measured | TAMA, Turner, Vikan. **Novelty risk: medium–high** | Prospective role randomization; independent qualitative/domain/participant adjudicators; logged overrides/stopping; downstream decision impact; total audit cost |

### Recommended study concept

**Working title:** *Whose Voice Survives? Auditing Participant, Source, and Negative-Case Confounds in LLM-Assisted Clinical Thematic Analysis*

**Core design.** Use at least two fresh, nonpublic clinical interview corpora from different sites/domains. Freeze human reference analyses before any model access. Create participant-, interviewer-, site-, and domain-disjoint evaluation partitions. Compare a locally hosted model, an approved proprietary model, and strong prompt/workflow baselines. Preserve exact quote-to-speaker provenance.

**Perturbations.** Mask or swap disease/site/participant/interviewer metadata; remove facilitator turns and boilerplate; counterfactually swap demographic descriptors without altering clinical content; shuffle transcript and chunk order; move controlled rare/negative cases to beginning/middle/end; vary their prevalence; introduce contradictions, irony, and culturally specific paraphrases. Add secret placebos/canaries for contamination tests.

**Outcomes.** Report theme/code semantic quality, evidence-provenance precision, participant evidence recall/precision, participant coverage/concentration, negative-case survival, rare-theme precision/recall, prevalence fidelity, source-probe accuracy, demographic/site residual-error tests, calibration, repeatability, and downstream decision/estimand changes. Report exact models, prompts, dates, runs, seeds where supported, and all failed runs.

**Human reference.** Blind qualitative-method and clinical-domain evaluators to model condition and source cues. Separate reference creators from system evaluators. Use plurality-aware adjudication rather than one canonical theme list, and obtain participant/member validation on a purposive subset. Audit disagreements and false negatives, not only matches.

**Governance.** Obtain explicit authorization for LLM processing; document deployment/processor/retention/training settings; evaluate indirect identifiers and embedding inversion; restrict quotations and participant linkage; preregister public-availability and contamination controls; make code/prompts/synthetic probes public even if transcripts cannot be.

## Exclusion and boundary candidates

| Candidate | Decision | Reason |
|---|---|---|
| Prescott et al. 2024, DOI 10.2196/54482 | Retain as core methods/ethics; exclude from clinical-interview subset | Inputs are 40 investigator-authored SMS prompts, not participant-generated interview/transcript data |
| Wachinger et al., DOI 10.1177/10497323241244669 | Retain as core failure-mode experiment; mark proxy/nonparticipant | One interview was generated between coauthors; no independent participant corpus |
| Castellanos et al. 2025, *JMIR AI* e64447, DOI [10.2196/64447](https://doi.org/10.2196/64447) | Adjacent/exclude from end-to-end TA set | Topic modeling plus LLM thematic summarization, not end-to-end transcript coding/theme generation |
| Psychiatric symptom extraction/summarization paper, PMID 39447159 | Exclude | Symptom extraction/summarization rather than qualitative coding or thematic analysis |
| “Linguistic Identity Leakage” (PrivateNLP 2026), [ACL Anthology](https://aclanthology.org/2026.privatenlp-main.8/) | Adjacent theory/exclude from empirical map | Conceptual taxonomy; empirical evaluation **not reported** |
| Psychotherapy paper, DOI [10.1016/j.ajp.2026.105071](https://doi.org/10.1016/j.ajp.2026.105071) | Await full text/exclude from quantitative synthesis | Abstract only was accessible in this track; detailed methods and statistics were not verified |
| Nursing paper, DOI [10.1016/j.ijnurstu.2026.105584](https://doi.org/10.1016/j.ijnurstu.2026.105584) | Await full text/exclude from quantitative synthesis | Abstract only was accessible in this track; detailed methods and statistics were not verified |
| Physician/patient qualitative studies about experiences *with* LLMs | Exclude unless LLM analyzes the data | The LLM is the research topic rather than the qualitative analyst |
| Generic topic modeling, sentiment classification, extraction, or summarization | Exclude from core | Does not operationalize qualitative coding/theme development; may be adjacent only if it isolates a named validity mechanism |

## Conclusions for the parent review

1. Frame identity/source/domain confounding as an open validity mechanism, not as a proven failure in every clinical dataset. Yu et al. establish plausibility and scale; Hill and Mathis show speaker/source pathways; direct clinical ablation remains missing.
2. Do not equate semantic overlap, theme hit rate, repeated-run kappa, or LLM-judge agreement with validity. Report evidence provenance, participant distribution, subgroup residual errors, and downstream distortion.
3. Treat minority/negative-case preservation as bidirectional: omission, dilution, misattribution, and sensational overrepresentation are all observed risks.
4. Mark contamination concerns as reviewer-inferred unless directly tested. Public references, disease names, model-assisted reference synthesis, and same-family judging make high agreement ambiguous.
5. Deidentification alone is inadequate. Consent/data-use authorization, indirect identifiers, embeddings, processor/retention/training settings, and accountable human review must be reported.
6. A paper limited to prompt/order robustness or another HITL pipeline has substantial novelty risk. The most defensible new contribution combines source-disjoint evaluation, controlled negative cases, contamination probes, and participant-level evidence accounting in fresh clinical data.

