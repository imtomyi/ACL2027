# Direction H study protocol: researcher in the annotation and feedback loop

Protocol version: `direction-h-study-v1`  
Date: 2026-08-25 (America/Chicago)  
Status: prospective; the selected synthetic pilot requires qualification and a
non-Charlie activation after local manifests validate.
No human ratings, revision outcomes, or empirical results are reported here.

## 0. Live Direction J reconciliation amendment (controlling)

The selected companion-compatible pilot is the 24-item Direction J browser lane
documented in `../CHARLIE_START_HERE.md` and
`../companion_j_bridge/browser/README.md`. It uses Direction J's exact
theme-and-evidence item bytes, shared guide, `direction-j-shared-rating-v1`
object, active-time rule, and complete pairing signature. The same locked
Direction H feedback sidecars feed only the same-unit theme revision extension
in `../companion_j_bridge/theme_revision/`.

The four-item `DHQ-*` full-output lane and `qc-paper-metrics-v1` procedures
below are retained as an internal workflow-rehearsal stratum. They are not an
item-level comparison with live Direction J and are inactive for Charlie's
selected phase. Where later sections call that four-item queue “the live pilot”
or describe its schema as the companion contract, this amendment and
`companion_alignment.md` control. No post-hoc mapping between the two units or
rating schemas is allowed, and Charlie may not run both overlapping queues in
one phase.

The research questions remain the same: detect a contract-relative defect, and
test whether Charlie's feedback improves downstream repair relative to active
self-revision with no external feedback. For the selected lane, detection is
matched only after independent post-lock construction verification; downstream
repair uses the exact Direction J item and `direction-j-repair-assessment-v1`
endpoint. Charlie remains a construction-involved developer-researcher case,
not independent human ground truth.

## 1. Purpose and relationship to WarrantRoute

Direction H establishes a researcher-in-the-loop baseline for WarrantRoute. A
researcher reviews a blinded theme-and-evidence packet, records the same
item-level judgments used in the companion LLM-as-rater direction, and supplies
structured feedback to one frozen revision model. The study asks two distinct
questions:

1. can the researcher detect a prespecified source-warrant defect; and
2. does the resulting feedback improve a downstream revision relative to the
   same revision process with no external feedback?

The task remains the bounded, codebook-oriented source-warrant task defined in
[`qc-analytic-contract-v1`](../../qualitative_coding_baselines/protocol/analytic_contract.md).
It is not an evaluation of a complete reflexive thematic analysis, a search for
one universally correct interpretation, or a participant-level decision system.
The WarrantRoute manuscript already separates artifact ratings, routing
outcomes, and successful repair without collateral error; Direction H preserves
that separation rather than adding a composite quality score.

## 2. The Charlie pilot is a developer-researcher case baseline

Charlie is the first reviewer in Direction H and is treated as a researcher for
task compatibility. He also helped develop the study. His pilot data therefore
have a deliberately narrow interpretation:

- Charlie is one `developer_researcher` case, not a sample of trained
  researchers.
- His judgments are observations, not universal human ground truth.
- His rating records use `evaluator_group = researcher` so they remain directly
  comparable at item level, while his development role and prior exposure are
  disclosed in the separate rater registry.
- His records are not pooled with independent-researcher estimates, used to
  estimate between-rater variance, used as an adjudication reference, or used to
  claim reliability or generalization.
- He may independently lock a rating before seeing any other rating, but he is
  not independent of study development. Reports may call his pilot
  **condition-blinded developer-researcher review** only when private-map access
  was technically separated; otherwise they must call it a **condition-masked
  developer-researcher review**. Neither is independent human validation.

The confirmatory extension replaces this single-case limitation with reviewers
who did not construct the items, choose the models or prompts, build the study
instrument, inspect the condition map, or adjudicate the revisions.

## 3. Compatibility contract

### 3.1 Shared task and evidence

