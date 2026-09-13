# WarrantRoute Claim-Flaw Detection: Bounded Playbook Experiment

Call-budget amendment: see
[version 3](warrantroute_claim_detection_call_consolidation_v3.md).
The current design merges diagnosis integration and verification into one call.
Single-call development learning is an exploratory candidate, not yet adopted.
The six-call diagram and timing below, including the v2 poster, remain historical
v2 specifications. The v2 data panel and checkpoint schedule remain unchanged.

Date: 2026-09-09. Version: 2.0.
Status: prospective design only. Not implemented, frozen, qualified or launched.
The previous TA-generation experiment and its progress automation remain stopped.
This protocol does not authorize inference, paid API spending or manuscript export.

## 1. Purpose and change from version 1

Given an immutable claim and its evidence, detect and characterize material
flaws. Learn reusable detection procedures from development feedback. Test
whether the resulting Playbook improves detection of flaws in other claims.
Do not generate thematic analyses, rewrite the evaluated claim, or treat more
flags, more rules, internal agreement or successful repair as better detection.
Improvement is a hypothesis and may fail.

This version supersedes the checkpoint workload in
[version 1](warrantroute_claim_detection_learning_curve_v1.md).
Initial and final Playbooks receive a full 100-item evaluation. Intermediate
Playbooks receive the same fixed 20-item probe. This reduces planned evaluation
outputs from 9,600 to 6,720 while retaining a paired initial-to-final comparison
on all 100 items. Historical protocols and outputs are not rewritten.

The source-only TA-generation run is not evidence for this objective. The old
claim-repair runtime also cannot implement this design without changes: it
revises claims, whereas this protocol refines allegations about a fixed claim.

## 2. Data and eligibility

Retain Dreaddit, GoEmotions, CaChe and ParlaMint-GB in that order. Use the same
candidate 100 evaluation packet IDs per corpus as the earlier diagnostic.
Use 20 development packets per corpus, shared across model conditions in a
fixed order. This gives 400 evaluation and 80 development packets, not 480
independent source documents. Each packet includes its original claim fields,
all stored evidence, evidence identifiers and permitted context.

Candidate provenance is available in:

- [Data inventory](../experiment_data_catalog/VERIFIED_INVENTORY.md).
- [Stopped run split manifest](../rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909_v6/manifest.json).
- [Flaw criteria audit](flaw_criteria_audit_v1.md).
- [Objective review criteria](objective_review_criteria_v1.md).

Reuse candidate IDs and split provenance, not source-only TA inputs. Re-audit
complete claims and evidence before freezing a new manifest. In particular,
remove reviewer access to answer keys, intended categories, construction notes
and nested target hints using a reviewed field allowlist. Do not silently alter
substantive claim text to remove a hint. Mark inseparable cases ineligible and
report any denominator change before launch.

Preserve text, evidence order and quotation offsets. No efficiency-driven
summarization, paraphrasing, translation, splitting, recombination or truncation.
Use Unicode code-point offsets with half-open spans [start, end). An oversized
input is an explicit eligibility or technical problem, not a shortened item.

Existing split checks found no shared record/text/source IDs for Dreaddit,
GoEmotions and ParlaMint-GB. CaChe has distinct development/evaluation records
and text but shares 11 source groups. The user authorized CaChe only as a
clearly labeled within-source diagnostic. Repeat these checks for the restored
claim inputs. None of the historically evaluated panels is a newly unseen test
set. Constructed claims remain private diagnostics under AGENTS.md, even when
their source excerpts are real. Do not copy their results into the manuscript.

## 3. What counts as a flaw

An established flaw requires an identifiable target, a demonstrable failure of
the claim-evidence relationship, and a material consequence for interpretation.
Apply the detailed criteria in the flaw audit. A disagreement in wording or a
plausible alternative reading alone is insufficient. Lack of support does not
prove that the opposite claim is true.

The intended historical categories are unsupported_inference,
hidden_source_concentration, lost_negative_case, contextual_flattening and
unsupported_abstraction. These are not an exhaustive inventory of natural
flaws. Record a justified other-category issue separately instead of forcing it
into an intended category.

Every method emits the same structured final schema:

- Packet ID, immutable claim hash and evidence-bundle hash.
- Decision: established_flaw, no_flaw_established or cannot_judge.
- An issues array with a stable issue ID, category and affected claim field.
- Exact claim span, or an omission target tied to the affected field.
- Evidence IDs and exact supporting or contradictory evidence spans.
- The failed inference or missing qualification and its material consequence.
- Uncertainty and unresolved concerns, separately from established allegations.

Technical failure is a runner status, not a fourth semantic answer. An omission
need not have a literal span in text where the missing content never appeared.
An existing evidence ID without a relevant supporting explanation is not a
grounded detection. Deduplicate overlapping descriptions of the same defect.

Use at most eight issue records per final output and provisionally 1,536 output
tokens per call. A truncated response is a technical failure, not an empty
issue list. The pilot must determine whether these limits permit complete
outputs; any change must precede the main freeze and apply across conditions.

## 4. Models, methods and call budgets

Use Qwen3 8B, Llama 3.1 8B and Gemma 3 4B. Every semantic agent in a model's
review and Playbook-update condition uses that same tested model. Keep model
digests, prompts, decoding parameters, seeds, context limits and output schema
in a new immutable manifest. Proposed decoding is temperature 0, top_p 1,
context 16,384 and a recorded fixed seed, subject to pilot feasibility. This
does not guarantee deterministic backend execution.

Method-specific prompts are identical across model families. All conditions
receive the same original claim and evidence. Different methods have different
call budgets; report this cost difference rather than claiming equal compute.

| Method | Processing | Maximum semantic calls per packet |
| --- | --- | ---: |
| Generalist | One general claim reviewer | 1 |
| Fixed role | One qualitative-methods claim reviewer | 1 |
| All roles | Independent general, methods and domain reviewers; one merger | 4 |
| WarrantRoute | Initial reviewer, independent evidence scout, up to two routed challengers, diagnosis merger, final verifier | 6 |

All roles reviewers do not see one another's drafts. Its merger can reconcile
and deduplicate supplied allegations but cannot invent a new allegation without
support from an input review and the supplied evidence. Record discarded issues
and reasons in the audit trace.

WarrantRoute has one bounded diagnosis-refinement pass:

1. An initial reviewer examines the original claim with retrieved Playbook rules.
2. An independent evidence scout examines the same claim and evidence without
   seeing the initial review. It receives the same checkpoint's retrieved rules.
3. A methods challenger checks inferential, scope, abstraction or negative-case
   concerns when the first two structured reviews identify these concerns.
4. A domain challenger checks contextual or domain-meaning concerns when
   identified. If either first review says cannot_judge, run both challengers.
5. A merger reconciles the diagnosis against the original claim and evidence.
6. A verifier checks the final allegations. It can downgrade an unsupported
   allegation or mark uncertainty, but cannot initiate another loop.

Routing is deterministic from the structured preliminary concerns and is fixed
before the main run. Do not route using the answer key, a judge score, model
identity or a desired result. Absence of established issues does not bypass the
merger/verifier. Never edit the claim or score a repaired version. Preserve every
stage output, including rejected allegations. Escalation is unresolved, not
successful repair or automatically a technical error.

## 5. Playbook development

Maintain separate memory for each of the 12 corpus/model combinations. Start
with the same immutable, corpus-neutral seed procedures. Do not import the
superseded TA-generation memory. Each rule has an ID, applicability conditions,
a concrete detection check, evidence requirements, counterconditions, provenance
and update history. Keep packet IDs and exact development quotations in a
non-retrieved audit record, not in the reusable rule text.

For each development packet, in the declared order:

1. Predict flaws using only the current memory, claim and evidence.
2. Lock the prediction, then obtain reference-relative diagnostic feedback.
3. A merged reflector/curator updater proposes local rule additions or changes
   explaining a missed flaw, wrong characterization or unsupported allegation.
4. A same-model guard checks evidence grounding, generality, duplication and
   forbidden item-specific information. Deterministic schema checks run too.
5. Apply accepted edits and save an immutable snapshot with a parent hash.

This is at most six detection calls, one fixed evaluation-model feedback call,
one same-model updater call and one same-model guard call: nine semantic calls
per development episode. A guard decision is automated acceptance for a private
diagnostic, not human approval. Never fabricate an approved_by field or bypass
historical approval requirements to make this a confirmatory run.

