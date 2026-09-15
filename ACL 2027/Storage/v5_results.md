# v5 results

**Qwen3-8B (Q4_K_M) · Four corpora · 100 evaluation items per corpus · Seeds 42, 43, 44**

Report generated: **2026-09-15 13:09:46 UTC**. This is a live internal experiment record; historical local/server scores are excluded.

| **Progress** | **Current / planned** |
| --- | ---: |
| Valid evaluation predictions | 8,338 / 8,400 |
| Evaluation attempts, including invalid outputs | 8,400 / 8,400 |
| Invalid evaluation outputs | 62 |
| Memory updates, including offline training cycles | 5,400 / 5,400 |
| Judgments | 8,400 / 8,400 |
| Runs with 100 valid predictions | 76 / 84 |
| Fully evaluated runs, including required updates and judgments | 76 / 84 |

**Run states:** 8 finished with invalid outputs; 76 predictions complete.

A prediction-complete run still needs judging. Failed and held runs are explicit; they are not counted as completed. Full completion ETA remains unavailable while methods and judging are unstarted.

**Conformability judge:** `conformability-v2-qwen3-8b-provisional-r1` (seal `de54896874b7`). **Same-family evaluation: the judge is the evaluated Qwen3-8B backbone.** Provisional; human calibration not collected. Conformability is filled only for runs whose 100 judgments are all resolved; unresolved judgments are never imputed.

**Latest stage:** `adaptation_r6_mipro` — `miprov2_prediction_complete` (status observed 2026-09-14 14:09:20 UTC).

ACE/DC r1 production and r2 development are preserved as historical evidence. r3 passed all 18 development cases. Its 36 ACE trajectories remain current. A separate r4 revision replaces only the 18 DC trajectories after passing all six DC development cases. r2 admitted no production because DC repeated to the output limit. A lower selected-panel count after admission reflects fresh trajectories, not deleted evidence. Development predictions are excluded from evaluation totals.

The revised generator format nests evidence under model-selected labels and makes abstention exclusive, then encodes those decisions into the unchanged canonical scoring format. DC retains the r3 serialization bounds: 1–24 complete description/example/usage-count items, with 160/320 Unicode-character text limits. Every model-authored item is rendered without trimming or deduplication. DC r4 additionally limits its generated explanation to 1600 Unicode characters to prevent repetitive answer narration; r3 ACE generation is unchanged. These are additional method-specific format constraints, so this is a documented task transfer rather than an exact free-form-curator reproduction. GT access, data/order, seeds, model, context/role token caps, the final 4096-token memory budget and scoring rules are unchanged. Base/ICL retains its original sealed output format.

**DC recovery execution revision:** `dc-r4-unicode-transport-recovery-v1`. CaChe GT ✗ seed44 and GoEmotions GT ✓ seed44 resume from their preserved r4 checkpoints. Invalid Unicode surrogate strings are rejected through the existing single format retry before tokenization; incomplete responses retry within the existing three-attempt transport limit. Model, prompts, requested schemas, seeds, data order and budgets are unchanged. Original failed responses and GT-reveal receipts are retained; no model-written text is normalized or removed. Five recovery tests and validation of 36 cached development curator responses passed. Prefix audits are recorded separately.

**DC retained-update variant (`four-corpus-server-v5-dc-retained-r5`):** GoEmotions GT ✓ seed 42, GoEmotions GT ✓ seed 43, GoEmotions GT ✓ seed 44 are selected from this separately reported DC variant. A verified unusable curator response is rejected and the prior memory is retained, instead of stopping the condition as the r4 fail-stop policy does. Per its revision record, seeds 42 and 43 are byte-for-byte imports of their complete r4 trajectories because no unusable curator response occurred in them; seed 44 continues its valid r4 prefix under the retained policy. Every other DC (CU) row remains r4 fail-stop. Seed detail marks these rows.

**MIPROv2 (`four-corpus-server-v5-miprov2-r6`):** pinned DSPy MIPROv2 on Dreaddit and GoEmotions, the two corpora with validated label GT. Candidate programs are selected by a full-development corpus F1 objective, macro for Dreaddit and micro for GoEmotions, over all 100 development records on every trial, with minibatching disabled, up to 30 trials and 10 instruction candidates. The selected program, bounded to eight demonstrations and the 4,096-token learned-context budget, is frozen and hashed before evaluation. Both seed-42 development cases passed before admission. A first development attempt that ran both cases in one process failed because the optimizer holds process-global runtime state. It is preserved, and every case now runs in its own process. Development evaluations are not memory updates and are excluded from the update total.

