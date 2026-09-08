# Decision: use WarrantGate v0 as the working WarrantRoute router

Decision date: 2026-09-01

Status: selected working candidate, not manuscript eligible.

## Decision

Use **WarrantGate v0** as the working implementation of the WarrantRoute row
for Table 3 development exports.

WarrantGate is a cost-sensitive four-action gating policy over reviewer modes:

```text
A = {G, M, D, B}
G = generalist/researcher review
M = qualitative-methods review
D = domain-context review
B = both specialist reviews
```

The selected working scoring rule is:

```text
S_G(x) = g(x)
S_M(x) = m(x) - c_M
S_D(x) = d(x) - c_D
S_B(x) = min(m(x), d(x)) + i_MD(x) - (c_M + c_D + c_B)

route(x) = argmax {S_G, S_M, S_D, S_B}
```

The `min(m,d)` term is intentional. A route to both specialists should require
evidence on both axes, not only a very large method score or a very large domain
score. This keeps `both` from becoming a disguised all-expert route.

## Why This Choice

This is the best current fit because it:

- directly represents all four Table 3 actions;
- matches the cost-quality structure used in LLM routing and gating work;
- keeps expert time explicit through action costs;
- remains interpretable enough to defend in the paper;
- avoids relying on unstable cluster/prototype estimates while development data
  are still small;
- can be evaluated as a deterministic route proposal without using answer keys
  or specialist outcomes.

## What It May Use

The working route may use only pre-specialist signals:

- the first-stage generalist rating projection;
- source-free packet structure, such as excerpt/source/speaker counts;
- the generalist `requested_expertise` field as one signal, not as the whole
  route.

## What It Must Not Use

The route must not use:

- source text;
- `known_intended_flaw_type` or any answer-key field;
- qualitative-methods or domain reviewer outputs;
- human responses, adjudication, repair outcomes, or held-out outcomes;
- protected participant attributes.

## Current Working Artifacts

Policy config:

```text
experiments/rq2_role_prompted_llm/config/working_warrantgate_v0_policy.json
```

Design note:

```text
experiments/rq2_role_prompted_llm/protocol/working_warrantgate_v0_design.md
```

Route builder:

```text
experiments/rq2_role_prompted_llm/scripts/build_working_warrantgate_routes.py
```

Table 3 scorer integration:

```text
experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py
```

## Current Dreaddit Dev100 Sanity Check

Using completed Dreaddit dev100 generalist outputs, the selected v0 policy
produced the following route distribution:

```text
qwen3:8b       G=14, M=77, D=7,  B=2
llama3.1:8b   G=88, M=5,  D=7,  B=0
gemma3:4b      G=6,  M=23, D=30, B=41
```

For qwen3:8b, where all three role outputs were available at the time of this
decision, the Table 3 working check was:

```text
Generalist    66/100 = 0.66
Fixed role    73/100 = 0.73
All roles     74/100 = 0.74
WarrantRoute  73/100 = 0.73
```

These values are working diagnostics only.

## Later Upgrade Path

Before manuscript use, WarrantGate must be promoted through a formal successor
freeze. That freeze must prospectively bind:

- feature names and encoding;
- missing-value rules;
- costs and budget;
- training or threshold target;
- route tie rule;
- failure action;
- qualification gate;
- policy artifact hash;
- pre-held-out access seal.

Prototype or nearest-centroid routing remains a backup/ablation idea, not the
main WarrantRoute candidate, unless enough development examples per mode and
corpus are available to show stable centroids.
