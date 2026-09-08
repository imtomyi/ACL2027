# ACE-TightLoop for Biomedical Thematic Analysis: Design v1

Implementation update (2026-09-05): the inner loop now has a live private
packet-review profile in
[`run_warrantroute_loop_n100.py`](../../rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py).
See the [experiment guide](../../rq2_role_prompted_llm/WARRANTROUTE_LOOP_EXPERIMENT_GUIDE.md)
for the implemented behavior, model assignments, commands and remaining gaps.
This profile reviews an existing claim before revision, schedules independent
initial passes serially, uses WarrantGate v0 with expertise escalation, and
keeps Playbook updates disabled. The outer memory loop below remains a design.

Status of this document: architecture and controller contract. The linked
experiment guide records the executable profile. This design note itself does
not authorize data use or establish empirical performance.

This is the implementation-direction successor to
`ace_biomedical_thematic_analysis_v0.md`. It keeps the v0 governance and
information-separation rules, but replaces ACE's privileged Generator with a
sparse network of compact semantic agents.

## 1. Design decision

Use a **sparse, evidence-constrained micro-agent loop** rather than a large
Generator followed by format-oriented reflection and curation.

The objective is not equal call counts for every agent. The objective is to
remove semantic monopoly: no single agent may both propose an interpretation,
judge its evidential support, decide that objections are resolved, and write the
lesson into the Playbook.

The loop has two levels:

1. an inner case loop that proposes, challenges, revises, and either accepts or
   escalates one evidence-linked analytic candidate; and
2. an outer memory loop that converts independently validated development
   outcomes into human-approved Playbook deltas.

## 2. Why the original balance needs correction

ACE conceptually assigns three roles, but the operational responsibilities are
asymmetric:

- the Generator sees the task, source context, current Playbook, and prior
  reflection, then produces the answer that is scored;
- the Reflector diagnoses the answer after generation and tags the bullets the
  Generator says it used;
- the current public Curator implementation primarily proposes `ADD`
  operations, with deterministic code applying the formatted result.

The Reflector and Curator remain useful, but this arrangement lets most task
interpretation originate from one model call. Using the same model for all
three roles also isolates the context-engineering effect in the ACE paper, but
does not create model-family diversity. For qualitative analysis, correlated
interpretive errors can then survive multiple nominal roles.

## 3. Principles

1. **LLMs perform semantic work only.** JSON validation, identifier checks,
   quote matching, counters, hashing, and state transitions belong to code.
2. **Independent first passes.** The proposer and evidence scout do not see one
   another's output before their initial records are locked.
3. **Sparse communication.** Agents receive only the state fields and evidence
   needed for their task, never an accumulated chat transcript.
4. **Conditional activation.** Methods and domain challengers run only when the
   frozen WarrantRoute action requires them or a hard rule escalates to them.
5. **Objection ownership.** An open material objection blocks acceptance. A
   revision must answer every issue by identifier, and the issue owner verifies
   the response.
6. **Model-family separation.** The reviser must not use the same model family
   as the original proposer. At least one active auditor must also differ from
   the proposer family.
7. **Finite monotone execution.** The loop permits at most two revision rounds.
   It terminates in `accepted`, `human_escalation`, or `quarantined`.
8. **No autonomous memory commit.** A Playbook semantic delta requires
   provenance, independent challenge, and named human approval.

These choices follow evidence that fully connected multi-agent interaction can
be wasteful, that unnecessary debate can overturn correct answers, and that
sparse response selection and early stopping can preserve much of the benefit
at lower cost.

## 4. Compact agent set

### Paper terminology

Use English throughout the paper, including figures, tables, prompts, and
supporting design documents. Use the following operation labels consistently:

| Operation | Meaning |
| --- | --- |
| Evidence Extraction | Identify relevant source passages and record supporting evidence, counterevidence, and context gaps. |
| Alternative Interpretation | Develop a plausible competing interpretation of the same evidence. |
| Methodological Challenge | Test an interpretation against the declared analytic method, including negative cases and theme boundaries. |
| Biomedical Scope Check | Check whether biomedical, causal, clinical, or subgroup claims exceed the evidence and study context. |
| Revision | Update the candidate interpretation in response to identified issues. |

These are operation labels. The agent names and route definitions below retain
their existing meaning. Methodological Challenge denotes critical testing and
does not presume that an interpretation has been falsified.

### Inner case loop

