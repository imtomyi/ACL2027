# Experiment results and live progress

Updated: **2026-09-14T01:23:22.782289+00:00**. **27/30 execution complete; 27/30 audited complete.**

The 12 completed ACE rows are preserved. This report tracks the original 30-row comparison matrix and separately versioned recovery results. New percentages are provisional until their final audit passes. Each online target is 100; reduced offline targets are shown per row.

Planning ETA: Stopped at the user-requested cell boundary. All three captured cells completed100/100 predictions, updates and judgments; owned GPU services are off. No automatic resume. Remaining ETA: not applicable until a user resume request. Stage estimates exclude later work.

| **Dataset** | **Phase** | **Method / feedback** | **Status** | **Predictions** | **Judgments** | **Human accuracy** | **Model-reference agreement** | **Conformability** |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Dreaddit | offline | Base | Audited complete | 24/24 | 24/24 | 54.2% | N/A | 100.0% |
| Dreaddit | offline | ICL | Audited complete | 24/24 | 24/24 | 66.7% | N/A | 100.0% |
| Dreaddit | offline | MIPROv2 | Audited complete | 24/24 | 24/24 | 54.2% | N/A | 100.0% |
| Dreaddit | offline | GEPA | Audited complete | 24/24 | 24/24 | 66.7% | N/A | 100.0% |
| Dreaddit | online | DC / reference | failed | 24/100 | 0/100 | — | N/A | — |
| Dreaddit | online | DC / no feedback | Audited complete | 100/100 | 100/100 | 80.0% | N/A | 99.0% |
| Dreaddit | online | ACE / reference | Audited complete | 100/100 | 100/100 | 79.0% | N/A | 93.0% |
| Dreaddit | online | ACE / no feedback | Audited complete | 100/100 | 100/100 | 67.0% | N/A | 99.0% |
| GoEmotions | offline | Base | Audited complete | 128/128 | 128/128 | 24.2% | N/A | 100.0% |
| GoEmotions | offline | ICL | Audited complete | 128/128 | 128/128 | 18.8% | N/A | 98.4% |
| GoEmotions | offline | MIPROv2 | Audited complete | 128/128 | 128/128 | 19.5% | N/A | 99.2% |
| GoEmotions | offline | GEPA | Audited complete | 128/128 | 128/128 | 21.9% | N/A | 100.0% |
| GoEmotions | online | DC / reference | failed | 16/100 | 0/100 | — | N/A | — |
| GoEmotions | online | DC / no feedback | failed | 13/100 | 0/100 | — | N/A | — |
| GoEmotions | online | ACE / reference | Audited complete | 100/100 | 100/100 | 29.0% | N/A | 99.0% |
| GoEmotions | online | ACE / no feedback | Audited complete | 100/100 | 100/100 | 32.0% | N/A | 100.0% |
| CaChe | offline | Base | Audited complete | 8/8 | 8/8 | N/A | 50.0% | 100.0% |
| CaChe | offline | ACE / reference | Audited complete | 8/8 | 8/8 | N/A | 37.5% | 100.0% |
| CaChe | offline | ACE / no feedback | Audited complete | 8/8 | 8/8 | N/A | 75.0% | 100.0% |
| CaChe | online | DC / reference | Audited complete | 100/100 | 100/100 | N/A | 60.0% | 97.0% |
| CaChe | online | DC / no feedback | Audited complete | 100/100 | 100/100 | N/A | 66.0% | 97.0% |
| CaChe | online | ACE / reference | Audited complete | 100/100 | 100/100 | N/A | 66.0% | 100.0% |
| CaChe | online | ACE / no feedback | Audited complete | 100/100 | 100/100 | N/A | 59.0% | 100.0% |
| ParlaMint-GB | offline | Base | Audited complete | 8/8 | 8/8 | N/A | 62.5% | 100.0% |
| ParlaMint-GB | offline | ACE / reference | Audited complete | 8/8 | 8/8 | N/A | 37.5% | 100.0% |
| ParlaMint-GB | offline | ACE / no feedback | Audited complete | 8/8 | 8/8 | N/A | 12.5% | 100.0% |
| ParlaMint-GB | online | DC / reference | Audited complete | 100/100 | 100/100 | N/A | 41.0% | 94.0% |
| ParlaMint-GB | online | DC / no feedback | Audited complete | 100/100 | 100/100 | N/A | 38.0% | 93.0% |
| ParlaMint-GB | online | ACE / reference | Audited complete | 100/100 | 100/100 | N/A | 36.0% | 100.0% |
| ParlaMint-GB | online | ACE / no feedback | Audited complete | 100/100 | 100/100 | N/A | 34.0% | 100.0% |

**Stop request:** Stopped; checkpoints preserved.


## Fresh DC recovery: curator limit 8,192

**2/8 execution complete; 2/8 audited complete.**
Queue status: paused.

This separate eight-cell block changes only the DC curator output limit from 4,096 to 8,192 tokens. All streams start from empty memory with fresh outputs and caches. The original outcomes above remain recorded separately. Generator limit 2,048, prompts, model, seed, frozen samples and reference banks are unchanged.

