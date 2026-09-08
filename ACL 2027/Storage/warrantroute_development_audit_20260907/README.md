# WarrantRoute: Deep Implementation Audit and Thematic Analysis Development Plan

Date: 2026-09-07. Status: analysis and proposed design, not an implemented upgrade.

This is an internal development record. It includes observations from historical controlled-flaw packets and synthetic software probes. It must remain under Storage and must not be incorporated into a manuscript, appendix, or submission as empirical evidence. No model calls, new corpus experiments, manuscript edits, or production-code changes were made for this audit.

## 1. Main Finding

**The executable WarrantRoute is a bounded claim-review and revision system with an optional frozen methodological Playbook. It is not yet a corpus-level thematic analysis system, and its Playbook does not currently learn from feedback.**

The most valuable next development is to make the *objects being analyzed and changed* explicit: source evidence, analytic codes, coding decisions, themes, and procedural rules. Adding more reviewers to the current single-claim object would not supply those missing capabilities.

Keep the method name **WarrantRoute**, the five-role pool, the four routing modes, and one LLM throughout each experimental condition. Develop a versioned analytic workspace underneath them. First repair revision freshness and experiment identity, then implement source-to-code-to-theme analysis, then validate controlled procedural adaptation.

The biomedical feedback design is a strong architectural starting point, especially its separation of evidence, codebooks, themes, rules, and feedback. Its principal missing connection to WarrantRoute is an executable contract specifying who can change each object, how changes invalidate previous approvals, and what independent evidence permits a procedural rule to become reusable.

## 2. Scope and Sources of Truth

The audit traced the live execution path, its schemas, prompts, routing policy, controller, same-model experiment configuration, Table 3 projection, tests, Playbook files, and relevant historical run metadata. It also inspected the local ACE adaptation loop and consulted primary methodological and systems research. This is not a claim that every historical branch or every repository file was audited.

Start with these files:

- [Playbook structure](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/playbooks/PLAYBOOK_STRUCTURE.md>).
- [Biomedical feedback design](/Users/tom/Documents/GitHub/ACL2027/ace_paper/BIOMEDICAL_PLAYBOOK_FEEDBACK_DESIGN.md).
- [Live runtime](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py>).
- [Deterministic loop controller](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/direction_h_human_in_loop/scripts/ace_tight_loop_controller.py>).
- [n=100 runner](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py>).
- [Static-Playbook configuration](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/config/warrantroute_loop_n100_same_model_playbook_v1.json>).
- [Same-model Table 3 evaluator](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_same_model_table3.py>).

There are multiple generations of WarrantRoute in this repository. The opening note in [the working record](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/warrentroute.md:3>) correctly directs readers to the live loop, but much of its body explains historical cached-role replay. That replay must not be described as the present live revision mechanism. Likewise, the opening of [the Playbook adaptation protocol](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/protocol/warrantroute_playbook_adaptation_v1.md:12>) still describes an empty Playbook field. Static injection has since been implemented, although online updating has not.

### Recorded Execution Status

| **Artifact** | **Observed Status** | **What It Establishes** |
| --- | --- | --- |
| `n100_same_model_table3_20260905_v2` | 1,200 result files, no-Playbook variant | A historical controlled-packet execution completed |
| `playbook_smoke_dreaddit_qwen_n1_20260906T184913Z` | One result, six calls, two revisions, human escalation, no recorded technical error | Static Playbook injection ran for one Dreaddit/Qwen trajectory |
| `n100_same_model_static_playbook_ready_20260906T185213Z` | Frozen inventory for 1,200 trajectories, zero result files at inspection | A full Playbook run was prepared, not completed |

These observations do not establish the absence of other runs elsewhere. They identify the concrete runs referenced by the inspected implementation and documentation.

## 3. What the Current System Actually Does

### 3.1 Roles, Models, and Modes

| **Role** | **Current Executable Responsibility** |
| --- | --- |
| P: Proposer | Generalist assessment of an already supplied claim, with an optional alternative interpretation |
| E: Evidence Scout | Assessment of support, counterevidence, context and evidence-related issues |
| M: Methods Challenger | Optional methodological audit of the supplied claim |
| D: Domain Challenger | Optional domain and biomedical-scope audit using supplied context |
| R: Reviser | A replacement claim plus an explicit response to every assigned issue |

There are **five logical roles, not five independently trained models**. Rechecking reuses E and selected issue owners. The router, schema validators and controller are deterministic software, not additional LLM agents.

| **Condition** | **LLM Used by Every Role and Recheck** |
| --- | --- |
| `qwen_only` | `qwen3:8b` |
| `llama_only` | `llama3.1:8b` |
| `gemma_only` | `gemma3:4b` |

The implementation enforces this same-model policy. Calling the agents separately provides operational isolation, not independent model knowledge or independent statistical evidence.

The four live modes select optional expertise on top of mandatory P and E:

| **Mode** | **Initial Calls** |
| --- | --- |
| G: generalist | P + E |
| M: qualitative methods | P + E + M |
| D: domain | P + E + D |
| B: both | P + E + M + D |

