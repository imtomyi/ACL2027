# Paper-aligned synthetic metric results

## Scope

This measurement-pipeline pilot calculates the four artifact-quality measures
defined in the ACL manuscript on 60 outputs from entirely fictional packets. It
does not estimate performance on the real Dreaddit, CaCHe/AGYW, KODIS, or CANDOR
corpora.

Three blinded model judges (GPT-5.5, GPT-5.6 Sol, and GPT-5.6 Terra) independently
rated every output. Each model has 36 rater-output judgments for the ordinal
measures. Code and theme coverage use a two-of-three recovery rule over 63 frozen
synthetic reference opportunities per model and level. Intervals are 95%
percentile bootstrap intervals clustered by packet and run (20,000 replicates).

## Complete four-metric table

| Model | Integrity gate | Evidential adequacy, % [95% CI] | Voice/boundary adequacy, % [95% CI] | Scope adequacy, % [95% CI] | Code coverage, % [95% CI] | Theme coverage, % [95% CI] | Serious-error rate, % [95% CI] |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | **10/12** | 100.0 [100.0, 100.0] | **100.0 [100.0, 100.0]** | **100.0 [100.0, 100.0]** | 93.7 [89.1, 98.4] | 85.7 [78.5, 93.4] | **0.0 [0.0, 0.0]** |
| GPT-5.4 | 9/12 | 100.0 [100.0, 100.0] | 97.2 [91.7, 100.0] | 100.0 [100.0, 100.0] | 93.7 [89.1, 98.4] | **93.7 [89.1, 98.4]** | 5.6 [0.0, 13.9] |
| GPT-5.5 | 9/12 | 100.0 [100.0, 100.0] | **100.0 [100.0, 100.0]** | **100.0 [100.0, 100.0]** | 93.7 [89.1, 98.4] | 92.1 [87.3, 96.8] | **0.0 [0.0, 0.0]** |
| GPT-5.6 Luna | 8/12 | 80.6 [69.4, 91.7] | 80.6 [69.4, 91.7] | 88.9 [80.6, 97.2] | **95.2 [90.9, 100.0]** | 85.7 [79.7, 91.9] | 8.3 [0.0, 16.7] |
| GPT-5.6 Terra | 5/12 | 100.0 [100.0, 100.0] | **100.0 [100.0, 100.0]** | **100.0 [100.0, 100.0]** | **95.2 [90.9, 100.0]** | 88.9 [84.1, 93.7] | **0.0 [0.0, 0.0]** |

## Interpretation

The four measures are calculable, but adequacy rates alone are not sufficiently
discriminative for model selection. GPT-5.6 Sol, GPT-5.5, and GPT-5.6 Terra all
receive 100% adequacy on the three ordinal measures, while their deterministic
integrity pass rates are 83.3%, 75.0%, and 41.7%. The raw ordinal means reveal
additional separation that the adequacy threshold hides: for GPT-5.6 Sol they
are 4.92, 4.92, and 4.94; for GPT-5.6 Terra they are 4.61, 4.47, and 4.69.

Coverage is also compressed and recall-like. GPT-5.6 Luna has the joint-highest
code coverage despite substantially weaker evidential and voice/boundary scores.
This confirms that coverage cannot be interpreted without integrity, unsupported
concept, redundancy, and output-volume diagnostics.

The selection rule therefore remains gate-first. GPT-5.6 Sol is the remediation
candidate because it has the strongest integrity portfolio and no panel-flagged
serious errors, not because of an omnibus average. GPT-5.4 has the strongest
theme coverage but fails more integrity gates and has a nonzero serious-error
rate. No model is yet the frozen paper model.

## Paper implications

Retain the four constructs as a **source-grounded artifact profile**, with these
required companions:

1. deterministic integrity pass count and failure reasons;
2. full ordinal score distributions, not adequacy alone;
3. serious-error and cannot-judge rates;
4. generated code/theme volume, unmatched concepts, redundancy, and a
   human-audited unsupported-concept rate; and
5. controlled-defect sensitivity and evaluator-role reliability in the real
   study.

The synthetic reference space is the benchmark's frozen designed-construct set,
not the final multi-analyst human pool required for confirmatory
plural-reference coverage. The panel and candidates are all from one provider.
These limitations are stated in the manuscript table caption and prevent this
pilot from being presented as a real-corpus or human-evaluation result.

## Audit artifacts

- `paper_metric_model_summary.csv`: five-row model table with point estimates,
  intervals, raw means, leave-self-judge-out sensitivity, and matching unanimity.
- `paper_metric_model_dataset_summary.csv`: all four measures for every
  model-by-synthetic-dataset combination.
- `paper_metric_ratings_long.csv`: 180 direct ordinal ratings.
- `paper_metric_matches_long.csv`: 1,890 independent reference matches.
- `paper_metric_panel_matches.csv`: 630 majority-adjudicated matches.
- `paper_metric_validation_summary.json`: complete validation accounting.
- `paper_judges/`: immutable paper-aligned blinded judge records.

