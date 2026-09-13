# WarrantRoute ACE-Inspired Thematic Analysis Experiment

Date: 2026-09-09 KST. Version: 1.1.
Status: prospective design; implementation and inference are not complete.
Experiment family: `warrantroute_ace_ta`.

Execution update (2026-09-09 KST): an implementation of this design is now
available in [the ACE TA runner](../../experiments/warrantroute_ace_ta/README.md).
The initial live run is undergoing technical qualification before full
continuation. Its frozen execution_protocol.md records the implemented routing,
retrieval, update and failure rules. The user authorized CaChe as a within-source
diagnostic, with no shared records or exact text between its 20 development and
100 evaluation packets. The other three corpora passed source-disjoint packet
selection. This explicitly resolves the CaChe split limitation below for private
diagnostics; it does not make CaChe source-independent. Historical design text
below describes the proposal and must not substitute for the run's frozen contract.

## 1. Purpose and continuity

Compare source-grounded thematic analysis under Generalist, Fixed role,
All roles and WarrantRoute, using Qwen3 8B, Llama 3.1 8B and Gemma 3 4B.
Keep the earlier four-dataset layout: Dreaddit, GoEmotions, CaChe and
ParlaMint-GB. Preserve 100 evaluation packets per dataset as the initial
target, recorded as metadata rather than embedded in the experiment name.

The user requested multiple analytic agents and ACE-inspired learning while
keeping the experiment similar to the previous study. The primary design
therefore preserves same-model comparisons and adds a development-time
TA generation and combined Playbook Updater cycle to WarrantRoute.

The previous experiment reviewed a supplied constructed claim. This experiment
generates codes and provisional themes from evidence. Its new outcomes cannot
be combined with historical review-quality scores as if the task were unchanged.
All four methods must produce and be evaluated on the new common task.

## 2. What comes from ACE

The locally available [ACE paper](../../../ace_paper/original_sources/paper/ace_arxiv_2510.04618.pdf),
Section 3 and Figure 4, separates generation, reflection and curation, with
localized Playbook updates and context refinement. The paper supports offline
adaptation as well as online adaptation. These roles need not use different
model families. Model parameters remain fixed.

Our adaptation makes the Generator a routed TA team, adds explicit evidence
and scope checks, and uses model-based development feedback. Those choices
are WarrantRoute extensions, not claims that ACE itself specifies this TA
workflow or validates its semantic judgments.

Version 1.1 combines the Reflector and Curator responsibilities into one
Playbook Updater call. Its response contains both a feedback-grounded lesson
and a proposed delta. This is an ACE-inspired merged-role variant, not a
replication of ACE's separate Reflector and Curator. A formatter is deterministic
code, not another semantic agent.

The primary experiment uses offline adaptation: learn a Playbook on development
data, then freeze it for evaluation. A future online experiment would score
each output before incorporating its feedback and report the resulting learning
curve separately. It is not enabled in this design.

## 3. Shared analysis task

Each method receives identical approved source evidence, source identifiers,
available context, a frozen dataset-specific research question and the same
output schema. Preserve stored text and order without new shortening,
translation, artificial defect injection or source recombination.

Do not send constructed target claims, flaw labels, truth-map fields or builder
hints to agents performing source-based TA. Preserve them separately only for
historical traceability. This changes the task input contract explicitly.

The common output contains evidence-linked codes with definitions, provisional
subthemes/themes with a central concept, supporting and qualifying passages,
scope limits, alternative interpretations and unresolved context gaps. A theme
is optional when the evidence supports only codes. Do not force a hierarchy
or label frequency as prevalence. Outputs from a short packet are local analytic
candidates, not corpus-wide themes or evidence of thematic saturation.

The analytic contract is a structured, evidence-linked coding and theme-building
workflow. Freeze research questions and code/theme boundary instructions before
generation. It must not be described as a complete reflexive thematic analysis
or as biomedical expertise established by prompting.

## 4. Methods and model conditions

| Method | Proposed execution on each evaluation packet |
| --- | --- |
| Generalist | One analyst produces the common TA output in one pass. |
| Fixed role | One qualitative-methods analyst produces the same output in one pass. Use this global role consistently, not whichever role scores best on test data. |
| All roles | Generalist, methods and domain analysts independently produce candidates; one fixed synthesis call combines them into the common output while retaining conflicts. |
| WarrantRoute | Independent proposer and evidence scout, routed methods/domain challenge, bounded revision and issue-owner recheck, using a learned frozen Playbook. |

All roles synthesis is a new prospective rule. Historical All roles combined
reviewer flags, so its old scores are not substitutes for this baseline.
The domain role follows the corpus: stress narratives, emotion expression,
health-related group discussion or parliamentary context. It must not impose
clinical interpretations on nonclinical data.

For each of these four methods, run three conditions:

| Condition | Model used for every method agent |
| --- | --- |
| qwen_only | Qwen3 8B |
| llama_only | Llama 3.1 8B |
| gemma_only | Gemma 3 4B |

