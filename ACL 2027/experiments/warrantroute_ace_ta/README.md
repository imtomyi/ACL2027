# WarrantRoute ACE-inspired TA runner

This private working experiment generates evidence-linked codes and provisional
themes using four methods and three local Ollama models. It implements five TA
roles plus a combined Playbook Updater. Code handles routing, format validation,
versioned updates, resumability and exports. A fixed Qwen judge evaluates final
artifacts separately. It is not the historical claim-review experiment.

## Frozen execution policy

- Four datasets, 100 evaluation packets each, 20 additional development packets
  each, three model configurations and four methods: 240 development episodes
  and 4,800 evaluation slots.
- Same-model method agents; fixed role is qualitative methods. All roles uses
  three independent candidates and one synthesis call. WarrantRoute uses a
  routed loop, at most two revisions and 12 inner calls.
- The independent scout initially sees only evidence. A separate scout audit
  then sees the proposed analysis. It routes issues by declared expertise.
- Development uses a further Evidence Scout feedback call and one merged
  Updater call. A rule references warranted, quotation-valid, counterchecked
  model feedback. Structural checks are not independent semantic validation.
- Memory is isolated by corpus and tested model, versioned after each completed
  update and frozen before evaluation. Common seed guidance is in seed_playbook.json.
  Final judge results never update memory. No best-score checkpoint selection.
- The executable v2 admits at most 40 active rules and 400 characters per learned
  rule's condition/action/exception. Excess proposals are retained as rejected
  capacity/length holds. This resource limit supersedes the proposal's 60-rule
  cap. At most six applicable rules are retrieved. Development feedback receives
  the final audit round; earlier audit rounds remain in the episode record.
- The user explicitly authorized CaChe as a within-source diagnostic on
  2026-09-09: different records and exact text, but shared source groups.
  Other corpora use source-disjoint development packets. All historical source
  exposure remains disclosed; none of these are new manuscript-qualified tests.
- This runner selects existing packet evidence, retaining text/order/context,
  and excludes constructed claims and builder labels. It creates no new defects.
- A conservative UTF-8 byte bound plus output allowance must fit the context.
  Oversized inputs become explicit technical failures; no silent truncation.
  Source-task eligibility is checked at preparation with a 12,000-byte bound.
  Oversized development candidates are skipped before selection. An oversized
  evaluation packet blocks preparation instead of silently changing its denominator.
- One retry only for explicit transient service failures. In-flight/timeout
  ambiguity is retained without resubmission. Schema errors and unfavorable
  semantic judgments are not retried. Full requests and responses are journaled.
- Executable v3 constrains quotation fields to exact source-span anchors in the
  response schema and constrains Updater target IDs to the supplied memory IDs.
  Anchors annotate the unmodified full evidence; they do not replace or shorten
  it. Source sentences longer than 240 characters receive consecutive literal
  anchor spans. Exact quote validation remains active after constrained generation.
  These structural constraints do not change the substantive judge rubric.
- Executable v4 additionally constrains operation/target combinations and permits
  only eligible feedback IDs in update proposals. Ineligible feedback remains in
  the episode journal. With no eligible feedback the only valid delta is empty.
  This prevents one unlinked reference from invalidating an otherwise linked
  proposal, without changing any feedback verdict or its eligibility criterion.
- Before the long continuation, one development episode per dataset/model and
  a quality-call check must finish structurally. Valid low quality does not fail
  qualification. Technical qualification failure stops for diagnosis.
- Executable v5 constrains artifact Playbook citations to the exact retrieved
  rule IDs supplied to that call. Calls without a Playbook must return an empty
  citation list. This applies identically to every model and method, prevents
  confusion with code IDs, and retains post-generation reference validation.

## Launch

### Version 6 safeguards

Version 6 starts with clean seed memories and the same selected inputs. Earlier
outputs remain separate. All seed rules are immutable in the output schema and
the commit validator. Only learned rules can be revised. Deprecation requires an
unchanged active learned replacement that retains the target's useful guidance.
Conflicting operations on the same target are all held, not executed in order.

A stateless validation pass of the same tested model checks each delta for
source grounding, procedural reusability, correct target, preserved safeguards
and nonredundancy. Every criterion must be true. The pass receives original
source evidence and linked feedback, not final judge scores. This is an extra
development call within the Updater workflow, not a new TA role or independent
human validation. Decisions bind to the exact proposal and parent-memory hashes.
Missing, duplicate, invalid or negative decisions hold changes. Guard technical
failures are reported separately and preserve the prior memory.
Feedback or Updater technical failures after a completed TA loop also preserve
that artifact for judging and keep the prior memory. They are counted separately
as update technical holds, not silently converted to successful adaptations.

Known packet/source/code IDs and case-specific code-edit patterns cannot enter
rules. Exact or high-overlap duplicates are held. New learned rules are corpus
scoped. Memory version advances only when at least one operation commits.
Seed integrity is checked again before freezing. These checks reduce identified
failure modes but do not prove that every learned rule improves performance.

The output cap is 4,096 tokens for every model/method to address the observed
2,400-token truncations. Context bounds remain enforced; no truncated response
is silently accepted or retried for a better answer. Comparisons against older
versions must disclose both the memory-policy and token-budget changes.
Intermediate judging remains isolated via interim_quality.py; it never feeds
the updater. Report its cost and the guard cost separately from evaluation.

Run from the ACL 2027 project directory. Preparation freezes the executable,
prompts, inputs, seed memory, configuration and model digests. It makes no model
generation calls. Source changes require a new prepared run.

```sh
/opt/anaconda3/bin/python3 -B experiments/warrantroute_ace_ta/run.py prepare --cache-policy within-source --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909
/opt/anaconda3/bin/python3 -B experiments/warrantroute_ace_ta/run.py run --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909
/opt/anaconda3/bin/python3 -B experiments/warrantroute_ace_ta/run.py status --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909
```

The same run command resumes completed work using exact request hashes and a
single-worker lock. Background execution should use screen and caffeinate.
No paid API transport is present. Local inference can take many hours.

## Progress and statistics

results.csv and results.md contain 48 cells. stats.json reports current counts,
tokens, failures, unresolved loops, learned operations and a provisional ETA
only when every remaining timing stratum has observations. active_call.json
and phase.json identify in-flight work. Store checkpoints after 50 and 100
quality records in each dataset/model/method cell and every 50 global quality
records. Checkpoint counts include technical missingness so failures cannot
silently shrink the denominator. Intermediate checks never change prompts,
select model winners or stop for unfavorable scores.

Each quality call returns Credibility, Conformability and evidence-coverage
judgments as true/false/null. CSV exports report all T/F/U/technical counts,
resolved pass rates, binary coverage, bounds over the completed judged inventory
and pending planned items. A low-scoring valid result remains in the experiment.
No natural-flaw recall or precision is inferred from these TA quality judgments.
Metadata and private evidence are stored locally under Storage.

Generated Playbooks live under development/<dataset>/<model>/playbook_current.json
and playbook_frozen.json, with immutable episode records preserving every delta.
A five-minute Codex heartbeat reports development, evaluation, quality and errors
independently; it does not act as an additional experiment judge.

## Validation

```sh
/opt/anaconda3/bin/python3 -B -m unittest discover -s experiments/warrantroute_ace_ta -p 'test_*.py'
```

Tests exercise input allowlisting, independent first passes, synthesis,
issue-owner rechecks, quote checks, corpus-scoped memory retrieval, isolated
updates, exact-request resume, failed/in-flight call handling and the 50-packet
checkpoint denominators. These are software checks, not validity evidence for TA.
