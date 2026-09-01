# Direction J prospective study protocol (`direction-j-protocol-v1`)

Status: design retained for a future real Dreaddit/AGYW study. No fictional or
synthetic data is authorized, and both real-data lanes remain blocked before
access by governance and prospective-freeze requirements.

## 1. Question and scope

Direction J asks whether an LLM can serve as the first-stage judge in the
WarrantRoute evidence-packet task under the same visible information and
response interface as Charlie and later independent humans. It does not ask
whether a model can replace accountable qualitative interpretation.

The rated unit is one complete theme-and-evidence packet. The construct is
bounded source warrant under the declared codebook-oriented analytic contract,
not the existence of a uniquely correct thematic analysis.

The prospective questions are:

1. How closely do the LLM and Charlie agree item by item on the three ordinal
   constructs, disposition, serious-error flags, and escalation?
2. How well does each actor detect independently adjudicated material or
   high-consequence errors, including the planted defect in qualification
   controls?
3. Is each actor's confidence calibrated to the correctness of its primary
   pass-versus-needs-action decision?
4. What error remains as items are accepted at increasing confidence rather
   than escalated or abstained on?
5. Are rationales source-localized, diagnostically correct, actionable, and
   useful to a fixed revision system?
6. What latency and cost are required for the initial judgment, expert
   verification, and successful repair?
7. Does feedback repair the targeted defect while preserving accurate material
   and avoiding a new unsupported claim, omission, or distortion?

Human--LLM or human--human agreement alone answers none of questions 2--7.

## 2. Phases and non-overlap

### Phase 0: synthetic qualification

Use only the existing fictional four-proxy benchmark and its synthetic model
outputs. The prepared first run samples 24 distinct base theme outputs without
using prior judge scores: one natural and one sentinel-controlled item in each
proxy-packet by candidate-generation-repeat cell. No evaluator sees both the
presented item and its unmodified parent. Qualification verifies the interface,
schema adherence, blinding, latency/usage capture, stochastic stability,
adjudication workflow, and analysis code. It does not estimate real-corpus
validity or select the paper's candidate model. The four fictional source
packets necessarily recur across distinct candidate themes and generation
repetitions; these 24 items are therefore neither source-independent nor a
sample for inferential effect estimates.

### Phase 1: approved development and pilot

After all real-text gates pass, Dreaddit train may be used to develop packet
construction, tutorials, prompt wording, analysis code, and thresholds. Pilot
items, prompt-development items, qualification controls, and Charlie practice
items are excluded by `base_packet_id` and source cluster from later audit and
confirmation.

### Phase 2: locked evaluation

Dreaddit test is an in-domain audit. AGYW is the held-out cross-domain
confirmatory corpus. Before either is opened for Direction J evaluation, freeze
the item manifest, source clusters, candidate systems, judge model identifiers,
prompt/schema hashes, repetitions, retry rule, outcome definitions, calibration
mapping, sample size, exclusions, adjudication procedure, repair system, and
analysis code. KODIS/CANDOR are not primary corpora in v1.

## 3. Actors and independence

- **Charlie:** a pseudonymous first-stage human actor. Charlie's task-relevant
  role and prior item/corpus involvement must be recorded before rating; this
  protocol does not invent those facts.
- **Primary LLM judge (`J_PRIMARY`):** Anthropic `claude-opus-5`, a pinned
  model ID, represented in the actor registry as `actor_kind=llm`.
- **Cross-family sensitivity judge (`J_SENS_GEMINI`):** Google
  `gemini-2.5-pro`, one call per item, not used to choose or tune the primary.
  Google lists this stable endpoint for shutdown on 2026-10-16; qualification
  must finish before that date, and any successor requires a new prospective
  freeze rather than a silent substitution.
- **Independent humans:** qualitative-method and domain experts who did not
  construct or first-stage-rate their confirmatory items.
- **Adjudicators:** lock individual expert ratings before resolving an
  operational action. Persistent source-grounded disagreement remains
  `plural_ambiguous`.
- **Repair panel:** does not see feedback source, first-stage actor, planted
  condition, or original adjudication and does not evaluate its own feedback.

Actor metadata are joined through `actor_id`. The shared response contains no
human/LLM type field, preventing an LLM from being mislabeled as a human
evaluator group.

## 4. Identical-information rule

The immutable `evaluator_item` JSON and complete shared-guide bytes are the sole
semantic source rendered to both Charlie and every LLM call. Their exact hashes,
plus the derived actor-neutral semantic-input hash, are stored in all assignments
and observations. Equivalent typography may differ, but the semantic fields,
ordering of excerpts, labels, and scale anchors may not.

Visible information includes the research question, analytic-contract summary,
context note, proposed theme/claim/explanation, the packet's bounded source
excerpts, exact cited evidence and stated counterevidence, boundary conditions,
and source-coverage counts. It excludes candidate identity, model/provider,
workflow, condition, failure family, planted truth, evaluation guide, other
outputs, automatic scores, prior ratings, private provenance, and adjudication.

## 5. Frozen prompting and model conduct