Human and LLM raters must receive the same immutable, presentation-equivalent
rating unit. Each unit contains:

- the analytic question and analytic-contract identifier;
- one proposed theme or code-level interpretive claim and its explanation;
- the exact fictional or approved excerpts offered as evidence, with stable
  project source identifiers and bounded local context;
- the same source-coverage summary and supplied counterevidence or boundary
  information; and
- a blind packet/output identifier that does not reveal generator, run,
  condition, manipulation, or expected answer.

Raters may use only the supplied packet. Outside facts, web search, unpublished
reference themes, the private blind map, other ratings, and condition labels are
not admissible evidence. Presentation differences required for accessibility
must not change the substantive information available to either rater type.

The canonical keys for pairing are `packet_id` and `output_id`. The same values
must be used in Direction H and the companion LLM-as-rater direction. A private
item registry may map those blind identifiers to a base packet, generator, run,
and controlled label, but those fields cannot enter a rating prompt or rating
record.

### 3.2 Shared item-level rating record

Every Charlie or independent-human rating is validated directly against
[`paper_metric_rating.schema.json`](../../qualitative_coding_baselines/schemas/paper_metric_rating.schema.json)
with `annotation_version = qc-paper-metrics-v1`. Required observations are:

- `evidential_credibility` (1--5 or dimension-specific abstention);
- `voice_boundary_preservation` (1--5 or dimension-specific abstention);
- `scope_calibration` (1--5 or dimension-specific abstention);
- the per-construct `cannot_judge` array;
- reviewer `confidence` (1--5 even when one or more quality dimensions cannot be
  judged);
- `disposition` (`accept`, `revise`, `reject`, or `escalate`);
- all applicable canonical `serious_error_flags`;
- `review_seconds`;
- a nonempty source-grounded `rationale`; and
- `requested_expertise` when applicable.

No Direction H metadata may be added to that record because the shared schema
forbids additional properties. Charlie's development role and prior exposure
belong in a separately keyed record conforming to
`../schemas/rater_registry.schema.json` with
`registry_version = direction-h-rater-registry-v1`. His exact registry values are
`case_classification = developer_researcher_case_baseline`,
`helped_develop_study = true`,
`blinding_status = condition_masked_developer` in the v1 shared workspace; any
future `condition_blinded_developer` run requires a new frozen instrument plus
an independent prospective access-control attestation, and
`include_in_primary_independent_human_pool = false`.
`helped_construct_assigned_items` records the narrower item-specific fact and is
false for the live pilot only after the coordinator confirms that Charlie did not
construct those four assigned items.

The historical broad synthetic rubric is retained for audit but is not the
Direction H collection contract: it splits voice from negative cases and omits
scope calibration. The existing Warrant Study app likewise must not be treated
as schema-compatible without an explicit validated adapter because its current
form has only support and voice ratings and one global abstention.

### 3.3 Direction H workflow records

Direction-specific records supplement rather than alter the canonical rating:

| Record | Required version |
|---|---|
| Pilot item | `direction-h-pilot-item-v1` |
| Coordinator synthetic truth map | `direction-h-synthetic-truth-v1` |
| Independent construction verification | `direction-h-construction-verification-v1` |
| Target-assessment briefs | `direction-h-target-assessment-briefs-v1` |
| Target-brief commitment | `direction-h-target-assessment-briefs-commitment-v1` |
| Post-lock blinding debrief | `direction-h-blinding-debrief-v1` |
| Human feedback | `direction-h-feedback-v1` |
| Revision case | `direction-h-revision-case-v1` |
| Eligible-target revision allocation | `direction-h-revision-allocation-v2` |
| Revision output | `direction-h-revision-output-v1` |
| Reviewer-safe repair-panel item | `direction-h-repair-panel-item-v1` |
| Repair assessment | `direction-h-repair-assessment-v1` |
| Repair-assessment/shared-rating link | `direction-h-post-revision-rating-link-v1` |
| Rater registry | `direction-h-rater-registry-v1` |
| Revision freeze manifest | `direction-h-revision-freeze-v1` |

