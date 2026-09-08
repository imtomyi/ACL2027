# Local Comparison Experiment Log

These runs are exploratory context-engineering checks, not ACE paper-result
reproductions.

## Controlled settings

- Official released ACE Finance Generator prompt.
- Official released Formula test records and exact-match evaluator.
- Ollama OpenAI-compatible endpoint.
- Temperature 0, seed 100, 32K context, 1,024 maximum output tokens.
- Models run sequentially to avoid memory contention on the 24GB host.

## V1: generic financial precision guidance

Run: `20260904T163930Z`, Formula test offsets 0-2.

| Model | Correct | Accuracy |
| --- | ---: | ---: |
| `llama3.1:8b` | 2/3 | 66.7% |
| `qwen3:8b` | 1/3 | 33.3% |
| `gemma3:4b` | 2/3 | 66.7% |
| `deepseek-r1:8b` | 3/3 | 100.0% |

The generic rule that margin, rate, or yield should be multiplied by 100 fixed
the Operating Margin case but overgeneralized to Dividend Yield. The benchmark
expects Operating Margin as percentage points (`15.0`) and Dividend Yield as a
decimal ratio (`0.05`). Llama also selected the correct DDM formula but returned
an inconsistent calculation; Qwen produced one empty response.

## V2: metric-specific benchmark guidance

Run: `20260904T164300Z`, Formula test offsets 0-2.

| Model | Correct | Accuracy | Mean latency |
| --- | ---: | ---: | ---: |
| `llama3.1:8b` | 3/3 | 100.0% | 6.28s |
| `qwen3:8b` | 3/3 | 100.0% | 24.79s |
| `gemma3:4b` | 3/3 | 100.0% | 5.29s |
| `deepseek-r1:8b` | 3/3 | 100.0% | 15.01s |

V2 replaced the broad percentage rule with three explicit contracts:

1. Operating Margin = `(Operating Income / Revenue) * 100`, returned as `15.0`.
2. Constant-growth DDM = `D1 / (r - g)`, returned as a price.
3. Dividend Yield = `Dividend / Share Price`, returned as decimal `0.05` for
   this benchmark.

## Reproduction caveat

The raw Formula records contain the named formula and explanation, but the
released `parse_context_and_question_formula` function returns an empty context
and retains only the natural-language question. This makes accumulated formula
knowledge in the playbook important, but V2 is still a manually curated context,
not a playbook learned by the full ACE adaptation loop. Its 3/3 result is only a
targeted regression check and must not be reported as test-set accuracy.

## Independent ACE adaptation per model

Run: `model_specific_ace/runs/20260904T165818Z`.

Each model started from the same official empty section template. The same
model served as Generator, Reflector, and Curator, so no playbook or feedback
was shared across models. This controlled local subset used three Formula train,
three validation, and three test records, one epoch, and one reflection round.

| Model | Initial | Final | Bullets | Observed playbook style |
| --- | ---: | ---: | ---: | --- |
| `llama3.1:8b` | 3/3 | 2/3 | 8 | Verbose; formula, error, and heuristic bullets with substantial duplication. |
| `qwen3:8b` | 3/3 | 2/3 | 3 | Compact formula-only rules for Current Ratio, ROI, and Debt-to-Equity. |
| `gemma3:4b` | 2/3 | 3/3 | 3 | Verification-heavy rules; some malformed nested bullet metadata. |
| `deepseek-r1:8b` | 3/3 | 2/3 | 4 | Formula rules plus context-and-unit interpretation guidance. |

All four playbooks have distinct SHA-256 hashes. Gemma improved on this tiny
test subset, while the other three exhibited negative transfer. These scores
are highly unstable at n=3 and are useful only for inspecting the mechanism and
the model-dependent learned contexts.
