# Direction J first-run plan

Run status: **blocked; no data lane is authorized**. Do not run this plan.
Fictional or synthetic data requires fresh, explicit user permission before
each use. Protected real text remains separately blocked until every governance
gate passes. The remainder is retained as historical design documentation, not
current execution authority.

## Entry conditions

1. Confirm the run manifest says `synthetic_only` and every input path is under
   the allowlisted qualitative-coding synthetic benchmark/run.
2. Confirm `config/freeze_v1.json`, the model prompt, shared guide, schemas, and
   evaluator-item bank match their recorded SHA-256 values.
3. Confirm the private item key is stored separately and is not mounted in the
   LLM runner or participant client.
4. Record Charlie's task-relevant role, independence from item construction,
   and qualification-only consent/authorization. Do not infer these facts from
   the name.
5. Confirm provider account access, synthetic-data processing terms, run budget,
   raw request/response retention, and the ability to capture usage and latency.
   Confirm the frozen `gemini-2.5-pro` sensitivity calls will complete before
   its documented 2026-10-16 shutdown; otherwise create a new versioned freeze
   before looking at any first-stage outcomes.
6. Fill two preregistered independent qualification slots: `QME_QUAL` for a
   qualitative-methods expert and `DOMAIN_QUAL` for a domain expert. Neither may
   have constructed the items or see the private condition while first-stage
   responses are open. Record qualifications; do not infer them from the slot.
7. Validate the separate human instrument and its readiness receipt. An
   assignment CSV does not establish exact rendering, active-time measurement,
   response hashing, consent, or blinding.
8. Freeze and validate one provider wire adapter per judge. The adapter must map
   the provider-neutral system, developer, and user segments exactly once,
   compile the structural response schema, retain full shared-rating
   post-validation, disable tools/external context, and capture the returned
   model version. Provider-neutral packets alone do not authorize dispatch.

## Build and verify

From the workspace root:

```bash
python3 experiments/direction_j_llm_as_rater/scripts/build_synthetic_first_run.py
python3 experiments/direction_j_llm_as_rater/scripts/audit_legacy_judges.py \
  --output experiments/direction_j_llm_as_rater/legacy_evidence/legacy_judge_inventory.json
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py \
  --self-test
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py \
  --write Storage/synthetic-results/archived-experiments/direction-j/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py \
  --verify Storage/synthetic-results/archived-experiments/direction-j/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl
python3 experiments/direction_j_llm_as_rater/scripts/check_execution_readiness.py \
  --self-test
python3 experiments/direction_j_llm_as_rater/scripts/validate_direction_j.py
```

Expected prepared material:

- 24 evaluator-visible items: two per synthetic proxy packet by candidate
  generation repeat;
- 12 natural items and 12 single-defect sentinel controls;
- 24 unique base theme outputs, so no actor sees a natural/control twin pair;
- one Charlie assignment and three primary-judge assignments with identical
  item, complete-guide, interface, and semantic-input locks but separately
  randomized order;
- one cross-family sensitivity assignment;
- one blinded assignment each for the independent `QME_QUAL` and `DOMAIN_QUAL`
  expert slots, 24 items per actor;
- 96 canonical provider-neutral LLM request packets: 72 primary and 24
  cross-family sensitivity packets, all explicitly marked as not provider-wire
  rendered and not authorized for network dispatch;
- an access-restricted private item key and a build report; and
- empty rating directories/readmes, never placeholder ratings.

The build must also emit a matching synthetic source receipt: the independently
authored-fictional benchmark hash, all 12 blinded-bundle hashes, byte equality
between each bundled packet and that benchmark, and
`contains_real_source_text: false`. A label without those hash checks is not an
admissible synthetic input.

The selector balances generator model identity and control status without
reading prior judge scores. Sentinel controls qualify failure handling; their
difficulty is not representative and their results cannot be pooled with
natural outputs. The 24 units reuse four fictional source packets across
different themes and generation repetitions, so qualification summaries must
retain the base-packet cluster and remain descriptive engineering checks.
Its published deterministic seed supports exact rebuilds but is only an
operational blind: no evaluator account or model runner may access the workspace,
builder, legacy bundles, or private map during collection.

## Collect first-stage records

Collection remains blocked until a completed, restricted, untracked readiness
record passes `check_execution_readiness.py` immediately before the first call
or human rating. The checked-in template is never an approval. It cannot open a
real-text lane.

1. Charlie completes the shared guide and rates all assigned items in the
   frozen human interface. The application stores the assignment's exact item,
   complete-guide, interface, and semantic-input locks plus the shared response
   JSON; it does not expose the private condition or other ratings.
2. Run `J_PRIMARY` three times per item as new stateless requests. Capture raw
   request/response bytes and telemetry before parsing. Never reuse a chat or
   batch context across items.
3. Run `J_SENS_GEMINI` once per item with the same serialized guide/item and
   response schema.
4. Apply at most the frozen one-step format-only repair after `invalid_json` or
   `invalid_schema`. Repeat the original messages unchanged, append only the
   canonical invalid-response/schema-diagnostic envelope, retain both attempts,
   and forbid any substantive repair or third attempt.
5. Validate each observation on ingestion. Do not manually correct a rating.

## Lock, adjudicate, and unblind

1. Close the first-stage write window and produce a content hash for every raw
   and parsed record.
2. The two frozen independent qualification experts rate the same evaluator
   items without seeing actor, condition, or other ratings. Do not substitute a
   single adjudicator for the two locked individual records.
3. Lock individual expert records, then produce adjudication records. Preserve
   `plural_ambiguous` when disagreement remains source-grounded.
4. Rationale-usefulness raters see a newly randomized rationale packet with
   actor identity removed.
5. Only after all locks, join the private condition/model map for stratified
   analysis. Record the unblind timestamp and operator.
6. When advancing the run manifest to `locked_for_analysis`, preserve and
   re-verify its frozen run ID, freeze hash, build-report hash, evaluator-bank
   hash, and synthetic source-receipt hash. The analysis utility accepts no
   other run lineage.

## First-run outputs

Produce descriptive tables only:

- schema/parse/format-repair counts;
- paired construct/disposition/error-flag tables;
- primary-judge repeat stability;
- calibration by the five frozen confidence levels;
- abstention/escalation and selective-risk tables;
- rationale-usefulness dimensions;
- complete cost/latency/usage summaries; and
- sentinel manipulation checks and natural-item findings in separate sections.

Do not issue a primary-judge validity claim, rank candidate generators, tune the
prompt, or change thresholds from this run. Log defects in the instrument. Any
prompt/interface change creates v2 and requires fresh, non-overlapping
qualification items.

## Qualification exit criteria

The package may advance to an approved real-data pilot only when:

- all expected item/assignment/input hashes reconcile;
- no private field appears in evaluator payloads or raw model prompts;
- both human and LLM records pass the identical shared schema;
- rating repetition and candidate-generation repetition are demonstrably
  separate;
- raw/parsed/telemetry records reconcile with no silent edits;
- calibration, abstention, rationale, cost/latency, and repair joins execute on
  synthetic records without denominator drift; and
- every real-text governance gate independently passes.

Failure to meet an exit criterion is a pipeline finding, not an empirical model
result.