**GEPA (`four-corpus-server-v5-gepa-r7`):** pinned DSPy 3.0.3 GEPA with the GEPA 0.0.7 engine on Dreaddit and GoEmotions, with the v5 budget of 3,000 metric calls, including initialization and validation, and reflection minibatch 3. Reflection uses the same Qwen3-8B backbone at temperature 1.0, as in the documented DSPy configuration. GEPA searches with its native per-item scores, the F1 between reference and predicted label sets, and textual feedback naming reference, missed and unsupported labels. GEPA 0.0.7 averages per-item scores, so the final program is selected separately among its candidates by the same full-development corpus objective as MIPROv2, from recorded development predictions without additional calls. GEPA internals are unchanged. Both seed-42 development cases must pass before admission.

## Experiment conditions

- Each corpus uses **100 train/adaptation + 100 development + 100 evaluation** records. The panel contains 400 unique evaluation records, reused across methods and seeds; 8,400 is the planned number of prediction events.
- The three repetitions reuse the same item set. Their SD describes run/order variation, not 300 independent evaluation examples per corpus.
- Qwen3-8B Q4_K_M, thinking off, context 32,768; up to eight independent RTX A6000 streams. Online items remain serial within each run.
- Learned-context cap: 4,096 tokens. Initial output caps: generator/optimizer/reflector 4,096; curator 8,192. Predeclared length-only retries apply; malformed adaptive outputs stop their condition after the allowed format retry.
- GT ✓/✗ describes feedback used for adaptation. Online GT ✓ is revealed only after the current prediction is committed. Offline memory is learned from train, then frozen before evaluation.
- The evaluation panel was previously observed. These are documented task transfers with stage-specific seals, not exact reproductions of the papers' datasets or hyperparameters.

## Main results

Scores are percentages, shown as **mean ± sample SD across all three seeds** only when that metric is available for all three. `— (2/3)` means two seed scores exist but no partial-seed mean is reported. `N/A` means the metric does not apply. ΔAcc is the percentage-point difference from the matched Base mean.

Acc uses all 100 evaluation attempts per seed, counting invalid outputs as incorrect. For a seed with invalid outputs, Micro/Macro-F1 come from the validated all-attempt derivation `classification-all-attempts-invalid-as-no-label-r1`: an invalid output predicts no label, adding a false negative for its reference label and no false positive, so the denominator is never reduced. The derivation reproduces the stage F1 exactly on all 60 runs without invalid outputs. Seed detail marks these rows.

### Dreaddit

| **Phase** | **Method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **ΔAcc pp** | **Valid / 300** | **Status** |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base | Base | — | 68.67 ± 2.31 | 69.00 ± 1.73 | 67.55 ± 1.60 | 91.33 ± 2.08 | +0.00 | 297/300 | 1 finished with invalid outputs; 2 predictions complete |
| Offline | ICL | ✓ | 66.33 ± 0.58 | 66.44 ± 0.51 | 63.91 ± 0.77 | 83.33 ± 2.52 | -2.33 | 299/300 | 1 finished with invalid outputs; 2 predictions complete |
| Offline | MIPROv2 | ✓ | 70.00 ± 4.58 | 70.00 ± 4.58 | 68.63 ± 5.44 | 97.67 ± 1.53 | +1.33 | 300/300 | 3 predictions complete |
| Offline | GEPA | ✓ | 78.33 ± 2.08 | 78.33 ± 2.08 | 78.33 ± 2.08 | 92.33 ± 2.08 | +9.67 | 300/300 | 3 predictions complete |
| Offline | ACE | ✓ | 79.67 ± 2.89 | 79.67 ± 2.89 | 78.90 ± 3.28 | 76.00 ± 19.29 | +11.00 | 300/300 | 3 predictions complete |
| Offline | ACE | ✗ | 76.00 ± 6.24 | 76.00 ± 6.24 | 75.25 ± 7.11 | 93.67 ± 4.73 | +7.33 | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✓ | 63.67 ± 0.58 | 63.67 ± 0.58 | 60.49 ± 0.77 | 94.67 ± 3.21 | -5.00 | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✗ | 62.33 ± 1.53 | 62.33 ± 1.53 | 58.83 ± 2.32 | 91.33 ± 3.51 | -6.33 | 300/300 | 3 predictions complete |
| Online | ACE | ✓ | 80.00 ± 2.65 | 80.00 ± 2.65 | 79.92 ± 2.74 | 89.00 ± 1.00 | +11.33 | 300/300 | 3 predictions complete |
| Online | ACE | ✗ | 75.67 ± 5.51 | 75.67 ± 5.51 | 75.06 ± 5.98 | 90.67 ± 7.57 | +7.00 | 300/300 | 3 predictions complete |

### GoEmotions

