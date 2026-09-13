# Detection-First ACE-Inspired Online Experiment

Date: 2026-09-10. Current source runtime: `ace-claim-online-v2-detection-txt-v1`.
Scoring profile: `claim-flaw-detection-scoring-v2`.

## Objective and Status

Correctly detect AND characterize material flaws in a supplied claim against its
evidence. Do not substitute thematic-analysis generation, document repair or
plausible review writing. Performance statistics must concern correctly typed,
grounded flaw detection. Calls, rules, latency and failure counts are operational
diagnostics, not accuracy.

This prospective revision supersedes online v1. No previous frozen experiment,
score, prompt, prediction, clock or Table 3 is overwritten or resumed. No live
inference is authorized by this document. The old expansion remains paused.

Current selected packets have generator-intended labels, not complete adjudicated
gold inventories. Inference is blocked until a complete bank is supplied and
frozen. Software validates structure and bindings, not whether declared human
adjudication actually occurred. Researchers must check annotation provenance.
Never manufacture adjudication records or promote a model reference to gold.
Constructed-packet results remain private diagnostics under `Storage/`.
Adjudication does not itself make them manuscript-eligible under AGENTS.md.

## Dreaddit Data Unit

For this experiment, the user specifies **one Dreaddit source datapoint as one
paragraph**. Distinguish that source unit from a constructed review packet,
a claim being evaluated, and a repeated model exposure. Do not describe these
different units interchangeably as samples.

The currently selected Dreaddit inputs contain four source records per packet,
whose texts the packet builder carries as evidence, plus one separate constructed
claim. The detector currently evaluates that claim against the evidence; it does
not label each source paragraph itself as flawed. The source stress label is
not a gold flaw-type annotation.

The existing prepared selection contains 10 development packets using 40 unique
source records and 80 evaluation packets using 320 unique source records. Under
the paragraph unit above, these correspond to 40 and 320 source paragraphs,
respectively, not 10 and 80 paragraphs. Epochs and static/adaptive predictions
reuse these units and do not increase the number of unique source paragraphs.

Report paragraph/record counts, packet counts and model-exposure counts
separately. A requirement that one paragraph equal one query would change the
current packet construction and review target. It requires a new input and gold
design, not relabeling existing four-record packet results or silently changing
the frozen inputs. This clarification changes documentation only.

## Mandatory Adaptation Rules

The main ACE-inspired condition MUST satisfy all three requirements below.
They concern Playbook adaptation, not model-weight training. Static controls
and separately prespecified ablations must be identified explicitly and must
not be presented as the full adaptive condition.

### 1. Multi-Epoch Adaptation

The main condition MUST process each dataset's development panel for **three
epochs**. The Playbook at the end of one epoch MUST be carried into the next
epoch without resetting to seed rules. After the last development epoch, that
same accumulated Playbook initializes the dataset's online evaluation stream.
Each dataset retains separate memory. Freeze the packet order for every epoch
before execution and record the epoch and packet identity for each exposure.

Repeated exposure to a development packet is not a new independent sample or
independent support for an existing rule. Evaluation remains a single pass per
arm: never repeat scored evaluation packets as development epochs. One-epoch or
no-adaptation conditions require a separate, explicitly declared ablation.

### 2. An Update Cycle After Every Query

Every adaptive query MUST have a recorded Playbook update outcome, during both
development and online evaluation. Here, a query is one scheduled packet
exposure, not each individual internal LLM call. In paired evaluation, lock both
static and adaptive predictions before grading, then update only the adaptive
Playbook from the locked adaptive prediction and the allowed source evidence.

For every valid adaptive prediction, run the Reflector/Curator update step.
Audit eligible deltas, commit accepted changes, and publish the corresponding
TXT state before the next query uses that dataset's memory. Do not postpone
adaptation until the end of a batch, an epoch, or a 50-item reporting interval.
The next prediction uses P[t+1], never a stale copy of P[t].

