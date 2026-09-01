# AMI source-balance internal experiment

This directory contains a private, offline experiment on the real AMI
scenario-meeting transcripts. It tests how source concentration and role-aware
balancing affect four-way meeting-phase classification.

The experiment is deliberately separate from the active WarrantRoute
manuscript study. Its results are not measurements of human adequacy,
expertise sensitivity, routing, or repair and must not be substituted into
those table cells.

The runner emits no transcript text, per-meeting record, or raw AMI identifier.
Generated aggregate outputs are placed in `results/`.

Run from the workspace root:

```bash
/usr/local/bin/python3.11 \
  Storage/internal-experiments/ami_source_balance_v1/run_experiment.py
```

Validate the adapter without fitting models:

```bash
/usr/local/bin/python3.11 \
  Storage/internal-experiments/ami_source_balance_v1/run_experiment.py \
  --validate-only
```

See `PROTOCOL.md` for the frozen design and `ATTRIBUTION.md` for source and
license provenance.

After a run, read `results/report.md` together with `POSTRUN_REVIEW.md`. The
review narrows the interpretation, records the text-volume confound, and
distinguishes the conditional bootstrap from broader population uncertainty.
