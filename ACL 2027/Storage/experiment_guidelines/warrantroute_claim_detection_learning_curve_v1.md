# WarrantRoute Claim-Flaw Detection and Playbook Learning Curve

Superseded prospective schedule: use
[version 2](warrantroute_claim_detection_learning_curve_v2.md) for the bounded
diagnosis pipeline, pilot, reduced checkpoint workload and runtime estimate.
This version is retained as design history, not an active run contract.

Date: 2026-09-09. Version: 1.0.
Status: corrected objective and prospective protocol. The new experiment has
not been implemented, qualified or launched. This document is not a completed
validation checklist or permission to spend API credits.

## Authoritative objective

Detect material flaws in a supplied, fixed analysis claim using its supplied
evidence. Accumulate reusable detection procedures in a Playbook as development
experience increases. Test whether later Playbooks improve evidence-grounded
detection on the same evaluation items relative to the initial Playbook and
non-adaptive methods.

Do not substitute generation of codes, themes or new claims for this task.
Do not measure successful rewriting as successful detection. Improved detection
is a hypothesis, not an outcome that the runner must force. A longer Playbook,
more accepted rules, more flags, or agreement among agents is not proof of gain.

The source-only TA generation design in
[the superseded design](warrantroute_ace_ta_experiment_design_v1.md) does not
answer this objective. Its outputs and judges cannot populate this experiment's
detection or review-quality results.

## Inputs and reference boundaries

Each item contains a packet identifier, original claim fields, original claim
hash, source evidence with stable identifiers, and permitted context. Preserve
the original claim for every detection pass and checkpoint. All four methods
receive the same reviewer-visible task and claim hash.

Answer keys, intended flaw categories, construction notes, nested target hints,
future feedback and checkpoint scores are not reviewer-visible. An explicit
allowlist must separate permitted claim content from builder hints. Audit that
boundary before freezing the new run; do not silently edit historical packets.
If necessary content and a construction hint cannot be separated responsibly,
record the eligibility problem rather than silently changing the claim.

Retain Dreaddit, GoEmotions, CaChe and ParlaMint-GB and the three same-model
conditions Qwen3 8B, Llama 3.1 8B and Gemma 3 4B. The existing 100-packet panel
per corpus is a candidate diagnostic panel, not a newly unseen test set.
Re-audit eligibility after restoring claims. Previous source-only TA eligibility
does not establish claim-review eligibility.

The [flaw criteria audit](flaw_criteria_audit_v1.md) establishes that historical
truth maps are intended construction labels, not a validated exhaustive flaw
inventory. Their label-hit score must remain explicitly named intended-target
recall. It cannot be relabeled as natural-flaw accuracy or evidence-grounded
recall. Constructed claims remain private diagnostics under AGENTS.md.

## What qualifies as detection

Apply the common and category-specific criteria in the flaw criteria audit.
A reported issue must identify:

1. The affected original assertion, claim span or scope field.
2. The relevant evidence, contradiction, missing inferential support or omitted
   qualification. Check exact quoted spans against stored evidence.
3. The material consequence and a concise explanation of why the claim is
   unwarranted within the supplied packet.

An omission can be located by its affected claim field and counterevidence;
do not require an impossible literal span for absent text. Merely naming the
expected category, saying that something is wrong, or citing an existing
evidence ID is insufficient for evidence-grounded detection.

Keep established flaw, no flaw established, cannot judge and technical failure
separate. A plausible alternative reading is not automatically a flaw.
Do not count one issue repeatedly under overlapping categories.

## Methods and information flow

| Method | Fixed task |
| --- | --- |
| Generalist | One general reviewer detects flaws in the original claim. |
| Fixed role | One qualitative-methods reviewer detects flaws in that claim. |
| All roles | General, methods and domain reviewers independently detect flaws; a predeclared merger retains and deduplicates their issue records without inventing evidence. |
| WarrantRoute | An initial reviewer and independent evidence scout inspect the fixed claim; routed challengers verify issues; the loop refines the diagnosis, not the original claim. |

