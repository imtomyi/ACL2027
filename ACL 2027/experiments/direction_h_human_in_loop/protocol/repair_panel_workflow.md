# Direction H repair-panel workflow

Status: prospective synthetic workflow; no panel items, assessments,
post-revision ratings, or results have been created.

This workflow turns frozen revision-output envelopes into arm-blind items and
then collects assessor-entered repair and artifact-quality judgments. The
packaging stage does not call a model, infer a target, or create a rating, and no
stage opens protected real text.

## 1. Prerequisites

Do not run the packager until all of the following exist and validate:

1. Charlie's complete synthetic ratings and feedback are hashed in
   `pilot/review_lock.json`.
2. `pilot/revision_freeze.json` is a completed, hash-consistent
   `direction-h-revision-freeze-v1` record with `status = frozen` and
   `freeze_scope = synthetic_pilot`.
3. The current `coordinator_only/revision_allocation.json` and every frozen
   revision case remain unchanged.
4. A non-Charlie verifier has completed
   `coordinator_only/construction_verification.json`. At least one committed
   controlled-target item has item disposition `verified_for_detection`, and
   every condition/target flag still matches the committed truth map. Overall,
   control, `workflow_only`, and rejected dispositions remain private accounting
   fields but do not veto a different eligible target.
5. Every allocated revision case has at least one retained attempt envelope in
   `coordinator_only/revision_outputs/`. One JSON file represents one attempt,
   including failures; the packager blocks a nonterminal retry chain.
6. Before case creation or any model call, the coordinator has completed and
   hash-committed the target-assessment brief file described below.

Version 1 accepts only `synthetic_cc0` material. A real-text extension must use a
separately reviewed contract after all institutional, source/platform,
model-processing, rater-exposure, privacy, retention, and excerpt-review gates
pass.

## 2. Target-assessment briefs

Create `coordinator_only/target_assessment_briefs.json` only after independent
construction verification. The packager requires this exact top-level shape:

```json
{
  "target_briefs_version": "direction-h-target-assessment-briefs-v1",
  "study_id": "direction-h-synthetic-pilot-v1",
  "construction_verification_file_sha256": "<sha256 of the exact verification file>",
  "prepared_by_id": "<non-Charlie pseudonym>",
  "prepared_by_is_charlie": false,
  "prepared_at_utc": "<ISO-8601 date-time with offset>",
  "contains_feedback_arm": false,
  "contains_model_identity": false,
  "items": [
    {
      "task_id": "<independently verified target-defect task>",
      "target_assessment_reference_id": "TAR-<16 random uppercase hex characters>",
      "target_assessment_brief": "<minimal packet-relative repair criterion>"
    }
  ]
}
```

The `items` array must cover exactly the itemwise eligible controlled-target
tasks. The brief may state the contract-relative issue the assessor must judge,
but it must not name the feedback arm or author, model/provider/snapshot, private
condition label, revision diagnosis, expected global outcome, or another
assessment. Do not create a target brief for the intended no-planted-defect
control or a `workflow_only`/rejected task; such an item needs a separately
preregistered preservation/safety contract, not the target-repair record.

Then copy
`coordinator_only/target_assessment_briefs.commitment.template.json` to
`coordinator_only/target_assessment_briefs.commitment.json`. Record the exact
hashes of the completed briefs and construction-verification files, the actual
commitment time, and a non-Charlie committer. This is the pre-revision artifact
that freezes the brief contents. The case allocation carries hashes of all three
files; every model invocation must strictly postdate the commitment.

## 3. Package reviewer-safe items

From `experiments/direction_h_human_in_loop/`, run:

```bash
python3 scripts/prepare_repair_panel.py
```

Before writing, the script validates:

- the synthetic governance assertions and all frozen artifact hashes;
- the Charlie review lock, response hashes, and exact locked
  rating-to-feedback-to-case projection without changing those records;
- independent construction verification and committed-truth linkage;
- target-brief authorship, chronology, coverage, and disclosure assertions;
- the pre-revision target-brief commitment, allocation-bound hashes, and strict
  model-generation chronology;
- the complete frozen allocation and stored revision-case cross-links;
- pair equality outside `reviewer_feedback`;
- every supplied revision-output envelope and its model/freeze/case identity;
- contiguous attempt numbering, maximum attempts, and allowed retry reasons;
- canonical revised-output hashes, evidence links, exact quotes, assignments,
  references, and diagnostic locations; and
