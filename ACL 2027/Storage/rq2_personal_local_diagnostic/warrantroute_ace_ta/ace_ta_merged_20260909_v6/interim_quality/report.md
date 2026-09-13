# Interim quality monitoring

Private exploratory diagnostics. Development quality is not held-out evaluation.
Unknown, technical and pending cases are not counted as passes. Percentages use T/(T+F).
A shared Qwen judge may favor its own model family; these are not independent human ratings.

| Phase | Dataset | Model | Method | Outputs | Credibility T/N (%) | Conformability T/N (%) | Coverage T/N (%) |
|---|---|---|---|---:|---:|---:|---:|
| development | cache | gemma3:4b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | cache | llama3.1:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 0/0 (N/A); U=1, tech=0, pending=0 |
| development | cache | qwen3:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | dreaddit | gemma3:4b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | dreaddit | llama3.1:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 0/0 (N/A); U=1, tech=0, pending=0 |
| development | dreaddit | qwen3:8b | warrantroute | 19 | 16/16 (100.0); U=0, tech=2, pending=1 | 16/16 (100.0); U=0, tech=2, pending=1 | 15/15 (100.0); U=1, tech=2, pending=1 |
| development | goemotions | gemma3:4b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 0/0 (N/A); U=1, tech=0, pending=0 |
| development | goemotions | llama3.1:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 0/0 (N/A); U=1, tech=0, pending=0 |
| development | goemotions | qwen3:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | parlamint-gb | gemma3:4b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | parlamint-gb | llama3.1:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |
| development | parlamint-gb | qwen3:8b | warrantroute | 1 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 | 1/1 (100.0); U=0, tech=0, pending=0 |

## Matched comparisons

Only identical packet IDs and evidence, same phase, same dataset and the fixed judge are compared.
Deltas describe jointly binary cases only; missingness and small denominators limit interpretation.
No significance claims, winner selection or automatic changes follow from these interim looks.

- development / cache: gemma3:4b warrantroute minus llama3.1:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / cache: gemma3:4b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=0.0 pp, n=1, excluded=0
- development / cache: llama3.1:8b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / dreaddit: gemma3:4b warrantroute minus llama3.1:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / dreaddit: gemma3:4b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=0.0 pp, n=1, excluded=0
- development / dreaddit: llama3.1:8b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / goemotions: gemma3:4b warrantroute minus llama3.1:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / goemotions: gemma3:4b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / goemotions: llama3.1:8b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=None pp, n=0, excluded=1
- development / parlamint-gb: gemma3:4b warrantroute minus llama3.1:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=0.0 pp, n=1, excluded=0
- development / parlamint-gb: gemma3:4b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=0.0 pp, n=1, excluded=0
- development / parlamint-gb: llama3.1:8b warrantroute minus qwen3:8b warrantroute: credibility: delta=0.0 pp, n=1, excluded=0; conformability: delta=0.0 pp, n=1, excluded=0; coverage: delta=0.0 pp, n=1, excluded=0
No matched held-out method/model comparisons yet. Do not infer which method is better.

## Historical results

Historical claim-review quality and current TA generation use different tasks and rubrics. No valid improvement delta.
The unchanged historical values are in historical_reference.csv and report.json, for context only.

## Execution

The primary runner still judges each 50-output method batch. This sidecar adds at most one development judge call per scheduled tick.
No sidecar judgments enter Playbook learning, official evaluation outputs, or the historical table.
Additional judge cost: {"calls": 15, "input_tokens": 33174, "output_tokens": 9677, "seconds": 1127.0268142091809, "usage_complete": true}
