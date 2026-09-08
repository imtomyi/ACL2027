# Table 3: Same-Model WarrantRoute n100

Status: superseded after one trajectory by
[the active v2 continuation](../n100_same_model_table3_20260905_v2/README.md).
A concurrent default-config-path edit tripped the source hash guard. All six
complete calls were verified and reused without new inference in v2. See its
migration record. The historical commands below are not the current launch target.

Launch date: 2026-09-05. Working diagnostic only; not manuscript-eligible.
Screen session: `table3_same_model_n100_20260905`.

## Conditions

| Condition | Model for every loop agent | Packets per dataset | Datasets |
| --- | --- | ---: | ---: |
| qwen_only | Qwen3 8B (`qwen3:8b`) | 100 | 4 |
| llama_only | Llama 3.1 8B (`llama3.1:8b`) | 100 | 4 |
| gemma_only | Gemma 3 4B (`gemma3:4b`) | 100 | 4 |

Every condition uses the same Proposer, Evidence Scout, Methods Challenger,
Domain Challenger and Reviser prompts, route policy, packet IDs and budgets.
Agents are distinct calls, not independent model families. The mixed-family
`qwen_led`, `llama_led` and `gemma_led` bundles are not executed by this run.

There are 400 distinct packets from Dreaddit, GoEmotions, CaChe and ParlaMint-GB,
with 1,200 one-repetition trajectories and up to 1,200 quality judgments. The
first 12 trajectories cover every dataset-model cell. Their quality judgments
are included in the final audit, not extra statistical repetitions.

## Execution and Outputs

1. Run the actual bounded revision loop for every planned packet/model.
2. Score original intended-flaw detections after the complete loop inventory.
3. Judge original-review projections for Credibility and Conformability using
   the same fixed local Qwen rubric for all three evaluated models.
4. Export 48 Table 3 rows, changing only the 12 WarrantRoute rows in the Storage
   CSV and MD. Preserve all 36 historical baseline rows. Missing judgments stay
   unresolved rather than becoming fabricated numeric results.

The loop acceptance decision is not the quality grader. These C/C columns assess
review quality, not repaired-document quality. Human validation remains pending.
Qwen self-family judging bias and prior exposure to controlled flaw templates
remain limitations. No paid API or Portkey calls are made.

- [Frozen loop manifest](manifest.json)
- [Frozen quality manifest](quality/manifest.json)
- [Frozen English protocol](quality/protocol.md)
- [Quality judge prompt](quality/prompt.txt)
- [Progress snapshot](table3_progress.json)
- [Live process log](screenlog.0)
- [Original table CSV backup](quality/table_before.csv)
- [Original table MD backup](quality/table_before.md)

The progress snapshot is refreshed after each loop trajectory and periodically
during judging. Call journals under `results/` show an in-flight stage before a
whole trajectory finishes. A process failure is recorded separately in
`table3_supervisor_error.json`; do not confuse a stale snapshot with live health.

From the project directory, inspect current state:

```sh
/opt/anaconda3/bin/python3 -B \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_same_model_table3.py \
  status --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v1
```

Resume with the same command and `run` instead of `status`, after verifying no
other supervisor is active. Per-run locks prevent duplicate dispatch. Do not
modify frozen implementation files, overwrite completed outputs, or create a
new run merely to retry unfavorable results.

Final artifacts, once available: `comparison.json`, `quality/summary.json`,
`quality/final_manifest.json`, `quality/human_audit.private.json`, and
`quality/table3_export.csv` / `.md`. The target is
`Storage/draft_review_packets/table3_warrantroute_n100_final.csv` and its MD peer.

Verification at launch: 18 live-loop tests, 10 original controller tests,
10 same-model/audit tests and 10 historical quality-audit regression tests passed.
All 400 source packet projections and all three exact installed model digests
passed preparation checks. Successful software checks do not establish semantic
correctness or expert validity.
