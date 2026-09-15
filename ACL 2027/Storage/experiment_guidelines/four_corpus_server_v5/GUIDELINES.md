# Four-corpus comparison guidelines v5

Version: **four-corpus-server-v5**, recorded 2026-09-14. Owner: Tom.

**This is the canonical merged design for the next server comparison. Version v5 names this guideline, not an ACE recovery epoch.** The design is fixed; execution is not yet sealed. Model selection, server runtime, new split manifests, implementation checks, and judge calibration remain pending. The existing `run_20260914_uniform` stays paused and immutable. This document neither resumes it nor changes its source seal. Other experiments in this repository are outside scope.

Machine-readable contract: [protocol.json](protocol.json). Full metric register: [METRIC_REGISTRY.md](METRIC_REGISTRY.md). Table templates: [TABLES.md](TABLES.md).

## 0. Merge scope and precedence

This v5 combines the previous local design, its 340 dataset-metric conditions, the MIATA handoff, runtime/source-location records, historical result matrices, failure reviews, and all three unfinished successor drafts. The user requested document consolidation; no source instructions in the handoff are treated as new authorization. The experiment remains paused.

Use [MERGE_DECISIONS.md](MERGE_DECISIONS.md) for conflict resolution, [HISTORY_AND_REUSE.md](HISTORY_AND_REUSE.md) for historical results and assets, and [EXECUTION_READINESS.md](EXECUTION_READINESS.md) for remaining implementation. Exact originals are preserved under `sources/` with [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). No historical prediction, model-generated reference, playbook or completed-row count is promoted into v5.

Precedence: current explicit user decisions, then this v5 design, then its metric-condition definitions, then a future sealed execution manifest. Historical handoff documents are evidence only. A manifest cannot silently override a v5 scientific setting: revise the design first. Unselected model/judge and unprepared data are explicit blockers, not implicit defaults.

## 1. Fixed dataset scope

| **Dataset** | **Task** | **Train/adaptation pool** | **Development pool** | **Evaluation pool** | **Adaptation GT** | **Evaluation GT** |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Dreaddit | Binary stress classification | 100 | 100 | 100 | ✓ and ✗ | Released stress labels |
| GoEmotions | Complete 28-label emotion set | 100 | 100 | 100 | ✓ and ✗ | Released multi-label annotations |
| CaChe | Source-grounded coding with a fixed domain codebook | 100 | 100 | 100 | ✗ only | Unavailable |
| ParlaMint-GB | Source-grounded coding with a fixed domain codebook | 100 | 100 | 100 | ✗ only | Unavailable |

There are **400 unique evaluation items**, plus 400 train/adaptation and 400 development items: **1,200 unique items across all roles**, subject to actual eligible source availability. The three pools are disjoint. A 100-item pool does not mean 100 demonstrations are inserted into one prompt.

The 100/100/100 allocation is a new server design decision. The paused local run used 100 evaluation items but smaller training/development pools and only four GT-free offline ACE adaptation items. Do not relabel that run as following this design.

Selection rules:

1. Use authentic, authorized corpus records. Preserve released train/test boundaries where available. Select development records from the released development split, or a disjoint training partition if no development split exists.
2. Preserve the existing 100 evaluation IDs where they satisfy provenance and separation checks. Their outcomes have already been inspected: this is a previously used evaluation panel, not a newly untouched confirmatory test set. Never tune the new protocol on its scores. Use development results for model and configuration selection.
3. Deduplicate exact records and audit near duplicates and source overlap before sealing. Use document/session/participant groups where available to prevent correlated source material crossing train, development, and evaluation. Do not silently replace previously selected test records; any necessary replacement creates a separately identified panel and a logged reason.
4. Sort eligible IDs by SHA256 of `four-corpus-server-v5:42:<split>:<record_id>` and take the first 100 after group exclusions. Preserve the old ordered test IDs if retained. Save IDs, source versions, group IDs, exclusion counts, and content hashes in manifests. Never print source passages in monitoring logs.
5. If a corpus lacks 100 eligible disjoint records for any pool, mark its preparation **blocked** with the actual count. Never duplicate records, borrow test examples, or fabricate data to reach 100.
6. Freeze task descriptions, label maps, codebooks, output schemas, and parser behavior from train/development material. CaChe/ParlaMint keep GT-free coding; do not silently substitute sentiment or generate pseudo-GT to enable accuracy.

