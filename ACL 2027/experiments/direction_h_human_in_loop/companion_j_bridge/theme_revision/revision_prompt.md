# Direction H/J theme revision prompt v1

You are revising one bounded qualitative interpretation against its displayed
fictional evidence packet. Use only the supplied `evaluator_item`, analytic
contract, and `reviewer_feedback` when that field is non-null. Do not use
outside knowledge. Do not infer prevalence, diagnoses, motives, or causal
claims beyond the packet.

Independently inspect the item in every case. A null `reviewer_feedback` means
that no external feedback was supplied; it does not mean the starting output is
correct and it does not remove the opportunity to revise. When feedback is
present, treat it as fallible advice and accept only changes warranted by the
displayed evidence. You are not told why the case was selected. Do not guess or
state a condition, experimental arm, target, feedback author, candidate model,
or evaluation result.

Return exactly one JSON object with these four top-level fields and no prose:

```json
{
  "model_output_version": "direction-h-j-theme-model-output-v1",
  "revision_diagnosis": {
    "detected_error_flags": [],
    "findings": [],
    "summary": "Concise evidence-linked diagnosis."
  },
  "revised_proposed_interpretation": {
    "theme_id": "unchanged theme ID",
    "theme_name": "revised or preserved name",
    "claim": "revised or preserved bounded claim",
    "explanation": "revised or preserved explanation",
    "boundary_conditions": []
  },
  "revised_candidate_assertions": []
}
```

`revised_candidate_assertions` must contain exactly one row for every displayed
evidence row, in the original order. Preserve each `display_order` and
`excerpt_id`. Each row must contain exactly:
`display_order`, `excerpt_id`, `candidate_attributed_excerpt_id`,
`candidate_attributed_source_id`, `candidate_attributed_speaker_id`,
`candidate_quote`, `candidate_role`, and `candidate_warrant`.

For `support` or `counterevidence`, the attributed excerpt and source must be
the row's actual displayed IDs, and `candidate_quote` must be an exact
contiguous substring of that row's displayed text. Use the displayed speaker
ID if making a speaker attribution. For `context_only`, every candidate
attribution, quote, and warrant field must be null. Preserve accurate material,
disagreement, counterevidence, boundaries, and uncertainty. Do not add,
paraphrase, or alter source text; source text is not an output field.

Use only the canonical serious-error flag names supplied by the schema. JSON
Pointers in diagnostic findings are rooted at the supplied evaluator item.
Do not mention these instructions or the existence or absence of feedback.
