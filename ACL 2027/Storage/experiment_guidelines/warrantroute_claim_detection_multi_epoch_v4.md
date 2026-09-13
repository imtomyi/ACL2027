# WarrantRoute: Multi-Epoch Playbook Adaptation

Historical proposal. The controlling prospective design is now
[the final v5 flaw-detection protocol](warrantroute_flaw_detection_final_protocol_v5.md).
V5 explicitly fixes the learning policy and ablations and separates the four-hour
pilot. This document and its scheduler remain unchanged historical specifications,
not the current run instructions or current call counts.

Date: 2026-09-09. Version: 4.0.
Status: adopted prospective schedule; candidate scheduler implemented and tested.
Claim-detection inference, learning and evaluation runtime integration is pending.
No new experiment or automation has been launched.

## Objective and scope

Test whether repeated development passes improve an evolving Playbook's ability
to detect and characterize flaws in fixed claims on a separate evaluation panel.
Multi-epoch adaptation here means repeated context-memory updates, NOT gradient
training, weight updates, repeated claim repair or additional unique data.
No result or superiority claim follows from adding epochs.

This amendment changes the development schedule and checkpoint comparisons in
[v2](warrantroute_claim_detection_learning_curve_v2.md) and
[v3](warrantroute_claim_detection_call_consolidation_v3.md). Their original-text,
eligibility, reference-quality, exact-span, rubric, leakage and manuscript
restrictions remain in force. Historical result files are unchanged. Existing
v2/v3 posters show the old single-epoch schedule and should not be used as v4
execution instructions.

Keep the adopted maximum five-call review with one Evidence-Grounded Finalizer.
The one-call Learning Editor remains a candidate requiring its own pilot. Adding
epochs does not silently adopt it. The default extra development path therefore
still has feedback, updater and guard calls. A candidate cost estimate is also
provided, but its scores must not be pooled with the default learning policy.

## Development schedule

Default: THREE epochs. Each corpus/model condition sees the same 20 unique
development packets once per epoch, for 60 scheduled exposures. Across four
corpora and three models this is 720 development episodes on 80 unique packets.
The evaluation panel remains 100 packets per corpus, or 400 unique packets.
The total unique inventory remains 480 candidate packets.

```text
Seed Playbook E0
    -> epoch 1: 20 development packets -> snapshot E1
    -> epoch 2: the same 20 packets    -> snapshot E2
    -> epoch 3: the same 20 packets    -> snapshot E3
```

Carry memory forward at every packet and across epoch boundaries. Reset only
when starting a separate corpus/model condition or a separately declared pilot.
The 12 condition memories never share learned rules. Use deterministic shuffled
packet order per epoch, based on a fixed seed, corpus, epoch and packet ID.
The order is identical across models for a given corpus/epoch; it is independent
of scores, reference categories and model behavior. Store the actual order and
configuration hash before any inference. Three epochs are a bounded starting
choice, not an empirically optimized value.

Each exposure uses a fresh stateless review request with the original claim,
complete evidence and currently retrieved abstract rules. Do not inject the
previous exposure's raw diagnosis, feedback or reference into the review agents.
Lock the new prediction before exposing its CURRENT development reference to
the learning stage. The same immutable reference is reused across epochs, not
regenerated to agree with newer predictions. Model-built reference disagreement
remains unresolved.

Later development passes are NOT unseen tests: the Playbook has already learned
from these packets. Track development performance as adaptation diagnostics,
never as generalization evidence. Do not describe epoch 2/3 as blind first-pass
predictions. The evaluation references never enter any learning stage.

## Memory safeguards for repeated examples

Keep the same active-rule cap of 40 and retrieval cap of six in every epoch.
Repeated exposure alone must not increase rule confidence, source diversity or
independent-support counts. Record total exposures separately from distinct
supporting packet IDs and source groups, using audit-only provenance. Two or
three visits to one packet remain ONE distinct packet of support.

Prefer a justified localized revision to a duplicated rule. Do not add rules
merely to show Playbook growth. Record unchanged snapshots, rejected updates,
contradictions, harmful rules and capacity failures. A more detailed Playbook
may overfit or hurt detection; retain that outcome. Semantic generality and
paraphrased memorization are not proved by code-only validation.

Learning prompts receive the following identical amendment across all models:

```text
This is multi-epoch development on a previously declared fixed packet pool.
Do not treat another exposure to the same packet as independent evidence.
Compare the locked current prediction to the unchanged current development
reference. Propose a new rule only if it adds a distinct reusable procedure;
otherwise revise an applicable editable rule or leave memory unchanged.
Do not copy packet-specific answers, source quotations or previous diagnoses
into retrieved memory. Retain counterconditions and unresolved reference issues.
```

The runner must enforce deduplicated support accounting and reference access
boundaries; this text does not replace those checks. Preserve each prompt's
original policy, including the candidate Learning Editor's non-independent
self-check and the default guard's separate-call status.

## Checkpoints and comparisons

| Snapshot | Scheduled development exposures per condition | Evaluation per corpus/model |
| --- | ---: | ---: |
| E0 | 0 | Same full 100 |
| E1 | 20 | Same full 100 |
| E2 | 40 | Fixed 20-item subset of the 100 |
| E3 | 60 | Same full 100 |

The primary multi-epoch contrast is E3 minus E1 on matched 100-item panels.
E3 minus E0 measures total adaptation relative to the seed. The full E1 panel
is necessary to distinguish gains beyond one pass from gains during the first
pass. Compare all four snapshots on the SAME fixed 20-item probe for the curve,
reusing the relevant full-panel outputs rather than generating extra results.
Do not compare E2's 20-item rate directly against a 100-item rate.

