# ACL 2027 workspace

The workspace has seven clear entry points:

- `overleaf/` — the active ACL manuscript sources, earlier draft, and upload ZIP.
- `output/pdf/` — the sole location for the locally rendered manuscript PDF.
- `paper/` — literature only: source papers, reading lists, and publication libraries.
- `review/` — evidence records, screening scripts, generated review deliverables, and working files.
- `app/` — runnable software and data-collection tools.
- `dataset/` — private-by-default source data, de-identified working copies, and release-cleared research artifacts.
- `Storage/` — provenance records and inactive generated artifacts that are not manuscript inputs.

Use `overleaf/` for writing, `paper/` for reading, and `review/` for the reproducible literature-review workflow.

For a local manuscript build, run `./build_manuscript_pdf.sh` from the workspace
root. It writes the single rendered manuscript to
`output/pdf/warrant-route-acl2027-current-manuscript.pdf`. Do not run a direct
local `latexmk` or `pdflatex` build inside `overleaf/`, because that creates a
duplicate manuscript PDF there.

## Manuscript data policy

Fictional, synthetic, demo, toy, and mock datasets and every experiment or
result derived from them are records-only and are never eligible for a
manuscript, appendix, figure, table, compiled PDF, or submission export. Missing
experimental results remain explicit placeholders until an authorized,
frozen real-corpus analysis produces them. Before every build or export, run
`python3 governance/scripts/check_required_manuscript_citations.py` and
`python3 governance/scripts/check_manuscript_data_policy.py`; stop if either
check fails.

For the records-only index, including `kodis_demo`, see
[`dataset/SYNTHETIC_DATA.md`](dataset/SYNTHETIC_DATA.md).
