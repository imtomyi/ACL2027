# Reduced four-dataset pilot

Updated: 2026-09-13T09:28:42+09:00. User-authorized new protocol: at most 2 hours of wall time per dataset, serial execution (up to about 8 hours total, plus transition overhead).

Model: Qwen3-8B Q4_K_M, thinking off, seed 42. No full-run scores or predictions are imported. Fixed outcome-blind subsets are used for every method in each dataset. Small pilot results have high sampling uncertainty and are not full-test benchmarks.

Supervised offline: Base, 8-example ICL, MIPROv2 (2 candidates, 4 trials), GEPA (96 metric-call budget). Dreaddit additionally runs DC GT yes/no. CaChe and ParlaMint run Base, ACE offline GT yes/no, DC online GT yes/no, ACE online GT yes/no using the existing provisional task. GPT-5 and supervised ACE remain outside these queues; ICL/MIPROv2/GEPA are not implemented for the provisional corpora.

GT yes on CaChe/ParlaMint means unverified model pseudo-labels (†), never human GT. Their human-GT Acc is N/A; reference agreement is separately named. Conformability is a reference-blind same-family LLM grounding judgment, not human verification. Unresolved judgments remain unknown. Offline test labels never feed adaptation; online feedback follows the current prediction.

A 2-hour deadline stops a corpus gracefully and proceeds to the next. Incomplete rows remain incomplete; the deadline does not guarantee all rows finish. A resumed corpus retains its original deadline.

## Dreaddit

Test N=24. Queue: queued; — / — 0/24.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |
| icl | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |
| miprov2 | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |
| gepa | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |
| dc_gt | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |
| dc_no_gt | — | — | — | — | — | queued; predicted 0/24; judged 0/24; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/dreaddit/METRICS.md>).

## GoEmotions

Test N=128. Queue: running; icl / prediction 75/128.

Wall-time deadline: 11:20:34 KST.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | 24.22 | — | 33.95 | 23.23 | — | complete; predicted 128/128; judged 0/128; unresolved 0 |
| icl | — | — | — | — | — | running; predicted 76/128; judged 0/128; unresolved 0 |
| miprov2 | — | — | — | — | — | queued; predicted 0/128; judged 0/128; unresolved 0 |
| gepa | — | — | — | — | — | queued; predicted 0/128; judged 0/128; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/goemotions/METRICS.md>).

## CaChe

Test N=8. Queue: queued; — / — 0/8.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_offline_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_offline_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| dc_online_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| dc_online_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_online_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_online_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/cache/METRICS.md>).

## ParlaMint-GB

Test N=8. Queue: queued; — / — 0/8.

| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_offline_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_offline_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| dc_online_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| dc_online_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_online_no_gt | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |
| ace_online_ref | N/A | — | — | — | — | queued; predicted 0/8; judged 0/8; unresolved 0 |

[Run details](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/parlamint_gb/METRICS.md>).

## Preserved earlier runs

Earlier full-test scores use different denominators and protocols. They remain in their original directories and must not be compared as the same run.

- [Dreaddit](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/dreaddit_icl/comparison_run_20260912/METRICS.md>)
- [GoEmotions](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/goemotions_offline/run_20260912/METRICS.md>)
- [Paired corpora](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/paired_feedback/run_20260912/METRICS.md>)
