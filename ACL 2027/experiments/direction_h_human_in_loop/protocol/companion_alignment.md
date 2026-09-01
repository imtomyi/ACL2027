# Direction H companion alignment contract

Contract amendment: `direction-h-companion-j-alignment-v2`  
Status: prospective; synthetic only; no ratings or results

## Controlling lane

The active human–LLM item comparison is the exact Direction J browser lane in
`../companion_j_bridge/browser/`. It supersedes the earlier assumption that the
companion direction would use `qc-paper-metrics-v1` on four complete qualitative
outputs.

The live Direction J unit is one proposed interpretation plus its displayed
evidence. Its shared rating is the actor-neutral 10-field
`direction-j-shared-rating-v1` object. The original Direction H four-item lane
rates a complete qualitative output with the 19-field
`qc-paper-metrics-v1` object. These units, IDs, timing rules, evaluation roles,
abstention constraints, and rating schemas are materially different. No
post-hoc field mapping, projection, rescaling, or short-ID join is permitted.

The four-item lane remains an internal workflow rehearsal only. Charlie cannot
run both queues in one phase because they reuse the same four fictional packet
contexts and would create carryover. A completed non-Charlie browser activation
selects the exact Direction J queue and prospectively retires the four-item
queue for that phase.

## Exact comparison signature

Charlie receives the exact evaluator-item bytes and guide pinned by Direction
J's prepared synthetic run. The human and LLM observation pair is eligible only
when all of these match exactly:

1. `study_id`;
2. `item_id`;
3. `packet_id`;
4. `output_id`;
5. `corpus_id`;
6. `candidate_generation_run_id`;
7. `candidate_generation_repetition`;
8. `item_payload_sha256`;
9. `interface_version`;
10. `shared_rater_guide_version`;
11. `shared_rater_guide_sha256`; and
12. `semantic_input_sha256`.

The first five and the semantic/public hashes are available during masked
rating. Candidate-generation provenance stays in Direction J's private item
key and is joined only after all 24 rating/timing/feedback triplets are locked.
Opening that key earlier is a protocol stop.

Charlie uses Direction J actor ID `charlie`. His Direction H case alias
`charlie_dev_researcher_01`, `evaluator_group=researcher`,
`helped_construct=true`, and independence exclusion live in the separate actor
registry/timing receipt, not in the shared rating. Do not coerce an LLM into a
human evaluator group or widen either v1 schema.

## Exact rating object

The browser writes the object defined unchanged by
`../../direction_j_llm_as_rater/schemas/shared_rating.schema.json`:

- `evidential_credibility`;
- `voice_boundary_preservation`;
- `scope_calibration`;
- construct-specific `cannot_judge`;
- `confidence`;
- `disposition`;
- `requested_expertise`;
- `serious_error_flags`;
- `rationale`; and
- `shared_rating_version`.

Direction J's frozen semantic constraints also apply unchanged: construct nulls
and `cannot_judge` are bidirectionally coupled; any cannot-judge requires
`escalate`; a non-escalation uses `requested_expertise=none`; and `accept`
requires all three scores at least 4 with no serious flag. The rationale limit
is the exact Direction J limit. Human convenience metadata, timestamps, time,
identity, and provenance cannot be added to the rating object.

## Timing and observation envelope

The rating timer begins after the complete guide and item are rendered and
stops at rating submission before any feedback prompt. Hidden intervals are
excluded. A visible idle interval counts for 120 seconds after the last
keyboard, pointer, or scroll event, pauses thereafter, and resumes on the next
such visible event. The timing receipt retains wall, hidden, idle-paused, and
active durations and reconciles them before the rating locks.

After the 24-item lock, the coordinator joins the private generation fields and
creates the unchanged `direction-j-paired-observation-v1` envelope with
`actor_kind=human`, active `review_seconds`, an empty human execution-attempt
array, and unavailable/null token and cost fields. This post-lock finalization
computes no empirical result.

The browser display hides candidate identity, condition, and other ratings, but
the shared developer workspace cannot establish secure technical separation.
The official v1 description is `condition_masked_developer`; boolean interface
fields describe what the instrument displayed, not independence from study
development.

## Linked Direction H feedback

Only after the exact shared rating and eligible timing receipt commit does the
instrument elicit `direction-h-direction-j-browser-feedback-v1`. The sidecar is
linked by assignment, item identity, canonical rating hash, and timing-receipt
hash. It never changes the shared rating or its time.

The model-visible projection contains only, in frozen order:

1. `feedback_summary`;
2. `findings`;
3. `preserve`; and
4. `uncertainties`.

Each finding includes one canonical serious-error family, severity, evaluator-
item-root JSON Pointer locations, displayed excerpt IDs, a description, and a
requested change. Locations may address only proposed-interpretation or
candidate-assertion fields; source text and actual provenance are immutable.
Distinct serious finding flags must equal the rating's serious flags exactly.
The sidecar rejects author identity, planted/manipulation language, arm labels,
candidate model/provider identities, rating values, confidence, time, truth,
and other raters' information.

`no_change` has no finding; actionable revision/regeneration has at least one.
A no-change record remains a valid observed intervention and is not replaced
with invented criticism.

## Defect detection

Reviewer files contain no controlled truth. Charlie's target-family detection
is defined only after a non-Charlie, non-constructor verifies the synthetic item
against the locked private construction record:

`D_i = 1[target flag is in Charlie serious_error_flags_i]`.

Rationale-only mentions and low scores do not become primary detections after
unblinding. Controls support specificity language only when independently
verified to have no material rubric-defined defect; “no planted defect” alone
does not establish universal cleanliness. There is no human detection outcome
in the no-feedback revision arm, so a Charlie-versus-no-feedback human
detection contrast is undefined.

## Same-unit paired revision

The only downstream path for the selected queue is
`../companion_j_bridge/theme_revision/`. It revises the same evaluator-item
unit. The old full-output prompt, schema, formatter, and recorder are
incompatible and must never receive these records.

Every independently verified defective item with complete locked feedback is
allocated to both `no_feedback` and `charlie_feedback`, including Charlie
misses. The pair uses the same item, model snapshot, prompt, decoding, repeat,
one-attempt policy, fresh-context opportunity, and pair-shared model-visible
blind ID. Only `reviewer_feedback` differs: literal null versus the exact locked
identity-free projection. The model sees no target, condition, arm, feedback
author, rating, confidence, or review time.

An independent arm-blind panel uses Direction J's unchanged
`direction-j-repair-assessment-v1` endpoint. `successful repair without
collateral error` requires target repaired, accurate material preserved, and no
collateral flag. Report each component. Allocated model/pipeline failures remain
in the ITT denominator with established success zero. Post-treatment
conditional-on-detection results are mechanism analyses only.

## Confirmatory extension

Independent humans receive the same item bytes, guide, shared rating schema,
feedback interface, and timing contract. They must not have constructed the
items, prompts, model choice, software, condition map, or target briefs. Use
crossed incomplete blocks, at least three ratings per declared role/item if the
manuscript design is retained, and at most one twin or revision arm variant per
reviewer. Lock individual ratings before adjudication and preserve persistent
reasoned dissent as plural/ambiguous. Charlie remains a separate displayed case
row and is never pooled into the independent reference or population estimate.

## Protected-text boundary

This contract authorizes fictional synthetic qualification only. It does not
authorize the Warrant Study real-item bank or Dreaddit, AGYW/CaCHe, KODIS,
CANDOR, raw, provenance, or lightly masked text. The documented institutional,
platform, model-processing, rater-exposure, privacy, retention, and signed
manifest gates remain controlling.
