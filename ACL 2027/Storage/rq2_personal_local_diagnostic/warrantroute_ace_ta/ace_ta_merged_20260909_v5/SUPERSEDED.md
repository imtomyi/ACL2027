# Superseded after Playbook policy audit

The user authorized remediation on 2026-09-09 after the audit found a
case-specific code complaint had deactivated seed-dreaddit in episode 11.
The original operation, feedback, memory and judgments are retained unchanged.
No evaluation outputs existed at migration. This run is not merged into v6.

Worker 68276 was suspended at a completed-call boundary and terminated without
submitting the next call. The last completed journal was Dreaddit/Qwen episode
013 revision_2, finished 2026-09-09T03:16:36.327275+00:00. That partial episode
is preserved and will not be retried under this run ID.

The replacement is ../ace_ta_merged_20260909_v6, with byte-identical inputs,
fresh seed memory, protected seed rules, guarded learned-rule mutations,
conflict/identifier checks and a common 4096-token output cap. The earlier cap
was 2400. Thus this migration is not an isolated Playbook-effect comparison.
Do not restart v5, modify its records, or reuse its learned memory in evaluation.
