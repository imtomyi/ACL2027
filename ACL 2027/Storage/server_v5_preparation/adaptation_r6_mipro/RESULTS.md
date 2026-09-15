# Qwen3-8B offline MIPROv2 stage

Updated UTC: 2026-09-14 14:07:59. Valid predictions 600/600. Judgments pending.

Pinned DSPy MIPROv2 over the frozen train and development splits of the two corpora that carry validated label GT. Candidates are selected by a full-development corpus F1 objective rather than mean per-item accuracy. The selected program is frozen and hashed before evaluation begins. CaChe and ParlaMint-GB have no validated label GT and are outside this stage.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Demos** | **Dev evals** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| dreaddit | offline | miprov2 | yes | 42 | 100/100 | 4 | 26 | 71.00 | 71.00 | 69.91 | PENDING | 169.6 | prediction_complete |
| goemotions | offline | miprov2 | yes | 42 | 100/100 | 4 | 31 | 28.00 | 35.54 | 7.75 | PENDING | 120.1 | prediction_complete |
| dreaddit | offline | miprov2 | yes | 43 | 100/100 | 4 | 29 | 74.00 | 74.00 | 73.32 | PENDING | 149.4 | prediction_complete |
| goemotions | offline | miprov2 | yes | 43 | 100/100 | 4 | 30 | 30.00 | 36.75 | 9.79 | PENDING | 119.4 | prediction_complete |
| dreaddit | offline | miprov2 | yes | 44 | 100/100 | 0 | 27 | 65.00 | 65.00 | 62.67 | PENDING | 160.4 | prediction_complete |
| goemotions | offline | miprov2 | yes | 44 | 100/100 | 4 | 28 | 21.00 | 30.77 | 7.75 | PENDING | 112.7 | prediction_complete |

GT is optimization feedback. Train and development labels are read during candidate search only, and the frozen program is hashed before the first evaluation input is read. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. The development objective is macro-F1 for Dreaddit and micro-F1 for GoEmotions, computed over the complete development split. Conformability awaits judge selection. Quote matching is a separate mechanical metric.

Demos counts the demonstrations carried by the selected program. Dev evals counts completed full-development evaluations. A candidate exceeding eight demonstrations or the shared 4096-token learned-context budget is rejected without model calls.