Separate agent calls provide different responsibilities and information access,
not statistical independence. They may execute serially on one local machine.
Role prompts, schemas, decoding limits and routing rules are shared across
model conditions. A mixed-family team is a separate future ablation.

There are 48 reporting cells and 4,800 primary final-output slots if all 400
evaluation packets qualify. WarrantRoute occupies 1,200 of those slots. Agent
calls, development episodes and judge calls are additional, not extra samples.

## 5. WarrantRoute analytic agents

| Agent | Responsibility |
| --- | --- |
| Proposer | Build evidence-linked codes and provisional themes. |
| Evidence Scout | Independently map evidence, qualifications and context gaps before seeing the proposed analysis. |
| Methods Challenger | Check evidence-to-code/theme links, negative cases and analytic boundaries when activated. |
| Domain Challenger | Check attribution, domain meaning and unsupported causal or clinical scope when activated. |
| Reviser | Address located material issues without erasing unresolved objections. |
| Playbook Updater | During development, analyze recorded feedback, extract a procedural lesson, and propose a localized delta with scope and exceptions in one call. |

There are six distinct method-agent roles: five for TA and one for memory
adaptation. The final quality Judge is a separate evaluator. The Playbook is
persistent data, not an LLM. Routing, schema validation, formatting, hashing,
delta application and storage are code, not additional agent roles.

The Generator function consists of the first five agents. The inner process is:

```text
source packet + research question + retrieved Playbook rules
  -> independent Proposer and Evidence Scout
  -> deterministic evidence-reference checks
  -> fixed routing policy selects Methods, Domain, both, or neither
  -> located issue register
  -> up to two revisions with evidence/issue-owner rechecks
  -> final TA output plus unresolved issues and technical status
```

Retain the previous maximum of 12 inner-loop calls per packet. A no-issue
decision requires completed checks. Exhausted budget or disagreement yields
an unresolved status; it is neither a quality pass nor necessarily a technical
failure. Judge any complete final artifact independently of termination.

During development, the Evidence Scout makes one additional feedback call
after the inner loop. It reviews the final artifact and recorded checks; this
is a separate invocation of an existing role, not an eighth or seventh method
agent. It is not independent ground truth. The Playbook Updater receives the
resulting structured feedback and current scoped rules. The development flow is:

```text
Playbook P_t -> TA inner loop -> final artifact and checks
  -> Evidence Scout development feedback (one extra call)
  -> Playbook Updater (lesson + proposed delta, one call)
  -> code validates and applies eligible operations -> Playbook P_(t+1)
```

During evaluation, only the TA roles execute within WarrantRoute. They read a
frozen Playbook and cannot update it. The separate Judge evaluates the final
artifact without access to the development memory history. Each model condition
uses its own model for all six method roles; the fixed final Judge is shared
across conditions. Agent count does not mean simultaneous model instances.

## 6. Development and Playbook updates

Use one deterministic source-component-disjoint development partition per
dataset and the same ordered development episodes for all three models. The
target is 20 development packets per dataset, subject to eligibility audit.
No qualifying additional data or disjoint split has yet been verified.
Never take development feedback from the 100 evaluation packets and still call
them untouched evaluation. If disjoint development is unavailable, record that
blocker or explicitly use a development-only pilot; do not silently shrink or
relabel the evaluation inventory.

Each model starts from an identical seed Playbook and maintains separate memory
per dataset/model. This prevents order-dependent transfer between corpora and
prevents one model from inheriting another model's reflections.

For one fixed development pass:

1. Produce a TA artifact with the current Playbook.
2. Collect deterministic reference/quotation checks and an evidence-linked
   critique in one additional Evidence Scout call. Record model-only feedback
   provenance; do not treat agreement as verified correctness.
3. Invoke the Playbook Updater once. Return a concise lesson, feedback record
   references, scope, exceptions, and at most three proposed ADD/REVISE/DEPRECATE
   operations. Returning no operations is valid when feedback is insufficient.
4. Apply schema, ID, scope, duplicate and source-text-leakage checks. An operation
   must reference an existing feedback event and the expected parent Playbook
   version. Reject structurally invalid, stale or unlinked operations and retain
   the full rejected delta. These checks do not establish semantic correctness.
5. Commit eligible operations as a versioned delta deterministically. Unaffected
   bullets remain intact. Preserve prior versions and mark lessons as based on
   model feedback, not independently validated. The semantic acceptance and
   contradiction policy still needs specification before implementation freeze.

Only reusable procedures belong in the Playbook. Keep participant text, findings,
answer keys and study-specific codebooks in separate stores. Helpful/harmful
counters record feedback events, not probabilities or independent confirmations.
Use a proposed cap of 60 active bullets per memory and at most six retrieved
rules per inner call, including linked exceptions. At the cap, retain excess
proposals as candidates instead of silently truncating rules or source inputs.

