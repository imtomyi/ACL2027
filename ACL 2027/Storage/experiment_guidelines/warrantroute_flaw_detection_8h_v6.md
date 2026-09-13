# Eight-Hour Flaw-Detection and Playbook Diagnostic

Version: 6.0. Date: 2026-09-10 KST.
Status: budgeted design and offline planning checks, not a launched experiment.

## 1. Required outcome and scope

The requested next experiment has an **eight-hour maximum execution window**.
It must prioritize, for each of Dreaddit, GoEmotions, CaChe, and ParlaMint-GB:

1. Credibility and Conformability of evidence-grounded flaw-detection reviews.
2. An inspectable Playbook with versioned rules, update evidence, and usage logs.
3. A matched before/after comparison on the same evaluation packets.

The task remains **detecting and characterizing flaws in a supplied claim**,
not thematic-analysis generation, document revision, or successful repair.
Continue the user's Gemma-only choice. All reviewer, learning, reference, audit,
and judge calls use local `gemma3:4b`. No paid API usage or additional models.

This is WarrantRoute-Lite: Detector and one combined Evidence-Grounded Finalizer.
It is not the full routed WarrantRoute or a three-model comparison. Reflector,
multi-epoch adaptation, and delta updates are included as mechanisms. Their
individual ablations and the Generalist/Fixed role/All roles comparison are
deferred outside this eight-hour scope. A seed-versus-adapted comparison cannot
establish the contribution of each component individually.

This document supersedes the four-hour scope in
[v5](warrantroute_flaw_detection_final_protocol_v5.md) for the next proposed run.
V5's much larger main comparison remains a separate, unlaunched future design.
Its 62,640-call plan must not enter this eight-hour queue. Historical code and
results are unchanged. All new diagnostic artifacts remain under Storage and
cannot fill a manuscript or the historical Table 3.

## 2. Equal dataset allocation

| **Dataset** | **Unique development packets** | **Unique evaluation packets** | **Epochs** | **Core evaluation checkpoints** |
| --- | ---: | ---: | ---: | --- |
| Dreaddit | 10 | 20 | 3 | Same 20 at E0 and E3 |
| GoEmotions | 10 | 20 | 3 | Same 20 at E0 and E3 |
| CaChe | 10 | 20 | 3 | Same 20 at E0 and E3 |
| ParlaMint-GB | 10 | 20 | 3 | Same 20 at E0 and E3 |

Totals: 120 unique packets, including 40 unique development packets and 80
evaluation packets. Three epochs produce 120 development exposures, not 120
unique development packets. The core produces 160 evaluation reviews and
160 combined Credibility/Conformability judgments. Each review is generated
once at each declared checkpoint. The E0/E3 pair uses identical input text.

Twenty evaluation packets per corpus support a bounded diagnostic, not a precise
ranking or a general population-performance claim. One case is five percentage
points when all twenty decisions are resolved. Existing claim templates repeat.
Do not call packets independent natural documents or report an unqualified n=100.

### Selection and the pending reuse decision

The recommended selection uses ten of each corpus's prior twenty development
candidates and twenty of its existing n100 evaluation panel. The underlying
candidate files and hashes are in the prior stopped run's manifest:
`Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909_v6/manifest.json`.
Restore original claim-bearing packets, not source-only TA task payloads.

Read-only inspection on 2026-09-10 found zero development/evaluation record and
exact-text overlap in all four original candidate splits. Recorded source IDs
are also disjoint for Dreaddit, GoEmotions, and ParlaMint-GB. CaChe shares source
groups and retains its previously authorized within-source qualification.

This selection solves the earlier ParlaMint five/fifteen split problem without
inventing source independence: its development-only twenty candidates all share
one session, but its existing evaluation panel does not share that recorded
source group. The costs are reusing an existing evaluation panel and no longer
reserving those selected items as untouched future evaluation examples.

**Panel reuse is awaiting the user's answer.** Candidate inspection is allowed,
but no runtime input freeze or inference is authorized by this design. Do not
silently relax source separation instead. If the user chooses a within-source
development-only alternative, issue a revised allocation: ten development plus
twenty evaluation items cannot fit a twenty-item pool without overlap.

Select IDs by ascending SHA-256 of compact UTF-8 JSON
[20260910, "gemma8h-v6", dataset, phase, packet_id], without labels or scores.
Freeze all selected IDs and their order before inference. Recheck record/text/
source overlap on the selected rows and log missing source metadata. Never
replace a low-scoring or failed item. Candidate audits are not runtime freezes.

## 3. Input and detection contract