- a deterministic value-level disclosure screen over every complete
  `revised_output`, before attempt selection, for exact feedback-arm labels,
  Charlie/feedback-author disclosures, reviewer-feedback receipt, arm
  assignment, frozen model/snapshot identifiers, and model self-identification;
  and
- the final `direction-h-repair-panel-item-v1` records and public-field allowlist.

The disclosure screen is deliberately narrower than a generic keyword filter.
It scans string values at stable JSON Pointer locations, treats exact machine
arm/field labels as diagnostic, and compares contextual/model-identity matches
against the already reviewer-visible evidence packet and starting output. Thus
an exact inherited source phrase is not reclassified as model self-disclosure,
while an introduced identity/workflow statement is blocked. Exact arm labels
block even if inherited because they directly defeat condition masking.

Any match is a protocol deviation requiring the frozen deviation/exclusion and
reporting procedure. The packager stops before either the public panel or
private arm map is written. It must not redact the string, rewrite the output,
retry a complete response, or substitute a different attempt/repeat because it
looks safer. The retained envelope stays in coordinator accounting.

Within each case, selection is the first complete, schema-valid,
hard-gate-passing attempt reached under the frozen retry rule. The script retains
all attempts in coordinator accounting and never selects a best repeat. A case
with no eligible completion produces no reviewer item and remains in the private
unavailable-case inventory. It is not dropped from analysis: under the frozen
analysis plan it remains a pipeline-level non-established success, with its
technical or unusable-completion reason reported separately. Content-level
repair components are not invented for a revision the panel could not assess.

The script refuses existing output paths. On success it creates:

- reviewer-safe `pilot/repair_panel/manifest.json` and
  `pilot/repair_panel/items/*.json`; and
- coordinator-only `coordinator_only/repair_panel_arm_map.json`, containing the
  arm join, selected attempt, unavailable cases, complete attempt inventory,
  itemwise construction exclusions, and hashes of the recorder and packager
  code used for eligibility decisions.

The packager assigns a fresh cryptographically random `RPI-` identifier to every
public panel item. This identifier is generated independently of the feedback
arm. The earlier revision-envelope `RBI-` identifier and the `RBI-` to `RPI-`
join remain only in the coordinator arm map.

The public files omit arm/source, Charlie identity, feedback, model identity,
private condition label, revision diagnosis, other assessments, and derived
outcomes.

## 4. Freeze balanced, isolated assessor assignments

Do not give a reviewer the full staging panel from step 3. First copy
`coordinator_only/repair_assessor_roster.template.json` to
`coordinator_only/repair_assessor_roster.json` and replace every placeholder.
The roster declares exact per-item replication separately for each canonical
evaluator group. Every listed assessor must be independent of study development
and revision/feedback generation, arm-blind, eligible for this panel, and not
Charlie. The roster preparer/coordinator may not also be a listed assessor,
because the coordinator receives the private arm-bearing schedule.

Then run:

```bash
python3 scripts/build_repair_assessor_assignments.py
```

The builder consumes the exact public panel, its private arm map, and the
explicit roster. It fails before writing unless it can satisfy all of these
rules simultaneously:

- every assessable panel revision receives exactly the rostered replication in
  every requested evaluator-group stratum;
- no assessor receives more than one revision variant from the same underlying
  task;
- workloads within each evaluator-group stratum differ by at most one;
- each assessor's counts across observed, assessable feedback arms differ by at
  most one;
- every public-panel/item/arm join and file hash is exact; and
- the collector, runtime instructions, panel/bundle/reference schemas,
  repair-assessment schema, unchanged shared `qc-paper-metrics-v1` schema, and
  post-revision link schema are hash-frozen before review.

The builder also refuses to freeze a schedule until the collector declares
`ASSIGNMENT_BUNDLE_CONTRACT_VERSION =
"direction-h-repair-assessor-bundle-v1"` and exposes the token, assignment
payload, and rater-binding checks below. This prevents an assignment from being
frozen while the collector still accepts the full staging manifest.

The allocated comparison remains a multi-arm ITT design even if model/runtime
failure leaves only one arm with assessable revisions. A one-observed-arm panel
is permitted only when the private arm map proves that: every task/repeat block
was allocated to all arms (including `no_feedback`); every absent paired case is
listed in `unavailable_target_cases` with the frozen terminal-unavailability
reason; its retained attempt inventory is nonempty and contains no eligible
complete hard-gate-passing output; and selected plus unavailable cases exactly
equal the verified target-case denominator. The private schedule freezes the
allocated arms, observed arms, unavailable-case count, and canonical hash of
the unavailable inventory separately.

