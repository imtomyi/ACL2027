# Direction J analysis plan (`direction-j-analysis-v1`)

This is a prospective real-data plan. No fictional or synthetic run is
authorized, and no empty result shell is evidence. Dreaddit development/audit
and AGYW confirmatory estimates must remain separate.

## 1. Analysis units and pairing

The atomic comparison is an immutable `item_id` with an identical evaluator
input hash. The clustering hierarchy retains base packet, source/document or
speaker cluster, candidate generation run, and rater/model repetition. Charlie,
the primary LLM, sensitivity LLM, and independent humans are separate actors.

Primary LLM analyses use repetition 1. Repetitions 2--3 form the prespecified
stability analysis and secondary ensemble. Repeats are not independent items.
All results are stratified by corpus/evaluation role, natural versus controlled
status, failure family, severity, model family, and workflow when those private
fields are available after lock.

## 2. Reference outcomes

Independent experts submit the same three quality ratings and response fields
before seeing any first-stage label. Individual ratings are reported before
adjudication. Adjudication creates a contract-relative action:

- `accept`: no material issue requiring action;
- `expert_review`: a material/high-consequence error or specialist action is
  required; or
- `plural_ambiguous`: multiple defensible readings must remain visible.

The primary correctness target for confidence is frozen as follows:

- first-stage `accept` is correct only for adjudicated `accept`;
- first-stage `revise`, `reject`, or `escalate` is correct for adjudicated
  `expert_review`; and
- only first-stage `escalate` is correct for `plural_ambiguous`.

This binary indicator evaluates the first-stage pass-versus-needs-action
decision. A separate routing target asks whether an item that truly needs
specialist input was explicitly escalated. Planted-control truth measures only
detection of the planted manipulation and is never substituted for the full
expert adjudication.

## 3. Agreement and ordinal ratings

For Charlie versus primary LLM and for each actor versus each independent human
role, report item-paired:

- exact and within-one agreement for each ordinal construct;
- quadratic-weighted kappa with cluster-bootstrap intervals;
- the full paired cross-tabulation and signed difference distribution;
- exact disposition agreement and agreement after the declared
  pass/needs-action collapse;
- per-flag positive agreement and Jaccard similarity for serious-error sets;
  and
- abstention/escalation agreement.

For three or more humans, report ordinal Krippendorff alpha and Gwet AC2 with
cluster-bootstrap intervals, plus prevalence and raw agreement. Never call the
highest-agreement actor the most valid without the independent error and task
outcomes below.

The three quality constructs remain separate. Adequacy is the proportion of
evaluable ratings at 4 or 5 for each construct. `Cannot judge` has its own
denominator and is never recoded to a midpoint or failure. No omnibus score is
permitted.

## 4. Serious-error detection and false acceptance

Against locked expert adjudication, report for each serious-error family:
precision, recall, F1, false-positive rate, and item-level paired differences.
The confirmatory serious-error endpoint is recall for material or
high-consequence errors. High-severity failure recall is reported separately.
Do not infer severity from a nonempty flag; use the adjudicated severity field.

`False acceptance` is a first-stage `accept` on an adjudicated
`expert_review` or `plural_ambiguous` item. Also report false rejection and
unnecessary escalation. Qualification-control recall uses the planted family
as a manipulation check and is labeled synthetic/sentinel performance.

## 5. Calibration, abstention, and selective risk

Map confidence levels to probabilities with the frozen identity mapping
`p = confidence / 5`. Evaluate against the primary correctness target using:

- Brier score;
- expected calibration error with the five fixed confidence levels as bins;
- reliability tables/plots with counts and cluster-bootstrap intervals; and
- log loss as a secondary metric, clipping probabilities only for computation
  at `[0.001, 0.999]` and disclosing that transformation.

Report selective risk as items are retained from confidence 5 down to 1.
Coverage is the proportion automatically acted on rather than sent to a
specialist. Show false acceptance and high-severity miss risk at every coverage
point. A system cannot appear safe merely by escalating almost everything.

Dimension-specific `cannot_judge`, explicit escalation, requested expertise,
appropriate escalation, unnecessary escalation, and failure to escalate a
`plural_ambiguous` item are separate outcomes.

## 6. Repetition stability and cross-family sensitivity

For the primary LLM's three calls, report per-item range and modal agreement for
each construct/disposition/flag, the fraction with any material decision change,
and the first-repeat versus ensemble outcome difference. Do not choose the
repeat closest to experts.

Repeat the primary descriptive and expert-reference analyses for
`gemini-2.5-pro`. Report differences, not a winner ranking. Compare the new
family-disjoint judges with the historical overlapping GPT judge panel only in
a clearly labeled legacy sensitivity appendix because the old prompt,
information set, and response schema are non-equivalent.

## 7. Rationale usefulness

A separate blinded expert assesses each rationale, without actor identity, on:

1. source localization;
2. diagnostic correctness relative to the locked adjudication;
3. actionability for a bounded revision; and
4. preservation of defensible ambiguity and accurate material.

Each is 1--5 or dimension-specific `cannot_judge`; no omnibus usefulness score
is primary. Report each dimension and the expert's binary
`safe_to_send_to_revision` decision. Length, grammaticality, or confidence is
not treated as usefulness. The task-linked usefulness outcome is successful
repair without collateral error.

## 8. Cost and latency

For every model call retain wall-clock latency, input/output/cached/reasoning
tokens when exposed, retries, provider/model/version, request/response ID,
finish/filter state, and billed unit prices captured at run time. For humans,
retain active review seconds using the preregistered inactive-browser rule and
the compensation or loaded-hourly-cost basis approved for the study.

Report median, interquartile range, tail latency, and total cost per initial
decision; expert verification minutes; cost per correctly detected
high-severity error; and total cost/time per successful repair. Legacy records
with unavailable usage/latency/cost remain missing and are not imputed.

## 9. Downstream repair

On a separately frozen defective-item sample, a single revision model, prompt,
settings, and feedback formatter receive one of: no feedback, Charlie feedback,
primary-LLM repetition-1 feedback, independent-expert feedback, or the
companion expertise-aware routed feedback. The revision model is not told the
planted condition or feedback source.

A separate blinded panel records:

- whether the targeted defect was repaired;
- whether accurate and relevant material was preserved; and
- each new unsupported claim, omission, distortion, attribution/quotation
  error, or newly lost boundary case.

`successful_repair_without_collateral_error` is true only when all three
conditions pass. Fluency, length, and a changed rating alone are not repair.
Use item-paired cluster-bootstrap intervals and the companion mixed model, with
feedback condition and failure family fixed effects and base-packet and
adjudicator intercepts. The repair panel cannot assess its own feedback.

## 10. Missingness, exclusions, and inference

Schema failures, safety refusals, truncation, timeouts, and format repairs are
reported separately. A persistently invalid model response is an operational
escalation and a task failure; it is not silently dropped from error/coverage
denominators. Construct agreement is undefined for missing dimensions and uses
the declared evaluable denominator.

Qualification outputs are descriptive engineering checks only. Pilot variance
and timing determine confirmatory sample size and noninferiority margins before
held-out access; this protocol does not invent them. Confirmatory uncertainty
uses cluster bootstrap or the companion mixed models, preserving base packet,
source/speaker, rater, and generation-run blocks. Report effect sizes and 95%
intervals, not isolated p-values.
