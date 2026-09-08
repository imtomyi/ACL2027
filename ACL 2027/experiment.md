# Table 3 Working Experiment Runbook

Last updated: 2026-09-07 KST

## Prospective Judgment Criteria and No-Human-Reference Design

The [Evidence-grounded evaluation guidelines](Storage/experiment_guidelines/objective_review_criteria_v1.md)
record the 2026-09-07 decisions and operational criteria for future experiments:
no new efficiency-driven text transformations; exact evidence and claim
boundaries; five flaw-family criteria; separate review Credibility and
Conformability rules; missingness-aware reporting; and a proposed evaluation
without human answer creation or calibration. WarrantRoute implementation
remains user-led. The multi-judge design is a proposal, not an authorized run.

This addendum does not change frozen prompts, existing scores or historical
contracts below. It does not certify natural-flaw accuracy or manuscript
eligibility. New execution requires a separate implemented and frozen protocol.

## New WarrantRoute Live-Loop Experiment

The new live review-and-revision experiment has its own
[execution and comparison guide](experiments/rq2_role_prompted_llm/WARRANTROUTE_LOOP_EXPERIMENT_GUIDE.md).
It uses 100 working packets per dataset across Dreaddit, GoEmotions, CaChe and
ParlaMint-GB, with three single-model conditions: `qwen_only`, `llama_only` and
`gemma_only`. Every role and recheck uses the same LLM within a condition.
Running all three conditions produces 1,200 trajectories over 400 unique
packets. Mixed-model assignments are not the primary comparison.

This is a separately frozen private diagnostic, not an automatic continuation
of the historical Table 3 queue. Its live revision outputs do not replace the
saved baseline reviews or the deferred historical WarrantRoute quality rows.
The new protocol separates original-flaw detection, actual execution costs,
loop acceptance and independently evaluated repair quality. It does not use
answer labels for routing, update the Playbook between evaluation packets, or
export results to the manuscript. The sections below retain the earlier
experiments' conduct rules and records.

## Current Review-Quality Execution

The user-authorized retrospective Credibility and Conformability audit has
completed for the three baseline methods. Its authoritative English protocol is
[Review-quality guidelines](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/README.md>).
Base execution is recorded in
[progress.json](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/runs/review_quality_n100_20260904_r2/progress.json>)
and the adjacent immutable manifest.json.
The eight exhausted technical failures were completed under the separate
[repair final](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/repairs/review_quality_n100_20260904_r2_schema_r1/final.json>).

This audit reuses 400 packets and the repaired saved reviews, with no new
reviewer generations. Each packet-method-reviewer-model receives one primary
Qwen3 8B judgment containing both binary dimensions: 3,600 evaluations total.
Generalist uses generalist; Fixed role uses qualitative_methods for every model;
All roles is judged as one complete three-role bundle, not a union of passes.
WarrantRoute's 12 rows are deferred. No successful false/null judgment is retried.
Only technical failures permit up to two additional attempts.

Each baseline metric cell now has 100 binary decisions. All 36 baseline quality
rows have been exported to the existing Storage MD/CSV. Detection values,
original reviewer outputs, and WarrantRoute rows are preserved. WarrantRoute
quality remains deferred, leaving its 12 quality rows N/A. Results remain
diagnostic, without completed human validation or manuscript eligibility.

The sections below are the historical detection-run record, not the execution
contract for this audit. In particular, their model-specific role selection,
flag-union scoring, 48-row completion condition, and automatic restart rules
must not be applied to the current review-quality run.

An optional Portkey AI Gateway adapter, offline preflight, and concurrency-safe
USD 100 request-reservation ledger are prepared for a future, separately frozen
experiment. The run additionally requires a dedicated Portkey API key with a
non-resetting USD 100 remote budget. No credential is configured and no Portkey
request has been made. See
[Portkey backend setup](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/PORTKEY_SETUP.md>).

## Historical Detection Run

This document records the conduct rules and execution flow for the current
Table 3 working experiment. The immediate purpose is to fill the working Table 3
shape for flaw detection:

```text
4 datasets x 4 methods x 3 models = 48 rows
```

This experiment evaluates whether a reviewer output detects the intended flaw.
It is not a document-repair experiment.

## 1. Conduct Rules

1. Treat all current results as working/internal records unless a later formal
   study freeze explicitly promotes them.
2. Keep working outputs under `Storage/`. Do not insert these values into active
   manuscript, appendix, compiled PDF, or submission-export files.
3. Do not delete original reviewer outputs. Do not overwrite an existing
   `status=valid` reviewer JSON.
4. Count only reviewer JSON files whose packet IDs belong to the active
   `balanced_n100` packet set. Some run roots may contain older or larger-stage
   outputs, and those must not inflate Table 3 progress.
5. If a run crashes, resume through the resilient queue or finalizer. Avoid
   duplicate queue/finalizer processes.
6. Treat `schema_warning`, corrupt JSON, mismatched corpus/role/model, and
   missing outputs as repair targets. Existing valid outputs are reused.
7. WarrantRoute must not use answer-key fields, truth-map fields, source text,
   specialist outputs, human judgments, repair outcomes, held-out outcomes, or
   protected participant attributes for routing.
8. The answer key is opened only after reviewer outputs and routes exist, for
   scoring `TP/N` and recall.
9. The final working table is complete only when the final manifest says
   `status=validated_complete` and `table_row_count=48`.

## 2. Table 3 Shape

Datasets:

| Display label | Internal corpus ID | Run root |
| --- | --- | --- |
| Dreaddit | `dreaddit` | `Storage/draft_review_packets/dreaddit_dev580_working_v1` |
| GoEmotion | `goemotions` | `Storage/draft_review_packets/goemotions_train_all_working_v1` |
| CaChe | `agyw_focus_groups` | `Storage/draft_review_packets/agyw_focus_groups_eval765_working_v1` |
| ParlaMint-GB | `parlamint_gb` | `Storage/draft_review_packets/parlamint_gb_fullsample_eval100_working_v1` |

Methods:

| Method | Operational definition |
| --- | --- |
| Generalist | Use only the `generalist` reviewer output. |
| Fixed role | For each model, pick the single role with the highest working recall; ties prefer `generalist`, then `qualitative_methods`, then `domain`. |
| All roles | Union detected flaw flags from `generalist`, `qualitative_methods`, and `domain`. |
| WarrantRoute | Use WarrantGate v0 to route each packet to `generalist`, `qualitative_methods`, `domain`, or `both`; `both` unions the two specialist roles only. |

Models:

| Display label | Ollama model ID | Output directory |
| --- | --- | --- |
| Qwen3 8B | `qwen3:8b` | `qwen3_8b` |
| Llama 3.1 8B | `llama3.1:8b` | `llama3_1_8b` |
| Gemma 3 4B | `gemma3:4b` | `gemma3_4b` |

Reviewer roles:

```text
generalist
qualitative_methods
domain
```

Expected reviewer-output count:

```text
4 datasets x 100 packets x 3 roles x 3 models = 3600 reviewer JSON files
```

Expected WarrantRoute output:

```text
4 datasets x 100 packets x 3 models = 1200 routes
```

Expected final table:

```text
4 datasets x 4 methods x 3 models = 48 rows
```

## 3. Metrics

The current Table 3 columns are:

```text
Dataset | Method | Model | TP/N | Recall (%) ↑
```

Detection rule:

```text
TP = packet is counted as detected when the selected method's normalized flags
     contain the packet's known intended flaw type.
N  = evaluated packet count.
Recall = TP / N.
```

The displayed recall includes a 95% Wilson confidence interval.

Credibility and conformability are available as a separate LLM-as-Judge quality
path, following the binary success-rate idea:

- Credibility: whether generated codes, subthemes, or themes represent the data.
- Conformability: whether they are data-driven and consistent with the original
  input context.

For the current Table 3-only queue, this path is disabled with
`--skip-quality-judge`, so credibility and conformability are not required for
the five-column Table 3 currently being filled.

## 4. WarrantRoute Policy