An update cycle does not require inventing a new rule. Record `no_change`,
withheld changes, or a technical failure when appropriate, with its reason.
If no defensible change is admitted, P[t+1] equals P[t]. A failed prediction
must record why learning was not reached rather than fabricate a lesson.
Gold labels, judge outputs, scores and future packets remain unavailable to
the updater. The static comparison Playbook remains frozen throughout.

### 3. Persistent IDs for Every Playbook Item

Every admitted Playbook item MUST have an ID before it is published or used.
Use the TXT form `[shr-00001]`, `[shr-00002]`, and so on. IDs are unique within
one run and dataset's Playbook. Use `(run, dataset, text_id)` when referring to
items across datasets. Preserve the mapping to the internal canonical rule ID.

An accepted new item receives the next unused ID. Refinement or reinforcement
of an existing item MUST preserve its ID. Never renumber items because their
wording, retrieval rank, or internal list position changes, and never recycle
an assigned ID. Rejected or duplicate proposals do not become new numbered
items. Each admitted item still needs its applicability, detection check,
evidence requirement and countercondition.

Record each change's operation, affected item ID, packet/epoch provenance,
audit outcome, and before/after memory state. A proposal ID such as `patch_1`
is query-local, not the persistent Playbook item ID; identify such proposals
together with their complete job ID. Keep TXT revision history and the hash
manifest so each next-query memory exposure can be traced to admitted items.

## Fixed Taxonomy

Retain the existing repository mapping, not inferred model synonyms.

| Builder label | Detection category | Failed relation |
| --- | --- | --- |
| unsupported_evidence | unsupported_inference | Material proposition unsupported by evidence |
| source_concentration | hidden_source_concentration | Claimed coverage exceeds supporting sources |
| counterevidence_loss | lost_negative_case | Consequential supplied countercase lost |
| contextual_flattening | contextual_flattening | Consequential context distinction collapsed |
| unsupported_abstraction | unsupported_abstraction | Unwarranted conceptual or scope jump |

`other_material_flaw` is a residual category, never a wildcard for the five named
types. Adjudication must resolve overlapping types and avoid counting the same
mechanism under multiple labels. Listing all types is not a successful strategy:
unmatched allegations and duplicates count as FP and prevent exact correctness.

## Correctness Contract

A TP requires all of: equal canonical type, same claim target or omission, same
failed warrant/mechanism, evidence establishing that flaw, and a correct material
consequence. Claim and evidence quotes must pass exact-substring and excerpt-ID
checks. A whole-packet missing-support argument needs explicit semantic approval.
Quote existence alone is not semantic support.

A fallible matching assessor judges every same-category candidate pair using
`same_target`, `same_mechanism`, `evidence_supports_flaw`, and
`material_consequence_correct`. It provides reasons and valid evidence, not
TP/FP/FN totals. Code performs maximum-cardinality one-to-one bipartite matching.
Ties can select different valid pairs, but counts and per-type metrics are
invariant. Predictions and the complete gold inventory stay locked.

| Case | Outcome |
| --- | --- |
| Correct type, target, mechanism, evidence and consequence | One TP |
| Wrong type | FP for predicted type and FN for gold type |
| Right type but wrong target or unsupported mechanism | FP and FN |
| Empty final issues on verified positive | FN for each missed gold flaw |
| Repeated reports of one flaw | At most one TP; unmatched duplicates are FP |
| Correct detection plus an extra allegation | TP plus FP; not exact-packet correct |
| Verified clean packet and justified empty review | Exact-packet correct and true negative |
| Abstention or technical failure on positive | Gold flaws remain FN |
| Abstention or technical failure on negative | Not correct and not true negative |
| Missing gold or unresolved pair judgment | Unscored, never automatically correct |

A grounded false criterion defeats a match even if another is unknown. Unknown
criteria without a demonstrated mismatch, or invalid assessment evidence, leave
the pair unresolved. Do not redraw judgments for a preferred result. Rationale
prose cannot retroactively populate an empty final `issues` array.

## Gold Bank

