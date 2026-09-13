# Dreaddit: Accuracy and Conformability

Conformability is a blinded local Qwen-judged evidence-grounding pass rate, not independently verified correctness.

| Method | GT | Acc ↑ (%) | Conformability ↑ (%) | Progress |
| --- | --- | ---: | ---: | --- |
| GPT-5 | — | — | — | API setup pending |
| Qwen3-8B | — | 76.69 | — | predictions 712/712; judged 588/712; unresolved 0 |
| ICL ✓ | ✓ | 51.40 | — | predictions 712/712; judged 0/712; unresolved 0 |
| MIPROv2 ✓ | ✓ | 78.09 | — | predictions 712/712; judged 0/712; unresolved 0 |
| GEPA ✓ | ✓ | 78.65 | — | predictions 712/712; judged 0/712; unresolved 0 |
| DC (CU) ✓ | ✓ | — | — | predictions 97/712; judged 0/712; unresolved 0 |
| DC (CU) ✗ | ✗ | — | — | predictions 0/712; judged 0/712; unresolved 0 |

Both final percentages require all 712 items. Unresolved judgments are not converted to false or excluded silently.
Secondary audit is performed after prediction/adaptation finishes, with no audit feedback to training or memory.
Same-family judging may favor Qwen outputs. This adapted classification rubric is not identical to the prior thematic-review instrument.
