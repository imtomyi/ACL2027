# Expanded report revision ledger

**Target:** `research/report_draft.md`  
**Ledger basis:** the completed 2020–2024/undated and 2025 second-pass impact memos, the current 2026 full-text outcomes, and the provisional cross-stream consolidation supplied on 24 August 2026.  
**Editing rule:** do not patch the report from provisional totals. Freeze the consolidated master, publication-family ledger, and review flow first; then apply the section instructions below in one coordinated pass. Line anchors refer to the current draft and will move once editing begins.

## Freeze gates and global replacements

### Counts: stable discovery totals versus provisional evidence totals

| Quantity | Status for the later patch | Required handling |
|---|---|---|
| Database exports: 1,556 records; 196 exact DOI/title duplicates; 1,360-record union | Preserve unless the final flow builder finds a source-export defect | These are discovery/deduplication counts, not the evidence-master size. Preserve source counts at current lines 53–64. |
| Old evidence flow: 60 sought, 2 not retrieved, 58 assessed, 1 excluded, 57 retained = 41 core + 12 adjacent + 4 contextual | **Stale** | Replace at current lines 70, 370, and 481 from the final `review_flow.json`; do not update by hand. |
| Old master: 70 or 73 evidence rows and 44 core | **Stale** | Replace at current lines 70, 90, 386, 388, 435, 467, and 481. The draft mixes a pre-chain 70-row master with the later 73-row master. |
| Current master before second-pass merges | 73 evidence / 44 core-quality | Audit input only. |
| Completed 2020–2024/undated companion | 24 evidence / 23 core-quality / 1 adjacent | Frozen companion input. |
| Completed 2025 companion | 70 evidence / 61 core-quality / 9 adjacent | Frozen companion input. Drop the 9 adjacent quality rows during consolidation; adjacent evidence remains. |
| Current 2026 companion | 69 evidence / 52 core-quality / 17 non-core field values; the latest synthesis divides the latter into 10 adjacent + 7 contextual | **Provisional pending companion freeze.** It terminalizes 271 database candidates, 16 forward-only candidates, and 5 cross-stream handoffs and logs 14 nonretrievals. |
| Projected consolidated evidence | 236 evidence / 180 core-quality / 56 adjacent-contextual | **Provisional only:** 73 + 24 + 70 + 69 = 236 and 44 + 23 + 61 + 52 = 180. Use only after schema, family, and collision validation. |

The final patch must compute, not assume, all of the following from the frozen artifacts:

1. title/abstract decisions for all 1,360 union records, with any remaining unresolved stratum stated explicitly;
2. database full texts sought, not retrieved, assessed, excluded after full text, and retained;
3. forward/backward-chain reports identified, sought, not retrieved, assessed, excluded, and retained, kept separate from the database union until the final PRISMA reconciliation;
4. retained primary reports by core/adjacent/contextual class;
5. methodological/evaluation foundations cited but not counted as PRISMA-included primary reports;
6. consolidated evidence rows, unique publication families, and core-only quality rows; and
7. every exclusion and nonretrieval, with a record-specific reason and provenance.

Do not add the three second-pass stream flows mechanically. Their assignment frames differ, and handoffs/version families cross years. The final reconciliation must assert the PRISMA identities `sought = not retrieved + assessed`, `assessed = excluded after full text + retained`, and `retained = core + adjacent + contextual`, while separately reconciling master-only methodological foundations.

### Publication-family and status gates

Apply these one-time family decisions before any count, table, or bibliography is regenerated:

- retain the inspected 2026 *Qualitative Research in Psychology* NITA VOR, `nguyen_trung_nguyen_2026_nita`, once; suppress TA-0336;
- map TA-0016 and TA-0477 to the existing `bai_2026_three_datasets` family;
- map TA-1285 to the existing `centaurta_2026` family;
- count TA-0955 and TA-1299 once as the CHALET/TOCHI family;
- count TA-1121's arXiv:2309.10771 and 2025 journal VOR, DOI 10.1016/j.chbah.2025.100144, once;
- preserve TA-1332 as a distinct CSCL 2025 contribution analysis but flag its reuse of the TA-1334/2024 dataset and codebooks;
- retain the 2024 arXiv/ICWSM-2025 Islam–Goldwasser family once from the 2020–2024 companion, not again in 2025;
- retain one VOR for the TA-0664/TA-0665 maternal-health family;
- treat FC15 and FC09 as AIED 2026 electronic/conference manuscripts with formal Springer 2027 proceedings citations, labeling the post-cutoff bibliographic year explicitly and counting each family once;
- label FC11 as a SEET 2025 event paper whose proceedings record appeared in 2026;
- do not assert that FC14/CATALYST is the same Duolingo lineage as DOI 10.1080/10447318.2024.2427361 unless a full-text comparison later establishes overlap;
- correct FC07's status inconsistency: if acceptance is unverified, it cannot simultaneously be labeled peer reviewed; and
- preserve the exact Auto-TA and SFT-TA histories: Auto-TA is arXiv:2506.23998v2 with OpenReview label `ACL-SRW 2025 Poster` and no verified archival ACL Anthology paper; SFT-TA is arXiv:2509.17167v1 with OpenReview label `ML4H 2025 RejectfromProceedingsasFindingsPoster`, and `PMLR XXX` is not an archival citation.

### Claim discipline for every section

- Scope absence, novelty, “most complete,” “strongest,” “first,” and gap claims to **reviewer judgment among the inspected full texts**. Where plausible reports were not retrieved, state that limitation beside the claim.
- Use full-text evidence only for methods, human roles, results, and limitations. Abstract-only reports may appear solely in the screening/nonretrieval ledger.
- Separate an author's method label from the reviewer's operational classification. Do not pool fixed-label classification, topic discovery, codebook application, open coding, and interpretive theme construction as one task or one performance denominator.
- Cite factual statements beside the sentence with an official paper/VOR/preprint record. Repository claims require both the official paper/preprint citation and the repository link.
- Prefer peer-reviewed VORs; label preprints, posters, protocols, secondary reviews, workshop-only records, and post-cutoff formal publications explicitly.
- Preserve the K–12 corpus wording already corrected at current line 157: 45,000 total messages; 21,147 overlapping three-message windows in the inductive phases; and a message- and conversation-disjoint 2,560-message human-validation sample.

## Executive synthesis

**Current anchors:** lines 8–20.

