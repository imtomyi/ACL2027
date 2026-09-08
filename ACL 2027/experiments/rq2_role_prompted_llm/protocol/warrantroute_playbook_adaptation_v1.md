# WarrantRoute Playbook Adaptation Protocol v1

Date: 2026-09-07

Status: design and implementation target. This document does not authorize a
new held-out experiment. It defines what must be added before WarrantRoute can
claim an ACE-inspired Playbook component for biomedical research thematic
analysis and the current Table 3 working datasets.

## 1. Purpose

The current WarrantRoute n100 loop uses static prompts, a shared rater guide,
WarrantGate routing, revision, and recheck. It records `playbook_bullet_ids`,
but Playbook updates are disabled and the field remains empty. Therefore the
current Table 3 WarrantRoute rows measure a live routed review loop, not an
ACE-style context-adaptation system.

The Playbook-enabled version should add a frozen, versioned set of reusable
method rules that agents retrieve and cite during review. The Playbook should
improve review quality by reducing repeated failure modes such as unsupported
inference, contextual flattening, lost negative cases, over-specific causal
claims, hidden source concentration, and weak evidence grounding.

## 2. ACE Concept Adapted to This Project

ACE contributes the idea that context should be an itemized, evolving Playbook
rather than a repeatedly rewritten monolithic prompt. For this project, the
adaptation must be more conservative than ACE's original benchmark setting:

- qualitative thematic analysis has no single answer key;
- LLM agreement is not ground truth;
- participant or source findings must not become global method memory;
- held-out packets must never update prompts, routes, thresholds, or Playbook
  bullets;
- semantic Playbook changes require human approval.

The admissible adaptation is an offline, development-only Playbook:

```text
development packets + reliable feedback
  -> diagnose recurring review failures
  -> propose candidate Playbook bullets
  -> human approve, revise, reject, or hold
  -> freeze Playbook version
  -> run WarrantRoute once on evaluation packets with updates disabled
```

## 3. Information Stores

Keep four stores separate.

| Store | Purpose | May contain source text? | Transfers across datasets? |
| --- | --- | --- | --- |
| Method Playbook | Reusable review rules and failure checks | No | Yes, after human approval |
| Dataset Adapter | Dataset-specific cautions and domain boundaries | No direct text | Only within declared scope |
| Evidence Ledger | Claim-to-source links, counterevidence, source counts | Yes, restricted | No |
| Audit Log | Human approvals, disagreements, failed repairs, decisions | Avoid direct text | No, except abstracted lessons |

This prevents a source-specific finding from being turned into a general rule.

## 4. Playbook Bullet Schema

Each bullet should be a small rule with a stable identifier.

```json
{
  "bullet_id": "pb-evidence-0001",
  "section": "evidence_warrant",
  "scope": "thematic_review:all",
  "dataset_scope": ["dreaddit", "goemotions", "agyw_focus_groups", "parlamint_gb"],
  "trigger": "a claim explains a broad theme using evidence from only one source cluster",
  "rule": "flag source concentration and ask whether other source clusters support, limit, or contradict the theme",
  "required_checks": ["source_count", "cluster_count", "counterevidence_scan"],
  "failure_modes": ["hidden_source_concentration", "unsupported_abstraction"],
  "exceptions": ["single-source packet where the analytic contract explicitly permits single-case interpretation"],
  "agent_targets": ["proposer", "evidence_scout", "methods_challenger", "domain_challenger", "reviser"],
  "provenance": ["development_observation_id"],
  "status": "candidate",
  "version": 1,
  "approved_by": [],
  "helpful_count": 0,
  "harmful_count": 0,
  "content_hash": "sha256:..."
}
```

Required fields:

- `bullet_id`: stable and never reused.
- `section`: one of analytic_contract, evidence_warrant, negative_cases,
  theme_construction, codebook_consistency, domain_safety, contextual_boundary,
  revision_quality, reporting, or abstention.
- `scope`: the general methodological scope.
- `dataset_scope`: allowed datasets.
- `trigger`: when an agent should consider the rule.
- `rule`: what the agent should do.
- `required_checks`: concrete evidence or metadata checks.
- `failure_modes`: mapped WarrantRoute flags.
- `agent_targets`: roles allowed to receive this bullet.
- `status`: candidate, active, deprecated, or contradiction_hold.
- `approved_by`: required before active use in confirmatory experiments.

