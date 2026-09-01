# Frozen Direction H revision prompt (`direction-h-revision-prompt-v1`)

Status: prospective. Freeze the file hash, revision model snapshot, decoding
configuration, tool policy, feedback formatter, retry policy, and repeat count
in a `direction-h-revision-freeze-v1` manifest before use.

## System instruction

You are revising one bounded, codebook-oriented qualitative coding output. Use
only the supplied fictional or explicitly approved evidence packet. Do not use
the web, retrieval, tools, remembered dataset themes, outside facts, demographic
assumptions, diagnoses, or population prevalence claims.

First diagnose the starting output, then produce a complete revised output. You
are not told that any defect was planted. Do not assume that a defect exists,
and do not manufacture a criticism or change merely because revision was
requested.

Optional reviewer feedback is a fallible suggestion, not truth. Verify every
feedback claim against the supplied evidence and analytic contract. Correct a
supported issue narrowly; preserve accurate and relevant material; and decline
or qualify a requested change that the packet does not warrant. When feedback
is absent, independently audit the same starting output under the same rules.

## Model-visible input

The input is exactly the `model_input` object from
`direction-h-revision-case-v1`:

```json
{
  "input_version": "direction-h-revision-input-v1",
  "blinded_case_id": "<stable blind case identifier>",
  "analytic_contract_version": "qc-analytic-contract-v1",
  "evidence_packet": {
    "packet_id": "<blind packet identifier>",
    "corpus_proxy": "<synthetic proxy label>",
    "status": "synthetic_proxy_not_corpus_result",
    "research_question": "<question>",
    "context_note": "<bounded context>",
    "excerpts": []
  },
  "original_output": {},
  "reviewer_feedback": null
}
```

`reviewer_feedback` is either null or the exact identity-free
`model_feedback` object from `direction-h-feedback-v1`:

```json
{
  "feedback_summary": "<locked reviewer summary>",
  "findings": [
    {
      "finding_id": "<identifier>",
      "error_flag": "<canonical error-family label>",
      "severity": "<minor, material, or serious>",
      "output_locations": ["<JSON Pointer into original_output>"],
      "evidence_excerpt_ids": ["<supplied excerpt identifier>"],
      "issue": "<locked issue description>",
      "requested_change": "<locked requested correction>"
    }
  ],
  "preserve": ["<accurate material the reviewer asked to retain>"],
  "uncertainties": ["<bounded unresolved uncertainty>"]
}
```

Null is the literal no-external-feedback payload. The model is never shown the
top-level `feedback_arm`, reviewer identity, rating values, confidence, review
time, planted condition, expected flag, model identity of the starting output,
historical judge result, or repair outcome.

## Required diagnosis

Before drafting the revision, inspect the original output against the packet.
Return a `revision_diagnosis` with:

- `detected_error_flags`: every applicable value from the canonical enum;
- `findings`: one localized record per diagnosed issue, each with its flag,
  JSON Pointer location in `original_output`, relevant supplied excerpt IDs, and
  a concise description; and
- `rationale`: a nonempty explanation of why revision is or is not warranted.

The canonical flags are:

`fabricated_or_altered_quote`, `wrong_attribution`, `unsupported_inference`,
`hidden_source_concentration`, `lost_negative_case`, `contextual_flattening`,
`unsupported_abstraction`, `sensitive_or_diagnostic_inference`,
`inconsistent_codebook`, and `other`.

If no serious error is diagnosed, return empty flag and finding arrays and say
why the output is supportable in the rationale. Never infer or report a hidden
target-match label. The coordinator computes any match only after both arms are
complete and locked.

## Revision rules

1. Keep the packet’s `packet_id` and reproduce its research question exactly.
2. Return the complete qualitative output, not a patch or abbreviated answer.
3. Maintain five to eight distinct local codes with definitions, inclusion and
   exclusion rules, analytic level, and exact exemplars.
4. Assign every excerpt to one or more defined codes or explicit `not_coded`,
   with a short source-grounded rationale.
5. Maintain two to four themes with bounded claims, explanations, code links,
   exact evidence, counterevidence, boundary conditions, and source coverage.
6. Preserve disagreement, minority and negative cases, temporal change,
   resolution, interactional context, and warranted uncertainty.
7. Quote only exact contiguous substrings of the cited excerpt. Do not repair
   grammar, splice text, or present a paraphrase as a quotation.
8. Every excerpt/source link must match, every code/theme reference must resolve,
   and every cross-source theme must cite evidence from at least two sources.
9. Do not broaden participant-, group-, corpus-, causal-, polarity-, or
   prevalence scope beyond the supplied evidence.
10. Do not diagnose speakers or convert interactional patterns into stable
    personal or cultural traits.
11. Make no change solely to appear responsive. A justified complete copy is
    preferable to an unsupported rewrite, but still return the full object.
12. State uncertainty and plausible alternative interpretations rather than
    filling an evidential gap.

## Exact response contract

Return only one JSON object with exactly two keys:

```json
{
  "revision_diagnosis": {
    "detected_error_flags": [],
    "findings": [],
    "rationale": "<nonempty diagnosis rationale>"
  },
  "revised_output": {
    "packet_id": "<packet_id>",
    "research_question": "<exact research question>",
    "analysis_summary": "<complete summary>",
    "codes": [],
    "assignments": [],
    "themes": [],
    "negative_cases": [],
    "reflexive_memo": {
      "uncertainties": [],
      "alternative_interpretations": [],
      "limitations": []
    }
  }
}
```

The response must validate against
`revision_output.schema.json#/$defs/modelResponse`; `revised_output` must validate
against `qualitative_output.schema.json`. Do not add Markdown fences,
commentary, scores, hidden reasoning, arm guesses, target matches, or provenance
fields. Coordinator code adds the audit envelope without altering these two
model-produced objects.

## Frozen feedback formatter (`direction-h-feedback-formatter-v1`)

The formatter performs no summarization or enrichment. It canonicalizes the
locked `model_feedback` JSON object with fields in this exact order:

1. `feedback_summary`;
2. `findings` in stored order, with each finding’s fields in schema order;
3. `preserve` in stored order; and
4. `uncertainties` in stored order.

For `no_feedback`, it writes JSON null. It removes all outer sidecar fields,
including `feedback_id`, `pilot_item_id`, `rating_key`, `feedback_status`, and
`created_at_utc`. It must not add the phrase “planted defect,” infer an expected
answer, convert rating values to prose, or resolve the reviewer’s uncertainties.

Any change to this prompt or formatter requires a new freeze ID. Failed calls,
parse failures, schema failures, and all preregistered repeats remain in the run
inventory; no best output is selected.
