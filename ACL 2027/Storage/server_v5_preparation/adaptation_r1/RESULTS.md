# Qwen3-8B ACE/DC adaptation stage

Updated UTC: 2026-09-14 05:02:56. Valid predictions 271/5400. Judgments pending.

54 ACE/DC seed runs. Base/ICL is a separate preserved stage; MIPROv2/GEPA remain pending. No historical scores are imported.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Updates** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| cache | online | ace | no | 42 | 24/100 | 24/100 | N/A | — | — | PENDING | 6.8 | failed |
| dreaddit | online | ace | no | 42 | 57/100 | 57/100 | — | — | — | PENDING | 17.7 | paused |
| goemotions | online | ace | no | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | online | ace | no | 42 | 5/100 | 5/100 | N/A | — | — | PENDING | 1.6 | failed |
| dreaddit | online | ace | yes | 42 | 58/100 | 58/100 | — | — | — | PENDING | 17.8 | paused |
| goemotions | online | ace | yes | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| cache | online | dc_cu | no | 42 | 21/100 | 20/100 | N/A | — | — | PENDING | 19.7 | failed |
| dreaddit | online | dc_cu | no | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | no | 42 | 32/100 | 32/100 | — | — | — | PENDING | 17.7 | paused |
| parlamint_gb | online | dc_cu | no | 42 | 18/100 | 17/100 | N/A | — | — | PENDING | 10.4 | failed |
| dreaddit | online | dc_cu | yes | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | yes | 42 | 28/100 | 28/100 | — | — | — | PENDING | 17.9 | paused |
| cache | offline | ace | no | 42 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| dreaddit | offline | ace | no | 42 | 0/100 | 50/100 | — | — | — | PENDING | 16.0 | paused |
| goemotions | offline | ace | no | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | offline | ace | no | 42 | 0/100 | 3/100 | N/A | — | — | PENDING | 1.1 | failed |
| dreaddit | offline | ace | yes | 42 | 0/100 | 33/100 | — | — | — | PENDING | 9.5 | paused |
| goemotions | offline | ace | yes | 42 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| cache | online | ace | no | 43 | 20/100 | 20/100 | N/A | — | — | PENDING | 5.2 | failed |
| dreaddit | online | ace | no | 43 | 8/100 | 8/100 | — | — | — | PENDING | 1.9 | paused |
| goemotions | online | ace | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | online | ace | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | ace | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | ace | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| cache | online | dc_cu | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| parlamint_gb | online | dc_cu | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| cache | offline | ace | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| dreaddit | offline | ace | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | offline | ace | no | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | offline | ace | no | 43 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | offline | ace | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | offline | ace | yes | 43 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| cache | online | ace | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | ace | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | ace | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | online | ace | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | ace | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | online | ace | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| cache | online | dc_cu | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| parlamint_gb | online | dc_cu | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | online | dc_cu | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| goemotions | online | dc_cu | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| cache | offline | ace | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| dreaddit | offline | ace | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | offline | ace | no | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |
| parlamint_gb | offline | ace | no | 44 | 0/100 | 0/100 | N/A | — | — | PENDING | 0.0 | queued |
| dreaddit | offline | ace | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | queued |
| goemotions | offline | ace | yes | 44 | 0/100 | 0/100 | — | — | — | PENDING | 0.0 | withheld_failed_development_probe |

GT is adaptation feedback. Online GT is revealed only after the current prediction is committed. Offline updates use train only; the final playbook is frozen before evaluation. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. CaChe/ParlaMint have no validated label GT. Conformability awaits judge selection. Quote matching is a separate mechanical metric.

Complete oversized memory proposals are rejected with the prior state retained. Malformed or exhausted adaptive responses stop their condition. The 4096-token memory cap and common role caps match the Base/ICL runtime.