| **Phase** | **Method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **ΔAcc pp** | **Valid / 300** | **Status** |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base | Base | — | 17.00 ± 1.73 | 28.81 ± 0.14 | 8.29 ± 0.06 | 31.67 ± 1.53 | +0.00 | 300/300 | 3 predictions complete |
| Offline | ICL | ✓ | 3.67 ± 3.79 | 13.87 ± 1.81 | 6.76 ± 1.60 | 30.33 ± 8.08 | -13.33 | 300/300 | 3 predictions complete |
| Offline | MIPROv2 | ✓ | 26.33 ± 4.73 | 34.35 ± 3.16 | 8.43 ± 1.18 | 75.33 ± 3.79 | +9.33 | 300/300 | 3 predictions complete |
| Offline | GEPA | ✓ | 17.00 ± 2.65 | 25.73 ± 7.98 | 10.91 ± 0.61 | 78.67 ± 5.69 | +0.00 | 300/300 | 3 predictions complete |
| Offline | ACE | ✓ | 18.67 ± 4.16 | 28.41 ± 3.82 | 13.60 ± 0.54 | 77.67 ± 4.04 | +1.67 | 300/300 | 3 predictions complete |
| Offline | ACE | ✗ | 14.67 ± 1.15 | 28.03 ± 5.79 | 12.39 ± 3.93 | 69.33 ± 5.51 | -2.33 | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✓ | 9.67 ± 5.51 | 19.60 ± 4.52 | 6.07 ± 1.68 | 50.33 ± 19.63 | -7.33 | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✗ | 13.67 ± 5.51 | 22.33 ± 4.78 | 6.41 ± 0.20 | 57.33 ± 3.06 | -3.33 | 300/300 | 3 predictions complete |
| Online | ACE | ✓ | 19.00 ± 2.00 | 27.82 ± 1.83 | 12.18 ± 0.50 | 70.00 ± 4.36 | +2.00 | 300/300 | 3 predictions complete |
| Online | ACE | ✗ | 11.67 ± 3.21 | 21.27 ± 7.76 | 10.93 ± 2.07 | 69.00 ± 2.65 | -5.33 | 300/300 | 3 predictions complete |

### CaChe

| **Phase** | **Method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **ΔAcc pp** | **Valid / 300** | **Status** |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base | Base | — | N/A | N/A | N/A | 74.33 ± 2.08 | N/A | 284/300 | 3 finished with invalid outputs |
| Offline | ACE | ✗ | N/A | N/A | N/A | 30.00 ± 18.68 | N/A | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✗ | N/A | N/A | N/A | 70.33 ± 8.08 | N/A | 300/300 | 3 predictions complete |
| Online | ACE | ✗ | N/A | N/A | N/A | 52.67 ± 27.01 | N/A | 300/300 | 3 predictions complete |

### ParlaMint-GB

| **Phase** | **Method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **ΔAcc pp** | **Valid / 300** | **Status** |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base | Base | — | N/A | N/A | N/A | 70.00 ± 1.00 | N/A | 258/300 | 3 finished with invalid outputs |
| Offline | ACE | ✗ | N/A | N/A | N/A | 66.00 ± 12.29 | N/A | 300/300 | 3 predictions complete |
| Online | DC (CU) | ✗ | N/A | N/A | N/A | 75.00 ± 6.56 | N/A | 300/300 | 3 predictions complete |
| Online | ACE | ✗ | N/A | N/A | N/A | 57.67 ± 17.04 | N/A | 300/300 | 3 predictions complete |

## Dataset-specific metric definitions

| **Dataset** | **Accuracy** | **F1 / label conditions** | **Conformability** |
| --- | --- | --- | --- |
| Dreaddit | Binary exact-label accuracy against released stress labels | Micro/Macro-F1 over both classes; stress-class F1 and other binary metrics are in the source JSON when available | Source-grounding judgment, independent of classification correctness; provisional same-model judge |
| GoEmotions | Exact-set accuracy over the 28 official labels | Multilabel Micro/Macro-F1; official neutral co-labels are preserved. Macro-F1 over all 28 labels differs from supported-label Macro-F1 | Same four-dimension v2 grounding rubric; provisional same-model judge |
| CaChe | N/A: no validated label GT for the provisional thematic codebook | Label-reference F1 N/A. Model agreement is not substituted for accuracy | Source-only thematic grounding; provisional same-model judge |
| ParlaMint-GB | N/A: no validated label GT for the provisional thematic codebook | Label-reference F1 N/A. These provisional topics are not CAP benchmark labels | Source-only thematic grounding; provisional same-model judge |

**Conformability v2:** a method-blind, source-only judge scores factual support, evidence relevance, attribution, and material unsupported assertions on 0/1/2. A pass requires all four dimensions equal 2 and valid output/schema. Scores come from the provisional same-model Qwen3-8B judge named above; a known invalid prediction is a resolved failure without a judge call.

Literal exact-quote match and raw model-reported offset validity are separate mechanical diagnostics in the linked JSON reports. They are not Conformability. Partial quote statistics are not promoted to completed method scores.

