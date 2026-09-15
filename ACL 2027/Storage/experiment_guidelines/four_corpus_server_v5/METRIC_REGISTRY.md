# Metric registry

Protocol: four-corpus-server-v5. **85 registered metric entries/families.** Vector families produce additional per-label or per-stage values. This is a specification, not a claim that new metrics are implemented or measured.

See [dataset-specific conditions](DATASET_METRIC_CONDITIONS.md) and [all 340 applicability entries](metric_applicability.csv). These conditions qualify every definition below and must travel with exported scores.

## Conventions

Percentages are stored as 0–100; raw fractions may also be exported with an explicit unit. Never compare numeric values with different units. Directions describe interpretation, not an automatic optimization objective. All predictive label metrics require released or independently validated GT. CaChe/ParlaMint label metrics are N/A, even though adaptation is possible. Inapplicable AppWorld metrics are N/A for every row.

Hard-label macro/micro F1 uses a fixed label inventory and zero_division=0. Conditional supported-label variants are explicitly named. Missing or malformed predictions must not be silently converted to an empty set or excluded; publish full-panel failure-aware accuracy and coverage, and keep full-panel F1 unfinalized until its preconditions hold.

Probability metrics require calibrated comparable per-label scores obtained under a frozen procedure. Sequence token log-probabilities are not automatically class probabilities, especially for generated multi-label arrays. Hard labels and verbal confidence cannot support ROC-AUC, AP, Brier or ECE. Any probability-scoring calls are separate, frozen, charged evaluation work and never affect the original prediction.

For N=100 with P grounding passes and U unresolved decisions, show the full-panel bounds [P, P+U] percent and resolved coverage. No-answer/invalid-schema quality failures may be resolved as fail; failed judge calls remain unknown. Empty evidence/claim sets never receive a vacuous perfect score.

Class probabilities, independent gold evidence, human review, second judges and GPU/billing telemetry are conditional prerequisites. Until available use NC/PENDING with the reason. Finalization is per metric; optional human audits do not make already resolved automatic metrics disappear.

