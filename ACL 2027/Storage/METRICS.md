> Consolidated v5 results: [v5_results.md](v5_results.md).

> Current server v5: Base/ICL finished **1,800 attempts, 1,738 valid outputs, 62 format failures**. **ACE/DC is running: 33 seed runs admitted, 21 held for development fixes.** [Live ACE/DC results](server_v5_preparation/adaptation_r1/RESULTS.md) · [Base/ICL results](server_v5_preparation/live/RESULTS.md) · [Full status](server_v5_preparation/STATUS.md). Judging remains pending. Historical local results below retain their original protocol.

> Next server comparison: [merged experiment guidelines v5](EXPERIMENT_GUIDELINES.md). This report remains the separate paused local run.

# Fresh uniform comparison: 100 shared evaluation items per dataset

Updated: 2026-09-14T08:59:44+09:00. Run: run_20260914_uniform. All 24 rows begin afresh; old predictions, judgments, optimizer artifacts and playbooks are never imported. Same 400 unique evaluation IDs, fixed seed 42, Qwen3-8B Q4_K_M, thinking off, context 32768.

Common initial output caps: prediction/generator/optimizer/reflector 4096; curator 8192; judge 384. Length-only retries for non-judge roles double the cap to at most 16384 and available context. Partial output is discarded. ACE/DC memories are capped at 4096 Qwen tokens; over-budget candidates retain the previous valid memory, with a logged event. These rules apply from the start to every method.

Official method-specific prompts, optimizer search temperatures and reduced search budgets are preserved. Supervised offline: Base, ICL (up to 8 demos), MIPROv2 (2 candidates, 4 trials), GEPA (96 metric-call budget). GT-free offline: Base and ACE with 4 separate adaptation items. Online: DC/ACE, GT yes/no on released-label corpora and GT-free only on CaChe/ParlaMint. This is a controlled local transfer, not an exact paper reproduction.

Acc: Dreaddit binary accuracy; GoEmotions exact label-set accuracy; CaChe/ParlaMint N/A. Conformability: reference-blind same-family source grounding, not human validation. Final scores require all 100 resolved judgments. No test labels or judge outcomes enter offline adaptation; online current labels arrive only after the saved prediction. Extra runtime is authorized; there is no two-hour cutoff.

## Dreaddit

Offline evaluation N=100 (same IDs as online). Corpus queue: queued; — / — 0/100.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | — | — | — | — | — | queued; predicted 0/100; judged 0/100; unresolved 0 |
| icl | — | — | — | — | — | queued; predicted 0/100; judged 0/100; unresolved 0 |
| miprov2 | — | — | — | — | — | queued; predicted 0/100; judged 0/100; unresolved 0 |
| gepa | — | — | — | — | — | queued; predicted 0/100; judged 0/100; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/offline100/run_20260914_uniform/dreaddit/METRICS.md>).

## GoEmotions

Offline evaluation N=100 (same IDs as online). Corpus queue: paused; — / — 0/100.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | 26.00 | — | 35.48 | 23.38 | 100.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |
| icl | 22.00 | — | 33.20 | 23.80 | 99.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |
| miprov2 | 19.00 | — | 29.91 | 19.38 | 99.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |
| gepa | 23.00 | — | 31.54 | 16.65 | 100.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/offline100/run_20260914_uniform/goemotions/METRICS.md>).

## CaChe

Offline evaluation N=100 (same IDs as online). Corpus queue: failed; ace_offline_no_gt / prediction 0/100.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | N/A | N/A | — | — | 99.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |
| ace_offline_no_gt | N/A | N/A | — | — | — | running; predicted 0/100; judged 0/100; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/offline100/run_20260914_uniform/cache/METRICS.md>).

## ParlaMint-GB

Offline evaluation N=100 (same IDs as online). Corpus queue: failed; — / — 0/100.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | N/A | N/A | — | — | 100.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |
| ace_offline_no_gt | N/A | N/A | — | — | 100.00 | complete; predicted 100/100; judged 100/100; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/offline100/run_20260914_uniform/parlamint_gb/METRICS.md>).


