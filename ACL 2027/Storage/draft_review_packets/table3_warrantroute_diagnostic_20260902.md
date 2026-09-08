# Table 3 WarrantRoute failure analysis and recheck guide

Date: 2026-09-02  
Status: internal working diagnostic only  
Evidence: balanced n=100, 4 datasets, 3 models, 1,200 model-packet pairs  
Publication status: `working_result_only=true`, `manuscript_eligible=false`

## 1. Executive conclusion

The current WarrantRoute result is not lower because of one failed job or an
invalid JSON export. All 3,600 reviewer records passed final validation. The
main problem is the routing design and its alignment with the Table 3 metric.

1. WarrantRoute uses the Generalist output to decide a route, but discards that
   output whenever it selects a specialist. This loses already-correct detections
   at no call-cost saving.
2. The same uncalibrated routing weights are applied to models with very
   different rating behavior. This is especially harmful for Llama 3.1 8B.
3. The router is driven by perceived review sufficiency and action cost, while
   Table 3 reports recall only. The optimization target and reporting target do
   not match.
4. All roles is a union of all three role outputs. On an all-positive benchmark
   scored only by recall, this is a mathematical upper bound for any method that
   selects a subset of those outputs. WarrantRoute cannot exceed it on recall
   without producing a new synthesized decision.
5. The current tie implementation is numerically unstable. Mathematically tied
   scores can bypass the declared tie order because of floating-point differences
   around `5.55e-17`.

The first redesign should therefore be a Generalist-preserving cascade, followed
by model-calibrated routing trained on a disjoint development set. Rerunning the
same LLM calls before fixing these issues would mostly repeat the same failure.

## 2. Measured result

| Method | TP/1,200 | Mean recall |
| --- | ---: | ---: |
| Generalist | 654 | 54.5% |
| Fixed role | 767 | 63.9% |
| All roles | 874 | 72.8% |
| WarrantRoute | 653 | 54.4% |

WarrantRoute versus Generalist by model:

| Model | Generalist | WarrantRoute | Gained TP | Lost TP | Net |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 8B | 292/400 | 312/400 | 24 | 4 | +20 |
| Llama 3.1 8B | 123/400 | 85/400 | 1 | 39 | -38 |
| Gemma 3 4B | 239/400 | 256/400 | 22 | 5 | +17 |
| Total | 654/1,200 | 653/1,200 | 47 | 48 | -1 |

Exploratory paired exact tests confirm strong model interaction rather than a
uniform effect: Qwen improves (`p=0.00018`), Llama declines
(`p=7.46e-11`), Gemma improves (`p=0.00151`), and the pooled comparison is
effectively tied (`p=1.0`). These are working diagnostics, not confirmatory
publication tests.

## 3. Root-cause analysis

### 3.1 Generalist evidence is discarded after it has already been generated

The current role mapping is:

```text
generalist           -> Generalist
qualitative_methods  -> Methods only
domain               -> Domain only
both                 -> Methods + Domain
```

The router cannot choose a route until the Generalist review exists. Therefore,
discarding the Generalist flags on specialist routes saves no model call. It only
allows a specialist miss to erase a correct Generalist detection.

Observed consequence:

- 48 Generalist true positives were lost after routing.
- Only 47 new true positives were gained.
- Llama alone lost 39 and gained 1.

A zero-additional-call counterfactual that retains the Generalist flags gives:

```text
current WarrantRoute       653/1,200 = 54.4%
Generalist-preserving route 701/1,200 = 58.4%
All roles upper bound       874/1,200 = 72.8%
```

This is a 4.0-point improvement without another reviewer call, but it is not yet
enough to beat Fixed role or All roles.

### 3.2 Llama routing is anti-calibrated on the selected subsets

For Llama, the router selected Domain on 80 packets:

```text
Generalist detected target: 79/80
selected Domain detected:    42/80
```

The route therefore replaced an almost perfectly successful Generalist subset
with a weaker specialist subset. Conversely, the router retained Generalist on
306 packets, but All roles detected 150 targets while Generalist detected only
40. It missed 110 opportunities for useful escalation.

This means the problem is not merely that the Llama specialists are globally
weak. Llama All roles reaches 235/400 (58.8%). The routing rule sends specialists
on many already-solved cases and withholds them on many missed cases.