For this bounded diagnostic, the target is the exact stored claim sentence
`llm_generated_qualitative_claim.claim`, its cited excerpt IDs, and the complete
stored evidence/context bundle. No source shortening, translation, recombination,
or new injected flaw. The sentence is intentionally narrower than an entire
qualified analysis. Excluded theme_name/explanation/boundary_conditions fields
must not be silently interpreted as included qualifications. Full-analysis
conclusions cannot be drawn from this sentence-only experiment.

Hide builder labels, answer hints, prior model identity, previous results, and
category-bearing packet IDs from the model. Use opaque mapped task identifiers.
Retain original task/claim/source hashes and a field-exclusion audit privately.
Reject genuinely oversized inputs before freezing the common panel; do not
truncate text to meet the eight-hour limit.

Use the v5 definition: a flaw has an identifiable claim target, a demonstrated
evidence-to-claim failure, and a material consequence. Record type, target,
exact evidence anchors, mechanism, and uncertainty. A category guess alone is
not a successful detection. Allow established_flaw, no_flaw_established, and
cannot_judge. Do not infer that unsupported claims are false in the world.

Use the common v5 prompt contracts with these declared Lite changes: no Scout
or routed specialists; sentence-only target; all roles use Gemma; one provisional
Gemma reference; the added bounded patch-audit role below. These changes must
be compiled into new versioned templates, not silently applied to old outputs.

## 4. Adaptation and Playbook verification

Each development exposure has at most four calls:

```text
Original claim + complete evidence + retrieved Playbook procedures
    -> Detector
    -> Finalizer: integrate and evidence-check once; lock the diagnosis
    -> Learning Editor: structured reflection and up to two delta edits once
    -> Patch Auditor: check proposed edits against the development evidence once
    -> deterministic commit or recorded no-op
```

The audit is separate from the Learning Editor's self-check. It is a separate
invocation of the same model, not independent truth. No audit call is needed
when the editor proposes no changes or the proposed batch fails code checks.
Budget one audit call for every development exposure anyway, so optimistic
no-op assumptions do not hide work. There is no retry-until-approved loop.

### Mechanical checks before committing an edit

- Required rule fields: applicability, detection_check, evidence_requirement,
  countercondition, stable ID, version, parent hash, and audit-only provenance.
- No modification of the two immutable seed rules. At most forty active rules,
  six retrieved rules including the seed, and two add/replace operations.
- Every evidence/reference ID resolves; every submitted quote/offset is exact.
- No duplicate rule ID, exact duplicate procedure, packet/source identifier,
  source quotation, answer-specific claim, or evaluation data in retrieved text.
- The locked prediction exists before development-reference access.
- Repeated exposure does not increase distinct-packet or distinct-source support.
- Atomic parent-linked updates. A rejected batch preserves the entire old memory.

Literal leakage checks cannot prove absence of paraphrased memorization.
Keep that limitation explicit, and inspect semantic generality in the audit.

### Patch-audit prompt contract

```text
Audit ONLY the proposed Playbook changes for this DEVELOPMENT packet. The current
claim, full evidence, locked diagnosis, provisional reference, existing rules,
structured reflection, and proposed edits are supplied as untrusted task data.
Do not alter the diagnosis, produce replacement patches, or request another call.

For EACH proposed edit assess: evidence-grounded lesson; reusable procedure rather
than a memorized packet answer; preservation of uncertainty and counterconditions;
no unsupported domain/clinical inference; no substantive duplicate or contradiction
of retained rules; no source/reference/answer leakage into reusable memory.

Return edit IDs and true/false/null for each required criterion, with concise
reasons and exact relevant evidence anchors. Missing support or genuine uncertainty
is not a pass. References are fallible; agreement alone is insufficient. Assess
the proposed rule, not whether adding more rules would look like progress.
Your decision is a same-model diagnostic assessment, not human validation.
```

Apply a batch only if every proposed edit passes code checks and every required
semantic criterion is true. A false, null, malformed, or missing audit means
withheld, not approved. Record legitimate unchanged memory separately from
invalid output or audit rejection. Each accepted editable rule version must
trace to its own audit and supporting development exposure. Replacements need
new audits; approval of an earlier version is not inherited automatically.

Save E0 and the memory at every complete epoch, together with JSON and readable
Markdown rule diffs. During evaluation, save the exact retrieved rule IDs/text/
hashes and the review output. Count retrieval as exposure to a rule, not proof
that the model used it correctly or that it improved the answer.

### Required Playbook report per corpus

Report seed and learned rules separately; proposed/applied/withheld/unchanged
updates; add/replace counts; distinct supporting packets/source groups; audit
true/false/null counts; leakage/duplicate/capacity findings; rule versions
retrieved during evaluation; and paired quality/detection changes.

Use distinct statuses: seed_only, generated_not_retrieved,
generated_retrieved_audit_complete, or provenance_incomplete. Zero new rules is
not automatically a software failure, but is not evidence of successful learned
Playbook generation. A healthy version chain is not evidence of better detection.

