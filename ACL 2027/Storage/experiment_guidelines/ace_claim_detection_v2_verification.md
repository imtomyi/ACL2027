# Detection-First v2 Verification

Date: 2026-09-10. Private software verification, not experimental performance.

## Implemented and Tested

The source runner uses `claim-flaw-detection-scoring-v2` for new preparations.
It locks static/online predictions before private gold-based assessment, computes
one-to-one typed and grounded TP/FP/FN, exports per-type results and detection-gated
C/F composites, and keeps gold and grading feedback out of Playbook updates.

Offline test command from the `ACL 2027` directory:

```sh
/opt/anaconda3/bin/python3 -B -m unittest discover -s experiments/warrantroute_claim_detection -p 'test_*.py' -q
```

Outcome: **155 tests passed**, including 32 strict-scoring/integration tests.
Tests cover wrong types, semantic mismatches, invented quotations, duplicate
reports, maximum rather than greedy matching, missed flaws, verified negatives,
abstentions, prediction failures, unknown/failed matching judgments, hash binding,
gold coverage, missing-gold launch blocking, payload isolation, immutable replay,
all-four-dataset exports and the prevention of resolved-only 100-percent rates.
Tests use offline fixtures and make no real inference request. They do not
establish the semantic accuracy of an LLM assessor or qualify a gold inventory.

## Prepared Snapshot

```text
Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/
  ace_claim_online_v2_detection_dev10_stream80_20260910_prepared
```

- Status: `prepared_not_started`.
- Gold status: `missing_blocks_inference`.
- New model calls: **0**; no call directory or runtime clock.
- Planned: 120 development exposures, 320 paired evaluation items, 640 reviews.
- Maximum local inference calls: 2,280.
- All 12 frozen files verified against their manifest hashes.
- Maximum initial seed-detector context bound: 26,443 against 32,768.
- Downstream assessment admission is checked dynamically, not certified by the
  initial bound. No evidence truncation or retries are authorized.

The prepared snapshot is intentionally not runnable without gold. Supply a real,
complete bank and prepare another fresh snapshot; do not change frozen files.
Human annotation provenance and independent semantic validation remain pending.

## Historical Preservation and Audit

The old online-v1 prepared snapshot's frozen hashes were verified unchanged.
The paused expansion's frozen contract, selected source packet hashes and locked
predictions were rechecked through the independent offline type audit. Both old
processes, PIDs 34077 and 34087, still showed stopped `T` states at verification.
No process was resumed, no automation was modified, and no paid API was used.

The historical audit contains 48 dataset/checkpoint/type summary rows. Across
515 completed E0/E3 reviews, intended-category presence in the final issue lists
was **0/515**. This is agreement with generator-intended labels only. It is not
validated recall: the labels are not complete adjudicated flaw inventories.
Strict precision/recall/F1 remain unavailable. Original scores and the historical
Table 3 were not replaced with these diagnostics.

See [audit report](../experiment_reports/flaw_type_audit_20260910/flaw_type_detection_audit.md)
and [prospective protocol](ace_claim_detection_v2.md).