The corresponding schemas live under `../schemas/`. The exact field mapping to
the companion direction is documented in `companion_alignment.md`. The frozen
revision instruction is documented in `revision_prompt.md`.

Plural-reference coverage is intentionally absent from the packet rating and
feedback records. It is a complete natural-output inventory measure, not an
item-level judgment or a controlled-twin manipulation check.

## 4. Research questions and prospective hypotheses

### 4.1 Pilot questions

- **RQ-H1, detection:** On independently vetted synthetic controls, which planted
  source-warrant defects does Charlie flag and miss, and what does he flag on a
  verified no-planted-defect control?
- **RQ-H2, feedback utility:** Across all preregistered defective items, does a
  frozen revision model supplied with Charlie's locked feedback identify the
  target defect more often and produce more successful repairs without collateral
  error than the same model and prompt supplied with no external feedback?
- **RQ-H3, rater comparison:** On the same blind item identifiers, where do
  Charlie and the companion LLM rater agree or disagree in ordinal ratings,
  flags, disposition, abstention, confidence, and rationale focus?

The synthetic pilot tests the workflow and yields descriptive single-case
estimates. Its hypotheses are prospective engineering expectations, not claims:

- **H-H1:** Charlie's target-family detection rate will be higher on planted
  defect items than the serious-flag rate on the independently verified
  no-planted-defect control. This is not called specificity unless a construction
  verifier separately confirms the control has no material rubric-defined defect.
- **H-H2a:** The frozen revision model will record the target-family diagnosis
  more often with Charlie feedback than with no external feedback.
- **H-H2b:** The probability of successful repair without collateral error will
  be higher with Charlie feedback than with no external feedback.
- **H-H3:** Any repair advantage will be accompanied by lower target-defect
  persistence and will not be summarized in a way that hides new unsupported
  claims, omissions, or distortions.

No literal **human** defect-detection contrast against `no_feedback` is defined.
A no-feedback condition produces no human detection judgment. Charlie's detection
is scored against a prespecified planted label in the pilot and against an
independent, contract-relative panel in the extension. The frozen revision model
does produce an explicit truth-blind `revision_diagnosis` in both feedback arms,
so its paired target-diagnosis contrast is defined as a secondary mechanism
outcome. The primary intervention contrast remains downstream repair.

### 4.2 Confirmatory questions

After a separate independent-human pilot and before any held-out output is
inspected, the team will preregister:

- whether independent researcher feedback improves successful repair without
  collateral error relative to no feedback;
- whether the direction and error-family pattern seen in the Charlie case
  replicates across independent reviewers;
- paired human-versus-LLM rater differences on identical items; and
- any noninferiority margin for collateral-error risk or comparison with an
  expert-feedback condition.

The Charlie pilot cannot set a population effect size, between-rater variance,
or confirmatory reliability target. It may inform interface failures, timing
ranges, feedback formatting, and the list of prespecified protocol deviations.

## 5. Synthetic pilot design

### 5.1 Eligible material

The pilot uses fictional qualification material only. Eligible source packets
come from `../../qualitative_coding_baselines/benchmark/synthetic_packets_v1.json`
or a Direction H synthetic item bank whose lineage and hashes are recorded.
Historical generation files may be referenced through blinded derived packets,
but the historical run is not rewritten and its model-judge scores are not shown
to Charlie.

The live reviewer-safe manifest contains four items: three intended
single-defect manipulations and one item whose coordinator label is
`no_planted_defect_control`. This allocation count is a coordinator/analysis fact,
not an item map; the reviewer is not told which task has which status. Agent or
automatic QA establishes workflow readiness only. Until a non-Charlie
construction verifier confirms the intended manipulation and control status, all
four items remain eligible only for workflow qualification, not detection
accuracy, false-positive, or specificity estimates. `no_planted_defect_control`
means that the constructor intended no manipulation; it does not assert that the
output is universally error-free.

