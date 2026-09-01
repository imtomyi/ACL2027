# Dreaddit RQ2 test sampling and packet plan — version 0.1

Status: **prospective draft; pending design, PI, institutional,
source/platform, endpoint, privacy-process, and release approval**.

## Frozen design decision still required

Before opening the official test records, the approved study freeze must name:

- the number of analytic post clusters and ordered reserves;
- the private sampling seed and public seed commitment;
- the allocation across the five prespecified error families;
- the independent candidate-generation actor and snapshot;
- the packet/context rule and controlled-variant construction rule;
- the independent verification panel and acceptance rule;
- the exact target-to-response-flag mapping;
- all exclusion, replacement, and stop rules; and
- the final item denominator used for the Table 3 Generalist row.

The existing feasibility plan of 12 controlled items per error family, or 60
controlled items total, is a reasonable starting point for review. It is not
automatically the audit sample size and remains unfrozen until the responsible
study authority approves it.

## Selection and leakage boundary

1. Require a current formal readiness report with the Dreaddit lane at 10/10
   and `real_text_ready: true` before reading the official test records.
2. Bind the exact received-file, working-copy, source-manifest, exact-date
   quarantine, packet-rule, outcome, prompt, model, runner, and analysis hashes.
3. Treat each complete released post as one indivisible source cluster.
4. Select clusters deterministically from the eligible official test pool using
   the frozen seed. Do not use outcomes, model responses, or content difficulty
   to select or replace a cluster.
5. Apply ordered reserves only for prespecified eligibility, privacy, or
   technical reasons. Record controlled reason codes and never replace an item
   because its result is unfavorable.
6. Preserve one controlled version per base packet in the scoring set. No
   reviewer sees the target error, answer key, construction notes, generator
   identity, verifier output, route, or another reviewer's response.
7. Keep official training data, test data, and CaChe in their assigned roles.
   No test item may inform development or a later freeze revision.

## Packet and answer-key separation

The restricted evaluator-item bank contains only the blinded item shown to the
reviewer. A separate coordinator-only truth and post-cluster map contains the
item ID, post-cluster commitment, independently verified error family, and the
response-form flag assigned before evaluation. A text-free packet seal binds
both item sets by hash without revealing source text or item-level truth.

Every source excerpt and displayed context window requires two distinct,
current privacy reviewers. The permission intersection must allow Qwen model
processing for this study cell. Human display, quotation, and release are
separate decisions and cannot be inferred from model-processing clearance.

## Scoring contract

The frozen Generalist prompt is applied to every eligible item using the exact
Qwen3 8B reviewer snapshot. Three stateless repetitions use the fixed seeds in
the component contract. Repetition 1 supplies Table 3. Invalid output,
`cannot_judge`, abstention, timeout, truncation, filtering, terminal failure,
and a missing or incorrect response flag stay in the denominator as misses.

The aggregate exporter reports `TP/N`, recall, and the 10,000-resample
post-cluster percentile 95 percent interval using seed `20270826`. Fewer than
five independent post clusters is a stop condition for the interval. No result
is written when the packet bank, truth map, observation set, approval record,
or freeze is incomplete or hash-inconsistent.

## Final freeze fields

- Approved analytic and reserve cluster counts.
- Seed commitment and restricted seed location.
- Packet-bank seal, truth-map, and privacy-ledger hashes.
- Candidate generator and Qwen reviewer actor records.
- Component, prompt, guide, schema, runner, scoring, and analysis hashes.
- Formal governance record and current readiness-report hashes.
- Clean pre-test-access record and freeze time.
- Output directory, retention deadline, deletion procedure, and aggregate-only
  release manifest.