The current WarrantRoute row uses WarrantGate v0, a deterministic cost-sensitive
routing policy:

```text
S_G(x) = g(x)
S_M(x) = m(x) - c_M
S_D(x) = d(x) - c_D
S_B(x) = min(m(x), d(x)) + i_MD(x) - (c_M + c_D + c_B)

route(x) = argmax {S_G(x), S_M(x), S_D(x), S_B(x)}
```

Current costs:

```text
c_M = 0.25
c_D = 0.25
c_B = 0.08
```

Tie order:

```text
generalist -> qualitative_methods -> domain -> both
```

The executable policy source is:

```text
experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json
```

The main WarrantRoute record is:

```text
warrentroute.md
```

The filename intentionally keeps the spelling `warrentroute.md` for continuity
with the existing project notes.

## 5. Execution Flow

The working pipeline is:

```text
balanced_n100 packet bank
  -> run reviewer outputs for 3 roles x 3 models
  -> summarize each role's reviewer outputs
  -> build WarrantGate v0 routes
  -> score Generalist, Fixed role, All roles, and WarrantRoute
  -> export Table 3 snapshots
  -> finalizer repairs missing/invalid/warning records
  -> finalizer validates and publishes the 48-row final working table
```

Primary queue command currently used by the resilient agent:

```sh
python3 "ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py" \
  --max-stage 100 \
  --queue-name table3_resilient_n100_20260902 \
  --skip-quality-judge \
  --timeout 240 \
  --num-predict 256
```

Resilient queue agent:

```text
experiments/rq2_role_prompted_llm/scripts/run_table3_resilient_agent.sh
```

Postprocess/finalizer agent:

```text
experiments/rq2_role_prompted_llm/scripts/run_table3_warrantroute_postprocess_agent.sh
```

Finalizer:

```text
experiments/rq2_role_prompted_llm/scripts/finalize_table3_warrantroute.py
```

## 6. Current State Snapshot

Snapshot time: 2026-09-02 16:17 KST.

Active screen sessions:

```text
table3_resilient_n100_20260902
table3_warrantroute_n100_postprocess
```

Active queue state:

```text
Queue process: running
Reviewer process: running
Current visible reviewer combination:
  ParlaMint-GB / qualitative_methods / llama3.1:8b
Postprocess agent: waiting for queue/reviewer idle
Final manifest: not yet present
```

Progress counted only against the active `balanced_n100` packet IDs:

| Dataset | Files | Valid | Warnings |
| --- | ---: | ---: | ---: |
| Dreaddit | 900/900 | 900 | 0 |
| GoEmotion | 900/900 | 899 | 1 |
| CaChe | 900/900 | 900 | 0 |
| ParlaMint-GB | 484/900 | 482 | 2 |
| Total | 3184/3600 | 3181 | 3 |

Current overall progress:

```text
3184 / 3600 reviewer JSON files = 88.4%
416 target reviewer outputs remaining
```

Remaining or warning-bearing combinations:

| Dataset | Role | Model | Files | Valid | Warnings |
| --- | --- | --- | ---: | ---: | ---: |
| GoEmotion | `domain` | `qwen3:8b` | 100/100 | 99 | 1 |
| ParlaMint-GB | `generalist` | `qwen3:8b` | 100/100 | 98 | 2 |
| ParlaMint-GB | `qualitative_methods` | `llama3.1:8b` | 34/100 | 34 | 0 |
| ParlaMint-GB | `qualitative_methods` | `gemma3:4b` | 0/100 | 0 | 0 |
| ParlaMint-GB | `domain` | `qwen3:8b` | 50/100 | 50 | 0 |
| ParlaMint-GB | `domain` | `llama3.1:8b` | 0/100 | 0 | 0 |
| ParlaMint-GB | `domain` | `gemma3:4b` | 0/100 | 0 | 0 |

Recent production rate at this snapshot:

```text
27 target files in the last 5 minutes
83 target files in the last 15 minutes
174 target files in the last 30 minutes
Median valid Ollama duration: 8.480 seconds
```

## 7. Completion Criteria

