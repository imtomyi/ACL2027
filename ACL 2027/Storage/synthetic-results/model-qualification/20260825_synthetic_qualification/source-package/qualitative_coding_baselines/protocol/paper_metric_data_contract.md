# Paper metric data contract (`qc-paper-metrics-v1`)

This contract governs the four artifact-quality measures named in the ACL
manuscript. It supersedes the synthetic-qualification judge fields for paper
reporting; it does not rewrite or reinterpret the historical qualification run.

## Units and measures

The rated unit is a complete theme-and-evidence packet. Qualified raters record
three independent ordinal judgments using the manuscript anchors:

1. **Evidential credibility** (`evidential_credibility`): whether every material
   part of the interpretation is directly warranted by sufficient cited evidence
   in local context.
2. **Voice-and-boundary preservation** (`voice_boundary_preservation`): whether
   consequential differences, dissent, counterevidence, minority or boundary
   cases, and contextual qualifications survive synthesis.
3. **Scope calibration** (`scope_calibration`): whether breadth, strength,
   polarity, causal language, and participant/group/corpus scope are proportionate
   to the supplied evidence.

Each field is 1--5 or null. A null is valid only when the corresponding metric is
listed in `cannot_judge`. Adequacy is calculated separately for each measure as
the proportion of evaluable rater--packet judgments scored 4 or 5. `Cannot
judge` is reported separately and never converted to a midpoint or failure.

**Plural-reference coverage** is not a packet rating. For each complete natural
output inventory and level (code or theme), independently constructed reference
concepts are matched many-to-many to generated concepts. Coverage is the
proportion of frozen reference concepts with at least one accepted generated
match. Code and theme coverage are always reported separately.

## Integrity prerequisite

Before quality ratings are interpreted, report a deterministic integrity gate:

- schema and assignment completeness;
- exact quotation or valid source offsets;
- correct source/speaker attribution;
- valid code-to-evidence and theme-to-code references; and
- cross-source evidence for claims presented as cross-source themes.

Integrity is a prerequisite, not a fifth quality score. Report pass counts and
failure reasons. Do not let a high mean human rating conceal provenance failure.

## Coverage safeguards

Coverage is recall-like and can be increased by producing many concepts. Report
alongside it:

- generated code and theme counts;
- unmatched generated concepts and the human-audited unsupported-concept rate;
- split, merge, and redundant-concept counts; and
- source concentration and repeat stability as diagnostics.

Do not convert unmatched generated concepts into errors automatically. Experts
must distinguish defensible novelty from unsupported or redundant generation.

## Required separation

- Build and freeze separate `P_code` and `P_theme` pools from multiple independent
  analysts before test outputs are inspected.
- Keep pool construction, model-output generation, conceptual matching, packet
  rating, and final adjudication separate wherever staffing permits.
- Use Dreaddit development data for model and prompt selection only. Freeze all
  choices before Dreaddit audit or CaCHe/AGYW evaluation.
- Never pool synthetic qualification results with real-corpus results.
- Never combine the four measures into an omnibus score.

## Main results table

Use one row per system and evaluation role. The minimum columns are:

| Corpus / role | System | Complete inventories | Rated packets | Integrity pass n/N | Evidential adequacy % [95% CI] | Voice/boundary adequacy % [95% CI] | Scope adequacy % [95% CI] | Code coverage % [95% CI] | Theme coverage % [95% CI] | Cannot judge % | Serious-error rate % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

The caption must state the evaluable denominator, clustering unit, interval
method, evaluator roles, and whether the row is development, audit, or
confirmatory. Reliability, calibration, output volume, overgeneration,
codebook usability, parsimony, and stability belong in companion tables.