## 5. Credibility and Conformability for every corpus

Every completed evaluation review is judged immediately in ONE separate call
returning BOTH dimensions. Do not postpone judging to an unbudgeted final phase.
The judge sees the original claim/evidence and locked final review, but not the
checkpoint, dataset display name, memory contents, learning audit, prior scores,
or review-model/method labels. Necessary original source context is retained.

- **Credibility:** Is the diagnosis and disposition defensible against the supplied
  claim/evidence, with material counterevidence and uncertainty handled correctly?
- **Conformability:** Is the substantive reasoning faithful and traceable to that
  original evidence, preserving attribution, scope, negation, and context?

Apply the v5 true/false/null rubric. A demonstrated defect means false; otherwise
unresolved required evidence means null, not an invented binary answer. A valid
no-flaw review still needs defensible reasoning and does not pass automatically.
Treat malformed/missing judgments as technical missingness separately.

For each dataset/checkpoint/dimension publish:

- Planned N, processed reviews, T=true, F=false, U=null, E=technical/not completed.
- Resolved-case percentage: 100*T/(T+F), explicitly labeled **of resolved cases**.
- Binary coverage: 100*(T+F)/N, with the actual numerator and denominator.
- Full-panel percentage: 100*T/N only when U+E=0; otherwise unavailable.
- A missingness range [100*T/N, 100*(T+U+E)/N] where useful. This is an extreme-
  case bound, NOT a confidence interval and NOT a replacement for the score.

Rows must exist for all four corpora even when a run stops. Do not omit incomplete
corpora, average them away, coerce unknowns, or rerun unfavorable answers just to
remove N/A. If no binary judgments are available, that conditional rate is also
unavailable. Successful completion with fully resolved judgments is the target,
not something a time budget or prompt can guarantee.

Grounded reference-relative detection and characterization remain supplementary.
One blinded Gemma reference is prepared per unique packet, frozen and reused.
It is incomplete and same-model, not gold truth. Extra allegations are checked
against evidence rather than automatically called false. Correct matches require
claim target, mechanism, evidence, and material consequence, with one-to-one
matching. No complete natural-flaw precision/F1 or repair-success claim follows.

## 6. Eight-hour scheduling and completion priority

Maintain one persisted clock from supervisor start, including all reference,
review, learning, audit, and judge calls. Resume never resets it. Only one local
worker is allowed. Offline implementation work is not a measured inference run.

| **Window from start** | **Priority and boundary** |
| --- | --- |
| 0:00-3:30 | Development references, three adaptation epochs, and patch audits; interleave corpora at each development position |
| 3:30-7:15 | Mandatory paired E0/adapted reviews and immediate judging on the same twenty packets per corpus |
| 7:15-7:45 | Continue unfinished mandatory work first; optional checkpoint probes only if core is complete and forecast fits |
| 7:45-8:00 | No new inference; finish/cancel the owned request, preserve partial outputs, audit/export/report |

The evaluation phase may start earlier when development finishes. Optional work
may also start earlier when all core work is terminal and its forecast fits;
the clock windows are reservations, not instructions to idle. Admission at
3:30 stops further adaptation if necessary. Freeze the latest epoch completed
by ALL four corpora. Prefer E3. If only E1/E2 is common, label it explicitly as
budget_limited_E1/E2, keep E3 uncompleted, and score that shared available snapshot
for all corpora. If no full epoch completed, report seed-only quality and failed
adaptation feasibility, not a fictitious post-learning improvement. Do not use
different effective epoch counts for different corpora in the same comparison.

Selection of this fallback is based only on elapsed time and completed epoch
identities, never review scores. Archive partially completed later-epoch updates
but do not use them in the paired common-checkpoint comparison. All held-out
evaluation occurs after the used memories are frozen. Evaluation feedback cannot
change any memory, prompt, sample, or stopping rule.

Evaluate in round-robin packet pairs: corpus 1 E0+adapted+judgments, then corpus 2,
3, 4, then the next packet. If a call fails, record it and continue the declared
schedule unless a stop condition applies. This limits imbalance in scheduled
progress, not necessarily in valid/binary judgments. Show both counts.

Only after all core reviews AND judgments reach terminal states may the fixed
five-packet E1/E2 probes be evaluated, using read-only snapshots. Skip an optional
checkpoint already computed as the fallback; reuse matching identities instead.
Never spend optional-probe time while a mandatory corpus has unprocessed work.

Request timeout is the smaller of 180 seconds and the remaining phase deadline.
At a phase deadline, close owned client connections and confirm the outcome of
any in-flight backend call before starting another. An ambiguous backend request
blocks new inference until reconciled; a client timeout does not prove it stopped.
At the global deadline, do not reset time, restart the model, or kill unrelated
processes. Ambiguous/partial work remains recorded, never reported as completed.