Prompts are method-specific but identical across tested model families. All
semantic roles within a model condition use that tested model. Formatting,
routing and identity checks are code, not additional independent brains.

For WarrantRoute, keep original-claim findings separate from later diagnostic
revisions. A revised allegation must still target the original claim hash.
Claim repair, if explored later, is a separate endpoint and may not redefine
the item being scored. Internal checks and human escalation do not themselves
establish a true positive.

Historical reviewer runtime and flag mappings are reusable starting points,
not a ready implementation of this protocol. In particular, the historical
claim-revision loop must not be invoked unchanged as a diagnosis-refinement loop.
Historical All roles label-union scores are not fresh matched baselines.

## Development and Playbook adaptation

Use a fixed development order, split and feedback policy declared before any
new inference. Never use an evaluation packet's reference answer or judge
feedback to update the Playbook, prompts, routes or thresholds.

For each development packet:

1. Predict flaws with the current Playbook before observing its feedback.
2. Persist the input, claim and Playbook hashes and the complete prediction.
3. Obtain allowed development feedback under the frozen reference policy.
4. Have the merged Reflector/Curator (Playbook Updater) propose reusable lessons
   about missed flaws, unsupported allegations or confused categories.
5. Validate each proposed change and retain accepted and rejected deltas with
   their provenance. Update only for future development items.

A rule records trigger, evidence check, decision rule, exception, flaw category,
role/corpus scope, provenance and version. Rules may become more specific about
procedures, but must not memorize claims, source text, answers or item IDs.
Keep seed safeguards immutable, resolve contradictions explicitly, bound memory
and retrieval, and never force nonempty changes. Model-based feedback remains
model-based diagnostic supervision, not independent ground truth. Human approval
requirements for confirmatory semantic rules are not bypassed.

Before calling a development outcome a miss or a false allegation, verify that
the feedback/reference supports that classification. Intended labels alone
cannot certify additional allegations as false or the target as truly present.

Memory is isolated by corpus and model. CaChe's previously authorized
within-source diagnostic permits shared source groups, not repeated records or
exact text across development and evaluation. Other corpus splits remain
source-disjoint where verified. Disclose prior exposure for every corpus.

## Learning-curve comparison

Measure progress against development experience, not elapsed wall-clock time.
Save immutable Playbook checkpoints P0, Pk1, Pk2 and so on. Snapshot order and
evaluation schedule must be frozen before running.

For the previously proposed 20-development-item budget, the prospective schedule
is P0, P5, P10, P15 and P20. This is a design default, not a claim that all those
claim-review items are eligible. If the approved development pool is expanded,
predeclare a new schedule, such as every 50 development items, before execution.
Do not select checkpoints after inspecting evaluation scores.

Run every checkpoint against the same 100-item panel per eligible corpus/model,
with learning disabled and no cross-item evaluation memory. Final panel feedback
is isolated from development. Prefer batch evaluation of all snapshots after
development finishes; live checkpoint reporting is observational only and must
not trigger tuning or early stopping. A separate unseen final panel is required
before making confirmatory claims after exploratory inspection.

Primary Playbook control: WarrantRoute P0 versus WarrantRoute Pk with identical
agents, prompts, routing, decoding limits, input order and references. Reuse
the same valid P0 result only under an exact identity contract. This controls
for the loop itself. Compare Generalist, Fixed role and All roles on that same
panel with no adaptation. Freeze decoding seeds and sampling settings; separate
replicates are not currently authorized.

Later development batches can be easier or harder. Their raw hit-rate trend
alone does not establish learning. Same-panel paired checkpoint differences are
needed to distinguish Playbook changes from changing sample difficulty.

An online test-then-learn stream is a separate design. In that design, score
each new item before exposing its feedback, never retroactively improve its
score, and compare against a frozen-Playbook control on the same stream.
Do not mix online adaptation and held-out panel evaluation under one label.

## Metrics and matching