The model receives the shared rater guide followed by exactly one evaluator
item and returns only a JSON object conforming to `shared_rating.schema.json`.
It is told that it is an LLM judge, not a human. Hidden chain-of-thought is not
requested or stored; the retained rationale is concise, decision-relevant, and
source-linked.

Calls are stateless. Search, URL context, retrieval, code execution, function
calling, browsing, file access, conversation memory, and access to other items
are disabled. The prompt is fixed at `direction-j-judge-prompt-v1`. The primary
Claude request uses adaptive thinking, explicit `high` effort, the provider's
required/default sampling temperature (left unset), one response, and
structured JSON output. The Gemini sensitivity request uses temperature 0,
top-p 1, one response, and structured JSON output. The raw request, raw
response, response/request identifiers, provider-returned model/version,
timestamps, region, usage, finish/filter status, retries, and billed price
basis are retained in restricted run storage.

For Charlie and later humans, `review_seconds` starts only after the full item
and guide have rendered. It excludes every interval while the page is hidden.
In a visible page, an interval is counted through 120 seconds after the last
keyboard, pointer, or scroll event, pauses thereafter, and resumes on the next
event. Submission stops the timer. Wall time, hidden seconds, idle-paused
seconds, and active review seconds are retained separately in the instrument
log; the shared observation stores active review seconds. The qualification
must test this rule before any comparative timing claim.

Each provider call has a 600-second client deadline. Timeout, provider error,
or content filtering is terminal for that rating repetition: there is no
automatic transport retry, fallback model, or newly sampled replacement.
No model output may be silently edited. One format-only repair request is
allowed after invalid JSON/schema output; it receives the invalid response and
schema error only, not truth, adjudication, another answer, or a revised item.
Both raw attempts remain. A second failure is recorded as `invalid_output` and
treated as an operational escalation; it is not imputed as a midpoint.

## 6. Repetitions and aggregation

The primary judge makes three independent calls per item in separately created
stateless requests. `rating_repetition` is 1, 2, or 3 and must not be confused
with the candidate-generation repeat.

- Repetition 1 is the preregistered primary single-judge observation and its
  rationale is the only primary LLM feedback used in repair.
- Repetitions 2--3 estimate within-model instability and support a secondary
  operational ensemble.
- The ensemble uses the median for each evaluable ordinal dimension and
  confidence; majority membership for each serious-error flag and each
  per-dimension abstention; and the modal disposition. If all three
  dispositions differ, the ensemble disposition is `escalate`. It never
  selects the most favorable or most expert-aligned repeat.
- All repeat-level records remain in analysis; they are not treated as
  independent items.

The cross-family sensitivity judge makes one stateless call per item. It is a
prespecified robustness analysis, not a replacement chosen after results.

## 7. Blinding and leakage control

The synthetic qualification builder uses a published deterministic seed so its
fictional item bank is exactly reproducible. This is operational blinding only:
it depends on not mounting the repository, builder, legacy bundles, or private
map into evaluator sessions and is not secure against a person who can read the
full workspace. Qualification results must disclose that limit.

For every approved real-data phase, generate a fresh 256-bit secret blinding
key in restricted storage. Derive opaque item/assignment IDs with HMAC-SHA-256
over the private stable identifiers and phase label; publish only the key's
SHA-256 commitment in the locked manifest. The secret, input identifiers,
private key map, and adjudication data are never stored in the evaluator tree or
mounted into model/human clients. Retain access logs and file hashes, and destroy
or archive the secret under the approved retention plan only after the declared
unblind. The algorithm, commitment, and mapping hash lock before collection.

Each LLM request contains one item only. Human presentation uses an independently
randomized order. Related variants are not shown in one qualification run; in
later incomplete blocks, twin pairs are separated by rater where possible and
never adjacent. Item constructors and prompt developers do not adjudicate their
own confirmatory items. The held-out model/domain labels remain inaccessible
until the analysis package is frozen and ratings are locked. This hides the
private mapping, not semantic domain content: research questions, context, and
source/excerpt conventions can make a proxy or real domain inferable. Report
that limitation and never claim content-level domain blinding.

Prompt injection inside source text is data, not instruction. The model prompt
states that only the outer protocol is authoritative. Evaluator-visible source
text is delimited and never passed to a tool-capable agent.

## 8. Outcome reference

All first-stage observations are compared separately against:

1. locked individual expert ratings;
2. the contract-relative expert adjudication, including `plural_ambiguous`;
3. deterministic integrity checks and planted qualification manipulations;
4. rationale-usefulness judgments from a separate blinded panel; and
5. successful repair without collateral error.

Expert adjudication is an operational reference, not universal qualitative
truth. The analysis retains individual expert disagreement and audits cases of
high shared agreement that nevertheless fail a deterministic or task outcome.

## 9. Stop and change rules

Stop without inference if a governance gate, item hash, blind-map separation,
actor independence declaration, prompt/schema/config hash, raw-output capture,
or expert-rating lock is missing. Never switch the primary judge, retry strategy,
aggregation, outcome, severity threshold, or analysis after inspecting outcome
labels. Any necessary change creates a new version, excludes affected pilot
items from confirmation, and documents why.
