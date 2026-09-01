# Qwen3 All roles component contract v1

## Purpose and boundary

This component implements the source-free engineering boundary for the
WarrantRoute All roles reference with Qwen3 8B as the designated LLM reviewer.
All roles is descriptive. It is not the confirmatory comparison, a router, a
fixed-role selector, or a fourth reviewer role.

The source-free component accepts only projections marked as software fixtures
with no real observations. Any qualification, eligibility, truth, or review
matrix hashes carried by a fixture are labeled as unverified external study
references. This component checks their syntax and binds them into its local
record, but it does not authenticate them or convert them into authorization.
The future study component will consume sealed
evaluator items and sealed observations from the same review matrix used by the
other RQ2 methods. It will not construct or edit candidate interpretations.
Candidate generation and review require distinct actor and run records. A
future authorized study freeze must bind both records before any source-bearing
execution.

## Review matrix

The same exact Qwen3 snapshot receives three prompts:

1. `researcher`, for a researcher without specialist expertise
2. `qualitative_methods`, for a qualitative methods expert
3. `domain`, for a domain expert

Each eligible item has three independent and stateless repetitions under every
role. This yields nine observations per item. There is no All roles prompt and
no All roles actor. The source-free derived record links the nine local fixture
observation commitments and does not make additional model calls. A future
authorized component must separately bind and verify upstream sealed
observation identifiers.

The lane object uses the same `corpus`, `source_split`, `internal_lane`,
`experimental_role`, and `heldout` fields as the WarrantRoute routing
components. This permits one canonical observation projection to be reused
without a lane-name adapter.

Tools, browsing, retrieval, memory, model thinking, input truncation, and
context shifting are disabled. There is no fallback model, semantic retry,
replacement item, or cherry-picking.

## Primary All roles rule

Repetition 1 is primary. For each role, usable flags come only from a
schema-valid observation with an empty `cannot_judge` array. Every other status,
including invalid output, filtering, timeout, truncation, terminal failure,
abstention, and an explicit missing observation, contributes an empty flag set.

The primary All roles flag set is the union of the three roles' usable
repetition 1 flags. The item is a hit when this union contains its prespecified
required flag. This is an OR across roles. It is not an AND, majority vote,
pooled call count, or tie-breaking procedure. Two or three roles finding the
same target still contribute one true positive for the item. The denominator is
the number of eligible items, not the number of roles or calls.

All roles is distinct from a WarrantRoute route to `both`. The `both` route
unions only the qualitative methods and domain outputs. All roles also includes
the researcher output.

## Stability sensitivity

Repetitions 2 and 3 never change the primary result or enlarge the denominator.
For the descriptive stability sensitivity, a flag is retained within a role
only when at least two of that role's three repetitions contain the flag. The
three role-level retained flag sets are then unioned. Hits split across roles do
not combine to meet the two-of-three threshold.

## Uncertainty

Overall primary and stability recall use 10,000 percentile bootstrap resamples
over the frozen source clusters with seed `20270826`. The minimum is five
independent clusters. When there are fewer clusters or the bootstrap
distribution is degenerate, the result retains TP, FN, N, and recall and marks
the interval as not estimable. Repetitions and roles always travel with their
source cluster and never become resampling units.

## Validation and derived records

Structurally absent roles or repetitions make the input invalid. An explicit
failure or missing-observation slot is complete accounting and counts as an
empty flag set. The reducer rejects empty inputs, duplicate item identifiers,
duplicate evaluator-item hashes, duplicate observation hashes, unexpected role
or repetition ordering, actor or model drift, evaluator-item hash drift, an
incorrect error-family-to-flag mapping, a failed qualification gate, and schema
drift. In the current source-free schema, the qualification value is only a
fixture assumption and does not establish a real passed gate.

Every fixture observation has a domain-separated SHA-256 commitment over its
complete projected record plus its enclosing item and role. The component
recomputes every commitment before reduction. It also computes a local fixture
matrix commitment over the reviewer identity, item truths, and the ordered nine
observation commitments. These are reproducibility checks for the software
fixture. They are not signatures and do not verify the external study
references.

The derived record reports one row per eligible item, role-level hit indicators,
the primary and stability unions, TP, FN, N, and recall. It contains no source
text. Before sealing, the component reloads the tracked default freeze,
re-derives the complete result from the immutable validated fixture snapshot,
and requires byte-for-byte equality. The seal binds the exact input, local
fixture matrix, result, unverified external references, component freeze, lane,
and item count. A caller cannot supply the freeze hash. The record remains a
diagnostic integrity record and is not manuscript evidence under this
source-free component freeze.

## Current commands

`dry-run` validates the component freeze and builds the nine-request plan from
an inert in-memory interface canary. It does not contact a model service or open
`dataset/` or `Storage/`.

`preflight-service` checks only the numeric-loopback Ollama version and the
exact Qwen3 tag and digest.

`source-free-test` sends the inert interface canary once through each role
prompt. It writes nothing and produces no research result.

`run` is intentionally blocked. The current qualification gates failed and do
not authorize reviewer calls or held-out access. Real execution requires a new
approved study freeze with a passed qualification seal, privacy-cleared packet
bank, distinct candidate-generation record, exact sample and cluster rules,
output root under `Storage/`, analysis code, and a clean pre-held-out access
record. LLM outputs must be sealed before human ratings.
