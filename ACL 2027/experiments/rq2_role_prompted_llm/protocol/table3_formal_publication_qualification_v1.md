# Table 3 formal publication qualification contract v1

Status: prospective procedure freeze; approvals and final study freeze pending  
Applies to: the four-dataset, four-method, three-model Table 3 experiment  
Does not authorize: the completed `balanced_n100` working experiment or any
other existing result under `Storage/`

## 1. Purpose

This contract defines the only path by which a future Table 3 result may move
from an internal working diagnostic to manuscript evidence. It separates five
states that must never be conflated:

```text
working diagnostic
  -> governance cleared
  -> design and implementation frozen
  -> untouched evaluation completed
  -> independently validated frozen analysis export
  -> manuscript eligible
```

No state may be entered by renaming a file, changing a Boolean, copying an
existing result, or obtaining approval after test outcomes have been inspected.

## 2. Non-retroactivity

The following completed run is permanently classified as development evidence:

```text
Storage/draft_review_packets/table3_warrantroute_n100_final_manifest.json
```

Its 3,600 reviewer outputs and 48 table rows may be used for software debugging,
prompt diagnosis, router development, power planning, and protocol design. They
must not be reported as the untouched confirmatory or descriptive evaluation of
the successor policy.

Any packet, source cluster, truth label, role output, or derived feature accessed
during this working run is considered development-exposed. A final test set must
be disjoint at the corpus-specific source-cluster level, not only by packet ID.

## 3. Prospective Table 3 scope

The intended table has the following fixed dimensions. Exact corpus receipts,
model digests, sample sizes, and the final WarrantRoute successor remain blocked
until their respective gates below are complete.

### Corpora and display order

1. Dreaddit
2. GoEmotions
3. CaChe
4. ParlaMint-GB

Display names and order must match the active manuscript and Table 1.

### Reviewer roles

1. `generalist`
2. `qualitative_methods`
3. `domain`

### Compared methods

1. Generalist
2. Fixed role
3. All roles
4. WarrantRoute

### Reviewer model families

1. Qwen3 8B
2. Llama 3.1 8B
3. Gemma 3 4B

The family names are not adequate execution identifiers. Exact immutable model
digests and runtime versions must be recorded in the final study freeze.

### Complete reviewer-output matrix

The formal experiment must regenerate the complete role-output matrix for all
three models. WarrantRoute alone must never be rerun against cached test outputs
and compared with development-exposed baselines. At balanced n=100 with the
currently specified three repetitions, the required inventory is:

```text
4 corpora x 100 packets x 3 reviewer roles x 3 models x 3 repetitions
  = 10,800 reviewer outputs
```

Each repetition contains 3,600 reviewer outputs. The 48 Table 3 rows are then
derived from this one frozen matrix as 4 corpora x 4 methods x 3 models. The
four method labels do not imply four separately prompted reviewer runs:

- Generalist uses only the Generalist role output.
- Fixed role uses one shared role selected by pooling development results across
  the three frozen reviewer models.
- All roles combines the three role outputs under the frozen union rule.
- WarrantRoute uses the frozen routing policy and composition rule.

All four rows must therefore share packet IDs, model snapshots, repetition
seeds, prompts, failure handling, and scoring code. Fixed-role selection and
WarrantRoute fitting remain development-only operations and must be frozen
before any final-test outcome is inspected.

### Baseline-first acquisition phase

WarrantRoute may be deferred while it remains under development. A baseline
phase may acquire and seal the complete three-role reviewer matrix needed by
Generalist, Fixed role, and All roles without selecting or applying a router.
This phase still requires 10,800 reviewer outputs because All roles requires all
three roles. It prepares 36 baseline table rows rather than the final 48 rows.

To preserve a later same-packet WarrantRoute comparison, final-test truth and
baseline scores must remain unavailable to router development until the router
policy is frozen. If baseline test scores are inspected before the router is
frozen, a later WarrantRoute evaluation must use a new cluster-disjoint test set
and cannot be inserted as a directly comparable row beside those baseline
scores.

The baseline-only preflight is:

```bash
python3 experiments/rq2_role_prompted_llm/scripts/validate_table3_formal_freeze.py \
  --phase baseline
```

## 4. Governance gate

Every corpus must pass the following ten gates in this order before any formal
packet text is opened by a model or human rater:

1. `institutional_determination`
2. `source_platform_authorization`
3. `provider_model_processing`
4. `exact_corpus_input_contract`
5. `two_person_excerpt_privacy_review`
6. `cluster_aware_sampling`
7. `frozen_study_manifest`
8. `rater_and_service_access_controls`
9. `retention_deletion_controls`
10. `release_controls`

Each completed gate requires a nonempty evidence reference, approval authority
ID, evidence version, approval timestamp, expiry timestamp, and last verification
timestamp. Approval is corpus-, receipt-, endpoint-, role-, and purpose-specific.

The formal project governance record must contain dedicated lanes for all four
Table 3 corpora. The current tracked template does not contain GoEmotions or
ParlaMint-GB lanes. They must be added to a new version of the template and
supported by the readiness checker before a four-corpus run can pass.

The agent may validate evidence records but may not act as the institutional,
platform, data-provider, privacy, or release approval authority. Unknown facts
remain `pending`; they must never be inferred from public availability, a
license, successful download, deidentification, or local filesystem access.

Required pre-run command:

```bash
python3 governance/scripts/check_project_readiness.py \
  --record governance/local/project_governance.local.json \
  --reviewer-registry governance/local/reviewer_registry.local.json \
  --privacy-log governance/local/privacy_review_log.local.json \
  --as-of <CURRENT-UTC-TIMESTAMP> \
  --output governance/local/readiness_report.local.json
```

The formal run is blocked unless the generated report says all four exact corpus
lanes are ready and all 40 corpus-gates are complete.

## 5. Data separation and sampling gate

### Development set

Development data may be used to:

- choose Fixed role;
- fit or calibrate WarrantRoute;
- choose route thresholds and cost budget;
- debug prompts and schemas;
- estimate variance and plan sample size.

### Final evaluation set

The final set must satisfy all of the following before model execution:

- no source-cluster overlap with any development-exposed packet;
- one frozen packet manifest and SHA-256 per corpus;
- one private truth map excluded from every reviewer and router payload;
- cluster-preserving sampling using the corpus-specific unit;
- a prospectively justified sample size and flaw-family allocation;
- clean/no-flaw controls if precision, specificity, or false-positive behavior is
  claimed;
- a sealed test-access log showing who accessed packet text, truth, and outputs.

The target may be balanced n=100 per corpus only if 100 eligible, privacy-reviewed,
cluster-disjoint final packets exist after exclusions. N must never be reduced to
hide failures or forced to 100 by reusing exposed packets.

The current ParlaMint-GB working bank contains only 100 packets and all 100 have
already been used in the diagnostic run. A fresh n=100 ParlaMint-GB test therefore
requires additional eligible source material. If it cannot be obtained, the
formal design must be amended and frozen prospectively before any replacement
test truth is inspected. The current 100 must not be relabeled as untouched.

## 6. Method-definition gate

The following choices must be resolved before the final study freeze.

### Generalist

Apply only the frozen Generalist prompt and shared rating guide to every packet.

### Fixed role

Select one role shared by all reviewer models using development data only. Pool
true positives and denominators across the three frozen reviewer models, then
apply the prospectively frozen tie order. Freeze the shared role before final
test execution. Never reselect it by model, on final test data, within a test
corpus, or inside a bootstrap resample.

### All roles

Apply all three frozen role prompts. Freeze whether the final response is a flag
union or an adjudicated synthesis. The same definition must be used in code,
table prose, and statistical analysis.

### Prompt identity across methods and models

The role prompts are model-neutral assets. For a fixed packet, role, and
repetition, Qwen3 8B, Llama 3.1 8B, and Gemma 3 4B receive byte-identical task
text. Generalist maps to the frozen `generalist` prompt. Fixed role maps to the
single frozen shared role. All roles maps to the same three frozen role prompts
and unions their flags after generation. All roles is not a fourth combined LLM
prompt. Model- or dataset-specific task-text overrides are prohibited.

