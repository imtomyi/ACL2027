# WarrantRoute Playbook Structure

This document explains the current WarrantRoute Playbook implementation. The
Playbook is inspired by ACE's itemized memory concept, but in the Table 3
experiment it is used as a **static frozen methodological Playbook** to prevent
evaluation contamination.

In other words, the Playbook does not learn or update itself during evaluation.
It provides fixed method-rule bullets to WarrantRoute agents, and each agent
records the bullet IDs it actually used.

## 1. Core Files

| Purpose | File |
| --- | --- |
| Playbook body | `experiments/rq2_role_prompted_llm/playbooks/warrantroute_method_playbook_v1.json` |
| Dreaddit adapter | `experiments/rq2_role_prompted_llm/playbooks/dataset_adapters/dreaddit.json` |
| GoEmotions adapter | `experiments/rq2_role_prompted_llm/playbooks/dataset_adapters/goemotions.json` |
| CaChe / AGYW adapter | `experiments/rq2_role_prompted_llm/playbooks/dataset_adapters/agyw_focus_groups.json` |
| ParlaMint-GB adapter | `experiments/rq2_role_prompted_llm/playbooks/dataset_adapters/parlamint_gb.json` |
| Playbook schema | `experiments/rq2_role_prompted_llm/schemas/warrantroute_playbook_bullet_v1.schema.json` |
| Playbook prompt | `experiments/rq2_role_prompted_llm/prompts/warrantroute_loop_v2_playbook.md` |
| Playbook config | `experiments/rq2_role_prompted_llm/config/warrantroute_loop_n100_same_model_playbook_v1.json` |
| Validator | `experiments/rq2_role_prompted_llm/scripts/validate_warrantroute_playbook.py` |
| Runtime integration | `experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py` |

## 2. Top-Level Structure

The main Playbook file has the following top-level structure.

```json
{
  "playbook_schema_version": "warrantroute-method-playbook-v1",
  "playbook_id": "warrantroute_method_playbook_v1",
  "version": 1,
  "status": "active_static_pilot",
  "updates_enabled": false,
  "source_text_allowed": false,
  "description": "...",
  "bullets": []
}
```

| Field | Meaning |
| --- | --- |
| `playbook_schema_version` | Version of the Playbook file structure |
| `playbook_id` | Stable Playbook identifier used by the experiment |
| `version` | Playbook version |
| `status` | Current status, currently `active_static_pilot` |
| `updates_enabled` | Whether the Playbook can update during evaluation; currently `false` |
| `source_text_allowed` | Whether direct source text may be stored in the Playbook; currently `false` |
| `bullets` | Reusable method-rule bullets supplied to agents |

`updates_enabled=false` is important. If the Playbook changed during Table 3
evaluation, the run could suffer from held-out contamination or adaptive prompt
leakage. The current design therefore builds the Playbook from development
diagnosis, freezes it, and disables updates during evaluation.

`source_text_allowed=false` is also important. The Playbook must not memorize
participant text, source excerpts, or packet-specific findings. It may contain
only reusable methodological review rules.

## 3. Bullet Structure

The basic unit of the Playbook is a `bullet`. A bullet is a small methodological
rule that an agent can apply in a specific situation.

Example:

```json
{
  "bullet_id": "pb-evidence-0001",
  "section": "evidence_warrant",
  "scope": "thematic_review:all",
  "dataset_scope": ["all"],
  "trigger": "a review alleges a material flaw in a qualitative claim",
  "rule": "State the exact source-grounded warrant problem. Do not mark a flaw only because another interpretation is also plausible.",
  "required_checks": ["claim_scope", "cited_support", "counterevidence_scan"],
  "failure_modes": ["unsupported_inference", "unsupported_abstraction"],
  "exceptions": ["the claim directly contradicts supplied evidence"],
  "agent_targets": ["proposer", "evidence_scout", "methods_challenger", "domain_challenger", "reviser"],
  "provenance": ["current_n100_failure_diagnosis"],
  "status": "active",
  "version": 1,
  "approved_by": ["protocol_static_pilot"],
  "helpful_count": 0,
  "harmful_count": 0
}
```

## 4. Bullet Fields

