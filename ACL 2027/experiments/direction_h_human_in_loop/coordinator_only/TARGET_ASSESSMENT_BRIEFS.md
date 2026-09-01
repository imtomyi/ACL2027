# Preparing target-assessment briefs

The template is deliberately incomplete. It contains no task label, target
criterion, rating, model result, or expected outcome, and the panel packager
rejects every `__REQUIRED_*__` value.

After a non-Charlie verifier has completed
`construction_verification.json`:

1. Copy `target_assessment_briefs.template.json` to
   `target_assessment_briefs.json`.
2. Record the SHA-256 hash of the exact completed construction-verification file.
3. Use a stable non-Charlie pseudonym and the actual preparation time with a UTC
   offset.
4. Add exactly one row for every committed `controlled_defect` task whose
   itemwise disposition is `verified_for_detection`. Remove the placeholder row
   and do not add a control, `workflow_only`, or `reject_item` task.
5. Give each row an opaque arm-blind reference ID matching `TAR-` plus 16 random
   uppercase hexadecimal characters, and the minimum packet-relative criterion
   an assessor needs to decide whether the target problem is absent after
   revision.
6. Do not name or imply feedback arm/source, Charlie, model/provider/snapshot,
   private condition labels, revision diagnoses, expected global outcomes, or
   another assessor's judgment.
7. Do not copy protected real text. Version 1 accepts only the fictional
   `synthetic_cc0` pilot.
8. Before creating revision cases, compute the SHA-256 of the exact completed
   briefs file. Copy `target_assessment_briefs.commitment.template.json` to
   `target_assessment_briefs.commitment.json`, fill both exact file hashes, a
   non-Charlie committer pseudonym, and the actual commitment time, then leave
   both files unchanged.

From the Direction H directory, obtain the two exact hashes with:

```bash
shasum -a 256 coordinator_only/construction_verification.json \
  coordinator_only/target_assessment_briefs.json
```

After filling the commitment, do not reformat either source file. The scripts
hash file bytes, so even whitespace changes require a new prospective
commitment before any case or model call.

The same task brief is used unchanged across both feedback arms and every frozen
repeat. Do not revise a brief after its commitment or after seeing an output or
assessment. `scripts/prepare_revision_cases.py` refuses to allocate anything
until the completed briefs and their commitment validate, and embeds all three
file hashes in the private allocation. The recorder and panel packager recheck
those hashes and require every model invocation time to be strictly later than
the commitment time.
