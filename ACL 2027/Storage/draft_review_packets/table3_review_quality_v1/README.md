# Table 3 Review-Quality Experiment Guidelines

Version: v1, execution revision 5. Updated: 2026-09-04 KST.

**Status: execution authorized.** The user requested execution on 2026-09-04.
The runner is implemented and tested. A run-specific immutable manifest and
mutable progress.json record actual execution, not this guideline header.
The rubric from revision 3 is unchanged. Diagnostic artifacts remain under
Storage; authorization does not certify completed or manuscript-eligible results.

## 1. Relationship to the Previous Experiments

Two previous experiments provide the reference settings:

- The n100 detection experiment supplies the packets, reviewer models, frozen
  role prompts, repaired reviewer outputs, and method definitions.
- The Dreaddit n=5/n=25 quality evaluations supply the local judge, binary
  assessment pattern, and four-field response format.
- The n100 detection queue skipped quality judging. It did not already measure
  these two review-level metrics.

| Component | Historical reference | Current base design |
| --- | --- | --- |
| Packets | Four corpora, balanced n100 each | Reuse the exact packet IDs and files |
| Reviewer models | Qwen3 8B, Llama 3.1 8B, Gemma 3 4B | Reuse their repaired outputs |
| Generalist | generalist role | Same role |
| Fixed role | qualitative_methods shared across models after prompt repair | Same role; do not reselect it from scores |
| All roles | generalist + qualitative_methods + domain | Same members, assessed together as one review bundle |
| Quality judge | qwen3:8b in the n=5/n=25 runs | qwen3:8b for every primary evaluation |
| Judge decoding | temperature=0, top_p=1 | Same |
| Judge budget | num_ctx=8192, num_predict=384, timeout=240 seconds | Same starting configuration |
| Response | Two booleans and two rationales | Same four field names; null only for genuine unassessability |
| Rate | Percentage of positive decisions | Separate pass percentage for each completed n100 row |
| Assessed object | A shared qualitative claim | A method/model-specific review bundle |

The necessary conceptual change is the assessed object. Reusing the old prompt
unchanged would assess the input claim, not the quality of the different reviews.
The rubric must therefore be adapted, not described as an exact replication.

The earlier draft's gpt-oss primary judge and larger token budgets are removed
from the base design. Additional judges and human audits are optional extensions.
However, malformed booleans must not be silently converted to false, failed
calls must not disappear from denominators, and injected answer hints must not
be presented as evidence. Historical implementation defects are not reproduced.

## 2. Data and Method Contract

Use the existing n100 prompt-identity-repair configuration and no other packet
bank or reviewer output version.

| Dataset | Existing run ID | Packets | Stored valid role outputs |
| --- | --- | --- | --- |
| Dreaddit | dreaddit_dev580_working_v1 | 100 | 900 |
| GoEmotions | goemotions_train_all_working_v1 | 100 | 900 |
| CaChe | agyw_focus_groups_eval765_working_v1 | 100 | 900 |
| ParlaMint-GB | parlamint_gb_fullsample_eval100_working_v1 | 100 | 900 |

These inventory counts were checked on 2026-09-04. Packet file hashes matched
the repair configuration. Here, valid means the stored output passed its
existing format checks, not that its interpretation is correct.
Preserve the historical GoEmotion display key when joining the existing table.

For every packet and reviewer model, construct these bundles:

| Method | Included saved role outputs | Primary judge calls |
| --- | --- | --- |
| Generalist | generalist only | 1 |
| Fixed role | qualitative_methods only | 1 |
| All roles | generalist, qualitative_methods, domain | 1 for the entire bundle |

Do not generate a new synthesis for All roles. Retain all substantive diagnoses
and rationales. Its old detection result was a union of flags; its new quality
result is a judgment of the complete review bundle, not an OR of role scores.
Do not take the best member, a majority vote, or an average of role-level grades.
A supported finding does not cancel a different unsupported allegation.

