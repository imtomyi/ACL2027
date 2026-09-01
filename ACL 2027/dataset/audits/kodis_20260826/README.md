# KODIS received-package audit - 2026-08-26

## Scope

This is an aggregate, non-text audit of the restricted `KODIS-EN.xlsx` receipt.
It does not authorize model processing, rater display, quotation, redistribution,
or sampling. The source workbook and provider README remain under
`dataset/raw/kodis/` with restricted permissions.

## Reproducibility

Run:

```bash
python3 dataset/scripts/audit_kodis_workbook.py \
  dataset/raw/kodis/KODIS-EN.xlsx \
  --output-dir dataset/audits/kodis_20260826
```

The audit emits `aggregate_metrics.json` and an aggregate human-human country
distribution. It never emits transcript text, raw dyad IDs, survey responses,
or row-level records.

## Key findings

- Source SHA-256: `81f3f6d8c450bd39366f3c976803470a6d4e7049913330fb2daf4b7aa88270a1`.
- One worksheet, 2,860 unique dyads, and 107 columns.
- 2,085 dyads are flagged human-human and 775 human-AI; no dyad is flagged AI-AI.
- Human-human outcomes: 1,712 resolution (82.1%) and 373 impasse (17.9%).
- Nine human-human rows have no transcript. The 2,076 nonempty human-human
  transcripts contain 27,121 parsed messages and 568,333 parsed words.
- The median nonempty human-human transcript has 12 messages (IQR 11-14) and
  242 words (IQR 180-334).
- No exact duplicate nonempty transcript was detected.
- 271 nonempty human-human transcripts contain consecutive messages by the same
  role, and nine begin with the seller. Only 1,798 human-human dialogues satisfy
  the current synthetic adapter's strict structural rules. This is evidence that
  those fictional rules need revision for the real release, not a basis for
  deleting the other dialogues.
- The workbook has no stable cross-dialogue participant identifier, explicit
  completion marker, event-type field, message identifier, or reply link.

## Manuscript feasibility decision

KODIS is feasible to add immediately as a **received, restricted, source-only
candidate** in the manuscript's dataset inventory. It is not yet feasible to
describe it as processed, sampling-eligible, or assigned to a real experiment.

The cleanest manuscript design is to replace the current CaSiNo source-only
dyadic lane with KODIS, rather than expand from four to five lanes. KODIS is
larger, explicitly multicultural, and directly evokes emotionally charged
buyer-seller disputes, which aligns well with WarrantRoute's voice, scope, and
evidential-warrant questions. However, both KODIS and CaSiNo lack released
cross-dialogue person linkage, so KODIS does not solve participant-isolated
splitting. Unless the provider supplies linkage, it should be preregistered in
one unsplit role.

Before KODIS can enter generation, sampling, or human evaluation, the project
must record the governing access terms and institutional determination; obtain
explicit model/rater and quotation scope; confirm completeness and transcript
semantics with the provider; revise and validate the XLSX adapter without
requiring strict role alternation; define an unsplit role or obtain stable
participant linkage; minimize to complete human-human transcript text and
role/turn lineage; and complete the two-person contextual privacy review.
