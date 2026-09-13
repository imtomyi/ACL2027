# Four-Paragraph Dreaddit Playbook Smoke Test

Protocol: `dreaddit-four-paragraph-playbook-smoke-v1`.
Purpose: a user-requested, temporary local development experiment checking
paragraph-native review and the real Playbook update/use path. It is not the
gold-scored Table 3 experiment and does not relax that experiment's gold gate.

## Data and Scope

Use exactly four source paragraphs, not four four-record review packets. Select
the four evidence records from the lexicographically first Dreaddit development
packet in the existing hash-verified prepared inputs. Select before observing
any new model outputs. Confirm development status, unique record/text identities,
and no overlap with the prepared evaluation panel's records, text or sources.
Retain private source IDs and hashes. Do not import an old constructed claim,
intended flaw label, stress label, prediction, score, or learned Playbook.

Each paragraph becomes one query. The adapter retains `task.claim` as the full
original paragraph and supplies the same paragraph in `task.evidence` only as
a quote-anchor container. The prompt explicitly says this duplication is not
independent corroboration. No replacement claim, synthetic flaw or repair is
generated. Review only material internal inferential or contextual problems.
Self-reported feelings, uncertainty, hypotheses and questions are not by
themselves flaws. Do not diagnose writers or judge their character.

## Adaptation and Workload

Use local Gemma 3 4B with the pinned installed digest and the existing deterministic
generation options. Process four paragraphs over three prespecified epochs:
12 query exposures, not 12 independent datapoints. Carry memory across queries
and epochs. There is no held-out test phase in this small development smoke run.

Each valid query runs one integrated detector, one Reflector/Curator and at most
one delta auditor. New rules are not mandatory: negative cases can yield useful
bounded procedures, but unsupported, duplicate and uncertain edits must still
be withheld. Do not rerun unfavorable or failed outputs for a better outcome.
Maximum: 36 model calls and a 20-minute inference budget. There are no paid API
calls or model downloads. Initialization and shutdown are operational overhead.

Accepted items receive stable `[shr-00001]` IDs and the four existing rule fields.
Refinement retains identity. Publish `playbooks/dreaddit/current.txt` after each
committed result and before the next query, retaining JSON state, revision history,
provenance and hashes. Record the exact retrieved TXT in each prediction and
verify it against the actual detector request journal. Repeated exposure is not
independent rule support. Do not force growth or disable the six audit criteria.

## What Success Means

Operational update-chain success requires all 12 queries complete without a
technical failure, at least one admitted add/refine operation, a learned rule
included in a later query, and all detector TXT requests verified against their
locked memory text. Report added/refined/reinforced/withheld counts and observed
rule applications separately. Applications and semantic audit decisions are
same-model self-reports, not independent proof of correct detection or benefit.

If no defensible update is admitted, report that honestly. Completion alone does
not imply the update chain was demonstrated. Keep any failure or no-change
outcome and its reason. No adjudicated gold inventory is available for these
paragraphs: do not compute detection accuracy, TP/FP/FN, or Credibility/Conformability
success rates. All artifacts are private diagnostics under Storage, never
manuscript evidence or replacements for historical Table 3 cells.

## Execution Safety and Outputs

Use the shared project execution lock and a run-specific lock. Do not bypass a
lock owned by the paused prior experiment. Releasing paused processes requires
the user's approval and must preserve all previous artifacts. Explicit local
inference authorization is required. Freeze the inputs, order, prompts, config
and source snapshot before launch. Invoke the source entry point only while its
hashes match that snapshot. A change requires another versioned run.

Reuse an existing local Ollama service if available. Otherwise start a loopback
service with cloud use disabled and stop only the service this run owns on exit.
Ambiguous dispatches stop for diagnosis. Durable results replay without a new
model call. Context limits reject oversize requests without truncating evidence.

Outputs include `inputs.private.json`, `schedule.json`, immutable call and result
journals, `query_progress.csv`, `summary.md`, `status.json`, the Playbook TXT and
its revision history, and a final manifest. Keep this run separate from the
previous paused experiment and all scored experiment exports.
