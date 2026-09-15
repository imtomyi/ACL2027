# Dataset-specific metric conditions

Required companion to the [experiment guidelines](GUIDELINES.md). Version: `dataset-metric-conditions-v1`. This specifies the new server design, not completed measurements. The exhaustive [applicability CSV](metric_applicability.csv) records one entry per registered metric and dataset.

## Task and supervision profiles

| **Profile ID** | **Dataset / evaluation unit** | **Prediction target** | **Adaptation GT** | **Evaluation GT** | **Grounding task** |
| --- | --- | --- | --- | --- | --- |
| D-STRESS-v1 | Dreaddit / one selected passage | Exactly one of 2 labels; stress is positive | ✓ or ✗ by method | Released stress annotation, held by evaluator | Whether the stress/no-stress explanation and evidence are supported by the passage |
| G-EMOTION28-v1 | GoEmotions / one selected comment | Complete subset of the fixed 28 labels | ✓ or ✗ by method | Released multi-label annotation, held by evaluator | Whether each emotion claim and evidence are supported by the comment |
| C-CODING-v1 | CaChe / one selected source excerpt | Codes from the frozen CaChe codebook | ✗ only | None | Whether assigned thematic codes and explanations are supported by the excerpt |
| P-CODING-v1 | ParlaMint-GB / one selected source excerpt | Codes from the frozen ParlaMint-GB codebook | ✗ only | None | Whether assigned codes, attribution and explanations are supported by the excerpt |

Each profile has train/adaptation=100, development=100, evaluation=100, but the unit, annotation task and label space differ. CaChe and ParlaMint codebook sizes and exact code IDs must be populated from the selected codebook artifacts at execution seal time; they must not be invented from the other corpus. Store `codebook_sha256`, `label_count`, `evaluation_unit`, `source_group_unit` and annotation provenance in each dataset manifest.

The `GT` column in method tables must be titled **Adaptation GT**. An additional **Evaluation reference** field is mandatory in dataset metadata. GT✗ does not disable objective scoring when released evaluation labels exist. Conversely, an LLM judging a GT-free answer does not create evaluation GT.

## Metrics whose definitions or conditions differ

| **Metric / condition** | **Dreaddit** | **GoEmotions** | **CaChe** | **ParlaMint-GB** |
| --- | --- | --- | --- | --- |
| Acc | Binary label accuracy, exact one-label match /100 | Exact-set accuracy: all labels must match /100 | N/A: no task reference labels | N/A: no task reference labels |
| Micro-P/R/F1 | Pool both classes; with complete valid single-label predictions these equal Acc | Pool label decisions across all 28 emotions; not equivalent to exact-set Acc | N/A | N/A |
| Macro-P/R/F1 | Unweighted average over 2 fixed classes | Unweighted average over 28 fixed labels, including zero-support labels; also report supported-label variant separately | N/A | N/A |
| Weighted-P/R/F1 | Weight 2 classes by GT support | Weight 28 labels by GT support; an item can contribute to several labels | N/A | N/A |
| Stress F1 / specificity | Positive class stress=1; specificity uses no-stress negatives | N/A in this profile; do not choose an arbitrary positive emotion | N/A | N/A |
| Balanced Acc / MCC / kappa | Binary definitions; show degenerate cases | N/A in this profile; do not flatten 28 labels and label it binary MCC/balanced Acc | N/A | N/A |
| Confusion matrix | One 2×2 table | 28 separate one-vs-rest 2×2 tables | N/A | N/A |
| Sample P/R/F1, Jaccard | N/A as a separate multi-label metric in this profile | Per-item label-set overlap, then average over items | N/A without code reference sets | N/A without code reference sets |
| Hamming loss | N/A in this profile | Incorrect label bits / (100×28); report alongside F1 | N/A | N/A |
| ROC-AUC / AP | Continuous stress probability, both GT classes/support as required | Complete 28-label score vector; micro/macro/per-label variants explicitly named; undefined labels listed | N/A | N/A |
| Brier / log loss / ECE | Binary stress-probability formula and calibration bins | Label-marginal formulas; N×28 normalization; ECE is pooled label-bit ECE, not exact-set confidence calibration | N/A | N/A |
| LRAP / ranking loss / coverage error | N/A | Complete 28-label ranking scores required | N/A | N/A |
| Conformability v2 | Stress explanation grounding | Emotion explanation grounding | CaChe codebook-conditioned grounding | ParlaMint codebook-conditioned grounding |
| Quote validity | Exact spans within selected passage | Exact spans within selected comment | Exact spans within selected excerpt | Exact spans within selected excerpt |
| Label-to-evidence coverage | Evidence coverage of the one predicted stress label | Evidence coverage across the predicted emotion set | Evidence coverage across predicted CaChe codes | Evidence coverage across predicted ParlaMint codes |
| Evidence entailment | Is the quote sufficient for the stress/no-stress claim? | Is the quote sufficient for each emotion claim? | Does the quote support each code under the CaChe definition? | Does the quote support each code under the ParlaMint definition? |
| Correct AND grounded | Exact stress-label match AND grounding pass on the same item | Exact full emotion-set match AND grounding pass on the same item | N/A: grounding alone is insufficient | N/A: grounding alone is insufficient |
| Schema validity | Exactly one allowed label, required evidence and explanation | Nonempty unique set of allowed labels; neutral cannot coexist with an emotion | Frozen codebook, cardinality, evidence and schema rules | Frozen codebook, cardinality, evidence and schema rules |
| Human grounding audit | Same 20 preselected passage IDs across methods, seed 42 | Same 20 comment IDs across methods, seed 42 | Same 20 excerpt IDs across methods, seed 42 | Same 20 excerpt IDs across methods, seed 42 |
| TGC/SGC, Normal/Challenge | N/A | N/A | N/A | N/A |