WarrantRoute remains deferred, consistent with the baseline-first scope.
Its 12 table rows have older output/routing provenance. Do not combine repaired
outputs with old routes and silently call that the same experiment.
When explicitly added, freeze the route policy and compatible output version.
A both route selects the two specialists, not all three roles. Missing routes
are errors, not permission to use a fallback policy.

## 3. Exactly How Many Times Is Each Sample Run?

A sample here is a **packet**, not a unique source document. Different packets
can share source texts. An evaluation unit is:

```text
(corpus_id, packet_id, reviewer_model_id, method, reviewer_output_version)
```

### Default execution

| Quantity | Exact default |
| --- | --- |
| New reviewer generations | 0; reuse existing reviews |
| Accepted historical outputs consumed per packet-role-model | 1 saved output |
| Primary judge evaluations per packet-method-model | 1 |
| Metrics returned in that evaluation | 2, in the same response |
| Primary evaluations per packet for one reviewer model | 3 methods x 1 = 3 |
| Primary evaluations per packet across all reviewer models | 3 models x 3 methods = 9 |
| Primary evaluations per dataset | 100 packets x 9 = 900 |
| Primary evaluations across four datasets | 4 x 900 = 3,600 |
| Planned binary decisions across both metrics | 3,600 x 2 = 7,200 |
| Planned primary table rows | 4 datasets x 3 methods x 3 models = 36 |
| Planned denominator per row and metric | 100 |
| Scheduled repeats of a successful primary evaluation | 0 |

One call returns both metrics. There are not two separate primary calls for
Credibility and Conformability. Existing role outputs are reused in more than
one method bundle; this does not create new reviewer generations.

One accepted historical output does not establish that the original generation
was attempted only once. Earlier retries and the 229 prompt-repair regenerations
belong to historical execution, not new primary judging.

### Canary and technical retries

The operational canary contains one deterministically selected packet per corpus
and all nine method/model combinations: 4 x 9 = 36 primary units.
These units are part of the 3,600, not an extra batch, if their frozen request
contract is unchanged.

A transport or schema error permits at most two additional attempts with the
same request contract: at most three recorded attempts for one primary unit.
Use the first format-and-identity-valid response. Preserve every failed attempt.
A valid false or null decision is not eligible for a score-seeking retry.

Therefore, the base plan has 3,600 logical evaluations and up to 10,800 recorded
request attempts under the retry limit, not 10,800 independent samples.
Timeouts can leave server-side work unresolved; do not infer exact completed
server executions from client request counts alone.

If the canary requires a prompt, budget, model, or sanitizer change, create a
new contract revision. Keep old attempts separately and do not mix them into
the final primary denominator. Repeated schema failure is not a quality failure.

### Optional repeat and validation modules

These modules are disabled in the base plan and require a separate decision
to activate. Select 10 packets per corpus before inspecting scores, using
SHA256("human-audit-v1", 20260904, corpus_id, packet_id). Reuse the same selected
40 packets for all optional modules.

| Optional module | Units | Additional judgments per selected unit | Additional LLM calls |
| --- | --- | --- | --- |
| Second judge | All 9 combinations on each of 40 packets | 1 by the secondary judge | 360 |
| Same-request repeat | Generalist, 3 models, 40 packets | 1 additional primary-judge evaluation | 120 |
| Order sensitivity | All roles, 3 models, 40 packets | 1 evaluation with reversed member order | 120 |
| Human audit | All 9 combinations on each of 40 packets | 2 independent human assessments | 0 |

With every optional LLM module enabled, the plan is 3,600 + 360 + 120 + 120 =
4,200 logical judge evaluations, excluding retries and separate development
checks. Each selected packet has 24 evaluations across the complete optional
plan, while every other packet has the base nine.

Keep primary scores unchanged. Secondary, repeat, and order-reversal judgments
are sensitivity results, not extra samples in the n100 denominator.
The human audit comprises 360 bundles rated by two people, or 720 human bundle
assessments, each containing two metric decisions. Human availability is not
yet confirmed.

## 4. What Exactly Counts as a Pass?

**A pass means that the review meets the frozen review-quality rubric according
to the judge. It does not mean expert-verified correctness.**

