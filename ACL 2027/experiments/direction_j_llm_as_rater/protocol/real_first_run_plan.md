# Direction J real-data first-run plan

Status: **blocked before data access**. The intended sources are real Dreaddit
and `agyw_focus_groups` records. No fictional or synthetic data may be used.
Do not open either real dataset until the gate evidence below is complete and a
signed, prospective real-study freeze replaces the tracked template.

## Target roles

- Dreaddit train: approved development only.
- Dreaddit test: held-out in-domain audit only after the development freeze.
- `agyw_focus_groups`: cross-domain confirmatory evaluation only after every
  prompt, model snapshot, packet rule, defect definition, routing feature,
  threshold, expert-minute budget, outcome, and analysis artifact is frozen.

“Held out” means held out from this study's development. Do not claim that a
record was unseen during model training.

## Required gates before opening text

1. Document the institutional determination for secondary use, protected-text
   model processing, and human rating.
2. Document source/platform authorization separately: Reddit/platform approval
   for Dreaddit and the exact allowed-use, attribution, consent, and rater/model
   scope for `agyw_focus_groups`.
3. Approve the exact provider account, endpoint, model snapshot, processing
   terms, retention/deletion, training-use, human-access, subprocessors, and
   region.
4. Lock the exact corpus version, split, received-file hashes, allowed fields,
   prohibited fields, context limits, and processing purpose.
5. Complete two-person privacy and quotation clearance for every excerpt and
   local-context window shown to a model or person.
6. Freeze cluster-aware sampling and packet manifests. Preserve Dreaddit
   post/document clusters and AGYW focus-group/speaker clusters.
7. Approve access control, separation of identifiers, raw-output retention,
   deletion, withdrawal handling, and release-cleared fields.
8. Freeze the item builder, prompt, shared guide, human instrument, response
   schemas, blinding map, model configuration, repetitions, aggregation,
   calibration target, error severities, rationale rubric, repair assessment,
   cost accounting, budget, and analysis code before held-out access.

Any missing item is a stop condition. There is no operator override.

## First authorized sequence

1. Create an access-restricted gate record and fill
   `config/real_study_freeze.template.json` from documentary evidence. A
   template is never approval.
2. Build one evaluator item per theme from privacy-cleared real packets. Keep
   condition, generator identity, candidate family, and adjudication in a
   private map outside evaluator runtimes.
3. Verify that Charlie, the LLM judge, and later independent humans receive the
   identical canonical item and complete guide and return the same full shared
   rating object. Record Charlie's actual item-construction relationship; do not
   infer independence.
4. Lock first-stage ratings before independent qualitative-methods and domain
   experts rate and adjudicate. Preserve `plural_ambiguous` disagreement.
5. Unblind only after all declared locks. Analyze Dreaddit development/audit and
   AGYW confirmatory results separately with cluster-aware uncertainty.
6. Report agreement as a diagnostic, not validity. Compare every first-stage
   actor against independent expert adjudication and downstream serious-error,
   escalation, repair, cost, and latency outcomes.

## Current first step

Collect and approve the missing institutional, source/platform, provider, and
data-contract records. Until then, the correct run count is zero and no dataset
text should be opened.