Do not treat the run as complete merely because a combined snapshot exists.
Completion requires this manifest:

```text
Storage/draft_review_packets/table3_warrantroute_n100_final_manifest.json
```

Required manifest fields:

```text
status = validated_complete
table_row_count = 48
expected_table_row_count = 48
reviewer_status_requirement = valid
```

Expected final artifacts:

```text
Storage/draft_review_packets/table3_warrantroute_n100_final.csv
Storage/draft_review_packets/table3_warrantroute_n100_final.md
Storage/draft_review_packets/table3_warrantroute_n100_final_manuscript.csv
Storage/draft_review_packets/table3_warrantroute_n100_final_manifest.json
```

## 8. Monitoring Checklist

Use this checklist for each progress check:

1. Confirm that only one resilient queue and one postprocess/finalizer agent are
   active.
2. Count reviewer outputs only for active `balanced_n100` packet IDs.
3. Report `files`, `valid`, `schema_warning`, and remaining count by dataset.
4. Check whether output count increased since the last check.
5. Identify the active dataset, role, and model from the reviewer process.
6. Estimate ETA from recent real file generation rate, not from all historical
   files in the run root.
7. If the queue process is gone, inspect logs before restarting.
8. If errors repeat, diagnose from logs and resume through the prepared
   resilient queue or finalizer only when it is safe and non-duplicative.
9. Stop monitoring once the final manifest validates 48 rows.

Useful commands:

```sh
screen -ls

ps -axo pid,etime,command | rg \
  'run_table3_resilient_agent|run_all_usable_table3_queue|run_working_generalist_reviews|run_table3_warrantroute_postprocess_agent|finalize_table3_warrantroute' \
  | rg -v 'rg '

tail -n 80 "ACL 2027/Storage/draft_review_packets/table3_warrantroute_n100_postprocess.agent.log"
tail -n 80 "ACL 2027/Storage/draft_review_packets/table3_resilient_n100_20260902.log"
tail -n 80 "ACL 2027/Storage/draft_review_packets/table3_resilient_n100_20260902.watchdog.log"
```

## 9. Important Local Files

Project policy:

```text
AGENTS.md
```

WarrantRoute notes:

```text
warrentroute.md
experiments/rq2_role_prompted_llm/protocol/working_warrantgate_v0_decision.md
experiments/rq2_role_prompted_llm/protocol/working_warrantgate_v0_design.md
experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json
```

Queue and scoring:

```text
experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py
experiments/rq2_role_prompted_llm/scripts/run_working_generalist_reviews.py
experiments/rq2_role_prompted_llm/scripts/summarize_working_generalist_reviews.py
experiments/rq2_role_prompted_llm/scripts/build_working_warrantgate_routes.py
experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py
experiments/rq2_role_prompted_llm/scripts/finalize_table3_warrantroute.py
```

Interim outputs:

```text
Storage/draft_review_packets/table3_resilient_n100_20260902_table3_combined.csv
Storage/draft_review_packets/table3_resilient_n100_20260902_table3_combined.md
Storage/draft_review_packets/table3_working_interim_20260902.md
```

Logs:

```text
Storage/draft_review_packets/table3_resilient_n100_20260902.log
Storage/draft_review_packets/table3_resilient_n100_20260902.watchdog.log
Storage/draft_review_packets/table3_warrantroute_n100_postprocess.agent.log
Storage/draft_review_packets/table3_warrantroute_n100_finalize.log
```

## 10. Known Interpretation Notes

- Table 3 is about flaw detection quality, not fixing document quality.
- The model column names the local LLM that produced reviewer outputs.
- The methods are different ways to use reviewer roles, not separate datasets.
- WarrantRoute does not add a fourth reviewer call. It routes among existing
  role outputs.
- Fixed role is selected per model from working recall and then applied as a
  single fixed role for that model.
- All roles is the broadest role-union baseline.
- LLM-as-Judge credibility/conformability can be run separately, but the current
  Table 3 queue skipped it.
- Working snapshots are useful for debugging and planning, but the only current
  completion signal is the final validated manifest.

