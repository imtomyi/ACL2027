# Independent repair panel staging

No panel item or assessment exists. Only complete, integrity-valid revisions
may be staged. Use fresh arm-blind packet IDs and a frozen balanced incomplete
block with at least three independent assessors per revision, no Charlie, no
feedback author assessing their own revision, no target verifier, and at most
one arm variant of an item per assessor. Assessors use Direction J's unchanged
`direction-j-repair-assessment-v1` record. Lock all assessments before arm
unblinding; unavailable pipeline cases remain ITT failures and are not sent to
the panel.
