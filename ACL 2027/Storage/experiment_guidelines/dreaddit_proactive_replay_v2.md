# Proactive Dreaddit Replay v2: Context Admission Repair

This private development protocol retains the objective and rules of
[v1](dreaddit_proactive_replay_v1.md). It adds a documented infrastructure repair,
not a relaxed admission criterion or a new performance claim.

## Why a New Version

The initial proactive run paused after 16 queries. Its first 12 queries had no
technical failures. Three learning steps in epoch 2 were blocked BEFORE sending
an API request because repeated schema definitions, expanded memory and previous
learning feedback exceeded the conservative context admission bound. All 16
queries, including the failures and subsequent outputs, remain in that run.

## Fixed Representation

Keep the same model, options, prompts, input paragraphs, schedule, initial state,
six audit criteria, memory capacity and scoring restrictions. When the original
learning request exceeds admission, factor repeated property definitions into
JSON Schema `$defs` and `$ref`. Each operation still has a complete object schema.
The permitted JSON outputs and downstream validators remain unchanged. Do not
use a partial `anyOf` intersection that the grammar backend may interpret
differently from a general JSON Schema validator.

If factoring alone is insufficient, send a declared projection of the previous
same-paragraph learning record: retain all four candidate fields, candidate IDs,
operations, outcomes, failed criterion names, epoch and the binding record hash.
Omit repeated reflection prose, audit prose and duplicate receipt metadata only.
The complete originals remain immutable on disk. Never truncate the current
paragraph, locked prediction or active rules; never increase the context limit
or bypass admission. A request that still does not fit remains an explicit error.

## Preserve and Continue

The frozen replay may inherit the entire consecutive valid prefix before the
first context-admission failure. The boundary is determined by the first
infrastructure error, never by favorable or unfavorable content. Reuse the first
12 committed queries and every associated request, response, prediction, delta
and result byte-for-byte. Do not regenerate their outputs. Bind the copied
prefix and the complete interrupted source snapshot with hashes.

Continue the remaining 24 scheduled queries from that prefix state. The original
v1 suffix remains a superseded software-debugging record and is not erased or
silently merged into the repaired path. Report that this is a repaired lineage,
not an independent pristine rerun. New and reused calls must be separate counts.
Do not claim the archived v1 infrastructure errors never occurred.

## Completion and Interpretation

Complete all 36 scheduled exposures: 12 reused plus 24 continued. There is no
rule-count-based early stop. Keep the 108-call ceiling inclusive of copied calls,
90-minute continuation ceiling, shared worker lock, query-boundary pause,
immutable predictions, no ambiguous retries, stable IDs and candidate/active
separation. No paid calls, model downloads, Table 3 edits or manuscript exports.

Schema validity is not instruction adherence. Inspect whether the model actually
distinguishes the four requested opportunities; four arbitrary reflection entries
alone do not prove that it did. Same-model-admitted rules can remain source-bound
or over-detect flaws. Report these risks without manually rewriting learned text.
Detection accuracy and Credibility/Conformability remain unassessed without
adjudicated flaw ground truth.

## Additional Tests

- Compare compact and original schema acceptance on valid and invalid operations.
- Preserve full-object grammar branches and exact first-epoch requests.
- Reproduce admission for the actual previously blocked payloads offline.
- Verify prefix reuse is complete, byte-identical and stops at the first error.
- Verify copied outputs are never regenerated and new calls are counted separately.
- Run the existing full offline regression suite before continuing inference.