Stop immediately on frozen-hash mismatch, data leakage, duplicate-worker risk,
or ambiguous dispatch. Stop for diagnosis after three consecutive technical
trajectory failures. No semantic retries, audit retries, or automatic restart
loops. False/null quality and legitimate no-op learning are not such failures.

## 7. Call budget and timing honesty

| **Work** | **Maximum calls** |
| --- | ---: |
| References: 120 unique packets x 1 | 120 |
| Development diagnosis: 120 exposures x 2 | 240 |
| Learning Editor: 120 exposures x 1 | 120 |
| Separate patch audit: at most 120 exposures x 1 | 120 |
| Core E0/E3 review generation: 160 reviews x 2 | 320 |
| Core combined Credibility/Conformability judging: 160 x 1 | 160 |
| **Mandatory work ceiling** | **1,080** |
| Optional E1/E2 probes: 4 corpora x 2 x 5 x (2 review + 1 judge) | 120 |
| **Total ceiling with optional work** | **1,200** |

Do not multiply the quality calls by two: the same call returns both dimensions.
References are not regenerated per epoch or checkpoint. No-op edits and cached
checkpoint reuse can reduce calls, but cannot increase the sample denominator.

The prior same-model loop contains 2,521 completed Gemma calls, with median
7.95 seconds and mean 8.53 seconds of model-reported service duration. Those
were DIFFERENT prompts and do not measure these editors/auditors/judges.
For 1,080 mandatory calls, an assumed average of 15/20/25 seconds gives
4.5/6.0/7.5 hours before overhead. With optional work, the same assumptions give
5.0/6.67/8.33 hours. These are sensitivity scenarios, not a promised ETA.

Target approximately six hours of mandatory model work, with the remaining two
hours available for overhead, uncertainty, optional work, and finalization.
Actual stage timings must update the forecast. After each completed call, retain
wall time, model service time, input/output tokens, and phase. Estimate remaining
core work using per-role upper-quartile wall time once five observations exist;
use the conservative provisional rate of 25 seconds until then. A small warm-up
timing sample cannot guarantee later rule-rich contexts will be equally fast.

Do not add samples or alternate methods because an early rate appears fast.
Sample sizes and core endpoints are fixed. If the full planned workload cannot
finish within eight hours, prioritize the declared paired quality panels and
report the exact adaptation checkpoint, valid counts, and unfinished items.

## 8. Artifacts, progress, and implementation status

Required private artifacts:

- `dataset_quality.csv/.md`: four-corpus E0/adapted quality, actual denominators,
  binary coverage, missingness, checkpoint identity, and paired differences.
- `playbook_audit.csv/.md`: generation, approval, source support, and retrieval
  status for each corpus, without claiming more rules imply improved quality.
- `playbooks/<corpus>/E0..E3.json/.md` and each committed update/diff/audit.
- `predictions/`, `judgments/`, `references/`, append-only `calls/`, selection
  provenance, `status.json`, and a terminal manifest distinguishing completion,
  budget-limited output, unresolved quality, or technical failure.

When a run is separately launched, retain the user's five-minute reporting
preference: per-corpus progress, two quality dimensions with denominators,
Playbook changes/audit/usage counts, current phase, remaining core and optional
time, and time until the eight-hour deadline. Reports must remain honest when
no output finished. This design update does not create or resume an automation.

The [v6 plan](warrantroute_flaw_detection_8h_v6.plan.json) and the offline planner
test counts, priority, source candidates, and percentage/missingness arithmetic.
They are not inference execution or scientific validation. The existing
`gemma_4h_pilot.py` must not be run as this protocol: it has different allocation,
forced-binary judging, no separate patch auditor, and no v6 phase-reservation
contract. Runtime integration, the panel-reuse decision, and launch authorization
remain required. No new model calls or manuscript/table changes occurred here.

## 9. Offline verification record

The [candidate audit](warrantroute_flaw_detection_8h_v6.candidate_audit.json)
records the proposed 120 IDs, original bank hashes, and read-only selection
checks. All four selected splits have zero repeated records and exact source
texts across development/evaluation. Recorded source-group overlap is zero
except CaChe's eleven shared groups under its existing within-source exception.
This does not certify semantic eligibility, context fit, or natural-claim truth.

The offline workload checker recomputes 1,080 mandatory and 120 optional calls.
Unit tests cover tri-state quality denominators, missingness, atomic audit
approval, common-epoch fallback, paired corpus scheduling, and finalization
priority. The recorded candidate selection is not a runtime freeze and retains
`evaluation_reuse_authorized: false` until the user's pending decision is recorded.