- Keep the developmental arc at line 10, but extend the endpoint beyond CentaurTA/Muse/one clinical ledger. Add researcher-primary/noncoding workflows (NITA), versioned/reflexive provenance (Reflexis and ROCK), confidence/disagreement triage, and branchable graph or staged memo workflows. This prevents the executive from presenting autonomous hierarchy generation as the only frontier.
- At line 12, retain the bounded conclusion that code application can approach human reliability, then add a counterweight from the expanded evidence: Parkington's workflows missed 190/428 human excerpts; Berkmortel's models applied 181/183 codes versus 138 for humans with low alpha/overcoding; and ICR showed human reliability .86–1.00 versus LLM .35–.76 even when lexical scores were high. The supported conclusion remains assistance and bounded coding, not autonomous interpretive authority.
- Expand line 14's construct-validity paragraph with four direct demonstrations: QualiGPT's GPT self-agreement (.87) exceeding human-inclusive agreement (about .46); IDEAlign's human-oracle correlations (.906/.812) exceeding its best automated correlations (.618/.683) and style edits inflating embeddings by up to 82%; Dörfel's semantic mapping/stability (13/14 over .60; Jaccard .83) coexisting with unit overlap .39 and lost domain distinctions; and Han's LLM-judge correlations/ICC showing coarse-order but not magnitude validity. Add a sentence that verbal confidence is not calibrated evidence: FC15 reports accuracy .441/.520/.338 versus confidence .908/.922/.891 and ECE .467/.403/.553; a .95 anchor was adopted 96.5% and collapsed AUC to .518.
- Replace line 16's “two recent advances” frame. No-gold evaluation and provenance now have multiple overlapping implementations. Name plural code spaces, source-symmetric expert comparison, IDEAlign-style perturbation validation, exact quote/source ledgers, ROCK's versioned standard, Reflexis drift/positionality logs, Nyaaba/MindCoder/ROSAnnotator human-editable paths, and Teleoscope-style branchable provenance. The remaining joint gap is validation of exactness, omission, participant spread, rare/negative cases, and auditor usability across domains and independent experts.
- Extend line 18's minority/cultural conflict with Subbiah's 154 longitudinal interviews across three open models and five seeds: demographic conditioning changed semantics, affect, and themes; experts found stereotyping and omission of death, violence, abuse, and addiction. Add Lukito's interviewer-identity confound and Rizvi/Sakib/Wei as adjacent shortcut/platform evidence. Keep the bidirectional framing: erasure, distortion, refusal, stereotyping, and overemphasis all occur.
- Retain line 20's Rank-1 direction only as reviewer judgment. Narrow novelty to the **joint** benchmark: speaker/source lineage + controlled participant/interviewer/site/identity perturbations + participant/negative-case coverage + independent warrants. Reflexis, ROCK, Parkington, Subbiah, Lukito, MindCoder, ROSAnnotator, and NITA mean that provenance, demographic sensitivity, reflexivity prompts, or a quote ledger alone can no longer carry the novelty claim.
- Do not insert final corpus counts in the executive until the master and flow freeze. If a count is useful, report both unique retained evidence records and core empirical reports, not a single unlabeled “papers reviewed” number.

## 1. Introduction and motivation

**Current anchors:** lines 22–28.

- Preserve the motivation and task-heterogeneity argument.
- Add noncoding theme development, confidence/disagreement triage, automated memo/schema refinement, source-linked quote verification, and workflow standards to the examples at line 26. NITA is the clearest counterexample to the assumption that theme development always proceeds through machine coding; LOGOS and Neo-Grounded Theory show implemented schema/theory-like optimization without establishing full grounded-theory development.
- At line 28, describe the evidence base by final frozen classes and status (core, adjacent/contextual, methodological foundations; peer reviewed versus non-archival/preprint) rather than the current implicit 73-row map. State that later-version records were family-deduplicated and that formal post-cutoff citations are labeled.
- Add one sentence explaining the review's claim hierarchy: fixed-label/codebook accuracy supports a bounded coding claim; interpretive, reflexive, clinical, or theory-development claims require stronger source, plurality, expert, and governance evidence.

## 2. Review questions

**Current anchors:** lines 30–41.

- Keep all eight RQs and their numbering. Do not adopt the differently numbered shorthand in the stream memos.
- RQ1: explicitly include noncoding theme development, memoing/theoretical integration, stopping, confidence/abstention, and provenance/verification as tasks now seen in implementations.
- RQ2: keep claimed and operationalized methods separate and add “noncoding qualitative synthesis” where NITA does not fit a code-first taxonomy.
- RQ3: add confidence/diversity routing, model ensembles, deliberation versus independent agents, graph/version control, and stopping rules.
- RQ4: distinguish post-hoc checking/reference creation from intervention in the live analysis; include researcher-primary positionality/counterevidence work.
- RQ5: add quote exactness/alteration, omission/participant coverage, calibration/abstention, rationale fidelity, and verification burden.
- RQ6: add preprocessing/platform/language/time confounding, development-set reuse, label leakage, same-model deliberation, and anchoring of human revisions.
- RQ7: add provider assurances, API-key/code leakage, synthetic-participant substitution, and exclusion of reidentification-risk participants as possible silencing.
- RQ8: state that opportunities are assessed only after version-family deduplication and full-text inspection.

## 3. Search and screening methodology

**Current anchors:** lines 43–76.

- Preserve the eligibility criteria at line 47 but document the applied boundary now visible in the second passes: a paper may be core only when computation contributes to qualitative analysis itself; a paper using manual TA merely to evaluate an unrelated assistant remains excluded. Topic/classification records may be adjacent when they isolate a directly relevant validity mechanism.
- At line 49, expand the chaining description with the focused forward-chain streams and same-family resolution. State the stopping procedure actually achieved; do not claim citation saturation if forward chaining remained focused or if nonretrievals persist.
- Preserve the source-export and union arithmetic at lines 53–64 unless the final flow builder invalidates it.
- Replace line 70 completely with a machine-generated PRISMA paragraph and compact flow table. It must distinguish the 1,360 database union from chain-only candidates and reconcile full-text sought/not-retrieved/assessed/excluded/retained counts. Do not call deterministic triage labels eligibility decisions.
- Replace line 72's “612 uncertain remain” limitation with the final status distribution. The year-specific second passes resolved the assigned uncertain and unlinked high-priority records; any residual unscreened/uncertain union records must be counted exactly, not inherited from the old snapshot. Preserve the single-reviewer/no-independent-adjudication limitation.
- Report the stream-level audit trail in Appendix 19 rather than crowding the main methods narrative: 2020–2024/undated resolved 239 database records plus 6 forward-only records; 2025 resolved 188 database records, 4 handoffs, and 16 forward-only records; current 2026 work terminalizes 271 database candidates, 16 forward-only candidates, and 5 handoffs. These are audit strata, not additive unique-record totals until final family reconciliation.
- Update line 76 to the frozen consolidated schema/counts. Quality scores must be one per core record only; remove the nine 2025 adjacent quality rows from the final quality table. State how adjacent/contextual records are retained without quality totals.
- Add a short reproducibility paragraph naming the frozen artifacts: union export, final `review_flow.json`, consolidated master, year-resolution ledgers, nonretrieval log, publication-family ledger, 52-field extraction, 12-dimension core-quality table, and workbook build script/output.

## 4. Conceptual foundations of thematic analysis

**Current anchors:** lines 78–98, especially 88–98 (RQ2 synthesis).

