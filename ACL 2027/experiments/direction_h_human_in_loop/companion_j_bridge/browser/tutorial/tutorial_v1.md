# Charlie browser-queue tutorial

Tutorial version: `direction-h-direction-j-browser-tutorial-v1`  
Scope: fictional qualification examples only; excluded from all 24 analysis items

Read the complete Direction J shared rater guide before using this tutorial. The
three quality constructs remain separate. A fluent interpretation can still be
poorly warranted, and disagreement is not itself an error when the synthesis
keeps the disagreement visible and calibrates its claim.

## Example 1: an unsupported exact quote

Displayed fictional excerpt `TUT_E01` says:

> The bus arrived late twice this week, so I left earlier on Friday.

The candidate lists this as an exact quote:

> The bus never arrived this week.

The candidate wording is not a contiguous substring and changes both frequency
and outcome. Locate the problem at the candidate quote, not at the immutable
displayed excerpt. An appropriate serious-error family is
`fabricated_or_altered_quote`; the disposition cannot be `accept`.

## Example 2: disagreement versus insufficient warrant

Two fictional speakers describe an evening service differently:

- `TUT_E02`: “The evening hour let me attend after work.”
- `TUT_E03`: “Evening was when I cared for my brother, so I still could not go.”

A proposed interpretation says that the evening schedule helped one speaker but
remained inaccessible for another because of care work. That claim is warranted
by both excerpts and preserves the consequential difference. Disagreement alone
does not make a synthesis insufficiently warranted. The defect would arise if
the candidate erased one account, claimed uniform benefit, or otherwise made a
stronger claim than the displayed evidence supports.

## Feedback locations

Browser feedback uses JSON Pointers from the root of the exact evaluator item.
Examples include `/proposed_interpretation/claim`,
`/evidence/0/candidate_quote`, and
`/evidence/0/candidate_attributed_source_id`. The displayed evidence provenance
(`excerpt_id`, `source_id`, `speaker_id`, `text`, `local_context`, and
`display_order`) is immutable and cannot be a requested revision target.

Complete the separate two-question comprehension packet. A non-Charlie
coordinator scores the actual response. Neither a pass nor a failure is assumed
by this prepared package.