Freeze a maximum of 40 active rules and retrieval of at most six rules per
packet. Retrieval uses claim/evidence content only, with a deterministic
implementation and stable ID tie breaking. Log retrieved rule IDs and tokens.
Rule selection, replacement and capacity behavior must be tested before launch.
Rejecting every useful update is a feasibility problem to investigate in the
pilot; during the frozen main run it is an observed outcome, not permission to
relax acceptance until scores improve. No accepted rule does not invalidate a
checkpoint: save the unchanged memory and report zero growth.

Evaluate P0, P5, P10, P15 and P20, where the number is completed development
episodes, not accepted rules. P0 is the seed control, not a no-Playbook condition.
Twenty examples support only a short diagnostic learning curve. They cannot
establish indefinite improvement or an optimal memory size.

## 6. Checkpoints and workload

Before any new evaluation, select one fixed 20-item probe inside each 100-item
panel, using a recorded seed and source-aware selection. Never select it based
on observed method scores. Do not force unsupported reference categories into
the panel merely to balance counts.

| Checkpoint | WarrantRoute evaluation per corpus/model | Learning-curve comparison |
| --- | ---: | --- |
| P0 | 100 | Use its same 20 probe results for the curve |
| P5 | 20 fixed probe items | Same probe |
| P10 | 20 fixed probe items | Same probe |
| P15 | 20 fixed probe items | Same probe |
| P20 | 100 | Use its same 20 probe results for the curve |

The primary memory comparison is P20 versus P0 on the same 100 packets. The
five-point curve uses the same 20 probe items at every checkpoint. Do not
compare an intermediate n=20 rate directly with a full-panel n=100 rate or
extrapolate it to the other 80 packets. Generalist, Fixed role and All roles
each run once on all 100 items, with the new common output contract.

| Work item | Planned count |
| --- | ---: |
| Unique development packets | 80 |
| Development episodes across three models | 240 |
| Baseline final outputs: 4 corpora x 3 models x 3 methods x 100 | 3,600 |
| WarrantRoute final outputs: 12 conditions x (100 + 20 + 20 + 20 + 100) | 3,120 |
| Evaluation final-output slots | 6,720 |
| Evaluation quality/matching bundles, one per slot | 6,720 |
| Development feedback bundles | 240 |
| Reference preparations: 480 unique packets x two independent passes | 960 |

Run one trajectory per packet, method, model and applicable checkpoint. These
are not repeated random-seed trials. Multiple checkpoints on one packet are
paired observations, not independent samples. Do not pool development scores
with evaluation scores. No baseline output reuse from historical label-only or
different-prompt experiments is allowed in a fresh matched comparison.

Evaluation can be interleaved with judging for observability, but its feedback
must never enter the updater, prompt tuning or checkpoint selection. Prefer
finishing development and freezing all snapshots before evaluation. Report all
prespecified checkpoints, not the best-looking one.

## 7. Reference answers and evaluation

Historical truth maps identify intended defects, not a validated exhaustive
answer sheet. The current no-human diagnostic preference does not make model
judgments ground truth. Before reviewing new method outputs, prepare two
independent structured reference proposals per unique packet, one with Qwen and
one with Llama, without exposing the intended label or the other proposal.

Keep their raw proposals, exact span checks and agreement/disagreement records.
Require matching target and compatible defect mechanism for an agreed reference
issue; a shared category alone is insufficient. Do not silently reconcile
disagreement into certainty. Freeze unresolved cases as unresolved and record
reference coverage. This model-built inventory is neither guaranteed correct
nor exhaustive, and shared reference/evaluator model families can bias results.
This is an automated diagnostic reference, not independent human validation.

A fixed Qwen evaluator, blind to method/model/checkpoint labels, compares each
final review against the frozen agreed reference and source evidence. In one
structured call it reports issue matching, unsupported-allegation assessments,
Credibility and Conformability. Using Qwen for all reviews holds its identity
constant but does not eliminate self-evaluation bias. Report that limitation.
The evaluator must never see internal trajectories or rule-update history.