- Preserve the conceptual distinctions at lines 80–86.
- Replace line 90's 44/32/10/1/1 counts. A provisional concatenation suggests 180 core records, 168 with both claimed and operationalized fields, 10 with neither, 1 claim-only, and 1 operationalized-only, but these values must be recomputed after family deduplication and reviewer recoding. Do not infer methodological congruence merely from nonempty free-text fields.
- Add the 2025 reviewer audit as a bounded result: **at least 15 material mismatches or narrowings among 61 inspected 2025 core reports**, explicitly a judgmental audit count rather than a population prevalence. Representative cases must include fixed-theme/fixed-label work called inductive or thematic (Hairston, Shah, Mackenzie, Shen, Borchers, Rodriguez, Relins), clustering/factor reduction called themes (Ghali, Sulaiman), and codebook/reliability procedures labeled reflexive (Parkington and HHitL-TA).
- Expand the reflexive/codebook row with Parkington, HHitL-TA, NITA, Vikan, and Reflexis. The assessment should distinguish researcher-primary reflexive assistance from automated pipelines borrowing reflexive terminology.
- Expand the grounded-theory row beyond two papers: Yue, LOGOS, Neo-Grounded Theory, the K–12 open/axial/selective instrument, the 2026 axial-coding system, and any retained proposal. State that hierarchies, ten refinement rounds, or axial labels demonstrate implemented schema operations, not theoretical sampling or validated theory generation.
- Add a noncoding/alternative-workflow row for NITA and any similar retained reports. This is necessary for RQ2 because “no coding” is a deliberate methodological position, not missing reporting.
- Add confidence that task labels are not performance-equivalent: fixed-label accuracy/κ/F1 cannot be summarized with open-ended code/theme validity. The revised table should show claim, actual operation, success criterion, and reviewer congruence.
- Recompute all claimed-versus-operationalized family counts from explicit reviewer codes. If those categories remain overlapping, label denominators and allow multi-label membership rather than presenting percentages that sum to 100%.

## 5. Taxonomy of computational approaches

**Current anchors:** lines 100–128 (RQ1 and RQ3).

- Replace “six operational families” at line 106 with an expanded, nonexclusive taxonomy. At minimum distinguish: (1) fixed/codebook assignment; (2) open-code suggestion and collaborative code development; (3) hierarchy/schema/axial refinement; (4) code-first end-to-end theme pipelines; (5) noncoding narrative/theme workflows; (6) interactive workbenches; (7) autonomous/role-prompted pipelines; (8) adaptation/fine-tuning/steering; (9) retrieval/evidence/provenance; and (10) evaluation, confidence, disagreement, and stopping.
- Add CollabCoder, Qualitative Code Suggestion, De Paoli's staged family, QualiGPT, Rasheed, Islam–Goldwasser, LOGOS, Neo-Grounded Theory, LLMCode, MindCoder, ROSAnnotator, NITA, Reflexis, Nyaaba, ROCK, and the axial system as representative systems. Keep the historical distinction between non-LLM CoAIcoder and LLM systems.
- Revise line 111: “multi-agent” can mean same-model role prompts, repeated agents, model ensembles, or genuinely different models. Add Borchers' result that only 5/432 contrasts favored multi-agent consensus while 65 favored single agents; do not call same-model consensus independent triangulation.
- Revise line 112's adaptation paragraph. Fine-tuning is not limited to Parfenova and SFT-TA: Ganesh shows task-specific fine-tuning outperforming in-context learning; Thomas/TA-0441 and TA-1307 use LoRA-like adaptation; TA-0089 reports unspecified fine-tuning; FC15 tests activation steering. Separate leakage-safe adaptation from reference-conditioned training and report held-out domain/concept evidence.
- Add confidence/diversity routing and abstention as an assurance family. FC15's severe confidence miscalibration means “confidence” cannot be treated as a trustworthy routing signal without calibration; Tajik's rationale similarity is useful as disagreement triage, not correctness.
- Rebuild the comparative architecture table at lines 117–126 from the consolidated core table. Keep a manageable set in the report, but cover each operational family and link the complete comparison in Appendix/workbook. Add columns for actual human intervention, source lineage, independence of evaluators, run control, and publication status.
- Replace line 128's RQ1 answer with a fuller task map: every visible artifact from familiarization proxies through reports now has an implementation, including noncoding themes and stopping. Keep the critical boundary: conceptual-model/theory development is implemented or claimed by LOGOS/Neo-GT/axial systems but remains weakly validated; familiarization is often retrieval/summarization rather than sustained engagement.

## 6. Human–AI collaboration models

**Current anchors:** lines 130–144 (RQ4).

- Rebuild the table around implemented intervention points. Keep setup-only, codebook supplier, proposal reviewer, iterative co-analysis, independent adjudication, stakeholder/participant validation, and human-primary analyst, but add “reference creator/post-hoc evaluator” so papers cannot receive a collaboration label merely because humans supplied or scored a benchmark.
- Expand setup-only/autonomous examples with current role-prompted systems, preserving the correction that the provenance/refinement system's “reviewer” is an LLM agent and no human participates in its evaluated loop.
- Expand iterative co-analysis with CollabCoder, QCS, LLMCode, HHitL-TA, MindCoder, ROSAnnotator, Nyaaba, Reflexis, and relevant graph/versioning systems. Log whether analysts can reject, backtrack, memo, preserve disagreement, and view the raw evidence.
- Replace line 141's bare “Rare” with evidence-calibrated wording. Participant/stakeholder validation of **AI-specific output** remains uncommon, but Lukito includes youth co-researchers/participant checks and some source analyses are member-checked. Inherited member checking does not validate a model's output.
- Replace line 142's Vikan-only human-primary row. Add NITA, Nyaaba, Reflexis, Bang, Hill, Zupic, and other researcher-led/offline workflows supported by inspected full text. Distinguish primary interpretive authority from final approval after an autonomous draft.
- Extend line 144's anchoring analysis: Qiao asks humans to accept AI-proposed codes; LLMCode lets analysts revise baselines after model exposure; HHitL-TA logs accept/merge/reject; NITA keeps positionality, counterevidence, theme retention, and meta-narrative with humans; Reflexis users valued drift/disagreement prompts but the 12-person study did not establish a causal improvement in analytic outcomes.
- Add a compact RQ4 distribution only after final recoding; human-role categories may be multi-stage and should use a clearly stated primary-role rule plus secondary flags.

## 7. Datasets and application domains

**Current anchors:** lines 146–169.

