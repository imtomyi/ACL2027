# Direction H analysis plan

Analysis version: `direction-h-analysis-v1`  
Date: 2026-08-25 (America/Chicago)  
Status: prospective. This file defines estimands and reporting rules; it contains
no ratings or results.

## 0. Live Direction J analysis amendment (controlling)

The selected pilot population is Charlie's exact 24-item Direction J assignment,
not the older four-item full-output rehearsal. One rating item is one
`direction-j-evaluator-item-v1`; one shared rating is the unchanged
`direction-j-shared-rating-v1` object. Pair human and LLM observations on the
complete 12-field signature in `companion_alignment.md`. Do not project these
records into `qc-paper-metrics-v1` or pool them with `DHQ-*` records.

The selected downstream ITT population is every independently post-lock
verified defective Direction J item with a complete locked Charlie feedback
record, including Charlie misses. Each item is allocated once to both active
self-revision arms under the same frozen model/runtime, with null versus exact
Charlie feedback as the only model-visible difference. The primary estimand is
the finite-manifest paired mean difference in independently established
`successful_repair_without_collateral_error`; allocated pipeline failures have
established success zero. Target repair, accurate-material preservation,
collateral errors, and independent review time are reported separately.

Human no-feedback detection is undefined. Charlie's detection is compared only
with independently verified synthetic target flags, while the revision model's
truth-blind diagnosis may be compared across arms as a secondary mechanism
outcome. Charlie remains a separate developer-case row. All later references to
the four-item live manifest, `qc-paper-metrics-v1` pairing, post-revision paper
metrics, or the old full-output revision pipeline apply only to the inactive
internal rehearsal unless explicitly reactivated in a new non-overlapping
phase.

## 1. Analysis principles

1. Separate defect detection from downstream repair.
2. Score controlled-item detection against a label frozen before rating, not
   against fluency, agreement, or an evaluator's confidence.
3. Compare repair under Charlie feedback with repair under no external feedback
   using the same frozen revision process; separately compare the frozen revision
   model's explicit target diagnosis as a secondary mechanism outcome.
4. Treat Charlie as one fixed developer-researcher case. His item sample can
   support a finite-manifest case description, not a population estimate for
   researchers.
5. Preserve the three ordinal paper metrics, abstention, disposition, error
   flags, confidence, rationale, and time as distinct observations.
6. Do not combine evidential credibility, voice-and-boundary preservation, scope
   calibration, and plural-reference coverage into an omnibus score.
7. Retain all preregistered repeats and all locked ratings. Never select the best
   output, reviewer, revision, or adjudication after inspecting quality.
8. Report counts and denominators before percentages, effect sizes before
   significance claims, and pilot results before any confirmatory interpretation.

The shared measurement definitions in
[`qc-paper-metrics-v1`](../../qualitative_coding_baselines/protocol/paper_metric_data_contract.md)
control whenever this plan is silent.

## 2. Analysis units and keys

### 2.1 Base packet

A `base_packet_id` identifies the source evidence and underlying proposed
interpretation before a controlled transformation. Clean and defective twins
share a base packet. The base packet is the clustering and pairing unit; twins
are never treated as independent source observations.

### 2.2 Rating item

A rating item is the immutable pair identified by `packet_id` and `output_id`.
Human and companion LLM records must use exactly the same values. One canonical
human rating is one `qc-paper-metrics-v1` record for one rater and item.

### 2.3 Feedback unit

A feedback unit is a `direction-h-feedback-v1` record authored after the
canonical rating answers have been completed and frozen in-session. The
collector does not let Charlie revisit them while eliciting feedback, then
validates both records before a rollback-aware, no-overwrite atomic pair commit;
the study validator refuses any unmatched rating or sidecar as an
apparently complete observation. The sidecar links to the immutable rating
through its exact `rating_key` and record hash. It is not a second rating. The projection from the locked feedback record
into the revision prompt is deterministic; the feedback
content itself is Charlie's observed intervention, not an automatic restatement
of numeric scores. Organizer annotations added later are not part of the
intervention.

### 2.4 Revision case and revision output

A revision case fixes one starting output, source packet, target-defect metadata,
and the two planned `feedback_arm` values. A revision output is one frozen-model
attempt within a revision case, feedback arm, and repeat index. The same starting
output may therefore yield paired no-feedback and Charlie-feedback outputs.