`gold.private.json` contains `protocol` and `items`. Each item has `dataset`,
`packet_id`, `task_sha256`, `annotation_status: adjudicated`,
`inventory_complete: true`, `verified_negative`, `adjudicator`,
`adjudication_record`, and `review`. The review uses the full issue schema:
category, target kind, claim quote, evidence anchors, whole-packet warrant,
mechanism, material consequence and counterconditions. Unresolved inventories
are ineligible. Every selected evaluation packet must appear exactly once.

Annotate without evaluated predictions or scores. Resolve category overlaps and
disagreements before freezing. Retain supporting adjudication records privately.
Verified negatives must be affirmatively annotated, never inferred from missing
labels. No verified negative controls means specificity is unavailable. A new
gold dispute requires versioned adjudication, not silently editing an answer key
or selectively forgiving a method. Structural validation cannot replace this
research process or prove assessor independence.

## Metrics

```text
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 TP / (2 TP + FP + FN)
Exact packet accuracy = completely correct packets / planned packets
```

Report counts and precision/recall/F1 for each type and dataset. Micro metrics
pool counts. `macro_f1_over_gold_supported_types` averages only gold-supported
categories. A zero denominator is unavailable, not 100 percent. Exact-packet
correctness requires all gold flaws matched, no extra allegations or unresolved
concerns, a consistent disposition, and completed non-abstaining output.

Keep all planned packets represented. During incomplete scoring, show confirmed
TP, FP/FN in scored packets, scored/planned and unresolved/pending counts.
Withhold headline rates until the planned panel is fully scored. The separately
named confirmed-correct fraction of the plan is a lower bound, not an assumption
that pending packets failed. Never present resolved-only success as overall
accuracy. No confidence intervals or significance claims are generated here.
Source clustering and repeated exposures need a separately prespecified
uncertainty-analysis plan before such claims are added.

Historical raw Credibility and Conformability remain unchanged and are not
detection accuracy. Two new, explicitly named bespoke composites are:

```text
Detection-gated Credibility = exact detection AND raw Credibility
Detection-gated Conformability = exact detection AND raw Conformability
```

Wrong or missed flaws make both false even when a raw judge liked the review.
Correct detection with unknown required quality remains unresolved. When exact
detection is deterministically false, a quality-only call is unnecessary: the
composite fails and raw quality remains unassessed. Positive raw scores cannot
rescue unresolved detection. These composites are not established replacements
for the original quality dimensions. Typed detection remains the primary result.

## System and Information Flow

```text
Private adjudicated bank ------------------------------> scorer only
Claim + complete evidence + Playbook P[t]
  -> static-seed prediction and online prediction
  -> immutable prediction locks, before grading
  -> deterministic type and quotation checks
  -> at most one combined matching/quality assessment per arm
  -> one-to-one matching and detection-first statistics

Locked online prediction + evidence + rule traces + mechanical checks
  -> combined Reflector/Curator proposes incremental deltas
  -> one per-edit audit if eligible deltas exist
  -> accepted rules become P[t+1], retrieved for the next query
```

Gold, intended labels, judges, scores, static predictions and future packets
never enter the online detector or updater payload. This is source-grounded
self-reflection, not answer-key-supervised adaptation. More rules or epochs do
not guarantee better detection. Test improvements with matched static/online
predictions and typed learning curves, not rule count alone.

Rules retain applicability, detection_check, evidence_requirement and
countercondition, plus add/refine/reinforce operations, immutable seeds,
provenance, deduplication and context limits. Static/online prompts are identical
except for supplied memory. Baseline results using different scoring protocols
are not merged into this comparison.

## TXT Playbook Projection

Each corpus has `playbooks/<dataset>/current.txt` in a newly prepared run.
It starts with `## STRATEGIES AND HARD RULES` and uses one entry per line, such
as `[shr-00001] ...`, with a final newline. Each entry preserves all four fields:
applicability, detection check, evidence requirement and countercondition.
The user's API/code rules illustrated the format; they are not experiment rules.
The heading does not convert fallible learned heuristics into proven facts.