**Test-Normal TGC↑, Test-Normal SGC↑, Test-Challenge TGC↑, Test-Challenge SGC↑:** N/A for all four corpora; there are no corresponding AppWorld task-success evaluators, scenario groups, or official Normal/Challenge splits.

**Other metrics:** available per-seed source reports contain applicable precision/recall/F1 variants, class-wise statistics, confusion matrices, and corpus-specific metrics. Confidence intervals, probability-based calibration/ranking, human review, complete cost telemetry, and other conditional registry entries remain pending or unavailable until their prerequisites and exporters are satisfied. Registering a metric is not evidence it was measured.

## Per-seed results and progress

`Pred` = valid / attempted evaluation outputs, with 100 planned per seed. `Train` = offline ACE adaptation attempts. `Upd` = committed memory-update cycles, including rejected oversized candidates that retain prior valid memory. `Active min` is per-run active time; simultaneous runs must not be summed as elapsed wall time.

### Dreaddit — seed detail

| **Phase / method** | **GT** | **Seed** | **Pred** | **Train** | **Upd** | **Judged** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conf %** | **Active min** | **Status** |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base / Base | — | 42 | 100/100 | — | — | 100/100 | 70.00 | 70.00 | 68.47 | 92.00 | 10.1 | Predictions complete |
| Base / Base | — | 43 | 97/100 | — | — | 100/100 | 66.00 | 67.01 | 65.70 | 89.00 | 10.1 | Finished with invalid outputs · F1 counts 3 invalid as no label |
| Base / Base | — | 44 | 100/100 | — | — | 100/100 | 70.00 | 70.00 | 68.47 | 93.00 | 7.9 | Predictions complete |
| Offline / ICL | ✓ | 42 | 99/100 | — | — | 100/100 | 66.00 | 66.33 | 63.40 | 83.00 | 10.3 | Finished with invalid outputs · F1 counts 1 invalid as no label |
| Offline / ICL | ✓ | 43 | 100/100 | — | — | 100/100 | 67.00 | 67.00 | 64.80 | 86.00 | 10.8 | Predictions complete |
| Offline / ICL | ✓ | 44 | 100/100 | — | — | 100/100 | 66.00 | 66.00 | 63.53 | 81.00 | 7.3 | Predictions complete |
| Offline / MIPROv2 | ✓ | 42 | 100/100 | — | — | 100/100 | 71.00 | 71.00 | 69.91 | 99.00 | 169.6 | Predictions complete |
| Offline / MIPROv2 | ✓ | 43 | 100/100 | — | — | 100/100 | 74.00 | 74.00 | 73.32 | 96.00 | 149.4 | Predictions complete |
| Offline / MIPROv2 | ✓ | 44 | 100/100 | — | — | 100/100 | 65.00 | 65.00 | 62.67 | 98.00 | 160.4 | Predictions complete |
| Offline / GEPA | ✓ | 42 | 100/100 | — | — | 100/100 | 76.00 | 76.00 | 75.99 | 93.00 | 252.4 | Predictions complete |
| Offline / GEPA | ✓ | 43 | 100/100 | — | — | 100/100 | 79.00 | 79.00 | 79.00 | 90.00 | 261.7 | Predictions complete |
| Offline / GEPA | ✓ | 44 | 100/100 | — | — | 100/100 | 80.00 | 80.00 | 79.99 | 94.00 | 264.1 | Predictions complete |
| Offline / ACE | ✓ | 42 | 100/100 | 100 | 100 | 100/100 | 78.00 | 78.00 | 77.68 | 90.00 | 44.4 | Predictions complete |
| Offline / ACE | ✓ | 43 | 100/100 | 100 | 100 | 100/100 | 78.00 | 78.00 | 76.40 | 54.00 | 44.2 | Predictions complete |
| Offline / ACE | ✓ | 44 | 100/100 | 100 | 100 | 100/100 | 83.00 | 83.00 | 82.61 | 84.00 | 32.6 | Predictions complete |
| Offline / ACE | ✗ | 42 | 100/100 | 100 | 100 | 100/100 | 78.00 | 78.00 | 77.56 | 92.00 | 43.7 | Predictions complete |
| Offline / ACE | ✗ | 43 | 100/100 | 100 | 100 | 100/100 | 81.00 | 81.00 | 80.91 | 90.00 | 43.7 | Predictions complete |
| Offline / ACE | ✗ | 44 | 100/100 | 100 | 100 | 100/100 | 69.00 | 69.00 | 67.27 | 99.00 | 35.0 | Predictions complete |
| Online / DC (CU) | ✓ | 42 | 100/100 | — | 100 | 100/100 | 64.00 | 64.00 | 60.94 | 97.00 | 19.4 | Predictions complete |
| Online / DC (CU) | ✓ | 43 | 100/100 | — | 100 | 100/100 | 63.00 | 63.00 | 59.60 | 96.00 | 19.2 | Predictions complete |
| Online / DC (CU) | ✓ | 44 | 100/100 | — | 100 | 100/100 | 64.00 | 64.00 | 60.94 | 91.00 | 18.1 | Predictions complete |
| Online / DC (CU) | ✗ | 42 | 100/100 | — | 100 | 100/100 | 62.00 | 62.00 | 58.24 | 95.00 | 18.1 | Predictions complete |
| Online / DC (CU) | ✗ | 43 | 100/100 | — | 100 | 100/100 | 64.00 | 64.00 | 61.39 | 88.00 | 18.7 | Predictions complete |
| Online / DC (CU) | ✗ | 44 | 100/100 | — | 100 | 100/100 | 61.00 | 61.00 | 56.85 | 91.00 | 18.9 | Predictions complete |
| Online / ACE | ✓ | 42 | 100/100 | — | 100 | 100/100 | 77.00 | 77.00 | 76.81 | 90.00 | 33.5 | Predictions complete |
| Online / ACE | ✓ | 43 | 100/100 | — | 100 | 100/100 | 82.00 | 82.00 | 81.97 | 89.00 | 35.1 | Predictions complete |
| Online / ACE | ✓ | 44 | 100/100 | — | 100 | 100/100 | 81.00 | 81.00 | 80.98 | 88.00 | 35.5 | Predictions complete |
| Online / ACE | ✗ | 42 | 100/100 | — | 100 | 100/100 | 72.00 | 72.00 | 71.06 | 96.00 | 33.3 | Predictions complete |
| Online / ACE | ✗ | 43 | 100/100 | — | 100 | 100/100 | 73.00 | 73.00 | 72.20 | 94.00 | 34.4 | Predictions complete |
| Online / ACE | ✗ | 44 | 100/100 | — | 100 | 100/100 | 82.00 | 82.00 | 81.93 | 82.00 | 33.3 | Predictions complete |

