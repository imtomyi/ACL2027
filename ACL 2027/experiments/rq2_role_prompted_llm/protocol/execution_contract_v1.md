# RQ2 role-prompted LLM execution contract (`rq2-role-review-contract-v1`)

**Legacy status: inactive and forbidden for current execution.** This file is
retained only as a one-packet engineering record. The sole active contract is
`personal_local_main_contract_v2.md`. No command, authorization statement, or
cloud path in this v1 record overrides the exact current personal-local policy.

Status: frozen for the private local Dreaddit-train development shakedown only.
It is not the future three-repeat main-study freeze and does not make any output
manuscript-eligible.

## 1. Question and endpoint

The bounded task follows the active manuscript. RQ2 evaluates the
error-detection recall of frozen, role-prompted LLM reviewer proxies on
controlled variants with locked target-flaw labels. The sole performance
quantity is target-flaw recall, `TP / N`, where `N` contains every eligible
flaw-bearing item. Ordinal ratings, rationale text, latency, tokens, and failure
types are diagnostic or operational records, not additional performance
metrics.

This contract tests prompt-conditioned model behavior. It does not assert that
the model possesses human expertise, replaces a human reviewer, or produces a
natural-output validity judgment without independent human evidence.

## 2. Active shakedown scope

Only the scope in `config/private_local_development_freeze.json` may execute:

- corpus: Dreaddit;
- split: official training split used as development data;
- selection: deterministic one-base-packet development slice, preserving the
  post/document cluster;
- variants: the five locked controlled-flaw families;
- actors: the three role-prompted instances of one frozen local reviewer model;
- repetitions: exactly one stateless call per item and role; and
- transport: loopback Ollama only, with no cloud, retrieval, search, or tools.

Dreaddit test, any held-out data, CaCHe/Cache2, fixed-role selection,
confirmatory estimation, and human comparisons are unauthorized. A runner must
fail closed if a record, requested mode, endpoint, model identity, prompt hash,
or repetition count falls outside this list.

## 3. Shared evaluator interface and blinding

Use the Direction J v1 guide, evaluator-item schema, and shared-rating schema
unchanged. The three roles receive byte-identical guide and evaluator-item
payloads. The payload must exclude the route, controlled-condition name,
target-flaw label, answer key, candidate-generation identity, human responses,
adjudication, other model outputs, and outcomes.

The only role difference is the prospectively frozen model-facing prompt.
Instruction-like source material is data, not executable instruction. Prompts,
configuration, logs intended for aggregation, and aggregate result artifacts
must contain no source text. A rationale should locate evidence with opaque IDs
and must not reproduce source wording.

The current schema stays actor-neutral. Sidecar run records identify three LLM
actors with `judge_role="primary"`:

| Actor | Prompted role | Prompt |
|---|---|---|
| `J_RQ2_G` | generalist | `prompts/generalist_v1.md` |
| `J_RQ2_M` | qualitative methods | `prompts/methods_v1.md` |
| `J_RQ2_D` | domain context | `prompts/domain_v1.md` |

Each observation records the actor ID, complete prompt hash, model manifest
identity and digests, settings, `rating_repetition`, exact semantic-input hash,
request timing, response hash, validation state, and terminal failure state.

## 4. Role prompts

The generalist lens applies every construct and error category evenly without
assuming specialist knowledge. The methods lens prioritizes claim--evidence
warrant, analytic-contract fit, source coverage and concentration,
counterevidence, negative cases, boundary preservation, and scope calibration.
The domain lens prioritizes packet-stated meanings, qualifications,
terminology, participant differences, sensitive or diagnostic overreach, and
contextual flattening.

Every prompt states that its lens directs attention only, does not imply a flaw,
and must not force a flag. The model is always identified as a role-prompted
proxy rather than a human expert. No role may add outside facts.

## 5. Locked target-to-flag rule

Scoring uses only the exact `serious_error_flags` value mapped below:

| Controlled target flaw | Required flag |
|---|---|
| `unsupported_evidence` | `unsupported_inference` |
| `source_concentration` | `hidden_source_concentration` |
| `counterevidence_loss` | `lost_negative_case` |
| `contextual_flattening` | `contextual_flattening` |
| `unsupported_abstraction` | `unsupported_abstraction` |