R is invoked only when revision is requested and the controller can reserve its rechecks. Current limits are two revision rounds and twelve agent calls per packet. The live `always_on` comparator is not the historical Table 3 union of three cached reviewer outputs: it uses this live workflow with both specialists enabled.

### 3.2 Actual Flow

```text
Locked input claim + supplied excerpts
  -> P assessment and E assessment, initially isolated
  -> deterministic G/M/D/B routing
  -> selected specialist assessments, which see P/E reports
  -> collect located issues
  -> R rewrites the claim within the supplied evidence
  -> E + current issue owners recheck
  -> accept / revise again / human escalation / quarantine

Frozen Playbook -> role/dataset-specific prompt additions
Historical answer key -> scoring after execution, not agent input
```

The live route can expand in response to initial expertise requests. It does **not** continuously re-estimate the four actions after each revision. A request for an inactive specialist after revision causes escalation. The separate historical segment-switching implementation is not automatically part of this path.

### 3.3 The Router Is a Heuristic, Not a Learned Gain Predictor

The active scorer uses weighted source-structure and Proposer-rating features:

```text
S_G = g
S_M = m - c_M
S_D = d - c_D
S_B = min(m, d) + interaction - c_M - c_D - c_B
route = argmax S
```

The values are need/sufficiency heuristics with fixed penalties. They are not calibrated probabilities, measured expected discoveries, actual dollar costs, or a fitted causal estimate of the benefit of specialist review. E's explicit expertise requests can promote a route, but its complete evidence assessment is not part of the weighted initial scorer. See [route scoring](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/build_working_warrantgate_routes.py:189>) and [live route selection](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:390>).

### 3.4 What Is Already Well Engineered

- Same-model conditions, model digests, prompts, seeds and budgets are explicit.
- Original-claim detection is frozen separately from later revision findings.
- Evidence identifiers and issue ownership are validated.
- Reviser self-reports do not by themselves resolve issues.
- Calls are journaled before dispatch. Incomplete or failed cached calls do not silently trigger unlimited retries.
- The controller reserves revision and recheck calls before spending the remaining budget.
- Working outputs are explicitly not manuscript-eligible, and acceptance is not claimed to be independently measured repair quality.

These are valuable foundations. They should be retained during development.

## 4. Prioritized Findings

Severity here means development priority. A demonstrated software boundary failure is distinguished from an unmeasured semantic-quality concern.

### F1. High: Approvals and Resolutions Can Become Stale

At [runtime rechecking](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:669>), only E and owners of currently blocking issues review the revision. Other active specialists retain reports on earlier candidates. Acceptance checks dispositions but not the candidate version those dispositions assessed. Once resolved, an issue is not automatically reconsidered after another edit.

Two offline probes reproduce the boundary:

- A run accepts candidate r1 while M and D have reviewed only r0.
- A two-round run restores the original claim text in r2 while a D-owned issue remains resolved from r1 and D never reviews r2.

These are synthetic controller demonstrations, not estimates of real-world error rates. They do not assert that every stale approval is substantively wrong. They establish that the runtime cannot guarantee that its approvals apply to the final artifact.

**Required change:** bind each approval to target ID, target version/hash, criterion, evidence versions, and inspected dependencies. Invalidate affected approvals after a patch. Initially recheck all relevant active auditors after free-text replacement. Later, dependency-scoped patches can justify cheaper selective rechecks. Never infer that an unconstrained rewrite changed only the issue named in its explanation.

### F2. High: A Frozen No-Playbook Condition Can Receive an Unbound Playbook

[Execution](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py:289>) enables the Playbook client path when `playbook_bundle.json` exists. [Run validation](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py:225>) verifies declared assets but does not reject this additional behavior-changing file in a no-Playbook run.

An isolated temporary-run probe prepared a no-Playbook condition, added a valid bundle without changing its manifest, passed `load_run`, and observed the bundle being passed to the client. The client and model transport were mocked. No real run was altered.

**Required change:** enforce equality between config enablement, manifest enablement, expected asset presence, and the frozen bundle hash before constructing a client. Reject undeclared behavior-changing assets. Bind the Playbook schema and retrieval policy as well. This is an experiment-reproducibility defect, not evidence that existing results were tampered with.

### F3. High: Current Results Do Not Demonstrate a Successful Repair Loop

The metadata audit validated the saved result checksum for all 1,200 historical no-Playbook results:

| **Condition** | **Trajectories** | **Accepted** | **Human Escalation** | **Resolved Issue Records** |
| --- | ---: | ---: | ---: | ---: |
| Qwen only | 400 | 0 | 400 | 0 |
| Llama only | 400 | 0 | 400 | 0 |
| Gemma only | 400 | 0 | 400 | 1,417 |

All Qwen and Llama trajectories reached two revisions. Gemma reached two revisions in 391 trajectories. Its remaining trajectories stopped earlier. These are historical controlled-packet diagnostics, not publishable model-performance estimates. They also do not prove that every generated revision was worse or useless.

The important distinction is that **execution completion, flaw detection, issue resolution, independent repair quality and thematic quality are different outcomes**. The current loop can finish all scheduled jobs without accepting any final claim.