# Online adaptation: 100 examples per dataset

Updated: 2026-09-14T08:59:44+09:00. Dreaddit/GoEmotions: DC/ACE × GT yes/no. CaChe/ParlaMint: DC/ACE, GT-free only. Total 12 rows, 100 ordered examples per row.

Qwen3-8B Q4_K_M; seed 42, thinking off. Each method starts with empty memory and receives the same IDs in the same order. Save each prediction before current-label feedback. Evaluate that pre-update prediction. Never feed judge outcomes into adaptation. Offline/full-test results remain separate.

User-authorized extra time: both offline and online prioritize completing 100 items and all judgments. No two-hour cutoff applies.

Dreaddit/GoEmotions GT yes uses released labels, with binary/exact label-set ACC respectively. CaChe/ParlaMint use GT-free adaptation only; no reference labels are generated or supplied. Their ACC and reference agreement are N/A. Conformability is a reference-blind same-family LLM grounding judgment, not human verification. These are local task transfers, not exact paper reproductions.

Fresh uniform-local-v1: no earlier inference or memory imported. Shared initial output caps 4096 (prediction/generator/optimization/reflector), 8192 (curator), 384 (judge); non-judge length-only escalation up to 16384 within context 32768. ACE/DC memory bound 4096; reject oversized updates and retain previous valid memory.

## Dreaddit: online N=100

Queue: queued; — / — 0/100.

| Method | GT | Acc % | Reference agreement % | Conformability % | Progress |
| --- | --- | ---: | ---: | ---: | --- |
| DC (CU) | ✓ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |
| DC (CU) | ✗ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |
| ACE | ✓ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |
| ACE | ✗ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |

## GoEmotions: online N=100

Queue: paused; dc_online_ref / prediction 85/100.

| Method | GT | Acc % | Reference agreement % | Conformability % | Progress |
| --- | --- | ---: | ---: | ---: | --- |
| DC (CU) | ✓ | — | — | — | running; saved 86/100; updated 85/100; judged 0/100; unresolved 0 |
| DC (CU) | ✗ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |
| ACE | ✓ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |
| ACE | ✗ | — | — | — | queued; saved 0/100; updated 0/100; judged 0/100; unresolved 0 |

## CaChe: online N=100

Queue: complete; — / — 0/100.

| Method | GT | Acc % | Reference agreement % | Conformability % | Progress |
| --- | --- | ---: | ---: | ---: | --- |
| DC (CU) | ✗ | N/A | N/A | 99.00 | complete; saved 100/100; updated 100/100; judged 100/100; unresolved 0 |
| ACE | ✗ | N/A | N/A | 100.00 | complete; saved 100/100; updated 100/100; judged 100/100; unresolved 0 |

## ParlaMint-GB: online N=100

Queue: failed; ace_online_no_gt / prediction 16/100.

| Method | GT | Acc % | Reference agreement % | Conformability % | Progress |
| --- | --- | ---: | ---: | ---: | --- |
| DC (CU) | ✗ | N/A | N/A | 99.00 | complete; saved 100/100; updated 100/100; judged 100/100; unresolved 0 |
| ACE | ✗ | N/A | N/A | — | running; saved 16/100; updated 16/100; judged 0/100; unresolved 0 |


## Preserved earlier runs

Earlier full-test scores use different denominators and protocols. They remain in their original directories and must not be compared as the same run.

- [Superseded 24/128/8-item offline pilot](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/METRICS.md>)
- [Dreaddit](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/dreaddit_icl/comparison_run_20260912/METRICS.md>)
- [GoEmotions](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/goemotions_offline/run_20260912/METRICS.md>)
- [Paired corpora](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/paired_feedback/run_20260912/METRICS.md>)

[Archived earlier N=100 results](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_monitor/incidents/output_cap_recovery_20260914/prior_RESULTS.md>).
