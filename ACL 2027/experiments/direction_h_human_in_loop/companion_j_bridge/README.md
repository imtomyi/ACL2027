# Direction H compatibility bridge for the prepared Direction J run

Status: **prepared, not activated, no ratings or outcomes**  
Scope: synthetic qualification only

## What this bridge does

This bridge gives Direction H a lossless path onto Direction J's actual shared
first-stage interface. It reads Direction J's 24 canonical evaluator items and
the exact 24-row `charlie`, repetition-1 assignment in place. It does not copy,
relabel, reorder, rebuild, or modify Direction J.

For each completed item, the collector is designed to write an atomic
three-record bundle under `responses/`:

- `ratings/`: an unwrapped object that conforms exactly to
  `direction-j-shared-rating-v1`;
- `feedback/`: a Direction-H-only feedback sidecar whose `model_feedback`
  projection exactly reuses the existing Direction H feedback structure; and
- `receipts/`: public assignment, role, input-hash, linkage, and timing metadata
  that Direction J deliberately excludes from the actor-neutral rating.

No response directory or observation exists yet. The manifest remains a
prospective freeze and must never be edited to imply that a review occurred.

## Why the receipt is separate

Direction J's exact shared rating has ten fields and no item ID, actor ID,
timestamp, or review time. Those fields belong outside the rating. The local
receipt preserves Charlie's Direction H classification as a
construction-involved developer-researcher case, the immutable Direction J
assignment join, and separately measured rating and feedback time.

The terminal receipt stores continuous rating and feedback wall time separately,
with rating completion snapped before feedback begins. It cannot implement
Direction J's browser visibility and 120-second idle-pause rules, so the receipt
marks its rating time ineligible for Direction J's `review_seconds` field.

The receipt is not a Direction J paired-observation envelope. That envelope
requires private candidate-generation fields. The collector does not open the
private item key and cannot fabricate those values. A coordinator may perform
that private join only after the first-stage lock.

## Frozen files

- `manifest.json` pins every upstream and local normative artifact by SHA-256.
- `../protocol/direction_j_charlie_instrument_v1.md` defines rendering, timing,
  response, masking, and non-overlap rules.
- `../schemas/direction_j_feedback_record.schema.json` links Direction H
  feedback to an exact Direction J rating.
- `../schemas/direction_j_review_receipt.schema.json` keeps role, timing, and
  public assignment provenance outside that rating.
- `../scripts/validate_direction_j_bridge.py` performs a reviewer-safe,
  fail-closed validation without opening the private item key.
- `../scripts/collect_direction_j_review.py` contains the no-overwrite
  interactive collection implementation but is deliberately blocked before it
  renders the guide or an item.
- `downstream_gate.json` machine-readably blocks collection, model calls,
  revisions, repair assessments, and feedback-effect claims in this v1.
- `activation_record.template.json` is intentionally incomplete. Charlie cannot
  self-authorize collection; a non-Charlie coordinator would have to create a
  separate schema-valid `activation_record.json` before responses and bind the
  manifest, instrument, assignment, evaluator bank, shared schema, and gate.

## Activation is a prospective choice

Do not start this queue merely because the bridge validates. It is a
supersession option for the existing four-item Direction H pilot, not an
additional block. The four-item lane is internal Direction H workflow
qualification only, not a paired companion lane. Both queues use the same four
fictional source packets and different units of judgment. Running both with
Charlie would introduce source familiarity and prevent clean pooling.

The current `CHARLIE_QUICKSTART.md` therefore remains unchanged. Before any
rating, the coordinator must choose which single queue answers the pilot's
primary question and record that decision without inspecting outcomes. If the
Direction J paired comparison is selected, the coordinator should issue a new
versioned handoff that points Charlie to this bridge and retires—not deletes—the
four-item queue from that phase.

Typing a confirmation in the reviewer collector is never sufficient
authorization. Activation belongs to a separately identified coordinator who
is not Charlie, must occur while responses are absent and outcomes uninspected,
and must bind the exact frozen hashes. This repository contains only the null
template, not a completed activation record.

This bridge also stops short of a downstream intervention. A Direction J item
contains one proposed interpretation, whereas the existing Direction H
revision/repair pipeline expects a complete qualitative-coding output. The two
must not be joined. A new version must freeze theme-level paired revision cases,
the exact model/prompt/settings, independent target verification, arm-blind
repair items, assessor assignments, and locks before collection. Until then,
even a schema-valid first-stage rating could not support a no-feedback versus
Charlie-feedback empirical claim.

## Prepared-only verification

From the Direction H directory:

```bash
python3 scripts/validate_direction_j_bridge.py --prepared-only
```

The expected status is `valid`, with 24 evaluator items, 24 Charlie
assignments, and zero response triplets. This command reads only reviewer-safe
Direction J artifacts and local bridge files. It does not open Direction J's
private item key, ratings area, model assignments, builder, or historical judge
outputs.

## Governance boundary

Every upstream item is independently authored fictional text and the frozen run
manifest says `contains_real_source_text: false`. That makes this bridge usable
for pipeline qualification only. It does not satisfy any gate for protected
Dreaddit, CaCHe/AGYW, KODIS, CANDOR, app, or dataset text.

The displayed payload is condition- and identity-masked. Because this local
workspace can expose private files to a determined reader, the default receipt
classification is `condition_masked_developer` with
`private_map_access_separated: false`. Do not describe this local execution as
technically blinded. A later access-separated human run requires a separate
prospective environment and freeze.