### 2.5 Repair assessment

A repair assessment is one independent adjudicator's judgment of one blind
revision output. Adjudicator ratings are repeated observations nested in the
revision output and crossed, where assigned, with base packet.

### 2.6 Post-revision shared rating

Every repair assessment has one separately stored, exact `qc-paper-metrics-v1`
rating of the same blind revised output by the same adjudicator. Its `output_id`
is the reviewer-safe `blinded_revision_id`; a Direction H link record binds the
rating and repair assessment by canonical hashes. R/P/C/Y remain only in the
repair assessment and are not folded into the three ordinal constructs.

These are post-revision artifact ratings in both experimental arms. Charlie's
earlier rating of a starting output is not a same-rater pretest for an independent
repair adjudicator and is not used to calculate within-rater change.

## 3. Analysis populations

The following populations must be reported separately.

### 3.1 Workflow-qualification population

All assigned synthetic items, including natural or otherwise unlabeled items.
This population supports schema completion, timing, abstention, usability, and
protocol-deviation summaries. It does not support target-defect accuracy unless
the item has a frozen, independently vetted label.

The live pilot manifest contains four reviewer-safe items: three intended
single-defect manipulations and one `no_planted_defect_control`. Those are
construction intentions, not analysis-ready truth. Agent or automatic QA is
workflow-only. Until a non-Charlie construction verifier confirms each intended
manipulation and the control status in a valid
`direction-h-construction-verification-v1` record, all four remain only in this
population. The verifier cannot inspect Charlie's responses before locking that
record.

### 3.2 Controlled-detection population

All single-defect synthetic variants and no-planted-defect controls that passed
independent construction verification. Items with multiple material defects,
unresolved construction disagreement, a broken blind, or a label created after
Charlie's rating are excluded from target-family detection and listed with
reasons. They remain in workflow accounting when a valid rating exists.

### 3.3 Repair intention-to-treat population

All preregistered defective revision cases, regardless of whether Charlie
detected the defect, abstained, requested escalation, or supplied effective
feedback. This is the primary downstream population.

### 3.4 Detected-defect mechanism subset

Defective cases on which Charlie selected the matching target-family flag. This
subset may explain how actionable feedback operates, but it is post-selection on
the reviewer response and cannot replace the intention-to-treat repair analysis.

### 3.5 No-planted-defect control and clean-output safety populations

`no_planted_defect_control` means that no manipulation was intended. It does not
mean that the source output is universally error-free. Report it as a control
flag case after construction verification. Call it a clean-output safety item or
use it for a false-positive/specificity analysis only if an independent verifier
also records that no material rubric-defined defect is present under the declared
contract. If such verified controls are sent through revision, analyze them
separately; the outcome is preservation without a new material error, not
"repair."

### 3.6 Confirmatory independent-reviewer population

Eligible, protocol-complete ratings and feedback from reviewers who satisfy the
independence requirements in `governance_and_blinding.md`. Charlie is excluded
from this population and displayed as a separate case baseline.

## 4. Frozen defect labels and primary detection rule

Let `Z_i` be the private verified controlled status of item `i`: a single target
defect or `no_planted_defect_control`. Let `F_i` be the set of serious-error flags
in the locked rating. The primary target flag is frozen with the item before
rating:

| Controlled family | Primary matching `serious_error_flags` value |
|---|---|
| Unsupported evidence-to-claim link | `unsupported_inference` |
| Broad wording supported by concentrated sources | `hidden_source_concentration` |
| Removed contradiction, exception, or boundary case | `lost_negative_case` |
| Erased consequential context or situated meaning | `contextual_flattening` |
| Claim broadened beyond participant/group/corpus evidence | `unsupported_abstraction` |
| Altered or fabricated quotation integrity control | `fabricated_or_altered_quote` |
| Wrong source or speaker integrity control | `wrong_attribution` |
| Unwarranted sensitive or diagnostic inference control | `sensitive_or_diagnostic_inference` |
| Internally inconsistent or unusable codebook control | `inconsistent_codebook` |

An item with target flag `f_i` is detected in the primary analysis when

`D_i = 1[f_i is in F_i]`.

