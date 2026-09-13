# Guarded ACE-inspired TA run v6

Replacement for v5 after a user-authorized Playbook policy audit. Inputs are
byte-identical; all learned memories start afresh. Prior outputs remain in v5.

- Frozen protocol: [execution_protocol.md](execution_protocol.md)
- Official working statistics: [stats.json](stats.json)
- Tables: [results.md](results.md), [results.csv](results.csv)
- Interim judging: [interim_quality/report.md](interim_quality/report.md)
- Qualification: qualification.json
- Live work: phase.json, active_call.json, worker.json, screenlog.0
- Playbooks: development/<dataset>/<model>/playbook_current.json
- Final evaluation memories: development/<dataset>/<model>/playbook_frozen.json

The plan remains 240 development episodes and 4800 evaluation outputs across
48 cells. All seed rules are immutable. Proposed learned-rule mutations require
source-linked, target-specific semantic checks and deterministic safeguards.
Failures hold changes rather than silently replacing the existing memory.
These checks do not guarantee semantic correctness or improved quality.

The common output cap increases from 2400 to 4096 tokens to address prior
truncations. Model and method comparisons within v6 use the same cap. Development
guard calls and interim judgments have separate costs. Engineering checks are
not evaluation data or imported learned memory. CaChe remains a within-source
diagnostic. No results from this run are manuscript-qualified.
