# Legacy synthetic judge evidence

This directory records what can—and cannot—be reused from the historical
qualitative-coding model-judge run. It is an audit input for Research Direction
J, not a new evaluation result.

## Hard scope boundary

The audit script accepts no source-run argument. It reads only the allowlisted
`Storage/synthetic-results/model-qualification/20260825_synthetic_qualification`
run and its frozen benchmark, prompts, contracts, and schemas. It rejects any
input or output path containing a `dataset` or `datasets` path component and
fails closed unless the manifest still says all of the following:

- `qualification_scope` is `synthetic_only`;
- the benchmark explicitly contains no real source text;
- no real Dreaddit or AGYW text was processed; and
- held-out data were not used for selection.

The script also verifies every frozen SHA-256 digest named by the run manifest.
It does not read `dataset/`, does not contact a model or service, and does not
modify the shared baseline artifacts.

## Reproduce the inventory

From the project root, run:

```sh
python3 experiments/direction_j_llm_as_rater/scripts/audit_legacy_judges.py \
  --output experiments/direction_j_llm_as_rater/legacy_evidence/legacy_judge_inventory.json
```

The JSON is deterministic: it contains no audit-time timestamp or absolute
machine path. A second run against unchanged inputs must produce identical
bytes.

The re-pinned shared manifest also records a later `qc-paper-judge-v1`
measurement pilot: three OpenAI judges, 36 records, and 180 ratings against a
designed synthetic reference. It remains same-provider, has model-variant
overlap, and has no independent human ratings. It is not paired Direction J
evidence and was not used for item selection or prompt tuning. The current
inventory audits the original `qc-judge-v1` records while pinning the complete
extended manifest; the later pilot requires its own separate audit before any
descriptive reuse.

## What is reusable

The synthetic qualification provides a useful first engineering test bed:

- four entirely fictional packets, 48 excerpts, and stable packet, source, and
  excerpt identifiers;
- 60 candidate outputs from five model IDs, with three generation repetitions
  per packet;
- full source-plus-output blinded bundles;
- 36 legacy model-judge records and 180 candidate-score objects;
- the serious-error vocabulary, disposition vocabulary, confidence scale, and
  free-text rationale field; and
- deterministic integrity checks for schema, exact quotation, attribution,
  assignment completeness, code references, and multi-source themes.

These are suitable for synthetic pipeline qualification and for testing paired
item identifiers, parsing, blinding, and telemetry. The legacy records may be
retained as descriptive same-vendor starting evidence.

## What is not reusable as the Direction J primary interface

The historical `qc-judge-v1` record scores and ranks five candidates at once.
The paper-aligned record rates one `output_id`. The interfaces therefore differ
in unit, information context, and response structure.

Most importantly, the similarly named legacy fields are not the paper metrics:

- `evidential_support` is not `evidential_credibility`;
- `voice_context_preservation` plus `negative_case_preservation` is not the
  single `voice_boundary_preservation` item; and
- `analytic_contract_fit` is not `scope_calibration`.

The legacy interface also lacks metric-level `cannot_judge`, review time,
request latency, tokens, cost, a separate judge-repetition index, error
locations, independent expert adjudication, task outcomes, rationale-usefulness
ratings, and repair/collateral-error links. Its `run_index` is the candidate
generation repetition, not a repetition of the judge.

The paper schema's `evaluator_group` values are human expertise roles. An LLM
must not be assigned one of those values or described as a human. Direction J
needs an explicit LLM rater envelope while preserving the same item-level
rating payload shown to Charlie and later independent humans.

## Independence and blinding limitations

All three legacy judges are from the same vendor family as all five candidate
systems. The judge IDs `gpt-5.4`, `gpt-5.5`, and `gpt-5.6-sol` also appear
exactly in the candidate pool, so every judge record includes an anonymized
output from the same exact model ID as its judge. This overlap remains a design
limitation even though candidate labels were blinded.

The legacy blind order is deterministic, its seed is in the shared preparation
script, the private map is in the same run tree, and all judges see the same
candidate order. Direction J should use evaluator-isolated packets and a frozen,
balanced assignment plan unavailable to raters. Any evaluation guide or anchor
material must be identical across the LLM, Charlie, and independent-human arms.

## Interpretation rules

- Synthetic results must never be pooled with or labeled as real-corpus
  results.
- The blank historical human-review template is not human evidence.
- Agreement among related model judges is not validity.
- Serious-error flags in the legacy records are unadjudicated and must not be
  treated as gold labels.
- Direction J comparisons require paired item-level records, independent expert
  adjudication, and task outcomes.
- No protected real text may be processed until the documented institutional,
  platform, provider/model-processing, retention, privacy, and corpus-specific
  gates are satisfied.

The generated `legacy_judge_inventory.json` makes these limitations explicit
and reports unavailable outcomes as unavailable rather than filling them with
proxies.
