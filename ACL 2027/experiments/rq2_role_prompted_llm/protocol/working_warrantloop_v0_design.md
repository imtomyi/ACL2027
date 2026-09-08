# WarrantLoop v0: literature basis and modeling design

Status: selected research direction with a validated development-only offline
replay prototype; not prospectively frozen, not the Table 3 default, and not
manuscript eligible.

Date: 2026-09-02

## 1. Decision in one paragraph

The recommended extension of WarrantRoute is **WarrantLoop**, internally, and
**WarrantRoute-S: budgeted sequential reviewer routing** as the provisional
paper-facing label. WarrantGate remains the policy that estimates which review
expertise is useful. The extension adds a finite-state controller that may
observe a structured, source-free projection of an acquired role output,
acquire one additional specialist when its expected marginal detection value
exceeds its cost, and otherwise stop. The method is not an open-ended
self-refinement loop, does not let a model grade its own correctness, and does
not change the four terminal review modes. Its closest formal basis is
sequential cost-sensitive information acquisition with optimal stopping; the
generic agent loop is the execution pattern, not the primary mathematical
claim.

This design is a successor experiment. The current Table 3 WarrantRoute row
must remain the one-shot WarrantGate v0 result.

## 2. Why this document exists

The current project contains two related but distinct adaptive ideas:

1. Packet-level WarrantGate v0 chooses one terminal route before specialist
   outputs are used.
2. WarrantGate-Adaptive v0 can choose different routes for ordered document
   segments, but still routes before specialist outputs are used.

Neither is a complete agent loop. A complete loop requires an observation after
an action and a policy decision that uses that observation. Adding such feedback
inside the current Table 3 run would violate the active WarrantRoute contract,
which forbids route changes after specialist observations. WarrantLoop therefore
needs its own prospective successor contract, data split, policy freeze, and
evaluation row.

## 3. Terminology

### Agent loop

An agent loop is an execution pattern:

```text
state -> choose action -> execute action -> observe result -> update state
      -> stop or choose another action
```

ReAct interleaves reasoning and environment actions. Reflexion and Self-Refine
show variants in which feedback is carried into later attempts. CRITIC adds
tool-grounded verification before correction. These works motivate explicit
action, observation, and feedback interfaces, but they do not by themselves
specify the right cost function or stopping policy for WarrantRoute.

### Loop engineering

As of 2026, *loop engineering* is an emerging engineering label rather than a
mature, single academic theory. The recent literature describes triggered runs,
machine-checkable stop conditions, persistent state, verifier separation,
budgets, and human escalation. Those are useful implementation disciplines, but
the paper should not present "loop engineering" as the formal statistical or
decision-theoretic basis of WarrantRoute.

### WarrantGate and WarrantLoop

- **WarrantGate** estimates the value of the four review routes.
- **WarrantLoop** controls when to acquire another specialist and when to stop.
- **WarrantRoute** remains the name of the overall role-routing method family.

The provisional paper-facing description is:

```text
WarrantRoute-S: budgeted sequential reviewer routing
```

### Naming check

A 2026 non-peer-reviewed retrieval preprint already uses `WarrantGate` as a
software class and refers to a "warrant loop" in a different RAG architecture.
The conceptual overlap is small, but the phrase-level collision could confuse
search and attribution. Keep `WarrantLoop` as the internal design identifier for
now, prefer `WarrantRoute-S` in draft prose, and repeat the literature/name check
before the method name is frozen for submission. The existing `WarrantGate`
implementation name should also be described functionally rather than claimed
as a novel standalone term.

## 4. Literature synthesis

