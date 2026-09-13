# ACE-inspired TA experiment v5

This replacement run adds constrained Playbook citation IDs to the v4 protocol.
Data selection is unchanged. Prior qualification attempts are retained separately.
Engineering checks use development data and do not enter evaluation results or
the learned evaluation Playbooks.

- Frozen execution policy: [execution_protocol.md](execution_protocol.md)
- Current statistics: [stats.json](stats.json)
- Table: [results.md](results.md) and [results.csv](results.csv)
- Qualification status: qualification.json after structural checks pass
- Active work: phase.json and active_call.json
- Learned memory: development/<dataset>/<model>/playbook_current.json
- Evaluation memory: development/<dataset>/<model>/playbook_frozen.json

Planned: 240 development episodes and 4,800 evaluation outputs across 48 cells.
Per-cell statistics checkpoints occur after 50 and 100 judged packets.
CaChe is a within-source diagnostic with no dev/eval repeated records or exact
text. These are private working diagnostics, not manuscript-qualified results.
Historical Table 3 is not modified by this run.
