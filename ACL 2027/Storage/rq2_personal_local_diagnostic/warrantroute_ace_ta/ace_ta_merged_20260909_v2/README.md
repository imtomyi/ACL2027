# Active ACE-inspired WarrantRoute TA experiment

Run ID: ace_ta_merged_20260909_v2. Started 2026-09-09 KST.

The background worker begins with technical qualification: one development
episode and a judge-call check per dataset/model. Passing the 12 combinations
automatically continues to the remaining development and evaluation inventory.
The first qualification attempt is retained in ../ace_ta_merged_20260909/ and
was superseded before evaluation to exclude oversized development inputs.

- [Current statistics](stats.json)
- [48-row CSV](results.csv)
- [Readable results table](results.md)
- [Frozen execution protocol](execution_protocol.md)
- [Frozen plan and data-split audit](manifest.json)
- [Initial shared Playbook](seed_playbook.json)

Live generated Playbooks appear at:
development/<dataset>/<model>/playbook_current.json and playbook_frozen.json.
Every episode retains its feedback, proposed delta, accepted/rejected operations
and before/after memory identity. A seed alone is not a learned Playbook.

Planned inventory: 240 development episodes and 4,800 evaluation outputs across
four datasets, four methods and three same-model conditions. All 400 evaluation
packets remain the same as the selected historical packet inventory, with only
source evidence/context supplied to the new TA task. No constructed claims or
answer labels enter generation. CaChe is a within-source diagnostic explicitly
authorized by the user; its development records/text do not repeat evaluation
records/text. Three other corpora use source-disjoint development.

The worker saves statistics after each completed evaluation item and quality
judgment. Checkpoints are retained at 50/100 judged items per cell and every 50
global quality items. The five-minute Codex progress automation reports updates
including when an in-flight call has not yet finished. Failures and unresolved
judgments remain visible rather than being silently excluded or rejudged.

This run uses local Ollama only and does not spend paid API credits. Results are
private working diagnostics, not manuscript-qualified findings.