Assignments and per-item replication cover only revisions that actually exist
and can be assessed. Terminal-unavailable paired cases remain in the pipeline
ITT denominator as non-established successes under the analysis plan; they do
not receive invented R/P/C/Y judgments or shared metric ratings. With one
observed arm, within-rater arm balance is vacuous, while exact item coverage and
within-stratum workload balance remain enforced.

On success, it creates a private
`coordinator_only/repair_assessor_schedule.json` and one subset under
`pilot/repair_assessor_bundles/<bundle_id>/` per assessor. The schedule is the
only file that contains stable rater pseudonyms, raw 256-bit tokens, source
panel IDs, arm labels, and alias joins. Each reviewer bundle instead contains:

- only that assessor's assigned items, never the full panel or twin list;
- a random bundle ID and assessor alias;
- one stable opaque `RAI-` alias per underlying panel revision, one stable
  `RAT-` alias per underlying task, and one stable `RAREF-` alias per target
  reference; and
- exact item, payload, parent-manifest, token, rater-binding, and frozen
  instrument hashes; plus
- a self-contained `runtime/` directory containing the exact collector,
  every schema it loads (including referenced pilot/qualitative-output
  schemas), and reviewer instructions. Every shipped runtime file is pinned in
  `frozen_instrument_hashes` and in the private bundle-tree hash.

Aliases are stable across assessor bundles for the same underlying revision so
the direct shared rating uses one comparison-safe `output_id`. They are derived
from a private random schedule seed and do not encode arm, rater, model, repeat,
or condition. A reviewer still sees at most one `RAT-` variant.

The directories produced in the workspace are coordinator staging artifacts.
Deliver each assessor only their one bundle directory in a separately
access-controlled location, plus their raw assignment token through a separate
channel. Do not expose the bundle root, sibling bundle names, the private
schedule, the public staging panel, or the arm map. Local `0700`/`0600`
permissions reduce accidental exposure but do not replace separate reviewer
access controls.

### Collector authorization contract

Collection must use the isolated-bundle interface. The collector must require
all six arguments and must have no default or fallback to the full staging
panel. The preferred command is run from inside the separately delivered
`RAB-*` directory and needs no project checkout:

```bash
python3 runtime/collect_repair_assessment.py \
  --bundle-root . \
  --manifest manifest.json \
  --rater-id independent_reviewer_01 \
  --evaluator-group qualitative_methods_expert \
  --assignment-token <64-lowercase-hex> \
  --blind-id RAI-<20-HEX>
```

The shared-checkout collector may be used by a coordinator for a local dry run,
but it requires the same explicit `--bundle-root` and exact
`<bundle-root>/manifest.json`; it confers no access beyond that one bundle.

Before displaying an item or creating a response directory, the collector must
perform the following checks using only the supplied isolated bundle, raw
token, command-line rater pseudonym/group, and current local instrument files:

1. Require an explicit `RAB-*` bundle root and the exact
   `<bundle-root>/manifest.json`. Require and validate
   `bundle_manifest_version = direction-h-repair-assessor-bundle-v1`; reject the
   `direction-h-repair-panel-manifest-v1` staging manifest and every
   coordinator-only path.
2. Require the bundle's exact allowlisted fields, `synthetic_only` scope,
   `contains_real_source_text = false`, contiguous unique display order, and no
   arm/source/model/rater/twin keys or values.
3. Recompute every assigned item hash and row/item identity, including
   `corpus_id`; require unique `RAI-` and `RAT-` values within the bundle.
4. Rebuild this object and require its compact, sorted-key UTF-8 JSON plus one
   LF SHA-256 to equal `assignment_payload_sha256`:

   ```json
   {
     "assignment_payload_version": "direction-h-repair-assignment-payload-v1",
     "study_id": "<bundle study_id>",
     "schedule_id": "<bundle schedule_id>",
     "bundle_id": "<bundle bundle_id>",
     "assessor_alias": "<bundle assessor_alias>",
     "evaluator_group": "<bundle evaluator_group>",
     "parent_panel_manifest_sha256": "<bundle parent hash>",
     "frozen_instrument_hashes": {
       "repair_assessment_collector_script_sha256": "<hash>",
       "repair_panel_item_schema_sha256": "<hash>",
       "repair_assessor_bundle_schema_sha256": "<hash>",
       "pilot_item_schema_sha256": "<hash>",
       "qualitative_output_schema_sha256": "<hash>",
       "repair_assessment_schema_sha256": "<hash>",
       "paper_metric_rating_schema_sha256": "<hash>",
       "post_revision_rating_link_schema_sha256": "<hash>",
       "repair_assessor_runtime_readme_sha256": "<hash>"
     },
     "items": ["<the exact ordered bundle item rows>"]
   }
   ```

