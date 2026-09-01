# Dreaddit pilot cluster-aware sampling plan — version 0.1

Status: **prospective draft; pending PI, institutional, platform/source, and
privacy-process approval**.

## Design target

Select 60 analytic base packets from the official Dreaddit training split.
Assign exactly 12 base packets to each of the five controlled failure families:
unsupported evidence, source concentration, counterevidence loss, contextual
flattening, and unsupported abstraction. Each base packet yields one natural
item and one controlled twin, for 120 rated items. No rater may see both members
of a pair.

The design target is bound to
`experiments/direction_j_llm_as_rater/planning/INITIAL_DESIGN_RECOMMENDATION.md`
(SHA-256
`8d2b066b790de48059970713cd6b9eb286669fe5141f71a73c3d5d4107a22c79`).

## Candidate selection

1. Operate only after the Dreaddit real-text gates required before selection
   are affirmatively completed and machine validated.
2. Use only content-rule-eligible official training records after exact-text
   duplicate and complete-post exact-date quarantine.
3. Treat the complete released post as the indivisible source cluster. A post
   cannot appear in pilot, audit, practice, and confirmatory pools.
4. Draw 72 candidate post clusters in a deterministic order: 60 planned
   analytic clusters plus 12 ordered reserves. The seed must be generated and
   committed before records are opened; the public manifest stores only its
   SHA-256 commitment.
5. Apply the same frozen packet/context rule to every candidate. Do not replace
   a candidate because its content appears difficult or produces an
   unfavorable output.
6. Privacy reviewers work in the frozen candidate order. A rejected or
   use-restricted cluster is replaced only by the next reserve. The reason is
   recorded with a controlled code, not source text or free-form notes.
7. If fewer than 60 clusters clear all required uses, stop and revise the plan
   prospectively; do not expand or resample after inspecting outcomes.

## Balance and assignment

Before outcome generation, assign the first 60 cleared clusters to failure
families using a deterministic, seed-bound balanced allocation. Subreddit and
the released stress label may be used only to avoid extreme imbalance. They are
not evaluation truth, router features, or grounds for post hoc replacement.

Each item receives three independent ratings from each evaluator role. The
incomplete-block assignment balances family and natural/twin status, separates
twin pairs across raters, and excludes item constructors from rating or
adjudicating their own items.

## Privacy and leakage controls

Every excerpt and all displayed context require two distinct, current privacy
reviewers and separate permissions for model processing, rater display, and
quotation. Selection and review artifacts remain restricted. The official test
split and AGYW/CaCHe remain unopened for pilot development. Pilot source
clusters are permanently excluded from later audit/confirmation.

## Freeze fields still required

- Sampling seed commitment and private seed location.
- Packet/context-rule version and hash.
- Candidate-manifest version and hash.
- Reviewer registry and approved identity-crosswalk reference.
- Exact reserve/exclusion codes.
- Rater assignment algorithm and seed commitment.
- Approval references, authorities, effective dates, and expiries.
