# KODIS private exploratory preprocessing

This path is for private exploratory analysis of the received
`raw/kodis/KODIS-EN.xlsx` workbook. It is deliberately separate from the
governed real-data workflow in `prepare_kodis.py` and does not change, bypass,
or satisfy that workflow's authorization and sampling gates.

Build the private exploratory bundle with:

```bash
python3 dataset/scripts/prepare_kodis_exploratory.py \
  dataset/raw/kodis/KODIS-EN.xlsx \
  --output dataset/deidentified/kodis_exploratory_private \
  --replace
```

The builder reads the workbook without writing it, verifies its hash before
and after processing, selects only nonempty human-human transcripts, and drops
all human-AI rows. It accepts observed seller-first dialogues and consecutive
messages from the same role. Transcript timestamps, raw dyad IDs, surveys,
demographics, country fields, point totals, preferences, tactics, and other
workbook columns are not written.

The output directory and files are private (`0700` and `0600`).

- `dialogues.jsonl` is a non-text dialogue index with source-row lineage,
  outcome, counts, first role, and repeated-role diagnostics.
- `turns.jsonl` contains the restricted Buyer/Seller message text exactly once,
  without source timestamps or raw dyad IDs.
- `aggregate_report.json` contains aggregate counts and distributions only.
- `build_report.json` binds the source, pipeline, and output files by checksum.

All records are assigned to `exploratory_unsplit`. The workbook has no stable
cross-dialogue participant identifier, so this output must not be used to claim
participant-disjoint training, validation, or evaluation. The transcript file
is pseudonymous only at the dialogue level; it is not anonymous. Keep it local
and do not publish, redistribute, quote, or upload it to an external service
without separate authorization.

Run the focused tests with:

```bash
python3 -m unittest dataset/tests/test_kodis_exploratory.py
```
