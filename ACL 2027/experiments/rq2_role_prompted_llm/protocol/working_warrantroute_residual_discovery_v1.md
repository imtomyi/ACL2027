# WarrantRoute residual-discovery v1 working protocol

Date: 2026-09-02  
Status: implemented working diagnostic, quarantined from manuscript use

## Decision

Keep the public name `WarrantRoute`. The implementation identifier is
`residual_discovery_v1`; it is not a fifth Table 3 method. The existing
four-action router still chooses among Generalist, qualitative-methods,
domain, and all-role acquisition. Residual discovery is a post-routing output
layer that can recover one flaw flag missed by the selected reviewers.

This layer is necessary if WarrantRoute is expected to exceed `All roles`.
When every routed output is only a subset of the same three reviewer outputs,
the all-role union is a set-theoretic recall ceiling. A router alone cannot
cross it. Residual discovery expands the output hypothesis class rather than
pretending that a different route can beat its own superset.

## Mathematical contract

For packet `x`, route action `a`, and observed reviewer flag union `B(x,a)`, the
hashed Bernoulli Naive Bayes detector returns a flaw flag `h_theta(x)` and
posterior confidence `p_theta(x)`. The residual action is

```text
z_i(tau, k) = 1[p_i > tau + epsilon]
              * 1[h_i not in B_i]
              * 1[rank_i(p) <= k]

k = floor(r * n),  r = 0.35

F_i = B_i union {h_i if z_i = 1}
```

Threshold `tau` is selected on development validation data by

```text
maximize_tau    TP_validation(F)
subject to      sum_i z_i <= floor(0.35 * n)
tie break       fewer residual additions, then larger tau
```

The threshold comparison is strict: a confidence exactly on the threshold does
not trigger. Batch ties are resolved with a fixed digest seed. Role-LLM cost and
residual-compute cost are reported separately. The residual layer makes no new
LLM call and cannot remove an already observed flag, so recall on positive-only
packets is monotone by construction. That guarantee does not extend to
precision or real document quality.

## Leakage controls

- The classifier projects only predeclared claim and source-context text.
- Private answer fields, flaw notes, instructions, IDs, rationales, and raw
  reviewer responses are excluded.
- Text is mapped to 4,096 salted hash buckets; fitted artifacts store numeric
  document frequencies/log odds, never source text or a vocabulary.
- Each Dreaddit outer fold excludes its 20 test packets, 16 threshold-validation
  packets, and all 144 associated source groups. Each fitted fold contains 544
  of the 580 development packets.
- The transfer classifier is fitted on all 580 Dreaddit development packets.
  Its three model-specific thresholds use Dreaddit OOF predictions only.
- GoEmotion, CaChe, and ParlaMint-GB routes are written before their truth labels
  are parsed by the scorer. Their files are read earlier only to bind SHA-256
  input identities.
- Existing WarrantRoute actions, selected roles, and 1,200 role-call counts are
  immutable.

## Working replay

The validated replay produced the following aggregate diagnostic:

| Candidate | TP/1,200 | Recall | Mean role calls | Mean residual additions |
| --- | ---: | ---: | ---: | ---: |
| Fixed role | 767 | 63.9% | 1.0000 | 0 |
| WarrantRoute cumulative output | 773 | 64.4% | 1.3592 | 0 |
| All roles | 874 | 72.8% | 3.0000 | 0 |
| WarrantRoute residual discovery | 1,116 | 93.0% | 1.3592 | 0.2858 |
| All roles + same residual head | 1,163 | 96.9% | 3.0000 | 0.2408 |

At 1.3592 role calls, the randomized Fixed-role/All-roles convex mixture has an
expected 786.22 true positives. Strict Pareto efficiency therefore begins at
787. The residual working result crosses both that boundary and the all-role
total. It does not exceed All roles when the identical residual head and budget
are also given to All roles: the matched difference is 47 true positives in
favor of All roles, at an additional 1.6408 mean role calls. Thus the working
result suggests a cost-quality tradeoff, not an absolute quality win. These
comparisons are arithmetic diagnostics only.

## Shortcut quarantine

The apparent gain is not valid superiority evidence. The packet generators use
only five exact claim strings for 580 Dreaddit packets, one per intended flaw.
Exact claim, explanation, and theme-name values each predict the answer with
1.0 purity. All 343 residual flags selected by the threshold/budget rule match
the intended labels because the classifier exploits these synthetic templates.

The runner now audits exact-value purity before fitting and records
`scientific_interpretation_gate_passed=false`. A numerically successful replay
can remain `validated_working_complete` as an execution result while being
quarantined from scientific interpretation. The generated Markdown table also
shows the failed gate above the values.

## Formal qualification

Do not enable this implementation for a manuscript run until all of the
following exist:

1. Claims independently generated with lexical and structural variation, with
   no flaw name or fixed flaw-specific template in claim metadata.
2. Clean no-flaw negatives and plausible wrong-flaw hard negatives.
3. A source-cluster-disjoint frozen test bank untouched by router, classifier,
   prompt, and threshold development.
4. Precision, recall, F1, false-positive rate, calibration, and role-LLM plus
   residual-compute cost.
5. Ablations for source-only, claim-only, reviewer-output-only, and combined
   residual features.
6. A matched comparison that gives the same residual head to All roles, plus a
   separate system comparison without it. The working runner implements this;
   it must be repeated on the new frozen non-template test bank.

The current replay remains useful as an end-to-end feasibility and fail-closed
governance test. It must not populate the manuscript Table 3.

## Implementation

- Config: `experiments/rq2_role_prompted_llm/config/working_warrantroute_residual_discovery_v1.json`
- Runner: `experiments/rq2_role_prompted_llm/scripts/run_working_warrantroute_residual.py`
- Tests: `experiments/rq2_role_prompted_llm/tests/test_run_working_warrantroute_residual.py`
- Latest working output: `Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_warrantroute_residual_v4/`
