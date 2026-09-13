# Gemma-Only Four-Hour Claim-Sentence Pilot

Historical pilot-v1 implementation contract. The
[v5 design](../../Storage/experiment_guidelines/warrantroute_flaw_detection_final_protocol_v5.md)
now specifies a three-corpus default while ParlaMint-GB's within-source permission
is absent, plus tri-state quality judgments. The code described below has NOT
been migrated to those choices. Its four-corpus/620-call plan is not v5, and it
must not be launched under the v5 label.

Date: 2026-09-09. Scope: private WarrantRoute-Lite feasibility diagnostic.
The user selected Gemma only to inspect more packets within a four-hour budget.
This is NOT the original WarrantRoute, the full n100 experiment, a baseline
comparison, weight training or a manuscript-qualified experiment.

## Data and target

Use 20 existing development-pool packets per corpus: five adaptation packets
and 15 disjoint pilot evaluation packets. Retain all four corpora: Dreaddit,
GoEmotions, CaChe and ParlaMint-GB. All 80 unique packet IDs come from the
stopped TA run's development candidate inventory. Do not touch its 100-item
evaluation panels. Restore original claim sentences and source evidence from
the original packet files, not the source-only TA payload.

The declared target is ONLY `llm_generated_qualitative_claim.claim`, evaluated
as the literal assertion with its cited excerpt IDs and complete source bundle.
Preserve that sentence and all source text exactly. The builder's theme_name,
explanation, boundary_conditions and model_id are not part of this narrowed
target and are excluded. Some contain direct flaw hints. This is an explicit
change of target: do not interpret a sentence-only score as verification of the
complete qualified analysis. Original packet and projected-task hashes are saved.
No reviewer receives intended labels, construction notes or historical scores.

Record/text overlap across pilot development/evaluation is prohibited. Recorded
source-ID overlap is prohibited except for CaChe's previously authorized
within-source diagnostic. Deterministically choose the first eligible five-item
development combination from a fixed hash order; use the remaining 15 for
evaluation. The first five evaluation IDs form the fixed probe. Do not select
by model scores. The selector records actual overlap counts and unique claim
sentence counts. Claims repeat a small number of construction templates, so
80 packets do not imply 80 diverse natural claims or independent source groups.

Fifteen evaluation packets per corpus are suitable for checking mechanics and
describing preliminary outputs, not precise performance estimates or model
rankings. This pilot uses one model and has no baseline comparison. Results must
remain under Storage and must never fill the original Table 3 or manuscript.

## Calls and adaptation

All inference uses the installed local `gemma3:4b`, including reference and judge
roles. No Qwen/Llama calls, remote API, paid credits, downloads or model changes.
The installed model digest and all prompt/schema/config/input hashes are frozen.

For each diagnosis use two calls: Detector, then Evidence-Grounded Finalizer.
The finalizer integrates and checks the diagnosis in one response, preserves
issue IDs and accounts for every initial candidate. It does not rewrite the
claim or introduce unrelated issues. This removes the full system's independent
scout and specialist calls and is therefore a distinct Lite ablation.

For development, lock that prediction first, then make ONE Learning Editor call.
The editor compares it to this packet's provisional reference and proposes at
most two add/replace patches. Exact quotations, schema, rule IDs, immutable seed,
capacity and direct source leakage checks run in code. Those checks do not prove
semantic correctness or remove same-model confirmation bias. No hidden guard or
repair call is permitted. Rejected patches leave memory unchanged. Seed rules
cannot be edited. Keep distinct supporting packet IDs rather than counting each
epoch as independent evidence. Forty active rules and six retrieved rules are
the limits. Audit-only provenance is not sent to review agents.

Run three epochs over the same five development packets per corpus. Carry memory
forward and use deterministic epoch-specific orders. Each packet's raw previous
review/feedback is excluded from the next review request; only abstract memory
persists. This is context adaptation, not weight training. The 60 development
episodes do not create 60 distinct training packets.