Issues are appended with stage-based IDs. There is no semantic continuation, duplicate, or supersedes relation between similar objections. Repeated owner/category/evidence keys are common in the historical records, but this coarse overlap is not proof of identical criticism. Determine through a blinded source review whether failures reflect unresolved substantive problems, repeated objections, resolution-format behavior, over-criticism, or actual repair regressions before changing thresholds.

**Required change:** add structured per-issue verdicts for the latest candidate, a distinction between recurring and new issues, and independent before/after repair assessment. Do not improve the acceptance percentage by weakening approval criteria. Do not interpret zero technical errors as successful semantic repair.

### F4. High for the Proposed Goal: No Persistent Coding or Theme-Development State

[Input preparation](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:235>) forwards a research question, excerpts, and a pre-existing claim. [Revision output](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:91>) is one claim with its concept, scope, evidence and uncertainty.

There is no executable cross-document codebook, coding-decision store, theme graph, case-by-code matrix, analytic memo store, or dependency-aware recoding queue in this live path. An incoming top-level analytic contract or codebook is dropped by the allowlist. The Methods Challenger prompt asks about codebook consistency and a declared method without an explicit versioned object supplying either.

**Required change:** add a dedicated thematic-analysis task contract. Preserve the old claim-review task as a separate mode of operation so its evaluation target does not silently change.

### F5. Medium: Playbook Retrieval Is Role/Dataset Selection, Not State-Aware Retrieval

[Retrieval](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:198>) accepts `payload` but does not use it. Active bullets are ranked by role section, dataset failure priorities and a generic-scope bonus, with at most six supplied per call. Contrasting initial and recheck payloads returned identical lists in all twenty role/dataset combinations tested.

This does not mean a model cannot conditionally apply the supplied rules: the prompt explicitly asks it to do so. It means the software does not retrieve different checks in response to the current claim, a changed modality, a new issue, or a revision stage. Adapter caution text is not itself injected by this retrieval function.

The biomedical rule is restricted to Dreaddit, GoEmotions and CaChe. Its checks may still appear in the shared prompt, but the explicit rule cannot be retrieved for a health-related parliamentary excerpt or a newly registered biomedical corpus under the current dataset gate.

**Required change:** retrieve using analytic contract, operation, source type, observed topic/scope features, unresolved criteria and artifact dependencies. Include mandatory safety rules and linked exceptions before optional ranked rules. Keep this deterministic and logged initially. Embeddings can later propose candidates, not decide analytic equivalence.

### F6. Medium: Playbook Approval and Privacy Metadata Are Weaker Than Their Names Suggest

The ten bullets are active with `approved_by = ["protocol_static_pilot"]`, broad provenance `current_n100_failure_diagnosis`, and zero helpful/harmful counters. This is a static pilot marker, not recorded human approval or independently established rule utility.

[Source-leak screening](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:106>) checks a handful of identifier patterns in five fields. It does not cover all string fields or detect arbitrary participant prose. A schema-valid rule with source-like identifiers in `exceptions` passed validation in the offline probe. This establishes a coverage gap, not an actual disclosed participant record. Optional per-bullet hashes are not mandatory, although the prepared bundle itself is hashed.

**Required change:** distinguish protocol-authorized static rules from empirically validated or human-approved rules. Require structured reviewer identity, scope, provenance and versioned approval. Use a source-free procedural-rule schema and a controlled review/export boundary. Text screening is defense in depth, not a de-identification guarantee. Keep restricted evidence references in a private ledger, outside reusable prompt memory.

### F7. Medium: Some Hard Checks Are Proxies or Constants

At [hard-check construction](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:612>), quotation fidelity means no unresolved quote-related issue, not exact source-span verification. Source-count reconciliation is set to true. Runtime cluster count is the number of source IDs, not necessarily the number of independent participant or study families. Frozen hashes are set to true here, although the main runner separately verifies its declared assets.

**Required change:** separate `structural_check_passed`, `semantic_assessment`, and `not_evaluated`. Verify source spans and count invariants in code. Preserve study-family and participant dependencies. Do not present absence of an LLM warning as deterministic proof of fidelity.

### F8. Medium: Revision Rule Citations Are Lost from the Final Candidate

At [candidate replacement](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py:662>), the Reviser output is copied and then `playbook_bullet_ids` is overwritten with an empty list. The offline Playbook probe reproduced this. Revision history and aggregate used IDs remain available, so the provenance is not completely lost.

**Required change:** retain candidate-level rule references, and separately record supplied versus cited versus verified-applied rules. A cited ID is a model report, not proof that the rule was applicable or helpful.

### F9. High for Evaluation: The Scoring Target Does Not Match Thematic Improvement

[Detection scoring](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py:365>) tests whether an intended flaw appears among original-candidate flags. It leaves repair quality unset. [The secondary Table 3 projection](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_warrantroute_same_model_table3.py:133>) selects initial rating reports, not the revised claim, coding decisions, or final themes. Its Qwen judgment is not independent expert ground truth.

The projection is narrower than the complete initial review: it retains flags, rationale, disposition and abstention fields, but not the full evidence-linked issues, requested changes, alternative interpretation or Playbook application trace. Improving those omitted work products need not improve the current secondary score. A new evaluation should judge the actual work product claimed by the method. See [review projection](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_table3_review_quality.py:197>).