- Recompute any domain, language, sensitivity, dataset-size, and public/restricted counts from the consolidated evidence; do not infer denominators from the current short table.
- Preserve the corrected K–12 row at line 157 exactly: 45,000 total messages; 21,147 overlapping three-message windows in inductive phases; 2,560 message- and conversation-disjoint validation messages.
- Expand the representative dataset table with the strongest new validity cases rather than every corpus: Parkington mental-health transcripts/excerpts, Subbiah's 154 longitudinal interviews, Ghanaian/Nyaaba staged analysis, Lukito's youth corpus with interviewer effects, Bang's quote audit, CHALET's human–LLM disagreement set, and at least one multilingual/cross-cultural example from Finnish, Italian, Dutch, Ghanaian, Malaysian, Japanese, Kenyan-translated, Chinese, Korean, or China/Japan/Korea work.
- Rewrite line 167 from “limited non-English evidence” to “non-English and cross-cultural evidence exists but remains methodologically uneven.” Cite De Paoli's Italian interviews, Kousa's Finnish political text, Japanese clinical work, translated Kenyan/Ghanaian/Malaysian/Chinese examples as appropriate. TA-0577 remains abstract-only/nonretrieved and cannot support a method/result claim.
- Expand the dependency paragraph at line 165. Keep AAOCA as one family, and add: De Paoli's 2024 parent/Italian/saturation family; NITA–GAITA shared Down East corpus; Simon–Sankaranarayanan/CSCL shared survey and human analysis; TA-1332 reuse of TA-1334; QualiGPT overlapping preprints; Islam–Goldwasser reuse of two earlier advertising corpora/seed themes; Than, Gustavsen, Hairston, and other inherited human-analysis datasets. A reused corpus is useful evidence but not an independent replication.
- Soften line 165's “most important dependency correction” to “one major dependency cluster.” The enlarged corpus contains several consequential version, dataset, seed-theme, and human-reference families, and the review has no validated scale on which AAOCA is uniquely “most important.”
- Add a warning that very large post/social-media corpora do not equal participant-level qualitative breadth: the Bluesky pipeline assigned only 10.5m of 30.2m cleaned posts to identifiable microtopics and left 65% unassigned.

## 8. Evaluation practices

**Current anchors:** lines 171–207 (RQ5).

