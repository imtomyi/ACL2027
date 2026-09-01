# RQ2 personal-local one-packet smoke contract v1

Status: active only for a private, one-packet WarrantRoute engineering
diagnostic. This contract does not modify or authorize the frozen v2.2
qualification, and it does not broaden the source-free v2.3 prompt-limit
diagnostic.

Every outcome is labeled `diagnostic_not_manuscript_evidence`. Runner-written
copies of source text, source-derived prose, raw requests, and raw model
responses remain under the private
`Storage/rq2_personal_local_diagnostic/` tree. Source-bearing prompts are
transmitted only to the policy-bound numeric-loopback Ollama service. They must
not be emitted to the runner console, copied into a manuscript, submitted,
published, redistributed, released, or sent to a human reviewer.

Ollama service logging is an operator-managed boundary that this API does not
expose or attest. A source-bearing run requires a single-user local Ollama
process with debug or request-body logging disabled. The runner's sanitized
report makes no claim about independently configured service logs.

## Minimum semantic model input

The only source content sent to a model is one intact Dreaddit
`development_train` packet containing six excerpts from six disjoint post
clusters. One excerpt is not a valid WarrantRoute test because the construction
jointly evaluates support, counterevidence, context, boundary conditions, and
source independence.

This limit applies to model processing, not to integrity verification or
deterministic selection. The exact personal-local policy validator reads both
bound corpus files as bytes to verify their frozen hashes without parsing or
emitting records. The inherited deterministic selector then decodes the full
indexed Dreaddit development split to rank eligible post clusters. Exactly six
selected excerpts reach Qwen. If Qwen constructs a valid base, Gemma sees the
corresponding complete six-position compact view. No AGYW record is decoded or
sent to a model.

Selection reuses the frozen seed and cluster rule. It excludes the 90 source
clusters committed by the frozen v1 and shared v2 predecessor selections. It
also reserves the first ten packets that the v2.2 qualification would select
and uses only deterministic selection rank 11. Thus this smoke packet is
disjoint from those ten qualification packets and cannot be substituted into
their denominator.

## Boundary order

Before decoding a corpus record or opening a predecessor selection under
`Storage/`, the runner must validate every source-free binding, the
numeric-loopback local service, both required model identities, native context
capacity, and the full v2.3 chunked source-free canary. After that canary
passes, the runner validates the source-free policy boundary and invokes the
exact personal-local policy validator. Only after that validator accepts the
policy and live hashes may the runner validate predecessor selection
commitments and decode the Dreaddit development split.

The diagnostic creates its output directory only after all preceding checks
pass. The directory and every file use private permissions.

## Real-data process

The real-data process makes at most two generated calls and never retries,
regenerates, replaces, or cherry-picks a packet:

1. Qwen receives the frozen base-generation instruction and the intact
   six-position packet. Its response must pass the frozen generation schema.
2. Code maps the position plan, enforces the frozen structural invariants, and
   builds the frozen evaluator item.
3. If construction is valid, Gemma receives the frozen compact
   base-admissibility instruction and the complete six-position view. Its flat
   response must pass the frozen schema, deterministic v2.2 adapter, canonical
   schema, and frozen deterministic acceptance rule.

If Qwen returns `not_constructable` or fails a deterministic construction
invariant, the diagnostic records that outcome and stops without calling
Gemma. This is a valid terminal semantic outcome, not permission to select a
different packet.

## Prompt-limit invariant

Every real-data Ollama request sets top-level `truncate=false` and
`shift=false` and requests a 16,384-token context. Ollama rejects an input that
alone exceeds that context before generation. The public local API provides no
exact pre-generation token-count endpoint, so the runner validates each
successful response's reported prompt count against the role's frozen maximum
output tokens plus a 512-token safety margin. A response without that headroom
or with a done reason other than exact `stop` is terminal and is never retried.

The intact six-excerpt packet is an atomic semantic unit. It is never split,
summarized, clipped, or reduced. The exact Ollama input-overflow error is
terminal before generation. Output-context exhaustion or insufficient audited
headroom is terminal after the single attempt. A task-specific source-bearing
map and reducer would require a separate contract.

## Sanitized result

The user-facing and aggregate result may contain only dataset and split names,
fixed hashes, opaque commitments, counts, prompt byte and token accounting,
stage statuses, role counts, finite reason codes, boolean checks, readiness
position anchors, and artifact hashes. It must set `contains_source_text` to
false. Generated themes, claims, explanations, boundary-condition prose,
excerpt text, local context, record identifiers, and raw model content remain
private.

Operational success means the authorized stages that were reachable completed
with valid structured interfaces. It does not mean the constructed base was
semantically admitted. The semantic decision is reported separately. Neither
outcome is manuscript evidence.
