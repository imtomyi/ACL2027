# Bounded Dreaddit Playbook Follow-up

## Purpose and Scope

This private development diagnostic follows the completed four-paragraph smoke
test. The user requested a little more execution until an update is accepted.
It tests whether an evidence-grounded content delta can pass the existing audit,
receive a stable TXT ID, and reach a later detector query. It is not a performance
experiment and must not fill Table 3 or any manuscript result.

The same four original Dreaddit development paragraphs, original texts, pinned
local Gemma 3 4B model, and decoding options are retained. One paragraph remains
one data point. There is no new held-out-data access. The prior terminal seed
state is copied as the initial state, with its IDs unchanged. Previous outputs
are preserved, not rewritten or included as new successful results.

## Separate Version

Protocol: `dreaddit-paragraph-playbook-followup-v1`.

The completed smoke run could not produce accepted additions: all 18 proposed
refinements targeted immutable seeds. Its output schema allowed operations that
the prompt and admission checks prohibited. This new version freezes:

1. Operation-dependent generated-output branches: add targets an empty ID,
   refine targets only existing non-seed rules, and reinforce targets an existing
   rule without changing its text. No-change output is still permitted.
2. Nonempty reusable fields and novelty conditions for add/refine. The existing
   total length bound, evidence validation, and all six audit criteria remain.
3. Clearer paragraph-native instructions distinguishing reported experiences,
   questions, assertions, and actual failed inferences. The Reflector/Curator
   can identify an overcall in the locked diagnosis without changing it.

Prompts and the wire schema therefore differ from the original test. Do not call
this an unchanged continuation or pool the two versions as an unbiased estimate.
The new version does not lower admission requirements, force an addition, treat
seed reinforcement as learned content, or retry an unfavorable output.

The request uses Ollama's JSON schema `format` field, with the same schema in
the prompt and local response validation. API references checked before use:
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and
[generate endpoint](https://docs.ollama.com/api/generate).

## Sequence and Stop Rules

```text
Original paragraph + current TXT
  -> detector: lock diagnosis and rule checks
  -> combined Reflector/Curator: propose bounded deltas or no change
  -> mechanical eligibility validation
  -> same-model auditor, only if eligible deltas exist
  -> unchanged six-criterion admission
  -> persist result, JSON state, TXT, stable IDs, immutable revision history
  -> next original paragraph receives the newly published memory
```

- At most three additional epochs, numbered 4-6, of the same four paragraphs:
  12 additional exposures, not 12 independent data points.
- Stop after an accepted add/refine appears in a later valid detector request,
  with actual request-to-TXT bindings verified. A newly stored rule alone is not
  sufficient to demonstrate the full update/use path.
- Stop at 12 additional queries, 36 local model calls, or a 600-second inference
  budget, whichever occurs first. Every call retains the inherited 180-second
  timeout and 181-second remaining-budget admission reserve.
- Honor a query-boundary pause request. Fail closed on contract/hash errors or
  ambiguous calls. Do not redraw the same job after a technical or unfavorable
  response. Preserve partial outputs if the time budget closes mid-query.
- Use the shared experiment lock; never start a duplicate worker. Reuse an
  existing local Ollama server or clean up only the server owned by this run.
- No paid API calls, model downloads, or changes to frozen previous runs.

## Reporting

Report every completed query, including no-change and failed outcomes, and the
total number of attempts before the stopping event. Keep initial and after TXT
files, a unified diff, per-query outcomes, source hashes, request/response journals,
and a final manifest. An empty diff honestly represents no content update.

This outcome-dependent stop is suitable only for pipeline debugging. An accepted
delta is a fallible same-model admission, not independent semantic validation.
There is no adjudicated flaw inventory for these inputs: accuracy, precision,
recall, Credibility, and Conformability remain unassessed. Do not infer a detection
gain from growing memory, a rule application, or successful JSON generation.

Offline fixtures used to test the control path remain under temporary Storage
directories and must never be reported as live experiment results.
