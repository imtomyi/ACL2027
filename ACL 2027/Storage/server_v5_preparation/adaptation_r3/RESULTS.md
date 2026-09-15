# Qwen3-8B ACE/DC adaptation stage

Updated UTC: 2026-09-14 09:22:01. Valid predictions 3610/5400. Judgments pending.

54 ACE/DC seed runs. Base/ICL is a separate preserved stage; MIPROv2/GEPA remain pending. No historical scores are imported.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Updates** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| cache | online | ace | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 30.2 | prediction_complete |
| dreaddit | online | ace | no | 42 | 100/100 | 100/100 | 72.00 | 72.00 | 71.06 | PENDING | 33.3 | prediction_complete |
| goemotions | online | ace | no | 42 | 100/100 | 100/100 | 13.00 | 17.10 | 10.58 | PENDING | 33.4 | prediction_complete |
| parlamint_gb | online | ace | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 36.5 | prediction_complete |
| dreaddit | online | ace | yes | 42 | 100/100 | 100/100 | 77.00 | 77.00 | 76.81 | PENDING | 33.5 | prediction_complete |
| goemotions | online | ace | yes | 42 | 100/100 | 100/100 | 17.00 | 25.91 | 12.53 | PENDING | 32.8 | prediction_complete |
| cache | online | dc_cu | no | 42 | 8/100 | 8/100 | N/A | — | — | PENDING | 1.6 | running |
| dreaddit | online | dc_cu | no | 42 | 2/100 | 2/100 | — | — | — | PENDING | 0.4 | running |
| goemotions | online | dc_cu | no | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| parlamint_gb | online | dc_cu | no | 42 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | yes | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | dc_cu | yes | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| cache | offline | ace | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 39.8 | prediction_complete |
| dreaddit | offline | ace | no | 42 | 100/100 | 100/100 | 78.00 | 78.00 | 77.56 | PENDING | 43.7 | prediction_complete |
| goemotions | offline | ace | no | 42 | 100/100 | 100/100 | 14.00 | 28.91 | 16.40 | PENDING | 41.7 | prediction_complete |
| parlamint_gb | offline | ace | no | 42 | 100/100 | 100/100 | N/A | — | — | PENDING | 47.9 | prediction_complete |
| dreaddit | offline | ace | yes | 42 | 100/100 | 100/100 | 78.00 | 78.00 | 77.68 | PENDING | 44.4 | prediction_complete |
| goemotions | offline | ace | yes | 42 | 100/100 | 100/100 | 20.00 | 29.15 | 13.88 | PENDING | 41.5 | prediction_complete |
| cache | online | ace | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 30.7 | prediction_complete |
| dreaddit | online | ace | no | 43 | 100/100 | 100/100 | 73.00 | 73.00 | 72.20 | PENDING | 34.4 | prediction_complete |
| goemotions | online | ace | no | 43 | 100/100 | 100/100 | 8.00 | 16.48 | 9.06 | PENDING | 34.3 | prediction_complete |
| parlamint_gb | online | ace | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 35.9 | prediction_complete |
| dreaddit | online | ace | yes | 43 | 100/100 | 100/100 | 82.00 | 82.00 | 81.97 | PENDING | 35.1 | prediction_complete |
| goemotions | online | ace | yes | 43 | 100/100 | 100/100 | 21.00 | 29.57 | 12.40 | PENDING | 33.0 | prediction_complete |
| cache | online | dc_cu | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | dc_cu | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| parlamint_gb | online | dc_cu | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | dc_cu | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| cache | offline | ace | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 36.1 | prediction_complete |
| dreaddit | offline | ace | no | 43 | 100/100 | 100/100 | 81.00 | 81.00 | 80.91 | PENDING | 43.7 | prediction_complete |
| goemotions | offline | ace | no | 43 | 100/100 | 100/100 | 16.00 | 33.33 | 12.22 | PENDING | 43.2 | prediction_complete |
| parlamint_gb | offline | ace | no | 43 | 100/100 | 100/100 | N/A | — | — | PENDING | 48.4 | prediction_complete |
| dreaddit | offline | ace | yes | 43 | 100/100 | 100/100 | 78.00 | 78.00 | 76.40 | PENDING | 44.2 | prediction_complete |
| goemotions | offline | ace | yes | 43 | 100/100 | 100/100 | 22.00 | 31.80 | 13.93 | PENDING | 43.8 | prediction_complete |
| cache | online | ace | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 34.5 | prediction_complete |
| dreaddit | online | ace | no | 44 | 100/100 | 100/100 | 82.00 | 82.00 | 81.93 | PENDING | 33.3 | prediction_complete |
| goemotions | online | ace | no | 44 | 100/100 | 100/100 | 14.00 | 30.22 | 13.16 | PENDING | 34.6 | prediction_complete |
| parlamint_gb | online | ace | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 34.8 | prediction_complete |
| dreaddit | online | ace | yes | 44 | 100/100 | 100/100 | 81.00 | 81.00 | 80.98 | PENDING | 35.5 | prediction_complete |
| goemotions | online | ace | yes | 44 | 100/100 | 100/100 | 19.00 | 27.98 | 11.61 | PENDING | 33.4 | prediction_complete |
| cache | online | dc_cu | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | dc_cu | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| parlamint_gb | online | dc_cu | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | dc_cu | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| cache | offline | ace | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 32.3 | prediction_complete |
| dreaddit | offline | ace | no | 44 | 100/100 | 100/100 | 69.00 | 69.00 | 67.27 | PENDING | 35.0 | prediction_complete |
| goemotions | offline | ace | no | 44 | 100/100 | 100/100 | 14.00 | 21.86 | 8.55 | PENDING | 33.3 | prediction_complete |
| parlamint_gb | offline | ace | no | 44 | 100/100 | 100/100 | N/A | — | — | PENDING | 35.1 | prediction_complete |
| dreaddit | offline | ace | yes | 44 | 100/100 | 100/100 | 83.00 | 83.00 | 82.61 | PENDING | 32.6 | prediction_complete |
| goemotions | offline | ace | yes | 44 | 100/100 | 100/100 | 14.00 | 24.27 | 12.98 | PENDING | 30.0 | prediction_complete |

GT is adaptation feedback. Online GT is revealed only after the current prediction is committed. Offline updates use train only; the final playbook is frozen before evaluation. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. CaChe/ParlaMint have no validated label GT. Conformability awaits judge selection. Quote matching is a separate mechanical metric.

Complete oversized memory proposals are rejected with the prior state retained. Malformed or exhausted adaptive responses stop their condition. The 4096-token memory cap and common role caps match the Base/ICL runtime.
