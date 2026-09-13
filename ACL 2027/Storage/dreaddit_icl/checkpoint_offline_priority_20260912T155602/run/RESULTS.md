# Dreaddit comparison

Local diagnostic. Qwen3-8B Q4_K_M, thinking off. Accuracy is shown only for completed runs.

| Method | GT labels | Dreaddit Acc ↑ | Status |
| --- | --- | ---: | --- |
| GPT-5 | — | — | Awaiting API setup; no cloud requests made |
| Qwen3-8B | — | 76.69 | complete (712/712) |
| ICL ✓ | ✓ | 51.40 | complete (712/712) |
| MIPROv2 ✓ | ✓ | 78.09 | complete (712/712) |
| GEPA ✓ | ✓ | 78.65 | complete (712/712) |
| DC (CU) ✓ | ✓ | — | paused (97/712) |
| DC (CU) ✗ | ✗ | — | queued (0/712) |

ACE and other corpora are outside this run. Split: train 2249 / validation 555 / test 712.
GT-no DC receives no target labels or correctness feedback. Online scoring uses the prediction before memory update.
Implementation details and departures from the paper are recorded in the adjacent frozen configuration.
