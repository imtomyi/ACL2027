# Online Claim-Flaw Detection: System and Experiment Design

Historical design: superseded for future execution by
[detection-first v2](ace_claim_detection_v2.md). The frozen v1 preparation is
unchanged and must not be presented as implementing the new typed-gold scoring
requirement. Generic review-quality ratings below are not detection accuracy.

Version: `ace-claim-online-v1`. Date: 2026-09-10. Status: implementation and
offline verification only. No new inference is authorized by preparing files.
This protocol supersedes the *proposed future architecture*, not the identity,
outputs, or protocol of any previous run. The paused expansion stays paused.

## 1. Requirements and Constraints

The objective is to detect and characterize material flaws in a supplied claim
using its full original evidence. It is not theme generation, document repair,
or diagnosis of participants. A flaw needs a located claim target, failed
evidence-to-claim relation, and material consequence. A category label or model
agreement alone does not establish a flaw. Defensible negative and uncertain
decisions remain legitimate.

Functional requirements:

1. Update the corpus-specific Playbook after each completed stream item, when
   grounded learning is available. An opportunity to update is not a requirement
   to invent a new rule on every query.
2. Lock the first prediction before judging or learning from that item. Apply
   accepted rules only to subsequent items. Never overwrite or retrospectively
   rescore the current first-pass response after learning.
3. Track the entire path from proposed lesson to audited delta, stored rule,
   next-query retrieval, and reported rule application.
4. Produce per-corpus Credibility and Conformability with explicit denominators,
   nulls, coverage, technical failures and pending work, plus Playbook artifacts.
5. Compare adaptive memory with static seed memory on exactly the same stream.

Non-functional constraints: one local worker, Gemma 3 4B, no paid API, no model
download, at most eight wall-clock hours after an authorized launch, immutable
call journals, deterministic replay, and graceful pause after the current item.
No duplicate worker may bypass the project-wide lock, including a lock held by
the suspended previous experiment. The clock does not reset on resume.

All constructed-claim outputs remain private under `Storage/`. They are not
manuscript-qualified under `AGENTS.md`. Neither historical Table 3 nor the PDF
is an export target. Previously used diagnostic packets are not untouched tests.

## 2. Architecture and Information Boundaries

```text
Optional development warm-up: 10 packets/corpus x 3 epochs
  integrated detector -> lock -> Reflector/Curator -> audit -> delta commit
  (development scores are not primary stream scores)

For corpus d, current stream item x_t, and its memory P[d,t]:

  x_t + static seeds -> integrated detector -> immutable baseline prediction
  x_t + P[d,t]      -> integrated detector -> immutable online prediction
                          |                      |
                          +-- blind reference ---+
                          +-- blind C/F judging -+--> locked scores / export
                                                 |
  x_t + locked online prediction + rule checks ---+
          |
  combined Reflector/Curator (no reference, judge output, label, or future item)
          |
  per-delta exact-evidence / identity / leakage / duplicate validation
          |
  same-model semantic auditor, separately assessing each eligible delta
          |
  deterministic atomic merge -> P[d,t+1] -> next item in corpus d
```

Prediction order alternates by stream position to reduce a fixed arm-order
effect. Both predictions finish before any reference or quality call. Judge
payloads contain no arm, method, memory, checkpoint, earlier score, or future
sample. The combined Reflector/Curator receives an explicit allowlist of the
current task, unchanged online review, rule checks, mechanical findings, and
current corpus memory. It receives neither the provisional reference nor its
issue IDs, even when those are available. Thus an empty or unavailable reference
does not suppress the learning opportunity.
Rule-trace integrity findings are stored separately from review integrity
findings. The judge receives only review findings, so learned-rule identifiers
cannot reveal the adaptive arm through an error-report side channel. The
updater can inspect both finding types. Trace failures and retrieval-budget
omissions are separately reported in the Playbook export.