## Reference and quality policy

For this fast pilot only, create ONE blinded Gemma reference proposal per unique
packet before its first diagnosis. Do not expose Playbooks, candidate outputs or
intended labels to reference generation. Keep this reference unchanged across
epochs. This replaces the larger design's two-model reference preparation and
is explicitly a weaker, incomplete SAME-MODEL diagnostic reference, not truth.

After each evaluation diagnosis, make one separate Gemma judging call, blind to
method/checkpoint labels and Playbook contents. Report binary review Credibility
and Conformability, reference-relative grounded matches, and unsupported or
unresolved allegations. Matching requires target, mechanism, material consequence
and relevant evidence, not just a category. Unique ID constraints are checked in
code, while semantic matching remains a fallible model assessment. Do not call
this independent validation, complete precision/recall/F1 or repair success.

References with invalid quotations/schema are unavailable, not fabricated or
regenerated until a favorable answer appears. Missing reference means no learning
update from it; review quality may still be judged directly against evidence.
Return failures and reference coverage separately. No output is assumed correct
because it parses. Zero retained allegations is not automatically a failure,
and technical failures must not be confused with semantic no-flaw decisions.

## Workload and checkpoints

E0, E1 and E2 each evaluate the SAME five-item probe per corpus. E3 evaluates
all 15, including those same five. Export a separate fixed-probe curve for all
four checkpoints; never compare the E3 n=15 rate directly with earlier n=5 rates
as evidence of improvement. Baseline methods are omitted for this feasibility run.

- 80 unique packets: 20 development and 60 evaluation across corpora.
- 60 development episodes: 20 unique packets x three epochs.
- 120 evaluation trajectories and 120 external binary judgment pairs.
- 80 provisional reference calls, generated on first use, independently of output.
- At most 620 LLM calls if every scheduled stage runs once and completes.

Alternate corpora after each packet within a phase. Preserve each corpus's memory
order; do not process all of one corpus before the others. Evaluation judging is
interleaved for observability, but outputs, scores and references never enter
learning. No prompt, threshold, role or epoch tuning after held-out results.

## Four-hour limit and resumption

The four-hour wall-clock budget starts when the supervisor starts inference,
not while code or eligibility checks are being prepared. Persist one deadline
and never reset it on resume. Cap request timeout by both 180 seconds and the
remaining budget. At the deadline the supervisor terminates only its own worker
process group, closing active client connections. Do not terminate the global
Ollama service or other tasks. Any interrupted backend request remains explicitly
unresolved until confirmed canceled; do not claim that an interrupted trajectory
finished. No new request may start beyond the deadline. Fewer than all planned
packets may finish; retain balanced progress and report exact denominators.

Use exclusive supervisor and worker locks to prevent duplicate workers. Save
immutable request/response journals, locked predictions, results and snapshots.
Existing successful outputs are reused only when identities match, never
overwritten. A request with no response is ambiguous and stops execution without
automatic retry. Schema/quotation errors are recorded without rerunning semantic
outputs. Three consecutive invalid review trajectories stop the pilot for
investigation. No silent repeated repair or restart loop is allowed.

One model performing all roles may fit the budget, but completion within four
hours is NOT guaranteed. The budget is a stop rule, not an accuracy claim or a
promise that all stages will finish. The main experiment remains stopped.

## Outputs

Write to a new private pilot directory only. `status.json` gives scheduled and
completed development/evaluation counts, binary judgment pairs, failures and
remaining budget. `progress.csv` contains scheduled-panel and fixed-probe rows
with explicit sample counts, same-model quality percentages and reference counts.
`references/`, `predictions/`, `results/`, `calls/` and `snapshots/` retain provenance.
`manifest.json` records data qualifications and model/config/code hashes.

Do not export to the manuscript or historical final Table 3. Report the pilot as
completed, stopped at budget or stopped on error; do not translate a supervisor
exit into scientific validation. Quality, grounding and learning gains may be poor.