### 3.3 One policy is applied to incompatible model calibration patterns

The same raw 1--5 ratings, flags, confidence, and requested-expertise values are
used with the same weights for every model. Their output behavior is very
different:

- Qwen selects a specialist route on 373/400 packets.
- Llama selects a specialist route on only 94/400 packets.
- Gemma selects a specialist route on 270/400 packets.
- In Llama's Generalist-routed subset, `no_serious_flags` averages 0.86 and
  confidence is high, despite 110 specialist-recoverable misses.

Raw confidence and rating levels are therefore not interchangeable across model
families. Per-model calibration or normalized features are required.

### 3.4 Generalist self-assessment cannot reliably expose its own blind spots

The router's semantic signals come from the Generalist's own rating and flags.
When that model misses a flaw and incorrectly reports high sufficiency, the
router usually sees no reason to escalate. Structural counts alone cannot tell
whether a warrant, negative case, or contextual distinction was actually lost.

This is most visible for Llama and Gemma:

- Llama Generalist routes miss 110 detections available from another role.
- Gemma Generalist routes miss 43 detections available from another role.
- Qwen Generalist routes miss only 4, but Qwen almost always escalates.

The router needs a learned estimate of each specialist's *marginal value*, not
only a hand-written transformation of Generalist confidence.

### 3.5 The optimization objective does not match Table 3

WarrantGate subtracts specialist and coordination costs, but Table 3 reports no
latency, token, call, or cost column. It reports only `TP/N` and recall. A
cost-sensitive router can rationally trade away recall, but the table then judges
that trade only as lower quality.

Approximate calls per packet implied by the current routing are:

| Model | Calls per packet |
| --- | ---: |
| Qwen3 8B | 1.96 |
| Llama 3.1 8B | 1.24 |
| Gemma 3 4B | 1.93 |
| Overall | 1.71 |

The Generalist call is included because it is required to compute the route.
All roles uses 3 calls. Any WarrantRoute claim should therefore be framed as a
recall--cost Pareto comparison, not recall alone.

### 3.6 All roles is structurally favored by the current benchmark

Every balanced packet contains an intended flaw, and All roles is scored as the
union of all role flags. There are no no-flaw packets and no penalty for extra or
incorrect flags. Therefore:

```text
Recall(All roles union) >= Recall(any subset route)
```

WarrantRoute can tie All roles by selecting every useful role, but cannot exceed
it on this recall definition. To demonstrate better *quality*, the evaluation
must include clean negatives and measure precision, false-positive rate, F1,
credibility, confirmability, and cost. Alternatively, WarrantRoute needs a new
final synthesis/adjudication step whose output is not merely a subset union.

### 3.7 Routing gains are concentrated in one flaw family

Aggregated by intended flaw:

| Flaw | Generalist | WarrantRoute | Generalist-preserving route | All roles |
| --- | ---: | ---: | ---: | ---: |
| Contextual flattening | 181 | 177 | 183 | 230 |
| Counterevidence loss | 127 | 108 | 130 | 163 |
| Source concentration | 55 | 89 | 93 | 122 |
| Unsupported abstraction | 192 | 181 | 193 | 219 |
| Unsupported evidence | 99 | 98 | 102 | 140 |

The current policy mainly helps source-concentration detection. It harms
counterevidence loss and unsupported abstraction, indicating that method/domain
need signals are not separating flaw families reliably.

### 3.8 The declared tie rule is not implemented robustly

`choose_route` compares raw floating-point scores. It does not apply a tolerance
before the tie order. For Qwen, 240/400 decisions have top-score differences no
larger than `1e-12`; many are mathematical ties represented as, for example,
`0.32000000000000006` versus `0.32`.

Applying a `1e-9` tie tolerance changes Qwen's route distribution from:

```text
G=27, M=306, D=55, B=12
```

to:

```text
G=267, M=80, D=41, B=12
```

Recall changes little in this offline replay, but the claimed route distribution
and average call cost change substantially. This must be fixed before interpreting
efficiency or freezing a policy.

### 3.9 The current baselines and evidence are exploratory

- WarrantGate v0 was selected from a Dreaddit/Qwen working sanity check, not a
  prospectively frozen multicorpus, multimodel training procedure.
