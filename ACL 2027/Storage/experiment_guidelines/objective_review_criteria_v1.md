# Evidence-Grounded Review Evaluation Guidelines

Version: 1.0. Date: 2026-09-07 KST.
Status: prospective specification; not an implemented or authorized new run.

## 1. Scope and precedence

This document records the user's decisions: withdraw the proposed data
efficiency transformations; specify auditable judgment criteria; leave
WarrantRoute development with the user; and design evaluation without a
human-authored answer sheet or a human calibration subset.

These rules apply to a future separately frozen evaluation of Generalist,
Fixed role, All roles and, when ready, WarrantRoute. They do not change any
running experiment, historical prompt, frozen manifest, scorer or table.
Existing run-specific contracts remain authoritative for their own results.
The no-human design below is a proposal, not a replacement silently applied
to an existing human-panel study. Workspace manuscript and privacy policies
remain in force. Historical controlled-flaw results remain private diagnostics.

"Objective" here means explicit, evidence-addressable and reproducible rules.
It does not mean that an LLM's semantic decision becomes verified ground truth.

## 2. Data preservation and evaluation boundaries

Do not introduce summarization, paraphrasing, translation, efficiency-driven
splitting, deduplication, source recombination or silent truncation. Preserve
existing stored input text and order. This decision does not undo preparation
already performed by the dataset authors or historical packet builders.
Document those prior transformations rather than calling all stored text raw.

Record original file hash, source record ID, supplied text hash, and provenance
for every input. Metadata may be recorded separately without altering text.
Existing privacy and access restrictions are not waived. If a full permitted
input cannot fit a model's context, mark it input-ineligible and report the
reason; do not quietly shorten it. Future full-dataset inclusion rules and the
common cross-model eligible inventory must be frozen before execution.

| Object | Exact boundary |
| --- | --- |
| Source record | The dataset's stored record, not automatically a sentence, paragraph, person or entire conversation |
| Supplied evidence | The complete text and context actually sent to the reviewer, with source IDs and order preserved |
| Judgment target | The explicitly identified analysis claim, not the participant's experience or the source author's credibility |
| Located issue | A claim span plus cited evidence spans and an explicit alleged relation between them |
| Review bundle | All review outputs belonging to one packet, method, model and repetition under a frozen bundling rule |
| Revision target | A separately identified revised claim evaluated against the same supplied evidence |

For historical n100, the evidence unit is a packet containing four stored
excerpts and one constructed claim. Dreaddit excerpts are supplied post
segments; GoEmotions excerpts are comments; CaChe and ParlaMint-GB excerpts
are participant/speaker turns. A packet is neither one natural document nor
four independent people. Record unavailable surrounding context explicitly.

For future span annotations, use zero-based Unicode-code-point offsets with
an inclusive start and exclusive end in the exact decoded stored field.
Specify source field and record ID; require `text[start:end] == quote`.
Browser UTF-16 indexes require explicit conversion. Do not normalize whitespace
or punctuation to make a failed exact match pass. Missing locations remain
unlocated, rather than receiving fabricated offsets.

## 3. Evidence states and decision procedure

Assess each distinct review allegation separately, with its original wording
and scope preserved. An allegation is material when changing it would change
the diagnosis, recommended action, scope, attribution or overall disposition.
Locate allegations as annotations; do not replace the input with a rewritten
or shortened version. Log annotation failures and preserve the full bundle.

1. Verify input identity, response identity, schema and completeness.
2. Check referenced source IDs, exact quotations and valid span offsets.
3. Identify the alleged claim defect, its scope and the relevant evidence.
4. Apply the category criteria below, including counterconditions.
5. Record the evidence state, a concise justification and relevant spans.
6. Aggregate using the frozen review-quality rules, retaining unresolved cases.

| Evidence state | Decision rule |
| --- | --- |
| Supported | Supplied evidence warrants the allegation at its stated scope, with no decisive contrary evidence left unaddressed |
| Contradicted | Supplied evidence conflicts with a material part of the allegation under matching speaker, time, population and conditions |
| Insufficient evidence | Supplied evidence establishes neither support nor contradiction, or a necessary premise/context is missing |
| Not applicable | The criterion genuinely does not apply; record a reason, never substitute a pass |

Absence of support is not proof of the opposite. An unsupported causal claim
may warrant a criticism of causal support without establishing that the causal
claim is false. A plausible interpretation is not automatically the only valid
interpretation. A disagreement in style or preferred wording is not a flaw.
Missing wider context must not be invented from model knowledge. Restrict
conclusions to the supplied evidence, not the entire original corpus.

