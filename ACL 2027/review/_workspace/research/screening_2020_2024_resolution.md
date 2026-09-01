# 2020–2024 and undated second-pass resolution

## Outcome

This pass resolves every in-scope record from `review_flow.json` that was uncertain or included/high-priority without a linked assessed full text, using the actual union abstract where available. It also resolves all six focused <=2024/undated forward-chain candidates that did not match the database union by normalized DOI/title.

The machine-readable artifact is `research/screening_2020_2024_resolution.json`. Its evidence array is `evidence_records` and its quality array is `quality_scores`. Evidence rows use exactly the 52 columns in `master_evidence.json`; all missing extracted values use `not reported`. Quality rows use exactly the requested 12 dimensions and are attached only to core evidence.

## Counts

- Database records resolved: 239 (207 previously uncertain; 32 previously included but not linked to an assessed full-text report).
- Union abstracts available: 201; no-abstract titles that plausibly met scope were routed to retrieval rather than extracted from title evidence.
- Initially advanced database records terminalized: 67.
  - Included after complete-text inspection: 21 (20 core and 1 adjacent).
  - Excluded after complete-text inspection: 10.
  - Full text not retrieved after documented attempts: 29.
  - Resolved through a publication/version family: 2.
  - Handed to the separately assigned year track after year resolution: 5 (3 to 2025; 2 to 2026).
- Other database dispositions: 164 title/abstract exclusions, plus already extracted or pre-existing family resolutions reflected in the full 239-record decision table.
- Forward-only records resolved: 6.
  - One core inclusion after full-text inspection: Ganesh et al. (2024), *Prompting as Panacea?*
  - One scope exclusion from the official structured abstract: the Chinese clinical-researcher phenomenology preprint, where LLM use is the phenomenon rather than the analytic method.
  - Three explicit nonretrievals after official-source attempts: *From Words to Themes* (potential core), *Future Directions in Qualitative Research* (adjacent), and the visual-analysis article (adjacent).
  - One formerly undated record resolved to 2026 and handed to that year track: *LLMs and Coding in Qualitative Research*.
- Master-ready companion: 24 records (23 core; 1 adjacent) and 23 quality assessments. These are not merged into the shared master in this concurrency-safe pass.

## Material synthesis changes