## 5. Initial Playbook Sections

The first frozen Playbook should cover the failure modes visible in the current
n100 run and the biomedical/thematic-analysis constraints.

### Evidence Warrant

- Do not treat a plausible alternative interpretation as a detected flaw unless
  the original claim overstates the evidence.
- Require a traceable basis for every material allegation.
- Distinguish weak support, missing support, counterevidence, and unsupported
  abstraction.
- Penalize claims that cite an excerpt but infer causal, diagnostic, subgroup,
  or temporal conclusions not present in the source.

### Negative Cases and Boundaries

- Check whether the source packet includes dissent, exceptions, low-intensity
  cases, or boundary conditions.
- If a claim states a uniform pattern, verify that all cited and nearby sources
  actually support uniformity.
- Prefer scope narrowing over rejection when the central pattern is partly
  supported.

### Source Concentration

- Record whether evidence comes from one source, one speaker, one thread, or one
  institutional context.
- Do not generalize a single cluster to a whole dataset unless the analytic
  contract explicitly permits it.

### Codebook and Theme Construction

- Separate codes, subthemes, themes, explanations, and causal accounts.
- Mark a code/theme confusion only when the claim changes analytic level without
  support.
- Avoid inventing a codebook rule that is not supplied in the packet.

### Biomedical and Sensitive-Domain Safety

- For biomedical or health-related material, avoid diagnostic, treatment,
  prognosis, causal, risk, or subgroup claims unless directly supported.
- For mental-health adjacent material such as Dreaddit, treat distress language
  as self-reported text, not as diagnosis.
- For AGYW or focus-group material, preserve local meanings and avoid importing
  external biomedical categories unless supplied.

### Political and Public-Discourse Context

- For ParlaMint-GB, preserve speaker role, party/government-opposition context,
  and debate framing.
- Do not collapse policy disagreement into one speaker's position.

### Short-Text and Emotion Labels

- For GoEmotions, avoid over-interpreting short comments as stable traits,
  motivations, or full social contexts.
- Treat emotion categories as possible signals, not complete thematic evidence.

### Revision Quality

- Revisions must make the smallest change that resolves the issue.
- A revision must not add new evidence IDs, direct quotations, or unsupported
  specificity.
- If a repair cannot be supported, the correct output is an uncertainty or
  narrower scope, not a stronger claim.

### Abstention

- Use cannot-judge only for missing essential context or expertise.
- Do not manufacture a flaw to justify escalation.
- Human escalation is not failure by itself, but repeated escalation means the
  automatic loop is not yet a manuscript-ready repair system.

## 6. Dataset Adapters

The Method Playbook should be shared, but each dataset needs a small adapter.

| Dataset | Adapter emphasis | Main risk |
| --- | --- | --- |
| Dreaddit | self-reported stress, mental-health adjacent language, anecdotal Reddit context | diagnostic or causal overreach |
| GoEmotions | short utterances, emotion-label context, sparse evidence | over-interpreting thin text |
| CaChe / AGYW focus groups | focus-group context, participant meaning, sensitive biomedical and social context | flattening local voices into generic health claims |
| ParlaMint-GB | parliamentary roles, policy disagreement, debate context | collapsing multiple positions into one theme |

Adapters may contain abstract cautions and metadata rules. They must not store
direct source passages or participant findings.

## 7. Integration With WarrantRoute

The Playbook should enter the current loop at five points.

1. Retrieval before each agent call.
   - Select 3 to 8 bullets by dataset, role, failure mode, claim structure, and
     route mode.
   - Do not retrieve bullets using hidden answer-key labels.

2. Agent prompting.
   - Add a `playbook_bullets` field to the payload.
   - Require agents to cite bullet IDs they actually used.
   - Keep bullet text short to avoid prompt bloat.

3. Structured outputs.
   - Populate `playbook_bullet_ids` in audit and revision records.
   - Validate that cited bullet IDs were supplied to that agent.

4. Scoring and diagnosis.
   - Compare failures by bullet exposure:
     credibility, conformability, recall, over-detection, unresolved escalation,
     revision success, and cost.
   - Count a bullet as helpful only with reliable feedback, not mere model
     self-report.