### GoEmotions — seed detail

| **Phase / method** | **GT** | **Seed** | **Pred** | **Train** | **Upd** | **Judged** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conf %** | **Active min** | **Status** |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base / Base | — | 42 | 100/100 | — | — | 100/100 | 18.00 | 28.93 | 8.22 | 30.00 | 5.7 | Predictions complete |
| Base / Base | — | 43 | 100/100 | — | — | 100/100 | 18.00 | 28.84 | 8.33 | 33.00 | 5.8 | Predictions complete |
| Base / Base | — | 44 | 100/100 | — | — | 100/100 | 15.00 | 28.66 | 8.31 | 32.00 | 5.9 | Predictions complete |
| Offline / ICL | ✓ | 42 | 100/100 | — | — | 100/100 | 2.00 | 14.15 | 5.11 | 29.00 | 5.8 | Predictions complete |
| Offline / ICL | ✓ | 43 | 100/100 | — | — | 100/100 | 1.00 | 11.94 | 8.30 | 23.00 | 5.8 | Predictions complete |
| Offline / ICL | ✓ | 44 | 100/100 | — | — | 100/100 | 8.00 | 15.53 | 6.86 | 39.00 | 4.7 | Predictions complete |
| Offline / MIPROv2 | ✓ | 42 | 100/100 | — | — | 100/100 | 28.00 | 35.54 | 7.75 | 71.00 | 120.1 | Predictions complete |
| Offline / MIPROv2 | ✓ | 43 | 100/100 | — | — | 100/100 | 30.00 | 36.75 | 9.79 | 78.00 | 119.4 | Predictions complete |
| Offline / MIPROv2 | ✓ | 44 | 100/100 | — | — | 100/100 | 21.00 | 30.77 | 7.75 | 77.00 | 112.7 | Predictions complete |
| Offline / GEPA | ✓ | 42 | 100/100 | — | — | 100/100 | 15.00 | 20.25 | 11.12 | 85.00 | 209.7 | Predictions complete |
| Offline / GEPA | ✓ | 43 | 100/100 | — | — | 100/100 | 20.00 | 34.88 | 11.39 | 74.00 | 232.2 | Predictions complete |
| Offline / GEPA | ✓ | 44 | 100/100 | — | — | 100/100 | 16.00 | 22.05 | 10.22 | 77.00 | 215.1 | Predictions complete |
| Offline / ACE | ✓ | 42 | 100/100 | 100 | 100 | 100/100 | 20.00 | 29.15 | 13.88 | 80.00 | 41.5 | Predictions complete |
| Offline / ACE | ✓ | 43 | 100/100 | 100 | 100 | 100/100 | 22.00 | 31.80 | 13.93 | 73.00 | 43.8 | Predictions complete |
| Offline / ACE | ✓ | 44 | 100/100 | 100 | 100 | 100/100 | 14.00 | 24.27 | 12.98 | 80.00 | 30.0 | Predictions complete |
| Offline / ACE | ✗ | 42 | 100/100 | 100 | 100 | 100/100 | 14.00 | 28.91 | 16.40 | 73.00 | 41.7 | Predictions complete |
| Offline / ACE | ✗ | 43 | 100/100 | 100 | 100 | 100/100 | 16.00 | 33.33 | 12.22 | 63.00 | 43.2 | Predictions complete |
| Offline / ACE | ✗ | 44 | 100/100 | 100 | 100 | 100/100 | 14.00 | 21.86 | 8.55 | 72.00 | 33.3 | Predictions complete |
| Online / DC (CU) | ✓ | 42 | 100/100 | — | 100 | 100/100 | 15.00 | 21.95 | 6.29 | 73.00 | 36.5 | Predictions complete · retained DC variant |
| Online / DC (CU) | ✓ | 43 | 100/100 | — | 100 | 100/100 | 4.00 | 14.39 | 4.29 | 39.00 | 55.7 | Predictions complete · retained DC variant |
| Online / DC (CU) | ✓ | 44 | 100/100 | — | 100 | 100/100 | 10.00 | 22.47 | 7.64 | 39.00 | 42.0 | Predictions complete · retained DC variant |
| Online / DC (CU) | ✗ | 42 | 100/100 | — | 100 | 100/100 | 8.00 | 18.32 | 6.51 | 54.00 | 40.4 | Predictions complete |
| Online / DC (CU) | ✗ | 43 | 100/100 | — | 100 | 100/100 | 19.00 | 27.62 | 6.54 | 58.00 | 43.8 | Predictions complete |
| Online / DC (CU) | ✗ | 44 | 100/100 | — | 100 | 100/100 | 14.00 | 21.05 | 6.19 | 60.00 | 34.7 | Predictions complete |
| Online / ACE | ✓ | 42 | 100/100 | — | 100 | 100/100 | 17.00 | 25.91 | 12.53 | 68.00 | 32.8 | Predictions complete |
| Online / ACE | ✓ | 43 | 100/100 | — | 100 | 100/100 | 21.00 | 29.57 | 12.40 | 75.00 | 33.0 | Predictions complete |
| Online / ACE | ✓ | 44 | 100/100 | — | 100 | 100/100 | 19.00 | 27.98 | 11.61 | 67.00 | 33.4 | Predictions complete |
| Online / ACE | ✗ | 42 | 100/100 | — | 100 | 100/100 | 13.00 | 17.10 | 10.58 | 70.00 | 33.4 | Predictions complete |
| Online / ACE | ✗ | 43 | 100/100 | — | 100 | 100/100 | 8.00 | 16.48 | 9.06 | 66.00 | 34.3 | Predictions complete |
| Online / ACE | ✗ | 44 | 100/100 | — | 100 | 100/100 | 14.00 | 30.22 | 13.16 | 71.00 | 34.6 | Predictions complete |

