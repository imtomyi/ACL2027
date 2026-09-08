# Shared WarrantRoute first-stage rater guide (`direction-j-rater-guide-v1`)

This guide applies without construct changes to Charlie, later human raters,
and the LLM judge. The model-facing prompt adds serialization instructions only.

## Task boundary

Judge one proposed theme-and-evidence packet under the stated bounded,
codebook-oriented analytic contract. Decide whether the proposed interpretation
is warranted by the supplied sources. Do not decide whether it is the only
possible interpretation. Do not infer identity, diagnosis, prevalence,
causality, culture, or outside facts not supported by the packet.

Use only the displayed item. Do not search for the text, consult another item,
guess the generating system, or use another rater's judgment. A fluent, long,
or familiar-sounding interpretation is not better unless the evidence warrants
it and consequential differences remain visible.

Each evidence row separates actual displayed provenance from the candidate's
claim about that provenance. `excerpt_id`, `source_id`, and `speaker_id` identify
the displayed excerpt. `candidate_attributed_excerpt_id`,
`candidate_attributed_source_id`, and `candidate_attributed_speaker_id` report
what the candidate asserted; a null candidate speaker means no speaker was
stated. Compare these layers when checking attribution. Do not treat a
candidate-attributed ID as corrected ground truth or overwrite the displayed
provenance mentally. `context_only` rows were supplied for review but were not
cited by the candidate.

## Three independent quality ratings

Rate each construct from 1 to 5. Use `null` only when that specific construct
cannot be judged, and list its field name in `cannot_judge`.

### Evidential credibility

How fully does the cited evidence support every material part of the proposed
interpretation in local context?

- **1:** Core meaning is not supported or conflicts with the evidence.
- **2:** Major claims lack sufficient or correctly attributed support.
- **3:** General direction is plausible, but a material claim or warrant needs
  revision.
- **4:** Core meaning is supported; only a minor evidential qualification is
  needed.
- **5:** Every material part is directly warranted by sufficient, correctly
  linked evidence.

### Voice-and-boundary preservation

How well does the interpretation retain consequential differences, dissent,
counterevidence, minority or boundary cases, temporal change, speaker position,
and contextual qualifications?

- **1:** It reverses, erases, or seriously flattens consequential source meaning.
- **2:** Major differences or negative cases are lost.
- **3:** The main pattern remains, but a material boundary or voice needs repair.
- **4:** Important differences survive; only a minor qualification is missing.
- **5:** Consequential differences, counterevidence, and boundaries are fully
  visible and affect the synthesis appropriately.

### Scope calibration

How well do the breadth, strength, polarity, causal language, and
participant/group/corpus scope match the supplied evidence?

- **1:** Claim strength or scope is incompatible with the packet.
- **2:** The interpretation substantially overstates, reverses, or generalizes.
- **3:** Direction is broadly appropriate, but scope or strength needs a material
  change.
- **4:** Scope is proportionate with only a minor wording issue.
- **5:** Participant-, source-, packet-, and any broader scope are fully
  calibrated, with no stronger causal or prevalence claim than the evidence
  permits.

Do not average these constructs into one score.

## Cannot judge and requested expertise

Abstain only for the affected construct(s), not automatically for all three.
Use `cannot_judge` when the displayed context or your task-relevant expertise is
insufficient to make that construct rating responsibly. A nonempty
`cannot_judge` requires `disposition="escalate"` and a non-`none`
`requested_expertise` value. `Cannot judge` is reported separately; it is never
converted to 3 or counted as an error by itself.

## Disposition

- `accept`: no material change is needed.
- `revise`: the interpretation is usable after a material but bounded repair.
- `reject`: the central interpretation is unsupported or misleading enough that
  bounded revision is not appropriate.
- `escalate`: missing context/expertise, consequential ambiguity, or potential
  harm requires qualitative-method expertise, domain expertise, or both.

Whenever disposition is `escalate`, set `requested_expertise` to
`qualitative_methods`, `domain`, or `both`. For every other disposition set it
to `none`. `accept` is consistent only when all three construct ratings are 4 or
5 and no serious-error flag applies.

## Serious-error flags

Mark every applicable category; an empty list is allowed. A serious flag names
a located, material problem, not mere interpretive disagreement:

- `fabricated_or_altered_quote`
- `wrong_attribution`
- `unsupported_inference`
- `hidden_source_concentration`
- `lost_negative_case`
- `contextual_flattening`
- `unsupported_abstraction`
- `sensitive_or_diagnostic_inference`
- `inconsistent_codebook`
- `other`

Use the rationale to identify the relevant excerpt/source, claim, omission, or
ambiguity. Do not force one reading when multiple source-grounded readings are
defensible; explain the plurality and escalate if specialist deliberation is
needed.

## Confidence

Rate confidence in the correctness of your complete first-stage judgment:

- 1 = about 20% confident
- 2 = about 40% confident
- 3 = about 60% confident
- 4 = about 80% confident
- 5 = about 100% confident

The numeric mapping is frozen as `confidence / 5` for calibration against the
later expert-adjudicated pass-versus-needs-action target. Confidence is still
required when a construct is `cannot_judge`: it then describes confidence in
the abstention/escalation decision, not confidence that the interpretation is
correct.

## Rationale

Give a concise, decision-relevant explanation containing at least one
non-whitespace character and no more than 1,000 characters. Point to stable
excerpt/source IDs or an explicit missing boundary where possible. State the
defect or defensible ambiguity and the smallest safe action; do not provide
hidden step-by-step reasoning or invent replacement content.
