# Biomedical thematic analysis with an evolving playbook

Technical background and proposed research design. Prepared 2026-09-07.

This document addresses both published studies and participant data. It describes an extension to ACE, not an implemented or empirically validated biomedical system. Equations, schemas, and acceptance policies below are proposed engineering specifications unless explicitly attributed to a source.

## 1. What a playbook contributes

A playbook is persistent, editable knowledge supplied as model context. Its useful unit is an operational rule: under a specified condition, perform an action, check a criterion, and preserve relevant exceptions. For thematic analysis, an example is: when assigning a motivation to a participant's action, cite the stated reason and retain uncertainty if no reason is provided.

ACE uses generation, reflection, and curation to update such context through localized entries. The paper describes identified bullets with helpful/harmful metadata and a grow-and-refine process. Its motivation is preserving useful detail that can disappear during repeated whole-context rewriting. The model weights remain fixed. The paper also reports that unreliable feedback can degrade adaptation. These are architectural and empirical claims, not a guarantee that every new rule improves performance. [ACE, sections 2-3 and 4.4](https://arxiv.org/html/2510.04618v3).

The relevant precursor is verbal feedback and persistent memory: Reflexion uses task feedback to produce reflections that influence later attempts without changing model weights. [Reflexion](https://arxiv.org/abs/2303.11366).

For this project, distinguish four objects:

| Object | Meaning | Example |
| --- | --- | --- |
| Evidence | What a source actually contains | A transcript span and its speaker |
| Codebook | Definitions used to characterize evidence | Definition and exclusions for treatment concern |
| Theme structure | Interpretive relationships across coded evidence | How uncertainty shapes everyday treatment decisions |
| Playbook | Procedures for conducting and checking analysis | Check whether a concern is experienced, anticipated, or attributed by someone else |

A codebook describes the analytic categories; a playbook guides how to apply, question, and revise them. Both can evolve, but their updates require different justifications. Improving a procedure does not itself establish the truth of a biomedical claim.

## 2. Theoretical formulation

Let x_t be a task, P_t the current playbook, and theta the fixed parameters of the Generator. A useful formalization is:

```text
tau_t, y_t = G_theta(x_t, render(P_t), available_evidence)
F_t       = Evaluate(x_t, tau_t, y_t, criteria, observations)
R_t       = Reflect(x_t, tau_t, y_t, F_t, P_t)
Delta_t   = Curate(P_t, R_t)
P_(t+1)   = Apply(P_t, Delta_t)
```

Here, tau_t is an observable execution record: inputs, retrieved evidence, tool results, decisions, and short justifications. It need not expose or depend on a model's private chain of thought. F_t is feedback evidence; R_t is an interpretation of that feedback; Delta_t is a proposed state change. These are different data objects.

The feedback loop modifies the conditional behavior of G by changing its inputs. Calling this adaptation is appropriate; calling it gradient descent or a calibrated reinforcement-learning update would require an additional algorithm. There is no derivative through the prose and no general monotonic-improvement theorem supplied by this representation.

One property can be specified exactly. For an ordinary patch that touches IDs J, all unrelated entries should remain unchanged:

```text
for every i outside J: P_(t+1)[i] == P_t[i]
```

This is an implementation invariant that prevents accidental loss of unrelated rules during a patch. It does not ensure that the new content is true, useful, or nonredundant. Semantic merging is a separate operation and must be validated separately.

Treating the system as a feedback controller is a useful engineering analogy: outputs are observed, deviations are diagnosed, and the operating instructions are adjusted. It is not evidence of control-theoretic stability. Repeated self-judgment can amplify an initial error if the observations never introduce corrective evidence.

## 3. What the released ACE code actually does

The following observations were checked against the local source and Git revisions, rather than inferred from the paper diagram.

| Component | Verified behavior | Consequence for replication |
| --- | --- | --- |
| General ACE Reflector | Receives question, generated output, feedback, used bullets, and optionally a reference answer; returns a diagnosis and bullet tags | Item attribution and task correctness are separate signals |
| General counter function | Increments helpful or harmful by one for the corresponding tag; neutral changes neither | The counters count judgments; they are not probabilities |
| General adaptation loop | Evaluates the initial answer, reflects on both success and failure, retries failures within a configured bound, and periodically curates | Learning from successful strategies is part of the implementation |
| AppWorld Reflector | Receives the task conversation and playbook; the no-GT template omits explicit reference code and test-report fields | Available observations depend on prompt and execution configuration |
| AppWorld Curator | Produces JSON additions; code validates types/sections and assigns IDs | The Curator does not write the entire stored playbook |
| AppWorld counter function | Writes plain ID/content entries and does not increment helpful/harmful | Missing counters are more than a display choice in this revision |
| AppWorld analyzer | Optional embedding similarity grouping followed by an LLM merge | Deterministic patch application does not mean all refinement is deterministic |

The general repository revision is `82709de050e1db6e6ef2f07bcb0393560b94992a`; the AppWorld revision is `928e86877d34cd10eaba159606386f93a1765090`. The files supporting these observations were unmodified relative to their respective Git revisions. These statements apply to those revisions, not every version of ACE.

Source pointers:

- [General feedback and retry loop](/Users/tom/Documents/GitHub/ACL2027/ace_paper/upstream/ace/ace.py:463).
- [General Reflector schema](/Users/tom/Documents/GitHub/ACL2027/ace_paper/upstream/ace/prompts/reflector.py:5).
- [General counter updates](/Users/tom/Documents/GitHub/ACL2027/ace_paper/upstream/playbook_utils.py:50).
- [AppWorld parsing, counters, and ADD operations](/Users/tom/Documents/GitHub/ACL2027/ace_paper/paper_reproduction/sources/ace-appworld-latest/experiments/code/ace/playbook.py:62).
- [AppWorld reflection and curation](/Users/tom/Documents/GitHub/ACL2027/ace_paper/paper_reproduction/sources/ace-appworld-latest/experiments/code/ace/adaptation_react.py:235).
- [Optional semantic merge](/Users/tom/Documents/GitHub/ACL2027/ace_paper/paper_reproduction/sources/ace-appworld-latest/experiments/code/ace/bulletpoint_analyzer.py:110).

There is a further feedback distinction worth retaining. In the checked general adaptation loop, `no_ground_truth=True` hides the reference answer from the Reflector, but the loop still compares the prediction with `target` and passes match/mismatch feedback. Thus, reference-answer-free is not necessarily label-free. A biomedical replication should explicitly record whether feedback contains reference content, correctness judgments derived from references, source observations, expert decisions, or model-only critique.

The general counter updater creates one tag per ID per invocation. Repeated tags for an ID within a passed batch overwrite earlier ones in its lookup. Therefore, a counter is not automatically the number of independent successful cases. That distinction matters when interpreting or replacing it.

## 4. Choose a coherent qualitative method

For published qualitative findings, Thomas and Harden describe thematic synthesis through text coding, descriptive themes, and analytical themes, while retaining links to source findings. This offers a methodological basis for the literature branch. Quantitative study results need a separately specified extraction and synthesis protocol; a theme mentioning treatment benefit cannot establish treatment effectiveness. [Thomas and Harden, 2008](https://link.springer.com/article/10.1186/1471-2288-8-45).

For participant data, the Framework Method supports systematic organization and comparison within and between cases, with an experienced qualitative researcher directing the interpretation. This is compatible with the proposed use of explicit code definitions and case-by-code matrices. [Gale et al., 2013](https://pure-oai.bham.ac.uk/ws/portalfiles/portal/16708327/Gale_Using_framework_method_BMC_Medical_Research_Methodology_2013.pdf).

This is a recommended methodological fit, not an automatic equivalence. Braun and Clarke distinguish reflexive thematic analysis from approaches organized around shared codebooks or coding agreement. If the project adopts reflexive thematic analysis, feedback should support reflexive engagement and alternative interpretations; agreement scores should not be treated as its definition of quality. [Braun and Clarke's methodological FAQ](https://www.thematicanalysis.net/faqs/).

Before evaluation, specify the research question, unit of analysis, inductive/deductive orientation, semantic/latent interpretation, and role of researchers. Under an inductive design, literature-derived concepts can be recorded as sensitizing ideas, but novel participant evidence must remain able to challenge them.

## 5. Proposed advanced architecture

Represent the system state as S_t = (E_t, C_t, T_t, P_t, A_t): evidence, codebook, themes, playbook, and an action ledger. Source versions are preserved; interpretations can be revised by creating new versions.

```text
Published studies ---> typed source evidence ---+
                                               |
Participant data ----> typed source evidence ---+--> Analyst --> candidate codes/themes
                                                        ^                 |
                                                        |                 v
                                          active playbook          feedback evaluators
                                                        ^                 |
                                                        |                 v
                                                 accepted patch <-- Curator <-- diagnosis
                                                        ^
                                                        |
                                          source checks + replay + review
```

These are responsibilities, not a requirement to deploy a separate LLM for each box. Deterministic checks should be code; interpretive checks can use an LLM and researcher review. Separate model roles do not create independent evidence if they all repeat the same unsupported assumption.

### 5.1 Evidence and provenance

Every evidence unit should carry a document/transcript ID, version or content hash, exact span offsets, source type, speaker or authorial voice, study family, and relevant context. Preserve the source text and the surrounding passage separately from normalized text.

For literature, distinguish participant quotations, study authors' interpretations, reported quantitative results, and your synthesis. For interviews, distinguish participant statements, interviewer prompts, and researcher annotations. A reported diagnosis and a participant's fear about that diagnosis are different kinds of statement.

Keep literature and participant evidence in separate analytic branches until an explicit integration stage. At integration, compare patterns using source-type and population strata. A quote repeated in a review, primary paper, and accessible transcript should not become three independent confirmations. Record known relationships and flag uncertain duplication.

Proposed lineage:

```text
source version -> evidence span -> coding decision -> theme version
                                      |
                                      v
                               feedback event -> rule proposal -> rule version
```

Version derivation edges should be acyclic. Relations such as disagreement or alternative interpretation can be separate typed links. Every high-level theme needs a traversable evidence path, but such a path proves traceability, not interpretive validity.

### 5.2 Three targets for feedback

| Target | Example question | Typical consequence |
| --- | --- | --- |
| Evidence | Is the quotation present, correctly attributed, and in context? | Repair extraction or attribution |
| Coding/theme decision | Does this interpretation fit the evidence and chosen methodology? | Recode, revise, split, qualify, or retain alternatives |
| Playbook rule | Did a reusable instruction cause or prevent this error under these conditions? | Propose a scoped procedural update and test it |

Do not promote every output correction into a global rule. A mistaken page number needs a record repair; a repeated failure to retain speaker identity may justify an extraction procedure. Conversely, a valid unusual account may warrant a new code or a disconfirming case rather than an instruction that forces agreement with the majority.

### 5.3 A structured feedback event

The following is a proposed schema, illustrated with invented data:

```json
{
  "feedback_id": "fb-021",
  "run_id": "run-demo-04",
  "target_type": "coding_decision",
  "target_id": "decision-077",
  "criterion": "preserve_experienced_vs_anticipated",
  "finding": "The code asserts an experienced adverse effect, but the speaker describes fear of one.",
  "evidence_ids": ["interview-07:span-18"],
  "feedback_source": {"type": "researcher_review", "review_id": "review-12"},
  "status": "confirmed",
  "severity": "major",
  "suspected_rule_ids": ["coding-014:v1"],
  "scope": {"source_type": "participant_statement", "task": "experience_coding"},
  "suggested_action": "Recode as anticipated concern; examine whether coding-014 omits modality."
}
```

An LLM-only event would have a model origin and a provisional status. The `suspected_rule_ids` field is a hypothesis about attribution, not proof. If several reviewers disagree, preserve their individual events and an explicit adjudication or unresolved state; do not silently overwrite one with another.

Feedback needs an applicable criterion. For example, exact span matching is machine-checkable; determining whether an analytical theme adequately explains a pattern is interpretive. A source-faithfulness check should ask whether a claim is defensible from its cited material, whereas a clinical fact check asks a different question. Neither substitutes for the other.

### 5.4 Feedback signals and evaluators

| Signal | How to obtain it | What it cannot establish alone |
| --- | --- | --- |
| Quote integrity | Resolve offsets against the stored source version | The quote supports the interpretation |
| Attribution integrity | Verify speaker, source type, and study-family references | The speaker's statement is a clinical fact |
| Evidence support | Researcher adjudication; LLM critique as triage | A universally correct theme |
| Biomedical distinctions | Check subject, time, negation, modality, population, and stated outcome | Clinical causation from a narrative |
| Analytic quality | Review coherence, boundaries, explanatory value, exceptions, and research-question fit | Quality reducible to a single universal score |
| Coverage | Compare with independently reviewed evidence or an annotated subset | Recall on unreviewed material |
| Update utility | Paired runs before/after a proposed patch on development cases | Improvement on all future populations |

Record both the outcome and its origin. A machine check, model suggestion, and researcher judgment should remain distinguishable even when they agree. Agreement among models is not a new observation of the source.

### 5.5 A richer playbook item

```json
{
  "id": "coding-014",
  "version": 2,
  "kind": "procedure",
  "trigger": "Assigning an experience-related code to a statement about treatment effects",
  "action": "Identify whether the statement reports an experienced effect, an anticipated concern, or another person's account before assigning a code.",
  "scope": {"tasks": ["qualitative_coding"], "source_types": ["participant_statement", "participant_quote"]},
  "exceptions": ["Allow multiple codes if the passage explicitly includes multiple modalities."],
  "provenance": {"feedback_ids": ["fb-021"], "evidence_ids": ["interview-07:span-18"]},
  "supersedes": "coding-014:v1",
  "status": "candidate",
  "validation": {"evaluation_id": null, "independent_source_families": 0}
}
```

A scientific proposition would require a different `kind`, source support, scope, and review. General procedures may transfer across projects; code definitions and study-specific findings usually need more restricted scope. One reviewed example can motivate a candidate, but does not establish broad applicability.

### 5.6 Curator operations and lifecycle

Use typed operations: ADD_RULE, REVISE_RULE, RETIRE_RULE, ADD_CODE, SPLIT_CODE, MERGE_CODES, REVISE_THEME, LINK_EVIDENCE, and REGISTER_DISAGREEMENT. These extend the inspected AppWorld Curator's ADD-only interface.

Each patch includes a target ID, expected prior version, changed fields, supporting feedback IDs, and an operation ID. The patch executor checks the schema, references, scope, and version before application. Apply the same operation ID at most once. A rejected or invalid patch leaves the active state unchanged and remains in the ledger.

Use the lifecycle `candidate -> reviewed -> active -> superseded/retired`. Interpretive changes can remain contested. A narrow verified correction may be accepted directly into its appropriate record, while a rule that changes behavior across many documents needs broader evaluation. The architecture should not require a researcher to approve every mechanical formatting repair.

Code or theme merges must retain provenance and boundary cases. Embedding similarity can suggest candidates for review; it cannot establish equivalence. In particular, experienced toxicity and fear of toxicity may be close in embedding space while being analytically distinct.

## 6. Two loops and explicit credit assignment

The inner loop improves the current analysis: draft, inspect feedback, revise a bounded number of times. The outer loop evaluates and stores reusable knowledge for later tasks. A successful revision of the current example is evidence for local repair; generalization requires separate cases.

For a candidate patch delta, use a development replay set V containing both cases it should affect and boundary cases it should leave alone:

```text
gain_k(delta) = mean over j in V of
               [Q_k(G(x_j, Apply(P, delta))) - Q_k(G(x_j, P))]
```

Q_k is a specified quality dimension, with higher values consistently oriented as better. Hold model version, inputs, tools, and evaluation rubric constant. Repeat stochastic runs when feasible; a seed is useful when supported, but should not be assumed to ensure deterministic hosted inference.

For attribution to an existing rule r, a comparable diagnostic is quality with P versus P without r. This is an intervention on the system configuration, not a causal claim about biomedical outcomes. Rules can interact, so an isolated ablation does not fully explain their value. Test dependent rule groups when necessary.

A proposed acceptance policy is:

```text
Accept(delta) = structural_checks_pass
                AND relevant_evidence_review_complete
                AND no_critical_regression_on_boundary_cases
                AND targeted_quality_improvement_supported
```

Declare what counts as improvement and a critical regression before using the development results. If an update is justified by a decisive source correction but too few independent cases exist for a utility estimate, keep its scope narrow and its validation status explicit. Missing evidence is not a negative score or permission to invent precision.

Helpful/harmful counters can remain cheap diagnostics, but replace their role as the primary quality signal with evidence-linked evaluation records. Repeated retries on the same passage should not count as independent support. Track feedback events, independent study/participant clusters, and evaluator identity separately.

For research evaluation, estimate uncertainty by resampling independent units such as study families or participant groups, not arbitrary chunks from the same record. The correct clustering depends on how the data were collected. Development replay sets are used for selection; the final evaluation corpus must remain unused for patch selection.

## 7. Worked biomedical example

All passages in this example are invented to illustrate analytic behavior.

Participant A: "I skipped the tablet because I was afraid it would make me sick. It hasn't made me sick before."

Participant B: "I stopped after it made me nauseated every morning."

Published study finding: "Some participants delayed treatment because of concerns about potential adverse effects."

An initial analysis places all three under experienced side effects. A source-faithfulness review shows that A explicitly denies a prior experienced effect, B reports one, and the study authors summarize concerns. This is a specific error about modality and attribution, not simply a globally poor analysis.

The inner correction assigns A an anticipated-concern code, B an experienced-effect code, and the study finding an author-reported-concern interpretation. The literature finding retains its status as an authors' summary. An overarching theme may connect these experiences, but the distinctions remain visible beneath it.

The outer loop diagnoses a procedural omission: the original rule matched side-effect vocabulary without checking whether the event was experienced, anticipated, or attributed. The Curator proposes the `coding-014:v2` rule above and links it to the feedback.

Replay should include a mixed case: "It made me sick last time, and I worry it will happen again." A rule that now forces every mention into anticipated concern would introduce a new error. The candidate passes only if it preserves both codes when justified, as well as improving the targeted distinction on independent development examples.

At synthesis, ask how anticipated and experienced effects relate to treatment decisions across source types. Record where findings converge, differ, or cannot be compared. Do not convert the number of passages into population prevalence, and do not count a published quote twice if it overlaps with participant material.

## 8. Context selection and learning boundaries

Start with a small universal procedure set and project-scoped rules. Retrieve task-relevant rules together with their exceptions and unresolved conflicts. Keep a retrieval manifest listing the IDs and versions supplied to the model. A retrieved supportive rule should not hide a linked qualification or disconfirming case.

Avoid retrieving only examples that match the current theme: that creates a self-confirming loop. Include boundary examples and explicitly allow unmatched evidence to propose new codes. Changes to code definitions should flag previously coded material for targeted reconsideration so the final corpus does not silently mix incompatible versions.

For mixed evidence, a useful output is a matrix with themes as rows and source types, populations, and study/participant groups as columns. Its cells link to supporting and challenging evidence. This makes integration inspectable while retaining differences between published interpretation and direct participant accounts.

Stop a local loop when feedback is resolved, no supported improvement is available, or the specified iteration budget is reached. Model agreement, a stable code count, or no proposed edits does not by itself establish thematic saturation or exhaustive coverage.

## 9. Research contribution and evaluation

A testable central hypothesis is: evidence-linked, scope-aware feedback and update validation improve source-faithful thematic analysis and transfer across corpus types compared with ordinary ACE adaptation under matched resources.

Potential contributions are the explicit connection between analytic errors and reusable procedures, preservation of disagreements across source types, and measured acceptance of updates. These are proposed contributions; a focused related-work review is still required before claiming novelty or priority.

Iterative codebooks and provenance already appear together in a directly relevant clinical TA preprint. It describes identified quotes, codes, subthemes, themes, refinement operations, and an action ledger. The arXiv record labels it submitted to AMIA 2026, not confirmed accepted. This should be considered related work or a baseline, rather than presenting these features alone as novel. [Yi et al., 2026](https://arxiv.org/html/2603.08989v1).

Recommended comparisons are: static instructions; static evidence retrieval plus a codebook; the chosen ACE implementation; an existing iterative thematic-analysis pipeline when reproducible; and the proposed extension. Match Generator models and report both compute and human-review effort. Include a strong manually designed codebook baseline so gains cannot be attributed only to weak initial instructions.

For ablations, remove update replay, typed provenance, conflict preservation, or source-conditioned rule scope one at a time. Under a fixed budget, these tests show which mechanisms contribute. More agents and longer prompts are not independently evidence of better analysis.

| Evaluation target | Appropriate evidence |
| --- | --- |
| Source fidelity | Quote/attribution correctness and adjudicated unsupported-claim rate |
| Coding quality | Evidence-to-code fit; agreement or multi-label precision/recall only under a specified reference-coding protocol |
| Theme quality | Blinded researcher review of coherence, analytic depth, evidence fit, boundaries, and disconfirming accounts |
| Memory utility | Independent-task gains, regressions, and performance by rule scope |
| Cross-source transfer | Literature-to-participant and participant-to-literature transfer assessed separately |
| Robustness | Negation, mixed modality, speaker changes, rare accounts, duplication, source-order variation |
| Efficiency | Model calls, tokens, latency, and researcher minutes per accepted analysis/update |

Split by study family and participant/group identity before chunking; keep linked reports together. For a frozen evaluation, learn on development material, freeze the playbook, and evaluate unseen sources. For online evaluation, score each initial output before incorporating that example's feedback, and report that protocol separately. A final recoding of the same corpus can be analytically useful but is not an untouched generalization test.

Cross-source transfer should be conditional on comparable questions and contexts. A study-derived interpretive category that does not fit new participant accounts is a finding about limited transfer, not an error to suppress. Do not infer semantic quality merely from cosine similarity of theme labels.

An implementation can proceed in three increments: first source-linked evidence, codes, and themes with explicit feedback events; then versioned procedural patches and development replay; finally conflict-aware retrieval and cross-source transfer experiments. This isolates the contribution of each added mechanism.

## 10. What success would mean

The advanced system should explain which source supports a theme, how that source was interpreted, what feedback challenged the decision, which rule changed, and what independent evidence supports using that rule again. It should also preserve reasonable disagreement and decline unsupported generalization.

A defensible methods description is: "We extend agentic context adaptation with typed evidence provenance, feedback targeted at evidence, analytic decisions, and procedural rules, and validation of scoped updates through source review and development replay. The system supports biomedical thematic synthesis and participant-data analysis while retaining distinct source perspectives."

This document specifies the architecture and evaluation needed to test that claim. It does not establish superiority over ACE or validate the system for clinical decision-making.