The current static-Playbook configuration also changes the seed, prompt version and input-character ceiling relative to the historical no-Playbook configuration. A comparison against the old run would not isolate the effect of Playbook bullets. The default runner and Table 3 supervisor still select the no-Playbook configuration unless explicitly changed through the appropriate entry point.

**Required change:** pre-register a fresh matched comparison and separate detection, repair, theme quality and cost. For controlled flaw detection, include independently adjudicated defensible/no-material-flaw cases before claiming precision or specificity. The intended planted flaw is not necessarily an exhaustive list of all defensible criticisms.

## 5. How the Biomedical Design Should Be Adapted

### Rule Content to Revisit Before Expansion

The existing bullets appropriately discourage unsupported criticism, erased negative cases and excessive clinical inference. Several conditions should nevertheless be tightened under a declared analytic contract:

- `pb-dataset-0007` currently permits an exception when the packet frames its claim as a broad cross-group theme. The breadth of the candidate's own wording is not evidence authorizing that breadth. Require an explicit analytic scope and relevant cross-group evidence, or preserve the group-specific limitation.
- `pb-domain-0005` permits an exception when the packet states the biomedical relation. Separate faithful reporting of a source's assertion from endorsing that assertion as a biomedical fact. Explicit source wording can justify the former without justifying the latter.
- `pb-evidence-0002` exempts a single narrow source case. That should limit cross-case claims, not remove the need to inspect contradictions or changes within one person's account.
- `pb-revision-0009` favors minimal repair. Retain that for claim review, but do not make minimal text change the objective for theme development: splitting a concept or revising a code definition may be the appropriate substantive operation.
- `pb-theme-0004` should apply criteria supplied by the analytic contract, not demand a particular abstraction level from every corpus. A descriptive code, a topic domain and a meaning-based theme require different outputs.

These are proposed content corrections, not measured explanations of the historical results. Evaluate boundary cases before activating revised bullets. Add positive obligations to preserve useful explanatory meaning so that repeated scope reduction does not produce a safe but analytically empty output.

### 5.1 Choose the Analytic Method Explicitly

The router should choose the *expertise needed for the current analytic operation*. It should not silently change the epistemological method from paragraph to paragraph.