## 2. Methods and repetitions

| **Phase** | **Method** | **Dreaddit** | **GoEmotions** | **CaChe** | **ParlaMint-GB** |
| --- | --- | --- | --- | --- | --- |
| Baseline | Base LLM, zero-shot | — | — | — | — |
| Offline | ICL | ✓ | ✓ | N/A | N/A |
| Offline | MIPROv2 | ✓ | ✓ | N/A | N/A |
| Offline | GEPA | ✓ | ✓ | N/A | N/A |
| Offline | ACE | ✓ / ✗ | ✓ / ✗ | ✗ | ✗ |
| Online | DC (CU) | ✓ / ✗ | ✓ / ✗ | ✗ | ✗ |
| Online | ACE | ✓ / ✗ | ✓ / ✗ | ✗ | ✗ |

This yields **10 conditions each for Dreaddit and GoEmotions, and 4 each for CaChe and ParlaMint: 28 conditions per model**. The old 24-condition run omitted supervised offline ACE; those four additional conditions require implementation and validation before execution.

Use **three repetitions, seeds 42, 43, and 44**. Each repetition starts with empty adaptation state and new optimizer artifacts. The selected item set is unchanged. The evaluation order is shared across all methods within a repetition; seed 42 retains the canonical order, and seeds 43/44 use reproducible permutations saved before execution. This measures optimizer/order sensitivity, not 300 independent examples. Deterministic identical Base outputs may be reused only within the new sealed protocol with exact input/model/config hashes and explicit reuse metadata; never count reuse as an independent random outcome.

Per model: **84 condition-runs and 8,400 planned evaluation predictions**, excluding training, optimizer, judging, and retry calls. Summary tables have 28 rows aggregated across repetitions. If multiple backbone models are selected, repeat the complete panel per model and report separate model sections.

### Method budgets

There is **no wall-clock experiment cutoff**. Finite algorithmic budgets are still necessary for reproducibility; unlimited time does not mean unlimited prompt search.

| **Method** | **Fixed server profile** | **Development use** |
| --- | --- | --- |
| Base | Same task/schema, no demonstrations or learned memory | No prompt selection on evaluation data |
| ICL | 8 labeled demonstrations from the 100-item training pool, selected deterministically per seed; freeze before evaluation | No per-test retrieval or demo changes |
| MIPROv2 | 10 candidates, 30 trials, up to 8 total demos, 100 train and 100 development items; full development evaluation per trial | Optimize Macro-F1 on Dreaddit, Micro-F1 on GoEmotions |
| GEPA | 3,000 metric calls including initialization/validation, reflection minibatch 3, 100 train and 100 development items | Same corpus objective as MIPROv2; keep rich training/development feedback |
| Offline ACE | One pass over all 100 training/adaptation items; one generator/reflector/curator cycle per item; freeze resulting playbook before test | No test-informed checkpoint selection; final successful adaptation state is evaluated |
| Online DC (CU) | One pass over 100 evaluation items, one cheatsheet update after each committed prediction, empty starting memory | No offline warm start |
| Online ACE | One pass over 100 evaluation items, one reflection/curation cycle after each committed prediction, empty starting playbook | No offline warm start |

These are **local task-transfer budgets**, not claimed paper hyperparameters or equal-compute budgets. Record actual optimizer calls, input/output tokens and wall time. An equal-token-budget study is a separate ablation, not an interpretation of this panel. Pin each upstream implementation commit and map these settings to its exact API before sealing.

