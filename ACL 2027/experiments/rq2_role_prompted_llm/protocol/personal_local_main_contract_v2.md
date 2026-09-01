# RQ2 personal-local main diagnostic contract v2

Status: active personal-local execution contract. Every output is labeled
`private_personal_exploratory_not_for_publication` and
`diagnostic_not_manuscript_evidence`. No output may enter a manuscript,
submission, publication, release, redistribution, or human-review workflow.

## Frozen boundary

The only allowed transport is `http://127.0.0.1:11434` with proxies, redirects,
DNS, cloud processing, retrieval, and tools disabled. The generator is the
locally pinned `qwen3:8b`; the reviewer is the separately pinned
`llama3.1:8b`; and the independent blinded construction verifier is the pinned
`gemma3:4b`. Generator decoding is temperature 0 with a 1,536-token cap and
`think:false`. Reviewer decoding is temperature 0.2 with a 512-token cap and
three stateless calls seeded `2027082601`, `2027082602`, and `2027082603`.
Verifier decoding is temperature 0 with seed `2027082699` and a 768-token cap.
Truncation is a terminal validation failure.

The exact personal policy, its pinned validator, the source-free readiness
scope assessment, and independent live SHA-256 checks are all mandatory before
corpus JSON is parsed. Readiness records scope eligibility only; it is not an
external approval or an input-integrity substitute. The pre-run boundary
two-incident manifest is bound by hash, count, and status, and aggregate warnings
contain no snippet. The frozen source-free Dreaddit split index binds each line's
byte range and hash; the development loader decodes only indexed development
rows after verifying the complete file hash.

## Sampling and sequencing

Sampling seed `20260826` deterministically selects five base packets in each
lane. A Dreaddit packet contains six unique post clusters. Development and audit
selections are also required to be disjoint across lanes. An AGYW packet contains
six transcript-local speaker clusters from one focus group, and its five
packets use distinct focus groups. Each base packet produces exactly one
variant for each frozen flaw family: unsupported evidence, source
concentration, counterevidence loss, contextual flattening, and unsupported
abstraction.

Within a phase, the runner completes all Qwen construction calls before any
Gemma verification call, avoiding per-variant model swapping. Gemma receives
only blinded base and variant items. It never receives the target flaw,
construction note, family index, truth, filename semantics, or reviewer output.
No verifier rejection is regenerated, replaced, semantically retried, or
manually overridden.

The runner first constructs, verifies, and reviews only Dreaddit development. Review calls
within each phase are ordered by prompted role, then lane, item, and repetition;
the shared guide precedes item text. Repetition calls are stateless. Development
repetition-1 micro recall selects one fixed role with ties resolved
`generalist > methods > domain`. The selection and its hash seal must be
immutable before either held-out split is retained or prepared. Dreaddit audit
and AGYW heldout are then prepared, reviewed, and analyzed separately.

## Scoring and uncertainty

Frozen deterministic checks require unchanged packet metadata and evidence
content, self-consistent attribution and coverage, a materially changed
interpretation with unchanged theme name, and exact family topology. Unsupported
evidence changes exactly one context-only excerpt to support. Source
concentration retains the first of at least two independent support units,
demotes other supports, and preserves counterevidence. Counterevidence loss
demotes exactly the first countercase and preserves other roles. Contextual
flattening and unsupported abstraction preserve every evidence role.

Blinded Gemma must call the base warranted, the comparison clear, and the
variant a single material difference; it must return exactly the frozen target
as the sole flaw, no other material flaw, and exactly one valid opaque anchor
with the target's reason code. Invalid, unclear, wrong, compound, unchanged, or
otherwise flawed variants are quarantined before review. They are excluded,
not counted as misses, and acceptance counts and reasons are reported by lane
and family. The performance metric is `automated-target recall among
Gemma-screened variants`, never human-verified ground truth.

A target is detected only when the response is schema-valid, `cannot_judge` is
empty, and `serious_error_flags` contains the exact target-to-flag mapping. A
wrong flag, empty or invalid output, abstention, cannot-judge result, failure,
timeout, or truncation is a miss and remains in the denominator.

Repetition 1 is primary. The two-of-three sensitivity includes a flag only when
at least two of the three independently seeded responses contain it under the
same strict validity rule. The frozen personal-diagnostic router proxy maps the
generalist repetition-1 `requested_expertise` value as follows: `none` uses the
generalist output, `qualitative_methods` uses methods, `domain` uses domain, and
`both` uses the union of methods and domain flags. Invalid or terminal
generalist output routes to `none`. This proxy is not the manuscript's
unimplemented trained regularized router.

Reports include `TP/N`, recall, role-by-flaw summaries, WarrantRoute-proxy minus
fixed-role paired differences, both discordant counts, failures, prompt and
output token counts, and latency. The cluster bootstrap uses 10,000 resamples
and seed `20270826`; a 95% interval is marked not estimable when fewer than five
independent clusters are available. Development, Dreaddit audit, and AGYW
heldout remain separate descriptive analyses, never confirmatory claims.

## Storage, resume, and cost

All artifacts remain below `Storage/rq2_personal_local_diagnostic/` with
single-user permissions. Source-bearing packet, request, response, and
observation artifacts are restricted. Stdout, stderr, run manifests, seals,
selection commitments, and aggregate analyses contain no source text. Calls
and observations are checkpointed once; explicit resume requires the same
freeze, policy, runner, and fixed-role seal. Every loaded request, response,
success, item, construction, verification, and observation checkpoint is
reconstructed and hash/schema checked. Seals require a complete exact inventory;
all physical attempts, retries, failures, tokens, and latency are aggregated.

Locally served model calls record `api_cost_usd: 0.0` and
`energy_and_hardware_cost_not_measured: true`. The runner does not infer an
electricity or hardware cost.
