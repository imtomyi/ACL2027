# WarrantGate working router v0

Status: working diagnostic, not manuscript eligible.

## Purpose

WarrantGate is a candidate implementation of WarrantRoute's four-action router.
It is intended for local Table 3 development runs only. The formal
`qwen3_warrantroute` freeze still blocks policy inference, route sealing,
held-out access, and manuscript evidence until the feature set, training target,
costs, thresholds, and qualification gate are frozen prospectively.

## Framing

The routing problem is an instance-wise model-selection problem over reviewer
modes rather than model sizes. This follows the same decision-theoretic shape as
cost-quality LLM routing and mixture-of-experts gating: for each packet, choose
the action with the best expected utility after accounting for review cost.

The action set is

```text
A = {G, M, D, B}
G = generalist/researcher review
M = qualitative-methods review
D = domain-context review
B = both specialist reviews
```

The working policy computes four scores:

```text
S_G(x) = g(x)
S_M(x) = m(x) - lambda c_M
S_D(x) = d(x) - lambda c_D
S_B(x) = min(m(x), d(x)) + i_MD(x) - lambda(c_M + c_D + c_B)

route(x) = argmax_a S_a(x)
```

Here `g(x)` is generalist sufficiency, `m(x)` is methodological need, `d(x)` is
domain-context need, and `i_MD(x)` is the interaction gain for cases where both
forms of expertise appear jointly useful. The `min(m,d)` bottleneck is
intentional: a route to both should require evidence that neither specialist
axis is negligible, rather than letting one very strong axis drag the packet
into the most expensive action.

## Allowed working signals

The v0 feature projection may use:

- the first-stage generalist rating projection: confidence, disposition,
  construct scores, `cannot_judge`, `serious_error_flags`, and
  `requested_expertise`;
- source-free packet structure: number of displayed excerpts, number of source
  IDs, number of speaker IDs, and number of cited excerpt IDs.

The v0 feature projection must not use:

- source text or rationales;
- `known_intended_flaw_type`, `known_intended_flaw_note`, or other answer-key
  fields;
- qualitative-methods or domain reviewer outputs;
- human responses, adjudication, repair results, held-out outcomes, or protected
  participant attributes.

## Why this is the main candidate

This policy is more natural than a pure nearest-centroid router for the current
data size. It directly models the four actions, it exposes the expert-time
trade-off, and every contribution to the route can be audited. Prototype routing
can remain a later robustness check once there are enough development examples
per mode and corpus.

## Development target

For a later frozen manuscript router, the target should not be "which flaw type
is present." The cleaner target is the best route under a costed utility:

```text
y*(x) = argmax_a [ detection_gain_a(x) - lambda review_cost_a ]
```

In the current working pipeline, before human adjudication exists, WarrantGate
v0 is only a deterministic policy over pre-specialist LLM-reviewer signals.
It is a route proposal, not a verified learned router.

## Evaluation

Table 3 should continue to compare:

```text
Generalist / Fixed role / All roles / WarrantRoute
```

When using WarrantGate v0 as the WarrantRoute row, the export should record the
policy ID and the selected route per packet. The route is frozen before applying
method/domain outputs. The row is still working-only until the policy is frozen
under the formal WarrantRoute contract.
