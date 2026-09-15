# Qwen3-8B offline GEPA stage

Updated UTC: 2026-09-15 05:25:47. Valid predictions 600/600. Judgments pending.

Pinned DSPy GEPA over the frozen train and development splits of the two corpora that carry validated label GT, with a 3,000-metric-call budget and reflection minibatch 3. GEPA searches with its native per-item scores and label feedback. The final program is selected among GEPA candidates by the full-development corpus F1 objective, computed from recorded development predictions without additional calls, then frozen and hashed before evaluation begins. CaChe and ParlaMint-GB have no validated label GT and are outside this stage.

| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Candidates** | **Metric calls** | **Selected / GEPA best** | **Dev objective %** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| dreaddit | offline | gepa | yes | 42 | 100/100 | 20 | 3002 | 10 / 10 | 84.96 | 76.00 | 76.00 | 75.99 | PENDING | 252.4 | prediction_complete |
| dreaddit | offline | gepa | yes | 43 | 100/100 | 17 | 3005 | 11 / 11 | 79.93 | 79.00 | 79.00 | 79.00 | PENDING | 261.7 | prediction_complete |
| dreaddit | offline | gepa | yes | 44 | 100/100 | 20 | 3002 | 10 / 3 | 78.95 | 80.00 | 80.00 | 79.99 | PENDING | 264.1 | prediction_complete |
| goemotions | offline | gepa | yes | 42 | 100/100 | 27 | 3102 | 7 / 0 | 32.31 | 15.00 | 20.25 | 11.12 | PENDING | 209.7 | prediction_complete |
| goemotions | offline | gepa | yes | 43 | 100/100 | 25 | 3004 | 24 / 24 | 32.98 | 20.00 | 34.88 | 11.39 | PENDING | 232.2 | prediction_complete |
| goemotions | offline | gepa | yes | 44 | 100/100 | 26 | 3062 | 15 / 15 | 31.91 | 16.00 | 22.05 | 10.22 | PENDING | 215.1 | prediction_complete |

GT is optimization feedback. Train and development labels are read during candidate search only, and the frozen program is hashed before the first evaluation input is read. Invalid/failed rows are not completed experiment rows.

Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. The development objective is macro-F1 for Dreaddit and micro-F1 for GoEmotions, computed over the complete development split. Conformability awaits judging. Quote matching is a separate mechanical metric.

Selected / GEPA best compares the candidate chosen by the corpus objective with the candidate GEPA ranks first by mean per-item score. Metric calls include initialization, minibatch and full-development evaluations. A candidate exceeding the shared 4096-token learned-context budget produces invalid outputs without model calls.