## 4. Criteria for the five existing flaw families

These are semantic rubric conditions, not five automatically verified labels.
Multiple supported defects may coexist; unlisted historical flags are not
automatically false positives.

| Category | Required basis for a supported allegation | Insufficient basis or countercondition |
| --- | --- | --- |
| Unsupported evidence | Identify a material assertion and the missing inferential link to the supplied evidence; specify whether the unsupported step concerns causation, quantity, attribution or scope | A different opinion, a short explanation, or failure to cite every excerpt is not enough; lack of support is not contradiction |
| Source concentration | Identify the sources actually supporting a claim and the claim's broader representation/prevalence assertion; show why that broader scope is not warranted | One source alone is not a flaw if the claim is explicitly limited to that source; several turns do not necessarily represent several people |
| Counterevidence loss | Locate evidence that conflicts with or materially qualifies the claim under comparable conditions, and show that the claim fails to accommodate it | An unrelated statement, a different context, or an exception already acknowledged by the claim does not suffice |
| Contextual flattening | Identify a source condition, speaker distinction, uncertainty marker or temporal qualifier that was removed/merged and explain the resulting change in interpretation | Merely shortening text or omitting irrelevant metadata is not proof of a material distortion |
| Unsupported abstraction | Locate an abstract theme and show the missing evidence-to-concept link or a scope jump not justified by the supplied passages | Abstraction itself is not a flaw; a defensible interpretation need not repeat source vocabulary verbatim |

Separate quotation errors, nonexistent source IDs and numerical mismatches
from these semantic families. Deterministic checks establish those narrowly
defined errors, not general interpretive correctness. External-world claims
requiring outside evidence remain outside this closed-evidence evaluation.

## 5. Review-level Credibility and Conformability

These are project-specific operational adaptations to review quality, not
validated replacements for qualitative-research constructs. Judge the review
of the original claim separately from the revised claim or loop termination.

### Credibility

Question: Is the review's diagnosis and overall disposition defensible against
the supplied claim and evidence?

- `true`: every material allegation is supported at its stated scope; the
  disposition follows from the allegations; decisive contrary evidence is
  addressed; certainty is calibrated to the available context.
- `false`: at least one material diagnosis or disposition has an identifiable
  evidential/logical failure, including an unjustifiably definitive conclusion.
- `null`: no decisive failure is established, but missing evidence or genuine
  ambiguity prevents evaluating at least one required material judgment.

### Conformability

Question: Is the review's substantive reasoning traceable to, and faithful to,
the supplied evidence and context?

- `true`: required references resolve; quotations are faithful; material
  premises are evidence-grounded; speaker, negation, uncertainty, time and
  scope are preserved; no material unsupported premise is introduced.
- `false`: at least one material quotation/attribution is wrong, a cited
  passage is misrepresented, or the reasoning relies on an unsupported premise.
- `null`: the available record cannot establish either failure or the required
  evidence grounding for a material premise.

Evaluate the dimensions separately. Correct quotation does not prove a correct
diagnosis, and a plausible diagnosis does not excuse fabricated support.
For each dimension a demonstrated failure takes precedence over other unknown
items; otherwise unresolved required items prevent `true`. Minor stylistic
issues are not automatic failures. Record the decisive criterion and evidence.

Empty, missing, truncated or structurally invalid outputs are technical or
output-completeness failures, not semantic false judgments. A valid review
with no issue allegations does not pass vacuously: assess its explicit
disposition and grounding. "No flaw demonstrated in supplied evidence" is
different from asserting that the document contains no flaws.

## 6. Revision assessment is a separate endpoint

A future revision audit must separately assess whether an evidenced original
defect is resolved, supported meaning and boundaries are preserved, and no new
material unsupported assertion or contradiction is introduced. Judge original
and revision against the same evidence. Record each subcriterion, including
unknowns. Do not infer success from acceptance, reviewer agreement, a change
in text, reduced length or human escalation. Do not penalize a no-op solely
because no change occurred when no defect was established. Without an
independent reference, label the result judge-assessed repair quality, not
verified repair success. No revision scorer is implemented by this document.

## 7. Reporting and denominator rules

For every dataset/method/model/dimension retain planned N, true T, false F,
genuine null U and technical/missing E, with `N = T + F + U + E`.