After independent construction verification, a controlled item is either:

- a verified no-planted-defect control, with any additional determination that it
  has no material rubric-defined defect recorded separately; or
- a single-defect variant from a preregistered WarrantRoute family:
  unsupported inference, hidden source concentration, lost negative case,
  contextual flattening, or unsupported abstraction.

Quotation and attribution failures may be included only as separately labeled
integrity controls. A packet with more than one material manipulation is not
eligible for target-family detection analysis. Natural outputs without a known
single target, and intended controls without independent verification, may be
retained for workflow qualification and descriptive review but are not scored as
controlled detection successes, false positives, or failures.

### 5.2 Construction and assignment safeguards

- For future and confirmatory items, a person other than Charlie verifies the
  base, target defect/control status, target flag, plausible surface form, and
  absence of a second material manipulation before assignment and label freeze.
- The live four-item pilot already has coordinator-committed intended labels but
  not independent construction verification. A non-Charlie verifier who has not
  seen Charlie's responses must either confirm each intended label/control status
  or mark the item ineligible in a record conforming to
  `direction-h-construction-verification-v1` before detection analysis. The
  verifier cannot retarget a manipulation after observing Charlie's rating.
- The private label map is hashed and sealed before assignment.
- Charlie receives at most one version of a base packet. Clean and defective
  twins from the same base never appear in his pilot bundle.
- Tutorial and comprehension-check items do not enter the pilot analysis.
- Pilot base packets do not enter the confirmatory set.
- Item order is randomized from a frozen seed, with condition and failure-family
  balance checked by an organizer who is not the reviewer.
- No item is substituted after a rating has been seen. A necessary replacement
  is logged as a protocol deviation and uses a previously frozen reserve item.

The pilot item count is set in the validated item manifest rather than inferred
from completed ratings. This protocol does not invent a sample size or power
claim.

### 5.3 Rating procedure

For each item, Charlie:

1. starts the recorded review timer when the full packet becomes available;
2. reads the packet without opening the private maps, historical judge outputs,
   or other reviewers' data;
3. completes all three canonical ordinal constructs or marks only the dimensions
   that cannot be judged;
4. records confidence, disposition, every applicable serious-error flag,
   requested expertise, and a concise evidence-linked rationale;
5. stops the canonical rating timer and freezes those answers in-session;
6. writes actionable feedback without naming a presumed planted condition; and
7. submits the validated rating and linked sidecar as one atomic pair before
   proceeding.

The timer records bounded packet-review and rating time through completion of
the rating rationale. It excludes feedback-sidecar authoring and is not total
qualitative-analysis labor. Inactive-window rules and any interruption handling
must be frozen before the timed pilot begins.

### 5.4 Feedback derivation

Charlie completes and freezes the canonical rating answers in-session before
the collector elicits feedback under the frozen instructions in
`companion_alignment.md`; he cannot revisit those answers during the feedback
prompts. The collector then validates both records before a rollback-aware,
no-overwrite atomic pair commit, and the study validator refuses an unmatched
rating or sidecar as an apparently complete observation. Its `rating_key` and
hash link back to the unaltered canonical record. Beyond linkage
and timestamps, the
sidecar contains `feedback_status` and the identity-free
`model_feedback = {feedback_summary, findings, preserve, uncertainties}`;
findings carry canonical error flags and output/evidence locations. Disposition,
requested expertise, rating rationale, numeric ratings, confidence, and review
time remain only in the hash-linked canonical rating and are not duplicated in
the sidecar. Reviewer identity, private planted label, expected answer, original
model identity, arm label, other ratings, and post-rating organizer
interpretation are also absent from the revision-model payload.

A human correction made after submission creates a new version linked to the
original and is excluded from the primary as-collected analysis unless the
preregistered correction rule applies. The original record remains immutable.

