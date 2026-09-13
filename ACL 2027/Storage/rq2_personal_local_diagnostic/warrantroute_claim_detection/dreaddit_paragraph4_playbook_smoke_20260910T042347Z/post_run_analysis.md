# Four-Paragraph Smoke Test: Observed Outcome

This is a post-run diagnostic note, separate from the frozen experiment and its
final export manifest. No frozen input, prompt, implementation, prediction,
learning decision, or final result was changed to produce this note.

## Execution

- The user authorized stopping the previous suspended experiment. Only its two
  verified suspended processes were terminated. All 6,059 checked prior files
  retained their original hashes. See `prior_process_shutdown.json`.
- Local Gemma 3 4B processed four original Dreaddit development paragraphs over
  three epochs: 12 query exposures, not 12 independent paragraphs.
- The run completed all 12 detector calls and 12 Reflector/Curator calls in about
  four minutes and 24 seconds after the inference clock started.
- There were zero transport/schema technical failures and zero paid API calls.
- No audit call was reached because no proposed patch passed the mechanical
  admission checks. The model's lack of instruction compliance is not counted
  as a transport/schema error.
- The old processes and the temporary run's owned Ollama server are no longer
  running. The shared experiment lock was verified free after completion.

## Playbook Outcome

**The live run did not demonstrate a successful learned-rule update chain.**

All 12 actual detector request journals contained the expected paragraph-native
prompt and the exact retrieved Playbook TXT recorded with their predictions.
This verifies delivery of the existing memory, not the adoption or benefit of a
new rule. The current Playbook remains revision zero with only `shr-00001` and
`shr-00002`. Each query's completed-result binding was published, but no new
content revision was admitted.

| Observation | Count |
| --- | ---: |
| Completed query exposures | 12 |
| Valid detector request TXT bindings | 12 |
| Queries proposing two deltas | 9 |
| Queries proposing no delta | 3 |
| Proposed deltas | 18 |
| Proposed additions | 0 |
| Proposed refinements of immutable seeds | 18 |
| Accepted additions or refinements | 0 |
| Later prompt inclusions of learned rules | 0 |

Twelve deltas were rejected with `seed_or_missing_rule_refinement`. Six were
rejected earlier with `rule_text_budget`: their required `countercondition`
field was empty. The latter error name combines missing-field and length-budget
validation; it does not establish that those six proposals were too long. All
18 also targeted immutable seeds.

The prompt explicitly prohibits seed refinement, but the current learning wire
schema permits every operation together with seed target IDs. The validator
correctly protects the initial rules; the generated operation/target combinations
are unusable. With unchanged memory and deterministic decoding, repeating these
paragraphs over epochs did not establish adaptation.

## Detection Interpretation

Every exposure returned one alleged established flaw. This is a model output,
not a 100% detection accuracy result. There is no adjudicated flaw inventory for
these four paragraph-native inputs, so detection accuracy, Credibility, and
Conformability remain unassessed.

Manual inspection raises an over-detection concern. For example, the first
query calls the explicit report "Her parents supported her" contextual
flattening because parental reaction is allegedly absent. This appears to demand
external corroboration for an ordinary reported fact, despite the paragraph
prompt warning against that inference. This concern requires adjudication;
schema validity alone does not resolve it.

## Changes Needed Before a New Version

1. Restrict operations and targets together in the generated-output schema.
   When only seeds exist, allow valid additions, reinforcement, or no change;
   do not offer seed refinement. Keep the immutable-seed validator.
2. Enforce nonempty reusable fields for additions/refinements in the wire schema
   and distinguish missing-field errors from length-limit errors.
3. Strengthen and test the paragraph-native distinction between reported facts,
   subjective concerns, and actual material inferential flaws. Never convert
   an unsupported allegation into a memory rule just to obtain an update.
4. Test the add, audit, stable-ID publication, next-query retrieval, and refinement
   paths before freezing a separate live version. A no-change decision remains
   legitimate when no grounded lesson is available.

These are proposed next-version changes, not changes applied to this run. No
rejected patch was forced into memory and no unfavorable response was redrawn.

## Artifacts and Verification

- `summary.md`: compact operational summary.
- `query_progress.csv`: all 12 exposures and their update outcomes.
- `playbooks/dreaddit/current.txt`: actual current Playbook.
- `deltas/development/dreaddit/`: original proposals and rejection receipts.
- `calls/development/dreaddit/`: immutable local request/response journals.
- `final_manifest.json`: `completed_without_demonstrated_update_chain`.

All files listed in the frozen manifest and final manifest passed SHA-256
verification after completion. Historical Table 3 files and manuscript files
were not changed. This small development test does not establish detection
quality, performance improvement, or manuscript eligibility.
