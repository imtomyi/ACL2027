# Direction J shared evaluator interface

Version: `direction-j-shared-interface-v1`  
Status: prospective interface contract for an approved real-data study; both
real-data lanes are currently blocked before access; no empirical ratings or
results  
Applies to: one blinded theme-and-evidence item rated by either a registered human actor or a registered LLM actor

## Purpose and precedence

Direction J asks whether an LLM can perform the same bounded first-stage rating
task as Charlie and, later, independent humans. Comparability requires more than
similar questions. The human and LLM must receive the same evidence, candidate
claim, context, source-coverage information, and rating anchors, and they must
return the same judgment fields.

This interface adopts the paper constructs and anchors in
`../../../overleaf/sections/appendix.tex`. The retired engineering contract is
retained only with the archived qualification under `Storage/`. It is direction-scoped
because the current Warrant Study app and historical synthetic judge records do
not implement those constructs identically. These files do not modify or
reinterpret either historical artifact.

The five normative artifacts are:

| Artifact | Function |
|---|---|
| `../schemas/evaluator_item.schema.json` | Exact blinded information shown for one theme-and-evidence item |
| `../schemas/shared_rating.schema.json` | Actor-neutral rating returned field-for-field by humans and LLMs |
| `../schemas/paired_observation.schema.json` | Item, actor, timing, blinding, usage, and rating envelope |
| `../schemas/actor_registry.schema.json` | Separately frozen human qualifications and LLM configuration |
| this document | Rendering, blinding, timing, freeze, and compatibility rules |

If a future human-direction artifact defines a stricter shared interface, both
directions must migrate together under a new version. Do not make an LLM-only
field change to `shared_rating` while retaining the old human form.

## One-item evaluator payload

Each evaluation event presents exactly one `evaluator_item`. The unit is one
proposed theme and its evidence, not a five-candidate bundle, a pairwise choice,
or a complete model leaderboard.

The top-level item fields are:

- `item_schema_version`, `item_id`, `packet_id`, `output_id`, and `corpus_id`;
- `research_question`, `analytic_contract`, and `context_note`;
- `proposed_interpretation` containing `theme_id`, `theme_name`, `claim`,
  `explanation`, and `boundary_conditions`;
- `evidence`, an ordered list of exact displayed source excerpts; and
- `source_coverage`, the displayed counts and per-source distribution needed to
  inspect breadth and concentration.

Each evidence entry preserves two distinct layers. The actual displayed
provenance is `excerpt_id`, `source_id`, and nullable `speaker_id`; these fields
must never be rewritten to simulate a candidate error. The candidate's asserted
link is stored separately as `candidate_attributed_excerpt_id`,
`candidate_attributed_source_id`, and `candidate_attributed_speaker_id`.
The speaker attribution remains null when the candidate did not state one; it
must not be inferred merely to fill the field. `candidate_role` is `support`,
`counterevidence`, or `context_only`. Support and counterevidence entries require
the candidate-attributed excerpt and source IDs plus the candidate's quoted span
and concise warrant. A context-only entry has null candidate-attribution, quote,
and warrant fields. `candidate_role` describes the candidate output; it is not
an adjudicated truth label.

The evaluator item deliberately excludes:

- model, provider, workflow, prompt, and generation identity;
- controlled-condition and natural-versus-twin labels;
- `base_packet_id` or another identifier that reveals a twin relationship;
- evaluation-guide answers, planted-error labels, severity, or adjudication;
- other raters' judgments, aggregate scores, routing decisions, cost, or
  latency; and
- private privacy-review and provenance linkage fields.

These excluded fields may exist in a restricted manifest but never in the
rendered evaluator payload. `item_id`, `packet_id`, and `output_id` must be
opaque. The same canonical item JSON, including evidence order, is used for the
paired human and LLM observations. Direction J v1 defines its canonical bytes as
the output of Python 3.12 `json.dumps(item, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)`, followed by exactly one LF and
encoded as UTF-8 without a BOM. Hash those exact bytes as
`item_payload_sha256`; a pair with different hashes is not a same-information
comparison.

The common guide hash is equally literal: `shared_rater_guide_sha256` is the
SHA-256 of the complete `shared_rater_guide_v1.md` file bytes, including its
title, all status prose, and its existing final newline. Do not extract a body,
strip headings, or normalize line endings. The actor-neutral
`semantic_input_sha256` is the hash of this canonical JSON object (using the
same serialization above):