For the first implementation, use a **Framework Method or explicitly specified codebook-TA workflow for participant material**, with a case-by-code matrix and qualitative researcher oversight. This fits versioned coding and within/between-case comparisons. It is not a license to replace interpretation with counting. [Gale et al., 2013](https://pure-oai.bham.ac.uk/ws/portalfiles/portal/16708327/Gale_Using_framework_method_BMC_Medical_Research_Methodology_2013.pdf).

For published qualitative findings, use a **separate thematic-synthesis branch** with line-level coding, descriptive synthesis and explicitly warranted analytic interpretation. Do not pool study-author interpretations with raw participant speech as interchangeable observations. [Thomas and Harden, 2008](https://link.springer.com/article/10.1186/1471-2288-8-45).

Do not call a reliability-optimized consensus codebook system reflexive TA. Braun and Clarke distinguish coding-reliability, codebook and reflexive approaches, and warn against mixing their quality criteria without justification. Agreement is not universal evidence of interpretive quality. A central organizing concept is particularly important for meaning-based themes, whereas a declared descriptive framework may legitimately use topic domains. [Understanding TA](https://www.thematicanalysis.net/understanding-ta/), [reviewer guidance](https://www.thematicanalysis.net/editor-checklist/).

Represent this choice in a frozen `AnalysisContract` with research question, method, semantic/latent orientation, analysis unit, inductive/deductive/hybrid approach, source-voice policy, population boundaries, permitted theme kinds, permissible operations, and human responsibilities. Do not infer diagnoses or protected participant traits to configure routing.

### 5.2 Separate Six Persistent Objects

The biomedical design's E/C/T/P separation should be retained. Add explicit coding decisions and versioned feedback/action records, rather than putting everything into one Playbook.

| **Object** | **Required Content** | **Must Not Be Mistaken For** |
| --- | --- | --- |
| Evidence registry | Source version, exact span, case/study-family ID, speaker/voice, context, provenance, access boundary | A generated interpretation or a clinical fact inferred by the model |
| Codebook | Code ID/version, definition, inclusion/exclusion criteria, relationships and scope | Reusable global procedural instructions |
| Coding decisions | Evidence-to-code links, code version, rationale, alternate coding, status and evaluator | A bare label or an unversioned count |
| Themes and analytic memos | Theme kind, concept, member codes, support, negative cases, boundary and rationale | An embedding cluster or a list of popular topics |
| Method Playbook | Source-free scoped procedures, applicability, exceptions, conflicts, version and approval | An answer sheet, patient memory, or biomedical knowledge database |
| Feedback/action ledger | Evaluator identity, target/version, criterion, verdict, proposed patch, decision and replay provenance | A running conversation summary or a helpfulness counter |

For a small local implementation, ordinary versioned JSON records plus append-only JSONL events are sufficient and fit the repository. Introduce SQLite only when transactions or indexed cross-record queries become a real need. A graph database and learned vector router are not prerequisites.

### 5.3 Give Every Theme an Inspectable Warrant

A theme record should let a researcher answer:

1. What does this theme assert, and how does it address the research question?
2. Which analytic codes and exact source passages support it?
3. Which cases contradict, qualify or fail to support it?
4. What interpretation connects the evidence to the claim?
5. Where does it apply, and what is outside its scope?
6. How is it distinct from sibling themes or merely descriptive categories?
7. Which artifact versions and decisions produced it?

Use explicit relations such as `supports`, `qualifies`, `contradicts`, `alternative_interpretation`, and `not_comparable`. Permit a source span to receive multiple justified codes. Permit a relevant minority code to remain outside a larger theme. Do not force every code into a neat hierarchy or remove a consequential case because it is infrequent.

Coverage should distinguish `not inspected`, `inspected but not relevant`, `relevant but uncoded`, and `coded`. A blank matrix cell must not silently mean that a phenomenon is absent.

### 5.4 Biomedical Specificity Must Be Typed, Not Just a Stronger Prompt

Attach source-grounded facets where applicable: experiencer, assertion voice, time, negation, modality, population, intervention and outcome. Allow unknown values. Record whose assertion is being represented and whether it is anticipated, experienced, reported by another person, or inferred by an analyst.

A participant's causal attribution can be an important analytic finding without establishing biomedical causality. Preserve that attribution as their perspective. A published author interpretation can be synthesized as such without being silently reclassified as a patient quotation or independently verified clinical fact.

Keep original source text immutable. Normalization and source correction produce linked new versions. Related publications, quotations repeated across reports, and multiple excerpts from one participant need family-level deduplication and sensitivity analysis. Excerpt counts are not population prevalence.

External biomedical reference retrieval would be a separate, explicitly authorized and versioned capability. It is not currently implemented in the supplied-context-only Domain Challenger. Such reference material must remain distinguishable from the qualitative evidence being analyzed.

## 6. Keep Five Roles but Change Their Work Products

| **Role** | **Proposed Thematic-Analysis Work Product** | **Authority** |
| --- | --- | --- |
| P: Proposer | Candidate coding decisions, code definitions, theme structures and alternative interpretations | Propose, never self-approve |
| E: Evidence Scout | Verified span links, voice/context checks, support/countercase map and missing-evidence requests | Validate evidence references, raise scoped issues |
| M: Methods Challenger | Checks on code boundaries, method fit, abstraction, theme distinctiveness and negative cases | Challenge analytic decisions, not dictate one universal interpretation |
| D: Domain Challenger | Source-grounded checks of biomedical modality, time, population, attribution and scope | Flag overreach and missing context, not invent clinical truth |
| R: Reviser | Typed patches to codes, coding decisions or themes with explicit issue responses | Propose changes for validation and application |

In the new thematic task, P actually generates analytic candidates rather than assessing a pre-existing claim. E audits those candidates against the underlying source. This changes the current initial-call protocol and must be versioned and compared as a new task, not silently substituted into the old Table 3 run.

Additional calls for evidence retrieval, countercase review or procedural-rule proposals remain visible and charged. Reusing a logical role does not make a call free. The existing twelve-call limit is a per-packet limit, not a plausible total budget for analyzing an entire corpus. Specify both a bounded local review budget and a corpus-wide budget.

### Proposed Inner Loop

```text
Authorized source inventory + frozen AnalysisContract
  -> immutable source/span registry and case/family links
  -> P proposes codes or themes for a bounded analysis unit
  -> E checks source links and counterevidence
  -> router selects G, M, D or B for the current state
  -> selected challengers return criterion-specific feedback
  -> R proposes typed patches when repair is justified
  -> deterministic validation + evidence checks
  -> apply a new artifact version
  -> invalidate affected approvals/codings/themes
  -> targeted recheck or recoding
  -> accept scoped artifact / retain alternatives / request human review
  -> update the case-by-code matrix and theme evidence view
```

The system should be able to return a useful partially reviewed analysis with explicit unresolved decisions, not just an uninformative terminal escalation label.

## 7. Make Feedback Specific Enough to Improve the System

### 7.1 Three Feedback Targets

- **Evidence error:** wrong span, voice, source version or attribution. Repair the evidence link or derived representation, not the immutable source text.
- **Analytic decision:** inappropriate code, excessive abstraction, erased dissent, weak theme boundary or a defensible competing interpretation. Repair or register alternatives in the analytic workspace.
- **Procedural rule:** a repeatedly misleading or incomplete method instruction. Propose a Playbook patch for separate development review.

An analytic mistake does not automatically imply that a procedural rule is wrong. A correct output citing a rule does not automatically imply that the rule caused success.

### 7.2 Replace Sparse Resolution Lists with Per-Issue Verdicts

For every assigned issue require a structured verdict:

```text
issue_id
target_id + target_version + target_hash
criterion_id + criterion_version
verdict: resolved | persists | not_applicable | insufficient_context | contested
supporting_evidence_refs
brief_decision_rationale
evaluator_id + evaluator_type
related_issue_ids
```

This makes an omitted resolution distinguishable from an explicit judgment that the issue persists. Keep new issues in a separate list. Reject contradictory outputs such as the same issue being both resolved and repeated without a recurrence relation. Preserve uncertainty rather than coercing binary agreement.

Error categories should distinguish a factual/provenance violation, a material analytic weakness, an alternative defensible interpretation, and a methodological choice. The current practice of converting every reported issue into a material blocker is too blunt for interpretive analysis.

### 7.3 Give Patches Transactional Semantics

Useful operations include `LINK_EVIDENCE`, `ADD_CODE`, `REVISE_CODE`, `SPLIT_CODE`, `MERGE_CODES`, `ASSIGN_CODE`, `REVISE_THEME`, `REGISTER_DISAGREEMENT`, and separate `ADD_RULE`, `REVISE_RULE`, `RETIRE_RULE` operations.

Every patch must contain an operation ID, expected base version/hash, target type, changed fields, evidence/feedback references, proposed effects and actor identity. The executor validates the operation, checks permissions and dependencies, and creates new versions. It rejects stale-base updates and applies duplicate operation IDs idempotently.

Code merges and splits must retain lineage and trigger recoding of affected evidence. Changed definitions invalidate dependent decisions even if the code ID is unchanged. A theme must not retain an apparently valid warrant through an obsolete code definition. Reverting a bad patch should restore a prior state through an auditable event, not erase the history.

### 7.4 The Second Loop Is Procedural Adaptation, Not Another Debate Round

```text
Development feedback ledger
  -> identify a recurring, scoped procedural failure
  -> propose a source-free rule delta
  -> inspect conflicts, exceptions and source restrictions
  -> paired replay on development cases and boundary cases
  -> human/protocol approval with explicit scope
  -> activate a versioned rule in a new Playbook snapshot
  -> freeze before held-out evaluation
```

The same five-role pool can supply reflection and patch-proposal tasks. The deterministic executor supplies merge/application mechanics. Human methodological approval is not a sixth LLM. Initially perform procedural reflection offline after a batch, not inside every local revision loop.

An updated *project codebook* is not necessarily an updated *global method policy*. Thematic analysis can evolve project-specific artifacts under a frozen method. For a fixed-codebook transfer evaluation, freeze the codebook too and represent unmatched evidence explicitly. For corpus-level inductive analysis, permit within-corpus adaptation but evaluate on separate held-out corpora if making a generalization claim.

## 8. A More Defensible Mathematical Router

Keep the four actions. Make their utility refer to the next analytic operation on the current state, rather than calling a heuristic need score an expected gain.

```text
s_t = observed artifact state, unresolved criteria, evidence structure,
      analysis phase, approval freshness, and remaining budget

a_t = argmax over feasible a in {G, M, D, B}
      [ estimated_delta_quality(s_t, a)
        - lambda * estimated_incremental_cost(s_t, a)
        - rho * estimated_material_harm(s_t, a) ]
```

This is a proposed decision rule, not a fitted model, a stability proof or a guarantee of outperforming All roles.

Define quality as a pre-specified vector, with dimensions such as grounding, meaningful coverage, conceptual coherence, boundary preservation and research-question fit. A scalar projection may support routing, but report the components separately. Enforce provenance and critical-safety requirements as constraints rather than allowing enough aesthetic quality to compensate for fabricated evidence.

The feasible set must reserve downstream revision and verification costs. A cheaper initial choice that predictably causes many repair calls is not necessarily cheaper overall. Human review time, retrieval, rule adaptation, failed calls and recoding belong in end-to-end cost accounting.

**Initial implementation:** use an explicit rule-based policy with documented uncertainty and dependency requirements. Acquire paired outcomes for the four modes on development units using the same backbone, task, source inventory and budgets. Only then fit a small regularized gain estimator. If only the chosen action has an outcome, the benefits of unchosen actions cannot simply be inferred from that log. Controlled development exploration or paired offline execution is needed.

A role change should respond to newly observed criteria or changed artifact dependencies. Safe example classes are a new abstraction problem requiring M or a newly introduced biomedical scope assertion requiring D. Do not switch the scientific method or guess that clinical vocabulary alone establishes the need for a different epistemology.

For stopping, compare estimated remaining benefit with its uncertainty and full marginal cost on development data. Keep hard budget limits and mandatory checks. A lack of new suggestions is operational convergence, not evidence of thematic saturation. Choosing an arbitrary fixed threshold and naming it optimal would not improve the current model.

### Rule-Level Credit

For a candidate rule delta, compare the same development units under the prior and patched Playbook. Orient each quality measure so larger is better, and compute differences within independent participant/study-family clusters and stochastic repetitions before aggregation:

```text
delta_Q_k = average_over_clusters_and_repetitions(
                Q_k(with_patch) - Q_k(without_patch))
```

Include unchanged valid cases, targeted failures and boundary/exception cases. A rule that fixes one distinction while erasing a legitimate alternative must not receive unqualified positive credit. Evaluate important rule interactions when jointly retrieved. Repeated calls on one passage are not independent supporting cases. Candidate selection on this replay makes it development evidence, not final-test evidence.

## 9. What to Borrow from Research, and What Not to Claim

**ACE:** use structured procedural memory, localized deltas, and separate reflection from deterministic application. The reference implementation's no-ground-truth option can still receive correctness information derived from a target, so label-free biomedical feedback needs a separately defined source. The current WarrantRoute static Playbook is only an initial step toward adaptation. ACE's benchmark gains and noise tolerance do not establish biomedical thematic validity. [ACE v3](https://arxiv.org/html/2510.04618v3), [local target-derived feedback](/Users/tom/Documents/GitHub/ACL2027/ace_paper/upstream/ace/ace.py:477).

**Self-Refine:** a single LLM can take generator, feedback and refinement roles without weight training. This supports the same-backbone experimental design, but does not turn its feedback into independent validation. [Madaan et al., 2023](https://arxiv.org/abs/2303.17651).

**Existing clinical TA work:** Yi et al. already combine iterative codebooks, quote/code/theme identifiers, edit operations and an action ledger. Those features alone are not a defensible novelty claim. Their preprint's described evaluation also motivates caution about repeatedly inspecting a test set to select the best iteration, chunk-level splitting, frequency-based pruning and embedding similarity as thematic quality. These are design concerns inferred from the described protocol, not independently reproduced failures of their system. [Yi et al., 2026, v1](https://arxiv.org/html/2603.08989v1).

WarrantRoute's more promising contribution is a testable combination: **cost-aware reviewer routing over versioned analytic artifacts, with feedback that distinguishes evidence from interpretation and procedural policy, and with dependency-aware approval and recoding.** The contribution must be demonstrated against matched baselines. It is not established merely by drawing a more complicated agent diagram.

## 10. Evaluation That Can Show Actual Progress

### 10.1 Keep Three Evaluation Layers Separate

| **Layer** | **Target** | **Useful Measures** |
| --- | --- | --- |
| Claim review | Located, justified criticism of the original claim | Intended-flaw recall plus adjudicated precision, false alarms and abstention |
| Repair | Original versus revised artifact on the same evidence | Material errors fixed, new errors introduced, meaning retained, boundary preservation, independent preference with ties |
| Thematic analysis | Corpus-level codes, decisions, themes and synthesis | Grounding, meaningful coverage, within/between-case fit, coherent and distinct themes, negative-case preservation, useful uncertainty and human revision effort |

Evaluate the final artifact even when the loop escalates, while reporting that it was not internally approved. Never let dropping escalated cases inflate quality. Keep technical failures and unresolved judgments in denominators and report them explicitly.

An independent expert panel should examine blinded artifacts against source context under the declared analytic contract. It can identify clear violations, assess interpretive defensibility and retain disagreements. It need not manufacture one uniquely correct thematic answer sheet. An external frozen LLM judge may be a secondary instrument, with human validation and judge-family sensitivity analysis. It must not feed held-out grading back into the loop.

### 10.2 Build a Matched Comparison

Hold the backbone, source units, preprocessing, prompt scaffolding, output schema, seeds, evidence access, generation budgets and grader fixed. Deliberately vary one factor for a Playbook ablation. Keep an empty rule field and the same schema in the no-Playbook arm where appropriate, so a format change is not mistaken for a content effect.

Compare an explicit single-pass coding baseline, a structured iterative coding baseline, the live loop without a Playbook, a static-Playbook loop, a development-adapted frozen Playbook, and an always-on specialist version of the same thematic pipeline. Stage these comparisons instead of launching every combination immediately. Keep the three same-model conditions. Do not mix an earlier three-review union with a new generation-and-repair pipeline and interpret the difference as routing alone.

Report quality-cost curves, not only a best percentage. Include calls, input/output tokens, elapsed time, failed/retried calls, human minutes, adaptation cost and cost amortization assumptions. On local models, wall time and token usage are measured resources, not automatically a dollar price.

### 10.3 The Existing Four Banks Are Not Four Independent Biomedical Benchmarks

Use the current controlled-claim banks for software diagnosis only under the repository's policy. Dreaddit and GoEmotions supply social-media language, CaChe is participant/group material, and ParlaMint-GB supplies political speech. Relevance to a biomedical analytic question must be justified, not inferred from availability.

In the inspected historical comparison, the source-component counts were Dreaddit 100, GoEmotions 100, CaChe 1 and ParlaMint-GB 85. These are overlap components for those packet inventories, not counts of independent studies or universal properties of the full corpora. In particular, 100 CaChe packets did not produce 100 independent components. Do not claim a powered between-source analysis from that denominator.

For thematic development, obtain an authorized coherent participant corpus and, separately, an authorized collection of qualitative study findings addressing a defined question. Split by participant/family/study before chunking. Maintain untouched evaluation sources outside Playbook development, router fitting and stopping-rule selection. Existing exposed packets cannot become untouched test data again by renaming a file or changing a seed.

### 10.4 Essential Ablations

1. Freshness-aware rechecks versus the current owner-only reuse policy.
2. Typed analytic state versus single-claim revision.
3. State-aware retrieval versus the current role/dataset lists.
4. Validated procedural patches versus static instructions, with development cost included.
5. Routed specialists versus always-on specialists under the same generation/revision task.
6. Typed source voice and family tracking versus untyped excerpt pooling.

Predefine acceptable harm, meaningful improvement and uncertainty handling before evaluating the held-out corpus. Sample-size planning must use independent cases or study families and observed development variability, not just the number of chunks or packet rows.

## 11. Implementation Roadmap

All entries below are proposed, not completed. Preserve frozen historical code snapshots and results. New implementation versions require new run manifests.

| **Phase** | **Scoped Work** | **Acceptance Gate** |
| --- | --- | --- |
| 0: Repair the foundation | Version-bound approvals, resolution freshness, explicit per-issue verdicts, manifest/config Playbook binding, retained citations | Reproduced boundary failures become regression tests that fail on old behavior and pass on the patch |
| 1: Establish analytic state | AnalysisContract, source/span registry, codebook, coding decisions, theme/memo records, case-by-code matrix | Every analytic link resolves to a source/version; malformed or stale links fail; alternatives and uncovered evidence remain visible |
| 2: Add bounded analytic operations | P code/theme generation, R typed edits, dependency invalidation, recoding queue, task-specific E/M/D outputs | Changes preserve lineage and trigger all required rechecks; no clinical facts are invented to complete fields |
| 3: Improve context selection | Deterministic state-aware rule retrieval, mandatory rules/exceptions, per-call manifest and token accounting | Required checks cannot disappear through ranking; irrelevant rules can be omitted; replay reproduces supplied context |
| 4: Adapt procedures offline | Typed feedback, candidate rule patches, conflict review, paired development replay, approval lifecycle | Model-only assertions never silently become validated global rules; held-out data cannot update memory |
| 5: Calibrate routing and evaluate | Development action outcomes, optional gain estimator, matched baselines, independent quality/cost assessment | A pre-specified quality-cost advantage survives source-level uncertainty and does not rely on relaxed safety or dropped failures |

Implement Phase 0 in the existing runtime/controller/runner ownership boundaries. For Phase 1, add a small thematic-state schema and validator near the existing schemas and scripts. Add a separate thematic-analysis entry point rather than expanding the n=100 claim-review runner until its purpose becomes ambiguous. The actual new filenames should be selected during implementation, not mistaken for files already present.

### Minimum Regression Coverage

- Editing an already approved field invalidates the relevant specialist approval.
- Reintroducing a resolved problem cannot inherit approval from an earlier version.
- A no-Playbook manifest rejects an unexpected Playbook asset before any call.
- Rule references survive revision and distinguish supplied from cited rules.
- Every operation validates its target type, base version, evidence references and idempotency key.
- Code definition changes invalidate dependent coding decisions and themes.
- Source voice, negation, temporal scope and study-family links survive merges and splits.
- Duplicate objections are represented as recurrence or independent disagreement, not silently merged or inflated.
- Missing context and defensible alternatives do not become fabricated hard errors.
- Held-out feedback cannot activate a rule, tune a router, or select the final iteration.
- All five logical roles and all rechecks use the condition's single pinned model.
- Budget checks include required verification, newly activated expertise and failed calls.

## 12. Recommended Next Decision

**Build a trustworthy versioned thematic workspace before adding online learning or a more elaborate router.**

First establish whether the loop can correctly distinguish resolved, persistent and newly introduced problems on a small independently reviewed development set. Then let it manipulate codes and themes through explicit patches. Once those work products can be assessed, learn when extra methodological or domain review is worth its cost. That order supplies the feedback a meaningful router and Playbook updater need.

Do not target higher recall alone, force consensus, optimize the acceptance rate, automatically merge embedding-near codes, or expand the number of agents without specifying what new evidence or operation they contribute.

The intended result is a research-support system that develops traceable interpretations and exposes unresolved decisions to a researcher. It should not claim to discover the single correct interpretation, independently establish biomedical truth, or prove that no further themes exist.

## 13. Verification and Reproduction

Executed during this audit:

- `test_warrantroute_loop_n100.py`: 21 tests passed.
- `test_warrantroute_same_model_table3.py`: 10 tests passed.
- Static Playbook validator: passed, ten active bullets and four adapters.
- Eight offline probe groups: completed without model calls or reading real corpus records.
- Historical metadata inspection: 1,200 saved result checksums verified, with no live-service compatibility claim.

The empty-Playbook enum probe was valid under the installed JSON Schema validator. It is **not** reported as a schema defect. No dedicated Playbook test references were found in the existing experiment `test*.py` files. Passing the 31 existing tests therefore does not demonstrate the untested Playbook boundaries.

Artifacts:

- [Offline probe code](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/contract_probes.py>).
- [Offline probe results](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/probe_results.json>).
- [Historical metadata inspector](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/inspect_recorded_run.py>).
- [Historical aggregate observations](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/recorded_run_observations.json>).
- [Principal source fingerprints and validator version](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/source_fingerprints.json>).

Run the probes without contacting a model:

```sh
/opt/anaconda3/bin/python3 -B "/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/contract_probes.py"
```

Inspect the historical run without printing source text:

```sh
/opt/anaconda3/bin/python3 -B "/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/warrantroute_development_audit_20260907/inspect_recorded_run.py" "/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2"
```

These scripts test current implementation behavior or inspect saved metadata. They do not train a model, generate a new scientific result, certify privacy clearance, or authorize a manuscript export.