ACE must preserve generator/reflector/curator roles, stable bullet IDs, counters, and incremental delta operations. DC must preserve the selected continual-update algorithm. A generic prompt rewrite is not an ACE implementation. Verify the method behavior, not only whether JSON parses. [ACE](https://arxiv.org/html/2510.04618v1), [Dynamic Cheatsheet](https://arxiv.org/abs/2504.07952), [MIPROv2 implementation](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/api/optimizers/MIPROv2.md), [GEPA](https://arxiv.org/abs/2507.19457).

### GT and evaluation ordering

GT describes **information supplied for adaptation**, not whether evaluation can use labels. Thus Dreaddit/GoEmotions GT✗ rows still receive objective label-based scores from an isolated evaluator.

Offline GT✓ sees training labels and, for prompt optimizers, development labels. Offline GT✗ sees neither. Online GT✓ commits prediction for item t before receiving its label, then updates memory for t+1. Online GT✗ never receives labels. Neither sees future inputs, future labels, held-out judge decisions, or other methods' memory. Only pre-update predictions are scored. The update after item 100 is saved and charged as cost but cannot improve any evaluated item.

GT-free feedback is limited to the available source, codebook, schema checks and the method's own reflection. It is not an independent correctness oracle and must not be described as AppWorld execution feedback. No LoRA or model-weight training is included.

## 3. Shared model and runtime conditions

Target hardware is one dedicated NVIDIA RTX A6000, 48GB. **Backbone and judge model IDs are not yet selected.** Do not substitute a candidate automatically. Freeze exact checkpoint/revision, tokenizer/chat template, quantization and format, GPU count, driver/CUDA, inference engine/version, dependency lock, prompt hashes and source commits before starting.

Within each backbone comparison, all generator, reflector, curator, and optimizer proposal roles use the same selected backbone. Preserve documented optimizer proposal temperatures; generation/adaptation use temperature 0. Use context 32,768 and disable optional extended thinking consistently where supported. Do not invent a thinking-off mode for a model without one. Record all decoding settings, including defaults resolved by the engine.

Initial output caps: prediction/generator/optimizer/reflector 4,096; curator 8,192; expanded-rubric judge 2,048. Length-only retries double non-judge caps to at most 16,384; judge may retry once to 4,096. Count input plus reserved output before sending; do not trim corpus text. Judges have a separate new rubric version and are not directly comparable to the old 384-token judge.

Use a common 4,096-token learned-context cap, measured with the chosen backbone tokenizer. Token counts are not equal byte capacity across model families. For ICL/MIPRO, select demonstrations from training that fit this cap; do not trim text or silently change the requested eight-shot count. If eight do not fit, revise the shared profile on development data before sealing. Reject oversized memory candidates, retain the previous valid state, and log the rejection. An approved empty initial memory is valid. Log natural token growth, dropped/rejected operations and any compression events.

All sources, full expanded prompts and JSON schemas are sealed only after a development preflight exercises every adapter, long inputs, length exhaustion, malformed output, oversized memory and pause/resume. Pin concurrency at 1 for the reference timing profile, with one active model server; run a different judge sequentially. Batch throughput optimizations require a separately reported performance profile. Online items in one stream cannot run out of order. A faster server alone does not resolve nonterminating output.

## 4. Metrics and selection rules

**Dataset-specific definitions are mandatory:** see [DATASET_METRIC_CONDITIONS.md](DATASET_METRIC_CONDITIONS.md) and the exhaustive [metric applicability matrix](metric_applicability.csv). Visible tables must identify metric profile and evaluation reference. Acc means binary accuracy for Dreaddit and exact-set accuracy for GoEmotions; GT-free task accuracy is N/A. A shared display name never establishes a shared task or comparable denominator.

Compute **all applicable registered metrics**, preserve per-item primitives, and export a long-format metric table. Conditional metrics remain explicitly unavailable until their prerequisites are met. Registering a metric does not mean it has already been implemented or measured.

Default report panel:

| **Dataset scope** | **Always display when available** |
| --- | --- |
| Dreaddit | Acc, Macro-F1, stress-class F1, balanced accuracy, MCC |
| GoEmotions | Exact-set Acc, Micro-F1, Macro-F1, sample-F1, Hamming loss |
| All four | Conformability, resolved/100, quote validity, schema validity, prediction coverage, total active time, input/output tokens, retry rate |
| Online | Cumulative and 20-item block metrics; prediction and memory-update counts separately |

The full register adds class-wise precision/recall/F1, specificity, confusion matrices, Jaccard, label cardinality, calibration and ranking metrics when valid probabilities exist, detailed grounding judgments, joint correctness-and-grounding, memory behavior, statistical uncertainty, and operational cost. See [METRIC_REGISTRY.md](METRIC_REGISTRY.md) for exact applicability and denominators.

The main selection objective is fixed before evaluation: Macro-F1 for Dreaddit and Micro-F1 for GoEmotions. GT-free corpora have no objective accuracy ranking; show source-grounding quality together with evidence coverage and failures. Do not optimize an adaptation method using the held-out judge.

Additional metrics may be selected for readability later, but retain this default panel and the complete export. Mark analyses motivated by observed test results **exploratory**, disclose the selection rationale, and report multiplicity-adjusted tests when testing many comparisons. Do not select the most favorable seed, judge, denominator, label subset or metric after observing outcomes.

### Conformability and independent checks

Keep `conformability_legacy_v1` archived separately. The server uses `conformability_v2`: a source-only, method-blind rubric with per-item dimensions for factual support, evidence relevance, attribution and material unsupported assertions. Dimension values are 0=fail, 1=partial/ambiguous, 2=pass. The item passes only if all four dimensions equal 2 and the output/schema is valid. A legitimate source-justified abstention can pass grounding but cannot count as correct classification. The judging payload includes source, frozen task/codebook and final answer/evidence, excluding adaptation memory, method/model identity and GT.

Require an exact supporting quote with source offsets for each predicted label/code and a brief explanation; no private chain-of-thought is required. Quote presence is checked mechanically; whether it supports the claim requires a judge. Missing evidence is a quality failure, not a missing judgment. Model-generated claims are evaluated as claims, never as trusted instructions. Do not equate grounding with label correctness.

Use a fixed primary judge from a different model family from the evaluated backbone if possible. Otherwise mark same-family evaluation prominently. Choose and calibrate the judge only on development outputs before test. Save one frozen judge decision per answer with rubric and model hashes.

Independent human audit: preselect the same 20 evaluation IDs per corpus by an ID-only hash, inspect all 28 conditions on those IDs for seed 42 (560 outputs per backbone), with two blinded reviewers and adjudication of disagreements. Report agreement and calibration on this subset separately; do not project it to all 100. Human review remains pending until actual reviewers annotate. Never report an LLM as a human reviewer or create a human-validated accuracy column for CaChe/ParlaMint from grounding annotations alone. Task correctness there would need a separate fixed reference-label annotation study.

### Unavailable and partial scores

Use `N/A` for inapplicable metrics, `NC` for applicable but not collected, `PENDING` for planned unfinished measurement, and `—` for an unfinalized table cell with status beside it. Never use zero as missing.

For grounding with P passes, F failures and U unresolved among 100 items, show P/(P+F), resolved=(P+F)/100, and the full-panel interval [P/100, (P+U)/100]. Do not present resolved-only percentages as final when U>0. Materially invalid/missing task outputs count as failed task attempts; infrastructure-missing judgments remain unknown. Publish failure-aware full-panel accuracy separately from accuracy conditional on valid outputs. Distributional/F1 metrics require completed eligible predictions or an explicitly declared diagnostic denominator.

Acc can finalize once all 100 attempted predictions are accounted for, independently of judging. A **complete condition-run** requires all 100 valid committed predictions, all required updates, and all 100 resolved primary judgments. A terminal run with failures is `completed_with_failures`, not `complete`. Human and optional metric completion are tracked separately.

Official AppWorld Test-Normal TGC/SGC and Test-Challenge TGC/SGC remain **N/A** for these four corpora. Do not rename accuracy or Conformability as TGC/SGC. Local difficulty slices require separately frozen, prediction-blind annotations and actual slice counts; do not call them official benchmark splits. [ACE evaluation](https://arxiv.org/html/2510.04618v1#S4.SS1), [AppWorld](https://arxiv.org/html/2407.18901v1).

## 5. Statistical reporting

Show each seed separately and mean ± sample SD over three repetitions. Show paired change from the same-backbone Base on the same evaluation items; percentage metrics use percentage-point differences, not ambiguous percent improvements.

For independent offline examples, report 95% paired bootstrap CIs using 10,000 resamples and seed 20260914. Resample source groups when known; disclose unavailable grouping. Aggregate each bootstrap replicate over the same three seeds instead of treating repeats as new independent examples. Small/absent classes receive explicit support counts; no confidence interval rescues a test subset without positive examples.

For online adaptive sequences, use per-seed and 20-item block summaries as the default. Ordinary IID item bootstrap/McNemar tests do not establish uncertainty for a history-dependent learning algorithm. Any additional dependent-data inference must specify its assumptions and separately validated analysis. Do not interpret first-to-last block differences as causal learning gains: item difficulty differs.

If significance tests are requested, use paired tests appropriate to the estimand and dependency structure; Holm correction within each declared family of method comparisons. Report effect sizes and CIs, not only p-values. Never average unlike metrics or combine unsupported GT-free accuracy with labeled accuracy into one overall average.

## 6. Result tables and saved artifacts

Keep the visible main table compact; use detailed metric and operational tables for the complete register. Dataset order is Dreaddit, GoEmotions, CaChe, ParlaMint-GB for this internal comparison. A manuscript export must use the actual Table 1 order required by repository policy.

Main table: model, phase, method, adaptation GT, evaluation N, Acc, Micro-F1, Macro-F1, Conformability, change from matched Base, 95% CI or explicit unavailable marker, repetitions completed, status. A separate operational table contains predicted/100, updated/100, judged/100, unresolved, active time, elapsed time, paused time, input/output tokens, call count, retries, rejected-memory updates, peak VRAM and ETA scope.

One long-format metric row is keyed by protocol/run/model/dataset/method/phase/GT/seed/slice/metric. Store value, unit, direction, numerator, denominator, valid count, missing count, uncertainty method, status, metric version and artifact hashes. Tables are derived from records, not edited score totals. Keep both percentage-point deltas and raw scores.

Store per-item IDs, order, source hash, final parsed output, raw response in access-controlled artifacts, exact quote offsets, output validity, probabilities if available, judge dimensions, error types, token usage, monotonic durations, retry attempts, pre/post memory hashes and update IDs. Save model-native probabilities separately from self-reported confidence. Preserve actual playbooks and private data without placing them in progress notifications.

Archive the paused local panel, new server panel and every protocol revision separately. `RESULTS.md` is a summary, `METRICS.md` is the complete metric report, and this guideline is the stable specification. Add a guideline link to reports without editing sealed runtime source. Notion mirrors only measured results, preserving earlier model sections and other users' content.

## 7. Failures, pause/resume and implementation status

The experiment and five-minute automation remain **paused by user request**. No launch, transfer to a server or model download is authorized by this document alone. Resume requires the user's subsequent instruction and a runnable sealed server manifest.

Use atomic prediction and update checkpoints, an idempotency key per item/stage and one supervisor. Commit predictions before feedback; after interruption reuse the saved prediction and finish its missing update exactly once. Back up before operational repair. Count canceled/truncated inference as discarded cost only when actually measured; manual pause time is not failure waste.

Transient transport retries: at most two extra attempts with 5/15-second backoff and the same request identity. Do not combine retries into an unbounded loop. Reject malformed task output; one identical format retry is allowed without GT or judge feedback. Exhaustion leaves an explicit failure record. A failed online prediction/update interrupts that condition-run to preserve history; other independent conditions may proceed. No silent skip with synthetic output or label leakage. These new failure rules must be tested before sealing; they do not retroactively apply to the local run.

Required implementation work: prepare/audit new split manifests; implement the four missing supervised offline ACE conditions; map full optimizer budgets to pinned upstream APIs; add common evidence output; implement and validate the expanded metric exporters and judge rubric; attach probability scoring only if a valid backend is selected; create seed-aware tables; validate pause/resume and server compatibility. Existing code must not be claimed to satisfy these requirements merely because this document exists.

Freeze `execution_manifest.json` only after model/judge selection and all mandatory checks pass. It must enumerate every planned condition-run, source/data/prompt/runtime hashes, exact settings and metric implementation versions. Later scientific changes create a new protocol revision. Operational repairs preserving those semantics are logged within the run.

## Change log

- 2026-09-14: created server design with 100/100/100 disjoint pools, 28 conditions per model, three repetitions, broad metric register and explicit reporting rules. Existing 24-condition Qwen3-8B run remains paused. No server run has started and no new metric has been claimed as measured.

- 2026-09-14: added dataset-metric-conditions-v1, explicit task/GT/averaging/denominator distinctions, 340 metric-by-dataset applicability records, and mandatory table/export condition fields.

- 2026-09-14: merged previous guidelines and verified MIATA handoff into guideline v5, with historical evidence, conflict decisions, runtime reuse criteria and execution readiness tracked separately. No experiment started.
