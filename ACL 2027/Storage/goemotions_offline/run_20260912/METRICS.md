# GoEmotions offline comparison

Local diagnostic. Official test N = 5,427. ACC is exact label-set match. F1 is reported separately.
Conformability is a local Qwen-judged evidence-grounding pass rate, not human verification.

| Method | GT | Acc % ↑ | Micro-F1 % ↑ | Macro-F1 % ↑ | Conformability % ↑ | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Qwen3-8B | — | 25.63 | 37.06 | 30.30 | — | complete; predictions 5427/5427; judged 0/5427 |
| ICL | ✓ | 20.66 | 33.19 | 24.94 | — | complete; predictions 5427/5427; judged 0/5427 |
| MIPROv2 | ✓ | — | — | — | — | paused; predictions 0/5427; judged 0/5427 |
| GEPA | ✓ | — | — | — | — | queued; predictions 0/5427; judged 0/5427 |

All adaptation uses training/development labels only. Test outputs never update prompts.
Invalid outputs count as incorrect exact matches. Their F1 predictions are empty sets.
The original splits are preserved; disjoint comment IDs do not guarantee disjoint authors or identical-text exclusion.
This transfers official DSPy optimizers to a new classification task. It is not an exact reproduction of the finance results.
GPT-5 and ACE are not included in this local queue.