Definitions follow the [scikit-learn metric reference](https://scikit-learn.org/stable/api/sklearn.metrics.html) and [evaluation guide](https://scikit-learn.org/stable/modules/model_evaluation.html) where standard. Grounding/memory/reliability definitions are explicitly local study metrics.

## Classification

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| accuracy / Accuracy / exact-set accuracy | Dreaddit; GoEmotions | up / % | 100 * correct exact label predictions / 100 planned items. Invalid/abstaining outputs are incorrect; unattempted items keep the row partial. | Saved predictions and released GT |
| valid_accuracy / Valid-output accuracy | Dreaddit; GoEmotions | up / % | 100 * exact correct / valid parsed predictions; diagnostic only; always show valid N. | Saved predictions and released GT |
| micro_precision / Micro precision | Dreaddit; GoEmotions | up / % | Compute precision using micro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| micro_recall / Micro recall | Dreaddit; GoEmotions | up / % | Compute recall using micro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| micro_f1 / Micro f1 | Dreaddit; GoEmotions | up / % | Compute f1 using micro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| macro_precision / Macro precision | Dreaddit; GoEmotions | up / % | Compute precision using macro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| macro_recall / Macro recall | Dreaddit; GoEmotions | up / % | Compute recall using macro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| macro_f1 / Macro f1 | Dreaddit; GoEmotions | up / % | Compute f1 using macro averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| weighted_precision / Weighted precision | Dreaddit; GoEmotions | up / % | Compute precision using weighted averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| weighted_recall / Weighted recall | Dreaddit; GoEmotions | up / % | Compute recall using weighted averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| weighted_f1 / Weighted f1 | Dreaddit; GoEmotions | up / % | Compute f1 using weighted averaging over the fixed label inventory (2 or 28). zero_division=0; report per-label support. Weighted uses GT support. Requires all planned outputs valid; otherwise NC with failure-aware Acc reported. | Saved predictions and released GT |
| stress_f1 / Stress-positive F1 | Dreaddit | up / % | F1 for stress=1; zero_division=0. Never silently use no-stress as the positive class. | Saved predictions and released GT |
| balanced_accuracy / Balanced accuracy | Dreaddit | up / % | Mean recall across both GT classes; undefined if either class is absent. | Saved predictions and released GT |
| specificity / Specificity | Dreaddit | up / % | 100 * TN/(TN+FP), positive class stress=1; undefined with no negatives. | Saved predictions and released GT |
| mcc / Matthews correlation coefficient | Dreaddit | up / [-1,1] | Binary MCC; report degeneracy and support; use pinned sklearn convention for constant predictions. | Saved predictions and released GT |
| kappa / Cohen kappa against GT | Dreaddit | up / [-1,1] | Observed versus chance-corrected binary label agreement; undefined degenerate marginal cases marked NC. | Saved predictions and released GT |
| confusion / Confusion matrix | Dreaddit; GoEmotions | none / counts | Dreaddit 2x2 and GoEmotions per-label 2x2 matrices with fixed label order. | Saved predictions and released GT |
| per_label_prf / Per-label precision / recall / F1 / support | Dreaddit; GoEmotions | none / vector | Vector over the full label inventory, including zero-support labels and zero_division=0. | Saved predictions and released GT |
| supported_macro_f1 / Macro-F1 on supported labels | GoEmotions | up / % | Average F1 only over labels with GT support >0; diagnostic alongside fixed-28 Macro-F1; save label list. | Saved predictions and released GT |

## Multilabel

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| sample_precision / Sample-averaged precision | GoEmotions | up / % | Mean per-item set precision; zero_division=0. Normalize neutral as a real single label, not an empty set. | Saved predictions and released GT |
| sample_recall / Sample-averaged recall | GoEmotions | up / % | Mean per-item set recall; zero_division=0. Normalize neutral as a real single label, not an empty set. | Saved predictions and released GT |
| sample_f1 / Sample-averaged f1 | GoEmotions | up / % | Mean per-item set f1; zero_division=0. Normalize neutral as a real single label, not an empty set. | Saved predictions and released GT |
| hamming_loss / Hamming loss | GoEmotions | down / % | 100 * total false-positive and false-negative label bits / (100 * 28). Requires all valid predictions; also show F1 because absent labels dominate. | Saved predictions and released GT |
| sample_jaccard / Sample Jaccard | GoEmotions | up / % | Mean 100 * /predicted intersection GT/ / /predicted union GT/; empty union convention 1, though valid GT is nonempty. | Saved predictions and released GT |
| cardinality / Predicted / true label cardinality | GoEmotions | none / labels/item | Mean labels per item for predictions and GT, plus signed and absolute differences. | Saved predictions and released GT |
| empty_neutral_conflict / Empty / neutral-conflict output rates | GoEmotions | down / % | Separate rates for empty label sets and neutral combined with another emotion. Flag as invalid under the frozen schema. | Saved predictions and frozen label schema |

## Probabilistic

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| roc_auc / ROC-AUC | Labeled corpora where prerequisites hold | up / native | Dreaddit positive-class AUC; GoEmotions per-label, micro, and macro AUC. Skip undefined single-class labels, list them and the averaging denominator. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| average_precision / Average precision | Labeled corpora where prerequisites hold | up / native | Dreaddit positive-class AP; GoEmotions micro/macro/per-label AP. Report undefined/no-positive labels and valid averaging denominator; do not call trapezoidal PR-AUC AP. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| brier / Brier score | Labeled corpora where prerequisites hold | down / native | Dreaddit mean (p_stress-y)^2; GoEmotions mean over all N*28 squared marginal probability errors. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| log_loss / Log loss | Labeled corpora where prerequisites hold | down / native | Dreaddit binary NLL; GoEmotions mean binary cross-entropy over N*28. Clip probabilities at 1e-7; record clipping. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| ece / Expected calibration error | Labeled corpora where prerequisites hold | down / native | Ten equal-width bins over [0,1]. Binary positive-probability ECE or pooled multi-label-bit ECE; save bin N, mean predicted probability and positive frequency. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| lrap / Label-ranking average precision | Labeled corpora where prerequisites hold | up / native | GoEmotions only: use complete marginal score vector and GT label matrix. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| ranking_loss / Label-ranking loss | Labeled corpora where prerequisites hold | down / native | GoEmotions only: fraction of incorrectly ordered relevant/irrelevant label pairs under pinned sklearn convention. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| coverage_error / Coverage error | Labeled corpora where prerequisites hold | down / native | GoEmotions only: average depth required to cover all true labels in score ranking; not prediction coverage. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| risk_coverage / Risk-coverage curve / AURC | Labeled corpora where prerequisites hold | down / native | Order items by predeclared confidence in exact answer correctness; plot full-panel exact-error rate among retained items. Confidence construction must be calibrated on development data. | Comparable probabilities/scores from a separately frozen scoring procedure; never infer these from hard labels or verbal confidence |
| reliability_bins / Reliability diagram data | Labeled corpora | none / table | Per-bin counts, mean probabilities, observed frequencies; export machine-readable bin records. | Same valid probabilities as ECE |

## Grounding

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| conformability / Conformability v2 pass rate | All four | up / % | Pass iff all four source-grounding dimensions score 2 and output is valid. Report passes/resolved and resolved/100; final only with 100 resolved. | Frozen primary judge, source, task/codebook, final answer/evidence |
| factual_support / Factual support | All four | up / [0,2] | Mean dimension rating 0=fail, 1=partial/ambiguous, 2=pass over resolved ratings; show dimension-specific N and missing. | Frozen dimension rubric and judge |
| evidence_relevance / Evidence relevance | All four | up / [0,2] | Mean dimension rating 0=fail, 1=partial/ambiguous, 2=pass over resolved ratings; show dimension-specific N and missing. | Frozen dimension rubric and judge |
| attribution / Speaker / temporal attribution | All four | up / [0,2] | Mean dimension rating 0=fail, 1=partial/ambiguous, 2=pass over resolved ratings; show dimension-specific N and missing. | Frozen dimension rubric and judge |
| unsupported_assertions / Absence of material unsupported assertions | All four | up / [0,2] | Mean dimension rating 0=fail, 1=partial/ambiguous, 2=pass over resolved ratings; show dimension-specific N and missing. | Frozen dimension rubric and judge |
| claim_support / Claim support rate | All four | up / % | Supported atomic claims / all adjudicated atomic claims; show number of claims and extraction version. Empty answers do not earn a perfect score. | Additional frozen claim decomposition and claim-level annotations |
| contradiction / Contradiction rate | All four | down / % | Contradicted atomic claims / adjudicated claims; unclear claims separately reported. | Claim-level source judgments |

## Evidence

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| quote_validity / Exact-quote validity | All four | up / % | Quotes whose stored [start,end) offsets reproduce the quote exactly / all submitted quotes. Missing all required quotes is an item failure. | Final evidence quotes, Unicode codepoint offsets and original source |
| label_evidence_coverage / Label-to-evidence coverage | All four | up / % | Predicted labels/codes with at least one mechanically valid quote / predicted labels/codes; empty invalid output has coverage 0, never 100. | Label-linked quote records and deterministic quote validator |
| evidence_entailment / Evidence entailment rate | All four | up / % | Label/code claims actually supported by cited spans / judged label/code claims. Report all predicted-label denominator and missing separately. | Frozen entailment rubric and judge |
| evidence_token_f1 / Evidence token F1 / span overlap | Only with independently annotated evidence | up / % | Token overlap against independently annotated gold spans using a frozen tokenizer and multi-span matching rule. | Human reference evidence; not available for the current panel by default |

## Joint

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| correct_and_grounded / Joint correct-and-grounded rate | Dreaddit; GoEmotions | up / % | Match by record ID: exact label correctness AND Conformability pass. Use actual joint events, never multiply marginal rates. Show missing-grounding bounds. | Released GT and resolved per-item grounding |
| grounding_on_errors / Grounding pass rate among wrong answers | Dreaddit; GoEmotions | none / % | Grounding passes among exact-label errors / resolved exact-label errors. Exposes plausible but incorrect explanations. | Released GT and per-item judge decisions |

## Audit

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| human_grounding / Human-audited grounding pass rate | Preselected audit subset | up / % | Adjudicated passes / reviewed outputs using the same v2 rubric; show exact audited N and never extrapolate as full-panel score. | Two independent human reviews plus adjudication |
| human_agreement / Human-human raw agreement / kappa | Preselected audit subset | none / native | Pass/fail agreement and Cohen kappa before adjudication; dimension ordinal agreement separately. | Independent reviewer labels |
| judge_agreement / Judge-human agreement / sensitivity / specificity | Preselected audit subset | none / native | Compare judge with adjudicated human grounding; treat human grounding failures as positive for failure-detection sensitivity. Show confusion matrix. | Judge and human labels; both human outcome classes for sensitivity/specificity |
| second_judge_agreement / Primary-secondary judge agreement | Optional matched subset | none / native | Raw agreement and kappa, same answer/source and frozen rubric; agreement is not proof of truth. | Separately frozen secondary judge; not automatically scheduled |

## Reliability

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| prediction_coverage / Prediction coverage | All four | up / % | Valid committed predictions / 100 planned inputs. | Attempt logs and parser/error records |
| schema_validity / Schema-valid output rate | All four | up / % | Report first-attempt validity and eventual validity separately over attempted items. | Attempt logs and parser/error records |
| invalid_label_rate / Invalid-label rate | All four | down / % | Items with out-of-codebook, duplicate or forbidden label combinations / attempted items. | Attempt logs and parser/error records |
| abstention_rate / Abstention / refusal rate | All four | down / % | Separate explicit uncertainty abstentions and refusals / attempted items; preserve task failures. | Attempt logs and parser/error records |
| unresolved_judge_rate / Unresolved judgment rate | All four | down / % | Unresolved or unattempted planned primary judgments / 100; split error and not-yet-run counts. | Attempt logs and parser/error records |
| truncation_rate / Output-truncation rate | All four | down / % | Length-terminated model calls / all completed calls; also items affected / attempted items. | Attempt logs and parser/error records |
| retry_rate / Retry rate | All four | down / % | Items needing one or more retries / attempted items; report extra-call count separately. | Attempt logs and parser/error records |
| format_failure_rate / Exhausted format-failure rate | All four | down / % | Items still unparsable after the fixed retry policy / attempted items. | Attempt logs and parser/error records |

## Efficiency

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| active_time / Total active wall time | All four | none / seconds | Wall time spent on preparation, adaptation/search, prediction, judging and retries; sum nonoverlapping phase intervals. Separate cold-start setup. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| elapsed_pause / Elapsed and paused time | All four | none / seconds | End-start elapsed time plus separately measured user-pause, infrastructure-idle and active intervals. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| stage_latency / Stage latency mean / p50 / p95 | All four | none / seconds | Separate generator, reflector, curator, optimizer and judge latencies; completed versus failed attempts separately. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| online_step_latency / Online step latency | All four | none / seconds/item | Time from beginning prediction to committed memory update; include its retries; report mean/p50/p95. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| throughput / Throughput | All four | none / items/s | Completed valid evaluation items / active prediction wall time; separate token throughput and batch profile. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| tokens / Input / output / thinking / cached tokens | All four | none / tokens | Totals and per-item mean/p50/p95 by role, with native tokenizer and missing-usage counters. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| calls / Model and metric-call counts | All four | none / counts | Separate inference calls, optimizer metric evaluations, retries, and cache hits; do not equate them. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| discarded_time / Discarded inference time | All four | none / seconds | Sum measured duration of canceled, truncated or otherwise unusable calls; distinguish successful fallback calls and unknown cancellation duration. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| peak_vram / Peak VRAM | All four | none / GiB | Sample GPU memory at 1 second and store sampling interval; include model and KV cache, not only weight file size. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| energy / GPU energy | All four | none / Wh | Integrate measured GPU power over active intervals; report sampling/missing data, excludes unmeasured host energy. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |
| monetary_cost / Measured compute cost | All four | none / currency | Actual billed/API cost or rate-card estimate with explicit tariff, date and active allocation; no invented local dollar costs. | Stage logs / backend token usage / GPU telemetry or billing as appropriate |

## Adaptation Analysis

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| memory_size / Memory size and growth | Applicable methods and corpora | none / native | Before/after each update: tokens, bytes and stable bullet count where supported; p50/max/final plus growth. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| memory_operations / Memory additions / edits / removals | Applicable methods and corpora | none / counts | Count committed ACE delta operations by type; for DC report whole-cheatsheet revisions without inventing ACE bullet semantics. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| memory_rejections / Rejected / failed memory updates | Applicable methods and corpora | none / % | Rejected over-budget or invalid updates / attempted updates; retained-old-memory events tracked separately. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| bullet_use / Referenced playbook bullet rate | Applicable methods and corpora | none / % | Valid bullet IDs cited by predictions / total cited IDs; also distinct cited bullets / existing bullets. Self-reported references are not causal utilization. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| update_completion / Update completion | Applicable methods and corpora | none / % | Committed required online updates / 100, or offline adaptation updates / 100. No-op valid updates count but are identified. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| learning_curve / Cumulative and 20-item block curves | Applicable methods and corpora | none / metric curves | Compute applicable task and grounding metrics at prefixes 20,40,60,80,100 and disjoint blocks; include block N and GT support. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| matched_base_delta / Matched Base improvement | Applicable methods and corpora | none / native | Same-backbone/seed/item matched difference for applicable metric; percentages expressed in percentage points. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| seed_variation / Repetition variation | Applicable methods and corpora | none / native | Per-seed scores and mean/sample SD across seeds 42,43,44; never select the best seed or claim N=300 unique examples. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |
| paired_ci / Paired 95% confidence interval | Applicable methods and corpora | none / interval | 10,000 offline paired group/item bootstrap replicates, seed 20260914; online dependency caveats follow guideline. | Saved per-item predictions, ordered memory/update logs and applicable GT/judgments |

## Benchmark Only

| **ID / metric** | **Scope** | **Direction / unit** | **Definition** | **Required evidence** |
| --- | --- | --- | --- | --- |
| normal_tgc / AppWorld Test-Normal TGC | Actual AppWorld evaluation only | up / % | Official executable task/scenario success metric, not a classification or grounding proxy. N/A for all four corpora. | Official AppWorld task tests, scenarios and split definitions |
| normal_sgc / AppWorld Test-Normal SGC | Actual AppWorld evaluation only | up / % | Official executable task/scenario success metric, not a classification or grounding proxy. N/A for all four corpora. | Official AppWorld task tests, scenarios and split definitions |
| challenge_tgc / AppWorld Test-Challenge TGC | Actual AppWorld evaluation only | up / % | Official executable task/scenario success metric, not a classification or grounding proxy. N/A for all four corpora. | Official AppWorld task tests, scenarios and split definitions |
| challenge_sgc / AppWorld Test-Challenge SGC | Actual AppWorld evaluation only | up / % | Official executable task/scenario success metric, not a classification or grounding proxy. N/A for all four corpora. | Official AppWorld task tests, scenarios and split definitions |
