# Charlie quickstart: synthetic researcher-in-the-loop pilot

> **STOP — fictional/synthetic data is not authorized for the current study.**
> This file is retained only as an inactive audit artifact. The active targets
> are real Dreaddit and real `agyw_focus_groups`; start at
> [`REAL_DATA_START_HERE.md`](REAL_DATA_START_HERE.md) and do not run the
> commands below.

> **Inactive audit lane. Do not start this four-item collector in the selected
> Direction J phase.** The exact companion-compatible handoff is now
> [`CHARLIE_START_HERE.md`](CHARLIE_START_HERE.md). These instructions remain
> only so the earlier full-output workflow rehearsal is reproducible in a future
> separately activated phase. The same Charlie may not run both queues in one
> phase because their source contexts overlap.

This is a qualification session for one **developer-researcher case**, not a
human-gold study. Charlie helped develop WarrantRoute, so his judgments must be
reported as construction-involved pilot data and must not be generalized to
other researchers or treated as universal ground truth.

## Do this first

1. Close any WarrantRoute file that exposes model identity, designed defects,
   planted-condition labels, prior ratings, judge scores, or aggregate results.
   Confirm with the coordinator whether your review environment is actually
   access-separated from `coordinator_only/` and the shared private maps. Record
   your answer in the post-lock debrief. For this v1 shared-workspace pilot the
   official classification remains a procedurally masked developer case either
   way; your self-report does not establish a technical blind.
2. From the Direction H directory, run the reviewer-safe preflight. Do not begin
   if it reports any error:

   ```bash
   python3 scripts/validate_artifacts.py --reviewer-safe
   ```

   If the script is missing, a Python dependency is unavailable, or validation
   does not pass, stop and tell the coordinator. Do not install an unapproved
   dependency, bypass validation, or open an item as a workaround.

3. Read the short shared contracts, in this order:
   - `../qualitative_coding_baselines/protocol/analytic_contract.md`;
   - `../qualitative_coding_baselines/protocol/paper_metric_data_contract.md`;
   - `protocol/companion_alignment.md`.
4. Start the collector; it selects the next locked task and handles timing and
   validation:

   ```bash
   python3 scripts/collect_review.py
   ```

   The first task in the frozen, seed-derived presentation order must be
   `DHQ-004`. To request it explicitly, use:

   ```bash
   python3 scripts/collect_review.py --task-id DHQ-004
   ```

   The collector, not Charlie, should open `pilot/items/DHQ-004.json`. If it
   cannot do so, stop and tell the coordinator; do not substitute a shared
   blinded bundle or another item manually.
5. Save one paper-metric rating and one linked feedback record for the displayed
   item. Lock both before advancing. Do not fill any value before actually
   reviewing the item.

The frozen reviewer-safe queue has exactly one output from each of four
fictional evidence packets:

| Order | Task | Packet | Corpus label | Blind output |
|---:|---|---|---|---|
| 1 | `DHQ-004` | `syn_agyw_01` | `synthetic_agyw_proxy` | `DHO-F5N1` |
| 2 | `DHQ-002` | `syn_kodis_01` | `synthetic_kodis_proxy` | `DHO-P2M9` |
| 3 | `DHQ-003` | `syn_dreaddit_01` | `synthetic_dreaddit_proxy` | `DHO-V8C3` |
| 4 | `DHQ-001` | `syn_candor_01` | `synthetic_candor_proxy` | `DHO-K7R4` |

Use `rater_id = charlie_dev_researcher_01`, `evaluator_group = researcher`,
and `evaluation_role = development` throughout. The collector should read the
packet, corpus, and blind-output identifiers from `pilot/manifest.json`; do not
retype or reinterpret them.

The rating record must conform exactly to
`../qualitative_coding_baselines/schemas/paper_metric_rating.schema.json`.
The feedback record must conform to `schemas/feedback_record.schema.json`.
Use only the Charlie response paths reported by the collector.

