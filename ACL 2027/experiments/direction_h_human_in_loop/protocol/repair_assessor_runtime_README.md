# Direction H isolated repair-assessor package

This `runtime/` directory is part of one assessor-specific, synthetic-only
`RAB-*` bundle. It contains the exact collector and schemas frozen in the
bundle manifest. You do not need the ACL 2027 project checkout.

Keep the entire delivered `RAB-*` directory together. Do not open or request
the full repair panel, a sibling assessor bundle, the private schedule, an arm
map, feedback, model information, or another assessor's response.

From inside the delivered `RAB-*` directory, run one assigned item at a time:

```bash
python3 runtime/collect_repair_assessment.py \
  --bundle-root . \
  --manifest manifest.json \
  --rater-id <pseudonym delivered by the coordinator> \
  --evaluator-group <group delivered by the coordinator> \
  --assignment-token <64-character token delivered separately> \
  --blind-id <RAI identifier from manifest.json>
```

The collector verifies the assignment token, rater binding, bundle and item
hashes, and every runtime file before it displays an item. It saves only after
you review the summaries and type `SAVE`. Completed records stay under this
bundle's `responses/` directory. Return that directory through the approved
study channel; do not rename or edit its contents.

Stop and contact the coordinator if a hash check fails, the displayed material
is not explicitly synthetic, the bundle includes more than your assignment,
you recognize an arm/model/feedback author, or you encounter protected text.
