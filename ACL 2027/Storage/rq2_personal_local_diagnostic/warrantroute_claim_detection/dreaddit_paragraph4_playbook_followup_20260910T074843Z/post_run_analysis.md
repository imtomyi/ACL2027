# Follow-up Outcome and Semantic Caveats

This post-run note is separate from the frozen protocol and final export manifest.
It does not change any original response, audit, rule, or score.

## Observed Execution

- Same four original Dreaddit development paragraphs and pinned local Gemma 3 4B.
- Five additional query exposures: all four in epoch 4, then one in epoch 5.
  Together with the previous smoke run, this is 17 exposures of four paragraphs,
  not 17 independent data points. Remaining scheduled jobs were not executed.
- Inference elapsed time: approximately 124.4 seconds.
- Thirteen local calls: five detectors, five combined Reflector/Curator calls,
  and three auditors. Zero paid calls and zero transport/schema technical errors.
- One content addition was admitted at additional query 4. It received stable
  TXT ID `shr-00003`, canonical ID `learned-a247da5c3e36745f`, and revision 1.
- Query 5 received that exact new rule in its actual detector request. The run
  then stopped under the prespecified update-delivery stopping rule.
- Original seed rules remained unchanged. Initial rule count: 2. Final count: 3.

## What Changed

The new rule concerns distinguishing a genuine question expressing uncertainty
from an assertion that requires support. Its actual admitted text is retained in
[the after snapshot](playbook_comparison/playbook_after.txt), rather than replaced
with a cleaner manually written rule.

The source query was `development/dreaddit/E4/paragraph_65fc9eec620908a5`, concerning
contentment and happiness. The model auditor returned true for all six admission
criteria. The next query was
`development/dreaddit/E5/paragraph_af6643f2ccdacf9c`, concerning college-application
overwhelm. These are runtime observations, not externally adjudicated truth.

## Important Limitations

**The update and delivery path worked. Reliable rule quality and correct use were
not demonstrated.**

1. The new rule's applicability is `no_flaw_established`, an output decision
   rather than an independently observable input condition. This is circular.
2. Its countercondition still refers to a "replacement of happiness", which is
   specific to the source paragraph. Its evidence requirement, "No material
   inconsistency is present", is a conclusion rather than a concrete evidence
   check. The same-model auditor nevertheless marked it reusable.
3. In the next query, the model marked this uncertainty-protecting rule applicable
   with `flaw_supported`. Its alleged flaw was that the speaker expressed overwhelm
   without describing a plan to address it. That does not by itself establish a
   failed inference in the original paragraph. The issue's own countercondition
   also says the described situation does not establish a flaw. This raises both
   over-detection and inconsistent rule-application concerns.

The rule's delivery is supported by the actual request journal. Its reported
application is only a model self-report; it is not evidence of a causal benefit.
These observations require qualified semantic adjudication before any correctness
claim. No accuracy, precision, recall, Credibility, or Conformability is reported.

The stopping event depended on observing an accepted update, as requested by the
user. This is development debugging, not an unbiased evaluation. Both preceding
rejections and no-change outcomes are retained. Prompts and the operation-linked
schema changed in this explicitly separate version; the original smoke results
were not overwritten or merged into a claimed improvement.

## Verification and Next Gate

The offline suite passed 191 tests before inference, including 13 follow-up
tests. Frozen and final manifest hashes, all five result-chain links and their
artifact hashes, and initial-state identity with the prior final state were
verified after completion. The prior run's frozen and final files still match
their hashes. The worker finished, its owned Ollama server stopped, and the
shared execution lock was verified free.

`AGENTS.md` was not blocking this run and did not need an override. Admission
criteria were not weakened, and no rejected proposal was forced into memory.

Before a larger evaluation, a separate protocol version should require observable
input triggers instead of output-label applicability, reject case-bound conclusions
in reusable fields, and independently check whether the detector's cited rule
actually supports its decision. Preserve these artifacts as evidence of the
present limitations rather than silently repairing them.

## Files

- [Initial Playbook](playbook_comparison/playbook_initial.txt)
- [After Playbook](playbook_comparison/playbook_after.txt)
- [Exact changes](playbook_comparison/changes.diff)
- [All five query outcomes](query_progress.csv)
- [Operational summary](summary.md)

The final manifest status is `stopped_update_delivery_verified`. No manuscript
or Table 3 file was modified.
