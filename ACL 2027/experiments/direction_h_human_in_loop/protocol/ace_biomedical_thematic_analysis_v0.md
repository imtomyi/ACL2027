# ACE for Biomedical Thematic Analysis: Design v0

Status: background design retained. The implementation direction is superseded
by `ace_biomedical_tight_loop_v1.md`. No real-text access or experiment is
authorized by either document. Direction H governance and corpus-specific
freezes remain controlling.

## 1. Decision

Use the architecture of Agentic Context Engineering (ACE), but do not copy its
benchmark objective or current repository implementation unchanged.

For this project, ACE should evolve a versioned **method playbook** during the
development phase. It must not treat an LLM's themes as ground truth, learn from
held-out confirmation data, or place participant findings in a reusable global
memory.

The current Direction H contract is codebook-oriented thematic analysis. This
design therefore targets assisted codebook thematic analysis, not a claim that
an automated system performs Braun and Clarke-style reflexive thematic analysis
independently.

## 2. What ACE contributes

ACE treats context as an evolving, itemized Playbook rather than repeatedly
rewriting one large prompt. Its three roles are:

1. **Generator:** applies the current Playbook to a new task and records which
   Playbook bullets were used.
2. **Reflector:** examines the trajectory and reliable outcome feedback,
   diagnoses errors, extracts a reusable lesson, and tags used bullets as
   helpful, harmful, or neutral.
3. **Curator:** proposes small delta updates that are merged into the existing
   Playbook instead of replacing it wholesale.

Each Playbook bullet has a stable identifier, content, and helpful/harmful
counters. ACE's grow-and-refine step adds new bullets and periodically detects
semantic duplication. This structure is intended to reduce two failure modes:
brevity bias, in which useful detail is compressed into generic advice, and
context collapse, in which a full rewrite suddenly drops accumulated knowledge.

ACE supports offline adaptation on development data and online adaptation while
processing a stream. Only offline adaptation is admissible for the confirmatory
biomedical study. The final Playbook must be frozen before held-out data are
opened.

## 3. Why direct transplantation is invalid

The ACE paper mainly evaluates tasks with exact labels or execution outcomes.
Its medical result uses DDXPlus diagnostic classification, not qualitative
biomedical thematic analysis. The paper also reports that adaptation can
degrade when neither labels nor reliable execution signals are available.

Thematic analysis has no unique answer sheet. A theme is an interpretation that
must be coherent with the declared analytic approach, research question, source
material, and researcher positionality. Agreement with an LLM, frequency of a
theme, or an LLM's confidence is not a valid correctness signal by itself.

The official ACE implementation also needs hardening before biomedical use:

- the current Curator path applies `ADD` operations, while update, merge, and
  delete operations remain incomplete;
- optional semantic de-duplication can ask an LLM to merge bullets, which can
  alter meaning;
- helpful/harmful counts are model-generated judgments, not independent
  evidence;
- paper prompts request detailed reasoning traces, whereas this project should
  retain concise audit rationales and not request hidden chain-of-thought;
- the paper's public experiments did not involve human subjects or sensitive
  data, so its ethics statement does not cover this use case.

## 4. Required information separation

Four stores must remain separate.

| Store | Purpose | May contain participant text? | May transfer across studies? |
| --- | --- | --- | --- |
| Method Playbook | Reusable analytic and review rules | No | Only after human review |
| Study codebook | Current study codes, definitions, inclusions, exclusions | Restricted excerpts by opaque ID | No |
| Evidence ledger | Claim-to-excerpt links, source coverage, counterevidence | Yes, restricted | No |
| Reflexive audit log | Analyst decisions, disagreements, positionality, approvals | Avoid direct text where possible | No |

This separation prevents a study finding such as a participant subgroup's
experience from being converted into a general methodological rule.

## 5. Biomedical ACE roles

### Generator

For each approved development packet, the Generator produces:

- candidate codes or theme revisions that answer the frozen research question;
- a concise analytic claim and central organizing concept;
- exact evidence references using opaque excerpt IDs;
- source and participant-cluster coverage;
- negative or deviant cases;
- scope boundaries and uncertainty;
- IDs of the Playbook bullets actually used.

It may not infer diagnosis, treatment, risk, demographic identity, or causality
beyond the source text and approved domain context.

### Reflector

The Reflector audits the candidate against reliable signals in this order:

1. deterministic integrity checks, including quotation fidelity, valid excerpt
   IDs, source counts, and prohibited-field checks;
2. locked individual expert ratings and contract-relative adjudication;
3. source-localized evidence, counterevidence, and boundary violations;
4. success or failure of a blinded repair without collateral error;
5. secondary rubric ratings such as coherence, relevance, boundary clarity,
   data support, definition, naming, and analytical contribution.

It emits a concise error diagnosis, a proposed reusable lesson, affected bullet
IDs, and evidence provenance. It must preserve expert disagreement and the
`plural_ambiguous` state rather than forcing a single truth label.

### Curator

The Curator proposes, but does not autonomously commit, one of:

- `ADD`: a genuinely new rule;
- `REVISE`: a bounded correction with the old version retained;
- `DEPRECATE`: a harmful or obsolete rule;
- `SPLIT`: a rule that conflates distinct contexts;
- `CONTRADICTION_HOLD`: unresolved evidence requiring human adjudication.

Every semantic change requires named human approval. Mechanical counter updates
and deterministic validation may run automatically. No LLM-based merge may
silently replace the source bullets.

## 6. Playbook bullet contract

Each bullet should contain at least:

