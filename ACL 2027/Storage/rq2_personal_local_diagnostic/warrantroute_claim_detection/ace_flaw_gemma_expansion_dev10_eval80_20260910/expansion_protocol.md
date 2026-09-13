# Same-Protocol ACE Flaw-Detection Expansion

Date: 2026-09-10 KST. Status: authorized allocation, pending live preflight and
launch confirmation in the launch record. User request: run more data under the
same experiment and consider reducing withheld cases. This document records
the expansion and a separate, NOT IMPLEMENTED, semantic-improvement proposal.

## Scope and Identity

New directory:
`Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910`.

Previous completed directory, never resumed or overwritten:
`Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_8h_gemma_20260910_v2`.

The task remains detecting and characterizing flaws in supplied claims using
their evidence. It is not generating themes or repairing documents. All agents
use local Gemma 3 4B. Reference, Detector, Finalizer, Learning Editor, Patch Auditor
and combined quality-judge prompts and schemas are exactly those frozen in v2.
The semantic implementation `ace_flaw_contract.py` must have the same byte hash.
Temperature 0, seed 20260910, context 32768, output ceiling 8192, model digest,
seed memory, retrieval, audit requirements and nullable scoring remain unchanged.
Only input allocation, exclusion provenance, count-aware scheduling/reporting,
call limits and preflight launch checks are updated. There are no paid API calls.

## Allocation and Repetition

| Dataset | New development packets | Development exposures | New evaluation packets | E0/E3 reviews | Optional E1/E2 reviews |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dreaddit | 10 | 30 | 80 | 160 | 10 |
| GoEmotions | 10 | 30 | 80 | 160 | 10 |
| CaChe | 10 | 30 | 80 | 160 | 10 |
| ParlaMint-GB | 10 | 30 | 80 | 160 | 10 |
| Total | 40 | 120 | 320 | 640 | 40 |

There are 360 new unique packets. Each development packet appears once in each
of three epochs. Each evaluation packet receives one diagnosis and one combined
Credibility/Conformability judgment at E0 and at the common adapted checkpoint.
Five fixed evaluation packets per corpus may also run at E1/E2 after core work.
These are repeated measurements, not extra independent samples or adaptive
selection of the best checkpoint. Budget fallback uses the existing common-epoch
rule; it is never relabeled completed E3.

Each corpus starts with the same two seed rules, then learns from its ten NEW
development packets. No old reference, review, quality score or learned memory
is imported. Evaluation feedback never updates memory. Old and new E3 results
must stay separate because their learned memories may differ. Although the
two cohorts cover 100 distinct evaluation packets per corpus together, a pooled
single-Playbook n100 performance claim is not justified.

## Selection and Provenance

The candidate inventory remains
`Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909_v6`,
which records twenty development and one hundred evaluation candidate packets
per corpus. Deterministic selection excludes every packet ID used in either
phase of completed v2, without inspecting outcome scores. Source JSONL hashes,
selected IDs, original packet hashes, task hashes and overlap checks are frozen.

The selected corpus banks under `Storage/draft_review_packets/` are:

- Dreaddit: `dreaddit_dev580_working_v1`, its development JSONL and balanced_n100 evaluation subset.
- GoEmotions: `goemotions_train_all_working_v1`, its development JSONL and balanced_n100 evaluation subset.
- CaChe: `agyw_focus_groups_eval765_working_v1`, its development JSONL and balanced_n100 evaluation subset.
- ParlaMint-GB: development from `parlamint_gb_eval100_working_v1`; evaluation from the balanced_n100 subset of `parlamint_gb_fullsample_eval100_working_v1`.

All four new selections have zero packet-ID, exact-text and source-record
overlap with completed v2. New development/evaluation text and source-record
overlap is also zero. Their source groups are disjoint except CaChe, whose eleven
overlapping source groups remain the user-authorized within-source diagnostic.
This does not imply source independence between old and new experiments:
CaChe shares eleven source groups with v2 and ParlaMint-GB shares eight. The
candidate panels may have been exposed in earlier TA/n100 diagnostics. These
are not untouched final-test data or an independently sampled new corpus.

The new CaChe evaluation panel has 320 excerpts but 319 distinct exact
texts. Its within-panel repetition is disclosed rather than silently removing a
packet. Claim templates are also reused: five distinct claim strings for each
of Dreaddit, GoEmotions and CaChe, and six for ParlaMint-GB. More evidence packets
do not establish equivalent diversity of claim constructions.

## Budget and Launch

Core maximum: 2,760 model calls. Optional maximum: 120. Total ceiling: 2,880.
Reference calls are cached once per unique packet; development review calls
240, learning calls 120 and patch audits at most 120; core review calls 1,280
and combined judging calls 640. Rejected audits do not cause retries.

