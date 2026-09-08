# Workspace manuscript policy

- Write all manuscript prose, headings, role and operation labels, captions,
  tables, figures, and paper-facing design documents entirely in English.
  Use consistent English terminology throughout.
- Never incorporate fictional, synthetic, demo, toy, or mock datasets, or any
  experiment, result, model choice, metric, table, figure, or claim derived from
  them, into a manuscript source, draft, appendix, compiled PDF, or submission
  export. Labeling such material does not make it manuscript-eligible.
- Retain this material only as records under `Storage/`. It may be used for
  internal software testing, but never as manuscript evidence or to fill a
  manuscript result placeholder.
- When an authorized real-corpus experiment has not produced a result, keep an
  explicit `\fillin`, `\blankcell`, or `\blankwide` placeholder. Never infer,
  simulate, or substitute a value.
- Keep every publication enforced by
  `governance/scripts/check_required_manuscript_citations.py` cited at least
  once in the active manuscript. Citations in comments, inactive files, or
  `\nocite` do not satisfy this requirement.
- The caption of Table 1, which reports data statistics, must be exactly
  `Data Statistics`. Place all dataset-specific preparation details and
  qualifications in the main-text dataset section, including the Dreaddit
  duplicate-handling and exact-date-quarantine rules, the CaChe three-word
  participant-turn rule, and the distinction between candidate counts and
  privacy-cleared samples, final packet denominators, or experimental outcomes.
  Every header label in Table 1 must render on one line. This one-line header
  requirement applies only to Table 1 (`Data Statistics`) and must not be
  generalized to other tables.
- Aside from dataset names needed for headings, references, and citations, the
  Section 2 dataset prose and Table 1 must be complementary. Treat Table 1 as
  the authoritative and sole reporting location for every categorical field
  and statistic it contains, including domain, context-window category,
  document count, analysis language, total words, and average words. Do not
  restate a Table 1 cell value in the prose. If duplication occurs, retain the
  table and remove or recast the prose. Use the prose for column definitions,
  source provenance not shown in the table, preparation and exclusion rules,
  split roles, limitations, and the distinction between candidate counts and
  privacy-cleared samples, final packet denominators, and outcomes.
- Use `CaChe` as the sole display name for that corpus throughout the active
  manuscript, including the abstract, headings, prose, tables, figures,
  captions, placeholders, and appendices. Do not use `Cache2`, `CaCHe`, or a
  combined form as a manuscript label. Preserve exact official publication and
  repository titles in bibliographic metadata, and preserve internal citation
  keys, corpus identifiers, URLs, filenames, and source records.
- In every table or figure that presents more than one dataset, display the
  datasets in the same order used in Table 1 (`Data Statistics`). Preserve that
  order across main-text and appendix results, including when a dataset label
  carries a split qualifier such as `test`. Do not reorder datasets by study
  role, result magnitude, or narrative emphasis.
- Make the complete header row of every main-text and appendix table fully
  bold. When a table uses more than one header row, bold every header label in
  all header rows.
- Keep every table caption as short as possible. Aim for three rendered lines or
  fewer and never exceed four rendered lines in the compiled review PDF. Prefer
  a short descriptive title. Move definitions, denominators, formulas,
  comparison directions, exclusions, failure handling, interpretation rules,
  methodological details, provenance, and placeholder instructions to the
  surrounding manuscript prose. Retain only essential table-reading keys, such
  as `Bold marks the highest value. Underlining marks the second-highest value.`
  Include a key only when that formatting is actually used in the table, and do
  not add a ranking key while the values remain placeholders.
- Keep the rendered `Limitations` section and the rendered `Conclusion` section
  each to no more than one fifth of one ACL manuscript page, including the
  section heading and body. In the two-column ACL layout, one fifth of a page is
  equivalent to at most 40 percent of one full text column. If either section
  crosses a column or page boundary, add its occupied space across both parts.
  Shorten the prose when necessary rather than reducing the required font size,
  line spacing, or section spacing.
- Write the locally compiled manuscript PDF only to
  `output/pdf/warrant-route-acl2027-current-manuscript.pdf`. Do not create or
  retain rendered manuscript PDFs under `overleaf/`, `overleaf/exports/`,
  `tmp/`, or any other directory. PDF files under `overleaf/figures/` are source
  figure assets and are exempt. Use `build_manuscript_pdf.sh` for every local
  manuscript build.
