# ACE-TightLoop Execution Assessment

Assessment date: 2026-09-05. Governance check timestamp: 2026-09-05T07:04:47Z.

Requested implementation: `experiments/direction_h_human_in_loop/`.

**Outcome: model experiment not started. Controller unit tests passed. Real-data preflight blocked.**

No corpus item was opened for this assessment, no model inference was requested,
no Portkey spending occurred, no queue was started or changed, and no Table 3
result was modified. This is an execution-readiness record, not an experimental
result or empirical validation of the method.

## What Exists

The current design is [ACE-TightLoop v1](../experiments/direction_h_human_in_loop/protocol/ace_biomedical_tight_loop_v1.md),
which supersedes the v0 ACE adaptation document. It specifies an independent
Proposer and Evidence Scout, conditionally active Methods and Domain
Challengers, an issue-linked Reviser, and human-approved Playbook updates.

The [controller](../experiments/direction_h_human_in_loop/scripts/ace_tight_loop_controller.py)
implements role requirements, model-family separation checks and decisions
about waiting, acceptance, revision, escalation and quarantine. It consumes a
state supplied by a caller. It does not itself call an LLM, choose a route from
source evidence, verify quotations against source text, execute revisions,
persist a trajectory or update a Playbook.

The [state schema](../experiments/direction_h_human_in_loop/schemas/ace_tight_loop_state_v1.schema.json)
is present. Executable fixed prompts and an end-to-end ACE-TightLoop model
transport/orchestrator were not found in this implementation. Other existing
WarrantRoute runners are not evidence that this successor design has run.

## Checks Executed

```sh
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s "ACL 2027/experiments/direction_h_human_in_loop/scripts" \
  -p "test_ace_tight_loop_controller.py" -v
```

Result: **10 tests passed**, process exit code 0. Tests cover four route modes,
missing-agent waiting, clean acceptance, minor-issue handling, material-issue
revision, hard-check revision, hash-failure quarantine, proposer/reviser family
separation, round limits and call-budget limits.

These are source-text-free software tests. They do not test model accuracy,
source-based hard-check computation, real human approval, end-to-end schema
validation or the full experimental workflow.

```sh
env PYTHONDONTWRITEBYTECODE=1 python3 \
  "ACL 2027/experiments/direction_h_human_in_loop/active_real_data/check_readiness.py" \
  --as-of 2026-09-05T07:04:47Z
```

Result: process exit code **2**. The checker stopped at a missing governance
artifact. A separate existence check confirmed that all three required local
records are absent:

- `governance/local/project_governance.local.json`
- `governance/local/reviewer_registry.local.json`
- `governance/local/privacy_review_log.local.json`

The current [data-scope policy](../experiments/direction_h_human_in_loop/DATA_SCOPE_POLICY.json)
sets real-source processing, model processing and human-rater display to false.
It names only Dreaddit and CaChe (`agyw_focus_groups`) as active targets.
GoEmotions and ParlaMint-GB are not included in this Direction H scope.

The README's historical `0/10` gate counts were not re-established by the live
checker: absent local records prevent a current assessment. This report must
not be interpreted as evidence-backed approval or as a newly measured gate
completion count.

## Implementation Needed Before Model Execution

1. **Separate versioned run contract.** Define the task, corpus scope,
   development/evaluation partitions, model-role assignments, inference
   settings, prompts, schema versions, route policy, call/token budgets,
   outputs, metrics and failure handling.
2. **Agent prompts and model transport.** Implement P/E independent first
   passes, selected M/D calls, R revisions and original-issue-owner rechecks.
   Keep outputs locked between stages and enforce cross-family requirements.
3. **Orchestrator and integrity checks.** Compute schema, evidence-ID,
   quotation, source-count and hash checks instead of trusting booleans in a
   supplied state. Validate issue ownership and resolution evidence, enforce
   the two-round limit, and add append-only checkpoints, bounded retries,
   duplicate-run protection and complete cost/token accounting.
4. **Frozen routing integration.** Supply the G/M/D/B choice to the
   controller through a documented policy. A learned expected-gain estimator
   is not required for the initial deterministic version and must not be
   silently fitted on evaluation outcomes.
5. **Evaluation and exports.** Define initial and final quality, grounded
   objection correctness, repair outcomes and cost. Controller acceptance is
   not ground truth. Keep results in a separate output namespace.
6. **Outer-loop and human workflow.** Implement the reflectors and memory
   steward with development-only evidence, provenance and named human
   approval. A disabled outer loop must be labeled an inner-loop-only pilot,
   not a complete ACE-TightLoop experiment.

Governance work can proceed alongside source-text-free implementation. Required
institutional, source/platform, provider and privacy evidence cannot be
manufactured by setting authorization flags to true. The absent local records
must be populated through the project's actual approval process before the
current Direction H lane can process item data.

## Relationship to Existing n100 Results

The v1 design explicitly describes a successor study and forbids silently
replacing the existing Table 3 WarrantRoute row. Its mixed model-family
allocation also differs from a single-model table row.

The existing n100 packets are already exposed working diagnostic material.
Reusing them would require an explicitly separate diagnostic scope and cannot
create a fresh held-out evaluation. Their constructed claims and intended flaw
targets also differ from the v1 Proposer's task of producing an analytic
candidate from evidence. The treatment of the existing claim must therefore be
specified before comparison, rather than changing the task implicitly.

Recommended next implementation step: prepare a gated, local-only inner-loop
pilot runner with fixed prompts and resumable logging, keeping Playbook
learning disabled and Table 3 unchanged. That implementation step does not
itself authorize a source-data run. An external-provider extension must retain
the separately documented cumulative USD 100 hard budget and approved provider
processing scope.