- **RQ1 — systems and workflows:** CollabCoder and Qualitative Code Suggestion add researcher-controlled collaborative/suggestion workflows; De Paoli adds a staged inductive thematic-analysis family; QualiGPT and Rasheed add end-to-end and multi-agent variants; Islam and Goldwasser add cluster-plus-LLM theme discovery; Ganesh, Dunivin, Liu, and Fischer/Biemann clarify the boundary between deductive coding and fixed-label classification.
- **RQ2 — human roles and agency:** Jiang, Gao, and Spinoso show that ambiguity, disagreement, coder histories, and serendipity are analytic resources rather than noise. Kondo, Mannstadt, Parker, and Islam use humans mainly for comparison or validation and expose risks when the same team, seed themes, or generated output anchors evaluation.
- **RQ3 — models, prompts, and adaptation:** Dunivin shows that per-code prompts and requested rationales change agreement; Chen shows that item-, chunk-, verb-, and participle-oriented prompts change granularity and grounding; Ganesh shows task-specific fine-tuning can outperform in-context learning and that few-shot prompting can hurt; Liu and Kirsten show strong task/context dependence.
- **RQ4 — domains and data:** The evidence base now covers restricted health and classroom data, large educational-survey corpora, political text in Finnish, Italian interviews, German privacy/security interviews, hate-speech data, controversial policy discourse, and social-media advertising. De Paoli and Kousa materially strengthen the previously thin non-English evidence.
- **RQ5 — evaluation:** The new papers distinguish agreement/F1 for deductive labels from validity of inductive themes. QCS provides unusually strong evidence that a single reference assignment understates valid alternatives; De Paoli/Mathis shows that saturation is promising but unvalidated and order-sensitive; Parker offers large-scale component metrics but limited theme-level construct validation.
- **RQ6 — validity and failures:** Recurrent failures include high precision with low recall, loss of minority/culturally specific meanings, prompt leakage, reference leakage, ungrounded or unsupported themes, latent-task degradation, run/order sensitivity, and agreement inflated by fixed-answer framing. Lancaster is a useful negative-control case for opaque corpus construction and unsupported synthesis.
- **RQ7 — reproducibility:** Some studies supply unusually useful artifacts (for example QCS resources, CollabCoder materials, and Dunivin's OSF package), but exact proprietary snapshots, complete prompts, seeds/runs, cost accounting, and data-governance details remain inconsistent. QualiGPT's overlapping preprints demonstrate why version-family control is necessary.
- **RQ8 — ethics, privacy, and responsibility:** Ganesh documents withholding restricted classroom data from a proprietary API; medical, mental-health, hate-speech, and political studies expose high-stakes privacy and representation risks. Spitale is adjacent rather than core, but materially shows that aggregate predictive performance can diverge from gender fairness and explanation quality.

## Dependence and version families

- De Paoli's 2024 journal paper is the methodological parent of the Italian-language and saturation papers. They add distinct datasets or metric questions but are not independent replications of wholly different workflows.
- QualiGPT arXiv:2407.14925 substantially overlaps arXiv:2310.07061 and must be counted once.
- Islam and Goldwasser's 2024 arXiv record and ICWSM-2025 acceptance form one publication family; the inspected paper reuses two earlier advertising corpora and their seed themes.
- Parker's arXiv and 2024 journal article form one family; Chen's arXiv and reported AERA-2025 acceptance form one family.
- Kondo, Mannstadt, and Breazu reanalyse earlier human-coded datasets; QCS uses interviews from an earlier cardiovascular-risk project; Spitale uses the DAIC-WOZ/E-DAIC benchmark family. These dependencies must remain visible when judging replication breadth.
- The qualitative-analysis CollabCoder paper is distinct from a later software-code-generation system with the same name.

## Implications for ARR gap priorities

The companion strengthens the following design priorities, in this order of direct relevance to the proposed ARR evaluation—not as a ranking of papers or a ranking by quality-score total:

1. Independent, blind, plurality-aware human evaluation instead of treating one codebook or model-generated reference as ground truth.
2. Source-level evidence links, minority-case preservation, and checks for unsupported themes or rationale unfaithfulness.
3. Crossed robustness tests over prompt form, model/version, context size, input order, seeds/runs, and deductive versus latent task complexity.
4. Native-speaker and domain/stakeholder evaluation on multilingual and high-stakes data, with subgroup and disagreement reporting.
5. Reproducible resource, privacy, governance, latency, and cost reporting, including exact model snapshots and restrictions on proprietary-API use.

QCS is especially informative for plurality and human-control design; Gao and Jiang are especially informative for collaborative workflow and agency; Parker is useful for large-corpus component testing; Dunivin, Chen, Ganesh, Liu, and Kirsten are particularly useful for robustness ablations. Quality totals remain compact audit aids only and must not be interpreted as study rankings.

## Reproducibility and limits

- Every included companion record links to a local complete-text extraction and has an evidence-location trail in the resolution table.
- Every database nonretrieval and forward-chain nonretrieval has at least one documented retrieval attempt.
- The JSON builder asserts the 67 terminal dispositions, exact 52-field evidence schema, exact 12-dimension rubric, valid 0/1/2 scores and totals, core/quality one-to-one matching, and no duplicate companion DOI/title.
- One reviewer performed this pass. The 29 database nonretrievals and three forward-chain nonretrievals are not evidence inclusions and remain candidates for later reassessment if complete text becomes available.
- The six-record forward-only pass found one inspected eligible study, but this small focused set does not establish citation saturation.