- Fixed role is selected using role recall from the same n=100 dataset/model
  sample on which it is reported. That makes it an optimistic working baseline.
- There is one stochastic output per role/model/packet, temperature is 0.2, and
  no seed or immutable Ollama model digest is frozen.
- Current Wilson intervals are not paired tests over the common packets.

These limitations do not explain all of the WarrantRoute decline, but they make
small differences unreliable and prevent manuscript use.

## 4. Required redesign before another full LLM run

### P0: Correct the method semantics

- [ ] Make routing cumulative: always retain Generalist output.
- [ ] Define Methods route as `Generalist union Methods`.
- [ ] Define Domain route as `Generalist union Domain`.
- [ ] Define Both route as `Generalist union Methods union Domain`.
- [ ] Count the Generalist call in every WarrantRoute cost calculation.
- [ ] Add a monotonicity test: WarrantRoute recall cannot be below Generalist
      when both are scored from the same completed outputs.

### P0: Align the objective and the table claim

- [ ] Decide whether the primary objective is maximum recall or recall under a
      call/token/latency budget.
- [ ] If cost-sensitive, report calls, tokens, latency, or normalized cost beside
      quality metrics.
- [ ] Do not claim WarrantRoute should beat All roles on union recall; test
      Pareto efficiency instead.
- [ ] If the goal is to beat All roles on quality, add a final synthesis or
      adjudication stage and evaluate precision/credibility/confirmability.

### P0: Replace hand-written universal weights with calibrated routing

- [ ] Train the router to predict marginal escalation value:
      `M helps = not G_detected and M_detected`, and similarly for Domain.
- [ ] Use model identity or a separately calibrated policy per model.
- [ ] Calibrate confidence and ordinal rating features per model.
- [ ] Select thresholds under a predeclared average-call budget.
- [ ] Compare logistic regression or a small gradient-boosted tree against the
      hand-written score before introducing a larger router model.
- [ ] Keep answer-key and specialist outcomes available only during development;
      never expose them at inference.

### P1: Fix deterministic routing correctness

- [ ] Apply a declared score tolerance or fixed-point quantization before the tie
      order.
- [ ] Add unit tests for exact ties, near ties, missing features, invalid ratings,
      and fallback behavior.
- [ ] Record score precision, tolerance, tie order, and selected action in the
      policy manifest.
- [ ] Revalidate every route against an independent implementation, not the same
      helper function used to generate it.

### P1: Diagnose and recalibrate the reviewer models

- [ ] Audit Llama Generalist high-confidence/no-flag misses by flaw family.
- [ ] Audit why Llama Domain is selected on 80 packets where Generalist detects
      79 targets.
- [ ] Audit Gemma Domain replacement, which loses more targets than it gains.
- [ ] Check confusion matrices for each role x model x flaw type.
- [ ] Add balanced, training-only positive and negative examples to prompts if
      prompt-based calibration is retained.
- [ ] Verify that role prompts create useful specialization rather than merely
      different flagging frequency.
- [ ] Freeze exact Ollama model digests, prompt hashes, context length, seed,
      temperature, and generation limit.
- [ ] Run at least three deterministic seeds or set temperature to zero for the
      formal comparison, depending on the frozen protocol.

### P1: Repair evaluation design

- [ ] Add no-flaw and plausible-but-correct packets to measure false positives.
- [ ] Report precision, recall, F1, false-positive rate, credibility,
      confirmability, and review cost.
- [ ] Select Fixed role on a development split and report it on a separate test
      split.
- [ ] Use paired packet-level confidence intervals and paired tests.
- [ ] Correct for multiple model/dataset comparisons or designate one primary
      comparison prospectively.

## 5. Clean experimental sequence

1. Treat the current balanced n=100 results as diagnostic development evidence.
   Do not tune on them and then report the same values as a final test.
2. Implement Generalist-preserving offline replay using the already completed
   3,600 outputs. No new LLM run is needed for this step.
3. Fix tolerant tie handling and add routing/scoring invariant tests.
4. Build a disjoint route-development bank. Packet IDs must not overlap the
   future final evaluation bank.
