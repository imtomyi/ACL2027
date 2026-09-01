# Frozen generation prompt (`qc-direct-v1`)

You are performing a bounded, codebook-oriented qualitative coding exercise on
an explicitly fictional evidence packet.

Analyze only the supplied packet. Do not use outside facts, remembered dataset
themes, web knowledge, demographic assumptions, diagnoses, or prevalence claims.
The output is an aid for accountable human analysis, not a final truth.

Follow these rules:

1. Answer the packet's research question at a manifest or categorical analytic
   level. A more interpretive claim is allowed only when you state a concise,
   source-linked warrant and a boundary condition.
2. Create 5–8 distinct local codes. A code must have a concise label, definition,
   inclusion rule, exclusion rule, analytic level, and at least one exact exemplar.
3. Assign every excerpt either one or more defined codes or `not_coded`. Give a
   short rationale grounded in that excerpt.
4. Construct 2–4 themes. Each theme must have a bounded claim, explanation,
   linked code IDs, exact supporting evidence, counterevidence, boundary
   conditions, and the distinct source IDs represented.
5. Preserve disagreement, minority or negative cases, temporal change,
   resolution, and interactional context. Do not turn an interactional pattern
   into a stable trait of a person or group.
6. Quote only exact contiguous text from the cited excerpt. Never repair grammar,
   splice passages, or present a paraphrase as a quotation.
7. Do not write “most,” “typical,” “generally,” or population-level equivalents
   unless the supplied packet itself supports the wording and you state its exact
   coverage. Prefer bounded language such as “in these excerpts.”
8. State uncertainty and plausible alternative interpretations. Abstention is
   better than an unsupported claim.
9. Return only JSON conforming to `qualitative_output.schema.json`. Do not add
   Markdown fences or commentary.

