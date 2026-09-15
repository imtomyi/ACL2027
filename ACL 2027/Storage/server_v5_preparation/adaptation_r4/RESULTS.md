# Qwen3-8B ACE/DC adaptation stage

Updated UTC: 2026-09-14 10:12:13. Valid predictions 1720/1800. Judgments pending.

18 DC seed runs. The existing r3 ACE trajectories continue separately. Base/ICL is a separate preserved stage; MIPROv2/GEPA remain pending. No historical scores are imported.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Updates** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| cache | online | dc_cu | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 36.7 | prediction_complete |
| dreaddit | online | dc_cu | no | 42 | 100/100 | 100/100 | 62.00 | 62.00 | 58.24 | PENDING | 18.1 | prediction_complete |
| goemotions | online | dc_cu | no | 42 | 100/100 | 100/100 | 8.00 | 18.32 | 6.51 | PENDING | 40.4 | prediction_complete |
| parlamint_gb | online | dc_cu | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 51.7 | prediction_complete |
| dreaddit | online | dc_cu | yes | 42 | 100/100 | 100/100 | 64.00 | 64.00 | 60.94 | PENDING | 19.4 | prediction_complete |
| goemotions | online | dc_cu | yes | 42 | 100/100 | 100/100 | 15.00 | 21.95 | 6.29 | PENDING | 36.5 | prediction_complete |
| cache | online | dc_cu | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 42.7 | prediction_complete |
| dreaddit | online | dc_cu | no | 43 | 100/100 | 100/100 | 64.00 | 64.00 | 61.39 | PENDING | 18.7 | prediction_complete |
| goemotions | online | dc_cu | no | 43 | 100/100 | 100/100 | 19.00 | 27.62 | 6.54 | PENDING | 43.8 | prediction_complete |
| parlamint_gb | online | dc_cu | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 26.6 | prediction_complete |
| dreaddit | online | dc_cu | yes | 43 | 100/100 | 100/100 | 63.00 | 63.00 | 59.60 | PENDING | 19.2 | prediction_complete |
| goemotions | online | dc_cu | yes | 43 | 100/100 | 100/100 | 4.00 | 14.39 | 4.29 | PENDING | 55.7 | prediction_complete |
| cache | online | dc_cu | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 29.0 | prediction_complete |
| dreaddit | online | dc_cu | no | 44 | 100/100 | 100/100 | 61.00 | 61.00 | 56.85 | PENDING | 18.9 | prediction_complete |
| goemotions | online | dc_cu | no | 44 | 100/100 | 100/100 | 14.00 | 21.05 | 6.19 | PENDING | 34.7 | prediction_complete |
| parlamint_gb | online | dc_cu | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 43.3 | prediction_complete |
| dreaddit | online | dc_cu | yes | 44 | 100/100 | 100/100 | 64.00 | 64.00 | 60.94 | PENDING | 18.1 | prediction_complete |
| goemotions | online | dc_cu | yes | 44 | 20/100 | 19/100 | — | — | — | PENDING | 13.3 | failed |

GT is adaptation feedback. Online GT is revealed only after the current prediction is committed. Offline updates use train only; the final playbook is frozen before evaluation. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. CaChe/ParlaMint have no validated label GT. Conformability awaits judge selection. Quote matching is a separate mechanical metric.

Complete oversized memory proposals are rejected with the prior state retained. Malformed or exhausted adaptive responses stop their condition. The 4096-token memory cap and common role caps match the Base/ICL runtime.
