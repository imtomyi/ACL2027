# Active ACE-inspired WarrantRoute TA experiment

Run: ace_ta_merged_20260909_v4. Prepared 2026-09-09 KST.

The worker qualifies one development episode and judge call per dataset/model,
then automatically continues to 240 development episodes and 4,800 evaluation
outputs. It uses five analytic roles, one merged Playbook Updater, a persistent
Playbook and a separate fixed Qwen quality Judge.

- [Current statistics](stats.json)
- [Results CSV](results.csv)
- [Readable results](results.md)
- [Frozen execution protocol](execution_protocol.md)
- [Input split and model identities](manifest.json)
- [Common seed Playbook](seed_playbook.json)
- [Isolated Updater check and generated pilot memory](engineering_checks/merged_updater/playbook.json)

Main-experiment learned memories appear under
development/<dataset>/<model>/playbook_current.json and playbook_frozen.json.
Engineering-check memory is separate and is not injected into the experiment.
Earlier qualification versions are retained for traceability and extra-cost
accounting. No evaluation outcomes were overwritten or selected by score.

All four evaluation datasets retain 100 packets. Development uses 20 additional
packets per dataset. CaChe is explicitly authorized as a within-source diagnostic
with no repeated records or exact text across the split. Other corpora use
source-disjoint development. Oversized development candidates are excluded
before selection; source text is not silently shortened.

Statistics include Credibility, Conformability, evidence coverage, T/F/U/technical
counts, resolved denominators, token usage, calls and unresolved loops. The worker
saves 50/100 per-cell checkpoints and global checkpoints every 50 quality records.
A Codex heartbeat reports progress every five minutes, including unchanged
in-flight progress. No paid API transport is used.

These are private working diagnostics. Qualification tests format and execution,
not high scores, expert agreement or manuscript eligibility.
