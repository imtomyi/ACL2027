# Four-corpus experiment package v5

Start with [GUIDELINES.md](GUIDELINES.md), the complete merged experimental design. v5 is a guideline version, not a claim of a new completed ACE run.

| **Document / artifact** | **Purpose** |
| --- | --- |
| [GUIDELINES.md](GUIDELINES.md) | Dataset sizes, 28 method conditions, seeds, runtime rules, scoring, reporting and failure policy |
| [DATASET_METRIC_CONDITIONS.md](DATASET_METRIC_CONDITIONS.md) | Explicit task/GT/label/denominator differences across the four datasets |
| [METRIC_REGISTRY.md](METRIC_REGISTRY.md) | 85 metric entries/families and their prerequisites |
| [metric_applicability.csv](metric_applicability.csv) | 340 metric-by-dataset condition records |
| [TABLES.md](TABLES.md) | Main/detail/operational table rules and required condition labels |
| [summary_template.csv](summary_template.csv) | 28 unexecuted condition placeholders per model |
| [metrics_long_template.csv](metrics_long_template.csv) | Complete metric export schema |
| [MERGE_DECISIONS.md](MERGE_DECISIONS.md) | Resolutions of differing historical/new settings |
| [HISTORY_AND_REUSE.md](HISTORY_AND_REUSE.md) | Separate old results, MIATA locations, runtime assets and unfinished drafts |
| [EXECUTION_READINESS.md](EXECUTION_READINESS.md) | Missing implementation and execution seal requirements |
| [protocol.json](protocol.json) | Machine-readable design, all conditions and metric profiles |
| [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) | Original paths and hashes of preserved source files |

The source archive contains the previous design and the verified MIATA handoff, including its local-only drafts and selected audit records. These are historical evidence, not automatically adopted instructions or executable v5 components. Large server-only data/model/runtime files were not downloaded.

Fixed targets: train/adaptation 100 + development 100 + evaluation 100 per corpus, 400 unique evaluation items, 28 conditions × 3 seeds = 84 condition-runs per model, and no wall-clock cutoff. Exact backbone/judge selection, eligible split preparation, implementation and execution sealing remain pending. Existing experiments and monitors stay paused.

Verify package integrity without network or inference: `python3 verify_package.py` from this directory. This checks document/source hashes and design consistency, not model execution readiness.