### WarrantRoute

The current manuscript describes specialist replacement, while the working
diagnostic identifies a Generalist-preserving cascade as the leading successor.
One definition must be selected before freeze:

```text
replacement: G | M | D | M+D
cumulative:  G | G+M | G+D | G+M+D
```

The choice must be reflected simultaneously in the policy, route builder,
scorer, appendix, method prose, and tests. No mixed definition is allowed.

The WarrantRoute successor must be trained or calibrated only on development
data. Its inference inputs may contain only prospectively declared pre-specialist
signals. Test truth, intended-flaw labels, specialist outcomes, adjudication,
and held-out results are prohibited router features.

## 7. Model and prompt freeze gate

The final study manifest must freeze:

- exact model artifact name and immutable digest for all three models;
- Ollama/runtime version and hardware execution class;
- role-prompt and shared-guide paths plus SHA-256 hashes;
- response schema and semantic consistency validator hashes;
- `temperature`, `top_p`, `num_ctx`, `num_predict`, seed, timeout, and retry rule;
- repetition count and aggregation rule;
- normalization, invalid-output, timeout, and missing-output rules;
- role order, method order, dataset order, and display names.

The active manuscript currently specifies three repetitions and a sensitivity
analysis retaining flags selected in at least two of three repetitions. A formal
Table 3 run must either execute that frozen rule or amend the manuscript and
protocol before final-test access. The completed one-repetition working run does
not satisfy this gate.

Temperature without a frozen seed is prohibited for the final run. Model tags
without immutable digests are prohibited.

## 8. Router freeze gate

The frozen WarrantRoute policy must record:

- policy ID, version, file hash, and training-data manifest hash;
- feature names, encodings, missing-value rules, and normalization by model;
- permitted feature-source boundary;
- action set and selected-output semantics;
- weights or fitted model parameters;
- call/token/latency cost definition and budget;
- score precision and numerical tie tolerance;
- tie order, fallback, timeout, and failed-role behavior;
- calibration procedure and development performance;
- route-builder and independent-validator hashes.

The current floating-point tie behavior must be repaired before qualification.
The independent validator must not call the same route-selection helper used by
the generator.

If Generalist output is required to compute a route, its call must be included in
cost accounting. If cumulative routing is selected, tests must guarantee that a
routed output cannot lose a Generalist detection from the same repetition.

## 9. Outcome and statistical freeze gate

Before final-test truth access, freeze:

- primary reviewer model;
- primary corpus and comparison;
- primary endpoint and direction;
- all descriptive and sensitivity analyses;
- cluster unit for every corpus;
- interval and resampling method;
- multiplicity rule;
- nonestimable-cell and missingness handling;
- success, failure, and stopping criteria.

Unless prospectively amended, the active manuscript requires:

```text
primary confirmatory comparison:
  CaChe WarrantRoute versus Fixed role for one frozen primary reviewer model

uncertainty:
  10,000 paired source-cluster bootstrap resamples

bootstrap seed:
  20270826
```

Wilson intervals may be shown for a working diagnostic but do not replace the
frozen paired cluster analysis.

If cost-sensitive routing is claimed, recall must be reported with at least one
frozen resource measure such as reviewer calls, generated tokens, or latency.
All-positive intended-flaw packets cannot support precision or false-positive
claims.

Credibility and confirmability require a separate frozen judge protocol that
defines the judge model and digest, prompt, binary decision rule, blinding,
aggregation, disagreement handling, and human-audit subset. A skipped judge may
not produce those metrics.

## 10. Pre-run qualification sequence

The sequence is mandatory:

1. Complete all corpus-specific external evidence records.
2. Run the 40-gate formal readiness check.
3. Freeze source receipts and cluster-aware development/test manifests.
4. Seal development and final packet manifests and the private truth map.
5. Resolve WarrantRoute semantics and qualify candidate routers on development
   data only.
