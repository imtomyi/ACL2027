# Theme-level Charlie feedback versus no feedback

Status: **prospectively specified; not frozen or run**  
Scope: the same 24 fictional Direction J evaluator items selected for Charlie's
browser lane

This is the downstream extension for the active companion-compatible Direction
H pilot. It keeps the unit of analysis unchanged: one proposed interpretation
plus its displayed evidence. It does not translate a Direction J item into the
older four-item full-output task.

## Causal comparison

After all 24 exact Direction J ratings and identity-free feedback records are
locked, a non-Charlie verifier opens the private synthetic construction key and
classifies items individually. Every independently verified defective item with
a complete locked feedback record enters both paired arms—even if Charlie
missed or misdiagnosed the defect:

1. `no_feedback`: the frozen revision model receives the literal null feedback
   payload;
2. `charlie_feedback`: the same frozen model receives Charlie's exact locked
   `model_feedback` object.

The revision model, snapshot, prompt, decoding, one-attempt rule, repeat index,
source item, analytic contract, and fresh-context opportunity are identical.
The pair-shared model-visible blind ID is also identical. The only model-visible
difference is null versus Charlie feedback. The model is never told that an
error was planted, why the item was selected, the arm, Charlie's identity,
ratings, confidence, time, or the target brief.

The primary finite-manifest estimand is the paired ITT difference

`mean(S_charlie_feedback - S_no_feedback)`

over all independently verified defective items allocated before generation,
where `S=1` only when an independent panel records target repaired, accurate
material preserved, and no collateral-error flag. Every allocated runtime,
timeout, parse, schema, integrity, or unavailable-panel failure remains in the
denominator with `S=0`. Report target repair, accurate-material preservation,
and collateral-error rates separately. Conditional-on-Charlie-detection
analyses are mechanism-only because detection is post-selection information.

There is no literal human defect-detection comparison to a no-feedback rater:
that decision is structurally absent. Charlie's detection is evaluated against
the independently verified synthetic construction record; a secondary paired
contrast may compare the frozen revision model's truth-blind diagnosis across
the two revision arms.

## Prospective sequence

1. Complete and lock all 24 browser rating/timing/feedback triplets.
2. Only after that lock, allow a non-Charlie independent item verifier to open
   the private synthetic key and complete `target_verification.json`.
3. Write arm-blind target assessment briefs for every eligible defective item;
   commit their exact bytes before any revision call.
4. Complete `revision_freeze.json` from the draft template, including the exact
   model snapshot, runtime, decoding settings, and all current hashes.
5. Re-run the validator and build both paired cases atomically. Model inputs
   contain no private truth or author/arm label.
6. Run every allocated case once in a fresh context; retain failures and never
   select a best output. Reconstruct and validate the exact Direction J item,
   including immutable source text/provenance, assertion-row coverage, exact
   quotes, attribution, and recomputed source concentration.
7. Before assessor assignment, screen complete revised text for arm, feedback,
   author, or model self-disclosure. A flagged output is a retained protocol
   deviation—not redacted or replaced.
8. Give independent assessors isolated arm-blind bundles under a frozen
   balanced incomplete block: at least three assessors per revision and at most
   one arm variant of an item per assessor. Charlie, feedback authors, item
   constructors, and target verifiers cannot assess.
9. Collect the unchanged Direction J `direction-j-repair-assessment-v1` record
   and lock every expected assessment before unblinding arms or computing any
   contrast.

## Prepared artifacts

- `revision_prompt.md` — truth-blind theme-revision instruction and exact JSON
  response contract.
- `revision_freeze.template.json` — schema-valid draft with frozen upstream,
  prompt, formatter, schema, and software hashes; model/gate values remain null.
- `coordinator_only/*.template.json` — deliberately incomplete independent
  target verification, assessment briefs, and pre-revision commitment.
- `schemas/revision_case.schema.json` — paired case and exact null-versus-
  feedback coupling.
- `schemas/model_output.schema.json` and `revision_output.schema.json` — model
  response and one-attempt audit envelope, including hard integrity gates.
- `schemas/repair_panel_item.schema.json` — arm-blind original/revised evidence
  packet plus the precommitted target brief.
- `schemas/repair_assignment_plan.schema.json` and
  `repair_assessment_lock.schema.json` — independent-panel allocation and
  pre-unblinding lock contracts.
- `scripts/format_direction_j_theme_feedback.py` — emits only the frozen
  identity-free feedback projection.
- `scripts/validate_direction_j_theme_revision.py` — prepared or frozen
  fail-closed preflight.
- `scripts/prepare_direction_j_theme_revision_cases.py` — refuses to write
  before browser lock, independent target verification, brief commitment, and
  completed model freeze; then builds paired inputs with exact itemwise
  denominator accounting.
- `scripts/record_direction_j_theme_revision.py` — records the one retained
  raw attempt or terminal runtime/timeout failure, reconstructs the immutable
  Direction J item, and applies schema, exact-quote, attribution, source-
  coverage, diagnosis-link, and disclosure gates; it never calls a model.

No model caller is embedded here. The coordinator supplies the approved frozen
runtime and records every raw response through the pinned recorder. Until the
same-unit arm-blind panel packager/collector is implemented, frozen, and
adversarially tested, the pilot stops after retaining validated revision
envelopes. This is an explicit remaining execution gate, not an invitation to
use the incompatible full-output panel tooling.

## Confirmatory extension

The confirmatory study reuses the same Direction J evaluator-item bytes, guide,
shared rating schema, feedback sidecar, revision prompt, and assessment
endpoint with independent blinded humans who did not construct items, prompts,
models, software, or condition maps. Use crossed incomplete blocks, at least
three ratings per declared role/item if retaining the manuscript design, and
never show both twins/arm variants to one reviewer. Ratings lock before
adjudication; persistent reasoned dissent remains plural/ambiguous rather than
being overwritten. Charlie is displayed as a separate developer-case row and
is excluded from population inference, reliability, reference construction,
power estimates, and adjudication.

Real source text remains prohibited until all institutional, platform,
model-processing, rater-exposure, privacy, permissions, retention, and signed
manifest gates are satisfied.