### CaChe — seed detail

| **Phase / method** | **GT** | **Seed** | **Pred** | **Train** | **Upd** | **Judged** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conf %** | **Active min** | **Status** |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base / Base | — | 42 | 94/100 | — | — | 100/100 | N/A | N/A | N/A | 75.00 | 6.4 | Finished with invalid outputs |
| Base / Base | — | 43 | 95/100 | — | — | 100/100 | N/A | N/A | N/A | 72.00 | 5.8 | Finished with invalid outputs |
| Base / Base | — | 44 | 95/100 | — | — | 100/100 | N/A | N/A | N/A | 76.00 | 5.9 | Finished with invalid outputs |
| Offline / ACE | ✗ | 42 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 47.00 | 39.8 | Predictions complete |
| Offline / ACE | ✗ | 43 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 10.00 | 36.1 | Predictions complete |
| Offline / ACE | ✗ | 44 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 33.00 | 32.3 | Predictions complete |
| Online / DC (CU) | ✗ | 42 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 79.00 | 36.7 | Predictions complete |
| Online / DC (CU) | ✗ | 43 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 69.00 | 42.7 | Predictions complete |
| Online / DC (CU) | ✗ | 44 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 63.00 | 29.0 | Predictions complete |
| Online / ACE | ✗ | 42 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 26.00 | 30.2 | Predictions complete |
| Online / ACE | ✗ | 43 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 80.00 | 30.7 | Predictions complete |
| Online / ACE | ✗ | 44 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 52.00 | 34.5 | Predictions complete |

### ParlaMint-GB — seed detail