The new supervisor starts a separate eight-hour clock AFTER preflight. Resume
never resets it. Development admission ends at 3h30m, inference at 7h45m, with
15 minutes reserved for finalization. Previous role-duration estimates suggest
about six hours for this workload, provisionally. This is not a completion
guarantee; later reports must use actual phase timings and remaining counts.

Required gates: the full offline suite, a full mocked expanded schedule,
identity/overlap/count checks, input admission checks, and a live development-only
preflight on two scheduled packets per corpus. The eight preflight diagnoses
and eight combined judgments must be technically valid, not necessarily true
or binary. No evaluation items enter preflight. Exact code, input, prompt,
model and decoding hashes must match launch. Single-worker locks apply.
No old/smoke outputs enter the experiment. Ambiguous dispatch is not retried.

## What Withholding Means

The previous v2 completed 120 development exposures and 160 core reviews with
zero technical trajectory failures. However, technical completion did not
establish semantic correctness or Playbook learning:

- Every core final decision was `no_flaw_established`, with zero grounded flaw matches.
- Credibility was null in 96/160 core reviews; Conformability was null in 30/160. At least one dimension was null in 96/160.
- All resolved binary scores happened to be true. A conditional 100% is NOT a full-panel score or verified flaw-detection accuracy.
- Every Playbook remained seed-only with zero accepted new rules and zero learned-rule retrieval.
- There were 119 proposed edits in 87 withheld batches: 73 duplicate-rule batches, eight invalid-evidence batches and six semantic-audit holds.
- An additional 33 development exposures skipped learning because references were unavailable. They are not 33 additional withheld edit batches.
- Overall, 38/120 unique-packet references were unavailable due to reference-integrity findings, including 11/40 development references reused across three epochs.

Some final rationales explicitly describe an unsupported claim while the
decision says no flaw was established. Some null quality rationales are
positive assessments. These are examples of semantic inconsistency, not proof
that every null should have been true or every discarded flaw should be retained.
The additional same-protocol data will measure whether these patterns persist.
Increasing sample count alone does not fix this failure mode.

## Separate Improvement Proposal: Not Active

The following changes require a separately versioned protocol and development
validation. They must NOT be slipped into this same-prompt expansion.

1. Make each issue disposition justify the precise evidence-to-claim warrant and
   the reason for retaining, discarding or leaving it unresolved. Test explicit
   contradictions between the decision, allegation and rationale. Preserve the
   raw judgment and flag inconsistency; do not infer a corrected boolean from prose.
2. Require criterion-level quality decisions and explicit unresolved-reason codes,
   separating insufficient evidence, incomplete reference, semantic contradiction
   and an actually inapplicable criterion. Validate aggregation before launch.
   Keep true, false and unresolved distinct. Literal placeholder reasons should
   not satisfy a meaningful explanation check in a new contract.
3. In development, make delta proposals identify what NEW reusable condition
   they add beyond a named existing rule. An exact duplicate is a no-op, not
   successful learning. Record proposed duplicate/no-op separately from safety
   rejection, without rewriting historical batch counts or admitting weaker rules.
4. Separate exact source-span evidence from reusable rule wording. Check excerpt
   IDs and exact quote spans mechanically before semantic audit. Unsupported
   patches stay withheld; adding the source text to memory is not a valid fix.
5. Improve reference consistency on development data, especially disagreement
   between disposition and issue inventory. Use blinded human adjudication or a
   separately authorized independent judge as a SECONDARY analysis of a
   prespecified panel, retaining the original judgments. Do not retry only null
   or unfavorable cases until a favorable answer appears. Do not use paid APIs
   without a new explicit authorization and the project's cost controls.
6. Test all future changes on development items, freeze them, then assess on an
   outcome-independent evaluation panel. Report coverage, null rate, contradiction
   rate, retained/grounded flaws, accepted novel rules and actual retrieval.
   A gain in resolved-case percentage alone is not evidence of improvement.

Some evidence is genuinely insufficient. Eliminating all unresolved cases by
forcing binary decisions, weakening audit, dropping packets or hiding blanks
would make results less trustworthy. The goal is fewer avoidable failures and
more well-supported decisions, not a cosmetically complete table.

## Outputs and Interpretation

The new run maintains four ACE rows, four Playbook rows, eight E0/adapted quality
rows, paired-change and optional fixed-probe exports. Quality reports must show
T/binary-N, coverage, null, technical and pending counts alongside percentages.
Final export hashes are verified. No historical output or Table 3 is overwritten.

These are constructed-claim, same-model, private working diagnostics. References
are provisional, not independent gold annotations. No external baseline run,
full WarrantRoute comparison, ablation gain or repair validation is produced.
All results remain under Storage and are manuscript-ineligible under AGENTS.md.