| Field | Meaning |
| --- | --- |
| `bullet_id` | Stable bullet identifier. Agents cite this in `playbook_bullet_ids`. |
| `section` | Rule category, such as `evidence_warrant`, `negative_cases`, or `domain_safety`. |
| `scope` | Analytic scope where the rule applies. |
| `dataset_scope` | Dataset scope: `all` or a specific corpus ID. |
| `trigger` | Situation in which the agent should consider the bullet. |
| `rule` | The actual methodological instruction. |
| `required_checks` | Concrete checks required when applying the bullet. |
| `failure_modes` | WarrantRoute flaw types the bullet is intended to reduce. |
| `exceptions` | Situations where the bullet should not be applied mechanically. |
| `agent_targets` | Agent roles allowed to receive this bullet. |
| `provenance` | Why the bullet exists. |
| `status` | One of `active`, `candidate`, `deprecated`, or `contradiction_hold`. |
| `version` | Bullet version. |
| `approved_by` | Activation approval record. |
| `helpful_count` | Future counter for reliable evidence that the bullet helped. |
| `harmful_count` | Future counter for reliable evidence that the bullet harmed performance. |

The current `approved_by` value is `protocol_static_pilot`. For manuscript-grade
claims, this should be replaced or supplemented with a real human approval
record.

## 5. Current Ten Bullets

| Bullet ID | Section | Purpose |
| --- | --- | --- |
| `pb-evidence-0001` | `evidence_warrant` | Requires an exact source-grounded warrant problem before alleging a material flaw. |
| `pb-evidence-0002` | `negative_cases` | Checks exceptions, dissent, and boundaries before accepting a broad or uniform theme. |
| `pb-evidence-0003` | `evidence_warrant` | Treats source, speaker, thread, or group concentration as a scope limit. |
| `pb-theme-0004` | `theme_construction` | Separates codes, subthemes, themes, causal explanations, and abstractions. |
| `pb-domain-0005` | `domain_safety` | Prevents biomedical or health-adjacent overreach. |
| `pb-dataset-0006` | `contextual_boundary` | Prevents over-interpretation of short GoEmotions text. |
| `pb-dataset-0007` | `contextual_boundary` | Preserves participant meaning in CaChe / AGYW focus-group material. |
| `pb-dataset-0008` | `contextual_boundary` | Preserves speaker role, institutional position, and disagreement in ParlaMint-GB. |
| `pb-revision-0009` | `revision_quality` | Requires minimal evidence-supported revision. |
| `pb-abstain-0010` | `abstention` | Defines when cannot-judge or escalation is appropriate. |

## 6. Dataset Adapters

The Playbook body is accompanied by dataset adapters. An adapter defines the
dataset's priority failure modes and cautions.

Example:

```json
{
  "adapter_schema_version": "warrantroute-dataset-adapter-v1",
  "corpus_id": "goemotions",
  "dataset_label": "GoEmotions",
  "scope": "short affective social-media text",
  "priority_failure_modes": ["unsupported_inference", "contextual_flattening", "lost_negative_case"],
  "cautions": [
    "Do not infer stable traits, motives, identities, or full social context from sparse comments.",
    "Treat emotion labels as weak analytic signals, not complete thematic evidence.",
    "Prefer short, evidence-proportionate critiques."
  ]
}
```

The current adapter mainly affects retrieval priority. For example, GoEmotions
packets prioritize short-text caution bullets.

## 7. Dataset Adapter Purposes

| Dataset | Adapter purpose | Main risk |
| --- | --- | --- |
| Dreaddit | Treat stress and mental-health-adjacent language as source-reported language. | Diagnostic or causal overreach |
| GoEmotions | Prevent over-interpretation of short affective/social text. | Inferring stable traits, motives, or context from sparse text |
| CaChe / AGYW | Preserve focus-group participant meaning and local context. | Flattening participant voice into generic biomedical or social claims |
| ParlaMint-GB | Preserve parliamentary speaker role and policy disagreement. | Collapsing multiple political positions into one theme |

## 8. Runtime Behavior

Playbook-enabled WarrantRoute does not supply all bullets to every agent. The
runtime selects relevant active bullets based on role, dataset, and priority
failure modes.

Runtime flow:

```text
packet input
  -> check dataset adapter
  -> check agent role
  -> retrieve relevant active bullets
  -> add playbook_bullets to the agent payload
  -> agent performs review or revision
  -> agent records playbook_bullet_ids in output
  -> validator checks that only supplied bullet IDs were cited
```

