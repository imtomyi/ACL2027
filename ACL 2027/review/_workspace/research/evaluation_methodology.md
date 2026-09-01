# Evaluation and qualitative-methodological foundations

**Track:** methodological traditions and evaluation of automated codes/themes  
**Search cutoff:** 2026-08-24 (America/Chicago)  
**Search date for this track:** 2026-08-24  
**Reviewer:** one reviewer/agent; no independent duplicate screening  
**Companion machine-readable record:** `evaluation_methodology.json`

## Executive finding

The central validity problem is not a shortage of scores. It is a mismatch between the qualitative claim and the construct that the score actually measures. Most automated-qualitative-analysis evaluations measure one or more of: agreement with one codebook, lexical or embedding similarity to one reference set, internal coherence, repeated-run similarity, quote presence, or preference by a small evaluator panel. These can be useful diagnostics, but none alone establishes that a thematic interpretation is insightful, well warranted, reflexively situated, attentive to negative cases, or adequate for its intended decision.

The mismatch is sharpest when a system claims **reflexive thematic analysis (RTA)** yet treats consensus codes or themes as objective ground truth, uses inter-rater agreement as accuracy, or describes themes as reproducible discoveries. Such evaluation is much more congruent with **coding-reliability TA**, and sometimes with **codebook TA**, than with RTA. Grounded theory, qualitative content analysis, Framework analysis, rapid analysis, and generic qualitative coding likewise have different products and quality criteria and should not be collapsed into “TA.”

The strongest defensible evaluation design is therefore a **method-aware, multi-construct evidence portfolio**: (1) declare the analytic tradition and intended claim; (2) preserve traceable passage-to-code-to-theme provenance; (3) assess evidence fidelity, participant and negative-case coverage, and unsupported claims; (4) compare interpretations without assuming uniqueness; (5) report sensitivity to seeds, prompts, sampling, and semantic-matching rules; and (6) use blinded, qualified human assessment with reported uncertainty and disagreement. LLM judges can supplement this design only after task-specific calibration against independent experts.

## 1. Methodological traditions are not interchangeable

| Tradition | Analytic purpose and product | Appropriate role of agreement/reproducibility | Evaluation implications for automation |
|---|---|---|---|
| **Coding-reliability TA** | Applies a relatively structured coding frame; themes are commonly domain/topic summaries; multiple coders seek accurate and reproducible application. | Agreement, adjudication, and inter-rater reliability can be congruent, particularly when the codebook is the product or fixed instrument. | Evaluate assignment accuracy, code definitions, reliability, prevalence effects, held-out cases, and reference construction. Do not generalize these results to interpretive RTA. |
| **Codebook TA** | Uses a structured codebook or matrix while acknowledging interpretation; includes Framework and template-like variants. | Team coding and structured comparison can help consistency, but a reliability coefficient need not define analytic truth. | Evaluate codebook usability, transparent evolution, case-by-code matrices, evidence retention, team deliberation, and fit to the research question. |
| **Reflexive TA** | The researcher actively constructs patterns of shared meaning organized around a central concept; subjectivity and reflexivity are analytic resources. | Independent replication, consensus coding, saturation, or IRR are not universal quality tests and can be methodologically incongruent when imposed as truth criteria. | Evaluate analytic coherence, evidentiary warrants, depth, reflexive positioning, alternative readings, negative cases, and usefulness for the research purpose. Treat references as situated interpretations, not gold labels. |
| **Grounded theory (GT)** | Iterative comparison of incidents and categories, memoing, theoretical sampling, and category integration toward a theory. Schools differ; axial coding is Straussian, not universal. | Early codes are usually interim analytic devices. Reproducing open-code labels is not the central validity claim. | Test whether the workflow supports constant comparison, memo and category provenance, theoretical sampling, category relationships, and theory development—not merely “open coding.” |
| **Qualitative content analysis (QCA)** | Systematic interpretation/classification of content. Conventional QCA derives categories from data; directed QCA starts with theory; summative QCA counts words/content and then interprets context. | A clear coding scheme and transparent category application are central; reliability may be useful depending on the design. | Evaluate category definitions and exhaustiveness, context-sensitive classification, inductive additions in directed QCA, and the distinction between counting and interpretation. |
| **Framework analysis / Framework Method** | Deductive, inductive, or mixed coding charted into a case-by-code matrix, retaining the context of each case and supporting team analysis. | Structured comparison is expected; transparency does not eliminate interpretation. | Preserve transcript/page/line pointers, matrix cells, codebook versions, case context, and analytic decisions. Do not infer GT merely from iterative coding. |
| **Rapid qualitative analysis** | Uses focused templates, matrices, and synthesis to answer time-sensitive, usually narrow questions; may omit formal line-by-line coding. | Quality depends on fit to the focused purpose and team expertise, not on speed alone. | Compare decision-relevant findings, omissions, verification workload, time, and contextual fidelity. “Faster” is not synonymous with equivalent or better interpretation. |
| **Generic coding / qualitative text classification** | Produces short labels, snippets, categories, or clusters without a declared qualitative epistemology or analytic end product. | Agreement and label matching may be legitimate task metrics. | Name the task as coding/classification. Do not infer RTA or GT from the words “inductive,” “open,” or “themes.” |