```json
{
  "interface_version": "direction-j-shared-interface-v1",
  "item_payload_sha256": "<item_payload_sha256>",
  "shared_rater_guide_sha256": "<shared_rater_guide_sha256>",
  "shared_rater_guide_version": "direction-j-rater-guide-v1"
}
```

Human and LLM records for a paired item must match on all three hashes. Their
actor-specific rendering wrapper remains separately identified by
`prompt_or_instrument_version` and the SHA-256 of that complete source artifact.

Counts in `source_coverage` and references among evidence entries require a
semantic validator in addition to JSON Schema. It must check that:

1. displayed counts equal the displayed evidence and source IDs;
2. candidate-cited counts include support and counterevidence entries but not
   context-only entries and group those citations by the candidate's asserted
   `candidate_attributed_source_id`, never by silently substituted actual
   provenance;
3. every per-source distribution row reconciles with the evidence list, and
   every candidate-attributed source used by this v1 interface is among the
   displayed source IDs;
4. display orders and excerpt IDs are unique within an item; and
5. candidate-attributed excerpt/source IDs are checked against actual displayed
   provenance without overwriting either layer; and
6. any candidate quote claimed as exact is checked separately against source
   text. A schema-valid item is not automatically provenance-valid.

## Shared rating object

`shared_rating` contains no actor type, human role, model identity, timestamps,
latency, token usage, or cost. A human and an LLM therefore return the same ten
fields:

1. `rating_schema_version`;
2. `evidential_credibility`;
3. `voice_boundary_preservation`;
4. `scope_calibration`;
5. `cannot_judge`;
6. `confidence`;
7. `disposition`;
8. `requested_expertise`;
9. `serious_error_flags`; and
10. `rationale`.

### Quality constructs and anchors

The three quality constructs are independent ordinal judgments. Do not average
them into an omnibus quality score.

| Field | Construct |
|---|---|
| `evidential_credibility` | Whether every material part of the core interpretation is directly warranted by sufficient cited evidence in local context |
| `voice_boundary_preservation` | Whether consequential differences, dissent, counterevidence, minority or boundary cases, and contextual qualifications survive synthesis |
| `scope_calibration` | Whether claim breadth, strength, polarity, causal language, and participant/group/corpus scope are proportionate to the supplied evidence |

The common anchors are:

- 1: not adequate;
- 2: major problems;
- 3: partially adequate; material revision needed;
- 4: mostly adequate; minor issues only; and
- 5: fully adequate.

The tutorial or LLM prompt must also reproduce the frozen construct-specific
anchors from the manuscript appendix. `confidence` is separate: 1 means very
uncertain and 5 means very certain about the submitted judgment. It is not an
output-quality score.

### Cannot-judge and escalation rules

Abstention is per construct. Each quality field is either an integer from 1 to 5
or null, and its exact field name appears in `cannot_judge` if and only if it is
null. This preserves usable judgments on the remaining constructs.

Any nonempty `cannot_judge` array requires `disposition: "escalate"`. Escalation
may also be selected without abstention when specialist review is needed despite
complete scores. `requested_expertise` is always required:

- when disposition is `escalate`, it must be `qualitative_methods`, `domain`, or
  `both`; and
- for `accept`, `revise`, or `reject`, it must be `none`.

This retains the current app's operational safeguard that missing information or
expertise cannot silently become a midpoint or an acceptance, while improving
the app's all-or-nothing abstention to the paper's per-construct representation.

### Serious errors and rationale

`serious_error_flags` uses the historical paper-compatible enum:

- `fabricated_or_altered_quote`;
- `wrong_attribution`;
- `unsupported_inference`;
- `hidden_source_concentration`;
- `lost_negative_case`;
- `contextual_flattening`;
- `unsupported_abstraction`;
- `sensitive_or_diagnostic_inference`;
- `inconsistent_codebook`; and
- `other`.

A flag is a first-stage detection, not an adjudicated severity label. The schema
does not infer `minor`, `material`, or `high-consequence` severity from a flag and
does not treat flag agreement as validity. Independent experts assign and lock
error family and severity in a separate adjudication artifact.

The rationale is required, must contain a non-whitespace character, and is
limited to 1,000 characters. It should identify the strongest evidence, missing
distinction, ambiguity, error location, or reason for escalation. Hidden
chain-of-thought is neither requested nor stored. When a serious-error flag is
set, the rationale should name its exact excerpt, quote, claim, or coverage
location. A later location-specific schema may replace this convention only if
the human and LLM interfaces change together.

