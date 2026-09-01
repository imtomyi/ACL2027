# Qualitative-coding model baselines

This directory contains the reproducible model-qualification work for bounded,
evidence-linked qualitative coding. It deliberately separates three things that
must not be conflated:

1. **Synthetic engineering qualification** checks whether a model can follow the
   output contract, quote sources exactly, preserve negative cases, and produce
   useful codebook-oriented analysis on fictional packets.
2. **Model selection** must use only approved, eligible Dreaddit development
   records. It cannot use Dreaddit test, AGYW/CaCHe, KODIS, or CANDOR results.
3. **Held-out evaluation** occurs only after the model, prompt, packet rules,
   schema, settings, retries, and stopping rules are frozen.

The 2026-08-25 run is a synthetic qualification because the workspace does not
document authorization to send real Dreaddit or AGYW text to a model. KODIS is
present only in a separate private exploratory lane, and no KODIS or CANDOR
input is authorized for this baseline. Its ranking is therefore
an engineering recommendation, not the paper's confirmatory model selection.

## Layout

- `protocol/analytic_contract.md` — method and selection rules.
- `protocol/generation_prompt.md` — frozen direct-workflow instructions.
- `protocol/human_review_rubric.md` — blinded review form for later experts.
- `protocol/paper_metric_data_contract.md` — exact collection and reporting
  contract for the manuscript's four artifact-quality measures.
- `schemas/qualitative_output.schema.json` — required model output.
- `schemas/paper_metric_rating.schema.json` — paper-aligned ordinal rating record.
- `schemas/plural_reference_match.schema.json` — blinded code/theme concept-match
  record for plural-reference coverage.
- `benchmark/synthetic_packets_v1.json` — fictional, source-linked packets.
- `scripts/validate_and_score.py` — deterministic integrity and coverage audit.
- `scripts/aggregate_paper_metrics.py` — validates the paper-aligned blinded panel
  and computes all four measures with packet-by-run bootstrap intervals.
- `runs/<run_id>/raw/` — immutable model/run outputs.
- `runs/<run_id>/` — manifests, long-form metrics, summaries, and workbook.
- `runs/README.md` — run registry and immutability convention.

The cross-project index for synthetic fixtures, demo outputs, governance status,
and manuscript artifacts is [`../../dataset/SYNTHETIC_DATA.md`](../../dataset/SYNTHETIC_DATA.md).

## Governance gate

No script in this directory reads `dataset/deidentified/` by default. A future
real-data runner must fail closed unless a signed local approval manifest names
the permitted corpus, split, fields, provider, retention mode, approval scope,
and approval date. Even then, model selection is restricted to Dreaddit train.

## Interpretation

There is no unique gold thematic analysis. Automatic metrics are integrity and
diagnostic checks, not proof of interpretive validity. Final selection requires
blinded, source-symmetric assessment by qualified reviewers, with disagreement
retained, and a selection rule fixed before inspecting held-out results.