| **Phase / method** | **GT** | **Seed** | **Pred** | **Train** | **Upd** | **Judged** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conf %** | **Active min** | **Status** |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base / Base | — | 42 | 85/100 | — | — | 100/100 | N/A | N/A | N/A | 70.00 | 11.9 | Finished with invalid outputs |
| Base / Base | — | 43 | 86/100 | — | — | 100/100 | N/A | N/A | N/A | 71.00 | 10.9 | Finished with invalid outputs |
| Base / Base | — | 44 | 87/100 | — | — | 100/100 | N/A | N/A | N/A | 69.00 | 7.7 | Finished with invalid outputs |
| Offline / ACE | ✗ | 42 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 75.00 | 47.9 | Predictions complete |
| Offline / ACE | ✗ | 43 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 71.00 | 48.4 | Predictions complete |
| Offline / ACE | ✗ | 44 | 100/100 | 100 | 100 | 100/100 | N/A | N/A | N/A | 52.00 | 35.1 | Predictions complete |
| Online / DC (CU) | ✗ | 42 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 69.00 | 51.7 | Predictions complete |
| Online / DC (CU) | ✗ | 43 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 82.00 | 26.6 | Predictions complete |
| Online / DC (CU) | ✗ | 44 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 74.00 | 43.3 | Predictions complete |
| Online / ACE | ✗ | 42 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 67.00 | 36.5 | Predictions complete |
| Online / ACE | ✗ | 43 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 68.00 | 35.9 | Predictions complete |
| Online / ACE | ✗ | 44 | 100/100 | — | 100 | 100/100 | N/A | N/A | N/A | 38.00 | 34.8 | Predictions complete |

## AppWorld · ACE reproduction with Qwen3-8B

A separate experiment from the four-corpus panel above: the released ace-appworld configurations and paper-era ACE agents, with only the language model replaced by Qwen3-8B (Q4_K_M, thinking off, context 32,768). One run per condition. TGC = task goal completion (all unit tests of a task pass); SGC = scenario goal completion (all tasks of a scenario pass); both from the official AppWorld evaluator. A dash means the condition has not finished; no partial-split value is reported.

| **Method** | **GT** | **Test-Normal TGC ↑** | **Test-Normal SGC ↑** | **Test-Challenge TGC ↑** | **Test-Challenge SGC ↑** | **Status** |
| --- | :---: | ---: | ---: | ---: | ---: | --- |
| ReAct | — | 17.9 | 3.6 | 6.2 | 1.4 | normal complete; challenge complete |
| ACE offline | ✓ | 22.0 | 10.7 | — | — | normal complete; challenge running |
| ACE offline | ✗ | 20.8 | 10.7 | — | — | normal complete; challenge running |
| ACE online | ✗ | 18.4 | 5.4 | — | — | normal complete; challenge running |

**Paper reference, not our results:** Zhang et al. (ICLR 2026), Table 1, DeepSeek-V3.1 backbone.

| **Method** | **GT** | **Test-Normal TGC** | **Test-Normal SGC** | **Test-Challenge TGC** | **Test-Challenge SGC** |
| --- | :---: | ---: | ---: | ---: | ---: |
| ReAct | — | 63.7 | 42.9 | 41.5 | 21.6 |
| ACE offline | ✓ | 76.2 | 64.3 | 57.3 | 39.6 |
| ACE offline | ✗ | 75.0 | 64.3 | 54.4 | 35.2 |
| ACE online | ✗ | 69.6 | 53.6 | 66.0 | 48.9 |

**AppWorld progress**

| **Job** | **Kind** | **Tasks started** | **Context exhausted** | **Status** | **Trained playbook** |
| --- | --- | ---: | ---: | --- | --- |
| `ReAct_test_normal` | evaluation | 168/168 | 187 | complete | — |
| `ReAct_test_challenge` | evaluation | 417/417 | 874 | complete | — |
| `ACE_offline_with_GT_adaptation` | adaptation | 90/90 | 1410 | complete | [playbook.txt](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/appworld_ace_qwen/playbooks/offline_with_GT/playbook.txt>) (148 bullets) |
| `ACE_offline_with_GT_evaluation_test_normal` | evaluation | 168/168 | 539 | complete | — |
| `ACE_offline_with_GT_evaluation_test_challenge` | evaluation | 402/417 | 3159 | running | — |
| `ACE_offline_no_GT_adaptation` | adaptation | 90/90 | 86 | complete | [playbook.txt](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/appworld_ace_qwen/playbooks/offline_no_GT/playbook.txt>) (72 bullets) |
| `ACE_offline_no_GT_evaluation_test_normal` | evaluation | 168/168 | 122 | complete | — |
| `ACE_offline_no_GT_evaluation_test_challenge` | evaluation | 376/417 | 1370 | running | — |
| `ACE_online_no_GT_test_normal` | online | 168/168 | 422 | complete | [playbook.txt](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/appworld_ace_qwen/playbooks/online_no_GT_test_normal/playbook.txt>) (93 bullets) |
| `ACE_online_no_GT_test_challenge` | online | 129/417 | 860 | running | [playbook.txt](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/appworld_ace_qwen/playbooks/online_no_GT_test_challenge/playbook.txt>) (61 bullets) |

