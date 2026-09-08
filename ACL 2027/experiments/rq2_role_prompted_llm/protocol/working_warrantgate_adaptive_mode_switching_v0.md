# WarrantGate adaptive mode switching note v0

Status: working implementation available, not Table 3 default, not manuscript
eligible.

Date: 2026-09-02

## Purpose

The current WarrantGate v0 policy chooses one route for one review packet. That
is enough for Table 3 development exports, but long documents may shift across
sections: a background paragraph can be general, a methods paragraph can require
qualitative-methods expertise, and a discussion paragraph can require domain
context. This note records how WarrantGate could be extended so reviewer mode can
change inside a document without corrupting the current packet-level experiment.

## Core idea

Use WarrantGate as a local router over ordered document segments:

```text
document -> segments x_1 ... x_T
segment x_t -> scores S_G, S_M, S_D, S_B
segment x_t -> route a_t in {generalist, qualitative_methods, domain, both}
selected reviewers inspect only the segments routed to them
segment-level flags are merged into one document-level review
```

The route is still chosen before using specialist outputs. Specialist judgments
can affect flaw detection, but must not be fed back into routing for the same
evaluation item.

## Segment units

The segment should be the smallest unit that preserves local argumentative
meaning:

- paragraph, for short social or conversational examples;
- turn bundle, for dialogue or debate data;
- section or subsection, for long research-style documents;
- sliding window only as a fallback when document structure is absent.

Each segment keeps a stable `segment_id`, parent `packet_id`, order index, and
source-free structural features. The source text can be shown to the selected
reviewer, but the router feature projection must remain source-free if the
experiment is using the current source-free boundary.

The working implementation starts with packet-level WarrantGate features and
adds source-free segment adjustments. These adjustments let ordered segments
shift the method/domain scores when, for example, a segment has speaker/turn
context, local context, repeated sources, an evidence/context candidate role, or
a position that suggests synthesis. The `candidate_role` field may be used only
as a packet-structure label, such as `cited`, `support`, `context`, or
`context_only`; it must not encode the intended flaw type. If future packet
builders add a precomputed `router_features` object to each segment, those
numeric features can be used by the adaptive router without reading source text.

## Switching rule

A naive per-segment argmax may switch modes too often. The adaptive version
should use a switching penalty and a small amount of hysteresis:

```text
base_score_t(a) = WarrantGateScore(a, x_t)
switch_cost(a_prev, a) = 0 if a = a_prev else eta

a_t = argmax_a [ base_score_t(a) - switch_cost(a_{t-1}, a) ]
```

Optional stability constraints:

```text
switch only if score_t(new) - score_t(current) >= tau_switch
keep a selected specialist mode for at least k adjacent segments
cap the total specialist budget per document
```

This makes mode changes meaningful rather than noisy. For example, a document
can stay in `generalist` through ordinary context, switch to
`qualitative_methods` in the methods-heavy section, then switch to `domain` or
`both` only when the local signals justify the added cost.

## Document-level aggregation

The review output should preserve where each decision came from:

```text
packet_id
segment_id
route
selected_roles
detected_flags
flag_source_role
```

Document-level flaw detection is then the union of segment-level flags with
deduplication by flaw type. A later scorer can report both:

- segment-level detection quality;
- document-level detection quality.

## Relationship to Table 3

Do not use this adaptive version for the current Table 3 working row unless a
new explicit experiment variant is created. The current Table 3 WarrantRoute row
remains packet-level WarrantGate v0. The working scorer can add this variant as
an optional `Adaptive WarrantRoute` row when an adaptive route file is supplied.

If evaluated later, the adaptive version should appear as a separate row or
ablation, for example:

```text
Generalist
Fixed role
All roles
WarrantRoute
Adaptive WarrantRoute
```

## What must be frozen before manuscript use

Before using adaptive switching in a confirmatory table, the project must freeze:

- segmentation rule;
- segment feature schema;
- initial state;
- switching penalty `eta`;
- switch margin `tau_switch`;
- minimum dwell length `k`, if used;
- specialist budget, if used;
- segment-to-document aggregation rule;
- failure behavior when a selected specialist output is missing;
- route record and seal schema.

## Recommended path

Keep packet-level WarrantGate v0 as the Table 3 implementation. Build adaptive
mode switching later as `WarrantGate-Adaptive v0`, first on development data
only. It should be treated as a separate experiment because it answers a
slightly different question: not only whether routing helps, but whether local
section-aware routing is more efficient than one route for the whole packet.

## Working implementation

The current working implementation is:

```text
experiments/rq2_role_prompted_llm/scripts/build_working_warrantgate_adaptive_routes.py
```

The policy file is:

```text
experiments/rq2_role_prompted_llm/config/working_warrantgate_adaptive_v0_policy.json
```

The script writes packet-level route records that include a `segment_routes`
trace. Each segment record stores only route metadata, feature values, component
scores, and selected roles; it does not write source text.

The normal local pipeline can include this variant with:

```text
python3 experiments/rq2_role_prompted_llm/scripts/run_working_table3_pipeline.py --include-adaptive-warrantgate
```

The all-corpus queue can include it with:

```text
python3 experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py --include-adaptive-warrantgate
```