Each call is stateless except for the explicit supplied memory. No model weights
are trained. "Online learning" here means persistent inference-time context
adaptation. This is an ACE-inspired adaptation, not an exact reproduction of
ACE's implementation or benchmark. ACE distinguishes offline frozen evaluation
from sequential online prediction followed by context updates. Its structured
memory and incremental deltas motivate this design.
Primary source: [ACE paper](https://arxiv.org/html/2510.04618v1).

## 3. Components and Contracts

`ace_online_contract.py` defines fixed prompts, structured schemas, evidence
validation, retrieval, learning-input isolation, and deterministic delta merging.
`run_ace_flaw_online.py` handles scheduling, local transport, locking, immutable
records, state reconstruction, budget control, pause, and derived exports.
Legacy helpers are reused for exact-span checking and the existing C/F rubric.
Frozen copies of all imported local implementation files accompany each run.

The integrated detector diagnoses and checks its answer in **one** model call.
It returns a review and `rule_checks` keyed by every supplied rule ID, recording
applicability, outcome, exact evidence, rationale, and linked issue indices.
This replaces the previous two-call Detector/Finalizer path in this new version
only. The static and adaptive arms use the identical detector prompt/schema.

The learning call contains distinct structured reflection and curation outputs
but uses **one combined Reflector/Curator call**, as a latency trade-off. The
deterministic merger is not another LLM brain. The semantic auditor is a separate
call, only when an eligible delta exists. All model roles use Gemma 3 4B. A
same-model reference, judge or auditor is not independent validation.

Transport uses only `POST http://127.0.0.1:11434/api/generate`, `stream=false`,
temperature 0, seed 20260910, context 32768 and output ceiling 4096. The lower
output ceiling is a new-version latency/context trade-off, identical in both
arms, not a change to the old run. Incomplete generations remain failures. The source
run's model digest is pinned and rechecked at launch. Request JSON and raw
response JSON are journaled before interpretation. Conservative context bounds
reject oversized calls rather than truncate evidence or memory silently.

## 4. Memory and Actual Rule Application

Memory is `{revision, rules, support}`. Each rule has a stable ID, content version,
immutable-seed flag, applicability, detection check, evidence requirement, and
countercondition. Learned rules also retain their parent rule, novel condition
and last content-change revision. Support provenance is separate from the
reusable text. The two original seed rule objects cannot be modified.

Every proposal links grounded reflection entries and exact evidence spans. The
provisional reference is no longer a mandatory support key. Three operations:

- `add`: a genuinely more specific reusable trigger/check/boundary, with an
  explicit novelty statement and a new content-derived rule ID.
- `refine`: a localized improvement of a non-seed rule, retaining its ID and
  increasing its content version. Seed replacement is forbidden.
- `reinforce`: grounded support for an unchanged existing rule. It adds unique
  case provenance, not rule content or a novel-rule count.

Exact duplicate add/refine proposals are recorded as `duplicate_noop`, not
successful learning. They do not invalidate unrelated sibling edits. A separate
explicit reinforcement proposal is required to record support. Semantically
equivalent seed paraphrases must fail the novelty audit even if their strings
differ. Each eligible edit independently needs all six audit criteria true:
grounding, reusability, preserved counterconditions, no unsupported domain
inference, no duplicate/contradiction, and no leakage. False or null withholds
that edit. Invalid quotes are never repaired or accepted automatically.

Repeated exposure to identical claim/evidence text does not add independent
support. Distinct packet and source-group counts remain separate, particularly
for CaChe. Seed support is stored outside the immutable seed objects. Memory
state hashes distinguish support changes; content hashes distinguish actual
rule-text/version changes. Reinforcement alone is not substantive refinement.

Retrieval always includes both seeds and up to four learned rules. Learned rules
are ranked by deterministic lexical overlap, recent content change, then ID.
Unlike the old positive-overlap-only filter, available learned slots are filled
even with zero overlap, allowing the detector to explicitly mark irrelevant
rules not applicable. All original evidence still enters the detector.
If the complete detector request would exceed its conservative context budget,
remove the lowest-ranked learned retrieval slots until it fits, retaining seeds
and all original evidence. Record `retrieval_budget_omitted` on the locked
prediction. This is explicit budget-aware retrieval, not evidence truncation or
deletion of stored rules. The full stored catalog remains the editor/auditor's
input, subject to its separate memory cap and dispatch bound.

The evidence path is auditable through:

```text
learning patch ID -> per-edit receipt -> state/content hash after item t
 -> state/content hash before item t+1 -> retrieved rule ID/version
 -> detector rule_checks -> linked diagnosis + independent-of-memory judge call
```

Prompt inclusion and self-reported applicability are **not** causal proof of
benefit. A rule can be retrieved but irrelevant, applied incorrectly, or harmful.
Show these separately from accepted rules and quality improvements. No automatic
rewrite, deletion, capacity eviction, or score-driven rerun is permitted. At the
40-rule cap, new additions are withheld visibly; refinements can still occur.
The full visible rule catalog also has a 6,000-byte serialized prompt budget.
An edit that exceeds it is withheld, not silently truncated. This bounds memory
growth before it makes the editor/auditor context unusable; each actual call
still undergoes full input/schema/output-reserve admission. Large responses can
still make a later call ineligible, and are reported rather than shortened.

## 5. Sampling, Repetition and Comparison

The prepared diagnostic reuses the paused expansion's frozen *inputs only*:
`ace_flaw_gemma_expansion_dev10_eval80_20260910/inputs.private.json`. No old
predictions, references, quality scores, learned memory or call responses enter
the new run. Source input and manifest hashes are recorded. Preparation verifies
four-corpus balance and excludes development/stream packet-ID, normalized-text
and source-record overlap. Source-group overlap is allowed only for the
previously authorized CaChe within-source diagnostic.

| Dataset | Unique development | Development exposures | Unique online stream | First-pass predictions | C/F judgment pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dreaddit | 10 | 30 | 80 | 160 | 160 |
| GoEmotions | 10 | 30 | 80 | 160 | 160 |
| CaChe | 10 | 30 | 80 | 160 | 160 |
| ParlaMint-GB | 10 | 30 | 80 | 160 | 160 |
| Total | 40 | 120 | 320 | 640 | 640 |

Development defaults to three epochs. The main stream is traversed **once**.
Each stream packet has one static and one online first prediction and one
combined C/F judgment for each prediction. There is no post-update same-item
prediction. Corpus order is Dreaddit, GoEmotions, CaChe, ParlaMint-GB, round-robin
by position. Within-corpus ordering is frozen by a score-independent hash.
Corpus memories never mix. Repeated source groups and claim templates still
limit effective independence; 80 packets are not 80 independent constructions.

The static arm starts from seeds, not a copied adaptive checkpoint. Consequently
the main contrast measures the whole adaptation package, including warm-up and
online updates. It does **not** isolate online updates from warm-up. Historical
All roles and the paused E0/E3 run also differ in procedure; comparisons with
those are descriptive, not controlled causal contrasts.

## 6. Metrics and Analysis Rules

The existing review-quality rubric is retained: Credibility asks whether material
diagnoses and the disposition are defensible; Conformability asks whether
reasoning remains faithful and traceable to original context. Each dimension
is true, false or unresolved/null. A demonstrated failure takes priority over
unknown; unresolved required grounding prevents true. An empty issue list does
not pass vacuously. Mechanical validity is not semantic correctness.

For each corpus, arm and dimension report:

- success among binary cases: `100 * true / (true + false)`;
- binary coverage: `100 * (true + false) / planned`;
- observed true fraction of the planned panel: `100 * true / planned`, explicitly
  not a success rate that treats unresolved cases as established failures;
- true, false, null, technical/not-reached, pending and planned counts.

No binary cases means N/A, not 0% or 100%. Missing references may leave judging
unresolved; they never force a score or halt source-grounded learning. Paired
changes use only the same packet with binary values in both arms and show that
paired denominator. Unpaired aggregate percentages must not be subtracted and
called a paired gain. Do not infer verified flaw recall from this incomplete,
same-model reference inventory.

Inspect progress and quality after every completed item. Read cumulative and
20-position block curves, paired deltas, coverage, decision distributions, learned
rule counts, content changes, no-ops, rejected deltas, retrieval and application
traces. Changing corpus difficulty, within-source dependence, same-model judge
bias and prior exposure can mimic learning. Do not claim monotonic improvement,
component benefit, statistical significance or repair success from these traces.
Preserve a separate checkpoint after every 50 completed online items across the
four corpora. Raw predictions retain decision distributions and exact rule-use
traces; aggregate tables are not a replacement for inspecting those records.

## 7. Ablation Plan and Trade-offs

The requested "Effective by Design" claim is a hypothesis, not a result.
After the primary diagnostic, separately authorize and freeze controlled arms
on a common outcome-independent stream/order/model/judge contract:

1. Warm-up then frozen memory versus warm-up plus online updates, isolating online
   adaptation rather than conflating it with warm-up.
2. Structured Reflector/Curator versus direct delta generation without a reflection
   artifact, with the same evidence/audit requirements and declared call budget.
3. One versus three development epochs, keeping unique development items fixed.
4. Incremental delta merging versus a separately specified full-memory update
   policy with identical safety constraints, storage cap and evidence access.

The main runner supports separately frozen 0/1/3-epoch configurations; it does
not yet implement the other ablation arms. They are not silently substituted
into the eight-hour run. Repeated development exposures are not extra independent
samples. Multiple independent orders and external adjudication are future work
before stronger generalization or component-effect claims.

The combined editor and one-call detector save latency but reduce separation of
reasoning roles. Per-edit auditing costs calls but prevents one invalid sibling
from blocking useful learning. Lexical retrieval is reproducible but not semantic
retrieval; revisit it only as a versioned intervention. A single local worker is
appropriate for the current machine and avoids model-memory contention. Larger
runs should use explicit independent run leases and a transactional job store,
not uncoordinated workers sharing this mutable memory.

## 8. Reliability, Budget and Operations

Maximum scheduled calls: 120 development items x 3 = 360; 320 online items x 7
= 2,240; total **2,600**. An online item uses two integrated predictions, one
shared blind reference, two combined judges, one editor, and at most one audit.
No delta means no audit call. There are no automatic retries, optional probes,
repeated online epochs or paid API calls in this budget.

The absolute deadline is eight hours; new inference admission closes 15 minutes
earlier and each call needs its full 180-second timeout allowance. At the call
ceiling, the 7h45m inference allowance corresponds to about **10.7 seconds per
call**, including overhead. This is a feasibility threshold, not a measured ETA.
Actual role-specific duration medians determine provisional remaining-work
estimates. If the deadline is reached, export partial results with pending counts
and preserve unfinished journals. Do not shrink a panel after viewing scores.

The authoritative state is the immutable per-item result and its parent hash,
not a mutable current-memory file. Each result binds the prior memory, next
memory, task identity and hashes of its locked predictions/judgments/delta.
Atomic writes prevent half-written commits. On restart, reconstruct all corpus
states by replaying completed items and verify their chains and artifacts.
Completed raw calls are reused only for the identical request. A dispatched
request without a durable response is ambiguous and stops the run for diagnosis;
it is never guessed successful or redrawn automatically.

Schema/context failures are visible technical failures. They are not adverse
semantic judgments and are not selectively retried. A quality failure does not
rewrite a locked prediction or supply a learning label. Hash/identity failures
stop processing. Pause requests are checked at item boundaries, after prediction,
judging, learning, commit and export. Native pause releases worker locks. Resume
requires explicit authorization and preserves the absolute deadline. This does
not change the old expansion's OS-level suspended processes or held locks.

Run artifacts include `predictions/`, `judgments/`, `calls/`, `deltas/`,
`results/`, `playbooks/<corpus>/current.json` and `.md`, `status.json`,
`results_table_online.csv` and `.md`, `paired_comparison.csv`, and
`playbook_result.csv`, `learning_curve.csv`, and `checkpoints/items-0050.json`
(then 0100, 0150, etc.). Export completion is not scientific validation.

## 9. Acceptance and Launch Boundary

Offline tests must cover evidence-grounded additions, immutable seeds, independent
per-edit rejection, explicit reinforcement, repeated-exposure deduplication,
next-query retrieval, trace identity, future/score isolation, prediction-before-
learning order, replay without draws, atomic commit recovery, pause boundaries,
ambiguous transport, tampering, incomplete quality denominators and final export.

Before an authorized live main run: review real development-only pilot outputs
for semantic grounding, unsupported rule growth, meaningful novel conditions,
retrieval/application and avoidable schema errors. Freeze any resulting changes
as a new version; do not retry individual unfavorable pilot outputs until they
look good. A seed-only outcome is reportable, not a reason to weaken admission.
Offline tests demonstrate implemented behavior on controlled fixtures, not real
model quality, successful learning or performance gains. This live semantic
pilot remains pending. The previous experiment must be released safely by an
explicit user decision before the shared execution lock can be acquired.