## Actor registry: never call the LLM human

`actor_registry` separates actor identity and configuration from the shared
rating. Every actor has `actor_kind: "human"` or `actor_kind: "llm"`; the schema
branches are mutually exclusive.

A human profile may contain the paper evaluator group
`researcher`, `qualitative_methods_expert`, `domain_expert`, or
`dual_expertise`, plus tutorial/comprehension status, construction involvement,
independence eligibility, and corpus familiarity. It must use a pseudonymous
`actor_id`, never a name or email address.

An LLM profile contains provider, exact model ID and snapshot, model family,
runtime surface, reasoning mode/effort, temperature, top-p, seed, maximum output
tokens, response count, structured-output state, tool/web/function/retrieval/URL-
context/code-execution/memory access, data-processing scope, and an identifier
for the approved provider-processing profile. It also records whether the judge
family overlaps a candidate family and whether the actor is the primary judge,
a same-family sensitivity judge, or a cross-family sensitivity judge. In this v1
freeze the primary and cross-family roles require no candidate-family overlap;
the same-family sensitivity role requires overlap. Non-excluded primary versus
sensitivity analysis status must match that role.

An LLM profile cannot contain `evaluator_group`; `researcher` and the expert
groups are human qualification categories. User-facing prose must say “LLM
rater,” “model judge,” or “LLM actor,” never “human,” “researcher,” or “expert”
for the model.

The registry is frozen before a phase begins. Model aliases are insufficient:
record a dated or immutable snapshot. A change in provider, snapshot, prompt,
reasoning effort, sampling setting, tool access, web access, or processing
profile creates a new actor or a new preregistered configuration version.

## Paired observation envelope

`paired_observation` stores one completed response or one terminal LLM execution
failure. The join key for the primary
paired analysis is the combination of `study_id`, `item_id`, `packet_id`,
`output_id`, `corpus_id`, `candidate_generation_run_id`, and
`item_payload_sha256`, with `actor_id` and `rating_repetition` identifying the
paired responses. `base_packet_id` remains private and is never promoted into
the observation or evaluator payload.

`candidate_generation_repetition` and `rating_repetition` are deliberately
separate. The historical judge records use `run_index` for candidate-generation
repeats; they do not provide repeated calls of the same judge on the same item.

`actor_kind` is repeated in the observation envelope as a fail-fast check and
must match the actor registry. This duplication remains outside
`shared_rating`. A cross-record validator must also verify that `actor_id` exists,
the kinds match, actor IDs are unique in the registry, and excluded actors do not
enter a primary analysis.

### Timing, retries, usage, and cost

`review_seconds` belongs to the observation envelope, not the rating. The frozen
timing rule is:

- for a human, start after the complete item has rendered and stop when the
  submission is received;
- for an LLM, start immediately before dispatching the complete request and stop
  after the first schema-valid response or the terminal failed attempt is
  received; and
- include all allowed retries in the elapsed value and record their count in
  `execution.retry_count`.

Direction J v1 pauses the human active timer whenever the page is hidden and,
while visible, after 120 seconds without a keyboard, pointer, or scroll event;
it resumes on the next event. The first 120 seconds of a visible idle interval
remain counted. Wall, hidden, idle-paused, and active durations are retained in
the instrument log, while `review_seconds` stores active duration.
Each Direction J v1 provider attempt has a 600-second client deadline. Timeout,
provider error, and content filtering are terminal; only an invalid JSON/schema
response may receive the one declared format-only repair. Never compare a human's
active review estimate with a provider's server-only latency without labeling
the different measurement boundaries.

`execution.attempts` is empty for a human and contains one initial LLM call plus,
when used, one `format_only_repair` call. Each attempt records exact restricted-
storage IDs and SHA-256 hashes for the raw request and any raw response; provider
request/response IDs; provider-returned model ID and version; provider region;
timestamps; normalized attempt, finish, and filter states; schema-error summary;
and provider-reported input, output, cached-input, and reasoning-token usage.
Provider fields are required keys but nullable when the provider does not expose
them. A null raw-response artifact is allowed only when no response body arrived.