- Do not begin a sentence in active manuscript prose, captions, or appendices
  with `Because` or `But`.

## Required final manuscript checklist

Before treating any manuscript, compiled PDF, or submission export as final,
complete and report a final manuscript checklist. The checklist is
non-exhaustive, but it must include all of the following:

- Verify the active manuscript and compiled review PDF against the current,
  official ACL Rolling Review (ARR) review-submission formatting requirements.
  Check the applicable template and style files, anonymity, page limits,
  required sections, bibliography and appendix treatment, limitations and
  responsible-NLP requirements, and all upload-package constraints. Use the
  requirements for the intended review cycle rather than relying on memory or
  a camera-ready checklist.
- Remove all drafting instructions, manuscript-skeleton notices, internal
  comments, and authoring callouts from the source and rendered PDF. This
  includes the notice `Manuscript skeleton: gray fields and blank table cells
  must be replaced from the frozen analysis export.` and close variants of it.
- Remove all GPT-like formatting and stylistic artifacts from active manuscript
  prose, captions, tables, footnotes, and appendices. This includes, but is not
  limited to, dash-based asides or constructions using em dashes, en dashes,
  double hyphens (`--`), or spaced or repeated hyphens such as `- -`. Rewrite
  affected passages as natural, conventional academic prose rather than merely
  deleting punctuation in a way that changes or obscures the meaning. Treat
  semicolon-linked clauses and expressions ending in a semicolon as GPT-like,
  including constructions such as `the loop for this task;`. Replace them with
  grammatically complete sentences or a conventional conjunction, while
  preserving the intended meaning.
- Replace every gray placeholder field and every blank result table cell only
  with authorized real-corpus results from the applicable frozen analysis
  export. Resolve the corresponding result statements in the abstract and main
  text at the same time so that prose, tables, captions, and appendices agree.
- Confirm that no gray result fields, `\fillin`, `\blankcell`, `\blankwide`,
  unexplained blank result cells, prospective-result wording, or manuscript-
  skeleton text remains anywhere in the final source or rendered PDF. If an
  authorized result is still unavailable, retain the explicit placeholder as
  required above and do not label or export the manuscript as final.
- Re-run the workspace manuscript-policy checks: exclude all ineligible
  fictional or synthetic material, satisfy the required-citation checker, and
  confirm that no active sentence begins with `Because` or `But`.
- Confirm that every table caption is as short as possible and spans no more
  than four rendered lines. Confirm that it contains only a brief descriptive
  title and any table-reading key actually used. Confirm that all methodological
  and explanatory details appear in the surrounding manuscript prose.
- Confirm that every main-text and appendix table has fully bold header labels,
  including every label in a multirow header. Confirm separately that every
  Table 1 (`Data Statistics`) header label renders on one line. Do not apply the
  one-line requirement to other tables.
- Confirm that the Section 2 dataset prose does not restate any Table 1 cell
  value or statistic, apart from dataset names needed for navigation and
  citation. Confirm that Table 1 remains authoritative and that the prose still
  contains all required preparation rules, qualifications, source-versus-
  analysis distinctions, and candidate-versus-final-denominator caveats.
- Confirm that every active manuscript display name for the corpus is exactly
  `CaChe`, with no `Cache2`, `CaCHe`, or combined-form label remaining outside
  exact bibliographic titles or non-rendered internal identifiers.
- Confirm that every table and figure containing more than one dataset follows
  the dataset order established in Table 1, including all main-text and appendix
  results and any split-qualified dataset labels.
- Confirm in the compiled review PDF that `Limitations` and `Conclusion`, each
  including its heading, occupy no more than one fifth of a page. In the
  two-column ACL layout, each section must use no more than 40 percent of one
  full text column after summing any portion split across columns or pages.
- Confirm that the only locally rendered manuscript PDF is
  `output/pdf/warrant-route-acl2027-current-manuscript.pdf` and that no duplicate
  manuscript PDF remains under `overleaf/`, `overleaf/exports/`, `tmp/`, or any
  other directory.
- Compile from the final source and visually inspect the entire PDF for
  unresolved references or citations, overflow, clipping, illegible figures
  or tables, unintended color or highlighting, inconsistent values, and stray
  draft material. Confirm that the submission package contains only permitted
  files and excludes internal records under `Storage/`.