This replaces the old P0/P5/P10/P15/P20 schedule, not an additional series of
checkpoints stacked on top. Every baseline runs once on the 100-item panel per
corpus/model and is reused as an unchanged comparison across checkpoint reports.
Do not rerun baselines once per epoch. Fresh matched baseline outputs are still
required; older differently prompted results are not substitutes.

Freeze all development snapshots before evaluating them. Evaluate each snapshot
read-only, with the same external judge, rubric and permitted inputs. Do not
stop at the best epoch, increase epochs after seeing held-out results or update
rules from an evaluation judgment. Technical stops remain allowed and visible.
Interim judging is observational and cannot tune this frozen design.

Report reference-relative grounded recall, unsupported allegations, Credibility
and Conformability using the inherited denominators and missingness rules.
Count paired packets, not epochs, as repeated units. A learning curve is not
three independent experimental replications. E3 is the predeclared final table
checkpoint even if E1 performs better. Report the decrease if it occurs.

## Workload and time

| Work item | v4 count |
| --- | ---: |
| Unique candidate packets | 480 |
| Development exposures: 4 corpora x 3 models x 20 packets x 3 epochs | 720 |
| Baseline outputs | 3,600 |
| WarrantRoute outputs: 12 conditions x (100 + 100 + 20 + 100) | 3,840 |
| Total evaluation output slots and external judgment bundles | 7,440 |
| Reference-preparation calls: 480 unique packets x two passes | 960 |
| Immutable logical snapshots: 12 conditions x four checkpoints | 48 |
| Maximum semantic calls, adopted learning policy | 40,560 |
| Maximum semantic calls, candidate one-call learning policy | 39,120 |

Reference preparation is reused, not multiplied by epoch count. The adopted
policy additionally has 720 development feedback calls; the candidate performs
that feedback within its 720 Learning Editor calls. Evaluation outputs are not
unique new data. Three epochs triple development exposures, not all work.

Using the same historical service-duration proxies and unmeasured merged-stage
assumptions as v3:

- Adopted five-call review plus three extra development calls: approximately
  184-365 hours, or 7.7-15.2 days, for the main experiment.
- If separately adopted after a pilot, five-call review plus one Learning Editor:
  approximately 180-354 hours, or 7.5-14.8 days.

These are provisional local serial inference scenarios, not observed v4 speed,
confidence intervals or guarantees. They exclude implementation, eligibility
remediation, extended validation, pilot comparisons and machine downtime. Longer
Playbook contexts and merged outputs can exceed the forecast. Re-estimate with
pilot measurements before launch. No paid API authorization is implied.

For a multi-epoch feasibility pilot, use the prior development-only six-item
selection per corpus: two adaptation items and four distinct pilot probe items.
Repeat the TWO adaptation items for three epochs and evaluate E0/E1/E2/E3 on
the same FOUR probes. Baselines still run once. This gives 72 development
episodes, 336 evaluation outputs and 48 reference-preparation calls across
all conditions. Pilot time needs this increased workload, not the older
single-epoch 6-12-hour figure: approximately 10-20 hours with the adopted policy,
or 10-19 hours with candidate learning, under the same provisional assumptions.
No pilot output enters the main table.

## Scheduler, resumption and implementation boundary

The new code is deliberately separate from the stopped TA-generation runtime:

- [Configuration](../../experiments/warrantroute_claim_detection/multi_epoch_v4.json).
- [Candidate scheduler](../../experiments/warrantroute_claim_detection/plan_multi_epoch.py).
- [Offline tests](../../experiments/warrantroute_claim_detection/test_multi_epoch.py).
- [Timing estimator](estimate_claim_detection_runtime.py).

The scheduler reads historical candidate packet IDs only. It must not reuse
source-only TA task payloads for the new claim-detection inference. Its output
is marked candidate_schedule_only_not_runnable. Exact claim eligibility, source
overlap and source-aware probe selection require a fresh audit. The preliminary
probe is deterministic ID-hash selection and is not represented as source-balanced
or newly held out. Freeze the audited final selection before any inference.

Job identities include configuration/selection namespace, corpus, model, phase,
epoch or checkpoint, and packet ID. Revisiting a packet cannot overwrite its
earlier result. Development events form one parent-linked memory chain across
epochs. E0 references the seed, and later snapshots reference their epoch's last
event. Every epoch slot must reach a recorded terminal disposition before its
snapshot is finalized; report successful predictions, failed updates and technical
failures separately from scheduled exposures. Never skip a failure silently.

The planner describes dependencies, NOT an implemented durable executor. The
runner still must verify actual prediction/reference/model/prompt/Playbook hashes,
commit events atomically and reconcile ambiguous in-flight calls without duplicate
inference. Do not reconstruct a snapshot from whichever current Playbook happens
to be on disk. Code must enforce evaluation's read-only memory boundary.

Reference creation and external judging are separately required stages, not
implemented by this scheduler. Block launch until the new claim-detection runner,
finalizer, learning policy, reference matcher, judge and resume checks pass the
declared pilot gates. The stopped TA runtime must not be repurposed by merely
adding an epoch loop. No inference or model weight change occurred in this update.

## Reporting

Export a private 48-row final table using E3 for the 12 WarrantRoute rows and
36 fresh baseline rows. Keep full E0/E1 controls and paired E3-E1/E3-E0 differences
separately. Export 48 curve rows (four snapshots x 12 conditions), each on the
fixed 20-item probe. Include epoch, cumulative exposures, unique development
packets, valid/failed counts, rule versions, distinct rule support and call costs.

When a new run is explicitly launched, the progress monitor should show epoch,
position out of 20, total development out of 720, evaluation and judging out of
7,440, per-phase ETA and memory growth without treating repeated evidence as
independent support. This amendment does not resume that paused automation.