`text_ids` persistently maps internal rule IDs to numbered TXT IDs. Seeds start
at `shr-00001` and `shr-00002`. An admitted new rule gets the next number.
Refinement preserves its number, even if internal ordering changes. Reinforcement
can change support metadata without changing TXT wording. Withheld, duplicate
or no-change proposals do not force new text or consume a number.

The runner publishes TXT after a complete per-query result is committed and
before proceeding to the next query. Atomic replacement prevents partially
written text. `history/revision-00000.txt` and matching JSON preserve every
published state revision. `current.manifest.json` binds the TXT hash, state hash,
ID mapping and last committed result. Recovery replays durable results without
redrawing model output. Different content at an immutable revision is an error.

The admitted JSON state remains authoritative. Do not hand-edit `current.txt`
to inject unreviewed rules: it is a generated projection, not an import path.
The detector receives its retrieved subset in this SAME TXT format, plus a small
canonical-ID index for output-schema binding. Its locked prediction records
`retrieved_playbook_text` so the exact memory exposure can be inspected. The
Reflector/Curator and auditor receive the current memory in the same format.
Full TXT includes all admitted rules; an individual detector still retrieves
seeds plus at most four learned rules under the existing context budget.

Scoring and answer-key isolation are unchanged. This source revision changes
prompt serialization and versioned memory state, so it requires a fresh run
preparation. Existing frozen v1 and v2 preparations remain unchanged. The
format-preview files under `Storage/experiment_reports/playbook_txt_format_preview/`
contain only initial seed rules, not newly learned experimental findings.

## Workload and Reliability

Retain Dreaddit, GoEmotions, CaChe and ParlaMint-GB. Ten development packets per
dataset are exposed across three epochs. Eighty evaluation packets per dataset
are predicted once per static/online arm. This is 120 development exposures and
640 evaluation reviews, not 760 independent source samples. CaChe remains the
user-authorized within-source diagnostic with repeated dev/evaluation text and
records excluded. Reused panels are previously exposed diagnostic material.

At most three calls per development exposure and six per paired stream item:
two predictions, two combined assessments, one learning call and one audit.
Ceiling: 2,280 calls, versus online v1's 2,600. This is not a measured ETA or a
guarantee of completion. The eight-hour deadline and fifteen-minute reserve
remain. No paid API use is authorized.

Preflight requires v2, a complete gold bank, frozen hashes, pinned NetworkX and
model versions, isolated inputs and the shared lock. Missing gold blocks before
model contact. Context admission rejects oversized requests without truncating
evidence. Never duplicate workers, reset old clocks, change frozen artifacts or
redraw unfavorable outputs. Ambiguous dispatched calls stop for diagnosis.
Completed artifacts replay without new calls. Failures and unknowns stay visible.

## Exports and Launch Gate

- `results_table_online.csv/.md`: detection-first dataset/arm results.
- `detection_by_type.csv`: five named categories plus residual type.
- `paired_comparison.csv`: exact-detection improvements and regressions.
- `learning_curve.csv`: same metrics in 20-item blocks and cumulative windows.
- `playbook_result.csv`: operational memory changes and use, not correctness.

Checkpoint exports occur every 50 paired stream items. Finalization checks both
detection and composite-quality coverage. Unknowns prevent a fully scored
completion claim. Raw quality survives in immutable assessment artifacts.

The separate historical audit in
`Storage/experiment_reports/flaw_type_audit_20260910/` recovers intended types
through source-file, packet and prediction hashes. It is weak-label agreement,
not adjudicated precision/recall, and does not change historical Table 3.

Prepare only at a fresh Storage path. Without `--gold-bank`, preparation is
offline and marked `missing_blocks_inference`. Supplying a complete genuine bank
is required for a runnable snapshot. Never modify a prepared manifest to bypass
this gate. Explicit launch authorization and semantic preflight remain required.
Frozen v1 copies keep their old behavior and must not be launched as v2.
