# Complete the revision freeze before any revision call

`revision_freeze.template.json` is a schema-valid draft, not an authorization to
run a model. It deliberately contains `__REQUIRED_*__` placeholders and
`status = draft`; the case builder rejects both.

The coordinator must, without using Charlie's observed rating or feedback to
select a favorable model:

1. copy the template to `revision_freeze.json`;
2. fill the exact provider, model ID, dated or otherwise immutable snapshot,
   runtime surface, and freeze ID;
3. verify or deliberately change every decoding, retry, repeat, and token-limit
   value rather than accepting the template as an empirical choice;
4. recompute every artifact hash after any file change, including the shared
   integrity validator, revision-output recorder, and repair-panel packager;
5. set the actual UTC freeze time and `status = frozen`;
6. validate the completed record against
   `../schemas/revision_freeze_manifest.schema.json`; and
7. retain the completed manifest unchanged with all attempted runs.

For this synthetic pilot the two arms remain `no_feedback` and
`charlie_feedback`, tools/retrieval remain disabled, every independently
verified controlled-target item enters both arms, and no best-repeat selection
is permitted. Controls, `workflow_only` items, and rejected items remain in
private exclusion accounting. A protected-text extension
cannot reuse the synthetic gate values; it needs a separately approved manifest
after all institutional, source/platform, model-processing, rater-exposure,
privacy, retention, and excerpt-review gates clear.

After all Charlie records are locked, Charlie's schema-valid post-lock blinding
debrief is saved with the official v1 `condition_masked` classification,
independent construction verification is complete, and the completed target
briefs have an exact-hash commitment, the coordinator may build paired cases
with:

```bash
python3 scripts/prepare_revision_cases.py
```

Before it opens coordinator truth, the builder rechecks the exact four-task
review-lock identity, order, response paths and hashes, false mutation/truth
flags, and the post-lock debrief identity, schema, masking classification, and
chronology. Still before opening coordinator truth, it revalidates every public
item's exact file hash, canonical evidence-packet and candidate-output hashes,
schema, internal IDs, and `synthetic_cc0` classification. It then checks
itemwise eligibility, exact brief and commitment hashes, freeze schema,
placeholders, artifact hashes, paired-arm configuration, identity stripping,
and that the only model-visible difference inside each pair is
`reviewer_feedback`.
