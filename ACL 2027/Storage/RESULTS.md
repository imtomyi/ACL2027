> Consolidated v5 results: [v5_results.md](v5_results.md).

> Current server v5: Base/ICL finished **1,800 attempts, 1,738 valid outputs, 62 format failures**. **ACE/DC is running: 33 seed runs admitted, 21 held for development fixes.** [Live ACE/DC results](server_v5_preparation/adaptation_r1/RESULTS.md) · [Base/ICL results](server_v5_preparation/live/RESULTS.md) · [Full status](server_v5_preparation/STATUS.md). Judging remains pending. Historical local results below retain their original protocol.

> Next server comparison: [merged experiment guidelines v5](EXPERIMENT_GUIDELINES.md). This report remains the separate paused local run.

# Experiment results · N=100 per dataset

Updated: **2026-09-14T08:59:44+09:00**. Refreshed by the five-minute monitor.

**400 unique evaluation items: Dreaddit 100 · GoEmotions 100 · CaChe 100 · ParlaMint-GB 100.** Every method and both phases reuse the same ordered 100 items per dataset. Training and adaptation examples are separate.

**Fully evaluated rows in this report: 10/24.** A row is complete only after prediction, required online updates, and all 100 resolved judgments.

**Fresh uniform protocol:** all 24 rows restart from empty state with new run-local caches. Prediction/generator/optimizer/reflector start at 4,096 output tokens; curator at 8,192; judge at 384. The same predeclared length-only retry rule doubles non-judge caps up to 16,384 within context 32,768. No truncated answer is accepted. ACE/DC memory is bounded at 4,096 tokens; oversized updates retain the previous valid memory. Earlier scores remain separate. [Frozen protocol](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260914_uniform/PROTOCOL.md>).

Execution priority: ParlaMint-GB → CaChe → GoEmotions → Dreaddit.

Offline and online prioritize completing every scheduled 100-item evaluation and its judgments. The user authorized additional time; the previous two-hour cutoff is disabled.

## Results and progress

Acc and Conformability are percentages. **—** = not yet final; **N/A** = metric not applicable to the current evaluation. Predicted, updated, and judged are separate counts, each out of 100.

The four ACE/AppWorld metric columns are included for reference. They are N/A for these corpora: the current evaluation has no official AppWorld Normal/Challenge splits, executable task-success tests, or scenario groups. N/A is not zero or a pending score.

### Dreaddit

| Phase | Method | GT | Acc % | Conformability % | Test-Normal TGC↑ | Test-Normal SGC↑ | Test-Challenge TGC↑ | Test-Challenge SGC↑ | Predicted | Updated | Judged | Unresolved | Status |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Offline | Qwen3 8B Base | — | — | — | N/A | N/A | N/A | N/A | 0/100 | — | 0/100 | 0 | Queued |
| Offline | ICL | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | — | 0/100 | 0 | Queued |
| Offline | MIPROv2 | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | — | 0/100 | 0 | Queued |
| Offline | GEPA | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | — | 0/100 | 0 | Queued |
| Online | DC (CU) | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |
| Online | DC (CU) | ✗ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |
| Online | ACE | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |
| Online | ACE | ✗ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |

### GoEmotions

| Phase | Method | GT | Acc % | Conformability % | Test-Normal TGC↑ | Test-Normal SGC↑ | Test-Challenge TGC↑ | Test-Challenge SGC↑ | Predicted | Updated | Judged | Unresolved | Status |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Offline | Qwen3 8B Base | — | 26.00 | 100.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Offline | ICL | ✓ | 22.00 | 99.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Offline | MIPROv2 | ✓ | 19.00 | 99.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Offline | GEPA | ✓ | 23.00 | 100.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Online | DC (CU) | ✓ | — | — | N/A | N/A | N/A | N/A | 86/100 | 85/100 | 0/100 | 0 | Paused |
| Online | DC (CU) | ✗ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |
| Online | ACE | ✓ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |
| Online | ACE | ✗ | — | — | N/A | N/A | N/A | N/A | 0/100 | 0/100 | 0/100 | 0 | Queued |

### CaChe

| Phase | Method | GT | Acc % | Conformability % | Test-Normal TGC↑ | Test-Normal SGC↑ | Test-Challenge TGC↑ | Test-Challenge SGC↑ | Predicted | Updated | Judged | Unresolved | Status |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Offline | Qwen3 8B Base | — | N/A | 99.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Offline | ACE | ✗ | N/A | — | N/A | N/A | N/A | N/A | 0/100 | — | 0/100 | 0 | Failed |
| Online | DC (CU) | ✗ | N/A | 99.00 | N/A | N/A | N/A | N/A | 100/100 | 100/100 | 100/100 | 0 | Complete |
| Online | ACE | ✗ | N/A | 100.00 | N/A | N/A | N/A | N/A | 100/100 | 100/100 | 100/100 | 0 | Complete |

### ParlaMint-GB

| Phase | Method | GT | Acc % | Conformability % | Test-Normal TGC↑ | Test-Normal SGC↑ | Test-Challenge TGC↑ | Test-Challenge SGC↑ | Predicted | Updated | Judged | Unresolved | Status |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Offline | Qwen3 8B Base | — | N/A | 100.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Offline | ACE | ✗ | N/A | 100.00 | N/A | N/A | N/A | N/A | 100/100 | — | 100/100 | 0 | Complete |
| Online | DC (CU) | ✗ | N/A | 99.00 | N/A | N/A | N/A | N/A | 100/100 | 100/100 | 100/100 | 0 | Complete |
| Online | ACE | ✗ | N/A | — | N/A | N/A | N/A | N/A | 16/100 | 16/100 | 0/100 | 0 | Failed |

## Reading these results

- Model: Qwen3 8B Q4_K_M, thinking off, seed 42. GPT-5 is outside the current queue.
- Dreaddit Acc compares stress labels. GoEmotions Acc requires an exact match of the full emotion-label set.
- CaChe and ParlaMint-GB use GT ✗ only. Acc is N/A; no reference labels are generated.
- GT ✓ supplies labels for adaptation; GT ✗ does not. Offline context is frozen before evaluation; online feedback follows each saved prediction.
- Conformability measures source grounding using a reference-blind judge from the same model family. It is not human validation.
- ACE reports AppWorld Task Goal Completion (TGC: all tests pass for a task) and Scenario Goal Completion (SGC: all tasks in a scenario succeed). These are not substitutes for Acc or Conformability. See [ACE, evaluation metrics](https://arxiv.org/html/2510.04618v1#S4.SS1) and [AppWorld, evaluation and splits](https://arxiv.org/html/2407.18901v1).
- No earlier predictions, judgments, optimizer artifacts or playbooks are reused in this uniform run. These are local task transfers, not exact paper reproductions.

[Detailed metrics, F1 and run settings](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/METRICS.md>).

## Earlier runs · separate protocols

Do not combine these scores with the current N=100 results.

- [24/128/8-item pilot](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/budget_pilot/run_20260913/METRICS.md>)
- [Dreaddit full test](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/dreaddit_icl/comparison_run_20260912/METRICS.md>)
- [GoEmotions full test](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/goemotions_offline/run_20260912/METRICS.md>)
- [Earlier paired-corpus experiment](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/paired_feedback/run_20260912/METRICS.md>)

[Archived earlier N=100 results](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_monitor/incidents/output_cap_recovery_20260914/prior_RESULTS.md>).
