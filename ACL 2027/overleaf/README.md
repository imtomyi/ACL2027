# WarrantRoute — eight-page ACL manuscript skeleton

This folder contains the active ACL manuscript sources. Upload its prepared ZIP archive to Overleaf and compile `main.tex` with **pdfLaTeX** in Overleaf.

For local rendering, run `./build_manuscript_pdf.sh` from the workspace root.
The only local rendered manuscript is
`../output/pdf/warrant-route-acl2027-current-manuscript.pdf`. Do not compile
directly inside this folder.

## Upload in three steps

1. In Overleaf, choose **New Project → Upload Project**.
2. Upload `exports/warrant_route_acl2027_overleaf.zip`.
3. If Overleaf does not select it automatically, set `main.tex` as the main document and use pdfLaTeX.

## Included files

- `main.tex` — ACL review-mode entry point, result-placeholder commands, and abstract shell.
- `sections/paper.tex` — compact main paper, explicit RQ1--RQ2 framing, a standalone two-corpus dataset section and inventory table, and separate primary result tables for RQ1 and RQ2.
- `sections/appendix.tex` — concise supplementary protocol, ethics safeguards, and secondary reporting requirements.
- `custom.bib` — cited records with explicit archival and preprint status notes.
- `DATASET_PLAN.md` — the five candidate corpus lanes, verified source and processed-data audits, ethics caveats, access gates, and split constraints.
- `acl.sty` and `acl_natbib.bst` — unmodified official ACL files.
- `figures/` — publication PDFs, editable SVGs, and review PNGs for the WarrantRoute framework and the main role-by-flaw result template.
- `manuscript-draft/` — the earlier full protocol draft and its bibliography.
- `exports/` — the prepared Overleaf upload ZIP only. Local compiled manuscript PDFs do not belong here.

## Current status

- The project has been compiled successfully with the framework figure, the empty main result figure, separate RQ1 and RQ2 result tables, two supplementary RQ2 reporting tables, and every citation resolved.
- The current build has no LaTeX errors, undefined citations, missing controls, or overfull boxes.
- The manuscript is intentionally marked **pre-data**. It reports deterministic corpus-preparation statistics but no candidate-generation, human-rating, LLM-rating, routing, or other experimental result.
- The clean current build is **12 pages total**: the main paper occupies pages 1--7, references begin on page 8, and the appendix begins after the references on page 9 and ends on page 12. The unused eighth main-text page is reserved for actual results and their interpretation. Recount after every rebuild because page placement changes as placeholders are filled.
- Both figures are included as full-width vector PDFs. The result template contains no marks or estimates. Recompile and recount after inserting final values because page placement will change.

## Filling the manuscript

Search the project for the following three commands:

- `\fillin{...}` — replace the gray prose prompt with final text or a value.
- `\blankcell` — replace with a short result such as `0.81`.
- `\blankwide` — replace with a result and interval such as `0.81 [0.74, 0.87]`.

The main paper reserves one role-by-flaw figure and separate compact primary tables for RQ1 and RQ2. Each table requires `TP/N`, recall with a 95% interval, and paired percentage-point differences. RQ2 results are reported in the order analysis set and run integrity, pre-human WarrantRoute comparison, post-RQ1 common-packet human--LLM comparison, role-by-flaw patterns, then sensitivity and operations. RQ2 fields report pre-human LLM review on controlled variants; the human--LLM interpretation remains blank until RQ1 is complete. No third or fourth corpus row is reserved.

The appendix contains the supplementary protocol, data-governance safeguards, the RQ2 estimands and paired cluster-bootstrap specification, denominator and execution-flow accounting, a full primary-model role-by-flaw table, and model/repetition sensitivity fields. The sole pre-human confirmatory RQ2 contrast is the overall Cache2 WarrantRoute-minus-fixed-role difference for the prospectively designated primary snapshot. The post-RQ1 common-packet comparison applies its separately frozen practical-comparability margin and four-way interpretation. Dreaddit, flaw-specific estimates, additional models, and the two-of-three repetition ensemble are descriptive. The full pre-compaction appendix and its supporting assets are retained outside the active manuscript under `Storage/manuscript-exports/20260826_full_appendix_pre_compaction/` for internal records and must not be added to an upload package. Fill each active result field only from its corresponding frozen analysis export so denominators cannot drift between sections.

## Non-negotiable data policy

Fictional, synthetic, demo, toy, and mock datasets and all experiments or
results derived from them are never manuscript-eligible. Do not place them in
the abstract, main text, appendix, tables, figures, compiled PDFs, or Overleaf
ZIP. Keep missing experimental results as explicit `\fillin`, `\blankcell`, or
`\blankwide` placeholders until the authorized frozen real-corpus analysis is
complete.

Before compiling or exporting, run both checks:

```bash
python3 ../governance/scripts/check_required_manuscript_citations.py
python3 ../governance/scripts/check_manuscript_data_policy.py
```

The build or export must stop if either check fails. The citation check keeps
the six required related publications present in active manuscript prose;
citations in comments, inactive files, or `\nocite` do not count.

## Writing conventions

- Spell out the evaluator groups in prose: `researchers without specialist expertise`, `qualitative methods experts`, and `domain experts`.
- Do not introduce local acronyms for these groups. Narrow table headings use `Researchers`, `Methods experts`, and `Domain experts`.
- The manuscript narrative avoids dash punctuation and compressed compound labels. Preserve this style when adding results.
- Official publication titles in `custom.bib` remain unchanged even when the cited title itself contains a hyphen.

## Before submission

1. Confirm institutional, source or platform, model-processing, and rater-access authorization for every adopted corpus. Dreaddit and Cache2 (project alias: CaCHe) have provisional roles but remain governance-blocked. KODIS has a private exploratory conversion but no manuscript role; CaSiNo and AMI remain source-inventory candidates until their adapters, privacy reviews, experimental roles, and split constraints are approved and frozen.
2. Run `python3 ../governance/scripts/check_required_manuscript_citations.py` and `python3 ../governance/scripts/check_manuscript_data_policy.py`; stop on any failure.
3. Replace every `\fillin{...}`, `\blankcell`, and `\blankwide` field from one authorized, frozen real-corpus analysis export.
4. Replace the prospective abstract with a results-bearing abstract.
5. Set `\predatadraftfalse` in `main.tex` to remove the draft warning.
6. Keep the main content within the applicable page limit; place secondary protocol detail, operational records, robustness checks, and ablations in the appendix.
7. Keep `\usepackage[review]{acl}` and anonymous author metadata for review. For a camera-ready version, follow the venue instructions and change the ACL option/author block only then.
8. Recheck the ACL 2027 call and template immediately before submission. This package uses the latest official generic *ACL style available on 25 August 2026; an ACL 2027 venue-specific update was not yet assumed.

## Template provenance

Official source: <https://github.com/acl-org/acl-style-files>

- ACL style commit: `d5adc823ff0f80f98c80405ca0ab66c68e684409`
- Commit date: 29 June 2026
- `acl.sty` and `acl_natbib.bst` are copied byte-for-byte and have not been modified.

The earlier full protocol draft is preserved in `manuscript-draft/`; the files at this folder's top level form the compact Overleaf submission project.
