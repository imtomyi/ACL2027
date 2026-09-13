# WarrantRoute: Consolidated Diagnosis and Single-Call Learning

Schedule amendment: [v4 multi-epoch adaptation](warrantroute_claim_detection_multi_epoch_v4.md)
replaces the single-pass development schedule and its checkpoint workload.
The adopted finalizer and exploratory status of the Learning Editor remain unchanged.

Date: 2026-09-09. Version: 3.0.
Status: prospective design amendment. No experiment has been started.

## Decisions and scope

The user requested one call for diagnosis integration plus final verification,
and exploration of reducing the three additional development calls to one.

- Adopted in the design: replace the separate diagnosis merger and verifier
  with one Evidence-Grounded Finalizer call. Runtime implementation is pending.
- Recommended candidate, not yet adopted: replace development feedback,
  reflector/curator and semantic guard calls with one Learning Editor call,
  followed by deterministic validation. Test feasibility before choosing it.
- Unchanged: four datasets, three same-model conditions, the three baselines,
  480 unique candidate packets, P0/P5/P10/P15/P20 schedule, 6,720 evaluation
  output slots, reference preparation and external evaluation judging.

This document amends sections 4, 5 and 9 of the
[v2 protocol](warrantroute_claim_detection_learning_curve_v2.md).
All other v2 requirements remain applicable, including claim immutability,
split eligibility, exact-text preservation, failure accounting, same method
prompts across models, private-diagnostic status and manuscript restrictions.
The v2 poster depicts the previous structure and is not the current call-budget
specification. Historical runs, prompts, results and tables remain untouched.

## 1. Adopted five-call review structure

```text
Immutable claim + evidence + retrieved Playbook rules
    |
    +--> Initial Reviewer ------------------+
    +--> Independent Evidence Scout --------+
                                           |
                           Deterministic routing
                                           |
                         Methods Challenger (optional)
                         Domain Challenger  (optional)
                                           |
                         Evidence-Grounded Finalizer
                                           |
                         Locked final diagnosis
```

The initial two agents remain separate calls with no access to one another's
outputs. Challengers retain the v2 routing policy. The last agent receives all
available candidate allegations plus the original claim and complete evidence.
In ONE structured response it reconciles duplicates, checks each allegation
against the evidence, retains supported allegations, downgrades uncertainty
and explains rejections. It cannot request a second verification call.

With no routed challengers there are three review calls; with one there are
four; with both there are five. These are serial-call counts for estimation,
not authorization to add parallel workers. External scoring is not included.

The finalizer must provide a disposition for every namespaced candidate issue
ID: retain, discard or unresolved. Final issues cite their originating candidate
IDs. Merging compatible allegations is allowed; inventing an unrelated issue
or new source evidence is not. A negative diagnosis must explain why the
available concerns do not establish a flaw. Output structure and quotation
checks run in code without another LLM call.

This removes a separate second-pass review. One response that reports its own
checks is not independent verification, and the change may affect accuracy.
Keep unresolved allegations visible rather than converting self-confidence to
validation. The final fixed evaluator still scores the locked diagnosis.

The shared prompts are specified in
[the v3 prompt document](warrantroute_claim_detection_consolidated_prompts_v3.md).
They are prospective prompt contracts, not hashes of an implemented runner.

## 2. Recommended development candidate: one Learning Editor

The three previous calls were: fixed-model feedback, same-model updater and
same-model semantic guard. Replace these with one call only AFTER the final
prediction is durably locked:

```text
Locked DEVELOPMENT prediction + current DEVELOPMENT reference
                  + original claim/evidence + current Playbook
                                   |
                         Learning Editor (1 LLM call)
                                   |
                  Feedback record + bounded rule patch proposal
                                   |
                   Deterministic validator (0 LLM calls)
                                   |
                     Apply patch OR keep memory unchanged
```

The Learning Editor uses the tested condition's model, not a mixture of model
families. Its single response contains reference-relative errors, evidence
anchors, proposed reusable lessons, counterconditions and a bounded patch.
It replaces the earlier fixed-Qwen development-feedback call; this is a change
in feedback policy, not merely repackaging identical computation. Use the same
candidate policy for all tested model families if adopted.

The reference already exists under the unchanged two-pass preparation protocol.
It is not generated inside the one-call learning step, and its cost is not
removed from the estimate. Expose only this completed development packet's
reference, not future development feedback or any evaluation reference.
Keep model-reference disagreements unresolved. An unresolved reference cannot
justify a rule asserting a disputed flaw as established.

Compare the prediction to the reference, then propose a rule in a single
response. This ordering is an output contract, not evidence of independent
reasoning passes. Do not treat the editor's self-check as a separate guard or
as external Credibility/Conformability scoring. Learning feedback is not a result
row. Official evaluation remains model-blind and separate from the learner.

## 3. Checks that can move to code

The runner, not the model, verifies all of the following:

- The packet belongs to the development allowlist; the prediction was locked
  before reference access; claim/evidence and prediction hashes match.
- Inputs contain no evaluation answer, score, trajectory or future feedback.
- JSON keys, types, required fields, enums and operation counts are valid.
- Every source ID, quote and span exists exactly in the stored source field.
- A patch's parent hash matches the current immutable Playbook snapshot.
- Referenced rule IDs exist; new IDs are generated by the runner, not trusted
  from model text; seed rules cannot be overwritten or deleted.
- At most two rule operations occur per packet. Support only add and replace
  of non-seed rules; do not allow wholesale rewriting or arbitrary code/actions.