```json
{
  "bullet_id": "evidence-00017",
  "section": "evidence_warrant",
  "scope": "codebook_ta:interview_or_focus_group",
  "trigger": "a theme is supported primarily by one source cluster",
  "rule": "report concentration and test the claim against other clusters",
  "required_evidence": ["source_count", "cluster_count", "counterexample_check"],
  "exceptions": [],
  "provenance": ["development_item_id", "expert_observation_id"],
  "helpful_count": 0,
  "harmful_count": 0,
  "status": "candidate",
  "version": 1,
  "approved_by": [],
  "content_hash": "sha256:..."
}
```

Recommended sections are analytic contract, coding, theme construction,
evidence warrant, negative cases, biomedical/domain safety, reflexivity,
reporting, and common failure modes.

## 7. Adaptation loop

```text
approved development clusters only
  -> retrieve scoped Playbook bullets
  -> Generator creates evidence-linked candidate
  -> deterministic checks run
  -> independent human/expert observation is locked
  -> Reflector produces a source-localized audit
  -> Curator proposes a delta
  -> human approves, revises, rejects, or holds the delta
  -> versioned Playbook commit
  -> repeat on the next development cluster
  -> select thresholds on validation clusters
  -> freeze Playbook, prompts, models, schemas, and code
  -> evaluate once on held-out clusters with updates disabled
```

Participant, speaker, focus-group, clinic, or document clusters must not cross
development, validation, and held-out partitions. Held-out outcomes may be used
for final analysis only, never for Playbook updates or threshold selection.

## 8. Relationship to WarrantRoute and WarrantLoop

These components act at different levels:

```text
ACE outer loop
  learns approved review rules from development episodes
    -> WarrantRoute inner decision
       selects Generalist, Methods, Domain, or Both for the current packet
         -> WarrantLoop optional acquisition
            decides whether another review is worth its cost
```

WarrantRoute selects expertise for a current packet or section. ACE changes the
context that those reviewers receive across development episodes. WarrantLoop
may acquire another reviewer inside one item. ACE must not update either policy
during a held-out Table 3 or biomedical confirmation run.

## 9. Evaluation design

The minimum comparison is:

1. base model with the frozen ordinary prompt;
2. static human-authored Playbook;
3. ACE Playbook with automatic LLM updates only, diagnostic and not eligible
   for confirmatory claims;
4. human-approved ACE Playbook, the proposed method.

Use cluster-held-out evaluation and report:

- deterministic quotation and evidence-link integrity;
- unsupported-claim and boundary-violation rates;
- negative-case preservation and source-concentration disclosure;
- blind expert ratings of coherence, relevance, boundary clarity, data support,
  definition, naming, and analytical contribution;
- disposition, serious-error detection, abstention, and successful repair
  without collateral error;
- retained expert disagreement, not only consensus;
- token cost, latency, expert minutes, Playbook size, and performance versus
  accumulated development examples.

Inter-rater reliability may be reported for a declared coding-reliability or
codebook contract, but it is not a universal quality measure for reflexive
thematic analysis. COREQ and SRQR are reporting guides, not answer keys or
automatic quality scores.

## 10. Promotion and stop rules

A candidate bullet may become active only when it is novel, source-localized,
supported by an admissible feedback signal, applicable beyond one source
cluster, and explicitly human-approved. Exact numeric promotion thresholds must
be selected in a pilot and frozen before held-out access.

Stop adaptation and quarantine the affected run when any of the following
occurs:

- participant text or a study finding enters the global Method Playbook;
- a held-out item influences a prompt, threshold, route, or Playbook update;
- an excerpt cannot be reproduced exactly from its authorized source;
- the Curator changes meaning without a versioned human approval;
- protected attributes are inferred or exposed outside the approved contract;
- model-generated agreement is used as the sole correctness signal;
- a governance, provider, retention, or access-control gate is missing.

## 11. Recommended first pilot

1. First obtain explicit authorization for a qualification set. Direction H
   currently authorizes neither fictional/synthetic data nor real-text
   processing. After approval, use a non-sensitive set with known evidence-link
   defects to test schemas and mechanics only.
2. On approved development clusters, compare the static and human-approved ACE
   Playbooks. Use no held-out AGYW confirmation text for adaptation.
3. Estimate a learning curve at increasing numbers of development clusters and
   identify the point where marginal quality gain no longer justifies LLM and
   expert cost.
4. Freeze the complete system before the in-domain audit and cross-domain
   confirmation.

## 12. Sources

- Zhang et al., [Agentic Context Engineering: Evolving Contexts for
  Self-Improving Language Models](https://openreview.net/pdf?id=eC4ygDs02R),
  ICLR 2026.
- [Official ACE implementation](https://github.com/ace-agent/ace).
- Braun and Clarke, [One size fits all? What counts as quality practice in
  (reflexive) thematic analysis?](https://doi.org/10.1080/14780887.2020.1769238).
- Braun and Clarke, [Doing reflexive thematic
  analysis](https://www.thematicanalysis.net/doing-reflexive-ta/).
- O'Brien et al., [Standards for Reporting Qualitative Research
  (SRQR)](https://doi.org/10.1097/ACM.0000000000000388).
- Tong et al., [COREQ](https://www.equator-network.org/reporting-guidelines/coreq/).
- Martinez Montes et al., [Large Language Models in Thematic Analysis: Prompt
  Engineering, Evaluation, and Guidelines](https://arxiv.org/abs/2510.18456),
  preprint.
- Sharma et al., [DeTAILS: Deep Thematic Analysis with Iterative LLM
  Support](https://arxiv.org/abs/2510.17575), preprint.