This is not label-match grading. Do not provide the intended flaw, truth map,
old TP/Recall, or target label to the judge. A matching flaw label is neither
sufficient nor necessary for a quality pass.

Material means consequential enough to change a diagnosis, disposition,
scope, or interpretation of evidence. Minor wording differences do not count.

### Review Credibility: adequacy of the review's judgment

Return true only when all four conditions hold:

- C1: The review gives a meaningful, specific assessment of the supplied claim.
  Merely stating that a flaw exists, or listing labels without an assessment,
  does not satisfy this condition.
- C2: Its substantive diagnoses reflect the actual meaning of the claim and
  source context, without material misreading, exaggeration, or reversal.
- C3: Its diagnosis and accept/revise/reject/escalate disposition are defensible
  together. It does not miss an obvious issue that would materially overturn
  its overall assessment. Exhaustive discovery of every possible issue is
  not required.
- C4: The complete bundle contains no material unwarranted allegation or
  unresolved factual contradiction. Defensible interpretive differences are
  not automatically contradictions.

For an assessable unit, false means at least one condition fails.
A justified acceptance or a specific, appropriate reviewer abstention can pass.
Do not force a positive diagnosis merely because these are working flaw packets.

### Review Conformability: traceability and grounding

Return true only when all four conditions hold:

- F1: The review itself supplies a discernible basis for each material
  diagnosis, traceable to the reviewed claim or supplied source context.
- F2: The referenced evidence exists and is correctly linked to its source,
  speaker, polarity, time, and context.
- F3: That evidence supports the diagnosis and its scope without requiring
  invented material, unsupported external assumptions, or an unjustified leap.
- F4: These conditions hold for every material allegation in the bundle.
  One well-supported allegation does not compensate for another unsupported one.

For an assessable unit, false means at least one condition fails.
Exact excerpt IDs are helpful but not mandatory: an identifiable passage or
comparison is enough. Conversely, adding an ID does not establish support.
The judge must not invent a missing warrant on the reviewer's behalf.

The two dimensions overlap but are evaluated separately. Do not combine them
into one score or force their values to agree. These semantic checks are applied
by the judge; a schema validator cannot establish that the judgment is true.

### Worked boundary cases

These are rubric illustrations, not measured experiment results.

| Review behavior | Credibility | Conformability |
| --- | --- | --- |
| Substantively adequate diagnosis with a correct, traceable warrant | Pass | Pass |
| Adequate specific diagnosis, but its stated warrant cannot be traced | May pass if C1-C4 hold | Fail |
| Accurate, traceable observations but an obvious consequential omission | Fail | May pass if F1-F4 hold |
| Intended label matched, but support relies on a fabricated quotation | Fail | Fail |
| Different label from the intended target, with a sound assessment and warrant | May pass | May pass |
| Generic "there is a flaw" without an identifiable assessment or warrant | Fail | Fail |
| Correctly identifies a genuine context limit and appropriately abstains | May pass | May pass |
| Essential context unavailable to the evaluator | Null for affected dimension | Null for affected dimension |

A real flaw in the claim does not automatically make a review pass. The judge
assesses the review's account of that flaw. It must not simply grade the shared
claim and copy that score across methods.

## 5. Response Format, Errors, and the Percentage

Use the previous judge's four field names:

- credibility: boolean, or null only for genuine evaluator unassessability.
- conformability: boolean, or null under the same rule.
- credibility_rationale: nonempty concise explanation, at most 60 words.
- conformability_rationale: nonempty concise explanation, at most 60 words.

The prompt defines a review-level adaptation even though these field names are
retained. Label records with a new protocol ID and judged object.
Do not merge them with the old claim-level records.

A rationale should identify the failing condition or explain why the conditions
hold and refer to relevant anonymous review/source IDs when available.
Do not request or store hidden chain-of-thought or source quotations.
An unsupported review receives false, not null. Use null only when missing or
uninterpretable evaluation context prevents a responsible decision; explain why.

Require literal JSON booleans or null. Reject strings such as "true", numeric
surrogates, missing fields, extra fields, empty rationales, mismatched IDs, and
truncated responses. Do not normalize malformed or missing values into false.
Word-count and actual-ID checks belong to the runner, beyond JSON Schema.

