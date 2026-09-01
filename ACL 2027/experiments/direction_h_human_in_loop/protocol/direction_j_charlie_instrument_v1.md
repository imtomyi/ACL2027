# Direction H human instrument for the Direction J shared queue

Instrument version: `direction-h-direction-j-charlie-instrument-v1`  
Status: frozen compatibility instrument; prepared but not activated  
Data scope: Direction J synthetic qualification only

## Purpose

This instrument lets Charlie review the exact evaluator items in Direction J's
prepared synthetic run and return the exact actor-neutral
`direction-j-shared-rating-v1` object. Direction-H-only role, timing, and
feedback data are written beside that rating and never inserted into it.

Charlie is a construction-involved developer-researcher case baseline. His
records are not universal human ground truth, are excluded from the independent
human pool, and do not satisfy Direction J's independent expert slots.

## Frozen input

For each review event, the collector renders, in this order:

1. the complete, byte-locked Direction J shared rater guide;
2. exactly one object from Direction J's canonical `evaluator_items.jsonl`;
3. the rating prompts in this instrument; and
4. only after the rating is complete, the Direction H feedback prompts.

The item is not copied or translated into Direction H's four-item pilot shape.
Its `item_id`, `packet_id`, `output_id`, `corpus_id`, evidence order,
candidate-attribution fields, proposed interpretation, source coverage, and
canonical payload hash remain unchanged. The frozen `charlie_rep1.csv` sequence
is the only allowed order.

The shared guide and item together determine Direction J's actor-neutral
semantic-input hash. The collector verifies the item payload, guide, interface,
and semantic-input hashes before it renders anything.

## Exact rating prompts

Rate the following constructs separately using the complete Direction J guide:

- `evidential_credibility`: 1--5 or null when it cannot be judged;
- `voice_boundary_preservation`: 1--5 or null when it cannot be judged;
- `scope_calibration`: 1--5 or null when it cannot be judged;
- `cannot_judge`: exactly the set of constructs whose value is null;
- `confidence`: 1--5 confidence in this judgment, not output quality;
- `disposition`: `accept`, `revise`, `reject`, or `escalate`;
- `requested_expertise`: `none`, `qualitative_methods`, `domain`, or `both`;
- `serious_error_flags`: every applicable Direction J shared error flag; and
- `rationale`: a concise, source-grounded explanation, not hidden reasoning.

The collector enforces the shared schema's abstention, escalation, acceptance,
and serious-error consistency rules. It writes those ten fields directly as one
unwrapped `direction-j-shared-rating-v1` JSON object. Actor identity, item
identity, timestamps, and review time do not belong in that object.

The terminal collector snapshots time only after the complete guide and complete
item have been rendered and stops the rating clock after the last exact-rating
prompt, before feedback begins. Feedback time is measured separately.

This measurement is continuous terminal wall time. A terminal cannot determine
whether a page is hidden or apply Direction J's frozen 120-second visible-idle
grace and pause rule. The receipt therefore sets
`direction_j_review_seconds_eligible: false`. The elapsed time is a Direction H
feasibility measure only and must not be copied to a Direction J paired
observation's `review_seconds` field. Exact timing parity needs a prospectively
frozen browser instrument with visibility and input-activity logging.

## Direction H feedback sidecar

After completing the rating, Charlie records a separate feedback projection:

- an identity-free summary;
- zero or more structured findings;
- accurate material to preserve; and
- uncertainties the revision model should not overresolve.

Each finding has one shared error-family label, a `minor`, `material`, or
`serious` severity, one or more JSON Pointer locations, relevant displayed
excerpt IDs, a concise problem statement, and a requested change. In this
bridge, output pointers resolve relative to the Direction J item's
`proposed_interpretation` object. For example, `/claim` addresses the claim and
`/boundary_conditions/0` addresses the first boundary condition.

The distinct flags on findings marked `serious` must exactly equal the shared
rating's `serious_error_flags`. The feedback record contains no score,
confidence, time, condition, target truth, candidate identity, arm label, or
other rating. Its `model_feedback` object is the same structure used by the
existing Direction H feedback formatter and may be supplied verbatim to a
future frozen revision model.

## Three-file commit

One confirmed submission atomically creates:

1. a canonical, unwrapped Direction J shared rating;
2. one linked Direction H feedback sidecar; and
3. one Direction H review receipt containing public assignment identity,
   Charlie's developer-researcher role, separate rating/feedback wall times, exact
   input locks, and hashes of the first two files.

The receipt is not a `direction-j-paired-observation-v1` record. That Direction
J envelope needs candidate-generation identifiers found only in the private
item key. A coordinator may create it only after the first-stage review lock and
the permitted private join; the bridge never opens or guesses those fields.

No file is written before the reviewer types the exact confirmation token. The
collector refuses overwrites, partial pre-existing triplets, sequence gaps, or
schema-invalid responses.

## Masking and stop rules

The displayed item omits candidate identity, condition, planted error, other
ratings, and adjudication. This shared workspace is nevertheless classified as
`condition_masked_developer`, not technically blinded: a workspace reader could
open Direction J's private map. Do not open the private item key, builder,
legacy blind map, prior judge records, evaluation guide, other assignments, or
another response while first-stage reviews are open.

Stop before viewing the item if a hash fails, a condition or model field is
visible, another rating exists in the rendered payload, the material is not
explicitly synthetic, or the collector cannot complete its reviewer-safe
preflight. Protected real text remains blocked by the institutional,
platform/source, model-processing, retention, access-control, and release gates.

## Non-overlap rule

This 24-item queue is a prospective replacement for Charlie's existing
four-item Direction H qualification queue, not an add-on. The four-item lane is
internal Direction H workflow qualification only; it is not a paired companion
rating lane. Both queues reuse the same four fictional source packets. Running
both with the same reviewer in one phase would introduce source familiarity and
incompatible task units (complete outputs versus one proposed interpretation).
The coordinator must choose and freeze one queue before the first response. Do
not pool, concatenate, or treat ratings from the two queues as independent
observations.

The Direction J queue may be activated only if the paired Charlie-versus-LLM
comparison is the selected pilot objective. The existing four-item queue remains
the active Direction H quickstart until that prospective decision is recorded.
Charlie cannot self-authorize by typing a token in the collector. A separate,
schema-valid `activation_record.json` must be created prospectively by an
identified coordinator who is not Charlie, while responses are absent and
outcomes uninspected. It must select this exact Direction J queue, supersede the
internal four-item queue for the phase, and bind all frozen input and instrument
hashes. Only an incomplete null template is checked in.

## Downstream empirical-claim gate

This v1 bridge freezes only the lossless first-stage item/rating/feedback join.
It is not a complete human-feedback intervention and must not be routed into the
existing Direction H full-output revision schemas. A Direction J item is one
proposed interpretation; the old Direction H revision case is a complete
qualitative-coding output. Treating them as interchangeable would change the
task and repair denominator.

`companion_j_bridge/downstream_gate.json` therefore blocks first-stage
collection as well as all model calls, revision outputs, repair assessments,
and empirical feedback-effect claims in this v1. A new prospective version must
first freeze: a Direction-J-compatible browser timing instrument, independent
itemwise target verification, paired theme-level no-feedback/Charlie-feedback
revision cases, the exact revision prompt and model configuration, an arm-blind
theme-level repair panel, isolated assessor assignments, outcome definitions,
and complete locks. The gate may not be changed in place after any rating is
inspected.