Do not create placeholder observations. Empty templates are acceptable;
partially invented ratings, rationales, times, or repair outcomes are not.

## What to record for each task

Read the research question, every source excerpt, and the complete blinded
output. Do not search for the excerpts or use outside facts. Then
record:

1. `evidential_credibility` (1--5): is every material part of the
   interpretation directly warranted by sufficient cited evidence in context?
2. `voice_boundary_preservation` (1--5): do differences, dissent,
   counterevidence, minority/boundary cases, and qualifications survive the
   synthesis?
3. `scope_calibration` (1--5): are breadth, strength, polarity, causal language,
   and source/corpus scope proportionate to the supplied evidence?
4. `cannot_judge`: list only the metric or metrics that cannot be judged. The
   corresponding score must be `null`; other metrics remain independently
   rateable. Confidence is still required.
5. `serious_error_flags`: mark every applicable flag from the shared schema.
6. `disposition`: `accept`, `revise`, `reject`, or `escalate`.
7. `requested_expertise` on every record: `qualitative_methods`, `domain`,
   `both`, or `none`. Use `none` when no additional expertise is needed.
8. `confidence` (1--5), a concise evidence-based `rationale`, UTC rating
   completion time, and `review_seconds` from complete-item display through
   that rationale. Feedback-sidecar authoring is timed separately and is not
   included in the canonical rating time.

Scores of 4 or 5 count as adequate only during later analysis. Do not aim for a
quota of passes, failures, or error flags.

Use the manuscript's construct-specific anchors. For evidential credibility,
1 means evidence is absent, unverifiable, misattributed, or contradictory; 3
means the core is partly supported but a material link or qualifier is missing;
and 5 means every material part is directly warranted in context. For
voice-and-boundary preservation, 1 means a consequential voice, counterexample,
or distinction is erased or reversed; 3 means the main pattern survives but a
meaningful viewpoint or boundary is underplayed; and 5 retains all consequential
variation and qualification. For scope calibration, 1 means breadth, polarity,
or causal strength conflicts with the evidence; 3 needs a material scope or
strength change; and 5 matches participant, group, and corpus scope without an
unsupported causal or prevalence claim. Scores 2 and 4 are the corresponding
intermediate judgments.

## Write feedback for the frozen revision model

The feedback record is not a second rating and is not an invitation to rewrite
the output. State only what a revision model would need to change, preserve, or
check. When alleging a defect:

- name the affected claim, code, theme, quotation, or source link;
- point to the supplied evidence or missing boundary/countercase;
- state the requested correction without revealing or guessing the planted
  condition; and
- preserve accurate material explicitly when a narrow repair is sufficient.

The collector maps the disposition to `feedback_status`: `accept` to
`no_change`, `revise` to `actionable_revision`, `reject` to
`reject_or_regenerate`, and `escalate` to `human_escalation`. For actionable
revision or regeneration, enter at least one structured finding. Each finding
needs the canonical error-family label, a `minor`, `material`, or `serious`
severity, one or more output locations expressed as JSON Pointers, the relevant
evidence excerpt IDs (or an empty list when none applies), a plain description
of the issue, and the requested change. Also
complete the identity-free `feedback_summary`, `preserve`, and `uncertainties`
fields. The collector generates the rating-record hash and linked `rating_key`;
do not edit that linkage by hand.

Do not mention candidate model identity, prior judge scores, a hidden failure
family, or coordinator truth. Use the same formatter-ready structure described
in `protocol/companion_alignment.md` so Charlie feedback can be compared with
the companion rater condition.

If the output is acceptable and no repair is warranted, record that outcome in
the schema-defined way: use `no_change` with no findings and a concise summary.
Do not manufacture a criticism merely to create a feedback payload.

## Keep the review blind

Until all four first-pass records are timestamped, validated, and locked, **do
not open** any of the following:

- `../../Storage/synthetic-results/model-qualification/20260825_synthetic_qualification/blind_map_private.csv`;
- any shared `blinded/syn_*_run*.json` bundle or `blind_outputs_flat.csv`;
- `../qualitative_coding_baselines/benchmark/evaluation_guide_v1.json`;
- the run's `judges/` directory, `judge_scores_long.csv`, model summaries,
  `selection.json`, `RESULTS.md`, or paper-metric proxy results;
- anything under `coordinator_only/`, including its README, build script, and
  truth map;
- any other Direction H file containing `truth_record`,
  unblinding keys, planted-defect labels, expected dispositions, repair labels,
  or prior assessments; or
- another rater's responses.

The shared private blind map is never part of Charlie's reviewer packet. Do not
copy it into Direction H, even after the pilot.

Lock each task's first-pass record before moving to the next task. Do not revise
an earlier score after seeing a later output. If a clerical error
must be corrected, preserve the original row and append a dated amendment; do
not silently overwrite it.

## Protected-text stop rule

This pilot is synthetic only. Do **not** open, run, import, copy, or rate:

- `../../app/feedback-collector-demo/lib/study-data.ts` or the hosted Warrant Study
  real-item flow;
- anything under `../../dataset/raw/` or `../../dataset/deidentified/`;
- the real Dreaddit, AGYW/CaCHe, KODIS, or CANDOR records; or
- any packet whose provenance is not explicitly fictional/synthetic.

Stop immediately if a reviewer file exposes a real platform/source identifier,
real protected prose, `model_id`, `truth_record`, condition/failure labels, or
existing ratings. Tell the coordinator which file was exposed; do not continue
rating it.

Real text remains blocked until the documented institutional, platform,
secondary-use, rater-exposure, model-processing, retention, and excerpt-review
gates are all satisfied. A directory named `deidentified` or an app access code
does not satisfy those gates.

## End the first session

Before handoff, confirm that:

- there are exactly four unique rating records and four uniquely linked feedback
  records, one each for `DHQ-001` through `DHQ-004`;
- every record matches its manifest packet, corpus, blind output, rater, role,
  and development identifiers;
- per-metric nulls match `cannot_judge` exactly;
- each review time starts after complete-item display, stops when the canonical
  rating rationale is complete, and excludes feedback-sidecar authoring;
- no model, condition, truth, or prior-rating field leaked into reviewer files;
  and
- all eight per-task `.json` response files under
  `pilot/responses/ratings/` and `pilot/responses/feedback/` pass their schemas
  without changing substantive judgments.

From the Direction H directory, validate once more and write the immutable
review lock:

```bash
python3 scripts/validate_artifacts.py --reviewer-safe
python3 scripts/lock_reviews.py
```

The lock command must report four paired tasks and
`truth_opened_by_this_step = false`. If either command fails, stop; do not open
coordinator material or edit a substantive response merely to make validation
pass.

Complete the post-lock blinding-integrity debrief after the fourth task:

```bash
python3 scripts/record_blinding_debrief.py
```

Disclose any item you recognized, construction detail you remembered, model or
condition you believe you inferred, accidental label exposure, discussion with
another person, or timing interruption. The debrief is metadata for sensitivity
analysis; it must not alter the locked first-pass records.

After the debrief is saved, create the schema-exact handoff exports without
opening coordinator truth:

```bash
python3 scripts/export_locked_ratings.py
```

The ratings export contains direct `qc-paper-metrics-v1` objects, one per line;
the feedback export is separate. Do not merge sidecar fields into a rating row.

Then give the locked files to the coordinator and stop. The coordinator—not
Charlie during blinded rating—creates matched no-feedback and Charlie-feedback
revision cases using the frozen revision manifest. Repair outputs are judged by
a separate blinded assessment step. Do not unblind simply to see whether
Charlie's ratings were "right."

The first pilot can establish whether this workflow is usable and whether a
single construction-involved researcher supplied actionable feedback. It cannot
establish population-level human accuracy, expert equivalence, or a paper
effect. Those claims require the planned independent, blinded confirmatory
reviewers.