Primary evidence-grounded recall requires a validated reference inventory.
A true positive must match the reference issue's location, material failure
and evidential basis under a frozen semantic matching rule, not category
membership alone. Enforce one-to-one matching and deduplicate allegations.

- Report TP and reference-positive count N separately from technical and
  unresolved cases. Show assessed and planned reference coverage.
- Precision/F1 require adjudication of extra allegations; a missing reference
  label is not proof of a false positive with an incomplete inventory.
- False-positive rate requires validated no-flaw items. Do not invent TNs for
  a bank consisting of intended-flaw packets.
- If only intended labels are available, report intended-target recall as a
  secondary diagnostic and disclose the flag-all vulnerability.
- Credibility assesses whether the review's diagnosis correctly characterizes
  the claim-evidence problem; Conformability assesses evidence grounding and
  preservation of context. Use a review-quality rubric, not the TA-generation
  code/theme rubric. These are auxiliary judge outcomes, not detection truth.
- Retain T/F/U/technical/pending counts with each judge percentage. Do not retry
  unknown or unfavorable scores. A fixed local judge is not an independent
  human expert and may have model-family bias.

Report per-corpus/model learning curves, fixed-initial versus final checkpoint
differences, per-flaw-category outcomes, unsupported-allegation counts, abstention,
technical failures, calls, tokens and time. In paired uncertainty analyses,
resample source components while retaining all methods/checkpoints together.
Repeated measurements on the same items are not independent samples. Do not
choose the best-performing checkpoint or guarantee monotonic improvement.

## Budget and output structure

With 100 evaluation items per corpus and five checkpoints, the proposed design
has 6,000 WarrantRoute panel trajectories and 3,600 non-adaptive baseline outputs:
9,600 outputs before development and auxiliary judging. The main 48-row table
would use the predeclared final checkpoint for the 12 WarrantRoute rows and the
36 fresh baseline rows. Store the full checkpoint curves separately.

This is not the previous 4,800-output workload. Neither its 225-hour ETA nor the
earlier GPT cost estimate applies unchanged. Recalculate after an eligible
claim-review pilot. No paid API calls are authorized by this correction. The
existing USD 100 cumulative spending cap remains mandatory if API execution is
subsequently authorized, with pre-call reservation as well as usage tracking.

Use a new claim-detection run directory, manifest and export namespace. Do not
overwrite the historical n100 tables, TA run artifacts or manuscript. Keep
interrupted requests auditable and do not blindly resubmit ambiguous calls.

## Required work before launching

These checks are not yet complete:

- Inventory eligible claim/evidence packets, development/evaluation overlap,
  nested construction hints, reference annotations and no-flaw controls.
- Freeze the taxonomy, reference provenance, feedback access policy, matching
  rules, checkpoint counts and budget. Choose diagnostic versus confirmatory
  claims according to actual reference quality, not desired table completion.
- Implement original-claim-only diagnosis refinement, adaptive rule updates,
  immutable snapshot replay, exact-identity baselines and read-only evaluation.
- Test answer-key isolation, span validation, one-to-one matching, false-alarm
  handling, unknown denominators, failed/in-flight calls, checkpoint identity,
  immutable seeds and no evaluation-to-development feedback path.
- Run a separately labeled local development pilot and report actual token
  cost, failure rates and timing before enqueueing the long experiment.
- Replace the paused TA monitor only after the new run exists and its command,
  denominators, reference policy, costs and ETA are verified.

## Correction record

The source-only TA v6 worker (PID 78491) was stopped with SIGTERM following the
user's objective correction. Its screen session ended. The associated
`warrantroute-ace-ta-progress` heartbeat was paused. No artifacts were deleted,
no original reviewer output was overwritten, and no new API request was made.

Read-only snapshot at 2026-09-09T07:51:21Z: 31 processed development episodes,
29 structurally completed and two technical failures; no completed evaluation
result. The first Generalist evaluation request remained recorded as in flight
when interrupted. That record is ambiguous, not a completed result or an
invitation to retry. Existing TA quality percentages do not answer claim-flaw
detection or Playbook learning-curve questions.