Context exhausted counts model calls whose input did not fit the 32,768-token context; following the upstream generator, such a call returns an empty response and the input is never truncated. Deviations from the paper environment: Python 3.13 (changes traceback formatting shown to the agent), a one-line evaluator return-value compatibility patch, and the released configurations’ single offline epoch. Native-bridge revision r2 (decided 2026-09-15): a model response the local runtime leaves incomplete is retried up to three times and, if still incomplete, its partial text is passed to the agent; r1 stopped the shard instead. Only the three test_challenge shards that stopped on such a response were rerun; every other job had none, so its calls and scores are unchanged. Trained playbooks are mirrored under `Storage/appworld_ace_qwen/playbooks/`; snapshots every 30 tasks sit beside each live file.

## Sources and refresh

This file is regenerated from the following v5 metadata snapshots. The existing five-minute monitor refreshes the server mirrors and regenerates this file. Server stage reports refresh about every 20 seconds while their controller runs; this file is a periodic snapshot. Links below point to the local workspace mirrors. Original server artifacts are under `/home/sy23985/Storage/acl2027_server_v5_20260914`.

- [four-corpus-server-v5-prediction-stage-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/live/results.json>) — 2026-09-14 04:23:17 UTC, seal `84e81e7b72a1ce69359fef80e7101168284b055690ed97e190c65430a525c4bc`.
- [four-corpus-server-v5-adaptation-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r1/results.json>) — 2026-09-14 05:02:56 UTC, seal `6f2c9c9c4cb050413aa8eaf215b1ea250bf3593eac1832564f00188e8aad3906`.
- [four-corpus-server-v5-adaptation-r3](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r3/results.json>) — 2026-09-14 09:22:01 UTC, seal `ad467964d07d8cf222bf78d623fc5eacbe0479e2597d2ecac2eaaa2c57414abc`.
- [four-corpus-server-v5-dc-adaptation-r4](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r4/results.json>) — 2026-09-14 10:12:13 UTC, seal `97c1f0d4271fe4056b412aae62c1e7f6c657b309caf9821df76da5ae922943a9`.
- [four-corpus-server-v5-dc-retained-r5](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r5_retained/results.json>) — 2026-09-14 10:41:03 UTC, seal `fd26642ee63acd0b5d7485ce8b4d3505c532d56c56505e14ece11d749ff1baca`.
- [four-corpus-server-v5-miprov2-r6](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r6_mipro/results.json>) — 2026-09-14 14:07:59 UTC, seal `055a52b87bbede3124817b1ed3c7c486a045e7c6e3ced3b22292a6ce098b1421`.
- [four-corpus-server-v5-gepa-r7](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/adaptation_r7_gepa/results.json>) — 2026-09-15 05:25:47 UTC, seal `ae065f0b734d1e2e07f5f7a6803fe9104b9dc0ef3db37bfd056c2e2c790370fa`.
- [conformability-v2-qwen3-8b-provisional-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/evaluation/conformability_v2_r1/results.json>) — judge, 2026-09-15 00:56:32 UTC, seal `39c78e4ecc87a75bd817e1bb4e69d020720a12b86ec2eddda6477dea56d3973c`.
- [conformability-v2-qwen3-8b-provisional-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/evaluation/conformability_v2_r1_miprov2/results.json>) — judge, 2026-09-15 00:59:35 UTC, seal `9252c92606f30eb3b219785ae46600ffd9d98978eb9bbfeb930e8e1ba09ee6a5`.
- [conformability-v2-qwen3-8b-provisional-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/evaluation/conformability_v2_r1_gepa/results.json>) — judge, 2026-09-15 05:29:19 UTC, seal `de54896874b786791fd33b27ac07840a59e658ab647fecdb1e80b3345f593568`.
- [classification-all-attempts-invalid-as-no-label-r1](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/derived/classification_all_attempts_r1/results.json>) — derived metric, 2026-09-15 05:29:20 UTC, validated on 60 runs without invalid outputs.

- [Machine-readable snapshot of the 84 planned runs](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/v5_results.snapshot.json>)
- [Current execution status](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/STATUS.md>)
- [Fixed v5 metric registry and applicability](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_guidelines/four_corpus_server_v5/METRIC_REGISTRY.md>)
- [Terminal progress viewer](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/server_v5_preparation/TERMINAL_PROGRESS.md>)

Later revisions select the latest admitted result for each matching condition; repeats are not counted as independent runs. Source stage reports and older evidence remain preserved. No source excerpts, generated answers, GT labels, or playbooks are included here.
