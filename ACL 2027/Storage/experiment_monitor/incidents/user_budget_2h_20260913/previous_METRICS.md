# Four-dataset metrics and current results

Updated: **2026-09-13T09:09:19+09:00**. [Shared results](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/RESULTS.md>).

- Dreaddit Acc: stress-label accuracy over all 712 test examples.
- GoEmotions Acc: exact equality of the complete emotion-label set over all 5,427 test examples. Micro-F1 pools label decisions; macro-F1 averages the 28 label scores. Invalid predictions count as wrong for Acc and as an empty set for F1.
- CaChe and ParlaMint-GB: human-GT Acc/F1 are N/A. Reference agreement is exact topic-set agreement with frozen, unverified Qwen3-8B annotations. Invalid topic outputs count as nonagreement. It is not independent ground-truth accuracy.
- GT ✓ uses dataset reference labels in Dreaddit/GoEmotions. GT ✓† in CaChe/ParlaMint means model-generated reference feedback, not human ground truth. GT ✗ provides no reference feedback to adaptation.
- Offline methods adapt before evaluation and freeze the resulting context. Online methods predict the current example before its feedback can update memory for subsequent examples.
- Conformability is the same-family LLM source-grounding pass rate: traceable basis, faithful meaning, supported scope and no invented facts. The judge does not receive reference labels or method identity; its outcomes never feed adaptation. It is not human validation.
- Final percentages require the complete evaluation denominator. Unresolved judgments are displayed, never silently excluded or converted into failures. Partial progress is not a final score.
- CaChe/ParlaMint use a 100-adaptation / 200-evaluation pilot per corpus with provisional topic codebooks. They are not full-corpus benchmark runs. The same teacher/generator/judge family can share errors.
- Current implementations cover different method subsets across corpora, as listed below. Missing methods and GPT-5 are not represented as completed experiments. These are task transfers, not exact reproductions of the finance-paper results.

Last health check: **healthy**, at 2026-09-13T09:09:05+09:00. Recovery is enabled for diagnosed operational failures. [Recovery rules](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_monitor/RECOVERY.md>).

## Dreaddit

Queue: **paused**. [Run-specific metrics](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/dreaddit_icl/comparison_run_20260912/METRICS.md>).

Conformability is a blinded local Qwen-judged evidence-grounding pass rate, not independently verified correctness.

| Method | GT | Acc ↑ (%) | Conformability ↑ (%) | Progress |
| --- | --- | ---: | ---: | --- |
| GPT-5 | — | — | — | API setup pending |
| Qwen3-8B | — | 76.69 | — | predictions 712/712; judged 588/712; unresolved 0 |
| ICL ✓ | ✓ | 51.40 | — | predictions 712/712; judged 0/712; unresolved 0 |
| MIPROv2 ✓ | ✓ | 78.09 | — | predictions 712/712; judged 0/712; unresolved 0 |
| GEPA ✓ | ✓ | 78.65 | — | predictions 712/712; judged 0/712; unresolved 0 |
| DC (CU) ✓ | ✓ | — | — | predictions 97/712; judged 0/712; unresolved 0 |
| DC (CU) ✗ | ✗ | — | — | predictions 0/712; judged 0/712; unresolved 0 |

Both final percentages require all 712 items. Unresolved judgments are not converted to false or excluded silently.
Secondary audit is performed after prediction/adaptation finishes, with no audit feedback to training or memory.
Same-family judging may favor Qwen outputs. This adapted classification rubric is not identical to the prior thematic-review instrument.

## GoEmotions

Queue: **running**. [Run-specific metrics](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/goemotions_offline/run_20260912/METRICS.md>).

Local diagnostic. Official test N = 5,427. ACC is exact label-set match. F1 is reported separately.
Conformability is a local Qwen-judged evidence-grounding pass rate, not human verification.

| Method | GT | Acc % ↑ | Micro-F1 % ↑ | Macro-F1 % ↑ | Conformability % ↑ | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Qwen3-8B | — | 25.63 | 37.06 | 30.30 | — | complete; predictions 5427/5427; judged 0/5427 |
| ICL | ✓ | 20.66 | 33.19 | 24.94 | — | complete; predictions 5427/5427; judged 0/5427 |
| MIPROv2 | ✓ | — | — | — | — | optimizing; predictions 0/5427; judged 0/5427 |
| GEPA | ✓ | — | — | — | — | queued; predictions 0/5427; judged 0/5427 |

All adaptation uses training/development labels only. Test outputs never update prompts.
Invalid outputs count as incorrect exact matches. Their F1 predictions are empty sets.
The original splits are preserved; disjoint comment IDs do not guarantee disjoint authors or identical-text exclusion.
This transfers official DSPy optimizers to a new classification task. It is not an exact reproduction of the finance results.
GPT-5 and ACE are not included in this local queue.

## CaChe and ParlaMint-GB

Queue: **paused**. [Run-specific metrics](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/paired_feedback/run_20260912/METRICS.md>).

Reference annotations saved: **10/600**. This run is paused while GoEmotions has priority.

Real excerpts; 100 adaptation and 200 evaluation items per corpus. GT ✓† means unverified local Qwen3-8B reference labels are supplied to adaptation. These are pseudo-labels, NOT human ground truth. GT ✗ receives no reference labels. Base receives neither.

Human-GT ACC/F1 are N/A. Reference agreement is exact topic-set agreement with the frozen model annotation, not accuracy. Same-family model bias applies. Conformability is a reference-blind LLM grounding judgment, not human verification.

Reference annotation preparation: 10/600. Sealed: False.

| Corpus | Method | GT labels | Human-GT Acc | Reference agreement % | Conformability % | Progress |
| --- | --- | --- | --- | ---: | ---: | --- |
| CaChe | Qwen3-8B | — | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | ACE offline | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | ACE offline | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | DC online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | DC online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | ACE online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| CaChe | ACE online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | Qwen3-8B | — | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE offline | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE offline | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | DC online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | DC online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/200; judged 0/200; unresolved 0; invalid topic outputs 0 |

† References are generated once from the source and fixed codebook, with no evaluated answers, playbooks or judge outcomes. All 600 annotations are sealed before comparative prediction. Matching codebook IDs and verbatim evidence checks verify format/traceability only, not semantic correctness.
Offline: feedback only on 100 adaptation items, then freeze memory. Online: label feedback only after the current prediction, affecting future items. Same task, data, order, model, seed and per-call caps across each pair; native official with/no-GT prompt templates differ. Conformability never feeds adaptation.
Local exploratory method transfer with model-generated supervision; keep separate from human-GT benchmark and manuscript results. The earlier GT-free run is preserved separately; structured topic outputs in this protocol require new paired baselines.
