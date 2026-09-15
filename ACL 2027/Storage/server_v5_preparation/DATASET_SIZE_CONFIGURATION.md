# Dataset-size configuration

The current experiment stays at 100 train, 100 dev and 100 evaluation records per corpus. Future counts are controlled by [`dataset_sizes.json`](../../experiments/server_v5_configurable/dataset_sizes.json).

- Set `defaults.train`, `defaults.dev` and `defaults.test` independently.
- Use `overrides.<corpus>.<split>` for a dataset-specific count.
- Use `"all"` for every eligible record in an already assigned, validated split.
- Counts flow into sampling, frozen manifests, Base/ICL, ACE/DC, online update lengths, progress totals and metric denominators. A size change creates a fresh run root and retains earlier results separately.

The configurable runner and full-pool interface are documented in [README.md](../../experiments/server_v5_configurable/README.md). Dataset-specific raw-source import and eligibility/split audits remain required. The current 100-record snapshot cannot supply a 500-record run: the preparer reports a shortfall instead of duplicating or silently capping rows.

The bundle was tested under the pinned MIATA Python runtime without model calls, including unequal train/test sizes, online update counts, deterministic nested samples, per-dataset overrides, all-record selection, immutable manifests, and accuracy using the actual evaluation denominator. MIPROv2/GEPA and judge integration remain pending; this configuration does not claim those methods are implemented.
