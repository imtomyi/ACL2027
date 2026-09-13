# WarrantRoute: Final Flaw-Detection Experimental Design

Next-run amendment: the user now requires an eight-hour experiment with
per-corpus quality and Playbook verification. Use the
[v6 eight-hour diagnostic](warrantroute_flaw_detection_8h_v6.md) for that scope.
The larger main design below remains a separate future study; its four-hour
pilot section is historical and is not the current requested time budget.

Version: 5.0. Date: 2026-09-10 KST.
Status: design decisions finalized; NOT an inference authorization, implemented
executor, completed data audit, experimental result, or manuscript qualification.

## 1. Purpose and authority

**Detect and characterize material flaws in an existing claim using its supplied
evidence. Test whether development-only Playbook adaptation improves that task.**

Thematic analysis is the application context. The evaluated object is a supplied
interpretation or claim. Generating codes, discovering themes, rewriting claims,
repairing documents, and accepting a loop are NOT the task or success endpoints.
No document revision is produced or scored by this experiment.

This is the controlling prospective design for the new claim-detection study.
It replaces the unresolved choices in the v1-v4 claim-detection proposals, not
their historical records. It does not change the stopped TA experiment, frozen
n100 runs, historical scoring, Table 3, or manuscript. Workspace AGENTS.md and
privacy restrictions still take precedence. All new results stay under Storage.

The [machine-readable plan](warrantroute_flaw_detection_v5.plan.json) fixes scope,
repetitions, arms, checkpoints, and call ceilings. The
[prompt contracts](warrantroute_flaw_detection_prompts_v5.md) fix role behavior.
Writing these artifacts does not establish that a runner obeys them.

## 2. Research questions and falsifiable hypotheses

| **Question** | **Prespecified comparison** | **Interpretation** |
| --- | --- | --- |
| Does adaptive WarrantRoute detect more grounded flaws than the other methods? | Full WarrantRoute E3 versus Generalist, Fixed role, and All roles on the same packets/model | System comparison, not an equal-call comparison |
| Does adaptation help beyond the starting rules? | Full E3 minus frozen-seed E0 | Total context-adaptation effect |
| Does explicit reflection help? | Full E3 minus No explicit reflection E3 | Effect of a structured reflection function inside the Learning Editor |
| Do additional development passes help? | Full E3 minus the same branch's E1 | Three epochs versus one, on the same unique development data |
| Do localized memory updates help? | Full E3 minus Full-memory rewrite E3 | Delta-update policy versus rewriting editable memory |

The last three are the component ablations. Improvement, no difference, and
deterioration are all admissible outcomes. More rules, more words, more flags,
or more epochs are not evidence of better detection. Do not select the best
checkpoint retrospectively. E3 remains the final checkpoint even if E1 wins.