A rationale that describes the problem without selecting the canonical flag is
not a primary target-family detection. It is reported as a flag/rationale
discordance and may enter a blinded secondary coding of rationale content. An
`other` flag is not retroactively mapped to the expected target after unblinding.
If an `other` mapping is scientifically necessary, independent coders must apply
a rule frozen before the private label map is opened.

For a verified no-planted-defect control, define the descriptive control flag
indicator

`G_i = 1[F_i is not empty]`.

`G_i` is not automatically a false positive: Charlie may identify a material
natural defect that was not planted. Only when an independent construction
verifier also confirms that the control has no material rubric-defined defect may
the frozen plan relabel `G_i` as `FP_i` for a controlled false-positive analysis.
Even then, the label is contract- and packet-relative, not a claim that the output
is universally clean.

Disposition-based defect interception is secondary:

- `revise` or `reject` counts as a material-problem decision;
- `accept` counts as no material problem; and
- `escalate` remains a separate referral/abstention decision unless accompanied
  by a matching target flag.

This preserves the distinction between detecting a defect and recognizing that
the supplied evidence or one's expertise is insufficient.

## 5. Pilot detection estimands

### 5.1 Target-family detection rate

For the fixed defective manifest `I_defect`, the Charlie case estimand is

`p_detect,C = sum(D_i) / |I_defect|`.

Report the numerator and denominator overall and by defect family. This is a
finite-manifest description of Charlie's reviews. Any interval reflects item
sampling or clustering assumptions only; it does not represent uncertainty over
a population of human researchers.

### 5.2 No-planted-defect control flag rate

For the fixed, independently verified no-planted-defect manifest `I_control`,
report

`p_control_flag,C = sum(G_i) / |I_control|`.

The live pilot contains one intended control, so show its item-level flags and
disposition rather than implying a stable rate or specificity estimate. If and
only if independent verification confirms no material rubric-defined defect,
also report the predeclared controlled false-positive indicator/rate. Do not
subtract it from sensitivity and call the result qualitative quality.

### 5.3 Descriptive discrimination contrast

After independent verification, the descriptive pilot contrast is

`Delta_flag,C = p_detect,C - p_control_flag,C`.

This contrasts target-family detection on the intended single-defect items with
serious flags on the no-planted-defect control. It is not specificity, a
Charlie-versus-no-feedback comparison, or a population treatment effect.

### 5.4 Additional detection summaries

Report, without replacing the primary rule:

- exact flag confusion counts by controlled family;
- any-serious-error sensitivity and, only with independently verified
  no-material-defect controls, controlled specificity;
- accept/revise/reject/escalate distributions;
- per-construct `cannot_judge` counts;
- ordinal score distributions for all three constructs;
- confidence by correct versus incorrect target detection;
- flag/rationale discordance; and
- review time overall and by family.

The synthetic pilot is too narrow to interpret agreement or high confidence as
validity.

## 6. Human detection is not compared with no feedback

`no_feedback` has no human rating and therefore no observable human detection
decision. Assigning it a detection rate of zero would create a structural and
uninformative comparison; calling detection undefined and then imputing it would
be equally misleading.

Accordingly:

- Charlie's detection is evaluated against independently verified planted labels
  in the synthetic pilot;
- natural-item detection is evaluated only against a later independent,
  contract-relative panel; and
- no Charlie-versus-no-feedback **human** detection rate is reported.

The frozen revision model is different. Its output schema requires a truth-blind
`revision_diagnosis` in both `charlie_feedback` and `no_feedback`, so a paired
model target-diagnosis contrast is defined below. That mechanism measure does not
retroactively create a human detection response for the no-feedback arm.

A system-level descriptive endpoint may combine interception and repair, but its
components must remain visible and its two arms must still use the paired frozen
revision process below.

## 7. Repair outcomes and estimands

### 7.1 Frozen revision-model target diagnosis

For each verified target-defect item `i`, feedback arm `c`, and revision repeat
`k`, let

`M_ick = 1[f_i is in revision_diagnosis.detected_error_flags]`.

Here and throughout the repair analysis, the fixed revision denominator contains
exactly the committed `controlled_defect` tasks with itemwise construction
disposition `verified_for_detection`. Controls, `workflow_only` tasks, and
rejected tasks remain in private exclusion accounting; neither an overall
construction disposition nor a control-item disposition vetoes a different
eligible target. This eligible set and the exact arm-blind assessment-brief hash
are committed before case creation or model invocation.