## 6. Frozen downstream revision experiment

### 6.1 Conditions

Every preregistered defective base output is assigned to both paired
`feedback_arm` values:

1. `no_feedback`: model-visible `reviewer_feedback` is JSON null; and
2. `charlie_feedback`: `reviewer_feedback` is the exact frozen identity-free
   `model_feedback` projection authored after Charlie's locked review, including
   cases in which he missed or abstained on the target defect.

Including all defective items preserves a pipeline-level, intention-to-treat
estimand. Restricting the primary repair analysis to defects Charlie detected
would select on the intervention and overstate performance.

### 6.2 Controlled revision difference

The model snapshot, system and user prompts, formatter, analytic contract,
source packet, starting output, decoding settings, tool policy, maximum output,
retry rule, and repeat count are frozen in a manifest conforming to
`direction-h-revision-freeze-v1` before revision begins. The only planned input
difference is the external-feedback payload. The model receives no private
condition label and no outside knowledge or tools.

Before revision cases are created, an independent non-Charlie construction
verifier must mark each task. Only committed controlled-defect tasks with the
itemwise disposition `verified_for_detection` enter the paired revision
denominator; controls, `workflow_only` tasks, and rejected tasks remain in a
private exclusion inventory and do not veto other eligible targets. A
non-Charlie coordinator then completes the arm-blind target-assessment briefs
for exactly those eligible targets and freezes their exact hash in a separate
commitment. The case allocation binds the construction, brief, and commitment
hashes, and every model invocation must strictly postdate that commitment.

Before generating its revision, the model records a truth-blind
`revision_diagnosis` containing `detected_error_flags`, structured findings, and
a rationale. The same requirement applies in both feedback arms. It receives no
target label or evaluation answer. Because the Charlie-feedback payload may
itself name an error flag, increased target diagnosis in that arm measures
feedback transfer into the frozen model, not an independent second discovery of
the defect.

The no-feedback arm is an active self-revision control, not an untouched copy of
the original output. This controls for the extra opportunity to revise. If the
runtime does not provide deterministic seeds, the study retains all
preregistered independent repeats in both conditions and pairs them by base
output and repeat index; it never selects the best revision.

### 6.3 Independent repair adjudication

Charlie does not judge revisions produced from his feedback. A separate panel
rates randomly ordered objects conforming to
`direction-h-repair-panel-item-v1` without seeing feedback condition, feedback
author, model identity, planted label, revision diagnosis, or other adjudicators'
responses. Adjudicators receive the source packet, starting output, revision, and
the minimum arm-blind target-assessment brief needed to assess whether the target
problem is absent. They independently record:

- whether the target defect is repaired;
- whether accurate and relevant material is preserved;
- whether a new unsupported claim, omission, distortion, attribution problem, or
  other collateral error appears;
- the three canonical artifact-quality ratings in a separate exact shared row; and
- confidence, rationale, and review time.

Every repair assessment is accompanied by a separate direct
`qc-paper-metrics-v1` rating of that same blinded revised output. The shared
object is not wrapped or extended: it uses the panel item's `packet_id`,
`corpus_id`, and `evaluation_role`, uses `blinded_revision_id` as `output_id`,
and always includes `requested_expertise`. A Direction-H-local link record holds
the two record hashes and timing semantics. The three canonical constructs are
therefore available for paired post-revision arm comparisons, not as a
cross-rater change from Charlie's earlier starting-output score.

The repair record uses the exact component fields `target_defect_repaired`,
`accurate_relevant_material_preserved`, and `collateral_error_present`. The
derived `successful_repair_without_collateral_error` is true exactly when the
first two are true and the third is false. Its `cannot_judge` array is
component-specific. The adjudicator record contains `blinded_revision_id` but no
feedback-arm field; the private arm join occurs only after assessment lock.
Target repair and each collateral-error component are always reported separately.
Adjudication, if used, occurs only after independent assessments are locked, and
persistent reasoned disagreement is retained rather than forced into false
consensus.

