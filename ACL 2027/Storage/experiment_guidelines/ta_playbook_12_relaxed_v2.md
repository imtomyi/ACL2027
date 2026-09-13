# TA Playbook V2: Useful Operational Detail

Protocol: `ta-artifact-playbook-operational-specificity-v2`.
Status: policy/interface implementation for a fresh local development run.
The user authorized a moderate relaxation of rule-addition criteria. This
revision does not itself authorize inference, paid API calls or manuscript use.
Do not amend or replay the frozen V1 run as though it had used this policy.

## What Is Relaxed

A rule no longer needs a substantively new mechanism beyond existing guidance.
A grounded, reusable elaboration of a seed or learned rule can be admitted when
it adds a concrete checking step, observable trigger or countercondition.
Partial overlap with existing guidance is acceptable. Merely paraphrasing it,
duplicating its full content, or adding text to inflate a rule count is not.

The former combined duplicate/contradiction criterion is split. Novelty is a
descriptive field, not a veto. This is not a majority-vote shortcut: all seven
required audit decisions must still be true:

| Check | V2 Requirement |
| --- | --- |
| Grounded lesson | The procedure follows from the source-to-TA relation. |
| Reusable, not memorized | It applies beyond this particular participant, code or theme. |
| Counterconditions preserved | Legitimate alternatives, uncertainty and scope remain protected. |
| No unsupported domain inference | No invented causal, clinical or other domain premise. |
| No contradiction | No conflict with retained sound guidance. |
| Operationally useful | An actionable checking step, not a label, fact or cosmetic restatement. Useful overlap is allowed. |
| No leakage | No participant facts, quotations, case IDs, answers or evaluator information in reusable fields. |

False or unknown on these required checks still withholds the proposal.
Separately, distinct_contribution may be true, false or unknown. False means
overlapping/supporting guidance; unknown means novelty is not established.
Neither blocks an otherwise grounded, safe and useful procedure. Exact duplicate
content is still rejected by code and does not receive a new rule ID.

Raw novelty verdicts are preserved. Receipts and query CSVs separately identify
additions without established novelty. Do not describe those additions as newly
discovered mechanisms. The reducer adapter derives its legacy combined gate from
the passed V2 safety checks and existing exact-duplicate guard; it does not
rewrite the raw audit or turn its novelty judgment into true. Same-model
admission remains fallible and is not independent validation.

## Interface Corrections, Separately Recorded

The preceding V1 produced ten candidates but none reached semantic audit: seven
failed add-target validation, and three failed artifact-anchor validation.
Consequently, V1 does not show that the strict novelty criterion caused those
rejections. Relaxation alone would not have resolved them.

V2 also changes the learning interface prospectively:

- Add proposals do not expose target_rule_id to the model. The controller assigns
  the canonical empty target because adding is not editing an existing rule.
- Refine proposals can select only a currently existing non-seed rule. Reinforce
  proposals identify an existing rule and carry evidence, not replacement text.
- Each operation has a complete separate schema branch. There are no shared
  parent properties alongside anyOf branches, avoiding the previously observed
  grammar-backend ambiguity in the old paragraph work.
- Artifact anchors select a real collection/unit/field through target_slot. Code
  expands that selection deterministically; the quote still must match the
  selected field. Wrong quotes are not relocated, normalized or rewritten.
- The learner is explicitly told that applicability is a condition, not true or
  false, and detection_check is an action, not a category name. Placeholder-only
  fields are rejected. Source/artifact quotations remain separate.
- The operational_detail field states the useful added step or boundary. For
  compatibility the canonical reducer stores it as novel_condition. That legacy
  name does not restore the old novelty requirement.
- The exact output schema is included in the learner/auditor prompt as well as
  the structured-output format. Shared anchor definitions bound schema growth.

These are declared wire-to-canonical mappings, not retrospective repairs of old
model responses. Raw requests and responses remain preserved. A V1 candidate
with an invalid target or quote is not automatically imported or accepted.

## Unchanged Study and Protections

For the optional next local smoke, reuse the same three locked TA artifacts
from twelve previously exposed Dreaddit development paragraphs, three epochs,
nine review/update exposures, and at most 27 additional local Gemma 3 4B calls.
Keep the same model digest, temperature, seed, 49,152 context, 4,096 output-token
ceiling, 30-minute budget, and 180-second per-call timeout as V1.

Start from a fresh copy of the same two generic seed rules, not the rejected V1
candidates, old paragraph-learned rules, manual eight-rule draft, or assistant
inspection notes. No source selection based on outcomes. Preserve the locked
codes/themes without regeneration or repair. Per-query updates, three-epoch
memory continuity, exact TXT delivery, stable shr IDs, candidate IDs, duplicate
handling, seed immutability and memory limits remain in place.

The detector request is deliberately byte-equivalent to V1 given identical
configuration, task and Playbook. Only the learner/auditor interface and the
novelty-related interpretation change. Therefore a future V1/V2 difference
cannot be attributed solely to a looser admission criterion; the interface
corrections also changed. Do not present this as an isolated novelty ablation.

There is no gold inventory, quality-scoring authorization or manuscript export.
Do not claim accuracy, recall, Credibility/Conformability, improved detection or
successful new-rule learning based on offline checks. Rule counts are not quality.
No forced additions, paid calls, model downloads or ambiguous-call retries.

## Implementation and Verification

`ta_playbook_relaxed_contract.py` defines the V2 prompts, operation-specific
schemas and canonical mappings. It delegates unchanged source/target eligibility,
audited memory updates and TXT identity handling to the existing tested code.
`run_ta_playbook_relaxed.py` is an intentionally separate controller version,
retaining V1's execution behavior without editing files covered by V1's frozen
code manifest. Its new manifests include both strict helper and V2 source files.

Source-free tests cover absent add targets, forbidden extra targets, seed-refine
rejection, learned-rule refinement, reinforcement without text mutation, exact
slot mapping, wrong quotes withheld, seven hard checks including unknown values,
false/unknown novelty admitted only when required checks pass,
exact duplicates, placeholder rejection, source protection, no-change, unchanged
detector requests, explicit schema delivery and local-only restrictions.
Offline tests do not establish live grammar compatibility or semantic quality.

Use the controller's prepare command with a fresh run directory under private
Storage. Its run command additionally requires --authorize-local-inference and
a separately explicit launch request. Status is read-only; pause uses a query
boundary. Existing V1 results, Playbooks and manuscript files are not changed.