An observation detects the target only when its selected flag set contains the
exact mapped flag. Other flags may coexist. A correct-sounding rationale
without the exact flag is a miss. `other`, accept, a wrong or missing flag,
cannot-judge, abstention, invalid JSON or schema, timeout, filtering, truncation,
or terminal error is a miss and remains in the denominator. Natural or clean
items are outside this recall denominator.

## 6. Frozen route-output rule

All three role prompts run on every eligible item before the frozen router is
applied offline. The reviewer models never see the route.

| Frozen router output | Selected model flag set |
|---|---|
| `none` | generalist |
| `qualitative_methods` | methods |
| `domain` | domain |
| `both` | union of methods and domain flags |

For `both`, store a derived route record that links both source observation IDs
and the unioned flag set; do not manufacture a merged `shared_rating`. Detection
by either selected specialist role is sufficient. Do not include generalist in
a specialist route, substitute generalist after specialist failure, or change a
route based on model outputs.

The active shakedown may verify this derivation mechanically, but it cannot
train, tune, validate, or freeze the router.

## 7. Repetitions

The active shakedown makes exactly one call for each item-by-role cell. That
call is an engineering observation only. It cannot be reused as a selectively
chosen best response, a confirmatory observation, or evidence that one repeat
is adequate.

The separately authorized future main protocol requires exactly three
independent, stateless calls per item and role. Repetition 1 is the sole primary
observation. Repetitions 2 and 3 support a prespecified stability sensitivity;
a flag enters the sensitivity ensemble when at least two of three repetitions
contain it, after which the same route rule applies. Repeats are never treated
as independent items and the response closest to the target may never be
selected.

## 8. Future fixed-role comparator and inference

The current one-packet shakedown cannot choose the fixed-role comparator. In a
separately frozen, family-balanced Dreaddit-train development set, the main
protocol will compute repetition-1 micro recall for generalist, methods, and
domain, choose the highest, and resolve exact ties as `generalist > methods >
domain`. That role must be frozen before any Dreaddit-test or CaCHe access and
must never be reselected from held-out results, ensemble repeats, latency,
cost, or ordinal ratings.

For the future main analysis, report role-by-flaw and overall recall plus the
paired difference `WarrantRoute recall - frozen fixed-role recall`. Repetition
1 alone enters the primary estimate. Use 10,000 paired cluster-bootstrap
resamples, seed `20270826`, with percentile 95% intervals. Resampling preserves
the frozen Dreaddit post/document cluster or a connected component when packets
share posts. By-flaw intervals are descriptive; the sole confirmatory contrast
is the overall paired difference.

No interval or comparative inference is meaningful for this one-base-packet
shakedown.

## 9. Local model and request controls

The freeze pins Ollama `0.18.0`, local model `llama3.1:8b`, its local manifest
identity and digests, loopback service URL, context limit, `temperature=0`,
`top_p=1`, no generation seed, and maximum output length. Generator calls use
Ollama JSON-schema mode. Rating calls use Ollama JSON mode followed by local
validation against the complete frozen rating schema; the transport may not
narrow the schema's nullable or cannot-judge response space. No tool definition
may be supplied. Streaming and automatic semantic retries are disabled. A
transport retry may occur only if a later freeze explicitly defines it; no
retry may replace or erase the primary failure record.

The freeze also pins the runner file hash, Python version, and `jsonschema`
version. Requests use a proxy-disabled, redirect-denying loopback client.
Restricted request and raw-response artifacts are retained even when parsing or
schema validation fails; aggregate observation metadata records only sanitized
failure types and stages.

Any manifest, prompt, guide, schema, data-file, setting, or service-host drift
invalidates the freeze and stops execution.

## 10. Verification and eligibility

Shakedown output remains
`development_unverified_not_manuscript_eligible`, even when every response is
schema-valid. Independent verification must check at least:

1. real-corpus lineage, exact file hash, official train membership, and cluster
   preservation;
2. controlled-variant construction and the locked one-flaw target label;
3. identical blinded evaluator input across roles;
4. prompt, guide, schema, model manifest, and run-configuration hashes;
5. JSON-schema validation and complete failure accounting;
6. exact target-to-flag scoring and route derivation; and
7. denominator reconciliation against immutable observation IDs.

Manuscript eligibility additionally requires a prospectively frozen main-study
record, independent target verification, completion of the workspace's required
data-policy check, and an explicit eligibility decision. No script or person
may promote shakedown values automatically. Until then, manuscript fields stay
as explicit placeholders.
