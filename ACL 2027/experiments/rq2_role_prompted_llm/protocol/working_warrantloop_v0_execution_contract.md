# Working WarrantLoop v0 execution contract

Status: development-only offline replay, not a successor study freeze, not
Table 3, and not manuscript eligible.

## Purpose

This contract permits a software and small-sample diagnostic of the sequential
WarrantLoop design using independently cached role outputs. It does not modify
the current Table 3 WarrantRoute row, the Qwen3 WarrantRoute v1 contract, or any
formal data-access decision.

## Allowed execution

- Fit transition models only on packets whose corpus is `dreaddit`, whose source
  split is `development_train`, and whose packet record identifies the lane as
  development-only.
- Read only the active packet IDs and the source-free structured scoring
  projections for `generalist`, `qualitative_methods`, and `domain`.
- Use the private intended-flaw map only in the development fitter and the final
  scorer. The route application stage must not receive a truth-map path or any
  intended-flaw value.
- Reveal a cached specialist projection to the controller only after the route
  trace records the corresponding acquisition action.
- Write only restricted working artifacts below
  `Storage/rq2_personal_local_diagnostic/warrantloop_working/`.
- Keep every result labeled
  `private_personal_exploratory_not_for_publication` and
  `manuscript_eligible=false`.
- After a development-only policy is fitted and written, it may be applied
  without refitting to complete cached working banks from other corpora. Such an
  application is retrospective descriptive evidence only. All external routes
  must exist before their private truth subsets are opened for scoring.

## Prohibited execution

- Do not use source text, quotations, free-form rationales, answer-key fields,
  human judgments, final-grader outputs, or held-out outcomes as router inputs.
- Do not fit or tune on Dreaddit audit, CaChe, ParlaMint-GB evaluation, or any
  other held-out/evaluation lane.
- Do not replace, relabel, or append rows to the current Table 3 experiment.
- Do not contact a cloud service or start an additional local LLM call for this
  offline replay.
- Do not treat a smoke result, retrospective replay, software fixture, or model
  coefficient as manuscript evidence.
- Do not enable a formal run by editing a boolean. Formal execution requires a
  separately reviewed successor contract and prospective freeze.

## Stage order

1. Validate the personal-local policy, exact data lane, source-group separation,
   reviewer-output inventory, schemas, and model inventory.
2. Make a deterministic answer-key-independent hash split whose source
   components are disjoint across train, validation, and smoke-test partitions.
3. Fit improvement and harm estimators on train only.
   If either binary class has fewer than three observations, use the frozen
   Laplace-smoothed constant-risk fallback rather than fitting an unstable
   coefficient vector.
4. Select the stopping threshold on validation only and refit coefficients on
   train plus validation without changing the threshold.
5. Write and hash the fitted policy artifact.
6. Apply the policy to the smoke-test packets through an interface that cannot
   contain a truth map. Write and hash all route traces.
7. Only after the route file exists, load the smoke-test truth subset in the
   scorer and write private detail plus aggregate metrics. The fitter receives
   only the train and validation truth subset.
8. Mark the smoke complete only if every route terminates, the role and packet
   inventories reconcile, no route contains forbidden fields, and the maximum
   of two specialist acquisitions is respected.

## Fixed controller semantics

The terminal modes are `generalist`, `qualitative_methods`, `domain`, and
`both`. `STOP` and `ACQUIRE` are controller actions, not additional modes.
Specialist terminal modes replace rather than union generalist flags. `both`
unions the two specialist flag sets. The controller can acquire each specialist
at most once and must terminate after both are acquired.

Every first-stage transition estimates

```text
expected gain = P(improvement) - P(harm)
net value = expected gain - lambda * incremental cost
```

The controller stops when the largest available net value is no greater than
the selected threshold. After one specialist is acquired, only the transition
to `both` remains available.

## Promotion boundary

Passing this contract establishes only that the development-only offline replay
is executable and internally consistent. A real prospective WarrantRoute-S
experiment still requires a successor freeze that binds the data split, feature
order, prompts, model profiles, estimator, calibration, costs, threshold,
failure behavior, baselines, precision target, policy hash, and pre-access seal
before any audit or held-out outcome is opened.

## Completed retrospective working replay

The four-corpus `balanced_n100` replay completed under
`working_warrantloop_multicorpus_v0.json`. Dreaddit used five-fold out-of-fold
routes. One transfer policy fitted only on the full Dreaddit development bank
was then applied unchanged to GoEmotion, CaChe, and ParlaMint-GB. The run reused
the existing 3,600 valid role outputs and made no new LLM calls. Its outputs are
under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_v1/`.

This replay occurred after the earlier working Table 3 run had already opened
the evaluation outcomes. It is therefore retrospective even though its fitting
code excludes those outcomes. It cannot serve as a prospective held-out test.