| Agent | Always active? | Semantic responsibility | Forbidden responsibility |
| --- | --- | --- | --- |
| `P` Proposer | Yes | Candidate code/theme, central concept, scope, evidence IDs, uncertainty | Judging its own support or accepting itself |
| `E` Evidence Scout | Yes | Independent support, counterevidence, context gaps, source concentration | Seeing `P` before its first pass or naming the final theme |
| `M` Methods Challenger | Route `M` or `B` | Method-contract violations, code/theme confusion, boundary and negative-case tests | Biomedical factual adjudication |
| `D` Domain Challenger | Route `D` or `B` | Biomedical overreach, causal/clinical inference, subgroup and temporal-context checks | Declaring methodological quality alone |
| `R` Reviser | Only after a material issue | Minimal candidate revision that resolves issue IDs | Deleting unresolved objections or committing memory |

`E` is not a fifth WarrantRoute mode. Evidence integrity is a mandatory base
layer. The four review modes remain exactly:

```text
G = P + E
M = P + E + M
D = P + E + D
B = P + E + M + D
```

### Outer memory loop

| Agent | Semantic responsibility |
| --- | --- |
| `RF` Failure Reflector | Abstract a reusable lesson from a validated success, failure, or repair outcome |
| `RC` Counterexample Reflector | Search for overgeneralization, contradictory episodes, scope limits, and participant-finding leakage |
| `MS` Memory Steward | Propose `ADD`, `REVISE`, `DEPRECATE`, `SPLIT`, or `CONTRADICTION_HOLD` using both reflections |
| Human approver | Approve, edit, reject, or hold the semantic delta before deterministic commit |

This makes reflection and curation substantive. They must determine whether a
lesson generalizes, where it applies, and whether it contradicts current rules,
not merely reformat one Generator's explanation.

## 5. Tight inner loop

```text
START
  -> P and E run independently in parallel
  -> deterministic integrity checks
  -> frozen WarrantRoute selects G, M, D, or B
  -> selected challengers run in parallel
  -> issue register is locked
  -> ACCEPT when hard checks pass and no material issue is open
  -> otherwise R makes the smallest issue-linked revision
  -> only E and the original issue owners recheck affected fields
  -> ACCEPT, one final revision round, or HUMAN_ESCALATION
```

There is no free-form group conversation. An agent may emit one record per
round. Agents communicate through a typed state containing candidate fields,
evidence IDs, issue IDs, resolutions, budgets, and decision reasons.

### Development output budgets

These are starting values for qualification, not frozen experimental values:

| Output | Maximum tokens |
| --- | ---: |
| Proposer candidate | 700 |
| Evidence map | 350 |
| Each challenger report | 350 |
| Revision | 700 |
| Each memory reflection | 300 |
| Playbook delta proposal | 350 |

Prompt boilerplate should be cached where the runtime permits. A recheck sees
only the revised fields, original issue record, and necessary excerpts.

## 6. Acceptance and stopping

Hard checks are deterministic where possible:

- schema validity;
- allowed and existing evidence identifiers;
- exact quotation fidelity when quotation is permitted;
- source/cluster count reconciliation;
- prohibited field and protected-attribute screening;
- no held-out or answer-key field in the agent state;
- model, prompt, Playbook, and schema hash match.

An LLM's confidence cannot independently stop the loop. The controller uses
hard checks, open issue severity, remaining budget, and a development-fitted
expected marginal value:

```text
score(a | s_t) = expected_quality_gain(a | s_t)
                 - lambda * incremental_cost(a)
                 - mu * expected_overturn_harm(a | s_t)

a_t = argmax over {STOP, ACTIVATE_M, ACTIVATE_D, ACTIVATE_B, REVISE, ESCALATE}
```

The estimator is fitted only from development outcomes with independent human
or deterministic references. It never uses same-agent approval as truth. Stop
when hard checks pass and no material issue is open, or when the best additional
action has score at or below the frozen threshold. Escalate instead of guessing
when a hard failure or material disagreement remains at the round or budget
limit.

For the first implementation, the checked-in deterministic controller uses
hard checks and issue status only. A learned expected-gain policy is a later,
separately frozen extension after sufficient development observations exist.

## 7. Context boundaries

- `P` receives the approved bounded source packet, research question, analytic
  contract, scoped Playbook bullets, and study-codebook definitions.
- `E` receives the same source packet and question, but not `P`'s first output.
- `M` receives the locked candidate, analytic contract, and the evidence map.
- `D` receives the locked candidate, approved biomedical context, and the
  evidence map.
- `R` receives the candidate, open issue records, and only the evidence needed
  to answer those issues.
- `RF`, `RC`, and `MS` receive a deidentified structured development outcome.
  Participant text and study findings may not enter the global Method Playbook.