The taxonomy and congruence claims above are grounded in Braun and Clarke’s accounts of TA diversity and quality ([DOI](https://doi.org/10.1080/14780887.2020.1769238); [DOI](https://doi.org/10.1002/capr.12360); [authors’ 20 questions](https://study.sagepub.com/thematicanalysis/student-resources/20-questions)), Corbin and Strauss’s GT criteria ([DOI](https://doi.org/10.1007/BF00988593)), Hsieh and Shannon’s QCA distinctions ([DOI](https://doi.org/10.1177/1049732305276687)), Gale et al.’s Framework Method ([full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC3848812/)), and the PARRQA rapid-analysis guidance ([full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11468362/)).

McDonald, Schoenebeck, and Forte’s review of 251 CSCW papers provides direct evidence that labels are often conflated: only 20 of 85 papers reporting open coding described GT, only 9 of 27 reporting axial coding described GT, and fewer than half of 161 papers that coded to identify themes specified an analysis method. Their methodological conclusion is conditional rather than anti-reliability: IRR is useful for a predefined codebook, partitioned corpora, or quantitative use of codes, but disagreement can be analytically informative when codes are process rather than product ([author full text](https://yardi.people.si.umich.edu/pubs/Schoenebeck_Reliability_CSCW19.pdf); [DOI](https://doi.org/10.1145/3359174), pp. 13–17).

## 2. What current evaluation methods actually establish

| Evaluation operation | Defensible construct | What it does **not** establish without further evidence |
|---|---|---|
| Exact/fuzzy label overlap, ROUGE, BLEU, METEOR | Surface similarity to selected references | Interpretive equivalence, evidentiary adequacy, reflexivity, or uniqueness of a theme |
| Embedding cosine, BERTScore, MoverScore, BLEURT | Model-specific semantic proximity under a matching rule | That two themes make the same analytic claim or are supported by the same participants/evidence |
| One-to-one bipartite matching | Parsimonious alignment between similarly granular sets | Legitimate splits/merges or many-to-many relationships; it can penalize granularity differences |
| Many-to-many threshold matching | Partial accommodation of splits, merges, and granularity | Validity of the embedding space or threshold; minority evidence and interpretive warrants |
| Coverage / recall against a reference | Recovery of concepts in that reference | Recovery of concepts missed by every reference analyst; participant spread; non-uniqueness |
| Novelty / divergence | Difference from a pooled or reference code space | Error: difference can reflect a valuable standpoint or an unsupported invention |
| Internal coherence/distinctiveness | Within-theme similarity or between-theme separation | Qualitative depth; homogeneous embeddings may reward generic topical clusters |
| Repeated-run similarity | Procedural stability under the tested perturbation | Validity: a system can be stably biased, shallow, or unsupported |
| Quote grounding / provenance links | Traceability and checkability | Correctness of the interpretation, representativeness, or adequacy of omitted evidence |
| Inter-rater reliability | Reliability of specified judgments under prevalence and design conditions | Truth, validity, or methodological quality across all qualitative traditions |
| LLM-as-judge | Agreement with that judge’s rubric/application | Independent human validity, especially with same-family self-preference or order bias |
| Human preference/rating | Evaluator perception under a protocol | General validity unless evaluators, sampling, blinding, constructs, disagreement, and uncertainty are reported |

This distinction follows the measurement principle that a theoretical construct, its operationalization, and the evidence for reliability and validity must be separated ([Jacobs and Wallach, FAccT 2021](https://doi.org/10.1145/3442188.3445901)). The original lexical/semantic metrics were developed mainly for summarization, translation, captioning, or general text generation—not for interpretive thematic equivalence: [ROUGE](https://aclanthology.org/W04-1013/), [BERTScore](https://openreview.net/forum?id=SkeHuCVFDr), [MoverScore](https://doi.org/10.18653/v1/D19-1053), and [BLEURT](https://doi.org/10.18653/v1/2020.acl-main.704). Tay et al. demonstrate a concrete failure mode: ROUGE can treat texts about the same aspect but opposite polarity as similar, and results vary with configuration ([DOI](https://doi.org/10.18653/v1/U19-1008)). Task-specific validation is therefore required.

## 3. Verified study-level evidence

### Plurality-aware and semantic matching

- **Chen et al., 2026, “A Computational Method for Measuring ‘Open Codes’ in Qualitative Analysis.”** The Aggregate Code Space (ACS) pools and LLM-merges coder outputs; Coverage, Overlap, Novelty, and Jensen–Shannon Divergence are intended as a joint profile, not a ranking or fixed pass threshold. The paper explicitly rejects a singular correct inductive answer and tests ten runs per condition. Coefficients of variation below .1 and divergence near .01 show procedural stability in this experiment, not construct validity. Synthetic edge-case flooding can increase Coverage, Overlap, and Novelty, while hallucination reduces coverage/overlap and increases divergence. The single 127-message dataset, LLM-mediated merging, and inability to represent concepts missed by all coders limit generalization. Evidence: §§2.1–2.2, 3, 5–6 and Appendix A, pp. 41741–41749 ([ACL Anthology](https://aclanthology.org/2026.findings-acl.2073/); [DOI](https://doi.org/10.18653/v1/2026.findings-acl.2073)).

- **Zhong, Wang, and Field, 2025, HICode.** Theme and segment precision/recall use many-to-many embedding matches at cosine thresholds .4, .45, and .5, a better structural fit than forced one-to-one matching when themes split or merge. Results are reported over five runs with confidence intervals. In an Astro human evaluation by two original annotators, agreement was low (Krippendorff’s alpha .31); HICode’s human precision/recall (.72/.74) differed materially from cosine scores (.53/.51), and TopicGPT’s human precision/recall (.18/.33) differed from cosine (.04/.49). The authors identify conceptual matches that cosine missed. This validates neither the reference as unique nor the threshold; it does show that embedding matching cannot substitute for expert interpretation. Evidence: §4, pp. 31062–31065, human evaluation and limitations ([ACL Anthology](https://aclanthology.org/2025.emnlp-main.1580/); [DOI](https://doi.org/10.18653/v1/2025.emnlp-main.1580)).

- **Parfenova et al., 2025.** The task is best classified as generic inductive sentence coding: a code is a word/phrase expressing a sentence’s main idea. The study compares ROUGE and BERTScore against consensus references for 600 question–code pairs and includes a very small expert assessment (three experts; 15 sentences). Human alternatives could be preferred to the reference, while LLM codes could be closer to the reference but less analytically deep; reported alpha was .2. This is direct evidence that reference proximity and qualitative preference can diverge, but it does not evaluate theme generation. Evidence: task/data/evaluation and human-evaluation sections ([ACL Anthology](https://aclanthology.org/2025.findings-naacl.361/); [DOI](https://doi.org/10.18653/v1/2025.findings-naacl.361)).

- **Perez, Bhaduri, and Chadha, 2026, ICR position paper.** Five open-survey datasets compare human and LLM concept inventories over ten model runs, manually mapping concepts. The paper commendably treats the human analysis as situated. However, its “true negative” is impossible under the stated comparison universe—the union of concepts present in either set—so its reported accuracy reduces to `TP/(TP+FP+FN)`, mathematically Jaccard similarity after interpretive manual mapping. The human coder count, expertise, and IRR are not reported. Evidence: metric definition and experimental sections, pp. 1036–1047 ([ACL Anthology](https://aclanthology.org/2026.gem-main.81/); [DOI](https://doi.org/10.18653/v1/2026.gem-main.81)).

### Reference agreement and codebook-style evaluation

- **Dai, Xiong, and Ku, 2023.** Humans and GPT-3.5 co-construct a final codebook; assignment is assessed with Cohen’s kappa and embedding similarity to an author codebook. Human–machine kappa was .87/.81 on two reported settings, compared with original human agreement .66/.77; cosine similarity was .886/.890 and accuracy .84/.83. Because the system helped construct the reference, the high agreement is not an independent test of inductive discovery. The workflow is a codebook/coding-reliability hybrid, not RTA. Evidence: methods, evaluation, and discussion ([ACL Anthology](https://aclanthology.org/2023.findings-emnlp.669/); [DOI](https://doi.org/10.18653/v1/2023.findings-emnlp.669)).

- **Rao et al., 2025, QuaLLM.** The pipeline extracts concerns and quotes, assigns an externally specified four-to-five-topic taxonomy, and estimates prevalence; this is hybrid computational content analysis rather than RTA. Factuality precision, completeness recall, classification accuracy, prevalence agreement, and topic distinctness/coverage are reported. Two researchers jointly annotated/evaluated 125 submissions (2,511 comments); a separate appendix exercise with three annotators and 100 samples reports Fleiss kappa .59/.63 for human labels and .54/.61 for human–LLM judgments. “Coverage” here is topic coverage, not participant- or meaning-level coverage. Evidence: §§3–5 and appendix ([ACL Anthology](https://aclanthology.org/2025.findings-naacl.74/); [DOI](https://doi.org/10.18653/v1/2025.findings-naacl.74)).

- **AlGhamdi, 2026.** A 2012 PhD analysis is compared with four Claude Code Opus 4.5 sessions. Reported code F1 ranges 55.9–87.6 and theme agreement 90.9–100; structured prompts improve code agreement and inter-session theme agreement averages 86.1. The author explicitly warns that the study uses one reference interpretation, F1 does not capture depth/reflexivity, the public thesis could be contaminated, and four sessions from one system do not establish generality. The exact independence of manual match adjudication is not reported in the material inspected. This is an explicit coding-reliability framework. ([DOI](https://doi.org/10.1177/16094069261462093); [OSF](https://doi.org/10.17605/OSF.IO/AJPCW)).

### Multi-agent and end-to-end thematic systems

- **Xu et al., 2026, TAMA.** Twelve human themes from three analysts’ consensus analysis are called reliable ground truth. Evaluation combines expert criteria (Coverage, Actionability, Distinctiveness, Relevance) with all-MiniLM cosine threshold .60. The reported “Jaccard” is not set Jaccard: it is the fraction of all human×LLM pairs above threshold; human-theme hit rate does not penalize extra LLM themes. Distinctiveness averages within-theme cosine similarity, which can reward semantically homogeneous topical clusters. A GPT-4o-mini quote-grounding evaluator and the generating system are not independent. An expert stopping rule is essential because a G-Eval score plateau near 4.0 led to over-refinement/off-topic output instead of the target 4.5. Limitations include one clinical setting, possible confirmation bias because an evaluator helped create the reference, five lay evaluators without qualitative expertise, threshold dependence, no repeat-run stability, and no unique human truth. The operationalization is coding-reliability/codebook TA despite broader TA language. Evidence: methods, evaluation, results, limitations, and metric definitions in appendices ([ACM DOI](https://doi.org/10.1145/3828752)).

- **Yi et al., Auto-TA.** The system renames three automatic diagnostics using Lincoln and Guba’s qualitative trustworthiness terms: “credibility/confirmability” is the percentage of extracted quotes used in at least one theme; “dependability” is bidirectional ROUGE between themes from ten runs; “transferability” is ROUGE between themes from 7-transcript and 2-transcript subsets. These operationalizations do not measure the named constructs: quote reuse is not credibility/confirmability, lexical repeatability is not dependability of an auditable process, and same-corpus subset similarity is not transferability through thick description and contextual judgment. The audit log and quote IDs are useful provenance mechanisms, but the metrics remain lexical and reference-free rather than validity evidence. Evidence: evaluation/metric definitions and limitations in arXiv v2 ([arXiv](https://arxiv.org/abs/2506.23998); [DOI](https://doi.org/10.48550/arXiv.2506.23998)). Publication/peer-review status of the inspected version: arXiv; other status not independently verified.

- **Yi et al., SFT-TA.** The paper uses the same 12 reference themes as training targets: ten are used for training and two for validation, with 30 LLM-paraphrased variants per theme that are human reviewed. Evaluation then gives every generated theme a best-of-12 match using fuzzy matching, cosine, BLEU, and METEOR, so it cannot establish out-of-reference or out-of-domain generalization. Four raters (one surgeon, one qualitative analyst, two laypeople) evaluate outputs; human IRR and a full statistical analysis are not reported. A GPT-4o pairwise judge introduces same-family circularity. The copied Auto-TA credibility/dependability/transferability labels retain the construct mismatch. Evidence: methods, evaluation, appendices, arXiv v1 ([arXiv](https://arxiv.org/abs/2509.17167); [DOI](https://doi.org/10.48550/arXiv.2509.17167)). The inspected PDF says PMLR/ML4H 2025 with volume “XXX”; final bibliographic/peer-review status is not reported.

- **Yi et al., 2025, evaluation position paper.** It proposes one-to-one maximum-weight matching with lexical/semantic metrics, coverage/novelty/redundancy, repeated-seed stability, bootstrap uncertainty, and passage/participant coverage. These are useful ingredients, but the proposal is not empirically validated and conflicts with its own recognition that interpretations can align many-to-many. It also describes RTA with two-coder consensus/reliability procedures that are methodologically closer to coding-reliability TA. Evidence: methods review and proposed framework, arXiv v2 ([arXiv](https://arxiv.org/abs/2509.14597); [DOI](https://doi.org/10.48550/arXiv.2509.14597)). Status: arXiv/workshop position paper; peer-review status not reported.

### Provenance, auditability, and evidence fidelity

- **Yi et al., 2026, full-provenance refinement.** Persistent IDs connect transcript turns, chunks, quotes, codes, subthemes, and themes; parent–child edges and an action ledger record role, action, input, output, justification, and timestamp. Five seeds and an early-stopping Jaccard rule are reported. This is the most complete inspected process-provenance design. Evaluation still uses GPT-4o-mini as generator/judge, cosine overlap to human themes, and a composite of judge fitness/coverage, parsimony, consistency, and reusability. The authors acknowledge same-family judge bias, topical cosine limits, abstraction, post-hoc iteration, metric overlap, and need for domain experts. Provenance makes claims inspectable; it does not validate them. Evidence: architecture, metrics, experiments, and limitations, arXiv v1 ([arXiv](https://arxiv.org/abs/2603.08989); [DOI](https://doi.org/10.48550/arXiv.2603.08989)). Status: arXiv; manuscript states submission to AMIA 2026, not a verified acceptance.

- **Jowsey et al., 2025, “Frankenstein…”** Across five public-health TA datasets, a first-output Copilot analysis had little theme overlap with published analyses, particularly for two discursive TA studies. Neither humans nor Copilot reported participant spread; Copilot evidence concentrated in the first two to three pages even for corpora over 150 pages. Exact quote audit found 79.1% (SD 27.1) correct human quotes versus 36.0% (SD 43.4) correct Copilot quotes, and 57.5% (SD 44.5) fabricated Copilot quotes. The detailed text contains a conflicting 44.5% value; the table/abstract support 57.5%, so the discrepancy should be reported. One of five Copilot outputs had no fabricated quote. This study directly demonstrates why quote verification and positional/participant coverage matter, but it tests one minimally prompted proprietary assistant over heterogeneous methods. Evidence: methods, Tables/results, limitations ([PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0330217); [DOI](https://doi.org/10.1371/journal.pone.0330217)).

- **QualAnalyzer, 2026.** Each processed segment retains prompt, input, output, model configuration, row range, and timestamp. In one deductive case, two GPT-5.2 passes over 23 transcripts produced kappa 1.0 for binary decisions yet showed systematic excess mentions relative to a published human codebook. This is a valuable demonstration that consistency can coexist with systematic error. Atomistic processing can lose holistic context, and complete logs can still go unaudited. Evidence: system/case-study/limitations sections, arXiv v1 ([arXiv](https://arxiv.org/abs/2604.03820); [DOI](https://doi.org/10.48550/arXiv.2604.03820)). Status: arXiv/BEA submission; acceptance not verified.

### Human evaluation and LLM judging

- **CentaurTA, 2026.** An 18-item code and 12-item theme binary-constraint library covers context alignment, over-abstraction, clarity, evidence, completeness, faithful inference, and concision. Three domain experts reached rubric kappa .78. One expert supplied 300 code judgments for judge validation; the reported LLM-judge accuracy was 90%, expert accuracy 89%, and kappa .68. Quality peaked around ten iterations and then declined, supporting early stopping. Strength: an explicit rubric and some human calibration. Limits: binary judgments are coarse, only one expert/domain underlies the main judge validation, and the judge model’s independence from the generator is not reported. Evidence: rubric construction, judge validation, experiments, limitations ([ACL Anthology](https://aclanthology.org/2026.findings-acl.778/); [DOI](https://doi.org/10.18653/v1/2026.findings-acl.778)).

- **Hill et al., 2026.** One seven-participant focus group is evaluated in deductive and inductive modes using two blinded humans, GPT-5, Claude 4, and QualiGPT. Deductive human and LLM agreement was 92.7% and 93.5%, respectively, but both kappa values were .34 because code prevalence was only 7.8%; Gwet’s AC1 was .92/.93. Only GPT-5 was non-inferior in inductive ratings (p=.043; five-point Likert scale; margin .5), assessed by one qualitative researcher. Strict quote hallucination was 1.2%, but expanded and comprehensive definitions yielded 8.6% and 12.4%. Humans were more relational, affective, and latent; LLMs were more system/process focused. Calling the adjudicated reference/IRR design “reflexive” is incongruent with RTA; it is a codebook/coding-reliability test. Evidence: methods, results, qualitative comparison, limitations ([PLOS Digital Health](https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0001189); [DOI](https://doi.org/10.1371/journal.pdig.0001189)).

- **Montes et al., 2025.** Fifteen software-engineer well-being interviews were pre-coded by two experienced researchers; LLMs handled later phases. Across 96 blinded human-versus-LLM sets, LLM output was preferred in 61% and human output in 37%; only five evaluations were complete agreements and no IRR statistic is reported. Twenty-four code sets were rated on eight criteria; latent-semantic interpretation was weakest (weighted average 2.59), with fragmentation and unsupported justification. Pipeline prompts were tuned and the best pipeline selected on the same corpus, with no held-out data or repeated-run stability, so preference does not establish generalization. Evidence: methodology, results, limitations, arXiv v1 ([arXiv](https://arxiv.org/abs/2510.18456); [DOI](https://doi.org/10.48550/arXiv.2510.18456)). Status: preprint.

- **Bedemariam et al., 2025.** Human and LLM judges rate internal alignment among a generated theme name, description, and selected quote for 70 summaries from a non-public survey corpus exceeding 13,000 comments. Human–model agreement is 76–79%, kappa .34–.44, and ordinal alpha .49–.60; model–model agreement is often higher. Human judge count/expertise is not reported. The authors observe that LLM judges over-rate broad topical similarity and miss incomplete coverage or misaligned quotes. Crucially, the task assesses internal consistency of generated artifacts, not fidelity or coverage against the full corpus. Evidence: methods, results, discussion, arXiv ([arXiv](https://arxiv.org/abs/2501.08167); [DOI](https://doi.org/10.48550/arXiv.2501.08167)). Status: preprint.

General-purpose judge evidence reinforces these cautions. G-Eval was validated on summarization/dialogue, not thematic interpretation, and reports bias toward LLM-generated text ([EMNLP 2023](https://aclanthology.org/2023.emnlp-main.153/)). MT-Bench documents position, verbosity, and self-enhancement biases ([NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html)); order can reverse pairwise outcomes ([ACL 2024](https://aclanthology.org/2024.acl-long.511/)); and evaluators can recognize and favor their own model family’s generations ([NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7e6f8ff22020ee270c7e6488b7c99e5a-Abstract-Conference.html)). A qualitative-output judge should therefore be randomized for order, tested across independent model families and repeat runs, calibrated against blinded domain/qualitative experts, and accompanied by error analysis and agreement—not reported as an oracle.

## 4. Metric–construct failures that should be called out explicitly

1. **Trustworthiness relabeling:** Auto-TA’s quote-use, repeated-run ROUGE, and subset ROUGE do not operationalize credibility/confirmability, dependability, and transferability as used in qualitative methodology.
2. **Non-standard metric naming:** TAMA’s “Jaccard” is a proportion of thresholded cross-set pairs, not intersection-over-union. Its hit rate fails to penalize extra themes.
3. **Undefined negatives:** ICR defines the comparison universe as the union of observed concepts, leaving no true-negative concepts; “accuracy” reduces to Jaccard after manual concept alignment.
4. **Training/reference leakage:** SFT-TA evaluates generated themes by best matching against the same 12-theme universe used for training/validation.
5. **Reference circularity:** Dai et al.’s LLM helps construct the final codebook against which it is evaluated.
6. **Best-match inflation:** Per-output best-of-many similarity can reward overgeneration unless unmatched outputs, redundancy, and multiplicity are penalized.
7. **Granularity distortion:** One-to-one matching penalizes legitimate theme splits/merges; many-to-many thresholding helps but remains threshold- and embedding-dependent.
8. **Stability–validity conflation:** Identical or lexically similar repeated outputs may be consistently biased. QualAnalyzer’s two perfectly consistent passes with systematic excess coding are a direct counterexample.
9. **Coherence–depth conflation:** Embedding homogeneity can reward broad topical clusters and penalize complex themes connecting tension or contradiction.
10. **Internal-alignment substitution:** A theme, description, and quote can be mutually consistent while omitting most participants or misrepresenting the corpus.
11. **Prevalence-sensitive reliability:** High percent agreement with low kappa in Hill et al. shows why a single reliability statistic is uninterpretable without prevalence, unit, marginals, and disagreement analysis.
12. **Self-judging circularity:** Same-family generator/judge evaluation can reflect self-recognition or shared bias rather than human-aligned quality.

## 5. Recommended method-aware quality rubric

Score each dimension separately: **0 = absent or incongruent; 1 = partial/unclear; 2 = adequate for the study’s stated claim.** Do not sum scores into a “best paper” ranking.

| Dimension | A score of 2 requires |
|---|---|
| Analytic identity and congruence | Explicit qualitative tradition, epistemic stance, output definition, and procedures/evaluation consistent with that tradition |
| Analytic contract | Research question, unit of analysis, intended claim level (manifest/categorical/latent/theoretical), human and machine roles, and what counts as success specified before evaluation |
| Dataset and sampling adequacy | Documents/participants, language, lengths, context, sensitive status, inclusion process, and relevant identity/source/time splits reported |
| Workflow transparency | Exact model/version, prompts, context/chunking, temperature, tools, fine-tuning/retrieval, human edits, number of runs/seeds, and stopping rules reported |
| Reference and plurality design | Reference construction and analyst standpoint documented; multiple defensible readings allowed; disagreement and alternatives retained rather than erased |
| Evidence fidelity | Each code/theme traceable to exact sources; random/stratified quote audit; unsupported, altered, and fabricated evidence separately reported |
| Coverage and negative cases | Passage and participant spread, unrepresented participants, minority/negative cases, contradictions, and corpus-position effects measured |
| Semantic matching validity | Matching topology and threshold justified; expert validation sample, threshold sensitivity, unmatched items, splits/merges, and overgeneration reported |
| Stability and sensitivity | Crossed perturbations over seeds, prompts, ordering, sampling/chunking, models and—when relevant—analysts; uncertainty and substantive change, not just lexical change, reported |
| Human evaluation | Qualified and relevant evaluators, blinded/randomized sampling, explicit rubric, independent ratings, disagreements, reliability/uncertainty, and workload reported |
| LLM-judge validity | Judge independent of generator where possible; order randomized; repeat/multi-family judges; expert calibration and error analysis; prompts/version exposed |
| Statistical adequacy | Unit of analysis and independence correct; denominators, effect sizes, intervals, multiplicity and prevalence reported; ordinal data handled appropriately |
| Reflexivity and accountability | Analyst positionality, rationale for AI delegation, human responsibility, stakeholder/participant role where appropriate, and consequences of error considered |
| Reproducibility and governance | Data/code/prompt availability or justified restrictions; privacy/API retention/de-identification/ethics; complete, usable audit artifacts |
| Claim proportionality | Conclusions stay within dataset, method, comparison, judge, and deployment scope; efficiency includes verification and correction time |

**Interpretation-blocking red flags** (requiring qualification rather than automatic exclusion) are: fabricated/non-verifiable quotations; evaluation on leaked training references; RTA validity claimed solely from consensus/IRR; a same-family judge presented as independent truth without calibration; a mislabeled metric central to the claim; best-of-many matching without false-positive/overgeneration accounting; and no source-level evidence access for a fidelity claim.

Human-evaluation reporting should additionally follow the basic reproducibility logic in van der Lee et al. ([INLG 2019](https://doi.org/10.18653/v1/W19-8643)) and Howcroft et al.’s finding that NLG papers use more than 200 inconsistent quality terms and often omit evaluator, sample, rating, and statistical details ([INLG 2020](https://doi.org/10.18653/v1/2020.inlg-1.23)).

## 6. Candidate gaps, novelty risks, and suitable evidence

| Candidate unresolved gap | Closest work / novelty collision | Why unresolved | Minimum persuasive study |
|---|---|---|---|
| **Method-aware evaluation without a unique gold interpretation** | Chen ACS; HICode; ICR; 2025 evaluation position; Pi et al. landscape | Existing methods either pool the observed code space, retain a human reference, lack validated constructs, or are position frameworks. None validates a portfolio across TA traditions. | Preregister distinct coding-reliability, codebook, and reflexive tasks; multiple analyst interpretations; expert construct validation; show when rankings change by analytic contract. |
| **Validated semantic equivalence for codes/themes** | HICode many-to-many; BERTScore/MoverScore; ICR manual mapping | Thresholds and embeddings are not validated for interpretive equivalence; split/merge and contradiction remain difficult. | Multi-domain expert pair/set judgments with rationales; calibrate thresholds/topology; held-out domains/models; report ambiguity and disagreement rather than force labels. |
| **Participant/negative-case preservation** | Frankenstein; evaluation position; QuaLLM topic coverage; provenance paper | No inspected system jointly measures participant spread, minority/negative-case survival, contradiction, and unsupported synthesis end to end. | Public multi-speaker corpora with participant/evidence IDs; stratified recall for rare/negative cases; adversarial removal/insertion; qualitative expert review. |
| **Provenance-aware validity, not merely logging** | Full-provenance refinement; QualAnalyzer; Auto-TA; TAMA quote judge | Logs improve inspectability, but current composites and judges do not demonstrate that evidence is representative or interpretations warranted. | Machine-checkable provenance schema plus independent stratified audits of quote exactness, entailment, omission, participant spread, and audit completion/usability. |
| **Stability as an uncertainty envelope** | Chen ten runs; Auto-TA ROUGE; AlGhamdi four sessions; full-provenance five seeds | Most studies vary one factor, equate similarity with quality, or omit substantive adjudication. | Crossed seed×prompt×ordering×sample×model×analyst design; variance decomposition; distinguish label, evidence, interpretation, and decision stability. |
| **Independent LLM-judge validation for qualitative output** | CentaurTA; TAMA; Bedemariam; general judge-bias papers | Domain/rubric calibration is small, often one expert, and same-family dependence persists. | Blinded multi-expert gold *judgment sample* (not gold themes), multiple independent judge families, randomized order, adversarial cases, calibration/error/uncertainty reporting. |
| **Prospective workflow value and verification burden** | TAMA; rapid-analysis comparisons; small tool user studies | Preference and automatic similarity omit verification, correction, reflexive work, and downstream decision effects. | Prospective analyst study measuring time by stage, edits, detected/undetected errors, analytic depth, confidence calibration, and downstream use; include no-AI and constrained-assistant arms. |
| **Latent/critical interpretation evaluation** | Pi et al.’s M1–M4 framework; Hill qualitative comparison; Montes latent-semantic ratings | Current systems and metrics perform best on manifest/categorical meaning and have no validated test of warranted latent or theory-mediated interpretation. | Corpus supporting competing readings and counterevidence; analyst rationale chains; blinded experts assess warrants, theory fit, alternative readings, and harm—not reference wording. |
| **Unseen-domain/reference generalization** | HICode multi-dataset; SFT-TA; TAMA clinical line | Small/public/single-domain studies, prompt tuning on evaluation data, and reference leakage leave robustness uncertain. | Held-out datasets, institutions, speakers and time; frozen prompts; contamination assessment; open and proprietary models; domain-expert safety review. |
| **Construct-valid metric naming** | Auto-TA and TAMA failures; Jacobs & Wallach | No empirical audit maps commonly used “credibility,” “coverage,” “coherence,” etc. to qualitative constructs and validates them. | Expert concept elicitation, construct map, convergent/discriminant tests, failure cases, and reporting standard. This is feasible but must go beyond terminological critique. |

**Most defensible ARR opportunity (reviewer judgment):** a provenance- and plurality-aware evaluation suite that measures evidence/participant coverage, unsupported claims, many-to-many interpretive alignment, and perturbation stability under an explicit analytic contract. Novelty risk is **medium**, because Chen, HICode, CentaurTA, the provenance paper, and the 2025 position paper each cover parts. Novelty requires empirical construct validation and a crossed, held-out evaluation—not simply combining their metric names.

Pi et al.’s 2026 landscape preprint is especially important for novelty checking. It separates manifest description, categorical themes, latent interpretation, and theory-mediated meaning and argues that evidence standards must change with claim level; it also calls for analytic contracts, trace-linked rationales, counterexamples, contradiction checks, uncertainty, and abstention ([arXiv](https://arxiv.org/abs/2601.11739); [DOI](https://doi.org/10.48550/arXiv.2601.11739)). Treat it as a conceptual/landscape source, not validation of a benchmark.

## 7. Inclusion and exclusion recommendations for the parent review

### Core-method/evaluation inclusions

Include Braun & Clarke; Corbin & Strauss; Hsieh & Shannon; Gale et al.; McDonald et al.; Chen et al.; HICode; Parfenova et al. 2025; Dai et al.; QuaLLM; TAMA; Auto-TA; SFT-TA; the 2025 evaluation position; the 2026 full-provenance paper; CentaurTA; QualAnalyzer; Jowsey et al.; Hill et al.; Montes et al.; ICR; and AlGhamdi. Label preprints/position papers separately and do not treat proposals as validated metrics.

### Adjacent inclusions

Retain ROUGE, BERTScore, MoverScore, BLEURT, Red-faced ROUGE, G-Eval, MT-Bench, order-bias and self-preference judge papers, Jacobs & Wallach, NLG human-evaluation guidance, the Framework Method, PARRQA, and Taylor et al.’s direct rapid-versus-thematic comparison. Taylor et al. report 43 versus 116.5 hours for analysis management and 100 versus 126.5 total team hours; rapid analysis recovered 79% of TA findings and TA recovered 63% of rapid findings, with 55 of 59 recommendations overlapping. Different teams and situated interpretation confound equivalence, and “more findings” is not intrinsically better ([BMJ Open full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6194404/); [DOI](https://doi.org/10.1136/bmjopen-2017-019993)).

### Exclusion rules for this track

- Exclude pure topic modeling/clustering, summarization, sentiment, and fixed-label classification from the **core** unless they contribute a directly relevant qualitative-evaluation method.
- Exclude product demos without source-level evidence or evaluative design; retain in a technology map only.
- Exclude secondary reviews as technical evidence; they may support citation chasing/search completeness.
- Exclude papers using manual TA only to analyze interviews about an unrelated system.
- Exclude inaccessible abstract-only records from methodological claims; log them as “awaiting full text,” not as included evidence.
- Do not exclude a study merely for methodological incongruence; include it if it evaluates automated qualitative work, then code claimed versus operationalized method separately.

## 8. Search and verification log

Searches were run on 2026-08-24. Discovery used web indexing and official publisher/repository pages, then full texts were inspected where accessible. Interface-wide result counts were **not reported by the interface** for every query below. Consequently this track does not supply a deduplicated PRISMA count; it supplies independently verified evidence to be merged with the parent review’s database exports. Citation counts were not retrieved for this track.

Exact retained queries (verbatim):

1. `"Frankenstein, thematic analysis and generative AI"`
2. `"Large Language Models in Thematic Analysis: Prompt Engineering, Evaluation, and Guidelines"`
3. `"From Code Variability to Theme Convergence" thematic analysis LLM`
4. `site:aclanthology.org/2026.gem-main "Inductive Conceptual Rating"`
5. `site:aclanthology.org/2026.gem-main Perez Bhaduri Chadha "Inductive Conceptual Rating"`
6. `site:aclanthology.org/2026.gem-main. "Semiotic-Hermeneutic"`
7. `Braun Clarke 2021 one size fits all quality practice reflexive thematic analysis PDF`
8. `Braun Clarke 2021 comparing reflexive thematic analysis other pattern-based approaches PDF CAPR 12360`
9. `Corbin Strauss 1990 grounded theory procedures canons evaluative criteria full text PDF`
10. `Hsieh Shannon 2005 three approaches qualitative content analysis full text`
11. `"One size fits all? What counts as quality practice" PDF Braun Clarke Hayfield Terry`
12. `doi 10.1080/14780887.2020.1769238 PDF`
13. `site:uwe-repository.worktribe.com 1769238 Braun Clarke`
14. `Braun Clarke Hayfield Terry thematic analysis coding reliability codebook reflexive three types full text`
15. `"coding reliability approaches" "codebook approaches" "reflexive approaches" thematic analysis Braun`
16. `"reflexive TA" "codebook TA" "coding reliability TA"`
17. `Gale Heath Cameron Rashid Redwood 2013 framework method PMC full text`
18. `Taylor Henshall Kenyon Litchfield Greenfield 2018 rapid qualitative analysis BMJ Open PMC`
19. `PARRQA framework rapid qualitative analysis consensus 2024 DOI`
20. `McDonald Schoenebeck Forte 2019 Reliability and Inter-rater Reliability in Qualitative Research CSCW full text`
21. `"Can rapid approaches to qualitative analysis deliver timely, valid findings"`
22. `site:pmc.ncbi.nlm.nih.gov rapid thematic analysis Taylor Henshall Kenyon Litchfield Greenfield 2018`
23. `site:aclanthology.org G-Eval NLG evaluation using GPT-4 with better human alignment 2023`
24. `site:proceedings.neurips.cc LLM evaluators recognize and favor their own generations 2024`
25. `site:aclanthology.org "Large Language Models are not Fair Evaluators"`
26. `site:proceedings.neurips.cc Judging LLM-as-a-Judge MT-Bench Chatbot Arena 2023`
27. `"Potential and perils of large language models as judges of unstructured textual data"`
28. `arxiv 2501.08167 LLM judges unstructured textual data qualitative`
29. `site:openreview.net BERTScore Evaluating Text Generation with BERT ICLR 2020`
30. `site:aclanthology.org MoverScore Text Generation Evaluating with Contextualized Embeddings Earth Mover Distance`
31. `site:aclanthology.org BLEURT Learning Robust Metrics for Text Generation ACL 2020`
32. `site:aclanthology.org ROUGE package automatic evaluation summaries 2004`
33. `BERTScore Evaluating Text Generation with BERT OpenReview SkeHuCVFDr`
34. `site:openreview.net/forum?id=SkeHuCVFDr`
35. `site:aclanthology.org "Twenty Years of Confusion in Human Evaluation"`
36. `site:dl.acm.org "Measurement and Fairness" Jacobs Wallach 2021`
37. `site:dl.acm.org "The Fallacy of AI Functionality" Raji 2022`
38. `site:aclanthology.org "Best practices for the human evaluation of automatically generated text"`
39. `Jacobs Wallach Measurement and Fairness FAccT 2021 DOI`
40. `Raji Fallacy of AI Functionality FAccT 2022 DOI`
41. `site:dl.acm.org/doi/10.1145/3828752 TAMA thematic analysis`
42. `arxiv 2506.23998 Auto-TA Towards Scalable Automated Thematic Analysis`
43. `arxiv 2509.17167 SFT-TA thematic analysis`
44. `arxiv 2603.08989 provenance thematic analysis`

Full texts inspected for the core methodological/evaluation claims included the supplied/local TAMA, Auto-TA, SFT-TA, evaluation-position, and full-provenance manuscripts; official ACL papers for Chen, HICode, Parfenova, Dai, QuaLLM, CentaurTA, and ICR; publisher/full-text versions for Braun and Clarke, McDonald et al., Hsieh and Shannon, Gale et al., Taylor et al., PARRQA, Jowsey et al., and Hill et al.; and the cited preprints. Where only publication metadata rather than a methodological passage was verified, this report does not make a detailed technical claim.

## 9. Limitations of this track

This was a single-reviewer methodological track conducted in parallel with broader database searches. The web-search interface did not expose stable record counts, so its queries cannot independently support PRISMA numerators. Forward/backward chaining was targeted rather than demonstrably exhaustive. Publication status for several 2025–2026 manuscripts was not independently confirmed beyond the inspected version. Some studies use private data, preventing source-level replication. All reviewer critiques above are interpretations grounded in the cited metric definitions and methods; they are not necessarily author-stated limitations.