5. Require the supplied token to be exactly 64 lowercase hex characters and
   recompute the following UTF-8, NUL-delimited hashes (no trailing NUL):

   ```text
   assignment_token_sha256 = SHA256(
     "direction-h-assignment-token-v1" NUL study_id NUL schedule_id NUL
     bundle_id NUL assignment_token
   )

   rater_binding_sha256 = SHA256(
     "direction-h-rater-binding-v1" NUL study_id NUL schedule_id NUL
     bundle_id NUL rater_id NUL evaluator_group NUL
     assignment_payload_sha256 NUL assignment_token
   )
   ```

   Both values must equal the bundle fields; the command-line evaluator group
   must also equal the bundle group. Charlie's rater ID remains prohibited.
6. Require the exact `runtime/` file inventory and hash the collector, runtime
   README, repair-panel item schema, bundle schema, referenced pilot and
   qualitative-output schemas, repair-assessment schema, shared paper-metric
   schema, and post-revision link schema. Both the shipped copies and the files
   actually used by the running collector must equal
   `frozen_instrument_hashes`. A missing, extra, symlinked, or drifted runtime
   entry blocks before item display.
7. Permit only a requested `--blind-id` present in this bundle. Save responses
   only below this bundle's own `responses/<rater_id>/` directory, enforce one
   `RAT-` task per rater, and keep the existing all-or-none three-record write.

These checks let the collector authenticate its assignment without opening the
private full schedule. Possession of a token does not grant access to any item
outside the one delivered bundle.

The assessor completes two distinct records for the same blinded revision:

1. a Direction H repair assessment containing R
   (`target_defect_repaired`), P (`accurate_relevant_material_preserved`), C
   (`collateral_error_present`), component-specific cannot-judge values,
   collateral flags and localized findings, confidence, disposition, rationale,
   and review time; and
2. a direct, unwrapped object conforming to the unchanged shared
   `qc-paper-metrics-v1` schema, containing the three ordinal artifact-quality
   constructs, construct-specific abstention, confidence, disposition, serious
   error flags, `requested_expertise`, rationale, and review time.

The shared row copies `packet_id`, `corpus_id`, and `evaluation_role` from the
reviewer-safe panel item and uses the fresh `blinded_revision_id` as `output_id`.
It contains no Direction H wrapper or extra linkage field. A separate
`direction-h-post-revision-rating-link-v1` record stores the canonical hashes and
identity join between the shared row and the repair assessment without changing
either measurement schema.

The one visible review session begins immediately before the complete item is
displayed. Repair components are recorded first. The repair assessment's
`review_seconds` is cumulative from display through completion of that section;
the shared rating's `review_seconds` is cumulative from the same display through
completion of the later metric section. The link also records the incremental
metric-entry interval. That interval is not a cold-review duration, and neither
timer should be compared to a rating-only workflow without this qualification.

Y (`successful_repair_without_collateral_error`) is derived exactly from R/P/C
and remains only in the repair record. Nothing is written until the assessor
types `SAVE`. The collector then publishes one all-or-none bundle containing
`repair_assessment.json`, `post_revision_rating.json`, and `rating_link.json`
under
`<delivered RAB bundle>/responses/<rater_id>/<assessment_id>/`.
It refuses an overwrite, an incomplete existing bundle, or a second variant of
the same task for that assessor.

## 5. Lock all planned response triples before unblinding

After every rostered assessor has finished every assigned item, run:

```bash
python3 scripts/lock_repair_assessments.py
```

The lock command revalidates the frozen schedule and every input/instrument
hash, the exact shipped runtime tree, token/rater binding, bundle manifest and item, expected assessor/task
identity, schema, exact direct shared-rating fields, canonical assessment/rating
hash link, timer relation, collateral localization, and response path. It
requires exactly the planned set of three-record bundles and rejects missing,
duplicate, pending, extra, symlinked, or drifted entries.

Only a successful run writes the exclusive coordinator-only
`repair_assessment_lock.json` with `unblinding_ready = true`. Keep the arm map
and private schedule inaccessible to assessors and analysts until this lock
exists and the remaining analysis/unblinding conditions in the study protocol
are met. A manual completion claim is not a substitute for the lock.