For each dataset-method-model row, separately for each metric:

```text
P = number of valid true decisions
F = number of valid false decisions
U = unassessable, missing, or unresolved-error decisions
N_planned = 100
P + F + U = 100

If U = 0:
    metric_percent = 100 * P / 100
Else:
    final metric cell = N/A
    progress record retains P, F, U, and coverage

coverage_percent = 100 * (P + F) / 100
```

For illustration only, 72 true and 28 false decisions produce 72.0%.
Seventy-two true, 23 false, and five unresolved items do not produce 72/95 as
the final n100 result. The final cell remains N/A until coverage is resolved.
Do not treat an API error as a substantive quality failure.
One dimension may be complete while the other remains unassessable.

The primary table reports rubric pass rates, not verified accuracy.
If human validation is later performed, report its agreement measures separately.

## 6. Fixed Judge and Fair Comparison

The base judge is qwen3:8b for all three reviewer models and all methods.
This follows the historical n=5/n=25 quality runs. The observed current digest is
recorded in design.json. The old quality records did not record a digest, so
bit-identical historical weights cannot be certified retrospectively.

Use the historical local Ollama request pattern: format=json, stream=false,
temperature=0, top_p=1, num_ctx=8192, num_predict=384, timeout=240 seconds.
The historical script did not explicitly send a generation seed or think
option. Do not silently add either to the base request. Record the actual
runtime version, template, and effective reasoning behavior before freezing.
The seed 20260904 in sampling/order procedures is not a generation seed.

The judge instruction is identical for every primary unit. Only the packet and
review bundle vary. Do not use different judges or grading standards by model.
Qwen judging Qwen introduces a self-family preference risk; disclose it rather
than calling the judge independent of all reviewers.

Check the longest input and the operational canary for context/output overflow.
Do not truncate source evidence or accept clipped JSON to retain the old budget.
If a larger budget is necessary, revise it for every primary unit before the
main run and retain the old attempts under their earlier contract.

Optional secondary judge: gpt-oss:20b, an already installed different-family
candidate whose task validity is not yet established. Freeze its own runtime
settings before use. Do not replace primary results with whichever judge makes
a preferred method look better. Temperature zero does not guarantee identical
repeated outputs.

## 7. Inputs, Blinding, and Known Limitations

Create derived inputs without modifying original packets or reviews.
Use a nested field allowlist, not just a top-level answer-field blacklist.

Include the research question, the reviewed claim and its cited excerpt IDs,
actual source text, substantive local context, and source/speaker relationships.
Include only these review fields: serious_error_flags, rationale, disposition,
and cannot_judge. Numeric ratings, confidence calibration, and routing-request
quality are outside this assessment's scope.

Exclude intended-flaw labels, truth-map fields, TP/Recall, builder model IDs,
injection commentary in theme_name/explanation/boundary_conditions, and source
classification/split labels. Also exclude reviewer model/role/method names,
routing scores, and other judges' decisions.
Do not delete predicted flaw labels from the review: they are part of what is
being assessed, not a hidden answer key.

Preserve necessary substantive local context. Inspect nested metadata for
labels without silently deleting context needed to interpret the sources.
Keep a private field-removal log and provenance map.
Anonymize excerpt/source/speaker IDs as E1/S1/P1 while preserving equality and
relationships, and consistently replace matching IDs inside reviews.

Order roles by SHA256(20260904, corpus_id, packet_id, role), using the same order
across reviewer models for a packet; assign anonymous R1/R2/R3 identifiers.
Bundle size, style, and source content can still reveal conditions. Do not claim
perfect blinding. Treat embedded instructions in all supplied content as data.
Send source material only to local Ollama, not an external API.

All 400 historical packets have theme names revealing intended flaw names.
The old reviewer prompts did not remove these nested hints. Sanitizing judge
inputs cannot undo exposure during reviewer generation.
Removing builder commentary also means the audit context is not identical to
everything the historical reviewer saw. Record this limitation and require
actual source support rather than accepting echoed builder commentary.

