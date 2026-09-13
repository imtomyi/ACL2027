# TA Playbook Continuation: Outcome and Limitations

Post-run inspection outside the frozen result manifest. The first-response
outputs, requests, prompts, state transitions and admission decisions are
unchanged. This note is not a gold key or evaluator feedback.

## What Ran

- Three existing locked TA artifacts, generated from twelve original Dreaddit
  paragraphs, reviewed over three fixed-order development epochs.
- Nine detector calls and nine merged Reflector/Curator calls.
- Eighteen local Gemma 3 4B calls, approximately 223.44 seconds of summed request
  wall time. This excludes implementation, tests and inspection.
- No paid calls, generation retries, baseline runs, quality judgments or repairs.
- Zero transport/schema technical failures. This does not mean semantically
  correct output or successful memory learning.

## What Happened to the Playbook

| Measure | Result |
| --- | ---: |
| Initial seed rules | 2 |
| Candidate occurrences | 10 |
| Distinct candidate content hashes | 6 |
| Candidates withheld before semantic audit | 10 |
| Semantic auditor calls | 0 |
| New admitted rule IDs | 0 |
| Final active rules | 2 |
| New rules delivered to a later query | 0 |

The [initial TXT](playbook_comparison/playbook_initial.txt) and
[after TXT](playbook_comparison/playbook_after.txt) are byte-identical.
The [candidate register](candidates/current.txt) contains proposals, NOT active
learned rules. Ten proposals or six text hashes do not establish ten or six
distinct useful procedures.

Seven candidate occurrences selected add while specifying an existing target
rule ID. Adding a new rule requires an empty target; these were withheld with
add_target_not_empty. Three further occurrences supplied an artifact anchor
whose field/quotation did not match the named code. Some occurrences contain
more than one invalid anchor; the three count is of candidates, not spans.
Receipts report the first relevant rejection stage, not an exhaustive inventory
of all candidate problems.

The auditor was skipped because no candidate passed deterministic eligibility.
The audit path has source-free unit coverage but was not exercised by a live
model call in this run. It would be inaccurate to report nine successful audits,
new automatic rules, or improved detection.

## Review Limitations

All nine reviews returned no_flaw_established with zero allegations. Twelve
rule-check integrity flags were recorded across the repeated reviews. Those
reviews included issue-index references despite an empty issue list.
This is not evidence that the artifacts are clean: the generation-stage
inspection identified quotation, attribution and interpretation concerns.
Those assistant notes were deliberately NOT passed to the models.

The repeated unchanged Playbook and fixed artifacts make these development
exposures dependent. There is no qualified complete flaw inventory, so no TP,
recall, accuracy or Credibility/Conformability percentage is calculated.

## Follow-Up Engineering Questions

The current interface does not elicit reliable learning proposals from Gemma in
this setting. In addition to the counted failures, examples use the literal text
true as an applicability condition, terse labels instead of actionable checks,
or repeat seed wording. Fixing target IDs alone would not validate such rules.

A separately versioned development amendment should test:

1. Operation-specific wire schemas that distinguish adding a new rule from
   refining/reinforcing an existing one, without silently correcting a response.
2. Explicit field definitions and source-free structural examples in the prompt,
   including that applicability is an observable textual condition, not a vote.
3. Unit/field-compatible artifact anchors and separate source-anchor validation.
4. Reviewer handling of source roles, code/theme scope and contradictory rule
   checks, using approved calibration inputs rather than a forced-positive rule.
5. A live audit-path smoke test when a genuinely eligible proposal is available.

These are proposed future checks, not changes applied midway through this run.
No admission criterion was lowered and no rejected candidate was manually added.

## Verification

The combined test suite passed 234 source-free tests before launch. Post-run
verification checked all nine hash-linked results, immutable artifact bindings,
the exact seed TXT delivered to each detector, final memory, source manifests
and final output hashes. The test-owned Ollama server and worker exited.
The original TA generation reports, paused paragraph experiment, five-rule
automatic paragraph Playbook and manual eight-rule draft were not changed.

[Summary](summary.md) | [Query Progress CSV](query_progress.csv) |
[Candidate Register](candidates/current.txt) | [Final Manifest](final_manifest.json)
