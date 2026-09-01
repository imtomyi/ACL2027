# Five-corpus pre-human-feedback inventory - 2026-08-26

This folder consolidates aggregate, text-free preparation statistics for every
real corpus currently on disk: Dreaddit, Cache2/CaCHe, KODIS, CaSiNo, and the
AMI scenario meetings. It is preparation accounting, not a real-corpus model
or human-evaluation result.

Rebuild from the workspace root:

```bash
python3 dataset/scripts/build_all_corpus_inventory.py
```

- `corpus_inventory.csv` is the manuscript-facing corpus inventory.
- `aggregate_inventory.json` records the source reports and the boundary
  between completed deterministic work and required human input.
- `results_cell_status.csv` maps each still-empty results table to the human
  evidence required to populate it.

The script reads existing aggregate reports and minimized working records. It
does not copy transcript text, source identifiers, participant attributes, or
row-level data into this folder.
