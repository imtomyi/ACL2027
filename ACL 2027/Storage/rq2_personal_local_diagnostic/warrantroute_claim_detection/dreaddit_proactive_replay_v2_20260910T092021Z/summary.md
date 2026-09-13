# Proactive Dreaddit Replay

Status: `paused_at_query_boundary`.

Completed exposures: 26/36, using the same 12 paragraphs over 3 epochs.
Distinct candidate contents: 23; candidate occurrences: 40.
New admitted rule IDs: 2; delivered in later detector calls: 2.
Active rules: 3 initially, 5 currently.
Technical failures: 0; local calls: 72; paid calls: 0.

Reused pre-error queries: 12; new local calls in this version: 38.

## Files

- [Inputs](data_points.md)
- [Per-query outcomes](query_progress.csv)
- [Candidate register](candidates/current.txt)
- [Initial Playbook](playbook_comparison/playbook_initial.txt)
- [After Playbook](playbook_comparison/playbook_after.txt)
- [Exact changes](playbook_comparison/changes.diff)

## Interpretation

Candidate IDs are content identities, not proof of distinct useful lessons. Rejections remain visible.
All 36 exposures are scheduled regardless of rule growth. Refine, reinforce and repeated delivery do not count as new rules.
Detector, auditor, model/options, admission criteria, retrieval and memory capacity are unchanged.
Learning now searches four opportunities and uses the latest prior same-paragraph learning decision within this run.
v2 uses an equivalent compact learning schema only when the original representation exceeds admission. If still needed, historical reflection prose is omitted while retaining candidate fields and audit feedback.
An inherited prefix is byte-preserved, not regenerated. The interrupted v1 suffix and its infrastructure failures remain in the source run; this is a documented software-repair branch.
No prior comparator outputs, held-out items, gold labels or quality judgments enter the learning prompt.
Same-model admission and reported rule use do not establish semantic correctness or improved detection.
Inherited rule limitations remain; this is an unscored development replay, not independent evaluation.
Accuracy, Credibility and Conformability remain unassessed. Manuscript and Table 3 are untouched.