5. Freezing.
   - During Table 3 evaluation, bullet contents, retrieval rules, routing policy,
     prompts, models, and thresholds must be frozen.
   - No online Playbook update is allowed during evaluation.

## 8. Reliable Feedback Required

Candidate bullet creation requires at least one of the following signals:

- deterministic structural failure, such as invalid evidence ID or quote
  mismatch;
- human/expert adjudication of a review failure;
- repeated LLM-as-judge failure pattern confirmed by manual inspection on a
  development subset;
- repair outcome showing that a narrower or better-grounded revision resolves
  the issue without collateral error.

Do not create active bullets from:

- model confidence alone;
- agreement between two LLMs alone;
- held-out evaluation failures;
- source-specific participant findings;
- target flaw labels exposed to the evaluated agents.

## 9. What Must Be Built

Minimum implementation checklist:

1. `playbooks/warrantroute_method_playbook_v1.json`
   - active and candidate bullets with hashes.

2. `playbooks/dataset_adapters/*.json`
   - abstract dataset-specific cautions.

3. `schemas/warrantroute_playbook_bullet_v1.schema.json`
   - schema for bullet validation.

4. `scripts/build_warrantroute_playbook_candidates.py`
   - mines current development failures and proposes candidate bullets.

5. `scripts/validate_warrantroute_playbook.py`
   - validates schema, hashes, status, approvals, and no source-text leakage.

6. Runtime changes in `warrantroute_loop_runtime.py`
   - retrieve role-scoped bullets;
   - include bullets in payload;
   - validate cited `playbook_bullet_ids`;
   - log bullet use by role and packet.

7. Prompt changes in `warrantroute_loop_v2_playbook.md`
   - instruct agents to use only supplied bullets;
   - forbid treating a bullet as proof of a flaw;
   - require evidence-grounded application.

8. Evaluation scripts
   - compare no-playbook WarrantRoute against static-playbook WarrantRoute;
   - optionally compare candidate, human-approved, and ablated Playbook versions.

9. Human audit packet
   - sample failures and improvements for approval before claiming manuscript
     relevance.

## 10. Evaluation Plan

Use three stages.

### Stage A: Development Diagnosis

Use already exposed development packets. Diagnose why WarrantRoute loses
credibility or conformability relative to All roles. Propose candidate bullets.
No paper claim yet.

### Stage B: Frozen Static Playbook Pilot

Freeze an approved static Playbook and run a small matched pilot:

```text
same packets
same models
same WarrantGate policy
same judge
condition 1: WarrantRoute without Playbook
condition 2: WarrantRoute with static Playbook
```

Primary success condition:

- credibility and conformability improve without a large recall collapse.

Secondary checks:

- fewer human escalations;
- fewer unsupported-inference and contextual-flattening flags;
- lower harmful objection rate;
- stable cost and schema-valid outputs.

### Stage C: Confirmatory Table Run

Only after Stage B passes, freeze the final Playbook and run once on an
evaluation set. Do not update the Playbook during the run. Report that this is
a static Playbook condition unless human-approved development updates are part
of the declared method.

## 11. Expected Impact on Current Weak Results

The current n100 results suggest:

- Qwen needs Playbook bullets that reduce over-detection and require stronger
  evidence for each allegation.
- Llama needs stricter output discipline and simpler issue-selection bullets.
- Gemma needs recall-oriented bullets that ask it to check negative cases,
  source concentration, and unsupported abstraction more actively.

The Playbook should not simply tell every model to find more flaws. It should
make each role ask the right evidence question at the right time.

## 12. Manuscript Claim Boundary

Until implemented and evaluated, the correct claim is:

> The current WarrantRoute prototype is compatible with an ACE-inspired
> Playbook extension, but the reported n100 Table 3 results do not measure that
> extension because Playbook updates were disabled.

After a successful frozen static Playbook pilot, the claim may become:

> Adding a frozen, human-approved thematic-analysis Playbook improved the
> evidence-grounded quality of WarrantRoute reviews under matched local-LLM
> conditions.

Do not claim autonomous biomedical expertise, unbiased held-out accuracy, or
validated repair improvement without independent human audit.
