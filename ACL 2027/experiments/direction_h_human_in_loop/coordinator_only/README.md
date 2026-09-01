# Coordinator-only material — do not open during rating

This directory contains the synthetic pilot construction recipe and the
condition map. Charlie must not inspect any file here until all four core
ratings and linked feedback records have been validated and locked.

The directory contains no protected real text. It is nevertheless restricted
during collection because it reveals which synthetic outputs were altered and
which serious-error flag was predeclared for each alteration.

## Independent repair-assessor assignment files

After the repair panel is packaged, copy
`repair_assessor_roster.template.json` to `repair_assessor_roster.json` and
replace every placeholder with an eligible independent reviewer pseudonym and
the exact per-item evaluator-group replication targets. Do not list Charlie or
anyone who helped develop the study or produced a revision/feedback input.

`scripts/build_repair_assessor_assignments.py` then writes two non-overlapping
products:

- reviewer-safe, token-bound subset bundles under
  `pilot/repair_assessor_bundles/`; and
- `repair_assessor_schedule.json` here, containing the private reviewer,
  token, source-ID, stable-alias, arm, and bundle-hash joins.

The raw token for each assessor appears only in the private schedule. Deliver
that token out of band and deliver only the matching individual bundle in a
separate access scope. Never share the schedule, the full bundle root, sibling
bundle names, the staging panel manifest, or the arm map with an assessor. Each
individual bundle now includes its own hash-pinned `runtime/` collector and
schemas, so the assessor does not need the shared project checkout. Have the
assessor run from inside the delivered `RAB-*` directory with explicit
`--bundle-root .` and return its unchanged `responses/` directory through the
approved channel. Reinsert responses only into the matching staged `RAB-*`
directory before running the lock.

If only one allocated arm produced assessable revisions, the builder proceeds
only when the private arm map proves every missing paired case terminal under
the frozen retry policy. The schedule retains the allocated/observed arm split
and unavailable-case commitment. Do not create placeholder assessments for
those unavailable cases; they remain pipeline-level ITT non-established
successes.

After all planned reviews, `scripts/lock_repair_assessments.py` requires the
exact complete set of three-record response bundles and writes
`repair_assessment_lock.json`. Do not unblind arms without that validated lock.
The exact commands, token/rater hash formulas, collector integration contract,
and lock checks are in `protocol/repair_panel_workflow.md`.

After Charlie's review lock, a non-Charlie verifier completes
`construction_verification.json`. The coordinator then completes
`target_assessment_briefs.json` for only the itemwise eligible controlled
targets and freezes its exact hash with
`target_assessment_briefs.commitment.json` before revision-case creation or any
model call. The allocation retains controls, `workflow_only` tasks, and rejected
tasks as private exclusions.

For the confirmatory extension, move the corresponding construction map to an
access-controlled location unavailable to all raters, revision operators, and
repair adjudicators. A procedural `DO NOT OPEN` boundary is sufficient only for
this internal synthetic workflow qualification.