- Extend the metric table with quote exactness/alteration, source/participant coverage, omission, confidence calibration/abstention, rationale similarity, human verification burden, and workflow decision outcomes. For each, retain the four-way structure: intended construct, what the operation actually measures, what it cannot establish, and validation needed.
- Add controlled evidence that semantic metrics are style- and granularity-sensitive: IDEAlign's best correlations .618/.683 versus human-oracle .906/.812 and style-edit inflation up to 82%; Misra's context/duplication/theme-fit scores (38.9/28.5/19.2 and 45.6/29.5/27.1 for Gemma; 22.9/16.3/11.7 and 43.7/36.2/26.8 for Llama, with the paper's 46.8 narrative inconsistency flagged); and ICR's high lexical metrics but low interpretive reliability.
- Keep Dörfel at line 191 and add Parkington, QualiGPT, IDEAlign, Bang, Borchers, ICR, and Han as independent examples rather than replacing it. The synthesis should show several distinct divergences: reference similarity versus unit overlap; self-consistency versus human agreement; embedding similarity versus expert judgments; quote presence versus exactness; consensus versus benefit; lexical metrics versus ICR; and LLM-judge ordering versus magnitude.
- Replace line 193's “most developed no-single-gold diagnostic” superlative. Describe Chen/ACS as one well-developed pooled-code-space diagnostic and compare its flooding/shared-omission limits with QCS, source-symmetric verification, IDEAlign, Simon, Moskalewicz, ICR, and Han; the expanded evidence does not justify a unique “most developed” ranking.
- Add Parkington's exact source-coverage results: both workflows miss 190/428 human excerpts; out-of-box overlap is 238/428, knowledge-base overlap 124/428; 68/251 purported quotations in the knowledge-base condition are interpretive summaries. Add Bang's exact quote audit: 68% verbatim, 20% paraphrased, 6% partially hallucinated, 3% fully hallucinated, and 3% truncated.
- Add QualiGPT's human–human κ=.73, human-inclusive GPT-4 about .46, GPT self-κ=.87, and later GPT-4o/Claude .38/.42. State the denominators/design beside each result when patching from the extraction.
- Add Borchers' 5/432 versus 65/432 direction-of-benefit result and flag its unreconciled 77,273 reported decisions versus 500,256 implied by the stated factorial. Do not repeat the larger denominator as fact without author clarification.
- Add confidence/abstention evidence from FC15 and Tajik. Verbal confidence is grossly miscalibrated; rationale similarity has a large triage effect (d=1.16) but is not correctness.
- Strengthen the human-evaluation subsection with Parkington, IDEAlign, Simon, Moskalewicz, Han, CHALET, Reflexis, and Subbiah. Continue to report evaluator expertise, independence, sample size, blinding, reliability, statistical unit, and whether reference creators also judged output.
- Revise cost/workload at line 207 to make verification burden empirical: missed excerpts, altered/composite quotes, overcoding, and large candidate sets can erase nominal runtime savings. Add new time/cost numbers only where full-text denominators and whether review time was included are explicit.

## 9. Validity, reliability, and interpretability

**Current anchors:** lines 209–225.

- Keep the reference-is-not-ground-truth, reliability-is-not-validity, abstraction-is-not-quality, and warrants structure.
- Add QCS as evidence that a single reference assignment can undercount valid alternatives. Add Chen/ACS, source-symmetric comparison, IDEAlign, Simon, and Moskalewicz to show ways of preserving plurality—and each method's remaining dependency on its judges, pooled universe, or reference construction.
- Expand line 217 with QualiGPT, Dörfel, Jain/repeated-run work, De Paoli–Mathis saturation, and FC15. The revised claim is that repeated-run reliability exists, sometimes at high levels, but can coexist with shallow, biased, overconfident, or reference-conditioned output.
- Expand line 221 with Parkington/Gustavsen omissions, Berkmortel overcoding, Logan's iterative-versus-batch Jaccard advantage with rare themes still missed, and the Bluesky unassigned majority. Parsimony, broad coverage, and stability are design properties, not sufficient quality outcomes.
- Expand line 225's warrant discussion with Bang's quote audit, Mehta's altered/truncated/composite quotations, Parkington's summary-for-quotation substitutions, ICR, and Han. A matching quote can still be misattributed, selectively chosen, insufficient, or interpreted incorrectly.
- Add a short subsection or paragraph on calibration: confidence, same-family consensus, and LLM-judge scores should not be interpreted as epistemic certainty without human calibration and held-out failure tests.

## 10. Provenance, auditability, and reproducibility

**Current anchors:** lines 227–235.

- Preserve official paper/preprint citations beside every repository link at line 229. Add repositories only when the official paper/preprint or inspected full text verifies them.
- Replace “the most complete lineage architecture” with “one of the most explicit inspected lineage architectures.” Compare the clinical refinement pipeline with ROCK's exact source IDs/spans, codebooks, relationships, and versioned workflows; Reflexis's immutable code histories, drift alerts, and positionality prompts; Nyaaba's chats/revisions/memos; MindCoder/ROSAnnotator; NITA; Teleoscope's branchable graph provenance; and Bang/Parkington quote audits.
- Preserve the critical distinction that the provenance/refinement system's reviewer is an LLM agent, not a human. Keep its lack of independent human warrant validation.
- Expand line 231: a standard or ledger is an architecture, not evidence of adoption, privacy safety, representativeness, or interpretive validity. Reflexis's 12-person user study establishes perceived relevance/control, not an independent causal outcome. ROCK/ARC are standards/checklists and must be labeled as such.
- Keep the five-layer audit at line 233, but add version history, rejected alternatives, rationale fidelity, and negative-case/rare-case survival. The open joint validation target is exactness + warrant + omission/coverage + participant distribution + independent auditor usability.
- Update reproducibility examples with 2025–2026 resources and failures. Include the TA-1355 repository/API-key exposure and published-method/code contradictions as responsible-resource caveats, without reproducing the key. Continue to separate ethically restricted data from avoidable omissions of prompts/configurations.

## 11. Confounding, identity leakage, and shortcut learning

**Current anchors:** lines 237–247 (RQ6).

- Replace line 239's broad “no clinical TA study directly demonstrates” sentence. Direct evidence now includes Subbiah's demographic-conditioned semantic/affective/theme shifts, Lukito's interviewer-identity confound, Sakib's SDOH shortcut behavior, Rizvi's subgroup/keyword effects, and Wei's platform/language/time confounding. The defensible residual claim is narrower: **among inspected full texts, no end-to-end clinical theme benchmark jointly crossed participant/interviewer/site/source perturbations with participant-level evidence and independent warrant validation.**
- Add Subbiah's design and findings exactly: 154 longitudinal interviews; three open models; five seeds; demographic-conditioned shifts; expert reports of race/gender stereotyping and omitted deaths, violence, abuse, and addiction. Do not generalize beyond that corpus/models.
- Add Lukito's finding that topic models missed masking, self-doubt, and strengths and that diagnosis clustering was confounded by interviewer identity.
- Add development/reference leakage and anchoring: Flanders and LLMCode development reuse, Koh label leakage, SFT-TA's ten-of-twelve reference-theme paraphrase training, LLMCode baseline revision after model exposure, same-family judging, and AAOCA public-reference contamination risk.
- Add preprocessing/platform confounds (Na/Feng, Wei), class/prevalence confounds (Hairston, Than, Li, Osian), and source boundary/facilitator confounds. Keep the existing overlap, context-position, exemplar-order, and contamination discussion.
- Update the audit suite at line 247 to add platform/time/language-disjoint folds, development-set isolation, model-family-independent judges, confidence perturbation/anchors, human-before-AI baseline capture, and denominator reconciliation.

## 12. Ethics and high-stakes clinical use

**Current anchors:** lines 249–259 (RQ7).

- Retain local-inference and embedding/privacy examples, then broaden the evidence. Balt and Abramson provide positive restricted/local infrastructure examples; Mehta, the oncology comparison, and policy-analysis records illustrate incomplete provider/retention disclosure; Gustavsen documents exclusion of a reidentification-risk participant and explicitly notes the risk of silencing a marginalized voice.
- Add Kapania's evidence against substituting synthetic “participants” for situated people. Synthetic corpora may support controlled testing but cannot stand in for participant validation or lived experience.
- Add King as evidence that vendor privacy policies are fragmented and mutable, but do not reproduce the paper's broader default-training prose claim beyond what its table supports.
- Add the TA-1355 resource leak as a reproducibility/security failure without exposing the credential. Add provider terms, secrets scanning, code release review, and deletion verification to the governance checklist.
- Expand representational harm at line 257 with Subbiah's stereotyping/omission, Rizvi/Sakib shortcut findings, Wei's cross-platform/minority-removal risk, and Parkington/Gustavsen loss of emotion/domain distinctions. Retain the distinction between demonstrated harm in a study and reviewer-proposed risk.
- Keep the conclusion that full automation is not defensible for high-stakes interpretation on the inspected evidence. Human review must specify authority, expertise, independence, participant/stakeholder role, and the right to reject/stop—not merely assert “HITL.”

## 13. Critical synthesis

**Current anchors:** lines 261–288.

- Update “points of agreement” with a more precise consensus: bounded, explicit codebooks and source-visible intermediate artifacts generally improve tractability; performance remains conditional on prompts, model, segmentation, preprocessing, order, code prevalence, reference construction, and human intervention. Add Ganesh, Dunivin, Chen, Parker, and FC15/TA-0389 where task-matched.
- Expand the line 271 conflict paragraph beyond Dörfel and the original clinical examples. Add Parkington, QualiGPT, IDEAlign, Berkmortel, ICR, Bang, Han, and Subbiah. Organize by conflict rather than paper: high semantic similarity versus low unit/interpretive agreement; high self-stability versus low human agreement; exact-looking quotations versus alteration/hallucination; broad code coverage versus overcoding/omission; high confidence versus low accuracy; consensus versus no multi-agent benefit.
- Add TA-0389's deployment warning: test F1 .74–1.00 coexisted with deployment false-positive rates of 8–54%; critique improved F1 by .04–.25, but same-model/one-author anchoring remains.
- Expand the automation conflict with NITA, Nyaaba, Reflexis, Bang/Hill/Zupic, and the 2025 human-primary systems. The evidence favors bounded automation and visible human authority; it does not establish that researcher-primary workflows always save time or avoid anchoring.
- Replace the “partly closed” bullets at lines 277–282:
  - **No-gold/plurality:** Chen, source-symmetric comparison, QCS, IDEAlign, Simon, Moskalewicz, ICR, and Han provide partial solutions; multi-domain, multi-expert theme warrants remain open.
  - **Provenance:** Auto-TA/TAMA/Muse/clinical ledger, ROCK, Reflexis, Nyaaba, MindCoder, ROSAnnotator, NITA, Teleoscope, Bang, and Parkington make an architecture-only novelty claim untenable; joint validation remains open.
  - **Human feedback/reflexivity:** implemented widely, including Reflexis; prospective causal value, anchoring, burden, and longitudinal outcomes remain open.
  - **Multi-agent:** crowded; Borchers gives direct evidence that consensus often adds no benefit, and convergence may be flattening. Require ablation against strong single/sequential baselines.
  - **Fine-tuning/adaptation:** expand beyond Parfenova/SFT-TA to Ganesh, LoRA systems, reported fine-tuning, and activation steering. Leakage-safe held-out concept/domain generalization remains open.
  - **Stability:** repeated runs, iterative/batch comparisons, and saturation/confidence signals exist; crossed uncertainty plus substantive adjudication remains rare.
  - **Stopping:** simple no-new-theme, saturation-ratio, forced-allocation, fixed-round/trajectory, and confidence signals now exist; held-out transferable evidence-gain stopping remains open.
- Update the overall quality synthesis from the final core-only 12-dimension table. Do not report a mean/rank without dimensions, denominators, and sensitivity. Note that peer review and high total scores do not cure task/construct mismatch.
- Keep the bounded overall conclusion at line 288, but cite the expanded evidence and avoid a universal field-wide claim.

## 14. Research-gap matrix

**Current anchors:** lines 290–306 (RQ8).

Rebuild every “partial coverage” and “why unresolved” cell. Preserve the matrix columns required by the user: gap, partial papers, unresolved evidence, novelty risk, deadline feasibility, ARR significance, and recommended design.

- **Participant/minority/negative-case preservation (line 296):** add Parkington, Mehta, Gustavsen, Subbiah, Lukito, Rizvi, Sakib, Wei, Bang, and the newer provenance systems. The gap is not voice loss in general; it is a joint participant/source-aware, perturbation-tested, expert-warranted audit.
- **Identity/source/domain confounding (line 297):** remove “no direct ... ablation.” Cite direct demographic/interviewer/platform/keyword evidence. Retain the narrower absence of a joint clinical end-to-end theme benchmark with disjoint splits, counterfactuals, source probes, and participant evidence outcomes.
- **Plurality-aware quality (line 298):** add QCS, IDEAlign, Simon, Moskalewicz, ICR, Han, and Logan. Generic “agreement is not quality,” pairwise preference, or same-family judging is no longer novel. The gap is shared multi-domain, multi-expert warrant validation across analytic contracts and held-out models/domains.
- **Provenance-aware validity (line 299):** add ROCK, Reflexis, Nyaaba, MindCoder, ROSAnnotator, NITA, Teleoscope, Bang, and Parkington. A quote ledger or provenance interface alone has high novelty risk; validating exactness, omission, spread, counterevidence, and auditor use remains significant.
- **Cross-domain/model/temporal generalization (line 300):** add Than, Ganesh, TA-0389, Subbiah, and current multilingual/platform examples. Require frozen prompts, family-disjoint judges, site/participant splits, temporal versions, and full denominator/error reporting.
- **Stability (line 301):** add Jain, De Paoli–Mathis, Borchers, Logan, QualiGPT, and FC15. The novelty risk for repeated runs alone is very high. Retain crossed seed × prompt × order × sample × model × analyst perturbation tied to substantive/participant outcomes.
- **Stopping (line 302):** add CAILA no-new-theme, De Paoli saturation, TALLMesh allocation, LOGOS trajectories, LLMCode iteration, Teleoscope saturation confidence, and Logan iterative/batch comparisons. StopTA remains open only as a held-out, transferable balance of new supported evidence, minority recall, unsupported claims, stability, and verification burden.
- **Prospective workflow value (line 303):** add Reflexis, NITA, Nyaaba, MindCoder, LLMCode, and HHitL-TA. Reflexis already implements deliberation/positionality UI; novelty requires outcome validation, not the interface feature.
- **Hallucination/specificity (line 304):** add Bang, Mehta, Parkington, Cook, and Gustavsen with explicit fabricated/altered/paraphrased/composite/truncated/misattributed/unsupported/omitted categories.
- Add a **confidence/abstention and calibration** row. FC15 shows severe overconfidence, anchor adoption, and failed steering; Tajik supports triage but not correctness. A useful gap is calibrated abstention whose benefits survive model/domain shift and reduce human verification burden without hiding minority cases.
- Optionally add a **workflow security/governance** row if it can support an ACL contribution: API/credential leakage, proprietary data transfer, model drift, and audit artifacts. Keep it separate from a generic ethics checklist.
- Replace line 306 with a stronger novelty boundary: multi-agent roles, semantic overlap, quote/provenance ledgers, reflexivity prompts, repeated runs, and simple saturation/stopping rules all exist; a contribution must validate a construct, intervention, or failure mechanism against strong existing baselines.

## 15. Recommended ARR research direction

**Current anchors:** lines 308–366.

All three entries must retain the required fields: provisional title, central claim, research questions, novelty, datasets, experimental design, human evaluation, ethics, **key baselines**, expected contribution, major risk, mitigation, and October feasibility. Make “Key baselines” an explicit labeled paragraph for each project even where the current prose embeds them elsewhere.

### Rank 1 — VoiceTrace

- Keep Rank 1 provisionally; both completed memos and current 2026 evidence strengthen the failure mechanism.
- Rewrite novelty at line 320 to acknowledge Subbiah's direct demographic-conditioned effects, Lukito's interviewer confound, Parkington/Mehta/Gustavsen quote and omission failures, and ROCK/Reflexis/Nyaaba/MindCoder/ROSAnnotator/NITA/Teleoscope lineage. The defensible novelty is their **joint controlled evaluation**, not provenance or demographic sensitivity separately.
- Add Reflexis and ROCK as provenance/workflow baselines, Subbiah-style demographic perturbations, and a human-primary/NITA condition. Include a no-source-ID ablation and an exact-source ledger baseline.
- Keep participant/source-disjoint splits, rare/negative-case perturbations, expert warrants, and downstream conclusion change as the core contribution. Predeclare that source-probe success is diagnostic, not proof of causal shortcut use without ablation.
- Retain the data/ethics contingency: if authorized participant IDs and expert access are not already secured, do not rush clinical data; use a public nonclinical main experiment and scope clinical claims.

### Rank 2 — WarrantBench

- Keep Rank 2, but raise the novelty bar at line 342. Add IDEAlign's perturbations/triplets, Simon's blinded comparisons, Moskalewicz's specialist/lay judgments, ICR's interpretive reliability, Han's LLM-judge calibration, Misra's theme-fit dimensions, and Logan's iterative/batch comparison.
- Baselines must include ACS, source-symmetric Bradley–Terry, IDEAlign, one-to-one and many-to-many matching, ICR, human-oracle/reference creators, multiple cross-family judges, and quote/participant coverage. Do not use an LLM judge as the only verifier.
- Preserve alternative readings and disagreement; test held-out domain and held-out model family. The key contribution is cross-contract, source-grounded, theme-level multi-expert construct validation—not another scalar metric or slogan.

### Rank 3 — StopTA

- Keep Rank 3, but rewrite line 358 to acknowledge CAILA, De Paoli–Mathis, TALLMesh, LOGOS, LLMCode, Teleoscope, Logan, and confidence-based signals. “A stopping rule has not been proposed” is no longer defensible.
- Baselines must explicitly include no-new-theme, saturation ratio, fixed rounds, same- and cross-family judge thresholds, reference-similarity plateau, human stop, iterative-versus-batch processing, confidence/abstention, and Pareto-front reporting.
- Require a frozen rule on held-out domains/models that jointly handles marginal supported evidence, participant/minority recall, redundancy, unsupported claims, instability, and verification burden. Add an ablation showing which components drive transfer.

### Ranking statement

- The completed 2025 memo found no reason to reverse the order. The current 2026 evidence also narrows rather than closes VoiceTrace, WarrantBench, and StopTA. Confirm this once final quality/dataset feasibility is known.
- Keep the ranking explicitly reviewer judgment and conditional on local data authorization, expertise, engineering readiness, and the remaining seven-week schedule. Do not derive project rank from summed paper-quality scores.

## 16. Limitations of the review

**Current anchors:** lines 368–376.

- Replace line 370's “612 uncertain” and “57-report evidence map” with final flow counts. State exactly which union records remain unresolved, which full texts were not retrieved, which chain-only records remain unresolved, and how many reports were assessed. The older limitation is stale because the second-pass screening materially changed the status of the uncertain strata.
- Preserve single-reviewer screening/extraction, unavailable Web of Science/Scopus, nonauditable bulk Scholar access, fuzzy/title-only retrieval, and focused rather than exhaustive citation chaining. Add that several stream extractions were performed in parallel but not independently duplicated; schema assertions and exact-family deduplication improve reproducibility but do not create duplicate-reviewer agreement.
- Replace line 372's “cutoff is in the future relative to many indexes” with a precise near-cutoff limitation: online-first, accepted-manuscript, preprint, event-year, and formal-proceedings years can differ and statuses may change. Label FC15/FC09's 2026 electronic/2027 formal history and FC11's 2025 event/2026 proceedings history.
- Preserve the exact Auto-TA/SFT-TA OpenReview histories. Reaudit every current 2025-to-2026 family (TA-0514, TA-0601, TA-0767, NITA/TA-0771, TA-0838, TA-0840, TA-1355) against the final preferred record.
- List all plausible nonretrievals in Appendix 19 and state that no method/result claims derive from them. The six 2025 plausible-core nonretrievals include TA-0560, TA-0577, TA-0640, TA-0684, TA-0726, and FC25-008/LATA; add the 2020–2024 and 2026 lists from their resolution ledgers.
- Preserve heterogeneity/no-meta-analysis and reviewer-interpretation limitations. Add that provisional class labels, family resolution, and secondary-review overlap can alter counts; final counts must be generated, not narratively reconciled.

## 17. Conclusion

**Current anchors:** lines 378–382.

- Preserve the conclusion that LLMs can assist most visible workflow artifacts, but add noncoding themes, memos, confidence/disagreement triage, stopping, version control, and standards/checklists.
- Update “most defensible designs” to include editable/traceable artifacts, researcher authority, calibration, source/participant audits, independent evaluation, and explicit analytic contracts.
- Keep the field-level limitation bounded: evidence is strongest for specified code application and organization; weaker for reflexive, culturally situated, minority-sensitive, theory-building, and clinically consequential interpretation. Acknowledge direct new evidence rather than implying those regimes are unstudied.
- Replace the final novelty list with the narrowed joint targets: participant/source-confound control tied to voice preservation; cross-domain multi-expert warrants; held-out evidence-based stopping; or calibrated abstention/verification. Provenance, reflexivity UI, multi-agent consensus, simple stability, and simple saturation are components/baselines, not standalone novelty.

## 18. Complete references

**Current anchors:** lines 384–471.

- Delete and regenerate the entire section from the final consolidated evidence master plus every methodological/contextual foundation cited in the revised narrative. Do not manually append to the current 73-record list.
- Replace the stale “73 = 44 + 29 plus 3 contextual” statement and the 44/29/3 category headings with frozen totals. State clearly whether totals count unique publication families, evidence rows, core empirical reports, adjacent/contextual reports, and foundations.
- For every entry, use the final preferred record's complete verified title, author list, year, venue, volume/issue/pages or article number when available, publication type/status, DOI or official stable page, and preprint/version history. An arXiv DOI is not peer review. Do not use `et al.` where the consolidated source has complete authors.
- Cross-check every DOI/title pair and eliminate repository-only citations. Official paper/preprint records must appear beside repository claims in the prose.
- Order consistently (recommended: core, adjacent/contextual, methodological foundations; then alphabetically within category) and ensure every in-text citation has one reference and every reference is either retained evidence or an explicitly cited foundation.

### Mandatory companion-record inventory for regeneration

The final generator must include all retained, family-deduplicated records from these three companion sources. Keys are listed here to make omissions detectable; metadata must come from the JSON, not from this ledger.

**2020–2024/undated companion (24 evidence; 23 core + 1 adjacent):** `gao_2024_collabcoder`, `jiang_2021_supporting_serendipity`, `ganesh_2024_prompting_panacea`, `lancaster_2024_academic_integrity`, `kondo_2024_mixed_methods_chatgpt`, `mannstadt_2024_arthroplasty`, `liu_2024_potential_limits`, `khan_2024_controversial_topics`, `rasheed_2024_multi_agent`, `torii_2024_hci_horizons`, `fischer_biemann_2024_qda`, `breazu_2024_hate_speech`, `depaoli_mathis_2024_saturation`, `dunivin_2024_scalable_qualitative_coding`, `depaoli_2024_multilingual_italian`, `zhang_2024_qualigpt`, `parker_2024_educational_survey_feedback`, `depaoli_2024_inductive_thematic_analysis`, `kousa_2023_chatgpt_finnish_content_analysis`, `spinoso_2023_qualitative_code_suggestion`, `kirsten_2024_decoding_complexity`, `islam_goldwasser_2025_latent_themes`, `chen_2024_prompts_matter`, `spitale_2024_gender_fairness_depression`.

**2025 companion (70 evidence; 61 core + 9 adjacent):** `zhao_liu_2025_confidence_diversity`, `xu_2025_coti`, `flaherty_oliver_2025_positive_spin`, `yue_2025_chatgpt_grounded_theory`, `ahtisham_2026_annotation_orchestration`, `flanders_2025_few_shot_thematic`, `sulaiman_2025_laca_hospitals`, `hila_hauser_2025_deductive_cap`, `zhao_liu_2025_complex_confidence_diversity`, `hairston_et_al_2025_xylazine_thematic`, `sankaranarayanan_et_al_2025_ta_mas`, `osian_et_al_2025_pfd_toolkit`, `rizvi_et_al_2025_nuanced_ableism`, `ghali_et_al_2025_beyondwords`, `de_paoli_2025_turing_qualitative`, `mackenzie_et_al_2025_canary`, `munjita_et_al_2025_bedbugs`, `koh_et_al_2025_patient_complaints`, `de_paoli_mathis_2025_codebook_reduction_saturation`, `simon_et_al_2025_human_mas_consistency`, `moskalewicz_et_al_2026_computational_phenomenology_bpd`, `balt_et_al_2025_psychosocial_autopsy`, `gao_et_al_2025_mindcoder`, `hara_et_al_2025_or_nurses`, `mehta_et_al_2025_genai_qualitative`, `shah_et_al_2025_inductive_deductive_re`, `qiao_et_al_2025_maternal_health`, `zhang_et_al_2025_ai_followup_interviews`, `parkington_et_al_2025_human_vs_llm_mental_health`, `nam_et_al_2025_idealign`, `castellanos_et_al_2025_thematic_summarization`, `ornelas_et_al_2025_llm_assisted_ta_workshop`, `oksanen_et_al_2025_llmcode`, `jain_et_al_2026_multi_llm_dual_reliability`, `wen_et_al_2025_neo_grounded_theory`, `cevik_abu_zidan_2025_efast_llm_thematic_analysis`, `liu_et_al_2025_qualitative_coding_gpt4`, `abramson_et_al_2025_qualitative_research_ai_pragmatic`, `zhang_et_al_2025_rosannotator`, `sakib_et_al_2025_shortcut_sdoh`, `de_paoli_fawzi_2025_tallmesh`, `borchers_et_al_2026_temperature_persona_consensus`, `rodriguez_et_al_2026_text_chunking_urban`, `king_et_al_2025_frontier_privacy_policies`, `relins_et_al_2025_police_vulnerability`, `shanwetter_levit_saban_2025_cancer_llm_qualitative`, `zhang_et_al_2025_harnessing_ai_qualitative_research`, `chen_et_al_2025_processes_matter_open_coding`, `wei_et_al_2026_childbirth_parenthood_discourse`, `cook_et_al_2025_ai_qda_promises_pitfalls`, `zambrano_et_al_2025_data_theory_codebook`, `parfenova_et_al_2025_emergent_convergence`, `zhang_et_al_2025_qualigpt_inductive_deductive`, `nguyen_trung_nguyen_2026_nita`, `wiebe_et_al_2025_hhitl_thematic_analysis`, `zhou_et_al_2025_llm_qualitative_nursing_scoping_review`, `than_et_al_2025_future_of_coding_llms`, `gustavsen_et_al_2025_generative_ai_qualitative_coding`, `li_2025_llms_fall_short`, `shen_2025_graduate_school_ai`, `kapania_2025_simulacrum_stories`, `crocker_2025_extension_feedback`, `pi_2025_logos`, `na_feng_2025_dialogue_coding`, `wen_2025_charity_thematic_analysis`, `schroeder_2025_uses_tensions_intentions`, `liu_2025_hybrid_codebooks_whimc`, `lin_2025_caila`, `rodriguez_triana_2025_code_aware`, `sun_liu_2025_autocoding_dialogue`.

**Current 2026 companion (69 evidence; 52 core + 17 non-core before final adjacent/contextual normalization):** `ta_0004_2026_hashmi`, `ta_0010_2026_zupic`, `ta_0018_2026_qin`, `ta_0025_2026_muda`, `ta_0038_2026_tiong`, `ta_0040_2026_ashton`, `ta_0054_2026_berkmortel`, `ta_0064_2026_laingen`, `ta_0077_2026_wahbeh`, `ta_0089_2026_yeoh`, `ta_0090_2026_stinger`, `ta_0117_2026_davis`, `ta_0120_2026_hutchinson`, `ta_0123_2026_ban`, `ta_0137_2026_xu`, `ta_0144_2026_bang`, `ta_0151_2026_tajik`, `ta_0153_2026_wang`, `ta_0175_2026_saranto`, `ta_0228_2026_nyaaba`, `ta_0231_2026_misgav`, `ta_0246_2026_bowden`, `ta_0255_2026_cortal`, `ta_0264_2026_xu`, `ta_0294_2026_kucuk`, `ta_0314_2026_sawai`, `ta_0330_2026_forster`, `ta_0334_2026_hill`, `ta_0338_2026_ma`, `ta_0345_2026_habib`, `ta_0351_2026_fischer`, `ta_0360_2026_khalid`, `ta_0370_2026_ngo`, `ta_0373_2026_maerz`, `ta_0382_2026_chen`, `ta_0385_2026_garces`, `ta_0386_2026_simons`, `ta_0388_2026_tabassum`, `ta_0389_2026_dunivin`, `ta_0392_2026_perez`, `ta_0416_2026_prahl`, `ta_0419_2026_wang`, `ta_0424_2026_villafuerteglvez`, `ta_0426_2026_peters`, `ta_0441_2026_thomas`, `ta_0445_2026_zhu`, `ta_0450_2026_hudson`, `ta_0453_2026_galatzerlevy`, `ta_0454_2026_leonard`, `ta_0460_2026_kivity`, `ta_0461_2026_umer`, `ta_0475_2026_subbiah`, `ta_0221_2026_bazilinskyy`, `ta_0308_2026_cheng`, `ta_0955_2026_meng`, `ta_1307_2026_object`, `ta_1327_2026_sudhoff`, `ta_0029_2026_wu`, `fc_03_2026_ye`, `fc_06_2026_han`, `fc_07_2026_ernst`, `fc_11_2026_beltran`, `fc_01_2026_logan`, `fc_02_2026_cibrian`, `fc_05_2026_misra`, `fc_12_2026_lee`, `fc_13_2026_lukito`, `fc_15_2026_li`, `fc_16_2026_mutanana`.

Recheck the 2026 list after freeze because it is the only provisional inventory. Apply the suppressions above before expecting 236 unique consolidated rows.

## 19. Appendices: search strings, screening, extraction, and quality rubric

**Current anchors:** lines 473–493.

- Preserve the exact search strings at 19.1, but link them to database-specific stored queries, dates, filters, and source counts. If a query changed during the second pass, version it rather than overwriting the original discovery protocol.
- Replace 19.2 completely. The old 60/2/58/1/57 flow, two nonretrievals, sole exclusion, and 70-row extraction are stale. Generate a complete screening table from final flow with separate database and chain pathways, full-text exclusion reasons, all nonretrievals, and family/duplicate dispositions. Include record IDs so every number is auditable.
- Add a publication-family appendix or ledger covering preferred versions, suppressed duplicates, dataset/human-reference dependencies, event versus publication years, preprint/VOR status, and material exceptions such as DeTAILS.
- Update 19.3 to state the frozen consolidated row count and affirm exactly 52 evidence fields. Include a data dictionary or direct workbook/table pointer; retain “not reported” semantics. Adjacent/contextual evidence rows remain extractable even though only core reports receive quality scores.
- Update 19.4 to the frozen core-only quality-row count and assert one 12-dimension score per unique core family. Remove/audit the nine adjacent quality rows in the 2025 companion. Preserve dimension rationales and the warning against simplistic total-score ranking.
- Update 19.5 and the companion workbook: regenerate summary counts/formulas, evidence-class table, year/venue/status tables, RQ1 task table, RQ2 claimed-versus-operationalized table, RQ3 architecture table, RQ4 human-role table, RQ5 metric/human-evaluation tables, RQ6 threat table, RQ7 ethics/resources table, RQ8 gap table, quality/ARR-priority table, exclusion/nonretrieval ledger, and citation/version/dependency relationships.
- Validate that no abstract-only/nonretrieved record appears as evidence in any comparative table and that all full-text exclusions have concise record-specific reasons.

## Final patch and validation order

1. Freeze and schema-validate the 2026 companion.
2. Consolidate the current master plus the three companions; normalize non-core classes; drop adjacent quality rows; apply every publication-family suppression; assert unique normalized DOI/title and one core-quality row per core family.
3. Rebuild `review_flow.json` and the workbook from the consolidated decisions. Assert all PRISMA identities and reconcile database versus chain pathways and foundations.
4. Recompute every count and RQ summary from structured reviewer fields. Record exact queries/scripts used for each number.
5. Regenerate Section 18 programmatically from the consolidated preferred-version metadata.
6. Patch the executive and Sections 1–19 in order, using this ledger's line anchors only as a locator for the pre-patch draft.
7. Run final checks: exactly one executive synthesis plus 19 numbered top-level sections; RQ1–RQ8 each answered in synthesis; no old 44/57/60/70/73/612 evidence counts; correct K–12 denominators; no placeholders; no abstract-only method/result claims; explicit preprint/poster/post-cutoff labels; every factual paper claim directly cited; DOI/title/link validation; no duplicate publication family; and internally identical counts across report, appendices, references, master, flow, and workbook.