5. Fit and calibrate model-specific marginal-value routing on development data.
6. Choose one cost budget and one primary quality endpoint before opening the
   final test truth map.
7. Freeze policy, feature schema, thresholds, prompts, model digests, seed,
   scoring script, and artifact hashes.
8. Run one untouched balanced test set across all four datasets and all three
   models.
9. Report paired uncertainty and the quality--cost Pareto frontier.
10. Keep the export under `Storage/` until all governance gates make it
    manuscript eligible.

## 6. Proposed acceptance gates

The next WarrantRoute candidate should satisfy all of the following on untouched
test data:

- [ ] No dataset/model cell regresses below Generalist recall.
- [ ] No model family has a large negative cliff like Llama's current -9.5
      average points.
- [ ] Recall is compared at a declared average-call or token budget.
- [ ] WarrantRoute recovers a prospectively chosen fraction of All roles recall
      while using materially fewer calls.
- [ ] Precision or false-positive rate does not degrade when clean negatives are
      included.
- [ ] Credibility and confirmability are measured by a frozen judge protocol,
      with a human audit subset.
- [ ] Tie, fallback, blinding, call accounting, and output-union invariants pass.
- [ ] Policy selection and Fixed role selection use development data only.
- [ ] Final results are reproducible from frozen hashes and model digests.

## 7. Immediate next action

Do not rerun all 3,600 reviewer calls yet. First implement and test two offline
candidates against the existing outputs:

1. `WarrantRoute` cumulative-output candidate: current routes, but retain
   Generalist flags.
2. Calibrated-router prototype: cumulative routing plus model-calibrated
   marginal gain prediction trained and evaluated on disjoint packet splits.

The first candidate verifies the output-composition fix. The second tests whether
the routing idea can beat Generalist and approach All roles at lower cost without
post-hoc manipulation of the final evaluation set.

## 8. Implementation outcome

The two prescribed offline candidates were implemented and replayed on
2026-09-02 without new reviewer calls.

### 8.1 Selected immediate correction: WarrantRoute

The corrected `WarrantRoute` preserves all 1,200 frozen WarrantRoute-S decisions and
their call counts, but changes output composition to cumulative union:

```text
G  -> G
M  -> G union M
D  -> G union D
B  -> G union M union D
```

It detects `773/1,200` targets versus `770/1,200` for WarrantRoute-S at the
identical mean `1.3592` role calls per packet. It improves three cells by one TP,
regresses in no cell, and cannot fall below Generalist recall under the current
union-recall scorer. All 1,200 source route decisions and specialist acquisition
counts are byte-derived from the pinned source route artifact; only composition
metadata changes.

This is the selected P0 semantic correction because it strictly dominates the
source WarrantRoute-S replay on the current working metric without an additional
model call. Its validated artifacts are under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_warrantroute_improved_v1/`.

### 8.2 Calibrated cumulative candidates

A model-specific logistic marginal-gain router with a predeclared mean 1.75-call
development budget was also implemented. It includes `1e-9` score tolerance,
STOP on threshold ties, fixed transition tie order, and validation-score
breakpoint enumeration. The breakpoint version detects `747/1,200` targets at
mean `1.3692` calls. Because the corrected WarrantRoute has both higher recall and
lower mean calls, the breakpoint candidate is rejected as a replacement and is
retained only as a diagnostic prototype.

The rejected result does not invalidate calibrated routing as a research
direction. It shows that 64 training and 16 threshold-selection packets per
outer fold are insufficient for stable model-specific marginal-value transfer,
especially under corpus shift. A new disjoint development bank and clean
negative examples remain prerequisites for a formal calibrated-router claim.

### 8.3 Completed working gates

- [x] Generalist is retained on every cumulative specialist route.
- [x] Corrected WarrantRoute does not regress below Generalist in any of 12 cells.
- [x] Generalist call accounting is explicit in every route and aggregate.
- [x] Exact and near-tie behavior uses a declared tolerance and fixed order.
- [x] Threshold selection enforces its development call budget.
- [x] Route scoring is independently recomputed from selected-role flags.
- [x] Source routes, output union, call counts, and artifact hashes are checked.
- [ ] Clean negatives, precision, F1, and false-positive rate are not available.
- [ ] No prospective untouched test was created; all results remain working only.