The secondary paired mechanism estimand is

`Delta_model_detect = mean_i,k(M_i,charlie_feedback,k - M_i,no_feedback,k)`.

Also report discordant pairs and target-diagnosis counts by failure family. A
null `revision_diagnosis` from a failed or unusable model completion is missing,
not a nondetection; report completion and evaluable denominators by arm and do
not select replacement attempts outside the frozen retry rule.

Because `direction-h-feedback-v1` may explicitly carry Charlie's canonical error
flag and finding, the Charlie-arm diagnosis is not an independent model discovery.
`Delta_model_detect` measures whether structured human feedback is transferred
into the frozen model's explicit diagnosis. It is secondary to the repair
estimand and cannot substitute for independent repair assessment.

### 7.2 Component repair outcomes

For item `i`, feedback arm `c`, revision repeat `k`, and adjudicator `a`, use the
exact repair-assessment fields:

- `R_icka = target_defect_repaired`;
- `P_icka = accurate_relevant_material_preserved`;
- `C_icka = collateral_error_present`; and
- `Y_icka = successful_repair_without_collateral_error`.

The repair schema enforces `Y = true` exactly when `R = true`, `P = true`, and
`C = false`; it is false when a known component defeats success and otherwise
null. Dimension-specific adjudicator abstention uses those three component names
in `cannot_judge`. The assessment contains only `blinded_revision_id`, never a
feedback-arm field; the arm is joined from the private revision map after
assessment lock.

The three component rates are mandatory. A fluent rewrite or higher mean ordinal
score does not count as a repair when the target persists. A target fix does not
count as successful when it creates a collateral error.

For every assessment-level R/P/C/Y record, retain the separately linked exact
`qc-paper-metrics-v1` row. Report evidential credibility, voice-and-boundary
preservation, and scope calibration separately. The post-revision metric rows
support arm comparisons of revised artifacts; they do not turn Charlie's
starting-output rating into a same-assessor change score.

### 7.3 Primary Charlie repair estimand

The primary outcome is **pipeline-level established successful repair**, so a
revision case cannot disappear from the denominator merely because the frozen
model failed to deliver an assessable output. For item `i`, feedback arm `c`, and
preregistered repeat `k`, define `S_ick = 1` only when:

1. the frozen retry policy yields a complete, schema-valid, hard-gate-passing
   revision; and
2. the prespecified arm-blind panel decision establishes `Y = true`.

Set `S_ick = 0` when no eligible completion is delivered or when the locked
panel process does not establish all three success components. This is an
operational *established-success* endpoint, not an imputation that the content
of a missing or `cannot_judge` revision is defective. Report technical failure,
unusable completion, assessor `cannot_judge`, and panel-disagreement counts by
arm so the reasons for non-established success remain visible. Also report an
assessment-level sensitivity analysis restricted to eligible, judgeable outputs
using the unmodified `Y` values and its evaluable denominator.

For the fixed defective manifest, first average preregistered repeats within
each item and feedback arm. The primary paired case estimand is

`Delta_repair,C = mean_i(S_i,charlie_feedback - S_i,no_feedback)`.

The intervention is the exact as-collected identity-free `model_feedback`
projection from Charlie's locked sidecar; the outer linkage/status fields are
retained for audit but not sent to the model. Every preregistered defective item,
including items Charlie missed and revision cases without an eligible
completion, remains in this pipeline-level mean. The corresponding marginal
probabilities, paired item counts, delivery rates, and assessment-level `Y`
results must accompany the difference.

### 7.4 Required repair contrasts

Report the paired differences for:

- pipeline-level established successful repair (`S`, primary);
- assessment-level successful repair without collateral error (`Y`, eligible
  and judgeable outputs);
- target repair (`R`);
- preservation of accurate/relevant material (`P`);
- any collateral error (`C`);
- each preregistered collateral-error family;
- paired post-revision difference between feedback arms in evidential credibility;
- paired post-revision difference between feedback arms in voice-and-boundary
  preservation; and
- paired post-revision difference between feedback arms in scope calibration.