The agent payload receives:

```json
{
  "playbook_bullets": [
    {
      "bullet_id": "pb-evidence-0001",
      "section": "evidence_warrant",
      "scope": "thematic_review:all",
      "trigger": "...",
      "rule": "...",
      "required_checks": ["..."],
      "failure_modes": ["..."],
      "exceptions": ["..."]
    }
  ],
  "playbook_instruction": "Use only the supplied Playbook bullets when they apply..."
}
```

The agent output includes:

```json
{
  "playbook_bullet_ids": ["pb-evidence-0001", "pb-evidence-0002"]
}
```

The validator rejects invented or unavailable bullet IDs. Agents can cite only
bullet IDs that were actually supplied in the payload.

## 9. Role-Specific Retrieval

The runtime prioritizes different Playbook sections by role.

| Role | Priority sections |
| --- | --- |
| `proposer` | `analytic_contract`, `evidence_warrant`, `theme_construction`, `abstention` |
| `evidence_scout` | `evidence_warrant`, `negative_cases`, `contextual_boundary`, source concentration checks |
| `methods_challenger` | `codebook_consistency`, `theme_construction`, `negative_cases`, `evidence_warrant` |
| `domain_challenger` | `domain_safety`, `contextual_boundary`, `abstention`, `evidence_warrant` |
| `reviser` | `revision_quality`, `evidence_warrant`, `negative_cases`, `domain_safety` |

The config limits the number of bullets per call.

```json
{
  "retrieval": {
    "max_bullets_per_call": 6,
    "require_active_status": true,
    "updates_enabled_during_evaluation": false
  }
}
```

## 10. Relationship to ACE

The original ACE pattern is approximately:

```text
Generator
  -> Reflector
  -> Curator
  -> Playbook update
```

The current WarrantRoute Playbook does not update during evaluation.

Current structure:

```text
development diagnosis
  -> static Playbook creation
  -> Playbook freeze
  -> WarrantRoute evaluation run
  -> no Playbook updates during evaluation
```

The most accurate manuscript phrase for this implementation is:

```text
ACE-inspired frozen methodological Playbook
```

The following phrase would be inaccurate:

```text
ACE-style online self-updating memory
```

## 11. Problems Targeted by the Current Playbook

| Observed problem | Playbook response |
| --- | --- |
| Qwen over-detection | Requires an exact source-grounded warrant problem before alleging a flaw. |
| Gemma under-detection | Makes negative-case, source-concentration, and unsupported-abstraction checks explicit. |
| Llama unstable issue/revision behavior | Simplifies issue selection and revision-quality rules. |
| Low GoEmotions review quality | Prevents motive, trait, and contextual over-inference from short text. |
| Dreaddit health-adjacent risk | Prevents treating distress language as diagnosis. |
| CaChe / AGYW context flattening | Preserves participant meaning and focus-group context. |
| ParlaMint-GB discourse flattening | Preserves speaker role and policy disagreement. |

## 12. Validation Status

The current implementation passed the following checks:

```text
Playbook validator: passed
Existing WarrantRoute/Table3 tests: 31 tests passed
Full n100 playbook preflight: passed
Smoke experiment: completed
```

In the smoke experiment, agents actually recorded these bullet IDs:

```text
pb-domain-0005
pb-evidence-0001
pb-evidence-0002
pb-evidence-0003
pb-revision-0009
pb-theme-0004
```

## 13. Interpretation Caveats

The current Playbook is not yet manuscript-qualified evidence.

Reasons:

- `approved_by` currently uses a static-pilot placeholder, not a full human
  approval record.
- The Playbook was derived from prior n100 failure diagnosis.
- A manuscript-grade comparison requires a matched no-Playbook versus
  Playbook-enabled WarrantRoute experiment using the same packets, models,
  judge, and scoring rules.
- The Playbook is methodological memory for review quality, not memory of
  source text or answer keys.

The safest comparison is:

```text
same packets
same models
same WarrantGate policy
same judge

Condition 1: WarrantRoute without Playbook
Condition 2: WarrantRoute with frozen static Playbook
```

If Credibility and Conformability improve without a large recall collapse, the
Playbook-enabled WarrantRoute can be interpreted as an improvement over the
previous WarrantRoute prototype.