A revision case that exhausts the frozen retry policy without an eligible
completion cannot be shown to the panel, but it remains in the primary
pipeline-level denominator as a non-established successful repair. The same
rule applies when the locked panel process cannot establish every success
component. Technical failures, unusable completions, component-specific
`cannot_judge`, and disagreement are reported separately, alongside a
sensitivity analysis of `successful_repair_without_collateral_error` among
eligible judgeable outputs. This preserves every preregistered defective case
without pretending that missing content received a substantive defect rating.

## 7. Confirmatory extension with independent blinded reviewers

The extension preserves the same packet task, blind identifiers, rating schema,
feedback schema, formatter, revision model, condition definitions, and repair
outcomes. It changes the reviewer sample and the evidentiary status.

Eligibility requires research literacy, tutorial completion, and no task-relevant
qualitative-method or domain specialization for the assigned researcher stratum.
Relevant expertise, dual expertise, corpus familiarity, and positionality are
recorded rather than inferred from job title. Primary independent reviewers must
not have constructed the items, selected the generator or revision model,
developed the rubric or app, inspected the condition map, or adjudicated their
own feedback.

The design uses randomized crossed incomplete blocks. Each reviewer sees at most
one version per base packet, and each confirmatory item receives the
preregistered number of independent ratings. If the main manuscript design is
retained, that minimum is three ratings per role and item. Final numbers, the
smallest effect of interest, multiplicity, exclusions, and any noninferiority
margin are chosen through simulation after an independent-human pilot and frozen
before held-out evaluation.

Charlie remains a separate case row in every confirmatory table. His data are not
silently pooled with independent reviewers even if the direction of effect is
similar.

## 8. Required reporting language and prohibitions

Until records exist and validate, report only that the protocol and instruments
were prepared. Do not populate a results table, state that a defect was detected,
claim that feedback repaired an output, invent a completion time, or infer a
direction of effect.

When the synthetic Charlie pilot is complete, use language no stronger than:

> In a synthetic workflow qualification, one researcher-developer completed
> condition-masked, evidence-linked reviews. Because this reviewer helped
> develop WarrantRoute and the materials were synthetic, the observations are a
> developer-researcher case baseline; they do not estimate trained-researcher
> performance, establish universal human ground truth, or validate use on
> protected corpora.

Replace `condition-masked` with `condition-blinded` only when the access log and
review environment establish prospective technical separation from every
private map.

Every report must distinguish planned, attempted, completed, excluded, and
analyzed items; reconcile denominators; label synthetic results as synthetic;
and preserve null, adverse, and discordant findings.

## 9. Stop rule for real text

Direction H is **not cleared for protected real text**. No Dreaddit, CaCHe, or
other protected source-derived packet may be opened for this study, sent to a
model, placed in a rating bundle, or shown to Charlie or another reviewer until
all gates in `governance_and_blinding.md` are affirmatively documented. Source
collection approval does not by itself authorize this secondary study, model
processing, or rater exposure.

## 10. References to controlling local artifacts

- Shared analytic contract:
  `../../qualitative_coding_baselines/protocol/analytic_contract.md`
- Paper metric contract:
  `../../qualitative_coding_baselines/protocol/paper_metric_data_contract.md`
- Canonical rating schema:
  `../../qualitative_coding_baselines/schemas/paper_metric_rating.schema.json`
- Historical human rubric and its scope warning:
  `../../qualitative_coding_baselines/protocol/human_review_rubric.md`
- Synthetic qualification status:
  `../../../Storage/synthetic-results/model-qualification/20260825_synthetic_qualification/RESULTS.md`
- WarrantRoute dataset and approval plan: `../../../overleaf/DATASET_PLAN.md`
- Manuscript repair design: `../../../overleaf/sections/paper.tex`
- Existing feedback-collector status: `../../../app/feedback-collector-demo/README.md`