Correct detection requires a one-to-one matched allegation with all of:
the affected assertion or omission, a compatible defect mechanism/category,
relevant verifiable evidence, and a material consequence. Match each reference
issue and prediction at most once. Enforce identifier/quotation checks in code.
An additional allegation outside the agreed inventory is not automatically
false: report it separately as evaluator-supported, unsupported or unresolved.

Report these distinct quantities:

- Reference-relative grounded recall: matched grounded agreed-reference issues
  divided by agreed-reference issues in the declared panel. Always give both
  counts, the number of packets with scorable references, and unresolved cases.
- Characterization success: matched reference issues whose target, category,
  mechanism and evidence all meet the frozen rubric, with its explicit reference
  denominator. The strict grounded-recall definition above already requires
  these components; component rates diagnose which checks fail rather than
  being presented as independent evidence of success.
- Unsupported-allegation rate: evaluator-unsupported allegations divided by
  all emitted allegations, with unresolved allegations separately reported.
  This is model-adjudicated, not validated precision.
- Intended-target recall: optional legacy label-hit diagnostic only. Never use
  it as the primary endpoint. Flagging all five categories must fail the strict
  matching test whenever the specific claims/evidence are unsupported.
- Credibility: a binary review-level judgment that the diagnosis accurately
  characterizes the supplied claim and evidence without material distortion.
- Conformability: a binary review-level judgment that every material allegation
  and rationale is traceable to supplied evidence/context rather than invention
  or irrelevant assumptions. Use the user's established spelling.

Credibility and Conformability apply to reviews, not generated themes or repairs.
A justified no_flaw_established review may pass; an empty or failed output must
not pass by vacuity. Report successes / all scheduled output slots alongside
successes / adjudicated outputs, and disclose failed/missing judgments. A missing
judgment is not a known semantic failure; the all-slot rate is a conservative
observed-success proportion. Do not hide failures by changing denominators.

Do not claim conventional true-flaw precision/F1 or false-positive rate without
an appropriate complete reference audit and validated negative items. Do not
invent clean negatives by rewriting existing claims. A nonempty agreed flaw
inventory is required to compute its recall; otherwise report unavailable and
coverage, not zero or 100 percent.

The primary comparison is the paired change in reference-relative grounded
recall from P0 to P20, accompanied by change in unsupported allegations, cost
and C/C. A rising recall alone is insufficient if it comes from indiscriminate
accusations. Compare P20 with fresh baselines on matched panels as a secondary
comparison, noting unequal call budgets. Report source-group counts and paired
item outcomes. Do not produce naive independent-binomial intervals when packets
share sources, or infer run-to-run stability from one trajectory per condition.
Any inferential interval requires a separately frozen source-cluster procedure;
the default diagnostic export uses counts and paired differences, not a promise
of statistical significance.

## 8. Pilot before the main experiment

First run a separately named feasibility pilot on development-partition items
only, after implementation and explicit launch authorization. Per corpus/model,
use two development episodes and four other fixed pilot probe items. Compare
P0/P2 and all three baselines. No pilot packet comes from the 100-item panel.

This requires 24 unique packets across corpora, 24 development episodes across
models, 96 WarrantRoute outputs, 144 baseline outputs, 240 evaluation bundles
and 48 reference-preparation calls. The pilot is not powered to demonstrate
improvement. Check claim immutability, non-vacuous detection, memory updates,
model-blind evaluation, output completeness and actual wall-clock cost.

These six pilot items per corpus may be drawn from the planned 20 development
items. If reused in the later main development sequence, declare the pilot
exposure, reset to the original seed and do not pool pilot outcomes. Freeze any
pilot-driven changes before main inference. For a stronger independent study,
reserve separate pilot development data and audit eligibility again.

## 9. Runtime estimate

Estimate date: 2026-09-09. Local, serial inference only. These are provisional
planning scenarios, not confidence intervals, deadlines or upper guarantees.
The pipeline does not exist yet, so there is no live remaining-time estimate.

Measured proxy: completed claim-review calls under
`Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2/results/`.
Do not use the stopped source-only TA-generation timing as a direct forecast.

| Model | Historical complete calls | Mean service seconds | Median service seconds |
| --- | ---: | ---: | ---: |
| Qwen3 8B | 2,601 | 21.12 | 20.85 |
| Llama 3.1 8B | 2,409 | 14.51 | 14.10 |
| Gemma 3 4B | 2,521 | 8.53 | 7.95 |