After the fixed development pass, freeze each memory regardless of whether the
observed feedback was favorable. No best-checkpoint selection on evaluation.
The autonomous model-feedback update policy is a prospective private-diagnostic
alternative to the older human-approved memory design. It does not waive
manuscript eligibility requirements or claim expert validation.

## 7. Evaluation and metrics

Keep Credibility and Conformability as headline dimensions, with a new rubric
explicitly targeting the final TA artifact rather than its review text.

- Credibility: codes and provisional themes represent the supplied evidence at
  a defensible scope; the evidence-to-interpretation links and relevant exceptions
  support the material analytic claims.
- Conformability: material analytic content is traceable to source evidence and
  preserves attribution, negation, uncertainty and context without inventing
  premises or quotations.

Each dimension returns true, false or unresolved with cited evidence and a
decisive criterion. A demonstrated material violation gives false. Otherwise,
an unassessable required claim gives unresolved; true requires the positive
conditions. Invalid or missing outputs remain technical missingness, not
semantic false or an automatic pass. Codes-only outputs are judged on whether
that scope is justified, not automatically penalized for lacking themes.

Use one fixed Qwen3 8B judge configuration for the primary diagnostic to remain
close to the previous experiment. One call per final artifact returns both
dimensions. Freeze prompts, model digest and decoding across all tested models.
Hide method/model identities, Playbook history, internal acceptance decisions and
historical target labels. Disclose Qwen self-family bias. Final judge feedback
never reaches the Playbook Updater.

Report per-dimension T/F/U/technical counts, binary coverage and the pass rate
T/(T+F), always alongside its resolved denominator. Also show the full-inventory
lower/upper bounds T/N and (T+U+technical)/N, labeled as bounds, not binary
success estimates. Zero resolved cases yield N/A. Do not fill missing results
by repeated judging until they pass.

Original intended-flaw TP/N and Recall do not apply to newly generated TA
without an adequate reference annotation. Retain those metrics only in the
separate historical review experiment. The new 48-row table uses Dataset,
Method, Model, N, Credibility, Conformability and coverage; detailed missingness,
calls, tokens, latency and unresolved-loop rates belong in a companion export.

## 8. Comparisons and cost

Prespecify WarrantRoute versus All roles within each dataset/model as the main
descriptive comparison. Report all cells and missingness. Historical values
are context only. Learning curves use development episode number; development
outcomes are not included in final evaluation means.

The first study compares complete methods with measured unequal costs. It does
not isolate routing, extra calls or memory as the sole cause of a difference.
A later matched ablation can compare the same WarrantRoute loop with seed versus
learned Playbooks. Development and curation costs must be reported separately
and included in total cost claims.

Planned ceilings before technical retries are 80 development episodes per model,
14 calls per development episode (12 inner plus one Evidence Scout feedback
call and one combined Playbook Updater call),
and 12 calls per WarrantRoute evaluation packet. Generalist and Fixed role each
use one call; All roles uses four. With the proposed inventory this is at most
24,960 generation/adaptation calls plus 4,800 final judge calls. The merged
role saves at most 240 planned development calls relative to version 1.0;
it does not reduce the evaluation-loop budget. Actual routing
can use fewer. No reliable ETA follows from the old 38-hour experiment alone.

Local Ollama is the default; no paid inference is authorized by this document.
Any later paid path retains the cumulative USD 100 ceiling and must reserve
worst-case call cost before dispatch. Record token usage even for failed calls.

## 9. Implementation and launch requirements

The current runtime reviews supplied claims and has a static Playbook. It does
not yet implement this source-to-TA task, autonomous memory updates or TA judge.
The prepared `warrantroute_ace_playbook_static_20260909` bundle remains a separate
unlaunched engineering condition, not the executable version of this design.

Implement shared TA prompts/schema, source eligibility and disjoint partitions,
development feedback and delta storage, final-memory freezing, all four method
runners, and the TA-specific judge/export. Freeze research questions and exact
retry policy before pilot inference. Proposed technical policy: one retry for
an explicit connection/HTTP service failure, no retry of valid false/unresolved
verdicts, retain every attempt, and reconcile timeouts before resubmission.

Test evidence IDs, exact quotations, memory isolation, delta preservation,
evaluation freeze, resume identity, missingness and denominator accounting.
Then run a separately labeled small pilot across all datasets/models, audit
failures, and prepare a new immutable full-run contract. Do not claim readiness
or start the long experiment solely because this design document exists.

## 10. Related local records

- [Evidence-grounded review criteria](objective_review_criteria_v1.md).
- [Flaw criteria audit](flaw_criteria_audit_v1.md).
- [Earlier inner/outer loop design](../../experiments/direction_h_human_in_loop/protocol/ace_biomedical_tight_loop_v1.md).
- [Existing executable loop guide](../../experiments/rq2_role_prompted_llm/WARRANTROUTE_LOOP_EXPERIMENT_GUIDE.md).
- [Biomedical Playbook feedback design](../../../ace_paper/BIOMEDICAL_PLAYBOOK_FEEDBACK_DESIGN.md).