No agent receives other agents' private reasoning. Retained outputs are concise
decision rationales and evidence links, not requested chain-of-thought.

## 8. Compact model allocation

The currently installed core candidate pool is:

```text
gemma3:4b
qwen3:8b
llama3.1:8b
```

`llama3.2:latest` and `deepseek-r1:1.5b` may be screened as lower-cost
candidates, but must not be assigned a semantic role merely because they are
smaller.

Do not bind one model to one role before qualification. That would confound
role quality with model quality. Use a crossed development screen:

```text
each candidate model x each eligible semantic role
  -> quality, material-error recall, harmful-objection rate
  -> tokens, latency, and failure rate
  -> select a role-specific Pareto candidate
  -> enforce proposer/reviser family separation
  -> freeze assignments before held-out use
```

The model-role assignments are experimental factors and must be logged. A
model swap creates a new configuration version.

## 9. Making non-generator contribution measurable

Report more than final quality. For each agent role, measure:

- unique material issues first identified by that role;
- precision of material objections after expert adjudication;
- proportion of accepted revisions attributable to its issue IDs;
- harmful-overturn rate, where an objection degrades an initially acceptable
  candidate;
- counterevidence and boundary violations recovered;
- leave-one-role-out quality and cost change;
- model-swap sensitivity for the same role contract.

These measurements answer whether the added agents perform real epistemic work.
Call count or prompt length is not evidence of importance.

## 10. Outer Playbook loop

The outer loop operates only after an admissible development reference is
locked:

```text
validated development outcome
  -> RF proposes the narrow reusable lesson
  -> RC independently tests scope, contradictions, and leakage
  -> MS proposes one versioned semantic operation
  -> deterministic schema/provenance/duplicate checks
  -> named human approval
  -> deterministic append or version transition
```

A single episode cannot directly promote a global rule. Promotion thresholds
must require evidence from distinct source clusters and be selected before
held-out access. Helpful/harmful counters are telemetry, not proof. When a
semantic merge is needed, preserve both parents, the proposed merged child, and
the approval record.

## 11. Experimental comparison

After governance authorization and a prospective freeze, compare:

1. best single compact model, one pass;
2. original ACE-like `Generator -> Reflector -> Curator` workflow;
3. same-model iterative self-revision with a matched call/token budget;
4. always-on compact agent loop;
5. routed ACE-TightLoop with conditional challengers and early stopping;
6. human-approved routed ACE-TightLoop for the biomedical primary analysis.

Quality comparisons must be both call-budget-matched and token-budget-matched.
Report the quality-cost Pareto frontier and a learning curve over accumulated
development clusters. Never compare the routed loop's selective cost against an
unmatched always-on baseline and call that a quality improvement.

## 12. Relationship to WarrantRoute and Table 3

ACE-TightLoop does not add a fifth Table 3 reviewer mode. WarrantRoute still
selects `G`, `M`, `D`, or `B`. The loop controls which micro-agents execute
inside that selected path and whether a revision is worth its cost.

This is a successor study design. It must not silently replace the active Table
3 WarrantRoute row or learn from Table 3 held-out outcomes. Its prompts,
model-role assignments, controller, Playbook, thresholds, and data partitions
need a separate prospective freeze.

## 13. Implementation artifacts

- `../schemas/ace_tight_loop_state_v1.schema.json` defines the source-text-free
  shared loop state.
- `../scripts/ace_tight_loop_controller.py` implements the initial deterministic
  route requirements and accept/revise/escalate decision.
- `../scripts/test_ace_tight_loop_controller.py` checks the four-mode graph,
  hard-failure handling, material-objection veto, round limit, and budget limit.

The controller intentionally contains no model transport and cannot start a
data run.

## 14. Literature basis

- Zhang et al., [Agentic Context Engineering](https://openreview.net/pdf?id=eC4ygDs02R).
- Wang et al., [Mixture-of-Agents Enhances Large Language Model
  Capabilities](https://arxiv.org/abs/2406.04692).
- Li et al., [Improving Multi-Agent Debate with Sparse Communication
  Topology](https://arxiv.org/abs/2406.11776).
- Li et al., [Sparse Mixture-of-Agents](https://arxiv.org/abs/2411.03284).
- Eo et al., [Debate Only When Necessary](https://arxiv.org/abs/2504.05047).
- Fan et al., [iMAD: Intelligent Multi-Agent
  Debate](https://arxiv.org/abs/2511.11306).

These works motivate heterogeneity, sparse communication, conditional
activation, and early stopping. They do not establish validity for biomedical
thematic analysis; that claim requires the project-specific human and
evidence-linked evaluation above.