| Literature | Relevant result | Adaptation to this project | Limit |
| --- | --- | --- | --- |
| ReAct | Interleave decisions with observations from actions. | Make reviewer selection an explicit action followed by a structured observation. | ReAct does not supply a cost-sensitive reviewer objective. |
| Reflexion and Self-Refine | Feedback can guide later attempts. | Let a previously acquired role projection update the next routing state. | Pure self-feedback can preserve or amplify the same model error. |
| Huang et al. and CRITIC | Intrinsic self-correction can degrade performance; grounded feedback is more reliable. | Do not use unconstrained self-critique as a stop test. Use frozen structured observations and external truth only for training/scoring. | The role prompts currently share a base model, so their errors need not be independent. |
| FrugalGPT | A cascade invokes another model only when the earlier response is insufficient. | Generalist-first escalation and explicit reviewer cost. | Its candidates are model APIs rather than expertise prompts. |
| RouteLLM | Learn a cost-quality router from preference data. | Learn expected route benefit on development data, then freeze the policy. | Preference data are not the same as flaw-detection truth. |
| Confidence-token routing | Calibrated confidence can support fallback or expert routing. | Treat confidence as one calibrated feature, not a sufficient stop rule. | Raw LLM confidence is not assumed calibrated. |
| Sequential cost-sensitive feature acquisition | Adaptively acquire costly information under a prediction budget. | Treat a specialist review as a costly observation that may improve detection. | Reviewer observations are structured model outputs, not ordinary input features. |
| Active-Acquisition POMDP | Balance the value of newly acquired information against decision cost under partial observability. | Provides a general formalization for hidden review need and sequential observations. | Full POMDP/RL estimation is excessive for the initial two-specialist horizon. |
| Adaptive Computation Time and PonderNet | Allocate a variable number of computation steps and learn when to halt. | Charge every role call and make stopping part of the model. | These methods learn differentiable neural halting, which is not required here. |
| GPTSwarm and DyLAN | Represent agent interaction as a graph; dynamically select agents and stop early. | Represent WarrantLoop as an inspectable finite-state graph rather than an opaque conversation. | Their collaboration tasks and optimization targets differ from qualitative flaw detection. |
| iMAD | Trigger multi-agent debate only when expected to help because always-on debate can waste tokens or overturn correct answers. | Compare selective specialist activation with All roles and budget-matched controls. | WarrantLoop is review acquisition, not debate or consensus. |
| Adaptive submodularity | Greedy sequential information gathering may be near-optimal when conditional marginal gains diminish. | Test whether second-specialist gain is lower after the first specialist; use only as a later justification if the condition is supported. | No adaptive-submodularity guarantee may be claimed without verifying its assumptions. |

The strongest direct analogy is not generic multi-agent debate. It is **active
acquisition of costly reviewer evidence followed by optimal stopping**.

## 5. Requirements and non-requirements

### Functional requirements

WarrantLoop must:

- preserve the four terminal routes `generalist`, `qualitative_methods`,
  `domain`, and `both`;
- begin from the existing generalist diagnostic;
- allow a first specialist observation to justify acquiring the other
  specialist;
- stop after at most two specialist acquisitions;
- expose every state, score, action, cost, and stop reason in a route trace;
- support exact offline replay from independently generated role outputs;
- preserve the existing target-to-flag Table 3 scoring rule.

### Scientific non-requirements for v0

WarrantLoop v0 does not need:

- open-ended reflection;
- agents debating or rewriting one another's reviews;
- cross-packet memory at evaluation time;
- reinforcement learning;
- a free-form LLM judge inside the controller;
- source text inside the routing model;
- changes to the current Table 3 experiment.

## 6. Four terminal modes versus controller actions

The project has exactly four review modes. WarrantLoop does not create a fifth
mode:

```text
G = generalist
M = qualitative_methods
D = domain
B = both specialists
```

`STOP` and `ACQUIRE` are controller decisions, not review modes. At the first
decision, they map to the existing four modes:

```text
STOP_G        -> terminal mode G
ACQUIRE_M     -> observe M, then reconsider M versus B
ACQUIRE_D     -> observe D, then reconsider D versus B
ACQUIRE_BOTH  -> terminal mode B after both outputs are acquired
```

After acquiring `M`, the only valid decisions are `STOP_M` or
`ACQUIRE_D_TO_B`. After acquiring `D`, the only valid decisions are `STOP_D` or
`ACQUIRE_M_TO_B`. After acquiring both, the loop must stop.

This monotone specialist-acquisition graph prevents cycles and makes a separate
ad hoc loop-count cutoff unnecessary. Including the initial generalist, the hard
maximum is three **role acquisitions** per packet.

A role acquisition is the frozen observation unit for one role. In a
single-repetition working run it is one LLM call. If a future formal run binds
`R` stateless repetitions per role, an acquisition reveals the entire frozen
role bundle and costs `R` calls; the maximum is then `3R` actual calls, not
three. Repetitions and their reduction rule must be fixed before policy fitting
and cannot be requested adaptively.

## 7. Selected mathematical formulation

### 7.1 Hidden need and observable state

Let `x` be a packet and `y` its private intended-flaw label. The router never
observes `y` at inference time. Let:

```text
phi(x)  = frozen source-free packet features
o_G     = generalist role output
o_M     = qualitative-methods role output
o_D     = domain role output
P(o)    = frozen source-free structured projection of a role output
E_t     = specialist roles acquired by step t, a subset of {M, D}
b_t     = remaining reviewer budget
```

The state is:

```text
s_t = (phi(x), P(o_G), E_t, {P(o_e): e in E_t}, b_t)
```

Conceptually, this state represents a belief about the unobserved question:
which additional expertise, if any, will improve flaw detection for this
packet?

### 7.2 Terminal-route mapping

```text
rho(empty)  = G
rho({M})    = M
rho({D})    = D
rho({M,D})  = B
```

The mapping preserves the active WarrantRoute semantics:

- `G` uses only generalist flags;
- `M` uses only qualitative-methods flags;
- `D` uses only domain flags;
- `B` unions qualitative-methods and domain flags;
- specialist terminal routes do not silently union generalist flags.

The generalist output is therefore both a possible terminal review and an
initial routing observation. It is not automatically part of specialist-mode
predictions.

### 7.3 Costed terminal utility

With the current one-known-target packet design, the estimable detection reward
and cost-adjusted development utility are:

```text
R_det(r; x, y) = I[y is detected by route r]
U_recall_cost(r; x, y) = R_det(r; x, y) - lambda * C(r)
```

where `C(r)` includes all calls inside the acquired role bundle, tokens or wall
time, and any coordination cost. Because the generalist diagnostic is always
acquired, the absolute acquisition costs are:

```text
C(G) = c_G
C(M) = c_G + c_M
C(D) = c_G + c_D
C(B) = c_G + c_M + c_D + c_B
```

The current WarrantGate configuration treats `c_G` as the common zero-cost
baseline when comparing incremental routes. Extra flags cannot automatically be
counted as false positives because the current private map identifies the
intended flaw, not necessarily every valid flaw in the packet.

If a future adjudicated multi-label truth set `Y(x)` is available, the utility
may be extended prospectively:

```text
U_full(r) = detection_value(r, Y) - mu * false_positive_cost(r, Y)
            - lambda * C(r)
```

The current data support a recall-cost claim, not a precision-cost claim.

### 7.4 Marginal value of another specialist

For an unacquired specialist `e`, define its conditional expected gain:

```text
delta(r -> r') = R_det(r') - R_det(r), in {-1, 0, +1}
Delta_t(e) = E[delta(rho(E_t) -> rho(E_t union {e})) | s_t]
```

For the first specialist transition, `G -> M`, `G -> D`, or `G -> B`, the
reward can decrease because specialist terminal routes replace rather than
union the generalist flags. Therefore the estimator must represent both benefit
and harm:

```text
Delta_hat(r -> r' | s) = P(delta = +1 | s) - P(delta = -1 | s)
```

For `M -> B` and `D -> B`, the existing union reducer makes detection reward
monotone when both selected outputs are valid, so the decrement probability is
zero. Failure handling must still be modeled separately.

The net acquisition value is:

```text
N_t(e) = Delta_hat_t(e) - lambda * delta_C(E_t, e)
         - eta * c_coord(E_t, e)
```

Here `delta_C` is the incremental role-bundle/token/latency cost of acquiring
`e`; the already paid generalist cost is not subtracted again. If roles use
multiple frozen repetitions, `delta_C` includes every call in that bundle.

The controller selects the available specialist with the largest net value. It
stops when:

```text
max_e N_t(e) <= tau_stop
```

or when the hard reviewer budget is exhausted. `tau_stop`, costs, tie order,
and missing-observation behavior must be frozen on development data.

The one-shot WarrantGate `both` score remains useful at `t=0`. If the predicted
joint value is clearly above either sequential branch, the controller can
acquire `M` and `D` in parallel as `ACQUIRE_BOTH`; otherwise it observes one
specialist before deciding whether the second is worth its cost.

### 7.5 Finite-horizon value function

The general formulation is:

```text
V(s_t) = max(
    U_stop(s_t),
    max over available e [
        -lambda * delta_C(E_t, e) + E_o[V(T(s_t, e, P(o_e)))]
    ]
)
```

This resembles an active-acquisition POMDP, but the initial implementation
should not fit a general RL policy. There are only two specialists and four
reachable terminal routes, so exact enumeration plus calibrated supervised
gain estimation is simpler, more stable, and more auditable.