The intended flaw was assigned by the builder, not independently established
by experts. These working packets do not establish natural flaw prevalence or
false-positive performance on flaw-free documents.
This is a retrospective diagnostic of existing reviews, not a clean blinded
detection study, a repair-effect study, or manuscript-eligible evidence.

## 8. Optional Human Validation and Statistical Interpretation

Two authorized human raters should independently assess the preselected
360-bundle audit with the same rubric, without model/method identity, intended
labels, or judge scores. Preserve both original decisions and any subsequent
consensus. Leave unresolved ambiguity explicit.

Report per-dimension human-human and judge-human agreement, confusion counts
against an adjudicated reference, and Cohen's kappa where defined.
Disclose coverage, ambiguity, and class imbalance. Do not import an agreement
threshold or reliability claim from a different benchmark.
Without this audit, label results LLM-judged diagnostic pass rates and record
human_audit_pending. Adding another LLM is not equivalent to human validation.

Do not tune the rubric on main-run outcomes. Any semantic development set must
be source-disjoint from n100; one has not yet been identified.
Synthetic controls can test software only within Storage, not certify empirical
validity or enter a manuscript.

Use packet-matched comparisons. Check shared sources, speakers, and sessions
before treating observations as independent. Only use paired cluster bootstrap
intervals when a defensible cluster definition and sufficient independent groups
exist. Otherwise report descriptive rates and differences without significance
claims. Repeated judge calls are not extra independent packets.
Do not copy the old Wilson intervals to these new metrics.

## 9. Execution, Provenance, and Table Export

Runner: experiments/rq2_role_prompted_llm/scripts/run_table3_review_quality.py.
Use the isolated .venv/bin/python in this guideline directory. Dependency:
jsonschema==4.26.0. The runner freezes source files, derived payloads, request
hashes, the judge digest/template, and the Ollama/Python versions before inference.

1. Prepare: verify the 400 packet IDs, input hashes, 3,600 saved role outputs,
   and exact role/model bindings. Construct 3,600 anonymous evaluation units.
2. Freeze: bind the prompt, schema, sanitizer, runtime settings, model digest,
   source manifests, and output hashes to a new run contract.
3. Canary: check 36 included units and input sizes. Do not tune on score rankings.
4. Judge: issue one local request at a time with the bounded retry policy.
   Preserve raw responses, every attempt, identities, hashes, and timing.
5. Validate: check format, references, unique unit keys, and per-metric coverage.
   Distinguish schema validity from substantive judgment validity.
6. Aggregate: update only matching quality cells in the existing MD/CSV.
   Preserve TP/N, Recall, ordering, and every original reviewer output.

Use a single-run lock, atomic writes, and resumable manifests. Never overwrite
an existing valid record with a changed request hash.
The longest prompt by UTF-8 byte count is evaluated immediately after the 36
canary cases if it is not already among them. It is an existing primary unit,
not an additional sample. Byte length is only a probe-selection heuristic.
Every request additionally checks actual prompt tokens and the local server log
for truncation. An unverifiable log or capacity failure blocks execution.
Shared source and source-record IDs retain one consistent anonymous alias.
Private provenance, the frozen allowlist implementation, and original source
hashes record how derived inputs were produced.
An interrupted in-flight call with no saved response consumes a technical
attempt with unknown outcome. It is never silently erased on restart.
Stored responses exclude private thinking text, retaining its character count,
the final answer, performance metadata, validation errors, and attempt identity.
Track planned units, completed binary pairs, per-metric P/F/U, actual request
attempts, retries, and optional-module progress separately.
Estimate time from observed canary/main-run throughput, not an invented duration.

The base completion target is 36 evaluated rows, with WarrantRoute's 12 rows
explicitly deferred. Do not call all 48 rows evaluated.
The five-minute monitor must distinguish design, preparation, running,
incomplete coverage, and completion. An old detection validated_complete status
does not certify a new quality run.

Keep the existing table's quality cells N/A until matching evaluations exist.
The display headers may remain Credibility (%) and Conformability (%), but the
table note must identify these as review-level adaptations, name the judge and
protocol, and disclose human-audit status. Do not modify manuscript files.

