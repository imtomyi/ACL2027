# Qwen3 fixed-role component contract v1

## Purpose and boundary

This component implements the source-free engineering boundary for the
WarrantRoute fixed-role baseline with Qwen3 8B as the primary LLM reviewer. It
does not authorize a real-data run and does not produce manuscript evidence.
The historical v1 runner and every v2 qualification freeze remain immutable.

The component consumes already sealed evaluator items. It never constructs,
edits, selects, or verifies candidate interpretations. Candidate generation and
review use distinct actor and run records. A future authorized freeze must state
whether the same model family may occupy both records and must preserve that
decision prospectively.

## Reviewer roles

The same exact Qwen3 snapshot receives three role prompts:

1. `researcher`: a researcher without specialist expertise;
2. `qualitative_methods`: a qualitative-methods expert; and
3. `domain`: a domain expert.

Each item is reviewed in three independent, stateless repetitions. Repetition 1
is primary. Repetitions 2 and 3 support stability analyses only and never alter
the fixed-role choice or enlarge the denominator. Tools, browsing, retrieval,
memory, model thinking, input truncation, and context shifting are disabled.
There is no fallback model, semantic retry, replacement item, or cherry-picking.

## Fixed-role selection

Selection uses only a prospectively frozen, error-family-balanced Dreaddit
official-training development projection. The projection contains no source
text. It references sealed evaluator items and full reviewer observations by
SHA-256 and retains only the fields needed to score detection.

For each role, micro recall is calculated from repetition 1 across every
eligible development item. A hit requires a valid observation, an empty
`cannot_judge` array, and the target error flag. Invalid output, filtering,
timeout, terminal failure, a missing observation, `cannot_judge`, and a wrong or
missing target flag remain in the denominator as misses.

The role with the greatest true-positive count is selected because all roles
share the same denominator. Exact ties resolve in this order:

1. `researcher`;
2. `qualitative_methods`;
3. `domain`.

Selection fails closed when the development set is empty, a family is absent,
family counts are unequal, the frozen minimum item or cluster count is not met,
an item or observation is duplicated, the actor/model/item hash drifts, the
qualification gate is not passed, or held-out data were accessed. It never
selects a role from all-null recall.

The selection record and its hash seal must be written before Dreaddit test or
CaChe is opened for this analysis. The selected role is then applied unchanged
to every held-out item. It is not reselected from held-out outcomes, repetitions
2 or 3, a bootstrap sample, cost, latency, confidence, or ordinal ratings.

## Current commands

`dry-run` validates the component freeze, exact Qwen identity, role prompts,
schemas, shared guide, decoding, and source-free boundary without contacting a
model service or opening `dataset/` or `Storage/`.

`preflight-service` checks only the numeric-loopback Ollama version and exact
Qwen3 tag and digest.

`source-free-test` sends one inert in-memory interface canary through each role
prompt. It writes nothing and is not a dataset, experimental observation, or
manuscript result.

`run` is intentionally blocked. Real execution requires a separate approved
study freeze that binds a passed qualification seal, authorized packet bank,
privacy and provider approvals, exact sample size and cluster minima, candidate
generator, Qwen reviewer actors, prompts, schemas, failure rules, output root,
analysis code, and a clean pre-held-out access record.
