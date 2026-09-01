# Direction J bridge response area

No ratings, feedback, receipts, paired observations, or outcomes have been
created. Collection is blocked by `../downstream_gate.json`; this directory
describes the prospective layout only.

If this bridge is prospectively activated, the collector creates three sibling
directories and commits one complete triplet at a time:

- `ratings/<sequence>_<item_id>.json` — exact unwrapped
  `direction-j-shared-rating-v1`;
- `feedback/<sequence>_<item_id>.json` — linked Direction H feedback; and
- `receipts/<sequence>_<item_id>.json` — public assignment, role, timing, and
  content-hash receipt.

Do not add placeholders, hand-edit a record, copy a rating into Direction J, or
create a `direction-j-paired-observation-v1` envelope here. The coordinator-only
private join and first-stage lock are deliberately not implemented by this
reviewer-side bridge.