ACE motivates generation, reflection, and curation with evolving memory and
incremental updates. Here its generation function produces a flaw diagnosis,
not a thematic analysis. Its reported gains do not establish gains here. Our
merged Learning Editor is not a replication of separate ACE agents.
[ACE primary source](https://arxiv.org/html/2510.04618v3).

## 3. Two scopes, with no hidden expansion

### A. Four-hour Gemma feasibility pilot

Use only local Gemma 3 4B and WarrantRoute-Lite: Detector + Finalizer, followed
by one Learning Editor on development items. No baselines or component ablation
branches. Five adaptation packets and fifteen pilot-evaluation packets per
included corpus, three development epochs, and a fixed five-packet probe.
E0/E1/E2 evaluate the probe. E3 evaluates all fifteen. Compare the same five
probe packets across all four checkpoints, not n=5 against n=15.

Default included corpora: Dreaddit, GoEmotions, CaChe. This gives 60 unique
packets, 45 development episodes, 90 evaluation outputs, 90 judge bundles,
60 provisional reference calls, and at most **465 LLM calls**. All pilot IDs
must come from the older 20-item development candidates, never the main
100-item evaluation panels. Main adaptation later resets to the original seed.

ParlaMint-GB is excluded from this pilot by default: its twenty candidates
share one source-session group, so the proposed five/fifteen split cannot be
source-disjoint. The user has not authorized a within-source exception for it.
Do not silently use the CaChe exception for ParlaMint-GB. A later explicit
approval requires a new pilot manifest and recalculated counts, not a mid-run
addition. This exception does not remove ParlaMint-GB from the main design.

Pilot references and judges use Gemma only and are explicitly provisional,
same-model assessments. Apply the v5 unknown/technical-failure rules, not forced
binary judgments. The target is only the original stored claim sentence with
complete evidence. This narrowed target does NOT evaluate the complete qualified
analysis. Fifteen packets per corpus and repeated templates cannot establish
generalization, model rankings, or the three component hypotheses.

The four-hour limit starts at the first inference request, persists across
resume, and covers references, development, evaluation, and judging together.
It is a stop rule, not a guarantee that all 465 calls finish. At the deadline,
stop admitting calls and retain partial results with exact denominators. The
existing pilot runner still needs v5 scope and tri-state-judgment alignment.

### B. Main matched comparison and component study

Four corpora: Dreaddit, GoEmotions, CaChe, ParlaMint-GB. Three local model
families: qwen3:8b, llama3.1:8b, gemma3:4b. Per corpus, freeze 20 development
and 100 evaluation candidates, including one fixed 20-item evaluation probe.
There are **480 unique candidate packets**, not 480 independent documents.

Use one prespecified development-order realization, seed 20260910, and one
prediction per packet/method/model/checkpoint. Three epochs mean three visits
to each development packet, not three independent replications or extra data.
No repeated inference to select the best answer. This is a single-order,
model-reference diagnostic study. Broad claims of robust component gains
require separately preregistered replication and stronger reference validation.

The main study is NOT the four-hour run. It requires separate launch/budget
authorization after a fresh feasibility estimate. Do not queue it automatically
when the pilot finishes.

## 4. Input contract and eligibility

Reconstruct claim-bearing tasks from original packet banks. Historical TA input
payloads provide candidate identities/provenance only, not the new task text.
Freeze source paths, record IDs, source groups, exact field text, text hashes,
claim hashes, split membership, and the packet-order manifest before inference.

| **Corpus** | **Candidate bank relative to project root** |
| --- | --- |
| Dreaddit | Storage/draft_review_packets/dreaddit_dev580_working_v1/by_dataset/dreaddit.review_packets.jsonl |
| GoEmotions | Storage/draft_review_packets/goemotions_train_all_working_v1/by_dataset/goemotions.review_packets.jsonl |
| CaChe | Storage/draft_review_packets/agyw_focus_groups_eval765_working_v1/by_dataset/agyw_focus_groups.review_packets.jsonl |
| ParlaMint-GB development | Storage/draft_review_packets/parlamint_gb_eval100_working_v1/by_dataset/parlamint_gb.review_packets.jsonl |
| ParlaMint-GB evaluation | Storage/draft_review_packets/parlamint_gb_fullsample_eval100_working_v1/sample_packets/balanced_n100/by_dataset/parlamint_gb.review_packets.jsonl |

The prior candidate selection is recorded in
`Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909_v6/inputs.private.json`.
Those IDs are not newly validated by this design.

For the main target, retain the original claim and all legitimate supplied
qualifications needed to interpret it. Preserve evidence text and order. Remove
only clearly identified construction metadata, intended flaw labels, model IDs,
answer hints, historical reviewer outputs, and prior scores from task payloads.
Log every field exclusion and its reason before any prediction or reference.
If legitimate qualifications and answer hints cannot be separated without
rewriting the claim, mark the packet ineligible for this full-claim study.
Do not silently substitute the pilot's sentence-only task.

No summarization, translation, new flaw injection, recombination, or silent
truncation. Check the entire rendered request against each installed model's
actual context capacity. Use a common eligible inventory across models. A tag
name or requested context size does not establish model compatibility. If
fewer than the declared n remain eligible, stop preparation and revise the
sample-size manifest explicitly before inference. Do not claim n=100 anyway.

Development/evaluation record and exact-text overlap is prohibited. Compare
source-group connected components as well, not just packet IDs. CaChe may be a
clearly labeled within-source diagnostic under the user's existing exception,
with no repeated records/text. Other corpora require source separation. Preserve
all exclusions and template/source overlap counts. Per-corpus development on
CaChe or ParlaMint-GB is not zero-shot cross-domain transfer.

These banks contain constructed claims on real-source excerpts. Their builder
labels are intended flaws, not validated natural-flaw truth. Results from these
candidates remain private and manuscript-ineligible under AGENTS.md. A natural-
claim publication study needs separately authorized eligible inputs and a new
frozen inventory. Completing this protocol does not waive that requirement.

## 5. What counts as a flaw

An established flaw requires ALL of the following:

1. An identifiable claim assertion, attribution, scope, or omitted qualification.
2. A demonstrated failure in its relationship to the supplied evidence.
3. A material effect on interpretation, attribution, scope, strength, or disposition.

Use the exact category definitions and counterconditions in
[Flaw Definition and Experiment Audit](flaw_criteria_audit_v1.md), sections 1-3.
The executable taxonomy is fixed as unsupported_inference,
hidden_source_concentration, lost_negative_case, contextual_flattening,
unsupported_abstraction, and other_material_flaw. The last category requires
an explicit subtype and the same materiality/grounding test. Do not duplicate
one mechanism under multiple categories to inflate counts.

No automatic flaw quota: zero, one, or multiple flaws can be diagnosed.
A different interpretation, uncited but irrelevant excerpt, or source person's
emotion is not itself a flaw. Unsupported does not mean the opposite is true.
Do not diagnose the participant or import biomedical claims from outside the
packet. Biomedical interpretation is only permitted where the supplied evidence
supports it. The four corpora do not thereby become biomedical datasets.

Each final review includes an overall decision, rationale, at most eight distinct
established issues, and explicitly unresolved allegations. An issue records:

- Stable issue ID and category, with subtype for other_material_flaw.
- Claim field and exact target span, or an omission target without a fake quote.
- Evidence record IDs and exact spans, including relevant contrary evidence.
- Defect mechanism, material consequence, and counterconditions considered.

Offsets are zero-based Unicode code points, [start, end), with exact stored-text
matching. For missing support, identify the unsupported proposition and the
failed inferential link after considering the complete packet. Never invent an
evidence span for an absence. Keep a reasoned whole-packet grounding record when
there is genuinely no locatable supporting passage.

Decisions: established_flaw, no_flaw_established, cannot_judge. A missing,
truncated, or structurally unusable output is technical_failure, not no flaw.
No-flaw decisions require evidence-grounded reasoning and do not pass vacuously.

## 6. Methods and same-model agents

| **Method** | **Review calls per packet** | **Learned memory** |
| --- | ---: | --- |
| Generalist | One general reviewer | None |
| Fixed role | One qualitative-methods reviewer | None |
| All roles | Independent general, qualitative-methods, and domain reviewers, then one Finalizer | None |
| WarrantRoute | Initial reviewer + independent Evidence Scout + zero to two routed specialists + one Finalizer | Frozen checkpoint Playbook |

All roles is a finalized diagnosis bundle, not a union of category flags.
WarrantRoute has three to five review calls, with only ONE combined integration/
final-validation call. It never repeats diagnosis until the claim is accepted.
All agents, including learning, use the row's single tested model family.
There is no Qwen-led mixture standing in for a Qwen-only system.

Initial reviewer and Scout see the same claim/evidence/rules but not each other's
response. A deterministic router then requests qualitative-methods review when
their candidates include unsupported_inference, hidden_source_concentration, or
unsupported_abstraction, or either reports methodological uncertainty. Request
domain review for lost_negative_case, contextual_flattening, other_material_flaw,
or contextual/domain uncertainty. Otherwise omit that specialist. Call each at
most once. A technical failure in a required upstream call fails the trajectory
rather than changing its routing policy. The Finalizer accounts for every
candidate, merges duplicates, and may not invent unrelated new allegations.

Fix English templates by role, not model. The same role receives identical
instruction text, schema, input fields, rubric, and evidence limits for all
three models. Model-specific transport syntax is logged, not an excuse for
different instructions. WarrantRoute's learned rule contents can differ by
model because adaptation differs. Freeze and compare template hashes separately
from fully rendered request hashes. Do not reuse historical baseline outputs
whose target, schema, prompts, or bundling differs.

## 7. Playbook learning and memory policy

For each development exposure:

```text
Original claim + complete evidence + current retrieved rules
    -> 3-5 review calls -> locked flaw diagnosis
    -> ONE Learning Editor call on development-only reference feedback
    -> deterministic patch checks -> next Playbook version
```

The Learning Editor combines two explicit functions in one call: a concise
Reflector error analysis, then Curator rule edits. It is not an independent
semantic validator. This v5 design chooses the one-call policy, which was only
a candidate in v3/v4. It still requires implementation and pilot validation.

Store applicability, detection_check, evidence_requirement, countercondition,
rule ID/version, and audit-only support. The seed has two immutable rules:
locate evidence-to-claim warrants; preserve attribution, scope, and countercases.
Seed rules are included in every WarrantRoute request. At most 40 active rules
including the seed, with at most six retrieved rules including both seed rules.

For the remaining four retrieval slots, rank editable rules by the number of
distinct overlapping case-folded Unicode alphanumeric tokens between the rule's
four text fields and the visible claim/context/evidence. Break ties by stable
rule ID. Omit zero-overlap rules. This is a fixed, imperfect lexical retriever,
not another LLM call. Never use reference categories, intended targets, scores,
previous answers, or hidden metadata for retrieval.

At most two add/replace delta operations per exposure. Reject invalid patches
atomically, preserving the parent memory. At capacity, only valid replacements
are permitted. The full-rewrite ablation can replace the entire editable portion
under the same total capacity. No silent eviction, forced growth, or score-based
rule selection. Forty is a bounded engineering choice, not an optimized value.

Keep raw quotations, packet-specific answers, source identifiers, and reference
IDs in audit provenance only. Retrieved rules must describe reusable procedures,
not answers to recurring templates. Repeated exposure to a packet increases
exposure count but not unique support. Code checks integrity, literal leakage,
schema, and capacity, not semantic generality or absence of paraphrased leakage.
Record suspected semantic leakage and withhold affected claims of generalization.

Each corpus/model/ablation branch has isolated memory initialized from the same
seed. Carry it across epochs, never across branches or corpora. Predictions are
locked before reference access. Evaluation memory is read-only. No evaluation
answer, judgment, or reference may update memory, routing, prompts, or epochs.

## 8. Ablation matrix and schedule

| **Arm** | **Explicit Reflector function** | **Epochs** | **Memory update** | **Evaluation** |
| --- | --- | ---: | --- | --- |
| Full | Yes, inside Learning Editor | 3 | Incremental delta | E0/E1/E2/E3 |
| No explicit reflection | No structured error-analysis output | 3 | Incremental delta | E3 |
| One epoch | Same as Full | 1 | Incremental delta | Reuse Full E1 |
| Full-memory rewrite | Yes, inside Learning Editor | 3 | Rewrite editable memory | E3 |
| Frozen seed | No learning | 0 | None | Reuse Full E0 |

Only Full, No explicit reflection, and Full-memory rewrite need separate
adaptation. The other two are cached checkpoints, not extra runs. No-reflection
receives the SAME locked review, evidence, and frozen development reference as
Full. Only the explicit error-analysis requirement/output is removed. It still
returns patch provenance and must obey the same checks. This cannot demonstrate
that an LLM has no internal reflection. Call counts remain matched between the
three learned arms. Rewriting versus bounded delta changes the update policy,
not merely serialization. Report output-token/cost differences rather than
pretending equal calls mean equal computation.

For each corpus and epoch, order IDs by SHA-256 of the UTF-8 compact JSON array
[20260910, corpus_id, epoch_number, packet_id]. Use this same order across models
and ablation branches. Select the twenty probe IDs by the same rule with the
literal string "probe" in place of epoch_number, before seeing reference labels.
Record source/template concentration rather than implying hash order balances it.

Full evaluates E0 on all 100 packets, E1 on those same 100, E2 on the fixed 20,
and E3 on all 100. Other learned arms evaluate their E3 on the same 100.
Freeze all development snapshots before evaluation begins. The E0/E1/E3 full
outputs supply the fixed-probe curve without extra calls. Baselines run once
on the same 100 per model/corpus and are reused across checkpoint reports.

## 9. Reference preparation and judging

Main reference preparation uses one target-blind Qwen proposal and one target-
blind Llama proposal per unique packet, followed by one Gemma reconciliation
against the original evidence. Proposal calls cannot see each other, Playbooks,
predictions, builder labels, or past scores. Reconciliation can retain only
semantically compatible, grounded issues proposed by BOTH passes. Single-pass
or disputed issues remain unresolved. It cannot invent a consensus issue.
Store proposals, matches, rejections, and uncertainty. Three calls per packet,
reused for every model, method, and epoch. No regenerating unfavorable references.

This is a deliberately incomplete, model-built reference inventory, not gold
truth, exhaustive flaws, or independently validated negatives. An empty inventory
does not prove no flaws. Existing builder labels are audit-only, never scoring
answers. Reference failures are visible. Development items with no usable
reference still receive a diagnosis but no reference-driven learning update.

One separate Qwen 3 8B judge call scores each final evaluation output, supplying
issue-level support, compatible reference-prediction pairs, and Credibility/
Conformability together. Its inputs are the exact original claim/evidence,
unchanged final review, and frozen reference with uncertainty annotations.
Hide method/model/checkpoint/epoch, file names, Playbook, intermediate acceptance,
and historical scores. Preserve substantive review text, even if identity can
sometimes be inferred from style. A separate call is not an independent model:
Qwen self-family bias and shared reference-model bias remain explicit limitations.

The judge first checks the review directly against the supplied evidence, then
assesses reference matches. An additional grounded allegation outside the
reference is not automatically wrong. Reference disagreement cannot be forced
into a matching success or a false allegation. No human answer sheet is claimed.

All submitted IDs/quotes/offsets are checked mechanically. If a parseable complete
review contains a fabricated quotation, retain it for semantic failure judgment
with the integrity finding. Do not silently discard a bad review as missing data.
Unparseable/truncated outputs remain technical failures. The judge must assess
actual support, not treat passed structural checks as passed detection.

## 10. Endpoints and exact denominators

The primary endpoint is **reference-relative grounded detection recall**.
An alleged issue matches a reference issue only if target, compatible defect
mechanism, relevant evidence, and material consequence all agree. A category
match alone earns no credit. Report category accuracy among grounded matched
issues separately so correct detection and correct naming remain distinguishable.

Use maximum-cardinality one-to-one matching on judge-approved compatible edges,
with stable ID tie-breaking. Duplicate allegations cannot multiply hits. An
issue with a wrong taxonomy label but otherwise correct mechanism can match for
grounded detection and fail characterization. False extra allegations still
harm separate support/quality endpoints. Flagging all categories is not success.

Let R_i be retained reference flaws and M_i the matched ones for eligible packet
i. Main grounded recall is 100 * sum(M_i) / sum(R_i), with a zero-reference
denominator reported as N/A. Keep every scheduled reference-bearing packet in
this denominator. Missing/unscorable predictions contribute zero confirmed hits,
but are labeled technical/unresolved, not semantically false. Report that
conservative observed yield separately from resolved-pair-only recall and judge
coverage. Unavailable references are counted outside the estimable denominator
and must never be portrayed as zero-flaw packets.

| **Endpoint** | **Numerator / denominator and qualification** |
| --- | --- |
| Grounded detected/reference flaws | sum(M_i) / sum(R_i), not historical flag TP/N |
| Characterization accuracy | Correct category on grounded matched issues / all grounded matched issues |
| Supported-allegation rate | Supported established allegations / all established allegations in complete reviews; unknown support remains in denominator |
| Contradicted/unsupported allegations | Counts and rates among complete-review allegations, with insufficient-evidence cases separate |
| Review Credibility | Defensibility of diagnosis/disposition under the review-quality rubric |
| Review Conformability | Faithfulness and traceability to original evidence/context under the review-quality rubric |
| Coverage and reliability | Complete predictions, scored outputs, binary judgments, unavailable references, and technical failures / respective scheduled counts |

Use [objective_review_criteria_v1.md](objective_review_criteria_v1.md), sections
3-5 and 7, for review-quality decisions: true, false, or null. Demonstrated
failure takes precedence over unknown, which takes precedence over pass. These
are adapted LLM-assessed review-quality constructs, not repair quality.

For each quality dimension, N = T + F + U + E. Publish all four counts and
100*(T+F)/N binary coverage. Publish a full-row percentage 100*T/N only when
U+E=0. Otherwise leave that percentage N/A, show conditional 100*T/(T+F) with its
denominator, and show missingness. Never turn null into pass/fail to fill a table.
For supported-allegation rate, zero allegations means N/A, not 100%. Grounded
no-flaw reviews can pass quality but do not earn reference hits without issues.

Do not report true natural-flaw precision, F1, accuracy, specificity, or false-
positive rate without an adequate independent flaw inventory and qualified
negative cases. The current constructed targets do not provide those negatives.
Do not reward unsupported extra allegations merely to raise recall.

## 11. Comparisons, uncertainty, and claim limits

Report each corpus/model cell first. Use paired comparisons on identical packet
panels and separate the fixed-probe curve from full-panel results. Use equal-
weight corpus/model macro averages only when all constituent cells are estimable.
Do not quietly drop CaChe, failures, unresolved rows, or a poorly performing model.

For exploratory uncertainty, construct evaluation source connected components
from shared source IDs. Resample entire components with replacement within each
corpus, keeping all methods/checkpoints/models paired, 10,000 replicates with
seed 20260910. Recompute ratios each time, not the mean of packet percentages.
Report component counts, template repetition, and distinct references. As a
prespecified caution rule, suppress an interval if any contributing corpus has
fewer than twenty source components, unknown grouping, or any undefined bootstrap
denominator. This threshold is a protocol choice, not a statistical theorem.

Show descriptive 95% paired intervals where eligible. The three primary
component contrasts are equal-weight macro differences across the twelve
corpus/model cells. If inferential intervals are supportable, use 98.3333%
Bonferroni-adjusted intervals for that three-contrast family. Per-cell findings
remain descriptive. Do not reinterpret overlapping per-arm intervals as the
paired difference test. Repeated templates remain a generalization limitation
even when a source bootstrap is computable.

These intervals condition on one fixed development order, seed, reference
inventory, and judge. They do not quantify adaptation-order variability, judge
bias, natural-document diversity, or uncertainty due to reference incompleteness.
Three epochs and three ablation branches do not create independent test samples.

To describe a component as useful in this diagnostic, require positive paired
grounded-recall change and no decrease in supported-allegation rate, Credibility,
or Conformability, with comparable complete coverage. Otherwise report the
trade-off, unresolved evidence, or null/negative result. Do not claim "substantial"
gains without a preregistered practical-effect threshold and additional validation.
Do not claim all components succeed when only one model/corpus benefits.

## 12. Fixed workload and time policy

| **Main work item** | **Scheduled count** |
| --- | ---: |
| Unique development / evaluation packets | 80 / 400 |
| Isolated learned memory branches | 36 |
| Development episodes: 4 corpora x 3 models x 3 branches x 20 x 3 epochs | 2,160 |
| Full WarrantRoute evaluations: 12 x (100 + 100 + 20 + 100) | 3,840 |
| No-reflection and rewrite E3 evaluations: 12 x 2 x 100 | 2,400 |
| Baseline outputs: 12 x 3 x 100 | 3,600 |
| Total evaluation outputs / judge calls | 9,840 / 9,840 |
| Reference calls: 480 x 3 | 1,440 |
| Maximum WarrantRoute evaluation calls: 6,240 x 5 | 31,200 |
| Baseline generation calls: 12 x 100 x (1 + 1 + 4) | 7,200 |
| Maximum development calls: 2,160 x (5 + 1) | 12,960 |
| Maximum total semantic calls, no retries | **62,640** |

Full E0/E1 reuse means zero extra calls for frozen-seed and one-epoch controls.
Reference preparation is not multiplied by models or epochs. Physical memory
snapshots number 120: twelve shared seed snapshots and three epoch snapshots
for each of 36 learned branches. An error/skip may reduce executed calls, not
silently reduce scheduled denominators or represent completed adaptation.

Exact new-stage duration is unmeasured. The earlier 180-354-hour v4 estimate
excludes the new ablation branches and third reference pass and must not be
reused as a v5 ETA. Even averaging 10-30 seconds across the 62,640-call ceiling
gives approximately 174-522 serial hours. This is only arithmetic sensitivity,
not a measured forecast, bound, or confidence interval. Long rewrite outputs,
reference/judging work, source checks, and machine downtime can increase time.

Before authorizing the main run, report measured per-model/per-stage median and
upper-quartile times from eligible development-only smoke work. Calculate
remaining loop, learning, reference, and judge counts separately. Use remaining
count times the applicable stage rate and report an explicit provisional range
where measurements are missing. Do not hide pending judging in loop-only ETA.

All calls are serial and local. Paid API use is disabled. The user's USD 100
limit is not spending permission and is not consumed by this local design.
Future API execution needs a separate frozen pricing/budget contract with
pre-request reservations and a hard stop before the total limit is exceeded.

## 13. Execution, progress, failure, and export contract

Freeze installed model digests, role templates, schemas, full rendered requests,
source/claim/reference hashes, snapshot identities, code, decoding, and job IDs.
Main decoding: temperature 0, seed 20260910, requested context 32768, output cap
4096 for review/reference/judge and 8192 for every Learning Editor arm. These
are common ceilings, not guaranteed model support or measured output lengths.
The rewrite arm must fit the entire allowed memory representation. If it cannot,
revise the prospective contract before launch, not truncate it or change only
that arm's settings mid-run. Pilot retains a 2048 output cap as a separate scope.

Use exclusive supervisor/worker locks, atomic append-only events, parent-linked
memory versions, and a saved request journal before dispatch. Verify frozen
hashes on resume. Never overwrite successful raw outputs. No semantic retries
or automatic regeneration of invalid/unfavorable answers. Retry count is zero
in this design. Ambiguous in-flight calls stop for reconciliation. Three
consecutive technical trajectory failures stop the affected run for diagnosis.
A contract/hash/leakage failure stops immediately. Do not endlessly restart.

A rejected memory patch leaves a recorded no-op, not a fabricated successful
update. Human escalation/cannot_judge is neither successful detection nor
automatically a technical error. Route and reference failures remain visible.
Judge complete evaluation outputs as they arrive, interleaving corpora/models
where practical. Each set of fifty completed evaluation outputs produces an
immutable interim summary. Such judging observes a frozen design and cannot
change learning. Keep all final judgments, not only favorable ones.

On a separately authorized launch, a five-minute monitor reports development
episodes, evaluation outputs, judged outputs/binary pairs, current stage and
model/corpus, failures, rule changes, and phase-specific remaining time. Report
even when no item finished, and inspect in-flight calls before claiming a stall.
This design update does not create or resume an automation or worker.

New private exports: final_comparison.csv/.md (48 rows), ablation_comparisons.csv
(36 paired contrasts), fixed_probe_curve.csv (48 rows), reference_coverage.csv,
quality_missingness.csv, call_costs.csv, and final_manifest.json. Each row carries
task/target version, n, reference counts, matching rule, judge, branch/checkpoint,
input/prompt/model hashes, and the within-source or constructed-claim qualification.
Store source text only in restricted audit artifacts, not public summaries.

Verify 36 newly generated baseline rows and twelve Full E3 rows for the main
comparison, plus all component/probe rows and exact denominators. A complete
export with unresolved quality is completed_with_unresolved_quality, not all
cells validated. No historical Table 3 replacement, manuscript build, or paper
result claim is authorized by this document.

## 14. Launch gates and present implementation boundary

| **Gate** | **Required evidence before inference/export** | **Status at design finalization** |
| --- | --- | --- |
| Scope and scientific decisions | This protocol, plan, and prompt contracts | Specified |
| Input eligibility and split freeze | Exact claim/qualifier audit, blind task payloads, shared eligible IDs, source/text overlap report | Not certified |
| Main runtime | Four method bundles, three isolated learning branches, checkpoint reuse, one-call editor, spans and unknown handling | Not fully implemented |
| Pilot runtime alignment | Three-corpus default, 465-call plan, tri-state judge, v5 provenance | Pending |
| Reference and matcher | Blind proposal/reconciliation, one-to-one grounded matching, denominator and missingness tests | Pending integration |
| Leakage and resumption | Permission-separated evaluation references, immutable memory, hash/lock/ambiguous-call fault tests | Must pass on final runner |
| Fit and timing | Complete inputs and whole-memory output fit, installed-model digests, measured stage timing | Not measured for v5 |
| Inference authorization | Explicit selection of pilot or main with its own resource budget | Not given by this design request |
| Publication eligibility | Authorized non-constructed natural claims and applicable governance evidence | Not met by current candidate banks |

The old v4 scheduler and the earlier four-corpus, forced-binary pilot are not
v5 executors. Do not run them under a v5 label. Offline plan checks can establish
arithmetic and internal consistency only. Scientific success must be established
from the later frozen experiment, not from these documents or passing code tests.

## 15. Design verification record

On 2026-09-10 KST, `check_design_v5.py` recomputed both workload plans and passed
the scope, ablation, checkpoint-reuse, unknown-handling, and arithmetic checks.
The local unittest discovery passed 31 offline tests, including ten new v5
design tests and 21 existing scheduler/pilot tests. Ten local documentation
links and the five listed packet-bank paths resolved. No inference, reference
creation, experiment launch, paid request, manuscript change, or table update
was performed. These are document/code checks, not data or performance validation.
