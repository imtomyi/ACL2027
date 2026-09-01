# Coordinator runbook: execute and record frozen revisions

Status: prospective synthetic-pilot procedure; no model has been selected or
run, and this document contains no revision outcomes.

This runbook begins only after Charlie's four rating/feedback pairs are locked
and his schema-valid post-lock debrief records the official v1
`condition_masked` classification without modifying locked ratings,
independent itemwise construction verification is complete, the arm-blind
target-assessment briefs and their exact-hash commitment are frozen, the
revision manifest is complete and frozen, and
`scripts/prepare_revision_cases.py` has produced the committed allocation,
coordinator cases, and model-facing inputs. It does not authorize protected-text
processing. Construction truth, condition labels, ratings, and arm labels are
not needed by the revision model and must remain outside its context.

## 1. Required frozen inputs

For one attempt, the coordinator needs:

- `pilot/revision_freeze.json`, with `status = frozen`, an immutable model
  snapshot, exact decoding settings, disabled tools/retrieval, retry/repeat
  policy, and current hashes for the prompt, schemas, shared integrity validator,
  revision-output recorder, and repair-panel packager;
- `coordinator_only/construction_verification.json`, completed by an eligible
  non-Charlie verifier;
- `coordinator_only/target_assessment_briefs.json` and
  `coordinator_only/target_assessment_briefs.commitment.json`, completed and
  hash-frozen before case creation;
- `coordinator_only/revision_allocation.json`;
- one immutable
  `coordinator_only/revision_cases/<revision_case_id>.json` record;
- the matching `pilot/revision_model_inputs/<revision_case_id>.json`; and
- the frozen system instruction in `protocol/revision_prompt.md`.

`prepare_revision_cases.py` verifies the exact lock version, study/rater,
four-task order and coverage, manifest/condition-commitment hashes, false
truth/mutation flags, fixed response paths, and response hashes before opening
any coordinator-only truth. It also requires
`pilot/responses/blinding_debrief.json` to validate, match the lock's study and
rater, preserve `locked_ratings_modified = false`, retain the official
`condition_masked` classification, and postdate the lock. Before coordinator
truth is opened, the builder also revalidates all four public item file hashes,
canonical evidence-packet/candidate-output component hashes, schemas, internal
identity joins, and `synthetic_cc0` markers. The already validated in-memory
objects—not a second disk read—become the eventual model inputs.

The model-facing request consists only of the frozen system instruction and the
matching model-input object. Do not send the coordinator case or allocation.
They contain workflow provenance and an arm label. Do not add truth, a target
label, Charlie's identity, rating values, confidence, timing, prior model/judge
results, or repair outcomes.

Run every case in a fresh context using the exact provider, model ID, snapshot,
decoding configuration, token limit, and no-tool policy in the freeze. The
no-feedback case is an active self-revision request with literal JSON null in
`reviewer_feedback`; it is not an untouched-copy control. Do not change the
prompt or configuration after observing an output. A substantive change
requires a new freeze ID and retention of the old attempt inventory.

## 2. Capture the runtime result verbatim

`scripts/record_revision_output.py` records an attempt; it never invokes a
model. The runtime operator must save every returned response byte-for-byte as a
new UTF-8 file below:

`coordinator_only/revision_raw_responses/`

Name it
`<revision_case_id>.attempt-<three-digit-attempt>.raw.json`; the recorder rejects
another name so the retained bytes remain visibly bound to their envelope.

Do not strip Markdown, extract an inner object, repair JSON, rename fields,
rewrite quotations, or make a schema-invalid response look valid. Use a new raw
file for every retry and retain all files. Do not put provider credentials,
request headers, hidden reasoning, protected source data, or coordinator truth
in this directory.

If the runtime returns no usable response bytes, do not create a fabricated
response object. Record the actually observed `transport_failure` or
`empty_response`. The recorder supplies a fixed, source-free failure detail; it
does not accept free-text failure logs that could accidentally contain source
material or credentials.

## 3. Record one response

From `experiments/direction_h_human_in_loop/`, run:

```bash
python3 scripts/record_revision_output.py \
  --case coordinator_only/revision_cases/<revision_case_id>.json \
  --allocation coordinator_only/revision_allocation.json \
  --freeze pilot/revision_freeze.json \
  --attempt-index 1 \
  --runtime-model-id <actual-runtime-model-id> \
  --runtime-snapshot-id <actual-immutable-snapshot-id> \
  --generated-at-utc <actual-invocation-completion-RFC3339> \
  --raw-response coordinator_only/revision_raw_responses/<revision_case_id>.attempt-001.raw.json
```

Optional `--latency-ms`, `--input-tokens`, and `--output-tokens` values may be
included only when copied from actual runtime telemetry. The runtime model and
immutable snapshot arguments must also come from the actual invocation and must
equal the freeze. The recorder stores the frozen values only after that match;
there is no override that can relabel a different invocation. Supply the actual
invocation-completion time through `--generated-at-utc`; never substitute the
later recorder time or a file modification time. An offset-bearing RFC 3339
value is normalized to UTC.

For an observed failure before a usable response was captured, replace
`--raw-response` with:

```bash
--runtime-failure <transport_failure-or-empty_response>
```

The recorder writes exactly one new envelope to:

`coordinator_only/revision_outputs/<revision_case_id>.attempt-001.json`

It uses exclusive file creation and refuses an existing target. Do not delete
or rename a failed attempt to reuse its index.

## 4. What the recorder verifies

Before it reads a raw response, the recorder fails closed unless all of the
following hold:

1. the freeze validates, is `frozen`, contains no placeholders, is scoped to
   `synthetic_only`, declares no protected text, and still hashes to every
   allowlisted analytic, prompt, formatter, input-schema, output-schema, shared
   integrity-validator, recorder, and panel-packager artifact; the reported
   runtime model and snapshot must match it exactly;
