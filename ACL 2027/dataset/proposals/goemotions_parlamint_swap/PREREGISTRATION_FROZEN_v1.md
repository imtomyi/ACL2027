# WarrantRoute preregistration (FROZEN) — four-corpus add design

Preregistration id: `warrantroute-add-goemotions-v1`
Design freeze date: 2026-08-29 (America/Chicago)
Approved in session by the user: corpus addition and the Section 3 specs of
`TABLE3_GOEMOTIONS_UNBLOCK_PLAN.md`.

## Freeze scope and what this does NOT do

This freezes the **study design** for the add-corpus configuration now in the
manuscript. It fixes the corpus roles, the router and evaluation specs, the
estimands, and the resampling design so they cannot be chosen after seeing
outcomes.

It does not, by itself:
- lift the harness fail-closed `run` gate (`source_bearing_execution_allowed` and
  `routing_policy_bound` remain `false` until an authorized successor freeze),
- constitute the institutional or platform governance determination, or
- authorize model processing or rater exposure.

No result may populate the manuscript until a frozen, authorized analysis export
is produced under this design.

## 1. Corpus assignment (Table 1 order)

| Corpus | Role | Confirmatory? |
|---|---|---|
| Dreaddit | development + in-domain audit | descriptive |
| GoEmotions | development + in-domain audit | descriptive |
| CaChe | held-out cross-domain | **sole confirmatory** |
| ParlaMint-GB | held-out cross-domain | descriptive |

GoEmotions uses the simplified split: `train` for development, `test` for the
in-domain audit. Provenance and verified statistics are in
`provenance_goemotions.md`. The candidate pool is `train` + `test`.

## 2. Research questions and estimands

Unchanged from the manuscript. RQ1 detection recall by routing method, RQ2
WarrantRoute versus fixed-role recall difference and the paired human versus LLM
difference, RQ3 repair without collateral error. Recall is
\(R = TP/(TP+FN)\) on eligible controlled variants, each with one independently
verified error.

## 3. Frozen router and evaluation specs (approved)

- Feature encoding: pre-specialist signals only, that is the initial researcher
  rating, recorded uncertainty, and requested-expertise flag. No protected
  attributes, no verified error, no test outcome.
- Training target: the route that maximizes detection of the one verified error
  on development packets.
- Model formulation: a small interpretable policy over the three signals above.
- Regularization: prefer `none` and single-specialist routes over `both` unless a
  signal threshold is met, to bound expert time.
- Expert-time costs and budget: fixed per-route expert-minute cost and a total
  development budget, recorded in the run manifest at execution.
- Thresholds and route ties: thresholds fixed on development data, ties resolve
  toward the lower-cost route.
- Failure action: a failed selected role contributes no flag and is never
  replaced by another role.
- Development minima: minimum eligible variants and minimum source clusters
  required before a route is admissible, recorded in the run manifest.
- Baseline procedures: random routing and uncertainty-only routing, matching the
  RQ1 table.

## 4. Resampling and comparison families

- Intervals use 10,000 paired bootstrap resamples over source clusters, seed
  20260829.
- Cluster units: Dreaddit by post, GoEmotions by comment (the simplified split
  has no thread linkage), CaChe by focus group and transcript-local speaker,
  ParlaMint-GB by debate and speaker.
- Confirmatory family: the overall CaChe WarrantRoute versus fixed-role recall
  difference for the frozen primary reviewer, before human ratings. All Dreaddit,
  GoEmotions, and ParlaMint-GB results are descriptive.
- Reviewers: Qwen3 8B (primary designation to be confirmed at activation),
  Llama 3.1 8B, Gemma 3 4B, identical packets, roles, schemas, repetitions, and
  miss rules.

## 5. Gates remaining before execution (not covered by this design freeze)

1. Governance determination that GoEmotions model processing and rater exposure
   are approved.
2. GoEmotions packet generation with independent human verification of each
   variant's single verified error.
3. Bind Llama 3.1 8B and Gemma 3 4B (model-specific reviewer freeze and canary;
   Gemma on the guarded 16,384-token context path).
4. Authorized successor freeze that lifts the harness fail-closed `run` gate.
5. Run, compute intervals, freeze the analysis export, then populate Table 3 from
   that export.
