# Active Table 3 WarrantRoute Same-Model n100

Launched 2026-09-05. Screen: `table3_same_model_n100_20260905`.
Private working diagnostic only; not manuscript-eligible.

| Condition | Model used by every loop agent | Planned trajectories |
| --- | --- | ---: |
| qwen_only | Qwen3 8B (`qwen3:8b`) | 400 |
| llama_only | Llama 3.1 8B (`llama3.1:8b`) | 400 |
| gemma_only | Gemma 3 4B (`gemma3:4b`) | 400 |

Each condition uses the same 100 packets from each of Dreaddit, GoEmotions,
CaChe and ParlaMint-GB. The five agent roles share the condition's model, not
mixed model families. Role prompts, routing, seeds and call budgets match.
There is one trajectory per packet-model pair, at most two revision rounds and
12 agent calls per trajectory. Playbook updates are disabled.

The supervisor runs all 1,200 trajectories, scores original-flaw detection,
and performs up to 1,200 separate Qwen judgments of original-review Credibility
and Conformability. The first packet in every dataset-model cell is an included
technical canary, including its quality judgment. Each quality response yields
both dimensions. Successful judgments are never repeated for a better score.

It then updates the 12 WarrantRoute rows of the Storage Table 3 CSV and MD,
including detection and quality together, preserving the 36 baseline rows.
Unresolved quality cases remain N/A with explicit counts. Human validation is
pending. These are review-projection metrics, not independent repair scores.
Qwen self-family judging bias and controlled flaw-template exposure remain
limitations. No Portkey or other paid API calls are used.

## Open Files

- [Frozen experiment protocol](quality/protocol.md)
- [Frozen loop manifest](manifest.json)
- [Frozen quality manifest](quality/manifest.json)
- [Judge prompt](quality/prompt.txt)
- [Progress snapshot](table3_progress.json)
- [Live process log](screenlog.0)
- [Migration record](MIGRATION.md)
- [Original CSV backup](quality/table_before.csv)
- [Original Markdown backup](quality/table_before.md)

After completion: `comparison.json`, `quality/summary.json`,
`quality/final_manifest.json`, `quality/human_audit.private.json`, and
`quality/table3_export.csv` / `.md`. The target is
`Storage/draft_review_packets/table3_warrantroute_n100_final.csv` and its MD peer.

From the project directory:

```sh
/opt/anaconda3/bin/python3 -B \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_same_model_table3.py \
  status --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2
```

Use `run` instead of `status` only to resume after confirming no duplicate
supervisor is active. Never modify frozen source files while the run is active.
The run lock prevents duplicate supervisors. A `table3_supervisor_error.json`
records a blocked supervisor; a stale progress snapshot alone is not live health.

Verification: the three model digests and all 400 packet projections passed
preparation. Controller, live-loop, same-model and historical review-quality
tests passed. These are software checks, not expert semantic validation.
