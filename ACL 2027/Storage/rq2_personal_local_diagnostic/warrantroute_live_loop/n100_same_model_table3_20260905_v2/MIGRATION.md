# Verified Continuation After a Default-Path Edit

Date: 2026-09-05. Predecessor: `n100_same_model_table3_20260905_v1`.

The predecessor completed the first CaChe/Qwen trajectory, with six complete
calls, two revision rounds, no execution error, and a human-escalation terminal
state. Before its quality judgment, the source hash guard detected a concurrent
edit to `run_warrantroute_loop_n100.py` and stopped the supervisor.

The sole bound implementation change was `DEFAULT_CONFIG`, from
`warrantroute_loop_n100_v1.json` to `warrantroute_loop_n100_same_model_v1.json`.
Both supervisors already selected the same-model config explicitly. Exact
source comparison verified this was the only changed line. All other frozen
implementation and asset hashes matched; the full configuration objects were
equal. No prompts, packets, model digests, generation settings or decisions
were selected or changed based on outputs.

The six complete call journals for `PKT_0029910e85300902` were verified by their
record hashes and copied byte-for-byte into this new run's corresponding
CaChe/Qwen call directory. The original files and result remain untouched.
The new runner reconstructed the trajectory using those cached calls while
its LLM transport was replaced by an assertion that forbade any generation.
This completed successfully with six reused calls and zero transport calls.
The runtime verified every cached request identity against the new configuration.

The new result binds the same outputs to the new plan hash. This is a provenance
continuation, not a second stochastic trial, score-based retry, or replacement
sample. The six calls' original usage and wall time are retained. No old result
file was copied with a mismatching plan hash. No quality outputs existed to
migrate. All subsequent generation uses this frozen v2 plan and quality contract.

Count this packet once in the 1,200-trajectory inventory. The predecessor is
an archived provenance record, not an extra independent observation.