## 8. Recommended v0 controller

### 8.1 Prediction targets

Fit calibrated transition-value estimators on development data:

```text
Delta_GM(s_0) = E[R_det(M) - R_det(G) | s_0]
Delta_GD(s_0) = E[R_det(D) - R_det(G) | s_0]
Delta_GB(s_0) = E[R_det(B) - R_det(G) | s_0]
Delta_MB(s_M) = E[R_det(B) - R_det(M) | s_M]
Delta_DB(s_D) = E[R_det(B) - R_det(D) | s_D]
```

These may be implemented as one action-conditioned model or a small set of
regularized models. For the first three transitions, estimate both the
probability of improvement and the probability of harm, then use their
difference as expected detection gain. A binary "specialist helps" classifier
is not sufficient.

After one specialist is observed, the remaining transition estimator receives
the frozen projection of that observation. Small regularized logistic models
are the preferred first implementation. A shallow tree or gradient-boosted
model may be an ablation, but a neural policy or policy-gradient method is not
justified by the current sample size and two-step horizon.

The one-shot WarrantGate scores remain baseline features and may initialize the
gain estimators. They must not be treated as calibrated probabilities without
calibration testing.

### 8.2 Permitted feedback projection

For a successor WarrantLoop experiment, `P(o_e)` may contain only prospectively
frozen structured fields such as:

- construct ratings;
- confidence;
- disposition;
- `cannot_judge` indicators;
- `requested_expertise`;
- serious-error flag-family indicators or counts;
- schema-validity and inference-failure indicators.

It must exclude:

- source text and quotations;
- free-form rationale;
- intended flaw type or note;
- human/adjudicated judgments;
- final-grader results;
- held-out outcomes;
- protected attributes;
- cross-packet memory created during evaluation.

Specialist observations are forbidden by the current WarrantRoute v1 contract.
The list above is authorized only after a new WarrantLoop successor contract is
prospectively frozen.

### 8.3 No hidden verifier call

The v0 progress monitor is the calibrated gain estimator, not another LLM. A
free-form verifier that reads the packet and judges whether the flaw has been
found would function as an additional reviewer and would make the cost
comparison unfair. If an LLM verifier is studied later, it must:

- be declared as a separate action with its own token and latency cost;
- use a frozen prompt and observation schema;
- be separated from the final grader;
- appear in an ablation rather than silently inside WarrantLoop.

The existing `prompts/verifier_v1.md` is a construction-comparison verifier. It
is not a WarrantLoop progress verifier and must not be reused under that name.

## 9. Exact data flow

```text
blinded packet
  -> generalist role call
  -> source-free projection P(o_G)
  -> first WarrantLoop decision
       -> STOP_G -------------------------------------> terminal G
       -> ACQUIRE_BOTH -> M and D calls -------------> terminal B
       -> ACQUIRE_M -> P(o_M) -> second decision
              -> STOP_M ------------------------------> terminal M
              -> ACQUIRE_D_TO_B -> D call -----------> terminal B
       -> ACQUIRE_D -> P(o_D) -> second decision
              -> STOP_D ------------------------------> terminal D
              -> ACQUIRE_M_TO_B -> M call -----------> terminal B
  -> apply the unchanged route-to-flag reducer
  -> open private truth only in the scorer
```

The role prompts remain stateless and independent: specialists do not see the
generalist review or each other's reviews. Only the controller sees their
structured projections. Once the development all-role output bank is complete,
this permits exact offline replay and avoids turning the first experiment into
multi-agent debate.

## 10. Offline replay before new model calls

The existing pipeline already generates all three role outputs independently
for each model and packet. That makes a clean first experiment possible without
new adaptive prompts:

1. Split packets by source group before any policy fitting.
2. Treat the generalist output as initially visible.
3. Reveal cached specialist projections only when the simulated policy acquires
   that specialist.
4. Derive marginal-gain labels from the development truth map.
5. Fit and calibrate the gain estimators on development folds only.
6. Select `lambda`, `tau_stop`, and tie rules on validation folds only.
7. Freeze the complete policy and hashes.
8. Replay it once on untouched audit data.

This replay estimates a policy over independent role calls. It does not support
claims about conversational debate, role-to-role persuasion, or iterative text
repair.

## 11. Data splitting and leakage controls

The minimum safeguards are:

- group splits by original source or conversation cluster;
- no excerpt, speaker bundle, or source cluster shared across fitting and
  evaluation when provenance permits grouping;
