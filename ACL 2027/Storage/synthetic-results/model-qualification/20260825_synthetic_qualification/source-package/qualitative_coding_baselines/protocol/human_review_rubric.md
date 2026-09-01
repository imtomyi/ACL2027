# Blinded human review rubric (`qc-human-rubric-v1`)

> **Scope note:** this is the broader synthetic-qualification rubric retained for
> audit compatibility. It does not collect the ACL manuscript's three ordinal
> measures exactly: voice and negative cases are split, and scope calibration is
> absent. Use `paper_metric_data_contract.md` and
> `paper_metric_rating.schema.json` for paper data collection.

Reviewers see the source packet and anonymized outputs in randomized left/right
order. They do not see model names, cost, latency, automatic aggregate scores, or
another reviewer's judgment. At least two relevant reviewers should rate each
comparison independently before adjudication.

## Pairwise choice

Choose exactly one:

- A preferred
- B preferred
- both adequate
- neither adequate
- cannot judge

Then rate each output independently from 1 (poor) to 5 (excellent):

1. **Evidential support** — claims are warranted by the cited excerpts.
2. **Quote and attribution fidelity** — quotations and source links are correct.
3. **Voice and context preservation** — wording retains consequential differences,
   interaction, and speaker position.
4. **Negative-case preservation** — contradictions, exceptions, and change are
   visible and affect the interpretation.
5. **Analytic-contract fit** — codes and themes stay within the declared bounded,
   codebook-oriented task.
6. **Codebook usability** — code definitions and boundaries are distinct enough
   for another analyst to apply.
7. **Interpretive usefulness** — themes organize meaning beyond topic labels while
   remaining checkable.
8. **Parsimony** — the output is no more complex or repetitive than necessary.
9. **Confidence in judgment** — reviewer confidence, not output quality.

## Disposition

For each output choose: `accept`, `revise`, `reject`, or `escalate`. Record the
kind of expertise requested and a concise rationale.

## Serious-error flags

Mark every applicable flag and cite the exact location:

- fabricated or altered quotation;
- wrong source or speaker attribution;
- unsupported evidence-to-claim inference;
- source concentration hidden by broad wording;
- lost negative or contradictory case;
- contextual flattening;
- unsupported abstraction or population generalization;
- sensitive or diagnostic inference not warranted by the packet;
- unusable or internally inconsistent codebook; or
- other (explain).

Defensible interpretive disagreement is not automatically an error. Preserve it
in the rationale rather than forcing consensus.