| **Dataset** | **Method / feedback** | **Status** | **Predictions** | **Updates** | **Judgments** | **Human accuracy** | **Model-reference agreement** | **Conformability** |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dreaddit | DC / reference | failed | 24/100 | 23/100 | 0/100 | — | N/A | — |
| Dreaddit | DC / no feedback | queued | 0/100 | 0/100 | 0/100 | — | N/A | — |
| GoEmotions | DC / reference | failed | 16/100 | 15/100 | 0/100 | — | N/A | — |
| GoEmotions | DC / no feedback | queued | 0/100 | 0/100 | 0/100 | — | N/A | — |
| CaChe | DC / reference | Audited complete | 100/100 | 100/100 | 100/100 | N/A | 60.0% | 97.0% |
| CaChe | DC / no feedback | queued | 0/100 | 0/100 | 0/100 | N/A | — | — |
| ParlaMint-GB | DC / reference | Audited complete | 100/100 | 100/100 | 100/100 | N/A | 41.0% | 94.0% |
| ParlaMint-GB | DC / no feedback | queued | 0/100 | 0/100 | 0/100 | N/A | — | — |

| **Dataset** | **Phase** | **Method / feedback** | **Micro-F1** | **Macro-F1** | **Invalid** | **Judge pass / fail / unresolved** |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Dreaddit | offline | Base | 0.5417 | 0.4198 | 0 | 24 / 0 / 0 |
| Dreaddit | offline | ICL | 0.6667 | 0.6250 | 0 | 24 / 0 / 0 |
| Dreaddit | offline | MIPROv2 | 0.5417 | 0.4667 | 0 | 24 / 0 / 0 |
| Dreaddit | offline | GEPA | 0.6667 | 0.6250 | 0 | 24 / 0 / 0 |
| Dreaddit | online | DC / no feedback | 0.8000 | 0.7971 | 0 | 99 / 1 / 0 |
| Dreaddit | online | ACE / reference | 0.7900 | 0.7883 | 0 | 93 / 7 / 0 |
| Dreaddit | online | ACE / no feedback | 0.6700 | 0.6480 | 0 | 99 / 1 / 0 |
| GoEmotions | offline | Base | 0.3446 | 0.2333 | 0 | 128 / 0 / 0 |
| GoEmotions | offline | ICL | 0.2947 | 0.2621 | 0 | 126 / 2 / 0 |
| GoEmotions | offline | MIPROv2 | 0.2829 | 0.2057 | 0 | 127 / 1 / 0 |
| GoEmotions | offline | GEPA | 0.2750 | 0.2425 | 0 | 128 / 0 / 0 |
| GoEmotions | online | ACE / reference | 0.3866 | 0.2301 | 0 | 99 / 1 / 0 |
| GoEmotions | online | ACE / no feedback | 0.3852 | 0.2491 | 0 | 100 / 0 / 0 |
| CaChe | offline | Base | N/A | N/A | 0 | 8 / 0 / 0 |
| CaChe | offline | ACE / reference | N/A | N/A | 0 | 8 / 0 / 0 |
| CaChe | offline | ACE / no feedback | N/A | N/A | 0 | 8 / 0 / 0 |
| CaChe | online | DC / reference | N/A | N/A | 2 | 97 / 3 / 0 |
| CaChe | online | DC / no feedback | N/A | N/A | 0 | 97 / 3 / 0 |
| CaChe | online | ACE / reference | N/A | N/A | 0 | 100 / 0 / 0 |
| CaChe | online | ACE / no feedback | N/A | N/A | 1 | 100 / 0 / 0 |
| ParlaMint-GB | offline | Base | N/A | N/A | 0 | 8 / 0 / 0 |
| ParlaMint-GB | offline | ACE / reference | N/A | N/A | 0 | 8 / 0 / 0 |
| ParlaMint-GB | offline | ACE / no feedback | N/A | N/A | 0 | 8 / 0 / 0 |
| ParlaMint-GB | online | DC / reference | N/A | N/A | 0 | 94 / 6 / 0 |
| ParlaMint-GB | online | DC / no feedback | N/A | N/A | 0 | 93 / 7 / 0 |
| ParlaMint-GB | online | ACE / reference | N/A | N/A | 1 | 100 / 0 / 0 |
| ParlaMint-GB | online | ACE / no feedback | N/A | N/A | 0 | 100 / 0 / 0 |

F1 values use the 0–1 scale and appear after independent result verification. CaChe and ParlaMint agreement uses sealed, unverified model annotations. It is not human accuracy. Conformability is a same-family model judgment, not human validation. Invalid predictions remain in denominators.

Qwen3-8B Q4_K_M through Ollama 0.33.3; frozen real-corpus selections. DC retains generator 2,048 and curator 4,096. Offline supervised methods retain the frozen reduced optimizer settings. Topic comparisons reuse the exact reference banks of the selected ACE versions. Original ACE generator/reference differences remain recorded in the preserved ACE final summary.

MIATA: use all available GPUs for independent work, preserve sequential adaptation, retain checkpoints and provenance, and leave shared services and other users untouched. The separate 30-minute Codex monitor remains paused.