The observation's `observation_status` is `valid` only when its final attempt is
`schema_valid_output` and `rating` validates against `shared_rating`. A final
`invalid_json` or `invalid_schema` maps to `invalid_output`; timeout, provider
error, and content-filter states map to their same-named terminal statuses. A
non-valid observation has `rating: null`; it is an operational escalation, not
a midpoint or missing-at-random rating. The semantic validator must also check
that `retry_count == len(attempts) - 1` for LLMs, attempt timestamps are ordered,
the terminal status matches the final attempt, and every stored-artifact hash
matches its restricted raw bytes.

Aggregate token and cost fields are required but nullable under explicit
availability flags. Human observations normally set token availability false
and the associated values to null. LLM aggregate tokens sum all attempts only
when the provider exposed the required usage for every attempt; otherwise the
aggregate availability flag is false and the per-attempt records retain any
partial usage. Reasoning tokens have their own availability flag and are never
derived from total output tokens. Cost requires an amount, ISO 4217 currency
code, and frozen pricing-snapshot identifier. Missing usage or cost stays
missing; do not impute it from the historical synthetic run.

### Blinding state

Every accepted observation asserts that candidate identity, controlled
condition, and other ratings were hidden during evaluation. `unblinded_at_utc`
is null while ratings are being collected and may be populated only after the
record is locked. The private blind map is stored outside evaluator bundles.

## Same-information execution rules

For a valid paired comparison:

1. Render or serialize one canonical `evaluator_item` without adding actor-specific
   evidence or answers.
2. Give humans and LLMs the same task definition, construct definitions, anchors,
   disposition meanings, serious-error list, abstention rule, and rationale
   request. UI wording and JSON syntax may differ only as needed for interaction;
   any semantic difference is versioned and reported.
3. Do not provide the synthetic evaluation guide, private blind map, candidate
   names, model-specific aggregate metrics, planted-condition label, severity,
   or another rating to either actor.
4. Evaluate one item per isolated LLM context. Do not let earlier candidates,
   prior ratings, or a preference ranking enter the context. Human assignment
   prevents exposure to more than one version of a base packet where feasible.
5. Validate the item before dispatch and the rating before acceptance. A
   format-only retry may be allowed only under the frozen retry rule and must be
   counted. Retain both raw attempts and record a terminal failure rather than
   fabricating a rating. Do not repair a substantive model answer manually.
6. Lock every individual response before unblinding or expert adjudication.
7. Retain all prespecified LLM repetitions; never select a “best” judge response.

The human and LLM prompt/instrument versions and hashes are recorded separately
because their rendering mechanisms differ. Their semantic content must remain
aligned and auditable.

## Blinding, leakage, and governance

The item manifest, actor registry, primary LLM, number of rating repetitions,
prompt/instrument, schemas, retry policy, aggregation rule, cross-family
sensitivity plan, and analysis outcomes must be frozen before the held-out phase.

Dreaddit development data may be used only after the documented institutional,
platform, provider-processing, and excerpt-privacy gates are satisfied. Dreaddit
test and CaCHe remain unavailable for tuning. Protected real text must not enter
these artifacts, prompts, logs, or model calls until all applicable gates pass.
The first executable qualification therefore uses only release-cleared synthetic
items.

Provider-processing approval is configuration-specific. An actor registry entry
marked `approved_real_data` is not itself proof of approval; it must reference the
separately controlled approval record. Fail closed if the record, approved fields,
retention/training settings, or phase scope cannot be resolved.

## Deliberate compatibility decisions

1. **Paper names are canonical.** `evidential_credibility`,
   `voice_boundary_preservation`, and `scope_calibration` replace the app's
   `support` and `voice` names and the historical judge's broader proxy fields.
2. **One item, not relative ranking.** Five-way and pairwise preference can change
   judgments through comparison and cannot be paired with the current human
   interface. Direction J uses independent single-item ratings.
3. **Scope calibration is collected directly.** `analytic_contract_fit` is not a
   substitute.
4. **Abstention is dimension-specific.** Null and `cannot_judge` must agree in
   both directions. Any abstention escalates, but available dimensions remain
   rated.
5. **Requested expertise is never implicit.** It is required on every rating and
   must be non-`none` exactly when escalation is selected.
6. **The rationale is a concise observable warrant.** It is required for both
   actor kinds; no hidden reasoning is requested.
7. **Timing and actor metadata are not judgments.** They live in the observation
   and registry envelopes so the rating object stays field-for-field identical.
8. **Synthetic qualification is an explicit evaluation role.** This direction
   adds `synthetic_qualification` to the observation envelope without adding it
   to the historical paper schema or claiming it is a real-corpus result.