- corpus-specific reporting plus a macro average;
- leave-one-corpus-out development checks for transfer;
- model-specific reporting because Qwen, Llama, and Gemma have different error
  and confidence profiles;
- no cost, threshold, route, or feature change after audit outcomes are seen;
- no persistent Reflexion-style memory across evaluation packets;
- policy and projection hashes in every route trace.

The preferred initial policy shares the same architecture and route semantics
across model profiles but calibrates probabilities per frozen model profile.
Pooling models without model-aware calibration is a secondary ablation, not the
default.

## 12. Failure and termination contract

Every run terminates because specialist acquisition is monotone and finite.
Required stop reasons are:

```text
expected_gain_below_threshold
budget_exhausted
both_specialists_acquired
no_valid_action
policy_input_invalid
```

Required execution behavior:

- never acquire the same role bundle twice in v0;
- never alter the frozen number of stateless repetitions in response to a
  packet result;
- never retry a schema-valid review merely because the controller dislikes it;
- retry only transport or schema failures under a separately frozen retry rule;
- never substitute generalist flags for a failed selected specialist;
- record failed selected roles as failed and apply the frozen failure policy;
- never turn a timeout into an undeclared route change;
- cache role outputs by packet, role, model, prompt hash, and seed;
- enforce a hard token/call/wall-time budget;
- preserve an append-only route trace.

These rules adapt useful loop-engineering practices while keeping scientific
control flow deterministic and auditable.

## 13. Long-document adaptation

Packet-level sequential acquisition and segment-level mode switching answer
different questions:

- **WarrantLoop**: after observing one role, is another role worth acquiring?
- **WarrantGate-Adaptive**: should adjacent document segments use different
  modes?

They should first be evaluated separately. A later hierarchical extension may
run a short WarrantLoop for each segment and use a document-level budget:

```text
sum over segments and acquired roles of c(role) <= B_document
```

The segment policy may retain the existing switching cost:

```text
score_t(r) = local_value_t(r) - eta_switch * I[r != r_(t-1)]
```

The combined system must also freeze segmentation, segment aggregation, and the
allocation of a shared document budget. It is too complex for the first
WarrantLoop experiment and should remain a later ablation.

## 14. Evaluation plan

### Primary comparison

Keep the current Table 3 unchanged:

```text
Generalist / Fixed role / All roles / WarrantRoute
```

Evaluate WarrantLoop in a separate table or ablation:

```text
Generalist
Fixed role
All roles
WarrantRoute (one-shot WarrantGate)
WarrantLoop (sequential acquisition)
Random budget-matched routing
Fixed cascade M->D
Fixed cascade D->M
Oracle minimum-cost route (upper bound only)
```

### Primary outcomes

- intended-flaw recall with a 95% interval;
- mean specialist role acquisitions and actual model calls per packet;
- mean total reviewer calls, tokens, and wall time;
- recall at matched reviewer cost;
- cost at matched recall;
- cost-adjusted utility over a prospectively frozen `lambda` grid;
- route and transition distributions;
- regret against the oracle minimum-cost route;
- Brier score, calibration error, and reliability plots for transition gain and
  harm probabilities;
- schema/transport failure and forced-stop rates.

### Statistical comparison

Use paired packet-level comparisons because every method is evaluated on the
same packet bank. Report per-corpus results and a source-cluster bootstrap for
recall and cost differences. McNemar-style paired detection tests may be a
secondary check. Hyperparameters and the selected operating point must come
from development folds, never from the final audit table.

If H2 is confirmatory, define a paired non-inferiority margin for
`Recall(WarrantLoop) - Recall(All roles)` before audit access and perform a power
or precision analysis for that margin. The balanced `n=100` cells are working
diagnostics unless they meet that prospectively declared precision target.

### Diminishing-return point

Sweep `lambda` or the acquisition threshold to form a recall-cost frontier. The
efficiency point is the least-cost operating point whose recall is within a
prospectively frozen tolerance of the maximum or All-roles recall. A one-standard-
error rule is a defensible alternative. The tolerance or selection rule must be
frozen before audit results are opened.

This directly tests whether additional reviewer calls become inefficient rather
than assuming that more reviewed packets or more agents are always better.

## 15. Hypotheses

The recommended preregistered hypotheses are:

- **H1:** WarrantLoop improves recall-cost utility over one-shot WarrantRoute.
- **H2:** WarrantLoop is non-inferior to All roles under a prospectively frozen
  recall margin while using fewer mean specialist calls.