Post-revision ordinal arm differences are secondary and construct-specific. No
average quality index and no Charlie-original-to-independent-adjudicator change
score are permitted.

### 7.5 System-level interception-and-repair endpoint

A secondary workflow endpoint is the proportion of planted defective items that
end without the target defect and without collateral error after the assigned
pipeline. In the Charlie arm, this naturally includes whether his actual feedback
was useful; in the no-feedback arm, it captures spontaneous self-repair. Report
the original detection and revision components next to this endpoint so it does
not conceal where the pipeline succeeded or failed.

### 7.6 Additional mechanism analyses

Within the detected-defect subset, describe whether a matching flag, lower
ordinal dimension, revision disposition, requested expertise, or source-linked
rationale is associated with successful repair. These analyses are exploratory.
They cannot establish that a rationale feature caused repair because the content
was not randomized within Charlie's feedback.

## 8. Pilot statistical summaries

The pilot has one human reviewer. Primary reporting is therefore item-level and
descriptive:

- counts/denominators and paired differences;
- an item-by-condition outcome table with blind identifiers;
- defect-family stratification;
- median and interquartile range for review seconds;
- all exclusions and protocol deviations; and
- adjudicator disagreement before any adjudication.

If intervals are reported, use a base-packet cluster bootstrap or an exact method
appropriate to the prespecified finite item sample. State explicitly that the
interval does not capture human-reviewer sampling. Do not use isolated pilot
`p`-values, fit a reviewer random effect to one reviewer, or describe pilot
estimates as confirmatory.

## 9. Item-level comparison with the companion LLM rater

Only records with matching `packet_id`, `output_id`, task version, evidence hash,
and construct definitions are paired. Comparisons are diagnostic; neither rater
is treated as truth by agreement alone.

For Charlie versus each frozen companion LLM rater, report:

- 1--5 rating pairs and signed differences for each of the three constructs;
- exact agreement and ordinal weighted agreement by construct when the number of
  items supports it;
- dimension-specific cannot-judge discordance;
- disposition cross-tabulations;
- target-flag sensitivity and the no-planted-defect control flag result against
  the same independently verified private labels;
- paired target-detection discordance counts and risk difference;
- serious-error-flag overlap by family;
- confidence distributions and confidence/correctness tables; and
- human review seconds and model latency/cost as separately defined resource
  measures.

Do not treat human seconds as model latency, Charlie time as specialist expert
minutes, or a same-vendor LLM judge as independent adjudication. A McNemar test
may be used for a prespecified binary paired endpoint when the confirmatory sample
contains enough discordant pairs; the pilot should show the discordant counts
instead of overinterpreting a small-sample test.

Rationale comparison is a bounded qualitative diagnostic performed after the
confirmatory quantitative fields are frozen. It may identify differences in
source citation, omission, uncertainty, and requested expertise, but it cannot
change the target label or primary endpoint.

## 10. Confidence, abstention, and time

### 10.1 Confidence

The 1--5 confidence rating describes confidence in the review judgment, not
output quality. Pilot reports show correctness by confidence level. A Brier score
or expected calibration error requires a probability mapping and binning rule;
those rules must be fixed after an independent pilot and before confirmatory
analysis. Do not retrospectively map 1--5 values to favorable probabilities.

### 10.2 Cannot judge

`cannot_judge` is per construct. It is neither a midpoint nor a quality failure,
and its denominator is reported separately. Confidence remains required because
the canonical schema treats reviewer certainty as separate from construct
evaluable status. An escalation may accompany cannot-judge without being scored
as target detection unless the matching error flag is also present.

### 10.3 Review time

Report review time in seconds from first display of the complete rating item
through completion of the canonical rating rationale. The timer stops before
feedback-sidecar prompts, so feedback authoring is not included. Flag, rather
than silently trim, sessions affected by an interruption or inactive-browser threshold.
Charlie time is researcher time. The WarrantRoute manuscript's matched
`expert_minutes` outcome applies to scarce specialist review and must not be
relabeled to absorb Charlie's time. A Direction H resource table may separately
show researcher minutes, specialist minutes, model latency, and model cost.

## 11. Confirmatory analysis

### 11.1 Primary independent-human estimands

The confirmatory primary estimands are defined over the preregistered item sample
and eligible independent-researcher population:

1. target-family defect-detection probability and, for independently verified
   no-material-defect controls, controlled false-positive probability;
2. the average effect of independent-researcher feedback versus no feedback on
   successful repair without collateral error; and
3. the collateral-error risk difference between those revision arms.

The reference for natural-item detection is an independent panel under the
declared analytic contract. It is described as panel- and contract-relative, not
universal ground truth.

### 11.2 Models

Subject to the preregistered simulation and convergence plan:

- target detection uses a logistic mixed model with controlled status/failure
  family and relevant prespecified interactions, with crossed random intercepts
  for reviewer and base packet;
- post-revision ordinal artifact ratings use separate cumulative-link mixed
  models for each construct, with feedback arm as a fixed effect and reviewer
  and base-packet random effects; these are arm contrasts, not pre/post changes;
- successful repair and collateral error use separate logistic mixed models with
  feedback arm, failure family, and their prespecified interaction, with
  random intercepts for base packet, adjudicator, and feedback author where the
  assignment supports them; and
- review time uses a preregistered log-linked model after applying the frozen
  interruption rule.

Report effect sizes, predicted probabilities, and 95% uncertainty intervals.
Fallback models, collapsed random effects, and convergence failures are disclosed
rather than silently changed.

### 11.3 Reliability and disagreement

Within-role ordinal Krippendorff's alpha, Gwet's AC2, and raw agreement are
measurement diagnostics, not proof of validity. Report them with intervals and
score prevalence. Preserve individual judgments before adjudication, label
persistent reasoned disagreement as plural/ambiguous when warranted, and audit
both high-agreement errors and productive disagreements.

### 11.4 Multiplicity, margins, and power

The independent-human pilot supplies variance components and completion-time
distributions for simulation. Charlie alone cannot. Before held-out evaluation,
freeze:

- the primary contrast order;
- family-wise or false-discovery multiplicity handling;
- the smallest effect of scientific interest;
- any noninferiority margin for collateral error or expert comparison;
- item and reviewer counts and ratings per item;
- budget points and stopping rules; and
- all exclusions and model fallbacks.

No margin or sample size may be selected after inspecting held-out outcomes.

## 12. Validation, missingness, and exclusions

Before analysis, validate:

- all JSON records against their declared schemas;
- uniqueness and one-to-one links among assignment, rating, feedback, revision
  case, revision output, and repair assessment;
- exact match of packet/output identifiers and evidence hashes across human and
  LLM arms;
- an independent `direction-h-construction-verification-v1` record for every item
  entering a detection or control analysis;
- a post-lock `direction-h-blinding-debrief-v1` record and the frozen handling of
  recognized/exposed items;
- absence of private labels from reviewer-visible records and model prompts;
- the revision-freeze manifest hash;
- completeness of both paired revision arms and all preregistered repeats;
- absence of `feedback_arm`, feedback content, revision diagnosis, and private
  truth from every `direction-h-repair-panel-item-v1` object; and
- consistency of cannot-judge nulls with the canonical rating schema.

Schema-invalid or incomplete records are never silently repaired. Apply only a
predeclared format-only correction, retain the original, log the correction, and
exclude the record from endpoints whose required value is unresolved. Missing
paired revisions are not replaced with the better available arm. Report
attempted, completed, valid, excluded, and analyzed counts by feedback arm.

## 13. Reporting shell

Until data exist, every value remains `TO REPORT`; do not insert demonstrations
that resemble results.

| Population / reviewer | Items n/N | Target detection n/N | Control serious flags n/N | Cannot judge n/N | Median review seconds |
|---|---:|---:|---:|---:|---:|
| Charlie synthetic case | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |
| Independent researchers | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |
| Companion LLM rater | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |

| Revision condition | Cases n/N | Model target diagnosis n/N | Target repaired n/N | Preserved n/N | New collateral error n/N | Successful repair without collateral error n/N |
|---|---:|---:|---:|---:|---:|---:|
| No external feedback | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |
| Charlie feedback | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |
| Independent-researcher feedback | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT | TO REPORT |

The synthetic case table and confirmatory table remain separate. Every caption
must identify the dataset status, evaluator role, denominator, clustering unit,
interval method, feedback/revision freeze version, and whether the result is
workflow qualification, development, audit, or confirmatory.
