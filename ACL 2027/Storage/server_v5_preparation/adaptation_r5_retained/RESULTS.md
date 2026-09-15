# Qwen3-8B ACE/DC adaptation stage

Updated UTC: 2026-09-14 10:41:03. Valid predictions 300/300. Judgments pending.

DC retained-update variant for GoEmotions GT-yes, three seeds. Successful predecessor trajectories and the failed seed44 prefix are imported byte-for-byte under an explicit compatibility audit. Verified unusable curator responses retain prior memory; this differs from fail-stop DC. Other conditions remain separate.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Updates** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| goemotions | online | dc_cu | yes | 42 | 100/100 | 100/100 | 15.00 | 21.95 | 6.29 | PENDING | 36.5 | prediction_complete |
| goemotions | online | dc_cu | yes | 43 | 100/100 | 100/100 | 4.00 | 14.39 | 4.29 | PENDING | 55.7 | prediction_complete |
| goemotions | online | dc_cu | yes | 44 | 100/100 | 100/100 | 10.00 | 22.47 | 7.64 | PENDING | 42.0 | prediction_complete |

GT is adaptation feedback. Online GT is revealed only after the current prediction is committed. Offline updates use train only; the final playbook is frozen before evaluation. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. CaChe/ParlaMint have no validated label GT. Conformability awaits judge selection. Quote matching is a separate mechanical metric.

Complete oversized memory proposals are rejected with the prior state retained. Malformed or exhausted adaptive responses stop their condition. The 4096-token memory cap and common role caps match the Base/ICL runtime.