2. `pilot/review_lock.json` still matches the pilot manifest and every locked
   rating/feedback hash; a no-feedback case has null linkage and payload, while
   a Charlie-feedback case exactly matches the frozen formatter projection and
   `feedback_record_id` from its locked sidecar;
3. the case validates as `direction-h-revision-case-v1`, carries the correct
   canonical `model_input_sha256`, contains no truth/rater fields, and matches
   both its separately materialized model-input file and the hashed
   reviewer-safe synthetic pilot item exactly;
4. the complete allocation has the deterministic eligible-target × repeat × arm
   inventory frozen by `prepare_revision_cases.py`; it binds the exact
   construction-verification, target-brief, and brief-commitment hashes, retains
   all itemwise exclusions privately, its canonical hash matches the case,
   and its case, pair, repeat, arm, model-blind, and repair-blind IDs agree;
5. the attempt index is consecutive, does not exceed `maximum_attempts`, does
   not overwrite a prior file, and—after attempt 1—is authorized by the prior
   failure and the frozen `allowed_retry_reasons`; and
6. every prior attempt still validates and retains the same case, freeze, model
   snapshot, blind ID, deterministic output ID, and attempt index.

The recorder then hashes the exact raw bytes. Strict JSON parsing rejects
duplicate keys, non-UTF-8 input, non-standard numeric constants, surrounding
prose, and Markdown fences. A parsed response must be one object with exactly
the two fields `revision_diagnosis` and `revised_output`. Both must validate
against `revision_output.schema.json#/$defs/modelResponse`, including the
unchanged shared `qualitative-output-v1` schema.

For a schema-valid response, the recorder applies the hard gates used by the
existing qualitative baseline, tailored to the frozen case packet:

- exact packet ID and research question;
- one and only one assignment per supplied excerpt;
- resolving code and theme references and consistent `not_coded` semantics;
- known excerpt/source links, correct attribution, and exact contiguous quotes;
- at least two evidence sources per theme; and
- unique code/theme IDs.

It also checks that every diagnosis flag has a localized finding and vice
versa, every diagnosis JSON Pointer resolves in the unchanged starting output,
and every cited diagnosis excerpt exists in the supplied packet. Declared theme
source-list mismatch is retained as a non-hard diagnostic, matching the
baseline validator's treatment; unknown sources remain hard failures.

The envelope stores:

- the raw-byte SHA-256 (null only for an explicit runtime failure);
- the canonical revised-output SHA-256 for schema-valid responses;
- case, pair, repeat, task, packet, starting-output, freeze, arm, model, snapshot,
  attempt, and blind IDs derived from frozen records;
- the actual invocation-completion timestamp, a separate integrity-validation
  timestamp, and any supplied runtime telemetry;
- the exact parsed diagnosis and complete revised output only when the response
  schema passes; and
- a bounded failure record or integrity issue-code list without raw text.

Parse, schema, and runtime failures are written as denominator records with null
diagnosis/revision fields. A schema-valid response with a failed integrity hard
gate remains a `complete` response envelope but has `hard_gate_pass = false`;
retain it and apply the frozen analysis rule rather than silently repairing or
discarding it.

## 5. Retries and repeats

Attempt 1 may always be recorded. Attempt 2 or later is permitted only when:

- the immediately preceding attempt is not `complete`;
- its reason maps to one of the freeze's `allowed_retry_reasons`:
  `transport_failure`, `empty_response`, `invalid_json`, or `schema_invalid`;
- every earlier attempt index exists exactly once; and
- the new index does not exceed `maximum_attempts`.

A hard-gate failure in an otherwise schema-valid response is not a retry reason.
Do not ask for a cosmetically improved alternative or select the best attempt.
Preregistered repeats are separate frozen cases distinguished by
`repeat_index`; they are not retries, and all remain in the inventory.

## 6. Handoff to repair assessment

After every allocated case has a terminal recorded attempt, run the coordinator
preflight and inventory checks specified in `protocol/companion_alignment.md`.
`scripts/prepare_repair_panel.py` then revalidates the already frozen
construction record, target-assessment briefs, commitment, and allocation before
performing the
fail-closed downstream packaging and frozen first-eligible-attempt selection.
Before selection, it screens the string values of every complete revised output
for diagnostic arm, feedback-author, reviewer-feedback, frozen model/snapshot,
or model self-identification disclosures. Contextual matches already present in
the visible evidence/starting output are treated as inherited source content,
while exact arm labels always block. A match is a protocol deviation: retain the
envelope, write no panel product, and follow the frozen handling/reporting rule.
Do not redact, retry a complete output, or substitute another attempt/repeat.
Do not unblind condition truth to the revision model or use intended labels to
edit an envelope. Only the allocation's `blinded_revision_id`, the permitted
arm-blind source/starting/revised material, and the minimal frozen assessment
reference may enter a repair-panel bundle. Feedback arm, author, content, model
identity, construction truth, and derived success labels remain coordinator-side.

No repair rating or empirical result is created by this runbook or recorder.
Those require actual model attempts followed by the separate blinded assessment
workflow. Independent construction verification remains mandatory before the
pilot's intended labels are used for detection or specificity scoring.

## 7. Stop conditions

Stop without running or recording the case if any file contains protected real
text, is outside the Direction H synthetic roots, exposes truth/rater identity
to the model, differs from a frozen hash, or requires an unplanned model/config
change. This recorder intentionally has no approved-real-text mode. Real-text
revision requires a separate approved runner and all institutional,
platform/source, model-processing, rater-exposure, retention, and excerpt-review
gates documented in `protocol/governance_and_blinding.md`.
