# ACE Paper Reproduction

All files physically stored in this directory support our local reproduction
or analysis. Pristine author sources are in `../original_sources/`.
`upstream` and the relevant `paper_reproduction/sources/` entries are
compatibility symlinks. The patched AppWorld checkout is under
`working_sources/ace-appworld-latest/`.

This directory is an isolated reproduction workspace for **Agentic Context
Engineering: Evolving Contexts for Self-Improving Language Models** (ICLR 2026,
arXiv:2510.04618). It uses the authors' released ACE and ACE-AppWorld code and
targets the paper's reported AppWorld and Finance results.

## Active reproduction

The active, paper-faithful work is in `paper_reproduction/`:

- `source_manifest.json`: paper and official repository revisions.
- `targets.json`: the exact Table 1 and Table 2 values being reproduced.
- `docs/STATUS.md`: completed setup, known release gaps, and current blocker.
- `scripts/preflight.py`: structural and API-readiness checks.
- `scripts/run_table1_appworld.sh`: AppWorld commands.
- `scripts/run_table2_finance.sh`: Finance commands.

Run the structural preflight with:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/preflight.py
```

Exact paper rollouts require an authorized `SAMBANOVA_API_KEY` for the paper's
non-thinking DeepSeek-V3.1 model. No local or substitute model is accepted as
evidence for the paper's reported numbers.

## Isolation

Everything used by this reproduction lives under this `ace_paper/` directory.
It does not read, import, modify, or compare against any other ACL2027
experiment, result, or manuscript.

## Archived local smoke

The older `reproduction/`, `results/`, and `REPRODUCTION_REPORT.md` artifacts
are retained only for provenance. They used a local Qwen model to exercise the
mechanism and are excluded from the paper reproduction and all reported-paper
claims.
