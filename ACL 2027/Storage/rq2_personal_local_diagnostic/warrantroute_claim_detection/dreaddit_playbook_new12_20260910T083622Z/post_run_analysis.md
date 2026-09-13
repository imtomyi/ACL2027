# Twelve New Dreaddit Paragraphs: Outcome

This note is separate from the frozen protocol and final manifest. It does not
change any prompt, output, audit, rule, or scoring definition used in the run.

## Completed Work

- Exactly 12 new original Dreaddit paragraphs were selected before inference.
  No other corpus was run. All eight previously used paragraphs and the frozen
  evaluation panel were excluded by record, source group, and normalized text.
- Records: 518-521, 2299, 2300, 2302, 2303, and 2752-2755, with the full
  `dreaddit_train_` IDs in [data_points.md](data_points.md).
- All 12 paragraphs completed three epochs: 36 query exposures in approximately
  816.4 seconds, or 13 minutes 36 seconds.
- Local Gemma 3 4B made 36 detector calls, 36 Reflector/Curator calls, and six
  auditor calls. Zero paid calls and zero transport/schema technical errors.
- Across the preceding runs and this run, 20 distinct paragraphs have now been
  processed in 65 exposures. Different prior protocol versions and repeated
  exposures must not be pooled as independent accuracy samples.

## Playbook Outcome

The four-additional-rule target was not achieved. The Playbook remains at three
rules: two initial seeds and the previously admitted `shr-00003`.

| **Observation** | **Count** |
| --- | ---: |
| Queries with no candidate patches | 30 |
| Proposed patch occurrences | 6 |
| Distinct proposed patches before epoch repetition | 2 |
| Auditor calls | 6 |
| Rejected patches | 6 |
| Accepted new rules | 0 |
| Accepted refinements or reinforcements | 0 |

All six patch occurrences failed `reusable_not_memorized`; three also failed
`counterconditions_preserved`. The two distinct candidates concerned an uncertain
date and documentary-participant recruitment. They were not forced into memory.

[Initial](playbook_comparison/playbook_initial.txt) and
[after](playbook_comparison/playbook_after.txt) TXT files are byte-identical, and
[changes.diff](playbook_comparison/changes.diff) is empty. Existing memory was
delivered in all 36 detector requests; that is not 36 additions.

For every paragraph/role combination, all three epochs had identical request
hashes and identical parsed responses. Repetition did not create new adaptation
when neither the prompt input nor the memory state changed.

The detector alleged one established flaw on every exposure. This is not a
verified detection rate. Manual inspection raises over-detection concerns, such
as treating an explicitly uncertain date as an unsupported assertion. There is
no adjudicated flaw inventory here, and same-model audits are not independent
proof. Accuracy and Credibility/Conformability remain unassessed.

## Proposed More Active Candidate Generation

The user asked whether guideline creation can be more proactive. The following
is a next-version proposal, NOT a modification applied to this completed run:

1. Separate identifying a lesson from writing an admissible rule. For each query,
   explicitly assess opportunities for detecting a material flaw, avoiding a false
   positive, distinguishing flaw categories, or checking evidence sufficiency.
2. Keep the existing upper bound of two candidates per query, but require an
   explicit candidate-or-no-novel-lesson decision with a grounded explanation.
   Do not impose a minimum number of rules where no sound lesson exists.
3. Require observable input conditions, a concrete checking procedure, required
   evidence, and an exception condition. An output label such as
   `no_flaw_established` is not an adequate applicability condition. Avoid
   source-specific conclusions and simple copies of the general seeds.
4. Persist candidate proposals with stable candidate IDs and explicit statuses
   in a separate candidate TXT. Keep active `shr-` rules separate. A recorded
   candidate, an unvalidated reflection, or a rejected patch is not an active
   Playbook addition and must not enter the active-rule count.
5. Retain evidence, novelty, and countercondition checks for promotion. Inspect
   accepted rules and their actual later application; a fallible same-model
   approval still requires quality review before claiming detection gains.

This design makes proposal generation more explicit and diagnosable. It does
not guarantee that four valid rules exist in a small sample. Evaluate it under
a separately frozen, bounded diagnostic and preserve this run as its comparator.

## Verification

The offline suite passed 203 tests before inference. All frozen/final manifest
hashes, 36 result-chain links and artifact hashes, and 78 request/response hashes
were verified. Three ancestral runs retain their verified files. The worker and
owned Ollama server stopped; the shared lock was free after completion.

Final status: `stopped_epoch_cap`. All 36 planned exposures finished. No original
run, `AGENTS.md`, Table 3 file, or manuscript file was changed. See
[summary.md](summary.md) and [query_progress.csv](query_progress.csv) for outcomes.