## 10. Sources and Design Artifacts

Thematic-LM discusses thematic representation and data-groundedness under
Credibility and Confirmability. The supplied definitions motivate this design,
but these separate review-level binary rules are a new operationalization, not
an exact reproduction or an already validated metric.
The requested table spelling Conformability is retained, with that distinction
documented. The publisher full text was not available in this check; the public
author-version search text and user-supplied definitions were consulted.
[Thematic-LM author version](https://openreview.net/pdf?id=jiv0Gl6sto),
[publication DOI](https://doi.org/10.1145/3696410.3714595).

Position, verbosity, and self-enhancement biases motivate the optional judge
checks; results from another benchmark do not establish validity here.
[Zheng et al., 2023](https://arxiv.org/abs/2306.05685).

- [n100 source configuration](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/config/table3_n100_prompt_identity_repair_v1.json>)
- [Historical claim-level quality judge](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_working_quality_judge.py>)
- [Historical method scorer](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py>)
- [Current results table](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_warrantroute_n100_final.md>)
- [Design configuration](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/design.json>)
- [Judge prompt](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/judge_prompt_v1.txt>)
- [Response schema](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/judge_output.schema.json>)

Pre-execution checks cover all 400 packet sanitizations and ten focused tests
for schema validation, provenance masking, bundled reviews, null/false handling,
coverage, crash recovery, immutable attempts, and protected table exports.
Actual progress is recorded in each run directory. These software checks do not
replace semantic calibration or independent human auditing, neither of which
has been completed.

## 11. Technical Run History

The initial run review_quality_n100_20260904_r1 stopped after one response.
Its overly broad log check treated the normal `truncated = 0` message as a
failure. No response was accepted and no quality percentage was exported.
The corrected guard distinguishes zero/false from actual truncation warnings.
Run review_quality_n100_20260904_r2 restarts the same included canary with an
unchanged judge, rubric, prompt, and generation settings. The earlier attempt
remains archived under r1 and is excluded from r2, not chosen by its score.
There are 3,600 planned primary evaluations in r2 and one additional archived
technical attempt in r1. Frozen contracts are not edited in place.

Active run:
[Progress](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/runs/review_quality_n100_20260904_r2/progress.json>),
[Frozen manifest](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/runs/review_quality_n100_20260904_r2/manifest.json>).
After the canary passes, the persistent session is named
`table3_review_quality_n100_r2`. The existing five-minute monitor targets this run.
No valid primary decision is regenerated when moving from canary to main run.

## 12. Completed Technical Repair

The base run ended with 3,592 valid binary responses and eight units that had
exhausted all three technical attempts. Six repeatedly returned duplicate JSON
keys, one exceeded the 60-word Credibility-rationale limit, and one repeatedly
used an unknown evidence identifier. These failures were not scored as false,
imputed, or silently omitted.

The user requested repair on 2026-09-04. A separate frozen repair contract
re-evaluated all and only those eight units. It retained the same Qwen3 8B
judge, source payloads, substantive rubric, pass rules, temperature, context,
and output-token budget. The uniform technical revision used the frozen JSON
Schema as Ollama's structured-output format, requested at most 45 rationale
words as margin under the unchanged 60-word validator, and limited rationale
identifiers to CLAIM and review IDs present in the payload. Original attempts
remain preserved under the base run.

All eight repair units passed on their first repair attempt. The combined result
therefore contains 3,600/3,600 binary decisions for each metric and completes
all 36 baseline quality rows. TP/N, Recall, row ordering, and all 12 WarrantRoute
rows are unchanged. WarrantRoute quality remains deferred, so its 12 quality
cells remain N/A. This completion does not change the human-audit or manuscript-
eligibility limitations.

- [Repair final](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/repairs/review_quality_n100_20260904_r2_schema_r1/final.json>)
- [Repair manifest](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_review_quality_v1/repairs/review_quality_n100_20260904_r2_schema_r1/manifest.json>)
- [Completed baseline table](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_warrantroute_n100_final.md>)