6. Select Fixed role on development data only.
7. Designate the primary model and confirmatory comparison.
8. Freeze prompts, schemas, models, decoding, repetitions, metrics, and scripts.
9. Run schema, semantic, route-invariant, contamination, and negative-control
   tests without opening final-test truth.
10. Generate a pre-run freeze manifest and verify every bound artifact hash.
11. Obtain the responsible approval authority's activation record.
12. Only then unlock the formal queue.

Failure at any step returns the study to `blocked_before_formal_execution`.

## 11. Execution conduct

- Use a new queue ID and output root reserved for the formal freeze.
- Never mix working and formal outputs.
- Run only the packet IDs and repetitions in the frozen manifest.
- Do not change prompts, model artifacts, decoding, retries, role semantics, or
  scoring after the first final-test request.
- Preserve every valid response, failure, timeout, retry, and recovery event.
- Do not reduce N, remove difficult packets, replace failed packets, or repair
  semantic decisions against truth.
- Repair transport/schema failures only under the prospectively frozen rule.
- Keep truth inaccessible to reviewers, router inference, and operators who do
  not need it.
- Abort on artifact-hash mismatch, corpus-lane expiry, test contamination,
  duplicate reviewer processes, or an unplanned software change.

## 12. Post-run validation and promotion

The finalizer must independently verify:

- exact packet, role, model, repetition, method, and dataset cardinalities;
- all reviewer schema and semantic constraints;
- output-to-packet, prompt, model, and policy hashes;
- route reproduction with the independently implemented rule;
- Fixed-role development-only selection;
- absence of final-test truth in every prompt and route record;
- paired cluster scoring and frozen bootstrap seed;
- agreement among detail rows, table rows, prose-ready export, and manifest;
- complete failure and retry accounting;
- current unexpired 40-gate readiness at export time.

The analysis export must be immutable and include hashes for every input,
configuration, executable, and output class. `manuscript_eligible=true` may be
emitted only by a promotion validator after every condition above passes. It
must never be edited manually.

Before manuscript insertion, run:

```bash
python3 governance/scripts/check_manuscript_data_policy.py
python3 governance/scripts/check_required_manuscript_citations.py
./build_manuscript_pdf.sh
```

All Table 3 cells, related result prose, captions, appendix values, abstract
claims, and limitations must be updated from the same frozen export in one
change. If any required result remains unavailable, preserve the explicit
manuscript placeholder.

## 13. Mandatory stop conditions

Stop without opening or continuing the formal test when any of the following is
true:

- any corpus has fewer than 10/10 current governance gates;
- GoEmotions or ParlaMint-GB has no formal governed corpus lane;
- final packets overlap a development source cluster;
- sample size or cluster plan is not frozen;
- WarrantRoute semantics differ across policy, scorer, and manuscript;
- Fixed role was selected using final-test outcomes;
- model digest, prompt hash, seed, or repetition rule is missing;
- route ties depend on floating-point accidents;
- the primary comparison was chosen after final-test inspection;
- a result file is marked working-only or manuscript-ineligible;
- the final export cannot be regenerated from its recorded hashes.

## 14. Current blocker register

As of this contract's creation, the following are blockers, not completed gates:

1. The tracked formal readiness report says all real corpora are not ready and
   reports 0/10 gates for each existing real lane.
2. The formal governance template has no GoEmotions or ParlaMint-GB lane.
3. The completed four-corpus outputs are under a working diagnostic root and are
   explicitly manuscript-ineligible.
4. The current n=100 packets and truth have been used for development analysis.
5. The ParlaMint-GB working bank has no additional untouched n=100 reserve.
6. Fixed role was selected and evaluated on the same working n=100 sample.
7. The working run has one repetition, temperature 0.2 without a frozen seed,
   and model tags without immutable digests.
8. WarrantGate v0 has a floating-point tie defect and no independently
   calibrated multimodel training procedure.
9. WarrantRoute replacement versus cumulative semantics are unresolved for the
   successor study.
10. Credibility and confirmability judging was disabled.

The formal study may begin only after a new dated blocker register records zero
open blockers and references the passing readiness and freeze artifacts.