- **H3:** The second specialist has positive marginal value on a restricted
  subset of packets, rather than uniformly across the dataset.
- **H4:** Calibrated structured role observations outperform routing from raw
  self-reported confidence alone.

The later segment-aware study may add:

- **H5:** Hierarchical segment routing improves recall-cost utility on mixed or
  long documents relative to one packet-level route.

## 16. Required ablations

- no specialist-feedback projection: one-shot WarrantGate;
- confidence only;
- no action costs;
- no coordination cost;
- fixed first specialist order;
- always acquire both specialists;
- random routing matched on route counts and cost;
- pooled calibration versus model-profile calibration;
- packet-only versus segment-aware routing;
- optional LLM progress verifier with its cost made explicit.

## 17. Designs not selected

### Unbounded self-refinement

Rejected because the task is flaw detection rather than document rewriting,
self-verification is not reliably corrective, and unbounded repetition obscures
cost and stopping.

### Debate on every packet

Rejected as the default because it collapses toward All roles, raises cost, can
introduce anchoring or erroneous consensus, and does not test selective routing.

### Full RL or a general POMDP solver in v0

Rejected as unnecessary complexity. The maximum specialist horizon is two, and
a fully populated development all-role bank permits supervised counterfactual
labeling and exact enumeration.

### Cluster/prototype router as the loop controller

Kept as a robustness baseline. Current development sets may not provide stable
mode-level prototypes across corpora and models, and distance to a prototype
does not directly encode reviewer cost or stopping value.

### Same-model free-form judge as the stop rule

Rejected because it adds an undeclared reviewer, may share the reviewed model's
error, and confounds routing quality with judge quality.

## 18. Implementation sequence

### Phase A: offline replay prototype

- [x] define the working successor source-free projection schema;
- [x] build progressively revealed replay states from cached role outputs;
- [x] derive development-only marginal-gain labels;
- [x] fit paired improvement/harm logistic estimators with an explicit
  rare-class constant-risk fallback;
- [x] export hashed route traces and score only after routes exist;
- [x] run a separate four-corpus working replay with Dreaddit out-of-fold routes
  and an unchanged Dreaddit-only transfer policy for the other corpora;
- [ ] export the complete recall-cost frontier;
- [ ] run every baseline and ablation without new role calls.

The implementation is
`scripts/run_working_warrantloop.py`, its development-only configuration is
`config/working_warrantloop_v0_policy.json`, and its execution boundary is
`protocol/working_warrantloop_v0_execution_contract.md`. The validated smoke
record is retained under
`Storage/rq2_personal_local_diagnostic/warrantloop_working/smoke_n10_20260902_v4/`.
It used 75 train, 15 validation, and 10 source-disjoint smoke-test packets for
each of the three model profiles, made no new LLM calls, and remains private
exploratory software evidence only.

The subsequent four-corpus replay is implemented by
`scripts/run_working_warrantloop_multicorpus.py` with
`config/working_warrantloop_multicorpus_v0.json`. It produced 1,200 unique
routes, 12 WarrantRoute-S metric rows, and a separate 60-row working comparison
without modifying the completed 48-row Table 3. The observed controller never
acquired the second specialist. This is a substantive working result about the
selected operating point, not evidence that the second decision is unnecessary
in a fresh prospective study.

### Phase B: prospective development execution

- freeze role prompts, model profiles, state schema, action costs, thresholds,
  tie rules, failure behavior, and budgets;
- execute only the role calls selected by WarrantLoop;
- compare real saved cost and latency with offline replay predictions.

### Phase C: confirmatory promotion

- pass calibration and route-stability gates;
- seal policy and implementation hashes before held-out access;
- run one untouched audit evaluation;
- keep LLM-as-Judge quality analysis separate from target-flaw scoring.

### Phase D: segment-aware hierarchy

- freeze semantic segmentation and document budget allocation;
- combine local sequential acquisition with adjacent-segment switching costs;
- evaluate only after packet-level WarrantLoop is stable.

## 19. Separation from the operational experiment loop

The repository also uses operational loops that wait for reviewer jobs, retry
invalid artifacts, validate counts, and publish a complete table. Those loops
improve execution reliability but are not a study method and must not affect
which packet-level result is counted.

Use distinct language:

```text
WarrantLoop                 = scientific sequential reviewer-routing method
resilient execution loop    = operational queue/retry/validation machinery
```

## 20. Promotion checklist

WarrantLoop cannot become manuscript evidence until a successor freeze binds:

- terminal route semantics;
- state and observation-projection schemas;
- development/audit source-group split;
- gain-model family, features, preprocessing, regularization, and calibration;
- action costs and units;
- budget and stopping threshold;
- first-action and tie rules;
- failure and retry rules;
- route-trace schema;
- model-profile policy;
- qualification metrics and minimum event counts;
- policy, prompt, implementation, and data hashes;
- prohibition on cross-packet evaluation memory;
- separation of routing feedback, final truth scoring, and LLM-as-Judge output
  quality scoring.

Until then, every WarrantLoop result must be labeled exploratory/working.

## 21. References

- Yao et al. (2023), [ReAct: Synergizing Reasoning and Acting in Language
  Models](https://arxiv.org/abs/2210.03629), ICLR 2023.
- Shinn et al. (2023), [Reflexion: Language Agents with Verbal Reinforcement
  Learning](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf),
  NeurIPS 2023.
- Madaan et al. (2023), [Self-Refine: Iterative Refinement with
  Self-Feedback](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html),
  NeurIPS 2023.
- Huang et al. (2024), [Large Language Models Cannot Self-Correct Reasoning
  Yet](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html),
  ICLR 2024.
- Gou et al. (2024), [CRITIC: Large Language Models Can Self-Correct with
  Tool-Interactive Critiquing](https://proceedings.iclr.cc/paper_files/paper/2024/file/fef126561bbf9d4467dbb8d27334b8fe-Paper-Conference.pdf),
  ICLR 2024.
- Chen, Zaharia, and Zou (2024), [FrugalGPT: How to Use Large Language Models
  While Reducing Cost and Improving Performance](https://arxiv.org/abs/2305.05176),
  TMLR 2024.
- Ong et al. (2025), [RouteLLM: Learning to Route LLMs from Preference
  Data](https://mlanthology.org/iclr/2025/ong2025iclr-routellm/), ICLR 2025.
- Chuang et al. (2025), [Learning to Route LLMs with Confidence
  Tokens](https://proceedings.mlr.press/v267/chuang25b.html), ICML 2025.
- Contardo, Denoyer, and Artieres (2016), [Sequential Cost-Sensitive Feature
  Acquisition](https://arxiv.org/abs/1607.03691).
- Li and Oliva (2025), [Towards Cost Sensitive Decision
  Making](https://proceedings.mlr.press/v258/li25h.html), AISTATS 2025.
- Graves (2016), [Adaptive Computation Time for Recurrent Neural
  Networks](https://arxiv.org/abs/1603.08983).
- Banino, Balaguer, and Blundell (2021), [PonderNet: Learning to
  Ponder](https://arxiv.org/abs/2107.05407).
- Zhuge et al. (2024), [GPTSwarm: Language Agents as Optimizable
  Graphs](https://proceedings.mlr.press/v235/zhuge24a.html), ICML 2024.
- Liu et al. (2024), [A Dynamic LLM-Powered Agent Network for Task-Oriented
  Agent Collaboration](https://openreview.net/forum?id=XII0Wp1XA9), COLM 2024.
- Fan, Yoon, and Ji (2026), [iMAD: Intelligent Multi-Agent Debate for Efficient
  and Accurate LLM Inference](https://ojs.aaai.org/index.php/AAAI/article/view/40181),
  AAAI 2026.
- Golovin and Krause (2011), [Adaptive Submodularity: Theory and Applications
  in Active Learning and Stochastic
  Optimization](https://arxiv.org/abs/1003.3967), JAIR 42.
- Snell et al. (2025), [Scaling LLM Test-Time Compute Optimally Can Be More
  Effective than Scaling Parameters for
  Reasoning](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b623663fd9b874366f3ce019fdfdd44-Abstract-Conference.html),
  ICLR 2025.
- Lulla et al. (2026), [Loop Engineering: Building Blocks, Adoption, and
  Impact](https://arxiv.org/abs/2608.21884), exploratory preprint/under review.
- Kim (2026), [Pool-Gated Retrieval: Beyond Retrieval-Augmented Generation
  Toward Accountable Evidential
  Admission](https://www.preprints.org/manuscript/202606.0414), non-peer-reviewed
  preprint cited only for the WarrantGate/warrant-loop naming collision.