Probability metrics are `NC` until a valid scoring procedure is frozen and scores are collected. Different label-level and exact-answer confidences are not interchangeable. Human audit and gold-evidence metrics remain `PENDING`/`NC` until actually annotated; no values are inferred from the definition.

## Common formulas still require condition disclosure

Conformability uses the same four-dimensional rating scale and pass threshold across corpora, but the task text, label/code definitions, source length, attribution difficulty and prediction cardinality differ. Display `Conformability v2 · <profile ID>` and the rubric/task/codebook hashes. A 99% score on thematic coding does not establish better task performance than 95% on emotion classification. Do not pool these as one task accuracy or claim a cross-corpus winner.

Quote validity is an exact-text mechanical check, not semantic correctness. Always display quote count and item evidence coverage: a corpus/method producing fewer claims must not appear superior solely because it submits fewer quotes. Claim support and contradiction rates similarly require claim counts and extraction versions. A valid empty/abstaining response never gets a vacuous perfect evidence score.

Per-item latency and token cost depend on source length, label inventory, explanation length, learned memory and method call structure even with N=100 everywhere. Report input/output token distributions, per-role call counts, context cap, device, engine, quantization, concurrency and retry cost. Same N or same wall time does not establish equal compute. Compare timing under matched runtime profiles and describe corpus-dependent workload explicitly.

## Method, phase and denominator conditions

| **Condition** | **Required metric annotation** |
| --- | --- |
| Baseline / ICL / static optimized prompt | Online update count and online step latency are N/A. Static context size may be reported, but changing-playbook metrics are N/A. |
| Offline ACE | Training/adaptation progress /100 is separate from held-out prediction /100. Test outputs all use the frozen final memory. |
| Online DC/ACE | Score pre-update predictions only; memory update is /100 and affects future items. Keep corpus/seed order hash. No IID item-based significance claim for the adaptive process. |
| ACE bullet metrics | Require stable bullet IDs and delta operations. These are N/A for DC when it exposes only a complete cheatsheet. |
| GT✓ versus GT✗ | Compare and label feedback regimes separately; keep the same evaluator-held test references where available. |
| Missing or invalid predictions | Show planned N, attempted N, valid N and missing/error counts. Do not shrink denominators silently. |
| Unresolved judge decisions | Show resolved N and unknown N; pass/resolved is provisional until resolved=100. Full-panel bounds accompany partial scores. |
| Seeds / source grouping | Report 3 seed runs over the same 100 items, not 300 independent items. Store grouping basis and use it in eligible offline uncertainty calculations. |

## Mandatory result-table labels and export fields

1. Display **Dataset**, **Metric profile**, **Adaptation GT**, **Evaluation reference**, and **N per seed** in the visible table or immediately preceding dataset metadata. These may not be hidden only in JSON.
2. Use **Acc (binary)** for D-STRESS-v1 and **Acc (exact set)** for G-EMOTION28-v1. A cross-dataset wide table must use explicit header footnotes linking these definitions. Label Macro-F1 as **2-class** or **28-label**; distinguish supported-label Macro-F1 explicitly.
3. Each exported metric includes `metric_condition_id`, `metric_definition_variant`, `evaluation_reference`, `label_count`, `positive_label`, `averaging`, `denominator_basis`, `task_sha256`, `codebook_sha256`, `rubric_sha256`, `phase`, `adaptation_gt`, `probability_source`, `source_group_unit`, `evaluation_order_sha256` and `runtime_profile_id`. Inapplicable fields are null/N/A; unresolved required fields block metric finalization.
4. The condition ID combines profile, metric ID and `dataset-metric-conditions-v1`. Runtime metric records additionally key model, method, phase, GT, seed and slice. Never merge metric rows based on display name alone.
5. Differences from Base must identify the metric and use the same dataset/profile, model, item set, order, seed and judge. Cross-dataset averages, if ever added, must explicitly name their constituent metrics and weighting and remain secondary; this version does not schedule such averages.
6. The applicability CSV describes dataset eligibility. Phase/method restrictions and missing prerequisites must also pass. `applicable` means defined under this design, not implemented, collected or final.

## Versioning

This addition clarifies dataset-specific definitions already intended by four-corpus-server-v5. The server execution manifest is still unsealed; no existing run, frozen model, metric value or paused state was changed. Any later change to label inventory, codebook, positive class, metric averaging, pass threshold, denominator or evaluation reference requires a new condition version and separately identifiable results.
