# Qwen3-8B server prediction stage

Updated UTC: 2026-09-14 04:23:17. Predicted 1738/1800 for this stage. Full planned panel: 84 runs / 8400 predictions. Judgments: pending.

This is the first sealed prediction stage, not the completed v5 comparison. Four Base and two ICL conditions, seeds 42/43/44. Other method adapters remain pending validation. Historical scores are not imported.

| **Dataset** | **Method** | **Seed** | **Predicted** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| dreaddit | base | 42 | 100/100 | 70.00 | 70.00 | 68.47 | PENDING | 10.1 | prediction_complete |
| goemotions | base | 42 | 100/100 | 18.00 | 28.93 | 8.22 | PENDING | 5.7 | prediction_complete |
| cache | base | 42 | 94/100 | N/A | — | — | PENDING | 6.4 | prediction_complete_with_failures |
| parlamint_gb | base | 42 | 85/100 | N/A | — | — | PENDING | 11.9 | prediction_complete_with_failures |
| dreaddit | icl | 42 | 99/100 | 66.00 | — | — | PENDING | 10.3 | prediction_complete_with_failures |
| goemotions | icl | 42 | 100/100 | 2.00 | 14.15 | 5.11 | PENDING | 5.8 | prediction_complete |
| dreaddit | base | 43 | 97/100 | 66.00 | — | — | PENDING | 10.1 | prediction_complete_with_failures |
| goemotions | base | 43 | 100/100 | 18.00 | 28.84 | 8.33 | PENDING | 5.8 | prediction_complete |
| cache | base | 43 | 95/100 | N/A | — | — | PENDING | 5.8 | prediction_complete_with_failures |
| parlamint_gb | base | 43 | 86/100 | N/A | — | — | PENDING | 10.9 | prediction_complete_with_failures |
| dreaddit | icl | 43 | 100/100 | 67.00 | 67.00 | 64.80 | PENDING | 10.8 | prediction_complete |
| goemotions | icl | 43 | 100/100 | 1.00 | 11.94 | 8.30 | PENDING | 5.8 | prediction_complete |
| dreaddit | base | 44 | 100/100 | 70.00 | 70.00 | 68.47 | PENDING | 7.9 | prediction_complete |
| goemotions | base | 44 | 100/100 | 15.00 | 28.66 | 8.31 | PENDING | 5.9 | prediction_complete |
| cache | base | 44 | 95/100 | N/A | — | — | PENDING | 5.9 | prediction_complete_with_failures |
| parlamint_gb | base | 44 | 87/100 | N/A | — | — | PENDING | 7.7 | prediction_complete_with_failures |
| dreaddit | icl | 44 | 100/100 | 66.00 | 66.00 | 63.53 | PENDING | 7.3 | prediction_complete |
| goemotions | icl | 44 | 100/100 | 8.00 | 15.53 | 6.86 | PENDING | 4.7 | prediction_complete |

Dreaddit accuracy is binary exact-label accuracy. GoEmotions accuracy is exact-set accuracy over the fixed 28 labels; official neutral co-labels remain valid. CaChe/ParlaMint have no validated label GT.

Raw reported evidence offsets remain saved and are scored separately. Literal anchors use exact Unicode substring matching only, with no fuzzy text repair. A unique match or valid model offset resolves a location; otherwise location remains unresolved.

Task scores finalize independently of judging. A prediction-complete row is not a fully judged experiment. See metrics.json for per-label metrics and diagnostic denominators. Other registered metrics remain pending or conditional.