9. **Actor kind is explicit and disjoint.** The LLM is not entered as a researcher,
   expert, human panelist, or human evaluator group.
10. **Flags are detections, not truth or severity.** Agreement on a flag is
    evaluated against independent expert adjudication and task outcomes.
11. **Displayed provenance and candidate attribution are distinct.** Actual
    excerpt/source/speaker fields are never overwritten by the candidate's
    asserted IDs; this keeps wrong-attribution errors visible to both actor
    kinds.
12. **Execution failure is not a rating.** Invalid output, timeout, provider
    error, and content filtering are locked as null-rating operational states
    with raw-attempt audit records; none is converted to an abstention, midpoint,
    or silent exclusion.

## Current Warrant Study app gaps

The deployed prototype remains useful for interaction design, but it is not the
confirmatory shared interface. This contract does not silently rewrite its
historical records.

| Current app behavior or field | Shared-interface resolution |
|---|---|
| Public item has `researchQuestion`, `contextNote`, excerpts, `theme`, and `interpretation` | Add the declared analytic contract, explicit claim/explanation/boundaries, candidate quote/warrant, separate actual-versus-candidate attribution IDs, local context/speaker where available, and source-coverage summary |
| Top-level item ID, base ID, condition, and privacy review are removed from the client | Keep condition, base-packet relationship, and private review hidden; expose only opaque paired IDs |
| `support` | Rename and define as `evidential_credibility` |
| `voice` | Rename and broaden explicitly as `voice_boundary_preservation` |
| No scope item | Require `scope_calibration` |
| One `cannotJudge` Boolean clears all scales | Use a per-construct `cannot_judge` array and null only the named fields |
| Cannot judge forces escalation | Retain this safety rule for any nonempty abstention array |
| Expertise values are `qualitative_expert`, `domain_expert`, `both`, `none` | Use paper-aligned `qualitative_methods`, `domain`, `both`, `none` |
| Rationale is optional | Require a nonblank rationale, capped at the app's existing 1,000-character limit |
| No serious-error fields | Require the frozen serious-error flag array |
| Review time is `reviewTimeMs` inside the response and capped at one hour | Store uncapped nonnegative `review_seconds` in the observation envelope; freeze inactive-time handling separately |
| Human roles omit dual expertise and use `qualitative_expert` | Store paper-aligned human groups, including `dual_expertise`, only in the actor registry |
| `RUBRIC_VERSION` is declared but not persisted | Record interface and prompt/instrument versions and hashes on every observation |
| Assignment uses runtime randomness and balancing | Use a frozen manifest and logged assignment for study data |
| No item payload hash | Require `item_payload_sha256` for paired identity |

A future app adapter must prove round-trip equivalence to the schemas and must
not map missing scope or serious-error fields to fabricated defaults.

## Historical synthetic judge incompatibilities

The `qc-judge-v1` artifacts are starting evidence only. They are not convertible
to Direction J paired observations without new ratings because the judges:

- saw all five candidate outputs together and supplied preference groups;
- received a separate evaluation guide not shown in the Warrant Study app;
- rated eight legacy constructs plus overall quality rather than the three paper
  constructs;
- had no scope-calibration field, per-construct abstention, requested expertise,
  or review time; and
- were same-vendor models, with all judge families overlapping candidate
  families.

The old `run_index` is a candidate-generation repetition. It must map to
`candidate_generation_repetition`, never to `rating_repetition`. Historical
scores may motivate qualification checks, but they must remain labeled
same-vendor synthetic diagnostics and must not be pooled with new human-LLM
paired ratings.

## Validation and freeze checklist

Before accepting a run:

- validate all schema files as JSON Schema Draft 2020-12;
- validate every item, rating, observation, and actor registry instance;
- run semantic count, uniqueness, cross-reference, registry, and hash checks;
- verify that the human-rendered and LLM-serialized item hashes match;
- verify null/abstention and disposition/expertise invariants;
- confirm independent rating repetition IDs and absence of best-run selection;
- confirm that blind-map and condition fields are absent from evaluator payloads;
- confirm synthetic-only scope or resolve every real-data approval gate;
- lock the manifest, actors, versions, hashes, repetitions, retries, and analysis
  rules before evaluation; and
- report validation failures as failures, not as missing-at-random ratings.

Schema or wording changes after a run begins require a new interface version.
Never overwrite frozen records or backfill a field with an invented value.