Use role-specific mean service times for the new review stages, with reviewer
and reviser roles as proxies. Missing role/model measurements use that model's
slowest measured role mean. Llama's domain mean has only nine observations, so
this component is especially uncertain. Updater/guard cost uses the model's
overall call mean as a proxy, not a measurement of the proposed new prompt.

For historical role means p=proposer, s=evidence_scout, m=methods_challenger,
d=domain_challenger and r=reviser:

```text
W = p + 2*s + m + d + r             # maximum six WarrantRoute calls
B = 2*p + 2*m + d + r              # three baselines together, six calls
D = W + 2*overall_model_call_mean  # development excluding feedback judge
generation_seconds = sum_models(1040*W + 400*B + 80*D)
judging_seconds = (6720 + 240) * assumed_judge_seconds
reference_seconds = 480 * (qwen_proposer_mean + llama_proposer_mean)
```

Lower planning scenario: historical generation/reference proxy plus 15 seconds
per new matching/quality bundle. Upper scenario: 1.75 times those proxy costs
plus 45 seconds per bundle. The 15-45-second judge range and 1.75 multiplier are
assumptions for richer outputs and overhead, not observed new-task throughput.
Both scenarios budget all optional challengers. Service duration excludes some
scheduler idle time, sleep and unrelated machine contention. Repeated failures,
larger contexts or changed output limits can exceed the range.

| Scope | Provisional local inference time |
| --- | --- |
| Feasibility pilot, all corpora and models | Approximately 6-12 hours |
| Main experiment, all corpora and models | Approximately 155-310 hours, or 6.5-13 days |

The main lower scenario consists of about 121 generation hours, 29 judging hours
and 4.6 reference-preparation hours. The pilot is additional if run first.
Implementation, eligibility remediation, scientific review of reference quality
and unexpected repairs are not included. No human annotation time is assumed.
Do not present this as time until manuscript-qualified results.

The [read-only estimator](estimate_claim_detection_runtime.py) recomputes the
counts and timing from local historical journals without making inference calls.
After the pilot, replace proxy timings with actual stage/model measurements,
show fixed and optional stage counts, and refresh the forecast before launching
the main run. Track both full-budget and remaining-stage wall-clock forecasts.

## 10. Implementation, monitoring and export gates

Before any launch, implement a new claim-diagnosis runner, not a renamed TA
runner. Freeze the input allowlist, common issue schema, method prompts, routing,
memory policy, reference matching, evaluator prompts and failure policy. Test:

- No answer-key leakage, no claim mutation, no evaluation-to-memory feedback.
- Same method prompt hashes across models, with only declared input substitutions.
- Invalid spans rejected; omissions represented; all-flags shortcuts not credited.
- No-flaw, uncertainty and technical failure remain separate.
- P0 and P20 use identical panels; all curve points use the same fixed probe.
- Bounded calls, unchanged snapshots, missing judgments and no-rule updates.
- Resume without deleting, overwriting or duplicating completed semantic outputs.

Declare transport retry limits before freezing. Retry only technical failures
under that policy; do not rerun an unfavorable semantic answer. Preserve every
attempt. An ambiguous in-flight call must be reconciled before a retry. Record
technical and scoring failures in the scheduled-slot denominator. No hidden
backoff or retry loop may create an unbounded runtime.

When a new run is actually authorized, report progress every five minutes as
previously requested, including no-change checks, development/evaluation/judging
counts, current stage, rule counts, technical issues and separate phase ETAs.
Judge completed evaluation outputs in small batches. Export descriptive updates
every 50 completed evaluation trajectories and at each checkpoint. Interim
scores are observational only and cannot change this frozen experiment.
This document itself does not create or resume an automation.

Write new private Storage artifacts: a 48-row final table (36 fresh baseline
rows and 12 P20 WarrantRoute rows), 12 P0 control rows, and a five-point curve
with 60 corpus/model/checkpoint rows explicitly based on the fixed 20-item
probe. Retain the separate full-panel P0/P20 results and all counts, hashes and
eligibility qualifiers. Do not overwrite the historical Table 3 CSV or claim
these new results already exist. Completion requires actual output/judge count
reconciliation, not merely a successful exporter exit code.