## 11. WarrantLoop Development Smoke

WarrantLoop, provisionally labeled WarrantRoute-S, is a separate successor
method and is not one of the current Table 3 rows. Its development-only offline
replay passed the small-sample gate on 2026-09-02:

```text
Dreaddit development balanced_n100
  train = 75 packets
  validation = 15 packets
  source-disjoint smoke test = 10 packets
  models = 3
  completed routes = 30/30
  new LLM calls = 0
  status = validated_smoke_complete
```

The validated record is
`Storage/rq2_personal_local_diagnostic/warrantloop_working/smoke_n10_20260902_v4/`.
All estimators were either converged regularized logistic fits or the declared
Laplace-smoothed fallback for a binary class with fewer than three observations.
Every route terminated, used at most two specialists, excluded source text and
truth fields, and was scored only after the complete route file existed.

This establishes development-software readiness only. `formal-run` remains
fail-closed because there is no approved successor study freeze. Do not run
WarrantLoop on an audit or held-out lane, add it to Table 3, or use its smoke
metrics in a manuscript. The existing one-shot WarrantRoute Table 3 queue
continues under Sections 1 through 10 without alteration.

## 12. WarrantRoute-S Four-Corpus Working Replay

The sequential model is different from the one-shot WarrantRoute row, so it was
evaluated separately after the original 48-row table completed. The original
table and its final manifest were not changed.

Execution design:

- Dreaddit: five-fold out-of-fold routing, with threshold selection confined to
  each outer fold's training portion;
- GoEmotion, CaChe, and ParlaMint-GB: one policy fitted only on the complete
  Dreaddit development bank and applied unchanged;
- 100 packets per dataset and three model profiles;
- all 3,600 cached role outputs valid before replay;
- 1,200 unique routes generated before evaluation truth was opened;
- no new LLM calls.

The run completed with `status=validated_working_complete`. It produced 12
WarrantRoute-S rows and a separate 60-row comparison table. Across all 12 equal-
size cells, WarrantRoute-S detected `770/1200` targets (`64.2%`) versus
`653/1200` (`54.4%`) for the one-shot WarrantRoute. Its mean specialist
acquisition count was `0.36` per packet versus `0.71` for the one-shot route
assignments.

The selected WarrantRoute-S operating points acquired at most one specialist;
the second specialist was never acquired in these 1,200 routes. Thus this run
does not demonstrate a benefit from the second loop step. It shows that the new
policy behaves differently from WarrantGate and motivates a prospectively
frozen threshold/cost frontier rather than post-hoc retuning.

The results are retrospective working diagnostics. CaChe and ParlaMint-GB
outcomes had already been opened by the earlier Table 3 working run, so these
values are not a new held-out test and remain ineligible for manuscript use.
Artifacts are stored under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_v1/`.

## 13. WarrantRoute Diagnostic-Guided Correction

The failure analysis in
`Storage/draft_review_packets/table3_warrantroute_diagnostic_20260902.md` was
implemented as two no-new-call offline candidates.

The selected immediate correction keeps the public name `WarrantRoute` and uses
the internal variant ID `cumulative_output_v1`. It reuses the validated
WarrantRoute-S route decisions but always retains the already-paid-for Generalist
output. Across the same 1,200 model-packet pairs it produces
`773/1200` detections (`64.4%`) at mean `1.3592` role calls, compared with
`770/1200` (`64.2%`) at the same call count for WarrantRoute-S. The improvement
is three TPs, with no cell regression and no change to route decisions or
specialist acquisitions.

A separately fitted cumulative marginal-gain router was also tested with
model-specific logistic estimators, stable tie handling, a mean 1.75-call
development budget, and exact validation-score breakpoint search. It produces
`747/1200` detections at mean `1.3692` calls and is therefore rejected because
the corrected WarrantRoute has both higher recall and lower mean calls.

These are retrospective working diagnostics, not manuscript evidence. The
renamed working artifacts are under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_warrantroute_improved_v1/`.
The rejected breakpoint prototype is retained under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_calibrated_cascade_breakpoints_v2/`.
