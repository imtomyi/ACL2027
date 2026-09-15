# Configurable dataset sizes for future v5 runs

Edit **`dataset_sizes.json`**. The running 100-item experiment is frozen and is not changed by this bundle.

```json
{
  "schema_version": 1,
  "sampling_seed": 42,
  "defaults": {"train": 100, "dev": 100, "test": 500},
  "overrides": {
    "goemotions": {"test": 1000},
    "parlamint_gb": {"train": "all", "dev": "all", "test": "all"}
  }
}
```

`train` controls offline adaptation data; `dev` controls the optimization/validation pool; `test` controls evaluation and the online stream. A count applies to every method and repetition for that dataset. The unchanged ICL protocol still uses eight demonstrations selected from train; increasing train does not silently increase the demonstration count. MIPROv2 trials and GEPA call budgets are separate optimization settings and are not silently increased by changing a pool size. Their adapters remain pending integration, as in the active v5 panel.

`"all"` means all eligible records in the existing assigned split, after its source/split audit. It does not combine train and test, include excluded raw records, or invent GT. Full GoEmotions evaluation means the official eligible test pool. Full CaChe/ParlaMint evaluation means the eligible held-out session/document pool. Fixed group assignments must be established before sampling. Increasing a count never moves a session/document from train into test.

## Input pools and preparation

The one-time source-pool preparation must produce canonical JSONL files at `POOL_ROOT/<corpus>/{train,dev,test}.jsonl`, with record_id, text, source_id where available, and the original target only where validated GT exists. Corpus keys are dreaddit, goemotions, cache, parlamint_gb. Use the existing dataset-specific source, eligibility, group-disjointness and duplicate rules. This bundle consumes those validated pools; it does not replace the raw-corpus importers or their audits.

`POOL_ROOT/pool_manifest.json` must contain `status: "validated"`, `cross_split_checks_passed: true`, and `files`, a mapping from each relative JSONL path to its SHA256. Retain the underlying source/eligibility/split audit and its limitations with that pool. Mechanical validation does not imply human annotation or privacy review. The current server panel contains only 100 records per role: requesting 500 from that snapshot raises an explicit shortfall. A larger run needs the larger validated source pool; it will not duplicate rows or silently cap the request.

Prepare a fresh run root, with no model calls:

```sh
python prepare_panels.py --config dataset_sizes.json --pool-root /path/to/validated-pools --out /path/to/new-run
```

Preparation seals the requested and actual counts, selected IDs, source hashes and config into `sampling_manifest.json`. Stable ID-hash ordering makes a smaller sample a prefix of a larger sample under the same seed and pool. `all` resolves to numeric counts before runners start. Existing output directories are rejected. Editing a config requires a fresh run root, fresh validation and a new result version.

## What is connected

- `prepare_prediction_stage.py`: demonstrations, orders, per-cell sizes and the full panel target.
- `predict_stage.py`: evaluates the sealed item count and rejects count drift.
- `adaptation/stage.py` and `adaptation/run.py`: offline train length, frozen evaluation length, online update count, and all progress targets. Six development-probe items per condition remain a separate validation setting; dev must contain at least six records.
- `report_predictions.py`: accuracy and F1 completion checks use the actual frozen evaluation set. Invalid outputs remain incorrect in accuracy. There is no hard-coded 100-item denominator.
- `progress.py`: stage and full-panel totals derive from manifests.
- `render_results.py`: per-dataset, per-seed and aggregate denominators derive from sealed sizes, including rows for methods not yet run.

The final memory budget, model/token caps, GT rules, method conditions and three inference seeds remain independent of sample size. New sample counts never reuse old predictions as if they belonged to the new panel. The r3 bounded DC memory items and r4 1600-character DC explanation limit remain declared method-specific task-transfer settings.

## Future execution handoff

This is a prepared runner bundle, not a second launched experiment. For a future run, copy the selected task definitions, runtime/model pins, protocol and explicit amendments into the fresh root as `tasks.json`, `runtime.json`, `protocol.json` and `AMENDMENTS.json`. Establish fresh ownership of available GPU services after the existing run has released them. Do not copy an old live service ownership file into a new root. Run the Base development preflight before sealing its prediction manifest.

For ACE/DC, copy `code/adaptation/*.py` into a new stage's `code/`, reuse the verified upstream source bundle, and provide an updated `REVISION.json` describing the new sampling manifest. Run behavior checks under the pinned runtime, save `tests.json`, then call the stage's prepare, preflight, seal and launch actions in order with `PYTHONPATH=STAGE/code:RUN/code`. The 18-case gate is mandatory. This preserves separate scientific revisions and avoids changing any active source seal.

The exact run/GT/metric configuration remains in the canonical v5 guidelines. Conformability requires the selected judge; changing sample size does not make pending metrics measured.