- Binary coverage: `100 * (T + F) / N`.
- Complete-row LLM-assessed pass rate: `100 * T / N`, only if `U + E == 0`.
- If incomplete, leave that endpoint N/A and report all counts. An optional
  `100 * T / (T + F)` is a conditional resolved-case rate, not the full-row
  score. If `T + F == 0`, it too is N/A.
- Quote-match rate: matching submitted required quotation references divided
  by all submitted required quotation references. Separately report missing
  required references and review-level evidence-link coverage; zero submitted
  references yield N/A, not 100%.
- Historical intended-target recall remains tied to its original truth map
  and flag-matching contract. Do not relabel it natural-flaw accuracy.
- Without an adequate flaw reference set and established negatives, do not
  report natural-flaw precision, recall, F1, specificity or accuracy. A judge's
  agreement is not an independently verified TP.

Report per-dataset outcomes before a prespecified equal-weight dataset macro
average. Do not average away missing cells. Any uncertainty interval must
declare its estimand, dependence unit and resampling method. Shared source
components, repeated judgments and repeated trajectories are not independent
new documents. Statistical intervals do not capture unknown judge bias.

## 8. No-human-reference evaluation proposal

No human answer creation, human adjudication or human calibration subset is
required for this proposed diagnostic. That constraint limits the claims.

Recommended design for discussion, not yet authorized:

1. Run deterministic integrity/location/quotation checks on every output.
2. Use a separately frozen judge rubric on every complete review bundle.
   Keep the same evaluator panel and inputs across all tested methods/models.
3. Consider Qwen, Llama and Gemma as three independent-invocation evaluators,
   each producing one primary assessment of each unchanged bundle. These
   evaluations are not statistically independent just because calls differ.
   Hide model/method identities, filenames, intended-flaw fields, builder hints,
   internal acceptance labels and other judges' outputs. Preserve substantive
   reviewer wording. Record unavoidable identity leakage.
4. Report per-judge pass rates, joint binary coverage and full-panel agreement.
   On cases where all three judges are binary, unanimity is the fraction with
   three matching decisions. Report this denominator and unresolved cases.
   Majority vote, if shown, is a secondary consensus measure, never ground truth.
5. Report family-specific disagreement and self-family sensitivity. A
   leave-own-family-out analysis is secondary because it changes the evaluator
   panel between tested models. No panel member is a verified final grader.
6. For a later paired revision comparison, preregister both presentation orders
   and report order sensitivity. Do not rerun until a preferred verdict appears.

These measures assess evidence traceability, rubric-based judgments and
evaluation robustness. They cannot establish absolute natural-flaw detection
accuracy or human agreement. Model consensus can share systematic errors.
No new artificial defect injection or source transformation is authorized.
Existing controlled-flaw tests may remain separate engineering diagnostics,
never be pooled as validation of the natural-source evaluation.

## 9. Freeze checklist before any new execution

- Freeze dataset eligibility, full input boundaries and all included IDs.
- Fix method prompts across reviewer models, bundle rules and repetition count.
- Specify location annotation procedure and preserve original outputs.
- Implement and test evidence checks, rubric schema and aggregation rules.
- Freeze judge identities/digests, prompts, decoding, ordering and call budget.
- Declare retry limits before launch; retry technical failures only and retain
  every attempt. Never retry valid false/null to obtain a favorable score.
- Record full rendered requests, responses, hashes, code snapshots and usage
  under restricted Storage. Keep sensitive content out of public exports.
- Verify protection against answer-key and construction-hint leakage.
- Freeze reporting endpoints and missingness rules without viewing new scores.
- Keep current paid-API restrictions and the cumulative USD 100 ceiling; this
  document does not authorize spending, inference or an experiment launch.
- Require a separate implementation/preflight check; documentation is not
  evidence that these prospective checks have already passed.

## 10. Methodological references and limits

[Zheng et al. (2023)](https://arxiv.org/abs/2306.05685) document position,
verbosity and self-enhancement biases in LLM judging. Their results do not
validate this project's judges or substitute for human agreement measurements
on these data.

[Min et al. (2023), FActScore](https://aclanthology.org/2023.emnlp-main.741/)
motivate examining smaller factual assertions against evidence. The proposed
located-allegation audit here is not an implementation of FActScore and must
not be reported under that metric name. Neither reference establishes the
validity of this project's adapted Credibility/Conformability rubric.
