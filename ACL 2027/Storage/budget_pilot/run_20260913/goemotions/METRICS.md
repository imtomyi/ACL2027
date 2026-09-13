# goemotions reduced budget pilot

Reduced diagnostic: test N=128, train=32, dev=32. ACC is exact label-set match. No full-test scores are reused.
Conformability is a local Qwen-judged evidence-grounding pass rate, not human verification.

| Method | GT | Acc % ↑ | Micro-F1 % ↑ | Macro-F1 % ↑ | Conformability % ↑ | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Qwen3-8B | — | 24.22 | 33.95 | 23.23 | — | complete; predictions 128/128; judged 0/128 |
| ICL | ✓ | — | — | — | — | running; predictions 77/128; judged 0/128 |
| MIPROv2 | ✓ | — | — | — | — | queued; predictions 0/128; judged 0/128 |
| GEPA | ✓ | — | — | — | — | queued; predictions 0/128; judged 0/128 |

Offline adaptation uses training/development labels only. DC online receives current-label feedback only after prediction, affecting subsequent examples.
Invalid outputs count as incorrect exact matches. Their F1 predictions are empty sets.
The original splits are preserved; disjoint comment IDs do not guarantee disjoint authors or identical-text exclusion.
This transfers official DSPy optimizers to a new classification task. It is not an exact reproduction of the finance results.
GPT-5 and ACE are not included in this local queue.