- Capacity remains at most 40 active rules, with the unchanged retrieval limit
  of six. At capacity, an add-only patch fails instead of silently evicting rules.
- Exact duplicate normalized rule text, known packet/source IDs and exact stored
  source quotations in retrieved rule text are rejected. Retain the normalization
  policy in the freeze; never normalize the underlying evidence to match quotes.
- Provenance, feedback and exact source excerpts live in a non-retrieved audit
  record. Commit the complete valid patch atomically and record its parent hash.

Invalid output means no memory update, an explicit error record, and retention
of the original prediction. No automatic LLM repair/guard fallback may quietly
turn the one-call step into several calls. Apply the frozen technical retry
policy separately and expose retries in call counts.

These checks DO NOT establish semantic correctness, rule generality, materiality
or freedom from paraphrased memorization. The Learning Editor must reason about
these in its one response, but its answer can be wrong. This is the main tradeoff
of the candidate. Never label deterministic acceptance as human approval or
independent semantic validation.

## 4. Alternatives considered

| Option | Additional development LLM calls | Assessment |
| --- | ---: | --- |
| Learning Editor plus code checks | 1 per packet | Recommended candidate; semantic guard is no longer separate |
| Fixed-Qwen editor for all conditions | 1 per packet | Keeps feedback source constant but introduces a shared external learning agent; not the same-model design |
| Batch editor after five packets | Potentially 1 per batch | Changes online memory exposure, increases context size and combines several diagnoses; defer as a separate design |
| Generate feedback before locking detection | Potentially fewer | Reject: leaks the answer into the prediction |
| Use the learner as the official evaluation judge | Potentially fewer | Reject: conflates memory updates and evaluation |
| Hidden second-call semantic repair | More than 1 | Reject as an undocumented one-call claim |

The one-call candidate preserves per-packet memory updates, unlike batch
curation. It should not be sold as equivalent-quality compression without a
pilot. More detailed output can offset savings from fewer requests.

## 5. Call counts and timing

| Quantity | Previous v2 | Adopted finalizer only | Candidate with Learning Editor |
| --- | ---: | ---: | ---: |
| Maximum WarrantRoute review calls | 6 | 5 | 5 |
| Extra development calls | 3 | 3 | 1 |
| Maximum calls per development episode | 9 | 8 | 6 |
| Main experiment maximum semantic calls | 35,760 | 32,400 | 31,920 |

Total counts include the unchanged 7,200 baseline calls, 6,720 external
evaluation calls and 960 reference-preparation calls. Review calls cover
3,120 WarrantRoute evaluation slots and 240 development episodes. Counts assume
all optional challengers and exclude retries. They do not count code checks as
LLM calls. The approved finalizer saves up to 3,360 calls. The development
candidate saves another 480 calls, so its whole-experiment impact is smaller.

The [read-only estimator](estimate_claim_detection_runtime.py) now reports all
three scenarios. To avoid assuming that a merged task costs exactly as much as
a smaller old task, its unmeasured merged-finalizer service proxy is 1.25 times
the slower of historical scout/reviser means. The one-call Learning Editor
proxy is 1.5 times the model's overall call mean. Keep the v2 1.0/1.75 planning
multiplier and 15/45-second external judging scenarios. These are assumptions,
not measurements, confidence intervals or upper bounds.

| Main experiment scenario | Provisional local serial inference |
| --- | --- |
| Previous v2 | About 154-307 hours |
| Adopted finalizer only | About 147-293 hours |
| Candidate finalizer plus Learning Editor | About 145-290 hours |

The combined candidate cuts maximum development calls by one third, but does
not cut total runtime by one third. Baselines, external judging, reference
preparation and repeated checkpoint evaluations remain. Estimated whole-run
savings under these assumptions are about 9-17 hours relative to v2; actual
savings can be smaller, absent or negative if consolidated outputs are slow.
Pilot timings remain roughly 6-12 hours. Additional comparative pilot calls
described below are not included in those main-run estimates.

## 6. Candidate feasibility check before adoption

No inference is authorized by this amendment. When a pilot is separately
authorized, use development-partition data only and freeze candidate prompt
limits before collecting scores. The proposed 1,536-token cap from v2 is still
a pilot starting point, not evidence that the combined response will fit.

Test exact spans, all-candidate coverage, no-issue cases, mutually contradictory
allegations, unresolved references, unchanged memory, invalid patches, duplicate
rules, capacity limits and hash conflicts. Test that an invalid patch cannot
change the locked prediction or leak into a future retrieved Playbook.

For the development consolidation comparison, branch from the SAME memory and
locked five-call diagnosis. Compare the three-call learning path with the
one-call editor on the same current reference and development packets. Use
separate branch memories and held-out development-only probes. Keep all results
and overhead; do not label the repeated item as a new independent sample.

Inspect schema completion, wall time, output tokens, proposed/applied rules,
unsupported rules, reference-relative grounded detection and unsupported
allegations on those probes. Code-only pass rates cannot decide semantic
equivalence. Tiny pilot counts show feasibility, not statistical non-inferiority.
Report the tradeoff and choose/freeze a policy before main evaluation, without
using the 100-item evaluation panels for this decision. Do not automatically
adopt the candidate just because it is faster or produces more rules.

## Current operational state

Only design documents, prospective prompts and the read-only cost estimator
were changed. No experiment runner, frozen manifest, original output, target
table, API budget or progress automation was modified or resumed. The runtime
still needs implementation and qualification before any new experiment.
