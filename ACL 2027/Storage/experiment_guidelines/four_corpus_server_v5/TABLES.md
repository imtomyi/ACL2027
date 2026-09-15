# Result-table specification

These templates contain no measured server scores. The main [summary CSV](summary_template.csv) contains all 28 planned conditions; the [long metric CSV](metrics_long_template.csv) holds the complete metric export schema. Do not count a template as an executed run.

## Required dataset-specific metric context

Display the [dataset metric conditions](DATASET_METRIC_CONDITIONS.md) beside the results: profile ID, evaluation unit, Adaptation GT, Evaluation reference, label/codebook size and planned/valid/resolved N. Use Acc (binary) versus Acc (exact set), Macro-F1 (2-class) versus Macro-F1 (28-label), and Conformability v2 with the task-profile ID. In a compact dataset subsection, put these fields immediately above the table; a wide multi-dataset table needs visible header footnotes. JSON-only disclosure is insufficient.

The summary CSV now stores profile and definition fields; the long export stores all required condition IDs, hashes, averaging/denominator, probability source and runtime profile. No result may finalize with an unresolved applicable definition field.

## Main display

Use separate model sections and dataset subsections. Show 28 condition rows per model, aggregating seeds 42/43/44 only after displaying individual seed exports. Keep seed completion visible and do not average a partial subset as if all three finished.

| **Phase** | **Method** | **Adaptation GT** | **N / seed** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **Resolved / seed** | **Δ vs Base (pp)** | **Seeds** | **Status** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Add corpus-specific stress-F1/balanced-Acc/MCC or sample-F1/Hamming-loss in a companion task-quality table. Each delta must identify its metric. A single unnamed delta column is forbidden. Prefer separate named deltas or a selected-metric display with a visible metric selector. Confidence intervals accompany the corresponding metric in a companion uncertainty table; online uncertainty must follow the dependency caveat.

## Operational display, one row per condition and seed

| **Dataset** | **Method / GT** | **Seed** | **Stage** | **Predicted** | **Updated** | **Judged** | **Unresolved** | **Active time** | **Paused time** | **Tokens in/out** | **Retries** | **Peak VRAM** | **ETA scope** | **Status** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Predicted is valid committed predictions /100. Required online updates are /100. Baseline updates are N/A. Offline adaptation uses its own adapted/100 counter, not online updates. Optimizer progress reports candidates/trials/metric calls, not evaluation prediction percentage. Judge progress is independent. Unresolved counts include failed judgments separately from unattempted judgments.

## Full metric export

One row per metric/condition/seed/slice. Keep class-wise vectors as separate class-indexed rows or linked arrays with inventory hashes. Include version, numerator/denominator, missing counts, status, units and artifact lineage. Use metric-specific deltas/CI fields instead of blending different scores. All scores are reconstructed from record IDs and validated artifacts.

## Optional AppWorld reference display

Keep Test-Normal TGC, Test-Normal SGC, Test-Challenge TGC and Test-Challenge SGC as N/A in the four-corpus metric export. Do not crowd the main comparison with four identically inapplicable columns; if the original Notion layout requires them, preserve N/A explicitly. No proxy values.

## Display rules

- N/A: inapplicable; NC: applicable prerequisite not collected; PENDING: unfinished; FAILED/PAUSED: execution status, never a score.
- Show matched Base deltas in percentage points, not relative percentages.
- Show mean ± sample SD only with the number of repetitions. Bold best values only within the same model, dataset, phase, GT regime, metric and completed denominator; ties remain ties. Do not bold a partial run.
- Include model revision, quantization, context, judge family/rubric, train/dev/eval counts, seeds, method budget profile and protocol ID in the table metadata.
- CaChe/ParlaMint task accuracy and classification F1 stay N/A. Same-family judging and unresolved decisions remain visible.
- Pause state takes precedence over stale per-method running flags. A finished process with failures is not a completed evaluation.
- Five-minute English reports resume only with the experiment: dataset/method/GT/phase, predicted/updated/judged, unresolved, completed condition-runs/84, aggregated conditions/28, measured speed, phase ETA and full-run ETA separately. Never label phase ETA as full-run ETA.
